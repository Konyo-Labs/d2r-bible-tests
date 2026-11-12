# -*- coding: utf-8 -*-
"""v3775 (REG-2296) — A CHILD THAT READS NO FILE DOES NOT MAKE A GATE'S READS UNKNOWN.

The gate trace marks a run it cannot follow (any non-python child) as never-carry. On a v3775 bump
that cost test_the_bump_refuses_a_tree_that_does_not_parse (pgrep, 39 s) and test_an_exec_leaves_no_corpse
(sleep, 12 s) a full run every time. `sleep` reads a clock, and `ps` / `pgrep` read the process table: a
path inside a pgrep pattern is matched against command lines, never opened. They are inert now. lsof
with a path in this checkout still is not, and every other child (bash, sh, chrome, perl) still is.
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

import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import gate_ledger as GL  # noqa: E402

_CHILD = ("import subprocess, sys\n"
          "try:\n"
          "    subprocess.run(sys.argv[1:], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
          "except OSError:\n"
          "    pass\n")


class AnInertChildKeepsTheTrace(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="inert.")
        self.addCleanup(shutil.rmtree, self.root, True)
        os.makedirs(os.path.join(self.root, "tv"))
        self.law = os.path.join(self.root, "tv", "t_child.py")
        with io.open(self.law, "w", encoding="utf-8") as fh:
            fh.write(_CHILD)

    def _why(self, *argv):
        trace = GL.trace_path()
        self.addCleanup(lambda: os.path.exists(trace) and os.remove(trace))
        env = GL.trace_env(dict(os.environ), self.root, trace)
        subprocess.run([sys.executable, self.law] + list(argv), cwd=self.root, env=env,
                       capture_output=True, text=True, timeout=60)
        _facts, why = GL.read_trace(trace)
        return why

    def test_sleep_is_inert(self):
        self.assertIsNone(self._why("sleep", "0"))

    def test_an_absolute_sleep_is_inert(self):
        self.assertIsNone(self._why("/bin/sleep", "0"))

    def test_pgrep_with_a_path_in_its_pattern_is_inert(self):
        self.assertIsNone(self._why("pgrep", "-f", os.path.join(self.root, "tv", "t_child.py")))

    def test_ps_is_inert(self):
        self.assertIsNone(self._why("ps", "-o", "pid="))

    def test_bash_still_cannot_be_followed(self):
        self.assertIn("started bash", self._why("bash", "-c", "true") or "")

    def test_lsof_on_a_file_here_still_cannot_be_followed(self):
        self.assertIn("started lsof", self._why("lsof", self.law) or "")

    def test_lsof_of_the_process_table_is_inert(self):
        self.assertIsNone(self._why("lsof", "-p", "1"))

    def test_wilson_of_these_attacks_meets_the_bar(self):
        import confidence
        self.assertGreaterEqual(len(RED_PROOF), 10)
        self.assertGreaterEqual(confidence.wilson_lower(len(RED_PROOF), len(RED_PROOF)), 0.722)


RED_PROOF = [
    {"why": "sleep untraces the gate", "file": "gate_trace/sitecustomize.py",
     "find": "        if head in (\"ps\", \"pgrep\", \"sleep\"):\n", "replace": "        if head in (\"ps\", \"pgrep\"):\n",
     "matches": 1},
    {"why": "pgrep untraces the gate", "file": "gate_trace/sitecustomize.py",
     "find": "        if head in (\"ps\", \"pgrep\", \"sleep\"):\n", "replace": "        if head in (\"ps\", \"sleep\"):\n",
     "matches": 1},
    {"why": "ps untraces the gate", "file": "gate_trace/sitecustomize.py",
     "find": "        if head in (\"ps\", \"pgrep\", \"sleep\"):\n", "replace": "        if head in (\"pgrep\", \"sleep\"):\n",
     "matches": 1},
    {"why": "a path in a pgrep pattern untraces the gate", "file": "gate_trace/sitecustomize.py",
     "find": "        if head in (\"ps\", \"pgrep\", \"sleep\"):\n",
     # v3901 (REG-3760) - EITHER SEPARATOR. With "/" alone the tamper never bit on Windows: the case's path is C:\\...\\t_child.py,
     # so the sabotage changed nothing there and the OLD ALT's census filed this law BLIND ("a proof of it stayed green
     # tampered here", win32) - one BLIND shuts every lock on that PC (REG-1677)
     "replace": "        if head in (\"ps\", \"pgrep\", \"sleep\") and not any(rel(a) is not None for a in args[1:] if (\"/\" in a or \"\\\\\" in a)):\n",
     "matches": 1},
    {"why": "bash is called inert", "file": "gate_trace/sitecustomize.py",
     "find": "        if head in (\"ps\", \"pgrep\", \"sleep\"):\n", "replace": "        if head in (\"ps\", \"pgrep\", \"sleep\", \"bash\"):\n",
     "matches": 1},
    {"why": "lsof on a file here is called inert", "file": "gate_trace/sitecustomize.py",
     "find": "                rel(a) is not None for a in args[1:] if _pathish(a)):\n            return  # the process table, not a file in this checkout\n",
     "replace": "                False for a in args[1:] if _pathish(a)):\n            return  # the process table, not a file in this checkout\n",
     "matches": 1},
    {"why": "lsof of the process table untraces the gate", "file": "gate_trace/sitecustomize.py",
     "find": "        if head == \"lsof\" and not any(\n", "replace": "        if head == \"no-lsof\" and not any(\n",
     "matches": 1},
    {"why": "an absolute child path is not reduced to its name", "file": "gate_trace/sitecustomize.py",
     "find": "        head = _cmd_name(args[0]) if args else \"\"  # REG-3371", "replace": "        head = args[0] if args else \"\"  # REG-3371",
     "matches": 1},
    {"why": "a child nobody can follow is dropped silently", "file": "gate_trace/sitecustomize.py",
     "find": "        emit(\"U\", \"started %s\" % (head or \"a process\"))\n", "replace": "        pass\n",
     "matches": 1},
    {"why": "an untraced line is ignored by the reader", "file": "gate_ledger.py",
     "find": "            return None, \"the gate %s, which the trace cannot follow\" % text  # LEDGER-UNTRACED\n",
     "replace": "            continue  # LEDGER-UNTRACED\n", "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=1)
