# -*- coding: utf-8 -*-
"""REG-2850 - THE MAGIC & RARE WINDOW DRAWS EVERY ITEM ITS CARD COUNTS.

His report, 2026-10-28 19:31 (the ALT's shadow on v3829, two screenshots): the MAGIC & RARE locker card said 23; its window
said "Items 23 · Copies 5" and its stash grid drew 5 tiles - "its not showing the 23 items at all when i click the alt mule
it self". Measured on the whole page in node (tv/vault_page_node.py - never a browser on his Mac) with his report's shape:
  * the keepers of Magic & Rare (d2r_magicFinds) are rolled names no catalogue holds, so ownedPool leaves them out and no
    vault record is ever homed on magic-rare for one - owned or not. Owning a keeper (REG-2830's throw-out keep, the AI Item
    Checker, the photo intake) does not make it a record, so the brief's lead ("old keeps were never owned") is not the
    cause: the owned keepers here were missing from the window too;
  * the census (_vaultLockerItems) and the card count and draw every keeper, but the window's packer (_muleLoad) skipped
    every name its records span did not hold (v3767), so it drew only the records: here 11 counted, 2 packed, and FIND
    named no cell for any of the 9 keepers.
Now the packer packs each keeper the span lacks the way its card cell is drawn - one copy - whichever door kept it (the
throw-out review, the AI checker's judge and its border hold, the photo intake, a legacy record: one rule, in the packer, for
all of them). It writes nothing, so a shadow (#207: the owner's records store rides in the upload without its stamp, so the
shadow rebuilds) packs exactly what the owner's own screen packs; both are driven here, and the window's open is read for
writes. Where a keeper packs - its footprint - is the router's (ACT-3), not this law's.

REG-2853 (the sweep): a keeper the owned pool does hold - a TV stub he also kept - was a record of kind orphan, so the
vault header called it "with no home (owned, on no mule and not in the unsorted dock)" (#204 counted five on the ALT). Its
record is homed on MAGIC & RARE now (a real mule filing still wins), a stored orphan row of one takes that home on load,
and the card draws it once, as its keeper cell. RED_PROOF below.
"""
import json
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
import vault_page_node as VPN  # noqa: E402

# The keepers, one of each door's shape (fixture names, never his). REG-2964 integration: no charm - his 2026-10-28 ruling
# (REG-2895) homes every charm off MAGIC & RARE, so the magic keepers here are jewels and an amulet:
KEEPERS = {
    "Grim Spiral (rare)": {"q": "rare", "base": ""},                      # the throw-out review's keep, before REG-2830: not owned
    "Bitter Noose": "rare",                                              # a legacy record (a bare quality string)
    "Stone Knot": {"q": "rare", "base": "Ring", "mods": [], "frameId": "f1", "sessionId": "s1", "at": 1},   # the photo intake, owned
    "Garnet Jewel of Fervor": {"q": "magic", "base": "Jewel", "mods": [], "border": True},                 # the judge's border hold
    "Ruby Jewel of Fervor": {"q": "magic", "base": "Jewel", "mods": [], "border": True},                   # owned AND a TV stub
    "Shadow Hold": {"q": "rare", "base": "Ring", "mods": [], "border": True},
    "Bone Clasp": {"q": "rare", "base": "Plated Belt", "mods": [], "frameId": "f2", "sessionId": "s1", "at": 2},  # owned
    "Rune Eye": {"q": "rare", "base": ""},
    "Chaos Whorl": {"q": "rare", "base": ""},
}
# TV stubs (d2r_tvExtraItems: rarity 'basic', base = the name itself). The two not in Magic & Rare are routed there by the
# rolled-name grammar and so are the locker's records; the third is a keeper too (the orphan shape his ALT holds five of).
STUBS = ["Doom Eye", "Ruby Amulet of Balance", "Ruby Jewel of Fervor"]
RECORDS = ["Doom Eye", "Ruby Amulet of Balance"]
KEPT_STUB = "Ruby Jewel of Fervor"     # owned, a TV stub and a keeper: its record is homed on the locker (REG-2853)
OWNED = ["Stone Knot", "Ruby Jewel of Fervor", "Bone Clasp"] + RECORDS
ALL = sorted(set(KEEPERS) | set(RECORDS))


def _stub(n):
    return {"rarity": "basic", "base": n, "cat": "TV-vaulted", "val": "tv", "desc": "fixture"}


def _prelude(shadow, records=None):
    st = {"d2r_magicFinds": KEEPERS, "d2r_tvExtraItems": {n: _stub(n) for n in STUBS}, "d2r_owned": OWNED}
    pre = "localStorage.setItem('d2r_ownerClaim', '*');\n"
    pre += "".join("localStorage.setItem(%s, %s);\n" % (json.dumps(k), json.dumps(json.dumps(v))) for k, v in st.items())
    if records is not None:
        # the owner's records store rides in the upload; its migrate stamp does not, so the shadow rebuilds (#207)
        pre += "localStorage.setItem('d2r_vaultRecords', %s);\n" % json.dumps(records)
    if shadow:
        # a shadow is read only (the boot block's memory store and LSR's guard): the page's own writers stand down on it
        pre += "window._tvdShadow = { owner: 'fixture', t: 1, mem: null };\n"
    return pre


BODY = r"""
(function(){
var W = window, MR = 'magic-rare', STORES = ['d2r_owned', 'd2r_magicFinds', 'd2r_copies', 'd2r_muleAssign', 'd2r_vaultProv',
    'd2r_vaultRecords', 'd2r_mulePos', 'd2r_unknownReads', 'd2r_tvExtraItems'];
/* the owner's page arms the persisted records store after load (the seed cleanse's chain); a shadow never does and
   rebuilds from the uploaded stores (#207) - so the owner reads the stamped store and the shadow the live derivation */
if (!W._tvdShadow) { var _arm = W._vaultRecordsArm(); OUT.arm = !!(_arm && (_arm.stamped || _arm.already)); }
OUT.stored = H.RAW.has('d2r_vaultRecords') ? H.RAW.get('d2r_vaultRecords') : null;
OUT.stamped = H.RAW.has('d2r_vaultRecordsMigrate');
try { W.renderVault(); } catch (e) { OUT.renderErr = String(e && e.message || e); }
H.flush(60, 3);
OUT.census = W._vaultLockerItems(MR);
OUT.recordsSpan = W._vaultRecordsForMule(MR);
var names = W._muleNamesFor(MR), L = W._muleLoad(names, {}, MR), drawn = {}, foot = {};
(L.mules || []).forEach(function(m){
  var all = (m.stash || []).concat(m.inv || []);
  Object.keys(m.tabs || {}).forEach(function(k){ all = all.concat(m.tabs[k] || []); });
  all.forEach(function(p){ drawn[p.n] = (drawn[p.n] || 0) + 1; foot[p.n] = [p.w, p.h]; });
});
OUT.drawn = drawn; OUT.foot = foot; OUT.phys = L.phys; OUT.rem = (L.rem || []).length;
/* the card: its cells */
var shelf = String((document.getElementById('vault-shelf') || {}).innerHTML || '');
var at = shelf.indexOf('data-vault-mule="' + MR + '"'), nx = at < 0 ? -1 : shelf.indexOf('data-vault-mule="', at + 10);
var card = at < 0 ? '' : shelf.slice(at, nx < 0 ? shelf.length : nx);
OUT.cardCells = (card.match(/class="vm-cell[ "]/g) || []).length;
/* the window: what its head and its calculations print, and what opening it wrote */
var setsBefore = {}; STORES.forEach(function(k){ setsBefore[k] = H.ls.byKeySet[k] || 0; });
var rawBefore = {}; STORES.forEach(function(k){ rawBefore[k] = H.RAW.has(k) ? H.RAW.get(k) : null; });
try { W.openMuleCard(MR); } catch (e) { OUT.openErr = String(e && e.message || e); }
H.flush(60, 3);
var det = String((document.getElementById('vault-detail') || {}).innerHTML || '');
var txt = det.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
var mi = /Items in this locker (\d+) Copies \(physical\) (\d+)/.exec(txt);
OUT.calc = mi ? [+mi[1], +mi[2]] : null;
OUT.winTiles = {};
det.replace(/class="vd-item[^"]*" style="[^"]*" title="([^"]*?) \((\d+)×(\d+)\)/g, function(_, n, w, h){
  n = n.replace(/&#39;/g, "'").replace(/&amp;/g, '&'); OUT.winTiles[n] = (OUT.winTiles[n] || 0) + 1; return _; });
OUT.wrote = STORES.filter(function(k){ return (H.ls.byKeySet[k] || 0) !== setsBefore[k] || (H.RAW.has(k) ? H.RAW.get(k) : null) !== rawBefore[k]; });
/* FIND: the cell it names for each item */
OUT.find = {};
names.forEach(function(n){ var w = W._vaultWhereIs(n); OUT.find[n] = w ? [w.kind, w.cell] : null; });
OUT.shadow = !!W._tvdShadow;
/* REG-2853: the kept stub's record, the header's homeless count, and its cells on the card */
var R = W._vaultRecordsSource(), KS = %s;
OUT.ksRec = (R.records || []).filter(function(r){ return r && r.name === KS; }).map(function(r){ return [r.kind, r.mule]; });
var hd = W._vaultRecordsHeader(); OUT.head = hd ? { orphans: hd.orphans, noHome: hd.orphansNoHome } : null;
OUT.ksCells = [card.split('data-magic-find="' + KS + '"').length - 1, card.split('data-vault-item="' + KS + '"').length - 1];   /* [keeper cells, record cells] */
/* a records store written before REG-2853 holds the kept stub as an orphan row: the load takes the locker's home */
if (!W._tvdShadow && OUT.stored){
  var obj = JSON.parse(H.RAW.get('d2r_vaultRecords'));
  obj.records.forEach(function(r){ if (r && r.name === KS) { r.kind = 'orphan'; r.mule = null; r.loc = null; } });
  W.LSR.setItem('d2r_vaultRecords', JSON.stringify(obj));
  var ld = W._vaultRecordsLoad();
  OUT.ksLoaded = (ld && ld.records || []).filter(function(r){ return r && r.name === KS; }).map(function(r){ return [r.kind, r.mule]; });
}
OUT.errors = H.errors.slice();
})();
""" % json.dumps(KEPT_STUB)


class MagicAndRareDrawsEveryItemItCounts(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not VPN.NODE:
            raise AssertionError("node is not on this machine - this law does not skip")
        cls.o = VPN.run(BODY, prelude=_prelude(False), timeout=300)
        cls.s = VPN.run(BODY, prelude=_prelude(True, cls.o.get("stored")), timeout=300)

    def test_the_page_booted(self):
        for o in (self.o, self.s):
            self.assertEqual(o["__boot"]["errors"], [], o["__boot"])
            self.assertNotIn("renderErr", o, o.get("renderErr"))
            self.assertNotIn("openErr", o, o.get("openErr"))
            self.assertEqual(o["errors"], [])
        self.assertTrue(self.s["shadow"] and not self.o["shadow"], "PREMISE: the two runs are not an owner and a shadow")
        self.assertTrue(self.o.get("arm") and self.o["stored"] and self.o["stamped"], "PREMISE: the owner's records store was not armed: %r" % self.o.get("arm"))
        self.assertTrue(self.s["stored"] and not self.s["stamped"],
                        "PREMISE: the shadow does not hold the owner's records store without its stamp (#207's rebuild)")

    def test_the_premise_is_his_report(self):
        o = self.o
        # REG-2971 (#202 P3b): every keeper is a record now, homed on MAGIC & RARE by the keeper rule - so the locker's records
        # are every keeper and the two routed stubs (before it, only the routed stubs and the kept stub had one)
        self.assertEqual(sorted(o["recordsSpan"] or {}), ALL,
                         "PREMISE: the locker's records are not every keeper and the two routed stubs: %r" % o["recordsSpan"])
        self.assertEqual(o["census"], len(ALL), "PREMISE: the census does not count every keeper and record: %r" % o["census"])
        self.assertEqual(o["cardCells"], len(ALL), "PREMISE: the card does not draw every keeper and record: %r" % o["cardCells"])

    def test_the_window_draws_every_item_the_card_counts(self):
        o = self.o
        self.assertEqual(sorted(o["drawn"]), ALL, "the window packs %r of the %d items its card counts" % (sorted(o["drawn"]), len(ALL)))
        self.assertEqual(sorted(o["winTiles"]), ALL, "the window's stash grid draws %r" % sorted(o["winTiles"]))
        self.assertEqual(o["calc"], [len(ALL), len(ALL)], "the window says items / copies %r, the card %d cells" % (o["calc"], o["cardCells"]))
        self.assertEqual(o["phys"], o["cardCells"], "the window packs %r copies and the card draws %r cells" % (o["phys"], o["cardCells"]))
        self.assertEqual(o["rem"], 0, o)

    def test_find_names_a_cell_for_every_keeper(self):
        bad = {n: self.o["find"].get(n) for n in KEEPERS if not (self.o["find"].get(n) and self.o["find"][n][0] == "filed" and self.o["find"][n][1])}
        self.assertEqual(bad, {}, "FIND names no cell for these keepers in MAGIC & RARE: %r" % bad)
        # the routed records were found before the fix too ('would': the seam's home, assign not written) - the control
        self.assertTrue(all((self.o["find"].get(n) or [None, None])[1] for n in RECORDS), self.o["find"])

    def test_a_kept_stub_is_homed_on_magic_and_rare_never_homeless(self):
        for o in (self.o, self.s):
            self.assertEqual(o["ksRec"], [["filed", "magic-rare"]], "the kept stub's record is %r (shadow %r)" % (o["ksRec"], o["shadow"]))
            self.assertEqual(o["head"], {"orphans": 0, "noHome": 0}, "the header calls a Magic & Rare keeper homeless: %r" % o["head"])
            self.assertEqual(o["ksCells"], [1, 0], "the card draws the kept stub as [keeper, record] cells %r" % o["ksCells"])

    def test_a_stored_orphan_row_of_a_keeper_takes_the_lockers_home(self):
        self.assertEqual(self.o.get("ksLoaded"), [["filed", "magic-rare"]],
                         "a records store written before the fix keeps the kept stub homeless: %r" % self.o.get("ksLoaded"))

    def test_the_shadow_draws_what_the_owner_draws(self):
        o, s = self.o, self.s
        for k in ("census", "drawn", "foot", "phys", "calc", "winTiles", "find", "ksRec", "head"):
            self.assertEqual(s[k], o[k], "the shadow's %s is %r, the owner's %r" % (k, s[k], o[k]))

    def test_opening_the_window_writes_nothing(self):
        self.assertEqual(self.o["wrote"], [], "opening the MAGIC & RARE window wrote %r on the owner's board" % self.o["wrote"])
        self.assertEqual(self.s["wrote"], [], "opening the MAGIC & RARE window wrote %r in a shadow" % self.s["wrote"])


RED_PROOF = [
    {"why": "REG-2853 - a kept stub falls through to orphan again (the header calls it homeless)",
     "file": "bible.html",
     "find": "        else if (typeof window._vaultInMagicRare === 'function' && window._vaultInMagicRare(name) && typeof muleById === 'function' && muleById('magic-rare')) { kind = 'filed'; mid = 'magic-rare'; }   /* REG-2853 keeper home */\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2853 - a stored orphan row of a keeper stays homeless on load",
     "file": "bible.html",
     "find": "&& typeof muleById === 'function' && muleById('magic-rare')) { r.kind = 'filed'; r.mule = 'magic-rare'; r.loc = 'magic-rare'; return; }   /* REG-2853 stored keeper */",
     "replace": "&& false) { r.kind = 'filed'; r.mule = 'magic-rare'; r.loc = 'magic-rare'; return; }",
     "matches": 1, "needs": "node"},
    {"why": "REG-2853 - the card draws a homed keeper twice (a record cell beside its keeper cell)",
     "file": "bible.html",
     "find": "        items = items.filter(function(n){ return !Object.prototype.hasOwnProperty.call(magicFinds, n); });   /* REG-2853 one cell */\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2850 - the packer skips every keeper again (the window draws only the records: 2 of 11)",
     "file": "bible.html",
     "find": "        if (n && !Object.prototype.hasOwnProperty.call(_spanOf, n) && !(typeof _vaultCatalogueItem === 'function' && _vaultCatalogueItem(n))) _spanOf[n] = 1;   /* REG-2850 keeper span; REG-3042 never a catalogue item */\n",
     "replace": "        void 0;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2850 - the draw owns the keepers as it packs them (a migration in a paint): the window's open writes",
     "file": "bible.html",
     "find": "        if (n && !Object.prototype.hasOwnProperty.call(_spanOf, n) && !(typeof _vaultCatalogueItem === 'function' && _vaultCatalogueItem(n))) _spanOf[n] = 1;   /* REG-2850 keeper span; REG-3042 never a catalogue item */\n",
     "replace": "        if (n && !Object.prototype.hasOwnProperty.call(_spanOf, n)) { _spanOf[n] = 1; try { localStorage.setItem('d2r_owned', JSON.stringify(Array.from(owned).concat([n]))); } catch (eW) {} }\n",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
