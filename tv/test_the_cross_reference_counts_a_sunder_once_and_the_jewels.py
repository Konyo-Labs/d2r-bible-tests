# -*- coding: utf-8 -*-
"""v3861 - THE FLEET CROSS-REFERENCE COUNTS A SUNDER ONCE, CARRIES THE SIX COLOSSAL JEWELS, AND "BOTH NEED" SHOWS.

His words, 2026-11-05, on the Dean uniques panel: "i have all the latents so something here is bugged with it make sure
to check the fleet and deans pc and cross refrence the consoles one to the other from both sides", then "we both need
defenders bile.. and we need short staff which is the bane ash ... so the we both need needs to be fixed also".

MEASURED on the live fleet record the same hour (his console's /api/fleet, decoded against the 396-name roster):
    his console   all six sunders as Latent (+ bare Bone Break, Rotting Fissure)
    Dean          all six sunders bare, no Latent
So the panel listed Black Cleft / Cold Rupture / Crack of the Heavens / Flame Rift under "they have" and the six Latent
names under "you have" - one charm each, spelled two ways. His rulings (v2680, v3183) count a sunder ONCE in the
chronicle, and the board already folds it (bible.html _isUpgradedSunder); the compare did not. And "you both need"
refused itself: the board's unique tally is 403 = 397 hunt cards + 6 colossal jewels, the roster is 396 names, and the
six jewels (Defender's Bile among them) had no bit on the wire at all.

The fix, each half a case below: the uniques compare folds every sunder spelling to its bare name (the masks keep every
spelling - the vault still holds each as its own, v3183); the six jewels travel in a mask of their own (wire-additive:
an older peer still compares, and its jewels are NAMED as not judged, never read as none); and the both-need column is
published when the folded roster, the facet split and the jewels account for every name the board counts.
"""
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import fleet_mask as FM  # noqa: E402
import control_app as CA  # noqa: E402

SUN = list(FM.SUNDER_BASES)
LATENT = ["Latent " + b for b in SUN]


def _bible():
    with io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8") as fh:
        return fh.read()


class TheConstantsAreThePagesOwn(unittest.TestCase):
    """The compare folds and counts with the board's own lists - read from bible.html, never retyped."""

    @classmethod
    def setUpClass(cls):
        cls.page = _bible()

    def _js_list(self, start):
        i = self.page.index(start)
        body = self.page[i + len(start):self.page.index("]", i + len(start))]
        # a double-quoted name may hold an apostrophe (Defender's Bile), so each quote style is matched on its own
        return [a or b for a, b in re.findall(r"\"([^\"]*)\"|'([^']*)'", body)]

    def test_the_six_sunder_bases_are_the_boards(self):
        self.assertEqual(self.page.count("var _CHRON_SUNDER_BASES = ["), 1)
        self.assertEqual(sorted(self._js_list("var _CHRON_SUNDER_BASES = [")), sorted(FM.SUNDER_BASES))

    def test_the_facet_split_is_the_boards(self):
        self.assertEqual(self.page.count("var _CHRON_FACETS = ["), 1)
        self.assertEqual(len(self._js_list("var _CHRON_FACETS = [")), FM.FACET_VARIANTS)

    def test_the_colossal_roster_is_the_boards_six(self):
        self.assertEqual(self.page.count("  function _colossalTallyRows(){\n    return ["), 1)
        page6 = self._js_list("  function _colossalTallyRows(){\n    return [")
        roster, fp = FM.load_roster_for("colossal")
        self.assertEqual(roster, page6, "the colossal mask names a different six than the board tallies")
        self.assertTrue(fp)
        self.assertIn("Defender's Bile", roster)


class TheCompareFoldsASunder(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.roster, cls.fp = FM.load_roster_for("uniques")
        common = [n for n in cls.roster if n not in SUN + LATENT][:40]
        cls.mine = FM.encode(common + LATENT + ["Bone Break", "Rotting Fissure"], cls.roster, cls.fp)
        cls.theirs = FM.encode(common + SUN, cls.roster, cls.fp)

    def test_premise_unfolded_the_same_charms_land_on_both_sides(self):
        r = FM.compare(self.mine, self.theirs, self.roster, self.fp)
        self.assertEqual(sorted(r["iHaveTheyDont"]), sorted(LATENT), "the measured shape no longer reproduces")
        self.assertEqual(sorted(r["theyHaveIDont"]), sorted(set(SUN) - {"Bone Break", "Rotting Fissure"}))

    def test_folded_nobody_has_a_sunder_the_other_lacks(self):
        r = FM.compare(self.mine, self.theirs, self.roster, self.fp, fold=FM.chronicle_key)
        self.assertEqual(r["iHaveTheyDont"], [], "a sunder spelled two ways is still listed as a difference")
        self.assertEqual(r["theyHaveIDont"], [])
        self.assertEqual(r["foldedN"], len(self.roster) - len(LATENT))
        self.assertFalse(any(n.startswith(("Latent ", "Renewed ")) for n in r["neitherHas"]),
                         "an upgraded spelling is a both-need row of its own")

    def test_the_fold_touches_only_the_six(self):
        self.assertEqual(FM.chronicle_key("Renewed Black Cleft"), "Black Cleft")
        self.assertEqual(FM.chronicle_key("Latent Heart"), "Latent Heart")
        self.assertEqual(FM.chronicle_key("Bane Ash"), "Bane Ash")


class TheConsoleComparesBothSides(unittest.TestCase):
    """The real fleet_compare, with the fleet, his masks and his board's total stood in."""

    def setUp(self):
        self.roster, self.fp = FM.load_roster_for("uniques")
        self.croster, self.cfp = FM.load_roster_for("colossal")
        common = [n for n in self.roster if n not in SUN + LATENT and n != "Bane Ash"][:40]
        self.masks_mine = {"uniques": FM.encode(common + LATENT + ["Bone Break", "Rotting Fissure"], self.roster, self.fp),
                           "colossal": FM.encode(["Guardian's Light"], self.croster, self.cfp)}
        self.masks_dean = {"uniques": FM.encode(common + SUN, self.roster, self.fp),
                           "colossal": FM.encode(["Protector's Stone"], self.croster, self.cfp)}
        self.saved = {k: getattr(CA, k) for k in ("fleet_presence", "_mask_cached", "_fleet_show_total",
                                                  "board_tally_load")}
        CA._mask_cached = lambda ledger="sets": self.masks_mine.get(ledger)
        CA._fleet_show_total = lambda ledger: (403, None) if ledger == "uniques" else (135, None)
        CA.board_tally_load = lambda: {"uniques": {"have": 395, "total": 403}}

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(CA, k, v)

    def _compare(self, dean_masks):
        CA.fleet_presence = lambda force=False: {"ok": True, "online": [
            {"machine": "dean-box", "nickname": "Dean", "ver": "v3861", "masks": dean_masks}], "offline": []}
        return CA.fleet_compare("dean-box", "uniques")

    def test_from_his_side_no_sunder_appears_and_both_need_shows_the_jewel(self):
        r = self._compare(self.masks_dean)
        self.assertTrue(r.get("ok"), r.get("why"))
        listed = set(r["theyHaveIDont"]) | set(r["iHaveTheyDont"])
        self.assertFalse(listed & set(SUN + LATENT), "a sunder is still a difference: %r" % sorted(listed & set(SUN + LATENT)))
        self.assertIsInstance(r.get("neitherHas"), list, "both-need refused: %r" % r.get("neitherWhy"))
        self.assertIn("Defender's Bile", r["neitherHas"])
        self.assertIn("Bane Ash", r["neitherHas"])
        self.assertIn("Protector's Stone", r["theyHaveIDont"])
        self.assertIn("Guardian's Light", r["iHaveTheyDont"])
        self.assertIn("Rainbow Facet", r.get("neitherNote") or "", "the facet split is not said")

    def test_from_deans_side_the_mirror_holds(self):
        self.masks_mine, self.masks_dean = self.masks_dean, self.masks_mine
        r = self._compare(self.masks_dean)
        listed = set(r["theyHaveIDont"]) | set(r["iHaveTheyDont"])
        self.assertFalse(listed & set(SUN + LATENT))
        self.assertIn("Defender's Bile", r["neitherHas"])
        self.assertIn("Guardian's Light", r["theyHaveIDont"])

    def test_a_peer_with_no_jewel_mask_still_compares_and_names_the_six_not_judged(self):
        r = self._compare({"uniques": self.masks_dean["uniques"]})
        self.assertTrue(r.get("ok"), r.get("why"))
        self.assertIsInstance(r.get("neitherHas"), list, "an older peer blanked both-need: %r" % r.get("neitherWhy"))
        self.assertNotIn("Defender's Bile", r["neitherHas"], "a jewel nobody published was judged")
        note = r.get("neitherNote") or ""
        self.assertIn("not judged yet", note)
        self.assertIn("Defender's Bile", note)


RED_PROOF = [
    {"why": "v3861 - the uniques compare stops folding: one sunder lands on both sides again",
     "file": "tv/control_app.py",
     "find": "                      fold=(_fm.chronicle_key if ledger == \"uniques\" else None))\n",
     "replace": "                      fold=None)\n",
     "matches": 1},
    {"why": "v3861 - the fold leaves a Latent spelling as its own name",
     "file": "tv/fleet_mask.py",
     "find": "            return s[len(q):]\n",
     "replace": "            return s\n",
     "matches": 1},
    {"why": "v3861 - the six colossal jewels never reach the compare: Defender's Bile cannot be a both-need row",
     "file": "tv/control_app.py",
     "find": "        out = _fleet_merge_colossal(out, them)\n",
     "replace": "        pass\n",
     "matches": 1},
    {"why": "v3861 - the facet split is not counted, so the both-need column refuses again",
     "file": "tv/control_app.py",
     "find": "        cov = folded - 1 + FMX.FACET_VARIANTS\n",
     "replace": "        cov = folded\n",
     "matches": 1},
    {"why": "v3861 - an older peer with no jewel mask blanks the both-need column",
     "file": "tv/control_app.py",
     "find": "            partial[\"partialOk\"] = True\n",
     "replace": "            pass\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
