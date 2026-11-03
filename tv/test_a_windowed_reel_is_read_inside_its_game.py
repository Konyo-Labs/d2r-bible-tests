# -*- coding: utf-8 -*-
"""A lobby filmed in a window is measured inside its game area, and an empty In-game section says why no character was read.

RED_PROOF below: each one, applied, turns this law red."""
import json, os, shutil, subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable; enable()
ROOT = os.path.join(HERE, "..")


def _read(p):
    return open(os.path.join(ROOT, p), encoding="utf-8").read()


CHECKS = [
 [
  "tv/char_select.py",
  "            im = _in_game(im.convert(\"RGB\")).convert(\"HSV\")\n",
  1
 ],
 [
  "tv/char_select.py",
  "    return im if box == (0, 0) + im.size else im.crop(box)\n",
  1
 ],
 [
  "tv/console_doctor.py",
  "    (\"a windowed frame is read inside its game\", _check_a_windowed_frame_is_read_inside_its_game),\n",
  1
 ],
 [
  "bible.html",
  "data-none-why=",
  1
 ]
]


class TheLawHolds(unittest.TestCase):
    def test_each_line_is_where_it_should_be(self):
        for f, needle, n in CHECKS:
            self.assertEqual(_read(f).count(needle), n, "%s: %r should appear %d time(s)" % (f, needle, n))

    def test_dean_window_sizes_read_inside_their_game(self):
        import tempfile, shutil
        sys.path.insert(0, HERE)
        import char_select as C
        d = tempfile.mkdtemp(prefix="win_")
        try:
            # Dean's 800-wide windowed family: frame, game (16:9 inside title bar + letterbox)
            for fr, g in (((799, 434), (714, 402)), ((799, 456), (754, 424)), ((800, 402), (660, 371)),
                          ((800, 409), (672, 378)), ((800, 450), (743, 418))):
                p = C.windowed_fixture(os.path.join(d, "f_%dx%d.jpg" % fr), frame=fr, game=g)
                ok, why = C.looks_like_lobby(C.lobby_stats(p))
                self.assertTrue(ok, "a %dx%d windowed lobby is not seen: %s" % (fr + (why,)))
            # a full-screen frame is measured whole, and play stays play inside a window
            full = C.windowed_fixture(os.path.join(d, "f_full.jpg"), frame=(1440, 810), title=0, game=(1440, 810))
            self.assertTrue(C.looks_like_lobby(C.lobby_stats(full))[0])
            play = C.windowed_fixture(os.path.join(d, "f_play.jpg"), sat=0.8, val=0.5)
            self.assertFalse(C.looks_like_lobby(C.lobby_stats(play))[0], "a windowed play frame passed as the lobby")
        finally:
            shutil.rmtree(d, True)


class TheProofsNameOnePlace(unittest.TestCase):
    def test_each_find_matches_once(self):
        for p in RED_PROOF:
            self.assertEqual(_read(p["file"]).count(p["find"]), p["matches"], p["why"])

    def test_each_proof_turns_a_check_red(self):
        for p in RED_PROOF:
            after = _read(p["file"]).replace(p["find"], p["replace"])
            red = any(f == p["file"] and after.count(nd) != n for f, nd, n in CHECKS)
            self.assertTrue(red, "this proof would not turn the law red: " + p["why"])


RED_PROOF = [
 {
  "why": "the lobby scan measures the whole window again",
  "file": "tv/char_select.py",
  "find": "            im = _in_game(im.convert(\"RGB\")).convert(\"HSV\")\n",
  "replace": "            im = im.convert(\"RGB\").convert(\"HSV\")\n",
  "matches": 1
 },
 {
  "why": "the crop keeps the whole frame",
  "file": "tv/char_select.py",
  "find": "    return im if box == (0, 0) + im.size else im.crop(box)\n",
  "replace": "    return im\n",
  "matches": 1
 },
 {
  "why": "the empty section stops saying why",
  "file": "bible.html",
  "find": "data-none-why=",
  "replace": "data-none-x=",
  "matches": 1
 }
]

if __name__ == "__main__":
    unittest.main()
