# -*- coding: utf-8 -*-
"""v3894 (#155/#255, REG-3566) - A NEW REEL STAMPS THE FILMED JPEG'S PIXELS.

The seal measures the first listed frame with film_size_from_jpeg and writes
filmW/filmH onto capture. It does not copy the window client size into those keys.
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


class ANewReelStampsTheFilmedJpegSize(unittest.TestCase):

    def test_the_seal_measures_the_listed_jpeg(self):
        src = _read("tv/tv_diablo.py")
        self.assertIn("film_size_from_jpeg", src)
        self.assertIn('_merged["filmW"], _merged["filmH"] = _film', src)
        self.assertIn("from_measured(_merged)", src)
        self.assertIn("for _fn in _idx:", src)


RED_PROOF = [
    {"why": "v3894 (#155, REG-3566) - the seal no longer measures the filmed jpeg",
     "file": "tv/tv_diablo.py",
     "find": "                        _film = _cs.film_size_from_jpeg(os.path.join(_reel, _fn))\n",
     "replace": "                        _film = None\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
