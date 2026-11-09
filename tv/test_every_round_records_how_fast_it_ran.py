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

    def test_the_trend_compares_earlier_rounds_never_its_own_commit(self):
        row = dict(S.measure(RUN)[0], sha="aaa")
        past = [{"workflow": "Routine I", "sha": "old1", "slowestMin": 30.0},
                {"workflow": "Routine I", "sha": "old2", "slowestMin": 26.0},
                {"workflow": "Routine I", "sha": "aaa", "slowestMin": 1.0}]
        line = S.trend([row], past)[0]
        self.assertIn("FASTER 8.0 min than the last 2 rounds' 28.0", line)
        self.assertIn("the first round measured", S.trend([row], [])[0])

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
        self.assertIn("speed=_CS.observe)", src, "the real ship no longer measures its round")
        self.assertIn("    if speed is not None:\n        try:\n            speed(sha, version, CV.REPO_SLUG, say=say)", src)
        i = src.index('say("ship: GitHub vouches for %s - pushing main')
        self.assertLess(i, src.index("if speed is not None:"), "the round is measured before GitHub vouched for it")


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
     "find": "watch_publish_s=None if a.no_watch else a.publish_wait_min * 60, speed=_CS.observe)",
     "replace": "watch_publish_s=None if a.no_watch else a.publish_wait_min * 60)",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
