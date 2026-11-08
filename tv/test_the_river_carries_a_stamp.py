# -*- coding: utf-8 -*-
"""THE RIVER REMEMBERS — the gate on `river_stamp`, the only module in the family that WRITES.

MEASURED before this store existed. `reel_router.route()` answers where all 40 reels are, on every
call, and remembers nothing: `grep -rln river_stamp tv/` -> nothing, and no file in the tree held a
per-reel per-station history. So the console could say a reel was at CAPTURE and could not say
whether it had been there ten minutes or since July. His ask was the journey — *"synced from
station and down to tombstone"* — and the journey had no store.

=== WHY EACH LAW BELOW IS SHAPED THE WAY IT IS ===

1. APPEND-ONLY IS CHECKED BY AST, NOT BY PROMISE. A docstring saying "append-only" is a sentence;
   the file mode is the fact. `open(p, "w")` truncates BEFORE anything is computed and has already
   destroyed a multi-megabyte file in this tree once — here it would destroy every journey. The
   law walks the module's own AST for an open() whose mode contains "w", and separately requires
   the append call to exist and be REACHABLE. Text presence is not reachability: an append sitting
   under `if False:` leaves every string a grep looks for exactly where it was.

2. THE DEDUPE IS ON THE CURRENT STATION, AND THE RE-ENTRY LAW IS WHAT MAKES THAT TESTABLE. "Do not
   duplicate a row" has two readings and only one is honest. Global — one row per (reel, station)
   ever — silently erases every regression, and a regression is the most interesting thing a
   journey can hold; `reel_router.OWES["EMPTY"]` already documents that its verdict is REOPENABLE,
   so re-entry is a state this river is built to produce. So BOTH halves are pinned: a repeated
   stamp writes nothing, and a genuine return writes a row.

3. ORDER IS APPEND ORDER, AND THE LAW PROVES IT IS NOT A SORT. A row written with an `at` in the
   past must stay LAST. If `history()` ever sorted by the clock, two stamps in one millisecond or
   one clock step backwards would silently reorder a reel's life. The contradiction is published
   (`outOfOrder`) rather than resolved.

4. UNKNOWN IS THREE DIFFERENT FACTS AND NONE OF THEM IS ZERO — the store missing (measured, never
   stamped), the store unreadable (nobody could look), and a reel with no row (never walked). A
   census that answered `0` for the middle one would let a broken store read as a fresh shelf, and
   `stamp()` would then write a duplicate for every reel on it.

⚠ THIS SUITE NEVER TOUCHES THE LIVE STORE. Every write goes to a tempdir passed as `path=`, and the
last law fingerprints `tv/river_stamp.jsonl` before and after to prove it.
"""
import ast
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    from console_safe import enable
    enable()
except Exception:
    pass

import reel_router as RR  # noqa: E402
import river_stamp as RS  # noqa: E402

SRC = io.open(os.path.join(HERE, "river_stamp.py"), encoding="utf-8").read()
TREE = ast.parse(SRC)
LANE = "tvd-retro-triage"


RED_PROOF = [
    {
        "why": 'the law requires this text in river_stamp.py, where it occurs exactly once and in no other file the gate names; deleting it must turn the gate red',
        "file": 'river_stamp.py',
        "find": 'is not a station',
        "replace": '_HEART2_TAMPERED_',
        "matches": 1,
    },
]

def _fn(name):
    """The FunctionDef node, by AST. A name that is gone must fail loudly, not be searched for."""
    for n in ast.walk(TREE):
        if isinstance(n, ast.FunctionDef) and n.name == name:
            return n
    return None


def _open_calls(node):
    """Every open()/io.open() call under `node`, as (call, mode_literal_or_None)."""
    out = []
    for c in ast.walk(node):
        if not isinstance(c, ast.Call):
            continue
        f = c.func
        nm = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else "")
        if nm != "open":
            continue
        mode = None
        if len(c.args) > 1 and isinstance(c.args[1], ast.Constant) \
                and isinstance(c.args[1].value, str):
            mode = c.args[1].value
        for kw in (c.keywords or []):
            if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                mode = kw.value.value
        out.append((c, mode))
    return out


class TheRiverCarriesAStamp(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="river_stamp_gate_")
        self.p = os.path.join(self.d, "river_stamp.jsonl")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _stamp(self, reel, station, by=LANE, **kw):
        return RS.stamp(reel, station, by, path=self.p, **kw)

    # ── ⚠ A LAW THAT CANNOT FIND ITS SUBJECT PASSES HAVING EXAMINED NOTHING ───────────────────
    def test_the_subject_EXISTS_at_all(self):
        for name in ("stamp", "history", "current", "census", "run", "rows", "stations"):
            self.assertTrue(callable(getattr(RS, name, None)),
                            "river_stamp.%s is gone or is not callable — every law below this "
                            "would pass having examined nothing" % name)
        self.assertTrue(str(RS.STORE).endswith(".jsonl"),
                        "the store is no longer a JSONL append log (STORE=%r)" % (RS.STORE,))
        for name in ("stamp", "run", "census", "history"):
            self.assertIsNotNone(_fn(name), "%s is gone from the source the AST laws read" % name)

    # ── ⚠⚠ LAW 1 — ONE STATION VOCABULARY, IMPORTED, NEVER COPIED ────────────────────────────
    def test_the_vocabulary_IS_the_routers_and_is_not_a_second_copy(self):
        vocab, why = RS.stations()
        self.assertIsNotNone(vocab, "the station vocabulary could not be resolved: %s" % why)
        self.assertEqual(tuple(RR.STATIONS) + (RR.UNKNOWN,), tuple(vocab),
                         "river_stamp's vocabulary has drifted from reel_router's. Two authorities "
                         "on what a station IS is how a store starts refusing a station the router "
                         "just added.")
        # ⚠ AST, not a grep: a comment listing the stations is prose, a tuple is a second owner.
        for node in ast.walk(TREE):
            if not isinstance(node, ast.Assign):
                continue
            v = node.value
            if not isinstance(v, (ast.Tuple, ast.List)):
                continue
            vals = [e.value for e in v.elts
                    if isinstance(e, ast.Constant) and isinstance(e.value, str)]
            self.assertNotIn("INTAKE", vals,
                             "the station list is HARDCODED in river_stamp (%r). It must be "
                             "imported from reel_router or the two drift apart silently." % (vals,))

    # ── ⚠⚠ LAW 2 — APPEND-ONLY, PROVEN ON THE FILE MODE ──────────────────────────────────────
    def test_the_store_is_opened_for_APPEND_and_NEVER_for_write(self):
        """A trim or a rewrite here deletes the BEGINNING of every journey — the half a journey is
        for. The sibling free-space series trims by age and is right to; this one must not."""
        modes = [m for _c, m in _open_calls(TREE)]
        self.assertIn("a", modes,
                      "no open(..., \"a\") anywhere in river_stamp — the store is not appended to. "
                      "modes found: %r" % (modes,))
        for m in modes:
            if m is None:
                continue          # no mode literal == read
            self.assertNotIn("w", m,
                             "river_stamp opens a file in mode %r. `open(p, \"w\")` empties the "
                             "target before anything is computed; here that is every reel's "
                             "history. This store appends or it is not a record." % (m,))
            self.assertNotIn("+", m,
                             "mode %r can seek and overwrite. Append-only means append-only." % (m,))

    def test_the_append_is_REACHABLE_not_merely_present(self):
        """⚠ THE LESSON FROM `test_a_prune_records_what_it_freed`: replacing a guard with `if
        False:` left every string the text laws looked for exactly where it was, and they passed
        7/7 over a write that could never execute. Presence is not reachability."""
        fn = _fn("stamp")
        appends = [c for c, m in _open_calls(fn) if m == "a"]
        self.assertTrue(appends, "stamp() contains no append — nothing is ever written")
        for node in ast.walk(fn):
            if not isinstance(node, ast.If):
                continue
            if not any(c is a for a in appends for c, _m in _open_calls(node)):
                continue
            self.assertNotIsInstance(
                node.test, ast.Constant,
                "the append is guarded by a CONSTANT (%r), so it can never run while every law "
                "above still passes. That is exactly how a disabled write hides."
                % getattr(node.test, "value", "?"))

    # ── ⚠⚠ LAW 3 — A STAMP IS DURABLE ────────────────────────────────────────────────────────
    def test_a_stamp_survives_the_write_and_names_what_moved_the_reel(self):
        r = self._stamp("reel_a", "TRIAGE", why="the survey has not walked it")
        self.assertTrue(r["ok"] and r["wrote"], "the first stamp did not write: %s" % r["why"])
        raw = io.open(self.p, encoding="utf-8").read().strip().splitlines()
        self.assertEqual(1, len(raw), "expected exactly one row on disk, found %d" % len(raw))
        row = json.loads(raw[0])
        for k in ("at", "seq", "reel", "station", "from", "by", "byKind", "why"):
            self.assertIn(k, row, "the stamp row does not carry %r" % k)
        self.assertEqual("reel_a", row["reel"])
        self.assertEqual("TRIAGE", row["station"])
        self.assertEqual(LANE, row["by"],
                         "the row does not name WHAT MOVED THE REEL — the fact it exists to carry")
        self.assertIsNone(row["from"], "the first stamp claims a previous station it never had")

    def test_an_unattributed_stamp_is_REFUSED_and_writes_nothing(self):
        r = RS.stamp("reel_a", "TRIAGE", "", path=self.p)
        self.assertFalse(r["ok"], "a stamp with no `by` was accepted")
        self.assertFalse(r["wrote"])
        self.assertFalse(os.path.exists(self.p),
                         "a refused stamp still created the store — a refusal that writes is not "
                         "a refusal")

    def test_a_station_outside_the_river_is_REFUSED(self):
        r = self._stamp("reel_a", "SOMEWHERE")
        self.assertFalse(r["ok"], "a station that is not on the river was accepted")
        self.assertIn("is not a station", r["why"])

    # ── ⚠⚠ LAW 4 — RE-STAMPING WRITES NOTHING; A GENUINE RETURN WRITES A ROW ─────────────────
    def test_restamping_the_same_station_does_NOT_duplicate_a_row(self):
        self._stamp("reel_a", "PRINTER")
        before = os.path.getsize(self.p)
        for _ in range(5):
            r = self._stamp("reel_a", "PRINTER")
            self.assertTrue(r["ok"], "a no-op stamp reported failure: %s" % r["why"])
            self.assertFalse(r["wrote"],
                             "re-stamping a reel at the station it is already at wrote a row. On a "
                             "timer that is one row per walk forever and the journey drowns in it.")
        self.assertEqual(before, os.path.getsize(self.p),
                         "the store grew while nothing moved")
        self.assertEqual(1, RS.history("reel_a", self.p)["n"])

    def test_a_genuine_RE_ENTRY_is_kept_and_not_swallowed_by_the_dedupe(self):
        """⚠ The dedupe must be on the reel's CURRENT station, never on "(reel, station) seen
        before". The second reading erases every regression — and a reel returning to a station it
        already left is the most interesting thing this store can record."""
        self._stamp("reel_a", "PRINTER")
        self._stamp("reel_a", "TRIAGE")
        r = self._stamp("reel_a", "PRINTER")
        self.assertTrue(r["wrote"],
                        "a reel that LEFT PRINTER and came back was refused a second row. The "
                        "dedupe is keyed on the pair, so every regression is silently erased.")
        h = RS.history("reel_a", self.p)
        self.assertEqual(3, h["n"], "expected 3 rows for PRINTER->TRIAGE->PRINTER, got %d" % h["n"])
        self.assertEqual(["PRINTER", "TRIAGE", "PRINTER"], [s["station"] for s in h["stations"]])
        self.assertEqual("TRIAGE", h["stations"][2]["from"],
                         "the re-entry row does not record where it came back FROM")

    # ── ⚠⚠ LAW 5 — THE JOURNEY IS IN APPEND ORDER, AND IT IS NOT A SORT ─────────────────────
    def test_the_history_comes_back_in_the_order_it_happened(self):
        for st in ("INTAKE", "TRIAGE", "STATION", "PRINTER", "JOIN"):
            self._stamp("reel_a", st)
        h = RS.history("reel_a", self.p)
        self.assertTrue(h["ok"], h["why"])
        self.assertEqual(["INTAKE", "TRIAGE", "STATION", "PRINTER", "JOIN"],
                         [s["station"] for s in h["stations"]],
                         "the journey did not come back oldest-first")
        self.assertEqual([1, 2, 3, 4, 5], [s["seq"] for s in h["stations"]],
                         "the sequence numbers do not increase with the journey")
        self.assertEqual("JOIN", h["current"])

    def test_the_order_is_the_APPEND_order_and_a_backwards_clock_is_PUBLISHED_not_sorted(self):
        """⚠ Two stamps in one millisecond, or one clock step backwards, must not silently reorder
        a reel's life. The append order IS the history; `at` is a reading beside it."""
        self._stamp("reel_a", "STATION", at=9000)
        self._stamp("reel_a", "PRINTER", at=1000)          # written second, dated EARLIER
        h = RS.history("reel_a", self.p)
        self.assertEqual(["STATION", "PRINTER"], [s["station"] for s in h["stations"]],
                         "history() re-ordered by the clock. A backwards clock now rewrites the "
                         "past instead of being reported.")
        self.assertEqual(1, h["outOfOrder"],
                         "the clock contradicted the append order and nothing said so — the "
                         "contradiction IS the finding, not something to resolve quietly")

    def test_nothing_is_TRIMMED_out_of_the_store(self):
        """The sibling free-space series trims by age; doing that here deletes the beginning of
        every journey. Written as a ratchet: what went in comes out."""
        for i in range(60):
            self._stamp("reel_%02d" % i, "TRIAGE", at=1)   # `at=1` is 1970 — an age trim eats it
        rep = RS.rows(self.p)
        self.assertEqual(60, rep["n"],
                         "%d of 60 stamps survived. Something is trimming the record." % rep["n"])

    # ── ⚠⚠ LAW 6 — THE CENSUS ────────────────────────────────────────────────────────────────
    def test_the_census_separates_WHERE_THEY_ARE_from_HOW_OFTEN_THEY_PASSED(self):
        self._stamp("reel_a", "TRIAGE")
        self._stamp("reel_a", "STATION")
        self._stamp("reel_b", "TRIAGE")
        c = RS.census(self.p)
        self.assertTrue(c["ok"], c["why"])
        self.assertEqual(1, c["counts"]["STATION"], "counts should hold each reel ONCE, where it is now")
        self.assertEqual(1, c["counts"]["TRIAGE"])
        self.assertEqual(2, c["visits"]["TRIAGE"], "visits should count every arrival ever")
        self.assertEqual(2, c["reels"])
        self.assertEqual(3, c["stamps"])
        self.assertNotEqual(c["counts"], c["visits"],
                            "counts and visits are the same object or the same computation — they "
                            "answer different questions and folding them hides which is which")

    def test_the_census_NAMES_the_stations_nothing_has_ever_reached(self):
        """A 0 beside ROUTED must not read as "none waiting there". The router publishes
        `unreached` for exactly this reason; a store that did not would reproduce the defect."""
        self._stamp("reel_a", "TRIAGE")
        c = RS.census(self.p)
        self.assertIn("ROUTED", c["unreached"])
        self.assertIn("TOMBSTONE", c["unreached"])
        self.assertNotIn("TRIAGE", c["unreached"])

    # ── ⚠⚠ LAW 7 — UNKNOWN STAYS UNKNOWN, IN ALL THREE OF ITS SHAPES ────────────────────────
    def test_UNKNOWN_is_stamped_and_reported_BESIDE_the_counts_never_inside_them(self):
        self._stamp("reel_a", "UNKNOWN")
        self._stamp("reel_b", "TRIAGE")
        c = RS.census(self.p)
        self.assertEqual(1, c["unknown"], "a reel the router could not place was not counted")
        self.assertNotIn("UNKNOWN", c["counts"],
                         "UNKNOWN is inside `counts`, so any total taken from it silently includes "
                         "reels nobody could place")
        self.assertEqual(1, sum(c["counts"].values()),
                         "the unplaceable reel was folded into a station total")

    def test_a_MISSING_store_is_measured_and_zero_and_says_which(self):
        c = RS.census(self.p)
        self.assertTrue(c["ok"], "a store that has never been written read as a failure")
        self.assertIs(False, c["everStamped"])
        self.assertEqual(0, c["reels"])
        self.assertEqual(0, sum(c["counts"].values()))

    def test_an_UNREADABLE_store_is_None_and_NEVER_zero(self):
        """⚠ THE FAILURE THIS EXISTS FOR: a broken store answering `0` reads as a fresh shelf, and
        `stamp()` would then write a duplicate row for every reel on it, forever."""
        os.mkdir(self.p)              # a directory where the file should be — open() will refuse
        c = RS.census(self.p)
        self.assertFalse(c["ok"], "an unreadable store reported a successful census")
        self.assertIsNone(c["counts"], "an unreadable store published counts as if measured")
        self.assertIsNone(c["reels"])
        self.assertIn("UNKNOWN", c["why"])

    @unittest.skipIf(os.name == "nt", "a write-only (0o222) file is a POSIX mode; Windows cannot stage it (v3886, #107)")
    def test_a_stamp_REFUSES_when_it_cannot_read_the_store_it_would_dedupe_against(self):
        """⚠⚠ THIS LAW WAS VACUOUS ON ITS FIRST WRITING AND ITS OWN SABOTAGE CAUGHT IT. The fixture
        was `os.mkdir(self.p)` — a directory where the file belongs. Deleting the refusal outright
        still left this green, because the APPEND then failed too and `ok` was False for a
        completely different reason. The law was reading the right flag off the wrong code path.

        A WRITE-ONLY store separates them: the read is refused and the append would have SUCCEEDED,
        so only a real refusal can keep the row out. And the reason is asserted, not just the flag —
        [[feedback-verify-not-proxy]], because `ok=False` is a proxy for "it refused" and the two
        came apart here.
        """
        io.open(self.p, "w", encoding="utf-8").write(
            '{"at":1,"seq":1,"reel":"reel_a","station":"TRIAGE","by":"x"}\n')
        before = os.path.getsize(self.p)
        os.chmod(self.p, 0o222)                   # unreadable, still appendable
        try:
            r = self._stamp("reel_a", "STATION")
            self.assertFalse(r["ok"],
                             "a stamp was written without being able to read the store — the "
                             "dedupe cannot be enforced blind, so every walk becomes a row")
            self.assertIn("refusing to stamp", r["why"],
                          "the stamp came back not-ok for some OTHER reason (%r). The refusal "
                          "path is not what stopped it." % r["why"])
            self.assertEqual(before, os.path.getsize(self.p),
                             "the refusal still appended to the store")
        finally:
            os.chmod(self.p, 0o644)

    def test_a_reel_with_no_row_is_None_and_the_reason_says_nobody_looked(self):
        self._stamp("reel_a", "TRIAGE")
        st, why = RS.current("reel_zzz", self.p)
        self.assertIsNone(st)
        self.assertIn("never been walked", why,
                      "a never-stamped reel and a reel at no station are indistinguishable")

    # ── ⚠⚠ LAW 8 — THE JOIN: run() STAMPS THE SHELF, AND REFUSES RATHER THAN INVENTING ONE ──
    def test_run_stamps_every_reel_the_router_placed(self):
        rep = {"ok": True, "reels": [{"reel": "reel_a", "station": "PRINTER", "why": "w"},
                                     {"reel": "reel_b", "station": "CAPTURE", "why": "w"}]}
        r = RS.run("unit-test", rep=rep, path=self.p)
        self.assertTrue(r["ok"], r["why"])
        self.assertEqual(2, r["moved"])
        self.assertEqual(0, r["refused"])
        again = RS.run("unit-test", rep=rep, path=self.p)
        self.assertEqual(0, again["moved"],
                         "a second identical walk stamped again — on a timer this store becomes "
                         "one row per tick and the journey is unreadable inside its own noise")
        self.assertEqual(2, again["unchanged"])
        self.assertEqual(2, RS.rows(self.p)["n"])

    def test_a_FLEET_WALK_never_claims_it_moved_the_reel(self):
        """⚠⚠ A WALK SEES A TRANSITION; IT DOES NOT CAUSE ONE. It compares the router's answer
        against the store and finds a reel somewhere new — it cannot tell whether a lane moved it,
        a person did, or the evidence underneath changed. Writing the walker's name in unqualified
        would put a causal claim nobody measured into an APPEND-ONLY record, where it can never be
        taken back. `run()` writes observer rows only; a lane that actually acted stamps directly.
        """
        rep = {"ok": True, "reels": [{"reel": "reel_a", "station": "PRINTER", "why": "w"}]}
        RS.run("tvd-river-walk", rep=rep, path=self.p)
        row = RS.history("reel_a", self.p)["stations"][0]
        self.assertEqual("observer", row["byKind"],
                         "the fleet walk recorded itself as the ACTOR that moved this reel. It "
                         "only looked. That is a cause nobody measured, written where it cannot "
                         "be corrected.")

    def test_a_lane_that_ACTED_is_recorded_as_the_actor(self):
        """The other half — otherwise every row is 'observer' and the field carries nothing."""
        r = self._stamp("reel_a", "TRIAGE")
        self.assertEqual("actor", r["row"]["byKind"],
                         "a direct stamp by a lane that acted was recorded as a mere observer, so "
                         "no row anywhere can say what actually moved a reel")
        r2 = RS.stamp("reel_b", "TRIAGE", "some-walker", path=self.p, observed=True)
        self.assertEqual("observer", r2["row"]["byKind"])

    def test_run_REFUSES_an_unnamed_walk(self):
        rep = {"ok": True, "reels": [{"reel": "reel_a", "station": "PRINTER"}]}
        r = RS.run("", rep=rep, path=self.p)
        self.assertFalse(r["ok"], "a walk that would not name itself was allowed to stamp")
        self.assertFalse(os.path.exists(self.p))

    def test_an_unreadable_router_is_UNKNOWN_and_stamps_NOTHING(self):
        """⚠ A router that could not answer must never be recorded as an empty shelf. Stamping
        nothing and saying why is the only honest outcome."""
        r = RS.run("unit-test", rep={"ok": False, "why": "the printer would not import"},
                   path=self.p)
        self.assertFalse(r["ok"])
        self.assertIsNone(r["moved"], "a refused walk published a moved COUNT — 0 would read as "
                                      "'the river was walked and nothing moved'")
        self.assertIn("UNKNOWN", r["why"])
        self.assertFalse(os.path.exists(self.p))

    # ── ⚠ THE SUITE MUST NOT WRITE HIS STORE ─────────────────────────────────────────────────
    def test_this_suite_never_touches_the_live_store(self):
        live = os.path.join(HERE, RS.STORE)
        before = os.path.getsize(live) if os.path.exists(live) else None
        self._stamp("reel_a", "TRIAGE")
        RS.run("unit-test", rep={"ok": True, "reels": [{"reel": "reel_b", "station": "JOIN"}]},
               path=self.p)
        after = os.path.getsize(live) if os.path.exists(live) else None
        self.assertEqual(before, after,
                         "the gate wrote into the live stamp store. A harness that writes the "
                         "store it grades is not a harness.")

    def test_it_still_parses(self):
        ast.parse(SRC)


if __name__ == "__main__":
    unittest.main(verbosity=2)
