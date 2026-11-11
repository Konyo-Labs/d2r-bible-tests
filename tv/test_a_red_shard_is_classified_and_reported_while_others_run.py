# -*- coding: utf-8 -*-
"""REG-3648 - A RED SHARD IS CLASSIFIED AND REPORTED THE MOMENT IT FINISHES, NOT AFTER THE ROUND.

Attempt 9's agent-suite (2) was a real failure of
test_the_planner_spinner_stays_under_the_cursor (383s left of the 1500s
ceiling — not a cut-off). VERDICT then failed as UNKNOWN/cut-off after the
whole round. The engine now watches per-job status during the CI wait: a
real red is reported immediately so the fix can start while other shards
are still running; a flake, cut-off, timeout, or infra kill is auto-rerun
(or queued until the run completes, because GitHub refuses a mid-run rerun).
"""
import json
import os
import subprocess
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
import ship_when_green as SW  # noqa: E402
import ci_verdict as CV  # noqa: E402


ATTEMPT9_LOG = """
THE GATE SET
used 1117s, 383s left of 1500s ceiling
❌ test_the_planner_spinner_stays_under_the_cursor    8.2s  FAILED (failures=1)
AssertionError: 22.0625 not less than 1 : step 1: the Sockets field moved sideways
❌ 1 gate(s) FAILED: test_the_planner_spinner_stays_under_the_cursor
"""

CUTOFF_LOG = """
NO VERDICT — the gate set never reached the end
The operation was canceled
used 1490s, 10s left of 1500s ceiling
"""


class _GH:
    def __init__(self, jobs, logs=None, rerun_ok=True, rerun_err=""):
        self.jobs = jobs
        self.logs = logs or {}
        self.rerun_ok = rerun_ok
        self.rerun_err = rerun_err
        self.calls = []

    def __call__(self, cmd, **kw):
        self.calls.append(cmd)
        if cmd[:3] == ["gh", "run", "view"]:
            return subprocess.CompletedProcess(cmd, 0, json.dumps({"jobs": self.jobs}), "")
        if len(cmd) >= 3 and cmd[0] == "gh" and cmd[1] == "api" and "/logs" in cmd[2]:
            jid = cmd[2].split("/jobs/")[-1].split("/")[0]
            key = int(jid) if jid.isdigit() else jid
            return subprocess.CompletedProcess(cmd, 0, self.logs.get(key, self.logs.get(jid, "")), "")
        if cmd[:3] == ["gh", "run", "rerun"]:
            return subprocess.CompletedProcess(cmd, 0 if self.rerun_ok else 1, "",
                                               "" if self.rerun_ok else (self.rerun_err or "cannot rerun, run is in progress"))
        return subprocess.CompletedProcess(cmd, 1, "", "unexpected")


def _suite(jobs, rid=42810705250, status="in_progress", conclusion=""):
    return {"workflowName": CV.REQUIRED[0], "headSha": "a" * 40, "databaseId": rid,
            "status": status, "conclusion": conclusion, "createdAt": "2026-11-10T00:00:00Z",
            "jobs": jobs}


class TheLawHolds(unittest.TestCase):
    def test_attempt_9_classifies_as_a_real_failure_not_a_cutoff(self):
        job = {"name": "agent-suite (2)", "conclusion": "failure"}
        info = SHW.classify(ATTEMPT9_LOG, job)
        self.assertEqual(info["class"], "real", info)
        self.assertIn("test_the_planner_spinner_stays_under_the_cursor", info["failed"])
        self.assertFalse(SHW.near_ceiling(info), "383s left is not near the 300s warning")

    def test_a_cancelled_job_at_the_ceiling_is_a_cutoff(self):
        job = {"name": "agent-suite (2)", "conclusion": "cancelled"}
        info = SHW.classify(CUTOFF_LOG, job)
        self.assertEqual(info["class"], "cutoff", info)
        self.assertEqual(info["failed"], [])

    def test_a_real_red_is_reported_while_sibling_shards_still_run(self):
        root = tempfile.mkdtemp(prefix="shard-live-")
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        os.makedirs(os.path.join(root, "tv"), exist_ok=True)
        SHW.save({"rounds": [], "flags": []}, root)
        jobs = [
            {"name": "agent-suite (1)", "databaseId": 1, "status": "in_progress", "conclusion": ""},
            {"name": "agent-suite (2)", "databaseId": 2, "status": "completed", "conclusion": "failure"},
            {"name": "agent-suite (3)", "databaseId": 3, "status": "in_progress", "conclusion": ""},
        ]
        gh = _GH(jobs, logs={2: ATTEMPT9_LOG})
        said, seen, made = [], set(), {}
        kind, info = SHW.watch_jobs_live("a" * 40, [_suite(jobs)], gh, said.append, seen, made,
                                         clock=lambda: 1.0, root=root)
        self.assertEqual(kind, "real", (kind, info, said))
        self.assertEqual(info["class"], "real")
        self.assertTrue(any("REAL" in s or "real" in s.lower() for s in said), said)
        self.assertFalse(any(c[:3] == ["gh", "run", "rerun"] for c in gh.calls),
                         "a real failure is not auto-rerun")
        # siblings were still running — we did not wait for the workflow conclusion
        self.assertEqual(_suite(jobs)["status"], "in_progress")

    def test_a_red_seen_from_a_checkout_never_writes_its_tracked_files(self):
        """v3896 (REG-3684) - MEASURED 11-11 ~06:01: the watcher wrote the red slice into the TRACKED shard history and lessons
        of the ship's own tree, and the relaunch on the same commit refused - "the tree is not clean". From a checkout the
        history and the lesson go to the machine ledger (git's common dir); the tracked files stay as committed."""
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        root = tempfile.mkdtemp(prefix="shard-checkout-")
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        os.makedirs(os.path.join(root, "tv"))
        tracked = {"tv/shard_history.json": '{\n  "rounds": [],\n  "flags": []\n}\n',
                   "tv/preship_lessons.json": '{\n  "lessons": []\n}\n'}
        for rel, body in tracked.items():
            with open(os.path.join(root, rel), "w", encoding="utf-8") as fh:
                fh.write(body)
        self.assertEqual(subprocess.run(["git", "init", "-q"], cwd=root, capture_output=True, env=env).returncode, 0)
        subprocess.run(["git", "config", "core.autocrlf", "false"], cwd=root, capture_output=True, env=env)   # REG-3626 pin
        for args in (["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x"]):
            self.assertEqual(subprocess.run(["git"] + args, cwd=root, capture_output=True, env=env).returncode, 0, args)
        jobs = [{"name": "agent-suite (2)", "databaseId": 2, "status": "completed", "conclusion": "failure"}]
        gh = _GH(jobs, logs={2: ATTEMPT9_LOG})
        from unittest import mock
        with mock.patch.dict(os.environ, env, clear=True):
            kind, _info = SHW.watch_jobs_live("a" * 40, [_suite(jobs)], gh, [].append, set(), {}, clock=lambda: 1.0,
                                              root=root)
            local = SHW.local_path(root)
            history = SHW.load(root)
        self.assertEqual(kind, "real", "PREMISE: the planted red was not seen")
        for rel, body in tracked.items():
            with open(os.path.join(root, rel), encoding="utf-8") as fh:
                self.assertEqual(fh.read(), body, "the watcher wrote the TRACKED %s of the ship's own tree" % rel)
        self.assertTrue(local and os.path.isfile(local), "the red slice was recorded nowhere")
        self.assertEqual([j["name"] for r in history["rounds"] for j in r["jobs"]], ["agent-suite (2)"],
                         "the machine's own round is not read back with the tracked history")

    def test_a_cutoff_is_queued_when_github_refuses_a_mid_run_rerun(self):
        root = tempfile.mkdtemp(prefix="shard-cut-")
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        os.makedirs(os.path.join(root, "tv"), exist_ok=True)
        SHW.save({"rounds": [], "flags": []}, root)
        jobs = [
            {"name": "agent-suite (2)", "databaseId": 9, "status": "completed", "conclusion": "cancelled"},
            {"name": "agent-suite (3)", "databaseId": 10, "status": "in_progress", "conclusion": ""},
        ]
        gh = _GH(jobs, logs={9: CUTOFF_LOG}, rerun_ok=False, rerun_err="cannot rerun, run is in progress")
        said, seen, made = [], set(), {}
        kind, info = SHW.watch_jobs_live("a" * 40, [_suite(jobs)], gh, said.append, seen, made,
                                         clock=lambda: 1.0, root=root)
        self.assertEqual(kind, "queued", (kind, info, said))
        self.assertEqual(info["class"], "cutoff")
        reruns = [c for c in gh.calls if c[:3] == ["gh", "run", "rerun"]]
        self.assertEqual(len(reruns), 1, reruns)
        self.assertIn("--failed", reruns[0])
        self.assertNotIn(42810705250, made, "a refused mid-run rerun stays queued for suite_makeup")

    def test_the_wait_loop_calls_the_live_watch_before_the_round_ends(self):
        with open(os.path.join(HERE, "ship_when_green.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("SHW.watch_jobs_live", src)
        self.assertIn("LIVE_POLL_S", src)
        self.assertIn("REG-3648 - classify a shard the moment it goes red", src)
        pos_watch = src.find("SHW.watch_jobs_live")
        pos_green = src.find('verdict == "green"')
        self.assertGreater(pos_watch, 0)
        self.assertGreater(pos_green, pos_watch, "live watch must run before the round is judged green")


class TheProofsNameOnePlace(unittest.TestCase):
    def test_each_find_matches_once(self):
        for p in RED_PROOF:
            blob = open(os.path.join(SW.REPO, p["file"]), encoding="utf-8").read()
            self.assertEqual(blob.count(p["find"]), p["matches"], p["why"])


RED_PROOF = [
    {"why": "REG-3648 - the wait loop no longer watches a shard the moment it goes red",
     "file": "tv/ship_when_green.py",
     "find": "watch_jobs_live",
     "replace": "watch_jobs_never",
     "matches": 1},
    {"why": "v3896 (REG-3684) - the live watcher writes the TRACKED shard history of the ship's own tree again",
     "file": "tv/shard_watch.py",
     "find": "    p = local_path(root) or path(root)\n    os.makedirs(os.path.dirname(p), exist_ok=True)\n",
     "replace": "    p = path(root)\n    os.makedirs(os.path.dirname(p), exist_ok=True)\n",
     "matches": 1},
    {"why": "v3896 (REG-3684) - the watcher's lesson lands in the tracked lessons file of the ship's own tree again",
     "file": "tv/shard_watch.py",
     "find": "                        shard=info[\"name\"], local=True)      # v3896 (REG-3684) - never the tracked lessons of the ship's tree\n",
     "replace": "                        shard=info[\"name\"])\n",
     "matches": 1},
    {"why": "v3896 (REG-3684) - the machine's own rounds are not read back with the tracked history",
     "file": "tv/shard_watch.py",
     "find": "    for src in (tracked or {}, local or {}):\n",
     "replace": "    for src in (tracked or {},):\n",
     "matches": 1}
]

if __name__ == "__main__":
    unittest.main()
