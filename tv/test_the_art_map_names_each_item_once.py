# -*- coding: utf-8 -*-
"""v3895 (#91, REG-3591) - THE ART MAP NAMES EACH ITEM ONCE.

D2IO_ART held 21 duplicate keys (set pieces mostly, plus Nihlathak and The
Summoner). In JavaScript the later assignment silently wins, so a first edit
changed a key that did not count (REG-3315 left this for #91). Every key now
appears once. Bloodwitch the Wild, Lord De Seis and Treehead WoodFist each
have one sourced animated GIF (the leftover visual pass of #91); The Countess
and Hell Bovine remain noSpriteFound.
RED_PROOF below.
"""
import json
import os
import re
import sys
import unittest
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _enable  # noqa: E402
_enable()

BIBLE = os.path.join(HERE, "..", "bible.html")
ROOT = os.path.join(HERE, "..")

LEFTOVER = (
    ("Bloodwitch the Wild", "art/d2mon_Bloodwitch_the_Wild.gif"),
    ("Lord De Seis", "art/d2mon_Lord_De_Seis.gif"),
    ("Treehead WoodFist", "art/d2mon_Treehead_WoodFist.gif"),
)


def _pairs():
    with open(BIBLE, encoding="utf-8") as fh:
        src = fh.read()
    i = src.index("const D2IO_ART = {")
    chunk = src[i:src.index("\n};", i)]
    return re.findall(r'^\s*"([^"]+)":\s*"([^"]+)"', chunk, re.M)


class TheArtMapNamesEachItemOnce(unittest.TestCase):

    def test_no_name_is_written_twice(self):
        pairs = _pairs()
        keys = [k for k, _v in pairs]
        dups = sorted(k for k, n in Counter(keys).items() if n > 1)
        self.assertEqual(dups, [], "D2IO_ART repeats a name (the later silently wins): %s" % dups)
        self.assertGreaterEqual(len(keys), 500, "premise: the art map shrank too far (%d)" % len(keys))

    def test_the_three_leftover_monsters_have_one_sourced_animated_gif(self):
        """Each leftover now wears one shipped animated GIF, named once, not a still PNG or WebP-as-gif."""
        by = {}
        for k, v in _pairs():
            by.setdefault(k.lower(), set()).add(v)
        rec_path = os.path.join(HERE, "data", "monster_art_fandom.json")
        with open(rec_path, encoding="utf-8") as fh:
            rec = json.load(fh)
        rec_by = dict((r["name"], r) for r in rec["sprites"])
        missing = set(rec.get("noSpriteFound") or [])
        with open(BIBLE, encoding="utf-8") as fh:
            src = fh.read()
        su = dict(re.findall(r"(su_\w+):\s*'([^']+)'",
                             re.search(r"var _QW_SU_ART = \{(.*?)\};", src, re.S).group(1)))
        qw_id = {
            "Bloodwitch the Wild": "su_bloodwitchthewild",
            "Lord De Seis": "su_lorddeseis",
            "Treehead WoodFist": "su_treeheadwoodfist",
        }
        for name, path in LEFTOVER:
            files = by.get(name.lower(), set())
            self.assertEqual(files, {path}, "%s must name exactly one sprite: %s" % (name, files))
            full = os.path.join(ROOT, path)
            self.assertTrue(os.path.isfile(full), "%s's file is not shipped: %s" % (name, path))
            with open(full, "rb") as fh:
                raw = fh.read()
            magic = raw[:6]
            self.assertIn(magic, (b"GIF87a", b"GIF89a"),
                          "%s must stay an animated GIF (not a still PNG or WebP named .gif), got %r" % (name, magic))
            try:
                from PIL import Image
                with Image.open(full) as im:
                    self.assertEqual(im.format, "GIF")
                    self.assertGreaterEqual(getattr(im, "n_frames", 1), 2, "%s is not animated" % name)
            except ImportError:
                self.assertGreaterEqual(raw.count(b"\x21\xF9\x04"), 1,
                                        "%s lost its animation" % name)
            self.assertNotIn(name, missing, "%s is still listed as noSpriteFound" % name)
            self.assertIn(name, rec_by, "%s has no sprite record" % name)
            self.assertEqual(rec_by[name]["file"], path)
            self.assertTrue(rec_by[name].get("url", "").startswith("https://"),
                            "%s's sprite has no source URL" % name)
            sid = qw_id[name]
            self.assertEqual(su.get(sid), path.split("/")[-1],
                             "Quick wins %s must name the same file as the board" % sid)


RED_PROOF = [
    {"why": "v3895 (#91, REG-3591) - Wilhelm's Pride is listed twice again (the later silently wins)",
     "file": "bible.html",
     "find": '  "Wilhelm\'s Pride": "art/wilhelmspride_graphic.png",\n',
     "replace": '  "Wilhelm\'s Pride": "art/wilhelmspride_graphic.png",\n'
                '  "Wilhelm\'s Pride": "art/wilhelmspride_graphic.png",\n',
     "matches": 1},
    {"why": "v3895 (#91, REG-3591) - Bloodwitch the Wild lost its sourced sprite",
     "file": "bible.html",
     "find": '  "Bloodwitch the Wild": "art/d2mon_Bloodwitch_the_Wild.gif",\n',
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
