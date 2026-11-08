# -*- coding: utf-8 -*-
"""v3884 - BESIDE A CLOUD STREAM A BUSY PC PROVES AFTER HALF AN HOUR, NOT SIX (his ruling 2026-11-05: "prove beside cloud").

MEASURED 2026-11-08 ~11:00 IST on the work ALT (an i3; SSH, read-only): twenty 0.5 s GetSystemTimes samples read 82-88% busy
(mean 84.7) - Boosteroid 60%, the console's own capture of that stream 44% + 38%, its audio 33%. MAX_BUSY_TO_START (75)
refused every proof for up to BUSY_STARVE_S (6 h), so two BLIND verdicts its v3881 census had filed - laws v3882 fixed, RED
7 of 7 and 8 of 8 by hand on that PC at v3882's bytes - held all four of its locks shut; GrokBot read its row "proof waits for
an idle PC - the machine is 81% busy". The load is the stream he asked proofs to run beside. So while a cloud client runs and
the local game does not (cloud_streaming), a busy refusal starves its way in after BUSY_STARVE_BESIDE_CLOUD_S. Nothing else
moves: a local game still stops it, every memory floor still holds (REG-1502: dwm died at 690 MB free beside a stream),
an UNKNOWN process list keeps the long wait. Drives the real decide() and cloud_streaming() with the process list stubbed.
RED_PROOF below. [[heart-first]] [[unknown-stays-unknown]]
"""
import os
import subprocess
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import self_prove as SP  # noqa: E402

INSTALLED = ("installed", "level with origin")
STALE = {"state": "stale", "why": "gates changed", "fingerprint": "abc"}
NOW = 100 * 86400.0


def _d(busy_for_s, cloud, playing=False, free=8000, busy=85.0):
    mem = {"busySince": int((NOW - busy_for_s) * 1000)} if busy_for_s is not None else {}
    return SP.decide(STALE, INSTALLED, None, busy, mem, NOW, playing=playing, free=free, cloud=cloud)


class AProofStartsBesideACloudStream(unittest.TestCase):

    def test_half_an_hour_beside_a_stream_starts_a_proof(self):
        """* THE POINT - the work ALT at 85% with Boosteroid streaming: it proves after 30 min, not 6 h"""
        r = _d(31 * 60, cloud=True)
        self.assertTrue(r["start"], "a PC busy only with his cloud stream still waited - its locks stay shut: %s" % r["why"])
        self.assertIn("cloud stream", r["why"])

    def test_baseline_without_a_stream_the_long_wait_stands(self):
        r = _d(31 * 60, cloud=False)
        self.assertEqual((r["start"], r["key"]), (False, "busy"), "PREMISE: a PC busy for its own reasons waits the 6 h")
        self.assertEqual(_d(31 * 60, cloud=None)["start"], False, "an UNKNOWN process list shortened the wait")

    def test_inside_the_half_hour_it_waits_and_says_when(self):
        r = _d(10 * 60, cloud=True)
        self.assertEqual((r["start"], r["key"]), (False, "busy"))
        self.assertIn("past 30 min it proves anyway", r["why"])
        self.assertIn("a cloud stream is running", r["why"])

    def test_his_local_game_and_the_memory_floors_still_win(self):
        self.assertFalse(_d(5 * 3600, cloud=True, playing=True)["start"], "a local game was out-waited by the stream rule")
        self.assertFalse(_d(5 * 3600, cloud=True, free=600)["start"], "a proof started beside a stream under the memory floor")


class TheStreamIsReadNotGuessed(unittest.TestCase):

    def _ps(self, *lines, rc=0):
        out = "\n".join("%d %s" % (100 + i, ln) for i, ln in enumerate(lines))
        return mock.patch.object(SP.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, rc, out, ""))

    def test_a_cloud_client_alone_is_a_stream(self):
        if SP.IS_WIN:
            self.skipTest("the POSIX listing is this case's seam; Windows reads the toolhelp list (UNMEASURED here)")
        with self._ps("/usr/bin/python3 tv/control_app.py", "/Applications/Boosteroid.app/Contents/MacOS/Boosteroid"):
            self.assertIs(SP.cloud_streaming(), True)
        with self._ps("/Applications/Boosteroid.app/Contents/MacOS/Boosteroid", "wine D2R.exe"):
            self.assertIs(SP.cloud_streaming(), False, "the local game running beside the client read as a stream")
        with self._ps("/usr/bin/python3 tv/control_app.py"):
            self.assertIs(SP.cloud_streaming(), False)
        with self._ps(rc=1):
            self.assertIsNone(SP.cloud_streaming(), "an unreadable process list was read as 'no stream'")


RED_PROOF = [
    {"why": "v3884 - a busy PC beside a cloud stream waits the whole 6 h again (the work ALT's locks stay shut)",
     "file": "tv/self_prove.py",
     "find": "        _starve = BUSY_STARVE_BESIDE_CLOUD_S if cloud is True else BUSY_STARVE_S   # v3884 - beside a cloud stream\n",
     "replace": "        _starve = BUSY_STARVE_S\n", "matches": 1},
    {"why": "v3884 - an UNKNOWN process list shortens the wait (the stream rule fires on a guess)",
     "file": "tv/self_prove.py",
     "find": "        _starve = BUSY_STARVE_BESIDE_CLOUD_S if cloud is True else BUSY_STARVE_S   # v3884 - beside a cloud stream\n",
     "replace": "        _starve = BUSY_STARVE_BESIDE_CLOUD_S if cloud is not False else BUSY_STARVE_S\n", "matches": 1},
    {"why": "v3884 - the local game running beside the client reads as a stream",
     "file": "tv/self_prove.py",
     "find": "        return bool(hits) and not any(_POSIX_GAME.search(ln) for ln in hits)\n",
     "replace": "        return bool(hits)\n", "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
