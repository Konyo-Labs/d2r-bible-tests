#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""THE RIVER DRAINS EVERY PASS — FIFO, KEEP THE NEWEST 8, EACH CONSOLE ITS OWN.

HIS WORDS, 2026-09-27: *"session reels in shelf registered by FIFO first in first out and getting
extracted and tallied and ledgered accoridngly to its won indivudal console. and that it can be seen
in shelf rendering and allproeprly getting delted after the 8 sessions"* — and #255: *"getting pruned
and extracted data wise and eventually tombstones to get deleted.. that way storage is always smooth
and optimized and not stacking up"* / *"its already suppose to do this"* / *"as architecture"*.

WHAT WAS MEASURED BEFORE ANY OF THIS WAS WRITTEN — and the brief's root cause did NOT survive it:

  · The brief said the pass only frees under disk pressure (`free_mb=(need_mb or None)`). Above
    floor+headroom that expression is None — NO target — and has been since v2226. His live console
    (GET /api/status, 11.8 GB free) reported `eligible: 0`: 19 reel dirs = 8 test fixtures + the
    newest 8 + 3 held `panels-never-banked`. His drain was at its floor, correctly.
  · The REAL defect was the band at or below floor+headroom: there `need_mb` is positive, plan()
    stopped after selecting that much, and every other finished reel was held `target-met`.
    Driven here on 4 finished reels with 0.5 MB needed: ONE released, three held. Disk pressure freed
    LESS than a roomy disk — the inversion of what pressure is for. His disk falls ~0.6 GB/day toward it.
  · And nothing watched the mouth: shelf_driver's `deleter` lane declares no work period, so a drain
    that stopped with reels owed could only ever read UNTIMED.

WHAT THIS LAW DRIVES — the SHIPPED `control_app._retention_once` and `reel_retention.apply_plan`, on
fixture worlds, with a pinned clock and a pinned disk, counting which directories survive:

  1. twelve finished reels + one that is NOT sealed: with plenty of disk the four oldest finished
     reels are released OLDEST FIRST, the unsealed one is KEPT AND NAMED (tag + why), the newest
     KEEP_RECENT are never touched, and a second pass releases nothing more;
  2. disk pressure — inside the headroom band AND below the floor — releases every finished reel,
     never fewer than a roomy disk would;
  3. every path resolves from THAT console's own tree: tombstones and the per-pass series land in
     the fixture world, never in tv/;
  4. THE HEART: the drain speaks on/worked/lastTs/owed; three passes that carry the same owed reels
     and release nothing read STOPPED, and a relaunch in between cannot reset that; a busy drain
     that releases every pass never cries wolf; the doctor row reads the wire and goes MISSING on a
     stopped drain, UNKNOWN when the plan cannot run, UNMEASURED on a console that never filmed;
  5. a deleter that REFUSES (its lock holds) is said as a refusal, never as "freed 0 MB".

⚠ #84 (REG-1517) — the world's reels are PLACED ON ITS RIVER as they are made (finished -> ROUTED,
unsealed -> PRINTER), because the drain now reads the river's own positions beside the mouth: a
mouth that drained with an unsealed reel older than the newest KEEP_RECENT still at PRINTER is
BLOCKED / owed 1, not CLEAR / owed 0 — the ALT's defect in miniature, and this world always had it.
A world nobody stamped would read UNKNOWN (a floor), never CLEAR. The river's own law is
test_the_drain_names_what_is_blocked_upstream.

⚠ No reel id is written literally in this file: a real-looking id in test source makes retention
hold that footage as a fixture (test_no_pinned_footage). Ids are minted from a 2017 stamp.
⚠ Nothing here touches his tree: TV_HIST, rr.HERE and ca.HERE all point at a scratch world, and the
import-time stores are redirected BEFORE control_app is imported.
RED_PROOF below. [[heart-first]] [[unknown-stays-unknown]] [[regression-guard]]
"""
import io
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
import unittest.mock as mock

import fixture_tmp as _fx_tmp  # noqa: E402  #171 — this run's scratch dirs leave with it
_fx_tmp.contain()

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import console_safe  # noqa: E402
console_safe.enable()

# ⚠ BEFORE control_app IS IMPORTED: its import-time stores (the vault seal store, the chronicle
# autoread store) resolve ONCE, from TV_HIST, at import. Point them at a scratch world so no reading
# this law makes can land on his live files. [[feedback-fixtures-never-touch-live-data]]
_BOOT = tempfile.mkdtemp(prefix="drain_boot_")
_SAVED_ENV = dict((k, os.environ.get(k)) for k in
                  ("TV_HIST", "TV_VAULT_SWEPT", "TV_CHRON_AUTOREAD", "TV_AUTO_PRUNE"))
os.makedirs(os.path.join(_BOOT, "hist"))
os.environ["TV_HIST"] = os.path.join(_BOOT, "hist")
os.environ["TV_VAULT_SWEPT"] = os.path.join(_BOOT, "vault_swept.json")
os.environ["TV_CHRON_AUTOREAD"] = os.path.join(_BOOT, "chron_autoread.json")

import reel_retention as RR   # noqa: E402
import control_app as CA      # noqa: E402
import console_doctor as CD   # noqa: E402
import self_arming as SA      # noqa: E402

#: A stamp no recording can carry (2017), per frame_authority.test_referenced_reels.
BASE_MS = 1500000000000
HOUR_MS = 3600 * 1000
MB = 1024 * 1024
_REAL_MAY = SA.may


class _Clock(object):
    """A pinned clock that still moves forward, so rows keep their order. -> seconds"""

    def __init__(self, start_s):
        self.t = float(start_s)

    def __call__(self):
        self.t += 0.001
        return self.t


def _usage(free_gb):
    return shutil._ntuple_diskusage(int(500e9), int(500e9 - free_gb * 1e9), int(free_gb * 1e9))


class _World(object):
    """One console's own tree: W/ (HERE) with W/hist (TV_HIST), its ledgers and its witness index."""

    def __init__(self, tc, n_finished, unsealed_at=None):
        self.tc = tc
        self.root = tempfile.mkdtemp(prefix="drain_world_")
        tc.addCleanup(shutil.rmtree, self.root, True)
        self.hist = os.path.join(self.root, "hist")
        os.makedirs(self.hist)
        self.names = []
        self.chron, self.vault = {}, {}
        n = n_finished + (1 if unsealed_at is not None else 0)
        self.unsealed = None
        for i in range(n):
            self.add(sealed=(i != unsealed_at), at_ms=BASE_MS + i * HOUR_MS)
            if i == unsealed_at:
                self.unsealed = self.names[-1]
        self.write_ledgers()
        self._write(os.path.join(self.root, "vault_accum.json"), {"owned": []})
        self._write(os.path.join(self.root, "vault_seen.json"), {"rows": []})

    @property
    def river(self):
        """Where this world's river remembers its reels: river_stamp._store_path() under TV_HIST=hist.
        #84 (REG-1517) — the drain reads the river's own positions now, so a world whose reels were
        never stamped reads UNKNOWN (a floor), never CLEAR; every reel here is placed as it is made."""
        return os.path.join(self.hist, "river_stamp.jsonl")

    @staticmethod
    def _write(p, blob):
        with io.open(p, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(blob))

    def add(self, sealed=True, at_ms=None, station=None, stamp_at=None):
        """A reel that was filmed, read (pages>0) and — unless `sealed` is False — vault-sealed.

        Its river position is stamped as it is made: a finished reel at ROUTED (the mouth — the
        extraction contract is satisfied), an unsealed one at PRINTER ("the names were read; the
        session carries no seal"), or `station` when a law needs the ALT's shape. `stamp_at` is the
        arrival time the river records (default: when the reel was filmed)."""
        at_ms = at_ms if at_ms is not None else BASE_MS + (len(self.names) + 1000) * HOUR_MS
        nm = "reel_s_%d_%d" % (at_ms, 100 + len(self.names))
        d = os.path.join(self.hist, nm)
        os.makedirs(d)
        with open(os.path.join(d, "f_%d.jpg" % at_ms), "wb") as fh:
            fh.truncate(MB)                       # sparse: 1 MB to _dir_mb, ~0 bytes on disk
        self.names.append(nm)
        self.chron[nm] = {"pages": 9}
        if sealed:
            self.vault[nm] = {"rows": 0}
        import river_stamp as _rs
        st = _rs.stamp(nm, station or ("ROUTED" if sealed else "PRINTER"), by="fixture:world",
                       at=(stamp_at if stamp_at is not None else at_ms), path=self.river)
        self.tc.assertTrue(st.get("wrote"), "the world could not place its reel on the river: %r" % st)
        return nm

    def write_ledgers(self):
        self._write(os.path.join(self.root, "chronicle_swept.json"), self.chron)
        self._write(os.path.join(self.root, "vault_swept.json"), self.vault)

    def on_disk(self):
        return sorted(d for d in _fx_tmp.list_own(self.hist) if d.startswith("reel_"))

    def tombstones(self):
        p = os.path.join(self.root, "reel_tombstones.json")
        if not os.path.exists(p):
            return []
        with io.open(p, encoding="utf-8") as fh:
            return (json.load(fh) or {}).get("reels") or []

    def series(self):
        p = os.path.join(self.root, "disk_history.jsonl")
        if not os.path.exists(p):
            return []
        with io.open(p, encoding="utf-8") as fh:
            return [json.loads(l) for l in fh if l.strip()]


class _Base(unittest.TestCase):

    def setUp(self):
        for k in ("TV_AUTO_PRUNE",):
            self._restore_env(k)
            os.environ.pop(k, None)

    def _restore_env(self, k):
        was = os.environ.get(k)
        self.addCleanup(lambda: os.environ.__setitem__(k, was) if was is not None
                        else os.environ.pop(k, None))

    def _bind(self, w, floor=None, headroom=None):
        """Make `w` THIS console's world for the rest of the test."""
        self._restore_env("TV_HIST")
        os.environ["TV_HIST"] = w.hist
        pairs = [(RR, "HERE", w.root), (CA, "HERE", w.root)]
        if floor is not None:
            pairs.append((CA, "ON_AIR_FLOOR_GB", floor))
        if headroom is not None:
            pairs.append((CA, "PRUNE_HEADROOM_GB", headroom))
        for mod, attr, val in pairs:
            self.addCleanup(setattr, mod, attr, getattr(mod, attr))
            setattr(mod, attr, val)
        RR._TRIAGE_CACHE["at"] = None

    def _pass(self, free_gb, world_ok=True, frame_release=True, in_flight=None):
        """ONE retention pass, driven through the shipped code with every precondition STATED."""
        def _flight(*_a, **_k):
            if in_flight:
                return False, in_flight
            return True, "fixture: nothing in flight"

        def _may(lock):
            if lock == "frame.release":
                return ((True, "fixture: the frame.release lock is open") if frame_release else
                        (False, "fixture: frame.release is LOCKED"))
            return _REAL_MAY(lock)
        world = ({"state": "ok", "why": "fixture: a confirmed world"} if world_ok else
                 {"state": "unknown", "why": "fixture: the board world was never confirmed"})
        with mock.patch("time.time", self.clock), \
                mock.patch("shutil.disk_usage", return_value=_usage(free_gb)), \
                mock.patch.object(CA, "board_identity_drift", lambda: world), \
                mock.patch.object(CA, "nothing_in_flight", _flight), \
                mock.patch.object(SA, "may", _may):
            r = CA._retention_once()
            st = CA.retention_state()
        return r, st

    def _doctor(self, st):
        """The doctor row, reading the wire this pass published. -> (state, why)"""
        real = CD._get
        CD._get = lambda path, *a, **k: ({"retention": st} if path == "/api/status" else None)
        try:
            with mock.patch("time.time", self.clock):
                return CD._check_the_retention_drain_is_draining()
        finally:
            CD._get = real

    def setUpClock(self):
        self.clock = _Clock(BASE_MS / 1000.0 + 400 * 3600)


class TheRiverDrainsFifoAndKeepsTheNewest(_Base):
    """★ Claims 1 and 3 — twelve finished reels and one unsealed, plenty of disk."""

    def setUp(self):
        _Base.setUp(self)
        self.setUpClock()
        # the unsealed reel sits AMONG the old ones, so "oldest first" must step around a bar
        self.w = _World(self, n_finished=RR.KEEP_RECENT + 4, unsealed_at=2)
        self._bind(self.w)
        self.newest = self.w.names[-RR.KEEP_RECENT:]
        self.old_finished = [n for n in self.w.names[:-RR.KEEP_RECENT] if n != self.w.unsealed]
        self.assertEqual(len(self.old_finished), 4, "premise: four finished reels past the newest")
        self.assertEqual(len(self.w.on_disk()), RR.KEEP_RECENT + 5, "premise: the whole shelf")

    def test_the_four_oldest_finished_go_oldest_first_and_the_newest_are_never_touched(self):
        r, st = self._pass(free_gb=500.0)
        self.assertEqual(sorted(r.get("removed") or []), sorted(self.old_finished),
                         "with plenty of disk the pass did not release exactly the four finished "
                         "reels older than the newest %d: %r" % (RR.KEEP_RECENT, r))
        left = self.w.on_disk()
        for nm in self.newest:
            self.assertIn(nm, left, "one of the newest %d was deleted: %s" % (RR.KEEP_RECENT, nm))
        self.assertIn(self.w.unsealed, left, "a reel that is NOT sealed was deleted")
        tomb = [t.get("reel") for t in self.w.tombstones()]
        self.assertEqual(tomb, self.old_finished,
                         "the tombstone record is not the four released reels OLDEST FIRST: %r" % tomb)

    def test_a_reel_that_is_not_sealed_is_kept_and_NAMED(self):
        self._pass(free_gb=500.0)
        p = RR.plan(self.w.hist)
        row = [k for k in p.get("kept") or [] if k.get("reel") == self.w.unsealed]
        self.assertEqual(len(row), 1, "the unsealed reel is not on the kept list at all")
        self.assertEqual(row[0].get("tag"), "vault-owes",
                         "the unsealed reel is held for the wrong reason: %r" % row[0])
        self.assertIn("VAULT lane has never swept it", row[0].get("why") or "",
                      "the kept reel does not say WHY it is held")
        st = CA.retention_state()
        self.assertEqual(st.get("lockedBehindASweep"), 1,
                         "the console does not report the unsealed reel as waiting: %r"
                         % st.get("lockedBehindASweep"))

    def test_a_second_pass_releases_nothing_more(self):
        self._pass(free_gb=500.0)
        after_one, tomb_one = self.w.on_disk(), self.w.tombstones()
        r2, st2 = self._pass(free_gb=500.0)
        self.assertEqual(self.w.on_disk(), after_one, "a second pass took more reels")
        self.assertEqual(len(self.w.tombstones()), len(tomb_one),
                         "a second pass wrote more tombstones")
        self.assertFalse((r2 or {}).get("removed"), "a second pass reported removing something")
        # #84 (REG-1517) — the mouth is drained, and the unsealed reel older than the newest
        # KEEP_RECENT is still waiting at PRINTER: that is BLOCKED, owed 1, never CLEAR
        self.assertEqual(st2["drain"]["state"], "BLOCKED", st2["drain"])
        self.assertEqual(st2["drain"]["owed"], 1)
        self.assertEqual(st2["drain"]["owedAtMouth"], 0, "the mouth itself owes nothing")

    def test_every_path_resolves_from_THIS_consoles_own_tree(self):
        """Claim 3 — per console. The deleter's record, the per-pass series and the drain's
        `worked` reading all resolve to the world that was drained.

        ⚠ ASKED OF THE RESOLVERS, NEVER BY STAT-ING tv/. On his Mac the real tv/disk_history.jsonl
        is appended by his live console every 15 minutes, so a before/after stat of it would go red
        whenever his console happened to write mid-pass — the instrument, not the code. And reading
        his files at all is a fixture touching live data. [[feedback-fixtures-never-touch-live-data]]
        """
        self._pass(free_gb=500.0)
        tomb = os.path.join(self.w.root, "reel_tombstones.json")
        self.assertEqual(RR._tombstone_path(self.w.hist), tomb,
                         "the deleter records its tombstones outside this console's tree")
        self.assertEqual(CA._disk_history_path(), os.path.join(self.w.root, "disk_history.jsonl"),
                         "the per-pass series resolves outside this console's tree")
        import shelf_driver as SD
        beat = SD.lane_beat("deleter", allow_import=True)
        self.assertEqual(beat.get("store"), tomb,
                         "the drain's `worked` reads a ledger that is not this console's")
        self.assertNotEqual(os.path.dirname(tomb), HERE, "premise: the world is not tv/")
        self.assertEqual(len(self.w.tombstones()), 4, "the tombstones are not in this console's tree")
        self.assertTrue(self.w.series(), "the per-pass series is not in this console's tree")
        self.assertEqual(beat.get("works"), 4,
                         "the deleter's record counted reels that were not released in this world")

    def test_the_drain_speaks_the_shared_vocabulary_after_it_drains(self):
        r, st = self._pass(free_gb=500.0)
        dr = st.get("drain") or {}
        for k in ("on", "worked", "lastTs", "owed"):
            self.assertIn(k, dr, "the drain does not answer %r" % k)
        # #84 (REG-1517) — this world is the ALT in miniature: the four finished reels drained and
        # ONE unsealed reel older than the newest KEEP_RECENT still waits at PRINTER. Before the fix
        # this read CLEAR / owed 0 ("nothing is owed") over that reel.
        self.assertEqual(dr["state"], "BLOCKED", dr)
        self.assertEqual(dr["owed"], 1, "the unsealed reel waiting at PRINTER is not owed")
        self.assertEqual(dr["owedAtMouth"], 0, "a drained mouth still reports reels owed")
        self.assertIn("waiting at PRINTER 1", dr.get("why") or "", dr)
        self.assertEqual(dr["worked"], 4, "worked is not the deleter's own lifetime record")
        self.assertIsNotNone(dr["lastTs"], "a deleter that just released has no lastTs")
        rows = self.w.series()
        self.assertEqual([x.get("owed") for x in rows if "owed" in x], [4],
                         "the pass did not stamp what it owed on its own row")
        self.assertEqual([x.get("released") for x in rows if "released" in x], [4])


class AVaultPictureHoldsItsReel(_Base):
    """2026-09-28 — HIS §26: "the evidence linked and attached with the picture being able to be clicked". Grok's
    f189f767 recorded a `kept` list on the tombstone, but apply_plan still rmtree's the WHOLE reel and nothing called
    release_uncited, so a drained reel took the picture a vault item stands on. Driven: the real pass on a scratch
    world, only the witness index stubbed to cite one frame of one old reel."""

    def setUp(self):
        _Base.setUp(self)
        self.setUpClock()
        self.w = _World(self, n_finished=RR.KEEP_RECENT + 4)
        self._bind(self.w)
        self.old = self.w.names[:4]
        self.cited_reel = self.old[1]
        d = os.path.join(self.w.hist, self.cited_reel)
        self.cited_frame = [f for f in _fx_tmp.list_own(d) if f.endswith(".jpg")][0]
        import frame_authority as FA
        real = FA.witness_index
        self.addCleanup(setattr, FA, "witness_index", real)
        self.FA, self.real = FA, real

    def _cite(self, cited):
        def _wi(root=None, _real=self.real):
            out = dict(_real(root))
            out["cited"] = cited
            return out
        self.FA.witness_index = _wi

    def test_the_reel_releases_and_only_its_vault_picture_stays(self):
        d = os.path.join(self.w.hist, self.cited_reel)
        with open(os.path.join(d, "uncited_extra.jpg"), "wb") as fh:
            fh.write(b"x")
        self._cite({self.cited_frame})
        r, _st = self._pass(free_gb=500.0)
        self.assertEqual(sorted(r.get("removed") or []), sorted(self.old),
                         "the four old finished reels were not all released: %r" % r)
        self.assertEqual(sorted(_fx_tmp.list_own(d)), [self.cited_frame],
                         "the released reel did not keep EXACTLY its vault picture: %r" % sorted(_fx_tmp.list_own(d)))
        for nm in self.old:
            if nm != self.cited_reel:
                self.assertNotIn(nm, self.w.on_disk(), "an uncited old reel was not released: %s" % nm)
        rows = dict((t.get("reel"), t) for t in self.w.tombstones())
        self.assertEqual(rows.get(self.cited_reel, {}).get("kept"), [self.cited_frame],
                         "the tombstone does not name the picture it kept")

    def test_a_remnant_is_not_released_again(self):
        self._cite({self.cited_frame})
        self._pass(free_gb=500.0)
        p = RR.plan(self.w.hist)
        self.assertIn(self.cited_reel, p.get("remnants") or [], "the evidence remnant is not listed as one")
        self.assertNotIn(self.cited_reel, [c.get("reel") for c in p.get("candidates") or []],
                         "the evidence remnant is planned for release again - the drain would never read as done")

    def test_an_unreadable_evidence_ledger_releases_nothing(self):
        self._cite(None)
        r, _st = self._pass(free_gb=500.0)
        # None = the pass refused outright, which is also a release of nothing; the disk is the verdict
        self.assertEqual((r or {}).get("removed") or [], [], "reels were deleted while which pictures are cited was UNKNOWN")
        for nm in self.old:
            self.assertIn(nm, self.w.on_disk())

    # ── the second eye on v3521, three findings, each reproduced before it was fixed ──

    def _apply(self, p):
        """apply_plan on a plan already made, the frame.release lock open exactly as _pass opens it"""
        def _may(lock):
            return (True, "fixture: the frame.release lock is open") if lock == "frame.release" else _REAL_MAY(lock)
        with mock.patch("time.time", self.clock), mock.patch.object(SA, "may", _may):
            return RR.apply_plan(p, True)

    def test_a_partial_witness_index_releases_nothing(self):
        """`ok` False = a witness STORE would not parse, so `frames` is partial: a picture named only in that store
        read as "not evidence" and went. A partial index holds every reel, exactly as an unreadable cited set does."""
        def _wi(root=None, _real=self.real):
            out = dict(_real(root))
            out["cited"] = set()
            out["ok"] = False
            out["perStore"] = dict(out.get("perStore") or {}, **{"vault_accum_rows.json": None})
            return out
        # planned on a WHOLE index (so the plan releases), applied after a store stopped parsing - the plan
        # already holds a partial index itself, so this is the deleter's own guard, at the moment it deletes
        self._cite(set())
        with mock.patch("time.time", self.clock):
            p = RR.plan(self.w.hist)
        self.assertTrue(p.get("candidates"), "PREMISE: the whole index released nothing to hold")
        self.FA.witness_index = _wi
        pre = dict((nm, sorted(_fx_tmp.list_own(os.path.join(self.w.hist, nm)))) for nm in self.old)
        r = self._apply(p)
        self.assertEqual(r.get("removed") or [], [], "reels were deleted on a PARTIAL evidence index: %r" % r)
        for nm in self.old:
            self.assertEqual(sorted(_fx_tmp.list_own(os.path.join(self.w.hist, nm))), pre[nm], "a frame left %s" % nm)
        self.assertTrue(any("PARTLY known" in (f.get("why") or "") for f in r.get("failed") or []),
                        "the hold does not say why: %r" % r.get("failed"))

    def test_a_half_trimmed_remnant_is_planned_again(self):
        """The tombstone goes down BEFORE the delete. A trim that failed halfway left a `kept` row over a reel still
        holding its other frames, and plan() exempted it forever. Only a reel holding nothing but its kept pictures
        is a finished remnant."""
        self._cite({self.cited_frame})
        self._pass(free_gb=500.0)
        d = os.path.join(self.w.hist, self.cited_reel)
        self.assertIn(self.cited_reel, RR.plan(self.w.hist).get("remnants") or [], "PREMISE: no remnant was made")
        with open(os.path.join(d, "left_behind.jpg"), "wb") as fh:     # what a failed trim leaves
            fh.write(b"x" * 2048)
        p = RR.plan(self.w.hist)
        self.assertNotIn(self.cited_reel, p.get("remnants") or [],
                         "a half-trimmed reel still reads as a finished remnant - its leftover frames stay forever")

    def test_a_remnant_the_console_wrote_back_into_stays_a_remnant(self):
        """REG-2728 (#158) - the KAI closer met the remnant with no index and no report, rebuilt the index from the kept
        pictures, closed it (paid re-reads) and wrote a thumbnail; the next pass saw more than the kept pictures, planned
        it and trimmed them away. On his Mac: 12 reels, 82 rounds, 1,258 tombstone rows. What the console derives from
        the frames is not footage."""
        self._cite({self.cited_frame})
        self._pass(free_gb=500.0)
        d = os.path.join(self.w.hist, self.cited_reel)
        self.assertIn(self.cited_reel, RR.plan(self.w.hist, _fresh=True).get("remnants") or [], "PREMISE: no remnant")
        for nm in ("index.json", "kai_report.json", ".stash_eye_tab.jpg"):
            with open(os.path.join(d, nm), "w") as fh:
                fh.write("{}")
        p = RR.plan(self.w.hist, _fresh=True)
        self.assertIn(self.cited_reel, p.get("remnants") or [],
                      "the closer's own index and report turned a finished remnant back into a reel")
        self.assertNotIn(self.cited_reel, [c.get("reel") for c in p.get("candidates") or []],
                         "the remnant is planned for release again - the trim-and-reclose loop (REG-2728)")
        self.assertEqual(RR.remnant_reels(self.w.hist), {self.cited_reel}, "the planner and remnant_reels disagree")

    def test_freed_is_what_left_the_disk(self):
        """A trimmed reel was credited with its whole planned size. Freed = its size minus the pictures it kept."""
        d = os.path.join(self.w.hist, self.cited_reel)
        with open(os.path.join(d, self.cited_frame), "wb") as fh:          # a big kept picture, so the gap shows
            fh.write(b"x" * (3 * 1024 * 1024))
        self._cite({self.cited_frame})
        with mock.patch("time.time", self.clock):
            p = RR.plan(self.w.hist)
        planned = dict((c["reel"], float(c.get("mb") or 0)) for c in p.get("candidates") or [])
        self.assertIn(self.cited_reel, planned, "PREMISE: the cited reel is not a candidate")
        r = self._apply(p)
        want = sum(planned[nm] for nm in r.get("removed") or []) - 3.0
        self.assertEqual(r.get("trimmed"), 1, "the trimmed reel is not counted as trimmed: %r" % r)
        self.assertAlmostEqual(r.get("freedMb"), round(max(0.0, want), 1), delta=0.11,
                               msg="freed counts the kept picture as freed: %r vs %.1f" % (r.get("freedMb"), want))


class PressureNeverFreesLess(_Base):
    """★ Claim 2 — the band where `need_mb` used to cap the pass."""

    def setUp(self):
        _Base.setUp(self)
        self.setUpClock()
        self.w = _World(self, n_finished=RR.KEEP_RECENT + 4)
        self.old = self.w.names[:4]

    def _check_all_four(self, r, st, where):
        self.assertEqual(sorted(r.get("removed") or []), sorted(self.old),
                         "%s the pass released %d of the 4 finished reels — disk pressure freed LESS "
                         "than a roomy disk would (the target-met cap is back)"
                         % (where, len(r.get("removed") or [])))
        for nm in self.w.names[-RR.KEEP_RECENT:]:
            self.assertIn(nm, self.w.on_disk(), "pressure reached into the newest reels")

    def test_inside_the_headroom_band_every_finished_reel_goes(self):
        self._bind(self.w)
        free = CA.ON_AIR_FLOOR_GB + CA.PRUNE_HEADROOM_GB - 0.0005      # 0.5 MB short
        r, st = self._pass(free_gb=free)
        self.assertGreater(st.get("needMb") or 0, 0, "premise: the disk is short of its headroom")
        self._check_all_four(r, st, "inside the headroom band")

    def test_below_the_floor_every_finished_reel_goes(self):
        self._bind(self.w, headroom=0.0)
        free = CA.ON_AIR_FLOOR_GB - 0.0005                             # below the floor, 0.5 MB short
        self.assertLess(free, CA.ON_AIR_FLOOR_GB, "premise: below the floor")
        r, st = self._pass(free_gb=free)
        # ⚠ freeGb is published rounded to 0.1 (7.9995 -> 8.0), so the premise is asserted on the
        # pinned number above and on needMb here, never on the rounded display figure.
        self.assertGreater(st.get("needMb") or 0, 0, "premise: the pass measured itself short")
        # 2026-09-29 — BELOW THE RECORDING FLOOR THE WINDOW NARROWS TO THE OLD EIGHT (his sixteen must never be
        # what stops the next reel filming - reel_retention.keep_recent_for), so every finished reel older than
        # the newest eight goes: MORE than a roomy disk frees, which is the direction this class exists to pin.
        keep = RR.KEEP_RECENT_UNDER_PRESSURE
        want = self.w.names[:-keep]
        self.assertGreater(len(want), len(self.old), "premise: the narrowed window reaches past the four old reels")
        self.assertEqual(sorted(r.get("removed") or []), sorted(want),
                         "below the floor the pass kept more than the newest %d finished reels: %r" % (keep, r))
        for nm in self.w.names[-keep:]:
            self.assertIn(nm, self.w.on_disk(), "pressure reached into the newest %d reels" % keep)


class TheHeartSeesTheDrainStop(_Base):
    """★ Claim 4 — on/worked/lastTs/owed, STOPPED after the bar, and the doctor reads the wire."""

    def setUp(self):
        _Base.setUp(self)
        self.setUpClock()
        self.w = _World(self, n_finished=RR.KEEP_RECENT + 2)
        self._bind(self.w)

    def test_a_refused_drain_is_STOPPED_after_the_bar_and_a_relaunch_cannot_reset_it(self):
        bar = RR.DRAIN_STOPPED_AFTER_PASSES
        before = self.w.on_disk()
        states = []
        for i in range(bar):
            if i == bar - 1:
                # a RELAUNCH: the process forgets everything it held; the series does not
                CA._RETENTION["drain"] = {"state": "UNKNOWN", "why": "fresh process"}
            r, st = self._pass(free_gb=500.0, world_ok=False)
            states.append((st["drain"]["state"], st["drain"]["passesOwed"]))
        self.assertEqual(self.w.on_disk(), before, "a refused deleter deleted footage")
        self.assertEqual([s for s, _ in states[:-1]], ["OWED"] * (bar - 1),
                         "the drain called itself stopped before the bar: %r" % states)
        self.assertEqual(states[-1], ("STOPPED", bar),
                         "%d passes carried the same reels and released nothing, and the drain "
                         "did not say STOPPED: %r" % (bar, states))
        dr = st["drain"]
        self.assertEqual(dr["owed"], 2)
        self.assertIn("the board world was never confirmed", dr.get("why") or "",
                      "the stopped drain does not carry the refusal that stopped it")
        verdict, why = self._doctor(st)
        self.assertEqual(verdict, "missing", "the doctor row read a stopped drain as %r: %s"
                         % (verdict, why))
        # and once the world confirms, the next pass drains and the row clears
        r, st = self._pass(free_gb=500.0, world_ok=True)
        self.assertEqual(len(r.get("removed") or []), 2)
        self.assertEqual(st["drain"]["state"], "CLEAR")
        self.assertEqual(self._doctor(st)[0], "ok")

    def test_a_busy_drain_that_releases_every_pass_never_cries_wolf(self):
        bar = RR.DRAIN_STOPPED_AFTER_PASSES
        seen = []
        for i in range(bar + 2):
            r, st = self._pass(free_gb=500.0)
            seen.append(st["drain"]["state"])
            self.assertEqual(self._doctor(st)[0], "ok", "a working drain went red on pass %d" % i)
            self.w.add(sealed=True)                  # a new reel finishes; the 9th-newest is owed
            self.w.write_ledgers()
        owed = [x.get("owed") for x in self.w.series() if "owed" in x]
        # REG-1893 - an empty disk series makes the premise below vacuous: one owed row per pass first.
        self.assertGreaterEqual(len(owed), bar + 2, "the disk series recorded %d owed row(s) for %d passes, so "
                                                    "'every pass started with reels owed' is unsupported: %r"
                                % (len(owed), bar + 2, owed))
        self.assertTrue(all(o and o > 0 for o in owed),
                        "premise: every pass started with reels owed: %r" % owed)
        self.assertNotIn("STOPPED", seen, "a drain releasing every pass was called STOPPED: %r" % seen)

    def test_on_air_and_a_sweep_reading_are_DEFERRED_never_STOPPED(self):
        bar = RR.DRAIN_STOPPED_AFTER_PASSES
        reasons = (
            "the console is ON AIR (live) — you are filming",
            "a chronicle sweep is reading",
            "a vault sweep is reading",
        )
        before = self.w.on_disk()
        states = []
        for i in range(bar + 1):
            r, st = self._pass(free_gb=500.0, in_flight=reasons[i % len(reasons)])
            states.append(st["drain"]["state"])
            self.assertNotIn("STOPPED", st["drain"].get("why") or "", st["drain"])
            self.assertEqual(self._doctor(st)[0], "ok",
                             "a deferred drain went red on pass %d: %s" % (i, st["drain"]))
            self.assertFalse(r.get("removed") if isinstance(r, dict) else r,
                             "a deferred drain deleted footage")
        self.assertEqual(states, ["DEFERRED"] * (bar + 1), states)
        self.assertEqual(self.w.on_disk(), before, "a deferred drain deleted footage")
        held = [x.get("held") for x in self.w.series() if x.get("held")]
        self.assertGreaterEqual(len(held), bar + 1, "the passes were not marked held: %r" % held)
        r, st = self._pass(free_gb=500.0)
        self.assertEqual(len((r or {}).get("removed") or []), 2,
                         "the first quiet pass did not drain what the hold had left owed")
        self.assertEqual(st["drain"]["state"], "CLEAR", st["drain"])
        self.assertEqual(self._doctor(st)[0], "ok")

    def test_an_unreadable_sweep_is_not_a_deferral(self):
        self.assertIsNone(CA._retention_deferred(
            "could not tell whether a chronicle sweep is reading"))
        self.assertIsNotNone(CA._retention_deferred("a chronicle sweep is reading"))
        self.assertIsNotNone(CA._retention_deferred(
            "the console is ON AIR (live) — you are filming"))

    def test_a_refusing_lock_is_said_as_a_refusal_not_as_a_prune(self):
        r, st = self._pass(free_gb=500.0, frame_release=False)
        self.assertFalse(r.get("removed"), "a locked deleter removed reels")
        self.assertIn("refused", st.get("say") or "", "a refused deleter is not said as a refusal")
        self.assertNotIn("freed", st.get("say") or "",
                         "a deleter that never ran is described as having freed space: %r"
                         % st.get("say"))
        self.assertEqual(st["drain"]["state"], "OWED")
        self.assertIn("LOCKED", st["drain"].get("stopWhy") or "")

    def test_UNKNOWN_when_the_plan_cannot_run(self):
        # a footage path that exists and cannot be listed: plan() answers ok False
        bad = os.path.join(self.w.root, "not_a_dir")
        with io.open(bad, "w") as fh:
            fh.write("x")
        os.environ["TV_HIST"] = bad
        r, st = self._pass(free_gb=500.0)
        self.assertEqual(st["drain"]["state"], "UNKNOWN", st["drain"])
        self.assertIsNone(st["drain"]["owed"], "an unrunnable plan published a confident owed")
        self.assertEqual(self._doctor(st)[0], "unknown")

    def test_UNKNOWN_when_a_ledger_will_not_parse(self):
        io.open(os.path.join(self.w.root, "vault_swept.json"), "w").write("{ not json")
        r, st = self._pass(free_gb=500.0)
        self.assertEqual(self.w.on_disk(), sorted(self.w.names), "an unreadable ledger lost footage")
        self.assertEqual(st["drain"]["state"], "UNKNOWN",
                         "an unreadable ledger read as a %r drain — 'cannot judge' is not "
                         "'nothing owed'" % st["drain"]["state"])
        self.assertIsNone(st["drain"]["owed"])

    def test_a_console_that_never_filmed_is_UNMEASURED_not_stopped(self):
        os.environ["TV_HIST"] = os.path.join(self.w.root, "never_made")
        r, st = self._pass(free_gb=500.0)
        self.assertEqual(self._doctor(st)[0], "unmeasured", st["drain"])

    def test_a_STALE_drain_is_UNKNOWN_never_healthy(self):
        """A reading past its own cadence cannot certify the drain (stale-reading §4). It is not
        MISSING either: after his Mac sleeps, a healthy loop's `at` is hours old until its next
        pass, and whether the thread is alive is lane_liveness's row."""
        r, st = self._pass(free_gb=500.0)
        self.assertEqual(st["drain"]["state"], "CLEAR", "premise: a fresh, healthy drain")
        st = dict(st, drain=dict(st["drain"]))
        st["drain"]["at"] = int(self.clock() * 1000) - int(
            (RR.DRAIN_STOPPED_AFTER_PASSES + 1) * float(st["drain"]["everyS"]) * 1000)
        self.assertEqual(self._doctor(st)[0], "unknown",
                         "a drain whose newest reading is %d periods old was certified"
                         % (RR.DRAIN_STOPPED_AFTER_PASSES + 1))


class TheDrainArithmetic(unittest.TestCase):
    """The pure half — reel_retention.drain_state over hand-built series rows."""

    def _st(self, rows, **kw):
        # #84 (REG-1517) — a MEASURED-EMPTY river beside the mouth; a mouth read with no river is
        # UNKNOWN, never CLEAR, and test_the_drain_names_what_is_blocked_upstream drives that half
        kw.setdefault("upstream", RR.blocked_upstream({}, {"ok": True, "candidates": [], "kept": []},
                                                      now_ms=BASE_MS))
        return RR.drain_state(rows, beat={"works": 7, "lastWorkAt": BASE_MS}, now_ms=BASE_MS, **kw)

    def test_the_bar_is_exactly_the_constant(self):
        bar = RR.DRAIN_STOPPED_AFTER_PASSES
        rows = [{"owed": 2}] * (bar - 1)
        self.assertEqual(self._st(rows)["state"], "OWED")
        self.assertEqual(self._st(rows + [{"owed": 2}])["state"], "STOPPED")

    def test_a_disarmed_or_unread_deleter_is_never_a_stall(self):
        """The second eye on v3520: on=0 is disarmed (DORMANT), on=None is unread (UNKNOWN) - never STOPPED."""
        rows = [{"owed": 2}] * (RR.DRAIN_STOPPED_AFTER_PASSES + 2)
        self.assertEqual(self._st(rows, on=0)["state"], "DORMANT")
        st = self._st(rows, on=None)
        self.assertNotEqual(st["state"], "STOPPED", "an unread armed state was reported as a stalled drain")
        self.assertIn("could not be read", st["why"])

    def test_a_pass_that_released_what_it_owed_breaks_the_streak(self):
        bar = RR.DRAIN_STOPPED_AFTER_PASSES
        rows = []
        for _ in range(bar + 1):
            rows += [{"owed": 1}, {"released": 1}]
        st = self._st(rows)
        self.assertEqual(st["state"], "CLEAR")
        self.assertEqual(st["owed"], 0)

    def test_a_partial_release_still_carries_the_rest(self):
        bar = RR.DRAIN_STOPPED_AFTER_PASSES
        rows = [{"owed": 3}, {"released": 2}] + [{"owed": 1}] * (bar - 1)
        self.assertEqual(self._st(rows)["state"], "STOPPED")

    def test_rows_from_before_the_contract_end_the_walk(self):
        bar = RR.DRAIN_STOPPED_AFTER_PASSES
        rows = [{"owed": 2}] * bar + [{"freeGb": 10.0}] + [{"owed": 2}]
        st = self._st(rows)
        self.assertEqual((st["state"], st["passesOwed"]), ("OWED", 1))

    def test_unknown_is_never_zero(self):
        self.assertEqual(self._st([])["state"], "UNKNOWN")
        self.assertEqual(self._st(None)["state"], "UNKNOWN")
        st = self._st([{"owed": None}])
        self.assertEqual(st["state"], "UNKNOWN")
        self.assertIsNone(st["owed"])
        self.assertEqual(self._st([{"owed": 2}, {"released": "many"}])["state"], "UNKNOWN")
        self.assertEqual(self._st([{"owed": True}])["state"], "UNKNOWN", "True is not a count")

    def test_a_disarmed_deleter_is_DORMANT_not_stopped(self):
        rows = [{"owed": 2}] * (RR.DRAIN_STOPPED_AFTER_PASSES + 1)
        self.assertEqual(self._st(rows, on=False)["state"], "DORMANT")

    def test_a_held_pass_is_DEFERRED_and_does_not_extend_the_streak(self):
        bar = RR.DRAIN_STOPPED_AFTER_PASSES
        rows = []
        for _ in range(bar + 2):
            rows.append({"owed": 2})
            rows.append({"held": "the console is ON AIR (live) — you are filming"})
        st = self._st(rows)
        self.assertEqual(st["state"], "DEFERRED", st)
        self.assertEqual(st["owed"], 2)
        self.assertEqual(st["passesOwed"], 0, "a deferred pass extended the stall streak")
        self.assertNotIn("STOPPED", st.get("why") or "")
        self.assertEqual(self._st([{"owed": 2}] * bar)["state"], "STOPPED")

    def test_worked_and_lastTs_are_quoted_from_the_deleters_record(self):
        st = self._st([{"owed": 0}])
        self.assertEqual((st["worked"], st["lastTs"]), (7, BASE_MS))
        st = RR.drain_state([{"owed": 0}], beat={"why": "unreadable"}, now_ms=BASE_MS)
        self.assertIsNone(st["worked"], "an unreadable deleter record read as a count")

    def test_drain_owed_counts_what_a_target_held_back(self):
        p = {"ok": True, "unreadable": [], "candidates": [{"reel": "a"}],
             "kept": [{"reel": "b", "tag": "target-met"}, {"reel": "c", "tag": "recent"}]}
        self.assertEqual(RR.drain_owed(p), 2)
        self.assertIsNone(RR.drain_owed(dict(p, unreadable=["vault_swept.json"])))
        self.assertIsNone(RR.drain_owed(dict(p, ok=False)))


class TheDrainRunsBesideTheShadowReader(_Base):
    """★★ REG-1838 — A SHADOW REEL ALONE DOES NOT HOLD THE DRAIN, AND IT NEVER TOUCHES WHAT IS BEING FILMED.

    His 2026-10-04 ruling keeps the shadow reader on, so a PC with the game open is ON AIR every pass. MEASURED on
    his ALT: 87 of 96 passes on 10-05 deferred "through the SHADOW reader", 416 releasable, none ever released.
    The REAL retention_may_act -> nothing_in_flight decides here (only its inputs are stated), and the SHIPPED
    _retention_once deletes. The rolling reel is what the agent writes: loose f_<ms>.jpg in the hist root."""

    def setUp(self):
        _Base.setUp(self)
        self.setUpClock()
        self._make(2)

    def _make(self, n_old):
        """KEEP_RECENT + n_old finished reels, all filmed long ago, and a shadow reel rolling beside them."""
        self.w = _World(self, n_finished=RR.KEEP_RECENT + n_old)
        self._bind(self.w)
        self.old = self.w.names[:n_old]
        self.newest = self.w.names[n_old:]
        old_s = BASE_MS / 1000.0
        for nm in self.w.names:                    # every sealed reel finished filming long ago
            d = os.path.join(self.w.hist, nm)
            for f in _fx_tmp.list_own(d):
                os.utime(os.path.join(d, f), (old_s, old_s))
            os.utime(d, (old_s, old_s))
        self.live = []
        for k in range(3):                         # the shadow reel, rolling: loose frames, no folder yet
            fp = os.path.join(self.w.hist, "f_%d.jpg" % int(self.clock.t * 1000 + k))
            with open(fp, "wb") as fh:
                fh.write(b"live frame %d" % k)
            self.live.append(fp)

    def _beside(self, door, vault_running=False):
        def _may(lock):
            if lock == "frame.release":
                return True, "fixture: the frame.release lock is open"
            return _REAL_MAY(lock)
        with mock.patch("time.time", self.clock), \
                mock.patch("shutil.disk_usage", return_value=_usage(500.0)), \
                mock.patch.object(CA, "board_identity_drift", lambda: {"state": "ok", "why": "fixture"}), \
                mock.patch.object(CA, "_agent_mode", "live"), \
                mock.patch.object(CA, "_agent_alive", lambda: True), \
                mock.patch.object(CA, "_rolling_reel", lambda: {"door": door, "since": None, "why": ""}), \
                mock.patch.object(CA, "_CHRON_JOB", {"running": False}), \
                mock.patch.object(CA, "_VAULT_JOB", {"running": vault_running}), \
                mock.patch.object(CA, "mini_state", lambda: {"running": False}), \
                mock.patch.object(SA, "may", _may):
            r = CA._retention_once()
            st = CA.retention_state()
        return r, st

    def _live_intact(self):
        for k, fp in enumerate(self.live):
            self.assertTrue(os.path.isfile(fp), "the rolling reel lost a frame: %s" % fp)
            with open(fp, "rb") as fh:
                self.assertEqual(fh.read(), b"live frame %d" % k, "a rolling frame was rewritten")

    def test_a_shadow_reel_does_not_hold_the_drain(self):
        r, st = self._beside("shadow")
        r = r if isinstance(r, dict) else {}
        self.assertEqual(sorted(r.get("removed") or []), sorted(self.old),
                         "beside a rolling shadow reel the drain released %r, not the two reels older than the "
                         "newest %d" % (r.get("removed"), RR.KEEP_RECENT))
        left = self.w.on_disk()
        for nm in self.newest:
            self.assertIn(nm, left, "one of the newest %d was deleted beside the shadow" % RR.KEEP_RECENT)
        self._live_intact()
        self.assertEqual([t.get("reel") for t in self.w.tombstones()], self.old)
        self.assertNotEqual(st["drain"]["state"], "DEFERRED", st["drain"])

    def test_a_reel_still_receiving_frames_is_never_released_beside_the_shadow(self):
        d = os.path.join(self.w.hist, self.old[0])
        now_s = self.clock.t
        for f in _fx_tmp.list_own(d):
            os.utime(os.path.join(d, f), (now_s, now_s))
        r, st = self._beside("shadow")
        r = r if isinstance(r, dict) else {}
        self.assertEqual(r.get("removed"), [self.old[1]], "beside the shadow the drain released %r" % (r,))
        self.assertIn(self.old[0], self.w.on_disk(), "a reel still receiving frames was deleted")
        self.assertEqual(r.get("heldFilming"), [self.old[0]], r)
        self.assertIn("still receiving frames", st.get("say") or "")
        self._live_intact()

    def test_beside_the_shadow_at_most_the_cap_go_per_pass_oldest_first(self):
        """The ALT's first drain ever would release 416 reels in one pass while he plays. Beside the shadow a pass
        releases RETENTION_BESIDE_SHADOW_MAX, oldest first in the plan's order, and names the rest for the next."""
        cap = CA.RETENTION_BESIDE_SHADOW_MAX
        self.assertGreaterEqual(cap, 1)
        self._make(cap + 5)
        r, st = self._beside("shadow")
        r = r if isinstance(r, dict) else {}
        self.assertEqual(r.get("removed"), self.old[:cap],
                         "beside the shadow a pass released %d reel(s), not the oldest %d"
                         % (len(r.get("removed") or []), cap))
        self.assertEqual(r.get("heldNextPass"), self.old[cap:], r.get("heldNextPass"))
        self.assertIn("5 more next pass", st.get("say") or "", st.get("say"))
        left = self.w.on_disk()
        for nm in self.old[cap:] + self.newest:
            self.assertIn(nm, left)
        self._live_intact()
        r2, _ = self._beside("shadow")
        self.assertEqual((r2 or {}).get("removed"), self.old[cap:], "the next pass did not take the rest")

    def test_off_air_the_pass_is_not_capped(self):
        cap = CA.RETENTION_BESIDE_SHADOW_MAX
        self._make(cap + 5)
        r, st = self._pass(free_gb=500.0)
        self.assertEqual(sorted((r or {}).get("removed") or []), sorted(self.old),
                         "with nothing in flight the pass was capped")
        self.assertNotIn("heldNextPass", r or {})

    def test_his_session_an_unknown_door_and_a_sweep_still_hold_it(self):
        before = self.w.on_disk()
        for door, vault in (("onair", False), ("mini", False), (None, False), ("shadow", True)):
            r, st = self._beside(door, vault_running=vault)
            self.assertFalse((r or {}).get("removed") if isinstance(r, dict) else r,
                             "door %r (vault sweep %s) let the drain delete" % (door, vault))
            self.assertEqual(self.w.on_disk(), before)
            self.assertEqual(st["drain"]["state"], "DEFERRED", (door, vault, st["drain"]))
        self._live_intact()


class TheShadowCapNeverWidens(unittest.TestCase):
    """REG-1926 - `cands[:cap]` read a negative cap from the end, so a smaller cap released MORE reels."""

    def test_a_cap_below_zero_releases_nothing(self):
        p = {"candidates": [{"reel": "reel_s_%d_a" % i} for i in range(1, 6)]}
        names = [c["reel"] for c in p["candidates"]]
        for cap in (0, -1, -4, -50):
            go, later = CA._cap_beside_shadow(p, cap)
            self.assertEqual(go["candidates"], [], "cap %d released %r" % (cap, go["candidates"]))
            self.assertEqual(later, names, "cap %d did not leave every reel for the next pass" % cap)
        go, later = CA._cap_beside_shadow(p, 2)
        self.assertEqual([c["reel"] for c in go["candidates"]], names[:2], "the cap is no longer oldest first")
        self.assertEqual(later, names[2:])
        self.assertEqual(len(p["candidates"]), 5, "the shared plan was edited")
        saved = CA.RETENTION_BESIDE_SHADOW_MAX
        try:
            CA.RETENTION_BESIDE_SHADOW_MAX = -1          # the default path reads the constant the same way
            self.assertEqual(CA._cap_beside_shadow(p)[0]["candidates"], [])
        finally:
            CA.RETENTION_BESIDE_SHADOW_MAX = saved


def tearDownModule():
    for k, v in _SAVED_ENV.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    shutil.rmtree(_BOOT, ignore_errors=True)


class TheDeleterTakesOnlyAReelName(AVaultPictureHoldsItsReel):
    """REG-1918 - apply_plan rmtree's os.path.join(hist, reel). A candidate whose reel is "" IS the hist root - every reel
    he has - and ".." or a separator walks out of it; a symlinked reel_* that points outside the shelf is not his shelf.
    plan() never produces one; the deleter refuses them anyway, and a real candidate beside them still goes."""

    def test_a_malformed_name_deletes_nothing_and_a_real_one_still_goes(self):
        import tempfile, shutil
        outside = tempfile.mkdtemp(prefix="reel_outside_")
        self.addCleanup(shutil.rmtree, outside, True)
        with open(os.path.join(outside, "keep.jpg"), "wb") as fh:
            fh.write(b"x")
        os.symlink(outside, os.path.join(self.w.hist, "reel_link_out"))
        self._cite(set())
        p = RR.plan(self.w.hist)
        real = [c for c in (p.get("candidates") or []) if c.get("reel") == self.old[0]]
        self.assertTrue(real, "premise: the oldest finished reel is a candidate")
        bad = [{"reel": "", "mb": 1.0}, {"reel": "..", "mb": 1.0}, {"reel": "reel_x/../..", "mb": 1.0},
               {"reel": "reel_link_out", "mb": 1.0}, {"mb": 1.0}]
        before = sorted(self.w.on_disk())
        r = self._apply(dict(p, candidates=bad + real))
        self.assertTrue(os.path.isdir(self.w.hist), "THE SHELF ITSELF WAS DELETED (REG-1918)")
        self.assertTrue(os.path.isfile(os.path.join(outside, "keep.jpg")), "a symlinked reel deleted outside the shelf")
        self.assertEqual(sorted(r.get("removed") or []), [self.old[0]], "the real candidate did not go, or another did: %r" % r)
        refused = [f for f in (r.get("failed") or []) if "REFUSED" in str(f.get("why"))]
        self.assertEqual(len(refused), 5, "every malformed candidate must be refused by name: %r" % r.get("failed"))
        self.assertEqual(sorted(set(before) - set(self.w.on_disk())), [self.old[0]])


class TheKaiCloserLeavesARemnantAlone(unittest.TestCase):
    """REG-2728 (#158) - the closer asks the planner's own remnant answer before it rebuilds an index or closes a reel.
    The loop is a thread that never returns, so its source is read - code only, comments stripped."""

    def test_the_closer_skips_a_remnant_before_it_touches_the_index(self):
        import inspect
        code = "\n".join(l.split("#", 1)[0].rstrip() for l in inspect.getsource(CA._kai_closer_loop).split("\n"))
        ask = "                _remnants = _rr_rem.remnant_reels(hist)"
        skip = "                if d in _remnants:\n                    continue"
        ens = "                if not _reel_ensure_index(os.path.join(hist, d))[0]:"
        for need in (ask, skip, ens):
            self.assertEqual(code.count(need), 1, "the closer's remnant step is not where this law reads it: %r" % need)
        self.assertLess(code.index(ask), code.index(skip))
        self.assertLess(code.index(skip), code.index(ens), "the closer rebuilds a remnant's index before skipping it")


RED_PROOF = [
    {
        "why": "REG-1926 - a negative beside-shadow cap is read from the end again, so a smaller cap deletes more reels",
        "file": "control_app.py",
        "find": "    cap = max(0, RETENTION_BESIDE_SHADOW_MAX if cap is None else int(cap))\n",
        "replace": "    cap = RETENTION_BESIDE_SHADOW_MAX if cap is None else int(cap)\n",
        "matches": 1,
    },
    {
        "why": "REG-1918 - the deleter takes any name again: a candidate whose reel is '' rmtree's the whole shelf",
        "file": "tv/reel_retention.py",
        "find": "        if not _is_reel_dir_name(_rn) or not _is_child_dir(p.get(\"hist\"), _rn):\n",
        "replace": "        if False:\n",
        "matches": 1,
    },
    {
        "why": "REG-1838 - a rolling shadow reel holds the drain again, so the ALT's 416 releasable reels wait for ever",
        "file": "control_app.py",
        "find": "    if ok or not _kinds or any(k.get(\"kind\") != \"shadow\" for k in _kinds):\n        return ok, why\n",
        "replace": "    if True:\n        return ok, why\n",
        "matches": 1,
    },
    {
        "why": "REG-1838 - beside the shadow every eligible reel goes in one pass - the ALT's 416 at once while he plays",
        "file": "control_app.py",
        "find": "        _go, _later = _cap_beside_shadow(_go)\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "REG-1838 - beside the shadow a reel still receiving frames is released",
        "file": "control_app.py",
        "find": "        _go, _filming = _drop_reels_still_filming(p)\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "REG-1838 - every door reads as the shadow, so his own session and an unknown door let the deleter act",
        "file": "control_app.py",
        "find": "    if ok or not _kinds or any(k.get(\"kind\") != \"shadow\" for k in _kinds):\n        return ok, why\n",
        "replace": "    if ok or not _kinds:\n        return ok, why\n",
        "matches": 1,
    },
    {
        "why": "the second eye on v3521 - apply_plan deletes on a PARTIAL witness index (a store would not parse)",
        "file": "reel_retention.py",
        "find": "        elif not _wit.get(\"ok\", False) or _wit.get(\"frames\") is None:\n",
        "replace": "        elif _wit.get(\"frames\") is None:\n",
        "matches": 1,
    },
    {
        "why": "the second eye on v3521 - a half-trimmed reel with a `kept` row is a finished remnant forever",
        "file": "reel_retention.py",
        "find": "        if _left <= k:\n",
        "replace": "        if True:\n",
        "matches": 1,
    },
    {
        "why": "REG-2728 - the console's own index and report make a finished remnant a reel again (the trim-reclose loop)",
        "file": "reel_retention.py",
        "find": "            _left = set(f for f in os.listdir(os.path.join(hist, r)) if not f.startswith(\".\") and f not in REMNANT_DERIVED)\n",
        "replace": "            _left = set(os.listdir(os.path.join(hist, r)))\n",
        "matches": 1,
    },
    {
        "why": "REG-2728 - the KAI closer closes an evidence remnant again (paid re-reads, then the next trim)",
        "file": "tv/control_app.py",
        "find": "                if d in _remnants:\n                    continue\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "the second eye on v3521 - a trimmed reel is credited with its whole planned size as freed",
        "file": "reel_retention.py",
        "find": "        freed_by[c[\"reel\"]] = max(0.0, float(c.get(\"mb\") or 0) - _kept_mb)\n",
        "replace": "        freed_by[c[\"reel\"]] = float(c.get(\"mb\") or 0)\n",
        "matches": 1,
    },
    {
        "why": "the second eye on v3520 - an unread armed state reads as a stalled drain again",
        "file": "reel_retention.py",
        "find": "    if on is None and not _defer:\n",
        "replace": "    if False:\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 §26 - a released reel takes the picture a vault item stands on again (rmtree whole)",
        "file": "reel_retention.py",
        "find": "            kept = sorted(f for f in os.listdir(path) if f in _evid)\n",
        "replace": "            kept = []\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 §26 - an unreadable vault evidence ledger no longer stops the drain",
        "file": "reel_retention.py",
        "find": "        if _evid is None:\n            failed.append(",
        "replace": "        if False:\n            failed.append(",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - an evidence remnant is planned again every pass, so the drain never reads as done",
        "file": "reel_retention.py",
        "find": "        reels = [r for r in reels if r not in _remnants]\n",
        "replace": "        reels = list(reels)\n",
        "matches": 1,
    },
    {
        "why": "restoring the need_mb gate makes disk pressure free LESS than a roomy disk — "
               "every finished reel past the first is held target-met",
        "file": "tv/control_app.py",
        "find": "    p = _rr.plan(hist, free_mb=None, keep_recent=_keep)\n",
        "replace": "    p = _rr.plan(hist, free_mb=(need_mb or None), keep_recent=_keep)\n",
        "matches": 1,
    },
    {
        "why": "releasing newest-first puts the oldest reels in the keep window and deletes the "
               "newest sessions",
        "file": "tv/reel_retention.py",
        "find": '        reels = sorted((d for d in os.listdir(hist) if d.startswith("reel_")), '
                'key=_reel_ts)\n',
        "replace": '        reels = sorted((d for d in os.listdir(hist) if d.startswith("reel_")), '
                   'key=_reel_ts, reverse=True)\n',
        "matches": 1,
    },
    {
        "why": "a reel the vault lane never sealed is released as if it had given up its information",
        "file": "tv/reel_retention.py",
        "find": "        elif ve is None and _vault_lane_owes(path) and not _proven_empty(reel):\n",
        "replace": "        elif False:\n",
        "matches": 1,
    },
    {
        "why": "a drain that forgets how many passes it carried the same reels never says STOPPED",
        "file": "tv/reel_retention.py",
        "find": "        streak += 1\n",
        "replace": "        streak = 1\n",
        "matches": 1,
    },
    {
        "why": "the doctor row reads a stopped drain as anything but MISSING",
        "file": "tv/console_doctor.py",
        "find": '    if state == "STOPPED":\n        return MISSING, str(dr.get("why")',
        "replace": '    if state == "NEVER":\n        return MISSING, str(dr.get("why")',
        "matches": 1,
    },
    {
        "why": "a plan that cannot judge (an unreadable ledger) is published as a clear drain",
        "file": "tv/reel_retention.py",
        "find": '    if not isinstance(p, dict) or not p.get("ok") or p.get("unreadable"):\n'
                '        return None\n',
        "replace": '    if not isinstance(p, dict) or not p.get("ok") or p.get("unreadable"):\n'
                   '        return 0\n',
        "matches": 1,
    },
    {
        "why": "a deleter whose lock refused is described as a completed prune that freed 0 MB",
        "file": "tv/control_app.py",
        "find": "    _refused = (isinstance(r, dict) and not _removed_now and not r.get(\"ok\")\n"
                "                and r.get(\"freedMb\") is None)\n",
        "replace": "    _refused = False\n",
        "matches": 1,
    },
    {
        "why": "a drain reading older than its own cadence certifies the shelf as draining",
        "file": "tv/console_doctor.py",
        "find": "        if _age_s > float(_every) * _after:\n",
        "replace": "        if False:\n",
        "matches": 1,
    },
    {
        "why": "a pass held because the console is ON AIR still lengthens the stall and is called STOPPED",
        "file": "tv/reel_retention.py",
        "find": "        if _held(ps):\n            break\n",
        "replace": "        if False and _held(ps):\n            break\n",
        "matches": 1,
    },
    {
        "why": "an ON AIR refusal is not marked held, so the drain calls a deferred pass STOPPED",
        "file": "tv/control_app.py",
        "find": "                                    held=_defer,\n",
        "replace": "                                    held=None,\n",
        "matches": 1,
    },
    {
        "why": "the doctor reads a deferred drain as anything but OK",
        "file": "tv/console_doctor.py",
        "find": '    if state in ("CLEAR", "OWED", "DORMANT", "DEFERRED"):\n',
        "replace": '    if state in ("CLEAR", "OWED", "DORMANT"):\n',
        "matches": 1,
    },
    {
        "why": "an unreadable sweep is treated as a calm deferral and can never be called stopped",
        "file": "tv/control_app.py",
        "find": "    if \"could not tell\" in s or \"UNKNOWN\" in s:\n        return None\n",
        "replace": "    if False:\n        return None\n",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
