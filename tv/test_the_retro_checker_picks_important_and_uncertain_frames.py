# -*- coding: utf-8 -*-
"""v3895 (#190, REG-3590) - THE RETRO CHECKER PICKS IMPORTANT AND UNCERTAIN FRAMES.

A sealed reel's journal is walked; grails/keeps/uniques/sets/runewords and
rows where KAI and OCR disagreed are selected. Ordinary frames are not.
An unreadable journal is UNKNOWN. Calling a second model is the rest of #190.
RED_PROOF below.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _enable  # noqa: E402
_enable()

import retro_checker as RC  # noqa: E402


class TheRetroCheckerPicksImportantAndUncertainFrames(unittest.TestCase):

    def test_it_picks_important_and_uncertain_only(self):
        journal = [
            {"frame": "f_1", "kind": "unique", "kai": "Shako", "ocr": "Shako"},
            {"frame": "f_2", "kind": "magic", "kai": "ring", "ocr": "ring"},
            {"frame": "f_3", "kind": "rare", "kai": "jewel", "ocr": "charm"},
            {"frame": "f_4", "kind": "grail"},
            {"frame": "f_1", "kind": "unique"},  # already picked
        ]
        got = RC.pick_frames(journal)
        self.assertEqual([g["frame"] for g in got], ["f_1", "f_3", "f_4"])
        self.assertIn("important", got[0]["why"])
        self.assertIn("uncertain", got[1]["why"])
        self.assertEqual(got[2]["kind"], "grail")

    def test_empty_is_none_and_unreadable_is_unknown(self):
        self.assertEqual(RC.pick_frames([]), [])
        self.assertIsNone(RC.pick_frames(None))

    def test_an_ordinary_session_picks_nothing(self):
        self.assertEqual(RC.pick_frames([{"frame": "f_9", "kind": "magic", "kai": "a", "ocr": "a"}]), [])


RED_PROOF = [
    {"why": "v3895 (#190, REG-3590) - an ordinary agreeing frame is picked as if it were uncertain",
     "file": "tv/retro_checker.py",
     "find": "            or (row.get(\"kai\") not in (None, \"\") and row.get(\"ocr\") not in (None, \"\")\n                and row.get(\"kai\") != row.get(\"ocr\"))\n",
     "replace": "            or (row.get(\"kai\") not in (None, \"\") and row.get(\"ocr\") not in (None, \"\"))\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
