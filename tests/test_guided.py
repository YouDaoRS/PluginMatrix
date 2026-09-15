import io
import json
import struct
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from pluginmatrix import application
from pluginmatrix.analysis import analyze_plugin
from pluginmatrix.behavior import parse_behavior
from pluginmatrix.matrix import parse_matrix_config, load_matrix_config, validate_matrix_preconditions
from pluginmatrix.profiles import resolve_profile
from pluginmatrix.recommendations import recommend_environment, java_baseline


def make_plugin(path, name='Example', extra='', descriptor='plugin.yml', major=61):
    with zipfile.ZipFile(path, 'w') as jar:
        jar.writestr(descriptor, f'name: {name}\nversion: 1.0\nmain: example.Main\napi-version: "1.20"\n' + extra)
        jar.writestr('example/Main.class', b'\xca\xfe\xba\xbe' + struct.pack('>HH', 0, major))
    return path


class GuidedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.jar = make_plugin(self.root/'Example.jar', extra='''commands:
  wipe:
    description: Deletes all player data
    aliases: [destroy, erase]
    permission: example.admin
permissions:
  example.admin:
    default: op
  example.*:
    default: false
''')
        self.env = {'server': {'type': 'paper', 'version': '1.20.1', 'build': 196}, 'java': '17'}
        self.source = self.root/'config.json'

    def raw(self, **values):
        return {'plugin': str(self.jar), 'environments': [self.env], **values}

    def test_analysis_never_invokes_or_suggests_commands(self):
        with patch('pluginmatrix.runtime.resolve_java', side_effect=AssertionError('must be static')):
            result = analyze_plugin(self.jar)
        self.assertTrue(result['valid'])
        self.assertEqual(result['plugin']['commands'][0]['aliases'], ['destroy', 'erase'])
        self.assertEqual(result['plugin']['permissions'][0]['default'], 'op')
        self.assertEqual(result['plugin']['bytecode']['max_base_java'], 17)
        plan = parse_behavior(result['suggestions']['behavior']).to_dict()
        self.assertEqual([c['type'] for c in plan['checks']], ['command_registered', 'permission_registered'])
        self.assertEqual(plan['checks'][0]['name'], 'example:wipe')
        self.assertTrue(result['suggestions']['omitted'])  # wildcard is not representable by Behavior schema
        self.assertTrue(result['suggestions']['requires_review'])

    def test_unsupported_yaml_is_incomplete_and_does_not_produce_guessed_commands(self):
        make_plugin(self.jar, extra='commands: {wipe: {description: "delete"}}\n')
        result = analyze_plugin(self.jar)
        self.assertTrue(result['valid'])  # existing runtime preflight semantics are unchanged
        self.assertFalse(result['plugin']['analysis_complete'])
        self.assertIsNone(result['suggestions']['behavior'])
        with self.assertRaisesRegex(ValueError, 'strict'):
            application.prepare_configuration(plugin=self.jar, environments=[self.env],
                                              source_path=self.source, profile='strict')

    def test_duplicate_command_declarations_fail_closed_in_analysis(self):
        make_plugin(self.jar, extra='commands:\n  wipe: {}\n  Wipe: {}\n')
        result = analyze_plugin(self.jar)
        self.assertFalse(result['plugin']['analysis_complete'])
        self.assertEqual(result['plugin']['commands'], [])

    def test_block_aliases_and_permission_children_are_read_without_invocation(self):
        make_plugin(self.jar, extra='''commands:
  wipe:
    aliases:
      - erase
      - "destroy"
permissions:
  example.admin:
    default: op
    children:
      example.use: true
      example.ignore: false
''')
        metadata = analyze_plugin(self.jar)['plugin']
        self.assertTrue(metadata['analysis_complete'])
        self.assertEqual(metadata['commands'][0]['aliases'], ['erase', 'destroy'])
        self.assertEqual(metadata['permissions'][0]['children'], {'example.use': True, 'example.ignore': False})

    def test_paper_descriptor_dynamic_commands_are_unknown(self):
        make_plugin(self.jar, descriptor='paper-plugin.yml', extra='commands:\n  wipe: {}\n')
        result = analyze_plugin(self.jar)
        self.assertEqual(result['plugin']['commands'], [])
        self.assertIsNone(result['suggestions']['behavior'])
        make_plugin(self.jar, descriptor='paper-plugin.yml', extra='dependencies:\n  server:\n    Vault: {}\n')
        result = analyze_plugin(self.jar)
        self.assertFalse(result['valid'])
        self.assertIn('unsupported', result['errors'][0]['reason'])

    def test_required_optional_and_transitive_dependencies(self):
        make_plugin(self.jar, extra='depend: [API]\nsoftdepend: [Optional]\n')
        dependency = make_plugin(self.root/'API.jar', 'API', extra='depend: [Storage]\n')
        result = analyze_plugin(self.jar, [dependency])
        self.assertFalse(result['valid'])
        self.assertEqual(result['dependency_report']['errors'][0]['name'], 'Storage')
        storage = make_plugin(self.root/'Storage.jar', 'Store', extra='provides: [Storage]\n')
        result = analyze_plugin(self.jar, [dependency, storage])
        self.assertTrue(result['valid'])
        self.assertEqual(result['dependency_report']['warnings'][0]['name'], 'Optional')
        self.assertIn('Store', [e['resolved_plugin'] for e in result['dependency_report']['edges']])

    def test_identity_conflicts_and_required_cycles(self):
        dependency = make_plugin(self.root/'Other.jar', 'Other', extra='provides: [Example]\n')
        result = analyze_plugin(self.jar, [dependency])
        self.assertEqual(result['dependency_report']['errors'][0]['code'], 'IDENTITY_CONFLICT')
        make_plugin(self.jar, extra='depend: [Other]\n')
        make_plugin(dependency, 'Other', extra='depend: [Example]\n')
        result = analyze_plugin(self.jar, [dependency])
        self.assertEqual(result['dependency_report']['errors'][0]['code'], 'DEPENDENCY_CYCLE')

    def test_dependency_case_is_not_silently_guessed(self):
        make_plugin(self.jar, extra='depend: [Vault]\n')
        dependency = make_plugin(self.root/'Vault.jar', 'vault')
        graph = analyze_plugin(self.jar, [dependency])['dependency_report']
        self.assertFalse(graph['ready'])
        self.assertEqual(graph['errors'][0]['code'], 'DEPENDENCY_CASE_MISMATCH')

    def test_analysis_bounds_and_unsafe_descriptors(self):
        with zipfile.ZipFile(self.jar, 'w') as jar:
            jar.writestr('plugin.yml', 'x' * (1024 * 1024 + 1))
        self.assertFalse(analyze_plugin(self.jar)['valid'])
        make_plugin(self.jar, extra='folia-supported: "true"\n')
        self.assertFalse(analyze_plugin(self.jar)['valid'])
        with self.assertRaises(ValueError):
            analyze_plugin(self.jar, [self.jar] * 129)

    def test_legacy_and_v08_configuration_roundtrip(self):
        for behavior in (None, {'schema': 1, 'checks': [{'id': 'wait', 'type': 'wait', 'seconds': 1}]}):
            raw = {'plugin': str(self.jar), 'environments': [{'paper': '1.20.1', 'java': 17}]}
            if behavior:
                raw['behavior'] = behavior
            config = parse_matrix_config(raw, source_path=self.source)
            self.assertEqual((config.timeout, config.stability_window), (120, 5))
            self.assertNotIn('schema', config.to_dict())
            self.assertNotIn('profile', config.to_dict())
            self.assertEqual(parse_matrix_config(config.to_dict(), source_path=self.source).to_dict(), config.to_dict())
            self.assertEqual(config.behavior is not None, behavior is not None)

    def test_profile_defaults_and_explicit_behavior_are_preserved(self):
        config = parse_matrix_config(self.raw(schema=2, profile='standard'), source_path=self.source)
        self.assertEqual((config.timeout, config.stability_window), (180, 10))
        self.assertIsNone(config.behavior)  # profiles alone do not regenerate/execute suggestions
        prepared = application.prepare_configuration(plugin=self.jar, environments=[self.env], source_path=self.source)
        document = prepared['configuration']
        document['behavior']['checks'].pop()
        normalized = application.normalize_configuration(document, source_path=self.source)['configuration']
        self.assertEqual(normalized['behavior'], document['behavior'])
        self.assertEqual(normalized['profile'], {'id': 'standard', 'revision': 1})
        self.assertEqual(len(prepared['configuration_sha256']), 64)

    def test_suggestions_are_opt_in_and_quick_remains_runtime_only(self):
        for args in ({'profile': 'quick'}, {'use_suggestions': False}):
            prepared = application.prepare_configuration(plugin=self.jar, environments=[self.env],
                                                         source_path=self.source, **args)
            self.assertNotIn('behavior', prepared['configuration'])
        explicit = {'schema': 1, 'checks': [{'id': 'hold', 'type': 'wait', 'seconds': 1}]}
        prepared = application.prepare_configuration(plugin=self.jar, environments=[self.env],
                                                     source_path=self.source, behavior=explicit)
        self.assertEqual(prepared['configuration']['behavior'], parse_behavior(explicit).to_dict())

    def test_schema_evolution_rejects_unknown_versions_and_fields(self):
        for extra in ({'schema': True}, {'schema': 3}, {'schema': '2'},
                      {'profile': 'quick'}, {'schema': 2, 'profile': {'id': 'strict', 'revision': 2}},
                      {'schema': 2, 'profile': 'strict', 'unknown': 1}):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                parse_matrix_config(self.raw(**extra), source_path=self.source)
        with self.assertRaises(ValueError):
            resolve_profile({'id': 'quick', 'revision': True})
        self.source.write_text(json.dumps(self.raw())[:-1] + ', "plugin": "evil.jar"}')
        with self.assertRaisesRegex(ValueError, 'duplicate JSON'):
            load_matrix_config(self.source)

    def test_strict_and_matrix_require_concrete_environments(self):
        for profile, envs, options in (
            ('matrix', [self.env], {}),
            ('standard', [self.env, {**self.env, 'java': '21'}], {}),
            ('strict', [{'server': {'type': 'paper', 'version': '1.20.1'}, 'java': '17'}], {}),
            ('strict', [self.env], {'stability_window': 1}),
        ):
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                parse_matrix_config({'schema': 2, 'profile': profile, 'plugin': str(self.jar),
                                     'environments': envs, 'options': options}, source_path=self.source)
        strict = parse_matrix_config(self.raw(schema=2, profile='strict'), source_path=self.source)
        self.assertEqual(strict.stability_window, 30)

    def test_guided_missing_dependencies_block_before_java_or_network(self):
        make_plugin(self.jar, extra='depend: [Vault]\n')
        with patch('pluginmatrix.runtime.resolve_java', side_effect=AssertionError('must not run')):
            with self.assertRaisesRegex(ValueError, 'Vault'):
                application.prepare_configuration(plugin=self.jar, environments=[self.env], source_path=self.source)
        config = parse_matrix_config(self.raw(schema=2, profile='quick'), source_path=self.source)
        with self.assertRaisesRegex(ValueError, 'Vault'):
            validate_matrix_preconditions(config, java_resolver=lambda _: ('java', '17'), javac_resolver=lambda _: 'javac')

    def test_managed_configuration_never_downloads_and_preserves_identity(self):
        ident = 'temurin-17-windows-x64-' + 'a'*64
        raw = self.raw(schema=2)
        raw['environments'] = [{**self.env, 'java': {'managed': ident}}]
        raw['options'] = {'jdk_dir': 'jdks'}
        with patch('pluginmatrix.jdks.resolve_package', side_effect=AssertionError('no download')):
            config = parse_matrix_config(raw, source_path=self.source)
        self.assertEqual(config.environments[0].java, 'managed:' + ident)
        self.assertEqual(config.to_dict()['environments'][0]['java'], {'managed': ident})
        with self.assertRaisesRegex(ValueError, 'separate'):
            application.normalize_configuration({**raw, 'options': {'jdk_dir': '.pluginmatrix/cache'}},
                                                source_path=self.source)

    def test_recommendation_does_not_guess_target_or_future_java(self):
        analysis = analyze_plugin(self.jar)
        result = recommend_environment(analysis)
        self.assertFalse(result['ready'])
        self.assertIsNone(result['selection']['minecraft'])
        for version in ('99.1', '1.99', '26.2', 'snapshot', '1.21.999'):
            self.assertIsNone(java_baseline(version))
        self.assertEqual(java_baseline('1.20.1'), 17)
        result = recommend_environment(analysis, minecraft='1.19.4')
        self.assertTrue(any('api-version' in r for r in result['conflicts']))
        self.assertFalse(recommend_environment(analysis, minecraft='1.20.1', provider='folia')['ready'])

    def test_recommendation_requires_exact_catalog_and_jdk_match(self):
        analysis = analyze_plugin(self.jar)
        catalog = {'provider': 'paper', 'minecraft_version': '1.20.1', 'available': True, 'source': 'network',
                   'fetched_at': time.time(), 'builds': [{'id': 196, 'channel': 'STABLE'}], 'recommended_build': 196}
        runtimes = [{'path': 'jdk17', 'javac': 'javac17', 'major': 17, 'jdk': True},
                    {'path': 'jdk21', 'javac': 'javac21', 'major': 21, 'jdk': True}]
        result = recommend_environment(analysis, minecraft='1.20.1', catalog=catalog, java_runtimes=runtimes)
        self.assertTrue(result['ready'])
        self.assertEqual(result['selection']['java'], 'jdk17')
        self.assertEqual(result['selection']['build'], 196)
        for change in ({'source': 'stale_cache'}, {'minecraft_version': '1.21.4'}, {'provider': 'folia'},
                       {'fetched_at': 1}, {'fetched_at': float('nan')}):
            self.assertFalse(recommend_environment(analysis, minecraft='1.20.1',
                                                  catalog={**catalog, **change}, java_runtimes=runtimes)['ready'])
        catalog['builds'][0]['channel'] = 'ALPHA'
        self.assertFalse(recommend_environment(analysis, minecraft='1.20.1', catalog=catalog,
                                              java_runtimes=runtimes)['ready'])
        self.assertTrue(recommend_environment(analysis, minecraft='1.20.1', build=196, catalog=catalog,
                                             java_runtimes=runtimes)['ready'])
        make_plugin(self.jar, major=65)
        result = recommend_environment(analyze_plugin(self.jar), minecraft='1.20.1', catalog=catalog,
                                       build=196, java_runtimes=runtimes)
        self.assertFalse(result['ready'])
        self.assertTrue(any('bytecode' in r for r in result['unresolved']))

    def test_application_execution_uses_the_existing_matrix_entry(self):
        raw = self.raw(schema=2, profile='quick')
        with patch('pluginmatrix.application.run_matrix', return_value={'summary': 'same executor'}) as run:
            result = application.run_configuration(raw, source_path=self.source)
        self.assertEqual(result, {'summary': 'same executor'})
        self.assertEqual(run.call_args.args[0].profile.id, 'quick')

    def test_direct_config_cannot_forge_a_profile_policy(self):
        from dataclasses import replace
        from pluginmatrix.matrix import validate_matrix_paths
        config = parse_matrix_config(self.raw(schema=2, profile='strict'), source_path=self.source)
        forged = replace(config, profile=replace(config.profile, complete_analysis=False))
        with self.assertRaisesRegex(ValueError, 'immutable'):
            validate_matrix_paths(forged)

    def test_complete_cli_init_does_not_prompt_when_terminal_has_no_input(self):
        from contextlib import redirect_stdout
        from pluginmatrix.cli import main
        with patch('sys.stdin.isatty', return_value=True), \
                patch('builtins.input', side_effect=AssertionError('complete args must not prompt')), \
                redirect_stdout(io.StringIO()):
            code = main(['init', str(self.source), '--plugin', str(self.jar), '--minecraft', '1.20.1',
                         '--java', '17', '--profile', 'standard'])
        self.assertEqual(code, 0)
        document = json.loads(self.source.read_text())
        self.assertEqual(document['schema'], 2)
        self.assertEqual(document['profile']['id'], 'standard')
        self.assertIn('behavior', document)


if __name__ == '__main__':
    unittest.main()
