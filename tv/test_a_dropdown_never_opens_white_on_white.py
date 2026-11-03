# -*- coding: utf-8 -*-
"""#13: every native dropdown on the board opens dark - pale option text on a light native sheet was white on white (Vault editor Quality/Base, cube-up, character builder).

RED_PROOF below: each one, applied, turns this law red."""
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")


def _read(p):
    return open(os.path.join(ROOT, p), encoding="utf-8").read()


CHECKS = [
 [
  "bible.html",
  "select{color-scheme:dark}select option,select optgroup{background:var(--surface);color:var(--text)}",
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
  "why": "drop the dark sheet and the options go white on white again",
  "file": "bible.html",
  "find": "select{color-scheme:dark}select option",
  "replace": "select{}select option",
  "matches": 1
 },
 {
  "why": "drop the option background and pale text sits on the light sheet",
  "file": "bible.html",
  "find": "select optgroup{background:var(--surface);",
  "replace": "select optgroup{",
  "matches": 1
 }
]

if __name__ == "__main__":
    unittest.main()
