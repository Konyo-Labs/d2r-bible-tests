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
        # v3889 round 3 - THE TREE'S OWN PROOF CENSUS IS NOT THIS FIXTURE'S. _sp_prove_yield_here asks _sp_blind_owed, which
        # reads this tree's census (self_arming._owed_and_blind); a worktree whose census held an owed BLIND (a local prove run
        # of another law) turned 4 cases red on a Mac pre-flight while GitHub's fresh tree passed. No BLIND here unless a case
        # says so (AnOwedBlindDoesNotWaitForTheImport seeds its own).
        import self_arming as _SA
        self._SA, self._oab_base = _SA, _SA._owed_and_blind
        _SA._owed_and_blind = lambda: ([], [], {})

    def tearDown(self):
        self._SA._owed_and_blind = self._oab_base
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


class TheProversRecordSaysWhatItGaveWayTo(AProofGivesWayToGithubsImport):
    """v3883 - MEASURED 11-08 on both ALTs: no D2R.exe running, and self_prove's record said "he started playing" at 09:23 and
    09:38 - the console's judge had said yes for GitHub's import. The judge carries its reason (.why); the record writes it."""

    def test_an_import_is_recorded_as_the_import_never_as_playing(self):
        """* THE POINT"""
        self._importing(True)
        self.assertTrue(CA._sp_prove_yield_here())
        self.assertEqual(SP.stand_aside(True, 99999, why=SP._play_why(CA._sp_prove_yield_here)),
                         (True, CA.IMPORT_STAND_ASIDE), "an import was recorded as 'he started playing'")

    def test_the_guard_hands_the_reason_to_the_tick_that_books_it(self):
        self._importing(True)
        seen = {}
        keep = (SP.load, SP.identity)
        try:
            SP.load = lambda path=None: {"pid": 4242, "pidBirth": 1}
            SP.identity = lambda pid, birth: True
            SP.guard(playing=CA._sp_prove_yield_here, free=99999, _tick=lambda **kw: seen.update(kw) or {"key": "stood-aside"})
        finally:
            SP.load, SP.identity = keep
        self.assertEqual(seen.get("play_why"), CA.IMPORT_STAND_ASIDE, "the tick that books the stand-aside never heard why")

    def test_a_sweep_and_a_push_say_their_own_names_and_the_game_keeps_its_words(self):
        self._importing(False)
        CA._a_sweep_is_reading = lambda: True
        self.assertTrue(CA._sp_prove_yield_here())
        self.assertIn("a sweep is reading", SP._play_why(CA._sp_prove_yield_here) or "")
        CA._a_sweep_is_reading = lambda: False
        keep = CA._a_push_is_grading
        try:
            CA._a_push_is_grading = lambda: True
            self.assertTrue(CA._sp_prove_yield_here())
            self.assertEqual(SP._play_why(CA._sp_prove_yield_here), CA.PUSH_STAND_ASIDE)
            CA._a_push_is_grading = lambda: False
            _pp = CA._sp_proof_playing_here
            CA._sp_proof_playing_here = lambda: True
            try:
                self.assertTrue(CA._sp_prove_yield_here())
                self.assertIsNone(SP._play_why(CA._sp_prove_yield_here), "the game's yes carried another reason")
                self.assertEqual(SP.stand_aside(True, 99999, why=None)[1], "he started playing - a proof never runs beside his game")
            finally:
                CA._sp_proof_playing_here = _pp
        finally:
            CA._a_push_is_grading = keep

    test_a_running_proof_yields_to_the_import = None
    test_the_guard_and_the_tick_name_the_import = None
    test_the_price_refresh_does_not_wait_on_an_import = None
    test_the_prover_asks_its_own_judge = None


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
    {"why": "v3883 - the prover's record says 'he started playing' for GitHub's import again (both ALTs, 11-08, no D2R.exe)",
     "file": "tv/self_prove.py",
     "find": "        return True, (why or \"he started playing - a proof never runs beside his game\")\n",
     "replace": "        return True, \"he started playing - a proof never runs beside his game\"\n", "matches": 1},
    {"why": "v3883 - the guard never hands the judge's reason to the tick that books the stand-aside",
     "file": "tv/self_prove.py",
     "find": "playing=play_now, free=free_now, kill_fn=kill_fn, play_why=play_why)",
     "replace": "playing=play_now, free=free_now, kill_fn=kill_fn)", "matches": 1},
    {"why": "v3883 - the import's yes carries no reason",
     "file": "tv/control_app.py",
     "find": "        _sp_prove_yield_here.why = IMPORT_STAND_ASIDE     # v3883",
     "replace": "        _sp_prove_yield_here.why = None     # v3883", "matches": 1},
    {"why": "v3883 - a push's yes is recorded as the game's",
     "file": "tv/control_app.py",
     "find": "        _sp_yield_here.why = PUSH_STAND_ASIDE\n", "replace": "", "matches": 1},
    {"why": "#123 - a running proof no longer gives way to GitHub's import (Dean: 19 proofs a minute instead of ~330)",
     "file": "tv/control_app.py",
     "find": "    if _PROOF_RELEASE.get(\"running\") is True and not _sp_blind_owed():\n        _sp_prove_yield_here.why = IMPORT_STAND_ASIDE",
     "replace": "    if False:\n        _sp_prove_yield_here.why = IMPORT_STAND_ASIDE", "matches": 1},   # v3883 re-anchor (the reason rides the judge)
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
