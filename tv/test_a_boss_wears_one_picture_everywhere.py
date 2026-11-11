# -*- coding: utf-8 -*-
"""v3899 (#91, GrokBot #230 6803962990) - A BOSS WEARS ONE PICTURE EVERYWHERE.

GrokBot's look at the live bible (v3897, byte-matched): The Summoner's Boss card and Terror Zone card wore his animated
sprite (d2mon_The_Summoner.gif) while BOSS_PORTRAIT - run thumbs, source seams - still served summoner_graphic.png. The sweep
of the same split found the TV·D area art (TVN_BOSS) still giving the six act bosses their stone-backed renders
(mephisto_graphic.png ...) after REG-3321 moved every other surface to the sprites - his 11-07 "it should render just the
monster not the area behind it". Now every TVN_BOSS entry wears the file BOSS_PORTRAIT serves for that boss, and the
Summoner's sprite was opened on a contact sheet and recorded in the manifest (art/verify_boss_portraits.py passes).

DRIVEN on the shipped bible.html source: the two maps are parsed and compared. RED_PROOF below.
"""
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

ROOT = os.path.dirname(HERE)
NAME_TO_ID = {"Mephisto": "mephisto", "Baal": "baal", "Diablo": "diablo", "Andariel": "andariel", "Duriel": "duriel",
              "Nihlathak": "nihl", "The Summoner": "summoner", "The Countess": "countess"}


def _src():
    with io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8") as fh:
        return fh.read()


def _block(src, head, end):
    assert src.count(head) == 1, "PREMISE: %r is declared %d times" % (head, src.count(head))
    i = src.index(head)
    return src[i:src.index(end, i)]


def boss_portrait(src):
    body = _block(src, "  var BOSS_PORTRAIT = {", "\n  };")
    return dict(re.findall(r"(\w+):\s*'([^']+)'", body))


def tvn_boss(src):
    body = _block(src, "  var TVN_BOSS=[", "\n  ];")
    return dict(re.findall(r"name:'([^']+)',\s*art:'([^']+)'", body))


class ABossWearsOnePictureEverywhere(unittest.TestCase):

    def test_the_tv_d_area_art_wears_the_bosses_own_picture(self):
        """* THE POINT - TVN_BOSS and BOSS_PORTRAIT name the same file for every boss both carry"""
        src = _src()
        bp, tv = boss_portrait(src), tvn_boss(src)
        self.assertEqual(sorted(tv), sorted(NAME_TO_ID), "PREMISE: the TV·D area map names a different set of bosses")
        split = ["%s: TV·D %s vs BOSS_PORTRAIT %s" % (n, tv[n], bp.get(i)) for n, i in sorted(NAME_TO_ID.items())
                 if tv[n] != "art/" + str(bp.get(i))]
        self.assertEqual(split, [], "a boss wears two pictures: %s" % split)

    def test_the_summoner_wears_his_sprite(self):
        bp = boss_portrait(_src())
        self.assertEqual(bp.get("summoner"), "d2mon_The_Summoner.gif", "the Summoner's run thumb is his old render again")
        self.assertTrue(os.path.isfile(os.path.join(ROOT, "art", "d2mon_The_Summoner.gif")))


RED_PROOF = [
    {"why": "v3899 (#91) - the Summoner's run thumb wears his old render while his Boss card wears his sprite",
     "file": "bible.html",
     "find": "summoner:  'd2mon_The_Summoner.gif',",
     "replace": "summoner:  'summoner_graphic.png',",
     "matches": 1},
    {"why": "v3899 (#91) - the TV·D area art shows Mephisto's stone-backed render again",
     "file": "bible.html",
     "find": "name:'Mephisto',     art:'art/d2mon_Mephisto.gif' }",
     "replace": "name:'Mephisto',     art:'art/mephisto_graphic.png' }",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
