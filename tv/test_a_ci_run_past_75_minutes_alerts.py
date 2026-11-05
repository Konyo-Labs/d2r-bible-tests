# -*- coding: utf-8 -*-
"""REG-3213 - A VERSION'S CI THAT PASSES 75 MINUTES ALERTS, WITHOUT ANYONE PRESSING ANYTHING.

His words (2026-11-05): "why has it been stuck for so long and not triggered at an alert somewhere at 75 minutes which
was max?". MEASURED on v3864: Publish (run 42084305066) ran 18:27 -> ~21:20, and NOTHING watched it - tv/ship_when_green.py
waited on the ci/ branches only and returned at the main push, and the console had no row for CI. Held here:
  * tv/ci_watch.judge, over GitHub's runs on one commit: a run still going past 75 min is `overrun` and names the jobs
    still running; one that finished past 75 is `slow`; a failed one `red` - all three RED; inside the max it is
    `running` / `green`; no run `none`; an unread GitHub `unknown` (worked False, owed None) - never green. Every answer
    carries on / worked / lastTs / owed. Per workflow only its newest run counts; a SCHEDULED routine on the same commit
    is not this version's CI. watch() reads the jobs only of a run
    already past the max (the unauthenticated rate stays low);
  * the console asks it on its own (the rescue loop, every 5 minutes at most, on a thread; status.ciWatch publishes it;
    a TV_STUB test console never calls GitHub, and says so),
    and the eagle row "this version's CI" turns MISSING on overrun / slow / red, UNKNOWN when unread or stale - it is on
    the roster and asked in the console's own process;
  * tv/ship_when_green.py alerts ONCE, loudly, when its ci/ wait passes 75 min, and after the main push it watches
    Publish: an alert past 75 min with the running jobs, its exit says how Publish ended - and its CLI turns that on.
Fixtures only - GitHub, git and the clock are replaced; no network. RED_PROOF below.
"""
import inspect
import io
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import ci_watch as CW  # noqa: E402

SHA = "9d9485ea61f7482320cdc47a5d0e05f670776e77"
T0 = 1762367220.0                     # 2026-11-05 18:27:00 UTC - v3864's Publish began
PUBLISH = "Publish — gates, review, then deploy"


def _iso(t):
    import time
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))


def _run(name, minutes, status="in_progress", conclusion=None, rid=1, started=T0, sha=SHA, created=None):
    return {"id": rid, "name": name, "head_sha": sha, "status": status, "conclusion": conclusion,
            "created_at": _iso(created if created is not None else started), "run_started_at": _iso(started),
            "updated_at": _iso(started + minutes * 60), "html_url": "https://github.com/x/runs/%d" % rid}


class TheJudge(unittest.TestCase):

    def test_a_run_past_75_minutes_is_overrun_and_names_its_running_jobs(self):
        now = T0 + 80 * 60
        jobs = {7: [{"name": "Prove the laws (16 runners) / shard 6", "status": "in_progress", "started_at": _iso(T0 + 60)},
                    {"name": "Prove the laws (16 runners) / shard 14", "status": "completed", "started_at": _iso(T0)}]}
        r = CW.judge([_run(PUBLISH, 80, rid=7)], SHA, now=now, jobs=jobs)
        self.assertEqual(r["state"], "overrun")
        self.assertIn("ALERT", r["why"])
        self.assertTrue(any("shard 6" in x for x in r["running"]), r["running"])
        self.assertFalse(any("shard 14" in x for x in r["running"]), "a finished job was named as still running")
        self.assertEqual(r["owed"], [PUBLISH])
        self.assertEqual((r["on"], r["worked"], r["lastTs"]), (True, True, int(now * 1000)))

    def test_inside_the_max_it_is_running_then_green(self):
        self.assertEqual(CW.judge([_run(PUBLISH, 60)], SHA, now=T0 + 60 * 60)["state"], "running")
        g = CW.judge([_run(PUBLISH, 50, "completed", "success")], SHA, now=T0 + 99 * 60)
        self.assertEqual((g["state"], g["owed"]), ("green", []))

    def test_a_run_that_finished_past_the_max_is_slow_and_red(self):
        r = CW.judge([_run(PUBLISH, 170, "completed", "success")], SHA, now=T0 + 171 * 60)
        self.assertEqual(r["state"], "slow", "a 2 h 50 min Publish that ended green reads green")
        self.assertIn(r["state"], CW.RED_STATES)

    def test_a_failed_run_is_red(self):
        r = CW.judge([_run(PUBLISH, 20, "completed", "failure")], SHA, now=T0 + 30 * 60)
        self.assertEqual(r["state"], "red")
        self.assertIn("failure", r["why"])

    def test_an_unread_github_is_unknown_and_no_run_is_none(self):
        u = CW.judge(None, SHA, now=T0)
        self.assertEqual((u["state"], u["worked"], u["owed"]), ("unknown", False, None))
        n = CW.judge([_run(PUBLISH, 5, sha="e" * 40)], SHA, now=T0)
        self.assertEqual((n["state"], n["worked"]), ("none", True))

    def test_a_scheduled_routine_on_the_same_commit_is_not_this_versions_ci(self):
        sched = dict(_run("Routine G — end-to-end audit", 20, "completed", "failure", rid=3), event="schedule")
        r = CW.judge([sched, _run(PUBLISH, 30, "completed", "success", rid=4)], SHA, now=T0 + 99 * 60)
        self.assertEqual(r["state"], "green", "a scheduled routine's red painted this version's CI red")

    def test_only_the_newest_run_of_a_workflow_counts(self):
        old = _run(PUBLISH, 30, "completed", "failure", rid=1, created=T0)
        new = _run(PUBLISH, 10, "completed", "success", rid=2, started=T0 + 3600, created=T0 + 3600)
        self.assertEqual(CW.judge([old, new], SHA, now=T0 + 7200)["state"], "green")

    def test_watch_reads_jobs_only_for_a_run_past_the_max(self):
        paths = []

        def get(path):
            paths.append(path)
            if "/jobs" in path:
                return {"jobs": [{"name": "shard 13", "status": "in_progress", "started_at": _iso(T0)}]}
            return {"workflow_runs": [_run(PUBLISH, 0, rid=9), _run("📺 TV DIABLO — agent tests", 0, rid=4,
                                                                    started=T0 + 3000)]}
        r = CW.watch(SHA, get=get, now=T0 + 90 * 60)
        self.assertEqual(r["state"], "overrun")
        self.assertEqual(sorted(p for p in paths if "/jobs" in p), ["/repos/%s/actions/runs/9/jobs?per_page=100"
                                                                     % CW.REPO_SLUG])
        self.assertIn("head_sha=%s" % SHA, paths[0])
        self.assertEqual(CW.watch(SHA, get=lambda p: None, now=T0)["state"], "unknown")


class TheConsoleWatchesItOnItsOwn(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import control_app as CA
        import console_doctor as CD
        cls.CA, cls.CD = CA, CD

    def setUp(self):
        self._state = dict(self.CA._CI_WATCH)

    def tearDown(self):
        self.CA._CI_WATCH.clear()
        self.CA._CI_WATCH.update(self._state)

    @staticmethod
    def _git(argv, **kw):
        if argv[1:3] == ["rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(argv, 0, SHA + "\n", "")
        raise AssertionError(argv)

    def test_the_tick_reads_this_commit_at_most_every_five_minutes(self):
        asked = []

        def watch(sha):
            asked.append(sha)
            return CW.judge([_run(PUBLISH, 80, rid=7)], sha, now=T0 + 80 * 60, jobs={7: []})
        self.CA._CI_WATCH.pop("askedAt", None)
        self.CA._CI_WATCH["busy"] = False
        from unittest import mock
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("TV_STUB", None)               # this law may run inside a test console's environment
        r = self.CA._ci_watch_tick(_thread=lambda f: f(), _git_run=self._git, _watch=watch, _now=T0)
        self.assertEqual(asked, [SHA])
        self.assertEqual(self.CA._CI_WATCH["state"], "overrun")
        for k in ("on", "worked", "lastTs", "owed"):
            self.assertIn(k, self.CA._CI_WATCH, "the CI watch does not answer %s" % k)
        self.CA._ci_watch_tick(_thread=lambda f: f(), _git_run=self._git, _watch=watch, _now=T0 + 60)
        self.assertEqual(asked, [SHA], "GitHub was asked again inside 5 minutes")
        self.CA._ci_watch_tick(_thread=lambda f: f(), _git_run=self._git, _watch=watch, _now=T0 + CW.CI_WATCH_EVERY_S)
        self.assertEqual(asked, [SHA, SHA])
        self.assertTrue(r is not None)

    def test_a_test_console_never_asks_github(self):
        from unittest import mock
        asked = []
        self.CA._CI_WATCH.pop("askedAt", None)
        self.CA._CI_WATCH["busy"] = False
        with mock.patch.dict(os.environ, {"TV_STUB": "1"}):
            self.CA._ci_watch_tick(_thread=lambda f: f(), _git_run=self._git, _watch=lambda sha: asked.append(sha),
                                   _now=T0)
        self.assertEqual(asked, [], "a test console asked GitHub")
        self.assertIs(self.CA._CI_WATCH["on"], False)

    def test_the_rescue_loop_asks_it_and_status_publishes_it(self):
        self.assertIn("_ci_watch_tick()", inspect.getsource(self.CA._console_rescue_loop))
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            self.assertIn('"ciWatch": dict(_CI_WATCH)', fh.read())

    def test_the_eagle_row_is_red_past_the_max_and_unknown_when_unread(self):
        CD = self.CD
        over = CW.judge([_run(PUBLISH, 80, rid=7)], SHA, now=T0 + 80 * 60, jobs={7: []})
        self.assertEqual(CD._check_this_versions_ci(over, now=T0 + 80 * 60)[0], CD.MISSING)
        slow = CW.judge([_run(PUBLISH, 170, "completed", "success")], SHA, now=T0 + 171 * 60)
        self.assertEqual(CD._check_this_versions_ci(slow, now=T0 + 171 * 60)[0], CD.MISSING)
        unread = CW.judge(None, SHA, now=T0)
        self.assertEqual(CD._check_this_versions_ci(unread, now=T0)[0], CD.UNKNOWN, "an unread GitHub reads green")
        self.assertEqual(CD._check_this_versions_ci({"lastTs": None, "why": "not asked yet"}, now=T0)[0], CD.UNKNOWN)
        fine = CW.judge([_run(PUBLISH, 30)], SHA, now=T0 + 30 * 60)
        self.assertEqual(CD._check_this_versions_ci(fine, now=T0 + 30 * 60)[0], CD.OK)
        self.assertEqual(CD._check_this_versions_ci(fine, now=T0 + 30 * 60 + 3600)[0], CD.UNKNOWN,
                         "an hour-old reading of a running CI still reads OK")

    def test_the_row_is_on_the_roster_and_asked_in_the_console(self):
        names = [n for n, _fn in self.CD.CHECKS]
        self.assertEqual(names.count("this version's CI"), 1)
        self.assertIn("this version's CI", self.CD.IN_PROCESS)
        self.assertNotIn("this version's CI", self.CD.SLOW)


class ShipWhenGreenAlerts(unittest.TestCase):

    def setUp(self):
        import ship_when_green as S
        self.S = S

    def test_the_ci_wait_alerts_once_past_75_minutes(self):
        S = self.S
        clock = {"t": 0.0}
        said = []

        def run(argv, **kw):
            if argv[:2] == ["git", "rev-parse"]:
                return subprocess.CompletedProcess(argv, 0, SHA + "\n", "")
            return subprocess.CompletedProcess(argv, 0, "", "")
        runs = [{"workflowName": n, "headSha": SHA, "status": "in_progress", "createdAt": "x"} for n in S.CV.REQUIRED]

        def sleep(s):
            clock["t"] += s
        code = S.ship("v3864", run=run, fetch=lambda sha: runs, sleep=sleep, clock=lambda: clock["t"], say=said.append,
                      wait_s=100 * 60, preflight=lambda v, say: 0)
        self.assertEqual(code, 2)
        alerts = [l for l in said if "ALERT" in l]
        self.assertEqual(len(alerts), 1, "the 75-minute alert was said %d times" % len(alerts))
        self.assertIn("past the 75-minute max", alerts[0])
        self.assertIn(S.CV.REQUIRED[3], alerts[0], "the alert does not name what is still running")

    def _publish(self, rows_by_minute, wait_min=100):
        S = self.S
        clock = {"t": 0.0}
        said = []

        def watch(sha):
            m = int(clock["t"] // 60)
            row = rows_by_minute(m)
            return {"worked": True, "runs": [row] if row else [], "running": ["shard 6 (%d min)" % m] if m >= 75 else []}

        def sleep(s):
            clock["t"] += s
        code = S.watch_publish(SHA, watch, sleep, lambda: clock["t"], said.append, wait_min * 60)
        return code, said

    def test_after_the_main_push_publish_is_watched_and_alerts_at_75(self):
        code, said = self._publish(lambda m: {"name": PUBLISH, "status": "in_progress", "minutes": m}
                                   if m < 90 else {"name": PUBLISH, "status": "completed", "conclusion": "success",
                                                   "minutes": m})
        self.assertEqual(code, 0)
        alerts = [l for l in said if "ALERT" in l]
        self.assertEqual(len(alerts), 1)
        self.assertIn("shard 6", alerts[0])
        self.assertTrue(any("SUCCEEDED" in l and "past the 75-minute max" in l for l in said), said[-3:])

    def test_publish_red_or_unfinished_is_said_in_the_exit(self):
        code, _s = self._publish(lambda m: {"name": PUBLISH, "status": "completed", "conclusion": "failure", "minutes": 9})
        self.assertEqual(code, 1)
        code, said = self._publish(lambda m: {"name": PUBLISH, "status": "in_progress", "minutes": m}, wait_min=80)
        self.assertEqual(code, 2)
        self.assertIn("main IS pushed", said[-1])

    def test_the_cli_watches_publish(self):
        S = self.S
        seen = {}
        saved = S.ship
        try:
            S.ship = lambda version, **kw: seen.update(kw) or 0
            S.main(["v3864"])
            self.assertEqual(seen.get("watch_publish_s"), 100 * 60, "the CLI returns at the main push, unwatched")
            self.assertIs(seen.get("watch"), CW.watch)
            S.main(["v3864", "--no-watch"])
            self.assertIsNone(seen.get("watch_publish_s"))
        finally:
            S.ship = saved


RED_PROOF = [
    {"why": "REG-3213 - a run still going past 75 minutes is never called overrun (v3864: 2 h 50 min, no alert)",
     "file": "tv/ci_watch.py",
     "find": "        elif not done and m is not None and m >= limit:\n",
     "replace": "        elif False:\n",
     "matches": 1},
    {"why": "REG-3213 - a run that finished past the max reads green",
     "file": "tv/ci_watch.py",
     "find": "    elif slow:\n",
     "replace": "    elif False:\n",
     "matches": 1},
    {"why": "REG-3213 - a scheduled routine's red on main's head paints this version's CI red (crying wolf)",
     "file": "tv/ci_watch.py",
     "find": "\n            and r.get(\"event\") != \"schedule\"]\n",
     "replace": "]\n",
     "matches": 1},
    {"why": "REG-3213 - the eagle row reads a red CI as fine",
     "file": "tv/console_doctor.py",
     "find": "    if st in red:\n        return MISSING,",
     "replace": "    if False:\n        return MISSING,",
     "matches": 1},
    {"why": "REG-3213 - the eagle row reads an unread GitHub as fine",
     "file": "tv/console_doctor.py",
     "find": "    if rec.get(\"worked\") is not True or st in (None, \"unknown\"):\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "REG-3213 - the console never asks GitHub on its own",
     "file": "tv/control_app.py",
     "find": "                _ci_watch_tick()            # REG-3213",
     "replace": "                pass            # REG-3213",
     "matches": 1},
    {"why": "REG-3213 - the console asks GitHub on every tick (60 an hour unauthenticated is the whole budget)",
     "file": "tv/control_app.py",
     "find": "        if last is not None and now - last < _cw.CI_WATCH_EVERY_S:\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "REG-3213 - a test console calls GitHub every 5 minutes",
     "file": "tv/control_app.py",
     "find": "        if os.environ.get(\"TV_STUB\"):           # a test console never calls GitHub",
     "replace": "        if False:           # a test console never calls GitHub",
     "matches": 1},
    {"why": "REG-3213 - the ci/ wait never alerts at 75 minutes",
     "file": "tv/ship_when_green.py",
     "find": "        if not alerted and clock() - t0 >= CW.OVERRUN_MIN * 60:\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "REG-3213 - Publish is watched but never alerts past 75 minutes",
     "file": "tv/ship_when_green.py",
     "find": "        if not alerted and row and mins is not None and mins >= limit:\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "REG-3213 - the CLI returns at the main push and nothing watches Publish (v3864)",
     "file": "tv/ship_when_green.py",
     "find": "                watch_publish_s=None if a.no_watch else a.publish_wait_min * 60)",
     "replace": "                watch_publish_s=None)",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
