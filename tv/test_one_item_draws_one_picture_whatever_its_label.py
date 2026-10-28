# -*- coding: utf-8 -*-
"""v3831 second eye, GrokBot #230 (REG-2847) - ONE ITEM DRAWS ONE PICTURE, WHATEVER LABEL NAMES IT AND WHEREVER IT IS DRAWN.

GrokBot measured on his live board that one unique drew different files on different surfaces:
  * Lightsabre: mr_lightsabre.png on a list card, while artUrl gives hd_lightsabre.png;
  * Goldstrike Arch: goldstrikearch_graphic.png on a card, while artUrl gives the long war bow;
  * the wishlist chip "Harlequin Crest (Shako)" drew mr_harlequincrestshako.png, and "Harlequin Crest" drew
    mr_harlequincrest.png.

What was measured here:
  * REG-2805 itself changed 308 pictures: 307 from a base sprite to the item's own icon, and 1 for REG-2806. None was a
    downgrade.
  * The two odd files are the board table's MID-BOOT values. Lightsabre is registered three times and Goldstrike Arch
    twice, across the board's scripts. The console copied that table as soon as it had keys (thArt), so it could keep a
    half-built copy for good. The console now asks the board's own artUrl once window._artTableReady says the table is
    finished, and copies only a finished table.
  * goldstrikearch_graphic.png depicts a pile of GOLD COINS, not the bow (opened, 100x100). The bow's base sprite is the
    honest picture, so the table no longer names that file for it.
  * Five uniques carried a second icon under a slot or base label: Harlequin Crest (Shako), Gull (dagger), Crescent Moon
    (amulet), Hellmouth (gloves) and The Hand of Broc (gloves). Two pairs are byte-identical. In the other three, the
    label's file is the same picture at twice the size. The label's icon is now the item's icon, so both names draw it. A
    runeword label is another item (REG-2806) and keeps its base.
Driven on the whole page in node and on the console's own thArt in node. RED_PROOF below.
"""
import io
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import vault_page_node as VPN  # noqa: E402

PAIRS = {"Harlequin Crest": "Harlequin Crest (Shako)", "Gull": "Gull (dagger)", "Crescent Moon": "Crescent Moon (amulet)",
         "Hellmouth": "Hellmouth (gloves)", "The Hand of Broc": "The Hand of Broc (gloves)"}
BODY = r"""
(function(){
var out = {}, labels = [];
Object.keys(D2IO_ART).forEach(function(k){
  var m = /^(.+?)\s*\([^)]*\)\s*$/.exec(k); if (!m) return;
  var t = (typeof ITEM_TIP !== 'undefined') ? ITEM_TIP[k] : null;
  if (!_keeperArt(m[1]) || (t && t.t === 'Runeword')) return;
  labels.push([k, m[1], artUrl(k), artUrl(m[1])]);
});
OUT.labels = labels;
OUT.pairs = {}; Object.keys(%s).forEach(function(b){ OUT.pairs[b] = [artUrl(b), artUrl(%s[b])]; });
OUT.ga = artUrl('Goldstrike Arch'); OUT.ready = window._artTableReady === true;
OUT.errors = H.errors.slice();
})();
""" % (json.dumps(PAIRS), json.dumps(PAIRS))


def _png_w(rel):
    with open(os.path.join(ROOT, rel), "rb") as f:
        head = f.read(24)
    return struct.unpack(">I", head[16:20])[0]


CONSOLE = r"""
var window = globalThis, BOARD = { D2IO_ART: { Lightsabre: 'art/mr_lightsabre.png', "The Cat's Eye": 'art/mr_thecatseye.png' }, _artTableReady: false,
  artUrl: function(n){ n = String(n).replace(/\u2019/g, "'"); return n === 'Lightsabre' ? 'art/hd_lightsabre.png' : (BOARD.D2IO_ART[n] || ''); } };
var document = { getElementById: function(id){ return id === 'tvd-eng' ? { contentWindow: BOARD } : null; } };
var LATER = []; function setTimeout(f){ LATER.push(f); }
function esc(s){ return String(s); }
%s
var out = {};
thArtInit(); out.midCopy = thArt('Lightsabre');                 /* the board is still building its table */
BOARD._artTableReady = true; BOARD.D2IO_ART.Lightsabre = 'art/hd_lightsabre.png';
var f; while ((f = LATER.shift())) f();
out.ready = thArt('Lightsabre');
out.fold = thArt('The Cat\u2019s Eye');   /* the board's resolver folds the apostrophe; an exact copy cannot */
BOARD._artTableReady = false; BOARD.artUrl = null; out.away = thArt('Lightsabre');   /* the board away: the finished copy */
process.stdout.write(JSON.stringify(out));
"""


def _console_block():
    s = io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()
    a = s.index("  var _HDART = null, _HDARTbusy = false;")
    b = s.index("  /* v2279 — PUBLISHED FOR THE SECOND SCRIPT BLOCK", a)
    return s[a:b]


class OneItemDrawsOnePictureWhateverItsLabel(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not VPN.NODE:
            raise AssertionError("node is not on this machine - this law does not skip")
        cls.o = VPN.run(BODY, timeout=300)
        r = subprocess.run([VPN.NODE, "-"], input=CONSOLE % _console_block(), capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise AssertionError("the console's thArt would not run in node: %s" % (r.stderr or r.stdout)[-1500:])
        cls.c = json.loads(r.stdout)
        cls.src = io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8").read()

    def test_the_page_booted_and_its_table_says_it_is_finished(self):
        self.assertEqual(self.o["__boot"]["errors"], [], self.o["__boot"])
        self.assertEqual(self.o["errors"], [])
        self.assertTrue(self.o["ready"], "the board never says its art table is finished")

    def test_every_label_of_a_unique_draws_the_uniques_picture(self):
        self.assertGreaterEqual(len(self.o["labels"]), 5, "PREMISE: almost no slot or base labels of a unique: %r" % self.o["labels"])
        split = [x for x in self.o["labels"] if x[2] != x[3]]
        self.assertEqual(split, [], "a label of a unique draws another picture than the unique: %r" % split)

    def test_the_picture_both_names_draw_is_the_larger_file(self):
        for bare, label in PAIRS.items():
            a, b = self.o["pairs"][bare]
            self.assertEqual(a, b, (bare, a, b))
            files = {"Harlequin Crest": ("art/mr_harlequincrest.png", "art/mr_harlequincrestshako.png"),
                     "Gull": ("art/mr_gull.png", "art/mr_gulldagger.png"),
                     "Crescent Moon": ("art/mr_crescentmoon.png", "art/mr_crescentmoonamulet.png"),
                     "Hellmouth": ("art/mr_hellmouth.png", "art/mr_hellmouthgloves.png"),
                     "The Hand of Broc": ("art/mr_thehandofbroc.png", "art/mr_thehandofbrocgloves.png")}[bare]
            self.assertIn(a, files, (bare, a))
            self.assertEqual(_png_w(a), max(_png_w(f) for f in files), "%s draws the smaller of its two icons: %s" % (bare, a))

    def test_goldstrike_arch_never_draws_the_coins(self):
        self.assertEqual(self.o["ga"], "art/hd_long_war_bow.png", self.o["ga"])
        code = re.sub(r"/\*.{0,4000}?\*/", "", self.src, flags=re.S)
        self.assertNotIn('"Goldstrike Arch": "art/goldstrikearch_graphic.png"', code,
                         "the art table names the gold-coins file for Goldstrike Arch again")

    def test_the_console_never_keeps_a_half_built_table(self):
        self.assertEqual(self.c["midCopy"], "", "the console drew the board's mid-boot picture: %r" % self.c)

    def test_the_console_asks_the_boards_own_resolver(self):
        self.assertEqual(self.c["ready"], "art/hd_lightsabre.png", self.c)
        self.assertEqual(self.c["fold"], "art/mr_thecatseye.png", "a label the board resolves another way drew nothing here: %r" % self.c)
        self.assertEqual(self.c["away"], "art/hd_lightsabre.png", "with the board away the console lost the finished copy: %r" % self.c)


RED_PROOF = [
    {"why": "REG-2847 - a unique's slot or base label keeps its own icon file apart from the unique's",
     "file": "bible.html",
     "find": "      if (!_KEEPER_ART.own[_lb]) _KEEPER_ART.icon[_lb] = _lu;                                   /* REG-2847 the label's icon is the item's */\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2847 - the art table names the gold-coins picture for Goldstrike Arch again",
     "file": "bible.html",
     "find": "  /* REG-2847 - \"Goldstrike Arch\" pointed at art/goldstrikearch_graphic.png, which is a picture of GOLD COINS (opened, 100x100),\n",
     "replace": "  \"Goldstrike Arch\": \"art/goldstrikearch_graphic.png\",\n  /* REG-2847 - \"Goldstrike Arch\" pointed at art/goldstrikearch_graphic.png, which is a picture of GOLD COINS (opened, 100x100),\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2847 - the board never says its table is finished",
     "file": "bible.html",
     "find": "  window._artTableReady = true;",
     "replace": "  void 0;",
     "matches": 1, "needs": "node"},
    {"why": "REG-2847 - the console copies the board's table mid-boot again",
     "file": "tv/control_ui.html",
     "find": "Object.keys(w.D2IO_ART).length && w._artTableReady === true){",
     "replace": "Object.keys(w.D2IO_ART).length){",
     "matches": 1, "needs": "node"},
    {"why": "REG-2847 - the console reads its own copy instead of the board's resolver",
     "file": "tv/control_ui.html",
     "find": "      if (_bw && _bw._artTableReady === true && typeof _bw.artUrl === 'function'){\n",
     "replace": "      if (false){\n",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
