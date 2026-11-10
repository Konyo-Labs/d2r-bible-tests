# -*- coding: utf-8 -*-
"""v3895 (#106, REG-3586) - THE CHARACTER LIST IS CROPPED FROM THE GAME PANEL.

panel_crop is the door the name reader uses. It placed the right-hand list as a fraction of the
FULL frame height. On Dean's letterboxed 1920x1080 film (game 1920x961, 59 px bars) that included
the black bars and shifted the list, so the reader was handed bars and floor instead of the
names. Now the frame is trimmed to its game box first (the same trim lobby_stats already uses).
RED_PROOF below.
"""
import io
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _enable  # noqa: E402
_enable()

from PIL import Image  # noqa: E402
import char_select as C  # noqa: E402


class TheCharacterListIsCroppedFromThePanel(unittest.TestCase):

    def test_a_letterboxed_dean_frame_crops_the_list_from_the_game(self):
        td = tempfile.mkdtemp(prefix="char_panel_")
        src = os.path.join(td, "dean.jpg")
        canvas = Image.new("RGB", (1920, 1080), (0, 0, 0))
        game = Image.new("RGB", (1920, 961), (48, 52, 90))
        # stone list on the right of the GAME, using the same height-scaled width the crop uses
        pw = int((C.PANEL_W_H + 0.02) * 961)
        stone = Image.new("RGB", (pw, 961), (180, 170, 150))
        game.paste(stone, (1920 - pw, 0))
        canvas.paste(game, (0, 59))
        canvas.save(src, "JPEG", quality=95)
        crop_path = C.panel_crop(src, td)
        self.assertIsNotNone(crop_path)
        with Image.open(crop_path) as crop:
            self.assertEqual(crop.size[1], 961, crop.size)
            self.assertNotEqual(crop.size[1], 1080, crop.size)
            pix = crop.getpixel((crop.size[0] // 2, 4))
            self.assertGreater(sum(pix), 80, pix)


RED_PROOF = [
    {"why": "v3895 (#106, REG-3586) - panel_crop measures the canvas height again",
     "file": "tv/char_select.py",
     "find": "            im = _in_game(im.convert(\"RGB\"))\n            w, h = im.size\n            box = (max(0, int(w - (PANEL_W_H + 0.02) * h)), 0, w, h)\n",
     "replace": "            w, h = im.size\n            box = (max(0, int(w - (PANEL_W_H + 0.02) * h)), 0, w, h)\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
