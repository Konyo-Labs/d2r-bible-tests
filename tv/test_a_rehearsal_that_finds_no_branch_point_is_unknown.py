# -*- coding: utf-8 -*-
"""v3897 (REG-3702, the Grok CLI's follow-up look on v3895) - A REHEARSAL THAT CANNOT FIND ITS BRANCH POINT IS UNKNOWN.

preship._changed_test_stems finds the changed tv/test_*.py by diffing from the merge-base with origin/main (or main). When
neither resolves, it fell back to diffing against HEAD - which sees only uncommitted edits - so every test the branch had
COMMITTED was left out, and check_changed answered "no changed agent tests": a rehearsal that rehearsed nothing, read as a
pass. Now no branch point is UNKNOWN (exit 2), and the hook's lane never reads it as green.

DRIVEN on a throwaway git repo with no main and no origin, one committed test file. RED_PROOF below.
"""
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
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import preship as P  # noqa: E402

_CLEAN = dict((k, v) for k, v in os.environ.items() if not k.startswith("GIT_") and k != "TV_PRESHIP_BASE")


def _git(root, *args):
    return subprocess.run(["git"] + list(args), cwd=root, capture_output=True, text=True, env=_CLEAN)


class ARehearsalThatFindsNoBranchPointIsUnknown(unittest.TestCase):
    def setUp(self):
        env = mock.patch.dict(os.environ, _CLEAN, clear=True)
        env.start()
        self.addCleanup(env.stop)
        self.root = tempfile.mkdtemp(prefix="preship-nobase-")
        self.addCleanup(shutil.rmtree, self.root, True)
        os.makedirs(os.path.join(self.root, "tv"))
        for name, body in (("run_gates.py", "print('never run here')\n"), ("test_a_committed_law.py", "pass\n")):
            with open(os.path.join(self.root, "tv", name), "w") as fh:
                fh.write(body)
        self.assertEqual(_git(self.root, "init", "-q", "-b", "work").returncode, 0)
        _git(self.root, "config", "core.autocrlf", "false")
        _git(self.root, "add", "-A")
        self.assertEqual(_git(self.root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x").returncode, 0)

    def test_no_branch_point_is_unknown_never_nothing_changed(self):
        """* THE POINT"""
        self.assertNotEqual(_git(self.root, "rev-parse", "--verify", "-q", "main").returncode, 0,
                            "PREMISE: the fixture has a main branch, so a branch point exists")
        code, say = P.check_changed(self.root)
        self.assertEqual(code, 2, "a rehearsal with no branch point read as %r: %s" % (code, say))
        self.assertIn("UNKNOWN", say)

    def test_the_stems_say_no_base_rather_than_head(self):
        stems, base = P._changed_test_stems(self.root)
        self.assertIsNone(base, "the branch point fell back to %r - a diff that sees only uncommitted edits" % base)


RED_PROOF = [
    {"why": "v3897 (REG-3702) - with no branch point the rehearsal diffs against HEAD again and reads 'no changed tests'",
     "file": "tv/preship.py",
     "find": "            if base is None:\n                return [], None\n",
     "replace": "            if base is None:\n                base = \"HEAD\"\n",
     "matches": 1},
    {"why": "v3897 (REG-3702) - check_changed reads an unknown branch point as nothing changed",
     "file": "tv/preship.py",
     "find": "    if base is None:                    # v3897 (REG-3702) - no branch point: the changed tests are UNKNOWN, never none\n",
     "replace": "    if False:\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
