#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v3900 (REG-3739, #217) - A LOSS THE HUNT DOCUMENTED CLOSES OUT AS DOCUMENTATION; EVERY OTHER UNRECORDED LOSS STAYS RED.

MEASURED on his Mac 11-11: 34 reels left the shelf with no deleter's record, 29 of them on 10-24 between 10:08 and 21:22. The
hunt ruled out the recorder's disk floor, the retention ledger and git; the hand is still unnamed. river-log-matches-the-shelf
(corroborate.py) stood red over those 34 for 18 days and will stand red forever - and a row that is always red is the row
that hides the NEXT real loss. A reel can now be documented after the fact (river_stamp.document / --document): it closes
out with words that say "NOT a deleter's record - documented after the fact by ... : ...", and only a reel that is truly gone
AND unrecorded can be documented. Every reel nobody documented stays red.

DRIVEN: the real stamp store, close_out and document over a fixture shelf. RED_PROOF below.
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

import river_stamp as RS  # noqa: E402
import reel_forensics as RF  # noqa: E402

GONE = "reel_s_1500000000000_00001"
HERE_STILL = "reel_s_1500000100000_00002"


class ADocumentedLossClosesOutAsDocumented(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="forensics_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.hist = os.path.join(self.tmp, "w", "hist")
        os.makedirs(os.path.join(self.hist, HERE_STILL))
        self.store = os.path.join(self.tmp, "river_stamp.jsonl")
        for reel in (GONE, HERE_STILL):
            RS.stamp(reel, "ROUTED", "fixture", why="fixture", path=self.store)

    def test_baseline_a_gone_unrecorded_reel_is_red(self):
        out = RS.close_out("fixture", self.hist, path=self.store, dry=True)
        self.assertTrue(out["ok"], out)
        self.assertEqual(out["unrecorded"], [GONE])

    def test_a_documented_loss_closes_out_saying_it_is_documentation(self):
        """* THE POINT"""
        d = RF.document([GONE], "left the shelf 10-24 10:08-21:22 with no deleter's record (#217 hunt)", "claude", self.hist)
        self.assertEqual(d["documented"], [GONE], d)
        out = RS.close_out("fixture", self.hist, path=self.store, dry=True)
        self.assertEqual(out["unrecorded"], [], "a documented loss still reads as a deletion nobody logged: %r" % out)
        self.assertEqual(out["wouldClose"], [GONE])
        recs, _unread = RS._deleter_records(self.hist)
        self.assertTrue(recs[GONE].startswith("NOT a deleter's record - documented after the fact by claude"), recs[GONE])

    def test_only_a_truly_unrecorded_loss_can_be_documented(self):
        d = RF.document([HERE_STILL, "not_a_reel"], "anything", "claude", self.hist)
        self.assertEqual(d["documented"], [], d)
        self.assertEqual(sorted(x["why"].split(" -")[0] for x in d["refused"]), ["not a reel name", "still on the shelf"])
        self.assertFalse(RF.document([GONE], "", "claude", self.hist)["ok"], "a loss was documented with no reason")
        self.assertFalse(os.path.exists(RF.forensics_path(self.hist)), "a refusal still wrote the forensic record")

    def test_the_record_lives_beside_the_closure_ledger_and_is_never_committed(self):
        import reel_retention as RR
        self.assertEqual(os.path.dirname(RF.forensics_path(self.hist)), os.path.dirname(RR._tombstone_path(self.hist)))
        with io.open(os.path.join(os.path.dirname(HERE), ".gitignore"), encoding="utf-8") as fh:
            self.assertIn("tv/reel_forensics.json", fh.read().split("\n"), "his reel names could be committed to a public repo")


RED_PROOF = [
    {"why": "REG-3739 - the river check stops reading the forensic record, so a documented loss stands red forever again",
     "file": "tv/river_stamp.py",
     "find": "                if isinstance(t, dict) and t.get(\"reel\") and str(t[\"reel\"]) not in recs:\n",
     "replace": "                if False:\n",
     "matches": 1},
    {"why": "REG-3739 - a reel still on the shelf can be documented as lost",
     "file": "tv/reel_forensics.py",
     "find": "        elif os.path.isdir(os.path.join(hist, reel)):\n",
     "replace": "        elif False:\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
