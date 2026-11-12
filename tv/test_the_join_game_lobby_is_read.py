# -*- coding: utf-8 -*-
"""v3900 (REG-3747, #185) - THE JOIN GAME LOBBY IS READ AS A LOBBY, AND A DARK GAME BEHIND A MENU IS NOT.

His question 11-12 ~02:30: "i thought we calliberated and fixed the aspect/resolution to recording". REG-3508 (v3890) fitted
the lobby on the work ALT's and the OLD ALT's CREATE GAME tab and left Dean "OWED". MEASURED 11-12 on Dean's frozen footage
(copied over SSH while his PC was on; his pictures never enter this public repo - only the reader's own numbers off them):
Vision OCR read 224 opening frames LOBBY by their words, GrokBot labelled 140 by eye (#230, every one Join Game) - and the
reader agreed with 0. His lobby is darker in every region the bands read. The box over his lobbies (held out by sitting:
221 of 224) also admitted dark in-game scenes (9 of 22 sampled in-box frames, looked at), so the rule also asks the lobby's
own mark - the fire DIABLO logo atop the centre column. Every frame it admits in 6,000 sampled of his and 4,000 of the Mac's
was looked at: 73 of 73 are lobbies (two of them the Mac's own Join Game lobby, which the shipped bands missed too).

DRIVEN: the real looks_like_lobby over the reader's own measured 10-value stats (his lobbies, the Mac's, and the in-game frames
the box alone let in), and the real lobby_stats over a synthetic frame for the 10th value. RED_PROOF below.
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

import char_select as CS  # noqa: E402

#: measured 11-12 (lobby_stats, the 1/4 draft decode): Dean's Join Game lobbies - the darkest, the median, the brightest
DEAN_LOBBY = [(0.1915, 0.1029, 0.0892, 0.1021, 0.1222, 0.0741, 0.0817, 0.0515, 0.1381, 0.1921),
              (0.1886, 0.1076, 0.0866, 0.102, 0.1267, 0.0768, 0.0816, 0.0514, 0.1509, 0.2114),
              (0.2009, 0.1116, 0.0862, 0.1027, 0.1232, 0.0761, 0.1052, 0.0589, 0.1502, 0.2)]
#: the Mac's own Join Game lobbies in the sample (one with a dialog over it)
MAC_LOBBY = [(0.2089, 0.0878, 0.0663, 0.1373, 0.1046, 0.0635, 0.0552, 0.0492, 0.1137, 0.206),
             (0.2037, 0.1149, 0.0675, 0.112, 0.1366, 0.0842, 0.1156, 0.0791, 0.1675, 0.3024)]
#: in-game frames inside the box (dark scenes, a waypoint menu over the game): no fire logo
IN_GAME_IN_BOX = [(0.2005, 0.0927, 0.0931, 0.1351, 0.0781, 0.0439, 0.0573, 0.0443, 0.0603, 0.0021),
                  (0.1967, 0.0901, 0.0892, 0.1327, 0.075, 0.0435, 0.0555, 0.0449, 0.0597, 0.0065),
                  (0.2093, 0.1015, 0.0939, 0.1643, 0.1178, 0.0585, 0.0688, 0.0379, 0.0581, 0.0),
                  (0.2121, 0.1281, 0.089, 0.1636, 0.0983, 0.0902, 0.0716, 0.0493, 0.0637, 0.0081),
                  (0.1788, 0.1217, 0.0908, 0.1607, 0.1079, 0.0635, 0.099, 0.0697, 0.1095, 0.0),
                  (0.2128, 0.1019, 0.0875, 0.1768, 0.0834, 0.0453, 0.072, 0.0376, 0.0709, 0.0)]


class TheJoinGameLobbyIsRead(unittest.TestCase):

    def test_premise_the_create_game_rules_alone_refuse_his_lobby(self):
        for st in DEAN_LOBBY:
            self.assertFalse(CS.looks_like_lobby(st[:9])[0], "PREMISE: the 9-value rules already read his lobby - no case")

    def test_his_join_game_lobby_is_a_lobby(self):
        """* THE POINT - Dean's lobby: 0 of 224 read before"""
        for st in DEAN_LOBBY + MAC_LOBBY:
            ok, why = CS.looks_like_lobby(st)
            self.assertTrue(ok, "a Join Game lobby was refused: %s" % why)
            self.assertIn("join-game lobby", why)

    def test_a_dark_game_inside_the_box_is_not_a_lobby(self):
        for st in IN_GAME_IN_BOX:
            ok, why = CS.looks_like_lobby(st)
            self.assertFalse(ok, "an in-game frame with no fire logo was read as the lobby: %s" % why)

    def test_an_unmeasured_fire_logo_admits_nothing(self):
        st = DEAN_LOBBY[1][:9] + (None,)
        self.assertFalse(CS.looks_like_lobby(st)[0], "a lobby was read on a fire logo nobody measured")

    def test_lobby_stats_carries_the_fire_logo_as_its_tenth(self):
        from PIL import Image, ImageDraw
        d = tempfile.mkdtemp(prefix="joinlobby_")
        self.addCleanup(shutil.rmtree, d, True)
        im = Image.new("RGB", (800, 400), (30, 28, 26))
        ImageDraw.Draw(im).rectangle((350, 20, 450, 64), fill=(235, 90, 20))    # fire red-orange atop the centre column
        p = os.path.join(d, "f.jpg")
        im.save(p, quality=95)
        st = CS.lobby_stats(p)
        self.assertEqual(len(st), 10)
        self.assertGreater(st[9], 0.30, "the fire logo atop the centre column was not measured")
        dark = os.path.join(d, "g.jpg")
        Image.new("RGB", (800, 400), (30, 28, 26)).save(dark, quality=95)
        self.assertLess(CS.lobby_stats(dark)[9], 0.01)


RED_PROOF = [
    {"why": "REG-3747 - Dean's Join Game lobby is refused again (0 of 224 read, 11-12)",
     "file": "tv/char_select.py",
     "find": "    if len(stats) == 10 and stats[9] is not None and stats[9] >= JOIN_LOBBY_FIRE_MIN \\\n",
     "replace": "    if False and len(stats) == 10 and stats[9] is not None and stats[9] >= JOIN_LOBBY_FIRE_MIN \\\n",
     "matches": 1},
    {"why": "REG-3747 - the box alone reads a dark game behind a menu as the lobby",
     "file": "tv/char_select.py",
     "find": "    if len(stats) == 10 and stats[9] is not None and stats[9] >= JOIN_LOBBY_FIRE_MIN \\\n",
     "replace": "    if len(stats) == 10 \\\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
