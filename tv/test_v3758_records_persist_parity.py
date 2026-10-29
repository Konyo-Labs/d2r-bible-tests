# -*- coding: utf-8 -*-
"""#76 INC-3b (v-foundation, DORMANT) — THE PERSISTED d2r_vaultRecords STORE IS AT PARITY WITH THE IN-MEMORY MODEL.

The design doc PHASE-2 foundation. INC-1/INC-2 derive the one-record model on demand from the already-forked
name-homed stores (owned/copies/assign). This law proves that _vaultRecordsPersist() writes a d2r_vaultRecords store
whose records, re-derived into the header / find / overflow views, EQUAL the live in-memory _vaultRecords()-derived
views — so PHASE 2 (gated, his confirm) can flip the live views to read the store with NO behaviour change.

It extracts the SHIPPED functions out of bible.html and runs them in node on a seeded fixture, with an in-memory
fake window.LSR (NEVER his real disk):

  · the migration writes BOTH keys (store + stamp), is version-gated (a 2nd run is `already`), and is UNKNOWN-safe
    (an unreadable stamp persists NOTHING);
  · persisted header / find / overflow EQUAL the in-memory _vaultRecordsHeader / _vaultRecordsFind /
    _vaultRecordsOverflow AND the live _vaultSharedOverflowNames — including the SHARED-NAME-AT-CAP boundary (F has
    exactly _SHARED_COPY_CAP copies, so a `>= cap` bug would wrongly flag it as overflow);
  · each persisted record carries a STABLE OPAQUE recId (rec_<n>, not name+'#'+i) that SURVIVES a rename;
  · each record carries its OWN per-copy loc (Elad 2026-10-18 13:18 IDT: every shared copy -> 'shared');
  · a CORRUPT/unreadable d2r_vaultRecords is NEVER overwritten (the _muleUnread/_guardedSet guard);
  · the undo clears d2r_vaultRecords + the stamp and leaves owned/copies/assign UNTOUCHED;
  · the arm is the one source caller of the migrate function, and page load calls that arm once.

NOT vacuous: the persisted views are derived from the stored records, so a parity miss means the PERSIST drifted
from the model it snapshots — exactly what must hold before phase 2 swaps the source. A missing node raises — this
law does not skip. RED_PROOF below. [[the-unjoined-end]] [[unknown-stays-unknown]] [[heart-first]] [[regression-guard]]
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

# the shipped functions under test + the live overflow chain they are proven against
EXTRACT = [
    "_sharedNames", "_sharedCopyCount", "_sharedCappedCopies", "_vaultSharedOverflowCells",
    "_vaultSharedOverflowNames", "_vaultSameMuleCopies", "_vaultRecords", "_vaultRecordsSource", "_vrSourceChoice", "_vaultRecordsFind", "_vaultRecordsOverflow",
    "_vaultRecordsHeader",
    # INC-3b: persist / load / migrate / undo / rename + the model-in parity views
    "_vrRecWitness", "_vrRecRow", "_vrRecRowsFrom",
    "_vrRecLoadRaw", "_vrRecGuardedSet", "_vrLocForCopy", "_vaultRecordsLoad", "_vaultRecordsPersist",
    "_dockNames", "_vaultRecordsMigrate", "_vaultRecordsMigrateUndo", "_vaultRecordsArm", "_vaultRecordsRename",
    "_vrRecHome", "_vaultRecordsViewFind", "_vaultRecordsViewOverflow", "_vaultRecordsViewHeader",
]

# ── the fixture: A filed to mule1; B shared(1); C shared(4 -> overflow 2); E shared(3 -> overflow 1);
#    F shared(2 == cap, the BOUNDARY -> NO overflow, so a `>= cap` bug would wrongly fill dupes); D loose ──
PREAMBLE = r"""
var window = globalThis;
window.D2R_PROFILE = 'main';
// keep stdout clean for the result JSON — the shipped code's console.info/.log/.warn go to stderr here
console.info = function(){ try { process.stderr.write('[info] ' + Array.prototype.join.call(arguments, ' ') + '\n'); } catch(e){} };
console.log  = console.info;
console.warn = function(){ try { process.stderr.write('[warn] ' + Array.prototype.join.call(arguments, ' ') + '\n'); } catch(e){} };
// ── in-memory fake localStorage (NEVER his real disk) ──
var _LSRDATA = {};
window.LSR = {
  getItem: function(k){ return Object.prototype.hasOwnProperty.call(_LSRDATA, k) ? _LSRDATA[k] : null; },
  setItem: function(k, v){ _LSRDATA[k] = String(v); },
  removeItem: function(k){ delete _LSRDATA[k]; }
};
// ── the INC-3b module-level vars that _fn does not extract (they are `var`, not `function`) ──
var _VR_STORE_KEY = 'd2r_vaultRecords';
var _VRM_KEY = 'd2r_vaultRecordsMigrate';
var _VRM_VER = 1;
var _vrRecUnread = {};
// ── fixture stores + deps (kept consistent with the fixture) ──
var assign = { A:'mule1', B:'shared', C:'shared', E:'shared', F:'shared' };   // D unassigned -> loose
var copies = { C:4, E:3, F:2 };                                    // A,B default 1
var OWNED  = ['A','B','C','D','E','F'];
var _SHARED_COPY_CAP = 2, _MULE_COPY_CAP = 3;
function ownedPool(){ return OWNED.slice(); }
function copyCount(n){ var c = copies[n]; return (c && c > 0) ? c : (OWNED.indexOf(n) >= 0 ? 1 : 0); }
function isSharedStash(n){ return assign[n] === 'shared'; }         // fixture: shared-assigned == shared-stash
function muleById(id){ return (id === 'mule1') ? { id:'mule1', name:'Mule One' } : null; }
function _inMagicRare(n){ return false; }                          // the shipped dock calls this; a throw is UNKNOWN
window._carriedNames = function(){ return []; };                   // nothing carried
var KEEP_IN_INVENTORY = /Annihilus|Hellfire Torch|Gheed/;
function _keepName(n){ return n; }
"""


def _fn(src, name):
    """Extract `function NAME(...){ ...balanced... }` by brace-balancing from the first match."""
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


class TestV3758RecordsPersistParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not NODE:
            raise AssertionError("node is not on this machine — this law does not skip")
        with open(BIBLE, encoding="utf-8") as f:
            cls.src = f.read()
        cls.fns = "\n".join(_fn(cls.src, n) for n in EXTRACT)

    def _run(self, scenario):
        prog = PREAMBLE + self.fns + "\nvar out = {};\n" + scenario + "\nprocess.stdout.write(JSON.stringify(out));\n"
        p = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 0, (p.stderr or p.stdout)[-2000:])
        return json.loads(p.stdout)

    # ───────────────────────────────────────────────────────────────────────────────────────────
    def test_a_loose_split_is_persisted_and_an_older_store_reads_it_unknown(self):
        """#208 (REG-2677's sibling, found by v3815's CI): the loose split (in the dock / routed to THROW OUT) is decided when
        the records are built and SAVED on each loose row, so the persisted header counts what was known. A store saved
        before the split has no word for it and reads UNKNOWN - never 0 in the dock."""
        o = self._run(r"""
_vaultRecordsMigrate();
var raw = JSON.parse(window.LSR.getItem('d2r_vaultRecords'));
out.saved = raw.records.filter(function(r){ return r.kind === 'loose'; }).map(function(r){ return r.looseWhere || null; });
out.other = raw.records.filter(function(r){ return r.kind !== 'loose' && Object.prototype.hasOwnProperty.call(r, 'looseWhere'); }).length;
out.fresh = _vaultRecordsViewHeader(_vaultRecordsLoad());
raw.records.forEach(function(r){ delete r.looseWhere; });
window.LSR.setItem('d2r_vaultRecords', JSON.stringify(raw));
out.old = _vaultRecordsViewHeader(_vaultRecordsLoad());
""")
        self.assertEqual(o["saved"], ["dock"], "a loose row was saved without where it sat: %r" % o["saved"])
        self.assertEqual(o["other"], 0, "a row that is not loose grew a looseWhere field")
        self.assertEqual((o["fresh"]["looseDock"], o["fresh"]["looseThrow"]), (1, 0), o["fresh"])
        self.assertIsNone(o["old"]["looseDock"], "a store from before the split read %r in the dock, not UNKNOWN" % o["old"])
        self.assertIsNone(o["old"]["looseThrow"])

    def test_persisted_views_equal_the_in_memory_model_at_parity(self):
        o = self._run(r"""
var mem = _vaultRecords();
var m = _vaultRecordsMigrate();
var m2 = _vaultRecordsMigrate();          // version gate: a 2nd run is `already`, nothing re-persisted
var loaded = _vaultRecordsLoad();
var names = ['A','B','C','D','E','F','ZZ'];
out.migrate = m;
out.migrate2already = !!(m2 && m2.already && m2.ran === false);
out.storeWritten = (window.LSR.getItem('d2r_vaultRecords') != null);
out.stampWritten = (window.LSR.getItem('d2r_vaultRecordsMigrate') != null);
out.loadedIdxLen = (function(){ var q={}; ['A','B','C','D','E','F'].forEach(function(n){ q[n]=(loaded.index[n]||[]).length; }); return q; })();
// view helpers pinned to the SHIPPED in-memory functions (so the helpers cannot drift)
out.memViewHeader = _vaultRecordsViewHeader(mem);
out.shippedHeader = _vaultRecordsHeader();
out.memViewOverflow = _vaultRecordsViewOverflow(mem);
out.shippedOverflow = _vaultRecordsOverflow();
out.liveOverflow = _vaultSharedOverflowNames();
out.memFind = {}; out.shippedFind = {};
names.forEach(function(n){ out.memFind[n] = _vaultRecordsViewFind(mem, n); out.shippedFind[n] = _vaultRecordsFind(n); });
// PERSISTED parity: the SAME views derived from the LOADED store
out.loadedViewHeader = _vaultRecordsViewHeader(loaded);
out.loadedViewOverflow = _vaultRecordsViewOverflow(loaded);
out.loadedFind = {};
names.forEach(function(n){ out.loadedFind[n] = _vaultRecordsViewFind(loaded, n); });
""")
        # the migration wrote both keys, derived a faithful model, and is version-gated
        self.assertTrue(o["migrate"]["ran"], "the migration did not run: %r" % o["migrate"])
        self.assertTrue(o["migrate"]["stamped"], "the migration did not stamp: %r" % o["migrate"])
        self.assertTrue(o["storeWritten"], "d2r_vaultRecords was not written")
        self.assertTrue(o["stampWritten"], "the migrate stamp was not written")
        self.assertTrue(o["migrate2already"], "a 2nd migrate was not version-gated to `already`: %r" % o)
        # FIDELITY: the persisted index carries copyCount(name) records per name
        self.assertEqual(o["loadedIdxLen"], {"A": 1, "B": 1, "C": 4, "D": 1, "E": 3, "F": 2},
                         "persisted index miscounts copies: %r" % o["loadedIdxLen"])
        # the view helpers equal the SHIPPED functions on the in-memory model (no drift)
        self.assertEqual(o["memViewHeader"], o["shippedHeader"], "view header drifted from _vaultRecordsHeader")
        self.assertEqual(o["memViewOverflow"], o["shippedOverflow"], "view overflow drifted from _vaultRecordsOverflow")
        self.assertEqual(o["memFind"], o["shippedFind"], "view find drifted from _vaultRecordsFind")
        # PERSISTED == IN-MEMORY: header, find, overflow
        self.assertEqual(o["loadedViewHeader"], o["shippedHeader"],
                         "persisted header != in-memory header: %r vs %r" % (o["loadedViewHeader"], o["shippedHeader"]))
        self.assertEqual(o["loadedFind"], o["shippedFind"],
                         "persisted find != in-memory find: %r vs %r" % (o["loadedFind"], o["shippedFind"]))
        self.assertEqual(o["loadedViewOverflow"], o["shippedOverflow"],
                         "persisted overflow != in-memory overflow: %r vs %r" % (o["loadedViewOverflow"], o["shippedOverflow"]))
        # the BOUNDARY: F has exactly _SHARED_COPY_CAP copies -> NOT overflow; C, E are
        self.assertEqual(o["loadedViewOverflow"], [],
                         "overflow listed trade stock: %r" % o["loadedViewOverflow"])
        self.assertEqual(o["loadedViewOverflow"], o["liveOverflow"],
                         "persisted overflow != live _vaultSharedOverflowNames: %r vs %r" % (o["loadedViewOverflow"], o["liveOverflow"]))
        # a filed name resolves to its mule via the persisted store; non-filed / unknown invent no home
        self.assertEqual(o["loadedFind"]["A"], "mule1", "a filed name did not resolve to its mule via the store")
        self.assertEqual(o["loadedFind"]["B"], "shared", "a shared-locker name did not home on the shared locker")
        self.assertIsNone(o["loadedFind"]["D"], "a LOOSE name was given a mule home")
        self.assertIsNone(o["loadedFind"]["ZZ"], "an unknown name was given a home")

    def test_recId_is_opaque_and_survives_a_rename(self):
        o = self._run(r"""
_vaultRecordsMigrate();
var loaded = _vaultRecordsLoad();
out.allIds = loaded.records.map(function(r){ return r.recId; });
out.idShapeOk = loaded.records.every(function(r){ return /^rec_\d+$/.test(r.recId); });
out.idNotNameDerived = loaded.records.every(function(r){ return r.recId !== (r.name + '#' + r.copyIx); });
// per-copy loc: C -> [shared, shared, shared, shared]; F -> [shared, shared]
out.locByName = (function(){ var q={}; loaded.records.forEach(function(r){ (q[r.name]=q[r.name]||[]).push(r.loc); }); return q; })();
// rename A -> A2: the record's name field changes, the recId does NOT
out.aIdsBefore = (loaded.index['A'] || []).slice();
out.rename = _vaultRecordsRename('A', 'A2');
var loaded2 = _vaultRecordsLoad();
out.a2IdsAfter = (loaded2.index['A2'] || []).slice();
out.aGoneAfter = (loaded2.index['A'] || []).length;
out.a2IdNotNameDerived = (out.a2IdsAfter.length === 1 && out.a2IdsAfter[0] !== 'A2#0');
""")
        self.assertTrue(o["idShapeOk"], "a recId is not an opaque rec_<n> token: %r" % o["allIds"])
        self.assertTrue(o["idNotNameDerived"], "a recId is name+'#'+i derived: %r" % o["allIds"])
        # rule E per-copy location is persisted (phase-2 routing data), boundary respected
        self.assertEqual(o["locByName"]["C"], ["shared", "shared", "shared", "shared"],
                         "a shared copy left the mule: %r" % o["locByName"].get("C"))
        self.assertEqual(o["locByName"]["F"], ["shared", "shared"],
                         "F must be two shared copies: %r" % o["locByName"].get("F"))
        self.assertEqual(o["locByName"]["A"], ["mule1"], "a filed copy's loc must be its mule: %r" % o["locByName"].get("A"))
        self.assertEqual(o["locByName"]["D"], ["loose"], "a loose copy's loc must be loose: %r" % o["locByName"].get("D"))
        # the id SURVIVED the rename, unchanged, and is not the new name's positional id
        self.assertEqual(o["rename"]["moved"], 1, "the rename moved the wrong number of records: %r" % o["rename"])
        self.assertEqual(o["aIdsBefore"], o["a2IdsAfter"],
                         "the recId changed across a rename (it must be opaque): %r -> %r" % (o["aIdsBefore"], o["a2IdsAfter"]))
        self.assertEqual(o["aGoneAfter"], 0, "the old name still indexes records after the rename")
        self.assertTrue(o["a2IdNotNameDerived"], "the renamed record's id is name-derived: %r" % o["a2IdsAfter"])

    def test_rename_then_persist_reuses_the_recId(self):
        """REG-2272 item 1. Rename alone keeps the id. The next persist used to look the id up under the
        renamed spelling, miss the live name, re-mint, and overwrite the store."""
        o = self._run(r"""
_vaultRecordsMigrate();
var before = (_vaultRecordsLoad().index['A'] || []).slice();
out.rename = _vaultRecordsRename('A', 'A2');
var again = _vaultRecordsPersist();
var loaded = _vaultRecordsLoad();
out.ok = !!again.ok;
out.aIds = (loaded.index['A'] || []).slice();
out.a2Ids = (loaded.index['A2'] || []).slice();
out.same = (out.aIds.length === 1 && out.aIds[0] === before[0]);
""")
        self.assertTrue(o["ok"], "the persist after a rename refused: %r" % o)
        self.assertEqual(o["rename"]["moved"], 1, o["rename"])
        self.assertEqual(o["a2Ids"], [], "the live name is still A, so the snapshot must not keep the renamed spelling: %r" % o)
        self.assertTrue(o["same"], "rename-then-persist re-minted the id: %r" % o)

    def test_a_wrong_shape_store_is_unknown_and_not_overwritten(self):
        """REG-2272 item 2. Parse-OK but not {records: array} is UNKNOWN, not absent.

        The note names three shapes, not one: [], {"v":1}, {"records":{}}. A guard that only
        sees {"v":1} can miss a sibling the same branch was written to refuse.
        """
        o = self._run(r"""
var shapes = ['[]', JSON.stringify({ v: 1 }), JSON.stringify({ records: {} })];
out.rows = shapes.map(function(raw){
  _vrRecUnread = {};
  window.LSR.removeItem('d2r_vaultRecordsMigrate');
  window.LSR.setItem('d2r_vaultRecords', raw);
  var before = window.LSR.getItem('d2r_vaultRecords');
  var pr = _vaultRecordsPersist();
  var m = _vaultRecordsMigrate();
  return {
    unknown: !!pr.unknown, ok: pr.ok,
    unchanged: (window.LSR.getItem('d2r_vaultRecords') === before),
    stamped: (window.LSR.getItem('d2r_vaultRecordsMigrate') != null),
    migrateRan: m.ran
  };
});
""")
        self.assertEqual(len(o["rows"]), 3, o)
        for row in o["rows"]:
            self.assertTrue(row["unknown"], "a wrong-shape store was not UNKNOWN: %r" % row)
            self.assertFalse(row["ok"], "persist wrote over a wrong-shape store: %r" % row)
            self.assertTrue(row["unchanged"], "the wrong-shape bytes were overwritten: %r" % row)
            self.assertFalse(row["stamped"], "the migrate stamp latched over a wrong-shape store: %r" % row)
            self.assertFalse(row["migrateRan"], "the migration ran over a wrong-shape store: %r" % row)

    def test_an_unreadable_witness_store_is_not_a_null_witness(self):
        """REG-2272 item 3. Absent prov is null. Unreadable prov is a marker, not null."""
        o = self._run(r"""
window.LSR.setItem('d2r_vaultProv', '{bad');
var pr = _vaultRecordsPersist();
var loaded = _vaultRecordsLoad();
out.ok = !!pr.ok;
out.marked = loaded.records.every(function(r){ return r.provUnknown === true && !('prov' in r); });
out.n = loaded.records.length;
""")
        self.assertTrue(o["ok"], "persist refused a readable records store: %r" % o)
        self.assertGreater(o["n"], 0)
        self.assertTrue(o["marked"], "an unreadable witness store was stored as a null witness: %r" % o)

    def test_an_undo_that_throws_does_not_say_it_rearmed(self):
        """REG-2272 item 5. undone:true while removeItem threw left the stamp gating."""
        o = self._run(r"""
_vaultRecordsMigrate();
window.LSR.removeItem = function(){ throw new Error('disk'); };
var undo = _vaultRecordsMigrateUndo();
out.undone = undo.undone;
out.why = undo.why || '';
out.storeStill = (window.LSR.getItem('d2r_vaultRecords') != null);
out.stampStill = (window.LSR.getItem('d2r_vaultRecordsMigrate') != null);
""")
        self.assertFalse(o["undone"], "undo reported re-armed after a throw: %r" % o)
        self.assertIn("threw", o["why"], o["why"])
        self.assertTrue(o["storeStill"], "a thrown remove still cleared the store")
        self.assertTrue(o["stampStill"], "a thrown remove still cleared the stamp")

    def test_a_throwing_dock_dependency_persists_nothing(self):
        """A dock dependency that throws is UNKNOWN. null from _dockNames is not an empty loose list.

        The old catch returned [], so loose D was classified orphan and the migration stamped."""
        o = self._run(r"""
_inMagicRare = function(){ throw new Error('dock dependency'); };
var rec = _vaultRecords();
var hdr = _vaultRecordsHeader();
var pr = _vaultRecordsPersist();
var m = _vaultRecordsMigrate();
out.dockUnknown = !!(rec && rec.dockUnknown);
out.loose = hdr && hdr.loose;
out.orphans = hdr && hdr.orphans;
out.unknown = !!pr.unknown;
out.ok = !!pr.ok;
out.ran = !!m.ran;
out.stamped = !!m.stamped;
out.store = (window.LSR.getItem('d2r_vaultRecords') != null);
out.stamp = (window.LSR.getItem('d2r_vaultRecordsMigrate') != null);
out.dOrphan = (rec.records || []).filter(function(r){ return r && r.name === 'D' && r.kind === 'orphan'; }).length;
""")
        self.assertTrue(o["dockUnknown"], "a throwing dock was a measured empty list: %r" % o)
        self.assertIsNone(o["loose"], o)
        self.assertIsNone(o["orphans"], o)
        self.assertTrue(o["unknown"], o)
        self.assertFalse(o["ok"], o)
        self.assertFalse(o["ran"], o)
        self.assertFalse(o["stamped"], "a throwing dock still stamped: %r" % o)
        self.assertFalse(o["store"], o)
        self.assertFalse(o["stamp"], o)

    def test_a_stamp_remove_that_throws_leaves_the_store(self):
        """Only the stamp removal throws. The store must still be there, and undone is false.

        Removing the store first left the stamp gating an empty world, and the next arm said already."""
        o = self._run(r"""
_vaultRecordsArm();
var realGet = window.LSR.getItem.bind(window.LSR);
var realRemove = window.LSR.removeItem.bind(window.LSR);
window.LSR.removeItem = function(k){
  if (k === 'd2r_vaultRecordsMigrate') throw new Error('stamp');
  return realRemove(k);
};
var undo = _vaultRecordsMigrateUndo();
out.undone = !!undo.undone;
out.partial = !!undo.partial;
out.why = undo.why || '';
out.storeStill = (realGet('d2r_vaultRecords') != null);
out.stampStill = (realGet('d2r_vaultRecordsMigrate') != null);
""")
        self.assertFalse(o["undone"], "undo reported re-armed while the stamp remove threw: %r" % o)
        self.assertFalse(o["partial"], "a stamp remove that threw was reported as a partial clear: %r" % o)
        self.assertIn("threw", o["why"], o["why"])
        self.assertTrue(o["storeStill"], "the store was removed before the stamp remove threw: %r" % o)
        self.assertTrue(o["stampStill"], "the stamp was cleared by a remove that threw: %r" % o)

    def test_a_stamp_without_a_store_persists_again(self):
        """A stamp with no store is not already-done. The arm writes the store again."""
        o = self._run(r"""
var first = _vaultRecordsArm();
window.LSR.removeItem('d2r_vaultRecords');
var again = _vaultRecordsArm();
out.first = !!(first && first.stamped);
out.already = !!(again && again.already);
out.ran = !!(again && again.ran && again.stamped);
out.store = (window.LSR.getItem('d2r_vaultRecords') != null);
""")
        self.assertTrue(o["first"], o)
        self.assertFalse(o["already"], "a missing store was treated as already migrated: %r" % o)
        self.assertTrue(o["ran"], o)
        self.assertTrue(o["store"], o)

    def test_a_corrupt_store_is_never_overwritten(self):
        o = self._run(r"""
window.LSR.setItem('d2r_vaultRecords', '{this is : not valid json');   // corrupt bytes
var before = window.LSR.getItem('d2r_vaultRecords');
var pr = _vaultRecordsPersist();                 // marks the key UNREAD, refuses to write
var guardedSetRefused = (_vrRecGuardedSet({ v:1, records:[] }) === false);
var m = _vaultRecordsMigrate();                  // the migration refuses on the same UNKNOWN store
out.persistOk = pr.ok;
out.persistUnknown = !!pr.unknown;
out.guardedSetRefused = guardedSetRefused;
out.migrateRan = m.ran;
out.storeUnchanged = (window.LSR.getItem('d2r_vaultRecords') === before);
out.stampWritten = (window.LSR.getItem('d2r_vaultRecordsMigrate') != null);
""")
        self.assertFalse(o["persistOk"], "persist claimed success over a corrupt store")
        self.assertTrue(o["persistUnknown"], "a corrupt store was not reported UNKNOWN")
        self.assertTrue(o["guardedSetRefused"], "_vrRecGuardedSet overwrote a corrupt store")
        self.assertTrue(o["storeUnchanged"], "the corrupt d2r_vaultRecords bytes were overwritten — DATA LOSS")
        self.assertFalse(o["migrateRan"], "the migration ran over a corrupt store")
        self.assertFalse(o["stampWritten"], "the migration stamped over a corrupt store")

    def test_an_unreadable_stamp_persists_nothing(self):
        o = self._run(r"""
window.LSR.setItem('d2r_vaultRecordsMigrate', '{bad stamp');   // the stamp will not parse -> UNKNOWN
var m = _vaultRecordsMigrate();
out.ran = m.ran;
out.why = m.why || '';
out.storeWritten = (window.LSR.getItem('d2r_vaultRecords') != null);
""")
        self.assertFalse(o["ran"], "the migration acted on an unreadable stamp")
        self.assertIn("UNKNOWN", o["why"], "the refusal did not name UNKNOWN: %r" % o["why"])
        self.assertFalse(o["storeWritten"], "an unreadable stamp still let the store be written")

    def test_the_undo_clears_both_keys_and_leaves_the_source_stores_untouched(self):
        o = self._run(r"""
var assignBefore = JSON.stringify(assign), copiesBefore = JSON.stringify(copies), ownedBefore = OWNED.join(',');
_vaultRecordsMigrate();
// the migration must NEVER write the source stores
out.wroteOwned  = (window.LSR.getItem('d2r_owned') != null);
out.wroteCopies = (window.LSR.getItem('d2r_copies') != null);
out.wroteAssign = (window.LSR.getItem('d2r_muleAssign') != null);
var undo = _vaultRecordsMigrateUndo();
out.undo = undo;
out.storeAfter = (window.LSR.getItem('d2r_vaultRecords') != null);
out.stampAfter = (window.LSR.getItem('d2r_vaultRecordsMigrate') != null);
out.assignUnchanged = (JSON.stringify(assign) === assignBefore);
out.copiesUnchanged = (JSON.stringify(copies) === copiesBefore);
out.ownedUnchanged  = (OWNED.join(',') === ownedBefore);
// after the undo the migration RE-ARMS (a clean re-run persists again)
var again = _vaultRecordsMigrate();
out.reArmed = !!(again && again.ran && again.stamped);
""")
        self.assertFalse(o["wroteOwned"], "the migration wrote d2r_owned")
        self.assertFalse(o["wroteCopies"], "the migration wrote d2r_copies")
        self.assertFalse(o["wroteAssign"], "the migration wrote d2r_muleAssign")
        self.assertTrue(o["undo"]["clearedStore"], "the undo did not clear the store")
        self.assertTrue(o["undo"]["clearedStamp"], "the undo did not clear the stamp")
        self.assertFalse(o["storeAfter"], "d2r_vaultRecords survived the undo")
        self.assertFalse(o["stampAfter"], "the migrate stamp survived the undo")
        self.assertTrue(o["assignUnchanged"], "the undo altered assign")
        self.assertTrue(o["copiesUnchanged"], "the undo altered copies")
        self.assertTrue(o["ownedUnchanged"], "the undo altered owned")
        self.assertTrue(o["reArmed"], "the migration did not re-arm after the undo")

    def test_page_load_is_the_one_arm_call(self):
        """The arm is the one source caller of the migrate function. Page load calls the arm once.

        That is two `_vaultRecordsArm(` sites: the definition and the `_seedCleanseArm` call. A third
        is another door. Migrate stays at two (definition + the arm body). Persist stays at seven
        (definition, the migration, the write refresh, the move-list store create, the move-list
        row refresh, the register wrapper that files a live arrival, and the per-copy entry writer that
        builds a missing row before it writes one copy's entry - REG-2844). Window exports carry no '('."""
        code = re.sub(r"/\*.{0,4000}?\*/", "", self.src, flags=re.S)
        self.assertEqual(code.count("_vaultRecordsMigrate("), 2,
                         "migrate callers drifted: definition plus the arm body are the only two")
        self.assertEqual(code.count("_vaultRecordsArm("), 2,
                         "the arm call count drifted from definition plus the one page-load call")
        self.assertEqual(code.count("_vaultRecordsPersist("), 7,
                         "_vaultRecordsPersist callers drifted from the definition, the migration, the write refresh, the two move-list writers, the register wrapper, and the per-copy entry writer")

    def test_the_arm_is_the_migration_and_undo_rearms_it(self):
        """The seam v3765 calls. One arm persists and stamps. Undo drops both keys and the next arm runs."""
        o = self._run(r"""
var a = _vaultRecordsArm();
var a2 = _vaultRecordsArm();
out.ran = !!(a && a.ran && a.stamped);
out.seam = a && a.seam;
out.copyIdentity = a && a.copyIdentity;
out.already = !!(a2 && a2.already && a2.ran === false);
out.store = (window.LSR.getItem('d2r_vaultRecords') != null);
var undo = _vaultRecordsMigrateUndo();
var a3 = _vaultRecordsArm();
out.rearmed = !!(undo && undo.undone && a3 && a3.ran && a3.stamped);
out.sources = (window.LSR.getItem('d2r_owned') == null && window.LSR.getItem('d2r_copies') == null
               && window.LSR.getItem('d2r_muleAssign') == null);
""")
        self.assertTrue(o["ran"], "the arm did not run the migration: %r" % o)
        self.assertEqual(o["seam"], "page-load")
        self.assertEqual(o["copyIdentity"], "positional",
                         "the seam claimed a physical copy id: %r" % o)
        self.assertTrue(o["already"], "a second arm was not version-gated: %r" % o)
        self.assertTrue(o["store"])
        self.assertTrue(o["rearmed"], "undo did not re-arm the seam: %r" % o)
        self.assertTrue(o["sources"], "the arm wrote a source store")

    def test_an_unknown_carried_or_dock_list_persists_nothing(self):
        """carried UNKNOWN and dock UNKNOWN are one refusal: nothing is written and the stamp does not latch."""
        o = self._run(r"""
function probe(which){
  _vrRecUnread = {};
  window.LSR.removeItem('d2r_vaultRecords');
  window.LSR.removeItem('d2r_vaultRecordsMigrate');
  if (which === 'carried') window._carriedNames = function(){ return null; };
  if (which === 'dock') _dockNames = null;
  var pr = _vaultRecordsPersist();
  var m = _vaultRecordsMigrate();
  return {
    unknown: !!pr.unknown, ok: pr.ok, ran: m.ran,
    store: (window.LSR.getItem('d2r_vaultRecords') != null),
    stamp: (window.LSR.getItem('d2r_vaultRecordsMigrate') != null)
  };
}
out.carried = probe('carried');
out.dock = probe('dock');
""")
        for which in ("carried", "dock"):
            row = o[which]
            self.assertTrue(row["unknown"], which + " was not UNKNOWN: %r" % row)
            self.assertFalse(row["ok"], which)
            self.assertFalse(row["ran"], which)
            self.assertFalse(row["store"], which)
            self.assertFalse(row["stamp"], which)

    def test_a_short_readback_does_not_stamp(self):
        """The stamp waits until the store reads back at the count just written."""
        o = self._run(r"""
var realGet = window.LSR.getItem.bind(window.LSR);
var realSet = window.LSR.setItem.bind(window.LSR);
var wrote = false;
window.LSR.setItem = function(k, v){ if (k === 'd2r_vaultRecords') wrote = true; return realSet(k, v); };
window.LSR.getItem = function(k){
  var v = realGet(k);
  if (wrote && k === 'd2r_vaultRecords' && v) {
    var obj = JSON.parse(v);
    obj.records = obj.records.slice(0, 1);
    return JSON.stringify(obj);
  }
  return v;
};
var m = _vaultRecordsMigrate();
out.ran = m.ran;
out.stamped = !!m.stamped;
out.why = m.why || '';
out.stampKey = (realGet('d2r_vaultRecordsMigrate') != null);
""")
        self.assertTrue(o["ran"], o)
        self.assertFalse(o["stamped"], "a short read-back still stamped: %r" % o)
        self.assertFalse(o["stampKey"], o)
        self.assertIn("read back", o["why"])

    def test_a_stamp_write_that_throws_does_not_claim_it_stamped(self):
        o = self._run(r"""
var realSet = window.LSR.setItem.bind(window.LSR);
window.LSR.setItem = function(k, v){
  if (k === 'd2r_vaultRecordsMigrate') throw new Error('disk');
  return realSet(k, v);
};
var m = _vaultRecordsMigrate();
out.ran = m.ran;
out.stamped = !!m.stamped;
out.store = (window.LSR.getItem('d2r_vaultRecords') != null);
out.stamp = (window.LSR.getItem('d2r_vaultRecordsMigrate') != null);
""")
        self.assertTrue(o["ran"], o)
        self.assertFalse(o["stamped"], "a thrown stamp write reported stamped: %r" % o)
        self.assertTrue(o["store"], "the store was not left for a retry")
        self.assertFalse(o["stamp"], o)

    def test_distinct_attacks_clear_the_write_door_wilson_bar(self):
        """Write-door bar, scored per distinct attack (one RED_PROOF each), not per looped input.

        vault.apply is the class: this door persists a store. The kinds bar is reported and is not
        cleared by sabotage alone, so the score does not say the door is open."""
        from confidence import confluence, wilson_lower
        import self_arming as SA
        bar = SA.LOCKS["vault.apply"]["bar"]
        kinds_bar = SA.LOCKS["vault.apply"]["kinds_bar"]
        n = len(RED_PROOF)
        w = wilson_lower(n, n)
        conf = confluence(["sabotage"], SA.KINDS)
        msg = ("vault-records persist: %d distinct attacks, wilson %.4f vs write-door bar %.3f; "
               "kinds sabotage %.2f vs %.2f" % (n, w, bar, conf, kinds_bar))
        print(msg)
        self.assertGreaterEqual(n, 10, msg)
        self.assertGreaterEqual(w, bar, msg)
        self.assertLess(conf, kinds_bar, "one sabotage family must not read as enough to open the write door")


# ── RED_PROOF: each tamper matches EXACTLY ONCE and turns THIS law RED; heart2 reverts byte-identical. ──
RED_PROOF = [
    {
        "why": "Nothing is GRAIL-DUPES trade stock. Returning a name fills the dupes list and breaks parity with the live view.",
        "file": "bible.html",
        "find": "return []; /* v3767 no dupes list */",
        "replace": "return ['C']; /* v3767 no dupes list */",
        "matches": 1,
    },
    {
        "why": "#76 INC-3b - a persisted record must carry its name's assign-derived mule home, or _vaultRecordsFind "
               "re-derived from the store stops resolving a filed name to its mule (findA would go null) and the "
               "persisted FIND view drifts from the in-memory one.",
        "file": "bible.html",
        "find": "kind: r.kind, mule: r.mule,",
        "replace": "kind: r.kind, mule: null,",
        "matches": 1,
    },
    {
        "why": "#76 INC-3b - the recId must be a STABLE OPAQUE token, never name+'#'+i. A name-derived id re-mints on "
               "every rename/copy-count change (the defect recIdStability describes); the opaque-id + rename-stability "
               "assertions catch it.",
        "file": "bible.html",
        "find": "if (!recId) { seq += 1; recId = 'rec_' + seq; }",
        "replace": "if (!recId) { seq += 1; recId = r.name + '#' + r.copyIx; }",
        "matches": 1,
    },
    {
        "why": "A parse-OK store that is not {records: array} is UNKNOWN. Returning null treats it as absent, "
               "so persist overwrites it and the stamp latches.",
        "file": "bible.html",
        "find": "        _vrRecUnread[_VR_STORE_KEY] = 'wrong shape';\n        return undefined;\n",
        "replace": "        return null;\n",
        "matches": 1,
    },
    {
        "why": "An unreadable witness store is a marker, not the same null as no witness row.",
        "file": "bible.html",
        "find": "    if (spec.provUnknown) row.provUnknown = true;\n    else row.prov = (spec.prov != null ? spec.prov : null);",
        "replace": "    row.prov = null;",
        "matches": 1,
    },
    {
        "why": "A remove that throws must not report re-armed while the stamp still gates. The stamp goes first, so that throw leaves both keys.",
        "file": "bible.html",
        "find": "      return { undone: false, partial: false, clearedStore: false, clearedStamp: false,\n               why: 'a remove threw - the stamp still gates' };",
        "replace": "      return { undone: true, partial: false, clearedStore: false, clearedStamp: false,\n               why: 'a remove threw - the stamp still gates' };",
        "matches": 1,
    },
    {
        "why": "carried or dock UNKNOWN must not persist a guess or latch the stamp.",
        "file": "bible.html",
        "find": "if (rec.carUnknown || rec.dockUnknown) return { ok: false, wrote: false, unknown: true, why: 'carried or dock is UNKNOWN - nothing persisted' };",
        "replace": "if (false && (rec.carUnknown || rec.dockUnknown)) return { ok: false, wrote: false, unknown: true, why: 'carried or dock is UNKNOWN - nothing persisted' };",
        "matches": 1,
    },
    {
        "why": "A read-back that is not the count just written must leave the migration unstamped so it can retry.",
        "file": "bible.html",
        "find": "if (back === undefined || !back || !Array.isArray(back.records) || back.records.length !== pr.count)",
        "replace": "if (back === undefined)",
        "matches": 1,
    },
    {
        "why": "A stamp write that throws must not report stamped.",
        "file": "bible.html",
        "find": "catch (eS) { return { ran: true, stamped: false, why: 'stamp write failed - left UNstamped to retry', receipt: rc }; }",
        "replace": "catch (eS) { return { ran: true, stamped: true, why: null, receipt: rc }; }",
        "matches": 1,
    },
    {
        "why": "An unreadable migrate stamp persists nothing.",
        "file": "bible.html",
        "find": "catch (e) { return { ran: false, why: 'the migrate stamp would not read - UNKNOWN, nothing persisted' }; }",
        "replace": "catch (e) { var _pr = _vaultRecordsPersist(opts); return { ran: true, stamped: true, why: null, count: _pr.count }; }",
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
        "why": "Page load is the one arm call. A second call beside the export is another door.",
        "file": "bible.html",
        "find": "  window._vaultRecordsArm = _vaultRecordsArm;\n",
        "replace": "  window._vaultRecordsArm = _vaultRecordsArm; _vaultRecordsArm();\n",
        "matches": 1,
    },
    {
        "why": "A thrown dock dependency must not become an empty loose list. Returning [] classifies loose names "
               "as orphans and the migration stamps that guess.",
        "file": "bible.html",
        "find": "    } catch (e) { return null; }   /* a thrown dock is UNKNOWN, never an empty list of loose names */\n",
        "replace": "    } catch (e) { return []; }\n",
        "matches": 1,
    },
    {
        "why": "Undo must remove the stamp before the store. Removing the store first, then throwing on the stamp, "
               "leaves the gate with nothing behind it.",
        "file": "bible.html",
        "find": "    try { window.LSR.removeItem(_VRM_KEY); }\n",
        "replace": "    try { window.LSR.removeItem(_VR_STORE_KEY); }\n",
        "matches": 1,
    },
    {
        "why": "A stamp with no store must not report already. The arm has to persist again.",
        "file": "bible.html",
        "find": "      if (held && Array.isArray(held.records)) return { ran: false, already: true, receipt: done };\n",
        "replace": "      return { ran: false, already: true, receipt: done };\n",
        "matches": 1,
    },
    {"why": "#208 - a saved loose row forgets where it sat",
     "file": "bible.html",
     "find": "      row.looseWhere = spec.looseWhere;\n",
     "replace": "      void 0;\n",
     "matches": 1, "needs": "node"},
    {"why": "#208 - the persisted header loses the loose split",
     "file": "bible.html",
     "find": "      looseDock:  (unk || typeof model.looseDockN !== 'number') ? null : model.looseDockN,\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "#208 - a store from before the split reads 0 in the dock instead of UNKNOWN",
     "file": "bible.html",
     "find": "    if (_lwOld) { model.looseDockN = null; model.looseThrowN = null; }\n",
     "replace": "",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
