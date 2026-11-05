# -*- coding: utf-8 -*-
"""v3862 - A PROOF RUNS BESIDE A CLOUD GAME CLIENT; ONLY THE LOCAL GAME STOPS IT (his ruling 2026-11-05, "prove beside cloud").

MEASURED on the fleet that morning: the work ALT's census was MISSING and its river stuck, its proof lane saying "he is
playing on this PC (the game or its cloud client) - a proof never starts beside it". Boosteroid stays open there with his
AFK clicker, whose nudges also keep the OS idle clock fresh, so nothing ever let a proof start. Asked, he ruled: prove
beside cloud - the game runs in the cloud; only a local D2R.exe blocks proving, and proofs keep their low priority.

So the PROOF lane's judge (self_prove.proof_playing_state, control_app._sp_proof_playing_here) ignores a cloud client,
and every other lane that stands aside for play (the river warm, the disk sign, the shadow reader) keeps treating a cloud
client with the game on screen as play. Driven over stand-in process listings - no ps of his machine, no Toolhelp walk.
"""
import os
import subprocess
import sys
import types
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import self_prove as SP  # noqa: E402
import control_app as CA  # noqa: E402

BOOST = "4242 /Applications/Boosteroid.app/Contents/MacOS/Boosteroid"
GAME = "4343 wine64-preloader C:\\Program Files (x86)\\Diablo II Resurrected\\D2R.exe"


def _ps(*lines):
    def run(argv, *a, **k):
        return subprocess.CompletedProcess(argv, 0, "\n".join(("1 /sbin/launchd",) + lines) + "\n", "")
    return run


class TheProofJudgeIgnoresACloudClient(unittest.TestCase):

    def _posix(self, run, **kw):
        with mock.patch.object(SP, "IS_WIN", False), mock.patch.object(SP.subprocess, "run", run):
            return SP.playing_state(**kw)

    def test_premise_a_cloud_client_on_screen_is_play_for_the_other_lanes(self):
        self.assertIs(self._posix(_ps(BOOST), game_on_screen=lambda: True), True,
                      "PREMISE: a cloud client with the game on screen stopped counting as play for EVERY lane")

    def test_the_proof_runs_beside_a_cloud_client(self):
        with mock.patch.object(SP, "IS_WIN", False), mock.patch.object(SP.subprocess, "run", _ps(BOOST)):
            self.assertIs(SP.proof_playing_state(game_on_screen=lambda: True), False,
                          "a cloud client still stops the proof - the work ALT never proves")

    def test_the_local_game_still_stops_the_proof(self):
        with mock.patch.object(SP, "IS_WIN", False), mock.patch.object(SP.subprocess, "run", _ps(BOOST, GAME)):
            self.assertIs(SP.proof_playing_state(game_on_screen=lambda: False, free=1000), True,
                          "the local game no longer stops a proof on a PC short of memory")

    def test_windows_the_same_rule(self):
        seen = []

        def any_proc(pred):
            seen.append(True)
            return any(pred(n) for n in ("explorer.exe", "Boosteroid.exe", "chrome.exe"))
        fake = types.SimpleNamespace(_toolhelp_any=any_proc)
        with mock.patch.object(SP, "IS_WIN", True), mock.patch.dict(sys.modules, {"tv_diablo": fake}):
            self.assertIs(SP.playing_state(game_on_screen=lambda: True), True, "PREMISE: Windows cloud-on-screen")
            self.assertIs(SP.proof_playing_state(game_on_screen=lambda: True), False,
                          "Windows: Boosteroid still stops the proof")

            def with_game(pred):
                return any(pred(n) for n in ("Boosteroid.exe", "D2R.exe"))
            fake._toolhelp_any = with_game
            self.assertIs(SP.proof_playing_state(game_on_screen=lambda: True, free=1000), True,
                          "Windows: D2R.exe stopped counting on a PC short of memory")
        self.assertTrue(seen)

    def test_the_lane_s_own_default_is_the_proof_judge(self):
        """self_prove.tick/guard ask proof_playing_state when no judge is handed in, never the cloud-counting one."""
        import ast
        with open(os.path.join(HERE, "self_prove.py"), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        asks = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "_ask"
                and len(n.args) == 2 and isinstance(n.args[0], ast.Name) and n.args[0].id == "playing"]
        self.assertGreaterEqual(len(asks), 2, "PREMISE: the tick and the guard ask the play judge")
        for a in asks:
            self.assertEqual(getattr(a.args[1], "id", None), "proof_playing_state",
                             "a proof lane defaults to the cloud-counting judge at line %d" % a.lineno)


class TheConsoleProvesBesideCloud(unittest.TestCase):

    def setUp(self):
        self._saved = {k: getattr(CA, k) for k in ("_a_sweep_is_reading", "_a_push_is_grading", "_sp_playing_here",
                                                    "_sp_proof_playing_here")}

    def tearDown(self):
        for k, v in self._saved.items():
            setattr(CA, k, v)

    def test_the_stand_aside_judge_is_the_local_game_only(self):
        CA._a_sweep_is_reading = lambda: False
        CA._a_push_is_grading = lambda: False
        CA._sp_playing_here = lambda: True              # Boosteroid with the game on screen: play, for the other lanes
        CA._sp_proof_playing_here = lambda: False       # no local game
        self.assertFalse(CA._sp_yield_here(), "a cloud client still makes the proof stand aside")
        CA._sp_proof_playing_here = lambda: True
        self.assertTrue(CA._sp_yield_here(), "the local game no longer makes the proof stand aside")

    def test_the_console_proof_judge_asks_with_cloud_off(self):
        got = {}

        def rec(game_on_screen=None, cloud=True):
            got["cloud"] = cloud
            return False
        with mock.patch.object(SP, "playing_state", rec):
            CA._sp_proof_playing_here()
        self.assertIs(got.get("cloud"), False)


class TheLocalGameWithRoomToProve(unittest.TestCase):
    """v3863 (#241, his ruling 2026-11-03: Dean's 32 GB PC had 8.3 GB free with D2R open - "thats enough ram for his
    console to prove himself"). The local game stops a proof only while free memory is under BESIDE_GAME_FREE_MB."""

    def _ask(self, free):
        with mock.patch.object(SP, "IS_WIN", False), mock.patch.object(SP.subprocess, "run", _ps(GAME)):
            return SP.proof_playing_state(game_on_screen=lambda: True, free=free)

    def test_room_to_prove_beside_the_game(self):
        self.assertIs(self._ask(8300), False, "Dean's 8.3 GB free with D2R open still stops every proof")
        self.assertIs(self._ask(SP.BESIDE_GAME_FREE_MB), False)

    def test_short_of_memory_the_game_wins(self):
        self.assertIs(self._ask(SP.BESIDE_GAME_FREE_MB - 1), True, "a proof ran beside the game under the floor")
        self.assertIs(self._ask(1500), True, "the 8 GB ALT with the game open proved beside it")

    def test_memory_nobody_measured_is_the_game_winning(self):
        with mock.patch.object(SP, "free_mb", lambda: None):
            with mock.patch.object(SP, "IS_WIN", False), mock.patch.object(SP.subprocess, "run", _ps(GAME)):
                self.assertIs(SP.proof_playing_state(game_on_screen=lambda: True), True,
                              "UNKNOWN free memory read as room to prove")

    def test_no_game_is_untouched(self):
        with mock.patch.object(SP, "IS_WIN", False), mock.patch.object(SP.subprocess, "run", _ps()):
            self.assertIs(SP.proof_playing_state(game_on_screen=lambda: False, free=100), False)

    def test_the_other_lanes_still_count_a_cloud_client(self):
        for fn in (CA._river_warm_once, CA._disk_sign_once):
            names = set(fn.__code__.co_names)
            self.assertIn("_sp_playing_here", names, "%s stopped asking the cloud-counting judge" % fn.__name__)
            self.assertNotIn("_sp_proof_playing_here", names, "%s now proves-beside-cloud's judge" % fn.__name__)


RED_PROOF = [
    {"why": "v3863 (#241) - the local game stops every proof again, whatever is free: Dean never proves",
     "file": "tv/self_prove.py",
     "find": "    if isinstance(f, (int, float)) and not isinstance(f, bool) and f >= BESIDE_GAME_FREE_MB:\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "v3863 (#241) - a proof runs beside the game with no memory floor at all (the 8 GB ALT stutters)",
     "file": "tv/self_prove.py",
     "find": "    if isinstance(f, (int, float)) and not isinstance(f, bool) and f >= BESIDE_GAME_FREE_MB:\n",
     "replace": "    if True:\n",
     "matches": 1},
    {"why": "v3862 - a cloud client stops the proof again: the work ALT never proves (posix)",
     "file": "tv/self_prove.py",
     "find": "        if not cloud:\n            return False                       # v3862 - a cloud client never stops a proof\n",
     "replace": "",
     "matches": 1},
    {"why": "v3862 - Windows: Boosteroid stops the proof again",
     "file": "tv/self_prove.py",
     "find": "                if not cloud and (name or \"\").lower() in PLAY_EXES:\n                    return False                # v3862 - a cloud client never stops a proof\n",
     "replace": "",
     "matches": 1},
    {"why": "v3862 - the console's stand-aside judge counts a cloud client again",
     "file": "tv/control_app.py",
     "find": "    return _sp_proof_playing_here()     # v3862 - the local game only (his ruling: prove beside cloud)\n",
     "replace": "    return _sp_playing_here()\n",
     "matches": 1},
    {"why": "v3862 - the proof lane's own default judge counts a cloud client again",
     "file": "tv/self_prove.py",
     "find": "\n    play_now = _ask(playing, proof_playing_state)\n",
     "replace": "\n    play_now = _ask(playing, playing_state)\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
