"""Static report rendering. Stored JSON verdicts are never recomputed."""
from __future__ import annotations

import html
import json
import os
from pathlib import Path
from urllib.parse import quote

from .files import atomic_text, protect_inputs, reject_links
from .providers import PASS_SCOPE, FOLIA_SCOPE
from .locking import report_locks


def _object(value, label: str) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f'invalid report {label}')
    return value


def _array(value, label: str) -> list:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f'invalid report {label}')
    return value


def load_report(path: Path) -> dict:
    with Path(path).open('rb') as stream:
        data = stream.read(32 * 1024 * 1024 + 1)
    if len(data) > 32 * 1024 * 1024:
        raise ValueError('report exceeds the 32 MiB reader limit')
    try:
        value = json.loads(data)
    except (ValueError, RecursionError) as exc:
        raise ValueError(f'invalid JSON report: {exc}') from exc
    if not isinstance(value, dict) or not ('environments' in value or 'result' in value):
        raise ValueError('expected a PluginMatrix runtime or Matrix JSON report')
    return value


def _environments(report: dict) -> list[dict]:
    if 'environments' in report:
        if not isinstance(report['environments'], list) or not all(isinstance(e, dict) for e in report['environments']):
            raise ValueError('invalid report environments')
        return report['environments']
    metadata = _object(report.get('metadata'), 'metadata')
    return [{'id': metadata.get('server_type', 'paper'),
             'verdict': report.get('result'), 'failure_stage': report.get('failure_stage'),
             'reason': report.get('reason'), 'metadata': metadata,
             'evidence': report.get('evidence', []),
             'artifacts': {'runtime_report': report.get('report_path'), 'server_log': report.get('log_path'), 'run_dir': report.get('workdir')}}]


def _e(value) -> str:
    return html.escape(str(value if value is not None else ''), quote=True)


def _json(value) -> str:
    return _e(json.dumps(value, indent=2, ensure_ascii=True))


def _report_path(value: str, source: Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else source.parent / path


def report_inputs(report: dict, source: Path) -> list[Path]:
    inputs = [source]
    plugin = _object(report.get('plugin'), 'plugin')
    config = _object(report.get('config'), 'config')
    options = _object(config.get('options'), 'config options')
    top_artifacts = _object(report.get('artifacts'), 'artifacts')
    for value in (report.get('config_source'), plugin.get('plugin_jar'), config.get('plugin')):
        if isinstance(value, str):
            inputs.append(_report_path(value, source))
    for env in _environments(report):
        metadata = _object(env.get('metadata'), 'environment metadata')
        server = _object(metadata.get('server'), 'environment server')
        artifacts = _object(env.get('artifacts'), 'environment artifacts')
        protected = _array(metadata.get('protected_inputs'), 'protected inputs')
        dependencies = _array(metadata.get('dependencies'), 'environment dependencies')
        values = [*protected, metadata.get('plugin_jar'), metadata.get('paper_jar'), server.get('jar')]
        values += list(artifacts.values())
        values += [_object(dependency, 'environment dependency').get('plugin_jar') for dependency in dependencies]
        inputs.extend(_report_path(v, source) for v in values if isinstance(v, str))
    inputs.extend(_report_path(p, source) for p in _array(config.get('dependencies'), 'config dependencies') if isinstance(p, str))
    for environment in _array(config.get('environments'), 'config environments'):
        environment = _object(environment, 'config environment')
        server = _object(environment.get('server'), 'config environment server')
        if isinstance(server.get('jar'), str):
            inputs.append(_report_path(server['jar'], source))
    # A copied/renamed report still references the authoritative original JSON.
    inputs.extend(_report_path(v, source) for v in top_artifacts.values() if isinstance(v, str))
    report_path = options.get('report')
    if isinstance(report_path, str):
        inputs.append(_report_path(report_path, source))
    return inputs


def html_document(report: dict, source: Path, destination: Path) -> str:
    environments = _environments(report)
    rows, sections = [], []
    for index, env in enumerate(environments):
        metadata = _object(env.get('metadata'), 'environment metadata')
        resolved = _object(env.get('resolved'), 'environment resolved data')
        server = _object(metadata.get('server') or resolved.get('server'), 'environment server')
        rows.append(f'<tr><td><a href="#env-{index}">{_e(env.get("id"))}</a></td>'
                    f'<td>{_e(server.get("server_type", "paper"))}</td><td>{_e(env.get("verdict"))}</td>'
                    f'<td>{_e(env.get("failure_stage"))}</td><td>{_e(env.get("reason"))}</td></tr>')
        artifacts = []
        for label, value in _object(env.get('artifacts'), 'environment artifacts').items():
            if not isinstance(value, str):
                continue
            try:
                path = _report_path(value, source)
                relative = Path(os.path.relpath(path, destination.parent)).as_posix()
                # Percent-encoding plus ./ prevents URI schemes and injected attributes.
                link = './' + quote(relative, safe='/')
                rendered = f'<a href="{_e(link)}">{_e(relative)}</a>' if path.suffix.lower() in ('.json', '.log', '.txt') else _e(relative)
            except (OSError, ValueError):
                rendered = _e(value)
            artifacts.append(f'<li>{_e(label)}: {rendered}</li>')
        limit = FOLIA_SCOPE if server.get('regionized_runtime') else PASS_SCOPE
        sections.append(f'<section id="env-{index}"><h2>{_e(env.get("id"))}</h2><p>{_e(limit)}</p>'
                        f'<ul>{"".join(artifacts)}</ul><details><summary>Metadata</summary><pre>{_json(metadata or env.get("resolved", {}))}</pre></details>'
                        f'<details><summary>Evidence</summary><pre>{_json(env.get("evidence", []))}</pre></details></section>')
    plugin = _object(report.get('plugin') or report.get('metadata'), 'plugin')
    return ('<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">'
            '<title>PluginMatrix report</title><style>body{font:16px system-ui;margin:2rem auto;max-width:1200px;padding:0 1rem;color:#172434;background:#f5f7fa}'
            'table{border-collapse:collapse;width:100%;background:white}td,th{border:1px solid #cbd5e1;padding:.6rem;text-align:left;overflow-wrap:anywhere}'
            'section{background:white;margin:1.5rem 0;padding:1rem}pre{white-space:pre-wrap;overflow-wrap:anywhere}a{color:#125ba2}summary{cursor:pointer}</style>'
            f'<h1>PluginMatrix report</h1><p>{_e(plugin.get("plugin_name") or plugin.get("plugin_jar"))} {_e(plugin.get("plugin_version"))}</p>'
            f'<p>{_e(PASS_SCOPE)}</p><p>JSON is the authoritative report. Raw server logs are linked, not embedded.</p>'
            f'<p>Stored summary: {_e(json.dumps(report.get("summary", {})))}</p>'
            '<table><thead><tr><th>Environment</th><th>Provider</th><th>Verdict</th><th>Failure stage</th><th>Reason</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table>{"".join(sections)}</html>')


def render_html_report(source: Path, destination: Path) -> Path:
    with report_locks([destination], [source]):
        return _render_html_report(source, destination)


def _render_html_report(source: Path, destination: Path) -> Path:
    """Render while the caller owns the destination's report lock."""
    source, destination = Path(source).resolve(), Path(destination).absolute()
    report = load_report(source)
    reject_links(destination)
    protect_inputs(destination, report_inputs(report, source))
    config = _object(report.get('config'), 'config')
    options = _object(config.get('options'), 'config options')
    artifacts = _object(report.get('artifacts'), 'artifacts')
    roots = [options.get(k) for k in ('work_dir', 'cache_dir')]
    roots.append(artifacts.get('runtime_root'))
    for env in _environments(report):
        roots.append(_object(env.get('metadata'), 'environment metadata').get('cache_dir'))
        roots.append(_object(env.get('artifacts'), 'environment artifacts').get('run_dir'))
    for root in roots:
        if isinstance(root, str) and root:
            resolved_root = _report_path(root, source).resolve()
            resolved_output = destination.resolve()
            if (resolved_output == resolved_root or resolved_root in resolved_output.parents
                    or resolved_output in resolved_root.parents):
                raise ValueError('HTML report must be outside runtime/cache roots')
        elif root is not None:
            raise ValueError('invalid report runtime/cache root')
    content = html_document(report, source, destination)
    atomic_text(destination, content)
    return destination.resolve()
