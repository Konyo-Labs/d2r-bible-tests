# -*- coding: utf-8 -*-
"""#255 (v3881) - THE READER-PARITY BENCH IS AN INSTRUMENT, AND AN INSTRUMENT NEVER SEEN RED MEASURES NOTHING.

tv/reader_parity.py runs every deterministic eye over real frames in every capture shape (Mac 1440, Windows 800, windowed
caption, caption cut) on the Mac and on a Windows PC. Its verdicts are only as good as its variants and its comparison, so
those are pinned here on synthetic frames - no corpus needed:
  * the windowed variant puts a light caption strip on top and pushes the content down (what PrintWindow did);
  * the caption finder finds that strip, and finds NONE on a dark game frame (31 of 32 vs 0 of 16 on the real corpus is
    only evidence if it cannot fire on a frame without one);
  * the cut removes exactly the strip; the Windows eye variant is capture_win.ps1's 800 px / q72;
  * an empty corpus REFUSES (an empty bench is UNKNOWN, never a pass), and an eye that raised is never an agreement.
RED_PROOF below. [[unknown-stays-unknown]] [[regression-guard]]
"""
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

import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()   # v3881 pre-flight - its mkdtemp scratch is collected (test_a_test_run_leaves_no_scratch_dirs)
import reader_parity as rp  # noqa: E402


def _game_frame(path, size=(1440, 936)):
    """a dark, textured frame - what a D2R frame's top rows look like (never a uniform light band)"""
    from PIL import Image
    im = Image.new("RGB", size, (22, 18, 14))
    px = im.load()
    for y in range(0, size[1], 7):
        for x in range(0, size[0], 5):
            px[x, y] = (60 + (x * 7) % 90, 50 + (y * 3) % 60, 30)
    im.save(path, "JPEG", quality=92)
    return path


class TheBenchMeasuresWhatItSays(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="tvd_bench_")
        self.f = _game_frame(os.path.join(self.d, "f_1.jpg"))

    def test_a_game_frame_has_no_caption(self):
        self.assertEqual(rp.caption_rows(self.f), 0, "the caption finder fires on a frame that has none")

    def test_the_windowed_variant_carries_a_caption_and_the_cut_removes_exactly_it(self):
        """* THE POINT: the bench's windowed variant is the PrintWindow defect, and its cut is exact"""
        from PIL import Image
        tb = rp.titlebar(self.f, os.path.join(self.d, "tb.jpg"))
        cap = int(round(936 * rp.CAPTION_FRAC))
        n = rp.caption_rows(tb)
        self.assertTrue(cap - 2 <= n <= cap + 1, "found %d caption rows, the variant drew %d" % (n, cap))
        with Image.open(tb) as a, Image.open(self.f) as b:
            self.assertEqual(a.size, b.size, "the windowed variant changed the frame's size - PrintWindow does not")
        cut = rp.untitled(tb, os.path.join(self.d, "cut.jpg"))
        with Image.open(cut) as c:
            self.assertEqual(c.size, (1440, 936 - n))
        self.assertIsNone(rp.untitled(self.f, os.path.join(self.d, "none.jpg")), "a frame with no caption was cut")

    def test_the_windows_eye_variant_is_capture_wins(self):
        from PIL import Image
        w = rp.win800(self.f, os.path.join(self.d, "w.jpg"))
        with Image.open(w) as im:
            self.assertEqual((max(im.size), im.format), (800, "JPEG"))
        small = _game_frame(os.path.join(self.d, "s.jpg"), (640, 400))
        with Image.open(rp.win800(small, os.path.join(self.d, "ws.jpg"))) as im:
            self.assertEqual(im.size, (640, 400), "the eye variant enlarged a frame - capture_win only ever shrinks")

    def test_an_empty_corpus_refuses(self):
        with self.assertRaises(SystemExit):
            rp.bench(corpus=os.path.join(self.d, "nothing-here"), per_reel=1, say=lambda *_: None)

    def test_an_eye_that_raised_is_never_an_agreement(self):
        self.assertIsNone(rp._same({"unknown": "ValueError"}, {"unknown": "ValueError"}))
        self.assertIsNone(rp._same("stash", {"unknown": "x"}))
        self.assertTrue(rp._same("stash", "stash"))
        self.assertFalse(rp._same("stash", "gameplay"))


RED_PROOF = [
    {"why": "#255 - the caption finder fires on a dark game frame (the 31-of-32 evidence would mean nothing)",
     "file": "tv/reader_parity.py", "find": "        if mean > 180 and light > 0.7:", "replace": "        if mean > 10:",
     "matches": 1},
    {"why": "#255 - the windowed variant draws no caption strip",
     "file": "tv/reader_parity.py", "find": "    out.paste((243, 243, 243), (0, 0, w, cap))", "replace": "    pass",
     "matches": 1},
    {"why": "#255 - the Windows eye variant is not capped at 800 px",
     "file": "tv/reader_parity.py", "find": "WIN_EYE_PX, WIN_EYE_Q = 800, 72", "replace": "WIN_EYE_PX, WIN_EYE_Q = 1440, 72",
     "matches": 1},
    {"why": "#255 - an empty corpus passes as a bench",
     "file": "tv/reader_parity.py",
     "find": '        raise SystemExit("no corpus at %s - the bench has nothing to read (UNKNOWN, not a pass)" % corpus)',
     "replace": '        return {"frames": [], "parity": {}}', "matches": 1},
    {"why": "#255 - an eye that raised counts as an agreement",
     "file": "tv/reader_parity.py",
     "find": '    if isinstance(a, dict) and "unknown" in a or isinstance(b, dict) and "unknown" in b:\n        return None',
     "replace": '    if isinstance(a, dict) and "unknown" in a or isinstance(b, dict) and "unknown" in b:\n        return True',
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
