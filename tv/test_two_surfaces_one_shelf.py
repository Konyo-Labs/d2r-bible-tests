"""THE STRIP AND THE SHELF DRAW ONE SHELF, SO THEY MAY NOT PRINT TWO NUMBERS.

⚠⚠ WHY THIS LAW EXISTS, MEASURED ON HIS CONSOLE 2026-09-10 (#58).
`_shelf_visible()` has subtracted the 8 fixture reels from /api/reel_story since v2877, under his
ruling: *"no need to even mention those 8 anywhere visually on the console."* The RIVER STRIP — the
other surface drawn from the same shelf, two panels up the same page — went on counting all 24:

    strip header    the river · 24 reel(s) on the shelf
    the shelf below 16 rows
    INTAKE 6 · PRINTER 2 · CAPTURE 12 · TOMBSTONE 4     (2 · 1 · 4 · 1 of them fixtures)

One shelf, two answers, and nothing on screen saying which was his. That is [[copy-drift]] wearing
the costume this repo keeps re-tailoring: a rule applied at ONE of the places that draws the thing.

⚠ SO THE LAW IS NOT "the strip subtracts 8". It is that the subtraction happens ON THE REPORT, once,
above every figure derived from it — because `shelf`, each lane's `count`, each `byStation` cell and
`reconciles` are all derived from `rep`, and a fix that patched the OUTPUT would be four separate
chances to miss one. Each assertion below names a figure that must move by itself.

⚠ AND THE ROSTER MUST NOT BE FILTERED. roster() decides a reel has CLOSED OUT by its ABSENCE from
the walk, so handing it the filtered report would read all 8 hidden reels as finished — hidden from
the shelf and then announced in TOMBSTONE and in `closed`. Hidden means UNSEEN, never FINISHED.

⚠ NO FOOTAGE, BY CONSTRUCTION. Every reel below is synthetic and roster() is stubbed, so this law
measures the same thing on his Mac and on a CI runner that has no reels at all — the failure mode
[[feedback-blind-fixture-green-gate]] is named for. [[zero-needs-a-denominator]]
"""
import ast
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import river_lanes as RL   # noqa: E402

# ⚠ NON-ASCII IN THE VERDICT MEANS STDOUT MUST BE MADE SAFE FIRST. On a non-UTF-8 console this
# file crashes while REPORTING, so a clean tree exits non-zero — the gate's own output is the
# thing that breaks. test_control enforces it across every CLI in this tree.
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()


def _rep(hidden_ids=()):
    """A synthetic router report: 6 reels over four lanes, 2 of them 'fixtures'."""
    reels = [
        {"reel": "reel_keep_a", "station": "STATION"},
        {"reel": "reel_hide_a", "station": "STATION"},
        {"reel": "reel_keep_b", "station": "PRINTER"},
        {"reel": "reel_keep_c", "station": "CAPTURE"},
        {"reel": "reel_hide_b", "station": "CAPTURE"},
        {"reel": "reel_keep_d", "station": "ROUTED"},
    ]
    return {"ok": True, "reels": reels, "shelf": len(reels), "unknown": 0, "why": ""}


class _StubRoster(object):
    """Captures the report roster() was handed, and answers with a readable closure ledger."""

    def __init__(self):
        self.seen = []

    def __call__(self, hist=None, path=None, rep=None):
        self.seen.append(rep)
        return {"ok": True, "rows": [], "closed": 99, "closedReadable": True, "closedWhy": ""}


class TwoSurfacesOneShelf(unittest.TestCase):

    def setUp(self):
        import reel_router
        self._real = reel_router.roster
        self.stub = _StubRoster()
        reel_router.roster = self.stub

    def tearDown(self):
        import reel_router
        reel_router.roster = self._real

    # ── every figure moves, and each one is named separately ─────────────────────────────────
    def test_the_shelf_total_drops_by_exactly_what_was_hidden(self):
        base = RL.lanes(rep=_rep())
        cut = RL.lanes(rep=_rep(), hide={"reel_hide_a", "reel_hide_b"})
        self.assertTrue(base.get("ok") and cut.get("ok"), "the lanes refused to draw at all")
        self.assertEqual(base["shelf"], 6, "the fixture stopped describing the report it is built from")
        self.assertEqual(cut["shelf"], 4,
                         "the strip's own total still counts reels the shelf hides — this is the "
                         "24-over-16 defect exactly")
        self.assertEqual(cut.get("hidden"), 2, "the payload does not say how many it subtracted")

    def test_the_lane_counts_move_with_it(self):
        cut = RL.lanes(rep=_rep(), hide={"reel_hide_a", "reel_hide_b"})
        got = dict((l["name"], l["count"]) for l in cut["lanes"])
        self.assertEqual(got.get("INTAKE"), 1, "INTAKE still counts a hidden reel")
        self.assertEqual(got.get("CAPTURE"), 1, "CAPTURE still counts a hidden reel")
        self.assertEqual(got.get("PRINTER"), 1, "PRINTER lost a reel it should have kept")
        self.assertEqual(got.get("TOMBSTONE"), 1, "TOMBSTONE lost a reel it should have kept")

    def test_the_per_station_cells_move_too(self):
        """The lane count and its byStation breakdown are two figures, not one."""
        cut = RL.lanes(rep=_rep(), hide={"reel_hide_a", "reel_hide_b"})
        by = {}
        for l in cut["lanes"]:
            by.update(l.get("byStation") or {})
        self.assertEqual(by.get("STATION"), 1,
                         "the per-station cell still counts a hidden reel while the lane total "
                         "above it does not — one surface, two numbers, again")
        self.assertEqual(by.get("CAPTURE"), 1, "the CAPTURE cell still counts a hidden reel")

    def test_the_river_still_reconciles_after_the_cut(self):
        """A filter that leaves the lanes not adding up to the shelf has broken the river."""
        cut = RL.lanes(rep=_rep(), hide={"reel_hide_a", "reel_hide_b"})
        total = sum(l["count"] for l in cut["lanes"])
        self.assertEqual(total + cut["unknown"], cut["shelf"],
                         "the lanes and the shelf disagree after hiding: %s + %s != %s"
                         % (total, cut["unknown"], cut["shelf"]))
        self.assertTrue(cut["reconciles"], "reconciles went false on an intact river: %s"
                        % cut.get("why"))

    # ── hidden is not finished ───────────────────────────────────────────────────────────────
    def test_the_closure_roster_is_handed_every_reel(self):
        """roster() reads absence as closure, so a filtered report would resurrect the hidden 8
        as CLOSED OUT — the one place the ruling most obviously forbids."""
        RL.lanes(rep=_rep(), hide={"reel_hide_a", "reel_hide_b"})
        self.assertTrue(self.stub.seen, "roster() was never called, so this law measured nothing")
        got = self.stub.seen[-1]
        ids = {(r or {}).get("reel") for r in ((got or {}).get("reels") or [])}
        self.assertIn("reel_hide_a", ids,
                      "the closure roster was handed the FILTERED report — every hidden reel now "
                      "reads as closed out, and the console would hide them from the shelf and "
                      "then announce them in TOMBSTONE")
        self.assertEqual(len(ids), 6, "the roster saw %d reels, not the whole shelf" % len(ids))

    def test_hiding_does_not_move_the_closed_count(self):
        base = RL.lanes(rep=_rep())
        cut = RL.lanes(rep=_rep(), hide={"reel_hide_a", "reel_hide_b"})
        self.assertEqual(base.get("closed"), cut.get("closed"),
                         "hiding a reel that is ON DISK changed how many reels have CLOSED OUT")

    # ── an unknown filter hides nothing, and says nothing false ──────────────────────────────
    def test_no_filter_means_no_subtraction(self):
        """`hide=None` is 'this console could not establish the set'. It must leave the river
        whole rather than draw a filtered-looking river it never filtered."""
        for empty in (None, set(), frozenset()):
            r = RL.lanes(rep=_rep(), hide=empty)
            self.assertEqual(r["shelf"], 6, "hide=%r subtracted something" % (empty,))
            self.assertEqual(r.get("hidden"), 0,
                             "hide=%r reported a subtraction it did not make" % (empty,))

    # ── the joint: the endpoint must actually pass the set ───────────────────────────────────
    def test_the_river_endpoint_hands_the_hidden_set_to_the_lanes(self):
        """⚠ PARSED, NOT GREPPED. A filter built on both ends and never joined is this repo's most
        repeated defect, and it is invisible to any check that reads prose. [[plumbing-with-no-tap]]
        [[source-reading-guard]]"""
        src = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        tree = ast.parse(src)
        joined = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            f = node.func
            if not (isinstance(f, ast.Attribute) and f.attr in ("lanes", "lanes_shared", "lanes_last")):   # v3849 - the river reads lanes_last; lanes_shared stays the overlap door
                continue
            if any(k.arg == "hide" for k in (node.keywords or [])):
                joined.append(getattr(node, "lineno", 0))
        self.assertTrue(joined,
                        "no call to .lanes(hide=...) anywhere in control_app.py — the hidden set "
                        "is computed and never handed over, so the strip draws every fixture")

    def test_the_hidden_set_is_decided_once_and_refuses_when_it_cannot(self):
        """`shelf_hidden_reels()` must exist, must key on SHELF_HIDDEN_TAGS, and must return None —
        never an empty set — when the plan cannot be read. An empty set is a CLAIM."""
        src = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        tree = ast.parse(src)
        fn = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "shelf_hidden_reels":
                fn = node
        self.assertIsNotNone(fn, "shelf_hidden_reels() is gone — the two surfaces have no shared "
                                 "authority and are free to drift apart again")
        body = ast.dump(fn)
        self.assertIn("SHELF_HIDDEN_TAGS", body,
                      "shelf_hidden_reels() no longer keys on SHELF_HIDDEN_TAGS, so the strip and "
                      "the shelf can now hide DIFFERENT reels")
        returns_none = any(isinstance(n, ast.Return) and isinstance(n.value, ast.Tuple)
                           and isinstance(n.value.elts[0], ast.Constant)
                           and n.value.elts[0].value is None
                           for n in ast.walk(fn) if isinstance(n, ast.Return)
                           and isinstance(n.value, ast.Tuple) and n.value.elts)
        self.assertTrue(returns_none,
                        "shelf_hidden_reels() has no path returning None — an unreadable plan now "
                        "hands back an empty set, which CLAIMS nothing is hidden")

    def test_the_WITHHOLDING_says_why_even_when_it_SUCCEEDS(self):
        """★ EVERY FAILURE PATH ANSWERED CAREFULLY AND SUCCESS RETURNED `""`.

        `/api/river` shipped `hidden: 8, hiddenWhy: ""` — the console withheld eight of his reels
        and said nothing about why. Measured 2026-09-17: those 8 are exactly the `test-fixture`
        reels, which is exactly what he asked for (*"8 fixtures HIDDEN from a visual render just
        for data ... for the ai reads to work from"*). The thing was RIGHT AND SILENT, and a reader
        cannot tell a correct withholding from a broken one.

        ⚠ BEHAVIOURAL, NOT A SOURCE GREP, DELIBERATELY. Three laws in this session went green while
        the feature they guarded was dead, because they asserted a name appeared somewhere rather
        than that the code RAN. This one calls the function and reads what it actually returns.
        [[zero-needs-a-denominator]] [[the-unjoined-end]]
        """
        ca = self._ca() if hasattr(self, "_ca") else __import__("control_app")
        ids, why = ca.shelf_hidden_reels()
        if ids is None:
            self.assertTrue(
                (why or "").strip(),
                "the plan could not be read AND no reason was given — the one case that was "
                "already handled is now silent too")
            return
        self.assertTrue(
            (why or "").strip(),
            "%d reel(s) are withheld from every console surface with NO reason published. A "
            "number a reader cannot account for is indistinguishable from a bug." % len(ids))
        if ids:
            self.assertIn(str(len(ids)), why,
                          "the reason does not carry the COUNT it is explaining: %r" % why[:90])
            self.assertTrue(
                any(t in why for t in ca.SHELF_HIDDEN_TAGS),
                "the reason never names the tag the withholding is keyed on, so it cannot be "
                "checked against SHELF_HIDDEN_TAGS: %r" % why[:90])


class ThePrinterSpineCountsWhatTheShelfShows(unittest.TestCase):
    """THE THIRD SURFACE. Same shelf, same ruling, found by sweeping for siblings of REG-886.

    ⚠⚠ MEASURED on his shelf 2026-09-10: the printer spine is drawn from `stream()["counts"]`, an
    aggregate over every reel ON DISK, while `_shelf_visible()` had already cut the story's rows to
    16. ALL SEVEN STATIONS read 24 — in 24 · funnel 24 · template 24 · route 24 · extract 24 ·
    out 24 · tombstone "ON DISK 24" — directly beneath the handler's own sentence *"16 of 16
    reel(s) carry the printer's verdicts"*. A denominator and its own label, disagreeing, one line
    apart. [[zero-needs-a-denominator]] [[label-outlived-referent]]
    """

    ROWS = [
        {"reel": "reel_keep_a", "stations": {"in": {"say": "recorder"}, "out": {"say": "UNDECIDED"}}},
        {"reel": "reel_keep_b", "stations": {"in": {"say": "recorder"}, "out": {"say": "UNDECIDED"}}},
        {"reel": "reel_hide_a", "stations": {"in": {"say": "repair"}, "out": {"say": "UNDECIDED"}}},
    ]

    def test_the_counting_rule_has_a_name_the_endpoint_can_call(self):
        """The rule must live in the printer, not be re-tallied by whoever needs a subset."""
        import printer as PR
        self.assertTrue(callable(getattr(PR, "counts_for", None)),
                        "printer.counts_for() is gone — a caller wanting the visible subset must "
                        "now re-implement what a station 'said', which is a second opinion owned "
                        "by the wrong module")

    def test_a_subset_sums_to_the_subset(self):
        import printer as PR
        got = PR.counts_for(self.ROWS[:2], ["in", "out"])
        self.assertEqual(sum(got["in"].values()), 2,
                         "the station column does not sum to the rows it was given")
        self.assertEqual(got["in"], {"recorder": 2},
                         "the hidden reel's verdict is still in the tally: %s" % got["in"])
        self.assertEqual(PR.counts_for(self.ROWS, ["in"])["in"], {"recorder": 2, "repair": 1},
                         "counting every row no longer reproduces the whole-shelf tally")

    def test_a_missing_station_buckets_rather_than_vanishing(self):
        """A dropped row would stop the columns summing to the number of rows — the one property
        every reader of this spine relies on."""
        import printer as PR
        got = PR.counts_for(self.ROWS, ["in", "nosuchstation"])
        self.assertEqual(sum(got["nosuchstation"].values()), len(self.ROWS),
                         "rows vanished from a station they do not carry, so the columns no "
                         "longer sum to the shelf: %s" % got["nosuchstation"])

    def test_stream_itself_counts_with_it(self):
        """One rule, two callers — not one rule and a copy. [[copy-drift]]"""
        src = io.open(os.path.join(HERE, "printer.py"), encoding="utf-8").read()
        tree = ast.parse(src)
        inside_stream = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "stream":
                for n in ast.walk(node):
                    if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                            and n.func.id == "counts_for"):
                        inside_stream.append(n)
        self.assertTrue(inside_stream,
                        "stream() no longer calls counts_for() — the walk has gone back to its own "
                        "inline tally, so the spine and the subset are counted by two rules that "
                        "are free to drift apart")

    def test_the_endpoint_counts_only_the_reels_it_is_showing(self):
        """⚠ PARSED, NOT GREPPED. [[source-reading-guard]]"""
        src = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        tree = ast.parse(src)
        joined = [n for n in ast.walk(tree)
                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                  and n.func.attr == "counts_for"]
        self.assertTrue(joined,
                        "control_app.py never calls counts_for — printerCounts is back to the "
                        "whole-disk aggregate and the spine counts reels the shelf hides")



class OneWordMustNotCarryTwoNumbers(unittest.TestCase):
    """EVERY LANE IS NAMED AFTER A STATION IT CONTAINS, so the card shows one word twice.

    ⚠⚠ READ OFF HIS SCREEN, not off a fixture — grok bot capture at 1470x923, 2026-09-10:

        1 INTAKE      4        <- the LANE
          INTAKE  0            <- the STATION, same word, same card
        4 TOMBSTONE   3        <- the LANE
          TOMBSTONE 0          <- the STATION

    The strip ALREADY pays for this: there is a paragraph under the cards explaining why TOMBSTONE
    reads 0, and the closure chip carries its own `the ledger` label for the same reason. A figure
    that would be misread gets a word naming where it came from. `.shr-stlab` is that device applied
    to the row that needed it — nothing hidden, no number moved. [[label-outlived-referent]]
    """

    def _collisions(self):
        import river_lanes as RL
        import reel_router as RR
        sts = set(RR.STATIONS)
        return [n for n, s, w in RL.LANES if n in sts], list(RL.LANES)

    def test_the_collision_this_label_exists_for_is_real(self):
        """⚠ A ZERO NEEDS A DENOMINATOR. If no lane were named after a station, the caption would
        be decoration and this law would be asserting a habit. Count it. [[zero-needs-a-denominator]]"""
        hit, lanes = self._collisions()
        self.assertTrue(lanes, "river_lanes.LANES is empty, so this law measured NOTHING")
        self.assertEqual(len(hit), len(lanes),
                         "only %d of %d lane names are also station names — the premise of the "
                         "station caption has changed and the label should be re-judged, not kept "
                         "out of habit: %s" % (len(hit), len(lanes), hit))

    def test_the_chips_say_they_are_stations(self):
        """⚠ PARSED FROM THE RENDERER, COMMENTS STRIPPED — the comment above this markup quotes the
        very words it renders, so a law reading prose would pass on its own documentation. That has
        happened five times in this repo. [[source-reading-guard]]"""
        ui = io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()
        i = ui.find("function _shLanesRender")
        self.assertGreater(i, -1, "_shLanesRender is gone — the river strip has no renderer")
        d, j = 0, ui.index("{", i)
        end = j
        while end < len(ui):
            if ui[end] == "{":
                d += 1
            elif ui[end] == "}":
                d -= 1
                if d == 0:
                    break
            end += 1
        body = ui[i:end + 1]
        body = re.sub(r"/\*(?:.|\n)*?\*/", " ", body)
        body = re.sub(r"(?m)//.*$", " ", body)
        self.assertIn("shr-stlab", body,
                      "the lane card no longer says its chips are STATIONS, so the big number and "
                      "the chip under the same word are two figures with one name again")

    def test_the_label_is_styled_and_scoped(self):
        """An unstyled label is a bare word in the middle of a card; an unscoped one leaks."""
        ui = io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()
        self.assertIn("#th-shelfov .shr-stlab", ui,
                      "no rule styles .shr-stlab INSIDE #th-shelfov — it renders unstyled, or "
                      "worse, styled by something outside the shelf")



class EveryReelOnDiskIsAccountedFor(unittest.TestCase):
    """★ v3278 — THREE NUMBERS REACHED A SCREEN AND NOTHING RELATED THEM.

    He reported it as *"Shelf shows 13, disk holds 20"*, and his spec, in his own correction:
    *"not 8 fifo.. IN TOTAL i want to see only 8 reel session ... and obivously those 8 hidden
    fixtures are bakcend purpose also kept.. thats all 16 in total"*.

    MEASURED against `reel_retention.plan()` — **his 8 + 8 is already exactly right**:

        test-fixture          8   his 8 hidden fixtures
        recent                8   his 8 visible reels
        panels-never-banked   3   the VAULT still owes a bank
        eligible              1   the prune may release it
        ------------------------------------------------------
        on disk              20

    The river shows 8, the console's `onDisk` shows 12 (v2877's fixture filter moved every figure
    with it), the disk holds 20. Any two of those read as a contradiction while nothing published
    the third fact.

    ⚠ THE RED CONDITION IS THE SUM, NOT THE NUMBER. 20 is not wrong and 16 is not a target to
    enforce — reels pass through. What is wrong is a total whose parts do not add up, or a tag
    this console cannot name. [[zero-needs-a-denominator]] [[unknown-stays-unknown]]
    """

    @staticmethod
    def _plan(tags):
        return {"ok": True, "candidates": [], "kept": [{"reel": "r%d" % i, "tag": t}
                                                       for i, t in enumerate(tags)]}

    def _census(self, tags, ok=True):
        import control_app as ca
        import reel_retention as rr
        real = rr.plan
        rr.plan = (lambda *a, **k: self._plan(tags)) if ok else (lambda *a, **k: {"ok": False, "why": "nope"})
        try:
            return ca.reel_census()
        finally:
            rr.plan = real

    def test_the_parts_SUM_to_the_whole(self):
        c = self._census(["test-fixture"] * 8 + ["recent"] * 8 + ["panels-never-banked"] * 3 + ["eligible"])
        self.assertTrue(c["ok"], c.get("why"))
        self.assertTrue(c["sums"], "the census does not add up: %s" % c.get("why"))
        self.assertEqual(c["onDisk"], 20)
        self.assertEqual((c["his"], c["fixtures"], c["owed"], c["releasable"]), (8, 8, 3, 1))
        self.assertEqual(c["owedBy"], {"vault": 3},
                         "the owing LANE is not named, so 'waiting' says nothing actionable")

    def test_an_UNKNOWN_tag_is_NAMED_and_never_dropped(self):
        """⚠⚠ THE LAW THE WHOLE THING TURNS ON. Silently discarding a tag it does not recognise
        would make the census look exact and be wrong the first time a retention rule is added —
        a total that stops adding up without anybody being told."""
        c = self._census(["recent"] * 2 + ["some-future-rule"])
        self.assertEqual(c["onDisk"], 3)
        self.assertTrue(c["sums"], "an unrecognised tag broke the sum instead of being counted")
        self.assertEqual(c["other"], {"some-future-rule": 1},
                         "the unrecognised tag was dropped rather than named")
        self.assertIn("some-future-rule", c["why"], "the sentence hides the tag it could not place")

    def test_the_OWED_tags_come_from_the_ONE_map_not_a_private_copy(self):
        """⚠ `shelf_driver.OWED_BY` is the single tag->lane map. A second list inside the census is
        how the two drift the day a tag is added. [[copy-drift]]"""
        import shelf_driver as sd
        for tag, lane in sd.OWED_BY.items():
            c = self._census([tag])
            self.assertEqual(c["owed"], 1, "%r is in OWED_BY but the census does not count it" % tag)
            self.assertEqual(c["owedBy"], {lane: 1})

    def test_an_UNREADABLE_plan_is_UNKNOWN_not_an_empty_disk(self):
        c = self._census([], ok=False)
        self.assertFalse(c["ok"])
        self.assertIsNone(c["onDisk"], "an unreadable plan reported a COUNT, which invents a fact")

    def test_the_census_TRAVELS_on_the_river_payload(self):
        """⚠ v3279 — the doctor supervises the census, but the confusion he reported happens on the
        SHELF, where a count is on screen and its context is not. A census only the doctor can read
        cannot answer the question at the moment it is asked. [[the-unjoined-end]]

        ⚠ 2026-10-06 — DRIVEN, NOT PINNED. This read a 900-character window after the `mouth` line, and
        REG-1813's `riverKept` field pushed `"population"` out of it while the census still travelled.
        The route is driven now: /api/river through the real Handler over a scratch shelf, and
        `population` must be reel_census()'s own answer. [[source-reading-guard]]"""
        import shutil
        import tempfile
        from unittest import mock
        import control_app as ca
        import river_stamp as RVS
        d = tempfile.mkdtemp(prefix="census_travels_")
        self.addCleanup(shutil.rmtree, d, True)
        said = {"ok": True, "onDisk": 20, "his": 8, "fixtures": 8, "owed": 3, "releasable": 1, "sums": True,
                "why": "20 reel(s) on disk = 8 he sees + 8 hidden fixture(s) + 3 still owed + 1 the prune may release"}
        h = ca.Handler.__new__(ca.Handler)
        h.path = "/api/river"
        out = []
        h._json = lambda code, obj: out.append((code, obj))
        # v3849 — the route reads lanes_last and does not wait. An empty hide is the () key.
        # Plant the finished walk the stub used to return on the caller, so the census still
        # rides the success payload and this ask does not start a walk.
        import time
        walked = {"ok": True, "lanes": []}
        RL._LAST[()] = {"at": time.time(), "out": walked}
        try:
            with mock.patch.object(ca, "HIST_DIR", d), \
                    mock.patch.object(ca, "_RIVER_LAST", {"good": None, "fail": None}), \
                    mock.patch.object(RVS, "census", lambda *a, **k: {"ok": True, "counts": {}, "visits": {}, "reels": 0}), \
                    mock.patch.object(RVS, "stations", lambda: (("INTAKE", "ROUTED"), "")), \
                    mock.patch.object(RVS, "rows", lambda *a, **k: {"ok": True, "rows": [], "n": 0}), \
                    mock.patch.object(RL, "lanes", lambda *a, **k: dict(walked)), \
                    mock.patch.object(ca, "shelf_hidden_reels", lambda *a, **k: ([], "")), \
                    mock.patch.object(ca, "river_mouth", lambda *a, **k: {}), \
                    mock.patch.object(ca, "reel_census", lambda *a, **k: dict(said)), \
                    mock.patch.object(ca, "_river_labels", lambda: {}), \
                    mock.patch.object(ca, "_river_vocab_facts", lambda: {}):
                h.do_GET()
        finally:
            RL._LAST.pop((), None)
            RL._REFRESH_ON.discard(())
        self.assertEqual(len(out), 1, "premise: the river route answered once")
        code, body = out[0]
        self.assertTrue(body.get("ok"), "premise: the stubbed river computed: %r" % body.get("why"))
        self.assertEqual(body.get("population"), said,
                         "the river payload does not carry the population, so the shelf cannot say "
                         "why the disk holds more than he can see")

    def test_the_doctor_row_is_REGISTERED_and_reds_on_a_broken_sum(self):
        """⚠ a census nobody reads is [[the-unjoined-end]]. And it must go red on the one thing
        that makes every downstream figure suspect."""
        import console_doctor as D
        import control_app as ca
        self.assertIn("reel population", dict(D.CHECKS),
                      "the census is not registered with the doctor, so nothing supervises it")
        real = ca.reel_census
        ca.reel_census = lambda *a, **k: {"ok": False, "onDisk": 20, "sums": False,
                                          "why": "the parts do not add up: 19 accounted vs 20 on disk"}
        try:
            st, say = dict(D.CHECKS)["reel population"]()
        finally:
            ca.reel_census = real
        self.assertNotEqual(str(st).lower(), "ok",
                            "the doctor stayed green over a population that does not add up")
        self.assertIn("do not add up", say)


RED_PROOF = [
    {
        "why": "v3279 - the river payload stops carrying the census, so the shelf cannot say why the disk holds more than he sees",
        "file": "control_app.py",
        "find": "                    \"population\": reel_census(),\n",
        "replace": "                    \"population\": None,\n",
        "matches": 1,
    },
    {
        "why": "removing the report-level filter restores the strip that printed 24 over a shelf "
               "drawing 16",
        "file": "river_lanes.py",
        "find": '            out["hidden"] = len(_drop)',
        "replace": '            out["hidden"] = 0',
        "matches": 1,
    },
    {
        "why": "handing roster() the FILTERED report makes every hidden reel read as closed out — "
               "hidden from the shelf, then announced in TOMBSTONE",
        "file": "river_lanes.py",
        "find": "_ro = _rr2.roster(rep=rep_all)",
        "replace": "_ro = _rr2.roster(rep=rep)",
        "matches": 1,
    },
    {
        "why": "unjoining the endpoint from the filter: the hidden set is still computed, and the "
               "strip goes back to drawing every fixture",
        "file": "control_app.py",
        "find": "_lr = _RL.lanes_last(hide=_hide)",
        "replace": "_lr = _RL.lanes_last()",
        "matches": 1,
    },
    {
        "why": "putting the printer spine back on the whole-disk aggregate restores the seven "
               "stations reading 24 beside a shelf of 16",
        "file": "control_app.py",
        "find": "_PR.counts_for(_vis_rows, _p.get(\"stations\"))",
        "replace": "(_p.get(\"counts\") or {})",
        "matches": 1,
    },
    {
        "why": "returning stream() to its own inline tally means the spine and the visible subset "
               "are counted by two rules",
        "file": "printer.py",
        "find": '"rows": rows, "counts": counts_for(rows),',
        "replace": '"rows": rows, "counts": {},',
        "matches": 1,
    },
    {
        "why": "dropping the STATIONS caption: the lane's big number and the chip under the same "
               "word become two figures with one name again, on all four cards",
        "file": "control_ui.html",
        "find": "             + '<div class=\"shr-stlab\">stations</div>'\n",
        "replace": "",
        "matches": 1,
    },
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
