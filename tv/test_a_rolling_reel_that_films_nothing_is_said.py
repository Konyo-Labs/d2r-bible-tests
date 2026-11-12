# -*- coding: utf-8 -*-
"""v3901 (REG-3761, #188) - A ROLLING REEL THAT FILMS NOTHING IS A DOCTOR ROW.

Dean 11-08 (his frozen logs, off the repo): two reels opened, their AI reads ran (Catacombs at 17:22), and their first
footage frame landed 34 and 31 minutes in. Nothing on any surface said so while it happened. REG-3753 made the recorder
keep why each footage frame was refused; it now publishes the pause running NOW in its health (`footagePause`: kind, words,
since, count) and this reel's tally (`footageRefused`), and the doctor's "rolling reel filmed" row reads them through the
console's status: MISSING once a pause has lasted FOOTAGE_PAUSE_ROW_S while the recorder reports, in the gate's own words.
No recorder reporting, or a build that publishes no pause, is UNMEASURED - never a pass.

DRIVEN: console_doctor._check_the_rolling_reel_is_filmed over stubbed /api/status answers; tv_diablo.footage_pause_now over
its own pause record; the health dict's two fields by its own source. RED_PROOF below.
"""
import io
import os
import sys
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

import console_doctor as cd  # noqa: E402


def _status(pause, fresh=True, phase="live", tally=None, has=True):
    h = {"footageRefused": tally or {}}
    if has:
        h["footagePause"] = pause
    return {"stateFresh": fresh, "phase": phase, "health": h}


class ARollingReelThatFilmsNothingIsSaid(unittest.TestCase):

    def _row(self, st):
        with mock.patch.object(cd, "_get", lambda *a, **k: st):
            return cd._check_the_rolling_reel_is_filmed()

    def test_a_long_pause_while_rolling_is_missing_in_its_own_words(self):
        """* THE POINT - Dean 11-08: 34 minutes of a rolling reel with no footage and no word anywhere"""
        p = {"kind": "source-stale", "say": "the capture file is older than 5 s", "sinceMs": int((time.time() - 34 * 60) * 1000),
             "n": 2040}
        state, why = self._row(_status(p, tally={"source-stale": 2040, "warming-up": 3}))
        self.assertEqual(state, cd.MISSING)
        self.assertIn("filmed NOTHING for 34 min", why)
        self.assertIn("the capture file is older than 5 s", why)
        self.assertIn("source-stale 2040", why)

    def test_baseline_landing_and_a_short_pause_are_ok(self):
        self.assertEqual(self._row(_status(None))[0], cd.OK)
        p = {"kind": "warming-up", "say": "warming up", "sinceMs": int((time.time() - 60) * 1000), "n": 4}
        self.assertEqual(self._row(_status(p))[0], cd.OK, "a one-minute pause was raised as a row")

    def test_no_recorder_reporting_or_an_older_build_is_unmeasured(self):
        p = {"kind": "disk-floor", "say": "x", "sinceMs": int((time.time() - 3600) * 1000), "n": 9}
        self.assertEqual(self._row(_status(p, fresh=False))[0], cd.UNMEASURED, "a stale recorder state was judged")
        self.assertEqual(self._row(_status(p, phase="off"))[0], cd.UNMEASURED)
        self.assertEqual(self._row(_status(None, has=False))[0], cd.UNMEASURED, "an older build read as landing")
        self.assertEqual(self._row(None)[0], cd.UNKNOWN)

    def test_the_recorder_publishes_its_pause(self):
        import tv_diablo as T
        old = dict(T._FOOTAGE_PAUSE)
        self.addCleanup(lambda: T._FOOTAGE_PAUSE.update(old))
        T._FOOTAGE_PAUSE.update(since=None, kind=None, n=0)
        self.assertIsNone(T.footage_pause_now())
        T._FOOTAGE_PAUSE.update(since=1000.0, kind="disk-floor", n=7)
        self.assertEqual(T.footage_pause_now(), {"kind": "disk-floor", "say": T.FOOTAGE_REFUSAL_WORDS["disk-floor"],
                                                 "sinceMs": 1000000, "n": 7})
        with io.open(os.path.join(HERE, "tv_diablo.py"), encoding="utf-8") as fh:
            code = "\n".join(l.split("#", 1)[0].rstrip() for l in fh.read().split("\n"))
        self.assertEqual(code.count('         "footagePause": footage_pause_now(),\n'), 1,
                         "the recorder's health no longer carries the running pause")

    def test_the_row_is_registered_where_the_doctor_looks(self):
        self.assertIn("rolling reel filmed", dict(cd.CHECKS))
        self.assertIn("rolling reel filmed", cd.WATCHES)
        self.assertIn("rolling reel filmed", cd.MINE)


RED_PROOF = [
    {"why": "REG-3761 - a rolling reel that films nothing for half an hour reads OK again (Dean 11-08)",
     "file": "tv/console_doctor.py",
     "find": "    if age_s < FOOTAGE_PAUSE_ROW_S:\n",
     "replace": "    if True:\n",
     "matches": 1},
    {"why": "REG-3761 - a recorder that is not reporting now is judged on its stale pause",
     "file": "tv/console_doctor.py",
     "find": "    if st.get(\"stateFresh\") is not True or st.get(\"phase\") == \"off\":\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "REG-3761 - the recorder stops publishing its running pause",
     "file": "tv/tv_diablo.py",
     "find": "         \"footagePause\": footage_pause_now(),\n",
     "replace": "         \"footagePause\": None,\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
