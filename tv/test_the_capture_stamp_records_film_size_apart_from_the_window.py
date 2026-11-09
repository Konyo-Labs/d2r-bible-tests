# -*- coding: utf-8 -*-
"""v3894 (#155/#255, REG-3565) - FILM SIZE IS RECORDED APART FROM THE WINDOW.

from_measured copies filmW/filmH only when both were measured under those names.
Window w/h never become film size. from_index reads them back as None when absent.
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


class TheCaptureStampRecordsFilmSizeApartFromTheWindow(unittest.TestCase):

    def test_window_size_is_not_copied_into_film_size(self):
        import capture_stamp as CS
        got = CS.from_measured({"w": 1920, "h": 1080, "filmW": 800, "filmH": 450})
        self.assertEqual((got["w"], got["h"]), (1920, 1080))
        self.assertEqual((got["filmW"], got["filmH"]), (800, 450))
        bare = CS.from_measured({"w": 1920, "h": 1080})
        self.assertNotIn("filmW", bare)
        self.assertNotIn("filmH", bare)
        back = CS.from_index({"capture": {"w": 1920, "h": 1080}})
        self.assertIsNone(back["filmW"])
        self.assertIsNone(back["filmH"])
        self.assertEqual((back["w"], back["h"]), (1920, 1080))


RED_PROOF = [
    {"why": "v3894 (#155, REG-3565) - filmW/filmH are copied from the window's w/h",
     "file": "tv/capture_stamp.py",
     "find": "    fw, fh = _whole(measured.get(\"filmW\")), _whole(measured.get(\"filmH\"))\n",
     "replace": "    fw, fh = _whole(measured.get(\"w\")), _whole(measured.get(\"h\"))\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
