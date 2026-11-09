"""v3844 - THE D2JSP PRICE SEARCH, ITS EVIDENCE AND THE KEY MODS (Elad, 2026-10-30 00:40/00:41).
1. A PRICE SEARCH bar on the desk prices anything a trader types ("anni 20/20/10", "40/15 shako", "jmod") from d2jsp
   posts dated 2026 or later on board 268 only, and nothing is posted.
2. Every quote carries an EVIDENCE DRAWER: each post the price came from - its link, day, fg, the roll as read and its
   weight - so a price can be rechecked by hand. The post's own words stay on the forum; the link opens them.
3. The roll tier is MOD-WEIGHTED per item family: key mods dominate and filler counts nothing. A Guardian's Thunder
   jewel with +10% lightning skill damage and -9% enemy lightning resistance reads near-perfect on its key mods, though
   its gold find, magic find and experience drag the plain mean down. A family with no defaults learns its weights from
   the mods the 2026 posts priced it on. Posts like yours are weighed by the same weights.
4. Annihilus read 18 fg over 5-2000: another item's price on a shared line, and a bundle, priced it. Only a clause that
   names the item counts, and a price over three times off the middle is set aside (kept in the evidence)."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
NODE = shutil.which("node")
NOW = "2026-10-29T12:00:00.000Z"


def _read(*p):
    with open(os.path.join(REPO, *p), encoding="utf-8") as f:
        return f.read()


def _block(src, a, b):
    return src[src.index(a) + len(a):src.index(b)]


def _node(prog):
    out = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        raise AssertionError(out.stderr[:2000])
    return json.loads(out.stdout)


ANNI_PAGE = "<br>".join([
    '<a href="topic.php?t=111&amp;f=268">WTS anni</a> Oct 20, 2026',
    "Anni 20/20/10 - 18 fg",
    '<a href="/topic.php?t=222">FT</a> Oct 21, 2026',
    "anni 5 ist, pc 2000 fg, torch 300 fg",
    "Anni 19/18/7 15fg",
    "Anni 20/20/9 20 fg",
    "anni 17/15/5 12 fg",
    "Anni 20/20/10 2000 fg bundle",
    "Shako 1,500 fg, anni 22 fg",
])


@unittest.skipIf(NODE is None, "node is not on this machine")
class TheQuoteKeepsItsPosts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parser = _block(_read("functions", "api", "d2jsp_quote.js"), "/* ⟦D2JSP QUOTE BEGIN⟧ */", "/* ⟦D2JSP QUOTE END⟧ */")
        body = "var out = {};\n"
        body += "out.anni = d2jspRead(%s, 'Annihilus', %s);\n" % (json.dumps(ANNI_PAGE), json.dumps(NOW))
        body += "out.y2025 = d2jspRead('Dec 30, 2025\\nShako 300 fg', 'Harlequin Crest', '2026-01-05T10:00:00.000Z');\n"
        body += "out.y2026 = d2jspRead('Jan 2, 2026\\nShako 300 fg', 'Harlequin Crest', '2026-01-05T10:00:00.000Z');\n"
        body += "process.stdout.write(JSON.stringify(out));"
        cls.out = _node(parser + "\n" + body)

    def test_annihilus_is_priced_by_its_own_clauses_and_a_far_price_is_set_aside(self):
        a = self.out["anni"]
        self.assertEqual(a["reason"], "read")
        self.assertEqual((a["low"], a["high"], a["n"]), (12, 22, 5), "another item's price or a bundle priced Annihilus")
        self.assertNotIn(300, [p["fg"] for p in a["posts"]], "the torch's price on a shared line priced Annihilus")
        far = [p for p in a["posts"] if p["fg"] == 2000]
        self.assertEqual(len(far), 1, "a set-aside price must stay in the evidence")
        self.assertEqual(far[0]["w"], 0)
        self.assertIn("far from the middle", far[0]["out"])

    def test_each_post_carries_its_link_day_and_roll(self):
        p = self.out["anni"]["posts"]
        self.assertEqual(p[0]["link"], "https://forums.d2jsp.org/topic.php?t=111&f=268")
        self.assertEqual(p[0]["day"], "2026-10-20")
        self.assertEqual(p[0]["roll"], [[20, 20, 10]])
        self.assertEqual(p[1]["link"], "https://forums.d2jsp.org/topic.php?t=222")

    def test_only_2026_posts_price_it(self):
        self.assertEqual(self.out["y2025"]["reason"], "no prices", "a 2025 post priced it")
        self.assertEqual(self.out["y2026"]["fg"], 300)

    def test_the_console_passes_the_evidence_but_never_the_page(self):
        import d2jsp_chrome
        parsed = dict(self.out["anni"])
        parsed["posts"] = parsed["posts"] + [{"fg": 9, "w": 1, "link": "https://evil.example/x", "line": "SECRET PAGE TEXT"}]
        got = d2jsp_chrome._public_fields(parsed, "Annihilus", NOW)
        self.assertEqual(len(got["posts"]), len(parsed["posts"]))
        self.assertEqual(got["posts"][-1]["link"], "", "a link off the forum was passed to the desk")
        self.assertNotIn("SECRET PAGE TEXT", json.dumps(got))
        self.assertNotIn("Anni 20/20/10", json.dumps(got), "the page's words rode out with the evidence")
        self.assertEqual(d2jsp_chrome._public_fields({"reason": "no prices", "posts": [{"fg": 3}]}, "x", NOW)["posts"], [])


@unittest.skipIf(NODE is None, "node is not on this machine")
class TheDeskWeighsTheKeyMods(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        page = _read("bible.html")
        cls.page = page
        desk = _block(page, "/* ⟦D2JSP DESK BEGIN⟧ */", "/* ⟦D2JSP DESK END⟧ */")
        db = re.search(r'<script[^>]*id="cb-db"[^>]*>([\s\S]*?)</script>', page).group(1).strip()
        body = r"""
var d = DBJSON; d.byName = {}; d.it.forEach(function(x){ d.byName[x[1].toLowerCase()] = d.byName[x[1].toLowerCase()] || x; });
d.anc = {}; Object.keys(d.ty).forEach(function(t){ var a = {}; (d.ty[t][4] || [t]).forEach(function(x){ a[x] = 1; }); d.anc[t] = a; });
var out = {};
var gt = d2jspAffixRead("+10% to Lightning Skill Damage\n-9% to Enemy Lightning Resistance\n+26% Extra Gold from Monsters\n16% Better Chance of Getting Magic Items\n+3% to Experience Gained", d, "Guardian's Thunder");
out.gtEven = d2jspTierLine(gt);
out.gtLine = d2jspTierLine(gt, "Guardian's Thunder", null, 'Colossal Jewel');
out.gtAvg = d2jspTierAvg(gt, "Guardian's Thunder");
out.gtPrice = d2jspTierPrice({reason: 'read', fg: 180, low: 100, high: 1100}, out.gtAvg);
var reads = [{line: '+2 to Lightning Spells', pct: 100, lo: 1, hi: 2}, {line: '+5 to Light Radius', pct: 0, lo: 1, hi: 5}];
var posts = [{fg: 50, w: 1, mods: ['lightning']}, {fg: 60, w: 1, mods: ['lightning', 'spells']}, {fg: 40, w: 1, mods: []}];
out.learned = d2jspModWeights(reads, 'Some Unknown Orb', posts);
out.even = d2jspModWeights(reads, 'Some Unknown Orb', []);
var q = {reason: 'read', posts: [
  {fg: 18, w: 1, roll: [[20, 20, 10]], day: '2026-10-20', link: 'https://forums.d2jsp.org/topic.php?t=1'},
  {fg: 12, w: 1, roll: [[17, 15, 5]], day: '2026-10-21', link: 'https://forums.d2jsp.org/topic.php?t=2'},
  {fg: 20, w: 1, roll: [[20, 20, 9]], day: '2026-10-21', link: ''},
  {fg: 2000, w: 0, roll: [[20, 20, 10]], day: '2026-10-21', link: '', out: 'far from the middle 18 fg'}]};
out.sim = d2jspSimilarPrice(q, [20, 20, 10], 'Annihilus');
out.ev = d2jspEvidenceHtml(out.sim);
out.evBad = d2jspEvidenceHtml(d2jspSimilarPrice({posts: [{fg: 5, w: 1, roll: [], day: '<img>', link: 'https://forums.d2jsp.org/"onmouseover="x'}]}, null, 'X'));
out.evBare = d2jspEvidenceHtml(null, {reason: 'read', item: 'Enigma', posts: [{fg: 2000, w: 1, day: '2026-11-02', link: 'https://forums.d2jsp.org/topic.php?t=9', roll: []}], aside: [{why: 'no fg price on the line', day: '2026-11-01', link: 'https://forums.d2jsp.org/topic.php?t=8'}]});
out.evNone = d2jspEvidenceHtml(null, {reason: 'no prices', item: 'Enigma', posts: [], aside: [{why: 'no fg price on the line', day: '2026-11-01', link: 'https://forums.d2jsp.org/topic.php?t=8'}]});
out.search = [d2jspParseSearch('anni 20/20/10'), d2jspParseSearch('40/15 shako'), d2jspParseSearch('jmod'), d2jspParseSearch('torch sorc 18/18 eth 2os')];
out.searchBare = [d2jspParseSearch('shako 141'), d2jspParseSearch('arach 3os'), d2jspParseSearch('griffon 12 15')];
out.searchLine = d2jspSearchLine({reason: 'read', fg: 18, low: 12, high: 20, n: 3, board: 268}, out.sim, out.search[0]);
out.searchLineDb = d2jspSearchLine({reason: 'read', fg: 50, low: 15, high: 100, n: 11, board: 268,
  db: {normal: {fg: 40, n: 15}, perfect: {fg: 80, n: 2}}}, null, {item: 'shako', roll: null});
process.stdout.write(JSON.stringify(out));
"""
        cls.out = _node("var window = {}, document = {};\n" + desk + "\nvar DBJSON = " + db + ";\n" + body)

    def test_guardians_thunder_reads_near_perfect_on_its_key_mods(self):
        self.assertIn("Roll tier: low, 38% up the rolls", self.out["gtEven"], "PREMISE: the plain mean is dragged down")
        self.assertEqual(self.out["gtLine"],
                         "Roll tier: near-perfect on the key mods 10% / -9%, 90% weighted; 38% across all 5 mods read.")
        self.assertGreaterEqual(self.out["gtAvg"], 85)
        self.assertIn("near-perfect roll", self.out["gtPrice"])

    def test_a_family_with_no_defaults_learns_from_the_posts(self):
        l = self.out["learned"]
        self.assertEqual(l["from"], "posts")
        self.assertEqual(l["w"], [1, 0], "the mod the posts priced on did not dominate")
        self.assertEqual(self.out["even"]["from"], "even")

    def test_posts_like_yours_are_weighed_and_a_set_aside_post_stays_out(self):
        s = self.out["sim"]
        self.assertEqual(s["like"], 3)
        self.assertEqual(s["fg"], 18)
        w = [p["w"] for p in s["posts"]]
        self.assertGreater(w[0], w[1], "a closer roll did not weigh more")
        self.assertEqual(w[3], 0)
        self.assertIn("Posts like 20/20/10: about 18 fg from 3 posts.", self.out["searchLine"])

    def test_with_the_items_price_below_the_read_line_names_no_second_price(self):
        """v3881 (GrokBot's v3878 pass, #96: "middle 50 from 11 prices" above "40 fg from 15 posts" - two prices, one item)"""
        line = self.out["searchLineDb"]
        self.assertEqual(line, "Board 268 (D2:R RotW Softcore Trading): this read saw 11 prices, 15\u2013100 fg - weighed into "
                               "the price below.")
        self.assertNotIn("middle", line)
        self.assertNotIn("50", line, "the read's own middle price is still printed above the item's price")
        self.assertIn("range 12\u201320 fg, middle 18, from 3 prices", self.out["searchLine"],
                      "PREMISE: with no stored price the line reads exactly as before")

    def test_the_drawer_lists_every_post_with_link_day_fg_roll_and_weight(self):
        ev = self.out["ev"]
        self.assertIn("<summary>show the 4 posts</summary>", ev)
        self.assertIn('<a href="https://forums.d2jsp.org/topic.php?t=1" target="_blank" rel="noopener noreferrer">open post</a>', ev)
        self.assertIn("<td>2026-10-20</td><td>18 fg</td><td>20/20/10</td><td>1.00</td>", ev)
        self.assertIn("set aside, far from the middle 18 fg", ev)
        self.assertNotIn("<img>", self.out["evBad"])
        self.assertNotIn('"onmouseover', self.out["evBad"])
        bare = self.out["evBare"]
        self.assertIn("<summary>show the 1 post</summary>", bare)
        self.assertIn("<td>2000 fg</td>", bare)
        self.assertNotIn("no price", bare)
        self.assertNotIn("topic.php?t=8", bare)
        self.assertEqual(self.out["evNone"], "", "an item with no price still drew posts")

    def test_the_search_reads_slang_and_rolls(self):
        a, b, c, d = self.out["search"]
        self.assertEqual((a["item"], a["roll"]), ("anni", [20, 20, 10]))
        self.assertEqual((b["item"], b["roll"]), ("shako", [40, 15]))
        self.assertEqual((c["item"], c["roll"]), ("jmod", None))
        self.assertEqual((d["item"], d["roll"]), ("torch sorc", [18, 18]))

    def test_one_bare_number_beside_the_item_is_the_roll(self):
        # v3861 (#230 6644125606): "shako 141" lost its 141 - every bare number was deleted, so the roll never reached the
        # quote. One bare number is the roll; a socket count is not a roll; two bare numbers stay ambiguous (none).
        a, b, c = self.out["searchBare"]
        self.assertEqual((a["item"], a["roll"]), ("shako", [141]))
        self.assertEqual((b["item"], b["roll"]), ("arach", None))
        self.assertEqual((c["item"], c["roll"]), ("griffon", None))

    def test_the_desk_wears_the_bar_and_a_drawer_under_every_card_quote(self):
        p = self.page
        form = p[p.index('id="d2jsp-price-form"'):p.index('id="d2jsp-find"')]
        self.assertIn('id="d2jsp-price-q"', form)
        self.assertIn("Reads d2jsp posts dated 2026 or later, board 268 only. Nothing is posted.", form)
        self.assertIn("+ '<div data-d2jsp-evbox>' + evHtml(n) + '</div>'", p)
        self.assertIn("if (gen !== searchGen) return;", p, "an older search answer can paint over a newer one")
        search = p[p.index("function priceSearch(){"):p.index("window._d2jspPriceSearch = priceSearch;")]
        self.assertNotIn("/api/d2jsp_post", search, "the price search must never post")
        self.assertIn("d2jspTierLine(reads, n, posts, base)", p, "the card tier is not weighted")


RED_PROOF = [
    {"why": "v3881 - with the item's price below, the search line prints the read's own middle price again (two prices, #96)",
     "file": "bible.html", "find": "  var line = _dbP ? d2jspReadLine(q) : d2jspPriceLine(q);",
     "replace": "  var line = d2jspPriceLine(q);", "matches": 1, "needs": "node"},
    {"why": "v3861 - a single bare number is deleted again: 'shako 141' loses the defence he holds",
     "file": "bible.html",
     "find": "  return { item: item, roll: tuples[0] || (bare.length === 1 ? [bare[0]] : null), text: t };",
     "replace": "  return { item: item, roll: tuples[0] || null, text: t };",
     "matches": 1},
    {"why": "a line with no fg is drawn as a post again",
     "file": "bible.html",
     # v3889 (#178) - re-aimed: the drawer builds its rows with _evRow now (one tier's list, or every post)
     "find": "  var body = rows.map(_evRow).join('');\n  var shown = rows.length, _of = rows.length;\n",
     "replace": "  var body = rows.map(_evRow).join('') + ((q && q.aside) || []).map(function (a) {\n"
                "    return '<tr><td>?</td><td>no price</td><td></td><td>' + a.why + '</td><td></td></tr>';\n"
                "  }).join('');\n  var shown = rows.length + ((q && q.aside) || []).length, _of = shown;\n",
     "matches": 1},
    {"why": "an item with no price draws a post list again",
     "file": "bible.html",
     # v3889 (#178) - re-aimed: an empty drawer returns early unless it is a tier's own line or the head alone
     "find": "  if (!rows.length && !opts.headOnly) return _tier ? ",
     "replace": "  if (!rows.length && !opts.headOnly && !_tier) return '<details class=\"d2jsp-ev\"><summary>show the 0 posts</summary></details>';\n  if (!rows.length && !opts.headOnly) return _tier ? ",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
