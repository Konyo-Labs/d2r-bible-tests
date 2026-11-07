# -*- coding: utf-8 -*-
"""v3880 (REG-3373) - NO SHARD IS HANDED A CHUNK ITS OWN CUT WILL END, SO A RE-RUN CAN FINISH.

MEASURED on v3878's proof round (run 42360263008, 2026-11-07): proof_shard.plan put test_control[13]-[27] on shard 10 as ONE
chunk - priced at the last round's ~90 s a proof, really ~270 s - and heart2 cuts one gate on a shard at HEART2_GATE_CAP_S
(1500 s). After the clean wave each ~40-minute re-run banked only ~4 more (fresh: attempt 2 [4]-[7], 3 [8]-[11], 4
[13]-[17], and attempt 5 [13]-[16] AGAIN - it lost attempt 4's), so 28 proofs on one shard needed 6+ attempts. His question
that day: "there is always one shard thats timing out isnt there? ... is this normal to go through 5 rounds everytime".

REG-3365 (v3879) fixed the PRICE. This fixes the PLAN, which never knew the cut: no chunk is planned longer than its gate's
cap (its proofs plus the gate's two clean runs), two owed chunks of one capped gate never share a shard while a shard
without one is left (on one shard they run as one gate, under one cut), and a gate whose ONE proof cannot fit is named.
The cap comes from proof_shard.run_caps - a copy of heart2._gate_cap_for's rule, held equal to it here for every
registered gate (heart2 is every proof's key; touching it would re-prove the world). RED_PROOF below.
[[the-unjoined-end]] [[copy-drift]]
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import proof_shard as PS  # noqa: E402

CAP = 1500.0
U = 272.811          # test_control's committed seconds per proof (tv/proof_costs.json, REG-3365's floor)


def _heavy_round(tc_proofs=28):
    """a full re-prove round: test_control plus enough other work that a fair share is far over the cut"""
    have = [("test_control", "test_control.py", list(range(tc_proofs)))]
    per = {"test_control": U}
    costs = {"test_control": 240.0}
    for i in range(40):
        nm = "law_%02d" % i
        have.append((nm, nm + ".py", list(range(60))))
        per[nm] = 30.0
        costs[nm] = 25.0
    return have, per, costs


def _tc_by_shard(assign):
    by = {}
    for (g, _i), k in assign.items():
        if g == "test_control":
            by[k] = by.get(k, 0) + 1
    return by


class AChunkFitsItsCut(unittest.TestCase):

    def test_without_the_cap_the_round_hands_a_shard_more_than_its_cut(self):
        """BASELINE - the case can fail: the same heavy round planned the old way gives test_control a shard it cannot finish"""
        have, per, costs = _heavy_round()
        a = PS.plan(have, 16, costs, per_proof=per, caps={})
        worst = max(_tc_by_shard(a).values())
        self.assertGreater(worst * U + 2 * U, CAP, "the fixture cannot reproduce the v3878 chunk - it proves nothing")

    def test_with_the_cap_every_shard_can_finish_its_test_control(self):
        """* THE POINT: each shard's test_control proofs plus its two clean runs fit inside the cut"""
        have, per, costs = _heavy_round()
        rep = {}
        a = PS.plan(have, 16, costs, per_proof=per, caps={"test_control": CAP}, report=rep)
        by = _tc_by_shard(a)
        self.assertEqual(sum(by.values()), 28, "a test_control proof was planned nowhere, or twice")
        for k, n in sorted(by.items()):
            self.assertLessEqual(n * U + 2 * U, CAP, "shard %d holds %d test_control proofs - its cut ends it" % (k, n))
        self.assertEqual(rep.get("overCap"), [])

    def test_a_capped_gate_never_doubles_up_on_a_shard_while_one_is_free(self):
        have, per, costs = _heavy_round()
        a = PS.plan(have, 16, costs, per_proof=per, caps={"test_control": CAP})
        per_chunk = int((CAP - 2 * U) // U)
        for k, n in _tc_by_shard(a).items():
            self.assertLessEqual(n, per_chunk, "shard %d took two test_control chunks - they run as one gate, one cut" % k)

    def test_two_chunks_never_stack_where_the_least_loaded_shard_would_stack_them(self):
        """three heavy chunks fill three of four shards first, so the least-loaded rule alone sends BOTH test_control chunks
        to the fourth - where they run as one gate (4+ proofs) under one cut"""
        have = [("test_control", "t.py", list(range(6))), ("big", "b.py", list(range(3)))]
        per = {"test_control": U, "big": 2000.0}
        a = PS.plan(have, 4, {"test_control": 240.0, "big": 1900.0}, per_proof=per, caps={"test_control": CAP})
        by = _tc_by_shard(a)
        self.assertEqual(sum(by.values()), 6)
        for k, n in by.items():
            self.assertLessEqual(n * U + 2 * U, CAP, "shard %d stacked %d test_control proofs - one gate, one cut" % (k, n))

    def test_a_gate_whose_one_proof_cannot_fit_is_named_and_alone(self):
        have = [("huge", "huge.py", list(range(4)))]
        rep = {}
        a = PS.plan(have, 8, {"huge": 600.0}, per_proof={"huge": 700.0}, caps={"huge": CAP}, report=rep)
        self.assertEqual(rep.get("overCap"), ["huge"])
        self.assertEqual(sorted(_count(a, "huge").values()), [1, 1, 1, 1], "an over-cap gate's proofs were bundled")

    def test_no_cap_is_the_old_plan_exactly(self):
        have, per, costs = _heavy_round()
        old = dict(os.environ)
        try:
            os.environ.pop("HEART2_GATE_CAP_S", None)
            self.assertEqual(PS.plan(have, 16, costs, per_proof=per), PS.plan(have, 16, costs, per_proof=per, caps={}))
        finally:
            os.environ.clear()
            os.environ.update(old)

    def test_the_run_s_cap_reaches_a_plan_that_was_not_handed_one(self):
        """heart2 calls plan() with no caps: the shard's HEART2_GATE_CAP_S must still bound it"""
        have, per, costs = _heavy_round()
        old = dict(os.environ)
        try:
            os.environ["HEART2_GATE_CAP_S"] = "1500"
            a = PS.plan(have, 16, costs, per_proof=per)
        finally:
            os.environ.clear()
            os.environ.update(old)
        for k, n in _tc_by_shard(a).items():
            self.assertLessEqual(n * U + 2 * U, CAP, "the run's cap did not reach heart2's plan() (shard %d: %d)" % (k, n))


def _count(a, gate):
    by = {}
    for (g, _i), k in a.items():
        if g == gate:
            by[k] = by.get(k, 0) + 1
    return by


class TheCapRuleIsHeart2s(unittest.TestCase):
    """run_caps is a copy of heart2._gate_cap_for (heart2 keys every proof); the two must answer alike for every gate"""

    def test_run_caps_matches_the_rule_heart2_cuts_by(self):
        import heart2
        import run_gates
        names = [g.name for g in run_gates.GATES]
        got = PS.run_caps(names, env={"HEART2_GATE_CAP_S": "1500"})
        bad = [(n, got.get(n), heart2._gate_cap_for(n, 1500.0)) for n in names if got.get(n) != heart2._gate_cap_for(n, 1500.0)]
        self.assertEqual(bad, [], "the plan's cap and heart2's cut disagree")
        self.assertTrue(any(v > 1500.0 for v in got.values()), "no gate's own prove_cap_s was read - the case is vacuous")

    def test_no_run_cap_is_no_cap(self):
        self.assertEqual(PS.run_caps(["test_control"], env={}), {})
        self.assertEqual(PS.run_caps(["test_control"], env={"HEART2_GATE_CAP_S": "x"}), {})


RED_PROOF = [
    {"why": "REG-3373 - the plan ignores the cut again (v3878's shard 10: test_control[13]-[27] as one chunk)",
     "file": "tv/proof_shard.py",
     "find": "            if cap and u > 0:                    # REG-3373 - never a chunk its shard's cut will end\n",
     "replace": "            if False:                    # REG-3373 - never a chunk its shard's cut will end\n", "matches": 1},
    {"why": "REG-3373 - two chunks of one capped gate land on one shard (they run as one gate under one cut)",
     "file": "tv/proof_shard.py",
     "find": "        if owed and name in capd and k in held.get(name, ()):", "replace": "        if False:", "matches": 1},
    {"why": "REG-3373 - a gate whose one proof cannot fit its cut is no longer named",
     "file": "tv/proof_shard.py",
     "find": "                    over.append(name)\n", "replace": "                    pass\n", "matches": 1},
    {"why": "REG-3373 - a gate's own larger prove_cap_s is ignored (the plan's cap and heart2's cut disagree)",
     "file": "tv/proof_shard.py",
     "find": "            if isinstance(c, (int, float)) and c > run_cap:\n", "replace": "            if False:\n", "matches": 1},
    {"why": "REG-3373 - heart2's plan() call (no caps argument) no longer reads the run's cap",
     "file": "tv/proof_shard.py",
     "find": "        caps = run_caps([g[0] for g in gates])\n", "replace": "        caps = {}\n", "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
