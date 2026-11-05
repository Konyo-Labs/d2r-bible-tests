# -*- coding: utf-8 -*-
"""v3775 review B1 (REG-2296) - A RUN THAT DIES MID-WAY STILL FOLDS WHAT ITS GATES BANKED.

The fold of the deferred self-arming rows ran after the last gate. A gate that raised (Ctrl-C, an
OSError from the runner, a bug) skipped it: TV_SELF_ARMING_DEFER stayed set and the banked rows sat
in a scratch file nobody named. The gate loop is now inside try/finally; the finally pops the
defer, folds, and if the fold itself fails it prints the scratch path so nothing is silently lost.
"""
import contextlib
import io
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

import self_arming as SA  # noqa: E402
import test_a_gate_proven_on_these_bytes_is_carried as C  # noqa: E402
from test_a_gate_run_does_not_dirty_the_proof_queue import _BANKER  # noqa: E402


class ARunThatDiesStillFolds(unittest.TestCase):
    def _run(self, crash=True, fold=None):
        import run_gates as RG
        root, led = C._tree({"t_bank.py": _BANKER, "t_two.py": _BANKER})
        self.addCleanup(shutil.rmtree, root, True)
        q = os.path.join(tempfile.mkdtemp(prefix="arm-crash."), "queue.jsonl")
        g1, g2 = C._gate(root, "t_bank.py"), C._gate(root, "t_two.py")
        g1.name, g2.name = "banker", "crasher"
        # v3861 - every gate launches through run_gates._run_with_grace (REG-1995's load grace for every gate), so that
        # is the launch this law kills; subprocess.run stays untouched under it
        held, real, held_fold = RG.GATES, RG._run_with_grace, SA.fold_deferred
        seen = []

        def spy(*a, **kw):
            env = kw.get("env") or {}
            argv = a[0] if a else kw.get("args") or []
            # REG-2396 - a GATE run is told by what it runs, never by its environment alone: gate_ledger's own git
            # questions now carry a (GIT_*-free) copy of the run's environment, defer variable included, and counted
            # here as gates they fired the "crash" before the first gate had run - its banked row was never written
            ran_gate = any(os.path.basename(str(x)) in ("t_bank.py", "t_two.py")
                           for x in (argv if isinstance(argv, (list, tuple)) else [argv]))
            if ran_gate and env.get("TV_SELF_ARMING_DEFER"):
                seen.append(env["TV_SELF_ARMING_DEFER"])
                if crash and len(seen) == 2:
                    raise KeyboardInterrupt("a gate died mid-run")
            return real(*a, **kw)
        RG.GATES, RG._run_with_grace = [g1, g2], spy
        if fold is not None:
            SA.fold_deferred = fold
        buf, raised = io.StringIO(), None
        try:
            with C._Env(GITHUB_ACTIONS=None, GATE_LEDGER=None, TV_GATE_LEDGER=led,
                        TV_SELF_ARMING_LEDGER=q, TV_SELF_ARMING_DEFER=None):
                with contextlib.redirect_stdout(buf):
                    try:
                        RG.run(live_watch=False, ledger="full")
                    except KeyboardInterrupt as e:
                        raised = e
                after = os.environ.get("TV_SELF_ARMING_DEFER")
        finally:
            RG.GATES, RG._run_with_grace, SA.fold_deferred = held, real, held_fold
        text = ""
        if os.path.exists(q):
            with io.open(q, encoding="utf-8") as fh:
                text = fh.read()
        return raised, after, text, seen, buf.getvalue()

    def test_the_banked_row_lands_when_a_later_gate_raises(self):
        raised, after, text, seen, _out = self._run()
        self.assertIsNotNone(raised, "the crash was swallowed - the run must still fail")
        self.assertEqual(len(seen), 2, seen)
        self.assertIn('"src": "fixture"', text, "the first gate's banked row was lost when the second raised")

    def test_the_defer_is_cleared_after_a_crash(self):
        _r, after, _t, _s, _o = self._run()
        self.assertIsNone(after, "TV_SELF_ARMING_DEFER leaked out of a crashed run")

    def test_the_scratch_file_is_removed_after_a_crash(self):
        _r, _a, _t, seen, _o = self._run()
        self.assertFalse(os.path.exists(seen[0]), "the scratch file was left behind by a crashed run")

    def test_a_failed_fold_names_the_scratch_file_and_keeps_it(self):
        def broken(path):
            raise OSError("disk full")
        _r, after, text, seen, out = self._run(fold=broken)
        self.assertIsNone(after)
        self.assertIn(seen[0], out, "a failed fold did not print where the rows are kept")
        self.assertTrue(os.path.exists(seen[0]), "a failed fold deleted the only copy of the rows")
        os.remove(seen[0])

    def test_a_clean_run_still_folds(self):
        raised, after, text, _s, _o = self._run(crash=False)
        self.assertIsNone(raised)
        self.assertIsNone(after)
        self.assertEqual(text.count('"src": "fixture"'), 2, text)

    def test_wilson_of_these_attacks_meets_the_bar(self):
        import confidence
        self.assertGreaterEqual(len(RED_PROOF), 10)
        self.assertGreaterEqual(confidence.wilson_lower(len(RED_PROOF), len(RED_PROOF)), 0.722)


RED_PROOF = [
    {"why": "the fold is skipped when a gate raises", "file": "run_gates.py",
     "find": "        _fold_deferred_bank(_defer)\n", "replace": "        if False: _fold_deferred_bank(_defer)\n", "matches": 1},
    {"why": "the fold never runs at all", "file": "run_gates.py",
     "find": "def _fold_deferred_bank(path):\n", "replace": "def _fold_deferred_bank(path):\n    return True\n",
     "matches": 1},
    {"why": "the defer is left set", "file": "run_gates.py",
     "find": "        os.environ.pop(\"TV_SELF_ARMING_DEFER\", None)\n", "replace": "        pass\n", "matches": 1},
    {"why": "the deferred rows are dropped", "file": "run_gates.py",
     "find": "        _nf, _nr = _SA.fold_deferred(path)\n", "replace": "        _nf, _nr = 0, 0\n", "matches": 1},
    {"why": "the scratch file is left behind", "file": "run_gates.py",
     "find": "        os.remove(path)\n", "replace": "        pass\n", "matches": 1},
    {"why": "a failed fold is silent", "file": "run_gates.py",
     "find": "they are kept at %s\"\n", "replace": "they are kept\"\n", "matches": 1},
    {"why": "a failed fold still deletes the scratch file", "file": "run_gates.py",
     "find": "        return False\n    try:\n        os.remove(path)\n", "replace": "        os.remove(path)\n        return False\n    try:\n        os.remove(path)\n",
     "matches": 1},
    {"why": "the crash is swallowed", "file": "run_gates.py",
     "find": "    finally:\n        # v3775 review B1",
     "replace": "    except BaseException:\n        pass\n    finally:\n        # v3775 review B1", "matches": 1},
    {"why": "the fold only runs when nothing raised", "file": "run_gates.py",
     "find": "    finally:\n        # v3775 review B1",
     "replace": "    except BaseException:\n        raise\n    else:\n        # v3775 review B1", "matches": 1},
    {"why": "the runner never hands gates a scratch file", "file": "run_gates.py",
     "find": "        os.environ[\"TV_SELF_ARMING_DEFER\"] = _defer\n", "replace": "        pass\n", "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=1)
