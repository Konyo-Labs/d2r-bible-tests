#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v3901 (REG-3751, #217) - THE RECORDER'S REAPER WRITES ITS INTENT BEFORE IT DELETES, AND A STOPPED DELETE KEEPS ITS RECORD.

The Grok CLI's second look on v3899 (Mac ledger, finding 2): "_reap_record ... a crash after write() ... can still drop the
reap line while the caller believes the record landed". Reproduced in part. The line itself is safe once written (the `with`
closes the file before the True, so a process crash after it loses nothing), but the ORDER was the hole: the disk-floor reel
reaper ran rmtree / os.remove FIRST and wrote its reap-log line SECOND. A recorder stopped between the two - an update's
relaunch, a kill, a crash, a long rmtree of an 11,000-frame reel - left a reel gone with no line at all, the #217 shape
(reels off the shelf with no deleter's record).

Now an INTENT line goes down before the delete (`removed: null`, `intent: true`) and the outcome line still follows. The
river's deleter-record reader and the reel's custody both credit an intent line whose outcome never landed - in words that
say the recorder stopped mid-delete - so such a reel is never "gone with no record at all".

DRIVEN: the real _reap_record into a reap log of our own, the real river_stamp._deleter_records and reel_custody._recorder
over it, and the reaper's own source for the order (one anchor each, comments stripped). RED_PROOF below.
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

import tv_diablo as TVD  # noqa: E402
import river_stamp as RS  # noqa: E402
import reel_custody as RC  # noqa: E402

A, B, C = "reel_s_1500000000000_00001", "reel_s_1500000100000_00002", "reel_s_1500000200000_00003"


def _code(path):
    with io.open(os.path.join(HERE, os.path.basename(path)), encoding="utf-8") as fh:
        return "\n".join(l.split("#", 1)[0].rstrip() for l in fh.read().split("\n"))


class AReapWritesItsIntentFirst(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="reap_intent_")
        self.hist = os.path.join(self.tmp, "frames", "hist")
        os.makedirs(self.hist)
        self.log = TVD._reap_log_path(self.hist)
        self._real = TVD._reap_log_path
        TVD._reap_log_path = lambda *a, **k: self.log

    def tearDown(self):
        TVD._reap_log_path = self._real
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _rows(self):
        with io.open(self.log, encoding="utf-8") as fh:
            return [json.loads(l) for l in fh if l.strip()]

    def test_the_intent_line_says_null_never_removed(self):
        self.assertIs(TVD._reap_record(A, 7, None, 3, intent=True), True)
        row = self._rows()[-1]
        self.assertIs(row.get("intent"), True)
        self.assertIsNone(row.get("removed"), "an intent line claimed an outcome before the delete ran: %r" % row)

    def test_a_delete_stopped_after_its_intent_keeps_its_record(self):
        """* THE POINT - A: intent, then the recorder stopped (no outcome). B: intent + outcome. C: outcome only (old)."""
        TVD._reap_record(A, 7, None, 3, intent=True)
        TVD._reap_record(B, 4, None, 3, intent=True)
        TVD._reap_record(B, 4, True, 3)
        TVD._reap_record(C, 2, True, 3)
        recs, unread = RS._deleter_records(self.hist)
        self.assertEqual(unread, [])
        self.assertIn(A, recs, "a reel the recorder began removing reads as gone with no record at all")
        self.assertIn("INTENT line only", recs[A])
        self.assertIn("its reap log", recs[B])
        self.assertNotIn("INTENT", recs[B], "a reap that finished was called stopped mid-delete")
        self.assertIn(C, recs)

    def test_baseline_a_failed_delete_is_not_credited(self):
        """intent, then an outcome that says the delete did NOT happen: no deleter's record for the reel"""
        TVD._reap_record(A, 7, None, 3, intent=True)
        TVD._reap_record(A, 7, False, 3)
        recs, _unread = RS._deleter_records(self.hist)
        self.assertNotIn(A, recs, "a delete whose outcome says it failed was credited as a deleter's record")

    def test_custody_names_the_stopped_delete(self):
        src = {"shelf": set(), "paths": {"hist": self.hist},
               "reaps": [{"ts": 1500000000000, "reel": A, "frames": 7, "removed": None, "intent": True}]}
        h = RC._recorder(A, "s_1500000000000_00001", src, False)
        self.assertIn("INTENT", h["why"])
        self.assertIn("stopped mid-delete", h["why"])
        src["reaps"] = []
        self.assertIn("does not name it", RC._recorder(A, "s_1500000000000_00001", src, False)["why"])

    def test_the_reaper_writes_the_intent_before_each_delete(self):
        code = _code("tv_diablo.py")
        whole = ("                                             intent=True)\n"
                 "                                _shr.rmtree(_vp, ignore_errors=True)")
        part = ("                                             kept=_pick[\"kept\"], river=_rv, intent=True)\n"
                "                                for _f in _pick[\"gone\"]:")
        self.assertEqual(code.count(whole), 1, "the whole-reel rmtree no longer follows its intent line")
        self.assertEqual(code.count(part), 1, "the partial release no longer follows its intent line")


RED_PROOF = [
    {"why": "REG-3751 - the whole-reel reaper deletes before any record again (no intent line)",
     "file": "tv/tv_diablo.py",
     "find": "                                _reap_record(_pick[\"reel\"], _n, None, len(_all), names=_pick[\"gone\"], river=_rv,\n"
             "                                             intent=True)\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3751 - an intent line with no outcome is not read as the deleter's record (gone with no record again)",
     "file": "tv/river_stamp.py",
     "find": "                if nm not in outcomes:\n",
     "replace": "                if False:\n",
     "matches": 1},
    {"why": "REG-3751 - the intent line claims removed before the delete ran",
     "file": "tv/tv_diablo.py",
     "find": "               \"removed\": (None if intent else bool(removed)), \"shelfBefore\": int(shelf), \"by\": str(by),\n",
     "replace": "               \"removed\": bool(removed), \"shelfBefore\": int(shelf), \"by\": str(by),\n",
     "matches": 1},
    {"why": "REG-3751 - the reel's custody says nothing about a delete stopped after its intent",
     "file": "tv/reel_custody.py",
     "find": "    elif intended:\n",
     "replace": "    elif False:\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
