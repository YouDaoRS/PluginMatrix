"""Local plugin identities and dependency graph shared by analysis and runtime."""
from __future__ import annotations

from pathlib import Path


def validate_identities(items: list[tuple[Path, dict]]) -> None:
    from .probe import PROBE_PLUGIN_NAME, PROBE_FILE_NAME
    names = {PROBE_PLUGIN_NAME.casefold()}
    files = {'pluginmatrix-runtime-probe.jar', PROBE_FILE_NAME.casefold(), (PROBE_FILE_NAME + '.tmp').casefold()}
    for path, info in items:
        name = str(info.get('plugin_name') or '').casefold()
        if not path.name.lower().endswith('.jar') or any(c in path.name for c in ':\\') or path.name.endswith((' ', '.')):
            raise ValueError(f'unsupported plugin JAR filename: {path.name}')
        if path.name.casefold() in files or name in names:
            raise ValueError(f'plugin filename or identity conflicts with another plugin or runtime probe: {path}')
        files.add(path.name.casefold())
        names.add(name)
    for _, info in items:
        for alias in info.get('provides', []):
            if alias.casefold() in names:
                raise ValueError(f'plugin provides identity conflicts with another plugin or runtime probe: {alias}')
            names.add(alias.casefold())


def dependency_report(items: list[tuple[Path, dict]]) -> dict:
    errors, warnings, edges = [], [], []
    try:
        validate_identities(items)
    except ValueError as exc:
        errors.append({'code': 'IDENTITY_CONFLICT', 'reason': str(exc)})
        return {'schema': 1, 'ready': False, 'errors': errors, 'warnings': [], 'edges': []}
    owners = {}
    folded = {}
    for _, item in items:
        for name in [item['plugin_name'], *item.get('provides', [])]:
            owners[name] = item['plugin_name']
            folded[name.casefold()] = name
    graph = {item['plugin_name']: set() for _, item in items}
    for _, item in items:
        source = item['plugin_name']
        for field, required in (('depend', True), ('softdepend', False), ('loadbefore', False)):
            for name in item.get(field, []):
                owner = owners.get(name)
                edge = {'plugin': source, 'name': name, 'kind': field, 'required': required,
                        'resolved_plugin': owner, 'source': item['plugin_descriptor'] + ':' + field}
                edges.append(edge)
                if owner is None:
                    spelling = folded.get(name.casefold())
                    issue = {'code': 'DEPENDENCY_CASE_MISMATCH' if spelling else
                                     'MISSING_DEPENDENCY' if required else 'OPTIONAL_DEPENDENCY_ABSENT',
                             'plugin': source, 'name': name,
                             'reason': (f'{source} declares {field}: {name}, but supplied spelling is {spelling}; '
                                        'resolve the descriptor identity explicitly.' if spelling else
                                        f'{source} declares {field}: {name}; supply its local JAR if needed.')}
                    (errors if required else warnings).append(issue)
                elif required:
                    graph[source].add(owner)
    # Kahn's algorithm also catches self-dependencies through provides aliases.
    remaining = {key: set(value) for key, value in graph.items()}
    while remaining:
        ready = {key for key, value in remaining.items() if not value}
        if not ready:
            errors.append({'code': 'DEPENDENCY_CYCLE', 'plugins': sorted(remaining),
                           'reason': 'Required dependencies contain a cycle; no reliable load order.'})
            break
        remaining = {key: value - ready for key, value in remaining.items() if key not in ready}
    return {'schema': 1, 'ready': not errors, 'errors': errors, 'warnings': warnings, 'edges': edges}
