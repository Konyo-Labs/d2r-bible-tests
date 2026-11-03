# -*- coding: utf-8 -*-
"""Five law files carried an invalid backslash escape ('\\s', '\\*', '\\w', '\\-') in a docstring. Python 3.12 warns
on it (SyntaxWarning in every census parse) and a later Python makes it a SyntaxError: the law would stop loading.
Each one is doubled now; the value of the docstring is unchanged. This law compiles each file with warnings as errors.

RED_PROOF below: each one, applied, turns this law red."""
import os
import sys
import unittest
import warnings

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable; enable()
ROOT = os.path.join(HERE, "..")

FILES = ["tv/test_app_ctx_nav.py", "tv/test_control.py", "tv/test_the_board_folds_the_apostrophe_too.py",
         "tv/test_the_shelf_tabs_are_the_real_sessions.py", "tv/test_the_world_band_leaves_room_for_the_ladder_ribbon.py"]


def _read(p):
    return open(os.path.join(ROOT, p), encoding="utf-8").read()


def _warns(src, name):
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        compile(src, name, "exec")
    return [str(x.message) for x in w if issubclass(x.category, SyntaxWarning)]


CHECKS = [
 ["tv/test_app_ctx_nav.py", "two arguments defeat the `\\\\s*\\\\)`", 1],
 ["tv/test_control.py", "`[A-Za-z0-9_.\\\\-$(\\\\[]`", 1],
 ["tv/test_control.py", "a greedy `/*.*\\\\*/` once ate", 1],
 ["tv/test_the_board_folds_the_apostrophe_too.py", "`/\\\\*.*?\\\\*/` with DOTALL", 1],
 ["tv/test_the_shelf_tabs_are_the_real_sessions.py", "`(?![\\\\w-])` boundary", 1],
 ["tv/test_the_world_band_leaves_room_for_the_ladder_ribbon.py", "`[}\\\\s]#id{`", 1],
]


class TheLawHolds(unittest.TestCase):
    def test_each_line_is_where_it_should_be(self):
        for f, needle, n in CHECKS:
            self.assertEqual(_read(f).count(needle), n, "%s: %r should appear %d time(s)" % (f, needle, n))

    def test_each_file_compiles_without_a_syntax_warning(self):
        for f in FILES:
            self.assertEqual(_warns(_read(f), f), [], f + " has an invalid escape: a later Python refuses to load it")


class TheProofsNameOnePlace(unittest.TestCase):
    def test_each_find_matches_once(self):
        for p in RED_PROOF:
            self.assertEqual(_read(p["file"]).count(p["find"]), p["matches"], p["why"])

    def test_each_proof_turns_a_check_red(self):
        for p in RED_PROOF:
            after = _read(p["file"]).replace(p["find"], p["replace"])
            red = any(f == p["file"] and after.count(nd) != n for f, nd, n in CHECKS) or bool(_warns(after, p["file"]))
            self.assertTrue(red, "this proof would not turn the law red: " + p["why"])


RED_PROOF = [
 {"file": "tv/test_app_ctx_nav.py", "find": "defeat the `\\\\s*\\\\)`", "replace": "defeat the `\\s*\\)`", "matches": 1,
  "why": "the ctx-nav law carries '\\s' again"},
 {"file": "tv/test_the_shelf_tabs_are_the_real_sessions.py", "find": "`(?![\\\\w-])`", "replace": "`(?![\\w-])`", "matches": 1,
  "why": "the shelf-tabs law carries '\\w' again"},
]

if __name__ == "__main__":
    unittest.main()
