# -*- coding: utf-8 -*-
"""v3888 (REG-3480) - A RECORDING BEING FILMED IS NOT FOOTAGE NO REEL HOLDS.

The hook on OLD PC ALT, 11-08 ~23:15: "footage has a reel - 48 frame(s) (0.00 GB) belong to NO reel - an unsealed recording no
sweep can reach". MEASURED there minutes later (read-only, `python tv/orphan_fold.py`): one cluster, REFUSED because "the newest
frame here is 1s old, inside the 180s gap that defines a cluster. This may be a recording STILL IN PROGRESS" - he was filming. A
session's frames are loose until its seal folds them into the reel, so the row read MISSING through every recording. It now takes
the rolling tail apart with the planner's own rule (orphan_fold.GAP_MS): the newest frame within the gap of now, and every frame
chained to it by gaps no longer than that. Only the rest is the died-before-seal footage the row exists for, and that stays red.

Drives the shipped check on a contained fixture hist (TV_HIST). RED_PROOF below. [[unknown-stays-unknown]] [[stale-reading]]
"""
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
import console_doctor as cd  # noqa: E402
import orphan_fold as of  # noqa: E402

NOW = 1_794_175_000_000


class ARollingRecordingIsNotOrphanedFootage(unittest.TestCase):

    def setUp(self):
        self.hist = tempfile.mkdtemp(prefix="rolling-law-")
        self._old = os.environ.get("TV_HIST")
        os.environ["TV_HIST"] = self.hist

    def tearDown(self):
        if self._old is None:
            os.environ.pop("TV_HIST", None)
        else:
            os.environ["TV_HIST"] = self._old
        shutil.rmtree(self.hist, ignore_errors=True)

    def _frames(self, stamps):
        for ms in stamps:
            with open(os.path.join(self.hist, "f_%d.jpg" % ms), "wb") as fh:
                fh.write(b"x" * 10)

    def test_premise_the_rule_is_the_planners(self):
        self.assertEqual(of.GAP_MS, 180000, "PREMISE: the planner's cluster gap moved - the cases below are built on 180 s")

    def test_the_session_being_filmed_reads_rolling_never_missing(self):
        """* THE POINT - OLD PC ALT: he was filming, the newest frame a second old"""
        self._frames([NOW - 1000 - 2000 * k for k in range(10)])
        state, why = cd._check_footage_belongs_to_a_reel(now_ms=NOW)
        self.assertEqual(state, cd.OK, why)
        self.assertIn("a recording is rolling: 10 frame(s)", why)

    def test_a_session_that_died_before_its_seal_is_still_missing(self):
        """the row's own reason to exist: a cluster that stopped ten minutes ago is footage no reel holds"""
        self._frames([NOW - 600000 - 2000 * k for k in range(4)])
        state, why = cd._check_footage_belongs_to_a_reel(now_ms=NOW)
        self.assertEqual(state, cd.MISSING, why)
        self.assertIn("4 frame(s)", why)

    def test_only_the_tail_chained_to_now_is_rolling(self):
        old = [NOW - 2 * 86400000 - 2000 * k for k in range(5)]
        live = [NOW - 1000, NOW - 3000]
        broken = [NOW - 3000 - 400000]           # a gap past the cluster rule: not the live session
        self._frames(old + live + broken)
        state, why = cd._check_footage_belongs_to_a_reel(now_ms=NOW)
        self.assertEqual(state, cd.MISSING, why)
        self.assertIn("6 frame(s)", why, "the old cluster and the broken-off frame are not both counted: %s" % why)
        self.assertIn("(2 more are the recording rolling now)", why)


RED_PROOF = [
    {"why": "v3888 (REG-3480) - the session being filmed reads as footage no reel holds again",
     "file": "tv/console_doctor.py",
     "find": "    if gap is not None and stamped and 0 <= now - stamped[-1][0] <= gap:\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "v3888 (REG-3480) - every loose frame chains to the live one, so a died-before-seal cluster hides behind it",
     "file": "tv/console_doctor.py",
     "find": "        while i > 0 and stamped[i][0] - stamped[i - 1][0] <= gap:\n",
     "replace": "        while i > 0:\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
