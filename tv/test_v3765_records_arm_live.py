# -*- coding: utf-8 -*-
"""#76 INC-3 live (v3765) — PAGE LOAD CALLS THE ARM ONCE.

v3764 left window._vaultRecordsArm dormant. This law is the one page-load call, from
_seedCleanseArm, and the reads that follow it. d2r_vaultRecords is the source for FIND,
GRAIL-DUPES and the vault header once the store is a real records array. A presence set
piece is one record at one location. The shelf card and the locker Items box print that
census. Undo is window._vaultRecordsMigrateUndo.

An unknown dock, an unreadable witness, an unreadable d2r_muleAssign or a wrong store
shape does not stamp. Page load does not arm when the set-piece reconcile refuses.
A successful owned, copies or assign write re-persists and confirms the readback when
the full row that derivation would write differs from the stored row. That row is
the one persist writes, including prov and provUnknown, so a multi-keep add, a Magic
& Rare membership change, and a witness-only change are all changes. A refusal or a short readback drops the stamp and writes a
dirty marker, so a reload follows the live model. A dirty marker still present bypasses
the migrate already path, and the marker clears only when the removal reads back gone. The source consumes a store only
while that stamp is current and no row is an unreadable witness. A shared-locker name
finds the shared locker. A reset holds refresh until the clears finish, then refreshes
once. FIND and GRAIL-DUPES read that source through the UI seams. copies[] is not
rewritten. recId stays positional (REG-2272 item 4): a dropped copy reuses the prefix
id. That item stays open. The write door stays shut on sabotage alone.

The functions are extracted from bible.html and run in node on a seeded fixture, with an
in-memory window.LSR. A missing node raises. RED_PROOF below.
[[heart-first]] [[the-unjoined-end]] [[unknown-stays-unknown]] [[regression-guard]]
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

EXTRACT = [
    "_sharedNames", "_sharedCopyCount", "_sharedCappedCopies", "_vaultSharedOverflowCells",
    "_vaultSharedOverflowNames", "_vaultDupesNames", "_vaultDupesCells", "_vaultSharedOverflowHtml",
    "_vaultPresenceSpan", "_mkWant", "_mkDest", "_mkSetWant", "_assignStoreUnknown", "_vaultRecords", "_vaultRecordsSource",
    "_vaultRecordsStampOk", "_vrRecDirty", "_vrRecMarkDirty", "_vrRecClearDirty",
    "_vrRecWitness", "_vrRecRow", "_vrRecRowsFrom", "_vrRecCanon",
    "_vrRecDerivedCanon", "_vrRecStoredCanon",
    "_vrRecSig", "_vrRecSigSame", "_vrRecNoteSig", "_vrRecHome",
    "_vaultLockerItems", "_vaultRecordsHeader", "_vaultRecordsFind", "_vaultSameMuleCopies", "_vaultRecordsOverflow",
    "_vrRecLoadRaw", "_vrRecGuardedSet", "_vrLocForCopy", "_vaultRecordsLoad",
    "_vaultRecordsPersist", "_vaultRecordsRefresh", "_vaultRecordsMigrate",
    "_vaultRecordsMigrateUndo", "_vaultRecordsMayArm", "_vaultRecordsArm",
    "_shelfCopyCount", "_shelfDrawNames", "_muleLoad", "_vaultPlanCis", "_vaultPlanCell",
    "_inMagicRare", "_dockNames", "_vaultWhereIs", "_vaultFindHome", "_vfNorm", "_vfKey", "_vfVaultKey", "_vaultFindMatches",
    "saveA", "persistOwned",
]

PREAMBLE = r"""
var window = globalThis;
window.D2R_PROFILE = 'main';
console.info = function(){ try { process.stderr.write('[info] ' + Array.prototype.join.call(arguments, ' ') + '\n'); } catch (e) {} };
console.log = console.info;
console.warn = function(){ try { process.stderr.write('[warn] ' + Array.prototype.join.call(arguments, ' ') + '\n'); } catch (e) {} };
var _LSRDATA = {};
window.LSR = {
  getItem: function(k){ return Object.prototype.hasOwnProperty.call(_LSRDATA, k) ? _LSRDATA[k] : null; },
  setItem: function(k, v){ _LSRDATA[k] = String(v); },
  removeItem: function(k){ delete _LSRDATA[k]; }
};
var _VR_STORE_KEY = 'd2r_vaultRecords';
var _VRM_KEY = 'd2r_vaultRecordsMigrate';
var _VRM_VER = 1;
var _vrRecUnread = {};
var _vrRecFollowLive = false;
var _VR_DIRTY_KEY = 'd2r_vaultRecordsDirty';
var _vrRecHold = 0;
var _vrRecSigSeen = null;
var _muleUnread = {};
var AK = 'd2r_muleAssign';
var LS = window.LSR;
var NATALYA = "Natalya's Totem";
var TAL = "Tal Rasha's Guardianship";
var IK = "Immortal King's Soul Cage";
var ENIGMA = "Enigma";
var GRIFFON = "Griffon's Eye";
var assign = {};
assign[NATALYA] = 'mule-sets';
assign[TAL] = 'mule-sets';
assign[IK] = 'mule-sets';
assign[ENIGMA] = 'mule-sets';
assign[GRIFFON] = 'shared';
var copies = {};
copies[NATALYA] = 4;
copies[TAL] = 4;
copies[IK] = 3;
copies[ENIGMA] = 2;
copies[GRIFFON] = 4;
var OWNED = [NATALYA, TAL, IK, ENIGMA, GRIFFON];
var multiKeep = {};
var SET_PIECES = {};
SET_PIECES[NATALYA] = 1;
SET_PIECES[TAL] = 1;
SET_PIECES[IK] = 1;
window._vfIsSetPiece = function(n){ return !!SET_PIECES[n]; };
var _SHARED_COPY_CAP = 2, _MULE_COPY_CAP = 3;
function ownedPool(){ return OWNED.slice(); }
function copyCount(n){ var c = copies[n]; return (c && c > 0) ? c : (OWNED.indexOf(n) >= 0 ? 1 : 0); }
function isSharedStash(n){ return false; }
function muleById(id){
  if (id === 'shared') return { id: 'shared', name: 'SHARED STASH', icon: '' };
  return (id === 'mule-sets' || id === 'mule-other') ? { id: id, name: id } : null;
}
window._carriedNames = function(){ return []; }
function esc(t){ return String(t == null ? '' : t); }
function art(){ return ''; }
function isAggregate(){ return false; }
function _vfCanon(n){ return n; }
var _VF_ALIAS = {};
var magicFinds = {};
var document = { getElementById: function(){ return null; } };
function mountFind(){
  var box = { hidden: true, innerHTML: '' };
  document.getElementById = function(id){
    if (id === 'vault-find-results') return box;
    if (id === 'vault-find-input') return { value: '' };
    return null;
  };
  return box;
}
function askFind(q){ var box = mountFind(); window.vaultFind(q); return box.innerHTML; }
var mf = 0, players = 1, wishlist = new Set(), owned = new Set(OWNED);
var etherealItems = new Set(), superiorBases = new Set(), unknownReads = new Set();
var statues = new Set(), bossFilters = {}, bossSorts = {}, setPieces = new Set();
var runeStash = {}, rwMade = {}, materialStash = {}, gemStash = {}, craftStash = {}, craftBaseStash = {};
var pinnedBoss = null;
function _writeGrailFarm(){}
var KEEP_IN_INVENTORY = /Annihilus|Hellfire Torch|Gheed/;
function _keepName(n){ return n; }
function _mpInvSeeds(){ return { hold: {}, at: {}, bad: [], n: 0 }; }
function vaultSize(){ return [1, 1]; }
function tipOf(){ return null; }
function _muleItemKey(n, ci){ return ci ? n + ' #' + (ci + 1) : n; }
function _mulePosAll(){ return {}; }
var MULE_STASH_W = 10, MULE_STASH_H = 10, MULE_INV_W = 10, MULE_INV_H = 4, MULE_CAP = 140;
var MULE_AREAS = {
  personal: [10, 10, 'Personal'], shared: [10, 10, 'Shared'], gems: [10, 10, 'Gems'],
  materials: [10, 10, 'Materials'], runes: [10, 10, 'Runes'], inv: [10, 4, 'Inventory']
};
function packGrid(items){
  var placed = (items || []).map(function(it, i){
    return { n: it.n, key: it.key, x: 0, y: i, w: it.w || 1, h: it.h || 1 };
  });
  return { placed: placed, left: [] };
}
"""


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


def _window_fn(src, name):
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


def _strip(src):
    return re.sub(r"/\*.{0,4000}?\*/", "", src, flags=re.S)


def _const_arrow(src, name):
    m = re.search(r"\bconst %s = \(\) => \{" % re.escape(name), src)
    if not m:
        raise AssertionError("could not find const %s" % name)
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
    raise AssertionError("unbalanced braces extracting const %s" % name)


def _slice(src, start, end):
    a = src.index(start)
    b = src.index(end, a) + len(end)
    return src[a:b]


class TestV3765RecordsArmLive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not NODE:
            raise AssertionError("node is not on this machine — this law does not skip")
        with open(BIBLE, encoding="utf-8") as f:
            cls.src = f.read()
        cls.fns = "\n".join(_fn(cls.src, n) for n in EXTRACT)
        cls.loader = _slice(cls.src, "  function load(k,f){",
                            "  window._muleStoreUnread = function(k){ return _muleUnread[k || AK] || null; };")
        cls.persist_js = _const_arrow(cls.src, "persist")
        cls.vault_find = _assigned_fn(cls.src, "vaultFind")

    def _line(self, needle):
        hits = [ln.strip() for ln in self.src.splitlines() if needle in ln]
        if len(hits) != 1:
            raise AssertionError("%r matched %d lines" % (needle, len(hits)))
        return hits[0]

    def _run(self, scenario, extra=""):
        prog = (PREAMBLE + self.fns + "\n" + self.loader + "\n" + self.persist_js + "\n" +
                self.vault_find +
                "\nwindow._vaultPresenceSpan = _vaultPresenceSpan;\n"
                "window._vaultRecordsMayArm = _vaultRecordsMayArm;\n"
                "window._vaultRecordsRefresh = _vaultRecordsRefresh;\n" +
                extra +
                "\nvar out = {};\n" + scenario +
                "\nprocess.stdout.write(JSON.stringify(out));\n")
        p = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 0, (p.stderr or p.stdout)[-2000:])
        return json.loads(p.stdout)

    def test_page_load_calls_the_arm_once(self):
        code = _strip(self.src)
        self.assertEqual(code.count("_vaultRecordsArm("), 2,
                         "arm sites drifted from the definition plus the one page-load call")
        self.assertEqual(code.count("_vaultRecordsMigrate("), 2,
                         "a second caller of the migrate function appeared")
        self.assertEqual(code.count("_vaultRecordsPersist("), 7,
                         "persist callers drifted from the definition, the migration, the write refresh, the two move-list writers, the register wrapper, and the per-copy entry writer (REG-2844)")
        body = _strip(_assigned_fn(self.src, "_seedCleanseArm"))
        self.assertEqual(body.count("_vaultRecordsArm("), 1,
                         "the page-load call is not the one inside _seedCleanseArm")
        self.assertIn("window._vaultRecordsMayArm(_spr)", body)
        self.assertIn("window._vaultRecordsMigrateUndo", code)

    def test_a_presence_set_piece_is_one_record_at_one_location(self):
        o = self._run(r"""
var before = JSON.stringify(copies);
var a = _vaultRecordsArm();
var loaded = _vaultRecordsLoad();
function pack(name){
  return loaded.records.filter(function(r){ return r.name === name; }).map(function(r){
    return r.loc;
  });
}
out.stamped = !!(a && a.stamped);
out.seam = a && a.seam;
out.copyIdentity = a && a.copyIdentity;
out.nat = pack(NATALYA);
out.tal = pack(TAL);
out.ik = pack(IK);
out.enigma = pack(ENIGMA);
out.griffon = pack(GRIFFON);
out.copiesSame = JSON.stringify(copies) === before;
out.shelfNat = _shelfDrawNames([NATALYA], 'mule-sets').length;
out.shelfTal = _shelfDrawNames([TAL], 'mule-sets').length;
out.shelfIk = _shelfDrawNames([IK], 'mule-sets').length;
out.shelfEnigma = _shelfDrawNames([ENIGMA], 'mule-sets').length;
out.physNat = _muleLoad([NATALYA], null, 'mule-sets', {}).phys;
out.physTal = _muleLoad([TAL], null, 'mule-sets', {}).phys;
out.physIk = _muleLoad([IK], null, 'mule-sets', {}).phys;
out.physEnigma = _muleLoad([ENIGMA], null, 'mule-sets', {}).phys;
out.storedCopies = copies[NATALYA];
""")
        self.assertTrue(o["stamped"], o)
        self.assertEqual(o["seam"], "page-load")
        self.assertEqual(o["copyIdentity"], "positional")
        self.assertEqual(o["nat"], ["mule-sets"], "Natalya x4 stayed more than one record: %r" % o["nat"])
        self.assertEqual(o["tal"], ["mule-sets"], "Tal Guardianship x4 stayed more than one record: %r" % o["tal"])
        self.assertEqual(o["ik"], ["mule-sets"], "IK Soul Cage x3 stayed more than one record: %r" % o["ik"])
        self.assertEqual(o["enigma"], ["mule-sets", "mule-sets"],
                         "a non-set spare was collapsed: %r" % o["enigma"])
        self.assertEqual(o["griffon"], ["shared", "shared", "shared", "shared"],
                         "a shared copy left the mule: %r" % o["griffon"])
        self.assertTrue(o["copiesSame"], "the span rewrote copies[]")
        self.assertEqual(o["storedCopies"], 4)
        self.assertEqual(o["shelfNat"], 1, o)
        self.assertEqual(o["shelfTal"], 1, o)
        self.assertEqual(o["shelfIk"], 1, o)
        self.assertEqual(o["shelfEnigma"], 2, o)
        self.assertEqual(o["physNat"], 1, o)
        self.assertEqual(o["physTal"], 1, o)
        self.assertEqual(o["physIk"], 1, o)
        self.assertEqual(o["physEnigma"], 2, o)

    def test_an_explicit_multi_keep_keeps_the_spare(self):
        o = self._run(r"""
multiKeep[IK] = 2;
var before = copies[IK];
_vaultRecordsArm();
var loaded = _vaultRecordsLoad();
out.ik = loaded.records.filter(function(r){ return r.name === IK; }).length;
out.nat = loaded.records.filter(function(r){ return r.name === NATALYA; }).length;
out.copies = copies[IK];
out.before = before;
""")
        self.assertEqual(o["ik"], 3, "a multi-keep above 1 was collapsed: %r" % o)
        self.assertEqual(o["nat"], 1, o)
        self.assertEqual(o["copies"], o["before"])

    def test_the_card_and_the_items_box_print_one_census(self):
        card = self._line("var _ci76 = _vaultLockerItems(m.id)")
        locker = self._line("var _li76 = _vaultLockerItems(muleId)")
        o = self._run(r"""
_vaultRecordsArm();
assign.Shako = 'mule-sets';
OWNED.push('Shako');
owned.add('Shako');
persist();
var liveNames = [NATALYA, TAL, IK, ENIGMA, 'Shako'];
var muleId = 'mule-sets';
var m = { id: muleId };
var _physN = _muleLoad(liveNames, null, muleId, {}).phys;
var _itemN = -1;
var _namesN = -1;
""" + "\n" + card + "\n" + locker + r"""
var drawn = _shelfDrawNames(liveNames, muleId);
var tiles = {};
drawn.forEach(function(n){ tiles[n] = 1; });
out.itemN = _itemN;
out.namesN = _namesN;
out.physN = _physN;
out.census = _vaultLockerItems(muleId);
out.tiles = Object.keys(tiles).length;
""")
        self.assertEqual(o["census"], 5, "the write did not move the census to the five names: %r" % o)
        self.assertEqual(o["itemN"], o["census"], "the card did not print the census: %r" % o)
        self.assertEqual(o["namesN"], o["census"], "the Items box did not print the census: %r" % o)
        self.assertEqual(o["itemN"], o["namesN"], "card and Items diverged: %r" % o)
        self.assertEqual(o["tiles"], o["census"], "the shelf tiles did not match the census: %r" % o)
        self.assertGreater(o["physN"], o["itemN"],
                           "the shared count was the physical copy total: %r" % o)

    def test_find_and_dupes_read_the_persisted_store(self):
        card = self._line("var _ovNames = (m.id === 'dupes') ? _vaultDupesNames() : [];")
        self._line("var _ovNames = _vaultDupesNames();")
        o = self._run(r"""
_vaultRecordsArm();
copies[GRIFFON] = 1;
assign[NATALYA] = 'mule-other';
var m = { id: 'dupes' };
""" + "\n" + card + r"""
out.find = askFind('natalya');
out.card = _ovNames.slice();
out.html = _vaultSharedOverflowHtml();
out.lockerDupes = _vaultLockerItems('dupes');
out.spare = _vaultDupesCells(GRIFFON);
out.liveOverflow = _vaultSharedOverflowNames();
out.liveFind = (function(){
  var w = _vaultWhereIs(NATALYA);
  return w && w.mule;
})();
""")
        self.assertIn("mule-sets", o["find"], "FIND left the persisted store: %r" % o)
        self.assertNotIn("mule-other", o["find"], o)
        self.assertEqual(o["card"], [], "a copy was listed as GRAIL-DUPES: %r" % o)
        self.assertNotIn("Griffon's Eye", o["html"], "the dupes window drew a copy: %r" % o)
        self.assertEqual(o["lockerDupes"], 0, "the dupes count listed a copy: %r" % o)
        self.assertEqual(o["spare"], 0, o)
        self.assertEqual(o["liveOverflow"], [], o)
        self.assertEqual(o["liveFind"], "mule-other", o)

    def test_add_delete_and_move_refresh_counts_tiles_find_and_dupes(self):
        card = self._line("var _ovNames = (m.id === 'dupes') ? _vaultDupesNames() : [];")
        o = self._run(r"""
_vaultRecordsArm();
function tiles(id){
  var names = OWNED.filter(function(n){ return assign[n] === id; });
  var drawn = _shelfDrawNames(names, id);
  var seen = {};
  drawn.forEach(function(n){ seen[n] = 1; });
  return Object.keys(seen).length;
}
assign.Shako = 'mule-sets';
OWNED.push('Shako');
owned.add('Shako');
persist();
var m = { id: 'dupes' };
""" + "\n" + card + r"""
out.addCensus = _vaultLockerItems('mule-sets');
out.addTiles = tiles('mule-sets');
out.addFind = askFind('shako');
out.addDupes = _ovNames.slice();
OWNED = OWNED.filter(function(n){ return n !== 'Shako'; });
delete assign.Shako;
owned.delete('Shako');
persistOwned();
out.delCensus = _vaultLockerItems('mule-sets');
out.delTiles = tiles('mule-sets');
out.delFind = askFind('shako');
assign[NATALYA] = 'mule-other';
saveA();
out.moveFind = askFind('natalya');
out.moveCensus = _vaultLockerItems('mule-sets');
out.moveTiles = tiles('mule-sets');
out.moveOther = _vaultLockerItems('mule-other');
copies[GRIFFON] = 1;
persist();
m = { id: 'dupes' };
""" + "\n" + card + r"""
out.dupesCard = _ovNames.slice();
out.dupesHtml = _vaultSharedOverflowHtml();
out.dupesLive = _vaultSharedOverflowNames();
""")
        self.assertEqual(o["addCensus"], 5, o)
        self.assertEqual(o["addTiles"], 5, o)
        self.assertIn("mule-sets", o["addFind"], o)
        self.assertEqual(o["addDupes"], [], o)
        self.assertEqual(o["delCensus"], 4, o)
        self.assertEqual(o["delTiles"], 4, o)
        self.assertIn("no vaulted item matches", o["delFind"], o)
        self.assertIn("mule-other", o["moveFind"], o)
        self.assertNotIn("mule-sets", o["moveFind"], o)
        self.assertEqual(o["moveCensus"], 3, o)
        self.assertEqual(o["moveTiles"], 3, o)
        self.assertEqual(o["moveOther"], 1, o)
        self.assertEqual(o["dupesCard"], [], o)
        self.assertNotIn("Griffon's Eye", o["dupesHtml"], o)
        self.assertEqual(o["dupesLive"], [], o)

    def test_an_unreadable_assignment_does_not_stamp(self):
        o = self._run(r"""
_vaultRecordsArm();
out.stampedFirst = window.LSR.getItem('d2r_vaultRecordsMigrate') != null;
window.LSR.setItem('d2r_muleAssign', '{bad');
assign = load('d2r_muleAssign', {});
var dock = _dockNames();
out.unread = window._muleStoreUnread('d2r_muleAssign');
out.dock = dock;
out.assignEmpty = Object.keys(assign).length === 0;
window.LSR.removeItem('d2r_vaultRecords');
window.LSR.removeItem('d2r_vaultRecordsMigrate');
_vrRecUnread = {};
var a = _vaultRecordsArm();
out.stamped = !!(a && a.stamped);
out.unknown = !!(a && a.unknown);
out.store = window.LSR.getItem('d2r_vaultRecords') != null;
out.stamp = window.LSR.getItem('d2r_vaultRecordsMigrate') != null;
_vrRecFollowLive = false;
window.LSR.removeItem('d2r_vaultRecordsDirty');
window.LSR.setItem('d2r_vaultRecordsMigrate', JSON.stringify({ ver: 1 }));
window.LSR.setItem('d2r_vaultRecords', JSON.stringify({ v: 1, records: [
  { recId: 'rec_1', name: NATALYA, copyIx: 0, kind: 'filed', mule: 'mule-sets', loc: 'mule-sets' }
]}));
out.find = askFind('natalya');
""")
        self.assertTrue(o["stampedFirst"], o)
        self.assertEqual(o["unread"], "will not parse", o)
        self.assertTrue(o["assignEmpty"], o)
        self.assertIsInstance(o["dock"], list, o)
        self.assertGreater(len(o["dock"]), 0, "the real dock did not list the loose names: %r" % o)
        self.assertFalse(o["stamped"], "an unreadable assignment stamped: %r" % o)
        self.assertTrue(o["unknown"], o)
        self.assertFalse(o["store"], o)
        self.assertFalse(o["stamp"], o)
        self.assertNotIn("mule-sets", o["find"],
                         "FIND kept the stamped home over an unreadable assignment: %r" % o)

    def test_reconcile_refusal_does_not_arm(self):
        extra = "\n".join([
            _fn(self.src, "_bfJson"),
            _fn(self.src, "_assignMap"),
            _assigned_fn(self.src, "_setPieceReconcile"),
        ])
        o = self._run(r"""
window.vaultRemove = function(){ return { removed: [] }; };
window._vfCanon = function(n){ return n; };
var _SPR_KEY = 'd2r_setPieceReconcile', _SPR_VER = 3;
window.LSR.setItem('d2r_muleAssign', '{bad');
var rec = window._setPieceReconcile({});
out.why = rec && rec.why;
out.may = window._vaultRecordsMayArm(rec);
var called = false;
var real = window._vaultRecordsArm;
window._vaultRecordsArm = function(){ called = true; return real(); };
if (typeof window._vaultRecordsMayArm === 'function' && window._vaultRecordsMayArm(rec)) window._vaultRecordsArm();
out.called = called;
""", extra=extra)
        self.assertIn("d2r_muleAssign would not read", o["why"] or "", o)
        self.assertFalse(o["may"], o)
        self.assertFalse(o["called"], "the arm ran after reconcile refused: %r" % o)

    def test_a_refused_refresh_follows_the_live_model(self):
        card = self._line("var _ovNames = (m.id === 'dupes') ? _vaultDupesNames() : [];")
        o = self._run(r"""
_vaultRecordsArm();
_dockNames = function(){ return null; };
copies[GRIFFON] = 1;
persist();
window.LSR.setItem('d2r_vaultRecordsMigrate', JSON.stringify({ ver: 1 }));
window.LSR.removeItem('d2r_vaultRecordsDirty');
var m = { id: 'dupes' };
""" + "\n" + card + r"""
out.card = _ovNames.slice();
out.html = _vaultSharedOverflowHtml();
out.live = _vaultSharedOverflowNames();
out.find = askFind('natalya');
""")
        self.assertEqual(o["live"], [], o)
        self.assertEqual(o["card"], [], "GRAIL-DUPES kept the stale store after a refused refresh: %r" % o)
        self.assertNotIn("Griffon's Eye", o["html"], o)
        self.assertIn("mule-sets", o["find"], o)

    def test_a_short_readback_follows_the_live_model(self):
        o = self._run(r"""
_vaultRecordsArm();
var realSet = window.LSR.setItem.bind(window.LSR);
window.LSR.setItem = function(k, v){
  if (k === 'd2r_vaultRecords') {
    var obj = JSON.parse(v);
    obj.records = obj.records.slice(0, 1);
    return realSet(k, JSON.stringify(obj));
  }
  return realSet(k, v);
};
assign.Shako = 'mule-sets';
OWNED.push('Shako');
owned.add('Shako');
persist();
window.LSR.setItem('d2r_vaultRecordsMigrate', JSON.stringify({ ver: 1 }));
window.LSR.removeItem('d2r_vaultRecordsDirty');
out.census = _vaultLockerItems('mule-sets');
out.stored = JSON.parse(window.LSR.getItem('d2r_vaultRecords')).records.length;
out.find = askFind('shako');
""")
        self.assertEqual(o["stored"], 1, o)
        self.assertEqual(o["census"], 5, "a short readback still fed the card: %r" % o)
        self.assertIn("mule-sets", o["find"], o)

    def test_an_unknown_dock_does_not_stamp(self):
        o = self._run(r"""
function probe(mode){
  _vrRecUnread = {};
  window.LSR.removeItem('d2r_vaultRecords');
  window.LSR.removeItem('d2r_vaultRecordsMigrate');
  if (OWNED.indexOf('Nagelring') < 0) OWNED.push('Nagelring');
  if (mode === 'missing') _dockNames = null;
  if (mode === 'null') _dockNames = function(){ return null; };
  var a = _vaultRecordsArm();
  return {
    stamped: !!(a && a.stamped),
    unknown: !!(a && a.unknown),
    store: window.LSR.getItem('d2r_vaultRecords') != null,
    stamp: window.LSR.getItem('d2r_vaultRecordsMigrate') != null
  };
}
out.missing = probe('missing');
out.nullDock = probe('null');
""")
        for which in ("missing", "nullDock"):
            row = o[which]
            self.assertFalse(row["stamped"], which + " stamped: %r" % row)
            self.assertTrue(row["unknown"], which + " was not UNKNOWN: %r" % row)
            self.assertFalse(row["store"], which)
            self.assertFalse(row["stamp"], which)

    def test_a_wrong_shape_store_does_not_stamp(self):
        o = self._run(r"""
function probe(raw){
  _vrRecUnread = {};
  window.LSR.setItem('d2r_vaultRecords', raw);
  window.LSR.removeItem('d2r_vaultRecordsMigrate');
  var a = _vaultRecordsArm();
  return {
    stamped: !!(a && a.stamped),
    bytes: window.LSR.getItem('d2r_vaultRecords'),
    stamp: window.LSR.getItem('d2r_vaultRecordsMigrate') != null
  };
}
out.arr = probe('[]');
out.obj = probe('{"v":1}');
out.badRec = probe('{"records":{}}');
""")
        for key, raw in (("arr", "[]"), ("obj", '{"v":1}'), ("badRec", '{"records":{}}')):
            row = o[key]
            self.assertFalse(row["stamped"], key + " stamped: %r" % row)
            self.assertEqual(row["bytes"], raw, key + " was overwritten: %r" % row)
            self.assertFalse(row["stamp"], key)

    def test_an_unreadable_witness_does_not_stamp(self):
        o = self._run(r"""
window.LSR.setItem('d2r_vaultProv', '{bad');
var a = _vaultRecordsArm();
var loaded = _vaultRecordsLoad();
out.stamped = !!(a && a.stamped);
out.unknown = !!(a && a.unknown);
out.store = window.LSR.getItem('d2r_vaultRecords') != null;
out.stamp = window.LSR.getItem('d2r_vaultRecordsMigrate') != null;
out.marked = !!(loaded && loaded.records.length && loaded.records.every(function(r){
  return r.provUnknown === true && !('prov' in r);
}));
""")
        self.assertFalse(o["stamped"], "an unreadable witness stamped: %r" % o)
        self.assertTrue(o["unknown"], o)
        self.assertTrue(o["store"], "persist did not leave the marker store: %r" % o)
        self.assertFalse(o["stamp"], o)
        self.assertTrue(o["marked"], "the marker was stored as a null witness: %r" % o)

    def test_undo_clears_both_keys_and_a_stamp_throw_leaves_the_store(self):
        o = self._run(r"""
var copiesBefore = JSON.stringify(copies);
var assignBefore = JSON.stringify(assign);
_vaultRecordsArm();
var u = _vaultRecordsMigrateUndo();
out.undone = !!(u && u.undone);
out.store = window.LSR.getItem('d2r_vaultRecords') != null;
out.stamp = window.LSR.getItem('d2r_vaultRecordsMigrate') != null;
out.copiesSame = JSON.stringify(copies) === copiesBefore;
out.assignSame = JSON.stringify(assign) === assignBefore;
var again = _vaultRecordsArm();
out.rearmed = !!(again && again.stamped);
var realRemove = window.LSR.removeItem.bind(window.LSR);
window.LSR.removeItem = function(k){
  if (k === 'd2r_vaultRecordsMigrate') throw new Error('stamp disk');
  return realRemove(k);
};
var u2 = _vaultRecordsMigrateUndo();
out.throwUndone = !!(u2 && u2.undone);
out.throwStore = window.LSR.getItem('d2r_vaultRecords') != null;
out.throwStamp = window.LSR.getItem('d2r_vaultRecordsMigrate') != null;
""")
        self.assertTrue(o["undone"], o)
        self.assertFalse(o["store"], o)
        self.assertFalse(o["stamp"], o)
        self.assertTrue(o["copiesSame"], o)
        self.assertTrue(o["assignSame"], o)
        self.assertTrue(o["rearmed"], o)
        self.assertFalse(o["throwUndone"], "a stamp remove that threw reported undone: %r" % o)
        self.assertTrue(o["throwStore"], "a stamp remove that threw dropped the store: %r" % o)
        self.assertTrue(o["throwStamp"], o)

    def test_a_dropped_copy_reuses_the_prefix_id(self):
        """REG-2272 item 4 stays open. The survivor takes the lower positional id.

        No cell, witness or frame was named as the per-copy anchor, so this law does not
        invent one. The arm keeps reporting copyIdentity positional."""
        o = self._run(r"""
_vaultRecordsPersist();
var loaded = _vaultRecordsLoad();
var ids = loaded.records.filter(function(r){ return r.name === ENIGMA; }).map(function(r){ return r.recId; });
copies[ENIGMA] = 1;
_vaultRecordsPersist();
var loaded2 = _vaultRecordsLoad();
var ids2 = loaded2.records.filter(function(r){ return r.name === ENIGMA; }).map(function(r){ return r.recId; });
var a = _vaultRecordsArm();
out.ids = ids;
out.ids2 = ids2;
out.copyIdentity = a && a.copyIdentity;
""")
        self.assertEqual(len(o["ids"]), 2, o)
        self.assertEqual(o["ids2"], [o["ids"][0]],
                         "a dropped copy did not keep the positional prefix id: %r" % o)
        self.assertEqual(o["copyIdentity"], "positional", o)

    def test_a_shared_locker_item_finds_the_shared_locker(self):
        """Griffon's Eye is filed in the shared locker. FIND must name that locker, not the dock."""
        o = self._run(r"""
_vaultRecordsArm();
out.find = askFind('griffon');
""")
        self.assertIn("SHARED STASH", o["find"], "FIND did not name the shared locker: %r" % o)
        self.assertNotIn("unsorted", o["find"], "a shared filing was sent to the dock: %r" % o)
        self.assertNotIn("in the dock", o["find"], o)

    def test_a_short_readback_stays_live_after_reload(self):
        """The follow-live flag dies with the page. The stamp drop or the dirty marker has to remain."""
        o = self._run(r"""
_vaultRecordsArm();
var realSet = window.LSR.setItem.bind(window.LSR);
window.LSR.setItem = function(k, v){
  if (k === 'd2r_vaultRecords') {
    var obj = JSON.parse(v);
    obj.records = obj.records.slice(0, 1);
    return realSet(k, JSON.stringify(obj));
  }
  return realSet(k, v);
};
assign.Shako = 'mule-sets';
OWNED.push('Shako');
owned.add('Shako');
persist();
_vrRecFollowLive = false;
out.census = _vaultLockerItems('mule-sets');
out.stored = JSON.parse(window.LSR.getItem('d2r_vaultRecords')).records.length;
out.stamp = window.LSR.getItem('d2r_vaultRecordsMigrate') != null;
out.dirty = window.LSR.getItem('d2r_vaultRecordsDirty') != null;
""")
        self.assertEqual(o["stored"], 1, o)
        self.assertEqual(o["census"], 5, "a reload served the truncated store: %r" % o)
        self.assertTrue((not o["stamp"]) or o["dirty"], "neither the stamp nor the dirty marker moved: %r" % o)

    def test_a_refused_refresh_stays_live_after_reload(self):
        card = self._line("var _ovNames = (m.id === 'dupes') ? _vaultDupesNames() : [];")
        o = self._run(r"""
_vaultRecordsArm();
_dockNames = function(){ return null; };
copies[GRIFFON] = 1;
persist();
_vrRecFollowLive = false;
var m = { id: 'dupes' };
""" + "\n" + card + r"""
out.card = _ovNames.slice();
out.stamp = window.LSR.getItem('d2r_vaultRecordsMigrate') != null;
out.dirty = window.LSR.getItem('d2r_vaultRecordsDirty') != null;
""")
        self.assertEqual(o["card"], [], "a reload served the stale dupes snapshot: %r" % o)
        self.assertTrue((not o["stamp"]) or o["dirty"], o)

    def test_undo_then_persist_does_not_create_a_store(self):
        """No stamp, no store. An ordinary persist must not recreate one the source would then consume."""
        o = self._run(r"""
_vaultRecordsArm();
_vaultRecordsMigrateUndo();
assign[NATALYA] = 'mule-other';
var writes = 0;
var real = window.LSR.setItem.bind(window.LSR);
window.LSR.setItem = function(k, v){
  if (k === 'd2r_vaultRecords') writes++;
  return real(k, v);
};
persist();
out.writes = writes;
out.store = window.LSR.getItem('d2r_vaultRecords') != null;
_vrRecFollowLive = false;
window.LSR.removeItem('d2r_vaultRecordsDirty');
out.census = _vaultLockerItems('mule-sets');
""")
        self.assertEqual(o["writes"], 0, "refresh created a store with no stamp: %r" % o)
        self.assertFalse(o["store"], o)
        self.assertEqual(o["census"], 3, "an unstamped store became the census: %r" % o)

    def test_an_unstamped_store_is_not_the_source_after_reload(self):
        o = self._run(r"""
_vaultRecordsArm();
window.LSR.removeItem('d2r_vaultRecordsMigrate');
window.LSR.removeItem('d2r_vaultRecordsDirty');
window.LSR.setItem('d2r_vaultRecords', JSON.stringify({ v: 1, records: [
  { recId: 'rec_9', name: NATALYA, copyIx: 0, kind: 'filed', mule: 'mule-sets', loc: 'mule-sets' }
]}));
_vrRecFollowLive = false;
out.census = _vaultLockerItems('mule-sets');
""")
        self.assertEqual(o["census"], 4, "an unstamped store survived a reload: %r" % o)

    def test_a_prov_unknown_snapshot_is_not_the_source_after_reload(self):
        """A planted stamp does not make an unreadable witness the source. A store that was never stamped does not either."""
        o = self._run(r"""
function plant(stamp){
  _vrRecFollowLive = false;
  window.LSR.removeItem('d2r_vaultRecordsDirty');
  if (stamp) window.LSR.setItem('d2r_vaultRecordsMigrate', JSON.stringify({ ver: 1 }));
  else window.LSR.removeItem('d2r_vaultRecordsMigrate');
  window.LSR.setItem('d2r_vaultRecords', JSON.stringify({ v: 1, records: [
    { recId: 'rec_9', name: NATALYA, copyIx: 0, kind: 'filed', mule: 'mule-sets', provUnknown: true }
  ]}));
  return _vaultLockerItems('mule-sets');
}
out.stamped = plant(true);
out.never = plant(false);
""")
        self.assertEqual(o["stamped"], 4, "a provUnknown snapshot was the source: %r" % o)
        self.assertEqual(o["never"], 4, "a never-stamped provUnknown snapshot was the source: %r" % o)

    def test_an_unchanged_persist_does_not_rewrite_the_records_store(self):
        o = self._run(r"""
_vaultRecordsArm();
var writes = 0;
var real = window.LSR.setItem.bind(window.LSR);
window.LSR.setItem = function(k, v){
  if (k === 'd2r_vaultRecords') writes++;
  return real(k, v);
};
mf = 250;
players = 8;
_vrRecSigSame = function(){ return false; };
persist();
out.idle = writes;
assign[NATALYA] = 'mule-other';
persist();
out.moved = writes;
""")
        self.assertEqual(o["idle"], 0, "an unchanged persist rewrote d2r_vaultRecords: %r" % o)
        self.assertEqual(o["moved"], 1, "a real assign change did not refresh: %r" % o)

    def test_a_multi_keep_add_refreshes_the_presence_span(self):
        """vaultMultiKeepAdd writes only multiKeep. Natalya's span leaves 1 and the store must follow."""
        o = self._run(r"""
_vaultRecordsArm();
function _resolveGrailName(){ return null; }
function status(){}
function renderMultiKeep(){}
function renderVaultRegistered(){}
window._vfCanon = function(n){ return n; };
var input = { value: NATALYA };
document.getElementById = function(id){ return id === 'vmk-add-input' ? input : null; };
var before = _vaultRecordsLoad().records.filter(function(r){ return r.name === NATALYA; }).length;
window.vaultMultiKeepAdd();
var stored = _vaultRecordsLoad().records.filter(function(r){ return r.name === NATALYA; }).length;
var liveRec = _vaultRecords();
var live = liveRec.records.filter(function(r){ return r.name === NATALYA; }).length;
out.before = before;
out.target = _mkWant(NATALYA);   /* REG-2900 - a keeper is {want, dest}: the target is its want */
out.stored = stored;
out.live = live;
out.header = _vaultRecordsHeader().copies;
out.liveCopies = liveRec.records.length;
""", extra=_window_fn(self.src, "vaultMultiKeepAdd") + ";\n")
        self.assertEqual(o["before"], 1, o)
        self.assertEqual(o["target"], 2, "vaultMultiKeepAdd did not set the spare target: %r" % o)
        self.assertEqual(o["live"], 4, "the live span did not open to the climbed copies: %r" % o)
        self.assertEqual(o["stored"], 4, "the store kept the collapsed record: %r" % o)
        self.assertEqual(o["header"], o["liveCopies"], "the header left the live copy total: %r" % o)
        self.assertEqual(o["header"], 12, o)

    def test_throwing_a_magic_find_refreshes_the_loose_and_orphan_counts(self):
        """vaultThrowFind drops magicFinds membership. A name stored as orphan must become loose, and the header must follow."""
        o = self._run(r"""
var HARP = "Harpoonist's Grand Charm";
OWNED.push(HARP);
magicFinds[HARP] = { q: 'rare', base: '' };
function renderVault(){}
function status(){}
_vaultRecordsArm();
var before = _vaultRecordsLoad().records.filter(function(r){ return r && r.name === HARP; })[0];
out.beforeKind = before ? before.kind : null;
out.beforeLoc = before ? before.loc : 'missing';
window.vaultThrowFind(HARP);
var row = _vaultRecordsLoad().records.filter(function(r){ return r && r.name === HARP; })[0];
var live = _vaultRecords();
var liveRow = live.records.filter(function(r){ return r && r.name === HARP; })[0];
var h = _vaultRecordsHeader();
out.kind = row ? row.kind : null;
out.loc = row ? row.loc : 'missing';
out.liveKind = liveRow ? liveRow.kind : null;
out.headerLoose = h && h.loose;
out.headerOrphans = h && h.orphans;
out.liveLoose = live.byKind.loose || 0;
out.liveOrphans = live.orphans.length;
out.magicGone = !Object.prototype.hasOwnProperty.call(magicFinds, HARP);
""", extra=_window_fn(self.src, "vaultThrowFind") + ";\n")
        self.assertEqual(o["beforeKind"], "orphan", o)
        self.assertIsNone(o["beforeLoc"], o)
        self.assertTrue(o["magicGone"], o)
        self.assertEqual(o["kind"], "loose", "the stored row stayed orphan: %r" % o)
        self.assertEqual(o["loc"], "loose", o)
        self.assertEqual(o["liveKind"], "loose", o)
        self.assertEqual(o["headerLoose"], o["liveLoose"], "header loose left the live count: %r" % o)
        self.assertEqual(o["headerOrphans"], o["liveOrphans"], "header orphans left the live count: %r" % o)
        self.assertEqual(o["headerLoose"], 1, o)
        self.assertEqual(o["headerOrphans"], 0, o)

    def test_a_dirty_marker_whose_removal_throws_is_not_already(self):
        """The first dirty removal throws. The arm re-persists, and the marker stays until a read says it is gone."""
        o = self._run(r"""
_vaultRecordsArm();
var obj = JSON.parse(window.LSR.getItem('d2r_vaultRecords'));
var full = obj.records.length;
obj.records = obj.records.slice(0, 1);
window.LSR.setItem('d2r_vaultRecords', JSON.stringify(obj));
window.LSR.setItem('d2r_vaultRecordsDirty', '1');
_vrRecFollowLive = true;
var throws = 0;
var realRemove = window.LSR.removeItem.bind(window.LSR);
window.LSR.removeItem = function(k){
  if (k === 'd2r_vaultRecordsDirty' && throws < 1) { throws++; throw new Error('dirty disk'); }
  return realRemove(k);
};
var a = _vaultRecordsArm();
out.already = !!(a && a.already);
out.stamped = !!(a && a.stamped);
out.throws = throws;
out.dirty = window.LSR.getItem('d2r_vaultRecordsDirty') != null;
out.follow = _vrRecFollowLive === true;
out.count = JSON.parse(window.LSR.getItem('d2r_vaultRecords')).records.length;
out.full = full;
""")
        self.assertEqual(o["throws"], 1, o)
        self.assertFalse(o["already"], "a dirty marker took the already path: %r" % o)
        self.assertTrue(o["stamped"], "the dirty marker did not force a confirmed re-persist: %r" % o)
        self.assertEqual(o["count"], o["full"], "the truncated store survived the re-persist: %r" % o)
        self.assertTrue(o["dirty"], "the marker was cleared without a readback: %r" % o)
        self.assertTrue(o["follow"], "the flag dropped while the marker was still stored: %r" % o)

    def test_a_light_reset_refreshes_once_after_the_clears(self):
        """Assign clears before provenance. The records store must not be rewritten in between."""
        scope = _slice(self.src,
                       "  var _VAULT_RESET_SCOPE = Object.freeze({",
                       "    try { console.info('[vault reset] ' + JSON.stringify(R)); } catch(e){}\n    return R;\n  }")
        extra = (
            "var JOURNAL_KEY = 'd2r_journal';\n"
            "var SEEN_KEY = 'd2r_seen';\n"
            "var FOLDER_DB = 'folderdb';\n"
            "var FOLDER_KEY = 'folderkey';\n"
            "var PROV_KEY = 'd2r_vaultProv';\n"
            "function _vaultRefileFromPlan(){ return; }\n"
            + _fn(self.src, "_provWrite") + "\n"
            + scope + "\n"
        )
        o = self._run(r"""
window.LSR.setItem('d2r_vaultProv', JSON.stringify((function(){
  var o = {}; o[NATALYA] = { by: 'witness', kind: 'filed' }; return o;
})()));
_vaultRecordsArm();
var realProv = _provWrite;
_provWrite = function(all){
  var rows = [];
  try { rows = JSON.parse(window.LSR.getItem('d2r_vaultRecords')).records; } catch (e) { rows = []; }
  out.midFiled = rows.some(function(r){ return r && r.kind === 'filed' && r.mule === 'mule-sets'; });
  out.midWitness = rows.some(function(r){ return r && r.prov && r.prov.by === 'witness'; });
  return realProv(all);
};
_vaultResetRun('vaultReset');
var after = [];
try { after = JSON.parse(window.LSR.getItem('d2r_vaultRecords')).records; } catch (e2) { after = []; }
out.afterWitness = after.some(function(r){ return r && r.prov && r.prov.by === 'witness'; });
out.hold = _vrRecHold;
""", extra=extra)
        self.assertTrue(o["midFiled"], "refresh rewrote the store between the clears: %r" % o)
        self.assertTrue(o["midWitness"], "the mid snapshot was not the pre-reset witness: %r" % o)
        self.assertFalse(o["afterWitness"], "the witness survived the reset refresh: %r" % o)
        self.assertEqual(o["hold"], 0, o)

    def test_a_light_reset_with_empty_assignments_clears_the_witness(self):
        """Assignments are already empty, so kind and loc do not move. The stored witness must still clear."""
        scope = _slice(self.src,
                       "  var _VAULT_RESET_SCOPE = Object.freeze({",
                       "    try { console.info('[vault reset] ' + JSON.stringify(R)); } catch(e){}\n    return R;\n  }")
        extra = (
            "var JOURNAL_KEY = 'd2r_journal';\n"
            "var SEEN_KEY = 'd2r_seen';\n"
            "var FOLDER_DB = 'folderdb';\n"
            "var FOLDER_KEY = 'folderkey';\n"
            "var PROV_KEY = 'd2r_vaultProv';\n"
            "function _vaultRefileFromPlan(){ return; }\n"
            + _fn(self.src, "_provWrite") + "\n"
            + scope + "\n"
        )
        o = self._run(r"""
Object.keys(assign).forEach(function(k){ delete assign[k]; });
window.LSR.setItem('d2r_vaultProv', JSON.stringify((function(){
  var o = {}; o[NATALYA] = { by: 'witness', kind: 'filed' }; return o;
})()));
_vaultRecordsArm();
var before = JSON.parse(window.LSR.getItem('d2r_vaultRecords')).records;
out.beforeWitness = before.some(function(r){ return r && r.prov && r.prov.by === 'witness'; });
out.beforeFiled = before.some(function(r){ return r && r.kind === 'filed'; });
var realProv = _provWrite;
_provWrite = function(all){
  var rows = [];
  try { rows = JSON.parse(window.LSR.getItem('d2r_vaultRecords')).records; } catch (e) { rows = []; }
  out.midWitness = rows.some(function(r){ return r && r.prov && r.prov.by === 'witness'; });
  return realProv(all);
};
_vaultResetRun('vaultReset');
var after = [];
try { after = JSON.parse(window.LSR.getItem('d2r_vaultRecords')).records; } catch (e2) { after = []; }
out.afterWitness = after.some(function(r){ return r && r.prov && r.prov.by === 'witness'; });
out.hold = _vrRecHold;
""", extra=extra)
        self.assertTrue(o["beforeWitness"], "the arm did not store the witness: %r" % o)
        self.assertFalse(o["beforeFiled"], "an empty assignment was stored as filed: %r" % o)
        self.assertTrue(o["midWitness"], "refresh rewrote the store between the clears: %r" % o)
        self.assertFalse(o["afterWitness"], "the witness stayed after a prov-only reset: %r" % o)
        self.assertEqual(o["hold"], 0, o)

    def test_a_stamped_prov_unknown_snapshot_is_repaired_when_prov_returns(self):
        """A stamped provUnknown row is not a source. Once valid prov exists, the store must be rewritten and then consumed."""
        o = self._run(r"""
_vaultRecordsArm();
var obj = JSON.parse(window.LSR.getItem('d2r_vaultRecords'));
obj.records.forEach(function(r){ if (!r) return; r.provUnknown = true; delete r.prov; });
window.LSR.setItem('d2r_vaultRecords', JSON.stringify(obj));
var before = _vaultRecordsSource();
out.beforeUnknown = (before.records || []).some(function(r){ return r && r.provUnknown === true; });
var pv = {}; pv[NATALYA] = { by: 'repaired' };
window.LSR.setItem('d2r_vaultProv', JSON.stringify(pv));
var refreshed = _vaultRecordsRefresh();
out.skipped = !!(refreshed && refreshed.skipped);
var stored = JSON.parse(window.LSR.getItem('d2r_vaultRecords')).records;
out.stillUnknown = stored.some(function(r){ return r && r.provUnknown === true; });
out.repaired = stored.some(function(r){ return r && r.name === NATALYA && r.prov && r.prov.by === 'repaired'; });
var after = _vaultRecordsSource();
out.sourceRepaired = (after.records || []).some(function(r){ return r && r.name === NATALYA && r.prov && r.prov.by === 'repaired'; });
""")
        self.assertFalse(o["beforeUnknown"], "the source consumed a provUnknown snapshot: %r" % o)
        self.assertFalse(o["skipped"], "refresh skipped a provUnknown store: %r" % o)
        self.assertFalse(o["stillUnknown"], "the provUnknown row was left in the store: %r" % o)
        self.assertTrue(o["repaired"], "valid prov was not written onto the row: %r" % o)
        self.assertTrue(o["sourceRepaired"], "the source did not consume the repaired store: %r" % o)

    def test_the_written_row_and_the_compared_row_are_one_function(self):
        """The serialization and the persist write build the row in one function."""
        persist = _strip(_fn(self.src, "_vaultRecordsPersist"))
        derived = _strip(_fn(self.src, "_vrRecDerivedCanon"))
        rows_fn = _strip(_fn(self.src, "_vrRecRowsFrom"))
        canon = _strip(_fn(self.src, "_vrRecCanon"))
        row = _strip(_fn(self.src, "_vrRecRow"))
        self.assertEqual(persist.count("_vrRecRowsFrom("), 1, persist)
        self.assertEqual(derived.count("_vrRecRowsFrom("), 1, derived)
        self.assertEqual(rows_fn.count("_vrRecRow("), 1, rows_fn)
        self.assertEqual(canon.count("_vrRecRow("), 1, canon)
        self.assertEqual(row.count("row.provUnknown = true"), 1, row)
        self.assertEqual(row.count("row.prov ="), 1, row)
        self.assertNotIn("provUnknown", persist)
        self.assertNotIn("row.prov", persist)

    def test_distinct_attacks_clear_the_write_door_wilson_bar(self):
        """vault.apply bar. One RED_PROOF is one attack. Sabotage does not open the door."""
        from confidence import confluence, wilson_lower
        import self_arming as SA
        bar = SA.LOCKS["vault.apply"]["bar"]
        kinds_bar = SA.LOCKS["vault.apply"]["kinds_bar"]
        n = len(RED_PROOF)
        w = wilson_lower(n, n)
        conf = confluence(["sabotage"], SA.KINDS)
        msg = ("vault-records arm: %d distinct attacks, wilson %.4f vs write-door bar %.3f; "
               "kinds sabotage %.2f vs %.2f" % (n, w, bar, conf, kinds_bar))
        print(msg)
        self.assertGreaterEqual(n, 10, msg)
        self.assertGreaterEqual(w, bar, msg)
        self.assertLess(conf, kinds_bar,
                        "one sabotage family must not read as enough to open the write door")


RED_PROOF = [
    {
        "why": "Page load must call the arm once. Removing that call leaves d2r_vaultRecords unwired.",
        "file": "bible.html",
        "find": "          try { if (typeof window._vaultRecordsMayArm === 'function' && window._vaultRecordsMayArm(_spr)) window._vaultRecordsArm(); } catch (eArm) {}   /* #76 INC-3 v3765 — the one page-load call, only when reconcile did not refuse */",
        "replace": "          /* page-load call removed */",
        "matches": 1,
    },
    {
        "why": "A second page-load call is another door. The arm count leaves two.",
        "file": "bible.html",
        "find": "          try { if (typeof window._vaultRecordsMayArm === 'function' && window._vaultRecordsMayArm(_spr)) window._vaultRecordsArm(); } catch (eArm) {}   /* #76 INC-3 v3765 — the one page-load call, only when reconcile did not refuse */",
        "replace": "          try { if (typeof window._vaultRecordsMayArm === 'function' && window._vaultRecordsMayArm(_spr)) window._vaultRecordsArm(); } catch (eArm) {}\n          try { if (typeof window._vaultRecordsMayArm === 'function' && window._vaultRecordsMayArm(_spr)) window._vaultRecordsArm(); } catch (eArm) {}",
        "matches": 1,
    },
    {
        "why": "A presence set piece is one record. Returning the raw count puts Natalya x4, Tal x4 and Soul Cage x3 back.",
        "file": "bible.html",
        "find": "      if (!(typeof multiKeep !== 'undefined' && multiKeep && _mkWant(name) > 1)) return 1;",
        "replace": "      if (!(typeof multiKeep !== 'undefined' && multiKeep && _mkWant(name) > 1)) return have;",
        "matches": 1,
    },
    {
        "why": "The record model has to use the presence span. Without it the store keeps copyCount records.",
        "file": "bible.html",
        "find": "        if (typeof _vaultPresenceSpan === 'function') { var _psRec = _vaultPresenceSpan(name, cc); if (_psRec != null) cc = _psRec; }",
        "replace": "        /* presence span removed from the record model */",
        "matches": 1,
    },
    {
        "why": "The shelf card draws one tile for a presence set piece. Without the span a x4 name draws the capped copies.",
        "file": "bible.html",
        "find": "    if (typeof _vaultPresenceSpan === 'function') { var _psShelf = _vaultPresenceSpan(n, c); if (_psShelf != null) c = _psShelf; }",
        "replace": "    /* presence span removed from the shelf */",
        "matches": 1,
    },
    {
        "why": "The locker packs one copy of a presence set piece. Without the span it packs the capped copy count.",
        "file": "bible.html",
        "find": "      if (typeof _vaultPresenceSpan === 'function') { var _psMule = _vaultPresenceSpan(n, cc); if (_psMule != null) cc = Math.max(1, _psMule); /* v3767 every copy */ }",
        "replace": "      /* presence span removed from the locker pack */",
        "matches": 1,
    },
    {
        "why": "The Items box prints the one-record census. Putting the physical copy total back makes the card come out lower.",
        "file": "bible.html",
        "find": "if (typeof _li76 === 'number') _namesN = _li76;",
        "replace": "if (typeof _li76 === 'number') _namesN = _physN;",
        "matches": 1,
    },
    {
        "why": "The shelf card prints the same census. A null census leaves the sentinel, so the card and the Items box diverge.",
        "file": "bible.html",
        "find": "var _ci76 = _vaultLockerItems(m.id);",
        "replace": "var _ci76 = null;",
        "matches": 1,
    },
    {
        "why": "An unreadable witness must not stamp. Skipping the marker check latches the migration over UNKNOWN.",
        "file": "bible.html",
        "find": "    if (back.records.some(function(row){ return row && row.provUnknown === true; }))",
        "replace": "    if (false && back.records.some(function(row){ return row && row.provUnknown === true; }))",
        "matches": 1,
    },
    {
        "why": "An unknown dock must not stamp. Dropping the guard persists the guess.",
        "file": "bible.html",
        "find": "if (rec.carUnknown || rec.dockUnknown) return { ok: false, wrote: false, unknown: true, why: 'carried or dock is UNKNOWN - nothing persisted' };",
        "replace": "if (false && (rec.carUnknown || rec.dockUnknown)) return { ok: false, wrote: false, unknown: true, why: 'carried or dock is UNKNOWN - nothing persisted' };",
        "matches": 1,
    },
    {
        "why": "A wrong-shape store is UNKNOWN. Returning null treats it as absent, so the arm overwrites it and stamps.",
        "file": "bible.html",
        "find": "        _vrRecUnread[_VR_STORE_KEY] = 'wrong shape';\n        return undefined;\n",
        "replace": "        return null;\n",
        "matches": 1,
    },
    {
        "why": "FIND and GRAIL-DUPES read the persisted store. Falling through to the live model drops the snapshot.",
        "file": "bible.html",
        "find": "        if (loaded && loaded.ok && Array.isArray(loaded.records)) return loaded;",
        "replace": "        return _vaultRecords();",
        "matches": 1,
    },
    {
        "why": "The arm is the migration. Cutting that call leaves the page-load seam as a no-op.",
        "file": "bible.html",
        "find": "    var r = _vaultRecordsMigrate();\n",
        "replace": "    var r = { ran: false, stamped: false, why: 'seam cut' };\n",
        "matches": 1,
    },
    {
        "why": "Undo removes the stamp before the store. Removing the store first, then throwing on the stamp, leaves the gate with nothing behind it.",
        "file": "bible.html",
        "find": "    try { window.LSR.removeItem(_VRM_KEY); }\n",
        "replace": "    try { window.LSR.removeItem(_VR_STORE_KEY); }\n",
        "matches": 1,
    },
    {
        "why": "recId stays positional. Reporting another identity would close REG-2272 item 4 without an anchor.",
        "file": "bible.html",
        "find": "    r.copyIdentity = 'positional';",
        "replace": "    r.copyIdentity = 'cell';",
        "matches": 1,
    },
    {
        "why": "An unreadable d2r_muleAssign must not persist. Dropping the guard stamps the loose guess the loader built from {}.",
        "file": "bible.html",
        "find": "if (rec.assignUnknown) return { ok: false, wrote: false, unknown: true, why: 'd2r_muleAssign would not read - nothing persisted' };",
        "replace": "if (false && rec.assignUnknown) return { ok: false, wrote: false, unknown: true, why: 'd2r_muleAssign would not read - nothing persisted' };",
        "matches": 1,
    },
    {
        "why": "Page load must not arm when reconcile refuses. A mayArm that always returns true calls the arm on that refusal.",
        "file": "bible.html",
        "find": "    return !!(rec && (rec.already || (rec.ran && rec.stamped !== false)));",
        "replace": "    return true;",
        "matches": 1,
    },
    {
        "why": "The page-load call has to sit behind mayArm. An unconditional arm runs when reconcile refused.",
        "file": "bible.html",
        "find": "          try { if (typeof window._vaultRecordsMayArm === 'function' && window._vaultRecordsMayArm(_spr)) window._vaultRecordsArm(); } catch (eArm) {}   /* #76 INC-3 v3765 — the one page-load call, only when reconcile did not refuse */",
        "replace": "          try { window._vaultRecordsArm(); } catch (eArm) {}",
        "matches": 1,
    },
    {
        "why": "An older stamp must not hide an unreadable assignment. Serving the store keeps FIND on the stale mule.",
        "file": "bible.html",
        "find": "      if (typeof _assignStoreUnknown === 'function' && _assignStoreUnknown()) return _vaultRecords();",
        "replace": "      /* unreadable assignment still served from the stamp */",
        "matches": 1,
    },
    {
        "why": "A successful owned and copies write has to refresh the store. Without it the card stays on the previous census.",
        "file": "bible.html",
        "find": "  try { if (typeof window._vaultRecordsRefresh === 'function') window._vaultRecordsRefresh(); } catch (eVr) {}",
        "replace": "  /* owned and copies write did not refresh the records store */",
        "matches": 1,
    },
    {
        "why": "A successful assign write has to refresh the store. Without it FIND stays on the mule the item left.",
        "file": "bible.html",
        "find": "if (_w && typeof _vaultRecordsRefresh === 'function') _vaultRecordsRefresh();",
        "replace": "if (false && _w) _vaultRecordsRefresh();",
        "matches": 1,
    },
    {
        "why": "persistOwned writes owned and copies. Without the refresh a delete stays on the previous census.",
        "file": "bible.html",
        "find": "    if (_ownedOk && _copiesOk) { try { if (typeof _vaultRecordsRefresh === 'function') _vaultRecordsRefresh(); } catch (eRec) {} }",
        "replace": "    /* persistOwned did not refresh the records store */",
        "matches": 1,
    },
    {
        "why": "A refused refresh has to follow the live model. Ignoring the flag leaves GRAIL-DUPES on the stale stamp.",
        "file": "bible.html",
        "find": "      if (typeof _vrRecFollowLive !== 'undefined' && _vrRecFollowLive) return _vaultRecords();",
        "replace": "      /* refused refresh still served the stamp */",
        "matches": 1,
    },
    {
        "why": "A short readback is not a confirmed store. Treating it as success feeds the card a truncated census.",
        "file": "bible.html",
        "find": "      if (back === undefined || !countOk) return refused('the persisted store did not read back');",
        "replace": "      if (false) return refused('the persisted store did not read back');",
        "matches": 1,
    },
    {
        "why": "FIND has to ask the records home. Calling where-is shows the live mule while the store still names the old one.",
        "file": "bible.html",
        "find": "      var w = (typeof _vaultFindHome === 'function') ? _vaultFindHome(n) : ((typeof window._vaultWhereIs === 'function') ? window._vaultWhereIs(n) : null);",
        "replace": "      var w = (typeof window._vaultWhereIs === 'function') ? window._vaultWhereIs(n) : null;",
        "matches": 1,
    },
    {
        "why": "The dupes card has to ask the records overflow. The live list moves when copies change and the store has not.",
        "file": "bible.html",
        "find": "      var _ovNames = (m.id === 'dupes') ? _vaultDupesNames() : [];",
        "replace": "      var _ovNames = (m.id === 'dupes') ? _vaultSharedOverflowNames() : [];",
        "matches": 1,
    },
    {
        "why": "The fullscreen dupes window has to ask the records overflow. The live list is empty while the store still holds the spare.",
        "file": "bible.html",
        "find": "    var _ovNames = _vaultDupesNames();",
        "replace": "    var _ovNames = _vaultSharedOverflowNames();",
        "matches": 1,
    },
    {
        "why": "Spare cells would put a copy in GRAIL-DUPES. A non-zero count draws trade stock the ruling retired.",
        "file": "bible.html",
        "find": "return 0; /* v3767 no spare cells */",
        "replace": "return 3; /* v3767 no spare cells */",
        "matches": 1,
    },
    {
        "why": "The dupes locker count has to ask the records overflow. The live spare list drops a copy the store still holds.",
        "file": "bible.html",
        "find": "      try { (_vaultDupesNames() || []).forEach(function(n){ if (n) names[n] = 1; }); } catch (e3) {}",
        "replace": "      try { (['Griffon\\'s Eye']).forEach(function(n){ if (n) names[n] = 1; }); } catch (e3) {}",
        "matches": 1,
    },
    {
        "why": "A shared-locker record homes on the shared locker. Returning null sends Griffon's Eye to the dock.",
        "file": "bible.html",
        "find": "      if (inLocker) return 'shared';",
        "replace": "      if (false && inLocker) return 'shared';",
        "matches": 1,
    },
    {
        "why": "A refused or short refresh has to drop the stamp and leave a dirty marker. The memory flag does not survive a reload.",
        "file": "bible.html",
        "find": "    try { window.LSR.removeItem(_VRM_KEY); } catch (eSt) {}\n    try { window.LSR.setItem(_VR_DIRTY_KEY, '1'); } catch (eD) {}",
        "replace": "    /* a reload serves the stale stamp again */",
        "matches": 1,
    },
    {
        "why": "Refresh must not create a store when no stamp exists. After undo, persist would recreate a store the source can consume.",
        "file": "bible.html",
        "find": "    if (typeof _vaultRecordsStampOk === 'function' && !_vaultRecordsStampOk()) return { ok: false, live: true, why: 'no current stamp - refresh does not create a store' };",
        "replace": "    /* refresh creates a store with no stamp */",
        "matches": 1,
    },
    {
        "why": "An unstamped store is not the source. Serving it after a reload makes a store that was never armed active.",
        "file": "bible.html",
        "find": "      if (typeof _vaultRecordsStampOk === 'function' && !_vaultRecordsStampOk()) return _vaultRecords();",
        "replace": "      /* an unstamped store is still the source */",
        "matches": 1,
    },
    {
        "why": "A provUnknown snapshot is not the source, even under a planted stamp. A reload must follow the live model.",
        "file": "bible.html",
        "find": "        if (loaded && loaded.ok && Array.isArray(loaded.records) && loaded.records.some(function(row){ return row && row.provUnknown === true; })) return _vaultRecords();",
        "replace": "        /* a provUnknown snapshot is still the source */",
        "matches": 1,
    },
    {
        "why": "Refresh has to wait until a reset finishes clearing. Running it after assign and before provenance keeps the old witness.",
        "file": "bible.html",
        "find": "    if (typeof _vrRecHold !== 'undefined') _vrRecHold++;",
        "replace": "    /* refresh runs between the reset clears */",
        "matches": 1,
    },
    {
        "why": "The reset refreshes once after the clears. Without that call the old witness rows stay in d2r_vaultRecords.",
        "file": "bible.html",
        "find": "    try { if (typeof _vaultRecordsRefresh === 'function') _vaultRecordsRefresh(); } catch (eVrReset) {}",
        "replace": "    /* the reset never refreshed the records store */",
        "matches": 1,
    },
    {
        "why": "An unchanged persist must not rewrite the records store. Skipping the same-record check writes it from every slider tick.",
        "file": "bible.html",
        "find": "      if (_sameRec) return { ok: true, wrote: false, skipped: true, count: outRecs.length, seq: seq, why: null };",
        "replace": "      if (false && _sameRec) return { ok: true, wrote: false, skipped: true, count: outRecs.length, seq: seq, why: null };",
        "matches": 1,
    },
    {
        "why": "The refresh gate compares the derived rows with the stored rows. An always-equal comparison skips vaultThrowFind and leaves the orphan record.",
        "file": "bible.html",
        "find": "      return derived === stored;",
        "replace": "      return true;",
        "matches": 1,
    },
    {
        "why": "Kind and loc are part of that comparison. Nulling both makes an orphan and a loose row look the same, so the header counts stay stale.",
        "file": "bible.html",
        "find": "      kind: spec.kind,\n      mule: (spec.mule == null ? null : spec.mule),\n      loc: (spec.loc == null ? null : spec.loc)",
        "replace": "      kind: null,\n      mule: (spec.mule == null ? null : spec.mule),\n      loc: null",
        "matches": 1,
    },
    {
        "why": "Prov and provUnknown are part of the row. Dropping them leaves a witness in place on an empty-assignment reset, and leaves a provUnknown snapshot unrepaired.",
        "file": "bible.html",
        "find": "    if (spec.provUnknown) row.provUnknown = true;\n    else row.prov = (spec.prov != null ? spec.prov : null);",
        "replace": "    row.prov = null;",
        "matches": 1,
    },
    {
        "why": "The written row and the compared row are one function. A second writer in persist can store a field the comparison never sees.",
        "file": "bible.html",
        "find": "    var built = _vrRecRowsFrom(rec, prior, witness); /* persist writes the row the comparison serializes */",
        "replace": "    var built = { rows: rec.records.slice(), seq: 0 }; /* a second row writer */",
        "matches": 1,
    },
    {
        "why": "A dirty marker bypasses already and forces a re-persist. Leaving the stamp on the already path keeps the truncated store.",
        "file": "bible.html",
        "find": "      if (typeof _vrRecDirty === 'function' && _vrRecDirty()) held = null; /* a dirty marker is not already */",
        "replace": "      /* a dirty marker still takes the already path */",
        "matches": 1,
    },
    {
        "why": "The dirty marker clears only when the removal reads back gone. Treating a thrown remove as success drops the flag while the marker remains.",
        "file": "bible.html",
        "find": "    try { gone = (window.LSR.getItem(_VR_DIRTY_KEY) == null); } catch (eR) { gone = false; }",
        "replace": "    gone = true;",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
