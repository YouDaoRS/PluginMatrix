from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

from . import __version__
from .application import (
    MatrixConfigError,
    load_matrix_config,
    matrix_exit_code,
    run_matrix,
    validate_matrix_preconditions,
)
from .application import run_single as verify, write_report
from . import application
from .providers import parse_server
from .terminal import print
from .files import validate_output_paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pluginmatrix", description="Verify a Minecraft plugin in a real, isolated server.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    test = subparsers.add_parser("test", help="run one plugin against one server/Java environment")
    test.add_argument("--plugin", required=True, type=Path)
    test.add_argument("--paper", help="legacy Minecraft/Paper version, e.g. 1.20.1")
    test.add_argument('--server', choices=['paper', 'purpur', 'folia', 'local', 'custom'])
    test.add_argument('--minecraft', help='Minecraft version for --server')
    test.add_argument('--build', help='fixed build integer or latest')
    test.add_argument('--server-jar', type=Path)
    test.add_argument('--server-name')
    test.add_argument('--runtime', choices=['paperclip', 'bukkit', 'folia'])
    test.add_argument('--heap-mb', type=int, default=1024)
    test.add_argument("--paper-build", type=int, help="pin an exact Paper build for reproducible runs")
    test.add_argument("--java", required=True, help="Java major version (17) or executable path/name")
    test.add_argument("--dependency", action="append", type=Path, default=[], help="local dependency plugin JAR; repeatable")
    test.add_argument("--work-dir", type=Path, default=Path(".pluginmatrix/runs"))
    test.add_argument("--cache-dir", type=Path, default=Path(".pluginmatrix/cache"))
    test.add_argument("--timeout", type=int, default=120)
    test.add_argument("--stability-window", type=int, default=5)
    test.add_argument("--report", type=Path)
    test.add_argument('--html', type=Path, help='static HTML report output')
    matrix = subparsers.add_parser("matrix", help="run one plugin across multiple server/Java environments")
    matrix.add_argument("config", type=Path, help="JSON matrix configuration file")
    matrix.add_argument('--max-parallel', type=int, help='bounded concurrency, 1 through 8 (default 1)')
    matrix.add_argument('--html', type=Path, help='override HTML report output path')
    providers = subparsers.add_parser('providers', help='inspect built-in provider metadata')
    providers.add_argument('--json', action='store_true')
    validate = subparsers.add_parser('validate', help='local preflight without server downloads or startup')
    validate.add_argument('config', type=Path)
    validate.add_argument('--network', action='store_true', help='also resolve official version/build metadata')
    validate.add_argument('--json', action='store_true')
    doctor = subparsers.add_parser('doctor', help='check Python, Java/JDK, disk, permissions and provider APIs')
    doctor.add_argument('--java', default='java')
    doctor.add_argument('--directory', type=Path, default=Path('.pluginmatrix'))
    doctor.add_argument('--offline', action='store_true')
    doctor.add_argument('--json', action='store_true')
    init = subparsers.add_parser('init', help='generate a Matrix JSON config without hand-writing JSON')
    init.add_argument('config', nargs='?', type=Path, default=Path('matrix.json'))
    init.add_argument('--plugin', type=Path)
    init.add_argument('--server', action='append', choices=['paper', 'purpur', 'folia', 'local', 'custom'])
    init.add_argument('--minecraft')
    init.add_argument('--build')
    init.add_argument('--java')
    init.add_argument('--server-jar', type=Path)
    init.add_argument('--server-name')
    init.add_argument('--runtime', choices=['paperclip', 'bukkit', 'folia'])
    init.add_argument('--max-parallel', type=int, default=1)
    init.add_argument('--force', action='store_true', help='explicitly replace an existing JSON config, never an input JAR')
    html = subparsers.add_parser('report', help='render saved JSON as static HTML without recalculating verdicts')
    html.add_argument('source', type=Path)
    html.add_argument('--html', required=True, type=Path)
    web = subparsers.add_parser('web', help='start the loopback-only local Web UI')
    web.add_argument('--port', type=int, default=8642, help='loopback TCP port; use 0 to select a free port')
    web.add_argument('--no-browser', action='store_true', help='print the local URL without opening a browser')
    web.add_argument('--state-dir', type=Path, default=Path('.pluginmatrix/web'))
    web.add_argument('--cache-dir', type=Path, default=Path('.pluginmatrix/cache'))
    return parser


def _print_result(result) -> None:
    server = result.metadata.get('server', {})
    print(f"{server.get('server_type', 'paper')} {server.get('minecraft_version', result.metadata.get('requested_paper'))} / Java {result.metadata.get('requested_java')}")
    if server:
        print(f"Build: {server.get('requested_build')} -> {server.get('resolved_build')}; SHA-256: {server.get('jar_sha256')}")
        print(f"Source: {server.get('download_url') or server.get('jar')}")
    print("\nPreflight")
    runtime_names = {"Server start", "Plugin discovered", "Plugin load", "Plugin enable", "Runtime probe", "Plugin stability"}
    for check in result.checks:
        if check.name in runtime_names:
            continue
        print(f"  {check.name:<18} {check.status:<5}" + (f" {check.detail}" if check.detail else ""))
    runtime_checks = [check for check in result.checks if check.name in runtime_names]
    if runtime_checks:
        print("\nRuntime")
        for check in runtime_checks:
            print(f"  {check.name:<18} {check.status:<7}" + (f" {check.detail}" if check.detail else ""))
    print(f"  Result             {result.result}")
    if result.failure_stage:
        print(f"  Failure stage      {result.failure_stage}")
    if result.reason:
        print(f"  Reason             {result.reason}")
    print(f"\nRESULT: {'PASS' if result.result == 'PASS' else 'FAIL'}")
    if result.report_path:
        print(f"Report: {result.report_path}")
    if result.log_path:
        print(f"Server log: {result.log_path}")
    if result.workdir:
        print(f"Run directory: {result.workdir}")


def _print_matrix_result(report: dict, report_path: Path) -> None:
    print("\nEnvironment                         Result")
    for environment in report["environments"]:
        print(f"{environment['id']:<35} {environment['verdict']}")
    summary = report["summary"]
    print(f"\nSummary: {summary['passed']} passed, {summary['failed']} failed")
    failures = [environment for environment in report["environments"] if environment.get("verdict") != "PASS"]
    if failures:
        print("\nFailures")
        for environment in failures:
            print(f"  {environment.get('id', 'unknown environment')}")
            print(f"    Verdict: {environment.get('verdict', 'UNKNOWN_FAILURE')}")
            print(f"    Failure stage: {environment.get('failure_stage') or 'unknown'}")
            if environment.get("reason"):
                print(f"    Reason: {environment['reason']}")
            artifacts = environment.get("artifacts") if isinstance(environment.get("artifacts"), dict) else {}
            availability = (
                environment.get("artifact_availability")
                if isinstance(environment.get("artifact_availability"), dict)
                else {}
            )
            primary = environment.get("primary_evidence")
            if primary:
                print(f"    Primary evidence: {primary}")
            if artifacts.get("runtime_report"):
                print(f"    Runtime report: {artifacts['runtime_report']}")
            if artifacts.get("server_log") and availability.get("server_log", True):
                print(f"    Server log: {artifacts['server_log']}")
            elif artifacts.get("server_log"):
                print("    Server log: not generated (failure occurred before server launch)")
            if artifacts.get("run_dir"):
                print(f"    Run directory: {artifacts['run_dir']}")
    print(f"\nMatrix report: {report_path}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == 'web':
        try:
            from .web import serve
            return serve(args.port, not args.no_browser, args.state_dir, args.cache_dir)
        except (OSError, ValueError) as exc:
            print(f'Could not start local Web UI: {exc}')
            return 2
    if args.command in {'init', 'validate', 'doctor', 'providers', 'report'}:
        try:
            return _utility(args)
        except (OSError, ValueError) as exc:
            print(f'Configuration error: {exc}')
            return 2
    if args.command == "matrix":
        config = None
        try:
            config = load_matrix_config(args.config)
            if args.max_parallel is not None:
                config = replace(config, max_parallel=args.max_parallel)
            if args.html:
                config = replace(config, html_path=args.html.absolute())
            preflight = validate_matrix_preconditions(config)
            print("PluginMatrix Compatibility Matrix")
            print(f"\nPlugin: {config.plugin.name}")

            def progress(index, total, environment):
                print(f"\n[{index}/{total}] {environment.server_spec.type} {environment.paper} / Java {environment.java}")

            report = run_matrix(config, progress=progress, preflight=preflight)
            _print_matrix_result(report, config.report_path)
            return matrix_exit_code(report)
        except (MatrixConfigError, ValueError) as exc:
            print(f"Matrix configuration error: {exc}")
            return 2
        except Exception as exc:
            print(f"PluginMatrix internal error: {type(exc).__name__}: {exc}")
            if config is not None:
                print(f"Intended Matrix report: {config.report_path}")
            return 3
    if args.command != "test":
        return 2
    report_path = args.report
    try:
        if args.paper and (args.server or args.minecraft or args.build or args.server_jar or args.runtime):
            raise ValueError('legacy --paper cannot be combined with --server/--minecraft/--build; choose one configuration style')
        if args.paper_build and not args.paper:
            raise ValueError('--paper-build requires --paper; use --build with --server')
        spec = _server(args, args.server or 'paper')
        if args.timeout <= 0 or args.stability_window <= 0:
            raise ValueError('timeout and stability-window must be positive')
        inputs = [args.plugin, *args.dependency, *([spec.jar] if spec.jar else [])]
        validate_output_paths(args.work_dir, args.cache_dir, inputs, report_path)
        if args.html:
            validate_output_paths(args.work_dir, args.cache_dir, [*inputs, *([report_path] if report_path else [])], args.html)
    except (OSError, ValueError) as exc:
        print(f'Configuration error: {exc}')
        return 2
    try:
        result = verify(
            plugin=args.plugin.resolve(), java=args.java,
            work_root=args.work_dir.resolve(), cache_dir=args.cache_dir.resolve(),
            timeout=args.timeout, stability=args.stability_window,
            dependencies=[path.resolve() for path in args.dependency], server=spec,
            report_path=report_path, html_path=args.html,
        )
    except (OSError, ValueError) as exc:
        print(f'Could not finish/save verification: {exc}')
        return 3
    if report_path is None:
        if not result.workdir:
            _print_result(result)
            return 1
        report_path = Path(result.workdir) / "result.json"
    try:
        if not result.report_path:
            write_report(result, report_path)
    except (OSError, ValueError) as exc:
        _print_result(result)
        print(f'Could not save report {report_path}: {exc}')
        return 3
    _print_result(result)
    return 0 if result.result == "PASS" else 1


def _server(args, kind):
    raw = {'type': kind, 'version': getattr(args, 'paper', None) or args.minecraft,
           'heap_mb': getattr(args, 'heap_mb', 1024)}
    if kind in ('local', 'custom'):
        if args.build:
            raise ValueError('local servers do not accept --build')
        raw.update(jar=str(args.server_jar) if args.server_jar else None, name=args.server_name, runtime=args.runtime)
    else:
        if args.server_jar or args.server_name or args.runtime:
            raise ValueError('--server-jar/--server-name/--runtime require --server local')
        build = getattr(args, 'paper_build', None) or args.build
        raw['build'] = int(build) if build and str(build).isdigit() else build
    return parse_server(raw)


def _utility(args):
    if args.command == 'init':
        if sys.stdin.isatty():
            args.plugin = args.plugin or Path(input('Plugin JAR path: '))
            args.server = args.server or [input('Provider (paper/purpur/folia/local) [paper]: ').strip() or 'paper']
            args.minecraft = args.minecraft or input('Minecraft version: ').strip()
            args.java = args.java or input('Java version or executable [21]: ').strip() or '21'
            if any(s in ('local', 'custom') for s in args.server):
                args.server_jar = args.server_jar or Path(input('Local server JAR: '))
                args.server_name = args.server_name or input('Declared server name: ').strip()
                args.runtime = args.runtime or input('Runtime contract (paperclip/bukkit/folia): ').strip()
        if not args.plugin or not args.minecraft or not args.java:
            raise ValueError('non-interactive init requires --plugin, --minecraft and --java')
        servers = [_server(args, kind) for kind in (args.server or ['paper'])]
        path = application.init_configuration(args.config, plugin=args.plugin, servers=servers,
                                              java=args.java, force=args.force, max_parallel=args.max_parallel)
        print(f'Created config: {path}')
        return 0
    if args.command == 'report':
        print(f'HTML report: {application.render_html_report(args.source, args.html)}')
        return 0
    if args.command == 'providers':
        result = {'schema': 1, 'providers': application.inspect_providers(), 'exit_code': 0}
    elif args.command == 'validate':
        result = application.validate_configuration(args.config, args.network)
    else:
        result = application.doctor(args.java, args.directory, not args.offline)
    if args.json:
        # json.dumps escapes terminal controls and keeps stdout machine-readable.
        sys.stdout.write(json.dumps(result, ensure_ascii=True, indent=2) + '\n')
    elif args.command == 'providers':
        for p in result['providers']:
            print(f"{p['type']}: {p['status']} - {', '.join(p['capabilities'])}")
            for key, value in p['config_fields'].items():
                print(f'  {key}: {value}')
            print(f"  {p['pass_scope']}")
    elif args.command == 'validate':
        print('Configuration valid' if result['valid'] else 'Configuration invalid')
        for error in result['errors']:
            print(f'  {error}')
    else:
        for check in result['checks']:
            print(f"{check['level']} {check['status']} {check['name']}: {check['detail']}")
    return result['exit_code']
