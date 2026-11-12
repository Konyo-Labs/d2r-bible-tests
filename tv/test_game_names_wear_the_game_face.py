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
import js_strip  # noqa: E402  (one comment stripper for the laws - test_one_comment_stripper_for_the_laws)

#: the elements that hold a GAME NAME (item, zone, terror zone, monster, boss, runeword, set) - the theme's whole reach
GAME_NAMES = (".qw-name", ".f-rwbig", ".boss-name", ".fh-boss", ".gic-name", ".item-name", ".ct-name", ".tz-zone-name",
              ".tzt-z-name", ".rw-name", ".rwc-name", ".set-card-name", ".set-piece-name", ".statue-card-name",
              ".gic-char-name", ".gf-cname", ".qw-zone",
              # v3898 (#23 phase 2) - an inline name the board hangs hover art on, the names inside rows and cards that
              # carry the art on the row, and the game's mod lines
              "span[data-arttip]", "b[data-arttip]", ".item-tile-name", ".zd-su-card-name", ".er-it-name", ".hvf-name",
              ".iv-name", ".cn-name", ".cn-pv-opt-nm", ".arw-name", ".vm-item-name", ".zd-hg-name strong",
              ".cw-g-mod", ".cw-reroll-mod", ".hpbar-mods",
              # REG-3814 (#23) - a super-unique monster's name, measured in the console serif on a terror-zone card's line
              ".su-link",
              # REG-3814 (#23, the widened probe: 1,927 game names on 18 tabs) - the endgame road's key names
              ".rn-name")
#: v3898 - the console's own pieces INSIDE a name (a wall chip's tick, base, badge, qlvl and ETA, the TZ tag, the tier,
#: LADDER and stash badges, the runeword base's slot label, a button) - they keep the console's face
BADGES_IN_A_NAME = ("[data-arttip] .si-tier", "[data-arttip] .rwc-ladder", ".rwc-name .rwc-ladder", "[data-arttip] .gf-tick",
                    "[data-arttip] .gp-ck", "[data-arttip] .gq", "[data-arttip] .gp-q",
                    "[data-arttip] .tz-tag", "[data-arttip] .tvn-badge", "[data-arttip] .cw-ing-badge", ".rwd-base-t>b",
                    "[data-arttip] button", ".rw-ladder-tag")
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
    return js_strip.strip_js_comments(css)


class GameNamesWearTheGameFace(unittest.TestCase):

    def setUp(self):
        self.src = _bible()
        self.css = _code(_block(self.src))

    def test_the_token_is_the_builders_face_then_the_display_serif(self):
        self.assertIn(':root{--ff-game:"D2 Exocet",var(--serif-display)}', self.css,
                      "the game face no longer leads with the builder's own item face")

    def test_only_a_board_the_console_serves_asks_for_the_font(self):
        """v3889 round 2 (REG-3490): once every game name wears the face, its source is fetched on EVERY load. A url() in
        the board's stylesheet asked file:///api/d2r_font/exocet in every CI spec - 45 "no console errors" reds on
        5fd22f6b5 - and <the public site>/api/d2r_font/exocet on the live site, which has no such route. MEASURED 11-09
        (headless Chrome, a game name rendered): the old board asked file:///api/... and logged ERR_FILE_NOT_FOUND; the
        fixed one asks nothing as a file or from a static server's /bible.html, and asks /api/d2r_font/exocet at /board.
        Held here: the stylesheet's face has no url(), and the one url() lives in the loader that runs only for http on
        loopback at /board (the #223 condition - the console serves the board there and nowhere else)"""
        static = ('@font-face{font-family:"D2 Exocet";src:local("Exocet Blizzard OT"),local("ExocetBlizzardOT-Medium");'
                  'font-display:swap}')
        self.assertEqual(self.src.count(static), 1, "the board's own D2 Exocet face is not the local()-only rule")
        head = '<script id="v3889-game-font">'
        self.assertEqual(self.src.count(head), 1, "PREMISE: the console-only font loader is gone or doubled")
        i = self.src.index(head)
        loader = self.src[i:self.src.index("</script>", i)]
        code = js_strip.strip_js_comments(loader)
        for cond in ("String(L.protocol || '') !== 'http:'", "/^(127\\.0\\.0\\.1|localhost)(:\\d+)?$/.test(String(L.host || ''))",
                     "/^\\/+board\\/?$/.test(String(L.pathname || ''))"):
            self.assertIn(cond, code, "the font loader no longer waits for a board the console serves: %s" % cond)
        url = "url('/api/d2r_font/exocet')"
        self.assertIn(url, code, "the loader adds no source, so a console-served board never gets the face")
        at, outside = 0, []
        while True:
            at = self.src.find(url, at)
            if at < 0:
                break
            if not (i <= at < i + len(loader)):
                outside.append(self.src[max(0, at - 80):at + 40].replace("\n", " "))
            at += len(url)
        self.assertEqual(outside, [], "the font's url() is asked outside the console-only loader:\n  " + "\n  ".join(outside))
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
        # v3898 (#23 phase 2) - the console's pieces inside a game name keep the console's face
        b = re.search(r"([^{}]+)\{font-family:var\(--sans\)!important\}", self.css)
        self.assertTrue(b, "no rule gives the console's badges inside a name their own face back")
        spared = set(x.strip() for x in b.group(1).split(","))
        self.assertEqual([c for c in BADGES_IN_A_NAME if c not in spared], [],
                         "a console badge inside a game name took the game face")
        # a piece that sets its own face keeps it by itself; spared here it would wear --sans instead (11-11: "7h" mono->Inter)
        self.assertNotIn("[data-arttip] .gp-eta", spared, "the wall chip's ETA lost its own monospace face to the console sans")
        self.assertIn("font-family:var(--mono,monospace)}", self.src[self.src.index(".gf-piece .gp-eta{"):][:400],
                      "PREMISE: the wall chip's ETA no longer sets its own face, so it now needs sparing")

    def test_the_art_hook_dresses_inline_names_never_whole_rows(self):
        """v3898 (#23 phase 2) - MEASURED 11-11 over the source: 75 kinds of element carry data-arttip, and the div and td
        ones are whole rows and cards (a recipe row, a super-unique card, a crafts header with '0 / 9 make now'). The hook
        sets the face only where it sits on an inline name; a row's name takes it by its own name class"""
        m = re.search(r"([^{}]+)\{font-family:var\(--ff-game\)!important\}", self.css)
        self.assertTrue(m, "PREMISE: no rule sets the game face")
        sels = [x.strip() for x in m.group(1).split(",")]
        broad = [c for c in sels if "data-arttip" in c and not re.match(r"^(span|b)\[data-arttip\]$", c)]
        self.assertEqual(broad, [], "the art hook dresses more than an inline name - a whole row or card takes the game face")

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



class AMonsterNameInsideAThingOfTheirsIsNotLinked(unittest.TestCase):
    """REG-3814 (#23) - linkifySU wrapped EVERY occurrence of a super-unique's name, so the Tristram terror-zone line
    "Griswold (drops the Griswold's Legacy set)" linked the set name's first word too, and once the link took the game face
    the set name read in two faces ("GRISWOLD's Legacy"). A name followed by 's names a thing of theirs, never the monster."""

    def test_the_possessive_stays_plain_and_the_name_is_linked(self):
        from cb_node_harness import NODE
        if NODE is None:
            raise AssertionError("node is not installed on this PC - this law runs the shipped linker in node and does not skip")
        src = _bible()
        i = src.index("function linkifySU(str){")
        j = src.index("window.linkifySU=linkifySU;", i)
        js = ("var SUPER_UNIQUES = [{name: 'Griswold'}, {name: 'The Smith'}, {name: 'Nihlathak'}];\n" + src[i:j] +
              "\nprocess.stdout.write(JSON.stringify([linkifySU(\"Griswold (drops the Griswold's Legacy set)\"),"
              " linkifySU('The Smith and Nihlathak'), linkifySU('Griswold\u2019s Legacy'), linkifySU('nothing here')]));")
        r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-600:])
        gris, two, curly, none = __import__("json").loads(r.stdout)
        self.assertEqual(gris.count('class="su-link"'), 1, "a monster's name inside a thing of theirs was linked: %s" % gris)
        self.assertTrue(gris.endswith("(drops the Griswold's Legacy set)"), gris)
        self.assertEqual(two.count('class="su-link"'), 2, "BASELINE: two names in one line are both linked: %s" % two)
        self.assertNotIn("su-link", curly, "a curly-apostrophe possessive was linked")
        self.assertEqual(none, "nothing here")


class TheConsolesGameNamesToo(unittest.TestCase):
    """the console's half: its terror-zone names, hunt-history item and boss names, the cross-reference's item names and
    a shelf card's areas - in a monospace console whose own words keep their face"""

    CONSOLE_NAMES = (".tzz-top b", ".hh-name", ".hh-grail", ".hh-boss", ".fx-name", ".shc-area")

    def setUp(self):
        with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
            self.ui = fh.read()
        i = self.ui.index("/* v3889 (#23, his theme pass) - IN-GAME TEXT IN THE GAME'S OWN FACE, the console's half")
        self.css = _code(self.ui[i:self.ui.index("</style>", i)])

    def test_the_console_loads_the_face_from_its_own_route(self):
        self.assertIn("@font-face{font-family:\"D2 Exocet\";src:local(\"Exocet Blizzard OT\"),local(\"ExocetBlizzardOT-Medium\"),"
                      "url('/api/d2r_font/exocet') format('opentype')", self.css, "the console's game face has no source")
        self.assertIn(':root{--ff-game:"D2 Exocet",var(--serif)}', self.css)

    def test_its_game_names_wear_it_and_its_placeholder_does_not(self):
        m = re.search(r"([^{}]+)\{font-family:var\(--ff-game\)!important\}", self.css)
        self.assertTrue(m, "no console rule sets the game face")
        sels = set(x.strip() for x in m.group(1).split(","))
        self.assertEqual([c for c in self.CONSOLE_NAMES if c not in sels], [], "a console game name lost the face")
        self.assertIn(".tzz-pending .tzz-top b{font-family:inherit!important}", self.css,
                      "the zone card's 'not published yet' placeholder wears the game face")

    def test_the_console_block_sets_the_font_and_nothing_else(self):
        props = set(re.findall(r"[{;]\s*([a-z-]+)\s*:", self.css))
        self.assertEqual(props - {"font-family", "--ff-game", "src", "font-display"}, set(),
                         "the console's theme block sets more than the face: %s" % sorted(props))


RED_PROOF = [
    {"why": "v3898 (#23 phase 2) - the names phase 1's class list missed (an inline [data-arttip]) keep the console face again",
     "file": "bible.html",
     "find": ".gf-cname,.qw-zone,.rn-name,span[data-arttip],b[data-arttip],.item-tile-name,",
     "replace": ".gf-cname,.qw-zone,.item-tile-name,",
     "matches": 1},
    {"why": "v3898 (#23 phase 2) - a bare [data-arttip] dresses whole rows and cards (a crafts header's '0 / 9 make now')",
     "file": "bible.html",
     "find": ".gf-cname,.qw-zone,.rn-name,span[data-arttip],b[data-arttip],.item-tile-name,",
     "replace": ".gf-cname,.qw-zone,[data-arttip],.item-tile-name,",
     "matches": 1},
    {"why": "v3898 (#23 phase 2) - a wall chip's base type and badge ('Cap', 'unidentified') take the game face",
     "file": "bible.html",
     "find": "[data-arttip] .gp-ck,\n[data-arttip] .gq,[data-arttip] .gp-q,",
     "replace": "[data-arttip] .gp-ck,\n[data-arttip] .gp-q,",
     "matches": 1},
    {"why": "v3898 (#23 phase 2) - the wall chip's ETA is spared to the console sans and loses its own monospace face",
     "file": "bible.html",
     "find": "[data-arttip] .gq,[data-arttip] .gp-q,[data-arttip] .tz-tag,",
     "replace": "[data-arttip] .gq,[data-arttip] .gp-q,[data-arttip] .gp-eta,[data-arttip] .tz-tag,",
     "matches": 1},
    {"why": "v3898 (#23 phase 2) - the runeword base's slot label ('Weapon') takes the game face",
     "file": "bible.html",
     "find": "[data-arttip] .cw-ing-badge,.rwd-base-t>b,",
     "replace": "[data-arttip] .cw-ing-badge,",
     "matches": 1},
    {"why": "v3898 (#23 phase 2) - the tier and LADDER badges inside a name take the game face",
     "file": "bible.html",
     "find": "[data-arttip] .si-tier,[data-arttip] .rwc-ladder,.rwc-name .rwc-ladder,[data-arttip] .gf-tick,",
     "replace": "[data-arttip] .gf-tick,",
     "matches": 1},
    {"why": "v3889 round 2 (REG-3490) - the board's stylesheet asks for the font again on every page, file:// and the site",
     "file": "bible.html",
     "find": '@font-face{font-family:"D2 Exocet";src:local("Exocet Blizzard OT"),local("ExocetBlizzardOT-Medium");font-display:swap}',
     "replace": '@font-face{font-family:"D2 Exocet";src:local("Exocet Blizzard OT"),local("ExocetBlizzardOT-Medium"),url(\'/api/d2r_font/exocet\') format(\'opentype\');font-display:swap}',
     "matches": 1},
    {"why": "v3889 round 2 (REG-3490) - the font loader runs for any loopback page, so CI's static server asks it too",
     "file": "bible.html",
     "find": "    if (!/^\\/+board\\/?$/.test(String(L.pathname || ''))) return;\n",
     "replace": "",
     "matches": 1},
    {"why": "v3889 (#23) - the console's terror-zone names lose the game face",
     "file": "tv/control_ui.html",
     "find": ".tzz-top b,.hh-name,.hh-grail,.hh-boss,.fx-name,.shc-area{font-family:var(--ff-game)!important}",
     "replace": ".hh-name,.hh-grail,.hh-boss,.fx-name,.shc-area{font-family:var(--ff-game)!important}",
     "matches": 1},
    {"why": "v3889 (#23) - the console's 'not published yet' placeholder is set in the game face",
     "file": "tv/control_ui.html",
     "find": ".tzz-pending .tzz-top b{font-family:inherit!important}",
     "replace": ".tzz-pending .tzz-top b{}",
     "matches": 1},
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
     # v3898 re-anchored: phase 2 grew the selector list, this rule's last line is now the mod chips; REG-3814 adds .su-link
     "find": ".cw-g-mod,.cw-reroll-mod,.hpbar-mods,.su-link{font-family:var(--ff-game)!important}",
     "replace": ".cw-g-mod,.cw-reroll-mod,.hpbar-mods,.su-link{font-family:var(--ff-game)!important;color:#fff}",
     "matches": 1},
    {"why": "v3889 (#23, the Grok CLI's catch) - the item card's badge is set in a face it never had",
     "file": "bible.html",
     "find": ".gic-name .gic-grail-badge{font-family:var(--serif-display)!important}",
     "replace": ".gic-name .gic-grail-badge{font-family:var(--sans)!important}",
     "matches": 1},
    {"why": "REG-3814 (#23) - linkifySU links a monster's name inside a thing of theirs again (Griswold's Legacy in two faces)",
     "file": "bible.html",
     "find": "+\"(?![\\u2019']s\\\\b)\",'g');",
     "replace": "+\"\",'g');",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main()
