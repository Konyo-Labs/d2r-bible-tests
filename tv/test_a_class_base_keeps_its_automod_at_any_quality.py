# -*- coding: utf-8 -*-
"""v3886 (#139, GrokBot's #28 pass 6720634931, adjudicated REAL 11-08) - A CLASS BASE'S AUTOMOD IS ITS OWN, WHATEVER THE
QUALITY.

GrokBot, on the build screen: "the builder offers 0 automod rows for an Auric base; a Spirit Sacred Targe can carry up to
+45 all res the panel never shows". The game draws a class base's automod (armor / weapons.txt `auto prefix`, the
automagic.txt group: an Auric shield's Shimmering +5-10 ... Chromatic +35-45 all res, or Sharp ... Knight's ED/AR) on a
normal and a superior item too, and a runeword keeps the base it was made in. The builder allowed an automod on magic, rare
and crafted items only (_cbLimits: white, superior and runeword 0). Now those three take ONE automod from the base's own
group; a base with no group (a Monarch, a Diadem) still takes none.

Drives the SHIPPED builder in node over the edit-tab law's harness (imported, never re-typed). RED_PROOF below.
"""
import os
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

import test_the_item_edit_tab_builds_magic_and_rare_items as ED  # noqa: E402  the edit tab's own harness

ALL_RES = ["a22", "a23", "a24", "a25", "a26"]      # Shimmering, Rainbow, Scintillating, Prismatic, Chromatic (group 304)

BODY = r"""
mk('Paladin', 90);
function base(code){ var d = window._cbDb(); return d.b[code]; }
function code(name){ var d = window._cbDb(), c = null; Object.keys(d.b).forEach(function(k){ if (!c && d.b[k][0] === name) c = k; }); return c; }
var targe = code('Sacred Targe'), monarch = code('Monarch');
OUT.groups = [base(targe)[22], base(monarch)[22]];
OUT.lim = {};
['b', 'sup', 'r', 'm', 'rare', 'low'].forEach(function(q){ OUT.lim[q] = [window._cbLimits(q, base(targe)).a, window._cbLimits(q, base(monarch)).a]; });
function pool(q, bcode){ var e = { id: 'b:' + bcode, base: bcode, q: q, ilvl: 99, affixes: [] }; return ids(e).a; }
OUT.white = pool('b', targe); OUT.sup = pool('sup', targe); OUT.whiteMonarch = pool('b', monarch);
var spirit = null; window._cbDb().it.forEach(function(x){ if (x[1] === 'Spirit' && x[2] === 'r') spirit = x[0]; });
OUT.spirit = spirit ? ids({ id: spirit, base: targe, ilvl: 99, affixes: [] }).a : null;
OUT.spiritMonarch = spirit ? ids({ id: spirit, base: monarch, ilvl: 99, affixes: [] }).a : null;
"""


@unittest.skipIf(ED.CB.NODE is None, "node is not on this machine")
class AClassBaseKeepsItsAutomodAtAnyQuality(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.o = ED._run(BODY)

    def test_premise_the_targe_has_a_group_and_the_monarch_none(self):
        self.assertEqual(self.o["groups"], [304, 0], "PREMISE: the bases' automagic groups are not what the install says")

    def test_white_superior_and_runeword_take_one_automod_from_the_bases_own_group(self):
        """* THE POINT - a white or superior Sacred Targe, and a Spirit made in one, offer the all-res automods"""
        lim = self.o["lim"]
        for q in ("b", "sup", "r"):
            self.assertEqual(lim[q][0], 1, "a %s Sacred Targe takes no automod" % q)
        for nm in ("white", "sup", "spirit"):
            got = self.o[nm] or []
            self.assertTrue(all(a in got for a in ALL_RES), "%s Sacred Targe does not offer every all-res automod: %r" % (nm, got))

    def test_a_base_with_no_group_takes_none(self):
        """baseline: the change is the base's group, never every item - a Monarch (no auto prefix) offers no automod"""
        lim = self.o["lim"]
        for q in ("b", "sup", "r", "low"):
            self.assertEqual(lim[q][1], 0, "a %s Monarch is given an automod it cannot roll" % q)
        self.assertEqual(self.o["whiteMonarch"], [], "a white Monarch lists automods")
        self.assertEqual(self.o["spiritMonarch"] or [], [], "a Spirit Monarch lists automods")
        self.assertEqual(self.o["lim"]["low"][0], 0, "a low-quality item is given an automod")


RED_PROOF = [
    {"why": "v3886 (#139) - a white or runeword class base takes no automod again (a Spirit Sacred Targe's +45 all res unpickable)",
     "file": "bible.html",
     "find": "    if (q === 'b' || q === 'r') return { p: 0, s: 0, a: own ? 1 : 0, q: 0, total: null };\n",
     "replace": "    if (q === 'b' || q === 'r') return { p: 0, s: 0, a: 0, q: 0, total: null };\n",
     "matches": 1, "needs": "node"},
    {"why": "v3886 (#139) - every white item is given an automod, whatever its base (a Monarch rolls none)",
     "file": "bible.html",
     "find": "    var own = !!(b && (b[22] | 0) > 0);\n",
     "replace": "    var own = true;\n",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main()
