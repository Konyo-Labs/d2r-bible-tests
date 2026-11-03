# -*- coding: utf-8 -*-
"""#13: the Vault planner's plate and its Done stay drawn through every choice (base, quality, edit). _cbModal re-drew the host with _cbPickHtml() only and dropped the foot.

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
  "else m.innerHTML = _cbPickHtml() + ((st.pick && st.pick.host === 'mule' && st.host && typeof window._cbHostFoot === 'function') ? window._cbHostFoot() : '');",
  1
 ],
 [
  "bible.html",
  "    var foot = window._cbHostFoot();\n",
  1
 ],
 [
  "bible.html",
  "window._cbHostFoot = function(){",
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
  "why": "re-draw the picker without the foot and Done vanishes after a choice",
  "file": "bible.html",
  "find": "else m.innerHTML = _cbPickHtml() + ((st.pick",
  "replace": "else m.innerHTML = _cbPickHtml(); void ((st.pick",
  "matches": 1
 },
 {
  "why": "a second foot builder in the host drifts from the re-draw",
  "file": "bible.html",
  "find": "    var foot = window._cbHostFoot();\n",
  "replace": "    var foot = '';\n",
  "matches": 1
 }
]

if __name__ == "__main__":
    unittest.main()
