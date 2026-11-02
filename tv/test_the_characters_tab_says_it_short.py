# -*- coding: utf-8 -*-
"""v3855 item C - THE CHARACTERS TAB SAYS IT SHORT (Elad, 2026-11-02: make the copy UX-friendly and human).

The two header lines (what the room is, where it is kept) are one line: "Automatically syncs your items to
characters". The in-game section's bar ladder (WATCHED -> PROVEN at 10 -> HARDENED at 20) rides the section title's
hover. Empty states are short words: "No gear seen yet", "Wearing · 3 of 10 slots", "Slot unknown:", "No characters
seen yet", "Level 1 · probably mules · N"; their long explanations ride a hover. "this build says 88" stays: it is said
only when the build's level differs from the one the game showed. RED_PROOF below.
"""
import os
import unittest
import sys as _sys; _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from console_safe import enable; enable()

HERE = os.path.dirname(os.path.abspath(__file__))
BIBLE = os.path.join(HERE, "..", "bible.html")

GONE = (
    "Your characters in game, learned from this console's reels",
    "Kept on this device, per account (Main and Ladder hold their own)",
    "each proves itself the way the Vault\\'s filings do",
    "Nothing seen on ' + ",
    " slots so far</div>",
    "Worn, slot not told yet",
    "None yet. A character joins here",
    " wears is UNKNOWN here",
)
SAID = (
    '<div class="chx-sub" id="chars-what">Automatically syncs your items to characters</div>',
    ">No gear seen yet</div>",
    ">Wearing · ' + seen + ' of '",
    "Slot unknown: ",
    ">No characters seen yet</span>",
    "Level 1 · probably mules · ",
    '<span class="chx-sec-t" title="\' + esc(ladder) + \'">',
)


def _page():
    return open(BIBLE, encoding="utf-8").read()


class TheLongWordsAreGone(unittest.TestCase):
    def test_absent(self):
        s = _page()
        for w in GONE:
            self.assertNotIn(w, s, "the Characters tab still says %r" % w)

    def test_one_header_line(self):
        s = _page()
        head = s[s.index('<div class="tab-content" id="tab-chars">'):s.index('<style id="chars-tab-css">')]
        self.assertNotIn("chx-meta", head, "the kept-on-this-device line is back")
        self.assertEqual(head.count('class="chx-sub"'), 1)


class TheShortWordsAreSaid(unittest.TestCase):
    def test_present(self):
        s = _page()
        for w in SAID:
            self.assertIn(w, s, "the Characters tab does not say %r" % w)


class TheProofsNameOnePlace(unittest.TestCase):
    def test_each_find_matches_once(self):
        for p in RED_PROOF:
            s = open(os.path.join(HERE, "..", p["file"]), encoding="utf-8").read()
            self.assertEqual(s.count(p["find"]), p["matches"], p["why"])


RED_PROOF = [
    {"why": "the long subtitle comes back",
     "file": "bible.html",
     "find": '<div class="chx-sub" id="chars-what">Automatically syncs your items to characters</div>',
     "replace": '<div class="chx-sub" id="chars-what">Your characters in game, learned from this console\'s reels</div>',
     "matches": 1},
    {"why": "the bar ladder is printed under the section title again",
     "file": "bible.html",
     "find": '<span class="chx-sec-t" title="\' + esc(ladder) + \'">⚔️ In-game characters</span></div>',
     "replace": '<span class="chx-sec-t">⚔️ In-game characters</span><span class="chx-sec-s">each proves itself the way the Vault\\\'s filings do: \' + ladder + \'</span></div>',
     "matches": 1},
    {"why": "an empty gear list says a long sentence",
     "file": "bible.html",
     "find": ">No gear seen yet</div></div>';",
     "replace": ">Nothing seen on ' + nm + ' yet</div></div>';",
     "matches": 1},
    {"why": "the slot count says 'so far'",
     "file": "bible.html",
     "find": "      + (G.g.slots || []).length + ' slots</div>",
     "replace": "      + (G.g.slots || []).length + ' slots so far</div>",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main()
