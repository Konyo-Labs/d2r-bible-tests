# -*- coding: utf-8 -*-
"""REG-3330 (#98 - the v3876 pre-live Grok batch at 901 wide: "MAIN, BOSSES, CALCULATOR, TZ ZONES, TZ TRACKER and RUNES are
cut through horizontally"; GrokBot at 1024x720: "nav plus banner take about the top half") - THE NAV STICKS BELOW THE
CLAIM BAR, NEVER UNDER IT.

The claim bar (a first-time visitor's "This browser has its own empty world") and the sticky .header that carries the tabs
were BOTH sticky at top:0, the bar above (z 9997); at narrow widths the bar's sentence and button wrap, so it grows and
covers more of the nav. The header now sticks at the bar's height, read from v1800's --claim-h (the bar + the popovers'
8px gap, 0 with no bar), and the inbox panel that pins under the header moves down with it.

REG-3335 - THE FIRST CUT PUT `top` ON .tabs. Outside the console .tabs is position:relative (the v159 sheen rule outranks
the old sticky one), so `top` became a relative offset and pushed the whole nav 88-120px down onto the search bar at every
width (measured on a render: tabs at 273 against main's 185 at 1440, unscrolled). It also brought back a second height
variable (--claim-bar-h) that v2059 had already removed as a weaker duplicate of --claim-h. Held here: the header carries
the offset; no plain-.tabs rule sets a non-zero top; one variable. Pixels at 901/1024/1440/375, plain and ?app=1, are the
v3877 render batch (scrolled: header top == bar bottom at every width). RED_PROOF below.
"""
import io
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEADER_RULE = "  .header { top: max(0px, calc(var(--claim-h, 0px) - 8px)); }"
INBOX_RULE = "  .inbox-sticky.has { top: calc(var(--hdr-h,282px) + max(8px, var(--claim-h,0px))); }"
TALL = "@media (min-height: 481px) {"


class TheTabsStickBelowTheClaimBar(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8") as fh:
            cls.src = fh.read()

    def _tall_block(self):
        a = self.src.index(TALL)
        return self.src[a:self.src.index("\n}\n", a)]

    def test_the_sticky_header_sits_below_the_bar(self):
        self.assertIn(HEADER_RULE, self._tall_block(), "the sticky header no longer clears the claim bar - the bar covers the nav")
        self.assertRegex(self.src, r"\.header\{position:sticky;top:0", "PREMISE: the header is no longer the sticky chrome")
        self.assertLess(self.src.index(".header{position:sticky;top:0"), self.src.index(HEADER_RULE),
                        "the override sits before the sticky rule it must outweigh")

    def test_the_bar_is_measured_once(self):
        i = self.src.index("var _claimSync = function(){")
        body = self.src[i:self.src.index("};", i)]
        self.assertIn("setProperty('--claim-h', h + 'px')", body, "PREMISE: the bar's measured height is not published")
        for use in ("setProperty('--claim-bar-h'", "var(--claim-bar-h"):   # v2059's own note still names it, as history
            self.assertNotIn(use, self.src, "a second variable for the claim bar's height is back (v2059 removed one)")

    def test_no_plain_tabs_rule_shifts_the_nav(self):
        """outside the console .tabs is position:relative, so any non-zero top on it moves the nav off its place"""
        bad, src, seen = [], self.src, 0
        # anchored on each ".tabs" (never a whole-page regex - [^{}]* over 8 MB backtracks quadratically): its rule's
        # selector runs back to the previous } { ; or comment end, its body forward to the next }
        for m in re.finditer(r"\.tabs\b", src):
            o = src.find("{", m.end())
            if o < 0 or "}" in src[m.end():o] or ";" in src[m.end():o]:
                continue
            a = max(src.rfind(c, 0, m.start()) for c in ("}", "{", ";", "*/")) + 1
            sels = [x.strip() for x in src[a:o].split(",")]
            if not any(re.fullmatch(r"(?:body(?:\.[\w-]+)*\s+)?\.tabs", x) for x in sels):
                continue
            seen += 1
            body = src[o + 1:src.find("}", o)]
            for top in re.findall(r"(?<![-\w])top\s*:\s*([^;!}]+)", body):
                if top.strip() not in ("0", "0px"):
                    bad.append("%s { top: %s }" % (src[a:o].strip()[-60:], top.strip()))
        self.assertGreaterEqual(seen, 5, "PREMISE: fewer than 5 rules on the tabs were read")
        self.assertEqual(bad, [], "a .tabs rule sets a top offset - on the relative tabs it pushes the nav down: %r" % bad)

    def test_the_inbox_pinned_under_the_header_moves_with_it(self):
        self.assertIn(INBOX_RULE, self._tall_block(), "the inbox panel pins under where the header WAS - the header now covers it")

    def test_a_short_screen_keeps_the_old_stack(self):
        """REG-3335b (v1800 on CI, 640x400 with the bar up): bar + header + inbox offset overran a 400 px window - the Tools
        map chip went under the header and the inbox's first answer under the dock. The offsets live only in a block for
        windows taller than REG-3092's short screen (480 px), and the base rules are main's."""
        self.assertIn(".inbox-sticky.has{top:calc(var(--hdr-h,282px) + 8px);", self.src, "the base inbox rule moved")
        outside = self.src.replace(self._tall_block(), "")
        self.assertNotIn("max(0px, calc(var(--claim-h, 0px) - 8px))", outside, "the header offset applies on a short screen")


RED_PROOF = [
    {"why": "REG-3335b - the offsets apply on a short screen too: at 640x400 the stack covers the Tools map chip (v1800)",
     "file": "bible.html",
     "find": "@media (min-height: 481px) {\n  /* REG-3335b",
     "replace": "@media (min-height: 1px) {\n  /* REG-3335b",
     "matches": 1},
    {"why": "REG-3330 - the sticky header sits under the claim bar again (901 wide: the nav cut through)",
     "file": "bible.html",
     "find": "  .header { top: max(0px, calc(var(--claim-h, 0px) - 8px)); }\n",
     "replace": "  .header { }\n",
     "matches": 1},
    {"why": "REG-3335 - the offset goes on the relative tabs again and pushes the nav onto the search bar",
     "file": "bible.html",
     "find": "  .header { top: max(0px, calc(var(--claim-h, 0px) - 8px)); }\n",
     "replace": "  .header { top: max(0px, calc(var(--claim-h, 0px) - 8px)); }\n.tabs, body.app-ctx .tabs { top: var(--claim-h, 0px); }\n",
     "matches": 1},
    {"why": "REG-3330 - the inbox panel pins under the header's old place",
     "file": "bible.html",
     "find": "  .inbox-sticky.has { top: calc(var(--hdr-h,282px) + max(8px, var(--claim-h,0px))); }\n",
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
