"""Build and audit one platform-native PyInstaller onedir archive."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import queue
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import urllib.request
import zipfile
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

from pluginmatrix.files import atomic_text, reject_links


ROOT = Path(__file__).resolve().parents[1]


def identity() -> tuple[str, str]:
    system = {"Windows": "windows", "Linux": "linux", "Darwin": "macos"}.get(platform.system())
    machine = {"amd64": "x86_64", "x86_64": "x86_64", "aarch64": "arm64", "arm64": "arm64"}.get(
        platform.machine().lower()
    )
    if not system or not machine:
        raise SystemExit(f"unsupported standalone build target: {platform.system()} {platform.machine()}")
    return system, machine


def clean_directory(path: Path, parent: Path) -> None:
    reject_links(parent)
    reject_links(path)
    resolved, boundary = path.resolve(), parent.resolve()
    if resolved == boundary or boundary not in resolved.parents:
        raise RuntimeError(f"refusing to clean path outside {boundary}: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True)


def version() -> str:
    completed = subprocess.run(
        [sys.executable, "-c", "from pluginmatrix import __version__; print(__version__)"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def git_commit() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def git_dirty() -> bool | None:
    try:
        return bool(subprocess.run(
            ["git", "status", "--porcelain"], cwd=ROOT, check=True, capture_output=True, text=True
        ).stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        return None


def windows_version_file(destination: Path, value: str) -> Path:
    numeric = value.split(".")[:3]
    numeric = [int("".join(character for character in item if character.isdigit()) or "0") for item in numeric]
    numeric += [0] * (4 - len(numeric))
    dotted = ".".join(str(item) for item in numeric)
    content = f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={tuple(numeric)}, prodvers={tuple(numeric)}, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[StringFileInfo([StringTable('040904B0', [
    StringStruct('CompanyName', 'PluginMatrix contributors'),
    StringStruct('FileDescription', 'PluginMatrix local runtime verifier'),
    StringStruct('FileVersion', '{dotted}'),
    StringStruct('InternalName', 'pluginmatrix'),
    StringStruct('LegalCopyright', 'Apache-2.0'),
    StringStruct('OriginalFilename', 'pluginmatrix.exe'),
    StringStruct('ProductName', 'PluginMatrix'),
    StringStruct('ProductVersion', '{value}')
  ])]), VarFileInfo([VarStruct('Translation', [1033, 1200])])]
)"""
    destination.write_text(content, encoding="utf-8")
    return destination


def archive_bundle(bundle: Path, output: Path, system: str) -> None:
    audit_bundle(bundle)
    if system == "windows":
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(bundle.rglob("*")):
                if path.is_file():
                    archive.write(path, (Path(bundle.name) / path.relative_to(bundle)).as_posix())
    else:
        with tarfile.open(output, "w:gz", format=tarfile.PAX_FORMAT) as archive:
            archive.add(bundle, arcname=bundle.name, recursive=True)


def audit_bundle(bundle: Path) -> None:
    """Reject runtime/private files before creating any distributable archive."""
    root = bundle.resolve(strict=True)
    forbidden_parts = {".git", ".pluginmatrix", "cache", "logs", "runs", "__pycache__", ".ssh", ".aws"}
    forbidden_suffixes = {".jar", ".log", ".jsonl", ".pem", ".key", ".p12", ".pfx", ".jks"}
    for path in bundle.rglob("*"):
        relative = path.relative_to(bundle)
        parts = {part.lower() for part in relative.parts}
        name = path.name.lower()
        if (parts & forbidden_parts or path.suffix.lower() in forbidden_suffixes
                or name == ".env" or name.startswith(".env.") or name in {"credentials", "id_rsa", "id_ed25519"}):
            raise RuntimeError(f"standalone bundle contains forbidden runtime/private asset: {relative}")
        # Native PyInstaller POSIX bundles need internal library symlinks.
        resolved = path.resolve(strict=True)
        if root not in resolved.parents or (not path.is_file() and not path.is_dir()):
            raise RuntimeError(f"standalone bundle contains an escaping link or special file: {relative}")


def python_license(candidates: Sequence[Path] | None = None) -> Path:
    version_directory = f"python{sys.version_info.major}.{sys.version_info.minor}"
    if candidates is None:
        candidates = [
            Path(sys.base_prefix) / "LICENSE.txt",
            Path(sys.base_prefix) / "LICENSE",
            Path(sys.base_prefix) / "share" / "doc" / version_directory / "copyright",
            Path(sys.executable).resolve().parent / "LICENSE.txt",
            Path(sys.executable).resolve().parent.parent / "LICENSE.txt",
        ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    fallback = ROOT / "standalone" / "licenses" / "CPYTHON-LICENSE.txt"
    if not fallback.is_file():
        raise RuntimeError("neither the build Python installation nor the source tree exposes a Python license")
    return fallback


def smoke(bundle: Path, value: str, java: str | None) -> None:
    executable = bundle / ("pluginmatrix.exe" if os.name == "nt" else "pluginmatrix")
    completed = subprocess.run([executable, "--version"], check=True, capture_output=True, text=True, timeout=30)
    if completed.stdout.strip() != f"pluginmatrix {value}":
        raise RuntimeError(f"frozen version mismatch: {completed.stdout!r}")
    providers = subprocess.run(
        [executable, "providers", "--json"], check=True, capture_output=True, text=True, timeout=30
    )
    metadata = json.loads(providers.stdout)
    if [item["type"] for item in metadata["providers"]] != ["paper", "purpur", "folia", "local"]:
        raise RuntimeError("frozen Provider registry is incomplete")
    if java:
        doctor = subprocess.run(
            [executable, "doctor", "--offline", "--java", java, "--directory", str(bundle.parent / "doctor")],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if doctor.returncode != 0:
            raise RuntimeError(f"frozen Java/Javac check failed:\n{doctor.stdout}\n{doctor.stderr}")
    if os.name == "nt":
        smoke_windows_double_click(executable, bundle, value)
    import socket

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    state = bundle.parent / "web-smoke"
    process = subprocess.Popen(
        [executable, "web", "--no-browser", "--port", str(port), "--state-dir", str(state / "state"),
         "--cache-dir", str(state / "cache")],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.monotonic() + 15
        while True:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as response:
                    health = json.load(response)
                break
            except OSError:
                if process.poll() is not None or time.monotonic() >= deadline:
                    stdout, stderr = process.communicate(timeout=2)
                    raise RuntimeError(f"frozen Web UI did not start:\n{stdout}\n{stderr}")
                time.sleep(0.1)
        if health != {"status": "ok", "version": value}:
            raise RuntimeError(f"unexpected frozen Web UI health: {health!r}")
    finally:
        if process.poll() is None:
            process.terminate()
        process.communicate(timeout=10)


def smoke_windows_double_click(executable: Path, bundle: Path, value: str) -> None:
    """Exercise the exact no-argument Windows entry without opening a browser."""
    with tempfile.TemporaryDirectory(prefix="double-click-", dir=bundle.parent) as temporary:
        environment = dict(os.environ, LOCALAPPDATA=temporary, PLUGINMATRIX_NO_BROWSER="1")
        process = subprocess.Popen(
            [executable], cwd=bundle, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        lines = queue.Queue()
        reader = threading.Thread(target=lambda: lines.put(process.stdout.readline()), daemon=True)
        reader.start()
        try:
            try:
                line = lines.get(timeout=15).strip()
            except queue.Empty as exc:
                raise RuntimeError("frozen no-argument Web UI did not print its local URL") from exc
            match = re.fullmatch(r"PluginMatrix Web UI: (http://127\.0\.0\.1:[1-9][0-9]*/)", line)
            if not match:
                raise RuntimeError(f"unexpected frozen no-argument startup output: {line!r}")
            with urllib.request.urlopen(match.group(1) + "health", timeout=5) as response:
                health = json.load(response)
            if health != {"status": "ok", "version": value}:
                raise RuntimeError(f"frozen no-argument Web UI is unhealthy: {health!r}")
        finally:
            if process.poll() is None:
                process.terminate()
            process.communicate(timeout=10)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--java", help="also verify frozen access to this installed JDK")
    args = parser.parse_args(argv)
    system, architecture = identity()
    value = version()
    stem = f"pluginmatrix-{value}-{system}-{architecture}"
    build_parent = ROOT / "build" / "standalone"
    output_parent = ROOT / "dist" / "standalone"
    work = build_parent / f"{system}-{architecture}"
    stage = work / "dist"
    clean_directory(work, build_parent)
    output_parent.mkdir(parents=True, exist_ok=True)
    version_file = windows_version_file(work / "version.txt", value) if system == "windows" else None
    environment = dict(os.environ)
    environment["PLUGINMATRIX_VERSION_FILE"] = str(version_file) if version_file else ""
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", "--distpath", str(stage),
         "--workpath", str(work / "work"), str(ROOT / "standalone" / "pluginmatrix.spec")],
        cwd=ROOT,
        env=environment,
        check=True,
    )
    source = stage / "pluginmatrix"
    bundle = output_parent / stem
    if bundle.exists():
        clean_directory(bundle, output_parent)
        bundle.rmdir()
    source.replace(bundle)
    for name in ("LICENSE", "README.md", "THIRD_PARTY_NOTICES.md"):
        shutil.copy2(ROOT / name, bundle / name)
    python_license_path = python_license()
    shutil.copy2(python_license_path, bundle / "PYTHON-LICENSE.txt")
    shutil.copy2(
        ROOT / "standalone" / "licenses" / "NATIVE-LICENSES.txt",
        bundle / "NATIVE-LICENSES.txt",
    )
    try:
        import PyInstaller
        pyinstaller_version = PyInstaller.__version__
    except (ImportError, AttributeError):
        pyinstaller_version = "unknown"
    build_info = {
        "schema": 1,
        "name": "pluginmatrix",
        "version": value,
        "platform": system,
        "architecture": architecture,
        "python": platform.python_version(),
        "python_license_source": (
            "vendored-cpython-license"
            if python_license_path.parent == ROOT / "standalone" / "licenses"
            else "build-interpreter"
        ),
        "license_files": [
            "LICENSE",
            "THIRD_PARTY_NOTICES.md",
            "PYTHON-LICENSE.txt",
            "NATIVE-LICENSES.txt",
        ],
        "pyinstaller": pyinstaller_version,
        "commit": git_commit(),
        "source_dirty": git_dirty(),
        "built_at": datetime.fromtimestamp(int(os.environ.get("SOURCE_DATE_EPOCH", time.time())), timezone.utc).isoformat(),
        "bundled": {"java": False, "servers": False, "third_party_plugins": False},
    }
    (bundle / "BUILD-INFO.json").write_text(json.dumps(build_info, indent=2) + "\n", encoding="utf-8")
    smoke(bundle, value, args.java)
    extension = ".zip" if system == "windows" else ".tar.gz"
    archive = output_parent / f"{stem}{extension}"
    archive.unlink(missing_ok=True)
    archive_bundle(bundle, archive, system)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum = output_parent / f"{stem}.sha256"
    atomic_text(checksum, f"{digest}  {archive.name}\n")
    print(json.dumps({"bundle": str(bundle), "archive": str(archive), "sha256": digest}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
