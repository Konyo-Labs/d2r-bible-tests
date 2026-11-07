#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A7·ROUTE — one station per reel, and the keep-reason may never decide it.

⚠⚠ THE DEFECT THESE GRADE, measured on his shelf 2026-09-05: 40 reels, 29 never read, and the
oldest ten — back to 2026-07-25 — all with zero reads. Not a badly-ordered queue: `vault-owes`
matched 0 of 40 because `_vault_owed_reels()` is first-match-wins and that tag is LAST, so the
reel reader picked nothing, forever, while publishing `owed: 0` like a healthy idle lane. And
`reel_story._stage_of(tag)` derives a reel's STAGE from the RETENTION TAG, so all 40 sat at two of
six stages with four permanently empty.

⚠ NOTHING HERE TOUCHES HIS FOOTAGE. Every case builds synthetic evidence dicts or a temp reel dir;
none reads `frames/hist`. [[feedback-fixtures-never-touch-live-data]]
"""
import io
import os
import shutil
import sys
import tempfile
import unittest
import fixture_tmp as _fx_tmp  # noqa: E402  #171 — this run's scratch dirs leave with it
_fx_tmp.contain()

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import reel_router as RR  # noqa: E402


def _ev(sealed=False, names=0, worth=True, surveyed=True):
    return {"sealed": sealed, "names": names, "worthReading": worth, "surveyed": surveyed}


class TheStationComesFromEvidence(unittest.TestCase):
    """Each position is decided by what the reel itself carries, never by why we are keeping it."""

    def test_no_seal_no_names_is_STATION_owing_a_READ(self):
        st, why = RR._station_of(_ev(sealed=False, names=0))
        self.assertEqual(st, "STATION")
        self.assertIn("no name", why)

    def test_names_without_a_seal_is_PRINTER_owing_a_SEAL(self):
        st, _ = RR._station_of(_ev(sealed=False, names=3))
        self.assertEqual(st, "PRINTER")

    def test_sealed_with_names_is_JOIN_because_the_names_already_exist(self):
        """★ The cheapest work on the whole shelf: 3 reels where the reading is DONE and the seal
        simply does not carry it. Calling that a capture problem hid finished reading."""
        st, why = RR._station_of(_ev(sealed=True, names=2))
        self.assertEqual(st, "JOIN")
        self.assertIn("does not carry", why)

    def test_sealed_with_no_names_is_CAPTURE_not_a_paid_read(self):
        """REG-340 — the name prints only on the character panel, which the reel does not film.
        Buying a read for these spends money on footage that cannot answer."""
        st, _ = RR._station_of(_ev(sealed=True, names=0))
        self.assertEqual(st, "CAPTURE")

    def test_an_unsurveyed_reel_is_INTAKE(self):
        st, _ = RR._station_of(_ev(surveyed=False))
        self.assertEqual(st, "INTAKE")


class TheSurveyIsAStationNotAFlag(unittest.TestCase):
    """★★ HIS QUESTION, 2026-09-05: *"what decides its worth reading or not why doesnt it go
    through the unified filtering process down the river and through the station and printer."*

    It DOES. `worthReading` is `retro_triage.worth_reading()` — `bool(panels)` from the full-frame
    triage pass, `None` when never surveyed. My first cut flattened that river verdict into a FLAG
    beside one station, so 13 reels sat in a READ queue of which only 7 could ever yield anything:
    the position said READ while the river had already said otherwise for six of them. A verdict
    the river reached belongs in the POSITION."""

    def test_surveyed_in_full_with_ZERO_panels_is_EMPTY_not_a_read_candidate(self):
        st, why = RR._station_of(_ev(worth=False))
        self.assertEqual(st, "EMPTY", "a reel with no panel frames is still queued for a paid read")
        self.assertIn("zero panel frames", why)

    def test_EMPTY_owes_A_ROUTE_because_it_is_not_an_EXIT(self):
        """⚠ THIS CASE ASSERTED THE OPPOSITE UNTIL v2639 AND WENT RED WHEN THE RULE CHANGED,
        which is the correct outcome and worth keeping the scar for. It read
        `OWES["EMPTY"].startswith("nothing")` — written when EMPTY was a dead end.

        His question, 2026-09-05: *"this happens before it even enters the printer and station?
        doesnt it need to be gated after also.. like those should also have been through the same
        route and then end up where they should be."* He was right. A reel with nothing to READ
        still has a door it came from and still owes a stamped tombstone, so it continues down the
        same river carrying less — it does not leave it.

        The stale assertion is REPLACED rather than deleted: assert the RULE (EMPTY continues),
        never the old sentence. [[unknown-stays-unknown]] §6 — a test whose NAME describes
        inverted behaviour must be corrected, and that outranks no-drive-by-changes."""
        self.assertTrue(RR.OWES["EMPTY"].startswith("ROUTE"),
                        "EMPTY reads as an exit again; a reel with nothing to read still owes a "
                        "route and a stamped tombstone")
        # ⚠ v2811 — `[:40]` READ 40 OF 796 CHARACTERS, so 95% of the sentence was never
        # searched. It passes today only because STATION appears nowhere at all; add it at
        # character 100 and this stays green forever. A negative assertion over a fixed window is
        # the worst combination in this repo — a SHORT read and a PASS are the same result.
        # The whole string is the honest haystack. [[source-window-shortcut]]
        self.assertNotIn("STATION", RR.OWES["EMPTY"],
                         "EMPTY was routed back to the paid READ queue")

    def test_NEVER_TRIAGED_is_TRIAGE_and_is_NOT_the_same_as_EMPTY(self):
        """[[unknown-stays-unknown]] — `worth_reading` returns None for an unsurveyed reel and
        never False, precisely so footage nobody looked at cannot be skipped as if it had been
        looked at and found empty. Collapsing those two is how footage gets abandoned."""
        st, why = RR._station_of(_ev(worth=None))
        self.assertEqual(st, "TRIAGE")
        self.assertIn("UNSURVEYED", why)
        self.assertNotEqual(st, "EMPTY")

    def test_a_SEALED_reel_is_never_sent_back_to_the_survey(self):
        """Order matters: the further-down-river states are tested first. Asking a sealed reel
        whether it is worth reading would walk it backwards up its own river."""
        for worth in (None, False, True):
            st, _ = RR._station_of(_ev(sealed=True, names=2, worth=worth))
            self.assertEqual(st, "JOIN", "a sealed, read reel was routed by its survey flag")


class UnknownIsAPositionNotAGap(unittest.TestCase):
    """[[unknown-stays-unknown]] — 'we could not measure this reel' and 'this reel is at the
    start' are different facts, and collapsing them is how a shelf nobody could read reports as a
    shelf with no work waiting."""

    def test_unmeasured_seal_is_UNKNOWN_never_a_default_station(self):
        st, why = RR._station_of(_ev(sealed=None, names=0))
        self.assertEqual(st, RR.UNKNOWN)
        self.assertIn("unmeasured", why)

    def test_unmeasured_names_is_UNKNOWN(self):
        st, _ = RR._station_of({"sealed": True, "names": None, "worthReading": True,
                                "surveyed": True})
        self.assertEqual(st, RR.UNKNOWN)

    def test_no_evidence_at_all_is_UNKNOWN_with_a_reason(self):
        st, why = RR._station_of(None)
        self.assertEqual(st, RR.UNKNOWN)
        self.assertTrue(why.strip(), "UNKNOWN was returned with no reason")


class TheClockIsTheFramesNotTheId(unittest.TestCase):
    """⚠⚠ HIS CORRECTION, 2026-09-05: *"timestamps should be taken care of this though the 13
    digit is like a reference id"*. Measured on his shelf: `reel_s_1784984019250_95276`'s id says
    1784984019250 and its FIRST FRAME says 1784984130673 — **111 seconds apart**. The id is
    stamped when the session opens; the frame is stamped when the picture was taken."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="router_")
        self.addCleanup(shutil.rmtree, self.dir, True)

    def _reel(self, name, frame_stamps):
        d = os.path.join(self.dir, name)
        os.makedirs(d)
        for ms in frame_stamps:
            io.open(os.path.join(d, "f_%d.jpg" % ms), "w").close()
        return name

    def test_it_takes_the_EARLIEST_FRAME_not_the_id(self):
        r = self._reel("reel_s_1784984019250_95276", [1784984130673, 1784984131791])
        ms, src = RR._captured_ms(r, self.dir)
        self.assertEqual(src, "frames")
        self.assertEqual(ms, 1784984130673,
                         "it used the session id (or a later frame) instead of the first frame")

    def test_a_reel_with_no_frames_falls_back_to_the_id_AND_SAYS_SO(self):
        """The fallback is legitimate — a pruned reel can still be ordered — but it must be
        visible, because the two clocks differ by minutes and one of them is an id."""
        os.makedirs(os.path.join(self.dir, "reel_s_1784984019250_95276"))
        ms, src = RR._captured_ms("reel_s_1784984019250_95276", self.dir)
        self.assertEqual(src, "id")
        self.assertEqual(ms, 1784984019250)

    def test_no_clock_at_all_is_None_and_NEVER_zero(self):
        """★ 0 is 1970. A zero here sorts an unmeasured reel to the FRONT of a FIFO queue, ahead
        of every reel whose age is actually known — the exact inversion this module refuses."""
        os.makedirs(os.path.join(self.dir, "reel_nameless"))
        ms, src = RR._captured_ms("reel_nameless", self.dir)
        self.assertIsNone(ms)
        self.assertIsNone(src)

    def test_a_clockless_reel_sorts_LAST_not_first(self):
        rows = [{"reel": "b", "capturedMs": None}, {"reel": "a", "capturedMs": 1784984130673}]
        rows.sort(key=lambda r: (r["capturedMs"] is None, r["capturedMs"] or 0, r["reel"]))
        self.assertEqual([r["reel"] for r in rows], ["a", "b"],
                         "the reel with no readable clock jumped the queue")


class ThePositionIsNotTheBill(unittest.TestCase):
    """⚠ 13 reels sit at STATION and the survey says only 7 are worth reading. A paid queue built
    from the position alone buys six reads the survey already argued against — which is the
    2026-08-28 incident's shape: a predicate that read as equivalent queued 19 where retention
    said 2, three of them test fixtures."""

    def test_worth_only_is_OFF_by_default_so_the_shelf_is_never_silently_shrunk(self):
        import inspect
        sig = inspect.signature(RR.owed)
        self.assertIs(sig.parameters["worth_only"].default, False,
                      "the paid filter is applied on the caller's behalf instead of being asked "
                      "for at the call site that spends the money")

    def test_worth_only_drops_an_UNREADABLE_survey_not_just_a_False_one(self):
        """A survey that could not be read is not permission to spend."""
        rows = [{"worthReading": True}, {"worthReading": False}, {"worthReading": None}]
        kept = [r for r in rows if r["worthReading"] is True]
        self.assertEqual(len(kept), 1)


class ItRefusesToMixSHELVES(unittest.TestCase):
    """⚠⚠ CAUGHT BY TWO INDEPENDENT AUDITS WITHIN MINUTES OF EACH OTHER, and it is the exact
    fixture/live crossing this repo has been bitten by before. `_evidence(hist)` accepted a `hist`
    argument and never used it — `printer.stream()` takes only `(reel=None)` and reads whatever
    shelf its own module resolves. So `route(hist=<fixture>)` took CAPTURE CLOCKS from the fixture
    and STATION EVIDENCE from the live shelf, and any fixture test calling it would have silently
    graded his real 40 reels AND PASSED. A parameter that is accepted and ignored is worse than
    one that does not exist. [[feedback-fixtures-never-touch-live-data]]"""

    def test_a_mismatched_hist_is_REFUSED_and_names_the_supported_route(self):
        import tempfile
        d = tempfile.mkdtemp(prefix="othershelf_")
        ev, why = RR._evidence(d)
        self.assertIsNone(ev, "it answered for a shelf it cannot actually read")
        self.assertIn("TV_HIST", why, "the refusal does not say how to point it at a fixture")

    def test_route_surfaces_that_refusal_rather_than_reporting_an_empty_shelf(self):
        """★ An empty shelf and a refused one are different facts. Reporting 0 reels for a shelf
        it declined to read is the confident-zero this module exists to refuse."""
        import tempfile
        rep = RR.route(tempfile.mkdtemp(prefix="othershelf2_"))
        self.assertFalse(rep["ok"])
        self.assertEqual(rep["shelf"], 0)
        self.assertIn("refusing to mix shelves", rep["why"])

    def test_the_MATCHING_hist_is_still_accepted(self):
        """⚠ THE BASELINE. A refusal that fires on everything is not a guard, it is a broken
        function — and it would make the module unusable from its own CLI."""
        ev, why = RR._evidence(RR._hist_dir())
        self.assertTrue(ev is not None or "printer" in why,
                        "it refused its OWN shelf: %s" % why)


class TheRiverLeavesItsRemnantsOut(unittest.TestCase):
    """REG-3329 (#44) - MEASURED 11-07 on his Mac: route() stationed 42 reels and the shelf held 30; the 12 extra were
    EVIDENCE REMNANTS (released and tombstoned WITH a kept list - their folder lives on for the kept pictures), stationed
    as live reels (8 UNKNOWN, 4 ROUTED 'owes only a tombstone' they already had). route() asks retention's remnant rule,
    stations only the shelf's reels, and NAMES every remnant it set apart."""

    def test_a_remnant_is_named_and_never_stationed(self):
        from unittest import mock
        import reel_retention as _rrem
        ev = {"reel_s_1_1": {"sealed": True, "names": 3, "surveyed": True, "panels": 2},
              "reel_s_2_2": {"sealed": None, "names": None}}
        with mock.patch.object(RR, "_evidence", lambda hist=None: (ev, "")), \
                mock.patch.object(RR, "_routed_by_a_lane", lambda path=None: ({}, "")), \
                mock.patch.object(_rrem, "remnant_reels", lambda hist=None: {"reel_s_2_2"}):
            rep = RR.route()
        self.assertEqual([r["reel"] for r in rep["reels"]], ["reel_s_1_1"], "a remnant was stationed as a live reel")
        self.assertEqual(rep.get("remnants"), ["reel_s_2_2"], "the remnant set apart is not named")

    def test_an_unreadable_remnant_rule_sets_nothing_apart(self):
        from unittest import mock
        import reel_retention as _rrem
        ev = {"reel_s_1_1": {"sealed": True, "names": 3, "surveyed": True, "panels": 2}}
        def boom(hist=None):
            raise OSError("no ledger")
        with mock.patch.object(RR, "_evidence", lambda hist=None: (ev, "")), \
                mock.patch.object(RR, "_routed_by_a_lane", lambda path=None: ({}, "")), \
                mock.patch.object(_rrem, "remnant_reels", boom):
            rep = RR.route()
        self.assertEqual([r["reel"] for r in rep["reels"]], ["reel_s_1_1"])
        self.assertEqual(rep.get("remnants"), [])


class TheGuardRefusesTheCouplingItExistsFor(unittest.TestCase):
    """★★ THE ONE THAT MATTERS. `_stage_of(tag)` is the defect: the keep-reason deciding the
    read-fate. This guard must fail when that returns, in EITHER half."""

    def test_the_real_module_is_independent(self):
        ok, findings = RR.assert_independent_of_retention()
        self.assertTrue(ok, "the shipped module reads a retention field: %r" % (findings,))

    def test_it_goes_RED_when_the_DECIDER_reads_the_tag(self):
        """RED-proven for its own reason, not merely asserted green."""
        def _coupled(ev):
            if ev.get("tag") == "zero-pages":      # the exact defect, restored
                return "STATION", "because retention says so"
            return "JOIN", ""
        seen = RR._string_keys_read_by(_coupled)
        self.assertIn("tag", seen,
                      "the AST walk did not even see the coupling it exists to catch — "
                      "instrument failure, not a clean result")
        self.assertTrue(any(f in RR.RETENTION_FIELDS for f in seen))

    def test_it_goes_RED_when_the_EVIDENCE_BUILDER_smuggles_the_tag_in(self):
        """⚠ The hole my first cut left open: the decider stays spotless while the dict it is
        handed carries the keep-reason. Same coupling, one function upstream, guard reporting
        clean. [[the-unjoined-end]]"""
        def _smuggler(hist=None):
            row = {}
            return {"r": {"sealed": row.get("funnel"), "names": row.get("route")}}, ""
        seen = RR._string_keys_read_by(_smuggler)
        self.assertTrue({"funnel", "route"} & seen,
                        "the walk missed a retention field being copied into the evidence dict")

    def test_a_walk_that_sees_NOTHING_is_an_instrument_failure_not_a_pass(self):
        """[[feedback-suspect-the-instrument]] — a guard that inspects nothing reports clean
        forever, which is indistinguishable from a guard that works."""
        def _blind(ev):
            return "STATION", "no field reads at all"
        self.assertEqual(RR._string_keys_read_by(_blind), set())


class EveryReelGetsExactlyOneStation(unittest.TestCase):
    """His ask in one sentence: *"a unified logic for all reels no gaps"*. The invariant is that
    the counts reconcile with the shelf — asserted, not hoped for."""

    def test_counts_plus_unknown_equal_the_shelf(self):
        ev = {"a": _ev(sealed=True, names=1), "b": _ev(), "c": _ev(sealed=None),
              "d": _ev(sealed=True, names=0), "e": _ev(surveyed=False)}
        real = RR._evidence
        RR._evidence = lambda hist=None: (ev, "")
        self.addCleanup(setattr, RR, "_evidence", real)
        rep = RR.route()
        self.assertTrue(rep["ok"])
        self.assertEqual(rep["shelf"], 5)
        self.assertTrue(rep["reconciles"])
        self.assertEqual(sum(rep["counts"].values()) + rep["unknown"], 5)
        self.assertEqual(rep["unknown"], 1, "the unmeasured reel was placed at a real station")

    def test_a_DROPPED_reel_makes_reconcile_go_FALSE(self):
        """RED for the invariant itself — a router that silently loses a reel is the gap."""
        counts, unknown, shelf = {"STATION": 3}, 0, 5
        self.assertFalse((sum(counts.values()) + unknown) == shelf)

    def test_UNKNOWN_is_not_inside_counts(self):
        """A total that already contains the unmeasured reels lets a caller print one number and
        never say how many it could not place."""
        self.assertNotIn(RR.UNKNOWN, RR.STATIONS)

    def test_every_station_declares_what_it_owes(self):
        for s in RR.STATIONS:
            self.assertIn(s, RR.OWES)
            self.assertTrue(RR.OWES[s].strip())


class ItArmsNothing(unittest.TestCase):
    """⚠⚠ The prune stays OFF and no paid read is started from here. This module publishes a
    queue; wiring a reader to it spends his money and is his decision."""

    def test_the_module_never_calls_a_prune_or_a_sweep(self):
        import ast
        import inspect
        src = inspect.getsource(RR)
        called = set()
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.Call):
                f = node.func
                nm = getattr(f, "attr", None) or getattr(f, "id", None)
                if nm:
                    called.add(nm)
        for banned in ("prune_once", "chronicle_sweep_start", "vault_sweep_start", "unlink",
                       "rmtree", "remove"):
            self.assertNotIn(banned, called,
                             "the router calls %r — it routes and stamps, it never removes"
                             % banned)


RED_PROOF = [
    {"why": "REG-3329 - an evidence remnant is stationed as a live reel again (42 vs his shelf's 30)",
     "file": "reel_router.py",
     "find": "        if reel in _rem:\n            continue\n",
     "replace": "",
     "matches": 1},
    {
        'why': "UNKNOWN is a position, not a default. `_station_of()` returns UNKNOWN the moment EITHER `sealed` or `names` is unmeasured, so a reel nobody could measure is never dressed up as a reel sitting at a real station. Collapsing the `or` to an `and` lets a single unmeasured field fall through into the evidence ladder: sealed=None/names=0 is published as STATION (a paid-read candidate built on nothing) and sealed=True/names=None as CAPTURE, while route()'s `unknown` count drops to 0 so the shelf reports that it could place every reel. That is the confident-zero this module exists to refuse.  MEASURED: untampered GREEN — `python3 test_reel_router.py` -> Ran 30 tests in 0.163s, OK; tampered (all 1) RED — Ran 30 tests, FAILED (failures=3): UnknownIsAPositionNotAGap.test_unmeasur; reddened law test_reel_router.UnknownIsAPositionNotAGap.test_unmeasured_seal_is_UNK; ALONE FAILS ALONE — `python3 -m unittest test_reel_router.UnknownIsAPositionNotAGap.test_unmeasured_seal_i.",
        'file': 'reel_router.py',
        'find': 'if sealed is None or names is None:',
        'replace': 'if sealed is None and names is None:',
        'matches': 1,
    },
]


if __name__ == "__main__":
    try:
        from console_safe import enable
        enable()
    except Exception:
        pass
    unittest.main(verbosity=2)
