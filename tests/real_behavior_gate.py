"""Explicit real-JVM behavioral core Gate; no release, UI or packaging operations."""
import argparse
import importlib.util
import json
import tempfile
import threading
from pathlib import Path

from pluginmatrix.application import run_single, run_matrix
from pluginmatrix.behavior import parse_behavior
from pluginmatrix.control import RunControl
from pluginmatrix.files import atomic_json
from pluginmatrix.matrix import MatrixConfig, MatrixEnvironment, matrix_exit_code
from pluginmatrix.paper import ensure_paper
from pluginmatrix.probe import resolve_javac
from pluginmatrix.providers import ServerSpec
from pluginmatrix.runtime import resolve_java


def checks():
    return [
        {'id': 'command', 'type': 'command_registered', 'name': 'pluginmatrixbehavior:pmbehavior'},
        {'id': 'permission', 'type': 'permission_registered', 'name': 'pluginmatrix.behavior'},
        {'id': 'service', 'type': 'service_registered', 'name': 'pluginmatrix.fixtures.BehaviorFixture$FixtureService'},
        {'id': 'once', 'type': 'console_command', 'name': 'pluginmatrixbehavior:pmbehavior', 'args': ['once']},
        {'id': 'wait', 'type': 'wait', 'seconds': .2, 'timeout': 3},
        {'id': 'count-one', 'type': 'console_command', 'name': 'pluginmatrixbehavior:pmbehavior', 'args': ['count-one']},
        {'id': 'remove', 'type': 'console_command', 'name': 'pluginmatrixbehavior:pmbehavior', 'args': ['unregister']},
        {'id': 'removed', 'type': 'service_registered', 'name': 'pluginmatrix.fixtures.BehaviorFixture$FixtureService', 'expect': False},
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--java', default='17')
    parser.add_argument('--minecraft', default='1.20.1')
    parser.add_argument('--build', type=int, default=196)
    parser.add_argument('--provider', choices=['paper', 'purpur', 'folia', 'local'], default='paper')
    parser.add_argument('--cache', type=Path, default=Path('.pluginmatrix/cache'))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--scenarios', nargs='+', default=['success', 'false', 'exception', 'disable', 'hang', 'cancel', 'missing', 'matrix'])
    args = parser.parse_args()
    root = (args.output or Path(tempfile.mkdtemp(prefix='pluginmatrix-08-behavior-'))).resolve()
    root.mkdir(parents=True, exist_ok=True)
    print('GATE_ROOT=' + str(root), flush=True)
    java, version = resolve_java(args.java)
    paper, _ = ensure_paper(args.minecraft, args.cache, args.build)
    source = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location('fixtures', source/'ci-fixtures/build_fixtures.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    fixture = root/'PluginMatrixBehavior.jar'
    with tempfile.TemporaryDirectory() as directory:
        builder.build_fixture(source/'ci-fixtures', 'behavior', fixture, resolve_javac(java), builder.paper_classpath(paper, Path(directory)))
    server = ServerSpec(args.provider, args.minecraft, args.build if args.provider == 'paper' else None)
    if args.provider == 'local':
        from pluginmatrix.files import atomic_copy
        local = root/'local-server.jar'
        atomic_copy(paper, local)
        server = ServerSpec('local', args.minecraft, jar=local, name='Gate local Paper', runtime='paperclip')
    outcomes = []
    def record(scenario, runtime, behavior, expected, report):
        item = dict(scenario=scenario, runtime=runtime, behavior=behavior, expected_behavior=expected,
                    report=str(report), passed=runtime == 'PASS' and behavior == expected)
        outcomes.append(item)
        atomic_json(root/'gate-summary.json', {'java': version, 'server': server.to_dict(), 'results': outcomes})
        print(json.dumps(item), flush=True)
    for scenario in args.scenarios:
        entries = checks()
        expected = 'PASS'
        if scenario == 'success' and args.provider == 'folia':
            entries = entries[:5]  # only the command is unsupported, read-only registries still pass
            expected = 'UNSUPPORTED'
        elif scenario in ('matrix', 'matrix-cancel'):
            config_path = root/'matrix-source.json'
            config_path.write_text('{}')
            # Use distinct official environments with existing bootstrap caches.
            # Local bootstrap downloads are deliberately not seeded by the verifier.
            second = ServerSpec('paper', '1.20.4', 499) if args.minecraft == '1.20.1' else ServerSpec('purpur', args.minecraft)
            servers = [server, second]
            waiting = set()
            if scenario == 'matrix-cancel':
                entries = [{'id': 'wait', 'type': 'wait', 'seconds': 20, 'timeout': 25}]
            def observe_matrix(event):
                if scenario == 'matrix-cancel' and event.kind == 'behavior_check_started':
                    waiting.add(event.environment_index)
                    if len(waiting) == 2:
                        matrix_control.cancel()
            matrix_control = RunControl(observe_matrix)
            config = MatrixConfig(config_path, fixture, tuple(MatrixEnvironment(s.version, java, s.build, s) for s in servers),
                                  root/'runs', args.cache.resolve(), root/'matrix.json', timeout=180, stability_window=2,
                                  max_parallel=2, behavior=parse_behavior({'schema': 1, 'checks': entries}))
            report = run_matrix(config, control=matrix_control)
            for entry in report['environments']:
                record(scenario + '-' + entry['id'], entry['runtime_verdict'], entry['behavior']['verdict'],
                       'CANCELLED' if scenario == 'matrix-cancel' else 'PASS', entry['runtime_report'])
            assert matrix_exit_code(report) == (1 if scenario == 'matrix-cancel' else 0)
            continue
        elif scenario != 'success':
            action = {'false': 'spoof-log', 'exception': 'throw', 'disable': 'disable', 'hang': 'hang', 'cancel': 'hang'}.get(scenario, 'ok')
            entries = [{'id': scenario, 'type': 'console_command', 'name': 'pluginmatrixbehavior:pmbehavior',
                        'args': [action], 'timeout': 1 if scenario == 'hang' else 5}]
            expected = {'false': 'FAIL', 'exception': 'ERROR', 'disable': 'ERROR', 'hang': 'TIMEOUT', 'cancel': 'CANCELLED', 'missing': 'FAIL', 'foreign': 'ERROR'}[scenario]
            if scenario == 'missing':
                entries = [{'id': 'missing', 'type': 'command_registered', 'name': 'missing'}]
            if scenario == 'foreign':
                entries = [{'id': 'foreign', 'type': 'console_command', 'name': 'stop', 'expect': False}]
        timer = None
        def observe(event):
            nonlocal timer
            if scenario == 'cancel' and event.kind == 'behavior_check_started':
                timer = threading.Timer(.25, control.cancel)
                timer.start()
        control = RunControl(observe)
        result = run_single(plugin=fixture, server=server, java=java, cache_dir=args.cache, work_root=root/'runs',
                            timeout=180, stability=2, behavior={'schema': 1, 'checks': entries}, control=control,
                            report_path=root/(scenario+'.json'))
        if timer:
            timer.join()
        record(scenario, result.result, result.behavior['verdict'], expected, result.report_path)
        assert Path(result.log_path).is_file()
        if result.behavior['verdict'] in ('PASS', 'FAIL', 'UNSUPPORTED'):
            assert result.behavior['post_health']['status'] == 'PASS'
    return 0 if all(item['passed'] for item in outcomes) else 1


if __name__ == '__main__':
    raise SystemExit(main())
