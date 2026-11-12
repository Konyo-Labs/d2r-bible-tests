# -*- coding: utf-8 -*-
"""v3901 (REG-3754, #188) - IN A WHOLE-DESKTOP CAPTURE THE D2 LOGO IS FOUND INSIDE ITS WINDOW.

MEASURED on Dean's PC (GrokBot's frame labels, #230; the frames stay off the repo): 445 of his frames are 800x450 captures
of his WHOLE 1920x1080 desktop - the game a 627x315 box under a white Windows title bar, the Battle.net launcher and his
browser around it, the taskbar below. His only two logo sittings (10-29, 10-31) show the small corner logo in such frames,
and d2r_screens.screen_of read 3 of their 4 logo frames as "not D2R": the corner box and the dark share were taken over the
whole desktop, so the session's first door was invisible. After the fix all 3 read "logo" (x 3-316 / 44-356 of 400 px).

Now a frame that matches nothing whole is looked at once more inside the window it holds - the white title bar run sitting
directly on the black client, whose edges stay dark down to its bottom - and only the door screens (logo, title, Connecting)
are named from that box. A frame that already matched is unchanged; a white bar over a dark window that holds no D2R door
stays unmatched.

DRIVEN: the real screen_of over synthetic desktops (a busy wallpaper, a launcher panel, a taskbar, a titled window). RED_PROOF
below.
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
import d2r_screens as DS  # noqa: E402

W, H = 800, 450
FIRE = (240, 150, 40)
WIN = (86, 44, 712, 372)          # x0, title-bar top, x1, client bottom - Dean's measured box (GrokBot, S8 #1)


def _desktop():
    im = Image.new("RGB", (W, H), (70, 110, 150))
    d = ImageDraw.Draw(im)
    for x in range(0, W, 23):
        d.line([(x, 0), (W - x // 2, H)], fill=(160, (x * 5) % 200 + 40, 90), width=4)      # a busy wallpaper
    d.rectangle([0, 0, 660, 300], fill=(28, 30, 38))                                         # the launcher behind it
    d.rectangle([20, 280, 120, 300], fill=(40, 120, 230))                                    # its blue Play button
    d.rectangle([0, H - 22, W, H], fill=(225, 228, 235))                                     # the taskbar
    return im


def _window(im, client):
    x0, yb, x1, y1 = WIN
    d = ImageDraw.Draw(im)
    d.rectangle([x0, yb, x1 - 1, yb + 12], fill=(243, 243, 243))                             # the white title bar
    d.text((x0 + 12, yb + 1), "Diablo II: Resurrected", fill=(20, 20, 20))
    d.rectangle([x0, yb + 13, x1 - 1, y1], fill=(0, 0, 0))                                   # the black client
    client(d, x0, yb + 13, x1, y1)
    return im


def _corner_logo(d, x0, y0, x1, y1):
    w, h = x1 - x0, y1 - y0
    d.ellipse([x1 - int(w * .09), y1 - int(h * .14), x1 - int(w * .03), y1 - int(h * .05)], fill=FIRE)


def _nothing(d, x0, y0, x1, y1):
    d.rectangle([x0 + 40, y0 + 40, x0 + 140, y0 + 90], fill=(60, 60, 200))                   # a dark app, not D2R


class ADesktopCaptureFindsTheLogo(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="desk_logo_")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _kind(self, im, name):
        p = os.path.join(self.tmp, name + ".jpg")
        im.save(p, "JPEG", quality=92)
        return DS.screen_of(p)

    def test_the_corner_logo_inside_a_desktop_is_the_logo(self):
        """* THE POINT - Dean's two logo sittings showed the logo only in whole-desktop frames, read as 'not D2R'"""
        k, why = self._kind(_window(_desktop(), _corner_logo), "desk_logo")
        self.assertEqual(k, "logo", why)
        self.assertIn("whole-desktop", why)

    def test_baseline_the_same_logo_alone_is_the_logo_without_the_window_path(self):
        im = Image.new("RGB", (W, H), (0, 0, 0))
        _corner_logo(ImageDraw.Draw(im), 0, 0, W, H)
        k, why = self._kind(im, "bare_logo")
        self.assertEqual(k, "logo", why)
        self.assertNotIn("whole-desktop", why, "a full-frame logo went through the desktop path")

    def test_a_dark_window_without_a_door_stays_unmatched(self):
        k, why = self._kind(_window(_desktop(), _nothing), "desk_dark_app")
        self.assertIsNone(k, "a titled dark window holding no D2R door was named %r: %s" % (k, why))

    def test_a_desktop_with_no_window_stays_unmatched(self):
        self.assertIsNone(self._kind(_desktop(), "desk_only")[0])


RED_PROOF = [
    {"why": "REG-3754 - a frame that matches nothing whole is never looked at inside its window again (Dean's logo lost)",
     "file": "tv/d2r_screens.py",
     "find": "        box = window_box(a)\n",
     "replace": "        box = None\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
