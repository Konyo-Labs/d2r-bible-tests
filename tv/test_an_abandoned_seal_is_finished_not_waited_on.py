#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""REG-1679 - AN ABANDONED SEAL IS FINISHED, NOT WAITED ON FOR EVER.

MEASURED on his ALT (the river-chain audit, 2026-10-01): three reels carried an index.json.tmp 23.7 h, 36.3 h and
85.8 h old - each holding the NEWER index (1,283 frames on disk, 1,280 in index.json). reel_repair called any temp "a
seal in flight" and skipped the reel for ever. The recorder's seal retried os.replace at once, into the same Windows
lock, and left the temp stranded.

Driven through the REAL reel_repair.inspect / repair and reel_index.replace_with_retry over a temp shelf (never his):
  1. a FRESH temp is still a seal in flight and is not touched;
  2. a temp older than STALE_TMP_S is ABANDONED: when it lists at least what index.json lists it is installed (the
     seal's own last step), and when it lists less it is kept aside, never dropped, and the index stands;
  3. the replace waits out a brief lock and gives up loudly (the last error raised) when the lock never lifts;
  4. both index writers use that one rule (the recorder's seal and reel_index's own writer).
RED_PROOF below.
"""
import io
import json
import os
import shutil
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import reel_index as RI  # noqa: E402
import reel_repair as RR  # noqa: E402


def _index(n):
    return {"sessionId": "s_1500000000001_1", "n": n,
            "frames": [{"f": "f_%d.jpg" % (1500000000000 + k), "ts": 1500000000000 + k} for k in range(n)]}


class _Reel(unittest.TestCase):

    def setUp(self):
        self.hist = tempfile.mkdtemp(prefix="abandoned_seal_")
        self.addCleanup(shutil.rmtree, self.hist, True)
        self.reel = os.path.join(self.hist, "reel_s_1500000000001_1")
        os.makedirs(self.reel)
        for k in range(5):
            with open(os.path.join(self.reel, "f_%d.jpg" % (1500000000000 + k)), "wb") as fh:
                fh.write(b"\xff\xd8\xff\xd9")

    def write(self, name, obj, age_s=0):
        p = os.path.join(self.reel, name)
        with io.open(p, "w", encoding="utf-8") as fh:
            json.dump(obj, fh)
        if age_s:
            t = time.time() - age_s
            os.utime(p, (t, t))
        return p

    def listed(self):
        return RR.read_index(self.reel)[1]


class AnAbandonedSealIsFinished(_Reel):

    def test_a_fresh_temp_is_still_a_seal_in_flight(self):
        self.write("index.json", _index(3))
        self.write("index.json.tmp", _index(5), age_s=5)
        row = RR.inspect(self.reel)
        self.assertEqual(row["state"], RR.SEALING, "a seal in flight was raced: %r" % row)

    def test_an_old_temp_is_abandoned_and_its_newer_index_installed(self):
        self.write("index.json", _index(3))
        self.write("index.json.tmp", _index(5), age_s=RR.STALE_TMP_S + 60)
        row = RR.inspect(self.reel)
        self.assertEqual(row["state"], RR.ABANDONED, "a temp days old still reads as a seal in flight: %r" % row)
        self.assertTrue(RR.repair(row))
        self.assertEqual(self.listed(), 5, "the newer index the seal meant to install is still stranded")
        self.assertFalse(os.path.exists(os.path.join(self.reel, "index.json.tmp")))

    def test_a_temp_that_lists_less_is_kept_aside_and_the_index_stands(self):
        self.write("index.json", _index(4))
        self.write("index.json.tmp", _index(2), age_s=RR.STALE_TMP_S + 60)
        row = RR.inspect(self.reel)
        self.assertTrue(RR.repair(row))
        self.assertEqual(self.listed(), 4, "an older temp overwrote a fuller index")
        kept = [n for n in _fx_tmp.list_own(self.reel) if n.startswith("index.json.tmp.abandoned-")]
        self.assertEqual(len(kept), 1, "the abandoned temp was dropped instead of kept aside: %r" % _fx_tmp.list_own(self.reel))

    def test_an_abandoned_temp_with_no_index_still_leaves_the_reel_playable(self):
        self.write("index.json.tmp", _index(5), age_s=RR.STALE_TMP_S + 60)
        row = RR.inspect(self.reel)
        self.assertEqual(row["state"], RR.ABANDONED)
        self.assertTrue(RR.repair(row))
        self.assertEqual(self.listed(), 5)


class TheReplaceWaitsOutALock(unittest.TestCase):

    def test_a_brief_lock_is_waited_out(self):
        calls, naps = [], []

        def rep(a, b):
            calls.append((a, b))
            if len(calls) < 3:
                raise PermissionError("locked by another process")
        RI.replace_with_retry("a", "b", attempts=6, pause_s=0.01, _replace=rep, _sleep=naps.append)
        self.assertEqual(len(calls), 3, "the replace did not try again after a lock")
        self.assertEqual(len(naps), 2, "the retries did not wait between tries - an immediate retry hits the same lock")

    def test_a_lock_that_never_lifts_raises_its_last_error(self):
        def rep(a, b):
            raise PermissionError("still locked")
        with self.assertRaises(PermissionError):
            RI.replace_with_retry("a", "b", attempts=3, pause_s=0, _replace=rep, _sleep=lambda s: None)

    def test_both_index_writers_use_the_one_rule(self):
        src = io.open(os.path.join(HERE, "tv_diablo.py"), encoding="utf-8").read()
        code = "\n".join(l.split("#", 1)[0] for l in src.split("\n"))
        self.assertEqual(code.count('_rix.replace_with_retry(_tmp, os.path.join(_reel, "index.json"))'), 1,
                         "the recorder's seal replaces its index without the retry rule")
        self.assertIn("replace_with_retry", RI._write_json_atomic.__code__.co_names,
                      "reel_index's own writer replaces without the retry rule")


RED_PROOF = [
    {"why": "REG-1679 - any temp is a seal in flight again: an abandoned one is skipped for ever",
     "file": "reel_repair.py",
     "find": "        row[\"state\"] = ABANDONED if (row[\"tmpAgeS\"] is not None and row[\"tmpAgeS\"] >= STALE_TMP_S) else SEALING\n",
     "replace": "        row[\"state\"] = SEALING\n",
     "matches": 1},
    {"why": "REG-1679 - the abandoned seal's newer index is never installed",
     "file": "reel_repair.py",
     "find": "        if want is not None and (have is None or want >= have):\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "REG-1679 - an older temp overwrites a fuller index",
     "file": "reel_repair.py",
     "find": "        if want is not None and (have is None or want >= have):\n",
     "replace": "        if want is not None:\n",
     "matches": 1},
    {"why": "REG-1679 - the replace retries at once, into the same lock",
     "file": "reel_index.py",
     "find": "            if k + 1 < n:\n                nap(pause)\n",
     "replace": "            if False:\n                nap(pause)\n",
     "matches": 1},
    {"why": "REG-1679 - the replace tries once and gives up on a brief lock",
     "file": "reel_index.py",
     "find": "    n = REPLACE_ATTEMPTS if attempts is None else max(1, int(attempts))\n",
     "replace": "    n = 1\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
