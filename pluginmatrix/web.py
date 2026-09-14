"""Loopback-only Web UI adapter over the public application API."""
from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

from . import __version__, application
from .control import RunControl
from .files import atomic_text, reject_links
from .external import run_external
from .matrix import MatrixConfigError
from .providers import parse_server
from .scheduler import MAX_PARALLEL, validate_parallel


MAX_JSON_BYTES = 1024 * 1024
MAX_JAR_BYTES = 512 * 1024 * 1024
MAX_JOBS = 64
MAX_EVENTS = 512
MAX_ENVIRONMENTS = 256
MAX_HTTP_CONNECTIONS = 32
REQUEST_SECONDS = 30
MAX_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024
LOOPBACK_HOST = "127.0.0.1"


class WebError(ValueError):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class Artifact:
    id: str
    label: str
    path: Path
    content_type: str
    device: int
    inode: int
    size: int
    modified: int
    changed: int


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _open_regular(path: Path):
    """Open without blocking on a raced FIFO; validate the descriptor, not just its name."""
    reject_links(path)
    before = path.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise ValueError("expected a regular file with one link")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NONBLOCK", 0)
                 | getattr(os, "O_NOFOLLOW", 0))
    try:
        info = os.fstat(fd)
        reject_links(path)
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or _identity(info) != _identity(before) or _identity(path.stat()) != _identity(info)):
            raise ValueError("file changed while opening")
        return os.fdopen(fd, "rb")
    except BaseException:
        os.close(fd)
        raise


@dataclass
class Job:
    id: str
    mode: str
    slots: int
    control: RunControl
    request: dict
    status: str = "queued"
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    error: str | None = None
    summary: dict | None = None
    artifacts: dict[str, Artifact] = field(default_factory=dict)
    thread: threading.Thread | None = None
    _events: deque = field(default_factory=lambda: deque(maxlen=MAX_EVENTS))
    _next_event: int = 1
    _lock: threading.RLock = field(default_factory=threading.RLock)

    def observe(self, event) -> None:
        with self._lock:
            self._events.append({"sequence": self._next_event, **event.to_dict()})
            self._next_event += 1

    def snapshot(self, after: int = 0, include_events: bool = True) -> dict:
        with self._lock:
            events = [event for event in self._events if event["sequence"] > after] if include_events else []
            return {
                "id": self.id,
                "mode": self.mode,
                "status": self.status,
                "cancel_requested": self.control.cancelled,
                "created_at": self.created_at,
                "started_at": self.started_at,
                "completed_at": self.completed_at,
                "error": self.error,
                "summary": self.summary,
                "events": events,
                "next_event": self._next_event - 1,
                "artifacts": [
                    {
                        "id": item.id,
                        "label": item.label,
                        "name": item.path.name,
                        "path": str(item.path),
                        "size": item.size,
                        "url": f"/api/jobs/{self.id}/artifacts/{item.id}",
                    }
                    for item in self.artifacts.values()
                ],
            }


class WebApplication:
    """Own Web UI jobs, uploaded local copies, and the global eight-slot limit."""

    def __init__(self, state_dir: Path = Path(".pluginmatrix/web"), cache_dir: Path = Path(".pluginmatrix/cache")):
        self.state_dir = Path(state_dir).expanduser().absolute()
        self.cache_dir = Path(cache_dir).expanduser().absolute()
        reject_links(self.state_dir)
        reject_links(self.cache_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self._uploads = tempfile.TemporaryDirectory(prefix="pluginmatrix-web-")
        self.upload_root = Path(self._uploads.name).resolve()
        self._files: dict[str, Path] = {}
        self._jobs: dict[str, Job] = {}
        self._lock = threading.RLock()
        self._active_slots = 0
        self._closing = False
        self._upload_count = 0
        self._upload_bytes = 0

    def import_file(self, stream, length: int, encoded_name: str, kind: str) -> dict:
        if kind not in {"plugin", "dependency", "server"}:
            raise WebError(HTTPStatus.BAD_REQUEST, "file kind must be plugin, dependency, or server")
        if length <= 0 or length > MAX_JAR_BYTES:
            raise WebError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "JAR must be between 1 byte and 512 MiB")
        if len(encoded_name) > 2048:
            raise WebError(HTTPStatus.BAD_REQUEST, "file name is too long")
        try:
            name = unquote(encoded_name, errors="strict")
        except UnicodeError as exc:
            raise WebError(HTTPStatus.BAD_REQUEST, "file name is not valid UTF-8") from exc
        if (not name or len(name) > 255 or name in {".", ".."} or "/" in name or "\\" in name or ":" in name
                or any(ord(character) < 32 for character in name) or Path(name).suffix.lower() != ".jar"):
            raise WebError(HTTPStatus.BAD_REQUEST, "select a JAR with a plain file name")
        with self._lock:
            if self._closing:
                raise WebError(HTTPStatus.SERVICE_UNAVAILABLE, "Web UI is shutting down")
            if self._upload_count >= 256 or self._upload_bytes + length > MAX_UPLOAD_BYTES:
                raise WebError(HTTPStatus.CONFLICT, "session upload limit reached (256 files or 2 GiB)")
            self._upload_count += 1
            self._upload_bytes += length
            file_id = uuid.uuid4().hex
            destination = self.upload_root / f"{file_id}.jar"
        remaining = length
        digest = hashlib.sha256()
        try:
            with destination.open("xb") as output:
                while remaining:
                    chunk = stream.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise WebError(HTTPStatus.BAD_REQUEST, "request body ended before Content-Length")
                    output.write(chunk)
                    digest.update(chunk)
                    remaining -= len(chunk)
            with self._lock:
                if self._closing:
                    raise WebError(HTTPStatus.SERVICE_UNAVAILABLE, "Web UI is shutting down")
                self._files[file_id] = destination
        except BaseException:
            destination.unlink(missing_ok=True)
            with self._lock:
                self._upload_count -= 1
                self._upload_bytes -= length
            raise
        return {"file_id": file_id, "name": name, "size": length, "sha256": digest.hexdigest(), "kind": kind}

    def import_configuration(self, path_value: object) -> dict:
        path = self._path_value(path_value, "config", ".json", MAX_JSON_BYTES)
        with _open_regular(path) as stream:
            config = application.load_matrix_config(path, stream=stream)
        return {"source": str(path), "configuration": config.to_dict()}

    def generate_configuration(self, payload: object) -> dict:
        request = self._normalize_request(payload)
        return self._configuration_document(request, include_outputs=False)

    def submit(self, payload: object) -> Job:
        request = self._normalize_request(payload)
        slots = 1 if request["mode"] == "single" else request["options"]["max_parallel"]
        with self._lock:
            if self._closing:
                raise WebError(HTTPStatus.SERVICE_UNAVAILABLE, "Web UI is shutting down")
            self._discard_old_jobs()
            if len(self._jobs) >= MAX_JOBS:
                raise WebError(HTTPStatus.CONFLICT, "job history is full; restart the local Web UI after current jobs finish")
            if self._active_slots + slots > MAX_PARALLEL:
                raise WebError(
                    HTTPStatus.CONFLICT,
                    f"active jobs reserve {self._active_slots} of {MAX_PARALLEL} environment slots; reduce concurrency or wait",
                )
            job_id = uuid.uuid4().hex
            holder: list[Job] = []
            control = RunControl(lambda event: holder[0].observe(event))
            job = Job(job_id, request["mode"], slots, control, request)
            holder.append(job)
            self._jobs[job_id] = job
            self._active_slots += slots
            thread = threading.Thread(target=self._run_job, args=(job,), name=f"pluginmatrix-web-{job_id[:8]}", daemon=False)
            job.thread = thread
            try:
                thread.start()
            except BaseException:
                self._active_slots -= slots
                del self._jobs[job_id]
                raise
            return job

    def list_jobs(self) -> list[dict]:
        with self._lock:
            jobs = list(self._jobs.values())
        return [job.snapshot(include_events=False) for job in reversed(jobs)]

    def get_job(self, job_id: str) -> Job:
        if len(job_id) != 32 or any(character not in "0123456789abcdef" for character in job_id):
            raise WebError(HTTPStatus.NOT_FOUND, "job not found")
        with self._lock:
            job = self._jobs.get(job_id)
        if not job:
            raise WebError(HTTPStatus.NOT_FOUND, "job not found")
        return job

    def cancel(self, job_id: str) -> Job:
        job = self.get_job(job_id)
        with job._lock:
            if job.status in {"queued", "running"}:
                job.status = "cancelling"
                job.control.cancel()
        return job

    def artifact(self, job_id: str, artifact_id: str) -> tuple[Artifact, object]:
        job = self.get_job(job_id)
        with job._lock:
            artifact = job.artifacts.get(artifact_id)
        if not artifact:
            raise WebError(HTTPStatus.NOT_FOUND, "artifact not found")
        try:
            reject_links(artifact.path)
            if artifact.path.resolve() != artifact.path:
                raise ValueError("artifact path changed")
            stream = _open_regular(artifact.path)
            info = os.fstat(stream.fileno())
            if _identity(info) != (artifact.device, artifact.inode, artifact.size, artifact.modified, artifact.changed):
                stream.close()
                raise ValueError("artifact changed after job completion")
        except (OSError, ValueError) as exc:
            raise WebError(HTTPStatus.CONFLICT, f"artifact is no longer the completed file: {exc}") from exc
        return artifact, stream

    def begin_close(self) -> list[Job]:
        with self._lock:
            self._closing = True
            jobs = list(self._jobs.values())
        for job in jobs:
            if job.thread and job.thread.is_alive():
                job.control.cancel()
        return jobs

    def close(self) -> None:
        jobs = self.begin_close()
        for job in jobs:
            if job.thread:
                while job.thread.is_alive():
                    job.thread.join(timeout=0.2)
        self._uploads.cleanup()

    def _normalize_request(self, payload: object) -> dict:
        if not isinstance(payload, dict):
            raise WebError(HTTPStatus.BAD_REQUEST, "request must be a JSON object")
        unknown = set(payload) - {"mode", "plugin", "dependencies", "environments", "options"}
        if unknown:
            raise WebError(HTTPStatus.BAD_REQUEST, f"unknown request fields: {sorted(unknown)}")
        mode = payload.get("mode", "single")
        if mode not in {"single", "matrix"}:
            raise WebError(HTTPStatus.BAD_REQUEST, "mode must be single or matrix")
        plugin = self._file_reference(payload.get("plugin"), "plugin", ".jar", MAX_JAR_BYTES)
        dependencies = payload.get("dependencies", [])
        if not isinstance(dependencies, list) or len(dependencies) > 128:
            raise WebError(HTTPStatus.BAD_REQUEST, "dependencies must be an array of at most 128 JARs")
        dependencies = [self._file_reference(value, "dependency", ".jar", MAX_JAR_BYTES) for value in dependencies]
        environments = payload.get("environments")
        if not isinstance(environments, list) or not environments or len(environments) > MAX_ENVIRONMENTS:
            raise WebError(HTTPStatus.BAD_REQUEST, "environments must contain between 1 and 256 entries")
        if mode == "single" and len(environments) != 1:
            raise WebError(HTTPStatus.BAD_REQUEST, "single mode requires exactly one environment")
        normalized_environments = []
        for index, item in enumerate(environments):
            if not isinstance(item, dict) or set(item) - {"server", "java"}:
                raise WebError(HTTPStatus.BAD_REQUEST, f"environment #{index + 1} must contain only server and java")
            java = item.get("java")
            if isinstance(java, int) and not isinstance(java, bool):
                java = str(java)
            if not isinstance(java, str) or not java.strip() or len(java) > 4096 or "\x00" in java:
                raise WebError(HTTPStatus.BAD_REQUEST, f"environment #{index + 1} needs a Java version or executable")
            raw_server = item.get("server")
            if not isinstance(raw_server, dict):
                raise WebError(HTTPStatus.BAD_REQUEST, f"environment #{index + 1} needs a server object")
            raw_server = dict(raw_server)
            if raw_server.get("type") in {"local", "custom"}:
                raw_server["jar"] = str(self._file_reference(raw_server.get("jar"), "server", ".jar", MAX_JAR_BYTES))
            try:
                server = parse_server(raw_server)
            except (OSError, ValueError) as exc:
                raise WebError(HTTPStatus.BAD_REQUEST, f"environment #{index + 1}: {exc}") from exc
            normalized_environments.append({"server": server, "java": java.strip()})
        options = payload.get("options", {})
        if not isinstance(options, dict) or set(options) - {"timeout", "stability_window", "max_parallel"}:
            raise WebError(HTTPStatus.BAD_REQUEST, "options accepts timeout, stability_window, and max_parallel")
        timeout = options.get("timeout", 120)
        stability = options.get("stability_window", 5)
        parallel = options.get("max_parallel", 1)
        if type(timeout) is not int or not 1 <= timeout <= 3600:
            raise WebError(HTTPStatus.BAD_REQUEST, "timeout must be an integer from 1 to 3600 seconds")
        if type(stability) is not int or not 1 <= stability <= 600:
            raise WebError(HTTPStatus.BAD_REQUEST, "stability_window must be an integer from 1 to 600 seconds")
        try:
            parallel = validate_parallel(parallel)
        except ValueError as exc:
            raise WebError(HTTPStatus.BAD_REQUEST, str(exc)) from exc
        if mode == "single":
            parallel = 1
        return {
            "mode": mode,
            "plugin": plugin,
            "dependencies": dependencies,
            "environments": normalized_environments,
            "options": {"timeout": timeout, "stability_window": stability, "max_parallel": parallel},
        }

    def _file_reference(self, value: object, label: str, suffix: str, maximum: int) -> Path:
        if isinstance(value, dict) and set(value) == {"file_id"}:
            file_id = value["file_id"]
            if not isinstance(file_id, str):
                raise WebError(HTTPStatus.BAD_REQUEST, f"{label} file_id is invalid")
            with self._lock:
                path = self._files.get(file_id)
            if path is None:
                raise WebError(HTTPStatus.BAD_REQUEST, f"{label} imported file is missing or expired")
        else:
            path = self._path_value(value, label, suffix, maximum)
        if not path.is_file() or path.suffix.lower() != suffix or path.stat().st_size > maximum:
            raise WebError(HTTPStatus.BAD_REQUEST, f"{label} must be an existing {suffix} file of at most {maximum // 1024 // 1024} MiB")
        return path.resolve()

    @staticmethod
    def _path_value(value: object, label: str, suffix: str, maximum: int) -> Path:
        if not isinstance(value, str) or not value.strip() or len(value) > 4096 or "\x00" in value:
            raise WebError(HTTPStatus.BAD_REQUEST, f"{label} path is required")
        path = Path(value).expanduser().resolve()
        if not path.is_file() or path.suffix.lower() != suffix or path.stat().st_size > maximum:
            raise WebError(HTTPStatus.BAD_REQUEST, f"{label} must be an existing {suffix} file")
        return path

    def _configuration_document(self, request: dict, include_outputs: bool, job_id: str | None = None) -> dict:
        environments = [{"server": item["server"].to_dict(), "java": item["java"]} for item in request["environments"]]
        options = dict(request["options"])
        if include_outputs:
            if not job_id:
                raise ValueError("job id required for output configuration")
            options.update(
                work_dir=str((self.state_dir / "runs").resolve()),
                cache_dir=str(self.cache_dir.resolve()),
                report=str((self.state_dir / "reports" / f"{job_id}.json").resolve()),
                html_report=str((self.state_dir / "reports" / f"{job_id}.html").resolve()),
            )
        return {
            "plugin": str(request["plugin"]),
            "dependencies": [str(path) for path in request["dependencies"]],
            "environments": environments,
            "options": options,
        }

    def _run_job(self, job: Job) -> None:
        with job._lock:
            job.status = "running" if not job.control.cancelled else "cancelling"
            job.started_at = time.time()
        try:
            document = self._configuration_document(job.request, include_outputs=True, job_id=job.id)
            report_path = Path(document["options"]["report"])
            html_path = Path(document["options"]["html_report"])
            if job.mode == "single":
                environment = job.request["environments"][0]
                result = application.run_single(
                    plugin=job.request["plugin"],
                    server=environment["server"],
                    java=environment["java"],
                    work_root=Path(document["options"]["work_dir"]),
                    cache_dir=Path(document["options"]["cache_dir"]),
                    timeout=document["options"]["timeout"],
                    stability=document["options"]["stability_window"],
                    dependencies=job.request["dependencies"],
                    report_path=report_path,
                    html_path=html_path,
                    control=job.control,
                )
                summary = {
                    "total": 1,
                    "passed": int(result.result == "PASS"),
                    "failed": int(result.result != "PASS"),
                    "environments": [{
                        "id": environment["server"].type,
                        "provider": environment["server"].type,
                        "verdict": result.result,
                        "failure_stage": result.failure_stage,
                        "reason": result.reason,
                        "report_path": result.report_path,
                        "log_path": result.log_path,
                        "run_dir": result.workdir,
                        "checks": [vars(check) for check in result.checks],
                    }],
                }
                candidates = [("JSON report", report_path), ("HTML report", html_path), ("server.log", Path(result.log_path) if result.log_path else None)]
            else:
                config_path = self.state_dir / "configs" / f"{job.id}.json"
                atomic_text(config_path, json.dumps(document, indent=2, ensure_ascii=True) + "\n", overwrite=False)
                config = application.load_matrix_config(config_path)
                report = application.run_matrix(config, control=job.control)
                summary = {
                    **report.get("summary", {}),
                    "environments": [
                        {
                            "id": item.get("id"),
                            "provider": (item.get("metadata", {}).get("server", {}) or item.get("resolved", {}).get("server", {})).get("server_type"),
                            "verdict": item.get("verdict"),
                            "failure_stage": item.get("failure_stage"),
                            "reason": item.get("reason"),
                            "report_path": item.get("artifacts", {}).get("runtime_report"),
                            "log_path": item.get("artifacts", {}).get("server_log"),
                            "run_dir": item.get("artifacts", {}).get("run_dir"),
                        }
                        for item in report.get("environments", [])
                    ],
                }
                candidates = [("Matrix JSON report", report_path), ("Matrix HTML report", html_path)]
                for index, item in enumerate(report.get("environments", []), start=1):
                    artifacts = item.get("artifacts", {}) if isinstance(item.get("artifacts"), dict) else {}
                    candidates.extend([
                        (f"Environment {index} JSON report", Path(artifacts["runtime_report"]) if artifacts.get("runtime_report") else None),
                        (f"Environment {index} server.log", Path(artifacts["server_log"]) if artifacts.get("server_log") else None),
                    ])
            registered = self._register_artifacts(candidates)
            with job._lock:
                job.summary = summary
                job.artifacts = registered
                job.status = "completed"
        except BaseException as exc:
            with job._lock:
                job.error = f"{type(exc).__name__}: {exc}"[:4096]
                job.status = "failed"
        finally:
            with job._lock:
                job.completed_at = time.time()
            with self._lock:
                self._active_slots -= job.slots

    @staticmethod
    def _register_artifacts(candidates) -> dict[str, Artifact]:
        artifacts: dict[str, Artifact] = {}
        seen: set[Path] = set()
        for label, candidate in candidates:
            if candidate is None:
                continue
            try:
                reject_links(Path(candidate))
                path = Path(candidate).resolve(strict=True)
                reject_links(path)
                if not path.is_file() or path in seen:
                    continue
                with _open_regular(path) as stream:
                    info = os.fstat(stream.fileno())
            except (OSError, ValueError):
                continue
            seen.add(path)
            artifact_id = uuid.uuid4().hex
            content_type = {
                ".html": "text/html; charset=utf-8",
                ".json": "application/json; charset=utf-8",
                ".log": "text/plain; charset=utf-8",
                ".txt": "text/plain; charset=utf-8",
            }.get(path.suffix.lower(), "application/octet-stream")
            artifacts[artifact_id] = Artifact(artifact_id, label, path, content_type, *_identity(info))
        return artifacts

    def _discard_old_jobs(self) -> None:
        if len(self._jobs) < MAX_JOBS:
            return
        for job_id, job in list(self._jobs.items()):
            if job.status in {"completed", "failed"}:
                del self._jobs[job_id]
                if len(self._jobs) < MAX_JOBS:
                    return


class LocalWebServer(ThreadingHTTPServer):
    daemon_threads = False
    allow_reuse_address = False

    def __init__(self, address, app: WebApplication):
        if address[0] != LOOPBACK_HOST:
            raise ValueError("Web UI must bind to 127.0.0.1")
        self.app = app
        self._connections = set()
        self._connection_lock = threading.Lock()
        self._connection_slots = threading.BoundedSemaphore(MAX_HTTP_CONNECTIONS)
        self._closed = False
        self.session_token = uuid.uuid4().hex + uuid.uuid4().hex
        super().__init__(address, LocalRequestHandler)
        port = self.server_address[1]
        self.allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        self.allowed_origins = {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}

    def process_request(self, request, client_address):
        with self._connection_lock:
            if self._closed or not self._connection_slots.acquire(blocking=False):
                self.shutdown_request(request)
                return
            self._connections.add(request)
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._release_connection(request)
            raise

    def _release_connection(self, request):
        with self._connection_lock:
            self._connections.discard(request)
            self._connection_slots.release()

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._release_connection(request)

    def server_close(self):
        with self._connection_lock:
            self._closed = True
            connections = list(self._connections)
        self.app.begin_close()
        for connection in connections:
            _interrupt_socket(connection)
        try:
            super().server_close()
        finally:
            self.app.close()


def _interrupt_socket(connection):
    try:
        connection.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    # makefile() retains the socket: close() alone defers the native close.
    # On Windows shutdown() also need not wake an already-waiting timed recv.
    try:
        descriptor = connection.detach()
        if descriptor != -1:
            socket.close(descriptor)
    except OSError:
        pass


class LocalRequestHandler(BaseHTTPRequestHandler):
    server: LocalWebServer
    protocol_version = "HTTP/1.1"
    server_version = "PluginMatrix"
    sys_version = ""

    def setup(self):
        super().setup()
        self.connection.settimeout(REQUEST_SECONDS)

    def handle(self):
        # A socket timeout alone resets on every byte and permits slowloris.
        timer = threading.Timer(REQUEST_SECONDS, _interrupt_socket, args=(self.connection,))
        timer.daemon = True
        timer.start()
        try:
            super().handle()
        except OSError:
            pass
        finally:
            timer.cancel()

    def handle_expect_100(self):
        self.send_error(HTTPStatus.EXPECTATION_FAILED)
        return False

    def log_message(self, _format, *args):
        return

    def do_GET(self):
        try:
            self._validate_request()
            route = urlsplit(self.path)
            if route.query and not route.path.startswith("/api/jobs/"):
                raise WebError(HTTPStatus.BAD_REQUEST, "unexpected query string")
            if route.path == "/health":
                self._json({"status": "ok", "version": __version__})
                return
            if route.path == "/":
                content = self._resource("index.html").replace("{{SESSION_TOKEN}}", self.server.session_token).replace("{{VERSION}}", __version__)
                self._send(content.encode("utf-8"), "text/html; charset=utf-8", cookie=True)
                return
            if route.path in {"/assets/app.js", "/assets/style.css"}:
                name = route.path.rsplit("/", 1)[1]
                content_type = "text/javascript; charset=utf-8" if name.endswith(".js") else "text/css; charset=utf-8"
                self._send(self._resource(name).encode("utf-8"), content_type)
                return
            self._require_cookie()
            if route.path == "/api/providers":
                self._json({"schema": 1, "providers": application.inspect_providers()})
                return
            if route.path == "/api/jobs":
                self._json({"schema": 1, "jobs": self.server.app.list_jobs()})
                return
            parts = route.path.strip("/").split("/")
            if len(parts) == 3 and parts[:2] == ["api", "jobs"]:
                after_values = {}
                if route.query:
                    for pair in route.query.split("&"):
                        key, separator, value = pair.partition("=")
                        if not separator or key != "after" or not value.isdigit():
                            raise WebError(HTTPStatus.BAD_REQUEST, "only a non-negative after event cursor is accepted")
                        after_values[key] = int(value)
                self._json(self.server.app.get_job(parts[2]).snapshot(after=after_values.get("after", 0)))
                return
            if len(parts) == 5 and parts[:2] == ["api", "jobs"] and parts[3] == "artifacts" and not route.query:
                artifact, stream = self.server.app.artifact(parts[2], parts[4])
                try:
                    headers = {"Content-Disposition": f"inline; filename*=UTF-8''{quote(artifact.path.name)}"}
                    self._send_stream(stream, artifact.size, artifact.content_type, headers)
                finally:
                    stream.close()
                return
            raise WebError(HTTPStatus.NOT_FOUND, "not found")
        except WebError as exc:
            self._error(exc.status, str(exc))
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception:
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "local Web UI request failed")

    def do_POST(self):
        try:
            self._validate_request()
            self._require_cookie()
            if self.headers.get("Origin") not in self.server.allowed_origins:
                raise WebError(HTTPStatus.FORBIDDEN, "request Origin is not this local Web UI")
            if self.headers.get("X-PluginMatrix-Token") != self.server.session_token:
                raise WebError(HTTPStatus.FORBIDDEN, "missing or invalid request token")
            if self.headers.get("Transfer-Encoding"):
                raise WebError(HTTPStatus.BAD_REQUEST, "chunked request bodies are not accepted")
            route = urlsplit(self.path)
            if route.query:
                raise WebError(HTTPStatus.BAD_REQUEST, "unexpected query string")
            if route.path == "/api/import":
                length = self._content_length(MAX_JAR_BYTES)
                if self.headers.get_content_type() != "application/octet-stream":
                    raise WebError(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "JAR import requires application/octet-stream")
                name = self.headers.get("X-PluginMatrix-Filename", "")
                kind = self.headers.get("X-PluginMatrix-File-Kind", "")
                self._json(self.server.app.import_file(self.rfile, length, name, kind), HTTPStatus.CREATED)
                return
            payload = self._read_json()
            if route.path == "/api/config/import":
                if not isinstance(payload, dict) or set(payload) != {"path"}:
                    raise WebError(HTTPStatus.BAD_REQUEST, "config import requires only path")
                self._json(self.server.app.import_configuration(payload["path"]))
                return
            if route.path == "/api/config/generate":
                self._json({"schema": 1, "configuration": self.server.app.generate_configuration(payload)})
                return
            if route.path == "/api/jobs":
                job = self.server.app.submit(payload)
                self._json(job.snapshot(), HTTPStatus.ACCEPTED)
                return
            parts = route.path.strip("/").split("/")
            if len(parts) == 4 and parts[:2] == ["api", "jobs"] and parts[3] == "cancel":
                if payload not in ({}, None):
                    raise WebError(HTTPStatus.BAD_REQUEST, "cancel request body must be an empty JSON object")
                self._json(self.server.app.cancel(parts[2]).snapshot())
                return
            raise WebError(HTTPStatus.NOT_FOUND, "not found")
        except WebError as exc:
            self._error(exc.status, str(exc))
        except (BrokenPipeError, ConnectionResetError):
            return
        except (MatrixConfigError, OSError, ValueError) as exc:
            self._error(HTTPStatus.BAD_REQUEST, str(exc)[:4096])
        except Exception:
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "local Web UI request failed")

    def _validate_request(self) -> None:
        self.close_connection = True
        if (not self.path.startswith("/") or self.path.startswith("//") or "#" in self.path
                or self.headers.defects):
            raise WebError(HTTPStatus.BAD_REQUEST, "invalid request target or headers")
        for name in ("Host", "Origin", "Cookie", "Content-Length", "Content-Type", "X-PluginMatrix-Token",
                     "X-PluginMatrix-Filename", "X-PluginMatrix-File-Kind"):
            values = self.headers.get_all(name, [])
            if len(values) > 1 or any("\r" in value or "\n" in value for value in values):
                raise WebError(HTTPStatus.BAD_REQUEST, "duplicate or folded request header")
        if "Transfer-Encoding" in self.headers or "Expect" in self.headers:
            raise WebError(HTTPStatus.BAD_REQUEST, "unsupported request framing")
        if self.command == "GET" and self.headers.get("Content-Length", "0") != "0":
            raise WebError(HTTPStatus.BAD_REQUEST, "GET bodies are not accepted")
        if "Origin" in self.headers and self.headers["Origin"] not in self.server.allowed_origins:
            raise WebError(HTTPStatus.FORBIDDEN, "request Origin is not this local Web UI")
        try:
            if not ipaddress.ip_address(self.client_address[0]).is_loopback:
                raise WebError(HTTPStatus.FORBIDDEN, "only loopback clients are accepted")
        except ValueError as exc:
            raise WebError(HTTPStatus.FORBIDDEN, "invalid client address") from exc
        if self.headers.get("Host", "").lower() not in self.server.allowed_hosts:
            raise WebError(HTTPStatus.BAD_REQUEST, "invalid local Host header")

    def _require_cookie(self) -> None:
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
        except Exception as exc:
            raise WebError(HTTPStatus.FORBIDDEN, "invalid session cookie") from exc
        value = cookie.get("PluginMatrixSession")
        if value is None or value.value != self.server.session_token:
            raise WebError(HTTPStatus.FORBIDDEN, "open the local Web UI before using its API")

    def _read_json(self):
        length = self._content_length(MAX_JSON_BYTES)
        if self.headers.get_content_type() != "application/json":
            raise WebError(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "request requires application/json")
        data = self.rfile.read(length)
        if len(data) != length:
            raise WebError(HTTPStatus.BAD_REQUEST, "request body ended before Content-Length")
        try:
            return json.loads(data)
        except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
            raise WebError(HTTPStatus.BAD_REQUEST, f"invalid JSON request: {exc}") from exc

    def _content_length(self, maximum: int) -> int:
        raw = self.headers.get("Content-Length")
        if raw is None or not raw.isascii() or not raw.isdigit() or len(raw) > 10:
            raise WebError(HTTPStatus.LENGTH_REQUIRED, "a numeric Content-Length is required")
        length = int(raw)
        if length > maximum:
            raise WebError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "request body exceeds the local UI limit")
        return length

    @staticmethod
    def _resource(name: str) -> str:
        return resources.files("pluginmatrix.webui").joinpath(name).read_text(encoding="utf-8")

    def _json(self, payload, status: int = HTTPStatus.OK) -> None:
        content = json.dumps(payload, ensure_ascii=True).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
        self._send(content.encode("utf-8"), "application/json; charset=utf-8", status=status)

    def _error(self, status: int, message: str) -> None:
        try:
            self._json({"error": message}, status)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _security_headers(self, allow_inline_style: bool = False) -> None:
        self.send_header("Connection", "close")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header(
            "Content-Security-Policy",
            ("default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
             if allow_inline_style else
             "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
             "base-uri 'none'; frame-ancestors 'none'; form-action 'none'"),
        )

    def _send(self, content: bytes, content_type: str, status: int = HTTPStatus.OK, cookie: bool = False) -> None:
        self.send_response(status)
        self._security_headers()
        if cookie:
            self.send_header("Set-Cookie", f"PluginMatrixSession={self.server.session_token}; HttpOnly; SameSite=Strict; Path=/")
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_stream(self, stream, size: int, content_type: str, headers: dict[str, str]) -> None:
        self.send_response(HTTPStatus.OK)
        self._security_headers(allow_inline_style=content_type.startswith("text/html"))
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(size))
        for name, value in headers.items():
            self.send_header(name, value)
        self.end_headers()
        remaining = size
        while remaining:
            chunk = stream.read(min(remaining, 1024 * 1024))
            if not chunk:
                break
            self.wfile.write(chunk)
            remaining -= len(chunk)


def create_server(port: int = 8642, state_dir: Path = Path(".pluginmatrix/web"),
                  cache_dir: Path = Path(".pluginmatrix/cache")) -> LocalWebServer:
    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError("Web UI port must be an integer from 0 to 65535")
    return LocalWebServer((LOOPBACK_HOST, port), WebApplication(state_dir, cache_dir))


def serve(port: int = 8642, open_browser: bool = True, state_dir: Path = Path(".pluginmatrix/web"),
          cache_dir: Path = Path(".pluginmatrix/cache")) -> int:
    server = create_server(port, state_dir, cache_dir)
    url = f"http://{LOOPBACK_HOST}:{server.server_address[1]}/"
    print(f"PluginMatrix Web UI: {url}", flush=True)
    print("Local-only session; press Ctrl+C to cancel active jobs, clean server process trees, and stop.", flush=True)
    if open_browser:
        threading.Timer(0.1, _open_browser, args=(url,)).start()
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        server.app.close()
    return 0


def _open_browser(url: str) -> None:
    try:
        if os.name == "nt":
            os.startfile(url)  # type: ignore[attr-defined]
        else:
            command = ["open" if sys.platform == "darwin" else "xdg-open", url]
            run_external(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
    except OSError:
        pass
