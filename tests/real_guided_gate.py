"""Explicit v0.9 Gate: official managed JDK + real Paper, no fixture downloads.

Not part of offline discovery. Artifacts stay in a dedicated Gate directory.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import tempfile
from pathlib import Path

from pluginmatrix import application
from pluginmatrix.control import RunControl
from pluginmatrix.files import atomic_json
from pluginmatrix.jdks import JdkStore
from pluginmatrix.providers import ServerSpec
from pluginmatrix.paper import ensure_paper


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--cache', type=Path, default=Path('.pluginmatrix/cache'))
    parser.add_argument('--scenarios', nargs='+', choices=['quick', 'standard', 'strict', 'matrix'],
                        default=['quick', 'standard', 'strict', 'matrix'])
    parser.add_argument('--delete-jdk', action='store_true')
    args = parser.parse_args()
    root = (args.output or Path(tempfile.mkdtemp(prefix='pluginmatrix-09-guided-'))).resolve()
    root.mkdir(parents=True, exist_ok=True)
    print('GATE_ROOT=' + str(root), flush=True)
    summary = {'schema': 1, 'results': [], 'jdk': None}

    def record(event, **fields):
        item = {'event': event, **fields}
        summary['results'].append(item)
        atomic_json(root/'gate-summary.json', summary)
        print(json.dumps(item), flush=True)

    before = {key: os.environ.get(key) for key in ('PATH', 'JAVA_HOME', 'JDK_HOME')}
    preview = application.preview_managed_jdk(17)
    atomic_json(root/'jdk-preview.json', preview)
    record('jdk_preview', package=preview['package']['id'])
    installed = application.install_managed_jdk(17, root=root/'jdks', expected_id=preview['package']['id'],
                                                control=RunControl(lambda e: print(e.kind, flush=True)))
    summary['jdk'] = installed
    atomic_json(root/'jdk-install.json', installed)
    record('jdk_installed', cached=installed['cached'])
    store = JdkStore(root/'jdks')
    with store.lease(installed['id']) as jdk:
        assert jdk['major'] == 17
        record('jdk_integrity_and_selection', passed=True)
        try:
            store.delete(installed['id'])
        except ValueError as exc:
            assert 'in use' in str(exc)
            record('jdk_delete_during_use_refused', passed=True)
        else:
            raise AssertionError('JDK deletion succeeded while leased')
        paper, _ = ensure_paper('1.20.1', args.cache, 196)
        source = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location('fixtures', source/'ci-fixtures/build_fixtures.py')
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        fixture = root/'PluginMatrixBehavior.jar'
        with tempfile.TemporaryDirectory() as directory:
            builder.build_fixture(source/'ci-fixtures', 'behavior', fixture, jdk['javac'],
                                  builder.paper_classpath(paper, Path(directory)))
    analysis = application.analyze_plugin(fixture)
    atomic_json(root/'analysis.json', analysis)
    assert analysis['valid']
    assert {c['type'] for c in analysis['suggestions']['behavior']['checks']} == {
        'command_registered', 'permission_registered'}
    record('safe_static_suggestions', passed=True)
    recommendation = application.recommend_setup(plugin=fixture, minecraft='1.20.1', build=196,
                                                  network=True, cache_dir=args.cache, java_runtimes=[installed])
    atomic_json(root/'recommendation.json', recommendation)
    record('official_environment_recommendation', ready=recommendation['recommendation']['ready'],
           unresolved=recommendation['recommendation']['unresolved'])
    assert recommendation['recommendation']['ready']
    java = 'managed:' + installed['id']
    for profile in args.scenarios:
        environments = [{'server': {'type': 'paper', 'version': '1.20.1', 'build': 196}, 'java': java}]
        if profile == 'matrix':
            environments.append({'server': {'type': 'paper', 'version': '1.20.4', 'build': 499}, 'java': java})
        prepared = application.prepare_configuration(
            plugin=fixture, environments=environments, source_path=root/(profile+'-source.json'), profile=profile,
            options={'cache_dir': str(args.cache.resolve()), 'work_dir': str(root/'runs'),
                     'jdk_dir': str(root/'jdks'), 'report': str(root/(profile+'-result.json')),
                     'max_parallel': 2 if profile == 'matrix' else 1})
        atomic_json(root/(profile+'-source.json'), prepared['configuration'])
        control = RunControl(lambda e: print(json.dumps(e.to_dict()), flush=True))
        report = application.run_configuration(prepared['configuration'], source_path=root/(profile+'-source.json'),
                                               control=control)
        for environment in report['environments']:
            expected = 'NOT_RUN' if profile == 'quick' else 'PASS'
            passed = (environment['runtime_verdict'] == 'PASS'
                      and environment['behavior']['verdict'] == expected and environment['verification_passed'])
            record(profile, runtime=environment['runtime_verdict'], behavior=environment['behavior']['verdict'],
                   passed=passed, report=environment['runtime_report'])
            assert passed
            assert Path(environment['artifacts']['server_log']).is_file()
    assert before == {key: os.environ.get(key) for key in before}
    record('system_java_configuration_unchanged', passed=True)
    if args.delete_jdk:
        record('jdk_deleted', **application.delete_managed_jdk(installed['id'], root=root/'jdks'))
        assert not store.list()['jdks']
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
