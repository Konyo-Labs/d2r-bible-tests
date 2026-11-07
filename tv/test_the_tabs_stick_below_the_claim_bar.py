# -*- coding: utf-8 -*-
"""REG-3330 (#98 - the v3876 pre-live Grok batch at 901 wide: "MAIN, BOSSES, CALCULATOR, TZ ZONES, TZ TRACKER and RUNES are
cut through horizontally"; GrokBot at 1024x720: "nav plus banner take about the top half") - THE STICKY TABS SIT BELOW THE
CLAIM BAR, NEVER UNDER IT.

The claim bar (a first-time visitor's "This browser has its own empty world") and the tabs were BOTH position:sticky at
top:0, the bar above them (z 9997); at narrow widths the bar's sentence and button wrap, so it grows and covers more of the
tabs. The bar's observer now publishes its own height (--claim-bar-h, 0 with no bar) and the tabs stick below it. Held on
the source (the pixels at 901/1024 are the render batch's): the observer sets --claim-bar-h from the bar's measured
height, and the tabs' sticky top reads it. RED_PROOF below.
"""
import io
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TheTabsStickBelowTheClaimBar(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8") as fh:
            cls.src = fh.read()

    def test_the_bar_publishes_its_own_height(self):
        i = self.src.index("var _claimSync = function(){")
        body = self.src[i:self.src.index("};", i)]
        self.assertIn("h0 = Math.ceil(r.height)", body, "the bar's own height is not measured")
        self.assertIn("setProperty('--claim-bar-h', Math.min(h0, 252) + 'px')", body, "the bar's height is not published")

    def test_the_tabs_stick_below_it(self):
        self.assertIn(".tabs, body.app-ctx .tabs { top: var(--claim-bar-h, 0px); }", self.src)
        # premise: the rules it overrides are the sticky ones at top:0, earlier in the page
        self.assertRegex(self.src, r"\.tabs\{position:sticky;top:0")
        self.assertLess(self.src.index(".tabs{position:sticky;top:0"), self.src.index(".tabs, body.app-ctx .tabs { top: var(--claim-bar-h"),
                        "the override sits before the rule it must outweigh")


RED_PROOF = [
    {"why": "REG-3330 - the sticky tabs sit under the claim bar again (901 wide: the nav cut through)",
     "file": "bible.html",
     "find": ".tabs, body.app-ctx .tabs { top: var(--claim-bar-h, 0px); }",
     "replace": ".tabs, body.app-ctx .tabs { }",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
