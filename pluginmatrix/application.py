"""GUI-ready application API, version 1. No CLI argument parsing or terminal output."""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

from .control import ProgressEvent, RunControl
from .files import atomic_text, protect_inputs, validate_output_paths
from .matrix import (MatrixConfig, MatrixConfigError, load_matrix_config, validate_matrix_preconditions,
                     validate_matrix_paths, matrix_exit_code, run_matrix as _run_matrix, _check_writable_directory)
from .providers import ServerSpec, get_provider, inspect_providers, parse_server
from .reports import load_report, render_html_report, _render_html_report
from .locking import report_locks, validate_report_locks
from .runtime import verify as _verify, resolve_java, write_report
from .probe import resolve_javac

API_VERSION = 1


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
        compiler = subprocess.run([javac, '-version'], capture_output=True, text=True, timeout=10) if javac else None
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
