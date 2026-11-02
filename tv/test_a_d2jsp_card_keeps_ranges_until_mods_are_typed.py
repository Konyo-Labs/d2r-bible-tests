# -*- coding: utf-8 -*-
"""v3855 C6 (Elad 2026-11-02) - A D2JSP ITEM CARD SHOWS THE ITEM'S MIN-MAX RANGES UNTIL HIS MODS ARE TYPED.

The card printed "No mods yet" and nothing else, so a unique with no typed roll showed none of what it can roll. Now the
card draws the range lines (a rolled name's affix ranges, else the catalogue lines that carry a min-max) until mods are
typed - in Options (modsOf) or in Edit mods (_typedModsOf) - and then draws none.
"""
import os, re, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable; enable()
import vault_page_node as VPN  # noqa: E402

SRC = open(os.path.join(HERE, "..", "bible.html"), encoding="utf-8").read()
BODY = r"""
var W = window;
OUT.shako = W._d2jspRangeLines('Harlequin Crest (Shako)');
OUT.charm = W._d2jspRangeLines('Small Charm of Vita');
OUT.rune = W._d2jspRangeLines('Ber Rune');
"""
_OUT = None


def out():
    global _OUT
    if _OUT is None:
        _OUT = VPN.run(BODY, prelude="localStorage.setItem('d2r_ownerClaim','*');", timeout=300)
    return _OUT


def card_src():
    a = SRC.index("  function cardHtml(n){\n    var art = d2jspArt(n);")
    return SRC[a:SRC.index("\n  }\n", a)]


class D2jspCardKeepsRanges(unittest.TestCase):
    def test_a_unique_and_a_charm_have_range_lines(self):
        o = out()
        for k in ("shako", "charm"):
            self.assertTrue(o[k], (k, o[k]))
            for l in o[k]:
                self.assertRegex(l, r"\d+\s*[-\u2013]\s*\d+", (k, l))
                self.assertNotIn("<", l)

    def test_the_card_draws_them_only_while_no_mod_is_typed(self):
        c = card_src()
        self.assertIn("var rng = (mods.trim() || (typeof window._typedModsOf === 'function' && window._typedModsOf(n))) ? [] : _d2jspRangeLines(n);", c)
        self.assertIn("+ rngHtml", c)
        self.assertIn('data-mod-range="1"', c)


RED_PROOF = [
    {"why": "the card never draws its ranges", "file": "bible.html",
     "find": "      + hint\n      + rngHtml\n", "replace": "      + hint\n", "matches": 1},
    {"why": "ranges stay after Edit mods typed the roll", "file": "bible.html",
     "find": "var rng = (mods.trim() || (typeof window._typedModsOf === 'function' && window._typedModsOf(n))) ? [] : _d2jspRangeLines(n);",
     "replace": "var rng = mods.trim() ? [] : _d2jspRangeLines(n);", "matches": 1},
    {"why": "a unique's catalogue ranges are not read", "file": "bible.html",
     "find": "(src || []).forEach(function(l){ var t = strip(l); if (RANGE.test(t)) out.push(t); });", "replace": "", "matches": 1},
]

if __name__ == "__main__":
    unittest.main()
