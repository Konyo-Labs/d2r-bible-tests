# -*- coding: utf-8 -*-
"""v3900 (REG-3744, #185) - A WINDOWS TITLE BAR IS TRIMMED FROM THE GAME AREA EVEN WHERE ITS TEXT AND BUTTONS ARE.

MEASURED 11-12 on Dean's own frames (copied over SSH while his PC was on, kept off the repo): his 800x400 frames carry the
Windows light-theme title bar ("Diablo II: Resurrected" + minimise / maximise / close) on rows 0-16 at a row median of 243.
Rows 6-10, which carry the title text and the button glyphs, spread 17-31 - over _CHROME_STD (14) - so game_box stopped at
row 6 and 11 white rows stayed "in the game" under every fraction the readers measure (lobby, character select). In-game rows
read a median of 124 or less. The v3856 fixture drew a FLAT bar, so no law could see it. game_box now also trims a top row
whose median and mean are both over TITLE_ROW_MIN; the sides, the bottom and a dark game are untouched.

DRIVEN: the real game_box over synthetic frames with his measured row profile (his footage never enters this public repo).
RED_PROOF below.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import char_select as CS  # noqa: E402


def _frame(text=True, bar=17, w=800, h=400, game_val=40, bright_game=False):
    """Dean's 800x400 shape: a 243 title bar of `bar` rows (dark title text and three button glyphs on rows 6-10 when
    `text`), a 1-row grey border, then the game."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (w, h), (game_val, game_val, game_val))
    d = ImageDraw.Draw(im)
    if bar <= 0:
        return im
    d.rectangle((0, 0, w - 1, bar - 1), fill=(243, 243, 243))
    if text:
        d.text((26, 3), "Diablo II: Resurrected", fill=(20, 20, 20))   # thin glyphs, as Windows draws them
        d.rectangle((9, 5, 16, 11), fill=(170, 40, 30))               # the app icon
        for x in (w - 110, w - 70, w - 30):                           # minimise / maximise / close: one-pixel lines
            d.line((x, 8, x + 9, 8), fill=(30, 30, 30))
    d.rectangle((0, bar, w - 1, bar), fill=(129, 129, 129))
    if bright_game:
        d.rectangle((0, bar + 1, w - 1, h - 1), fill=(120, 120, 120))
        for y in range(bar + 1, h, 9):
            d.rectangle((0, y, w - 1, y + 3), fill=(15, 15, 15))
    return im


class ATitleBarWithItsTextIsNotTheGame(unittest.TestCase):

    def test_premise_the_text_rows_spread_over_the_chrome_bar(self):
        import numpy as np
        a = np.asarray(_frame().convert("L"), dtype=np.float32)
        self.assertTrue(any(a[r].std() > CS._CHROME_STD for r in range(6, 11)),
                        "PREMISE: the fixture's title text no longer spreads like his - the case would not distinguish")

    def test_the_bar_with_text_is_trimmed_whole(self):
        """* THE POINT - Dean's 800x400: the trim stopped at row 6 and 11 white rows stayed in the game"""
        x0, y0, x1, y1 = CS.game_box(_frame())
        self.assertGreaterEqual(y0, 17, "the title bar's text rows were left inside the game area (y0=%d)" % y0)
        self.assertLessEqual(y0, 18)
        self.assertEqual((x0, x1, y1), (0, 800, 400))

    def test_baseline_a_flat_bar_and_a_full_screen_frame_are_as_before(self):
        self.assertEqual(CS.game_box(_frame(text=False))[1], 17)
        self.assertEqual(CS.game_box(_frame(bar=0)), (0, 0, 800, 400), "a frame with no bar lost rows")

    def test_a_dark_game_row_is_never_title(self):
        self.assertFalse(CS._title_row(124.0, 124.0), "an in-game row read as title bar")
        self.assertFalse(CS._title_row(230.0, 180.0), "a bright row whose median is the game read as title bar")
        self.assertTrue(CS._title_row(239.0, 243.0))

    def test_only_the_top_edge_trims_a_title_bar(self):
        im = _frame(bar=0).transpose(0)   # a bright band at the bottom is never title bar
        im2 = _frame(text=True).rotate(180)
        x0, y0, x1, y1 = CS.game_box(im2)
        self.assertGreater(y1, 400 - 17 - 2, "a bright bottom band was trimmed as a title bar (y1=%d)" % y1)
        self.assertEqual(CS.game_box(im), (0, 0, 800, 400))


RED_PROOF = [
    {"why": "REG-3744 - a title bar's text rows stay inside the game area again (Dean's 800x400, 11-12)",
     "file": "tv/char_select.py",
     "find": "        while lo < lim and (_chrome(ms[lo], ss[lo]) or (med is not None and _title_row(ms[lo], med[lo]))):\n",
     "replace": "        while lo < lim and _chrome(ms[lo], ss[lo]):\n",
     "matches": 1},
    {"why": "REG-3744 - a row whose median is the game reads as title bar",
     "file": "tv/char_select.py",
     "find": "    return median > TITLE_ROW_MIN and mean > TITLE_ROW_MIN\n",
     "replace": "    return mean > TITLE_ROW_MIN\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
