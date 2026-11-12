# -*- coding: utf-8 -*-
"""REG-3654 - OUR OWN CI MUST NEVER MAKE A SHIP OR PUBLISH QUEUE.

v3893 Publish run 42833420352 (main, created 16:22 IST) sat queued 22+ minutes
behind grok/ship-system runs, a superseded grok/v3894-merge agent-tests run,
and stale ci/proof-keys-dry-v3894 runs (proof-keys plus windows, from 15:34 IST).
Those were cancelled by hand at about 16:46 IST. The yield rule now covers
Publish and the window after a main push, cancels our own holders when a ship
or Publish has been queued more than ~2 minutes, and sweeps leftover dry runs
on superseded shas and any ci/*dry* name (those names are never used again).
"""
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import ship_yield as SY  # noqa: E402
import ship_when_green as SW  # noqa: E402
import shard_watch as SHW  # noqa: E402

PUBLISH = "Publish — gates, review, then deploy"
MAIN_SHA = "518744bfd4ed9ab1ee0712b311aa3c529dc6ab82"
# 16:22 IST = 14:22 UTC; 16:46 IST = 14:46 UTC (queued 24 min).
CREATED = "2026-11-10T14:22:28Z"
NOW = 1794321960.0  # 2026-11-10 14:46:00 UTC


def _run(branch, status, rid, name="CI", sha=None, created=None, conclusion=""):
    row = {"headBranch": branch, "status": status, "databaseId": rid, "name": name}
    if sha:
        row["headSha"] = sha
    if created:
        row["createdAt"] = created
    if conclusion:
        row["conclusion"] = conclusion
    return row


LIVE_PUBLISH = [
    _run("main", "queued", 42833420352, PUBLISH, sha=MAIN_SHA, created=CREATED),
]
COMPETING = [
    _run("grok/ship-system", "in_progress", 42836008011, "TV DIABLO — agent tests"),
    _run("grok/v3894-merge", "queued", 42824900000, "TV DIABLO — agent tests",
         sha="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"),
    _run("ci/proof-keys-dry-v3894", "in_progress", 42825683620,
         "proof-keys shards (ci/proof-keys-* only)", created="2026-11-10T13:34:00Z"),
]
SHIP = [
    _run("ci/proof-keys-v3893", "queued", 42816227617, "proof-keys shards (ci/proof-keys-* only)",
         created=CREATED),
]
MAIN_OTHER = [
    _run("main", "in_progress", 99, "Routine L — data integrity drift", sha=MAIN_SHA),
]


class _GH:
    def __init__(self, ok=True):
        self.ok = ok
        self.calls = []

    def __call__(self, cmd, **kw):
        self.calls.append(cmd)
        if cmd[:3] == ["gh", "run", "cancel"]:
            return subprocess.CompletedProcess(cmd, 0 if self.ok else 1, "",
                                               "" if self.ok else "cannot cancel")
        return subprocess.CompletedProcess(cmd, 1, "", "unexpected")


class TheLawHolds(unittest.TestCase):
    def test_a_dry_or_grok_push_is_refused_while_publish_is_live(self):
        for branch in ("dry/v3894", "grok/v3894-merge", "grok/ship-system"):
            ok, why = SY.may_push(branch, LIVE_PUBLISH)
            self.assertFalse(ok, "%s was allowed: %s" % (branch, why))
            self.assertIn("42833420352", why)

    def test_a_dry_push_is_refused_in_the_window_after_a_main_push(self):
        # Main just landed; Publish has not appeared in the run list yet.
        main = {"sha": MAIN_SHA, "current": True, "pushed_at": NOW - 30}
        ok, why = SY.may_push("grok/ship-system", COMPETING, main=main, now=NOW)
        self.assertFalse(ok, why)
        self.assertTrue(SY.awaiting_publish(COMPETING, main=main, now=NOW))

    def test_a_dry_push_is_allowed_once_publish_on_that_sha_has_finished(self):
        done = [_run("main", "completed", 42833420352, PUBLISH, sha=MAIN_SHA,
                     created=CREATED, conclusion="success")]
        main = {"sha": MAIN_SHA, "current": True, "pushed_at": NOW - 30}
        self.assertFalse(SY.awaiting_publish(done, main=main, now=NOW))
        ok, why = SY.may_push("grok/ship-system", done + COMPETING, main=main, now=NOW)
        self.assertTrue(ok, why)

    def test_a_routine_on_main_without_publish_does_not_count_as_live_publish(self):
        ok, why = SY.may_push("dry/v3894", MAIN_OTHER + COMPETING)
        self.assertTrue(ok, why)
        self.assertEqual(SY.live_publish_runs(MAIN_OTHER), [])

    def test_ci_and_main_are_never_held_even_when_publish_is_live(self):
        for branch in ("ci/claude-v3893", "ci/proof-keys-v3893", "main", "feature/foo"):
            ok, why = SY.may_push(branch, LIVE_PUBLISH + COMPETING)
            self.assertTrue(ok, "%s was held: %s" % (branch, why))

    def test_ci_dry_names_are_never_used_again(self):
        self.assertTrue(SY.is_forbidden_ci_dry("ci/proof-keys-dry-v3894"))
        self.assertTrue(SY.is_forbidden_ci_dry("ci/claude-dry-v3894"))
        self.assertFalse(SY.is_forbidden_ci_dry("ci/proof-keys-v3893"))
        ok, why = SY.may_push("ci/proof-keys-dry-v3894", [])
        self.assertFalse(ok, why)
        self.assertIn("never used again", why)

    def test_competing_runs_are_cancelled_when_publish_is_live_and_main_is_not(self):
        gh = _GH()
        ids = SY.cancel_competing(LIVE_PUBLISH + COMPETING + MAIN_OTHER + SHIP, gh)
        self.assertEqual(sorted(ids), [42824900000, 42825683620, 42836008011])
        cancelled = [c[3] for c in gh.calls if c[:3] == ["gh", "run", "cancel"]]
        self.assertEqual(sorted(cancelled), ["42824900000", "42825683620", "42836008011"])
        self.assertNotIn("42833420352", cancelled)
        self.assertNotIn("99", cancelled)
        self.assertNotIn("42816227617", cancelled)

    def test_a_queued_ship_or_publish_cancels_holders_and_names_the_lesson(self):
        gh = _GH()
        said = []
        ids = SY.yield_to_ship(run=gh, say=said.append, runs=LIVE_PUBLISH + COMPETING,
                               now=NOW, sweep=True)
        self.assertEqual(sorted(ids), [42824900000, 42825683620, 42836008011])
        self.assertTrue(SY.queued_priority_runs(LIVE_PUBLISH, NOW))
        blob = "\n".join(said)
        self.assertIn(SY.LESSON_ID, blob)
        self.assertIn("42833420352", blob)
        self.assertIn("REG-3654 QUEUED", blob)

    def test_a_publish_queued_with_nothing_running_blames_no_runner_of_ours(self):
        """REG-3732 (v3898's Publish, 11-11 22:40): GitHub had started none of the repo's 11 queued runs, and the line said
        our own runs held the runners. With nothing in progress it says so; with runs in progress it counts them."""
        said = []
        SY.yield_to_ship(run=_GH(), say=said.append, runs=LIVE_PUBLISH, now=NOW, sweep=True)
        blob = "\n".join(said)
        self.assertIn("NO run of this repo is in progress - GitHub has not started it", blob)
        self.assertNotIn("held runners", blob, "a queue nothing of ours holds was blamed on our runners")
        said = []
        SY.yield_to_ship(run=_GH(), say=said.append, runs=LIVE_PUBLISH + COMPETING, now=NOW, sweep=True)
        self.assertIn("2 run(s) of this repo held runners", "\n".join(said))

    def test_an_unread_in_progress_poll_is_unknown_never_none_running(self):
        """REG-3750 (the second eye on REG-3732, #231 11-12): fetch_live asks each status on its own and DROPPED a poll that
        threw, so a queued Publish beside an unread in-progress poll was told "NO run of this repo is in progress - GitHub
        has not started it" - a certainty built on a reading that never happened. Now the unread status travels and the
        count is UNKNOWN."""
        import json as _json

        class _R(object):
            def __init__(self, rc, out):
                self.returncode, self.stdout = rc, out

        def run(argv, **kw):
            if "--status" in argv:
                st = argv[argv.index("--status") + 1]
                if st == "in_progress":
                    raise OSError("gh timed out")
                return _R(0, _json.dumps(LIVE_PUBLISH if st == "queued" else []))
            if "--workflow" in argv:
                return _R(0, "[]")
            return _R(1, "")
        live = SY.fetch_live(run=run)
        self.assertEqual(live.unread, ["in_progress"], "a poll that threw was not named as unread")
        said = []
        SY.yield_to_ship(run=run, say=said.append, now=NOW, sweep=False)
        blob = "\n".join(said)
        self.assertIn("REG-3654 QUEUED", blob, "PREMISE: the queued Publish was not logged - the case would not distinguish")
        self.assertNotIn("NO run of this repo is in progress", blob, "an unread poll was spoken as nothing running")
        self.assertIn("UNKNOWN (the live runs were not read)", blob)

    def test_a_publish_queued_under_two_minutes_is_not_the_queued_lesson(self):
        fresh = [_run("main", "queued", 42833420352, PUBLISH, sha=MAIN_SHA,
                      created="2026-11-10T14:45:00Z")]
        self.assertEqual(SY.queued_priority_runs(fresh, NOW), [])
        self.assertTrue(SY.live_publish_runs(fresh))

    def test_the_sweeper_cancels_stale_dry_and_ci_dry_never_main_or_the_ship(self):
        old = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
        tip = "cccccccccccccccccccccccccccccccccccccccc"
        rows = [
            _run("dry/v3894", "in_progress", 21, "agent tests", sha=old),
            _run("dry/v3894", "queued", 22, "agent tests", sha=tip),
            _run("ci/proof-keys-dry-v3894", "queued", 23,
                 "proof-keys shards (ci/proof-keys-* only)", sha=old),
            _run("main", "queued", 42833420352, PUBLISH, sha=MAIN_SHA, created=CREATED),
            _run("ci/proof-keys-v3893", "queued", 24, "proof-keys shards (ci/proof-keys-* only)"),
            _run("grok/ship-system", "in_progress", 25, "agent tests", sha=old),
        ]
        stale = SY.stale_or_forbidden_runs(rows, tips={"dry/v3894": tip})
        self.assertEqual(sorted(_run_id(r) for r in stale), [21, 23])
        gh = _GH()
        ids = SY.sweep_stale(rows, gh, tips={"dry/v3894": tip})
        self.assertEqual(sorted(ids), [21, 23])
        cancelled = [c[3] for c in gh.calls if c[:3] == ["gh", "run", "cancel"]]
        self.assertNotIn("42833420352", cancelled)
        self.assertNotIn("24", cancelled)
        self.assertNotIn("25", cancelled)  # grok is not a dry leftover; only cancelled when priority is live

    def test_the_ship_protects_runners_while_it_watches_publish(self):
        src = _read("tv/ship_when_green.py")
        needle = "            SY.protect_priority(run=run, say=say, main=sha, now=clock())\n"
        self.assertIn(needle, src)
        call_at = src.index(needle)
        # Inside watch_publish, before the first watch(sha) of the loop.
        watch_def = src.index("def watch_publish(")
        first_watch = src.index("        got = watch(sha)\n", watch_def)
        self.assertLess(watch_def, call_at)
        self.assertLess(call_at, first_watch)
        # v3898 re-anchored (card #206): the call carries the ship's phase marker on its next line
        ret = "        return watch_publish(sha, watch or CW.watch, sleep, clock, say, watch_publish_s, run=run,\n"
        self.assertIn(ret, src)

    def test_the_live_shard_watch_protects_runners(self):
        src = _read("tv/shard_watch.py")
        needle = "            SY.protect_priority(run=run, say=say, now=clock())\n"
        self.assertIn(needle, src)
        self.assertLess(src.index("def watch_jobs_live("), src.index(needle))


def _run_id(r):
    return r["databaseId"]


def _read(rel):
    with open(os.path.join(SW.REPO, rel), encoding="utf-8") as fh:
        return fh.read()


class TheProofsNameOnePlace(unittest.TestCase):
    def test_each_find_matches_once(self):
        for p in RED_PROOF:
            with open(os.path.join(SW.REPO, p["file"]), encoding="utf-8") as fh:
                blob = fh.read()
            self.assertEqual(blob.count(p["find"]), p["matches"], p["why"])


RED_PROOF = [
    {"why": "REG-3750 - an unread in-progress poll is spoken as no run in progress again (the second eye on REG-3732)",
     "file": "tv/ship_yield.py",
     "find": "    running = (None if runs is None or \"in_progress\" in (unread or ())\n",
     "replace": "    running = (None if runs is None\n",
     "matches": 1},
    {"why": "REG-3732 - a Publish queued with nothing of ours running is blamed on our runners again",
     "file": "tv/ship_yield.py",
     "find": "    if running == 0:\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "REG-3654 - the Publish watch no longer frees runners for a live Publish",
     "file": "tv/ship_when_green.py",
     "find": "            SY.protect_priority(run=run, say=say, main=sha, now=clock())\n",
     "replace": "            None\n",
     "matches": 1},
    {"why": "REG-3654 - the ship no longer hands its gh runner to the Publish watch",
     "file": "tv/ship_when_green.py",
     "find": "        return watch_publish(sha, watch or CW.watch, sleep, clock, say, watch_publish_s, run=run,\n",   # v3898 re-anchored
     "replace": "        return watch_publish(sha, watch or CW.watch, sleep, clock, say, watch_publish_s,\n",
     "matches": 1},
    {"why": "REG-3654 - the live shard watch no longer yields runners when a ship is queued",
     "file": "tv/shard_watch.py",
     "find": "            SY.protect_priority(run=run, say=say, now=clock())\n",
     "replace": "            None\n",
     "matches": 1},
    {"why": "REG-3654 - a ci/*dry* name can be pushed again",
     "file": "tv/ship_yield.py",
     "find": "    if is_forbidden_ci_dry(name):\n",
     "replace": "    if False and is_forbidden_ci_dry(name):\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
