# -*- coding: utf-8 -*-
"""v3859 (his Mac Fleet, 2026-11-03 17:27) - A REEL THE DRAIN HOLDS IS NOT A STUCK REEL.

His Konyo row read "river stuck" while /api/river's stuck.rows held 4 rows and 3 said "held by the drain, not owed"
(REG-3053 fixed the words, never the chip). The chip counted every row. Now a row the drain holds whole (server
`held: true`, or a reason opening "held by the drain, not owed") is drawn neutral, "river flowing · N held by the
drain"; "river stuck" stays for an owed row, and a lane's debt names itself ("vault lane owes 8"). The 4 real row
shapes are the fixture. The server flags a whole-held row. "locks shut" is the census, untouched by held rows.
"""
import os
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import test_one_river_chip_per_row as H  # noqa: E402  (the cut-and-run harness for _fleetStuckChip)
import fixture_tmp as _fx  # noqa: E402
_fx.contain()
import control_app as CA  # noqa: E402
import reel_retention as RR  # noqa: E402

CUR = {"census": "current", "key": "current", "blind": 0}
HELD = [
    {"station": "CAPTURE", "n": 5, "oldestS": 9 * 86400, "window": False,
     "why": "older than the newest 16 - held by the drain, not owed: 5 panels-never-banked (no bank yet)"},
    {"station": "ROUTED", "n": 6, "oldestS": 12 * 86400, "window": False,
     "why": "older than the newest 16 - held by the drain, not owed: 4 zero-pages (x); 2 panels-never-banked (y)"},
    {"station": "STATION", "n": 1, "oldestS": 8 * 86400, "window": False, "why": "held by the drain, not owed"},
]
PRINTER = {"station": "PRINTER", "n": 1, "oldestS": 30 * 3600,
           "why": "vault lane: owes 8, 6898 read(s) on record; 17 ruled empty by the sweep"}


class AHeldReelIsNotRiverStuck(unittest.TestCase):
    def test_held_only_rows_read_river_flowing(self):
        html = H._html(CUR, HELD, 60)
        self.assertNotIn("river stuck", html)
        self.assertNotIn("locks shut", html)
        self.assertEqual(html.count("fleet-riverstuck"), 0)
        self.assertIn("river flowing \u00b7 12 held by the drain", html)

    def test_a_river_whose_doors_are_shut_is_not_called_flowing(self):
        """#24 (GrokBot 6700580776: "river flowing" beside "safety net: test_control RED - its locks shut") - held reels
        whose river doors are shut wait on those locks; "flowing" only while every river door may act"""
        html = H._html(dict(CUR, locksShut=["reel.route", "frame.release"]), HELD, 60)
        self.assertNotIn("river flowing", html, "a river with two shut doors read flowing: %r" % html[:300])
        self.assertIn("12 held by the drain \u00b7 the river waits on 2 shut locks", html)

    def test_an_owed_lane_row_is_stuck_and_named(self):
        html = H._html(CUR, HELD + [PRINTER], 60)
        self.assertIn(">river stuck<", html)
        self.assertIn(">vault lane owes 8<", html)
        self.assertNotIn("river flowing", html)
        self.assertIn("also held by the drain, not owed: CAPTURE 5, ROUTED 6, STATION 1", html)

    def test_a_partly_owed_row_stays_stuck(self):
        mixed = dict(HELD[1], why="older than the newest 16 - the drain owes them a tombstone (2 of them; the rest "
                                  "held by the drain, not owed: 4 zero-pages)")
        self.assertIn(">river stuck<", H._html(CUR, [mixed], 60))

    def test_held_rows_never_open_the_locks(self):
        html = H._html({"census": "stale", "key": "stale"}, HELD, 60)
        self.assertIn("locks shut", html)

    def test_the_server_flags_a_whole_held_row(self):
        T, DAY = 1793000000000, 86400000
        new = ["reel_s_%d_%d" % (T + i * 60000, i) for i in range(1, 17)]
        old = ["reel_s_%d_%d" % (T - 10 * DAY + i, 900 + i) for i in range(3)]
        rows = [{"reel": r, "station": "CAPTURE", "at": RR._reel_ts(r)} for r in new + old]
        holds = {r: {"tag": "panels-never-banked", "why": "no bank"} for r in old}
        for held, want in ((holds, True), (dict(list(holds.items())[:2]), None)):
            with mock.patch.object(CA, "_RETENTION", {"holds": held, "checked": T}):
                out = CA._river_stuck_for_wire(T + 2 * DAY, _rows=rows, _shelf=new + old, _fixtures=(), _remnants=())
            self.assertEqual([(e["station"], e["n"], e.get("held")) for e in out], [("CAPTURE", 3, want)])

    def test_the_red_proof_finds_match_once(self):
        for p in RED_PROOF:
            with open(os.path.join(H.ROOT, p["file"]), encoding="utf-8") as fh:
                self.assertEqual(fh.read().count(p["find"]), p["matches"], p["why"])


RED_PROOF = [
    {"why": "#24 - a river whose own doors are shut reads 'river flowing' again",
     "file": "tv/control_ui.html",
     "find": "      var _rShut = (hs && Array.isArray(hs.locksShut)) ? hs.locksShut.filter(function (l) { return typeof l === 'string' && l; }) : [];\n",
     "replace": "      var _rShut = [];\n",
     "matches": 1},
    {"why": "held rows count as stuck again: the chip says river stuck over the drain's holds",
     "file": "tv/control_ui.html",
     "find": "    var _heldList = Array.isArray(sk) ? sk.filter(_isHeld) : [];",
     "replace": "    var _heldList = [];", "matches": 1},
    {"why": "the lane's debt is not named beside the chip",
     "file": "tv/control_ui.html",
     "find": "        bits.push('<span class=\"fleet-riverowes\" title=\"' + escC(tip) + '\">' + escC(x) + '</span>'); });",
     "replace": "        void x; });", "matches": 1},
    {"why": "the server never flags a whole-held row",
     "file": "tv/control_app.py",
     "find": "                e[\"held\"] = True",
     "replace": "                pass", "matches": 1},
]

if __name__ == "__main__":
    unittest.main()
