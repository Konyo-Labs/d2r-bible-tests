# -*- coding: utf-8 -*-
"""v3767 — #76 one record, one location, and #77 mule spread.

Elad, 2026-10-18 13:18 IDT: duplicate copies of a vault item sit next to the
original in the SAME mule. This replaces rule E (2 in shared, the 3rd+ in
GRAIL-DUPES). Every physical copy is one record on the category mule of its
original. The greedy packer keeps a same-name group together and overflows the
whole group to the next mule of that category only when the group does not fit.
A group bigger than an empty mule places what fits. Copies already stored in
GRAIL-DUPES re-home through the records-seam route home. No record is dropped
and no record is duplicated.

The functions are extracted from bible.html and run in node. A missing node raises.
RED_PROOF below. [[heart-first]] [[the-unjoined-end]] [[unknown-stays-unknown]] [[regression-guard]]
"""
import json
import os
import re
import shutil
import subprocess
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

BIBLE = os.path.join(HERE, "..", "bible.html")
NODE = os.environ.get("NODE") or shutil.which("node")

FNS = [
    "_vaultSameItemNames", "_dockNames", "_vaultRouteHome", "_vaultPresenceSpan", "_mkWant",
    "_vaultRecords", "_vaultRecordsSource", "_vrSourceChoice", "_vaultRecordsFind", "_vrRecHome",
    "_vaultRecordHome", "_vaultRecordsForMule", "_vaultNamesByMule", "_muleNamesFor",
    "_vaultSpread", "packGrid", "_muleLoad", "_vaultPlanCis", "_vaultPlanCell", "_vaultPopFromHeader",
    "_vaultAuditKeep", "_vaultAudit", "_vrLocForCopy",
]
ASSIGNED = ["vaultRemove", "tvVaultRegister"]


def _fn(src, name):
    m = re.search(r"\bfunction %s\s*\(" % re.escape(name), src)
    if not m:
        raise AssertionError("could not find function %s in bible.html" % name)
    i = src.index("{", m.start())
    depth, j = 0, i
    while j < len(src):
        c = src[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return src[m.start():j + 1]
        j += 1
    raise AssertionError("unbalanced braces extracting %s" % name)


def _assigned_fn(src, name):
    m = re.search(r"window\.%s\s*=\s*function\s*\(" % re.escape(name), src)
    if not m:
        raise AssertionError("could not find window.%s" % name)
    i = src.index("{", m.start())
    depth, j = 0, i
    while j < len(src):
        c = src[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return src[m.start():j + 1]
        j += 1
    raise AssertionError("unbalanced braces extracting window.%s" % name)


def _line_has(src, needle):
    for line in src.splitlines():
        if needle in line:
            return line
    raise AssertionError("missing line %r" % needle)


PREAMBLE = r"""
var window = globalThis;
window._vaultNotAnItem = function(){ return null; };   /* REG-2663 (#209, v3813): not this law's question */
window.D2R_PROFILE = 'main';
var BARE = "Natalya's Totem";
var SLOT = "Natalya's Totem (helm)";
var ENIGMA = "Enigma";
var SHAKO = "Shako";
var GHOST = "Ghost Blade";
var WIND = "Windforce";
function _vfCanon(n){
  if (n === BARE || n === SLOT) return SLOT;
  return n;
}
function _vfIsSetPiece(n){ return n === BARE || n === SLOT; }
window._vfCanon = _vfCanon;
window._vfIsSetPiece = _vfIsSetPiece;
var multiKeep = {};
var owned = new Set();
var assign = {};
var magicFinds = {};
var unknownReads = new Set();
var SUGGEST = null;
var FILED = [];
function ownedPool(){ return Array.from(owned).filter(function(n){ return !_inMagicRare(n); }).sort(); }
function copyCount(n){
  if (n === ENIGMA) return 4;
  if (n === SHAKO) return 2;
  return 1;
}
function isSharedStash(){ return false; }
function _inMagicRare(n){ return !!(magicFinds && magicFinds[n]); }
function _sharedNames(){
  return Object.keys(assign).filter(function(n){ return assign[n] === 'shared'; }).sort();
}
function muleById(id){
  var known = { shared: 'SHARED STASH', 'sets-rest': 'SETS-REST', 'uni-armor': 'UNI-ARMOR', 'uni-weap': 'UNI-WEAPONS' };
  return known[id] ? { id: id, name: known[id], icon: '' } : null;
}
function suggestMule(){ return SUGGEST; }
window._carriedNames = function(){ return []; };
function vaultSize(){ return [1, 1]; }
function tipOf(){ return null; }
function _mpInvSeeds(){ return { hold: {}, at: {}, bad: [], n: 0 }; }
function _muleItemKey(n, ci){ return ci ? n + ' #' + (ci + 1) : n; }
function _mulePosAll(){ return {}; }
var MULE_AREAS = {
  personal: [10, 10, 'Personal'], shared: [10, 10, 'Shared'], gems: [10, 10, 'Gems'],
  materials: [10, 10, 'Materials'], runes: [10, 10, 'Runes'], inv: [10, 4, 'Inventory']
};
function _muleName(id){ var m = muleById(id); return m ? m.name : String(id); }
function _vaStoreLabel(k){ return k; }
function _vaIsRW(){ return false; }
function _vaIsGrailUni(){ return false; }
function _mfChecker(){ return null; }
function _vaG3Filled(){ return {}; }
function _vaProvenance(){ return ''; }
function persistOwned(){}
function saveA(){}
function renderVault(){}
function refreshOpenCard(){}
function status(){}
function _provAll(){ return {}; }
function _provDrop(){}
function _vrRead(){ return []; }
function _vrWrite(){}
function _vNoHomeWhy(){ return 'no home'; }
window._repaintOwned = function(){};
window._vaultResolveName = function(n){ return String(n == null ? '' : n).trim(); };
window._ownedAdd = function(n){ if (n) owned.add(n); };
window.vaultFile = function(name, w, o){
  var mule = o && o.mule;
  FILED.push({ name: name, mule: mule });
  if (mule) assign[name] = mule;
  return { ok: true, mule: mule };
};
var document = {
  getElementById: function(){ return null; },
  querySelector: function(){ return null; }
};
function setPieceWorld(){
  owned.clear();
  Object.keys(assign).forEach(function(k){ delete assign[k]; });
  [BARE, SLOT, ENIGMA, SHAKO, 'Nagelring'].forEach(function(n){ owned.add(n); });
  assign[SLOT] = 'sets-rest';
  assign[ENIGMA] = 'shared';
  assign[SHAKO] = 'uni-armor';
}
function placedNames(load){
  var names = [];
  (load.mules || []).forEach(function(m){
    (m.stash || []).concat(m.inv || []).forEach(function(p){ if (p && p.n) names.push(p.n); });
  });
  return names;
}
"""


class TestV3767VaultSpread(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not NODE:
            raise AssertionError("node is not on this machine — this law does not skip")
        with open(BIBLE, encoding="utf-8") as f:
            cls.src = f.read()
        from test_v3767_copy_witness import look_rule   # #201 - the one rule the sight groups ask
        cls.bundle = look_rule(cls.src) + "\n" + "\n".join(_fn(cls.src, n) for n in FNS)
        cls.bundle += "\n" + "\n".join(_assigned_fn(cls.src, n) for n in ASSIGNED)
        cls.dims = "\n".join([
            _line_has(cls.src, "var MULE_STASH_W = 10"),
            _line_has(cls.src, "var MULE_INV_W = 10"),
            _line_has(cls.src, "var MULE_CAP = "),
            _line_has(cls.src, "var _MULE_COPY_CAP = 3"),
        ])

    def _run(self):
        prog = (
            PREAMBLE + "\n" + self.dims + "\n" + self.bundle + r"""
var out = {};
setPieceWorld();
var rec = _vaultRecords();
out.index = Object.keys(rec.index).sort();
out.nat = rec.records.filter(function(r){ return r.name === BARE || r.name === SLOT; }).map(function(r){
  return { name: r.name, kind: r.kind, mule: r.mule };
});
out.dock = _dockNames();
out.findBare = _vaultRecordsFind(BARE);
out.findSlot = _vaultRecordsFind(SLOT);
out.armor = _muleNamesFor('uni-armor');
out.shared = _muleNamesFor('shared');
var load = _muleLoad([SHAKO, GHOST], null, 'uni-armor', {});
out.viaSpread = !!(load.mules && load.mules.viaSpread);
out.placed = placedNames(load);
out.loc0 = _vrLocForCopy('sharedStash', null, 0);
out.loc1 = _vrLocForCopy('sharedStash', null, 1);
out.loc2 = _vrLocForCopy('sharedStash', null, 2);
out.routeNull = _vaultRouteHome(null);
out.routeUnsorted = _vaultRouteHome({ id: null, unsorted: true, why: 'unknown' });
out.routeArmor = _vaultRouteHome({ id: 'uni-armor', why: 'plate' });
out.pop = _vaultPopFromHeader(
  { owned: 9, shared: 2, filed: 9, loose: 1, carried: 1, sp: 0, orphans: 0 },
  { owned: 5, shared: 99, filed: 4, loose: 1, carried: 0, orphans: 0 });
out.popUnk = _vaultPopFromHeader(
  { owned: 9, shared: 2, filed: 9, loose: 1, carried: 1, sp: 0, orphans: 1 },
  { owned: 5, filed: null, loose: null, carried: null, orphans: null });
var blades = [];
for (var bi = 0; bi < 16; bi++) blades.push({ n: 'Colossus Blade', key: 'b' + bi, w: 2, h: 4 });
var sp16 = _vaultSpread(blades, {}, -1);
out.mules16 = sp16.mules.length;
out.capStash = sp16.capStash;
out.capInv = sp16.capInv;
out.count0 = sp16.mules.length ? ((sp16.mules[0].stash || []).length + (sp16.mules[0].inv || []).length) : 0;
out.on2 = [];
if (sp16.mules.length > 1) {
  (sp16.mules[1].stash || []).concat(sp16.mules[1].inv || []).forEach(function(p){ out.on2.push(p.key); });
}
var hole = [];
for (var hx = 0; hx < 10; hx++) hole.push({ n: 'occ', x: hx, y: 0, w: 1, h: 9 });
var gap = _vaultSpread(
  [{ n: 'big', key: 'big', w: 2, h: 2 }, { n: 'tiny', key: 'tiny', w: 1, h: 1 }],
  { 0: { personal: hole } }, -1);
function pick(list, name){ return (list || []).some(function(p){ return p && p.n === name; }); }
out.tinyStash = pick(gap.mules[0] && gap.mules[0].stash, 'tiny');
out.bigStash = pick(gap.mules[0] && gap.mules[0].stash, 'big');
var occStash = [{ n: 'occ', x: 0, y: 0, w: 10, h: 9 }, { n: 'occ', x: 0, y: 9, w: 9, h: 1 }];
var occInv = [{ n: 'occ', x: 0, y: 0, w: 10, h: 4 }];
var pair = _vaultSpread(
  [{ n: 'Rune', key: 'r0', w: 1, h: 1 }, { n: 'Rune', key: 'r1', w: 1, h: 1 }],
  { 0: { personal: occStash, inv: occInv } }, -1);
function keysOf(m){
  var ks = [];
  ((m && m.stash) || []).concat((m && m.inv) || []).forEach(function(it){ if (it && it.key) ks.push(it.key); });
  return ks;
}
out.pair0 = keysOf(pair.mules[0]);
out.pair1 = keysOf(pair.mules[1]);
owned.clear();
Object.keys(assign).forEach(function(k){ delete assign[k]; });
owned.add(BARE); owned.add(SLOT);
assign[SLOT] = 'sets-rest';
assign[BARE] = 'uni-weap';
assign[WIND] = 'uni-weap';
SUGGEST = { id: 'sets-rest', why: 'set' };
out.mis = _vaultAudit().findings.filter(function(f){ return f.kind === 'misroute'; }).map(function(f){ return f.item; }).sort();
setPieceWorld();
var rm = window.vaultRemove([BARE], { quiet: true, why: 'one item' });
out.removed = (rm.removed || []).slice().sort();
out.stillOwned = Array.from(owned).sort();
out.slotAssigned = Object.prototype.hasOwnProperty.call(assign, SLOT);
FILED = [];
owned.clear();
Object.keys(assign).forEach(function(k){ delete assign[k]; });
SUGGEST = { id: 'uni-armor', why: 'plate' };
out.regArmor = window.tvVaultRegister('Archon Plate', { by: 'hand', at: '2026-10-18T00:00:00.000Z', where: 'the vault' });
out.filedArmor = FILED.slice();
FILED = [];
owned.clear();
Object.keys(assign).forEach(function(k){ delete assign[k]; });
SUGGEST = { id: null, unsorted: true, why: 'unknown' };
out.regLoose = window.tvVaultRegister('Mystery Bone', { by: 'hand', at: '2026-10-18T00:00:00.000Z', where: 'the vault' });
out.filedLoose = FILED.slice();
FILED = [];
owned.clear();
Object.keys(assign).forEach(function(k){ delete assign[k]; });
SUGGEST = { id: 'shared', why: 'war gear' };
out.regShared = window.tvVaultRegister('Grief', { by: 'hand', at: '2026-10-18T00:00:00.000Z', where: 'the vault' });
out.filedShared = FILED.slice();
FILED = [];
owned.clear();
Object.keys(assign).forEach(function(k){ delete assign[k]; });
SUGGEST = null;
out.regNull = window.tvVaultRegister('Ist rune', { by: 'hand', at: '2026-10-18T00:00:00.000Z', where: 'the vault' });
out.filedNull = FILED.slice();
process.stdout.write(JSON.stringify(out));
"""
        )
        p = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 0, (p.stderr or p.stdout)[-2000:])
        return json.loads(p.stdout)

    def test_one_record_one_home_and_the_mule_spread(self):
        o = self._run()
        self.assertEqual(o["nat"], [{"name": "Natalya's Totem (helm)", "kind": "filed", "mule": "sets-rest"}], o["nat"])
        self.assertNotIn("Natalya's Totem", o["index"], o["index"])
        self.assertEqual(o["findBare"], "sets-rest", o["findBare"])
        self.assertEqual(o["findSlot"], "sets-rest", o["findSlot"])
        self.assertNotIn("Natalya's Totem", o["dock"], o["dock"])
        self.assertIn("Nagelring", o["dock"], o["dock"])
        self.assertEqual(o["removed"], ["Natalya's Totem", "Natalya's Totem (helm)"], o["removed"])
        self.assertNotIn("Natalya's Totem (helm)", o["stillOwned"], o["stillOwned"])
        self.assertFalse(o["slotAssigned"], o["slotAssigned"])
        self.assertNotIn("Enigma", o["armor"], o["armor"])
        self.assertIn("Shako", o["armor"], o["armor"])
        self.assertIn("Enigma", o["shared"], o["shared"])
        self.assertTrue(o["viaSpread"], o["viaSpread"])
        self.assertNotIn("Ghost Blade", o["placed"], o["placed"])
        self.assertIn("Shako", o["placed"], o["placed"])
        self.assertEqual(o["loc0"], "shared", o["loc0"])
        self.assertEqual(o["loc1"], "shared", o["loc1"])
        self.assertEqual(o["loc2"], "shared", o["loc2"])
        self.assertEqual(o["pair0"], [], o["pair0"])
        self.assertEqual(o["pair1"], ["r0", "r1"], o["pair1"])
        self.assertEqual(o["mules16"], 2, o)
        self.assertEqual(o["count0"], 15, o)
        self.assertEqual(o["on2"], ["b15"], o["on2"])
        self.assertEqual(o["capStash"], 100, o["capStash"])
        self.assertEqual(o["capInv"], 40, o["capInv"])
        self.assertTrue(o["tinyStash"], o)
        self.assertFalse(o["bigStash"], o)
        self.assertEqual(o["pop"]["filed"], 4, o["pop"])
        self.assertEqual(o["pop"]["owned"], 5, o["pop"])
        self.assertEqual(o["pop"]["shared"], 2, o["pop"])
        self.assertIsNone(o["popUnk"]["filed"], o["popUnk"])
        self.assertEqual(o["mis"], ["Windforce"], o["mis"])
        self.assertFalse(o["routeNull"]["unsorted"], o["routeNull"])
        self.assertIsNone(o["routeNull"]["home"], o["routeNull"])
        self.assertTrue(o["routeUnsorted"]["unsorted"], o["routeUnsorted"])
        self.assertIsNone(o["routeUnsorted"]["home"], o["routeUnsorted"])
        self.assertEqual(o["routeArmor"]["home"], "uni-armor", o["routeArmor"])
        self.assertFalse(o["routeArmor"]["unsorted"], o["routeArmor"])
        self.assertEqual(o["filedArmor"], [{"name": "Archon Plate", "mule": "uni-armor"}], o["filedArmor"])
        self.assertEqual(o["filedLoose"], [], o["filedLoose"])
        self.assertEqual(o["filedShared"], [{"name": "Grief", "mule": "shared"}], o["filedShared"])
        self.assertEqual(o["filedNull"], [], o["filedNull"])
        self.assertIn("_vaultPopFromHeader(_sub76, _rh76)", self.src)
        self.assertIn("mule: sg.id", self.src)

    def test_copies_already_in_grail_dupes_rehome_onto_the_same_mule(self):
        names = [
            "_vaultRehomeCopies", "_vaultRecordsLoad", "_vrRecLoadRaw",
            "_vaultRouteHome", "_vaultRecordHome", "_vrLocForCopy",
        ]
        bundle = "\n".join(_fn(self.src, n) for n in names)
        prog = r"""
var window = globalThis;
var _VR_STORE_KEY = 'd2r_vaultRecords';
var _vrRecUnread = {};
var _LSRDATA = {};
window.LSR = {
  getItem: function(k){ return Object.prototype.hasOwnProperty.call(_LSRDATA, k) ? _LSRDATA[k] : null; },
  setItem: function(k, v){ _LSRDATA[k] = String(v); },
  removeItem: function(k){ delete _LSRDATA[k]; }
};
""" + bundle + r"""
var rows = [
  { recId: 'rec_1', name: 'Grief', copyIx: 0, kind: 'sharedStash', mule: null, loc: 'shared' },
  { recId: 'rec_2', name: 'Grief', copyIx: 1, kind: 'sharedStash', mule: null, loc: 'dupes' },
  { recId: 'rec_3', name: 'Grief', copyIx: 2, kind: 'sharedStash', mule: null, loc: 'dupes' },
  { recId: 'rec_4', name: 'Archon Plate', copyIx: 0, kind: 'filed', mule: 'uni-armor', loc: 'dupes' },
  { recId: 'rec_5', name: 'Shako', copyIx: 0, kind: 'filed', mule: 'uni-armor', loc: 'uni-armor' }
];
window.LSR.setItem('d2r_vaultRecords', JSON.stringify({ v: 1, records: rows }));
var loaded = _vaultRecordsLoad();
var again = _vaultRecordsLoad();
var out = {
  n: loaded.records.length,
  ids: loaded.records.map(function(r){ return r.recId; }),
  locs: loaded.records.map(function(r){ return r.loc; }),
  again: again.records.map(function(r){ return r.loc; })
};
process.stdout.write(JSON.stringify(out));
"""
        p = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 0, (p.stderr or p.stdout)[-2000:])
        o = json.loads(p.stdout)
        self.assertEqual(o["n"], 5, o)
        self.assertEqual(o["ids"], ["rec_1", "rec_2", "rec_3", "rec_4", "rec_5"], o["ids"])
        self.assertEqual(o["locs"], ["shared", "shared", "shared", "uni-armor", "uni-armor"], o["locs"])
        self.assertEqual(o["again"], o["locs"], o)

    def test_distinct_attacks_clear_the_vault_apply_wilson_bar(self):
        from confidence import confluence, wilson_lower
        import self_arming as SA
        bar = SA.LOCKS["vault.apply"]["bar"]
        kinds_bar = SA.LOCKS["vault.apply"]["kinds_bar"]
        n = len(RED_PROOF)
        w = wilson_lower(n, n)
        conf = confluence(["sabotage"], SA.KINDS)
        msg = ("vault spread: %d distinct attacks, wilson %.4f vs vault.apply bar %.3f; "
               "kinds sabotage %.2f vs %.2f" % (n, w, bar, conf, kinds_bar))
        print(msg)
        self.assertGreaterEqual(n, 12, msg)
        self.assertGreaterEqual(w, bar, msg)
        self.assertLess(conf, kinds_bar,
                        "one sabotage family must not read as enough to open the write door")


RED_PROOF = [
    {
        "why": "Sixteen 2x4 blades need a second mule. Stopping the spread after one page leaves the 16th unplaced.",
        "file": "bible.html",
        "find": "++_spreadGuard < 80",
        "replace": "++_spreadGuard < 1",
        "matches": 1,
    },
    {
        "why": "A personal stash tab is 100 cells. Reporting 1 makes the capacity a label instead of the grid.",
        "file": "bible.html",
        "find": "capStash: MULE_STASH_W * MULE_STASH_H",
        "replace": "capStash: 1",
        "matches": 1,
    },
    {
        "why": "A character inventory is 40 cells. Reporting 1 hides the 10 by 4 grid.",
        "file": "bible.html",
        "find": "capInv: MULE_INV_W * MULE_INV_H",
        "replace": "capInv: 1",
        "matches": 1,
    },
    {
        "why": "First-fit still places a later item that fits. Stopping at the first miss leaves the 1x1 out of the gap.",
        "file": "bible.html",
        "find": "    items.forEach(function(it){\n      var near = it.near || (it.cluster && lastOf[it.n]) || null; /* L1 copies of one item cluster */\n",
        "replace": "    items.forEach(function(it){\n      if (left.length) { left.push(it); return; }\n      var near = it.near || (it.cluster && lastOf[it.n]) || null; /* L1 copies of one item cluster */\n",
        "matches": 1,
    },
    {
        "why": "A shared-stash record homes on the shared locker. Sending it to a category mule splits war gear.",
        "file": "bible.html",
        "find": "return 'shared'; /* v3767 war home */",
        "replace": "return 'uni-armor'; /* v3767 war home */",
        "matches": 1,
    },
    {
        "why": "Every shared copy sits on the same mule. Sending copy 3 to dupes puts it in GRAIL-DUPES.",
        "file": "bible.html",
        "find": "return 'shared'; /* v3767 same mule */",
        "replace": "return (copyIx < 2) ? 'shared' : 'dupes';",
        "matches": 1,
    },
    {
        "why": "Two copies that do not fit the remaining cell move together. Placing one leaves its twin behind.",
        "file": "bible.html",
        "find": "if (_spreadFits(grp.items, null)) { deferred.push(grp); return; } /* v3767 whole group */",
        "replace": "if (false && _spreadFits(grp.items, null)) { deferred.push(grp); return; } /* v3767 whole group */",
        "matches": 1,
    },
    {
        "why": "A copy already in GRAIL-DUPES has to move onto the original mule. Skipping that leaves the old loc.",
        "file": "bible.html",
        "find": "if (typeof _vaultRehomeCopies === 'function') recs = _vaultRehomeCopies(recs); /* v3767 rehome call */",
        "replace": "if (false && typeof _vaultRehomeCopies === 'function') recs = _vaultRehomeCopies(recs); /* v3767 rehome call */",
        "matches": 1,
    },
    {
        "why": "Two spellings of one set piece are one record. Skipping the collapse files Natalya twice.",
        "file": "bible.html",
        "find": "if (typeof _vaultSameItemNames === 'function') { /* v3767 one set piece */",
        "replace": "if (false) { /* v3767 one set piece */",
        "matches": 1,
    },
    {
        "why": "FIND of the loose spelling must resolve to the filed spelling. Dropping the twin lookup returns no mule.",
        "file": "bible.html",
        "find": "if ((!ids || !ids.length) && typeof _vaultSameItemNames === 'function') { /* v3767 find twin */",
        "replace": "if (false) { /* v3767 find twin */",
        "matches": 1,
    },
    {
        "why": "Deleting one spelling removes the item everywhere. Keeping the request unwidened leaves the mule filing.",
        "file": "bible.html",
        "find": "req = wide; /* v3767 same item */",
        "replace": "req = req; /* v3767 same item */",
        "matches": 1,
    },
    {
        "why": "A loose spelling of a filed set piece is not a second dock chip. Skipping the twin check draws the ghost.",
        "file": "bible.html",
        "find": "if (typeof _vaultSameItemNames === 'function') { /* v3767 dock twin */",
        "replace": "if (false) { /* v3767 dock twin */",
        "matches": 1,
    },
    {
        "why": "A name the records do not home on this mule is not drawn. Packing it draws a ghost tile.",
        "file": "bible.html",
        "find": "if (_spanOf && !Object.prototype.hasOwnProperty.call(_spanOf, n)) return;",
        "replace": "if (false && _spanOf && !Object.prototype.hasOwnProperty.call(_spanOf, n)) return;",
        "matches": 1,
    },
    {
        "why": "The population line takes filed and owned from the record. Keeping the subtraction puts the orphan back in filed.",
        "file": "bible.html",
        "find": "o[k] = header[k];",
        "replace": "o[k] = o[k];",
        "matches": 1,
    },
    {
        "why": "Integrity drops the second spelling of a recorded set piece. Keeping it makes one totem two findings.",
        "file": "bible.html",
        "find": "return false; /* v3767 twin finding */",
        "replace": "return true; /* v3767 twin finding */",
        "matches": 1,
    },
    {
        "why": "A null router answer is the shared-stash regex, not Unsorted. Marking it unsorted files a rune nowhere it can land.",
        "file": "bible.html",
        "find": "if (!sg) return { home: null, unsorted: false, why: 'no route' };",
        "replace": "if (!sg) return { home: null, unsorted: true, why: 'no route' };",
        "matches": 1,
    },
    {
        "why": "The register files the route home. Nulling that home leaves a known plate in the dock.",
        "file": "bible.html",
        "find": "sg = { id: _route.home, unsorted: false, why: _route.why || sg.why || '' };",
        "replace": "sg = { id: null, unsorted: true, why: _route.why || sg.why || '' };",
        "matches": 1,
    },
    {
        "why": "The locker packer fills through the spread. Turning the join off packs the fallback and the spread can drift.",
        "file": "bible.html",
        "find": "mules.viaSpread = true;",
        "replace": "mules.viaSpread = false;",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
