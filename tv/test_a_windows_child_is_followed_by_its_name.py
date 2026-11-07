# -*- coding: utf-8 -*-
"""#107 (v3880, REG-3371) - ON WINDOWS THE TRACE NAMES A CHILD BY ITS COMMAND, NOT BY ITS WHOLE COMMAND LINE.

CPython's Windows subprocess joins the argv with list2cmdline BEFORE it raises the `subprocess.Popen` audit event, so the
gate trace (tv/gate_trace/sitecustomize.py) saw `node --version` as ONE argument. Its name was never node, git, sleep or
python, so every child of a traced gate wrote a U line, "the trace cannot follow". MEASURED on GitHub's Windows runner
(#107's probe, run 42367869017): test_a_node_version_ask_does_not_untrace_a_gate read "the gate started node --version,
which the trace cannot follow", and six sibling trace laws the same. On his ALTs every gate that starts any child ran
untraced: never carried, proved again.

Now the hook splits a Windows command line back by CommandLineToArgvW's rules (the inverse of list2cmdline), and reads a
name without .exe / .cmd / .bat / .com, in lower case. Pinned two ways: the split round-trips list2cmdline on hard
arguments, and a REAL traced child raises the audit event in Windows' shape (the hook's Windows flag set) and must trace
whole for an inert child while an unknown one still reads untraced. RED_PROOF below.
"""
import importlib.util
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


def _hook():
    sp = importlib.util.spec_from_file_location("tvd_gate_trace_hook", os.path.join(HERE, "gate_trace", "sitecustomize.py"))
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)       # unarmed: with no TV_GATE_TRACE it installs nothing
    return m


# a child that raises the event exactly the way Windows' subprocess does: the command LINE, not the list
_WIN_CHILD = ("import sys\n"
              "import sitecustomize\n"
              "sitecustomize._NT = True\n"
              "sys.audit('subprocess.Popen', None, sys.argv[1], None, None)\n")


class TheCommandLineIsSplitBack(unittest.TestCase):

    def test_list2cmdline_round_trips(self):
        h = _hook()
        for argv in (["C:\\Program Files\\nodejs\\node.exe", "--version"], ["a b", 'c"d', "e\\", 'f\\"g', ""],
                     ["x\\\\", '"q"'], ["tab\there", "end\\\\"], ["plain"]):
            with self.subTest(argv=argv):
                self.assertEqual(h._argv_of(subprocess.list2cmdline(argv), nt=True), argv)

    def test_a_windows_name_drops_its_suffix_and_case(self):
        h = _hook()
        self.assertEqual(h._cmd_name("C:\\Program Files\\nodejs\\Node.EXE", nt=True), "node")
        self.assertEqual(h._cmd_name("C:/Program Files/Git/usr/bin/sleep.exe", nt=True), "sleep")
        self.assertEqual(h._cmd_name("git.cmd", nt=True), "git")
        self.assertEqual(h._cmd_name("/usr/local/bin/node", nt=False), "node")
        self.assertEqual(h._argv_of("ls -la /tmp", nt=False), ["ls -la /tmp"], "a POSIX shell string changed shape")


class AWindowsChildIsFollowed(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="winchild.")
        self.addCleanup(shutil.rmtree, self.root, True)
        os.makedirs(os.path.join(self.root, "tv"))
        self.law = os.path.join(self.root, "tv", "t_child.py")
        with io.open(self.law, "w", encoding="utf-8") as fh:
            fh.write(_WIN_CHILD)

    def _trace(self, cmdline):
        trace = GL.trace_path()
        self.addCleanup(lambda: os.path.exists(trace) and os.remove(trace))
        env = GL.trace_env(dict(os.environ), self.root, trace)
        r = subprocess.run([sys.executable, self.law, cmdline], cwd=self.root, env=env, capture_output=True, text=True,
                           timeout=90)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        return GL.read_trace(trace)[1]

    def test_windows_node_version_traces_whole(self):
        """* THE POINT: Windows' `"...\\node.exe" --version` is the inert node version ask, never an untraced child"""
        self.assertIsNone(self._trace('"C:\\Program Files\\nodejs\\node.exe" --version'))

    def test_windows_sleep_traces_whole(self):
        self.assertIsNone(self._trace("C:\\PROGRA~1\\Git\\usr\\bin\\SLEEP.EXE 0"))

    def test_an_unknown_windows_child_is_still_untraced(self):
        why = self._trace('"C:\\tools\\mystery.exe" --read C:\\x')
        self.assertIsNotNone(why, "a child the trace cannot follow was taken as followed")
        self.assertIn("cannot follow", why)


RED_PROOF = [
    {"why": "#107 - Windows' command line reaches the trace as one argument again (node --version untraced there)",
     "file": "gate_trace/sitecustomize.py",
     "find": "        args = _argv_of(argv)                      # REG-3371",
     "replace": "        args = [str(a) for a in (argv if isinstance(argv, (list, tuple)) else [argv or \"\"])]  # REG-3371",
     "matches": 1},
    {"why": "#107 - a Windows name keeps its .exe, so node.exe and sleep.exe are never named",
     "file": "gate_trace/sitecustomize.py",
     "find": "        if low.endswith(suf):\n            return low[:-len(suf)]\n",
     "replace": "        if False:\n            return low[:-len(suf)]\n",
     "matches": 1},
    {"why": "#107 - the Windows split no longer splits",
     "file": "gate_trace/sitecustomize.py",
     "find": "        got = _split_cmdline(s)\n",
     "replace": "        got = [s]\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
