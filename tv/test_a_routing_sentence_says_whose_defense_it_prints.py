# -*- coding: utf-8 -*-
"""REG-2885 (#137, GrokBot v3740: "Ravenlore defense 103-155 (message) vs 343-390 (card)"; the batch's ACT list: "defense
ranges agree") - THE ROUTING SENTENCE SAYS WHOSE DEFENSE IT PRINTS.

MEASURED before (whole page in node): suggestMule('Ravenlore').why read "armor slot — Sky Spirit (BASE_DB defense
103-155)". That range is the BASE's, and the game's own table (the CB_DB block from his install) has Sky Spirit at
103-155. The item card prints the item's own defense. An item that spawns with Enhanced Defense sits at its base's max
+ 1, times its roll: 156 x 2.20-2.50 = 343-390. Both numbers were right, but "BASE_DB defense" read as the item's, so the
two looked like a disagreement.

Now the sentence says it: "Sky Spirit is armour (the base's own defense is 103-155; the item card shows the item's
defense)". Its range is the game table's base range, the one the card starts from. Whole page in node; the game table is
read from the page's own CB_DB block. Never a browser. RED_PROOF below.
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

BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")
TAG = '<script type="application/json" id="cb-db">'


def _base_defense(code):
    """the base's defense range in the game's own table (b[code][8], b[code][9], the Edit panel's min and max)"""
    with open(BIBLE, encoding="utf-8") as fh:
        s = fh.read()
    i = s.index(TAG) + len(TAG)
    b = json.loads(s[i:s.index("</script>", i)])["b"][code]
    return b[0], "%d-%d" % (b[8], b[9])


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class ARoutingSentenceSaysWhoseDefenseItPrints(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.o = VPN.run("OUT.raven = window.suggestMule('Ravenlore'); OUT.lidless = window.suggestMule('Lidless Wall');", prelude="")

    def test_the_sentence_names_the_base_and_its_own_range_from_the_game_table(self):
        name, rng = _base_defense("dre")
        self.assertEqual((name, rng), ("Sky Spirit", "103-155"), "PREMISE: the game table moved")
        r = self.o["raven"]
        self.assertEqual(r["id"], "uni-armor", r)
        self.assertIn("Sky Spirit is armour (the base's own defense is %s; the item card shows the item's defense)" % rng, r["why"])
        self.assertNotIn("BASE_DB", r["why"], "the sentence still reads the base's range as the item's")

    def test_every_armour_base_says_it_the_same_way(self):
        name, rng = _base_defense("xsh")
        self.assertIn("%s is armour (the base's own defense is %s;" % (name, rng), self.o["lidless"]["why"])


RED_PROOF = [
    {"why": "REG-2885 - the routing sentence prints the base's range as if it were the item's again",
     "file": "bible.html",
     "find": "why:'armor slot — '+base+' is armour (the base\\'s own defense is '+_bRec.defense+'; the item card shows the item\\'s defense)'};",
     "replace": "why:'armor slot — '+base+' (BASE_DB defense '+_bRec.defense+')'};",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
