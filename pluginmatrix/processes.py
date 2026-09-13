"""Own the server process tree; stdout is a file, never a blocking pipe."""
from __future__ import annotations

import os
import signal
import subprocess
import time
import sys
from pathlib import Path


def _windows_job(process):
    import ctypes
    from ctypes import wintypes as w

    class Limits(ctypes.Structure):
        _fields_ = [('process_time', ctypes.c_int64), ('job_time', ctypes.c_int64),
                    ('flags', w.DWORD), ('min_ws', ctypes.c_size_t), ('max_ws', ctypes.c_size_t),
                    ('active', w.DWORD), ('affinity', ctypes.c_size_t), ('priority', w.DWORD),
                    ('scheduling', w.DWORD)]

    class Extended(ctypes.Structure):
        _fields_ = [('basic', Limits), ('io', ctypes.c_uint64 * 6),
                    ('process_memory', ctypes.c_size_t), ('job_memory', ctypes.c_size_t),
                    ('peak_process', ctypes.c_size_t), ('peak_job', ctypes.c_size_t)]

    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, w.LPCWSTR]
    kernel.CreateJobObjectW.restype = w.HANDLE
    kernel.SetInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
    kernel.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
    kernel.CloseHandle.argtypes = [w.HANDLE]
    kernel.CloseHandle.restype = w.BOOL
    kernel.TerminateJobObject.argtypes = [w.HANDLE, w.UINT]
    kernel.TerminateJobObject.restype = w.BOOL
    kernel.QueryInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD, ctypes.c_void_p]
    kernel.QueryInformationJobObject.restype = w.BOOL
    job = kernel.CreateJobObjectW(None, None)
    if not job:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        limits = Extended()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not kernel.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            raise ctypes.WinError(ctypes.get_last_error())
        if not kernel.AssignProcessToJobObject(job, int(process._handle)):
            raise ctypes.WinError(ctypes.get_last_error())
        nt = ctypes.WinDLL('ntdll')
        nt.NtResumeProcess.argtypes = [w.HANDLE]
        nt.NtResumeProcess.restype = ctypes.c_long
        if nt.NtResumeProcess(int(process._handle)) != 0:
            raise OSError('could not resume isolated server process')
    except BaseException:
        kernel.CloseHandle(job)
        raise
    process._pluginmatrix_job = (kernel, job)


def start_process(command, cwd, output):
    options = {'creationflags': 0x4} if os.name == 'nt' else {'start_new_session': True}
    process = subprocess.Popen(list(command), cwd=cwd, stdout=output, stderr=subprocess.STDOUT, **options)
    try:
        if os.name == 'nt':
            # Assign before running user code, so even short-lived parents cannot escape tracking.
            _windows_job(process)
        else:
            process._pluginmatrix_group = True
    except BaseException:
        process.kill()
        process.wait(timeout=5)
        raise
    return process


def stop_process(process):
    job = getattr(process, '_pluginmatrix_job', None)
    if job:
        import ctypes
        from ctypes import wintypes as w
        class Accounting(ctypes.Structure):
            _fields_ = [('times', ctypes.c_int64 * 4), ('faults', w.DWORD),
                        ('total', w.DWORD), ('active', w.DWORD), ('terminated', w.DWORD)]
        kernel, handle = job
        try:
            if not kernel.TerminateJobObject(handle, 1):
                raise ctypes.WinError(ctypes.get_last_error())
            deadline = time.monotonic() + 5
            while True:
                info = Accounting()
                if not kernel.QueryInformationJobObject(handle, 1, ctypes.byref(info), ctypes.sizeof(info), None):
                    raise ctypes.WinError(ctypes.get_last_error())
                if info.active == 0:
                    break
                if time.monotonic() >= deadline:
                    raise OSError('Windows job still has active processes after cleanup deadline')
                time.sleep(.02)
        finally:
            kernel.CloseHandle(handle)
            process._pluginmatrix_job = None
    elif os.name != 'nt' and getattr(process, '_pluginmatrix_group', False):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=5)
        deadline = time.monotonic() + 5
        while _group_has_live_processes(process.pid):
            if time.monotonic() >= deadline:
                raise OSError('POSIX process group still has live processes after cleanup deadline')
            time.sleep(.02)
    elif process.poll() is None:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                           capture_output=True, timeout=10)
        if process.poll() is None:
            process.kill()
    process.wait(timeout=5)


def _group_has_live_processes(group: int) -> bool:
    try:
        os.killpg(group, 0)
    except ProcessLookupError:
        return False
    if sys.platform.startswith('linux'):
        # Orphan zombies can await PID 1 reaping even though they cannot execute
        # or retain files/ports. Do not confuse them with running descendants.
        for entry in Path('/proc').iterdir():
            if not entry.name.isdigit():
                continue
            try:
                fields = (entry/'stat').read_text().rsplit(')', 1)[1].split()
            except (FileNotFoundError, ProcessLookupError):
                continue
            if int(fields[2]) == group and fields[0] not in ('Z', 'X'):
                return True
        return False
    return True
