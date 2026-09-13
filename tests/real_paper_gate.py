"""Explicit local gate; never discovered by the offline unittest suite.

Run from a source checkout with a local, verified Paper JAR and JDK 17.
All builds and runs are stored in a new temporary directory. Existing bootstrap
cache files are copied before use. No third-party plugin is downloaded.
"""
import argparse
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from pluginmatrix.files import sha256_file
from pluginmatrix.probe import _extract_paper_libraries, resolve_javac
from pluginmatrix.runtime import resolve_java, verify, write_report


def build_fixture(root, paper, java, name, body):
    directory = root / name
    directory.mkdir()
    source = directory / f'{name}.java'
    source.write_text('package pluginmatrix.fixture;\n'
                      f'public final class {name} extends org.bukkit.plugin.java.JavaPlugin {{\n'
                      ' public void onEnable() {\n' + body + '\n }\n}\n')
    classes = directory / 'classes'; classes.mkdir()
    classpath = _extract_paper_libraries(paper, directory / 'libraries')
    subprocess.run([resolve_javac(java), '--release', '17', '-cp', classpath,
                    '-d', str(classes), str(source)], check=True, capture_output=True, timeout=60)
    jar = directory / f'{name}.jar'
    with zipfile.ZipFile(jar, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('plugin.yml', f'name: {name}\nversion: 1.0.0\nmain: pluginmatrix.fixture.{name}\napi-version: "1.20"\n')
        for path in classes.rglob('*.class'):
            archive.write(path, path.relative_to(classes).as_posix())
    return jar


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--paper-jar', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--java', default='17')
    parser.add_argument('--paper-version', default='1.20.1')
    parser.add_argument('--paper-build', type=int, default=196)
    parser.add_argument('--require-remapped', action='store_true')
    args = parser.parse_args()
    root = Path(tempfile.mkdtemp(prefix='pluginmatrix-051-gate-'))
    print(f'GATE_ROOT={root}', flush=True)
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as output:
            output.write(f'gate_root={root}\n')
    if (args.cache / 'runtime').is_dir():
        shutil.copytree(args.cache / 'runtime', root / 'cache/runtime')
    java, _ = resolve_java(args.java)
    paper = args.paper_jar.resolve()
    noise = build_fixture(root, paper, java, 'Noise', '''
        getServer().getScheduler().runTaskLater(this, () -> {
            getLogger().warning("java.io.IOException: optional integration unavailable");
            getLogger().warning("UnknownDependencyException: PluginMatrixSmoke for Noise");
            try { new java.io.FileOutputStream(java.io.FileDescriptor.out).write(new byte[]{(byte)255,10}); }
            catch (java.io.IOException failure) { throw new RuntimeException(failure); }
        }, 20L);
    ''')
    raw = build_fixture(root, paper, java, 'RawOutput', '''
        getServer().getScheduler().runTaskLater(this, () -> {
            try { new java.io.FileOutputStream(java.io.FileDescriptor.out).write(new byte[]{(byte)255,10}); }
            catch (java.io.IOException failure) { throw new RuntimeException(failure); }
        }, 20L);
        getServer().getScheduler().runTaskLater(this, () -> getServer().getPluginManager().disablePlugin(this), 80L);
    ''')
    fixtures = Path(__file__).resolve().parents[1] / 'ci-fixtures'
    scenarios = [('success', fixtures/'PluginMatrixSmoke.jar', [], 'PASS', 3),
                 ('enable-failure', fixtures/'PluginMatrixEnableFailure.jar', [], 'PLUGIN_ENABLE_FAILED', 3),
                 ('noise-invalid-utf8', fixtures/'PluginMatrixSmoke.jar', [noise], 'PASS', 3),
                 ('raw-late-disable', raw, [], 'PLUGIN_DISABLED', 6)]
    summary = []
    for label, plugin, dependencies, expected, stability in scenarios:
        result = verify(plugin, args.paper_version, args.java, root/'runs', root/'cache', 180, stability,
                        dependencies=dependencies, paper_jar=paper,
                        paper_metadata={'minecraft_version':args.paper_version,'paper_build':args.paper_build})
        write_report(result, root/f'{label}.json')
        write_report(result, Path(result.workdir)/'result.json')
        item = dict(scenario=label, expected=expected, verdict=result.result, report=result.report_path,
                    reason=result.reason, raw_invalid_utf8=b'\xff' in Path(result.log_path).read_bytes(),
                    windows=[event.__dict__ for event in result.evidence if event.kind.startswith('stability_window')])
        summary.append(item)
        print(json.dumps(item), flush=True)
        assert result.result == expected, item
        if args.require_remapped and expected == 'PASS':
            source = result.metadata['runtime_probe']['target_source']
            assert Path(source).parent.name == '.paper-remapped', source
        if label in ('noise-invalid-utf8', 'raw-late-disable'):
            assert item['raw_invalid_utf8'], item
        if label != 'enable-failure':
            assert any(event.kind == 'stability_window_completed' for event in result.evidence), item
    (root/'summary.json').write_text(json.dumps({'paper_sha256':sha256_file(paper),'results':summary},indent=2))
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as output:
            output.write(f'## Real Paper {args.paper_version} / build {args.paper_build}\n\n')
            for item in summary:
                output.write(f"- {item['scenario']}: {item['verdict']} (expected {item['expected']})\n")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
