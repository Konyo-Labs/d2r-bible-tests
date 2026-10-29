# -*- coding: utf-8 -*-
"""v3767 - holder, location and cell survive the real writers, and a record round-trips.

The copy-witness law injects a finished look into PROV. That never calls the retro row
builder, the receipt, or the filing door, so a dropped holder still passed. This law
drives those writers:

  vault_retro._witness_rows
  -> _receipt
  -> _receiptStashWitness
  -> _vaultWitnessCheck
  -> vaultFile's persisted looks
  -> _vaultEvidenceLooks / _vaultSightGroups

An unknown holder stays unknown. It does not merge with another holder's same cell.
Two unknowns on one cell stay one bucket.

source, sight, watching and locked are on the row _vrRecRow writes. Save, then load,
then the source that prefers the store still equals the live record, for a manual
WATCHING record and a LOCKED record. The live prov and the lane lock are cleared
before the read, so a stripped store cannot be repaired by deriving them again.

RED_PROOF below. [[heart-first]] [[the-unjoined-end]] [[unknown-stays-unknown]]
"""
import json
import os
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

import vault_retro as vr  # noqa: E402
from test_every_mule_filing_carries_its_witness import HARNESS, _door  # noqa: E402
from test_v3767_copy_witness import _fn, _slice_fn  # noqa: E402

BIBLE = os.path.join(HERE, "..", "bible.html")
NODE = os.environ.get("NODE") or shutil.which("node")

EVIDENCE = [
    {"session": "sA", "frame": "fA", "lane": "stash", "conf": 0.91,
     "holder": "MuleA", "cell": "stash:c1r1"},
    {"session": "sB", "frame": "fB", "lane": "stash", "conf": 0.92,
     "holder": "MuleB", "cell": "stash:c1r1"},
    {"session": "sU", "frame": "fU", "lane": "stash", "conf": 0.93,
     "cell": "stash:c1r1"},
    {"session": "sU2", "frame": "fU2", "lane": "stash", "conf": 0.94,
     "cell": "stash:c1r1"},
    {"session": "sL", "frame": "fL", "lane": "mule", "conf": 0.95,
     "holder": "MuleA", "cell": "stash:c1r1"},
]

PLACE_FNS = [
    "_vaultCellKey", "_vaultSightGroups", "_vaultRecords",
    "_vaultRecordsSource", "_vrSourceChoice", "_vaultRecordsStampOk",
    "_vrRecWitness", "_vrRecRow", "_vrRecRowsFrom",
    "_vrRecLoadRaw", "_vrRecGuardedSet", "_vrLocForCopy",
    "_vaultRehomeCopies", "_vaultReconcileHomes",
    "_vaultRecordsLoad", "_vaultRecordsPersist",
]

STUBS = r"""
function copyCount(){ return 1; }
function _dockNames(){ return []; }
function _sharedNames(){ return []; }
window._carriedNames = function(){ return []; };
window._furnitureLocked = function(){ return false; };
window._mainLockOf = function(){ return null; };
window._vfIsSetPiece = function(){ return false; };
var multiKeep = {};
var _VR_STORE_KEY = 'd2r_vaultRecords';
var _VRM_KEY = 'd2r_vaultRecordsMigrate';
var _VRM_VER = 1;
var _VR_DIRTY_KEY = 'd2r_vaultRecordsDirty';
var _vrRecHold = 0;
var _vrRecSigSeen = null;
var _vrRecUnread = {};
"""

BODY = r"""
function placeOf(k){
  return { holder: (k && k.holder != null && k.holder !== '') ? k.holder : null,
           loc: (k && (k.loc || k.location)) || null,
           cell: (k && k.cell) || null };
}
function sig(g){
  return (g.holder == null ? '*' : g.holder) + '|' + (g.location || '') + '|' + g.cell + '|' + g.witnesses;
}
var looks = ROWS.map(function(r){
  var rec = _receipt({
    source: 'kai-register', sessionId: r.session, frame: r.frame, loc: r.lane,
    holder: Object.prototype.hasOwnProperty.call(r, 'holder') ? r.holder : null,
    cell: r.cell, conf: r.conf
  }, 1710000000000, true);
  return rec.looks[0];
});
OUT.receipt = looks.map(placeOf);
var prov = {};
prov["Griffon's Eye"] = { kind: 'owned', source: 'kai-register', looks: looks };
_provWrite(prov);
var wit = window._vaultReceiptStashWitness("Griffon's Eye", null);
OUT.witness = (wit && wit.sessions || []).map(placeOf);
var filed = window.vaultFile("Griffon's Eye", wit, { mule: 'uni-armor' });
OUT.filed = !!(filed && filed.ok);
var row = _provAll()["Griffon's Eye"] || {};
OUT.persisted = (row.looks || []).map(placeOf);
var again = window._vaultProvAsWitness(row);
OUT.refile = (again && again.sessions || []).map(placeOf);
OUT.groups = (_vaultSightGroups("Griffon's Eye") || []).map(sig).sort();
"""

ROUND = r"""
function oneLook(holder, cell, session, frame){
  return _receipt({
    source: 'kai-register', sessionId: session, frame: frame, loc: 'stash',
    holder: holder, cell: cell, conf: 0.9
  }, 1710000000000, true).looks[0];
}
var prov = {};
prov.Grief = { kind: 'owned', source: 'hand', looks: [
  oneLook('MuleA', 'stash:c1r1', 'g1', 'gf1'),
  oneLook('MuleA', 'stash:c1r1', 'g2', 'gf2')
]};
prov.Enigma = { kind: 'owned', source: 'kai-register', looks: [
  oneLook('MuleB', 'stash:c2r2', 'e1', 'ef1')
]};
_provWrite(prov);
owned.add('Grief');
owned.add('Enigma');
window._laneLockNote('Grief', 'equipment', 's1');
window._laneLockNote('Grief', 'equipment', 's2');
window._laneLockNote('Enigma', 'equipment', 's1');
window._laneLockNote('Enigma', 'equipment', 's2');
window._laneLockNote('Enigma', 'equipment', 's3');
function pack(r){
  var s = r && r.sight;
  return {
    source: r && r.source != null ? r.source : null,
    holder: s && s.holder != null ? s.holder : null,
    location: s && s.location != null ? s.location : null,
    cell: s && s.cell != null ? s.cell : null,
    witnesses: s && typeof s.witnesses === 'number' ? s.witnesses : null,
    watching: !!(r && r.watching === true),
    locked: !!(r && r.locked === true)
  };
}
function byName(model){
  var out = {};
  ((model && model.records) || []).forEach(function(r){ if (r && r.name) out[r.name] = pack(r); });
  return out;
}
OUT.live = byName(_vaultRecords());
var wrote = _vaultRecordsPersist();
OUT.wrote = !!(wrote && wrote.ok);
window.LSR.setItem('d2r_vaultRecordsMigrate', JSON.stringify({ ver: 1 }));
_provWrite({});
window.LSR.removeItem('d2r_laneLock');
OUT.loaded = byName(_vaultRecordsLoad());
OUT.back = byName(_vaultRecordsSource());
"""


def _rows():
    rows = vr._witness_rows(EVIDENCE)
    by_frame = {r["frame"]: r for r in rows}
    return rows, by_frame


class TestV3767IntakeIdentity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not NODE:
            raise AssertionError("node is not on this machine - this law does not skip")
        with open(BIBLE, encoding="utf-8") as f:
            src = f.read()
        lane = _slice_fn(src, "var _LANE_LOCK_KEY = 'd2r_laneLock';", "window._laneLockWhy = function(name){")
        receipt = "\n".join(_fn(src, n) for n in ("_iso", "_num", "_str", "_receipt"))
        place = "\n".join(_fn(src, n) for n in PLACE_FNS)
        cls.prefix = "\n".join([HARNESS, STUBS, _door(src), receipt, lane, place])

    def _run(self, body, rows=None):
        prog = self.prefix + "\nvar ROWS = %s;\nvar OUT = {};\n" % json.dumps(rows or []) + body + "\nprocess.stdout.write(JSON.stringify(OUT));\n"
        raw = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=30)
        self.assertEqual(raw.returncode, 0, (raw.stderr or "")[-2500:] + (raw.stdout or "")[-800:])
        return json.loads(raw.stdout)

    def test_holder_location_and_cell_survive_retro_receipt_and_persist(self):
        rows, by_frame = _rows()
        self.assertEqual(by_frame["fA"]["holder"], "MuleA")
        self.assertEqual(by_frame["fA"]["lane"], "stash")
        self.assertEqual(by_frame["fA"]["cell"], "stash:c1r1")
        self.assertEqual(by_frame["fB"]["holder"], "MuleB")
        self.assertNotIn("holder", by_frame["fU"], "an unknown holder was invented on the retro row")
        self.assertEqual(by_frame["fU"]["cell"], "stash:c1r1")
        self.assertEqual(by_frame["fL"]["lane"], "mule")
        o = self._run(BODY, rows)
        self.assertEqual(o["receipt"], [
            {"holder": "MuleA", "loc": "stash", "cell": "stash:c1r1"},
            {"holder": "MuleB", "loc": "stash", "cell": "stash:c1r1"},
            {"holder": "MuleA", "loc": "mule", "cell": "stash:c1r1"},
            {"holder": None, "loc": "stash", "cell": "stash:c1r1"},
            {"holder": None, "loc": "stash", "cell": "stash:c1r1"},
        ], o["receipt"])
        self.assertEqual(o["witness"], o["receipt"], "the receipt witness dropped the place: %r" % o["witness"])
        self.assertTrue(o["filed"], "vaultFile refused the witnessed looks")
        self.assertEqual(sorted(o["persisted"], key=lambda k: (k["holder"] or "", k["loc"] or "", k["cell"] or "")),
                         sorted(o["receipt"], key=lambda k: (k["holder"] or "", k["loc"] or "", k["cell"] or "")),
                         "persisted looks dropped the place: %r" % o["persisted"])
        self.assertEqual(o["refile"], o["witness"], "a re-file of the stored row dropped the place: %r" % o["refile"])
        self.assertEqual(o["groups"], [
            "*|stash|stash:c1r1|2",
            "MuleA|mule|stash:c1r1|1",
            "MuleA|stash|stash:c1r1|1",
            "MuleB|stash|stash:c1r1|1",
        ], o["groups"])

    def test_source_sight_watching_and_locked_round_trip(self):
        o = self._run(ROUND)
        self.assertTrue(o["wrote"], "persist refused: %r" % o)
        want = {
            "Grief": {"source": "manual", "holder": "MuleA", "location": "stash",
                      "cell": "stash:c1r1", "witnesses": 2, "watching": True, "locked": False},
            "Enigma": {"source": "kai-register", "holder": "MuleB", "location": "stash",
                       "cell": "stash:c2r2", "witnesses": 1, "watching": False, "locked": True},
        }
        self.assertEqual(o["live"], want, "the live record was not manual/watching or locked: %r" % o["live"])
        self.assertEqual(o["loaded"], want, "load stripped the record: %r" % o["loaded"])
        self.assertEqual(o["back"], want, "the source preferred a stripped store: %r" % o["back"])

    def test_distinct_attacks_clear_the_vault_apply_wilson_bar(self):
        from confidence import confluence, wilson_lower
        import self_arming as SA
        bar = SA.LOCKS["vault.apply"]["bar"]
        kinds_bar = SA.LOCKS["vault.apply"]["kinds_bar"]
        n = len(RED_PROOF)
        w = wilson_lower(n, n)
        conf = confluence(["sabotage"], SA.KINDS)
        msg = ("intake identity: %d distinct attacks, wilson %.4f vs vault.apply bar %.3f; "
               "kinds sabotage %.2f vs %.2f" % (n, w, bar, conf, kinds_bar))
        print(msg)
        self.assertGreaterEqual(n, 10, msg)
        self.assertGreaterEqual(w, bar, msg)
        self.assertLess(conf, kinds_bar, msg)


RED_PROOF = [
    {"why": "The retro row drops the holder, so two mules on one cell become one unknown.",
     "file": "tv/vault_retro.py",
     "find": '        for _vf in ("sockets", "eth", "quality", "promptVer", "point", "cell", "cellWhy", "holder"):   # v3767 - who holds it, and where',
     "replace": '        for _vf in ("sockets", "eth", "quality", "promptVer", "point", "cell", "cellWhy"):   # v3767 - who holds it, and where',
     "matches": 1},
    {"why": "The receipt look drops holder and cell.",
     "file": "bible.html",
     "find": "                looks: fr ? [{ id: sid, frame: fr, conf: _num(rec.conf), at: m ? _iso(ts) : null, loc: _str(rec.loc), scene: _str(rec.scene), holder: _str(rec.holder), character: _str(rec.character), cell: (rec.cell == null || rec.cell === '') ? null : rec.cell }] : [], /* v3767 receipt place */",
     "replace": "                looks: fr ? [{ id: sid, frame: fr, conf: _num(rec.conf), at: m ? _iso(ts) : null, loc: _str(rec.loc), scene: _str(rec.scene) }] : [], /* v3767 receipt place */",
     "matches": 1},
    {"why": "The witness check keeps a look with no place, so the filing door has nothing to store.",
     "file": "bible.html",
     "find": "      var _kept = { id: id, frame: String(fr), conf: c, reel: String(e.reel || e.session || '') || null };\n"
             "      if (e.holder != null && e.holder !== '') _kept.holder = e.holder;\n"
             "      else if (e.character != null && e.character !== '') _kept.character = e.character;\n"
             "      var _kloc = (e.loc != null && e.loc !== '') ? e.loc : ((e.lane != null && e.lane !== '') ? e.lane : ((e.location != null && e.location !== '') ? e.location : null));\n"
             "      if (_kloc != null) _kept.loc = _kloc;\n"
             "      if (e.cell != null && e.cell !== '') _kept.cell = e.cell;\n"
             "      /* REG-2891 - and WHEN it was seen: the look's own capture time, kept only when it reads as a time (never invented) */\n"
             "      var _kat = (typeof e.at === 'number') ? e.at : ((typeof e.at === 'string' && e.at) ? Date.parse(e.at) : NaN);\n"
             "      if (isFinite(_kat) && _kat > 0) _kept.at = new Date(_kat).toISOString();\n"
             "      keep.push(_kept); /* v3767 witness place */",
     "replace": "      keep.push({ id: id, frame: String(fr), conf: c, reel: String(e.reel || e.session || '') || null }); /* v3767 witness place */",
     "matches": 1},
    {"why": "The receipt's stash witness drops holder, location and cell before the filing door sees them.",
     "file": "bible.html",
     "find": "        .map(function(k){ lane = lane || String(k.loc).toLowerCase(); return { session: k.id, frame: k.frame, conf: k.conf, holder: k.holder || k.character || null, loc: k.loc || null, cell: k.cell || null }; }) /* v3767 receipt look */",
     "replace": "        .map(function(k){ lane = lane || String(k.loc).toLowerCase(); return { session: k.id, frame: k.frame, conf: k.conf }; }) /* v3767 receipt look */",
     "matches": 1},
    {"why": "vaultFile stores a look as id, frame and conf, so the cell identity is gone.",
     "file": "bible.html",
     "find": "      looks: (wc.looks || []).map(function(k){\n"
             "        var lk = { id: k.id, frame: k.frame, conf: k.conf };\n"
             "        if (k.holder != null && k.holder !== '') lk.holder = k.holder;\n"
             "        else if (k.character != null && k.character !== '') lk.character = k.character;\n"
             "        if (k.loc != null && k.loc !== '') lk.loc = k.loc;\n"
             "        else if (k.location != null && k.location !== '') lk.loc = k.location;\n"
             "        else if (k.lane != null && k.lane !== '') lk.loc = k.lane;\n"
             "        if (k.cell != null && k.cell !== '') lk.cell = k.cell;\n"
             "        if (k.at) lk.at = k.at;   /* REG-2891 capture time */\n"
             "        return lk;\n"
             "      }), /* v3767 persisted look */",
     "replace": "      looks: (wc.looks || []).map(function(k){ return { id: k.id, frame: k.frame, conf: k.conf }; }), /* v3767 persisted look */",
     "matches": 1},
    {"why": "Filing the stored row again builds a witness with no place.",
     "file": "bible.html",
     "find": "             sessions: (row.looks || []).map(function(k){ return { witness: k.id, frame: k.frame, conf: k.conf, holder: k.holder || k.character || null, loc: k.loc || null, cell: k.cell || null }; }), /* v3767 refile look */",
     "replace": "             sessions: (row.looks || []).map(function(k){ return { witness: k.id, frame: k.frame, conf: k.conf }; }), /* v3767 refile look */",
     "matches": 1},
    {"why": "An unknown holder shares a key with every other holder of that cell.",
     "file": "bible.html",
     "find": "      var key = holderKey + '\\u0000' + String(location || '') + '\\u0000' + cell; /* v3767 copy key */",
     "replace": "      var key = cell; /* v3767 copy key */",
     "matches": 1},
    {"why": "The persisted record row drops source, sight, watching and locked.",
     "file": "bible.html",
     "find": "      source: (spec.source == null ? null : spec.source), /* v3767 record source */\n"
             "      sight: (spec.sight && typeof spec.sight === 'object' && !Array.isArray(spec.sight)) ? spec.sight : null, /* v3767 record sight */\n"
             "      watching: spec.watching === true, /* v3767 record watching */\n"
             "      locked: spec.locked === true /* v3767 record locked */\n",
     "replace": "",
     "matches": 1},
    {"why": "Persist builds the row without source, sight, watching and locked, so the store never receives them.",
     "file": "bible.html",
     "find": "          source: (r.source == null ? null : r.source),\n"
             "          sight: (r.sight && typeof r.sight === 'object' && !Array.isArray(r.sight)) ? r.sight : null,\n"
             "          watching: r.watching === true,\n"
             "          locked: r.locked === true,\n",
     "replace": "",
     "matches": 1},
    {"why": "The source ignores the stored row and derives again, so a wiped live prov comes back empty.",
     "file": "bible.html",
     "find": "        if (loaded && loaded.ok && Array.isArray(loaded.records)) return { store: loaded, why: '' };",
     "replace": "        return _vaultRecords();",
     "matches": 1},
    {"why": "A repeat sighting of the same cell does not count as a witness, so two looks become an uncounted copy.",
     "file": "bible.html",
     "find": "      if (sid) g.sessions[String(sid)] = 1; /* v3767 session witness */",
     "replace": "      if (sid) g.sessions = {}; /* v3767 session witness */",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
