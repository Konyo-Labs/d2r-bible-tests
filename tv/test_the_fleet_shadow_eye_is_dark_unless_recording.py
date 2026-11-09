# -*- coding: utf-8 -*-
"""v3893 (#189, REG-3549) - THE FLEET'S MIDDLE EYE IS DARK UNLESS A REEL IS RECORDING.

His ruling 2026-11-09: the middle shadow-reader eye must be DARK unless a reel
is actually recording (`sh.recording`). The calm-green 'lit' of shadow-ON-while
waiting is gone. Dashed UNKNOWN for offline / unknown, the red outline for a
watcher that has STOPPED, and bright LIVE for a rolling reel stay. The hover
still says whether the film shows Diablo II; that no longer picks the colour.
RED_PROOF below.
"""
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

from test_the_fleet_shows_the_shadow_eye import LIVE, NODE, UI, _eye  # noqa: E402


@unittest.skipIf(NODE is None, "node is absent - this law RUNS the shipped card helper and will not re-implement it")
class TheFleetShadowEyeIsDarkUnlessRecording(unittest.TestCase):

    def test_waiting_is_dark_and_a_reel_is_live(self):
        waiting = _eye(LIVE)
        self.assertEqual(waiting["st"], "dark", waiting)
        self.assertIn("waiting", waiting["title"])
        self.assertIn("no reel", waiting["title"])
        self.assertNotIn("st-lit", waiting["h"])
        watching = _eye(dict(LIVE, recording=True, game=True))
        self.assertEqual(watching["st"], "live", watching)
        self.assertIn("recording the game", watching["title"])
        no_game = _eye(dict(LIVE, recording=True, game=False))
        self.assertEqual(no_game["st"], "live", no_game)
        self.assertIn("shows no Diablo II", no_game["title"])
        unk_film = _eye(dict(LIVE, recording=True))
        self.assertEqual(unk_film["st"], "live", unk_film)
        self.assertIn("not known yet", unk_film["title"])

    def test_stopped_stays_red_and_unknown_stays_dashed(self):
        stopped = _eye(dict(LIVE, working=False, beatAgeS=1400.0))
        self.assertEqual(stopped["st"], "idle", stopped)
        self.assertIn("STOPPED", stopped["title"])
        offline = _eye(LIVE, online=False)
        self.assertEqual(offline["st"], "unk", offline)
        self.assertIn("UNKNOWN", offline["title"])
        off = _eye(dict(LIVE, on=False))
        self.assertEqual(off["st"], "off", off)

    def test_the_page_has_no_calm_green_waiting_glow(self):
        with io.open(UI, encoding="utf-8") as fh:
            src = fh.read()
        self.assertEqual(src.count(".fleet-shadow.st-dark .sh-lid { stroke: #6b5a48; }"), 1)
        self.assertEqual(src.count(".fleet-shadow.st-live .sh-lid { stroke: #6df0a0; }"), 1)
        self.assertEqual(src.count(".fleet-shadow.st-lit .sh-lid { stroke: #3fbf72; }"), 0,
                         "the retired calm-green waiting stroke is still on the page")
        self.assertEqual(src.count("st = sh.recording ? 'live' : 'dark';"), 1)


RED_PROOF = [
    {"why": "v3893 (#189, REG-3549) - waiting (no reel) glows the retired calm-green again",
     "file": "tv/control_ui.html",
     "find": "      st = sh.recording ? 'live' : 'dark';\n",
     "replace": "      st = sh.recording ? 'live' : 'lit';\n",
     "matches": 1},
    {"why": "v3893 (#189, REG-3549) - a rolling reel whose film is not the game goes dark",
     "file": "tv/control_ui.html",
     "find": "      st = sh.recording ? 'live' : 'dark';\n",
     "replace": "      st = (sh.recording && sh.game === true) ? 'live' : 'dark';\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
