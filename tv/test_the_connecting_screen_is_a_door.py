# -*- coding: utf-8 -*-
"""v3898 (#188, REG-3715) - "CONNECTING TO BATTLE.NET" IS A SCREEN THE CLASSIFIER NAMES, AND IT WITNESSES THE DOOR.

His 11-11 ruling: on every route the trigger chain is the D2 logo -> CONNECTING TO BATTLE.NET -> character select, starting
at the first. d2r_screens named logo, title, char-select, lobby and hud, and called the real Connecting frame None ("not D2R's
logo, title or in-game orbs"): the dark stone plaque covers the fire title's centre, so the title test never fires on it.

MEASURED: GrokBot's 3 real frames (#230 6798662136, Mac native) - the plaque's inner box colourless (saturation 0.008) and
dark grey (0.084), the fire D and O flanking it, 91% dark. Then EVERY reel frame on his Mac, 44,818: the first cut matched 17
- 16 identical real Connecting screens and one in-game River of Flame frame (fire ring + lava as the flanks, 0.019 / 0.126 /
0.79). The bounds were tightened so each refuses it alone, and a frame with both orbs (in a game) is never this screen.
GeForce NOW's own loading / queue pages pass the plaque half and fail the flanks - both halves must meet.

DRIVEN on drawn fixtures (this law runs where his footage does not), the shipped screen_of / chain. RED_PROOF below.
"""
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
from PIL import Image, ImageDraw  # noqa: E402
import d2r_screens as DS  # noqa: E402

W, H = 800, 500
FIRE = (232, 124, 30)


def _title():
    im = Image.new("RGB", (W, H), (6, 4, 4))
    ImageDraw.Draw(im).rectangle([int(W * .22), int(H * .30), int(W * .78), int(H * .62)], fill=FIRE)   # the fire DIABLO
    return im


def _plaque(im, fill=(21, 21, 21)):
    d = ImageDraw.Draw(im)
    d.rectangle([int(W * .31), int(H * .375), int(W * .69), int(H * .585)], fill=(95, 95, 95))       # the stone bevel
    d.rectangle([int(W * .315), int(H * .385), int(W * .685), int(H * .575)], fill=fill)            # the dark plaque
    return im


def _orbs(im):
    d = ImageDraw.Draw(im)
    d.ellipse([150, 410, 210, 470], fill=(190, 20, 20))
    d.ellipse([590, 410, 650, 470], fill=(20, 40, 200))
    return im


def _kind(im):
    d = tempfile.mkdtemp(prefix="connecting_")
    p = os.path.join(d, "f.png")
    try:
        im.save(p)
        return DS.screen_of(p)[0]
    finally:
        try:
            os.remove(p)
            os.rmdir(d)
        except OSError:
            pass


class TheConnectingScreenIsADoor(unittest.TestCase):

    def test_the_plaque_over_the_fire_title_is_connecting(self):
        """* THE POINT - the screen his ruling makes the trigger's middle link is named, never None"""
        self.assertEqual(_kind(_plaque(_title())), "connecting")

    def test_the_title_alone_is_still_the_title(self):
        """BASELINE - the fire title without the plaque keeps its own name"""
        self.assertEqual(_kind(_title()), "title")

    def test_a_streaming_page_with_a_grey_centre_and_no_fire_is_not(self):
        """GeForce NOW's loading / queue pages pass the plaque half alone - the fire flanks are missing"""
        self.assertNotEqual(_kind(_plaque(Image.new("RGB", (W, H), (8, 8, 8)))), "connecting")

    def test_a_frame_in_a_game_is_never_connecting(self):
        """the River of Flame false match: fire around a dark centre IN A GAME (both orbs) is not this screen"""
        self.assertNotEqual(_kind(_orbs(_plaque(_title()))), "connecting")

    def test_a_tinted_centre_is_not_the_colourless_plaque(self):
        self.assertNotEqual(_kind(_plaque(_title(), fill=(26, 19, 14))), "connecting")

    def test_connecting_witnesses_the_door_and_the_logo_starts_it(self):
        c = DS.chain([(1000, "logo"), (9000, "connecting"), (20000, "char-select")])
        self.assertIsNotNone(c, "a logo then CONNECTING then character select is not read as the door")
        self.assertEqual((c["startTs"], c["connectingTs"], c["titleTs"], c["entered"]), (1000, 9000, None, True))
        self.assertIsNone(DS.chain([(1000, "logo"), (20000, "char-select")]), "BASELINE - a logo alone is still no door")

    def test_the_scenario_names_connecting_from_real_frames(self):
        self.assertFalse(DS.SCENARIO_EVIDENCE["connecting"].startswith("none"),
                         "the classifier names the screen now; the evidence line still says no frame exists")
        self.assertIn("connecting", DS.PRE_GAME, "CONNECTING is before a town: it must never open the stash reader")


RED_PROOF = [
    {"why": "v3898 (#188, REG-3715) - the Connecting screen reads None again (the trigger's middle link is invisible)",
     "file": "tv/d2r_screens.py",
     "find": "    if is_connecting_stats(st):\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "v3898 (#188, REG-3715) - an in-game frame with fire around a dark centre reads Connecting (the River of Flame)",
     "file": "tv/d2r_screens.py",
     "find": "                and not (st.get(\"red\", 0) >= ORB_MIN and st.get(\"blue\", 0) >= ORB_MIN))\n",
     "replace": "                )\n",
     "matches": 1},
    {"why": "v3898 (#188, REG-3715) - the plaque half alone is enough again (a streaming page with no fire reads Connecting)",
     "file": "tv/d2r_screens.py",
     "find": "                and st[\"flank\"] is not None and st[\"flank\"] >= FLANK_FIRE_MIN and st[\"dark\"] >= CONNECT_DARK_MIN\n",
     "replace": "                and st[\"dark\"] >= 0\n",
     "matches": 1},
    {"why": "v3898 (#188, REG-3715) - Connecting no longer witnesses the door",
     "file": "tv/d2r_screens.py",
     "find": "            elif k2 == \"char-select\" and (title is not None or conn is not None):\n",
     "replace": "            elif k2 == \"char-select\" and title is not None:\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
