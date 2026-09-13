"""Small shared helpers for evidence files and input preservation."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import tempfile
from pathlib import Path
from typing import Any, Iterable


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def protect_inputs(output: Path, inputs: Iterable[Path]) -> None:
    reject_links(output)
    output = output.resolve()
    for source in inputs:
        source = source.resolve()
        if output == source or output in source.parents or (output.exists() and source.exists() and output.samefile(source)):
            raise ValueError(f"report path '{output}' conflicts with input '{source}'; choose a separate JSON file")


def atomic_json(path: Path, payload: Any) -> None:
    reject_links(path)
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix='.pluginmatrix-', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(payload, stream, indent=2, ensure_ascii=True)
            stream.write('\n')
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def reject_links(path: Path) -> None:
    """Reject symlinks and Windows junction/reparse aliases before resolving paths."""
    path = path.absolute()
    for part in (*reversed(path.parents), path):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError(f'symbolic links/reparse points are not allowed in output paths: {part}')


def validate_output_paths(work: Path, cache: Path, inputs: Iterable[Path], report: Path | None = None) -> None:
    for path in (work, cache):
        reject_links(path)
    work, cache = work.resolve(), cache.resolve()
    if work == cache or work in cache.parents or cache in work.parents:
        raise ValueError("fields 'options.work_dir' and 'options.cache_dir' require separate run and download-cache directories without overlap. Fix: choose distinct paths.")
    inputs = list(inputs)
    for source in inputs:
        source = source.resolve()
        if any(source == root or root in source.parents or source in root.parents for root in (work, cache)):
            raise ValueError(f'input {source} conflicts with work_dir/cache_dir')
    if report is not None:
        protect_inputs(report, inputs)
        resolved = report.resolve()
        if any(resolved == root or root in resolved.parents or resolved in root.parents for root in (work, cache)):
            raise ValueError('report must be outside work_dir/cache_dir, not inside or an ancestor of either')


def atomic_copy(source: Path, destination: Path) -> str:
    source, destination = Path(source), Path(destination)
    reject_links(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as stream:
            temporary = Path(stream.name)
            with source.open('rb') as original:
                shutil.copyfileobj(original, stream, 1024 * 1024)
        digest = sha256_file(temporary)
        os.replace(temporary, destination)
        return digest
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
