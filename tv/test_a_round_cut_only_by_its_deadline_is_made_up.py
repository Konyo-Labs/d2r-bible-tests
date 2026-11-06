# -*- coding: utf-8 -*-
"""REG-3270..3274 - A PROOF ROUND CUT ONLY BY ITS DEADLINE IS MADE UP, AND THE PLAN PRICES ITSELF FROM WHAT IT MEASURED.

MEASURED on v3872 (0d4e24537, ci/proof-keys-v3872 run 42200089396, every one of 9,378 proofs run fresh, 0 served): the
plan modelled each of 22 shards at 1,720 s; they proved for 1,521-3,357 s (job walls 26-57 min). Shards 14 and 22 reached
heart2's minute-55 deadline with 27 proofs still to run (TIMEOUT - no law red), the run went red, and the ship stopped
until the failed shards were re-run by hand an hour later. Held here:
  * REG-3270 the census writes its totals as JSON beside census.md; proof_shard.makeup_due says a round is made up only
    when its ONLY debt is cut proofs (no law owes a fix, every shard left a store); ship_when_green then re-runs the
    failed shards ONCE and waits on - a law that went red, a store that is missing, or a second red is never made up;
  * REG-3271 measure_costs never reads a gap past the job's bound as one proof (shard 14's store held a proof served
    from 04:21 beside 258 run at 10:0x-11:01 - a 6-hour "per-proof" price for that gate);
  * REG-3272 the plan's modelled wall is the work over the lanes times the measured SHARD_WALL_FACTOR (1.30 on v3872;
    real = 1.30 x modelled, residual mean 154 s over 22 shards);
  * REG-3273 the shard's first lines say whether the slowest shard fits PLAN_HEADROOM of the proving window;
  * REG-3274 the prices update themselves: the fan-in measures this round's per-proof costs beside the seed it saves,
    the seed job carries them in the one proof-seed artifact, and every shard's plan reads them (HEART2_SHARD_COSTS)
    over the committed tv/proof_costs.json - all shards one table, so one plan.
Fixtures only: no GitHub, no heart2 run. RED_PROOF below.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import proof_shard as PS  # noqa: E402
import proof_seed as SEED  # noqa: E402
import ship_when_green as SW  # noqa: E402
import ci_verdict as CV  # noqa: E402

SHA = "0d4e24537fe744df866433a808ed69daa2d65ecd"


def _store(d, k, n, owed=(), entries=None):
    os.makedirs(d, exist_ok=True)
    body = {"format": 2, "entries": entries or {},
            "shard": PS.manifest(k, n, SHA, False, "plan1", {"g": {0, 1}}, None, None, 1000, owed=list(owed))}
    with io.open(os.path.join(d, PS.STORE_NAME), "w", encoding="utf-8") as fh:
        json.dump(body, fh)


class TheMakeupDecision(unittest.TestCase):
    def test_only_cut_proofs_are_made_up(self):
        due, why = PS.makeup_due({"cut": [["g", 3, PS.TIMEOUT, "deadline", 14]], "fix": [], "lost": [], "missing": []})
        self.assertTrue(due, why)
        self.assertIn("shard(s) 14", why)

    def test_a_red_law_is_never_made_up(self):
        due, why = PS.makeup_due({"cut": [["g", 3, PS.TIMEOUT, "x", 14]], "fix": [["h", 0, "RED", "x", 2]],
                                  "lost": [], "missing": []})
        self.assertFalse(due)
        self.assertIn("owe a fix", why)

    def test_a_shard_with_no_store_is_never_made_up(self):
        self.assertFalse(PS.makeup_due({"cut": [["g", 3, PS.TIMEOUT, "x", 14]], "fix": [], "lost": [7],
                                        "missing": []})[0])
        self.assertFalse(PS.makeup_due({"cut": [["g", 3, PS.TIMEOUT, "x", 14]], "fix": [], "lost": [],
                                        "missing": ["proof-shard-7"]})[0])

    def test_nothing_cut_and_no_census_are_not_made_up(self):
        self.assertFalse(PS.makeup_due({"cut": [], "fix": [], "lost": [], "missing": []})[0])
        self.assertFalse(PS.makeup_due(None)[0])

    def test_the_census_json_carries_what_the_decision_reads(self):
        t = tempfile.mkdtemp()
        try:
            _store(os.path.join(t, "proof-shard-1"), 1, 2)
            _store(os.path.join(t, "proof-shard-2"), 2, 2, owed=[["g", 1, PS.TIMEOUT, "the run's deadline passed"]])
            out = os.path.join(t, "census.json")
            with open(os.devnull, "w") as nul:
                saved, sys.stdout = sys.stdout, nul
                try:
                    code = PS.main(["--census", t, "--shards", "2", "--head", SHA, "--json", out])
                finally:
                    sys.stdout = saved
            self.assertEqual(code, 0)
            with io.open(out, encoding="utf-8") as fh:
                tot = json.load(fh)
            self.assertEqual(tot["stores"], 2)
            self.assertEqual(tot["lost"], [])
            self.assertEqual(len(tot["cut"]), 1)
            self.assertTrue(tot["makeupDue"], tot["makeupWhy"])
            _store(os.path.join(t, "proof-shard-2"), 2, 2, owed=[["g", 1, "RED", "the law failed"]])
            _t = PS.census(t, SHA, 2)[1]
            self.assertFalse(PS.makeup_due(_t)[0], "a red law read as only cut")
            shutil.rmtree(os.path.join(t, "proof-shard-2"))
            _t = PS.census(t, SHA, 2)[1]
            self.assertEqual(_t["lost"], [2])
            self.assertFalse(PS.makeup_due(_t)[0], "a lost shard read as only cut")
        finally:
            shutil.rmtree(t, ignore_errors=True)


class _Gh(object):
    """A fake `gh`/`git` for ship(): runs on one sha; the proof run red until re-run, then green (or red again)."""

    def __init__(self, census, second="success"):
        self.census, self.second, self.reruns, self.calls = census, second, 0, []

    def runs(self):
        rs = [{"workflowName": wf, "headSha": SHA, "status": "completed", "conclusion": "success",
               "createdAt": "2026-11-06T10:00:00Z", "databaseId": 100 + i} for i, wf in enumerate(CV.REQUIRED)]
        p = rs[3]
        p["databaseId"] = 42200089396
        if self.reruns == 0:
            p["conclusion"] = "failure"
        else:
            p["conclusion"] = self.second
        return rs

    def __call__(self, cmd, **kw):
        self.calls.append(list(cmd))
        out = ""
        if cmd[:3] == ["gh", "run", "download"]:
            d = cmd[cmd.index("-D") + 1]
            if self.census is None:
                return subprocess.CompletedProcess(cmd, 1, "", "no artifact")
            with io.open(os.path.join(d, "census.json"), "w", encoding="utf-8") as fh:
                json.dump(self.census, fh)
        elif cmd[:3] == ["gh", "run", "rerun"]:
            self.reruns += 1
        elif cmd[:2] == ["git", "rev-parse"]:
            out = SHA + "\n"
        elif cmd[:2] == ["git", "ls-remote"]:
            out = "%s\trefs/heads/ci/claude-v3875\n%s\trefs/heads/ci/proof-keys-v3875\n" % (SHA, SHA)
        return subprocess.CompletedProcess(cmd, 0, out, "")


def _ship(gh):
    said, t = [], [0.0]

    def sleep(s):
        t[0] += s

    code = SW.ship("v3875", run=gh, fetch=lambda sha: gh.runs(), sleep=sleep, clock=lambda: t[0],
                   say=said.append, wait_s=600 * 60, preflight=False, watch=None, watch_publish_s=None)
    return code, said


CUT = {"cut": [["test_what_keeps_growing_is_salvaged_then_pruned", 23, PS.TIMEOUT, "deadline", 22]], "fix": [],
       "lost": [], "missing": [], "stores": 22}


class TheShipMakesUpARound(unittest.TestCase):
    def test_a_cut_only_red_is_re_run_once_and_then_ships(self):
        gh = _Gh(CUT)
        code, said = _ship(gh)
        self.assertEqual(gh.reruns, 1, said)
        self.assertEqual(code, 0, "\n".join(said))
        self.assertTrue(any("REG-3270 MAKE-UP" in s for s in said), said)
        self.assertIn(["git", "-c", "core.hooksPath=hooks", "push", "origin", "HEAD:main"], gh.calls)

    def test_a_second_red_on_the_same_run_stops_the_ship(self):
        gh = _Gh(CUT, second="failure")
        code, said = _ship(gh)
        self.assertEqual(gh.reruns, 1, "a red re-run was re-run again")
        self.assertEqual(code, 1, said)
        self.assertNotIn(["git", "-c", "core.hooksPath=hooks", "push", "origin", "HEAD:main"], gh.calls)

    def test_a_red_law_is_not_re_run(self):
        gh = _Gh(dict(CUT, fix=[["test_x", 0, "RED", "failed", 3]]))
        code, said = _ship(gh)
        self.assertEqual(gh.reruns, 0)
        self.assertEqual(code, 1)
        self.assertTrue(any("not made up" in s for s in said), said)

    def test_an_unreadable_census_is_not_re_run(self):
        gh = _Gh(None)
        code, said = _ship(gh)
        self.assertEqual((gh.reruns, code), (0, 1), said)


class ThePricesMeasureThemselves(unittest.TestCase):
    def test_a_gap_past_the_jobs_bound_is_not_one_proof(self):
        t0 = 1793960000000
        body = {"entries": {
            "a": {"gate": "g", "provedAt": t0},                                   # served from an older round
            "b": {"gate": "g", "provedAt": t0 + 6 * 3600 * 1000},
            "c": {"gate": "g", "provedAt": t0 + 6 * 3600 * 1000 + 40000}}}
        self.assertEqual(PS.measure_costs([body]), {"g": 40.0})

    def test_the_last_rounds_prices_win_over_the_committed_table(self):
        t = tempfile.mkdtemp()
        try:
            base = PS.proof_costs(env={})
            self.assertTrue(base and len(base) > 300, "the committed table is not read")
            g = sorted(base)[0]
            f = os.path.join(t, "proof_costs.json")
            with io.open(f, "w", encoding="utf-8") as fh:
                json.dump({"perProof": {g: base[g] + 77.0, "a_gate_only_the_round_measured": 3.0}}, fh)
            got = PS.proof_costs(env={"HEART2_SHARD_COSTS": f})
            self.assertEqual(got[g], base[g] + 77.0)
            self.assertEqual(got["a_gate_only_the_round_measured"], 3.0)
            self.assertEqual(len(got), len(base) + 1)
            self.assertEqual(PS.proof_costs(env={"HEART2_SHARD_COSTS": os.path.join(t, "absent.json")}), base)
            with io.open(f, "w", encoding="utf-8") as fh:
                fh.write("{not json")
            self.assertEqual(PS.proof_costs(env={"HEART2_SHARD_COSTS": f}), base, "a broken round file replaced the table")
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_the_seed_carries_the_prices_and_refuses_a_broken_file(self):
        t = tempfile.mkdtemp()
        try:
            rest, out = os.path.join(t, "restored"), os.path.join(t, "out")
            os.makedirs(rest)
            os.makedirs(out)
            self.assertEqual(SEED.carry_prices(rest, out, say=lambda *_: None), 0)
            with io.open(os.path.join(rest, SEED.PRICES_NAME), "w", encoding="utf-8") as fh:
                json.dump({"perProof": {"g": 12.5}}, fh)
            self.assertEqual(SEED.carry_prices(rest, out, say=lambda *_: None), 1)
            self.assertEqual(PS.proof_costs(os.path.join(out, SEED.PRICES_NAME)), {"g": 12.5})
            os.remove(os.path.join(out, SEED.PRICES_NAME))
            with io.open(os.path.join(rest, SEED.PRICES_NAME), "w", encoding="utf-8") as fh:
                fh.write("[]")
            self.assertEqual(SEED.carry_prices(rest, out, say=lambda *_: None), 0)
            self.assertFalse(os.path.exists(os.path.join(out, SEED.PRICES_NAME)))
        finally:
            shutil.rmtree(t, ignore_errors=True)


class ThePlanSaysItsRealWall(unittest.TestCase):
    def test_the_modelled_wall_carries_the_measured_factor(self):
        have = [("g%d" % i, "f", [{"i": j} for j in range(4)]) for i in range(6)]
        rep = {}
        PS.plan(have, 2, {"g%d" % i: 10.0 for i in range(6)}, browser=set(), per_proof={}, report=rep)
        self.assertEqual(rep["factor"], PS.SHARD_WALL_FACTOR)
        raw = [w / PS.SHARD_WALL_FACTOR for w in rep["wall"]]
        for w, t in zip(raw, rep["work"]):
            self.assertAlmostEqual(w, t / PS.RUNNER_LANES, delta=0.2)
        self.assertGreater(PS.SHARD_WALL_FACTOR, 1.0, "the plan models less than the shards really take")

    def test_headroom_is_said_both_ways(self):
        ok, why = PS.headroom([0.5 * PS.PROVE_WINDOW_S])
        self.assertTrue(ok, why)
        bad, why = PS.headroom([0.78 * PS.PROVE_WINDOW_S, 100.0])
        self.assertFalse(bad)
        self.assertIn("over the 70% headroom", why)
        self.assertFalse(PS.headroom(None)[0] and PS.headroom(["x"])[0])

    def test_the_shard_says_its_headroom(self):
        with io.open(os.path.join(HERE, "heart2.py"), encoding="utf-8") as fh:
            src = fh.read()
        line = '    say("  REG-3273 HEADROOM: %s" % _PS.headroom(_w)[1] if _w else "  REG-3273 HEADROOM: UNKNOWN - the plan said no wall")\n'
        self.assertEqual(src.count(line), 1)


class TheWorkflowCarriesIt(unittest.TestCase):
    def setUp(self):
        with io.open(os.path.join(ROOT, ".github", "workflows", "proof-keys-shards.yml"), encoding="utf-8") as fh:
            self.y = "\n".join(l for l in fh.read().split("\n") if not l.lstrip().startswith("#"))

    def test_the_census_writes_and_keeps_its_json(self):
        self.assertEqual(self.y.count('--out census.md \\\n            --json census.json\n'), 1)
        self.assertEqual(self.y.count("          path: |\n            census.md\n            census.json\n"), 1)

    def test_the_fan_in_saves_the_rounds_prices_beside_the_seed(self):
        line = '          python3 tv/proof_shard.py --measure-costs shards --out "$RUNNER_TEMP/heart2-seed/proof_costs.json" || true\n'
        self.assertEqual(self.y.count(line), 1)
        self.assertLess(self.y.index('--merge-shards shards --out "$RUNNER_TEMP/heart2-seed/.heart2_cache.json"'),
                        self.y.index(line))

    def test_every_shard_reads_the_carried_prices(self):
        prove = self.y[self.y.index("- name: Prove this shard"):]
        line = '          export HEART2_SHARD_COSTS="$RUNNER_TEMP/heart2-seed/proof_costs.json"\n'
        self.assertEqual(prove.count(line), 1)
        self.assertLess(prove.index(line), prove.index("python3 -u tv/heart2.py --prove --push"))


RED_PROOF = [
    {"why": "REG-3270 - a round with a red law is made up as if only cut",
     "file": "tv/proof_shard.py",
     "find": "    if fix:\n        return False, \"%d proof(s) owe a fix (a law went red) - a re-run cannot make that up\" % len(fix)\n",
     "replace": "    if False:\n        return False, \"\"\n",
     "matches": 1},
    {"why": "REG-3270 - a missing shard store is made up",
     "file": "tv/proof_shard.py",
     "find": "    if lost or missing:\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "REG-3270 - the census JSON never says what the decision reads",
     "file": "tv/proof_shard.py",
     "find": "               lost=lost, missing=missing, stores=len(rows))      # REG-3270 - what makeup_due reads\n",
     "replace": "               stores=len(rows))\n",
     "matches": 1},
    {"why": "REG-3270 - the ship never makes a round up",
     "file": "tv/ship_when_green.py",
     "find": "            elif only_proofs and makeup(sha, runs, run, say, made, clock):\n",
     "replace": "            elif False:\n",
     "matches": 1},
    {"why": "REG-3270 - a made-up run is made up again and again",
     "file": "tv/ship_when_green.py",
     "find": "    if not rid or rid in made:\n",
     "replace": "    if not rid:\n",
     "matches": 1},
    {"why": "REG-3271 - a gap that spans two rounds prices one proof",
     "file": "tv/proof_shard.py",
     "find": "if x <= MAX_PROOF_GAP_S)",
     "replace": "if x >= 0)",
     "matches": 1},
    {"why": "REG-3272 - the modelled wall drops the measured factor",
     "file": "tv/proof_shard.py",
     "find": "        report.update(wall=[round(SHARD_WALL_FACTOR * max(t / lanes, w), 1) for t, w in zip(tot, brw)],\n",
     "replace": "        report.update(wall=[round(max(t / lanes, w), 1) for t, w in zip(tot, brw)],\n",
     "matches": 1},
    {"why": "REG-3273 - an over-full plan reads as fitting",
     "file": "tv/proof_shard.py",
     "find": "    if w <= share * window:\n",
     "replace": "    if True:\n",
     "matches": 1},
    {"why": "REG-3274 - the round's prices never reach the plan",
     "file": "tv/proof_shard.py",
     "find": "        out.update(last)\n",
     "replace": "        pass\n",
     "matches": 1},
    {"why": "REG-3274 - a broken round file is carried into every shard",
     "file": "tv/proof_seed.py",
     "find": "    if not got:\n        say(\"  REG-3274 PRICES: no measured prices",
     "replace": "    if got is None and False:\n        say(\"  REG-3274 PRICES: no measured prices",
     "matches": 1},
    {"why": "REG-3274 - the fan-in never saves the round's prices",
     "file": ".github/workflows/proof-keys-shards.yml",
     "find": "          python3 tv/proof_shard.py --measure-costs shards --out \"$RUNNER_TEMP/heart2-seed/proof_costs.json\" || true\n",
     "replace": "          true\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
