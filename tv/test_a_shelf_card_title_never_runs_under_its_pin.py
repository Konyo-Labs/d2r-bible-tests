# -*- coding: utf-8 -*-
"""#86 (REG-2755, GrokBot's v3821 and v3823 passes) - A SHELF CARD'S TITLE NEVER RUNS UNDER ITS PIN AND SEAL.

GrokBot saw a card's date wrap "AM" under the ☆ twice. The title was absolute with a fixed right reserve of 104px for
the pin and the seal (v3214), and "🛡 clean" + the pin + their gap + the inset need ~111px in Chrome's mono and more in
his WebKit's: a reserve is a guess about a width it cannot see. The title and the cluster are one flex row now
(.shc-top): the cluster takes what it needs (flex:none), the title takes the rest (min-width:0), whatever the seal says
or the font measures - and the title's time is one unit (.shc-hm), so a narrow card breaks the line at the dot.

The overlap depends on font metrics (CI's fonts are not his), so a geometry check is a floor here and the stylesheet
parse is the proof - the v2229 rule for the console's grid tracks. RED_PROOF below.
"""
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

UI = io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()


def _rule(sel):
    """The declarations of the ONE rule whose selector is exactly `sel`. -> {prop: value}"""
    hits = re.findall(r"(?m)^\s*" + re.escape(sel) + r"\s*\{([^}]*)\}", UI)
    if len(hits) != 1:
        raise AssertionError("expected one %s rule, found %d" % (sel, len(hits)))
    body = re.sub(r"/\*.*?\*/", "", hits[0], flags=re.S)
    out = {}
    for decl in body.split(";"):
        if ":" in decl:
            k, v = decl.split(":", 1)
            out[k.strip()] = v.strip()
    return out


class TheTitleAndTheClusterShareOneRow(unittest.TestCase):

    def test_the_row_is_a_flex_row(self):
        top = _rule(".shc-top")
        self.assertEqual(top.get("display"), "flex", "the title and the cluster are not one flex row: %r" % top)
        self.assertEqual(top.get("position"), "absolute", "PREMISE: the row is not pinned to the hero's top: %r" % top)

    def test_the_title_takes_only_what_is_left(self):
        t = _rule(".shc-sess")
        self.assertNotEqual(t.get("position"), "absolute",
                            "the title is absolute again, so a fixed reserve decides whether it runs under the pin: %r" % t)
        self.assertNotIn("right", t, "the title carries a fixed right reserve again: %r" % t.get("right"))
        self.assertEqual(t.get("min-width"), "0", "a flex title without min-width:0 refuses to shrink below its text")

    def test_the_cluster_takes_what_it_needs(self):
        c = _rule(".shc-tr")
        self.assertNotEqual(c.get("position"), "absolute", "the pin and seal left the row: %r" % c)
        self.assertEqual(c.get("flex"), "none", "the cluster can be squeezed under its own seal: %r" % c)

    def test_the_card_builds_them_into_the_row_and_keeps_the_time_whole(self):
        self.assertEqual(UI.count("'<div class=\"shc-top\"><div class=\"shc-sess\">'"), 1,
                         "the card does not put its title in the row")
        self.assertEqual(UI.count("+ '<div class=\"shc-tr\">' + pinBtn + seal + '</div></div>'"), 1,
                         "the card does not put its pin and seal in the row")
        self.assertIn("' · <span class=\"shc-hm\">' + d0.toLocaleTimeString(", UI,
                      "the title's time is not one unit, so a narrow card splits \"7:40\" from \"AM\"")
        self.assertEqual(_rule(".shc-hm").get("white-space"), "nowrap")
        self.assertEqual(_rule(".shc-hm").get("display"), "inline-block",
                         "the time is an inline span, so its font box sticks out of the clamped title (cut by shc-sess)")


RED_PROOF = [
    {"why": "REG-2755 - the title is absolute with a fixed 104px reserve again",
     "file": "control_ui.html",
     "find": "  .shc-sess { position: relative; flex: 1 1 auto; min-width: 0; margin-top: 1px; z-index: 2;",
     "replace": "  .shc-sess { position: absolute; top: 9px; left: 12px; right: 104px; z-index: 2;",
     "matches": 1},
    {"why": "REG-2755 - the cluster can be squeezed",
     "file": "control_ui.html",
     "find": "  .shc-tr { position: relative; flex: none; z-index: 2;",
     "replace": "  .shc-tr { position: relative; z-index: 2;",
     "matches": 1},
    {"why": "REG-2755 - the title's time splits from its AM again",
     "file": "control_ui.html",
     "find": "  .shc-hm { white-space: nowrap; display: inline-block; }",
     "replace": "  .shc-hm { white-space: normal; display: inline-block; }",
     "matches": 1},
    {"why": "v3855 - the time is an inline span again, its 21px font box poking out of the 15px clamped title",
     "file": "control_ui.html",
     "find": "  .shc-hm { white-space: nowrap; display: inline-block; }",
     "replace": "  .shc-hm { white-space: nowrap; }",
     "matches": 1},
    {"why": "REG-2755 - the card leaves its title outside the row",
     "file": "control_ui.html",
     "find": "          + '<div class=\"shc-top\"><div class=\"shc-sess\">'",
     "replace": "          + '<div class=\"shc-top\"></div><div class=\"shc-sess\">'",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
