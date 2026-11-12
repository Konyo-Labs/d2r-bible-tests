# -*- coding: utf-8 -*-
"""v3902 (REG-3782, #91) - A ROW THAT NAMES THE TRAVINCAL COUNCIL DRAWS EACH PRIEST'S OWN SPRITE.

His ruling 11-12 ~09:20, asked "keep the council picture or show the priests' own sprites?": "show their own sprites".
GrokBot's v3899 look (#230): the BOSSES Super-Uniques chip "Travincal Council" and the RUNES row "Travincal Council · Toorc +
Geleb + Ismail · the 3-Council fight" both wore the one shared councilmember_graphic.png, while each priest has had his own
hash-pinned sprite since REG-3963. artOr now draws a GROUP name as its members' own sprites, in the order the row names them;
a caller that wants one URL (artUrl) and the Travincal zone card, which names no priest, keep the council picture.

DRIVEN: the shipped page run in node (vault_page_node): artOr / artUrl and the two rows' own data. RED_PROOF below.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import vault_page_node as VPN  # noqa: E402

BODY = r"""
var h = String(artOr('Travincal Council', 'X', 'sm'));
var srcs = []; h.replace(/src="([^"]+)"/g, function(_m, s){ srcs.push(s); return _m; });
var one = String(artOr('Toorc Icefist', 'X', 'sm'));
var rs = (typeof RUNE_SOURCES !== 'undefined' ? RUNE_SOURCES : []).filter(function(s){ return s.id === 'travincal'; })[0] || {};
var bs = (typeof BOSSES !== 'undefined' ? BOSSES : []).filter(function(b){ return b.id === 'travincal'; })[0] || {};
OUT.r = {group: /class="d2art-group"/.test(h), srcs: srcs, aria: (h.match(/aria-label="([^"]+)"/) || [])[1] || '',
         url: String(artUrl('Travincal Council') || ''), one: (one.match(/src="([^"]+)"/) || [])[1] || '',
         oneGroup: /d2art-group/.test(one), runeName: rs.name || '', runeSub: rs.subtitle || '', bossName: bs.name || ''};
"""


class ACouncilGroupRowDrawsEachPriestsSprite(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not VPN.NODE:
            raise AssertionError("node is not installed on this PC - this law runs the shipped page in node and does not skip")
        cls.r = VPN.run(BODY, timeout=300)["r"]

    def test_baseline_the_two_rows_name_the_council_and_one_url_is_the_council(self):
        self.assertEqual(self.r["runeName"], "Travincal Council", "PREMISE: the Runes row no longer names the Council")
        self.assertIn("Toorc + Geleb + Ismail", self.r["runeSub"])
        self.assertEqual(self.r["bossName"], "Travincal Council", "PREMISE: the Bosses chip no longer names the Council")
        self.assertIn("councilmember_graphic", self.r["url"], "a one-URL caller (the zone card) lost the council picture")

    def test_the_group_draws_the_three_priests_in_the_rows_order(self):
        """* THE POINT - his 11-12 ruling"""
        self.assertTrue(self.r["group"], "the Council row is drawn as one picture again")
        names = [s.rsplit("/", 1)[-1] for s in self.r["srcs"]]
        self.assertEqual(names, ["d2mon_Toorc_Icefist.gif", "d2mon_Geleb_Flamefinger.gif", "d2mon_Ismail_Vilehand.gif"],
                         names)
        self.assertEqual(self.r["aria"], "Travincal Council", "the group lost its own name for a screen reader")

    def test_a_priest_alone_is_one_sprite(self):
        self.assertFalse(self.r["oneGroup"])
        self.assertTrue(self.r["one"].endswith("d2mon_Toorc_Icefist.gif"), self.r["one"])


RED_PROOF = [
    {"why": "REG-3782 - the Council group row wears the one shared council picture again (his 11-12 ruling)",
     "file": "bible.html",
     "find": "  if (_grp) return '<span class=\"d2art-group\" role=\"img\" aria-label=\"' + _d2artEsc(name) + '\">'\n",
     "replace": "  if (false) return '<span class=\"d2art-group\" role=\"img\" aria-label=\"' + _d2artEsc(name) + '\">'\n",
     "matches": 1},
    {"why": "REG-3782 - the priests are drawn out of the order the row names them",
     "file": "bible.html",
     "find": "var ART_GROUP = {\"Travincal Council\": [\"Toorc Icefist\", \"Geleb Flamefinger\", \"Ismail Vilehand\"]};\n",
     "replace": "var ART_GROUP = {\"Travincal Council\": [\"Ismail Vilehand\", \"Geleb Flamefinger\", \"Toorc Icefist\"]};\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
