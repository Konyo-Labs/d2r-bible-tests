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
          "    import os\n"
          "    subprocess.run(sys.argv[1:], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20,\n"
          "                   cwd=os.environ.get('T_CHILD_CWD') or None)\n"
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

    def _why(self, *argv, **kw):
        trace = GL.trace_path()
        self.addCleanup(lambda: os.path.exists(trace) and os.remove(trace))
        env = GL.trace_env(dict(os.environ), self.root, trace)
        if kw.get("child_cwd"):
            env["T_CHILD_CWD"] = kw["child_cwd"]
        subprocess.run([sys.executable, self.law] + list(argv), cwd=kw.get("cwd") or self.root, env=env,
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

    # v3859 L1 (#230, Claude slice 3): the forms that read a file they are named never untrace as inert
    def test_defaults_import_of_a_bare_name_still_untraces(self):
        self.assertIn("started defaults", self._why("defaults", "import", "com.example.x", "x.plist") or "")

    def test_defaults_on_a_home_path_still_untraces(self):
        self.assertIn("started defaults", self._why("defaults", "read", "~/x.plist") or "")

    def test_sysctl_reading_a_file_still_untraces(self):
        self.assertIn("started sysctl", self._why("sysctl", "-f", "x.conf") or "")

    def test_a_relative_path_is_read_in_the_childs_cwd(self):
        out = tempfile.mkdtemp(prefix="print_out.")
        self.addCleanup(shutil.rmtree, out, True)
        self.assertIn("started defaults", self._why("defaults", "read", "tv/x.plist", cwd=out, child_cwd=self.root) or "")

    def test_a_sysctl_meter_is_still_inert(self):
        self.assertIsNone(self._why("sysctl", "-n", "hw.memsize"))

    def test_cat_still_untraces(self):
        # a bare name has no "/", so only the list itself keeps cat out
        self.assertIn("started cat", self._why("cat", "README") or "")

    def test_wilson_of_these_attacks_meets_the_bar(self):
        import confidence
        self.assertGreaterEqual(len(RED_PROOF), 5)
        self.assertGreaterEqual(confidence.wilson_lower(len(RED_PROOF), len(RED_PROOF)), 0.45)


RED_PROOF = [{'why': 'echo untraces the gate',
  'file': 'gate_trace/sitecustomize.py',
  'find': '        if head in ("echo", "printf") and not any(\n',
  'replace': '        if head in ("printf",) and not any(\n',
  'matches': 1},
 {'why': 'printf untraces the gate',
  'file': 'gate_trace/sitecustomize.py',
  'find': '        if head in ("echo", "printf") and not any(\n',
  'replace': '        if head in ("echo",) and not any(\n',
  'matches': 1},
 {'why': 'defaults untraces the gate',
  'file': 'gate_trace/sitecustomize.py',
  'find': '        if head == "defaults" and not any(a in ("import", "export") for a in args[1:]) and not any(\n',
  'replace': '        if head == "never" and not any(a in ("import", "export") for a in args[1:]) and not any(\n',
  'matches': 1},
 {'why': 'defaults on a plist here is called inert',
  'file': 'gate_trace/sitecustomize.py',
  # v3886 (#107) - the arg test became _pathish (a Windows path is a path); the proof moved with it
  'find': '                _here(a) for a in args[1:] if _pathish(a) or a.startswith("~")):\n',
  'replace': '                False for a in args[1:] if _pathish(a) or a.startswith("~")):\n',
  'matches': 1},
 {'why': 'cat is called inert',
  'file': 'gate_trace/sitecustomize.py',
  'find': '        if head in ("echo", "printf") and not any(\n',
  'replace': '        if head in ("echo", "printf", "cat") and not any(\n',
  'matches': 1},
 {'why': 'v3859 L1 - defaults import of a bare name is called inert',
  'file': 'gate_trace/sitecustomize.py',
  'find': '        if head == "defaults" and not any(a in ("import", "export") for a in args[1:]) and not any(\n',
  'replace': '        if head == "defaults" and not any(a in ("export",) for a in args[1:]) and not any(\n',
  'matches': 1},
 {'why': "v3859 L1 - defaults' own ~ expansion is called inert",
  'file': 'gate_trace/sitecustomize.py',
  'find': '            if a.startswith("~"):\n                return True\n',
  'replace': '            if a.startswith("~"):\n                return False\n',
  'matches': 1},
 {'why': 'v3859 L1 - sysctl -f is called inert',
  'file': 'gate_trace/sitecustomize.py',
  'find': '                head == "sysctl" and any(a.startswith(("-f", "-p", "--load", "--system")) for a in '
          'args[1:])):\n',
  'replace': '                False):\n',
  'matches': 1},
 {'why': "v3859 L1 - a relative path resolves against the parent's cwd, not the child's",
  'file': 'gate_trace/sitecustomize.py',
  'find': '        _cbase = fsdecode(cwd) if cwd is not None else getcwd()\n',
  'replace': '        _cbase = getcwd()\n',
  'matches': 1}]

if __name__ == "__main__":
    unittest.main(verbosity=1)
