# -*- coding: utf-8 -*-
"""The D2JSP price-reading probe waits for the 228-card list to go quiet before releasing the held reading, so late paints under load are not billed to the reading.

RED_PROOF below: each one, applied, turns this law red."""
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")


def _read(p):
    return open(os.path.join(ROOT, p), encoding="utf-8").read()


CHECKS = [
 [
  "tv/test_d2jsp_cards_stay_cheap.py",
  "calm < 5; qw++",
  1
 ],
 [
  "tv/test_d2jsp_cards_stay_cheap.py",
  "out.quietBeforeReading = calm >= 5;",
  1
 ],
 [
  "tv/test_d2jsp_cards_stay_cheap.py",
  "never went quiet before the held reading",
  1
 ],
 [
  "tv/test_d2jsp_cards_stay_cheap.py",
  "READING_CARDS",
  5
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
  "why": "drop the quiet wait",
  "file": "tv/test_d2jsp_cards_stay_cheap.py",
  "find": "calm < 5; qw++",
  "replace": "calm < 0; qw++",
  "matches": 1
 },
 {
  "why": "drop the quiet flag",
  "file": "tv/test_d2jsp_cards_stay_cheap.py",
  "find": "out.quietBeforeReading = calm >= 5;",
  "replace": "",
  "matches": 1
 }
]

if __name__ == "__main__":
    unittest.main()
