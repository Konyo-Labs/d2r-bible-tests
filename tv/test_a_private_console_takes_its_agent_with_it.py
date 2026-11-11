# -*- coding: utf-8 -*-
"""REG-3670 - A PRIVATE CONSOLE A LAW STARTS GOES, AND THE AGENT IT STARTED GOES WITH IT.

MEASURED 2026-11-11 on his Mac: three tv_diablo agents ran on as orphans (ppid 1) - 9 hours and 2.7 days old, each
listening on an ephemeral agent port and writing a btnmatrix-* fixture log. test_button_matrix boots a private
control_app, turns its SIM agent on, and at exit SIGTERMed the console alone; control_app never setsids its agent on a
Mac (v779, the Screen Recording chain), so the agent was re-parented to launchd and lived on. run_gates' end-of-run check
(test_a_leak_is_this_runs_not_his_consoles) names such leaks; this law holds the source shut.

DRIVEN through the law's own two helpers (test_button_matrix.spawn_private / stop_private): a fake console - a python
that starts a child and sleeps - is spawned exactly as the private console is, and the stop must take the child too.
POSIX only: the group is the mechanism, and Windows has none (its proofs declare "posix").
"""
import os
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

import test_button_matrix as B   # noqa: E402

_FAKE_CONSOLE = (
    "import os, subprocess, sys, time\n"
    "c = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])\n"
    "open(sys.argv[1], 'w').write(str(c.pid))\n"
    "time.sleep(120)\n"
)


def _alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    # a zombie answers kill(0) until its parent reaps it; launchd reaps an orphan at once, so give it a moment
    return True


@unittest.skipUnless(os.name == "posix", "the process group is the mechanism - POSIX only")
class APrivateConsoleTakesItsAgentWithIt(unittest.TestCase):
    def _spawn(self):
        d = tempfile.mkdtemp(prefix="private-console-")
        pidfile = os.path.join(d, "agent.pid")
        proc, group = B.spawn_private([sys.executable, "-c", _FAKE_CONSOLE, pidfile], dict(os.environ))
        self.addCleanup(lambda: proc.poll() is None and proc.kill())
        for _ in range(100):
            if os.path.exists(pidfile) and open(pidfile).read().strip():
                break
            time.sleep(0.05)
        child = int(open(pidfile).read().strip())
        self.addCleanup(lambda: _alive(child) and os.kill(child, 9))
        return proc, group, child

    def test_the_console_runs_in_a_group_of_its_own(self):
        proc, group, child = self._spawn()
        self.assertTrue(group, "the private console was started without a session of its own")
        self.assertEqual(os.getpgid(proc.pid), proc.pid, "the private console does not lead its own group")
        self.assertEqual(os.getpgid(child), proc.pid, "the fixture's 'agent' is not in the console's group")

    def test_stopping_the_console_stops_its_agent(self):
        proc, group, child = self._spawn()
        self.assertTrue(_alive(child), "the fixture's 'agent' never started - the case could not distinguish")
        B.stop_private(proc, "http://127.0.0.1:9", group, ask_s=0.2, wait_s=3.0)
        self.assertIsNotNone(proc.poll(), "the private console is still running")
        deadline = time.time() + 5
        while _alive(child) and time.time() < deadline:
            time.sleep(0.1)
        self.assertFalse(_alive(child), "the agent the private console started outlived it (pid %d)" % child)


RED_PROOF = [
    {"why": "REG-3670 - the private console shares the law's group again, so a group signal cannot reach only its agent",
     "file": "test_button_matrix.py",
     "find": "    group = os.name == \"posix\"\n",
     "replace": "    group = False\n",
     "matches": 1, "needs": "posix"},
    {"why": "REG-3670 - the stop signals the console alone again and its agent is re-parented to launchd",
     "file": "test_button_matrix.py",
     "find": "                os.killpg(proc.pid, sig)\n",
     "replace": "                os.kill(proc.pid, sig)\n",
     "matches": 1, "needs": "posix"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
