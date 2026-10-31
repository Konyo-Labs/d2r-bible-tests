# -*- coding: utf-8 -*-
"""#109 — /api/river'S LEDGER READS DO NOT GROW WITH THE REELS: ONCE FOR ITS OWN WALK, NOT TWICE PER REEL.

MEASURED 2026-09-30 on his ALT (over SSH, read-only): 266 reels on the shelf, 145 MB of RAM free, and /api/river did
not answer inside 60 s. The route asks river_stamp.current() and history() about every reel it lists, and each of
those re-read and re-parsed the WHOLE ledger - current() through history() - so a request read the ledger twice per
reel: quadratic in reels x rows, on the machine least able to afford it.

Now the route reads the ledger once for its own walk (rows()), groups it by reel once (index()), and hands that report
to history() and current(). One derivation - the same answers, including the never-stamped reel and the unreadable
store, which must stay two different sentences. Two other readers in the request (the census, and the router's lane
overlay inside river_lanes) read it once each per request - a constant, so the law pins the SCALING: the number of reads
is the same for 12 reels as for 48.

⚠ MEASURED BEFORE CLAIMING: the ALT's ledger is 141 KB / 480 rows, so this term cost it seconds, not the whole minute -
the rest of that route's time is measured separately (#109), never assumed to be this.

Driven, never re-implemented: river_stamp over a throwaway ledger, and the real /api/river branch of the console's GET
handler over that ledger and an empty temp shelf. [[paid-work-with-no-memory]] [[unknown-stays-unknown]]
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
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import river_stamp as RS  # noqa: E402

RED_PROOF = [
    {
        "why": "#109 - the route asks each reel's station off the disk again: two ledger reads per reel",
        "file": "control_app.py",
        "find": "                    _cur = _RVS.current(_r, report=_raw)\n",
        "replace": "                    _cur = _RVS.current(_r)\n",
        "matches": 1,
    },
    {
        "why": "#109 - the route asks each reel's journey off the disk again",
        "file": "control_app.py",
        "find": "                    _hops = (_RVS.history(_r, report=_raw) or {}).get(\"stations\") or []\n",
        "replace": "                    _hops = (_RVS.history(_r) or {}).get(\"stations\") or []\n",
        "matches": 1,
    },
    {
        "why": "#109 - history() ignores the report it was handed and reads the ledger anyway",
        "file": "river_stamp.py",
        "find": "    rep = report if isinstance(report, dict) else rows(path)\n",
        "replace": "    rep = rows(path)\n",
        "matches": 1,
    },
    {
        "why": "#109 - the index keeps only each reel's first stamp: a journey loses its later stations",
        "file": "river_stamp.py",
        "find": "            by.setdefault(str(r.get(\"reel\")), []).append(r)\n",
        "replace": "            by.setdefault(str(r.get(\"reel\")), [r])\n",
        "matches": 1,
    },
]

REELS = ["reel_s_1790000%03d000_1" % i for i in range(12)]


def _ledger(d):
    """12 reels, each stamped CAPTURE -> PRINTER -> TOMBSTONE except the last two (one and two stamps)."""
    p = os.path.join(d, "river_stamps.jsonl")
    at = 1790000000000
    with io.open(p, "w", encoding="utf-8") as fh:
        for i, r in enumerate(REELS):
            stations = ["CAPTURE", "PRINTER", "TOMBSTONE"][: (1 if i == 10 else 2 if i == 11 else 3)]
            for st in stations:
                at += 1000
                fh.write(json.dumps({"reel": r, "station": st, "at": at, "by": "fixture", "byKind": "observer",
                                     "why": "%s reached %s" % (r, st)}) + "\n")
    return p


class TheLedgerIsReadOnce(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="river_once_")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.path = _ledger(self.d)

    def test_the_index_groups_each_reel_in_file_order(self):
        rep = RS.index(RS.rows(self.path))
        self.assertEqual(sorted(rep["byReel"]), sorted(REELS))
        self.assertEqual([r["station"] for r in rep["byReel"][REELS[0]]], ["CAPTURE", "PRINTER", "TOMBSTONE"])
        again = RS.index(rep)
        self.assertIs(again, rep, "indexing twice rebuilt the index")
        failed = RS.index({"ok": False, "why": "would not read"})
        self.assertNotIn("byReel", failed, "an unreadable store was indexed as if it were empty")

    def test_the_same_answers_as_asking_the_disk(self):
        rep = RS.index(RS.rows(self.path))
        for reel in REELS + ["reel_never_stamped"]:
            self.assertEqual(RS.history(reel, report=rep), RS.history(reel, self.path), reel)
            self.assertEqual(RS.current(reel, report=rep), RS.current(reel, self.path), reel)
        unread = RS.history(REELS[0], report={"ok": False, "why": "the stamp store would not read (OSError)"})
        self.assertFalse(unread["ok"])
        self.assertIn("UNKNOWN", unread["why"], "an unreadable store read as a reel never stamped")

    def _route(self, ledger):
        import control_app as ca
        import river_lanes as RL
        shelf = os.path.join(self.d, "hist")
        os.makedirs(shelf, exist_ok=True)
        real_rows, calls = RS.rows, []

        def counted(path=None):
            calls.append(path)
            return real_rows(ledger)
        # v3849 — the route reads the last finished walk and returns before the success payload
        # when this process has none. Plant one under the empty-hide key, and keep lanes() from
        # walking a real shelf if that key is missed. The population census is not this law.
        finished = {"ok": True, "lanes": [], "reconciles": True}
        RL._LAST[()] = {"at": time.time(), "out": dict(finished)}
        got = {}
        h = ca.Handler.__new__(ca.Handler)
        h.path = "/api/river"
        h._json = lambda code, obj: got.update(code=code, obj=obj)
        try:
            with mock.patch.object(RS, "rows", counted), \
                    mock.patch.object(ca, "HIST_DIR", shelf), \
                    mock.patch.object(ca, "shelf_hidden_reels", lambda *a, **k: ([], "")), \
                    mock.patch.object(ca, "reel_census", lambda *a, **k: {"ok": True, "why": "fixture"}), \
                    mock.patch.object(RL, "lanes", lambda *a, **k: dict(finished)):
                h.do_GET()
        finally:
            RL._LAST.pop((), None)
            RL._REFRESH_ON.discard(())
        return got, calls

    def test_the_reads_do_not_grow_with_the_reels(self):
        big_d = os.path.join(self.d, "big")
        os.makedirs(big_d)
        big = os.path.join(big_d, "river_stamp.jsonl")
        with io.open(big, "w", encoding="utf-8") as fh:
            for i in range(48):
                fh.write(json.dumps({"reel": "reel_s_%d_9" % (1790100000000 + i * 1000), "station": "CAPTURE",
                                     "at": 1790100000000 + i, "by": "fixture", "byKind": "observer"}) + "\n")
        _g12, few = self._route(self.path)
        _g48, many = self._route(big)
        self.assertEqual(len(many), len(few), "the ledger was read %d times for 12 reels and %d for 48 - a read per "
                                              "reel is back, quadratic on the ALT's shelf" % (len(few), len(many)))
        self.assertLessEqual(len(few), 3, "one request read the ledger %d times: its own walk, the census and the "
                                          "router's lane overlay are the three that belong" % len(few))

    def test_the_route_answers_every_reel(self):
        got, _calls = self._route(self.path)
        self.assertEqual(got.get("code"), 200, got)
        reels = {r.get("reel"): r for r in (got.get("obj") or {}).get("detail") or []}   # `reels` is the census count
        self.assertEqual(sorted(reels), sorted(REELS), "the route stopped listing every stamped reel")
        self.assertEqual(reels[REELS[0]].get("at"), "TOMBSTONE")
        self.assertEqual(reels[REELS[10]].get("at"), "CAPTURE")
        self.assertEqual([s.get("station") for s in reels[REELS[11]].get("history") or []], ["CAPTURE", "PRINTER"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
