# -*- coding: utf-8 -*-
"""v3893 (REG-3561) - CORNER TEXT IS CHECKED AGAINST THE FIVE TOWNS.

The overlay already writes the zone name (area from the top-right Game block /
ENTERING banner / automap). That string is checked against the five act towns.
A known town names its act; any other written area is the field; empty is unknown.
An act that disagrees with the town is a conflict. No pixel town template is
invented (this tree has no act-1-5 town frames).
RED_PROOF below.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import read_identity as RI  # noqa: E402
import d2r_screens as DS  # noqa: E402


class CornerTextIsCheckedAgainstTheTown(unittest.TestCase):

    def test_a_town_names_its_act_and_a_field_does_not(self):
        self.assertEqual(RI.corner_vs_town("Rogue Encampment")["act"], 1)
        self.assertEqual(RI.corner_vs_town("The Rogue Encampment")["town"], "Rogue Encampment")
        self.assertEqual(RI.corner_vs_town("Lut Gholein")["act"], 2)
        self.assertEqual(RI.corner_vs_town("Kurast Docks")["act"], 3)
        self.assertEqual(RI.corner_vs_town("Pandemonium Fortress")["act"], 4)
        self.assertEqual(RI.corner_vs_town("Harrogath")["act"], 5)
        field = RI.corner_vs_town("The Pit")
        self.assertEqual(field["kind"], "field")
        self.assertIsNone(field["town"])
        self.assertEqual(RI.corner_vs_town("")["kind"], "unknown")

    def test_difficulty_and_a_disagreeing_act(self):
        hell = RI.corner_vs_town("Hell Rogue Encampment")
        self.assertEqual(hell["kind"], "town")
        self.assertEqual(hell["difficulty"], "Hell")
        self.assertTrue(hell["agree"])
        self.assertFalse(RI.corner_vs_town("Rogue Encampment", act=2)["agree"])
        self.assertTrue(RI.corner_vs_town("Rogue Encampment", act=1)["agree"])

    def test_no_town_pixel_template_was_invented(self):
        self.assertIn("no act-1–5 town templates", DS.SCENARIO_EVIDENCE["town"])


RED_PROOF = [
    {"why": "v3893 (REG-3561) - a known town is no longer recognized from the already-read area",
     "file": "tv/read_identity.py",
     "find": "    hit = _TOWN_ACT.get(key)\n",
     "replace": "    hit = None\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
