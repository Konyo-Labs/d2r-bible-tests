# -*- coding: utf-8 -*-
"""v3895 (#91, REG-3591) - THE ART MAP NAMES EACH ITEM ONCE, AND ONE MONSTER IS ONE PICTURE.

D2IO_ART held 21 duplicate keys (set pieces mostly, plus Nihlathak and The
Summoner). In JavaScript the later assignment silently wins, so a first edit
changed a key that did not count (REG-3315 left this for #91). Every key now
appears once. Bloodwitch the Wild, Lord De Seis and Treehead WoodFist each
have one sourced animated GIF (the leftover visual pass of #91). Hell Bovine
wears Elad's gamepedia Hell Bovine (Diablo II).gif; The Countess wears
gamepedia's The Countess (Diablo II).gif. Mephisto wears Elad's File:Mephisto.gif
and Baal wears File:Baal_D2.gif (both format=original, real GIF bytes — Wikia
had served WebP under a .gif name). File:Cow.gif is recorded as unused.

MONSTER_PICTURE in bible.html is the one map every renderer reads. A monster
cannot have two different picture paths in the shipped pages or the portrait
manifest. RED_PROOF below.
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
import art_names  # noqa: E402

BIBLE = os.path.join(HERE, "..", "bible.html")
ROOT = os.path.join(HERE, "..")

LEFTOVER = (
    ("Bloodwitch the Wild", "art/d2mon_Bloodwitch_the_Wild.gif"),
    ("Lord De Seis", "art/d2mon_Lord_De_Seis.gif"),
    ("Treehead WoodFist", "art/d2mon_Treehead_WoodFist.gif"),
    ("Hell Bovine", "art/d2mon_Hell_Bovine.gif"),
    ("The Countess", "art/d2mon_The_Countess.gif"),
)

# Elad's supplied GIFs (and The Summoner, unified onto the sprite D2IO_ART already drew).
# These must stay original animated GIF bytes, never a still PNG or a WebP named .gif.
ELAD_GIFS = (
    ("Mephisto", "art/d2mon_Mephisto.gif"),
    ("Baal", "art/d2mon_Baal.gif"),
    ("The Summoner", "art/d2mon_The_Summoner.gif"),
    ("Nihlathak", "art/d2mon_Nihlathak.gif"),
    ("Andariel", "art/d2mon_Andariel.gif"),
    ("Duriel", "art/d2mon_Duriel.gif"),
    ("Diablo", "art/d2mon_Diablo.gif"),
    ("Lilith", "art/d2mon_Lilith.gif"),
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
            sid = qw_id.get(name)
            if sid:
                self.assertEqual(su.get(sid), path.split("/")[-1],
                                 "Quick wins %s must name the same file as the board" % sid)
        d2 = dict(_pairs())
        self.assertEqual(d2.get("Hell Bovines"), "art/d2mon_Hell_Bovine.gif")
        self.assertEqual(d2.get("Hell Bovines (Cow Level)"), "art/d2mon_Hell_Bovine.gif")
        block = re.search(r"var BOSS_PORTRAIT = \{(.*?)\n  \}", src, re.S).group(1)
        portraits = dict(re.findall(r"([a-z]+):\s*'([^']+)'", block))
        self.assertEqual(portraits.get("cows"), "d2mon_Hell_Bovine.gif",
                         "the cow tile must render the animated GIF, not the old portrait")
        self.assertEqual(d2.get("The Countess"), "art/d2mon_The_Countess.gif")
        self.assertEqual(portraits.get("countess"), "d2mon_The_Countess.gif",
                         "the Countess tile must render the animated GIF, not the old portrait")
        rec_by_name = dict((r["name"], r) for r in rec["sprites"])
        self.assertIn("Hell_Bovine", rec_by_name["Hell Bovine"]["url"])
        self.assertIn("diablo_gamepedia", rec_by_name["Hell Bovine"]["url"])
        self.assertIn("The_Countess", rec_by_name["The Countess"]["url"])
        unused = [r for r in rec.get("rejected") or []
                  if r.get("name") == "Hell Bovine" and (r.get("file") or "") == "Cow.gif"]
        self.assertTrue(unused, "File:Cow.gif must stay recorded as unused")
        self.assertEqual(list(rec.get("noSpriteFound") or []), [],
                         "the leftover #91 names must not remain noSpriteFound")



def _monster_picture(src=None):
    if src is None:
        with open(BIBLE, encoding="utf-8") as fh:
            src = fh.read()
    i = src.index("const MONSTER_PICTURE = {")
    return dict(re.findall(r'"([^"]+)":\s*"(art/[^"]+)"', src[i:src.index("};", i)]))


def _is_gif(path, name):
    full = path if os.path.isabs(path) else os.path.join(ROOT, path)
    with open(full, "rb") as fh:
        raw = fh.read()
    magic = raw[:6]
    if magic not in (b"GIF87a", b"GIF89a"):
        raise AssertionError("%s must stay an animated GIF (not a still PNG or WebP named .gif), got %r" % (name, magic))
    try:
        from PIL import Image
        with Image.open(full) as im:
            if im.format != "GIF" or getattr(im, "n_frames", 1) < 2:
                raise AssertionError("%s is not an animated GIF (format=%s frames=%s)" % (name, im.format, getattr(im, "n_frames", 1)))
            return raw, im.size, im.n_frames
    except ImportError:
        if raw.count(b"\x21\xF9\x04") < 1:
            raise AssertionError("%s lost its animation" % name)
        return raw, None, None


# Filename stems that depict the monster itself, not an item, an uber variant, or a zone.
_EXCLUDE_BITS = (
    "visage", "shell", "shooves", "cowking", "aldiabol", "torbaal", "dulmephist",
    "uberdiablo", "diablo_hell", "diablo_icon", "tv_diablo", "baallair",
)
_EXCLUDE_PREFIX = ("mr_", "hd_", "hdx_", "tz_", "d2arreat_")
_STEM_TO_MONSTER = (
    ("The Countess", ("countess",)),
    ("Mephisto", ("mephisto",)),
    ("Baal", ("baal",)),
    ("Diablo", ("diablo",)),
    ("Andariel", ("andariel",)),
    ("Duriel", ("duriel",)),
    ("Nihlathak", ("nihlathak",)),
    ("The Summoner", ("summoner",)),
    ("Bloodwitch the Wild", ("bloodwitch",)),
    ("Lord De Seis", ("deseis", "de_seis", "lord_de_seis")),
    ("Treehead WoodFist", ("treehead",)),
    ("Hell Bovine", ("hell_bovine", "hellbovine")),
    ("Grand Vizier of Chaos", ("grand_vizier", "grandvizier")),
    ("Infector of Souls", ("infector",)),
    ("Oblivion Knight", ("oblivion_knight",)),
    ("Doom Knight", ("doom_knight",)),
    ("Venom Lord", ("venom_lord",)),
    ("Storm Caster", ("storm_caster",)),
    ("Abyss Knight", ("abyss_knight",)),
    ("Pit Lord", ("pit_lord",)),
    ("Doom Caster", ("doom_caster",)),
    ("Strangler", ("strangler",)),
)
_FILE_IN_QUOTES = re.compile(
    r"""['\"](?:/?art/)?([A-Za-z0-9_.-]+\.(?:png|gif|jpe?g|webp))['\"]""", re.I
)


def _classify(fname):
    """Which of the twelve monsters does this file depict, or None if it is something else."""
    base = re.sub(r"\.(png|gif|jpe?g|webp)$", "", fname.split("/")[-1].split("?")[0].lower())
    if base.startswith(_EXCLUDE_PREFIX) or any(bit in base for bit in _EXCLUDE_BITS):
        return None
    if "mephisto" in base and "key" in base:
        return None
    if base == "cow":
        return None
    for name, keys in _STEM_TO_MONSTER:
        if any(k in base for k in keys):
            return name
    return None


def _norm(path):
    f = path.split("?")[0].replace("\\", "/")
    if f.startswith("/art/"):
        f = f[1:]
    if not f.startswith("art/"):
        f = "art/" + f.split("/")[-1]
    return f


def _paths_in_page(path):
    """Live (non-comment) picture paths in a shipped page, classified by monster. -> dict"""
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    found = {}
    for m in _FILE_IN_QUOTES.finditer(src):
        if art_names.in_comment(src, m.start()):
            continue
        name = _classify(m.group(1))
        if not name:
            continue
        line = src.count("\n", 0, m.start()) + 1
        found.setdefault(name, []).append((_norm(m.group(0).strip("\"'")), os.path.relpath(path, ROOT), line))
    return found


class NoMonsterHasTwoPicturePaths(unittest.TestCase):
    """REG-3591 - a monster has ONE picture, unified everywhere it renders.

    MONSTER_PICTURE is the source of truth. D2IO_ART, BOSS_PORTRAIT, the NOW ON AIR
    stage, baked <img> tags, the boss-portrait manifest and the sprite record must
    all name that same file. A second path for the same monster is the Countess
    still (countess01_graphic.png on the NOW ON AIR stage) all over again.
    """

    REQUIRED = (
        "Andariel", "Baal", "Diablo", "Duriel", "Mephisto", "Nihlathak",
        "The Summoner", "The Countess", "Bloodwitch the Wild", "Lord De Seis",
        "Treehead WoodFist", "Hell Bovine",
    )

    def test_the_map_names_each_monster_once(self):
        with open(BIBLE, encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("const MONSTER_PICTURE = {", src, "the one-picture map is gone")
        pics = _monster_picture(src)
        missing = [n for n in self.REQUIRED if n not in pics]
        self.assertEqual(missing, [], "MONSTER_PICTURE is missing: %s" % missing)
        self.assertEqual(len(pics), len(set(pics)), "MONSTER_PICTURE repeats a name")

    def test_elad_gifs_stay_original_animated_gif_bytes(self):
        pics = _monster_picture()
        for name, path in ELAD_GIFS + LEFTOVER:
            self.assertEqual(pics.get(name), path, "%s's map entry is not %s" % (name, path))
            _is_gif(path, name)

    def test_no_monster_has_two_different_picture_paths(self):
        pics = _monster_picture()
        by = {n: [] for n in self.REQUIRED}
        for name in pics:
            by.setdefault(name, [])
        # the map itself
        for name, path in pics.items():
            if name in by:
                by[name].append((path, "bible.html", "MONSTER_PICTURE"))
        # shipped pages
        for rel in ("bible.html", os.path.join("tv", "control_ui.html")):
            for name, hits in _paths_in_page(os.path.join(ROOT, rel)).items():
                if name in by:
                    by[name].extend(hits)
        # structured portrait manifest (not the historical _why prose)
        with open(os.path.join(ROOT, "art", "boss_portraits.manifest.json"), encoding="utf-8") as fh:
            man = json.load(fh)
        id_to_name = {
            "andariel": "Andariel", "mephisto": "Mephisto", "baal": "Baal", "diablo": "Diablo",
            "duriel": "Duriel", "nihl": "Nihlathak", "summoner": "The Summoner",
            "countess": "The Countess", "cows": "Hell Bovine",
        }
        for row in man["portraits"]:
            name = id_to_name.get(row["bossId"])
            if name:
                by[name].append((_norm(row["file"]), "art/boss_portraits.manifest.json", "portraits"))
        with open(os.path.join(ROOT, "tv", "data", "monster_art_fandom.json"), encoding="utf-8") as fh:
            rec = json.load(fh)
        for row in rec["sprites"]:
            name = row.get("name")
            if name in by and row.get("file"):
                by[name].append((_norm(row["file"]), "tv/data/monster_art_fandom.json", "sprites"))

        split = {}
        for name, hits in by.items():
            paths = sorted(set(p for p, _w, _l in hits))
            want = pics[name]
            if paths != [want]:
                split[name] = {"want": want, "found": paths, "where": hits}
        if split:
            lines = []
            for name, info in split.items():
                lines.append("%s should be %s, found %s" % (name, info["want"], info["found"]))
                for path, where, line in info["where"]:
                    if path != info["want"]:
                        lines.append("  %s:%s %s" % (where, line, path))
            self.fail("a monster has two different picture paths:\n  " + "\n  ".join(lines))
        for name in self.REQUIRED:
            self.assertTrue(by[name], "no shipped renderer names a picture for %s" % name)

        pics = _monster_picture()
        self.assertEqual(pics.get("Lilith"), "art/d2mon_Lilith.gif")
        self.assertEqual(pics.get("Uber Duriel"), "art/d2arreat_duriel.gif")
        self.assertNotEqual(pics.get("Andariel"), pics.get("Lilith"), "Andariel and Lilith must not share a picture")
        self.assertNotEqual(pics.get("Duriel"), pics.get("Uber Duriel"), "Duriel and Uber Duriel must not share a picture")


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
    {"why": "v3895 (#91, REG-3591) - Hell Bovine lost its sourced sprite",
     "file": "bible.html",
     "find": '  "Hell Bovine": "art/d2mon_Hell_Bovine.gif",\n',
     "replace": "",
     "matches": 1},
    {"why": "v3895 (#91, REG-3591) - The Countess lost its sourced sprite",
     "file": "bible.html",
     "find": '  "The Countess": "art/d2mon_The_Countess.gif",\n',
     "replace": "",
     "matches": 1},
    {"why": "v3895 (#91, REG-3591) - the NOW ON AIR stage paints The Countess with a second, still picture",
     "file": "bible.html",
     "find": "    { re:/(forgotten tower|tower cellar)/i,       name:'The Countess' }",
     "replace": "    { re:/(forgotten tower|tower cellar)/i,       name:'The Countess', art:'art/countess01_graphic.png' }",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
