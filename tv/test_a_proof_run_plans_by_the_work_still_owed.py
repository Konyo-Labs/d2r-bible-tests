# -*- coding: utf-8 -*-
"""REG-3211 - A PROOF RUN'S SHARDS ARE PLANNED BY THE WORK STILL OWED, NOT BY WHERE THE NAMES FALL.

MEASURED on v3864's Publish (run 42084305066, 2026-11-05, 56 min): shard 6 was assigned 388 proofs (53 gates -
test_a_roster_publish_is_signed_and_a_forgery_is_refused 62, test_the_fleet_says_where_a_river_is_stuck 40) and proved 380
of them again for 49.5 min, shard 13 for 52.8 min, while shard 14 proved 11 in 23.5 min - slowest 3,170 s, mean 2,297 s
(1.38x). Once Publish starts from the exact commit's proofs (REG-3210), most of every plan is SERVED; a plan that priced a
served proof exactly like one it must RUN would land the owed rest wherever the gate names put it. Held here:
  * given the proofs already PROVEN at this exact commit (`served`), the plan costs each at SERVED_PROOF_S with no clean
    run, cuts only the OWED proofs by cost and places them longest-first - so the owed work per shard is balanced
    (a fixture shaped like v3864: the old plan's slowest shard carries 5.1x the mean owed work, this one <=1.25x);
  * every proof is still assigned to exactly one shard (a served proof is served by the shard it belongs to);
  * with no served set the plan is the pre-REG-3211 plan exactly, and the same set in any order cuts the same plan;
  * heart2 reads the set from the seed job's served.json (HEART2_SHARD_SERVED) only for THIS checkout's HEAD - a list
    for another commit, or one that will not read, is UNKNOWN (every proof priced as owed) - and its shard cut hands it
    to the plan; the push sets it before the cut;
  * the shard workflow hands heart2 that file from the one seed every shard downloads.
Fixtures only - no git history read, no network. RED_PROOF below.
"""
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import proof_shard as PS  # noqa: E402
import heart2  # noqa: E402

SHA = "9d9485ea61f7482320cdc47a5d0e05f670776e77"


def _pile():
    """v3864's shape: 200 gates of 1-62 proofs at 2-60 s a proof (the spread proof_costs.json measures); the cache serves
    all but FIFTEEN gates that sit next to each other by name (the roster and river laws of shard 6). Arithmetic, no RNG."""
    sizes, prices = [1, 2, 3, 5, 8, 13, 20, 40, 62], [2.0, 5.0, 10.0, 30.0, 60.0]
    have, pp = [], {}
    for i in range(200):
        g = "g%03d" % i
        have.append((g, g + ".py", [{"i": j} for j in range(sizes[(i * 7) % 9])]))
        pp[g] = prices[(i * 3) % 5]
    owed_gates = set("g%03d" % i for i in range(60, 75))
    served = set((g, j) for g, _f, p in have if g not in owed_gates for j in range(len(p)))
    return have, served, pp, owed_gates


def _owed_load(a, served, pp, n):
    load = [0.0] * n
    for (g, j), k in a.items():
        if (g, j) not in served:
            load[k - 1] += pp[g]
    return load


class ThePlanSpreadsTheOwedWork(unittest.TestCase):

    def test_the_owed_work_is_balanced_where_the_old_plan_piled_it(self):
        have, served, pp, _og = _pile()
        n = 22
        old = PS.plan(have, n, {}, browser=set(), per_proof=pp)
        new = PS.plan(have, n, {}, browser=set(), per_proof=pp, served=served)
        lo, ln = _owed_load(old, served, pp, n), _owed_load(new, served, pp, n)
        mo, mn = sum(lo) / n, sum(ln) / n
        self.assertGreater(max(lo) / mo, 2.0, "PREMISE: the fixture no longer piles owed work under the old plan")
        self.assertLessEqual(max(ln) / mn, 1.25, "the slowest shard carries %.2fx the mean OWED work: %s"
                             % (max(ln) / mn, sorted(ln, reverse=True)[:4]))

    def test_every_proof_is_still_in_exactly_one_shard(self):
        have, served, pp, _og = _pile()
        a = PS.plan(have, 22, {}, browser=set(), per_proof=pp, served=served)
        want = set((g, j) for g, _f, p in have for j in range(len(p)))
        self.assertEqual(set(a), want, "a proof has no shard, or a shard was given a proof that does not exist")
        self.assertTrue(all(1 <= k <= 22 for k in a.values()))

    def test_no_served_set_is_the_old_plan_and_order_never_matters(self):
        have, served, pp, _og = _pile()
        self.assertEqual(PS.plan(have, 7, {}, browser=set(), per_proof=pp),
                         PS.plan(have, 7, {}, browser=set(), per_proof=pp, served=None))
        a1 = PS.plan(have, 7, {}, browser=set(), per_proof=pp, served=sorted(served))
        a2 = PS.plan(list(reversed(have)), 7, {}, browser=set(), per_proof=pp, served=sorted(served, reverse=True))
        self.assertEqual(a1, a2, "two shards given the same proofs in another order cut different plans")

    def test_the_report_says_what_each_shard_is_expected_to_carry(self):
        have, served, pp, _og = _pile()
        rep = {}
        PS.plan(have, 22, {}, browser=set(), per_proof=pp, served=served, report=rep)
        self.assertEqual((rep["owed"], rep["served"]), (239, 3190))
        self.assertEqual(len(rep["wall"]), 22)


class HeartTwoReadsTheServedList(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="served-law-")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.have = [("ga", "ga.py", [{}, {}]), ("gb", "gb.py", [{}])]

    def _file(self, body):
        p = os.path.join(self.d, "served.json")
        with io.open(p, "w", encoding="utf-8") as fh:
            fh.write(body if isinstance(body, str) else json.dumps(body))
        return p

    def test_the_list_of_this_commit_is_read_and_cut_to_the_proofs_in_scope(self):
        p = self._file({"sha": SHA, "served": [["ga", 0], ["ga", 1], ["gz", 0], ["gb", 7], ["ga", "1"]]})
        self.assertEqual(heart2._served_now(self.have, path=p, head=SHA), {("ga", 0), ("ga", 1)})

    def test_another_commits_list_or_a_broken_one_is_unknown(self):
        said = []
        p = self._file({"sha": "e" * 40, "served": [["ga", 0]]})
        self.assertIsNone(heart2._served_now(self.have, path=p, head=SHA, say=said.append),
                          "a served list of another commit priced this commit's plan")
        self.assertIn("not this checkout's HEAD", "\n".join(said))
        self.assertIsNone(heart2._served_now(self.have, path=self._file("{not json"), head=SHA, say=said.append))
        self.assertIsNone(heart2._served_now(self.have, path="", head=SHA))

    def test_the_shard_cut_hands_the_list_to_the_plan(self):
        seen = {}

        def plan(have, n, costs=None, browser=None, per_proof=None, served=None, **_k):
            seen["served"] = served
            return dict(((g, i), 1) for g, _f, p in have for i in range(len(p)))
        self.addCleanup(heart2._SHARD.update, {"spec": None, "manifest": None, "plan": None, "own": None, "served": None})
        heart2._SHARD.update(spec=(1, 2), served={("ga", 0)})
        with mock.patch.object(PS, "plan", plan):
            heart2._shard_cut(self.have, {"ga": [0, 1], "gb": [0]}, ["ga", "gb"], lambda *a, **k: None)
        self.assertEqual(seen.get("served"), {("ga", 0)}, "the shard cut planned without the served list")

    def test_the_push_reads_the_list_before_it_cuts(self):
        with io.open(os.path.join(HERE, "heart2.py"), encoding="utf-8") as fh:
            src = fh.read()
        body = src[src.index("\ndef _prove_push(have,"):src.index("\ndef _reused_ages(")]
        code = "\n".join(l.split("  #")[0].rstrip() for l in body.split("\n") if not l.lstrip().startswith("#"))
        line = '    _SHARD["served"] = _served_now(have, say=say) if _SHARD.get("spec") else None'
        self.assertEqual(code.count(line), 1, "the push no longer reads the served list for a shard")
        self.assertLess(code.index(line), code.index("    order, gates = _shard_cut(have, order, gates, say)"),
                        "the served list is read after the shard was already cut")


class TheWorkflowHandsHeartTwoTheList(unittest.TestCase):

    def test_each_shard_exports_the_seed_jobs_served_list(self):
        with io.open(os.path.join(ROOT, ".github", "workflows", "proof-keys-shards.yml"), encoding="utf-8") as fh:
            wf = fh.read()
        shard = wf[wf.index("\n  shard:\n"):wf.index("\n  fan-in:\n")]
        prove = shard[shard.index("- name: Prove this shard"):]
        self.assertIn('export HEART2_SHARD_SERVED="$RUNNER_TEMP/heart2-seed/served.json"\n', prove)
        self.assertLess(prove.index("HEART2_SHARD_SERVED="), prove.index("python3 -u tv/heart2.py --prove --push"))
        self.assertTrue(re.search(r"\[ -f \"\$HEART2_SHARD_SERVED\" \] \|\| unset HEART2_SHARD_SERVED", prove),
                        "a seed with no served list hands heart2 a path that is not there")


RED_PROOF = [
    {"why": "REG-3211 - the plan ignores what the cache serves: the owed work piles where the names fall (v3864 shard 6)",
     "file": "tv/proof_shard.py",
     "find": "    hit = set((str(g), i) for g, i in (served or ()))\n",
     "replace": "    hit = set()\n",
     "matches": 1},
    {"why": "REG-3211 - a served proof is priced like a run, so the plan balances total work and the owed work piles",
     "file": "tv/proof_shard.py",
     "find": "            chunks.append((SERVED_PROOF_S * len(done), False, name, done))\n",
     "replace": "            chunks.append((u * len(done) + f, b, name, done))\n",
     "matches": 1},
    {"why": "REG-3211 - heart2's shard cut never hands the served list to the plan",
     "file": "tv/heart2.py",
     "find": "                          served=_SHARD.get(\"served\"), report=_rep)",
     "replace": "                          served=None, report=_rep)",
     "matches": 1},
    {"why": "REG-3211 - a served list of another commit prices this commit's plan",
     "file": "tv/heart2.py",
     "find": "    if not head or body.get(\"sha\") != head:\n",
     "replace": "    if not head:\n",
     "matches": 1},
    {"why": "REG-3211 - the push never reads the served list, so every shard plans as before",
     "file": "tv/heart2.py",
     "find": "    _SHARD[\"served\"] = _served_now(have, say=say) if _SHARD.get(\"spec\") else None",
     "replace": "    _SHARD[\"served\"] = None",
     "matches": 1},
    {"why": "REG-3211 - the shard workflow never hands heart2 the served list",
     "file": ".github/workflows/proof-keys-shards.yml",
     "find": "          export HEART2_SHARD_SERVED=\"$RUNNER_TEMP/heart2-seed/served.json\"\n",
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
