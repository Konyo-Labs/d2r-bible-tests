"""v2001 — the retention planner's five bars, and the proof it can actually select and delete.

A deleter nobody has watched select anything is worse than none: on his real tree it correctly
reports ZERO candidates today, so without these the "safe" answer and a broken one are the same
output. Every case here runs against a TEMP fixture — never his frames.
[[feedback-fixtures-never-touch-live-data]] [[feedback-blind-fixture-green-gate]]
"""
import io
import json
import os
import shutil
import sys
import tempfile
# ⚠ v2122 (#32) — THE BASE EPOCH IS 14000000000xx ON PURPOSE, DO NOT MOVE IT BACK TO 10000000000xx.
# reel_retention holds any reel whose id appears as a LITERAL in a tv/test_*.py file (v2069: a real
# prune deleted three reels tv/test_control.py names, turning real checks into permanent skips).
# tv/test_control.py contains the literal `reel_s_1000000000000_1`, and this suite CONSTRUCTED that
# same id — so the fixture-protection rule claimed this suite's own fixture and eight cases here
# asserted deletions that could never happen. The rule was right; the id collided.
# [[gate-blind-to-unexercised-input]] [[feedback-blind-fixture-green-gate]]
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import console_safe  # noqa: F401,E402 — this file's own docstring carries 🔓, and a suite that
                     # crashes while REPORTING makes a clean tree exit non-zero
console_safe.enable()
import fixture_tmp as _fx_tmp  # noqa: E402  #173 - its scratch is its own, so listing it keeps the law keyable
_fx_tmp.contain()

import reel_retention as rr  # noqa: E402


RED_PROOF = [
    {
        "why": 'the law requires this text in reel_retention.py, where it occurs exactly once and in no other file the gate names; deleting it must turn the gate red',
        "file": 'reel_retention.py',
        "find": 'never chronicle-swept',
        "replace": '_HEART2_TAMPERED_',
        "matches": 1,
    },
]

class TestRetentionSelectsAndRefuses(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.hist = os.path.join(self.root, "hist")
        os.makedirs(self.hist)
        self.addCleanup(shutil.rmtree, self.root, True)
        # point the module's ledger lookup at the fixture, never at his tree
        self._real_here = rr.HERE
        rr.HERE = self.root
        self.addCleanup(setattr, rr, "HERE", self._real_here)
        # v2122 (#32) — AND GIVE IT A DURABLE WITNESS STORE, because his tree has one. The reel
        # deleter now holds every reel when `haveIndex` is False, matching frame_authority, which
        # has always refused to delete a single FRAME in that state. A fixture with no durable
        # store was asking this module to release footage the frame deleter would not touch —
        # i.e. asserting the very disagreement #32 exists to close.
        with open(os.path.join(self.root, "vault_accum.json"), "w") as fh:
            json.dump({}, fh)
        self._allow_release()

    # ⚠⚠ THE LOCK SITS ABOVE EVERYTHING THIS CLASS MEASURES. v3050 put the `frame.release`
    # self-arming lock at the top of apply_plan, and it fails closed on a stale heart census —
    # the tree's normal state the moment ANY gate file changes. So
    # `test_apply_with_yes_actually_removes_it_and_leaves_the_rest` went red reporting
    # "frame.release is LOCKED — the heart census is STALE", which is not a statement about
    # retention at all. Identical to the outage that silenced test_freed_is_measured (REG-1025),
    # one file over — the same lock, the same shape, found twice.
    # [[copy-drift]] [[feedback-blind-fixture-green-gate]]
    #
    # The lock is CORRECT and stays. It is stubbed for the SELECTION laws, and
    # `test_the_release_lock_still_bites` asserts the real one still refuses, so the stub can
    # never quietly become a bypass.
    def _allow_release(self):
        import self_arming as _sa
        _real = _sa.may
        def _may(name, *a, **k):
            if name == "frame.release":
                return (True, "stubbed by test_reel_retention so the SELECTION laws are "
                              "reachable; the real lock is asserted separately")
            return _real(name, *a, **k)
        _sa.may = _may
        self.addCleanup(setattr, _sa, "may", _real)

    def test_the_release_lock_still_bites(self):
        """★ THE STUB IS NOT A BYPASS. With the real lock engaged, no footage may be removed."""
        import self_arming as _sa
        _real = _sa.may
        _sa.may = lambda name, *a, **k: (False, "engaged for this test")
        self.addCleanup(setattr, _sa, "may", _real)
        name = self._reel(1500000000009, 1)
        d = os.path.join(self.hist, name if isinstance(name, str) else "")
        if not os.path.isdir(d):
            d = os.path.join(self.hist, sorted(_fx_tmp.list_own(self.hist))[0])
        r = rr.apply_plan({"hist": self.hist, "freeMb": 1.0,
                           "candidates": [{"reel": os.path.basename(d), "mb": 1.0}]}, yes=True)
        self.assertFalse(r.get("ok"), "a LOCKED frame.release reported success")
        self.assertEqual(r.get("removed"), [], "it deleted through a locked door")
        self.assertTrue(os.path.isdir(d),
                        "the reel is GONE — the lock on the one line that deletes his footage "
                        "did not hold")
        self.assertIn("LOCKED", str(r.get("why") or ""),
                      "the refusal must name the lock, or the next reader debugs retention "
                      "instead [[unknown-stays-unknown]]")

    def _reel(self, ms, n=1, kb=8):
        name = "reel_s_%d_%d" % (ms, n)
        d = os.path.join(self.hist, name)
        os.makedirs(d)
        with open(os.path.join(d, "f_%d.jpg" % ms), "wb") as fh:
            fh.write(b"\0" * (kb * 1024))
        return name

    def _ledgers(self, chron=None, vault=None):
        with open(os.path.join(self.root, "chronicle_swept.json"), "w") as fh:
            json.dump(chron or {}, fh)
        if vault is not None:
            with open(os.path.join(self.root, "vault_swept.json"), "w") as fh:
                json.dump(vault, fh)

    def test_it_selects_only_a_reel_BOTH_lanes_have_sealed_with_evidence(self):
        good = self._reel(1_400_000_000_000)
        nopages = self._reel(1_400_000_000_001)
        novault = self._reel(1_400_000_000_002)
        never = self._reel(1_400_000_000_003)
        self._ledgers(
            chron={good: {"pages": 12}, nopages: {"pages": 0}, novault: {"pages": 9}},
            vault={good: {"ts": 1}, nopages: {"ts": 1}})
        p = rr.plan(self.hist, keep_recent=0)
        names = [c["reel"] for c in p["candidates"]]
        self.assertEqual(names, [good], "selected %s" % names)
        why = {k["reel"]: k["why"] for k in p["kept"]}
        self.assertIn("0 pages", why[nopages])
        self.assertIn("VAULT", why[novault])
        self.assertIn("never chronicle-swept", why[never])

    def test_a_zero_page_seal_is_never_a_candidate_however_old(self):
        """The bar that matters most: 1166 MB of his footage is sealed with 0 pages, and the engine
        reopens exactly those when the prompt improves."""
        old = self._reel(1_400_000_000_000)
        self._ledgers(chron={old: {"pages": 0}}, vault={old: {"ts": 1}})
        self.assertEqual(rr.plan(self.hist, keep_recent=0)["candidates"], [])

    def test_the_newest_are_kept_whatever_the_ledgers_say(self):
        reels = [self._reel(1_400_000_000_000 + i) for i in range(6)]
        self._ledgers(chron={r: {"pages": 5} for r in reels},
                      vault={r: {"ts": 1} for r in reels})
        p = rr.plan(self.hist, keep_recent=5)
        self.assertEqual([c["reel"] for c in p["candidates"]], [reels[0]],
                         "keep_recent must protect the newest five")

    def test_it_stops_as_soon_as_the_target_is_met(self):
        reels = [self._reel(1_400_000_000_000 + i, kb=1024) for i in range(4)]
        self._ledgers(chron={r: {"pages": 5} for r in reels},
                      vault={r: {"ts": 1} for r in reels})
        p = rr.plan(self.hist, free_mb=1.5, keep_recent=0)
        self.assertLess(len(p["candidates"]), 4, "it emptied the shelf instead of meeting the target")
        self.assertGreaterEqual(p["freeMb"], 1.0)
        self.assertTrue(any("target was already met" in k["why"] for k in p["kept"]))

    def test_oldest_first(self):
        newer = self._reel(1_400_000_000_009)
        older = self._reel(1_400_000_000_000)
        self._ledgers(chron={newer: {"pages": 5}, older: {"pages": 5}},
                      vault={newer: {"ts": 1}, older: {"ts": 1}})
        p = rr.plan(self.hist, keep_recent=0)
        self.assertEqual([c["reel"] for c in p["candidates"]], [older, newer])

    def test_apply_REFUSES_without_yes_and_deletes_nothing(self):
        r1 = self._reel(1_400_000_000_000)
        self._ledgers(chron={r1: {"pages": 5}}, vault={r1: {"ts": 1}})
        p = rr.plan(self.hist, keep_recent=0)
        self.assertEqual(len(p["candidates"]), 1)
        out = rr.apply_plan(p, yes=False)
        self.assertFalse(out["ok"])
        self.assertTrue(os.path.isdir(os.path.join(self.hist, r1)),
                        "it deleted footage without an explicit yes")

    def test_apply_with_yes_actually_removes_it_and_leaves_the_rest(self):
        gone = self._reel(1_400_000_000_000)
        stay = self._reel(1_400_000_000_001)
        self._ledgers(chron={gone: {"pages": 5}, stay: {"pages": 0}},
                      vault={gone: {"ts": 1}, stay: {"ts": 1}})
        p = rr.plan(self.hist, keep_recent=0)
        out = rr.apply_plan(p, yes=True)
        self.assertTrue(out["ok"], out)
        self.assertEqual(out["removed"], [gone])
        self.assertFalse(os.path.isdir(os.path.join(self.hist, gone)))
        self.assertTrue(os.path.isdir(os.path.join(self.hist, stay)),
                        "it took a reel that had given up nothing")

    def test_an_unparseable_reel_name_sorts_NEWEST_so_nobody_deletes_it_first(self):
        odd = "reel_weird_name"
        os.makedirs(os.path.join(self.hist, odd))
        self.assertEqual(rr._reel_ts(odd), float("inf"))

    def test_a_missing_hist_dir_refuses_rather_than_reporting_an_empty_plan(self):
        p = rr.plan(os.path.join(self.root, "nope"))
        self.assertFalse(p["ok"])
        self.assertEqual(p["candidates"], [])


class TestV2042AHoldThatCanNeverBeSatisfiedIsALeak(unittest.TestCase):
    """The vault hold must ask whether the VAULT LANE WILL EVER COME.

    `vault_retro.OWNERSHIP_SURFACES` deliberately excludes 'chronicle', so a reel that DECLARED a
    chronicle focus is never the vault lane's to read. Holding it until the vault sweeps it holds it
    forever. Measured on his tree 2026-08-24: five reels declaring chronicle-uniques /
    chronicle-sets — 185 MB — kept on exactly that reason while the disk sat at 96%, waiting for a
    lane that was never going to come.

    Every case runs against a TEMP fixture, never his frames.
    [[feedback-fixtures-never-touch-live-data]]
    """

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.hist = os.path.join(self.root, "hist")
        os.makedirs(self.hist)
        self.addCleanup(shutil.rmtree, self.root, True)
        self._real_here = rr.HERE
        rr.HERE = self.root
        self.addCleanup(setattr, rr, "HERE", self._real_here)
        # v2122 (#32) — a durable witness store, because his tree has one. Without it the reel
        # deleter now holds everything (matching frame_authority, which has always refused to
        # delete a single FRAME in that state), and these cases are about the LANE holds, not
        # about that one.
        with open(os.path.join(self.root, "vault_accum.json"), "w") as fh:
            json.dump({}, fh)

    def _reel(self, ms, focus="__none__", kb=8):
        name = "reel_s_%d_1" % ms
        d = os.path.join(self.hist, name)
        # exist_ok: _plan_one is called once per focus in a subTest loop with the SAME id, so the
        # second focus raised FileExistsError before it could assert anything.
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "f_%d.jpg" % ms), "wb") as fh:
            fh.write(b"\0" * (kb * 1024))
        if focus != "__no_index__":
            ix = {} if focus == "__none__" else {"focus": focus}
            with open(os.path.join(d, "index.json"), "w") as fh:
                json.dump(ix, fh)
        return name

    def _sweep(self, reels):
        with open(os.path.join(self.root, "chronicle_swept.json"), "w") as fh:
            json.dump({r: {"pages": 12} for r in reels}, fh)
        with open(os.path.join(self.root, "vault_swept.json"), "w") as fh:
            json.dump({}, fh)          # the vault lane has swept NOTHING

    def _why(self, plan, reel):
        for row in (plan.get("candidates") or []) + (plan.get("kept") or []):
            if row.get("reel") == reel or row.get("name") == reel:
                return row.get("why") or ""
        return None

    def _plan_one(self, focus):
        r = self._reel(1_400_000_000_000, focus=focus)
        self._sweep([r])
        p = rr.plan(self.hist, keep_recent=0)
        cands = {row.get("reel") or row.get("name") for row in (p.get("candidates") or [])}
        return r, p, (r in cands)

    def test_a_chronicle_reel_is_not_held_for_a_lane_that_will_never_read_it(self):
        for focus in ("chronicle-uniques", "chronicle-sets"):
            with self.subTest(focus=focus):
                r, p, eligible = self._plan_one(focus)
                self.assertTrue(eligible,
                                "a %s reel is still held for the VAULT lane, which by "
                                "OWNERSHIP_SURFACES will never read it - that reel can never be "
                                "freed. why=%r" % (focus, self._why(p, r)))
                self.setUp()

    def test_a_stash_reel_IS_still_held_until_the_vault_reads_it(self):
        r, p, eligible = self._plan_one("stash")
        self.assertFalse(eligible,
                         "a stash reel the vault lane has never read became deletable - its rows "
                         "would be lost before they were ever banked")
        self.assertIn("VAULT lane", self._why(p, r) or "")

    def test_a_reel_with_NO_declared_focus_is_still_held(self):
        """No focus means the vault lane classifies it, so it may still owe rows."""
        r, p, eligible = self._plan_one("__none__")
        self.assertFalse(eligible, "an unfocused reel became deletable before the vault saw it")

    def test_an_UNREADABLE_index_keeps_the_hold(self):
        """Deleting footage is irreversible. 'I could not tell' must never resolve to 'delete it'."""
        r, p, eligible = self._plan_one("__no_index__")
        self.assertFalse(eligible,
                         "a reel whose index could not be read was selected for deletion - the "
                         "planner guessed in the one direction that cannot be undone")



class TestV2056ReadIsNotBanked(unittest.TestCase):
    """Konyo: "after the sweep ... data needs to be extracted and ledgered and counted for items as
    witnesses so when they get pruned they continue to exist on record."

    MIN_PAGES called it "evidence banked" and meant "at least one page was READ". A sweep produces a
    PROPOSAL; only an apply puts rows in a store that outlives the frames. The night before this
    guard was written, a blocked apply left 7 grounded and 17 unsure sitting in a proposal for hours
    while retention was free to run — and reel s_1787242455315_9654 had rows=7 in vault_swept with
    nothing durable behind it.

    ⚠ ON HIS REAL TREE THIS BRANCH IS CURRENTLY UNEXERCISED: that reel is held by the EARLIER
    chronicle-pages branch, so his data cannot tell a working guard from a broken one. The case is
    therefore built here. [[gate-blind-to-unexercised-input]]
    """

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.hist = os.path.join(self.root, "hist")
        os.makedirs(self.hist)
        self.addCleanup(shutil.rmtree, self.root, True)
        self._real = rr.HERE
        rr.HERE = self.root
        self.addCleanup(setattr, rr, "HERE", self._real)

    def _reel(self, sid, kb=8):
        d = os.path.join(self.hist, "reel_" + sid)
        os.makedirs(d)
        with open(os.path.join(d, "f_1.jpg"), "wb") as fh:
            fh.write(b"\0" * (kb * 1024))
        with open(os.path.join(d, "index.json"), "w") as fh:
            json.dump({"sessionId": sid, "focus": "stash"}, fh)
        return "reel_" + sid

    def _ledgers(self, sid, rows, durable):
        """Both lanes have READ it. `durable` decides whether the rows reached a store."""
        with open(os.path.join(self.root, "chronicle_swept.json"), "w") as fh:
            json.dump({"reel_" + sid: {"pages": 12}}, fh)
        with open(os.path.join(self.root, "vault_swept.json"), "w") as fh:
            json.dump({sid: {"ts": 1, "rows": rows}}, fh)
        acc = {"owned": []}
        if durable:
            acc["owned"] = [{"name": "Enigma", "lane": "stash",
                             "witnesses": [{"session": sid, "frame": "f_1.jpg"}]}]
        with open(os.path.join(self.root, "vault_accum.json"), "w") as fh:
            json.dump(acc, fh)

    def _eligible(self, name):
        p = rr.plan(self.hist, keep_recent=0)
        return name in {r.get("reel") or r.get("name") for r in (p.get("candidates") or [])}, p

    def _why(self, plan, name):
        for row in (plan.get("candidates") or []) + (plan.get("kept") or []):
            if (row.get("reel") or row.get("name")) == name:
                return row.get("why") or ""
        return ""

    def test_rows_read_but_NOT_banked_holds_the_reel(self):
        sid = "s_1400000000000_1"
        name = self._reel(sid)
        self._ledgers(sid, rows=7, durable=False)
        ok, plan = self._eligible(name)
        self.assertFalse(ok, "a reel whose 7 rows exist ONLY in these frames was offered for "
                             "deletion — that destroys the only record of those witnesses")
        self.assertIn("NONE of them are in the ledger", self._why(plan, name))

    def test_the_same_reel_becomes_eligible_ONCE_the_rows_are_banked(self):
        """The mirror. Without it, a guard that holds everything forever would also pass."""
        sid = "s_1400000000000_2"
        name = self._reel(sid)
        self._ledgers(sid, rows=7, durable=True)
        ok, plan = self._eligible(name)
        self.assertTrue(ok, "banked evidence still did not release the reel: %r"
                            % self._why(plan, name))

    def test_vault_seen_counts_as_durable_too(self):
        """v2051's ungrounded sightings outlive the frames just as owned rows do."""
        sid = "s_1400000000000_3"
        name = self._reel(sid)
        self._ledgers(sid, rows=4, durable=False)
        with open(os.path.join(self.root, "vault_seen.json"), "w") as fh:
            json.dump({"rows": [{"name": "Dwarf Star", "lane": "stash",
                                 "witnesses": [{"session": sid, "frame": "f_1.jpg"}]}]}, fh)
        ok, plan = self._eligible(name)
        self.assertTrue(ok, "a sighting durable in vault_seen.json did not release the reel: %r"
                            % self._why(plan, name))

    def test_an_unreadable_ledger_holds_rather_than_releases(self):
        """'I could not read the record' must never resolve to 'delete the record'."""
        sid = "s_1400000000000_4"
        name = self._reel(sid)
        self._ledgers(sid, rows=5, durable=False)
        with open(os.path.join(self.root, "vault_accum.json"), "w") as fh:
            fh.write("{ this is not json")
        ok, plan = self._eligible(name)
        self.assertFalse(ok, "an unreadable ledger released a reel holding un-banked evidence")

    def test_a_reel_that_produced_NO_rows_is_unaffected(self):
        """Nothing was found in it, so there is no record to lose."""
        sid = "s_1400000000000_5"
        name = self._reel(sid)
        self._ledgers(sid, rows=0, durable=False)
        ok, plan = self._eligible(name)
        self.assertTrue(ok, "a reel with no rows was held by the banked check: %r"
                            % self._why(plan, name))




class TestV2122TheTwoDeletersAgreeAboutTheSameFootage(unittest.TestCase):
    """frame_authority refuses to delete a single FRAME while `haveIndex` is False — nothing there
    can prove a frame is not the only record of what it saw. reel_retention deletes the WHOLE REEL
    those frames live in, and never asked: `haveIndex` appeared ZERO times in that module.

    MEASURED before the fix, on a tree with both swept ledgers and no durable witness store:

        haveIndex False   frames offered 0   reels offered 8

    Two authorities, opposite answers, same footage — and footage has no un-delete.
    [[feedback-contradiction-is-the-finding]] [[unknown-stays-unknown]]
    """

    def _tree(self, durable):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, True)
        hist = os.path.join(root, "hist")
        os.makedirs(hist)
        chron, vault = {}, {}
        for i in range(4):
            name = "reel_s_%d_1" % (1_400_000_000_100 + i)
            d = os.path.join(hist, name)
            os.makedirs(d)
            with open(os.path.join(d, "f_%d.jpg" % (1_400_000_000_100 + i)), "wb") as fh:
                fh.write(b"\0" * 200 * 1024)
            with open(os.path.join(d, "index.json"), "w") as fh:
                json.dump({"frames": [{"ts": 1_400_000_000_100 + i}]}, fh)
            chron[name] = {"pages": 9}      # swept with real pages
            vault[name] = {"rows": 0}       # the vault lane sealed it and owes nothing
        for fn, data in (("chronicle_swept.json", chron), ("vault_swept.json", vault)):
            with open(os.path.join(root, fn), "w") as fh:
                json.dump(data, fh)
        if durable:
            with open(os.path.join(root, "vault_accum.json"), "w") as fh:
                json.dump({}, fh)
        return root, hist

    def _plan(self, root, hist):
        real = rr.HERE
        rr.HERE = root
        try:
            return rr.plan(hist_dir=hist, free_mb=5000, keep_recent=0)
        finally:
            rr.HERE = real

    def _frame_plan(self, root, hist):
        """v2122 (#143) — ASK THE OTHER DELETER TOO, or this is not an agreement test.

        The first cut of this class asked reel_retention alone: it proved "the reel deleter holds",
        never "the two deleters agree". frame_authority could start OFFERING frames in this state
        and nothing here would notice — which is the same one-sidedness the original #32 report
        called out in the test it replaced."""
        import frame_authority as fa
        real = fa.HERE
        fa.HERE = root
        try:
            return fa.plan_frames(hist, root=root, keep=0)
        finally:
            fa.HERE = real

    def test_the_two_deleters_give_the_SAME_answer_with_no_index(self):
        """The actual invariant. Neither may release footage the other is protecting."""
        root, hist = self._tree(durable=False)
        frames = self._frame_plan(root, hist)
        reels = self._plan(root, hist)
        self.assertEqual(frames.get("prunable"), [],
                         "the FRAME deleter offered frames with no durable witness index — the "
                         "premise this whole agreement rests on has changed")
        self.assertEqual(reels.get("candidates"), [],
                         "the REEL deleter offered footage the frame deleter refuses to touch: "
                         "two authorities, opposite answers, and footage has no un-delete")

    def test_no_durable_index_holds_every_reel(self):
        root, hist = self._tree(durable=False)
        p = self._plan(root, hist)
        self.assertEqual(p.get("candidates"), [],
                         "the reel deleter offered footage the FRAME deleter refuses to touch — "
                         "two authorities, opposite answers, and footage has no un-delete")
        self.assertEqual((p.get("coverage") or {}).get("no-witness-index"), 4,
                         "the reels were held, but not for this reason — a right hold with the "
                         "wrong reason sends him to fix the wrong thing")

    def test_it_is_NOT_a_blanket_refusal_once_the_index_exists(self):
        """The mirror, and it is the half that matters: a rule that holds everything forever is
        the same defect wearing a helmet. With a durable store present the other rules decide.
        [[feedback-blind-fixture-green-gate]]"""
        root, hist = self._tree(durable=True)
        p = self._plan(root, hist)
        self.assertEqual((p.get("coverage") or {}).get("no-witness-index"), 0,
                         "the new hold fires even when a durable witness store EXISTS — it would "
                         "quietly become a permanent refusal to prune anything")
        self.assertTrue(p.get("candidates"),
                        "nothing is eligible even with both lanes sealed and a durable store — "
                        "this guard can no longer tell the hold from a dead planner")


class TestV2272ExtractedFirstThenPruned(unittest.TestCase):
    """Konyo, 2026-08-29: "everything thats detail related should be extracted and tallied.. and
    then pruned" — and specifically that the LOCATION ("where it is exactly and where it was seen")
    counts as detail.

    A seal certifies promptVer/agentVer: WHICH READER ran, a statement about the NAME lane only.
    frame_verdict treated sealed + not-a-witness as disposable, so a frame whose location had never
    been extracted was deletable. MEASURED on his own footage the day this was written:
    274 of 6719 frames (0.37 GB) were being offered; with the contract in place, 0 are.
    """

    def _wit(self):
        return {"ok": True, "haveIndex": True, "frames": set()}

    def _sealed(self, extracted=None):
        row = {"ts": 1, "rows": 3, "promptVer": "vp2017", "agentVer": "v2026"}
        if extracted is not None:
            row["extracted"] = extracted
        return {"s_1_1": row}

    def _verdict(self, sealed):
        import frame_authority as fa
        return fa.frame_verdict("/tmp/hist/reel_s_1_1/f_9.jpg", sealed=sealed,
                                wit=self._wit(), recent=set())

    def test_a_seal_that_predates_the_contract_HOLDS(self):
        ok, why = self._verdict(self._sealed(None))
        self.assertFalse(ok)
        self.assertIn("predates the extraction contract", why)

    def test_a_seal_missing_LOCATION_holds_and_NAMES_what_is_missing(self):
        # the whole point of his rule: the name alone is not enough
        ok, why = self._verdict(self._sealed(["name", "provenance"]))
        self.assertFalse(ok)
        self.assertIn("location", why)

    def test_a_seal_missing_PROVENANCE_holds(self):
        ok, why = self._verdict(self._sealed(["name", "location"]))
        self.assertFalse(ok)
        self.assertIn("provenance", why)

    def test_a_COMPLETE_seal_RELEASES_the_frame(self):
        # ⚠ A HOLD THAT CAN NEVER BE RELEASED IS NOT A GATE, IT IS A WALL. If this ever fails, the
        # contract has become unsatisfiable and the pruner can never be armed no matter what the
        # sweep does. [[feedback-threshold-above-the-ceiling]]
        ok, why = self._verdict(self._sealed(["name", "location", "provenance"]))
        self.assertTrue(ok, why)

    def test_the_facts_are_NAMED_not_counted(self):
        # three of the same fact is not three facts
        import frame_authority as fa
        ok, why = fa.seal_covers_extraction({"extracted": ["name", "name", "name"]})
        self.assertFalse(ok)
        self.assertIn("location", why)

    def test_a_non_record_seal_holds(self):
        import frame_authority as fa
        for junk in (None, "sealed", 7, []):
            ok, _ = fa.seal_covers_extraction(junk)
            self.assertFalse(ok, "a %r seal was accepted" % (junk,))


class AFalsyLedgerEntryIsPresentNotAbsent(unittest.TestCase):
    """⚠⚠ REG-561 — `ledger.get(x) or ledger.get(y)` TREATED A PRESENT-BUT-EMPTY RECORD AS ABSENT,
    and did it ASYMMETRICALLY. Measured: `{}` stored under `reel_s_1` returned None — *never
    swept* — while the SAME `{}` stored under `s_1` returned it. **The same data under two
    spellings gave two different answers**, which is exactly the naming mismatch `_entry` exists to
    remove, and this is the DELETER's ledger.
    """

    def test_a_falsy_entry_reads_the_same_under_BOTH_spellings(self):
        import reel_retention as RR
        a = RR._entry({"reel_s_1": {}}, "reel_s_1")
        b = RR._entry({"s_1": {}}, "reel_s_1")
        self.assertEqual(a, b, "the same empty entry reads differently depending on which spelling "
                               "it was stored under: %r vs %r" % (a, b))
        self.assertIsNotNone(a, "a present-but-empty entry reads as 'never swept'")

    def test_an_EMPTY_ledger_row_HOLDS_exactly_as_an_absent_one_does(self):
        """⚠⚠ REG-562 — v2560 QUIETLY MOVED THE DELETER'S SAFE DIRECTION AND I SHIPPED IT.

        `_entry` was fixed to return a present-but-EMPTY record faithfully, because the REPORT was
        lying about which reels had a ledger row. But the plan's branches ask `ce is None` /
        `ve is None` to mean *this lane has not finished with the reel* — so after that fix an
        empty `{}` stopped answering None, and a reel whose row exists and **says nothing** would
        skip the HOLD branches and fall toward releasable.

        Measured on his tree at the time: chronicle_swept 401 entries, vault_swept 30, **0 falsy in
        either** — so nothing moved. **That is luck, not design, and it is the DELETER.**

        Two different questions: the report asks *is there a row?*, the deleter asks *does the row
        SAY anything?* This pins the second.
        """
        # ⚠⚠ AND THIS GUARD'S FIRST CUT READ A CACHE, NOT THE FILE. It used
        # `inspect.getsource`, which goes through `linecache` — after the sabotage rewrote the
        # module on disk, the guard was still served the ORIGINAL lines and went GREEN on a defect
        # that was really there. A source-reading guard that reads a cache is reading its own
        # memory. The file, by path, every time. [[source-reading-guard]]
        import os
        here = os.path.dirname(os.path.abspath(__file__))
        src = io.open(os.path.join(here, "reel_retention.py"), encoding="utf-8").read()
        i = src.index("def plan(")
        j = src.index("\ndef ", i + 10)
        body = src[i:j]
        # ⚠⚠ AND THE ANCHOR'S FIRST CUT WAS SATISFIED BY THE DEFINITION. `"_told(" in body` is
        # True because `def _told(e):` contains it — so removing the only CALL left the guard
        # green. A guard that reads for a token is satisfied by the token, and the token was
        # supplied by the very thing it was meant to check is USED. Anchor on the CALL SHAPE.
        # [[source-reading-guard]]
        self.assertIn("def _told", body, "the deleter's question is not asked at all")
        self.assertIn("_told(_entry(chron", body,
                      "the plan asks `_entry` directly again, so an empty ledger row no longer "
                      "holds the way an absent one does — on the one door with no undo")
        self.assertIn("_told(_entry(vault", body,
                      "the vault side asks `_entry` directly again — same defect, other lane")

    def test_ONE_precedence_for_the_reel_lookup_across_BOTH_modules(self):
        """⚠⚠ REG-563 — TWO MODULES IMPLEMENTED ONE LOOKUP WITH OPPOSITE PRECEDENCE. `_entry`
        tried the PREFIXED key first; `reel_river`'s seal lookup tried the BARE one first. Measured
        with both keys present, they returned **different records for the same reel**.

        Nothing was duplicated in text, so no filename or path check could see it — two modules
        simply decided one question had two answers, the same class as REG-556's `ok`. This drives
        both over one store holding BOTH spellings and requires the same record out.
        """
        import reel_retention as RR
        import reel_river as RiR
        led = {"reel_s_1": {"who": "prefixed"}, "s_1": {"who": "bare"}}
        a = RR._entry(led, "reel_s_1")
        b = RiR._seal_row(led, "reel_s_1") if hasattr(RiR, "_seal_row") else \
            RR.lookup_either_way(led, "reel_s_1")
        self.assertEqual(a, b, "the deleter and the river pick DIFFERENT records for one reel: "
                               "%r vs %r" % (a, b))
        self.assertEqual(a, {"who": "prefixed"},
                         "the precedence moved: the prefixed form is the deleter's, and the "
                         "deleter owns this rule because its answer has no undo")

    def test_an_already_prefixed_name_never_reaches_a_DOUBLE_prefixed_key(self):
        """⚠⚠ REG-565, from a cold review of the shipped bytes. The third lookup step built
        `"reel_" + r` from the ORIGINAL name, so asking for `reel_s_1` against a store holding only
        `reel_reel_s_1` **returned that double-prefixed record** — a key this lookup should never
        be able to reach, in the DELETER's own rule. The prefixed form of a name that already has
        the prefix is itself; only a BARE name gets one added.
        """
        import reel_retention as RR
        self.assertIsNone(
            RR.lookup_either_way({"reel_reel_s_1": {"who": "double"}}, "reel_s_1"),
            "an already-prefixed name reached a DOUBLE-prefixed key")

    def test_the_ASKED_form_wins_and_the_docstring_says_so(self):
        """⚠⚠ REG-566 — THE DOCSTRING STATED A RULE THE CODE HAS NEVER FOLLOWED. It said *"the
        PREFIXED form first, then the bare one"*; measured against a store holding BOTH keys,
        asking with `reel_s_1` returns the prefixed record and asking with `s_1` returns the bare
        one — **the asked form, both times.**

        The stated rule and the real rule agreed only for the caller the deleter happens to use
        (`plan()` always asks with the directory name, which is prefixed), so nothing ever
        contradicted it. This asks BOTH ways, so they cannot drift apart again.

        ⚠ This is REG-564's class one version later — a comment contradicting its own code — in the
        docstring of the function that fix produced.
        """
        import reel_retention as RR
        store = {"reel_s_1": {"who": "prefixed"}, "s_1": {"who": "bare"}}
        self.assertEqual(RR.lookup_either_way(store, "reel_s_1"), {"who": "prefixed"},
                         "asking with the prefixed name did not return the prefixed record")
        self.assertEqual(RR.lookup_either_way(store, "s_1"), {"who": "bare"},
                         "asking with the bare name did not return the bare record — the asked "
                         "form must win, which is what the code does and now what it says")
        # ⚠ AND THE TEXT CHECK'S FIRST CUT WAS THE WRONG INSTRUMENT. It asserted the old wrong
        # rule was ABSENT from the docstring — but the correction QUOTES that rule while explaining
        # it was wrong, so the guard fired on the very sentence recording the fix. A negative text
        # match on prose that deliberately cites what it replaced cannot work. Check the STATED
        # RULE, which lives on the PRECEDENCE line, not the whole blob.
        doc = RR.lookup_either_way.__doc__ or ""
        rule = [l for l in doc.split("\n") if "PRECEDENCE" in l]
        self.assertTrue(rule, "the docstring no longer states a precedence at all")
        self.assertIn("ASKED WITH", rule[0],
                      "the PRECEDENCE line does not state the rule the code implements: %r"
                      % rule[0])

    def test_a_name_that_names_NOTHING_finds_no_record(self):
        """⚠⚠ REG-567 — the phantom-key class one more time (REG-550, REG-559). `bare_reel("reel_")`
        is `""`, and the lookup then searched for `""` in the store: `lookup_either_way({"": 5},
        "reel_")` returned **5**. A name that names nothing must not find a record.

        ⚠ Found by a cold review asking what these tests did NOT cover — the `"reel_"` and
        empty-string inputs had no case at all.
        """
        import reel_retention as RR
        for ask in ("reel_", "", "   ", None):
            self.assertIsNone(RR.lookup_either_way({"": 5}, ask),
                              "%r resolved to a record under the empty-string key" % (ask,))

    def test_BASELINE_all_three_real_shapes_still_resolve(self):
        """⚠ Or the fix cut off the prefixed lookup entirely — the case that exists to find a reel
        stored under `reel_<sid>` when asked by its bare id."""
        import reel_retention as RR
        self.assertEqual(RR.lookup_either_way({"reel_x": 1}, "x"), 1,
                         "a bare name no longer finds its prefixed record")
        self.assertEqual(RR.lookup_either_way({"reel_s_1": 9}, "reel_s_1"), 9)
        self.assertEqual(RR.lookup_either_way({"s_1": 7}, "reel_s_1"), 7)

    def test_the_bare_form_is_a_PREFIX_strip_not_a_substring_replace(self):
        """⚠ `str.replace("reel_", "", 1)` strips the substring ANYWHERE — `"xreel_foo"` became
        `"xfoo"`, inventing a session id from a name that never had that prefix."""
        import reel_retention as RR
        self.assertEqual(RR.bare_reel("reel_s_1"), "s_1")
        self.assertEqual(RR.bare_reel("xreel_foo"), "xreel_foo",
                         "a name merely CONTAINING reel_ was stripped as though it began with it")
        self.assertEqual(RR.bare_reel("my_reel_thing"), "my_reel_thing")

    def test_BASELINE_a_genuinely_absent_entry_is_still_None(self):
        """⚠ Or the fix turned every miss into a find, which for a DELETER is the dangerous
        direction — its own docstring says 'never swept' is the safe answer."""
        import reel_retention as RR
        self.assertIsNone(RR._entry({}, "reel_s_1"))
        self.assertIsNone(RR._entry({"reel_other": {"pages": 1}}, "reel_s_1"))



class AFixtureCanActuallyRedirectTheLedgers(unittest.TestCase):
    """v2575 REG-570 — it could not, and eleven call sites believed it could.

    `_pick` searched HERE before the caller's `hist`, unconditionally, and took the first
    NON-EMPTY copy. So `plan(hist_dir=<scratch>)` read Konyo's live chronicle_swept (401 entries)
    and vault_swept (30) instead of the fixture's, and setting TV_HIST did not help either.

    Proven before the fix: a scratch ledger declaring pages=99 for three fixture reels still
    produced `never-chronicle-swept: 3` — his store answered and the fixture's was ignored.

    The consequence is not a wrong number in a report. Every sabotage ever aimed at this chooser
    was graded against live data it could not control, which is exactly why four separately
    claimed defects in it could not be reproduced. [[feedback-fixtures-never-touch-live-data]]
    """

    def _scratch(self):
        d = tempfile.mkdtemp(prefix="rr_redirect_")
        self.addCleanup(shutil.rmtree, d, True)
        sids = ["s_fixture_%d" % i for i in range(3)]
        for sid in sids:
            r = os.path.join(d, "reel_" + sid)
            os.makedirs(r)
            with io.open(os.path.join(r, "f_1780000000000.jpg"), "w") as fh:
                fh.write("x")
        for fn in ("chronicle_swept.json", "vault_swept.json"):
            with io.open(os.path.join(d, fn), "w", encoding="utf-8") as fh:
                json.dump({s: {"pages": 99, "rows": 99, "banked": True} for s in sids}, fh)
        return d

    def test_the_callers_hist_dir_is_the_one_that_answers(self):
        d = self._scratch()
        cov = rr.plan(hist_dir=d, keep_recent=0).get("coverage") or {}
        self.assertFalse(cov.get("never-chronicle-swept"),
                         "the fixture's ledger declared pages=99 for every reel and the plan "
                         "still reported never-chronicle-swept=%s — it read the LIVE store, so "
                         "this fixture is grading against Konyo's real data"
                         % cov.get("never-chronicle-swept"))

    def test_the_real_path_is_untouched_by_the_redirect(self):
        """BASELINE — or the fix bought isolation by changing what the deleter really does.

        ⚠⚠ THIS CASE READ KONYO'S FOOTAGE AND WAS RED ON EVERY CI RUN. It was a bare `rr.plan()`
        — the only one of 15 `rr.plan(` call sites in this file that passed no scratch dir — so it
        resolved reel_retention.py:319 `hist_dir or os.path.join(HERE, "frames", "hist")` onto
        tv/frames/hist. That directory is gitignored (.gitignore "tv/frames/", `git ls-files
        tv/frames` -> 0 tracked bytes) and no CI step creates it, so on a fresh clone plan()
        returns the :366-368 OSError payload, which carries NO `coverage` key at all — `.get(
        "coverage") or {}` is `{}` and `sum({}.values()) > 0` is unsatisfiable. Measured in CI
        af8beac9 2026-09-05: "AssertionError: False is not true : the real path stopped reporting
        anything at all". An empty-but-present frames/hist fails identically, via the all-zero
        counter at :444 — there is no input on a runner that could have made it pass.

        The file's own header already said what should have happened here: "Every case here runs
        against a TEMP fixture — never his frames." A skipUnless would have bought green by giving
        the baseline up on the venue that actually runs it — that is the trade that turned eight of
        seventeen named reels into permanent skips (see the v2069 note in reel_retention.py). So
        HERE is pointed at a scratch tree with the real SHAPE (frames/hist/reel_*) and plan() is
        still called with NO hist_dir and no TV_HIST, which is the thing this case is about: the
        UN-REDIRECTED order is still HERE-then-hist (reel_retention.py:343-344) and still reports.

        The order is now OBSERVABLE rather than assumed: the HERE copy of the ledger seals every
        reel, the hist copy is a readable `{}`, and "first readable wins" means whichever copy is
        consulted first is the one that answers. Un-redirected -> never-chronicle-swept 0.
        Measured with the redirect forced on (TV_HIST=1, same tree) -> never-chronicle-swept 2.
        [[feedback-fixtures-never-touch-live-data]] [[feedback-blind-fixture-green-gate]]
        """
        root = tempfile.mkdtemp(prefix="rr_realpath_")
        self.addCleanup(shutil.rmtree, root, True)
        hist = os.path.join(root, "frames", "hist")
        os.makedirs(hist)
        # KEEP_RECENT + 2, because a shielded reel never reaches the ledger branches. ⚠ #123 — this
        # said "SEVEN, because KEEP_RECENT is 5"; v2875 made it 8, so all seven were shielded as
        # `recent` and the case could never see the branch it guards. Sized FROM the constant now.
        sids = ["s_17300000000%02d_%d" % (i, i) for i in range(rr.KEEP_RECENT + 2)]
        for i, sid in enumerate(sids):
            d = os.path.join(hist, "reel_" + sid)
            os.makedirs(d)
            with io.open(os.path.join(d, "f_17300000000%02d.jpg" % i), "w") as fh:
                fh.write("x")
        # a durable store, or `_durable_sessions` reports ok=False and EVERY reel is held by
        # `no-witness-index` before any ledger is consulted — the fixture would have disabled the
        # branch it exists to watch, exactly as the stale-store case below records.
        with io.open(os.path.join(root, "vault_accum.json"), "w", encoding="utf-8") as fh:
            json.dump({}, fh)
        sealed = {("reel_" + s): {"pages": 99, "rows": 99, "banked": True} for s in sids}
        for fn in ("chronicle_swept.json", "vault_swept.json"):
            with io.open(os.path.join(root, fn), "w", encoding="utf-8") as fh:
                json.dump(sealed, fh)                       # the HERE copy — consulted FIRST
            with io.open(os.path.join(hist, fn), "w", encoding="utf-8") as fh:
                json.dump({}, fh)                           # readable, empty — the hist copy
        # ⚠⚠ #123 — plan() now asks machine_tree.footage_hist() for the hist when it is given none,
        # and that door resolves THIS MACHINE's shelf: patching HERE alone let the case read his REAL
        # 19 reels (coverage test-fixture 8 · recent 8 · never-chronicle-swept 3) and go red on his
        # footage. The door is pointed at the fixture — still no hist_dir and no TV_HIST, which is
        # the un-redirected order this case is about. [[feedback-fixtures-never-touch-live-data]]
        import machine_tree as _mt
        was, was_door, was_env = rr.HERE, _mt.footage_hist, os.environ.pop("TV_HIST", None)
        rr.HERE = root
        _mt.footage_hist = lambda: hist
        try:
            cov = rr.plan().get("coverage") or {}
            # PREMISE: the fixture must be able to tell the two orders apart, or the assertion
            # below is vacuous. Forced redirect -> the hist copy ({}) answers -> reels never swept.
            os.environ["TV_HIST"] = hist
            forced = rr.plan().get("coverage") or {}
        finally:
            rr.HERE, _mt.footage_hist = was, was_door
            os.environ.pop("TV_HIST", None)
            if was_env is not None:
                os.environ["TV_HIST"] = was_env
        self.assertEqual(sum(cov.values()), len(sids),
                         "coverage counted %d reel(s) and the fixture built %d — plan() read some "
                         "other shelf: %s" % (sum(cov.values()), len(sids), cov))
        self.assertTrue(forced.get("never-chronicle-swept"),
                        "premise: with the redirect forced the hist copy must answer and leave reels "
                        "never-chronicle-swept, or this fixture cannot see the order at all: %s" % forced)
        self.assertFalse(cov.get("ledger-unreadable"),
                         "the real path now cannot read its own ledgers: %s" % cov)
        self.assertFalse(cov.get("never-chronicle-swept"),
                         "with no hist_dir and no TV_HIST the order must still be HERE then hist "
                         "— the hist copy of the ledger (a readable {}) answered instead, so %s "
                         "reel(s) came back never-chronicle-swept. coverage=%s"
                         % (cov.get("never-chronicle-swept"), cov))

    def test_a_readable_EMPTY_store_is_not_overruled_by_a_stale_one(self):
        """The docstring always said 'first readable copy wins'; the code said 'first non-empty'.

        They differ on the one case that matters: a readable {} is a MEASUREMENT — nothing swept —
        and under the old rule a stale non-empty sibling overruled it, so more reels looked swept
        and MORE FOOTAGE became eligible.

        ⚠ THE FIRST VERSION OF THIS TEST WAS INERT AND THE SABOTAGE SAID SO. It put a readable
        `{}` in the scratch dir and asserted the reels stayed unswept — but under the OLD rule the
        empty store is merely skipped and the fallback is Konyo's real store, which contains no
        `s_fixture_*` session, so the count came out identical either way. The distinguishing case
        needs the STALE copy to name the SAME sessions, which means owning both ends: `HERE` is
        pointed at a second scratch dir carrying a non-empty ledger for exactly those reels.
        """
        d = self._scratch()
        for fn in ("chronicle_swept.json", "vault_swept.json"):
            with io.open(os.path.join(d, fn), "w", encoding="utf-8") as fh:
                json.dump({}, fh)              # readable, and deliberately empty
        stale = tempfile.mkdtemp(prefix="rr_stale_")
        self.addCleanup(shutil.rmtree, stale, True)
        sids = ["s_fixture_%d" % i for i in range(3)]
        for fn in ("chronicle_swept.json", "vault_swept.json"):
            with io.open(os.path.join(stale, fn), "w", encoding="utf-8") as fh:
                json.dump({s: {"pages": 99, "rows": 99, "banked": True} for s in sids}, fh)
        # ⚠ AND REPOINTING HERE MOVED A SECOND DEPENDENCY WITH IT — `_have_index` asks
        # frame_authority.witness_index(HERE), which found no index under the stale dir, so
        # `no-witness-index` held all three reels BEFORE the rule under test could be reached.
        # The branch order is correct; the fixture had silently disabled the thing it wanted to
        # observe. Both are pinned so the test sees the branch it is about.
        import frame_authority as _fa
        was, was_wi = rr.HERE, _fa.witness_index
        try:
            rr.HERE = stale
            _fa.witness_index = lambda *a, **k: {"haveIndex": True, "ok": True,
                                                 "sessions": {}, "frames": {}, "perStore": {}}
            cov = rr.plan(hist_dir=d, keep_recent=0).get("coverage") or {}
        finally:
            rr.HERE, _fa.witness_index = was, was_wi
        self.assertEqual(cov.get("never-chronicle-swept"), 3,
                         "the caller's ledger is readable and EMPTY — nothing was swept — and a "
                         "stale non-empty copy overruled it, so %s reel(s) looked swept and "
                         "became releasable. coverage=%s"
                         % (3 - (cov.get("never-chronicle-swept") or 0), cov))



class TheShieldAndThePageCountHoldUnderHostileLedgers(unittest.TestCase):
    """v2576 — REG-571/572/573, four defects in the chooser, all four reproduced.

    ⚠ THEY COULD NOT BE REPRODUCED AT ALL UNTIL v2575. `_pick` read Konyo's live ledgers whatever
    the fixture said, so every earlier attempt measured his data and reported "not reproduced".
    Isolation came first; the verdicts came second. An unreproducible claim is UNVERIFIED, which
    is a different fact from refuted.
    """

    def _fx(self, n=5, pages=3, extra=()):
        d = tempfile.mkdtemp(prefix="fx_")
        self.addCleanup(shutil.rmtree, d, True)
        sids = ["s_178000000000%d_%d" % (i, i) for i in range(n)]
        for sid in sids:
            r = os.path.join(d, "reel_" + sid)
            os.makedirs(r)
            with io.open(os.path.join(r, "f_1780000000000.jpg"), "w") as fh:
                fh.write("x")
        for name in extra:
            r = os.path.join(d, name)
            os.makedirs(r)
            with io.open(os.path.join(r, "f_1780000000000.jpg"), "w") as fh:
                fh.write("x")
        for fn in ("chronicle_swept.json", "vault_swept.json"):
            with io.open(os.path.join(d, fn), "w", encoding="utf-8") as fh:
                json.dump({x: {"pages": pages, "rows": 2, "banked": True} for x in sids}, fh)
        return d, sids

    def _plan(self, d, sids, **kw):
        import frame_authority as _fa
        wi, ds = _fa.witness_index, rr._durable_sessions
        try:
            _fa.witness_index = lambda *a, **k: {"haveIndex": True, "ok": True,
                                                 "sessions": {}, "frames": {}, "perStore": {}}
            rr._durable_sessions = lambda *a, **k: (set(sids), True, "")
            r = rr.plan(hist_dir=d, **kw)
        finally:
            _fa.witness_index, rr._durable_sessions = wi, ds
        return {k: v for k, v in (r.get("coverage") or {}).items() if v}

    def test_unparseable_dirs_do_not_take_the_recent_shields_slots(self):
        """REG-571 — measured: 5 junk siblings took all 3 slots, eligible went 2 -> 5."""
        d, s = self._fx()
        clean = self._plan(d, s, keep_recent=3)
        d2, s2 = self._fx(extra=["reel_backup_" + c for c in "abcde"])
        junked = self._plan(d2, s2, keep_recent=3)
        self.assertEqual(junked.get("eligible"), clean.get("eligible"),
                         "unparseable sibling directories displaced real reels out of the recent "
                         "shield: eligible %s -> %s while coverage still reported recent=%s"
                         % (clean.get("eligible"), junked.get("eligible"), junked.get("recent")))

    def test_a_negative_keep_recent_is_refused_not_silently_ignored(self):
        """REG-572 — `reels[-(-6):]` is a suffix from the front: empty, so the shield vanished."""
        d, s = self._fx()
        with self.assertRaises(ValueError):
            self._plan(d, s, keep_recent=-6)

    def test_a_boolean_page_count_does_not_read_as_one_page(self):
        """REG-573 — bool is a subclass of int, so `pages: true` stamped a TOMBSTONE with
        "read (1 pages) and sealed by BOTH lanes" — the permanent record of an act with no undo."""
        d, s = self._fx(pages=True)
        cov = self._plan(d, s, keep_recent=0)
        self.assertFalse(cov.get("eligible"),
                         "pages=True released %s reel(s); a boolean is not a page count" % cov)
        self.assertTrue(cov.get("ledger-unreadable"), cov)

    def test_an_unparseable_page_count_holds_instead_of_escaping(self):
        """REG-573 — `pages: "many"` raised out of plan(), and _retention_loop swallows it."""
        d, s = self._fx(pages="many")
        cov = self._plan(d, s, keep_recent=0)          # must not raise
        self.assertTrue(cov.get("ledger-unreadable"), cov)

    def test_an_HONEST_ledger_still_releases(self):
        """BASELINE — or these fixes bought safety by holding everything for ever."""
        d, s = self._fx(pages=3)
        cov = self._plan(d, s, keep_recent=0)
        self.assertTrue(cov.get("eligible"),
                        "a clean ledger released nothing at all: %s" % cov)



class TheShieldHasOneOrderAndAnExitClock(unittest.TestCase):
    """REG-1812 / REG-1813 — recent_order is the ONE order (the shield is its tail, the shelf shows it), and
    shield_exits dates when each older reel left the shield: the name epoch of the reel `keep` places newer."""

    def test_the_shield_is_the_tail_of_the_order_whatever_order_the_reels_arrive_in(self):
        names = ["reel_s_%d_%d" % (1000 + i * 10, i) for i in range(7)] + ["reel_backup_x", "reel_s_1030_tie"]
        fwd, back = rr.recent_order(names), rr.recent_order(list(reversed(names)))
        self.assertEqual(fwd, back, "two callers handed the same reels in another order got another order")
        self.assertNotIn("reel_backup_x", fwd, "REG-571: an unparseable name stood in the order")
        self.assertEqual(rr.recent_shield(names, 3), set(fwd[-3:]))

    def test_an_older_reel_left_when_the_keep_th_newer_one_arrived(self):
        names = ["reel_s_%d_%d" % (1000 + i * 10, i) for i in range(6)]
        got = rr.shield_exits(names, 4)
        self.assertEqual(got, {names[0]: 1040, names[1]: 1050}, got)
        self.assertFalse(set(got) & rr.recent_shield(names, 4), "a reel inside the shield was given an exit")
        self.assertEqual(rr.shield_exits(names, 6), {})
        self.assertEqual(rr.shield_exits(names[:1], 0), {names[0]: 1000}, "no shield: out from its own arrival")


if __name__ == "__main__":
    unittest.main(verbosity=2)
