# -*- coding: utf-8 -*-
"""v3889 (#23, his theme pass) - IN-GAME TEXT WEARS THE GAME'S OWN FACE, AND NOTHING ELSE ON THE PAGE CHANGES.

His spec, 11-07: "a visual pass for the diablo ii fonts ... as they are within the d2r planner we extracted just like it
already renders for ADD ITEM ... colors still the same as they are currently no need to change. just the fonts"; narrowed
11-08 ~14:02: "maybe the titles and stuff should stay the same font they are now.. just ingame related stuff should have a
visual theme pass fix" - item names, zones and maps, terror zones, monsters and bosses.

MEASURED on the shipped page 11-09 (headless Chrome, computed style): the Quick wins place names (3,806) and the Best runs
names rendered in Inter, the boss names, item card titles and zone cards in the display serif. After: every one computes
to "D2 Exocet" (the builder's item face - local, else streamed from HIS install by the console, never this public repo),
falling back to the same display serif. The Grok CLI read the before/after crops cold: the names changed, every number,
label, "Run" and "TZ" did not, nothing clipped, no colour moved - and it caught the item card's badge going "UNIQUE" ->
"Unique" under a --sans exclusion: a console word inside a name keeps the face it HAD.

Held here without a browser (the pixels are the render gate's): the token, the list of game-name classes, a block that sets
the font and nothing else, the console words it leaves alone, the zone name wrapped apart from the words after it, and the
face itself never shipped from this repo. RED_PROOF below. [[visual-regression-detector]] [[copy-drift]]
"""
import io
import os
import re
import sys
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable   # it prints non-ASCII: never crash while REPORTING
    _enable()
except Exception:
    pass

#: the elements that hold a GAME NAME (item, zone, terror zone, monster, boss, runeword, set) - the theme's whole reach
GAME_NAMES = (".qw-name", ".f-rwbig", ".boss-name", ".fh-boss", ".gic-name", ".item-name", ".ct-name", ".tz-zone-name",
              ".tzt-z-name", ".rw-name", ".rwc-name", ".set-card-name", ".set-piece-name", ".statue-card-name",
              ".gic-char-name", ".gf-cname", ".qw-zone")
#: the console's own words beside or around a name - they keep their face (his "titles and stuff should stay")
NOT_GAME = (".f-atomact", ".qw-area", ".qw-sub", ".gq", ".gf-chip", ".qw-also-h", ".tab", ".tz-zone-tag")


def _bible():
    with io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8") as fh:
        return fh.read()


def _block(src):
    head = '<style id="v3889-game-face">'
    assert src.count(head) == 1, "PREMISE: the game-face stylesheet is gone or doubled (%d)" % src.count(head)
    i = src.index(head)
    return src[i:src.index("</style>", i)]


def _code(css):
    return re.sub(r"/\*.{0,4000}?\*/", "", css, flags=re.S)


class GameNamesWearTheGameFace(unittest.TestCase):

    def setUp(self):
        self.src = _bible()
        self.css = _code(_block(self.src))

    def test_the_token_is_the_builders_face_then_the_display_serif(self):
        self.assertIn(':root{--ff-game:"D2 Exocet",var(--serif-display)}', self.css,
                      "the game face no longer leads with the builder's own item face")
        self.assertIn('@font-face{font-family:"D2 Exocet";src:local("Exocet Blizzard OT")', self.src,
                      "PREMISE: the builder's D2 Exocet face is no longer declared - the token names a face nobody loads")

    def test_every_game_name_wears_it(self):
        """* THE POINT - each class that holds a game name is in the rule that sets the face"""
        m = re.search(r"([^{}]+)\{font-family:var\(--ff-game\)!important\}", self.css)
        self.assertTrue(m, "no rule sets the game face")
        sels = set(x.strip() for x in m.group(1).split(","))
        missing = [c for c in GAME_NAMES if c not in sels]
        self.assertEqual(missing, [], "these game names lost the game face: %s" % missing)

    def test_the_block_sets_the_font_and_nothing_else(self):
        """his 'colors still the same' and the locked type system: no colour, size, weight, spacing or case here"""
        props = set(re.findall(r"[{;]\s*([a-z-]+)\s*:", self.css))
        self.assertTrue(props, "PREMISE: no declaration read in the game-face block")
        self.assertEqual(props - {"font-family", "--ff-game"}, set(),
                         "the theme block sets more than the face: %s" % sorted(props - {"font-family", "--ff-game"}))

    def test_the_consoles_words_keep_their_face(self):
        m = re.search(r"([^{}]+)\{font-family:var\(--ff-game\)!important\}", self.css)
        self.assertTrue(m, "PREMISE: no rule sets the game face, so whom it spares cannot be read")
        sels = set(x.strip() for x in m.group(1).split(","))
        self.assertEqual([c for c in NOT_GAME if c in sels], [], "a console word was given the game face")
        self.assertIn(".gic-name .gic-grail-badge{font-family:var(--serif-display)!important}", self.css,
                      "the item card's Unique / Runeword badge lost the face it had (Grok CLI 11-09: 'UNIQUE' -> 'Unique')")

    def test_a_zone_name_is_wrapped_apart_from_the_words_after_it(self):
        """the area line reads 'Catacombs L4 · ~350 kills a run': only the zone is a game name"""
        self.assertEqual(self.src.count('<span class="qw-sub qw-area"><span class="qw-zone">'), 3,
                         "a Quick wins area line no longer wraps its zone name on its own")
        self.assertNotIn('<span class="qw-sub qw-area">\' + esc(', self.src, "an area line puts its zone and its words in one span again")

    def test_the_games_face_is_never_shipped_from_this_repo(self):
        """Exocet is Blizzard's: streamed from HIS install by the console, never committed, never served by the site"""
        out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.lower().split("\n")
        self.assertEqual([f for f in out if "exocet" in f and f.endswith((".otf", ".ttf", ".woff", ".woff2"))], [],
                         "the game's font file is tracked in a PUBLIC repo")


RED_PROOF = [
    {"why": "v3889 (#23) - the Quick wins place names lose the game face",
     "file": "bible.html",
     "find": ".qw-name,.f-rwbig,.boss-name,.fh-boss,.gic-name,.item-name,.ct-name,.tz-zone-name,.tzt-z-name,\n",
     "replace": ".f-rwbig,.boss-name,.fh-boss,.gic-name,.item-name,.ct-name,.tz-zone-name,.tzt-z-name,\n",
     "matches": 1},
    {"why": "v3889 (#23) - the game face is the page's sans again",
     "file": "bible.html",
     "find": ':root{--ff-game:"D2 Exocet",var(--serif-display)}',
     "replace": ":root{--ff-game:var(--sans)}",
     "matches": 1},
    {"why": "v3889 (#23) - the theme block recolours a name (his 'colors still the same')",
     "file": "bible.html",
     "find": ".gf-cname,.qw-zone{font-family:var(--ff-game)!important}",
     "replace": ".gf-cname,.qw-zone{font-family:var(--ff-game)!important;color:#fff}",
     "matches": 1},
    {"why": "v3889 (#23, the Grok CLI's catch) - the item card's badge is set in a face it never had",
     "file": "bible.html",
     "find": ".gic-name .gic-grail-badge{font-family:var(--serif-display)!important}",
     "replace": ".gic-name .gic-grail-badge{font-family:var(--sans)!important}",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
