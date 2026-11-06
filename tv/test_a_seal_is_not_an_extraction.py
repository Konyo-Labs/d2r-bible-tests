#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""🎞🏦 A SEAL IS NOT AN EXTRACTION, AND A CHRONICLE VERDICT CANNOT SPEAK FOR STASH FOOTAGE.

Konyo, 2026-09-10: *"all of the reels get extracted with information thats needed.. whatever doesn
have information on the reels get filtered anyways and go to tombstone eventually within the
filtering system and process"* — and, on the order: *"properly getting filtered and extracted"*
BEFORE the tombstone.

Two rules ship together here, and they are each other's safety.

⚠⚠ 1. `zero-pages` HELD REELS FOR AN EVENT THAT CANNOT HAPPEN.
Its sentence is "the engine reopens these when the prompt improves" — right for footage that HAS a
Chronicle screen the reader failed to read, meaningless for footage that has none.

    MEASURED on his 41 reels, 2026-09-10:
        held as   zero-pages 25 · test-fixture 8 · recent 8      (vault-owes NEVER reached)
        2,437 panel frames, 36% of all footage
        stash 1855 · shared 407 · personal 121 · materials 40 · runes 10 · gems 4
        chronicle: ZERO — and across all 454 surveyed reels in his store, never once

`retro_triage.PANEL_KINDS` carries 'chronicle', so the survey CAN say it and never has. Those reels
are stash footage held by a chronicle verdict, and `vault-owes` — the rule that would claim them —
is never reached because `zero-pages` matches first. reel_retention predicted exactly this: *"the
vault-owes tag genuinely never fires on his tree because earlier rules match first... a LATENT
defect the day a reel legitimately reaches it."*

⚠⚠ 2. AND LIFTING THAT HOLD EXPOSED ELEVEN REELS THE CHAIN CALLED FINISHED.
The moment `zero-pages` stopped matching, eleven reels came back as *"sealed by BOTH lanes — it has
given up its information"*. They had not:

    reel_s_1787508759592_46621   73 panels in  80 frames   148 MB
    reel_s_1787512325134_62795   64 panels in  67 frames   124 MB
    reel_s_1788105158696_89699   49 panels in  49 frames    88 MB

A vault SEAL existed for each with ZERO rows behind it, and the vault lane has never run
(reads: 0). `rows-not-banked` could not catch them — it fires only when rows EXIST and are not
durable, never when the count is zero and the panels are real. **A seal that records nothing is not
an extraction.** `panels-never-banked` is that missing case, and it sits BEFORE `rows-not-banked`
because it is the same lane at a different count.

MEASURED after both rules:
    41 on disk · 34 kept · 7 candidates
    held: test-fixture 8 · panels-never-banked 18 · recent 8
    every one of the 7 survivors: panels on film AND rows durable — genuinely extracted

[[unknown-stays-unknown]] [[label-outlived-referent]] [[feedback-contradiction-is-the-finding]]
"""
import collections
import io
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
import fixture_tmp as _fx_tmp  # noqa: E402  #171 — this run's scratch dirs leave with it
_fx_tmp.contain()

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import console_safe  # noqa: E402  — this file prints 🎞 🏦 ⚠ ★
console_safe.enable()

import reel_retention as RR  # noqa: E402
import reel_story as RS      # noqa: E402


RED_PROOF = [
    {
        "why": "putting the chronicle hold back over stash footage: 25 reels with no chronicle "
               "panel anywhere are held waiting for a prompt improvement that can never find a "
               "page, and vault-owes is never reached",
        "file": "reel_retention.py",
        "find": "        elif (pages < MIN_PAGES and not _proven_empty(reel) and not _no_chronicle_to_find(reel)",
        "replace": "        elif (pages < MIN_PAGES and not _proven_empty(reel)",
        "matches": 1,
    },
    {
        "why": "removing the safety half: reels whose panels were never banked become deletable "
               "on the strength of a seal with zero rows behind it — the stash rows live only in "
               "those frames, and deleting them destroys the only copy",
        "file": "reel_retention.py",
        "find": "        elif _panels_never_banked(reel, ve) and not _rel(reel, ve):",
        "replace": "        elif False and _panels_never_banked(reel, ve) and not _rel(reel, ve):",
        "matches": 1,
    },
]


def _shelf(rows):
    """Build an isolated shelf and return (tmp, hist, plan). -> (str, str, dict)

    ⚠⚠ v2875 — FIXTURE, NOT HIS FOOTAGE, AND THAT IS WHY THIS GATE CAN BE PROVEN AT ALL.
    The first cut read `frames/hist` directly. MEASURED: a heart2 sandbox has NO frames/hist —
    `safe_copy` carries the JSON stores and deliberately leaves the 6 GB of film behind — so
    `plan()` returned ok:False, three of five laws called skipTest, and both red-proofs came back
    BLIND. heart2's own verdict named it exactly: "3 of 5 law(s) SKIPPED, but the other 2 DID run
    and stayed green — so the law IS weak, and separately some laws opted out."

    `TV_HIST` redirects `retro_triage._store_path()`, and v2750 made `plan()` read the CALLER's
    chronicle_swept/vault_swept out of its hist_dir rather than the live ones. So a shelf built
    here is answered by stores built here, and the laws run on every machine.
    [[feedback-fixtures-never-touch-live-data]] [[feedback-blind-fixture-green-gate]]

    `rows` is [(age_days, panels, pages)] — oldest first.
    """
    tmp = tempfile.mkdtemp(prefix="sealshelf_")
    hist = os.path.join(tmp, "hist")
    os.makedirs(hist)
    now = int(time.time() * 1000)
    survey, chron = {}, {}
    for i, (age, panels, pages) in enumerate(rows):
        nm = "reel_s_%d_%03d" % (now - int(age * 86400000), i)
        d = os.path.join(hist, nm)
        os.makedirs(d)
        for f in range(3):
            io.open(os.path.join(d, "f_%d.jpg" % (1700000000 + f)), "w").write("x")
        survey[nm] = {"full": True, "panels": panels, "frames": 3,
                      "kinds": ({"stash": panels} if panels else {})}
        chron[nm] = {"ts": now, "classified": 1, "pages": pages, "looked": True,
                     "framesAtLook": 3, "why": "fixture"}
    io.open(os.path.join(hist, "chronicle_swept.json"), "w", encoding="utf-8").write(
        json.dumps(chron))
    io.open(os.path.join(hist, "vault_swept.json"), "w", encoding="utf-8").write(json.dumps({}))
    old = os.environ.get("TV_HIST")
    os.environ["TV_HIST"] = hist
    # ⚠⚠ v2879 — THE WITNESS INDEX IS STUBBED, OR THE CHAIN NEVER REACHES THE RULE.
    # MEASURED on CI and reproduced here by hiding the ambient stores: every reel comes back
    # `no-witness-index` — the FIRST rule in plan()'s chain — because `frame_authority.
    # witness_index(HERE)` reads a durable store that a runner does not have. The safety promise
    # still held there (candidates: 0), but these laws are about the rule FURTHER DOWN, and a law
    # that never reaches its subject certifies nothing. `plan()` reads that index from HERE, not
    # from the caller's hist_dir (the v2750 host-dependency), so the fixture cannot supply it by
    # writing a file — it has to say so out loud. Stubbing what you are NOT testing is not
    # weakening a law; letting the runner's filesystem decide which branch runs is.
    # [[feedback-blind-fixture-green-gate]] [[gate-blind-to-unexercised-input]]
    import frame_authority as _fa
    _real_wi = _fa.witness_index
    # ⚠ A COMPLETE index, not a half one. The first cut returned only `haveIndex`, and the
    # chain then held every reel as `ledger-unreadable` — the SECOND rule — because a result
    # missing `ok` reads as "the durable witness index could not be read". A stub that is
    # missing a field is a different fixture from the one you meant to build.
    _fa.witness_index = lambda *a, **k: {"haveIndex": True, "ok": True,
                                         "frames": set(), "sessions": set(), "perStore": {}}
    try:
        import retro_triage as rt
        io.open(rt._store_path(), "w", encoding="utf-8").write(json.dumps(survey))
        RR._TRIAGE_CACHE["at"] = None
        plan = RR.plan(hist)
    finally:
        _fa.witness_index = _real_wi
        if old is None:
            os.environ.pop("TV_HIST", None)
        else:
            os.environ["TV_HIST"] = old
        RR._TRIAGE_CACHE["at"] = None
    return tmp, hist, plan


def _tags(plan):
    return collections.Counter(k.get("tag") for k in (plan.get("kept") or []))


class ASealIsNotAnExtraction(unittest.TestCase):

    # ── ⚠⚠ THE LAW ──────────────────────────────────────────────────────────────────────────
    def test_panels_on_film_with_NOTHING_banked_are_HELD(self):
        """★★ The safety rule. A reel the survey says holds panels, whose rows are not durable,
        must be KEPT — whatever any seal claims. Driven on an isolated shelf so it holds on every
        machine, including a sandbox with no footage at all."""
        rows = [(90, 40, 0), (89, 0, 0)] + [(d, 5, 0) for d in range(30, 30 - RR.KEEP_RECENT, -1)]
        tmp, hist, plan = _shelf(rows)
        try:
            self.assertTrue(plan.get("ok"), "the fixture shelf did not plan: %r" % plan.get("say"))
            t = _tags(plan)
            self.assertGreater(
                t.get("panels-never-banked", 0), 0,
                "a reel with 40 panel frames and no durable row was not held by "
                "`panels-never-banked` — tags: %r" % dict(t))
            names = [k.get("reel") for k in plan["kept"] if k.get("tag") == "panels-never-banked"]
            cands = [c.get("reel") if isinstance(c, dict) else str(c)
                     for c in (plan.get("candidates") or [])]
            self.assertEqual([], [n for n in names if n in cands],
                             "a reel is both held and offered for deletion")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_a_reel_with_NO_panels_is_not_held_by_that_rule(self):
        """★★ The other half — a rule that holds everything is not a filter. A full survey finding
        zero panels means there is nothing to bank, so it must fall through."""
        rows = [(90, 0, 0)] + [(d, 5, 0) for d in range(30, 30 - RR.KEEP_RECENT, -1)]
        tmp, hist, plan = _shelf(rows)
        try:
            self.assertTrue(plan.get("ok"))
            held = [k.get("reel") for k in plan["kept"] if k.get("tag") == "panels-never-banked"]
            oldest = sorted(k.get("reel") for k in plan["kept"] + list(plan.get("candidates") or [])
                            if isinstance(k, dict))[:1]
            self.assertEqual(
                [], [h for h in held if h in oldest],
                "a reel whose FULL survey found zero panels was held as `panels-never-banked` — "
                "there is nothing in it to extract, so it must be allowed to retire")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_a_chronicle_verdict_does_not_hold_STASH_footage(self):
        """★★ The unjamming rule. A reel whose FULL survey found no chronicle panel may not be
        held as `zero-pages` — no future prompt can find a page that was never filmed."""
        rows = [(90, 40, 0), (89, 12, 0)] + [(d, 5, 0) for d in range(30, 30 - RR.KEEP_RECENT, -1)]
        tmp, hist, plan = _shelf(rows)
        try:
            self.assertTrue(plan.get("ok"))
            t = _tags(plan)
            self.assertEqual(
                0, t.get("zero-pages", 0),
                "%d reel(s) are held for a chronicle re-read although a FULL survey found no "
                "chronicle panel in them — tags: %r" % (t.get("zero-pages", 0), dict(t)))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    # ── the wiring ──────────────────────────────────────────────────────────────────────────
    def test_the_new_rule_is_DECLARED_and_has_a_river_stage(self):
        """★★ [[the-unjoined-end]] — a verdict plan() can emit with no stage draws a reel nowhere.
        reel_retention.RULES is module-level for exactly this, and test_reel_story asserts it."""
        self.assertIn("panels-never-banked", RR.RULES,
                      "the rule fires but is not declared in RULES, so coverage cannot report it")
        self.assertIn("panels-never-banked", RS.TAG_STAGE,
                      "the rule has no stage in the river story — a reel wearing it is drawn nowhere")
        self.assertEqual("banked", RS.TAG_STAGE["panels-never-banked"],
                         "stuck-before is %r; it has been swept and surveyed, and what has not "
                         "happened is the extraction" % RS.TAG_STAGE["panels-never-banked"])

    def test_it_sits_BEFORE_rows_not_banked(self):
        """★ Order is the whole point: rows-not-banked fires when rows exist and are not durable;
        this one when the count is ZERO and the panels are real. Reversed, the zero case falls
        through to the rules that call the reel finished."""
        self.assertLess(RR.RULES.index("panels-never-banked"), RR.RULES.index("rows-not-banked"),
                        "panels-never-banked must be evaluated before rows-not-banked")


if __name__ == "__main__":
    unittest.main(verbosity=2)
