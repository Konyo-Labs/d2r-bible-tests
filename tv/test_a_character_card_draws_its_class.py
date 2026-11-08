# -*- coding: utf-8 -*-
"""v3887 (#154, REG-3469) - EVERY CHARACTER CARD DRAWS ITS CLASS'S OWN ANIMATED FIGURE; A MAIN WEARS IT IN A GOLD FRAME.

His 11-08: the characters "should render the visual character ingame like .gif like we have for bosses/monsters ... sorceress
mule should be a naked sorceress ... for a sorceress thats a main it should be equipped ... paladin is paladin ... render within
each cell", his reference the classic animated Sorceress. Each card's letter crest (W, A, S, P) is now that class's own idle
loop from d2runewizard.com/classes - the site whose Banished loop he picked the same evening - one per class, its starting
outfit and empty hands. Every file's source, sha1 and the Grok CLI's cold look (no names given, each matched to its class)
are in tv/data/class_art.json. A MAIN's card frames it in gold. A class the map does not name, or a file that will not load,
keeps the letter - never another class's figure. NOT DONE, said: a geared figure per class for a MAIN (no site serves one;
measured 11-08) - his install's legacy sprites are the route (#154 stays open for it).

Reads the record, the art files and the page's own helper (run in node). RED_PROOF below. [[unknown-stays-unknown]]
"""
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
NODE = shutil.which("node")
REC = os.path.join(HERE, "data", "class_art.json")
CLASSES = ("Amazon", "Assassin", "Barbarian", "Druid", "Necromancer", "Paladin", "Sorceress", "Warlock")


def _src():
    with io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8") as fh:
        return fh.read()


class ACharacterCardDrawsItsClass(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.src = _src()
        with io.open(REC, encoding="utf-8") as fh:
            cls.rec = json.load(fh)

    def test_every_class_has_its_own_file_with_its_recorded_sha1_and_cold_look(self):
        self.assertEqual(sorted(self.rec["classes"]), sorted(CLASSES), "a class has no figure, or one is extra")
        files = set()
        for c, path in self.rec["classes"].items():
            f = os.path.basename(path)
            files.add(f)
            r = self.rec["files"].get(f) or {}
            self.assertEqual(r.get("class"), c, "%s's file is recorded as %r" % (c, r.get("class")))
            p = os.path.join(ROOT, path)
            self.assertTrue(os.path.isfile(p), "%s's figure is not shipped: %s" % (c, path))
            with open(p, "rb") as fh:
                self.assertEqual(hashlib.sha1(fh.read()).hexdigest(), r.get("sha1"), "%s's file is not the one recorded" % c)
            self.assertTrue(r.get("grokCold"), "%s's figure was wired without its cold look" % c)
        self.assertEqual(len(files), len(CLASSES), "two classes share one figure")

    def test_the_page_map_is_the_record(self):
        m = re.search(r"  var _CHX_CLASS_SPRITE = (\{[^\n]*\});", self.src)
        self.assertIsNotNone(m, "PREMISE: the page carries no class-figure map")
        self.assertEqual(json.loads(m.group(1)), self.rec["classes"], "the page's map drifted from tv/data/class_art.json")

    def test_both_cards_draw_through_the_one_helper(self):
        """a build card says whether it is the MAIN; an in-game card with no build never is"""
        self.assertEqual(self.src.count("'<div class=\"chx-top\">' + _chxCrest(b.cls, isMain)"), 1, "the build card draws its own crest")
        self.assertEqual(self.src.count("'<div class=\"chx-top\">' + _chxCrest(t.cls, false)"), 1, "the in-game card draws its own crest")
        self.assertNotIn("<span class=\"chx-crest\" aria-hidden=\"true\">' + esc(String(", self.src, "a card still draws a bare letter")

    @unittest.skipUnless(NODE, "node is required to run the page's helper - UNMEASURED without it")
    def test_the_helper_draws_the_figure_frames_a_main_and_keeps_an_unknown_letter(self):
        """* THE POINT"""
        i = self.src.index("  var _CHX_CLASS_SPRITE = ")
        j = self.src.index("\n  }\n", self.src.index("  function _chxCrest(cls, isMain){", i)) + 4
        js = ("var own = Object.prototype.hasOwnProperty;\n"
              "function esc(s){ return String(s == null ? '' : s).replace(/[&<>\"']/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',\"'\":'&#39;'}[c]; }); }\n"
              + self.src[i:j] + "\nprocess.stdout.write(JSON.stringify([_chxCrest('Sorceress', false), _chxCrest('paladin', true), "
              "_chxCrest('Monk', false), _chxCrest('', false)]));")
        r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        sorc, pal, monk, none = json.loads(r.stdout)
        self.assertIn('src="art/d2rw_cls_sorceress.webp"', sorc)
        self.assertNotIn("chx-crest-main", sorc, "a card that is not the MAIN wears the gold frame")
        self.assertIn('src="art/d2rw_cls_paladin.webp"', pal, "a class spelled in lower case found no figure")
        self.assertIn("chx-crest-main", pal, "the MAIN's figure has no gold frame")
        self.assertNotIn("<img", monk, "a class the map does not name drew another class's figure")
        self.assertIn(">M</span>", monk)
        self.assertIn(">?</span>", none)


RED_PROOF = [
    {"why": "v3887 (#154) - the in-game card draws its bare letter again",
     "file": "bible.html",
     "find": "      + '<div class=\"chx-top\">' + _chxCrest(t.cls, false)\n",
     "replace": "      + '<div class=\"chx-top\"><span class=\"chx-crest\" aria-hidden=\"true\">' + esc(String(t.cls || '?').charAt(0)) + '</span>'\n",
     "matches": 1},
    {"why": "v3887 (#154) - the MAIN loses its gold frame",
     "file": "bible.html",
     "find": "(isMain ? ' chx-crest-main' : '')",
     "replace": "('')",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main()
