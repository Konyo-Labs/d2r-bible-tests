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

    def test_the_geared_map_is_the_manifest(self):
        """v3899 (#154) - the MAIN's geared figure per class is exactly art/class_geared.manifest.json's opened files"""
        m = re.search(r"  var _CHX_CLASS_GEARED = (\{[^\n]*\});", self.src)
        self.assertIsNotNone(m, "PREMISE: the page carries no geared-figure map")
        with io.open(os.path.join(os.path.dirname(HERE), "art", "class_geared.manifest.json"), encoding="utf-8") as fh:
            man = json.load(fh)
        self.assertEqual(json.loads(m.group(1)), dict((r["class"], "art/" + r["file"]) for r in man["classes"]),
                         "the page's geared map drifted from art/class_geared.manifest.json")

    def test_both_cards_draw_through_the_one_helper(self):
        """a build card says whether it is the MAIN; an in-game card with no build never is"""
        self.assertEqual(self.src.count("'<div class=\"chx-top\">' + _chxCrest(b.cls, isMain)"), 1, "the build card draws its own crest")
        self.assertEqual(self.src.count("'<div class=\"chx-top\">' + _chxCrest(t.cls, false)"), 1, "the in-game card draws its own crest")
        self.assertNotIn("<span class=\"chx-crest\" aria-hidden=\"true\">' + esc(String(", self.src, "a card still draws a bare letter")

    @unittest.skipUnless(NODE, "node is required to run the page's helper - UNMEASURED without it")
    def test_a_geared_figure_fits_its_crest_whole(self):
        """REG-3802 (#154) - MEASURED: the 38x89 geared GIF drew at 72x168 in the 76x76 crest (only its helm showed): the
        crest is a grid whose auto row took the img's own height. Its one track is definite, and a geared body is drawn at 1x."""
        self.assertIn(".chx-crest.chx-crest-sprite{width:76px;height:76px;border-radius:12px;overflow:hidden;padding:0;"
                      "grid-template:minmax(0,1fr)/minmax(0,1fr);", self.src, "the crest's grid row may size itself to its figure")
        self.assertIn("\n.chx-crest-sprite img.chx-geared{transform:none}\n", self.src,
                      "a geared figure is magnified past its crest again")

    def test_the_helper_draws_the_figure_frames_a_main_and_keeps_an_unknown_letter(self):
        """* THE POINT"""
        i = self.src.index("  var _CHX_CLASS_SPRITE = ")
        j = self.src.index("\n  }\n", self.src.index("  function _chxCrest(cls, isMain){", i)) + 4
        js = ("var own = Object.prototype.hasOwnProperty;\n"
              "function esc(s){ return String(s == null ? '' : s).replace(/[&<>\"']/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',\"'\":'&#39;'}[c]; }); }\n"
              + self.src[i:j] + "\nprocess.stdout.write(JSON.stringify([_chxCrest('Sorceress', false), _chxCrest('paladin', true), "
              "_chxCrest('Monk', false), _chxCrest('', false), _chxCrest('Warlock', true), _chxCrest('Paladin', false)]));")
        r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        sorc, pal, monk, none, wl_main, pal_card = json.loads(r.stdout)
        # v3899 (#154) - only a MAIN wears the geared figure, and a class with none (the Warlock) keeps its bare one
        self.assertIn('src="art/d2rw_cls_paladin.webp"', pal_card, "a card that is not the MAIN wears the geared figure")
        self.assertIn('src="art/d2rw_cls_warlock.webp"', wl_main, "a Warlock MAIN lost its figure (it has no geared one)")
        self.assertIn('src="art/d2rw_cls_sorceress.webp"', sorc)
        self.assertNotIn("chx-crest-main", sorc, "a card that is not the MAIN wears the gold frame")
        self.assertIn('src="art/d2cls_geared_paladin.gif"', pal, "a class spelled in lower case found no figure, or a MAIN "
                      "lost its geared figure (v3899 #154)")
        self.assertIn("chx-crest-main", pal, "the MAIN's figure has no gold frame")
        # REG-3802 (#154) - the geared figure is marked so it is drawn whole; a bare figure is not
        self.assertIn('<img class="chx-geared" src="art/d2cls_geared_paladin.gif"', pal, "the geared figure is not marked")
        self.assertNotIn("chx-geared", pal_card + wl_main + sorc, "a bare figure was marked geared")
        self.assertNotIn("<img", monk, "a class the map does not name drew another class's figure")
        self.assertIn(">M</span>", monk)
        self.assertIn(">?</span>", none)


RED_PROOF = [
    {"why": "v3899 (#154) - a MAIN draws its bare starting figure again, never its geared one",
     "file": "bible.html",
     "find": "    if (geared) src = _CHX_CLASS_GEARED[k];   /* v3899 (#154) - a MAIN, geared */\n",   # REG-3802 re-aimed
     "replace": "",
     "matches": 1, "needs": "node"},
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
    {"why": "REG-3802 (#154) - the crest's grid row sizes itself to a tall figure again (a MAIN shows only its helm)",
     "file": "bible.html",
     "find": "padding:0;grid-template:minmax(0,1fr)/minmax(0,1fr);border-color:",
     "replace": "padding:0;border-color:",
     "matches": 1},
    {"why": "REG-3802 (#154) - the geared figure is no longer marked, so it is magnified like the bare art",
     "file": "bible.html",
     "find": "(geared ? ' class=\"chx-geared\"' : '')",
     "replace": "('')",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main()
