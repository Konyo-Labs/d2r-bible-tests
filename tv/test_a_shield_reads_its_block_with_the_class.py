# -*- coding: utf-8 -*-
"""v3886 (#141, GrokBot's #28 pass 6720634931, adjudicated REAL 11-08) - A SHIELD'S CHANCE TO BLOCK READS ITS BASE BLOCK PLUS
THE CLASS'S BLOCK FACTOR.

The build screen's "Chance to Block (items)" row summed only the items' +% Increased Chance of Blocking: a Paladin with a
white Sacred Targe read nothing, while the game shows 60% - the base's own block (armor.txt `block`, 30) plus the class's
BlockFactor (charstats.txt: Paladin 30, Amazon / Assassin / Barbarian / Warlock 25, Druid / Necromancer / Sorceress 20). Both
numbers are read from his install by tv/char_props.py into the engine's tables (bases [9], classes [5]); the character's own
total, that x (Dexterity - 15) / (2 x level) capped at 75%, needs Dexterity, which is UNKNOWN until a save is imported - the
row says so instead of guessing. With no class chosen, the base block stands and the class factor is UNKNOWN, named.

Runs the SHIPPED engine element in node (the harness of test_the_character_sheet_sums_the_game_data). RED_PROOF below.
[[unknown-stays-unknown]]
"""
import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import test_the_character_sheet_sums_the_game_data as SHEET  # noqa: E402  (the engine cut and its source)

NODE = SHEET.NODE
CASES = {
    "pal": ({"cls": "Paladin", "level": 80, "sets": [{"slots": {"larm": {"name": "Sacred Targe"}}}]}, {"difficulty": "Hell"}),
    "sor": ({"cls": "Sorceress", "level": 80, "sets": [{"slots": {"larm": {"name": "Monarch"}}}]}, {"difficulty": "Hell"}),
    "none": ({"level": 80, "sets": [{"slots": {"larm": {"name": "Monarch"}}}]}, {"difficulty": "Hell"}),
    "bare": ({"cls": "Paladin", "level": 80, "sets": [{"slots": {}}]}, {"difficulty": "Hell"}),
}
DRIVER = r"""
var window = {};
%(engine)s
var E = window.D2R_CHAR_ENGINE, C = %(cases)s, out = {};
Object.keys(C).forEach(function(k){
  var s = E.sheet(C[k][0], C[k][1]);
  out[k] = (s.rows || []).filter(function(r){ return r.key === 'block'; })[0] || null;
});
process.stdout.write(JSON.stringify(out));
"""


def _run():
    js = DRIVER % {"engine": SHEET._engine(SHEET._src()), "cases": json.dumps(CASES)}
    r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=90)
    if r.returncode != 0:
        raise AssertionError("the shipped stats engine would not run - UNKNOWN, not passing: %s" % r.stderr[:900])
    return json.loads(r.stdout)


def _parts(row):
    return [(p.get("src"), p.get("lo"), p.get("hi")) for p in (row or {}).get("parts") or []]


@unittest.skipIf(NODE is None, "node is absent - this law is UNMEASURED, not passing")
class AShieldReadsItsBlockWithTheClass(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.o = _run()

    def test_a_paladin_with_a_sacred_targe_reads_60(self):
        """* THE POINT - 30 base + the Paladin's 30"""
        row = self.o["pal"]
        self.assertIsNotNone(row, "PREMISE: the sheet has no Chance to Block row")
        self.assertIn(("Sacred Targe", 60, 60), _parts(row), "a Paladin's Sacred Targe does not read 60%%: %r" % _parts(row))

    def test_the_class_factor_is_the_classs_own(self):
        """a Sorceress's Monarch (base 22 in his install) adds her 20, never the Paladin's 30"""
        parts = dict((p[0], p[1]) for p in _parts(self.o["sor"]))
        self.assertIn("Monarch", parts, "PREMISE: the Monarch put nothing in the block row: %r" % _parts(self.o["sor"]))
        base = SHEET.CP.embedded(SHEET._src())["bases"]
        mon = next(v for v in base.values() if v[0] == "Monarch")
        self.assertEqual(parts["Monarch"], mon[9] + 20, "the Sorceress's block factor is not 20 on her Monarch")

    def test_no_class_keeps_the_base_and_names_the_unknown_factor(self):
        row = self.o["none"]
        base = SHEET.CP.embedded(SHEET._src())["bases"]
        mon = next(v for v in base.values() if v[0] == "Monarch")
        self.assertIn(("Monarch", mon[9], mon[9]), _parts(row), "with no class the base block went missing or got a factor")
        self.assertIn("no class is chosen", json.dumps(row), "the missing class factor was not named")

    def test_the_total_needs_dexterity_and_says_so(self):
        self.assertIn("Dexterity is UNKNOWN until a save is imported", self.o["pal"].get("note") or "",
                      "the row claims a total its Dexterity cannot give")
        self.assertNotIn("Sacred Targe", json.dumps(self.o["bare"]), "a build wearing no shield read a shield's block")


RED_PROOF = [
    {"why": "v3886 (#141) - the class factor is dropped: a Paladin's Sacred Targe reads 30%, not the game's 60%",
     "file": "bible.html",
     "find": "          parts.push({ src: it.name, via: 'armor.txt block + charstats.txt BlockFactor', how: 'fixed', lo: bb + cf, hi: bb + cf,\n",
     "replace": "          parts.push({ src: it.name, via: 'armor.txt block + charstats.txt BlockFactor', how: 'fixed', lo: bb, hi: bb,\n",
     "matches": 1, "needs": "node"},
    {"why": "v3886 (#141) - the shield's own block is never read again (only the items' +% mods)",
     "file": "bible.html",
     "find": "          if (!(it.base && it.base[1] === 's' && it.base[9] > 0)) return;\n",
     "replace": "          return;\n",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main()
