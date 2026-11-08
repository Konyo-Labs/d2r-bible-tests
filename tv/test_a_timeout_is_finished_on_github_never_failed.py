# -*- coding: utf-8 -*-
"""v3881 (REG-3387) - A PROOF ROUND CUT ONLY BY ITS BOUND IS FINISHED ON GITHUB, NEVER HANDED BACK AS A FAILED ROUND.

His words 2026-11-07: "red is logical but timeout? ... something needs to be done for rounds not being pushed through because
a shard was timed out instead of red", and of the finishing job: "build this regardless ... as an extra layer".
MEASURED on v3879 (run 42387199487): shard 5 owed 6 proofs its 1500 s cap cut (21 of 27 banked) beside shard 16's red law;
both were re-run by hand. .github/workflows/proof-keys-finish.yml now starts the moment a proof-keys round completes red, reads
that round's census, and asks tv/proof_shard.finish_plan: only cut proofs -> re-run the failed jobs (a re-run serves what was
banked and proves only the cut); cut shards beside a red one -> re-run one cut job (GitHub re-runs nothing on a run in
progress); a red law, a shard with no store, a third attempt -> nothing. It never re-runs a red law, it runs the DEFAULT
branch's code (no ci/ code with an actions: write token), and the ship waits on a round the finisher already re-ran.
RED_PROOF below. [[the-unjoined-end]] [[regression-guard]]
"""
import io
import json
import os
import re
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

import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()   # v3881 pre-flight - its mkdtemp scratch is collected (test_a_test_run_leaves_no_scratch_dirs)
import proof_shard as PS  # noqa: E402

ROOT = os.path.dirname(HERE)
WF = os.path.join(ROOT, ".github", "workflows")
T = PS.TIMEOUT


def _wf(name):
    return io.open(os.path.join(WF, name), encoding="utf-8").read()


def _code(text):
    return "\n".join(l for l in text.split("\n") if not l.lstrip().startswith("#"))


def _block(text, head, nxt):
    """the text between a top-level `head` line and the next top-level `nxt` line - both anchors must be there, once.
    NO yaml: TestNoSuiteImportsSomethingCIDoesNotHave bans it outright (GitHub's agent suite does not install PyYAML -
    v3881's round went red on exactly this). The workflow is read as text, every anchor counted."""
    assert text.count("\n" + head + "\n") == 1, "%r is not one top-level line" % head
    i = text.index("\n" + head + "\n") + len(head) + 2
    j = text.index("\n" + nxt, i)
    return text[i:j]


CUT5 = [["safety", i, T, "cut at its bound", 5] for i in range(21, 27)]
RED16 = [["war", 22, "UNPROVABLE", "red untampered", 16]]


class TheFinishPlan(unittest.TestCase):

    def test_only_cut_proofs_re_run_the_failed_jobs(self):
        p = PS.finish_plan({"cut": CUT5, "fix": [], "lost": [], "missing": []}, 1)
        self.assertEqual((p["action"], p["shards"]), ("rerun-failed", ["5"]), p)

    def test_v3879_cut_beside_a_red_re_runs_only_the_cut_shard(self):
        """* THE POINT: v3879's round - shard 5 finished on GitHub, shard 16's red left for a human"""
        p = PS.finish_plan({"cut": CUT5, "fix": RED16, "lost": [], "missing": []}, 1)
        self.assertEqual((p["action"], p["shards"]), ("rerun-jobs", ["5"]), p)

    def test_a_red_alone_is_never_re_run(self):
        for tot in ({"cut": [], "fix": RED16, "lost": [], "missing": []},
                    {"cut": [["war", 1, T, "cut", 16]], "fix": RED16, "lost": [], "missing": []}):
            p = PS.finish_plan(tot, 1)
            self.assertEqual(p["action"], "none", "a red shard was re-run: %r" % p)

    def test_unknown_is_never_re_run(self):
        self.assertEqual(PS.finish_plan({"cut": [], "fix": [], "lost": [7], "missing": []}, 1)["action"], "none")
        self.assertEqual(PS.finish_plan(None, 1)["action"], "none")
        self.assertEqual(PS.finish_plan({"cut": CUT5, "fix": [], "lost": [], "missing": []}, None)["action"], "none")

    def test_a_round_is_finished_at_most_twice(self):
        tot = {"cut": CUT5, "fix": [], "lost": [], "missing": []}
        self.assertEqual(PS.finish_plan(tot, PS.FINISH_MAX_ATTEMPT)["action"], "rerun-failed")
        self.assertEqual(PS.finish_plan(tot, PS.FINISH_MAX_ATTEMPT + 1)["action"], "none", "the finisher loops")

    def test_the_cli_the_workflow_calls_writes_the_plan(self):
        d = tempfile.mkdtemp(prefix="tvd_finish_")
        c, out = os.path.join(d, "census.json"), os.path.join(d, "plan.json")
        with io.open(c, "w", encoding="utf-8") as fh:
            json.dump({"cut": CUT5, "fix": RED16, "lost": [], "missing": []}, fh)
        r = subprocess.run([sys.executable, os.path.join(HERE, "proof_shard.py"), "--finish-plan", c, "--attempt", "1",
                            "--out", out], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr[-400:])
        with io.open(out, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["action"], "rerun-jobs")
        r = subprocess.run([sys.executable, os.path.join(HERE, "proof_shard.py"), "--finish-plan",
                            os.path.join(d, "absent.json"), "--attempt", "1"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(json.loads(r.stdout)["action"], "none", "no census read as something to re-run")


class TheWorkflowIsJoined(unittest.TestCase):

    def setUp(self):
        self.text = _code(_wf("proof-keys-finish.yml"))
        self.on = _block(self.text, "on:", "permissions:")
        self.job = self.text[self.text.index("\n  finish:\n"):]

    def test_it_listens_to_the_shards_workflow_by_its_exact_name(self):
        """the joint: a name that is not the shards workflow's own `name:` never fires, and nothing says so"""
        shards = re.search(r"^name: (.+)$", _wf("proof-keys-shards.yml"), re.M).group(1).strip()
        wf = re.findall(r"^    workflows: \[(.*)\]$", self.on, re.M)
        self.assertEqual(len(wf), 1, self.on)
        self.assertEqual([w.strip().strip('"') for w in wf[0].split(",")], [shards])
        self.assertEqual(re.findall(r"^    types: \[(.*)\]$", self.on, re.M), ["completed"])
        self.assertIsNone(re.search(r"^  push:", self.on, re.M), "the finisher must not run on a push (it would run ci/ code)")

    def test_it_runs_only_on_a_red_round_and_at_most_twice(self):
        m = re.search(r"^    if: \$\{\{ (.+) \}\}$", self.job, re.M)
        self.assertTrue(m, "the finish job has no one-line if:")
        cond = m.group(1)
        self.assertIn("github.event.workflow_run.conclusion == 'failure'", cond)
        m = re.search(r"run_attempt <= (\d+)", cond)
        self.assertTrue(m, cond)
        self.assertEqual(int(m.group(1)), PS.FINISH_MAX_ATTEMPT, "the workflow and finish_plan bound attempts apart")

    def test_no_ci_code_runs_with_the_write_token(self):
        self.assertEqual(_block(self.text, "permissions:", "jobs:").strip(), "contents: read")
        jp = self.job[self.job.index("\n    permissions:\n"):self.job.index("\n    env:\n")]
        self.assertEqual(sorted(l.strip() for l in jp.strip().split("\n")[1:]), ["actions: write", "contents: read"])
        steps = self.job[self.job.index("\n    steps:\n"):]
        co = [m.start() for m in re.finditer(r"^      - uses: actions/checkout", steps, re.M)]
        self.assertEqual(len(co), 1)
        nxt = steps.find("\n      - ", co[0] + 1)
        self.assertNotIn("with:", steps[co[0]:nxt if nxt > 0 else None],
                         "the finisher checks out the triggering ci/ commit - its code would hold actions: write")

    def test_it_reads_the_census_the_fan_in_keeps_and_acts_on_the_plan(self):
        fan_in = _code(_wf("proof-keys-shards.yml"))
        self.assertIn("name: proof-census-${{ github.sha }}", fan_in, "the fan-in's census artifact moved")
        code = _code(_wf("proof-keys-finish.yml"))
        self.assertIn('-n "proof-census-$SHA"', code)
        self.assertIn('python3 tv/proof_shard.py --finish-plan census/census.json --attempt "$ATTEMPT" --out plan.json', code)
        i, j = code.index('if [ "$act" = "rerun-failed" ]; then'), code.index('gh run rerun "$RID" --failed')
        k, m = code.index('elif [ "$act" = "rerun-jobs" ]; then'), code.index('gh run rerun --job "$jid"')
        self.assertTrue(i < j < k < m, "a re-run is not under the plan's own action")
        self.assertEqual(code.count("gh run rerun"), 2, "a re-run outside the plan's two actions")


class TheShipWaitsOnTheFinisher(unittest.TestCase):

    def _makeup(self, status):
        import ship_when_green as SW
        census = {"cut": CUT5, "fix": [], "lost": [], "missing": []}
        calls, said = [], []

        def run(cmd, **kw):
            calls.append(list(cmd))
            if cmd[:3] == ["gh", "run", "download"]:
                with io.open(os.path.join(cmd[cmd.index("-D") + 1], "census.json"), "w", encoding="utf-8") as fh:
                    json.dump(census, fh)
                return subprocess.CompletedProcess(cmd, 0, "", "")
            if cmd[:3] == ["gh", "run", "rerun"]:
                return subprocess.CompletedProcess(cmd, 1, "", "This workflow is already running")
            if cmd[:3] == ["gh", "run", "view"] and "status" in cmd:
                return subprocess.CompletedProcess(cmd, 0, json.dumps({"status": status}), "")
            return subprocess.CompletedProcess(cmd, 0, "", "")
        runs = [{"workflowName": SW.CV.REQUIRED[3], "headSha": "abc123", "status": "completed", "conclusion": "failure",
                 "createdAt": "2026-11-07T16:00:00Z", "databaseId": 4242}]
        made = {}
        got = SW.makeup("abc123", runs, run, said.append, made, lambda: 5.0, tmp=tempfile.mkdtemp(prefix="tvd_mk_"))
        return got, made, said

    def test_a_round_the_finisher_already_re_ran_is_waited_on(self):
        got, made, said = self._makeup("in_progress")
        self.assertTrue(got, said)
        self.assertEqual(made.get(4242), 5.0)
        self.assertTrue(any("REG-3387" in s for s in said), said)

    def test_baseline_a_refused_re_run_of_a_still_red_round_stops(self):
        got, made, said = self._makeup("completed")
        self.assertFalse(got)
        self.assertIsNone(made.get(4242))
        self.assertTrue(any("REFUSED" in s for s in said), said)


RED_PROOF = [
    {"why": "REG-3387 - the finisher listens for a workflow name that does not exist (it never fires, silently)",
     "file": ".github/workflows/proof-keys-finish.yml", "find": '    workflows: ["proof-keys shards (ci/proof-keys-* only)"]\n',
     "replace": '    workflows: ["proof-keys shards"]\n', "matches": 1},
    {"why": "REG-3387 - the finisher runs the triggering ci/ commit's code with an actions: write token",
     "file": ".github/workflows/proof-keys-finish.yml",
     "find": "      - uses: actions/checkout@v4\n      - name: The round's census",
     "replace": "      - uses: actions/checkout@v4\n        with:\n          ref: ${{ env.SHA }}\n      - name: The round's census",
     "matches": 1},
    {"why": "REG-3387 - the finisher loops on a round (no attempt bound shared with finish_plan)",
     "file": ".github/workflows/proof-keys-finish.yml", "find": "github.event.workflow_run.run_attempt <= 2 }}",
     "replace": "github.event.workflow_run.run_attempt <= 9 }}", "matches": 1},
    {"why": "REG-3387 - a round with a red law is re-run whole (a red re-run until it greens)",
     "file": "tv/proof_shard.py", "find": "    due, why = makeup_due(tot)\n    if due:\n        sh = sorted(",
     "replace": "    due, why = makeup_due(tot)\n    if due or tot.get('fix'):\n        sh = sorted(", "matches": 1},
    {"why": "REG-3387 - the ship stops on a round GitHub's finisher is already re-running",
     "file": "tv/ship_when_green.py", "find": "            if running_again(rid, run):",
     "replace": "            if False:", "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
