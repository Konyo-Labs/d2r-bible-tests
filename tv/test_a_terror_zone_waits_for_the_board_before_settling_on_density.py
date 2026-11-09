# -*- coding: utf-8 -*-
"""v3891 (#133, REG-3527) - A TERROR ZONE THAT COULD NOT ASK THE BOARD WAITS, THEN GRADES AGAIN.

REG-3495 (v3889) already grades a zone by his missing items (`tzZoneGrade` on #tvd-eng) and leaves
the density grade with "your grail could not be asked, so this grade is density only" when the
board cannot be asked - UNKNOWN about his items, never a guess. MEASURED: `_tzFetch` paints as soon
as `/api/tz` answers, and `#tvd-eng` loads the whole board (bible.html). The first paint almost
always beats that iframe, so the card settles on density and the next automatic fetch is 60-120 s
later (and only while Sessions is on screen).

Now `_tzPaint` remembers the rotation, notices when `#tvd-eng` has no `tzZoneGrade` yet, and waits
for it (the iframe's load, and a short poll) to grade that same rotation again. A board that never
answers still keeps the density grade and says so. RED_PROOF below.
"""
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

UI = os.path.join(HERE, "control_ui.html")


def _page():
    with io.open(UI, encoding="utf-8") as fh:
        return fh.read()


class ATerrorZoneWaitsForTheBoard(unittest.TestCase):

    def test_a_board_that_cannot_be_asked_still_keeps_density_and_says_so(self):
        src = _page()
        self.assertIn("try { g = W ? W.tzZoneGrade(k, TZ_BOSS[k] || '') : null; } catch (e) { g = null; }", src)
        self.assertIn("'your grail could not be asked, so this grade is density only'", src)
        self.assertIn("return (w && typeof w.tzZoneGrade === 'function') ? w : null;", src)

    def test_the_first_paint_waits_for_the_board_then_grades_the_same_rotation(self):
        src = _page()
        self.assertIn("_tzNeedBoard = !_tzBoardW();", src,
                      "the first paint no longer notices that the board was not there")
        self.assertIn("if (_tzNeedBoard) _tzWaitForBoard();", src,
                      "a density-only first paint never waits for the board")
        self.assertGreaterEqual(src.count("_tzPaint(_tzLastD)"), 2,
                                "waiting never grades the last rotation again")
        self.assertIn("else if (tries >= 40) _tzStopWait();", src,
                      "a board that never answers is polled forever")
        self.assertIn("f.addEventListener('load'", src)


RED_PROOF = [
    {"why": "v3891 (#133, REG-3527) - a density-only first paint never waits for the board",
     "file": "tv/control_ui.html",
     "find": "    if (_tzNeedBoard) _tzWaitForBoard();\n",
     "replace": "",
     "matches": 1},
    {"why": "v3891 (#133, REG-3527) - waiting never grades the last rotation again",
     "file": "tv/control_ui.html",
     "find": "_tzPaint(_tzLastD)",
     "replace": "_tzPaint(null)",
     "matches": 2},
]


if __name__ == "__main__":
    unittest.main()
