"""Independent critical-path regressions; all artifacts and processes are local."""
import json
import os
import stat
import sys
import tempfile
import threading
import time
import subprocess
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import Mock, patch

from pluginmatrix.control import RunControl
from pluginmatrix.matrix import MatrixConfig, MatrixEnvironment, validate_matrix_preconditions
from pluginmatrix.matrix import run_matrix
from pluginmatrix.model import VerificationResult
from pluginmatrix.processes import stop_process
from pluginmatrix.providers import ServerSpec
from pluginmatrix.reports import render_html_report
from pluginmatrix.runtime import _seed_paper_runtime, run_server_process, verify
from pluginmatrix.scheduler import schedule
from pluginmatrix.locking import file_lock
from pluginmatrix.files import sha256_file
from pluginmatrix.artifacts import ensure_download, ProviderError
from pluginmatrix.providers import FILL_HOSTS
from probe_support import probe_writer
from test_regressions import plugin


class CriticalPathTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_fatal_worker_cancels_siblings_before_waiting_for_all(self):
        control = RunControl()
        sibling_started = threading.Event()
        observed_cancel = []

        def worker(index, item):
            if index == 0:
                self.assertTrue(sibling_started.wait(2))
                raise RuntimeError('fatal scheduler worker')
            sibling_started.set()
            # The deadline makes reverting the fix fail without hanging the suite.
            observed_cancel.append(control._cancelled.wait(1))

        with self.assertRaisesRegex(RuntimeError, 'fatal scheduler worker'):
            schedule(range(2), worker, 2, control)
        self.assertEqual(observed_cancel, [True])

    def test_repeated_interrupts_during_cleanup_drain_real_process(self):
        processes = []
        attempts = []
        from pluginmatrix.processes import start_process

        def start(*args):
            process = start_process(*args)
            processes.append(process)
            return process

        def stop(process):
            attempts.append(process)
            if len(attempts) <= 2:
                raise KeyboardInterrupt
            stop_process(process)

        interrupted = False
        try:
            with patch('pluginmatrix.runtime.start_process', side_effect=start), patch('pluginmatrix.runtime._stop_process', side_effect=stop):
                try:
                    outcome = run_server_process([sys.executable, '-c', 'import time; time.sleep(30)'],
                                                 self.root, self.root/'server.log', 'Example', None, .15, .1)
                except KeyboardInterrupt:
                    interrupted = True
            self.assertFalse(interrupted, 'cleanup must finish despite repeated Ctrl+C')
            self.assertEqual(outcome.evidence.verdict(True, True)[0], 'CANCELLED')
            self.assertIsNotNone(processes[0].poll())
            self.assertEqual(len(attempts), 3)
        finally:
            for process in processes:
                if process.poll() is None or getattr(process, '_pluginmatrix_job', None):
                    stop_process(process)

    def test_windows_job_ownership_survives_interrupted_drain(self):
        kernel = Mock()
        kernel.QueryInformationJobObject.side_effect = [KeyboardInterrupt, True]
        process = Mock()
        process._pluginmatrix_job = (kernel, 123)
        with self.assertRaises(KeyboardInterrupt):
            stop_process(process)
        self.assertEqual(process._pluginmatrix_job, (kernel, 123))
        kernel.CloseHandle.assert_not_called()
        stop_process(process)
        kernel.CloseHandle.assert_called_once_with(123)
        self.assertIsNone(process._pluginmatrix_job)

    def test_legacy_jar_override_cannot_bypass_explicit_local_contract(self):
        target = plugin(self.root/'target.jar')
        jar = plugin(self.root/'input.jar', 'Server')
        original = jar.read_bytes()
        with patch('pluginmatrix.runtime.resolve_java', return_value=('java', '17.0.1')) as java, patch('pluginmatrix.runtime.build_probe_plugin', side_effect=RuntimeError('probe stopped')) as probe:
            result = verify(target, '1.20.1', '17', self.root/'runs', self.root/'cache', 2, 1,
                            paper_jar=jar, paper_metadata={'official': True, 'resolved_build': '../../outside'})
        self.assertEqual(result.result, 'ENVIRONMENT_INVALID')
        self.assertIn('server.type=local', result.reason)
        java.assert_not_called()
        probe.assert_not_called()
        self.assertEqual(jar.read_bytes(), original)

    def test_html_relative_inputs_and_artifacts_use_report_directory(self):
        directory = self.root/'saved'; directory.mkdir()
        source = directory/'result.json'
        for field, name in [('plugin', 'target.jar'), ('server', 'server.jar'), ('log', 'server.log')]:
            with self.subTest(field=field):
                target = directory/name; target.write_bytes(b'original evidence')
                report = {'result': 'PASS', 'metadata': {}}
                if field == 'plugin':
                    report['metadata']['plugin_jar'] = name
                elif field == 'server':
                    report['metadata']['server'] = {'jar': name}
                else:
                    report['log_path'] = name
                source.write_text(json.dumps(report))
                with self.assertRaises(ValueError):
                    render_html_report(source, target)
                self.assertEqual(target.read_bytes(), b'original evidence')

    def test_html_cannot_overwrite_other_matrix_report_reference(self):
        source = self.root/'saved.json'
        target = self.root/'matrix.json'; target.write_bytes(b'original JSON')
        source.write_text(json.dumps({'environments': [], 'config': {'options': {'report': 'matrix.json'}},
                                     'artifacts': {'matrix_report': 'matrix.json'}}))
        with self.assertRaises(ValueError):
            render_html_report(source, target)
        self.assertEqual(target.read_bytes(), b'original JSON')

    def test_html_relative_runtime_root_cannot_receive_output(self):
        directory = self.root/'saved'; directory.mkdir()
        source = directory/'result.json'
        source.write_text(json.dumps({'result': 'PASS', 'workdir': 'runs/run-1'}))
        destination = directory/'runs/run-1/server/plugins/probe.json'
        with self.assertRaises(ValueError):
            render_html_report(source, destination)
        self.assertFalse(destination.exists())

    def test_shared_html_is_locked_before_any_matrix_worker_starts(self):
        target = plugin(self.root/'target.jar')
        html = self.root/'shared.html'; html.write_text('existing report')
        config = MatrixConfig(self.root/'config.json', target, (MatrixEnvironment('1.20.1', '17'),),
                              self.root/'runs', self.root/'cache', self.root/'matrix.json', html_path=html)
        verifier = Mock(return_value=VerificationResult(result='PASS'))
        with file_lock(html.with_name(html.name + '.lock')):
            with self.assertRaises(TimeoutError):
                run_matrix(config, verifier=verifier)
        verifier.assert_not_called()
        self.assertEqual(html.read_text(), 'existing report')
        self.assertFalse(config.report_path.exists())

    def test_reports_cannot_replace_persistent_lock_files(self):
        source = self.root/'result.json'
        source.write_text(json.dumps({'result': 'PASS'}))
        lock = self.root/'another.json.lock'; lock.write_bytes(b'0')
        with self.assertRaisesRegex(ValueError, 'lock'):
            render_html_report(source, lock)
        self.assertEqual(lock.read_bytes(), b'0')

    def test_programmatic_relative_paths_are_saved_as_absolute(self):
        config = MatrixConfig(Path('config.json'), Path('target.jar'), (), Path('runs'), Path('cache'), Path('matrix.json'))
        saved = config.to_dict()
        self.assertTrue(Path(saved['plugin']).is_absolute())
        for key in ('report', 'work_dir', 'cache_dir'):
            self.assertTrue(Path(saved['options'][key]).is_absolute())

    def test_folia_dependency_declaration_is_checked_by_offline_preflight(self):
        target = plugin(self.root/'target.jar', extra='folia-supported: true')
        dependency = plugin(self.root/'dependency.jar', 'Dependency')
        config = MatrixConfig(self.root/'config.json', target,
                              (MatrixEnvironment('1.21.4', '21', server=ServerSpec('folia', '1.21.4')),),
                              self.root/'runs', self.root/'cache', self.root/'report.json', dependencies=(dependency,))
        with self.assertRaisesRegex(ValueError, 'Dependency.*Folia'):
            validate_matrix_preconditions(config, lambda _: ('java', '21.0.1'), lambda _: 'javac')

    def test_nonregular_bootstrap_cache_entry_is_rejected_before_copy(self):
        cache = self.root/'cache'
        directory = cache/'libraries'; directory.mkdir(parents=True)
        fifo = directory/'pipe'; fifo.write_bytes(b'placeholder')
        original_stat = Path.stat

        def entry_stat(path, *args, **kwargs):
            if path == fifo:
                return SimpleNamespace(st_mode=stat.S_IFIFO | 0o600, st_file_attributes=0)
            return original_stat(path, *args, **kwargs)

        with patch.object(Path, 'stat', entry_stat), patch('pluginmatrix.runtime.shutil.copytree') as copy:
            with self.assertRaisesRegex(ValueError, 'regular'):
                _seed_paper_runtime(self.root/'server', cache)
            copy.assert_not_called()

    def test_nonregular_checksum_receipt_is_rejected_before_read(self):
        cache = self.root/'cache'; cache.mkdir()
        artifact = cache/'server.jar'; artifact.write_bytes(b'fixture')
        receipt = cache/'server.jar.sha256.json'; receipt.write_text('{}')
        original = Path.is_file
        with patch.object(Path, 'is_file', lambda path: False if path == receipt else original(path)), \
             patch.object(Path, 'read_text', return_value='{}') as read:
            with self.assertRaisesRegex(ProviderError, 'regular'):
                ensure_download(cache, artifact.name, 'https://fill-data.papermc.io/server.jar',
                                'sha256', sha256_file(artifact), FILL_HOSTS)
            read.assert_not_called()

    def test_process_lock_exclusion_and_release_after_holder_exit(self):
        lock = self.root/'cache.lock'
        script = ('import time; from pathlib import Path; from pluginmatrix.locking import file_lock; '
                  f'lock = file_lock(Path({str(lock)!r})); lock.__enter__(); print("held", flush=True); time.sleep(30)')
        process = subprocess.Popen([sys.executable, '-u', '-c', script], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            # communicate would wait for exit; use a reader with a bounded join.
            lines = []
            reader = threading.Thread(target=lambda: lines.append(process.stdout.readline()), daemon=True)
            reader.start(); reader.join(5)
            self.assertEqual(lines, [b'held\r\n' if os.name == 'nt' else b'held\n'])
            with self.assertRaises(TimeoutError):
                with file_lock(lock, timeout=0):
                    self.fail('another process owns the lock')
        finally:
            process.kill(); process.communicate(timeout=5)
        with file_lock(lock, timeout=0):
            self.assertTrue(lock.is_file())

    def test_all_providers_share_live_identity_and_failure_verification(self):
        target = plugin(self.root/'target.jar', extra='folia-supported: true')
        artifact = plugin(self.root/'server.jar', 'Server')
        from pluginmatrix.providers import get_provider
        for kind in ('paper', 'purpur', 'folia', 'local'):
            spec = ServerSpec(kind, '1.21.4', **({'jar': artifact, 'name': 'Local', 'runtime': 'paperclip'} if kind == 'local' else {}))
            provider = get_provider(kind)
            info = {**provider.requested_metadata(spec), 'jar_sha256': sha256_file(artifact), 'resolved_build': 1}
            for scenario, expected in [('success', 'PASS'), ('wrong_source', 'UNKNOWN_FAILURE'),
                                       ('disabled', 'PLUGIN_DISABLED'), ('enable_failure', 'PLUGIN_ENABLE_FAILED'),
                                       ('startup_failure', 'SERVER_START_FAILED'), ('timeout', 'SERVER_START_TIMEOUT')]:
                with self.subTest(provider=kind, scenario=scenario):
                    def build_probe(server_jar, plugins, name, evidence, java, major, **kwargs):
                        origin = artifact if scenario == 'wrong_source' else plugins/target.name
                        code = probe_writer(path=str(evidence), run_id=kwargs['run_id'], target_source=str(origin.resolve()),
                                            target_ever_disabled=scenario == 'disabled')
                        if scenario == 'startup_failure':
                            code += "\nprint('Error during server startup', flush=True); raise SystemExit(1)"
                        elif scenario == 'timeout':
                            code += '\ntime.sleep(30)'
                        else:
                            if scenario == 'enable_failure':
                                code += "\nprint('Error occurred while enabling Example v1.0', flush=True)"
                            code += "\nprint('Enabling Example v1.0', flush=True); print('Done (1s)!', flush=True); time.sleep(30)"
                        (plugins.parent/'fake.py').write_text(code)

                    with patch('pluginmatrix.runtime.resolve_java', return_value=(sys.executable, '21.0.1')), \
                         patch('pluginmatrix.runtime.ensure_paper', return_value=(artifact, info)), \
                         patch.object(provider, 'prepare', return_value=(artifact, info)), \
                         patch.object(provider, 'command', return_value=[sys.executable, '-u', 'fake.py']), \
                         patch('pluginmatrix.runtime.build_probe_plugin', side_effect=build_probe):
                        result = verify(target, spec.version, '21', self.root/'runs', self.root/'cache', .4, .15, server=spec)
                    self.assertEqual(result.result, expected, result.reason)
                    if expected == 'PASS':
                        events = {event.kind: event for event in result.evidence}
                        self.assertGreaterEqual(events['stability_window_completed'].timestamp - events['stability_window_started'].timestamp, .15)
                        self.assertEqual(result.metadata['server']['official'], kind != 'local')
                        self.assertEqual(Path(result.metadata['runtime_probe']['target_source']).name, target.name)

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'native FIFO requires POSIX')
    def test_native_fifo_cache_cannot_block_worker(self):
        cache = self.root/'cache'; (cache/'libraries').mkdir(parents=True)
        os.mkfifo(cache/'libraries/pipe')
        # A separate process bounds this regression even if the safety check is reverted.
        import subprocess
        script = 'from pathlib import Path; from pluginmatrix.runtime import _seed_paper_runtime; _seed_paper_runtime(Path(%r), Path(%r))' % (str(self.root/'server'), str(cache))
        result = subprocess.run([sys.executable, '-c', script], capture_output=True, timeout=3)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'regular', result.stderr)
