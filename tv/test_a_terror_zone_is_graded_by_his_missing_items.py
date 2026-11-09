# -*- coding: utf-8 -*-
"""v3889 (#133, REG-3495) - A TERROR ZONE IS GRADED BY THE ITEMS HE STILL NEEDS, AND A GOOD ONE GLOWS WHILE IT IS UP.

His words 11-08 12:45, with the console's TERROR ZONE card (Far Oasis GOOD, 880 density): "for terror zones far oasis is
good? why? what reason? density here looks low for a good farm is it related to the items i have or need to farm?", "it
should be greyed off should it not?", "when a good terror zone is up it should glow". MEASURED: the card graded on density
alone (control_ui _tzTier, s = den/2200*0.85) and never read his grail.

Now the board answers (bible.html window.tzZoneGrade, beside the Quick wins ranking it reuses - _qwPlaces at his MF,
/players and level): for every unique he has not found, a terror-zone kill IN this zone (a silospen place in that area, or
the zone's own farm, an area run counted by its kills) that takes fewer runs to an even chance than the item's best plain
run is a reason; GOOD on any, PRIME at half the runs or fewer, THIN on none. The console's cards and the slot's chip read
that grade (control_ui _tzGrade), a notable zone keeps PRIME, a board that cannot be asked leaves the density grade and
says so in the hover, and a LIVE zone graded GOOD or PRIME by his items glows.

Measured on an empty world (all 397 uniques missing): Far Oasis THIN (Beetleburst's terror never beats an item's best run),
Catacombs PRIME (Tyrael's Might 48,274 runs in Hell TZ Andariel vs 304,501 at Hell Baal), Moo Moo Farm GOOD. The board half
runs on the whole page in node (tv/vault_page_node.py, empty storage - never his); the console half is read from its
source. RED_PROOF below. [[heart-first]] [[unknown-stays-unknown]] [[the-unjoined-end]]
"""
import io
import json
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable   # it prints non-ASCII: never crash while REPORTING
    _enable()
except Exception:
    pass
import vault_page_node as VPN  # noqa: E402

BODY = r"""
var _TZG_ASK = function (z, f) { return window.tzZoneGrade(z, f); };
OUT.oasis = _TZG_ASK('Far Oasis', '');
OUT.cata = _TZG_ASK('Catacombs', 'andariel');
OUT.cows = _TZG_ASK('Moo Moo Farm', 'cows');
OUT.nowhere = _TZG_ASK('Nowhere At All', '');
var fl = {}; (OUT.cata.items || []).forEach(function (h) { fl[h.n] = ''; });
window.LSR.setItem('d2r_foundLog', JSON.stringify(fl));
OUT.cataAfter = _TZG_ASK('Catacombs', 'andariel');
OUT.areas = Object.keys(QW_TARGETS).map(function (t) { return [QW_TARGETS[t].a, window._tzgZoneOfArea(QW_TARGETS[t].a)]; });
"""


def _flat(z):
    z = re.sub(r"[‘’']", "", str(z or "").lower())
    z = re.sub(r"[^a-z0-9]", "", z)
    return z[3:] if z.startswith("the") else z


def _tz_info_keys():
    with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
        ui = fh.read()
    head = "var TZ_INFO = "
    assert ui.count(head) == 1, "PREMISE: the console's TZ_INFO table moved or doubled"
    i = ui.index(head) + len(head)
    return list(json.loads(ui[i:ui.index("\n", i)].rstrip().rstrip(";")).keys())


class TheBoardGradesAZoneByHisMissingItems(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.out = VPN.run(BODY, prelude="localStorage.setItem('d2r_ownerClaim', '*');\n", timeout=300) if VPN.NODE else None

    def setUp(self):
        if self.out is None:
            self.skipTest("node is absent on this machine - the board's grade is UNMEASURED here, never a pass")

    def test_a_zone_his_items_gain_from_is_good_and_one_they_do_not_is_thin(self):
        """* THE POINT - Far Oasis (his picture) reads THIN with the reason; Catacombs PRIME on a named item"""
        oasis, cata = self.out["oasis"], self.out["cata"]
        self.assertTrue(oasis["ok"] and cata["ok"], (oasis, cata))
        self.assertGreater(oasis["missing"], 300, "PREMISE: an empty world misses (almost) every unique: %s" % oasis["missing"])
        self.assertEqual(oasis["tier"], "thin", "Far Oasis is graded worth his items on an empty world: %s" % oasis)
        self.assertIn("missing uniques drops sooner here", oasis["why"])
        self.assertEqual(cata["tier"], "prime", cata)
        h = cata["items"][0]
        self.assertTrue(h["n"] and h["here"] and h["best"], h)
        self.assertLessEqual(h["hereRuns"] * 2, h["bestRuns"], "PRIME without half the runs: %s" % h)
        self.assertIn("TZ", h["here"], "the reason is not a terror-zone kill: %s" % h)

    def test_an_area_run_is_a_run(self):
        self.assertIn(self.out["cows"]["tier"], ("good", "prime"), "the Cow Level's terror run is not counted: %s" % self.out["cows"])

    def test_his_grail_is_read(self):
        """an item he found is no longer a reason - the grade reads d2r_foundLog, never a fixed list"""
        before = set(h["n"] for h in self.out["cata"]["items"])
        after = set(h["n"] for h in self.out["cataAfter"]["items"])
        self.assertTrue(before, "PREMISE: Catacombs named no item to find")
        self.assertEqual(before & after, set(), "found items are still graded as missing: %s" % sorted(before & after))
        self.assertLess(self.out["cataAfter"]["count"], self.out["cata"]["count"])

    def test_a_zone_nobody_knows_is_thin_not_an_error(self):
        self.assertTrue(self.out["nowhere"]["ok"])
        self.assertEqual((self.out["nowhere"]["tier"], self.out["nowhere"]["count"]), ("thin", 0))

    def test_every_place_names_a_zone_the_console_knows(self):
        """the board's areas (QW_TARGETS) and the console's zones (TZ_INFO) are two vocabularies: every area must land on a
        console zone or be declared no terror zone (''), or its reasons never reach a card"""
        keys = set(_flat(k) for k in _tz_info_keys())
        bad = sorted(set("%s -> %r" % (a, z) for a, z in self.out["areas"] if z != "" and z not in keys))
        self.assertEqual(bad, [], "a place's area lands on no console zone: %s" % bad)
        self.assertGreater(len(self.out["areas"]), 30, "PREMISE: almost no places were read")
        # two zones share a word: Radament's sewers are Act 2's (Lut Gholein), Icehawk Riftwing's are Act 3's (Kurast)
        got = dict(self.out["areas"])
        self.assertEqual(got.get("Sewers Level 3"), _flat("Lut Gholein Sewers"), "Radament's place lands in Act 3's sewers")
        self.assertEqual(got.get("Sewers Level 1"), _flat("Sewers"), "Icehawk Riftwing's place lands in Act 2's sewers")
        self.assertEqual(got.get("Cave Level 1"), _flat("The Cave"), "BASELINE: a 'Level N' area lands on its zone by rule")


class TheConsoleCardReadsThatGrade(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
            cls.ui = fh.read()

    def test_the_cards_and_the_chip_read_the_items_grade(self):
        self.assertIn("var file = _artFor(x), act = _actOf(file, x), t = _tzGrade(x);", self.ui)
        self.assertIn("        var t = _tzGrade(x);   /* v3889 (#133) - the chip says what the cards say */", self.ui)
        self.assertEqual(len(re.findall(r"_tzTier\(", self.ui)), 1, "a card grades on density alone again (only _tzGrade may ask _tzTier)")

    def test_a_board_that_cannot_be_asked_keeps_density_and_says_so(self):
        self.assertIn("try { g = W ? W.tzZoneGrade(k, TZ_BOSS[k] || '') : null; } catch (e) { g = null; }", self.ui)
        self.assertIn("'your grail could not be asked, so this grade is density only'", self.ui)

    def test_a_live_zone_worth_his_items_glows(self):
        self.assertIn("((hero && t.byItems && (t.tier === 'good' || t.tier === 'prime')) ? ' tzz-glow' : '')", self.ui)
        self.assertIn(".tzz.tzz-glow { opacity: 1; filter: none; }", self.ui)
        # MEASURED (computed style, 1512 and 1120): at (0,2,0) above the live cards' tzAlive breath the glow lost the cascade
        # and the card ran tzAlive like every live card. The glow must outrank it AND come after it.
        alive = self.ui.find(".tz-zones-hero .tzz { animation: tzAlive")
        glow = self.ui.find(".tz-zones-hero .tzz.tzz-glow { animation: tzzGlow 2.6s ease-in-out infinite; }")
        self.assertGreater(alive, 0, "PREMISE: the live cards' tzAlive breath moved - re-read the cascade")
        self.assertGreater(glow, alive, "the glow rule is missing or sits before tzAlive, which then wins the cascade")
        self.assertIn("@media (prefers-reduced-motion: reduce) { .tzz.tzz-glow { animation: none;", self.ui)


RED_PROOF = [
    {"why": "v3889 (#133) - every terror-zone row is a reason, whether or not it beats the item's best run",
     "file": "bible.html",
     "find": "          if (plain && !(h.runs < plain.runs * (1 - QW_SAME))) return;\n",
     "replace": "          if (false) return;\n",
     "matches": 1, "needs": "node"},
    {"why": "v3889 (#133) - the grade ignores his grail",
     "file": "bible.html",
     "find": "        if (!x || !x.n || _ownedHas(own, x.n)) return;\n        missing++;\n",
     "replace": "        if (!x || !x.n) return;\n        missing++;\n",
     "matches": 1, "needs": "node"},
    {"why": "v3889 (#133) - an area run (the Cow Level) is left out again",
     "file": "bible.html",
     "find": "          if (!p || !p.s || p.runs == null) return;   // an AREA run",
     "replace": "          if (!p || !p.s || p.kind === 'area' || p.kpr > 1 || p.runs == null) return;   // an AREA run",
     "matches": 1, "needs": "node"},
    {"why": "v3889 (#133) - the Cow King's level lands on no console zone",
     "file": "bible.html",
     "find": " 'The Secret Cow Level': 'Moo Moo Farm',\n",
     "replace": "\n",
     "matches": 1, "needs": "node"},
    {"why": "v3889 (#133) - Radament's place lands in Act 3's sewers (a real zone, the wrong one)",
     "file": "bible.html",
     "find": "                    'Sewers Level 3': 'Lut Gholein Sewers', ",
     "replace": "                    ",
     "matches": 1, "needs": "node"},
    {"why": "v3889 (#133) - the cards grade on density alone again",
     "file": "tv/control_ui.html",
     "find": "var file = _artFor(x), act = _actOf(file, x), t = _tzGrade(x);",
     "replace": "var file = _artFor(x), act = _actOf(file, x), t = _tzTier(x);",
     "matches": 1},
    {"why": "v3889 (#133) - the glow sits at tzAlive's specificity again and loses the cascade (measured: the card ran tzAlive)",
     "file": "tv/control_ui.html",
     "find": "    .tz-zones-hero .tzz.tzz-glow { animation: tzzGlow 2.6s ease-in-out infinite; }\n",
     "replace": "",
     "matches": 1},
    {"why": "v3889 (#133) - every live card glows, worth his items or not",
     "file": "tv/control_ui.html",
     "find": "((hero && t.byItems && (t.tier === 'good' || t.tier === 'prime')) ? ' tzz-glow' : '')",
     "replace": "(hero ? ' tzz-glow' : '')",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
