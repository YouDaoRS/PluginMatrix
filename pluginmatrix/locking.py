"""OS locks shared by threads and independent PluginMatrix processes.

Lock files are persistent: unlinking a live lock permits another inode to bypass it.
The OS releases ownership after crashes. Acquisitions are cancellable and bounded.
"""
from __future__ import annotations

import os
import time
from contextlib import contextmanager
from pathlib import Path

from .files import reject_links


@contextmanager
def file_lock(path: Path, control=None, timeout: float = 180):
    reject_links(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Do not write to an existing file: it could be a hardlink to an input.
    try:
        with path.open('xb') as created:
            created.write(b'0')
    except FileExistsError:
        pass
    if not path.is_file() or path.stat().st_nlink != 1:
        raise ValueError(f'unsafe lock file: {path}')
    with path.open('r+b') as stream:
        acquired = False
        deadline = time.monotonic() + timeout
        try:
            while not acquired:
                if control:
                    control.check()
                try:
                    if os.name == 'nt':
                        import msvcrt
                        stream.seek(0)
                        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    acquired = True
                except OSError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError(f'lock busy: {path}')
                    time.sleep(.05)
            yield
        finally:
            if acquired:
                if os.name == 'nt':
                    stream.seek(0)
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream, fcntl.LOCK_UN)
