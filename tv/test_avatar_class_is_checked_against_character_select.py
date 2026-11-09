# -*- coding: utf-8 -*-
"""v3893 (REG-3559) - AVATAR CLASS IS CHECKED AGAINST THE CHARACTER-SELECT CLASS.

The in-game avatar class and the class read on character select are a soft cross-check.
They agree, they conflict, or the check is unknown when either side was not read.
attribute_character is unchanged: disagreeing classes there still leave the name UNKNOWN.
The digest carries the check as classCheck, next to the existing character seal.
RED_PROOF below.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import read_identity as RI  # noqa: E402


class AvatarClassIsCheckedAgainstCharacterSelect(unittest.TestCase):

    def test_agree_conflict_and_unknown(self):
        sel = {"name": "Blizzy", "cls": "Sorceress", "level": 90, "source": "select-screen"}
        av_ok = {"name": None, "cls": "Sorceress", "level": None, "source": "avatar"}
        av_no = {"name": None, "cls": "Barbarian", "level": None, "source": "avatar"}
        self.assertEqual(RI.class_crosscheck([sel, av_ok]),
                         {"select": "Sorceress", "avatar": "Sorceress", "agree": True})
        self.assertEqual(RI.class_crosscheck([sel, av_no]),
                         {"select": "Sorceress", "avatar": "Barbarian", "agree": False})
        self.assertEqual(RI.class_crosscheck([sel])["agree"], None)
        self.assertIsNone(RI.class_crosscheck([sel])["avatar"])

    def test_attribute_character_still_unknowns_a_class_conflict(self):
        sigs = [
            {"name": "Blizzy", "cls": "Sorceress", "level": 90, "source": "select-screen"},
            {"name": None, "cls": "Barbarian", "level": None, "source": "avatar"},
        ]
        got = RI.attribute_character(sigs)
        self.assertTrue(got["conflict"])
        self.assertIsNone(got["name"])
        self.assertIsNone(got["cls"])

    def test_the_digest_carries_the_check(self):
        with open(os.path.join(HERE, "shadow_sessions.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn('s["classCheck"] = class_crosscheck(_sig)', src)
        self.assertIn("class_crosscheck, soft_understanding", src)


RED_PROOF = [
    {"why": "v3893 (REG-3559) - avatar vs select no longer compares the two classes",
     "file": "tv/read_identity.py",
     "find": "    agree = None if not select or not avatar else (select == avatar)\n",
     "replace": "    agree = None\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
