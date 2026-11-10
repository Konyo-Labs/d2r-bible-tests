# -*- coding: utf-8 -*-
"""#23 (REG-3585) - ITEM MODS AND KEYWORDS WEAR THE GAME FACE THE NAMES ALREADY WEAR.

v3889 phase 1 put --ff-game on the game-NAME classes (item, zone, monster, boss). His 11-08 scope:
"anything game related.. like keywords for items and even maps and terror zones" and "just ingame
related stuff" - item mods / keywords were the names phase 1 missed (the set-tile affix list still
rendered in ui-monospace). Titles, headings and the console's own words stay as they are; no colour,
size or weight is touched (LOCKED_TYPE_SYSTEM). RED_PROOF below.
"""
import io
import os
import re
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
import js_strip  # noqa: E402

GAME_MODS = (".ct-affixes", ".ct-affixes li")


def _block(src):
    head = '<style id="v3889-game-face">'
    assert src.count(head) == 1, "PREMISE: the game-face stylesheet is gone or doubled (%d)" % src.count(head)
    i = src.index(head)
    return src[i:src.index("</style>", i)]


class GameModsWearTheGameFace(unittest.TestCase):

    def setUp(self):
        with io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8") as fh:
            self.src = fh.read()
        self.css = js_strip.strip_js_comments(_block(self.src))

    def test_item_mods_wear_the_game_face(self):
        found = set()
        for m in re.finditer(r"([^{}]+)\{font-family:var\(--ff-game\)!important\}", self.css):
            found.update(x.strip() for x in m.group(1).split(","))
        missing = [c for c in GAME_MODS if c not in found]
        self.assertEqual(missing, [], "these item mods/keywords lost the game face: %s" % missing)

    def test_the_block_still_sets_no_colour(self):
        props = set(re.findall(r"[{;]\s*([a-z-]+)\s*:", self.css))
        self.assertEqual(props - {"font-family", "--ff-game"}, set(),
                         "the theme block sets more than the face: %s" % sorted(props - {"font-family", "--ff-game"}))


RED_PROOF = [
    {"why": "REG-3585 - item affix lines lose the game face",
     "file": "bible.html",
     "find": ".ct-affixes,.ct-affixes li{font-family:var(--ff-game)!important}\n",
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
