# -*- coding: utf-8 -*-
"""REG-3307 (v3875's GitHub round) - THE INSTALL CREST IS MEASURED BEFORE IT IS CALLED QUIET.

crest_loudness[0] came back BLIND on a Linux proof shard (its tamper paints the crest solid red and the gate stayed green)
while it was PROVEN on this Mac: tampered here the crest measures 95.0% against the help button's 75.7%. Two paths in the
gate's verdict made a green that had measured nothing about the crest:
  * a crest absent from the ranking (below the fold, under the 12x8 floor, hidden) read "the crest is not in the ranking,
    behind X - identity is quiet", whatever colour it was painted;
  * a crest TIED with the loudest element read green whenever the sort put the other element first.
So, held here without a browser (crest_loudness.verdict is the gate's whole decision; its pixels are GitHub's):
  * no crest in the ranking is UNKNOWN (exit 2), never green;
  * a crest as loud as the loudest is red, wherever the sort put it;
  * a quiet crest says its own share and the leader's, so a green can be read.
RED_PROOF below.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import console_safe  # noqa: E402,F401 - this law prints non-ASCII; a cp1255 console must not crash reporting it
import crest_loudness as C  # noqa: E402


class TheCrestIsMeasuredBeforeItIsCalledQuiet(unittest.TestCase):

    def test_a_crest_nobody_measured_is_unknown(self):
        code, lines = C.verdict([(0.757, ".help-btn"), (0.52, ".tab-ic-img")])
        self.assertEqual(code, 2, "a crest absent from the ranking was called quiet: %s" % lines)
        self.assertIn("never measured", " ".join(lines))

    def test_the_loudest_crest_is_red(self):
        code, _ = C.verdict([(0.95, "#bs-glyph"), (0.757, ".help-btn")])
        self.assertEqual(code, 1)

    def test_a_crest_tied_with_the_loudest_is_red_wherever_the_sort_put_it(self):
        code, lines = C.verdict([(0.95, ".some-badge"), (0.95, "#bs-glyph"), (0.5, ".help-btn")])
        self.assertEqual(code, 1, "a crest as loud as the loudest read green because it sorted second: %s" % lines)
        self.assertIn("tied with .some-badge", " ".join(lines))

    def test_a_quiet_crest_says_both_shares(self):
        code, lines = C.verdict([(0.757, ".help-btn"), (0.52, ".nc-n"), (0.179, "#bs-name")])
        self.assertEqual(code, 0)
        said = " ".join(lines)
        for part in ("#3", "#bs-name", "17.9%", ".help-btn", "75.7%"):
            self.assertIn(part, said)

    def test_the_gate_measures_its_own_empty_world(self):
        """A proof shard's browser gates share one Chrome and one file:// storage: ladder mode left on by an earlier gate
        draws a 92.9% gold ribbon over this page. The gate clears storage before it claims the board."""
        with open(os.path.join(HERE, "crest_loudness.py"), encoding="utf-8") as fh:
            src = fh.read()
        body = src[src.index("\ndef main():"):]
        claim = body.index("localStorage.setItem('d2r_ownerClaim','*')")
        setup = body[body.rindex("t.ev(", 0, claim):claim]
        self.assertIn("localStorage.clear();", setup, "the gate inherits whatever the gate before it left in storage")
        self.assertIn("sessionStorage.clear();", setup)
        # REG-3313 - the Mac owner's world on every venue: Linux is the 'windows' world, whose blue cousin ribbon
        # out-shouted a solid-red crest on GitHub (86.8% vs 88.7%)
        self.assertIn("localStorage.setItem('d2r_activeMachine','mac');", setup, "the gate measures whichever world the venue's platform picks")
        self.assertIn("localStorage.setItem('d2r_machineSource','user');", setup, "an 'auto' machine is re-detected from the platform")
        self.assertLess(claim, body.index('t.send("Page.reload")'), "the world is cleared after the page it measures loaded")

    def test_main_decides_through_verdict(self):
        """PREMISE: main() prints and returns verdict()'s answer - a second, inline decision would make this law about
        a function nobody calls."""
        with open(os.path.join(HERE, "crest_loudness.py"), encoding="utf-8") as fh:
            src = fh.read()
        body = src[src.index("\ndef main():"):]
        self.assertIn("code, lines = verdict(scored)", body)
        self.assertNotIn("if top in CREST", body, "main() decides the crest's verdict inline again")


RED_PROOF = [
    {"why": "REG-3313 - the crest gate measures whichever storage world the venue's platform picks (Linux: the cousin ribbon)",
     "file": "tv/crest_loudness.py",
     "find": "localStorage.setItem('d2r_activeMachine','mac');",
     "replace": "localStorage.setItem('d2r_activeMachine_unused','mac');",
     "matches": 1},
    {"why": "REG-3307 - the crest gate inherits the storage the gate before it left (ladder mode's ribbon)",
     "file": "tv/crest_loudness.py",
     "find": "t.ev(\"try{localStorage.clear();sessionStorage.clear();localStorage.setItem('d2r_activeMachine','mac');\"",
     "replace": "t.ev(\"try{localStorage.setItem('d2r_activeMachine','mac');\"",
     "matches": 1},
    {"why": "REG-3307 - a crest absent from the ranking is called quiet again",
     "file": "tv/crest_loudness.py",
     "find": "        return 2, [\"⚪ UNKNOWN — the install crest (%s) is not among",
     "replace": "        return 0, [\"⚪ UNKNOWN — the install crest (%s) is not among",
     "matches": 1},
    {"why": "REG-3307 - a crest tied with the loudest reads green when it sorts second",
     "file": "tv/crest_loudness.py",
     "find": "    if share >= scored[0][0]:\n",
     "replace": "    if rank == 0:\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
