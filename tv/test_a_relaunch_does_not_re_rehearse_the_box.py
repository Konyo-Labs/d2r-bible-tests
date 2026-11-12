# -*- coding: utf-8 -*-
"""v3902 (REG-3776, #200) - A SHIP RELAUNCHED ON A COMMIT BOTH ci BRANCHES ALREADY HOLD DOES NOT RE-RUN THE BOX REHEARSAL.

MEASURED 11-12: v3900's ship was relaunched by hand on e0513929e after its flaked shards were re-run (same commit, both ci
branches already at it). It spent ~7 minutes re-running the box rehearsal before reading the verdict GitHub was already
grading. The box rehearsal exists only to keep a red off the ci push (REG-3646), and a resumed ship makes no ci push (v3866).
Now, when git says both ci branches hold HEAD, the box rehearsal is not run again and the ship says so; when they hold
another commit, or git will not say, it rehearses exactly as before.

DRIVEN: the real ship_when_green.ship() over a fake git and GitHub, with a box rehearsal that records whether it ran.
RED_PROOF below.
"""
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import ship_when_green as SW  # noqa: E402
from test_a_push_trusts_github_only_for_the_exact_commit import SHA, _all_green  # noqa: E402

OTHER = "f" * 40


def _ship(listed_sha, ls_rc=0):
    calls, said, box = [], [], []
    listed = "%s\trefs/heads/ci/claude-v3862\n%s\trefs/heads/ci/proof-keys-v3862\n" % (listed_sha, listed_sha)

    def run(argv, **kw):
        calls.append(list(argv))
        if argv[:2] == ["git", "ls-remote"]:
            return subprocess.CompletedProcess(argv, ls_rc, listed if ls_rc == 0 else "", "")
        if argv[:3] == ["git", "status", "--porcelain"]:
            return subprocess.CompletedProcess(argv, 0, "", "")
        if argv[:3] == ["git", "rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(argv, 0, SHA + "\n", "")
        return subprocess.CompletedProcess(argv, 0, "", "")
    rc = SW.ship("v3862", run=run, fetch=lambda sha: _all_green(), sleep=lambda s: None, clock=lambda: 0.0,
                 say=said.append, preflight=False, version_check=lambda v, say: 0,
                 box_rehearse=lambda say: (box.append(1), 0)[1])
    return rc, box, said


class ARelaunchDoesNotReRehearseTheBox(unittest.TestCase):

    def test_baseline_a_fresh_ship_rehearses_the_box(self):
        rc, box, said = _ship(OTHER)
        self.assertEqual(rc, 0, said)
        self.assertEqual(box, [1], "PREMISE: a ship whose ci branches hold another commit did not rehearse the box")

    def test_a_relaunch_on_the_held_commit_skips_it_and_says_so(self):
        """* THE POINT - v3900's relaunch, 11-12 08:02"""
        rc, box, said = _ship(SHA)
        self.assertEqual(rc, 0, said)
        self.assertEqual(box, [], "the box was rehearsed again for a ci push that is not made")
        self.assertTrue(any("box rehearsal" in l and "not run again" in l for l in said), said)

    def test_git_that_will_not_say_rehearses_as_before(self):
        rc, box, said = _ship(SHA, ls_rc=128)
        self.assertEqual(box, [1], "an unread remote skipped the box rehearsal on a guess")


RED_PROOF = [
    {"why": "REG-3776 - a relaunch on a commit the ci branches hold re-runs the box rehearsal again (~7 min)",
     "file": "tv/ship_when_green.py",
     "find": "    if box_rehearse and _ci_branches_hold(run, remote, version, sha) is True:\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "REG-3776 - a remote git would not read is taken as holding the commit",
     "file": "tv/ship_when_green.py",
     "find": "        if getattr(have, \"returncode\", 1) != 0:\n            return None\n        at = dict(",
     "replace": "        if getattr(have, \"returncode\", 1) != 0:\n            return True\n        at = dict(",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
