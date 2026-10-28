# -*- coding: utf-8 -*-
"""REG-2069 - THE BOSS-NAV TIER MULTIPLIER NAMES THE DIFFICULTY IT WAS COMPUTED FOR.

#231 second eye on v43 (51774a21), re-measured at HEAD 2026-10-08: renderBossNav (and, swept, renderBossCards' tier heads) paint
a tier multiplier from playerMult(id, 'hell', players) under a title "drop-quantity multiplier at /players N" with no difficulty.
the /players factor differs by difficulty (REG-2953, silospen's own PLAYER_F: PRIME EVILS x1.188 on Hell vs x1.194 on
Normal at /players 3), so a number computed for Hell must say Hell. The law reads the difficulty the computation ASKS for and requires the title to
name that same difficulty - change one without the other and it goes red.
"""
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

PAGE = os.path.join(os.path.dirname(HERE), "bible.html")
# every surface that paints a /players tier multiplier: (function start, the multiplier span's class)
SITES = [("function renderBossNav() {\n", "boss-nav-group-mult"), ("function renderBossCards() {\n", "tier-mult")]
NAMES = {"hell": "Hell", "nm": "Nightmare", "norm": "Normal"}


def _src():
    with open(PAGE, encoding="utf-8") as f:
        return f.read()


def _body(s, start):
    if s.count(start) != 1:
        raise AssertionError("%r matched %d times - re-point this law" % (start.strip(), s.count(start)))
    i = s.index(start)
    return s[i:s.index("\n}\n", i)]


class ATierMultiplierNamesItsDifficulty(unittest.TestCase):

    def test_each_title_names_the_difficulty_its_multiplier_was_computed_for(self):
        s = _src()
        for start, cls in SITES:
            b = _body(s, start)
            diffs = set(re.findall(r"playerMult\(id, '(\w+)', players\)", b))
            self.assertEqual(len(diffs), 1, "premise: %s computes its tier multiplier for one difficulty: %r" % (cls, diffs))
            d = diffs.pop()
            self.assertIn(d, NAMES, "an unknown difficulty key %r" % d)
            titles = [t for t in re.findall(r'class="%s" title="([^"]*)"' % re.escape(cls), b)
                      if "drop-quantity" in t]          # the WORLD EVENT span shares the class and is not /players scaled
            self.assertEqual(len(titles), 1, "premise: one %s title in its function: %r" % (cls, titles))
            self.assertIn(NAMES[d] + " drop-quantity multiplier", titles[0],
                          "%s is computed for %s and its title does not say so: %r" % (cls, NAMES[d], titles[0]))

    def test_no_multiplier_title_anywhere_omits_its_difficulty(self):
        pre = re.findall(r'title="([^"]*?)drop-quantity multiplier at /players', _src())
        self.assertGreaterEqual(len(pre), len(SITES), "premise: the multiplier titles are on the page: %r" % pre)
        for p in pre:
            self.assertIn(p.strip(), NAMES.values(), "a multiplier title names no difficulty: %r" % p)


RED_PROOF = [
    {"why": "REG-2069 - the boss-nav tier multiplier's title stops naming the difficulty it was computed for",
     "file": "bible.html",
     "find": 'class="boss-nav-group-mult" title="Hell drop-quantity multiplier at /players ${players}"',
     "replace": 'class="boss-nav-group-mult" title="drop-quantity multiplier at /players ${players}"',
     "matches": 1},
    {"why": "REG-2069 - the boss-card tier head's multiplier title stops naming its difficulty",
     "file": "bible.html",
     "find": 'class="tier-mult" title="Hell drop-quantity multiplier at /players ${players}"',
     "replace": 'class="tier-mult" title="drop-quantity multiplier at /players ${players}"',
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
