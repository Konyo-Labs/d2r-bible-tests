# -*- coding: utf-8 -*-
"""#154 - A MAIN HAS A GEARED FIGURE OF ITS OWN CLASS: AN ANIMATED IN-GAME SPRITE IN ARMOUR, OPENED BEFORE IT SHIPPED
(v3899, REG-3971, GrokBot on a grok/ branch).

tv/data/class_art.json gives each class its bare starting-outfit idle loop and said "no site serves a geared variant per
class (measured 11-08)". diablo-archive.fandom.com's Diablo II build pages carry in-game GIFs of geared characters for seven
of the eight classes. art/class_geared.manifest.json pins each one (what it depicts, sha256, source page and file URL, the
licence the source states) and names the eighth, the Warlock, under "none" with the reason - a class with no geared
sprite says NONE instead of borrowing another class's figure or a still.

Not wired here: bible.html and the console are untouched; Claude wires the card. RED_PROOF below.
"""
import hashlib
import io
import json
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MANIFEST = os.path.join(ROOT, "art", "class_geared.manifest.json")
CLASS_ART = os.path.join(HERE, "data", "class_art.json")


def _load(p):
    with io.open(p, encoding="utf-8") as fh:
        return json.load(fh)


def _gif_frames(b):
    """frames in a GIF, by walking its blocks (header, colour tables, extensions, image descriptors) - enough to tell a loop
    from a still without PIL (CI and the ALTs do not all carry it). -> int (0 for anything that is not a GIF)"""
    if len(b) < 13 or not b.startswith(b"GIF8"):
        return 0
    i = 13 + ((3 << ((b[10] & 7) + 1)) if b[10] & 0x80 else 0)
    n = 0
    while i < len(b):
        t = b[i]
        if t == 0x3B:                                   # trailer
            break
        if t == 0x21:                                   # extension: label, then sub-blocks
            i += 2
        elif t == 0x2C:                                 # image descriptor (+ local table, LZW min size), then sub-blocks
            n += 1
            f = b[i + 9]
            i += 10 + ((3 << ((f & 7) + 1)) if f & 0x80 else 0) + 1
        else:
            return n
        while i < len(b) and b[i]:
            i += b[i] + 1
        i += 1
    return n


class AMainHasAGearedFigurePerClass(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.man = _load(MANIFEST)
        cls.rows = cls.man.get("classes") or []
        cls.none = dict((k, v) for k, v in (cls.man.get("none") or {}).items() if not k.startswith("_"))
        cls.classes = sorted(set(v["class"] for v in _load(CLASS_ART)["files"].values()))

    def test_every_class_has_a_geared_figure_or_says_none(self):
        self.assertGreaterEqual(len(self.classes), 8, "PREMISE: class_art.json names too few classes")
        have = set(r["class"] for r in self.rows)
        unsaid = [c for c in self.classes if c not in have and c not in self.none]
        self.assertEqual(unsaid, [], "a class has no geared figure and the manifest does not say NONE: %s" % unsaid)
        both = sorted(have & set(self.none))
        self.assertEqual(both, [], "a class is both pictured and declared NONE: %s" % both)
        for c, why in self.none.items():
            self.assertGreater(len(why), 60, "%s is declared NONE without saying what was searched" % c)

    def test_each_figure_is_the_animated_bytes_that_were_opened(self):
        bad = []
        for r in self.rows:
            p = os.path.join(ROOT, "art", r["file"])
            if not os.path.isfile(p):
                bad.append("%s: art/%s is not shipped" % (r["class"], r["file"]))
                continue
            with open(p, "rb") as fh:
                b = fh.read()
            if hashlib.sha256(b).hexdigest() != r.get("sha256") or len(b) != r.get("bytes"):
                bad.append("%s: art/%s is not the file that was opened (sha256/bytes)" % (r["class"], r["file"]))
            if not b.startswith(b"GIF8") or _gif_frames(b) < 2:
                bad.append("%s: art/%s is not an animated GIF" % (r["class"], r["file"]))
        self.assertEqual(bad, [], "\n".join(bad))

    def test_each_figure_is_its_own_and_not_the_bare_loop(self):
        seen, bad = {}, []
        bare = set()
        for f in _load(CLASS_ART)["files"]:
            p = os.path.join(ROOT, "art", f)
            if os.path.isfile(p):
                with open(p, "rb") as fh:
                    bare.add(hashlib.sha256(fh.read()).hexdigest())
        for r in self.rows:
            s = r.get("sha256")
            if s in seen:
                bad.append("%s and %s wear one picture" % (seen[s], r["class"]))
            seen[s] = r["class"]
            if s in bare:
                bad.append("%s's geared figure is a bare starting loop" % r["class"])
            if r["class"].lower() not in r["file"].lower():
                bad.append("%s's file %s does not name its class" % (r["class"], r["file"]))
        self.assertEqual(bad, [], "\n".join(bad))

    def test_each_figure_says_what_it_shows_where_it_came_from_and_its_licence(self):
        bad = []
        for r in self.rows:
            if len(r.get("depicts") or "") < 60:
                bad.append("%s: no description of what was SEEN" % r["class"])
            for k in ("url", "page"):
                if not str(r.get(k) or "").startswith("https://"):
                    bad.append("%s: no source %s" % (r["class"], k))
            if len(r.get("licence") or "") < 40:
                bad.append("%s: no stated licence" % r["class"])
        self.assertEqual(bad, [], "\n".join(bad))


RED_PROOF = [
    {"why": "#154 - the Amazon's geared figure is not the file that was opened",
     "file": "art/class_geared.manifest.json",
     "find": "\"sha256\": \"1b6c37ba8b3b",
     "replace": "\"sha256\": \"006c37ba8b3b",
     "matches": 1},
    {"why": "#154 - the Warlock has no geared figure and nothing says NONE",
     "file": "art/class_geared.manifest.json",
     "find": "\"none\": {\n    \"Warlock\": ",
     "replace": "\"none\": {\n    \"_Warlock\": ",
     "matches": 1},
    {"why": "#154 - the Sorceress's row borrows the Amazon's figure",
     "file": "art/class_geared.manifest.json",
     "find": "\"file\": \"d2cls_geared_sorceress.gif\"",
     "replace": "\"file\": \"d2cls_geared_amazon.gif\"",
     "matches": 1},
    {"why": "#154 - a figure ships with no stated licence",
     "file": "art/class_geared.manifest.json",
     "find": "Javazon.gif/revision/latest?format=original\",\n      \"licence\": \"No licence on the file page",
     "replace": "Javazon.gif/revision/latest?format=original\",\n      \"licence\": \"\", \"_was\": \"No licence on the file page",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
