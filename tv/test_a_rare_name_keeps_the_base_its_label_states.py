# -*- coding: utf-8 -*-
"""REG-3089 (#158) - A RARE'S NAME FOLLOWED BY ITS BASE KEEPS THE BASE IT STATES.

A ground label is two lines - the rare's name over its base - and the reader handed some over as one. Measured read-only on
claude/int (836921abc): routing every name of his last vault sweep through the page's router in node, "Chaos Whorl Ring",
"Dread Grip Demonhide Gloves" and "Raven Casque Circlet" had no home ("nothing on the board recognises this name"). Now the
rare grammar (_rolledQuality) reads the first two words as the rare and keeps the rest as its base when the builder's base
table names it AND its type is a slot the suffix can name (the game's itypes - a Circlet is a helm, Demonhide Gloves are
gloves); the router files it as a rare, and its picture is its stated base. A base the suffix cannot wear is not settled
here - nothing is claimed - and a two-word rare is unchanged. Driven on the whole page in node, fixture names. RED_PROOF below.
"""
import json
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
import vault_page_node as VPN  # noqa: E402

NAMES = ["Chaos Whorl Ring", "Dread Grip Demonhide Gloves", "Raven Casque Circlet", "DREAD GRIP DEMONHIDE GLOVES",
         "Raven Whorl Gloves", "Grim Hood Monarch", "Raven Casque", "Doom Grasp Zorblax"]
BODY = r"""
(function(){
var W = window, N = __N__;
OUT.r = {};
N.forEach(function(n){
  var q = null, s = null, b = null;
  try { q = _rolledQuality(n); } catch (e) {}
  try { s = W.suggestMule(n); } catch (e) {}
  try { b = W._artRolledBase(n); } catch (e) {}
  OUT.r[n] = { q: q && q.q || null, base: q && q.base || null, slots: q && q.slots || null, mule: s ? (s.id || s.mule || null) : null,
               art: b ? b.base : null, ask: b ? b.ask : null };
});
})();
""".replace("__N__", json.dumps(NAMES))


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class ARareNameKeepsTheBaseItsLabelStates(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.o = VPN.run(BODY, prelude="localStorage.setItem('d2r_ownerClaim', '*');\n", timeout=300)["r"]

    def test_the_label_two_lines_read_as_one_keep_their_base(self):
        for n, base in (("Chaos Whorl Ring", "Ring"), ("Dread Grip Demonhide Gloves", "Demonhide Gloves"),
                        ("Raven Casque Circlet", "Circlet"), ("DREAD GRIP DEMONHIDE GLOVES", "Demonhide Gloves")):
            r = self.o[n]
            self.assertEqual((r["q"], r["base"]), ("rare", base), "%s: %r" % (n, r))
            self.assertEqual(r["mule"], "magic-rare", "%s has no home: %r" % (n, r))
            self.assertEqual(r["art"], base, "%s does not draw the base its label states: %r" % (n, r))

    def test_a_base_the_suffix_cannot_wear_settles_nothing(self):
        for n in ("Raven Whorl Gloves", "Grim Hood Monarch", "Doom Grasp Zorblax"):
            self.assertIsNone(self.o[n]["base"], "%s: a base the suffix cannot wear (or no base) was kept: %r" % (n, self.o[n]))
            self.assertNotEqual(self.o[n]["mule"], "magic-rare", "%s was filed on a base its suffix cannot wear" % n)

    def test_a_two_word_rare_is_unchanged(self):
        r = self.o["Raven Casque"]
        self.assertEqual((r["q"], r["base"], r["slots"]), ("rare", None, ["Helm"]), r)


RED_PROOF = [
    {"why": "REG-3089 - a rare's name followed by its base has no home again",
     "file": "bible.html",
     "find": "    if (fits) return { q: 'rare', slots: ks3, prefix: w[0], suffix: w[1], base: fits };\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3089 - a base the suffix cannot wear is kept anyway (Raven Whorl Gloves a rare on gloves)",
     "file": "bible.html",
     "find": "  return ok ? String(d.b[code][0]) : null;\n",
     "replace": "  return String(d.b[code][0]);\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3089 - the picture ignores the base the label states",
     "file": "bible.html",
     "find": "  if (rq && rq.q === 'rare' && rq.base) { out.base = String(rq.base); return out; }   /* REG-3089 the base its label states */\n",
     "replace": "",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
