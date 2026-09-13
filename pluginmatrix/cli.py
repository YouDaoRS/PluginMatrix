from __future__ import annotations

import argparse
from pathlib import Path

from . import __version__
from .matrix import (
    MatrixConfigError,
    load_matrix_config,
    matrix_exit_code,
    run_matrix,
    validate_matrix_preconditions,
)
from .runtime import verify, write_report
from .files import validate_output_paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pluginmatrix", description="Verify a Minecraft Paper plugin in a real server.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    test = subparsers.add_parser("test", help="run one plugin against one Paper/Java environment")
    test.add_argument("--plugin", required=True, type=Path)
    test.add_argument("--paper", required=True, help="Minecraft/Paper version, e.g. 1.20.1")
    test.add_argument("--paper-build", type=int, help="pin an exact Paper build for reproducible runs")
    test.add_argument("--java", required=True, help="Java major version (17) or executable path/name")
    test.add_argument("--dependency", action="append", type=Path, default=[], help="local dependency plugin JAR; repeatable")
    test.add_argument("--work-dir", type=Path, default=Path(".pluginmatrix/runs"))
    test.add_argument("--cache-dir", type=Path, default=Path(".pluginmatrix/cache"))
    test.add_argument("--timeout", type=int, default=120)
    test.add_argument("--stability-window", type=int, default=5)
    test.add_argument("--report", type=Path)
    matrix = subparsers.add_parser("matrix", help="run one plugin across multiple Paper/Java environments")
    matrix.add_argument("config", type=Path, help="JSON matrix configuration file")
    return parser


def _print_result(result) -> None:
    print(f"Paper {result.metadata.get('requested_paper')} / Java {result.metadata.get('requested_java')}")
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
    if args.command == "matrix":
        config = None
        try:
            config = load_matrix_config(args.config)
            preflight = validate_matrix_preconditions(config)
            print("PluginMatrix Compatibility Matrix")
            print(f"\nPlugin: {config.plugin.name}")

            def progress(index, total, environment):
                print(f"\n[{index}/{total}] Paper {environment.paper} / Java {environment.java}")

            report = run_matrix(config, progress=progress, preflight=preflight)
            _print_matrix_result(report, config.report_path)
            return matrix_exit_code(report)
        except MatrixConfigError as exc:
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
        if args.timeout <= 0 or args.stability_window <= 0:
            raise ValueError('timeout and stability-window must be positive')
        validate_output_paths(args.work_dir, args.cache_dir, [args.plugin, *args.dependency], report_path)
    except (OSError, ValueError) as exc:
        print(f'Configuration error: {exc}')
        return 2
    result = verify(
        plugin=args.plugin.resolve(),
        paper_version=args.paper,
        java=args.java,
        work_root=args.work_dir.resolve(),
        cache_dir=args.cache_dir.resolve(),
        timeout=args.timeout,
        stability=args.stability_window,
        dependencies=[path.resolve() for path in args.dependency],
        paper_build=args.paper_build,
    )
    if report_path is None:
        if not result.workdir:
            _print_result(result)
            return 1
        report_path = Path(result.workdir) / "result.json"
    try:
        write_report(result, report_path)
    except (OSError, ValueError) as exc:
        _print_result(result)
        print(f'Could not save report {report_path}: {exc}')
        return 3
    _print_result(result)
    return 0 if result.result == "PASS" else 1
