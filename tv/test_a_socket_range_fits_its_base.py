# -*- coding: utf-8 -*-
"""GrokBot #230 (v3838): the builder's Aldur's Rhythm read 'Socketed (2-5)' - a Jagged Star holds at most 3. The builder's
set and unique rows (bible.html cb-db) carry a socket range; two rows asked more than their base can hold: Aldur's Rhythm
(Jagged Star, max 3) 2-5 and Heaven's Light (Mighty Scepter, max 2) 1-3. The game caps a socket roll at the base, so the
range is now 2-3 and 1-2. This law reads every row's sock range against the base's maxSockets in the same page.

RED_PROOF below: each one, applied, turns this law red."""
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable; enable()
ROOT = os.path.join(HERE, "..")


def _read(p):
    return open(os.path.join(ROOT, p), encoding="utf-8").read()


def over(src):
    ms = dict(re.findall(r'"([^"]+)":\{"tier":"[a-z]+","maxSockets":(\d+)', src))
    code = {}
    for n, c in re.findall(r'"([^"]+)":"([0-9a-z]{3})"', src):
        code.setdefault(c, n)
    bad, seen = [], 0
    for m in re.finditer(r'\["([^"]+)","[^"]*",\d+,"([0-9a-z]{3})"[^\n]*?\["sock","",(\d+),(\d+)\]', src):
        n, c, a, b = m.groups()
        mx = ms.get(code.get(c))
        if mx is None:
            continue
        seen += 1
        if int(b) > int(mx) or int(a) > int(b):
            bad.append("%s %s-%s on %s (max %s)" % (n, a, b, code.get(c), mx))
    return bad, seen


CHECKS = [
 ["bible.html", '["manasteal","",5,5],["sock","",2,3]]', 1],
]


class TheLawHolds(unittest.TestCase):
    def test_each_line_is_where_it_should_be(self):
        for f, needle, n in CHECKS:
            self.assertEqual(_read(f).count(needle), n, "%s: %r should appear %d time(s)" % (f, needle, n))

    def test_no_socket_range_passes_its_base(self):
        bad, seen = over(_read("bible.html"))
        self.assertGreaterEqual(seen, 15, "the rows were found and joined to their bases")
        self.assertEqual(bad, [], "a socket range asks more than its base holds")


class TheProofsNameOnePlace(unittest.TestCase):
    def test_each_find_matches_once(self):
        for p in RED_PROOF:
            self.assertEqual(_read(p["file"]).count(p["find"]), p["matches"], p["why"])

    def test_each_proof_turns_a_check_red(self):
        for p in RED_PROOF:
            after = _read(p["file"]).replace(p["find"], p["replace"])
            red = any(f == p["file"] and after.count(nd) != n for f, nd, n in CHECKS) or bool(over(after)[0])
            self.assertTrue(red, "this proof would not turn the law red: " + p["why"])


RED_PROOF = [
 {"file": "bible.html", "find": '["manasteal","",5,5],["sock","",2,3]]', "replace": '["manasteal","",5,5],["sock","",2,5]]',
  "matches": 1, "why": "Aldur's Rhythm reads Socketed (2-5) again"},
 {"file": "bible.html", "find": '["crush","",33,33],["sock","",1,2]', "replace": '["crush","",33,33],["sock","",1,3]', "matches": 1,
  "why": "Heaven's Light asks 3 sockets of a 2-socket scepter again"},
]

if __name__ == "__main__":
    unittest.main()
