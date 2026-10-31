# -*- coding: utf-8 -*-
"""v3849 GATE-BANK - A FULL RUN REUSES A PASS WHOSE INPUTS DID NOT MOVE, AND RERUNS ONE WHOSE INPUTS DID.

--full never asked the ledger, so every push that fell to full re-proved ~1,300 gates whose inputs had not
moved. It now asks the same lookup --changed asks. A changed input, TV_FULL_FRESH=1 or CI runs the gate.
"""
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import gate_ledger as GL  # noqa: E402
import test_a_gate_proven_on_these_bytes_is_carried as C  # noqa: E402


class AFullRunReusesAnUnmovedPass(unittest.TestCase):
    def setUp(self):
        self.held = C._Env(GITHUB_ACTIONS=None, GATE_LEDGER=None, TV_FULL_FRESH=None, TV_SELF_ARMING_DEFER=None,
                           TV_SELF_ARMING_LEDGER=os.path.join(tempfile.mkdtemp(prefix="full-bank."), "arm.jsonl"))
        self.held.__enter__()
        self.addCleanup(self.held.__exit__, None, None, None)

    def _run(self, move=None, **env):
        import run_gates as RG
        root, led = C._tree({"helper_gl.py": "SALT = 1\n", "unrelated.py": "a\n", "t_ok.py": C._LAW})
        self.addCleanup(shutil.rmtree, root, True)
        g = C._gate(root, "t_ok.py", timeout=60)
        g.name = "green"
        held = RG.GATES
        RG.GATES = [g]
        try:
            with C._Env(TV_GATE_LEDGER=led):
                self.assertTrue(C._prove(GL.Ledger(path=led), g))
                C._write(root, "tv/" + (move or "unrelated.py"), "# moved\n")
                C._commit(root, "a later commit")
                with C._Env(**env):
                    res = RG.run(live_watch=False, ledger="full")
            return [s for _g, s, _dt, _d, _b in res if _g.name == "green"]
        finally:
            RG.GATES = held

    def test_an_unchanged_input_is_reused(self):
        self.assertEqual(self._run(), ["CARRY"])

    def test_a_changed_input_forces_a_rerun(self):
        self.assertEqual(self._run(move="helper_gl.py"), ["PASS"])

    def test_full_fresh_runs_every_gate(self):
        self.assertEqual(self._run(TV_FULL_FRESH="1"), ["PASS"])

    def test_ci_never_reuses(self):
        self.assertEqual(self._run(GITHUB_ACTIONS="true"), ["PASS"])

    def test_a_parallel_shard_is_a_full_run(self):
        with open(os.path.join(HERE, "gates_parallel.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn('"run_gates.py"), "--full", "--only"]', src)


RED_PROOF = [
    {"why": "a full run never consults the ledger again", "file": "run_gates.py",
     "find": '(ledger == "changed" or (ledger == "full" and full_banks()))', "replace": '(ledger == "changed")'},
    {"why": "TV_FULL_FRESH is ignored", "file": "run_gates.py",
     "find": '    return os.environ.get("TV_FULL_FRESH") != "1"', "replace": "    return True"},
    {"why": "a moved input is not seen", "file": "gate_ledger.py",
     "find": "        if cwhy or changed is None:\n", "replace": "        changed = set()\n        if cwhy or changed is None:\n"},
]

if __name__ == "__main__":
    unittest.main()
