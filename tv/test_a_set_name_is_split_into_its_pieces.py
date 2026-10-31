# -*- coding: utf-8 -*-
"""v3849 B2/B3 (Elad's ruling, 2026-10-31) - A SET'S NAME IS ITS PIECES, AND THE PIECES OF ONE SET LIVE TOGETHER.

A full-set name (Naj's Ancient Vestige, Sazabi's Grand Tribute, Sigon's Complete Steel - any set's own name) entered or
read as one vault item is split into its real pieces from the set tables. Each piece keeps its own art, footprint and
routing; nothing owns the set's name, so no full-set picture is drawn. A set name already in his store is read the
same way at load.

Addendum (Elad 15:56): pieces of the same set are kept on the same mule. A sister piece already filed on a sets mule
takes the next piece there, and when a mule overflows the whole set moves to the next mule together.
"""
import json, os, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable; enable()
import vault_page_node as VPN  # noqa: E402

NAJ = ["Naj's Puzzler", "Naj's Light Plate", "Naj's Circlet"]
SAZ = ["Sazabi's Cobalt Redeemer", "Sazabi's Ghost Liberator", "Sazabi's Mental Sheath"]

BODY = r"""
var W = window, r = {};
r.naj = W._setPiecesOf("Naj's Ancient Vestige");
r.sigon = W._setPiecesOf("Sigon's Complete Steel");
r.piece = W._setPiecesOf("Naj's Circlet");
r.shako = W._setPiecesOf('Shako');
r.loaded = [...owned].sort();
var add = W._ownedAdd("Sazabi's Grand Tribute", null);
r.add = add && add.split;
r.ownsSaz = %(saz)s.map(function(n){ return owned.has(n); });
r.ownsSet = owned.has("Sazabi's Grand Tribute") || owned.has("Naj's Ancient Vestige");
r.art = %(naj)s.map(function(n){ return String(W.artUrl(n) || ''); });
r.setArt = String(W.artUrl("Naj's Ancient Vestige") || '');
r.size = %(naj)s.map(function(n){ return vaultSize(n); });
r.sister = suggestMule("Tal Rasha's Adjudication");
r.alone = suggestMule("Immortal King's Will");
/* overflow: 138 one-cell fillers leave 2 cells on mule 1; a set of three one-cell pieces must move whole to mule 2 */
var items = [];
for (var i = 0; i < 138; i++) items.push({n: 'F' + i, key: 'F' + i + '#0', w: 1, h: 1, area: 1, set: '', ct: 1});
['A', 'B', 'C'].forEach(function(p){ items.push({n: 'Set ' + p, key: 'Set ' + p + '#0', w: 1, h: 1, area: 1, set: 'Test Set', ct: 1}); });
var sp = W._vaultSpread(items, {}, -1);
r.where = {};
sp.mules.forEach(function(m, k){ (m.stash || []).concat(m.inv || []).forEach(function(c){ if (/^Set /.test(c.n)) r.where[c.n] = k; }); });
OUT.r = r;
""" % {"saz": json.dumps(SAZ), "naj": json.dumps(NAJ)}

PRELUDE = ("localStorage.setItem('d2r_ownerClaim','*');"
           "localStorage.setItem('d2r_owned', %s);"
           "localStorage.setItem('d2r_muleAssign', JSON.stringify({\"Tal Rasha's Guardianship\": 'sets-rest'}));"
           ) % json.dumps(json.dumps(["Naj's Ancient Vestige", "Shako", "Tal Rasha's Guardianship"]))

RED_PROOF = [
    {"file": "bible.html", "why": "v3849 B2/B3 - a set name is one item again",
     "find": "    if (_norm(String(sn).replace(tag, '')) === q) return sets[i].pieces.map(__pieceBase);\n",
     "replace": "    if (false) return sets[i].pieces.map(__pieceBase);\n"},
    {"file": "bible.html", "why": "v3849 B2/B3 - the door owns the set name",
     "find": "    if (_pcs && _pcs.length){\n      var _any = false, _lastP = null;\n",
     "replace": "    if (false){\n      var _any = false, _lastP = null;\n"},
    {"file": "bible.html", "why": "v3849 B2/B3 - a stored set name stays at load",
     "find": "      owned = new Set(_spl);\n",
     "replace": "      void _spl;\n"},
    {"file": "bible.html", "why": "v3849 B2/B3 - a sister piece's mule is ignored",
     "find": "        if (_sis) return {id:_sis, why:'set piece: '+psn+' - kept with its set'};\n",
     "replace": "        void _sis;\n"},
    {"file": "bible.html", "why": "v3849 B2/B3 - overflow splits a set across mules",
     "find": "        var name = it && it.set ? '\\u0000set:' + it.set : (it && it.n);\n",
     "replace": "        var name = it && it.n;\n"},
]


class SetNameSplits(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = VPN.run(BODY, prelude=PRELUDE, timeout=300)["r"]

    def test_the_set_tables_name_the_pieces(self):
        self.assertEqual(self.r["naj"], NAJ)
        self.assertGreaterEqual(len(self.r["sigon"] or []), 5)
        self.assertIsNone(self.r["piece"])
        self.assertIsNone(self.r["shako"])

    def test_a_stored_set_name_loads_as_its_pieces(self):
        for n in NAJ:
            self.assertIn(n, self.r["loaded"])
        self.assertNotIn("Naj's Ancient Vestige", self.r["loaded"])
        self.assertIn("Shako", self.r["loaded"])

    def test_the_door_splits_a_set_name(self):
        self.assertEqual(self.r["add"], SAZ)
        self.assertEqual(self.r["ownsSaz"], [True, True, True])
        self.assertFalse(self.r["ownsSet"])

    def test_each_piece_has_its_own_art_and_footprint(self):
        self.assertEqual(len(set(self.r["art"])), 3, self.r["art"])
        self.assertTrue(all(self.r["art"]), self.r["art"])
        self.assertNotEqual(self.r["size"][0], self.r["size"][2])

    def test_a_piece_joins_its_sisters_mule(self):
        self.assertEqual(self.r["sister"]["id"], "sets-rest", self.r["sister"])
        self.assertEqual(self.r["alone"]["id"], "sets-major", self.r["alone"])

    def test_an_overflowing_set_moves_together(self):
        w = self.r["where"]
        self.assertEqual(sorted(w), ["Set A", "Set B", "Set C"])
        self.assertEqual(len(set(w.values())), 1, w)


if __name__ == "__main__":
    unittest.main()
