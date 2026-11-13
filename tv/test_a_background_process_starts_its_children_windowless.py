# -*- coding: utf-8 -*-
"""REG-3826 (GrokBot #230 11-12 23:33Z, his OLD PC ALT 11-13 ~01:30 IST) - EVERY LAW AND SCRIPT INSTALLS THE ONE DOOR THAT
KEEPS A WINDOWS CHILD WINDOWLESS.

His words via GrokBot: "black console windows keep popping up, one ended in a git.exe Application Error" - he wants "every
background process windowless and hidden". GrokBot SAW git.exe -C <a d2r-test- temp repo> commit while the console's
heart2 proof import ran under pythonw. The door already exists - tv/win_quiet.py (REG-1307): every child of a Windows
process starts with CREATE_NO_WINDOW + SW_HIDE, a deliberate new console is kept - and the console, tv_diablo and
run_gates install it. A LAW is its own python process and imports none of them, so the door was never installed there.
console_safe.enable() is the first call of nearly every law and script: it now installs the SAME door (never a second
copy - a safety routine that exists twice is the copy that drifts). The door's own behaviour is
test_no_child_opens_a_window_on_windows; this pins the join.
"""
import inspect
import os
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import console_safe as CS  # noqa: E402
import win_quiet as WQ  # noqa: E402


class EnableInstallsTheOneDoor(unittest.TestCase):

    def test_enable_installs_win_quiet(self):
        calls = []
        with mock.patch.object(WQ, "install", lambda *a, **k: calls.append(1) or (False, "fixture")):
            CS.enable()
        self.assertEqual(calls, [1], "enable() did not install the windowless-children door")

    def test_it_is_the_same_door_never_a_copy(self):
        src = inspect.getsource(CS._install_quiet_children)
        self.assertEqual(src.count("    return win_quiet.install()\n"), 1, "the door is not the one called")
        self.assertNotIn("creationflags", inspect.getsource(CS), "console_safe carries its own copy of the door's rule")

    def test_a_door_that_will_not_import_never_breaks_enable(self):
        with mock.patch.object(CS, "_install_quiet_children", side_effect=ImportError("no win_quiet")):
            self.assertIn(CS.enable(), (True, False), "enable() raised because the door could not be installed")

    def test_on_windows_the_installed_door_hides_a_childs_window(self):
        """the join driven end to end on a Windows-shaped stand-in: enable()'s door makes a plain spawn windowless"""
        class FakeSub(object):
            class STARTUPINFO(object):
                def __init__(self):
                    self.dwFlags, self.wShowWindow = 0, 1

            class Popen(object):
                def __init__(self, args, **kw):
                    self.kw = kw
        installed, _why = WQ.install(mod=FakeSub, platform="win32")
        self.assertTrue(installed)
        kw = FakeSub.Popen(["git", "commit"]).kw
        self.assertTrue(int(kw.get("creationflags") or 0) & WQ.CREATE_NO_WINDOW, "a child of a law still gets a window")


RED_PROOF = [
    {"why": "REG-3826 - enable() stops installing the door, so a law's git under pythonw opens a black window again",
     "file": "tv/console_safe.py",
     "find": "    try:\n        _install_quiet_children()\n    except Exception:\n        pass\n",
     "replace": "",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main()
