from __future__ import annotations

import json
import os
import queue
import re
import shutil
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from .model import Check, EvidenceEvent, VerificationResult
from .paper import PaperDownloadError, ensure_paper
from .preflight import PreflightError, inspect_plugin, java_target_name
from .probe import PROBE_FILE_NAME, build_probe_plugin, read_probe_evidence


READY_MARKERS = ("done (", 'for help, type "help"')
ENVIRONMENT_FAILURE_MARKERS = (
    "paperclip.setupclasspath",
    "unable to access jarfile",
    "could not reserve enough space",
)
NETWORK_FAILURE_MARKERS = (
    "connection reset",
    "connection refused",
    "unknown host",
)
RUNTIME_DOWNLOAD_CONTEXT_MARKERS = (
    "mojang",
    "paperclip",
    "downloadcontext",
    "server dependency",
    "paper jar",
)
SERVER_FAILURE_MARKERS = (
    "failed to bind",
    "address already in use",
    "server thread stopped",
    "error during server startup",
)
PLUGIN_LOAD_FAILURE_MARKERS = (
    "invalidpluginexception",
    "unknowndependencyexception",
    "could not load",
    "failed to load",
    "does not contain plugin.yml",
    "plugin.yml is missing",
)
PLUGIN_ENABLE_FAILURE_MARKERS = (
    "error occurred while enabling",
    "exception occurred while enabling",
    "failed to enable",
)
RUNTIME_PROBE_FAILURE_MARKER = "unable to write runtime evidence"
PLUGIN_DISABLE_RE = re.compile(r"\bdisabling\s+(?P<name>.+?)(?:\s+v[\w.+-]+)?\s*$", re.IGNORECASE)
PLUGIN_ENABLE_RE = re.compile(r"\benabling\s+(?P<name>.+?)(?:\s+v[\w.+-]+)?\s*$", re.IGNORECASE)
PLUGIN_LOAD_RE = re.compile(r"\b(?:loading|loaded)\s+(?:server\s+plugin\s+|plugin\s+)?(?P<name>.+?)(?:\s+v[\w.+-]+)?\s*$", re.IGNORECASE)
EXCEPTION_RE = re.compile(
    r"(?i)(?:caused by: |exception: |error: )?"
    r"([A-Za-z0-9_.$]+(?:Exception|Error|Throwable))(?::\s*(.*))?"
)


@dataclass
class RuntimeEvidence:
    plugin_name: str
    plugin_jar_name: str | None = None
    events: list[EvidenceEvent] = field(default_factory=list)
    server_process_started: bool = False
    server_ready: bool = False
    plugin_discovered: bool = False
    plugin_load_failed: bool = False
    plugin_enable_started: bool = False
    plugin_enable_failed: bool = False
    plugin_disabled: bool = False
    environment_failed: bool = False
    server_failed: bool = False
    direct_runtime_observed: bool = False
    direct_plugin_present: bool | None = None
    direct_plugin_enabled: bool | None = None
    direct_plugin_name: str | None = None
    direct_plugin_version: str | None = None
    direct_runtime_error: str | None = None
    require_direct_runtime: bool = False
    failure_reason: str | None = None
    process_exit_code: int | None = None

    def add(self, kind: str, timestamp: float, source: str = "log", detail: str | None = None) -> None:
        if any(event.kind == kind and event.detail == detail for event in self.events):
            return
        self.events.append(EvidenceEvent(kind=kind, timestamp=round(timestamp, 3), source=source, detail=detail))

    def mark_process_started(self, timestamp: float) -> None:
        self.server_process_started = True
        self.add("server_process_started", timestamp, source="process")

    def mark_process_exit(self, timestamp: float, exit_code: int | None) -> None:
        self.process_exit_code = exit_code
        self.add("server_process_exited", timestamp, source="process", detail=f"exit_code={exit_code}")

    def _mentions_target(self, line: str) -> bool:
        lowered = line.lower()
        plugin_name = self.plugin_name.lower()
        jar_name = (self.plugin_jar_name or "").lower()
        return bool(plugin_name and plugin_name in lowered) or bool(jar_name and jar_name in lowered)

    def observe_line(self, line: str, timestamp: float) -> None:
        stripped = line.strip()
        lowered = stripped.lower()
        if not stripped:
            return

        environment_marker = any(marker in lowered for marker in ENVIRONMENT_FAILURE_MARKERS)
        if any(marker in lowered for marker in ("failed to download", "could not download")):
            environment_marker = any(
                token in lowered
                for token in RUNTIME_DOWNLOAD_CONTEXT_MARKERS
            )
        if environment_marker:
            self.environment_failed = True
            self.failure_reason = _reason_from_line(stripped) or stripped
            self.add("environment_failure", timestamp, detail=self.failure_reason)
        elif self.environment_failed and any(marker in lowered for marker in NETWORK_FAILURE_MARKERS):
            self.failure_reason = _reason_from_line(stripped) or stripped
            self.add("environment_failure", timestamp, detail=self.failure_reason)

        if any(marker in lowered for marker in SERVER_FAILURE_MARKERS):
            self.server_failed = True
            self.failure_reason = _reason_from_line(stripped) or stripped
            self.add("server_failure", timestamp, detail=self.failure_reason)

        if RUNTIME_PROBE_FAILURE_MARKER in lowered:
            self.direct_runtime_error = stripped
            self.add("runtime_probe_failure", timestamp, detail=stripped)

        if any(marker in lowered for marker in PLUGIN_LOAD_FAILURE_MARKERS):
            if self._mentions_target(stripped) or "unknowndependencyexception" in lowered:
                self.plugin_load_failed = True
                self.failure_reason = _reason_from_line(stripped) or stripped
                self.add("plugin_load_failed", timestamp, detail=self.failure_reason)

        if any(marker in lowered for marker in PLUGIN_ENABLE_FAILURE_MARKERS) and self._mentions_target(stripped):
            self.plugin_enable_failed = True
            self.failure_reason = _reason_from_line(stripped) or stripped
            self.add("plugin_enable_failed", timestamp, detail=self.failure_reason)

        disable_match = PLUGIN_DISABLE_RE.search(stripped)
        if disable_match and self._name_matches(disable_match.group("name")):
            self.plugin_disabled = True
            self.failure_reason = self.failure_reason or "plugin was disabled after startup"
            self.add("plugin_disabled", timestamp, detail=stripped)

        enable_match = PLUGIN_ENABLE_RE.search(stripped)
        if enable_match and self._name_matches(enable_match.group("name")):
            self.plugin_discovered = True
            self.plugin_enable_started = True
            self.add("plugin_discovered", timestamp, detail=stripped)
            self.add("plugin_enable_started", timestamp, detail=stripped)

        load_match = PLUGIN_LOAD_RE.search(stripped)
        if load_match and self._name_matches(load_match.group("name")):
            self.plugin_discovered = True
            self.add("plugin_discovered", timestamp, detail=stripped)

        if any(marker in lowered for marker in READY_MARKERS):
            self.server_ready = True
            self.add("server_ready", timestamp, detail=stripped)

        if self.plugin_enable_started and not self.failure_reason:
            exception_match = EXCEPTION_RE.search(stripped)
            if exception_match:
                self.plugin_enable_failed = True
                self.failure_reason = _format_exception(exception_match)
                self.add("plugin_enable_failed", timestamp, detail=self.failure_reason)

    def observe_probe(self, payload: dict[str, object], timestamp: float) -> None:
        self.direct_runtime_observed = True
        self.direct_plugin_present = bool(payload.get("target_present"))
        self.direct_plugin_enabled = bool(payload.get("target_enabled"))
        self.direct_plugin_name = str(payload.get("target_name") or "") or None
        self.direct_plugin_version = str(payload.get("target_version") or "") or None
        self.add(
            "runtime_probe_observed",
            timestamp,
            source="runtime_probe",
            detail=json.dumps(payload, sort_keys=True),
        )
        if self.direct_plugin_present:
            self.plugin_discovered = True
            self.add("plugin_discovered", timestamp, source="runtime_probe", detail=self.direct_plugin_name)
        if self.direct_plugin_enabled:
            self.plugin_enable_started = True
            self.add("plugin_enabled", timestamp, source="runtime_probe", detail=self.direct_plugin_version)
        elif self.direct_plugin_present:
            self.plugin_disabled = True
            self.failure_reason = self.failure_reason or "runtime probe observed target plugin disabled"
            self.add("plugin_disabled", timestamp, source="runtime_probe", detail=self.direct_plugin_name)

    def _name_matches(self, value: str) -> bool:
        normalized = re.sub(r"\s+v[\w.+-]+$", "", value.strip(), flags=re.IGNORECASE)
        return normalized.casefold() == self.plugin_name.casefold()

    def finalize(self, timestamp: float, process_alive: bool, timed_out: bool) -> None:
        if self.server_ready and self.plugin_enable_started and not self.plugin_load_failed and not self.plugin_enable_failed and not self.plugin_disabled:
            self.add("plugin_enabled", timestamp, source="inferred", detail="enable evidence survived until server ready")
        if timed_out:
            self.add("startup_timeout" if not self.server_ready else "stability_timeout", timestamp, source="process")

    def verdict(self, process_alive: bool, timed_out: bool) -> tuple[str, str | None, str | None]:
        if self.environment_failed:
            return "ENVIRONMENT_INVALID", "environment", self.failure_reason
        if self.plugin_load_failed:
            return "PLUGIN_LOAD_FAILED", "plugin_load", self.failure_reason
        if self.plugin_enable_failed:
            return "PLUGIN_ENABLE_FAILED", "plugin_enable", self.failure_reason
        if self.plugin_disabled:
            return "PLUGIN_DISABLED", "plugin_runtime", self.failure_reason
        if self.server_failed:
            return "SERVER_START_FAILED", "server_start", self.failure_reason
        if not self.server_ready:
            if process_alive and timed_out:
                return "SERVER_START_TIMEOUT", "server_start", "server did not become ready before timeout"
            return "SERVER_START_FAILED", "server_start", self.failure_reason or f"server exited with code {self.process_exit_code}"
        if not self.plugin_discovered:
            return "PLUGIN_NOT_DISCOVERED", "plugin_discovery", "no explicit evidence that the target plugin was discovered"
        if not self.plugin_enable_started:
            return "PLUGIN_ENABLE_FAILED", "plugin_enable", "no explicit evidence that the target plugin entered enable"
        if self.require_direct_runtime and self.direct_runtime_error:
            return "UNKNOWN_FAILURE", "runtime_probe", self.direct_runtime_error
        if self.require_direct_runtime and not self.direct_runtime_observed:
            return "UNKNOWN_FAILURE", "runtime_probe", "runtime probe did not produce direct plugin state evidence"
        if self.require_direct_runtime and self.direct_plugin_enabled is not True:
            return "PLUGIN_ENABLE_FAILED", "plugin_enable", "runtime probe did not confirm target plugin enabled"
        if not process_alive:
            return "SERVER_START_FAILED", "server_runtime", "server exited during the stability window"
        return "PASS", None, None


@dataclass
class ProcessRun:
    evidence: RuntimeEvidence
    exit_code: int | None
    timed_out: bool


def resolve_java(java: str) -> tuple[str, str]:
    candidate = java
    if java.isdigit():
        candidate = shutil.which("java") or "java"
    else:
        candidate = shutil.which(java) or java
    try:
        completed = subprocess.run([candidate, "-version"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as exc:
        raise ValueError(f"Java executable is not available: {java} ({exc})") from exc
    output = (completed.stderr or "") + (completed.stdout or "")
    if completed.returncode != 0:
        raise ValueError(f"Java executable failed: {java}")
    match = re.search(r'version "([^"]+)"', output)
    version = match.group(1) if match else "unknown"
    requested_major = java if java.isdigit() else None
    actual_major = version.split(".", 1)[0]
    if version.startswith("1."):
        actual_major = version.split(".")[1]
    if requested_major and actual_major != requested_major:
        raise ValueError(f"requested Java {requested_major}, found Java {actual_major} ({version})")
    return candidate, version


def _append_log(path: Path, text: str) -> None:
    with path.open("a", encoding="utf-8", errors="replace") as stream:
        stream.write(text)


def _paper_runtime_cache_dir(cache_dir: Path, metadata: dict[str, Any]) -> Path:
    version = str(metadata.get("minecraft_version") or metadata.get("requested_paper") or "unknown")
    build = str(metadata.get("paper_build") or "local")
    return cache_dir / "runtime" / f"paper-{version}-{build}"


def _seed_paper_runtime(server_dir: Path, runtime_cache: Path) -> bool:
    if not runtime_cache.is_dir():
        return False
    seeded = False
    for name in ("cache", "libraries", "versions"):
        source = runtime_cache / name
        if source.is_dir():
            shutil.copytree(source, server_dir / name, dirs_exist_ok=True)
            seeded = True
    return seeded


def _cache_paper_runtime(server_dir: Path, runtime_cache: Path, paper_version: str) -> bool:
    if not (server_dir / "versions" / paper_version / f"paper-{paper_version}.jar").is_file():
        return False
    for name in ("cache", "libraries", "versions"):
        source = server_dir / name
        if source.is_dir():
            shutil.copytree(source, runtime_cache / name, dirs_exist_ok=True)
    return True


def _format_exception(match: re.Match[str]) -> str:
    return f"{match.group(1)}: {match.group(2)}" if match.group(2) else match.group(1)


def _reason_from_line(line: str) -> str | None:
    match = EXCEPTION_RE.search(line)
    if match:
        return _format_exception(match)
    return line.strip() or None


def _reader(stream: Any, output: queue.Queue[str | None]) -> None:
    try:
        for line in stream:
            output.put(line)
    finally:
        output.put(None)


def _allocate_server_port() -> int:
    """Return an available local TCP port for this isolated Paper run."""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _create_run_dir(work_root: Path) -> Path:
    work_root.mkdir(parents=True, exist_ok=True)
    while True:
        candidate = work_root / f"run-{int(time.time())}-{uuid.uuid4().hex[:12]}"
        try:
            candidate.mkdir(parents=False)
        except FileExistsError:
            continue
        return candidate


def _write_server_properties(server_dir: Path, port: int) -> Path:
    path = server_dir / "server.properties"
    path.write_text(
        "\n".join(
            [
                f"server-port={port}",
                "server-ip=127.0.0.1",
                "online-mode=false",
                "enable-query=false",
                "enable-rcon=false",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def _stop_process(process: subprocess.Popen[str]) -> None:
    """Stop Paper and, on Windows, any child process it spawned."""
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
        return
    except subprocess.TimeoutExpired:
        pass
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    else:
        process.kill()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass


def run_server_process(
    command: Sequence[str],
    server_dir: Path,
    log_path: Path,
    plugin_name: str,
    plugin_jar_name: str | None,
    timeout: int,
    stability: int,
    probe_path: Path | None = None,
    require_direct_runtime: bool = False,
) -> ProcessRun:
    evidence = RuntimeEvidence(
        plugin_name=plugin_name,
        plugin_jar_name=plugin_jar_name,
        require_direct_runtime=require_direct_runtime,
    )
    output: queue.Queue[str | None] = queue.Queue()
    process: subprocess.Popen[str] | None = None
    reader: threading.Thread | None = None
    started_at = time.monotonic()
    timed_out = False
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.touch()
    try:
        process = subprocess.Popen(
            list(command),
            cwd=server_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        evidence.mark_process_started(0.0)
        reader = threading.Thread(target=_reader, args=(process.stdout, output), daemon=True)
        reader.start()

        def consume_until(deadline: float, stop_when_ready: bool = False) -> None:
            nonlocal timed_out
            while time.monotonic() < deadline:
                try:
                    line = output.get(timeout=0.1)
                except queue.Empty:
                    line = ""
                if line is None:
                    break
                if line:
                    _append_log(log_path, line)
                    evidence.observe_line(line, time.monotonic() - started_at)
                    if stop_when_ready and evidence.server_ready:
                        return
                if probe_path and probe_path.exists():
                    payload = read_probe_evidence(probe_path)
                    if payload:
                        evidence.observe_probe(payload, time.monotonic() - started_at)
                if process.poll() is not None:
                    break
            else:
                timed_out = True

        consume_until(started_at + timeout, stop_when_ready=True)
        ready_at = time.monotonic()
        if evidence.server_ready and process.poll() is None:
            timed_out = False
            consume_until(ready_at + stability, stop_when_ready=False)
            if process.poll() is None and time.monotonic() >= ready_at + stability:
                timed_out = False
        exit_code = process.poll()
        if exit_code is not None:
            evidence.mark_process_exit(time.monotonic() - started_at, exit_code)
        evidence.finalize(time.monotonic() - started_at, exit_code is None, timed_out)
        return ProcessRun(evidence=evidence, exit_code=exit_code, timed_out=timed_out)
    except OSError as exc:
        evidence.environment_failed = True
        evidence.failure_reason = str(exc)
        evidence.add("environment_failure", time.monotonic() - started_at, source="process", detail=str(exc))
        evidence.finalize(time.monotonic() - started_at, False, False)
        return ProcessRun(evidence=evidence, exit_code=None, timed_out=False)
    finally:
        if process and process.poll() is None:
            _stop_process(process)
        if reader:
            reader.join(timeout=2)
        if process and process.stdout:
            process.stdout.close()
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline:
            try:
                line = output.get_nowait()
            except queue.Empty:
                break
            if line:
                _append_log(log_path, line)


def _runtime_checks(evidence: RuntimeEvidence, process_run: ProcessRun) -> list[Check]:
    return [
        Check("Server process", "PASS" if evidence.server_process_started else "FAIL"),
        Check("Server start", "PASS" if evidence.server_ready else ("TIMEOUT" if process_run.timed_out else "FAIL")),
        Check("Plugin discovered", "PASS" if evidence.plugin_discovered else "FAIL"),
        Check("Plugin load", "FAIL" if evidence.plugin_load_failed else "PASS" if evidence.plugin_enable_started else "UNKNOWN"),
        Check("Plugin enable", "FAIL" if evidence.plugin_enable_failed else "PASS" if evidence.plugin_enable_started and not evidence.plugin_disabled else "UNKNOWN"),
        Check(
            "Runtime probe",
            "PASS" if evidence.direct_plugin_enabled else "FAIL" if evidence.direct_runtime_observed else "UNKNOWN",
            evidence.direct_runtime_error,
        ),
        Check("Plugin stability", "FAIL" if evidence.plugin_disabled else "PASS" if evidence.server_ready and process_run.exit_code is None else "FAIL"),
    ]


def verify(
    plugin: Path,
    paper_version: str,
    java: str,
    work_root: Path,
    cache_dir: Path,
    timeout: int,
    stability: int,
    dependencies: list[Path] | None = None,
    paper_build: int | None = None,
    paper_jar: Path | None = None,
    paper_metadata: dict[str, Any] | None = None,
) -> VerificationResult:
    result = VerificationResult()
    result.metadata["requested_paper"] = paper_version
    result.metadata["requested_java"] = java
    workdir = _create_run_dir(work_root)
    result.workdir = str(workdir.resolve())
    log_path = workdir / "server.log"
    result.log_path = str(log_path.resolve())
    try:
        metadata, checks = inspect_plugin(plugin)
        result.metadata.update(metadata)
        result.checks.extend(checks)
        java_bin, java_version = resolve_java(java)
        result.metadata["java_executable"] = str(Path(java_bin).resolve()) if Path(java_bin).exists() else java_bin
        result.metadata["java_runtime_version"] = java_version
        result.checks.append(Check("Java runtime", "PASS", java_version))
        java_major = int(java_version.split(".", 1)[0])
        if java_version.startswith("1."):
            java_major = int(java_version.split(".")[1])
        result.metadata["java_runtime_major"] = java_major
        bytecode_major = metadata.get("main_class_major")
        if bytecode_major and bytecode_major > java_major + 44:
            detail = f"target {java_target_name(bytecode_major)} exceeds runtime Java {java_major}"
            result.checks.append(Check("Java bytecode", "FAIL", detail))
            result.result = "PLUGIN_LOAD_FAILED"
            result.failure_stage = "preflight"
            result.reason = detail
            return result
        if paper_jar is None:
            paper_jar, resolved_metadata = ensure_paper(paper_version, cache_dir, paper_build)
        else:
            resolved_metadata = paper_metadata or {"paper_jar_name": paper_jar.name}
        result.metadata.update(resolved_metadata)
        result.checks.append(Check("Paper artifact", "PASS", f"build {resolved_metadata.get('paper_build', 'local')}"))
    except PreflightError as exc:
        result.checks.extend(exc.checks)
        result.result = exc.state
        result.failure_stage = "preflight"
        result.reason = str(exc)
        return result
    except (ValueError, PaperDownloadError) as exc:
        result.result = "ENVIRONMENT_INVALID"
        result.failure_stage = "environment"
        result.reason = str(exc)
        result.checks.append(Check("Environment", "FAIL", str(exc)))
        return result

    server_dir = workdir / "server"
    plugins_dir = server_dir / "plugins"
    plugins_dir.mkdir(parents=True)
    shutil.copy2(paper_jar, server_dir / "paper.jar")
    runtime_cache = _paper_runtime_cache_dir(cache_dir, {**result.metadata, "requested_paper": paper_version})
    runtime_cache_seeded = _seed_paper_runtime(server_dir, runtime_cache)
    result.metadata["paper_runtime_cache"] = {
        "path": str(runtime_cache.resolve()),
        "seeded": runtime_cache_seeded,
    }
    shutil.copy2(plugin, plugins_dir / plugin.name)
    for dependency in dependencies or []:
        if not dependency.is_file():
            result.result = "ENVIRONMENT_INVALID"
            result.failure_stage = "environment"
            result.reason = f"dependency does not exist: {dependency}"
            result.checks.append(Check("Dependency", "FAIL", result.reason))
            return result
        shutil.copy2(dependency, plugins_dir / dependency.name)
    probe_path = plugins_dir / PROBE_FILE_NAME
    try:
        build_probe_plugin(
            paper_jar,
            plugins_dir,
            str(result.metadata.get("plugin_name") or ""),
            probe_path,
            java_bin,
            java_major,
        )
    except RuntimeError as exc:
        result.result = "ENVIRONMENT_INVALID"
        result.failure_stage = "runtime_probe"
        result.reason = str(exc)
        result.checks.append(Check("Runtime probe", "FAIL", str(exc)))
        return result
    (server_dir / "eula.txt").write_text("eula=true\n", encoding="utf-8")
    server_port = _allocate_server_port()
    _write_server_properties(server_dir, server_port)
    result.metadata["server_port"] = server_port
    command = [java_bin, "-jar", "paper.jar", "--nogui"]
    result.metadata["command"] = command
    process_run = run_server_process(
        command=command,
        server_dir=server_dir,
        log_path=log_path,
        plugin_name=str(result.metadata.get("plugin_name") or ""),
        plugin_jar_name=plugin.name,
        timeout=timeout,
        stability=stability,
        probe_path=probe_path,
        require_direct_runtime=True,
    )
    evidence = process_run.evidence
    result.evidence = evidence.events
    if evidence.direct_runtime_observed:
        result.metadata["runtime_probe"] = {
            "target_present": evidence.direct_plugin_present,
            "target_enabled": evidence.direct_plugin_enabled,
            "target_name": evidence.direct_plugin_name,
            "target_version": evidence.direct_plugin_version,
        }
    result.result, result.failure_stage, result.reason = evidence.verdict(
        process_alive=process_run.exit_code is None,
        timed_out=process_run.timed_out,
    )
    result.metadata["paper_runtime_cache"]["captured"] = _cache_paper_runtime(server_dir, runtime_cache, paper_version)
    result.checks.extend(_runtime_checks(evidence, process_run))
    return result


def write_report(result: VerificationResult, path: Path) -> None:
    result.report_path = str(path.resolve())
    path.write_text(json.dumps(result.to_dict(), indent=2, ensure_ascii=True), encoding="utf-8")
