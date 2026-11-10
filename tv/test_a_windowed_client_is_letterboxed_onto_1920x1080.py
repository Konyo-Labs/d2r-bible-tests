# -*- coding: utf-8 -*-
"""REG-3583 - A WINDOWED CLIENT IS LETTERBOXED ONTO THE 1920x1080 FILM.

MEASURED 2026-11-07 (Claude, #255): a Windows PC that plays D2R windowed, client 1507x755.
Elad recalled that as "about 1500 px wide". v3881 cropped to the client (PW_CLIENTONLY) and
stopped filming the desktop, but it did not map that ~2:1 client onto the 1920x1080
reference. A 1507x755 frame stayed 1507x755 (or was first capped at 800 px), so full-frame
reader fractions missed and shadow theatre later magnified a 160x79 thumb of it.

Now the calibrated client is resampled (LANCZOS / HighQualityBicubic) and letterboxed onto
1920x1080: 1507x755 becomes 1920x961 centered with 59 px black bars. Aspect is kept.
Held here. Fixtures only. RED_PROOF below.
"""
import io
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import fixture_tmp as _fx  # noqa: E402
_fx.contain()

from PIL import Image  # noqa: E402
import film_frame as FF  # noqa: E402
from char_select import windowed_fixture  # noqa: E402

CAP = os.path.join(HERE, "capture_win.ps1")
DIABLO = os.path.join(HERE, "tv_diablo.py")


def _src(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


class AWindowedClientIsLetterboxedOnto1920x1080(unittest.TestCase):

    def test_the_recorded_dean_client_fits_at_1920x961_on_the_film(self):
        self.assertEqual(FF.DEAN_WINDOWED_CLIENT, (1507, 755))
        (nw, nh), (ox, oy) = FF.film_dest_size(1507, 755)
        self.assertEqual((nw, nh), (1920, 961))
        self.assertEqual((ox, oy), (0, 59))

    def test_a_1507x755_frame_becomes_a_letterboxed_1920x1080_film(self):
        im = Image.new("RGB", FF.DEAN_WINDOWED_CLIENT, (40, 80, 120))
        # a solid interior mark, far from the letterbox, so LANCZOS does not bleed black into it
        for x in range(200, 280):
            for y in range(200, 280):
                im.putpixel((x, y), (220, 30, 30))
        out = FF.to_film_frame(im)
        self.assertEqual(out.size, (1920, 1080))
        self.assertEqual(out.getpixel((960, 5)), (0, 0, 0), "top letterbox is not black")
        self.assertEqual(out.getpixel((960, 1075)), (0, 0, 0), "bottom letterbox is not black")
        # dest of source (240, 240): 240 * 1920/1507 ≈ 306, 240 * 961/755 + 59 ≈ 365
        mark = out.getpixel((306, 365))
        self.assertGreater(mark[0], 180, "interior mark did not land on the film: %r" % (mark,))
        self.assertLess(mark[1], 80, "interior mark hue drifted: %r" % (mark,))
        game = out.getpixel((127, 186))  # source ~(100, 100)
        self.assertTrue(all(abs(game[i] - (40, 80, 120)[i]) < 20 for i in range(3)),
                        "game fill did not land: %r" % (game,))

    def test_the_windows_reel_letterboxes_the_dean_client(self):
        os.environ.setdefault("TV_STUB", "1")
        import tv_diablo as t
        d = tempfile.mkdtemp(prefix="tvd_deanfilm_")
        self.addCleanup(lambda: __import__("shutil").rmtree(d, True))
        src, dest = os.path.join(d, "live.bmp"), os.path.join(d, "f_1.jpg")
        Image.new("RGB", FF.DEAN_WINDOWED_CLIENT, (90, 70, 40)).save(src, "BMP")
        # paint enough variation that the JPEG clears the 4 KB floor
        im = Image.open(src)
        px = im.load()
        for x in range(0, 1507, 9):
            for y in range(0, 755, 7):
                px[x, y] = ((x * 3) % 256, (y * 5) % 256, ((x + y) * 7) % 256)
        im.save(src, "BMP")
        self.assertTrue(t._film_shrink(src, dest, t.FILM_MAX_PX, t.FILM_JPEG_Q))
        with Image.open(dest) as got:
            self.assertEqual(got.format, "JPEG")
            self.assertEqual(got.size, (1920, 1080),
                             "a 1507x755 windowed client did not become 1920x1080: %r" % (got.size,))
            self.assertEqual(got.getpixel((960, 5)), (0, 0, 0))

    def test_a_16x9_frame_fills_the_film_and_an_exact_film_is_unchanged(self):
        filled = FF.to_film_frame(Image.new("RGB", (2560, 1440), (90, 70, 40)))
        self.assertEqual(filled.size, (1920, 1080))
        self.assertEqual(filled.getpixel((960, 540)), (90, 70, 40))
        src = Image.new("RGB", (1920, 1080), (10, 20, 30))
        src.putpixel((0, 0), (255, 1, 2))
        same = FF.to_film_frame(src)
        self.assertEqual(same.size, (1920, 1080))
        self.assertEqual(same.getpixel((0, 0)), (255, 1, 2))
        self.assertEqual(same.getpixel((960, 540)), (10, 20, 30))

    def test_chrome_is_trimmed_before_a_16x9_game_fills_the_film(self):
        d = tempfile.mkdtemp(prefix="tvd_chrome_")
        self.addCleanup(lambda: __import__("shutil").rmtree(d, True))
        path = os.path.join(d, "win.jpg")
        # 1507x786 window: 31 px title + 1342x755 (16:9) game, black sides. After game_box
        # the game is 16:9 and must fill 1920x1080 — the mapping Mac templates expect.
        windowed_fixture(path, frame=(1507, 786), title=31, game=(1342, 755), sat=0.4, val=0.55)
        with Image.open(path) as raw:
            out = FF.to_film_frame(raw)
        self.assertEqual(out.size, (1920, 1080))
        top = out.getpixel((960, 0))
        # After a successful crop the 16:9 game FILLS the film, so the top row is the
        # plaque, not the bright title bar (236,236,236) and not a black letterbox.
        self.assertLess(max(top), 200, "title-bar chrome survived onto the film: %r" % (top,))
        self.assertGreater(sum(top), 80, "the 16:9 game did not fill the film (top is empty): %r" % (top,))
        mid = out.getpixel((960, 540))
        self.assertGreater(sum(mid), 80, "the 16:9 game did not fill the film: %r" % (mid,))

    def test_the_windows_eye_letterboxes_onto_a_1920x1080_canvas(self):
        s = _src(CAP)
        self.assertIn("int filmW = 1920, filmH = 1080;", s)
        self.assertIn("double scale = Math.Min(filmW / (double)bmp.Width, filmH / (double)bmp.Height);", s)
        self.assertNotIn("if (nw > filmW || nh > filmH)", s,
                         "the eye still only shrinks a larger source and leaves a windowed client as-is")
        self.assertIn("using (var eye = new Bitmap(filmW, filmH))", s)
        self.assertIn("eg.Clear(Color.Black);", s)
        self.assertIn("eg.DrawImage(bmp, ox, oy, nw, nh);", s)
        self.assertIn("InterpolationMode.HighQualityBicubic", s)
        self.assertIn("from film_frame import to_film_jpeg", _src(DIABLO))


RED_PROOF = [
    {"why": "REG-3583 - a windowed client smaller than 1920x1080 is no longer upscaled onto the film",
     "file": "tv/film_frame.py",
     "find": "    scale = min(film_w / float(src_w), film_h / float(src_h))\n",
     "replace": "    scale = min(1.0, min(film_w / float(src_w), film_h / float(src_h)))\n",
     "matches": 1},
    {"why": "REG-3583 - the Windows eye only shrinks a larger source and leaves a 1507x755 window as-is",
     "file": "tv/capture_win.ps1",
     "find": "    double scale = Math.Min(filmW / (double)bmp.Width, filmH / (double)bmp.Height);\n",
     "replace": "    double scale = Math.Min(1.0, Math.Min(filmW / (double)bmp.Width, filmH / (double)bmp.Height));\n",
     "matches": 1},
    {"why": "REG-3583 - the Windows eye is drawn into a client-sized bitmap again, not the 1920x1080 canvas",
     "file": "tv/capture_win.ps1",
     "find": "    using (var eye = new Bitmap(filmW, filmH))\n",
     "replace": "    using (var eye = new Bitmap(nw, nh))\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
