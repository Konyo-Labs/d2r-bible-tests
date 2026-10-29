# -*- coding: utf-8 -*-
"""REG-3042 (#163, GrokBot on Dean's shadow 2026-10-29) - A CATALOGUE ITEM IS NEVER A MAGIC & RARE KEEPER, ANYWHERE.

Dean's saved records filed a set piece (Aldur's Rhythm) and a runeword (Enigma) on MAGIC & RARE. The file door has refused to
treat a catalogue item as a keeper since REG-2854 (a grail unique, a set piece or a runeword is drawn from the catalogue on its
own locker, never as a rolled name on MAGIC & RARE), but the live records derivation (REG-2853's keeper home), the dock, the
keeper home every locker asks (_mfKeeperHome) and the MAGIC & RARE window's pack only asked "is it in magicFinds". Measured in
node on Dean's shapes: a set piece registered in magicFinds was homed on MAGIC & RARE. Now one test, the door's three
(window._vaultCatalogueItem), is asked by each of them, and v1251's self-heal moves every catalogue item - not only a runeword -
out of the keeper track into the dock (owned, unfiled), keeping its read's provenance. A rolled-name keeper is untouched.

Driven on the whole page in node (vault_page_node), a fixture board (never his, never Dean's). RED_PROOF below.
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

RHY, KEEP, RW = "Aldur's Rhythm", "Brimstone Clasp", "Enigma"
#: rolled names that merely CONTAIN a catalogue word (the Grief runeword, Aldur's RHYTHM): keepers, never catalogue items
ROLLED = ("Grief Mark", "Rhythm Visage")
STORES = {
    "d2r_ownerClaim": "*", "d2r_ledgerName": "Fixture-Ledger",
    "d2r_owned": [KEEP],
    "d2r_muleAssign": {},
    "d2r_magicFinds": {RHY: {"q": "magic", "base": "Jagged Star", "sessionId": "s_1_1", "frameId": "f1", "at": 1},
                       KEEP: {"q": "rare", "base": "Amulet"},
                       RW: {"q": "rare", "base": "Archon Plate"},
                       ROLLED[0]: {"q": "rare", "base": "Bone Visage"}, ROLLED[1]: {"q": "rare", "base": "Bone Visage"}},
}
PRELUDE = "".join("localStorage.setItem(%s, %s);" % (json.dumps(k), json.dumps(v if isinstance(v, str) else json.dumps(v)))
                  for k, v in STORES.items())

BODY = r"""
(function(){
var RHY = %(rhy)s, KEEP = %(keep)s, RW = %(rw)s;
OUT.cat = [RHY, KEEP, RW, 'Harlequin Crest'].map(function(n){ return !!window._vaultCatalogueItem(n); });
var ROLLED = %(rolled)s;
/* BEFORE the self-heal (a shadow never runs it): the register still holds the catalogue items, and every caller of the one
   test must give each its own home */
OUT.pre = { pool: window.ownedPool().indexOf(RHY) >= 0, seam: window._vaultSeamHome(RHY), where: window._vaultWhereIs(RHY),
  route: (suggestMule(RHY) || {}).id, mrItems: window._vaultLockerItems('magic-rare'), setsItems: window._vaultLockerItems('sets-rest'),
  rec: (_vaultRecords().records || []).filter(function(x){ return x.name === RHY; }).map(function(x){ return x.kind + ':' + (x.mule || ''); }),
  dock: window.__dockNamesForLaw().indexOf(RHY) >= 0,
  stored: window.__reconcileForLaw([{ recId: RHY + '#0', name: RHY, copyIx: 0, kind: 'orphan', mule: null }]).map(function(x){ return x.kind + ':' + (x.mule || ''); }),
  rolled: ROLLED.map(function(n){ return [!!window._vaultCatalogueItem(n), window._vaultInMagicRare(n), window._mfKeeperHome(n), window._vaultSeamHome(n)]; }) };
try { renderVault(); } catch (e) { OUT.renderErr = String(e); }
var mf = JSON.parse(LSR.getItem('d2r_magicFinds') || '{}');
OUT.mfAfter = Object.keys(mf).sort();
OUT.ownedAfter = Array.from(owned).sort();
OUT.provRhy = JSON.parse(LSR.getItem('d2r_vaultProv') || '{}')[RHY] || null;
/* the register holds a catalogue name again (an older reader wrote it): every place that homes it must say no */
magicFinds[RHY] = { q: 'magic', base: 'Jagged Star' };
OUT.inMR = window._vaultInMagicRare(RHY);
OUT.keeperHome = window._mfKeeperHome(RHY) === undefined ? 'none' : window._mfKeeperHome(RHY);
OUT.keepHome = window._mfKeeperHome(KEEP);
var r = _vaultRecords();
OUT.recs = (r.records || []).map(function(x){ return x.name + ':' + x.kind + ':' + (x.mule || ''); }).sort();
var load = window._muleLoad([RHY, KEEP], {}, 'magic-rare');   /* both names handed in: the pack itself decides */
OUT.mrPack = JSON.stringify(load);
OUT.refuse = window.vaultAssign(KEEP, 'uni-small');
OUT.catFiles = window.vaultAssign(RHY, 'sets-rest');
})();
""" % {"rhy": json.dumps(RHY), "keep": json.dumps(KEEP), "rw": json.dumps(RW), "rolled": json.dumps(list(ROLLED))}
PATCHES = [("  window._vaultLockerItems = _vaultLockerItems;\n",
            "  window._vaultLockerItems = _vaultLockerItems;\n  window.__dockNamesForLaw = _dockNames; window.__reconcileForLaw = _vaultReconcileHomes;\n", 1)]

_RUN = {}


def page():
    if "o" not in _RUN:
        _RUN["o"] = VPN.run(BODY, prelude=PRELUDE, patches=PATCHES, timeout=300)
    return _RUN["o"]


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class ACatalogueItemIsNeverAMagicRareKeeper(unittest.TestCase):

    def test_the_premise_the_board_boots_and_knows_which_names_are_catalogue_items(self):
        o = page()
        self.assertEqual(o["__boot"]["errors"], [], o["__boot"])
        self.assertNotIn("renderErr", o, o.get("renderErr"))
        self.assertEqual(o["cat"], [True, False, True, True], "the one catalogue test answers %r" % o["cat"])

    def test_the_self_heal_moves_every_catalogue_item_to_the_dock_and_keeps_a_keeper(self):
        o = page()
        self.assertEqual(o["mfAfter"], sorted([KEEP] + list(ROLLED)), "the keeper track is not exactly its keepers: %r" % o["mfAfter"])
        self.assertIn(RHY, o["ownedAfter"]); self.assertIn(RW, o["ownedAfter"])
        self.assertEqual((o["provRhy"] or {}).get("frameId"), "f1", "the read's provenance was not kept: %r" % o["provRhy"])
        self.assertEqual(o["provRhy"].get("by"), "Magic & Rare catalogue item migration")

    def test_no_place_homes_a_catalogue_item_on_magic_rare(self):
        o = page()
        self.assertFalse(o["inMR"], "the Magic & Rare membership test took a set piece")
        self.assertEqual(o["keeperHome"], "none", "a set piece got a keeper home: %r" % o["keeperHome"])
        self.assertEqual(o["keepHome"], "magic-rare", "PREMISE: a rolled-name keeper lost its home")
        self.assertNotIn(RHY + ":filed:magic-rare", o["recs"], "the records derivation homed a set piece on MAGIC & RARE")
        self.assertNotIn(RHY, o["mrPack"], "the MAGIC & RARE window packs a set piece")
        self.assertIn(KEEP, o["mrPack"], "PREMISE: the MAGIC & RARE window no longer packs its keeper")

    def test_a_rolled_name_that_contains_a_catalogue_word_stays_a_keeper(self):
        for name, (cat, in_mr, home, seam) in zip(ROLLED, page()["pre"]["rolled"]):
            self.assertFalse(cat, "%s was taken for a catalogue item" % name)
            self.assertTrue(in_mr, "%s left the Magic & Rare keepers" % name)
            self.assertEqual(home, "magic-rare", "%s lost its keeper home" % name)
            self.assertIsNone(seam, "%s is homed off MAGIC & RARE by the seam: %r" % (name, seam))

    def test_every_caller_gives_a_register_held_catalogue_item_its_own_home(self):
        p = page()["pre"]
        self.assertTrue(p["pool"], "the pool does not carry a catalogue item the register holds - it is drawn nowhere")
        self.assertEqual(p["route"], "sets-rest", "PREMISE: the router's home for the set piece moved")
        self.assertEqual((p["seam"] or {}).get("mule"), "sets-rest", "the seam gives it %r" % p["seam"])
        self.assertEqual(p["rec"], ["filed:sets-rest"], "the live records home it %r" % p["rec"])
        self.assertEqual(p["stored"], ["filed:sets-rest"], "a stored orphan row of it is homed %r" % p["stored"])
        self.assertNotEqual((p["where"] or {}).get("mule"), "magic-rare", "FIND places it on MAGIC & RARE: %r" % p["where"])
        self.assertIn((p["where"] or {}).get("mule"), ("sets-rest", None), p["where"])
        self.assertNotIn((p["where"] or {}).get("kind"), ("orphan", "none", None), "FIND says it has no home: %r" % p["where"])
        self.assertGreaterEqual(p["setsItems"], 1, "SETS-REST does not list it")
        self.assertFalse(p["dock"], "it waits in the dock although its router home can hold it")

    def test_the_file_door_still_keeps_a_keeper_on_its_locker_and_files_a_catalogue_item(self):
        o = page()
        r = o["refuse"]
        self.assertFalse(r["ok"]); self.assertEqual(r["refused"], "magic-rare-keeper", r)
        self.assertNotEqual((o["catFiles"] or {}).get("refused"), "magic-rare-keeper", o["catFiles"])


RED_PROOF = [
    {"why": "REG-3042 - the Magic & Rare membership test takes a catalogue item again",
     "file": "bible.html",
     "find": "Object.prototype.hasOwnProperty.call(magicFinds, n) && !(typeof _vaultCatalogueItem === 'function' && _vaultCatalogueItem(n)); }\n",
     "replace": "Object.prototype.hasOwnProperty.call(magicFinds, n); }\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3042 - a catalogue item gets a keeper home",
     "file": "bible.html",
     "find": "    if (typeof window._vaultCatalogueItem === 'function' && window._vaultCatalogueItem(name)) return undefined;\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3042 - the self-heal moves only runewords",
     "file": "bible.html",
     "find": "          if (_vaultCatalogueItem(_mfk)){\n",
     "replace": "          if (window.findRuneword(_mfk)){\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3042 - the MAGIC & RARE window packs every register name",
     "file": "bible.html",
     "find": "_spanOf, n) && !(typeof _vaultCatalogueItem === 'function' && _vaultCatalogueItem(n))) _spanOf[n] = 1;",
     "replace": "_spanOf, n)) _spanOf[n] = 1;",
     "matches": 1, "needs": "node"},
    {"why": "REG-3042 - the one catalogue test knows only runewords, as v1251's self-heal did",
     "file": "bible.html",
     "find": "  function _vaultCatalogueItem(n){ return _vaIsGrailUni(n) || !!(typeof findSetPiece === 'function' && findSetPiece(n)) || _vaIsRW(n); }\n",
     "replace": "  function _vaultCatalogueItem(n){ return _vaIsRW(n); }\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3042 - the pool does not carry a catalogue item the register holds, so it is drawn nowhere",
     "file": "bible.html",
     "find": "          Object.keys(magicFinds).forEach(function(n){ if (n && !owned.has(n) && _vaultCatalogueItem(n) && _vaultKeeps(n)) p.push(n); });\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3042 - the catalogue test matches a WORD of a rolled name (Grief Mark reads as the runeword Grief)",
     "file": "bible.html",
     "find": "  function _vaultCatalogueItem(n){ return _vaIsGrailUni(n) || !!(typeof findSetPiece === 'function' && findSetPiece(n)) || _vaIsRW(n); }\n",
     "replace": "  function _vaultCatalogueItem(n){ return _vaIsGrailUni(n) || !!(typeof findSetPiece === 'function' && findSetPiece(n)) || _vaIsRW(n) || String(n).split(' ').some(function(w){ return _vaIsRW(w); }); }\n",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main()
