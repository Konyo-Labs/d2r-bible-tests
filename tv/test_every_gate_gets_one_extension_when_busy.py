# -*- coding: utf-8 -*-
"""v3861 - EVERY GATE GETS REG-1995's ONE EXTENSION WHEN THE MACHINE IS BUSY AT ITS DEADLINE; A QUIET MACHINE STILL KILLS.

hooks/pre-push carried REG-1995 for three gates only (render, blueprint, heart). run_gates.py's per-gate bound had no
grace, so one slow-but-healthy gate on a loaded box threw away a whole push (GrokBot's v3859 run #1: refused at 88 min on
five gate timeouts that passed on the same bytes). `_run_with_grace` is that rule for every gate: busy at the deadline
(1-minute load above 5) -> ONE extension to the bound x load/5, capped at 2.5x, said in the output; quiet -> killed at
the bound, exactly as before; no load average at all (Windows) -> never "busy".

Drives the REAL helper on a real child that sleeps, with a stand-in load reading so the case's load is the case's.
Bounds are seconds-scale with wide margins on purpose: this law grades a timer and must not become the flake it cures.
"""
import os
import subprocess
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import run_gates as RG  # noqa: E402


def _sleeper(s):
    return [sys.executable, "-c", "import time; time.sleep(%s); print('done')" % s]


class EveryGateGetsOneExtensionWhenBusy(unittest.TestCase):

    def _run(self, sleep_s, timeout, load):
        said = []
        t0 = time.time()
        try:
            p = RG._run_with_grace(_sleeper(sleep_s), timeout=timeout, grace=True, name="fixture", say=said.append,
                                   load=lambda: load, capture_output=True, text=True)
            return p, time.time() - t0, said, None
        except subprocess.TimeoutExpired as e:
            return None, time.time() - t0, said, e

    def test_busy_at_the_deadline_is_extended_once_and_finishes(self):
        p, took, said, err = self._run(3.0, 2.0, 15.0)        # extension to 2 x min(3, 2.5) = 5 s
        self.assertIsNone(err, "a gate busy at its deadline was killed: %r" % (said,))
        self.assertEqual(p.returncode, 0)
        self.assertIn("done", p.stdout)
        self.assertGreaterEqual(took, 2.5)
        self.assertEqual(len(said), 1, "the extension was not said once in the run's output: %r" % (said,))
        self.assertIn("busy at its deadline (load 15.0) - one extension to 5s", said[0])

    def test_a_quiet_machine_still_kills_at_the_bound(self):
        p, took, said, err = self._run(8.0, 2.0, 1.0)
        self.assertIsNotNone(err, "a gate on a QUIET machine was not killed - the hang detector is gone")
        self.assertLess(took, 6.0)
        self.assertEqual(said, [])

    def test_no_load_average_is_never_busy(self):
        p, took, said, err = self._run(8.0, 2.0, None)
        self.assertIsNotNone(err, "a machine with no load reading was treated as busy")
        self.assertLess(took, 6.0)

    def test_the_extension_is_capped_and_comes_once(self):
        p, took, said, err = self._run(12.0, 2.0, 40.0)       # cap 2.5x -> 5 s, never 16 s, never a second one
        self.assertIsNotNone(err, "the extension was not capped at 2.5x the gate's own bound")
        self.assertLess(took, 9.0)
        self.assertEqual(len(said), 1)

    def test_the_runner_hands_every_uncapped_gate_the_grace(self):
        src = open(os.path.join(HERE, "run_gates.py"), encoding="utf-8").read()
        code = "\n".join(l.split("#", 1)[0] for l in src.split("\n"))
        self.assertEqual(code.count("p = _run_with_grace(_argv, cwd=g.cwd, capture_output=True, text=True,"), 1,
                         "the per-gate run no longer goes through the grace")
        self.assertIn("env=law_env(g.needs_app, _env), grace=not _capped, name=g.name)", code)


RED_PROOF = [
    {"why": "v3861 - a gate busy at its deadline is killed again: one loaded moment throws away the whole push",
     "file": "tv/run_gates.py",
     "find": "            if l is None or l <= GATE_GRACE_LOAD:\n                raise\n",
     "replace": "            raise\n",
     "matches": 1},
    {"why": "v3861 - the extension stops asking the load: every gate is extended, quiet or not (the hang detector dies)",
     "file": "tv/run_gates.py",
     "find": "            if l is None or l <= GATE_GRACE_LOAD:\n",
     "replace": "            if False:\n",
     "matches": 1},
    {"why": "v3861 - the extension is no longer capped at 2.5x the gate's own bound",
     "file": "tv/run_gates.py",
     "find": "            total = timeout * min(l / GATE_GRACE_LOAD, GATE_GRACE_MAX)\n",
     "replace": "            total = timeout * (l / GATE_GRACE_LOAD)\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
