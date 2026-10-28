# -*- coding: utf-8 -*-
"""THE BACKUP LANE MUST SURVIVE A LOSS — a drop is SEEN, the restore reads the backup BEFORE it,
the prune keeps that backup, and the doctor says so until the store is back.

Konyo: *"ledgers and backups and all correctly wired and joined and obivusly read blueprints to see
whats already archirtured"* / *"the heart too dont forget"*.

MEASURED 2026-09-27 on his real backup dir (shape only — this law never reads or writes it):

    ledger_2026-09-27_024127.json   setPieces 134   owned 223
    ledger_2026-09-27_033127.json   setPieces   0   owned   0      <- a vault reset
    every backup after              setPieces   0   owned   0

Three things that already existed each missed it, and every one was built correctly:
  · `ledger_restore.plan()` took hits[0] — the NEWEST backup — so the restore door would have put
    back NOTHING (the newest held 0 pieces);
  · the prune's episode guard reads `d2r_storeEmptied`, which the board writes only when the FOUND
    ledger comes up empty at load, so nothing opened an episode and the 02:41 file was protected
    only by luck (the prune had not reached it yet);
  · the doctor's `ledger entries` row diffs only the TWO NEWEST snapshots, so one snapshot after
    the drop it went clean with the pieces still gone.

WHAT THIS PINS, EACH DRIVEN (the shipped code runs; nothing here greps source):
  1. `ledger_restore.drops_between` — ONE definition of a drop (to 0, or by >= max(10, 25%)), and an
     UNKNOWN count is never a drop;
  2. the plan reads a dropped store from the last backup BEFORE the drop, says so per store, and
     goes back to the newest once the store recovers; the doors for the other stores read the SAME
     per-store source;
  3. a file HE NAMES wins; a traversal, a symlink out, an unrouted or another profile's file is
     refused — and the HTTP routes carry {"file": name} through;
  4. one REAL iteration of `_ledger_backup_loop` (pinned clock, stubbed board, real writer) opens a
     durable episode and the prune keeps its before-file past every age rule;
  5. the episode CLOSES when the store is back to >= where it fell from; a first look REPLAYS a drop
     that happened before the watcher existed; an unreadable record is set aside, never written
     over, and while it is unreadable the prune deletes NOTHING;
  6. THE HEART — the doctor row `ledger drop` names store/from/to/when and the door, is UNKNOWN when
     it cannot see, and watches the watcher (a newest backup it never judged is MISSING).

⚠ FIXTURES ONLY. TV_HIST points the record at a temp world before control_app is imported; the
backup dir is a temp dir; the board is a stub; the clock is pinned. [[feedback-fixtures-never-touch-live-data]]
[[heart-first]] [[the-unjoined-end]] [[unknown-stays-unknown]] [[copy-drift]]
"""
import io
import json
import os
import shutil
import sys
import tempfile
import threading
import time as _real_time
import unittest
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402  #171 — this run's scratch dirs leave with it
_fx_tmp.contain()

# ⚠ BEFORE control_app is imported: its module-level paths resolve through TV_HIST, and the drop
# record resolves through it at call time. A fixture world, never his.
_WORLD = tempfile.mkdtemp(prefix="backup_lane_world_")
os.environ["TV_HIST"] = _WORLD

try:
    from console_safe import enable
    enable()
except Exception:
    pass

import control_app as CA  # noqa: E402
import console_doctor as CD  # noqa: E402
import ledger_restore as LR  # noqa: E402

DAY = 24 * 3600.0
#: 2026-06-15 12:00:00 UTC — the same pinned mid-day the prune law uses, so day arithmetic is stable.
PINNED_NOW = 1781524800.0
ROUTE = {"id": "law-route-aaaa", "p": "main"}
OTHER = {"id": "someone-else", "p": "main"}
PIECES = ["Piece %03d" % i for i in range(134)]


class _Stop(BaseException):
    """Escapes the loop's `except Exception: pass` after exactly one iteration."""


class _Clock(object):
    """A pinned clock standing in for control_app's `time` module. sleep() lets the loop through
    ONCE, then stops it; everything not overridden is the real module."""

    def __init__(self, now, sleeps_allowed=1):
        self.now = float(now)
        self.sleeps = 0
        self.allowed = sleeps_allowed

    def time(self):
        return self.now

    def sleep(self, s):
        self.sleeps += 1
        if self.sleeps > self.allowed:
            raise _Stop()

    def strftime(self, fmt, t=None):
        return _real_time.strftime(fmt, _real_time.localtime(self.now) if t is None else t)

    def __getattr__(self, k):
        return getattr(_real_time, k)


def _board(pieces, owned, found=50, rw=0, gf=0, route=ROUTE):
    """What his board answers board_ownership with — the stub the REAL writer consumes."""
    sp = PIECES[:pieces]
    ow = ["Owned %03d" % i for i in range(owned)]
    # foundLog carries every set piece (toggleSetPiece writes the found ledger) and is untouched by
    # a vault reset — so it stays constant while setPieces/owned fall, exactly as measured.
    fl = ["Found %03d" % i for i in range(found)] + list(PIECES)
    return {"ok": True, "route": dict(route),
            "counts": {"foundLog": len(fl), "owned": len(ow), "setPieces": len(sp),
                       "runewordsMade": rw},
            "sample": {"foundLog": list(fl), "owned": ow, "setPieces": list(sp)},
            "dates": dict((n, "Sep 1, 2026") for n in fl),
            "gameFound": dict(("Game %02d" % i, "Sep 1") for i in range(gf)) or None,
            "rwMadeFull": dict(("RW %02d" % i, "Sep 1") for i in range(rw)) or None,
            "fullStores": {}}


class _Patched(object):
    """Point control_app at a fixture backup dir, a stub board and a pinned clock; restore after."""

    def __init__(self, bdir, board, now, sleeps_allowed=1):
        self.bdir, self.board, self.clock = bdir, board, _Clock(now, sleeps_allowed)

    def __enter__(self):
        self.saved = (CA._LEDGER_BACKUP_DIR, CA.board_ownership, CA.time,
                      dict(CA._LEDGER_BACKUP_STATE))
        CA._LEDGER_BACKUP_DIR = self.bdir
        CA.board_ownership = lambda *a, **k: self.board
        CA.time = self.clock
        CA._LEDGER_BACKUP_STATE["counts"] = None       # never "unchanged" across fixtures
        return self

    def __exit__(self, *exc):
        CA._LEDGER_BACKUP_DIR, CA.board_ownership, CA.time, st = self.saved
        CA._LEDGER_BACKUP_STATE.clear()
        CA._LEDGER_BACKUP_STATE.update(st)
        return False


def _write(bdir, when, board):
    """One backup written by the REAL writer (`_ledger_snapshot_once`), mtime pinned to `when`."""
    with _Patched(bdir, board, when):
        path, why = CA._ledger_snapshot_once(force=True)
    assert path, "premise: the real writer refused the fixture: %s" % why
    os.utime(path, (when, when))
    return os.path.basename(path)


class _World(unittest.TestCase):

    def setUp(self):
        self.bdir = tempfile.mkdtemp(prefix="backups_")
        self.rec = os.path.join(tempfile.mkdtemp(prefix="drops_"), ".ledger_drops.json")
        self.addCleanup(shutil.rmtree, self.bdir, True)

    def _measured(self, before_age=2 * DAY):
        """The 2026-09-27 shape: 134/223 -> 0/0 -> 0/0. -> (before, drop, after) file names."""
        a = _write(self.bdir, PINNED_NOW - before_age, _board(134, 223))
        b = _write(self.bdir, PINNED_NOW - 1800, _board(0, 0))
        c = _write(self.bdir, PINNED_NOW - 600, _board(0, 0))
        return a, b, c

    def _record(self, path=None):
        doc, why = CA.ledger_drops_load(path or self.rec)
        self.assertIsNotNone(doc, why)
        return doc


# ── 1. ONE DEFINITION OF A DROP ─────────────────────────────────────────────────────────────────
class ADropIsDefinedOnce(unittest.TestCase):

    def test_the_measured_vault_reset_is_a_drop_and_the_steady_store_is_not(self):
        d = LR.drops_between({"foundLog": {"A": 1}, "setPieces": PIECES, "owned": ["x"] * 223},
                             {"foundLog": {"A": 1}, "setPieces": [], "owned": []})
        got = dict((x["store"], (x["from"], x["to"])) for x in d)
        self.assertEqual({"setPieces": (134, 0), "owned": (223, 0)}, got,
                         "134 -> 0 set pieces and 223 -> 0 owned is the measured loss: %r" % d)

    def test_the_floor_and_the_fraction(self):
        def fell(a, b):
            return bool(LR.drops_between({"owned": ["x"] * a}, {"owned": ["x"] * b}))
        self.assertFalse(fell(30, 21), "a fall of 9 is under the floor of 10 — ordinary churn")
        self.assertTrue(fell(30, 20), "a fall of 10 meets max(10, 25%) and is a drop")
        self.assertFalse(fell(445, 340), "105 of 445 is under 25% — not a drop")
        self.assertTrue(fell(445, 333), "112 of 445 is >= 25% — a drop")
        self.assertTrue(fell(5, 0), "any store falling to ZERO is a drop, however small")

    def test_an_UNKNOWN_count_is_never_a_drop(self):
        # gameFound has no independent count: absent means nobody copied it, not "he has none"
        self.assertEqual([], LR.drops_between({"ledger": {"gameFound": {"g%d" % i: 1 for i in range(29)}},
                                               "counts": {}},
                                              {"ledger": {}, "counts": {}}))
        # rwMade absent beside the board's own count of 0 IS a measured zero
        d = LR.drops_between({"ledger": {"rwMade": {"r%d" % i: 1 for i in range(99)}}, "counts": {}},
                             {"ledger": {}, "counts": {"runewordsMade": 0}})
        self.assertEqual([{"store": "rwMade", "from": 99, "to": 0}], d)
        # and with no count at all it stays UNKNOWN
        self.assertEqual([], LR.drops_between({"ledger": {"rwMade": {"r": 1}}, "counts": {}},
                                              {"ledger": {}, "counts": {}}))


# ── 2. THE PLAN READS THE BACKUP BEFORE THE DROP ────────────────────────────────────────────────
class ThePlanReadsTheBackupBeforeTheDrop(_World):

    def test_a_dropped_store_is_read_from_the_last_backup_BEFORE_the_drop(self):
        before, drop, newest = self._measured()
        cur = {"foundLog": dict((n, "d") for n in _board(0, 0)["sample"]["foundLog"]), "setPieces": []}
        # BASELINE — the newest backup holds nothing to put back, so a newest-only plan restores 0
        with io.open(os.path.join(self.bdir, newest), encoding="utf-8") as fh:
            self.assertEqual([], json.load(fh)["ledger"]["setPieces"],
                             "premise: the newest backup must be the emptied one")
        p = LR.plan(ROUTE, cur, d=self.bdir)
        self.assertTrue(p["ok"], p)
        sp = p["stores"]["setPieces"]
        self.assertEqual(before, sp["source"], "setPieces must come from the backup before the drop: %r" % sp)
        self.assertEqual(sorted(PIECES), sorted(sp["missing"]),
                         "the 134 pieces the drop took are what the plan must offer back")
        self.assertIn("BEFORE the drop", sp["sourceWhy"])
        self.assertTrue(p["why"].startswith("DROP-AWARE"), p["why"])
        self.assertEqual(newest, p["stores"]["foundLog"]["source"],
                         "foundLog never dropped, so it reads the newest backup")
        self.assertEqual(before, p["sources"]["owned"], "owned dropped too — its source is the same file")
        self.assertEqual(newest, p["file"])

    def test_a_thinned_chain_does_not_invent_a_drop_the_record_never_opened(self):
        # Two keepers, 223 -> 163. Replaying that pair calls it a drop. The watcher, stepping
        # every snapshot, never opened one. The plan must believe the record.
        old = _write(self.bdir, PINNED_NOW - 100 * DAY, _board(134, 223))
        new = _write(self.bdir, PINNED_NOW - 600, _board(134, 163))
        cur = {"foundLog": {}, "setPieces": list(PIECES), "owned": ["Owned %03d" % i for i in range(163)]}
        replayed = LR.plan(ROUTE, cur, d=self.bdir)
        self.assertEqual(old, replayed["sources"]["owned"],
                         "premise: the thinned pair is a drop when replayed: %r" % replayed.get("sources"))
        trusted = LR.plan(ROUTE, cur, d=self.bdir, episodes=[])
        self.assertEqual(new, trusted["sources"]["owned"],
                         "no open episode, but the plan still read the old keeper: %r" % trusted.get("sources"))
        held = LR.plan(ROUTE, cur, d=self.bdir, episodes=[{
            "store": "owned", "from": 223, "to": 163, "open": True,
            "beforeFile": old, "afterFile": new, "routeKey": LR._route_key(ROUTE)}])
        self.assertEqual(old, held["sources"]["owned"],
                         "an open episode was ignored: %r" % held.get("sources"))

    def test_a_RECOVERED_store_reads_the_newest_again(self):
        _write(self.bdir, PINNED_NOW - 3 * DAY, _board(134, 223))
        _write(self.bdir, PINNED_NOW - 2 * DAY, _board(0, 0))
        back = _write(self.bdir, PINNED_NOW - 600, _board(134, 223))
        p = LR.plan(ROUTE, {"foundLog": {}, "setPieces": []}, d=self.bdir)
        self.assertEqual(back, p["stores"]["setPieces"]["source"],
                         "the store came back to where it fell from — the drop is over: %r" % p["sources"])
        self.assertEqual([], p["drops"])

    def test_the_set_piece_roster_comes_from_the_file_that_still_holds_it(self):
        """⚠ #246 W0c's refill, through the drop: after a reset the NEWEST holds setPieces [] while
        foundLog still carries the pieces, so a roster read from the newest alone sends every piece
        down the uniques half."""
        self._measured()
        p = LR.plan(ROUTE, {"foundLog": {}, "setPieces": []}, d=self.bdir)
        prop = LR.proposal_from(p)
        uni = set(r["name"] for r in prop["wouldAdd"].get("uniques", []))
        sets = set(r["name"] for r in prop["wouldAdd"].get("sets", []))
        self.assertFalse(uni & set(PIECES), "set pieces rode the UNIQUES half: %d" % len(uni & set(PIECES)))
        self.assertEqual(set(PIECES), sets & set(PIECES))

    def test_the_other_doors_read_the_same_per_store_source(self):
        _write(self.bdir, PINNED_NOW - 2 * DAY, _board(134, 223, rw=99))
        _write(self.bdir, PINNED_NOW - 600, _board(0, 0, rw=0))
        p = LR.plan(ROUTE, {"foundLog": {}, "setPieces": []}, d=self.bdir)
        extra, _why = LR.backed_up_only_from(p, d=self.bdir)
        self.assertEqual(99, len(extra.get("rwMade") or {}),
                         "the runeword door was handed the EMPTIED snapshot, not the one before the drop")
        self.assertEqual(223, len(extra.get("owned") or []))


# ── 3. A NAMED FILE WINS; A FOREIGN ONE IS REFUSED; THE ROUTES CARRY IT ─────────────────────────
class ANamedFileWinsAndAForeignOneIsRefused(_World):

    def test_the_file_he_names_wins_for_every_store(self):
        before, drop, newest = self._measured()
        p = LR.plan(ROUTE, {"foundLog": {}, "setPieces": []}, d=self.bdir, file=drop)
        self.assertTrue(p["ok"], p)
        self.assertEqual(drop, p["file"])
        self.assertEqual({drop}, set(p["sources"].values()), "a named file must win for EVERY store")
        self.assertTrue(p["named"])

    def test_a_traversal_a_symlink_out_or_another_profiles_file_is_refused(self):
        before, _d, _n = self._measured()
        outside = tempfile.mkdtemp(prefix="outside_")
        # a REAL backup of THIS route outside the dir, so only the location check can refuse it
        shutil.copy(os.path.join(self.bdir, before), os.path.join(outside, "ledger_outside.json"))
        os.symlink(os.path.join(outside, "ledger_outside.json"),
                   os.path.join(self.bdir, "ledger_2000-01-01_000000.json"))
        foreign = _write(self.bdir, PINNED_NOW - 5 * DAY, _board(10, 10, route=OTHER))
        with io.open(os.path.join(self.bdir, "ledger_1999-01-01_000000.json"), "w", encoding="utf-8") as fh:
            json.dump({"ledger": {"foundLog": {"A": 1}}}, fh)             # unrouted
        for name, why in (("../ledger_outside.json", "a path"),
                          (os.path.join(outside, "ledger_outside.json"), "an absolute path"),
                          ("ledger_2000-01-01_000000.json", "a symlink pointing OUT of the dir"),
                          (foreign, "another profile's backup"),
                          ("ledger_1999-01-01_000000.json", "an unrouted backup"),
                          ("notes.json", "not a ledger backup"),
                          ("ledger_2099-01-01_000000.json", "a file that does not exist")):
            p = LR.plan(ROUTE, {"foundLog": {}, "setPieces": []}, d=self.bdir, file=name)
            self.assertFalse(p.get("ok"), "%s was HONOURED as a restore source: %r" % (why, p))
            self.assertTrue(p.get("why"), "%s was refused with no reason" % why)

    def test_the_routes_carry_the_named_file_through(self):
        before, drop, newest = self._measured()
        from http.server import ThreadingHTTPServer
        srv = ThreadingHTTPServer(("127.0.0.1", 0), CA.Handler)       # ephemeral, never :17772
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        saved = (CA._LEDGER_BACKUP_DIR, CA._restore_current_from_board)
        CA._LEDGER_BACKUP_DIR = self.bdir
        CA._restore_current_from_board = lambda: ({"foundLog": {}, "setPieces": []}, dict(ROUTE), "")
        try:
            def post(route, body):
                req = urllib.request.Request("http://127.0.0.1:%d%s" % (srv.server_address[1], route),
                                             data=json.dumps(body).encode(), method="POST",
                                             headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    return json.loads(r.read().decode("utf-8"))
            named = post("/api/ledger_restore_plan", {"file": drop})
            self.assertTrue(named.get("ok"), named)
            self.assertEqual(drop, named.get("file"), "the plan route dropped {\"file\"} on the floor")
            aware = post("/api/ledger_restore_plan", {})
            self.assertEqual(before, (aware.get("sources") or {}).get("setPieces"),
                             "the route's no-file plan is not drop-aware: %r" % aware.get("sources"))
            bad = post("/api/ledger_restore_plan", {"file": "../ledger_x.json"})
            self.assertFalse(bad.get("ok"), "the route honoured a traversal: %r" % bad)
            ap = post("/api/ledger_restore_apply", {"file": drop})          # no confirm
            self.assertFalse(ap.get("applied"), ap)
            self.assertEqual(drop, (ap.get("planned") or {}).get("file"),
                             "the apply route dropped {\"file\"} on the floor")
        finally:
            CA._LEDGER_BACKUP_DIR, CA._restore_current_from_board = saved
            srv.shutdown()
            srv.server_close()


# ── 4. THE LOOP OPENS AN EPISODE AND THE PRUNE KEEPS ITS BEFORE-FILE ────────────────────────────
class TheLoopSeesTheDropAndThePruneKeepsTheBackup(_World):

    def test_one_real_loop_iteration_opens_the_episode_and_the_prune_keeps_the_before_file(self):
        before = _write(self.bdir, PINNED_NOW - 100 * DAY, _board(134, 223))
        # BASELINE — past 48h and past the 90-day keeper, the age rules alone DO delete it
        copy = tempfile.mkdtemp(prefix="baseline_")
        shutil.copy2(os.path.join(self.bdir, before), os.path.join(copy, before))
        r0 = CA._ledger_backup_prune(copy, now=PINNED_NOW,
                                     drops_path=os.path.join(copy, ".none.json"))
        self.assertEqual(1, r0["pruned"], "premise: without a drop episode the file must be prunable")
        # ONE iteration of the real loop: real writer, real watch, real prune, pinned clock
        rec = CA._ledger_drops_path()
        self.assertTrue(rec.startswith(os.path.realpath(_WORLD)), "the record is not in the fixture world: %s" % rec)
        if os.path.exists(rec):
            os.remove(rec)
        self.addCleanup(lambda: os.path.exists(rec) and os.remove(rec))
        with _Patched(self.bdir, _board(0, 0), PINNED_NOW):
            with self.assertRaises(_Stop):
                CA._ledger_backup_loop()
            dw = dict(CA._LEDGER_BACKUP_STATE.get("dropWatch") or {})
        self.assertTrue(dw.get("ok"), "the loop's drop watch did not run or failed: %r" % dw)
        doc = self._record(rec)
        opened = dict((e["store"], e) for e in doc["episodes"] if e.get("open"))
        self.assertIn("setPieces", opened, "the loop saw 134 -> 0 and opened no episode: %r" % doc)
        ep = opened["setPieces"]
        self.assertEqual((134, 0, before), (ep["from"], ep["to"], ep["beforeFile"]))
        self.assertIn("owned", opened)
        self.assertTrue(os.path.exists(os.path.join(self.bdir, before)),
                        "the prune DELETED the one backup that can put the pieces back, while the drop is open")

    def test_the_prune_keeps_every_open_before_file_and_frees_it_once_closed(self):
        before, drop, newest = self._measured(before_age=100 * DAY)
        CA._ledger_drop_watch(os.path.join(self.bdir, newest), bdir=self.bdir, path=self.rec,
                              now_ms=PINNED_NOW * 1000)
        r = CA._ledger_backup_prune(self.bdir, now=PINNED_NOW, drops_path=self.rec)
        self.assertIn(before, r["dropProtected"], r)
        self.assertIn(before, _fx_tmp.list_own(self.bdir))
        self.assertIn("open ledger drop", r["why"])
        # the store comes back: the episode closes and the file ages out like any other
        back = _write(self.bdir, PINNED_NOW - 60, _board(134, 223))
        CA._ledger_drop_watch(os.path.join(self.bdir, back), bdir=self.bdir, path=self.rec,
                              now_ms=PINNED_NOW * 1000)
        r2 = CA._ledger_backup_prune(self.bdir, now=PINNED_NOW, drops_path=self.rec)
        self.assertEqual([], r2["dropProtected"], "a CLOSED drop still protects: %r" % r2)
        self.assertNotIn(before, _fx_tmp.list_own(self.bdir),
                         "the drop closed and its 100-day-old before-file was kept forever anyway")

    def test_while_the_record_is_UNREADABLE_the_prune_deletes_nothing(self):
        before, _d, _n = self._measured(before_age=100 * DAY)
        with io.open(self.rec, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        r = CA._ledger_backup_prune(self.bdir, now=PINNED_NOW, drops_path=self.rec)
        self.assertEqual(0, r["pruned"], "the prune deleted while it could not read which files a loss needs")
        self.assertIn(before, _fx_tmp.list_own(self.bdir))
        self.assertIn("UNKNOWN", r["why"])


# ── 5. THE EPISODE LIFECYCLE ────────────────────────────────────────────────────────────────────
class TheEpisodeClosesOnlyWhenTheStoreIsBack(_World):

    def _judge(self, name):
        return CA._ledger_drop_watch(os.path.join(self.bdir, name), bdir=self.bdir, path=self.rec,
                                     now_ms=PINNED_NOW * 1000)

    def test_it_opens_stays_open_and_closes_on_recovery(self):
        a = _write(self.bdir, PINNED_NOW - 4 * 3600, _board(134, 223))
        self.assertTrue(self._judge(a)["ok"])
        b = _write(self.bdir, PINNED_NOW - 3 * 3600, _board(0, 0))
        w = self._judge(b)
        self.assertTrue(any(s.startswith("setPieces 134->0") for s in w["opened"]), w)
        ep = [e for e in self._record()["episodes"] if e["store"] == "setPieces"][0]
        self.assertEqual((a, b), (ep["beforeFile"], ep["afterFile"]))
        self.assertEqual(LR.stamp_ms(b), ep["at"], "the episode does not say WHEN the store fell")
        c = _write(self.bdir, PINNED_NOW - 2 * 3600, _board(100, 0))
        self._judge(c)
        self.assertTrue([e for e in self._record()["episodes"] if e["store"] == "setPieces"][0]["open"],
                        "100 of 134 is not back — the episode closed early")
        d = _write(self.bdir, PINNED_NOW - 3600, _board(140, 0))
        self._judge(d)
        sp = [e for e in self._record()["episodes"] if e["store"] == "setPieces"][0]
        self.assertFalse(sp["open"], "the store is back to 140 >= 134 and the episode is still open")
        self.assertEqual(d, sp["closedBy"])
        self.assertTrue([e for e in self._record()["episodes"] if e["store"] == "owned"][0]["open"],
                        "owned is still 0 — its episode must stay open")

    def test_a_deliberate_clear_closes_the_drop_and_frees_the_backup(self):
        before, _drop, newest = self._measured(before_age=100 * DAY)
        self.assertTrue(self._judge(newest)["ok"])
        refused = CA.ledger_drop_accept("setPieces", "", confirm=True, path=self.rec,
                                        now_ms=PINNED_NOW * 1000)
        self.assertFalse(refused.get("applied"), refused)
        self.assertTrue([e for e in self._record()["episodes"] if e["store"] == "setPieces"][0]["open"],
                        "an empty reason closed the drop")
        preview = CA.ledger_drop_accept("setPieces", "fresh vault", confirm=False, path=self.rec)
        self.assertFalse(preview.get("applied"), preview)
        self.assertTrue([e for e in self._record()["episodes"] if e["store"] == "setPieces"][0]["open"],
                        "a preview wrote the record")
        done = CA.ledger_drop_accept("setPieces", "fresh vault", confirm=True, path=self.rec,
                                     now_ms=PINNED_NOW * 1000)
        self.assertTrue(done.get("applied"), done)
        owned = CA.ledger_drop_accept("owned", "fresh vault", confirm=True, path=self.rec,
                                      now_ms=PINNED_NOW * 1000)
        self.assertTrue(owned.get("applied"), owned)
        ep = [e for e in self._record()["episodes"] if e["store"] == "setPieces"][0]
        self.assertFalse(ep["open"])
        self.assertTrue(str(ep.get("closedBy") or "").startswith("accepted:"), ep)
        r = CA._ledger_backup_prune(self.bdir, now=PINNED_NOW, drops_path=self.rec)
        self.assertNotIn(before, r.get("dropProtected") or [],
                         "an accepted drop still pins its backup: %r" % r)

    def test_a_first_look_REPLAYS_a_drop_that_happened_before_the_watcher_existed(self):
        """His exact case: the drop at 03:31 predates this code, so no step ever compared it."""
        before, drop, newest = self._measured()
        w = self._judge(newest)
        self.assertIn("replayed", w["why"], w)
        opened = [e for e in self._record()["episodes"] if e.get("open") and e["store"] == "setPieces"]
        self.assertEqual([before], [e["beforeFile"] for e in opened],
                         "the first look did not find the drop that happened before it existed")

    def test_an_unreadable_record_is_SET_ASIDE_and_rebuilt_never_written_over(self):
        before, drop, newest = self._measured()
        with io.open(self.rec, "w", encoding="utf-8") as fh:
            fh.write("{damaged")
        w = self._judge(newest)
        self.assertTrue(w["ok"], w)
        aside = [n for n in _fx_tmp.list_own(os.path.dirname(self.rec)) if ".unreadable-" in n]
        self.assertEqual(1, len(aside), "the damaged record was written over instead of set aside")
        with io.open(os.path.join(os.path.dirname(self.rec), aside[0]), encoding="utf-8") as fh:
            self.assertEqual("{damaged", fh.read())
        self.assertTrue([e for e in self._record()["episodes"] if e.get("open")],
                        "the rebuilt record lost the open drop")

    def test_the_record_path_is_resolved_at_CALL_time(self):
        other = tempfile.mkdtemp(prefix="world2_")
        saved = os.environ.get("TV_HIST")
        try:
            os.environ["TV_HIST"] = other
            self.assertEqual(os.path.join(os.path.realpath(other), ".ledger_drops.json"),
                             CA._ledger_drops_path())
        finally:
            os.environ["TV_HIST"] = saved
        self.assertTrue(CA._ledger_drops_path().startswith(os.path.realpath(_WORLD)))


# ── 6. THE HEART — the doctor row ───────────────────────────────────────────────────────────────
class TheDoctorSaysSoUntilItIsBack(_World):

    def _row(self, bdir=None, now=None):
        return CD._check_no_ledger_store_dropped_unseen(bdir=bdir or self.bdir, drops_path=self.rec,
                                                        now=PINNED_NOW if now is None else now)

    def test_an_open_drop_names_store_from_to_when_and_the_door(self):
        before, drop, newest = self._measured()
        CA._ledger_drop_watch(os.path.join(self.bdir, newest), bdir=self.bdir, path=self.rec,
                              now_ms=PINNED_NOW * 1000)
        st, why = self._row()
        self.assertEqual(CD.MISSING, st, why)
        for must in ("setPieces fell 134 -> 0", before, "/api/ledger_restore_apply",
                     _real_time.strftime("%Y-%m-%d %H:%M", _real_time.localtime(LR.stamp_ms(drop) / 1000.0)),
                     "/api/owned_restore", "/api/ledger_drop_accept"):
            self.assertIn(must, why)

    def test_a_runeword_drop_is_sent_to_the_runeword_door(self):
        """The second eye on v3520: rwMade is BACKED_UP_ONLY - the chronicle door never carries it, so sending him
        there for a runeword loss restored nothing. The advice names /api/rw_restore and keeps rwMade off the list
        the chronicle plan 'reads'."""
        _write(self.bdir, PINNED_NOW - 3 * 3600, _board(134, 0, rw=99))
        n = _write(self.bdir, PINNED_NOW - 3600, _board(134, 0, rw=0))
        CA._ledger_drop_watch(os.path.join(self.bdir, n), bdir=self.bdir, path=self.rec, now_ms=PINNED_NOW * 1000)
        st, why = self._row()
        self.assertEqual(CD.MISSING, st, why)
        self.assertIn("rwMade fell 99 -> 0", why)
        self.assertIn("/api/rw_restore", why, "a runeword drop is not sent to the runeword door")
        self.assertNotIn("the plan reads rwMade", why, "the chronicle plan is said to read rwMade - it does not")
        # the second eye on v3521: with ONLY rwMade open, the chronicle door restores nothing that fell - it must not
        # be the first thing he is told to POST, and "take every store from that one file" must not be offered
        self.assertNotIn("/api/ledger_restore_plan", why, "an rwMade-only drop still sends him to the chronicle plan first")
        self.assertTrue(why.index("/api/rw_restore") < why.index("ledger_drop_accept"), why)

    def test_one_file_is_offered_only_when_every_drop_fell_against_it(self):
        """The second eye on v3519 (11c3e2f5): a named file wins OUTRIGHT in ledger_restore.plan, so the hint that
        offered the FIRST drop's beforeFile for 'every store' sent a store that fell LATER back to an older snapshot.
        Two chronicle stores fall against two different backups here, through the real writer and the real watcher:
        no single file may be offered, and both before-files are named. The one-drop world still gets its one file."""
        a = _write(self.bdir, PINNED_NOW - 4 * 3600, _board(134, 0, found=500))
        b = _write(self.bdir, PINNED_NOW - 3 * 3600, _board(0, 0, found=500))            # setPieces 134 -> 0
        CA._ledger_drop_watch(os.path.join(self.bdir, b), bdir=self.bdir, path=self.rec, now_ms=PINNED_NOW * 1000)
        c = _write(self.bdir, PINNED_NOW - 2 * 3600, _board(0, 0, found=600))            # he kept playing
        CA._ledger_drop_watch(os.path.join(self.bdir, c), bdir=self.bdir, path=self.rec, now_ms=PINNED_NOW * 1000)
        d = _write(self.bdir, PINNED_NOW - 3600, _board(0, 0, found=0))                  # foundLog 734 -> 134
        CA._ledger_drop_watch(os.path.join(self.bdir, d), bdir=self.bdir, path=self.rec, now_ms=PINNED_NOW * 1000)
        opened = dict((e["store"], e["beforeFile"]) for e in self._record().get("episodes") or [] if e.get("open"))
        self.assertEqual({"setPieces": a, "foundLog": c}, opened,
                         "PREMISE: two chronicle stores fell against two different backups: %r" % opened)
        st, why = self._row()
        self.assertEqual(CD.MISSING, st, why)
        self.assertIn("/api/ledger_restore_apply", why)
        self.assertNotIn("take every store from that one file", why,
                         "one file was offered for two drops that fell against different backups - the later store "
                         "would be put back from the older snapshot")
        for f in (a, c):
            self.assertIn(f, why, "the hint does not name the backup %s fell against" % f)

    def test_the_one_drop_world_still_gets_its_one_file(self):
        before, drop, newest = self._measured()
        CA._ledger_drop_watch(os.path.join(self.bdir, newest), bdir=self.bdir, path=self.rec,
                              now_ms=PINNED_NOW * 1000)
        st, why = self._row()
        self.assertIn("\"file\": \"%s\" to take every store from that one file" % before, why)

    def test_it_is_UNKNOWN_when_it_cannot_see(self):
        self.assertEqual(CD.UNKNOWN, self._row(bdir=os.path.join(self.bdir, "gone"))[0],
                         "no readable backup dir must be UNKNOWN, not clean")
        self._measured()
        st, why = self._row()
        self.assertEqual(CD.UNKNOWN, st, "a watcher that never wrote its record read as clean: %s" % why)
        self.assertIn("UNMEASURED", why)
        with io.open(self.rec, "w", encoding="utf-8") as fh:
            fh.write("[1, 2")
        self.assertEqual(CD.UNKNOWN, self._row()[0], "an unreadable record read as clean")

    def test_all_closed_is_OK(self):
        _write(self.bdir, PINNED_NOW - 3 * 3600, _board(134, 0))
        _write(self.bdir, PINNED_NOW - 2 * 3600, _board(0, 0))
        n = _write(self.bdir, PINNED_NOW - 3600, _board(134, 0))
        CA._ledger_drop_watch(os.path.join(self.bdir, n), bdir=self.bdir, path=self.rec,
                              now_ms=PINNED_NOW * 1000)
        st, why = self._row()
        self.assertEqual(CD.OK, st, why)

    def test_it_watches_the_WATCHER(self):
        a = _write(self.bdir, PINNED_NOW - 3 * 3600, _board(134, 0))
        CA._ledger_drop_watch(os.path.join(self.bdir, a), bdir=self.bdir, path=self.rec,
                              now_ms=PINNED_NOW * 1000)
        self.assertEqual(CD.OK, self._row()[0])
        _write(self.bdir, PINNED_NOW - 3600, _board(134, 0))              # written, never judged
        st, why = self._row()
        self.assertEqual(CD.MISSING, st, "a backup the watcher never judged read as fine: %s" % why)
        self.assertIn("has NOT judged", why)

    def test_the_row_is_on_the_roster_the_eagle_runs(self):
        fns = dict(CD.CHECKS)
        self.assertIs(fns.get("ledger drop"), CD._check_no_ledger_store_dropped_unseen,
                      "the row exists and the doctor never runs it")


RED_PROOF = [
    {
        "why": "the second eye on v3519 - one backup is offered for every store when two drops fell against different backups",
        "file": "tv/console_doctor.py",
        "find": "            if len(_bfs) == 1:\n",
        "replace": "            if True:\n",
        "matches": 1,
    },
    {
        "why": "the second eye on v3521 - an rwMade-only drop LEADS with the chronicle plan, which puts back nothing that fell",
        "file": "console_doctor.py",
        "find": "        _own_doors = (\"owned\", \"rwMade\", \"gameFound\")\n",
        "replace": "        _own_doors = (\"owned\", \"gameFound\")\n",
        "matches": 1,
    },
    {
        "why": "the second eye on v3520 - a runeword drop is sent to the chronicle door that never restores it",
        "file": "console_doctor.py",
        "find": "        if any(e.get(\"store\") == \"rwMade\" for e in open_eps):\n",
        "replace": "        if False:\n",
        "matches": 1,
    },
    {"why": "a partial drop (445 -> 333) is never seen — only a fall to zero counts",
     "file": "ledger_restore.py",
     "find": "        if b == 0 or (a - b) >= max(DROP_MIN, DROP_FRAC * a):",
     "replace": "        if b == 0:",
     "matches": 1},
    {"why": "an UNKNOWN count read as zero turns a store nobody copied into a reported drop",
     "file": "ledger_restore.py",
     "find": "    return None\n\n\ndef drops_between(",
     "replace": "    return 0\n\n\ndef drops_between(",
     "matches": 1},
    {"why": "the plan goes back to reading the NEWEST backup, which after a reset holds nothing",
     "file": "ledger_restore.py",
     "find": "        live = [e for e in eps if e.get(\"open\") and e.get(\"store\") == s",
     "replace": "        live = [e for e in eps if False and e.get(\"store\") == s",
     "matches": 1},
    {"why": "an episode never closes, so a recovered store reads a stale source forever",
     "file": "ledger_restore.py",
     "find": "        if back:\n            ep.update(",
     "replace": "        if False:\n            ep.update(",
     "matches": 1},
    {"why": "a symlink inside the backup dir pointing OUT is honoured as a restore source",
     "file": "ledger_restore.py",
     "find": "    if os.path.dirname(real_p) != real_d:",
     "replace": "    if False:",
     "matches": 1},
    {"why": "another profile's backup is honoured when named — one person's ledger into another's",
     "file": "ledger_restore.py",
     "find": "    if got != want:\n        return None, \"refused",
     "replace": "    if False:\n        return None, \"refused",
     "matches": 1},
    {"why": "the runeword door re-reads the newest (emptied) file instead of the per-store source",
     "file": "ledger_restore.py",
     "find": "        n = os.path.basename(str(_srcs.get(store) or plan_out[\"file\"]))",
     "replace": "        n = os.path.basename(str(plan_out[\"file\"]))",
     "matches": 1},
    {"why": "the set-piece roster comes from the newest alone, so every piece rides the uniques half",
     "file": "ledger_restore.py",
     "find": "    for _sp, _sb, _sw in [(path, blob, \"\")] + list(sources.values()):",
     "replace": "    for _sp, _sb, _sw in [(path, blob, \"\")]:",
     "matches": 1},
    {"why": "the prune ignores open drop episodes and deletes the one backup that can put them back",
     "file": "control_app.py",
     "find": "        if os.path.basename(pp) in _drop_keep:",
     "replace": "        if False:",
     "matches": 1},
    {"why": "an unreadable drop record is read as 'no drops' and the prune deletes blind",
     "file": "control_app.py",
     "find": "    _ddoc, _dwhy = ledger_drops_load(drops_path)",
     "replace": "    _ddoc, _dwhy = (ledger_drops_load(drops_path)[0] or {\"episodes\": []}), \"\"",
     "matches": 1},
    {"why": "the loop snapshots and prunes without judging the snapshot — the unjoined end",
     "file": "control_app.py",
     "find": "                _dw = _ledger_drop_watch(path)",
     "replace": "                _dw = {}",
     "matches": 1},
    {"why": "a first look never replays, so a drop that predates the watcher is never found",
     "file": "control_app.py",
     "find": "            found = _LR.replay(chain, route_key=rk)",
     "replace": "            found = []",
     "matches": 1},
    {"why": "a damaged record is written over instead of set aside — the evidence is destroyed",
     "file": "control_app.py",
     "find": "                os.replace(p, aside)",
     "replace": "                pass",
     "matches": 1},
    {"why": "the record path is frozen to HERE — a fixture world would read and write his record",
     "file": "control_app.py",
     "find": "    return os.path.join(_fixture_root_for_state(), \".ledger_drops.json\")",
     "replace": "    return os.path.join(HERE, \".ledger_drops.json\")",
     "matches": 1},
    {"why": "the plan route ignores {\"file\"} — the door he names a backup through is dead",
     "file": "control_app.py",
     "find": "            self._json(200, ledger_restore_plan(file=body.get(\"file\") or None))",
     "replace": "            self._json(200, ledger_restore_plan())",
     "matches": 1},
    {"why": "the doctor row stops reporting an open drop and reads clean with the pieces gone",
     "file": "console_doctor.py",
     "find": "    if open_eps:\n        def _when(e):",
     "replace": "    if False:\n        def _when(e):",
     "matches": 1},
    {"why": "a watcher that never wrote its record reads as clean — UNKNOWN reported as zero",
     "file": "console_doctor.py",
     "find": "    if why == \"absent\":\n        return UNKNOWN, (\"the drop watcher has never",
     "replace": "    if False:\n        return UNKNOWN, (\"the drop watcher has never",
     "matches": 1},
    {"why": "the watcher's own death goes unseen — a backup nobody judged reads fine",
     "file": "console_doctor.py",
     "find": "        if age_s is None or age_s > _DROP_JUDGE_GRACE_S:",
     "replace": "        if False:",
     "matches": 1},
    {"why": "a deliberate clear closes with no reason, so a bug and a choice look the same",
     "file": "ledger_restore.py",
     "find": "    if not why_reason:\n        return [], \"a reason is required — closing a drop without one is the same as not recording it\"\n",
     "replace": "    if False:\n        return [], \"a reason is required — closing a drop without one is the same as not recording it\"\n",
     "matches": 1},
    {"why": "the plan ignores the durable record and replays a thinned chain into a drop that never happened",
     "file": "ledger_restore.py",
     "find": "    if episodes is None:\n        eps = replay(",
     "replace": "    if True:\n        eps = replay(",
     "matches": 1},
    {"why": "the doctor never names the door that closes a deliberate clear",
     "file": "console_doctor.py",
     "find": "        door += (\". A deliberate clear is not a loss to undo: POST /api/ledger_drop_accept \"\n                 \"{\\\"store\\\": %r, \\\"reason\\\": \\\"why\\\", \\\"confirm\\\": true}\"\n                 % open_eps[0].get(\"store\"))\n",
     "replace": "        door += \"\"\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
