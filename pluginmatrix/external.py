"""Launch system tools safely from normal and PyInstaller-frozen processes."""
from __future__ import annotations

import contextlib
import os
import subprocess
import sys
import threading


_WINDOWS_DLL_LOCK = threading.RLock()


def external_environment() -> dict[str, str]:
    """Return an environment suitable for Java, javac, browsers, and other system tools."""
    environment = dict(os.environ)
    if not getattr(sys, "frozen", False):
        return environment
    key = "LIBPATH" if sys.platform.startswith("aix") else "LD_LIBRARY_PATH"
    if os.name != "nt" and sys.platform != "darwin":
        original = environment.get(key + "_ORIG")
        if original is None:
            environment.pop(key, None)
        else:
            environment[key] = original
    return environment


@contextlib.contextmanager
def _windows_system_dlls():
    """Temporarily undo PyInstaller's DLL directory while a child is created."""
    if os.name != "nt" or not getattr(sys, "frozen", False):
        yield
        return
    import ctypes

    bundle = getattr(sys, "_MEIPASS", None)
    with _WINDOWS_DLL_LOCK:
        if not ctypes.windll.kernel32.SetDllDirectoryW(None):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            yield
        finally:
            # Never turn a successfully created child into an unowned process by
            # raising after Popen returned. A failed restore leaves the safer
            # system lookup behavior in place for later external tools.
            if bundle:
                ctypes.windll.kernel32.SetDllDirectoryW(str(bundle))


def run_external(command, **kwargs):
    kwargs.setdefault("env", external_environment())
    with _windows_system_dlls():
        return subprocess.run(command, **kwargs)


def popen_external(command, **kwargs):
    kwargs.setdefault("env", external_environment())
    with _windows_system_dlls():
        return subprocess.Popen(command, **kwargs)
