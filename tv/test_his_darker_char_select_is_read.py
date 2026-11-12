# -*- coding: utf-8 -*-
"""v3901 (REG-3758, #185 / #104) - DEAN'S DARKER CHARACTER SELECT IS READ, BY ITS PANELS AND THE FIRE LOGO ABOVE THEM.

MEASURED on Dean's frozen footage (off the repo; his frames never enter it): the 4 opening frames OCR read as character select
read right sat 0.065 / val 0.222, left sat 0.135 / val 0.160 - under the bands fitted on his Mac's 8 visits (right val
0.30-0.45, left val 0.17-0.27): the same darker look as his Join Game lobby (REG-3747). char_select.looks_like_char_select said
"no list panel" on all 4, so his character select was never a door and his reels learned no name from it. Widening the bands
alone lets dark game scenes in (REG-3508's measurement). What only this screen has is the fire DIABLO logo atop the LEFT menu
column: share 0.22-0.25 on his 6 character-select frames, 0.000 on 60 of his lobbies. A frame in the darker band now passes
only WITH that logo; the original bands are unchanged.

DRIVEN: the real panel_stats / looks_like_char_select / d2r_screens.screen_of over synthetic frames built to his measured
values (stone panels at his brightness, the fire logo at the column's top). RED_PROOF below.
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
import char_select as CS  # noqa: E402

W, H = 800, 400


def _frame(fire_at="left", stone=(57, 55, 53), menu=(41, 38, 35)):
    """His character select at his size: a dark scene, the stone list on the right, the stone menu column on the left."""
    im = Image.new("RGB", (W, H), (22, 24, 20))
    d = ImageDraw.Draw(im)
    d.rectangle([int(W - 0.385 * H), 0, W, H], fill=stone)               # the list panel (right), his darker grey
    d.rectangle([0, 0, int(0.36 * H), H], fill=menu)                      # the menu column (left)
    for i in range(5):                                                     # its stone buttons - a little texture
        d.rectangle([12, 170 + i * 30, int(0.30 * H), 190 + i * 30], fill=(46, 43, 40))
    if fire_at == "left":
        d.ellipse([30, 50, 130, 115], fill=(225, 80, 20))                 # the fire DIABLO logo atop the left column
    elif fire_at == "centre":
        d.ellipse([350, 20, 450, 70], fill=(225, 80, 20))                 # a lobby's logo sits centre-top instead
    return im


class HisDarkerCharSelectIsRead(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="dark_cs_")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _stats(self, im, name):
        p = os.path.join(self.tmp, name + ".jpg")
        im.save(p, "JPEG", quality=92)
        return p, CS.panel_stats(p)

    def test_premise_the_fixture_reads_in_his_darker_band(self):
        _p, st = self._stats(_frame(), "cs")
        rs, rv, ls, lv, fire = st
        self.assertTrue(rv < CS.RIGHT_VAL[0] or lv < CS.LEFT_VAL[0],
                        "PREMISE: the fixture passes the original bands - the case would not distinguish: %r" % (st,))
        self.assertGreaterEqual(fire, CS.CS_FIRE_MIN, "PREMISE: the fixture's logo does not read as fire: %r" % (st,))

    def test_his_character_select_is_read(self):
        """* THE POINT - Dean's 4 (+2) character-select frames read 'no list panel'"""
        p, st = self._stats(_frame(), "cs")
        ok, why = CS.looks_like_char_select(st)
        self.assertTrue(ok, why)
        self.assertIn("fire logo", why)
        import d2r_screens as DS
        self.assertEqual(DS.screen_of(p)[0], "char-select")

    def test_baseline_the_same_panels_without_the_logo_stay_refused(self):
        for where in (None, "centre"):
            _p, st = self._stats(_frame(fire_at=where), "nolog_%s" % where)
            self.assertFalse(CS.looks_like_char_select(st)[0], "dark panels with no left logo were read: %r" % (st,))

    def test_four_stats_still_judge_by_the_original_bands(self):
        self.assertFalse(CS.looks_like_char_select((0.065, 0.222, 0.135, 0.160))[0])
        self.assertTrue(CS.looks_like_char_select((0.04, 0.36, 0.10, 0.22))[0])


RED_PROOF = [
    {"why": "REG-3758 - his darker character select is refused again (no list panel), the door never seen on his PC",
     "file": "tv/char_select.py",
     "find": "    if (fire is not None and fire >= CS_FIRE_MIN and rs < DARK_CS_RIGHT_SAT_MAX\n",
     "replace": "    if (False and fire is not None and fire >= CS_FIRE_MIN and rs < DARK_CS_RIGHT_SAT_MAX\n",
     "matches": 1},
    {"why": "REG-3758 - the darker band admits a frame with no fire logo atop the left column",
     "file": "tv/char_select.py",
     "find": "    if (fire is not None and fire >= CS_FIRE_MIN and rs < DARK_CS_RIGHT_SAT_MAX\n",
     "replace": "    if (rs < DARK_CS_RIGHT_SAT_MAX\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
