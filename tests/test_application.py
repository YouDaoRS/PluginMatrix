import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pluginmatrix import application
from pluginmatrix.cli import main
from pluginmatrix.matrix import load_matrix_config, MatrixConfigError
from pluginmatrix.providers import ServerSpec
from pluginmatrix.reports import render_html_report, load_report
from pluginmatrix.control import RunControl
from test_regressions import plugin


class ApplicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.plugin = plugin(self.root/'plugin.jar')

    def config(self, servers=None):
        path = self.root/'matrix.json'
        application.init_configuration(path, plugin=self.plugin, java='17', servers=servers or [ServerSpec('paper', '1.20.1')])
        return path

    def invoke(self, args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(args)
        return code, output.getvalue()

    def test_init_supports_all_providers_and_roundtrips_relative_paths(self):
        local = plugin(self.root/'server.jar', 'Server')
        for kind in ('paper', 'purpur', 'folia', 'local'):
            args = ['init', str(self.root/f'{kind}.json'), '--plugin', str(self.plugin), '--server', kind,
                    '--minecraft', '1.21.4', '--java', '21']
            if kind == 'local':
                args += ['--server-jar', str(local), '--server-name', 'Mine', '--runtime', 'paperclip']
            with patch('pluginmatrix.cli.sys.stdin.isatty', return_value=False):
                code, _ = self.invoke(args)
            self.assertEqual(code, 0)
            config = load_matrix_config(self.root/f'{kind}.json')
            self.assertTrue(os.path.samefile(config.plugin, self.plugin))
            self.assertEqual(config.environments[0].server_spec.type, kind)
            self.assertEqual(config.max_parallel, 1)

    def test_init_refuses_existing_file_and_force_never_overwrites_input_alias(self):
        path = self.config()
        original = path.read_bytes()
        with self.assertRaises(FileExistsError):
            self.config()
        self.assertEqual(path.read_bytes(), original)
        alias = self.root/'alias.json'; os.link(self.plugin, alias)
        with self.assertRaises(ValueError):
            application.init_configuration(alias, plugin=self.plugin, java='17', servers=[ServerSpec('paper', '1.20.1')], force=True)
        application.init_configuration(path, plugin=self.plugin, java='17', servers=[ServerSpec('purpur', '1.20.1')], force=True)
        self.assertEqual(load_matrix_config(path).environments[0].server_spec.type, 'purpur')

    def test_validate_is_offline_and_network_mode_does_not_download(self):
        path = self.config()
        with patch('pluginmatrix.matrix.resolve_java'):
            # Inject at service boundary: parser and local safety checks still run.
            from pluginmatrix.matrix import validate_matrix_preconditions
            preflight = validate_matrix_preconditions(load_matrix_config(path), lambda _: ('java', '17.0.1'), lambda _: 'javac')
        with patch('pluginmatrix.application.validate_matrix_preconditions', return_value=preflight), patch('pluginmatrix.providers.read_json') as network, patch('pluginmatrix.runtime.start_process') as start:
            result = application.validate_configuration(path)
            self.assertTrue(result['valid'])
            network.assert_not_called(); start.assert_not_called()
        from test_providers import build
        with patch('pluginmatrix.application.validate_matrix_preconditions', return_value=preflight), patch('pluginmatrix.providers.read_json', return_value=[build()]), patch('pluginmatrix.artifacts.ensure_download') as download:
            result = application.validate_configuration(path, network=True)
            self.assertTrue(result['valid'])
            self.assertEqual(result['resolved'][0]['resolved_build'], 10)
            download.assert_not_called()

    def test_providers_validate_and_doctor_emit_machine_readable_json(self):
        code, output = self.invoke(['providers', '--json'])
        self.assertEqual(code, 0)
        self.assertEqual(len(json.loads(output)['providers']), 4)
        code, output = self.invoke(['validate', str(self.root/'missing.json'), '--json'])
        self.assertEqual(code, 2)
        self.assertFalse(json.loads(output)['valid'])
        with patch('pluginmatrix.application.resolve_java', side_effect=ValueError('missing JDK')):
            code, output = self.invoke(['doctor', '--offline', '--json', '--directory', str(self.root/'doctor')])
        value = json.loads(output)
        self.assertEqual(code, 2)
        self.assertEqual({c['level'] for c in value['checks']}, {'required', 'warning', 'informational'})

    def test_legacy_config_and_explicit_paper_are_semantically_equal(self):
        path = self.root/'legacy.json'
        path.write_text(json.dumps({'plugin': str(self.plugin), 'environments': [{'paper': '1.20.1', 'paper_build': 196, 'java': 17}]}))
        legacy = load_matrix_config(path)
        self.assertEqual(legacy.environments[0].server_spec, ServerSpec('paper', '1.20.1', 196))
        self.assertEqual(legacy.environments[0].to_dict(), {'paper': '1.20.1', 'paper_build': 196, 'java': '17'})
        raw = json.loads(path.read_text()); raw['environments'][0]['server'] = {'type': 'paper', 'version': '1.20.1'}
        path.write_text(json.dumps(raw))
        with self.assertRaisesRegex(MatrixConfigError, 'cannot be combined'):
            load_matrix_config(path)

    def test_html_uses_saved_verdict_escapes_injection_and_links_relative_artifacts(self):
        source = self.root/'report.json'; target = self.root/'report.html'
        report = {'plugin': {'plugin_name': '<img src=x onerror=alert(1)>'}, 'summary': {'passed': 99},
                  'environments': [{'id': '<script>alert(1)</script>', 'verdict': 'PLUGIN_DISABLED', 'failure_stage': 'plugin_runtime',
                                    'reason': '"><script>evil()</script>', 'metadata': {'server': {'regionized_runtime': True, 'server_type': 'folia'}},
                                    'artifacts': {'server_log': str(self.root/'runs/a b/server.log')},
                                    'evidence': [{'detail': '</pre><script>bad()</script>'}]}]}
        source.write_text(json.dumps(report))
        render_html_report(source, target)
        html = target.read_text()
        self.assertIn('PLUGIN_DISABLED', html)
        self.assertIn('99', html)
        self.assertNotIn('<script>', html)
        self.assertNotIn('<img ', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('./runs/a%20b/server.log', html)
        self.assertIn('cross-region safety', html)
        self.assertEqual(load_report(source), report)

    def test_html_cannot_overwrite_source_plugin_local_jar_or_raw_log(self):
        local = plugin(self.root/'server.jar', 'Server')
        rawlog = self.root/'server.log'; rawlog.write_bytes(b'raw')
        source = self.root/'result.json'
        source.write_text(json.dumps({'result': 'PASS', 'metadata': {'plugin_jar': str(self.plugin), 'server': {'jar': str(local)}},
                                      'log_path': str(rawlog)}))
        for destination in (source, self.plugin, local, rawlog):
            original = destination.read_bytes()
            with self.assertRaises(ValueError):
                render_html_report(source, destination)
            self.assertEqual(destination.read_bytes(), original)

    def test_html_rejects_malformed_nested_report_without_partial_output(self):
        source = self.root/'result.json'
        destination = self.root/'result.html'
        malformed = [
            {'result': 'PASS', 'metadata': 'not-an-object'},
            {'environments': [{'id': 'paper', 'metadata': {'server': []}}]},
            {'environments': [{'id': 'paper', 'artifacts': []}]},
            {'environments': [], 'config': {'environments': [{'server': []}]}}
        ]
        for report in malformed:
            with self.subTest(report=report):
                source.write_text(json.dumps(report))
                with self.assertRaisesRegex(ValueError, 'invalid report'):
                    render_html_report(source, destination)
                self.assertFalse(destination.exists())

        source.write_text(json.dumps(malformed[0]))
        code, output = self.invoke(['report', str(source), '--html', str(destination)])
        self.assertEqual(code, 2)
        self.assertIn('invalid report metadata', output)

    def test_terminal_control_sequences_are_escaped(self):
        from pluginmatrix.terminal import safe_text
        self.assertEqual(safe_text('a\x1b[31m\n\u202eb'), 'a\\u001b[31m\\u000a\\u202eb')

    def test_invalid_plugin_with_valid_java_returns_configuration_error(self):
        path = self.config()
        self.plugin.write_bytes(b'invalid')
        from pluginmatrix.matrix import validate_matrix_preconditions
        with self.assertRaisesRegex(MatrixConfigError, 'plugin JAR failed preflight'):
            validate_matrix_preconditions(load_matrix_config(path), lambda _: ('java', '17.0.1'), lambda _: 'javac')

    def test_progress_observer_failures_do_not_change_run_control(self):
        events = []
        control = RunControl(events.append)
        control.emit('matrix_started', total=1, secret='ignored', logs='ignored')
        self.assertEqual(events[0].to_dict()['data'], {'total': 1})
        control = RunControl(lambda e: (_ for _ in ()).throw(ValueError('GUI error')))
        control.emit('matrix_started')
        self.assertFalse(control.cancelled)
        self.assertEqual(control.observer_errors, 1)
