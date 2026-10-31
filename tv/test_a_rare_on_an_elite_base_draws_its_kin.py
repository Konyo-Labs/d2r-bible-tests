# -*- coding: utf-8 -*-
"""v3849 B4 (vault batch 2026-10-31) - A RARE ON AN ELITE BASE DRAWS A PICTURE, NOT THE BLANK MARK.

Measured before (the whole page in node): Storm Visor kept on a Shako, Beast Spur on Wyrmhide Boots and Plague Hold on
Bramble Mitts each drew d2art-failed (the blank mark), and so did the plain bases. An elite base with no art file of its
own is drawn through its tier chain kin (Shako -> War Hat -> Cap, the same slot and shape). A unique keeps its own
picture, and a ring/jewel doubt (Chaos Gyre) keeps its question.
"""
import os, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable; enable()
import vault_page_node as VPN  # noqa: E402

BODY = r"""
magicFinds['Storm Visor'] = {q:'rare', base:'Shako'};
magicFinds['Beast Spur'] = {q:'rare', base:'Wyrmhide Boots'};
magicFinds['Plague Hold'] = {q:'rare', base:'Bramble Mitts'};
var r = {};
['Storm Visor','Beast Spur','Plague Hold','Shako','Wyrmhide Boots','Bramble Mitts','Harlequin Crest','Chaos Gyre'].forEach(function(n){
  var h = String(artOr(n, 'X', 'lg')); var m = h.match(/src="([^"]+)"/);
  r[n] = {failed: /class="d2art-wrap[^"]*d2art-failed/.test(h), src: m ? m[1] : ''};
});
OUT.r = r;
"""


class EliteBaseKin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = VPN.run(BODY, timeout=300)["r"]

    def test_rares_on_elite_bases_draw_a_picture(self):
        for n in ("Storm Visor", "Beast Spur", "Plague Hold", "Shako", "Wyrmhide Boots", "Bramble Mitts"):
            self.assertFalse(self.r[n]["failed"], n)
            self.assertTrue(self.r[n]["src"], n)

    def test_a_slot_draws_its_own_slot(self):
        self.assertEqual(self.r["Storm Visor"]["src"], self.r["Shako"]["src"])
        self.assertEqual(self.r["Plague Hold"]["src"], self.r["Bramble Mitts"]["src"])

    def test_unique_and_doubt_unchanged(self):
        self.assertIn("harlequin", self.r["Harlequin Crest"]["src"])
        self.assertTrue(self.r["Chaos Gyre"]["failed"])


RED_PROOF = [
    {"why": "v3849 B4 - a kept elite base asks only its own (missing) file again",
     "file": "bible.html",
     "find": "      var _bu = _artBaseOrKin(_rb.base);\n",
     "replace": "      var _bu = artUrl(_rb.base);\n",
     "matches": 1},
    {"why": "v3849 B4 - a plain elite base is not drawn through its kin",
     "file": "bible.html",
     "find": "  if (!u) u = _artBaseOrKin(_cleanP, true);",
     "replace": "  if (false) u = _artBaseOrKin(_cleanP, true);",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
