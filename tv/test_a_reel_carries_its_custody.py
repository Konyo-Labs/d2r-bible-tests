#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A REEL CARRIES ITS CUSTODY — every hand that held it, quoted from that hand's own store; every contradiction named.

His vision, 2026-09-28 (#55): a robot-vacuum map — *"it maps out the rooms and house and areas it cant go"*, with
*"witnesses ... some sort of stamping system"*. This is the first slice, at REEL granularity. MEASURED before it
existed, read-only on his tree: 460 tombstones ALL say "sealed by BOTH lanes", 44 have a vault seal, 56 have
neither seal, 0 river stamps say TOMBSTONE — five stores keyed three ways, and nothing could say per reel who
held it and who only claims to have.

WHAT THIS LAW HOLDS, driven over a temp world laid out where each owner's own resolver says (never his stores):
  · reel_custody.world — every path is an owner's answer (retro_triage, reel_retention, river_stamp, read_pictures)
  · a reel that reached the vault names four hands and the room it never entered; a recorder-only reel names four
  · a tombstone claiming both seals is contradicted by the seal stores, with both writers named
  · a removal the shelf still shows, and a hand-stamped TOMBSTONE with no ledger row, are contradictions
  · a claim the seal stores back is no contradiction, and the door end_routes says it left by is quoted
  · an UNREADABLE store leaves that hand None, never False, and raises NO contradiction; the doctor says UNKNOWN
  · a reel no store records is none yet, not nowhere
  · the journal hands the printer its reads and whether their pictures are still on disk; not handed = None
  · the census counts every reel and caps only the rows DRAWN
  · the doctor row says MISSING with its denominators, OK over 0 of 0, OK over a clean chain
  · the console serves /api/custody for one reel and for the census, hands in the journal only when it read
    cleanly, and says why when the record cannot be assembled
  · the row is in CHECKS, WATCHES and corroborate's registry, and hands reel_custody.doctor's answer through
RED_PROOF below — 4, each seen red.
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402  #171 — this run's scratch dirs leave with it
_fx_tmp.contain()
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import reel_custody as RC  # noqa: E402


# synthetic ids from the 2017 epoch (the tree's convention: no recording can carry one, so no footage is ever pinned)
def _reel(n):
    return "reel_s_150000000000%d_%d" % (n, n)


def _sess(n):
    return "s_150000000000%d_%d" % (n, n)


BOTH = "read (0 pages) and sealed by BOTH lanes - it has given up its information"


def _dump(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh)


def _append(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "a", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")


def _shelf_reel(hist, n, frames=3):
    d = os.path.join(hist, _reel(n))
    os.makedirs(d)
    for k in range(frames):
        with open(os.path.join(d, "f_%d.jpg" % (1000000000000 + n * 10 + k)), "wb") as fh:
            fh.write(b"\xff\xd8")


class World(object):
    """A temp world with six reels, laid out where each owner's resolver says:
      1 on the shelf, surveyed empty, routed by a lane — recorder + triage
      2 on the shelf, surveyed, chronicle-sealed, vault-sealed COVERED, cited — four hands, never tombstoned
      3 on the shelf only, hand-stamped TOMBSTONE — recorder only, one contradiction
      4 gone: reaped, surveyed, chronicle 0 pages, tombstone claiming BOTH seals, no vault seal — contradiction
      5 tombstoned AND still on the shelf, stamped TOMBSTONE by the deleter — two contradictions
      6 gone: surveyed, both seals, tombstone claiming BOTH — a backed claim, no contradiction
    """

    def __init__(self, clean=False):
        self.tmp = tempfile.mkdtemp(prefix="custody-law-")
        self.hist = os.path.join(self.tmp, "tv", "frames", "hist")
        os.makedirs(self.hist)
        self.stamp = os.path.join(self.tmp, "tv", "river_stamp.jsonl")
        self.w = RC.world(hist=self.hist, stamp_path=self.stamp)
        w = self.w
        if clean:
            _shelf_reel(self.hist, 2)
            _dump(w["retro_triage"], {_reel(2): {"ts": 1700000000002, "full": True, "panels": 4, "frames": 3}})
            _dump(w["chronicle_swept"], {_reel(2): {"ts": 1700000001002, "pages": 3, "promptVer": "p1"}})
            _dump(w["vault_swept"], {_sess(2): {"ts": 1700000002002, "rows": 2, "promptVer": "vp1",
                                                "extracted": ["name", "location", "provenance"]}})
            _dump(w["reel_tombstones"], {"reels": [], "updatedTs": 1})
            self.src = RC.sources(hist=self.hist, stamp_path=self.stamp)
            return
        for n in (1, 2, 3, 5):
            _shelf_reel(self.hist, n)
        _dump(w["retro_triage"], {
            _reel(1): {"ts": 1700000000001, "full": True, "panels": 0, "frames": 3},
            _reel(2): {"ts": 1700000000002, "full": True, "panels": 4, "frames": 3},
            _reel(4): {"ts": 1700000000004, "full": True, "panels": 0, "frames": 9},
            _reel(6): {"ts": 1700000000006, "full": True, "panels": 2, "frames": 9}})
        _dump(w["chronicle_swept"], {
            _reel(2): {"ts": 1700000001002, "pages": 3, "classified": 5, "promptVer": "p1"},
            _reel(4): {"ts": 1700000001004, "pages": 0, "classified": 0, "promptVer": "p1"},
            _reel(6): {"ts": 1700000001006, "pages": 2, "classified": 2, "promptVer": "p1"}})
        _dump(w["vault_swept"], {
            _sess(2): {"ts": 1700000002002, "rows": 2, "promptVer": "vp1",
                       "extracted": ["name", "location", "provenance"]},
            _sess(6): {"ts": 1700000002006, "rows": 0, "promptVer": "vp1", "extracted": [],
                       "examinedEmpty": True, "extractedWhy": "nothing to take"}})
        _dump(w["reel_tombstones"], {"reels": [
            {"reel": _reel(4), "session": _sess(4), "mb": 9.5, "pages": 0, "why": BOTH,
             "deletedTs": 1700000003004, "frames": 9, "startedTs": 1000000000040},
            {"reel": _reel(5), "session": _sess(5), "mb": 1.0, "pages": 0, "why": BOTH,
             "deletedTs": 1700000003005, "frames": 3},
            {"reel": _reel(6), "session": _sess(6), "mb": 2.0, "pages": 2,
             "why": "read (2 pages) and sealed by BOTH lanes", "deletedTs": 1700000003005, "frames": 9},
            # his ledger really holds one reel twice (measured 2026-09-29) — the LAST row is the act, both are counted
            {"reel": _reel(6), "session": _sess(6), "mb": 2.0, "pages": 2,
             "why": "read (2 pages) and sealed by BOTH lanes", "deletedTs": 1700000003006, "frames": 9},
            {"mb": 0.1, "why": "a row that names no reel"},
        ], "updatedTs": 1700000003006})
        _dump(os.path.join(w["witness_root"], "vault_accum.json"),
              {"owned": [{"name": "Grief", "witnesses": [{"session": _sess(2), "frame": "f_1000000000020.jpg"}]}]})
        stamps = [(_reel(1), "INTAKE", "loop:tvd-retro-triage", "observer"),
                  (_reel(1), "TRIAGE", "loop:tvd-retro-triage", "observer"),
                  (_reel(1), "EMPTY", "loop:tvd-retro-triage", "observer"),
                  (_reel(1), "ROUTED", "reel_route_lane", "actor"),
                  (_reel(2), "INTAKE", "fleet", "observer"), (_reel(2), "PRINTER", "fleet", "observer"),
                  (_reel(2), "CAPTURE", "fleet", "observer"),
                  (_reel(3), "TOMBSTONE", "a person at the console", "actor"),
                  (_reel(5), "TOMBSTONE", "reel_retention", "actor")]
        _append(self.stamp, [{"at": 1700000004000 + i, "seq": i + 1, "reel": r, "station": st, "from": None,
                              "by": by, "byKind": k, "why": None} for i, (r, st, by, k) in enumerate(stamps)])
        _append(w["reel_reaps"], [{"ts": 1700000003004, "reel": _reel(4), "frames": 9, "removed": True,
                                   "shelfBefore": 5, "by": "recorder"}])
        _append(w["read_pictures"], [{"ts": 1700000001500, "frameId": "", "why": "disk-full", "freeGb": 0.9,
                                      "session": _sess(2)}])
        self.reads = [
            {"sessionId": _sess(2), "frameId": _reel(2) + "/f_1000000000020.jpg", "names": ["Grief"],
             "ts": 1700000001100},
            {"sessionId": _sess(2), "frameId": _reel(2) + "/f_1000000000099.jpg", "names": ["Shako"],
             "ts": 1700000001200},
            {"sessionId": _sess(9), "frameId": "9_1", "names": ["Nothing"], "ts": 1700000001300}]
        self.plan = {"ok": True,
                     "candidates": [{"reel": _reel(1), "why": "eligible", "tag": "eligible"}],
                     "kept": [{"reel": _reel(2), "why": "newest", "tag": "recent"}]}
        self.src = RC.sources(hist=self.hist, stamp_path=self.stamp)

    def corrupt(self, key):
        with io.open(self.w[key], "w", encoding="utf-8") as fh:
            fh.write("{")
        self.src = RC.sources(hist=self.hist, stamp_path=self.stamp)

    def close(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


def _hand(rec, name):
    return next(h for h in rec["hands"] if h["holder"] == name)


class AReelCarriesItsCustody(unittest.TestCase):

    def setUp(self):
        self.W = World()

    def tearDown(self):
        self.W.close()

    def test_premise_the_world_is_where_each_owner_says(self):
        """Every path the record reads is the OWNER's answer, never a layout joined here."""
        import read_pictures as RP
        import reel_retention as RR
        import retro_triage as RT
        import river_stamp as RS
        w = self.W.w
        base = os.path.realpath(self.W.hist)
        self.assertEqual(w["retro_triage"], RT._store_path(root=base))
        self.assertEqual(w["reel_tombstones"], RR._tombstone_path(base))
        self.assertEqual(w["reel_reaps"], os.path.join(RP.root_of(self.W.hist), RP.REAPS))
        self.assertEqual(w["read_pictures"], os.path.join(RP.root_of(self.W.hist), RP.REFUSALS))
        self.assertEqual(w["river_stamp"], self.W.stamp)
        self.assertEqual(w["witness_root"], os.path.dirname(w["vault_swept"]))
        # with no argument, every owner honours TV_HIST on its own — and so does the world
        # (compared as real paths: macOS spells a temp dir /var and /private/var — one file, two names)
        with mock.patch.dict(os.environ, {"TV_HIST": self.W.hist}):
            w2 = RC.world()
            self.assertEqual(w2["hist"], self.W.hist)
            self.assertEqual(os.path.realpath(w2["river_stamp"]), os.path.realpath(RS._store_path(None)))
            self.assertEqual(os.path.realpath(w2["retro_triage"]), os.path.realpath(RT._store_path()))
        # the premise the rest stands on: nothing in this world was unreadable or absent
        self.assertEqual(self.W.src["unreadable"], [])
        self.assertEqual(sorted(self.W.src["shelf"]), [_reel(1), _reel(2), _reel(3), _reel(5)])

    def test_a_reel_that_reached_the_vault_names_four_hands_and_the_room_it_never_entered(self):
        c = RC.custody(_reel(2), src=self.W.src, plan=self.W.plan)
        self.assertTrue(c["ok"], c)
        self.assertEqual([h["holder"] for h in c["hands"]], list(RC.HOLDERS))
        self.assertEqual(c["entered"], ["recorder", "triage", "printer", "vault"])
        self.assertEqual(c["never"], ["tombstone"])
        self.assertEqual(c["unknown"], [])
        self.assertEqual(c["current"], "vault")
        self.assertEqual(c["contradictions"], [])
        rec = _hand(c, "recorder")
        self.assertIs(rec["held"], True)
        self.assertEqual(rec["frames"], 3)
        self.assertEqual(rec["at"], 1000000000020, "the recorder's clock is the FIRST FRAME, quoted from reel_router")
        self.assertEqual(rec["clock"], "frames")
        self.assertEqual(rec["refusals"], 1, "the recorder's own refusal record for this session")
        tri = _hand(c, "triage")
        self.assertEqual((tri["held"], tri["full"], tri["panels"], tri["at"]), (True, True, 4, 1700000000002))
        pr = _hand(c, "printer")
        self.assertEqual((pr["held"], pr["pages"], pr["at"]), (True, 3, 1700000001002))
        self.assertIsNone(pr["reads"], "no journal was handed in: reads is None (not asked), never 0")
        va = _hand(c, "vault")
        self.assertEqual((va["held"], va["verdict"], va["rows"]), (True, "COVERED", 2))
        self.assertIs(va["cited"], True, "the durable stores cite this session — his §26, a cited frame is never drained")
        to = _hand(c, "tombstone")
        self.assertIs(to["held"], False)
        self.assertEqual(to["intent"], {"say": "kept", "tag": "recent", "why": "newest"},
                         "the deleter's CURRENT intent is quoted from the plan and labelled as intent")
        self.assertEqual(c["journey"]["current"], "CAPTURE")
        self.assertEqual(c["journey"]["n"], 3)
        for h in c["hands"]:
            self.assertIn(h["holder"], RC.WRITER)
            self.assertEqual(h["by"], RC.WRITER[h["holder"]], "every hand names its writer")

    def test_a_recorder_only_reel_names_the_rooms_it_never_entered(self):
        c = RC.custody(_reel(3), src=self.W.src)
        self.assertEqual(c["entered"], ["recorder"])
        self.assertEqual(c["never"], ["triage", "printer", "vault", "tombstone"])
        self.assertEqual(c["current"], "recorder")
        # its only stamp was a hand's, at TOMBSTONE, and no ledger row backs it
        self.assertEqual(c["journey"]["current"], "TOMBSTONE")
        kinds = [k["kind"] for k in c["contradictions"]]
        self.assertEqual(kinds, ["stamped-tombstone-no-ledger-row"])
        k = c["contradictions"][0]
        self.assertIn("a person at the console", k["left"]["who"])
        self.assertEqual(k["right"]["who"], RC.WRITER["tombstone"])

    def test_a_tombstone_that_claims_both_seals_is_contradicted_by_the_seal_stores(self):
        c = RC.custody(_reel(4), src=self.W.src)
        self.assertEqual(c["entered"], ["triage", "printer", "tombstone"])
        self.assertEqual(c["never"], ["recorder", "vault"])
        self.assertEqual(c["current"], "tombstone")
        rec = _hand(c, "recorder")
        self.assertIs(rec["held"], False)
        self.assertIs(rec["removedByReaper"], True)
        self.assertIn("reaper removed it", rec["why"])
        to = _hand(c, "tombstone")
        self.assertIs(to["claimsBothSeals"], True)
        self.assertEqual(to["at"], 1700000003004)
        kinds = [k["kind"] for k in c["contradictions"]]
        self.assertEqual(kinds, ["tombstone-claims-seals"])
        k = c["contradictions"][0]
        self.assertEqual(k["left"]["who"], RC.WRITER["tombstone"])
        self.assertIn(RC.BOTH_LANES, k["left"]["says"])
        self.assertIn("vault_swept.json holds no seal", k["right"]["says"])
        self.assertNotIn("chronicle_swept.json", k["right"]["says"],
                         "the chronicle seal EXISTS (0 pages) — only the missing hand is named")
        self.assertIn("1 contradiction", c["why"])

    def test_the_deleters_measured_sentence_claims_only_the_seals_it_held(self):
        """REG-3293 - the eligible sentence names the seals it held: a 'chronicle only' release of a reel with no vault
        seal claims nothing false; a 'chronicle and vault' one whose vault seal is gone is still caught."""
        import reel_retention as RR
        rows = json.load(io.open(self.W.w["reel_tombstones"], encoding="utf-8"))
        for r in rows["reels"]:
            if r.get("reel") == _reel(4):
                r["why"] = "read (0 pages); seals held: chronicle only - it has given up its information"
        _dump(self.W.w["reel_tombstones"], rows)
        src = RC.sources(hist=self.W.hist, stamp_path=self.W.stamp)
        c = RC.custody(_reel(4), src=src)
        self.assertIs(_hand(c, "tombstone")["claimsBothSeals"], False)
        self.assertEqual([k["kind"] for k in c["contradictions"]], [], "a true one-seal sentence was called a lie")
        for r in rows["reels"]:
            if r.get("reel") == _reel(4):
                r["why"] = "read (0 pages); %s - it has given up its information" % RR.SEALS_BOTH
        _dump(self.W.w["reel_tombstones"], rows)
        c = RC.custody(_reel(4), src=RC.sources(hist=self.W.hist, stamp_path=self.W.stamp))
        self.assertEqual([k["kind"] for k in c["contradictions"]], ["tombstone-claims-seals"],
                         "a both-seals sentence over a missing vault seal went unread")

    def test_a_removal_the_shelf_still_shows_is_a_contradiction(self):
        c = RC.custody(_reel(5), src=self.W.src)
        self.assertEqual(c["entered"], ["recorder", "tombstone"])
        kinds = sorted(k["kind"] for k in c["contradictions"])
        self.assertEqual(kinds, ["deleted-but-present", "tombstone-claims-seals"])
        both = next(k for k in c["contradictions"] if k["kind"] == "tombstone-claims-seals")
        self.assertIn("vault_swept.json holds no seal for it and chronicle_swept.json holds no seal for it",
                      both["right"]["says"])
        # the deleter's own stamp is not a contradiction: the ledger row backs it
        self.assertEqual(c["journey"]["current"], "TOMBSTONE")

    def test_a_backed_claim_is_no_contradiction_and_the_door_is_quoted(self):
        c = RC.custody(_reel(6), src=self.W.src)
        self.assertEqual(c["entered"], ["triage", "printer", "vault", "tombstone"])
        self.assertEqual(c["never"], ["recorder"])
        self.assertEqual(c["contradictions"], [])
        to = _hand(c, "tombstone")
        self.assertIs(to["claimsBothSeals"], True)
        self.assertEqual(to["at"], 1700000003006, "the LAST ledger row is the act")
        self.assertEqual(to["ledgerRows"], 2, "a reel the ledger records as removed twice says so")
        self.assertIn("removed 2 times", to["why"])
        self.assertEqual(_hand(RC.custody(_reel(4), src=self.W.src), "tombstone")["ledgerRows"], 1)
        self.assertEqual(to["door"]["say"], "QUALIFIED", to["door"])
        self.assertEqual(to["door"]["door"], "semantic", "end_routes' verdict is quoted, never re-derived")
        self.assertEqual(_hand(c, "vault")["verdict"], "EMPTY")
        self.assertIsNone(c["journey"]["current"], "never stamped: None because nobody looked, not nowhere")
        self.assertIn("never been walked", c["journey"]["why"])

    def test_an_unreadable_store_leaves_that_hand_unknown_and_raises_no_contradiction(self):
        self.W.corrupt("vault_swept")
        self.assertEqual(self.W.src["unreadable"], ["vault_swept.json"])
        c = RC.custody(_reel(4), src=self.W.src)
        self.assertEqual(c["unknown"], ["vault"])
        self.assertIsNone(_hand(c, "vault")["held"])
        self.assertNotIn("vault", c["never"], "an unreadable store is not a room measured empty")
        self.assertEqual(c["contradictions"], [],
                         "the tombstone's claim cannot be contradicted by a store nobody could read")
        self.assertIn("vault_swept.json", c["why"])
        self.assertIn("UNKNOWN", c["why"])
        self.assertEqual(c["unreadable"], ["vault_swept.json"])
        st, why = RC.doctor(src=self.W.src)
        self.assertEqual(st, RC.UNKNOWN)
        self.assertIn("vault_swept.json", why)

    def test_a_reel_no_store_records_is_none_yet_not_nowhere(self):
        c = RC.custody(_reel(7), src=self.W.src)
        self.assertTrue(c["ok"])
        self.assertEqual(c["entered"], [])
        self.assertEqual(c["never"], list(RC.HOLDERS))
        self.assertIsNone(c["current"])
        self.assertIn("none yet, not nowhere", c["why"])
        # a bare session id is the same reel, never re-prefixed
        c2 = RC.custody(_sess(2), src=self.W.src)
        self.assertEqual((c2["reel"], c2["session"]), (_reel(2), _sess(2)))
        self.assertEqual(RC.custody("", src=self.W.src)["ok"], False)

    def test_the_journal_hands_the_printer_its_reads_and_their_pictures(self):
        c = RC.custody(_reel(2), src=self.W.src, reads=self.W.reads)
        rd = _hand(c, "printer")["reads"]
        self.assertEqual(rd["n"], 2, "only the reads that named something IN THIS REEL")
        self.assertEqual(rd["names"], ["Grief", "Shako"])
        self.assertEqual((rd["firstTs"], rd["lastTs"]), (1700000001100, 1700000001200))
        self.assertEqual((rd["pictures"]["onDisk"], rd["pictures"]["gone"], rd["pictures"]["unknown"]), (1, 1, 0))
        self.assertEqual(len(rd["pictures"]["goneWhy"]), 1)
        self.assertIn("f_1000000000099", rd["pictures"]["goneWhy"][0])
        self.assertIn("UNKNOWN", rd["pictures"]["goneWhy"][0], "no deleter recorded taking it — who_took's words")
        # an empty journal is a measured zero; no journal is not asked
        self.assertEqual(_hand(RC.custody(_reel(2), src=self.W.src, reads=[]), "printer")["reads"]["n"], 0)
        self.assertIsNone(_hand(RC.custody(_reel(2), src=self.W.src, reads=None), "printer")["reads"])

    def test_the_census_counts_every_reel_and_never_hides_one_behind_the_cap(self):
        cen = RC.census(src=self.W.src, plan=self.W.plan, limit=2)
        self.assertTrue(cen["ok"], cen)
        self.assertEqual((cen["n"], cen["shelf"], cen["tombstoned"]), (6, 4, 3))
        self.assertEqual(len(cen["rows"]), 2)
        self.assertIs(cen["truncated"], True)
        self.assertEqual(sum(cen["byCurrent"].values()), 6, "the counts are over ALL reels, not the drawn rows")
        self.assertEqual(cen["byCurrent"], {"triage": 1, "vault": 1, "recorder": 1, "tombstone": 3})
        self.assertEqual((cen["contradicted"], cen["contradictions"]), (3, 4))
        self.assertEqual((cen["duplicateTombstones"], cen["namelessTombstones"]), (1, 1))
        self.assertIn("1 reel(s) tombstoned more than once", cen["why"])
        self.assertEqual(cen["byKind"], {"stamped-tombstone-no-ledger-row": 1, "tombstone-claims-seals": 2,
                                         "deleted-but-present": 1})
        self.assertIn("2 of 6 rows drawn", cen["why"])
        full = RC.census(src=self.W.src, limit=1000)
        self.assertIs(full["truncated"], False)
        self.assertEqual([r["reel"] for r in full["rows"]], [_reel(n) for n in (1, 2, 3, 4, 5, 6)])
        row5 = next(r for r in full["rows"] if r["reel"] == _reel(5))
        self.assertEqual(row5["station"], "TOMBSTONE")
        self.assertEqual(sorted(row5["contradictions"]), ["deleted-but-present", "tombstone-claims-seals"])

    def test_the_doctor_row_names_the_contradictions_and_its_denominators(self):
        st, why = RC.doctor(src=self.W.src)
        self.assertEqual(st, RC.MISSING)
        self.assertIn("3 of 6 reel(s)", why)
        self.assertIn("tombstone-claims-seals ×2", why)
        self.assertIn(_reel(3), why, "the first contradicted reel is named")
        clean = World(clean=True)
        try:
            st, why = RC.doctor(src=clean.src)
            self.assertEqual(st, RC.OK, why)
            self.assertIn("1 reel(s) (1 on the shelf, 0 tombstoned)", why)
            cen = RC.census(src=clean.src)
            self.assertEqual((cen["n"], cen["contradicted"]), (1, 0))
            self.assertEqual((cen["duplicateTombstones"], cen["namelessTombstones"]), (0, 0),
                             "counted and none — 0, never None, over a ledger that was read")
        finally:
            clean.close()
        empty = tempfile.mkdtemp(prefix="custody-empty-")
        try:
            h = os.path.join(empty, "tv", "frames", "hist")
            os.makedirs(h)
            src = RC.sources(hist=h, stamp_path=os.path.join(empty, "tv", "river_stamp.jsonl"))
            st, why = RC.doctor(src=src)
            self.assertEqual(st, RC.OK, why)
            self.assertIn("0 of 0", why, "a clean chain over nothing says its denominator")
            self.assertEqual(sorted(src["absent"])[:2], ["chronicle_swept.json", "read_pictures.jsonl"])
        finally:
            shutil.rmtree(empty, ignore_errors=True)


class TheDoctorNamesTheFirstPastTheCap(unittest.TestCase):
    """v3526 (#231 second eye on v3525): the doctor named "the first" contradicted reel from the census ROWS, which
    stop at the draw cap (1000) while `contradicted` counts every reel — so past the cap it said 'first: ?'."""

    def test_the_first_contradiction_is_named_past_the_draw_cap(self):
        names = ["reel_s_%04d" % i for i in range(1200)]

        def fake(nm, src=None, reads=None, plan=None, list_frames=False):
            return {"current": "SHELF", "entered": None, "never": [], "unknown": [], "journey": {},
                    "contradictions": ([{"kind": "shelf-and-tomb"}] if nm == names[-1] else [])}
        src = {"shelf": names, "tombByReel": {}, "ledgerState": "ok", "unreadable": [], "absent": [],
               "tombRowsByReel": {}, "tombNameless": 0}
        with mock.patch.object(RC, "custody", fake):
            state, why = RC.doctor(src=src)
        self.assertEqual(state, RC.MISSING, why)
        self.assertIn("first: reel_s_1199 (shelf-and-tomb)", why)
        self.assertNotIn("first: ?", why)


class TheConsoleServesTheCustody(unittest.TestCase):

    def setUp(self):
        self.W = World()

    def tearDown(self):
        self.W.close()

    def _get(self, path, journal=None, plan=None, sources=None):
        import control_app as CA
        import reel_retention as RR
        got = {}
        h = CA.Handler.__new__(CA.Handler)
        h.path = path
        h.headers = {}
        h._json = lambda code, obj: got.update(code=code, body=json.loads(json.dumps(obj, default=str)))
        with mock.patch.object(RC, "sources", sources or (lambda *a, **k: self.W.src)), \
                mock.patch.object(CA, "_kai_journal_rows",
                                  journal or (lambda want_why=False: ((self.W.reads, None) if want_why else self.W.reads))), \
                mock.patch.object(RR, "plan", plan or (lambda *a, **k: self.W.plan)):
            h.do_GET()
        return got

    def test_the_console_serves_one_reels_custody_with_the_journal_and_the_plan_handed_in(self):
        got = self._get("/api/custody?reel=%s" % _reel(2))
        self.assertEqual(got.get("code"), 200, got)
        b = got["body"]
        self.assertTrue(b.get("ok"), b)
        self.assertEqual(b["reel"], _reel(2))
        self.assertEqual(b["current"], "vault")
        pr = next(hh for hh in b["hands"] if hh["holder"] == "printer")
        self.assertIsNotNone(pr["reads"], "the console did not hand the journal in — reads arrived as not-asked")
        self.assertEqual(pr["reads"]["n"], 2, "the console handed the journal in")
        to = next(hh for hh in b["hands"] if hh["holder"] == "tombstone")
        self.assertEqual(to["intent"]["say"], "kept", "the console handed reel_retention.plan in")
        # a bare session id is accepted on the wire too
        self.assertEqual(self._get("/api/custody?reel=%s" % _sess(4))["body"]["current"], "tombstone")

    def test_an_unreadable_journal_is_not_asked_never_no_reads(self):
        got = self._get("/api/custody?reel=%s" % _reel(2),
                        journal=lambda want_why=False: (([], "the journal would not read") if want_why else []))
        pr = next(hh for hh in got["body"]["hands"] if hh["holder"] == "printer")
        self.assertIsNone(pr["reads"], "an unreadable journal must reach the record as None, not 0 reads")

    def test_the_console_serves_the_census_and_honours_the_cap(self):
        got = self._get("/api/custody?limit=2")
        b = got["body"]
        self.assertTrue(b.get("ok"), b)
        self.assertEqual((b["n"], len(b["rows"]), b["truncated"]), (6, 2, True))
        self.assertEqual(b["contradicted"], 3)
        got = self._get("/api/custody")
        self.assertEqual(len(got["body"]["rows"]), 6)

    def test_the_console_says_why_when_the_record_cannot_be_assembled(self):
        def boom(*a, **k):
            raise RuntimeError("no world")
        got = self._get("/api/custody?reel=%s" % _reel(2), sources=boom)
        self.assertEqual(got.get("code"), 200)
        self.assertIs(got["body"].get("ok"), False)
        self.assertIn("could not be assembled", got["body"]["why"])
        self.assertIn("no world", got["body"]["why"])

    def test_a_plan_that_will_not_answer_leaves_the_intent_unknown(self):
        def boom(*a, **k):
            raise RuntimeError("plan down")
        got = self._get("/api/custody?reel=%s" % _reel(2), plan=boom)
        to = next(hh for hh in got["body"]["hands"] if hh["holder"] == "tombstone")
        self.assertEqual(to["intent"]["say"], "UNKNOWN")
        self.assertIn("RuntimeError", to["intent"]["why"], "the console names what would not answer")


class TheRowIsOnTheHeart(unittest.TestCase):

    def test_the_row_is_registered_and_hands_the_record_through(self):
        import console_doctor as D
        import corroborate as C
        self.assertIn("reel custody", dict(D.CHECKS))
        self.assertIn("reel custody", D.WATCHES)
        self.assertTrue("reel custody" in C.NO_JOINT_YET or "reel custody" in C.COVERED_BY,
                        "the row must be explained in corroborate's registry")
        W = World()
        try:
            self.assertEqual(D._check_reel_custody(src=W.src), RC.doctor(src=W.src))
            self.assertEqual(D._check_reel_custody(src=W.src)[0], D.MISSING)
        finally:
            W.close()
        with mock.patch.object(RC, "doctor", side_effect=RuntimeError("no stores")):
            st, why = D._check_reel_custody()
        self.assertEqual(st, D.UNKNOWN)
        self.assertIn("RuntimeError", why)


RED_PROOF = [
    {"why": "REG-3293 - custody never reads the deleter's measured both-seals sentence as a claim",
     "file": "tv/reel_custody.py",
     "find": " or _rr_s.SEALS_BOTH in str(why_txt))\n",
     "replace": ")\n",
     "matches": 1},
    {
        "why": "v3526 - the doctor names the first contradiction from the capped rows again ('first: ?')",
        "file": "tv/reel_custody.py",
        "find": "        first = c.get(\"firstContradicted\") or next((r for r in c[\"rows\"] if r[\"contradictions\"]), None)\n",
        "replace": "        first = next((r for r in c[\"rows\"] if r[\"contradictions\"]), None)\n",
        "matches": 1,
    },
    {
        "why": "dropping the claim check lets a tombstone that names seals the stores never wrote pass as clean",
        "file": "reel_custody.py",
        "find": '    if t["held"] is True and t.get("claimsBothSeals") is True:\n',
        "replace": '    if False and t.get("claimsBothSeals") is True:\n',
        "matches": 1,
    },
    {
        "why": "an unreadable store read as a room measured empty: None collapsed into False, and a contradiction is raised on a store nobody could open",
        "file": "reel_custody.py",
        "find": '    if state == "unreadable":\n        return None, None\n',
        "replace": '    if state == "unreadable":\n        return None, False\n',
        "matches": 1,
    },
    {
        "why": "the console stops handing the journal in, so the printer never learns its reads (not asked wearing the shape of a route that answers)",
        "file": "control_app.py",
        "find": "                    self._json(200, _rcu.custody(_creel, src=_csrc, reads=(None if _cjwhy else _crows),\n",
        "replace": "                    self._json(200, _rcu.custody(_creel, src=_csrc, reads=None,\n",
        "matches": 1,
    },
    {
        "why": "the doctor row reads OK over reels whose writers contradict each other",
        "file": "reel_custody.py",
        "find": '        return MISSING, ("%d of %d reel(s) carry a custody contradiction (%s) — first: %s (%s). Two writers "\n',
        "replace": '        return OK, ("%d of %d reel(s) carry a custody contradiction (%s) — first: %s (%s). Two writers "\n',
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
