# -*- coding: utf-8 -*-
"""REG-3087 + REG-3088 (#158) - A ROLLED NAME IS READ IN EVERY SLOT THE GAME'S TABLES NAME, AND IN CAPITALS.

Measured read-only on claude/int (836921abc): every one of the 307 names on his last vault sweep was routed through the
page's own router (suggestMule) in node. 51 had no home ("nothing on the board recognises this name ... it stays in
Unsorted"); two causes were the grammar's, not the reads':
  * REG-3087 - 25 were reads in CAPITALS (FINE SMALL CHARM OF VITA, WRAITH GRASP, SHIMMERING SMALL CHARM OF FLAME): the rare
    and charm grammar (_rolledQuality, _charmKind) matched title case only, while every catalogue folds case. The grammar now
    folds case where the catalogues fold it: any casing is matched in the game's own (_rolledSpelling) - never written back.
  * REG-3088 - the rare grammar knew four slots (amulet, ring, jewel, gloves). The game's RareSuffix table (the builder's
    CB_DB carries it, with each word's itypes) names helms, boots, belts, armour, shields and weapons too: Grim Hood, Raven
    Casque, Bone Visor, Raven Greaves, Glyph Badge, Cruel Needle, Soul Bite sat in Unsorted. RARE_NAME_POOLS now carries
    those rows (every game word but the ones the four rows already answer), the prefixes carry the game's Armageddon and
    Empyrian, a magic suffix of the "of the X" shape reads (Shadow Amulet of the Whale), a BASE is never a rolled name
    (Bone Shield, Grim Wand, Death Mask), and a one-slot class (Armor, Shield, Weapon) asks which base, never names one.
After: 35 of the 51 found their home and no name changed from one home to another.

Driven on the whole page in node, fixture names only. RED_PROOF below.
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

ROUTE = {   # name -> the home the router must answer
    "WRAITH GRASP": "magic-rare", "GHOUL GRASP": "magic-rare", "AMULET OF WEALTH": "magic-rare",
    "FINE SMALL CHARM OF VITA": "shared", "SHIMMERING SMALL CHARM OF FLAME": "shared",
    "Wraith grasp": "magic-rare", "fine small charm of vita": "shared",
    "Grim Hood": "magic-rare", "Raven Casque": "magic-rare", "Raven Greaves": "magic-rare", "Glyph Badge": "magic-rare",
    "Cruel Needle": "magic-rare", "Soul Bite": "magic-rare", "RAVEN GREAVES": "magic-rare",
    "Shadow Amulet of the Whale": "magic-rare", "Amulet of the Fox": "magic-rare",
    "Armageddon Hood": "magic-rare",
    # unchanged: a title-case read, a real unique in capitals, a base that wears a rare's words
    "Wraith Grasp": "magic-rare", "Fine Small Charm of Vita": "shared",
}
BODY = r"""
(function(){
var W = window, R = __R__;
OUT.route = {}; OUT.rq = {}; OUT.base = {};
Object.keys(R).concat(['RAVEN CLAW', 'Raven Claw', 'Bone Shield', 'Grim Wand', 'Death Mask', 'Grim Coat', 'Grim Hood', 'Wraith Claw', 'Raven Whorl', 'Shadow Horn']).forEach(function(n){
  var s = null; try { s = W.suggestMule(n); } catch (e) {}
  OUT.route[n] = s ? (s.id || s.mule || null) : null;
  var q = null; try { q = _rolledQuality(n); } catch (e) {}
  OUT.rq[n] = q ? { q: q.q, slots: q.slots || null } : null;
  var b = null; try { b = W._artRolledBase(n); } catch (e) {}
  OUT.base[n] = b;
});
OUT.spell = ['FINE SMALL CHARM OF VITA', 'GHEED\'S FORTUNE', 'Shimmering small charm', 'X'].map(function(n){ return _rolledSpelling(n); });
/* the game's own table: every RareSuffix word sits in a pool, every RarePrefix word in the prefixes */
var d = W._cbDb(), pools = W.RARE_NAME_POOLS, all = {};
Object.keys(pools).forEach(function(k){ pools[k].forEach(function(w){ all[w] = 1; }); });
OUT.sufMissing = d.rn[1].map(function(r){ return r[0]; }).filter(function(w){ return !all[w]; });
OUT.preMissing = d.rn[0].map(function(r){ return r[0]; }).filter(function(w){ return W.RARE_NAME_PREFIXES.indexOf(w) < 0; });
OUT.suffixes = d.rn[1].length;
})();
""".replace("__R__", json.dumps(ROUTE))


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class ARolledNameIsReadInEverySlotAndAnyCasing(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.o = VPN.run(BODY, prelude="localStorage.setItem('d2r_ownerClaim', '*');\n", timeout=300)

    def test_every_read_finds_its_home(self):
        bad = ["%s -> %r, wants %r" % (n, self.o["route"].get(n), want) for n, want in ROUTE.items() if self.o["route"].get(n) != want]
        self.assertEqual(bad, [], "\n".join(bad))

    def test_capitals_are_read_in_the_games_casing_and_nothing_else_is_touched(self):
        self.assertEqual(self.o["spell"], ["Fine Small Charm of Vita", "Gheed's Fortune", "Shimmering Small Charm", "X"])
        self.assertIsNone(self.o["rq"]["RAVEN CLAW"], "a real unique in capitals was read as a rare")
        self.assertIsNone(self.o["rq"]["Raven Claw"])

    def test_the_games_rare_table_is_every_pool_word(self):
        self.assertGreater(self.o["suffixes"], 100, "PREMISE: the builder's RareSuffix table did not read")
        self.assertEqual(self.o["sufMissing"], [], "a game RareSuffix word no pool carries: %r" % self.o["sufMissing"])
        self.assertEqual(self.o["preMissing"], [], "a game RarePrefix word the prefixes lack: %r" % self.o["preMissing"])

    def test_a_base_is_never_a_rolled_name(self):
        for n in ("Bone Shield", "Grim Wand", "Death Mask"):
            self.assertIsNone(self.o["rq"][n], "%s is a base, read as a rare: %r" % (n, self.o["rq"][n]))

    def test_a_class_asks_its_base_and_the_old_rows_keep_their_answer(self):
        b = self.o["base"]
        self.assertEqual((b["Grim Coat"]["base"], b["Grim Coat"]["ask"][:13]), ("", "which armor? "), b["Grim Coat"])
        self.assertEqual(b["Grim Hood"]["base"], "Helm", b["Grim Hood"])
        self.assertEqual(self.o["rq"]["Wraith Claw"]["slots"], ["Gloves"], "REG-2402's gloves answer moved")
        # v3849 - his ruling (11:43, on the ALT's MAGIC locker, as bible.html records it): "Raven Whorl IS a ring", so REG-2903's ring-or-jewel
        # doubt no longer covers a Whorl; Gyre stays both
        self.assertEqual(self.o["rq"]["Raven Whorl"]["slots"], ["Ring"], "his v3849 ruling moved: a Whorl is a ring")
        self.assertEqual(self.o["rq"]["Shadow Horn"]["slots"], ["Helm", "Weapon"], "a word two rows share is not asked")


RED_PROOF = [
    {"why": "REG-3087 - a read in capitals is matched as typed again (WRAITH GRASP has no home)",
     "file": "bible.html",
     "find": "  if (!s) return s;\n  return s.toLowerCase().split(",
     "replace": "  if (s) return s;\n  return s.toLowerCase().split(",
     "matches": 1, "needs": "node"},
    {"why": "REG-3088 - the rare grammar knows four slots again (Grim Hood has no home)",
     "file": "bible.html",
     "find": "  Helm:   ['Horn',",
     "replace": "  Helmx:  ['Hornx',",
     "matches": 1, "needs": "node"},
    {"why": "REG-3088 - an 'of the X' suffix is unread again (Shadow Amulet of the Whale)",
     "file": "bible.html",
     "find": "(?:\\s+(of\\s+(?:the\\s+)?[A-Z][A-Za-z' \\-]*))?$/;",
     "replace": "(?:\\s+(of\\s+[A-Z][A-Za-z' \\-]*))?$/;",
     "matches": 1, "needs": "node"},
    {"why": "REG-3088 - a base is read as a rolled name (Bone Shield a rare shield)",
     "file": "bible.html",
     "find": "  try { if (typeof _baseRec === 'function' && _baseRec(nm)) return null; } catch(e){}\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3088 - a one-slot class names a base ('Armor') instead of asking",
     "file": "bible.html",
     "find": "  if (rq && rq.q === 'rare' && rq.slots && rq.slots.length === 1 && /^(Armor|Shield|Weapon)$/.test(rq.slots[0])) {",
     "replace": "  if (false) {",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
