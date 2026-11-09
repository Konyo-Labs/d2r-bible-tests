# -*- coding: utf-8 -*-
"""A theatre chronicle row wraps its note instead of ellipsing the count, and the whole-page clip floors are ratcheted to what is now measured.

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
  ".tf-row.tf-chron .tf-t { white-space: normal; overflow: visible; text-overflow: clip; }",
  1
 ],
 [
  "tv/control_ui.html",
  ".tf-row.tf-chron .tf-chron-note { white-space: nowrap; }",
  1
 ],
 [
  "tv/render_check.py",
  "\"901x900\":   {\"clipped\": 0, \"broken\": None, \"zero\": 6}",
  1
 ],
 [
  "tv/render_check.py",
  "\"1440x1000\": {\"clipped\": 0, \"broken\": None, \"zero\": 6}",
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
  "why": "ellipse the chronicle title again",
  "file": "tv/control_ui.html",
  "find": ".tf-row.tf-chron .tf-t { white-space: normal; overflow: visible; text-overflow: clip; }",
  "replace": "",
  "matches": 1
 },
 {
  "why": "loosen the 901 floor",
  "file": "tv/render_check.py",
  "find": "\"901x900\":   {\"clipped\": 0,",
  "replace": "\"901x900\":   {\"clipped\": 5,",
  "matches": 1
 }
]

if __name__ == "__main__":
    unittest.main()
