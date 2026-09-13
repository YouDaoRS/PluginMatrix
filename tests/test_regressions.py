"""Behavioral regressions found in the independent v0.5.0 review."""
import json
import os
import struct
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from probe_support import probe_writer, one_probe

from pluginmatrix.cli import main
from pluginmatrix.files import atomic_json, protect_inputs
from pluginmatrix.matrix import MatrixConfig, MatrixEnvironment, run_matrix, matrix_exit_code, validate_matrix_preconditions
from pluginmatrix.model import VerificationResult
from pluginmatrix.preflight import inspect_plugin, PreflightError
from pluginmatrix.probe import read_probe_evidence
from pluginmatrix.runtime import RuntimeEvidence, run_server_process, validate_plugin_inputs, verify


def plugin(path, name='Example', version='1.0', extra=''):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, 'w') as jar:
        jar.writestr('plugin.yml', f'name: {name}\nversion: {version}\nmain: example.Main # valid comment\napi-version: \'1.20.5\'\n{extra}')
        jar.writestr('example/Main.class', b'\xca\xfe\xba\xbe\x00\x00\x00\x3d')
    return path


class RegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def process(self, code, stability=.4, timeout=2, expected_version=None):
        return run_server_process([sys.executable, '-u', '-c', code], self.root,
                                  self.root/'server.log', 'Example', 'example.jar', timeout, stability,
                                  self.root/'probe.json', True, expected_version=expected_version)

    def test_legal_comments_and_minor_api_version(self):
        metadata, _ = inspect_plugin(plugin(self.root/'test.jar'))
        self.assertEqual(metadata['plugin_main'], 'example.Main')
        self.assertEqual(metadata['api_version'], '1.20.5')

    def test_quoted_hash_and_nested_fields(self):
        from pluginmatrix.preflight import _yaml_value
        self.assertEqual(_yaml_value("version: '1#2' # note\n", 'version'), '1#2')
        self.assertEqual(_yaml_value('commands:\n  main: bad\nmain: good\n', 'main'), 'good')

    def test_bad_compression_produces_report(self):
        jar = plugin(self.root/'bad.jar')
        data = bytearray(jar.read_bytes())
        for signature, offset in [(b'PK\x03\x04', 8), (b'PK\x01\x02', 10)]:
            cursor = 0
            while (cursor := data.find(signature, cursor)) >= 0:
                struct.pack_into('<H', data, cursor + offset, 99)
                cursor += 4
        jar.write_bytes(data)
        report = self.root/'report.json'
        code = main(['test', '--plugin', str(jar), '--paper', '1.20.1', '--java', '17',
                     '--work-dir', str(self.root/'runs'), '--report', str(report)])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(report.read_text())['result'], 'ENVIRONMENT_INVALID')

    def test_duplicate_filenames_names_and_probe_are_rejected_before_download(self):
        target = plugin(self.root/'target/plugin.jar')
        for filename, name in [('plugin.jar', 'Other'), ('PLUGIN.jar', 'Other'),
                               ('other.jar', 'Example'), ('probe.jar', 'PluginMatrixRuntimeProbe')]:
            with self.subTest(filename=filename, name=name):
                dep = plugin(self.root/'dep'/filename, name)
                with patch('pluginmatrix.runtime.ensure_paper') as download:
                    result = verify(target, '1.20.1', '17', self.root/'runs', self.root/'cache', 2, 1, [dep])
                self.assertEqual(result.result, 'ENVIRONMENT_INVALID')
                self.assertIn('conflicts', result.reason)
                download.assert_not_called()

    def test_unrelated_errors_and_name_substrings_do_not_fail_target(self):
        evidence = RuntimeEvidence('Example', 'example.jar')
        evidence.observe_line('Enabling Example v1.0', 0)
        for line in ['[Other] java.io.IOException: optional integration unavailable',
                     'UnknownDependencyException: Vault for Other',
                     'Error occurred while enabling ExampleExtra v1.0']:
            evidence.observe_line(line, .1)
        evidence.observe_line('Done (1s)!', .2)
        evidence.observe_probe(dict(target_present=True, target_enabled=True, target_name='Example', target_version='1.0'), .3)
        evidence.observation_complete = True
        self.assertEqual(evidence.verdict(True, False)[0], 'PASS')

    def test_probe_wrong_identity_and_invalid_shapes(self):
        evidence = RuntimeEvidence('Example', require_direct_runtime=True, expected_version='1.0')
        evidence.observe_line('Enabling Example v1.0', 0)
        evidence.observe_line('Done (1s)!', .1)
        evidence.observe_probe(dict(target_present=True, target_enabled=True, target_name='Example', target_version='2.0'), .2)
        self.assertEqual(evidence.verdict(True, False)[0], 'UNKNOWN_FAILURE')
        for value in [[], None, {'probe': 'pluginmatrix', 'target_enabled': 'false'}]:
            path = self.root/'probe.json'
            path.write_text(json.dumps(value))
            self.assertIsNone(read_probe_evidence(path))

    def test_invalid_bytes_preserved_and_late_disable_is_observed(self):
        payload = dict(probe='pluginmatrix', target_present=True, target_enabled=True, target_name='Example', target_version='1.0')
        code = (probe_writer() + "\nimport os,time,pathlib; print('Done (1s)!',flush=True); "
                "time.sleep(.1); os.write(1,b'\\xff\\n'); time.sleep(.2); "
                "print('Disabling Example v1.0',flush=True); time.sleep(10)")
        result = self.process(code, stability=.5)
        self.assertEqual(result.evidence.verdict(result.exit_code is None, result.timed_out)[0], 'PLUGIN_DISABLED')
        self.assertIn(b'\xff', (self.root/'server.log').read_bytes())
        self.assertTrue(result.evidence.observation_complete)

    def test_zero_window_is_rejected_before_start(self):
        with patch('pluginmatrix.runtime.start_process') as start:
            with self.assertRaisesRegex(ValueError, 'positive'):
                self.process('raise SystemExit(0)', stability=0)
            start.assert_not_called()
        target = plugin(self.root/'target.jar')
        with patch('pluginmatrix.cli.verify') as verifier:
            self.assertEqual(main(['test','--plugin',str(target),'--paper','1.20.1','--java','17','--stability-window','0']), 2)
            verifier.assert_not_called()

    def test_stale_probe_cannot_pass(self):
        payload = dict(probe='pluginmatrix', sequence=1, target_present=True, target_enabled=True, target_name='Example', target_version='1.0')
        result = self.process(one_probe() + "print('Done (1s)!',flush=True); time.sleep(10)",
                              stability=2.2, expected_version='1.0')
        self.assertEqual(result.evidence.verdict(True, False)[0], 'UNKNOWN_FAILURE')

    def test_child_retaining_stdout_does_not_hold_runner_open(self):
        marker = self.root/'child-survived'
        child = f"import time,pathlib; time.sleep(1); pathlib.Path({str(marker)!r}).write_text('alive')"
        # The parent exits first; descendants must remain owned by the job/process group.
        code = f"import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',{child!r}]); time.sleep(.1)"
        started = time.monotonic()
        result = self.process(code, timeout=.4)
        self.assertLess(time.monotonic() - started, 3)
        self.assertNotEqual(result.evidence.verdict(False, False)[0], 'PASS')
        time.sleep(1.1)
        self.assertFalse(marker.exists())

    def config(self, target, report):
        return MatrixConfig(self.root/'config.json', target,
                            (MatrixEnvironment('1.20.1','17'), MatrixEnvironment('1.20.4','17')),
                            self.root/'runs', self.root/'cache', report)

    def test_report_input_collision_never_changes_input(self):
        target = plugin(self.root/'plugin.jar')
        original = target.read_bytes()
        with self.assertRaises(ValueError):
            validate_matrix_preconditions(self.config(target, target))
        self.assertEqual(main(['test','--plugin',str(target),'--report',str(target),'--paper','1.20.1','--java','17']), 2)
        self.assertEqual(original, target.read_bytes())
        alias = self.root/'hardlink.json'
        os.link(target, alias)
        with self.assertRaises(ValueError):
            protect_inputs(alias, [target])

    def test_runtime_report_cannot_overwrite_paper_or_server_log(self):
        target = plugin(self.root/'plugin.jar')
        paper = self.root/'paper.jar'
        paper.write_bytes(b'paper')
        result = VerificationResult(
            metadata={'plugin_jar': str(target), 'paper_jar': str(paper), 'dependencies': []},
            log_path=str(self.root/'server.log'),
        )
        Path(result.log_path).write_text('evidence', encoding='utf-8')
        with self.assertRaises(ValueError):
            from pluginmatrix.runtime import write_report
            write_report(result, paper)
        with self.assertRaises(ValueError):
            from pluginmatrix.runtime import write_report
            write_report(result, Path(result.log_path))

    def test_paper_runtime_cache_symlink_is_rejected(self):
        from pluginmatrix.runtime import _seed_paper_runtime
        cache = self.root / 'cache'
        cache.mkdir()
        (cache / 'libraries').mkdir()
        outside = self.root / 'outside'
        outside.mkdir()
        try:
            (cache / 'libraries' / 'escape').symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            if os.name != 'nt':
                raise
            self.skipTest('symlink creation is unavailable')
        with self.assertRaises(ValueError):
            _seed_paper_runtime(self.root / 'server', cache)

    def test_report_write_failure_keeps_following_environment_and_logs(self):
        config = self.config(plugin(self.root/'plugin.jar'), self.root/'matrix.json')
        calls = []
        def verifier(**kwargs):
            calls.append(kwargs)
            directory = self.root/f'run-{len(calls)}'
            directory.mkdir()
            (directory/'server.log').write_text('evidence')
            if len(calls) == 1:
                (directory/'result.json').mkdir()
            return VerificationResult(result='PASS', workdir=str(directory), log_path=str(directory/'server.log'))
        report = run_matrix(config, verifier=verifier)
        self.assertEqual(len(calls), 2)
        self.assertEqual(matrix_exit_code(report), 3)
        self.assertEqual(report['environments'][0]['failure_stage'], 'report')
        self.assertTrue(report['environments'][0]['artifact_availability']['server_log'])
        self.assertEqual(report['environments'][1]['verdict'], 'PASS')

    def test_matrix_report_inside_runtime_output_is_rejected(self):
        target = plugin(self.root/'plugin.jar')
        config = self.config(target, self.root/'runs'/'matrix.json')
        with self.assertRaises(Exception) as raised:
            validate_matrix_preconditions(config)
        self.assertIn('inside', str(raised.exception))

    def test_atomic_report_failure_keeps_previous_report(self):
        path = self.root/'report.json'
        path.write_text('previous')
        with patch('pluginmatrix.files.os.replace', side_effect=OSError('disk error')):
            with self.assertRaises(OSError):
                atomic_json(path, {'new': True})
        self.assertEqual(path.read_text(), 'previous')
        self.assertEqual(list(self.root.glob('.pluginmatrix-*.tmp')), [])
