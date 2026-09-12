from __future__ import annotations

import hashlib
import re
import struct
import zipfile
from pathlib import Path
from typing import Any

from .model import Check


class PreflightError(Exception):
    def __init__(self, checks: list[Check], message: str, state: str = "PLUGIN_LOAD_FAILED"):
        super().__init__(message)
        self.checks = checks
        self.state = state


def _yaml_value(text: str, key: str) -> str | None:
    match = re.search(rf"(?m)^[ \t]*{re.escape(key)}[ \t]*:[ \t]*(.*?)[ \t]*$", text)
    if not match:
        return None
    value = match.group(1).strip().strip("'\"")
    return value or None


def _yaml_list(text: str, key: str) -> list[str]:
    value = _yaml_value(text, key)
    if not value:
        # Handle the common block-list form:
        #   depend:
        #     - Vault
        match = re.search(
            rf"(?ms)^\s*{re.escape(key)}\s*:\s*$\n(?P<body>(?:\s*-\s*.+\s*(?:\n|$))+)",
            text,
        )
        if not match:
            return []
        return [
            item.strip().lstrip("-").strip().split(" #", 1)[0].strip().strip("'\"")
            for item in match.group("body").splitlines()
            if item.strip().startswith("-")
        ]
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    return [item.strip().split(" #", 1)[0].strip().strip("'\"") for item in value.split(",") if item.strip()]


def _class_name_from_entry(entry: str) -> str:
    return entry.replace("/", ".").removesuffix(".class")


def _class_major_version(jar: zipfile.ZipFile, class_name: str) -> int | None:
    entry = class_name.replace(".", "/") + ".class"
    try:
        data = jar.read(entry)
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
    checks: list[Check] = []
    if not plugin_path.exists():
        raise PreflightError([Check("plugin JAR", "FAIL", "file does not exist")], "plugin JAR does not exist", "ENVIRONMENT_INVALID")
    if not plugin_path.is_file():
        raise PreflightError([Check("plugin JAR", "FAIL", "path is not a file")], "plugin path is not a file", "ENVIRONMENT_INVALID")

    metadata: dict[str, Any] = {
        "plugin_jar": str(plugin_path.resolve()),
        "plugin_jar_sha256": hashlib.sha256(plugin_path.read_bytes()).hexdigest(),
        "plugin_jar_size": plugin_path.stat().st_size,
    }
    try:
        jar = zipfile.ZipFile(plugin_path)
        bad = jar.testzip()
        if bad:
            raise zipfile.BadZipFile(f"corrupt entry: {bad}")
    except (zipfile.BadZipFile, OSError) as exc:
        raise PreflightError([Check("plugin JAR", "FAIL", str(exc))], "invalid plugin JAR", "ENVIRONMENT_INVALID") from exc

    checks.append(Check("plugin JAR", "PASS"))
    try:
        plugin_yml = jar.read("plugin.yml").decode("utf-8")
    except KeyError as exc:
        jar.close()
        raise PreflightError(checks + [Check("plugin.yml", "FAIL", "missing")], "plugin.yml is missing") from exc
    except UnicodeDecodeError as exc:
        jar.close()
        raise PreflightError(checks + [Check("plugin.yml", "FAIL", "not UTF-8")], "plugin.yml is not valid UTF-8") from exc
    checks.append(Check("plugin.yml", "PASS"))

    name = _yaml_value(plugin_yml, "name")
    main = _yaml_value(plugin_yml, "main")
    version = _yaml_value(plugin_yml, "version")
    api_version = _yaml_value(plugin_yml, "api-version")
    depend = _yaml_list(plugin_yml, "depend")
    softdepend = _yaml_list(plugin_yml, "softdepend")
    loadbefore = _yaml_list(plugin_yml, "loadbefore")
    metadata.update({
        "plugin_name": name,
        "plugin_version": version,
        "plugin_main": main,
        "api_version": api_version,
        "depend": depend,
        "softdepend": softdepend,
        "loadbefore": loadbefore,
    })
    if api_version and not re.fullmatch(r"\d+\.\d+", api_version):
        jar.close()
        raise PreflightError(
            checks + [Check("api-version", "FAIL", f"invalid value: {api_version}")],
            "plugin.yml has an invalid api-version",
        )
    checks.append(Check("api-version", "PASS", api_version or "not declared"))
    if not name or not main:
        jar.close()
        raise PreflightError(checks + [Check("plugin metadata", "FAIL", "name and main are required")], "plugin.yml lacks name or main")
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
