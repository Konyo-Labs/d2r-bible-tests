# -*- coding: utf-8 -*-
"""REG-3581 / REG-3582 - EVERY PC FILMS AT 1920x1080, AND SHADOW THEATRE PLAYS THAT FRAME.

MEASURED 2026-11-10 on the Mac (read-only) while Elad viewed Dean's console in shadow mode:
  * Dean's published frames (tv/roster_frames_cache/Dean.json, 137 KB, written 10:38 IST) were
    45 JPEGs at 160x79 or 160x80, 1.6-3.1 KB each (median 1.9 KB), aspect ~2.025.
  * The Mac's own published thumbs were 160x100, 6.4-10.2 KB (from full-size sources).
  * The Mac's local hist frames are full-window (1440x904 / 1440x936 / 2560x1607), 150-380 KB.
  * Dean's session character name was null (only class=Assassin from the avatar).
  * Dean is not a registered machine (LAPTOP-QNFL860M, v3886, last seen ~5 h earlier).

Root cause, two stacked shrinks:
  1. capture_win.ps1 SaveAll wrote eye.jpg at 800 px q72 bilinear. Readers called that "soft"
     (v3881 / reader_parity: inventory-title eye lost 7 of 16 at 800, "crisp" at 1440).
  2. shadow_sessions uploaded the theatre's 160 px / 20 KB scrub thumb; roster.js refused
     anything larger. Theatre (.th-film { width:100%; height:100%; object-fit:contain }) then
     painted that 160x79 JPEG at stage size - a 10x magnification, which is what Elad saw.

A full reel still never leaves its PC. The few key frames and vault evidence now ride at film
size (1920x1080, never enlarged). Held here. Fixtures only. RED_PROOF below.
"""
import io
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import fixture_tmp as _fx  # noqa: E402
_fx.contain()
import shadow_sessions as SS  # noqa: E402
from PIL import Image  # noqa: E402

CAP = os.path.join(HERE, "capture_win.ps1")
DIABLO = os.path.join(HERE, "tv_diablo.py")
ROSTER = os.path.join(ROOT, "functions", "api", "roster.js")
SHADOW = os.path.join(HERE, "shadow_sessions.py")


def _src(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


def _jpeg(path, size):
    im = Image.new("RGB", size)
    px = im.load()
    for x in range(0, size[0], 11):
        for y in range(0, size[1], 7):
            px[x, y] = ((x * 3) % 256, (y * 5) % 256, ((x + y) * 7) % 256)
    im.save(path, "JPEG", quality=90)


class EveryPcFilmsAt1920x1080(unittest.TestCase):

    def test_the_windows_eye_fits_inside_1920x1080_at_q82(self):
        s = _src(CAP)
        self.assertIn("int filmW = 1920, filmH = 1080;", s,
                      "capture_win.ps1 no longer names the 1920x1080 film box")
        self.assertNotIn("int maxPx = 800;", s,
                         "capture_win.ps1 still caps the eye at 800 px")
        self.assertIn("InterpolationMode.HighQualityBicubic", s,
                      "the eye downscale is not HighQualityBicubic")
        self.assertNotIn("InterpolationMode.Bilinear", s,
                         "the eye downscale is still bilinear")
        self.assertIn("Encoder.Quality, 82L", s,
                      "the eye JPEG is not quality 82")
        self.assertNotIn("Encoder.Quality, 72L", s,
                         "the eye JPEG is still quality 72")

    def test_the_python_film_defaults_to_1920x1080(self):
        s = _src(DIABLO)
        self.assertIn("FILM_W, FILM_H = 1920, 1080", s)
        self.assertIn('os.environ.get("TV_FILM_MAX_PX", "1920")', s,
                      "FILM_MAX_PX no longer defaults to 1920")
        self.assertNotIn('os.environ.get("TV_FILM_MAX_PX", "1440"', s,
                         "FILM_MAX_PX still defaults to 1440")

    def test_a_1920x1080_source_rides_the_digest_at_full_size(self):
        d = tempfile.mkdtemp(prefix="film1920_")
        self.addCleanup(lambda: __import__("shutil").rmtree(d, True))
        fid = "1_1795000000000"
        _jpeg(os.path.join(d, fid + ".jpg"), (1920, 1080))
        data, why = SS.thumb_bytes(d, fid)
        self.assertIsNone(why, why)
        self.assertLessEqual(len(data), SS.MAX_THUMB)
        with Image.open(io.BytesIO(data)) as im:
            self.assertEqual(im.size, (1920, 1080), "a 1920x1080 frame did not ride whole: %r" % (im.size,))
        self.assertTrue(os.path.isfile(os.path.join(d, SS.SHADOW_CACHE, fid + ".jpg")))

    def test_a_larger_source_fits_inside_1920_and_a_small_one_is_not_enlarged(self):
        d = tempfile.mkdtemp(prefix="filmfit_")
        self.addCleanup(lambda: __import__("shutil").rmtree(d, True))
        big, small = "2_1795000000001", "3_1795000000002"
        _jpeg(os.path.join(d, big + ".jpg"), (2560, 1440))
        _jpeg(os.path.join(d, small + ".jpg"), (800, 450))
        bdata, bwhy = SS.thumb_bytes(d, big)
        sdata, swhy = SS.thumb_bytes(d, small)
        self.assertIsNone(bwhy, bwhy)
        self.assertIsNone(swhy, swhy)
        with Image.open(io.BytesIO(bdata)) as im:
            self.assertEqual(im.size, (1920, 1080), "a 2560x1440 frame did not fit to 1920x1080: %r" % (im.size,))
        with Image.open(io.BytesIO(sdata)) as im:
            self.assertEqual(im.size, (800, 450), "an 800x450 frame was upscaled: %r" % (im.size,))

    def test_shadow_theatre_does_not_send_a_160_px_thumb(self):
        self.assertEqual(SS.SHADOW_FRAME_PX, 1920)
        self.assertEqual(SS.SHADOW_FRAME_H, 1080)
        self.assertEqual(SS.SHADOW_CACHE, "cache1920")
        self.assertGreaterEqual(SS.MAX_THUMB, 800 * 1024)
        self.assertGreaterEqual(SS.MAX_TOTAL, 12 * 1024 * 1024)
        self.assertEqual(SS.THUMB_PX, 160, "the shelf scrub thumb size moved - cache160 is a different consumer")
        s = _src(SHADOW)
        self.assertIn('cached = os.path.join(hist_dir, SHADOW_CACHE, base)', s)
        self.assertNotIn('cached = os.path.join(hist_dir, "cache160", base)', s)

    def test_the_worker_accepts_a_film_size_jpeg(self):
        s = _src(ROSTER)
        self.assertIn("const FRAMES_MAX_JPG_B64 = 1100000;", s,
                      "roster.js still caps a frame at the old 20 KB thumb")
        self.assertIn("const FRAMES_MAX_BODY = 18874368;", s,
                      "roster.js still caps the digest at 900 KB")
        self.assertNotIn("const FRAMES_MAX_JPG_B64 = 27400;", s)
        self.assertNotIn("const FRAMES_MAX_BODY = 900000;", s)


RED_PROOF = [
    {"why": "REG-3581 - the Windows eye is capped at 800 px again",
     "file": "capture_win.ps1",
     "find": "    int filmW = 1920, filmH = 1080;\n",
     "replace": "    int filmW = 800, filmH = 450;\n",
     "matches": 1},
    {"why": "REG-3581 - the Windows eye is encoded at q72 again",
     "file": "capture_win.ps1",
     "find": "          ep.Param[0] = new EncoderParameter(System.Drawing.Imaging.Encoder.Quality, 82L);\n",
     "replace": "          ep.Param[0] = new EncoderParameter(System.Drawing.Imaging.Encoder.Quality, 72L);\n",
     "matches": 1},
    {"why": "REG-3581 - the Windows eye downscales with bilinear again",
     "file": "capture_win.ps1",
     "find": "      eg.InterpolationMode = System.Drawing.Drawing2D.InterpolationMode.HighQualityBicubic;\n",
     "replace": "      eg.InterpolationMode = System.Drawing.Drawing2D.InterpolationMode.Bilinear;\n",
     "matches": 1},
    {"why": "REG-3581 - the Python film defaults to 1440 px again",
     "file": "tv_diablo.py",
     "find": 'FILM_MAX_PX = max(1280, min(3840, int(os.environ.get("TV_FILM_MAX_PX", "1920") or 1920)))\n',
     "replace": 'FILM_MAX_PX = max(1280, min(3840, int(os.environ.get("TV_FILM_MAX_PX", "1440") or 1440)))\n',
     "matches": 1},
    {"why": "REG-3582 - shadow theatre uploads a 160 px thumb again",
     "file": "shadow_sessions.py",
     "find": "SHADOW_FRAME_PX = 1920\n",
     "replace": "SHADOW_FRAME_PX = 160\n",
     "matches": 1},
    {"why": "REG-3582 - the worker refuses a film-size JPEG as too big",
     "file": "functions/api/roster.js",
     "find": "const FRAMES_MAX_JPG_B64 = 1100000;        // v3894: 800 KB of JPEG, base64 (was 20 KB / 160 px)\n",
     "replace": "const FRAMES_MAX_JPG_B64 = 27400;        // 20 KB of JPEG, base64\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
