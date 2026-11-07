# -*- coding: utf-8 -*-
"""A KILLED PROVER LEAVES NO SANDBOX BEHIND — AND THE NEXT RUN SWEEPS WHAT AN EARLIER ONE LEFT.

MEASURED 2026-09-26 05:05: eleven heart2.* repo copies in the temp dir, dated Sep 23 -> Sep 26, one per interrupted
`heart2 --prove` - a pre-push gate's bound, a `perl alarm`, a closed terminal. Each sandbox was removed in a `finally`,
and a `finally` never runs when the process is killed by a signal. The newest was from a proof I had bounded at 50
minutes myself; its children were still rendering when the parent was already gone.

  · DRIVEN (a real child process, a real signal): a prover that installed the cleanup and holds a registered sandbox is
    sent SIGTERM, and separately killed by its own SIGALRM - the sandbox is gone and the exit says which signal.
  · DRIVEN: the sweep removes a sandbox whose owner pid is dead and one with no owner that is a day old; it KEEPS a
    sandbox whose owner is alive (another prover, mid-run), a fresh one with no owner, and anything not named heart2.*.
  · DRIVEN: make_sandbox registers its root the moment it exists, and a refused copy leaves nothing registered or on disk.
  · JOINED (ast): main() installs the cleanup and runs the sweep on --prove.
RED_PROOF below.
"""
import ast
import io
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import heart2 as H  # noqa: E402

CHILD = r"""
import os, sys, tempfile, time
sys.path.insert(0, %(here)r)
import heart2 as H
H.install_sandbox_cleanup()
root = H._track_sandbox(tempfile.mkdtemp(prefix="heart2.", dir=%(tmp)r))
open(os.path.join(root, "marker"), "w").write("x")
print(root, flush=True)
if %(alarm)r:
    import signal
    signal.alarm(1)
time.sleep(30)
print("NOT KILLED", flush=True)
"""


def _dead_pid():
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    p.wait()
    return p.pid


class AKilledProverLeavesNoSandbox(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="killedprover-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _child(self, alarm):
        js = CHILD % {"here": HERE, "tmp": self.tmp, "alarm": alarm}
        p = subprocess.Popen([sys.executable, "-c", js], stdout=subprocess.PIPE, text=True)
        root = p.stdout.readline().strip()
        self.assertTrue(root and os.path.isdir(root), "the child never made its sandbox - UNKNOWN, not passing")
        return p, root

    # #107 - a POSIX signal's handler is what this case measures. Windows has no SIGALRM, and its SIGTERM is
    # TerminateProcess, which runs no handler at all; the sandbox sweep (the next cases) is what cleans up there.
    @unittest.skipIf(os.name == "nt", "POSIX signals only - Windows has no SIGALRM and its SIGTERM runs no handler")
    def test_sigterm_removes_the_sandbox_before_the_prover_dies(self):
        p, root = self._child(alarm=False)
        p.send_signal(signal.SIGTERM)
        rc = p.wait(timeout=20)
        p.stdout.close()
        self.assertEqual(rc, 128 + signal.SIGTERM, "the prover did not exit the way SIGTERM meant (rc %s)" % rc)
        self.assertFalse(os.path.exists(root), "a SIGTERM'd prover left its sandbox behind: %s" % root)

    # #107 - a POSIX signal's handler is what this case measures. Windows has no SIGALRM, and its SIGTERM is
    # TerminateProcess, which runs no handler at all; the sandbox sweep (the next cases) is what cleans up there.
    @unittest.skipIf(os.name == "nt", "POSIX signals only - Windows has no SIGALRM and its SIGTERM runs no handler")
    def test_its_own_alarm_removes_the_sandbox_too(self):
        p, root = self._child(alarm=True)
        rc = p.wait(timeout=20)
        p.stdout.close()
        self.assertEqual(rc, 128 + signal.SIGALRM, "the alarm did not end the prover (rc %s)" % rc)
        self.assertFalse(os.path.exists(root), "a prover ended by its alarm left its sandbox behind: %s" % root)

    def test_the_sweep_takes_only_what_an_interrupted_run_left(self):
        def mk(name, owner=None, age_h=0):
            d = os.path.join(self.tmp, name)
            os.makedirs(os.path.join(d, "repo"))
            if owner is not None:
                with open(os.path.join(d, H._SANDBOX_OWNER), "w") as f:
                    f.write(str(owner))
            if age_h:
                t = time.time() - age_h * 3600
                os.utime(d, (t, t))
            return d
        dead = mk("heart2.dead", owner=_dead_pid())
        live = mk("heart2.live", owner=os.getpid())
        live_old = mk("heart2.liveold", owner=os.getpid(), age_h=72)
        legacy_old = mk("heart2.legacyold", age_h=48)
        legacy_new = mk("heart2.legacynew", age_h=1)
        other = mk("nothing-of-ours", age_h=72)
        gone = sorted(os.path.basename(p) for p, _ in H.sweep_stale_sandboxes(tmp=self.tmp))
        # the #231 eye on v3507: a pid is REUSED, so an "alive" owner past a day is a number some other process now
        # carries - no proof run lives a day, and keeping it would keep the copy forever
        self.assertEqual(gone, ["heart2.dead", "heart2.legacyold", "heart2.liveold"],
                         "the sweep took the wrong sandboxes: %s" % gone)
        for d in (live, legacy_new, other):
            self.assertTrue(os.path.isdir(d), "the sweep removed %s - a live prover's, a fresh one, or not ours" % d)
        for d in (dead, legacy_old, live_old):
            self.assertFalse(os.path.exists(d))

    def test_make_sandbox_registers_its_root_and_a_refused_copy_leaves_nothing(self):
        seen = []
        real_mkdtemp = tempfile.mkdtemp

        def spy(*a, **k):
            k["dir"] = self.tmp
            r = real_mkdtemp(*a, **k)
            seen.append((r, os.path.exists(os.path.join(r, H._SANDBOX_OWNER))))
            return r
        import safe_copy
        real_copy = safe_copy.copy
        tempfile.mkdtemp = spy
        safe_copy.copy = lambda *a, **k: (seen.append(("registered", [r for r in H._SANDBOXES])) or 2)
        try:
            tv, root = H.make_sandbox(say=lambda *a, **k: None)
        finally:
            tempfile.mkdtemp = real_mkdtemp
            safe_copy.copy = real_copy
        self.assertEqual((tv, root), (None, None), "a refused copy was not refused")
        made = seen[0][0]
        self.assertIn(made, seen[1][1], "the sandbox was not registered before the copy ran")
        self.assertFalse(os.path.exists(made), "a refused copy left its sandbox on disk")
        self.assertNotIn(made, H._SANDBOXES, "a removed sandbox stayed registered")

    def test_main_installs_the_cleanup_and_sweeps_on_prove(self):
        with io.open(os.path.join(HERE, "heart2.py"), encoding="utf-8") as f:
            tree = ast.parse(f.read())
        main = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main"]
        self.assertEqual(len(main), 1, "heart2 has no single main()")
        calls = [n.func.id for n in ast.walk(main[0]) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
        for fn in ("install_sandbox_cleanup", "sweep_stale_sandboxes"):
            self.assertIn(fn, calls, "main() never calls %s, so a --prove run neither cleans up on a signal nor sweeps" % fn)


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {
        "why": "#231 on v3507 - a reused pid keeps a dead prover's sandbox forever: an 'alive' owner is never aged out",
        "file": "heart2.py",
        "find": "        if owner and _pid_alive(owner) and age < SANDBOX_STALE_S:\n",
        "replace": "        if owner and _pid_alive(owner):\n",
        "matches": 1,
    },
    {
        "why": "a signal kills the prover without removing its sandboxes - eleven repo copies piled up that way",
        "file": "heart2.py",
        "find": "    _remove_all_sandboxes()\n    os._exit(128 + int(signum))\n",
        "replace": "    os._exit(128 + int(signum))\n",
        "matches": 1,
        "needs": "posix-signals",
    },
    {
        "why": "the sweep removes a sandbox whose owner is ALIVE - another prover's, mid-run",
        "file": "heart2.py",
        "find": "        if owner and _pid_alive(owner) and age < SANDBOX_STALE_S:\n            continue\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "make_sandbox stops registering its root, so a signal can no longer find it to remove it",
        "file": "heart2.py",
        "find": "    root = _track_sandbox(tempfile.mkdtemp(prefix=\"heart2.\"))\n",
        "replace": "    root = tempfile.mkdtemp(prefix=\"heart2.\")\n",
        "matches": 1,
    },
    {
        "why": "main() stops installing the cleanup, so a --prove run killed by the gate's bound leaks again",
        "file": "heart2.py",
        "find": "        install_sandbox_cleanup()\n        for _p, _why in sweep_stale_sandboxes():\n",
        "replace": "        for _p, _why in sweep_stale_sandboxes():\n",
        "matches": 1,
    },
]
