# -*- coding: utf-8 -*-
"""v3895 (#29, REG-3589) - THE GEAR ADVISOR CLOSES A BREAKPOINT GAP.

It reads a gap {stat, now, next, need} from the stats engine and searches a
catalogue of items and charms. An item that does not reach the need is not
suggested. The closest overshoot wins. An unreadable gap is UNKNOWN.
RED_PROOF below.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _enable  # noqa: E402
_enable()

import gear_advisor as GA  # noqa: E402

CAT = [
    {"name": "Spirit", "kind": "item", "stats": {"fcr": 35}},
    {"name": "FCR grand charm", "kind": "charm", "stats": {"fcr": 7}},
    {"name": "Shako", "kind": "item", "stats": {"mf": 50}},
]


class TheGearAdvisorClosesABreakpointGap(unittest.TestCase):

    def test_it_suggests_what_closes_the_gap(self):
        gap = {"stat": "fcr", "now": 63, "next": 75, "need": 12}
        got = GA.suggest(gap, CAT)
        self.assertEqual([g["name"] for g in got], ["Spirit"])
        self.assertEqual(got[0]["gives"], 35)
        self.assertEqual(got[0]["overshoot"], 23)
        self.assertEqual(got[0]["kind"], "item")

    def test_a_charm_that_reaches_is_suggested(self):
        gap = {"stat": "fcr", "now": 70, "next": 75, "need": 5}
        got = GA.suggest(gap, CAT)
        self.assertEqual([g["name"] for g in got], ["FCR grand charm", "Spirit"])
        self.assertEqual(got[0]["overshoot"], 2)

    def test_nothing_that_fits_is_a_measured_none(self):
        self.assertEqual(GA.suggest({"stat": "fhr", "need": 10}, CAT), [])

    def test_an_unreadable_gap_is_unknown(self):
        self.assertIsNone(GA.suggest(None, CAT))
        self.assertIsNone(GA.suggest({"stat": "fcr"}, CAT))
        self.assertIsNone(GA.suggest({"need": 10}, CAT))


RED_PROOF = [
    {"why": "v3895 (#29, REG-3589) - an item short of the need is suggested anyway",
     "file": "tv/gear_advisor.py",
     "find": "        if gives < need_n:\n            continue\n",
     "replace": "        if False and gives < need_n:\n            continue\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
