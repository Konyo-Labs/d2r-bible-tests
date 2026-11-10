# -*- coding: utf-8 -*-
"""v3895 (#22, REG-3587) - STASH AND CHRONICLE READERS SHARE ONE CALIBRATION FILM.

Each reader used to carry its own (2940, 1912) copy. A re-measure that updated one
would leave the other reading a screen shape that no longer exists. Both now import
reader_calibration.FILM. The later calibration phase (re-measuring live, buff %) is
not this slice.
RED_PROOF below.
"""
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _enable  # noqa: E402
_enable()

import reader_calibration as RC  # noqa: E402
import stash_eye as SE  # noqa: E402
import chronicle_template as CT  # noqa: E402


class ReadersShareOneCalibrationFilm(unittest.TestCase):

    def test_both_readers_use_the_shared_film(self):
        self.assertEqual(RC.FILM, (2940, 1912))
        self.assertEqual(SE._CROP_CAL_FILM, RC.FILM)
        self.assertEqual(CT._CAL_FILM, RC.FILM)
        self.assertEqual(SE._CROP_CAL_FILM, CT._CAL_FILM)
        self.assertEqual(SE._CROP_CAL_ASPECT, RC.aspect())
        self.assertEqual(CT._CAL_ASPECT, RC.aspect())

    def test_the_aspect_is_the_exact_ratio(self):
        self.assertEqual(RC.aspect(), 2940 / 1912.0)
        self.assertNotEqual(round(RC.aspect(), 3), RC.aspect())


RED_PROOF = [
    {"why": "v3895 (#22, REG-3587) - chronicle_template keeps a private film again",
     "file": "tv/chronicle_template.py",
     "find": "_CAL_FILM = _RC.FILM\n",
     "replace": "_CAL_FILM = (1920, 1080)\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
