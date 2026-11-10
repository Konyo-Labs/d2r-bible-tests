# -*- coding: utf-8 -*-
"""#50 — EVERY PC PROVES ITS OWN INSTRUMENTS, IN THE BACKGROUND (REG-1447).

His ruling 2026-09-29: the ALT and Dean's PC must prove their own gates - a Mac proof does not speak for
Windows (measured: different gate fingerprints at one commit; the river-outlet law BLIND on the ALT and
red on the Mac). Until today only his Mac's pre-push gate ever wrote a heart census, so on every other PC
`self_arming.may()` said "the heart has never run here" and every lock stayed shut - 76 ALT reels at
EMPTY never routed.

DRIVEN: `self_prove.decide` across every state; `self_prove.tick` end to end with a recording spawn, a
temp memory file and stubbed census/tree/load - never a real prover; `tree_state` on a real temporary
git repo (clean + at upstream -> installed; a local edit or an unpushed commit -> dev); `pid_alive` on
this process and on a dead pid; the rescue loop asks. RED_PROOF below.

REG-1511 (review of v3524) - TheStandAsideIsSafe drives the stand-aside against a REUSED pid (alive, other birth),
a prover that survives its kill, the start/kill flap, a proof already finishing, Boosteroid idling in the tray (the
real Toolhelp walk and memory read over a stubbed kernel32), the prover's own law in a Mac `ps` listing, and free
memory on a Mac without psutil. Never a real kill: every kill is a recorder, every Windows edge a stub.
"""
import inspect
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
import self_prove as SP  # noqa: E402

_REAL_PROBES = (SP.playing_state, SP.free_mb)


def setUpModule():
    # REG-1502 — the cases below are about the census, the tree and the load. Whether HIS machine is playing (his Mac
    # runs D2R under CrossOver) or short of memory must not decide them, so both probes answer "idle, roomy" here,
    # and the stand-aside cases pass their own values.
    SP.playing_state = lambda *a, **k: False      # v3862 - the proof judge asks it with cloud=False
    SP.free_mb = lambda: 8000


def tearDownModule():
    SP.playing_state, SP.free_mb = _REAL_PROBES

INSTALLED = ("installed", "level with origin")
STALE = {"state": "stale", "why": "gates changed", "fingerprint": "abc"}
MISSING = {"state": "missing", "why": "never proved"}
CURRENT = {"state": "current", "why": "proved 600 of 650, 0 blind", "fingerprint": "abc", "blind": []}


class TheOneDecision(unittest.TestCase):

    def d(self, census=STALE, tree=INSTALLED, pid=None, busy=5.0, mem=None, now=10_000.0, on=True,
          playing=False, free=8000):
        return SP.decide(census, tree, pid, busy, mem or {}, now, on=on, playing=playing, free=free)

    def test_an_idle_installed_pc_with_no_census_proves(self):
        for c in (MISSING, STALE):
            self.assertTrue(self.d(census=c)["start"], "an idle installed PC with %s census did not prove"
                            % c["state"])

    def test_a_current_census_is_left_alone(self):
        self.assertFalse(self.d(census=CURRENT)["start"])

    def test_a_development_tree_never_proves_in_the_background(self):
        r = self.d(tree=("dev", "3 local commit(s)"))
        self.assertFalse(r["start"], "a dev tree started a background prove - it would fight the pre-push gate")
        self.assertEqual(r["key"], "dev")
        self.assertFalse(self.d(tree=("unknown", "no upstream"))["start"], "an UNKNOWN tree was proved on a guess")

    def test_a_busy_or_unmeasured_machine_does_not_start(self):
        self.assertFalse(self.d(busy=SP.MAX_BUSY_TO_START)["start"], "a proof started while he was playing")
        r = self.d(busy=None)
        self.assertFalse(r["start"], "a proof started on an UNKNOWN load")
        self.assertEqual(r["key"], "load-unknown")

    def test_one_proof_at_a_time(self):
        self.assertFalse(self.d(pid=4242)["start"], "a second proof started over a running one")

    def test_a_failed_proof_backs_off_for_the_same_gates_only(self):
        mem = {"lastFailAt": 9_000.0, "lastFailFingerprint": "abc", "lastFailWhy": "x"}
        self.assertFalse(self.d(mem=mem)["start"], "a prover that just failed was restarted at once")
        self.assertTrue(self.d(mem=mem, now=9_000.0 + SP.RETRY_AFTER_FAIL_S + 1)["start"],
                        "the backoff never ends")
        self.assertTrue(self.d(mem=dict(mem, lastFailFingerprint="other"))["start"],
                        "a failure on OLD gates blocked proving the new ones")

    def test_the_switch_turns_it_off(self):
        self.assertFalse(self.d(on=False)["start"])
        self.assertFalse(SP.enabled({"TV_SELF_PROVE": "0"}))
        self.assertTrue(SP.enabled({}))


class TheTickEndToEnd(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="self_prove_law_")
        self.path = os.path.join(self.dir, ".self_prove.json")
        self.spawned = []
        SP._STARTED.update(pid=None, birth=None)      # this process's memory of a prover never leaks between cases

    def _spawn(self, log_path):
        self.spawned.append(log_path)
        return 999_999_1                     # a pid that is not alive

    def test_it_spawns_once_then_records_the_outcome(self):
        r = SP.tick(now_s=1000.0, busy=3.0, tree=INSTALLED, census=MISSING, path=self.path,
                    spawn_fn=self._spawn, env={})
        self.assertEqual(len(self.spawned), 1, "an idle installed PC with no census did not start a proof")
        self.assertEqual(r["owed"], 1)
        mem = json.load(io.open(self.path, encoding="utf-8"))
        self.assertEqual(mem.get("pid"), 999_999_1, "the lane did not remember the prover it started")
        # the prover has ended (the pid is dead) and left a current census -> worked, and nothing new starts
        r = SP.tick(now_s=2000.0, busy=3.0, tree=INSTALLED, census=CURRENT, path=self.path,
                    spawn_fn=self._spawn, env={})
        self.assertEqual(len(self.spawned), 1, "a PC with a current census started another proof")
        self.assertEqual(r["worked"], 1, "a finished proof was not counted as work")
        self.assertEqual(r["owed"], 0)
        self.assertIsNotNone(r["lastTs"])

    def test_a_proof_that_leaves_no_census_backs_off(self):
        SP.tick(now_s=1000.0, busy=3.0, tree=INSTALLED, census=STALE, path=self.path,
                spawn_fn=self._spawn, env={})
        r = SP.tick(now_s=1600.0, busy=3.0, tree=INSTALLED, census=STALE, path=self.path,
                    spawn_fn=self._spawn, env={})
        self.assertEqual(len(self.spawned), 1, "a prover that failed was restarted ten minutes later")
        self.assertEqual(r["key"], "backoff")

    def _log(self, *lines):
        with io.open(self.path + ".log", "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")

    def test_a_proof_no_lane_could_copy_is_not_a_3h_failure(self):
        """REG-1845 - his Mac 2026-10-06: every lane said "safe_copy REFUSED the sandbox (exit 1)", the proof exited
        with the census stale, and the lane waited 3 h to try the same refused copy. A proof whose log ends in no
        sandbox is booked as that, the copier is asked every tick, and the tick it can copy, a proof starts."""
        SP.tick(now_s=1000.0, busy=3.0, tree=INSTALLED, census=STALE, path=self.path,
                spawn_fn=self._spawn, env={}, sandbox=(True, ""))
        self._log("  40 gate(s) in scope · 40 declare a red-proof · 0 do not",
                  "  safe_copy REFUSED the sandbox (exit 1): REFUSED — 420.4 MB is over the 400 MB ceiling.",
                  "  no lane could build a sandbox — nothing was proven, and that is UNKNOWN, not clean.")
        refused = "REFUSED — 420.4 MB is over the 400 MB ceiling."
        r = SP.tick(now_s=1600.0, busy=3.0, tree=INSTALLED, census=STALE, path=self.path,
                    spawn_fn=self._spawn, env={}, sandbox=(False, refused))
        self.assertEqual(len(self.spawned), 1, "a proof was started into a copy the copier refuses")
        self.assertEqual(r["key"], "no-sandbox", r)
        self.assertIn("420.4 MB", r["say"], "the refusal was not said in the copier's own words")
        mem = json.load(io.open(self.path, encoding="utf-8"))
        self.assertEqual(mem.get("lastFailKind"), "sandbox", mem)
        # REG-1861 - fixed copy: the bounded sandbox backoff, then a start - never the 3 h one
        r = SP.tick(now_s=1600.0 + SP.RETRY_AFTER_SANDBOX_S + 5, busy=3.0, tree=INSTALLED, census=STALE,
                    path=self.path, spawn_fn=self._spawn, env={}, sandbox=(True, ""))
        self.assertEqual(len(self.spawned), 2, "the copy was fixed and the lane still waited out the 3 h backoff")
        self.assertEqual(r["key"], "start", r)

    def test_a_record_from_before_the_kind_is_read_from_its_log(self):
        """His Mac's own store: lastFailWhy "census still stale after the proof exited", no kind, and a log whose
        last proof built no sandbox. Once the copy is possible it starts after the bounded sandbox backoff, not 3 h."""
        mem = {"lastFailAt": 1000.0, "lastFailFingerprint": STALE.get("fingerprint"),
               "lastFailWhy": "census still stale after the proof exited"}
        with io.open(self.path, "w", encoding="utf-8") as fh:
            json.dump(mem, fh)
        self._log("  40 gate(s) in scope", "  no lane could build a sandbox — nothing was proven")
        r = SP.tick(now_s=1000.0 + SP.RETRY_AFTER_SANDBOX_S + 5, busy=3.0, tree=INSTALLED, census=STALE,
                    path=self.path, spawn_fn=self._spawn, env={}, sandbox=(True, ""))
        self.assertEqual(r["key"], "start", r)
        self.assertEqual(len(self.spawned), 1)

    def test_a_proof_that_really_failed_still_backs_off(self):
        SP.tick(now_s=1000.0, busy=3.0, tree=INSTALLED, census=STALE, path=self.path,
                spawn_fn=self._spawn, env={}, sandbox=(True, ""))
        self._log("  40 gate(s) in scope", "  test_x  BLIND")
        r = SP.tick(now_s=1600.0, busy=3.0, tree=INSTALLED, census=STALE, path=self.path,
                    spawn_fn=self._spawn, env={}, sandbox=(True, ""))
        self.assertEqual(r["key"], "backoff", r)
        self.assertEqual(json.load(io.open(self.path, encoding="utf-8")).get("lastFailKind"), "proof")

    def _sandbox_failure(self, now_s=1600.0):
        """One proof started and ended with no lane able to build a sandbox; the lane books it at `now_s`."""
        SP.tick(now_s=now_s - 600.0, busy=3.0, tree=INSTALLED, census=STALE, path=self.path,
                spawn_fn=self._spawn, env={}, sandbox=(True, ""))
        self._log("  40 gate(s) in scope", "  no lane could build a sandbox — nothing was proven")
        r = SP.tick(now_s=now_s, busy=3.0, tree=INSTALLED, census=STALE, path=self.path,
                    spawn_fn=self._spawn, env={}, sandbox=(False, "REFUSED — fixture"))
        self.assertEqual(json.load(io.open(self.path, encoding="utf-8")).get("lastFailKind"), "sandbox", r)
        return len(self.spawned)

    def test_an_unknown_preflight_never_starts_a_proof(self):
        """REG-1861 (H1.1, the v3598 cross-family eye) - check() or the safe_copy import raising made the preflight
        None, the sandbox-class booking skipped every backoff, and the 10 s rescue guard respawned a proof that failed
        the same way. A preflight that could not answer is UNKNOWN: nothing starts, and the lane says so."""
        n = self._sandbox_failure()
        r = SP.tick(now_s=1610.0, busy=3.0, tree=INSTALLED, census=STALE, path=self.path,
                    spawn_fn=self._spawn, env={}, sandbox=(None, "safe_copy would not import (ImportError)"))
        self.assertEqual(len(self.spawned), n, "a proof started on a preflight nobody could answer")
        self.assertEqual(r["key"], "sandbox-unknown", r)
        self.assertIn("ImportError", r["say"])

    def test_a_sandbox_failure_backs_off_for_a_bounded_while_even_when_the_copy_looks_fine(self):
        """REG-1861 (H1.2) - plan() can count a tree copytree then fails on (an unreadable file, a fifo), so check()
        says yes while every lane fails. A sandbox-class exit still backs off - RETRY_AFTER_SANDBOX_S, never the 10 s
        rescue cadence and never 3 h - and starts again once that has passed."""
        n = self._sandbox_failure(now_s=1600.0)
        for t in (1610.0, 1600.0 + SP.RETRY_AFTER_SANDBOX_S - 5):
            r = SP.tick(now_s=t, busy=3.0, tree=INSTALLED, census=STALE, path=self.path,
                        spawn_fn=self._spawn, env={}, sandbox=(True, ""))
            self.assertEqual(len(self.spawned), n, "a sandbox-class failure was respawned %d s later" % (t - 1600))
            self.assertEqual(r["key"], "backoff", r)
        self.assertLess(SP.RETRY_AFTER_SANDBOX_S, SP.RETRY_AFTER_FAIL_S)
        self.assertGreaterEqual(SP.RETRY_AFTER_SANDBOX_S, 600, "the bounded backoff is no longer than a tick")
        r = SP.tick(now_s=1600.0 + SP.RETRY_AFTER_SANDBOX_S + 5, busy=3.0, tree=INSTALLED, census=STALE,
                    path=self.path, spawn_fn=self._spawn, env={}, sandbox=(True, ""))
        self.assertEqual((r["key"], len(self.spawned)), ("start", n + 1), r)

    def test_a_spawn_that_raises_is_its_own_kind_and_backs_off(self):
        """REG-1861 (H1.3) - the spawn-failed handler set lastFailAt and left the kind, so after any sandbox booking
        a raising spawn() was retried every tick."""
        self._sandbox_failure(now_s=1600.0)

        def _boom(log_path, names=None):
            raise OSError("no python")
        later = 1600.0 + SP.RETRY_AFTER_SANDBOX_S + 5
        r = SP.tick(now_s=later, busy=3.0, tree=INSTALLED, census=STALE, path=self.path,
                    spawn_fn=_boom, env={}, sandbox=(True, ""))
        self.assertEqual(r["key"], "spawn-failed", r)
        mem = json.load(io.open(self.path, encoding="utf-8"))
        self.assertEqual(mem.get("lastFailKind"), "spawn", mem)
        r = SP.tick(now_s=later + 600.0, busy=3.0, tree=INSTALLED, census=STALE, path=self.path,
                    spawn_fn=_boom, env={}, sandbox=(True, ""))
        self.assertEqual(r["key"], "backoff", "a spawn that raised was retried on the next tick: %r" % (r,))

    def test_the_10s_rescue_guard_never_respawns_a_sandbox_failure(self):
        """REG-1861 - the trigger the eye named: guard() runs every 10 s and ticks the lane the moment the prover has
        ended. Driven for three minutes of rescue ticks after a sandbox-class exit, with a copy check() calls fine and
        a preflight that cannot answer: no second proof."""
        def _ticker(sandbox):
            def _t(**kw):
                kw.pop("busy", None)
                return SP.tick(busy=3.0, tree=INSTALLED, census=STALE, spawn_fn=self._spawn, env={},
                               sandbox=sandbox, **kw)
            return _t
        for sb in ((True, ""), (None, "safe_copy would not import")):
            self.setUp()
            n = self._sandbox_failure(now_s=1600.0)
            mem = json.load(io.open(self.path, encoding="utf-8"))
            mem["pid"] = 999_999_1                 # an ended prover the guard would book and replace
            with io.open(self.path, "w", encoding="utf-8") as fh:
                json.dump(mem, fh)
            for k in range(18):
                SP.guard(now_s=1600.0 + 10 * (k + 1), path=self.path, playing=False, free=8000,
                         kill_fn=lambda *a: True, _tick=_ticker(sb))
            self.assertEqual(len(self.spawned), n, "the rescue guard respawned a sandbox failure (%r)" % (sb,))

    def test_only_this_runs_own_last_word_is_read(self):
        """REG-1862 (H2) - the classifier read the last 8 KB and took a mark anywhere after the last banner, so a
        prover that died before its banner (a traceback) after an older run's mark was booked as sandbox - and
        looped. Only the bytes THIS run wrote count, and the mark must be their final word."""
        self._log("  40 gate(s) in scope", "  no lane could build a sandbox — nothing was proven")
        SP.tick(now_s=1000.0, busy=3.0, tree=INSTALLED, census=STALE, path=self.path,
                spawn_fn=self._spawn, env={}, sandbox=(True, ""))
        self._log("Traceback (most recent call last):", "ImportError: cannot import name 'x'")
        r = SP.tick(now_s=1600.0, busy=3.0, tree=INSTALLED, census=STALE, path=self.path,
                    spawn_fn=self._spawn, env={}, sandbox=(True, ""))
        self.assertEqual(json.load(io.open(self.path, encoding="utf-8")).get("lastFailKind"), "proof",
                         "a crash after an older run's mark was booked as a sandbox refusal")
        self.assertEqual(r["key"], "backoff", r)

    def test_a_run_that_wrote_nothing_is_a_proof_failure(self):
        self._log("  40 gate(s) in scope", "  no lane could build a sandbox — nothing was proven")
        SP.tick(now_s=1000.0, busy=3.0, tree=INSTALLED, census=STALE, path=self.path,
                spawn_fn=self._spawn, env={}, sandbox=(True, ""))
        SP.tick(now_s=1600.0, busy=3.0, tree=INSTALLED, census=STALE, path=self.path,
                spawn_fn=self._spawn, env={}, sandbox=(True, ""))
        self.assertEqual(json.load(io.open(self.path, encoding="utf-8")).get("lastFailKind"), "proof")

    def test_an_update_during_the_proof_is_not_a_failure(self):
        SP.tick(now_s=1000.0, busy=3.0, tree=INSTALLED, census=STALE, path=self.path,
                spawn_fn=self._spawn, env={})
        moved = dict(STALE, fingerprint="def")          # the console pulled new gates mid-proof
        r = SP.tick(now_s=1600.0, busy=3.0, tree=INSTALLED, census=moved, path=self.path,
                    spawn_fn=self._spawn, env={})
        self.assertEqual(len(self.spawned), 2, "an update during the proof was punished with the failure "
                                                "backoff instead of proving the new gates")
        self.assertEqual(r["key"], "start")

    def test_a_lost_save_never_starts_a_second_prover(self):
        """second eye: if saving fails right after a spawn, the next tick must still know a proof runs."""
        from unittest import mock
        alive = {"pid": None}

        def _spawn_live(log_path):
            self.spawned.append(log_path)
            alive["pid"] = 4_242_424
            return 4_242_424
        SP._STARTED["pid"] = None
        with mock.patch.object(SP, "save", side_effect=OSError("disk full")), \
                mock.patch.object(SP, "pid_alive", lambda pid: pid == alive["pid"]), \
                mock.patch.object(SP, "proc_birth", lambda pid: "b%d" % pid if pid == alive["pid"] else None):
            SP.tick(now_s=1000.0, busy=3.0, tree=INSTALLED, census=MISSING, path=self.path,
                    spawn_fn=_spawn_live, env={})
            r = SP.tick(now_s=1600.0, busy=3.0, tree=INSTALLED, census=MISSING, path=self.path,
                        spawn_fn=_spawn_live, env={})
        SP._STARTED.update(pid=None, birth=None)
        self.assertEqual(len(self.spawned), 1, "a failed save made the lane forget its running proof and "
                                               "start a second one - a runaway every ten minutes")
        self.assertEqual(r["key"], "running")

    def test_a_corrupt_memory_or_load_never_raises_and_never_starts(self):
        io.open(self.path, "w", encoding="utf-8").write(json.dumps({"worked": "x", "pid": 999_999_1,
                                                                    "lastFailAt": "bad"}))
        r = SP.tick(now_s=1000.0, busy=float("nan"), tree=INSTALLED, census=CURRENT, path=self.path,
                    spawn_fn=self._spawn, env={})
        self.assertEqual(self.spawned, [])
        self.assertIn("key", r)
        self.assertEqual(SP.decide(STALE, INSTALLED, None, float("nan"), {}, 1.0, playing=False, free=8000)["key"], "load-unknown",
                         "a NaN load reading passed the idle check")
        self.assertEqual(SP.decide(STALE, INSTALLED, None, "5", {}, 1.0, playing=False, free=8000)["start"], True)
        self.assertEqual(SP.decide(STALE, INSTALLED, None, "junk", {}, 1.0, playing=False, free=8000)["key"], "load-unknown")

    def test_a_probe_that_throws_never_reaches_the_rescue_loop(self):
        """Its red-proof narrows tick()'s catch-all - and it had been GREEN through that sabotage (measured
        2026-09-29): no case ever made _tick raise, so the guard it names was never exercised. Now one does."""
        def _boom():
            raise RuntimeError("the load probe fell over")
        r = SP.tick(now_s=1000.0, busy=_boom, tree=INSTALLED, census=MISSING, path=self.path,
                    spawn_fn=self._spawn, env={}, playing=False, free=8000)
        self.assertEqual("raised", r["key"], "a probe that threw reached the rescue loop")
        self.assertEqual(self.spawned, [], "a tick that raised started a proof anyway")

    def test_an_unreadable_memory_is_unknown_and_starts_nothing(self):
        io.open(self.path, "w", encoding="utf-8").write("{not json")
        r = SP.tick(now_s=1000.0, busy=3.0, tree=INSTALLED, census=MISSING, path=self.path,
                    spawn_fn=self._spawn, env={})
        self.assertEqual(self.spawned, [])
        self.assertIsNone(r["owed"], "an unreadable lane memory reported a measured figure")


class TheTreeIsToldApart(unittest.TestCase):

    def setUp(self):
        # REG-2360 - inside a git hook GIT_DIR points at the REAL repo and beats cwd=: `_repo`'s
        # `git init --bare` would rewrite the real config to core.bare=true and its commits would land on the push
        # branch. Dropped for THIS test only; addCleanup puts them back.
        _gitenv = {_k: os.environ.pop(_k) for _k in list(os.environ) if _k.startswith("GIT_")}
        self.addCleanup(os.environ.update, _gitenv)

    def _repo(self):
        root = tempfile.mkdtemp(prefix="self_prove_git_")
        up, wk = os.path.join(root, "up.git"), os.path.join(root, "wk")
        run = lambda *a, cwd=root: subprocess.run(["git"] + list(a), cwd=cwd, capture_output=True, text=True)
        run("init", "-q", "--bare", up)
        run("config", "core.autocrlf", "false", cwd=up)  # #107 REG-3626 - the fixture's bytes, not the PC's git default
        run("clone", "-q", up, wk)
        for k, v in (("user.email", "law@x"), ("user.name", "law")):
            run("config", k, v, cwd=wk)
        io.open(os.path.join(wk, "f.txt"), "w").write("a\n")
        run("add", "f.txt", cwd=wk)
        run("commit", "-qm", "one", cwd=wk)
        run("push", "-q", "origin", "HEAD", cwd=wk)
        run("branch", "--set-upstream-to=origin/" + run("rev-parse", "--abbrev-ref", "HEAD", cwd=wk).stdout.strip(),
            cwd=wk)

        def git(*args, timeout=15):
            r = subprocess.run(["git"] + list(args), cwd=wk, capture_output=True, text=True, timeout=timeout)
            return r.returncode, (r.stdout or "").strip()
        return wk, git, run

    def test_clean_and_level_is_installed_and_an_edit_or_a_local_commit_is_dev(self):
        wk, git, run = self._repo()
        self.assertEqual(SP.tree_state(git)[0], "installed", SP.tree_state(git))
        io.open(os.path.join(wk, "f.txt"), "w").write("b\n")
        self.assertEqual(SP.tree_state(git)[0], "dev", "a tree with local edits read as an installed console")
        run("commit", "-qam", "two", cwd=wk)
        self.assertEqual(SP.tree_state(git)[0], "dev", "a tree with an unpushed commit read as installed")

    def test_the_consoles_own_record_is_not_a_local_edit(self):
        """REG-1837 - his ALT 2026-10-06: the one local edit was ` M tv/.status_worst.json`, the tracked record the
        console rewrites on its slowest request, so this lane said "the tree has local edits" every tick and the
        heart never proved there again. Real git, a real temp repo: that record alone is installed; a second
        edit beside it is still dev."""
        wk, git, run = self._repo()
        os.makedirs(os.path.join(wk, "tv"))
        rec = os.path.join(wk, *SP.CONSOLE_OWN_RECORDS[0].split("/"))
        io.open(rec, "w").write('{"totalMs": 1773092.2}\n')
        run("add", "-A", cwd=wk)
        run("commit", "-qm", "the kept record", cwd=wk)
        run("push", "-q", "origin", "HEAD", cwd=wk)
        self.assertEqual(SP.tree_state(git)[0], "installed", SP.tree_state(git))
        io.open(rec, "w").write('{"totalMs": 25414039.5}\n')
        self.assertEqual(git("status", "--porcelain", "--untracked-files=no")[1], "M tv/.status_worst.json",
                         "PREMISE: the record is not the only local edit")
        self.assertEqual(SP.tree_state(git)[0], "installed",
                         "the console's own record made an installed console a development tree")
        io.open(os.path.join(wk, "f.txt"), "w").write("c\n")
        self.assertEqual(SP.tree_state(git)[0], "dev", "an edit beside the record was hidden by it")

    def test_the_verdict_key_and_the_ship_audit_ask_the_same_rule(self):
        """REG-1865 - the sweep for every other reader of a dirty tree: suite_verdict's key (a cached gate verdict is
        reused only for the commit's bytes) and ship_audit's "uncommitted" list. The console rewriting its own record
        is not a change to what a gate grades or to what was committed; a real edit beside it still is."""
        import suite_verdict as SV
        import ship_audit as SA
        from unittest import mock
        wk, git, run = self._repo()
        os.makedirs(os.path.join(wk, "tv"))
        rec = os.path.join(wk, *SP.CONSOLE_OWN_RECORDS[0].split("/"))
        io.open(rec, "w").write('{"totalMs": 1}\n')
        run("add", "-A", cwd=wk)
        run("commit", "-qm", "the kept record", cwd=wk)
        before, _ = SV.tree_key(wk)
        self.assertIsNotNone(before, "PREMISE: a clean tree has no key")
        io.open(rec, "w").write('{"totalMs": 25414039.5}\n')
        after, why = SV.tree_key(wk)
        self.assertEqual(before, after, "the console's own record moved the verdict key: %s" % why)
        io.open(os.path.join(wk, "f.txt"), "w").write("edit\n")
        self.assertIsNone(SV.tree_key(wk)[0], "a real edit beside the record kept the commit's key")
        with mock.patch.object(SA, "_sh", lambda *a: (0, "M tv/.status_worst.json\n M tv/control_app.py")):
            self.assertEqual(SA._dirty(), [" M tv/control_app.py"])
        with mock.patch.object(SA, "_sh", lambda *a: (0, "M tv/.status_worst.json")):
            self.assertEqual(SA._dirty(), [], "the ship audit calls the console's own record uncommitted work")

    def test_one_failure_answer_at_every_door(self):
        """REG-1898 (the v3600 cross-family look) - the rule raising gave two answers: launcher_pull blocked, the fleet
        row / ship audit kept raw rows, the verdict key raised. Now self_prove.tracked_edits is the one door and its
        failure is (None, why); each reader's safe answer to that is documented and driven here: the pull says it
        cannot tell (exit 1, nothing reset), the ship audit claims nothing (None), the verdict key is None, the prover's
        tree is unknown. The fleet row's None is driven in test_a_stale_git_lock_is_cleared_and_said."""
        import suite_verdict as SV
        import ship_audit as SA
        import launcher_pull as LP
        from unittest import mock
        wk, git, run = self._repo()
        os.makedirs(os.path.join(wk, "tv"))
        rec = os.path.join(wk, *SP.CONSOLE_OWN_RECORDS[0].split("/"))
        io.open(rec, "w").write('{"totalMs": 1}\n')
        run("add", "-A", cwd=wk)
        run("commit", "-qm", "the kept record", cwd=wk)
        io.open(rec, "w").write('{"totalMs": 2}\n')

        def _boom(*a, **k):
            raise RuntimeError("the rule broke")
        with mock.patch.object(SP, "_edits_beyond_own_records", _boom):
            lines, why = SP.tracked_edits("M tv/.status_worst.json")
            self.assertIsNone(lines)
            self.assertIn("could not be asked (RuntimeError)", why)
            self.assertEqual(SP.tree_state(git)[0], "unknown", "the prover read an unaskable rule as a verdict")
            with mock.patch.object(LP, "_porcelain", lambda repo: [(" M", "tv/.status_worst.json")]):
                self.assertFalse(LP.classify(wk)["ok"], "the launcher acted on a rule it could not ask")
                self.assertEqual(LP.apply(wk), 1, "the pull did not say it could not tell")
            with mock.patch.object(SA, "_sh", lambda *a: (0, "M tv/.status_worst.json")):
                self.assertIsNone(SA._dirty(), "the ship audit forgave or counted a record the rule could not judge")
            key, kwhy = SV.tree_key(wk)
            self.assertIsNone(key, "the verdict key was given over a rule that could not be asked")
            self.assertIn("UNKNOWN", kwhy)
        with mock.patch.dict(sys.modules, {"self_prove": None}):          # the rule cannot even be imported
            self.assertIsNone(LP._own_record(" M", "tv/.status_worst.json"))
            with mock.patch.object(SA, "_sh", lambda *a: (0, "M tv/.status_worst.json")):
                self.assertIsNone(SA._dirty())
        with mock.patch.object(SV, "_SP", None):
            self.assertIsNone(SV.tree_key(wk)[0])

    def test_the_verdict_key_forgives_exactly_one_list(self):
        """REG-1899 - suite_verdict kept its own SELF_RECORDS beside the console's list, and skipped it AFTER the rule.
        SELF_RECORDS is derived now: the console's records (self_prove) plus the records a gate run writes, listed once
        each, and tree_key forgives exactly that set through the one rule."""
        import suite_verdict as SV
        self.assertEqual(SV.SELF_RECORDS, frozenset(SP.CONSOLE_OWN_RECORDS) | SV.RUN_RECORDS, "the two lists drifted")
        self.assertFalse(SV.RUN_RECORDS & frozenset(SP.CONSOLE_OWN_RECORDS), "a console record is listed twice")
        wk, git, run = self._repo()
        os.makedirs(os.path.join(wk, "tv"))
        for r in sorted(SV.SELF_RECORDS):
            io.open(os.path.join(wk, *r.split("/")), "w").write("one\n")
        run("add", "-A", cwd=wk)
        run("commit", "-qm", "every record", cwd=wk)
        clean, _ = SV.tree_key(wk)
        self.assertIsNotNone(clean)
        for r in sorted(SV.SELF_RECORDS):
            io.open(os.path.join(wk, *r.split("/")), "w").write("two\n")
            self.assertEqual(SV.tree_key(wk)[0], clean, "the key moved on %s, a record it should forgive" % r)
        io.open(os.path.join(wk, "f.txt"), "w").write("edit\n")
        self.assertIsNone(SV.tree_key(wk)[0], "a real edit beside the records kept the key")

    def test_only_the_named_record_is_forgiven(self):
        f = SP._edits_beyond_own_records
        self.assertEqual(f("M tv/.status_worst.json"), [])
        self.assertEqual(f(" M tv/.status_worst.json\n M tv/control_app.py"), [" M tv/control_app.py"])
        self.assertEqual(f("M  tv/.status_worst.json.bak"), ["M  tv/.status_worst.json.bak"])
        self.assertEqual(f("R  tv/x.py -> tv/.status_worst.json"), ["R  tv/x.py -> tv/.status_worst.json"],
                         "a file renamed onto the record was forgiven, and the file it was is gone")
        self.assertEqual(f(""), [])

    def test_only_a_rewrite_of_the_record_is_forgiven(self):
        """REG-1927 - every porcelain state of the record was forgiven, so `UU` alone (a tree mid-merge) read installed."""
        f = SP._edits_beyond_own_records
        for row in (" M tv/.status_worst.json", "M  tv/.status_worst.json", "MM tv/.status_worst.json",
                    "M tv/.status_worst.json"):            # the last: self_prove._git strips the whole output
            self.assertEqual(f(row), [], "the console's own rewrite read as a local edit: %r" % row)
        for row in (" D tv/.status_worst.json", "D  tv/.status_worst.json", "UU tv/.status_worst.json",
                    "AA tv/.status_worst.json", "A  tv/.status_worst.json", " T tv/.status_worst.json",
                    "DU tv/.status_worst.json"):
            self.assertEqual(f(row), [row], "a record that was not rewritten was forgiven: %r" % row)

        def git(rows):
            def g(*args):
                return (0, rows) if args[0] == "status" else (0, "0\t0")
            return g
        self.assertEqual(SP.tree_state(git("M tv/.status_worst.json"))[0], "installed")
        self.assertEqual(SP.tree_state(git("UU tv/.status_worst.json"))[0], "dev",
                         "a tree mid-merge on the record was called an installed console")


class TheSandboxRefusalIsSaid(unittest.TestCase):
    """REG-1845 - heart2 handed safe_copy's refusal to a no-op and logged only "exit 1", 125 times on his Mac."""

    def test_heart2_writes_the_copiers_own_sentence(self):
        from unittest import mock
        import heart2
        import safe_copy

        def _refuse(src, dst, force=False, say=print):
            say("plan: 3392 file(s), 420.4 MB, skipping 12 heavy directories")
            say("REFUSED — 420.4 MB is over the 400 MB ceiling. This copier is for source, not data.")
            return 1
        said = []
        with mock.patch.object(safe_copy, "copy", _refuse):
            got = heart2.make_sandbox(say=said.append)
        self.assertEqual(got, (None, None))
        line = [x for x in said if "REFUSED the sandbox" in x]
        self.assertEqual(len(line), 1, said)
        self.assertIn("420.4 MB is over the 400 MB ceiling", line[0], "the refusal's reason never reached the log")

    def test_the_preflight_asks_the_copiers_own_rule(self):
        from unittest import mock
        import safe_copy
        with mock.patch.object(safe_copy, "check", lambda *a, **k: (1, "REFUSED — 420.4 MB is over the 400 MB ceiling")):
            self.assertEqual(SP.sandbox_ready(), (False, "REFUSED — 420.4 MB is over the 400 MB ceiling"))
        with mock.patch.object(safe_copy, "check", lambda *a, **k: (0, "")):
            self.assertEqual(SP.sandbox_ready(), (True, ""))
        with mock.patch.object(safe_copy, "check", side_effect=OSError("x")):
            got = SP.sandbox_ready()
        self.assertIs(got[0], None, "a preflight that could not ask read as an answer: %r" % (got,))
        self.assertIn("could not be asked (OSError)", got[1])


class TheProcessProbeIsSafe(unittest.TestCase):

    def test_alive_and_dead(self):
        self.assertTrue(SP.pid_alive(os.getpid()))
        self.assertFalse(SP.pid_alive(None))
        self.assertFalse(SP.pid_alive(0))
        p = subprocess.Popen([sys.executable, "-c", "pass"])
        p.wait()
        self.assertFalse(SP.pid_alive(p.pid), "a finished process read as alive")

    def test_the_heart_never_sends_signal_zero_on_windows(self):
        """Driven as Windows: os.name is 'nt', os.kill records, and the answer must come from the safe probe."""
        import heart2
        from unittest import mock
        kills, asked = [], []

        def _kill(pid, sig):
            kills.append((pid, sig))

        def _safe(pid):
            asked.append(pid)
            return True
        with mock.patch.object(heart2.os, "name", "nt"), mock.patch.object(heart2.os, "kill", _kill), \
                mock.patch.object(SP, "pid_alive", _safe):
            got = heart2._pid_alive(4242)
        self.assertEqual(kills, [], "heart2._pid_alive sent os.kill(pid, 0) on Windows, where signal 0 is "
                                    "CTRL_C_EVENT - a Ctrl-C, not a probe")
        self.assertEqual((got, asked), (True, [4242]), "the Windows answer did not come from the safe probe")


class ABackgroundProofIsPatient(unittest.TestCase):
    """REG-1454 - on the ALT a 120 s law timed out on every background proof (BELOW_NORMAL, console filming)."""

    def test_the_heart_honours_the_patience_it_is_given_and_bounds_it(self):
        import heart2
        self.assertEqual(heart2._deadline_scale(1, env={}), 1, "the default single-lane deadline moved")
        self.assertEqual(heart2._deadline_scale(4, env={}), heart2.LANE_DEADLINE_SCALE)
        self.assertEqual(heart2._deadline_scale(1, env={"HEART2_DEADLINE_SCALE": "4"}), 4,
                         "the patience a background caller asked for was ignored")
        self.assertEqual(heart2._deadline_scale(1, env={"HEART2_DEADLINE_SCALE": "999"}),
                         heart2.DEADLINE_SCALE_MAX, "an unbounded deadline would let a hung gate hang forever")
        self.assertEqual(heart2._deadline_scale(1, env={"HEART2_DEADLINE_SCALE": "junk"}), 1)

    def test_the_lane_asks_for_it(self):
        seen = {}

        class _P(object):
            pid = 4242

        def _popen(cmd, **kw):
            seen.update(kw.get("env") or {})
            return _P()
        d = tempfile.mkdtemp(prefix="self_prove_spawn_")
        SP.spawn(os.path.join(d, "log"), python=sys.executable, popen=_popen)
        self.assertEqual(seen.get("HEART2_DEADLINE_SCALE"), "4",
                         "the background prover runs with the Mac's deadlines on a slower, busier PC")


class TheProverHasWhatItNeeds(unittest.TestCase):
    """REG-1457 - on the ALT all 8 browser cases failed with "No module named 'websocket'"."""

    def test_a_missing_import_is_installed_once_hidden_on_windows(self):
        from unittest import mock
        calls = []

        class _R(object):
            returncode = 0

        def _run(argv, **kw):
            calls.append((argv, kw))
            return _R()
        with mock.patch.object(SP, "IS_WIN", True):
            got = SP.ensure_prover_deps(find=lambda m: None, run=_run)
        self.assertEqual(len(calls), 1, "the missing prover import was not installed")
        self.assertIn("websocket-client", calls[0][0])
        self.assertIn("--user", calls[0][0])
        self.assertTrue(calls[0][1].get("creationflags"), "pip ran without CREATE_NO_WINDOW - a window "
                                                          "over his game")
        self.assertEqual(got["installed"], ["websocket-client"])

    def test_present_does_nothing_and_off_windows_never_installs(self):
        from unittest import mock
        ran = []
        got = SP.ensure_prover_deps(find=lambda m: object(), run=lambda *a, **k: ran.append(a))
        self.assertTrue(got["ok"])
        self.assertEqual(ran, [])
        with mock.patch.object(SP, "IS_WIN", False):
            got = SP.ensure_prover_deps(find=lambda m: None, run=lambda *a, **k: ran.append(a))
        self.assertEqual(ran, [], "pip was run off Windows")
        self.assertFalse(got["ok"])


class TheConsoleAsks(unittest.TestCase):

    def test_the_rescue_loop_ticks_the_lane_and_status_publishes_it(self):
        import control_app as ca
        loop = inspect.getsource(ca._console_rescue_loop)
        # REG-1624 - the loop reaches the lane through ONE dispatch (the tick every 10 min, the guard while a proof
        # runs); driven here rather than read, so a dispatch that stopped ticking cannot pass on its words
        self.assertIn("_self_prove_dispatch(", loop, "nothing asks - no PC ever proves itself")
        ticked = []
        with mock.patch.object(ca, "_self_prove_tick", lambda: ticked.append(1)), \
                mock.patch.object(ca, "_console_beacon_async", lambda event: None):
            ca._self_prove_dispatch(ca.SELF_PROVE_FIRST_TICK)
        self.assertEqual(ticked, [1], "the loop's dispatch never ticks the lane")
        self.assertIn('"selfProve": dict(_SELF_PROVE)', inspect.getsource(ca), "the lane is invisible")



class AProofNeverRunsBesideHisGame(unittest.TestCase):
    """REG-1502 — MEASURED 2026-09-29 on the ALT: a hand-started inventory prove ran five hours beside his Boosteroid
    session at 690 MB free, dwm.exe died of memory exhaustion eight times in an hour, and Boosteroid crashed with it.
    A cloud client leaves the CPU nearly idle, so the load gate alone would have started this lane beside it."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="self_prove_game_")
        self.path = os.path.join(self.dir, ".self_prove.json")
        self.killed = []
        SP._STARTED.update(pid=None, birth=None)

    def _kill(self, pid, birth):
        self.killed.append(pid)
        return True                                   # the recorded prover is gone - nothing real is signalled

    def d(self, **kw):
        a = dict(playing=False, free=8000)
        a.update(kw)
        return SP.decide(STALE, INSTALLED, None, 3.0, {}, 10_000.0, **a)

    def test_it_never_starts_while_he_plays_or_when_that_cannot_be_asked(self):
        r = self.d(playing=True)
        self.assertEqual((False, "playing"), (r["start"], r["key"]),
                         "a proof started beside his game on an idle CPU - the cloud-client case")
        r = self.d(playing=None)
        self.assertEqual((False, "play-unknown"), (r["start"], r["key"]), "a proof started on a guess about play")

    def test_it_never_starts_short_of_memory_or_when_memory_cannot_be_measured(self):
        r = self.d(free=690)
        self.assertEqual((False, "low-memory"), (r["start"], r["key"]),
                         "a proof started with 690 MB free - the ALT's number the afternoon dwm died")
        self.assertEqual("mem-unknown", self.d(free=None)["key"])
        self.assertEqual("mem-unknown", self.d(free=float("nan"))["key"])
        self.assertTrue(self.d(free=SP.MIN_FREE_MB_TO_START)["start"])

    def test_the_game_and_its_cloud_clients_count_as_playing(self):
        for n in ("Boosteroid.exe", "D2R.exe", "GeForceNOW.exe", "DiabloII Resurrected.exe"):
            self.assertTrue(SP.is_play_exe(n), "%s did not count as playing" % n)
        for n in ("chrome.exe", "python.exe", "powershell.exe", "", None):
            self.assertFalse(SP.is_play_exe(n), "%r counted as playing" % (n,))

    def test_a_corrupt_stand_aside_time_never_holds_the_lane_shut(self):
        """The skeptic on fix24-selfprove: an unreadable lastStoodAsideAt re-armed the cooldown on EVERY tick."""
        r = SP.decide(STALE, INSTALLED, None, 3.0, {"lastStoodAsideAt": "junk"}, 9e9, playing=False, free=8000)
        self.assertTrue(r["start"], "a corrupt stand-aside time held the lane shut: %r" % r)

    def test_a_live_prover_with_no_recorded_birth_is_left_alone_and_never_doubled(self):
        """The skeptic on fix24-selfprove: a store from before REG-1511 holds a LIVE pid with no birth. It was booked as
        ENDED (a failure, a 3 h backoff) and forgotten, so a second prover could start beside it."""
        SP.save({"pid": os.getpid(), "startedFor": "abc", "startedAt": "x", "runs": 1}, self.path)
        spawned = []
        r = SP.tick(now_s=5000.0, busy=3.0, tree=INSTALLED, census=STALE, path=self.path, env={},
                    spawn_fn=lambda lp: spawned.append(lp) or 1, playing=False, free=8000, kill_fn=self.killed.append)
        mem = json.load(io.open(self.path, encoding="utf-8"))
        self.assertEqual("running-unverified", r["key"], r)
        self.assertEqual([], spawned, "a second proof started beside one that is still alive")
        self.assertEqual([], self.killed, "a pid whose identity cannot be checked was killed")
        self.assertEqual(os.getpid(), mem.get("pid"), "the live prover was forgotten")
        self.assertIsNone(mem.get("lastFailAt"), "a proof that is still running was booked as a failure")

    def _running(self):
        # REG-1511 — a running proof is THIS process, with its real birth: the lane only ever acts on a pid it can
        # prove is the one it started. A birth that cannot be read here would make every case below vacuous.
        born = SP.proc_birth(os.getpid())
        self.assertIsNotNone(born, "this platform cannot read a process's birth - the identity check has no input")
        SP.save({"pid": os.getpid(), "pidBirth": born, "startedFor": "abc", "startedAt": "x", "runs": 1}, self.path)

    def test_a_running_proof_stands_aside_when_he_starts_playing_and_it_is_not_a_failure(self):
        self._running()
        r = SP.tick(now_s=5000.0, busy=3.0, tree=INSTALLED, census=STALE, path=self.path, env={},
                    spawn_fn=lambda lp: 1, playing=True, free=8000, kill_fn=self._kill)
        self.assertEqual([os.getpid()], self.killed, "the running proof went on beside his game")
        self.assertEqual("stood-aside", r["key"])
        mem = json.load(io.open(self.path, encoding="utf-8"))
        self.assertNotIn("pid", mem)
        self.assertEqual(1, mem.get("stoodAside"))
        self.assertIsNone(mem.get("lastFailAt"), "standing aside for his game was booked as a failure - 3 h backoff")

    def test_a_running_proof_gives_memory_back(self):
        self._running()
        r = SP.tick(now_s=5000.0, busy=3.0, tree=INSTALLED, census=STALE, path=self.path, env={},
                    spawn_fn=lambda lp: 1, playing=False, free=SP.MIN_FREE_MB_WHILE_RUNNING_IDLE - 50, kill_fn=self._kill)
        self.assertEqual([os.getpid()], self.killed)      # REG-1715: under the floor that applies with no game beside it
        self.assertIn("%d MB" % (SP.MIN_FREE_MB_WHILE_RUNNING_IDLE - 50), r["say"])

    def test_an_unknown_answer_never_kills_a_running_proof(self):
        self._running()
        r = SP.tick(now_s=5000.0, busy=3.0, tree=INSTALLED, census=STALE, path=self.path, env={},
                    spawn_fn=lambda lp: 1, playing=None, free=None, kill_fn=self._kill)
        self.assertEqual([], self.killed, "a proof was killed on a guess")
        self.assertEqual("running", r["key"])


VM_STAT_SAMPLE = (  # measured on his Mac 2026-09-29 (no psutil there, and Darwin has no SC_AVPHYS_PAGES)
    "Mach Virtual Memory Statistics: (page size of 16384 bytes)\n"
    "Pages free:                                     4003.\n"
    "Pages active:                                 239219.\n"
    "Pages inactive:                               236127.\n"
    "Pages speculative:                              1985.\n")


class _FakeWin(object):
    """The Windows edges, stubbed: a Toolhelp32 snapshot over `procs` [(exe, pid)], and a private kernel32 whose
    OpenProcess / GetProcessTimes answer from `births` by pid. The real Python in tv_diablo._toolhelp_any and
    self_prove.proc_birth fills and reads the structures. (REG-1666: no client's memory is read any more.)"""

    def __init__(self, procs, births=None):
        self.procs, self.births = list(procs), dict(births or {})
        self._i = 0
        self.kernel32 = self                      # ctypes.windll.kernel32

    # -- Toolhelp32 (ctypes.windll.kernel32) --
    def CreateToolhelp32Snapshot(self, flags, pid):
        self._i = 0
        return 77

    def _fill(self, ref):
        if self._i >= len(self.procs):
            return 0
        name, pid = self.procs[self._i]
        ref._obj.szExeFile, ref._obj.th32ProcessID = name, pid
        self._i += 1
        return 1

    def Process32FirstW(self, snap, ref):
        return self._fill(ref)

    def Process32NextW(self, snap, ref):
        return self._fill(ref)

    def CloseHandle(self, h):
        return 1

    # -- the private kernel32 self_prove._k32() returns --
    def OpenProcess(self, access, inherit, pid):
        return (10_000 + pid) if pid in self.births else None

    def GetProcessTimes(self, h, c, e, k, u):
        v = self.births.get(h - 10_000)
        if v is None:
            return 0
        c._obj.dwHighDateTime, c._obj.dwLowDateTime = v >> 32, v & 0xFFFFFFFF
        return 1


class TheStandAsideIsSafe(unittest.TestCase):
    """REG-1511 — the review of v3524 found the REG-1502 stand-aside could kill a process that was not the prover
    (a finished prover's pid kept in memory; a stored pid that outlived a restart), could flap start/kill every tick,
    counted Boosteroid idling in the tray as play forever, matched the prover's own law as play on a Mac, forgot a
    prover its kill did not end, killed a proof that had already written its census, and on a Mac without psutil
    could never measure memory at all. Every case below drives the lane; the Windows edges are stubbed."""

    def setUp(self):
        from unittest import mock
        self.mock = mock
        self.dir = tempfile.mkdtemp(prefix="self_prove_safe_")
        self.path = os.path.join(self.dir, ".self_prove.json")
        self.killed, self.spawned = [], []
        SP._STARTED.update(pid=None, birth=None)

    def tearDown(self):
        SP._STARTED.update(pid=None, birth=None)

    def _kill(self, pid, birth):
        self.killed.append(pid)
        return True

    def _tick(self, now, **kw):
        a = dict(now_s=now, busy=3.0, tree=INSTALLED, census=STALE, path=self.path, env={},
                 spawn_fn=self._spawn, playing=False, free=8000, kill_fn=self._kill)
        a.update(kw)
        return SP.tick(**a)

    def _spawn(self, log_path):
        self.spawned.append(log_path)
        return os.getpid()                        # a LIVE pid whose real birth the lane records

    def _mem(self):
        return json.load(io.open(self.path, encoding="utf-8"))

    # (1) the pid is only ours while its birth matches
    def test_a_finished_proof_is_forgotten_by_this_process_too(self):
        world = {"alive": {4_242_001}}
        with self.mock.patch.object(SP, "pid_alive", lambda pid: pid in world["alive"]), \
                self.mock.patch.object(SP, "proc_birth", lambda pid: "b-one" if pid in world["alive"] else None):
            r = self._tick(1000.0, spawn_fn=lambda lp: 4_242_001)
            self.assertEqual(("start", 4_242_001), (r["key"], SP._STARTED["pid"]))
            world["alive"].clear()                # the prover exits having made the census current
            r = self._tick(1600.0, census=CURRENT)
        self.assertEqual(1, r["worked"])
        self.assertIsNone(SP._STARTED["pid"], "a finished prover's pid stayed in this process's memory - the pid a "
                                              "later stand-aside handed to taskkill /T /F once something reused it")
        self.assertNotIn("pid", self._mem())

    def test_a_reused_pid_is_never_the_prover_and_never_killed(self):
        me = SP.proc_birth(os.getpid())
        self.assertIsNotNone(me, "baseline: this platform must read a live process's birth")
        self.assertEqual(me, SP.proc_birth(os.getpid()), "the same process read two different births")
        self.assertTrue(SP.is_ours(os.getpid(), me), "baseline: the prover itself must read as ours")
        # the store names a LIVE pid, but the process there was born at another time: pid reuse, or a reboot
        SP.save({"pid": os.getpid(), "pidBirth": "ps:Mon Jan  1 00:00:00 2024", "startedFor": "abc"}, self.path)
        r = self._tick(5000.0, playing=True)
        self.assertEqual([], self.killed, "a stand-aside killed a process that was not the prover (a reused pid)")
        self.assertNotIn(r["key"], ("stood-aside", "running"))
        self.assertNotIn("pid", self._mem(), "a pid that names a stranger stayed on the books")
        # the same through this process's backstop, with the store empty
        io.open(self.path, "w", encoding="utf-8").write("{}")
        SP._STARTED.update(pid=os.getpid(), birth="ps:Mon Jan  1 00:00:00 2024")
        self._tick(5600.0, playing=True)
        self.assertEqual([], self.killed, "the in-memory backstop handed a stranger's pid to the kill")
        # and a store from before this fix (a pid with no recorded birth) is never trusted with a kill either
        SP.save({"pid": os.getpid(), "startedFor": "abc"}, self.path)
        self._tick(6200.0, playing=True)
        self.assertEqual([], self.killed, "a pid with no recorded birth was killed on trust")

    def test_end_tree_signals_only_a_pid_whose_birth_matches(self):
        for win in (False, True):
            sent = []
            with self.mock.patch.object(SP, "IS_WIN", win), \
                    self.mock.patch.object(SP, "pid_alive", lambda pid: True), \
                    self.mock.patch.object(SP, "proc_birth", lambda pid: "born-later"), \
                    self.mock.patch.object(SP.os, "killpg", lambda *a: sent.append(("killpg",) + a), create=True), \
                    self.mock.patch.object(SP.os, "kill", lambda *a: sent.append(("kill",) + a)), \
                    self.mock.patch.object(SP.subprocess, "run", lambda *a, **k: sent.append(("run",) + a)):
                gone = SP.end_tree(4_242_002, "born-first", wait_s=0)
            self.assertEqual([], sent, "end_tree signalled a pid whose birth differs (IS_WIN=%s)" % win)
            self.assertTrue(gone, "our prover is not there - nothing of ours is left running")

    # (5) a kill that did not take is reported, and the prover stays tracked
    def test_end_tree_reports_a_prover_that_survived(self):
        for win in (False, True):
            sent = []
            with self.mock.patch.object(SP, "IS_WIN", win), \
                    self.mock.patch.object(SP, "pid_alive", lambda pid: True), \
                    self.mock.patch.object(SP, "proc_birth", lambda pid: "b"), \
                    self.mock.patch.object(SP.os, "killpg", lambda *a: sent.append(("killpg",) + a), create=True), \
                    self.mock.patch.object(SP.subprocess, "run", lambda *a, **k: sent.append(("run",) + a)):
                gone = SP.end_tree(4_242_003, "b", wait_s=0)
            self.assertEqual(1, len(sent), "our own prover was not told to end (IS_WIN=%s)" % win)
            self.assertIs(False, gone, "a prover that outlived its kill was reported gone (IS_WIN=%s)" % win)

    def test_a_prover_that_survives_its_kill_stays_tracked(self):
        world = {"alive": {4_242_004}}
        with self.mock.patch.object(SP, "pid_alive", lambda pid: pid in world["alive"]), \
                self.mock.patch.object(SP, "proc_birth", lambda pid: "b4" if pid in world["alive"] else None):
            SP.save({"pid": 4_242_004, "pidBirth": "b4", "startedFor": "abc"}, self.path)
            r = self._tick(5000.0, playing=True, kill_fn=lambda pid, birth: False)
            self.assertEqual("aside-survived", r["key"])
            mem = self._mem()
            self.assertEqual((4_242_004, "b4"), (mem.get("pid"), mem.get("pidBirth")),
                             "a prover that survived the stand-aside was forgotten - still running, tracked by nothing")
            self.assertEqual((1, 0), (mem.get("asideSurvived"), _int0(mem.get("stoodAside"))))
            r = self._tick(5600.0, playing=False)
            self.assertEqual("running", r["key"], "a second prover could start beside one that survived")
            self.assertEqual([], self.spawned)
            world["alive"].clear()                # it ends after all
            r = self._tick(6200.0, playing=False)
        mem = self._mem()
        self.assertIsNone(mem.get("lastFailAt"), "a stood-aside prover that ended late was booked as a failure")
        self.assertEqual(1, mem.get("stoodAside"))
        self.assertEqual("aside-cooldown", r["key"])

    # (2) no flapping
    def test_a_stand_aside_holds_the_next_start(self):
        # the review's simulation: 2500 MB free idle, and with the proof running a reading under the floor that applies
        # (REG-1715: with no game beside it that is the idle floor - the law here is the cooldown, not the number)
        low = SP.MIN_FREE_MB_WHILE_RUNNING_IDLE - 100
        keys = []
        for i in range(7):
            running = bool(self.spawned) and "pid" in (self._mem() if os.path.exists(self.path) else {})
            keys.append(self._tick(1000.0 + 600 * i, free=low if running else 2500)["key"])
        self.assertEqual(["start", "stood-aside", "aside-cooldown", "aside-cooldown", "start", "stood-aside",
                          "aside-cooldown"], keys, "a proof its own memory pushes out flapped start/kill every tick")
        # after a PLAYING stand-aside too: he stops, and the cooldown still holds
        self.setUp()
        self._tick(1000.0)
        self.assertEqual("stood-aside", self._tick(1600.0, playing=True)["key"])
        self.assertEqual("aside-cooldown", self._tick(2200.0, playing=False)["key"])
        self.assertEqual("start", self._tick(1600.0 + SP.STAND_ASIDE_COOLDOWN_S, playing=False)["key"])
        # (an unreadable stand-aside time: see test_a_corrupt_stand_aside_time_never_holds_the_lane_shut)

    # (6) a proof that already wrote its census is finishing, not in the way
    def test_a_proof_whose_census_is_current_finishes_and_is_booked_once(self):
        world = {"alive": {4_242_005}}
        with self.mock.patch.object(SP, "pid_alive", lambda pid: pid in world["alive"]), \
                self.mock.patch.object(SP, "proc_birth", lambda pid: "b5" if pid in world["alive"] else None):
            SP.save({"pid": 4_242_005, "pidBirth": "b5", "startedFor": "abc"}, self.path)
            r = self._tick(5000.0, census=CURRENT, playing=True)
            self.assertEqual([], self.killed, "a proof that had already written its census was killed in its cleanup")
            self.assertEqual(("running", 1), (r["key"], r["worked"]), "its census went current and it was not booked")
            r = self._tick(5300.0, census=CURRENT, playing=True)
            self.assertEqual(([], 1), (self.killed, r["worked"]))
            world["alive"].clear()                # cleanup done, it exits
            r = self._tick(5900.0, census=CURRENT, playing=True)
        self.assertEqual(1, r["worked"], "one proof was booked as worked twice")
        self.assertNotIn("pid", self._mem())

    def test_a_finished_proof_that_hangs_is_still_stood_aside(self):
        world = {"alive": {4_242_006}}
        with self.mock.patch.object(SP, "pid_alive", lambda pid: pid in world["alive"]), \
                self.mock.patch.object(SP, "proc_birth", lambda pid: "b6" if pid in world["alive"] else None):
            SP.save({"pid": 4_242_006, "pidBirth": "b6", "startedFor": "abc"}, self.path)
            self._tick(5000.0, census=CURRENT, playing=True)
            r = self._tick(5000.0 + SP.FINISH_GRACE_S, census=CURRENT, playing=True)
        self.assertEqual([4_242_006], self.killed, "a proof still running a whole tick after its census went on "
                                                   "beside his game forever")
        self.assertEqual(("stood-aside", 1), (r["key"], r["worked"]))

    # (3) a cloud client plays only while the GAME is on his screen (REG-1666 - memory was the wrong signal: MEASURED
    #     2026-10-01, Boosteroid in the tray held 2,190 MB private bytes, more than a live stream)
    def test_a_cloud_client_plays_only_with_the_game_on_his_screen(self):
        for client in ("Boosteroid.exe", "GeForceNOW.exe", "NVIDIA GeForce NOW.exe"):
            self.assertFalse(SP.is_play_proc(client, False), "%s with no game on his screen (the tray, the launcher, "
                                                             "the library) counted as playing - the ALT would never "
                                                             "prove" % client)
            self.assertTrue(SP.is_play_proc(client, True), "%s streaming the game did not count" % client)
            self.assertTrue(SP.is_play_proc(client, None), "%s nobody could look at was guessed idle" % client)
        self.assertTrue(SP.is_play_proc("D2R.exe", False), "the game itself must always count - exclusive fullscreen "
                                                           "can hide its window from the walk")
        self.assertFalse(SP.is_play_proc("Battle.net.exe", True), "the Battle.net launcher is not the game")
        self.assertFalse(SP.is_play_proc("chrome.exe", True))

    def test_the_windows_walk_asks_the_screen_once_and_only_for_a_client(self):
        import ctypes
        real_playing = _REAL_PROBES[0]

        def ask(procs, game):
            asked = []

            def judge():
                asked.append(1)
                return game() if callable(game) else game
            fake = _FakeWin(procs)
            with self.mock.patch.object(SP, "IS_WIN", True), \
                    self.mock.patch.object(ctypes, "windll", fake, create=True):
                return real_playing(game_on_screen=judge), len(asked)
        tray = [("System", 4), ("Boosteroid.exe", 700), ("chrome.exe", 800)]
        self.assertEqual((False, 1), ask(tray, False),
                         "Boosteroid with no game on his screen read as playing through the real Toolhelp walk")
        self.assertEqual((True, 1), ask(tray, True), "Boosteroid streaming the game did not read as playing")
        self.assertEqual((True, 1), ask(tray, None), "a client nobody could look at was guessed idle")
        self.assertEqual((True, 1), ask(tray, lambda: 1 / 0), "a judge that raised was read as 'not on screen'")
        two = [("Boosteroid.exe", 700), ("GeForceNOW.exe", 701)]
        self.assertEqual((False, 1), ask(two, False), "the screen was asked once per client, not once per walk")
        self.assertEqual((True, 0), ask([("D2R.exe", 900)], False), "the game did not read as playing")
        self.assertEqual((False, 0), ask([("chrome.exe", 800)], True), "the screen was asked with no client running")
        fake = _FakeWin(tray)
        with self.mock.patch.object(SP, "IS_WIN", True), self.mock.patch.object(ctypes, "windll", fake, create=True):
            self.assertIs(True, real_playing(), "with no judge handed in, a client was guessed idle")
        fake = _FakeWin([], births={700: (0x01DC << 32) | 0x1234})
        with self.mock.patch.object(SP, "IS_WIN", True), self.mock.patch.object(SP, "_k32", lambda: fake):
            self.assertEqual("ft:%d" % ((0x01DC << 32) | 0x1234), SP.proc_birth(700), "GetProcessTimes misread")
            self.assertIsNone(SP.proc_birth(701), "a process that would not open was given a birth")

    # (4) the prover's own law is not play
    def test_a_mac_never_reads_the_provers_own_law_as_play(self):
        law = ("81234 /Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/Resources/"
               "Python.app/Contents/MacOS/Python /tmp/heart2.X/tv/test_a_bare_boosteroid_window_must_show_the_hud.py")
        game = r"81235 /Applications/CrossOver.app/Contents/wine64-preloader C:\Program Files\Diablo II Resurrected\D2R.exe"
        self.assertFalse(SP.posix_play_line(law), "the prover's own law read as play")
        self.assertFalse(SP.posix_play_line("81236 python3 -c pass /tmp/x/test_a_bare_boosteroid_window.py"))
        self.assertTrue(SP.posix_play_line(game), "D2R under CrossOver did not read as play")
        self.assertTrue(SP.posix_play_line("81237 /Applications/Boosteroid.app/Contents/MacOS/Boosteroid"))
        real_playing = _REAL_PROBES[0]

        class _R(object):
            def __init__(self, out, rc=0):
                self.stdout, self.returncode = out, rc

        for out, want in ((law + "\n", False), (law + "\n" + game + "\n", True), ("", None)):
            with self.mock.patch.object(SP, "IS_WIN", False), \
                    self.mock.patch.object(SP.subprocess, "run", lambda *a, **k: _R(out)):
                self.assertIs(want, real_playing(), "ps listing %r read as %r" % (out[:40], want))

    # (7) a Mac without psutil can still measure memory
    def test_free_memory_is_measured_on_a_mac_without_psutil(self):
        import child_guard as cg

        class _R(object):
            returncode, stdout = 0, VM_STAT_SAMPLE
        with self.mock.patch.object(cg, "IS_WIN", False), self.mock.patch.object(cg.os.path, "isfile", lambda p: False), \
                self.mock.patch.dict(sys.modules, {"psutil": None}), \
                self.mock.patch.object(cg.subprocess, "run", lambda *a, **k: _R()):
            got = _REAL_PROBES[1]()
        self.assertEqual((4003 + 236127 + 1985) * 16384 // (1024 * 1024), got,
                         "free memory on a Mac without psutil read %r - 'mem-unknown' forever" % (got,))

    # (7b) REG-1825 - Linux is asked for what it would hand out, not for the pages nothing holds
    def test_linux_memory_is_memavailable_not_memfree(self):
        """GrokBot's box 2026-10-06: `free -m` 657 MB free, 4918 MB available, and the prover said "only 643 MB of
        memory free" every tick. Driven through the prover's own probe with that /proc/meminfo."""
        import child_guard as cg
        meminfo = ("MemTotal:        8131592 kB\nMemFree:          672768 kB\n"
                   "MemAvailable:    5036032 kB\nBuffers:          120000 kB\nCached:          4100000 kB\n")
        no_avail = "MemTotal:        8131592 kB\nMemFree:          672768 kB\n"
        for text, want in ((meminfo, 4918), (no_avail, None)):
            with self.mock.patch.object(cg, "IS_WIN", False), \
                    self.mock.patch.object(cg.os.path, "isfile", lambda p: p == "/proc/meminfo"), \
                    self.mock.patch("builtins.open", self.mock.mock_open(read_data=text)), \
                    self.mock.patch.object(SP.sys, "platform", "linux"), \
                    self.mock.patch.dict(sys.modules, {"psutil": None}):
                got = _REAL_PROBES[1]()
            self.assertEqual(want, got, "a Linux meminfo read as %r MB (MemFree is 657, MemAvailable 4918)" % (got,))
        self.assertEqual(SP.decide(STALE, ("installed", ""), None, 5.0, {}, 1e9, playing=False, free=4918)["key"]
                         != "low-memory", True, "4918 MB available still refused as low memory")

    # the doctor reads the new keys the way they are meant
    def test_the_doctor_calls_the_cooldown_healthy_and_a_survivor_a_warning(self):
        import ast
        src = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        anchor = '_sp_ok = (_sp_key in ('
        self.assertEqual(1, src.count(anchor))
        i = src.index(anchor) + len(anchor) - 1
        keys = ast.literal_eval(src[i:src.index(")", i) + 1])
        self.assertIn("aside-cooldown", keys, "the wait after a stand-aside warns on every doctor pass")
        self.assertNotIn("aside-survived", keys, "a prover that outlived its kill beside his game reads healthy")


def _int0(v):
    return int(v or 0)



class TwoLanesOnlyWithRoom(unittest.TestCase):
    """REG-1670 — as many proving lanes as the PC has clear room for (his ALT, ~1.9 GB free, stays on one)."""

    def test_the_rule(self):
        self.assertEqual(SP.lanes_for(1900, 8), 1, "his ALT at ~1.9 GB free was given more than one lane")
        self.assertEqual(SP.lanes_for(3072, 4), 2, "3 GB free and 4 cores is room for two")
        self.assertEqual(SP.lanes_for(9000, 16), 4, "a 16 GB PC like Dean's did not scale up")
        self.assertEqual(SP.lanes_for(30000, 32), SP.MAX_PROVE_LANES, "the lanes were not capped")
        self.assertEqual(SP.lanes_for(8000, 2), 1, "a two-core PC was given more than one lane")
        self.assertEqual(SP.lanes_for(8000, 6), 3, "the cores did not bound the lanes")
        self.assertEqual(SP.lanes_for(None, 8), 1, "an unmeasured memory read as room")
        self.assertEqual(SP.lanes_for(float("nan"), 8), 1)
        self.assertEqual(SP.lanes_for(8000, None), 1, "an unknown core count read as enough")

    def test_spawn_asks_the_memory_free_now(self):
        seen = []

        class _P(object):
            pid = 4242

        def popen(cmd, **kw):
            seen.append(kw["env"]["HEART2_PROVE_WORKERS"])
            return _P()
        with tempfile.TemporaryDirectory() as d:
            log = os.path.join(d, "p.log")
            with mock.patch.object(SP, "free_mb", lambda: 8000), mock.patch.object(SP.os, "cpu_count", lambda: 8):
                SP.spawn(log, popen=popen)
            with mock.patch.object(SP, "free_mb", lambda: 1900), mock.patch.object(SP.os, "cpu_count", lambda: 8):
                SP.spawn(log, popen=popen)
            SP.spawn(log, popen=popen, workers=1)
        self.assertEqual(seen, ["4", "1", "1"], "the prover's lane count did not follow the memory free at spawn")

RED_PROOF = [
    {
        "why": "REG-1927 - every porcelain state of the console's own record is forgiven again, so UU reads installed",
        "file": "tv/self_prove.py",
        "find": "        if len(bits) < 2 or path not in forgiven or set(bits[0]) - {\"M\"}:\n",
        "replace": "        if len(bits) < 2 or path not in forgiven:\n",
        "matches": 1,
    },
    {
        "why": "REG-1898 - the launcher acts on a rule it could not ask (a failure reads as a verdict)",
        "file": "tv/launcher_pull.py",
        "find": "    return None if lines is None else (lines == [])\n",
        "replace": "    return lines == []\n",
        "matches": 1,
    },
    {
        "why": "REG-1898 - the ship audit keeps the raw rows when the rule could not be asked",
        "file": "tv/ship_audit.py",
        "find": "        lines, _why = _sp.tracked_edits(\"\\n\".join(lines))\n",
        "replace": "        lines = _sp.tracked_edits(\"\\n\".join(lines))[0] or lines\n",
        "matches": 1,
    },
    {
        "why": "REG-1898 - the verdict key is given over a rule that could not be asked",
        "file": "tv/suite_verdict.py",
        "find": "    if lines is None:\n        return None, \"%s, so whether the working tree is the commit is UNKNOWN - no key\" % uwhy\n",
        "replace": "    if lines is None:\n        lines = []\n",
        "matches": 1,
    },
    {
        "why": "REG-1898 - the prover reads an unaskable rule as an installed tree",
        "file": "tv/self_prove.py",
        "find": "        if _ed is None:\n            return \"unknown\", \"%s, so this tree cannot be told apart from a dev tree\" % _ewhy\n",
        "replace": "        if _ed is None:\n            _ed = []\n",
        "matches": 1,
    },
    {
        "why": "REG-1899 - suite_verdict lists its own records again instead of deriving them from the console's",
        "file": "tv/suite_verdict.py",
        "find": "    SELF_RECORDS = frozenset(_SP.CONSOLE_OWN_RECORDS) | RUN_RECORDS\n",
        "replace": "    SELF_RECORDS = RUN_RECORDS\n",
        "matches": 1,
    },
    {
        "why": "REG-1899 - tree_key forgives only the console's records, so a gate run's own record moves its key",
        "file": "tv/suite_verdict.py",
        "find": "    lines, uwhy = _SP.tracked_edits(st, also=RUN_RECORDS)   # REG-1898/1899 - the one rule, its one failure answer\n",
        "replace": "    lines, uwhy = _SP.tracked_edits(st)\n",
        "matches": 1,
    },
    {
        "why": "REG-1865 - the gate verdict key moves on the console's own record again, so every push re-runs its suites",
        "file": "tv/suite_verdict.py",
        "find": "    lines, uwhy = _SP.tracked_edits(st, also=RUN_RECORDS)   # REG-1898/1899 - the one rule, its one failure answer\n",
        "replace": "    lines, uwhy = st.splitlines(), None\n",
        "matches": 1,
    },
    {
        "why": "REG-1865 - the ship audit calls the console's own record uncommitted work again",
        "file": "tv/ship_audit.py",
        "find": "        lines, _why = _sp.tracked_edits(\"\\n\".join(lines))\n",
        "replace": "        lines = list(lines)\n",
        "matches": 1,
    },
    {
        "why": "REG-1861 - an unknown preflight reads as a yes, so a sandbox-class exit respawns on every rescue tick",
        "file": "tv/self_prove.py",
        "find": "    if isinstance(sandbox, tuple) and sandbox and sandbox[0] is None:\n",
        "replace": "    if False:\n",
        "matches": 1,
    },
    {
        "why": "REG-1861 - a sandbox-class exit skips every backoff again, and a copy check() passes is respawned every 10 s",
        "file": "tv/self_prove.py",
        "find": "    _wait = RETRY_AFTER_SANDBOX_S if mem.get(\"lastFailKind\") == \"sandbox\" else RETRY_AFTER_FAIL_S\n",
        "replace": "    _wait = 0 if mem.get(\"lastFailKind\") == \"sandbox\" else RETRY_AFTER_FAIL_S\n",
        "matches": 1,
    },
    {
        "why": "REG-1861 - a raising spawn keeps an older run's kind and is retried every tick",
        "file": "tv/self_prove.py",
        "find": "                       lastFailKind=\"spawn\")                # REG-1861 - never left as an older run's kind\n",
        "replace": "                       )\n",
        "matches": 1,
    },
    {
        "why": "REG-1862 - an older run's mark is read again, so a crash after it is booked as a sandbox refusal",
        "file": "tv/self_prove.py",
        "find": "    return bool(lines) and NO_SANDBOX_MARK in lines[-1]\n",
        "replace": "    return NO_SANDBOX_MARK in text or NO_SANDBOX_MARK in io.open(log_path, encoding=\"utf-8\", errors=\"replace\").read()\n",
        "matches": 1,
    },
    {
        "why": "REG-1845 - a refused copy is booked as a failed proof again, so the lane waits 3 h after the cause is gone",
        "file": "tv/self_prove.py",
        "find": "    _wait = RETRY_AFTER_SANDBOX_S if mem.get(\"lastFailKind\") == \"sandbox\" else RETRY_AFTER_FAIL_S\n",
        "replace": "    _wait = RETRY_AFTER_FAIL_S\n",
        "matches": 1,
    },
    {
        "why": "REG-1845 - a proof is started into a copy the copier refuses, and exits with the census unwritten",
        "file": "tv/self_prove.py",
        "find": "    if isinstance(sandbox, tuple) and sandbox and sandbox[0] is False:\n",
        "replace": "    if False:\n",
        "matches": 1,
    },
    {
        "why": "REG-1845 - heart2 drops safe_copy's refusal sentence again and logs only the exit code",
        "file": "tv/heart2.py",
        "find": "        rc = safe_copy.copy(REPO, dest, False, lambda *a, **k: _said.append(str(a[0]) if a else \"\"))\n",
        "replace": "        rc = safe_copy.copy(REPO, dest, False, lambda *a, **k: None)\n",
        "matches": 1,
    },
    {
        "why": "REG-1825 - the prover reads memory its own way again, MemFree on Linux, so GrokBot's 4918 MB available reads as 643 free and the heart never proves",
        "file": "tv/self_prove.py",
        "find": "        import child_guard as _cg\n        return _cg._free_ram_mb_read()\n",
        "replace": "        if hasattr(os, \"sysconf\") and \"SC_AVPHYS_PAGES\" in os.sysconf_names:\n            return int(os.sysconf(\"SC_AVPHYS_PAGES\") * os.sysconf(\"SC_PAGE_SIZE\") // (1024 * 1024))\n        return None\n",
        "matches": 1,
    },
    {
        "why": "REG-1825 - the one memory reader asks Linux for MemFree, the pages nothing holds, instead of what it would hand out",
        "file": "tv/child_guard.py",
        "find": "                    if line.startswith(\"MemAvailable:\"):\n",
        "replace": "                    if line.startswith(\"MemFree:\"):\n",
        "matches": 1,
    },
    {
        "why": "REG-1837 - the console's own tracked record makes it a dev tree again, so the ALT never proves and its deleter stays locked",
        "file": "tv/self_prove.py",
        "find": "        _ed, _ewhy = tracked_edits(dirty)\n",
        "replace": "        _ed, _ewhy = (dirty.splitlines() if dirty else []), None\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 (skeptic on fix24-selfprove) - a corrupt stand-aside time re-arms the cooldown every tick, for ever",
        "file": "tv/self_prove.py",
        "find": "        last_aside = None\n",
        "replace": "        last_aside = now_s\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 (skeptic on fix24-selfprove) - a live prover with no recorded birth is booked as ended and a second one starts",
        "file": "tv/self_prove.py",
        "find": "    unverified = bool(pid) and _who is None\n",
        "replace": "    unverified = False\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 (REG-1502) - a proof starts beside his game when the CPU looks idle (a cloud client)",
        "file": "tv/self_prove.py",
        "find": "    if playing:\n        return {\"start\": False, \"key\": \"playing\",",
        "replace": "    if False:\n        return {\"start\": False, \"key\": \"playing\",",
        "matches": 1,
    },
    {
        "why": "2026-09-29 (REG-1502) - a running proof goes on beside the game he just started",
        "file": "tv/self_prove.py",
        "find": "    if playing is True:\n        return True, ",
        "replace": "    if False:\n        return True, ",
        "matches": 1,
    },
    {
        "why": "2026-09-29 (REG-1502) - Boosteroid does not count as playing: the ALT's exact case",
        "file": "tv/self_prove.py",
        "find": "PLAY_EXES = (\"boosteroid.exe\", ",
        "replace": "PLAY_EXES = (",
        "matches": 1,
    },
    {
        "why": "2026-09-29 (REG-1502) - a proof starts with 690 MB free",
        "file": "tv/self_prove.py",
        "find": "    if free < MIN_FREE_MB_TO_START:\n",
        "replace": "    if False:\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - the prover's websocket-client is never ensured, so Windows browser laws fail (REG-1457)",
        "file": "tv/self_prove.py",
        "find": "PROVER_DEPS = ((\"websocket\", \"websocket-client\"),)\n",
        "replace": "PROVER_DEPS = ()\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - the heart ignores the patience a background proof asks for (REG-1454)",
        "file": "tv/heart2.py",
        "find": "    raw = (env if env is not None else os.environ).get(\"HEART2_DEADLINE_SCALE\")\n",
        "replace": "    raw = None\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 (second eye) - a failed save after a spawn makes the lane start a second prover",
        "file": "tv/self_prove.py",
        "find": "            _STARTED.update(pid=mem[\"pid\"], birth=mem[\"pidBirth\"])\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "2026-09-29 (second eye) - a NaN load reading passes the idle check",
        "file": "tv/self_prove.py",
        "find": "    if busy_pct is None or busy_pct != busy_pct:",
        "replace": "    if busy_pct is None:",
        "matches": 1,
    },
    {
        "why": "2026-09-29 (second eye) - a corrupt lane memory makes every tick raise into the rescue loop",
        "file": "tv/self_prove.py",
        "find": "        return _tick(now_s, busy, tree, census, path, spawn_fn, env, playing, free, kill_fn, sandbox, takes_only,\n                     lock_rank, play_why)\n    except Exception as e:\n",
        "replace": "        return _tick(now_s, busy, tree, census, path, spawn_fn, env, playing, free, kill_fn, sandbox, takes_only,\n                     lock_rank, play_why)\n    except ZeroDivisionError as e:\n",   # v3883 re-anchor (REG-3423)
        "matches": 1,
    },
    {
        "why": "2026-09-29 - an update during a proof is booked as a failure and the new gates wait 3 hours",
        "file": "tv/self_prove.py",
        "find": "        elif mem.get(\"startedFor\") and census.get(\"fingerprint\") != mem.get(\"startedFor\"):\n",
        "replace": "        elif False:\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - a development tree proves in the background and fights the pre-push gate for the CPU",
        "file": "tv/self_prove.py",
        "find": "    if kind != \"installed\":\n",
        "replace": "    if kind == \"unknown\":\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - a proof starts while he is playing",
        "file": "tv/self_prove.py",
        "find": "    if busy_pct >= MAX_BUSY_TO_START:\n",
        "replace": "    if busy_pct >= 1000:\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - a prover that failed is restarted every ten minutes, all day",
        "file": "tv/self_prove.py",
        "find": "            and now_s - last_fail < _wait:\n",
        "replace": "            and now_s - last_fail < 0:\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - the heart sends signal 0 (a Ctrl-C) on Windows again",
        "file": "tv/heart2.py",
        "find": "    if os.name == \"nt\":\n        try:\n            import self_prove as _sp\n",
        "replace": "    if False:\n        try:\n            import self_prove as _sp\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - nothing asks: no PC ever proves itself",
        "file": "tv/control_app.py",
        "find": "        _self_prove_tick()          # #50 — has THIS PC proved its own instruments?\n",
        "replace": "        pass\n",
        "matches": 1,
    },
    # ── REG-1511 (review of v3524) ─────────────────────────────────────────────────────────────────────────────
    {
        "why": "2026-09-29 (REG-1511) - a finished prover's pid stays in this process's memory for the console's life",
        "file": "tv/self_prove.py",
        "find": "        mem.pop(k, None)\n    _STARTED.update(pid=None, birth=None)\n",
        "replace": "        mem.pop(k, None)\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 (REG-1511) - any live process at the stored pid is taken for the prover (a reused pid is killed)",
        "file": "tv/self_prove.py",
        "find": "        return now == birth\n",
        "replace": "        return True\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 (REG-1511) - end_tree runs taskkill /T /F on a pid whose birth is not the prover's",
        "file": "tv/self_prove.py",
        "find": "        if not is_ours(pid, birth):\n            return True                   # nothing of ours",
        "replace": "        if False:\n            return True                   # nothing of ours",
        "matches": 1,
    },
    {
        "why": "2026-09-29 (REG-1511) - the prover's birth is never recorded at spawn, so the lane cannot recognise its own proof",
        "file": "tv/self_prove.py",
        "find": "            mem[\"pidBirth\"] = proc_birth(mem[\"pid\"])",
        "replace": "            mem[\"pidBirth\"] = None",
        "matches": 1,
    },
    {
        "why": "2026-09-29 (REG-1511) - a proof its own memory pushes out flaps start/stood-aside every tick",
        "file": "tv/self_prove.py",
        "find": "    if last_aside is not None and now_s - last_aside < STAND_ASIDE_COOLDOWN_S:\n",
        "replace": "    if False:\n",
        "matches": 1,
    },
    {
        "why": "2026-10-01 (REG-1666) - a cloud client with no game on his screen (the tray, the launcher) counts as playing",
        "file": "tv/self_prove.py",
        "find": "    return on_screen is not False             # every cloud client in PLAY_EXES is judged by the screen\n",
        "replace": "    return True\n",
        "matches": 1,
    },
    {
        "why": "2026-10-01 (REG-1666) - the game itself is judged by the screen, so D2R hidden by fullscreen is not play",
        "file": "tv/self_prove.py",
        "find": "    if _is_game_exe(n):\n        return True\n",
        "replace": "    if _is_game_exe(n):\n        return on_screen is not False\n",
        "matches": 1,
    },
    {
        "why": "2026-10-01 (REG-1666) - the Windows walk asks the name alone again, never whether the game is on screen",
        "file": "tv/self_prove.py",
        "find": "                    return is_play_proc(name, _screen())\n",
        "replace": "                    return is_play_exe(name)\n",
        "matches": 1,
    },
    {
        "why": "2026-10-01 (REG-1666) - the screen is asked for every process, not once and only for a cloud client",
        "file": "tv/self_prove.py",
        "find": "        if \"v\" not in seen:\n            seen[\"v\"] = _ask(game_on_screen, lambda: None)\n        return seen[\"v\"]\n",
        "replace": "        seen[\"v\"] = _ask(game_on_screen, lambda: None)\n        return seen[\"v\"]\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 (REG-1511) - on a Mac the prover's own boosteroid law reads as play and stands the proof aside",
        "file": "tv/self_prove.py",
        "find": "    if exe.startswith(\"python\") or any(a.lower().endswith(\".py\") for a in argv):\n        return False\n",
        "replace": "    if False:\n        return False\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 (REG-1511) - end_tree reports a prover that survived its kill as gone",
        "file": "tv/self_prove.py",
        "find": "            return False                  # it SURVIVED",
        "replace": "            return True                   # it SURVIVED",
        "matches": 1,
    },
    {
        "why": "2026-09-29 (REG-1511) - a prover that survived the stand-aside is forgotten while it still runs",
        "file": "tv/self_prove.py",
        "find": "        if gone:\n            mem.update(stoodAside=",
        "replace": "        if True:\n            mem.update(stoodAside=",
        "matches": 1,
    },
    {
        "why": "2026-09-29 (REG-1511) - a stood-aside prover that ended a tick late is booked as a failure (3 h backoff)",
        "file": "tv/self_prove.py",
        "find": "        elif mem.get(\"standingAside\"):\n",
        "replace": "        elif False:\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 (REG-1511) - a proof that already wrote its census is killed in its cleanup and never booked",
        "file": "tv/self_prove.py",
        "find": "    finishing = bool(running) and census.get(\"state\") == \"current\"",
        "replace": "    finishing = False and census.get(\"state\") == \"current\"",
        "matches": 1,
    },
    {
        "why": "2026-09-29 (REG-1511) - a finished proof that hangs runs beside his game forever",
        "file": "tv/self_prove.py",
        "find": "    if aside and finishing and now_ms - _int(mem.get(\"finishingSince\")) < FINISH_GRACE_S * 1000:\n",
        "replace": "    if aside and finishing:\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 (REG-1511) - a proof booked when its census went current is booked again when it exits",
        "file": "tv/self_prove.py",
        "find": "        if mem.get(\"finishingSince\"):\n            pass",
        "replace": "        if False:\n            pass",
        "matches": 1,
    },
    {
        "why": "2026-09-29 (REG-1511) - a Mac without psutil never measures free memory ('mem-unknown' forever)",
        "file": "tv/child_guard.py",
        "find": "        out = subprocess.run([\"vm_stat\"], capture_output=True, text=True, encoding=\"utf-8\", errors=\"replace\",\n                             timeout=5).stdout\n        return parse_vm_stat(out)\n",
        "replace": "        return None\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 (REG-1511) - the doctor warns through every stand-aside cooldown",
        "file": "tv/control_app.py",
        # REG-1521 - the v3524 union put "running-unverified" inside this tuple after the anchor was written, so it
        # matched 0 times and the red-proof census refused every push from the integration (REG-1513's class). The
        # anchor is the tuple as the tree holds it; the tamper still drops only "aside-cooldown".
        "find": "\"playing\", \"stood-aside\", \"running-unverified\", \"low-memory\", \"aside-cooldown\")",
        "replace": "\"playing\", \"stood-aside\", \"running-unverified\", \"low-memory\")",
        "matches": 1,
    },
    {
        "why": "2026-10-01 (REG-1670) - the lanes ignore free memory, so his 8 GB ALT is pushed under its floor",
        "file": "tv/self_prove.py",
        "find": "    return max(1, min(int(f // LANE_BUDGET_MB), c // 2, MAX_PROVE_LANES))\n",
        "replace": "    return max(1, min(c // 2, MAX_PROVE_LANES))\n",
        "matches": 1,
    },
    {
        "why": "2026-10-01 (REG-1670) - the prover always starts one lane, whatever room the PC has",
        "file": "tv/self_prove.py",
        "find": "    if workers is None:\n        workers = lanes_for(free_mb(), os.cpu_count())\n",
        "replace": "    if workers is None:\n        workers = 1\n",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
