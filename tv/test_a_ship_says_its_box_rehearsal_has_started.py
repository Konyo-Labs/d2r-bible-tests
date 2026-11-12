# -*- coding: utf-8 -*-
"""v3902 (REG-3779) - THE SHIP SAYS ITS BOX REHEARSAL HAS STARTED, NOT ONLY THAT IT ENDED.

MEASURED 11-12 08:02-08:09: v3900's relaunched ship wrote nothing at all to ship_v3900.log for ~6 minutes - the box
rehearsal prints its table only when it ends - and a log that stays at 0 bytes reads exactly like a ship that hung (I
checked its process tree to tell them apart). The ship now says the rehearsal is running, for which commit, before it runs.

DRIVEN: the real ship_when_green.ship() over a fake git and GitHub, with a box rehearsal that records what had been said
the moment it was called. RED_PROOF below.
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


def _run(argv, **kw):
    if argv[:2] == ["git", "ls-remote"]:
        return subprocess.CompletedProcess(argv, 0, "", "")         # the ci branches hold nothing yet: a fresh ship
    if argv[:3] == ["git", "status", "--porcelain"]:
        return subprocess.CompletedProcess(argv, 0, "", "")
    if argv[:3] == ["git", "rev-parse", "HEAD"]:
        return subprocess.CompletedProcess(argv, 0, SHA + "\n", "")
    return subprocess.CompletedProcess(argv, 0, "", "")


class AShipSaysItsBoxRehearsalHasStarted(unittest.TestCase):

    def test_the_start_is_said_before_the_rehearsal_runs(self):
        """* THE POINT - 6 silent minutes in v3900's log"""
        said, seen = [], []
        rc = SW.ship("v3862", run=_run, fetch=lambda sha: _all_green(), sleep=lambda s: None, clock=lambda: 0.0,
                     say=said.append, preflight=False, version_check=lambda v, say: 0,
                     box_rehearse=lambda say: (seen.append(list(said)), 0)[1])
        self.assertEqual(rc, 0, said)
        self.assertEqual(len(seen), 1, "PREMISE: the box rehearsal did not run")
        self.assertTrue(any("box rehearsal running for %s" % SHA[:9] in l for l in seen[0]),
                        "nothing was said before the box rehearsal ran: %r" % seen[0])


RED_PROOF = [
    {"why": "REG-3779 - the box rehearsal runs silent again until its table prints (6 minutes of an empty log)",
     "file": "tv/ship_when_green.py",
     "find": "        say(\"ship: box rehearsal running for %s - its table prints when it ends (several minutes)\" % sha[:9])\n",
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
