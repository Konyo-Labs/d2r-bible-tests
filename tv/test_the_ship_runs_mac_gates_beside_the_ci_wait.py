# -*- coding: utf-8 -*-
"""REG-3646 - THE SHIP RUNS LOCAL GATES BESIDE (AND BEFORE) THE CI WAIT, AND A RED STOPS IT AT ONCE.

A box rehearsal red blocks the ci/ push. A Mac-readiness red (attempt 8: no playwright in
the worktree) is reported in seconds, before sitting on CI. A Mac rehearsal red is reported
immediately while CI may still be running. The main push still goes through hooks/pre-push:
never --no-verify, never a force push to main.
"""
import os
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import ship_when_green as SW  # noqa: E402


def _git_ok(run):
    """A tiny stand-in: tree clean, HEAD is 40 hex, fast-forward."""
    def git(cmd, **kw):
        import subprocess
        if cmd[:2] == ["git", "status"] or (len(cmd) > 2 and cmd[2] == "status"):
            return subprocess.CompletedProcess(cmd, 0, "", "")
        # ship uses _git(run, "status", "--porcelain") -> run(["git", "status", ...])
        joined = " ".join(cmd) if isinstance(cmd, (list, tuple)) else str(cmd)
        if "rev-parse" in joined and "HEAD" in joined:
            return subprocess.CompletedProcess(cmd, 0, "a" * 40, "")
        if "merge-base" in joined:
            return subprocess.CompletedProcess(cmd, 0, "", "")
        if "fetch" in joined or "ls-remote" in joined:
            return subprocess.CompletedProcess(cmd, 0, "", "")
        if "push" in joined:
            return subprocess.CompletedProcess(cmd, 0, "", "")
        return subprocess.CompletedProcess(cmd, 0, "", "")
    return git


class TheLawHolds(unittest.TestCase):
    def test_a_red_box_rehearsal_does_not_push_ci(self):
        pushes = []

        def run(cmd, **kw):
            import subprocess
            if cmd and cmd[0] == "git" and "push" in cmd:
                pushes.append(cmd)
                return subprocess.CompletedProcess(cmd, 0, "", "")
            return _git_ok(run)(cmd, **kw)

        said = []
        rc = SW.ship("v3894", run=run, fetch=lambda s: [], sleep=lambda s: None, clock=lambda: 0.0,
                     say=said.append, wait_s=10, preflight=False, version_check=lambda v, say: 0,
                     box_rehearse=lambda say: 1, mac_ready=False, mac_rehearse=False)
        self.assertEqual(rc, 1)
        self.assertFalse(pushes, "a red rehearsal must not push ci/ or main")
        self.assertTrue(any("box rehearsal" in s for s in said), said)

    def test_a_red_mac_ready_does_not_wait_on_ci(self):
        pushes = []
        fetches = []

        def run(cmd, **kw):
            import subprocess
            if cmd and cmd[0] == "git" and "push" in cmd:
                pushes.append(list(cmd))
                return subprocess.CompletedProcess(cmd, 0, "", "")
            return _git_ok(run)(cmd, **kw)

        said = []
        rc = SW.ship("v3894", run=run, fetch=lambda s: fetches.append(s) or [], sleep=lambda s: None,
                     clock=lambda: 0.0, say=said.append, wait_s=10, preflight=False,
                     version_check=lambda v, say: 0,
                     box_rehearse=False, mac_ready=lambda say: 1, mac_rehearse=False)
        self.assertEqual(rc, 1)
        # readiness runs after the ci/ push (the worktree must be the one that was pushed) but
        # before the wait: fetch must not have been asked, and main must not be pushed.
        self.assertFalse(fetches, "must not sit on CI after a red readiness check")
        self.assertFalse(any("HEAD:main" in p for p in pushes), pushes)
        self.assertTrue(any("readiness" in s.lower() or "Mac readiness" in s for s in said), said)

    def test_a_red_rehearsal_is_reported_during_the_ci_wait(self):
        said = []
        n = {"t": 0}

        def clock():
            n["t"] += 1
            return float(n["t"])

        def run(cmd, **kw):
            import subprocess
            return _git_ok(run)(cmd, **kw)

        # rehearsal reports red immediately; fetch would return 'not yet' forever
        rc = SW.ship("v3894", run=run, fetch=lambda s: [], sleep=lambda s: None, clock=clock,
                     say=said.append, wait_s=10, preflight=False, version_check=lambda v, say: 0,
                     box_rehearse=False, mac_ready=False,
                     mac_rehearse=lambda say: 1)
        self.assertEqual(rc, 1)
        self.assertTrue(any("rehearsal" in s.lower() for s in said), said)
        self.assertFalse(any("vouches" in s for s in said), said)

    def test_the_main_push_never_uses_no_verify_or_force(self):
        with open(os.path.join(HERE, "ship_when_green.py"), encoding="utf-8") as fh:
            src = fh.read()
        # the main push argv is HEAD:main through hooks/pre-push; --no-verify appears only in
        # comments that forbid it; force-plus is used for the ci/ branches, never for main.
        self.assertIn('push", remote, "HEAD:main"', src)
        self.assertIn("core.hooksPath=hooks", src)
        self.assertNotIn("+HEAD:main", src)
        self.assertNotIn(' "--no-verify"', src)
        self.assertNotIn("'--no-verify'", src)


if __name__ == "__main__":
    unittest.main()
