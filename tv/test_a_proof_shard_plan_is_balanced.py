# -*- coding: utf-8 -*-
"""REG-2593 — THE PROOF SHARD PLAN IS PRICED BY WHAT A PROOF MEASURED ON A RUNNER, AND BALANCED ON THE BROWSER QUEUE.

⚠ WHAT IT IS FOR. The 16-shard CI run at dcff7160 measured the old plan: slowest shard about 2.1x the mean. Two causes:
the plan priced a proof from gate_costs.json (seconds per gate run ON HIS MAC, + a fixed overhead), which is not what a
proof costs on a 2-lane runner; and the gates that start a browser are proved ONE AT A TIME on a runner, so a shard
handed several big browser gates waits on a serial queue the plan never saw.

⚠ THE RULE. proof_costs.json holds the seconds per proof MEASURED on a runner (measure_costs: the median provedAt gap
of each gate's back-to-back proofs). A chunk costs per-proof x (size + 2) (its proofs and the gate's two clean runs).
Every gate is cut at one target (cutting browser gates finer MODELLED slower: each chunk pays two
clean runs again), and each chunk goes to the shard whose WALL grows least: max(its work / lanes, its browser
queue). heart2's shard cut and its push-time lock use ONE rule for which gates are browser gates (_push_browser).

⚠ THE DEFECTS THIS GUARDS:
  · the measured costs dropped (the plan prices from the Mac again) or misread;
  · the browser queue not balanced: big browser gates pile into one shard;
  · the wall-clock model swapped back to total work (a 2-lane runner's wall is not its work);
  · heart2's shard cut plans without the browser set or the measured costs.
The tree's own gates are read (parsed, never imported). RED_PROOF below.
"""
import collections
import json
import os
import shutil
import statistics
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402  (it prints non-ASCII)
_console_safe_enable()
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
import heart2         # noqa: E402
import proof_shard as PS  # noqa: E402

LIMIT = 1.2           # the slowest shard's modelled wall over the mean, at N=16 on this tree


def walls(have, a, n, browser, per_proof, costs):
    """Each shard's modelled wall: max(work / lanes, browser queue), every chunk priced as plan prices it."""
    known = sorted(v for v in costs.values() if v > 0)
    default = known[len(known) // 2] if known else 1.0
    own = collections.defaultdict(collections.Counter)
    for (g, _i), k in a.items():
        own[k][g] += 1
    out = []
    for k in range(1, n + 1):
        tot = brw = 0.0
        for g, c in own[k].items():
            u = per_proof.get(g)
            if u is None:
                u = PS.cost_factor(costs, per_proof)[0] * ((costs.get(g) or default) + PS.PROOF_OVERHEAD_S)   # v3883
            tot += u * (c + 2)
            if g in browser:
                brw += u * (c + 2)
        out.append(max(tot / PS.RUNNER_LANES, brw))
    return out


class OnThisTree(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        have = [(n, f, heart2.red_proofs_in(f)) for n, f in heart2.gate_files(say=lambda *a, **k: None)]
        cls.have = [(n, f, p) for n, f, p in have if p]
        cls.browser = heart2._push_browser(cls.have)
        cls.pp = PS.proof_costs()
        cls.costs = PS.gate_costs()

    def test_the_measured_costs_are_read(self):
        self.assertGreater(len(self.pp), 300, "proof_costs.json is not read - the plan prices from his Mac again")

    def test_the_slowest_shard_is_within_the_limit_of_the_mean(self):
        a = PS.plan(self.have, 16, self.costs, browser=self.browser, per_proof=self.pp)
        self.assertEqual(len(a), sum(len(p) for _n, _f, p in self.have), "a proof has no shard")
        w = walls(self.have, a, 16, self.browser, self.pp, self.costs)
        ratio = max(w) / statistics.mean(w)
        self.assertLessEqual(ratio, LIMIT, "slowest shard %.0fs is %.2fx the mean %.0fs" % (
            max(w), ratio, statistics.mean(w)))


class ThePlanItself(unittest.TestCase):

    def test_big_browser_gates_never_share_a_shard_while_one_has_none(self):
        have = [("b%d" % i, "b%d.py" % i, [{}] * 4) for i in range(4)] + [("w", "w.py", [{}] * 40)]
        pp = dict(("b%d" % i, 50.0) for i in range(4))
        pp["w"] = 5.0
        a = PS.plan(have, 4, {}, browser={"b0", "b1", "b2", "b3"}, per_proof=pp)
        per = collections.defaultdict(float)
        for (g, _i), k in a.items():
            if g.startswith("b"):
                per[k] += 50.0
        self.assertEqual(sorted(per), [1, 2, 3, 4], "the browser work piled into %s" % dict(per))

    def test_a_shard_wall_is_its_work_over_its_lanes(self):
        # one big browser proof (its shard's wall is its serial queue, 150 s) and ten CPU proofs of 30 s: balancing
        # total WORK hands the browser shard five of them and leaves the other at half its wall (ratio 1.33); the
        # wall-aware placement fills the browser shard's idle lane instead (second eye, REG-2593)
        have = [("br", "br.py", [{}])] + [("c%d" % i, "c%d.py" % i, [{}]) for i in range(10)]
        pp = dict(("c%d" % i, 10.0) for i in range(10))
        pp["br"] = 50.0
        a = PS.plan(have, 2, {}, browser={"br"}, per_proof=pp, lanes=2)
        w = walls(have, a, 2, {"br"}, pp, {})
        self.assertLessEqual(max(w) / statistics.mean(w), 1.1, w)


class TheMeasuredCosts(unittest.TestCase):

    def test_the_median_gap_between_back_to_back_proofs(self):
        b1 = {"entries": {"1": {"gate": "g", "provedAt": 0}, "2": {"gate": "g", "provedAt": 2000},
                          "3": {"gate": "g", "provedAt": 4000}, "4": {"gate": "solo", "provedAt": 9},
                          "5": "junk", "6": {"gate": "g", "provedAt": True}}}
        b2 = {"entries": {"1": {"gate": "g", "provedAt": 10000}, "2": {"gate": "g", "provedAt": 19000}}}
        self.assertEqual(PS.measure_costs([b1, b2]), {"g": 2.0})
        b3 = {"entries": {"1": {"gate": "h", "provedAt": 0}, "2": {"gate": "h", "provedAt": 1000},
                          "3": {"gate": "h", "provedAt": 4000}, "4": {"gate": "h", "provedAt": 9000}}}
        self.assertEqual(PS.measure_costs([b3]), {"h": 3.0}, "an even count's median is the mean of the middle two")

    def test_the_file_is_read_and_junk_dropped(self):
        tmp = tempfile.mkdtemp(prefix="pcosts-")
        self.addCleanup(shutil.rmtree, tmp, True)
        p = os.path.join(tmp, "proof_costs.json")
        with open(p, "w", encoding="utf-8") as fh:
            json.dump({"v": 1, "perProof": {"a": 2.5, "b": 0, "c": True, "d": "x", "e": 7}}, fh)
        self.assertEqual(PS.proof_costs(p), {"a": 2.5, "e": 7.0})
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        self.assertIsNone(PS.proof_costs(p))            # REG-2597 - unreadable is UNKNOWN, never "no costs"
        self.assertEqual(PS.proof_costs(os.path.join(tmp, "never_written.json")), {})

    def test_the_factor_is_the_one_the_measured_costs_give(self):
        """REG-3243 - a gate with no per-proof row of its own is priced at PROOF_COST_FACTOR x its clean run, and that ratio
        is read off the same measurements as proof_costs.json. Re-measuring the file and leaving the factor behind is how
        v3867's plan priced every shard at ~18 min while they ran 18-55 (shard 7 hit the 55-minute deadline with 6 proofs
        unstarted). The factor stays within 0.1 of the table's own median ratio."""
        pp, gc = PS.proof_costs(), PS.gate_costs()
        r = [pp[k] / (gc[k] + PS.PROOF_OVERHEAD_S) for k in pp if gc.get(k) and pp[k] > 0]
        self.assertGreater(len(r), 300, "premise: too few gates carry both a per-proof and a clean-run cost (%d)" % len(r))
        med = statistics.median(r)
        # v3883 (#129) - the plan DERIVES the factor from the table it is handed; the constant is only a thin table's fallback
        f, rows = PS.cost_factor(gc, pp)
        self.assertEqual(rows, len(r))
        self.assertAlmostEqual(f, med, places=9, msg="the plan prices an unmeasured gate at %.3f, the table's median is %.3f"
                               % (f, med))
        rep = {}
        PS.plan([("g", "g.py", [{}] * 3)], 1, costs=gc, per_proof=pp, report=rep)
        self.assertEqual(rep.get("costFactor", {}).get("derived"), True, rep.get("costFactor"))

    def test_a_round_seed_moves_the_factor_with_it(self):
        """v3883 - v3881's round 3: the seed's median was 0.741 and a fixed 0.62 priced the shards short; a derived factor
        follows whichever table the round plans with"""
        cs = dict(("g%d" % i, 10.0) for i in range(80))
        slow = dict((g, 0.9 * (10.0 + PS.PROOF_OVERHEAD_S)) for g in cs)
        self.assertAlmostEqual(PS.cost_factor(cs, slow)[0], 0.9)
        self.assertEqual(PS.cost_factor(cs, dict(list(slow.items())[:10])), (PS.PROOF_COST_FACTOR, 10),
                         "a thin table priced every unmeasured gate")
        a = PS.plan([("x", "x.py", [{}] * 4)], 1, costs=dict(cs, x=10.0), per_proof=slow, report={})
        self.assertEqual(sorted(a.values()), [1, 1, 1, 1])


class HeartTwosCutUsesIt(unittest.TestCase):

    def test_the_shard_cut_plans_with_the_browser_set_and_the_measured_costs(self):
        seen = {}

        def plan(have, n, costs=None, browser=None, per_proof=None, **_k):
            seen.update(browser=browser, per_proof=per_proof)
            return dict(((g, i), 1) for g, _f, p in have for i in range(len(p)))
        have = [("g", "g.py", [{}, {}])]
        self.addCleanup(heart2._SHARD.update, {"spec": None, "manifest": None, "plan": None, "own": None})
        heart2._SHARD.update(spec=(1, 2))
        with mock.patch.object(PS, "plan", plan), \
                mock.patch.object(PS, "proof_costs", lambda *a: {"g": 3.0}), \
                mock.patch.object(heart2, "_push_browser", lambda have, unk=None: {"g"}):
            heart2._shard_cut(have, {"g": [0, 1]}, ["g"], lambda *a, **k: None)
        self.assertEqual(seen, {"browser": {"g"}, "per_proof": {"g": 3.0}})


RED_PROOF = [
    {"why": "REG-3243 / v3883 - the factor is left behind the re-measured costs (v3867's shards ran 3x their plan, v3881 lost "
            "a round): the plan prices unmeasured gates at the constant again, not at the table's own median",
     "file": "proof_shard.py",
     "find": "    factor, _frows = cost_factor(costs, pp) if per_proof is not None else (PROOF_COST_FACTOR, 0)   # v3883\n",
     "replace": "    factor, _frows = PROOF_COST_FACTOR, 0\n",
     "matches": 1},
    {"why": "v3883 - the derived factor is not the table's median (the largest ratio)",
     "file": "proof_shard.py",
     "find": "    return (r[m] if len(r) % 2 else (r[m - 1] + r[m]) / 2.0), len(r)\n",
     "replace": "    return r[-1], len(r)\n",
     "matches": 1},
    {"why": "REG-2593 - the measured costs are never read: the plan prices every proof from his Mac again",
     "file": "proof_shard.py",
     "find": "            c = json.load(fh).get(\"perProof\") or {}\n",
     "replace": "            c = {}\n",
     "matches": 1},
    {"why": "REG-2593 - the plan balances total work, not the wall: the browser queue piles up",
     "file": "proof_shard.py",
     "find": "            k = min(range(n), key=lambda s: (max((tot[s] + cost) / lanes, brw[s] + (cost if b else 0.0)), tot[s], s))\n",
     "replace": "            k = min(range(n), key=lambda s: (tot[s], s))\n",
     "matches": 1},
    {"why": "REG-2597 - an unreadable cost file is handed back as \"no costs\", a measurement nobody took",
     "file": "proof_shard.py",
     "find": "        return None                     # REG-2597 - there and unreadable is UNKNOWN, never \"no costs\"\n",
     "replace": "        return {}\n",
     "matches": 2},
    {"why": "REG-2593 - the median is misread (the largest gap)",
     "file": "proof_shard.py",
     "find": "            out[g] = round(v[m] if len(v) % 2 else (v[m - 1] + v[m]) / 2.0, 3)\n",
     "replace": "            out[g] = round(v[-1], 3)\n",
     "matches": 1},
    {"why": "REG-2593 - heart2's shard cut plans without the browser set",
     "file": "heart2.py",
     "find": "    assignment = _PS.plan(have, n, _PS.gate_costs(), browser=_push_browser(have), per_proof=_PS.proof_costs(),\n",
     "replace": "    assignment = _PS.plan(have, n, _PS.gate_costs(), browser=set(), per_proof=_PS.proof_costs(),\n",
     "matches": 1},
    {"why": "REG-2593 - heart2's shard cut plans without the measured costs",
     "file": "heart2.py",
     "find": "    assignment = _PS.plan(have, n, _PS.gate_costs(), browser=_push_browser(have), per_proof=_PS.proof_costs(),\n",
     "replace": "    assignment = _PS.plan(have, n, _PS.gate_costs(), browser=_push_browser(have), per_proof={},\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
