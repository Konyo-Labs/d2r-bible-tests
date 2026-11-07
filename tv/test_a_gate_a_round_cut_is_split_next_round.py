# -*- coding: utf-8 -*-
"""v3881 (REG-3402) - A GATE A ROUND CUT AT ITS DEADLINE IS SPLIT NEXT ROUND, WHATEVER ITS PRICE SAYS - AND THE SPLIT IS KEPT.

His rule, 11-07 23:58, after v3880's shard 5 was cut at minute 55: "we mentioned this prior and earlier we need to split the
shard that DO TIME OUT that way they wont". REG-3401 fixed the PRICE that overloaded shard 5 (10.4 s planned, 57.5 s measured);
this is the rule that does not wait on a price: the fan-in reads which gates' proofs the deadline cut (TIMEOUT in a shard's
owed list), counts the shards each was planned on, and the next plan cuts that gate into at least TWICE as many chunks - spread
over shards like any chunk, under the per-gate cut (REG-3373). The split rides in the carried prices file ("split"), is
carried round to round like a price (REG-3401) and never forgotten; the committed table holds tonight's (the gate that cut
shard 5: 2). Applied to the round's real 22 stores, the rule learned exactly that one gate. RED_PROOF below.
"""
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import proof_shard as PS  # noqa: E402


def _body(k, assigned, cut=(), measured=None):
    entries, t = {}, 1794000000000
    for g, (n, gap) in (measured or {}).items():
        for i in range(n):
            t += int(gap * 1000)
            entries["%s-%d-%d" % (g, k, i)] = {"gate": g, "provedAt": t}
    return {"entries": entries, "shard": {"k": k, "n": 4, "head": "abc123def456", "assigned": [list(a) for a in assigned],
                                          "owed": [[g, i, PS.TIMEOUT, "cut at its bound"] for g, i in cut]}}


class AGateARoundCutIsSplitNextRound(unittest.TestCase):

    def test_a_cut_gate_on_one_shard_is_planned_in_two_next_round(self):
        """* THE POINT - v3880's shard 5: one gate, one shard, its tail cut -> at least 2 chunks next round"""
        b = [_body(5, [("test_slow", i) for i in range(27)], cut=[("test_slow", i) for i in range(18, 27)]),
             _body(6, [("test_fast", i) for i in range(4)])]
        self.assertEqual(PS.cut_splits(b), {"test_slow": 2})

    def test_a_gate_cut_across_two_shards_doubles_to_four_and_a_learned_split_is_never_lost(self):
        b = [_body(1, [("test_slow", 0), ("test_slow", 1)], cut=[("test_slow", 1)]),
             _body(2, [("test_slow", 2), ("test_slow", 3)], cut=[("test_slow", 3)])]
        self.assertEqual(PS.cut_splits(b, prev={"test_old": 3}), {"test_slow": 4, "test_old": 3})
        self.assertEqual(PS.cut_splits([_body(1, [("test_slow", 0)])], prev={"test_slow": 6}), {"test_slow": 6},
                         "a learned split was dropped by a round that did not cut the gate")

    def test_the_plan_honours_a_split_whatever_the_price(self):
        """a cheap price alone would keep the gate whole on one shard; its learned split spreads it"""
        have = [("test_slow", "test_slow.py", [None] * 12)] + [("test_g%d" % i, "test_g%d.py" % i, [None] * 6) for i in range(8)]
        pp = dict(("test_g%d" % i, 20.0) for i in range(8))
        pp["test_slow"] = 1.0
        whole = PS.plan(have, 4, per_proof=pp, served=set(), caps={}, splits={})
        split = PS.plan(have, 4, per_proof=pp, served=set(), caps={}, splits={"test_slow": 3})
        on = lambda asg: sorted(set(k for (g, i), k in asg.items() if g == "test_slow"))
        self.assertEqual(len(on(whole)), 1, "premise: priced cheap, the gate is one chunk on one shard: %r" % on(whole))
        self.assertGreaterEqual(len(on(split)), 3, "the learned split did not spread the gate: %r" % on(split))
        self.assertEqual(sorted(split), sorted(whole), "every proof is still planned exactly once")

    def test_the_fan_in_writes_the_split_and_carries_the_last_one(self):
        root = tempfile.mkdtemp(prefix="tvd_split_")
        for k, body, prev in ((5, _body(5, [("test_slow", i) for i in range(6)], cut=[("test_slow", 5)],
                                        measured={"test_slow": (3, 50.0)}), {"v": 1, "perProof": {}, "split": {"test_old": 2}}),
                              (6, _body(6, [("test_fast", i) for i in range(3)], measured={"test_fast": (3, 4.0)}), None)):
            d = os.path.join(root, "proof-shard-%d" % k)
            os.makedirs(d)
            with io.open(os.path.join(d, PS.STORE_NAME), "w", encoding="utf-8") as fh:
                json.dump(body, fh)
            if prev:
                with io.open(os.path.join(d, PS.PREV_COSTS_NAME), "w", encoding="utf-8") as fh:
                    json.dump(prev, fh)
        out = os.path.join(root, "out.json")
        r = subprocess.run([sys.executable, os.path.join(HERE, "proof_shard.py"), "--measure-costs", root, "--out", out],
                           capture_output=True, text=True, timeout=120, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        with io.open(out, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh).get("split"), {"test_old": 2, "test_slow": 2})

    def test_every_shard_reads_the_split_the_same_way(self):
        """the plan's default reads the committed table and HEART2_SHARD_COSTS (the one seed every shard reads)"""
        root = tempfile.mkdtemp(prefix="tvd_split_env_")
        p = os.path.join(root, "costs.json")
        with io.open(p, "w", encoding="utf-8") as fh:
            json.dump({"v": 1, "perProof": {}, "split": {"test_from_last_round": 4}}, fh)
        sp = PS.proof_splits(env={"HEART2_SHARD_COSTS": p})
        self.assertEqual(sp.get("test_from_last_round"), 4)
        self.assertGreaterEqual(sp.get("test_a_safety_net_red_closes_only_its_own_lock") or 0, 2,
                                "the committed table lost the split v3880's shard 5 taught")


RED_PROOF = [
    {"why": "REG-3402 - a gate a round cut is not split next round (its price alone decides again)",
     "file": "tv/proof_shard.py", "find": "                k = max(k, min(p, spd[name]))\n", "replace": "                pass\n",
     "matches": 1},
    {"why": "REG-3402 - a learned split is forgotten by the next round that did not cut the gate",
     "file": "tv/proof_shard.py",
     "find": "    out = dict((str(g), int(v)) for g, v in (prev or {}).items() if isinstance(v, int) and not isinstance(v, bool) and v > 1)\n    on, cut = {}, set()\n",
     "replace": "    out = {}\n    on, cut = {}, set()\n", "matches": 1},
    {"why": "REG-3402 - the fan-in stops writing what it learned",
     "file": "tv/proof_shard.py", "find": '"perProof": dict(sorted(got.items())), "split": dict(sorted(split.items()))}',
     "replace": '"perProof": dict(sorted(got.items()))}', "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
