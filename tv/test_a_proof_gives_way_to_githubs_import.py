# -*- coding: utf-8 -*-
"""v3882 (#123) - A PROOF ALREADY RUNNING ON A PC GIVES WAY TO GITHUB'S IMPORT OF ITS PROOFS, AND THE CARD SAYS SO.

MEASURED on Dean's PC (SSH, read-only): his console's heart2 --prove of 15:42 kept running beside the 16:39 import of
GitHub's proofs, at up to 237% CPU, and at 23:50 that kind of import crawled at ~19 proofs a minute (2,989 -> 3,056 of 4,954
in 3.5 min). From 00:28 to 00:39, with his game up and the proof paused, the next import ran at ~330 a minute and landed
9,295 of 9,295 at 00:57. v3862 kept a NEW proof tick from starting while an import ran; a proof that began BEFORE the import
had nothing telling it to stop, so the two fought for the cores and the import - GitHub's proofs, the fast way to a current
census - lost.

Now the prover's stand-aside judge (_sp_prove_yield_here) is the console's (_sp_yield_here: his game, a sweep, a push) plus
a running import, so a running proof yields within one guard tick and the card names the import as the reason; the
after-import tick (REG-3195) resumes it on what is still owed (after self_prove's stand-aside cooldown). The d2jsp price
refresh keeps asking _sp_yield_here - an import is no reason for it to wait. Drives the console's real judges, guard and
tick wrappers with the process list, the game and the sweep stubbed - no live import, no live prover. RED_PROOF below.
[[the-unjoined-end]]
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import self_prove as SP  # noqa: E402
import control_app as CA  # noqa: E402

QUIET = [("1", "0", 999999, "/sbin/launchd"), ("700", "1", 40000, "/usr/bin/python3 tv/control_app.py --open")]


class AProofGivesWayToGithubsImport(unittest.TestCase):

    def setUp(self):
        self._saved = {k: getattr(CA, k) for k in ("_a_sweep_is_reading", "_sp_playing_here", "shadow_game_detail",
                                                    "_self_prove_free_view", "_proof_carrier_kick")}
        self._sp = {k: getattr(SP, k) for k in ("process_rows", "guard", "tick")}
        self._state = dict(CA._SELF_PROVE)
        self._rel = dict(CA._PROOF_RELEASE)
        CA._a_sweep_is_reading = lambda: False
        CA._sp_playing_here = lambda: False
        CA.shadow_game_detail = lambda *a, **k: None
        CA._self_prove_free_view = lambda r, *a, **k: r
        CA._proof_carrier_kick = lambda *a, **k: {}
        SP.process_rows = lambda run=None: list(QUIET)
        CA._PUSH_GRADING.update(at=0.0, v=(False, ""))

    def tearDown(self):
        for k, v in self._saved.items():
            setattr(CA, k, v)
        for k, v in self._sp.items():
            setattr(SP, k, v)
        CA._SELF_PROVE.clear()
        CA._SELF_PROVE.update(self._state)
        CA._PROOF_RELEASE.clear()
        CA._PROOF_RELEASE.update(self._rel)
        CA._PUSH_GRADING.update(at=0.0, v=(False, ""))

    def _importing(self, yes):
        CA._PROOF_RELEASE["running"] = bool(yes)

    def test_a_running_proof_yields_to_the_import(self):
        """* THE POINT - Dean's 15:42 proof beside the 16:39 import"""
        self._importing(False)
        self.assertFalse(CA._sp_prove_yield_here(), "PREMISE: no import, no game, no sweep, no push - and it yields")
        self._importing(True)
        self.assertTrue(CA._sp_prove_yield_here(), "GitHub's import is running and the proof was not told to give way")

    def test_the_price_refresh_does_not_wait_on_an_import(self):
        """the console's shared judge is unchanged: the d2jsp price refresh asks it, and an import is no reason to wait"""
        self._importing(True)
        self.assertFalse(CA._sp_yield_here())

    def test_the_prover_asks_its_own_judge(self):
        seen = {}
        SP.guard = lambda **kw: seen.setdefault("guard", kw.get("playing")) and None
        SP.tick = lambda **kw: seen.setdefault("tick", kw.get("playing")) and {"key": "idle"}
        CA._self_prove_guard()
        CA._self_prove_tick()
        self.assertIs(seen.get("guard"), CA._sp_prove_yield_here)
        self.assertIs(seen.get("tick"), CA._sp_prove_yield_here)

    def test_the_guard_and_the_tick_name_the_import(self):
        self._importing(True)
        SP.guard = lambda **kw: {"key": "aside-cooldown", "say": "stood aside"}
        self.assertEqual(CA._self_prove_guard().get("standAside"), CA.IMPORT_STAND_ASIDE,
                         "the guard stood aside and did not say for what")
        SP.tick = lambda **kw: {"key": "aside-cooldown", "say": "stood aside"}
        self.assertEqual(CA._self_prove_tick().get("standAside"), CA.IMPORT_STAND_ASIDE)


RED_PROOF = [
    {"why": "#123 - a running proof no longer gives way to GitHub's import (Dean: 19 proofs a minute instead of ~330)",
     "file": "tv/control_app.py",
     "find": "    if _PROOF_RELEASE.get(\"running\") is True:\n        return True\n    return _sp_yield_here()\n",
     "replace": "    return _sp_yield_here()\n", "matches": 1},
    {"why": "#123 - the guard asks the shared judge again, which never waits on an import",
     "file": "tv/control_app.py",
     "find": "        r = _sp.guard(busy=_cpu_busy_pct, playing=_sp_prove_yield_here)   # REG-2192 a sweep · #123 an import\n",
     "replace": "        r = _sp.guard(busy=_cpu_busy_pct, playing=_sp_yield_here)\n", "matches": 1},
    {"why": "#123 - the card does not say the proof gave way to the import",
     "file": "tv/control_app.py",
     "find": "            if _PROOF_RELEASE.get(\"running\") is True and not _sp_proof_playing_here():   # #123\n"
             "                r = dict(r, standAside=IMPORT_STAND_ASIDE)\n",
     "replace": "", "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
