# -*- coding: utf-8 -*-
"""v3895 (#29, REG-3595) - THE GEAR ADVISOR SCORES AN UBER RUN APART FROM A REGULAR RUN.

The first slice listed every catalogue row that closed the gap. An UBER run
and a regular run want different items. A row tagged only for the other
scenario is skipped; a row with no tag still applies to both. An unreadable
scenario is UNKNOWN.
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
    {"name": "Spirit", "kind": "item", "stats": {"fcr": 35}, "scenarios": ("regular", "uber")},
    {"name": "FCR grand charm", "kind": "charm", "stats": {"fcr": 7}},
    {"name": "Treachery", "kind": "item", "stats": {"fcr": 45}, "scenarios": ("regular",)},
    {"name": "Call to Arms", "kind": "item", "stats": {"fcr": 40}, "scenarios": ("uber",)},
]
GAP = {"stat": "fcr", "now": 73, "next": 105, "need": 32}


class TheGearAdvisorScoresUberApartFromARegularRun(unittest.TestCase):

    def test_uber_skips_a_regular_only_item(self):
        got = GA.suggest(GAP, CAT, scenario="uber")
        self.assertEqual([g["name"] for g in got], ["Spirit", "Call to Arms"])

    def test_regular_skips_an_uber_only_item(self):
        got = GA.suggest(GAP, CAT, scenario="regular")
        self.assertEqual([g["name"] for g in got], ["Spirit", "Treachery"])

    def test_no_scenario_still_lists_every_closer(self):
        got = GA.suggest(GAP, CAT)
        self.assertEqual([g["name"] for g in got], ["Spirit", "Call to Arms", "Treachery"])

    def test_an_unreadable_scenario_is_unknown(self):
        self.assertIsNone(GA.suggest(GAP, CAT, scenario="nightmare"))
        self.assertIsNone(GA.suggest(GAP, CAT, scenario=""))


RED_PROOF = [
    {"why": "v3895 (#29, REG-3595) - an UBER ask no longer skips a regular-only item",
     "file": "tv/gear_advisor.py",
     "find": "            if scenario is not None and scenario not in sc:\n                continue\n",
     "replace": "            if False and scenario is not None and scenario not in sc:\n                continue\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
