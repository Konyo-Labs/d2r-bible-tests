# -*- coding: utf-8 -*-
"""v3856 (#230 6507907850 nit) - A VERSION CARD'S DATE WEARS NO ZONE. The history card head read '2026-10-29 IDT': a bare date with a zone label and no time. It reads the date alone.

RED_PROOF below: each one, applied, turns this law red."""
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")


def _read(p):
    return open(os.path.join(ROOT, p), encoding="utf-8").read()


CHECKS = [
 [
  "tv/control_ui.html",
  "'<span class=\"hist-date\">' + histEsc(e.date) + '</span></div><ul>'",
  1
 ],
 [
  "tv/control_ui.html",
  "histEsc(e.date) + ' IDT",
  0
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
  "why": "the zone label comes back on a bare date",
  "file": "tv/control_ui.html",
  "find": "histEsc(e.date) + '</span></div><ul>'",
  "replace": "histEsc(e.date) + ' IDT</span></div><ul>'",
  "matches": 1
 }
]

if __name__ == "__main__":
    unittest.main()
