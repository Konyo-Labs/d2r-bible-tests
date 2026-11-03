# -*- coding: utf-8 -*-
"""Every d2jsp desk key forks with the profile and moves into a guest world, so main and ladder never share a tag or topic.

RED_PROOF below: each one, applied, turns this law red."""
import json, os, shutil, subprocess
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
  "bible.html",
  "  'd2r_d2jsp_tags',\n",
  1
 ],
 [
  "bible.html",
  "'d2r_d2jsp_mods', 'd2r_d2jsp_tags'];",
  1
 ]
]


class TheLawHolds(unittest.TestCase):
    def test_each_line_is_where_it_should_be(self):
        for f, needle, n in CHECKS:
            self.assertEqual(_read(f).count(needle), n, "%s: %r should appear %d time(s)" % (f, needle, n))

    def test_every_desk_key_forks_with_the_profile(self):
        import re
        src = open(os.path.join(ROOT, "bible.html"), encoding="utf-8").read()
        i = src.index("window._LP_FORKED = new Set([")
        forked = set(re.findall(r"'(d2r_[A-Za-z0-9_]+)'", src[i:src.index("]);", i)]))
        j = src.index("var D2JSP_FORKED_KEYS = [")
        desk = set(re.findall(r"'(d2r_[A-Za-z0-9_]+)'", src[j:src.index("];", j)]))
        used = set(re.findall(r"['\"](d2r_d2jsp_[A-Za-z0-9_]+)['\"]", src))
        self.assertGreater(len(used), 5, "PREMISE: the desk's keys did not read")
        self.assertEqual(sorted(used - forked), [], "a d2jsp desk key is shared by main and ladder")
        self.assertEqual(sorted(used - desk), [], "a d2jsp desk key is not copied into a guest world's own namespace")


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
  "why": "the tags go back to one shared bare key",
  "file": "bible.html",
  "find": "  'd2r_d2jsp_tags',\n",
  "replace": "",
  "matches": 1
 },
 {
  "why": "a guest world stops copying its tags",
  "file": "bible.html",
  "find": "'d2r_d2jsp_mods', 'd2r_d2jsp_tags'];",
  "replace": "'d2r_d2jsp_mods'];",
  "matches": 1
 }
]

if __name__ == "__main__":
    unittest.main()
