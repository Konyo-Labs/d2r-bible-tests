# -*- coding: utf-8 -*-
"""v3855 (REG-3124) - A MACHINE METER DOES NOT MAKE A GATE'S READS UNKNOWN.

GATE SPEED. On the v3853 hook (fast gate set, 2026-11-02) 138 gates were "not stored" because the trace saw a
child it cannot follow, so each one runs on every push. Six of those children only read a meter of the machine,
never a file in this checkout: vm_stat (memory pages), sysctl (kernel values), true (nothing), netstat (sockets),
ioreg (the IO registry), lsappinfo (the app list). That is the same class REG-2296 already made inert for sleep,
ps and pgrep. They cost 10 gates about 64 s idle per push (gate_costs.json: test_button_matrix 12.9 s,
test_an_exec_leaves_no_corpse 9.8 s, test_the_doctor_never_forks_a_quartz_process 6.4 s, test_vault_lane 5.7 s,
test_vault_retro 4.9 s, robot_smoke 20 s, ...), about 1.6-1.8x that under a hook's load.

A meter given a path inside this checkout is NOT inert and still untraces the gate. Every other child (bash, git,
Chrome, sips, caffeinate - which can run a command - and defaults) still does. Nothing is carried that its real
inputs moved under: the gate's own python reads stay traced exactly as before.
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


class AMachineMeterKeepsTheTrace(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="meter.")
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

    def test_vm_stat_is_inert(self):
        self.assertIsNone(self._why("vm_stat"))

    def test_sysctl_is_inert(self):
        self.assertIsNone(self._why("sysctl", "-n", "hw.ncpu"))

    def test_true_is_inert(self):
        self.assertIsNone(self._why("true"))

    def test_an_absolute_true_is_inert(self):
        self.assertIsNone(self._why("/usr/bin/true"))

    def test_netstat_ioreg_and_lsappinfo_are_inert(self):
        # the child may be absent on this OS; the TRACE decides, never whether it ran
        for argv in (("netstat", "-an"), ("ioreg", "-l", "-w0", "-d1"), ("lsappinfo", "list")):
            self.assertIsNone(self._why(*argv), argv)

    def test_a_meter_given_a_file_here_still_cannot_be_followed(self):
        self.assertIn("started true", self._why("true", self.law) or "")

    def test_caffeinate_can_run_a_command_so_it_still_untraces(self):
        self.assertIn("started caffeinate", self._why("caffeinate", "-i", "true") or "")

    def test_bash_still_cannot_be_followed(self):
        self.assertIn("started bash", self._why("bash", "-c", "true") or "")

    def test_wilson_of_these_attacks_meets_the_bar(self):
        import confidence
        self.assertGreaterEqual(len(RED_PROOF), 8)
        self.assertGreaterEqual(confidence.wilson_lower(len(RED_PROOF), len(RED_PROOF)), 0.6)


_LINE = "        if head in (\"vm_stat\", \"sysctl\", \"true\", \"netstat\", \"ioreg\", \"lsappinfo\") and not any(\n"


def _drop(name):
    return {"why": "%s untraces the gate" % name, "file": "gate_trace/sitecustomize.py", "find": _LINE,
            "replace": _LINE.replace("\"%s\", " % name, "").replace(", \"%s\")" % name, ")"), "matches": 1}


RED_PROOF = [{'why': 'vm_stat untraces the gate',
  'file': 'gate_trace/sitecustomize.py',
  'find': '        if head in ("vm_stat", "sysctl", "true", "netstat", "ioreg", "lsappinfo") and not any(\n',
  'replace': '        if head in ("sysctl", "true", "netstat", "ioreg", "lsappinfo") and not any(\n',
  'matches': 1},
 {'why': 'sysctl untraces the gate',
  'file': 'gate_trace/sitecustomize.py',
  'find': '        if head in ("vm_stat", "sysctl", "true", "netstat", "ioreg", "lsappinfo") and not any(\n',
  'replace': '        if head in ("vm_stat", "true", "netstat", "ioreg", "lsappinfo") and not any(\n',
  'matches': 1},
 {'why': 'true untraces the gate',
  'file': 'gate_trace/sitecustomize.py',
  'find': '        if head in ("vm_stat", "sysctl", "true", "netstat", "ioreg", "lsappinfo") and not any(\n',
  'replace': '        if head in ("vm_stat", "sysctl", "netstat", "ioreg", "lsappinfo") and not any(\n',
  'matches': 1},
 {'why': 'netstat untraces the gate',
  'file': 'gate_trace/sitecustomize.py',
  'find': '        if head in ("vm_stat", "sysctl", "true", "netstat", "ioreg", "lsappinfo") and not any(\n',
  'replace': '        if head in ("vm_stat", "sysctl", "true", "ioreg", "lsappinfo") and not any(\n',
  'matches': 1},
 {'why': 'ioreg untraces the gate',
  'file': 'gate_trace/sitecustomize.py',
  'find': '        if head in ("vm_stat", "sysctl", "true", "netstat", "ioreg", "lsappinfo") and not any(\n',
  'replace': '        if head in ("vm_stat", "sysctl", "true", "netstat", "lsappinfo") and not any(\n',
  'matches': 1},
 {'why': 'lsappinfo untraces the gate',
  'file': 'gate_trace/sitecustomize.py',
  'find': '        if head in ("vm_stat", "sysctl", "true", "netstat", "ioreg", "lsappinfo") and not any(\n',
  'replace': '        if head in ("vm_stat", "sysctl", "true", "netstat", "ioreg") and not any(\n',
  'matches': 1},
 {'why': 'a meter given a file here is called inert',
  'file': 'gate_trace/sitecustomize.py',
  # v3859 L1 (10c4ba8d) renamed the check to _here() and added the sysctl -f/-p clause; the proof moved with it
  'find': '                _here(a) for a in args[1:] if "/" in a) and not (\n',
  'replace': '                False for a in args[1:] if "/" in a) and not (\n',
  'matches': 1},
 {'why': 'caffeinate is called inert',
  'file': 'gate_trace/sitecustomize.py',
  'find': '        if head in ("vm_stat", "sysctl", "true", "netstat", "ioreg", "lsappinfo") and not any(\n',
  'replace': '        if head in ("vm_stat", "sysctl", "true", "netstat", "ioreg", "lsappinfo", '
             '"caffeinate") and not any(\n',
  'matches': 1},
 {'why': 'bash is called inert',
  'file': 'gate_trace/sitecustomize.py',
  'find': '        if head in ("vm_stat", "sysctl", "true", "netstat", "ioreg", "lsappinfo") and not any(\n',
  'replace': '        if head in ("vm_stat", "sysctl", "true", "netstat", "ioreg", "lsappinfo", "bash") and '
             'not any(\n',
  'matches': 1}]

if __name__ == "__main__":
    unittest.main(verbosity=1)
