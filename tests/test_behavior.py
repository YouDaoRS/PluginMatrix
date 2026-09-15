"""Behavior verdict, evidence and real process lifecycle regressions (offline)."""
import json
import os
import sys
import tempfile
import textwrap
import time
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from pluginmatrix.behavior import (parse_behavior, initial_behavior, assert_observation, validate_response,
                                   REQUEST_FILE, RESPONSE_FILE)
from pluginmatrix.control import RunControl
from pluginmatrix.model import VerificationResult
from pluginmatrix.runtime import run_server_process
from pluginmatrix.files import read_evidence_bytes
from pluginmatrix.matrix import load_matrix_config, run_matrix, matrix_exit_code
from pluginmatrix.reports import html_document
from pluginmatrix.application import run_single
from pluginmatrix.providers import ServerSpec


def plan(*checks, timeout=10):
    return parse_behavior({'schema': 1, 'timeout': timeout, 'checks': list(checks)})


def command(ident='command', **changes):
    return {'id': ident, 'type': 'console_command', 'name': 'example:check', **changes}


class BehaviorModelTests(unittest.TestCase):
    def test_cli_behavior_failure_returns_one_while_runtime_stays_pass(self):
        from pluginmatrix.cli import main
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root/'behavior.json'
            config.write_text(plan(command()).canonical)
            result = VerificationResult(result='PASS', report_path=str(root/'report.json'))
            result.behavior = initial_behavior(plan(command()))
            result.behavior.update(verdict='FAIL')
            with patch('pluginmatrix.cli.verify', return_value=result) as verify, redirect_stdout(StringIO()):
                code = main(['test', '--plugin', str(root/'plugin.jar'), '--paper', '1.20.1', '--java', '17',
                             '--behavior', str(config), '--report', str(root/'report.json'),
                             '--work-dir', str(root/'runs'), '--cache-dir', str(root/'cache')])
            self.assertEqual(code, 1)
            self.assertEqual(result.result, 'PASS')
            self.assertEqual(verify.call_args.kwargs['behavior'].digest, plan(command()).digest)
            self.assertEqual(verify.call_args.kwargs['behavior_source'], config)

    def test_matrix_config_roundtrip_and_parallel_results_preserve_both_verdicts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plugin = root/'Example.jar'
            plugin.write_bytes(b'fixture')
            config_path = root/'matrix.json'
            config_path.write_text(json.dumps({'plugin': 'Example.jar', 'environments': [
                {'paper': '1.20.1', 'java': '17'}, {'paper': '1.20.4', 'java': '17'}],
                'behavior': {'schema': 1, 'checks': [command()]}, 'options': {'max_parallel': 2}}))
            config = load_matrix_config(config_path)
            self.assertEqual(config.behavior.to_dict(), config.to_dict()['behavior'])
            def verify(**options):
                result = VerificationResult(result='PASS')
                result.behavior = initial_behavior(options['behavior'])
                result.behavior.update(verdict='FAIL' if options['environment_index'] == 0 else 'PASS')
                return result
            report = run_matrix(config, verifier=verify)
            self.assertEqual([e['behavior']['verdict'] for e in report['environments']], ['FAIL', 'PASS'])
            self.assertEqual([e['runtime_verdict'] for e in report['environments']], ['PASS', 'PASS'])
            self.assertEqual(report['summary'], {'total': 2, 'passed': 1, 'failed': 1})
            self.assertEqual(matrix_exit_code(report), 1)
            self.assertIn('Behavior verdict', html_document(report, config.report_path, root/'report.html'))

    def test_behavior_source_is_protected_from_report_and_lock_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'behavior.json'
            source.write_text('{}')
            options = dict(plugin=root/'plugin.jar', server=ServerSpec('paper', '1.20.1'), java='17',
                           work_root=root/'runs', cache_dir=root/'cache', behavior_source=source)
            with patch('pluginmatrix.application._verify') as verifier:
                with self.assertRaises(ValueError):
                    run_single(**options, report_path=source)
                verifier.assert_not_called()
            self.assertEqual(source.read_text(), '{}')

    def test_web_import_cannot_silently_drop_requested_behavior(self):
        from pluginmatrix.web import WebApplication, WebError
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'plugin.jar').write_bytes(b'fixture')
            path = root/'matrix.json'
            path.write_text(json.dumps({'plugin': 'plugin.jar', 'environments': [{'paper': '1.20.1', 'java': 17}],
                                        'behavior': {'schema': 1, 'checks': [command()]}}))
            app = WebApplication(root/'web', root/'cache')
            try:
                with self.assertRaisesRegex(WebError, 'CLI or application API'):
                    app.import_configuration(str(path))
            finally:
                app.close()

    def test_evidence_rejects_hardlinks_and_oversized_files(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'evidence'
            path.write_bytes(b'{}')
            self.assertEqual(read_evidence_bytes(path, 2), b'{}')
            with self.assertRaises(ValueError):
                read_evidence_bytes(path, 1)
            alias = path.with_name('alias')
            os.link(path, alias)
            with self.assertRaises(ValueError):
                read_evidence_bytes(path, 100)

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'POSIX FIFO')
    def test_evidence_fifo_never_blocks_the_deadline(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'pipe'
            os.mkfifo(path)
            with self.assertRaises(ValueError):
                read_evidence_bytes(path, 100)

    def test_strict_bounded_config_and_immutable_plan(self):
        good = {'schema': 1, 'checks': [command(args=['hello'])]}
        frozen = parse_behavior(good)
        good['checks'][0]['args'].append('changed')
        self.assertEqual(frozen.to_dict()['checks'][0]['args'], ['hello'])
        for bad in [[], {}, {'schema': True, 'checks': [command()]},
                    {'schema': 1, 'checks': []}, {'schema': 1, 'checks': [command()] * 65},
                    {'schema': 1, 'checks': [command(), command()]},
                    {'schema': 1, 'checks': [command(type='script')]},
                    {'schema': 1, 'checks': [command(timeout=float('nan'))]},
                    {'schema': 1, 'checks': [command(expect='true')]},
                    {'schema': 1, 'checks': [command(name='stop\nreload')]},
                    {'schema': 1, 'checks': [command(args=['ok\nstop'])]},
                    {'schema': 1, 'checks': [command(script='evil')]},
                    {'schema': 1, 'checks': [command()], 'timeout': 301},
                    {'schema': 1, 'checks': [{'id': 'w', 'type': 'wait', 'seconds': 5, 'timeout': 5}]}]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                parse_behavior(bad)

    def test_false_is_not_permission_to_run_foreign_command(self):
        check = plan(command(expect=False)).to_dict()['checks'][0]
        self.assertFalse(assert_observation(check, {'registered': True, 'owned': False, 'owner': 'Other'}, 'Example'))
        with self.assertRaises(ValueError):
            assert_observation(check, {'registered': True, 'owned': True, 'owner': 'Other'}, 'Example')
        with self.assertRaises(ValueError):
            assert_observation(check, {'registered': True, 'owned': True, 'owner': 'Example', 'sender': 'CONSOLE', 'returned': 'true'}, 'Example')

    def test_service_requires_target_registration_not_foreign_provider(self):
        check = plan({'id': 's', 'type': 'service_registered', 'name': 'api.Service'}).to_dict()['checks'][0]
        with self.assertRaises(ValueError):
            assert_observation(check, {'registrations': [{'owner': 'Other', 'service': 'api.Service',
                                'implementation': 'other.Impl', 'priority': 'Normal'}]}, 'Example')
        self.assertFalse(assert_observation(check, {'registrations': []}, 'Example'))

    def test_response_binding_and_typed_observations_reject_forged_pass(self):
        config = plan(command())
        check = config.to_dict()['checks'][0]
        request = {'request_id': 'a' * 32, 'index': 0}
        response = {'schema': 1, 'probe': 'pluginmatrix-behavior', 'run_id': 'run', 'plan_sha256': config.digest,
                    **request, 'check_id': 'command', 'type': 'console_command', 'status': 'OK',
                    'completed_at_ms': int(time.time() * 1000),
                    'observation': {'registered': True, 'owned': True, 'owner': 'Example', 'sender': 'CONSOLE', 'returned': True}}
        options = dict(request=request, check=check, plan=config, run_id='run', started_wall=0, target='Example')
        self.assertEqual(validate_response(response, **options)[0], 'PASS')
        for changes in [{'run_id': 'other'}, {'plan_sha256': 'wrong'}, {'request_id': 'old'}, {'index': True},
                        {'check_id': 'other'}, {'schema': True}, {'status': 'PASS'}, {'observation': {'result': 'PASS'}},
                        {'completed_at_ms': 1}, {'completed_at_ms': int(time.time() * 1000) + 9000}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_response({**response, **changes}, **options)

    def test_runtime_and_behavior_are_separate_and_skips_never_pass(self):
        result = VerificationResult(result='PASS')
        self.assertTrue(result.passed)
        for status in ('FAIL', 'ERROR', 'TIMEOUT', 'CANCELLED', 'UNSUPPORTED', 'SKIPPED'):
            result.behavior = {**initial_behavior(plan(command())), 'verdict': status}
            self.assertFalse(result.passed)
            self.assertEqual(result.to_dict()['runtime_verdict'], 'PASS')


def server_script(config, mode):
    """A real child process implements the wire contract; no JVM behavior is simulated in the real Gate."""
    return textwrap.dedent('''
        import json, pathlib, threading, time, os
        root = pathlib.Path('.')
        payload = dict(probe='pluginmatrix', schema=2, run_id='run', target_present=True,
                       target_enabled=True, target_name='Example', target_version='1.0',
                       target_main='example.Main', target_source='', target_ever_disabled=False,
                       sequence=0, emitted_at_ms=0)
        def publish(path, value):
            temporary = path.with_suffix('.tmp')
            temporary.write_text(json.dumps(value))
            try: os.replace(temporary, path)
            except PermissionError: pass
        def evidence():
            while True:
                payload['sequence'] += 1
                payload['emitted_at_ms'] = int(time.time()*1000)
                publish(root/'probe.json', payload)
                time.sleep(.025)
        threading.Thread(target=evidence, daemon=True).start()
        print('[Server thread/INFO]: Done (1s)! For help, type "help"', flush=True)
        handled = set()
        while True:
            request_file = root/REQUEST_FILE
            if request_file.exists():
                request = dict(line.split('=', 1) for line in request_file.read_text().splitlines())
                if request['request_id'] not in handled:
                    handled.add(request['request_id'])
                    index = int(request['index'])
                    check = CHECKS[index]
                    if MODE == 'hang':
                        time.sleep(60)
                    if MODE == 'exit':
                        os._exit(8)
                    if MODE == 'disable':
                        payload['target_enabled'] = False
                        payload['target_ever_disabled'] = True
                    if MODE == 'identity':
                        payload['target_main'] = 'other.Main'
                    response = dict(schema=1, probe='pluginmatrix-behavior', run_id='run', plan_sha256=DIGEST,
                                    request_id=request['request_id'], index=index, check_id=check['id'], type=check['type'],
                                    completed_at_ms=int(time.time()*1000), status='OK',
                                    observation=dict(registered=True, owned=True, owner='Example', sender='CONSOLE', returned=MODE != 'false'))
                    if MODE == 'replay': response['request_id'] = 'old'
                    if MODE == 'malformed': response['observation']['returned'] = 'true'
                    if MODE == 'unsupported': response.update(status='UNSUPPORTED', reason='unsupported API')
                    if MODE == 'exception':
                        print('[Example] Error occurred while enabling Example v1.0', flush=True)
                        response.update(status='ERROR', reason='command exception')
                    publish(root/RESPONSE_FILE, response)
            time.sleep(.025)
    ''').replace('REQUEST_FILE', repr(REQUEST_FILE)).replace('RESPONSE_FILE', repr(RESPONSE_FILE)).replace(
        'CHECKS', repr(config.to_dict()['checks'])).replace('DIGEST', repr(config.digest)).replace('MODE', repr(mode))


class BehaviorProcessTests(unittest.TestCase):
    def run_case(self, mode, config=None, control=None):
        config = config or plan(command(timeout=.8), command('after', timeout=.8))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = run_server_process([sys.executable, '-u', '-c', server_script(config, mode)], root,
                                        root/'server.log', 'Example', 'Example.jar', timeout=4, stability=.12,
                                        probe_path=root/'probe.json', expected_main='example.Main', expected_version='1.0',
                                        run_id='run', behavior=config, control=control)
            self.assertFalse((root/REQUEST_FILE).exists())
            self.assertEqual(result.evidence.verdict(result.exit_code is None, result.timed_out)[0], 'PASS')
            return result.behavior

    def test_pass_requires_fresh_post_check_health_and_independent_assertions(self):
        result = self.run_case('ok')
        self.assertEqual(result['verdict'], 'PASS')
        self.assertEqual(result['post_health']['status'], 'PASS')
        for check in result['checks']:
            self.assertGreater(check['evidence']['final_sample']['sequence'], check['evidence']['start_sequence'])

    def test_false_return_and_exception_do_not_reclassify_runtime(self):
        self.assertEqual(self.run_case('false')['verdict'], 'FAIL')
        self.assertEqual(self.run_case('exception')['verdict'], 'ERROR')

    def test_disabled_identity_exit_and_corrupt_response_cannot_pass(self):
        for mode in ('disable', 'identity', 'exit', 'replay', 'malformed'):
            with self.subTest(mode=mode):
                result = self.run_case(mode)
                self.assertEqual(result['verdict'], 'ERROR')
                self.assertEqual(result['checks'][1]['status'], 'SKIPPED')

    def test_timeout_is_behavior_timeout_and_disarms_request(self):
        result = self.run_case('hang')
        self.assertEqual(result['verdict'], 'TIMEOUT')
        self.assertEqual(result['checks'][1]['status'], 'SKIPPED')

    def test_no_post_command_sample_cannot_pass(self):
        config = plan(command(timeout=.4))
        script = server_script(config, 'ok')
        script = script.replace('while True:\n        payload', "while not (root/'freeze').exists():\n        payload")
        script = script.replace("response = dict(schema=1", "(root/'freeze').touch()\n            time.sleep(.08)\n            response = dict(schema=1")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = run_server_process([sys.executable, '-u', '-c', script], root, root/'server.log', 'Example',
                                        'Example.jar', timeout=2, stability=.1, probe_path=root/'probe.json',
                                        run_id='run', behavior=config)
            self.assertEqual(result.evidence.verdict(True, False)[0], 'PASS')
            self.assertEqual(result.behavior['verdict'], 'TIMEOUT')

    def test_cleanup_failure_still_prevents_runtime_pass_with_behavior_enabled(self):
        from pluginmatrix.runtime import _stop_process
        config = plan(command())
        def cleanup(process):
            _stop_process(process)
            raise OSError('cleanup evidence failure')
        with tempfile.TemporaryDirectory() as directory, patch('pluginmatrix.runtime._stop_process', cleanup):
            root = Path(directory)
            result = run_server_process([sys.executable, '-u', '-c', server_script(config, 'ok')], root,
                                        root/'server.log', 'Example', 'Example.jar', timeout=2, stability=.1,
                                        probe_path=root/'probe.json', run_id='run', behavior=config)
            self.assertEqual(result.behavior['verdict'], 'PASS')
            self.assertEqual(result.evidence.verdict(True, False)[0], 'ENVIRONMENT_INVALID')

    def test_cancel_during_command_drains_owned_process(self):
        control = RunControl(lambda event: control.cancel() if event.kind == 'behavior_check_started' else None)
        result = self.run_case('hang', control=control)
        self.assertEqual(result['verdict'], 'CANCELLED')
        self.assertTrue(control.cancelled)

    def test_unsupported_is_not_success(self):
        self.assertEqual(self.run_case('unsupported')['verdict'], 'UNSUPPORTED')

    def test_wait_and_total_timeout(self):
        config = plan({'id': 'wait', 'type': 'wait', 'seconds': .15, 'timeout': .7})
        self.assertEqual(self.run_case('ok', config)['verdict'], 'PASS')
        config = plan(command(timeout=2), timeout=.2)
        self.assertEqual(self.run_case('hang', config)['verdict'], 'TIMEOUT')

    def test_runtime_failure_skips_behavior_without_sending_requests(self):
        for script, expected in [
            ('import time; time.sleep(4)', 'SERVER_START_TIMEOUT'),
            ('print("Could not load Example.jar: InvalidPluginException", flush=True)', 'PLUGIN_LOAD_FAILED'),
            ('raise SystemExit(2)', 'SERVER_START_FAILED')]:
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                result = run_server_process([sys.executable, '-u', '-c', script], root, root/'server.log',
                                            'Example', 'Example.jar', timeout=.2, stability=.1,
                                            probe_path=root/'probe.json', behavior=plan(command()))
                self.assertEqual(result.evidence.verdict(result.exit_code is None, result.timed_out)[0], expected)
                self.assertEqual(result.behavior['verdict'], 'SKIPPED')
                self.assertFalse((root/REQUEST_FILE).exists())

    def test_codesource_change_after_command_is_not_behavior_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root/'Example.jar'
            target.write_bytes(b'fixture')
            config = plan(command())
            script = server_script(config, 'ok').replace("target_source=''", f'target_source={str(target)!r}')
            script = script.replace("response = dict(schema=1", "payload['target_source'] = 'foreign.jar'\n            response = dict(schema=1")
            result = run_server_process([sys.executable, '-u', '-c', script], root, root/'server.log',
                                        'Example', 'Example.jar', timeout=2, stability=.1, probe_path=root/'probe.json',
                                        expected_source=target, run_id='run', behavior=config)
            self.assertEqual(result.evidence.verdict(True, False)[0], 'PASS')
            self.assertEqual(result.behavior['verdict'], 'ERROR')
            self.assertIn('source', result.behavior['reason'])
            self.assertEqual(result.behavior['post_health']['observed_sample']['target_source'], 'foreign.jar')

    def test_cancel_at_last_check_completion_cannot_be_overwritten_by_pass(self):
        control = RunControl(lambda event: control.cancel() if event.kind == 'behavior_check_completed' else None)
        self.assertEqual(self.run_case('ok', plan(command()), control)['verdict'], 'CANCELLED')


if __name__ == '__main__':
    unittest.main()
