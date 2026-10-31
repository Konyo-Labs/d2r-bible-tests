# -*- coding: utf-8 -*-
"""v3850 (Elad 18:03 IDT 2026-10-31) - THE RECORDER OUTLIVES ITS CONSOLE, AND THERE IS STILL ONLY ONE.

The recorder is capture_win.ps1 (ON AIR and the shadow reels both film through it). It used to leave with its console
(REG-1502), because on 2026-09-29 five ran at once on the ALT and dwm.exe died eight times in an hour. His ruling:
recording survives a console restart under ONE lease. Four joints are pinned here, each with a red-proof:
  1. a second recorder that finds a live, fresh lease is refused (the Sept 29 shape);
  2. a stale lease (older than 90 s) or one whose pid is dead is taken over;
  3. the recorder survives the console: no parent-gone exit, no kill-on-close job, an exiting console's stop
     neither kills it nor withdraws its pid file;
  4. a restarted console adopts the live recorder instead of spawning one, and comes up ON AIR only when a hand
     ON AIR was on at exit and its recorder still films.
RED_PROOF below.
"""
import io
import json
import os
import re
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import recorder_lease as RL  # noqa: E402

NOW = 1793462400000
ALIVE = {4242, 5151}


def _alive(pid):
    return pid in ALIVE


def _src(name):
    with io.open(os.path.join(HERE, name), encoding="utf-8-sig") as f:
        return f.read()


RED_PROOF = [
    {"why": "1 - a second recorder beside a live one is allowed again (the 2026-09-29 dwm crash)",
     "file": "recorder_lease.py",
     "find": "    if fresh and alive(lease[\"pid\"]):\n        return \"refuse\"\n",
     "replace": "    if False:\n        return \"refuse\"\n",
     "matches": 1},
    {"why": "2 - a stale lease is never taken over, so a crashed recorder blocks recording for ever",
     "file": "recorder_lease.py",
     "find": "    fresh = 0 <= (int(now_ms) - lease[\"t\"]) <= STALE_S * 1000\n",
     "replace": "    fresh = True\n",
     "matches": 1},
    {"why": "3 - an exiting console's stop kills the recorder again",
     "file": "control_app.py",
     "find": "    if _EXIT_KEEPS_RECORDER[\"on\"]:\n        # v3850 - the console is exiting",
     "replace": "    if False:\n        # v3850 - the console is exiting",
     "matches": 1},
    {"why": "3 - the recorder goes back into the console's kill-on-close job",
     "file": "control_app.py",
     "find": "            contain=False,                              # v3850",
     "replace": "            contain=True,                              # v3850",
     "matches": 1},
    {"why": "4 - a restarted console spawns a second recorder instead of adopting the live one",
     "file": "control_app.py",
     "find": "    _adopt = _recorder_adoptable()\n    if _adopt:\n",
     "replace": "    _adopt = _recorder_adoptable()\n    if False:\n",
     "matches": 1},
]


class OneLease(unittest.TestCase):
    def test_a_live_fresh_lease_refuses_a_second_recorder(self):
        self.assertEqual(RL.verdict(RL.fmt(4242, NOW - 10000), 7000, NOW, _alive), "refuse")
        self.assertEqual(RL.verdict(RL.fmt(4242, NOW - 10000), 4242, NOW, _alive), "hold")

    def test_a_stale_or_dead_lease_is_taken_over(self):
        self.assertEqual(RL.verdict(RL.fmt(4242, NOW - (RL.STALE_S + 1) * 1000), 7000, NOW, _alive), "take")
        self.assertEqual(RL.verdict(RL.fmt(9999, NOW - 1000), 7000, NOW, _alive), "take")
        self.assertEqual(RL.verdict("garbage", 7000, NOW, _alive), "take")
        self.assertEqual(RL.verdict(None, 7000, NOW, _alive), "take")

    def test_the_powershell_half_keeps_the_same_rule(self):
        ps = _src("capture_win.ps1")
        self.assertIn("$RecLeaseRenewS = %d" % RL.RENEW_S, ps)
        self.assertIn("$RecLeaseStaleS = %d" % RL.STALE_S, ps)
        self.assertIn("'control_capture.lease'", ps)
        self.assertEqual(RL.LEASE_NAME, "control_capture.lease")
        self.assertIn("if ($v0 -eq 'refuse') {", ps)                     # refused at start
        self.assertIn("-eq 'refuse') {\n      Write-Host (\"  capture pid $PID leaving: another live recorder", ps)
        # 3 - the console that started it being gone is no longer a reason to leave
        self.assertNotIn("is gone\" }", ps)
        self.assertNotIn("the console that started me (pid $parentPid) is gone", ps)

    def test_the_beacon_reads_the_lease(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, RL.LEASE_NAME)
            self.assertFalse(RL.read(p, _alive, NOW)["alive"])
            with open(p, "w") as f:
                f.write(RL.fmt(4242, NOW - 20000))
            r = RL.read(p, _alive, NOW)
            self.assertTrue(r["alive"])
            self.assertEqual(r["pid"], 4242)
            self.assertEqual(RL.adoptable(p, _alive, NOW), 4242)
            with open(p, "w") as f:
                f.write(RL.fmt(4242, NOW - 200000))
            self.assertFalse(RL.read(p, _alive, NOW)["alive"])
            self.assertIsNone(RL.adoptable(p, _alive, NOW))


class TheConsoleSide(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import control_app
        cls.C = control_app

    def test_the_capture_spawns_outside_the_kill_on_close_job(self):
        import child_guard as G
        calls = []
        with mock.patch.object(G, "_win_job_assign", lambda proc: calls.append(proc) or (None, "x")):
            fake = mock.Mock(pid=None)
            G.spawn("v3850-law-role", ["x"], popen=lambda argv, **kw: fake, contain=False)
            self.assertEqual(calls, [], "a contain=False role was put in a kill-on-close job")
            G.spawn("v3850-law-role", ["x"], popen=lambda argv, **kw: fake)
            self.assertEqual(len(calls), 1)
        src = _src("control_app.py")
        i = src.index('_capture_proc = _child_guard.spawn(\n            "capture",')
        call = src[i:src.index("\n        )\n", i)]
        self.assertIn("creationflags=_WIN_CREATE | _WIN_BREAKAWAY,", call)
        self.assertIn("contain=False,", call, "the recorder is spawned inside the console's kill-on-close job")

    def test_an_exiting_console_leaves_the_recorder_filming(self):
        C = self.C
        with tempfile.TemporaryDirectory() as d:
            pidf = os.path.join(d, "control_capture.pid")
            with open(pidf, "w") as f:
                f.write("4242")
            ended = []
            with mock.patch.object(C, "CAP_PID_PATH", pidf), \
                    mock.patch.object(C._child_guard, "end", lambda *a, **k: ended.append(a) or {}), \
                    mock.patch.object(C, "_kill_pid", lambda *a, **k: ended.append(a)), \
                    mock.patch.dict(C._EXIT_KEEPS_RECORDER, {"on": True}):
                C._stop_capture()
            self.assertEqual(ended, [], "an exiting console killed its recorder")
            self.assertTrue(os.path.isfile(pidf), "an exiting console withdrew the recorder's pid file")

    def test_a_restarted_console_adopts_the_live_recorder(self):
        C = self.C
        with tempfile.TemporaryDirectory() as d:
            pidf = os.path.join(d, "control_capture.pid")
            spawned = []
            log = io.StringIO()
            with mock.patch.object(C, "CAP_PID_PATH", pidf), \
                    mock.patch.object(C, "_recorder_adoptable", lambda: 4242), \
                    mock.patch.object(C._child_guard, "spawn", lambda *a, **k: spawned.append(a)):
                got = C._start_capture_locked({}, log)
            self.assertEqual(got, 4242)
            self.assertEqual(spawned, [], "a second recorder was spawned beside the live one")
            with open(pidf) as f:
                self.assertEqual(f.read().strip(), "4242")
            self.assertIn("ADOPTED", log.getvalue())

    def test_on_air_comes_back_only_when_it_was_on_and_still_films(self):
        dec = self.C.onair_resume_decision
        on = {"mode": "live", "origin": "hand", "ts": NOW - 60000}
        self.assertTrue(dec(on, 4242, NOW)[0])
        self.assertFalse(dec(on, None, NOW)[0], "ON AIR resumed with its recorder gone")
        self.assertFalse(dec(None, 4242, NOW)[0])
        self.assertFalse(dec(dict(on, origin="shadow"), 4242, NOW)[0])
        self.assertFalse(dec(dict(on, mode="off"), 4242, NOW)[0])
        self.assertFalse(dec(dict(on, ts=NOW - 7 * 3600 * 1000), 4242, NOW)[0])

    def test_the_recorder_beat_never_refreshes_the_console_time(self):
        js = _src(os.path.join("..", "functions", "api", "console.js"))
        i = js.index("if (body.recorderOnly === true) {")
        block = js[i:js.index("\n  }\n", i)]
        self.assertIn("recorder: rec.recorder", block)
        self.assertNotIn("t: rec.t", block, "a recorder beat would read as a fresh console heartbeat")


if __name__ == "__main__":
    unittest.main(verbosity=2)
