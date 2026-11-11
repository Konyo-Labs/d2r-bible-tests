# -*- coding: utf-8 -*-
"""v3861 - A PROOF ALREADY RUNNING ON THIS PC STANDS ASIDE FOR A PUSH THAT IS GRADING HERE, AND NEVER FOR ITS OWN LAW.

MEASURED 2026-11-05 ~02:00 on his Mac: the console's own `heart2 --prove test_control` started about 20 minutes before
the v3860 push and kept running the same suite beside the push's test_control. self_prove.stand_aside() stopped a running
proof for his game and for low memory only, and decide() refuses only to START a proof on a busy machine, so a proof that
began before a push ran through the whole gate. v3860's push #2 was refused on two timing cases that pass alone; that load
is what refuses a push.

The rule: a pre-push hook or `git push` (tree_busy's one definition) alive PUSH_GRADING_AFTER_S on this PC makes the
console's stand-aside judge say yield, so a running proof stands aside within one guard tick and none starts during the
push; the console card names the push as the reason. Three edges, each a case: a hook run by the prover's OWN law (laws
run the hook in fixture repos) never counts, or the proof would end itself every slice; a ci/ push's hook that exits in
seconds never counts, or each one would cost the proof a half-hour cooldown; a process list that cannot be read is
UNKNOWN, never a push.

Drives the real push_grading / process_rows over stand-in process tables, and the console's real _sp_yield_here, guard and
tick wrappers with the process list stubbed - no live push, no live prover, no ps of his machine.
"""
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import self_prove as SP  # noqa: E402
import control_app as CA  # noqa: E402

PROVER = "/usr/bin/python3 -X tvd_self_prove /repo/tv/heart2.py --prove test_control --slice --reuse"
GIT_PUSH = "git -c core.hooksPath=hooks push origin HEAD:main"
HOOK = "/bin/bash hooks/pre-push origin git@github.com:o/r.git"


def _table(*extra):
    base = [("1", "0", 999999, "/sbin/launchd"),
            ("500", "1", 50000, "/bin/zsh -l"),
            ("700", "1", 40000, "/usr/bin/python3 tv/control_app.py --open"),
            ("701", "700", 1500, PROVER),
            ("702", "701", 1400, "/usr/bin/python3 /tmp/heart2.x/repo/tv/test_control.py")]
    return base + list(extra)


class PushGrading(unittest.TestCase):

    def test_a_push_from_a_shell_is_grading(self):
        got, why = SP.push_grading(_table(("800", "500", 300, GIT_PUSH), ("801", "800", 299, HOOK)))
        self.assertIs(got, True, "a push grading for 5 minutes was not seen: %r" % why)
        self.assertIn("800", why)

    def test_the_provers_own_law_running_the_hook_is_not_a_push(self):
        rows = _table(("710", "702", 400, "/bin/bash /tmp/fx/repo/hooks/pre-push origin /tmp/fx/remote"),
                      ("711", "701", 400, "git -C /tmp/fx/repo push origin HEAD:main"))
        got, why = SP.push_grading(rows)
        self.assertIs(got, False, "the prover's own law read as a push - the proof would end itself: %r" % why)

    def test_a_ship_running_here_is_given_the_cores_and_its_launcher_is_not_one(self):
        """v3896 (REG-3678) - a ship runs the main push's gates on this Mac; the console's proof stands aside for it"""
        ship = ("900", "500", 600, "/Library/Python.app/Contents/MacOS/Python -u tv/ship_when_green.py v3895 --no-preflight")
        launcher = ("899", "500", 600, "/bin/zsh -c nohup env python3 -u tv/ship_when_green.py v3895")
        got, why = SP.push_grading(_table(ship, launcher))
        self.assertIs(got, True, "a ship running for 10 minutes was not seen: %r" % why)
        self.assertIn("a ship is running on this PC (pid 900)", why)
        self.assertIs(SP.push_grading(_table(launcher))[0], False, "the shell that launched a ship was read as the ship")
        self.assertIs(SP.push_grading(_table(ship), self_pid="900")[0], False, "a ship read itself as one to stand aside for")

    def test_a_ci_push_over_in_seconds_is_not_grading_yet(self):
        rows = _table(("800", "500", 5, "git push origin HEAD:ci/claude-v3861"), ("801", "800", 4, HOOK))
        self.assertEqual(SP.push_grading(rows)[0], False,
                         "a 5-second-old ci push read as grading - each would cost the proof its cooldown")

    def test_a_running_hook_whose_age_cannot_be_read_still_counts(self):
        self.assertIs(SP.push_grading(_table(("801", "500", None, HOOK)))[0], True)

    def test_an_unreadable_process_list_is_unknown_never_a_push(self):
        got, why = SP.push_grading(None)
        self.assertIsNone(got, "a process list nobody read was given a verdict")
        self.assertIn("could not be read", why)

    def test_the_push_that_is_running_the_asker_is_not_one_to_yield_to(self):
        """CAUGHT BY THE v3861 PUSH ITSELF: a law inside the pre-push asked the judge, saw that very push, and read
        "yield" on an idle fixture. A hook that is an ancestor of the asking process is the push running it."""
        rows = _table(("800", "500", 300, GIT_PUSH), ("801", "800", 299, HOOK),
                      ("900", "801", 120, "/usr/bin/python3 tv/run_gates.py --fast"),
                      ("901", "900", 30, "/usr/bin/python3 tv/test_control.py"))
        self.assertIs(SP.push_grading(rows, self_pid="901")[0], False,
                      "a law inside the gate yields to the push that is running it")
        self.assertIs(SP.push_grading(rows, self_pid="700")[0], True,
                      "his console (no hook above it) stopped seeing a real push")

    def test_naming_the_hook_is_not_running_it(self):
        rows = _table(("820", "500", 900, "grep -n pre-push hooks/pre-push"), ("821", "500", 900, "git log --grep push"))
        self.assertEqual(SP.push_grading(rows)[0], False)


class ProcessRows(unittest.TestCase):

    def test_ps_elapsed_times_read(self):
        self.assertEqual(SP._etime_s("1-02:03:04"), 93784)
        self.assertEqual(SP._etime_s("02:03:04"), 7384)
        self.assertEqual(SP._etime_s("05:06"), 306)
        self.assertIsNone(SP._etime_s("junk"))

    def test_the_posix_table_is_read_and_a_failed_ps_is_unknown(self):
        if SP.IS_WIN:
            self.skipTest("the posix reader - Windows reads CIM; this case is UNMEASURED there, not passing")
        out = "  1     0 30-06:09:47 /sbin/launchd\n 801   500   01:05 /bin/bash hooks/pre-push origin url\n"

        def ok(argv, **kw):
            return subprocess.CompletedProcess(argv, 0, out, "")

        def bad(argv, **kw):
            return subprocess.CompletedProcess(argv, 1, "", "ps: denied")
        rows = SP.process_rows(run=ok)
        self.assertEqual(rows[1], ("801", "500", 65, "/bin/bash hooks/pre-push origin url"))
        self.assertIsNone(SP.process_rows(run=bad))


class TheConsoleYieldsAndSaysWhy(unittest.TestCase):

    def setUp(self):
        self._saved = {k: getattr(CA, k) for k in ("_a_sweep_is_reading", "_sp_playing_here", "shadow_game_detail",
                                                    "_self_prove_free_view", "_proof_carrier_kick")}
        self._sp = {k: getattr(SP, k) for k in ("process_rows", "guard", "tick")}
        self._state = dict(CA._SELF_PROVE)
        CA._a_sweep_is_reading = lambda: False
        CA._sp_playing_here = lambda: False
        CA.shadow_game_detail = lambda *a, **k: None
        CA._self_prove_free_view = lambda r, *a, **k: r
        CA._proof_carrier_kick = lambda *a, **k: {}
        CA._PUSH_GRADING.update(at=0.0, v=(False, ""))

    def tearDown(self):
        for k, v in self._saved.items():
            setattr(CA, k, v)
        for k, v in self._sp.items():
            setattr(SP, k, v)
        CA._SELF_PROVE.clear()
        CA._SELF_PROVE.update(self._state)
        CA._PUSH_GRADING.update(at=0.0, v=(False, ""))

    def _pushing(self, yes):
        SP.process_rows = (lambda run=None: _table(("800", "500", 300, GIT_PUSH))) if yes else (lambda run=None: _table())
        CA._PUSH_GRADING.update(at=0.0, v=(False, ""))

    def test_the_stand_aside_judge_yields_to_a_push_and_only_to_a_push(self):
        self._pushing(False)
        self.assertFalse(CA._sp_yield_here(), "no push, no game, no sweep - and the proof was told to yield")
        self._pushing(True)
        self.assertTrue(CA._sp_yield_here(), "a push grading on this PC and the running proof was not told to yield")

    def test_a_list_that_cannot_be_read_never_freezes_the_proof(self):
        SP.process_rows = lambda run=None: None
        CA._PUSH_GRADING.update(at=0.0, v=(False, ""))
        self.assertFalse(CA._sp_yield_here())

    def test_the_guard_and_the_tick_name_the_push(self):
        self._pushing(True)
        SP.guard = lambda **kw: {"key": "aside-cooldown", "say": "stood aside"}
        r = CA._self_prove_guard()
        self.assertEqual(r.get("standAside"), CA.PUSH_STAND_ASIDE, "the guard stood aside and did not say for what")
        SP.tick = lambda **kw: {"key": "aside-cooldown", "say": "stood aside"}
        r = CA._self_prove_tick()
        self.assertEqual(r.get("standAside"), CA.PUSH_STAND_ASIDE, "the tick stood aside and did not say for what")


RED_PROOF = [
    {"why": "v3861 - a law inside the pre-push yields to the push that is running it (an idle fixture reads busy)",
     "file": "tv/self_prove.py",
     "find": "            if pid in mine:\n                continue                       # the push that is running THIS process (a law inside the gate)\n",
     "replace": "",
     "matches": 1},
    {"why": "v3861 - a running proof no longer yields to a push grading on this PC: it runs the same suites beside the gate",
     "file": "tv/control_app.py",
     "find": "    if _a_push_is_grading():        # v3861 - a push grading on this PC goes first; the proof waits for it\n"
             "        _sp_yield_here.why = PUSH_STAND_ASIDE\n"
             "        return True\n",   # v3883 re-anchor (REG-3423: the judge carries its reason)
     "replace": "",
     "matches": 1},
    {"why": "v3861 - the prover's own law running the hook in a fixture reads as a push: the proof ends itself every slice",
     "file": "tv/self_prove.py",
     "find": "                if mark in cmd_of.get(p, \"\").split():\n                    ours = True\n",
     "replace": "                if False:\n                    ours = True\n",
     "matches": 1},
    {"why": "v3861 - a ci/ push over in seconds costs the proof its half-hour cooldown",
     "file": "tv/self_prove.py",
     "find": "            if age is not None and age < after_s:\n                continue\n",
     "replace": "",
     "matches": 1},
    {"why": "v3861 - a process list nobody read is called a push",
     "file": "tv/self_prove.py",
     "find": "    if rows is None:\n        return None, \"the process list could not be read\"\n",
     "replace": "    if rows is None:\n        return True, \"the process list could not be read\"\n",
     "matches": 1},
    {"why": "v3861 - the guard stands aside for a push and the card does not say why",
     "file": "tv/control_app.py",
     "find": "            if _a_push_is_grading() and not _sp_proof_playing_here():\n"
             "                r = dict(r, standAside=PUSH_STAND_ASIDE)\n",
     "replace": "",
     "matches": 1},
    {"why": "v3896 (REG-3678) - a running ship is not seen, so the console's proof grades beside the ship's own gates",
     "file": "tv/self_prove.py",
     "find": "            ship = _tb._is_ship_command(cmd)\n",
     "replace": "            ship = False\n",
     "matches": 1}
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
