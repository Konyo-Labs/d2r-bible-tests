# -*- coding: utf-8 -*-
"""THE FLEET MUST NAME WHAT EACH SIDE LACKS — ON HIS REAL ROSTER, NOT A TOY ONE.

Konyo, 2026-09-16, looking at the Dean drill: *"its not showing what dean doesnt have that i have
and doesnt show what we both need still.. which is the cow boots in this case... but in general it
should work not only the cows all of the logic behind it!"*

Two different things were tangled in that screenshot and this file separates them for good:

  · the COMPARE ENGINE — given two published masks, does it put each name in the right column?
  · the PUBLISH path  — did the other machine actually send a per-item list at all?

The engine was never the defect. The panel was on its one-sided branch because Dean's console
published a COUNT and no mask ("no board window"), which is the headless-console state Konyo's own
machine was in the same afternoon. A refusal drawn correctly looks exactly like a broken column,
which is why this pins the engine explicitly rather than trusting a screenshot to tell them apart.

⚠ HIS REAL ROSTER, HIS REAL CASE. A fixture roster would prove the arithmetic and not the join:
the names have suffixes ("Cow King's Hooves (heavy boots)"), and a compare fed bare names matches
NOTHING while every count still looks plausible. Measured — the first version of this check asserted
on "Cow King's Hooves" and could not find it in the roster at all. [[feedback-blind-fixture-green-gate]]

⚠ `neitherHas` MAY BE None AND THAT IS NOT A FAILURE. The server answers null when the roster is not
known to be the whole universe. This asserts the CONTENT only when a list was actually returned, and
never turns a refusal into a confident zero. [[unknown-stays-unknown]] [[zero-needs-a-denominator]]
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import fleet_mask as fm

COW = "Cow King's Hooves (heavy boots)"
VID = "Vidala's Ambush (armor)"


class TestTheFleetNamesWhatEachSideLacks(unittest.TestCase):

    def setUp(self):
        self.roster, self.fp = fm.load_roster_for("sets")
        self.lf = fm.list_fingerprint(self.roster)
        # the denominator: a roster that failed to load would make every assertion below vacuous
        self.assertGreater(len(self.roster), 100,
                           "the sets roster loaded %d names — too few to compare anything against"
                           % len(self.roster))
        for n in (COW, VID):
            self.assertIn(n, self.roster,
                          "%r is not in his sets roster, so this law is asserting on a name the "
                          "compare can never return — the suffix form is load-bearing" % n)

    def _mask(self, names):
        m = fm.encode(names, self.roster, self.fp)
        m["r"] = self.lf
        return m

    def test_a_name_only_they_have_is_named_not_counted(self):
        """His exact case: Dean has the cow boots, he does not. It must appear BY NAME."""
        mine = [n for n in self.roster if n not in (COW, VID)]
        theirs = [n for n in self.roster if n != VID]
        j = fm.compare(self._mask(mine), self._mask(theirs), self.roster, self.fp)
        self.assertTrue(j.get("ok"), "the compare refused two well-formed masks: %s" % j.get("why"))
        self.assertIn(COW, j.get("theyHaveIDont") or [],
                      "the one item Dean holds and he does not was not named in "
                      "'they have / you do not' — that column is the whole point of the drill")

    def test_a_name_neither_side_has_reaches_you_both_need(self):
        mine = [n for n in self.roster if n not in (COW, VID)]
        theirs = [n for n in self.roster if n != VID]
        j = fm.compare(self._mask(mine), self._mask(theirs), self.roster, self.fp)
        both = j.get("neitherHas")
        if both is None:
            self.skipTest("the server declined to call this roster the whole universe — "
                          "UNKNOWN, and this law does not manufacture a list from it")
        self.assertIn(VID, both,
                      "a piece NEITHER of them holds never reached 'you both need', which is the "
                      "column that tells them what to hunt together")

    def test_a_name_only_he_has_is_named_on_his_side(self):
        mine = [n for n in self.roster if n != VID]
        theirs = [n for n in self.roster if n not in (COW, VID)]
        j = fm.compare(self._mask(mine), self._mask(theirs), self.roster, self.fp)
        self.assertIn(COW, j.get("iHaveTheyDont") or [],
                      "the mirror direction is broken: a piece HE holds and Dean does not was "
                      "not named")

    def test_the_columns_are_disjoint(self):
        """A name in two columns at once would make the drill self-contradicting."""
        mine = [n for n in self.roster if n not in (COW, VID)]
        theirs = [n for n in self.roster if n != VID]
        j = fm.compare(self._mask(mine), self._mask(theirs), self.roster, self.fp)
        a = set(j.get("theyHaveIDont") or [])
        b = set(j.get("iHaveTheyDont") or [])
        c = set(j.get("neitherHas") or [])
        self.assertEqual(a & b, set(), "a name is both 'they have' and 'you have': %s" % (a & b))
        self.assertEqual(a & c, set(), "a name is both 'they have' and 'neither has': %s" % (a & c))
        self.assertEqual(b & c, set(), "a name is both 'you have' and 'neither has': %s" % (b & c))
        self.assertGreater(len(a) + len(b) + len(c), 0,
                           "all three columns came back empty for two masks that differ — that is "
                           "a silent compare, not agreement")

RED_PROOF = [
    {"why": "the compare names what THEY have from his own mask: the item Dean holds and he does not never reaches 'they have / you do not'",
     "file": "tv/fleet_mask.py",
     "find": "            \"theyHaveIDont\": [n for n in roster if n in sb and n not in sa],\n",
     "replace": "            \"theyHaveIDont\": [n for n in roster if n in sa and n not in sb],\n",
     "matches": 1},
    {"why": "a piece neither of them holds never reaches 'you both need'",
     "file": "tv/fleet_mask.py",
     "find": "            \"neitherHas\": [n for n in roster if n not in sa and n not in sb],\n",
     "replace": "            \"neitherHas\": [n for n in roster if n not in sa and n in sb],\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
