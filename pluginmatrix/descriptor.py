"""Read-only, bounded descriptor hints. This is deliberately not a YAML engine.

Only unambiguous block mappings and simple scalar/list fields become suggestions.
Unsupported syntax produces incomplete analysis, never executable instructions.
Runtime identity parsing remains in preflight.
"""
from __future__ import annotations

import re

MAX_DECLARATIONS = 256
NAME = re.compile(r"[A-Za-z0-9_.-]{1,128}")
PERMISSION = re.compile(r"[A-Za-z0-9_.*-]{1,128}")


def _section(text: str, section: str) -> list[tuple[int, str]]:
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines)
              if re.match(r"^['\"]?" + re.escape(section) + r"""['"]?\s*:""", line)]
    if not starts:
        return []
    if len(starts) != 1 or not re.fullmatch(section + r'\s*:\s*(?:#.*)?', lines[starts[0]]):
        raise ValueError(f'{section}: use one unquoted block mapping')
    result = []
    for line in lines[starts[0] + 1:]:
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        if not line[0].isspace():
            break
        if '\t' in line or len(line) > 4096:
            raise ValueError(f'{section}: tabs or oversized lines are unsupported')
        result.append((len(line) - len(line.lstrip()), line.strip()))
    return result


def _declarations(text, section):
    lines = _section(text, section)
    if not lines:
        return []
    indent = lines[0][0]
    entries, seen = [], set()
    for depth, line in lines:
        if depth < indent:
            raise ValueError(f'{section}: ambiguous indentation')
        if depth == indent:
            match = re.fullmatch(r"""(['"]?)([A-Za-z0-9_.*-]{1,128})\1\s*:\s*(?:\{\}\s*)?(?:#.*)?""", line)
            if not match or match[2].casefold() in seen:
                raise ValueError(f'{section}: unsupported or duplicate declaration')
            seen.add(match[2].casefold())
            entries.append((match[2], []))
            if len(entries) > MAX_DECLARATIONS:
                raise ValueError(f'{section}: exceeds {MAX_DECLARATIONS} declarations')
        else:
            entries[-1][1].append((depth, line))
    return entries


def _nested_lines(body, field):
    for index, (depth, line) in enumerate(body):
        if re.match(re.escape(field) + r'\s*:', line):
            nested = []
            for nested_depth, nested_line in body[index + 1:]:
                if nested_depth <= depth:
                    break
                nested.append((nested_depth, nested_line))
            return nested
    return []


def inspect_declarations(text: str, descriptor: str) -> dict:
    from .preflight import _yaml_value
    result = {'commands': [], 'permissions': [], 'analysis_complete': True, 'analysis_warnings': []}
    for section in ('commands', 'permissions'):
        try:
            declarations = _declarations(text, section)
        except ValueError as exc:
            result['analysis_complete'] = False
            result['analysis_warnings'].append(str(exc))
            continue
        for name, body in declarations:
            entry = {'name': name, 'source': f'{descriptor}:{section}.{name}'}
            fields = {}
            if body:
                indent = body[0][0]
                for depth, line in body:
                    if depth != indent:
                        continue  # Nested children/list contents are not guessed.
                    key = line.split(':', 1)[0]
                    if key in fields or key == '<<' or not re.fullmatch('[a-z-]+', key):
                        result['analysis_complete'] = False
                        result['analysis_warnings'].append(f'{entry["source"]}: unsupported/duplicate field')
                        continue
                    fields[key] = line
            keys = ('description', 'usage', 'permission', 'aliases') if section == 'commands' else ('description', 'default')
            for key in keys:
                if key not in fields:
                    continue
                try:
                    value = _yaml_value(fields[key], key)
                    if key == 'aliases':
                        if value is None:
                            nested = _nested_lines(body, key)
                            if any(not re.match(r'-\s+\S', line) for _, line in nested):
                                raise ValueError('unsupported block aliases')
                            values = [line[1:].strip() for _, line in nested]
                        else:
                            values = value[1:-1].split(',') if value.startswith('[') and value.endswith(']') else [value]
                        aliases = [_yaml_value('alias: ' + v.strip(), 'alias') for v in values if v.strip()]
                        if len(aliases) > 64 or any(not isinstance(v, str) or not NAME.fullmatch(v) for v in aliases):
                            raise ValueError('unsupported aliases')
                        entry[key] = aliases
                    elif value is not None:
                        if len(value) > 1024 or any(ord(c) < 32 for c in value):
                            raise ValueError('oversized/control-character scalar')
                        if key == 'default' and value.lower() not in ('true', 'false', 'op', 'not op'):
                            raise ValueError('unknown permission default')
                        entry[key] = value
                except ValueError as exc:
                    result['analysis_complete'] = False
                    result['analysis_warnings'].append(f'{entry["source"]}.{key}: {exc}')
            if section == 'permissions' and 'children' in fields:
                children = {}
                nested = _nested_lines(body, 'children')
                try:
                    if _yaml_value(fields['children'], 'children') is not None:
                        raise ValueError('use a block mapping of child permissions to booleans')
                    for depth, line in nested:
                        match = re.fullmatch(r"([A-Za-z0-9_.*-]{1,128}):\s*(true|false)\s*(?:#.*)?", line)
                        if not match or depth != nested[0][0] or match[1] in children:
                            raise ValueError('nested/duplicate child permission definitions are unsupported')
                        if len(children) >= MAX_DECLARATIONS:
                            raise ValueError('too many child permission declarations')
                        children[match[1]] = match[2] == 'true'
                    entry['children'] = children
                except ValueError as exc:
                    result['analysis_complete'] = False
                    result['analysis_warnings'].append(f'{entry["source"]}.children: {exc}')
            if section == 'commands' and not NAME.fullmatch(name):
                result['analysis_complete'] = False
                result['analysis_warnings'].append(f'{entry["source"]}: unsupported command name')
                continue
            result[section].append(entry)
    if descriptor == 'paper-plugin.yml':
        # Paper plugins register commands programmatically; a commands key does
        # not establish Bukkit PluginCommand registration.
        if result['commands']:
            result['analysis_warnings'].append('paper-plugin.yml commands do not imply Bukkit command registration')
        result['commands'] = []
    result['external_libraries_declared'] = bool(re.search(r'(?m)^libraries\s*:', text))
    return result


def suggest_behavior(metadata: dict) -> dict:
    from .behavior import parse_behavior
    checks, evidence, omitted = [], [], []
    namespace = metadata['plugin_name'].lower()
    for section, kind in (('commands', 'command_registered'), ('permissions', 'permission_registered')):
        for entry in metadata.get(section, []):
            name = namespace + ':' + entry['name'].lower() if section == 'commands' else entry['name']
            # Do not lowercase permissions: the global permission registry's
            # semantics cannot be inferred from a differently cased declaration.
            check = {'id': f'suggested_{len(checks) + 1}', 'type': kind, 'name': name}
            try:
                parse_behavior({'schema': 1, 'checks': [check]})
                if len(checks) >= 64:
                    raise ValueError('Behavior limit of 64 checks')
            except ValueError as exc:
                omitted.append({'source': entry['source'], 'reason': str(exc)})
                continue
            checks.append(check)
            evidence.append({'id': check['id'], 'source': entry['source'],
                             'reason': 'Declared registration; no command invocation or permission evaluation.'})
    plan = parse_behavior({'schema': 1, 'timeout': 300, 'checks': checks}) if checks else None
    return {'schema': 1, 'behavior': plan.to_dict() if plan else None, 'evidence': evidence,
            'omitted': omitted, 'requires_review': True,
            'scope': 'Editable registration assertions only. Dynamic commands/services and gameplay are unknown.'}
