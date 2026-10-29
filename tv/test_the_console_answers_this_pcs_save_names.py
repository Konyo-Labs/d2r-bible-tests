# -*- coding: utf-8 -*-
"""#251 (REG-2926) - THE CONSOLE ANSWERS GET /api/saves WITH THIS PC'S SAVE NAMES, AND KEEPS THE ANSWER WHILE THE FOLDERS
STAND STILL.

control_app.saves_answer() is tv/d2s_read.saves() behind one route, kept while nothing in the save folders changes (each
folder's mtime, every .d2s's size and mtime - a .d2s is read whole). A folder that will not stat or list is never kept,
and a failure is UNKNOWN (chars None), never an empty roster. Fixtures only: the folders are made in this process's own
scratch and passed in; the route itself passes none, so the console reads its own PC. RED_PROOF below.
"""
import io
import os
import re
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
from console_safe import enable as _enable  # noqa: E402
_enable()

import control_app as CA  # noqa: E402
import d2s_read as D  # noqa: E402


def _pc():
    sg = os.path.join(tempfile.mkdtemp(), "Saved Games")
    d = os.path.join(sg, D.SAVE_DIR_NAME)
    os.makedirs(d)
    for n in ("Konyolock1234567.ctlo", "Settings.json"):
        with io.open(os.path.join(d, n), "w", encoding="utf-8") as fh:
            fh.write("x")
    return sg, d


class _Counting(object):
    def __init__(self):
        self.n = 0

    def __call__(self, *a):
        self.n += 1
        return D.saves(*a)


class TheConsoleAnswersThisPcsSaveNames(unittest.TestCase):

    def setUp(self):
        CA._SAVES_CACHE["sig"] = CA._SAVES_CACHE["answer"] = None

    def test_the_answer_is_the_readers(self):
        sg, _ = _pc()
        got = CA.saves_answer(platform="windows", saved_games=sg)
        self.assertEqual(got["chars"], [{"name": "Konyolock", "ids": 1}])
        self.assertEqual(got["chars"], D.saves(platform="windows", saved_games=sg)["chars"])

    def test_a_folder_that_stood_still_is_not_read_again(self):
        sg, _ = _pc()
        read = _Counting()
        first = CA.saves_answer(platform="windows", saved_games=sg, _read=read)
        again = CA.saves_answer(platform="windows", saved_games=sg, _read=read)
        self.assertEqual(read.n, 1, "the save folder was read again though nothing in it changed")
        self.assertTrue(again.get("cached"))
        self.assertEqual(again["chars"], first["chars"])

    def test_a_new_character_is_read_at_once(self):
        sg, d = _pc()
        read = _Counting()
        CA.saves_answer(platform="windows", saved_games=sg, _read=read)
        with io.open(os.path.join(d, "Hammer-Din987654.keyo"), "w", encoding="utf-8") as fh:
            fh.write("x")
        st = os.stat(d)
        os.utime(d, ns=(st.st_atime_ns, st.st_mtime_ns + 2000000000))   # a coarse clock still sees the folder change
        got = CA.saves_answer(platform="windows", saved_games=sg, _read=read)
        self.assertEqual(read.n, 2, "a folder that gained a character was answered from the kept copy")
        self.assertEqual([c["name"] for c in got["chars"]], ["Hammer-Din", "Konyolock"])

    def test_no_folder_is_unknown(self):
        got = CA.saves_answer(platform="windows", saved_games=tempfile.mkdtemp())
        self.assertIsNone(got["chars"])

    def test_a_failure_is_unknown_not_an_empty_roster(self):
        def boom(*a):
            raise PermissionError("denied")
        orig = D.save_dirs
        D.save_dirs = boom
        try:
            got = CA.saves_answer(platform="windows", saved_games=tempfile.mkdtemp())
        finally:
            D.save_dirs = orig
        self.assertIs(got["ok"], False)
        self.assertIsNone(got["chars"])
        self.assertIn("PermissionError", got["why"])

    def test_the_route_answers_from_saves_answer(self):
        src = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        self.assertRegex(src, r'\n        if path == "/api/saves":\n            self\._json\(200, saves_answer\(\)\)',
                         "GET /api/saves does not answer from saves_answer() with no fixture arguments")


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {"why": "#251 (REG-2926) - the kept answer is never used, so every poll reads the save folder (and every .d2s) again",
     "file": "tv/control_app.py",
     "find": '        if sig is not None and _SAVES_CACHE["sig"] == key and isinstance(_SAVES_CACHE["answer"], dict):\n',
     "replace": '        if False:\n',
     "matches": 1},
    {"why": "#251 (REG-2926) - the kept answer ignores a folder that changed, so a new character never appears",
     "file": "tv/control_app.py",
     "find": "            sig.append((d, os.stat(d).st_mtime_ns))\n",
     "replace": "            sig.append((d, 0))\n",
     "matches": 1},
    {"why": "#251 (REG-2926) - a failed look for the save folder reads as a PC with no characters",
     "file": "tv/control_app.py",
     "find": '        return {"ok": False, "state": "unknown", "chars": None, "d2s": None,\n                "why": "looking for the save folder raised %s" % type(e).__name__}\n',
     "replace": '        return {"ok": False, "state": "unknown", "chars": [], "d2s": None,\n                "why": "looking for the save folder raised %s" % type(e).__name__}\n',
     "matches": 1},
]
