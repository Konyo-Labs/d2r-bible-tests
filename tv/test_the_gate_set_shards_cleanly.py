# -*- coding: utf-8 -*-
"""v3472 (#184) — the gate set splits into slices that are DISJOINT, COMPLETE and the SAME everywhere.

⚠ WHY: the agent-suite ran 25m18s against its 25-minute ceiling on d9bdb682 and was CANCELLED — the
shipped version got no verdict. CI now runs `run_gates.py --shard K/N` as a matrix. A slice that
drops a gate is a gate that silently never runs; two slices sharing one is a ceiling paid twice; a
slice that differs between machines is a verdict nobody can reproduce. And an EMPTY slice is worse
than all three: `run()` treats `[]` as "every gate".

DRIVEN against the real registry; nothing here reads source text. RED_PROOF below.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import run_gates as RG  # noqa: E402


class TheGateSetShardsCleanly(unittest.TestCase):

    def test_every_gate_lands_in_exactly_one_slice(self):
        names = [g.name for g in RG.GATES]
        for n in (2, 3):
            slices = [RG.shard_names(k, n) for k in range(1, n + 1)]
            flat = [x for s in slices for x in s]
            self.assertEqual(sorted(flat), sorted(names),
                             "%d-way: a gate is missing from every slice, or sits in two" % n)
            self.assertTrue(all(slices), "%d-way: an EMPTY slice — run() would run EVERY gate" % n)

    def test_no_gate_name_is_registered_twice(self):
        """2026-09-25 — test_every_decision_file_is_ignored was registered TWICE (an interrupted edit re-applied)
        and this law stayed green: sorted(flat) == sorted(names) holds when BOTH lists carry the duplicate. A
        second entry runs the gate twice and inflates every census that counts the registry."""
        names = [g.name for g in RG.GATES]
        dup = sorted(set(n for n in names if names.count(n) > 1))
        self.assertEqual(dup, [], "gate names registered more than once: %s" % dup)

    def test_the_slices_are_the_same_on_every_run(self):
        self.assertEqual(RG.shard_names(1, 2), RG.shard_names(1, 2))
        self.assertEqual(RG.shard_names(1, 2, gates=list(reversed(RG.GATES))), RG.shard_names(1, 2),
                         "the slice depends on registry ORDER, so two machines can cut it differently")

    def test_the_slices_are_balanced_by_MEASURED_cost(self):
        """v3477 — balanced on declared timeout, the first sharded run came back 8m41s / 17m25s."""
        w = RG.cost_weights()
        a = sum(w[x] for x in RG.shard_names(1, 2))
        b = sum(w[x] for x in RG.shard_names(2, 2))
        # ⚠ 2026-09-25 — THE OLD BOUND WAS ABOVE THE CEILING. "within one gate's cost" = 303 s while the
        # sabotage it guards (weigh by declared timeout) splits 572 / 794 s - 222 s apart - so heart2 read this
        # proof BLIND. The measured split is 683 / 683. 5% of the total (min 60 s) sees the defect and leaves
        # the greedy split room. [[feedback-threshold-above-the-ceiling]]
        # ⚠ 2026-10-07 (REG-1864) - THE BOUND WENT ABOVE THE CEILING AGAIN: with the table grown to 849 gates the
        # declared-timeout deal splits 998 / 1061 s - 63 s apart - under the 5% (103 s) bound, so v3599's proof read this
        # BLIND. The measured deal is 0.1 s apart. 2% of the total (min 20 s) sits between the two, AND the deal must
        # beat what the declared timeouts would have dealt, judged by the same weights - that comparison cannot drift
        # above the defect however the registry grows.
        self.assertLess(abs(a - b), max(20.0, 0.02 * (a + b)),
                        "slices differ by 2%% or more of the MEASURED total (floor 20 s): %.0f vs %.0f" % (a, b))
        bins = [[0.0, i, []] for i in range(2)]
        for g in sorted(RG.GATES, key=lambda g: (-float(g.timeout or 0), g.name)):
            bn = min(bins, key=lambda x: (x[0], x[1]))
            bn[0] += float(g.timeout or 0)
            bn[2].append(g.name)
        da, db = [sum(w[x] for x in bn[2]) for bn in bins]
        # ⚠ 2026-10-08 - AND BY A MARGIN, NOT BY FLOAT NOISE: under the declared-timeout sabotage the two deals are the SAME
        # bins (31.0 s apart both ways on the refreshed 894-gate table), summed in a different order, and a strict `<`
        # between 31.0 and 31.0 passed on rounding - heart2 read this proof BLIND. The measured deal must win by 0.5 s.
        self.assertLess(abs(a - b) + 0.5, abs(da - db),
                        "dealing by MEASURED cost balances no better than dealing by declared timeout "
                        "(%.1f s apart vs %.1f s apart, judged on measured seconds)" % (abs(a - b), abs(da - db)))

    def test_the_cost_table_is_a_measurement_that_covers_the_registry(self):
        import gate_costs as GC
        table = GC.load()
        self.assertTrue(table, "tv/gate_costs.json is missing or empty — the shards fall back to "
                               "declared timeout, which the first sharded run proved lopsided")
        names = {g.name for g in RG.GATES}
        covered = len(names & set(table)) / float(len(names))
        self.assertGreaterEqual(covered, 0.95, "the cost table covers only %.0f%% of the gate set — "
                                "refresh it: python3 tv/gate_costs.py <ci-job-logs>" % (covered * 100))
        w = RG.cost_weights()
        # v3891 (#194) merges last-round CI seconds (GATE_COSTS) over the committed file. A gate
        # that file has not seen is still MEASURED when last round timed it — that is not a median
        # guess. Unseen means neither table has the name (the sentence _cost_table already prints).
        used, _ = RG._cost_table()
        unseen = sorted(names - set(used or table or {}))
        if unseen:
            src = used or table
            med = sorted(src.values())[len(src) // 2]
            self.assertEqual(w[unseen[0]], med,
                             "an unmeasured gate did not weigh the median: %s" % unseen[0])

    def test_last_rounds_own_seconds_are_not_an_unmeasured_guess(self):
        """v3893 - CI's GATE_COSTS file is last round's own per-gate seconds, a measurement.

        d08ee13e1 went red on the next ship after the first bundle run timed 57 new gates at their
        real CI seconds (many 0.1). The coverage law treated anyone missing from tv/gate_costs.json
        as unmeasured and demanded the committed median (0.3), while cost_weights() correctly used
        last round's 0.1: AssertionError 0.1 != 0.3.
        """
        import json
        import tempfile
        table = __import__("gate_costs").load()
        self.assertTrue(table)
        names = [g.name for g in RG.GATES]
        med = sorted(table.values())[len(table) // 2]
        victim = names[0]
        want = 0.1 if med != 0.1 else 0.2
        rec = {"source": "test last-round overlay", "gates": 1, "totalSeconds": want,
               "costs": {victim: want}}
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(rec, fh)
            old = os.environ.get(RG._ENV_GATE_COSTS)
            os.environ[RG._ENV_GATE_COSTS] = path
            try:
                w = RG.cost_weights()
                self.assertEqual(w[victim], want,
                                 "last round's own seconds for %s were discarded for the median" % victim)
                used, _ = RG._cost_table()
                self.assertIn(victim, used)
                unseen = sorted(set(names) - set(used))
                if unseen:
                    umed = sorted(used.values())[len(used) // 2]
                    self.assertEqual(w[unseen[0]], umed,
                                     "a gate neither table has seen did not weigh the median: %s" % unseen[0])
            finally:
                if old is None:
                    os.environ.pop(RG._ENV_GATE_COSTS, None)
                else:
                    os.environ[RG._ENV_GATE_COSTS] = old
        finally:
            os.remove(path)

    def test_the_banner_names_the_basis_the_weights_actually_used(self):
        """#219 follow-up — the second eye on ea3f05da: every --shard run printed "balanced by
        declared timeout" while cost_weights() balanced on the measured table. One decision
        (_cost_table), two readers; DRIVEN through all three states, and the banner and the weights
        are both pinned to it."""
        import ast
        import inspect
        import gate_costs as _gc
        real = _gc.load
        try:
            for table, word in (({"a": 1.0}, "measured"), ({}, "no measured cost table"),
                                (None, "UNREADABLE")):
                _gc.load = lambda *a, _t=table, **k: _t
                got, basis = RG._cost_table()
                self.assertEqual(got, table)
                self.assertIn(word, basis, "a %r table was described as %r" % (table, basis))
        finally:
            _gc.load = real
        self.assertIn("measured", RG._cost_table()[1],
                      "premise: the committed table is readable, so the basis must say measured")
        tree = ast.parse(inspect.getsource(RG))
        banner = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                  and getattr(n.func, "id", "") == "print" and n.args
                  and isinstance(n.args[0], ast.BinOp)
                  and isinstance(n.args[0].left, ast.Constant)
                  and "SHARD %d/%d" in str(n.args[0].left.value)]
        self.assertEqual(len(banner), 1, "the shard banner moved — this law is judging nothing")
        self.assertNotIn("declared timeout", banner[0].args[0].left.value,
                         "the banner hard-codes a basis again instead of asking _cost_table()")
        self.assertIn("_cost_table", ast.dump(banner[0]),
                      "the banner does not ask _cost_table() which basis the weights used")
        self.assertIn("_cost_table", inspect.getsource(RG.cost_weights),
                      "cost_weights() decides its basis somewhere the banner cannot see")

    def test_a_slice_that_is_not_a_slice_is_refused(self):
        for k, n in ((0, 2), (3, 2), (1, 10 ** 6)):
            with self.assertRaises(ValueError, msg="shard %d/%d was accepted" % (k, n)):
                RG.shard_names(k, n)
        self.assertEqual(RG.main(["run_gates.py", "--shard", "3/2"]), 2,
                         "a malformed --shard did not answer exit 2 (NO GATE RAN)")

    def test_an_only_name_the_registry_does_not_have_is_refused(self):
        """2026-09-29 - a zsh `--only $G` handed 34 names as ONE argument; it matched nothing and the run printed
        '0 gate(s) passed', exit 0. A check that never happened is not a pass."""
        real = RG.GATES[0].name
        self.assertEqual(RG.main(["run_gates.py", "--only", real + " " + RG.GATES[1].name]), 2,
                         "names glued into one argument ran nothing and still answered as if it passed")
        self.assertEqual(RG.main(["run_gates.py", "--only", real, "no_such_gate_anywhere"]), 2,
                         "one unknown name among real ones was dropped silently")


class TheFillMissingKeepsItsHonesty(unittest.TestCase):
    """REG-1858/1859/1860 (the Grok look on gate_costs.fill_missing) - driven on a scratch table."""

    def setUp(self):
        import json
        import shutil
        import tempfile
        self.d = tempfile.mkdtemp(prefix="gc_fill_")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.table = os.path.join(self.d, "gate_costs.json")
        with open(self.table, "w", encoding="utf-8") as fh:
            json.dump({"source": "CI", "gates": 2, "totalSeconds": 3.0, "costs": {"a": 1.0, "b": 2.0}}, fh)
        self.json = json

    def _log(self, name, rows):
        p = os.path.join(self.d, name)
        with open(p, "w", encoding="utf-8") as fh:
            for g, sec in rows:
                fh.write("\u2705 %s    %.1fs  OK\n" % (g, sec))
        return p

    def _rec(self):
        with open(self.table, encoding="utf-8") as fh:
            return self.json.load(fh)

    def test_headline_counts_stay_measured_and_each_fill_keeps_its_own_source(self):
        import gate_costs as GC
        self.assertEqual(GC.fill_missing([self._log("l1", [("a", 9.0), ("c", 4.0)])], "run one", "d1", table=self.table), 1)
        self.assertEqual(GC.fill_missing([self._log("l2", [("d", 5.0)])], "run two", "d2", table=self.table), 1)
        r = self._rec()
        self.assertEqual(r["costs"]["a"], 1.0, "a measured cost was overwritten")
        self.assertEqual((r["gates"], r["totalSeconds"]), (2, 3.0), "estimates leaked into the measured headline")
        self.assertEqual((r["estimatedGates"], r["estimatedSeconds"]), (2, 9.0))
        self.assertEqual([(f["source"], f["date"], f["count"]) for f in r["localEstimates"]["fills"]],
                         [("run one", "d1", 1), ("run two", "d2", 1)], "an earlier fill reads as from the latest log")

    @unittest.skipIf(os.name == "nt", "no fcntl on Windows - gate_costs edits unlocked there and says so: "
                                      "test_a_platform_without_fcntl_edits_unlocked_and_says_so is that arm (v3886, #107)")
    def test_a_lock_that_cannot_be_taken_refuses_the_write(self):
        """REG-1894 - the lock used to fail OPEN: every exception swallowed, the edit went ahead unlocked, nothing said."""
        from unittest import mock
        import gate_costs as GC
        log = self._log("l1", [("c", 4.0)])
        real_open = GC.io.open

        def deny(path, *a, **k):
            if str(path).endswith(".lock"):
                raise PermissionError("no lock for you")
            return real_open(path, *a, **k)

        with mock.patch.object(GC.io, "open", deny):
            with self.assertRaises(GC.LockError):
                GC.fill_missing([log], "x", "d", table=self.table)
        self.assertNotIn("c", self._rec()["costs"], "the table was edited without its lock")

    def test_a_flock_that_fails_where_fcntl_exists_refuses_the_write(self):
        """REG-2027 (the #231 eye on v3599) - "on a machine that HAS fcntl an open() or flock() failure also silently skips
        the lock". The open() arm is the case above; this is the flock() arm, with fcntl really imported."""
        from unittest import mock
        import gate_costs as GC
        try:
            import fcntl
        except ImportError:
            self.skipTest("no fcntl on this platform - the unlocked arm is test_a_platform_without_fcntl_edits_unlocked_and_says_so")
        log = self._log("l1", [("c", 4.0)])
        with mock.patch.object(fcntl, "flock", side_effect=OSError("flock refused")) as fl:
            with self.assertRaises(GC.LockError):
                GC.fill_missing([log], "x", "d", table=self.table)
        self.assertTrue(fl.called, "premise: the lock never reached flock(), so this case measured nothing")
        self.assertNotIn("c", self._rec()["costs"], "a failed flock() on a machine with fcntl still wrote the table")

    def test_an_old_shape_estimate_becomes_the_first_fill_before_a_new_one(self):
        """REG-2027 (the #231 eye on v3599) - fill_missing appended its fill BEFORE _normalise, and _normalise migrates an
        old-shape localEstimates ({source, date}, no fills) only when `fills` is absent: the old source/date stayed
        beside a fills list that held only the new fill, and the earlier fill was never one of them."""
        import gate_costs as GC
        rec = self._rec()
        rec["costs"]["x"] = 7.0
        rec["localEstimates"] = {"gates": ["x"], "count": 1, "source": "old run", "date": "d0"}
        with open(self.table, "w", encoding="utf-8") as fh:
            self.json.dump(rec, fh)
        self.assertEqual(GC.fill_missing([self._log("l1", [("c", 4.0)])], "new run", "d1", table=self.table), 1)
        est = self._rec()["localEstimates"]
        self.assertEqual([(f["source"], f["date"], f["count"]) for f in est["fills"]],
                         [("old run", "d0", 1), ("new run", "d1", 1)],
                         "the old-shape fill was not migrated before the new fill was appended")
        self.assertEqual(sorted(k for k in ("source", "date") if k in est), [],
                         "the old-shape source/date still sit beside the fills list")
        self.assertEqual((est["gates"], est["count"]), (["c", "x"], 2))

    def test_a_platform_without_fcntl_edits_unlocked_and_says_so(self):
        import contextlib
        import io
        import sys
        from unittest import mock
        import gate_costs as GC
        log = self._log("l1", [("c", 4.0)])
        err = io.StringIO()
        with mock.patch.dict(sys.modules, {"fcntl": None}), contextlib.redirect_stderr(err):
            self.assertEqual(GC.fill_missing([log], "x", "d", table=self.table), 1)
        self.assertIn("UNLOCKED", err.getvalue())
        self.assertIs(self._rec()["localEstimates"]["fills"][-1]["locked"], False, "an unlocked fill did not record it")

    @unittest.skipIf(os.name == "nt", "no fcntl on Windows - gate_costs edits unlocked there and says so: "
                                      "test_a_platform_without_fcntl_edits_unlocked_and_says_so is that arm (v3886, #107)")
    def test_a_locked_fill_records_locked_true(self):
        import gate_costs as GC
        GC.fill_missing([self._log("l1", [("c", 4.0)])], "x", "d", table=self.table)
        self.assertIs(self._rec()["localEstimates"]["fills"][-1]["locked"], True)

    @unittest.skipIf(os.name == "nt", "no fcntl on Windows - gate_costs edits unlocked there and says so: "
                                      "test_a_platform_without_fcntl_edits_unlocked_and_says_so is that arm (v3886, #107)")
    def test_two_fills_that_overlap_both_survive(self):
        """REG-1859 - load -> edit -> replace: the first fill is held at its replace while a second fill runs; without
        the lock the second's cost is overwritten by the first's stale snapshot."""
        import threading
        import time
        from unittest import mock
        import gate_costs as GC
        l1 = self._log("l1", [("c", 4.0)])
        l2 = self._log("l2", [("d", 5.0)])
        go = threading.Event()
        real = os.replace
        first = []

        def slow_replace(a, b):
            if not first:
                first.append(1)
                go.wait(5)
            return real(a, b)

        out = []
        with mock.patch.object(GC.os, "replace", slow_replace):
            ta = threading.Thread(target=lambda: out.append(GC.fill_missing([l1], "A", "d", table=self.table)))
            ta.start()
            time.sleep(0.3)
            tb = threading.Thread(target=lambda: out.append(GC.fill_missing([l2], "B", "d", table=self.table)))
            tb.start()
            time.sleep(0.5)
            go.set()
            ta.join(20)
            tb.join(20)
        got = self._rec()["costs"]
        self.assertEqual((got.get("c"), got.get("d")), (4.0, 5.0), "an overlapping fill was lost: %r" % got)


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {
        "why": "REG-1894 - the table lock fails OPEN again: a lock that cannot be taken is swallowed and the edit goes ahead",
        "file": "gate_costs.py",
        "find": "            raise LockError(\"could not take the table lock",
        "replace": "            return self; raise LockError(\"could not take the table lock",
        "matches": 1,
        "needs": "posix",   # v3886 (#107) - its catching cases need fcntl: on Windows it is judged ELSEWHERE, never BLIND
    },
    {
        "why": "REG-1859 - fill_missing edits without the lock: a writer that commits during the fill is lost again",
        "file": "gate_costs.py",
        "find": "    with _table_lock(table) as _lk:\n        with io.open(table, encoding=\"utf-8\") as fh:\n",
        "replace": "    import contextlib\n    with contextlib.nullcontext(type(\"L\", (), {\"locked\": False})()) as _lk:\n        with io.open(table, encoding=\"utf-8\") as fh:\n",
        "matches": 1,
    },
    {
        "why": "REG-1858 - the measured headline counts estimates again",
        "file": "gate_costs.py",
        "find": "    meas = dict((k, v) for k, v in costs.items() if k not in names)\n",
        "replace": "    meas = dict(costs)\n",
        "matches": 1,
    },
    {
        "why": "REG-1860 - a later fill overwrites an earlier fill's source",
        "file": "gate_costs.py",
        "find": "        est.setdefault(\"fills\", []).append(",
        "replace": "        est.__setitem__(\"fills\", []) or est[\"fills\"].append(",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - an --only name the registry does not have runs nothing and answers '0 gate(s) passed', exit 0",
        "file": "tv/run_gates.py",
        "find": "        if _unknown:\n            print(\"⛔ REFUSED — --only names %d gate(s) this registry does not have",
        "replace": "        if False:\n            print(\"⛔ REFUSED — --only names %d gate(s) this registry does not have",
        "matches": 1,
    },
    {
        "why": "2026-09-25 - a gate registered twice (the interrupted edit that shipped in dc0cae95) goes unseen again",
        "file": "run_gates.py",
        "find": '    Gate("test_every_decision_file_is_ignored",\n',
        "replace": '    Gate("test_every_decision_file_is_ignored", [sys.executable, os.path.join(HERE, "test_every_decision_file_is_ignored.py")], 60, why="dup"),\n    Gate("test_every_decision_file_is_ignored",\n',
        "matches": 1,
    },
    {
        "why": "v3477 — the measured table ignored: back to declared timeout, the lopsided 8m41s / 17m25s split",
        "file": "run_gates.py",
        "find": "    weigh = cost_weights(gates)\n",
        "replace": "    weigh = dict((g.name, float(g.timeout or 0)) for g in gates)\n",
        "matches": 1,
    },
    {
        "why": "every slice returns the WHOLE set: each shard re-runs everything and pays the ceiling",
        "file": "run_gates.py",
        "find": "    return sorted(bins[int(k) - 1][2])\n",
        "replace": "    return sorted(g.name for g in gates)\n",
        "matches": 1,
    },
    {
        "why": "ties broken by registry order instead of name: two machines cut different slices",
        "file": "run_gates.py",
        # v3477 — RE-ANCHORED (REG-1163, my own proof): v3477 weighs by measured cost now.
        # Same property: ties must break by NAME, never by registry order.
        "find": "    for g in sorted(gates, key=lambda g: (-weigh[g.name], g.name)):\n",
        "replace": "    for g in gates:\n",
        "matches": 1,
    },
    {
        "why": "the bounds check removed: shard 3/2 is 'accepted' and indexes past the slices",
        "file": "run_gates.py",
        "find": "    if not (1 <= int(k) <= int(n)) or int(n) > len(gates):\n",
        "replace": "    if False:\n",
        "matches": 1,
    },
    {
        "why": "REG-2027 - a failed flock() on a machine that HAS fcntl is swallowed: the table is written unlocked and the fill says locked",
        "file": "gate_costs.py",
        "find": "            fcntl.flock(self.fh, fcntl.LOCK_EX)\n",
        "replace": "            try:\n                fcntl.flock(self.fh, fcntl.LOCK_EX)\n            except OSError:\n                pass\n",
        "matches": 1,
    },
    {
        "why": "REG-2027 - fill_missing appends before the old-shape {source, date} is migrated: the earlier fill is lost from fills",
        "file": "gate_costs.py",
        "find": "        est = _migrate_fills(rec.get(\"localEstimates\")) or {\"gates\": [], \"fills\": []}",
        "replace": "        est = rec.get(\"localEstimates\") or {\"gates\": [], \"fills\": []}",
        "matches": 1,
    },
]
