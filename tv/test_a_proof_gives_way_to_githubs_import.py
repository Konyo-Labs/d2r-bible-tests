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

v3883 - EXCEPT A BLIND THE PC STILL OWES. MEASURED on the work ALT 11-08 ~09:40 (v3882 pulled 09:03): its four locks shut by
two BLIND verdicts its v3881 census filed, GitHub's import keying at 0.55 a second (~83 min left), and the prover standing
aside for all of it - while both laws, run by hand on that PC at v3882's bytes, went RED on 7 of 7 and 8 of 8 sabotages. An
owed BLIND is proved first and ALONE (REG-1673: one law), so it runs beside an import; the next slice yields as before. A
BLIND already judged on these bytes owes nothing and waits; an unreadable census waits; his game still wins.
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


class AnOwedBlindDoesNotWaitForTheImport(AProofGivesWayToGithubsImport):
    """v3883 - the work ALT, 11-08: an owed BLIND shut every lock while the prover waited ~83 min for an import"""

    def setUp(self):
        super(AnOwedBlindDoesNotWaitForTheImport, self).setUp()
        import self_arming as SA
        self.SA = SA
        self._oab = SA._owed_and_blind
        self.census = {"owed": ["test_a", "test_blind"], "blind": ["test_blind"]}
        SA._owed_and_blind = lambda: (self.census["owed"], self.census["blind"], {})

    def tearDown(self):
        self.SA._owed_and_blind = self._oab
        super(AnOwedBlindDoesNotWaitForTheImport, self).tearDown()

    def test_an_owed_blind_is_proved_beside_the_import(self):
        """* THE POINT - the work ALT's two stale BLIND verdicts, its locks shut through an 83-minute import"""
        self._importing(True)
        self.assertFalse(CA._sp_prove_yield_here(), "an owed BLIND waited for the whole import, every lock shut")
        self.assertTrue(CA._sp_blind_owed())

    def test_baseline_no_blind_still_yields(self):
        self._importing(True)
        self.census.update(blind=[])
        self.assertTrue(CA._sp_prove_yield_here(), "PREMISE: without a BLIND the proof gives way to the import (REG-3408)")

    def test_a_blind_already_judged_here_waits(self):
        """a BLIND on these bytes owes nothing - re-running it says BLIND again, and the import keeps the cores"""
        self._importing(True)
        self.census.update(owed=["test_a"])
        self.assertTrue(CA._sp_prove_yield_here())
        self.assertFalse(CA._sp_blind_owed())

    def test_an_unreadable_census_waits_and_his_game_still_wins(self):
        self._importing(True)
        self.SA._owed_and_blind = lambda: (None, None, "no proof census on this PC")
        self.assertTrue(CA._sp_prove_yield_here(), "an unreadable census let the prover fight the import")
        self.SA._owed_and_blind = lambda: 1 / 0
        self.assertTrue(CA._sp_prove_yield_here(), "a census reader that raised let the prover fight the import")
        self.SA._owed_and_blind = lambda: (self.census["owed"], self.census["blind"], {})
        _keep = CA._sp_proof_playing_here
        CA._sp_proof_playing_here = lambda: True
        try:
            self.assertTrue(CA._sp_prove_yield_here(), "an owed BLIND outranked his game")
        finally:
            CA._sp_proof_playing_here = _keep

    def test_the_card_does_not_say_it_waits_for_the_import(self):
        self._importing(True)
        SP.tick = lambda **kw: {"key": "proving", "say": "proving the BLIND"}
        self.assertNotEqual(CA._self_prove_tick().get("standAside"), CA.IMPORT_STAND_ASIDE,
                            "the card said the proof gives way to the import while it proved the BLIND")
        SP.guard = lambda **kw: {"key": "proving", "say": "proving the BLIND"}
        self.assertNotEqual((CA._self_prove_guard() or {}).get("standAside"), CA.IMPORT_STAND_ASIDE)

    # the parent's cases assume no BLIND: they run in the parent class only
    test_a_running_proof_yields_to_the_import = None
    test_the_guard_and_the_tick_name_the_import = None


RED_PROOF = [
    {"why": "#123 - a running proof no longer gives way to GitHub's import (Dean: 19 proofs a minute instead of ~330)",
     "file": "tv/control_app.py",
     "find": "    if _PROOF_RELEASE.get(\"running\") is True and not _sp_blind_owed():\n        return True\n    return _sp_yield_here()\n",
     "replace": "    return _sp_yield_here()\n", "matches": 1},   # v3883 re-anchor
    {"why": "v3883 - an owed BLIND waits for the whole import again (the work ALT: every lock shut ~83 min)",
     "file": "tv/control_app.py",
     "find": "    if _PROOF_RELEASE.get(\"running\") is True and not _sp_blind_owed():\n",
     "replace": "    if _PROOF_RELEASE.get(\"running\") is True:\n", "matches": 1},
    {"why": "v3883 - a BLIND already judged on these bytes runs beside the import (it would only say BLIND again)",
     "file": "tv/control_app.py",
     "find": "        return bool(set(str(b) for b in blind) & set(str(o) for o in owed))\n",
     "replace": "        return bool(blind)\n", "matches": 1},
    {"why": "v3883 - an unreadable census lets the prover fight the import",
     "file": "tv/control_app.py",
     "find": "        if not owed or not blind:\n            return False\n        return bool(set(str(b)",
     "replace": "        if not owed or not blind:\n            return True\n        return bool(set(str(b)", "matches": 1},
    {"why": "v3883 - the tick's card says the proof waits for the import while it proves the BLIND",
     "file": "tv/control_app.py",
     "find": "                and not _sp_blind_owed()):                                         # v3883 - an owed BLIND does not wait\n"
             "            r = dict(r, standAside=IMPORT_STAND_ASIDE)",
     "replace": "                or False):\n            r = dict(r, standAside=IMPORT_STAND_ASIDE)", "matches": 1},
    {"why": "#123 - the guard asks the shared judge again, which never waits on an import",
     "file": "tv/control_app.py",
     "find": "        r = _sp.guard(busy=_cpu_busy_pct, playing=_sp_prove_yield_here)   # REG-2192 a sweep · #123 an import\n",
     "replace": "        r = _sp.guard(busy=_cpu_busy_pct, playing=_sp_yield_here)\n", "matches": 1},
    {"why": "#123 - the card does not say the proof gave way to the import",
     "file": "tv/control_app.py",
     "find": "            if (_PROOF_RELEASE.get(\"running\") is True and not _sp_proof_playing_here()   # #123\n"
             "                    and not _sp_blind_owed()):                                         # v3883 - an owed BLIND does not wait\n"
             "                r = dict(r, standAside=IMPORT_STAND_ASIDE)\n",
     "replace": "", "matches": 1},   # v3883 re-anchor
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
