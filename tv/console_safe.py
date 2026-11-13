#!/usr/bin/env python3
"""v1480 — one place that makes a script's OUTPUT survive the operator's console.

Why this module exists
----------------------
This has now been the same bug three times:

  REG-044  tv_diablo needed a win32 stdio reconfigure to print its own status lines.
  REG-054  both test suites were only ever green because PYTHONIOENCODING was set by hand
           off-screen; a plain run went red AND corrupted a tracked fixture.
  REG-077  visual_lock_invariant and js_syntax_gate each PASSED their check, reached the success
           branch, and died inside print("✅ …") -> exit 1 on a clean tree.

The machine this ships on has a Hebrew console (cp1255), which cannot encode the check marks,
arrows and box characters the tooling prints everywhere. The failure is always the same shape and
always in the dangerous direction: a correct tree reports FAILURE, which trains people to ignore
the tool, and then the next real failure is ignored too.

A gate that cannot REPORT is a broken gate. Its verdict must depend on the code under test, never
on the shell that happened to launch it.

Usage
-----
    from console_safe import enable
    enable()          # first thing in main(), before anything prints

`errors="replace"` rather than a strict encoder: a character we failed to anticipate should cost a
question mark in the output, never the verdict.
"""
from __future__ import annotations

import sys

__all__ = ["enable"]


def enable(*streams):
    """Make stdout/stderr (or the given streams) encode any text without raising.

    Safe to call more than once, safe on every platform, and never raises — a helper whose job is
    to stop crashes must not become a new source of them. Returns True if every stream is now
    UTF-8 capable, False if any could not be reconfigured (an old file object, a redirect to a
    non-text stream), so a caller that cares can degrade its own output instead of guessing.
    """
    ok = True
    for stream in (streams or (sys.stdout, sys.stderr)):
        if stream is None:
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            # Python < 3.7, or a stream that is not a TextIOWrapper (pytest capture, a pipe wrapper,
            # a StringIO under test). Nothing to do and nothing worth crashing over.
            ok = False
    try:
        _install_quiet_children()
    except Exception:
        pass
    return ok


def _install_quiet_children():
    """REG-3826 (GrokBot #230, his OLD PC ALT 11-13 ~01:30: "black console windows keep popping up, one ended in a git.exe
    Application Error" - "every background process windowless and hidden"). -> win_quiet.install()'s answer

    The door already exists: tv/win_quiet.py gives every child of a Windows process CREATE_NO_WINDOW + SW_HIDE (a caller
    asking for a new console on purpose keeps it), and the console, tv_diablo and run_gates install it. The windows came
    from LAW processes - a law is its own python process, imports neither, so the door was never installed there, and a
    pythonw-run law's git helper (a gbump temp repo's commit) got a NEW visible console. enable() is the first call of
    nearly every law and script, so it installs the SAME door - never a second copy of it. [[copy-drift]]"""
    import win_quiet
    return win_quiet.install()


# ══ v3293 — THE AUDIT LIVES BESIDE THE FIX ═══════════════════════════════════════════════════
# test_control has carried this rule for a long time and it WORKS — it refused three files in tv/
# on their first run (lane_census.py, rung_accounting_wilson.py, render_check.py each say so in a
# comment) and it refused one of mine this session. The defect is not the rule, it is WHEN you
# learn: it sits inside a ~500s suite that runs at push time, which is the most expensive moment
# to discover a missing one-line import.
#
# So the rule moves HERE, next to the enable() it tells you to call, and test_control calls this
# instead of keeping its own copy. One definition, three callers (the suite, the CLI, the hook) —
# a second copy of a rule is how two rules start disagreeing. [[copy-drift]]
import glob as _glob
import os as _os
import re as _re

# an entry point that imports any of these is already safe: they call enable() on import
_VIA_IMPORT = _re.compile(r"^\s*(?:import|from)\s+(control_app|tv_diablo|console_safe)\b", _re.M)
_NON_ASCII = _re.compile(r"[^\x00-\x7F]")


def scripts(repo=None):
    """Every python entry point this rule covers. One list, so the suite and the CLI agree."""
    repo = repo or _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    tv = _os.path.join(repo, "tv")
    out = list(_glob.glob(_os.path.join(tv, "*.py")))
    out.append(_os.path.join(repo, "visual_lock_invariant.py"))
    return sorted(p for p in out if _os.path.exists(p))


def audit(repo=None):
    """-> [repo-relative paths] that print non-ASCII and never make stdout encoding-safe.

    On a cp1255 console such a script crashes WHILE REPORTING, so a clean tree exits non-zero for
    a reason that has nothing to do with what it was checking.
    """
    repo = repo or _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    bad = []
    for path in scripts(repo):
        try:
            # plain open(): this module imports only `sys` at the top, deliberately — it is the
            # first thing other scripts import, so it stays as small as it can be.
            with open(path, encoding="utf-8", errors="replace") as fh:
                src = fh.read()
        except OSError:
            continue
        if "__main__" not in src:
            continue                       # an importable module, not an entry point
        if not _NON_ASCII.search(src):
            continue                       # pure ASCII output cannot hit this
        if "reconfigure" in src or _VIA_IMPORT.search(src):
            continue
        bad.append(_os.path.relpath(path, repo))
    return bad


if __name__ == "__main__":
    import sys as _sys
    # ⚠ THE AUDITOR MUST SURVIVE THE CONSOLE IT AUDITS. Raised by the cross-family eye on v3293:
    # these lines print non-ASCII, which is the exact hazard being reported — and the audit cannot
    # see it, because the source spells them as \u2713 escapes and is therefore pure ASCII. So the
    # tool would have crashed on a cp1255 console while telling somebody else off for the same
    # thing. It calls its own fix first.
    enable()
    # an optional repo root, so a test can exercise the FAILING path on a fixture. Without it the
    # only reachable case is the clean tree, and a law that never sees the failure cannot pin it:
    # the v3293 red-proof that flipped exit(1) to exit(0) came back BLIND for exactly that reason.
    _root = _sys.argv[1] if len(_sys.argv) > 1 else None
    _bad = audit(_root)
    if _bad:
        print("\u2717 %d script(s) print non-ASCII and never make stdout encoding-safe:" % len(_bad))
        for _p in _bad:
            print("    " + _p)
        print("  On a cp1255 console these crash WHILE REPORTING, so a clean tree exits non-zero")
        print("  for a reason unrelated to the check. Add at the top:")
        print("      from console_safe import enable; enable()")
        _sys.exit(1)
    print("\u2713 encoding-safe: %d entry point(s) checked, 0 unsafe." % len(scripts(_root)))
