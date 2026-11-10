# -*- coding: utf-8 -*-
"""v3895 (#91, REG-3591) - THE ART MAP NAMES EACH ITEM ONCE.

D2IO_ART held 21 duplicate keys (set pieces mostly, plus Nihlathak and The
Summoner). In JavaScript the later assignment silently wins, so a first edit
changed a key that did not count (REG-3315 left this for #91). Every key now
appears once. Bloodwitch the Wild, Lord De Seis and Treehead WoodFist still
have no sourced sprite (noSpriteFound); that visual pass is the rest of #91.
RED_PROOF below.
"""
import os
import re
import sys
import unittest
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _enable  # noqa: E402
_enable()

BIBLE = os.path.join(HERE, "..", "bible.html")


def _pairs():
    with open(BIBLE, encoding="utf-8") as fh:
        src = fh.read()
    i = src.index("const D2IO_ART = {")
    chunk = src[i:src.index("\n};", i)]
    return re.findall(r'^\s*"([^"]+)":\s*"([^"]+)"', chunk, re.M)


class TheArtMapNamesEachItemOnce(unittest.TestCase):

    def test_no_name_is_written_twice(self):
        pairs = _pairs()
        keys = [k for k, _v in pairs]
        dups = sorted(k for k, n in Counter(keys).items() if n > 1)
        self.assertEqual(dups, [], "D2IO_ART repeats a name (the later silently wins): %s" % dups)
        self.assertGreaterEqual(len(keys), 500, "premise: the art map shrank too far (%d)" % len(keys))

    def test_the_three_leftover_monsters_are_not_split_across_two_files(self):
        """They still have no sprite; they must not quietly wear two different older pictures."""
        by = {}
        for k, v in _pairs():
            by.setdefault(k.lower(), set()).add(v)
        for name in ("Bloodwitch the Wild", "Lord De Seis", "Treehead WoodFist"):
            files = by.get(name.lower(), set())
            self.assertLessEqual(len(files), 1, "%s names two pictures: %s" % (name, files))


RED_PROOF = [
    {"why": "v3895 (#91, REG-3591) - Wilhelm's Pride is listed twice again (the later silently wins)",
     "file": "bible.html",
     "find": '  "Wilhelm\'s Pride": "art/wilhelmspride_graphic.png",\n',
     "replace": '  "Wilhelm\'s Pride": "art/wilhelmspride_graphic.png",\n'
                '  "Wilhelm\'s Pride": "art/wilhelmspride_graphic.png",\n',
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
