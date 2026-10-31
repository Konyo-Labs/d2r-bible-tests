# -*- coding: utf-8 -*-
"""v3849 D1 (Elad 2026-10-31 12:16-12:24) - WHILE THE ROLL IS UNKNOWN, A MAGIC ITEM SHOWS EACH MOD'S MIN-MAX RANGE.

Measured before (the whole page in node): Lion Branded Grand Charm tipped "Base item - rolls: base item - value = type +
sockets + ethereal", and a magic keeper with no read mods showed only "1-2 random affixes". The affix names are read
against the game's affix table (CB_DB af) for the base's type, one range line per mod, in the att-aff style a unique's
range uses. Exact mods (read or typed) replace the ranges.
"""
import os, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable; enable()
import vault_page_node as VPN  # noqa: E402

BODY = r"""
EXTRA_ITEMS['Lion Branded Grand Charm'] = {rarity:'basic', base:'Lion Branded Grand Charm', val:'tv'};
OUT.r = {
  sharp: _affixRangeLines('Sharp Grand Charm of Sustenance'),
  lion: _affixRangeLines('Lion Branded Grand Charm'),
  harl: _affixRangeLines('Harlequin Crest'),
  lionTip: String(_extraTipHtml('Lion Branded Grand Charm')),
  balTip: String(_mfTipHtml('Small Charm of Balance')),
  balCard: String(_magicFindCardHtml('Small Charm of Balance'))
};
"""


class AffixRanges(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = VPN.run(BODY, timeout=300)["r"]

    def test_each_affix_gives_a_range_line(self):
        self.assertEqual(len(self.r["sharp"]), 3, self.r["sharp"])
        self.assertTrue(any("Maximum Damage" in l and "-" in l for l in self.r["sharp"]), self.r["sharp"])
        self.assertTrue(any("Life" in l for l in self.r["sharp"]), self.r["sharp"])
        self.assertTrue(any("Combat Skills" in l for l in self.r["lion"]), self.r["lion"])

    def test_a_unique_is_not_read_as_affixes(self):
        self.assertEqual(self.r["harl"], [])

    def test_a_magic_charm_is_never_a_base_item(self):
        self.assertNotIn("Base item", self.r["lionTip"])
        self.assertNotIn("value = type + sockets", self.r["lionTip"])
        self.assertIn('data-mod-range="1"', self.r["lionTip"])

    def test_tip_and_card_show_the_ranges(self):
        self.assertIn("Faster Hit Recovery", self.r["balTip"])
        self.assertIn('data-mod-range="1"', self.r["balCard"])


RED_PROOF = [
    {"why": "v3849 D1 - the affix ranges are never read",
     "file": "bible.html",
     "find": "  if (!pre && !suf) return [];\n",
     "replace": "  return [];\n",
     "matches": 1},
    {"why": "v3849 D1 - a tables-read magic charm tips as a Base item again",
     "file": "bible.html",
     "find": "  if (_eRng.length && rar === 'basic') rar = 'magic';\n",
     "replace": "",
     "matches": 1},
    {"why": "v3849 D1 - the keeper tip drops the ranges",
     "file": "bible.html",
     "find": "    + rngLine\n",
     "replace": "",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
