# -*- coding: utf-8 -*-
"""v3883 (#129 item 5) - THE SAFETY NET RE-CHECKS A RED ON A QUIET PC, AND A RED THAT REPEATS ONLY UNDER LOAD IS NOT A FIND.

MEASURED 2026-11-06 23:38Z on his Mac: under my load, the safety net judged test_control RED; its immediate re-check
(REG-3324) ran under the same load and was RED again, so the find shut all nine locks - and 25 minutes later, quiet, the
same law ran 2,274 OK. A re-check that runs under the load that made the first red cannot tell a defect from the load.

Now heart2._net_red_holds waits - at most NET_QUIET_WAIT_S - for the 1-minute load per core to fall to NET_QUIET_LOAD
before it re-checks. A red that repeats on a PC that went quiet is the find it always was (his ruling 2026-11-05 (4): it
closes the locks its law guards). A red that repeats on a PC that stayed loaded through the whole wait is judged UNDER LOAD:
not a find - the gate stays trusted, closes nothing, and the net asks it again. Windows has no load average: UNKNOWN load
waits for nothing and the find stands, failing closed exactly as before. A green re-check is still a FLAKE.

The clock, the sleep and the load are the law's own; no gate runs, no census of his is read. RED_PROOF below.
[[unknown-stays-unknown]] [[regression-guard]]
"""
import os
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import heart2  # noqa: E402


class _Clock(object):
    """a fake clock whose load follows a script of (seconds, load per core) steps"""

    def __init__(self, script):
        self.t, self.script, self.slept = 0.0, list(script), 0

    def now(self):
        return self.t

    def sleep(self, s):
        self.t += s
        self.slept += 1

    def load(self):
        lv = None
        for at, v in self.script:
            if self.t >= at:
                lv = v
        return lv


class _NetFixture(unittest.TestCase):

    def setUp(self):
        self._runs = getattr(heart2._CLEAN, "runs", None)
        self._census = dict(heart2._CENSUS)
        self.addCleanup(self._restore)
        self.said, self.asked = [], []

    def _restore(self):
        heart2._CLEAN.runs = self._runs
        heart2._CENSUS.clear()
        heart2._CENSUS.update(self._census)

    def judge(self, clock, again_ok=False):
        def again():
            self.asked.append(clock.t)
            return again_ok, "FAIL: test_b (m.C)\n"
        heart2._CLEAN.runs = {"clean": {"ok": False, "tail": "FAIL: test_a (m.C)\n", "again": again}}
        real = heart2._wait_for_quiet
        with mock.patch.object(heart2, "_wait_for_quiet",
                               lambda: real(_load=clock.load, _sleep=clock.sleep, _now=clock.now)):
            return heart2._net_red_holds("test_control", self.said.append)


class ARedUnderLoadIsJudgedAgain(_NetFixture):

    def test_a_red_that_repeats_only_under_load_is_not_a_find(self):
        """* THE POINT - 11-06 23:38Z: loaded through the whole wait, red twice - judged UNDER LOAD, no lock closes"""
        c = _Clock([(0, 3.2)])
        self.assertFalse(self.judge(c), "a red that repeated under load was filed as the net's find")
        self.assertEqual(heart2._CENSUS.get("loadedRed", {}).get("test_control"), 3.2)
        self.assertGreaterEqual(c.t, heart2.NET_QUIET_WAIT_S, "PREMISE: it waited the whole bound for quiet")
        self.assertTrue(any("UNDER LOAD" in s for s in self.said), self.said)

    def test_premise_a_red_that_repeats_on_a_quiet_pc_is_the_find(self):
        self.assertTrue(self.judge(_Clock([(0, 0.2)])), "a red on a quiet PC no longer closes its locks")
        self.assertEqual(self.asked, [0.0], "a quiet PC waited before its re-check")

    def test_the_re_check_waits_for_quiet_when_quiet_comes(self):
        c = _Clock([(0, 2.5), (120, 0.3)])
        self.assertTrue(self.judge(c), "the red repeated on a PC that had gone quiet and was not the find")
        self.assertEqual(len(self.asked), 1)
        self.assertGreaterEqual(self.asked[0], 120, "the re-check ran before the PC went quiet")
        self.assertLess(self.asked[0], heart2.NET_QUIET_WAIT_S)

    def test_unknown_load_waits_for_nothing_and_fails_closed(self):
        c = _Clock([(0, None)])
        self.assertTrue(self.judge(c), "an UNKNOWN load (Windows) let a repeated red pass as 'under load'")
        self.assertEqual((c.slept, self.asked), (0, [0.0]))

    def test_a_green_re_check_is_still_a_flake(self):
        self.assertFalse(self.judge(_Clock([(0, 3.0)]), again_ok=True))
        self.assertIn("test_control", heart2._CENSUS.get("flakes", {}))
        self.assertNotIn("test_control", heart2._CENSUS.get("loadedRed", {}))


class TheLoadIsMeasuredNotGuessed(unittest.TestCase):

    def test_load_per_core(self):
        self.assertAlmostEqual(heart2._load_per_core(_getload=lambda: (8.0, 1, 1), _cpus=4), 2.0)
        self.assertIsNone(heart2._load_per_core(_getload=lambda: 1 / 0, _cpus=4), "an unreadable load read as a number")
        self.assertIsNone(heart2._load_per_core(_getload=lambda: (1.0, 1, 1), _cpus=0))

    def test_the_wait_is_bounded(self):
        c = _Clock([(0, 9.9)])
        heart2._wait_for_quiet(_load=c.load, _sleep=c.sleep, _now=c.now)
        self.assertLessEqual(c.t, heart2.NET_QUIET_WAIT_S + heart2.NET_QUIET_POLL_S, "the wait outran its bound")


RED_PROOF = [
    {"why": "v3883 - a red that repeats under load is the net's find again: one loaded re-check shuts every lock its law guards",
     "file": "tv/heart2.py",
     "find": "    if ok is not True and isinstance(_lv, (int, float)) and _lv > NET_QUIET_LOAD:\n",
     "replace": "    if False:\n", "matches": 1},
    {"why": "v3883 - the re-check no longer waits for a quiet PC: it runs under the load that made the first red",
     "file": "tv/heart2.py",
     "find": "        _lv = _wait_for_quiet()                       # v3883 - the re-check runs on a quiet PC when one comes in time\n",
     "replace": "        _lv = _load_per_core()\n", "matches": 1},
    {"why": "v3883 - the wait has no bound",
     "file": "tv/heart2.py",
     "find": "    while lv is not None and lv > NET_QUIET_LOAD and now() - t0 < NET_QUIET_WAIT_S:\n",
     "replace": "    while lv is not None and lv > NET_QUIET_LOAD and now() - t0 < NET_QUIET_WAIT_S * 1000:\n", "matches": 1},
    {"why": "v3883 - an unreadable load is read as zero (quiet)",
     "file": "tv/heart2.py",
     "find": "        return float((_getload or os.getloadavg)()[0]) / float(n)\n    except Exception:\n        return None\n",
     "replace": "        return float((_getload or os.getloadavg)()[0]) / float(n)\n    except Exception:\n        return 0.0\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
