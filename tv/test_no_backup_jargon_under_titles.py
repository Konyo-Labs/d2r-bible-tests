# -*- coding: utf-8 -*-
"""v3856 - NO BACKUP JARGON UNDER TITLES. Elad (t1211u) asked for plain words: 'rides 💾 Backup & Share' is dev-speak. The Runewords subtitle ends at what is left, and a saved build just says Saved.

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
  "bible.html",
  "rides 💾 Backup &amp; Share",
  0
 ],
 [
  "bible.html",
  "see exactly what's left</p>",
  1
 ],
 [
  "bible.html",
  "'Saved')",
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
  "why": "the Runewords subtitle gets its jargon back",
  "file": "bible.html",
  "find": "see exactly what's left</p>",
  "replace": "see exactly what's left · rides 💾 Backup &amp; Share</p>",
  "matches": 1
 }
]

if __name__ == "__main__":
    unittest.main()
