# -*- coding: utf-8 -*-
"""v3856 - THE FLEET ROW SAYS BLIND GATES. A current census with blind gates shut every river lock, yet the Mac row showed no chip (#230 6506572227). The row now says 'locks shut · N gates blind'.

RED_PROOF below: each one, applied, turns this law red."""
import os
import unittest
import sys as _cs_sys
_cs_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from console_safe import enable; enable()

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")


def _read(p):
    return open(os.path.join(ROOT, p), encoding="utf-8").read()


CHECKS = [
 [
  "tv/control_ui.html",
  "if (census === 'current' && _blindN) {",
  1
 ],
 [
  "tv/control_ui.html",
  "gate' + (_blindN === 1 ? '' : 's') + ' blind</span>",
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
  "why": "the blind chip is never drawn",
  "file": "tv/control_ui.html",
  "find": "if (census === 'current' && _blindN) {",
  "replace": "if (false) {",
  "matches": 1
 }
]

if __name__ == "__main__":
    unittest.main()
