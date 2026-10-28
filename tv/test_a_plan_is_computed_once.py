# -*- coding: utf-8 -*-
"""REG-1410..1414 (#66) — ON A CONSOLE, reel_retention.plan() IS COMPUTED ONCE, AND NEVER SERVED STALE.

HIS WORDS: "the windows needs proper care and attention.. its needs to work perfectly and smoothly there".

MEASURED on his ALT (Windows + Boosteroid, ~30 reels, ~21,000 frames) right after v3522 landed, with py-spy
dumps of the console:
  (A) ~15 min of /api/status at 11 s, then timeouts: ONE hot thread, tvd-eagle-watch, held the GIL in
      frame_authority.test_referenced_reels -> _executable_only -> tokenize over EVERY tv/*.py, reached through
      reel_retention.plan(). That scan's key moves on every ship, so every ship paid it again.
  (B) then /api/river timed out at 90 s: THREE threads (tvd-retro-triage, tvd-eagle-watch, an HTTP request) were
      each inside frame_ref.Index.__init__ at the same moment. plan() is called from ~62 places and remembered
      nothing, so every lane re-listed the whole shelf and rebuilt the proof set from scratch, concurrently.

On an ALT-shaped fixture here (31 reels, 21,205 files; 3 plan() callers + reel_story.story at once), v3522:
cold 114-154 s (7,232 files tokenized, 4 index builds, 284 folder listings), warm 4.6 s. After: cold 0.69 s (1 index
build, 0 tokenized), unchanged 0.02 s (0 builds, 0 listings), a live frame landing 0.58 s (only the live folder
re-listed), and all five rounds' plans byte-identical to v3522's.

  · DRIVEN: 4 concurrent callers -> ONE computation and one index build; every answer a private copy.
  · DRIVEN: plan() and plan(<the same tree>) - reel_story's call and _vault_owed_reels' - are ONE computation
    while each ledger has one copy, and two when HERE and hist both hold one (the order then decides the answer).
  · DRIVEN: an unchanged world is served and lists no folder; OFF the console nothing is remembered.
  · DRIVEN, DIFFERENTIAL: every input plan() reads is moved in turn - each ledger, the triage store, the evidence,
    the tombstone, a durable store, a reel's index.json rewritten IN PLACE, a frame added, a reel removed, a nested
    folder, the ratchet - and after each the console's answer must equal a from-scratch answer, and must have
    been recomputed. A memo that serves a stale "may delete" is worse than none.
  · DRIVEN: an input that moved less than RACY_S ago is computed fresh and never kept; only a changed folder is
    listed again; a folder holding a write in flight (*.tmp) is never kept.
  · DRIVEN: the console path never tokenizes a test file; a ratchet that will not read falls back to the exact
    scan (UNKNOWN is not empty); exact=True always scans.
  · DRIVEN: reel_router's filmed-at reads the same kept listing (one more whole-shelf walk per route()).
  · JOINED: the ratchet law asks for the exact set.

THE ADVERSARIAL REVIEW OF alt-speed (8b5ecd0a), each finding reproduced and then DRIVEN here:
  · REG-1436 DRIVEN: control_app.main() runs its boot prefix under stubs on a fixture shelf - nothing it asks
    before the mark may reach the exact scan. The co_names check this replaces stayed green with the mark one
    line too late: status_payload() for the boot banner reached plan() -> the tokenize scan, once per ship.
  · REG-1437 DRIVEN: while a writer drops a loose frame into hist every 0.2 s (his footage writer, ~1 s), no
    input is ever still, so nothing may be remembered - but concurrent callers share one run, and none is handed
    a run that began before its own call: each answer equals a from-scratch plan taken after that call began.
  · REG-1438 DIFFERENTIAL: a loose frame at hist root whose STEM a citation names flips its reel between
    holds-proof and eligible, and only hist's own folder key sees it arrive or leave.
  · REG-1439 DRIVEN: on a console whose ratchet will not read, the exact scan decides the fixture set from files
    the fingerprint does not cover - so no plan is kept, and an edited test moves the next answer.
  · REG-1440 (docs) the working-tree gap is stated in frame_authority.test_referenced_reels.
RED_PROOF below.
"""
import ast
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import fixture_tmp as _fx_tmp  # noqa: E402  #171 — this run's scratch dirs leave with it
_fx_tmp.contain()

_WORLD = tempfile.mkdtemp(prefix="plan-once-")
os.environ["TV_HIST"] = os.path.join(_WORLD, "hist")      # before anything resolves a store path

import frame_authority as FA  # noqa: E402
import frame_ref as FR  # noqa: E402
import reel_retention as RR  # noqa: E402

STILL_S = 0.25          # the law's RACY_S: short, so a case settles in a third of a second
T0 = 1500000000000      # 2017 - no recording carries it, and no literal id is written in this file


def _reel(i):
    return "reel_s_%d_%d" % (T0 + i * 3600000, 20000 + i)


def _frame(i, j):
    return "f_%d.jpg" % (T0 + i * 3600000 + j * 1000)


def _dump(path, blob):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(blob, fh, sort_keys=True)


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _settle():
    time.sleep(STILL_S + 0.15)


def _strip(p):
    q = dict(p)
    q.pop("hist", None)
    return json.dumps(q, sort_keys=True)


class _World(unittest.TestCase):
    """14 reels plus one the ratchet pins. The 7 oldest carry the verdicts; the newest 8 are the recent shield.

        r0 eligible · r1 never-chronicle-swept · r2 rows-not-banked · r3 eligible (a chronicle focus owes the vault
        nothing) · r4 eligible · r5 holds-proof · r6 eligible · r7..r13 + the pinned reel: recent / test-fixture
    """

    # SIZED FROM THE WINDOW: six reels older than the newest KEEP_RECENT, which the cases name (r0..r5). A literal 14
    # was 8 + 6 and went red the day his window became 16 (2026-09-29, REG-1433) - every reel read "recent".
    N = RR.KEEP_RECENT + 6

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="world-", dir=_WORLD)
        self.hist = os.path.join(self.root, "hist")
        self.tv = os.path.join(self.root, "tv")
        os.makedirs(self.hist)
        os.makedirs(self.tv)
        self._keep = (os.environ.get("TV_HIST"), RR.HERE, FR.RACY_S, FR.on_console_path(), FA.RATCHET_PATH,
                      RR.proof_reels, FA._executable_only, FA.HERE)
        os.environ["TV_HIST"] = self.hist
        RR.HERE = self.tv
        FR.RACY_S = STILL_S
        FR._forget_listings()
        RR._forget_plans()
        # the ratchet the console reads: a private copy, so a case may edit it
        self.ratchet = os.path.join(self.root, "test_reel_refs.json")
        shutil.copyfile(self._keep[4], self.ratchet)
        FA.RATCHET_PATH = self.ratchet
        self.pinned = sorted(_load(self.ratchet)["accepted"])[3]
        self.reels = [_reel(i) for i in range(self.N)]
        chron, vault, tri = {}, {}, {}
        for i, r in enumerate(self.reels):
            d = os.path.join(self.hist, r)
            os.makedirs(d)
            for j in range(30):
                with open(os.path.join(d, _frame(i, j)), "wb") as fh:
                    fh.write(b"\xff\xd8" + b"x" * (40 + j))
            _dump(os.path.join(d, "index.json"), {"focus": "chronicle-uniques" if i == 3 else "stash"})
            sid = r[len("reel_"):]
            if i != 1:
                chron[r] = {"pages": 3}
            if i not in (1, 3):
                vault[sid] = {"rows": 2 if i == 2 else 0}
            if i != 3:
                tri[r] = {"full": True, "panels": 5 if i == 1 else 0, "kinds": {"stash": 1}}
        d = os.path.join(self.hist, self.pinned)
        os.makedirs(d)
        with open(os.path.join(d, "f_1.jpg"), "wb") as fh:
            fh.write(b"pin")
        _dump(os.path.join(d, "index.json"), {"focus": "stash"})
        chron[self.pinned] = {"pages": 2}
        _dump(os.path.join(self.hist, "chronicle_swept.json"), chron)
        _dump(os.path.join(self.hist, "vault_swept.json"), vault)
        _dump(os.path.join(self.hist, "retro_triage.json"), tri)
        _dump(os.path.join(self.hist, "chron_evidence.json"),
              {"uniques": {"Shako": [{"reel": self.reels[5], "frame": "%s/%s" % (self.reels[5], _frame(5, 3)[:-4])}]},
               "sets": {}})
        _dump(os.path.join(self.tv, "vault_accum.json"), {"owned": []})
        _dump(os.path.join(self.tv, "vault_seen.json"), {"rows": [{"witnesses": [{"session": "nobody"}]}]})
        FR.mark_console_path(True)
        _settle()

    def tearDown(self):
        (tvh, here, racy, console, ratchet, proof, exe, fahere) = self._keep
        if tvh is None:
            os.environ.pop("TV_HIST", None)
        else:
            os.environ["TV_HIST"] = tvh
        RR.HERE, FR.RACY_S, FA.RATCHET_PATH = here, racy, ratchet
        RR.proof_reels, FA._executable_only, FA.HERE = proof, exe, fahere
        FR.mark_console_path(console)
        FR._forget_listings()
        RR._forget_plans()
        shutil.rmtree(self.root, True)

    def fresh(self):
        """The from-scratch answer: no kept listing, no kept plan, computed now."""
        FR._forget_listings()
        with RR._PLAN_LOCK:
            RR._PLAN_MEMO.clear()
        return RR.plan(self.hist, _fresh=True)

    def tags(self, p):
        return dict((c["reel"], c["tag"]) for c in (p.get("candidates") or []) + (p.get("kept") or []))

    def tiny_repo(self):
        """Point the EXACT scan at a one-file repo, so a case can take that path without tokenizing 1,800 files."""
        repo = os.path.join(self.root, "repo")
        os.makedirs(os.path.join(repo, "tv"))
        self.named = "reel_s_%d_%d" % (T0 + 77, 7)
        with open(os.path.join(repo, "tv", "test_tiny.py"), "w", encoding="utf-8") as fh:
            fh.write("R = %r\n" % self.named)
        FA.HERE = os.path.join(repo, "tv")
        FA.__dict__.pop("_FIXTURE_CACHE", None)
        self.addCleanup(FA.__dict__.pop, "_FIXTURE_CACHE", None)
        n = []
        real = self._keep[6]

        def counting(*a, **k):
            n.append(1)
            return real(*a, **k)
        FA._executable_only = counting
        return n


class ConcurrentCallersShareOneComputation(_World):

    def test_four_callers_one_computation_one_index(self):
        real = RR.proof_reels

        def slow(h):
            time.sleep(0.4)            # hold the leader open long enough that every caller arrives during it
            return real(h)
        RR.proof_reels = slow
        builds0 = FR.LIST_STATS["builds"]
        gate = threading.Barrier(4)
        out, errs = [None] * 4, []

        def go(i):
            try:
                gate.wait(5)
                out[i] = RR.plan(self.hist)
            except Exception as e:
                errs.append(repr(e))
        ths = [threading.Thread(target=go, args=(i,)) for i in range(4)]
        for t in ths:
            t.start()
        for t in ths:
            t.join(30)
        self.assertEqual(errs, [])
        s = dict(RR.PLAN_STATS)
        self.assertEqual((s["runs"], s["led"], s["joined"]), (1, 1, 3),
                         "4 concurrent callers ran plan() %d time(s) - each lane is rebuilding the proof set from "
                         "scratch again (his ALT: three index walks at once, /api/river past 90 s): %r" % (s["runs"], s))
        self.assertEqual(FR.LIST_STATS["builds"] - builds0, 1, "the frame index was built more than once")
        self.assertTrue(all(_strip(o) == _strip(out[0]) for o in out), "the callers were handed different answers")
        RR.proof_reels = real
        self.assertEqual(_strip(out[0]), _strip(self.fresh()), "the shared answer is not the answer plan() computes")
        out[1]["candidates"].append({"reel": "edited"})
        out[1]["coverage"]["eligible"] = -1
        self.assertNotIn({"reel": "edited"}, out[2]["candidates"], "two callers were handed the SAME object")
        again = RR.plan(self.hist)
        self.assertNotIn({"reel": "edited"}, again["candidates"], "a caller's edit reached the kept answer")
        self.assertNotEqual(again["coverage"]["eligible"], -1)


class AnUnchangedWorldIsServed(_World):

    def test_served_without_listing_a_folder(self):
        first = RR.plan(self.hist)
        listed0, builds0, runs0 = FR.LIST_STATS["listed"], FR.LIST_STATS["builds"], RR.PLAN_STATS["runs"]
        second = RR.plan(self.hist)
        self.assertEqual(RR.PLAN_STATS["runs"], runs0, "an unchanged world was computed again")
        self.assertEqual(RR.PLAN_STATS["served"], 1)
        self.assertEqual((FR.LIST_STATS["listed"] - listed0, FR.LIST_STATS["builds"] - builds0), (0, 0),
                         "serving an unchanged world still listed folders or built an index")
        self.assertEqual(_strip(first), _strip(second))

    def test_off_the_console_nothing_is_remembered(self):
        FR.mark_console_path(False)
        n = self.tiny_repo()
        RR.plan(self.hist)
        self.assertGreater(len(n), 0, "off the console the fixture set must come from the EXACT scan")
        listed = FR.LIST_STATS["listed"]
        RR.plan(self.hist)
        self.assertEqual((RR.PLAN_STATS["runs"], RR.PLAN_STATS["served"], RR.PLAN_STATS["off"]), (2, 0, 2),
                         "a law, the gate or CI was served a remembered plan: %r" % RR.PLAN_STATS)
        self.assertEqual(FR.LIST_STATS["listed"], listed, "off the console the listing memory must not even count")
        self.assertEqual(FR._LISTINGS, {}, "off the console a listing was kept")


class TwoCallShapesOneTree(_World):
    """_vault_owed_reels calls plan(<hist>); reel_story calls plan(). On his ALT those were two of the three threads
    walking the shelf at once. With one copy of each ledger they are ONE question; with two they are not."""

    def _as_his_console(self):
        import retro_triage as RT
        keep = (os.environ.pop("TV_HIST", None), RR._resolve_hist, RT._store_path)
        RR._resolve_hist = lambda h: h or self.hist               # his console: plan() resolves to the same shelf
        RT._store_path = lambda root=None: os.path.join(self.hist, "retro_triage.json")

        def undo():
            if keep[0] is not None:
                os.environ["TV_HIST"] = keep[0]
            RR._resolve_hist, RT._store_path = keep[1], keep[2]
        self.addCleanup(undo)

    def test_one_copy_one_computation(self):
        self._as_his_console()
        a = RR.plan()
        b = RR.plan(self.hist)
        self.assertEqual((RR.PLAN_STATS["runs"], RR.PLAN_STATS["served"]), (1, 1),
                         "plan() and plan(<the same tree>) were computed separately: %r" % RR.PLAN_STATS)
        self.assertEqual(_strip(a), _strip(b))
        self.assertEqual(_strip(b), _strip(self.fresh()))

    def test_two_copies_two_answers(self):
        self._as_his_console()
        _dump(os.path.join(self.tv, "chronicle_swept.json"), {})     # HERE's copy says: nothing was ever read
        _settle()
        a = RR.plan()
        b = RR.plan(self.hist)
        self.assertEqual(RR.PLAN_STATS["runs"], 2, "with BOTH ledger copies present the two call shapes read "
                                                   "different copies first, and one was served the other's answer")
        FR._forget_listings()
        want_a = RR.plan(_fresh=True)
        FR._forget_listings()
        want_b = RR.plan(self.hist, _fresh=True)
        self.assertNotEqual(_strip(want_a), _strip(want_b), "PREMISE: the two copies do not change the answer")
        self.assertEqual((_strip(a), _strip(b)), (_strip(want_a), _strip(want_b)))


class EveryInputMovesTheAnswer(_World):
    """The differential: after each move the console's answer == a from-scratch answer, and it was recomputed."""

    def _moves(self):
        h, tv, r = self.hist, self.tv, self.reels

        def ledger(fn, fix):
            p = os.path.join(h, fn)
            b = _load(p)
            fix(b)
            _dump(p, b)

        def vault_rows(b):
            b[r[4][len("reel_"):]]["rows"] = 7                       # same byte length: 0 -> 7

        def chron_drop(b):
            b.pop(r[6], None)

        def triage(b):
            b[r[0]]["panels"] = 9                                     # same byte length: 0 -> 9

        def cite(b):
            # by BARE stem, as a citation may be: the loose-frame moves below turn on how that stem resolves
            b["uniques"]["Harlequin Crest"] = [{"reel": r[6], "frame": _frame(6, 2)[:-4]}]

        def loose_dup():
            # REG-1438 - the footage writer's own layout: a loose hist/f_<ms>.jpg, here the same capture the
            # citation above names by stem. It now resolves to the loose copy, so r6 no longer holds the proof.
            with open(os.path.join(h, _frame(6, 2)), "wb") as fh:
                fh.write(b"\xff\xd8dup")

        def loose_gone():
            os.remove(os.path.join(h, _frame(6, 2)))                  # folded or pruned: ONLY hist's stamp moves

        def tomb():
            d = os.path.join(h, r[7])
            keep = sorted(_fx_tmp.list_own(d))[:2]
            for f in _fx_tmp.list_own(d):
                if f not in keep:
                    os.remove(os.path.join(d, f))
            _dump(os.path.join(self.root, "reel_tombstones.json"), {"reels": [{"reel": r[7], "kept": keep}]})

        def durable():
            _dump(os.path.join(tv, "vault_accum.json"),
                  {"owned": [{"name": "Shako", "witnesses": [{"session": r[2][len("reel_"):], "frame": "x.jpg"}]}]})

        def index_in_place():
            # rewritten IN PLACE (no .tmp, no rename): the reel folder's own stamp does not move
            with open(os.path.join(h, r[3], "index.json"), "r+", encoding="utf-8") as fh:
                fh.seek(0)
                fh.write(json.dumps({"focus": "stash"}))
                fh.truncate()

        def frame_added():
            with open(os.path.join(h, r[8], _frame(8, 99)), "wb") as fh:
                fh.write(b"y" * 200000)                               # a plan's `mb` is rounded to 0.1 MB

        def reel_removed():
            shutil.rmtree(os.path.join(h, r[9]))

        def nested():
            os.makedirs(os.path.join(h, r[10], "deep"))
            with open(os.path.join(h, r[10], "deep", "a.jpg"), "wb") as fh:
                fh.write(b"z" * 200000)

        def nested_again():
            with open(os.path.join(h, r[10], "deep", "b.jpg"), "wb") as fh:
                fh.write(b"z" * 200000)                                # only the NESTED folder's stamp moves

        def ratchet():
            b = _load(self.ratchet)
            b["accepted"] = [x for x in b["accepted"] if x != self.pinned]
            b["count"] = len(b["accepted"])
            _dump(self.ratchet, b)

        return [
            ("vault_swept.json rows (same size)", lambda: ledger("vault_swept.json", vault_rows)),
            ("chronicle_swept.json entry", lambda: ledger("chronicle_swept.json", chron_drop)),
            ("retro_triage.json panels (same size)", lambda: ledger("retro_triage.json", triage)),
            ("chron_evidence.json new citation", lambda: ledger("chron_evidence.json", cite)),
            ("a loose frame at hist root whose stem a citation names", loose_dup),
            ("that loose frame leaves hist root", loose_gone),
            ("reel_tombstones.json remnant", tomb),
            ("vault_accum.json witness", durable),
            ("a reel's index.json rewritten in place", index_in_place),
            ("a frame added to an old reel", frame_added),
            ("a reel removed", reel_removed),
            ("a nested folder", nested),
            ("a file in the nested folder", nested_again),
            ("the ratchet", ratchet),
        ]

    def test_no_move_is_ever_served_stale(self):
        prev = RR.plan(self.hist)
        self.assertEqual(_strip(prev), _strip(self.fresh()), "PREMISE: the first answer is not plan()'s answer")
        RR.plan(self.hist)
        RR.plan(self.hist)
        self.assertEqual(RR.PLAN_STATS["served"], 1, "PREMISE: an unchanged world was not served, so nothing below "
                                                     "could be served stale either")
        unmoved = []
        for label, move in self._moves():
            move()
            _settle()
            runs0 = RR.PLAN_STATS["runs"]
            got = RR.plan(self.hist)
            self.assertGreater(RR.PLAN_STATS["runs"], runs0,
                               "after '%s' the console SERVED its remembered plan - an input plan() reads is missing "
                               "from plan_fingerprint()" % label)
            want = self.fresh()
            self.assertEqual(_strip(got), _strip(want),
                             "after '%s' the console's plan differs from a from-scratch plan: a stale answer about "
                             "which reels may be DELETED" % label)
            if _strip(want) == _strip(prev):
                unmoved.append(label)
            prev = want
            RR.plan(self.hist)                                          # and now it is kept again
        self.assertEqual(unmoved, [], "these moves did not change the answer, so this case cannot tell a stale "
                                      "memo from a fresh one for them: %s" % unmoved)


class AMovingInputIsNeverKept(_World):

    def test_a_just_moved_ledger_is_computed_every_time(self):
        RR.plan(self.hist)
        p = os.path.join(self.hist, "vault_swept.json")
        b = _load(p)
        b[self.reels[4][len("reel_"):]]["rows"] = 5
        _dump(p, b)
        runs0 = RR.PLAN_STATS["runs"]
        RR.plan(self.hist)
        RR.plan(self.hist)
        self.assertEqual(RR.PLAN_STATS["runs"] - runs0, 2,
                         "an answer computed while a ledger was still moving was KEPT: a second change inside one "
                         "clock tick leaves the stamp unchanged, so that answer can be served after it went stale")
        self.assertGreaterEqual(RR.PLAN_STATS["moving"], 2)

    def test_only_the_changed_folder_is_listed_again(self):
        RR.plan(self.hist)
        RR.plan(self.hist)
        with open(os.path.join(self.hist, self.reels[8], _frame(8, 77)), "wb") as fh:
            fh.write(b"q")
        _settle()
        listed0 = FR.LIST_STATS["listed"]
        RR.plan(self.hist)
        self.assertEqual(FR.LIST_STATS["listed"] - listed0, 1,
                         "one reel folder changed and %d folder(s) were listed again - a sealed reel must never be "
                         "re-listed" % (FR.LIST_STATS["listed"] - listed0))

    def test_a_write_in_flight_is_never_kept(self):
        d = os.path.join(self.hist, self.reels[8])
        with open(os.path.join(d, "kai_report.json.tmp"), "wb") as fh:
            fh.write(b"{")
        _settle()
        FR.listing(d)
        listed = FR.LIST_STATS["listed"]
        FR.listing(d)
        self.assertEqual(FR.LIST_STATS["listed"] - listed, 1, "a folder holding a .tmp write was served from memory")


class WhileHeFilmsCallersStillShareOneRun(_World):
    """REG-1437 — his footage writer drops a loose hist/f_<ms>.jpg about once a second while D2R runs, so hist is
    NEVER still and plan_fingerprint raises _Moving on every call: the memo cannot engage, and before this every
    caller computed alone. Concurrent callers must share a run - but never one that began before their own call."""

    LATE = 4

    def test_concurrent_callers_share_a_run_that_began_after_them(self):
        FR.RACY_S = 1.0                  # a 0.2 s writer against a 1 s window: hist is moving for the whole case
        stop = threading.Event()

        def writer():
            k = 0
            while not stop.is_set():
                # a loose frame whose stem no citation names - the answer's content is stable under these writes
                with open(os.path.join(self.hist, "f_%d.jpg" % (T0 - 10 ** 9 + k)), "wb") as fh:
                    fh.write(b"\xff\xd8live")
                k += 1
                stop.wait(0.2)
        wt = threading.Thread(target=writer, name="footage-writer", daemon=True)
        wt.start()

        def halt():
            stop.set()
            wt.join(5)
        self.addCleanup(halt)
        real = RR.proof_reels
        inside = threading.Event()

        def slow(h):
            inside.set()                 # plan() has read both ledgers by now (_pick runs first)
            time.sleep(0.8)
            return real(h)
        RR.proof_reels = slow
        time.sleep(0.3)
        out, errs = {}, []

        def call(name, gate=None):
            try:
                if gate is not None:
                    gate.wait(5)
                out[name] = RR.plan(self.hist)
            except Exception as e:
                errs.append(repr(e))
        first = threading.Thread(target=call, args=("first",))
        first.start()
        self.assertTrue(inside.wait(10), "PREMISE: the first caller's computation never started")
        # the world moves WHILE that computation runs: r4's rows go unbanked (0 -> 7). A caller arriving now must
        # not be handed the running computation's answer - it read the ledger before this call.
        p = os.path.join(self.hist, "vault_swept.json")
        b = _load(p)
        b[self.reels[4][len("reel_"):]]["rows"] = 7
        _dump(p, b)
        gate = threading.Barrier(self.LATE)
        late = [threading.Thread(target=call, args=("late%d" % i, gate)) for i in range(self.LATE)]
        for t in late:
            t.start()
        for t in late + [first]:
            t.join(30)
        s = dict(RR.PLAN_STATS)
        runs_burst = s["runs"]
        # and one more caller, still filming: nothing was remembered, so it computes
        call("after")
        s2 = dict(RR.PLAN_STATS)
        halt()
        RR.proof_reels = real
        self.assertEqual(errs, [])
        callers = 1 + self.LATE
        self.assertGreaterEqual(s["moving"], callers, "PREMISE: a caller found every input still, so the memo - "
                                                      "not the moving path - answered it: %r" % s)
        self.assertLess(runs_burst, callers,
                        "%d concurrent callers while he films ran plan() %d times - every lane rebuilds the proof set "
                        "alone for as long as D2R runs (2 expected: the running one, then ONE for every caller that "
                        "arrived during it): %r" % (callers, runs_burst, s))
        self.assertEqual((s2["runs"] - runs_burst, s2["served"]), (1, 0),
                         "a remembered answer was served while an input was moving: %r" % s2)
        want_new = _strip(self.fresh())                   # a from-scratch plan taken after every late call began
        for i in range(self.LATE):
            self.assertEqual(_strip(out["late%d" % i]), want_new,
                             "late%d arrived after r4's rows went unbanked and was handed an answer computed from "
                             "the ledger as it stood BEFORE its call - a stale 'may delete'" % i)
        self.assertEqual(_strip(out["after"]), want_new)
        b[self.reels[4][len("reel_"):]]["rows"] = 0
        _dump(p, b)
        want_old = _strip(self.fresh())                   # the world as it stood when `first` began
        self.assertNotEqual(want_old, want_new, "PREMISE: unbanking r4's rows does not change the answer, so this "
                                                "case cannot tell a stale answer from a fresh one")
        self.assertIn(_strip(out["first"]), (want_old, want_new),
                      "the first caller's answer matches neither the world at its call nor the world after it")


class TheConsoleNeverTokenizes(_World):

    def test_the_console_reads_the_ratchet(self):
        calls = []

        def banned(*a, **k):
            calls.append(a[1:2])
            raise AssertionError("a console tokenized %r" % (a[1:2],))
        FA._executable_only = banned
        got = FA.test_referenced_reels()
        self.assertEqual(got, FA.ratchet_reels())
        self.assertIn(self.pinned, got)
        FA._FIXTURE_BG.update(thread=None, last=None)
        FA.test_referenced_reels_nowait()
        th = FA._FIXTURE_BG.get("thread")
        if th is not None:
            th.join(10)
        self.assertEqual(FA.test_referenced_reels_nowait(), got)
        p = RR.plan(self.hist)
        self.assertEqual(self.tags(p).get(self.pinned), "test-fixture", "the pinned reel lost its fixture hold")
        self.assertEqual(calls, [], "the console tokenized the test suite")

    def test_an_unreadable_ratchet_is_not_an_empty_set(self):
        n = self.tiny_repo()
        with open(self.ratchet, "w", encoding="utf-8") as fh:
            fh.write("{ not json")
        self.assertIsNone(FA.ratchet_reels())
        got = FA.test_referenced_reels()
        self.assertEqual(got, {self.named}, "a ratchet that will not read answered %r - UNKNOWN is not EMPTY; the "
                                            "console must pay the exact scan instead" % (got,))
        self.assertGreater(len(n), 0)
        FA.__dict__.pop("_FIXTURE_CACHE", None)

    def test_an_unreadable_ratchet_keys_no_plan(self):
        """REG-1439 — the exact scan the console falls back to reads tv/*.py and tests/*, which plan_fingerprint
        does not cover: a kept plan would outlive an edited test. So on a console whose ratchet will not read,
        nothing is kept, and a test that starts naming a reel moves the very next answer."""
        self.tiny_repo()
        with open(self.ratchet, "w", encoding="utf-8") as fh:
            fh.write("{ not json")
        # warm the exact scan FIRST: its disk cache lands in _fixture_root, which under TV_HIST is this fixture's
        # hist (on his console it is tv/, outside the key) - written during a plan it would move hist and hide the
        # defect behind an unkept answer
        self.assertEqual(FA.test_referenced_reels(), {self.named}, "PREMISE: the fixture set did not come from the exact scan")
        _settle()                                    # the ratchet is STILL: only its unreadability can refuse a key
        r0 = self.reels[0]
        a = RR.plan(self.hist)
        self.assertEqual(self.tags(a).get(r0), "eligible", "PREMISE: r0 is not eligible, so a test naming it "
                                                           "cannot move the answer")
        RR.plan(self.hist)
        self.assertEqual((RR.PLAN_STATS["runs"], RR.PLAN_STATS["served"]), (2, 0),
                         "a plan was KEPT while the fixture set came from the exact scan: %r" % RR.PLAN_STATS)
        with open(os.path.join(FA.HERE, "test_tiny.py"), "a", encoding="utf-8") as fh:
            fh.write("S = %r\n" % r0)                # a test that now opens r0 by name
        b = RR.plan(self.hist)
        self.assertEqual(self.tags(b).get(r0), "test-fixture",
                         "a test began naming r0 and the console still offered it for release: it served a plan kept "
                         "while the fixture set came from files its key does not cover")
        self.assertEqual(_strip(b), _strip(self.fresh()))
        self.assertGreaterEqual(RR.PLAN_STATS["unkeyed"], 3)
        FA.__dict__.pop("_FIXTURE_CACHE", None)

    def test_exact_always_scans(self):
        n = self.tiny_repo()
        got = FA.test_referenced_reels(exact=True)
        self.assertEqual(got, {self.named}, "exact=True answered from the ratchet - the ratchet law would then grade "
                                            "the ratchet against itself and could never go red")
        self.assertGreater(len(n), 0)
        FA.__dict__.pop("_FIXTURE_CACHE", None)


class TheCachedWalkIsTheWalk(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="walk-", dir=_WORLD)
        for reel in ("reel_a", "reel_b"):
            for sub in ("", "hist", "hist/deep"):
                d = os.path.join(self.root, reel, sub)
                os.makedirs(d, exist_ok=True)
                for i in range(4):
                    with open(os.path.join(d, "f_%d_%d.jpg" % (len(sub), i)), "wb") as fh:
                        fh.write(b"x" * (10 + i + len(sub)))
        with open(os.path.join(self.root, "loose.png"), "wb") as fh:
            fh.write(b"yy")
        if hasattr(os, "symlink"):
            try:
                os.symlink(os.path.join(self.root, "reel_a"), os.path.join(self.root, "a_link_dir"))
            except (OSError, NotImplementedError):
                pass
        self._keep = (FR.RACY_S, FR.on_console_path())
        FR.RACY_S = STILL_S
        FR._forget_listings()
        _settle()

    def tearDown(self):
        FR.RACY_S = self._keep[0]
        FR.mark_console_path(self._keep[1])
        FR._forget_listings()
        shutil.rmtree(self.root, True)

    def _shape(self, ix):
        return list(ix.by_path.items()), ix.by_stem, ix.files, ix.bytes

    def test_the_console_walk_equals_the_fresh_walk(self):
        FR.mark_console_path(False)
        want, want_mb = self._shape(FR.Index(self.root)), RR._dir_mb(self.root)
        FR.mark_console_path(True)
        cold = self._shape(FR.Index(self.root))
        listed = FR.LIST_STATS["listed"]
        warm = self._shape(FR.Index(self.root))
        self.assertEqual(FR.LIST_STATS["listed"], listed, "a still tree was listed again")
        self.assertEqual(cold, want, "the console's index differs from the fresh walk (paths, order, stems, sizes)")
        self.assertEqual(warm, want, "the remembered index differs from the fresh walk")
        self.assertEqual(RR._dir_mb(self.root), want_mb)


class TheRouterReadsTheSameListing(_World):
    """reel_router.route() asks every reel when it was filmed - one more walk of the whole shelf per route() on the
    triage thread's stack (river_stamp.run -> reel_router.route) - so it reads the same kept listing."""

    def test_filmed_at_is_read_once_from_a_still_folder(self):
        import reel_router as RT
        FR.mark_console_path(False)
        # REG-1893 - `calls == []` below is only evidence if this spy can hear a listing at all. The fresh arm
        # lists every reel through os.scandir; if the router stopped listing through it, an empty spy would read
        # as "never listed again" while the still folder was listed by some other door.
        real, fresh = os.scandir, []

        def counting_fresh(*a, **k):
            fresh.append(a[:1])
            return real(*a, **k)
        os.scandir = counting_fresh
        try:
            want = [RT._captured_ms(r, self.hist) for r in self.reels]
        finally:
            os.scandir = real
        self.assertGreaterEqual(len(fresh), len(self.reels),
                                "the os.scandir spy heard %d listing(s) for %d reels on the FRESH path, so it "
                                "cannot hear a re-listing either and the absence below would be vacuous"
                                % (len(fresh), len(self.reels)))
        FR.mark_console_path(True)
        got = [RT._captured_ms(r, self.hist) for r in self.reels]
        # count the OS's own listings, not the memory's counter - a fresh scan that bypasses listing() never
        # touches LIST_STATS, so a counter would stay green through exactly the defect this case exists for
        real, calls = os.scandir, []

        def counting(*a, **k):
            calls.append(a[:1])
            return real(*a, **k)
        os.scandir = counting
        try:
            again = [RT._captured_ms(r, self.hist) for r in self.reels]
        finally:
            os.scandir = real
        self.assertEqual(got, want, "the console's filmed-at differs from a fresh listing")
        self.assertEqual(again, want)
        self.assertTrue(all(src == "frames" for _ms, src in want), "PREMISE: the frames were not the clock")
        self.assertEqual(calls, [], "a still reel folder was listed again for its first frame: %d listing(s)"
                                    % len(calls))


class _Booted(BaseException):
    """control_app.main() stops here: past its boot prefix, before it binds, opens a window or spawns a lane.
    A BaseException, so none of main()'s `except Exception` arms can swallow it and carry on booting."""


class TheConsoleIsMarkedBeforeItAsksAnything(_World):
    """REG-1436 — DRIVEN, never read: control_app.main() itself runs, on a fixture shelf, with every step of its boot
    prefix stubbed to record whether the console path was marked when it was asked. status_payload()'s stub asks
    what the real one's autoread refresh asks (_vault_autoread_kick -> tvd-vault-autoread -> _vault_autoread_state
    -> _vault_owed_reels -> reel_retention.plan(<hist>)), on the calling thread so no race with the mark can
    decide the verdict. The exact scan is pointed at a one-file repo and counted: before the mark it is the
    tokenize over every tv/*.py that stalled his ALT after each ship. A co_names check was green with the mark
    one line too late."""

    def test_nothing_main_asks_at_boot_tokenizes_the_suite(self):
        import types
        import control_app as CA
        n = self.tiny_repo()
        FR.mark_console_path(False)                 # a fresh process: nothing has said "console" yet
        asked = []

        def reap(*a, **k):
            asked.append(("_reap_inherited_at_boot", FR.on_console_path()))
            return ""

        def status(*a, **k):
            asked.append(("status_payload", FR.on_console_path()))
            CA._vault_owed_reels(self.hist)
            raise _Booted()

        def stop(*a, **k):
            raise _Booted()
        # backstops: if the boot ever stops asking status_payload(), main() still halts before anything real
        fake_wr = types.ModuleType("win_relaunch")
        for fn in ("install_excepthook", "wait_for_parent", "boot_log", "read_receipt"):
            setattr(fake_wr, fn, stop)
        had = "win_relaunch" in sys.modules
        keep_wr = sys.modules.get("win_relaunch")
        sys.modules["win_relaunch"] = fake_wr

        def undo_wr():
            if had:
                sys.modules["win_relaunch"] = keep_wr
            else:
                sys.modules.pop("win_relaunch", None)
        self.addCleanup(undo_wr)
        for name, fn in (("_reap_inherited_at_boot", reap), ("status_payload", status),
                         ("open_control_window", stop), ("start_background_watchers", stop),
                         ("board_window", stop), ("_win_primary_mutex", stop), ("ThreadingHTTPServer", stop)):
            self.addCleanup(setattr, CA, name, getattr(CA, name))
            setattr(CA, name, fn)
        runs0 = RR.PLAN_STATS["runs"]
        with self.assertRaises(_Booted):
            CA.main()
        self.assertIn("status_payload", [a for a, _on in asked],
                      "PREMISE: main() no longer asks status_payload() at boot, so this case drove nothing - re-aim "
                      "it at whatever the boot asks first")
        self.assertGreater(RR.PLAN_STATS["runs"], runs0, "PREMISE: the boot's question never reached plan()")
        self.assertEqual([a for a, on in asked if not on], [],
                         "control_app.main() asked these BEFORE it marked the console path - on his console that is "
                         "the exact scan over every tv/*.py, once per ship, at boot")
        self.assertEqual(len(n), 0, "control_app.main()'s boot tokenized %d test file(s) before the console path was "
                                    "marked" % len(n))
        self.assertTrue(FR.on_console_path(), "main() never marked the console path at all")


class TheJoints(unittest.TestCase):

    def test_the_ratchet_law_asks_for_the_exact_set(self):
        with open(os.path.join(HERE, "test_a_gate_may_not_pin_his_footage.py"), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        exact = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and getattr(n.func, "attr", None) == "test_referenced_reels"
                 and any(k.arg == "exact" and getattr(k.value, "value", None) is True for k in n.keywords)]
        self.assertTrue(exact, "the ratchet law no longer asks for the exact scan")


RED_PROOF = [
    {
        "why": "REG-1411 - concurrent callers stop joining the running computation; every lane rebuilds the proof set "
               "at once again (his ALT: three index walks, /api/river past 90 s)",
        "file": "reel_retention.py",
        "find": "                elif fl[\"fp\"] == fp:\n",
        "replace": "                elif False:\n",
        "matches": 1,
    },
    {
        "why": "REG-1411 - the kept plan is served without comparing its fingerprint: a stale answer about which "
               "reels may be DELETED",
        "file": "reel_retention.py",
        "find": "            if m is not None and m[0] == fp:\n",
        "replace": "            if m is not None:\n",
        "matches": 1,
    },
    {
        "why": "REG-1411 - an input plan() reads (the triage store) is left out of the fingerprint, so moving it "
               "serves the old verdict",
        "file": "reel_retention.py",
        "find": "    out.append(_rt._store_path())\n",
        "replace": "    pass\n",
        "matches": 1,
    },
    {
        "why": "REG-1411 - _pick's order is left out of the key when both ledger copies exist: plan() and plan(<tree>) "
               "read different copies first, and one is served the other's answer",
        "file": "reel_retention.py",
        "find": "    _order = (bool(hist_dir) or bool(os.environ.get(\"TV_HIST\"))) if _both else None\n",
        "replace": "    _order = None\n",
        "matches": 1,
    },
    {
        "why": "REG-1411/1412 - the stillness rule is dropped: an answer (or a listing) taken while an input was "
               "still moving is kept, and a second change inside one clock tick is then invisible",
        "file": "frame_ref.py",
        "find": "    return now_ns - newest >= int(RACY_S * 1e9)\n",
        "replace": "    return True\n",
        "matches": 1,
    },
    {
        "why": "REG-1412 - a kept folder listing is served without comparing the folder's key: a new or removed "
               "frame is never seen",
        "file": "frame_ref.py",
        "find": "        if hit is not None and hit[0] == key:\n",
        "replace": "        if hit is not None:\n",
        "matches": 1,
    },
    {
        "why": "REG-1410 (#66) - the console tokenizes every test file again after each ship (his ALT: 11 s "
               "/api/status, then timeouts)",
        "file": "frame_authority.py",
        "find": "            if _rat is not None:\n                return _rat\n",
        "replace": "            if False:\n                return _rat\n",
        "matches": 1,
    },
    {
        "why": "REG-1410 - a ratchet that will not read becomes an EMPTY fixture set, and the reels the suite opens "
               "become deletable",
        "file": "frame_authority.py",
        "find": "            # the ratchet will not read -> fall through to the exact scan, never to an empty set\n",
        "replace": "            return set()\n",
        "matches": 1,
    },
    {
        "why": "REG-1412 - reel_router lists every reel folder afresh again for its first frame, once per route()",
        "file": "reel_router.py",
        "find": "        _names = _fr.listing(d)\n",
        "replace": "        _names = _fr._scan(d)\n",
        "matches": 1,
    },
    {
        "why": "REG-1410..1412 - control_app.main() stops marking the console path, so his console gets none of it",
        "file": "control_app.py",
        "find": "        _fr_console.mark_console_path(True)\n",
        "replace": "        pass\n",
        "matches": 1,
    },
    {
        "why": "REG-1436 - the console path is marked only AFTER status_payload() (the boot banner), whose autoread "
               "refresh reaches plan() -> the exact tokenize scan over every tv/*.py, once per ship, at boot. "
               "main() still names mark_console_path, so a co_names check stays green on exactly this",
        "file": "control_app.py",
        "find": "        _bv = (status_payload() or {}).get(\"ver\") or \"?\"\n",
        "replace": "        _fr_console.mark_console_path(False)\n"
                   "        _bv = (status_payload() or {}).get(\"ver\") or \"?\"\n"
                   "        _fr_console.mark_console_path(True)\n",
        "matches": 1,
    },
    {
        "why": "REG-1437 - while he films, a caller joins the computation ALREADY RUNNING, which read the ledgers "
               "before its call: a stale 'may delete' handed to a caller that asked after the world moved",
        "file": "reel_retention.py",
        "find": "            w = st[\"next\"]\n            lead = w is None\n",
        "replace": "            w = st[\"running\"]\n            lead = False\n",
        "matches": 1,
    },
    {
        "why": "REG-1437 - while he films (hist never still) every caller computes alone again: the concurrent index "
               "walks REG-1411 was written for, for as long as D2R runs",
        "file": "reel_retention.py",
        "find": "            return _plan_wave(hist_dir, free_mb, keep_recent)\n",
        "replace": "            return _NO_MEMO\n",
        "matches": 1,
    },
    {
        "why": "REG-1438 - hist's own folder key leaves the fingerprint: a loose frame whose stem a citation names "
               "arrives or leaves, the reel flips holds-proof <-> eligible, and the console serves the old verdict",
        "file": "reel_retention.py",
        "find": "    parts.append((hist, _fr.folder_key(st)))\n",
        "replace": "    pass\n",
        "matches": 1,
    },
    {
        "why": "REG-1439 - a console whose ratchet will not read keeps its plan, while the fixture set comes from the "
               "exact scan over files the key does not cover: a test that starts naming a reel is not seen",
        "file": "reel_retention.py",
        "find": "    if _fr.on_console_path() and _fa_key.ratchet_reels() is None:\n",
        "replace": "    if False:\n",
        "matches": 1,
    },
]


if __name__ == "__main__":
    try:
        unittest.main(verbosity=2)
    finally:
        shutil.rmtree(_WORLD, True)
