# -*- coding: utf-8 -*-
"""v3884 (REG-3440, his 11-08 12:09-12:10 with silospen's Debug Information open) - EVERY ITEM'S QUALITY LEVEL IS SILOSPEN'S.

His words: "the Q levels i think its 69 and not 71? could that based on what it reads in silopen" (Heaven's Light) and "for
bane ash ... lvl 7 required lvl to use it? and base lvl 1? ... the console reads q5 for this and it should be q1 or q7".
MEASURED 11-08: silospen's `level` (the item's QUALITY level - the item level a monster must reach to drop it) against the
page's qlvl, in the two stores that hold one (BOSSES' drop tables - the Best runs / Quick wins chips - and ITEM_CODEX - the
item card): 366 items wrong, 626 cells. About a hundred were the WEAR level (Bane Ash 5, Death's Web 66), some the base
item's level, seven 0, the rest nothing (Heaven's Light 71 vs 69, Stormlash 73 vs 86, The Cat's Eye 50 vs 58). GrokBot's
independent pass (#230): 117 of 390 uniques right. Every qlvl is silospen's level now; the wear level stays in its own field
(ITEM_CODEX reqLvl), untouched.

Joined on one spelling (silospen_tz_levels.canon - "Gull (dagger)" is silospen's "Gull"). A page name silospen does not list
must be one of the declared non-items below (a whole set, a rune, a key, a token) - anything else is a refusal, never a skip.
Reads the page's two JSON literals and the vendored pull (tv/data/silospen_qlvl_rotw30.json). RED_PROOF below.
"""
import io
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import silospen_tz_levels as T  # noqa: E402

BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")
DATA = os.path.join(HERE, "data", "silospen_qlvl_rotw30.json")

#: page names that are not one item silospen prices - each a whole set, a rune, a key or a token (measured 11-08: 19)
NOT_AN_ITEM = {
    "Aldur's Watchtower (any)", "Cow King's Leathers (set)", "Griswold's Legacy (any)", "Hwanin's Majesty (set)",
    "Immortal King set (any)", "Ist rune", "Jah/Ber/Sur rune", "Key of Destruction", "Key of Hate", "Key of Terror",
    "M'avina's Battle Hymn (any)", "Naj's Ancient Vestige", "Natalya's Odium (any)", "Orphan's Call (set)",
    "Sazabi's Grand Tribute", "Sigon's Complete Steel", "Tal Rasha set (any piece)", "Trang-Oul set (any piece)",
    "Worldstone Shard (any)",
}


def _literal(src, name):
    i = src.index(name) + len(name)
    return json.JSONDecoder().raw_decode(src[i:])[0]


class EveryQlvlIsSilospens(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with io.open(BIBLE, encoding="utf-8") as fh:
            src = fh.read()
        with io.open(DATA, encoding="utf-8") as fh:
            cls.silo = json.load(fh)["levels"]
        cls.lv = dict((T.canon(n), v["level"]) for n, v in cls.silo.items() if v.get("level") is not None)
        cls.cells = []
        for b in _literal(src, "const BOSSES = "):
            for d in b["dropTable"]:
                if "qlvl" in d:
                    cls.cells.append(("BOSSES." + b["id"], d["n"], d["qlvl"]))
        for n, c in _literal(src, "const ITEM_CODEX = ").items():
            if isinstance(c, dict) and "qlvl" in c:
                cls.cells.append(("ITEM_CODEX", n, c["qlvl"]))

    def test_every_qlvl_is_the_level_silospen_gives(self):
        """* THE POINT - Heaven's Light 69, Bane Ash 7, Death's Web 74: zero cells differ"""
        bad = ["%s %s: page q%s, silospen %s" % (w, n, q, self.lv[T.canon(n)])
               for w, n, q in self.cells if T.canon(n) in self.lv and q != self.lv[T.canon(n)]]
        self.assertGreater(len(self.cells), 1000, "premise: the page's qlvl cells were not read (%d)" % len(self.cells))
        self.assertEqual(bad, [], "%d qlvl cell(s) are not silospen's level:\n  %s" % (len(bad), "\n  ".join(bad[:25])))

    def test_his_three(self):
        for w, n, q in self.cells:
            want = {"Heaven's Light": 69, "Bane Ash": 7, "Death's Web": 74}.get(n)
            if want is not None:
                self.assertEqual(q, want, "%s %s reads q%s" % (w, n, q))

    def test_a_name_silospen_does_not_list_is_a_declared_non_item(self):
        stray = sorted(set(n for _w, n, _q in self.cells if T.canon(n) not in self.lv) - NOT_AN_ITEM)
        self.assertEqual(stray, [], "a page item silospen does not list and nobody declared - its qlvl is unchecked: %s" % stray)
        gone = sorted(n for n in NOT_AN_ITEM if not any(n == c[1] for c in self.cells))
        self.assertEqual(gone, [], "a declared non-item is no longer on the page - drop it from NOT_AN_ITEM: %s" % gone)

    def test_the_wear_level_stays_its_own(self):
        with io.open(BIBLE, encoding="utf-8") as fh:
            codex = _literal(fh.read(), "const ITEM_CODEX = ")
        self.assertEqual((codex["Bane Ash"].get("qlvl"), codex["Bane Ash"].get("reqLvl")), (7, 5),
                         "Bane Ash: quality 7, wear 5 - the two numbers must stay two fields")


RED_PROOF = [
    {"why": "v3884 (REG-3440) - Heaven's Light's card reads q71 again (neither silospen's 69 nor its wear level)",
     "file": "bible.html",
     "find": '"Heaven\'s Light":{"rarity":"unique","base":"Mighty Scepter","reqLvl":61,"reqStr":125,"reqDex":65,"sockets":3,"qlvl":69,',
     "replace": '"Heaven\'s Light":{"rarity":"unique","base":"Mighty Scepter","reqLvl":61,"reqStr":125,"reqDex":65,"sockets":3,"qlvl":71,',
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
