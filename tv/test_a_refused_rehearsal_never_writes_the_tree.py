# -*- coding: utf-8 -*-
"""REG-3674 - A REFUSED REHEARSAL NEVER WRITES THE TREE IT GRADES.

MEASURED 2026-11-11 05:25: v3895's main push was refused by the hook's readiness step (tv/preship.py --mac-ready), and the
CLI's "remember the first red" appended two lessons to the TRACKED tv/preship_lessons.json of the very worktree the hook
was grading - the tree went dirty under its own gate, and every later readiness run carried a false lesson. A refusal is
now remembered in the MACHINE ledger (git's common dir, beside the speed and second-eye ledgers): never a tracked byte,
read by every checkout of this machine, and its lesson still runs (_lesson_checks reads both ledgers).

DRIVEN: a throwaway git repo with a committed lessons file; the CLI's own main() with one planted red check.
RED_PROOF below.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import preship as P  # noqa: E402

_CLEAN = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def _git(root, *args):
    return subprocess.run(["git"] + list(args), cwd=root, capture_output=True, text=True, env=_CLEAN)


class ARefusedRehearsalNeverWritesTheTree(unittest.TestCase):
    def setUp(self):
        env = mock.patch.dict(os.environ, _CLEAN, clear=True)    # a hook's GIT_DIR must never point this at the real repo
        env.start()
        self.addCleanup(env.stop)
        self.root = tempfile.mkdtemp(prefix="preship-lessons-")
        self.addCleanup(shutil.rmtree, self.root, True)
        os.makedirs(os.path.join(self.root, "tv"))
        self.lessons = os.path.join(self.root, "tv", P.LESSONS_NAME)
        with io.open(self.lessons, "w", encoding="utf-8") as fh:
            fh.write('{\n  "lessons": []\n}\n')
        self.assertEqual(_git(self.root, "init", "-q").returncode, 0)
        _git(self.root, "config", "core.autocrlf", "false")    # REG-3626 - the fixture's LF stays LF on Windows
        _git(self.root, "add", "-A")
        self.assertEqual(_git(self.root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x").returncode, 0)

    def _refuse(self):
        red = [{"name": "render_check", "code": 1, "ms": 1, "say": "planted red - the render gate refused"}]
        with mock.patch.object(P, "run_checks", lambda *a, **k: (1, red)), \
                mock.patch.object(P, "format_table", lambda *a, **k: ""):
            return P.main(["--only", "render_check", "--root", self.root])

    def test_a_refusal_leaves_the_tracked_ledger_as_committed(self):
        with io.open(self.lessons, encoding="utf-8") as fh:
            before = fh.read()
        self.assertEqual(self._refuse(), 1, "PREMISE: the planted red did not refuse")
        with io.open(self.lessons, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), before, "a refused rehearsal wrote the TRACKED lessons file of the tree it graded")
        self.assertEqual(_git(self.root, "status", "--porcelain").stdout.strip(), "", "the refusal left the tree dirty")

    def test_the_refusal_is_remembered_on_this_machine_and_its_check_runs(self):
        self._refuse()
        p = P.auto_lessons_path(self.root)
        self.assertTrue(p and os.path.isfile(p), "the refusal was remembered nowhere")
        self.assertTrue(os.path.realpath(p).startswith(os.path.realpath(os.path.join(self.root, ".git"))),
                        "the machine ledger is not in git's own dir: %s" % p)
        with io.open(p, encoding="utf-8") as fh:
            rows = json.load(fh)["lessons"]
        self.assertEqual([r["check"] for r in rows], ["render_check"])
        self.assertIn("render_check", P._lesson_checks(self.root, []),
                      "a lesson remembered on this machine does not run in its next rehearsal")


RED_PROOF = [
    {"why": "REG-3674 - the CLI remembers a refusal in the TRACKED lessons file again (the tree it grades goes dirty)",
     "file": "tv/preship.py",
     "find": "                remember_refusal(reds[0][\"say\"], reds[0][\"name\"], root=root, cls=\"auto\", local=True)\n",
     "replace": "                remember_refusal(reds[0][\"say\"], reds[0][\"name\"], root=root, cls=\"auto\")\n",
     "matches": 1},
    {"why": "REG-3674 - a lesson remembered on this machine no longer runs in the next rehearsal",
     "file": "tv/preship.py",
     "find": "    rows += load_auto_lessons(root)",
     "replace": "    rows += []",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
