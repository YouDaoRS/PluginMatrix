"""Explicit network/real JVM gate; excluded from ordinary offline discovery.

Builds only project-owned fixtures and retains reports, summaries and raw logs.
Run with a preinstalled JDK 21: python -m tests.real_provider_gate --java /path/java
"""
import argparse
import importlib.util
import json
import os
import tempfile
from dataclasses import replace
from pathlib import Path

from pluginmatrix.application import run_single, run_matrix, RunControl
from pluginmatrix.files import atomic_json
from pluginmatrix.matrix import MatrixConfig, MatrixEnvironment
from pluginmatrix.paper import ensure_paper
from pluginmatrix.providers import ServerSpec, get_provider
from pluginmatrix.probe import resolve_javac
from pluginmatrix.runtime import resolve_java
from pluginmatrix.github_summary import render_job_summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--java', default='21')
    parser.add_argument('--cache', type=Path, default=Path('.pluginmatrix/cache'))
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    root = args.output or Path(tempfile.mkdtemp(prefix='pluginmatrix-06-gate-'))
    root.mkdir(parents=True, exist_ok=True)
    root = root.resolve()
    print(f'GATE_ROOT={root}', flush=True)
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as out:
            out.write(f'gate_root={root}\n')
    java, version = resolve_java(args.java)
    paper, _ = ensure_paper('1.21.4', args.cache, 232)
    source = Path(__file__).resolve().parents[1]
    module_spec = importlib.util.spec_from_file_location('fixture_builder', source/'ci-fixtures/build_fixtures.py')
    builder = importlib.util.module_from_spec(module_spec); module_spec.loader.exec_module(builder)
    fixtures = root/'fixtures'; fixtures.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='pluginmatrix-gate-compile-') as temporary:
        classpath = builder.paper_classpath(paper, Path(temporary))
        for name, filename in builder.FIXTURES.items():
            builder.build_fixture(source/'ci-fixtures', name, fixtures/filename, resolve_javac(java), classpath)
    events = root/'progress.jsonl'
    def observe(event):
        with events.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(event.to_dict())+'\n')
    specs = [ServerSpec('paper', '1.21.4', 232), ServerSpec('purpur', '1.21.4'), ServerSpec('folia', '1.21.4')]
    outcomes = []
    artifact_checks = []
    for spec in specs:
        for scenario, filename, expected in [
            ('success', 'PluginMatrixFoliaSuccess.jar' if spec.type == 'folia' else 'PluginMatrixSmoke.jar', 'PASS'),
            ('enable-failure', 'PluginMatrixFoliaEnableFailure.jar' if spec.type == 'folia' else 'PluginMatrixEnableFailure.jar', 'PLUGIN_ENABLE_FAILED')]:
            label = spec.type+'-'+scenario
            result = run_single(plugin=fixtures/filename, server=spec, java=java, work_root=root/'runs',
                                cache_dir=args.cache, timeout=180, stability=3, report_path=root/(label+'.json'),
                                html_path=root/(label+'.html'), control=RunControl(observe))
            outcome = {'scenario': label, 'expected': expected, 'verdict': result.result, 'reason': result.reason,
                       'report': result.report_path, 'source': result.metadata.get('runtime_probe', {}).get('target_source')}
            artifact_checks.append({
                'scenario': label,
                'json': Path(result.report_path).is_file() if result.report_path else False,
                'html': (root/(label+'.html')).is_file(),
                'server_log': Path(result.log_path).is_file() if result.log_path else False,
            })
            outcomes.append(outcome)
            print(json.dumps(outcome), flush=True)
            atomic_json(root/'gate-summary.json', {'java': version, 'results': outcomes})
    result = run_single(plugin=fixtures/'PluginMatrixFoliaUnsupported.jar', server=specs[2], java=java,
                        work_root=root/'runs', cache_dir=args.cache, report_path=root/'folia-unsupported.json')
    outcomes.append({'scenario': 'folia-unsupported', 'expected': 'PLUGIN_UNSUPPORTED', 'verdict': result.result})
    matrix_source = root/'gate-config.json'
    matrix_source.write_text('{}')
    for parallel in (1, 3):
        config = MatrixConfig(matrix_source, fixtures/'PluginMatrixFoliaSuccess.jar',
                              tuple(MatrixEnvironment(s.version, java, s.build, s) for s in specs),
                              root/'runs', args.cache.resolve(), root/f'matrix-{parallel}.json',
                              timeout=180, stability_window=3, max_parallel=parallel,
                              html_path=root/f'matrix-{parallel}.html')
        report = run_matrix(config, control=RunControl(observe))
        summary_path = root/f'matrix-{parallel}-summary.md'
        summary_path.write_text(render_job_summary(config.report_path), encoding='utf-8')
        artifacts_available = all(
            all(entry['artifact_availability'].values())
            and Path(entry['artifacts']['runtime_report']).name == 'result.json'
            for entry in report['environments']
        )
        artifact_checks.append({
            'scenario': f'matrix-{parallel}',
            'json': config.report_path.is_file(),
            'html': config.html_path.is_file(),
            'summary': summary_path.is_file() and bool(summary_path.read_text(encoding='utf-8').strip()),
            'runtime_artifacts': artifacts_available,
        })
        for entry in report['environments']:
            outcomes.append({'scenario': f'matrix-{parallel}-'+entry['requested']['server']['type'],
                             'expected': 'PASS', 'verdict': entry['verdict'], 'reason': entry['reason']})
        print(f'matrix-{parallel}: {report["summary"]}', flush=True)
    local = ServerSpec('local', '1.21.4', jar=paper.resolve(), name='User supplied test JAR', runtime='paperclip')
    # Input outside all mutable roots, even when supplied from another existing cache.
    from pluginmatrix.files import atomic_copy, sha256_file
    local_jar = fixtures/'local-server.jar'; atomic_copy(paper, local_jar)
    local = replace(local, jar=local_jar)
    before = sha256_file(local_jar)
    result = run_single(plugin=fixtures/'PluginMatrixSmoke.jar', server=local, java=java, work_root=root/'runs',
                        cache_dir=args.cache, timeout=180, stability=3, report_path=root/'local.json', html_path=root/'local.html')
    outcomes.append({'scenario': 'local', 'expected': 'PASS', 'verdict': result.result,
                     'input_unchanged': sha256_file(local_jar) == before, 'official': result.metadata['server']['official']})
    artifact_checks.append({'scenario': 'local', 'json': (root/'local.json').is_file(),
                            'html': (root/'local.html').is_file(),
                            'server_log': Path(result.log_path).is_file() if result.log_path else False})
    remapped = all(o.get('source') and Path(o['source']).parent.name == '.paper-remapped'
                   for o in outcomes if o['scenario'].endswith('-success'))
    progress_kinds = {json.loads(line)['kind'] for line in events.read_text(encoding='utf-8').splitlines() if line}
    progress_complete = {'matrix_started', 'environment_started', 'server_started', 'plugin_enabled',
                         'stability_progress', 'environment_completed', 'matrix_completed'} <= progress_kinds
    artifacts_complete = all(all(value for key, value in check.items() if key != 'scenario')
                             for check in artifact_checks)
    summary = {'java': version, 'results': outcomes, 'artifact_checks': artifact_checks,
               'remapped_sources_verified': remapped, 'progress_events_verified': progress_complete,
               'passed': (all(o['verdict'] == o['expected'] for o in outcomes)
                          and remapped and progress_complete and artifacts_complete)}
    atomic_json(root/'gate-summary.json', summary)
    print(json.dumps(summary), flush=True)
    return 0 if summary['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
