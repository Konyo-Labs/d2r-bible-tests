# -*- coding: utf-8 -*-
"""REG-3652 - REQUIRED-CHECK JUDGEMENT IGNORES NON-REQUIRED PROOF-KEYS WINDOWS JOBS.

Attempt 10 (run 42816227617, sha 518744bfd): every required Linux proof-keys
job (seed + ci shards, including the shard-15 make-up) was already green, but
the ship kept waiting and fired the 75-minute alert because the non-required
'proof-keys windows' jobs in the same CI cycle were still running or queued.
Required-check judgement now looks only at the required jobs (the Linux seed,
the ci shard jobs, and the fan-in that bags them). Windows jobs never hold
the verdict, never make a required check red, and never trip the 75-minute
alert on their own.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import ci_verdict as CV  # noqa: E402
import shard_watch as SHW  # noqa: E402
import ship_when_green as SW  # noqa: E402

SHA = "518744bfd" + "0" * 31


def _job(name, status="completed", conclusion="success"):
    return {"name": name, "status": status, "conclusion": conclusion,
            "databaseId": abs(hash(name)) % 10_000_000}


def _linux_required(extra=None, shards=3):
    jobs = [_job("seed - the proofs this exact commit already has")]
    for i in range(1, shards + 1):
        jobs.append(_job("shard %d" % i))
    jobs.append(_job("fan-in - one whole set of this commit, or none"))
    jobs.extend(extra or [])
    return jobs


def _windows_running():
    return [
        _job("seed - the Windows proofs the bank already has"),
        _job("windows shard 1", "in_progress", ""),
        _job("windows shard 5", "queued", ""),
        _job("windows fan-in - one whole set of this commit, or none", "queued", ""),
    ]


def _proof_run(jobs, status="in_progress", conclusion=""):
    return {"workflowName": CV.REQUIRED[3], "headSha": SHA, "databaseId": 42816227617,
            "status": status, "conclusion": conclusion, "createdAt": "2026-11-10T13:00:00Z",
            "jobs": jobs}


def _all_required_green(proof_jobs=None, proof_status="in_progress", proof_conclusion=""):
    rows = []
    for i, wf in enumerate(CV.REQUIRED):
        if wf == CV.REQUIRED[3]:
            rows.append(_proof_run(proof_jobs or _linux_required(_windows_running() + [
                _job("proof bank - publish this commit's proofs for every PC", "queued", ""),
            ]), proof_status, proof_conclusion))
        else:
            rows.append({"workflowName": wf, "headSha": SHA, "databaseId": 1000 + i,
                         "status": "completed", "conclusion": "success",
                         "createdAt": "2026-11-10T13:00:00Z"})
    return rows


class TheLawHolds(unittest.TestCase):
    def test_windows_job_names_are_recognized_and_boot_is_not(self):
        self.assertTrue(SHW.is_proof_windows_name("windows shard 1"))
        self.assertTrue(SHW.is_proof_windows_name(
            "🪟 proof-keys windows (beside the ci shards, not required) / windows shard 1 (27 min)"))
        self.assertTrue(SHW.is_proof_windows_job(
            _job("seed - the Windows proofs the bank already has"),
            "🪟 proof-keys windows (beside the ci shards, not required)"))
        self.assertFalse(SHW.is_proof_windows_name("🪟 TV DIABLO — Windows boot"))
        self.assertFalse(SHW.is_proof_windows_job(_job("Windows boot"), CV.REQUIRED[2]))
        self.assertFalse(SHW.is_proof_windows_job(
            _job("shard 15"), CV.REQUIRED[3]))

    def test_seed_shards_and_fan_in_green_is_green_while_windows_jobs_run(self):
        jobs = _linux_required(_windows_running() + [
            _job("proof bank - publish this commit's proofs for every PC", "in_progress", ""),
        ])
        v, why = SHW.required_jobs_verdict(jobs, CV.REQUIRED[3])
        self.assertEqual(v, "green", why)
        self.assertIn("windows", why.lower())

        verdict, why = CV.decide(_all_required_green(jobs), SHA)
        self.assertEqual(verdict, "green", why)

    def test_a_windows_job_failure_does_not_make_the_required_check_red(self):
        jobs = _linux_required([_job("windows shard 12", "completed", "failure")])
        v, why = SHW.required_jobs_verdict(jobs, CV.REQUIRED[3])
        self.assertEqual(v, "green", why)
        self.assertEqual(SW.red_runs(_all_required_green(jobs), SHA), [])

    def test_a_red_linux_shard_is_still_red_while_windows_jobs_run(self):
        jobs = _linux_required(_windows_running())
        for j in jobs:
            if j["name"] == "shard 2":
                j["conclusion"] = "failure"
        v, why = SHW.required_jobs_verdict(jobs, CV.REQUIRED[3])
        self.assertEqual(v, "not", why)
        self.assertIn("shard 2", why)
        runs = _all_required_green(jobs)
        self.assertEqual(CV.decide(runs, SHA)[0], "not")
        red = SW.red_runs(runs, SHA)
        self.assertTrue(red, "a required shard failure was hidden by in-progress windows jobs")
        self.assertTrue(any(CV.REQUIRED[3] in x for x in red), red)

    def test_fan_in_still_owed_is_pending_not_green(self):
        jobs = [_job("seed - the proofs this exact commit already has"),
                _job("shard 1"), _job("shard 2")] + _windows_running()
        v, why = SHW.required_jobs_verdict(jobs, CV.REQUIRED[3])
        self.assertEqual(v, "pending", why)
        self.assertEqual(CV.decide(_all_required_green(jobs), SHA)[0], "not")

    def test_suites_in_progress_ignores_windows_jobs(self):
        jobs = _linux_required(_windows_running())
        runs = _all_required_green(jobs)
        self.assertFalse(SHW.suites_in_progress(runs, SHA),
                         "windows jobs kept the required suite 'in progress'")
        pending = _linux_required(_windows_running())
        for j in pending:
            if j["name"] == "shard 3":
                j["status"] = "queued"
                j["conclusion"] = ""
        self.assertTrue(SHW.suites_in_progress(_all_required_green(pending), SHA))

    def test_the_75_minute_alert_does_not_name_windows_jobs(self):
        line = SW.overrun_alert(
            SHA, 75, _all_required_green(),
            watch=lambda _sha: {
                "running": [
                    "🪟 proof-keys windows (beside the ci shards, not required) / windows shard 1 (27 min)",
                    "🪟 proof-keys windows (beside the ci shards, not required) / windows shard 5 (22 min)",
                ],
                "runs": [],
            })
        self.assertNotIn("windows shard", line.lower())
        self.assertNotIn("proof-keys windows", line.lower())

    def test_an_in_progress_run_without_jobs_stays_not_green(self):
        # Existing decide() contract: no job list means run-level status still rules.
        runs = _all_required_green()
        runs[-1].pop("jobs", None)
        self.assertEqual(CV.decide(runs, SHA)[0], "not")


class TheProofsNameOnePlace(unittest.TestCase):
    def test_each_find_matches_once(self):
        for p in RED_PROOF:
            blob = open(os.path.join(os.path.dirname(HERE), p["file"]), encoding="utf-8").read()
            self.assertEqual(blob.count(p["find"]), p["matches"], p["why"])



class TheShipCancelsItsOptionalRunsOnceVouched(unittest.TestCase):
    """card #200 guard 7 - MEASURED 11-11: v3894's optional Windows set held Publish's runners after the vouch"""

    def _runs(self):
        W = "🪟 proof-keys windows (beside the ci shards, not required)"
        return [
            {"name": W, "status": "in_progress", "databaseId": 11, "headSha": "abc123"},          # cancel
            {"name": W, "status": "completed", "databaseId": 12, "headSha": "abc123"},            # finished: leave
            {"name": W, "status": "queued", "databaseId": 13, "headSha": "fff999"},               # another commit
            {"name": CV.REQUIRED[3], "status": "in_progress", "databaseId": 14, "headSha": "abc123"},  # required
        ]

    def test_only_this_commits_live_beside_runs_are_cancelled(self):
        asked = []
        class R(object):
            returncode = 0
            stderr = ""
        got = SW.cancel_beside(self._runs(), "abc123", run=lambda cmd, **k: asked.append(cmd) or R(), say=lambda *a: None)
        self.assertEqual(got, [11], "the ship cancelled the wrong runs: %r" % asked)
        self.assertEqual(asked, [["gh", "run", "cancel", "11", "--repo", CV.REPO_SLUG]])

    def test_the_ship_cancels_them_right_after_the_vouch(self):
        src = open(os.path.join(HERE, "ship_when_green.py"), encoding="utf-8").read()
        i = src.index('    say("ship: GitHub vouches for %s - pushing main (the pre-push trusts this verdict)" % sha[:9])\n')
        # bounded by the next statement, never a byte count (test_a_source_window_must_reach_its_subject)
        self.assertIn("        cancel_beside(runs, sha, run=run, say=say)\n", src[i:src.index("    if speed is not None:", i)],
                      "the ship no longer cancels its optional runs once GitHub vouches")



class AFakeShipNeverWritesTheRealTimings(unittest.TestCase):
    """v3895 - MEASURED 11-11: every pre-flight left tv/shard_timings.json dirty with a law's fixture version and sha
    ("v3862 aaaaaaaaa", "v3875 0d4e24537"), because a fake ship() folded timings into the REAL file"""

    def test_only_the_cli_hands_the_ship_its_timings_writer(self):
        src = open(os.path.join(HERE, "ship_when_green.py"), encoding="utf-8").read()
        self.assertEqual(src.count("merge_timings_after_green(sha, version, say)"), 0,
                         "ship() calls the real timings writer itself - a law's fake ship writes the tracked file")
        self.assertIn("timings=merge_timings_after_green)", src, "the real CLI no longer hands the ship its timings writer")
        self.assertIn("    if timings is not None:\n        timings(sha, version, say)\n", src)


RED_PROOF = [
    {"why": "v3895 - a law's fake ship folds its fixture timings into the real tracked file again",
     "file": "tv/ship_when_green.py",
     "find": "    if timings is not None:\n        timings(sha, version, say)\n",
     "replace": "    merge_timings_after_green(sha, version, say)\n",
     "matches": 1},
    {"why": "card #200 guard 7 - the ship stops cancelling its optional runs once GitHub vouches",
     "file": "tv/ship_when_green.py",
     "find": "        cancel_beside(runs, sha, run=run, say=say)\n",
     "replace": "        pass\n",
     "matches": 1},
    {"why": "card #200 guard 7 - a REQUIRED workflow can be cancelled as if it were optional",
     "file": "tv/ship_when_green.py",
     "find": "CV._name(r) not in BESIDE or CV._name(r) in CV.REQUIRED:",
     "replace": "False:",
     "matches": 1},
    {"why": "REG-3652 - decide() no longer skips a required check whose required jobs are already green",
     "file": "tv/ci_verdict.py",
     "find": "            if _required_jobs_green(last, wf):  # REG-3652 - windows proofs never hold a required check\n",
     "replace": "            if False:\n",
     "matches": 1},
    {"why": "REG-3652 - suites_in_progress still treats a run as live from its status alone, so windows jobs hold the poll",
     "file": "tv/shard_watch.py",
     "find": "            v, _why = required_jobs_verdict(jobs, wf)\n            if v == \"pending\":\n                return True\n            continue\n",
     "replace": "            if str(r.get(\"status\") or \"\") in (\"in_progress\", \"queued\", \"waiting\", \"pending\"):\n                return True\n            continue\n",
     "matches": 1},
    {"why": "REG-3652 - the 75-minute alert still names non-required windows jobs as what holds the ship",
     "file": "tv/ship_when_green.py",
     "find": "            named = [n for n in named if not SHW.is_proof_windows_name(n)]\n",
     "replace": "            named = list(named)\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
