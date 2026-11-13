#!/usr/bin/env python3
"""THE CORROBORATOR — what the engines say about EACH OTHER.

Konyo, 2026-08-28: "the system needs an eagle eye corroborator, the engines all communicating...
diablo doctor self heals self fixes, scars its own."

WHY THIS EXISTS, and it is not a hunch — it is the shape of every serious defect found on
2026-08-28, all four of them found by hand, none by a gate:

    19 vs 2      the new vault watchdog's work list against reel_retention's own vault-blocked
                 bucket. Both computed correctly. The watchdog would have started SEVENTEEN
                 unnecessary paid sweeps, three of them over test fixtures.
    1263 vs 403  the shadow ledger's `names` against the uniques universe. 1263 distinct names is
                 arithmetically impossible; the field was counting repeat scorings. It had already
                 crossed the threshold whose sentence is "The record is worth a decision".
    157 vs 7     two payload fields both called `owned` — the board's stash backup and the vault
                 lane's own ledger. Both true, about different quantities, and nothing said so.
    36 vs 30     the durable sweep memory against the reels on disk. True, and unlabelled, and it
                 nearly got six read-records deleted as "ghosts".

EVERY ONE was a pair of numbers that were each right and wrong TOGETHER. No single engine could
have caught its own; each was healthy by its own lights. console_doctor asks 21 questions about
whether each engine is well. Nothing asked whether they AGREE.

THE RULES THIS FILE OBEYS
  * IT NEVER WRITES. Reads only, like chronicle_retro. A corroborator that repairs is a corroborator
    whose evidence you cannot trust, because it has already acted on it.
  * IT NEVER AVERAGES, AND IT NEVER PICKS A SIDE. Founding rule 3: two checks disagreeing IS the
    finding. Both numbers are reported with the name of who said them, and the disagreement is the
    result — not an error bar, not a "roughly".
  * UNKNOWN IS NOT ZERO AND NOT AGREEMENT. If either side cannot be computed the invariant reports
    UNKNOWN and says which side went dark. An invariant that silently passes when its inputs are
    missing is worse than no invariant. [[unknown-stays-unknown]]
  * AN INVARIANT THAT CANNOT FAIL IS NOT AN INVARIANT. Each carries `prove`, a description of the
    state that would break it, and `selftest()` drives every one of them to a RED verdict against
    synthetic inputs — because a corroborator nobody has seen disagree is exactly the green that
    lies. [[regression-guard]] [[feedback-blind-fixture-green-gate]]
"""

import io
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))

AGREE = "agree"
DISAGREE = "disagree"
UNKNOWN = "unknown"


class Reading(object):
    """One side of an invariant: a number, who computed it, or why it could not be had."""

    __slots__ = ("value", "who", "why")

    def __init__(self, value=None, who="", why=None):
        self.value = value
        self.who = who
        self.why = why

    @property
    def known(self):
        return self.value is not None and self.why is None

    def __repr__(self):
        return "<%s=%r%s>" % (self.who, self.value, "" if self.known else " UNKNOWN")


def _reading(who, fn):
    """Compute one side, turning any failure into an honest UNKNOWN rather than a zero."""
    try:
        v = fn()
    except Exception as e:
        return Reading(None, who, "%s could not be asked: %s" % (who, str(e)[:90]))
    if v is None:
        return Reading(None, who, "%s answered UNKNOWN" % who)
    return Reading(v, who)


# ── THE INVARIANTS ───────────────────────────────────────────────────────────────────────────
# Each is (key, what, prove, left_name, left_fn, right_name, right_fn, relation).
# `relation` is "==" or "<=" and is applied LEFT rel RIGHT.

def _inv_vault_worklist():
    """★ THE v2223 NEAR-MISS — AND FOR MONTHS THIS INVARIANT CORROBORATED A THING AGAINST ITSELF.

    MEASURED 2026-09-01 on his live tree, and it is the reason a whole pipeline stage had never
    run without anything noticing:

        the vault watchdog                       owed  0
        reel_retention (this check's old right)  owed  0        -> AGREE ✅ for months
        _vault_lane_owes(), asked per reel       owed 43        -> the truth

    BOTH OLD SIDES READ plan()'s TAGS, and plan() checks its rules IN ORDER with first-match-wins.
    `vault-owes` is 8th of 10; his 44 reels all match an earlier rule (test-fixture 15,
    zero-pages 24, recent 5), so `vault-owes` fires ZERO times. Two derivations of one broken
    source agreeing with each other is not corroboration — it is one number wearing two names.

    ⚠ AND THE OLD `prove` LINE NAMED THE FIX AS THE SABOTAGE: "make _vault_owed_reels ask its own
    question instead of retention's, and this parts". The author knew. It was written down as the
    way to BREAK the invariant rather than as the way to build it.

    WHAT IT COST: no vault sweep -> no seal -> 72.5% of his 6,380 frames held as "not sealed" ->
    0 frames prunable -> 7.4 GB of reels -> 7 GB free against an 8 GB floor -> CAPTURE BLOCKED.
    Every stage individually correct. [[feedback-contradiction-is-the-finding]] [[the-unjoined-end]]

    The right side is now an INDEPENDENT question — _vault_lane_owes asked of each reel directory
    on disk — which is what "corroborate" was supposed to mean. It reads no plan and no tag, so it
    cannot inherit the ordering that hid the work.
    """
    import control_app as ca
    import reel_retention as rr
    hist = os.environ.get("TV_HIST") or os.path.join(HERE, "frames", "hist")

    def left():
        got = ca._vault_owed_reels(hist)
        return None if got is None else len(got)

    def right():
        # ⚠⚠ THIS SIDE WAS _vault_lane_owes() AND THAT BECAME SELF-CORROBORATION THE MOMENT THE
        # JOINT WAS FIXED. v2391 made _vault_owed_reels ask _vault_lane_owes directly — correct,
        # and it meant BOTH sides of this invariant now ran the same predicate. The independence
        # audit added in v2390 caught it on the next self-test run, on the person who had just
        # written the audit. That is the machine working.
        #
        # So the right side is now a plain directory count: independent by construction, and
        # honest about being the WEAK half. It catches gross over-reach — a worklist larger than
        # the disk it was built from — and nothing subtler.
        #
        # THE STRONG HALF IS A SEPARATE CHECK. `vault-lane-has-worked` is what actually catches
        # the failure that hid here for months (a lane that never swept while work waited); this
        # `<=` cannot, because 0 <= anything holds. Two failures, two checks, neither pretending
        # to be the other. [[unknown-stays-unknown]]
        try:
            return len([d for d in os.listdir(hist) if d.startswith("reel_")])
        except OSError:
            return None

    return ("vault-worklist",
            "the vault watchdog never queues more reels than exist on disk",
            "have the worklist invent or duplicate a path and it exceeds the directory count",
            "the vault watchdog", left, "reel directories on disk", right, "<=")


def _inv_a_lane_that_is_ON_has_either_worked_or_says_why_not():
    """★ THE SHAPE THAT HID A WHOLE PIPELINE STAGE, AND THE ONE `<=` CANNOT CATCH.

    Konyo: "how do we find these before i tell you about them?" — after the vault lane was found
    to have run every 45 seconds since it was built without ever sweeping anything.

    The vault-worklist invariant caught it ONCE, at `==` (0 vs 43). It is now `<=`, because after
    the fix the worklist legitimately narrows (owed AND unsealed = 35 of 43 owed) — and `0 <= 43`
    HOLDS. The relation that catches over-reach cannot catch emptiness. They are two failures and
    they need two checks.

    THE GENERAL RULE, worth more than this one lane: A LANE THAT IS ON AND HAS NEVER COMPLETED A
    SINGLE UNIT OF WORK IS EITHER UNNECESSARY OR BROKEN, AND IT MUST SAY WHICH. Reporting
    {on: True, reads: 0, lastTs: None, owed: 0} forever is not a status — it is the absence of
    one, and it reads identically to a lane with nothing to do.
    [[unknown-stays-unknown]] [[the-unjoined-end]]

    Left is what the lane has DONE; right is whether there is anything to do. A lane that has done
    nothing is fine only while the worklist is empty too.
    """
    import control_app as ca

    def left():
        # 1 if the lane has ever completed a read, else 0.
        # ⚠⚠ v2901 — THIS COMMENT USED TO SAY "lastTs is the durable tell — `reads` is a
        # process-local counter and resets on every restart". BOTH were process-local: measured
        # 2026-09-10, `_VAULT_AUTOREAD` had 14 write sites and ZERO persistence sites, so there
        # was no durable tell at all. The false distinction is why this invariant fired on a
        # RESTART and read as "this lane has never swept" — a very different accusation from
        # "this process is new". `lastTs` IS durable now (control_app persists it); the comment
        # is true as of #60 and was a lie before it. [[label-outlived-referent]]
        try:
            st = ca._vault_autoread_state() or {}
        except Exception:
            return None                       # could not ask -> UNKNOWN, never "it has worked"
        if not st:
            return None
        return 1 if (st.get("lastTs") or (st.get("reads") or 0) > 0) else 0

    def right():
        # 1 if there is work waiting, else 0. UNKNOWN stays UNKNOWN.
        w = ca._vault_owed_reels()
        if w is None:
            return None
        return 1 if len(w) > 0 else 0

    return ("vault-lane-has-worked",
            "a vault lane that has never swept anything is only acceptable while nothing is owed",
            "empty the worklist while the lane still reports work and this parts 0 vs 1",
            "the lane has ever swept", left, "there is work owed", right, ">=")


def _inv_shadow_names_fit_the_universe():
    """1263 distinct names in a 403-name game is not a large sample, it is a broken counter."""
    import shadow_ledger as sl

    def left():
        st = sl.state()
        return int(st.get("names") or 0) if st.get("ok") else None

    def right():
        p = os.path.join(os.path.dirname(HERE), "bible.html")
        try:
            # ⚠ READ THE WHOLE FILE. The first cut capped at 4MB and the assignment lives at 5.1MB
            # in a 5.8MB file, so this reported UNKNOWN — honestly, but for a reason that was my
            # cap rather than his data. A guard that cannot reach the thing it measures fails on
            # its own REACH first. [[source-reading-guard]]
            s = io.open(p, encoding="utf-8", errors="replace").read()
        except Exception:
            return None
        import re
        # the ASSIGNMENT, not the prose. "chronTotal 403 is the game's own" appears in comments
        # 2MB earlier and must never be what this reads.
        m = re.search(r"chronTotal\s*[:=]\s*(\d+)", s)
        if not m:
            return None
        # uniques + sets + runewords is the widest the shadow lane could ever legitimately score
        return int(m.group(1)) * 2

    return ("shadow-sample-fits",
            "the shadow lane has not scored more distinct names than the game contains",
            "sum per-sweep scorings into `names` again and this crosses the ceiling within hours",
            "shadow_ledger.names", left, "the item universe", right, "<=")


def _inv_a_tombstone_is_never_ahead_of_extraction():
    """v3011 (#80) — HIS RULE ON THE OUTLET, AS AN INVARIANT TWO ENGINES MUST AGREE ON.

    "most important is the reels coming in the data and information being extracted on the way..
    make sure that stamps/verification is happening obviously before they go to tombstone and then
    deleted." The route lane already CHECKS this before acting — but a check inside the actor is
    the actor grading itself. This pair re-derives the answer from the reels' OWN evidence, so a
    tombstone ahead of extraction goes red INDEPENDENTLY of whichever lane did it.

    left  = closed-out reels (actor rows, reel_router._routed_by_a_lane) that were MEASURED
            WORTH READING and are MEASURED-unsealed — worth extracting, never sealed, routed
            anyway. right = 0.

    ⚠⚠ WHAT THIS PAIR CANNOT SEE, SAID OUT LOUD. It grades only routed reels whose extract
    evidence is still on disk. The deleter removes that evidence, so a reel tombstoned ahead of
    extraction stops being gradable at the moment the violation finishes — this pair can catch the
    act in flight and never after the fact. Measured 2026-09-12: 20 routed, 4 gradable. It is a
    real check with a real blind spot, and the blind spot is now in the label rather than hidden
    behind a confident 0.

    ⚠⚠ THE FIRST PREDICATE WAS WRONG AND WENT RED ON HIS LIVE DATA WITHIN A MINUTE. `sealed is
    False` alone read 4 violations — and all four were `worthReading=False, surveyed=True,
    names=0`: reels the template station surveyed and judged EMPTY OF VALUE, where nothing was
    ever sealed because there was nothing to seal, and routing them is exactly right. A reel with
    nothing to extract satisfies the extraction contract vacuously. The violation is the
    CONJUNCTION: worth reading AND unsealed AND routed. sealed=None or worthReading=None is an
    unmeasured half and counts NEITHER way — the `what` says so out loud.
    [[unknown-stays-unknown]] [[sabotage-is-usually-the-wrong-one]]
    """
    def left():
        import reel_router as rr
        routed, _why = rr._routed_by_a_lane()
        if routed is None:
            return None                      # the stamp store could not be read — unmeasured
        ev, _ewhy = rr._evidence()
        if not isinstance(ev, dict):
            return None                      # no evidence walk — unmeasured, never zero
        # ⚠⚠ v3015 — THE ZERO HAD NO DENOMINATOR, AND THE COMMENT BELOW WAS THE TELL.
        # "absent by design, not silent" described the INTENT and then did the silent thing: the
        # absent reels were dropped and the survivors' count was published as if it spoke for all
        # of them. MEASURED on his live tree: 20 routed reels, 16 absent from the evidence walk,
        # so FOUR were graded and the row said "0 — agree". 20% coverage wearing a 100% verdict.
        #
        # Worse, the absence is not random. Evidence disappears when the deleter runs, so a reel
        # that WAS tombstoned ahead of extraction becomes ungradable at exactly the moment the
        # violation completes. The pair stayed green through the terminal state of the pipeline it
        # guards. [[zero-needs-a-denominator]] [[label-outlived-referent]]
        #
        # Two fixes, and neither invents coverage that does not exist:
        #   · graded == 0 returns None — UNMEASURED, never a clean zero. `_reading` turns that
        #     into an honest "cannot be corroborated" instead of an agreement nobody earned.
        #   · the LEFT LABEL below now names the population it actually counts, so the number is
        #     read against the right denominator even when most reels are gone.
        graded, bad = 0, 0
        for reel in routed:
            e = ev.get(str(reel))
            if e is None:
                continue                     # deleted after routing — ungradable, not innocent
            graded += 1
            if e.get("sealed") is False and e.get("worthReading") is True:
                bad += 1
        if graded == 0:
            return None                      # nothing survived to grade; 0 here would be a lie
        return bad

    def right():
        return 0

    return ("route-not-ahead-of-extract",
            "no reel that was MEASURED worth reading is closed out unsealed — his rule, "
            "re-derived from the reels' own evidence rather than trusted from the acting lane; "
            "an unmeasured seal or worth counts neither way, and a judged-empty reel routes "
            "freely because its contract is vacuously satisfied",
            "route one worth-reading reel whose extract read sealed:false and this goes red "
            "without asking the lane that did it",
            "worth-reading reels closed out unsealed, among those whose extract evidence "
            "still exists", left, "0 allowed", right, "<=")


def _inv_swept_memory_matches_the_disk():
    """36 vs 30: true, unlabelled, and it nearly got six read-records deleted."""
    import control_app as ca

    def left():
        sp = ca._chron_swept_split()
        if sp.get("onDisk") is None:
            return None
        return int(sp["onDisk"]) + int(sp["retained"] or 0)

    def right():
        import chronicle_retro as cr
        hist = os.environ.get("TV_HIST") or os.path.join(HERE, "frames", "hist")
        mem = ca._chron_swept_mem()
        return len(mem) if isinstance(mem, dict) else None

    return ("swept-split-adds-up",
            "every sweep-memory entry is accounted for as either on-disk or retained-for-pruned",
            "drop the retained bucket and the split stops summing to the file",
            "onDisk + retained", left, "sweep memory entries", right, "==")


def _inv_a_stored_reach_still_matches_git():
    """v3354 (#106) — THE LEDGER'S OWN CLASSIFICATION, AGAINST GIT, ON THE SAME ROWS.

    `absentKind` decides whether a look that missed a file gets WARNED ABOUT or waved through, so a
    wrong value there is silent in the dangerous direction: "stamp" SILENCES the warning. It is
    written once, at record time, and then trusted forever — which is exactly the shape
    [[stale-reading]] §4 names, a verdict with no expiry.

    TWO GENUINELY DIFFERENT ENGINES, and the left one deliberately does NOT call `blind_to`:
        left   the STORED dict on each row, read as a dict and nothing else
        right  the same files re-derived from the COMMIT, by git, ignoring the store

    A disagreement means the persisted classification no longer describes the commit it names —
    a rebase, an amended history, or a writer that stored the wrong thing. Equality is the whole
    claim, so the relation is "==" and not a bound.

    ⚠ IT COUNTS BLIND FILES, NOT ROWS. Rows are few; files are the thing being classified, and a
    per-row count would hide one file flipping inside a row that stays blind either way.

    ⚠ UNKNOWN ON EITHER SIDE MAKES THE WHOLE READING UNKNOWN. A sha this clone cannot resolve —
    a shallow checkout, a CI runner — must not read as "0 blind files, all agree". That is the
    confident zero [[unknown-stays-unknown]] exists to refuse, and here it would report perfect
    agreement precisely when nothing could be compared.
    """
    import second_eye_ledger as _sel

    def _rows_with_reach():
        try:
            rows = _sel._rows()
        except Exception:
            return None
        if not rows:
            return None
        mine = [r for r in rows
                if r.get("absent") and isinstance(r.get("absentKind"), dict) and r.get("sha")]
        # ⚠⚠ AN EMPTY POPULATION IS UNKNOWN, NOT AGREEMENT — and this invariant shipped GREEN at
        # `0 == 0` on its first run for exactly that reason: no row carried `absentKind` yet, so
        # both sides summed over nothing and the pair reported perfect agreement about a
        # comparison that never happened. That is the confident zero this repo keeps re-learning
        # to distrust, committed inside the corroborator built to catch it.
        # [[zero-needs-a-denominator]] [[unknown-stays-unknown]]
        return mine or None

    # ⚠⚠ ONE SNAPSHOT, READ ONCE, SHARED BY BOTH SIDES — and the cross-family eye found this on
    # the day v3354 shipped. Each side used to call `_rows_with_reach()` for itself, and the
    # ledger is an APPEND-ONLY file that `second_eye_run --answer-in` writes: a single row landing
    # between the two calls makes a perfectly healthy store report DISAGREE. REPRODUCED by handing
    # the sides populations of 1 and 2 rows: left 0, right 1, relation "==" false, no defect
    # present. The asymmetric case is worse still — one side None and the other a number reads as
    # UNKNOWN, which is the "agreement about nothing" this invariant was written to refuse.
    #
    # ⚠ SHARING THE SUBJECT IS NOT SELF-CORROBORATION. What must be independent is the METHOD —
    # the stored dict on one side, git on the other — never the rows being judged. Two sides
    # looking at different subjects are not corroborating anything.
    _snapshot = _rows_with_reach()

    def left():
        rows = _snapshot
        if rows is None:
            return None
        n = 0
        for r in rows:
            kinds = r.get("absentKind") or {}
            for f in r["absent"]:
                k = kinds.get(f)
                if k is None:
                    return None          # the store cannot answer: UNKNOWN, never a zero
                if k != "stamp":
                    n += 1
        return n

    def right():
        rows = _snapshot
        if rows is None:
            return None
        n = 0
        for r in rows:
            for f in r["absent"]:
                k = _sel.absent_kind(r.get("sha"), f)
                if k == "unknown":
                    return None          # git cannot answer here: UNKNOWN, never a zero
                if k != "stamp":
                    n += 1
        return n

    return ("second-eye-reach",
            "the stored absentKind still says what git says about the same commit",
            "store 'stamp' for a file whose commit diff is 37 lines and these part by one",
            "absentKind as persisted on the row", left,
            "the same files re-derived from the commit by git", right, "==")


def _inv_chronicle_owed_agrees():
    """The #167 stall class: the reader's own count against retention's view of it."""
    import control_app as ca
    import reel_retention as rr
    hist = os.environ.get("TV_HIST") or os.path.join(HERE, "frames", "hist")

    def left():
        n = ca._chron_owed_count()
        return n if isinstance(n, int) else None

    def right():
        p = rr.plan(hist)
        if not p.get("ok"):
            return None
        # ⚠ v2393 — THE THIRD SITE OF THE SAME PROSE MATCH, AND IT WAS IN THE CORROBORATOR.
        # v2392 fixed one, a cross-family review found the second, and sweeping the class for the
        # second found this one — inside the module whose entire job is catching this. An
        # instrument built out of the defect it grades is the sharpest version of
        # [[feedback-suspect-the-instrument]]. Match the tag reel_retention._rule() writes.
        return len([k for k in (p.get("kept") or [])
                    if k.get("tag") == "never-chronicle-swept"])

    return ("chronicle-owed",
            "the chronicle reader and retention agree on how many reels owe a read",
            "let the private seen-set gate the loop again and these part by 27, as they did",
            "_chron_owed_count", left, "reel_retention", right, ">=")




def _inv_shadow_switch_matches_the_watcher():
    """★ THE EVENING THAT WAS LOST. He played with the shadow switch ON and got ZERO reels — 28 on
    disk, the newest 154 hours old. The switch said "armed"; nothing was watching for the game,
    because shadow only READ frames another mode had already rolled.

    So: if the switch is ON, the watcher must have looked RECENTLY. Two independent readings of the
    same claim — his choice, and the watcher's own durable record — and the whole defect was that
    only the first one existed. A switch that reports its own position and nothing about whether
    the thing it switches is running is the lie this file exists to catch.
    [[the-unjoined-end]] [[label-outlived-referent]]
    """
    import control_app as ca

    def left():
        try:
            return 1 if ca._shadow_state().get("on") else 0
        except Exception:
            return None

    def right():
        """1 when the watcher has looked inside the last 5 minutes. None when it cannot be told —
        never 0, because "no record" and "looked and found nothing" are different facts."""
        try:
            w = ca.shadow_watch_state()
            if not isinstance(w, dict) or w.get("ok") is False:
                return None
            at = w.get("lookedAt")
            if at is None:
                return 0
            return 1 if (time.time() * 1000.0 - float(at)) < 300000.0 else 0
        except Exception:
            return None

    return ("shadow-armed-is-watching",
            "the shadow switch being ON means something is actually looking for the game",
            "an evening of play produced no reels while the panel read 'armed'",
            "_shadow_state().on", left, "shadow_watch.lookedAt<5m", right, "<=")



def _inv_the_deleter_is_never_looser_than_the_planner():
    """★ TWO AUTHORITIES ON "MAY THIS BE DELETED", AND ONLY ONE OF THEM CAN ACT.

    reel_retention PLANS ("1 reel may go, freeing 389 MB — it has given up its information") and
    frame_authority DECIDES ("0 of 6719 could be freed — sealed, but the sweep never extracted
    name, location..."). They disagreed the moment the vault seal landed on 2026-08-30, and the
    strict one held — correctly, because the seal honestly recorded that nothing was extracted.

    That disagreement is HEALTHY and is not what this watches. What must never happen is the
    reverse: the deleter freeing MORE than the planner ever offered. That would mean the thing that
    can destroy his footage is running on a wider rule than the thing that merely suggests, and it
    is the direction with no undo. [[feedback-contradiction-is-the-finding]]
    """
    import frame_authority as fa
    import reel_retention as rr
    hist = os.environ.get("TV_HIST") or os.path.join(HERE, "frames", "hist")

    def left():
        """Reels the FRAME deleter would free at least one frame from, that the REEL planner does
        NOT offer. Both sides are REEL NAMES — the only comparable form of this file's own law.

        ⚠⚠ v2905 — THIS WAS A UNITS ERROR AND IT COULD NOT HOLD IN ANY WORLD. Until now the left
        side was len(plan["prunable"]) — FRAME FILES — and the right was sum(candidate["pages"]) —
        CHRONICLE PAGES, the reader's OUTPUT, a quantity the frame deleter never produces.
        MEASURED on his tree 2026-09-10: frames exceed pages on 24 of 24 reels (3,151 vs 676), so
        the right side's CEILING — the planner offering every reel it keeps — sits BELOW the left
        side's present value of 798. The relation was structurally biased to fire the moment
        anything at all was prunable. [[label-outlived-referent]]

        ⚠ IT STAYS RED, AND THAT IS THE POINT. On his tree this reads 3 — three reels the frame
        deleter would free from that the planner is still holding. The arithmetic is corrected; the
        finding underneath is NOT swept up with it.
        """
        try:
            plan = fa.plan_frames(hist)
        except Exception:
            return None
        if not isinstance(plan, dict) or "prunable" not in plan:
            return None
        try:
            p = rr.plan(hist)
        except Exception:
            return None
        # ⚠ AN UNREADABLE OFFER IS UNKNOWN, NEVER AN EMPTY ONE. Subtracting a set nobody could read
        # would answer "nothing is outside the offer" — a confident zero from an unanswered
        # question, which is the exact defect this file exists to refuse. [[unknown-stays-unknown]]
        if not p.get("ok") or p.get("candidates") is None:
            return None
        offered = {c.get("reel") for c in (p.get("candidates") or [])}
        freeing = {os.path.basename(os.path.dirname(f)) for f in (plan.get("prunable") or [])}
        return len(freeing - offered)

    def right():
        # ⚠ CONSTANT BY CONSTRUCTION, NOT BY ACCIDENT — and unlike the v2393 defect this file
        # carries a scar for, the constant is on the side that is NOT the measurement. The question
        # is CONTAINMENT, so the only passing answer is "no reel freed outside the offer".
        # `left()` varies with BOTH engines and can invert.
        return 0
    return ("deleter-not-looser",
            "the one thing that can delete never frees a frame from a reel the planner holds",
            "let frame_authority clear a reel retention still holds and this inverts",
            "reels freed outside the offer", left, "reels allowed outside the offer", right, "<=")



def _inv_the_two_deleters_stay_at_their_own_granularity():
    """★ TWO DELETERS, TWO QUESTIONS, AND CONFLATING THEM WAS MY ERROR — TWICE IN ONE DAY.

    reel_retention answers "may this REEL go" — both lanes finished with it.
    frame_authority answers "may this FRAME go" — stricter, because it protects the witness frames
    standing behind his vault rows, and a frame is the last copy of a name.

    They disagree by DESIGN and both are right. On 2026-08-30 I read that disagreement as a defect,
    made retention ask frame_authority's contract, and broke three deliberate cases — a change that
    would have stopped the prune firing on every existing reel, since all his seals predate that
    contract. Withdrawn.

    What must stay true is the ordering: the FRAME deleter, being the stricter one, must never free
    more than the reel planner is willing to let go. If that inverts, the thing protecting his
    witness frames has become the looser of the two. [[feedback-contradiction-is-the-finding]]

    ⚠⚠ v3304 (#61) — THE LABELS SAY "WOULD FREE", NOT "FREED", AND THAT IS NOT PEDANTRY.
    `frame_authority.plan_frames()` REPORTS; control_app.py:17935 says it outright — "Deletes
    nothing, ever." Nothing has been freed from any reel. But the row rendered "reels freed
    outside the offer says 4" on his console, which reads as four reels having LOST footage, and
    I read it that way myself before measuring. A standing design warning was wearing the clothes
    of an incident. The relation is UNCHANGED and must stay red: if the frame deleter were ever
    ARMED while the planner holds everything, it would take 1,904 frames from 4 reels held on
    purpose — three of them held BECAUSE a full survey found panel frames there, which are the
    witness standing behind his vault rows. [[unknown-stays-unknown]]

    ⚠ AND THIS NOTE LIVES HERE, NOT BESIDE THE RETURN, FOR A MEASURED REASON. Written between
    `right()` and the return it turned the corroborator's OWN self-audit red: that audit resolves
    each side's callees FROM SOURCE, `right()` is a literal `return 0`, and a comment of mine
    naming `frame_authority.plan_frames` inside its window made both sides look like one engine —
    "no invariant corroborates a thing against ITSELF". My prose, someone else's guard, and the
    guard was right. [[source-reading-guard]]
    """
    import frame_authority as fa
    import reel_retention as rr
    hist = os.environ.get("TV_HIST") or os.path.join(HERE, "frames", "hist")

    def left():
        """Reels the FRAME deleter would free at least one frame from, that the REEL planner does
        NOT offer. Both sides are REEL NAMES — the only comparable form of this file's own law.

        ⚠⚠ v2905 — THIS WAS A UNITS ERROR AND IT COULD NOT HOLD IN ANY WORLD. Until now the left
        side was len(plan["prunable"]) — FRAME FILES — and the right was sum(candidate["pages"]) —
        CHRONICLE PAGES, the reader's OUTPUT, a quantity the frame deleter never produces.
        MEASURED on his tree 2026-09-10: frames exceed pages on 24 of 24 reels (3,151 vs 676), so
        the right side's CEILING — the planner offering every reel it keeps — sits BELOW the left
        side's present value of 798. The relation was structurally biased to fire the moment
        anything at all was prunable. [[label-outlived-referent]]

        ⚠ IT STAYS RED, AND THAT IS THE POINT — the arithmetic was corrected and the finding
        underneath was NOT swept up with it. What it means: these are reels the frame deleter
        WOULD free from while the planner is still holding them. Nothing has been freed;
        plan_frames only ever reports.

        ⚠ AND THE COUNT IS NOT QUOTED HERE ANY MORE. This said "reads 3"; re-measured 2026-09-18
        it reads 4 (1,904 frames). A number written into prose goes stale the day the tree moves
        and then contradicts the row it describes — pin the LAW, never the number.
        [[regression-guard]] [[stale-reading]]

        ⚠ WHY IT IS RED RIGHT NOW, which the row cannot say for itself: the planner offers ZERO
        candidates, and that is a MEASURED zero with its own sentence — "NOTHING is safe to delete
        yet ... every reel is recent, unread, or still owed to a lane." So everything the frame
        deleter would touch is outside the offer by construction. That does not make the relation
        wrong; it makes the warning precise.
        """
        try:
            plan = fa.plan_frames(hist)
        except Exception:
            return None
        if not isinstance(plan, dict) or "prunable" not in plan:
            return None
        try:
            p = rr.plan(hist)
        except Exception:
            return None
        # ⚠ AN UNREADABLE OFFER IS UNKNOWN, NEVER AN EMPTY ONE. Subtracting a set nobody could read
        # would answer "nothing is outside the offer" — a confident zero from an unanswered
        # question, which is the exact defect this file exists to refuse. [[unknown-stays-unknown]]
        if not p.get("ok") or p.get("candidates") is None:
            return None
        offered = {c.get("reel") for c in (p.get("candidates") or [])}
        freeing = {os.path.basename(os.path.dirname(f)) for f in (plan.get("prunable") or [])}
        return len(freeing - offered)

    def right():
        # ⚠ CONSTANT BY CONSTRUCTION, NOT BY ACCIDENT — and unlike the v2393 defect this file
        # carries a scar for, the constant is on the side that is NOT the measurement. The question
        # is CONTAINMENT, so the only passing answer is "no reel freed outside the offer".
        # `left()` varies with BOTH engines and can invert.
        return 0
    return ("frame-deleter-not-looser",
            "the frame deleter never frees a frame from a reel the planner is still holding",
            "let frame_authority clear frames inside a reel retention is holding and this inverts",
            "reels the frame deleter WOULD free, outside the offer", left,
            "reels it is allowed to free outside the offer", right, "<=")

def _inv_the_two_readers_measure_the_same_screen():
    """★ TWO READERS, TWO COPIES OF ONE MEASUREMENT OF HIS MONITOR.

    stash_eye reads the LEFT-ANCHORED stash/inventory panel; chronicle_template reads the CENTERED
    Chronicle modal. Their geometry genuinely differs — chronicle_template's own header explains it
    cannot copy "stash_eye's left-anchor math" and uses a CENTER-PRESERVING derivation instead.
    That part is a real reason, not drift.

    What IS drift: each carries its own calibration film of the SAME physical screen —
    stash_eye._CROP_CAL_FILM and chronicle_template._CAL_FILM, both (2940, 1912) today. One
    recalibration (new monitor, new resolution, a re-measure of one panel) updates one and leaves
    the other silently reading his screen as a shape it no longer is. Nothing would say so; the
    reader would simply start missing panels.

    Konyo: "the readers and ai analyzers all need the same upgraded logic and tools ... should be a
    synced and unified logic". This is that sync, expressed as an invariant instead of a refactor.
    [[copy-drift]]
    """
    def left():
        try:
            import stash_eye as _se
            f = getattr(_se, "_CROP_CAL_FILM", None)
            return int(f[0] * 100000 / float(f[1])) if f else None
        except Exception:
            return None

    def right():
        try:
            import chronicle_template as _ct
            f = getattr(_ct, "_CAL_FILM", None)
            return int(f[0] * 100000 / float(f[1])) if f else None
        except Exception:
            return None

    return ("readers-same-screen",
            "both readers are calibrated to the same physical screen",
            "recalibrate one reader's film and leave the other, and this parts",
            "stash_eye._CROP_CAL_FILM", left, "chronicle_template._CAL_FILM", right, "==")


def _inv_the_fleet_divides_by_the_same_number_the_board_does():
    """v2717 — THE FLEET AND THE BOARD'S OWN TABS PUBLISHED DIFFERENT UNIQUES, AND HE SAW IT.

    Konyo, 2026-09-06: *"no reason for it to render something in the roster or fleet different from
    the consoles main tabs Uniques/Sets/runewords"*. Measured on his live console, GET /api/fleet,
    twice six minutes apart on the SAME machine:

        10:33:26   uniques {have: 169, total: 398}
        10:39:39   uniques {have: 292, total: 403}
        the board's own Chronicle meter:  258 / 403

    ⚠ NEITHER SIDE WAS BROKEN. They were two coherent measures wearing one label: the fleet
    published `d2r_owned.length / _gUniqueRoster().length` (vault over vault roster, 398 — which
    keeps both spellings of all six sunders on purpose since v2685), while the tabs showed
    `funiScan().found / chronTotal` (chronicle over the pinned game count, 403). Two questions, one
    word. [[label-outlived-referent]] [[zero-needs-a-denominator]]

    ⚠⚠ AND v2714 DID NOT FIX IT. That ship unified NINE call sites inside bible.html and shipped
    believing the job done; the fleet's number is built in control_app.py, which it never touched.
    A read-only agent traced it afterwards. THIS invariant is the thing that would have said so —
    the reason it exists is that a fix was believed rather than corroborated.

    INDEPENDENCE, which is the whole point of living here: the left side is the BANKED denominator
    the beacon published; the right side is the chronicle number route_totals reads out of
    bible.html. The pin and that number are the same. Neither side can inherit the other's answer.
    That distinction is what [[feedback-verify-not-proxy]] means, and the audit added in v2390
    exists because a previous invariant quietly lost it.

    HONEST-ABSENT: a console that cannot be asked, or a board that cannot say, returns None on the
    left and the invariant reports UNMEASURED rather than a pass. A guest world, an unclaimed
    board, a console that is down — none of those are evidence of agreement.
    """
    def left():
        """The denominator in the BANKED tally on disk — the row the beacon actually publishes.

        ⚠⚠ THIS WAS `ca.grail_tally()` AND IT WAS VACUOUS. Out of process there is no board window,
        so `board_ownership()` fails and grail_tally falls straight through to the disk bank — the
        very file the right side would then be compared against. MEASURED: sabotaging the live
        eval path (putting the fleet back on the vault roster) left this invariant GREEN, because
        `left()` never reached that code at all. The sabotage pass caught it, on the person who had
        just written it, which is the second time this file has caught its own author.
        [[feedback-suspect-the-instrument]]

        So it reads the BANK, which is a real artifact with a real denominator, and the sabotage
        below can move it. The live-eval path is a CODE law and lives in a unit test where it can
        actually be graded, not here where the process cannot reach it.
        """
        try:
            p = os.path.join(HERE, "board_tally.json")
            d = json.load(io.open(p, encoding="utf-8"))
            # ⚠ AND THE SHAPE WAS NOT WHAT I ASSUMED EITHER. board_tally.json is not a map of
            # routes — it carries `uniques`/`sets`/`runewords` at the TOP level (the headline the
            # beacon publishes) plus `byRoute` and `high` maps beneath. My first cut walked
            # d.values() expecting per-route dicts, hit an int, and returned UNKNOWN on a perfectly
            # readable file. Measured before fixing: top-level uniques = {"have":292,"total":403}.
            u = d.get("uniques") if isinstance(d, dict) else None
            n = (u or {}).get("total") if isinstance(u, dict) else None
            return int(n) if isinstance(n, int) and n > 0 else None
        except Exception:
            return None

    def right():
        """The tally the tabs divide by, read from bible.html. Never from the console.

        The pin and the tally are the chronicle number. A fleet that posts the file-row
        count, or the vault roster, while the tabs use the pin, parts here.
        """
        try:
            import route_totals as _rt
            n = _rt.total("unique")
            return int(n) if isinstance(n, int) and n > 0 else None
        except Exception:
            return None

    return ("fleet-divides-by-the-board's-number",
            "the fleet's uniques denominator is the tally the board's own tabs divide by",
            "let the fleet publish the file-row count, or the vault roster, while the tabs "
            "use the chronicle pin and this parts",
            "the banked board_tally denominator (disk)", left,
            "the unique tally in bible.html (source)", right, "==")


def _inv_the_deleter_releases_only_what_the_store_declares():
    """v2720 — THE DECIDER MUST NEVER RELEASE MORE SEALS THAN THE STORE ACTUALLY DECLARES.

    His ruling, 2026-09-06: an examined-empty reel *"can continue down the river to tombstone...
    and delete"* — **"as long as its ledgered and extracted properly and tallied where needed"**.
    A conditional yes. This is the invariant that keeps the condition attached to it.

    ⚠⚠ WHY IT EXISTS AT ALL, MEASURED. `seal_verdict` scores a seal EMPTY when `examinedEmpty` is
    set OR when `extractedWhy` merely contains the word "nothing". Across his 31 real seals that is
    23 EMPTY — but only 17 declared `examinedEmpty`; the other 6 qualify on the string alone, and
    their why is literally "nothing was taken", which is the DEFAULT branch of `_seal_extracted`
    for any sweep that grounded no rows. Wiring `!= UNEVIDENCED` into the deleter would have
    released six reels on a substring. The looser read is CORRECT for a report and WRONG for a
    deletion, and nothing but this invariant keeps the two apart over time.

    INDEPENDENCE, which is the whole point of living here: the LEFT side runs the predicate the
    deleter actually calls; the RIGHT side counts declarations straight out of the seal JSON,
    touching no frame_authority logic at all. A drift in the predicate cannot move the right side,
    which is exactly the property the v2390 audit exists to protect.

    RELATION IS `<=`, NOT `==`, AND THAT IS DELIBERATE. The deleter may be STRICTER than the store
    (it also demands a readable seal, and `rows == 0` before it will call a thing empty). It may
    never be LOOSER. An equality here would go red for a safe reason and teach us to ignore it.
    [[unknown-stays-unknown]] [[join-gate-heart]]
    """
    def left():
        """How many seals the DELETION-side predicate would release."""
        try:
            import frame_authority as FA
            sealed, ok = FA.sealed_sessions()
            if not ok or not isinstance(sealed, dict) or not sealed:
                return None            # nothing examined names nothing
            return sum(1 for r in sealed.values() if FA.seal_releases_frames(r)[0])
        except Exception:
            return None

    def right():
        """How many seals DECLARE a releasable state, read straight from the store."""
        try:
            import frame_authority as FA
            contract = set(FA.EXTRACTION_CONTRACT)
            sealed, ok = FA.sealed_sessions()
            if not ok or not isinstance(sealed, dict) or not sealed:
                return None
            n = 0
            for r in sealed.values():
                if not isinstance(r, dict):
                    continue
                got = r.get("extracted")
                covered = isinstance(got, (list, tuple, set)) and contract <= {str(x) for x in got}
                if covered or r.get("examinedEmpty") is True:
                    n += 1
            return n
        except Exception:
            return None

    return ("deleter-releases-only-what-is-declared",
            "the deleter releases no more seals than the store actually declares releasable",
            "let EMPTY-by-substring reach the deleter and this parts — 23 released against 17 "
            "declared, six of them on the words 'nothing was taken'",
            "seal_releases_frames over his seals", left,
            "seals declaring the contract or examinedEmpty (raw JSON)", right, "<=")


def _inv_the_two_owned_fields():
    """157 vs 7 — TWO PAYLOAD FIELDS BOTH CALLED `owned`, and I found this by hand and did not
    encode it. That omission is the whole argument for this file existing.

    They are DIFFERENT QUANTITIES: ledgerBackup.counts.owned is the durable backup of the board's
    d2r_owned (what is in his stash); vault_ledger.totals.owned is what the VAULT SWEEP LANE has
    independently established from film. Both true. Nothing said so, and 157 beside 7 reads as data
    loss.

    So the invariant is NOT equality — it is CONTAINMENT: the vault lane can only ever have
    established a subset of what the board holds. If the lane ever claims MORE than the stash, one
    of them is wrong and it is worth his attention.
    """
    import control_app as ca

    def left():
        try:
            v = ca.vault_ledger_view() or {}
            t = v.get("totals") or {}
            n = t.get("owned")
            return int(n) if isinstance(n, int) else None
        except Exception:
            return None

    def right():
        st = ca.ledger_backup_state() or {}
        c = st.get("counts") or {}
        n = c.get("owned")
        return int(n) if isinstance(n, int) else None

    return ("owned-is-contained",
            "the vault lane has never established more owned items than the board holds",
            "swap the two fields, or let the lane count something the stash does not, and this parts",
            "vault_ledger.totals.owned", left, "board d2r_owned (backed up)", right, "<=")


#: v2394 — how old the eagle's durable pass may be and still mean something. The loop runs every
#: few minutes; an hour is generous and still refuses a record from yesterday. [[stale-reading]]
_EAGLE_RECORD_MAX_AGE_MS = 60 * 60 * 1000
#: the canonical console port. ⚠ A SECOND COPY OF A CONSTANT IS A THING THAT CAN DRIFT — the cold
#: review flagged control_app's own `_PRIMARY_CONTROL_PORT = 17772` as already duplicating
#: TV_CONTROL_PORT's fallback. So this reads control_app's value and only falls back to the literal
#: when the module cannot be imported at all (a gate on a machine without it).
try:
    import control_app as _ca_for_port
    _PRIMARY_PORT = int(getattr(_ca_for_port, "_PRIMARY_CONTROL_PORT", 17772))
except Exception:
    _PRIMARY_PORT = 17772

#: The durable pass. A MODULE CONSTANT so a test can point it somewhere harmless.
#: ⚠ THE FIRST CUT HARDCODED THIS PATH AND THE GUARD RACED HIS RUNNING CONSOLE. The live console
#: rewrites this file on every eagle pass; a test that wrote it, asserted, and restored it was
#: fighting a process that writes every few minutes — three of my own guards failed on the push
#: for exactly that. A test must never read or write a file the product is actively writing.
#: [[feedback-fixtures-never-touch-live-data]]
def _eagle_record_path():
    """Where the PRIMARY console's durable pass lives.

    ⚠ ASK THE WRITER RATHER THAN RE-DERIVING, BECAUSE THE TWO DERIVATIONS HAD ALREADY SPLIT. This
    computed `dirname(control_app.__file__)` while v2411 moved the writer onto `_decision_path`,
    whose directory comes from `_chron_swept_path()`. On his machine those resolve to the same
    folder, which is exactly why nothing noticed — but they are two different rules, and under a
    redirected state directory (any test, any packaged run) they genuinely diverge. A cold review
    named it; the join test then reproduced it, writer landing in a temp state dir while the reader
    looked beside the module.

    Two paths computed two ways is [[copy-drift]] with a filename instead of a function. Ask the
    owner. The fallback stays for a process that cannot import control_app at all — a gate on a
    machine without it — where UNKNOWN is the honest answer anyway.

    ⚠ ALWAYS THE PRIMARY'S PATH, never this process's own. A scratch console reading the record
    should read the record the CONSOLE wrote, not its own; asking `_decision_path` from inside a
    scratch would silently retarget the reader to the scratch's file and re-create the very
    self-agreement v2411 removed."""
    # ⚠ THE FALLBACK MUST FIRE ONLY WHEN control_app IS GENUINELY ABSENT. A first cut wrapped the
    # whole thing in `except Exception: pass` and fell through to `dirname(__file__)` — so if
    # `_chron_swept_path()` raised for any reason the reader would SILENTLY REVERT to the old rule
    # while the writer kept using the redirected one, re-creating the split this function exists to
    # close, invisibly. That is the same broad-catch mislabel being removed from the render gate in
    # the same ship. A cold review caught both.
    # ⚠ ImportError, NOT Exception. A cold review: catching Exception here means a BROKEN
    # control_app — a syntax error, a circular import — also falls back to this module's own
    # directory, which in this tree is the same `tv/`. Under a redirected TV_HIST that is the
    # writer/reader split all over again, just narrowed to the case where the import fails.
    try:
        import control_app as _ca
    except ImportError:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), ".eagle_last.json")
    # ⚠ AND A CORRECTION TO MY OWN COMMENT, which said an unguarded raise here "must surface".
    # It does not. The only production caller is _durable_pass, which ends `except Exception:
    # return (None, None)` — so a raise becomes UNKNOWN, silent about its cause. That is still the
    # right OUTCOME (no row count and no wrong file, rather than a confident read of the wrong
    # one), but the comment claimed something the code does not do, which is the defect I spent
    # this evening finding in my own commit messages.
    base = _ca._chron_swept_path()
    return os.path.join(os.path.dirname(os.path.abspath(base)), ".eagle_last.json")


def _durable_pass(max_age_ms=None):
    """The last durable eagle pass as ONE snapshot. -> (rows, slow, periodic), any possibly None.

    ⚠ v2943 — `periodic` joined the tuple rather than getting its own reader, because this file's
    own rule is ONE READ, ONE POLICY: a second reader of the same record under different rules is
    exactly how this broke twice before (see below).

    ⚠ ONE READ, ONE POLICY, BECAUSE TWO READERS OF ONE RECORD IS HOW THIS BROKE TWICE. v2407 had
    `left()` reading rows here under freshness + author rules while a separate `_durable_slow_flag`
    read `slow` from the same file under NO rules — its docstring claimed "same file and freshness
    rules as the row count it accompanies" and it checked neither `ts` nor `port`. Two readers of
    one record with two policies is the same shape as the mixed-source bug it was written to fix,
    one level down; a cold review caught the docstring lying before it cost anything.

    Every refusal below returns (None, None): the pass is UNREADABLE, and reporting a row count
    without knowing which roster it was measured against is worse than reporting nothing.
    """
    try:
        import json as _json, os as _os, time as _time
        _p = _eagle_record_path()
        if not _os.path.isfile(_p):
            return (None, None, None)
        with io.open(_p, encoding="utf-8") as _fh:
            _row = _json.load(_fh)
        _ts = _row.get("ts")
        if not isinstance(_ts, (int, float)):
            return (None, None, None)
        cap = _EAGLE_RECORD_MAX_AGE_MS if max_age_ms is None else max_age_ms
        if (_time.time() * 1000 - float(_ts)) > cap:
            return (None, None, None)            # too old to mean anything
        # ⚠ v2409 — ASK WHETHER IT WAS THE PRIMARY CONSOLE, NOT WHETHER IT HAD A PORT.
        # v2408 refused a record whose port was None, reasoning that a portless process has no
        # window. Grok Bot then named the actual stray: `control_app.py --no-open` on **:17985** —
        # windowless, but serving. It writes port=17985 and would have sailed straight past that
        # check, so the guard was inert on the one case that produced it. A guard that cannot fail
        # on its own motivating example is measuring nothing. [[feedback-blind-fixture-green-gate]]
        #
        # `primary` comes from _is_primary_console(): only the canonical :17772 console is the one
        # anyone is asking about. Port is still recorded, for diagnosis rather than for judgement.
        #
        # ⚠ ABSENT IS NOT False. A pre-v2409 record carries no `primary` key at all and must still
        # be read, or upgrading blinds this on every machine until each rewrites its file.
        if _row.get("primary") is False:
            return (None, None, None)
        # ⚠ THE COMPATIBILITY HOLE THE COLD REVIEW FOUND, AND IT WAS THE ONE CASE THAT MATTERS.
        # A pre-v2409 record carries no `primary` key and is deliberately still read — but the
        # record an OLD SCRATCH actually produces is `{port: 17985}` with no `primary`, which sailed
        # straight through. The suite covered `{port: 17772}` with no primary and `{port: 17985,
        # primary: false}`, and missed exactly the combination a live older scratch writes.
        # `port` was already stamped by the previous writer, so it closes the hole without blinding
        # a genuinely keyless file.
        if _row.get("primary") is None and isinstance(_row.get("port"), int) \
                and _row.get("port") != _PRIMARY_PORT:
            return (None, None, None)
        if "port" in _row and _row.get("port") is None:
            return (None, None, None)
        _r = _row.get("rows")
        _s = _row.get("slow")
        # ⚠ v2943 — same "absent stays absent" rule as `slow`: a record written before the eagle
        # persisted this key answers None, and the caller then says UNKNOWN rather than assuming
        # the pass did or did not include PERIODIC. [[unknown-stays-unknown]]
        _p = _row.get("periodic")
        return (int(_r) if isinstance(_r, int) else None,
                bool(_s) if isinstance(_s, bool) else None,
                bool(_p) if isinstance(_p, bool) else None)
    except Exception:
        return (None, None, None)


def _inv_the_eagle_can_still_look():
    """A watchdog that cannot run is not a passing watchdog. The eagle runs the corroborator; until
    now nothing checked the eagle. UNKNOWN is the honest answer when its own state is unreadable."""
    import control_app as ca

    def left():
        e = dict(getattr(ca, "_EAGLE", {}) or {})
        # ⚠⚠ NEVER-RUN IS NOT ZERO-COVERAGE, AND MY FIRST CUT SAID IT WAS. `_EAGLE` initialises to
        # {"checked": None, "rows": [], "say": "not measured yet"}, so reading len(rows) on a fresh
        # process answered 0 and the invariant reported "the eagle covered 0 of 22 checks" — a
        # confident finding about an eagle that had simply not flown yet. It fired on this machine
        # the first time it was asked.
        #
        # That is the exact law this whole file exists to enforce, broken inside the file: 0 means
        # "we measured, it was zero"; None means "nobody looked". `checked` is the module's own
        # explicit never-run marker — ask it rather than inferring from an empty list.
        # [[unknown-stays-unknown]]
        if e.get("checked") is None:
            # ══ v2394 — READ THE DURABLE PASS, BECAUSE _EAGLE IS A MODULE GLOBAL ═════════════
            # Konyo: "the_eagle_can_still_look = UNKNOWN... no gaps... information is needed
            # obviously, so connect it to the heart of the console too."
            #
            # `_EAGLE` lives in the CONSOLE'S process. Everywhere else — this CLI, a gate, CI —
            # the module is fresh and `checked` is None, so the one invariant that watches the
            # watchdog could only ever be graded inside the thing it grades. v2394 makes
            # _eagle_once persist {checked, rows, ts}; this reads it.
            #
            # ⚠ STALE IS NOT FRESH, AND IT IS NOT A PASS EITHER. A pass from three days ago is
            # not evidence the eagle flew today, so a record older than the bound answers
            # UNKNOWN — the same answer as no record at all, which is the honest one.
            # [[stale-reading]] [[unknown-stays-unknown]]
            # ⚠ ONE READ FOR BOTH SIDES — see _durable_pass. This branch used to inline its own
            # loader while `slow` was read by a second function with different rules.
            return _durable_pass()[0]
        rows = e.get("rows")
        return len(rows) if isinstance(rows, list) else None

    def right():
        """The checks the eagle ACTUALLY RUNS — which is not the whole roster.

        ⚠ THIS RETURNED len(cd.CHECKS) AND THE INVARIANT COULD THEREFORE NEVER BE SATISFIED. The
        eagle calls `run(include_slow=False)` (control_app.py:14601) and `run` skips any name in
        `SLOW`, so it emits len(CHECKS) - len(SLOW) rows by design. Measured on his live console
        2026-09-01: 32 rows against a roster of 34, flagged as an engine pair disagreeing, when
        34 - 2 = 32 is exactly right. The two are `sweep would find` and `the other doctors`.

        He photographed the panel and asked what it meant. A corroborator comparing a filtered
        count against an unfiltered one is not detecting drift, it is reporting its own filter —
        and it had presumably been red since SLOW was introduced. A permanently-red alarm is worse
        than no alarm: it teaches the eye to skip the row, and then the row that MATTERS gets
        skipped with it. [[feedback-suspect-the-instrument]] [[label-outlived-referent]]

        ⚠ DERIVED FROM THE SAME CONSTANTS THE RUNNER USES, never a hardcoded 32. Adding a check
        must move this number automatically; pinning the literal would rot on the next check and
        reintroduce the identical defect one roster entry later. [[regression-guard]]
        """
        import console_doctor as cd
        full = len(cd.CHECKS)
        cheap = len([c for c in cd.CHECKS if c[0] not in cd.SLOW])
        # ⚠ THE EXPECTATION DEPENDS ON WHICH PASS RAN, AND MY FIRST FIX HARDCODED ONE OF THEM.
        # Returning `cheap` unconditionally traded a permanently-red alarm for one that goes red
        # whenever a COMPLETE pass runs — the suite caught it immediately
        # (test_an_eagle_that_flew_EVERY_check_agrees drives 34 rows and expects agreement).
        # v2407 makes the eagle RECORD `slow`, so this asks instead of assuming.
        #
        # ⚠ AND THE DEFAULT WHEN THE FLAG IS ABSENT IS `full`, DELIBERATELY. An old record, or a
        # caller that never set it, must not be silently reinterpreted as a cheap pass — that
        # would make a genuinely incomplete pass of 32 rows read as healthy, which is the exact
        # blindness this invariant exists to prevent. Defaulting to the STRICTER expectation means
        # an unlabelled pass can still be caught skipping checks. [[unknown-stays-unknown]]
        #
        # ⚠⚠ AND THE FLAG MUST COME FROM THE SAME PASS AS THE ROWS. The first cut read the flag
        # from the DURABLE record while left() was counting rows from the IN-MEMORY _EAGLE — so a
        # fixture's 34 rows got graded against his live console's `slow: False`, and the suite
        # failed with `34 != 32` for a reason that had nothing to do with either. Two halves of one
        # comparison sourced from two different passes is not a comparison at all, and it made the
        # test's verdict depend on the machine it ran on. left() decides which record it is reading
        # by asking whether `checked` is set; this mirrors that decision exactly rather than
        # guessing again. [[feedback-fixtures-never-touch-live-data]] [[copy-drift]]
        e = dict(getattr(ca, "_EAGLE", {}) or {})
        # ⚠⚠ v2943 (#63) — AND `periodic`, WHICH THIS EXPECTATION IGNORED. The unattended tick
        # skips PERIODIC on 5 of every 6 passes, so roster-minus-SLOW was 1 too high almost always
        # and this pair read DISAGREE almost always. MEASURED on his tree before the fix: "rows in
        # the last eagle pass says 53 and rows that pass was expected to cover says 54". A pair
        # that is permanently red cannot report a genuinely dropped check — it is the cry-wolf
        # shape, and a finding he learns to skip is worse than no finding at all.
        _dur = _durable_pass()
        slow = e.get("slow") if e.get("checked") is not None else _dur[1]
        periodic = e.get("periodic") if e.get("checked") is not None else _dur[2]
        _base = None
        if slow is False:
            _base = cheap
        if slow is True:
            _base = full
        if _base is not None:
            # ⚠ ABSENT IS UNKNOWN, NOT False — the same rule the block below states for `slow`.
            # A record written before the eagle persisted `periodic` cannot say whether that pass
            # included it, and guessing turns this pair back into an alarm nobody can act on.
            if periodic is None:
                # ⚠⚠ v2944 — BACKWARD COMPATIBILITY OUTRANKS THE NEW RULE, AND THE GATE TAUGHT ME
                # THAT. v2943 returned UNKNOWN here on the "absent is not False" principle, and
                # test_control's TestV2394TheEagleCanBeGradedFromOUTSIDEItsOwnProcess went RED in
                # five places — including `test_a_PRE_v2409_record_with_no_primary_key_is_still_read`,
                # whose own message is "refused for lacking a key it COULD NOT HAVE HAD". That is a
                # deliberate contract: a record written by an older console must still be gradeable.
                # So a record with no `periodic` keeps the PRE-v2943 expectation. The cost is
                # stated rather than hidden: such a record can still read red on a pass that
                # skipped PERIODIC — which is the state it was already in — and it corrects itself
                # the moment the console writes one record carrying the key.
                # [[feedback-blind-fixture-green-gate]] [[copy-drift]]
                return _base
            # ⚠ v3298 — #35: a skipped PERIODIC check now EMITS a not-asked row instead of
            # vanishing, so every labelled pass covers the same population and the subtraction
            # that lived here went with the defect it compensated for. A legacy periodic=False
            # record from a pre-v3298 console can read red until one new record lands — the
            # v2944 precedent, cost stated rather than hidden. [[regression-guard]]
            return _base
        # ⚠⚠ AN UNLABELLED PASS IS UNKNOWN, NOT "ASSUME THE WHOLE ROSTER" — AND MY DEFENCE OF THE
        # STRICT DEFAULT WAS WRONG ON ITS OWN TERMS. I argued that defaulting to `full` keeps a
        # skipped check catchable. It does not: a skip is caught by a LABELLED cheap pass reporting
        # 31 against 32. The default fires only in the UNLABELLED case — where it reports 32
        # against 34, which is precisely the permanently-red row he photographed, back under
        # different arithmetic.
        #
        # A cold cross-family read put it exactly right: "it protects against a store nobody
        # writes, and alarms on the store everybody writes." Confirmed — nothing in production
        # RECORDS a complete pass. control_app.py:23398 runs one for an API response and never
        # touches _EAGLE or the durable file, so `full` was reachable only through this default.
        #
        # The engine already grades a None side as UNKNOWN, symmetrically with left(). Not knowing
        # which roster a pass was measured against is a fact about the record, and reporting a
        # count against a roster nobody chose is an expectation with no author.
        # [[unknown-stays-unknown]] [[label-outlived-referent]]
        return None

    return ("eagle-ran-every-check",
            "the eagle's last pass covered every check it actually runs (the roster minus SLOW)",
            "drop a check from the loop and its row stops appearing while the roster still lists it",
            # ⚠ THE NAME MUST NOT ASSERT A BRANCH IT CANNOT KNOW. It read "checks the eagle runs
            # (roster minus SLOW)" while right() may legitimately return the FULL roster — so a
            # human reading `34` under a label saying "minus SLOW" correctly works out that the
            # instrument is wrong, and no action follows. The tuple is static, so the name must be
            # true in every branch. [[label-outlived-referent]]
            "rows in the last eagle pass", left,
            "rows that pass was expected to cover", right, "==")


def _inv_hunt_memory_is_being_used():
    """The paid-work-with-no-memory scar, as an invariant. His hunt bought 3,434 paid reads for 2
    sightings — 1,717 each — re-buying the same 8 names for eight hours, and it looked exactly like
    healthy activity. The memory exists so it stops re-buying; if the memory is EMPTY while reads
    are being spent, the memory is not reaching the buyer."""
    import os, json, io as _io

    def left():
        p = os.path.join(HERE, "chron_hunt_memory.json")
        if not os.path.exists(p):
            return None
        try:
            d = json.load(_io.open(p, encoding="utf-8"))
        except Exception:
            return None
        return len(d) if hasattr(d, "__len__") else None

    def right():
        return 0                      # any memory at all beats none, once the hunt has spent

    return ("hunt-remembers",
            "the hunt has banked what it already bought, so it cannot re-buy the same names",
            "empty the memory while the hunt keeps spending and this goes to zero",
            "hunt-memory entries", left, "the floor", right, ">=")


def _inv_every_declared_tooltip_surface_is_served():
    """v2316 — the surfaces that say they need hover evidence, against the code that derives it.

    Five surfaces declare tooltip=True; a tooltip rectangle is derived by differencing consecutive
    frames, so it is the reel sweep that must own the step. If no production module imports
    tooltip_crop, those five are asking for something nobody performs — and until v2316 the
    function meant to notice returned the same five names whether or not that was true, so it
    could never have told anyone. [[label-outlived-referent]] [[plumbing-with-no-tap]]
    """
    import surfaces as S

    def left():
        return len(S.tooltip_surfaces())

    def right():
        ok, _why = S.tooltip_wiring()
        return len(S.tooltip_surfaces()) if ok else 0

    return ("tooltip-surfaces-served",
            "every surface that declares it needs hover evidence has a sweep that derives it",
            "delete `import tooltip_crop` from vault_retro and this parts 5 vs 0",
            "surfaces declaring tooltip", left, "surfaces actually served", right, "==")


def _inv_the_console_and_the_law_agree_about_furniture():
    """v2319 — the console's own furniture verdict against the shared law it now delegates to.

    Konyo: "these are locked inventory items within the inventory template thats a LAW ... make
    this also a unified logic within the ai readers and console. it needs a hardcode logic."

    The law WAS already encoded three times — control_app._REGISTER_ANCHORS, vault_corpus's FIXED
    cells, and the live prompt's prose — and the retro readers could see none of them. Now there is
    one module and the console asks it. This pair fails the moment those two answers part, in
    either direction: a console that stops recognising the cube, or a law that starts calling loot
    furniture. [[copy-drift]]
    """
    import control_app as ca
    import inventory_law as il

    NAMES = ("Horadric Cube", "Tome of Identify", "Tome of Town Portal", "Wirt's Leg")

    def left():
        return sum(1 for n in NAMES if ca._register_is_anchor(n.lower()))

    def right():
        return sum(1 for n in NAMES if il.is_locked(n))

    return ("furniture-law-agrees",
            "the console and the shared inventory law name the same items as furniture",
            "drop one from inventory_law.LOCKED and this parts 4 vs 3",
            "console anchors", left, "the shared law", right, "==")


def _inv_the_tooltip_finder_refuses_more_than_it_finds():
    """v2321 — a finder that never refuses is not finding, it is guessing.

    Text density alone locates the HUD: on a reel that registered nothing it returned the same
    (2450, 0, 490, 318) corner box on five consecutive frames. The 8% area floor is what separates
    a real tooltip (33.4% of the frame) from that impostor (2.8%), and the tell that the floor is
    still doing its job is that REFUSALS outnumber LOCATIONS — most frames in a reel have no
    tooltip on them, because he is walking, fighting and looting between hovers.

    If locations ever outnumber refusals, either the floor has been lowered or he has started
    hovering on every single frame. The first is a defect and the second has never happened.
    """
    import tooltip_find as tf

    def left():
        return int((tf.report() or {}).get("refused") or 0)

    def right():
        return int((tf.report() or {}).get("located") or 0)

    return ("tooltip-finder-refuses",
            "the tooltip finder still refuses more frames than it claims (most frames have no tooltip)",
            "drop _MIN_AREA_FRAC and the HUD box starts counting as a tooltip on every frame",
            "frames refused", left, "tooltips located", right, ">=")


#: v2434 — INVARIANTS DELIBERATELY NOT IN BUILDERS, each with the reason it is not run.
#: ⚠ THIS EXISTS BECAUSE THE TWO REGISTRIES DISAGREED BY ONE AND NOTHING SAID SO.
#: `run()` / `verdict()` / the eagle iterate BUILDERS. `prove_each()` (:1017) and the independence
#: audit (:1116) enumerate `sorted(n for n in globals() if n.startswith("_inv_"))` instead. Those
#: two rosters are not the same roster, and for the whole life of this file they have differed by
#: `_inv_the_deleter_is_never_looser_than_the_planner` — graded by the self-proving surface as
#: proven=True, and never once evaluated by the live path. `git log -S` finds no commit that ever
#: added it to BUILDERS, so it has never run.
#: A surface that reports on an invariant the engine cannot run is the shape this whole module
#: exists to catch, one level up from the invariants themselves. Declaring it is not a fix for the
#: invariant; it is what stops the DIVERGENCE being silent. The selftest below now refuses any
#: `_inv_*` that is in neither list. [[the-unjoined-end]] [[unknown-stays-unknown]]
RETIRED = {
    "_inv_the_deleter_is_never_looser_than_the_planner":
        "superseded in practice by `frame-deleter-not-looser` (:401), which asks the same question "
        "-- the frame deleter must never free more than the reel planner offers -- against "
        "frame_authority.free vs retention.candidate pages. This earlier version was never "
        "registered. It is kept, not deleted, because its docstring records the 2026-08-30 "
        "disagreement between reel_retention and frame_authority and why the strict one was RIGHT "
        "to hold; that reasoning is worth more than the function. If it should run, move it into "
        "BUILDERS and delete this entry -- do not leave it in both.",
}

def _inv_every_door_counts_the_reels_it_opened():
    """v2687 — THE PARENT'S COUNTER vs THE CHILD'S STAMP. Two witnesses to one event.

    The defect this is written from: v2316 gave each capture door a Wilson score, and only
    `shadow` ever passed opened=True. Measured on his live ledger 2026-09-05 —

        shadow  opened=609  filmed=181        onair  opened=0        mini  opened=0

    — while ON AIR and MINI had been filming reels the whole time. Nothing reported it, and the
    report itself was HONEST: `wilson: null`, "no sealed reel from this door yet — nothing has been
    proved either way". Every word true. A broken counter and a door nobody pressed are the same
    sentence, and only a SECOND witness can tell them apart. [[zero-needs-a-denominator]]

    The second witness is the journal. Since v2687 the agent stamps `door` onto every row it
    writes, so the reels are counted twice by parties that do not talk to each other: the parent
    increments a counter at spawn, the child writes a name into its own file.

    NOT equality — CONTAINMENT, and the direction is the point. A reel can open and write nothing
    (a near-black shadow reel does exactly that, 263 of them), so the journal can only ever hold a
    SUBSET of what the doors opened. If the journal ever shows MORE door-stamped sessions than the
    doors admit opening, a counter is not being incremented — which is the original bug, and it is
    the only direction that can catch it.

    ⚠ PRE-v2687 REELS CARRY NO STAMP AND MUST NOT BE COUNTED. They are not evidence of a missing
    increment; they are evidence of nothing, and forging a door for them is the exact lie the
    stamp's own guard refuses. An unstamped reel is UNKNOWN. [[unknown-stays-unknown]]
    """
    import control_app as ca

    def left():
        """Distinct sessions the AGENT stamped with a door — the child's testimony."""
        try:
            import reel_templates as rt
            by, why = rt._journal_rows()
            if why:
                return None
            return len({sid for sid, rows in (by or {}).items()
                        if any(str((r or {}).get("door") or "").strip() for r in (rows or []))})
        except Exception:
            return None

    def right():
        """Opens claimed by the doors — the parent's testimony.

        ⚠ v3297 — AN ABSENT LEDGER IS UNKNOWN, NEVER 0. `_capture_door_load` swallows a missing
        file into {}, and the report then coerces every door to int 0 — so "no ledger exists in
        this world" and "672 attempts, 0 opens" were byte-identical to this reading. Measured
        2026-09-18: the guest seed world ships the journal (56 door-stamped sessions) and NO
        capture_doors.json, and this arm manufactured the 56-vs-0 disagreement on its panel. The
        non-int check below can never catch a missing FILE, because {} always yields int 0, so
        the absence is refused HERE, before the report flattens it. [[zero-needs-a-denominator]]
        """
        try:
            if not os.path.exists(ca._capture_doors_path()):
                return None
            rep = ca.capture_door_report() or {}
            tot = 0
            for _d, row in rep.items():
                n = (row or {}).get("opened")
                if not isinstance(n, int):
                    return None
                tot += n
            return tot
        except Exception:
            return None

    return ("door-opens-are-counted",
            "no more door-stamped sessions in the journal than the doors admit opening",
            "stop passing opened=True in start_agent and film a reel: the journal gains a stamped "
            "session while the ledger's total stands still, and these part",
            "journal sessions carrying a door", left, "ledger opened (all doors)", right, "<=")


def _inv_only_a_declared_owner_world_posts_owner_numbers():
    """v2695 — WOULD HAVE FLAGGED HIS COUSIN'S BOARD THE DAY IT HAPPENED.

    Konyo: "this should be or have been connected to the heart of the console so regression for
    this.. or it suddenly not cross referencing should and could have been flagged?" He is right,
    and the two witnesses were already on disk.

    THE DEFECT IT WATCHES. bible.html carries `_GRAIL_SEED` (245 of HIS dated finds) and applies it
    to any board that resolves as OWNER. `_isCousinShell` is only `!_D2R_OWNER`, so pressing "claim
    this browser" flipped a stranger into the owner world and handed him another man's chronicle —
    his cousin Dean's Uniques tab read 243/403 of items he has never held. Fixed in v2692 by giving
    the seeds a named ledger; this is the alarm that says if it ever comes back.

    THE TWO WITNESSES, and they do not talk to each other:
      LEFT   `byRoute` — every route that actually POSTED a tally, each stamped with its install id
             and its namespace prefix. An owner-namespace post carries pfx ''.
      RIGHT  `ownerWorlds` — the worlds the console DECLARES are his.
    An install that posts owner numbers while not being a declared owner world is a stranger inside
    the owner namespace. That is the leak, stated as arithmetic.

    MEASURED on his tree when this was written: 404 routes — 401 guests, every one reading
    uniques.have 0 (the per-install ledger works and has never leaked to a guest), and 3 owner-pfx
    routes: 77f64154 (292/123/99), c5c2c92d (280/120/99) and one null-id bootstrap row. Both real
    ids are in ownerWorlds, so this holds at 0 today.

    ⚠ CONTAINMENT, NOT EQUALITY, and the direction is the point: undeclared-owner-posts <= 0. A
    world can be declared and never post (he has two and one is stale); the reverse — posting
    owner numbers without being declared — is the only direction that can be a leak.
    ⚠ THE NULL-ID ROW IS NOT A VIOLATION. It carries no install id at all, so it names nobody and
    cannot be a stranger; counting it would make this red forever over a bootstrap artifact.
    [[unknown-stays-unknown]]
    """
    import json as _json
    import os as _os

    def _tally():
        try:
            with open(_os.path.join(HERE, "board_tally.json"), encoding="utf-8") as fh:
                return _json.load(fh) or {}
        except Exception:
            return None

    def left():
        """Install ids that POSTED owner-namespace numbers and are NOT declared owner worlds."""
        d = _tally()
        if d is None:
            return None
        declared = set()
        for w in (d.get("ownerWorlds") or []):
            declared.add(str(w).split("|")[0])
        oid = d.get("ownerId")
        if oid:
            declared.add(str(oid))
        # ⚠⚠ v2703 — AN EMPTY ROSTER IS UNKNOWN, NOT A LEAK. `_tally()` returns None only when the
        # file is missing or will not parse. A tally written mid-update, or by a version that has
        # not yet populated ownerWorlds, parses fine and yields declared == set() — and then EVERY
        # owner-namespace route lands in `bad`. Measured on his real tally: ownerWorlds holds 2 and
        # ownerId is set, so this is LATENT today, not firing. But a reader failure must never
        # manufacture a red; the honest answer when nothing is declared is that nobody can say.
        if not declared:
            return None
        bad = set()
        for v in (d.get("byRoute") or {}).values():
            r = (v or {}).get("route") or {}
            # ⚠⚠ v2703 — A MISSING `pfx` IS UNKNOWN, NOT AN ASSERTION OF THE OWNER NAMESPACE.
            # This read `if r.get("pfx"): continue`, so an ABSENT key is falsy and fell through to
            # be judged as an owner-namespace post. Two lines below, an absent `id` is explicitly
            # treated as UNKNOWN with a comment citing unknown-stays-unknown by name — the same
            # file giving absent evidence opposite meanings depending on which field is missing.
            # Measured on his tally: 404 byRoute rows, 401 carry a truthy pfx, exactly ONE has no
            # pfx key at all, and that row also has no id, so the guard below catches it first.
            # LATENT today; it fires the moment a row lands with an id and no pfx.
            if "pfx" not in r:
                continue                      # nobody recorded a namespace; that names nobody
            if r.get("pfx"):
                continue                      # a guest route — its own namespace, not the owner's
            rid = r.get("id")
            if not rid:
                continue                      # no id names nobody; see the note above
            if str(rid) not in declared:
                bad.add(str(rid))
        return len(bad)

    def right():
        d = _tally()
        if d is None:
            return None
        declared = set(str(w).split("|")[0] for w in (d.get("ownerWorlds") or []))
        if d.get("ownerId"):
            declared.add(str(d.get("ownerId")))
        return None if not declared else 0

    return ("owner-namespace-is-declared",
            "no install posts owner-namespace numbers without being a declared owner world",
            "claim a fresh browser, let it post a tally, and its id appears with pfx '' while "
            "ownerWorlds still lists only his — these part",
            "undeclared installs posting owner numbers", left, "the allowed number of them", right,
            "<=")


def _inv_the_evidence_ledger_survived_the_sweep_that_filled_it():
    """v2730 — 310 NAMES OF TESTIMONY, 7,944 SIGHTINGS, AND NOTHING WAS WATCHING THEM.

    Konyo: *"the join the heart of the console connect and wire whatever is needed so its all not
    in the dark"*. `chron_evidence.json` is, in its own writer's words (control_app.py:19721),
    "the only thing making cross-reel corroboration possible" — and grepping corroborate.py,
    console_doctor.py, heart.py and lane_census.py for it returned ZERO hits. It was not declared
    covered and not declared uncovered; it was simply unexplained, which is the silence
    `coverage()` exists to shout about.

    ⚠⚠ AND THE FAILURE IT WATCHES FOR HAS ALREADY HAPPENED ONCE. v1779's docstring records that
    `_chron_evidence_load` returned {} on any exception, `_chron_evidence_merge` then merged the
    current run into {} and saved THAT as the whole accumulated ledger — so ONE TORN READ SILENTLY
    DELETED EVERY SIGHTING EVER COLLECTED. Nothing on any screen would have said so.

    THE TWO SIDES, and why they are independent WITHOUT being computed independently:
      LEFT   chronicle_swept.json — did the sweep ever bank a page? (any entry with pages > 0)
      RIGHT  chron_evidence.json  — does the evidence ledger hold any name at all?
    Both are written during the same sweep, from the same result — so this is NOT independence of
    DERIVATION. It is independence of SURVIVAL: two files, two save functions, two failure modes.
    The v1779 bug destroyed one and left the other untouched, which is exactly the shape a
    corroborator can see and a single reader cannot. Measured today: chronicle_swept.json holds 401
    entries, 24 with pages > 0; chron_evidence.json holds 310 uniques and 126 sets.

    ⚠ THE RELATION IS `<=` AND THE DIRECTION IS THE POINT. "We remember sweeping pages" (1) while
    "the ledger holds nothing" (0) is 1 <= 0 and FAILS. The reverse — evidence without a sweep
    memory — is not a loss and is allowed: a rebuilt or hand-seeded ledger is not a defect.

    ⚠ EMPTY IS UNKNOWN, NOT ZERO, ON BOTH SIDES. A tree that has never swept has nothing to say
    about whether the ledger survived, and answering 0 there would make this hold vacuously on
    every fresh checkout — the [[zero-needs-a-denominator]] trap that let another invariant in this
    file pass for months while examining nothing. [[unknown-stays-unknown]]
    """
    def left():
        import control_app as ca
        try:
            sw = ca._chron_swept_mem()
        except Exception:
            return None
        if not isinstance(sw, dict) or not sw:
            return None                      # nothing swept yet — UNKNOWN, never 0
        return 1 if any(isinstance(v, dict) and (v.get("pages") or 0) > 0
                        for v in sw.values()) else 0

    def right():
        import control_app as ca
        try:
            ev = ca._chron_evidence_load()
        except Exception:
            return None
        if not isinstance(ev, dict):
            return None
        n = len(ev.get("uniques") or {}) + len(ev.get("sets") or {})
        if n == 0 and not ev:
            return None                      # an absent file is not an emptied one
        return 1 if n > 0 else 0

    return ("evidence-survived-its-sweep",
            "if the sweep remembers banking pages, the evidence ledger still holds names",
            "empty chron_evidence.json while chronicle_swept.json still remembers 24 reels with "
            "pages — the exact v1779 failure, where one torn read deleted every sighting ever "
            "collected and no screen said so",
            "sweep memory banked pages", left,
            "evidence ledger holds names", right, "<=")


def _inv_every_rung_the_shelf_declares_is_one_the_funnel_can_ACCOUNT_FOR():
    """v2725 — THE RUNG VOCABULARY HAS TWO OWNERS, AND ONLY ONE OF THEM KNOWS IT.

    `reel_story.STAGES` is the ladder a reel climbs. `one_funnel` reports, per rung, how a reel's
    passage is observed — from a CACHE (`WAYPOINT_SOURCES`) or from a LIVE DECIDER
    (`DERIVED_SOURCES`, added v2725). Nothing made the second list follow the first.

    THE FAILURE THIS CATCHES, and it is not hypothetical: reel_story's own module docstring
    already names a SEVENTH stage that STAGES does not yet carry —

        PRUNED   gone, tombstoned   reel_retention._tombstone

    The day that lands in STAGES, one_funnel gains a rung it has never been taught about. It would
    not crash and it would not go red. `_store_of` would answer "no store records this rung",
    `DERIVED_SOURCES` would have no entry, and the new rung would report as TRACELESS — the exact
    false sentence v2725 was written to delete, reappearing on a different rung. The passage
    fraction would also silently change denominator, from `of 6` to `of 7`, with no edit to the
    text that prints it. [[label-outlived-referent]]

    THE TWO SIDES ARE INDEPENDENT, which is the whole point:
      LEFT   reel_story.STAGES               — the shelf's vocabulary, owned by reel_story
      RIGHT  the rungs one_funnel can account for — owned by one_funnel, and derived from two
             different maps neither of which reel_story imports

    ⚠ THE RELATION IS `<=`, NOT `==`, ON PURPOSE. one_funnel is allowed to know about a rung the
    shelf has retired; that is harmless and self-correcting. The dangerous direction is a stage the
    shelf declares and the funnel cannot see, which is the only one an inequality here forbids.
    ⚠ EITHER SIDE UNIMPORTABLE IS UNKNOWN, NEVER ZERO. `0 <= 0` would hold forever on any machine
    where these modules will not load, which is precisely how
    _inv_a_world_reporting_nothing_holds_nothing passed vacuously for months.
    """
    def left():
        import reel_story as RS
        st = tuple(getattr(RS, "STAGES", ()) or ())
        return len(st) if st else None

    def right():
        import one_funnel as OF
        known = set(getattr(OF, "WAYPOINT_SOURCES", {}) or {}) | set(
            getattr(OF, "DERIVED_SOURCES", {}) or {})
        return len(known) if known else None

    return ("every-rung-is-accounted-for",
            "every stage the reel shelf declares is a rung one_funnel can observe, by cache or by "
            "live decider",
            "add a stage to reel_story.STAGES and teach one_funnel nothing: the new rung reports "
            "as traceless and the passage denominator moves with no edit to the text printing it",
            "reel_story.STAGES", left,
            "rungs one_funnel accounts for", right, "<=")


def _inv_a_world_reporting_nothing_holds_nothing():
    """v2696 — WOULD HAVE CAUGHT DEAN'S BOARD, WHICH THE PREVIOUS INVARIANT COULD NOT.

    Konyo: "via the roster via the fleet maybe? like we have trackers within the console maybe?" —
    yes, and the two witnesses were already on disk, in the same snapshot.

    THE SYMPTOM HE REPORTED: his cousin's world showed 0/403 in the console FLEET while the same
    board's Uniques chronicle tab read 243/403. Both surfaces count with the same funiScan(), so
    they cannot differ by logic — only by TIME, and a fleet row is a snapshot read off disk.
    The honest, unambiguous half of that disagreement is this: a world that REPORTS zero finds while
    its own ledger HOLDS entries is contradicting itself, whatever the reason.

    THE TWO WITNESSES, and they are independent readings of one image:
      LEFT   d2r_tally.uniques.have — what the BOARD said about itself
      RIGHT  d2r_foundLog           — the ledger it said it from
    control_app._store_read_all() takes both keys in ONE snapshot, and its own docstring is why
    that matters: "a route can never be paired with another snapshot's values". Reading them
    separately would let a stale tally meet a fresh ledger and invent a disagreement.

    ⚠ ZERO-AND-EMPTY IS NOT A VIOLATION, and that distinction is the whole invariant. A fresh guest
    world reports 0 and holds nothing — correct, and the commonest state on his tree (401 guest
    routes, every one 0). Only 0-while-holding is a contradiction. [[zero-needs-a-denominator]]
    ⚠ IT DOES NOT COMPARE MAGNITUDES. foundLog holds uniques AND set pieces (measured on his own
    world: tally 292 uniques, foundLog 419 keys), so "292 != 419" is not a defect and asserting it
    would be a gate red from birth. Only the zero case is unambiguous.

    MEASURED when written: 1 board world readable on this machine — owner, tally 292, foundLog 419.
    Holds at 0.
    """
    def _worlds():
        try:
            import control_app as ca
        except Exception:
            return None
        out = []
        try:
            for db in ca._webkit_localstorage_dbs():
                got = ca._store_read_all(db, ("d2r_tally", "d2r_foundLog"))
                if not got or not got.get("isBoard"):
                    continue
                v = got.get("vals") or {}
                t = v.get("d2r_tally")
                fl = v.get("d2r_foundLog")
                if not isinstance(t, dict) or not isinstance(fl, dict):
                    continue
                have = ((t.get("uniques") or {}) if isinstance(t.get("uniques"), dict) else {}).get("have")
                out.append((have, len(fl)))
        except Exception:
            return None
        return out

    #: ⚠⚠ v2703 — AN EMPTY WORLD LIST IS UNKNOWN, NOT ZERO, AND THIS PASSED VACUOUSLY FOR MONTHS.
    #: `_worlds()` returns None only on an EXCEPTION. When ca._webkit_localstorage_dbs() simply
    #: yields nothing — Linux CI, the Windows PC, any machine that is not his Mac — it returns [].
    #: left() then summed an empty list to 0, right() returned 0, and `0 <= 0` held forever.
    #:
    #: MEASURED 2026-09-06: this Mac has 1 WebKit localStorage DB and 1 of them is a board world.
    #: CI and the Windows PC have 0. The invariant printed THE SAME GREEN on all three, having
    #: examined one board in one case and nothing at all in the others. Its own docstring says
    #: "MEASURED when written: 1 board world readable on this machine" — which is exactly the
    #: count it never printed at runtime. [[zero-needs-a-denominator]] inside a heart invariant,
    #: which is the layer built to catch this everywhere else.
    def left():
        w = _worlds()
        if w is None:
            return None
        if not w:
            return None      # nothing examined names nothing; a 0 here would be a lie with no author
        return sum(1 for have, held in w if have == 0 and held > 0)

    def right():
        w = _worlds()
        if w is None or not w:
            return None
        return 0

    return ("a-world-reporting-nothing-holds-nothing",
            "no board world reports zero uniques while its own ledger holds entries",
            "seed a world's foundLog and leave its tally at 0 — the fleet then shows 0/403 for a "
            "board that holds a chronicle, which is what he saw and what nothing flagged",
            "worlds reporting 0 while holding a ledger", left, "the allowed number of them", right,
            "<=")


def _inv_every_backed_up_store_can_be_PUT_BACK_or_says_it_cannot():
    """v2735 — A BACKUP COPIES FIVE STORES AND THE DOOR IT COMES BACK THROUGH TAKES TWO.

    Konyo: *"i want it no wiped · i want that saved · and being able to be restored · indefinitely"*
    and *"the join the heart of the console connect and wire whatever is needed so its all not in
    the dark"*.

    The backup and the restore were built at different times against different vocabularies:
        BACKED UP (v2731)   foundLog · owned · setPieces · rwMade · gameFound
        RESTORABLE          foundLog -> uniques, setPieces -> sets   (chronicleApply's two halves)
    Three of five cannot travel back through that door. `ledger_restore` names them in
    `BACKED_UP_ONLY` and reports them on every plan, so the gap is stated rather than hidden — a
    restore that silently covered two of five stores while reporting success is the worst kind.

    ⚠ WHAT THIS INVARIANT ACTUALLY WATCHES is the drift, not the gap. The gap is a known, declared
    design fact. The failure is a SIXTH store joining the backup — the way rwMade and gameFound
    joined it — with nobody deciding whether it can be put back. It would be copied faithfully
    forever and be unrestorable, and every existing check would stay green, because each one grades
    a list it was given rather than the list that exists. That is the same shape as the two stores
    which were absent from sixty consecutive backups while a ratchet watched a column that could
    only read UNKNOWN. [[the-unjoined-end]] [[copy-drift]]

    THE TWO SIDES:
      LEFT   stores present in the newest backup FILE that `ledger_restore` has never heard of
      RIGHT  0
    Independent by SOURCE, not by derivation: the left is read off an artifact on disk that a
    running console wrote, the right is a constant in a module. A store can only appear on the left
    by being written to a real backup, which is precisely the event that needs a decision.

    ⚠ NO BACKUP FILE IS UNKNOWN, NOT ZERO. A fresh checkout has never snapshotted anything and has
    nothing to say about which stores travel; answering 0 would make this hold vacuously forever.
    [[zero-needs-a-denominator]]
    """
    def left():
        import glob as _g
        import json as _j
        import os as _o
        d = _o.path.expanduser("~/d2r_ledger_backups")
        if not _o.path.isdir(d):
            return None
        files = sorted(_g.glob(_o.path.join(d, "ledger_*.json")), key=_o.path.getmtime, reverse=True)
        if not files:
            return None                      # never snapshotted — UNKNOWN, never 0
        try:
            with open(files[0], encoding="utf-8") as fh:
                blob = _j.load(fh)
        except Exception:
            return None                      # unreadable is UNKNOWN, not "no stray stores"
        led = (blob or {}).get("ledger")
        if not isinstance(led, dict) or not led:
            return None
        try:
            import ledger_restore as _LR
        except Exception:
            return None                      # the module is the right-hand side; absent is UNKNOWN
        known = set(_LR.RESTORABLE) | set(_LR.BACKED_UP_ONLY)
        stray = [k for k in led if k not in known]
        # REG-1481 — the hand-made stores the watcher judges live in `allStores`, not in `led`, and each
        # must have a declared way back (HAND_MADE_DOOR). A store added to HAND_MADE without a door is
        # the same drift one level down: judged, paged, and nowhere to send him.
        al = (blob or {}).get("allStores")
        if isinstance(al, dict):
            stray += [s for s in getattr(_LR, "HAND_MADE", ())
                      if ("d2r_" + s) in al and s not in getattr(_LR, "HAND_MADE_DOOR", {})]
        return len(stray)

    def right():
        return 0

    return ("backup-restore-vocabulary",
            "every store the backup writes is one the restore has an answer for, even if the "
            "answer is that it cannot travel",
            "add a sixth store to the backup and leave ledger_restore's two lists alone — it is "
            "then copied faithfully forever and can never be put back, and nothing says so",
            "stores in the newest backup that ledger_restore does not know", left,
            "the allowed number of them", right, "<=")


def _inv_no_world_reports_progress_it_INHERITED_from_the_owner_seed():
    """v2739 — DEAN'S CONSOLE SHOWS 249/403 UNIQUES HE NEVER FOUND, AND EVERY CHECK AGREED.

    Konyo, seeing THE FLEET card on his own console: *"it should be rendering for him 0 meaning
    its not and has not been sycned yet based on his profile and ledgers"*.

    ⚠ THE FLEET IS NOT LYING, WHICH IS WHY NOTHING CAUGHT IT. The 249 really are in Dean's own
    `d2r_foundLog`. bible.html:3990 resolves an UNNAMED ledger to 'KonyoEndgame' whenever the world
    holds any rows at all, and :20442 then re-seeds every missing `_GRAIL_SEED` name on EVERY boot.
    So Konyo's 245 finds are written into Dean's store, and every downstream reader reports them
    faithfully as Dean's progress.

    ⚠⚠ AND THE EXISTING GUARD CANNOT SEE IT. `_inv_only_a_declared_owner_world_posts_owner_numbers`
    asks whether an UNDECLARED world is posting owner numbers. Dean IS declared — he is a legitimate
    guest world with a legitimate install. Nothing guarded a declared world INHERITING the seed,
    which is a different sentence and needed a different invariant. [[gate-blind-to-unexercised-input]]

    THE TWO SIDES:
      LEFT   worlds whose ledger resolves to the SEED ledger while not being the owner install
      RIGHT  0
    Independent by SOURCE: the left is computed in the BOARD window, where `_D2R_LEDGER` and
    `_SEED_LEDGER` both live and where the resolution actually happens; the right is a constant.
    Neither side is derived from the tally the fleet prints, which is the number that looked fine.

    ⚠ IT CANNOT REPAIR ANYTHING, AND MUST NOT CLAIM TO. Stamping `d2r_ledgerName` happens on DEAN'S
    machine — v2692's claim button does exactly that. This turns an invisible contamination into a
    stated one, which is the whole of what this machine can reach. [[unknown-stays-unknown]]
    """
    def left():
        """How many DISTINCT installs currently report that the owner's seed belongs to them.

        ⚠⚠ v2740 — v2739 ASKED THIS AS "IS THIS BOARD SEEDED", AND THAT QUESTION HAS NO ANSWER.
        The board's real decision is
            _seedsBelongHere = (!_isCousinShell && _D2R_LEDGER === _SEED_LEDGER)
        and `_isCousinShell = !_D2R_OWNER`, so it is TRUE on a CLAIMED browser whose ledger
        resolves to the seed. That is correct and expected on KONYO'S OWN board — it is his seed —
        and identical, from inside the board, on a stranger's claimed-and-unnamed one. A single
        board cannot tell the two apart, so a per-board law either cries wolf on his own console or
        says nothing at all. v2739's version did worse than both: it computed `!owner && ...`,
        firing only on GUESTS, who are the one class the seed can never reach.

        THE FLEET CAN TELL. Exactly one install may legitimately own the seed ledger. Two or more
        is contamination by construction, and no single machine can see it. This is the shape a
        corroborator exists for. [[feedback-contradiction-is-the-finding]]
        """
        import control_app as ca
        # ⚠ `fleet_pull()` IS NOT THE FLEET — it reports a git pull, and keys off it are all
        # missing, so the first cut of this law returned None forever: permanently UNKNOWN, which
        # is invisible rather than loud. `fleet_presence()` is the roster, split online/offline,
        # each row carrying `install` and the `tally` the beacon reported.
        # [[feedback-suspect-the-instrument]] [[zero-needs-a-denominator]]
        try:
            fl = ca.fleet_presence() or {}
        except Exception:
            return None
        if not isinstance(fl, dict) or not fl.get("ok"):
            return None
        rows = list(fl.get("online") or []) + list(fl.get("offline") or [])
        if not rows:
            return None                      # no fleet answer — UNKNOWN, never 0
        seen, answered = set(), 0
        for m in rows:
            t = (m or {}).get("tally")
            v = (t or {}).get("onOwnerSeed") if isinstance(t, dict) else None
            if v is None:
                continue                     # that console predates the field; it is not a zero
            answered += 1
            if v:
                # keyed on INSTALL, not machine name: two boards can share a nickname, and the
                # question is how many distinct installs claim the ledger
                seen.add(str((m or {}).get("install") or (m or {}).get("machine") or len(seen)))
        if not answered:
            return None                      # nobody could answer, so the count is UNKNOWN
        return len(seen)

    def right():
        # exactly one board may own the seed ledger: the one the seed was written for
        return 1

    return ("owner-seed-inheritance",
            "no world reports progress it inherited from the owner's hardcoded seed",
            "point a guest world at an unnamed ledger — it resolves to the seed ledger, the boot "
            "path re-seeds 245 of the owner's finds into it, and every tally reports them as that "
            "person's own progress while staying internally consistent",
            "installs claiming the owner seed ledger", left,
            "the one board it was written for", right, "<=")


def _inv_the_router_and_the_shelf_count_the_SAME_reels():
    """v2742 — THE STATION ASSIGNER IS WATCHED BY NOTHING, AND IT IS THE WHOLE STAMP.

    Konyo: *"all connected to the heart of the console obviously so they flag themselves"*.

    MEASURED before writing this, because a fourth watcher over a well-watched module is decoration
    while the centre goes unguarded:

        module            corroborate invariants     console_doctor checks
        reel_router                 0                        0     <- the STATION ASSIGNER
        printer                     0                        0     <- the STORYLINE
        reel_retention             13                        1
        frame_authority            15                        0

    `reel_router` assigns one station per reel — INTAKE · TRIAGE · EMPTY · STATION · PRINTER ·
    JOIN · CAPTURE · ROUTED · TOMBSTONE — and is watched by no invariant, checked by no doctor row,
    and read by NO console code (`grep -c reel_router tv/control_app.py` -> 0). Built, correct,
    covered by its own suite, and invisible to every supervision layer in the repo.

    THE TWO SIDES:
      LEFT   how many reels reel_router.route() stations
      RIGHT  how many reels reel_story.story() puts on the shelf
    INDEPENDENT BY DERIVATION, which is the point: `reel_router.assert_independent_of_retention`
    exists precisely because the router must NOT reach through reel_retention, while reel_story
    quotes retention's plan directly. Two walks over one shelf, computed from different sources.
    If they disagree about how many reels EXIST, one of them is enumerating something the other
    cannot see — and neither module can notice that about itself.

    ⚠ EQUALITY, NOT `<=`. A router that stations FEWER reels than the shelf holds is silently
    dropping some; a router that stations MORE has invented one. Both directions are defects here,
    so the relation is `==` and the invariant says so rather than picking the comfortable half.
    ⚠ EITHER SIDE UNREADABLE IS UNKNOWN, NEVER 0 — a fresh checkout with no shelf must not make
    this hold vacuously. [[zero-needs-a-denominator]]
    """
    def left():
        try:
            import reel_router as _rr
            d = _rr.route()
        except Exception:
            return None
        if not isinstance(d, dict) or not d.get("ok"):
            return None
        rows = d.get("reels")
        return len(rows) if isinstance(rows, list) and rows else None

    def right():
        try:
            import reel_story as _rs
            st = _rs.story()
        except Exception:
            return None
        if not isinstance(st, dict) or not st.get("ok"):
            return None
        rows = st.get("reels")
        return len(rows) if isinstance(rows, list) and rows else None

    return ("router-and-shelf-agree",
            "the station assigner and the shelf are looking at the same reels",
            "let the router enumerate on a different root, or teach one of them a filter the other "
            "does not have, and every station count becomes a claim about a shelf nobody else sees",
            "reels the router stations", left, "reels on the shelf", right, "==")


def _inv_every_seed_the_authority_NAMES_has_a_door_that_can_REMOVE_it():
    """v2746 — THE CARD PROMISES A REMOVAL; THE BUTTON IS WHAT PERFORMS IT.

    Konyo, on Dean's fleet card: *"how does that get removed what of him to do?"* — so the fleet
    card is about to state, per ledger, how many of a person's rows came from the owner's hardcoded
    seed, and point them at the un-seed door to remove them.

    THAT MAKES TWO HALVES THAT MUST AGREE ABOUT WHICH SEEDS EXIST, and they are maintained in
    different places by different hands:

        `ledger_authority.SEED_ANCHORS`  the console's list of seed literals, used to COUNT what
                                         is inherited and to print it on his card
        `window._d2rUnseed`              bible.html's exit door (:9988), which STRIPS them

    If the authority knows a seed the door does not touch, the card says "246 of your rows were
    inherited", the person presses the button, and those rows survive — then the boot floor
    re-asserts them on the next load and the warning comes back with no explanation. If the door
    strips a seed the authority never counted, the button deletes more than the card said it would.
    Both directions are silent, and neither file can notice it about itself. [[the-unjoined-end]]

    ⚠⚠ THE FIFTH SEED IS WHY THIS IS NOT HYPOTHETICAL. `_RWV_SEED` (bible.html:18488) was an inline
    literal until v2704 and is named in bible.html's own comment as "THE FIFTH SEED ... the other
    four" — a seed that existed, was applied, and was invisible to every list that enumerated them.
    A sixth added tomorrow lands in exactly the same blind spot.

    THE TWO SIDES:
      LEFT   seed literals the authority declares AND can actually parse out of bible.html
      RIGHT  distinct `window._*_SEED` globals the un-seed door's own body reaches
    Independent by DERIVATION, not merely by file: the left is a DECLARATION TABLE resolved by
    brace-matching each anchor and parsing the object; the right is read off EXECUTABLE STATEMENTS
    inside one function body. Neither consults the other, and neither counts rows — a seed that
    grows by a hundred names moves neither side, which is correct: this asks how many seeds there
    ARE, never how big they are.

    ⚠ EQUALITY, NOT `<=`. Both directions are real defects, so the relation refuses to pick the
    comfortable half.
    ⚠ EITHER SIDE UNREADABLE IS UNKNOWN, NEVER 0 — a bible.html that cannot be read must not make
    this hold vacuously with 0 == 0. [[zero-needs-a-denominator]]
    """
    def left():
        try:
            import ledger_authority as la
            t = la.seed_table()
        except Exception:
            return None
        if not isinstance(t, dict) or not t.get("ok"):
            return None                      # a refused parse is UNKNOWN, not "no seeds exist"
        n = len(t.get("seeds") or {})
        return n or None

    def right():
        import io as _io
        import re as _re
        p = os.path.join(os.path.dirname(HERE), "bible.html")
        try:
            with _io.open(p, encoding="utf-8", errors="replace") as fh:
                src = fh.read()
        except Exception:
            return None
        # ⚠ ANCHORED AT BOTH ENDS. A fixed-size window past the end of a 14 KB function body reads
        # as "this door reaches no seeds at all", which is a green nobody measured.
        # [[source-reading-guard]]
        i = src.find("window._d2rUnseed = function(){")
        if i < 0:
            return None                      # the door was renamed — UNKNOWN, never 0
        j = src.find("window._d2rUnseedRestore", i + 20)
        if j < 0:
            return None
        body = src[i:j]
        names = set(_re.findall(r"window\.(_[A-Z][A-Z0-9_]*_SEED)\b", body))
        return len(names) or None

    return ("seed-exit-door-covers-every-seed",
            "every seed the console counts as inherited has a door that can remove it",
            "add a sixth seed literal to bible.html and register it in "
            "ledger_authority.SEED_ANCHORS without teaching window._d2rUnseed to strip it — the "
            "fleet card then reports rows as inherited that the exit button leaves behind, and the "
            "boot floor re-asserts them on the next load",
            "seed literals the authority parses", left,
            "seeds the un-seed door reaches", right, "==")


def _inv_a_posted_COUNT_and_its_own_MASK_agree():
    """v2746 — TWO SURFACES PUBLISH THE SAME FIGURE; NOTHING EVER ASKED WHETHER THEY MATCH.

    Konyo: *"and also not be mixing with the other consoles and profiles related... and sets also
    needs to be fetched from the right data so it also renders like the sets tab"*.

    Every machine publishes its set-piece progress TWICE, by two unrelated routes:
      · `tally.sets.have` — a COUNT its own console posted (`len(d2r_setPieces)`)
      · `masks.sets`      — an OPAQUE BITMASK, decoded HERE against a roster file on THIS disk
    Neither is derived from the other. The mask is bits over a shared roster and the worker that
    carries it never decodes it, so the popcount is computed on this machine from a different
    artifact entirely. That is a real second witness to one fact, and until now nobody compared them.

    ⚠ THE DIVERGENCE THIS EXISTS FOR IS LATENT ON HIS BOARD, WHICH IS PRECISELY WHY IT NEEDS A LAW.
    The fleet card's numerator is `d2r_setPieces.length` (control_app.py:11847 via g() at :11715);
    the Sets tab counts `pieces.filter(p => setPieces.has(p))` (bible.html:23696). The two agree only
    while the store is a SUBSET of the roster, and nothing checks that. MEASURED 2026-09-06:
        Dean  128 vs popcount 128        Konyo  123 vs popcount 123
    Agreeing today is not a reason to leave it unwatched — it is the definition of a hazard that
    fires the first time a store holds a name the roster lacks. [[gate-blind-to-unexercised-input]]

    THE TWO SIDES:
      LEFT   machine/ledger pairs where the posted count EQUALS the popcount of that machine's mask
      RIGHT  machine/ledger pairs that published both and whose mask could be decoded
    ⚠ ONLY LEDGERS WHOSE TWO SIDES READ THE SAME STORE ARE COMPARED, and the exclusions are NOT
    silent — `ledger_authority.surface_pairs()` names each one with its reason, and the sibling
    invariant below grades the exclusion list itself. An exemption nobody can audit is one that grows.
    ⚠ NO ROW COMPARABLE IS UNKNOWN, NEVER 0 == 0. A fleet that published no masks must not make this
    hold vacuously. [[zero-needs-a-denominator]]
    """
    # ⚠⚠⚠ v2906 — ONE FLEET READING, HANDED TO BOTH SIDES. Each side called `fleet_presence()`
    # for itself and that answer is cached 60s (control_app.py:25361), so a run straddling the
    # expiry GRADED TWO DIFFERENT FLEETS. Measured: Konyo's maskKeys read [sets, uniques] on one
    # probe and [] minutes later, because his masks appear and vanish with his board window. That
    # is not a data defect — it is this invariant reading two worlds and calling the difference a
    # disagreement. [[feedback-suspect-the-instrument]]
    _shared = {"got": False, "fleet": None}

    def _fleet():
        if not _shared["got"]:
            _shared["got"] = True
            try:
                import control_app as _ca
                _shared["fleet"] = _ca.fleet_presence()
            except Exception:
                _shared["fleet"] = None
        return _shared["fleet"]

    def left():
        try:
            import ledger_authority as la
            d = la.mask_cross_check(fleet=_fleet())
        except Exception:
            return None
        if not isinstance(d, dict) or not d.get("ok"):
            return None
        return d["agreeN"] if d.get("comparableN") else None

    def right():
        try:
            import control_app as ca
            import fleet_mask as fm
            # ⚠ IMPORTED HERE, IN **THIS** CLOSURE. `la` is imported inside left() and left() only,
            # so referencing it from right() raises NameError — which the `except Exception:
            # return None` below then SWALLOWED, turning a broken side into a permanent None that
            # reads exactly like "nothing comparable to count". Measured when it was written:
            # right went 1 -> None while left went 1 -> 2. Same shape as the `qs` free-variable
            # defect in /api/river the same day.
            import ledger_authority as la
        except Exception:
            return None
        fl = _fleet() or {}
        if not isinstance(fl, dict) or not fl.get("ok"):
            return None
        rows = list(fl.get("online") or []) + list(fl.get("offline") or [])
        # ⚠⚠ ASK THE AUTHORITY, DO NOT RE-DECLARE ITS MAP. This held a SECOND, hardcoded copy of
        # the ledger->store map with "uniques" simply ABSENT, so the exclusion was accidental
        # rather than stated: `.get("uniques")` returns None, the comparison can never match, and
        # uniques was skipped for a reason nobody wrote down.
        #
        # ⚠ AND IT WAS A LOADED GUN AIMED AT ITS OWN FIX. `ledger_authority.surface_pairs()`
        # already reported uniques `sameQuestion: false`; the day fleet_mask's uniques store was
        # repointed at the tally's, the LEFT side (dynamic) would start counting uniques while
        # this RIGHT side, frozen in a literal, would not. Left != Right, and the invariant would
        # go RED because the code became MORE correct — the two-independently-computed-sides drift
        # this whole file exists to catch, self-inflicted. [[copy-drift]] [[the-unjoined-end]]
        try:
            _same = {str(p.get("ledger")): (p.get("comparable") is True)
                     for p in (la.surface_pairs() or []) if isinstance(p, dict)}
        except Exception:
            return None                      # cannot say which pairs are comparable — UNKNOWN
        n = 0
        for m in rows:
            if not isinstance(m, dict):
                continue
            for led in sorted(fm.LEDGERS):
                # count only the pairs the left side is allowed to compare: the mask's store and
                # the tally's store must be the same store, which ledger_authority states ONCE.
                if not _same.get(led):
                    continue
                mk = (m.get("masks") or {}).get(led)
                t = (m.get("tally") or {}).get(led)
                if not (isinstance(mk, dict) and isinstance(t, dict)):
                    continue
                # ⚠⚠ v2947 — THE UNIVERSE RULE, RE-DERIVED HERE FROM THE ROW ITSELF.
                # v2947 moved the universe half of the gate into mask_cross_check, per ROW. This
                # side must apply the same RULE or the two sides count different populations: left
                # went 2 (uniques excluded for both machines) while this went 4, and the pair went
                # RED because the code got MORE correct — the exact self-inflicted drift the
                # comment above already warns about, one version later.
                # ⚠ RE-DERIVED, NOT BORROWED. It reads the ROW's own `total` and the roster length
                # from fleet_mask, never mask_cross_check's answer — two sides calling one function
                # is one source wearing two hats, and this file exists to catch drift between two
                # genuinely independent computations. [[copy-drift]]
                try:
                    _r, _fp = fm.load_roster_for(led)
                    _rn = len(_r) if _r else None
                except Exception:
                    _rn = None
                _tot = t.get("total") if isinstance(t.get("total"), int) else None
                if _tot is not None and _rn is not None and _tot != _rn:
                    continue
                # ⚠⚠ COMPARABLE, NOT MERELY PUBLISHED. This counted every pair that published both,
                # while the LEFT side counts agreements among pairs mask_cross_check could actually
                # READ — it `continue`s a pair whose roster will not load, and an undecodable mask
                # lands with popcount None. So RIGHT could exceed LEFT with ZERO disagreement, and
                # "they disagree" and "I could not check" shared one red verdict and one sentence.
                # ⚠ Decodability is judged HERE, independently: this side never asks
                # mask_cross_check what it concluded, so the two sides stay two witnesses.
                # [[zero-needs-a-denominator]] [[unknown-stays-unknown]]
                # ⚠ THE FINGERPRINT COMES FROM THE ROSTER LOADER, NOT FROM THE MASK — and the
                # mask dict is passed WHOLE. My first cut read mk["mask"]/mk["fingerprint"], keys
                # this payload does not carry (it is {b, have, n, v}), so decode refused every pair
                # and this side returned None: a confident "nothing is comparable" produced by my
                # own wrong call. Caught because the live value was checked, not assumed.
                _roster, _rw = la._roster_for(led)
                if _roster is None:
                    continue
                try:
                    _rr, _fp = fm.load_roster_for(led)
                    _names, _dw = fm.decode(mk, _roster, _fp)
                except Exception:
                    continue
                if _names is None:
                    continue
                n += 1
        return n or None

    return ("count-and-mask-agree",
            "every machine's posted count matches the mask it published for the same ledger",
            "let a board hold BOTH a sunder's base name and its `Latent ...` form — his own "
            "ledger does, by the v2691 ruling — and the mask sets two bits where the chronicle "
            "counts one row; or let one name differ only by apostrophe glyph and the tally's "
            "canonical fold counts it while the mask's exact match does not",
            "machine/ledger pairs that agree", left,
            "machine/ledger pairs that published both", right, "==")


def _inv_every_figure_pair_under_ONE_NAME_reads_ONE_STORE():
    """v2746 — ⚠⚠ THIS IS RED ON ARRIVAL, FOR A DEFECT IT DID NOT CAUSE. READ BEFORE "FIXING" IT.

    Konyo asked that a disagreement between two surfaces be something the heart states rather than
    something he spots on a screenshot. This is that law, and the first thing it found was already
    live on his console.

    `uniques` NAMES TWO DIFFERENT QUESTIONS:
        fleet_mask.LEDGERS["uniques"]["store"] = "d2r_owned"     <- the VAULT
        grail_tally's `uniques` pair            = chronFound      <- the CHRONICLE
    v2717 moved the tally from the vault measure to the chronicle measure — control_app.py:2004 says
    so in as many words, "`uniques` NOW ANSWERS THE SAME QUESTION THE BOARD'S TABS DO" — and moved
    the old one to `vaultUniques`, named for what it is. **fleet_mask was not moved with it.**

    MEASURED 2026-09-06, popcount vs posted count on the live fleet:
        sets      Dean 128 vs 128     Konyo 123 vs 123     same store, agrees
        uniques   Dean 249 vs   0     Konyo 292 vs 160     DIFFERENT stores, one label

    Dean's vault mask is EMPTY, so `fleet_compare(machine, "uniques")` — his "show me what he has
    that i dont" — answers "he owns none" beside a card reading 249/403. Both numbers are honest
    about different questions, which is exactly why nothing caught it. [[label-outlived-referent]]

    THE FIX IS NOT HERE: either point fleet_mask's uniques store at the chronicle, or rename that
    mask `vaultUniques` to match what control_app already calls it. Until one of those happens this
    is SUPPOSED to be red.

    THE TWO SIDES:
      LEFT   ledgers where the mask's store and the tally's store are the same store
      RIGHT  ledgers that have a mask at all
    Independent by SOURCE: the left reads `fleet_mask.LEDGERS`, a table in one module; the right
    counts the masks a different module actually publishes.
    """
    def left():
        try:
            import ledger_authority as la
            pairs = la.surface_pairs()
        except Exception:
            return None
        if not pairs or any(p.get("ledger") is None for p in pairs):
            return None
        # ⚠⚠ v2945 — THIS INVARIANT IS ABOUT STORES, SO IT ASKS ABOUT STORES.
        # It read `sameQuestion` as a proxy, and when that flag was collapsed into the single
        # `comparable` (which also requires a shared DENOMINATOR) this pair went red — correctly
        # refusing, but about the wrong question: `uniques` genuinely does read ONE store on both
        # sides, and only its universes differ. Its name says "one name, one store"; it now
        # compares the two store fields, which `surface_pairs` publishes as facts precisely so an
        # invariant with a different question does not have to borrow someone else's verdict.
        # [[label-outlived-referent]]
        n = sum(1 for p in pairs
                if p.get("tallyStore") and p.get("maskStore")
                and p.get("tallyStore") == p.get("maskStore"))
        return n if n else None

    def right():
        try:
            import fleet_mask as fm
            n = len(fm.LEDGERS)
        except Exception:
            return None
        return n or None

    return ("one-name-one-store",
            "no two surfaces publish different questions under the same ledger name",
            "point fleet_mask's `uniques` mask at d2r_owned while grail_tally counts chronFound — "
            "both stay internally honest, the cross-reference names the wrong ledger, and the card "
            "beside it shows a number from the other store",
            "ledgers whose mask and tally read one store", left,
            "ledgers that publish a mask", right, "==")


def _inv_a_tier_stands_on_the_looks_the_gate_counts():
    """2026-09-28 (Ledger P0) — AN ITEM'S TIER MUST STAND ON LOOKS THE LIVE GATE WOULD COUNT.

    His ruling (§34.2): "a look is a distinct visit, never a frame of a still screen."
    MEASURED on his vault_accum.json, read-only: Radiance scored HARDENED 103/103 and the Horadric
    Cube HARDENED 21/21, because vault_evidence._measure counted witness ROWS — 102 of Radiance's
    were one stash screen held still. The live gate, vault_retro.gate, counted TWO looks for each.
    Two engines disagreed about the same item for a day and nothing compared them: the doctor row
    'evidence tiers' counted the tiers through the one Wilson function that assigned them.

    THE TWO SIDES:
      LEFT   items the tier table places at PROVEN or above (vault_evidence.tier_census)
      RIGHT  of THOSE SAME items, the ones the LIVE GATE sees at least TRIALS_PROVEN distinct
             looks for (vault_retro.gate's own `looksSeen`, over the same witness rows)
    Independent by ENGINE: the left is the Wilson tier table, the right is the keep-bar gate's own
    witness counting, which owns the independence law (vault_retro.py: "Wilson runs on the FOLDED
    WITNESS LIST, never on raw sightings").

    ⚠ THE RELATION IS `==`, PER ITEM. PROVEN needs a Wilson bound of WILSON_BAR (0.722), which no
    record under ten successful visits reaches (a perfect 9/9 is 0.701), and every successful visit
    is a look the gate counts. So a PROVEN+ item the gate does not back means the tier counted
    something that is not a look.

    ══ 2026-09-28 (Ledger fix, finding 4) — IT COMPARED COUNTS, AND TWO WRONG ITEMS BALANCE ═════
    The first cut was `PROVEN+ count <= count of items with TRIALS_PROVEN+ gate looks`, over the
    WHOLE ledger. Reproduced with two items: StillScreen (1 visit x 25 frames) and TenLooks (10
    buckets, 5 of them unsure). With the frame math back in _measure, StillScreen reads HARDENED
    and TenLooks stays WATCHED 5/10 — left 1 — while TenLooks alone gives the gate side 1. 1 <= 1:
    AGREE, over the exact defect this joint exists for. The right side now counts only the
    tier table's own PROVEN+ names, so a PROVEN+ item without its looks can never be paid for by
    a different item that has them. [[the-unjoined-end]]

    ⚠ WHY NOT trace_spine.independence, which the Ledger design named: it hangs every vault look
    with `witness: None`, so it can count REELS and never re-look visits. A re-look-proven item
    (ten visits in four recordings) would read as a false alarm, and the frame-counting defect
    passes it cleanly. It answers a different question. [[the-unjoined-end]]

    UNKNOWN when the witness ledger cannot be read, never 0. [[unknown-stays-unknown]]
    """
    def _ledger():
        return os.environ.get("TV_VAULT_LEDGER") or os.path.join(HERE, "vault_accum.json")

    def left():
        import vault_evidence as ve
        got = ve.tier_census(_ledger())
        if not got.get("ok"):
            return None
        return int(got.get("proven") or 0) + int(got.get("hardened") or 0)

    def right():
        import vault_retro as vr
        import vault_evidence as ve
        got = ve.tier_census(_ledger())
        names = got.get("provenNames") if got.get("ok") else None
        if not isinstance(names, list):
            return None
        try:
            with io.open(_ledger(), encoding="utf-8") as fh:
                doc = json.load(fh)
        except Exception:
            return None
        rows = doc.get("owned") if isinstance(doc, dict) else None
        if not isinstance(rows, list):
            return None
        piles = {}
        for row in rows:
            if not isinstance(row, dict) or not str(row.get("name") or "").strip():
                continue
            looks = row.get("witnesses") if "witnesses" in row else row.get("looks")
            if not isinstance(looks, list):
                continue
            piles.setdefault(str(row["name"]).strip(), []).extend(
                x for x in looks if isinstance(x, dict))
        # per item: each of the tier table's PROVEN+ names, asked of the gate by name
        return sum(1 for name in names
                   if vr.gate(piles.get(name, [])).get("looksSeen", 0) >= ve.TRIALS_PROVEN)

    return ("a-tier-stands-on-its-looks",
            "every item the tier table files PROVEN or HARDENED has at least TRIALS_PROVEN looks "
            "the live gate counts",
            "count witness ROWS as trials in vault_evidence._measure — one stash screen held still "
            "for 103 frames reads HARDENED while vault_retro.gate counts 2 looks (Radiance, "
            "2026-09-28)",
            "tier table: PROVEN+ items", left,
            "of those, items the live gate sees TRIALS_PROVEN+ looks for", right, "==")


def _inv_a_reset_hold_is_not_a_register_prompt():
    """#41 rank 1 (2026-09-29) — A ROW HIS RESET HELD IS NEVER TURNED INTO A "PRESS REGISTER" PROMPT.

    One vault, three admission bars, nothing pairing them: Wilson 0.722 over 10 visits (the reset's
    rebuild), 2 looks at the normal door, 1 look for a keepFiled retro row. The heart's own 'vault
    provenance' row (arm 3) told him to press register for stash rows that cleared the 2-look gate —
    11 of the 13 on his real ledger were rows the reset's plan had just HELD, so the advice would undo
    the hold. Since #41 the doctor reports a reset-held row beside, never as a gap; this joint keeps
    that true against a record the doctor does not read.

    THE TWO SIDES:
      LEFT   names the last full reset's receipt says its plan HELD, as the BACKUP LANE snapshotted
             them on disk (ledger_*.json allStores.d2r_vaultLastReset.heldNames), that arm 3's own
             row filter (console_doctor.arm3_row_class, with the live 2-look gate) classes 'reset-held'
             over the witness ledger — against the SNAPSHOT's mule map and lane locks
      RIGHT  of the stash rows the doctor judged, the ones its verdict counted as
             gatePassingResetHeld — off the LIVE board read (console_doctor._vault_provenance_counts)
    Independent by RECORD: the left reads the backup lane's snapshot on disk; the right is the doctor's
    own verdict over the live board. `==`, per name count: a reset-held row the gate passes that the
    doctor did not report as held is a row it prompted him to register.

    ⚠ round-5 review (MED, reproduced) — THE TWO SIDES ASKED TWO FILTERS. The first cut counted on the
    left every held stash row the gate passes, while the doctor reaches its held bucket only after arm
    3's pre-filters (an ITEM row, not filed under its canonical name, worth registering, not locked,
    routable) — so a held Sunder charm (shared stash: no mule), a rune tally row or a locked name was
    counted left and skipped right: DISAGREE over a healthy board (left 3, right 1). Both sides now ask
    the ONE predicate; what stays independent is the record each hands it. [[the-obvious-fix-cried-wolf]]

    UNKNOWN when no backup carries a receipt, the ledger cannot be read, or the console did not
    answer — never 0. A backup older than the live board's reset reads as a disagreement, which is
    the honest state until the backup lane catches up. [[unknown-stays-unknown]]
    """
    def _ledger():
        return os.environ.get("TV_VAULT_LEDGER") or os.path.join(HERE, "vault_accum.json")

    def _newest_backup():
        import glob as _g
        d = os.environ.get("TV_LEDGER_BACKUP_DIR") or os.path.join(os.path.expanduser("~"), "d2r_ledger_backups")
        try:
            files = sorted(_g.glob(os.path.join(d, "ledger_*.json")))
        except Exception:
            return None
        return files[-1] if files else None

    def left():
        import vault_retro as vr
        p = _newest_backup()
        if not p:
            return None
        try:
            with io.open(p, encoding="utf-8") as fh:
                snap = json.load(fh)
        except Exception:
            return None
        stores = snap.get("allStores") if isinstance(snap, dict) else None
        if not isinstance(stores, dict):
            return None
        raw = stores.get("d2r_vaultLastReset")
        try:
            rec = raw if isinstance(raw, dict) else (json.loads(raw) if isinstance(raw, str) else None)
        except Exception:
            return None
        if not isinstance(rec, dict) or rec.get("door") != "vaultClearHistory":
            return None
        held = {str(n): "held by the reset the backup snapshotted" for n in (rec.get("heldNames") or []) if n}

        def _store(key, dflt):
            raw = stores.get(key)
            try:
                v = raw if isinstance(raw, (dict, list)) else (json.loads(raw) if isinstance(raw, str) else dflt)
            except Exception:
                return None
            return v if isinstance(v, dict) else None
        assign, lane_lock = _store("d2r_muleAssign", {}), _store("d2r_laneLock", {})
        if assign is None or lane_lock is None:
            return None
        try:
            with io.open(_ledger(), encoding="utf-8") as fh:
                doc = json.load(fh)
        except Exception:
            return None
        rows = (doc.get("result") or {}).get("owned") if isinstance(doc.get("result"), dict) else doc.get("owned")
        if not isinstance(rows, list):
            return None
        import console_doctor as cd
        locked_fn, route_fn, gate_fn = cd._arm3_defaults(lane_lock, gate_fn=lambda ev: vr.gate(ev))
        n = 0
        for r in rows:
            if cd.arm3_row_class(r, assign, route_fn, locked_fn, gate_fn, held) == "reset-held":
                n += 1
        return n

    def right():
        import console_doctor as cd
        st, why, counts = cd._vault_provenance_counts()
        if not isinstance(counts, dict):
            return None
        v = counts.get("gatePassingResetHeld")
        return int(v) if isinstance(v, int) else None

    return ("a-reset-hold-is-not-a-register-prompt",
            "every stash row the last full reset's plan held that clears the 2-look gate is reported by the "
            "doctor as held by that reset, never as a row to press register for",
            "drop the `nm in held_by_reset` continue in console_doctor.vault_provenance_verdict, so a reset-held "
            "row counts as gate-passing-unfiled again — the doctor's held count falls to 0 while the backup's "
            "receipt still names them",
            "backup lane: reset-held names the live gate passes unfiled", left,
            "the doctor's verdict: gate-passing rows counted as reset-held", right, "==")


def _inv_their_tooltip_rows_are_ours():
    """#41 rank 16 (REG-1560, 2026-09-30) — THEIR PLANNER'S TOOLTIP ROWS AGAINST OURS, FROM THE LANE'S RECEIPT.

    The character builder's tooltip had ONE independent engine - their planner's in-game tooltip, measured on
    headless Chrome and frozen as text (tv/the_tooltip_oracle.json: 203 rows over 6 runewords) - and it was
    compared only by a gate, at push time, in node. Nothing on his console asked, unattended, whether the shipped
    composition was still theirs. The tvd-tooltip-oracle lane now runs the composition over every oracle row on
    its own cadence and receipts a verdict PER ROW; this joint compares the two counts.

    THE TWO SIDES:
      LEFT   rows the oracle holds - THEIRS, counted straight off the fixture file (every runeword's `bases`),
             never through the lane's reader, so a reader that drops a row cannot move both sides
      RIGHT  of the rows in the lane's receipt, those measured as OURS (agree is True) - and ONLY when the receipt
             is FRESH for the bible.html on disk (same sha1) and carries rows, not a summary
    Independent by ENGINE: the left is their planner's text; the right is our composition, run by node and
    receipted by the lane. The relation is `==`: every one of their rows is ours.

    ⚠ UNKNOWN (None), never 0, when there is no receipt, when the receipt says `node absent` (a PC without node),
    when it carries a summary in place of rows, or when bible.html has moved since it was measured - an old
    agreement is not today's. [[stale-reading]] [[unknown-stays-unknown]]
    ⚠ THE LIMIT: 203 rows over SIX runewords, one class, one level. A green here vouches for those rows and
    nothing beyond them.
    """
    def left():
        with io.open(os.path.join(HERE, "the_tooltip_oracle.json"), encoding="utf-8") as fh:
            fx = json.load(fh)
        rw = fx.get("runewords") if isinstance(fx, dict) else None
        if not isinstance(rw, dict) or not rw:
            return None
        n = 0
        for v in rw.values():
            b = v.get("bases") if isinstance(v, dict) else None
            if not isinstance(b, dict):
                return None
            n += len(b)
        # an oracle with no rows is not a measurement of theirs: UNKNOWN, not a zero to agree with
        return n or None

    def right():
        import tooltip_oracle_lane as tol
        rec, _why = tol.read_receipt()
        if rec is None:
            return None
        rows = rec.get("rows")
        if not isinstance(rows, list):
            return None                   # node absent, or a summary: nothing was judged per row
        fresh, _fwhy = tol.freshness(rec)
        if fresh is not True:
            return None                   # stale or undatable: an old agreement is not today's
        return sum(1 for r in rows if isinstance(r, dict) and r.get("agree") is True)

    return ("their-tooltip-rows-are-ours",
            "every row of their planner's tooltip oracle is composed line for line by the shipped tooltip on the "
            "bible.html on disk (203 rows over 6 runewords - the oracle's limit)",
            "delete `if (J.s > 0) L = _cbTipMerge(L, rolls);` in bible.html and let the lane re-measure "
            "(python3 tv/tooltip_oracle_lane.py --force): the receipt agrees on fewer rows than the oracle holds "
            "- or drop a base in tooltip_oracle_lane.oracle_rows() so a row never reaches the composition",
            "their oracle rows", left, "rows the lane's receipt measured as ours", right, "==")


def _inv_the_river_log_places_only_reels_the_shelf_has_or_a_deleter_recorded():
    """REG-1615 — THE RIVER'S STAMP LOG AGAINST THE SHELF ITSELF, AND AGAINST EVERY DELETER'S OWN RECORD.

    His fleet card read "river stuck" on every PC (2026-09-30), and on his Mac 21 of the 27 reels it counted were
    gone: the log kept each reel's last station for ever, because neither deleter (the retention pass, the
    recorder's disk floor) ever stamped it. Each engine was right by its own lights - the log about what it was
    told, the shelf about what is on disk, each deleter about what it removed - and nothing asked whether they
    AGREE. This does: a reel the log still places on the river whose folder is gone must be named by a deleter's own
    record (the triage tick then closes it out, river_stamp.close_out). A reel gone with NO record is a deletion
    nobody logged - a third deleter, or a folder removed by hand - and that is this invariant's red.
    Left: the log + the shelf + the deleters' records (river_stamp.close_out, DRY - this file never writes).
    Right: 0 allowed. An unreadable log, shelf or record is UNKNOWN, never 0."""

    def left():
        import river_stamp as _rs
        hist = os.environ.get("TV_HIST") or os.path.join(HERE, "frames", "hist")
        r = _rs.close_out("corroborate", hist, dry=True)
        if not r.get("ok") or r.get("unread"):
            return None
        return len(r.get("unrecorded") or [])

    def right():
        return 0

    return ("river-log-matches-the-shelf",
            "every reel the river's stamp log still places on the river is on the shelf, or a deleter's own record "
            "names its removal",
            "remove a reel's folder with no closure-ledger row and no reap-log row and this goes red naming it",
            "reels the stamp log places on the river, gone from the shelf, recorded by no deleter", left,
            "0 allowed", right, "==")


BUILDERS = (_inv_their_tooltip_rows_are_ours,
            _inv_a_reset_hold_is_not_a_register_prompt,
            _inv_a_tier_stands_on_the_looks_the_gate_counts,
            _inv_the_router_and_the_shelf_count_the_SAME_reels,
            _inv_a_tombstone_is_never_ahead_of_extraction,
            _inv_every_seed_the_authority_NAMES_has_a_door_that_can_REMOVE_it,
            _inv_a_posted_COUNT_and_its_own_MASK_agree,
            _inv_every_figure_pair_under_ONE_NAME_reads_ONE_STORE,
            _inv_no_world_reports_progress_it_INHERITED_from_the_owner_seed,
            _inv_every_backed_up_store_can_be_PUT_BACK_or_says_it_cannot,
            _inv_the_evidence_ledger_survived_the_sweep_that_filled_it,
            _inv_every_rung_the_shelf_declares_is_one_the_funnel_can_ACCOUNT_FOR,
            _inv_a_world_reporting_nothing_holds_nothing,
            _inv_only_a_declared_owner_world_posts_owner_numbers,
            _inv_every_door_counts_the_reels_it_opened,
            _inv_the_tooltip_finder_refuses_more_than_it_finds,
            _inv_the_console_and_the_law_agree_about_furniture,
            _inv_every_declared_tooltip_surface_is_served,
            _inv_vault_worklist,
            _inv_the_two_owned_fields,
            _inv_the_deleter_releases_only_what_the_store_declares,
            _inv_the_fleet_divides_by_the_same_number_the_board_does,
            _inv_the_eagle_can_still_look,
            _inv_hunt_memory_is_being_used,
            _inv_a_lane_that_is_ON_has_either_worked_or_says_why_not,
            _inv_shadow_names_fit_the_universe,
            _inv_swept_memory_matches_the_disk,
            _inv_a_stored_reach_still_matches_git,
            _inv_chronicle_owed_agrees,
            _inv_shadow_switch_matches_the_watcher,
            _inv_the_two_deleters_stay_at_their_own_granularity,
            _inv_the_two_readers_measure_the_same_screen,
            _inv_the_river_log_places_only_reels_the_shelf_has_or_a_deleter_recorded)



# ══ THE COVERAGE MAP — EVERY ENGINE IS NAMED, AND AN UNCOVERED ONE SAYS SO ═══════════════════════
# Konyo: "make it reach them all". The eagle's checks and this file's invariants are NOT the same
# unit — a check asks "is this engine well", an invariant asks "do these two agree" — so there is no
# 1:1 mapping to reach. What there IS: every engine the eagle knows must appear here, and one with
# no invariant must be VISIBLE rather than silently absent.
#
# That is the anti-silence principle turned on this file itself. Without it "4 of 11 joints" is a
# fact nobody can see, which is precisely the defect a corroborator exists to catch.
COVERED_BY = {
    # ⚠⚠ v3017 — THE BACKFILL. 36 of 59 doctor checks carried no entry in EITHER registry, so
    # "covered by a joint" and "nobody has looked" were indistinguishable for more than half the
    # roster. Each entry below was classified by reading the check's implementation and every
    # candidate builder, then every COVERED claim was put to an adversarial pass told to REFUTE it.
    # That pass killed one of the two: 'readers agree' was claimed covered and refuted, because the
    # joint reads the same two calibration constants the check already reads. One survived.
    'shadow watch': ('shadow-armed-is-watching',),
    "reel extract":      ("chronicle-owed", "swept-split-adds-up"),
    # v3313 (#63) — BOTH HALVES OF THAT CHECK ARE ALREADY JOINTED, which is why this is a
    # COVERED_BY rather than a NO_JOINT_YET. `router-and-shelf-agree` pins the DENOMINATOR (the
    # reel universe, counted independently by reel_router and reel_story), and
    # `swept-split-adds-up` pins the SUM (onDisk + retained against the sweep memory), which is
    # the check's own stated red condition: "THE RED CONDITION IS THE SUM, not the number".
    # ⚠ WHAT IT DOES NOT COVER, stated so the claim cannot over-reach: neither joint grades the
    # RETENTION TAG VOCABULARY — a tag this console cannot name would still pass both.
    "reel population":   ("router-and-shelf-agree", "swept-split-adds-up"),
    "sweep would find":  ("vault-worklist",),
    "shadow gate":       ("shadow-sample-fits",),
    "vault stores":      ("owned-is-contained",),
    "ledger entries":    ("owned-is-contained",),
    "hunt economy":      ("hunt-remembers",),
    "engines corroborate": ("eagle-ran-every-check",),
    # ⚠⚠ v3017 — "reel rungs" REMOVED: it never named a real doctor check. Measured, not argued —
    # `git log --oneline --all -S "reel rungs"` returns exactly ONE commit repo-wide (e8ba02ac,
    # v2725), and console_doctor.py is NOT in that commit's file list. It added the builder to
    # BUILDERS and the key to COVERED_BY in one hop and never added the matching eagle row, so this
    # entry has claimed coverage for a check that has never existed. Not a rename and not a
    # removal — a key born pointing at nothing. NO COVERAGE IS LOST by deleting it: the builder
    # `every-rung-is-accounted-for` is registered and still runs; only the false claim goes.
    # [[label-outlived-referent]] [[the-unjoined-end]]
    # v2730 — his "so its all not in the dark". 310 names of testimony had NO joint of any kind.
    "evidence ledger":   ("evidence-survived-its-sweep",),
    # 2026-09-28 (Ledger P0) — moved out of NO_JOINT_YET. The row's tiers are now checked against
    # the live gate's own look count, the engine that owns the independence law. What it does NOT
    # cover, said so the claim cannot over-reach: the broken-picture half of the row (cited frames
    # gone from the shelf) has no second source yet.
    "evidence tiers":    ("a-tier-stands-on-its-looks",),
    # #41 rank 16 (REG-1560) — the doctor row reads the lane's per-row receipt; the joint compares that receipt
    # (ours, fresh for the page on disk) against the oracle file (theirs). What it does NOT cover, said so the
    # claim cannot over-reach: any runeword, class or level the 6-runeword oracle never held.
    "their tooltip rows": ("their-tooltip-rows-are-ours",),
}
# Engines with NO invariant, each with the reason — a blank here would read as covered.
NO_JOINT_YET = {
    # #208 (v3905) - the reel upload lane: one source today, said so rather than claimed covered.
    "shadow reels reach the bucket":
        "the row reads the reel lane's own receipt (.shadow_reels_state.json: worked, owed, its last words) - one witness. "
        "An independent second source is the site's own reel index for this PC (/api/roster?reels=), whose sessions should "
        "hold every one the lane says it sent; no joint compares them yet.",
    # REG-3761 (v3901) - the rolling reel's footage: one source today, said so rather than claimed covered.
    "rolling reel filmed":
        "the row reads the recorder's own footage state (tv_diablo's health: footagePause and footageRefused) - one "
        "witness. An independent second source would be the rolling reel's frame files on disk (the newest f_<ms>.jpg's "
        "age against the pause the recorder says) or the shadow watch's rolling-reel record; no joint compares them yet.",
    # REG-3208/3209 (v3865) - the disk growers lane: one source today, said so rather than claimed covered.
    "disk growers":
        "the row reads the growers lane's own pass record (tv/disk_growers.py: measured, salvaged, read back, pruned) - "
        "one witness. An independent second source would be the disk's own free-space reading rising by the bytes the "
        "lane says it pruned, and the salvage dir's manifest re-read apart from the lane; no joint compares them yet.",
    # REG-3213 (v3865) - this version's CI: one source today, said so rather than claimed covered.
    "this version's CI":
        "the row reads what the console's CI tick recorded from GitHub's public Actions API (tv/ci_watch.py) - one "
        "witness. An independent second source would be tv/ship_when_green.py's own Publish watch on the same commit, "
        "or the fan-in's prove_seconds per shard, and no joint compares either with the tick yet.",
    # REG-3218 (v3865) - the task board against the tree: one source today, said so rather than claimed covered.
    'the board agrees with the tree':
        "the row reads the board lane's own record, which tv/task_truth.py derived from git and the #230/#231 looks - one "
        "witness. An independent second source would be the published board (/api/roster?tasks=1) read back from the site "
        "and its phases compared with the lane's, which nothing reads yet.",
    # v3856 - windowed lobby frames: one source today, said so rather than claimed covered.
    'a windowed frame is read inside its game':
        "the row measures a synthetic windowed frame through char_select's own game_box and lobby bands - the reader "
        "grading itself. An independent second source would be his real windowed reels: per-size matched counts in "
        "lobbyBySize rising above 0 for the 800-wide family once a console runs this; no joint reads that yet.",
    # v3854 - the D2JSP Advanced door onto the price database. CI caught it in neither registry.
    'the d2jsp price database is on its tab':
        "the row reads bible.html and control_app.py for the Advanced door and the quote's fold, then grades "
        "d2jsp_price_db on a seeded fixture - the source and the module it imports, one witness. A real second "
        "source would be the rendered D2JSP tab showing the same Wilson score the quote returned, which is not built.",
    # #85 (REG-3269) - the Quick wins grid's pictures.
    'quick wins places have their pictures':
        "the row reads the page's picture map and the files in art/ - the page and the disk, one witness of whether a "
        "file exists. A real second source would be the rendered tiles reporting a loaded image each, which only "
        "render_check's quick-wins target sees (imgs broken 0 of 602), never the console.",
    # #87 (REG-3253) - the Mac's own d2jsp window.
    'the Mac signs in to d2jsp through its own window':
        "the row asks the lamp's opener for its command and reads the console's own d2jsp profile settings - the "
        "code and the file it writes, one witness. A real second source would be d2jsp itself answering a read sent "
        "with that profile's cookie, which only a live price read does (and that never runs during checks).",
    # #36 (REG-2909) - one reader names the character on every screen it reads.
    'which character each session is on':
        "the row reads char_select's ledger: character select, the lobby and the C panel are all read by the console's "
        "one vision reader, so three screens agreeing are one witness, not a joint (two that disagree already make the "
        "span UNKNOWN). A real second source would be the save file (.d2s) of the character he played that session, "
        "which nothing reads per session yet.",
    # #151 (v3551) — his reader switch: one source today, said so rather than claimed covered.
    'reader switch':
        "the row reads the switch file and the Grok CLI's login through g5_grok_eyes - the same module that decides who "
        "reads. An independent second source would be the reads themselves: the journal rows' own model stamps (at "
        "GROK ONLY none may carry a Claude model after the switch was set) - no joint walks the journal against the "
        "switch yet.",
    # #54 (v3526 integration) — the equipped lane's own row: one source today, said so rather than claimed covered.
    'picker census':
        "the row reads each PC's own page counting its picker's list function against its own type table - two halves "
        "of ONE page's count, handed over by that page. An independent second source would be the picker actually "
        "opened on that PC (a pixel count of its Base Items rows on film) - no such joint yet (REG-1584).",
    'equipped ledger files every seal':
        "the row reads equipped_ledger.contract() — the lane's own store against the journal ring the same console "
        "writes, so a lane that files and a row that checks it read one writer's two halves. An independent second "
        "source would be the reel's own frames (a worn-item panel seen on film) or the vault's witness ledger naming "
        "the same character's gear; no joint walks either against the equipped ledger yet.",
    # 2026-09-28 — the owned door's heart rows. Each is one source today, said so rather than claimed covered.
    'a vault item with no provenance':
        "the row compares the board's owned list against its own d2r_vaultProv store — two stores written by the "
        "same board through one door (window._ownedAdd), so they are one writer describing itself. An independent "
        "second source would be the reader's own ledger (d2r_chronicleInboxLog) or the console's session journal "
        "naming the read that filed each item; no joint walks either against the owned list yet.",
    'a read left no picture':
        "the row joins the reader's journal (which reads named things) against the frame shelf on disk and the "
        "recorder's own reap and refusal records — the journal and the shelf are written by the same recorder "
        "process. A genuinely independent side would be the vision lane's own receipt of the frame it was handed "
        "(its size and hash at read time) compared with the file on disk; nothing records that receipt yet.",
    # 2026-09-29 (#55) — the reel custody row. It DOES compare two writers per reel (the deleter's tombstone
    # sentence against the two sweeps' seal stores; the ledger against the shelf; a stamp against the ledger)
    # and publishes each contradiction with both sides — but no corroborate JOINT is registered for it yet,
    # said so rather than claimed. The joint would be `tombstone-claims-its-seals` (left: tombstones whose
    # `why` says "sealed by BOTH lanes", right: those whose session the seal stores actually hold); MEASURED
    # 2026-09-29 it reads 460 against 44 on his tree, because reel_retention writes one sentence for every
    # door (end_routes.derived_from counts the same thing as labelContradictions). Registering that as an
    # invariant before the deleter's sentence names its door would put a permanently red joint on the heart
    # for a known cause, which is furniture. The row carries the finding until then.
    'reel custody':
        "the row joins five stores (reel_tombstones, vault_swept, chronicle_swept, retro_triage, river_stamp, plus "
        "the recorder's reap/refusal records) written by five different lanes, and names every reel on which two "
        "of them contradict each other. No corroborate joint yet: the natural one (tombstones claiming both seals "
        "vs. sessions the seal stores hold) is red on every console for a known cause — the deleter writes one "
        "sentence for every door — and would be furniture until reel_retention's tombstone names its door.",
    # 2026-09-28 — Grok's #246 heart rows (§27) shipped without a registry line; test_every_doctor_check_is_explained
    # went red on CI. Both were one source, said so rather than claimed covered. 'evidence tiers'
    # got its joint on 2026-09-28 (a-tier-stands-on-its-looks) and moved to COVERED_BY.
    'vault reset receipt':
        "the row reads the receipt the reset runner PERSISTS (d2r_vaultLastReset, #41 rank 2 — before that it read nothing: "
        "registered with no arguments, it was UNKNOWN for ever): cleared / kept / touched / unknown / refused, with the "
        "runner's own digest of every kept store before the clears and after the rebuild — one writer describing its own "
        "act. An independent second source would be a ledger backup taken just before the reset diffed against the store "
        "after it; the backup lane holds those snapshots but no joint reads them against a receipt yet.",
    # 2026-09-28 — the triage starvation row.
    'triage starved':
        "the row pairs two things the serving console publishes on /api/river — reel_router's TRIAGE "
        "count (the printer's evidence) and the triage lane's record of its last walk and refusals — "
        "but the second is the lane describing itself (its last walk is seeded from retro_triage.json, "
        "the lane's own store). A genuinely independent witness would be retro_triage.owed() recounted "
        "from the reel directories on disk against a walk observed from outside the lane, and no "
        "registered builder takes that walk yet.",
    # 2026-09-29 (#58, Ledger 3.0 first slice) — the per-session extraction record row.
    'ledger3 sessions':
        "the row draws each shelf reel's extraction record through control_app._ledger3_stores — the journal "
        "ring (the live reader's own rows), the chronicle book and the vault witness ledger — and prints the "
        "reader-against-vault agreement side by side, which IS two engines (the live deep reader writes the "
        "journal; vault_retro's sweep writes the witnesses). But that comparison lives on the row and is not "
        "a registered corroborate BUILDER yet, and the row's red condition (a sealed reel on the shelf with no "
        "journal rows) is one source — the shelf listed against the ring. The joint would be ledger3.census "
        "recounted against reel_index's own per-reel row list by a builder that runs; none does yet.",
    # 2026-09-27 — the drain row.
    'retention drain':
        "the row reads the drain contract the serving console publishes from TWO of its own records "
        "(the per-pass disk_history series for owed/released, the tombstone ledger for worked); a "
        "genuinely independent second source would be the reel directories counted fresh on disk "
        "against the pass that planned them, and every reader that could count them asks the same "
        "reel_retention.plan() — a joint over it would be one number wearing two names.",
    # #227
    # #105
    "this machine's reader can read":
        "the row reads the reader's OWN journal rows (did its newest read return) through control_app._reader_health, "
        "which also paints the lamps - one source. The independent second source is an actual probe call answering "
        "(the one a sign-in check would make); no joint spends that call yet.",
    'this machine can decode a frame':
        "the row round-trips a BMP through Pillow in memory; a second source would be a real frame this machine filmed decoding in the reader, which only happens when it films.",
    # REG-1719
    'this machine can cross-check an inventory':
        "the row imports numpy and takes one median in memory; the independent side would be the vault's grid measure answering on a real frame this machine filmed, which only happens when an inventory is on screen.",
    # #228
    'a fresh remaining page':
        "the row reads the calibration the last chronicle sweep SAVED (his board's count against the game's Remaining page); the independent side would be a newly filmed Remaining page, which is exactly what the row asks him for - until one exists there is no second source to join.",
    # v3475
    'the seed was checked against his board':
        'the row reads the baker\'s receipt; the independent side would be his board read live, '
        'which only the baker can open (his WebKit store) and the row must never re-run.',
    # v3468 (#208) — THE 23 ROWS EXPLAINED NOWHERE. test_every_doctor_check_is_explained has been red
    # on CI for as long as the agent-tests workflow has been read (#123), because these were in
    # neither registry — so 'a joint corroborates this' and 'nobody ever classified it' were the same
    # state. Each now says what it reads and what a genuinely INDEPENDENT second source would be.
    # Five are ITSELF two-sided; for those a corroborate.py joint re-reading the same two fields
    # would be one number wearing two names (precedent: v3389). Declared, not claimed.
    'sweep attack reaches its door':
        'the row drives one stubbed call at the real sweep door and grades the harness that scores it; a second source would be a live sweep reaching that door under a real attack, which only happens inside heart2 --prove sandboxes.',
    'no git child steals his screen':
        "the row counts git argv sites in SOURCE; a second source would be the Windows box's live window census showing zero git.exe consoles over the game, which no target captures.",
    'this machine can get a second opinion':
        'the row asks whether THIS machine has a signed-in eye on disk; a second source would be a completed look taken FROM this machine, and ledger rows do not record which machine took them.',
    'the compare panel can name a difference':
        'the row calls /api/fleet and /api/fleet_compare and asks whether a column names anything; a second source would be the rendered panel on his real fleet, and render_check has no target with live peers.',
    'this console tree is established':
        "the row checks this machine's own tree exists and a write landed in it; the independent side is the writers' paths, which is its sibling row 'the door and the writers agree', not a corroborate.py joint.",
    'the door and the writers agree':
        "the row is ITSELF a two-sided comparison (machine_tree's footage paths vs tv_diablo's HIST_DIR/FRAMES); a separate invariant re-reading the same two paths would be one number wearing two names.",
    'the resume agrees with git':
        "the row is ITSELF a two-sided comparison (RESUME_HERE's derived block vs git now); a separate invariant over the same two reads would be the same number twice.",
    'the chip can say nobody looked':
        'the row asks the engine the heart chip reads whether it hands over a census; a second source would be the rendered chip on his console, which only its gate drives, in a fake DOM.',
    'the eye audit agrees with the gate':
        'the row is ITSELF a two-sided comparison (audit() vs owes_a_look() -> looked_at()); a separate invariant re-reading both would be one number wearing two names.',
    'the eye cap is a size it has finished':
        "the row reads the live ledger for looks that finished at the cap; a second source would be the CLI's own count of the bytes it received, which the CLI does not report.",
    'the eye answers in a field':
        'the row counts verdictFrom=schema on live ledger rows; a second source would be an independent re-read of the raw answers, which is not built.',
    'the eye seat can be filled':
        'the row probes whether the default transport answers at all; a second source would be a completed look through that transport, which proves reachability only after the fact.',
    'the hunt names a quicker route':
        'the row reads the SERVED file for the disclosure clause; a second source would be the rendered hunt card for a Hell-first piece, and render_check has no such target.',
    'the board build door is open':
        'the row asks the route table and the served route; a second source would be an outside caller (the GrokBot seat) reaching the door, which reaches this console only as #230 prose.',
    'this process runs the code on disk':
        "the row is ITSELF a two-sided comparison (the loaded code objects' first lines vs the AST on disk); a separate invariant over the same two would be the same number twice.",
    'nothing we started is a corpse':
        "the row reads the process table for our own subtree; a second source would be the kernel's accounting through a different tool, and re-reading ps would be the same number twice.",
    'our scratch is collected':
        'the row walks the scratch root by prefix; the independent side is the MINT — call sites registering what they create (#171) — which is not built.',
    'a verdict comes from a declared field':
        'the row checks the prompt asks for a declared verdict and answers carry it; a second source would be an independent re-judge of the same answers, which is not built.',
    'a queue zero came from a read that worked':
        "the row checks the drain reports a failed read apart from an empty one; a second source would be GitHub's own comment count for the lane set against the drain's, which no target captures.",
    'a hidden element is actually hidden':
        'the row scans the bytes ON THE WIRE while its gate scans the bytes on disk — the two sides exist, across the row and its gate, not as a corroborate.py joint.',
    'his window can be measured':
        "the row reads pywebview's live Window size; a second source would be the OS window server's frame for the same window, which is not wired.",
    'his window has a keyboard door':
        'the row checks the W shortcut is in the served bytes; a second source would be a synthetic key press observed to change the frame, which needs Accessibility (needs-hid).',
    'this machine keeps itself current':
        "the row reads this machine's own HEAD and pull cadence; a second source would be the fleet roster's record of this machine's version, which lives behind the console's KV read.",
    # #64 — filed IN THE SAME COMMIT as the row, which is this registry's whole rule.
    'this checkout can update':
        "a SELF-REPORT: the row reads the pull lane's own record of how its last attempt ended (/api/status pullLane). "
        "The independent second source exists — git's own count of HEAD..origin/main, which 'this machine keeps itself "
        "current' reads from the refs — and a lane saying 'pulled' while that count stays above zero is exactly the "
        "disagreement a joint would grade. That joint is not built yet.",
    # v3467 — the two rows THIS arc added (v3458, v3467) and never explained, so the explained-
    # exactly-once law grew 23 -> 25 on my ships. Declared, not claimed.
    'two eyes compared':
        'the row reads g5_shadow_reducer over the shadow log, which is ITSELF a two-family '
        'comparison; a second source for the ROW would be a different engine counting the same '
        'store, and one that re-read the same rows would be one number wearing two names.',
    'handoff lanes drained':
        'the row judges #230 by its watermark and #231 by the ledger drain, each by its own '
        'mechanism; a second source would be the seats\' own record of what they posted, which '
        'no target captures.',
    # v3386 (#129) — the row reads the ledger file and asks the ledger's own reader. A genuine
    # second source would be an independent re-judge actually RUNNING over the stored answers and
    # agreeing with the recorded verdict; that is the next version's work, and claiming it now
    # would claim the very thing this one only made possible.
    'a look keeps its evidence':
        'the row counts rows whose answer text survived and asks answer_for_rejudge; the second '
        'source would be an independent re-judge over those answers, which is not built yet.',
    # v3385 (#130) — the row reads the presence cache and greps control_ui for the helper. A
    # genuine second source would be the RENDERED rail: the two label strings a reader actually
    # sees for a shared nickname. No target captures that, so claiming coverage would claim the
    # very thing this version was written to make visible.
    # v3387 (#131) — the row reads the cached roster and the UI SOURCE. A genuine second
    # source would be the rendered rail line a person actually reads, or the site's own
    # /visits dashboard — and that is behind VISITS_KEY, which this console does not hold.
    # Claiming coverage would claim the very join this version exists to make visible.
    # v3390 (#135) — the two sides are the `console:` presence key and the `lastseen:` record:
    # different keys, written under different conditions. A separate corroborate.py invariant
    # over the same fact does not exist, and one that re-read the same payload would be the same
    # number twice.
    'a present machine has a fresh last-seen':
        'the row compares online membership (from the presence key) against the last-seen stamp; '
        'a second source would be the roster read straight from KV, which no target captures.',
    # #223 — the row reads ver / diskVer / relaunch.may from the presence cache. A genuine second source
    # is the machine itself (its boot log, over SSH), which no target captures; re-reading the same roster
    # would be one fact wearing two names.
    # #229 — the row asks Windows (schtasks) and the Startup folder; a second source would be a real
    # reboot of the machine, which no target performs.
    'this console starts at sign-in':
        'the row reads the scheduled task and the Startup folder; a second source would be a real reboot '
        'coming back on its own, which no target performs.',
    'no machine went quiet mid-restart':
        'the row reads the last beacon (running build, build on disk, restart allowed) from the presence '
        'cache; a second source would be the silent machine\'s own boot log, which no target captures.',
    # v3389 (#133) — ⚠ THIS ROW IS ITSELF A TWO-SIDED COMPARISON: the tally's outer claim
    # against ledger_authority's nested verdict, written by different engines. What it still
    # lacks is a SEPARATE corroborate.py invariant over the same fact, and inventing one that
    # re-read the same two fields would be one number wearing two names. Declared, not claimed.
    'a tally agrees with its own ledger verdict':
        'the row compares a tally headline against the ledgerVerdict inside the same object; a '
        'second source would be the board store read independently of the beacon, which no '
        'target captures.',
    # v3388 (#134) — the row parses the SHIPPED pathspec and asks git what one version changed.
    # A genuine second source would be the eye's own account of what it could not see — which is
    # exactly what failed here, since an excluded file is never reported missing. Claiming that
    # as corroboration would cite the broken witness.
    'the eye asks for every code extension':
        'the row parses the extensions out of second_eye_run.py and diffs them against the last '
        'looked version\'s changed files; the second source would be the eye\'s own omitted-file '
        'report, which cannot see a file the pathspec excluded.',
    'a presence reading names its door':
        'the row asks whether the cached roster carries a webAt half and whether control_ui '
        'renders the joined phrase; the second source would be the RENDERED rail age, or '
        '/visits, which is key-gated and unreadable from here.',
    'a fleet row identifies its machine':
        'the row counts shared nicknames in the cached roster and checks the UI carries the '
        'disambiguator; the second source would be the RENDERED rail labels, which no target '
        'captures yet.',
    # v3384 (#128) — the row reads the PRESENCE CACHE and the capability helper. A genuine
    # second source would be the RENDERED panel: the sentence a reader actually sees under
    # "they have - you do not" for a peer below the bar. That is not built here, and claiming
    # coverage would claim the very join this version was written to make.
    'a fleet refusal names an action':
        'the row reads the cached roster and asks the capability helper; the second source would '
        'be the RENDERED refusal on the panel, which no target captures yet.',
    # #95 (REG-2514) — NO_JOINT_YET, not COVERED_BY: there is no joint id to cite. The row compares
    # this PC's own key file with the key id the fetched roster names for its owner, but both other
    # inputs (the publish receipt and the roster cache) are answers from ONE server. The signers'
    # own corroboration (cryptography against the RFC 8032 signer) runs inside roster_sign, per
    # signature, and reaches this row as the receipt's `agree`.
    'every roster publish is signed':
        "the row reads this PC's publish receipt and its fetched roster cache, both the site's own "
        "answers, against the public half of this PC's key; an independent second witness would be "
        "a read of the KV store itself (rosterkey:<owner>) from the Mac, which nothing runs yet.",
    # v3358 (#99) — the row reads the ASSEMBLY ORDER out of control_ui.html. The real joint is a
    # RENDERED one: the first reel card's top against the viewport height at his real 1120x660,
    # which is the measurement that actually caught this (708px in a 660px window). It is NOT
    # built — the render target that watches this grid proves cards ARRIVE and never that one is
    # above the fold — so claiming coverage here would be claiming the very thing that was missing.
    'shelf order and guard': 'the row reads source order and the presence of the scroll guard; the second source would be RENDERED '
                              'geometry - first card top against viewport height at 1120x660 - '
                              'and that is not built. The render target proves arrival, not '
                              'position, which is how this survived 68 versions.',
    # ⚠⚠ v3357 (#111) — `swallowed reads` LANDED IN NEITHER REGISTRY AND CI CAUGHT IT, not the
    # push. v3355 added the row and registered it in CHECKS, the surface map and the MINE map —
    # three places — and missed this pair, so `test_every_doctor_check_is_explained` went red on
    # the runner the same hour. It never ran locally because the pre-push derives its gates from
    # CHANGED TEST FILES and v3355 changed console_doctor.py, not that law. A sample is not a
    # verdict. [[regression-guard]] §1
    # ⚠ HERE AND NOT COVERED_BY, for the #95 reason: I have no joint to cite. The row recounts
    # rank 1 from the AST and compares it to a baseline file — one source read twice, which is a
    # ratchet rather than a corroboration. A REAL JOINT IS AVAILABLE AND UNBUILT: the census's own
    # per-file breakdown against a second walker that asks the same question from the exception
    # side would be two genuinely independent counts. That is heart-first work, not a registry
    # edit, and claiming coverage I cannot back is what this registry exists to prevent.
    'swallowed reads': 'the row recounts rank 1 from the AST and compares it to a baseline file, '
                       'which is one source read twice - a ratchet, not a second witness. A '
                       'second independent walker counting from the exception side would be a '
                       'real joint and is not built.',
    # v3340 (#95) — `reel clocks` asks whether every reel on disk can still yield an epoch from
    # its id, which is the precondition v3333's card fix rests on. It sits HERE and not in
    # COVERED_BY because I have no joint to cite: nothing pairs it with a second independent
    # source today, and test_every_covered_claim_cites_a_joint_that_actually_runs would rightly
    # refuse a coverage claim I cannot back. The gate test_session_card_has_a_clock pins the CODE;
    # this row watches the DATA; neither corroborates the other.
    # ⚠ A REAL JOINT IS AVAILABLE AND UNBUILT: the console's own session list and the reel ids on
    # disk are two genuinely independent sources for the same question. Building it would move
    # this row to COVERED_BY honestly, and that is heart-first work rather than a registry edit.
    'reel clocks': 'no second source is paired with it yet; the gate pins the code and this row '
                   'watches the data, so neither corroborates the other. The console session list '
                   'versus the reel ids on disk would be a real joint and is not built.',
    # v3310 (#56) — the second-eye ledger is the ONLY record of what an eye said. There is no
    # second witness to corroborate it against: the eye's reply exists nowhere else, and the
    # models are not asked to sign their answers. What this check DOES do is compare two looks at
    # ONE payload against each other, which is a self-consistency test rather than a joint — and
    # saying so beats leaving it unexplained, which is indistinguishable from forgotten.
    # v3363 (#114) — NO_JOINT_YET and not COVERED_BY, for the #95 reason: there is no second
    # source to cite. The only other witness to how much of a file an eye saw is the EYE's own
    # prose REACH line, and that was measured at 5.2% of 854 answered rows with 16 of 44
    # unparsable — too thin to corroborate anything. Claiming coverage here would be claiming
    # the very thing that is missing.
    # v3364 (#60) — NO_JOINT_YET, not COVERED_BY, for the #95 reason: the second witness
    # would be the GAME's own composed name as the reader saw it on a tooltip, and the
    # reader gives a NAME, never a decomposition — so there is nothing to compare the
    # parse against. ⚠ AND THE OBVIOUS SECOND SOURCE IS A FAKE ONE: the root and base\\
    # copies of rareprefix/raresuffix are BYTE-IDENTICAL (sha256, measured), so citing
    # them as two witnesses for the rare half is n inflated by repetition.
    # v3365 (#24) — NO_JOINT_YET, not COVERED_BY: the second witness would be a RENDERED
    # capture of the stage at the instant it went blank, and nothing captures on that
    # trigger. The render targets prove a page CAN paint, never that it did at 12s.
    # v3366 (#115) — NO_JOINT_YET, not COVERED_BY. The second witness would be the SEAT
    # saying where it just wrote; it posts prose to a queue and names no path, so there is
    # nothing machine-readable to compare the chosen root against. Claiming coverage here
    # would be claiming exactly what is missing.
    # v3368 (#60) — NO_JOINT_YET, not COVERED_BY. The second witness would be the FRAME
    # itself re-read for sockets, which costs a paid look and is exactly the cost this
    # version exists to avoid paying twice. Claiming coverage would claim the thing missing.
    # v3378 (#28) - NO_JOINT_YET, not COVERED_BY, for the #95 reason. The row DOES compare two
    # readings - the printer's own station and the routed row - but they are not two engines:
    # `_evidence` is DOWNSTREAM of `printer.stream()`, so the pair is honest about the WIRE and
    # is one source twice over for the verdict itself. A real second witness would be an
    # independent reading of the reel's names, which costs a paid look. Claiming coverage here
    # would claim exactly the thing that is missing. [[heart-first]] section 1
    # v3379 (#128) - NO_JOINT_YET, not COVERED_BY, for the #95 reason. The row compares the
    # banked TALLY against the banked STORES, and both were written by the same board on the
    # same beat - one witness in two files, not two witnesses. A real second source would be a
    # live board read, which is precisely the thing a windowless console cannot do and this
    # whole version exists to work around.
    # v3380 - NO_JOINT_YET, not COVERED_BY. The row reads ONE source: the text of tv/*.py.
    # A real second witness would be a runtime observation that a launcher left no child
    # behind, and nothing records that today.
    'a worker read has a deadline': 'the row reads one source, the text of tv/*.py; a real second witness would be a runtime observation that no caller ever waited past its deadline on a quiet worker, and nothing records that yet.',
    'no browser is launched unreaped': 'the row reads one source, the text of tv/*.py; a real second witness would be a runtime observation that a timed-out launcher left no surviving child, and nothing records that yet.',
    'fleet can name what it counts': 'the row compares the banked tally against the banked stores, both '
                          'written by the same board on the same beat; a real second source would be a '
                          'live board read, which the console this protects cannot perform.',
    'river owes what its engine says': 'the row compares the printed station against the routed row, which '
                          'is upstream and downstream of the one wire it watches rather than two engines; '
                          'a real second source would be an independent read of the reel names, and that '
                          'costs a paid look.',
    'item facts captured': 'the row counts sightings carrying the three facts against sightings read by this '
                          'prompt version; a real second source would be re-reading the frame, which costs '
                          'a paid look.',
    'capture root live': 'the row ages the newest capture in the root the watcher chose; a real second source '
                          'would be the seat declaring its own write path, which it does not do in any '
                          'machine-readable form.',
    'fault evidence': 'the row counts snapshots on console-reported fault rows; the real second source '
                          'would be a capture taken at the moment the stage went blank, and no capture is '
                          'triggered by that event.',
    # #174 v-B2 - NO_JOINT_YET, not COVERED_BY: the row re-derives ONE source (the install) through ONE generator.
    # tv/item_tables.json is a second generator over the same tables, and the law compares the two in CI (every
    # unique / set name on the same base code) - that catches a transform bug, but it is one install read twice,
    # not a second witness to what the game sums.
    # #174 v-B2 fix round - the same shape for the builder's CB_DB block: one install, one generator
    'builder item data': 'the row re-derives the CB_DB block from the install and compares it; a real second source '
                          'would be the game listing its own item database, which it never writes anywhere this '
                          'console can read. #41 rank 16 (2026-09-29) - AND THE BUILDER\'S OTHER LINKS ARE GATE-ONLY '
                          'BY DESIGN, said here so silence is not read as coverage: the picker (test_the_character_'
                          'builder_is_their_builder, the mule picker law), the tooltip composition and the art rule '
                          'have no runtime invariant or doctor row. The one independent engine is their planner\'s '
                          'tooltip oracle (tv/the_tooltip_oracle.json: 203 rows over 6 runewords, measured once and '
                          'frozen), compared by test_the_tooltip_is_the_games_tooltip in node - a gate, never a '
                          'joint this console runs unattended, because the shipped composition needs node over '
                          'bible.html and no lane writes a per-row verdict the eagle could read. A runtime joint '
                          'would need that lane and its receipt (the #41 plan).',
    # #41 rank 15 (2026-09-29) — NO_JOINT_YET, not COVERED_BY, the #174 v-B2 shape again: one install, one generator.
    'mule slot rules': 'the row re-derives the MULE_BASE_* blocks from the install through ONE generator '
                       '(tv/mule_slot_map.py) and compares them. The builder\'s CB_DB block is the same install through '
                       'a second generator, and test_the_mule_rules_and_the_builder_agree_on_hands_and_class compares '
                       'the two on hands and class for every base (a transform bug shows) - but one install read twice '
                       'is not a second witness to what the game wears where. A real second source would be the game '
                       'itself laying an item in a slot, which no read captures.',
    # #41 rank 12 (2026-09-29) — NO_JOINT_YET, not COVERED_BY: his hand is the only witness.
    'characters room': 'the row reads d2r_charBuilds and d2r_cbMain, which the 👤 room and the planner write from his '
                       'own presses and nothing else — no reader, reel or ledger names a build, so there is no second '
                       'source to pair them with. The one other fact it reads, the vault\'s MAIN (d2r_mainCharacter), '
                       'is his declaration in the lock panel: two declarations by the same hand are one witness, not '
                       'a joint. A real second source would be a .d2s of the build he says is his, read by the save '
                       'reader; nothing files a build from a save yet.',
    # #246 W7 — the row already JOINS two sides (the board's map and witness store against the console's
    # gated stash ledger and MAIN ledger), but no registered builder returns that pair as a joint yet.
    'vault provenance': 'the row compares the board mule map and its d2r_vaultProv witness rows against the '
                        'console gate verdicts on vault_accum and the MAIN ledger; a truly independent second '
                        'source would be the game listing what each mule holds, which it never writes anywhere '
                        'this console can read. (#41 rank 1: arm 3\'s reset-held subset alone has a joint — '
                        'a-reset-hold-is-not-a-register-prompt, against the backup lane\'s snapshot of the '
                        'reset receipt — which does not cover the other three arms.)',
    'character sheet data': 'the row re-derives the CHAR_PROPS block from the install and compares it; a real second '
                          'source would be the game reporting a character sheet itself (its own resistances and '
                          'totals), which it never writes anywhere this console can read.',
    'save reader tables': 'the row re-derives the item tables from the install and compares sourceHash; the '
                          'second source would be the game decoding a save itself, which it never reports.',
    'item vocabulary': 'the row re-derives the lexicon from the install and compares sourceHash; a real '
                          'second source would be the game reporting its own affix decomposition, which it '
                          'never does - and the base\\ table copies are byte-identical for the rare half, so '
                          'they are one witness, not two.',
    'verdict matches the answer': 'the check IS the corroboration - our parser verdict against the other family own stated words, two independent sources. It is scoped to the CURRENT parser generation on purpose: every older row is re-judgement debt already counted by verdict_provenance(), which reported 213 agree and 118 do not, and repeating that here would be one reader wearing two names.',
    'eye told what was stripped': 'the only record of what the transport removed is the transport\'s own '
                          'count, so a second side would have to re-run the same two strip functions over '
                          'the same diff - one engine derived twice, which heart-first rule 1 says is one '
                          'number wearing two names. The honest corroborator is the EYE saying it could not '
                          'see the note, and no look has been asked that question yet.',
    'eye reach per file': 'the row recounts the payload from git and compares it against the ledger field; a '
                          'genuine second source would be the eye OWN reported reach, measured at 5.2% of 854 '
                          'rows with 16 of 44 unparsable, which is too thin to be a witness.',
    'second eye asked twice': 'the ledger is the only record of what an eye said; two looks at one '
                              'payload check each other, which is self-consistency and not a '
                              'second witness',
    # v3304 (#55/#38) — the relaunch interlock's green light. It IS the corroboration, so a joint
    # would be the same question asked twice. Its two sides are already independent: our own
    # register (a relaunch is HELD) against control_app.nothing_in_flight() (something is ACTUALLY
    # in flight), which is computed from the sweep/mini/agent state and knows nothing about the
    # register. A river joint over that pair would resolve to the same two engines one level down
    # — precisely what this file's own self-audit refuses. ⚠ What it genuinely CANNOT be jointed
    # to is an independent witness that the relaunch HAPPENED: os.execv replaces the process, so
    # no reader on this side survives to confirm it. Saying so beats leaving it unexplained, which
    # is indistinguishable from forgotten. [[heart-first]] [[the-unjoined-end]]
    'relaunch green light': 'it IS the corroboration - the register against nothing_in_flight, '
                            'two engines that know nothing of each other; and execv leaves no '
                            'witness this process survives to read',
    # 2026-09-28 — the build that never landed on his ALT (v3520 beside v3521 for 2+ h). Like the
    # green light above, the row IS a corroboration: the RUNNING process's compiled stamp, read over
    # the wire, against the literal in the file on DISK — neither derivable from the other. A joint
    # over the fleet beacon's ver/diskVer would be the same two readings relayed by the same
    # process: one engine wearing two names, which this file's self-audit refuses. The cause it
    # names (his session / shadow close failed / relaunch refused) is the drift lane's own record,
    # a self-report, and is said to be one. [[heart-first]]
    'the running build is behind the disk':
        'it IS the corroboration - the running process own compiled stamp over /api/status against '
        'the disk file literal, two sources neither can derive; the fleet beacon ver/diskVer is the '
        'same pair relayed by the same process, so a joint over it would be one engine counted '
        'twice. The cause it names is the drift lane self-report, and is labelled as one.',
    # v3232 — `the shelf tabs are his stations` (v3204's station chips). It is NOT jointed, and
    # its own docstring is why: it "asks the RIVER, which is the same source the chips are built
    # from". Comparing a render against the data that built it is one engine checked against its
    # own label map, not two witnesses — exactly the bar this file sets three lines below, and
    # exactly the trap it warns about ("a joint whose id mentions shelf does not corroborate every
    # check with shelf in its name"). A second witness would have to date the tab row from outside
    # the river; none does yet. Saying so is the point — an unexplained check looks exactly like a
    # forgotten one, and this one WAS forgotten for a version. [[the-unjoined-end]]
    'the shelf tabs are his stations': 'the only source is the river the chips are built from',
    # v3247 — the vault ledger is the sole authority on which names carry a proof; nothing else
    # counts witnesses, so there is no second source to corroborate it against. Saying so beats
    # leaving it unexplained, which is indistinguishable from forgotten.
    'the vault can say what it proves': 'the vault ledger is the only counter of witnesses',
    # ⚠⚠ v3017 — the other 35. The bar for a joint is a GENUINELY INDEPENDENT second source, not a
    # name that sounds related: a joint whose id mentions "shelf" does not corroborate every check
    # with "shelf" in its name, and a module reading back its own output is one engine, not two.
    # Most of these are honestly unjointable — a self-report, a single census, a sole authority —
    # and saying so is the point. An unexplained check looks exactly like a forgotten one.
    # ⚠ v3185 — AND IT HAPPENED AGAIN, TO ME, EXACTLY AS v3131 DESCRIBES. `check_stash_bank`
    # shipped into console_doctor with the vault_bank reader and was never filed here, so for one
    # version "a joint covers this" and "nobody has ever looked" were indistinguishable for it —
    # 1 of 61 in NEITHER registry. The gate that caught it was itself red on CI at the time, which
    # is how it stayed unnoticed. File the entry IN THE SAME COMMIT as the check.
    'stash bank':
        "a SELF-REPORT, and unjointable by construction. vault_bank.state() is the ONE reader over "
        "the vault's own accumulation (the accum + seen stores) — it reads back the "
        "output of the sweep that wrote it, and this file's own bar says a module reading back its "
        "own output is one engine, not two. The chronicle ledger is a genuinely separate source "
        "but answers a different question (what the film SAW, not what the stash HOLDS), so "
        "pairing them would be a joint in name only. The honest second witness would be his own "
        "eyes on the stash, which is not a thing this console can call.",

    # ⚠ v3131 — ADDED WITH THE CHECK IT EXPLAINS, WHICH IS THE WHOLE POINT OF THIS REGISTRY.
    # I shipped `window runs the document on disk` into console_doctor.WATCHES and never filed it
    # here, so for one version it was indistinguishable from a check nobody had ever looked at —
    # 1 of 60 in NEITHER registry. The law caught it; the law was itself reported as "unrun".
    'window runs the document on disk':
        "a SELF-REPORT with no second witness available inside the console. The check asks the "
        "webview what document it is rendering and compares that to the file on disk — and every "
        "other version reading here (ver, liveVer, bibleVer, agentVer) describes a FILE, not the "
        "rendered DOCUMENT, so none of them can corroborate it. The render gate photographs a "
        "SANDBOX console rather than his, and Grok Bot photographs his real screen but is not a "
        "joint this doctor can call. Honestly unjointable until something else witnesses the live "
        "document; saying so is better than a joint that reads the same source twice.",
    'armed migration':
        "a source-level parse of one file; whether the gating flag is actually stamped on his board lives in WebKit localStorage this process does not own, and the check's own docstring says so",
    'backup loop':
        "the loop's own liveness and last act, read from the one place that records them; nothing else witnesses whether the backup loop ran",
    'behind the fleet':
        'both sides of the count come out of the one .git store, and a second witness of what origin holds would need the network fetch this row exists to avoid',
    'board join':
        'one live probe of one window; nothing else independently observes whether the board answers, and the board-flavoured joints compare its DATA, not its reachability',
    'console painted whole':
        'per-cell ink of the actual window pixels; no builder reads a screen capture, so there is no second instrument photographing the window to agree with',
    'end routes reachable':
        'the end-route report is the only reckoning of which exit doors would take a reel; route-not-ahead-of-extract watches the opposite fault and never asks whether a reel CAN reach a door',
    'extraction lanes':
        "each lane's freshness is its own ledger's clock; vault-lane-has-worked reads has-EVER-swept and stays green through a stall, and chronicle-owed grows on both sides during one",
    'fleet reachable':
        'it reads the exact cache the fleet card paints, ON PURPOSE by its own docstring, and the remote site is the only authority on its own reachability',
    'his gear':
        'the main-character ledger reads back its own accumulation; no second engine observes what he wears',
    'ledger backup':
        'it asserts a want-list is PRESENT in the newest backup; the one joint that reads that artifact watches the opposite drift — stores present that restore has never heard of',
    'ledger provenance':
        'the row is itself the two-sided comparison, board window against fleet wire; its verdict-bearing quantities are paired by no joint',
    'ledger staleness':
        "the drift half already pairs its own two sources internally, and no invariant anywhere measures a figure's AGE — freshness has no second engine to agree with",
    'names banked':
        'a stall in the LIVING river, before any close-out; route-not-ahead-of-extract fires only once a reel has been routed, so it cannot speak about names still waiting',
    'panels on screen':
        "the page classifies its own panels and the row reads that self-report — the same shape as 'console UI faults', with no second engine grading the same panels",
    'printer reach':
        'one reading of one store through one contract; nothing independently measures how much of the corpus the pipeline can act on',
    'read names lane':
        'the lane grades its own autoOwed/autoHeld verdict, and read_names_lane appears in no builder — it marks its own homework',
    'readers agree':
        '⚠ CLASSIFIED COVERED AND REFUTED ON REVIEW: readers-same-screen reads the SAME two calibration constants the check already reads, so it is one module pair re-derived, not an independent second source',
    'river joints':
        "the river reports about itself — the row taps river.py's own trace and summary, an engine's self-diagnosis, and no builder asks river anything",
    'river outlet':
        "the quantity is FLOW, a waiting queue against the driver's own counter inside one process; the route joints guard what was already routed and stay green while the river is dead",
    'river walk':
        'the walker is the only witness that it looked — the serving process publishing its own global over its own wire, with no second record of when the river was last walked',
    'route chronicle · sets':
        'one census from one engine decides whether sets-ledgered reels left on the sets route; chronicle-owed looks related by name but compares reading DEBT',
    'route chronicle · uniques':
        'as for sets — reel_templates.route_census is the sole authority on whether uniques-ledgered reels exited intact, and nothing re-derives it',
    'route inventory':
        'the same single census judges the inventory route, and no joint pairs it with an independent derivation',
    'route stash':
        'one census, one engine: a single walk over templates() judging whether stash-evidence reels came out on the stash route, read by no builder',
    'running code matches disk':
        "already two-sided inside the row — the console's report of what it LOADED against the file's bytes; no third engine knows what the console imported, and a second hash would be the disk agreeing with itself",
    'screen still painting':
        'the screencaptures are themselves the second eye over every text-based check; there is no third instrument photographing his window for a joint to pair them with',
    'shelf is where it says':
        "the rect and the fill it joins are two fields of ONE uiBeat published by the same page — an internal pair, not two engines; same family as 'console UI faults'",
    'shelf lanes reading':
        "one reading of the driver's own stored beat; the shelf-named joints count REELS, never whether the driver is still beating",
    'stage shows the dom':
        "the row IS the pairing — the DOM's claim held against an actual screen reading — and stage_witness appears in no builder, so nothing re-derives either side",
    'stray processes':
        'the process table is the ground truth and no second engine measures what is running on the machine; none of the joints touches processes at all',
    'test venue':
        'launchd is the only authority on what is scheduled here; there is no second store of scheduling truth to pair it with',
    'the river':
        'the station assignment and the owes field have ONE source — reel_router grades the lanes itself; router-and-shelf-agree only corroborates the denominator, the reel universe',
    'tooltip finder':
        "tooltip-finder-refuses reads refused and located out of the SAME report the row reads — one module reading back its own output, a shared-source exception the registry's own audit already names",
    'vault proposal':
        "the vault's own gate re-grades the vault's own stored photograph; no invariant reads the proposal, so nothing else says whether the rows still clear the bar",
    'what runs without you':
        "promise-versus-body is already the two-sided reading, and ONE reader performs both halves over one module — the same shape as the registered 'lane intent' reason",
    "console UI faults": "the console reports about itself; there is no second engine to agree with",
    # v2726 — DECLARED, NOT SKIPPED. coldread now EXCUSES a missing region when its host declares
    # itself empty, and that exemption decides whether a ship may proceed (the second-eye gate).
    # By [[join-gate-heart]] that earns a joint — but a joint needs two INDEPENDENT readings, and
    # there is only one instrument here: the renderer is the sole thing that photographs a version.
    # The ledger cannot corroborate it (it records what the renderer produced), and comparing the
    # exemption against its own declaration is a tautology. Writing one anyway would be a joint in
    # name, which is worse than none because it would READ as covered.
    # The gate does the load-bearing work instead: test_coldread_empty_is_not_broken pins that the
    # excused empty branch still EXISTS in bible.html, so the exemption cannot outlive its premise.
    # ⚠⚠ v3017 — "cold read exemption" REMOVED for the same reason as "reel rungs": it names no
    # live doctor check and never did. The reason it carried was sound prose about a real
    # difficulty, but it was filed against a row that was never added to console_doctor.CHECKS, so
    # nothing was ever explained by it. A registry entry for a check that does not exist is not
    # documentation — it is a second thing to keep in step, and it inflates the explained count.
    # If that row is ever built, this entry comes back WITH it. [[label-outlived-referent]]
    "version drift":     "one reading of one number; a joint would need a second source of truth",
    "lane intent":       "intent vs reality is already a two-sided check inside the eagle itself",
    "disk headroom":     "the disk is the ground truth; nothing else independently measures it",
    "subscription":      "the provider is the only authority on spend",
    "unattended reel":   "a single live observation",
    "board is claimed":  "needs the board window open; UNKNOWN here is honest, not a gap",
    "visual lock":       "a source invariant, checked structurally rather than cross-engine",
    "art corpus":        "file-level integrity, no second engine",
    "footage has a reel": "the frame stamp IS the second source; the eagle already joins them",
    "progress number":   "his board is the only authority on his own progress",
    "store emptied":     "needs the board window open",
    # 2026-09-27 — DECLARED, NOT SKIPPED. The watcher's record and the restore plan's replay run ONE
    # function (ledger_restore.drops_between / step_episodes) over the SAME backup files, on
    # purpose — two definitions of a drop would drift. Pairing them would be one number wearing two
    # names; the backups are the only source, and the row reads the record the prune obeys.
    "ledger drop":       "one definition over one source by design — the backups are the only witness",
    "locked lanes":      "a policy assertion, not a measurement pair",
    "surfaces agree":    "already a two-surface check inside the eagle",
    "the other doctors": "a roll-up of other verdicts",
}


def coverage():
    """Which engines have a joint, which do not, and why. -> dict. Reads nothing, decides nothing."""
    try:
        sys.path.insert(0, HERE)
        import console_doctor as _cd
        engines = [n for n, _fn in _cd.CHECKS]
    except Exception as e:
        return {"ok": False, "why": "could not ask the eagle for its roster: %s" % str(e)[:80]}
    covered, uncovered, unexplained = {}, {}, []
    for n in engines:
        if n in COVERED_BY:
            covered[n] = list(COVERED_BY[n])
        elif n in NO_JOINT_YET:
            uncovered[n] = NO_JOINT_YET[n]
        else:
            # ⚠ A NEW ENGINE WITH NEITHER A JOINT NOR A STATED REASON. Silence here is the defect:
            # it would read as covered simply by not appearing in either list.
            unexplained.append(n)
    return {"ok": True, "engines": len(engines),
            "covered": covered, "uncovered": uncovered, "unexplained": unexplained,
            "say": ("%d engine(s): %d with a joint, %d with a stated reason for none%s"
                    % (len(engines), len(covered), len(uncovered),
                       "" if not unexplained else
                       " — ⚠ %d NEITHER: %s" % (len(unexplained), ", ".join(unexplained))))}


def _holds(a, b, rel):
    if rel == "==":
        return a == b
    if rel == "<=":
        return a <= b
    if rel == ">=":
        return a >= b
    raise ValueError("unknown relation %r" % rel)


def check_one(builder):
    """-> dict. Never raises; a builder that explodes is UNKNOWN, never agreement."""
    try:
        key, what, prove, ln, lf, rn, rf, rel = builder()
    except Exception as e:
        return {"key": getattr(builder, "__name__", "?"), "state": UNKNOWN,
                "say": "the invariant could not be built: %s" % str(e)[:90]}
    L, R = _reading(ln, lf), _reading(rn, rf)
    row = {"key": key, "what": what, "prove": prove, "rel": rel,
           "left": {"who": ln, "value": L.value}, "right": {"who": rn, "value": R.value}}
    if not L.known or not R.known:
        row["state"] = UNKNOWN
        row["say"] = ("cannot be corroborated — %s"
                      % "; ".join(x.why for x in (L, R) if not x.known))
        return row
    if _holds(L.value, R.value, rel):
        row["state"] = AGREE
        row["say"] = "%s (%s %s %s %s)" % (what, ln, L.value, rel, rn)
        return row
    row["state"] = DISAGREE
    # BOTH numbers, BOTH names, no averaging and no verdict about which is right.
    row["say"] = ("%s says %s and %s says %s, and they must be %s. Neither number is corrected "
                  "here: two surfaces disagreeing IS the finding, and the one that is wrong is not "
                  "knowable from the pair alone." % (ln, L.value, rn, R.value, rel))
    return row


def run():
    """Every invariant. -> list of rows."""
    sys.path.insert(0, HERE)
    return [check_one(b) for b in BUILDERS]


def verdict(rows=None):
    """-> (state, say) for the eagle."""
    rows = run() if rows is None else rows
    bad = [r for r in rows if r.get("state") == DISAGREE]
    unk = [r for r in rows if r.get("state") == UNKNOWN]
    if bad:
        return DISAGREE, ("%d engine pair(s) disagree: %s"
                          % (len(bad), " · ".join("%s — %s" % (r["key"], r["say"]) for r in bad[:2])))
    if unk and len(unk) == len(rows):
        return UNKNOWN, ("none of the %d invariants could be corroborated: %s"
                         % (len(rows), unk[0].get("say", "")[:110]))
    if unk:
        return AGREE, ("%d engine pair(s) agree, %d could not be measured (%s)"
                       % (len(rows) - len(unk), len(unk), unk[0]["key"]))
    return AGREE, "all %d engine pair(s) agree" % len(rows)


# ══ v2393 — EVERY INVARIANT PROVES ITSELF, OR SAYS IT HAS NOT ════════════════════════════════
# Konyo: "self-proving gaps i want taken care of everywhere all round the console — i want this
# logic and its own logic coded proving itself, and if it drifts it gets flagged accordingly."
#
# selftest() proves the RELATIONS can refuse (==, <=, >= against synthetic numbers). It has never
# proved that any PARTICULAR invariant can. Those are different claims, and the gap between them
# is where an inert check hides.
#
# MEASURED 2026-09-01, every invariant against his live tree — SIX OF FIFTEEN carry no information:
#     agreeing at ZERO vs ZERO (cannot tell healthy from inert)
#         a_lane_that_is_ON_has_either_worked_or_says_why_not   0 vs 0
#         chronicle_owed_agrees                                 0 vs 0
#         the_deleter_is_never_looser_than_the_planner          0 vs 0
#         the_tooltip_finder_refuses_more_than_it_finds         0 vs 0   <- and THAT is a finding:
#                                                                          the finder has never
#                                                                          located OR refused
#         the_two_deleters_stay_at_their_own_granularity        0 vs 0
#     UNKNOWN (a side could not be read)
#         the_eagle_can_still_look                           None vs 34
#         the_two_owned_fields                                  7 vs None
# Every one of them RENDERS AS "agree" — indistinguishable from a healthy check.
#
# ⚠ THIS SABOTAGES THE INVARIANT'S OWN OPERANDS, NEVER THE LIVE SYSTEM. Perturbing real state to
# test a check would be a test that can damage the thing it grades, on a machine he plays on. The
# perturbation is arithmetic on the value the builder already returned, fed through the SAME
# check_one the live path uses.
#
# ⚠ AND IT PROVES A NARROW THING, WHICH IT MUST SAY OUT LOUD: that the invariant's RELATION can
# refuse given its own operands. It does NOT prove the builders read the right engines — that is
# what the independence audit above is for, and what a runnable per-invariant sabotage would prove
# properly. An instrument that oversells its reach is the defect this whole file exists to catch.
# [[unknown-stays-unknown]] [[regression-guard]]

def _perturb(L, R, rel):
    """A left-hand value that MUST violate `rel` against R. -> (value, why) or (None, why)."""
    if R is None or isinstance(R, bool) or not isinstance(R, (int, float)):
        return None, "the right side is %r — no arithmetic perturbation is defined" % (R,)
    if rel == "==":
        return R + 1, "left made one greater than right"
    if rel == "<=":
        return R + 1, "left pushed above the ceiling it must stay under"
    if rel == ">=":
        return R - 1, "left pushed below the floor it must stay above"
    return None, "unknown relation %r" % (rel,)


def prove_each():
    """Can each invariant actually REFUSE? -> list of dicts, one per invariant.

    proven    the relation went red when its own left value was perturbed
    exercised BOTH sides were non-zero — i.e. it has been asked a real question, not 0 vs 0
    """
    out = []
    for name in sorted(n for n in globals() if n.startswith("_inv_")):
        f = globals()[name]
        if not callable(f):
            continue
        row = {"invariant": name[5:], "proven": False, "exercised": None, "why": ""}
        try:
            key, what, prove, ln, lf, rn, rf, rel = f()
        except Exception as e:
            row["why"] = "could not be built: %s" % str(e)[:70]
            out.append(row)
            continue
        L = _reading(ln, lf)
        R = _reading(rn, rf)
        row["rel"] = rel
        row["left"] = L.value if L.known else None
        row["right"] = R.value if R.known else None
        if not (L.known and R.known):
            # UNKNOWN is not a pass and not a failure — it is "this could not be graded today".
            row["why"] = "a side is UNKNOWN, so it cannot be perturbed or judged"
            out.append(row)
            continue
        # has it ever been asked a real question? 0 vs 0 agrees whatever the engines say.
        row["exercised"] = bool(L.value) or bool(R.value)
        bad, why = _perturb(L.value, R.value, rel)
        if bad is None:
            row["why"] = why
            out.append(row)
            continue
        probe = check_one(lambda: (key, what, prove, ln, (lambda: bad), rn, (lambda: R.value), rel))
        row["proven"] = (probe.get("state") == DISAGREE)
        row["why"] = why if row["proven"] else (
            "PERTURBED AND IT STILL AGREED — this invariant cannot refuse: %s" % probe.get("say", "")[:80])
        out.append(row)
    return out


def selftest():
    """DRIVE EVERY INVARIANT RED. An invariant nobody has seen disagree proves nothing.

    This does not touch his tree: each relation is exercised against synthetic numbers through the
    same `_holds` the live path uses, and `check_one` is driven with builders that return known
    readings. If a relation stops being able to fail, this says so.
    """
    out = []
    for rel, a, b in (("==", 1, 2), ("<=", 5, 4), (">=", 3, 9)):
        out.append(("relation %s can refuse" % rel, not _holds(a, b, rel)))
        out.append(("relation %s can hold" % rel, _holds(a, a, rel)))

    def _mk(lv, rv, rel):
        return lambda: ("synthetic", "what", "prove", "L", (lambda: lv), "R", (lambda: rv), rel)

    out.append(("a mismatch reports DISAGREE", check_one(_mk(1, 2, "=="))["state"] == DISAGREE))
    out.append(("a match reports AGREE", check_one(_mk(2, 2, "=="))["state"] == AGREE))
    out.append(("a None side reports UNKNOWN", check_one(_mk(None, 2, "=="))["state"] == UNKNOWN))
    out.append(("UNKNOWN is not AGREE", check_one(_mk(None, 2, "=="))["state"] != AGREE))
    row = check_one(_mk(157, 7, "=="))
    out.append(("both numbers survive into the message",
                "157" in row["say"] and "7" in row["say"]))
    out.append(("it does not pick a side",
                "is not knowable" in row["say"]))

    # ══ v2390 — AND THE CORROBORATOR NOW POLICES ITS OWN INVARIANTS ═══════════════════════════
    # Konyo: "that is why we built corroborator so all 54 modules/engines can be communicating..
    # and doctor that can fix it all and flag whats needed" — after a whole pipeline stage was
    # found never to have run.
    #
    # The machinery was not missing. `_inv_vault_worklist` existed and was GREEN for months
    # because BOTH of its sides read reel_retention.plan()'s tags: two derivations of one broken
    # source agreeing with each other. 0 == 0, while an independent question answered 43.
    #
    # Two numbers that share a source cannot corroborate anything, so this is now checked
    # STRUCTURALLY, on every invariant, forever — rather than by someone noticing.
    # [[feedback-contradiction-is-the-finding]] [[the-unjoined-end]]
    #
    # ⚠ ONE DELIBERATE EXCEPTION, NAMED RATHER THAN PATTERN-MATCHED AROUND.
    # `_inv_the_tooltip_finder_refuses_more_than_it_finds` reads two DIFFERENT COUNTERS out of one
    # report (refused >= located). That is an internal-ratio check, not self-corroboration: it
    # genuinely goes red when the area floor is lowered. An exception list of one, with its
    # reason, is honest; a regex that quietly excused this shape would not be.
    # ⚠ EXCEPTIONS ARE NAMED ONE BY ONE, WITH THE MEASUREMENT THAT EARNED THEM. A regex that
    # quietly excused this shape would re-open the hole this whole audit exists to close, and a
    # syntactic pass genuinely cannot tell "delegates entirely" from "consults, then falls back".
    # So each entry below was PROVEN independent by driving its own `prove` line and watching the
    # two sides part.
    _SHARED_SOURCE_OK = {
        # two DIFFERENT counters out of one report (refused >= located) — an internal ratio, not a
        # shared source. It goes red when _MIN_AREA_FRAC is lowered, which is what it is for.
        "_inv_the_tooltip_finder_refuses_more_than_it_finds",
        # v2746 — BOTH SIDES REACH control_app.fleet_presence, AND IT IS AN ENVELOPE RATHER THAN A
        # SOURCE. The two numbers that travel in it are computed by unrelated code: `tally.have` is
        # a COUNT the other machine's console posted, and the mask is an OPAQUE BITMASK this machine
        # decodes against a roster file on its own disk — the worker in between never decodes it.
        # PROVEN INDEPENDENT 2026-09-06 by driving its own prove line rather than by argument: a
        # synthetic board holding ONE set-piece name absent from the shared roster, posting
        # have=21 against a mask encoding 20.
        #     baseline   agreeN 2, comparable 2   ->  2 == 2   AGREE
        #     sabotage   agreeN 0, comparable 1   ->  0 != 1   DISAGREE
        # The sides part. A shared envelope is not a shared derivation. [[feedback-suspect-the-instrument]]
        "_inv_a_posted_COUNT_and_its_own_MASK_agree",
        # left calls ca._register_is_anchor, which CONSULTS inventory_law.is_locked and then falls
        # back to its own frozenset and a "tome of" test — so the console keeps independent
        # knowledge. MEASURED 2026-09-01 by driving its own prove line: drop one entry from
        # inventory_law.LOCKED and the sides part 4 vs 3. A real invariant with a shared call in it.
        "_inv_the_console_and_the_law_agree_about_furniture",
        # 2026-09-28 (Ledger fix, finding 4) — BOTH SIDES REACH vault_evidence.tier_census, AND ON
        # THE RIGHT IT IS THE SUBJECT LIST, NOT THE VERDICT. The review asked for this joint PER
        # ITEM ("the PROVEN+ names must be a subset of the names the gate sees 10+ looks for"),
        # because a count compare let two wrong items balance. A per-item check has to ask the gate
        # about the tier table's OWN names, so the right side reads those names from tier_census —
        # and the number it returns is vault_retro.gate's verdict on each, computed by the gate's
        # own look counting, which never calls vault_evidence. PROVEN INDEPENDENT 2026-09-28 by
        # driving its own prove line (the frame math back in _measure):
        #     Radiance(1+102 frames, 2 visits) + Shako(12 visits)   baseline 1 == 1 AGREE
        #                                                          sabotage 2 vs 1 DISAGREE
        #     StillScreen(1 visit x 25) + TenLooks(10 looks, 5 unsure) baseline 0 == 0 AGREE
        #                                                          sabotage 1 vs 0 DISAGREE
        # (the old count compare read 1 vs 1 AGREE on that second sabotage). The sides part.
        "_inv_a_tier_stands_on_the_looks_the_gate_counts",
    }
    try:
        import inspect as _insp
        import re as _re
        shared_bad = []
        unjudged = []
        # ⚠ v2434 — EVERY INVARIANT MUST BE IN ONE LIST OR THE OTHER. Without this an invariant
        # can sit in the file, be graded by prove_each() and audited for independence, and never be
        # evaluated by run() -- which is exactly what `deleter-not-looser` did from the day it was
        # written. Neither roster noticed, because neither was compared to the other.
        _declared = set(RETIRED) | {getattr(_b, "__name__", "") for _b in BUILDERS}
        _orphans = [n for n in sorted(globals())
                    if n.startswith("_inv_") and n not in _declared]
        out.append(("no invariant is graded but never RUN"
                    + (" — in neither BUILDERS nor RETIRED, so prove_each() and the independence "
                       "audit grade them while run() and the eagle can never evaluate them: %s"
                       % ", ".join(_orphans) if _orphans else ""),
                   not _orphans))
        for _name in sorted(n for n in globals() if n.startswith("_inv_")):
            _f = globals()[_name]
            if not callable(_f):
                continue
            try:
                src = _insp.getsource(_f)
            except Exception:
                unjudged.append(_name)
                continue
            if "def left()" not in src or "def right()" not in src:
                unjudged.append(_name)          # NOT the same as clean
                continue
            # local import aliases declared inside this invariant: {alias: real module}
            _aliases = dict((a, m) for m, a in
                            _re.findall(r"import\s+([A-Za-z_][\w.]*)\s+as\s+(\w+)", src))
            l = src[src.index("def left()"):src.index("def right()")]
            r = src[src.index("def right()"):]
            def _direct(b):
                return set(_re.findall(r"\b([a-z_]{2,}(?:\.[a-zA-Z_]+)+)\s*\(", b))

            def _norm(tok, al):
                """alias.fn -> realmodule.fn. The comparison must be on what a call RESOLVES to."""
                head, _, rest = tok.partition(".")
                return "%s.%s" % (al.get(head, head), rest) if rest else tok

            def _calls(b, depth=1):
                """Calls this body makes, plus the calls THOSE make, one level down.

                ⚠ ONE LEVEL IS NOT DECORATION — IT IS THE WHOLE POINT, AND THE FIRST CUT OF THIS
                AUDIT WITHOUT IT WOULD HAVE MISSED THE DEFECT IT WAS WRITTEN FOR. In the real
                case, left called `ca._vault_owed_reels(hist)` and right called `rr.plan(hist)`:
                two different literals, no direct overlap, "independent" by a syntactic reading —
                and _vault_owed_reels is nothing but a filter over plan(). The sharing was one
                hop down. Proven by sabotage: with direct-only matching, restoring the original
                shape kept the self-test GREEN. [[feedback-suspect-the-instrument]]
                """
                out = set(_norm(t, _aliases) for t in _direct(b))
                if depth <= 0:
                    return out
                for tok in list(out):
                    mod, _, fn = tok.rpartition(".")
                    # ⚠ THE ALIAS IS LOCAL TO THE INVARIANT, AND THE FIRST TWO CUTS OF THIS AUDIT
                    # BOTH DIED HERE. Invariants do `import control_app as ca` INSIDE themselves,
                    # so "ca" is not in globals() and __import__("ca") raises — every callee went
                    # unresolved, the expansion found nothing, and the self-test stayed green
                    # through a sabotage that restored the exact defect. Resolve the alias from
                    # the invariant's own import lines first. [[feedback-suspect-the-instrument]]
                    mod = _aliases.get(mod, mod)
                    try:
                        m = globals().get(mod) or __import__(mod)
                        tgt = getattr(m, fn, None)
                        if tgt is None or not callable(tgt):
                            continue
                        # ⚠ NORMALISE THE CALLEE'S OWN TOKENS TOO, THROUGH ITS OWN ALIASES.
                        # The fifth cut of this audit failed here and it is the subtlest step:
                        # control_app._vault_owed_reels calls `_rr.plan(...)` while the invariant's
                        # right side calls `rr.plan(...)`. Same module, different local alias, so a
                        # literal comparison found no overlap and the sabotage stayed GREEN.
                        # Compare RESOLVED module.function, never the alias someone happened to type.
                        _sub = _insp.getsource(tgt)
                        _sub_al = dict((a, m) for m, a in
                                       _re.findall(r"import\s+([A-Za-z_][\w.]*)\s+as\s+(\w+)", _sub))
                        out |= set(_norm(t, _sub_al) for t in _direct(_sub))
                    except Exception:
                        # a callee we cannot read is a callee whose sharing we cannot rule out.
                        # Record it so the pair is judged, never silently cleared.
                        out.add("?unreadable:" + tok)
                return out

            def _is_ours(tok):
                """Is this call into one of THIS PROJECT's engines?

                ⚠ THE THIRD CUT OF THIS AUDIT OVER-FIRED, and an over-firing gate is as useless
                as a silent one. Following callees one level surfaced os.path.join, io.open and
                json.load as "shared" on seven invariants — true, and meaningless: two sides both
                opening a file share PLUMBING, not a SOURCE. The question is only ever whether
                they read the same ENGINE. Resolved by asking where the module lives, not by a
                name blocklist that would rot the moment an engine is renamed.
                """
                mod = tok.split(".")[0]      # already normalised by _norm
                try:
                    m = globals().get(mod) or __import__(mod)
                    f = getattr(m, "__file__", "") or ""
                except Exception:
                    return False
                return os.path.dirname(os.path.abspath(f)) == HERE

            shared = {c for c in (_calls(l) & _calls(r))
                      if _is_ours(c)
                      and not c.split(".")[-1].startswith(("get", "int", "str", "len"))}
            if shared and _name not in _SHARED_SOURCE_OK:
                shared_bad.append("%s (%s)" % (_name, ",".join(sorted(shared))))
        out.append(("no invariant corroborates a thing against ITSELF"
                    + (" — %s" % "; ".join(shared_bad) if shared_bad else ""),
                    not shared_bad))
        # an invariant this audit could not read is UNJUDGED, and unjudged is not clean
        out.append(("every invariant was judgeable"
                    + (" — could not read: %s" % ",".join(unjudged) if unjudged else ""),
                    not unjudged))
    except Exception as _e:
        out.append(("the independence audit ran at all (%s)" % str(_e)[:60], False))
    return out


def main(argv):
    try:
        from console_safe import enable  # noqa: F401
    except Exception:
        pass
    if "--selftest" in argv:
        rows = selftest()
        for what, ok in rows:
            print("  %s %s" % ("OK  " if ok else "FAIL", what))
        bad = [w for w, ok in rows if not ok]
        print("\n%s" % ("🟢 every invariant can both hold and refuse"
                        if not bad else "🔴 %d self-test(s) failed" % len(bad)))
        return 1 if bad else 0
    rows = run()
    for r in rows:
        icon = {AGREE: "🟢", DISAGREE: "🔴", UNKNOWN: "⚪"}.get(r.get("state"), "?")
        print("%s %-24s %s" % (icon, r.get("key"), str(r.get("say"))[:150]))
        if r.get("state") == DISAGREE:
            print("     to reproduce: %s" % r.get("prove"))
    st, say = verdict(rows)
    print("\n%s %s" % ({AGREE: "🟢", DISAGREE: "🔴", UNKNOWN: "⚪"}.get(st, "?"), say))
    return 1 if st == DISAGREE else 0


RED_PROOF = [
    {
        'why': 'The gate is `python3 tv/corroborate.py --selftest` (run_gates.py:189) and the source it protects is corroborate.py itself. `_holds(a, b, rel)` is the one place every cross-engine invariant\'s relation is actually evaluated — check_one() calls it for the live path, and the self-test\'s first six laws exist to prove each relation can both hold and refuse. The ceiling arm `return a <= b` (line 1945) IS the comparison, not a comment, not a message string, and not a constant read by both sides of an agreement law: replacing it with `return True` deletes the ability of the `<=` relation to ever say no, so any invariant asserting "left must stay under this ceiling" would report agreement whatever the engines said — precisely the failure the gate\'s own `why` names ("If this self-test stops going red on demand, the corroborator would report agreement whatever the engines actually said"). The mirror arm `return a >= b` is untouched, so the red is attributable to this edit alone and not to a broadly broken module.  MEASURED: untampered GREEN — 15/15 OK, EXIT=0; tampered (all 1) RED — 1 of 15 rows FAILed ("relation <= can refuse"), EXIT=1; reddened law relation <= can refuse — corroborate.selftest() row 3, asserting `not ; ALONE FAILS ALONE. The gate is a script, not a unittest, so "alone" was a fresh process invoking only that one check.  ⚠⚠ matches=3, NOT 1, AND THAT IS NOT A TYPO. This gate\'s FILE IS ITS OWN TARGET: the gate is `python3 corroborate.py --selftest`, so the RED_PROOF lives in the very file it tampers, and the proof\'s own `find` and `why` fields ARE occurrences of the anchor. The count was a true 1 when measured before the proof was written and a false 1 the moment it landed — a reading that was correct when taken and stale when used. heart2 measured it: "INVALID — the tamper matched 3 time(s), expected 1". The real code site is line 1945; the other two are this declaration, replaced harmlessly in a throwaway sandbox copy after heart2 has already parsed it. The gate reddens because of 1945. [[stale-reading]]',
        'file': 'corroborate.py',
        'find': 'return a <= b',
        'replace': 'return True',
        'matches': 3,
    },
]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
