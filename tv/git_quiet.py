#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ONE door for every git spawn in this codebase, so no child ever owns a console.

⚠⚠ v3409 — WHY THIS IS A MODULE AND NOT A SECOND COPY. v3407 put `_git_run` in control_app.py
and routed its 14 git argv sites through it. The cross-family review of v3404 then named a site
that fix could not reach: `console_doctor.py` spawns git too (`git show --name-only`, and
`git rev-list --count HEAD..origin/main` on the eagle tick), and the v3407 gate reads only
control_app.py — so the guard was green while two more console-popping spawns survived in a file
it never opened. Giving console_doctor its own `_git_run` would be [[copy-drift]]: two bodies,
one of which will eventually stop matching. One module, every caller.

THE FAULT IT PREVENTS, measured on the Windows box 2026-09-21: `git.exe` console windows stealing
focus 2-3 in a row, every couple of minutes, while TV DIABLO sat idle. Git for Windows' PATH git
(`Git\\cmd\\git.exe`) is a 46 KB CUI WRAPPER and `pythonw` owns no console, so a CUI child
ALLOCATES one — a real terminal on top of D2R.

⚠ CREATE_NO_WINDOW ON THE WRAPPER IS NOT ENOUGH: it spawns the real git WITHOUT the flag, so the
flag protects the 46 KB stub and nothing else. `headless-git.exe` is no better — a GUI trampoline
that still starts a CUI `git.exe` child (caught live: git.exe -> headless-git.exe -> pythonw) with
Windows Terminal taking the focus. Calling `mingw64\\bin\\git.exe` DIRECTLY is what makes
CREATE_NO_WINDOW + SW_HIDE apply to the binary that actually runs.
"""
import os
import subprocess
import sys

IS_WIN = sys.platform.startswith("win")

# Windows: CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
WIN_CREATE = 0x00000200 | 0x08000000 if IS_WIN else 0

GIT_MINGW = r"C:\Program Files\Git\mingw64\bin\git.exe"
#: v3866 - GIT FOR WINDOWS SHIPS MORE THAN ONE LAYOUT. Measured on his work ALT 2026-11-06 03:09 (playing through Boosteroid):
#: Git for Windows there is the ucrt64 build - there is no mingw64\bin\git.exe - so run() fell back to the bare "git", PATH gave
#: Git\cmd\git.exe, and that CUI wrapper spawned the real ucrt64\bin\git.exe WITHOUT the flag: every console git call opened a
#: terminal window over his game (7 in 8 s at 03:08). The real binary is looked for in every layout, beside the wrapper PATH finds.
GIT_LAYOUTS = ("mingw64", "ucrt64", "clang64", "clangarm64", "mingw32")
_REAL_GIT = {}


def real_git(_isfile=os.path.isfile, _which=None, _env=None):
    r"""The git.exe that actually runs (no CUI wrapper in front of it), or None. Cached once found. -> path | None

    Tries each Git for Windows layout under the install the PATH's git belongs to (Git\cmd\git.exe -> Git\<layout>\bin\git.exe),
    then under %ProgramFiles%\Git, then the historical mingw64 path."""
    if "path" in _REAL_GIT and _isfile is os.path.isfile:
        return _REAL_GIT["path"]
    import ntpath as _np          # Windows paths on every OS, so a law can drive this from the Mac
    import shutil
    env = os.environ if _env is None else _env
    roots = []
    w = (_which or shutil.which)("git")
    if w:
        d = _np.dirname(_np.normpath(w))
        if _np.basename(d).lower() in ("cmd", "bin"):
            roots.append(_np.dirname(d))
    for pf in (env.get("ProgramFiles"), env.get("ProgramW6432"), r"C:\Program Files"):
        if pf:
            roots.append(_np.join(pf, "Git"))
    found = None
    for root in roots:
        for lay in GIT_LAYOUTS:
            p = _np.join(root, lay, "bin", "git.exe")
            if _isfile(p):
                found = p
                break
        if found:
            break
    if found is None and _isfile(GIT_MINGW):
        found = GIT_MINGW
    if _isfile is os.path.isfile and found:
        _REAL_GIT["path"] = found
    return found


def run(argv, **kw):
    """subprocess.run for git. On Windows the child must not own a console.

    Everything else is passed straight through, so a caller keeps its own cwd, timeout and
    capture settings — this adds the quiet, it does not take the control.

    ⚠⚠ #64 follow-up — NO CONSOLE GIT TAKES AN OPTIONAL LOCK. A read-only `git status` refreshes the
    index on its own and takes .git/index.lock to write it back. Every console git call runs under
    subprocess.run(timeout=N), and a timeout is a SIGKILL: git gets no chance to clean up, so a
    status killed mid-refresh leaves a 0-byte index.lock, which is the same state his ALT was stuck in
    for 11 hours. Measured on a 300-file temp repo with its mtimes touched: a plain `git status` took
    index.lock on every run; with GIT_OPTIONAL_LOCKS=0 it never did and never rewrote the index.
    Only the optional lock is affected: merge, pull and checkout still take the locks they need.
    """
    argv = list(argv)
    # the caller's env if it passed one (an empty dict is still the caller's choice), else ours
    env = dict(os.environ if kw.get("env") is None else kw["env"])
    env["GIT_OPTIONAL_LOCKS"] = "0"
    kw["env"] = env
    # v3866 - IS_WIN is read once, at import: a law that pretends to be Windows (sys.platform patched) and first
    # imports this module inside that pretence would build Windows-only arguments on a Mac. Only a Python that
    # really has Windows' process API takes the Windows branch.
    if IS_WIN and hasattr(subprocess, "STARTUPINFO"):
        if argv and argv[0] == "git":
            _rg = real_git()
            if _rg:
                argv[0] = _rg
        kw["creationflags"] = kw.get("creationflags", 0) | WIN_CREATE
        # ⚠ Git Credential Manager opens a window of its OWN and then sits there until the caller's
        # timeout kills it. A prompt nobody can answer is a stolen screen plus a stalled lane.
        env["GIT_TERMINAL_PROMPT"] = "0"
        si = kw.get("startupinfo") or subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0
        kw["startupinfo"] = si
    return subprocess.run(argv, **kw)
