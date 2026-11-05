# -*- coding: utf-8 -*-
"""v3865 (his ruling 2026-11-05: "no way we pass 30$ .. this stops completely and goes back to github if we hit our monthly
cap - 25$ is better") - THE PROOF SHARDS NEVER SPEND PAST THEIR MONTHLY CAP.

Ubicloud runs the shards on 8-core machines (measured that evening: 8 cores, 31 GB, the GitHub-compatible ubuntu-24.04
image) and has no hard spending cap of its own - only alerts. tv/ci_budget.py is the cap: the workflow's budget job sends a
round to Ubicloud only while this month's MEASURED spend + the next round fits PROOF_BUDGET_USD; otherwise, and whenever the
spend cannot be read, GitHub's free runners. Held here:
  * the meter prices only Ubicloud jobs, by vCPU, every started minute rounded UP; one unreadable job makes it UNKNOWN;
  * UNKNOWN, an unset runner, a budget that is not a number, or spend + the next round over the cap -> GitHub's runner;
  * the budget step never fails the run (a failed budget job would stop the shards - not a spending decision);
  * the workflow's shards really take the budget job's runner and provers, and a newer push still cancels them.
Fixtures only - no network. RED_PROOF below.
"""
import io
import datetime
import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import ci_budget as B  # noqa: E402

GH = B.GITHUB_RUNNER
UBI = "ubicloud-standard-8"


def _job(run, label, a, b):
    return {"run_id": run, "labels": [label], "started_at": a, "completed_at": b}


class TheMeterNeverUnderCounts(unittest.TestCase):

    def test_only_ubicloud_jobs_cost_and_by_their_vcpus(self):
        self.assertEqual((B.vcpus(UBI), B.vcpus("ubicloud-standard-2"), B.vcpus("ubicloud-standard-16-arm"),
                          B.vcpus("ubuntu-latest"), B.vcpus("depot-ubuntu-24.04-8"), B.vcpus("")), (8, 2, 16, 0, 0, 0))
        self.assertEqual(B.job_cost(_job("r", "ubuntu-latest", "2026-11-05T10:00:00Z", "2026-11-05T11:00:00Z")), 0.0)

    def test_every_started_minute_is_rounded_up(self):
        c = B.job_cost(_job("r", UBI, "2026-11-05T10:00:00Z", "2026-11-05T10:10:01Z"))     # 10 min 1 s -> 11 minutes
        self.assertAlmostEqual(c, 11 * 8 * B.PRICE_PER_VCPU_MIN)
        self.assertAlmostEqual(B.job_cost(_job("r", UBI, "2026-11-05T10:00:00Z", "2026-11-05T10:00:05Z")),
                               1 * 8 * B.PRICE_PER_VCPU_MIN, msg="a 5-second job is a whole minute")

    def test_a_running_job_is_priced_to_now_and_an_unreadable_one_is_unknown(self):
        now = datetime.datetime(2026, 11, 5, 10, 30, 0)
        self.assertAlmostEqual(B.job_cost(_job("r", UBI, "2026-11-05T10:00:00Z", None), now), 30 * 8 * B.PRICE_PER_VCPU_MIN)
        spend, last, why = B.month_spend([_job("a", UBI, "2026-11-05T10:00:00Z", "2026-11-05T10:20:00Z"),
                                          _job("b", UBI, "garbage", "2026-11-05T10:20:00Z")])
        self.assertIsNone(spend, "a job whose times would not read was left out of the spend")
        self.assertTrue(why)

    def test_the_month_and_the_last_round(self):
        jobs = [_job("1.1", UBI, "2026-11-01T10:00:00Z", "2026-11-01T10:20:00Z"),
                _job("1.1", UBI, "2026-11-01T10:00:00Z", "2026-11-01T10:30:00Z"),
                _job("2.1", UBI, "2026-11-03T10:00:00Z", "2026-11-03T10:10:00Z"),
                _job("2.1", "ubuntu-latest", "2026-11-03T10:00:00Z", "2026-11-03T12:00:00Z")]
        spend, last, why = B.month_spend(jobs)
        p = 8 * B.PRICE_PER_VCPU_MIN
        self.assertIsNone(why)
        self.assertAlmostEqual(spend, (20 + 30 + 10) * p)
        self.assertAlmostEqual(last, 10 * p, msg="the last round is the newest run's Ubicloud cost")


class TheCapDecides(unittest.TestCase):

    def test_ubicloud_only_inside_the_cap(self):
        self.assertEqual(B.decide(5.0, "25", UBI, 2.0)[0], UBI)
        self.assertEqual(B.decide(23.5, "25", UBI, 2.0)[0], GH, "a round that would pass $25 still went to Ubicloud")
        self.assertEqual(B.decide(25.0, "25", UBI, 0.5)[0], GH)
        self.assertEqual(B.decide(20.0, "25", UBI, None)[0], UBI)          # 20 + the 3.00 default fits
        self.assertEqual(B.decide(22.5, "25", UBI, None)[0], GH, "an unmeasured round was priced at zero")

    def test_anything_unknown_is_github(self):
        for spend, budget, want in ((None, "25", UBI), (1.0, "lots", UBI), (1.0, "25", ""), (1.0, "25", "ubuntu-latest")):
            with self.subTest(spend=spend, budget=budget, want=want):
                self.assertEqual(B.decide(spend, budget, want)[0], GH)

    def test_the_step_never_fails_and_writes_its_choice(self):
        d = tempfile.mkdtemp(prefix="budget-law-")
        out = os.path.join(d, "out")
        env = {"PROOF_RUNNER": UBI, "PROOF_BUDGET_USD": "25", "GITHUB_REPOSITORY": "x/y", "GITHUB_OUTPUT": out}
        with mock.patch.dict(os.environ, env), mock.patch.object(B, "fetch_jobs", side_effect=RuntimeError("HTTP 502")):
            self.assertEqual(B.main(), 0, "the budget step failed the run")
        got = io.open(out, encoding="utf-8").read()
        self.assertIn("runner=ubuntu-latest\n", got, "a budget that could not be read did not fall back to GitHub")
        self.assertIn("provers=", got)
        with mock.patch.dict(os.environ, dict(env, GITHUB_OUTPUT=out + "2")), mock.patch.object(B, "fetch_jobs", return_value=[]):
            B.main()
        self.assertIn("runner=%s\n" % UBI, io.open(out + "2", encoding="utf-8").read())

    def test_every_attempt_and_page_is_read(self):
        calls = []

        def api(path):
            calls.append(path)
            if "workflows/ubicloud-probe.yml" in path:
                raise RuntimeError("gh: Not Found (HTTP 404)")
            if "/runs?" in path:
                return {"workflow_runs": [{"id": 7, "run_attempt": 2}]}
            return {"jobs": [{"labels": [UBI], "started_at": "2026-11-05T10:00:00Z", "completed_at": "2026-11-05T10:05:00Z"}]}
        jobs = B.fetch_jobs("x/y", datetime.datetime(2026, 11, 5), _api_=api)
        self.assertEqual(sorted(j["run_id"] for j in jobs), ["7.1", "7.2"], "a re-run attempt's jobs were not counted")
        self.assertTrue(any("created=%3E%3D2026-11-01" in c for c in calls), calls)


class TheWorkflowObeysIt(unittest.TestCase):

    def test_the_shards_take_the_budget_jobs_choice(self):
        wf = io.open(os.path.join(ROOT, ".github", "workflows", "proof-keys-shards.yml"), encoding="utf-8").read()
        shard = wf[wf.index("  shard:\n"):wf.index("    strategy:", wf.index("  shard:\n"))]
        self.assertIn("    needs: [budget]\n", shard)
        self.assertIn("    runs-on: ${{ needs.budget.outputs.runner || 'ubuntu-latest' }}\n", shard,
                      "the shards ignore the budget job's runner")
        self.assertIn("    if: ${{ !cancelled() }}\n", shard, "a newer push no longer cancels the shards")
        self.assertIn("      HEART2_PROVE_WORKERS: ${{ needs.budget.outputs.provers || '3' }}\n", wf)
        budget = wf[wf.index("  budget:\n"):wf.index("  shard:\n")]
        self.assertIn("        continue-on-error: true\n", budget, "a failing budget step can fail the run")
        self.assertIn("run: python3 tv/ci_budget.py", budget)


RED_PROOF = [
    {"why": "v3865 - a round that would pass the cap still goes to Ubicloud",
     "file": "tv/ci_budget.py",
     "find": "    if spend + nxt > budget:\n",
     "replace": "    if spend > budget:\n",
     "matches": 1},
    {"why": "v3865 - an UNKNOWN spend is read as zero and spends",
     "file": "tv/ci_budget.py",
     "find": "    if spend is None:\n        return GITHUB_RUNNER,",
     "replace": "    if spend is None:\n        spend = 0.0\n    if False:\n        return GITHUB_RUNNER,",
     "matches": 1},
    {"why": "v3865 - a part minute is not counted (the meter under-counts)",
     "file": "tv/ci_budget.py",
     "find": "    mins = max(1, int(math.ceil((b - a).total_seconds() / 60.0)))",
     "replace": "    mins = int((b - a).total_seconds() // 60)",
     "matches": 1},
    {"why": "v3865 - an unreadable job is left out of the spend instead of making it UNKNOWN",
     "file": "tv/ci_budget.py",
     "find": "        if c is None:\n            return None, None,",
     "replace": "        if c is None:\n            continue\n        if False:\n            return None, None,",
     "matches": 1},
    {"why": "v3865 - a re-run attempt's jobs are not counted",
     "file": "tv/ci_budget.py",
     "find": "                for att in range(1, int(r.get(\"run_attempt\") or 1) + 1):\n",
     "replace": "                for att in (int(r.get(\"run_attempt\") or 1),):\n",
     "matches": 1},
    {"why": "v3865 - a budget that could not be read fails the run instead of falling back to GitHub",
     "file": "tv/ci_budget.py",
     "find": "    except Exception as e:\n        runner, say = GITHUB_RUNNER,",
     "replace": "    except ZeroDivisionError as e:\n        runner, say = GITHUB_RUNNER,",
     "matches": 1},
    {"why": "v3865 - the shards ignore the budget job and run wherever the variable says",
     "file": ".github/workflows/proof-keys-shards.yml",
     "find": "    runs-on: ${{ needs.budget.outputs.runner || 'ubuntu-latest' }}\n",
     "replace": "    runs-on: ${{ vars.PROOF_RUNNER || 'ubuntu-latest' }}\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
