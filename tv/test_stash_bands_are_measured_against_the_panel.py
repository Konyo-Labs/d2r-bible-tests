# -*- coding: utf-8 -*-
"""v3895 (#106, REG-3585) - 2:1 STASH BAND LAWS ARE MEASURED AGAINST THE PANEL.

Dean's windowed client is 1507x755 (~2:1). After v3894 it is filmed as 1920x961 centered on a
1920x1080 canvas (59 px black bars). stash_eye used the canvas aspect (1.778) and applied the
derived band as if the game filled the frame, so the crop included the bars and missed the
panel. Now the frame is trimmed to its game box first; the band is derived from that panel's
own aspect (~2.00) and cropped from the panel, not the canvas.
A fullscreen frame with no bars is unchanged.
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
import stash_eye as se  # noqa: E402


def _letterboxed_dean_frame(path):
    """1920x1080 canvas, Dean-shaped game 1920x961 at y=59, non-black so game_box can see it."""
    canvas = Image.new("RGB", (1920, 1080), (0, 0, 0))
    game = Image.new("RGB", (1920, 961), (48, 52, 90))
    canvas.paste(game, (0, 59))
    canvas.save(path, "JPEG", quality=95)
    return path


class StashBandsAreMeasuredAgainstThePanel(unittest.TestCase):

    def test_a_letterboxed_dean_frame_uses_the_panel_aspect(self):
        td = tempfile.mkdtemp(prefix="stash_panel_")
        src = _letterboxed_dean_frame(os.path.join(td, "dean.jpg"))
        dest = os.path.join(td, "crop.jpg")
        self.assertIsNotNone(se.prep_stash_grid(src, dest, layout="runes"))
        d = se.last_crop_decision()
        self.assertAlmostEqual(d["aspect"], 1920 / 961.0, places=3, msg=d)
        self.assertNotAlmostEqual(d["aspect"], 1920 / 1080.0, places=3, msg=d)
        with Image.open(dest) as crop:
            # the saved band is a crop of the panel, so it cannot be as tall as the canvas
            self.assertLess(crop.size[1], 1080)
            self.assertGreater(crop.size[1], 200)

    def test_a_fullscreen_frame_is_unchanged(self):
        td = tempfile.mkdtemp(prefix="stash_full_")
        src = os.path.join(td, "mac.jpg")
        Image.new("RGB", (2940, 1912), (48, 52, 90)).save(src, "JPEG", quality=95)
        dest = os.path.join(td, "crop.jpg")
        self.assertIsNotNone(se.prep_stash_grid(src, dest, layout="runes"))
        d = se.last_crop_decision()
        self.assertAlmostEqual(d["aspect"], 2940 / 1912.0, places=3, msg=d)
        self.assertEqual(d["branch"], "locked-mac", d)


def _read(rel):
    path = os.path.join(HERE, os.path.basename(rel)) if rel.startswith("tv/") else rel
    with io.open(path if os.path.isabs(path) else os.path.join(HERE, os.path.basename(rel)), encoding="utf-8") as fh:
        return fh.read()


RED_PROOF = [
    {"why": "v3895 (#106, REG-3585) - prep_stash_grid measures the canvas again, not the panel",
     "file": "tv/stash_eye.py",
     "find": "            from char_select import game_box as _game_box\n            _box = _game_box(im)\n            if _box != (0, 0) + im.size and _box[2] > _box[0] and _box[3] > _box[1]:\n                im = im.crop(_box)\n        except Exception:\n            pass\n        w, h = im.size\n        aspect = (w / float(h)) if h else 0\n",
     "replace": "            pass\n        except Exception:\n            pass\n        w, h = im.size\n        aspect = (w / float(h)) if h else 0\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
