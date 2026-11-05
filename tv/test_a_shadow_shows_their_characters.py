# -*- coding: utf-8 -*-
"""v3856 - A SHADOW SHOWS THEIR CHARACTERS. A shadow console's Characters tab drew no in-game characters: _cbLearnedFetch returned early and _cbSections answered 'their reels stay on their console'. The shadow shim already answers /api/chars_learned from the owner's own upload (GET only, never this console), so the room now asks it and draws the same plain worn-gear cards.

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
  "    if (document.documentElement.classList.contains('tvd-shadow')) return _cbLearnedQuiet(then);\n",
  1
 ],
 [
  "bible.html",
  "their reels stay on their console, so in-game characters are not read here",
  0
 ],
 [
  "bible.html",
  "var hit = /^\\/api\\/(chars_learned|main_locks|saves)$/.exec(path);",
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
  "why": "the shadow stops asking for their characters",
  "file": "bible.html",
  "find": "tvd-shadow')) return _cbLearnedQuiet(then);",
  "replace": "tvd-shadow')) return;",
  "matches": 1
 },
 {
  "why": "the shim stops serving their chars_learned",
  "file": "bible.html",
  "find": "var hit = /^\\/api\\/(chars_learned|main_locks|saves)$/.exec(path);",
  "replace": "var hit = /^\\/api\\/(main_locks|saves)$/.exec(path);",
  "matches": 1
 }
]

if __name__ == "__main__":
    unittest.main()
