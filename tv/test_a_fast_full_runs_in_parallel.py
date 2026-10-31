# -*- coding: utf-8 -*-
"""v3849 (Elad 15:2x, after the v3848 push ran 1,331 gates serially past the hook's 5400 s bound) -
A FAST RUN THAT FALLS THROUGH TO EVERY GATE RUNS THEM --parallel auto.

`run_gates.py --fast` is the push's gate stage. When a shared file changed (bible.html, the gate machinery) the selector
returns None and every gate runs. That full set now goes through the parallel plan (light shards at once, then the heavy
gates alone) unless --parallel off was given or TV_FAST_FULL_PARALLEL=off. A fast run that picks a subset stays as it was.
"""
import os, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable; enable()
import run_gates as RG
import fast_gates as FG


class _Stop(Exception):
    pass


def _seen(argv, names, env=None):
    got = {}
    old_sel, old_chg, old_pl, old_cl = FG.select, FG.changed, RG._parallel_light, RG._claim_the_tree
    RG._claim_the_tree = lambda: None   # the law never takes the tree lock; no gate runs
    old_env = os.environ.get("TV_FAST_FULL_PARALLEL")
    FG.select = lambda gates, changed, base: (names, "law fixture")
    FG.changed = lambda base: ["bible.html"]
    def _pl(a, only):
        got["full"], got["parallel"], got["only"] = a.full, a.parallel, only
        raise _Stop()
    RG._parallel_light = _pl
    if env is None:
        os.environ.pop("TV_FAST_FULL_PARALLEL", None)
    else:
        os.environ["TV_FAST_FULL_PARALLEL"] = env
    try:
        RG.main(["run_gates.py"] + argv)
    except _Stop:
        pass
    finally:
        FG.select, FG.changed, RG._parallel_light, RG._claim_the_tree = old_sel, old_chg, old_pl, old_cl
        if old_env is None:
            os.environ.pop("TV_FAST_FULL_PARALLEL", None)
        else:
            os.environ["TV_FAST_FULL_PARALLEL"] = old_env
    return got


class FastFullRunsInParallel(unittest.TestCase):
    def test_a_full_fallthrough_is_parallel_auto(self):
        g = _seen(["--fast"], None)
        self.assertTrue(g.get("full"), g)
        self.assertEqual(g.get("parallel"), "auto", "a --fast run that falls through to every gate ran serially")

    def test_off_keeps_it_serial(self):
        self.assertEqual(_seen(["--fast"], None, env="off").get("parallel"), "off")
        self.assertEqual(_seen(["--fast", "--parallel", "off"], None).get("parallel"), "off")

    def test_a_subset_is_not_made_full(self):
        g = _seen(["--fast"], ["test_not_in_game_is_one_chip"])
        self.assertFalse(g.get("full"), g)
        self.assertIsNone(g.get("parallel"), g)

    def test_the_hook_still_calls_fast(self):
        hook = open(os.path.join(os.path.dirname(HERE), "hooks", "pre-push"), encoding="utf-8").read()
        self.assertIn('python3 "$REPO/tv/run_gates.py" --fast', hook)


RED_PROOF = [
    {"why": "v3849 - the fast fallthrough to every gate runs serially again",
     "file": "run_gates.py",
     "find": '                a.parallel = os.environ.get("TV_FAST_FULL_PARALLEL", "auto")',
     "replace": '                a.parallel = os.environ.get("TV_FAST_FULL_PARALLEL", "off")',
     "matches": 1},
    {"why": "v3849 - an explicit --parallel off is overridden",
     "file": "run_gates.py",
     "find": "            if a.parallel is None:   # FAST-FULL-PARALLEL",
     "replace": "            if True:   # FAST-FULL-PARALLEL",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
