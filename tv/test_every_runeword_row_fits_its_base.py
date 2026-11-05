# -*- coding: utf-8 -*-
"""v3864 (GrokBot Batch B 7, #230 6655906382; the Grok CLI re-read it, 6655933519) - EVERY RUNEWORD ROW'S BASE CAN HOLD ITS RUNES.

bible.html's RUNEWORDS row for Call to Arms read base "5-sock weapon/wand": a wand holds at most 2 sockets (every wand base
in BASE_DB is 1 or 2), so the row named a base no CTA can ever be made in. Now: every row (except the one reference unique,
"(unique, not RW)") says "N-sock ..." with N equal to its rune count, and a row that names a wand asks for at most 2 runes.
The 101 rows are 99 runewords + Spirit's two bases + Death's Web for reference - counted here so a new extra row is seen.
RED_PROOF below.
"""
import io
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")
WAND_MAX = 2


def rows():
    s = io.open(BIBLE, encoding="utf-8").read()
    i = s.index("const RUNEWORDS = [")
    j = s.index("\n];", i)
    return re.findall(r'\{n:"([^"]+)", runes:"([^"]*)", base:"([^"]*)"', s[i:j])


class EveryRunewordRowFitsItsBase(unittest.TestCase):

    def test_the_rows_are_the_runewords_plus_the_two_known_extras(self):
        r = rows()
        self.assertGreater(len(r), 90, "PREMISE: the RUNEWORDS rows were not read")
        ref = [n for n, ru, b in r if "not RW" in ru]
        self.assertEqual(ref, ["Death's Web"], "a reference row that is not a runeword: %r" % ref)
        spirit = [n for n, ru, b in r if n.startswith("Spirit")]
        self.assertEqual(len(spirit), 2, "PREMISE: Spirit's two bases moved: %r" % spirit)
        self.assertEqual(len(r), 101, "a new extra row joined the runeword list (99 + Spirit's second base + Death's Web)")

    def test_each_row_holds_its_own_rune_count(self):
        bad = []
        for n, ru, b in rows():
            if "not RW" in ru:
                continue
            k = len([x for x in ru.split("+") if x.strip()])
            m = re.match(r"(\d+)-sock", b)
            if not m or int(m.group(1)) != k:
                bad.append((n, ru, b))
        self.assertEqual(bad, [], "a row's socket count is not its rune count: %r" % bad[:5])

    def test_no_row_asks_a_wand_for_more_than_two_sockets(self):
        bad = [(n, b) for n, ru, b in rows() if re.search(r"\bwand\b", b, re.I) and int(re.match(r"(\d+)", b).group(1)) > WAND_MAX]
        self.assertEqual(bad, [], "a runeword row names a wand for more runes than a wand can hold: %r" % bad)


RED_PROOF = [
    {"why": "v3864 - Call to Arms names a 5-socket wand again",
     "file": "bible.html",
     "find": 'base:"5-sock weapon", notes:"BO + Battle Command',
     "replace": 'base:"5-sock weapon/wand", notes:"BO + Battle Command',
     "matches": 1},
    {"why": "v3864 - a row's socket count drifts from its runes",
     "file": "bible.html",
     "find": '{n:"White", runes:"Dol + Io", base:"2-sock Wand"',
     "replace": '{n:"White", runes:"Dol + Io", base:"3-sock Wand"',
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
