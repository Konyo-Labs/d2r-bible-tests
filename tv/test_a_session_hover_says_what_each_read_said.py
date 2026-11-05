# -*- coding: utf-8 -*-
"""v3856 - A SESSION'S HOVER SAYS WHAT EACH READ SAID. The shadow session row stays answer-only; its hover now says the character picked at login, the character panel and the class the avatar looks like, beside the game series. attribute_character carries a per-source 'seen' list; never a password.

RED_PROOF below: each one, applied, turns this law red."""
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")


def _read(p):
    return open(os.path.join(ROOT, p), encoding="utf-8").read()


CHECKS = [
 [
  "tv/read_identity.py",
  "\"seen\": seen[:6], \"seenN\": len(seen)}",
  1
 ],
 [
  "tv/control_ui.html",
  "? ' \u00b7 +' + (ch.seenN - ch.seen.length) + ' more read(s)' : ''));",
  1
 ],
 [
  "tv/control_ui.html",
  "var _SEEN_SAY = { 'select-screen': 'picked at login', 'char-panel': 'character panel', 'avatar': 'avatar looks like' };",
  1
 ],
 [
  "tv/control_ui.html",
  "if (_seen.length) whyBits.push(",
  1
 ]
]


class TheLawHolds(unittest.TestCase):
    def test_each_line_is_where_it_should_be(self):
        for f, needle, n in CHECKS:
            self.assertEqual(_read(f).count(needle), n, "%s: %r should appear %d time(s)" % (f, needle, n))


class SevenReadsAreNotSix(unittest.TestCase):
    """v3866 (the #231 eye on v3858) - the record keeps 6 reads for the hover; the 7th and later were dropped with no word"""

    def test_the_record_counts_every_read_it_does_not_keep(self):
        import sys
        sys.path.insert(0, HERE)
        import read_identity as RI
        sigs = [{"source": "char-panel", "name": "Konyo", "cls": "Sorceress", "level": 80 + i} for i in range(8)]
        got = RI.attribute_character(sigs)
        self.assertEqual((len(got["seen"]), got["seenN"]), (6, 8), got)


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
  "why": "the record stops carrying what each read said",
  "file": "tv/read_identity.py",
  "find": "\"seen\": seen[:6], \"seenN\": len(seen)}",
  "replace": "}",
  "matches": 1
 },
 {
  "why": "v3866 - the hover drops reads past the six kept with no word",
  "file": "tv/control_ui.html",
  "find": "? ' \u00b7 +' + (ch.seenN - ch.seen.length) + ' more read(s)' : ''));",
  "replace": "? '' : ''));",
  "matches": 1
 },
 {
  "why": "the hover stops saying it",
  "file": "tv/control_ui.html",
  "find": "if (_seen.length) whyBits.push(",
  "replace": "if (false) whyBits.push(",
  "matches": 1
 }
]

if __name__ == "__main__":
    unittest.main()
