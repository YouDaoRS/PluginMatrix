from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from . import __version__
from .model import VerificationResult
from .runtime import verify, write_report


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
        raise MatrixConfigError(f"{label} must be an object")
    return value


def _resolve_path(value: object, base: Path, label: str, must_exist: bool = False) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise MatrixConfigError(f"{label} must be a non-empty path")
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base / path
    path = path.resolve()
    if must_exist and not path.is_file():
        raise MatrixConfigError(f"{label} does not exist: {path}")
    return path


def load_matrix_config(path: Path) -> MatrixConfig:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise MatrixConfigError(f"matrix config does not exist: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MatrixConfigError(f"cannot read matrix config {path}: {exc}") from exc
    document = _require_mapping(raw, "matrix config")
    plugin = _resolve_path(document.get("plugin"), path.parent, "plugin", must_exist=True)

    raw_environments = document.get("environments")
    if not isinstance(raw_environments, list) or not raw_environments:
        raise MatrixConfigError("environments must be a non-empty array")
    environments: list[MatrixEnvironment] = []
    seen: set[str] = set()
    for index, raw_environment in enumerate(raw_environments, start=1):
        item = _require_mapping(raw_environment, f"environment #{index}")
        paper = item.get("paper")
        java = item.get("java")
        if not isinstance(paper, str) or not re.fullmatch(r"\d+\.\d+(?:\.\d+)?", paper.strip()):
            raise MatrixConfigError(f"environment #{index} paper must be a version such as 1.20.1")
        paper = paper.strip()
        if isinstance(java, int) and not isinstance(java, bool):
            java = str(java)
        if not isinstance(java, str) or not java.strip():
            raise MatrixConfigError(f"environment #{index} java must be a version or executable")
        java = java.strip()
        build = item.get("paper_build")
        if build is not None:
            if isinstance(build, bool) or not isinstance(build, int) or build <= 0:
                raise MatrixConfigError(f"environment #{index} paper_build must be a positive integer")
        environment = MatrixEnvironment(paper=paper, java=java, paper_build=build)
        if environment.environment_id in seen:
            raise MatrixConfigError(f"duplicate environment definition: {environment.environment_id}")
        seen.add(environment.environment_id)
        environments.append(environment)

    options = _require_mapping(document.get("options", {}), "options")
    timeout = options.get("timeout", 120)
    stability = options.get("stability_window", 5)
    if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
        raise MatrixConfigError("options.timeout must be a positive integer")
    if isinstance(stability, bool) or not isinstance(stability, int) or stability < 0:
        raise MatrixConfigError("options.stability_window must be a non-negative integer")
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
    }


def run_matrix(
    config: MatrixConfig,
    verifier: Callable[..., VerificationResult] = verify,
    progress: Callable[[int, int, MatrixEnvironment], None] | None = None,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    internal_errors = 0
    plugin_metadata: dict[str, Any] = {"plugin_jar": str(config.plugin)}
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
            runtime_report = Path(result.workdir) / "result.json"
            if not result.report_path:
                write_report(result, runtime_report)
        results.append(_result_entry(environment, result))

    passed = sum(entry["verdict"] == "PASS" for entry in results)
    failed = len(results) - passed
    report = {
        "pluginmatrix_version": __version__,
        "plugin": plugin_metadata,
        "config": config.to_dict(),
        "environments": results,
        "summary": {"total": len(results), "passed": passed, "failed": failed},
        "internal_errors": internal_errors,
    }
    config.report_path.parent.mkdir(parents=True, exist_ok=True)
    config.report_path.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    return report


def matrix_exit_code(report: dict[str, Any]) -> int:
    if report.get("internal_errors", 0):
        return 3
    return 0 if report["summary"]["failed"] == 0 else 1
