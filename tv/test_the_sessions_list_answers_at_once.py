# -*- coding: utf-8 -*-
"""v3860 (#230): /api/sessions answers from its last build at once; a stale build is redone in the background.

The ALT, 2026-11-03: the list took 52 s to build (567 reels), the Shelf's fetch gives up at 45 s, and the Shelf showed
only the 08:00 session while he played all day. A slow build must never make the list late again.

RED_PROOF below: each one, applied, turns this law red."""
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable; enable()


class TheSessionsList(unittest.TestCase):
    def setUp(self):
        import control_app as ca
        self.ca = ca
        self.d = tempfile.mkdtemp(prefix="swr_")
        self.calls = []
        self.gate = threading.Event()

    def tearDown(self):
        self.gate.set()
        shutil.rmtree(self.d, True)

    def slow(self):
        self.calls.append(1)
        if len(self.calls) > 1:
            self.gate.wait(5)
        return [{"n": len(self.calls)}]

    def test_a_stale_list_is_served_at_once_and_rebuilt_once(self):
        ca = self.ca
        with mock.patch.object(ca, "HIST_DIR", self.d):
            swr = ca._SessionsSWR()
            rows, _ = swr.get(self.slow)
            self.assertEqual([{"n": 1}], rows)
            os.makedirs(os.path.join(self.d, "reel_s_1_1"))        # a new reel: the build is stale
            t0 = time.time()
            rows, meta = swr.get(self.slow)
            rows2, _ = swr.get(self.slow)
            self.assertLess(time.time() - t0, 1.0, "a stale list waited for its rebuild")
            self.assertEqual([{"n": 1}], rows)
            self.assertTrue(meta["stale"])
            self.gate.set()
            for _ in range(50):
                if swr.get(self.slow)[0] == [{"n": 2}]:
                    break
                time.sleep(0.05)
            self.assertEqual([{"n": 2}], swr.get(self.slow)[0], "the background rebuild never landed")
            self.assertEqual(2, len(self.calls), "more than one rebuild ran")

    def test_the_door_reads_the_cache(self):
        src = open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        self.assertIn("_SESSIONS_SWR.get(self._theatre_sessions)", src)


RED_PROOF = [
    {"why": "a stale list waits for its rebuild in line",
     "file": "tv/control_app.py",
     "find": "        if not have:\n            self._build(builder, fp)\n",
     "replace": "        if not have or kick:\n            self._build(builder, fp)\n",
     "matches": 1},
    {"why": "the door builds every time",
     "file": "tv/control_app.py",
     "find": "_SESSIONS_SWR.get(self._theatre_sessions)",
     "replace": "(self._theatre_sessions(), None)",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
