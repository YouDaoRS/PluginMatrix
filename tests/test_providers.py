"""Provider behavior and official input trust boundaries; no public network calls."""
import hashlib
import io
import json
import os
import tempfile
import threading
import unittest
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from pluginmatrix.artifacts import ProviderError, ensure_download, safe_url, read_json
from pluginmatrix.control import RunControl
from pluginmatrix.providers import ServerSpec, get_provider, parse_server, inspect_providers, FILL_HOSTS
from pluginmatrix.runtime import verify, write_report, RuntimeEvidence
from pluginmatrix.preflight import inspect_plugin, PreflightError
from test_regressions import plugin


def build(number=10, channel='STABLE', **download):
    return {'id': number, 'channel': channel, 'time': '2026-01-01', 'downloads': {'server:default': {
        'name': f'server-{number}.jar', 'url': 'https://fill-data.papermc.io/server.jar',
        'checksums': {'sha256': '0' * 64}, **download}}}


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_contract_metadata_and_spec_roundtrip(self):
        self.assertEqual([p['type'] for p in inspect_providers()], ['paper', 'purpur', 'folia', 'local'])
        for kind in ('paper', 'purpur', 'folia'):
            spec = parse_server({'type': kind, 'version': '1.21.4', 'build': 'latest'})
            self.assertEqual(parse_server(spec.to_dict()), spec)
            provider = get_provider(kind)
            self.assertIn('fixed_build', provider.metadata.capabilities)
            self.assertIn('ready', provider.interpret_server_line('Done (1.2s)! For help, type "help"'))
            self.assertIn('shutdown', provider.interpret_server_line('Stopping server'))
            self.assertNotIn('ready', provider.interpret_server_line('Loading world'))
            self.assertEqual(provider.command(spec, 'java', 'server.jar')[-3:], ['-jar', 'server.jar', '--nogui'])
        self.assertTrue(get_provider('folia').metadata.regionized)

    def test_latest_prefers_stable_and_fixed_is_exact_across_channels(self):
        for kind in ('paper', 'folia'):
            with patch('pluginmatrix.providers.read_json', return_value=[build(10), build(11, 'ALPHA')]):
                self.assertEqual(get_provider(kind).resolve(ServerSpec(kind, '1.21.4'))['resolved_build'], 10)
                self.assertEqual(get_provider(kind).resolve(ServerSpec(kind, '1.21.4', 11))['channel'], 'ALPHA')
            with patch('pluginmatrix.providers.read_json', return_value=[build(11, 'ALPHA')]):
                self.assertEqual(get_provider(kind).resolve(ServerSpec(kind, '1.21.4'))['resolved_build'], 11)

    def test_purpur_latest_is_pinned_before_download(self):
        payload = {'project': 'purpur', 'version': '1.21.4', 'result': 'SUCCESS', 'build': '2416', 'md5': 'a'*32}
        for requested in (None, 2416):
            with patch('pluginmatrix.providers.read_json', return_value=payload):
                info = get_provider('purpur').resolve(ServerSpec('purpur', '1.21.4', requested))
            self.assertEqual(info['resolved_build'], 2416)
            self.assertTrue(info['download_url'].endswith('/2416/download'))
            self.assertEqual(info['checksum_algorithm'], 'md5')
        with patch('pluginmatrix.providers.read_json', return_value=payload):
            with self.assertRaises(ProviderError):
                get_provider('purpur').resolve(ServerSpec('purpur', '1.21.4', 1))

    def test_malformed_apis_and_unsafe_urls_fail_closed(self):
        bad = [None, {}, [], [None], [build(True)], [build(channel='unknown')],
               [build(name='../escape.jar')], [build(url='file:///tmp/server.jar')],
               [build(checksums={'sha256': 'no'})], [build(name='NUL.jar')]]
        for payload in bad:
            with self.subTest(payload=payload), patch('pluginmatrix.providers.read_json', return_value=payload):
                with self.assertRaises(ProviderError):
                    get_provider('paper').resolve(ServerSpec('paper', '1.21.4'))
        for url in ('http://fill.papermc.io/x', 'https://evil.invalid/x', 'https://user@fill.papermc.io/x', 'https://fill.papermc.io:444/x'):
            with self.assertRaises(ProviderError):
                safe_url(url, FILL_HOSTS)
        with patch('pluginmatrix.artifacts.open_official', return_value=io.BytesIO(b'x'*(4*1024*1024+1))):
            with self.assertRaises(ProviderError):
                read_json('https://fill.papermc.io/x', FILL_HOSTS)

    def download(self, algorithm='sha256', content=b'fixture'):
        return ensure_download(self.root/'cache', 'server.jar', 'https://fill-data.papermc.io/server.jar',
                               algorithm, hashlib.new(algorithm, content).hexdigest(), FILL_HOSTS)

    def test_corruption_is_not_published_and_conflicting_cache_is_preserved(self):
        with patch('pluginmatrix.artifacts.open_official', return_value=io.BytesIO(b'bad')):
            with self.assertRaisesRegex(ProviderError, 'checksum'):
                self.download()
        self.assertFalse((self.root/'cache/server.jar').exists())
        (self.root/'cache/server.jar').write_bytes(b'old')
        with patch('pluginmatrix.artifacts.open_official') as network:
            with self.assertRaisesRegex(ProviderError, 'checksum'):
                self.download()
            network.assert_not_called()
        self.assertEqual((self.root/'cache/server.jar').read_bytes(), b'old')

    def test_concurrent_download_has_one_writer_and_sha256_receipt(self):
        with patch('pluginmatrix.artifacts.open_official', side_effect=lambda *a: io.BytesIO(b'fixture')) as network:
            with ThreadPoolExecutor(max_workers=4) as pool:
                results = list(pool.map(lambda _: self.download('md5'), range(4)))
        self.assertEqual(network.call_count, 1)
        self.assertEqual(len(set(results)), 1)
        self.assertEqual(results[0][1], hashlib.sha256(b'fixture').hexdigest())
        self.assertEqual(json.loads((self.root/'cache/server.jar.sha256.json').read_text())['sha256'], results[0][1])

    def test_cache_receipt_conflict_and_hardlink_lock_are_rejected(self):
        cache = self.root/'cache'; cache.mkdir()
        (cache/'server.jar').write_bytes(b'fixture')
        (cache/'server.jar.sha256.json').write_text(json.dumps({'sha256': '0'*64}))
        with self.assertRaisesRegex(ProviderError, 'receipt'):
            self.download()
        source = self.root/'input'; source.write_bytes(b'keep')
        os.link(source, cache/'server.jar.lock-alias')
        from pluginmatrix.locking import file_lock
        with self.assertRaises(ValueError):
            with file_lock(cache/'server.jar.lock-alias'):
                pass
        self.assertEqual(source.read_bytes(), b'keep')

    def test_namespace_and_artifact_identity_are_separate(self):
        identities = []
        for kind in ('paper', 'purpur', 'folia'):
            identities.append(get_provider(kind).cache_identity(ServerSpec(kind, '1.21.4'), {'resolved_build': 1, 'jar_sha256': 'a'*64}))
        self.assertEqual(len(set(identities)), 3)

    def test_folia_missing_declaration_is_specific_without_downloading(self):
        target = plugin(self.root/'target.jar')
        with patch('pluginmatrix.providers.read_json') as network, patch('pluginmatrix.runtime.start_process') as start:
            result = verify(target, '1.21.4', '21', self.root/'runs', self.root/'cache', 2, 1, server=ServerSpec('folia', '1.21.4'))
        self.assertEqual(result.result, 'PLUGIN_UNSUPPORTED')
        self.assertEqual(result.failure_stage, 'provider_preflight')
        self.assertTrue(result.metadata['server']['regionized_runtime'])
        network.assert_not_called(); start.assert_not_called()

    def test_both_descriptor_formats_and_ambiguous_folia_declarations(self):
        for descriptor in ('plugin.yml', 'paper-plugin.yml'):
            path = self.root/'plugin.jar'
            with zipfile.ZipFile(path, 'w') as jar:
                jar.writestr(descriptor, 'name: Example\nversion: 1\nmain: example.Main\nfolia-supported: true\n')
                jar.writestr('example/Main.class', b'\xca\xfe\xba\xbe\x00\x00\x00\x3d')
            metadata, _ = inspect_plugin(path)
            self.assertTrue(metadata['folia_supported'])
            self.assertEqual(metadata['plugin_descriptor'], descriptor)
        for extra in ('folia-supported: "true"', 'folia-supported: true\nfolia-supported: false', 'folia-supported: yes'):
            with self.assertRaises(PreflightError):
                inspect_plugin(plugin(self.root/'bad.jar', extra=extra))

    def test_local_identity_and_input_protection_including_aliases(self):
        jar = plugin(self.root/'server.jar')
        spec = parse_server({'type': 'custom', 'version': '1.21.4', 'name': 'My Server', 'jar': str(jar), 'runtime': 'paperclip', 'metadata': {'owner': 'local'}})
        with patch('pluginmatrix.providers.read_json') as network:
            path, info = get_provider('local').prepare(spec, self.root/'cache')
        self.assertEqual(path, jar)
        self.assertFalse(info['official'])
        self.assertEqual(info['server_type'], 'local')
        self.assertEqual(info['jar_sha256'], hashlib.sha256(jar.read_bytes()).hexdigest())
        network.assert_not_called()
        original = jar.read_bytes()
        target = plugin(self.root/'target.jar')
        result = verify(target, spec.version, '21', self.root, self.root/'cache', 2, 1, server=spec)
        self.assertEqual(result.result, 'ENVIRONMENT_INVALID')
        alias = self.root/'report.json'; os.link(jar, alias)
        with self.assertRaises(ValueError):
            write_report(result, alias)
        self.assertEqual(jar.read_bytes(), original)

    def test_unknown_local_contract_and_mixed_legacy_fields_are_errors(self):
        for raw in ({'type': 'unknown', 'version': '1.21.4'}, {'type': 'local', 'version': '1.21.4', 'name': 'custom', 'jar': 'server.jar', 'runtime': 'magic'},
                    {'type': 'paper', 'version': '../x'}, {'type': 'paper', 'version': '1.21.4', 'args': ['--plugins', '/outside']}):
            with self.assertRaises(ValueError):
                parse_server(raw)

    def test_local_bukkit_does_not_allow_remapped_codesource(self):
        target = self.root/'plugins/target.jar'; target.parent.mkdir(); target.write_bytes(b'x')
        remapped = target.parent/'.paper-remapped/target.jar'; remapped.parent.mkdir(); remapped.write_bytes(b'x')
        spec = ServerSpec('local', '1.21.4', jar=self.root/'server.jar', name='Custom', runtime='bukkit')
        evidence = RuntimeEvidence('Example', expected_source=target,
                                   allowed_sources=get_provider('local').allowed_sources(spec, target), provider_type='local')
        evidence.observe_probe({'target_present': True, 'target_name': 'Example', 'target_source': str(remapped)}, 0)
        self.assertIsNotNone(evidence.direct_runtime_error)

    def test_target_logger_cannot_manufacture_server_ready(self):
        evidence = RuntimeEvidence('Example')
        evidence.observe_line('[Example] Done (1.0s)!', 0)
        self.assertFalse(evidence.server_ready)

    def test_local_jar_changed_after_resolution_is_rejected_before_start(self):
        target = plugin(self.root/'target.jar')
        local = plugin(self.root/'server.jar', 'Server')
        original_hash = hashlib.sha256(local.read_bytes()).hexdigest()
        spec = ServerSpec('local', '1.21.4', jar=local, name='Mine', runtime='paperclip')
        def prepare(*args):
            local.write_bytes(b'changed')
            return local, {'jar_sha256': original_hash}
        with patch('pluginmatrix.providers.LocalProvider.prepare', side_effect=prepare), patch('pluginmatrix.runtime.resolve_java', return_value=('java', '21.0.1')), patch('pluginmatrix.runtime.start_process') as start:
            result = verify(target, '1.21.4', '21', self.root/'runs', self.root/'cache', 2, 1, server=spec)
        self.assertEqual(result.result, 'ENVIRONMENT_INVALID')
        self.assertIn('changed after provider resolution', result.reason)
        start.assert_not_called()
