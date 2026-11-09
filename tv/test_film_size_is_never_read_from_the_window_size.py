# -*- coding: utf-8 -*-
"""v3894 (#155/#255, REG-3577) - FILM SIZE IS NEVER READ FROM THE WINDOW SIZE.

film_size_of returns (filmW, filmH) or None. A reel that only recorded the window
client size does not pretend those pixels are the jpeg.
RED_PROOF below.
"""
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()


def _read(rel):
    path = os.path.join(HERE, os.path.basename(rel)) if rel.startswith("tv/") else os.path.join(ROOT, rel)
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


class FilmSizeIsNeverReadFromTheWindowSize(unittest.TestCase):

    def test_film_size_of_ignores_window_wh(self):
        import capture_stamp as CS
        self.assertIsNone(CS.film_size_of({"capture": {"w": 1920, "h": 1080}}))
        self.assertEqual(CS.film_size_of({"capture": {"w": 1920, "h": 1080, "filmW": 800, "filmH": 450}}), (800, 450))
        self.assertIsNone(CS.film_size_of({"capture": {"filmW": 800}}))
        self.assertIsNone(CS.film_size_of({"w": 800, "h": 450}))


RED_PROOF = [
    {"why": "v3894 (#155, REG-3577) - film_size_of falls back to the window size",
     "file": "tv/capture_stamp.py",
     "find": "    w, h = _whole(src.get(\"filmW\")), _whole(src.get(\"filmH\"))\n    if w and h:\n        return (w, h)\n    return None\n",
     "replace": "    w, h = _whole(src.get(\"filmW\")), _whole(src.get(\"filmH\"))\n    if w and h:\n        return (w, h)\n    w, h = _whole(src.get(\"w\")), _whole(src.get(\"h\"))\n    if w and h:\n        return (w, h)\n    return None\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
