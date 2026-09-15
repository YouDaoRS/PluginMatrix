import hashlib
import io
import json
import os
import stat
import subprocess
import sys
import tarfile
import tempfile
import threading
import unittest
import zipfile
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import quote

from pluginmatrix import application
from pluginmatrix.control import RunControl, RunCancelled
from pluginmatrix.jdks import (JdkPackage, JdkStore, host_platform, _query, _extract,
                               java_selection, resolve_package)


class JdkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.system, self.arch = host_platform()
        self.suffix = '.exe' if self.system == 'windows' else ''
        self.store = JdkStore(self.root/'jdks')
        self.archive = self.make_archive()
        self.package = self.make_package(self.archive)

    def make_package(self, data):
        filename = 'OpenJDK17-test' + ('.zip' if self.system == 'windows' else '.tar.gz')
        release = 'jdk-17.0.20+8'
        return JdkPackage(17, self.system, self.arch, release, filename,
                          f'https://github.com/adoptium/temurin17-binaries/releases/download/{quote(release)}/{filename}',
                          hashlib.sha256(data).hexdigest(), len(data), _query(17, self.system, self.arch))

    def make_archive(self):
        files = {'jdk/bin/java' + self.suffix: b'java placeholder',
                 'jdk/bin/javac' + self.suffix: b'javac placeholder',
                 'jdk/lib/runtime': b'library',
                 'jdk/release': f'JAVA_VERSION="17.0.20"\r\nOS_ARCH="{self.arch}"\r\n'.encode()}
        stream = io.BytesIO()
        if self.system == 'windows':
            with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as jar:
                for name, data in files.items():
                    jar.writestr(name, data)
        else:
            with tarfile.open(fileobj=stream, mode='w:gz') as tar:
                for name, data in files.items():
                    entry = tarfile.TarInfo(name)
                    entry.size, entry.mode = len(data), 0o755
                    tar.addfile(entry, io.BytesIO(data))
        return stream.getvalue()

    def install(self, store=None, package=None, data=None, control=None):
        with patch('pluginmatrix.jdks.open_official', side_effect=lambda *a, **k: io.BytesIO(data or self.archive)), \
                patch('pluginmatrix.runtime.resolve_java', return_value=('java', '17.0.20')), \
                patch('pluginmatrix.external.run_external', return_value=SimpleNamespace(returncode=0, stdout='javac 17.0.20', stderr='')):
            return (store or self.store).install(package or self.package, control)

    def test_official_metadata_binds_version_platform_size_and_checksum(self):
        p = self.package
        document = [{'release_type': 'ga', 'vendor': 'eclipse', 'release_name': p.release,
                     'version_data': {'major': 17}, 'binaries': [{
                         'architecture': self.arch, 'os': self.system, 'image_type': 'jdk',
                         'heap_size': 'normal', 'jvm_impl': 'hotspot', 'project': 'jdk',
                         'package': {'name': p.filename, 'link': p.url, 'checksum': p.sha256, 'size': p.size}}]}]
        with patch('pluginmatrix.jdks.read_json', return_value=document):
            self.assertEqual(resolve_package(17), p)
            document[0]['binaries'][0]['image_type'] = 'jre'
            with self.assertRaises(ValueError):
                resolve_package(17)

    def test_download_is_checked_before_extraction_or_execution(self):
        with patch('pluginmatrix.jdks._extract', side_effect=AssertionError('must not extract')):
            with self.assertRaisesRegex(ValueError, 'SHA-256'):
                self.install(package=replace(self.package, sha256='0'*64))
        self.assertEqual(self.store.list()['jdks'], [])
        with self.assertRaisesRegex(ValueError, 'size'):
            self.install(package=replace(self.package, size=self.package.size-1))

    def test_source_urls_and_platform_are_not_caller_selected(self):
        for changes in ({'url': 'http://github.com/evil.zip'},
                        {'url': self.package.url.replace('adoptium/', 'attacker/')},
                        {'url': self.package.url + '?redirect=elsewhere'},
                        {'api_url': 'https://evil.invalid/'}, {'sha256': 'bad'},
                        {'filename': '../escape.zip'}, {'size': True}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.install(package=replace(self.package, **changes))
        with self.assertRaises(ValueError):
            resolve_package(True)

    def test_install_cache_selection_and_deletion(self):
        before = {key: os.environ.get(key) for key in ('PATH', 'JAVA_HOME', 'JDK_HOME')}
        record = self.install()
        self.assertFalse(record['cached'])
        self.assertEqual(record['package']['sha256'], self.package.sha256)
        self.assertTrue(Path(record['javac']).is_file())
        with patch('pluginmatrix.jdks.open_official', side_effect=AssertionError('cache must not download')):
            self.assertTrue(self.store.install(self.package)['cached'])
        with java_selection('managed:' + record['id'], self.store.root) as (executable, managed):
            self.assertEqual(executable, record['path'])
            self.assertEqual(managed['id'], record['id'])
            with self.assertRaisesRegex(ValueError, 'in use'):
                self.store.delete(record['id'])
        with java_selection(record['path'], self.store.root) as (executable, managed):
            self.assertEqual(managed['id'], record['id'])
            with self.assertRaisesRegex(ValueError, 'in use'):
                self.store.delete(record['id'])
        self.assertTrue(self.store.delete(record['id'])['deleted'])
        self.assertEqual(self.store.list()['jdks'], [])
        self.assertEqual(before, {key: os.environ.get(key) for key in before})

    def test_integrity_failure_blocks_java_use(self):
        record = self.install()
        library = Path(record['path']).parents[1]/'lib/runtime'
        library.write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError, 'integrity|size'):
            with self.store.lease(record['id']):
                self.fail('corrupt JDK was selected')
        self.assertTrue(self.store.delete(record['id'])['deleted'])

    def test_concurrent_installs_publish_only_one_download(self):
        barrier = threading.Barrier(2)
        results, errors, downloads = [], [], []

        def download(*a, **k):
            downloads.append(1)
            return io.BytesIO(self.archive)

        def worker():
            try:
                barrier.wait(timeout=5)
                results.append(self.store.install(self.package))
            except BaseException as exc:
                errors.append(exc)
        with patch('pluginmatrix.jdks.open_official', side_effect=download), \
                patch('pluginmatrix.runtime.resolve_java', return_value=('java', '17.0.20')), \
                patch('pluginmatrix.external.run_external', return_value=SimpleNamespace(returncode=0, stdout='javac 17', stderr='')):
            threads = [threading.Thread(target=worker) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=15)
                self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(len(downloads), 1)
        self.assertEqual(sorted(r['cached'] for r in results), [False, True])

    def test_separate_process_use_lease_prevents_deletion(self):
        self.install()
        code = ('import sys; from pathlib import Path; from pluginmatrix.jdks import JdkStore\n'
                'with JdkStore(Path(sys.argv[1])).lease(sys.argv[2]):\n'
                ' print("leased", flush=True)\n'
                ' sys.stdin.readline()\n')
        process = subprocess.Popen([sys.executable, '-c', code, str(self.store.root), self.package.id],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(process.stdout.readline().strip(), 'leased')
            with self.assertRaisesRegex(ValueError, 'in use'):
                self.store.delete(self.package.id)
            process.communicate('\n', timeout=10)
            self.assertEqual(process.returncode, 0)
        finally:
            if process.poll() is None:
                process.kill()
            process.communicate()
        self.assertTrue(self.store.delete(self.package.id)['deleted'])

    def test_cancelled_install_is_not_published(self):
        control = RunControl()
        control.cancel()
        with self.assertRaises(RunCancelled):
            self.install(control=control)
        self.assertFalse(self.store.root.exists())
        control = RunControl(lambda event: control.cancel() if event.kind == 'jdk_download_completed' else None)
        with self.assertRaises(RunCancelled):
            self.install(control=control)
        self.assertEqual(self.store.list()['jdks'], [])

    def test_crashed_lease_is_reclaimed_and_unknown_directory_is_not_deleted(self):
        self.install()
        leases = self.store.root/'leases'/self.package.id
        leases.mkdir(parents=True)
        (leases/('a'*32+'.lock')).write_bytes(b'0')
        self.assertTrue(self.store.delete(self.package.id)['deleted'])
        other = self.root/'unrelated'
        other.mkdir()
        (other/'keep.txt').write_text('keep')
        with self.assertRaises(ValueError):
            self.install(store=JdkStore(other))
        self.assertEqual((other/'keep.txt').read_text(), 'keep')
        for ident in ('../unrelated', '', 'temurin-17-windows-x64-'+'a'*63):
            with self.assertRaises(ValueError):
                self.store.delete(ident)

    def test_hardlinks_are_rejected_on_selection_and_deletion(self):
        record = self.install()
        java = Path(record['path'])
        external = self.root/'external'
        external.write_bytes(java.read_bytes())
        java.unlink()
        os.link(external, java)
        with self.assertRaisesRegex(ValueError, 'hardlink'):
            with self.store.lease(record['id']):
                pass
        with self.assertRaisesRegex(ValueError, 'hardlink'):
            self.store.delete(record['id'])
        self.assertTrue(external.is_file())
        java.unlink()  # Test-owned link only, not recursive cleanup of user data.

    def test_symlink_or_junction_parent_is_refused(self):
        outside = self.root/'outside'
        outside.mkdir()
        alias = self.root/'alias'
        try:
            alias.symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest('symlink privilege unavailable')
        with self.assertRaises(ValueError):
            JdkStore(alias/'jdk')
        self.assertEqual(list(outside.iterdir()), [])

    def test_zip_traversal_case_collision_links_and_specials(self):
        for names in (['../escape'], ['/absolute'], ['C:/escape'], ['jdk/CON'], ['jdk\\bad'],
                      ['jdk/A', 'jdk/a'], ['jdk/Lib/a', 'jdk/lib/b'], ['jdk/file:stream'], ['jdk/trailing.']):
            stream = io.BytesIO()
            with zipfile.ZipFile(stream, 'w') as jar:
                for name in names:
                    entry = zipfile.ZipInfo()
                    entry.filename = name  # Avoid ZipInfo normalizing backslashes on Windows.
                    jar.writestr(entry, b'x')
            archive = self.root/'bad.zip'
            archive.write_bytes(stream.getvalue())
            with tempfile.TemporaryDirectory(dir=self.root) as directory:
                with self.assertRaises(ValueError):
                    _extract(archive, Path(directory)/'payload', RunControl())
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as jar:
            entry = zipfile.ZipInfo('jdk/link')
            entry.external_attr = (stat.S_IFLNK | 0o777) << 16
            jar.writestr(entry, '../../outside')
        archive.write_bytes(stream.getvalue())
        with self.assertRaisesRegex(ValueError, 'links'):
            _extract(archive, self.root/'link-payload', RunControl())

    def test_tar_link_and_device_entries_are_never_created(self):
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE, tarfile.FIFOTYPE):
            stream = io.BytesIO()
            with tarfile.open(fileobj=stream, mode='w:gz') as tar:
                entry = tarfile.TarInfo('jdk/link')
                entry.type, entry.linkname = kind, '../../outside'
                tar.addfile(entry)
            archive = self.root/'bad.tar.gz'
            archive.write_bytes(stream.getvalue())
            with tempfile.TemporaryDirectory(dir=self.root) as directory:
                with self.assertRaises(ValueError):
                    _extract(archive, Path(directory)/'payload', RunControl())

    def test_preview_pin_cannot_silently_change_download(self):
        with patch('pluginmatrix.application.resolve_package', return_value=self.package), \
                patch.object(JdkStore, 'install', side_effect=AssertionError('must not download')):
            with self.assertRaisesRegex(ValueError, 'changed since preview'):
                application.install_managed_jdk(17, expected_id='old-id', root=self.store.root)

    def test_receipt_escape_cannot_select_or_delete_unrelated_files(self):
        record = self.install()
        receipt = Path(record['receipt'])
        value = json.loads(receipt.read_text())
        value['home'] = '../../outside'
        receipt.write_text(json.dumps(value))
        outside = self.root/'outside'
        outside.write_text('keep')
        with self.assertRaises(ValueError):
            with self.store.lease(record['id']):
                pass
        with self.assertRaises(ValueError):
            self.store.delete(record['id'])
        self.assertEqual(outside.read_text(), 'keep')

    def test_managed_recommendation_preserves_reference_and_store(self):
        import time
        from pluginmatrix.recommendations import recommend_environment
        record = self.install()
        analysis = {'valid': True, 'plugin': {'plugin_name': 'Example', 'api_version': '1.20'}}
        catalog = {'available': True, 'provider': 'paper', 'minecraft_version': '1.20.1',
                   'source': 'network', 'fetched_at': time.time(), 'recommended_build': 196,
                   'builds': [{'id': 196, 'channel': 'STABLE'}]}
        result = recommend_environment(analysis, minecraft='1.20.1', catalog=catalog, java_runtimes=[record])
        self.assertTrue(result['ready'])
        self.assertEqual(result['selection']['java'], 'managed:' + record['id'])
        self.assertEqual(result['selection']['jdk_dir'], str(self.store.root))
        listed = self.store.list()['jdks']
        result = recommend_environment(analysis, minecraft='1.20.1', catalog=catalog, java_runtimes=listed)
        self.assertFalse(result['ready'])  # Listing metadata alone is not integrity verification.

    def test_application_single_holds_lease_until_verifier_finishes(self):
        from pluginmatrix.model import VerificationResult
        from pluginmatrix.providers import ServerSpec
        record = self.install()
        reference = 'managed:' + record['id']

        def verify(*args, **kwargs):
            self.assertEqual(args[2], record['path'])
            with self.assertRaisesRegex(ValueError, 'in use'):
                self.store.delete(record['id'])
            return VerificationResult(result='PASS')
        with patch('pluginmatrix.application._verify', side_effect=verify):
            result = application.run_single(plugin=self.root/'input.jar', server=ServerSpec('paper', '1.20.1'),
                                            java=reference, jdk_dir=self.store.root,
                                            work_root=self.root/'runs', cache_dir=self.root/'cache')
        self.assertTrue(result.passed)
        self.assertEqual(result.metadata['requested_java'], reference)
        self.assertEqual(result.metadata['managed_jdk']['package']['sha256'], self.package.sha256)

    def test_matrix_managed_prerequisite_failure_is_environment_failure(self):
        from pluginmatrix.matrix import MatrixConfig, MatrixEnvironment, run_matrix, matrix_exit_code
        config = MatrixConfig(self.root/'config.json', self.root/'input.jar',
                              (MatrixEnvironment('1.20.1', 'managed:' + self.package.id),),
                              self.root/'runs', self.root/'cache', self.root/'report.json',
                              schema_version=2, jdk_dir=self.store.root)
        with patch('pluginmatrix.matrix.verify', side_effect=AssertionError('must not launch')) as verifier:
            report = run_matrix(config, verifier=verifier)
        self.assertEqual(report['environments'][0]['runtime_verdict'], 'ENVIRONMENT_INVALID')
        self.assertEqual(report['internal_errors'], 0)
        self.assertEqual(matrix_exit_code(report), 1)
        verifier.assert_not_called()

    def test_single_missing_and_cancelled_jdk_preserve_prerequisite_verdicts(self):
        from pluginmatrix.providers import ServerSpec
        for cancel in (False, True):
            control = RunControl()
            if cancel:
                control.cancel()
            with patch('pluginmatrix.application._verify', side_effect=AssertionError('must not launch')):
                result = application.run_single(
                    plugin=self.root/'input.jar', server=ServerSpec('paper', '1.20.1'),
                    java='managed:' + self.package.id, jdk_dir=self.store.root,
                    work_root=self.root/'runs', cache_dir=self.root/'cache', control=control,
                    report_path=self.root/'single.json',
                    behavior={'schema': 1, 'checks': [{'id': 'wait', 'type': 'wait', 'seconds': 1}]})
            self.assertEqual(result.result, 'CANCELLED' if cancel else 'ENVIRONMENT_INVALID')
            self.assertEqual(result.behavior['verdict'], 'SKIPPED')
            self.assertFalse(result.passed)
            self.assertEqual(json.loads((self.root/'single.json').read_text())['result'], result.result)

    def test_expanded_archive_bound_is_checked_before_writing_member(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as jar:
            jar.writestr('jdk/large', b'x'*100)
        archive = self.root/'size.zip'
        archive.write_bytes(stream.getvalue())
        with patch('pluginmatrix.jdks.MAX_EXPANDED', 10), self.assertRaisesRegex(ValueError, 'expanded'):
            _extract(archive, self.root/'large-payload', RunControl())
        self.assertFalse((self.root/'large-payload/jdk/large').exists())


if __name__ == '__main__':
    unittest.main()
