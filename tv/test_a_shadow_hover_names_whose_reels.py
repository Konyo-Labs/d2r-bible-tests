# -*- coding: utf-8 -*-
"""A shadow's Characters hover names the owner's reels: the In-game title says whose reels learned them and the shadow rewrite covers titles.

RED_PROOF below: each one, applied, turns this law red."""
import os
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
  "bible.html",
  "    ladder = 'Characters this console\\'s reels learned · ' + ladder;\n",
  1
 ],
 [
  "bible.html",
  "          var _t = node.getAttribute('title');\n",
  1
 ]
]


class TheLawHolds(unittest.TestCase):
    def test_each_line_is_where_it_should_be(self):
        for f, needle, n in CHECKS:
            self.assertEqual(_read(f).count(needle), n, "%s: %r should appear %d time(s)" % (f, needle, n))


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
  "why": "the rewrite skips hovers again",
  "file": "bible.html",
  "find": "          var _t = node.getAttribute('title');\n",
  "replace": "          var _t = null;\n",
  "matches": 1
 },
 {
  "why": "the hover stops saying whose reels",
  "file": "bible.html",
  "find": "    ladder = 'Characters this console\\'s reels learned · ' + ladder;\n",
  "replace": "",
  "matches": 1
 }
]

if __name__ == "__main__":
    unittest.main()
