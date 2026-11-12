# -*- coding: utf-8 -*-
"""v3902 (REG-3769) - THE TERROR ZONE CARDS GO TWO-UP ONLY WHEN A CARD HOLDS ITS LINES.

GrokBot 11-12 05:30, his live console at his MacBook's 1512: the TZ cards cut their density line ("880 density ·…"). Swept
900-2600 in the render sandbox: the zone grid's 238px floor let a slot go two-up from 1480, at a 245px card whose text column is
137px, and every density line and verdict was cut ("650 density ·…", "→ 96 terroriz…") 1480-1860 and again 2080-2500 (three
across). MEASURED: the card's fixed parts are 108px (art 68 + padding 9 + 18 + gap 11 + border 2) and its widest line is the
verdict "→ 96 terrorized" at --fs-md: 211px at 23px, 15 mono characters at 0.61 em. The slot's zone grid now floors each track
at 108px + 9.2 x --fs-md. After: 0 of 5 lines cut at every width 900-2600; 1512 stacks like 1440; 1920 stays two-up.

DRIVEN: the shipped stylesheet, read as the law (the parts and the floor come from the same file, so a change to either is
checked against the other). The pixels were looked at by eye and by the Grok CLI. RED_PROOF below.
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

UI = os.path.join(HERE, "control_ui.html")
VERDICT = u"→ 96 terrorized"     # the widest line a card prints (the density line measured 202px against its 211px)
MONO_EM = 0.61                        # measured: 211px / 23px / 15 characters


def _css():
    s = io.open(UI, encoding="utf-8").read()
    return re.sub(r"/\*.*?\*/", "", s, flags=re.S)


def _one(css, pat, what):
    m = re.findall(pat, css)
    assert len(m) == 1, "%s: %d matches for %r" % (what, len(m), pat)
    return m[0]


class TzCardsGoTwoUpOnlyWhenTheirLinesFit(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        css = _css()
        cls.art = float(_one(css, r"\n  \.tz-slot \.tzz-art \{ width: (\d+)px", "the slot card's art width"))
        pad = _one(css, r"\n  \.tz-slot \.tzz \{ padding: (\d+)px (\d+)px (\d+)px (\d+)px; \}", "the slot card's padding")
        cls.pad = float(pad[1]) + float(pad[3])
        cls.gap = float(_one(css, r"\n  \.tzz \{ display: flex; align-items: center; gap: (\d+)px", "the card's gap"))
        cls.fixed = cls.art + cls.pad + cls.gap + 2          # + the 1px border each side
        cls.fs_md = float(_one(css, r"--fs-md:\s*clamp\(\s*\d+px,\s*[\d.]+vw,\s*(\d+)px\)", "--fs-md's ceiling"))
        rule = _one(css, r"\n  \.hd-tz \.tz-slot \.tz-zones \{\s*grid-template-columns: repeat\(auto-fit, minmax\(min\(max\(238px, "
                         r"calc\((\d+)px \+ ([\d.]+) \* var\(--fs-md\)\)\), 100%\), 1fr\)\); \}", "the slot's zone grid floor")
        cls.a, cls.k = float(rule[0]), float(rule[1])

    def test_baseline_238px_alone_cuts_the_verdict(self):
        need = self.fixed + MONO_EM * len(VERDICT) * self.fs_md
        self.assertLess(238, need, "PREMISE: a 238px card holds the verdict - the case would not distinguish")

    def test_the_floor_covers_the_cards_fixed_parts(self):
        """* THE POINT (1/2) - the px part of the floor is the art, padding, gap and border, read from this file"""
        self.assertGreaterEqual(self.a, self.fixed, "the floor's %gpx is under the card's fixed %gpx" % (self.a, self.fixed))

    def test_the_floor_covers_the_verdict_at_its_font(self):
        """* THE POINT (2/2) - '→ 96 terrorized' at --fs-md: 15 mono characters"""
        self.assertGreaterEqual(self.k, MONO_EM * len(VERDICT),
                                "%g x --fs-md is under the verdict's %g em" % (self.k, MONO_EM * len(VERDICT)))


RED_PROOF = [
    {"why": "REG-3769 - the slot's zone grid floor is gone: two-up from 1480 cuts every density line at his 1512",
     "file": "tv/control_ui.html",
     "find": "  .hd-tz .tz-slot .tz-zones {\n",
     "replace": "  .hd-tz .tz-slot .tz-zones-gone {\n",
     "matches": 1},
    {"why": "REG-3769 - the floor no longer covers the verdict's width at its font",
     "file": "tv/control_ui.html",
     "find": "calc(108px + 9.2 * var(--fs-md))",
     "replace": "calc(108px + 6 * var(--fs-md))",
     "matches": 1},
    {"why": "REG-3769 - the floor no longer covers the card's art and padding",
     "file": "tv/control_ui.html",
     "find": "calc(108px + 9.2 * var(--fs-md))",
     "replace": "calc(60px + 9.2 * var(--fs-md))",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
