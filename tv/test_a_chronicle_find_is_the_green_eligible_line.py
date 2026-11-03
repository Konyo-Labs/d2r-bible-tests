# -*- coding: utf-8 -*-
"""v3859 (#230): a session's chronicle finds are only the items whose own tooltip carried the green
"Eligible for Chronicle" line (tv/session_route.py chronicle_eligible). A chronicle panel read, the same words in
another colour, or an item never farmed on this run is not a chronicle find.

RED_PROOF below: each one, applied, turns this law red."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable; enable()


def R(t, scene, lines, **kw):
    d = {"ts": t, "captureTs": t, "scene": scene, "raw_lines": lines, "names": lines}
    d.update(kw)
    return d


class TheChronicleLine(unittest.TestCase):

    def test_the_green_line_on_the_items_tooltip_counts(self):
        import session_route as sr
        rows = [R(1000, "ground", ["Shako", "Unidentified"]), R(2000, "inventory", ["Shako", "Unidentified"]),
                R(3000, "inventory", ["Harlequin Crest", "Shako", "Eligible for Chronicle"],
                  lineColors=["gold", "gold", "green"])]
        r = sr.route(rows)
        print("chronicle: %s" % r["chronicle"])
        self.assertEqual(["Harlequin Crest"], r["chronicle"])

    def test_a_chronicle_panel_or_a_non_green_line_does_not(self):
        import session_route as sr
        rows = [R(1000, "inventory", ["The Stone of Jordan", "Eligible for Chronicle"], lineColors=["gold", "white"]),
                R(2000, "chronicle", ["Tyrael's Might"]),
                R(3000, "inventory", ["Ber Rune"])]
        r = sr.route(rows)
        self.assertEqual([], r["chronicle"], "a white line or a chronicle panel read was called a chronicle find")

    def test_an_item_not_farmed_this_run_is_not_a_find(self):
        import session_route as sr
        rows = [R(1000, "trade", ["The Stone of Jordan", "Eligible for Chronicle"]),
                R(2000, "inventory", ["The Stone of Jordan", "Eligible for Chronicle"]),
                R(3000, "ground", ["Tyrael's Might", "Eligible for Chronicle"])]
        self.assertEqual([], sr.route(rows)["chronicle"],
                         "a traded item, or one left on the floor, counted as this run's chronicle find")


RED_PROOF = [
    {"why": "the line's colour is ignored",
     "file": "tv/session_route.py",
     "find": "                if c != \"green\":\n",
     "replace": "                if False:\n",
     "matches": 1},
    {"why": "every farmed unique is a chronicle find, line or not",
     "file": "tv/session_route.py",
     "find": "            if elig and h[1] != \"bases\":\n",
     "replace": "            if h[1] != \"bases\":\n",
     "matches": 1},
    {"why": "an item never farmed this run counts",
     "file": "tv/session_route.py",
     "find": "            \"chronicle\": [it.name for it in items if it.farmed and it.chron],\n",
     "replace": "            \"chronicle\": [it.name for it in items if it.chron],\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
