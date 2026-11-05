# -*- coding: utf-8 -*-
"""REG-3206 (GrokBot v3864, 2026-11-05) - EVERY PICTURE THE CONSOLE CAN ASK /art/ FOR IS A FILE THAT SHIPS.

MEASURED by GrokBot on v3864: the guest console logged ~103 distinct /art/* 404s (boss, HD and gem keys) and 581 failed
requests; his Mac console's own network log showed no /art failure at all (its fails were 3 /hist 404s). Nothing in
the repo could say which art names the console can request, so a missing picture was found only on the glass.

tv/art_names.py reads them from the code that asks: the console's /art/ literals and its terror-zone composer, the
board's art/ literals (the console iframes it from /board) and its eleven composers, each expanded from the table that
feeds it, and the HD manifest the board folds in at runtime. Found that way on this tree: two names that were never in
art/ - UBER_BOSSES gave Korlic and Madawc `korlic-opt_graphic.png` / `madawc-opt_graphic.png`. The board's art table
already drew them as Korlic.gif / Madawc.gif, so UBER_BOSSES now names those files. And the guest's 404s had a
second cause: the guest refresh (tv/sync_guest_api.sh) shipped a new board.html every time and never the art it
names, so the guest kept an older art tree than its board. The refresh now ships art/ and checks the board's names
against it.

Held here:
  * every name is a file in art/, by exact case (a Mac's disk forgives case, the Linux guest and CI do not) - comments
    excepted, and only the two declared ones. On CI the checkout is a fresh clone, so there "in art/" IS "tracked by
    git", which is what every installer's clone ships (his Mac's art/ was measured identical to the tracked set the
    same day);
  * the enumerator is not blind: each feed finds at least its floor, and every art composer in the two pages is a
    door it knows (a new composer it does not expand is RED, not skipped);
  * the guest refresh ships art/ to the box and runs the check before it copies; the check exits 1 on a missing name.
Pure python: it reads two pages, the manifest and one listing of art/; the CLI's verdict is driven over fixture
trees of empty files named like the art. No browser, no network, no git. RED_PROOF below.
"""
import io
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import fixture_tmp as _fx  # noqa: E402
_fx.contain()
import art_names as A  # noqa: E402

ART = os.path.join(ROOT, "art")

#: names written only inside comments that are not files - each read, each harmless (no code asks for it)
COMMENT_ONLY_MISSING = {
    "d2io_sandersriprap.png": "bible.html v394 note: the crawled sprite was a blue gem and was dropped",
    "x.png": "bible.html v1643 note: an example url ('art/x.png?v=v1643') in the cache-stamp explanation",
}

#: each feed's floor, measured on this tree 2026-11-05 (found / floor): a parser that stops reading drops below it
FLOORS = {"console-literal": (55, 40), "board-literal": (2694, 2000), "manifest": (639, 600), "art-props": (18, 15),
          "tz-zone-art": (11, 8), "craft-slots": (9, 9), "branch-emblems": (2, 2), "base-map": (23, 20),
          "gems": (35, 35), "tz-info": (31, 25), "tab-icons": (17, 15), "boss-portraits": (12, 10),
          "console-tz-info": (31, 25)}


class EveryPictureIsAFileThatShips(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.found = A.names(ROOT)
        cls.gone = A.missing(cls.found, ART)

    def test_every_name_the_console_can_ask_for_is_in_art(self):
        gone = [n for n in self.gone if n not in self.found["commentOnly"]]
        print("   names the console can ask /art/ for: %d; not in art/: %r"
              % (len(self.found["names"]) - len(self.found["commentOnly"]), gone))
        self.assertEqual([], ["%s (asked by %s)" % (n, ", ".join(self.found["names"][n])) for n in gone],
                         "the console can ask /art/ for a picture art/ does not carry - it 404s")

    def test_only_the_declared_comment_mentions_are_excused(self):
        """A name is excused only when every mention of it is in a comment. If a CODE reference were misjudged as a
        comment, a new missing name would hide here - so the excused missing set must be exactly the declared one."""
        excused = sorted(set(self.gone) & set(self.found["commentOnly"]))
        self.assertEqual(sorted(COMMENT_ONLY_MISSING), excused,
                         "the set of missing names excused as comment-only moved: %r" % (excused,))

    def test_the_enumerator_is_not_blind(self):
        feeds = self.found["feeds"]
        low = dict((k, (feeds.get(k), floor)) for k, (_m, floor) in FLOORS.items() if (feeds.get(k) or 0) < floor)
        print("   feeds: %r" % (feeds,))
        self.assertEqual({}, low, "a feed read fewer names than its floor (found, floor): the check went blind")

    def test_every_art_composer_is_a_door_it_knows(self):
        doors = self.found["doors"]
        print("   art composers: %d (bible.html %d, console %d)"
              % (len(doors), sum(1 for d in doors if d["page"] == "bible.html"),
                 sum(1 for d in doors if d["page"] != "bible.html")))
        self.assertEqual([], ["%s:%d %s" % (d["page"], d["line"], d["text"]) for d in self.found["unknownDoors"]],
                         "a page composes an art url this check does not expand - its names are unchecked")
        self.assertGreaterEqual(len(doors), 13, "the composer census found fewer doors than this tree has")

    def test_the_two_ancients_draw_the_file_the_board_draws(self):
        """UBER_BOSSES only registers its picture when the board's art table has none, so the file it names must be
        the one D2IO_ART already draws for that name - never a second, absent one."""
        with io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8") as fh:
            b = fh.read()
        for nm in ("Korlic", "Madawc"):
            self.assertIn('"%s": "art/%s.gif"' % (nm, nm), b, "D2IO_ART no longer draws %s" % nm)
            m = re.search(r"\{ id:'%s', name:'%s', emoji:'[^']*', art:'([^']+)'" % (nm.lower(), nm), b)
            self.assertIsNotNone(m, "UBER_BOSSES lost %s" % nm)
            self.assertEqual("%s.gif" % nm, m.group(1), "UBER_BOSSES names %s a picture the board does not draw" % nm)


class TheGuestRefreshShipsTheArt(unittest.TestCase):

    def setUp(self):
        with io.open(os.path.join(HERE, "sync_guest_api.sh"), encoding="utf-8") as fh:
            raw = fh.read()
        # code only: a shell comment line, or a trailing ` # ...`, says nothing about what runs
        self.src = "\n".join(re.sub(r"\s+#\s.*$", "", l) for l in raw.split("\n") if not l.lstrip().startswith("#"))

    def test_the_box_copy_carries_art(self):
        self.assertEqual(1, self.src.count('BOX_ART="${GUEST_BOX_ART:-$BOX_PATH/art}"'), "the box art path is gone")
        i = self.src.find('if [ "$TO_BOX" = "1" ]; then')
        self.assertGreater(i, 0, "the copy-to-box branch is gone")
        branch = self.src[i:self.src.find("\nfi", i)]
        self.assertIn('rsync -a --delete "$REPO_ROOT/art/" "$BOX_HOST:$BOX_ART/"', branch,
                      "the refresh ships a new board and never the art it names")
        self.assertIn("rsync -a --delete --exclude '/art/' \"$OUT/\" \"$BOX_HOST:$BOX_PATH/\"", branch,
                      "the mirror copy's --delete would remove the box's art every refresh")

    def test_the_names_are_checked_before_the_copy(self):
        chk = self.src.find('python3 "$REPO_ROOT/tv/art_names.py" --board "$_board" --art "$REPO_ROOT/art"')
        cp = self.src.find('if [ "$TO_BOX" = "1" ]; then')
        self.assertGreater(chk, 0, "the refresh never checks the board's art names")
        self.assertLess(chk, cp, "the art check runs after the copy, when it can no longer say anything useful")

    def test_the_check_fails_on_a_missing_name_and_passes_on_the_full_tree(self):
        d = tempfile.mkdtemp(prefix="art_names_")
        try:
            found = A.names(ROOT)
            names = sorted(n for n in found["names"] if n not in found["commentOnly"])
            full, short = os.path.join(d, "full"), os.path.join(d, "short")
            os.makedirs(full)
            os.makedirs(short)
            for n in names:                           # the check reads names, not bytes: empty files stand in
                io.open(os.path.join(full, n), "wb").close()
                if n != names[0]:
                    io.open(os.path.join(short, n), "wb").close()
            self.assertEqual(1, A.main(["--art", short]), "the check passed an art tree that lacks %s" % names[0])
            self.assertEqual(0, A.main(["--art", full]), "the check failed a tree carrying every name")
        finally:
            shutil.rmtree(d, True)


RED_PROOF = [
    {"why": "REG-3206 - UBER_BOSSES names Korlic a picture that was never in art/ (the 404 found on this tree)",
     "file": "bible.html",
     "find": "art:'Korlic.gif',",
     "replace": "art:'korlic-opt_graphic.png',",
     "matches": 1},
    {"why": "REG-3206 - a console icon is renamed to a file art/ does not carry",
     "file": "tv/control_ui.html",
     "find": "    tz:        '/art/ui_tz.png',",
     "replace": "    tz:        '/art/ui_tz_glyph.png',",
     "matches": 1},
    {"why": "REG-3206 - a terror-zone key the console composes into /art/tz_<key>.jpg has no picture",
     "file": "tv/control_ui.html",
     "find": "\"Abaddon\":[800,85,\"act4-lava\"]",
     "replace": "\"Abaddon\":[800,85,\"act4-lavafield\"]",
     "matches": 1},
    {"why": "REG-3206 - the enumerator forgets the UBER_BOSSES composer, so its names go unchecked",
     "file": "tv/art_names.py",
     "find": "    (\"bible.html\", r\"art/' \\+ b\\.art\", \"art-props\"),                          # UBER_BOSSES\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3206 - the gem feed stops reading GEM_TYPES and the check goes blind to 35 pictures",
     "file": "tv/art_names.py",
     "find": "                out.append(\"gem_\" + slug + \".png\")\n",
     "replace": "                pass\n",
     "matches": 1},
    {"why": "REG-3206 - the guest refresh ships a new board and never the art it names",
     "file": "tv/sync_guest_api.sh",
     "find": "  rsync -a --delete \"$REPO_ROOT/art/\" \"$BOX_HOST:$BOX_ART/\" && echo \"  ✓ art copied\"",
     "replace": "  true && echo \"  ✓ art copied\"",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
