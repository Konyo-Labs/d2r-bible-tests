# -*- coding: utf-8 -*-
"""v3855 (REG-3127) - `node --version` DOES NOT MAKE A GATE'S READS UNKNOWN.

GATE SPEED, ROOT CAUSE. On the v3853 hook 11 gates were "not stored - a python child of the gate ran without the trace".
Traced on 2026-11-02: in test_a_proof_proved_elsewhere_counts_only_under_this_trees_key (65.9 s, the costliest of them) the
three "python children" were `node --version`. The trace counts a node child as followed when NODE_OPTIONS carries
node_trace.cjs, and expects it to write its own B line. `node --version` prints and exits before NODE_OPTIONS is read, so no
B line ever comes and the reader calls the run untraced. The version itself is the ledger's tool key, not a file read.

Now a node child whose only argument is --version or -v is inert. Measured after the fix: that gate,
test_the_bump_refuses_a_tree_that_does_not_parse (20.7 s), test_the_fleet_says_where_a_river_is_stuck (3.1 s) and
test_unseed_is_reversible (1.6 s) trace whole. Any other node child is still a P line that must write its own B line.
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
          "    subprocess.run(sys.argv[1:], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)\n"
          "except (OSError, subprocess.TimeoutExpired):\n"
          "    pass\n")


def _node():
    return shutil.which("node") or shutil.which("nodejs")


class ANodeVersionAskKeepsTheTrace(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="nodev.")
        self.addCleanup(shutil.rmtree, self.root, True)
        os.makedirs(os.path.join(self.root, "tv"))
        self.law = os.path.join(self.root, "tv", "t_child.py")
        with io.open(self.law, "w", encoding="utf-8") as fh:
            fh.write(_CHILD)

    def _trace(self, *argv):
        trace = GL.trace_path()
        self.addCleanup(lambda: os.path.exists(trace) and os.remove(trace))
        env = GL.trace_env(dict(os.environ), self.root, trace)
        subprocess.run([sys.executable, self.law] + list(argv), cwd=self.root, env=env,
                       capture_output=True, text=True, timeout=90)
        with io.open(trace, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
        return GL.read_trace(trace)[1], lines

    def test_node_version_is_inert(self):
        why, lines = self._trace("node", "--version")
        self.assertIsNone(why)
        self.assertFalse([ln for ln in lines if ln.startswith("P\t")], "no node child is owed a B line")

    def test_node_dash_v_is_inert(self):
        self.assertIsNone(self._trace("node", "-v")[0])

    def test_an_absolute_node_version_is_inert(self):
        self.assertIsNone(self._trace("/usr/local/bin/node", "--version")[0])

    @unittest.skipUnless(_node(), "no node here - the followed-child case is UNMEASURED, not passing")
    def test_a_node_program_is_still_followed_by_its_own_b_line(self):
        prog = os.path.join(self.root, "tv", "p.js")
        with io.open(prog, "w", encoding="utf-8") as fh:
            fh.write("require('fs').readFileSync(%r);\n" % self.law)
        why, lines = self._trace(_node(), prog)
        self.assertIsNone(why)
        self.assertTrue([ln for ln in lines if ln.startswith("P\t")], "a node program is a child that writes its own B line")

    def test_node_version_with_a_program_is_not_inert(self):
        _why, lines = self._trace("node", "--version", "x.js")
        self.assertTrue([ln for ln in lines if ln.startswith(("P\t", "U\t"))])

    def test_wilson_of_these_attacks_meets_the_bar(self):
        import confidence
        self.assertGreaterEqual(len(RED_PROOF), 4)
        self.assertGreaterEqual(confidence.wilson_lower(len(RED_PROOF), len(RED_PROOF)), 0.39)


_F = "gate_trace/sitecustomize.py"
_L = "        if is_node and len(args) == 2 and args[1] in (\"--version\", \"-v\"):\n"
RED_PROOF = [{'why': 'node --version untraces the gate',
  'file': 'gate_trace/sitecustomize.py',
  'find': '        if is_node and len(args) == 2 and args[1] in ("--version", "-v"):\n',
  'replace': '        if False:\n',
  'matches': 1},
 {'why': 'node -v untraces the gate',
  'file': 'gate_trace/sitecustomize.py',
  'find': '        if is_node and len(args) == 2 and args[1] in ("--version", "-v"):\n',
  'replace': '        if is_node and len(args) == 2 and args[1] in ("--version",):\n',
  'matches': 1},
 {'why': 'any node child with --version first is called inert',
  'file': 'gate_trace/sitecustomize.py',
  'find': '        if is_node and len(args) == 2 and args[1] in ("--version", "-v"):\n',
  'replace': '        if is_node and len(args) >= 2 and args[1] in ("--version", "-v"):\n',
  'matches': 1},
 {'why': 'every node child is called inert',
  'file': 'gate_trace/sitecustomize.py',
  'find': '        if is_node and len(args) == 2 and args[1] in ("--version", "-v"):\n',
  'replace': '        if is_node:\n',
  'matches': 1}]

if __name__ == "__main__":
    unittest.main(verbosity=1)
