from __future__ import annotations

import re
import struct
import zipfile
import zlib
import textwrap
from pathlib import Path
from typing import Any

from .model import Check
from .files import sha256_file


class PreflightError(Exception):
    def __init__(self, checks: list[Check], message: str, state: str = "PLUGIN_LOAD_FAILED"):
        super().__init__(message)
        self.checks = checks
        self.state = state


def _yaml_value(text: str, key: str) -> str | None:
    match = re.search(rf"(?m)^{re.escape(key)}[ \t]*:[ \t]*(.*?)[ \t]*$", textwrap.dedent(text))
    if not match:
        return None
    value = match.group(1).strip()
    if value.startswith('#'):
        return None
    # Quoted scalars may contain '#'; only an unquoted, whitespace-separated '#' starts a comment.
    if value.startswith("'"):
        scalar = re.match(r"'((?:[^']|'')*)'(?:\s*(?:#.*)?)$", value)
        if scalar:
            return scalar.group(1).replace("''", "'")
        raise ValueError(f'unsupported quoted scalar for {key}')
    elif value.startswith('"'):
        import json
        scalar = re.match(r'"((?:[^"\\]|\\.)*)"(?:\s*(?:#.*)?)$', value)
        if scalar:
            try:
                return json.loads('"' + scalar.group(1) + '"')
            except ValueError:
                pass
        raise ValueError(f'unsupported quoted scalar for {key}')
    else:
        value = re.split(r'\s+#', value, maxsplit=1)[0].strip()
    if value and value[0] in '&*!|>{}':
        raise ValueError(f'unsupported YAML scalar for {key}; use a plain or quoted single-line value')
    return value or None


def _yaml_list(text: str, key: str) -> list[str]:
    text = textwrap.dedent(text)
    value = _yaml_value(text, key)
    if not value:
        match = re.search(rf"(?m)^{re.escape(key)}[ \t]*:[ \t]*(?:#.*)?$", text)
        if not match:
            return []
        items = []
        for line in text[match.end():].splitlines():
            if not line.strip() or line.lstrip().startswith('#'):
                continue
            item = re.fullmatch(r'[ \t]*-[ \t]+(.+)', line)
            if item:
                items.append(_yaml_value('item: ' + item.group(1), 'item'))
            elif not line[0].isspace():
                break
            else:
                raise ValueError(f'unsupported YAML list for {key}')
    else:
        if not (value.startswith('[') and value.endswith(']')):
            raise ValueError(f'unsupported YAML list for {key}; use a block or bracketed list')
        items = [_yaml_value('item: ' + item.strip(), 'item') for item in value[1:-1].split(',') if item.strip()]
    if any(not item or not re.fullmatch(r'[A-Za-z0-9_.-]+', item) for item in items):
        raise ValueError(f'unsupported YAML list for {key}; use simple plugin names')
    return items


def _class_name_from_entry(entry: str) -> str:
    return entry.replace("/", ".").removesuffix(".class")


def _class_major_version(jar: zipfile.ZipFile, class_name: str) -> int | None:
    entry = class_name.replace(".", "/") + ".class"
    try:
        with jar.open(entry) as stream:
            data = stream.read(8)
    except KeyError:
        return None
    if len(data) < 8 or data[:4] != b"\xca\xfe\xba\xbe":
        return None
    return struct.unpack(">H", data[6:8])[0]


def java_target_name(major: int | None) -> str | None:
    if major is None:
        return None
    return str(major - 44) if major >= 49 else f"Java {major}"


def inspect_plugin(plugin_path: Path) -> tuple[dict[str, Any], list[Check]]:
    try:
        if not plugin_path.is_file():
            raise ValueError('plugin JAR must be a regular file')
        if plugin_path.stat().st_size > 512 * 1024 * 1024:
            raise ValueError('compressed JAR exceeds 512 MiB')
        with zipfile.ZipFile(plugin_path) as jar:
            entries = jar.infolist()
            if len(entries) > 100000 or sum(item.file_size for item in entries) > 512 * 1024 * 1024:
                raise ValueError('JAR exceeds preflight limits (100000 entries / 512 MiB uncompressed)')
            if len({item.filename for item in entries}) != len(entries):
                raise ValueError('JAR contains duplicate entries')
            if any(item.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED) or item.flag_bits & 1 for item in entries):
                raise ValueError('JAR uses unsupported compression or encryption')
            if any(item.filename in ('plugin.yml', 'paper-plugin.yml') and item.file_size > 1024 * 1024 for item in entries):
                raise ValueError('plugin.yml exceeds 1 MiB')
            bad = jar.testzip()
            if bad:
                raise zipfile.BadZipFile(f'corrupt entry: {bad}')
            return _inspect_plugin(plugin_path, jar)
    except (OSError, zipfile.BadZipFile, RuntimeError, NotImplementedError, ValueError, zlib.error, EOFError) as exc:
        raise PreflightError([Check('plugin JAR', 'FAIL', str(exc))],
                             f'invalid plugin JAR: {exc}', 'ENVIRONMENT_INVALID') from exc


def _inspect_plugin(plugin_path: Path, jar: zipfile.ZipFile) -> tuple[dict[str, Any], list[Check]]:
    checks: list[Check] = []
    if not plugin_path.exists():
        raise PreflightError([Check("plugin JAR", "FAIL", "file does not exist")], "plugin JAR does not exist", "ENVIRONMENT_INVALID")
    if not plugin_path.is_file():
        raise PreflightError([Check("plugin JAR", "FAIL", "path is not a file")], "plugin path is not a file", "ENVIRONMENT_INVALID")

    metadata: dict[str, Any] = {
        "plugin_jar": str(plugin_path.resolve()),
        "plugin_jar_sha256": sha256_file(plugin_path),
        "plugin_jar_size": plugin_path.stat().st_size,
    }
    checks.append(Check("plugin JAR", "PASS"))
    descriptors = [name for name in ('plugin.yml', 'paper-plugin.yml') if name in jar.namelist()]
    if len(descriptors) > 1:
        raise PreflightError(checks, 'dual descriptors are ambiguous; supply exactly one plugin.yml or paper-plugin.yml')
    descriptor = descriptors[0] if descriptors else 'plugin.yml'
    metadata['plugin_descriptor'] = descriptor
    try:
        plugin_yml = jar.read(descriptor).decode("utf-8")
    except KeyError as exc:
        jar.close()
        raise PreflightError(checks + [Check("plugin.yml", "FAIL", "missing")], "plugin.yml is missing") from exc
    except UnicodeDecodeError as exc:
        jar.close()
        raise PreflightError(checks + [Check("plugin.yml", "FAIL", "not UTF-8")], "plugin.yml is not valid UTF-8") from exc
    plugin_yml = textwrap.dedent(plugin_yml.lstrip('\ufeff'))
    critical = {'name', 'version', 'main', 'api-version', 'depend', 'softdepend', 'loadbefore', 'provides', 'folia-supported', 'dependencies', 'bootstrapper', 'loader'}
    seen = set()
    for line in plugin_yml.splitlines():
        if not line or line[0].isspace() or line.startswith('#'):
            continue
        if line.startswith(('---', '...', '<<:', '%')):
            raise PreflightError(checks, 'unsupported YAML document/merge syntax; use a simple plugin.yml')
        key = line.split(':', 1)[0].strip().strip("'\"")
        if key in critical:
            if key in seen or not re.match(re.escape(key) + r'[ \t]*:', line):
                raise PreflightError(checks, f'duplicate or unsupported quoted metadata key: {key}')
            seen.add(key)
    if descriptor == 'paper-plugin.yml' and seen & {'dependencies', 'bootstrapper', 'loader'}:
        raise PreflightError(checks, 'paper-plugin.yml bootstrapper/loader/nested dependencies are unsupported; use a simple descriptor and explicit local dependencies')
    checks.append(Check("plugin.yml", "PASS"))

    name = _yaml_value(plugin_yml, "name")
    main = _yaml_value(plugin_yml, "main")
    version = _yaml_value(plugin_yml, "version")
    api_version = _yaml_value(plugin_yml, "api-version")
    depend = _yaml_list(plugin_yml, "depend")
    softdepend = _yaml_list(plugin_yml, "softdepend")
    loadbefore = _yaml_list(plugin_yml, "loadbefore")
    provides = _yaml_list(plugin_yml, 'provides')
    folia = _yaml_value(plugin_yml, 'folia-supported')
    declaration = re.search(r'(?m)^folia-supported\s*:\s*(.*?)\s*$', plugin_yml)
    if declaration and not re.fullmatch(r'(?:true|false)(?:\s+#.*)?', declaration.group(1)):
        raise PreflightError(checks, 'folia-supported must be an unquoted YAML boolean true or false')
    metadata.update({
        "plugin_name": name,
        "plugin_version": version,
        "plugin_main": main,
        "api_version": api_version,
        "depend": depend,
        "softdepend": softdepend,
        "loadbefore": loadbefore,
        "provides": provides,
        "folia_supported": folia == 'true',
    })
    if api_version and not re.fullmatch(r"\d+\.\d+(?:\.\d+)?", api_version):
        jar.close()
        raise PreflightError(
            checks + [Check("api-version", "FAIL", f"invalid value: {api_version}")],
            "plugin.yml has an invalid api-version",
        )
    checks.append(Check("api-version", "PASS", api_version or "not declared"))
    if not name or not main or not version:
        jar.close()
        raise PreflightError(checks + [Check("plugin metadata", "FAIL", "name, version and main are required")], "plugin.yml lacks name, version or main")
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', name) or not re.fullmatch(r'[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*', main, re.ASCII):
        raise PreflightError(checks, 'invalid plugin name or main class')
    if any(ord(character) < 32 for character in version) or len(version) > 256:
        raise PreflightError(checks, 'unsupported plugin version scalar')
    if any(not re.fullmatch(r'[A-Za-z0-9_.-]+', alias) for alias in provides):
        raise PreflightError(checks, 'unsupported provides list; use simple plugin names')
    checks.append(Check("plugin metadata", "PASS", f"{name} {version or ''}".strip()))

    main_entry = main.replace(".", "/") + ".class"
    names = set(jar.namelist())
    if main_entry not in names:
        jar.close()
        raise PreflightError(checks + [Check("main class", "FAIL", f"{main_entry} missing")], "main class is missing")
    checks.append(Check("main class", "PASS", main))
    major = _class_major_version(jar, main)
    if major is None:
        jar.close()
        raise PreflightError(
            checks + [Check("Java bytecode", "FAIL", "main class is not a readable JVM class")],
            "main class bytecode is invalid",
        )
    metadata["main_class_major"] = major
    metadata["main_class_java_target"] = java_target_name(major)
    checks.append(Check("Java bytecode", "PASS", f"major {major} ({java_target_name(major)})" if major else "unreadable"))
    checks.append(Check("dependencies", "PASS", f"depend={depend or 'none'}, softdepend={softdepend or 'none'}"))
    jar.close()
    return metadata, checks
