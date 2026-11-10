# -*- coding: utf-8 -*-
"""REG-3630 — the Fleet lamp's ? is a third button on a nowrap rail head, and at 901 it
must wrap with the refresh control instead of being cut off by .rail overflow-x:hidden.

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
  "tv/control_ui.html",
  "@media (max-width: 1279px) { .fleet-head { flex-wrap: wrap; row-gap: 3px; min-width: 0; } }",
  1
 ],
 [
  "tv/control_ui.html",
  "  .fleet-head-tools { display: inline-flex; align-items: center; gap: inherit; margin-left: auto; flex: none; }",
  1
 ],
 [
  "tv/control_ui.html",
  '<span class="fleet-head-tools"><button class="util-btn fleet-refresh"',
  1
 ],
]


class TheLawHolds(unittest.TestCase):
    def test_each_line_is_where_it_should_be(self):
        for f, needle, n in CHECKS:
            self.assertEqual(_read(f).count(needle), n, "%s: %r should appear %d time(s)" % (f, needle, n))

    def test_the_nowrap_title_law_is_still_there(self):
        # REG-3630 adds wrap for the tools; it must not delete the title nowrap that
        # keeps THE FLEET on one line at 1024 (test_the_rail_titles_hold_one_line).
        src = _read("tv/control_ui.html")
        self.assertEqual(src.count(
            "@media (max-width: 1279px) { .fleet-head { white-space: nowrap; letter-spacing: .04em; gap: 6px; } }"
        ), 1)


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
  "file": "tv/control_ui.html",
  "find": "@media (max-width: 1279px) { .fleet-head { flex-wrap: wrap; row-gap: 3px; min-width: 0; } }",
  "replace": "@media (max-width: 1279px) { .fleet-head { row-gap: 3px; min-width: 0; } }",
  "matches": 1,
  "why": "without flex-wrap the lamp ? is cut off by the rail at 901"
 },
 {
  "file": "tv/control_ui.html",
  "find": '<span class="fleet-head-tools"><button class="util-btn fleet-refresh"',
  "replace": '<button class="util-btn fleet-refresh"',
  "matches": 1,
  "why": "without the tools group, ↻ stays on line 1 and the ? wraps alone (or still clips)"
 },
]

if __name__ == "__main__":
    unittest.main()
