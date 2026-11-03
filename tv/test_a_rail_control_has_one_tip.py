# -*- coding: utf-8 -*-
"""#220 (board half): the ?, nav and inbox rail controls draw one tip - their data-tip pseudo tip - and no longer also carry a title the prose lane borrowed into #arttip. Found and proven with a real-pointer sweep over 73 Vault and rail tip hosts.

RED_PROOF below: each one, applied, turns this law red."""
import os
import json, os, shutil, subprocess
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
  "title=\"Help &amp; guide\"",
  0
 ],
 [
  "bible.html",
  "title=\"Navigate\"",
  0
 ],
 [
  "bible.html",
  "title=\"Inbox — names the readers could not call on their own\"",
  0
 ],
 [
  "bible.html",
  "#220 (v3856) - A RAIL CONTROL HAS ONE TIP.",
  1
 ]
]


class TheLawHolds(unittest.TestCase):
    def test_each_line_is_where_it_should_be(self):
        for f, needle, n in CHECKS:
            self.assertEqual(_read(f).count(needle), n, "%s: %r should appear %d time(s)" % (f, needle, n))

    def test_no_pseudo_tip_carries_a_title(self):
        import re
        s = _read("bible.html")
        bad = []
        for m in re.finditer(r"<(?:button|span|a|div)\b[^>]*\bclass=\"[^\"]*\b(?:fab-tip|kbd-tip)\b[^\"]*\"[^>]*>", s):
            if re.search(r"\btitle=", m.group(0)):
                bad.append(m.group(0)[:90])
        for m in re.finditer(r"class=\"(?:help|nav|inbox)-fab[^\"]*fab-tip\"[\s\S]{0,400}?</button>", s):
            if "title=" in m.group(0).split("onclick")[0]:
                bad.append(m.group(0)[:90])
        self.assertEqual(bad, [], "a data-tip control also carries a title - two tips on one hover: %r" % bad)


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
  "why": "give the ? its title back",
  "file": "bible.html",
  "find": "classList.add('show')\">?</button>",
  "replace": "classList.add('show')\" title=\"Help &amp; guide\">?</button>",
  "matches": 1
 },
 {
  "why": "give the nav FAB its title back",
  "file": "bible.html",
  "find": "aria-label=\"Navigation menu\" onclick=",
  "replace": "aria-label=\"Navigation menu\" title=\"Navigate\" onclick=",
  "matches": 1
 }
]

if __name__ == "__main__":
    unittest.main()
