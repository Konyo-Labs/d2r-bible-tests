# -*- coding: utf-8 -*-
"""v3855 (REG-3126) - ECHO, PRINTF AND A DEFAULTS DOMAIN READ NO FILE HERE, SO THEY DO NOT UNTRACE A GATE.

GATE SPEED. On the v3853 hook test_a_stub_agent_never_films_his_screen (echo, 4.6 s) and test_d2jsp_desk (defaults, 4.2 s)
were "not stored" and ran on every push. echo and printf print their own argv; `defaults read <domain>` reads a preference
domain under the user's Library, never a file in this checkout. Each is inert now unless an argument names a path inside
the checkout (`defaults read <path here>`, `defaults import <domain> <path here>`), which still untraces the gate.
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
          "    subprocess.run(sys.argv[1:], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)\n"
          "except (OSError, subprocess.TimeoutExpired):\n"
          "    pass\n")


class APrintingChildKeepsTheTrace(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="print.")
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
        return GL.read_trace(trace)[1]

    def test_echo_is_inert(self):
        self.assertIsNone(self._why("echo", "hello"))

    def test_printf_is_inert(self):
        self.assertIsNone(self._why("printf", "%s", "x"))

    def test_a_defaults_domain_read_is_inert(self):
        self.assertIsNone(self._why("defaults", "read", "com.example.never-a-real-domain"))

    def test_defaults_on_a_plist_here_still_untraces(self):
        self.assertIn("started defaults", self._why("defaults", "read", os.path.join(self.root, "tv", "x.plist")) or "")

    def test_cat_still_untraces(self):
        # a bare name has no "/", so only the list itself keeps cat out
        self.assertIn("started cat", self._why("cat", "README") or "")

    def test_wilson_of_these_attacks_meets_the_bar(self):
        import confidence
        self.assertGreaterEqual(len(RED_PROOF), 5)
        self.assertGreaterEqual(confidence.wilson_lower(len(RED_PROOF), len(RED_PROOF)), 0.45)


_F = "gate_trace/sitecustomize.py"
_L = "        if head in (\"echo\", \"printf\", \"defaults\") and not any(\n"
RED_PROOF = [{'why': 'echo untraces the gate',
  'file': 'gate_trace/sitecustomize.py',
  'find': '        if head in ("echo", "printf", "defaults") and not any(\n',
  'replace': '        if head in ("printf", "defaults") and not any(\n',
  'matches': 1},
 {'why': 'printf untraces the gate',
  'file': 'gate_trace/sitecustomize.py',
  'find': '        if head in ("echo", "printf", "defaults") and not any(\n',
  'replace': '        if head in ("echo", "defaults") and not any(\n',
  'matches': 1},
 {'why': 'defaults untraces the gate',
  'file': 'gate_trace/sitecustomize.py',
  'find': '        if head in ("echo", "printf", "defaults") and not any(\n',
  'replace': '        if head in ("echo", "printf") and not any(\n',
  'matches': 1},
 {'why': 'defaults on a plist here is called inert',
  'file': 'gate_trace/sitecustomize.py',
  'find': '                rel(a) is not None for a in args[1:] if "/" in a):\n'
          '            return  # prints its own argv',
  'replace': '                False for a in args[1:] if "/" in a):\n'
             '            return  # prints its own argv',
  'matches': 1},
 {'why': 'cat is called inert',
  'file': 'gate_trace/sitecustomize.py',
  'find': '        if head in ("echo", "printf", "defaults") and not any(\n',
  'replace': '        if head in ("echo", "printf", "defaults", "cat") and not any(\n',
  'matches': 1}]

if __name__ == "__main__":
    unittest.main(verbosity=1)
