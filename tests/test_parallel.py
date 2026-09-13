"""Real concurrent child-process tests with synthetic servers, never network access."""
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from pluginmatrix.control import RunControl
from pluginmatrix.matrix import MatrixConfig, MatrixEnvironment, run_matrix, matrix_exit_code
from pluginmatrix.model import VerificationResult
from pluginmatrix.providers import ServerSpec
from pluginmatrix.runtime import run_server_process, _lease_port, _ACTIVE_PORTS, _PORT_LOCK
from pluginmatrix.scheduler import schedule
from probe_support import probe_writer
from test_regressions import plugin


class ParallelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.target = plugin(self.root/'target.jar')

    def config(self, parallel):
        environments = tuple(MatrixEnvironment('1.21.4', '21', server=ServerSpec(kind, '1.21.4')) for kind in ('paper', 'purpur', 'folia'))
        return MatrixConfig(self.root/'config.json', self.target, environments, self.root/f'runs-{parallel}',
                            self.root/'cache', self.root/f'matrix-{parallel}.json', max_parallel=parallel)

    def test_parallel_equals_serial_and_keeps_order_and_isolation(self):
        active, peak = 0, 0
        lock = threading.Lock()
        def verifier(**kwargs):
            nonlocal active, peak
            with lock:
                active += 1; peak = max(peak, active)
            try:
                index = kwargs['environment_index']
                directory = kwargs['work_root']/str(index); directory.mkdir(parents=True)
                (directory/'server.log').write_text(str(index))
                time.sleep(.05 * (3-index))
                return VerificationResult(result='PASS' if index != 1 else 'PLUGIN_ENABLE_FAILED',
                                          workdir=str(directory), log_path=str(directory/'server.log'))
            finally:
                with lock:
                    active -= 1
        serial = run_matrix(self.config(1), verifier=verifier)
        self.assertEqual(peak, 1)
        parallel = run_matrix(self.config(3), verifier=verifier)
        self.assertEqual(peak, 3)
        self.assertEqual(serial['summary'], parallel['summary'])
        self.assertEqual([e['verdict'] for e in serial['environments']], [e['verdict'] for e in parallel['environments']])
        self.assertEqual([e['requested']['server']['type'] for e in parallel['environments']], ['paper', 'purpur', 'folia'])
        self.assertEqual(len({e['artifacts']['run_dir'] for e in parallel['environments']}), 3)
        self.assertEqual(matrix_exit_code(parallel), 1)

    def test_internal_failure_continues_other_environments(self):
        def verifier(**kwargs):
            if kwargs['environment_index'] == 1:
                raise RuntimeError('injected environment failure')
            return VerificationResult(result='PASS')
        report = run_matrix(self.config(3), verifier=verifier)
        self.assertEqual(report['summary']['passed'], 2)
        self.assertEqual(report['internal_errors'], 1)
        self.assertEqual(matrix_exit_code(report), 3)

    def test_cancel_stops_all_real_process_trees_and_preserves_reports(self):
        control = RunControl()
        launched = threading.Event()
        started = []
        def observer(event):
            if event.kind == 'server_started':
                started.append(event.environment_index)
                if len(started) == 3:
                    launched.set()
        control = RunControl(observer)
        def verifier(**kwargs):
            index = kwargs['environment_index']
            directory = kwargs['work_root']/str(index); directory.mkdir(parents=True)
            marker = self.root/f'survivor-{index}'
            child = f"import time,pathlib; time.sleep(1.5); pathlib.Path({str(marker)!r}).write_text('alive')"
            code = f"import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',{child!r}]); time.sleep(30)"
            outcome = run_server_process([sys.executable, '-u', '-c', code], directory, directory/'server.log',
                                         'Example', 'target.jar', 10, 1, control=control, environment_index=index)
            verdict, stage, reason = outcome.evidence.verdict(outcome.exit_code is None, outcome.timed_out)
            return VerificationResult(result=verdict, failure_stage=stage, reason=reason,
                                      evidence=outcome.evidence.events, workdir=str(directory), log_path=str(directory/'server.log'))
        def cancel():
            launched.wait(5)
            control.cancel()
        thread = threading.Thread(target=cancel); thread.start()
        report = run_matrix(self.config(3), verifier=verifier, control=control)
        thread.join(5)
        self.assertEqual(len(started), 3)
        self.assertEqual([e['verdict'] for e in report['environments']], ['CANCELLED']*3)
        self.assertTrue(all(e['artifact_availability']['runtime_report'] for e in report['environments']))
        self.assertEqual(matrix_exit_code(report), 1)
        time.sleep(1.6)
        self.assertEqual(list(self.root.glob('survivor-*')), [])

    def test_precancelled_run_never_calls_verifier(self):
        control = RunControl(); control.cancel()
        with patch('pluginmatrix.runtime.start_process') as start:
            report = run_matrix(self.config(2), control=control)
        start.assert_not_called()
        self.assertTrue(report['cancelled'])
        self.assertEqual(report['summary']['failed'], 3)

    def test_ctrl_c_drains_workers_before_returning(self):
        control = RunControl()
        def worker(index, item):
            while not control.cancelled:
                time.sleep(.01)
            return index
        from concurrent.futures import wait as real_wait
        calls = 0
        def interrupt(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise KeyboardInterrupt
            return real_wait(*args, **kwargs)
        with patch('pluginmatrix.scheduler.wait', side_effect=interrupt):
            self.assertEqual(schedule(range(3), worker, 2, control), [0, 1, 2])
        self.assertTrue(control.cancelled)

    def test_ports_are_unique_while_leased(self):
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(8) as pool:
            ports = list(pool.map(lambda _: _lease_port(), range(40)))
        try:
            self.assertEqual(len(ports), len(set(ports)))
        finally:
            with _PORT_LOCK:
                _ACTIVE_PORTS.difference_update(ports)

    def test_parallel_bounds_and_same_report_lock(self):
        for parallel in (0, 9, True, 1.5):
            with self.assertRaises(ValueError):
                run_matrix(self.config(parallel))
        from pluginmatrix.locking import file_lock
        config = self.config(2)
        with file_lock(config.report_path.with_name(config.report_path.name + '.lock')):
            with self.assertRaises(TimeoutError):
                run_matrix(config)

    def test_independent_live_probe_runs_keep_run_identity(self):
        control = RunControl()
        def worker(index, item):
            directory = self.root/str(index); directory.mkdir()
            code = probe_writer(run_id=str(index)) + "\nprint('Done (1s)!',flush=True); time.sleep(10)"
            result = run_server_process([sys.executable, '-u', '-c', code], directory, directory/'server.log',
                                        'Example', 'target.jar', 2, .3, directory/'probe.json', True,
                                        run_id=str(index), control=control, environment_index=index)
            return result.evidence.verdict(result.exit_code is None, result.timed_out)[0]
        self.assertEqual(schedule(range(3), worker, 3, control), ['PASS']*3)
