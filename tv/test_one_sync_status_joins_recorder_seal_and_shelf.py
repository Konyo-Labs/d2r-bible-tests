# -*- coding: utf-8 -*-
"""v3860 (#230): one sync status joins the recorder, the hourly seal, the published digest and the Shelf.

His words, 2026-11-03: "make sure the shadow reader recorder and the shelf and everything is synced meaning a joined
logic". The ALT filmed every hour while its Shelf read 08:00 and nothing said so. machine_sync.judge is the one verdict;
/api/sync, /api/sessions (this PC's Shelf) and the published digest (every shadow's Shelf) carry it, and one badge draws it.

RED_PROOF below: each one, applied, turns this law red."""
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable; enable()

NOW = 1793711000000
M = 60000


class OneSyncStatus(unittest.TestCase):
    def j(self, **f):
        import machine_sync as ms
        return ms.judge(f, NOW)

    def test_a_silent_recorder_with_the_game_up_is_red(self):
        r = self.j(gameUp=True, frameAt=NOW - 10 * M, sealAt=NOW - 20 * M, publishAt=NOW - 15 * M, shelfAt=NOW)
        self.assertEqual("red", r["level"]); self.assertEqual("red", r["lanes"]["recorder"])
        self.assertIn("silent", r["say"])

    def test_silence_with_the_game_down_is_not(self):
        r = self.j(gameUp=False, frameAt=NOW - 600 * M, sealAt=NOW - 20 * M, publishAt=NOW - 15 * M, shelfAt=NOW)
        self.assertEqual("ok", r["level"], r["say"])

    def test_the_alt_on_nov_3_is_red_not_silent(self):
        # the ALT's real stamps: filming, seal failed at 15:00, last good seal 10-29, digest 13:17, shelf from 08:00
        r = self.j(gameUp=True, frameAt=NOW - 5000, rollingSince=1793710955767, rotateAfterS=3600,
                   sealAt=1793239218985, sealFailAt=1793710810167, publishAt=1793704664894, shelfAt=1793685749734)
        self.assertEqual("red", r["lanes"]["seal"])
        self.assertEqual("warn", r["lanes"]["shelf"])
        self.assertEqual("red", r["level"])

    def test_a_digest_behind_the_last_seal_warns(self):
        r = self.j(gameUp=True, frameAt=NOW, sealAt=NOW - 5 * M, publishAt=NOW - 120 * M, shelfAt=NOW)
        self.assertEqual("warn", r["lanes"]["publish"])

    def test_all_in_step_is_ok(self):
        r = self.j(gameUp=True, frameAt=NOW - 3000, rollingSince=NOW - 10 * M, sealAt=NOW - 11 * M,
                   publishAt=NOW - 5 * M, shelfAt=NOW - M, shelfNewestAt=NOW - 10 * M)
        self.assertEqual("ok", r["level"], r["say"])

    def test_every_surface_reads_the_one_verdict(self):
        src = open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        self.assertIn('if path == "/api/sync":', src)
        self.assertIn('"sync": sync_status()}', src)
        self.assertIn('_sy = sync_status(now_ms)', src)   # v3859 - the digest carries that verdict minus its own publish lane
        self.assertIn('d["sync"] = __import__("machine_sync").published_view(_sy)', src)
        self.assertIn('_v["sync"] = ((rec or {}).get("digest") or {}).get("sync")', src)
        ui = open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()
        self.assertIn("_syncBadgeHtml(d.sync)", ui)
        self.assertIn("TH.sync = (j && j.sync) || null;", ui)

    def test_sync_status_never_raises_on_a_cold_console(self):
        import control_app as ca
        out = ca.sync_status(NOW)
        self.assertIn(out["level"], ("ok", "warn", "red", "unknown"))


RED_PROOF = [
    {"why": "a silent recorder with the game up reads fine",
     "file": "tv/machine_sync.py",
     "find": "        elif now - frame > RECORDER_SILENT_MS:\n",
     "replace": "        elif False:\n",
     "matches": 1},
    {"why": "a failed seal is not red",
     "file": "tv/machine_sync.py",
     "find": "    if fail is not None and (seal is None or fail > seal):\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "the shadow's Shelf stops drawing the badge",
     "file": "tv/control_ui.html",
     "find": "_syncBadgeHtml(d.sync) : '');",
     "replace": "'' : '');",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
