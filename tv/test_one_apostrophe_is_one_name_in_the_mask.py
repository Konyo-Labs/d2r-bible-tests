# -*- coding: utf-8 -*-
"""v3887 (REG-3470) - A CURLY AND A STRAIGHT APOSTROPHE ARE ONE NAME IN THE CROSS-REFERENCE MASK.

His 11-08, on the Fleet's uniques cross-reference with Dean: "cats eye i already have and tallied im pretty sure in my console
definitely sure in mygame ... this one is bugged". The column THEY HAVE - YOU DO NOT read "The Cat’s Eye". MEASURED on a copy of
his board's store the same evening: his found log held "The Cat's Eye" with a STRAIGHT apostrophe only, and the uniques roster
(tv/unique_roster.json) spells it - with Atma’s Scarab, Saracen’s Chance and Seraph’s Hymn - with the game's CURLY one. The mask
matched by exact name, so his bit was 0. The other three survived only because his log also held their curly spelling.
fleet_mask.encode now folds the apostrophe on both sides; nothing else is folded (the roster-drift guard the exact match was for
still stands).

Drives the shipped encoder and decoder. RED_PROOF below. [[copy-drift]] [[the-unjoined-end]]
"""
import io
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import fleet_mask as FM  # noqa: E402

CURLY = ["Atma’s Scarab", "Saracen’s Chance", "Seraph’s Hymn", "The Cat’s Eye"]


class OneApostropheIsOneNameInTheMask(unittest.TestCase):

    def test_premise_the_roster_spells_these_four_curly(self):
        with io.open(os.path.join(HERE, "unique_roster.json"), encoding="utf-8") as fh:
            names = json.load(fh)["names"]
        for n in CURLY:
            self.assertIn(n, names, "PREMISE: the roster no longer spells %s curly - the case moved" % n)

    def test_his_straight_cats_eye_sets_the_rosters_curly_bit(self):
        """* THE POINT - his found log's "The Cat's Eye" is the roster's "The Cat’s Eye\""""
        m = FM.encode(["The Cat's Eye"], CURLY, "fp")
        names, why = FM.decode(m, CURLY, "fp")
        self.assertEqual(names, ["The Cat’s Eye"], "a straight apostrophe missed the curly roster name: %r %r" % (names, why))
        self.assertEqual(m["have"], 1)

    def test_every_spelling_of_the_four_is_found_and_nothing_else_is_folded(self):
        straight = [n.replace("’", "'") for n in CURLY]
        self.assertEqual(FM.encode(straight, CURLY, "fp")["have"], 4)
        self.assertEqual(FM.encode(CURLY, CURLY, "fp")["have"], 4, "the roster's own spelling stopped matching")
        self.assertEqual(FM.encode(["The Cats Eye", "the cat's eye", "The Cat's Eye (amulet)"], CURLY, "fp")["have"], 0,
                         "a name that is not the same name was folded in - the mask is not a fuzzy match")


RED_PROOF = [
    {"why": "v3887 (REG-3470) - the mask matches by exact string again: his Cat's Eye reads 'they have - you do not'",
     "file": "fleet_mask.py",
     "find": "        if _fold(name) in have:\n",
     "replace": "        if name in have:\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
