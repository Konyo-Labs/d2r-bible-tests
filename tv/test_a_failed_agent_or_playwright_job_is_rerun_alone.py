# -*- coding: utf-8 -*-
"""REG-3645 - A FLAKY OR RUNNER-KILLED AGENT / PLAYWRIGHT JOB IS RE-RUN ALONE, NOT THE WHOLE ROUND.

REG-3270 already re-runs only the failed proof-keys shards (`gh run rerun --failed`).
The same shape now covers the agent-tests and Playwright workflows: a known flake, or a
job the runner cancelled, is made up once; a genuine new red is left for a human.
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
import ci_verdict as CV  # noqa: E402
import flake_ledger as FL  # noqa: E402


class _GH:
    def __init__(self, jobs, logs=None, rerun_ok=True):
        self.jobs = jobs
        self.logs = logs or {}
        self.rerun_ok = rerun_ok
        self.calls = []

    def __call__(self, cmd, **kw):
        self.calls.append(cmd)
        import json
        import subprocess
        if cmd[:3] == ["gh", "run", "view"]:
            return subprocess.CompletedProcess(cmd, 0, json.dumps({"jobs": self.jobs}), "")
        if cmd[:2] == ["gh", "api"] and "/logs" in cmd[2]:
            jid = cmd[2].rsplit("/", 2)[-2] if False else cmd[2].split("/jobs/")[-1].split("/")[0]
            return subprocess.CompletedProcess(cmd, 0, self.logs.get(int(jid) if jid.isdigit() else jid, ""), "")
        if cmd[:3] == ["gh", "run", "rerun"]:
            return subprocess.CompletedProcess(cmd, 0 if self.rerun_ok else 1, "", "" if self.rerun_ok else "no")
        return subprocess.CompletedProcess(cmd, 1, "", "unexpected")


def _run(workflow, rid=11, conclusion="failure"):
    return {"workflowName": workflow, "headSha": "a" * 40, "databaseId": rid,
            "status": "completed", "conclusion": conclusion, "createdAt": "2026-11-10T00:00:00Z"}


class TheLawHolds(unittest.TestCase):
    def test_proof_keys_makeup_still_uses_rerun_failed(self):
        """REG-3270 is unchanged: the make-up command is `gh run rerun --failed`, never a full rerun."""
        src = open(os.path.join(HERE, "ship_when_green.py"), encoding="utf-8").read()
        self.assertIn('["gh", "run", "rerun", str(rid), "--failed"', src)
        self.assertIn("REG-3270", src)

    def test_a_flaky_agent_job_is_rerun_failed_once(self):
        sha = "a" * 40
        wf = CV.REQUIRED[0]
        jobs = [{"name": "agent-suite (3)", "databaseId": 77, "conclusion": "failure"}]
        gh = _GH(jobs, logs={77: "flake"})
        ledger = {"nClean": 3, "entries": {"agent-suite (3)": {"fails": 1, "cleans": 0}}}
        made, said = {}, []
        with mock.patch.object(FL, "load", return_value=ledger):
            ok = SW.suite_makeup(sha, [_run(wf)], gh, said.append, made, clock=lambda: 1.0)
        self.assertTrue(ok, said)
        reruns = [c for c in gh.calls if c[:3] == ["gh", "run", "rerun"]]
        self.assertEqual(len(reruns), 1, reruns)
        self.assertIn("--failed", reruns[0])
        self.assertNotIn("+HEAD:main", str(gh.calls))

    def test_a_genuine_red_is_not_made_up(self):
        sha = "a" * 40
        wf = CV.REQUIRED[1]
        jobs = [{"name": "shard 2/10", "databaseId": 88, "conclusion": "failure"}]
        gh = _GH(jobs, logs={88: "Error: expect(page).toHaveURL failed"})
        made, said = {}, []
        with mock.patch.object(FL, "load", return_value={"nClean": 3, "entries": {}}):
            ok = SW.suite_makeup(sha, [_run(wf)], gh, said.append, made, clock=lambda: 1.0)
        self.assertFalse(ok, said)
        self.assertTrue(any("not made up" in s for s in said), said)
        self.assertFalse(any(c[:3] == ["gh", "run", "rerun"] for c in gh.calls))


if __name__ == "__main__":
    unittest.main()
