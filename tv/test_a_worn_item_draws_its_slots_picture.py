# -*- coding: utf-8 -*-
"""REG-3070 (#36, GrokBot 04:03) - A WORN ITEM DRAWS ITS SLOT'S PICTURE.

The character window drew each worn item by its own NAME, the one surface that only has a name: a runeword's name drew
whatever base its picture was keyed to whatever the slot (Fortitude in the Armor slot drew hd_crystal_sword, Splendor and
Plague likewise another slot's base), and a rare's name or a plain word drew nothing at all (Carrion Greaves, Wraith
Grasp, Dragon Talon, and the bare "Shield", "Armor", "Boots" a read sometimes leaves). #248's rule, given the slot
(_cbSlotArtName, asked by _chxDollHtml):
  * a unique or set item draws its own graphic;
  * a recorded base of THAT slot's type draws that base, and a plain base names itself (when it is of that slot's type);
  * a runeword draws a base of that slot's type it can be made in - its own picture when that is one (Enigma's plate mail
    on the torso), never another slot's (Fortitude's crystal sword on the torso) - the slot's own kind first (a shield in
    the off-hand before a second weapon);
  * anything else (a rare's name, a bare word, a runeword read in a slot it cannot be made for) draws a base of that
    slot's type;
  * null when the builder's database cannot be read, which the doll draws UNKNOWN.
Run on the whole page in node (tv/vault_page_node.py): each case's answer is checked against the database's own type tree
(the base is of the slot's kind, and a runeword's base is one its recipe names), and the window is opened on a gear map
and every worn cell is read for its picture. RED_PROOF below.
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

# (item, worn slot, what it is) - GrokBot's 04:03 list, plus the off-hand's two kinds
CASES = [("Fortitude", "torso", "rw"), ("Fortitude", "weapon", "rw"), ("Splendor", "torso", "rw"),
         ("Splendor", "off-hand", "rw"), ("Peace", "torso", "rw"), ("Treachery", "torso", "rw"), ("Plague", "torso", "rw"),
         ("Enigma", "torso", "rw"), ("Spirit", "off-hand", "rw"), ("Lawbringer", "off-hand", "rw"),
         ("Carrion Greaves", "boots", "word"), ("Wraith Grasp", "gloves", "word"), ("Dragon Talon", "gloves", "word"),
         ("Shield", "off-hand", "word"), ("Armor", "torso", "word"), ("Boots", "boots", "word"),
         ("Battle Boots", "boots", "base"), ("Harlequin Crest", "helm", "own"), ("Arachnid Mesh", "belt", "own")]
# the slot's kind, by the database's own item types (a base is of the kind when its type or an ancestor is one of these)
KIND = {"torso": ["tors"], "boots": ["boot"], "gloves": ["glov"], "helm": ["helm", "circ", "pelt", "phlm"],
        "belt": ["belt"], "weapon": ["weap"], "off-hand": ["shld", "weap", "bowq", "xboq", "head", "grim", "ashd"]}
SHIELD_FIRST = {"Spirit", "Splendor"}   # runewords a shield can carry: in the off-hand they draw a shield, never a sword

BODY = r"""
(function(){
var W = window, d = W._cbDb(), CASES = %s, KIND = %s;
function baseOf(name){ return Object.keys(d.b).filter(function(k){ return d.b[k][0] === name; }); }
function isOf(code, types){ var t = d.b[code][1], anc = d.anc[t] || {}; return types.some(function(x){ return x === t || !!anc[x]; }); }
OUT.cases = CASES.map(function(c){
  var n = W._cbSlotArtName(c[0], c[1]), it = d.byName[c[0].toLowerCase()] || null, codes = n ? baseOf(n) : [];
  var allowed = (it && it[2] === 'r' && it[7] && it[7].it) || null;
  return { item: c[0], slot: c[1], kind: c[2], name: n, src: n ? (W.artUrl(n) || null) : null, ownSrc: W.artUrl(c[0]) || null,
           q: it ? it[2] : null, isBase: codes.length > 0,
           ofSlot: codes.some(function(k){ return isOf(k, KIND[c[1]]); }),
           shield: codes.some(function(k){ return isOf(k, ['shld']); }),
           madeIn: !allowed || codes.some(function(k){ return isOf(k, allowed); }),
           /* can the runeword be made in ANY base of this slot's kind? (Plague, a weapon's, read on the torso cannot) */
           possible: !allowed || Object.keys(d.b).some(function(k){ return isOf(k, KIND[c[1]]) && isOf(k, allowed); }) };
});
/* the window, opened on a gear map that holds the cases (one item per slot) */
var slots = ['helm','amulet','weapon','torso','off-hand','gloves','ring1','belt','ring2','boots'];
var wear = { helm: 'Harlequin Crest', weapon: 'Fortitude', torso: 'Enigma', 'off-hand': 'Shield', gloves: 'Dragon Talon',
             belt: 'Arachnid Mesh', boots: 'Carrion Greaves' };
var L = { ok: true, chars: [], gear: { konyolock: { name: 'KonyoLock', reels: 1, unplaced: [], slots: slots.map(function(s){
  return { slot: s, item: wear[s] || null, sightings: wear[s] ? 3 : 0, tier: wear[s] ? 'WATCHED' : null }; }) } } };
W._cbLearnedNow = function(){ return L; };
W._chxOpen('seen:konyolock');
var h = document.getElementById('chx-win').innerHTML, re = /data-cell="equipped:([\w-]+)"[\s\S]*?<\/button>/g, m;
OUT.win = {};
while ((m = re.exec(h))){ var s = /src="([^"]+)"/.exec(m[0]); OUT.win[m[1]] = s ? s[1].split('?')[0] : null; }
OUT.want = {};
Object.keys(wear).forEach(function(s){ var n = W._cbSlotArtName(wear[s], s); OUT.want[s] = n ? String(W.artUrl(n) || '').split('?')[0] : null; });
})();
"""


class AWornItemDrawsItsSlotsPicture(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.out = None
        if not VPN.NODE:
            return
        cls.out = VPN.run(BODY % (json.dumps(CASES), json.dumps(KIND)),
                          prelude="localStorage.setItem('d2r_ownerClaim', '*');\n", timeout=300)

    def setUp(self):
        if self.out is None:
            self.skipTest("node is absent on this machine - the pictures are UNMEASURED here, never a pass")

    def test_every_case_draws_a_picture_of_its_slot(self):
        bad = []
        for c in self.out["cases"]:
            what = "%s in the %s slot -> %r (%r)" % (c["item"], c["slot"], c["name"], c["src"])
            if not c["src"]:
                bad.append(what + ": no picture")
            elif c["kind"] == "own":
                if c["name"] != c["item"]:
                    bad.append(what + ": a unique or set item lost its own graphic")
            elif not (c["isBase"] and c["ofSlot"]):
                bad.append(what + ": not a base of the slot's kind")
            elif c["kind"] == "rw" and c["possible"] and not c["madeIn"]:
                bad.append(what + ": a base the runeword cannot be made in, while the slot has one it can")
            elif c["kind"] == "base" and c["name"] != c["item"]:
                bad.append(what + ": a plain base did not draw itself")
        self.assertEqual(bad, [], "\n".join(bad))

    def test_a_runeword_never_draws_another_slots_base(self):
        c = {(x["item"], x["slot"]): x for x in self.out["cases"]}
        fort = c[("Fortitude", "torso")]
        self.assertNotEqual(fort["src"], fort["ownSrc"], "Fortitude on the torso still draws its crystal sword")
        # the own picture stays when it is of the slot (Enigma's plate mail on the torso, Fortitude's sword in the hand)
        self.assertEqual(c[("Enigma", "torso")]["src"], c[("Enigma", "torso")]["ownSrc"])
        self.assertEqual(c[("Fortitude", "weapon")]["src"], c[("Fortitude", "weapon")]["ownSrc"])
        for rw in SHIELD_FIRST:
            self.assertTrue(c[(rw, "off-hand")]["shield"], "%s in the off-hand drew a second weapon before a shield" % rw)
        self.assertFalse(c[("Lawbringer", "off-hand")]["shield"], "Lawbringer cannot be a shield, yet drew one")

    def test_the_character_window_draws_each_cell_by_its_slot(self):
        win, want = self.out["win"], self.out["want"]
        self.assertTrue(win, "the window drew no worn cell")
        bad = ["%s: drew %r, the slot's answer is %r" % (s, win.get(s), want[s]) for s in want if not want[s] or win.get(s) != want[s]]
        self.assertEqual(bad, [], "\n".join(bad))


RED_PROOF = [
    {"why": "REG-3070 - the character window draws a worn item by its own name again",
     "file": "bible.html",
     "find": "      var _an = (typeof window._cbSlotArtName === 'function') ? window._cbSlotArtName(s.item, worn, s.base) : s.item;",
     "replace": "      var _an = s.item;",
     "matches": 1, "needs": "node"},
    {"why": "REG-3070 - a runeword keeps its own picture whatever the slot",
     "file": "bible.html",
     "find": "    if (it && (it[2] === 'u' || it[2] === 's')) return it[1];\n    var types = _cbWornTypes(worn);",
     "replace": "    if (it && (it[2] === 'u' || it[2] === 's' || it[2] === 'r')) return it[1];\n    var types = _cbWornTypes(worn);",
     "matches": 1, "needs": "node"},
    {"why": "REG-3070 - the off-hand draws a second weapon before a shield",
     "file": "bible.html",
     "find": "    return own.length ? [own, weap].filter(function(t){ return t.length; }) : [weap];",
     "replace": "    return [weap.concat(own)];",
     "matches": 1, "needs": "node"},
    {"why": "REG-3070 - a rare's name draws nothing (no base of the slot stands in)",
     "file": "bible.html",
     "find": "    return (mine && _cbWornBase(worn, allowed, mine)) || (allowed && _cbWornBase(worn, allowed)) || _cbWornBase(worn, null) || n;",
     "replace": "    return (mine && _cbWornBase(worn, allowed, mine)) || (allowed && _cbWornBase(worn, allowed)) || n;",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
