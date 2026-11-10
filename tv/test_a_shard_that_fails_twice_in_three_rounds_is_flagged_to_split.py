# -*- coding: utf-8 -*-
"""REG-3649 - A SHARD THAT FAILS TWICE IN THREE ROUNDS IS FLAGGED TO SPLIT.

A shard that fails repeatedly (twice in three rounds), or that runs near the
25-minute cut-off (less than 300s left), is auto-flagged for rebalancing.
The flag lists the slow or failing tests to move so no shard sits against
the ceiling. choose_shards then asks for one extra slice when a flag is up
(still capped at SHARD_MAX).
"""
import os
import sys
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import shard_watch as SHW  # noqa: E402
import run_gates as RG  # noqa: E402


def _round(n, klass, name="agent-suite (2)", used=1117, left=383):
    return {"run": n, "sha": "s%d" % n, "when": "2026-11-10", "jobs": [
        {"name": name, "k": 2, "n": 5, "class": klass,
         "failed": ["test_the_planner_spinner_stays_under_the_cursor"] if klass == "real" else [],
         "used_s": used, "left_s": left, "ceiling_s": 1500}]}


class TheLawHolds(unittest.TestCase):
    def test_one_fail_in_three_is_not_flagged(self):
        root = tempfile.mkdtemp(prefix="shard-1of3-")
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        os.makedirs(os.path.join(root, "tv"), exist_ok=True)
        data = {"rounds": [_round(1, "success"), _round(2, "success"), _round(3, "real")],
                "flags": []}
        SHW.save(data, root)
        self.assertFalse(SHW.needs_rebalance("agent-suite (2)", root=root))
        self.assertEqual(SHW.extra_shards(root=root), 0)
        self.assertIsNone(SHW.maybe_flag("agent-suite (2)",
                                         info={"class": "real", "left_s": 383, "ceiling_s": 1500,
                                               "failed": ["test_the_planner_spinner_stays_under_the_cursor"]},
                                         k=2, n=5, root=root))

    def test_two_fails_in_three_rounds_are_flagged(self):
        root = tempfile.mkdtemp(prefix="shard-2of3-")
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        os.makedirs(os.path.join(root, "tv"), exist_ok=True)
        data = {"rounds": [_round(1, "success"), _round(2, "real"), _round(3, "cutoff")],
                "flags": []}
        SHW.save(data, root)
        self.assertTrue(SHW.needs_rebalance("agent-suite (2)", root=root))
        flag = SHW.maybe_flag("agent-suite (2)",
                              info={"class": "cutoff", "left_s": 10, "ceiling_s": 1500, "failed": []},
                              k=2, n=5, root=root)
        self.assertIsNotNone(flag)
        self.assertIn("failed 2 of the last 3 rounds", flag["why"])
        self.assertTrue(flag.get("move"), "a split names tests to move, from timings")
        self.assertEqual(SHW.extra_shards(root=root), 1)

    def test_a_shard_near_the_ceiling_is_flagged_even_on_one_round(self):
        root = tempfile.mkdtemp(prefix="shard-near-")
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        os.makedirs(os.path.join(root, "tv"), exist_ok=True)
        data = {"rounds": [_round(1, "success", used=1290, left=210)], "flags": []}
        SHW.save(data, root)
        self.assertFalse(SHW.needs_rebalance("agent-suite (2)", root=root))
        flag = SHW.maybe_flag("agent-suite (2)",
                              info={"class": "success", "used_s": 1290, "left_s": 210, "ceiling_s": 1500},
                              k=2, n=5, root=root)
        self.assertIsNotNone(flag, "210s left is under the 300s near-ceiling warning")
        self.assertIn("near the cut-off", flag["why"])

    def test_choose_shards_asks_for_an_extra_slice_when_flagged(self):
        root = tempfile.mkdtemp(prefix="shard-choose-")
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        os.makedirs(os.path.join(root, "tv"), exist_ok=True)
        data = {"rounds": [_round(1, "real"), _round(2, "real"), _round(3, "success")],
                "flags": []}
        SHW.save(data, root)
        SHW.maybe_flag("agent-suite (2)", info={"class": "real", "left_s": 383, "ceiling_s": 1500,
                                               "failed": ["test_the_planner_spinner_stays_under_the_cursor"]},
                       k=2, n=5, root=root)
        gates = [RG.Gate("g%d" % i, ["true"], 10) for i in range(20)]
        n_plain, _ = RG.choose_shards(target_s=10 ** 9, n_min=3, n_max=5, gates=gates, root=None)
        n_flag, why = RG.choose_shards(target_s=10 ** 9, n_min=3, n_max=5, gates=gates, root=root)
        # With a huge target, unflagged choose_shards returns n_min (3). A flag bumps n_min by 1.
        self.assertEqual(n_plain, 3, "premise: a light set stays at n_min without a flag")
        self.assertEqual(n_flag, 4, why)
        self.assertGreaterEqual(n_flag, n_plain)


class TheProofsNameOnePlace(unittest.TestCase):
    def test_each_find_matches_once(self):
        repo = os.path.dirname(HERE)
        for p in RED_PROOF:
            blob = open(os.path.join(repo, p["file"]), encoding="utf-8").read()
            self.assertEqual(blob.count(p["find"]), p["matches"], p["why"])


RED_PROOF = [
    {"why": "REG-3649 - 2-of-3 no longer flags a shard to split",
     "file": "tv/shard_watch.py",
     "find": "failed %d of the last %d rounds",
     "replace": "ignored %d of the last %d rounds",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main()
