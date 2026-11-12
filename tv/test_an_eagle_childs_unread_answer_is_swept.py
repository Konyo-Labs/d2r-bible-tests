# -*- coding: utf-8 -*-
"""v3902 (REG-3780) - AN EAGLE-CHILD ANSWER NOBODY WILL READ IS SWEPT, AND THE CHILD'S RUNTIME FILES ARE NEVER IN GIT'S VIEW.

MEASURED 11-12 on his Mac's live tree: `git status` listed tv/.eagle_child_<nonce>.json x3 (11-06, 11-08, 11-10, ~50 KB
each), tv/.eagle_child_progress.json and tv/control_agent.lease as UNTRACKED. doctor_rows removes its child's answer in a
`finally`, and a console killed mid-ask (each update relaunch) never runs it - the child finishes and writes rows no process
reads; one per relaunch, and nothing took them. Each ask now sweeps answers older than twice the child's own timeout (no
live ask's), keeping the progress file and anything younger; and .gitignore names all three runtime files.

DRIVEN: the real audit_child.sweep_doctor_orphans over a temp dir with planted ages; doctor_rows' own call by its AST; the
repo's .gitignore patterns. RED_PROOF below.
"""
import ast
import fnmatch
import inspect
import io
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import audit_child as AC  # noqa: E402

NOW = 1794467000.0
OLD = "0123456789abcdef0123456789abcdef"
YOUNG = "fedcba9876543210fedcba9876543210"


class AnEagleChildsUnreadAnswerIsSwept(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="tvd-eagle-child-law-")
        self.addCleanup(shutil.rmtree, self.d, True)
        for name, age in ((".eagle_child_%s.json" % OLD, 3 * 86400), (".eagle_child_%s.json.tmp" % OLD, 3 * 86400),
                          (".eagle_child_%s.json" % YOUNG, 60), (AC.DOCTOR_PROGRESS, 3 * 86400),
                          (".eagle_child_notanonce.json", 3 * 86400)):
            p = os.path.join(self.d, name)
            io.open(p, "w", encoding="utf-8").write("{}")
            os.utime(p, (NOW - age, NOW - age))

    def _left(self):
        return sorted(os.listdir(self.d))

    def test_baseline_the_planted_dir_holds_both_ages(self):
        self.assertEqual(len(self._left()), 5, "PREMISE: the planted files are not all there")

    def test_only_an_answer_older_than_any_live_ask_goes(self):
        """* THE POINT - three answers from three relaunches on his Mac, never taken"""
        self.assertEqual(AC.sweep_doctor_orphans(self.d, now=NOW), 2)
        self.assertEqual(self._left(), sorted([".eagle_child_%s.json" % YOUNG, AC.DOCTOR_PROGRESS,
                                               ".eagle_child_notanonce.json"]),
                         "the sweep took the wrong files")

    def test_an_unlistable_dir_is_unknown(self):
        self.assertIsNone(AC.sweep_doctor_orphans(os.path.join(self.d, "nope"), now=NOW))

    def test_each_ask_sweeps_first(self):
        tree = ast.parse(inspect.getsource(AC.doctor_rows).lstrip())
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and getattr(n.func, "id", None) == "sweep_doctor_orphans"]
        self.assertEqual(len(calls), 1, "doctor_rows no longer sweeps what a killed console left")

    def test_git_never_sees_the_childs_runtime_files(self):
        pats = [l.strip() for l in io.open(os.path.join(os.path.dirname(HERE), ".gitignore"), encoding="utf-8")
                if l.strip() and not l.startswith("#") and not l.startswith("!")]
        for name in ("tv/.eagle_child_%s.json" % OLD, "tv/.eagle_child_progress.json", "tv/control_agent.lease"):
            self.assertTrue(any(fnmatch.fnmatch(name, p) for p in pats), "%s is not ignored - it lands in git status" % name)


RED_PROOF = [
    {"why": "REG-3780 - the sweep takes a young answer a live ask may still read",
     "file": "tv/audit_child.py",
     "find": "            if now - os.path.getmtime(p) <= older_s:\n",
     "replace": "            if False:\n",
     "matches": 1},
    {"why": "REG-3780 - an ask stops sweeping what a killed console left (one orphan per relaunch again)",
     "file": "tv/audit_child.py",
     "find": "        sweep_doctor_orphans(root)        # REG-3780 - what a killed console's asks left behind\n",
     "replace": "        pass\n",
     "matches": 1},
    {"why": "REG-3780 - the eagle child's answers show in git status again",
     "file": "../.gitignore",          # the ROOT one: heart2 resolves tv/ first, and tv/.gitignore exists
     "find": "tv/.eagle_child_*.json\n",
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
