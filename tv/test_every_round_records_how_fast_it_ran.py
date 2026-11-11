# -*- coding: utf-8 -*-
"""v3890 (#194, REG-3518) - EVERY ROUND RECORDS HOW FAST IT RAN, SO "IS IT GETTING FASTER" IS A NUMBER.

His words, 11-09: "optimize the #194 all the way and make sure it keeps getting faster self improve it". The rounds now
choose their own shard counts and carry what they learned; tv/ci_speed.py is the ledger that says whether that works. When
GitHub vouches, the ship measures every workflow on the commit from GitHub's own job records (queue wait, jobs, slowest
job, wall) and says each against its previous rounds. MEASURED on v3889 (the old account): Publish waited up to 15.0 min,
Routine I's slowest job 19.8-20.0, the proof shards' 43.3, the Windows set's 54.0 in a 99.6-min wall. Held here:
  * measure() is GitHub's job records arithmetic: the queue is created->started, the slowest is started->completed, the
    wall is first created -> last completed; a job never started or finished is counted unfinished, never timed as 0;
  * trend() says FASTER / SLOWER / the same against the same workflow's earlier rounds, never against its own commit;
  * the ship hands its real run the observer, never a law's fake run, and a measuring fault never refuses a ship.
RED_PROOF below.
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import ci_speed as S  # noqa: E402


def _job(name, c, s, e):
    t = lambda m: None if m is None else "2026-11-09T14:%02d:00Z" % m
    return {"name": name, "created_at": t(c), "started_at": t(s), "completed_at": t(e)}


RUN = [{"workflow": "Routine I", "jobs": [_job("shard 1/14", 0, 2, 12), _job("shard 2/14", 0, 0, 20),
                                         _job("merge", 20, 21, 23), _job("queued", 0, None, None)]}]


class EveryRoundRecordsHowFastItRan(unittest.TestCase):

    def test_the_numbers_are_githubs_own_job_records(self):
        """* THE POINT - queue, slowest, wall, and the job that never ran is not a 0-minute job"""
        r = S.measure(RUN)[0]
        self.assertEqual((r["jobs"], r["unfinished"]), (3, 1))
        self.assertEqual((r["queueMaxMin"], r["slowestJob"], r["slowestMin"], r["wallMin"]), (2.0, "shard 2/14", 20.0, 23.0))
        self.assertEqual(r["queueAvgMin"], 1.0)

    def test_a_job_our_own_cancel_cut_short_is_never_a_speed(self):
        """v3896 (REG-3683) - the ship cancels the optional Windows run once GitHub vouches; that run is not a timing"""
        t = "2026-11-11T02:%02d:00Z"
        cut = {"workflow": "proof-keys windows", "jobs": [
            {"name": "w1", "conclusion": "cancelled", "created_at": t % 0, "started_at": t % 1, "completed_at": t % 43}]}
        mixed = {"workflow": "agent tests", "jobs": [
            {"name": "a", "conclusion": "success", "created_at": t % 0, "started_at": t % 1, "completed_at": t % 21},
            {"name": "b", "conclusion": "cancelled", "created_at": t % 0, "started_at": t % 1, "completed_at": t % 50}]}
        rows = S.measure([cut, mixed])
        self.assertEqual([r["workflow"] for r in rows], ["agent tests"], "a run our own cancel cut short became a speed")
        self.assertEqual((rows[0]["slowestMin"], rows[0]["cancelled"]), (20.0, 1), rows)

    def test_the_fetch_asks_each_jobs_conclusion(self):
        seen = []

        def run(cmd, **k):
            seen.append(cmd)
            import subprocess as _sp
            if cmd[:3] == ["gh", "run", "list"]:
                return _sp.CompletedProcess(cmd, 0, '[{"databaseId": 1, "name": "w"}]', "")
            return _sp.CompletedProcess(cmd, 0, "", "")
        S.fetch("abc", "o/r", run=run)
        jq = [c[c.index("-q") + 1] for c in seen if "-q" in c]
        self.assertTrue(jq and "conclusion" in jq[0], "the job fetch does not ask whether a job was cancelled: %r" % jq)

    def test_the_trend_compares_earlier_rounds_never_its_own_commit(self):
        row = dict(S.measure(RUN)[0], sha="aaa")
        past = [{"workflow": "Routine I", "sha": "old1", "slowestMin": 30.0},
                {"workflow": "Routine I", "sha": "old2", "slowestMin": 26.0},
                {"workflow": "Routine I", "sha": "aaa", "slowestMin": 1.0}]
        line = S.trend([row], past)[0]
        self.assertIn("FASTER 8.0 min than the last 2 rounds' 28.0", line)
        self.assertIn("the first round measured", S.trend([row], [])[0])
        # v3896 (REG-3675) - a tie reads "the same as", never "the same than"
        same = S.trend([row], [{"workflow": "Routine I", "sha": "old3", "slowestMin": 20.2}])[0]
        self.assertIn("(the same as the last 1 rounds' 20.2)", same)
        self.assertNotIn(" than the last", same)

    def test_a_round_is_recorded_once_per_workflow_and_read_back(self):
        tmp = tempfile.mkdtemp(prefix="ci_speed_")
        try:
            p = os.path.join(tmp, "ci_speed.jsonl")
            self.assertEqual(S.record("abcdef1234567890", "v3891", S.measure(RUN), p, now=1), 1)
            rows = S.history(p)
            self.assertEqual([(r["workflow"], r["sha"], r["version"]) for r in rows], [("Routine I", "abcdef123456", "v3891")])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_an_unreadable_ledger_is_unknown_never_an_empty_history(self):
        """the swallow ratchet's rule: absent = no round yet ([]); there and unreadable = None, never []"""
        tmp = tempfile.mkdtemp(prefix="ci_speed_unread_")
        try:
            self.assertEqual(S.history(os.path.join(tmp, "absent.jsonl")), [])
            self.assertIsNone(S.history(tmp), "a ledger that will not read (here: a directory) read as no history")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_a_round_that_cannot_be_measured_is_said_and_never_raises(self):
        said = []

        def broken(*a, **k):
            raise OSError("gh is not here")
        self.assertIsNone(S.observe("abc", "v1", "o/r", say=said.append, run=broken, path=os.devnull),
                          "a round that could not be measured read as a measured zero")
        self.assertTrue(any("could not be measured" in x for x in said), said)

    def test_the_ship_measures_its_real_round_only(self):
        with io.open(os.path.join(HERE, "ship_when_green.py"), encoding="utf-8") as fh:
            src = "\n".join(l.split("#", 1)[0] for l in fh.read().split("\n"))
        self.assertIn("mac_rehearse=not a.no_mac_rehearse, speed=_CS.observe)", src, "the real ship no longer measures its round")
        self.assertIn("    if speed is not None:\n        try:\n            speed(sha, version, CV.REPO_SLUG, say=say)", src)
        i = src.index('say("ship: GitHub vouches for %s - pushing main')
        self.assertLess(i, src.index("if speed is not None:"), "the round is measured before GitHub vouched for it")


def _gh(branches, fail=False, commit_runs=None):
    """A fake `gh` for observe()/attempts(): per ci branch, its runs; one finished job on the commit."""
    import subprocess as _sp

    def run(cmd, **k):
        if cmd[:3] == ["gh", "run", "list"] and "--branch" in cmd:
            if fail:
                return _sp.CompletedProcess(cmd, 1, "", "HTTP 502")
            return _sp.CompletedProcess(cmd, 0, json.dumps(branches.get(cmd[cmd.index("--branch") + 1], [])), "")
        if cmd[:3] == ["gh", "run", "list"]:
            return _sp.CompletedProcess(cmd, 0, json.dumps(commit_runs or [{"databaseId": 1, "name": "Routine I"}]), "")
        return _sp.CompletedProcess(cmd, 0, json.dumps(dict(_job("shard 1/14", 0, 2, 12), conclusion="success")) + "\n", "")
    return run


def _r(sha, wf, attempt, minute):
    return {"headSha": sha * 40, "workflowName": wf, "attempt": attempt, "createdAt": "2026-11-11T0%d:00:00Z" % minute}


AGENT, PLAYWRIGHT, PROOFS = "📺 TV DIABLO — agent tests", "Routine I — Playwright suite", "proof-keys shards (ci/proof-keys-* only)"
WINDOWS_BESIDE = "🪟 proof-keys windows (beside the ci shards, not required)"
BRANCHES = {"ci/claude-v1": [_r("b", AGENT, 3, 5), _r("a", PLAYWRIGHT, 1, 2), _r("c", WINDOWS_BESIDE, 1, 7)],
            "ci/proof-keys-v1": [_r("a", PROOFS, 2, 1), _r("b", PROOFS, 1, 4)]}


class EveryVersionCountsItsRounds(unittest.TestCase):
    """v3897 (card #200) - his 11-10 words: "this is ridiculous to do 7-12 attempts to ship". MEASURED by hand until now
    (v3894: 7 attempts; v3895: 3 GitHub rounds, 4 re-runs). The ship now counts, at the vouch, the commits its two ci branches
    carried a REQUIRED run on and the re-runs inside them, records them, and says them against the target of 2."""

    def test_a_round_is_a_commit_with_a_required_run_and_a_re_run_is_an_attempt_past_the_first(self):
        """* THE POINT"""
        a = S.attempts("v1", "o/r", run=_gh(BRANCHES))
        self.assertEqual((a["rounds"], a["reruns"]), (2, 3), a)
        self.assertEqual(a["shas"], ["a" * 12, "b" * 12], "the rounds are not in the order GitHub ran them")
        self.assertNotIn("c" * 12, a["shas"], "the optional Windows run beside the ship counted as a round")

    def test_a_count_github_would_not_give_is_unknown_never_zero(self):
        self.assertIsNone(S.attempts("v1", "o/r", run=_gh(BRANCHES, fail=True)))
        self.assertIsNone(S.attempts("v1", "o/r", run=_gh({})), "no round on either branch read as a measured zero")
        self.assertIsNone(S.attempts(None, "o/r", run=_gh(BRANCHES)))

    def test_the_sentence_says_the_target_and_the_last_versions(self):
        past = [{"workflow": S.ATTEMPTS_ROW, "version": "v0", "rounds": 7}, {"workflow": S.ATTEMPTS_ROW, "version": "v1", "rounds": 9}]
        line = S.attempts_line({"version": "v1", "rounds": 2, "reruns": 1}, past)
        self.assertIn("v1 took 2 GitHub round(s) and 1 re-run(s) of failed jobs - within the target of 2", line)
        self.assertIn("the last 1 versions took v0 7", line, "the trend left out an earlier version or read its own")
        self.assertIn("OVER the target of 2", S.attempts_line({"version": "v2", "rounds": 3, "reruns": 0}, []))

    def test_the_vouch_records_the_count_and_the_ledger_still_shows(self):
        tmp = tempfile.mkdtemp(prefix="ci_speed_attempts_")
        try:
            p, said = os.path.join(tmp, "ci_speed.jsonl"), []
            self.assertEqual(S.observe("b" * 40, "v1", "o/r", say=said.append, run=_gh(BRANCHES), path=p), 1)
            rows = S.history(p)
            self.assertEqual([r["workflow"] for r in rows], ["Routine I", S.ATTEMPTS_ROW], rows)
            self.assertTrue(any("#200 ATTEMPTS - v1 took 2 GitHub round(s)" in x for x in said), said)
            said = []
            S.observe("b" * 40, "v1", "o/r", say=said.append, run=_gh(BRANCHES, fail=True), path=p)
            self.assertTrue(any("#200 ATTEMPTS" in x and "UNKNOWN" in x for x in said), said)
            import contextlib
            from unittest import mock
            out = io.StringIO()
            with mock.patch.object(S, "ledger_path", lambda *a, **k: p), contextlib.redirect_stdout(out):
                self.assertEqual(S.main(["--show"]), 0)
            self.assertIn("2 round(s) · 3 re-run(s) · target 2", out.getvalue())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


RED_PROOF = [
    {"why": "v3890 (#194) - a round that could not be measured hands back 0, the same as a measured round with no job",
     "file": "tv/ci_speed.py",
     "find": "(type(e).__name__, str(e)[:120]))\n        return None\n",
     "replace": "(type(e).__name__, str(e)[:120]))\n        return 0\n",
     "matches": 1},
    {"why": "v3890 (#194) - an unreadable ledger reads as an empty history (a failed read handed back as data)",
     "file": "tv/ci_speed.py",
     "find": "    except OSError:\n        return None\n    return rows\n",
     "replace": "    except OSError:\n        return []\n    return rows\n",
     "matches": 1},
    {"why": "v3890 (#194) - a job that never ran is timed as a 0-minute job",
     "file": "tv/ci_speed.py",
     "find": "            if c is None or s is None or e is None or e < s:\n                unfinished += 1\n                continue\n",
     "replace": "            if c is None or s is None or e is None or e < s:\n                c = s = e = c or 0\n",
     "matches": 1},
    {"why": "v3890 (#194) - the trend compares a round with its own commit",
     "file": "tv/ci_speed.py",
     "find": "if p.get(\"workflow\") == r[\"workflow\"] and p.get(\"sha\") != r.get(\"sha\")][-n:]",
     "replace": "if p.get(\"workflow\") == r[\"workflow\"]][-n:]",
     "matches": 1},
    {"why": "v3890 (#194) - a measuring fault raises into the ship",
     "file": "tv/ci_speed.py",
     "find": "    except Exception as e:\n        say(\"ship: v3890 (#194) SPEED - this round could not be measured",
     "replace": "    except ZeroDivisionError as e:\n        say(\"ship: v3890 (#194) SPEED - this round could not be measured",
     "matches": 1},
    {"why": "v3890 (#194) - the real ship stops measuring its rounds",
     "file": "tv/ship_when_green.py",
     "find": "mac_rehearse=not a.no_mac_rehearse, speed=_CS.observe)",
     "replace": "mac_rehearse=not a.no_mac_rehearse)",
     "matches": 1},
    {"why": "v3896 (REG-3675) - a tie reads 'the same than the last N rounds' again",
     "file": "tv/ci_speed.py",
     "find": "        cmp = (\"the same as\" if word == \"the same\" else \"%s %.1f min than\" % (word, abs(delta)))\n",
     "replace": "        cmp = (\"the same than\" if word == \"the same\" else \"%s %.1f min than\" % (word, abs(delta)))\n",
     "matches": 1},
    {"why": "v3897 (card #200) - the optional Windows run beside the ship counts as a round",
     "file": "tv/ci_speed.py",
     "find": "            if not isinstance(w, dict) or w.get(\"workflowName\") not in CV.REQUIRED or not w.get(\"headSha\"):\n",
     "replace": "            if not isinstance(w, dict) or not w.get(\"headSha\"):\n",
     "matches": 1},
    {"why": "v3897 (card #200) - a round count GitHub would not give reads as zero rounds",
     "file": "tv/ci_speed.py",
     "find": "    if not seen:\n        return None\n",
     "replace": "    if False:\n        return None\n",
     "matches": 1},
    {"why": "v3897 (card #200) - a re-run of failed jobs is never counted",
     "file": "tv/ci_speed.py",
     "find": "                reruns += max(0, int(w.get(\"attempt\") or 1) - 1)\n",
     "replace": "                reruns += 0\n",
     "matches": 1},
    {"why": "v3897 (card #200) - a version over the target reads as within it",
     "file": "tv/ci_speed.py",
     "find": "    word = \"within\" if row[\"rounds\"] <= ATTEMPTS_TARGET else \"OVER\"\n",
     "replace": "    word = \"within\"\n",
     "matches": 1},
    {"why": "v3897 (card #200) - the vouch never records how many rounds the version took",
     "file": "tv/ci_speed.py",
     "find": "            record(sha, version, [a], p)\n",
     "replace": "            pass\n",
     "matches": 1},
    {"why": "v3897 (card #200) - the ledger's --show crashes on a version's round count",
     "file": "tv/ci_speed.py",
     "find": "            if r.get(\"workflow\") == ATTEMPTS_ROW:    # v3897 (card #200) - a version's rounds, never a speed\n",
     "replace": "            if False:\n",
     "matches": 1},
    {"why": "v3896 (REG-3683) - a job our own cancel cut short is timed as a speed again",
     "file": "tv/ci_speed.py",
     "find": "            if str(j.get(\"conclusion\") or \"\").lower() in (\"cancelled\", \"skipped\"):\n",
     "replace": "            if False:\n",
     "matches": 1},
    {"why": "v3896 (REG-3683) - the job fetch stops asking each job's conclusion, so no cancel can be seen",
     "file": "tv/ci_speed.py",
     "find": "                 \"-q\", \".jobs[] | {name, conclusion, created_at, started_at, completed_at}\"],\n",
     "replace": "                 \"-q\", \".jobs[] | {name, created_at, started_at, completed_at}\"],\n",
     "matches": 1}
]


if __name__ == "__main__":
    unittest.main()
