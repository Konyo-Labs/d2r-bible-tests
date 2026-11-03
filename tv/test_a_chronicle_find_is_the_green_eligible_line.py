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
                R(2000, "inventory", ["The Stone of Jordan", "Eligible for Chronicle"], lineColors=["gold", "green"]),
                R(3000, "ground", ["Tyrael's Might", "Eligible for Chronicle"], lineColors=["gold", "green"])]
        self.assertEqual([], sr.route(rows)["chronicle"],
                         "a traded item, or one left on the floor, counted as this run's chronicle find")

    def test_a_journal_row_with_no_line_colours_is_unknown_never_zero(self):
        """v3859 B2 (#230): the real journal shape - ocr_raw, no raw_lines, no lineColors (nothing writes them). The plain
        text cannot say green, so the session's chronicle count is UNKNOWN, never a measured 0."""
        import session_route as sr
        rows = [{"ts": 1000, "captureTs": 1000, "scene": "ground", "ocr_raw": ["Harlequin Crest", "Shako"]},
                {"ts": 2000, "captureTs": 2000, "scene": "inventory",
                 "ocr_raw": ["Harlequin Crest", "Shako", "Eligible for Chronicle"]}]
        r = sr.route(rows)
        self.assertEqual(r["itemsFarmed"], 2, "PREMISE: the ocr_raw lines were not read at all: %r" % r)
        self.assertIsNone(r["chronicle"], "plain OCR text was called a measured chronicle count: %r" % r["chronicle"])


RED_PROOF = [
    {"why": "v3859 B2 - a session no colour reader spoke for says 0 chronicles, not UNKNOWN",
     "file": "tv/session_route.py",
     "find": "            \"chronicle\": [it.name for it in items if it.farmed and it.chron] if colours_read(rows) else None,\n",
     "replace": "            \"chronicle\": [it.name for it in items if it.farmed and it.chron],\n",
     "matches": 1},
    {"why": "v3859 B2 - the route reads raw_lines only, never the journal's ocr_raw",
     "file": "tv/session_route.py",
     "find": "r.get(\"raw_lines\") or r.get(\"ocr_raw\") or r.get(\"names\")",
     "replace": "r.get(\"raw_lines\") or r.get(\"names\")",
     "matches": 1},
    {"why": "the line's colour is ignored",
     "file": "tv/session_route.py",
     "find": "            if c == \"green\":\n",
     "replace": "            if True:\n",
     "matches": 1},
    {"why": "every farmed unique is a chronicle find, line or not",
     "file": "tv/session_route.py",
     "find": "            if elig and h[1] != \"bases\":\n",
     "replace": "            if h[1] != \"bases\":\n",
     "matches": 1},
    {"why": "an item never farmed this run counts",
     "file": "tv/session_route.py",
     "find": "            \"chronicle\": [it.name for it in items if it.farmed and it.chron] if colours_read(rows) else None,\n",
     "replace": "            \"chronicle\": [it.name for it in items if it.chron] if colours_read(rows) else None,\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
