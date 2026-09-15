"""Bounded, ID-based management of official server download entries.

Only exact JAR/receipt pairs are removable. Runtime bootstrap trees, unrecognized
files and persistent lock files are never recursively deleted.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path

from .artifacts import MAX_ARTIFACT, safe_name
from .files import read_evidence_bytes, reject_links
from .locking import file_lock
from .providers import get_provider, parse_server


def _id(relative):
    return hashlib.sha256(relative.encode()).hexdigest()


def _regular(path):
    reject_links(path)
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError("cache entry must be a regular file without links")
    return info


def _identity(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _entry(root, path):
    relative = path.relative_to(root).as_posix()
    parts = Path(relative).parts
    if len(parts) == 1 and re.fullmatch(r"paper-[0-9.]+-[0-9]+\.jar", path.name):
        provider = "paper"
    elif (len(parts) == 4 and parts[0] in {"paper", "purpur", "folia"}
          and re.fullmatch(r"\d+\.\d+(?:\.\d+)?", parts[1]) and parts[2].isdigit()):
        provider = parts[0]
    else:
        raise ValueError("unrecognized server cache layout")
    safe_name(path.name)
    info = _regular(path)
    if info.st_size > MAX_ARTIFACT:
        raise ValueError("cache JAR exceeds 512 MiB")
    receipt = path.with_name(path.name + ".sha256.json")
    _regular(receipt)
    record = json.loads(read_evidence_bytes(receipt, 4096))
    if not isinstance(record, dict) or not re.fullmatch("[a-f0-9]{64}", record.get("sha256", "")):
        raise ValueError("invalid local SHA-256 receipt")
    return {"id": _id(relative), "provider": provider, "path": str(path), "name": path.name,
            "size": info.st_size, "sha256": record["sha256"], "integrity": "not_checked",
            "source": "local receipt; official checksum is revalidated on download/use"}


def inspect(root: Path):
    root = Path(root).expanduser().absolute()
    reject_links(root)
    entries, warnings = [], []
    visited = 0
    if root.exists():
        # Do not descend into runtime bootstrap caches or arbitrary link trees.
        for directory, dirs, files in os.walk(root, followlinks=False):
            current = Path(directory)
            reject_links(current)
            depth = len(current.relative_to(root).parts)
            dirs[:] = [d for d in dirs if (depth > 0 or d in {"paper", "purpur", "folia"})
                       and depth < 3 and not (current / d).is_symlink()
                       and not getattr((current / d).lstat(), "st_file_attributes", 0) & 0x400]
            visited += len(files) + len(dirs)
            if visited > 4096:
                warnings.append("Cache listing stopped at 4096 entries.")
                break
            for name in files:
                if not name.endswith(".jar"):
                    continue
                try:
                    entries.append(_entry(root, current / name))
                except (OSError, ValueError, TypeError) as exc:
                    warnings.append(f"{name}: {exc}")
    return {"schema": 1, "directory": str(root), "entries": entries, "warnings": warnings,
            "scope": "Official server JARs only; runtime bootstrap trees and lock files are retained."}


def manage(ident: str, root: Path, *, delete=False):
    if not isinstance(ident, str) or not re.fullmatch("[a-f0-9]{64}", ident):
        raise ValueError("invalid server cache id")
    root = Path(root).expanduser().absolute()
    found = next((entry for entry in inspect(root)["entries"] if entry["id"] == ident), None)
    if found is None:
        raise ValueError("server cache entry is absent or unrecognized")
    path = Path(found["path"])
    with file_lock(path.with_name(path.name + ".lock"), timeout=0):
        entry = _entry(root, path)
        receipt = path.with_name(path.name + ".sha256.json")
        before, receipt_before = _regular(path), _regular(receipt)
        if delete:
            # Check the resolved absolute target before unlinking; never recursive.
            if not path.resolve().is_relative_to(root.resolve()) or path.resolve() == root.resolve():
                raise ValueError("cache path escapes its root")
            if _identity(_regular(path)) != _identity(before) or _identity(_regular(receipt)) != _identity(receipt_before):
                raise ValueError("cache changed during deletion")
            path.unlink()
            receipt.unlink()
            return {"id": ident, "deleted": True}
        digest = hashlib.sha256()
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
                     | getattr(os, "O_NONBLOCK", 0))
        with os.fdopen(fd, "rb") as stream:
            if _identity(os.fstat(stream.fileno())) != _identity(before):
                raise ValueError("cache changed during verification")
            total = 0
            while chunk := stream.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_ARTIFACT:
                    raise ValueError("cache size limit exceeded")
                digest.update(chunk)
        if (_identity(_regular(path)) != _identity(before) or _identity(_regular(receipt)) != _identity(receipt_before)
                or digest.hexdigest() != entry["sha256"]):
            raise ValueError("server cache integrity mismatch; remove explicitly and download again")
        return {**entry, "integrity": "verified"}


def download(server, root: Path, control=None):
    spec = parse_server(server)
    if spec.type not in {"paper", "purpur", "folia"} or spec.build is None:
        raise ValueError("cache download requires an official Provider and explicit reviewed build")
    path, metadata = get_provider(spec.type).prepare(spec, Path(root), control)
    return {"schema": 1, "path": str(path), "metadata": metadata, "integrity": "verified"}
