# -*- coding: utf-8 -*-
"""REG-3579 - A HUNG PROOF IS CUT TIMEOUT AND NAMED BEFORE IT CAN STARVE THE RUNNER SILENT.

MEASURED on v3890 run 42712427277 (sha d22085c7b, ci/proof-keys-v3890) attempt 1, shard 10: the hosted runner lost
communication at 54 minutes (started 00:41 IST, failed 01:35 IST) while "Prove this shard" was still in_progress.
No logs were kept, the cache was never uploaded, and the fan-in refused the set. GitHub: "Anything in your workflow
that terminates the runner process, starves it for CPU/Memory, or blocks its network access can cause this error."
Attempt 2 of the same shard, on another runner, proved the same 475 proofs in 26.9 minutes (prove_seconds=1554) and
wrote its manifest. Shard 10 is not systematically the longest (recent slowest shards were 3, 12, 17, 20, 21; a
healthy v3890 shard 3 ran 56.9 minutes), so a shorter job-level cut would falsely TIMEOUT work that finishes.
The hole is one proof: with 2 lanes, DEADLINE_SCALE doubles every law's timeout, so test_control's registered 900 s
becomes 1,800 s - long enough for a hang to starve the runner agent before HARD_STOP (deadline + 480 s = job minute
63). Held here:
  * heart2.PROOF_CAP_S is 900 - the longest registered law timeout - and _inflight_limit of a CI run (one with a
    deadline) takes it as a bound, so a doubled 1,800 s timeout is cut at 900 s with why naming "this proof";
  * a cut proof is TIMEOUT, owed, named (REG-3212's path) - never a silent runner death;
  * no deadline (his Mac's push, a PC's census) does not apply the cap;
  * a tighter hard-stop or gate cap still wins.
Fixtures only: no browser, nothing is proved. RED_PROOF below.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import heart2  # noqa: E402


class AShardCutsBeforeTheRunnerGoesSilent(unittest.TestCase):

    def test_the_proof_cap_is_the_longest_registered_timeout(self):
        self.assertEqual(heart2.PROOF_CAP_S, 900)
        self.assertLess(heart2.PROOF_CAP_S, 900 * heart2.LANE_DEADLINE_SCALE,
                        "the cap does not stop lanes doubling a 900 s law into a 30-minute hang")

    def test_a_doubled_timeout_is_cut_and_named_on_a_ci_run(self):
        run = heart2._PushRun(keep_going=True)
        run.deadline, run.gate_cap = 1e12, None
        t, why = heart2._inflight_limit(900 * heart2.LANE_DEADLINE_SCALE, now=1000.0, run=run, gate_t0=1000.0)
        self.assertEqual(t, float(heart2.PROOF_CAP_S))
        self.assertIn("proof", why)
        self.assertIn(str(heart2.PROOF_CAP_S), why)

    def test_a_law_already_inside_the_cap_is_unchanged(self):
        run = heart2._PushRun(keep_going=True)
        run.deadline, run.gate_cap = 1e12, None
        t, why = heart2._inflight_limit(240, now=1000.0, run=run)
        self.assertEqual((t, why), (240, None), "a short law was clipped")

    def test_no_deadline_does_not_cap_a_proof(self):
        run = heart2._PushRun(keep_going=True)
        run.deadline = run.gate_cap = None
        self.assertEqual(heart2._inflight_limit(1800, now=1000.0, run=run), (1800, None),
                         "his Mac or a PC census was capped")

    def test_a_tighter_hard_stop_still_wins(self):
        run = heart2._PushRun(keep_going=True)
        run.deadline, run.gate_cap = 2000.0, None
        # hard stop = 2000 + 480 = 2480; at now=2400 that leaves 80 s, tighter than 900
        t, why = heart2._inflight_limit(1800, now=2400.0, run=run)
        self.assertEqual(t, 80.0)
        self.assertIn("hard stop", why)


RED_PROOF = [
    {"why": "REG-3579 - a scaled-up law timeout is not capped, so a hung proof can starve the runner",
     "file": "tv/heart2.py",
     "find": "    if getattr(run, \"deadline\", None) is not None and (best is None or PROOF_CAP_S < best):\n",
     "replace": "    if False and getattr(run, \"deadline\", None) is not None and (best is None or PROOF_CAP_S < best):\n",
     "matches": 1},
    {"why": "REG-3579 - the proof cap equals a doubled 900 s timeout, so a hang can run 30 minutes",
     "file": "tv/heart2.py",
     "find": "PROOF_CAP_S = 900\n",
     "replace": "PROOF_CAP_S = 1800\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
