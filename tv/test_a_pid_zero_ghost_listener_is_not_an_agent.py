# -*- coding: utf-8 -*-
"""v3860 (#230): a socket Windows lists as LISTENING under PID 0 is an orphan, never a live agent.

Seen on the ALT 2026-11-03: `netstat -ano` held four 127.0.0.1:17771 LISTENING rows owned by PID 0 after hourly
stops. _port_listener_pid returned 0, _pid_cached kept 0 (not None), _agent_alive read True, and every hourly shadow
rollover logged "STILL ROLLING (stop requested · forcing)" - no close row since 10-29, so no reel was sealed.

RED_PROOF below: applied, this law turns red."""
import os
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable; enable()

GHOSTS = ("  Proto  Local Address          Foreign Address        State           PID\n"
          "  TCP    127.0.0.1:17771        127.0.0.1:0            LISTENING       0\n"
          "  TCP    127.0.0.1:17771        127.0.0.1:0            LISTENING       0\n")
LIVE = GHOSTS + "  TCP    127.0.0.1:17771        0.0.0.0:0              LISTENING       11936\n"


class APidZeroGhost(unittest.TestCase):
    def _scan(self, text):
        import control_app as ca
        with mock.patch.object(ca, "IS_WIN", True), \
                mock.patch.object(ca, "_WIN_CREATE", 0, create=True), \
                mock.patch.object(ca.subprocess, "check_output", return_value=text):
            return ca._port_listener_pid(17771)

    def test_only_ghosts_reads_nobody_listening(self):
        self.assertIsNone(self._scan(GHOSTS), "a PID 0 orphan socket was read as a live agent")

    def test_a_real_listener_behind_ghosts_is_still_found(self):
        self.assertEqual(11936, self._scan(LIVE))


RED_PROOF = [
    {"why": "PID 0 counts as the agent again",
     "file": "tv/control_app.py",
     "find": "                if _owner <= 0:\n                    continue\n",
     "replace": "",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
