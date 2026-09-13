from __future__ import annotations

import json
import os
import re
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

from . import __version__
from .files import sha256_file, reject_links


PAPER_API = "https://fill.papermc.io/v3/projects/paper/versions/{version}/builds"
USER_AGENT = f"PluginMatrix/{__version__}"


class PaperDownloadError(Exception):
    pass


def resolve_paper(version: str, build_id: int | None = None) -> dict[str, Any]:
    request = urllib.request.Request(
        PAPER_API.format(version=version),
        headers={"User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            builds = json.load(response)
    except Exception as exc:
        raise PaperDownloadError(
            f"could not query Paper builds for requested version {version!r}: {exc}. "
            "Expected access to the official Paper API; check the version and network access, then retry."
        ) from exc
    stable = [build for build in builds if build.get("channel") == "STABLE"]
    candidates = stable or builds
    if not candidates:
        raise PaperDownloadError(
            f"no Paper builds were found for requested version {version!r}. "
            "Expected a Minecraft version published by Paper; correct the environment 'paper' value."
        )
    if build_id is not None:
        matches = [item for item in candidates if item.get("id") == build_id]
        if not matches:
            raise PaperDownloadError(
                f"requested paper_build {build_id} was not found for Paper {version}. "
                "Expected a build published for that exact version; correct paper_build or remove it to select "
                "the latest stable build."
            )
        build = matches[0]
    else:
        build = max(candidates, key=lambda item: item.get("id", 0))
    download = (build.get("downloads") or {}).get("server:default")
    if not download:
        raise PaperDownloadError(
            f"Paper {version} build {build.get('id')} has no default server download. "
            "Expected the official API to provide server:default; choose another published build or retry later."
        )
    return {
        "minecraft_version": version,
        "paper_build": build.get("id"),
        "paper_channel": build.get("channel"),
        "paper_time": build.get("time"),
        "paper_jar_name": download.get("name"),
        "paper_sha256": (download.get("checksums") or {}).get("sha256"),
        "paper_download_url": download.get("url"),
    }


def ensure_paper(version: str, cache_dir: Path, build_id: int | None = None) -> tuple[Path, dict[str, Any]]:
    metadata = resolve_paper(version, build_id)
    name = metadata.get('paper_jar_name')
    expected = metadata.get('paper_sha256')
    if (not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+\.jar', name)
            or re.match(r'(?i)^(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)', name)):
        raise PaperDownloadError('official API returned an unsafe Paper JAR filename')
    if not isinstance(expected, str) or not re.fullmatch(r'[A-Fa-f0-9]{64}', expected):
        raise PaperDownloadError('official API did not provide a valid Paper SHA-256')
    try:
        reject_links(cache_dir / name)
    except ValueError as exc:
        raise PaperDownloadError(str(exc)) from exc
    cache_dir.mkdir(parents=True, exist_ok=True)
    jar_path = cache_dir / metadata["paper_jar_name"]
    if jar_path.is_symlink():
        raise PaperDownloadError(
            f"Paper cache path '{jar_path}' is a symbolic link. "
            "Expected a regular cached Paper JAR; remove the link and retry."
        )
    if jar_path.exists() and not jar_path.is_file():
        raise PaperDownloadError(
            f"Paper cache path '{jar_path}' is not a regular file. "
            "Expected a cached Paper JAR; remove the conflicting path and retry."
        )
    if not jar_path.exists():
        request = urllib.request.Request(metadata["paper_download_url"], headers={"User-Agent": USER_AGENT})
        temporary = None
        try:
            with urllib.request.urlopen(request, timeout=120) as response, tempfile.NamedTemporaryFile(dir=cache_dir, delete=False) as output:
                temporary = Path(output.name)
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
            if sha256_file(temporary).lower() != expected.lower():
                raise PaperDownloadError('downloaded Paper checksum mismatch')
            reject_links(jar_path)
            os.replace(temporary, jar_path)
        except Exception as exc:
            raise PaperDownloadError(
                f"could not download Paper {version} build {metadata.get('paper_build')} to '{jar_path}': {exc}. "
                "Expected a writable cache and network access to the official download URL; check both and retry."
            ) from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    actual = sha256_file(jar_path)
    if expected and actual.lower() != expected.lower():
        raise PaperDownloadError(
            f"Paper {version} build {metadata.get('paper_build')} checksum mismatch for '{jar_path}': "
            f"expected {expected}, got {actual}. The existing file was preserved; choose a clean cache or remove it explicitly."
        )
    metadata["paper_jar_sha256"] = actual
    metadata["paper_jar"] = str(jar_path.resolve())
    return jar_path, metadata
