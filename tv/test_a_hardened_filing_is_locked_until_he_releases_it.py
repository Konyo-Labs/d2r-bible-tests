# -*- coding: utf-8 -*-
"""#41 heart audit, rank 17 (REG-1562) — A HARDENED FILING IS LOCKED UNTIL HE RELEASES IT.

THE DEFECT: vault_evidence.rebuild_plan has said "HARDENED is re-filed and locked" since the reset was built, and the
board's rebuild branch wrote locked:true on every such row — and no door ever read the field. A grep of bible.html for
readers found the write, the MAIN-ledger list and the picker's _mpLockRefusal (a different lock: his MAIN's gear). The
lock was a label: a drag to another locker, the cell ✕ and the vault audit's move all took a 21/21 row exactly as they
took a 2-look one.

WHAT THIS LAW HOLDS — the SHIPPED doors, cut from bible.html between their own anchors and driven in node, never
re-typed (the same cut test_every_mule_filing_carries_its_witness makes, plus vaultUnassign, assignItem, vaultRemove
and vaultRestoreLast):
  · THE PREMISE — a HARDENED plan row rebuilt through the door carries locked:true; a PROVEN one carries locked:false;
    the one reader (window._vaultHardLock) answers {tier, successes, trials, holder} for the first and null for the
    second. A law with no locked row to refuse grades nothing.
  · THE MACHINE'S MOVE (vaultFile {move} — the vault audit, a reroute) is refused 'hardened', map and row untouched.
  · HIS HAND'S MOVE (assignItem -> vaultFile with a hand witness and another locker) is refused, and the status line
    says so with the release; a re-drop on the SAME locker leaves the evidence row standing ('already', locked:true)
    instead of replacing it with a hand row.
  · A READER'S RE-LOOK at the same locker leaves the evidence row standing too — two looks never overwrite twenty-one.
  · THE CELL ✕ (vaultUnassign) is refused, said, and the filing stays.
  · THE RELEASE — Shift on the drop (opts.unlock) moves it and the new hand row says what lock it opened
    (unlockedFrom); Shift on the ✕ sends it to the dock and the receipt says it was unlocked; the reader answers null
    after either, and the doors open.
  · THE BASELINE — a PROVEN (locked:false) row moves and unassigns freely: a lock that refuses everything is an off
    switch, not a lock.
  · UNKNOWN — a witness store that will not parse makes the reader answer {unknown:true}, and every hand door refuses
    'prov-unreadable' rather than reading {} as "not locked".
    Since REG-2415 the door refuses a store that will not read before the hand block runs, so the hand block's own
    UNKNOWN check is driven with a lock read that throws after the door's read answered (P1b).
  · EVIDENCE LANES STAY FREE — vaultRemove (lane tv-unvault) takes a locked filing, and vaultRestoreLast puts the row
    back verbatim, lock included: a removal is journaled and undoable, so it needs no lock.
  · THE JOIN, in the source — the ✕ the mule cell renders and both hand paths (the drop, the click) carry the Shift
    release; a door that reads a field nobody can send is the unjoined end this audit is about.
RED_PROOF below — each applied to bible.html, run, and seen RED through tv/heart2.py --prove.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import test_every_mule_filing_carries_its_witness as FILE   # noqa: E402  (the cut, the harness, the say line)

NODE = shutil.which("node")
BIBLE = os.path.join(ROOT, "bible.html")

UNASSIGN_START = "  window.vaultUnassign = function(name, opts){"
ASSIGN_START = "  function assignItem(name, muleId, opts){"
ASSIGN_END = "  window.vaultAssign = assignItem;\n"
VR_START = "  function _vrRead(){"
VR_END = "  /* the heart and the console read the journal through here"
REMOVE_START = "  window.vaultRemove = function(names, opts){"
REMOVE_END = "  /* The reverse of exactly one batch"
RESTORE_START = "  window.vaultRestoreLast = function(){"
AUDIT_START = "  function _vaultAuditApply(f){"
AUDIT_END = "  function _vaultAuditPersist(){"


def _src():
    with io.open(BIBLE, encoding="utf-8") as f:
        return f.read()


def _once(s, needle):
    n = s.count(needle)
    assert n == 1, "%r is not a unique anchor in bible.html (%d matches)" % (needle[:60], n)
    return s.index(needle)


def _fn(s, start):
    """From a unique start line to the first `  };` that closes it (the door's own two-space indent)."""
    i = _once(s, start)
    j = s.index("\n  };\n", i) + len("\n  };\n")
    return s[i:j]


def _span(s, start, end):
    i = _once(s, start)
    j = s.index(end, i)
    return s[i:j]


EXTRA = r"""
var _VR_LOG = 'd2r_vaultRemoved', _VR_RING = 20;
var STATUS = [];
function status(m){ STATUS.push(String(m)); }
function renderVault(){}
function refreshOpenCard(){}
var selectedChip = null;
window._repaintOwned = function(){};
window._ownedAdd = function(n){ owned.add(n); persistOwned(); };
window._consumable = function(){ return false; };
var document = { querySelector: function(){ return null; }, getElementById: function(){ return null; } };
"""

BODY = r"""
var OUT = { steps: {} };
var HAND = function(){ return { by: 'hand', at: '2026-09-30T00:00:00Z', where: 'the vault manager' }; };
var L2 = [{ session: 's_a', frame: 'f_a.jpg', conf: 0.9 }, { session: 's_b', frame: 'f_b.jpg', conf: 0.85 }];
function prov(){ return JSON.parse(window.LSR.getItem('d2r_vaultProv') || '{}'); }
function row(n){ return prov()[n] || null; }
function map(){ return JSON.parse(JSON.stringify(assign)); }
function rebuild(name, tier, k, n, mule){
  return window.vaultFile(name, { lane: 'stash', sessions: L2 },
    { rebuild: true, mule: mule || 'uni-armor',
      plan: { name: name, tier: tier, why: tier, locked: tier === 'HARDENED', successes: k, trials: n, bound: 0.8,
              sessions: ['s_a', 's_b'] } });
}
function seed(){
  Object.keys(STORE).forEach(function(k){ delete STORE[k]; });
  Object.keys(assign).forEach(function(k){ delete assign[k]; });
  owned.clear(); STATUS.length = 0;
  OUT.steps.seedHard = rebuild('Arachnid Mesh', 'HARDENED', 21, 21);
  OUT.steps.seedProven = rebuild('Shako', 'PROVEN', 12, 12);
}
seed();
OUT.premise = { hard: row('Arachnid Mesh'), proven: row('Shako'), map: map(),
                lockHard: window._vaultHardLock('Arachnid Mesh'), lockProven: window._vaultHardLock('Shako'),
                lineHard: window._vaultEvidenceLine('Arachnid Mesh'), lineProven: window._vaultEvidenceLine('Shako') };

/* the machine's move */
OUT.machineMove = { r: window.vaultFile('Arachnid Mesh', null, { move: true, mule: 'uni-small', by: 'vault audit' }),
                    map: map(), row: row('Arachnid Mesh') };
/* his hand: a drag to another locker, through assignItem (the drop handler's door) */
STATUS.length = 0;
assignItem('Arachnid Mesh', 'uni-small');
OUT.handMove = { status: STATUS.slice(), map: map(), row: row('Arachnid Mesh'),
                 door: window.vaultFile('Arachnid Mesh', HAND(), { mule: 'uni-small' }) };
/* a re-drop on the same locker */
OUT.sameHome = { r: window.vaultFile('Arachnid Mesh', HAND(), { mule: 'uni-armor' }), row: row('Arachnid Mesh'), map: map() };
/* a reader's re-look at the same locker */
OUT.readerSame = { r: window.vaultFile('Arachnid Mesh', { lane: 'stash', sessions: L2 }, { mule: 'uni-armor' }),
                   row: row('Arachnid Mesh'), map: map() };
/* the cell ✕ */
STATUS.length = 0;
OUT.x = { r: window.vaultUnassign('Arachnid Mesh'), status: STATUS.slice(), map: map(), row: row('Arachnid Mesh') };

/* the baseline: PROVEN moves and unassigns freely */
OUT.baseMove = { r: window.vaultFile('Shako', null, { move: true, mule: 'uni-small', by: 'vault audit' }), map: map() };
OUT.baseX = { r: window.vaultUnassign('Shako'), map: map(), row: row('Shako') };

/* the release on the drop: Shift held -> assignItem carries unlock */
STATUS.length = 0;
assignItem('Arachnid Mesh', 'uni-small', { unlock: true });
OUT.releaseDrop = { status: STATUS.slice(), map: map(), row: row('Arachnid Mesh'), lock: window._vaultHardLock('Arachnid Mesh'),
                    line: window._vaultEvidenceLine('Arachnid Mesh'),
                    thenMove: window.vaultFile('Arachnid Mesh', null, { move: true, mule: 'shared', by: 'vault audit' }) };
/* the release on the ✕ */
OUT.steps.seedHard2 = rebuild('Stormshield', 'HARDENED', 30, 30);
OUT.releaseX = { refused: window.vaultUnassign('Stormshield'), r: window.vaultUnassign('Stormshield', { unlock: true }),
                 map: map(), row: row('Stormshield'), lock: window._vaultHardLock('Stormshield') };

/* UNKNOWN: a witness store that will not parse */
seed();
STORE['d2r_vaultProv'] = '{ not json';
STATUS.length = 0;
OUT.unknown = { lock: window._vaultHardLock('Arachnid Mesh'),
                x: window.vaultUnassign('Arachnid Mesh'),
                hand: window.vaultFile('Arachnid Mesh', HAND(), { mule: 'uni-small' }),
                same: window.vaultFile('Arachnid Mesh', HAND(), { mule: 'uni-armor' }),
                move: window.vaultFile('Arachnid Mesh', null, { move: true, mule: 'uni-small', by: 'vault audit' }),
                map: map(), status: STATUS.slice(), store: STORE['d2r_vaultProv'] };

/* evidence lanes stay free, and the undo brings the lock back */
seed();
OUT.evidence = { removed: window.vaultRemove(['Arachnid Mesh'], { lane: 'tv-unvault', quiet: true, why: 'the TV saw it thrown' }),
                 mapAfter: map(), rowAfter: row('Arachnid Mesh') };
OUT.evidence.restored = window.vaultRestoreLast();
OUT.evidence.mapBack = map(); OUT.evidence.rowBack = row('Arachnid Mesh');
OUT.evidence.lockBack = window._vaultHardLock('Arachnid Mesh');
/* ── #98 (his ruling 2026-09-30: "whatever is logical... just make it visually known") — the verifier's findings ── */
var CHRON = []; window.kaiChronicleRecord = function(x){ CHRON.push(x); };
var ELS = {};
function _el(){ var cl = {}; return { hidden: true, textContent: '', className: '', title: '', _cl: cl,
  classList: { add: function(c){ cl[c] = 1; }, remove: function(c){ delete cl[c]; } } }; }
ELS['vault-lock-chip'] = _el(); ELS['vault-lock-alert'] = _el();
document.getElementById = function(id){ return ELS[id] || null; };
document.querySelectorAll = function(){ return []; };
/* P1 — UNKNOWN + Shift: nothing filed, nothing released, the unreadable bytes untouched */
seed();
STORE['d2r_vaultProv'] = '{ not json';
OUT.p1 = { hand: window.vaultFile('Arachnid Mesh', HAND(), { mule: 'uni-small', unlock: true }),
           x: window.vaultUnassign('Arachnid Mesh', { unlock: true }),
           move: window.vaultFile('Arachnid Mesh', null, { move: true, mule: 'uni-small', by: 'hand', unlock: true }),
           store: STORE['d2r_vaultProv'], map: map() };
/* P1b — the door's read and the lock's read are TWO reads of storage. With REG-2415 the door refuses a store that will
   not read before the hand block is reached, so the hand block's own UNKNOWN check is met only when the first read
   answers and a later one throws (a storage read that fails mid-call). That check must still refuse: without it the
   UNKNOWN answer is taken for a lock and Shift goes to the release, or a same-locker drop answers 'already'. Only the
   lock's read fails; the release's own read answers, so a missing check shows as the lock dropped and the item moved. */
seed();
var _gi1b = window.LSR.getItem, _pr1b = 0, _st1b = STORE['d2r_vaultProv'];
window.LSR.getItem = function(k){
  if (k === 'd2r_vaultProv' && ++_pr1b === 2) throw new Error('the storage read failed');   /* the lock's read only */
  return _gi1b.apply(this, arguments);
};
OUT.p1b = { shift: window.vaultFile('Arachnid Mesh', HAND(), { mule: 'uni-small', unlock: true }), shiftReads: _pr1b };
_pr1b = 0;
OUT.p1b.same = window.vaultFile('Arachnid Mesh', HAND(), { mule: 'uni-armor' });
OUT.p1b.sameReads = _pr1b;
window.LSR.getItem = _gi1b;
OUT.p1b.storeKept = (STORE['d2r_vaultProv'] === _st1b);
OUT.p1b.row = row('Arachnid Mesh'); OUT.p1b.map = map();
/* P4 + P8 — a re-drop on the SAME locker, without and with Shift: an answer, never a filing */
seed(); CHRON.length = 0; STATUS.length = 0;
assignItem('Arachnid Mesh', 'uni-armor');
assignItem('Arachnid Mesh', 'uni-armor', { unlock: true });
OUT.p48 = { chron: CHRON.slice(), status: STATUS.slice(), row: row('Arachnid Mesh'),
            lock: window._vaultHardLock('Arachnid Mesh'), map: map() };
/* P5 — the locker is gone (a deleted mule keeps the witness row, mule:null) and the row is still locked */
seed();
delete assign['Arachnid Mesh'];
var _pr5 = prov(); _pr5['Arachnid Mesh'].mule = null; STORE['d2r_vaultProv'] = JSON.stringify(_pr5);
OUT.p5 = { plain: window.vaultFile('Arachnid Mesh', HAND(), { mule: 'uni-small' }) };
OUT.p5.rowAfterPlain = row('Arachnid Mesh'); OUT.p5.mapAfterPlain = map();
OUT.p5.shift = window.vaultFile('Arachnid Mesh', HAND(), { mule: 'uni-small', unlock: true });
OUT.p5.rowAfterShift = row('Arachnid Mesh'); OUT.p5.mapAfterShift = map();
/* P6 — a hand witness that names no locker moves nothing (the router says uni-armor, the row is locked in uni-small) */
seed();
rebuild('Stormshield', 'HARDENED', 30, 30, 'uni-small');
OUT.p6 = { r: window.vaultFile('Stormshield', HAND(), {}), map: map(), row: row('Stormshield') };
/* P7 — the vault audit's fix says the lock's refusal instead of dropping it */
seed(); STATUS.length = 0; ELS['vault-lock-alert'] = _el();
OUT.p7 = { applied: _vaultAuditApply({ fixable: true, kind: 'misroute', item: 'Arachnid Mesh', to: 'uni-small' }),
           alert: { hidden: ELS['vault-lock-alert'].hidden, text: ELS['vault-lock-alert'].textContent }, map: map() };
/* P9 — one parse of the witness store per CHANGE, not one per cell */
seed();
var _jp = JSON.parse, _np = 0; JSON.parse = function(){ _np++; return _jp.apply(JSON, arguments); };
for (var _i = 0; _i < 25; _i++) window._vaultHardLock('Arachnid Mesh');
var _np25 = _np;
STORE['d2r_vaultProv'] = STORE['d2r_vaultProv'] + ' ';
window._vaultHardLock('Arachnid Mesh');
JSON.parse = _jp;
OUT.p9 = { parsesFor25: _np25, afterChange: _np - _np25 };
/* THE SURFACE — the chip counts the locks, a refused drop is said in the banner, UNKNOWN reads 🔒 ? */
seed(); ELS['vault-lock-alert'] = _el(); ELS['vault-lock-chip'] = _el();
window._vaultLockChip();
OUT.surface = { chip: { hidden: ELS['vault-lock-chip'].hidden, text: ELS['vault-lock-chip'].textContent,
                        title: ELS['vault-lock-chip'].title } };
assignItem('Arachnid Mesh', 'uni-small');
OUT.surface.alert = { hidden: ELS['vault-lock-alert'].hidden, text: ELS['vault-lock-alert'].textContent };
STORE['d2r_vaultProv'] = '{ not json';
window._vaultLockChip();
OUT.surface.chipUnknown = { hidden: ELS['vault-lock-chip'].hidden, text: ELS['vault-lock-chip'].textContent };
/* P10 — SEEN ON PIXELS 2026-09-30: the banner sat ~600 px above a locker lower on the page; the refusal is also said AT the
   cell he acted on (the copy in view), once, and never floats when no copy is in view */
var BODYKIDS = [], CELLS = [];
function _cellAt(top){ var cl = {}; return { classList: { add: function(c){ cl[c] = 1; }, remove: function(c){ delete cl[c]; } }, offsetWidth: 63,
  getBoundingClientRect: function(){ return { top: top, bottom: top + 30, left: 800, right: 863, width: 63, height: 30 }; } }; }
document.querySelectorAll = function(sel){ return /Arachnid Mesh/.test(sel) ? CELLS : []; };
document.createElement = function(){ var e = _el(); e.style = {}; e.attrs = {}; e.offsetWidth = 300; e.offsetHeight = 52; e.parentNode = null;
  e.setAttribute = function(k, v){ e.attrs[k] = String(v); }; return e; };
document.body = { appendChild: function(e){ e.parentNode = document.body; BODYKIDS.push(e); if (e.id) ELS[e.id] = e; return e; },
                  removeChild: function(e){ e.parentNode = null; BODYKIDS = BODYKIDS.filter(function(x){ return x !== e; }); if (ELS[e.id] === e) delete ELS[e.id]; } };
window.innerHeight = 1000; window.innerWidth = 1400; window.scrollX = 0; window.scrollY = 700;
seed(); CELLS = [_cellAt(-400), _cellAt(560)];
OUT.p10 = { refused: window.vaultUnassign('Arachnid Mesh') };
var _pop = ELS['vault-lock-pop'] || null;
OUT.p10.pops = BODYKIDS.length; OUT.p10.text = _pop ? _pop.textContent : null;
OUT.p10.top = _pop ? _pop.style.top : null; OUT.p10.left = _pop ? _pop.style.left : null; OUT.p10.aria = _pop ? _pop.attrs['aria-hidden'] : null;
window.vaultUnassign('Arachnid Mesh');
OUT.p10.popsAfterTwo = BODYKIDS.length;
CELLS = [_cellAt(-400)];
window.vaultUnassign('Arachnid Mesh');
OUT.p10.popsNoneInView = BODYKIDS.length; OUT.p10.map = map();
/* P11 — a release takes its own refusal down (seen on pixels: "LOCKED ... Hold Shift" stayed up after Shift released it) */
seed(); CELLS = [_cellAt(560)]; ELS['vault-lock-alert'] = _el();
window.vaultUnassign('Arachnid Mesh');
OUT.p11 = { popBefore: BODYKIDS.length, alertBefore: !ELS['vault-lock-alert'].hidden };
OUT.p11.released = window.vaultUnassign('Arachnid Mesh', { unlock: true });
OUT.p11.popAfter = BODYKIDS.length; OUT.p11.alertAfter = !ELS['vault-lock-alert'].hidden; OUT.p11.map = map();
/* P12 — #114 (REG-1622): only the refused item's OWN release hushes it. A name inside its words (Mesh, Shift, Armor,
   UNI) or no name at all leaves the bubble and the banner standing. */
seed(); CELLS = [_cellAt(560)]; ELS['vault-lock-alert'] = _el();
window.vaultUnassign('Arachnid Mesh');
OUT.p12 = { before: [BODYKIDS.length, !ELS['vault-lock-alert'].hidden] };
['Mesh', 'Shift', 'Armor', 'UNI', ''].forEach(function(n){ _vaultLockHush(n); });
OUT.p12.others = [BODYKIDS.length, !ELS['vault-lock-alert'].hidden];
_vaultLockHush('Arachnid Mesh');
OUT.p12.own = [BODYKIDS.length, !ELS['vault-lock-alert'].hidden];
process.stdout.write(JSON.stringify(OUT));
"""


def _drive():
    s = _src()
    prog = (FILE.HARNESS + EXTRA + FILE._say_line(s) + FILE._door(s)
            + "var magicFinds = {}, unknownReads = new Set();\n" + _span(s, AUDIT_START, AUDIT_END)
            + _fn(s, UNASSIGN_START) + _span(s, ASSIGN_START, ASSIGN_END) + ASSIGN_END
            + _span(s, VR_START, VR_END) + _span(s, REMOVE_START, REMOVE_END) + _fn(s, RESTORE_START) + BODY)
    r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise AssertionError("the shipped doors would not execute — UNKNOWN, not passing: %s" % (r.stderr or r.stdout)[-1200:])
    return json.loads(r.stdout)


def _code_only(s):
    return FILE._code_only(s)


@unittest.skipIf(NODE is None, "node is absent — this law runs the SHIPPED doors; UNMEASURED, not passing")
class AHardenedFilingIsLockedUntilHeReleasesIt(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.out = _drive()

    def test_1_the_premise_is_a_hardened_row_that_says_locked(self):
        p = self.out["premise"]
        self.assertTrue(self.out["steps"]["seedHard"]["ok"], "premise: the HARDENED row was not rebuilt: %r" % self.out["steps"]["seedHard"])
        self.assertTrue(self.out["steps"]["seedProven"]["ok"], "premise: the PROVEN row was not rebuilt: %r" % self.out["steps"]["seedProven"])
        self.assertIs(True, p["hard"]["locked"], "premise: the HARDENED row does not carry locked:true: %r" % p["hard"])
        self.assertIs(False, p["proven"]["locked"], "premise: the PROVEN row is not locked:false: %r" % p["proven"])
        self.assertEqual({"Arachnid Mesh": "uni-armor", "Shako": "uni-armor"}, p["map"])
        lk = p["lockHard"]
        self.assertEqual(("HARDENED", 21, 21, "UNI-ARMOR"), (lk["tier"], lk["successes"], lk["trials"], lk["holder"]),
                         "the reader does not answer the row's own tier and tally: %r" % lk)
        self.assertIsNone(p["lockProven"], "a PROVEN row reads as locked: %r" % p["lockProven"])
        self.assertIn("🔒 locked", p["lineHard"], "the evidence line does not say the lock: %r" % p["lineHard"])
        self.assertIn("HARDENED 21/21", p["lineHard"])
        self.assertNotIn("locked", p["lineProven"], "a PROVEN row's line says locked: %r" % p["lineProven"])

    def test_2_the_machines_move_is_refused(self):
        m = self.out["machineMove"]
        self.assertFalse(m["r"]["ok"], "the vault audit moved a HARDENED row: %r" % m["r"])
        self.assertEqual("hardened", m["r"]["refused"])
        self.assertIn("LOCKED in UNI-ARMOR", m["r"]["why"])
        self.assertIn("Shift", m["r"]["why"], "the refusal does not name the release: %r" % m["r"]["why"])
        self.assertEqual("uni-armor", m["map"]["Arachnid Mesh"], "the map moved under a refusal")
        self.assertIs(True, m["row"]["locked"], "the row lost its lock under a refusal: %r" % m["row"])
        self.assertNotIn("unlockedAt", m["row"])

    def test_3_his_hands_move_is_refused_and_said(self):
        h = self.out["handMove"]
        self.assertEqual("uni-armor", h["map"]["Arachnid Mesh"], "a drag to another locker moved a HARDENED row: %r" % h["map"])
        self.assertTrue(h["status"] and h["status"][-1].startswith("🔒 "), "the refusal was not said on the status line: %r" % h["status"])
        self.assertIn("HARDENED 21/21", h["status"][-1])
        self.assertIn("Shift", h["status"][-1])
        self.assertFalse(h["door"]["ok"], "the door filed his hand over the lock: %r" % h["door"])
        self.assertEqual("hardened", h["door"]["refused"])
        self.assertIs(True, h["row"]["locked"])

    def test_4_a_re_drop_on_the_same_locker_leaves_the_evidence_row_standing(self):
        s = self.out["sameHome"]
        self.assertTrue(s["r"]["ok"], "a same-locker re-drop was refused outright: %r" % s["r"])
        self.assertEqual("already", s["r"]["mode"])
        self.assertIs(True, s["r"].get("locked"), "the same-locker answer does not say the row is locked: %r" % s["r"])
        self.assertEqual("stash", s["row"]["source"], "the evidence row was replaced by a hand row — the lock evaporated on a confirm: %r" % s["row"])
        self.assertIs(True, s["row"]["locked"])
        self.assertEqual("uni-armor", s["map"]["Arachnid Mesh"])

    def test_5_a_readers_re_look_never_overwrites_a_locked_row(self):
        s = self.out["readerSame"]
        self.assertTrue(s["r"]["ok"], s["r"])
        self.assertEqual("already", s["r"]["mode"], "two looks replaced a HARDENED row at the same locker: %r" % s["r"])
        self.assertIs(True, s["row"]["locked"], "the reader's re-look took the lock off the row: %r" % s["row"])
        self.assertEqual(21, s["row"]["trials"], "the reader's two looks overwrote the twenty-one: %r" % s["row"])

    def test_6_the_cell_x_is_refused_and_said(self):
        x = self.out["x"]
        self.assertFalse(x["r"]["ok"], "the cell ✕ unfiled a HARDENED row: %r" % x["r"])
        self.assertEqual("hardened", x["r"]["refused"])
        self.assertEqual("uni-armor", x["map"].get("Arachnid Mesh"), "the filing left under a refusal: %r" % x["map"])
        self.assertTrue(x["status"] and x["status"][-1].startswith("🔒 "), "the ✕ refusal was not said: %r" % x["status"])
        self.assertIn("click ✕", x["status"][-1], "the ✕ refusal does not say how to release it: %r" % x["status"])
        self.assertIs(True, x["row"]["locked"])

    def test_7_a_proven_row_moves_and_unassigns_freely(self):
        b = self.out["baseMove"]
        self.assertTrue(b["r"]["ok"], "the baseline: a PROVEN row would not move — the lock is an off switch: %r" % b["r"])
        self.assertEqual("moved", b["r"]["mode"])
        self.assertEqual("uni-small", b["map"]["Shako"])
        x = self.out["baseX"]
        self.assertTrue(x["r"]["ok"], "the baseline: a PROVEN row would not unassign: %r" % x["r"])
        self.assertFalse(x["r"]["unlocked"], "nothing was locked, yet the ✕ reports a release: %r" % x["r"])
        self.assertNotIn("Shako", x["map"])
        self.assertEqual("owned", (x["row"] or {}).get("kind"), "the receipt did not stay behind: %r" % x["row"])

    def test_8_shift_on_the_drop_releases_it_and_the_row_says_so(self):
        d = self.out["releaseDrop"]
        self.assertEqual("uni-small", d["map"]["Arachnid Mesh"], "Shift on the drop did not move the row: %r · %r" % (d["map"], d["status"]))
        self.assertEqual("hand", d["row"]["source"])
        uf = d["row"].get("unlockedFrom") or {}
        self.assertEqual(("HARDENED", 21, 21, "uni-armor"), (uf.get("tier"), uf.get("successes"), uf.get("trials"), uf.get("mule")),
                         "the hand row does not say what lock it opened: %r" % d["row"])
        self.assertIsNone(d["lock"], "the reader still says locked after the release: %r" % d["lock"])
        self.assertTrue(d["thenMove"]["ok"], "the machine's move is still refused after the release: %r" % d["thenMove"])
        self.assertTrue(d["status"] and d["status"][-1].startswith("🏦 "), "the move was not confirmed on the status line: %r" % d["status"])

    def test_9_shift_on_the_x_releases_it_and_the_receipt_says_so(self):
        x = self.out["releaseX"]
        self.assertFalse(x["refused"]["ok"], "premise: the plain ✕ did not refuse Stormshield: %r" % x["refused"])
        self.assertTrue(x["r"]["ok"], "Shift+✕ was refused: %r" % x["r"])
        self.assertIs(True, x["r"]["unlocked"])
        self.assertNotIn("Stormshield", x["map"])
        self.assertEqual("owned", (x["row"] or {}).get("kind"), "no receipt stayed behind: %r" % x["row"])
        self.assertTrue((x["row"] or {}).get("unlocked", {}).get("at"), "the receipt does not say it was unlocked: %r" % x["row"])
        self.assertIsNone(x["lock"])

    def test_10_an_unreadable_witness_store_is_unknown_and_unknown_refuses(self):
        u = self.out["unknown"]
        self.assertIs(True, (u["lock"] or {}).get("unknown"), "unreadable bytes read as a verdict: %r" % u["lock"])
        self.assertIn("UNKNOWN", u["lock"]["why"])
        for k in ("x", "hand", "same", "move"):
            self.assertFalse(u[k]["ok"], "%s proceeded on an unreadable witness store: %r" % (k, u[k]))
            self.assertEqual("prov-unreadable", u[k]["refused"], "%s: %r" % (k, u[k]))
        self.assertEqual({"Arachnid Mesh": "uni-armor", "Shako": "uni-armor"}, u["map"], "the map moved on UNKNOWN")
        self.assertEqual("{ not json", u["store"], "a hand door wrote over bytes it could not read")
        self.assertTrue(u["status"] and "UNKNOWN" in u["status"][-1], "UNKNOWN was not said: %r" % u["status"])

    def test_11_evidence_lanes_stay_free_and_the_undo_brings_the_lock_back(self):
        e = self.out["evidence"]
        self.assertEqual(["Arachnid Mesh"], e["removed"]["removed"], "the TV's unvault could not take a locked filing: %r" % e["removed"])
        self.assertNotIn("Arachnid Mesh", e["mapAfter"])
        self.assertIsNone(e["rowAfter"], "the row stayed after an evidence-lane removal: %r" % e["rowAfter"])
        self.assertEqual(1, e["restored"]["restored"], e["restored"])
        self.assertEqual("uni-armor", e["mapBack"].get("Arachnid Mesh"), "the undo did not re-file: %r" % e["mapBack"])
        self.assertIs(True, (e["rowBack"] or {}).get("locked"), "the undo lost the lock: %r" % e["rowBack"])
        self.assertEqual("HARDENED", (e["lockBack"] or {}).get("tier"), "the reader does not see the lock after the undo: %r" % e["lockBack"])

    def test_12_the_x_and_both_hand_paths_carry_the_release(self):
        """THE JOIN. A door that reads opts.unlock is the unjoined end unless the surface can send it. Code only,
        anchored on the CALLS — never on prose about them. [[source-reading-guard]] [[the-unjoined-end]]"""
        code = _code_only(_src())
        x_call = "window.vaultUnassign(\\'' + jsArg(n) + '\\', { unlock: !!event.shiftKey })"
        self.assertEqual(1, code.count(x_call), "the mule cell's ✕ does not send the Shift release (%d)" % code.count(x_call))
        drop = "mule.dataset.vaultMule, { unlock: !!e.shiftKey })"
        self.assertEqual(2, code.count(drop), "the drop and the click do not both carry the Shift release (%d of 2)" % code.count(drop))
        fwd = "{ mule: muleId, unlock: !!(opts && opts.unlock) }"
        self.assertEqual(1, code.count(fwd), "assignItem does not hand the release to the door (%d)" % code.count(fwd))


    # ── #98 (his ruling 2026-09-30: "whatever is logical. i trust you. just make it visually known") ──────────────────
    def test_13_unknown_never_releases_even_with_shift(self):
        p = self.out["p1"]
        self.assertEqual((p["hand"]["ok"], p["hand"].get("refused")), (False, "prov-unreadable"),
                         "Shift on an unreadable witness store filed the item: %s" % p["hand"])
        self.assertEqual((p["x"]["ok"], p["x"].get("refused")), (False, "prov-unreadable"),
                         "Shift+✕ on an unreadable witness store answered %s" % p["x"])
        self.assertFalse(p["move"]["ok"])
        self.assertEqual(p["store"], "{ not json", "a release under UNKNOWN wrote over the unreadable witness store")
        self.assertEqual(p["map"].get("Arachnid Mesh"), "uni-armor", "a filing moved or was deleted on UNKNOWN")

    def test_13b_unknown_at_the_lock_read_refuses_even_when_the_door_read_answered(self):
        """The hand block's own UNKNOWN check, reached: the door's read answers, the lock's read throws."""
        p = self.out["p1b"]
        self.assertGreaterEqual(p["shiftReads"], 2, "the premise: the lock read never reached storage after the door: %r" % p)
        self.assertGreaterEqual(p["sameReads"], 2, "the premise: the lock read never reached storage after the door: %r" % p)
        self.assertEqual((p["shift"]["ok"], p["shift"].get("refused")), (False, "prov-unreadable"),
                         "Shift with the lock UNKNOWN went past the hand block's check: %s" % p["shift"])
        self.assertIn("UNKNOWN", p["shift"].get("why") or "", "the refusal does not say UNKNOWN: %s" % p["shift"])
        self.assertEqual((p["same"]["ok"], p["same"].get("refused")), (False, "prov-unreadable"),
                         "a same-locker drop with the lock UNKNOWN answered as if the lock were read: %s" % p["same"])
        self.assertTrue(p["storeKept"], "a door wrote the witness store while its lock read was UNKNOWN")
        self.assertIs(True, (p["row"] or {}).get("locked"), "the lock evaporated on UNKNOWN: %r" % p["row"])
        self.assertEqual(p["map"].get("Arachnid Mesh"), "uni-armor", "a filing moved on UNKNOWN: %r" % p["map"])

    def test_14_a_same_locker_redrop_is_an_answer_not_a_filing(self):
        p = self.out["p48"]
        self.assertEqual([c for c in p["chron"] if c.get("status") == "filed-by-hand"], [],
                         "a drop on the locker it already sits in went on the record as 'you filed it here yourself'")
        self.assertEqual(p["row"]["source"], "stash", "the 21/21 evidence row was replaced by a hand row")
        self.assertIs(p["row"]["locked"], True, "Shift on the SAME locker spent the release: %s" % p["row"])
        self.assertIsNotNone(p["lock"])
        self.assertTrue(any("locked here" in x for x in p["status"]), p["status"])

    def test_15_a_locked_row_whose_locker_is_gone_still_refuses_and_shift_refiles_it(self):
        p = self.out["p5"]
        self.assertEqual((p["plain"]["ok"], p["plain"].get("refused")), (False, "hardened"),
                         "a plain drop replaced the evidence row of a locked item whose mule was deleted: %s" % p["plain"])
        self.assertIn("is gone", p["plain"]["why"])
        self.assertEqual(p["rowAfterPlain"]["source"], "stash")
        self.assertNotIn("Arachnid Mesh", p["mapAfterPlain"])
        self.assertTrue(p["shift"]["ok"], p["shift"])
        self.assertEqual(p["mapAfterShift"].get("Arachnid Mesh"), "uni-small")
        self.assertEqual((p["rowAfterShift"].get("unlockedFrom") or {}).get("tier"), "HARDENED",
                         "the release his Shift made is not on the row that replaced the evidence")

    def test_16_a_hand_witness_that_names_no_locker_moves_nothing(self):
        p = self.out["p6"]
        self.assertEqual((p["r"]["ok"], p["r"].get("mode")), (True, "already"),
                         "a hand witness that named no locker was refused as a move: %s" % p["r"])
        self.assertEqual(p["map"].get("Stormshield"), "uni-small")

    def test_17_the_audits_refused_fix_is_said(self):
        p = self.out["p7"]
        self.assertFalse(p["applied"])
        self.assertFalse(p["alert"]["hidden"], "the vault audit's fix was refused by the lock and nothing said so")
        self.assertIn("not applied", p["alert"]["text"])
        self.assertEqual(p["map"].get("Arachnid Mesh"), "uni-armor")

    def test_18_the_witness_store_is_parsed_once_per_change(self):
        p = self.out["p9"]
        self.assertLessEqual(p["parsesFor25"], 1, "25 lock reads of an unchanged store parsed it %d times" % p["parsesFor25"])
        self.assertEqual(p["afterChange"], 1, "a changed store was not re-read")

    def test_19_the_lock_is_counted_and_a_refusal_is_said_where_he_looks(self):
        sf = self.out["surface"]
        self.assertEqual((sf["chip"]["hidden"], sf["chip"]["text"]), (False, "\U0001f512 1 locked"), sf["chip"])
        self.assertIn("Shift", sf["chip"]["title"])
        self.assertFalse(sf["alert"]["hidden"], "a refused drop was said only on the status line")
        self.assertIn("Shift", sf["alert"]["text"])
        self.assertIn("Arachnid Mesh", sf["alert"]["text"])
        self.assertEqual(sf["chipUnknown"]["text"], "\U0001f512 ?", "an unreadable store must read UNKNOWN on the chip")

    def test_21_a_refusal_is_said_at_the_cell_he_acted_on(self):
        """SEEN ON PIXELS 2026-09-30 (headless Chrome, a real ✕ click on a locker lower on the page): the banner and the
        status line sit in the Vault's header, ~600 px above his view, so the refusal on screen was a 0.9 s shake."""
        p = self.out["p10"]
        self.assertEqual(p["map"].get("Arachnid Mesh"), "uni-armor", "the refused ✕ moved the item: %r" % p["map"])
        self.assertEqual(p["pops"], 1, "a refusal was not said at the cell he acted on")
        self.assertIn("Shift", p["text"] or "")
        self.assertIn("Arachnid Mesh", p["text"] or "")
        self.assertEqual((p["top"], p["left"]), ("1200px", "682px"),
                         "the bubble is not over the copy of the cell that is IN VIEW: top %r left %r" % (p["top"], p["left"]))
        self.assertEqual(p["aria"], "true", "the bubble must not be read aloud twice - the banner is the one announced")
        self.assertEqual(p["popsAfterTwo"], 1, "two refusals left two bubbles")
        self.assertEqual(p["popsNoneInView"], 0, "with no copy in view a bubble floated over nothing")

    def test_22_a_release_takes_its_own_refusal_down(self):
        p = self.out["p11"]
        self.assertEqual((p["popBefore"], p["alertBefore"]), (1, True), "the premise: the plain ✕ was refused, loudly: %r" % p)
        self.assertNotIn("Arachnid Mesh", p["map"], "Shift+✕ did not release it to the dock")
        self.assertEqual((p["popAfter"], p["alertAfter"]), (0, False),
                         "after Shift released it, the refusal still said LOCKED beside it: %r" % p)

    def test_23_only_its_own_release_hushes_a_refusal(self):
        p = self.out["p12"]
        self.assertEqual(p["before"], [1, True], "the premise: Arachnid Mesh's refusal is up as a bubble and a banner")
        self.assertEqual(p["others"], [1, True],
                         "another release whose name sits inside the refusal's words (or no name) took it down: %r" % p)
        self.assertEqual(p["own"], [0, False], "its own release no longer hushes it: %r" % p)

    def test_20_the_cell_wears_the_lock_and_the_header_holds_the_chip(self):
        """The render half, read in the source (the pixels are looked at by hand and by the Grok eye): the cell's class
        carries the lock, its badge sits before the ✕, both surfaces exist, and every render refreshes the chip."""
        s = _code_only(_src())
        self.assertIn("(cl.approx ? ' vmc-approx' : '') + _lockCls + '\" style=", s)
        # REG-2882 - the badge sits before the ✕ IN THE SAME CELL. REG-2878 drew the listed mark between them (one line, a
        # span), so adjacency went red on reach; a cell boundary or a second ✕ between them is still the defect.
        lock = s.index("          + _lockTag\n")
        x = s.index("'<button class=\"vm-unassign vm-cell-x\"", lock)
        self.assertNotIn("</div>", s[lock:x], "the lock badge and the ✕ are no longer in one cell")
        between = s[lock:x].splitlines()
        self.assertEqual(between[-1].strip(), "+", "the ✕ is not its own term after the badge: %r" % s[lock:x])
        self.assertTrue(all(ln.strip().startswith("+ (") for ln in between[1:-1]),
                        "something other than a mark sits between the lock badge and the ✕: %r" % s[lock:x])
        self.assertIn('id="vault-lock-chip"', _src())
        self.assertIn('id="vault-lock-alert" role="alert"', _src())
        self.assertIn("if (window._vaultLockChip) window._vaultLockChip();", s)
        mp = _span(_src(), "  function _mpEqWrite(all){", "\n  }\n")
        self.assertIn("var _vfM = window.vaultFile(", mp)
        self.assertIn("window._vaultLockSay(e.name,", mp, "the mule window drops the door's refusal again")


RED_PROOF = [
    {"why": "#114 (REG-1622) - a release hushes any refusal whose words CONTAIN its name (and an empty name hushes all)",
     "file": "bible.html",
     "find": "      if (pop && pop.parentNode && pop._vlaItem === n) pop.parentNode.removeChild(pop);\n",
     "replace": "      if (pop && pop.parentNode && String(pop.textContent || '').indexOf(n) >= 0) pop.parentNode.removeChild(pop);\n",
     "matches": 1},
    {
        "why": "#98 seen on pixels - after Shift released it, the refusal still says LOCKED beside it for 9 s",
        "file": "bible.html",
        "find": "    all[nm] = r; _provWrite(all); _vaultLockHush(nm); return true;\n",
        "replace": "    all[nm] = r; _provWrite(all); return true;\n",
        "matches": 1,
    },
    {
        "why": "#98 seen on pixels - the refusal is said only in the header, ~600 px above a locker lower on the page",
        "file": "bible.html",
        "find": "      if (at){\n        /* seen on pixels: his hover had opened the item's art card (#arttip, z 9999) over the words - it steps aside */\n",
        "replace": "      if (false){\n        /* seen on pixels: his hover had opened the item's art card (#arttip, z 9999) over the words - it steps aside */\n",
        "matches": 1,
    },
    {
        "why": "#98 seen on pixels - the bubble floats over a copy of the cell that is out of view",
        "file": "bible.html",
        "find": "if (!at && r && r.width > 0 && r.bottom > 0 && r.top < vh) at = { c: c, r: r }; });",
        "replace": "if (!at && r && r.width > 0) at = { c: c, r: r }; });",
        "matches": 1,
    },
    {
        "why": "#98 seen on pixels - every refusal adds another bubble",
        "file": "bible.html",
        "find": "      if (old && old.parentNode) old.parentNode.removeChild(old);\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#98 P1 - UNKNOWN is checked only as a refusal reason again: Shift on an unreadable store reaches the release",
        "file": "bible.html",
        "find": "      if (lkH && lkH.unknown)\n        return { ok: false, refused: 'prov-unreadable', lock: lkH, why: _hardLockWhy(nm, lkH, 'moved') };\n",
        "replace": "      if (false)\n        return { ok: false, refused: 'prov-unreadable', lock: lkH, why: _hardLockWhy(nm, lkH, 'moved') };\n",
        "matches": 1,
    },
    {
        "why": "#98 P5 - the lock is asked only while the name is filed: a deleted mule's locked row is replaced by a plain drop",
        "file": "bible.html",
        "find": "    if (hand){\n      lkH = _hardLock(nm);\n",
        "replace": "    if (hand && assign[nm] != null){\n      lkH = _hardLock(nm);\n",
        "matches": 1,
    },
    {
        "why": "#98 P6 - a hand witness that names no locker is refused as a move again",
        "file": "bible.html",
        "find": "        if (assign[nm] != null && !opts.mule)\n          return { ok: true, mode: 'already', mule: assign[nm], locked: true,\n",
        "replace": "        if (false)\n          return { ok: true, mode: 'already', mule: assign[nm], locked: true,\n",
        "matches": 1,
    },
    {
        "why": "#98 P4 - his drop records 'you filed it here yourself' over a locked evidence row again",
        "file": "bible.html",
        "find": "    if (_vf.mode === 'already' && _vf.locked){ _vaultLockSay(name, '🔒 ' + _vf.why, false); return { ok: true, mode: 'already', locked: true,",
        "replace": "    if (false){ _vaultLockSay(name, '🔒 ' + _vf.why, false); return { ok: true, mode: 'already', locked: true,",
        "matches": 1,
    },
    {
        "why": "#98 P1/P3 - Shift+✕ on an unreadable store is let through to the release again",
        "file": "bible.html",
        "find": "    if (lkU && (lkU.unknown || opts.unlock !== true)){\n",
        "replace": "    if (lkU && opts.unlock !== true){\n",
        "matches": 1,
    },
    {
        "why": "#98 P9 - every lock read parses the whole witness store again",
        "file": "bible.html",
        "find": "    if (raw === _hlMemo.raw) return _hlMemo.all;\n",
        "replace": "    if (false) return _hlMemo.all;\n",
        "matches": 1,
    },
    {
        "why": "#98 - a refusal is said only on the 4.2 s status line again: the banner never shows",
        "file": "bible.html",
        "find": "      if (box){\n        box.textContent = msg; box.hidden = false; box._vlaItem = String(nm == null ? '' : nm);   /* #114: whose refusal */\n",
        "replace": "      if (false){\n        box.textContent = msg; box.hidden = false; box._vlaItem = String(nm == null ? '' : nm);   /* #114: whose refusal */\n",
        "matches": 1,
    },
    {
        "why": "#98 P7 - the vault audit drops the lock's refusal again",
        "file": "bible.html",
        "find": "        if (!_mv0.ok){ if ((_mv0.refused === 'hardened' || _mv0.refused === 'prov-unreadable') && window._vaultLockSay)\n",
        "replace": "        if (!_mv0.ok){ if (false && window._vaultLockSay)\n",
        "matches": 1,
    },
    {
        "why": "#98 - the header chip stops counting the locks",
        "file": "bible.html",
        "find": "    el.textContent = '🔒 ' + c.locked + ' locked' + (c.released ? ' · ' + c.released + ' released' : '');\n",
        "replace": "    el.textContent = '';\n",
        "matches": 1,
    },
    {
        "why": "#41 rank 17 - the reader answers null for every row: the lock is a label again",
        "file": "bible.html",
        "find": "if (!r || typeof r !== 'object' || r.kind === 'owned' || r.locked !== true) return null;   /* the lock is the row's own word */",
        "replace": "if (!r || typeof r !== 'object' || r.kind === 'owned' || r.locked !== 'never') return null;   /* the lock is the row's own word */",
        "matches": 1,
    },
    {
        "why": "#41 rank 17 - the machine's move takes a HARDENED row again",
        "file": "bible.html",
        "find": "if (lkM && (lkM.unknown || opts.unlock !== true)) return",
        "replace": "if (false && lkM && (lkM.unknown || opts.unlock !== true)) return",
        "matches": 1,
    },
    {
        "why": "#41 rank 17 - his drag to another locker takes a HARDENED row again",
        "file": "bible.html",
        "find": "        if (opts.unlock !== true)\n          return { ok: false, refused: 'hardened', lock: lkH,",
        "replace": "        if (false)\n          return { ok: false, refused: 'hardened', lock: lkH,",
        "matches": 1,
    },
    {
        "why": "#41 rank 17 - a same-locker re-drop is refused outright instead of leaving the evidence row standing",
        "file": "bible.html",
        "find": "        if (assign[nm] === home)\n          return { ok: true, mode: 'already', mule: home, locked: true,",
        "replace": "        if (false)\n          return { ok: true, mode: 'already', mule: home, locked: true,",
        "matches": 1,
    },
    {
        "why": "#41 rank 17 - a reader's two looks overwrite a locked evidence row at the same locker again",
        "file": "bible.html",
        # 150af30a gave the same-locker refusal a body ({ ... _noteHand ... }), so the anchor ends at its brace
        "find": "if (_pw && _pw.kind !== 'owned' && _pw.locked === true) return",
        "replace": "if (false && _pw && _pw.kind !== 'owned' && _pw.locked === true) return",
        "matches": 1,
    },
    {
        "why": "#41 rank 17 - the cell ✕ unfiles a HARDENED row again",
        "file": "bible.html",
        "find": "    if (lkU && (lkU.unknown || opts.unlock !== true)){\n",
        "replace": "    if (false && lkU && (lkU.unknown || opts.unlock !== true)){\n",
        "matches": 1,
    },
    {
        "why": "#41 rank 17 - unreadable witness bytes read as {} (not locked) and the hand doors proceed",
        "file": "bible.html",
        "find": "try { all = JSON.parse(raw); } catch (e) { all = null; }",
        "replace": "try { all = JSON.parse(raw); } catch (e) { all = {}; }",
        "matches": 1,
    },
    {
        "why": "#41 rank 17 - assignItem drops the release, so Shift on the drop can never open a lock",
        "file": "bible.html",
        "find": "{ mule: muleId, unlock: !!(opts && opts.unlock) }",
        "replace": "{ mule: muleId, unlock: false }",
        "matches": 1,
    },
    {
        "why": "#41 rank 17 - the mule cell's ✕ stops sending the Shift release (the unjoined end)",
        "file": "bible.html",
        "find": "window.vaultUnassign(\\'' + jsArg(n) + '\\', { unlock: !!event.shiftKey })",
        "replace": "window.vaultUnassign(\\'' + jsArg(n) + '\\')",
        "matches": 1,
    },
    {
        "why": "#41 rank 17 - the drop and the click stop sending the Shift release",
        "file": "bible.html",
        "find": "mule.dataset.vaultMule, { unlock: !!e.shiftKey })",
        "replace": "mule.dataset.vaultMule)",
        "matches": 2,
    },
    {
        "why": "#41 rank 17 - the evidence line stops saying the lock where it says the tier",
        "file": "bible.html",
        "find": "(r.locked === true ? ' · \U0001F512 locked' :",
        "replace": "(r.locked === true ? '' :",
        "matches": 1,
    },
    {"why": "REG-2882 - the lock badge is drawn outside the cell its ✕ closes",
     "file": "bible.html",
     "find": "          + _lockTag\n          + (_lsc ?",
     "replace": "          + _lockTag + '</div><div>'\n          + (_lsc ?",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
