# -*- coding: utf-8 -*-
"""v3850 (Elad 17:46 IDT 2026-10-31) - ONE HUNG GATE CANNOT HANG A PROOF BATCH.

Seen: Dean's slice child (pid 421132) sat on one gate from 17:08:29 with its log last written 17:08:42. His ask: a
per-gate timeout, so a stuck gate is cut off and the batch goes on. heart2 already runs each gate under its registered
timeout (_run_gate_once, subprocess timeout); this law pins it, end to end, with a real child that sleeps: it is ended
within the bound, its verdict is UNKNOWN ("timed out after Ns" - never a forged green or red), its process is gone,
and the NEXT gate in the same call sequence still runs and passes. RED_PROOF below.
"""
import os
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import heart2  # noqa: E402

RED_PROOF = [
    {"why": "the per-gate timeout is dropped, so one hung gate holds the batch for ever",
     "file": "heart2.py",
     "find": "                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)\n",
     "replace": "                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=None)\n",
     "matches": 1},
]

HANG = """import os, sys, time
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hung.pid'), 'w').write(str(os.getpid()))
time.sleep(60)
"""
OK = "print('ok')\n"


def _alive(pid):
    if os.name == "nt":                  # REG-1725 - os.kill(pid, 0) is a Ctrl-C there; ask the safe door
        try:
            import self_prove as _sp
            return _sp.pid_alive(pid)
        except Exception:
            return True
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except Exception:
        return True


class AHungGateIsCutOff(unittest.TestCase):
    def test_it_is_ended_within_its_bound_and_the_next_gate_runs(self):
        with tempfile.TemporaryDirectory() as d:
            tv = os.path.join(d, "tv")
            os.makedirs(tv)
            with open(os.path.join(tv, "test_v3850_hangs.py"), "w") as f:
                f.write(HANG)
            with open(os.path.join(tv, "test_v3850_passes.py"), "w") as f:
                f.write(OK)
            t0 = time.time()
            ok, tail = heart2._run_gate_once(tv, "test_v3850_hangs.py", timeout=3)
            took = time.time() - t0
            self.assertLess(took, 30, "a hung gate held the call %.1f s past a 3 s bound" % took)
            self.assertIsNone(ok, "a gate cut off at its deadline was given a verdict: %r" % ok)
            self.assertIn("timed out after 3s", tail)
            with open(os.path.join(tv, "hung.pid")) as f:
                pid = int(f.read())
            time.sleep(0.5)
            self.assertFalse(_alive(pid), "the hung gate's process outlived its deadline")
            ok2, _ = heart2._run_gate_once(tv, "test_v3850_passes.py", timeout=30)
            self.assertIs(ok2, True, "the gate after a hung one did not run")


if __name__ == "__main__":
    unittest.main(verbosity=2)
