"""Static application analysis; never loads classes, executes plugins or downloads dependencies."""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from .dependencies import dependency_report
from .descriptor import suggest_behavior
from .preflight import PreflightError, inspect_plugin

LIMITATIONS = [
    'Static metadata is untrusted and does not prove compatibility or safety.',
    'The verifier is not a sandbox; plugins run with the current OS account.',
    'api-version is a minimum API declaration, not a supported Minecraft version range.',
    'Bytecode observations do not identify reflection, dynamic classes or all runtime requirements.',
    'Folia declaration does not prove thread or cross-region safety.',
    'Only explicitly supplied local dependency JARs are considered; none are downloaded.',
]


def analyze_plugin(plugin: Path, dependencies=()) -> dict:
    dependencies = tuple(Path(p) for p in dependencies)
    if len(dependencies) > 128:
        raise ValueError('at most 128 local dependencies are supported')
    items, errors, checks = [], [], []
    for path in (Path(plugin), *dependencies):
        try:
            metadata, observed = inspect_plugin(path)
            items.append((path, metadata))
            checks.append({'path': str(path.resolve()), 'checks': [asdict(c) for c in observed]})
        except PreflightError as exc:
            errors.append({'code': 'STATIC_ANALYSIS_FAILED', 'path': str(path.absolute()),
                           'reason': str(exc), 'preflight_state': exc.state,
                           'checks': [asdict(c) for c in exc.checks]})
    target = next((metadata for path, metadata in items if path == Path(plugin)), None)
    graph = dependency_report(items) if items else {'schema': 1, 'ready': False, 'errors': [], 'warnings': [], 'edges': []}
    return {'schema': 1, 'valid': not errors and graph['ready'], 'plugin': target,
            'dependencies': [m for p, m in items if p != Path(plugin)],
            'dependency_report': graph, 'errors': errors, 'checks': checks,
            'suggestions': suggest_behavior(target) if target else None, 'limitations': list(LIMITATIONS)}
