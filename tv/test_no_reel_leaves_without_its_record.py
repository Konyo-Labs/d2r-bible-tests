#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""REG-3725 (#217) - NO RECORD, NO DELETE: A REEL NEVER LEAVES THE SHELF WHILE ITS CLOSURE-LEDGER ROW COULD NOT BE WRITTEN.

His Mac, measured 11-11: 34 reels left the shelf with no deleter's record (river_stamp.close_out, dry: "34 with no record
at all"), 29 of them between 10:08 and 21:22 on 10-24. He deleted nothing by hand. The hunt has not named that day's hand
yet, but it found a door that does exactly this: reel_retention.apply_plan wrote the closure ledger (reel_tombstones.json)
inside a try, kept the error as `tombstoneWhy`, and ran the rmtree anyway - "a failure here is reported and does NOT block
the delete". So one failed write is a reel gone with no row, which is what the river's corroborator
(river-log-matches-the-shelf) calls a deletion nobody logged.

Now a ledger that would not write holds every reel: nothing is removed, each reel is named HELD, and the next pass retries.

DRIVEN: the real apply_plan on a shelf of our own (TV_HIST), with the lock and the evidence index stubbed for this
selection only and the ledger writer made to fail. BASELINE: the same plan with a working ledger removes both reels and
writes both rows, so the case can tell the two apart. RED_PROOF below. [[the-unjoined-end]] [[unknown-stays-unknown]]
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import console_safe  # noqa: E402
console_safe.enable()

import reel_retention as RR  # noqa: E402

REELS = ("reel_s_1700000000000_00001", "reel_s_1700000100000_00002")


class _Shelf(object):
    """Two spent reels on a shelf of our own; the lock and the evidence index answer for this selection only."""

    def __init__(self, tomb_fails):
        self.tomb_fails = tomb_fails

    def __enter__(self):
        self.tmp = tempfile.mkdtemp(prefix="norecord_")
        self.hist = os.path.join(self.tmp, "hist")
        for r in REELS:
            os.makedirs(os.path.join(self.hist, r))
            for f in ("f_1700000000.jpg", "f_1700000001.jpg", "index.json"):
                with io.open(os.path.join(self.hist, r, f), "w") as fh:
                    fh.write("x")
        self._env = os.environ.get("TV_HIST")
        os.environ["TV_HIST"] = self.hist
        import frame_authority as _fa
        import self_arming as _sa
        self._fa, self._wi, self._sa, self._may, self._tomb = _fa, _fa.witness_index, _sa, _sa.may, RR._tombstone
        _fa.witness_index = lambda *a, **k: {"haveIndex": True, "ok": True, "frames": set(), "cited": set(),
                                             "sessions": set(), "perStore": {}}
        _real = self._may
        _sa.may = lambda name, *a, **k: ((True, "stubbed for this law") if name == "frame.release"
                                         else _real(name, *a, **k))
        if self.tomb_fails:
            def _fails(hist, cands):
                raise OSError("No space left on device")
            RR._tombstone = _fails
        return self

    def __exit__(self, *a):
        self._fa.witness_index = self._wi
        self._sa.may = self._may
        RR._tombstone = self._tomb
        if self._env is None:
            os.environ.pop("TV_HIST", None)
        else:
            os.environ["TV_HIST"] = self._env
        shutil.rmtree(self.tmp, ignore_errors=True)

    def apply(self):
        p = {"ok": True, "hist": self.hist, "freeMb": 2,
             "candidates": [{"reel": r, "mb": 1, "tag": "eligible", "why": "fixture: spent"} for r in REELS]}
        return RR.apply_plan(p, yes=True)

    def left(self):
        return [r for r in REELS if os.path.isdir(os.path.join(self.hist, r))]


class NoReelLeavesWithoutItsRecord(unittest.TestCase):

    def test_a_ledger_that_will_not_write_deletes_nothing(self):
        """* THE POINT - the closure ledger fails, both reels stay, both are named HELD, the answer says why"""
        with _Shelf(tomb_fails=True) as sh:
            out = sh.apply()
            self.assertEqual(sh.left(), list(REELS), "a reel left the shelf while its closure-ledger row could not be "
                                                     "written - a deletion nobody logged (#217)")
            self.assertEqual(out.get("removed"), [])
            self.assertIs(out.get("ok"), False)
            held = sorted(f.get("reel") for f in out.get("failed") or [] if "HELD" in str(f.get("why")))
            self.assertEqual(held, sorted(REELS), "the held reels are not named in the answer: %r" % out.get("failed"))
            self.assertIn("No space left on device", str(out.get("tombstoneWhy")))
            self.assertIn("nothing deleted", str(out.get("why")))

    def test_baseline_a_working_ledger_records_then_removes(self):
        """BASELINE - with a ledger that writes, the same plan removes both reels and leaves a row for each"""
        with _Shelf(tomb_fails=False) as sh:
            out = sh.apply()
            self.assertEqual(sh.left(), [], "the fixture plan no longer removes anything - the case cannot tell a held "
                                            "delete from a refused one: %r" % (out.get("why") or out.get("failed")))
            with io.open(RR._tombstone_path(sh.hist), encoding="utf-8") as fh:
                rows = [t.get("reel") for t in (json.load(fh).get("reels") or [])]
            self.assertEqual(sorted(rows), sorted(REELS))
            self.assertEqual(out.get("tombstoned"), 2)


class TheDiskFloorSaysWhenItsRecordFails(unittest.TestCase):
    """REG-3726 (#217) - the recorder's disk floor deletes FIRST (a full disk stops recording), then writes its reap-log
    line; a failed line was `except: pass`, so a reel it took could leave no trace. Now it says so, naming the reel."""

    def _record(self, path):
        import contextlib
        import tv_diablo as TVD
        buf = io.StringIO()
        real = TVD._reap_log_path
        TVD._reap_log_path = lambda *a, **k: path
        try:
            with contextlib.redirect_stdout(buf):
                ok = TVD._reap_record("reel_s_1700000000000_00009", 3, True, 5)
        finally:
            TVD._reap_log_path = real
        return ok, buf.getvalue()

    def test_a_reap_line_that_will_not_write_is_said_out_loud(self):
        tmp = tempfile.mkdtemp(prefix="reaplog_")
        try:
            ok, said = self._record(os.path.join(tmp, "no_such_dir", "reel_reaps.jsonl"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertIs(ok, False)
        self.assertIn("REAP RECORD NOT WRITTEN", said, "a reap-log line that failed to write was swallowed again")
        self.assertIn("reel_s_1700000000000_00009", said, "the loud line does not name the reel that went")

    def test_baseline_a_writable_reap_log_gets_its_line(self):
        tmp = tempfile.mkdtemp(prefix="reaplog_")
        try:
            path = os.path.join(tmp, "reel_reaps.jsonl")
            ok, said = self._record(path)
            with io.open(path, encoding="utf-8") as fh:
                row = json.loads(fh.read().strip().splitlines()[-1])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertIs(ok, True)
        self.assertNotIn("REAP RECORD NOT WRITTEN", said)
        self.assertEqual((row.get("reel"), row.get("removed")), ("reel_s_1700000000000_00009", True))


RED_PROOF = [
    {"why": "REG-3725 (#217) - a closure ledger that would not write no longer holds the delete: the rmtree runs and the "
            "reel leaves the shelf with no record again",
     "file": "tv/reel_retention.py",
     "find": "    if tomb is None and go:\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "REG-3726 (#217) - the recorder's disk floor swallows a reap-log line that would not write again, so a reel "
            "it took leaves no trace",
     "file": "tv/tv_diablo.py",
     "find": "        _dbg(\"REAP RECORD NOT WRITTEN (%s: %s) - %s left the shelf with no reap-log line\"\n",
     "replace": "        (lambda *_a: None)(\"REAP RECORD NOT WRITTEN (%s: %s) - %s left the shelf with no reap-log line\"\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
