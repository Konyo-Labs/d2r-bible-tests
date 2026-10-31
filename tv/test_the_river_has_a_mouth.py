# -*- coding: utf-8 -*-
"""I REPORTED THAT THE RIVER NEVER REACHED ITS END. IT HAS REACHED IT 410 TIMES.

Konyo asked for THE SHELF drawn as the river, "down the river ending in extraction and then
TOMBSTONE ... eventually pruned and deleted in tombstone".

I measured `reel_router._station_of` and found it returns TOMBSTONE **zero times in code** while
every other station has exactly one return path, and the live census reads:

    counts    {..., "ROUTED": 0, "TOMBSTONE": 0}
    unreached ["INTAKE", "TRIAGE", "ROUTED", "TOMBSTONE"]

and I reported that as "the river has no mouth — nothing can ever reach the end". **THAT WAS
WRONG**, and it is the kind of wrong that would have shaped a whole feature around a false premise.

MEASURED, on his real stores:
    tombstoned in the ledger   410 reel(s), 5,768.1 MB reclaimed
    living reels on the shelf   40
    OVERLAP                      0
A tombstoned reel LEAVES THE DISK. It stops being a card and becomes a row. The router stations
what EXISTS — it was never wrong, it was answering a different question, and I read its answer to
one question as the answer to another. [[label-outlived-referent]]
[[feedback-contradiction-is-the-finding]]

⇒ So the mouth is read from the LEDGER and never manufactured in the router. That is not a
workaround: `reel_router.assert_independent_of_retention()` exists precisely so a living reel's
POSITION comes from its own reading evidence and never from a retention tag. "Has this been closed
out and its footage reclaimed?" is a retention fact. Putting it in the router would merge the two
questions that guard was written to keep apart.

WHAT THE MOUTH CARRIES, and why each field is there:
  · n / mb        410 journeys, 5,768.1 MB — the end of the river, quantified
  · dated/undated 410 dated, 0 undated. FIFO needs a timestamp; a row without one cannot be placed
                  in the order, and saying so beside the count is cheaper than a timeline that
                  quietly omits it. [[zero-needs-a-denominator]]
  · recent        the tail, each with why/pages/mb — 394 of 410 closed having read ZERO pages,
                  which is either healthy filtering or a lot of capture that never earned its disk.
                  Exactly the "is something not right" signal he asked the view to surface.
"""
import ast
import io
import re
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    from console_safe import enable
    enable()
except Exception:
    pass

import control_app as CA  # noqa: E402

SRC = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()


UI = io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()


def _js_only(src):
    """JS with /* ... */ comments removed. -> str

    ⚠ A LAW MUST NEVER READ ITS OWN COMMENTARY. This file's neighbours have been satisfied four
    times by explanatory prose that names the very thing being asserted, so every assertion below
    runs on executable text. [[presence-law-vs-reachability-law]]
    """
    out, i = [], 0
    while True:
        j = src.find("/*", i)
        if j < 0:
            out.append(src[i:]); break
        out.append(src[i:j])
        k = src.find("*/", j)
        if k < 0:
            break
        i = k + 2
    return "".join(out)


def _between(src, start, end):
    """The text between two REAL anchors, or None. Never a fixed-size window. -> str|None"""
    i = src.find(start)
    if i < 0:
        return None
    j = src.find(end, i + len(start))
    return src[i:j + len(end)] if j > i else None


def _code_of(fn_name):
    """One function's CODE, with its docstring and comments removed.

    ⚠⚠ THIS EXISTS BECAUSE THE LAW BELOW WAS FOOLED BY ITS OWN SUBJECT'S PROSE — the FOURTH time
    in one session. `river_mouth`'s docstring explains, correctly and at length, why it must never
    reach into `reel_router`; a bare `assertNotIn("reel_router", blk)` matched THAT SENTENCE and
    reported the function as violating the rule its own comment states.

    A guard that greps prose grades prose. Every one of the four had the same shape and the same
    fix, which is why this is now a helper rather than a fourth ad-hoc patch.
    [[source-reading-guard]] [[sabotage-is-usually-the-wrong-one]]
    """
    tree = ast.parse(SRC)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == fn_name:
            body = list(node.body)
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                body[0].value.value = ""
            fn = ast.Module(body=[node], type_ignores=[])
            out = ast.unparse(fn) if hasattr(ast, "unparse") else ""
            return re.sub(r"(?m)#[^\n]*", "", out)
    return None


def _river_payload():
    """The /api/river success payload, anchored at BOTH ends. [[source-reading-guard]]

    ⚠⚠ v2795 — IT SAID "ANCHORED AT BOTH ENDS" AND THE OPENING WAS A CHARACTER COUNT. The old cut
    was `SRC[i:i + 9000]`, and the route grew: MEASURED, `self._json(200, {` now sits at **+9145**
    from `if path == "/api/river"`. It fell 145 characters past the window, `find` returned -1,
    and this helper returned None — so `test_the_guard_can_find_the_route_AT_ALL` failed and the
    two real laws ERRORED on `None`. The route was perfectly fine. Nothing about the river broke;
    the guard's REACH did, and it shrank a little more every time somebody documented the route.

    That is the same defect this repo has now paid for repeatedly: a fixed-size source window
    measures the size of my guess, not the file. The end anchor is the NEXT route's `if path ==`,
    because that is the real boundary of this handler and it cannot drift with prose.
    [[source-reading-guard]] [[feedback-suspect-the-instrument]]
    """
    i = SRC.find('if path == "/api/river"')
    if i < 0:
        return None
    # ⚠ BOTH ENDS REAL. The handler ends where the next one begins; if this is the last route in
    # the chain there is no next `if path ==`, and running to end-of-file is correct, not a
    # fallback window.
    end = SRC.find('\n        if path == "', i + 1)
    blk = SRC[i:end if end > i else len(SRC)]
    # v3849: the route answers `{"ok": False, "computing": True, ...}` first while the plan is built beside the
    # request (a one-line 200). The SUCCESS payload is the multi-line one - its dict opens at the end of the line.
    k = blk.find("self._json(200, {\n")
    if k < 0:
        return None
    j = blk.find("except Exception", k)
    return blk[k:j if j > k else len(blk)]


class TheRiverHasAMouth(unittest.TestCase):

    def test_the_guard_can_find_the_route_AT_ALL(self):
        """⚠ A law that cannot find its subject passes having examined nothing."""
        self.assertIsNotNone(_river_payload(), "the /api/river success payload is gone or renamed")

    # ── ⚠⚠ THE LAW ────────────────────────────────────────────────────────────────────────────
    def test_the_mouth_is_ON_the_river_and_in_the_SUCCESS_branch(self):
        pay = _river_payload()
        self.assertIn('"mouth": river_mouth()', pay,
                      "the river reports no mouth, so the end of the river is invisible to every "
                      "surface — which is how 410 completed journeys read as zero")

    def test_the_mouth_reads_the_LEDGER_and_never_the_ROUTER(self):
        """⛔ THE BOUNDARY THIS FIX RESTS ON. reel_router.assert_independent_of_retention() exists
        so a living reel's position comes from its own reading evidence and never from a retention
        tag. Manufacturing TOMBSTONE inside the router would merge exactly those two questions."""
        blk = _code_of("river_mouth")
        self.assertIsNotNone(blk, "river_mouth is gone or unparseable")
        self.assertIn("_tombstone_path", blk, "the mouth no longer reads the tombstone ledger")
        for bad in ("reel_router", "_station_of", "STATIONS"):
            self.assertNotIn(bad, blk,
                             "river_mouth reaches into the router (%r) IN CODE. The mouth is a "
                             "retention fact and must not be manufactured as a station." % bad)
        # ⚠ prove the stripper stripped, or this law grades an empty string
        self.assertIn("def river_mouth", blk, "the code-only view lost the function")
        self.assertNotIn("Merging them would put a retention fact", blk,
                         "the docstring survived the strip, so this law is reading prose again")

    # ── ⚠ UNKNOWN IS NEVER A CONFIDENT ZERO ───────────────────────────────────────────────────
    def test_a_missing_ledger_is_UNKNOWN_not_zero_journeys(self):
        """"No tombstone file" is NOT "no reel ever finished". The file is untracked runtime state
        and can legitimately be absent on a fresh venue."""
        r = CA.river_mouth(path=os.path.join(HERE, "__no_such_tombstone_file__.json"))
        self.assertFalse(r.get("ok"), "a missing ledger reported a confident result")
        self.assertIsNone(r.get("n"), "a missing ledger reported n=%r instead of None" % r.get("n"))
        self.assertIn("NOT the same", str(r.get("why") or ""),
                      "the reason does not distinguish 'no record here' from 'nothing finished'")

    # ── ⚠ FIFO, AND WHAT AN UNDATED ROW DOES ──────────────────────────────────────────────────
    def test_it_is_FIFO_and_an_UNDATED_row_sorts_LAST(self):
        """He asked to watch "first in to first out". A row with no deletedTs cannot be placed in
        that order at all, and must not be allowed to head the queue by accident."""
        import json
        import tempfile
        rows = [{"reel": "b", "deletedTs": 200, "mb": 1},
                {"reel": "a", "deletedTs": 100, "mb": 1},
                {"reel": "?", "mb": 1},
                {"reel": "c", "deletedTs": 300, "mb": 1}]
        fd, p = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        try:
            io.open(p, "w", encoding="utf-8").write(json.dumps({"reels": rows}))
            r = CA.river_mouth(limit=10, path=p)
            got = [x["reel"] for x in r["recent"]]
            self.assertEqual(["a", "b", "c", "?"], got,
                             "not FIFO, or the undated row did not sort last: %r" % got)
            self.assertEqual(3, r["dated"], "dated count wrong")
            self.assertEqual(1, r["undated"],
                             "the undated row is not counted, so a reader cannot tell the timeline "
                             "is incomplete")
        finally:
            os.unlink(p)

    def test_the_totals_are_real_and_carry_their_denominator(self):
        r = CA.river_mouth(limit=1)
        if not r.get("ok"):
            self.skipTest("no tombstone ledger on this venue: %s" % r.get("why"))
        self.assertGreater(r["n"], 0, "the ledger reports zero journeys")
        self.assertEqual(r["n"], r["dated"] + r["undated"],
                         "dated + undated does not account for every row")

    # ── the comment that invited MY wrong conclusion must not stand ───────────────────────────
    def test_the_unreached_field_no_longer_implies_nothing_ever_finished(self):
        """`unreached` answers "which stations has the STAMP JOURNAL recorded" — narrower than its
        name. Beside counts.TOMBSTONE = 0 it invites exactly the conclusion I drew and had to
        retract, so the payload now says which question each field answers."""
        pay = _river_payload()
        self.assertNotIn("ROUTED and TOMBSTONE are both in\n                    # it today.", pay,
                         "the old comment still asserts TOMBSTONE has never been reached")
        self.assertIn("410", pay,
                      "the payload does not record the measurement that refuted the old reading")

    def test_it_still_parses(self):
        ast.parse(SRC)



class TheShelfTellsTheMouthTheSameWayTheLedgerDoes(unittest.TestCase):
    """★ v3270 — THE SAME FACT, TOLD TWO WAYS, ON ONE SCREEN, IN ONE GLANCE.

    GrokBot filed it from his NATIVE Linux seat (#180): *"River header still notes tombstone
    ledger would not answer (content otherwise populated)."*

    Measured on ONE `/api/river` payload the same minute:

        header (his Mac)   "453 closed out · 9.9 GB freed"
        station chip       "no reel has EVER reached DELETED — the river counts 0 visits"

    Both true to the field they read, and flatly contradictory to a person. A reel that reaches the
    MOUTH leaves the disk: it stops being something the router can station, so the stamp journal
    can never record it there. `control_app.river_mouth`'s own docstring records me drawing that
    wrong conclusion once and having to retract it.

    And GrokBot's header read differently from mine for a REAL reason: `tv/reel_tombstones.json`
    is runtime state, gitignored (.gitignore:164), so his fresh Linux checkout has none. The
    backend already said the careful thing —

        "there is no tombstone ledger on this venue - retention has no record here,
         which is NOT the same as no reel having ever finished"

    — and the header threw that whole sentence away for the words "would not answer", which
    describe a malfunction. Absent is not broken, and neither is zero.
    [[label-outlived-referent]] [[unknown-stays-unknown]] [[zero-needs-a-denominator]]
    """

    def _chip(self):
        blk = _between(_js_only(UI), "var _isMouth = (SHELF_MOUTH_STATION",
                       "not a reason to hide the station';")
        self.assertIsNotNone(blk, "the mouth-aware station branch is gone or renamed")
        return blk

    def test_the_chip_asks_the_LEDGER_before_saying_a_terminus_was_never_reached(self):
        blk = self._chip()
        self.assertIn("SHELF_MOUTH", blk,
                      "the chip still decides 'never reached' from the stamp journal alone, so it "
                      "contradicts the ledger figure printed in the header beside it")
        self.assertIn("LEAVES THE DISK", blk,
                      "it does not say WHY the journal is silent about the mouth, so the next "
                      "reader draws the same wrong conclusion")

    def test_an_UNREADABLE_ledger_is_UNKNOWN_and_never_NEVER_REACHED(self):
        """⚠ GrokBot's seat exactly: no ledger on this venue. The chip must not convert that into
        'no reel has ever finished'."""
        blk = self._chip()
        self.assertIn("UNKNOWN, not zero", blk,
                      "a venue with no retention ledger reads as a terminus nothing ever reached")

    def test_a_NON_mouth_station_keeps_the_original_sentence(self):
        """⚠ the guard against over-reach: only the station the RIVER calls the mouth gets the
        ledger treatment. Every other empty station keeps its actionable 'never reached'."""
        blk = self._chip()
        self.assertIn("no reel has EVER reached", blk,
                      "the original sentence is gone, so an ordinary unreached station can no "
                      "longer be reported as the actionable fact it is")

    def test_WHICH_station_is_the_mouth_comes_from_the_PAYLOAD(self):
        """⚠ [[copy-drift]] — a literal "TOMBSTONE" in the shelf is a second copy of a name
        `river.py` owns, and the two drift the day a station is renamed."""
        ui = _js_only(UI)
        self.assertIn("d.vocab && d.vocab.mouth", ui,
                      "the shelf does not read the river's own name for the terminus")
        blk = self._chip()
        self.assertNotIn("'TOMBSTONE'", blk,
                         "the mouth station is hard-coded in the chip instead of read from vocab")

    def test_the_HEADER_quotes_the_backends_reason_instead_of_calling_it_a_malfunction(self):
        ui = _js_only(UI)
        blk = _between(ui, "SHELF_MOUTH.ok === false", "mouthTxt = ' \u00b7 ' + SHELF_MOUTH.n")
        self.assertIsNotNone(blk, "the header's unreadable-ledger branch is gone or renamed")
        self.assertIn("SHELF_MOUTH.why", blk,
                      "the header invents its own wording instead of quoting the backend, which "
                      "already distinguishes an ABSENT ledger from a broken one")
        self.assertNotIn("would not answer", blk,
                         "the header still calls a venue with no ledger a malfunction")


RED_PROOF = [
    {
        'why': 'The gate\'s central law asserts the end of the river is actually ON the /api/river SUCCESS payload: test_the_mouth_is_ON_the_river_and_in_the_SUCCESS_branch reads the handler block between \'if path == "/api/river"\' and the next route, then requires \'"mouth": river_mouth()\' inside it. The tamper deletes the REAL THING — the call that computes the mouth — while leaving the key, the comments, the docstrings and the file\'s parseability untouched, so the payload reports mouth=None and 410 completed journeys become invisible to every surface, exactly the defect the gate exists to catch. It is not a comment (the anchor is executable code inside the dict literal), not a mention inside a message string (the law\'s own failure message lives in the test file, not the target), and not a shared constant (the law reads the payload text, not river_mouth\'s definition — the function and its ledger reads are untouched, so the sibling law test_the_mouth_reads_the_LEDGER_and_never_the_ROUTER stays green and cannot mask the red).  MEASURED: untampered OK (skipped=1) — Ran 8 tests in 0.234s, exit 0. The one skip is test_the_totals_are_real_a; tampered (all 1) FAILED (failures=1, skipped=1), exit 1 — Ran 8 tests. Exactly one law red.; reddened law test_the_river_has_a_mouth.TheRiverHasAMouth.test_the_mouth_is_ON_the_; ALONE FAILS ALONE. `python3 -m unittest test_the_river_has_a_mouth.TheRiverHasAMouth.test_the_mouth_is_ON_the_river_.',
        'file': 'control_app.py',
        'find': '"mouth": river_mouth(),',
        'replace': '"mouth": None,',
        'matches': 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
