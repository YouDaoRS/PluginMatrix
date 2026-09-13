from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import time
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from . import __version__
from .files import atomic_json, atomic_copy, protect_inputs, reject_links, sha256_file, validate_output_paths
from .processes import start_process, stop_process
from .model import Check, EvidenceEvent, VerificationResult
from .paper import PaperDownloadError, ensure_paper
from .preflight import PreflightError, inspect_plugin, java_target_name
from .probe import PROBE_FILE_NAME, PROBE_PLUGIN_NAME, build_probe_plugin, read_probe_evidence
from .providers import ServerSpec, get_provider
from .control import RunControl, RunCancelled
from .locking import file_lock


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
    last_probe_payload: dict[str, object] | None = None
    direct_plugin_present: bool | None = None
    direct_plugin_enabled: bool | None = None
    direct_plugin_name: str | None = None
    direct_plugin_version: str | None = None
    direct_runtime_error: str | None = None
    require_direct_runtime: bool = False
    failure_reason: str | None = None
    process_exit_code: int | None = None
    observation_complete: bool = False
    expected_version: str | None = None
    expected_main: str | None = None
    expected_source: Path | None = None
    allowed_sources: tuple[Path, ...] | None = None
    provider_type: str = 'paper'
    cancelled: bool = False

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
        return any(re.search(r'(?<![\w.-])' + re.escape(value) + r'(?![\w.-])', lowered)
                   for value in (plugin_name, jar_name) if value)

    def observe_line(self, line: str, timestamp: float) -> None:
        stripped = line.strip()
        lowered = stripped.lower()
        if not stripped:
            return
        # A plugin logger is not a server lifecycle authority. In particular,
        # mentioning the target as a missing dependency does not implicate it.
        message = re.sub(r'^\[(?:\d[^\]]*|[^\]]+/[^\]]+)\](?:\s+\[[^\]]+/[^\]]+\])?:?\s*', '', stripped)
        logger = re.match(r'\[([^\]]+)\]\s*', message)
        if logger and logger.group(1).casefold() not in {self.plugin_name.casefold(), PROBE_PLUGIN_NAME.casefold(), 'minecraft', 'minecraftserver', 'directoryprovidersource', 'fileprovidersource', 'simplepluginmanager', 'paperplugininstancemanager'}:
            return

        server_events = get_provider(self.provider_type).interpret_server_line(stripped)
        if logger and logger.group(1).casefold() in {self.plugin_name.casefold(), PROBE_PLUGIN_NAME.casefold()}:
            server_events = set()
        environment_marker = 'environment_failure' in server_events
        if environment_marker:
            self.environment_failed = True
            self.failure_reason = _reason_from_line(stripped) or stripped
            self.add("environment_failure", timestamp, detail=self.failure_reason)
        elif self.environment_failed and any(marker in lowered for marker in NETWORK_FAILURE_MARKERS):
            self.failure_reason = _reason_from_line(stripped) or stripped
            self.add("environment_failure", timestamp, detail=self.failure_reason)

        if server_events & {'startup_failure', 'shutdown'}:
            self.server_failed = True
            self.failure_reason = _reason_from_line(stripped) or stripped
            self.add("server_failure", timestamp, detail=self.failure_reason)

        if RUNTIME_PROBE_FAILURE_MARKER in lowered and PROBE_PLUGIN_NAME.lower() in lowered:
            self.direct_runtime_error = stripped
            self.add("runtime_probe_failure", timestamp, detail=stripped)

        if any(marker in lowered for marker in PLUGIN_LOAD_FAILURE_MARKERS):
            subject = re.search(r'(?:could not load|failed to load)(?:\s+plugin)?\s+[\'\"]?([^\s:\'\"]+)', stripped, re.IGNORECASE)
            dependency_subject = re.search(r'\bfor\s+([\w.-]+)\s*$', stripped, re.IGNORECASE)
            attributed = self._mentions_target(stripped)
            if subject:
                value = subject.group(1).replace('\\', '/').split('/')[-1]
                attributed = value.casefold() in {self.plugin_name.casefold(), (self.plugin_jar_name or '').casefold()}
            elif dependency_subject:
                attributed = self._name_matches(dependency_subject.group(1))
            else:
                attributed = False
            if attributed:
                self.plugin_load_failed = True
                self.failure_reason = _reason_from_line(stripped) or stripped
                self.add("plugin_load_failed", timestamp, detail=self.failure_reason)

        enable_failure = re.search(r'(?:error occurred while enabling|exception occurred while enabling|failed to enable)\s+([\w.-]+)', stripped, re.IGNORECASE)
        if enable_failure and self._name_matches(enable_failure.group(1)):
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

        if 'ready' in server_events:
            self.server_ready = True
            self.add("server_ready", timestamp, detail=stripped)

    def observe_probe(self, payload: dict[str, object], timestamp: float) -> None:
        if payload.get('target_present') and (
            payload.get('target_name') != self.plugin_name or
            (self.expected_version is not None and payload.get('target_version') != self.expected_version)
            or (self.expected_main is not None and payload.get('target_main') != self.expected_main)
        ):
            self.direct_runtime_error = 'runtime probe target identity does not match the inspected plugin'
            self.add(
                "runtime_probe_identity_mismatch",
                timestamp,
                source="runtime_probe",
                detail=json.dumps(payload, sort_keys=True),
            )
            return
        if self.direct_runtime_error:
            return
        if payload.get('target_present') and self.expected_source is not None:
            actual = Path(str(payload.get('target_source') or '')).resolve()
            allowed = {p.resolve() for p in (self.allowed_sources or get_provider(self.provider_type).allowed_sources(None, self.expected_source))}
            if actual not in allowed or not actual.is_file():
                self.direct_runtime_error = 'runtime probe source does not match the isolated target JAR'
                self.add('runtime_probe_identity_mismatch', timestamp, source='runtime_probe', detail=json.dumps(payload, sort_keys=True))
                return
        self.direct_runtime_observed = True
        self.last_probe_payload = dict(payload)
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
        elif self.direct_plugin_present or self.plugin_enable_started:
            self.plugin_disabled = True
            self.failure_reason = self.failure_reason or "runtime probe observed target plugin disabled"
            self.add("plugin_disabled", timestamp, source="runtime_probe", detail=self.direct_plugin_name)
        if payload.get('target_ever_disabled'):
            self.plugin_disabled = True
            self.failure_reason = self.failure_reason or 'runtime probe recorded a target disable event'
            self.add('plugin_disabled', timestamp, source='runtime_probe', detail=self.failure_reason)

    def _name_matches(self, value: str) -> bool:
        normalized = re.sub(r"\s+v[\w.+-]+$", "", value.strip(), flags=re.IGNORECASE)
        return normalized.casefold() == self.plugin_name.casefold()

    def finalize(self, timestamp: float, process_alive: bool, timed_out: bool) -> None:
        if timed_out:
            self.add("startup_timeout" if not self.server_ready else "stability_timeout", timestamp, source="process")

    def verdict(self, process_alive: bool, timed_out: bool) -> tuple[str, str | None, str | None]:
        if self.environment_failed:
            return "ENVIRONMENT_INVALID", "environment", self.failure_reason
        if self.cancelled:
            return 'CANCELLED', 'cancelled', 'run cancelled; owned server processes cleaned up'
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
        if self.direct_runtime_error:
            return "UNKNOWN_FAILURE", "runtime_probe", self.direct_runtime_error
        if not self.direct_runtime_observed:
            return "UNKNOWN_FAILURE", "runtime_probe", "runtime probe did not produce direct plugin state evidence"
        if self.direct_plugin_enabled is not True:
            return "PLUGIN_ENABLE_FAILED", "plugin_enable", "runtime probe did not confirm target plugin enabled"
        if not process_alive:
            return "SERVER_START_FAILED", "server_runtime", "server exited during the stability window"
        if self.observation_complete is not True:
            return "UNKNOWN_FAILURE", "runtime_probe", self.direct_runtime_error or "observation window did not complete"
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
        raise ValueError(
            f"Java value {java!r} did not resolve to an available executable ({exc}). "
            "Expected an installed JDK java executable; fix PATH or provide its executable path."
        ) from exc
    output = (completed.stderr or "") + (completed.stdout or "")
    if completed.returncode != 0:
        raise ValueError(
            f"Java value {java!r} resolved to {candidate!r}, but 'java -version' exited with "
            f"code {completed.returncode}. Expected a working JDK executable; check the installation."
        )
    match = re.search(r'version "([^"]+)"', output)
    version = match.group(1) if match else "unknown"
    requested_major = java if java.isdigit() else None
    actual_major = version.split(".", 1)[0]
    if version.startswith("1."):
        actual_major = version.split(".")[1]
    if requested_major and actual_major != requested_major:
        raise ValueError(
            f"requested Java {requested_major}, but {candidate!r} reports Java {actual_major} ({version}). "
            f"Expected Java {requested_major}; select the matching JDK or correct PATH."
        )
    return candidate, version


def _append_log(path: Path, text: str) -> None:
    with path.open("a", encoding="utf-8", errors="replace") as stream:
        stream.write(text)


def _paper_runtime_cache_dir(cache_dir: Path, metadata: dict[str, Any]) -> Path:
    version = str(metadata.get("minecraft_version") or metadata.get("requested_paper") or "unknown")
    build = str(metadata.get("paper_build") or "local")
    if not re.fullmatch(r'\d+\.\d+(?:\.\d+)?', version) or not re.fullmatch(r'(?:[1-9]\d*|local)', build):
        raise ValueError('invalid Paper version/build for runtime cache path')
    return cache_dir / "runtime" / f"paper-{version}-{build}"


def _seed_paper_runtime(server_dir: Path, runtime_cache: Path) -> bool:
    reject_links(runtime_cache)
    if not runtime_cache.is_dir():
        return False
    seeded = False
    for name in ("cache", "libraries", "versions"):
        source = runtime_cache / name
        if source.is_dir():
            if source.is_symlink():
                raise ValueError(f"symbolic links are not allowed in Paper runtime data: {source}")
            _reject_symlinks(source)
            _reject_symlinks(server_dir / name)
            shutil.copytree(source, server_dir / name, dirs_exist_ok=True, copy_function=atomic_copy)
            seeded = True
    return seeded


def _cache_paper_runtime(server_dir: Path, runtime_cache: Path, paper_version: str) -> bool:
    reject_links(runtime_cache)
    if not any((server_dir / 'versions').rglob('*.jar')):
        return False
    for name in ("cache", "libraries", "versions"):
        source = server_dir / name
        if source.is_dir():
            if source.is_symlink():
                raise ValueError(f"symbolic links are not allowed in Paper runtime data: {source}")
            _reject_symlinks(source)
            _reject_symlinks(runtime_cache / name)
            shutil.copytree(source, runtime_cache / name, dirs_exist_ok=True, copy_function=atomic_copy)
    return True


def _reject_symlinks(root: Path) -> None:
    reject_links(root)
    for path in root.rglob("*"):
        reject_links(path)


def _format_exception(match: re.Match[str]) -> str:
    return f"{match.group(1)}: {match.group(2)}" if match.group(2) else match.group(1)


def _reason_from_line(line: str) -> str | None:
    match = EXCEPTION_RE.search(line)
    if match:
        return _format_exception(match)
    return line.strip() or None




def _allocate_server_port() -> int:
    """Return an available local TCP port for this isolated Paper run."""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


_PORT_LOCK = threading.Lock()
_ACTIVE_PORTS: set[int] = set()


def _lease_port() -> int:
    with _PORT_LOCK:
        for _ in range(100):
            port = _allocate_server_port()
            if port not in _ACTIVE_PORTS:
                _ACTIVE_PORTS.add(port)
                return port
    raise OSError('could not allocate an independent server port')


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


def _stop_process(process) -> None:
    stop_process(process)


def run_server_process(
    command: Sequence[str], server_dir: Path, log_path: Path,
    plugin_name: str, plugin_jar_name: str | None, timeout: int, stability: int,
    probe_path: Path | None = None, require_direct_runtime: bool = False,
    expected_version: str | None = None,
    expected_main: str | None = None, expected_source: Path | None = None,
    run_id: str = '',
    allowed_sources: tuple[Path, ...] | None = None, provider_type: str = 'paper',
    control: RunControl | None = None, environment_index: int | None = None,
) -> ProcessRun:
    if any(isinstance(value, bool) or not math.isfinite(value) or value <= 0 for value in (timeout, stability)):
        raise ValueError('timeout and stability_window must be positive finite seconds')
    evidence = RuntimeEvidence(plugin_name=plugin_name, plugin_jar_name=plugin_jar_name,
                               require_direct_runtime=require_direct_runtime,
                               expected_version=expected_version, expected_main=expected_main,
                               expected_source=expected_source, observation_complete=False)
    evidence.allowed_sources, evidence.provider_type = allowed_sources, provider_type
    control = control or RunControl()
    process = None
    started = time.monotonic()
    ready_at = None
    first_probe = None
    last_probe = None
    sequence = None
    emitted_at = None
    window_start = None
    completion_sequence = None
    launched_wall = time.time() * 1000
    pending = b''
    timed_out = False
    exit_code = None
    progress_at = 0.0
    enabled_emitted = False
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        control.check()
        reject_links(log_path)
        if probe_path:
            reject_links(probe_path)
            probe_path.unlink(missing_ok=True)
        # Exclusive creation protects existing artifacts and hardlink aliases.
        with log_path.open('xb', buffering=0) as output, log_path.open('rb') as log:
            process = start_process(command, server_dir, output)
            evidence.mark_process_started(0)
            control.emit('server_started', environment_index, provider=provider_type)
            def read_log():
                nonlocal pending
                # Bound work per poll so heavy logging cannot starve timeout/probe checks.
                data = log.read(65536)
                pending += data
                lines = pending.split(b'\n')
                pending = lines.pop()
                if len(pending) > 65536:
                    lines.append(pending)
                    pending = b''
                for line in lines:
                    evidence.observe_line(line.decode('utf-8', errors='replace'), time.monotonic() - started)
                return bool(data)

            while True:
                control.check()
                backlog = read_log()
                now = time.monotonic()
                if evidence.server_ready and ready_at is None:
                    ready_at = now
                if probe_path:
                    payload = read_probe_evidence(probe_path)
                    if payload:
                        current = payload['sequence']
                        updated = payload['emitted_at_ms']
                        if payload['run_id'] != run_id:
                            evidence.direct_runtime_error = 'runtime probe belongs to another run'
                        elif sequence is not None and (current < sequence or updated < emitted_at):
                            evidence.direct_runtime_error = 'runtime probe sequence/time moved backwards'
                        elif sequence is None or current > sequence:
                            if updated < launched_wall or abs(time.time() * 1000 - updated) > 2000:
                                evidence.direct_runtime_error = 'runtime probe timestamp is stale or in the future'
                            elif last_probe is not None and now - last_probe > 2:
                                evidence.direct_runtime_error = 'runtime probe observation gap exceeded 2 seconds'
                            elif emitted_at is not None and updated <= emitted_at:
                                evidence.direct_runtime_error = 'runtime probe sequence advanced without a newer timestamp'
                            else:
                                first_probe = first_probe if first_probe is not None else now
                                last_probe, sequence, emitted_at = now, current, updated
                                evidence.observe_probe(payload, now - started)
                                if evidence.direct_plugin_enabled and not evidence.direct_runtime_error and not enabled_emitted:
                                    control.emit('plugin_enabled', environment_index)
                                    enabled_emitted = True
                                if ready_at is not None and window_start is None and evidence.direct_plugin_enabled and not evidence.direct_runtime_error:
                                    window_start = now
                                    completion_sequence = sequence
                                    evidence.add('stability_window_started', now - started, source='process', detail=f'sequence={sequence}; configured_seconds={stability}')
                if window_start is not None and now - progress_at >= 1:
                    control.emit('stability_progress', environment_index, elapsed=round(now-window_start, 2), duration=stability)
                    progress_at = now
                exit_code = process.poll()
                if exit_code is not None:
                    # Retain failure lines emitted immediately before exit.
                    drain_deadline = time.monotonic() + 0.5
                    while time.monotonic() < drain_deadline and read_log():
                        pass
                    if pending:
                        evidence.observe_line(pending.decode('utf-8', errors='replace'), now - started)
                    evidence.mark_process_exit(now - started, exit_code)
                    break
                if ready_at is None:
                    if now >= started + timeout:
                        timed_out = True
                        break
                else:
                    if window_start is None:
                        if now >= ready_at + min(timeout, 10):
                            evidence.direct_runtime_error = 'runtime probe did not produce direct plugin state evidence'
                            break
                    else:
                        if now - last_probe > 2:
                            evidence.direct_runtime_error = 'runtime probe stopped producing fresh evidence'
                            break
                        if now >= window_start + stability:
                            # Require an advancing sample at/after the end, plus a caught-up log.
                            if last_probe >= window_start + stability and sequence > completion_sequence and not backlog and not pending:
                                evidence.observation_complete = True
                                evidence.add('stability_window_completed', now - started, source='process',
                                             detail=f'configured_seconds={stability}; observed_seconds={now-window_start:.3f}; sequence={sequence}')
                                break
                            if now >= window_start + stability + 2:
                                evidence.direct_runtime_error = 'missing final probe sample or log could not be fully consumed'
                                break
                if evidence.direct_runtime_error:
                    evidence.add('runtime_probe_failure', now - started, source='runtime_probe', detail=evidence.direct_runtime_error)
                    break
                time.sleep(0.05)
    except (RunCancelled, KeyboardInterrupt):
        control.cancel()
        evidence.cancelled = True
        evidence.add('run_cancelled', time.monotonic() - started, source='process')
    except (OSError, subprocess.SubprocessError) as exc:
        evidence.environment_failed = True
        evidence.failure_reason = str(exc)
        evidence.add('environment_failure', time.monotonic() - started, source='process', detail=str(exc))
    finally:
        if process is not None:
            try:
                _stop_process(process)
            except (OSError, subprocess.SubprocessError) as exc:
                evidence.environment_failed = True
                evidence.failure_reason = f'could not clean up server process tree: {exc}'
                evidence.add('cleanup_failure', time.monotonic() - started, source='process', detail=str(exc))
    evidence.finalize(time.monotonic() - started, exit_code is None, timed_out)
    return ProcessRun(evidence=evidence, exit_code=exit_code, timed_out=timed_out)


def _runtime_checks(evidence: RuntimeEvidence, process_run: ProcessRun) -> list[Check]:
    return [
        Check("Server process", "PASS" if evidence.server_process_started else "FAIL"),
        Check("Server start", "PASS" if evidence.server_ready else ("TIMEOUT" if process_run.timed_out else "FAIL")),
        Check("Plugin discovered", "PASS" if evidence.plugin_discovered else "FAIL"),
        Check("Plugin load", "FAIL" if evidence.plugin_load_failed else "PASS" if evidence.plugin_enable_started else "UNKNOWN"),
        Check("Plugin enable", "FAIL" if evidence.plugin_enable_failed or evidence.plugin_disabled else "PASS" if evidence.direct_plugin_enabled else "UNKNOWN"),
        Check(
            "Runtime probe",
            "FAIL" if evidence.direct_runtime_error else "PASS" if evidence.direct_plugin_enabled else "FAIL" if evidence.direct_runtime_observed else "UNKNOWN",
            evidence.direct_runtime_error,
        ),
        Check(
            "Plugin stability",
            "PASS"
            if (
                evidence.observation_complete is True
                and not evidence.environment_failed
                and not evidence.direct_runtime_error
                and not evidence.plugin_disabled
                and process_run.exit_code is None
            )
            else "FAIL",
        ),
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
    server: ServerSpec | None = None,
    control: RunControl | None = None,
    environment_index: int | None = None,
) -> VerificationResult:
    result = VerificationResult()
    control = control or RunControl()
    server = server or ServerSpec('paper', paper_version, paper_build)
    provider = get_provider(server.type)
    result.metadata['server'] = provider.requested_metadata(server)
    result.metadata['server_type'] = server.type
    result.metadata.update(pluginmatrix_version=__version__, timeout=timeout, stability_window=stability)
    if server.type == 'paper':
        result.metadata["requested_paper"] = paper_version
    result.metadata["requested_java"] = java
    result.metadata['protected_inputs'] = [str(path.resolve()) for path in [plugin, *(dependencies or []), *([paper_jar] if paper_jar else [])]]
    if server.jar:
        result.metadata['protected_inputs'].append(str(server.jar.resolve()))
    result.metadata['cache_dir'] = str(cache_dir.resolve())
    try:
        validate_output_paths(work_root, cache_dir, [plugin, *(dependencies or []), *([server.jar] if server.jar else [])])
        workdir = _create_run_dir(work_root)
    except (OSError, ValueError) as exc:
        result.result, result.failure_stage, result.reason = 'ENVIRONMENT_INVALID', 'environment', str(exc)
        return result
    result.workdir = str(workdir.resolve())
    log_path = workdir / "server.log"
    result.log_path = str(log_path.resolve())
    try:
        control.check()
        provider.validate(server)
        metadata, checks = inspect_plugin(plugin)
        result.metadata.update(metadata)
        result.checks.extend(checks)
        if any(isinstance(value, bool) or not math.isfinite(value) or value <= 0 for value in (timeout, stability)):
            raise ValueError('timeout and stability_window must be positive finite seconds')
        result.metadata['dependencies'] = validate_plugin_inputs(plugin, metadata, dependencies or [])
        unsupported = provider.check_plugin(server, metadata)
        if unsupported:
            result.result, result.failure_stage, result.reason = 'PLUGIN_UNSUPPORTED', 'provider_preflight', unsupported
            result.checks.append(Check('Provider support declaration', 'FAIL', unsupported))
            return result
        for dependency in result.metadata['dependencies']:
            if provider.check_plugin(server, dependency):
                raise ValueError(f"dependency {dependency['plugin_name']} has no Folia support declaration")
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
            if server.type == 'paper':
                paper_jar, resolved_metadata = ensure_paper(server.version, cache_dir, server.build, control, environment_index)
            else:
                paper_jar, resolved_metadata = provider.prepare(server, cache_dir, control, environment_index)
        else:
            if server.type != 'paper':
                raise ValueError('legacy paper_jar override is Paper-only; use server.type=local for custom JARs')
            resolved_metadata = paper_metadata or {"paper_jar_name": paper_jar.name}
        actual_hash = sha256_file(paper_jar)
        expected_hash = resolved_metadata.get('jar_sha256') or resolved_metadata.get('paper_jar_sha256')
        if expected_hash and actual_hash != expected_hash:
            raise ValueError('server JAR changed after provider resolution')
        resolved_metadata = {**resolved_metadata, 'jar': str(paper_jar.resolve()), 'jar_sha256': actual_hash}
        if server.type == 'paper':
            resolved_metadata.update(paper_jar=resolved_metadata['jar'], paper_jar_sha256=resolved_metadata['jar_sha256'])
            resolved_metadata.setdefault('resolved_build', resolved_metadata.get('paper_build'))
        result.metadata['server'].update(resolved_metadata)
        result.metadata.update({key: value for key, value in resolved_metadata.items()
                                if key.startswith('paper_') or key == 'minecraft_version'})
        result.checks.append(Check('Server artifact', 'PASS', f"{server.type} build {resolved_metadata.get('resolved_build', 'local')}"))
    except (RunCancelled, KeyboardInterrupt):
        control.cancel()
        result.result, result.failure_stage, result.reason = 'CANCELLED', 'cancelled', 'run cancelled before startup'
        return result
    except PreflightError as exc:
        result.checks.extend(exc.checks)
        result.result = exc.state
        result.failure_stage = "preflight"
        result.reason = str(exc)
        return result
    except (OSError, ValueError, PaperDownloadError) as exc:
        result.result = "ENVIRONMENT_INVALID"
        result.failure_stage = "environment"
        result.reason = str(exc)
        result.checks.append(Check("Environment", "FAIL", str(exc)))
        return result

    server_port = None
    try:
        control.check()
        server_dir = workdir / "server"
        plugins_dir = server_dir / "plugins"
        plugins_dir.mkdir(parents=True)
        server_filename = 'paper.jar' if server.type == 'paper' else 'server.jar'
        expected_paper_hash = result.metadata['server']['jar_sha256']
        if atomic_copy(paper_jar, server_dir / server_filename) != expected_paper_hash:
            raise ValueError("Paper JAR changed while preparing the isolated server")
        runtime_cache = provider.runtime_cache(server, result.metadata['server'], cache_dir)
        cache_info = {'path': str(runtime_cache.resolve()) if runtime_cache else None, 'seeded': False}
        result.metadata['runtime_cache'] = cache_info
        if server.type == 'paper':
            result.metadata['paper_runtime_cache'] = cache_info
        if runtime_cache:
            with file_lock(runtime_cache.with_suffix('.lock'), control):
                cache_info['seeded'] = _seed_paper_runtime(server_dir, runtime_cache)
        shutil.copy2(plugin, plugins_dir / plugin.name)
        if sha256_file(plugins_dir / plugin.name) != result.metadata['plugin_jar_sha256']:
            raise ValueError('target JAR changed after preflight')
        for dependency in dependencies or []:
            if not dependency.is_file():
                result.result = "ENVIRONMENT_INVALID"
                result.failure_stage = "environment"
                result.reason = f"dependency does not exist: {dependency}"
                result.checks.append(Check("Dependency", "FAIL", result.reason))
                return result
            shutil.copy2(dependency, plugins_dir / dependency.name)
            expected_hash = next(
                (
                    item.get("plugin_jar_sha256")
                    for item in result.metadata.get("dependencies", [])
                    if item.get("plugin_jar") == str(dependency.resolve())
                ),
                None,
            )
            if expected_hash and sha256_file(plugins_dir / dependency.name) != expected_hash:
                raise ValueError(f"dependency JAR changed after preflight: {dependency}")
        probe_path = plugins_dir / PROBE_FILE_NAME
        run_id = uuid.uuid4().hex
        result.metadata['probe_run_id'] = run_id
        try:
            build_probe_plugin(
                server_dir / server_filename,
                plugins_dir,
                str(result.metadata.get("plugin_name") or ""),
                probe_path,
                java_bin,
                java_major,
                run_id=run_id,
                regionized=result.metadata['server']['regionized_runtime'],
                standalone_api=server.runtime == 'bukkit',
            )
        except RuntimeError as exc:
            result.result = "ENVIRONMENT_INVALID"
            result.failure_stage = "runtime_probe"
            result.reason = str(exc)
            result.checks.append(Check("Runtime probe", "FAIL", str(exc)))
            return result
        (server_dir / "eula.txt").write_text("eula=true\n", encoding="utf-8")
        control.check()
        server_port = _lease_port()
        _write_server_properties(server_dir, server_port)
        result.metadata["server_port"] = server_port
        command = provider.command(server, java_bin, server_filename)
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
            expected_version=str(result.metadata.get('plugin_version') or '') or None,
            expected_main=result.metadata['plugin_main'], expected_source=plugins_dir / plugin.name,
            run_id=run_id,
            allowed_sources=provider.allowed_sources(server, plugins_dir / plugin.name),
            provider_type=server.type, control=control, environment_index=environment_index,
        )
        evidence = process_run.evidence
        result.evidence = evidence.events
        if evidence.direct_runtime_observed:
            result.metadata["runtime_probe"] = evidence.last_probe_payload
        result.result, result.failure_stage, result.reason = evidence.verdict(
            process_alive=process_run.exit_code is None,
            timed_out=process_run.timed_out,
        )
        try:
            if runtime_cache and not control.cancelled:
                with file_lock(runtime_cache.with_suffix('.lock'), control):
                    cache_info['captured'] = _cache_paper_runtime(server_dir, runtime_cache, server.version)
        except (OSError, ValueError) as exc:
            cache_info['captured'] = False
            result.checks.append(Check('Runtime cache', 'WARN', str(exc)))
        result.checks.extend(_runtime_checks(evidence, process_run))
        return result
    except (RunCancelled, KeyboardInterrupt):
        control.cancel()
        result.result, result.failure_stage, result.reason = 'CANCELLED', 'cancelled', 'run cancelled'
        return result
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        result.result = 'ENVIRONMENT_INVALID'
        result.failure_stage = 'environment'
        result.reason = f'{type(exc).__name__}: {exc}'
        result.checks.append(Check('Environment', 'FAIL', result.reason))
        return result
    finally:
        if server_port is not None:
            with _PORT_LOCK:
                _ACTIVE_PORTS.discard(server_port)


def write_report(result: VerificationResult, path: Path) -> None:
    reject_links(path)
    path = path.resolve()
    inputs = [Path(value) for value in result.metadata.get('protected_inputs', [])]
    inputs += [Path(result.metadata['plugin_jar'])] if result.metadata.get('plugin_jar') else []
    inputs.extend(Path(item['plugin_jar']) for item in result.metadata.get('dependencies', []))
    if result.metadata.get("paper_jar"):
        inputs.append(Path(result.metadata["paper_jar"]))
    if result.metadata.get('server', {}).get('jar'):
        inputs.append(Path(result.metadata['server']['jar']))
    if result.log_path:
        inputs.append(Path(result.log_path))
    protect_inputs(path, inputs)
    for root in [result.metadata.get('cache_dir'), str(Path(result.workdir) / 'server') if result.workdir else None]:
        if root and (path == Path(root).resolve() or Path(root).resolve() in path.parents):
            raise ValueError('report path conflicts with cache/server artifacts')
    payload = result.to_dict()
    payload['report_path'] = str(path)
    atomic_json(path, payload)
    result.report_path = str(path)


def validate_plugin_inputs(plugin: Path, metadata: dict, dependencies: list[Path]) -> list[dict]:
    names = {PROBE_PLUGIN_NAME.casefold()}
    files = {'pluginmatrix-runtime-probe.jar', PROBE_FILE_NAME.casefold(), (PROBE_FILE_NAME + '.tmp').casefold()}
    result = []
    identities = []
    for path, info in [(plugin, metadata)] + [(path, inspect_plugin(path)[0]) for path in dependencies]:
        name = str(info.get('plugin_name') or '').casefold()
        if not path.name.lower().endswith('.jar') or any(char in path.name for char in ':\\') or path.name.endswith((' ', '.')):
            raise ValueError(f'unsupported plugin JAR filename: {path.name}')
        if path.name.casefold() in files or name in names:
            raise ValueError(f'plugin filename or identity conflicts with another plugin or runtime probe: {path}')
        files.add(path.name.casefold())
        names.add(name)
        identities.append((name, info.get('provides', [])))
        if path != plugin:
            result.append(info)
    for name, aliases in identities:
        for alias in aliases:
            if alias.casefold() in names:
                raise ValueError(f'plugin provides identity conflicts with another plugin or runtime probe: {alias}')
            names.add(alias.casefold())
    return result
