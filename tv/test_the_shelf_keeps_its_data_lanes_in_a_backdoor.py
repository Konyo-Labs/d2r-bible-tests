# -*- coding: utf-8 -*-
"""v3898 (card #214, his 11-11 design brief via GrokBot #230 6795098365) - THE SHELF KEEPS ITS DATA LANES IN A BACKDOOR.

His rule: "if it is not for him to act on and it is just data, it stays off the main view". The shelf's river strip (the
four lanes, the FRESH ... UNKNOWN chips, the intake / printer / tombstone line, the triage lane - #sh-lanes) and its
pipeline board (#sh-story) move into ONE collapsed drawer at the foot of the shelf, in the Vault backdoor's format
(bible.html's "⚙ Advanced · Vault backdoor"). This supersedes v2985's "nothing collapsed behind a click" by his newer word.

Held without a browser (the pixels are the render check's): the drawer wraps exactly those two blocks, starts closed,
keeps its open state across the shelf's repaints for the page's life only, keeps both ids (their loaders find them by id),
and still sits below the reel list. RED_PROOF below. [[visual-regression-detector]]
"""
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import js_strip  # noqa: E402  (one comment stripper for the laws)

OPEN = "'<details class=\"sh-backdoor\" id=\"sh-backdoor\"' + (window._shBackdoorOpen ? ' open' : '')"
LANES = "'<div class=\"sh-lanes\" id=\"sh-lanes\">"
STORY = "'<div class=\"sh-story\" id=\"sh-story\">"
CLOSE = "+ '</details>';"


def _code():
    with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
        return js_strip.strip_js_comments(fh.read())


class TheShelfKeepsItsDataLanesInABackdoor(unittest.TestCase):

    def setUp(self):
        self.code = _code()
        self.assertEqual(self.code.count(OPEN), 1, "PREMISE: the shelf backdoor is gone or doubled")
        self.i = self.code.index(OPEN)

    def test_the_drawer_holds_the_lanes_and_the_pipeline(self):
        """* THE POINT - both data blocks are inside the drawer, nothing else is"""
        j = self.code.index(CLOSE, self.i)
        inside = self.code[self.i:j]
        self.assertIn(LANES, inside, "the river strip is back on the shelf's main view")
        self.assertIn(STORY, inside, "the pipeline board is back on the shelf's main view")
        self.assertNotIn("_shHighlights()", inside, "the highlights moved into the backdoor - they are his to read")
        self.assertNotIn("timelineDiv", inside, "the ACTIVITY chart moved into the backdoor")
        self.assertEqual(self.code.count(LANES), 1, "a second river strip sits outside the drawer")
        self.assertEqual(self.code.count(STORY), 1, "a second pipeline board sits outside the drawer")

    def test_it_starts_closed_and_remembers_only_this_page(self):
        tail = self.code[self.i:self.i + 400]
        self.assertIn("' ontoggle=\"window._shBackdoorOpen=this.open\">'", tail,
                      "an opened backdoor snaps shut on the shelf's next repaint")
        self.assertNotIn("localStorage", tail, "the backdoor's open state outlives the page - his default is collapsed")
        self.assertNotIn("<details class=\"sh-backdoor\" id=\"sh-backdoor\" open", self.code, "the backdoor opens by default")

    def test_it_sits_below_the_reel_list(self):
        """the reels come first (v2985/v3289's measured rule): the drawer is after the cards in the assembly"""
        k = self.code.rfind("searchBar + body", 0, self.i)
        self.assertGreater(k, -1, "PREMISE: the reel list is no longer assembled before the backdoor")
        self.assertLess(self.i - k, 600, "the backdoor no longer follows the reel list closely - something moved between them")

    def test_its_look_is_the_vault_backdoors(self):
        self.assertIn("\\u2699 Advanced \\u00b7 Shelf backdoor", self.code, "the drawer is not named like the Vault backdoor")
        self.assertIn("#th-shelfov .sh-backdoor > summary { cursor: pointer; list-style: none;", self.code,
                      "the drawer lost the Vault backdoor's summary row")


RED_PROOF = [
    {"why": "v3898 (#214) - the river strip and pipeline board are back on the shelf's main view (no drawer)",
     "file": "tv/control_ui.html",
     "find": "      + '<div class=\"sh-story\" id=\"sh-story\"><div class=\"shs-wait\">reading the pipeline…</div></div>'\n"
             "      + '</details>';\n",
     "replace": "      + '</details>'\n"
                "      + '<div class=\"sh-story\" id=\"sh-story\"><div class=\"shs-wait\">reading the pipeline…</div></div>';\n",
     "matches": 1},
    {"why": "v3898 (#214) - an opened backdoor snaps shut on the shelf's next repaint",
     "file": "tv/control_ui.html",
     "find": "      + ' ontoggle=\"window._shBackdoorOpen=this.open\">'\n",
     "replace": "      + '>'\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
