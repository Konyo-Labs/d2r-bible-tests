# -*- coding: utf-8 -*-
"""v3889 (#103/#44, REG-3498) - A PROOF SHARD PROVES THE LAWS THAT GUARD A LOCK FIRST.

His ask (11-08): "for fleet the river should be flowing for all pcs". MEASURED 11-09 on the work ALT (SSH, read-only):
frame.release, vault.sweep_start and vault.apply shut on v3888 - "6 of its own guard law(s) changed or are unproven" - a
trust pass over its bank served 0 of 11 owed guards ("proof 0 has no PROVEN banked over these bytes"), because the
Windows set it imported was PARTIAL: 3,496 proofs cut at the shards' 55-minute deadline, the make-up round too (shard 15:
test_a_pruned_frame_says_it_was_pruned "26 proof(s) cut at their bound"). Its own prover, beside the Boosteroid stream at
79% busy with 1.1 GB free, had not started for 14 hours. A deadline cuts what has not started, so order decides what a
partial set holds: 315 of 1,713 gates guard a lock, and heart2._shard_cut now puts them first - the clean wave AND the
tamper wave (the order dict) - each group in the run's own order. The plan (which proofs are this shard's) is unchanged.

Driven on the real self_arming rule over real gate names (no proving). RED_PROOF below. [[the-unjoined-end]]
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable   # it prints non-ASCII: never crash while REPORTING
    _enable()
except Exception:
    pass
import heart2 as H2  # noqa: E402
import self_arming as SA  # noqa: E402

GUARDS = ("test_a_pruned_frame_says_it_was_pruned", "test_a_safety_net_red_closes_only_its_own_lock",
          "test_the_fleet_says_importing_not_river_stuck")


class AShardProvesTheLocksGuardsFirst(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.files = dict(H2.gate_files())
        cls.plain = []
        for n in sorted(cls.files):
            if not any(SA._lock_guard(n, lk, cls.files) for lk in SA.LOCK_DOORS):
                cls.plain.append(n)
            if len(cls.plain) == 3:
                break

    def test_the_premise_holds(self):
        for g in GUARDS:
            self.assertIn(g, self.files, "PREMISE: %s is no longer a gate - re-point this law" % g)
            self.assertTrue(any(SA._lock_guard(g, lk, self.files) for lk in SA.LOCK_DOORS), "PREMISE: %s guards no lock" % g)
        self.assertEqual(len(self.plain), 3, "PREMISE: no gate guards nothing")

    def test_guards_go_first_and_each_group_keeps_its_order(self):
        """* THE POINT - the run's order puts the guards last; the shard runs them first"""
        gates = list(self.plain) + list(GUARDS)
        have = [(n, self.files[n], [None]) for n in gates]
        out = H2._guards_first(gates, have)
        self.assertEqual(out, list(GUARDS) + list(self.plain))

    def test_the_shard_cut_hands_both_waves_that_order(self):
        """the clean wave walks `gates`, the tamper wave the `order` dict - both come back guards-first"""
        gates = list(self.plain) + list(GUARDS)
        have = [(n, self.files[n], [None, None]) for n in gates]
        order = dict((n, [0, 1]) for n in gates)
        saved = dict(H2._SHARD)
        try:
            H2._SHARD.clear()
            H2._SHARD["spec"] = (1, 1)
            o2, g2 = H2._shard_cut(have, order, gates, lambda *a, **k: None)
        finally:
            H2._SHARD.clear()
            H2._SHARD.update(saved)
        self.assertEqual(g2[:3], list(GUARDS), g2)
        self.assertEqual(list(o2)[:3], list(GUARDS), list(o2))

    def test_a_lock_that_cannot_be_asked_keeps_the_runs_order(self):
        gates = list(self.plain) + list(GUARDS)
        have = [(n, self.files[n], [None]) for n in gates]
        real = SA._lock_guard
        try:
            def boom(*a, **k):
                raise RuntimeError("x")
            SA._lock_guard = boom
            self.assertEqual(H2._guards_first(gates, have), gates)
        finally:
            SA._lock_guard = real


RED_PROOF = [
    {"why": "v3889 (REG-3498) - a shard proves in the run's order again, lock guards wherever they fall",
     "file": "tv/heart2.py",
     "find": "    out = [g for g in gates if g in guard] + [g for g in gates if g not in guard]\n",
     "replace": "    out = list(gates)\n",
     "matches": 1},
    {"why": "v3889 (REG-3498) - the tamper wave walks the old order while the clean wave goes guards-first",
     "file": "tv/heart2.py",
     "find": "    order2 = dict((g, order2[g]) for g in gates2)   # the tamper wave walks this dict: the same order as the clean wave\n",
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
