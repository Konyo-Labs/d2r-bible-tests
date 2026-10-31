# -*- coding: utf-8 -*-
"""v3849 - a no-roll price 10x off the close-fit median is one quiet "n lines skipped".

The 3x rule still names a far price out loud. This one is extra and quiet: only posts that wrote a
roll set the middle, and only when at least three of them did. A post with no roll beyond 10x or
under a tenth of that middle is set aside and counted once on the price line.

A weak or unreadable key mod goes to the drawer with a reason and never weighs 1.00. A learned key
the posts priced, and a family's real key mod, still may.

Already guarded elsewhere, cited and re-checked by name:
  links per post — test_the_d2jsp_price_search_shows_its_posts_and_weighs_the_key_mods.py
  perfect tier and fleet merge — test_the_d2jsp_price_db_ages_weighs_and_merges.py
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
GT_LINES = ["+7 -5 4 41 27 15fg", "+7 -6 4 34 30 20fg", "+5 -8 3 37 29 20fg", "+6 -8 3 36 26 25fg",
            "+7 -7 4 42 23 25fg", "+8 -7 4 49 17 35fg", "+10 -6 3 30 30 100fg", "+8 -9 3 47 33 130fg",
            "+8 -9 4 40 28 140fg", "+8 -9 4 46 27 140fg", "+7 -10 4 33 29 390fg"]


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


def _page(lines, topic):
    body = "\n".join(lines)
    return 'Oct 12, 2026 <a href="topic.php?t=%s&amp;f=268">#1</a>\n%s' % (topic, body)


def _boot():
    desk, db = _desk_js()
    pages = {
        "gap": _page(["anni 20/20/10 1000fg", "anni 20/19/10 1000fg", "anni 19/20/10 1000fg"]
                     + ["anni 50fg"] * 5, "9101"),
        "one": _page(["anni 20/20/10 1000fg", "anni 20/19/10 1000fg", "anni 19/20/10 1000fg",
                      "anni 50fg"], "9102"),
        "shako": _page(["shako %d fg" % n for n in (100, 110, 120, 130, 140, 150, 160, 170, 180, 9000)], "9103"),
        "gt": _page(["guardian's thunder %s" % s for s in GT_LINES], "9104"),
    }
    body = r"""
var d = DBJSON; d.byName = {}; d.it.forEach(function(x){ d.byName[x[1].toLowerCase()] = d.byName[x[1].toLowerCase()] || x; });
d.anc = {}; Object.keys(d.ty).forEach(function(t){ var a = {}; (d.ty[t][4] || [t]).forEach(function(x){ a[x] = 1; }); d.anc[t] = a; });
var out = {};
out.gap = d2jspRead(PAGES.gap, "Annihilus", NOW);
out.one = d2jspRead(PAGES.one, "Annihilus", NOW);
out.shako = d2jspRead(PAGES.shako, "Harlequin Crest", NOW);
out.gt = d2jspRead(PAGES.gt, GT, NOW);
var reads = [{line: '+2 to Lightning Spells', pct: 80, lo: 1, hi: 2, warn: ''},
             {line: '+5 to Light Radius', pct: 40, lo: 1, hi: 5, warn: ''}];
var learnedPosts = [{fg: 50, w: 1, mods: ['lightning']}, {fg: 60, w: 1, mods: ['lightning', 'spells']}, {fg: 40, w: 1, mods: []}];
out.learned = d2jspModWeights(reads, 'Some Unknown Orb', learnedPosts);
out.even = d2jspModWeights(reads, 'Some Unknown Orb', []);
out.evenLine = d2jspTierLine(reads, 'Some Unknown Orb');
var specReads = [{line: 'a', pct: 100, lo: 0, hi: 10, warn: ''}, {line: 'b', pct: 100, lo: 0, hi: 10, warn: ''}];
var cq = {posts: [
  {fg: 100, w: 1, cols: [10, 10], day: '2026-10-01', link: 'https://forums.d2jsp.org/topic.php?t=1'},
  {fg: 110, w: 1, cols: [10, 10], day: '2026-10-02', link: 'https://forums.d2jsp.org/topic.php?t=2'},
  {fg: 5000, w: 1, cols: [999, -999], day: '2026-10-03', link: 'https://forums.d2jsp.org/topic.php?t=3'}]};
out.weak = d2jspColsPrice(cq, specReads, 'Some Unknown Orb');
out.weakHtml = d2jspEvidenceHtml(out.weak);
out.junk = d2jspAffixRead('hello there friend', d, GT);
out.junkLine = d2jspTierLine(out.junk, GT, null, 'Colossal Jewel');
var gtReads = d2jspAffixRead(HELD, d, GT);
out.family = d2jspModWeights(gtReads, GT, null, 'Colossal Jewel');
out.sim = d2jspSimilarPrice(out.gt, null, GT, gtReads);
process.stdout.write(JSON.stringify(out));
"""
    js = ("var window = {}, document = {};\n" + _quote_js()
          + "\nvar PAGES = " + json.dumps(pages) + ";\nvar NOW = " + json.dumps(NOW)
          + ";\nvar GT = " + json.dumps(GT) + ";\nvar HELD = " + json.dumps(HELD) + ";\n"
          + desk + "\nvar DBJSON = " + db + ";\n" + body)
    return _node(js)


class GrossOutlierIsQuiet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = _boot()
        cls.gap = D._public_fields(cls.raw["gap"], "Annihilus", NOW)
        cls.one = D._public_fields(cls.raw["one"], "Annihilus", NOW)
        cls.shako = D._public_fields(cls.raw["shako"], "Harlequin Crest", NOW)

    def _line(self, q):
        desk, _db = _desk_js()
        js = ("var window = {}, document = {};\n" + desk
              + "\nprocess.stdout.write(JSON.stringify(d2jspPriceLine(" + json.dumps(q) + ")));\n")
        return _node(js)

    def test_five_no_roll_lines_are_one_quiet_skip(self):
        q = self.gap
        self.assertEqual(q["reason"], "read")
        self.assertEqual(q["fg"], 1000, q)
        self.assertEqual(q.get("skipped"), 5)
        flat = [p for p in q["posts"] if p["fg"] == 50]
        rolled = [p for p in q["posts"] if p["fg"] == 1000]
        self.assertEqual(len(flat), 5)
        self.assertEqual(len(rolled), 3)
        for p in flat:
            self.assertEqual(p["w"], 0, p)
            self.assertFalse(p.get("out"), "a gross skip grew a loud reason: %r" % p)
        for p in rolled:
            self.assertGreater(p["w"], 0, p)
        line = self._line(q)
        self.assertEqual(line.count("5 lines skipped."), 1, line)
        self.assertNotIn("far from the middle", line)

    def test_one_such_line_is_singular(self):
        q = self.one
        self.assertEqual(q.get("skipped"), 1)
        self.assertEqual(q["fg"], 1000)
        line = self._line(q)
        self.assertIn("1 line skipped.", line)
        self.assertNotIn("lines skipped", line)

    def test_the_three_times_rule_still_names_the_shako_outlier(self):
        q = self.shako
        self.assertNotIn("skipped", q, "no close-fit roll, so the 10x rule must stay quiet")
        self.assertEqual((q["fg"], q["n"], q["low"], q["high"]), (140, 9, 100, 180), q)
        far = [p for p in q["posts"] if p["fg"] == 9000]
        self.assertEqual(len(far), 1)
        self.assertEqual(far[0]["w"], 0)
        self.assertIn("far from the middle", far[0].get("out") or "")
        line = self._line(q)
        self.assertNotIn("skipped", line)


class WeakKeyModNeverWeighsOne(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = GrossOutlierIsQuiet.raw if hasattr(GrossOutlierIsQuiet, "raw") else _boot()

    def test_no_family_weighs_a_quarter_and_says_why(self):
        even = self.raw["even"]
        self.assertEqual(even["from"], "even")
        self.assertEqual(even["why"], "no key-mod family to weigh")
        self.assertTrue(even["w"])
        self.assertTrue(all(w == 0.25 for w in even["w"]), even)
        self.assertNotIn(1, even["w"])
        self.assertIn("no key-mod family to weigh", self.raw["evenLine"])

    def test_a_key_the_posts_priced_still_weighs_one(self):
        self.assertEqual(self.raw["learned"]["from"], "posts")
        self.assertEqual(self.raw["learned"]["w"], [1, 0])

    def test_an_unreadable_column_is_set_aside_with_a_reason(self):
        rows = self.raw["weak"]["posts"]
        good = [r for r in rows if r.get("cols") == [10, 10]]
        bad = [r for r in rows if r.get("cols") == [999, -999]]
        self.assertEqual(len(good), 2)
        self.assertEqual(len(bad), 1)
        for r in good:
            self.assertEqual(r["w"], 0.25, r)
            self.assertNotEqual(r["w"], 1)
        self.assertEqual(bad[0]["w"], 0)
        self.assertIn("key mods could not be read", bad[0].get("out") or "")
        html = self.raw["weakHtml"]
        self.assertIn("set aside, key mods could not be read", html)
        self.assertNotIn("<td>1.00</td>", html)

    def test_an_unparsed_affix_is_in_the_drawer_and_not_weighed(self):
        junk = self.raw["junk"]
        self.assertEqual(len(junk), 1, junk)
        self.assertEqual(junk[0]["warn"], "could not be read")
        self.assertFalse(junk[0]["hi"] > junk[0]["lo"])
        self.assertEqual(self.raw["junkLine"], "Check: could not be read.")

    def test_a_real_family_key_still_weighs_one_and_the_thunder_fit_holds(self):
        fam = self.raw["family"]["w"]
        self.assertIn(1, fam, fam)
        self.assertIn(0, fam, fam)
        sim = self.raw["sim"]
        self.assertGreaterEqual(sim["fg"], 130, sim)
        self.assertGreater(sim["fit"], 230, sim)
        best = [r for r in sim["posts"] if r.get("cols") == [7, -10, 4, 33, 29]]
        self.assertEqual(len(best), 1)
        self.assertEqual(best[0]["out"], "")
        self.assertGreater(best[0]["w"], 0)


class AlreadyGuarded(unittest.TestCase):
    def test_links_perfect_tier_and_fleet_merge_already_have_laws(self):
        with open(os.path.join(HERE, "test_the_d2jsp_price_search_shows_its_posts_and_weighs_the_key_mods.py"),
                  encoding="utf-8") as fh:
            search = fh.read()
        with open(os.path.join(HERE, "test_the_d2jsp_price_db_ages_weighs_and_merges.py"), encoding="utf-8") as fh:
            db = fh.read()
        self.assertIn("def test_each_post_carries_its_link_day_and_roll", search)
        self.assertIn("def test_a_perfect_post_never_lifts_the_normal_price", db)
        self.assertIn("def test_the_quote_door_folds_the_reading_and_the_parser_carries_perfect", db)
        self.assertIn("def test_two_pcs_merge_into_one_db_either_way", db)


RED_PROOF = [
    {"why": "a no-roll price 10x off the close fit still moves the quote",
     "file": "functions/api/d2jsp_quote.js",
     "find": "    if (r.fg > mid * 10 || r.fg * 10 < mid) { r.w = 0; n++; }",
     "replace": "    if (false) { r.w = 0; n++; }",
     "matches": 1},
    {"why": "the skipped lines are not said on the price line",
     "file": "bible.html",
     "find": "  var nskip = Number(q.skipped), skip = nskip > 0 ? (' ' + nskip + (nskip === 1 ? ' line skipped.' : ' lines skipped.')) : '';",
     "replace": "  var nskip = 0, skip = '';",
     "matches": 1},
    {"why": "the public door drops the skip count",
     "file": "d2jsp_chrome.py",
     "find": "    if skipped > 0:\n        out[\"skipped\"] = skipped\n",
     "replace": "    if False:\n        out[\"skipped\"] = skipped\n",
     "matches": 1},
    {"why": "a weak key mod with no family weighs 1.00",
     "file": "bible.html",
     "find": "  return { from: 'even', family: null, why: 'no key-mod family to weigh', w: (reads || []).map(function () { return 0.25; }) };",
     "replace": "  return { from: 'even', family: null, why: 'no key-mod family to weigh', w: (reads || []).map(function () { return 1; }) };",
     "matches": 1},
    {"why": "an unreadable column weighs again and the drawer loses the reason",
     "file": "bible.html",
     "find": "    if (!r.read) { r.w = 0; if (!r.out) r.out = 'key mods could not be read'; return; }",
     "replace": "    if (!r.read) { r.w = r.w > 0 ? 0.05 : 0; return; }",
     "matches": 1},
    {"why": "a roll with no key mod weighs 1.00",
     "file": "bible.html",
     "find": "    if (!spec.some(function (m) { return m.key; }) && r.w > 0.25) r.w = 0.25;",
     "replace": "    if (false && r.w > 0.25) r.w = 0.25;",
     "matches": 1},
    {"why": "an unparsed affix line is dropped instead of shown",
     "file": "bible.html",
     "find": "    if (!any) { out.push({ line: t, value: null, lo: 0, hi: 0, pct: 0, warn: 'could not be read' }); return; }",
     "replace": "    if (!any) return;",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
