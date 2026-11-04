# -*- coding: utf-8 -*-
"""v3860 - A WINDOWS CONSOLE, AND THE PROVER IT STARTS, RUN IN PYTHON'S UTF-8 MODE.

Windows Python reads and writes subprocess text and open() in the ANSI codepage (cp1255 on his ALT, cp1252 on Dean's
PC). Node writes UTF-8, so a text-mode read of node's output dies in the reader thread (stdout comes back None) or
mojibakes a middle dot into two letters, and writing a `⚠` to a child's stdin raises UnicodeEncodeError.
MEASURED 2026-11-04 on the new Konyo · ALT: 94 law cases FAILED (3 failures, 20 errors) in the ANSI codepage and were
OK (99) with nothing but PYTHONUTF8=1 added.

Two doors, two halves of one fix:
  * the launcher (start_tvd_win.ps1) - the mode is chosen when an interpreter STARTS. control_app.py has put
    PYTHONUTF8 into os.environ at import since v1463, which reaches every child, but never the console process itself;
  * self_prove.spawn - the census must not depend on WHO called it. The console's lane inherited the mode from that
    import; a hand runner did not, and its census filed at least 9 laws red that the console's lane runs green.
"""
import io
import os
import re
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import self_prove as SP  # noqa: E402

LAUNCHER = os.path.join(HERE, "start_tvd_win.ps1")
SET_LINE = "$env:PYTHONUTF8 = '1'"
SPAWN_LINE = "$proc = Start-Process -FilePath $exePath -ArgumentList $argLine"


def _code(path):
    """The launcher's lines with PowerShell comments cut, so a comment that NAMES the setting never satisfies it."""
    with io.open(path, encoding="utf-8-sig") as fh:
        return [ln.split("#", 1)[0].rstrip() for ln in fh.read().split("\n")]


class TheLauncherStartsTheConsoleInUtf8Mode(unittest.TestCase):

    def test_the_mode_is_set_before_the_console_is_started(self):
        lines = _code(LAUNCHER)
        sets = [i for i, ln in enumerate(lines) if ln.strip() == SET_LINE]
        starts = [i for i, ln in enumerate(lines) if ln.strip().startswith(SPAWN_LINE)]
        self.assertEqual(len(starts), 1, "PRINT THE DENOMINATOR: the launcher's one Start-Process of the console "
                                         "was not found (%d) - this case would measure nothing" % len(starts))
        self.assertTrue(sets, "start_tvd_win.ps1 starts the console without PYTHONUTF8=1, so the console process "
                              "runs in the ANSI codepage and its own node reads die or mojibake on every Windows PC")
        self.assertLess(min(sets), starts[0], "PYTHONUTF8 is set AFTER the console was started - an interpreter "
                                              "chooses its mode at start, so the setting reaches nothing")


class _Door(object):
    def __init__(self):
        self.calls = []

    def __call__(self, role, argv, popen=None, **kw):
        self.calls.append(dict(kw))

        class _P(object):
            pid = 4242
        return _P()


class TheProverItStartsRunsInUtf8Mode(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="utf8_prover_")
        self.addCleanup(shutil.rmtree, self.d, True)

    def _env(self, win):
        door = _Door()
        clean = dict((k, v) for k, v in os.environ.items() if k != "PYTHONUTF8")   # a caller that never set it
        with mock.patch.object(SP, "_guard_spawn", door), mock.patch.object(SP, "IS_WIN", win), \
                mock.patch.dict(os.environ, clean, clear=True):
            SP.spawn(os.path.join(self.d, "log"), python=sys.executable, workers=1, names=["g1"])
        self.assertEqual(len(door.calls), 1, "premise: the prover was not started through the door")
        return door.calls[0].get("env") or {}

    def test_a_windows_prover_is_in_utf8_mode_whoever_called_spawn(self):
        self.assertEqual(self._env(True).get("PYTHONUTF8"), "1",
                         "a Windows prover started by anyone but the console runs in the ANSI codepage: its census "
                         "files every law that pipes UTF-8 through a child as red (at least 9 on the ALT, 11-04)")

    def test_a_posix_prover_is_left_as_its_caller_had_it(self):
        self.assertNotIn("PYTHONUTF8", self._env(False),
                         "spawn forced UTF-8 mode on a POSIX prover - the Mac and CI never asked for it")


RED_PROOF = [
    {"why": "v3860 - the launcher starts the console without UTF-8 mode: the console's own node reads die or mojibake "
            "in the ANSI codepage on every Windows PC",
     "file": "tv/start_tvd_win.ps1",
     "find": "$env:PYTHONUTF8 = '1'\n",
     "replace": "",
     "matches": 1},
    {"why": "v3860 - a prover started by anyone but the console inherits the ANSI codepage, so a hand-run census files "
            "every UTF-8 law red on Windows",
     "file": "tv/self_prove.py",
     "find": "    if IS_WIN:\n        env[\"PYTHONUTF8\"] = \"1\"\n",
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
