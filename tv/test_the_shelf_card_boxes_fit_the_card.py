# -*- coding: utf-8 -*-
"""v3898 (#184's four boxes) - THE SHELF CARD'S FOUR BOXES FIT INSIDE THE CARD.

MEASURED 11-11 on a scratch console, in his own font (SF Mono): `.shc-stats` was `repeat(4, 1fr)`. A bare 1fr track keeps
its min-content, so CHRONICLES held its column at ~98 px and the row needed 290 px in a 237 px card at 1440 (267 in 226 at
1120) - the SETS box sat 39 px past the card's edge and was cut off. The label floor (--fs-2xs, 13 px and up) cannot shrink
four across into a card (~260 px at best), so a Shelf CARD lays the four boxes 2 x 2; the wide shadow row keeps four in a
row with tracks that may shrink. After: 237/237, 226/226, 241/241 (scrollWidth/clientWidth), the Grok CLI's cold look saw
a 2 x 2 grid, nothing cut off, at both widths. The geometry depends on font metrics, so this law reads the stylesheet's
TRACKS (deterministic on every machine) - the visual-regression skill's ④b rule. RED_PROOF below.
"""
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()


def _css():
    with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
        src = fh.read()
    return re.sub(r"/\*.{0,4000}?\*/", "", src, flags=re.S)   # bounded: a stray /* never eats the file


def _rule(css, sel):
    hits = re.findall(r"(?m)^\s*" + re.escape(sel) + r"\s*\{([^}]*)\}", css)
    return hits


class TheShelfCardBoxesFitTheCard(unittest.TestCase):

    def test_no_bare_fr_track_on_the_four_box_row(self):
        css = _css()
        rules = _rule(css, ".shc-stats") + _rule(css, ".sh-card .shc-stats")
        self.assertTrue(rules, "PREMISE: the four-box row's rules are gone")
        for body in rules:
            m = re.search(r"grid-template-columns\s*:\s*([^;]+);", body)
            if not m:
                continue
            tracks = m.group(1)
            self.assertNotRegex(tracks, r"repeat\(\s*\d+\s*,\s*1fr\s*\)",
                                "a bare 1fr track keeps its min-content: CHRONICLES pushes SETS past the card (%s)" % tracks)

    def test_a_card_lays_the_four_boxes_two_by_two(self):
        """* THE POINT - four across cannot fit a card at the label floor; 2 x 2 always does"""
        bodies = _rule(_css(), ".sh-card .shc-stats")
        self.assertEqual(len(bodies), 1, "the card's own four-box rule is gone or doubled: %r" % bodies)
        self.assertIn("grid-template-columns: repeat(2, minmax(0, 1fr))", bodies[0])


RED_PROOF = [
    {"why": "v3898 (#184) - the card's four boxes go four across again and SETS is cut off at the card's edge",
     "file": "tv/control_ui.html",
     "find": "  .sh-card .shc-stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }\n",
     "replace": "",
     "matches": 1},
    {"why": "v3898 (#184) - a bare 1fr track again (min-content blows the row out)",
     "file": "tv/control_ui.html",
     "find": "  .shc-stats { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 6px; margin: 1px 0 2px; }\n",
     "replace": "  .shc-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin: 1px 0 2px; }\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
