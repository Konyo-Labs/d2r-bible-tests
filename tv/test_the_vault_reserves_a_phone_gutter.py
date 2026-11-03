# -*- coding: utf-8 -*-
"""v3856 (board #224) - THE VAULT RESERVES A PHONE GUTTER. At 375 px the fixed dock badges, compass and ? (~44 px + 12 px inset) sat over the right edge of the Vault's lockers and FIND row. Under 480 px the Vault column keeps a 56 px right gutter.

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
  "@media (max-width:480px){#tab-vault{padding-right:56px;box-sizing:border-box}}",
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
  "why": "the Vault loses its phone gutter",
  "file": "bible.html",
  "find": "@media (max-width:480px){#tab-vault{padding-right:56px;box-sizing:border-box}}",
  "replace": "",
  "matches": 1
 }
]

if __name__ == "__main__":
    unittest.main()
