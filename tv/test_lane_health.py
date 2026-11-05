#!/usr/bin/env python3
"""Guards for lane health. Every one asserts a REFUSAL as well as a pass — the thing being replaced
is a watchdog that stayed silent for five days, so silence must never be a pass here."""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lane_health as LH

HOUR = 3600000.0


RED_PROOF = [
    {
        "why": 'the law requires this text in lane_health.py, where it occurs exactly once and in no other file the gate names; deleting it must turn the gate red',
        "file": 'lane_health.py',
        "find": 'unanswerable',
        "replace": '_HEART2_TAMPERED_',
        "matches": 1,
    },
]

class _Tree(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="lane-")
        self.addCleanup(shutil.rmtree, self.root, True)
        self._here = LH.HERE
        LH.HERE = self.root
        self.addCleanup(setattr, LH, "HERE", self._here)
        self.now = 1_000_000 * HOUR

    def _write(self, name, blob):
        with io.open(os.path.join(self.root, name), "w", encoding="utf-8") as fh:
            json.dump(blob, fh)

    def _seal(self, n, hours_ago):
        return {"s_%d" % i: {"ts": self.now - hours_ago * HOUR, "rows": 1} for i in range(n)}


class TestFreshness(_Tree):
    def test_a_lane_that_worked_recently_is_FRESH(self):
        self._write("chronicle_swept.json", self._seal(3, 2))
        self.assertEqual(LH.lane("chronicle", self.now)["state"], "fresh")

    def test_a_lane_past_its_threshold_is_STALLED_and_says_how_long(self):
        self._write("vault_swept.json", self._seal(8, 136.7))
        r = LH.lane("vault", self.now)
        self.assertEqual(r["state"], "stalled")
        self.assertAlmostEqual(r["ageHours"], 136.7, places=0)
        self.assertIn("STOPPED", r["why"])

    def test_an_UNREADABLE_store_is_UNKNOWN_never_healthy(self):
        # ⚠ the whole point: "cannot tell" must not read the same as "fine"
        with io.open(os.path.join(self.root, "vault_swept.json"), "w", encoding="utf-8") as fh:
            fh.write("{not json")
        r = LH.lane("vault", self.now)
        self.assertEqual(r["state"], "unknown")
        self.assertIn("never healthy", r["why"])

    def test_a_MISSING_store_is_UNKNOWN_not_fresh(self):
        self.assertEqual(LH.lane("vault", self.now)["state"], "unknown")

    def test_seals_with_NO_TIMESTAMP_are_UNKNOWN_not_fresh(self):
        # a lane with 40 sealed rows and no clock cannot answer "how long ago"
        self._write("vault_swept.json", {"s_%d" % i: {"rows": 1} for i in range(40)})
        r = LH.lane("vault", self.now)
        self.assertEqual(r["state"], "unknown")
        self.assertIn("unanswerable", r["why"])


class TestDivergenceIsTheCorroborator(_Tree):
    def test_one_lane_ahead_of_the_other_is_DIVERGED_and_names_the_deleter(self):
        self._write("chronicle_swept.json", self._seal(36, 49))
        self._write("vault_swept.json", {"s_0": {"ts": self.now, "rows": 1}})
        d = LH.divergence("chronicle", "vault")
        self.assertEqual(d["state"], "diverged")
        self.assertEqual(d["onlyInFirst"], 35)
        self.assertIn("frame deleter", d["why"])

    def test_lanes_covering_the_same_sessions_are_ALIGNED(self):
        same = self._seal(5, 1)
        self._write("chronicle_swept.json", same)
        self._write("vault_swept.json", same)
        self.assertEqual(LH.divergence("chronicle", "vault")["state"], "aligned")

    def test_divergence_with_an_unreadable_side_is_UNKNOWN(self):
        self._write("chronicle_swept.json", self._seal(3, 1))
        self.assertEqual(LH.divergence("chronicle", "vault")["state"], "unknown")

    def test_divergence_is_DIRECTIONAL(self):
        # vault ahead of chronicle is a different fact and must not read as the same defect
        self._write("chronicle_swept.json", {"s_0": {"ts": self.now, "rows": 1}})
        self._write("vault_swept.json", self._seal(9, 1))
        self.assertEqual(LH.divergence("chronicle", "vault")["state"], "aligned")
        self.assertEqual(LH.divergence("vault", "chronicle")["state"], "diverged")


class TestDivergenceCountsOnlyWhatALaneCanStillActOn(_Tree):
    """★ v2437 — THE CORROBORATOR WAS ALWAYS-RED A SECOND TIME, AND NO FIXTURE COULD SEE IT.

    v2302 fixed the DIALECT (`reel_` prefix) and the identical defect survived one level up:
    divergence() differenced two LIFETIME ledgers against nothing on disk. Measured on his tree
    2026-09-02 — 401 chronicle entries, 30 vault, 40 reels on disk, 371 "diverged", of which
    **346 have no footage at all**. The vault lane can only sweep a directory, so those 346 can
    never be sealed by any amount of lane work, and the number GROWS every time footage is
    correctly pruned. A red that gets worse the better the system behaves carries no information.

    ⚠ WHY EVERY EXISTING TEST STAYED GREEN THROUGH IT: none of them creates footage, so the
    hist dir never existed and the fallback path was the only one a fixture ever ran. That is
    [[gate-blind-to-unexercised-input]] exactly — real gate, real data, still green — so these
    cases exist to exercise the branch his tree actually takes.
    """

    def _reel(self, sid):
        os.makedirs(os.path.join(self.hist, "reel_%s" % sid), exist_ok=True)

    def setUp(self):
        _Tree.setUp(self)
        # ⚠ point TV_HIST at the fixture. Without this the module resolves HERE/frames/hist —
        # and HERE is already the temp root, so it would be absent rather than wrong; the env
        # var is set anyway because a future default change must not silently read his footage.
        self.hist = os.path.join(self.root, "frames", "hist")
        os.makedirs(self.hist)
        self._old_hist = os.environ.get("TV_HIST")
        os.environ["TV_HIST"] = self.hist
        self.addCleanup(self._restore_hist)

    def _restore_hist(self):
        if self._old_hist is None:
            os.environ.pop("TV_HIST", None)
        else:
            os.environ["TV_HIST"] = self._old_hist

    def test_a_divergence_whose_FOOTAGE_IS_GONE_reads_as_aligned(self):
        """The 346 case. No lane can seal a reel that no longer exists, so it is not a fault."""
        self._write("chronicle_swept.json", self._seal(9, 1))
        self._write("vault_swept.json", {"s_0": {"ts": self.now, "rows": 1}})
        # no reel_* directories at all -> every difference is historic
        d = LH.divergence("chronicle", "vault")
        self.assertEqual(d["state"], "aligned",
                         "8 sessions differ but NONE has footage — a lane cannot act on any of "
                         "them, so calling it diverged is a red that can never be cleared")
        self.assertEqual(d["actionable"], 0)
        # ⚠ v2439 — THIS ASSERTED THE PROSE AND WENT RED ON A DELIBERATE REWORDING. The law is
        # "footage-less differences do not count as a fault and are still REPORTED"; the sentence
        # that carried the second half moved into the payload when a cross-family read pointed out
        # that a larger unfixable number inside the actionable sentence is the number that sticks.
        # Pin the FIELD, which is where the fact now lives and cannot be lost to an edit.
        # [[regression-guard]] §4 — pin the law, not the number, and prose is a number here.
        self.assertEqual(d["historyOnly"], 8,
                         "the historic count vanished. It must stay REPORTED even though it no "
                         "longer competes with the actionable one in the sentence — dropping it "
                         "would make 'aligned' unexplainable")

    def test_only_the_sessions_WITH_footage_count_as_diverged(self):
        """The 25 case. Mixed tree: some differences are actionable, most are not."""
        self._write("chronicle_swept.json", self._seal(9, 1))
        self._write("vault_swept.json", {"s_0": {"ts": self.now, "rows": 1}})
        self._reel("s_3")
        self._reel("s_7")
        d = LH.divergence("chronicle", "vault")
        self.assertEqual(d["state"], "diverged")
        self.assertEqual(d["actionable"], 2, "only s_3 and s_7 still have footage")
        self.assertEqual(d["historyOnly"], 6)
        self.assertEqual(d["onlyInFirst"], 8, "the raw lifetime difference must stay truthful")
        self.assertEqual(sorted(d["sample"]), ["s_3", "s_7"],
                         "the sample must name reels somebody can actually go and sweep")

    def test_a_reel_on_disk_that_BOTH_lanes_swept_is_not_a_divergence(self):
        same = self._seal(4, 1)
        self._write("chronicle_swept.json", same)
        self._write("vault_swept.json", same)
        for i in range(4):
            self._reel("s_%d" % i)
        self.assertEqual(LH.divergence("chronicle", "vault")["state"], "aligned")

    def test_the_reel_DIALECT_still_normalises_against_disk(self):
        """A reel dir is `reel_s_x`; vault keys are `s_x`. Comparing those raw is the v2302 bug
        arriving through the new door — so it is pinned here too, not just at _sid."""
        self._write("chronicle_swept.json", {"reel_s_9": {"ts": self.now, "rows": 1}})
        self._write("vault_swept.json", {"s_1": {"ts": self.now, "rows": 1}})
        self._reel("s_9")
        d = LH.divergence("chronicle", "vault")
        self.assertEqual(d["actionable"], 1,
                         "reel_s_9 on disk must match chronicle's `reel_s_9` key; if the prefix "
                         "is compared raw this reads 0 and the divergence silently vanishes")

    def test_UNREADABLE_footage_is_the_RAW_difference_and_SAYS_SO(self):
        """⚠ THE FALSE-GREEN THIS FIX COULD HAVE INTRODUCED. If a missing hist dir returned an
        empty SET instead of None, every session would be 'no footage' and every divergence
        would read ALIGNED — a green corroborator produced by not looking, which is worse than
        the always-red it replaced. [[unknown-stays-unknown]]"""
        self._write("chronicle_swept.json", self._seal(9, 1))
        self._write("vault_swept.json", {"s_0": {"ts": self.now, "rows": 1}})
        os.environ["TV_HIST"] = os.path.join(self.root, "no-such-dir")
        d = LH.divergence("chronicle", "vault")
        self.assertEqual(d["state"], "diverged",
                         "footage unreadable must NOT collapse to aligned — that would be a "
                         "clean bill of health earned by failing to look")
        self.assertIsNone(d["historyOnly"], "unknown is not zero")
        self.assertIn("could not be listed", d["why"],
                      "the answer must disclose that it is the raw difference, not a measurement")

    def test_it_reads_HIS_footage_only_through_TV_HIST(self):
        """[[feedback-fixtures-never-touch-live-data]] — guard the FIXTURE, not the call site."""
        import inspect
        src = inspect.getsource(LH._reels_on_disk)
        code = "\n".join(l.split("#", 1)[0] for l in src.split("\n"))
        self.assertIn('os.environ.get("TV_HIST")', code,
                      "a fixture that repoints the ledgers and not the footage would compare "
                      "test sessions against his real reels")


class TestTheReportRefusesToBeGreenOnAnyProblem(_Tree):
    def test_everything_fresh_and_aligned_is_ok(self):
        same = self._seal(4, 1)
        self._write("chronicle_swept.json", same)
        self._write("vault_swept.json", same)
        self.assertTrue(LH.report(self.now)["ok"])

    def test_ONE_stalled_lane_makes_the_whole_report_not_ok(self):
        self._write("chronicle_swept.json", self._seal(4, 1))
        self._write("vault_swept.json", self._seal(4, 200))
        # v2308 — say what this fixture owes, or report() asks the real machine and a
        # deliberately stalled lane reads as idle on a tree where nothing is owed.
        self.assertFalse(LH.report(self.now, owed={"chronicle": 2, "vault": 2})["ok"])

    def test_a_DIVERGENCE_ALONE_makes_it_not_ok_even_when_both_lanes_are_fresh(self):
        # ⚠ this is the exact shape that hid the five-day stall: each lane correct on its own
        self._write("chronicle_swept.json", self._seal(9, 1))
        self._write("vault_swept.json", {"s_0": {"ts": self.now, "rows": 1}})
        rep = LH.report(self.now)
        self.assertTrue(all(l["state"] == "fresh" for l in rep["lanes"].values()))
        self.assertFalse(rep["ok"], "both lanes fresh but diverged, and the report called it ok")

    def test_it_writes_nothing(self):
        import inspect
        src = inspect.getsource(LH)
        for forbidden in ('open(', "os.remove", "unlink", "rmtree"):
            if forbidden == 'open(' and 'io.open' in src:
                continue          # io.open for READING is the module's whole job
            self.assertNotIn(forbidden, src, "lane_health must stay a reader; found %r" % forbidden)
        self.assertNotIn('"w"', src, "lane_health opened something for writing")



class TestIdleIsNotStopped(_Tree):
    """★ A LANE WITH NOTHING TO DO IS NOT A LANE THAT STOPPED.

    lane() measured ONE thing — how long since work last happened — so a lane that had swept
    everything reported the same "STOPPED" as a broken one. MEASURED on his console 2026-08-30,
    two checks of the same doctor contradicting each other in the same breath:
        reel extract      ok       all 28 reel(s) have been read
        extraction lanes  missing  chronicle: last did work 63.5 h ago -- this lane has STOPPED
    And it mattered the moment it was fixed: with owed counted, the chronicle lane is IDLE (0 owed)
    while the VAULT lane is genuinely STALLED with 2 reels and 452 MB it has never read. Those two
    had been telling the same story.
    """

    def test_stale_with_nothing_owed_is_IDLE(self):
        self._write("chronicle_swept.json", self._seal(36, 64.0))
        r = LH.lane("chronicle", self.now, owed=0)
        self.assertEqual(r["state"], "idle")
        self.assertIn("IDLE, not stopped", r["why"])
        self.assertNotIn("STOPPED", r["why"])

    def test_stale_with_work_owed_is_still_STALLED(self):
        self._write("vault_swept.json", self._seal(8, 151.5))
        r = LH.lane("vault", self.now, owed=2)
        self.assertEqual(r["state"], "stalled")
        self.assertIn("STOPPED", r["why"])

    def test_an_UNCOUNTED_lane_is_STALLED_and_says_idle_could_not_be_ruled_in(self):
        """⚠ THE LAW THIS WHOLE CHANGE TURNS ON. "nothing was owed" and "nobody counted" must never
        reach the same box, and the cheap wrong version of this fix — treat missing as zero — would
        have silenced every genuinely stalled lane on any venue that cannot count."""
        self._write("vault_swept.json", self._seal(8, 151.5))
        r = LH.lane("vault", self.now, owed=None)
        self.assertEqual(r["state"], "stalled")
        self.assertIn("IDLE cannot be ruled in", r["why"])

    def test_a_FRESH_lane_is_never_relabelled_by_the_owed_count(self):
        self._write("chronicle_swept.json", self._seal(3, 2))
        for owed in (0, 2, None):
            self.assertEqual(LH.lane("chronicle", self.now, owed=owed)["state"], "fresh")

    def test_the_report_is_not_red_merely_because_a_lane_is_idle(self):
        self._write("chronicle_swept.json", self._seal(36, 64.0))
        self._write("vault_swept.json", self._seal(8, 2.0))
        rep = LH.report(self.now)
        ch = rep["lanes"]["chronicle"]
        # ⚠ assert on the LANE'S OWN sentence, never on the word "chronicle" anywhere in why:
        # the first cut did that and caught the DIVERGENCE line ("28 session(s) the chronicle lane
        # covered that vault never did"), which is a different and entirely real problem. A guard
        # that matches a substring of an unrelated finding is measuring the wrong thing.
        if ch["state"] == "idle":
            self.assertNotIn(ch["why"], rep["why"],
                             "an idle lane is healthy and must not be listed as a problem")
            self.assertIn("IDLE, not stopped", ch["why"])




class TestTheCorroboratorCanSayALIGNED(_Tree):
    """★ A DIVERGENCE CHECK THAT HAS NEVER BEEN SEEN SAY "ALIGNED" HAS NEVER BEEN PROVEN ABLE TO.

    MEASURED on his tree 2026-08-30: chronicle_swept.json keys carry a `reel_` prefix and
    vault_swept.json keys do not, and divergence() differenced them raw. It reported 36 diverged
    where the truth was 20 — and 8 reels covered by BOTH lanes were counted as diverged purely
    because of the spelling. Being wrong by 16 was the small half. The large half: the difference
    was non-empty BY CONSTRUCTION, so this check could never report agreement on any tree, which
    makes its red mean nothing at all. [[feedback-blind-fixture-green-gate]]
    """

    def _ids(self, ids):
        """A sealed store keyed by EXACTLY these ids — the point of these tests is the spelling,
        so the fixture may not go through a helper that invents its own keys."""
        return {i: {"ts": self.now - HOUR, "rows": 1} for i in ids}

    def test_the_same_sessions_in_BOTH_dialects_read_as_aligned(self):
        self._write("chronicle_swept.json", self._ids(["reel_s_1_a", "reel_s_2_b"]))
        self._write("vault_swept.json", self._ids(["s_1_a", "s_2_b"]))
        d = LH.divergence("chronicle", "vault")
        self.assertEqual(d["state"], "aligned",
                         "the same two sessions, spelled the two ways the real stores spell them, "
                         "must not read as diverged: %s" % d.get("why"))

    def test_a_REAL_gap_still_diverges(self):
        self._write("chronicle_swept.json", self._ids(["reel_s_1_a", "reel_s_2_b"]))
        self._write("vault_swept.json", self._ids(["s_1_a"]))
        d = LH.divergence("chronicle", "vault")
        self.assertEqual(d["state"], "diverged")
        # ⚠ v2439 — was `assertIn("1 session", why)` and went red when the sentence started saying
        # "reel(s)" instead. The LAW is that exactly one difference is reported and that the reader
        # is told what to DO about it; the noun is presentation. Asserting the count as a FIELD
        # survives every rewording, and the action clause is pinned separately because a panel that
        # diagnoses and never prescribes was the cross-family finding this ship exists to answer.
        self.assertEqual(d["onlyInFirst"], 1)
        self.assertIn("sweep", d["why"].lower(),
                      "the sentence names no action. A reader learns something is wrong and not "
                      "what to do, which is the state this check was written to replace.")

    def test_the_normaliser_is_idempotent_and_leaves_bare_ids_alone(self):
        self.assertEqual(LH._sid("reel_s_1_a"), "s_1_a")
        self.assertEqual(LH._sid("s_1_a"), "s_1_a")
        self.assertEqual(LH._sid(LH._sid("reel_s_1_a")), "s_1_a")



class TestBlockedIsNotStopped(_Tree):
    """★ v3265 — A LANE THAT OWES WORK IT CANNOT TOUCH IS BLOCKED, AND BLOCKED IS NOT STOPPED.

    `TestIdleIsNotStopped` above split "stale" into IDLE (nothing owed) and STOPPED (work owed).
    Two boxes. A third state walked in on 2026-09-17 and had nowhere to go:

        the doctor said   chronicle lane STOPPED 62.2 h ago
        the switch        TV_CHRON_AUTOREAD default "1", unset in env -> ON
        the thread        ("tvd-chron-autoread", _chron_autoread_loop) -> IN THE ROSTER, alive
        the sweeper       "nothing waiting: every reel with a chosen Chronicle focus has been swept"
        owed by the rule  4    (…_1789419985817_32179 and three more, named)
        sweepable NOW     0

    Nothing was stopped. The lane owes four reads and may perform none of them, because none of
    those reels has a chosen Chronicle focus — it is waiting on a declaration nobody has made.
    The word "STOPPED" sent me hunting a dead thread that was alive, switched on and correct.

    ⚠ The cheap wrong fix is to call it IDLE and move on. That HIDES four reels that genuinely owe
    work. The other cheap wrong fix is to treat an uncounted `actionable` as zero, which would mark
    every lane BLOCKED on any venue that cannot count and turn the whole check off.
    [[unknown-stays-unknown]] [[zero-needs-a-denominator]]
    """

    def test_owed_but_NONE_actionable_is_BLOCKED_and_refuses_the_word_stopped(self):
        self._write("chronicle_swept.json", self._seal(36, 64.0))
        r = LH.lane("chronicle", self.now, owed=4, actionable=0)
        self.assertEqual(r["state"], "blocked")
        self.assertIn("BLOCKED, not stopped", r["why"])
        self.assertNotIn("STOPPED", r["why"])
        # the count he can act on travels WITH the verdict, so a reader need not re-derive the gap
        self.assertEqual(r["actionable"], 0)

    def test_an_UNCOUNTED_actionable_leaves_a_stalled_lane_STALLED(self):
        """⚠⚠ THE LAW THE WHOLE THIRD STATE TURNS ON, and the exact sibling of the `owed=None`
        law twenty lines up. "it can act on nothing" and "nobody counted what it can act on" must
        never reach the same box. If they do, the venue with no counter reports every stopped lane
        as merely blocked — an off switch wearing a verdict."""
        self._write("vault_swept.json", self._seal(8, 151.5))
        r = LH.lane("vault", self.now, owed=2, actionable=None)
        self.assertEqual(r["state"], "stalled")
        self.assertIn("STOPPED", r["why"])

    def test_owed_work_it_CAN_do_is_still_STOPPED(self):
        """A lane holding work it is able to perform, and not performing it, is the original
        fault and must keep the original word."""
        self._write("vault_swept.json", self._seal(8, 151.5))
        r = LH.lane("vault", self.now, owed=2, actionable=2)
        self.assertEqual(r["state"], "stalled")
        self.assertIn("STOPPED", r["why"])
        self.assertNotIn("BLOCKED", r["why"])

    def test_nothing_owed_stays_IDLE_even_when_actionable_is_zero(self):
        """owed=0 and actionable=0 is the SWEPT-EVERYTHING lane. Zero of zero is not blocked."""
        self._write("chronicle_swept.json", self._seal(36, 64.0))
        r = LH.lane("chronicle", self.now, owed=0, actionable=0)
        self.assertEqual(r["state"], "idle")
        self.assertIn("IDLE, not stopped", r["why"])

    def test_a_FRESH_lane_is_never_relabelled_BLOCKED(self):
        self._write("chronicle_swept.json", self._seal(3, 2))
        for act in (0, 2, None):
            self.assertEqual(LH.lane("chronicle", self.now, owed=4, actionable=act)["state"],
                             "fresh")

    def test_a_BLOCKED_lane_still_makes_the_whole_report_NOT_ok(self):
        """⚠ THE JOIN. A new verdict word that no consumer knows is an off switch: `health_engine`
        collected `state == "stalled"` and nothing else, so on the day BLOCKED shipped, a lane
        owing four reads would have fallen out of the bad list and landed on "every extraction lane
        is fresh and aligned" — a GREEN HEART over the fault being fixed. [[the-unjoined-end]]"""
        import sys as _sys
        import health_engine as HE
        rep = {"lanes": {"chronicle": {"state": "blocked", "owed": 4, "lane": "chronicle",
                                       "why": "chronicle: BLOCKED, not stopped"}},
               "divergences": []}
        class _Stub:
            @staticmethod
            def report(*a, **k):
                return rep
        real = _sys.modules.get("lane_health")
        _sys.modules["lane_health"] = _Stub
        try:
            row = HE.check_lanes()
        finally:
            if real is not None:
                _sys.modules["lane_health"] = real
            else:
                _sys.modules.pop("lane_health", None)
        self.assertNotEqual(row["state"], "ok", "the heart went GREEN over a blocked lane")
        self.assertIn("blocked", row["line"])
        self.assertNotIn("has stopped", row["line"])


class TestTheDivergenceKnowsWhatIsOWED(TestDivergenceCountsOnlyWhatALaneCanStillActOn):
    """★ v3266 — "STILL ON DISK AND UNSEALED" AND "THE LANE OWES IT" ARE DIFFERENT QUESTIONS,
    AND THE PANEL WAS ANSWERING THE SECOND WITH THE FIRST.

    v2437 taught this check to count only reels whose footage still exists. Correct, and still
    one question short. MEASURED on his console 2026-09-17, in the sentence the heart LEADS with:

        9 reel(s) still on disk need a vault sweep — chronicle read them, vault never sealed
        them ... Sweep vault to free them.

    Asked of `reel_retention.plan()`, all nine:   4 test-fixture, 5 recent.
    Asked of the vault lane itself (`_vault_owed_reels`): it owes **3**, and NOT ONE of them is
    in the nine. The panel prescribed a sweep the lane owes for none of the reels named, and
    following it is the 2026-09-01 incident the retention rules exist to prevent — a queue of 26
    reels, 10 explicitly held, up to 97 paid reads.

    The count was right and the WORD OVER IT had stopped being true. [[label-outlived-referent]]

    ⚠ The trap in fixing it is making the check quieter. A reel on disk that no lane owes AND no
    retention rule names is a REAL fault — nothing automatic will ever deliver it — and it is one
    line of carelessness away from being swept into the held-by-design bucket and never seen.
    """

    def _ledgers(self, n_diverged):
        """chronicle has swept n reels the vault has not, and all of them still have footage."""
        sids = ["s_%d" % i for i in range(n_diverged)]
        self._write("chronicle_swept.json",
                    {s: {"ts": self.now, "rows": 1} for s in sids})
        self._write("vault_swept.json", {"s_other": {"ts": self.now, "rows": 1}})
        for s in sids:
            self._reel(s)
        return sids

    def test_held_BY_DESIGN_is_aligned_and_STILL_SAYS_THE_NUMBER(self):
        """⚠ It must not go quiet. A reader who saw "9" yesterday reads today's silence as the
        reels having vanished. Same number, true word, named reasons."""
        sids = self._ledgers(3)
        d = LH.divergence("chronicle", "vault", owed_by=set(),
                          held={sids[0]: "test-fixture", sids[1]: "recent", sids[2]: "recent"})
        self.assertEqual(d["state"], "aligned")
        self.assertEqual(d["heldByDesign"], 3)
        self.assertIn("3 reel(s)", d["why"])
        self.assertIn("2 recent", d["why"])
        self.assertIn("1 test-fixture", d["why"])
        self.assertNotIn("Sweep", d["why"], "it still prescribes a sweep nobody owes")

    def test_a_reel_NOBODY_owes_and_NOTHING_holds_stays_RED(self):
        """⚠⚠ THE LAW THE WHOLE CHANGE TURNS ON. This is the only genuinely broken state in the
        family and the easiest one to lose while making the panel calmer."""
        sids = self._ledgers(2)
        d = LH.divergence("chronicle", "vault", owed_by=set(),
                          held={sids[0]: "test-fixture"})     # sids[1] held by NOTHING
        self.assertEqual(d["state"], "diverged")
        self.assertEqual(d["orphan"], 1)
        self.assertIn("nothing automatic will ever deliver them", d["why"])

    def test_a_reel_the_lane_DOES_owe_still_prescribes_the_sweep(self):
        sids = self._ledgers(2)
        d = LH.divergence("chronicle", "vault", owed_by={sids[0]},
                          held={sids[1]: "recent"})
        self.assertEqual(d["state"], "diverged")
        self.assertEqual(d["waiting"], 1)
        self.assertEqual(d["heldByDesign"], 1)
        self.assertIn("need a vault sweep", d["why"])
        self.assertIn("Sweep vault to free them", d["why"])
        self.assertIn("held ON PURPOSE", d["why"], "the held ones vanished from the sentence")

    def test_an_UNCOUNTED_doctrine_leaves_the_OLD_sentence_exactly(self):
        """⚠ owed_by=None means nobody could ask the lane. Collapsing that into "owes nothing"
        turns the check off wherever the doctrine cannot be read — the same discipline `owed` and
        `actionable` carry. [[unknown-stays-unknown]]"""
        self._ledgers(2)
        d = LH.divergence("chronicle", "vault")          # no doctrine injected at all
        self.assertEqual(d["state"], "diverged")
        self.assertEqual(d["waiting"], 2)
        self.assertEqual(d["heldByDesign"], 0)
        self.assertIn("need a vault sweep", d["why"])


class TestTheThirdStateReachesEveryConsumer(_Tree):
    """★ v3266 — v3265 SHIPPED A NEW VERDICT WORD AND JOINED ONE OF ITS THREE CONSUMERS.

    `health_engine` was taught BLOCKED. `report()["ok"]` and `say()` were not, and both were
    found by grepping for the OLD word after the ship rather than before it. A new verdict is a
    join at every consumer or it is an off switch at the ones that were missed.
    [[the-unjoined-end]]
    """

    def test_report_is_NOT_ok_when_a_lane_is_blocked(self):
        self._write("chronicle_swept.json", self._seal(36, 64.0))
        self._write("vault_swept.json", self._seal(8, 2.0))
        rep = LH.report(self.now, owed={"chronicle": 4}, actionable={"chronicle": 0})
        self.assertEqual(rep["lanes"]["chronicle"]["state"], "blocked")
        self.assertFalse(rep["ok"], "report() went green over a lane that owes 4 and can do none")

    def test_say_gives_blocked_its_OWN_mark(self):
        self._write("chronicle_swept.json", self._seal(36, 64.0))
        self._write("vault_swept.json", self._seal(8, 2.0))
        rep = LH.report(self.now, owed={"chronicle": 4}, actionable={"chronicle": 0})
        line = [l for l in LH.say(rep) if "chronicle:" in l][0]
        self.assertTrue(line.startswith("\U0001f7e1"),
                        "blocked has no mark of its own, so it reads as either healthy or dead: %r"
                        % line[:12])

    def test_a_FIXTURE_never_asks_the_LIVE_machine_what_is_actionable(self):
        """⚠⚠ v3265 RE-OPENED THE HOLE v2308 CLOSED ONE LINE ABOVE IT. `actionable_counts()`
        imports control_app and asks the REAL console, and v3265 called it unconditionally from
        report() — so a fixture sealing a deliberately stalled lane would have had its verdict
        decided by whatever HIS machine happened to owe. A caller supplying `owed` is a fixture
        and must get UNCOUNTED, which preserves the verdict it is actually testing."""
        self._write("vault_swept.json", self._seal(8, 151.5))
        calls = []
        real = LH.actionable_counts
        real_rs = LH.lane_reasons          # REG-3200 - report() asks lane_reasons now; both are the live machine
        LH.actionable_counts = lambda: calls.append(1) or {"vault": 0}
        LH.lane_reasons = lambda: calls.append(2) or {"vault": {"actionable": 0, "why": "live"}}
        try:
            rep = LH.report(self.now, owed={"vault": 2})
        finally:
            LH.actionable_counts = real
            LH.lane_reasons = real_rs
        self.assertEqual(calls, [], "report() measured the LIVE machine for a fixture")
        self.assertIsNone(rep["lanes"]["vault"]["actionable"])
        self.assertEqual(rep["lanes"]["vault"]["state"], "stalled",
                         "the fixture's own verdict changed because of the venue it ran on")


if __name__ == "__main__":
    try:
        import console_safe as _cs
        _cs.enable()
    except Exception:
        pass
    unittest.main(verbosity=1)
