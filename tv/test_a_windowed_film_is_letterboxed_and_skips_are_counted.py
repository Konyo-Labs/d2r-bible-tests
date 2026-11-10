# -*- coding: utf-8 -*-
"""#115 (REG-3624) - A WINDOWED CLIENT IS LETTERBOXED ONTO 1920x1080 AND FILM SKIPS ARE COUNTED BY REASON.

His ask: even when Dean plays windowed (measured 1507x755, #255 / Claude 2026-11-07), record at full
resolution, find the game in the frame, cut it out and scale it onto 1920x1080 without stretching
the aspect (bars, not a squash). v3894 already letterboxes in capture_win.ps1 (d01f1e689). This law
holds the geometry in Python so panel-relative reader bands (inventory, stash, character select)
map through the same place, and skip events are counted by reason (desktop-refused is not the same
number as no-game-window).

Held here: Dean's 1507x755 fills the 1920 width with bars top and bottom; a band on that client
lands inside the letterboxed game, never on a bar; skips group by their named reason. RED_PROOF below.
"""
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import film_letterbox as F  # noqa: E402

CAP = os.path.join(HERE, "capture_win.ps1")


class AWindowedFilmIsLetterboxed(unittest.TestCase):

    def test_dean_1507x755_fills_the_1920_width_with_bars(self):
        p = F.letterbox_place(1507, 755)
        self.assertIsNotNone(p)
        self.assertEqual(p["nw"], 1920, p)
        self.assertGreater(p["nh"], 950)
        self.assertLess(p["nh"], 970)
        self.assertEqual(p["ox"], 0, p)
        self.assertGreater(p["oy"], 50)
        filled = p["oy"] * 2 + p["nh"]
        self.assertIn(filled, (1079, 1080), "the bars plus the game do not fill 1080: %s" % p)

    def test_a_panel_band_lands_inside_the_letterboxed_game(self):
        # a stash-grid-shaped band in the lower half of Dean's client
        band = F.map_panel_band((200, 400, 400, 300), (1507, 755))
        p = F.letterbox_place(1507, 755)
        self.assertIsNotNone(band)
        self.assertGreaterEqual(band["x"], p["ox"])
        self.assertGreaterEqual(band["y"], p["oy"])
        self.assertLessEqual(band["x"] + band["w"], p["ox"] + p["nw"])
        self.assertLessEqual(band["y"] + band["h"], p["oy"] + p["nh"])
        self.assertGreater(band["y"], p["oy"], "a mid-window band was mapped onto the top bar")

    def test_skips_are_counted_by_reason(self):
        got = F.count_skips([
            "no-game-window", "desktop-refused", "desktop-refused",
            {"reason": "stood-aside"}, "mystery", "", None,
        ])
        self.assertEqual(got["no-game-window"], 1)
        self.assertEqual(got["desktop-refused"], 2)
        self.assertEqual(got["stood-aside"], 1)
        self.assertEqual(got["client-empty"], 0)
        self.assertEqual(got["other"], 1, "an unnamed skip was dropped or invented: %s" % got)

    def test_the_windows_capture_still_letterboxes_onto_1920x1080(self):
        with io.open(CAP, encoding="utf-8") as fh:
            s = fh.read()
        self.assertIn("int filmW = 1920, filmH = 1080;", s)
        self.assertIn("Math.Min(filmW / (double)bmp.Width, filmH / (double)bmp.Height)", s)


RED_PROOF = [
    {"why": "REG-3624 - a 1507x755 client is stretched to fill 1080 tall (squashed aspect)",
     "file": "tv/film_letterbox.py",
     "find": "    scale = min(film_w / float(src_w), film_h / float(src_h))\n",
     "replace": "    scale = film_h / float(src_h)\n",
     "matches": 1},
    {"why": "REG-3624 - skip reasons are flattened into one number",
     "file": "tv/film_letterbox.py",
     "find": '        if r in SKIP_REASONS:\n            out[r] += 1\n        else:\n            out["other"] += 1\n',
     "replace": '        out["other"] += 1\n',
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
