# -*- coding: utf-8 -*-
"""v3891 (#194) - A PROOF ROUND CHOOSES ITS OWN SHARD COUNT, AND EACH ROUND STARTS FROM WHAT THE LAST ONE LEARNED.

His words, 11-09 (the repo moved to Konyo-Labs, 500 jobs at once): "optimize the #194 all the way and make sure it keeps
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
  * the Mac's import reads the set's size from the shards' own manifests.
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
        self.assertEqual(SEED.carry_red(restored, out, say=lambda *a, **k: None), 0)
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


RED_PROOF = [
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
]


if __name__ == "__main__":
    unittest.main()
