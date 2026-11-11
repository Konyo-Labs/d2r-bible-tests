# -*- coding: utf-8 -*-
"""v3891 (#194) - A PROOF ROUND CHOOSES ITS OWN SHARD COUNT, AND EACH ROUND STARTS FROM WHAT THE LAST ONE LEARNED.

His words, 11-09 (the repo went to Konyo-Labs and came back to Pro, ~40 shared workers, the counts capped at today's): "optimize the #194 all the way and make sure it keeps
getting faster self improve it". MEASURED on v3889's round: workers were not the wait (Routine I waited <= 1 min, Publish
up to 15); the slowest proof shard ran 43 min of a hand-set 22. And cold on v3891's tree, even 160 shards modelled a
slowest prove of 1,064 s: one test_control proof (~270 s) and its two clean runs - the floor more shards cannot beat.
Held here:
  * proof_shard.choose_n: the fewest shards whose slowest MODELLED prove (plan()'s own model) fits the target, or - when
    one chunk alone is over it - the fewest that reach that floor, never every shard the bound allows;
  * heart2 --plan-shards: n= and list= 1..n, and the fallback count when the plan cannot be cut (never a red round);
  * the workflow: the seed job asks it (the same served list and carried prices every shard plans from);
  * THE RED MEMORY TRAVELS: each shard starts from the last round's (which cases caught each sabotage - #42 lever 1, which
    only ever saves time), the fan-in merges every shard's with heart2's own rule (newest learning wins a key), and the
    seed carries it;
  * the Mac's import reads the set's size from the shards' own manifests;
  * the agent suite: run_gates.choose_shards takes the fewest slices whose heaviest fits the target, or the floor of
    the heaviest single gate; GATE_COSTS (the last round's table) wins over the committed tv/gate_costs.json; gate_costs
    --base keeps every gate the round did not run; the plan job chooses the count, hands one table, and the verdict
    re-measures; hashFiles() never sees runner.temp.
RED_PROOF below. [[heart-first]] [[the-unjoined-end]]
"""
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import proof_shard as PS  # noqa: E402
import proof_seed as SEED  # noqa: E402
import proof_keys_mac as PKM  # noqa: E402
import routine_i_shards as RIS  # noqa: E402

RI_WF = os.path.join(ROOT, ".github", "workflows", "routine-i-playwright.yml")
TV_WF = os.path.join(ROOT, ".github", "workflows", "tv-tests.yml")

WF = os.path.join(ROOT, ".github", "workflows", "proof-keys-shards.yml")
PR = {"why": "x", "file": "tv/x.py", "find": "a", "replace": "b", "matches": 1}


def _have(gates=20, proofs=10):
    return [("g%02d" % i, "test_g%02d.py" % i, [dict(PR) for _ in range(proofs)]) for i in range(gates)]


def _kw(per=30.0, extra=None):
    costs = dict(("g%02d" % i, 5.0) for i in range(20))
    pp = dict(("g%02d" % i, per) for i in range(20))
    for g, (run, proof) in (extra or {}).items():
        costs[g], pp[g] = run, proof
    return {"costs": costs, "browser": set(), "per_proof": pp, "caps": {}}


def _slowest(have, n, kw):
    rep = {}
    PS.plan(have, n, report=rep, **kw)
    return max(rep["wall"])


def _wf():
    with io.open(WF, encoding="utf-8") as fh:
        return fh.read()


def _job(text, name):
    m = re.search(r"\n  %s:\n(.*?)(?=\n  [A-Za-z][\w-]*:\n|\Z)" % re.escape(name), "\n" + text.split("\njobs:\n", 1)[-1] + "\n",
                  re.S)
    return m.group(1) if m else ""


class TheCountIsTheFewestThatFits(unittest.TestCase):

    def test_the_fewest_shards_whose_slowest_fits_the_target(self):
        """* THE POINT - 200 proofs of 30 s against a 10-minute target: the chosen n fits, and n - 1 does not"""
        have, kw = _have(), _kw()
        n, info = PS.choose_n(have, n_min=1, n_max=64, target_s=600, **kw)
        self.assertLessEqual(_slowest(have, n, kw), 600, info)
        self.assertGreater(_slowest(have, n - 1, kw), 600, "n - 1 also fits - the count is not the fewest: %r" % info)
        self.assertLess(n, 64, "the chooser took every shard the bound allows")

    def test_past_the_floor_more_shards_are_not_asked_for(self):
        """one 1,000-s proof: its chunk alone is over the target, so the count is the fewest that reach that floor"""
        have = _have() + [("big", "test_big.py", [dict(PR)])]
        kw = _kw(extra={"big": (300.0, 1000.0)})
        n, info = PS.choose_n(have, n_min=1, n_max=64, target_s=600, **kw)
        floor = _slowest(have, 64, kw)
        self.assertGreater(floor, 600, "PREMISE: the fixture's floor is over the target")
        self.assertLess(n, 64, "past the floor the round still asked for every shard: %r" % info)
        self.assertLessEqual(_slowest(have, n, kw), floor * PS.FLOOR_SLACK, info)
        self.assertIn("floor", info["why"])
        # v3896 (REG-3675) - the floor is said as the slowest SHARD at the most shards, never as one chunk to split
        self.assertIn("even at 64 shards the slowest shard models", info["why"])

    def test_the_plan_mode_prints_one_count_and_its_list_and_falls_back_when_it_cannot_cut(self):
        import heart2 as H
        out = tempfile.mkdtemp(prefix="plan_shards_")
        try:
            real = PS.choose_n
            PS.choose_n = lambda have, **kw: (7, {"why": "fixture"})
            try:
                H.plan_shards(output=os.path.join(out, "o1"), say=lambda *a, **k: None)
            finally:
                PS.choose_n = real
            PS.choose_n = lambda have, **kw: (_ for _ in ()).throw(RuntimeError("no plan"))
            try:
                H.plan_shards(fallback=22, output=os.path.join(out, "o2"), say=lambda *a, **k: None)
            finally:
                PS.choose_n = real
            for name, n in (("o1", 7), ("o2", 22)):
                with io.open(os.path.join(out, name), encoding="utf-8") as fh:
                    lines = dict(l.split("=", 1) for l in fh.read().split("\n") if "=" in l)
                self.assertEqual(int(lines["n"]), n)
                self.assertEqual(json.loads(lines["list"]), list(range(1, n + 1)), "the list is not every shard 1..n")
        finally:
            shutil.rmtree(out, ignore_errors=True)

    def test_the_seed_job_asks_the_plan_over_the_shards_own_inputs(self):
        seed = _job(_wf(), "seed")
        i = seed.index("name: Choose this round's shard count")
        step = seed[i:seed.index("- name:", i + 10)]
        self.assertIn('export HEART2_SHARD_SERVED="$RUNNER_TEMP/seed-out/served.json"', step)
        self.assertIn('export HEART2_SHARD_COSTS="$RUNNER_TEMP/seed-out/proof_costs.json"', step)
        self.assertIn("continue-on-error: true", step, "a plan that cannot be cut would fail the round")


class TheWallFactorIsMeasuredEveryRound(unittest.TestCase):
    """The planner's 1.30 (real prove time over modelled, fitted once by hand on v3872) is re-fitted from every round's own
    shards and carried with the prices - upward only (REG-3365's rule: under-planning costs a whole round)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="wall_fit_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _shard(self, k, model, real):
        d = os.path.join(self.tmp, "proof-shard-%d" % k)
        os.makedirs(d)
        with io.open(os.path.join(d, "prove.log"), "w", encoding="utf-8") as fh:
            fh.write("  REG-3211 OWED-WORK PLAN: x; this shard's modelled wall %d s, the slowest shard's 9 s\n"
                     "prove_seconds=%d rc=0\n" % (model, real))
        return d

    def test_a_round_that_ran_slower_than_modelled_raises_the_factor(self):
        """* THE POINT - three shards ran 1.5x their model: the next plan multiplies by 1.30 x 1.5"""
        dirs = [self._shard(1, 600, 900), self._shard(2, 800, 1200), self._shard(3, 1000, 1500), self._shard(4, 60, 600)]
        self.assertEqual(PS.fit_wall_factor(dirs, current=1.30), 1.95, "the tiny shard (60 s modelled) is noise, not data")

    def test_a_shard_the_deadline_cut_is_no_wall_sample(self):
        """v3894 - MEASURED: the #92 rounds' shards were all cut at ~57 min; their 'real' was the deadline, and the factor
        climbed to its 3.0 cap. A cut shard is left out; the honest shards decide."""
        dirs = [self._shard(1, 600, 900), self._shard(2, 800, 1200), self._shard(3, 1000, 1500)]
        cut = self._shard(9, 600, 3300)
        with io.open(os.path.join(cut, "prove.log"), "a", encoding="utf-8") as fh:
            fh.write("     OWED x[3] TIMEOUT - %s - the run's deadline passed 30 s ago\n" % PS.CUT_AT_BOUND)
        self.assertEqual(PS.fit_wall_factor(dirs + [cut], current=1.30), 1.95,
                         "a deadline-cut shard's wall (the deadline) moved the factor")
        self.assertIsNone(PS.fit_wall_factor([cut], current=1.30), "a round of cut shards alone measured a factor")

    def test_a_round_that_ran_faster_never_sinks_it_below_the_committed_factor(self):
        dirs = [self._shard(1, 1000, 300), self._shard(2, 1000, 400)]
        self.assertEqual(PS.fit_wall_factor(dirs, current=1.30), PS.SHARD_WALL_FACTOR)

    def test_the_plan_and_the_seed_use_the_carried_factor(self):
        prices = os.path.join(self.tmp, "proof_costs.json")
        with io.open(prices, "w", encoding="utf-8") as fh:
            json.dump({"v": 1, "perProof": {"g00": 30.0}, "wallFactor": 1.8}, fh)
        old = os.environ.get("HEART2_SHARD_COSTS")
        os.environ["HEART2_SHARD_COSTS"] = prices
        try:
            rep = {}
            PS.plan(_have(), 4, report=rep, **_kw())
            self.assertEqual(rep["factor"], 1.8, "the plan ignored the factor the last round measured")
        finally:
            if old is None:
                os.environ.pop("HEART2_SHARD_COSTS", None)
            else:
                os.environ["HEART2_SHARD_COSTS"] = old
        restored, out = os.path.join(self.tmp, "r"), os.path.join(self.tmp, "o")
        os.makedirs(restored)
        os.makedirs(out)
        shutil.copy(prices, os.path.join(restored, SEED.PRICES_NAME))
        SEED.carry_prices(restored, out, say=lambda *a, **k: None)
        with io.open(os.path.join(out, SEED.PRICES_NAME), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh).get("wallFactor"), 1.8, "the seed dropped the measured factor")


class TheRedMemoryTravels(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="red_travels_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _mem(self, name, entries):
        d = os.path.join(self.tmp, "shards", name)
        os.makedirs(d)
        p = os.path.join(d, ".heart2_red.json")
        with io.open(p, "w", encoding="utf-8") as fh:
            json.dump({"format": 2, "entries": entries}, fh)
        return p

    def test_the_count_never_lands_in_the_checkout(self):
        """the seed's count is a step output (GITHUB_OUTPUT, outside the checkout) - a path inside the tree is refused"""
        import heart2 as H
        inside = os.path.join(H.REPO, "tv", ".plan_shards_probe_%d" % os.getpid())
        said = []
        try:
            H.plan_shards(fallback=22, output=inside, say=said.append)
            self.assertFalse(os.path.exists(inside), "the shard count was written into the checkout")
            self.assertTrue(any("refused" in x for x in said), said)
        finally:
            if os.path.exists(inside):
                os.remove(inside)

    def test_the_fan_in_writes_only_a_red_memory_file(self):
        """the fan-in writes the seed's red file and nothing else - a wrong --red-out never overwrites another file"""
        import heart2 as H
        import proof_seed as PS
        self.assertEqual(H._SEED_RED_NAME, PS.RED_NAME, "heart2 and the seed name the travelling red memory differently")
        a = self._mem("proof-shard-1", {"k1": {"gate": "g", "proof": 0, "ids": ["x"], "at": 1000, "usedAt": 1000}})
        victim = os.path.join(self.tmp, "seed", "prices.json")
        os.makedirs(os.path.dirname(victim))
        with io.open(victim, "w", encoding="utf-8") as fh:
            fh.write("{}")
        said = []
        self.assertEqual(H.merge_red_files([a], victim, say=said.append), 0)
        with io.open(victim, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "{}", "the fan-in overwrote a file that is not a red memory")
        self.assertTrue(any("refused" in x for x in said), said)
        ok = os.path.join(self.tmp, "seed", PS.RED_NAME)
        H.merge_red_files([a], ok, say=lambda *x, **k: None)
        self.assertTrue(os.path.isfile(ok), "the seed's own red file was refused")

    def test_the_fan_in_merges_every_shards_memory_newest_learning_first(self):
        """* THE POINT - two shards learned the same sabotage at different times: the newer cases win"""
        import heart2 as H
        a = self._mem("proof-shard-1", {"k1": {"gate": "g", "proof": 0, "ids": ["old"], "at": 2000, "usedAt": 2000},
                                        "k2": {"gate": "g", "proof": 1, "ids": ["x"], "at": 1000, "usedAt": 1000}})
        b = self._mem("proof-shard-2", {"k1": {"gate": "g", "proof": 0, "ids": ["new"], "at": 3000, "usedAt": 3000}})
        out = os.path.join(self.tmp, "seed", "heart2_red.json")
        # the newer learning sits in the FIRST file: a merge by file order would keep "old"
        self.assertEqual(H.merge_red_files([b, a], out, say=lambda *x, **k: None), 0)
        with io.open(out, encoding="utf-8") as fh:
            ent = json.load(fh)["entries"]
        self.assertEqual(sorted(ent), ["k1", "k2"])
        self.assertEqual(ent["k1"]["ids"], ["new"])
        b2 = self._mem("proof-shard-3", {"k1": {"gate": "g", "proof": 0, "ids": ["old"], "at": 2000, "usedAt": 2000}})
        H.merge_red_files([b, b2], out, say=lambda *x, **k: None)
        with io.open(out, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["entries"]["k1"]["ids"], ["new"], "an older learning read last overwrote it")

    def test_the_seed_carries_a_memory_and_refuses_a_file_that_is_not_one(self):
        restored, out = os.path.join(self.tmp, "restored"), os.path.join(self.tmp, "out")
        os.makedirs(restored)
        os.makedirs(out)
        with io.open(os.path.join(restored, SEED.RED_NAME), "w", encoding="utf-8") as fh:
            json.dump({"format": 2, "entries": {"k": {"ids": ["a"], "at": 1}}}, fh)
        self.assertEqual(SEED.carry_red(restored, out, say=lambda *a, **k: None), 1)
        self.assertTrue(os.path.isfile(os.path.join(out, SEED.RED_NAME)))
        os.remove(os.path.join(out, SEED.RED_NAME))
        with io.open(os.path.join(restored, SEED.RED_NAME), "w", encoding="utf-8") as fh:
            json.dump({"not": "a memory"}, fh)
        self.assertIsNone(SEED.carry_red(restored, out, say=lambda *a, **k: None),
                          "a file that would not read is unknown, not a measured zero")
        self.assertFalse(os.path.isfile(os.path.join(out, SEED.RED_NAME)))

    def test_the_seed_build_carries_it_and_every_shard_starts_from_it(self):
        with io.open(os.path.join(HERE, "proof_seed.py"), encoding="utf-8") as fh:
            seed_src = "\n".join(l.split("#", 1)[0] for l in fh.read().split("\n"))
        self.assertIn('rec["red"] = carry_red(restored, out_dir, say=say)', seed_src)
        text = _wf()
        self.assertIn('if [ -f "$RUNNER_TEMP/heart2-seed/heart2_red.json" ]; then cp "$RUNNER_TEMP/heart2-seed/heart2_red.json" '
                      '"$D/.heart2_red.json"; fi', _job(text, "shard"), "a shard starts with an empty red memory again")
        fan = _job(text, "fan-in")
        i = fan.index('--merge-red $_red --red-out "$RUNNER_TEMP/heart2-seed/heart2_red.json"')
        self.assertLess(i, fan.index("name: Save the seed"), "the merged memory is written after the seed was saved")


class TheBrowserSuiteDealsFromWhatItMeasured(unittest.TestCase):
    """Routine I: v3889's fast shards ran 12.8-20.0 min on a table measured once (10-15). Now each round measures every
    spec, saves the table, and the next round chooses its count from it and deals every shard from that one file."""

    def test_the_fewest_fast_shards_that_fit_and_the_heaviest_file_is_the_floor(self):
        names = ["tests/s%03d.spec.ts" % i for i in range(100)]
        costs = dict((n, 60.0) for n in names)              # 6,000 s of tests at 2 workers
        n, why = RIS.choose_n(names, costs, target_s=480, workers=2, n_min=1, n_max=60)
        self.assertEqual(n, 7, why)                          # 6000 / 7 / 2 = 428.6 <= 480; 6 would be 500
        costs["tests/s000.spec.ts"] = 900.0                  # one file alone runs 900 s in one worker
        n2, why2 = RIS.choose_n(names, costs, target_s=480, workers=2, n_min=1, n_max=60)
        self.assertLess(n2, 60, "past the heaviest file's floor every shard was asked for: %s" % why2)
        self.assertIn("floor", why2)

    def test_the_measured_table_wins_file_by_file(self):
        tmp = tempfile.mkdtemp(prefix="ri_costs_")
        try:
            p = os.path.join(tmp, "routine_i_costs.json")
            some = sorted(RIS.load_costs())[0]
            with io.open(p, "w", encoding="utf-8") as fh:
                json.dump({"costs": {some: 999.0}}, fh)
            got = RIS.measured_costs(env={RIS.ENV_COSTS: p})
            self.assertEqual(got[some], 999.0, "the round's measured cost lost to the committed snapshot")
            self.assertEqual(len(got), len(RIS.load_costs()), "the committed files the round did not run were dropped")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_a_refresh_keeps_the_specs_the_round_did_not_run(self):
        tmp = tempfile.mkdtemp(prefix="ri_blobs_")
        try:
            base = os.path.join(tmp, "base.json")
            with io.open(base, "w", encoding="utf-8") as fh:
                json.dump({"costs": {"tests/old.spec.ts": 50.0, "tests/a.spec.ts": 10.0}}, fh)
            real = RIS.costs_from_blob_zips
            RIS.costs_from_blob_zips = lambda paths: {"tests/a.spec.ts": 20.0}
            try:
                out = os.path.join(tmp, "out", "routine_i_costs.json")
                self.assertEqual(RIS.main(["--from-blobs", "--base", base, "--out", out, "x.zip"]), 0)
            finally:
                RIS.costs_from_blob_zips = real
            with io.open(out, encoding="utf-8") as fh:
                c = json.load(fh)["costs"]
            self.assertEqual(c, {"tests/old.spec.ts": 50.0, "tests/a.spec.ts": 20.0})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_the_workflow_hands_one_measured_table_to_every_shard_and_saves_the_next(self):
        with io.open(RI_WF, encoding="utf-8") as fh:
            wf = fh.read()
        code = "\n".join(l for l in wf.split("\n") if not l.lstrip().startswith("#"))
        self.assertIn("python3 tv/routine_i_shards.py --choose --fallback 10 --output \"$GITHUB_OUTPUT\"", code)
        self.assertIn("if: ${{ steps.count.outputs.measured == 'true' }}", code, "the table is never handed on")
        self.assertIn('export ROUTINE_I_COSTS="$RUNNER_TEMP/ri-costs/routine_i_costs.json"', _job(code, "test"),
                      "a shard deals from the committed snapshot, not the round's one table")
        merge = _job(code, "merge-report")
        self.assertIn("--from-blobs --base \"$B\" --out \"$RUNNER_TEMP/ri-costs/routine_i_costs.json\" all-blobs/*.zip", merge)
        self.assertIn("if: ${{ !cancelled() && steps.measure.outputs.wrote == 'true' }}", merge)
        self.assertIsNone(re.search(r"hashFiles\([^)]*runner\.temp", code),
                          "hashFiles() reads only the workspace: a condition on a runner.temp file is never true")



class TheAgentSuiteChoosesItsOwnSliceCount(unittest.TestCase):
    """The agent suite: v3889 ran 5 fixed slices, the slowest job 20.1 min. Now each round chooses its count from
    measured gate costs (GATE_COSTS over the committed table) and the verdict refreshes them (--base: a gate not run
    keeps its last cost)."""

    class _G(object):
        def __init__(self, name):
            self.name = name

    def _with_costs(self, costs, fn):
        tmp = tempfile.mkdtemp(prefix="ag_costs_")
        try:
            p = os.path.join(tmp, "gate_costs.json")
            with io.open(p, "w", encoding="utf-8") as fh:
                json.dump({"costs": costs}, fh)
            old = os.environ.get("GATE_COSTS")
            os.environ["GATE_COSTS"] = p
            try:
                return fn()
            finally:
                if old is None:
                    os.environ.pop("GATE_COSTS", None)
                else:
                    os.environ["GATE_COSTS"] = old
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_the_fewest_slices_that_fit_and_the_heaviest_gate_is_the_floor(self):
        """* THE POINT - 100 gates of 60 s against a 4-minute target: 25 slices fit, and 24 do not; one 500-s gate is the floor"""
        import run_gates as RG
        names = ["ag%03d" % i for i in range(100)]
        costs = dict((n, 60.0) for n in names)
        gates = [self._G(n) for n in names]

        def choose():
            return RG.choose_shards(target_s=240, n_min=1, n_max=60, gates=gates)

        n, why = self._with_costs(costs, choose)
        self.assertEqual(n, 25, why)                          # 6000 / 25 = 240; 24 would be 250
        costs["ag000"] = 500.0                                # one gate alone runs 500 s
        n2, why2 = self._with_costs(costs, choose)
        self.assertLess(n2, 60, "past the heaviest gate's floor every shard was asked for: %s" % why2)

    def test_GATE_COSTS_wins_over_the_committed_table(self):
        import run_gates as RG
        import gate_costs as GC
        committed = GC.load()
        self.assertTrue(committed, "PREMISE: the committed table is readable")
        some = sorted(committed)[0]
        p = tempfile.mkdtemp(prefix="ag_last_")
        try:
            path = os.path.join(p, "gate_costs.json")
            with io.open(path, "w", encoding="utf-8") as fh:
                json.dump({"costs": {some: 999.0}}, fh)
            old = os.environ.get("GATE_COSTS")
            os.environ["GATE_COSTS"] = path
            try:
                got, _why = RG._cost_table()
            finally:
                if old is None:
                    os.environ.pop("GATE_COSTS", None)
                else:
                    os.environ["GATE_COSTS"] = old
            self.assertEqual(got[some], 999.0, "the round's measured cost lost to the committed snapshot")
            self.assertEqual(len(got), len(committed), "the committed gates the round did not run were dropped")
            other = next(k for k in committed if k != some)
            self.assertEqual(got[other], committed[other], "a committed gate GATE_COSTS did not name was rewritten")
        finally:
            shutil.rmtree(p, ignore_errors=True)

    def test_a_refresh_keeps_the_gates_the_round_did_not_run(self):
        import gate_costs as GC
        tmp = tempfile.mkdtemp(prefix="ag_base_")
        try:
            base = os.path.join(tmp, "base.json")
            with io.open(base, "w", encoding="utf-8") as fh:
                json.dump({"costs": {"old": 50.0, "a": 10.0}}, fh)
            log = os.path.join(tmp, "shard.log")
            with io.open(log, "w", encoding="utf-8") as fh:
                fh.write("\u2705 a 20.0s done\n")
            out = os.path.join(tmp, "out", "gate_costs.json")
            self.assertEqual(GC.main(["gate_costs.py", "--base", base, "--out", out, log]), 0)
            with io.open(out, encoding="utf-8") as fh:
                c = json.load(fh)["costs"]
            self.assertEqual(c, {"a": 20.0, "old": 50.0})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_the_workflow_plans_hands_one_table_and_the_verdict_remeasures(self):
        with io.open(TV_WF, encoding="utf-8") as fh:
            wf = fh.read()
        code = "\n".join(l for l in wf.split("\n") if not l.lstrip().startswith("#"))
        plan = _job(code, "plan")
        self.assertIn("python3 tv/run_gates.py --choose-shards --fallback 5 --output \"$GITHUB_OUTPUT\"", plan)
        self.assertIn("continue-on-error: true", plan, "a count that cannot be chosen would fail the round")
        self.assertIn('export GATE_COSTS="$RUNNER_TEMP/gate-costs/gate_costs.json"', plan)
        self.assertIn("if: ${{ steps.count.outputs.measured == 'true' }}", plan, "the table is never handed on")
        suite = _job(code, "agent-suite")
        self.assertIn('export GATE_COSTS="$RUNNER_TEMP/gate-costs/gate_costs.json"', suite,
                      "a shard cuts from the committed snapshot, not the round's one table")
        verdict = _job(code, "verdict")
        self.assertIn("--base \"$B\" --out \"$RUNNER_TEMP/gate-costs/gate_costs.json\"", verdict)
        self.assertIn("if: ${{ steps.measure.outputs.wrote == 'true' }}", verdict)
        self.assertIsNone(re.search(r"hashFiles\([^)]*runner\.temp", code),
                          "hashFiles() reads only the workspace: a condition on a runner.temp file is never true")


class TheMacReadsTheSetsOwnSize(unittest.TestCase):

    def test_the_size_is_the_one_n_the_manifests_carry(self):
        tmp = tempfile.mkdtemp(prefix="pkm_n_")
        try:
            files = []
            for k, n in ((1, 30), (2, 30), (3, 30)):
                p = os.path.join(tmp, "proof-shard-%d" % k, ".heart2_cache.json")
                os.makedirs(os.path.dirname(p))
                with io.open(p, "w", encoding="utf-8") as fh:
                    json.dump({"entries": {}, "shard": {"k": k, "n": n}}, fh)
                files.append(p)
            self.assertEqual(PKM.shard_count_of(files), 30)
            with io.open(files[2], "w", encoding="utf-8") as fh:
                json.dump({"entries": {}, "shard": {"k": 3, "n": 31}}, fh)
            self.assertIsNone(PKM.shard_count_of(files), "manifests that disagree were given a size")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)



class TheProofKeyFormatIsDeclaredAndCarried(unittest.TestCase):
    """card #200 guards 1+3 (REG-3665) - v3894's #92 changed the key salt alone: 0 of 10,187 proofs reused, then the seed
    restored the dead-format branch cache over main's. The format is one constant; the cache prefix and the salt follow it."""

    def test_the_salt_and_the_cache_prefix_carry_the_declared_format(self):
        import heart2 as H
        src = io.open(os.path.join(HERE, "heart2.py"), encoding="utf-8").read()
        self.assertIn('h = hashlib.sha256(b"heart2 P3 key v%d\\0")' % H.P3_KEY_FORMAT, src,
                      "heart2's newest key salt is not the declared P3_KEY_FORMAT - a salt changed without the format")
        yml = io.open(os.path.join(os.path.dirname(HERE), ".github", "workflows", "proof-keys-shards.yml"), encoding="utf-8").read()
        keys = re.findall(r"^\s+key: (heart2-proofs-\S*)", yml, re.M)
        self.assertGreaterEqual(len(keys), 4, keys)
        for k in keys:
            self.assertTrue(k.startswith("heart2-proofs-k%d-" % H.P3_KEY_FORMAT), "a cache key without the format: %s" % k)
        legacy = re.search(r"^\s+heart2-proofs-\s*$", yml, re.M)
        if H.P3_KEY_FORMAT != 3:
            self.assertIsNone(legacy, "the bare legacy prefix (format 3's caches) is restored under another format")

    def test_a_format_change_without_a_reseed_plan_refuses_the_ship(self):
        import ship_when_green as SW
        main3, tree4 = "x\nP3_KEY_FORMAT = 3\n", "x\nP3_KEY_FORMAT = 4\n"
        self.assertIsNone(SW.key_format_refusal(tree_src=main3, main_src="no constant here", have_plan=False))
        self.assertIn("format 4", SW.key_format_refusal(tree_src=tree4, main_src=main3, have_plan=False) or "")
        self.assertIsNone(SW.key_format_refusal(tree_src=tree4, main_src=main3, have_plan=True))


RED_PROOF = [
    {"why": "card #200 guard 3 - a cache key loses its format and a seed can restore another format's entries",
     "file": ".github/workflows/proof-keys-shards.yml",
     "find": "          key: heart2-proofs-k3-${{ github.sha }}-${{ github.run_id }}-${{ github.run_attempt }}\n",
     "replace": "          key: heart2-proofs-${{ github.sha }}-${{ github.run_id }}-${{ github.run_attempt }}\n",
     "matches": 1},
    {"why": "card #200 guard 1 - a proof-key format change ships without a re-seed plan",
     "file": "tv/ship_when_green.py",
     "find": "    if t != m and not have_plan:\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "v3894 - the wall fit takes a deadline-cut shard's wall (the deadline) as a measurement of its work",
     "file": "tv/proof_shard.py",
     "find": "        if CUT_AT_BOUND in log:\n            continue\n",
     "replace": "",
     "matches": 1},
    {"why": "v3891 (#194, REG-3519) - the seed's shard count is appended to any path, the checkout included",
     "file": "tv/heart2.py",
     "find": "    if output and _inside(REPO, output):\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "v3891 (#194, REG-3520) - the fan-in writes its merged memory over whatever --red-out names",
     "file": "tv/heart2.py",
     "find": "    if os.path.basename(out) not in (_SEED_RED_NAME, _RED_NAME):\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "v3891 (#194) - Routine I asks for every shard past the heaviest file's floor",
     "file": "tv/routine_i_shards.py",
     "find": "    aim = max(float(target_s), floor * 1.05)\n",
     "replace": "    aim = float(target_s)\n",
     "matches": 1},
    {"why": "v3891 (#194) - Routine I deals from the committed snapshot whatever the round measured",
     "file": "tv/routine_i_shards.py",
     "find": "    out.update(last)\n",
     "replace": "",
     "matches": 1},
    {"why": "v3891 (#194) - a refresh forgets every spec the round did not run",
     "file": "tv/routine_i_shards.py",
     "find": "            costs = dict(base, **costs)\n",
     "replace": "",
     "matches": 1},
    {"why": "v3891 (#194) - the hand-on waits on hashFiles over runner.temp, which is never true",
     "file": ".github/workflows/routine-i-playwright.yml",
     "find": "        if: ${{ steps.count.outputs.measured == 'true' }}\n",
     "replace": "        if: ${{ hashFiles(format('{0}/ri-costs/routine_i_costs.json', runner.temp)) != '' }}\n",
     "matches": 1},
    {"why": "v3891 (#194) - a fast round sinks the wall factor below the committed one (under-planning costs a round)",
     "file": "tv/proof_shard.py",
     "find": "    return round(max(SHARD_WALL_FACTOR, min(3.0, cur * med)), 3)\n",
     "replace": "    return round(min(3.0, cur * med), 3)\n",
     "matches": 1},
    {"why": "v3891 (#194) - the plan keeps the hand-set factor whatever the last round measured",
     "file": "tv/proof_shard.py",
     "find": "        _wf = wall_factor()\n",
     "replace": "        _wf = SHARD_WALL_FACTOR\n",
     "matches": 1},
    {"why": "v3891 (#194) - the seed drops the factor the last round measured",
     "file": "tv/proof_seed.py",
     "find": "    if _wf > PS.SHARD_WALL_FACTOR:\n        body[\"wallFactor\"] = _wf\n",
     "replace": "",
     "matches": 1},
    {"why": "v3891 (#194) - past the floor the chooser asks for every shard the bound allows",
     "file": "tv/proof_shard.py",
     "find": "    aim = max(float(target_s), floor * FLOOR_SLACK)\n",
     "replace": "    aim = float(target_s)\n",
     "matches": 1},
    {"why": "v3891 (#194) - the count is not the fewest that fits (it stops one wider)",
     "file": "tv/proof_shard.py",
     "find": "    rep = cache[hi][1]\n    if floor > target_s:\n",
     "replace": "    hi = min(n_max, hi + 1)\n    slowest(hi)\n    rep = cache[hi][1]\n    if floor > target_s:\n",
     "matches": 1},
    {"why": "v3891 (#194) - the plan mode's list is not every shard 1..n",
     "file": "tv/heart2.py",
     "find": "json.dumps(list(range(1, n + 1)), separators=(\",\", \":\"))",
     "replace": "json.dumps(list(range(1, n)), separators=(\",\", \":\"))",
     "matches": 1},
    {"why": "v3891 (#194) - the fan-in keeps whichever memory it read last, not the newest learning",
     "file": "tv/heart2.py",
     "find": "        ent = _red_merged(ent, (body or {}).get(\"entries\"), None)\n",
     "replace": "        ent.update((body or {}).get(\"entries\") or {})\n",
     "matches": 1},
    {"why": "v3891 (#194) - the seed carries a file that is not a red memory",
     "file": "tv/proof_seed.py",
     "find": "        if not isinstance(ent, dict):\n            raise ValueError(\"no entries map\")\n",
     "replace": "",
     "matches": 1},
    {"why": "v3891 (#194) - every shard starts with an empty red memory again",
     "file": ".github/workflows/proof-keys-shards.yml",
     "find": "          if [ -f \"$RUNNER_TEMP/heart2-seed/heart2_red.json\" ]; then cp \"$RUNNER_TEMP/heart2-seed/heart2_red.json\" \"$D/.heart2_red.json\"; fi\n",
     "replace": "",
     "matches": 1},
    {"why": "v3891 (#194) - the Mac sizes a set whose manifests disagree",
     "file": "tv/proof_keys_mac.py",
     "find": "    return ns.pop() if len(ns) == 1 else None\n",
     "replace": "    return max(ns) if ns else None\n",
     "matches": 1},
    {"why": "v3891 (#194, REG-3523) - past the floor the agent suite asks for every slice the bound allows",
     "file": "tv/run_gates.py",
     "find": "    aim = max(float(target_s), floor * 1.05)\n",
     "replace": "    aim = float(target_s)\n",
     "matches": 1},
    {"why": "v3891 (#194, REG-3523) - GATE_COSTS loses to the committed table",
     "file": "tv/run_gates.py",
     "find": "        merged.update(_last)\n",
     "replace": "",
     "matches": 1},
    {"why": "v3891 (#194, REG-3523) - a refresh forgets every gate the round did not run",
     "file": "tv/gate_costs.py",
     "find": "        costs = dict(prev, **costs)\n",
     "replace": "",
     "matches": 1},
    {"why": "v3891 (#194, REG-3523) - the hand-on waits on hashFiles over runner.temp, which is never true",
     "file": ".github/workflows/tv-tests.yml",
     "find": "        if: ${{ steps.count.outputs.measured == 'true' }}\n",
     "replace": "        if: ${{ hashFiles(format('{0}/gate-costs/gate_costs.json', runner.temp)) != '' }}\n",
     "matches": 1},
    {"why": "v3891 (#194, REG-3523) - the verdict save waits on hashFiles over runner.temp, which is never true",
     "file": ".github/workflows/tv-tests.yml",
     "find": "        if: ${{ steps.measure.outputs.wrote == 'true' }}\n",
     "replace": "        if: ${{ hashFiles(format('{0}/gate-costs/gate_costs.json', runner.temp)) != '' }}\n",
     "matches": 1},
    {"why": "v3896 (REG-3675) - the floor is said as one chunk to split again, while the shards are balanced",
     "file": "tv/proof_shard.py",
     "find": "        why = (\"even at %d shards the slowest shard models %d s, over the %d-s target, so %d shard(s) are the fewest that \"\n",
     "replace": "        why = (\"the slowest proof chunk alone at %d models %d s, over the %d-s target, so %d shard(s) are the fewest that \"\n",
     "matches": 1}
]


if __name__ == "__main__":
    unittest.main()
