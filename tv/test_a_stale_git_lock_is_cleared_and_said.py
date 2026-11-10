#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""#64 — AN ABANDONED GIT LOCK WEDGED EVERY PULL FOR ELEVEN HOURS, AND NOTHING READ THE FAILURE.

MEASURED 2026-09-29 on his ALT: `.git/index.lock` dated 2026-09-28 14:09, 0 bytes, no git process
running. Every automatic pull after that failed with "Unable to create ... index.lock: File exists",
so the ALT stayed on v3521 for 11 h. `_pull_once` RECORDED it in `_PULL.say` ("the fast-forward did
not succeed ... UNKNOWN, NOT up to date") — and no doctor row read `_PULL`, the fleet beacon said
"clear to pull" off a cached origin view, and nothing cleared the lock. His words for the class:
"the windows needs proper care and attention"; "make sure nothing is running on my pc for nothing".

THE LAWS, each on a REAL git fixture in a temp dir (never his checkout):
  · a stale lock (empty, older than the bar, no git running) is cleared and the pull LANDS, with a
    receipt on the lane's record; and git's own error naming the lock is a second trigger
  · a YOUNG lock, a NON-EMPTY lock, a RUNNING git, or a probe that cannot answer -> the lock is
    left untouched and the lane SAYS why
  · the doctor row 'this checkout can update' reads MISSING after failures past the bar (reason and
    since when), OK after a success or a deliberate stand-down, UNKNOWN when nobody tried
  · the row reads the lane OVER THE WIRE, and /api/status publishes it under the key the row reads
  · the fleet beacon's pull.why says the pulls are failing instead of "clear to pull"

THE FOLLOW-UP LAWS (the review of #64, all four findings reproduced before fixing):
  · an update SIGKILLed mid-checkout (a 0-byte lock older than the bar beside a dirty tree) is its own
    outcome, 'interrupted' - named with the lock and the file count, the lock NEVER removed, nothing
    merged - and the doctor row reads it MISSING, the fleet beacon names it; a dirty tree with no lock,
    a young lock or a non-empty lock is still an ordinary stand-down
  · the root cause: no console git takes an OPTIONAL lock (GIT_OPTIONAL_LOCKS=0 on the one door), so a
    read of the tree killed by its timeout cannot leave index.lock behind - checked on the env of every
    status site AND on a real temp repo, where a plain status is first SEEN taking the lock
  · one pull at a time: both doors wait on the one lock, and a lock replaced between the judge's two
    looks (same bytes, same mtime, a different inode) is left alone

⚠ The git-running probe is stubbed in the lock cases: a real `pgrep -x git` on his Mac answers
about whatever git HE is running, and a verdict that depends on his machine is not a law.
[[feedback-fixtures-never-touch-live-data]] [[the-unjoined-end]] [[unknown-stays-unknown]]
"""
import ast
import io
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import fixture_tmp as _fx_tmp     # noqa: E402  - this run's scratch dirs leave with it
_fx_tmp.contain()
import control_app as ca          # noqa: E402
import console_doctor as cd       # noqa: E402

_PULL0 = dict(ca._PULL)

# git must not read his global/system config (pull.rebase, signing, hooks) inside the fixture
_GIT_ENV = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0"}
_ID = ["-c", "user.name=law", "-c", "user.email=law@example.invalid", "-c", "commit.gpgsign=false"]


def _git(cwd, *args):
    r = subprocess.run(["git"] + _ID + list(args), cwd=cwd, capture_output=True, text=True,
                       timeout=30, env=dict(os.environ, **_GIT_ENV))
    if r.returncode != 0:
        raise AssertionError("fixture git %s failed: %s" % (" ".join(args), r.stderr.strip()[-200:]))
    return (r.stdout or "").strip()


def _fixture():
    """origin (bare) <- seed pushes 2 commits; clone holds only the first. -> (root, clone, origin_head)"""
    root = tempfile.mkdtemp(prefix="tvd-gitlock-")
    origin = os.path.join(root, "origin.git")
    seed = os.path.join(root, "seed")
    clone = os.path.join(root, "clone")
    _git(root, "-c", "init.defaultBranch=main", "init", "-q", "--bare", origin)
    _git(origin, "config", "core.autocrlf", "false")  # #107 REG-3626 - the fixture's bytes, not the PC's git default
    _git(root, "-c", "init.defaultBranch=main", "init", "-q", seed)
    _git(seed, "config", "core.autocrlf", "false")  # #107 REG-3626 - the fixture's bytes, not the PC's git default
    with open(os.path.join(seed, "f.txt"), "w") as fh:
        fh.write("one\n")
    _git(seed, "add", "f.txt")
    _git(seed, "commit", "-q", "-m", "one")
    _git(seed, "push", "-q", origin, "HEAD:refs/heads/main")
    _git(root, "clone", "-q", "--branch", "main", origin, clone)
    with open(os.path.join(seed, "f.txt"), "w") as fh:
        fh.write("two\n")
    _git(seed, "commit", "-q", "-am", "two")
    _git(seed, "push", "-q", origin, "HEAD:refs/heads/main")
    return root, clone, _git(seed, "rev-parse", "--short", "HEAD")


def _plant(clone, age_s, body=b""):
    lk = os.path.join(clone, ".git", "index.lock")
    with open(lk, "wb") as fh:
        fh.write(body)
    t = time.time() - age_s
    os.utime(lk, (t, t))
    return lk, int(t * 1000)


class _Base(unittest.TestCase):

    def setUp(self):
        # REG-2360 - inside a git hook GIT_DIR points at the REAL repo and beats cwd=: the fixture's
        # `git init --bare` then rewrites the real config to core.bare=true. Dropped for THIS test only, before the
        # fixture is built; addCleanup (which runs after tearDown) puts them back.
        _gitenv = {_k: os.environ.pop(_k) for _k in list(os.environ) if _k.startswith("GIT_")}
        self.addCleanup(os.environ.update, _gitenv)
        self.root, self.clone, self.origin_head = _fixture()
        self._env = mock.patch.dict(os.environ, _GIT_ENV)
        self._env.start()
        os.environ.pop("TV_NO_AUTO_PULL", None)
        self._repo = mock.patch.object(ca, "REPO", self.clone)
        self._repo.start()
        ca._PULL.clear()
        ca._PULL.update(_PULL0)
        self.seen = []
        self._real_run = ca._git_run

        def _counting(argv, **kw):
            self.seen.append(" ".join(list(argv)[1:3]))
            return self._real_run(argv, **kw)
        self._run = mock.patch.object(ca, "_git_run", _counting)
        self._run.start()

    def tearDown(self):
        self._run.stop()
        self._repo.stop()
        self._env.stop()
        ca._PULL.clear()
        ca._PULL.update(_PULL0)
        shutil.rmtree(self.root, ignore_errors=True)

    def head(self):
        return _git(self.clone, "rev-parse", "--short", "HEAD")

    def probe(self, answer, how):
        return mock.patch.object(ca, "_git_running_here", lambda: (answer, how))


class TestAStaleLockIsClearedAndThePullLands(_Base):

    def test_BASELINE_the_fixture_reproduces_the_ALT(self):
        """Without this, every case below could pass on a fixture where a lock blocks nothing."""
        _plant(self.clone, 20 * 60)
        _git(self.clone, "fetch", "-q", "origin", "main")
        r = subprocess.run(["git", "merge", "--ff-only", "origin/main"], cwd=self.clone,
                           capture_output=True, text=True, timeout=30, env=dict(os.environ, **_GIT_ENV))
        self.assertNotEqual(r.returncode, 0, "a held index.lock did not block the fast-forward")
        self.assertIn("index.lock", r.stderr, "git's refusal does not name the lock: %r" % r.stderr)
        self.assertTrue(ca._names_index_lock(r))
        self.assertTrue(ca._git_err_line(r).lower().startswith("error:"),
                        "the reason picked is git's advice, not its error: %r" % ca._git_err_line(r))

    def test_a_stale_lock_is_cleared_and_the_pull_lands(self):
        lk, planted_ms = _plant(self.clone, 20 * 60)
        with self.probe(False, "stub: no git running"):
            out = ca._pull_once()
        self.assertIs(out, True, "the pull did not land: %r" % ca._PULL.get("say"))
        self.assertFalse(os.path.exists(lk), "the abandoned lock is still there")
        self.assertEqual(self.head(), self.origin_head, "HEAD did not reach origin/main")
        self.assertEqual(self.seen.count("merge --ff-only"), 1,
                         "the lock was cleared only AFTER a failed fast-forward (%s) — the check "
                         "before the fetch is not running" % self.seen)
        self.assertEqual(ca._PULL.get("outcome"), "pulled")
        self.assertIsNone(ca._PULL.get("failSince"))
        rec = ca._PULL.get("lockCleared") or {}
        self.assertIn("cleared a stale git lock", rec.get("say") or "", "no receipt: %r" % rec)
        self.assertEqual(rec.get("lockMtime"), planted_ms, "the receipt does not carry the lock's time")
        self.assertTrue(isinstance(rec.get("at"), int) and rec["at"] > planted_ms)
        self.assertIn("cleared a stale git lock", ca._PULL.get("say") or "",
                      "the lane's own sentence hides that it removed a lock")

    def test_a_lock_that_appears_AFTER_the_check_is_cleared_when_git_names_it(self):
        """The second trigger: git's own error naming index.lock (a lock left between the check and the merge)."""
        planted = {}
        real = self._real_run

        def _plant_at_merge(argv, **kw):
            key = " ".join(list(argv)[1:3])
            self.seen.append(key)
            if key == "merge --ff-only" and not planted:
                planted["lk"] = _plant(self.clone, 20 * 60)[0]
            return real(argv, **kw)
        with mock.patch.object(ca, "_git_run", _plant_at_merge), self.probe(False, "stub: none"):
            out = ca._pull_once()
        self.assertTrue(planted, "the fixture never planted its lock")
        self.assertIs(out, True, "the pull did not land: %r" % ca._PULL.get("say"))
        self.assertFalse(os.path.exists(planted["lk"]), "git named the lock and it was not cleared")
        self.assertEqual(self.seen.count("merge --ff-only"), 2, "expected one refused + one retried "
                         "fast-forward, saw %s" % self.seen)
        self.assertIn("cleared a stale git lock", (ca._PULL.get("lockCleared") or {}).get("say") or "")

    def test_the_in_app_update_door_clears_it_too(self):
        lk, _ = _plant(self.clone, 20 * 60)
        with self.probe(False, "stub: none"):
            out = ca.fleet_pull()
        self.assertTrue(out.get("ok") and out.get("pulled"), "the /api/update door did not pull: %r" % out)
        self.assertFalse(os.path.exists(lk))
        self.assertEqual(self.seen.count("pull --ff-only"), 1,
                         "the door cleared the lock only after a refused pull: %s" % self.seen)
        self.assertIn("cleared a stale git lock", out.get("lock") or "")
        self.assertIn("cleared a stale git lock", (ca._PULL.get("lockCleared") or {}).get("say") or "")


class TestAnyOtherLockIsLeftAndSaid(_Base):

    def _left(self, lk, body):
        self.assertTrue(os.path.exists(lk), "a lock this law must LEAVE was removed")
        with open(lk, "rb") as fh:
            self.assertEqual(fh.read(), body, "the lock's bytes changed")
        self.assertNotEqual(self.head(), self.origin_head, "HEAD moved past a lock that stayed")
        self.assertEqual(ca._PULL.get("outcome"), "failed")
        self.assertIsNone(ca._PULL.get("lockCleared"), "a receipt for a clearing that did not happen")
        return ca._PULL.get("say") or ""

    def test_a_YOUNG_lock_is_left_and_said(self):
        lk, _ = _plant(self.clone, 5)
        with self.probe(False, "stub: none"):
            self.assertIsNone(ca._pull_once())
            since = ca._PULL.get("failSince")
            self.assertIsNone(ca._pull_once())
        say = self._left(lk, b"")
        self.assertIn("left the git lock", say)
        self.assertIn("the bar is %ds" % ca._GIT_LOCK_STALE_S, say, "the age refusal is not said: %s" % say)
        self.assertEqual(ca._PULL.get("failures"), 2)
        self.assertEqual(ca._PULL.get("failSince"), since, "a second failure restarted the clock")
        self.assertIn("index.lock", ca._PULL.get("lastErr") or "", "the reason lost the lock")

    def test_a_NON_EMPTY_lock_is_left_and_said(self):
        lk, _ = _plant(self.clone, 20 * 60, b"0123456789")
        with self.probe(False, "stub: none"):
            self.assertIsNone(ca._pull_once())
        say = self._left(lk, b"0123456789")
        self.assertIn("holds 10 bytes", say, "the size refusal is not said: %s" % say)

    def test_a_RUNNING_git_leaves_the_lock(self):
        lk, _ = _plant(self.clone, 20 * 60)
        with self.probe(True, "stub: pgrep -x git found pid 4242"):
            self.assertIsNone(ca._pull_once())
        say = self._left(lk, b"")
        self.assertIn("a git process is running", say)
        self.assertIn("pid 4242", say, "the lane does not name what it saw running")

    def test_a_probe_that_CANNOT_ANSWER_leaves_the_lock(self):
        lk, _ = _plant(self.clone, 20 * 60)
        with self.probe(None, "stub: pgrep could not run"):
            self.assertIsNone(ca._pull_once())
        say = self._left(lk, b"")
        self.assertIn("could not be asked", say)


def _half_update(clone):
    """What a fast-forward SIGKILLed mid-checkout leaves: origin's bytes in a tracked file, HEAD unmoved."""
    with open(os.path.join(clone, "f.txt"), "w") as fh:
        fh.write("two\n")


class TestAnInterruptedUpdateIsNotAStandDown(_Base):
    """#64 follow-up — the review's repro: a bare origin + a 20k-file clone, origin one commit ahead,
    `git merge --ff-only origin/main` SIGKILLed 150 ms after index.lock appeared -> exit -9, a 0-byte
    lock left, hundreds of modified files, and the row said OK. Re-measured here on 4,000 files (lock
    seen at 0.22 s, SIGKILL 50 ms later): exit -9, a 0-byte lock, 113 modified tracked files. The state
    is CONSTRUCTED below (an old 0-byte lock + a modified tracked file) because a kill timed against a
    checkout is a race on a CI runner, and a law that depends on winning a race is not a law."""

    def test_BASELINE_git_still_reads_the_half_written_tree_beside_the_lock(self):
        """Without this the lane would never reach its DIRTY branch and every case below is moot."""
        _plant(self.clone, 20 * 60)
        _half_update(self.clone)
        r = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=self.clone,
                           capture_output=True, text=True, timeout=30, env=dict(os.environ, **_GIT_ENV))
        self.assertEqual(r.returncode, 0, "git status refused beside a held lock: %r" % r.stderr)
        self.assertIn("f.txt", r.stdout, "the modified tracked file is not listed")

    def test_the_lane_records_INTERRUPTED_and_touches_nothing(self):
        lk, planted_ms = _plant(self.clone, 20 * 60)
        _half_update(self.clone)
        with self.probe(False, "stub: none"):
            out = ca._pull_once()
        self.assertIsNone(out, "an interrupted update read as a pull that answered")
        self.assertEqual(ca._PULL.get("outcome"), "interrupted",
                         "a tree cut off mid-checkout was filed as %r: %r"
                         % (ca._PULL.get("outcome"), ca._PULL.get("say")))
        say = ca._PULL.get("say") or ""
        self.assertIn("CUT OFF mid-checkout", say)
        self.assertIn("index.lock", say, "the sentence does not name the lock")
        self.assertIn("1 modified tracked file", say, "the sentence does not name the files")
        self.assertTrue(os.path.exists(lk), "report only: the lock was REMOVED")
        self.assertEqual(os.path.getsize(lk), 0)
        self.assertNotIn("fetch origin", self.seen, "it fetched on the interrupted branch: %s" % self.seen)
        self.assertNotIn("merge --ff-only", self.seen, "it merged on the interrupted branch: %s" % self.seen)
        self.assertNotEqual(self.head(), self.origin_head, "HEAD moved on a report-only branch")
        self.assertEqual((ca._PULL.get("interrupted") or {}).get("lockMtime"), planted_ms)
        self.assertEqual(ca._PULL.get("failures"), 1, "an interrupted update does not run the clock")

    def test_the_doctor_row_and_the_fleet_say_INTERRUPTED(self):
        _plant(self.clone, 20 * 60)
        _half_update(self.clone)
        with self.probe(False, "stub: none"):
            ca._pull_once()
        st, why = cd.pull_lane_verdict(ca.pull_state())
        self.assertEqual(st, cd.MISSING, "an update cut off mid-checkout graded %s: %s" % (st, why))
        self.assertIn("INTERRUPTED", why)
        self.assertIn("index.lock", why, "the row does not name the lock: %s" % why)
        self.assertIn("modified tracked file", why, "the row does not name the files: %s" % why)
        with mock.patch.object(ca, "fleet_origin_status",
                               lambda *a, **k: {"ok": True, "behind": 1, "dirty": True}):
            rep = ca._pull_report()
        self.assertIs(rep.get("can"), False)
        self.assertIn("CUT OFF", rep.get("why") or "", "the fleet still says 'local tracked edits': %r" % rep)

    def test_the_in_app_update_door_says_it_too(self):
        lk, _ = _plant(self.clone, 20 * 60)
        _half_update(self.clone)
        with self.probe(False, "stub: none"):
            out = ca.fleet_pull()
        self.assertEqual(out.get("outcome"), "interrupted", "/api/update said: %r" % out.get("msg"))
        self.assertIn("CUT OFF mid-checkout", out.get("msg") or "")
        self.assertIn("1 modified tracked file", out.get("msg") or "")
        self.assertFalse(out.get("ok"))
        self.assertTrue(os.path.exists(lk), "report only: the door REMOVED the lock")
        self.assertNotIn("pull --ff-only", self.seen, "the door pulled over a half-written tree")
        self.assertEqual(ca._PULL.get("outcome"), "interrupted", "the door's finding is not on the lane")

    def test_an_ordinary_dirty_tree_is_still_a_stand_down(self):
        """The other side of the line: no lock, a YOUNG lock, or a NON-EMPTY lock beside edits is 'dirty'."""
        for age, body in ((None, b""), (5, b""), (20 * 60, b"0123456789")):
            ca._PULL.clear()
            ca._PULL.update(_PULL0)
            lk = os.path.join(self.clone, ".git", "index.lock")
            if os.path.exists(lk):
                os.remove(lk)
            if age is not None:
                _plant(self.clone, age, body)
            _half_update(self.clone)
            with self.probe(False, "stub: none"):
                self.assertIs(ca._pull_once(), False, "age=%r bytes=%d" % (age, len(body)))
            self.assertEqual(ca._PULL.get("outcome"), "dirty",
                             "age=%r bytes=%d filed as %r" % (age, len(body), ca._PULL.get("outcome")))
            self.assertEqual(cd.pull_lane_verdict(ca.pull_state())[0], cd.OK)


class TestNoConsoleGitTakesAnOptionalLock(_Base):
    """#64 follow-up — the root cause: a read-only `git status` takes index.lock on its own (to write a
    refreshed index back), and every console git call is subprocess.run(timeout=N), which SIGKILLs git
    with no cleanup. GIT_OPTIONAL_LOCKS=0 on the ONE door means no read of this tree can leave a lock."""

    def test_every_console_git_spawn_carries_GIT_OPTIONAL_LOCKS_0(self):
        seen_env = []

        class _R(object):
            returncode, stdout, stderr = 0, "", ""

        def _spawn(argv, **kw):
            seen_env.append((list(argv), dict(kw.get("env") or {})))
            r = _R()
            if not kw.get("text"):
                r.stdout, r.stderr = b"", b""
            return r
        self._run.stop()                    # the REAL door, with only the process spawn stubbed
        try:
            with mock.patch.object(ca._git_quiet.subprocess, "run", _spawn), \
                    self.probe(False, "stub: none"):
                ca._git_tracked_dirty()
                ca._tree_is_mid_edit()
                ca._pull_once()
                ca.fleet_pull()
                ca._git_run(["git", "status"], env={"LAW_CALLER": "1"})
        finally:
            self._run.start()
        # _git_tracked_dirty, _tree_is_mid_edit, _pull_once's and fleet_pull's status, the caller's own
        statuses = [a for a, _ in seen_env if "status" in a]
        self.assertGreaterEqual(len(statuses), 5, "the status sites were not all reached: %s"
                                % [" ".join(a[1:4]) for a, _ in seen_env])
        bad = [" ".join(a[:4]) for a, e in seen_env if e.get("GIT_OPTIONAL_LOCKS") != "0"]
        self.assertEqual(bad, [], "git spawned WITHOUT GIT_OPTIONAL_LOCKS=0: %s" % bad)
        self.assertEqual(seen_env[-1][1].get("LAW_CALLER"), "1", "the caller's own env was dropped")

    def _many_file_repo(self, n=600):
        repo = os.path.join(self.root, "optlock")
        _git(self.root, "-c", "init.defaultBranch=main", "init", "-q", repo)
        _git(repo, "config", "core.autocrlf", "false")  # #107 REG-3626 - the fixture's bytes, not the PC's git default
        for i in range(n):
            with open(os.path.join(repo, "f%04d.txt" % i), "w") as fh:
                fh.write("x\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "files")
        return repo, n

    def _status_under_watch(self, repo, n, spawn):
        """Touch every mtime (so status has an index refresh to write), run `spawn`, poll for the lock.
        -> (lock seen while it ran, index rewritten)"""
        t = time.time() - 30 - len(self._stamps)
        self._stamps.append(t)
        for i in range(n):
            os.utime(os.path.join(repo, "f%04d.txt" % i), (t, t))
        idx = os.path.join(repo, ".git", "index")
        lk = idx + ".lock"
        s0 = os.stat(idx)
        seen, stop = [False], [False]

        def _poll():
            while not stop[0]:
                if os.path.exists(lk):
                    seen[0] = True
        th = threading.Thread(target=_poll, daemon=True)
        th.start()
        try:
            r = spawn()
        finally:
            stop[0] = True
            th.join(5)
        self.assertEqual(r.returncode, 0, "git status failed: %r" % (r.stderr,))
        s1 = os.stat(idx)
        return seen[0], (s0.st_ino != s1.st_ino or s0.st_mtime_ns != s1.st_mtime_ns)

    def test_a_real_git_status_through_the_door_never_creates_index_lock(self):
        repo, n = self._many_file_repo()
        self._stamps = []
        env = dict(os.environ, **_GIT_ENV)
        env.pop("GIT_OPTIONAL_LOCKS", None)
        # PREMISE: a plain status DOES take the lock, and this instrument can see it - or the absence
        # below is the absence of a look. Up to five tries: a fast machine may win one race.
        took = [self._status_under_watch(repo, n, lambda: subprocess.run(
            ["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True, timeout=30,
            env=env)) for _ in range(5)]
        self.assertTrue(any(s or w for s, w in took),
                        "premise failed: a plain git status never took index.lock here (%s)" % took)
        with mock.patch.dict(os.environ, {}):
            os.environ.pop("GIT_OPTIONAL_LOCKS", None)
            quiet = [self._status_under_watch(repo, n, lambda: ca._git_quiet.run(
                ["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True,
                timeout=30)) for _ in range(3)]
        self.assertEqual(quiet, [(False, False)] * 3,
                         "a git status through the ONE door took index.lock (seen, rewritten): %s" % quiet)


class TestOnePullAtATime(_Base):
    """#64 follow-up — the drift thread's _pull_once and /api/update's fleet_pull both judge and REMOVE
    a stale lock, and nothing kept them apart."""

    def test_a_lock_REPLACED_between_the_two_looks_is_left(self):
        """Same 0 bytes, same mtime, a DIFFERENT file: another git took the lock anew. It is left."""
        lk, _ = _plant(self.clone, 20 * 60)
        st0 = os.stat(lk)
        swapped = {}

        def _probe_that_swaps():
            tmp = lk + ".law-new"
            with open(tmp, "wb"):
                pass
            os.utime(tmp, ns=(st0.st_atime_ns, st0.st_mtime_ns))
            os.replace(tmp, lk)            # the old file still existed, so the inode cannot be reused
            swapped["st"] = os.stat(lk)
            return False, "stub: none"
        with mock.patch.object(ca, "_git_running_here", _probe_that_swaps):
            out = ca._clear_stale_git_lock(self.clone)
        st1 = swapped.get("st")
        self.assertIsNotNone(st1, "the probe never ran, so the re-stat was never reached")
        self.assertEqual((st1.st_size, st1.st_mtime), (0, st0.st_mtime),
                         "premise: only the inode may differ, or the size/mtime clause decides this")
        self.assertNotEqual(st1.st_ino, st0.st_ino, "premise: the replacement kept the inode")
        self.assertFalse(out.get("cleared"), "a lock replaced between the checks was removed: %r" % out)
        self.assertTrue(os.path.exists(lk), "the replacement lock is gone")
        self.assertIn("changed while it was being judged", out.get("say") or "")

    def _held_door(self, door):
        """Hold the pull lock, start `door` on a thread, and see it wait. -> (git calls while held, after)"""
        box = {}
        th = threading.Thread(target=lambda: box.setdefault("out", door()), daemon=True)
        ca._GIT_PULL_DOOR.acquire()
        try:
            th.start()
            time.sleep(0.8)
            during = list(self.seen)
            alive = th.is_alive()
        finally:
            ca._GIT_PULL_DOOR.release()
        th.join(60)
        self.assertFalse(th.is_alive(), "the door never finished after the lock was released")
        self.assertTrue(alive, "the door finished while another pull held the checkout")
        return during, list(self.seen)

    def test_both_doors_wait_on_the_ONE_lock(self):
        with self.probe(False, "stub: none"):
            for name in ("_pull_once", "fleet_pull"):
                del self.seen[:]
                during, after = self._held_door(getattr(ca, name))
                self.assertEqual(during, [], "%s ran git while the other door held the checkout: %s"
                                 % (name, during))
                self.assertTrue(after, "%s never ran git after the lock was released" % name)


class TestTheConsolesOwnRecordIsNotAnEdit(_Base):
    """★ REG-1865 — his ALT sat on v3595, 123 behind, with pull outcome "dirty": "local tracked edits are present, so
    this machine is NOT auto-pulling". Its one edit was ` M tv/.status_worst.json`, the tracked record the console
    rewrites on its slowest request. Real git: origin (bare) is one commit ahead on f.txt, the clone tracks the
    record and has rewritten it. The record is never reset or checked out - git's own fast-forward decides."""

    REC = os.path.join("tv", ".status_worst.json")

    def setUp(self):
        _Base.setUp(self)
        seed = os.path.join(self.root, "seed")
        os.makedirs(os.path.join(seed, "tv"), exist_ok=True)
        with open(os.path.join(seed, self.REC), "w") as fh:
            fh.write('{"totalMs": 1773092.2}\n')
        _git(seed, "add", self.REC)
        _git(seed, "commit", "-q", "-m", "the kept record")
        _git(seed, "push", "-q", os.path.join(self.root, "origin.git"), "HEAD:refs/heads/main")
        # the clone takes everything up to the record, then origin moves one commit on f.txt only
        _git(self.clone, "pull", "-q", "--ff-only", "origin", "main")
        with open(os.path.join(seed, "f.txt"), "w") as fh:
            fh.write("three\n")
        _git(seed, "commit", "-q", "-am", "three")
        _git(seed, "push", "-q", os.path.join(self.root, "origin.git"), "HEAD:refs/heads/main")
        self.origin_head = _git(seed, "rev-parse", "--short", "HEAD")
        self.seed = seed
        self.mine = '{"totalMs": 25414039.5}\n'
        with open(os.path.join(self.clone, self.REC), "w") as fh:
            fh.write(self.mine)

    def _record(self):
        with open(os.path.join(self.clone, self.REC)) as fh:
            return fh.read()

    def test_the_record_alone_pulls_and_stays_his(self):
        self.assertEqual(_git(self.clone, "status", "--porcelain", "--untracked-files=no"),
                         "M tv/.status_worst.json", "PREMISE: the record is not the only edit")
        with self.probe(False, "stub: no git running"):
            out = ca._pull_once()
        self.assertIs(out, True, "the console's own record held the pull: %r" % ca._PULL.get("say"))
        self.assertEqual(ca._PULL.get("outcome"), "pulled")
        self.assertEqual(self.head(), self.origin_head, "HEAD did not reach origin/main")
        self.assertEqual(self._record(), self.mine, "the pull reset or checked out his record")

    def test_the_record_and_a_real_edit_is_still_dirty(self):
        with open(os.path.join(self.clone, "f.txt"), "w") as fh:
            fh.write("his edit\n")
        with self.probe(False, "stub: no git running"):
            out = ca._pull_once()
        self.assertIs(out, False, "a real edit beside the record was pulled over: %r" % ca._PULL.get("say"))
        self.assertEqual(ca._PULL.get("outcome"), "dirty")
        self.assertEqual(self._record(), self.mine)

    def test_origin_changing_the_record_is_refused_by_git_and_the_record_stays(self):
        with open(os.path.join(self.seed, self.REC), "w") as fh:
            fh.write('{"totalMs": 1.0}\n')
        _git(self.seed, "commit", "-q", "-am", "origin moves the record")
        _git(self.seed, "push", "-q", os.path.join(self.root, "origin.git"), "HEAD:refs/heads/main")
        before = self.head()
        with self.probe(False, "stub: no git running"):
            out = ca._pull_once()
        self.assertIsNone(out, "git's own refusal was not reported as a failed fast-forward")
        self.assertEqual(ca._PULL.get("outcome"), "failed")
        self.assertEqual(self.head(), before)
        self.assertEqual(self._record(), self.mine, "his record was overwritten")

    def test_an_unaskable_rule_is_an_unknown_fleet_flag_and_a_blocked_pull(self):
        """REG-1898 - the rule raising: the fleet's dirty flag is None (UNKNOWN, never clean), the beacon says so, the
        lane and the in-app door do not pull, and his record is untouched."""
        import self_prove as SP

        def _boom(*a, **k):
            raise RuntimeError("the rule broke")
        before = self.head()
        with mock.patch.object(SP, "_edits_beyond_own_records", _boom):
            self.assertIsNone(ca._git_tracked_dirty(), "the fleet row read an unaskable rule as clean or dirty")
            with mock.patch.object(ca, "fleet_origin_status", lambda *a, **k: {"ok": True, "behind": 1, "dirty": None}):
                rep = ca._pull_report() or {}
            self.assertIsNone(rep.get("can"), "the beacon called an UNKNOWN tree clear to pull: %r" % (rep,))
            self.assertIn("UNKNOWN", rep.get("why") or "")
            with self.probe(False, "stub: no git running"):
                out = ca._pull_once()
            self.assertIs(out, False, "the lane pulled over a rule it could not ask: %r" % ca._PULL.get("say"))
            r = ca.fleet_pull()
            self.assertFalse(r.get("pulled"), "the in-app door pulled over a rule it could not ask")
        self.assertEqual(self.head(), before)
        self.assertEqual(self._record(), self.mine)

    def test_the_in_app_door_and_the_fleet_row_use_the_same_rule(self):
        self.assertFalse(ca._git_tracked_dirty(), "the fleet row calls the console's own record a dirty tree")
        r = ca.fleet_pull()
        self.assertTrue(r.get("ok") and r.get("pulled"), "the in-app update door refused over the record: %r" % (r,))
        self.assertEqual(self._record(), self.mine)


class TestTheRunningProbeAnswersThreeWays(unittest.TestCase):

    def test_pgrep_exit_codes_map_to_three_answers(self):
        class _R(object):
            def __init__(self, rc, out=""):
                self.returncode, self.stdout, self.stderr = rc, out, ""
        with mock.patch.object(ca, "IS_WIN", False):
            for rc, want in ((0, True), (1, False), (2, None)):
                with mock.patch.object(ca.subprocess, "run", lambda *a, **k: _R(rc, "4242\n")):
                    self.assertIs(ca._git_running_here()[0], want, "pgrep exit %d" % rc)

            def _boom(*a, **k):
                raise FileNotFoundError("pgrep")
            with mock.patch.object(ca.subprocess, "run", _boom):
                self.assertIsNone(ca._git_running_here()[0], "a missing pgrep read as 'no git'")

    def test_windows_asks_the_process_table_not_tasklist(self):
        for procs, want in (({4: "explorer.exe", 7: "git.exe"}, True),
                            ({4: "explorer.exe", 9: "git-remote-https.exe"}, True),
                            ({4: "explorer.exe", 5: "D2R.exe"}, False),
                            (None, None), ({}, None)):
            stub = types.SimpleNamespace(_win_process_names=lambda p=procs: p)
            with mock.patch.object(ca, "IS_WIN", True), \
                    mock.patch.dict(sys.modules, {"tv_diablo": stub}):
                self.assertIs(ca._git_running_here()[0], want, "snapshot %r" % (procs,))


class TestTheDoctorRowReadsTheLane(unittest.TestCase):
    NOW = 1790000000000

    def lane(self, **kw):
        base = {"checked": self.NOW, "on": True, "outcome": None, "failSince": None, "failures": 0,
                "failBarS": 3600, "now": self.NOW, "lastTs": None, "say": "",
                "lockCleared": None}
        base.update(kw)
        return base

    def test_failing_PAST_the_bar_is_MISSING_with_the_reason_and_since_when(self):
        st, why = cd.pull_lane_verdict(self.lane(
            outcome="failed", failSince=self.NOW - 2 * 3600 * 1000, failures=24,
            say="the fast-forward did not succeed (exit 128: error: Unable to create "
                "'C:/d2r/.git/index.lock': File exists.) — UNKNOWN, NOT up to date"))
        self.assertEqual(st, cd.MISSING, why)
        self.assertIn("index.lock", why, "the reason is not named")
        self.assertIn("since ", why, "since when is not named")
        self.assertIn("24 attempt", why)

    def test_failing_UNDER_the_bar_is_not_yet_a_finding(self):
        st, why = cd.pull_lane_verdict(self.lane(outcome="failed", failSince=self.NOW - 10 * 60 * 1000,
                                                 failures=2, say="the fetch did not succeed"))
        self.assertEqual(st, cd.UNKNOWN, "a ten-minute blip graded as %s: %s" % (st, why))

    def test_a_pull_that_worked_is_OK(self):
        for oc in ("pulled", "level"):
            st, why = cd.pull_lane_verdict(self.lane(outcome=oc, lastTs=self.NOW - 60000,
                                                     say="already level with origin/main at abc1234"))
            self.assertEqual(st, cd.OK, "%s -> %s: %s" % (oc, st, why))

    def test_a_deliberate_stand_down_is_OK_and_says_so(self):
        st, why = cd.pull_lane_verdict(self.lane(on=False, outcome="off",
                                                 say="auto-pull is switched off here by TV_NO_AUTO_PULL"))
        self.assertEqual(st, cd.OK)
        self.assertIn("TV_NO_AUTO_PULL", why)
        st, why = cd.pull_lane_verdict(self.lane(outcome="dirty", say="local tracked edits are present"))
        self.assertEqual(st, cd.OK)
        self.assertIn("ON PURPOSE", why)

    def test_nobody_tried_is_UNKNOWN_never_OK(self):
        self.assertEqual(cd.pull_lane_verdict(self.lane(checked=None))[0], cd.UNKNOWN)
        self.assertEqual(cd.pull_lane_verdict(None)[0], cd.UNKNOWN)

    def test_the_row_asks_the_console_OVER_THE_WIRE(self):
        failing = self.lane(outcome="failed", failSince=self.NOW - 3 * 3600 * 1000, failures=30,
                            say="the fast-forward did not succeed (index.lock)")
        with mock.patch.object(cd, "_get", lambda path, timeout=4: {cd._PULL_LANE_KEY: failing}):
            self.assertEqual(cd._check_this_checkout_can_update()[0], cd.MISSING)
        with mock.patch.object(cd, "_get", lambda path, timeout=4: None):
            self.assertEqual(cd._check_this_checkout_can_update()[0], cd.UNKNOWN)
        with mock.patch.object(cd, "_get", lambda path, timeout=4: {"ok": True}):
            st, why = cd._check_this_checkout_can_update()
            self.assertEqual(st, cd.UNKNOWN)
            self.assertIn("predates", why)

    def test_the_row_is_on_the_roster(self):
        self.assertIs(dict(cd.CHECKS).get("this checkout can update"), cd._check_this_checkout_can_update)


class TestTheLaneIsPublishedWhereTheRowReads(unittest.TestCase):

    def tearDown(self):
        ca._PULL.clear()
        ca._PULL.update(_PULL0)

    def test_status_publishes_the_lane_under_the_key_the_row_reads(self):
        """THE JOINT: the route must EMIT the key the row asks for. Read as a parsed dict, never as text."""
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "status_payload")
        hits = []
        for node in ast.walk(fn):
            if isinstance(node, ast.Dict):
                for k, v in zip(node.keys, node.values):
                    if isinstance(k, ast.Constant) and k.value == cd._PULL_LANE_KEY:
                        hits.append(v)
        self.assertEqual(len(hits), 1, "status_payload emits %r %d time(s) — the row reads a key the "
                         "route does not send" % (cd._PULL_LANE_KEY, len(hits)))
        v = hits[0]
        self.assertTrue(isinstance(v, ast.Call) and getattr(v.func, "id", "") == "_t"
                        and len(v.args) == 2 and getattr(v.args[1], "id", "") == "pull_state",
                        "the key is not fed by pull_state() through the timing wrapper")

    def test_what_the_console_publishes_grades_as_the_row_says(self):
        now = int(time.time() * 1000)
        with ca._PRUNE_LOCK:
            ca._PULL.update({"checked": now, "on": True, "outcome": "failed", "failures": 12,
                             "failSince": now - 2 * 3600 * 1000,
                             "say": "the fast-forward did not succeed (exit 128: error: Unable to "
                                    "create '.git/index.lock': File exists.)"})
        pl = ca.pull_state()
        self.assertEqual(pl.get("failBarS"), ca._PULL_FAIL_MISSING_S, "the bar is not published")
        st, why = cd.pull_lane_verdict(pl)
        self.assertEqual(st, cd.MISSING, why)

    def test_the_fleet_beacon_says_the_pulls_are_FAILING(self):
        now = int(time.time() * 1000)
        view = {"ok": True, "behind": 3, "dirty": False}
        with mock.patch.dict(os.environ, {}), mock.patch.object(ca, "fleet_origin_status", lambda *a, **k: dict(view)):
            os.environ.pop("TV_NO_AUTO_PULL", None)
            with ca._PRUNE_LOCK:
                ca._PULL.update({"outcome": "failed", "failures": 30, "failSince": now - 11 * 3600 * 1000,
                                 "lastErr": "error: Unable to create '.git/index.lock': File exists."})
            rep = ca._pull_report()
            self.assertIs(rep.get("can"), False, "the beacon still says clear to pull: %r" % rep)
            self.assertIn("auto-pull FAILING", rep.get("why") or "")
            self.assertIn("index.lock", rep.get("why") or "")
            self.assertLessEqual(len(rep.get("why") or ""), 160, "the worker keeps 160 chars of why")
            with ca._PRUNE_LOCK:
                ca._PULL.update({"failSince": now - 5 * 60 * 1000})
            self.assertIs(ca._pull_report().get("can"), True, "a five-minute blip refused the fleet pull")


RED_PROOF = [
    {
        "why": "REG-1898 - the fleet row reads an unaskable rule as a clean tree",
        "file": "control_app.py",
        "find": "    return None if lines is None else \"\\n\".join(lines)   # REG-1898 - UNKNOWN stays None, never the raw rows\n",
        "replace": "    return \"\\n\".join(lines or [])\n",
        "matches": 1,
    },
    {
        "why": "REG-1898 - the beacon calls an UNKNOWN tree clear to pull",
        "file": "control_app.py",
        "find": "    if \"dirty\" in fl and fl.get(\"dirty\") is None:   # REG-1898 - UNKNOWN is said as UNKNOWN, never \"clear to pull\"\n",
        "replace": "    if False:\n",
        "matches": 1,
    },
    {
        "why": "REG-1865 - the console's own record makes the pull lane and the in-app door dirty again, and the ALT never auto-updates",
        "file": "launcher_pull.py",
        "find": "    return None if lines is None else (lines == [])\n",
        "replace": "    return False\n",
        "matches": 1,
    },
    {
        "why": "REG-1865 - the fleet row calls the console's own record a dirty tree again",
        "file": "control_app.py",
        "find": "        lines, _why = _sp.tracked_edits(\"\\n\".join(lines))\n",
        "replace": "        lines = list(lines)\n",
        "matches": 1,
    },
    {
        "why": "#64 - without the size refusal a lock a LIVE git is filling (its new index) would be removed from under it",
        "file": "control_app.py",
        "find": "    if st.st_size != 0:\n        out[\"say\"] = (\"left the git lock from %s: it holds",
        "replace": "    if False:\n        out[\"say\"] = (\"left the git lock from %s: it holds",
        "matches": 1,
    },
    {
        "why": "#64 - without the age bar a lock a git took a moment ago would be removed mid-operation",
        "file": "control_app.py",
        "find": "    if age < float(_GIT_LOCK_STALE_S):",
        "replace": "    if False:",
        "matches": 1,
    },
    {
        "why": "#64 - without the running-git refusal a lock whose owner is alive would be removed",
        "file": "control_app.py",
        "find": "    if running:\n        out[\"say\"] = (\"left the git lock from %s: a git process",
        "replace": "    if False:\n        out[\"say\"] = (\"left the git lock from %s: a git process",
        "matches": 1,
    },
    {
        "why": "#64 - a probe that CANNOT answer would read as 'no git running' and license a removal",
        "file": "control_app.py",
        "find": "    if running is None:\n        out[\"say\"] = (\"left the git lock from %s: whether",
        "replace": "    if False:\n        out[\"say\"] = (\"left the git lock from %s: whether",
        "matches": 1,
    },
    {
        "why": "#64 - without the check before the fetch every pull pays a refused fast-forward before the lock is judged",
        "file": "control_app.py",
        "find": "    _lock = _clear_stale_git_lock(REPO)\n    _pull_note_lock(_lock)\n    try:\n",
        "replace": "    _lock = {}\n    try:\n",
        "matches": 1,
    },
    {
        "why": "#64 - without the second trigger a lock that appears after the check wedges the lane exactly like the ALT's",
        "file": "control_app.py",
        "find": "            if _r.returncode != 0 and _names_index_lock(_r):",
        "replace": "            if False:",
        "matches": 1,
    },
    {
        "why": "#64 - the in-app update door (/api/update) must judge the lock before its pull too",
        "file": "control_app.py",
        "find": "        _lk = _clear_stale_git_lock(REPO)\n        _pull_note_lock(_lk)\n        r = _git_run(",
        "replace": "        _lk = {}\n        r = _git_run(",
        "matches": 1,
    },
    {
        "why": "#64 - pulls failing for 11 h must read MISSING on the doctor, not a quiet UNKNOWN",
        "file": "console_doctor.py",
        "find": "        if fail_s > bar:",
        "replace": "        if False:",
        "matches": 1,
    },
    {
        "why": "#64 - the lane must be ON the route the row reads, or the row reads 'predates' forever (the unjoined end)",
        "file": "control_app.py",
        "find": "        \"pullLane\": _t(\"pullLane\", pull_state),\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#64 - the fleet beacon said 'clear to pull' for 11 h while every pull failed",
        "file": "control_app.py",
        "find": "    _failing = _pull_failing_words()\n",
        "replace": "    _failing = None\n",
        "matches": 1,
    },
    {
        "why": "#64 follow-up - an update SIGKILLed mid-checkout (0-byte stale lock + half-written tree) read as 'dirty, standing down ON PURPOSE' and the row said OK",
        "file": "control_app.py",
        "find": "        _cut = _interrupted_update(REPO, _dirty)\n        if _cut:\n            _pull_note_interrupted(_cut)\n            return None\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#64 follow-up - the /api/update door told him 'commit or stash your edits' about a tree an interrupted update half-wrote",
        "file": "control_app.py",
        "find": "            _door_cut = _interrupted_update(REPO, dirty.stdout)\n",
        "replace": "            _door_cut = None\n",
        "matches": 1,
    },
    {
        "why": "#64 follow-up - the doctor must grade an interrupted update MISSING, never a quiet stand-down",
        "file": "console_doctor.py",
        "find": "    if oc == \"interrupted\":\n        return MISSING,",
        "replace": "    if False:\n        return MISSING,",
        "matches": 1,
    },
    {
        "why": "#64 follow-up - without the size/age line EVERY dirty tree beside any lock (his own edits, a live git) would read as an interrupted update",
        "file": "control_app.py",
        "find": "    if st.st_size != 0 or age < float(_GIT_LOCK_STALE_S):\n        return None\n",
        "replace": "    if False:\n        return None\n",
        "matches": 1,
    },
    {
        "why": "#64 follow-up - the fleet beacon called a half-written tree 'local tracked edits'",
        "file": "control_app.py",
        "find": "            _cut = _PULL.get(\"outcome\") == \"interrupted\"\n",
        "replace": "            _cut = False\n",
        "matches": 1,
    },
    {
        "why": "#64 follow-up - the root cause: a read-only git status takes index.lock on its own, and a timeout SIGKILL leaves it behind",
        "file": "git_quiet.py",
        "find": "    env[\"GIT_OPTIONAL_LOCKS\"] = \"0\"\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#64 follow-up - a lock REPLACED between the two looks (same 0 bytes, same mtime, another git's) would be removed from under its owner",
        "file": "control_app.py",
        "find": " or st2.st_ino != st.st_ino:",
        "replace": ":",
        "matches": 1,
    },
    {
        "why": "#64 follow-up - /api/update and the drift thread judged and removed locks on one checkout AT THE SAME TIME",
        "file": "control_app.py",
        "find": "@_one_pull_at_a_time\ndef fleet_pull():",
        "replace": "def fleet_pull():",
        "matches": 1,
    },
    {
        "why": "#64 follow-up - the drift thread's pull must wait on the same lock the /api/update door holds",
        "file": "control_app.py",
        "find": "@_one_pull_at_a_time\ndef _pull_once():",
        "replace": "def _pull_once():",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
