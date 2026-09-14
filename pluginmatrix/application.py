"""GUI-ready application API, version 1. No CLI argument parsing or terminal output."""
from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path

from .control import ProgressEvent, RunControl
from .files import atomic_json, atomic_text, protect_inputs, reject_links, validate_output_paths
from .matrix import (MatrixConfig, MatrixConfigError, load_matrix_config, validate_matrix_preconditions,
                     validate_matrix_paths, matrix_exit_code, run_matrix as _run_matrix, _check_writable_directory)
from .providers import ServerSpec, get_provider, inspect_providers, parse_server
from .reports import load_report, render_html_report, _render_html_report
from .locking import file_lock, report_locks, validate_report_locks
from .runtime import verify as _verify, resolve_java, write_report
from .probe import resolve_javac
from .external import run_external

API_VERSION = 1
PROVIDER_CATALOG_TTL = 6 * 60 * 60
MAX_PROVIDER_CACHE_BYTES = 1024 * 1024


class _ReplaceableProviderCacheError(ValueError):
    """A regular bounded cache file whose contents may be refreshed safely."""


def validate_configuration(path: Path, network: bool = False) -> dict:
    """No server download/launch. Network mode resolves only official build metadata."""
    try:
        config = load_matrix_config(path)
        preflight = validate_matrix_preconditions(config)
        errors = [p['reason'] for p in preflight['providers'] if p['status'] == 'unsupported']
        resolved = []
        if network:
            for environment in config.environments:
                try:
                    resolved.append(get_provider(environment.server_spec.type).resolve(environment.server_spec))
                except (OSError, ValueError) as exc:
                    errors.append(f'{environment.environment_id}: {exc}')
        return {'schema': 1, 'valid': not errors, 'exit_code': 2 if errors else 0,
                'network': network, 'config': config.to_dict(), 'preflight': preflight,
                'resolved': resolved, 'errors': errors}
    except (OSError, ValueError) as exc:
        return {'schema': 1, 'valid': False, 'exit_code': 2, 'network': network, 'errors': [str(exc)]}


def run_matrix(config: MatrixConfig | Path, *, max_parallel: int | None = None,
               control: RunControl | None = None, progress=None, preflight=None) -> dict:
    if not isinstance(config, MatrixConfig):
        config = load_matrix_config(Path(config))
    if max_parallel is not None:
        config = replace(config, max_parallel=max_parallel)
    validate_matrix_paths(config)
    preflight = preflight if preflight is not None else validate_matrix_preconditions(config)
    return _run_matrix(config, progress=progress, preflight=preflight, control=control)


def run_single(*, plugin: Path, server: ServerSpec, java: str,
               work_root: Path = Path('.pluginmatrix/runs'), cache_dir: Path = Path('.pluginmatrix/cache'),
               timeout: int = 120, stability: int = 5, dependencies=None,
               report_path: Path | None = None, html_path: Path | None = None,
               control: RunControl | None = None):
    dependencies = list(dependencies or [])
    inputs = [plugin, *dependencies, *([server.jar] if server.jar else [])]
    validate_output_paths(work_root, cache_dir, inputs, report_path)
    if html_path:
        validate_output_paths(work_root, cache_dir, [*inputs, *([report_path] if report_path else [])], html_path)
    for lock in validate_report_locks([report_path, html_path], inputs):
        validate_output_paths(work_root, cache_dir, inputs, lock)
    with report_locks([report_path, html_path], inputs):
        control = control or RunControl()
        control.emit('environment_started', 0, provider=server.type)
        result = _verify(plugin, server.version, java, work_root, cache_dir, timeout, stability,
                         dependencies, server.build, server=server, control=control, environment_index=0)
        if report_path or result.workdir:
            write_report(result, report_path or Path(result.workdir) / 'result.json')
            if html_path:
                _render_html_report(Path(result.report_path), html_path)
        control.emit('environment_completed', 0, verdict=result.result)
        return result


def init_configuration(path: Path, *, plugin: Path, servers: list[ServerSpec], java: str,
                       force: bool = False, max_parallel: int = 1) -> Path:
    from .scheduler import validate_parallel
    validate_parallel(max_parallel)
    if path.suffix.lower() != '.json' or not servers:
        raise ValueError('init needs a .json destination and at least one server')
    path = path.absolute()
    inputs = [plugin, *(s.jar for s in servers if s.jar)]
    protect_inputs(path, inputs)
    for server in servers:
        get_provider(server.type).validate(server)
    def relative(p):
        try:
            return Path(os.path.relpath(Path(p).resolve(), path.parent)).as_posix()
        except ValueError:
            return str(Path(p).resolve())
    environments = []
    for server in servers:
        value = server.to_dict()
        if server.jar:
            value['jar'] = relative(server.jar)
        environments.append({'server': value, 'java': java})
    document = {'plugin': relative(plugin), 'environments': environments,
                'options': {'timeout': 120, 'stability_window': 5, 'max_parallel': max_parallel,
                            'report': '.pluginmatrix/matrix-report.json', 'html_report': '.pluginmatrix/matrix-report.html',
                            'work_dir': '.pluginmatrix/runs', 'cache_dir': '.pluginmatrix/cache'}}
    atomic_text(path, json.dumps(document, indent=2) + '\n', overwrite=force)
    return path.resolve()


def doctor(java: str = 'java', directory: Path = Path('.pluginmatrix'), network: bool = True) -> dict:
    from .artifacts import read_json
    checks = []
    def add(name, level, ok, detail):
        checks.append({'name': name, 'level': level, 'status': 'PASS' if ok else 'FAIL', 'detail': str(detail)})
    add('python', 'required', sys.version_info >= (3, 10), platform.python_version())
    add('platform', 'informational', True, platform.platform())
    try:
        executable, version = resolve_java(java)
        add('java', 'required', True, version)
        javac = resolve_javac(executable)
        compiler = run_external([javac, '-version'], capture_output=True, text=True, timeout=10) if javac else None
        compiler_output = ((compiler.stdout or '') + (compiler.stderr or '')).strip() if compiler else 'javac missing'
        add('jdk', 'required', bool(compiler and compiler.returncode == 0), compiler_output)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        add('java/jdk', 'required', False, exc)
    try:
        from .files import reject_links
        reject_links(directory)
        error = _check_writable_directory(directory, 'doctor.directory')
        add('directory', 'required', error is None, error or directory.resolve())
        free = shutil.disk_usage(directory).free
        add('disk', 'warning', free >= 2 * 1024**3, f'{free} free bytes; allow at least 2 GiB per concurrent environment')
    except (OSError, ValueError) as exc:
        add('directory', 'required', False, exc)
    if network:
        for provider in inspect_providers():
            if provider['api']:
                from urllib.parse import urlsplit
                try:
                    read_json(provider['api'], {urlsplit(provider['api']).hostname})
                    add(provider['type'] + '_api', 'warning', True, 'reachable')
                except (OSError, ValueError) as exc:
                    add(provider['type'] + '_api', 'warning', False, exc)
    else:
        add('network', 'informational', True, 'not checked (--offline)')
    valid = all(c['status'] == 'PASS' for c in checks if c['level'] == 'required')
    return {'schema': 1, 'checks': checks, 'exit_code': 0 if valid else 2}


def minecraft_java_requirement(version: str) -> int | None:
    """Return Paper's documented Java baseline for a release version."""
    if not isinstance(version, str) or not re.fullmatch(r'\d+\.\d+(?:\.\d+)?', version):
        return None
    parts = tuple(int(part) for part in version.split('.'))
    if parts[0] >= 26:
        return 25
    if parts[0] != 1 or len(parts) < 2:
        return None
    minor = parts[1]
    patch = parts[2] if len(parts) > 2 else 0
    if minor >= 21 or minor == 20 and patch >= 5:
        return 21
    if minor >= 17:
        return 17
    if minor == 16 and patch >= 5:
        return 16
    if minor >= 12:
        return 11
    return 8


def inspect_provider_catalog(provider_type: str, version: str | None = None,
                             cache_dir: Path = Path('.pluginmatrix/cache'),
                             max_age: int = PROVIDER_CATALOG_TTL) -> dict:
    """Return normalized Provider versions/builds with bounded disk-cache fallback."""
    provider = get_provider(provider_type)
    if version is not None and not re.fullmatch(r'\d+\.\d+(?:\.\d+)?', version):
        raise ValueError('Minecraft version must use numbers such as 1.21.4')
    if provider_type == 'local':
        return {'schema': 1, 'provider': provider_type, 'provider_name': provider.metadata.name,
                'available': True, 'source': 'local', 'versions': [], 'builds': [],
                'recommended_build': None, 'recommended_java': None}
    key = f'{provider_type}-versions' if version is None else f'{provider_type}-{version}-builds'
    path = Path(cache_dir).expanduser().absolute() / 'metadata' / f'{key}.json'
    query = {'provider': provider_type, 'version': version}
    now = time.time()
    cached = None
    cache_warning = None
    try:
        try:
            cached = _read_provider_cache(path, query)
        except _ReplaceableProviderCacheError as exc:
            cache_warning = str(exc)
        if cached and now - cached['fetched_at'] <= max_age:
            return _catalog_response(provider, version, cached, 'cache')
        with file_lock(path.with_name(path.name + '.lock'), timeout=35):
            try:
                refreshed = _read_provider_cache(path, query)
            except _ReplaceableProviderCacheError as exc:
                cache_warning = str(exc)
                refreshed = None
            if refreshed and now - refreshed['fetched_at'] <= max_age:
                return _catalog_response(provider, version, refreshed, 'cache')
            data = provider.catalog_builds(version) if version is not None else {
                'versions': provider.catalog_versions()
            }
            record = {'schema': 1, 'query': query, 'fetched_at': time.time(), 'data': data}
            atomic_json(path, record)
            response = _catalog_response(provider, version, record, 'network')
            if cache_warning:
                response['warning'] = cache_warning[:1024]
            return response
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        if cached:
            response = _catalog_response(provider, version, cached, 'stale_cache')
            response['warning'] = str(exc)[:1024]
            return response
        return {'schema': 1, 'provider': provider_type, 'provider_name': provider.metadata.name,
                'available': False, 'source': 'unavailable', 'versions': [], 'builds': [],
                'recommended_build': None,
                'recommended_java': minecraft_java_requirement(version) if version else None,
                'error': str(exc)[:1024]}


def _read_provider_cache(path: Path, query: dict) -> dict | None:
    reject_links(path)
    if not path.exists():
        return None
    info = path.stat()
    if not path.is_file() or info.st_nlink != 1 or info.st_size > MAX_PROVIDER_CACHE_BYTES:
        raise ValueError('Provider metadata cache is not a bounded regular file')
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError, RecursionError) as exc:
        raise _ReplaceableProviderCacheError(f'Provider metadata cache is invalid: {exc}') from exc
    if (not isinstance(value, dict) or value.get('schema') != 1 or value.get('query') != query
            or type(value.get('fetched_at')) not in (int, float) or not isinstance(value.get('data'), dict)):
        raise _ReplaceableProviderCacheError('Provider metadata cache does not match the requested catalog')
    return value


def _catalog_response(provider, version: str | None, record: dict, source: str) -> dict:
    data = record['data']
    return {'schema': 1, 'provider': provider.metadata.type, 'provider_name': provider.metadata.name,
            'available': True, 'source': source, 'fetched_at': record['fetched_at'],
            'versions': data.get('versions', []), 'builds': data.get('builds', []),
            'recommended_build': data.get('recommended_build'),
            'recommended_java': minecraft_java_requirement(version) if version else None}


def discover_java_runtimes() -> dict:
    """Discover a bounded set of installed Java runtimes without installing or modifying them."""
    candidates: list[tuple[Path, str]] = []
    executable_name = 'java.exe' if os.name == 'nt' else 'java'
    for variable in ('JAVA_HOME', 'JDK_HOME'):
        if os.environ.get(variable):
            candidates.append((Path(os.environ[variable]) / 'bin' / executable_name, variable))
    for directory in os.environ.get('PATH', '').split(os.pathsep):
        directory = directory.strip().strip('"')
        if directory:
            candidates.append((Path(directory) / executable_name, 'PATH'))
    patterns: list[tuple[Path, str, str]] = []
    if os.name == 'nt':
        for root_name in ('ProgramFiles', 'ProgramFiles(x86)', 'LOCALAPPDATA'):
            root = os.environ.get(root_name)
            if not root:
                continue
            base = Path(root)
            patterns.extend((base, pattern, 'installed JDK') for pattern in (
                'Java/*/bin/java.exe', 'Eclipse Adoptium/*/bin/java.exe', 'Microsoft/jdk-*/bin/java.exe',
                'Amazon Corretto/*/bin/java.exe', 'BellSoft/LibericaJDK-*/bin/java.exe',
                'Azul Systems/Zulu*/bin/java.exe', 'Programs/Eclipse Adoptium/*/bin/java.exe'))
    elif sys.platform == 'darwin':
        patterns.extend((Path(root), pattern, 'installed JDK') for root, pattern in (
            ('/Library/Java/JavaVirtualMachines', '*/Contents/Home/bin/java'),
            ('/opt/homebrew/opt', 'openjdk*/bin/java'), ('/usr/local/opt', 'openjdk*/bin/java')))
    else:
        patterns.extend((Path(root), pattern, 'installed JDK') for root, pattern in (
            ('/usr/lib/jvm', '*/bin/java'), ('/usr/java', '*/bin/java')))
    for root, pattern, source in patterns:
        if root.is_dir():
            candidates.extend((path, source) for path in root.glob(pattern))
    runtimes = []
    seen = set()
    deadline = time.monotonic() + 20
    for candidate, source in candidates[:128]:
        if time.monotonic() >= deadline:
            break
        try:
            if not candidate.is_file():
                continue
            resolved = candidate.resolve()
            identity = os.path.normcase(str(resolved))
            if identity in seen:
                continue
            seen.add(identity)
            executable, version = resolve_java(str(resolved))
            major = _java_major(version)
            javac = resolve_javac(executable)
            compiler_ok = False
            compiler_path = None
            if javac:
                compiler = run_external([javac, '-version'], capture_output=True, text=True, timeout=10)
                compiler_output = ((getattr(compiler, 'stdout', '') or '')
                                   + (getattr(compiler, 'stderr', '') or '')).strip()
                compiler_ok = compiler.returncode == 0 and _java_major(compiler_output) == major
                if compiler_ok:
                    compiler_path = str(Path(javac).resolve()) if Path(javac).exists() else javac
            runtimes.append({'path': str(resolved), 'version': version, 'major': major,
                             'jdk': compiler_ok, 'javac': compiler_path, 'source': source})
        except (OSError, ValueError, subprocess.SubprocessError):
            continue
    runtimes.sort(key=lambda item: (not item['jdk'], -(item['major'] or 0), item['path'].casefold()))
    recommended = next((item['path'] for item in runtimes if item['jdk']), None)
    return {'schema': 1, 'runtimes': runtimes, 'recommended': recommended}


def _java_major(version: str) -> int | None:
    match = re.search(r'(?<![\d.])(?:1\.)?(\d+)(?:\.\d+)*', version)
    return int(match.group(1)) if match else None
