# -*- coding: utf-8 -*-
"""v3867 (card #41, REG-2986 never built) - WHICH LANE IS EATING THE CPU. Per named thread, measured, no dependency.

MEASURED 2026-11-06 on his work ALT (8 GB, the game streaming beside the console): /api/status took 19-47 s and the heart
timed out at 40 s, and nothing on any surface could say which of the console's ~40 threads was busy - the process total
was all there was. Every lane is a named thread (threading.Thread(name=...)), so the question is answerable: ask the OS
for each thread's CPU time, match it to Python's thread by its native id, and diff two samples.

  darwin  task_threads + thread_info (THREAD_IDENTIFIER_INFO's thread_id == threading.get_native_id(); measured on his
          Mac: a named busy thread read 1.00 s after 1 s of work). Every port and the thread list are DEALLOCATED - a
          console that samples every minute must not leak a port per thread per sample.
  win32   OpenThread(THREAD_QUERY_LIMITED_INFORMATION) + GetThreadTimes (100 ns units), handle closed.
  linux   /proc/self/task/<tid>/stat, utime + stime over CLK_TCK.

Anything that cannot be read is UNKNOWN - None with a reason - never a zero (a zero is a measurement: "this lane did not
run"). Pure where it can be: window() takes two samples and the thread names. [[unknown-stays-unknown]] [[heart-first]]
"""
import collections
import ctypes
import ctypes.util
import os
import sys
import threading
import time

#: how far back the published window reaches, and how often a status call may take a new sample
WINDOW_S = 60.0
SAMPLE_EVERY_S = 5.0
TOP = 8

_LOCK = threading.Lock()
_SAMPLES = collections.deque(maxlen=64)      # (monotonic seconds, {native_id: cpu seconds})
_MACH = {}


def _darwin_sample():
    """-> {native_id: cpu seconds} | None"""
    if not _MACH:
        libc = ctypes.CDLL(ctypes.util.find_library("c"))
        libc.mach_task_self.restype = ctypes.c_uint
        libc.task_threads.argtypes = [ctypes.c_uint, ctypes.POINTER(ctypes.POINTER(ctypes.c_uint)),
                                      ctypes.POINTER(ctypes.c_uint)]
        libc.thread_info.argtypes = [ctypes.c_uint, ctypes.c_int, ctypes.POINTER(ctypes.c_int),
                                     ctypes.POINTER(ctypes.c_uint)]
        libc.mach_port_deallocate.argtypes = [ctypes.c_uint, ctypes.c_uint]
        libc.vm_deallocate.argtypes = [ctypes.c_uint, ctypes.c_size_t, ctypes.c_size_t]

        class TV(ctypes.Structure):
            _fields_ = [("seconds", ctypes.c_int), ("microseconds", ctypes.c_int)]

        class TBI(ctypes.Structure):
            _fields_ = [("user_time", TV), ("system_time", TV), ("cpu_usage", ctypes.c_int), ("policy", ctypes.c_int),
                        ("run_state", ctypes.c_int), ("flags", ctypes.c_int), ("suspend_count", ctypes.c_int),
                        ("sleep_time", ctypes.c_int)]

        class TII(ctypes.Structure):
            _fields_ = [("thread_id", ctypes.c_uint64), ("thread_handle", ctypes.c_uint64),
                        ("dispatch_qaddr", ctypes.c_uint64)]
        _MACH.update(libc=libc, TBI=TBI, TII=TII)
    libc, TBI, TII = _MACH["libc"], _MACH["TBI"], _MACH["TII"]
    task = libc.mach_task_self()
    lst = ctypes.POINTER(ctypes.c_uint)()
    n = ctypes.c_uint()
    if libc.task_threads(task, ctypes.byref(lst), ctypes.byref(n)) != 0:
        return None
    out = {}
    try:
        for i in range(n.value):
            port = lst[i]
            try:
                ii, c1 = TII(), ctypes.c_uint(ctypes.sizeof(TII) // 4)
                bi, c2 = TBI(), ctypes.c_uint(ctypes.sizeof(TBI) // 4)
                if libc.thread_info(port, 4, ctypes.cast(ctypes.byref(ii), ctypes.POINTER(ctypes.c_int)),
                                    ctypes.byref(c1)) != 0:
                    continue
                if libc.thread_info(port, 3, ctypes.cast(ctypes.byref(bi), ctypes.POINTER(ctypes.c_int)),
                                    ctypes.byref(c2)) != 0:
                    continue
                out[int(ii.thread_id)] = (bi.user_time.seconds + bi.user_time.microseconds / 1e6
                                          + bi.system_time.seconds + bi.system_time.microseconds / 1e6)
            finally:
                libc.mach_port_deallocate(task, port)
    finally:
        libc.vm_deallocate(task, ctypes.cast(lst, ctypes.c_void_p).value or 0,
                           n.value * ctypes.sizeof(ctypes.c_uint))
    return out


def _win32_sample(ids):
    """-> {native_id: cpu seconds} | None, for the native ids asked"""
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)

    class FT(ctypes.Structure):
        _fields_ = [("lo", ctypes.c_uint32), ("hi", ctypes.c_uint32)]
    k32.OpenThread.restype = ctypes.c_void_p
    k32.OpenThread.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    k32.GetThreadTimes.argtypes = [ctypes.c_void_p] + [ctypes.POINTER(FT)] * 4
    k32.CloseHandle.argtypes = [ctypes.c_void_p]
    out = {}
    for tid in ids:
        h = k32.OpenThread(0x0800, 0, int(tid))          # THREAD_QUERY_LIMITED_INFORMATION
        if not h:
            continue
        try:
            c, e, kt, ut = FT(), FT(), FT(), FT()
            if k32.GetThreadTimes(h, ctypes.byref(c), ctypes.byref(e), ctypes.byref(kt), ctypes.byref(ut)):
                out[int(tid)] = (((kt.hi << 32) | kt.lo) + ((ut.hi << 32) | ut.lo)) / 1e7
        finally:
            k32.CloseHandle(h)
    return out


def _linux_sample(ids):
    """-> {native_id: cpu seconds} | None"""
    tick = os.sysconf("SC_CLK_TCK")
    out = {}
    for tid in ids:
        try:
            with open("/proc/self/task/%d/stat" % int(tid)) as fh:
                rest = fh.read().rsplit(")", 1)[1].split()
            out[int(tid)] = (int(rest[11]) + int(rest[12])) / float(tick)    # fields 14, 15 (utime, stime)
        except (OSError, ValueError, IndexError):
            continue
    return out


def sample(platform=None, threads=None):
    """One reading. -> ({native_id: cpu seconds} | None, why | None). Never raises."""
    plat = sys.platform if platform is None else platform
    ids = [t.native_id for t in (threads if threads is not None else threading.enumerate())
           if getattr(t, "native_id", None)]
    try:
        if plat == "darwin":
            got = _darwin_sample()
        elif plat.startswith("win"):
            got = _win32_sample(ids)
        elif plat.startswith("linux"):
            got = _linux_sample(ids)
        else:
            return None, "per-thread CPU is not read on %s" % plat
    except Exception as e:
        return None, "per-thread CPU could not be read (%s)" % type(e).__name__
    if got is None:
        return None, "the OS would not list this process's threads"
    return got, None


def window(old, new, dt, names):
    """CPU per named lane between two samples. -> rows [{name, cpuS, pct}] busiest first. Pure.
    pct is the share of ONE core over `dt` (100 = a core busy the whole window). A thread in `new` but not `old` was born
    inside the window: its whole CPU so far counts. A thread with no name in `names` is said by its id."""
    rows = []
    if not dt or dt <= 0:
        return rows
    for tid, cpu in (new or {}).items():
        used = cpu - (old or {}).get(tid, 0.0)
        if used < 0:
            continue                      # an id reused by a new thread with less CPU than the old one: not this lane
        rows.append({"name": names.get(tid) or ("thread %d" % tid), "cpuS": round(used, 3),
                     "pct": round(100.0 * used / dt, 1)})
    rows.sort(key=lambda r: (-r["cpuS"], r["name"]))
    return rows


def state(now=None, platform=None, _sample=None):
    """The console's reading for /api/status: the busiest lanes over about WINDOW_S. Takes a new sample when the newest is
    older than SAMPLE_EVERY_S. -> {ok, windowS, rows, total, why}. Never raises."""
    now = time.monotonic() if now is None else now
    with _LOCK:
        if not _SAMPLES or now - _SAMPLES[-1][0] >= SAMPLE_EVERY_S:
            got, why = (_sample or sample)(platform)
            if got is None:
                return {"ok": False, "windowS": None, "rows": [], "total": None, "why": why}
            _SAMPLES.append((now, got))
        t_new, s_new = _SAMPLES[-1]
        base = None
        for t, s in _SAMPLES:
            if t_new - t <= WINDOW_S:
                base = (t, s)
                break
        if base is None or base[0] >= t_new:
            return {"ok": False, "windowS": None, "rows": [], "total": None,
                    "why": "one sample so far - the next status call measures the window"}
    names = {t.native_id: t.name for t in threading.enumerate() if getattr(t, "native_id", None)}
    dt = t_new - base[0]
    rows = window(base[1], s_new, dt, names)
    return {"ok": True, "windowS": round(dt, 1), "rows": rows[:TOP],
            "total": round(sum(r["pct"] for r in rows), 1), "why": None}
