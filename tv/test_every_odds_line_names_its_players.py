# -*- coding: utf-8 -*-
"""REG-3322 (#43, GrokBot 6698868304 on 11-07: "Calculator > Harlequin, NM TZ Mephisto: 1:1,902 '@ base odds (MF not set)'
... Quick wins has the same row ... Neither surface names the player count") - EVERY ODDS LINE NAMES BOTH THINGS ITS 1:N
WAS COMPUTED AT: the MF and the /players.

The drop model moves with /players (playerMult, the P# slider on the dock), but the odds lines said only the MF, so a 1:N
read at /players 1 looked the same as one read at /players 8. window._oddsAtSay() says both (the MF in _mfAtSay's
unchanged words, then "/players N"), and every odds line asks it - or prints /players itself beside _mfAtSay.

Held here: the seam's words, driven in node at an unset MF / players 1 and at 300% MF / players 3; the class - no line of
the page states its MF through _mfAtSay with no /players beside it; and Quick wins' header states it for its list.
RED_PROOF below.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
NODE = shutil.which("node") or shutil.which("nodejs")


def _page():
    with io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8") as fh:
        return fh.read()


class EveryOddsLineNamesItsPlayers(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.src = _page()

    def test_the_seam_says_the_mf_and_the_players(self):
        if not NODE:
            self.skipTest("no node - the seam is not driven here (UNMEASURED)")
        mf_at = re.search(r"window\._mfAtSay = function\(\)\{[^\n]*\};", self.src).group(0)
        odds_at = re.search(r"window\._oddsAtSay = function\(\)\{[^\n]*\};", self.src).group(0)
        prog = ("var window = {}, out = [];\n"
                "function run(chosen, m, p){ var _mfChosen = chosen, mf = m, players = p;\n"
                + mf_at + "\n" + odds_at + "\n return window._oddsAtSay(); }\n"
                "out.push(run(false, 0, 1)); out.push(run(true, 300, 3));\n"
                "process.stdout.write(JSON.stringify(out));")
        r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-1500:])
        self.assertEqual(json.loads(r.stdout), ["base odds (MF not set) · /players 1", "300% MF · /players 3"])

    def test_no_odds_line_states_its_mf_without_its_players(self):
        lines = [ln for ln in self.src.split("\n") if "window._mfAtSay()}" in ln]
        bare = [ln.strip()[:140] for ln in lines if "/players" not in ln]
        self.assertEqual(bare, [], "an odds line states the MF and not the /players it was computed at:\n  " + "\n  ".join(bare))
        self.assertGreaterEqual(self.src.count("window._oddsAtSay()"), 8, "PREMISE: too few odds lines ask the seam")

    def test_quick_wins_states_its_odds_for_the_list(self):
        h = self.src.index('<div class="forge-sec-h">⚡ Quick wins')
        self.assertIn("odds @ '+esc(window._oddsAtSay())+'", self.src[h:self.src.index("\n", h)])


RED_PROOF = [
    {"why": "REG-3322 - the odds lines say the MF and never the /players they were computed at",
     "file": "bible.html",
     "find": "window._oddsAtSay = function(){ return window._mfAtSay() + ' · /players ' + (typeof players !== 'undefined' && players > 0 ? players : 1); };",
     "replace": "window._oddsAtSay = function(){ return window._mfAtSay(); };",
     "matches": 1, "needs": "node"},
    {"why": "REG-3322 - the item card's top sources state their MF only",
     "file": "bible.html",
     "find": "Top 6 Sources @ ${window._oddsAtSay()} (click to focus boss)",
     "replace": "Top 6 Sources @ ${window._mfAtSay()} (click to focus boss)",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
