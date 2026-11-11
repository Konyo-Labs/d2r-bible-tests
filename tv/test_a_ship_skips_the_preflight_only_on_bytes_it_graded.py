# -*- coding: utf-8 -*-
"""REG-3681 (card #200 guard 4) - A SHIP SKIPS THE PRE-FLIGHT ONLY ON BYTES A PRE-FLIGHT GRADED.

MEASURED 2026-11-11, v3895 round 1: the pre-flight found four faults, they were fixed in a new commit, and the ship was
launched with --no-preflight on that commit - bytes no pre-flight had seen. GitHub spent a 55-minute round finding a law
already red untampered and two red-proofs whose tampers did not parse; the pre-flight runs every non-browser law and proves
the changed ones in minutes. Now a FULL pre-flight that comes back green on a clean tree records the commit (git's common
dir, tv/preflight.py record_green), and --no-preflight is honoured only for a recorded commit or when both ci branches
already point at HEAD (re-attaching to a round GitHub is grading). Anything git will not say refuses.

DRIVEN with a fake `run` (no git, no network) and a throwaway ledger. RED_PROOF below.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import preflight as PF  # noqa: E402
import ship_when_green as SW  # noqa: E402

HEAD = "a" * 40
OTHER = "b" * 40


def _run(head=HEAD, ci=(None, None), status="", head_rc=0, ls_rc=0):
    def run(cmd, *a, **k):
        args = cmd[1:]
        if args[:2] == ["rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(cmd, head_rc, head + "\n" if head_rc == 0 else "", "")
        if args[:1] == ["ls-remote"]:
            out = "".join("%s\trefs/heads/%s\n" % (s, n) for s, n in zip(ci, ("ci/claude-v9", "ci/proof-keys-v9")) if s)
            return subprocess.CompletedProcess(cmd, ls_rc, out, "")
        if args[:1] == ["status"]:
            return subprocess.CompletedProcess(cmd, 0, status, "")
        raise AssertionError("an unexpected git call: %r" % (cmd,))
    return run


class TheSkipIsHonouredOnlyOnGradedBytes(unittest.TestCase):
    def test_a_launch_on_bytes_no_preflight_graded_is_refused(self):
        why = SW.preflight_skip_refusal("v9", run=_run(), green=set())
        self.assertIsNotNone(why, "--no-preflight was honoured on bytes no pre-flight graded (v3895 round 1)")
        self.assertIn("--no-preflight refused", why)

    def test_a_commit_graded_green_may_skip(self):
        self.assertIsNone(SW.preflight_skip_refusal("v9", run=_run(), green={HEAD}))

    def test_a_green_for_another_commit_does_not_count(self):
        self.assertIsNotNone(SW.preflight_skip_refusal("v9", run=_run(), green={OTHER}))

    def test_re_attaching_to_a_round_github_is_grading_may_skip(self):
        self.assertIsNone(SW.preflight_skip_refusal("v9", run=_run(ci=(HEAD, HEAD)), green=set()))
        self.assertIsNotNone(SW.preflight_skip_refusal("v9", run=_run(ci=(HEAD, OTHER)), green=set()),
                             "one ci branch at HEAD is not a round grading these bytes")

    def test_a_commit_git_will_not_name_refuses(self):
        self.assertIsNotNone(SW.preflight_skip_refusal("v9", run=_run(head_rc=1), green={HEAD}))


class TheGreenIsRecordedOnlyForACleanTree(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="preflight-green-")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.path = os.path.join(self.d, PF.GREEN_LEDGER)

    def test_a_clean_tree_is_recorded_and_read_back(self):
        self.assertEqual(PF.record_green(run=_run(), path=self.path, version="v9", now=1), HEAD)
        self.assertEqual(PF.green_shas(path=self.path), {HEAD})

    def test_a_tracked_edit_is_never_recorded(self):
        self.assertIsNone(PF.record_green(run=_run(status=" M tv/x.py\n"), path=self.path, version="v9", now=1))
        self.assertEqual(PF.green_shas(path=self.path), set(), "a pre-flight of a dirty tree vouched for the commit")


RED_PROOF = [
    {"why": "REG-3681 - --no-preflight is honoured on any bytes again (v3895 round 1's 55-minute round)",
     "file": "tv/ship_when_green.py",
     "find": "    have = green if green is not None else _pf.green_shas()\n    if sha in have:\n        return None\n",
     "replace": "    have = green if green is not None else _pf.green_shas()\n    if True:\n        return None\n",
     "matches": 1},
    {"why": "REG-3681 - a pre-flight of a dirty tree is recorded as a green for the commit",
     "file": "tv/preflight.py",
     "find": "    if h.returncode != 0 or not sha or st.returncode != 0 or (st.stdout or \"\").strip():\n        return None\n",
     "replace": "    if h.returncode != 0 or not sha or st.returncode != 0:\n        return None\n",
     "matches": 1},
    {"why": "REG-3681 - one ci branch at HEAD reads as a round grading these bytes",
     "file": "tv/ship_when_green.py",
     "find": "    if ls.returncode == 0 and len(heads) == 2 and all(x == sha for x in heads):\n",
     "replace": "    if ls.returncode == 0 and any(x == sha for x in heads):\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
