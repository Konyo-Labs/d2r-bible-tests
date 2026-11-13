# -*- coding: utf-8 -*-
"""No child process of the console may open a window on Windows.

HIS REPORT, 2026-09-26: "on windows specifically a window terminal keeps jumping up and alt tabbing me and even
deans computer.. because the console its refreshing and like fetching data or something it has some background
process that jumps all the time and exits us from the game.. i need this hidden... no window should be opening".

THE MECHANISM. The console runs as pythonw.exe - no console of its own. A console-subsystem child it starts (git,
powershell, schtasks, tasklist, python.exe, ffmpeg ...) therefore gets a NEW console window unless the spawn passes
CREATE_NO_WINDOW; the window appears, takes focus, and pulls him out of a full-screen game. git_quiet.py fixed the git
spawns one door at a time; MEASURED the same night by a static sweep, 82 spawn sites across 38 tv/ modules pass no
creationflags at all - 24 of them in the three modules that run on his Windows machine every tick (control_app 10,
tv_diablo 8, console_doctor 6). Fixing 82 call sites one by one would miss the 83rd.

SO THIS IS THE DOOR, NOT A SITE. subprocess.run / call / check_output / check_call all construct `Popen` from the
subprocess module's own globals, so replacing `subprocess.Popen` once - first thing in each Windows process - covers
every spawn that exists and every one written later. [[heart-first]] rule 4: instrument at the door.

WHAT IT DOES, only on win32: every child gets CREATE_NO_WINDOW and a STARTUPINFO with SW_HIDE - UNLESS the caller
asked for a window on purpose (CREATE_NEW_CONSOLE, or DETACHED_PROCESS, both meaningful choices), which is respected.
Anywhere else it does nothing and says so. It never changes arguments, pipes, env or cwd.
"""
import os
import subprocess
import sys

CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_CONSOLE = 0x00000010
DETACHED_PROCESS = 0x00000008
STARTF_USESHOWWINDOW = 0x00000001
SW_HIDE = 0


def _quiet_kwargs(kw, mod):
    """-> the kwargs a Windows child should really get. Pure, so a law can drive it anywhere."""
    kw = dict(kw)
    flags = int(kw.get("creationflags") or 0)
    if not (flags & (CREATE_NEW_CONSOLE | DETACHED_PROCESS)):
        kw["creationflags"] = flags | CREATE_NO_WINDOW
    # A new console was asked for so a person can read it and type into it. SW_HIDE
    # on that console leaves it allocated and invisible: the sign-in prints its URL
    # into a window nobody can see, then waits for a paste that never arrives.
    if not (flags & CREATE_NEW_CONSOLE) and kw.get("startupinfo") is None and hasattr(mod, "STARTUPINFO"):
        si = mod.STARTUPINFO()
        si.dwFlags = int(getattr(si, "dwFlags", 0) or 0) | STARTF_USESHOWWINDOW
        si.wShowWindow = SW_HIDE
        kw["startupinfo"] = si
    return kw


def install(mod=None, platform=None):
    """Make every child of this process windowless on Windows. -> (installed_now, why)."""
    mod = subprocess if mod is None else mod
    # REG-3826 (v3905 pre-flight c): with no platform handed in, the REAL operating system decides, never sys.platform.
    # test_the_gates_load_on_windows patches sys.platform to "win32" for a moment to drive heart2's Windows copy path on a
    # Mac; console_safe.enable() inside that moment installed this door for the rest of the process, and every later child
    # on the Mac was refused (ValueError: the window flag is Windows-only). A caller that names a platform keeps it.
    if platform is None:
        platform = "win32" if os.name == "nt" else sys.platform
        if platform == "win32" and os.name != "nt":
            platform = "posix"
    if platform != "win32":
        return False, "not Windows - a child process opens no window here"
    base = mod.Popen
    if getattr(base, "_tvd_quiet", False):
        return False, "already installed in this process"

    class QuietPopen(base):
        _tvd_quiet = True

        def __init__(self, *args, **kw):
            super(QuietPopen, self).__init__(*args, **_quiet_kwargs(kw, mod))

    QuietPopen.__name__ = QuietPopen.__qualname__ = "Popen"
    mod.Popen = QuietPopen
    return True, "every child of this process starts with CREATE_NO_WINDOW + SW_HIDE"


def installed(mod=None):
    mod = subprocess if mod is None else mod
    return bool(getattr(mod.Popen, "_tvd_quiet", False))
