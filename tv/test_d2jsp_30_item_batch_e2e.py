# -*- coding: utf-8 -*-
"""v3849 - a 30-item d2jsp batch, fixtures only.

Cherry-picked from 792f6cfb7 (30 recorded posts: Shako, Annihilus, Guardian's Thunder) and
extended to 30 items. Each item comes back as a price headline or the words "none close".
Every priced post keeps a forums.d2jsp.org link. No network and no Chrome: node reads the
quote block and the desk block on stdin.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from console_safe import enable
enable()
import d2jsp_chrome as D  # noqa: E402

NODE = shutil.which("node")
NOW = "2026-10-30T07:00:00Z"
GT = "Guardian's Thunder"
HELD = ("Adds 1-75 lightning damage\n+10% to Lightning Skill Damage\n"
        "-9% to Enemy Lightning Resistance\n+3% to Experience Gained\n"
        "31% Extra Gold from Monsters\n20% Better Chance of Getting Magic Items")
FORUM = "https://forums.d2jsp.org/"

# Ten flat Shako prices. 9000 fg is the outlier (more than 3x the middle).
SHAKO = [100, 110, 120, 130, 140, 150, 160, 170, 180, 9000]
# Nine anni slash rolls. 15/15/5 at 5000 fg is the roll the fit must set aside.
ANNI = ["20/20/10 1200fg", "19/19/9 900fg", "18/18/8 700fg", "17/17/7 500fg", "16/16/6 400fg",
        "20/19/10 1100fg", "18/17/9 650fg", "15/15/5 5000fg", "19/20/10 1000fg"]
# Simsalara's compact columns, board 268, 2026-10-07. Eleven rows. The -10 at 390 fg stays,
# because the roll explains it.
GT_LINES = ["+7 -5 4 41 27 15fg", "+7 -6 4 34 30 20fg", "+5 -8 3 37 29 20fg", "+6 -8 3 36 26 25fg",
            "+7 -7 4 42 23 25fg", "+8 -7 4 49 17 35fg", "+10 -6 3 30 30 100fg", "+8 -9 3 47 33 130fg",
            "+8 -9 4 40 28 140fg", "+8 -9 4 46 27 140fg", "+7 -10 4 33 29 390fg"]

# 25 priced rows (Shako and its eth / 2os variants, Griffon's and a perf variant, then the trade list)
# and 5 rows asked with a roll the flat posts do not write, which must say "none close".
PRICED = [
    ("Harlequin Crest", "Harlequin Crest", "shako {n} fg"),
    ("shako eth", "Harlequin Crest", "shako eth {n} fg"),
    ("shako 2os", "Harlequin Crest", "shako 2os {n} fg"),
    ("Griffon's Eye", "Griffon's Eye", "griffons {n} fg"),
    ("griffons perf", "Griffon's Eye", "griffons perf {n} fg"),
    ("Annihilus", "Annihilus", "anni {n} fg"),
    ("Hellfire Torch", "Hellfire Torch", "torch {n} fg"),
    ("Stone of Jordan", "Stone of Jordan", "soj {n} fg"),
    ("Arachnid Mesh", "Arachnid Mesh", "arach {n} fg"),
    ("Mara's Kaleidoscope", "Mara's Kaleidoscope", "maras {n} fg"),
    ("War Traveler", "War Traveler", "war travs {n} fg"),
    ("Gore Rider", "Gore Rider", "gores {n} fg"),
    ("Herald of Zakarum", "Herald of Zakarum", "hoz {n} fg"),
    ("Crown of Ages", "Crown of Ages", "coa {n} fg"),
    ("Death's Fathom", "Death's Fathom", "fathom {n} fg"),
    ("Enigma", "Enigma", "nigma {n} fg"),
    ("Infinity", "Infinity", "infy {n} fg"),
    ("Call to Arms", "Call to Arms", "cta {n} fg"),
    ("Highlord's Wrath", "Highlord's Wrath", "highlords {n} fg"),
    ("Raven Frost", "Raven Frost", "raven {n} fg"),
    ("Nightwing's Veil", "Nightwing's Veil", "nightwing {n} fg"),
    ("Stormshield", "Stormshield", "stormshield {n} fg"),
    ("Windforce", "Windforce", "wf {n} fg"),
    ("Homunculus", "Homunculus", "homu {n} fg"),
    ("Andariel's Visage", "Andariel's Visage", "andy {n} fg"),
]
NONE_CLOSE = [
    ("shako 20/20 asked", "Harlequin Crest", "shako {n} fg"),
    ("griffons 20/20 asked", "Griffon's Eye", "griffons {n} fg"),
    ("anni flat", "Annihilus", "anni {n} fg"),
    ("soj flat", "Stone of Jordan", "soj {n} fg"),
    ("torch flat", "Hellfire Torch", "torch {n} fg"),
]


def _block(src, a, b):
    return src[src.index(a) + len(a):src.index(b)]


def _quote_js():
    with open(os.path.join(REPO, "functions", "api", "d2jsp_quote.js"), encoding="utf-8") as fh:
        return _block(fh.read(), "/* ⟦D2JSP QUOTE BEGIN⟧ */", "/* ⟦D2JSP QUOTE END⟧ */")


def _desk_js():
    with open(os.path.join(REPO, "bible.html"), encoding="utf-8") as fh:
        page = fh.read()
    desk = _block(page, "/* ⟦D2JSP DESK BEGIN⟧ */", "/* ⟦D2JSP DESK END⟧ */")
    db = re.search(r'<script[^>]*id="cb-db"[^>]*>([\s\S]*?)</script>', page).group(1).strip()
    return desk, db


def _node(js):
    if not NODE:
        raise AssertionError("node is not on this machine - this law does not skip")
    proc = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, encoding="utf-8", timeout=60)
    if proc.returncode != 0:
        raise AssertionError(proc.stderr[-2000:])
    return json.loads(proc.stdout)


def _page_30():
    """One fixture page, 30 priced lines, three items. Dates are inside the 120-day 2026 window."""
    shako = "\n".join("shako %d fg" % n for n in SHAKO)
    anni = "\n".join("anni %s" % s for s in ANNI)
    gt = "\n".join("guardian's thunder %s" % s for s in GT_LINES)
    return "\n".join([
        'Oct 12, 2026 <a href="topic.php?t=9001&amp;f=268">#1</a>',
        shako,
        'Oct 13, 2026 <a href="topic.php?t=9002&amp;f=268">#1</a>',
        anni,
        'Oct 7, 2026 <a href="topic.php?t=110445948&amp;f=268">#1</a>',
        gt,
    ])


def _parse(page, item):
    js = (_quote_js()
          + "\nprocess.stdout.write(JSON.stringify(d2jspRead(%s,%s,%s)));\n"
          % (json.dumps(page), json.dumps(item), json.dumps(NOW)))
    return D._public_fields(_node(js), item, NOW)


def _item_page(canon_line, fgs, topic0):
    lines = []
    for k, n in enumerate(fgs):
        lines.append('Oct %d, 2026 <a href="topic.php?t=%d&amp;f=268">#1</a>' % (10 + (k % 18), topic0 + k))
        lines.append(canon_line.format(n=n))
    return "\n".join(lines)


def _batch():
    """30 items. The first 25 are a tight price cluster. The last 5 are asked with a roll no post writes."""
    rows = []
    topic = 30000
    for i, (label, item, line) in enumerate(PRICED):
        fgs = [100 + i + k * 10 for k in range(5)]
        rows.append({"label": label, "item": item, "page": _item_page(line, fgs, topic),
                     "mine": None, "want": "headline"})
        topic += 10
    for label, item, line in NONE_CLOSE:
        rows.append({"label": label, "item": item, "page": _item_page(line, [80, 90, 100, 110, 120], topic),
                     "mine": [20, 20, 10], "want": "none close"})
        topic += 10
    desk, db = _desk_js()
    js = (
        "var window = {}, document = {};\n"
        + _quote_js()
        + "\n" + desk
        + "\nvar DBJSON = " + db + ";\n"
        + "var ROWS = " + json.dumps(rows) + ";\n"
        + "var NOW = " + json.dumps(NOW) + ";\n"
        + r"""
var out = ROWS.map(function (row) {
  var q = d2jspRead(row.page, row.item, NOW);
  var sim = row.mine ? d2jspSimilarPrice(q, row.mine, row.item) : null;
  var verdict = (row.mine && !(sim && sim.fg != null)) ? 'none close' : d2jspPriceLine(q);
  return { label: row.label, item: row.item, want: row.want, verdict: verdict,
           fg: q.fg, reason: q.reason, n: q.n,
           posts: (q.posts || []).map(function (p) { return { fg: p.fg, link: p.link || '', w: p.w }; }) };
});
process.stdout.write(JSON.stringify(out));
"""
    )
    return _node(js)


class ThirtyPostBatch(unittest.TestCase):
    """The 792f6cfb7 fixture: 30 posts, three items, the outlier set aside, the key-mod fit kept."""

    @classmethod
    def setUpClass(cls):
        page = _page_30()
        cls.n_lines = len(SHAKO) + len(ANNI) + len(GT_LINES)
        cls.shako = _parse(page, "Harlequin Crest")
        cls.anni = _parse(page, "Annihilus")
        cls.gt = _parse(page, GT)
        desk, db = _desk_js()
        body = (
            "var d = DBJSON; d.byName = {}; d.it.forEach(function(x){ d.byName[x[1].toLowerCase()] = d.byName[x[1].toLowerCase()] || x; });\n"
            "d.anc = {}; Object.keys(d.ty).forEach(function(t){ var a = {}; (d.ty[t][4] || [t]).forEach(function(x){ a[x] = 1; }); d.anc[t] = a; });\n"
            "var reads = d2jspAffixRead(%s, d, %s);\n"
            "var sim = d2jspSimilarPrice(%s, null, %s, reads);\n"
            "process.stdout.write(JSON.stringify({reads: reads, sim: sim}));\n"
            % (json.dumps(HELD), json.dumps(GT), json.dumps(cls.gt), json.dumps(GT))
        )
        cls.sim = _node("var window = {}, document = {};\n" + desk + "\nvar DBJSON = " + db + ";\n" + body)

    def test_the_batch_is_thirty_fixture_posts(self):
        self.assertEqual(self.n_lines, 30)
        got = len(self.shako["posts"]) + len(self.anni["posts"]) + len(self.gt["posts"])
        self.assertEqual(got, 30, "a fixture line was dropped or a foreign line was priced: %s %s %s"
                         % (len(self.shako["posts"]), len(self.anni["posts"]), len(self.gt["posts"])))

    def test_each_of_the_three_has_its_price(self):
        self.assertEqual(self.shako["reason"], "read")
        self.assertEqual((self.shako["fg"], self.shako["n"], self.shako["low"], self.shako["high"]),
                         (140, 9, 100, 180), self.shako)
        self.assertEqual(self.anni["reason"], "read")
        self.assertNotIn(5000, [p["fg"] for p in self.anni["posts"] if p["w"] > 0])
        kept = sorted(p["fg"] for p in self.anni["posts"] if p["w"] > 0)
        self.assertEqual(self.anni["fg"], kept[len(kept) // 2] if len(kept) % 2 else
                         int(round((kept[len(kept) // 2 - 1] + kept[len(kept) // 2]) / 2)))
        self.assertIn(1200, kept)
        self.assertLess(self.anni["fg"], 2000)
        self.assertEqual(self.gt["reason"], "read")
        self.assertEqual((self.gt["fg"], self.gt["n"], self.gt["low"], self.gt["high"]),
                         (35, 11, 15, 390), self.gt)

    def test_the_outlier_is_skipped_and_kept_in_the_evidence(self):
        far = [p for p in self.shako["posts"] if p["fg"] == 9000]
        self.assertEqual(len(far), 1)
        self.assertEqual(far[0]["w"], 0)
        self.assertIn("far from the middle", far[0]["out"])
        self.assertNotIn(9000, [p["fg"] for p in self.shako["posts"] if p["w"] > 0])
        roll = [p for p in self.anni["posts"] if p["fg"] == 5000]
        self.assertEqual(len(roll), 1)
        self.assertEqual(roll[0]["w"], 0)
        self.assertIn("does not explain", roll[0]["out"])

    def test_the_key_mod_fit_keeps_the_roll_that_explains_its_price(self):
        sim = self.sim["sim"]
        self.assertTrue(sim.get("cols"), "the compact columns were not priced by roll: %r" % sim)
        self.assertGreaterEqual(sim["fg"], 130, "the key-mod price fell back to the plain middle 35: %r" % sim)
        self.assertGreater(sim["fit"], 230, "the fit at +10/-9 is not above the plain middle: %r" % sim["fit"])
        rows = sim["posts"]
        best = [r for r in rows if r.get("cols") == [7, -10, 4, 33, 29]]
        self.assertEqual(len(best), 1, rows)
        self.assertEqual(best[0]["out"], "", "the -10 at 390 fg was set aside though its roll explains it")
        self.assertGreater(best[0]["w"], 0)
        w = dict((tuple(r["cols"]), r["w"]) for r in rows if r.get("cols"))
        nine = [w[(8, -9, 3, 47, 33)], w[(8, -9, 4, 40, 28)], w[(8, -9, 4, 46, 27)]]
        low = w[(7, -5, 4, 41, 27)]
        self.assertGreater(min(nine), low * 2, "a -9 key roll does not outweigh the -5 row: %r" % w)

    def test_each_of_those_posts_keeps_its_forum_link(self):
        for name, q, topic in (("shako", self.shako, "9001"), ("anni", self.anni, "9002"), ("gt", self.gt, "110445948")):
            self.assertGreater(len(q["posts"]), 0, name)
            for p in q["posts"]:
                self.assertTrue(str(p.get("link") or "").startswith(FORUM + "topic.php?t=" + topic),
                                "%s lost its forum link: %r" % (name, p))


class ThirtyItemBatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = _batch()

    def test_the_batch_is_thirty_items_from_fixtures(self):
        self.assertEqual(len(self.rows), 30)
        self.assertEqual(len(PRICED) + len(NONE_CLOSE), 30)
        labels = [r["label"] for r in self.rows]
        for needle in ("Harlequin Crest", "shako eth", "shako 2os", "Griffon's Eye", "griffons perf"):
            self.assertIn(needle, labels)

    def test_each_item_is_a_price_headline_or_none_close(self):
        for row in self.rows:
            if row["want"] == "none close":
                self.assertEqual(row["verdict"], "none close", row["label"])
                continue
            self.assertNotEqual(row["verdict"], "none close", row["label"])
            self.assertEqual(row["reason"], "read", row["label"])
            self.assertIn("fg", row["verdict"], row)
            self.assertIn(str(row["fg"]), row["verdict"], row)

    def test_every_post_keeps_its_forum_link(self):
        for row in self.rows:
            self.assertGreaterEqual(len(row["posts"]), 5, row["label"])
            for p in row["posts"]:
                link = str(p.get("link") or "")
                self.assertTrue(link.startswith(FORUM + "topic.php?t="), "%s dropped a link: %r" % (row["label"], p))
                self.assertIn("f=268", link)


RED_PROOF = [
    {"why": "a price three times off the middle still moves the quote",
     "file": "functions/api/d2jsp_quote.js",
     "find": "    if (r.fg > mid * 3 || r.fg * 3 < mid) { r.w = 0; r.out = 'far from the middle ' + mid + ' fg'; }",
     "replace": "    if (false) { r.w = 0; r.out = 'far from the middle ' + mid + ' fg'; }",
     "matches": 1},
    {"why": "a post's forum link is dropped on the way out",
     "file": "functions/api/d2jsp_quote.js",
     "find": "  return 'https://forums.d2jsp.org/' + h.replace(/^\\/+/, '');\n",
     "replace": "  return '';\n",
     "matches": 1},
    {"why": "a roll nobody wrote still prices as a close fit",
     "file": "bible.html",
     "find": "  return { posts: rows, fg: mine && like ? d2jspWeightedMiddle(rows) : null, like: like };",
     "replace": "  return { posts: rows, fg: d2jspWeightedMiddle(rows), like: like };",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
