from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from . import __version__
from .files import protect_inputs, atomic_json, reject_links, validate_output_paths
from .model import VerificationResult
from .preflight import PreflightError, inspect_plugin
from .probe import resolve_javac
from .runtime import resolve_java, verify, write_report


class MatrixConfigError(ValueError):
    """Raised when a matrix configuration is invalid before execution."""


@dataclass(frozen=True)
class MatrixEnvironment:
    paper: str
    java: str
    paper_build: int | None = None

    @property
    def environment_id(self) -> str:
        build = str(self.paper_build) if self.paper_build is not None else "auto"
        java = re.sub(r"[^A-Za-z0-9_.-]+", "-", self.java)
        paper = re.sub(r"[^A-Za-z0-9_.-]+", "-", self.paper)
        return f"paper-{paper}-java-{java}-build-{build}"

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {"paper": self.paper, "java": self.java}
        if self.paper_build is not None:
            value["paper_build"] = self.paper_build
        return value


@dataclass(frozen=True)
class MatrixConfig:
    source_path: Path
    plugin: Path
    environments: tuple[MatrixEnvironment, ...]
    work_dir: Path
    cache_dir: Path
    report_path: Path
    timeout: int = 120
    stability_window: int = 5

    def to_dict(self) -> dict[str, Any]:
        return {
            "plugin": str(self.plugin),
            "environments": [environment.to_dict() for environment in self.environments],
            "options": {
                "work_dir": str(self.work_dir),
                "cache_dir": str(self.cache_dir),
                "report": str(self.report_path),
                "timeout": self.timeout,
                "stability_window": self.stability_window,
            },
        }


def _require_mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MatrixConfigError(
            f"field '{label}' has value {value!r}; expected a JSON object. "
            f"Fix: set '{label}' to an object using {{ ... }}."
        )
    return value


def _resolve_path(value: object, base: Path, label: str, must_exist: bool = False) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise MatrixConfigError(
            f"field '{label}' has value {value!r}; expected a non-empty path. "
            f"Fix: set '{label}' to a path relative to {base} or to an absolute path."
        )
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base / path
    if not must_exist:
        try:
            reject_links(path)
        except ValueError as exc:
            raise MatrixConfigError(f"field '{label}': {exc}") from exc
        except OSError as exc:
            raise MatrixConfigError(
                f"field '{label}' path '{path}' is not writable: {exc}. "
                "Fix: choose an accessible path whose parents are directories."
            ) from exc
    path = path.resolve()
    if must_exist and not path.is_file():
        raise MatrixConfigError(
            f"field '{label}' has value {value!r}, resolved to '{path}'; expected an existing file. "
            f"Fix: paths in Matrix config are relative to '{base}'. In the hosted workflow, also make sure "
            "the config and plugin_jar inputs point to files committed to the selected branch."
        )
    return path


def load_matrix_config(path: Path) -> MatrixConfig:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise MatrixConfigError(
            f"field 'config' has value '{path}'; expected an existing JSON file. "
            "Fix: pass the Matrix config path, not its containing directory."
        )
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MatrixConfigError(
            f"field 'config' has invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}. "
            f"Current file: '{path}'. Fix: correct the JSON syntax and run the command again."
        ) from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise MatrixConfigError(
            f"field 'config' could not be read as UTF-8 JSON: '{path}' ({type(exc).__name__}: {exc}). "
            "Fix: make the file readable and save it as UTF-8."
        ) from exc
    document = _require_mapping(raw, "matrix config")
    plugin = _resolve_path(document.get("plugin"), path.parent, "plugin", must_exist=True)

    raw_environments = document.get("environments")
    if not isinstance(raw_environments, list) or not raw_environments:
        raise MatrixConfigError(
            f"field 'environments' has value {raw_environments!r}; expected a non-empty array. "
            "Fix: add at least one object with 'paper' and 'java'."
        )
    environments: list[MatrixEnvironment] = []
    seen: set[str] = set()
    for index, raw_environment in enumerate(raw_environments, start=1):
        item = _require_mapping(raw_environment, f"environment #{index}")
        paper = item.get("paper")
        java = item.get("java")
        if not isinstance(paper, str) or not re.fullmatch(r"\d+\.\d+(?:\.\d+)?", paper.strip()):
            raise MatrixConfigError(
                f"field 'environments[{index - 1}].paper' has value {paper!r}; expected a Paper/Minecraft "
                "version such as '1.20.1'. Fix: use a numeric Minecraft version supported by Paper."
            )
        paper = paper.strip()
        if isinstance(java, int) and not isinstance(java, bool):
            java = str(java)
        if not isinstance(java, str) or not java.strip():
            raise MatrixConfigError(
                f"field 'environments[{index - 1}].java' has value {java!r}; expected a Java major version "
                "or executable. Fix: use a value such as 17 or an available Java executable path."
            )
        java = java.strip()
        build = item.get("paper_build")
        if build is not None:
            if isinstance(build, bool) or not isinstance(build, int) or build <= 0:
                raise MatrixConfigError(
                    f"field 'environments[{index - 1}].paper_build' has value {build!r}; expected a positive "
                    "Paper build integer. Fix: remove the field for automatic stable-build selection or set a "
                    "build available for the requested Paper version."
                )
        environment = MatrixEnvironment(paper=paper, java=java, paper_build=build)
        if environment.environment_id in seen:
            raise MatrixConfigError(
                f"field 'environments[{index - 1}]' conflicts with an earlier environment after normalization: "
                f"'{environment.environment_id}'. Current value: {item!r}. Fix: remove the duplicate or choose "
                "a distinct Paper, Java, or paper_build value."
            )
        seen.add(environment.environment_id)
        environments.append(environment)

    options = _require_mapping(document.get("options", {}), "options")
    timeout = options.get("timeout", 120)
    stability = options.get("stability_window", 5)
    if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
        raise MatrixConfigError(
            f"field 'options.timeout' has value {timeout!r}; expected a positive integer number of seconds. "
            "Fix: use a value such as 120."
        )
    if isinstance(stability, bool) or not isinstance(stability, int) or stability <= 0:
        raise MatrixConfigError(
            f"field 'options.stability_window' has value {stability!r}; expected a positive integer "
            "number of seconds. Fix: use a value such as 5; zero is unsupported."
        )
    work_dir = _resolve_path(options.get("work_dir", ".pluginmatrix/runs"), path.parent, "options.work_dir")
    cache_dir = _resolve_path(options.get("cache_dir", ".pluginmatrix/cache"), path.parent, "options.cache_dir")
    report_path = _resolve_path(
        options.get("report", ".pluginmatrix/matrix-report.json"),
        path.parent,
        "options.report",
    )
    return MatrixConfig(
        source_path=path,
        plugin=plugin,
        environments=tuple(environments),
        work_dir=work_dir,
        cache_dir=cache_dir,
        report_path=report_path,
        timeout=timeout,
        stability_window=stability,
    )


def _check_writable_directory(path: Path, field: str) -> str | None:
    try:
        path.mkdir(parents=True, exist_ok=True)
        if not path.is_dir():
            return (
                f"field '{field}' resolves to '{path}', which is not a directory. "
                f"Fix: choose a creatable directory for '{field}'."
            )
        probe = path / f".pluginmatrix-write-test-{uuid.uuid4().hex}"
        try:
            probe.write_text("write test\n", encoding="utf-8")
        finally:
            probe.unlink(missing_ok=True)
    except OSError as exc:
        return (
            f"field '{field}' resolves to '{path}', which is not writable ({type(exc).__name__}: {exc}). "
            f"Fix: choose a writable directory for '{field}' or correct its permissions."
        )
    return None


def _check_report_path(path: Path) -> str | None:
    if not path.exists():
        return None
    if not path.is_file():
        return (
            f"field 'options.report' resolves to '{path}', which is not a file. "
            "Fix: choose a writable JSON file path."
        )
    try:
        with path.open("a", encoding="utf-8"):
            pass
    except OSError as exc:
        return (
            f"field 'options.report' resolves to existing file '{path}', which is not writable "
            f"({type(exc).__name__}: {exc}). Fix: correct its permissions or choose another report path."
        )
    return None


def _is_within(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory)
    except ValueError:
        return False
    return True


def validate_matrix_preconditions(
    config: MatrixConfig,
    java_resolver: Callable[[str], tuple[str, str]] = resolve_java,
    javac_resolver: Callable[[str], str | None] = resolve_javac,
) -> dict[str, Any]:
    """Validate local prerequisites without starting Paper or downloading artifacts."""

    errors: list[str] = []
    try:
        validate_output_paths(config.work_dir, config.cache_dir, [config.source_path, config.plugin], config.report_path)
    except ValueError as exc:
        raise MatrixConfigError(str(exc)) from exc
    if config.work_dir == config.cache_dir:
        errors.append(
            f"fields 'options.work_dir' and 'options.cache_dir' both resolve to '{config.work_dir}'. "
            "Expected separate run and download-cache directories. Fix: give the two fields distinct paths."
        )
    if (
        config.report_path.is_dir()
        or _is_within(config.report_path, config.work_dir)
        or _is_within(config.report_path, config.cache_dir)
    ):
        errors.append(
            f"field 'options.report' resolves to '{config.report_path}', which is a directory or is inside "
            "another output directory. Fix: choose a JSON file path outside 'work_dir' and 'cache_dir', such "
            "as '.pluginmatrix/matrix-report.json'."
        )
    else:
        report_error = _check_report_path(config.report_path)
        if report_error:
            errors.append(report_error)

    for field, directory in (
        ("options.work_dir", config.work_dir),
        ("options.cache_dir", config.cache_dir),
        ("options.report parent", config.report_path.parent),
    ):
        error = _check_writable_directory(directory, field)
        if error:
            errors.append(error)

    plugin_metadata: dict[str, Any] = {}
    try:
        plugin_metadata, _ = inspect_plugin(config.plugin)
    except PreflightError as exc:
        detail = next((check.detail for check in reversed(exc.checks) if check.status == "FAIL"), None)
        errors.append(
            f"field 'plugin' resolves to '{config.plugin}', but the plugin JAR failed preflight: {exc}"
            f"{f' ({detail})' if detail else ''}. Fix: provide a readable Paper plugin JAR with valid "
            "plugin.yml and main class metadata."
        )
    except OSError as exc:
        errors.append(
            f"field 'plugin' resolves to '{config.plugin}', but it could not be read "
            f"({type(exc).__name__}: {exc}). Fix: make the JAR readable or select another file."
        )

    java_runtimes: dict[str, dict[str, str]] = {}
    checked_java: set[str] = set()
    for environment in config.environments:
        if environment.java in checked_java:
            continue
        checked_java.add(environment.java)
        try:
            executable, runtime_version = java_resolver(environment.java)
        except (OSError, ValueError) as exc:
            errors.append(
                f"field 'java' has value {environment.java!r} for {environment.environment_id}; no compatible "
                f"Java runtime is available ({exc}). Fix: install the requested JDK and put java/javac on PATH, "
                "or set 'java' to the correct executable path. PluginMatrix does not download JDKs."
            )
        else:
            try:
                compiler = javac_resolver(executable)
            except OSError as exc:
                compiler = None
                compiler_error = f" ({type(exc).__name__}: {exc})"
            else:
                compiler_error = ""
            if not compiler:
                errors.append(
                    f"field 'java' has value {environment.java!r} for {environment.environment_id}; Java "
                    f"runtime '{executable}' is available but a matching JDK javac executable was not found"
                    f"{compiler_error}. "
                    "Fix: install a full JDK and ensure javac is beside java or available on PATH."
                )
                continue
            java_runtimes[environment.java] = {
                "executable": str(Path(executable).resolve()) if Path(executable).exists() else executable,
                "runtime_version": runtime_version,
                "javac": str(Path(compiler).resolve()) if Path(compiler).exists() else compiler,
            }

    if errors:
        raise MatrixConfigError("Matrix preflight failed:\n- " + "\n- ".join(errors))
    return {"plugin": plugin_metadata, "java_runtimes": java_runtimes}


def _environment_id(environment: MatrixEnvironment, result: VerificationResult) -> str:
    build = result.metadata.get("paper_build")
    if build is None:
        return environment.environment_id
    return f"paper-{environment.paper}-java-{re.sub(r'[^A-Za-z0-9_.-]+', '-', environment.java)}-build-{build}"


def _result_entry(environment: MatrixEnvironment, result: VerificationResult) -> dict[str, Any]:
    runtime_report = result.report_path
    artifact_paths = {
        "run_dir": result.workdir,
        "server_log": result.log_path,
        "runtime_report": runtime_report,
    }
    artifact_availability = {
        "run_dir": bool(result.workdir and Path(result.workdir).is_dir()),
        "server_log": bool(result.log_path and Path(result.log_path).is_file()),
        "runtime_report": bool(runtime_report and Path(runtime_report).is_file()),
    }
    primary_evidence = runtime_report or result.log_path or result.workdir
    if result.log_path and Path(result.log_path).is_file():
        primary_evidence = result.log_path
    return {
        "id": _environment_id(environment, result),
        "requested": environment.to_dict(),
        "resolved": {
            "paper": result.metadata.get("minecraft_version") or result.metadata.get("requested_paper"),
            "paper_build": result.metadata.get("paper_build"),
            "java": result.metadata.get("java_runtime_version") or result.metadata.get("requested_java"),
        },
        "verdict": result.result,
        "failure_stage": result.failure_stage,
        "reason": result.reason,
        "primary_evidence": primary_evidence,
        "runtime_report": runtime_report,
        "evidence": [
            {
                "kind": event.kind,
                "timestamp": event.timestamp,
                "source": event.source,
                "detail": event.detail,
            }
            for event in result.evidence
        ],
        "artifacts": artifact_paths,
        "artifact_availability": artifact_availability,
    }


def run_matrix(
    config: MatrixConfig,
    verifier: Callable[..., VerificationResult] = verify,
    progress: Callable[[int, int, MatrixEnvironment], None] | None = None,
    preflight: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validate_output_paths(config.work_dir, config.cache_dir, [config.source_path, config.plugin], config.report_path)
    results: list[dict[str, Any]] = []
    internal_errors = 0
    plugin_metadata: dict[str, Any] = {"plugin_jar": str(config.plugin)}
    if preflight and isinstance(preflight.get("plugin"), dict):
        plugin_metadata.update(preflight["plugin"])
    for index, environment in enumerate(config.environments, start=1):
        if progress:
            progress(index, len(config.environments), environment)
        try:
            result = verifier(
                plugin=config.plugin,
                paper_version=environment.paper,
                java=environment.java,
                paper_build=environment.paper_build,
                work_root=config.work_dir,
                cache_dir=config.cache_dir,
                timeout=config.timeout,
                stability=config.stability_window,
            )
        except Exception as exc:  # An environment must not prevent later environments.
            internal_errors += 1
            result = VerificationResult(
                result="UNKNOWN_FAILURE",
                failure_stage="internal",
                reason=f"{type(exc).__name__}: {exc}",
                metadata={
                    "requested_paper": environment.paper,
                    "requested_java": environment.java,
                },
            )
        if not plugin_metadata.get("plugin_name"):
            plugin_metadata.update(
                {
                    key: value
                    for key, value in result.metadata.items()
                    if key.startswith("plugin_") or key in {"api_version", "depend", "softdepend", "loadbefore"}
                }
            )
        if result.workdir:
            result.metadata.setdefault('protected_inputs', []).extend([str(config.source_path), str(config.plugin)])
            runtime_report = Path(result.workdir) / "result.json"
            if not result.report_path:
                try:
                    write_report(result, runtime_report)
                except (OSError, ValueError) as exc:
                    internal_errors += 1
                    result.metadata['verification_verdict'] = result.result
                    result.result = 'UNKNOWN_FAILURE'
                    result.failure_stage = 'report'
                    result.reason = f'could not save runtime report {runtime_report}: {exc}'
        entry = _result_entry(environment, result)
        if not entry["primary_evidence"]:
            entry["primary_evidence"] = str(config.report_path)
        results.append(entry)

    passed = sum(entry["verdict"] == "PASS" for entry in results)
    failed = len(results) - passed
    report = {
        "pluginmatrix_version": __version__,
        "config_source": str(config.source_path),
        "plugin": plugin_metadata,
        "config": config.to_dict(),
        "preflight": preflight or {},
        "environments": results,
        "summary": {"total": len(results), "passed": passed, "failed": failed},
        "internal_errors": internal_errors,
        "artifacts": {
            "matrix_report": str(config.report_path),
            "runtime_root": str(config.work_dir),
        },
    }
    validate_output_paths(config.work_dir, config.cache_dir, [config.source_path, config.plugin], config.report_path)
    atomic_json(config.report_path, report)
    return report


def matrix_exit_code(report: dict[str, Any]) -> int:
    if report.get("internal_errors", 0):
        return 3
    return 0 if report["summary"]["failed"] == 0 else 1
