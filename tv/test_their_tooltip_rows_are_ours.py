# -*- coding: utf-8 -*-
"""#41 rank 16 (REG-1560) — THEIR TOOLTIP ROWS ARE OURS: the runtime joint, driven.

The #41 heart audit (rank 16, verified) found the character builder's tooltip composition had no runtime
invariant and no doctor row - its one independent engine, their planner's in-game tooltip measured once as text
(tv/the_tooltip_oracle.json: 203 rows over 6 runewords), was compared only by a gate at push time. This law drives
the joint that closes it:

  · tooltip_oracle_lane.measure()  runs the SHIPPED composition (node over the bible.html on disk, through the
    builder law's stand-in tv/cb_node_harness.py) over EVERY oracle row and judges each: a verdict PER ROW
    ({runeword, base, agree, why}), the bible.html stamp it measured, the oracle's limit - never a summary
  · the receipt on disk, and what every reader makes of it: verdict() (the doctor row 'their tooltip rows'),
    contract() (on / worked / lastTs / owed), and the corroborate joint 'their-tooltip-rows-are-ours'
  · the lane tvd-tooltip-oracle: in the roster, beating under its own name, scoped, tracing, explained, declared

UNKNOWN IS NEVER 0 OR OK, and each case below is a shape of that: no receipt; node absent (a PC without node); a
receipt the page has moved from (stale-reading); a summary in place of rows; an oracle row the lane never judged;
a receipt whose own tally lies about its rows. Every verdict states the oracle's limit - 203 rows over 6 runewords
- so a green never reads as more than it measured.

RED_PROOF below, each seen RED: the stale receipt read as fresh; a summary written instead of rows; an oracle row
dropped by the lane's reader; node absent handed back as 0 rows; the verdict trusting the receipt's tally; the
lane's beat, its roster entry, its COVERED_BY entry and its doctor registration removed; the joint's right side
reading a stale receipt as today's; a directory accepted as node.
"""
import ast
import copy
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

import cb_node_harness as H          # noqa: E402  the stand-in (NODE, _run)
import tooltip_oracle_lane as TOL    # noqa: E402  the joint
import corroborate as C              # noqa: E402  the invariant
import console_doctor as CD          # noqa: E402  the row

LANE = "tvd-tooltip-oracle"
ROW = "their tooltip rows"
JOINT = "their-tooltip-rows-are-ours"


def _fixture_count():
    """The oracle's rows, counted OFF THE FILE and never through the lane's reader - so a reader that drops a row
    cannot satisfy a case that counts rows."""
    with io.open(TOL.ORACLE, encoding="utf-8") as fh:
        fx = json.load(fh)
    return sum(len(v["bases"]) for v in fx["runewords"].values()), len(fx["runewords"]), fx


def _scratch(case):
    d = tempfile.mkdtemp(prefix="tor-law-")
    case.addCleanup(shutil.rmtree, d, True)
    return os.path.join(d, "receipt.json")


def _joint_sides(case, path):
    """The invariant's two side functions, with the lane's receipt pointed at `path`. -> (left, right)"""
    real = TOL.receipt_path
    TOL.receipt_path = lambda: path
    case.addCleanup(setattr, TOL, "receipt_path", real)
    key, what, prove, ln, lf, rn, rf, rel = C._inv_their_tooltip_rows_are_ours()
    case.assertEqual((key, rel), (JOINT, "=="))
    return lf, rf


def _fresh_receipt(rows, **extra):
    """A receipt that measured the bible.html on disk right now."""
    rec = {"lane": LANE, "measuredTs": 1700000000000, "ok": all(r.get("agree") for r in rows) if isinstance(rows, list) else False,
           "why": "synthetic", "node": "/synthetic/node", "rows": rows,
           "agreed": (sum(1 for r in rows if r.get("agree")) if isinstance(rows, list) else None),
           "measured": (len(rows) if isinstance(rows, list) else None),
           "oracleRows": None, "limit": TOL.oracle_limit(), "bible": TOL.bible_stamp(), "kinds": None,
           "runs": 1, "runsMeasured": 1, "firstTs": 1700000000000}
    rec["oracleRows"] = rec["limit"]["rows"]
    rec.update(extra)
    return rec


def _write(path, rec):
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(rec))


@unittest.skipIf(H.NODE is None, "node is not on this machine - the composition cannot be driven here (UNMEASURED)")
class ThePerRowReceipt(unittest.TestCase):

    def test_measure_judges_every_oracle_row_and_never_summarises(self):
        n, k, fx = _fixture_count()
        self.assertGreater(n, 100, "the oracle fixture lost its rows: %d" % n)
        rep = TOL.measure(fx=fx)
        self.assertIsInstance(rep.get("rows"), list, "the composition did not run: %s" % rep.get("why"))
        self.assertEqual(len(rep["rows"]), n, "the lane judged %d rows of an oracle holding %d" % (len(rep["rows"]), n))
        self.assertEqual((rep["measured"], rep["agreed"], rep["ok"]), (n, n, True), rep.get("why"))
        for r in rep["rows"]:
            for key in ("runeword", "base", "agree", "why"):
                self.assertIn(key, r, "a row verdict is missing %r: %r" % (key, r))
            self.assertIs(r["agree"], True, "%s / %s is not theirs: %s" % (r["runeword"], r["base"], r["why"]))
        self.assertEqual(rep["oracleRows"], n)
        self.assertEqual(rep["limit"]["runewords"], k, "the limit does not count the oracle's runewords")
        self.assertEqual(rep["limit"]["rows"], n)
        self.assertEqual(len(rep["limit"]["names"]), k)
        self.assertTrue(rep["bible"] and rep["bible"].get("sha1") and rep["bible"].get("id"),
                        "the receipt does not say WHICH bible.html it measured: %r" % (rep.get("bible"),))
        self.assertEqual(rep["node"], H.NODE, "the receipt does not say which node ran")
        self.assertGreater(rep["kinds"]["equal"], n // 2, "most rows must be theirs exactly")
        for kd in ("sword", "blunt", "speed"):
            self.assertGreater(rep["kinds"][kd], 0, "the declared difference %r was never met" % kd)

    def test_one_altered_oracle_line_is_one_row_not_ours_named(self):
        n, k, fx = _fixture_count()
        fx = copy.deepcopy(fx)
        rw = "Breath of the Dying"
        base = "Crowbill"
        fx["runewords"][rw]["bases"][base]["head"][3] += " (altered by the law)"
        rep = TOL.measure(fx=fx)
        self.assertIsInstance(rep.get("rows"), list, rep.get("why"))
        bad = [r for r in rep["rows"] if r["agree"] is not True]
        self.assertEqual([(r["runeword"], r["base"]) for r in bad], [(rw, base)],
                         "exactly the altered row must be NOT ours: %r" % [(r["runeword"], r["base"]) for r in bad])
        self.assertIn("line 4 differs", bad[0]["why"], "the row does not say WHERE it differs: %s" % bad[0]["why"])
        self.assertIn("(altered by the law)", bad[0]["why"])
        self.assertEqual((rep["agreed"], rep["measured"], rep["ok"]), (n - 1, n, False))
        p = _scratch(self)
        self.assertTrue(TOL.write_receipt(rep, p))
        st, why = TOL.verdict(path=p)
        self.assertEqual(st, TOL.MISSING, why)
        self.assertIn("%s / %s" % (rw, base), why, "the verdict does not NAME the row: %s" % why)
        self.assertIn("1 of %d rows are NOT theirs" % n, why)
        self.assertIn("%d runewords" % k, why, "the verdict does not state the oracle's limit: %s" % why)
        c = TOL.contract(path=p)
        self.assertEqual((c["on"], c["worked"], c["owed"]), (True, 1, 1), c)
        self.assertIsInstance(c["lastTs"], int)
        lf, rf = _joint_sides(self, p)
        self.assertEqual((lf(), rf()), (n, n - 1))
        row = C.check_one(C._inv_their_tooltip_rows_are_ours)
        self.assertEqual(row["state"], C.DISAGREE, row.get("say"))
        self.assertIn(str(n), row["say"])
        self.assertIn(str(n - 1), row["say"])

    def test_run_once_writes_a_receipt_the_readers_read_ok_and_re_measures_only_when_owed(self):
        n, k, fx = _fixture_count()
        p = _scratch(self)
        r = TOL.run_once(path=p, force=True)
        self.assertEqual((r["measured"], r["wrote"], r["ok"], r["agreed"], r["owed"]), (True, True, True, n, 0), r)
        st, why = TOL.verdict(path=p)
        self.assertEqual(st, TOL.OK, why)
        self.assertIn("%d of %d rows are theirs" % (n, n), why)
        self.assertIn("%d runewords" % k, why, "an OK verdict must state the oracle's limit: %s" % why)
        self.assertIn("build ", why)
        c = TOL.contract(path=p)
        self.assertEqual((c["on"], c["worked"], c["owed"]), (True, 1, 0), c)
        lf, rf = _joint_sides(self, p)
        self.assertEqual((lf(), rf()), (n, n))
        self.assertEqual(C.check_one(C._inv_their_tooltip_rows_are_ours)["state"], C.AGREE)
        # fresh and young: the next tick has nothing to re-measure, and the counters do not move
        r2 = TOL.run_once(path=p)
        self.assertEqual((r2["measured"], r2["wrote"]), (False, False), r2)
        self.assertIn("nothing to re-measure", r2["why"])
        self.assertEqual(TOL.contract(path=p)["worked"], 1)
        # forced: it measures again and the LIFETIME counter moves
        r3 = TOL.run_once(path=p, force=True)
        self.assertEqual((r3["measured"], r3["wrote"]), (True, True))
        rec, _ = TOL.read_receipt(p)
        self.assertEqual((rec["runs"], rec["runsMeasured"]), (2, 2))
        # the doctor row, off the same receipt, through the module the row actually calls
        real = TOL.receipt_path
        TOL.receipt_path = lambda: p
        self.addCleanup(setattr, TOL, "receipt_path", real)
        st, why = CD._check_their_tooltip_rows_are_ours()
        self.assertEqual(st, CD.OK, why)


class TheReceiptStaysHonest(unittest.TestCase):
    """No node needed: synthetic receipts against the real readers. UNKNOWN is never 0 or OK."""

    def setUp(self):
        self.n, self.k, self.fx = _fixture_count()
        self.rows_ok = [{"runeword": rw, "base": b, "agree": True, "why": "theirs", "kinds": []}
                        for rw, v in self.fx["runewords"].items() for b in v["bases"]]

    def test_no_receipt_is_unknown_never_zero(self):
        p = _scratch(self)
        st, why = TOL.verdict(path=p)
        self.assertEqual(st, TOL.UNKNOWN, why)
        self.assertIn("no receipt", why)
        self.assertIn(LANE, why)
        c = TOL.contract(path=p)
        self.assertEqual((c["worked"], c["lastTs"], c["owed"]), (None, None, None), c)
        lf, rf = _joint_sides(self, p)
        self.assertEqual(lf(), self.n)
        self.assertIsNone(rf())
        self.assertEqual(C.check_one(C._inv_their_tooltip_rows_are_ours)["state"], C.UNKNOWN)

    def test_node_absent_is_a_receipt_saying_so_and_unknown_everywhere(self):
        real = H.NODE
        H.NODE = None
        self.addCleanup(setattr, H, "NODE", real)
        rep = TOL.measure(fx=self.fx)
        self.assertIsNone(rep["rows"], "with no node the rows must be UNKNOWN (None), not %r" % type(rep["rows"]).__name__)
        self.assertTrue(rep["why"].startswith("node absent"), rep["why"])
        self.assertEqual((rep["ok"], rep["agreed"], rep["measured"], rep["node"]), (False, None, None, None))
        self.assertEqual(rep["oracleRows"], self.n, "the oracle's count is still known; the composition is not")
        p = _scratch(self)
        r = TOL.run_once(path=p)
        self.assertEqual((r["measured"], r["wrote"], r["ok"], r["agreed"], r["owed"], r["node"]),
                         (True, True, False, None, None, None), r)
        self.assertTrue(r["why"].startswith("node absent"), r["why"])
        st, why = TOL.verdict(path=p)
        self.assertEqual(st, TOL.UNKNOWN, why)
        self.assertIn("node absent", why)
        c = TOL.contract(path=p)
        self.assertEqual((c["on"], c["worked"], c["owed"]), (True, 0, None), c)
        self.assertIsInstance(c["lastTs"], int, "the attempt is dated even though nothing was judged")
        lf, rf = _joint_sides(self, p)
        self.assertIsNone(rf())
        real_path = TOL.receipt_path
        TOL.receipt_path = lambda: p
        self.addCleanup(setattr, TOL, "receipt_path", real_path)
        st, why = CD._check_their_tooltip_rows_are_ours()
        self.assertEqual(st, CD.UNKNOWN, why)
        self.assertIn("node absent", why)
        # a later tick with node still absent measures again (it costs nothing) and never reads the old
        # attempt as a fresh verdict
        r2 = TOL.run_once(path=p)
        self.assertTrue(r2["measured"])
        self.assertEqual(TOL.read_receipt(p)[0]["runsMeasured"], 0, "nothing was ever judged, so worked stays 0")

    def test_a_receipt_the_page_has_moved_from_is_unknown_and_the_joint_reads_none(self):
        p = _scratch(self)
        rec = _fresh_receipt(self.rows_ok)
        rec["bible"] = dict(rec["bible"], sha1="0" * 40, id="v0000")
        _write(p, rec)
        st, why = TOL.verdict(path=p)
        self.assertEqual(st, TOL.UNKNOWN, "a stale receipt read as %s: %s" % (st, why))
        self.assertIn("STALE", why)
        self.assertIn("v0000", why)
        self.assertIn("re-measures within", why)
        c = TOL.contract(path=p)
        self.assertEqual((c["worked"], c["owed"]), (1, None), c)
        lf, rf = _joint_sides(self, p)
        self.assertIsNone(rf(), "the joint took a stale receipt as today's agreement")
        self.assertEqual(C.check_one(C._inv_their_tooltip_rows_are_ours)["state"], C.UNKNOWN)
        # an undatable receipt (no stamp) is UNKNOWN too, never fresh by default
        rec2 = _fresh_receipt(self.rows_ok)
        rec2.pop("bible")
        _write(p, rec2)
        st, why = TOL.verdict(path=p)
        self.assertEqual(st, TOL.UNKNOWN, why)
        self.assertIn("no bible.html stamp", why)
        self.assertIsNone(rf())

    def test_a_summary_in_place_of_rows_is_unknown(self):
        p = _scratch(self)
        rec = _fresh_receipt(self.rows_ok)
        rec["rows"] = {"agreed": self.n, "measured": self.n}
        rec["ok"], rec["agreed"], rec["measured"] = True, self.n, self.n
        _write(p, rec)
        st, why = TOL.verdict(path=p)
        self.assertEqual(st, TOL.UNKNOWN, "a summary was read as %s: %s" % (st, why))
        self.assertIn("summary", why)
        self.assertIsNone(TOL.contract(path=p)["owed"])
        lf, rf = _joint_sides(self, p)
        self.assertIsNone(rf())

    def test_a_row_the_lane_never_judged_is_missing_and_the_joint_parts(self):
        p = _scratch(self)
        _write(p, _fresh_receipt(self.rows_ok[1:]))
        st, why = TOL.verdict(path=p)
        self.assertEqual(st, TOL.MISSING, why)
        self.assertIn("%d of %d oracle rows were judged" % (self.n - 1, self.n), why)
        self.assertIn("never reached the composition", why)
        lf, rf = _joint_sides(self, p)
        self.assertEqual((lf(), rf()), (self.n, self.n - 1))
        row = C.check_one(C._inv_their_tooltip_rows_are_ours)
        self.assertEqual(row["state"], C.DISAGREE, row.get("say"))

    def test_the_verdict_counts_rows_and_never_trusts_the_receipts_own_tally(self):
        p = _scratch(self)
        rows = copy.deepcopy(self.rows_ok)
        rows[7]["agree"], rows[7]["why"] = False, "line 5 differs - synthetic"
        rec = _fresh_receipt(rows)
        rec["ok"], rec["agreed"] = True, self.n            # the tally LIES; the rows do not
        _write(p, rec)
        st, why = TOL.verdict(path=p)
        self.assertEqual(st, TOL.MISSING, "the verdict believed the receipt's tally over its rows: %s" % why)
        self.assertIn("%s / %s" % (rows[7]["runeword"], rows[7]["base"]), why)
        self.assertIn("%d runewords" % self.k, why)
        self.assertEqual(TOL.contract(path=p)["owed"], 1)
        lf, rf = _joint_sides(self, p)
        self.assertEqual(rf(), self.n - 1)

    def test_the_lifetime_counters_carry_and_a_lost_history_is_said(self):
        p = _scratch(self)
        rep = _fresh_receipt(self.rows_ok)
        for key in ("runs", "runsMeasured", "firstTs"):
            rep.pop(key)
        self.assertTrue(TOL.write_receipt(rep, p))
        rec, _ = TOL.read_receipt(p)
        self.assertEqual((rec["runs"], rec["runsMeasured"], rec["firstTs"]), (1, 1, rep["measuredTs"]))
        absent = dict(rep, rows=None, agreed=None, measured=None, ok=False, why="node absent: synthetic")
        self.assertTrue(TOL.write_receipt(absent, p))
        rec, _ = TOL.read_receipt(p)
        self.assertEqual((rec["runs"], rec["runsMeasured"]), (2, 1), "an attempt that judged nothing counts as a run, not as work")
        self.assertTrue(TOL.write_receipt(rep, p))
        rec, _ = TOL.read_receipt(p)
        self.assertEqual((rec["runs"], rec["runsMeasured"], rec["firstTs"]), (3, 2, rep["measuredTs"]))
        with io.open(p, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        self.assertTrue(TOL.write_receipt(rep, p))
        rec, _ = TOL.read_receipt(p)
        self.assertEqual((rec["runs"], rec["runsMeasured"], rec["firstTs"]), (None, None, None),
                         "counters restarted over a history this process could not read")
        self.assertIn("unreadable", rec["countersWhy"])
        self.assertEqual(TOL.contract(path=p)["worked"], None, "a lost history is UNKNOWN work, never 0")
        # 2026-09-30 (#231 5908899891) - and the NEXT write, which parses the receipt that stored the Nones, must not
        # restart them: UNKNOWN + 1 is UNKNOWN. lastTs is the part that keeps moving.
        later = dict(rep, measuredTs=rep["measuredTs"] + 60000)
        self.assertTrue(TOL.write_receipt(later, p))
        rec, _ = TOL.read_receipt(p)
        self.assertEqual((rec["runs"], rec["runsMeasured"], rec["firstTs"]), (None, None, None),
                         "the write after the loss restarted the counters - a lost history now reads as a young lane")
        self.assertIn("unreadable", rec["countersWhy"])
        c = TOL.contract(path=p)
        self.assertEqual(c["worked"], None, "a lost history read as %r units of work" % c["worked"])
        self.assertEqual(c["lastTs"], later["measuredTs"], "lastTs must still move after a loss")

    def test_a_directory_is_not_node_and_an_executable_file_is(self):
        d = tempfile.mkdtemp(prefix="tor-node-")
        self.addCleanup(shutil.rmtree, d, True)
        got = H.node_path(env={"TV_NODE": d, "PATH": ""})
        self.assertNotEqual(got, d, "a DIRECTORY was accepted as the node binary")
        self.assertTrue(got is None or os.path.isfile(got), got)
        fake = os.path.join(d, "node.exe" if os.name == "nt" else "node")   # v3886 (#107) - Windows finds node by PATHEXT
        with io.open(fake, "w", encoding="utf-8") as fh:
            fh.write("#!/bin/sh\nexit 0\n")
        os.chmod(fake, 0o755)
        self.assertEqual(H.node_path(env={"TV_NODE": fake, "PATH": ""}), fake, "the env override is first")
        # #107 (REG-3801) - Windows' which answers with PATHEXT's case (node.EXE) for this same file: compare the file
        self.assertEqual(os.path.normcase(H.node_path(env={"PATH": d}) or ""), os.path.normcase(fake), "PATH is second")


class TheLaneIsWired(unittest.TestCase):
    """Real objects, never source grep: the lane is started, beats, is scoped, traces, and its row is explained."""

    def _loop_def(self):
        import health_engine as HE
        spans, src = HE._lane_spans()
        self.assertIn("_tooltip_oracle_loop", spans, "the loop is not in the roster: %s" % sorted(spans))
        self.assertEqual(spans["_tooltip_oracle_loop"][0], LANE)
        tree = ast.parse(src)
        fn = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_tooltip_oracle_loop"]
        self.assertEqual(len(fn), 1)
        return fn[0]

    def test_the_loop_is_in_the_roster_and_beats_under_its_own_name(self):
        fn = self._loop_def()
        ticks = [c.args[0].value for c in ast.walk(fn) if isinstance(c, ast.Call)
                 and getattr(c.func, "id", "") == "_lane_tick" and c.args and isinstance(c.args[0], ast.Constant)]
        self.assertEqual(ticks, [LANE], "the lane does not stamp its beat under its own name: %r" % ticks)
        self.assertTrue(any(isinstance(n, ast.While) for n in ast.walk(fn)), "not a loop")
        import control_app as CA
        self.assertEqual(CA._TOOLTIP_ORACLE_EVERY_S, TOL.EVERY_S, "the loop's period and the module's disagree")
        self.assertLess(CA._TOOLTIP_ORACLE_FIRST_S, CA._TOOLTIP_ORACLE_EVERY_S)
        import lane_census as LC
        rows = {r["fn"]: r for r in LC.census()}
        self.assertEqual(rows["_tooltip_oracle_loop"]["kind"], "LOOP")
        self.assertTrue(rows["_tooltip_oracle_loop"]["supervised"], rows["_tooltip_oracle_loop"])

    def test_the_lane_declares_its_scope_and_never_deletes(self):
        import auto_scope as AS
        self.assertIn(LANE, AS.LANES)
        self.assertEqual(AS.LANE_FN.get(LANE), "_tooltip_oracle_loop")
        self.assertIn("delete", AS.LANES[LANE]["forbids"])
        import control_app as CA
        breaks = [b for b in AS.check_declarations(CA) if LANE in b]
        self.assertEqual(breaks, [], breaks)

    def test_the_lane_leaves_a_trace_the_corroborator_reads(self):
        import loop_corroborate as LCO
        import lane_trace as LT
        self.assertIn("_tooltip_oracle_loop", LCO.LOOPS)
        lane, pattern, every = LCO.LOOPS["_tooltip_oracle_loop"]
        self.assertEqual((lane, pattern, every), (LANE, LT.path_of(LANE), TOL.EVERY_S))
        self.assertIn("_tooltip_oracle_loop", LCO.SURFACES)

    def test_the_row_is_registered_explained_declared_and_mine(self):
        checks = dict(CD.CHECKS)
        self.assertIs(checks.get(ROW), CD._check_their_tooltip_rows_are_ours, "the doctor row is not registered")
        self.assertIn(ROW, CD.WATCHES)
        self.assertIn("_tooltip_oracle_loop", CD.WATCHES[ROW])
        self.assertIn(ROW, CD.MINE, "a row he cannot act on must not bill him")
        self.assertNotIn(ROW, CD.ASKS)
        self.assertIn(ROW, C.COVERED_BY)
        self.assertEqual(tuple(C.COVERED_BY[ROW]), (JOINT,))
        self.assertNotIn(ROW, C.NO_JOINT_YET)
        self.assertIn(C._inv_their_tooltip_rows_are_ours, C.BUILDERS, "the joint is graded but never RUN")
        cov = C.coverage()
        self.assertIn(ROW, cov["covered"], cov.get("say"))

    def test_the_row_maps_every_verdict_and_a_raise_is_unknown(self):
        real = TOL.verdict
        self.addCleanup(setattr, TOL, "verdict", real)
        for st, want in ((TOL.OK, CD.OK), (TOL.MISSING, CD.MISSING), (TOL.UNKNOWN, CD.UNKNOWN), ("weird", CD.UNKNOWN)):
            TOL.verdict = lambda _s=st: (_s, "why %s" % _s)
            got = CD._check_their_tooltip_rows_are_ours()
            self.assertEqual(got, (want, "why %s" % st))

        def boom():
            raise RuntimeError("synthetic")
        TOL.verdict = boom
        st, why = CD._check_their_tooltip_rows_are_ours()
        self.assertEqual(st, CD.UNKNOWN)
        self.assertIn("synthetic", why)

    def test_the_joint_can_refuse_and_reads_two_engines(self):
        rows = C.selftest()
        bad = [w for w, ok in rows if not ok]
        self.assertEqual(bad, [], "the corroborator's self-test is red: %s" % bad)


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {
        "why": "2026-09-30 (#231 5908899891) - the write after a lost history restarts the counters at 1 again: the lost history reads as a young lane",
        "file": "tooltip_oracle_lane.py",
        "find": "        if prev.get(\"countersWhy\"):\n            # ⚠ 2026-09-30 — UNKNOWN + 1 IS STILL UNKNOWN.",
        "replace": "        if False:\n            # ⚠ 2026-09-30 — UNKNOWN + 1 IS STILL UNKNOWN.",
        "matches": 1,
    },
    {
        "why": "REG-1560 - a receipt the page has moved from is read as FRESH: an old agreement reads as today's (stale-reading)",
        "file": "tooltip_oracle_lane.py",
        "find": '    if had["sha1"] == stamp["sha1"]:\n        return True,',
        "replace": '    if True:\n        return True,',
        "matches": 1,
    },
    {
        "why": "REG-1560 - the lane writes a SUMMARY instead of rows: nothing can say which row disagrees",
        "file": "tooltip_oracle_lane.py",
        "find": '    out["rows"] = rrows\n',
        "replace": '    out["rows"] = None\n    out["summaryOnly"] = {"agreed": sum(1 for r in rrows if r["agree"] is True)}\n',
        "matches": 1,
    },
    {
        "why": "REG-1560 - the lane's oracle reader DROPS a row per runeword: 197 rows judged of 203, and a gate counting through the same reader would never see it",
        "file": "tooltip_oracle_lane.py",
        "find": '        for base, e in v["bases"].items():\n            out.append((rw, base, list(e["head"]) + list(e.get("props") or v["props"])))',
        "replace": '        for base, e in list(v["bases"].items())[1:]:\n            out.append((rw, base, list(e["head"]) + list(e.get("props") or v["props"])))',
        "matches": 1,
    },
    {
        "why": "REG-1560 - node absent is handed back as 0 rows judged and ok: a PC without node reads as measured",
        "file": "tooltip_oracle_lane.py",
        "find": '            out["why"] = ("node absent: no node binary by env (TV_NODE), PATH or the known install locations - "\n                          "the composition was NOT run, so every row is UNKNOWN (not 0, not agreed)")\n            return out',
        "replace": '            out["rows"], out["agreed"], out["measured"], out["ok"] = [], 0, 0, True\n            out["why"] = "node absent"\n            return out',
        "matches": 1,
    },
    {
        "why": "REG-1560 - the verdict trusts the receipt's own tally (ok / agreed) instead of counting its rows",
        "file": "tooltip_oracle_lane.py",
        "find": '    bad = [r for r in rows if not (isinstance(r, dict) and r.get("agree") is True)]\n    if judged != live:',
        "replace": '    bad = [] if rec.get("ok") else [r for r in rows if not (isinstance(r, dict) and r.get("agree") is True)]\n    if judged != live:',
        "matches": 1,
    },
    {
        "why": "REG-1560 - the lane's beat is deleted: it keeps running and reads UNKNOWN to lane_liveness for ever",
        "file": "control_app.py",
        "find": "            _lane_tick('tvd-tooltip-oracle', _TOOLTIP_ORACLE_EVERY_S)\n",
        "replace": "            pass\n",
        "matches": 1,
    },
    {
        "why": "REG-1560 - the loop is defined and nobody starts it: the receipt is never written and every reader is UNKNOWN for ever",
        "file": "control_app.py",
        "find": '        ("tvd-tooltip-oracle", _tooltip_oracle_loop),\n',
        "replace": "",
        "matches": 1,
    },
    {
        "why": "REG-1560 - the row's COVERED_BY entry is removed: 'a joint covers this' and 'nobody looked' read the same again",
        "file": "corroborate.py",
        "find": '    "their tooltip rows": ("their-tooltip-rows-are-ours",),\n',
        "replace": "",
        "matches": 1,
    },
    {
        "why": "REG-1560 - the doctor row is de-registered: the receipt is written and no eagle row reads it",
        "file": "console_doctor.py",
        "find": '    ("their tooltip rows", _check_their_tooltip_rows_are_ours),\n',
        "replace": "",
        "matches": 1,
    },
    {
        "why": "REG-1560 - the joint's right side takes a STALE receipt as today's agreement",
        "file": "corroborate.py",
        "find": "        if fresh is not True:\n            return None                   # stale or undatable: an old agreement is not today's\n",
        "replace": "        if False:\n            return None                   # stale or undatable: an old agreement is not today's\n",
        "matches": 1,
    },
    {
        "why": "REG-1561 - a DIRECTORY (or anything that merely exists) is accepted as the node binary",
        "file": "cb_node_harness.py",
        "find": "            if c and os.path.isfile(c) and os.access(c, os.X_OK):\n",
        "replace": "            if c and os.path.exists(c):\n",
        "matches": 1,
    },
]
