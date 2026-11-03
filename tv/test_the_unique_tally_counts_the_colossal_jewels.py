# -*- coding: utf-8 -*-
"""v3857 item 16 (#230, Elad 2026-11-03): the unique tally is 403 - the 397 hunt cards plus the six colossal jewels
(Defender's Bile .. Guardian's Light, code cjw). The quest items stay off. funiScan pins chronTotal at 403, its found
counts a ticked colossal jewel, and the All-missing tile and the still-missing count read chronTotal - found without adding
the open jewels a second time; the named-card line and the still-dark band take the six back out of the pin.

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


# [file, needle, how many times it must appear]
CHECKS = [
 [
  "bible.html",
  "lowTotal:lowTotal, chronTotal:403, colTotal:_colRowsT.length, colFound:colFound };",
  1
 ],
 [
  "bible.html",
  "chronTotal:397",
  0
 ],
 [
  "bible.html",
  "    _colRowsT.forEach(function(x){ if(_ownedHas(own,x.n)) colFound++; });\n    found+=colFound;\n",
  1
 ],
 [
  "bible.html",
  "var _huntMiss = s.chronTotal ? (s.chronTotal-s.found) : (s.missing.length + _colossalStillOpen(_ownedNames()));",
  1
 ],
 [
  "bible.html",
  "var _uniLeft = (s.chronTotal || 0) - s.found;",
  1
 ],
 [
  "bible.html",
  "var _namedDark = (s.chronTotal - (s.colTotal||0) - s.total);",
  1
 ],
 [
  "bible.html",
  "var _darkN=(s.chronTotal||0)-(s.colTotal||0)-s.total;",
  1
 ],
 [
  "bible.html",
  "named cards: <b>'+(s.found-(s.colFound||0))+' / '+s.total+'</b> ticked",
  1
 ],
 [
  "bible.html",
  "      if (_CHRON_QUESTS.indexOf(n) >= 0) return;\n",
  1
 ],
 [
  "bible.html",
  "    return [\"Defender's Bile\",\"Guardian's Thunder\",\"Protector's Frost\",\"Defender's Fire\",\"Protector's Stone\",\"Guardian's Light\"]",
  1
 ]
]


def red_after(file, text):
    return any(f == file and text.count(nd) != n for f, nd, n in CHECKS)


class TheLawHolds(unittest.TestCase):
    def test_each_line_is_where_it_should_be(self):
        for f, needle, n in CHECKS:
            self.assertEqual(_read(f).count(needle), n, "%s: %r should appear %d time(s)" % (f, needle, n))

    def test_the_pin_is_the_cards_plus_the_jewels(self):
        import route_totals as RT
        self.assertEqual(RT.file_pin(), 397 + 6, "the tally is the 397 hunt cards plus the 6 colossal jewels")
        self.assertEqual(len(RT.quest_names() or []), 6, "the six quest items are still named, and kept off")


class TheProofsNameOnePlace(unittest.TestCase):
    def test_each_find_matches_once(self):
        for p in RED_PROOF:
            self.assertEqual(_read(p["file"]).count(p["find"]), p["matches"], p["why"])

    def test_each_proof_turns_a_check_red(self):
        for p in RED_PROOF:
            after = _read(p["file"]).replace(p["find"], p["replace"])
            self.assertTrue(red_after(p["file"], after), "this proof would not turn the law red: " + p["why"])


RED_PROOF = [
 {
  "file": "bible.html",
  "find": "lowTotal:lowTotal, chronTotal:403,",
  "replace": "lowTotal:lowTotal, chronTotal:397,",
  "matches": 1,
  "why": "the pin drops the six colossal jewels again (397)"
 },
 {
  "file": "bible.html",
  "find": "    found+=colFound;\n",
  "replace": "\n",
  "matches": 1,
  "why": "a ticked colossal jewel stops counting as found"
 },
 {
  "file": "bible.html",
  "find": "var _uniLeft = (s.chronTotal || 0) - s.found;",
  "replace": "var _uniLeft = (s.chronTotal || 0) - s.found + _colossalStillOpen(_ownMon);",
  "matches": 1,
  "why": "still missing counts an open jewel twice"
 },
 {
  "file": "bible.html",
  "find": "var _darkN=(s.chronTotal||0)-(s.colTotal||0)-s.total;",
  "replace": "var _darkN=(s.chronTotal||0)-s.total;",
  "matches": 1,
  "why": "the six jewels are painted as still-dark chronicle rows"
 },
 {
  "file": "bible.html",
  "find": "      if (_CHRON_QUESTS.indexOf(n) >= 0) return;\n",
  "replace": "",
  "matches": 1,
  "why": "the quest items come back onto the tally"
 }
]

if __name__ == "__main__":
    unittest.main()
