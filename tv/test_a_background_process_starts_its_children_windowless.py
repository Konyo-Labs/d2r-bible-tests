# -*- coding: utf-8 -*-
"""REG-3826 (GrokBot #230 11-12 23:33Z, his OLD PC ALT 11-13 ~01:30 IST) - A PROCESS WITH NO CONSOLE STARTS ITS
CHILDREN WITHOUT ONE.

His words via GrokBot: "black console windows keep popping up, one ended in a git.exe Application Error" - he wants "every
background process windowless and hidden". GrokBot SAW git.exe -C <temp test repo> commit while the console's heart2
proof import ran under pythonw. On Windows a process with no console of its own (pythonw) that starts a console program
gets a NEW visible console window for it unless the call passes CREATE_NO_WINDOW. console_safe.enable() - the first call
of nearly every law and script - now makes such a process start every child that names no creationflags windowless. A
call that asks for its own flags keeps them; a process with a console keeps sharing it; off Windows nothing changes.

Driven on a stand-in Popen class, so the rule is measured on any PC; the real Windows path is the same function.
"""
import inspect
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import console_safe as CS  # noqa: E402

NO_WINDOW = 0x08000000
NEW_CONSOLE = 0x00000010


def _fake():
    class P(object):
        def __init__(self, args, **k):
            self.args, self.kw = args, k
    return P


class TheChildrenOfAConsolelessProcess(unittest.TestCase):

    def test_a_child_that_names_no_flags_starts_windowless(self):
        P = _fake()
        self.assertTrue(CS.hide_child_consoles(_nt=True, _console=False, _popen=P))
        self.assertEqual(P(["git", "commit"]).kw.get("creationflags"), NO_WINDOW,
                         "a console-less process still starts git with a window of its own")
        self.assertEqual(P(["git"], creationflags=0).kw.get("creationflags"), NO_WINDOW, "flags=0 is no flags")

    def test_a_call_that_asks_for_its_own_flags_keeps_them(self):
        P = _fake()
        CS.hide_child_consoles(_nt=True, _console=False, _popen=P)
        self.assertEqual(P(["cmd"], creationflags=NEW_CONSOLE).kw.get("creationflags"), NEW_CONSOLE)

    def test_a_process_with_a_console_and_every_other_os_change_nothing(self):
        for nt, console in ((True, True), (False, False), (False, True)):
            P = _fake()
            self.assertFalse(CS.hide_child_consoles(_nt=nt, _console=console, _popen=P), (nt, console))
            self.assertNotIn("creationflags", P(["git"]).kw, "children were changed where nothing pops: %r" % ((nt, console),))

    def test_it_wraps_once(self):
        P = _fake()
        CS.hide_child_consoles(_nt=True, _console=False, _popen=P)
        first = P.__init__
        CS.hide_child_consoles(_nt=True, _console=False, _popen=P)
        self.assertIs(P.__init__, first, "a second enable() wrapped Popen again")

    def test_enable_installs_it(self):
        src = inspect.getsource(CS.enable)
        self.assertEqual(src.count("        hide_child_consoles()\n"), 1, "enable() no longer hides a background child's console")


RED_PROOF = [
    {"why": "REG-3826 - enable() stops hiding the children's consoles, so every git a law runs under pythonw flashes a window",
     "file": "tv/console_safe.py",
     "find": "    try:\n        hide_child_consoles()\n    except Exception:\n        pass\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3826 - a child that names no flags keeps its window again",
     "file": "tv/console_safe.py",
     "find": "            k[\"creationflags\"] = _NO_WINDOW",
     "replace": "            pass",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main()
