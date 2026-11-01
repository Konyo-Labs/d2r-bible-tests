#!/usr/bin/env python3
"""v3842 GATE-TRIM A - the parallel --full runs every registered gate exactly once, and stays serial when it must.

plan() is driven over the REAL registry and the real cost table: the light slices and the heavy list are disjoint,
their union is every gate, nothing at or over HEAVY_S lands in a light slice, and the slices are balanced. why_serial
refuses under the memory floor, on an unknown reading, and on a dirty tracked tree. And run_gates hands the heavy list
to the serial pass only when it is non-empty (an empty `only` would mean every gate).
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gates_parallel as GP  # noqa: E402
import run_gates as RG  # noqa: E402


class TheParallelFullRunsEveryGateOnce(unittest.TestCase):
    def test_every_gate_lands_in_exactly_one_place(self):
        weigh = RG.cost_weights(RG.GATES)
        slices, heavy = GP.plan(RG.GATES, weigh)
        seen = [n for s in slices for n in s] + heavy
        self.assertEqual(len(seen), len(set(seen)), "a gate would run twice")
        self.assertEqual(set(seen), set(g.name for g in RG.GATES), "a gate would not run at all")
        self.assertEqual(len(slices), GP.SLICES)
        for s in slices:
            for n in s:
                self.assertLess(weigh[n], GP.HEAVY_S, "%s is heavy but would share the box" % n)
                self.assertNotIn(n, GP.SERIAL_ONLY, "%s contends across trees but would share the box" % n)
        for n in heavy:
            self.assertTrue(weigh[n] >= GP.HEAVY_S or n in GP.SERIAL_ONLY, "%s is cheap and safe yet runs alone" % n)
        self.assertLessEqual(GP.SERIAL_ONLY, set(g.name for g in RG.GATES), "a SERIAL_ONLY name is not a gate")
        self.assertTrue(heavy, "the heavy pass is empty - run() would read [] as every gate")
        tot = [sum(weigh[n] for n in s) for s in slices]
        self.assertLess(max(tot) - min(tot), GP.HEAVY_S + 1, "the light slices are not balanced: %r" % tot)

    def test_it_stays_serial_under_the_floor_or_blind(self):
        self.assertIn("serial", GP.why_serial(mem=GP.FLOOR_GB - 0.5) or "")
        self.assertIn("UNKNOWN", GP.why_serial(mem=None) if GP.free_gb() is None else "UNKNOWN")

    def test_a_shard_never_carries_a_lock_key_into_its_tests(self):
        # The key leaked into tree_busy, so the bump law in a shard saw its own run as a holder.
        src = io.open(GP.__file__, encoding="utf-8").read()
        self.assertNotIn('env["D2R_GATE_LOCK_KEY"]', src)
        self.assertIn('env.pop("D2R_GATE_LOCK_KEY", None)', src)

    def test_a_gate_that_contends_across_trees_runs_alone(self):
        class G: pass
        gs = []
        for n in sorted(GP.SERIAL_ONLY) + ["cheap"]:
            g = G(); g.name = n; gs.append(g)
        slices, heavy = GP.plan(gs, {g.name: 1.0 for g in gs})
        self.assertEqual(sorted(heavy), sorted(GP.SERIAL_ONLY))
        self.assertEqual(sum(slices, []), ["cheap"])

    def test_a_local_full_is_serial_unless_asked(self):
        # v3842: parallel is opt-in; a --full with no --parallel must not shard (no worktree is made).
        import argparse
        a = argparse.Namespace(full=True, parallel=None)
        self.assertEqual(RG._parallel_light(a, None), (None, None))

    def test_a_dirty_tracked_tree_stays_serial(self):
        tmp = tempfile.mkdtemp(prefix="tvd-par-dirty-")
        self.addCleanup(shutil.rmtree, tmp, True)
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        g = lambda *a: subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t"] + list(a), cwd=tmp,
                                      env=env, capture_output=True, check=True)
        open(os.path.join(tmp, "f"), "w").write("a")
        g("init", "-q"); g("add", "f"); g("commit", "-qm", "x")
        self.assertIsNone(GP.why_serial(repo=tmp, mem=GP.FLOOR_GB + 10))
        open(os.path.join(tmp, "f"), "w").write("b")
        self.assertIn("uncommitted", GP.why_serial(repo=tmp, mem=GP.FLOOR_GB + 10) or "")

    def test_run_gates_never_hands_an_empty_heavy_list_on(self):
        src = open(os.path.join(HERE, "run_gates.py"), encoding="utf-8").read()
        body = src[src.index("def _parallel_light("):src.index("def gate_set_exit(")]
        self.assertIn("if not heavy:", body)
        self.assertLess(body.index("if not heavy:"), body.index("GP.run_light("))

    def test_each_shard_gets_its_own_scratch_chrome_port(self):
        # v3849: every shard inherited 9224, so one shard's browser law drove (and lost) another shard's Chrome.
        ports = GP.shard_ports(GP.SLICES)
        self.assertEqual(len(set(ports)), GP.SLICES, "two shards would share a scratch Chrome: %r" % ports)
        self.assertFalse({9222, 9223, 9224} & set(ports), ports)
        src = io.open(GP.__file__, encoding="utf-8").read()
        body = src[src.index("def run_light("):]
        self.assertIn('env["TV_RENDER_PORT"] = str(ports[i])', body)


RED_PROOF = [
    {"why": "v3849 - every light shard shares render_check's 9224 again, so one shard drives another's Chrome",
     "file": "tv/gates_parallel.py",
     "find": '            env["TV_RENDER_PORT"] = str(ports[i])\n',
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
