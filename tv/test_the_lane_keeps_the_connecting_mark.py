# -*- coding: utf-8 -*-
"""v3901 (REG-3752, #188) - THE CHRONICLE LANE KEEPS "CONNECTING TO BATTLE.NET" AS A DOOR MARK.

His 11-11 ruling: on every route the session trigger is the D2 logo -> Connecting to Battle.net -> character select,
starting at the first. v3898 (REG-3715) taught d2r_screens to see Connecting and chain() to accept it as the witness the
title is - but the chronicle lane's _mark kept only logo / title / character-select marks. It counted the Connecting frame
in its tally and dropped the mark, so a reel whose fire title fell between two frames (1 fps; the title shows 4-14 frames)
carried the logo alone, chain() saw no witness, and game_door() said the reel never entered the game.

DRIVEN: real JPEG reels on a temporary shelf, the real chronicle_line.tick over them, the real d2r_screens classifier and
chain. RED_PROOF below.
"""
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

from PIL import Image, ImageDraw  # noqa: E402
import chronicle_line as CL  # noqa: E402
import d2r_screens as DS  # noqa: E402

W, H = 800, 500
FIRE = (232, 124, 30)


def _logo():
    im = Image.new("RGB", (W, H), (4, 3, 3))
    ImageDraw.Draw(im).ellipse([W - 70, H - 50, W - 30, H - 22], fill=FIRE)       # the small fire logo, bottom right
    return im


def _connecting():
    im = Image.new("RGB", (W, H), (6, 4, 4))
    d = ImageDraw.Draw(im)
    d.rectangle([int(W * .22), int(H * .30), int(W * .78), int(H * .62)], fill=FIRE)        # the fire DIABLO title
    d.rectangle([int(W * .31), int(H * .375), int(W * .69), int(H * .585)], fill=(95, 95, 95))   # the stone bevel
    d.rectangle([int(W * .315), int(H * .385), int(W * .685), int(H * .575)], fill=(21, 21, 21))  # the dark plaque
    return im


def _idle():
    return Image.new("RGB", (W, H), (200, 205, 210))


class TheLaneKeepsTheConnectingMark(unittest.TestCase):
    T0 = 1796000000000

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="conn_lane_")
        self.hist = os.path.join(self.tmp, "frames", "hist")
        self.old = os.environ.get("TV_CHRONICLE_LINES")
        os.environ["TV_CHRONICLE_LINES"] = os.path.join(self.tmp, ".chronicle_lines.json")
        # the logo, then Connecting (the title fell between two frames), then the lobby-less idle; then two newer reels
        # (LIVE_REELS are never marked done)
        self.game = self._reel(self.T0, [_logo(), _connecting(), _connecting(), _idle()])
        self.logo_only = self._reel(self.T0 + 10 ** 6, [_logo(), _idle(), _idle()])
        self._reel(self.T0 + 2 * 10 ** 6, [_idle()])
        self._reel(self.T0 + 3 * 10 ** 6, [_idle()])

    def _reel(self, t, shots):
        name = "reel_s_%d_1" % t
        d = os.path.join(self.hist, name)
        os.makedirs(d)
        for i, im in enumerate(shots):
            im.save(os.path.join(d, "f_%d.jpg" % (t + i * 1000)), "JPEG", quality=92)
        return name

    def tearDown(self):
        if self.old is None:
            os.environ.pop("TV_CHRONICLE_LINES", None)
        else:
            os.environ["TV_CHRONICLE_LINES"] = self.old
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_premise_the_frames_are_what_they_claim(self):
        """the case distinguishes only if the saved JPEGs classify as the logo and Connecting"""
        d = os.path.join(self.hist, self.game)
        kinds = [DS.screen_of(os.path.join(d, f))[0] for f in sorted(os.listdir(d)) if f.endswith(".jpg")]
        self.assertEqual(kinds[:3], ["logo", "connecting", "connecting"], kinds)

    def test_a_logo_then_connecting_is_a_door(self):
        """* THE POINT - logo then Connecting, no title frame: the lane names the door, starting at the logo"""
        CL.tick(root=self.hist, budget_s=120)
        d = CL.load()
        door = CL.game_door(self.game, d)
        self.assertTrue(door, "the lane dropped the Connecting mark, so a logo -> Connecting reel named no door")
        self.assertEqual(door["startTs"], self.T0)
        self.assertEqual(door["connectingTs"], self.T0 + 1000)
        self.assertEqual([k for _t, k in d["reels"][self.game]["marks"]], ["logo", "connecting", "connecting"])

    def test_baseline_a_logo_alone_is_still_no_door(self):
        """the fix admits Connecting as the witness, not any logo: a logo with nothing after it stays no door"""
        CL.tick(root=self.hist, budget_s=120)
        self.assertIsNone(CL.game_door(self.logo_only, CL.load()))


RED_PROOF = [
    {"why": "REG-3752 - the chronicle lane drops the Connecting mark again, so a logo -> Connecting reel names no door",
     "file": "tv/chronicle_line.py",
     "find": "        if kind in (\"logo\", \"title\", \"connecting\", \"char-select\"):\n",
     "replace": "        if kind in (\"logo\", \"title\", \"char-select\"):\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
