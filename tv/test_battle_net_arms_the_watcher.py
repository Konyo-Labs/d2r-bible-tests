# -*- coding: utf-8 -*-
"""v3900 (REG-3748, #188) - BATTLE.NET OPEN ARMS THE SHADOW WATCHER: IT LOOKS FOR THE GAME EVERY 2 S, NOT EVERY 20.

His ruling 11-11: a route's own pre-game screen is the EARLY WARNING that arms the recorder ("it can start already like
understanding the game is coming to notify the future mechanism.. that can be smart so no delay happens"); his words 11-12:
"locally it opens battle.net and then it can be armed based on window already.. and then the same mechanism process".
MEASURED 11-12 on Dean's PC (Battle.net's own log + his shadow log, frozen off the repo): Battle.net launched the game at
17:38:18, the watcher's 20-second look opened the reel 15 s later, and the D2 logo had gone by. Now, while the reader is on,
no reel rolls and Battle.net runs, the loop sleeps 2 s and runs the full look the moment the game's process exists (or when
the 20 s look is due anyway); between them only a cheap process check runs. UNKNOWN arms nothing. A rolling reel disarms.

DRIVEN: the real _shadow_armed / _shadow_full_look_due over their seams, self_prove.launcher_state over a fake process list,
and the loop's own source. RED_PROOF below.
"""
import inspect
import os
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

import control_app as ca  # noqa: E402
import self_prove as SP  # noqa: E402


class _R(object):
    def __init__(self, rc, out):
        self.returncode, self.stdout = rc, out


class BattleNetArmsTheWatcher(unittest.TestCase):

    def test_battle_net_open_and_no_reel_arms_it(self):
        """* THE POINT - Dean 11-07: launch 17:38:18, reel 15 s later, the logo gone"""
        armed, why = ca._shadow_armed(launcher=True, rolling=False, on=True)
        self.assertTrue(armed, why)
        self.assertIn("every %d s" % ca._SHADOW_ARM_EVERY_S, why)
        self.assertLess(ca._SHADOW_ARM_EVERY_S, ca._SHADOW_WATCH_EVERY_S)

    def test_baseline_nothing_else_arms_it(self):
        for kw, word in ((dict(launcher=False, rolling=False, on=True), "not running"),
                         (dict(launcher=None, rolling=False, on=True), "could not be read"),
                         (dict(launcher=True, rolling=True, on=True), "rolling"),
                         (dict(launcher=True, rolling=False, on=False), "not on")):
            armed, why = ca._shadow_armed(**kw)
            self.assertFalse(armed, "%r armed the watcher: %s" % (kw, why))
            self.assertIn(word, why)

    def test_while_armed_the_full_look_waits_for_the_game(self):
        due = ca._shadow_full_look_due
        self.assertTrue(due(False, None, 0.0), "an unarmed watcher skipped its look")
        self.assertTrue(due(True, True, 0.5), "the game's process is up and the full look did not run")
        self.assertFalse(due(True, False, 4.0), "armed with no game: a full window look ran every 2 s")
        self.assertFalse(due(True, None, 4.0), "an unknown game state ran a full look before the 20 s")
        self.assertTrue(due(True, False, float(ca._SHADOW_WATCH_EVERY_S)), "armed starved the ordinary 20 s look")

    def test_the_launcher_is_read_off_the_process_list(self):
        with mock.patch.object(SP, "IS_WIN", False):
            with mock.patch.object(SP.subprocess, "run", lambda *a, **k: _R(0, "/Applications/x/Battle.net.exe --x\nzsh\n")):
                self.assertIs(SP.launcher_state(), True)
            with mock.patch.object(SP.subprocess, "run", lambda *a, **k: _R(0, "zsh\n/usr/bin/python3\n")):
                self.assertIs(SP.launcher_state(), False)
            with mock.patch.object(SP.subprocess, "run", lambda *a, **k: _R(1, "")):
                self.assertIsNone(SP.launcher_state(), "a process list that could not be read said no launcher")

    def test_the_loop_sleeps_armed_and_skips_until_the_game(self):
        src = "\n".join(l.split("#", 1)[0] for l in inspect.getsource(ca._shadow_watch_loop).split("\n"))
        self.assertEqual(src.count("time.sleep(_SHADOW_ARM_EVERY_S if _armed else _SHADOW_WATCH_EVERY_S)"), 1,
                         "the loop no longer looks faster while armed")
        self.assertEqual(src.count("if not _shadow_full_look_due(_armed, _game_running() if _armed else None, "), 1,
                         "the loop no longer waits for the game's process between full looks")


RED_PROOF = [
    {"why": "REG-3748 - Battle.net open no longer arms the watcher; the 20 s look misses the D2 logo again (Dean 11-07)",
     "file": "tv/control_app.py",
     "find": "        if launcher is True:\n            return True, (\"armed - Battle.net is open",
     "replace": "        if False:\n            return True, (\"armed - Battle.net is open",
     "matches": 1},
    {"why": "REG-3748 - the armed loop never runs the full look when the game's process appears",
     "file": "tv/control_app.py",
     "find": "    return game_running is True or since_full_s >= _SHADOW_WATCH_EVERY_S\n",
     "replace": "    return since_full_s >= _SHADOW_WATCH_EVERY_S\n",
     "matches": 1},
    {"why": "REG-3748 - the loop sleeps 20 s while armed",
     "file": "tv/control_app.py",
     "find": "            time.sleep(_SHADOW_ARM_EVERY_S if _armed else _SHADOW_WATCH_EVERY_S)\n",
     "replace": "            time.sleep(_SHADOW_WATCH_EVERY_S)\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
