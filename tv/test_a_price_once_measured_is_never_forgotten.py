# -*- coding: utf-8 -*-
"""v3881 (REG-3401) - A PROOF PRICE ONCE MEASURED IS NEVER FORGOTTEN, SO A STALE-LOW PRICE CANNOT OVERLOAD A SHARD AGAIN.

His words, 11-07 23:31, as v3880's round waited on its last shard: "if this shard times out again i want you making sure going
forward it doesnt happen make sure of it". It had: shard 5 of 22 ran 56.5 min and its last 9 proofs were cut at minute 55.
MEASURED from the round's own 22 shard stores (every one of 9,646 proofs fresh): the plan was balanced (every shard modelled at
2,555 s; the other 21 finished in 23-36 min), but one gate's price was 5.5x low - test_a_safety_net_red_closes_only_its_own_lock
at 10.4 s a proof (v3872's committed table) against 57.5 s measured: 27 proofs planned as 270 s, real ~1,550 s, all on shard 5.

Why the price was stale: each round saved ONLY the prices it re-measured (REG-3274), so a round that SERVED a gate from the
bank dropped its measured price and the next plan fell back to the committed table, last refreshed on v3872. Two fixes:
  * the committed table is raised to that round's measurement wherever it measured higher, never lowered (584 raised, 31 new);
  * every shard hands on the prices it was planned on (proof_costs.prev.json, beside its cache) and the fan-in's saved table is
    those prices with this round's measurements written over them - a price measured once carries until it is re-measured.
Pinned here on the fan-in's own CLI over shard stores built in a temp dir, and on the workflow's own lines. RED_PROOF below.
[[stale-reading]] [[unknown-stays-unknown]]
"""
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
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

WORKFLOW = os.path.join(ROOT, ".github", "workflows", "proof-keys-shards.yml")


def _shard(root, name, gate_gaps, prev=None):
    """a shard artifact dir: a store whose proofs of each gate were proved `gap` seconds apart, and (optionally) the prices
    the shard was planned on"""
    d = os.path.join(root, name)
    os.makedirs(d)
    entries, t = {}, 1794000000000
    for gate, (n, gap) in gate_gaps.items():
        for i in range(n):
            t += int(gap * 1000)
            entries["%s-%d" % (gate, i)] = {"gate": gate, "provedAt": t}
    with io.open(os.path.join(d, PS.STORE_NAME), "w", encoding="utf-8") as fh:
        json.dump({"entries": entries, "shard": {"head": "abc123def456"}}, fh)
    if prev is not None:
        with io.open(os.path.join(d, PS.PREV_COSTS_NAME), "w", encoding="utf-8") as fh:
            json.dump({"v": 1, "perProof": prev}, fh)
    return d


def _measure(root):
    out = os.path.join(root, "out", "proof_costs.json")
    r = subprocess.run([sys.executable, os.path.join(HERE, "proof_shard.py"), "--measure-costs", root, "--out", out],
                       capture_output=True, text=True, timeout=120, encoding="utf-8")
    got = None
    if os.path.isfile(out):
        with io.open(out, encoding="utf-8") as fh:
            got = json.load(fh).get("perProof")
    return r.returncode, got, r.stdout + r.stderr


class APriceOnceMeasuredIsNeverForgotten(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="tvd_prices_")

    def test_a_gate_this_round_served_keeps_its_measured_price(self):
        """* THE POINT - the safety-net law was measured once at 57.5 s; a round that serves it must not drop it to the stale 10"""
        _shard(self.root, "proof-shard-1", {"test_measured_now": (4, 30.0)},
               prev={"test_a_safety_net_red_closes_only_its_own_lock": 57.5, "test_measured_now": 12.0})
        _shard(self.root, "proof-shard-2", {"test_other": (3, 8.0)},
               prev={"test_a_safety_net_red_closes_only_its_own_lock": 57.5, "test_measured_now": 12.0})
        rc, got, say = _measure(self.root)
        self.assertEqual(rc, 0, say)
        self.assertAlmostEqual(got.get("test_a_safety_net_red_closes_only_its_own_lock") or 0, 57.5, places=3,
                               msg="a price this round did not re-measure was dropped: %r" % got)
        self.assertAlmostEqual(got["test_measured_now"], 30.0, places=1, msg="this round's measurement did not win")
        self.assertAlmostEqual(got["test_other"], 8.0, places=1)
        self.assertIn("carried from the prices this round was planned on", say)

    def test_a_round_that_measured_nothing_still_hands_on_the_prices(self):
        _shard(self.root, "proof-shard-1", {"test_one_proof": (1, 5.0)}, prev={"test_kept": 21.0})
        rc, got, say = _measure(self.root)
        self.assertEqual((rc, got), (0, {"test_kept": 21.0}), say)

    def test_baseline_no_prices_anywhere_writes_nothing(self):
        """the second eye's rule holds: an empty dir never blanks the table"""
        _shard(self.root, "proof-shard-1", {"test_one_proof": (1, 5.0)})
        rc, got, say = _measure(self.root)
        self.assertEqual((rc, got), (2, None), say)

    def test_every_shard_hands_on_the_prices_it_was_planned_on(self):
        with io.open(WORKFLOW, encoding="utf-8") as fh:
            wf = fh.read()
        code = "\n".join(l.split("#", 1)[0] if l.lstrip().startswith("#") else l for l in wf.split("\n"))
        i = code.index('export HEART2_SHARD_COSTS="$RUNNER_TEMP/heart2-seed/proof_costs.json"')
        j = code.index("python3 -u tv/heart2.py --prove --push --proof-shard", i)
        self.assertIn('if [ -n "${HEART2_SHARD_COSTS:-}" ]; then cp "$HEART2_SHARD_COSTS" "$D/proof_costs.prev.json"; fi',
                      code[i:j], "the shard no longer hands on the prices it was planned on")
        self.assertEqual(PS.PREV_COSTS_NAME, "proof_costs.prev.json", "the workflow and the fan-in name two different files")
        self.assertIn("path: ${{ runner.temp }}/shard-${{ matrix.shard }}/", code,
                      "the shard's artifact is no longer its whole dir, so the prices it handed on never reach the fan-in")

    def test_the_committed_table_carries_the_measured_price_of_the_gate_that_cut_v3880s_shard(self):
        """the stale price that cut shard 5 is gone from the committed table (raised to its measurement, never lowered)"""
        com = PS.proof_costs(os.path.join(HERE, "proof_costs.json"))
        self.assertGreaterEqual(com.get("test_a_safety_net_red_closes_only_its_own_lock") or 0, 50.0,
                                "the gate that cut v3880's shard 5 is priced at its stale 10 s again")


RED_PROOF = [
    {"why": "REG-3401 - a round's saved prices are only what it re-measured again (a served gate's price is forgotten)",
     "file": "tv/proof_shard.py", "find": "        got = dict(prev, **got)\n", "replace": "        got = dict(got)\n", "matches": 1},
    {"why": "REG-3401 - the shard no longer hands on the prices it was planned on",
     "file": ".github/workflows/proof-keys-shards.yml",
     "find": '          if [ -n "${HEART2_SHARD_COSTS:-}" ]; then cp "$HEART2_SHARD_COSTS" "$D/proof_costs.prev.json"; fi\n',
     "replace": "          true\n", "matches": 1},
    {"why": "REG-3401 - a round that measured nothing writes nothing, and the next plan loses every carried price",
     "file": "tv/proof_shard.py", "find": "        if not got and not prev:        # second eye",
     "replace": "        if not got:        # second eye", "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
