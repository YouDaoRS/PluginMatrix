from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile


PROBE_PLUGIN_NAME = "PluginMatrixRuntimeProbe"
PROBE_MAIN_CLASS = "pluginmatrix.probe.RuntimeProbe"
PROBE_FILE_NAME = "pluginmatrix-runtime-evidence.json"


def _java_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\r", "\\r").replace("\n", "\\n")


def build_probe_plugin(
    paper_jar: Path,
    plugins_dir: Path,
    target_plugin_name: str,
    evidence_path: Path,
    java_executable: str,
    java_major: int,
) -> Path:
    """Compile a tiny read-only Bukkit plugin against the exact Paper artifact."""
    javac = _resolve_javac(java_executable)
    if not javac:
        raise RuntimeError("a JDK javac executable is required to build the runtime probe")

    target = _java_string(target_plugin_name)
    output_name = "pluginmatrix-runtime-probe.jar"
    with tempfile.TemporaryDirectory(prefix="pluginmatrix-probe-") as temp:
        root = Path(temp)
        source = root / "RuntimeProbe.java"
        classes = root / "classes"
        classes.mkdir()
        classpath = _extract_paper_libraries(paper_jar, root / "libraries")
        source.write_text(
            f'''package pluginmatrix.probe;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import org.bukkit.plugin.Plugin;
import org.bukkit.plugin.java.JavaPlugin;

public final class RuntimeProbe extends JavaPlugin {{
    private static final String TARGET = "{target}";
    private static final String OUTPUT = "{_java_string(evidence_path.name)}";

    @Override
    public void onEnable() {{
        getServer().getScheduler().runTaskTimer(this, this::writeEvidence, 1L, 1L);
    }}

    private void writeEvidence() {{
        Plugin plugin = getServer().getPluginManager().getPlugin(TARGET);
        String name = plugin == null ? "" : plugin.getDescription().getName();
        String version = plugin == null ? "" : plugin.getDescription().getVersion();
        boolean enabled = plugin != null && plugin.isEnabled();
        String json = "{{" +
            "\\"probe\\":\\"pluginmatrix\\"," +
            "\\"target_present\\":" + (plugin != null) + "," +
            "\\"target_name\\":\\"" + escape(name) + "\\"," +
            "\\"target_version\\":\\"" + escape(version) + "\\"," +
            "\\"target_enabled\\":" + enabled +
            "}}";
        try {{
            Path destination = getDataFolder().getParentFile().toPath().resolve(OUTPUT);
            Path temporary = destination.resolveSibling(OUTPUT + ".tmp");
            Files.write(temporary, json.getBytes("UTF-8"));
            try {{
                Files.move(temporary, destination, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
            }} catch (java.nio.file.AtomicMoveNotSupportedException ignored) {{
                Files.move(temporary, destination, StandardCopyOption.REPLACE_EXISTING);
            }} catch (java.nio.file.AccessDeniedException transientLock) {{
                // The host may be reading the previous snapshot on Windows; retry on the next tick.
                Files.deleteIfExists(temporary);
                return;
            }}
        }} catch (Exception exception) {{
            getLogger().severe("Unable to write runtime evidence: " + exception);
        }}
    }}

    private static String escape(String value) {{
        return value.replace("\\\\", "\\\\\\\\").replace("\\"", "\\\\\\"");
    }}
}}
''',
            encoding="utf-8",
        )
        completed = subprocess.run(
            [javac, "--release", str(java_major), "-cp", classpath, "-d", str(classes), str(source)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "javac failed").strip()
            raise RuntimeError(f"could not compile runtime probe: {detail}")

        jar_path = plugins_dir / output_name
        plugin_yml = (
            f"name: {PROBE_PLUGIN_NAME}\n"
            f"version: 0.1.0\n"
            f"main: {PROBE_MAIN_CLASS}\n"
            "api-version: '1.13'\n"
        )
        with ZipFile(jar_path, "w", ZIP_DEFLATED) as archive:
            archive.writestr("plugin.yml", plugin_yml)
            for class_file in classes.rglob("*.class"):
                archive.write(class_file, class_file.relative_to(classes).as_posix())
        return jar_path


def _resolve_javac(java_executable: str) -> str | None:
    java_path = Path(java_executable)
    sibling = java_path.with_name("javac" + java_path.suffix) if java_path.exists() else None
    if sibling and sibling.is_file():
        return str(sibling)
    return shutil.which("javac")


def _extract_paper_libraries(paper_jar: Path, destination: Path) -> str:
    try:
        with ZipFile(paper_jar) as archive:
            candidates = [
                name
                for name in archive.namelist()
                if name.startswith("META-INF/libraries/")
                and name.endswith(".jar")
            ]
            if not candidates:
                raise RuntimeError("Paper artifact does not embed libraries for runtime probe compilation")
            extracted: list[Path] = []
            for name in candidates:
                jar_path = destination / Path(name).relative_to("META-INF/libraries")
                jar_path.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(name) as source, jar_path.open("wb") as output:
                    shutil.copyfileobj(source, output)
                extracted.append(jar_path)
            return os.pathsep.join(str(path) for path in extracted)
    except (OSError, BadZipFile) as exc:
        raise RuntimeError(f"could not extract Paper libraries for runtime probe: {exc}") from exc


def read_probe_evidence(path: Path) -> dict[str, object] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if payload.get("probe") != "pluginmatrix":
        return None
    return payload
