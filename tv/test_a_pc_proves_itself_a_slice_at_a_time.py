#!/usr/bin/env python3
"""#99 — A PC HE PLAYS ON PROVES ITS INSTRUMENTS A SLICE AT A TIME, AND A SLICE NEVER SPEAKS FOR GATES IT DID NOT RUN.

Konyo, 2026-09-30, on his fleet card: "now only grokbot and ALT TEST is both river stuck". Measured: both PCs have no heart
census, so every self-arming lock (the river's routing among them) stays shut. self_prove only ever started a WHOLE
`heart2.py --prove` (~90 min on his Mac, longer there), which writes its census at the very end; he plays on those PCs
most of the day, the proof stood aside every time, and a proof that stands aside writes nothing. His own Mac is current
only because the pre-push gate proves exactly the gates that changed and stamps the census.

Now each gate keeps the digest of the file it was proved against (`gateShas`), `heart2.py --prove NAMES --slice` merges
one slice and stamps the gate fingerprint only when no declaring gate is owed, and self_prove proves the owed gates a
slice at a time in the idle gaps: cheapest first, a stand-aside costing only its slice, a landed slice counted as
progress. Push-time and full runs stamp exactly as before. It reaches every PC through the ordinary update - nothing is
run by hand on the ALT or on Dean's PC.

Everything here runs on fixture gate files in a temp dir; nothing reads or writes this machine's real census.
[[heart-first]] [[unknown-stays-unknown]] [[the-unjoined-end]] [[open-for-write-truncates-first]]
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import fixture_tmp as _fx_tmp  # noqa: E402  #173 - its scratch is its own, so listing it keeps the law keyable
_fx_tmp.contain()

import heart2 as H2  # noqa: E402
import self_prove as SP  # noqa: E402

_GATE = ('"""a fixture gate"""\n# %s\n'
         'RED_PROOF = [{"why": "fixture", "file": "nowhere.py", "find": "a", "replace": "b", "matches": 1}]\n')
_NOPROOF = '"""a fixture gate that declares no proof"""\n'


class _Fixture(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="slice_law_")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.state = os.path.join(self.d, ".heart2.json")
        self.gates = []
        for n in ("g1", "g2", "g3"):
            self._write(n, _GATE % n)
        self._write("g0", _NOPROOF)                  # a gate with no proof is never owed one
        self.patches = [mock.patch.object(H2, "gate_files", lambda say=print: list(self.gates)),
                        mock.patch.object(H2, "STATE", self.state)]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def _write(self, name, text):
        f = os.path.join(self.d, "test_%s.py" % name)
        with io.open(f, "w", encoding="utf-8") as fh:
            fh.write(text)
        if name not in [n for n, _f in self.gates]:
            self.gates.append((name, f))
        return f

    def _census(self):
        with io.open(self.state, encoding="utf-8") as fh:
            return json.load(fh)


class ASliceNeverSpeaksForGatesItDidNotRun(_Fixture):

    def test_a_slice_that_leaves_gates_owed_does_not_stamp(self):
        H2._write_state({"g1": H2.PROVEN}, stamp=False)
        c = self._census()
        self.assertIsNone(c.get("gatesFingerprint"),
                          "ONE slice stamped the gate fingerprint - every lock on this PC would open with two "
                          "declaring gates never run here")
        self.assertEqual(c["sliceOwed"], 2)
        self.assertIn("g1", c["gateShas"])
        self.assertEqual([n for n, _k in H2.slice_owed()["owed"]], ["g2", "g3"])
        with mock.patch.object(SP, "HERE", self.d):
            st = SP.census_state()
        self.assertEqual(st["state"], "stale", "an unstamped census read as current: %s" % st)
        self.assertEqual(st["owed"], 2)

    def test_the_slice_that_completes_the_census_stamps_it(self):
        H2._write_state({"g1": H2.PROVEN}, stamp=False)
        H2._write_state({"g2": H2.PROVEN, "g3": H2.BLIND}, stamp=False)
        c = self._census()
        self.assertEqual(c.get("gatesFingerprint"), H2.gates_fingerprint(),
                         "the slice that left nothing owed did not stamp the census - the PC can never finish")
        self.assertEqual(c["sliceOwed"], 0)
        self.assertEqual(c["stampedBy"], "slice-complete")
        self.assertEqual(c["blind"], ["g3"], "a blind verdict from a slice was lost in the merge")
        self.assertEqual(sorted(c["provedGates"]), ["g1", "g2"])
        self.assertEqual(SP.census_state()["state"], "current")

    def test_a_push_time_run_still_stamps_what_it_proved(self):
        H2._write_state({"g1": H2.PROVEN}, stamp=True)
        self.assertEqual(self._census().get("gatesFingerprint"), H2.gates_fingerprint(),
                         "the pre-push gate proves only the changed gates and stamps - that must not change")
        self.assertEqual(self._census()["stampedBy"], "run")

    def test_a_changed_gate_file_is_owed_again(self):
        H2._write_state({"g1": H2.PROVEN, "g2": H2.PROVEN, "g3": H2.PROVEN}, stamp=False)
        self.assertEqual(SP.census_state()["state"], "current")
        self._write("g2", _GATE % "g2, edited by an update")
        st = SP.census_state()
        self.assertEqual(st["state"], "stale")
        self.assertEqual([n for n, _k in st["owedGates"]], ["g2"],
                         "an update that changed ONE gate file must owe exactly that gate, not the whole census")

    def test_an_unreadable_gate_is_owed_never_proved(self):
        H2._write_state({"g1": H2.PROVEN, "g2": H2.PROVEN, "g3": H2.PROVEN}, stamp=False)
        g2 = dict(self.gates)["g2"]
        real = H2._read_text
        with mock.patch.object(H2, "_read_text", lambda p: None if p == g2 else real(p)):
            self.assertIsNone(H2.gate_shas()["g2"])
            self.assertIn("g2", [n for n, _k in H2.slice_owed()["owed"]],
                          "a gate file nobody could read counted as proved for it")

    def test_the_census_write_is_atomic(self):
        H2._write_state({"g1": H2.PROVEN}, stamp=False)
        with io.open(self.state, "rb") as fh:
            before = fh.read()

        def dump(obj, fh, **kw):
            fh.write('{"half":')
            raise OSError("killed mid-write")
        with mock.patch.object(H2.json, "dump", dump):
            with self.assertRaises(OSError):
                H2._write_state({"g2": H2.PROVEN}, stamp=False)
        with io.open(self.state, "rb") as fh:
            self.assertEqual(fh.read(), before, "a write that died half-way left the census truncated - heart2 then "
                                                "refuses to write over it and every lock stays shut for good")
        self.assertEqual([f for f in _fx_tmp.list_own(self.d) if f.endswith(".tmp")], [], "a temp file was left behind")


class AGateNobodyMeasuredStaysOwed(_Fixture):
    """Second eye on v3528: BLIND is also what a gate NOBODY MEASURED is written as - never reached by a lane, a lane
    that died holding it, a gate that raised before any proof judged it. Banking its digest told the census it was
    proved against its file, so no slice ran it again and the census read current with it blind: every lock on that PC
    shut for good over a sandbox that failed once. A MEASURED blind is still banked, or one gate that is blind on Windows
    would keep the census from ever finishing."""

    def _prove(self):
        return H2.prove(only=["g1", "g2", "g3"], say=lambda *a, **k: None, stamp=False)

    def test_an_unmeasured_blind_is_owed_and_the_census_waits_for_it(self):
        H2._write_state({"g1": H2.PROVEN, "g2": H2.PROVEN, "g3": H2.BLIND}, stamp=False, unmeasured={"g3"})
        c = self._census()
        self.assertNotIn("g3", c["gateShas"], "a gate nobody measured was banked as proved against its file")
        self.assertEqual([n for n, _k in H2.slice_owed()["owed"]], ["g3"])
        self.assertIsNone(c.get("gatesFingerprint"), "the census was stamped over a gate that never ran")
        self.assertEqual(c["blind"], ["g3"], "while it is owed it still reads blind - the locks stay shut meanwhile")
        H2._write_state({"g3": H2.PROVEN}, stamp=False)
        self.assertEqual(self._census().get("gatesFingerprint"), H2.gates_fingerprint(),
                         "the slice that finally measured it did not complete the census")

    def test_a_full_run_that_could_not_measure_a_gate_does_not_stamp(self):
        # REG-1623 (the #231 eye on b135b25a): a full / push-time run stamped the fingerprint over a gate it tried and
        # could not measure - census current, the gate blind, may() shut, and the prover never ran it again
        with mock.patch("time.time", lambda: 1000.0):
            H2._write_state({"g1": H2.PROVEN, "g2": H2.PROVEN, "g3": H2.PROVEN}, stamp=False)
        self.assertEqual(self._census().get("gatesFingerprint"), H2.gates_fingerprint(), "premise: a complete census")
        with mock.patch("time.time", lambda: 2000.0):
            H2._write_state({"g1": H2.PROVEN, "g2": H2.PROVEN, "g3": H2.BLIND}, stamp=True, unmeasured={"g3"})
        c = self._census()
        self.assertIsNone(c.get("gatesFingerprint"),
                          "a full run stamped the census over a gate it could not measure (the prior stamp is the "
                          "tree's too, so keeping it reads current just the same)")
        self.assertIsNone(c.get("stampedBy"))
        self.assertIn("g3", c.get("unstampedWhy") or "")
        self.assertEqual(SP.census_state()["state"], "stale", "the prover sees nothing owed and never runs g3 again")
        self.assertEqual([n for n, _k in H2.slice_owed()["owed"]], ["g3"])
        # and a gate nobody measured keeps the stamp of when it WAS tested
        self.assertEqual(c["verdictAt"].get("g3"), 1000000, "a gate nobody measured was stamped as tested now")
        self.assertEqual(c["verdictAt"].get("g1"), 2000000)
        # the slice that measures it completes the census again
        H2._write_state({"g3": H2.PROVEN}, stamp=False)
        self.assertEqual(self._census().get("gatesFingerprint"), H2.gates_fingerprint())

    def test_a_measured_blind_still_completes_the_census(self):
        H2._write_state({"g1": H2.PROVEN, "g2": H2.PROVEN, "g3": H2.BLIND}, stamp=False, unmeasured=set())
        c = self._census()
        self.assertEqual(c["sliceOwed"], 0, "a gate MEASURED blind stayed owed - one gate blind on a PC would keep its "
                                           "census from ever finishing, and re-run it every idle gap")
        self.assertEqual(c.get("gatesFingerprint"), H2.gates_fingerprint())

    def test_the_gates_no_lane_reached_are_owed(self):
        def lane(i, work, out, lock, sink, built, buffered=True, blank=None):
            built.append(True)                   # built its sandbox, then took nothing
        with mock.patch.object(H2, "_prove_lane", lane):
            res = self._prove()
        self.assertEqual(res, {"g1": H2.BLIND, "g2": H2.BLIND, "g3": H2.BLIND})
        c = self._census()
        self.assertEqual(c["gateShas"], {}, "the missing-row sweep's rows were banked as proved: %s" % c["gateShas"])
        self.assertEqual(c["sliceOwed"], 3)
        self.assertIsNone(c.get("gatesFingerprint"))

    def test_a_gate_that_raised_before_any_proof_is_owed(self):
        def gate(sandbox, name, filename, proofs, say):
            if name == "g2":
                raise RuntimeError("the browser slot would not open")
            return H2.PROVEN, [H2.PROVEN] * len(proofs)
        box = os.path.join(self.d, "sandbox")       # inside the fixture dir, removed with it
        os.makedirs(box, exist_ok=True)
        with mock.patch.object(H2, "make_sandbox", lambda say=print: (box, None)), \
                mock.patch.object(H2, "_prove_gate", gate), \
                mock.patch.object(H2, "prove_workers", lambda *a, **k: 1):
            res = self._prove()
        self.assertEqual(res, {"g1": H2.PROVEN, "g2": H2.BLIND, "g3": H2.PROVEN})
        self.assertEqual(sorted(self._census()["gateShas"]), ["g1", "g3"],
                         "a gate that raised before any proof judged it was banked as proved against its file")
        self.assertEqual([n for n, _k in H2.slice_owed()["owed"]], ["g2"])

    def test_a_lane_that_died_holding_a_gate_leaves_it_owed(self):
        class _Unprintable(Exception):
            def __str__(self):
                raise ValueError("cannot even say why")       # the lane's own handler raises -> the lane dies

        def gate(sandbox, name, filename, proofs, say):
            raise _Unprintable()
        box = os.path.join(self.d, "sandbox")       # inside the fixture dir, removed with it
        os.makedirs(box, exist_ok=True)
        with mock.patch.object(H2, "make_sandbox", lambda say=print: (box, None)), \
                mock.patch.object(H2, "_prove_gate", gate), \
                mock.patch.object(H2, "prove_workers", lambda *a, **k: 1):
            res = self._prove()
        self.assertEqual(res, {"g1": H2.BLIND, "g2": H2.BLIND, "g3": H2.BLIND})
        self.assertNotIn("g1", self._census()["gateShas"],
                         "the gate a dying lane was holding was banked as proved against its file")
        self.assertEqual(self._census()["gateShas"], {})


class TheLaneProvesASliceAtATime(unittest.TestCase):

    INSTALLED = ("installed", "a clean installed tree")

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="slice_lane_")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.path = os.path.join(self.d, ".self_prove.json")
        self.spawned = []
        SP._STARTED.update(pid=None, birth=None)
        self.addCleanup(SP._STARTED.update, pid=None, birth=None)

    def _spawn(self, log_path, names=None):
        self.spawned.append(names)
        return 999_999_3                          # not alive: the next tick sees the slice ended

    def _census(self, state, owed):
        return {"state": state, "why": "fixture", "fingerprint": "fp1", "owed": len(owed),
                "owedGates": [(n, 1) for n in owed], "owedWhy": "fixture: %d owed" % len(owed)}

    def _tick(self, census, now):
        with mock.patch.object(SP, "_gate_costs", lambda path=None: {}):
            return SP.tick(now_s=now, busy=3.0, tree=self.INSTALLED, census=census, path=self.path,
                           spawn_fn=self._spawn, env={}, playing=False, free=8000)

    def test_the_tick_proves_a_recorded_blind_first(self):
        """REG-1673 - the tick hands the census's BLIND list to the planner: the slice is the BLIND gate alone"""
        census = dict(self._census("stale", ["g1", "g2", "harness"]), blind=["harness"])
        r = self._tick(census, 1000.0)
        self.assertEqual(r["key"], "start")
        self.assertEqual(self.spawned, [["harness"]],
                         "the recorded BLIND gate was not proved first and alone: %s" % self.spawned)

    def test_the_tick_starts_a_slice_and_names_its_gates(self):
        r = self._tick(self._census("missing", ["g1", "g2", "g3"]), 1000.0)
        self.assertEqual(r["key"], "start")
        self.assertEqual(self.spawned, [["g1", "g2", "g3"]],
                         "the lane started a WHOLE census on a PC that never finishes one: %s" % self.spawned)
        self.assertEqual(r["owed"], 3, "owed must count the gates, not say 1")

    def test_a_slice_that_landed_is_progress_and_the_next_slice_starts(self):
        self._tick(self._census("missing", ["g1", "g2", "g3"]), 1000.0)
        r = self._tick(self._census("stale", ["g3"]), 1600.0)
        mem = json.load(io.open(self.path, encoding="utf-8"))
        self.assertIsNone(mem.get("lastFailAt"), "a slice that proved its gates was booked as a FAILURE (3 h backoff)")
        self.assertEqual(mem.get("slices"), 1)
        self.assertEqual(r["worked"], 1)
        self.assertEqual(r["key"], "start")
        self.assertEqual(self.spawned[-1], ["g3"], "the next slice did not take what was still owed")

    def test_a_slice_that_landed_nothing_backs_off(self):
        self._tick(self._census("missing", ["g1", "g2"]), 1000.0)
        r = self._tick(self._census("stale", ["g1", "g2"]), 1600.0)
        self.assertEqual(r["key"], "backoff", "a slice that proved nothing was restarted at once - a prover that "
                                              "cannot write would spin every ten minutes")
        self.assertEqual(len(self.spawned), 1)

    def test_the_last_slice_makes_the_census_current(self):
        self._tick(self._census("stale", ["g3"]), 1000.0)
        r = self._tick({"state": "current", "why": "fixture", "fingerprint": "fp1"}, 1600.0)
        self.assertEqual(r["owed"], 0)
        self.assertEqual(r["worked"], 1)
        self.assertEqual(len(self.spawned), 1, "a current census started another proof")

    def test_spawn_hands_heart2_the_slice(self):
        seen = {}

        class _P(object):
            pid = 4242

        def popen(cmd, **kw):
            seen["cmd"] = cmd
            return _P()
        SP.spawn(os.path.join(self.d, "log"), popen=popen, names=["g1", "g2"])
        cmd = seen["cmd"]
        i = cmd.index("--prove")
        self.assertEqual(cmd[i + 1:], ["g1", "g2", "--slice", "--reuse"],
                         "heart2 was not told this is a SLICE (or #186: that its census reuses) - it would stamp a "
                         "census that spoke for two gates")
        SP.spawn(os.path.join(self.d, "log"), popen=popen)
        self.assertEqual(seen["cmd"][-2:], ["--prove", "--reuse"], "a whole-census run changed shape")


class TheSlicePlan(unittest.TestCase):

    def test_cheapest_first_within_the_budget(self):
        owed = [("a", 1), ("b", 0), ("c", 3)]
        costs = {"a": 10, "b": 100, "c": 5}                # est: a 20, b 100, c 20
        self.assertEqual(SP.plan_slice(owed, costs, budget_s=50), ["a", "c"])

    def test_a_gate_costlier_than_the_budget_is_a_slice_of_its_own(self):
        self.assertEqual(SP.plan_slice([("big", 4)], {"big": 1000}, budget_s=60), ["big"])

    def test_the_gate_cap_holds_and_an_untimed_gate_is_planned_by_its_default(self):
        owed = [("g%02d" % i, 0) for i in range(10)]
        self.assertEqual(len(SP.plan_slice(owed, {}, budget_s=10 ** 6, max_gates=4)), 4)
        self.assertEqual(SP.plan_slice([("x", 1)], {}, budget_s=SP.SLICE_UNKNOWN_COST_S * 2), ["x"])

    def test_nothing_owed_plans_nothing(self):
        self.assertEqual(SP.plan_slice([], {}), [])

    def test_a_recorded_blind_is_a_slice_of_its_own(self):
        """REG-1673 - one BLIND record shuts every lock on the PC; the gates that can lift it go first and alone"""
        owed = [("cheap", 0), ("blind_b", 3), ("mid", 1), ("blind_a", 5)]
        costs = {"cheap": 1, "mid": 5, "blind_a": 50, "blind_b": 60}
        self.assertEqual(SP.plan_slice(owed, costs, budget_s=10 ** 6, blind=["blind_a", "blind_b", "not_owed"]),
                         ["blind_b", "blind_a"],
                         "a slice mixed other gates in with the BLIND ones, so their verdict waits for all of them")
        self.assertEqual(SP.plan_slice(owed, costs, budget_s=10 ** 6, blind=["not_owed"]),
                         ["cheap", "mid", "blind_b", "blind_a"],
                         "a BLIND gate that is not owed (its file unchanged) cannot be re-proved; it must not empty "
                         "the slice")
        self.assertEqual(SP.plan_slice(owed, costs, budget_s=10 ** 6, blind=None)[0], "cheap")


RED_PROOF = [
    {"why": "REG-1673 - a recorded BLIND waits inside a slice of cheaper gates: the river stays shut for the whole slice",
     "file": "tv/self_prove.py",
     "find": "    if _first:\n        owed = _first\n",
     "replace": "    if False:\n        owed = _first\n", "matches": 1},
    {"why": "REG-1673 - the tick never hands the census's BLIND list to the planner",
     "file": "tv/self_prove.py",
     "find": "plan_slice(_plan, _costs, blind=census.get(\"blind\"), first=_lf[\"rank\"])",   # REG-3351 re-anchor     # REG-1674 re-anchor
     "replace": "plan_slice(_plan, _costs, first=_lf[\"rank\"])", "matches": 1},
    {"why": "REG-1623 - a full run stamps the census over a gate it could not measure",
     "file": "tv/heart2.py",
     "find": "    if _unm_owed:\n        _fp_out = None\n    else:\n",
     "replace": "    if False:\n        _fp_out = None\n    else:\n", "matches": 1},
    {"why": "REG-1623 - a gate nobody measured is stamped as tested now",
     "file": "tv/heart2.py",
     "find": "        if _n in _unm:\n            continue\n        _seen[_n] = _now_ms\n",
     "replace": "        _seen[_n] = _now_ms\n", "matches": 1},
    {
        "why": "#99 - a slice stamps the gate fingerprint again: one slice of a PC's first census opens every lock",
        "file": "heart2.py",
        "find": "    _fp_out = gates_fingerprint(gates) if (stamp or not _owed) else prior.get(\"gatesFingerprint\")\n",
        "replace": "    _fp_out = gates_fingerprint(gates)\n",
        "matches": 1,
    },
    {
        "why": "#99 - a slice's gates are no longer recorded against their files: the census can never be completed",
        "file": "heart2.py",
        "find": "        _gs[_n] = _shas.get(_n)\n",
        "replace": "        pass\n",
        "matches": 1,
    },
    {
        "why": "second eye on v3528 - a gate nobody measured is banked as proved against its file: the census stops "
               "owing it and reads current over a gate that never ran",
        "file": "heart2.py",
        "find": "        if _n in _unm:\n            _gs.pop(_n, None)\n            continue\n",
        "replace": "        if False:\n            _gs.pop(_n, None)\n            continue\n",
        "matches": 1,
    },
    {
        "why": "second eye on v3528 - every BLIND stays owed, measured or not: a gate blind on Windows keeps the census "
               "from ever finishing",
        "file": "heart2.py",
        "find": "        if _n in _unm:\n            _gs.pop(_n, None)\n",
        "replace": "        if _n in _unm or results.get(_n) == BLIND:\n            _gs.pop(_n, None)\n",
        "matches": 1,
    },
    {
        "why": "second eye on v3528 - the missing-row sweep no longer names what it wrote without measuring",
        "file": "heart2.py",
        "find": "            blank.add(nm)                      # never reached",
        "replace": "            pass                               # never reached",
        "matches": 1,
    },
    {
        "why": "second eye on v3528 - a gate that raised before any proof judged it is banked as proved",
        "file": "heart2.py",
        "find": "                        blank.add(name)        # raised before any proof judged it",
        "replace": "                        pass                   # raised before any proof judged it",
        "matches": 1,
    },
    {
        "why": "second eye on v3528 - the gate a dying lane was holding is banked as proved",
        "file": "heart2.py",
        "find": "                        blank.add(_n)          # the lane died holding it",
        "replace": "                        pass                   # the lane died holding it",
        "matches": 1,
    },
    {
        "why": "second eye on v3528 - prove() drops what the prover said it never measured before the census write",
        "file": "heart2.py",
        "find": "        _write_state(results, measured=_ages, stamp=False, unmeasured=_blank)",
        "replace": "        _write_state(results, measured=_ages, stamp=False, unmeasured=None)",
        "matches": 1,
    },
    {
        "why": "#99 - the census is written in place again: a kill mid-write truncates it for good",
        "file": "heart2.py",
        "find": "    _tmp = \"%s.%d.tmp\" % (STATE, os.getpid())\n",
        "replace": "    _tmp = STATE\n",
        "matches": 1,
    },
    {
        "why": "#99 - a slice that proved its gates is booked as a failure again: a 3 h backoff after every slice",
        "file": "self_prove.py",
        "find": "        elif mem.get(\"sliceGates\") and (_slice_landed(census, mem.get(\"sliceGates\")) or 0) > 0:\n",
        "replace": "        elif False:\n",
        "matches": 1,
    },
    {
        "why": "#99 - the spawn drops --slice: heart2 stamps a census that speaks for one slice",
        "file": "self_prove.py",
        "find": "((list(names) + [\"--slice\"]) if names else [])",
        "replace": "((list(names) + []) if names else [])",
        "matches": 1,
    },
    {
        "why": "#99 - the tick starts a whole census again on a PC that never finishes one",
        "file": "self_prove.py",
        "find": "                mem[\"pid\"] = (spawn_fn or _spawn_real)(log_path, names=_slice)\n",
        "replace": "                mem[\"pid\"] = (spawn_fn or _spawn_real)(log_path)\n",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
