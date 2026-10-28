# -*- coding: utf-8 -*-
"""v3769 — the vault paints a move list and keeps the target cell.

Elad, 2026-10-18. Each out-of-place copy gets one row, grouped by the holder and
stash it sits in now. The target cell comes from the same first-fit packer the
mule window uses, and a saved cell is not recomputed. A later witness at that
cell verifies the row only while AUTO INTAKE is on. A hand tally and a typed
move work while it is off. assign is not written.

Sets, uniques, runewords, charms and bases all go through that writer.
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

from test_v3767_copy_witness import _assigned, _fn, _slice_fn, look_rule  # noqa: E402

FNS = [
    "packGrid", "vaultSize",
    "_vaultCellKey", "_vaultSightGroups", "_vaultPresenceSpan", "_mkWant",
    "_vaultAutoIntakeRead", "_vaultAutoIntakePaint", "_vaultAutoIntakeSet",
    "_vaultAutoIntakeToggle", "_vaultFrameRefuse", "_vaultIntakeGate",
    "_vaultMovePlace", "_vaultMoveSamePlace", "_vmMs", "_vaultMoveReads", "_vaultMoveSeenAtTo", "_vaultMoveHalfSay",
    "_vaultMoveTask", "_vaultMoveQueue",
    "_vaultMoveTally", "_vaultMoveWitness",
    "_vaultSeamHome", "_dockNames", "_vaultRecords",
    "_vrRecWitness", "_vrRecRow", "_vrRecRowsFrom",
    "_vrRecLoadRaw", "_vrRecGuardedSet", "_vrLocForCopy",
    "_vaultRehomeCopies", "_vaultReconcileHomes",
    "_vaultRecordsLoad", "_vaultRecordsPersist",
    "_vaultMisfiled", "_vaultWarSmall", "_vaultWarKeeper", "_vaultWarExtra", "_vaultWarRole", "_vaultMuleOfPlace", "_vaultSharedFamily", "_vaultFamilyOfPlace", "_vaultWarMules", "_vaultCellAt",
    "_vaultWarCap0", "_vaultWarOver", "_vaultWarOverOn", "_vaultWarCap", "_vaultWarKept", "_vaultHandGear", "_vaultHandQuals", "_vaultHandBase", "_vaultHandBasePool",
    "_vaultIntakeOwned", "_vaultSightLooks",
    "_vaultMoveHome", "_vaultMoveCopies", "_vaultMovePackHome", "_vaultMovePlanCell",
    "_vaultMoveFromSight", "_vaultMoveBag", "_vaultMoveEnsure", "_vaultMoveCommit",
    "_vaultCellOk", "_vaultMoveApplySight", "_vaultMoveMark", "_vaultMoveNoteAdded",
    "_vaultMoveOnKeep", "_vaultMoveWorn", "_vaultMoveFarmLoot", "_vaultMoveMainLane", "_vaultMoveShown", "_vaultMoveStashSay", "_vaultMoveUnseen", "_vaultMoveGroup", "_vaultMoveLocks",
    "persistOwned",
    "_vaultMoveCellSay", "_vaultMovePlaceSay", "_vaultMoveGridHtml", "_vaultMoveHtml", "_vaultMoveCompareModel", "_vaultTaskExpandHtml",
    "_vaultMoveCollect", "_vaultMovePaint", "_vaultMoveCellMarkHtml", "_vaultFrameMeta",
]

PREAMBLE = r"""
var window = globalThis;
var owned = new Set();
var assign = {};
var copies = {};
var multiKeep = {};
var PROV = {};
var magicFinds = {};
var ROUTES = {};
var selectedChip = null;
var GRID_CALLS = [];
var VAULT_AUTO_INTAKE_KEY = 'd2r_vaultAutoIntake';
var unknownReads = new Set();
function _safeJsonParse(raw, fallback){
  if (raw == null || raw === '') return fallback;
  try { return JSON.parse(raw); } catch (e) { return fallback; }
}
var CELLS = {
  "Griffon's Eye": { w: 2, h: 2 },
  "Harlequin Crest": { w: 2, h: 2 },
  "Colossus Blade": { w: 2, h: 4 },
  "Tal Rasha's Guardianship": { w: 2, h: 3 },
  "Enigma": { w: 2, h: 3 },
  "Gheed's Fortune": { w: 1, h: 1 },
  "Archon Plate": { w: 2, h: 3 },
  "Eschuta's Temper": { w: 1, h: 3 }
};
var _VR_STORE_KEY = 'd2r_vaultRecords';
var _VRM_KEY = 'd2r_vaultRecordsMigrate';
var _VRM_VER = 1;
var _VR_DIRTY_KEY = 'd2r_vaultRecordsDirty';
var _vrRecHold = 0;
var _vrRecFollowLive = false;
var _vrRecUnread = {};
var _ls = {};
window.LSR = {
  getItem: function(k){ return Object.prototype.hasOwnProperty.call(_ls, k) ? _ls[k] : null; },
  setItem: function(k, v){ _ls[k] = String(v); },
  removeItem: function(k){ delete _ls[k]; }
};
var LS = window.LSR;
var document = { _els: {}, getElementById: function(id){
  if (!document._els[id]) document._els[id] = { id: id, hidden: true, innerHTML: '', textContent: '' };
  return document._els[id];
}};
function _itemCells(n){ return CELLS[n] || { w: 1, h: 1 }; }
function gridHtml(placed, gw, gh, cell, opt){
  GRID_CALLS.push({ n: (placed || []).length, gw: gw, gh: gh, opt: opt || null, keys: (placed || []).map(function(p){ return p.key; }) });
  return '<div class="vd-grid" data-gw="' + gw + '" data-gh="' + gh + '"></div>';
}
function art(n){ return '<img class="art" alt="' + n + '">'; }
function esc(t){ return String(t == null ? '' : t).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;'); }
function jsArg(t){ return String(t == null ? '' : t).replace(/\\/g,'\\\\').replace(/'/g,"\\'"); }
function _evEsc(t){ return esc(t); }
window._vaultEvidencePicHtml = function(){ return ''; };
function ownedPool(){ return Array.from(owned).sort(); }
function copyCount(n){ return (copies[n] > 0) ? copies[n] : 1; }
function isSharedStash(){ return false; }
function _sharedNames(){ return []; }
function _inMagicRare(){ return false; }
function muleById(id){
  var known = {
    shared: 'SHARED STASH', 'uni-weap': 'UNI-WEAPONS', 'uni-armor': 'UNI-ARMOR',
    'uni-small': 'UNI-JEWELRY', 'sets-major': 'SETS', bases: 'BASES', runewords: 'RUNEWORDS'
  };
  return known[id] ? { id: id, name: known[id] } : null;
}
function suggestMule(name){
  if (Object.prototype.hasOwnProperty.call(ROUTES, name)) return ROUTES[name];
  return { id: null, unsorted: true, why: 'unknown' };
}
window._vfIsSetPiece = function(){ return false; };
window._carriedNames = function(){ return []; };
window._furnitureLocked = function(){ return false; };
window._mainLockOf = function(){ return null; };
window._vaultLastSeenOnMain = function(){ return null; };
window._muleStoreUnread = function(){ return false; };
window._ownedAdd = function(nm){
  if (nm && !owned.has(String(nm))) owned.add(String(nm));
  return { added: true, prov: { ok: true } };
};
function _provAll(){ return PROV; }
function _isChronicleOnlyRow(){ return false; }
function _inner(){
  var nm = arguments[0];
  if (nm) owned.add(String(nm));
  return { ok: true, mode: 'new', name: nm };
}
function reset(){
  owned.clear();
  [assign, copies, multiKeep, PROV, ROUTES, _ls, CELLS].forEach(function(o){
    if (o === CELLS) return;
    Object.keys(o).forEach(function(k){ delete o[k]; });
  });
  Object.keys(_vrRecUnread).forEach(function(k){ delete _vrRecUnread[k]; });
  selectedChip = null;
  GRID_CALLS.length = 0;
  window._movePackCache = null;
  document._els = {};
}
function L(holder, loc, cell, session, frame){
  return { holder: holder, loc: loc, cell: cell, id: session || null, frame: frame || null };
}
function see(name, looks, nCopies){
  owned.add(name);
  if (nCopies) copies[name] = nCopies;
  if (looks) PROV[name] = { looks: looks };
}
function cellXY(cell){
  var m = String(cell || '').match(/c(\d+)r(\d+)/);
  return m ? { x: +m[1], y: +m[2] } : null;
}
"""

TAIL = r"""
window._vaultFrameRefuse = _vaultFrameRefuse;
window._vaultIntakeGate = _vaultIntakeGate;
window._vaultAutoIntakeSet = _vaultAutoIntakeSet;
window._vaultAutoIntakeRead = _vaultAutoIntakeRead;
window._vaultMoveApplySight = _vaultMoveApplySight;
window._vaultMoveEnsure = _vaultMoveEnsure;
window._vaultMoveCommit = _vaultMoveCommit;
window._vaultMoveMark = _vaultMoveMark;
window._vaultMoveNoteAdded = _vaultMoveNoteAdded;
window._vaultMoveHtml = _vaultMoveHtml;
window._vaultMoveGroup = _vaultMoveGroup;
window._vaultMoveShown = _vaultMoveShown;
window._vaultMoveCellMarkHtml = _vaultMoveCellMarkHtml;
window._vaultFrameMeta = _vaultFrameMeta;
window._vaultMovePaint = _vaultMovePaint;
window._vaultMoveHalfSay = _vaultMoveHalfSay;
"""


def move_bundle(src):
    lane = _slice_fn(src, "var _LANE_LOCK_KEY = 'd2r_laneLock';", "window._laneLockWhy = function(name){")
    # his 2026-10-27 ruling: only farming loot moves out of MAIN inventory - the page's OWN kit law decides, not a stub
    kit = _slice_fn(src, "  function _foldNm(n){", "  window._standingKit = function(name){")
    looks = _assigned(src, r"window\._vaultEvidenceLooks\s*=\s*function\s*\(")
    evidence = _assigned(src, r"window\._vaultEvidenceHtml\s*=\s*function\s*\(")
    register = _assigned(src, r"window\.tvVaultRegister = function\(name\)\{")
    reload_owned = _assigned(src, r"window\._vaultReloadOwned\s*=\s*function\(")
    # REG-2690 - _vaultCellOk reads the page's own grid sizes, never a copy of them
    grid = re.search(r"  var MULE_STASH_W = [^\n]*\n  var MULE_INV_W = [^\n]*\n", src).group(0)
    # REG-2703 - the hand door peels its quality words with the page's own _VH_QUAL, never a copy of it
    grid += re.search(r"  var _VH_QUAL = [^\n]*\n", src).group(0)
    return "\n".join(
        [grid, lane, kit, looks, evidence, register, reload_owned, look_rule(src)] + [_fn(src, n) for n in FNS] + [TAIL])


class TestV3769VaultMoveList(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not NODE:
            raise AssertionError("node is not on this machine — this law does not skip")
        with open(BIBLE, encoding="utf-8") as f:
            cls.src = f.read()
        cls.bundle = move_bundle(cls.src)

    def _run(self, body):
        prog = PREAMBLE + "\n" + self.bundle + "\n" + body
        raw = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=30)
        self.assertEqual(raw.returncode, 0, (raw.stderr or "")[-2500:] + "\n" + (raw.stdout or "")[-800:])
        line = [ln for ln in raw.stdout.splitlines() if ln.startswith("{") or ln.startswith("[")][-1]
        return json.loads(line)

    def test_a_duplicate_sits_beside_the_original(self):
        o = self._run(r"""
reset();
ROUTES["Griffon's Eye"] = { id: 'uni-armor', why: 'helm' };
see("Griffon's Eye", [
  L('MAIN','stash','stash:c1r1','s1','a'),
  L('MAIN','stash','stash:c8r2','s2','b')
], 1);
window._movePackCache = null;
var a = _vaultMoveEnsure("Griffon's Eye", 0).task.to;
var b = _vaultMoveEnsure("Griffon's Eye", 1).task.to;
var ax = cellXY(a.cell), bx = cellXY(b.cell);
console.log(JSON.stringify({
  a: a, b: b,
  beside: !!(ax && bx && bx.x === ax.x + 2 && bx.y === ax.y && a.holder === 'UNI-ARMOR' && a.location === 'stash')
}));
""")
        self.assertTrue(o["beside"], o)
        self.assertEqual(o["a"]["cell"], "stash:c0r0")
        self.assertEqual(o["b"]["cell"], "stash:c2r0")

    def test_a_saved_target_survives_a_repack_and_a_second_persist(self):
        o = self._run(r"""
reset();
ROUTES["Griffon's Eye"] = { id: 'uni-armor', why: 'helm' };
see("Griffon's Eye", [L('MAIN','stash','stash:c3r3','s1','a')], 1);
window._movePackCache = null;
var first = _vaultMoveEnsure("Griffon's Eye", 0);
var wrote = _vaultMoveCommit([{ name: "Griffon's Eye", copyIx: 0, task: first.task }]);
var cell = first.task.to.cell;
ROUTES["Colossus Blade"] = { id: 'uni-armor', why: 'blade' };
see("Colossus Blade", [L('MAIN','stash','stash:c0r8','s1','c')], 1);
window._movePackCache = null;
var again = _vaultMoveEnsure("Griffon's Eye", 0);
var persisted = _vaultRecordsPersist();
var loaded = _vaultRecordsLoad();
var row = (loaded.records || []).filter(function(r){ return r.name === "Griffon's Eye" && (r.copyIx || 0) === 0; })[0];
console.log(JSON.stringify({
  wrote: !!(wrote && wrote.ok),
  persisted: !!(persisted && persisted.ok),
  cell: cell,
  again: again.task.to.cell,
  stored: row && row.move && row.move.to && row.move.to.cell,
  fresh: again.fresh
}));
""")
        self.assertTrue(o["wrote"] and o["persisted"], o)
        self.assertEqual(o["again"], o["cell"])
        self.assertEqual(o["stored"], o["cell"])
        self.assertFalse(o["fresh"])

    def test_auto_off_does_not_verify_and_unknown_does_not_either(self):
        o = self._run(r"""
reset();
ROUTES["Griffon's Eye"] = { id: 'uni-armor', why: 'helm' };
see("Griffon's Eye", [L('MAIN','stash','stash:c1r1','s1','a')], 1);
var ens = _vaultMoveEnsure("Griffon's Eye", 0);
_vaultMoveCommit([{ name: "Griffon's Eye", copyIx: 0, task: ens.task }]);
var to = ens.task.to;
function sight(){ return { holder: to.holder, loc: to.location, cell: to.cell, frame: 'shot-1' }; }
_vaultAutoIntakeSet(false);
var off = _vaultMoveApplySight("Griffon's Eye", sight());
var bagOff = _vaultMoveBag().map["Griffon's Eye\u00000"];
window.LSR.setItem('d2r_vaultAutoIntake', 'maybe');
var unk = _vaultMoveApplySight("Griffon's Eye", sight());
var bagUnk = _vaultMoveBag().map["Griffon's Eye\u00000"];
console.log(JSON.stringify({
  off: off.applied, unk: unk.applied,
  status: bagUnk && bagUnk.status,
  evidence: bagUnk && bagUnk.evidence,
  offStatus: bagOff && bagOff.status
}));
""")
        self.assertFalse(o["off"])
        self.assertFalse(o["unk"])
        self.assertEqual(o["status"], "to-move")
        self.assertEqual(o["evidence"], [])

    def test_from_stays_to_move_a_third_spot_is_elsewhere_and_to_verifies(self):
        o = self._run(r"""
reset();
ROUTES["Griffon's Eye"] = { id: 'uni-armor', why: 'helm' };
see("Griffon's Eye", [L('MAIN','stash','stash:c1r1','s1','a')], 1);
_vaultAutoIntakeSet(true);
var ens = _vaultMoveEnsure("Griffon's Eye", 0);
_vaultMoveCommit([{ name: "Griffon's Eye", copyIx: 0, task: ens.task }]);
var from = ens.task.from, to = ens.task.to;
var still = _vaultMoveApplySight("Griffon's Eye", { holder: from.holder, loc: from.location, cell: from.cell, frame: 'still-1' });
var elsew = _vaultMoveApplySight("Griffon's Eye", { holder: 'SOMEONE', loc: 'stash', cell: 'stash:c9r9', frame: 'else-1' });
/* REG-2843 - his done rule: two sessions at the target, both read after the task opened */
var T0 = Date.now();
function atTo(n){ var ms = T0 + n * 60000; return { holder: to.holder, loc: to.location, cell: to.cell, frame: 'live-' + n, at: new Date(ms).toISOString(),
                                                   sessions: [{ id: 's_' + ms + '_' + n, frame: 'live-' + n }] }; }
var half = _vaultMoveApplySight("Griffon's Eye", atTo(1));
var ok = _vaultMoveApplySight("Griffon's Eye", atTo(2));
console.log(JSON.stringify({
  still: still.task.status,
  elsewhere: elsew.task.status,
  half: half.task.status, halfSeen: (half.task.seen || []).length,
  verified: ok.task.status,
  evidence: ok.task.evidence
}));
""")
        self.assertEqual(o["still"], "to-move")
        self.assertEqual(o["elsewhere"], "moved-elsewhere")
        self.assertEqual((o["half"], o["halfSeen"]), ("moved-elsewhere", 1), "one session at the target closed the task: %r" % o)
        self.assertEqual(o["verified"], "verified")
        self.assertIn("live-2", o["evidence"])

    def test_a_hand_tally_holds_until_the_target_is_witnessed(self):
        o = self._run(r"""
reset();
ROUTES["Griffon's Eye"] = { id: 'uni-armor', why: 'helm' };
see("Griffon's Eye", [L('MAIN','stash','stash:c1r1','s1','a')], 1);
_vaultAutoIntakeSet(false);
var marked = _vaultMoveMark("Griffon's Eye", 0);
var from = marked.from, to = marked.to;
_vaultAutoIntakeSet(true);
var held = _vaultMoveApplySight("Griffon's Eye", { holder: from.holder, loc: from.location, cell: from.cell, frame: 'from-2' });
var confirmed = _vaultMoveApplySight("Griffon's Eye", { holder: to.holder, loc: to.location, cell: to.cell, frame: 'to-2' });
console.log(JSON.stringify({
  marked: marked.status,
  held: held.task && held.task.status,
  heldWhy: held.why || null,
  confirmed: confirmed.task && confirmed.task.status,
  evidence: confirmed.task && confirmed.task.evidence
}));
""")
        self.assertEqual(o["marked"], "moved-manual")
        self.assertEqual(o["held"], "moved-manual")
        self.assertEqual(o["confirmed"], "verified")
        self.assertIn("to-2", o["evidence"])

    def test_a_hand_add_uses_the_packer_and_does_not_write_assign(self):
        o = self._run(r"""
reset();
_vaultAutoIntakeSet(false);
ROUTES["Harlequin Crest"] = { id: 'uni-armor', why: 'helm' };
var added = _vaultMoveNoteAdded("Harlequin Crest");
var home = _vaultMoveNoteAdded("Zzznotanitem");
console.log(JSON.stringify({
  ok: added.ok,
  shown: added.shown === true,
  manual: !!(added.task && added.task.manual),
  holder: added.task && added.task.to && added.task.to.holder,
  cell: added.task && added.task.to && added.task.to.cell,
  assign: Object.prototype.hasOwnProperty.call(assign, "Harlequin Crest") ? assign["Harlequin Crest"] : null,
  homeShown: home.shown === true,
  intake: _vaultAutoIntakeRead()
}));
""")
        self.assertTrue(o["ok"], o)
        self.assertTrue(o["shown"], o)
        self.assertTrue(o["manual"], o)  # v3773 Elad: a hand add reads MANUAL -> target cell
        self.assertEqual(o["holder"], "UNI-ARMOR")
        self.assertEqual(o["cell"], "stash:c0r0")
        self.assertIsNone(o["assign"])
        self.assertFalse(o["homeShown"], o)
        self.assertFalse(o["intake"]["on"])

    def test_a_typed_move_lands_after_the_store_already_exists(self):
        o = self._run(r"""
reset();
ROUTES["Griffon's Eye"] = { id: 'uni-armor', why: 'helm' };
see("Griffon's Eye", [L('Mule','stash','stash:c1r1','s1','a')], 1);
_vaultMovePaint();
ROUTES["Harlequin Crest"] = { id: 'uni-armor', why: 'helm' };
var added = _vaultMoveNoteAdded("Harlequin Crest");
var loaded = _vaultRecordsLoad();
var row = (loaded.records || []).filter(function(r){ return r.name === "Harlequin Crest"; })[0];
var kept = (loaded.records || []).filter(function(r){ return r.name === "Griffon's Eye"; })[0];
console.log(JSON.stringify({
  ok: added.ok,
  cell: row && row.move && row.move.to && row.move.to.cell,
  kept: kept && kept.move && kept.move.to && kept.move.to.cell,
  assign: Object.prototype.hasOwnProperty.call(assign, "Harlequin Crest") ? assign["Harlequin Crest"] : null
}));
""")
        self.assertTrue(o["ok"], o)
        self.assertTrue(o["cell"], o)
        self.assertTrue(o["kept"], o)
        self.assertIsNone(o["assign"])

    def test_three_sessions_stay_locked_when_the_target_is_saved(self):
        o = self._run(r"""
reset();
ROUTES["Eschuta's Temper"] = { id: 'uni-weap', why: 'wand' };
see("Eschuta's Temper", [L('MAIN','inventory','inventory:c1r1','s1','e1')], 1);
window._laneLockNote("Eschuta's Temper", 'equipment', 'a');
window._laneLockNote("Eschuta's Temper", 'equipment', 'b');
window._laneLockNote("Eschuta's Temper", 'equipment', 'c');
var ens = _vaultMoveEnsure("Eschuta's Temper", 0);
var wrote = _vaultMoveCommit([{ name: "Eschuta's Temper", copyIx: 0, task: ens.task }]);
var loaded = _vaultRecordsLoad();
var row = (loaded.records || []).filter(function(r){ return r.name === "Eschuta's Temper"; })[0];
var live = _vaultRecords().records.filter(function(r){ return r.name === "Eschuta's Temper"; })[0];
console.log(JSON.stringify({
  wrote: !!(wrote && wrote.ok),
  locked: !!(row && row.locked),
  liveLocked: !!(live && live.locked),
  watching: !!(live && live.watching)
}));
""")
        self.assertTrue(o["wrote"], o)
        self.assertTrue(o["locked"], o)
        self.assertTrue(o["liveLocked"], o)

    def test_rows_group_by_holder_and_stash_and_unknown_is_not_main(self):
        o = self._run(r"""
function row(name, holder, loc){
  return { name: name, copyIx: 0, witnesses: 1, task: _vaultMoveTask({
    name: name,
    from: { holder: holder, location: loc, cell: (loc || 'stash') + ':c0r0' },
    to: { holder: 'UNI-ARMOR', location: 'stash', cell: 'stash:c1r1' },
    status: 'to-move'
  })};
}
var groups = _vaultMoveGroup([
  row("Griffon's Eye", 'UNI-ARMOR', 'stash'),
  row('Zzznotanitem', null, 'stash'),
  row("Harlequin Crest", 'MAIN', 'inventory'),
  row('Enigma', 'SHARED STASH', 'shared')
]);
console.log(JSON.stringify(groups.map(function(g){
  return { label: g.label, stash: g.stash, holder: g.holder };
})));
""")
        self.assertEqual(o[0]["label"], "MAIN")
        self.assertEqual(o[0]["stash"], "inventory")
        labels = [g["label"] for g in o]
        self.assertIn("UNKNOWN", labels)
        self.assertNotEqual(labels[labels.index("UNKNOWN")], "MAIN")
        by = {g["label"]: g["stash"] for g in o}
        self.assertEqual(by["UNI-ARMOR"], "private stash")
        self.assertEqual(by["SHARED STASH"], "shared stash")

    def test_the_row_opens_the_evidence_ledger_and_draws_the_target_grid(self):
        o = self._run(r"""
reset();
ROUTES["Griffon's Eye"] = { id: 'uni-armor', why: 'helm' };
see("Griffon's Eye", [
  L('MAIN','stash','stash:c1r1','s1','a'),
  L('MAIN','stash','stash:c1r1','s2','b')
], 1);
var built = _vaultMoveCollect();
var html = _vaultMoveHtml(built);
var cmp = _vaultTaskExpandHtml("Griffon's Eye", 0); /* L1: the target grid is drawn in the row's own inline expand (#144.14) */
var panel = window._vaultEvidenceHtml({
  has: true, name: "Griffon's Eye", who: 'hand', line: 'evidence',
  looks: [{ frame: 'a', cell: 'stash:c1r1' }, { frame: 'b', cell: 'stash:c1r1' }]
}, { state: 'none' });
console.log(JSON.stringify({
  open: html.indexOf('_vaultEvidenceOpen') >= 0,
  witnesses: html.indexOf('2 witnesses') >= 0,
  art: html.indexOf("Griffon's Eye") >= 0,
  status: html.indexOf('data-status="to-move"') >= 0,
  grid: GRID_CALLS.length,
  gridKey: GRID_CALLS.length ? GRID_CALLS[0].keys : [],
  toGrid: GRID_CALLS.filter(function(c){ return c.opt && c.opt.label === 'To'; }).map(function(c){ return c.keys; }),
  door: panel.indexOf('_vaultOpenEvidence') >= 0,
  lockedChip: html.indexOf('LOCKED')
}));
""")
        self.assertTrue(o["open"], o)
        self.assertTrue(o["witnesses"], o)
        self.assertTrue(o["art"], o)
        self.assertTrue(o["status"], o)
        self.assertGreaterEqual(o["grid"], 1)
        # #144.14 (REG-2780) - the row's inline expand draws ONE target grid holding this copy alone
        self.assertEqual(o["toGrid"], [["Griffon's Eye#0"]], "the row's expand did not draw this copy's own TO grid: %r" % o)
        self.assertTrue(o["door"], o)

    def test_a_move_row_opens_from_the_keyboard(self):
        """#148.5 (REG-2734, GrokBot's vault sweep) - a move row opened on a click only: no tabindex, no role, so only its
        tick box took the keyboard. The row's OWN keydown is run here: Enter and Space on the row open it, a key that
        lands on a control inside it (the tick, a button) is left to that control, and Tab is not taken."""
        o = self._run(r"""
reset();
ROUTES["Griffon's Eye"] = { id: 'uni-armor', why: 'helm' };
see("Griffon's Eye", [L('MAIN','stash','stash:c1r1','s1','a'), L('MAIN','stash','stash:c1r1','s2','b')], 1);
var html = _vaultMoveHtml(_vaultMoveCollect());
var m = /<li class="[^"]*vtk-line[^"]*"([^>]*)>/.exec(html);
var attrs = m ? m[1] : '';
function attr(n){
  var r = new RegExp(' ' + n + '="([^"]*)"').exec(attrs);
  return r ? r[1].replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&#x27;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&') : null;
}
var ROW = { id: 'row' }, calls = [];
window._vaultTaskExpand = function(name, ci, el){ calls.push([name, ci, el === ROW]); };
var kd = attr('onkeydown');
function fire(key, target){
  var prevented = false;
  if (kd) new Function('event', kd).call(ROW, { key: key, target: target, preventDefault: function(){ prevented = true; } });
  return prevented;
}
var enterRow = fire('Enter', ROW), spaceRow = fire(' ', ROW), enterChild = fire('Enter', { id: 'tick' }), tabRow = fire('Tab', ROW);
console.log(JSON.stringify({ found: !!m, tabindex: attr('tabindex'), role: attr('role'), label: attr('aria-label'),
  calls: calls, enterRow: enterRow, spaceRow: spaceRow, enterChild: enterChild, tabRow: tabRow }));
""")
        self.assertTrue(o["found"], "PREMISE: no move row was drawn: %r" % o)
        self.assertEqual((o["tabindex"], o["role"]), ("0", "button"), "a move row cannot take the keyboard focus: %r" % o)
        self.assertIn("Griffon's Eye", o["label"] or "", "the row is focusable but says nothing: %r" % o)
        self.assertEqual(o["calls"], [["Griffon's Eye", 0, True], ["Griffon's Eye", 0, True]],
                         "Enter/Space on the row did not open it, or a key inside it did: %r" % o)
        self.assertEqual((o["enterRow"], o["spaceRow"], o["enterChild"], o["tabRow"]), (True, True, False, False), o)

    def test_a_verified_row_stays_visible_and_an_unknown_cell_is_not_marked(self):
        o = self._run(r"""
var same = _vaultMoveTask({
  name: 'Shako', status: 'verified',
  from: { holder: 'UNI-ARMOR', location: 'stash', cell: 'stash:c0r0' },
  to: { holder: 'UNI-ARMOR', location: 'stash', cell: 'stash:c0r0' }
});
var mark = _vaultMoveCellMarkHtml('stash:c2r3');
var meta = _vaultFrameMeta('evidence', 'tv/.render_shots/v3769-frame.png', 'stash:c2r3');
console.log(JSON.stringify({
  shown: _vaultMoveShown(same),
  empty: _vaultMoveCellMarkHtml(null),
  mark: mark.indexOf('class="on"') >= 0 && mark.indexOf('stash:c2r3') >= 0,
  cell: meta.cell,
  noCell: _vaultFrameMeta('evidence', null, null).cell || null
}));
""")
        self.assertTrue(o["shown"])
        self.assertEqual(o["empty"], "")
        self.assertTrue(o["mark"], o)
        self.assertEqual(o["cell"], "stash:c2r3")
        self.assertIsNone(o["noCell"])

    def test_five_classes_plan_through_the_real_writer(self):
        o = self._run(r"""
reset();
var spec = [
  ["Tal Rasha's Guardianship", 'sets-major', 'SETS', 'stash'],
  ["Griffon's Eye", 'uni-armor', 'UNI-ARMOR', 'stash'],
  ["Enigma", 'shared', 'SHARED STASH', 'shared'],
  ["Gheed's Fortune", 'uni-small', 'UNI-JEWELRY', 'stash'],
  ["Archon Plate", 'bases', 'BASES', 'stash']
];
var out = [];
spec.forEach(function(s){
  ROUTES[s[0]] = { id: s[1], why: s[0] };
  see(s[0], [L('MAIN','stash','stash:c4r4','s1','f')], 1);
});
window._movePackCache = null;
spec.forEach(function(s){
  var t = _vaultMoveEnsure(s[0], 0).task;
  out.push({ name: s[0], holder: t.to.holder, location: t.to.location, cell: t.to.cell, wantH: s[2], wantL: s[3] });
});
console.log(JSON.stringify(out));
""")
        self.assertEqual(len(o), 5)
        for row in o:
            self.assertEqual(row["holder"], row["wantH"], row)
            self.assertEqual(row["location"], row["wantL"], row)
            self.assertTrue(row["cell"] and row["cell"].startswith(row["wantL"] + ":c"), row)

    def test_the_register_applies_a_sight_only_through_the_auto_door(self):
        o = self._run(r"""
reset();
ROUTES["Griffon's Eye"] = { id: 'uni-armor', why: 'helm' };
see("Griffon's Eye", [L('MAIN','stash','stash:c1r1','s1','a')], 1);
var ens = _vaultMoveEnsure("Griffon's Eye", 0);
_vaultMoveCommit([{ name: "Griffon's Eye", copyIx: 0, task: ens.task }]);
var to = ens.task.to;
_vaultAutoIntakeSet(true);
/* REG-2843 - two sessions at the target, each read after the task opened */
var T0 = Date.now();
function wit(n){ var ms = T0 + n * 60000; return { holder: to.holder, loc: to.location, cell: to.cell, frame: 'live-' + n, at: new Date(ms).toISOString(),
                                                  sessions: [{ id: 's_' + ms + '_' + n, frame: 'live-' + n }] }; }
var res1 = window.tvVaultRegister("Griffon's Eye", wit(8));
var half = _vaultMoveBag().map["Griffon's Eye\u00000"];
var halfSay = window._vaultMoveHalfSay(half);
var res = window.tvVaultRegister("Griffon's Eye", wit(9));
var bag = _vaultMoveBag().map["Griffon's Eye\u00000"];
console.log(JSON.stringify({
  ok: !!(res1 && res1.ok && res && res.ok),
  half: half && half.status, halfSay: halfSay,
  status: bag && bag.status,
  evidence: bag && bag.evidence
}));
""")
        self.assertTrue(o["ok"], o)
        self.assertEqual(o["half"], "to-move", "one session at the target closed the task: %r" % o)
        self.assertRegex(o["halfSay"], r"^seen at target once \(\d{4}-\d\d-\d\d\)$", o)
        self.assertEqual(o["status"], "verified")
        self.assertIn("live-9", o["evidence"])

    def test_the_page_wires_the_list_and_the_frame(self):
        self.assertIn(
            "window._vaultMovePaint(); } catch (eMv) {} /* v3769 move paint */", self.src)
        self.assertIn("window._vaultMoveCellMarkHtml(meta.cell)", self.src)
        self.assertIn('id="vault-move-list"', self.src)
        self.assertIn("mark moved", self.src)
        self.assertIn("/* v3773 no manual move */", self.src)
        self.assertNotIn("vault-move-q", self.src)
        self.assertNotIn("_vaultMoveAddNamed", self.src)
        self.assertNotIn("_vaultMoveAddOpen", self.src)
        self.assertNotIn("Add a move", self.src)

    def test_add_a_move_persists_owned_across_reload(self):
        o = self._run(r"""
reset();
ROUTES["Harlequin Crest"] = { id: 'uni-armor', why: 'helm' };
var added = _vaultMoveNoteAdded("Harlequin Crest");
owned.clear();
var n = window._vaultReloadOwned();
console.log(JSON.stringify({
  ok: !!(added && added.ok),
  n: n,
  has: owned.has("Harlequin Crest"),
  raw: window.LSR.getItem('d2r_owned')
}));
""")
        self.assertTrue(o["ok"], o)
        self.assertEqual(o["n"], 1, o)
        self.assertTrue(o["has"], o)
        self.assertIn("Harlequin Crest", o["raw"] or "", o)

    def test_a_keep_on_main_is_not_a_row_and_a_displaced_keep_gets_a_cell(self):
        o = self._run(r"""
reset();
ROUTES["Eschuta's Temper"] = { id: 'uni-weap', why: 'wand' };
see("Eschuta's Temper", [L('MAIN','inventory','inventory:c1r1','s1','e1')], 1);
window._laneLockNote("Eschuta's Temper", 'equipment', 'a');
window._laneLockNote("Eschuta's Temper", 'equipment', 'b');
window._laneLockNote("Eschuta's Temper", 'equipment', 'c');
var home = _vaultMoveCollect();
var names = (home.tasks || []).map(function(r){ return r.name; });
var lockedInv = _vaultMoveShown({
  name: "Eschuta's Temper", status: 'to-move',
  from: { holder: 'MAIN', location: 'inventory', cell: 'inventory:c1r1' },
  to: { holder: 'UNI-WEAPONS', location: 'stash', cell: 'stash:c0r0', id: 'uni-weap' }
});
ROUTES["Griffon's Eye"] = { id: 'uni-armor', why: 'helm' };
var gear = _vaultMoveShown({
  name: "Griffon's Eye", status: 'to-move',
  from: { holder: 'MAIN', location: 'inventory', cell: 'inventory:c0r0' },
  to: { holder: 'UNI-ARMOR', location: 'stash', cell: 'stash:c0r0', id: 'uni-armor' }
});
ROUTES["Gheed's Fortune"] = { id: 'uni-small', why: 'charm' };
var kitInv = _vaultMoveShown({
  name: "Gheed's Fortune", status: 'to-move',
  from: { holder: 'MAIN', location: 'inventory', cell: 'inventory:c9r0' },
  to: { holder: 'UNI-JEWELRY', location: 'stash', cell: 'stash:c0r0', id: 'uni-small' }
});
var _kitLaw = window._standingKit;
window._standingKit = undefined;
var unasked = _vaultMoveShown({
  name: "Griffon's Eye", status: 'to-move',
  from: { holder: 'MAIN', location: 'inventory', cell: 'inventory:c0r0' },
  to: { holder: 'UNI-ARMOR', location: 'stash', cell: 'stash:c0r0', id: 'uni-armor' }
});
window._standingKit = _kitLaw;
var bare = _vaultMoveShown({
  name: "Eschuta's Temper", status: 'to-move',
  from: { holder: 'Mule', location: 'stash', cell: 'stash:c2r2' },
  to: { holder: 'MAIN', location: null, cell: null }
});
reset();
ROUTES["Eschuta's Temper"] = { id: 'uni-weap', why: 'wand' };
see("Eschuta's Temper", [L('Mule','stash','stash:c3r1','s9','e9')], 1);
window._laneLockNote("Eschuta's Temper", 'equipment', 'a');
window._laneLockNote("Eschuta's Temper", 'equipment', 'b');
window._laneLockNote("Eschuta's Temper", 'equipment', 'c');
var ens = _vaultMoveEnsure("Eschuta's Temper", 0);
var to = ens.task.to;
var built = _vaultMoveCollect();
var row = (built.tasks || []).filter(function(r){ return r.name === "Eschuta's Temper"; })[0];
console.log(JSON.stringify({
  homeNames: names,
  gear: gear,
  kitInv: kitInv,
  lockedInv: lockedInv,
  unasked: unasked,
  bare: bare,
  shown: !!row,
  holder: to && to.holder,
  location: to && to.location,
  cell: to && to.cell,
  say: _vaultMovePlaceSay(to)
}));
""")
        self.assertNotIn("Eschuta's Temper", o["homeNames"], o)
        # His ruling 2026-10-27: inventory items get no move row - only the farming space, where loot lands, does.
        self.assertTrue(o["gear"], "farming loot in MAIN inventory got no move row: %r" % o)
        self.assertFalse(o["kitInv"], "standing kit in MAIN inventory got a move row: %r" % o)
        self.assertFalse(o["unasked"], "a name the kit law could not answer for got a move row: %r" % o)
        # A lock is also enforced downstream (a locked name's home is MAIN, "v3769 already home"), so the farm-loot
        # helper's own lock check is defense in depth: no single sabotage of it can show, and it carries no red-proof.
        self.assertFalse(o["lockedInv"], "a name locked to his MAIN got a move row out of his inventory: %r" % o)
        self.assertFalse(o["bare"], o)
        self.assertTrue(o["shown"], o)
        self.assertEqual(o["holder"], "MAIN", o)
        self.assertEqual(o["location"], "inventory", o)
        self.assertRegex(o["cell"] or "", r"^inventory:c\d+r\d+$")
        self.assertNotIn("UNKNOWN", o["say"] or "", o)

    def test_every_bare_vault_helper_the_bundle_calls_is_in_the_bundle(self):
        """A new helper (like _vaultSightLooks) that the move code calls bare must be
        sliced in here too, or the move list dies with a ReferenceError."""
        import re
        b = self.bundle
        called = set(re.findall(r"(?<![\w.$])(_vault\w+)\s*\(", b))
        defined = set(re.findall(r"function\s+(_vault\w+)\s*\(", b)) | \
            set(re.findall(r"(?:var|let|const)\s+(_vault\w+)\s*=", b)) | \
            set(re.findall(r"window\.(_vault\w+)\s*=", b))
        guarded = set(re.findall(r"typeof\s+(_vault\w+)", b))
        self.assertEqual(sorted(called - defined - guarded), [])

    def test_a_zero_look_cell_opens_no_move_through_the_collector(self):
        """Grok CLI blocker: a sight cell with no session/frame look is not a move row."""
        import re
        m = re.search(r"var hasSight = ([^;]*);", self.src)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1).strip(), "!!(r.sight && r.sight.cell && _vaultSightLooks(r.sight) >= 1)")

    def test_distinct_attacks_clear_the_vault_apply_wilson_bar(self):
        from confidence import confluence, wilson_lower
        import self_arming as SA
        bar = SA.LOCKS["vault.apply"]["bar"]
        kinds_bar = SA.LOCKS["vault.apply"]["kinds_bar"]
        n = len(RED_PROOF)
        w = wilson_lower(n, n)
        conf = confluence(["sabotage"], SA.KINDS)
        msg = ("vault move list: %d distinct attacks, wilson %.4f vs vault.apply bar %.3f; "
               "kinds sabotage %.2f vs %.2f" % (n, w, bar, conf, kinds_bar))
        print(msg)
        self.assertGreaterEqual(n, 20, msg)
        self.assertGreaterEqual(w, bar, msg)
        self.assertLess(conf, kinds_bar, msg)


RED_PROOF = [
    {"why": "#148.5 (REG-2734) - a move row takes no keyboard focus again (only its tick box)",
     "file": "bible.html",
     "find": "        + ' tabindex=\"0\" role=\"button\" aria-label=\"' + esc(say) + '\"'\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "#148.5 (REG-2734) - Enter/Space on a focused move row does nothing",
     "file": "bible.html",
     "find": "if((event.key===\\'Enter\\'||event.key===\\' \\')&&event.target===this){event.preventDefault();window._vaultTaskExpand(",
     "replace": "if(false){event.preventDefault();window._vaultTaskExpand(",
     "matches": 1, "needs": "node"},
    {"why": "#148.5 (REG-2734) - a key on the tick or a button inside the row also opens the row",
     "file": "bible.html",
     "find": "if((event.key===\\'Enter\\'||event.key===\\' \\')&&event.target===this){event.preventDefault();window._vaultTaskExpand(",
     "replace": "if((event.key===\\'Enter\\'||event.key===\\' \\')){event.preventDefault();window._vaultTaskExpand(",
     "matches": 1, "needs": "node"},
    {"why": "A saved target is recomputed, so the cell he was sent to moves when a larger item arrives.",
     "file": "bible.html",
     "find": "if (stored && stored.to && stored.to.cell) return { task: stored, copyIx: copyIx, name: name, fresh: false }; /* v3769 saved target */",
     "replace": "if (false && stored && stored.to && stored.to.cell) return { task: stored, copyIx: copyIx, name: name, fresh: false }; /* v3769 saved target */",
     "matches": 1},
    {"why": "Copies of one item pack in reverse, so the duplicate is no longer beside the original.",
     "file": "bible.html",
     "find": "return a.copyIx - b.copyIx; /* v3769 beside */",
     "replace": "return b.copyIx - a.copyIx; /* v3769 beside */",
     "matches": 1},
    {"why": "The record row drops the move, so a second persist forgets the target cell.",
     "file": "bible.html",
     "find": "row.move = (spec.move && typeof spec.move === 'object' && !Array.isArray(spec.move)) ? spec.move : null; /* v3769 record move */",
     "replace": "row.move = null; /* v3769 record move */",
     "matches": 1},
    {"why": "A later persist does not carry the stored move onto the row it writes.",
     "file": "bible.html",
     "find": "move: priorMove[String(r.name) + '\\u0000' + (r.copyIx || 0)] || null, /* v3769 move carry */",
     "replace": "move: null, /* v3769 move carry */",
     "matches": 1},
    {"why": "AUTO INTAKE off still verifies a row from a frame.",
     "file": "bible.html",
     "find": "if (!(st.on === true && st.known === true)) return { applied: false, task: null, why: 'auto-off' }; /* v3769 auto off */",
     "replace": "if (false && !(st.on === true && st.known === true)) return { applied: false, task: null, why: 'auto-off' }; /* v3769 auto off */",
     "matches": 1},
    {"why": "A sighting still at FROM is called verified.",
     "file": "bible.html",
     "find": "t.status = 'to-move'; /* v3767 move still */",
     "replace": "t.status = 'verified'; /* v3767 move still */",
     "matches": 1},
    {"why": "A third spot is called verified instead of moved elsewhere.",
     "file": "bible.html",
     "find": "t.status = 'moved-elsewhere'; /* v3767 move elsewhere */",
     "replace": "t.status = 'verified'; /* v3767 move elsewhere */",
     "matches": 1},
    {"why": "The verifying frame is wiped off the task.",
     "file": "bible.html",
     "find": "if (frame != null && frame !== '' && t.evidence.indexOf(String(frame)) < 0) t.evidence.push(String(frame)); /* v3767 move proof */",
     "replace": "void frame; /* v3767 move proof */",
     "matches": 1},
    {"why": "A hand tally is stored as verified before any witness.",
     "file": "bible.html",
     "find": "t.status = 'moved-manual'; /* v3769 move mark */",
     "replace": "t.status = 'verified'; /* v3769 move mark */",
     "matches": 1},
    {"why": "A hand tally at FROM is reset to to-move, so the tally does not hold until the target is witnessed.",
     "file": "bible.html",
     "find": "if (t.status === 'moved-manual' && atFrom && !atTo) return { applied: false, task: t, why: 'hand-tally' }; /* v3769 moved-manual hold */",
     "replace": "if (false && t.status === 'moved-manual' && atFrom && !atTo) return { applied: false, task: t, why: 'hand-tally' }; /* v3769 moved-manual hold */",
     "matches": 1},
    {"why": "A hand add no longer writes the move, so an out-of-place item has no target.",
     "file": "bible.html",
     "find": "var wrote = _vaultMoveCommit([{ name: nm, copyIx: copyIx, task: hand }]); /* v3773 manual row */",
     "replace": "var wrote = { ok: false }; /* v3773 manual row */",
     "matches": 1},
    {"why": "A name owned after the store exists never gets a row, so the typed move is not saved.",
     "file": "bible.html",
     "find": "var pr = _vaultRecordsPersist(); /* v3769 row refresh */",
     "replace": "var pr = null; /* v3769 row refresh */",
     "matches": 1},
    {"why": "Noting a hand add writes assign. The hand door files the item.",
     "file": "bible.html",
     "find": "return { ok: !!(wrote && wrote.ok), shown: true, task: hand, assign: (typeof assign !== 'undefined' ? assign[nm] : undefined) }; /* v3773 no assign */",
     "replace": "try { assign[nm] = 'shared'; } catch (eAs) {} return { ok: !!(wrote && wrote.ok), shown: true, task: hand, assign: assign[nm] }; /* v3773 no assign */",
     "matches": 1},
    {"why": "Saving a target clears the 3-session lock.",
     "file": "bible.html",
     "find": "locked: row.locked === true, /* v3769 lock stays */",
     "replace": "locked: false, /* v3769 lock stays */",
     "matches": 1},
    {"why": "Noting a hand add keeps the name in memory and never writes d2r_owned, so a reload loses it.",
     "file": "bible.html",
     "find": "try { if (typeof persistOwned === 'function') persistOwned(); } catch (eOw) {} /* v3773 owned persist */",
     "replace": "try { void 0; } catch (eOw) {} /* v3773 owned persist */",
     "matches": 1},
    {"why": "Standing kit in MAIN inventory is painted as a move.",
     "file": "bible.html",
     "find": "    if (_vaultMoveMainLane(t.from && t.from.location, t.name)) return false; /* worn gear and inventory kit stay locked; farming loot moves */",
     "replace": "    if (false && _vaultMoveMainLane(t.from && t.from.location, t.name)) return false; /* worn gear and inventory kit stay locked; farming loot moves */",
     "matches": 1},
    {"why": "Farming loot in MAIN inventory gets no move row again (his 2026-10-27 ruling).",
     "file": "bible.html",
     "find": "    return !(lane === 'inventory' && _vaultMoveFarmLoot(name));",
     "replace": "    return true;",
     "matches": 1},
    {"why": "A name the kit law cannot answer for is treated as loot and moved out of his inventory.",
     "file": "bible.html",
     "find": "    return kit === false;",
     "replace": "    return kit !== true;",
     "matches": 1},
    {"why": "A row with no target location and no cell is still painted.",
     "file": "bible.html",
     "find": "if (!t.to || t.to.holder == null || t.to.location == null || t.to.cell == null) return false; /* v3769 known target */",
     "replace": "if (false && (!t.to || t.to.holder == null || t.to.location == null || t.to.cell == null)) return false; /* v3769 known target */",
     "matches": 1},
    {"why": "A keep is sent to MAIN with no location, so the packer has no inventory cell.",
     "file": "bible.html",
     "find": "if (seam.loc === 'keep') return { id: 'main', holder: 'MAIN', location: 'inventory' }; /* v3769 home keep */",
     "replace": "if (seam.loc === 'keep') return { id: null, holder: 'MAIN', location: null }; /* v3769 home keep */",
     "matches": 1},
    {"why": "A keep that must move is packed into a stash grid instead of MAIN inventory.",
     "file": "bible.html",
     "find": "if (home.id === 'main') { /* v3769 pack main */",
     "replace": "if (false && home.id === 'main') { /* v3769 pack main */",
     "matches": 1},
    {"why": "The sighting door copies the task and never asks the witness writer.",
     "file": "bible.html",
     "find": "var next = _vaultMoveWitness(t, sighting); /* v3769 one writer */",
     "replace": "var next = _vaultMoveTask(t); /* v3769 one writer */",
     "matches": 1},
    {"why": "A holder that was not named is called MAIN.",
     "file": "bible.html",
     "find": "var holder = (from.holder == null || from.holder === '') ? null : String(from.holder); /* v3769 group */",
     "replace": "var holder = 'MAIN'; /* v3769 group */",
     "matches": 1},
    {"why": "A private stash is no longer named, so the groups he clears one at a time collapse.",
     "file": "bible.html",
     "find": "if (location === 'stash') return 'private stash'; /* v3769 stash label */",
     "replace": "if (location === 'stash') return 'stash'; /* v3769 stash label */",
     "matches": 1},
    {"why": "A move row no longer opens the evidence ledger.",
     "file": "bible.html",
     "find": "window._vaultEvidenceOpen(\\'' + nm + '\\')\">' + (row.witnesses == null",
     "replace": "void 0)\">' + (row.witnesses == null",
     "matches": 1},
    {"why": "A witness in the evidence ledger no longer opens its frame.",
     "file": "bible.html",
     "find": "var _witFn = 'window._vaultOpenEvidence'; /* v3769 witness door */",
     "replace": "var _witFn = 'void'; /* v3769 witness door */",
     "matches": 1},
    {"why": "A known cell draws no mark, so the frame has nothing to point at.",
     "file": "bible.html",
     "find": "if (!key) return ''; /* v3769 cell mark */",
     "replace": "if (key) return ''; /* v3769 cell mark */",
     "matches": 1},
    {"why": "The fullscreen frame is opened without the cell, so the mark has nothing to draw.",
     "file": "bible.html",
     "find": "if (key) meta.cell = key; /* v3769 frame cell */",
     "replace": "if (false && key) meta.cell = key; /* v3769 frame cell */",
     "matches": 1},
    {"why": "The TV register no longer hands a sighting to the move, so a witness never ticks the row.",
     "file": "bible.html",
     "find": "window._vaultMoveApplySight((r && r.label) || (r && r.name) || nm, _witIn); /* v3769 register sight */",
     "replace": "void _witIn; /* v3769 register sight */",
     "matches": 1},
    {"why": "A filed item is no longer given its mule, so the unique, the set, the charm and the base lose their cell.",
     "file": "bible.html",
     "find": "if (seam.loc === 'filed' && seam.mule) { /* v3769 home filed */",
     "replace": "if (false && seam.loc === 'filed' && seam.mule) { /* v3769 home filed */",
     "matches": 1},
    {"why": "The shared stash is renamed, so a runeword's target is not the shared holder.",
     "file": "bible.html",
     "find": "                                         : { id: 'shared', holder: 'SHARED STASH', location: 'shared' }; /* L1 over the cap -> WAR mules */",
     "replace": "                                         : { id: 'shared', holder: 'MAIN', location: 'stash' }; /* L1 over the cap -> WAR mules */",
     "matches": 1},
    {"why": "A verified row whose cells already match is hidden, so the tick disappears.",
     "file": "bible.html",
     "find": "if (t.status === 'verified' || t.status === 'moved-manual' || t.status === 'moved-elsewhere') return true; /* v3769 shown */",
     "replace": "if (false) return true; /* v3769 shown */",
     "matches": 1},
    {"why": "The list no longer draws the target grid, so the cell is words without the item's art.",
     "file": "bible.html",
     "find": "      return (typeof gridHtml === 'function') ? gridHtml(it, d[0], d[1], cell, { area: area, page: 0, label: label }) : '';",
     "replace": "      return '';",
     "matches": 1},
    {"why": "The vault render no longer paints the move list.",
     "file": "bible.html",
     "find": "try { if (typeof window._vaultMovePaint === 'function') window._vaultMovePaint(); } catch (eMv) {} /* v3769 move paint */",
     "replace": "try { /* v3769 move paint removed */ } catch (eMv) {}",
     "matches": 1},
    {"why": "The fullscreen viewer no longer asks for the cell mark.",
     "file": "bible.html",
     "find": "window._vaultMoveCellMarkHtml(meta.cell)",
     "replace": "''",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
