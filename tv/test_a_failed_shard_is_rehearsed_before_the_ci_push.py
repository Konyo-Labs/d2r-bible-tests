# -*- coding: utf-8 -*-
"""REG-3647 - A SHARD THAT FAILED IN THE LAST N ROUNDS IS REHEARSED BEFORE THE CI PUSH.

Attempt 9 paid a full GitHub round because agent-suite (2) went red on
test_the_planner_spinner_stays_under_the_cursor after 18m41s, and the box
rehearsal had not run that shard's tests. The box rehearsal now runs the
exact failed tests (and the full shard set when the failure was a cut-off)
from the flake ledger plus shard_history, so a known-bad shard is tested
locally first.
"""
import os
import sys
import shutil
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import shard_watch as SHW  # noqa: E402
import preship as P  # noqa: E402


ATTEMPT9 = "test_the_planner_spinner_stays_under_the_cursor"


class TheLawHolds(unittest.TestCase):
    def test_attempt_9_is_in_the_history(self):
        owed = SHW.owed_shards()
        names = [j.get("name") for j in owed]
        self.assertIn("agent-suite (2)", names, owed)
        self.assertIn(ATTEMPT9, SHW.owed_tests())

    def test_failed_shards_is_in_the_box_rehearsal(self):
        self.assertIn("failed_shards", P.BOX_ORDER)
        self.assertLess(P.BOX_ORDER.index("agreement"), P.BOX_ORDER.index("failed_shards"),
                        "a known-bad shard runs after the cheap pins, before the long gates")
        self.assertIn("failed_shards", P.catalog())

    def test_the_box_rehearsal_runs_the_failed_tests_first(self):
        root = tempfile.mkdtemp(prefix="shard-rehearse-")
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        os.makedirs(os.path.join(root, "tv"), exist_ok=True)
        data = {"rounds": [{"run": 1, "sha": "abc", "when": "2026-11-10", "jobs": [
            {"name": "agent-suite (2)", "k": 2, "n": 5, "class": "real",
             "failed": [ATTEMPT9], "why": "named test failure"}]}],
                "flags": []}
        SHW.save(data, root)
        plan = SHW.rehearsal_cmd(root=root)
        self.assertEqual(plan["tests"], [ATTEMPT9])
        self.assertEqual(plan["shards"], [], "a real failure rehearses the named tests, not the whole 18-min shard")

        calls = []

        def fake_run(cmd, cwd, timeout, env=None):
            calls.append(list(cmd))
            import subprocess
            return subprocess.CompletedProcess(cmd, 0, "ok", "")

        with mock.patch.object(P, "_run", side_effect=fake_run):
            # Point the history at the temp root; the check uses shard_watch.load(root).
            code, say = P.check_failed_shards(root, timeout=30)
        self.assertEqual(code, 0, say)
        self.assertTrue(calls, say)
        only = [c for c in calls if "--only" in c]
        self.assertTrue(only, calls)
        self.assertIn(ATTEMPT9, only[0])
        self.assertNotIn("--shard", " ".join(" ".join(map(str, c)) for c in calls))

    def test_a_cutoff_shard_is_rehearsed_as_the_same_slice(self):
        root = tempfile.mkdtemp(prefix="shard-cutoff-")
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        os.makedirs(os.path.join(root, "tv"), exist_ok=True)
        SHW.save({"rounds": [{"run": 2, "sha": "def", "when": "2026-11-10", "jobs": [
            {"name": "agent-suite (2)", "k": 2, "n": 5, "class": "cutoff",
             "failed": [], "why": "runner cut-off"}]}], "flags": []}, root)
        plan = SHW.rehearsal_cmd(root=root)
        self.assertEqual(plan["shards"], [(2, 5)])
        calls = []

        def fake_run(cmd, cwd, timeout, env=None):
            calls.append(list(cmd))
            import subprocess
            return subprocess.CompletedProcess(cmd, 0, "ok", "")

        with mock.patch.object(P, "_run", side_effect=fake_run):
            code, say = P.check_failed_shards(root, timeout=30)
        self.assertEqual(code, 0, say)
        sharded = [c for c in calls if "--shard" in c]
        self.assertTrue(sharded, calls)
        i = sharded[0].index("--shard")
        self.assertEqual(str(sharded[0][i + 1]), "2/5")


class TheProofsNameOnePlace(unittest.TestCase):
    def test_each_find_matches_once(self):
        for p in RED_PROOF:
            with open(os.path.join(P.REPO, p["file"]), encoding="utf-8") as fh:
                blob = fh.read()
            self.assertEqual(blob.count(p["find"]), p["matches"], p["why"])

    def test_each_proof_drops_the_check_from_the_box_order(self):
        with open(os.path.join(HERE, "preship.py"), encoding="utf-8") as fh:
            src = fh.read()
        for p in RED_PROOF:
            after = src.replace(p["find"], p["replace"], 1)
            self.assertNotIn(p["find"], after)
            start = after.find("BOX_ORDER")
            end = after.find("READY_ORDER")
            self.assertNotIn('"failed_shards"', after[start:end], p["why"])



RED_PROOF = [
    {"why": "REG-3647 - failed_shards drops out of the box rehearsal order",
     "file": "tv/preship.py",
     "find": "    \"failed_shards\", \"integrity\",\n",
     "replace": "    \"integrity\",\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main()
