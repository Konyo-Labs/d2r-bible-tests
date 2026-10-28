# -*- coding: utf-8 -*-
"""v3180 — A SWEEP THAT IS READING CANNOT BE RELAUNCHED OUT FROM UNDER.

HIS ORDER, 2026-09-15: *"make sure theres a lock for this until its read and swept it cant
relaunch as a extra measure.."* — after a relaunch killed a paid vault sweep four minutes in,
losing 24 classified frames and banking nothing at all.

★ WHY THE EXISTING GUARD WAS NOT ENOUGH, and this is the whole point of a FILE:
  nothing_in_flight() checks _VAULT_JOB["running"] — perfect while the process lives, and it DIES
  WITH THE PROCESS. At the exact moment a relaunch is contemplated, the state that should forbid
  it is the state about to be destroyed. A lock on disk outlives the swap.

★ AND THE VAULT SWEEP WAS NEVER COVERED. MEASURED before this: `.sweep.lock` was touched in
  exactly ONE place in control_app.py — the CHRONICLE sweep — while _vault_sweep_run touched it
  0 times and drift_may_relaunch read it 0 times. Both halves missing at once, so a vault sweep
  was invisible to every out-of-process guard including run_gates._sweep_in_progress().
  [[the-unjoined-end]]

★ STALE IS IGNORED ON PURPOSE. run_gates' own 900s convention: a crashed sweep must not forbid
  relaunching forever. A heartbeat that cannot go cold is a deadlock, so the law pins BOTH — that
  a fresh lock refuses, and that a cold one does not.
"""
import ast
import io
import os
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable
    enable()
except Exception:
    pass


def _fn(name):
    with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
        src = fh.read()
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.FunctionDef) and n.name == name:
            return n, (ast.get_source_segment(src, n) or "")
    raise AssertionError("%s is gone" % name)


def _calls(name):
    node, _ = _fn(name)
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            out.add(f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", ""))
    return out


class ASweepHoldsTheRelaunchLock(unittest.TestCase):

    def test_the_vault_sweep_declares_itself_on_disk(self):
        """PARSED, not grepped — a mention in a comment must not satisfy this."""
        self.assertIn("_sweep_lock_touch", _calls("_vault_sweep_run"),
                      "the vault sweep does not touch the lock, so it is invisible to every "
                      "out-of-process guard — which is how a relaunch ate 24 classified frames")

    def test_it_heartbeats_rather_than_touching_once(self):
        """A single touch goes stale at 900s mid-run, on exactly the long sweep that most needs
        protecting."""
        _, body = _fn("_vault_sweep_run")
        self.assertGreaterEqual(body.count("_sweep_lock_touch()"), 2,
                                "the lock is touched once and will go cold during a long sweep")
        _, tick = _fn("_vault_sweep_run")
        # ⚠ BOTH ENDS ANCHORED, NOT A 900-CHARACTER GUESS. `tick[i:i+900]` measured how far I
        # ASSUMED _tick reaches; the function grows every time it gains a counter, and the day it
        # passes 900 chars this assertion reads the heartbeat as ABSENT while it is right there.
        # The body is bounded by its own closing instead. [[source-reading-guard]]
        i = tick.find("def _tick(")
        self.assertGreater(i, 0, "the per-progress tick is gone")
        j = tick.find("\n        prop = ", i)
        if j < 0:
            j = tick.find("\n        def ", i + 10)
        self.assertGreater(j, i, "the tick's body no longer ends where this law expects — fix "
                                 "this anchor before believing anything below it")
        self.assertIn("_sweep_lock_touch", tick[i:j],
                      "the heartbeat is not on the tick, so it cannot follow the sweep's progress")

    def test_the_relaunch_decider_reads_the_lock(self):
        self.assertIn("_sweep_lock_path", _calls("drift_may_relaunch"),
                      "auto-relaunch never consults the on-disk lock, so it can still replace the "
                      "process that is holding unbanked paid reads")

    def test_a_fresh_lock_refuses_and_a_cold_one_does_not(self):
        """Drive the SHIPPED decider against a real lock file."""
        import control_app as ca
        # 2026-09-29 — THIS CASE TESTS THE SWEEP LOCK, SO HIS BOARD'S WORLD MAY NOT ANSWER FIRST. drift_may_relaunch
        # asks board_identity_drift() BEFORE the lock, and that reads his LIVE .board_identity.json: on 2026-09-29 his
        # board read an unclaimed guest world and this case went red with the board's sentence instead of 'sweep' - a
        # verdict about his machine, not about the lock (CI, which has no board, never saw it). The world is neutral here.
        _bid = ca.board_identity_drift
        ca.board_identity_drift = lambda *a, **k: None
        self.addCleanup(setattr, ca, "board_identity_drift", _bid)
        # #128 - and the tree's own state: a red-proof that edits control_app.py makes the tree "mid-edit", and that
        # refusal (checked after the lock) would answer for the lock it removed. The lock is the subject here.
        _mid = ca._tree_is_mid_edit
        ca._tree_is_mid_edit = lambda *a, **k: (False, "")
        self.addCleanup(setattr, ca, "_tree_is_mid_edit", _mid)
        lk = ca._sweep_lock_path()
        had = os.path.exists(lk)
        saved = None
        if had:
            saved = os.path.getmtime(lk)
        try:
            with io.open(lk, "w", encoding="utf-8") as fh:
                fh.write("test")
            os.utime(lk, (time.time(), time.time()))          # fresh
            ok, why = ca.drift_may_relaunch()
            self.assertFalse(ok, "a fresh sweep lock did not stop a relaunch")
            self.assertIn("sweep", why.lower())

            old = time.time() - 4000                            # far past the 900s window
            os.utime(lk, (old, old))
            ok2, why2 = ca.drift_may_relaunch()
            # #128 - "lock was touched" covers both of the decider's lock refusals: the in-process lane's ("the lock was
            # touched Ns ago") and the no-lane one ("the sweep lock was touched Ns ago"), which this case could not see
            self.assertNotIn("lock was touched", why2 or "",
                             "a COLD lock still blocks — a crashed sweep would forbid relaunching "
                             "forever, which is a deadlock, not a guard")
        finally:
            try:
                if had and saved is not None:
                    os.utime(lk, (saved, saved))
                elif not had:
                    os.unlink(lk)
            except OSError:
                pass

RED_PROOF = [
    {"why": "v3180 - a fresh sweep lock no longer stops a relaunch, so a relaunch can kill a paid sweep mid-read",
     "file": "tv/control_app.py",
     "find": "        _lk = _sweep_lock_path()\n        _age = time.time() - os.path.getmtime(_lk)\n        if _age < 900:\n",
     "replace": "        _lk = _sweep_lock_path()\n        _age = time.time() - os.path.getmtime(_lk)\n        if False:\n",
     "matches": 1},
    {"why": "v3180 - a cold lock still blocks: a crashed sweep would forbid relaunching forever",
     "file": "tv/control_app.py",
     "find": "        _lk = _sweep_lock_path()\n        _age = time.time() - os.path.getmtime(_lk)\n        if _age < 900:\n",
     "replace": "        _lk = _sweep_lock_path()\n        _age = time.time() - os.path.getmtime(_lk)\n        if _age < 9000:\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
