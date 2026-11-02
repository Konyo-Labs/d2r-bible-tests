# -*- coding: utf-8 -*-
"""v3855 item D - YOUR BUILDS SIT ON TOP (Elad, 2026-11-02).

The Characters room reads header -> Your builds (+ New character is its first card: dashed gold, a big +) -> In-game
characters -> the collapsed data sections (names read, lobby checks), which close the in-game section. The header's own
+ New character button is a hidden holder of the store's read state only. Delete is untouched. RED_PROOF below.
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
BIBLE = os.path.join(HERE, "..", "bible.html")


def _sections_fn():
    s = open(BIBLE, encoding="utf-8").read()
    i = s.index("  function _sections(all, order, mainId){")
    return s[i:s.index("\n  }\n", i)]


class TheRoomReadsInOrder(unittest.TestCase):
    def test_builds_then_in_game_then_the_dumps(self):
        f = _sections_fn()
        b, g = f.index('data-sec="sim"'), f.index('data-sec="ingame"')
        self.assertLess(b, g, "Your builds are not above the in-game characters")
        self.assertLess(g, f.index("_surfaceWitnessHtml()", g))
        self.assertLess(f.index("_surfaceWitnessHtml()", g), f.index("_lobbySizeHtml()", g))
        self.assertEqual(f.count("data-sec="), 2)

    def test_the_new_tile_is_the_first_card_of_your_builds(self):
        f = _sections_fn()
        sec = f[f.index('data-sec="sim"'):f.index('data-sec="ingame"')]
        self.assertIn("Builds you make by hand to try things out", sec)
        self.assertIn("'<div class=\"chx-sec-list\">' + newTile + sim + '</div></section>'", sec)
        self.assertIn('class="chx-newtile" data-act="new" onclick="window._charsNew()"', f)

    def test_the_header_holds_no_visible_new_button(self):
        s = open(BIBLE, encoding="utf-8").read()
        self.assertRegex(s, r'<button[^>]*id="chars-new"[^>]*\shidden>')


class TheProofsNameOnePlace(unittest.TestCase):
    def test_each_find_matches_once(self):
        for p in RED_PROOF:
            s = open(os.path.join(HERE, "..", p["file"]), encoding="utf-8").read()
            self.assertEqual(s.count(p["find"]), p["matches"], p["why"])


RED_PROOF = [
    {"why": "the New tile drops out of Your builds",
     "file": "bible.html",
     "find": "      +   '<div class=\"chx-sec-list\">' + newTile + sim + '</div></section>'\n",
     "replace": "      +   '<div class=\"chx-sec-list\">' + sim + '</div></section>'\n",
     "matches": 1},
    {"why": "the header's New button shows again (two New buttons)",
     "file": "bible.html",
     "find": 'onclick="window._charsNew()" hidden>+ New character</button>',
     "replace": 'onclick="window._charsNew()">+ New character</button>',
     "matches": 1},
    {"why": "Your builds lose their subtitle",
     "file": "bible.html",
     "find": "<span class=\"chx-sec-s\">Builds you make by hand to try things out</span>",
     "replace": "",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main()
