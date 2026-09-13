"""Release regressions exercise observable behavior, real files and real children."""
import contextlib
import io
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
import warnings
import zipfile
from pathlib import Path
from unittest.mock import patch

from pluginmatrix.cli import main
from pluginmatrix.files import atomic_copy, atomic_json, protect_inputs, validate_output_paths
from pluginmatrix.matrix import load_matrix_config, MatrixConfigError
from pluginmatrix.paper import ensure_paper, PaperDownloadError
from pluginmatrix.preflight import inspect_plugin, PreflightError
from pluginmatrix.probe import _extract_paper_libraries, read_probe_evidence
from pluginmatrix.runtime import RuntimeEvidence, run_server_process, verify, _cache_paper_runtime
from probe_support import probe_writer, one_probe
from test_regressions import plugin

ROOT = Path(__file__).resolve().parents[1]


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def run_code(self, code, stability=.25, **kwargs):
        directory = self.root / str(time.time_ns())
        directory.mkdir()
        started = time.monotonic()
        result = run_server_process([sys.executable, '-u', '-c', code], directory,
                                    directory/'server.log', 'Example', 'example.jar', 1,
                                    stability, directory/'probe.json', True,
                                    expected_version='1.0', **kwargs)
        return result, directory, time.monotonic() - started

    def verdict(self, result):
        return result.evidence.verdict(result.exit_code is None, result.timed_out)[0]

    def test_full_window_starts_after_delayed_first_probe(self):
        code = "import time; print('Done (1s)!',flush=True); time.sleep(.3)\n" + probe_writer() + '\ntime.sleep(5)'
        result, _, elapsed = self.run_code(code, stability=.35)
        self.assertEqual(self.verdict(result), 'PASS')
        self.assertGreaterEqual(elapsed, .65)
        events = {event.kind: event for event in result.evidence.events}
        self.assertGreaterEqual(events['stability_window_completed'].timestamp - events['stability_window_started'].timestamp, .35)

    def test_single_snapshot_cannot_pass_even_short_window(self):
        result, _, _ = self.run_code(one_probe() + "print('Done (1s)!',flush=True); time.sleep(5)")
        self.assertEqual(self.verdict(result), 'UNKNOWN_FAILURE')
        self.assertFalse(result.evidence.observation_complete)

    def test_touching_or_rewriting_same_sequence_is_not_fresh_evidence(self):
        code = one_probe() + "print('Done (1s)!',flush=True)\nwhile True:\n p['emitted_at_ms']=int(time.time()*1000)\n pathlib.Path('probe.json').write_text(json.dumps(p))\n time.sleep(.05)"
        result, _, _ = self.run_code(code)
        self.assertEqual(self.verdict(result), 'UNKNOWN_FAILURE')
        self.assertFalse(result.evidence.observation_complete)

    def test_backwards_sequence_and_timestamp_fail_closed(self):
        for field, value in [('sequence', 1), ('emitted_at_ms', 1)]:
            with self.subTest(field=field):
                code = one_probe(sequence=10) + "print('Done (1s)!',flush=True); time.sleep(.15); "
                code += f"p[{field!r}]={value}; pathlib.Path('probe.json').write_text(json.dumps(p)); time.sleep(5)"
                result, _, _ = self.run_code(code, stability=.5)
                self.assertEqual(self.verdict(result), 'UNKNOWN_FAILURE')
                self.assertIn('backwards', result.evidence.direct_runtime_error)

    def test_wrong_run_version_main_and_source_never_pass(self):
        for payload, expected in [({'run_id':'old'}, {}), ({'target_version':'2.0'}, {}),
                                  ({'target_main':'other.Main'}, {'expected_main':'example.Main'}),
                                  ({'target_source':str(self.root/'dependency.jar')}, {'expected_source':self.root/'example.jar'})]:
            with self.subTest(payload=payload):
                result, _, _ = self.run_code(probe_writer(**payload) + "\nprint('Enabling Example v1.0'); print('Done (1s)!'); time.sleep(5)", **expected)
                self.assertEqual(self.verdict(result), 'UNKNOWN_FAILURE')

    def test_identity_error_cannot_be_cleared_by_later_valid_snapshot(self):
        evidence = RuntimeEvidence('Example', expected_version='1.0')
        evidence.observe_probe(dict(target_present=True,target_enabled=True,target_name='Example',target_version='2.0'), 0)
        evidence.observe_probe(dict(target_present=True,target_enabled=True,target_name='Example',target_version='1.0'), .1)
        self.assertIsNotNone(evidence.direct_runtime_error)
        from pluginmatrix.runtime import _runtime_checks, ProcessRun
        checks = {item.name: item.status for item in _runtime_checks(evidence, ProcessRun(evidence, None, False))}
        self.assertEqual(checks['Runtime probe'], 'FAIL')
        self.assertEqual(checks['Plugin stability'], 'FAIL')

    def test_old_or_malformed_probe_protocol_is_not_accepted(self):
        good = dict(probe='pluginmatrix', schema=2,run_id='',sequence=1,emitted_at_ms=1,
                    target_present=True,target_enabled=True,target_name='Example',target_version='1.0',
                    target_main='example.Main',target_source='',target_ever_disabled=False)
        for changes in [{'schema':1},{'sequence':True},{'emitted_at_ms':'1'}, {'target_present':False}]:
            path = self.root/'probe.json'
            path.write_text(json.dumps({**good,**changes}))
            self.assertIsNone(read_probe_evidence(path))
        path.write_bytes(b'\xff')
        self.assertIsNone(read_probe_evidence(path))
        path.write_text(' ' * 16385)
        self.assertIsNone(read_probe_evidence(path))

    def test_disable_event_survives_reenable_between_samples(self):
        result, _, _ = self.run_code(probe_writer(target_ever_disabled=True) + "\nprint('Done (1s)!'); time.sleep(5)")
        self.assertEqual(self.verdict(result), 'PLUGIN_DISABLED')

    def test_closed_stdout_does_not_shorten_observation(self):
        result, _, elapsed = self.run_code(probe_writer() + "\nprint('Done (1s)!',flush=True); os.close(1); time.sleep(5)", stability=.4)
        self.assertEqual(self.verdict(result), 'PASS')
        self.assertGreaterEqual(elapsed, .4)

    def test_invalid_utf8_success_retains_full_window_and_bytes(self):
        result, directory, elapsed = self.run_code(probe_writer() + "\nprint('Done (1s)!'); os.write(1,b'\\xff\\n'); time.sleep(5)", stability=.4)
        self.assertEqual(self.verdict(result), 'PASS')
        self.assertGreaterEqual(elapsed, .4)
        self.assertIn(b'\xff', (directory/'server.log').read_bytes())

    def test_read_error_returns_failure_and_cleans_real_process(self):
        original = Path.open
        class BrokenReader:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, size): raise OSError('injected log read failure')
        def open_file(path, *args, **kwargs):
            if path.name == 'server.log' and args and args[0] == 'rb':
                return BrokenReader()
            return original(path, *args, **kwargs)
        with patch.object(Path, 'open', open_file):
            result, _, elapsed = self.run_code('import time; time.sleep(30)')
        self.assertEqual(self.verdict(result), 'ENVIRONMENT_INVALID')
        self.assertIn('log read failure', result.evidence.failure_reason)
        self.assertLess(elapsed, 3)

    def test_log_flood_after_parent_exit_is_bounded_and_tree_is_killed(self):
        marker = self.root/'survived'
        child = f"import os,time,pathlib; end=time.monotonic()+1;\nwhile time.monotonic()<end: os.write(1,b'x'*8192)\npathlib.Path({str(marker)!r}).write_text('alive')"
        code = f"import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',{child!r}]); time.sleep(.1)"
        result, _, elapsed = self.run_code(code)
        self.assertNotEqual(self.verdict(result), 'PASS')
        self.assertLess(elapsed, 3)
        time.sleep(1.1)
        self.assertFalse(marker.exists())

    def test_live_parent_child_grandchild_timeout_cleanup(self):
        marker = self.root/'grandchild'
        grandchild = f"import pathlib,time; time.sleep(1); pathlib.Path({str(marker)!r}).write_text('alive')"
        child = f"import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',{grandchild!r}]); time.sleep(10)"
        code = f"import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',{child!r}]); time.sleep(10)"
        directory = self.root/'tree'; directory.mkdir()
        result = run_server_process([sys.executable,'-c',code],directory,directory/'server.log','Example',None,.35,.1)
        self.assertEqual(self.verdict(result), 'SERVER_START_TIMEOUT')
        time.sleep(1.1)
        self.assertFalse(marker.exists())

    def test_other_plugin_dependency_on_target_does_not_pollute_verdict(self):
        evidence = RuntimeEvidence('Example','example.jar')
        for line in ['UnknownDependencyException: Unknown dependency Example for Other',
                     "Could not load 'plugins/other.jar': UnknownDependencyException: Example",
                     '[12:00:00 WARN]: [Other] Failed to download Paper jar for Example',
                     '[Other] Error occurred while enabling Example v1.0',
                     'Error occurred while enabling Other v1.0 (depends on Example)']:
            evidence.observe_line(line, .1)
        self.assertFalse(evidence.plugin_load_failed)
        self.assertFalse(evidence.plugin_enable_failed)
        self.assertFalse(evidence.environment_failed)

    def test_aliases_and_probe_reserved_names_are_rejected_before_java(self):
        target = plugin(self.root/'target.jar')
        for extra in ['provides: [Example]', 'provides: [PluginMatrixRuntimeProbe]']:
            dep = plugin(self.root/'dep.jar', 'Other', extra=extra)
            with patch('pluginmatrix.runtime.resolve_java') as java:
                result = verify(target,'1.20.1','17',self.root/'runs',self.root/'cache',2,1,[dep])
            self.assertEqual(result.result,'ENVIRONMENT_INVALID')
            self.assertIn('conflicts',result.reason)
            java.assert_not_called()

    def test_copy_hash_change_is_rejected_before_server_start(self):
        target = plugin(self.root/'target.jar')
        paper = self.root/'paper.jar'; paper.write_bytes(b'paper')
        real_copy = shutil.copy2
        def changed(source,destination):
            output = real_copy(source,destination)
            if Path(source) == target:
                Path(destination).write_bytes(b'changed')
            return output
        with patch('pluginmatrix.runtime.resolve_java',return_value=('java','17.0.1')), patch('pluginmatrix.runtime.shutil.copy2',side_effect=changed), patch('pluginmatrix.runtime.run_server_process') as start:
            result=verify(target,'1.20.1','17',self.root/'runs',self.root/'cache',2,1,paper_jar=paper)
        self.assertEqual(result.result,'ENVIRONMENT_INVALID')
        self.assertIn('changed after preflight',result.reason)
        start.assert_not_called()

    def test_alias_after_block_comments_and_blank_lines_is_not_omitted(self):
        target = plugin(self.root/'target.jar')
        for extra in ['provides: # aliases\n  - Safe\n\n  # next alias\n  - Example\n',
                      'provides:\n- Safe\n# next alias\n- Example\n',
                      'provides: ["\\u0045xample"]\n']:
            dependency = plugin(self.root/'other.jar', 'Other', extra=extra)
            with patch('pluginmatrix.runtime.resolve_java') as java:
                result = verify(target, '1.20.1', '17', self.root/'runs', self.root/'cache', 2, 1, [dependency])
            self.assertEqual(result.result, 'ENVIRONMENT_INVALID')
            self.assertIn('conflicts', result.reason)
            java.assert_not_called()

    def test_reports_protect_invalid_plugin_and_dependencies(self):
        target=self.root/'bad.jar'; target.write_bytes(b'bad')
        dependency=self.root/'dependency.jar'; dependency.write_bytes(b'dependency')
        alias=self.root/'report.json'; os.link(dependency,alias)
        with contextlib.redirect_stdout(io.StringIO()):
            status=main(['test','--plugin',str(target),'--dependency',str(dependency),'--paper','1.20.1','--java','17','--report',str(alias)])
        self.assertEqual(status,2)
        self.assertEqual(dependency.read_bytes(),b'dependency')

    def test_work_cache_overlap_and_input_under_mutable_root_are_rejected(self):
        target=plugin(self.root/'target.jar')
        for work,cache in [(self.root/'work',self.root/'work/cache'),(self.root/'cache/work',self.root/'cache'),(self.root,self.root/'cache')]:
            with self.assertRaises(ValueError): validate_output_paths(work,cache,[target])

    def test_cache_capture_does_not_modify_destination_hardlink_target(self):
        server=self.root/'server'; cache=self.root/'cache'
        artifact=server/'versions/1.20.1/paper-1.20.1.jar'; artifact.parent.mkdir(parents=True); artifact.write_bytes(b'new')
        outside=self.root/'outside.jar'; outside.write_bytes(b'original')
        destination=cache/'versions/1.20.1/paper-1.20.1.jar'; destination.parent.mkdir(parents=True); os.link(outside,destination)
        self.assertTrue(_cache_paper_runtime(server,cache,'1.20.1'))
        self.assertEqual(outside.read_bytes(),b'original')
        self.assertEqual(destination.read_bytes(),b'new')

    def test_symlink_output_and_cache_destination_are_rejected(self):
        outside=self.root/'outside'; outside.mkdir()
        link=self.root/'link'
        try: link.symlink_to(outside,target_is_directory=True)
        except OSError:
            if os.name != 'nt': raise
            self.skipTest('symlinks require host permission; mandatory on Linux CI')
        with self.assertRaises(ValueError): atomic_json(link/'report.json',{})
        with self.assertRaises(ValueError): atomic_copy(ROOT/'README.md',link/'copied')
        self.assertEqual(list(outside.iterdir()),[])

    @unittest.skipUnless(os.name=='nt','Windows junction regression')
    def test_windows_junction_output_is_rejected(self):
        outside=self.root/'outside'; outside.mkdir(); junction=self.root/'junction'
        command=['powershell','-NoProfile','-Command', 'New-Item -ItemType Junction -Path $env:PM_TEST_LINK -Target $env:PM_TEST_TARGET | Out-Null']
        completed=subprocess.run(command,env={**os.environ,'PM_TEST_LINK':str(junction),'PM_TEST_TARGET':str(outside)},capture_output=True,timeout=10)
        self.assertEqual(completed.returncode,0,completed.stderr)
        try:
            with self.assertRaises(ValueError): atomic_json(junction/'result.json',{})
            self.assertFalse((outside/'result.json').exists())
        finally:
            junction.rmdir()

    @unittest.skipUnless(os.name=='nt','Windows suspended Job Object regression')
    def test_job_assignment_failure_cannot_execute_user_code(self):
        marker=self.root/'executed'
        with patch('pluginmatrix.processes._windows_job',side_effect=OSError('job assignment failed')):
            result, _, elapsed=self.run_code(f"import pathlib; pathlib.Path({str(marker)!r}).write_text('ran')")
        self.assertEqual(self.verdict(result),'ENVIRONMENT_INVALID')
        self.assertIn('job assignment failed',result.evidence.failure_reason)
        self.assertFalse(marker.exists())
        self.assertLess(elapsed,3)

    def test_unsafe_paper_names_and_missing_checksum_do_not_write(self):
        for name,checksum in [('../outside.jar','0'*64),('C:outside.jar','0'*64),('NUL.jar','0'*64),('COM1.jar','0'*64),('paper.jar',None)]:
            with patch('pluginmatrix.paper.resolve_paper',return_value={'paper_jar_name':name,'paper_sha256':checksum}), patch('pluginmatrix.paper.urllib.request.urlopen') as network:
                with self.assertRaises(PaperDownloadError): ensure_paper('1.20.1',self.root/'cache')
                network.assert_not_called()
        self.assertFalse((self.root/'outside.jar').exists())

    def test_embedded_library_traversal_is_rejected(self):
        for name in ['META-INF/libraries/../../../outside.jar','META-INF/libraries/C:/outside.jar','META-INF/libraries/a\\..\\..\\outside.jar']:
            jar=self.root/'paper.jar'
            with zipfile.ZipFile(jar,'w') as archive: archive.writestr(name,b'bad')
            with self.assertRaises(RuntimeError): _extract_paper_libraries(jar,self.root/'libraries')
        self.assertFalse((self.root/'outside.jar').exists())

    def test_duplicate_encrypted_and_large_zip_entries_are_rejected(self):
        jar=plugin(self.root/'duplicate.jar')
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            with zipfile.ZipFile(jar,'a') as archive: archive.writestr('plugin.yml','name: Other')
        with self.assertRaisesRegex(PreflightError,'duplicate'): inspect_plugin(jar)
        jar=plugin(self.root/'encrypted.jar'); data=bytearray(jar.read_bytes())
        for signature,offset in [(b'PK\x03\x04',6),(b'PK\x01\x02',8)]:
            cursor=data.index(signature); struct.pack_into('<H',data,cursor+offset,1)
        jar.write_bytes(data)
        with self.assertRaisesRegex(PreflightError,'encryption'): inspect_plugin(jar)
        jar=plugin(self.root/'huge.jar'); data=bytearray(jar.read_bytes()); cursor=data.index(b'PK\x01\x02'); struct.pack_into('<I',data,cursor+24,513*1024*1024); jar.write_bytes(data)
        with self.assertRaisesRegex(PreflightError,'limits'): inspect_plugin(jar)

    def test_ambiguous_descriptors_are_rejected(self):
        for descriptor in ['name: Example\nname: Other\nversion: 1\nmain: example.Main',
                           'name: Example\nmain: example.Main',
                           'name: Example\nversion: &version 1\nmain: example.Main',
                           'name: Example\nversion: 1\nmain: example.Main\n---\nname: Other']:
            jar=self.root/'bad.jar'
            with zipfile.ZipFile(jar,'w') as archive:
                archive.writestr('plugin.yml',descriptor)
                archive.writestr('example/Main.class',b'\xca\xfe\xba\xbe\x00\x00\x00\x3d')
            with self.assertRaises(PreflightError): inspect_plugin(jar)

    def test_zero_matrix_window_is_configuration_error(self):
        target=plugin(self.root/'target.jar'); config=self.root/'config.json'
        config.write_text(json.dumps({'plugin':str(target),'environments':[{'paper':'1.20.1','java':17}], 'options':{'stability_window':0}}))
        with self.assertRaisesRegex(MatrixConfigError,'positive'): load_matrix_config(config)


class WorkflowExecutionTests(unittest.TestCase):
    def test_prepare_executes_safe_names_and_preserves_conflicting_inputs(self):
        workflow=(ROOT/'.github/workflows/matrix.yml').read_text()
        script=textwrap.dedent(workflow.split("          python - <<'PY'\n",1)[1].split('          PY',1)[0])
        for filename in ['plugin.jar', '$(touch INJECTED).jar' if os.name!='nt' else 'semi;colon.jar']:
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as temp:
                root=Path(temp); (root/filename).write_bytes(b'input')
                config=root/'config.json'; config.write_text(json.dumps({'environments':[{'java':17}]}))
                env={**os.environ,'PYTHONPATH':str(ROOT),'GITHUB_WORKSPACE':str(root),'MATRIX_CONFIG':'config.json','PLUGIN_JAR':filename}
                result=subprocess.run([sys.executable,'-c',script],cwd=root,env=env,capture_output=True,timeout=10)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual((root/'.ci/plugin.jar').read_bytes(),b'input')
                self.assertFalse((root/'INJECTED').exists())
                original=(root/'.ci/matrix.json').read_bytes()
                env['MATRIX_CONFIG']='.ci/matrix.json'
                result=subprocess.run([sys.executable,'-c',script],cwd=root,env=env,capture_output=True,timeout=10)
                self.assertEqual(result.returncode,2)
                self.assertEqual((root/'.ci/matrix.json').read_bytes(),original)

    def test_bash_prepare_and_final_exit_handle_special_characters(self):
        bash = shutil.which('bash')
        if os.name == 'nt':
            git = shutil.which('git')
            bash = str(Path(git).parent.parent / 'bin/bash.exe') if git else None
        if not bash or not Path(bash).is_file(): self.skipTest('bash unavailable')
        workflow=(ROOT/'.github/workflows/matrix.yml').read_text()
        prepare=textwrap.dedent(workflow.split('          set +e\n',1)[1].split('      - name: Run Compatibility Matrix',1)[0])
        final=textwrap.dedent('          case "$PREPARE_EXIT"'+workflow.split('          case "$PREPARE_EXIT"',1)[1])
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); output=root/'output'
            (root/'config.json').write_text(json.dumps({'environments':[{'java':17}]}))
            # '$', parentheses and semicolons are data passed through env, not shell code.
            filename='$(echo INJECTED); plugin.jar'; (root/filename).write_bytes(b'jar')
            env={**os.environ,'PYTHONPATH':str(ROOT),'GITHUB_WORKSPACE':str(root),'MATRIX_CONFIG':'config.json','PLUGIN_JAR':filename,'GITHUB_OUTPUT':str(output)}
            result=subprocess.run([bash,'-c',prepare],cwd=root,env=env,capture_output=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('exit_code=0',output.read_text())
            self.assertEqual((root/'.ci/plugin.jar').read_bytes(),b'jar')
            for prepare_exit,matrix_exit,expected in [('0','0',0),('0','1',1),('2','0',2),('','0',3),('0','$(echo INJECTED)',3)]:
                result=subprocess.run([bash,'-c',final],cwd=root,env={**env,'PREPARE_EXIT':prepare_exit,'MATRIX_EXIT':matrix_exit},capture_output=True,timeout=10)
                self.assertEqual(result.returncode,expected,result.stderr)
