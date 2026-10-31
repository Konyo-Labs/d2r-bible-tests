"""v3843 - THE D2JSP DESK SPEAKS THE FORUM'S WORDS AND READS THE ROLL.

1. The search asks the way traders write: the slang form when the lexicon has one (Harlequin Crest -> shako), else the
   simplified name; a price line naming any form counts. The lexicon and notation come from the forum's guides; no
   price ever does.
2. The public price is read on board 268, the Softcore non-ladder trading board, and only from posts dated within the last 120 days of the reading: an
   older post, or a page that dates nothing, leaves the price unknown.
3. The roll-tier line places each typed mod within the game's own roll range (100% = the row's ceiling), prices the
   tier inside this year's range, and flags a value no row allows as likely misread. Advisory only: the post template
   and the post price do not change.
4. A shadow page never hands the console its copy readout (second eye 3828a)."""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable
enable()

ROOT = os.path.dirname(HERE)
NODE = shutil.which("node")


def _read(*p):
    with io.open(os.path.join(ROOT, *p), encoding="utf-8") as fh:
        return fh.read()


def _block(src, begin, end):
    a = src.index(begin) + len(begin)
    return src[a:src.index(end, a)]


def _node(prog):
    out = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        raise AssertionError(out.stderr)
    return json.loads(out.stdout)


QUOTE = os.path.join("functions", "api", "d2jsp_quote.js")


@unittest.skipIf(NODE is None, "node is not on this machine")
class TheSearchSpeaksSlang(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parser = _block(_read(QUOTE), "/* ⟦D2JSP QUOTE BEGIN⟧ */", "/* ⟦D2JSP QUOTE END⟧ */")
        body = r"""
var out = {};
out.shako = d2jspSearchWords('Harlequin Crest');
out.gheeds = d2jspSearchWords("Gheed's Fortune");
out.plain = d2jspSearchWords("The Stone of Jordan Ring Thing");
out.reaper = d2jspSearchWords("The Reaper's Toll");
out.note = d2jspNotation("Anni 20/20/10 eth 2os @30 perf up'd rand");
var NOW = Date.parse('2026-10-29T12:00:00.000Z');
out.day = [d2jspLineDate('Posted Oct 12, 2026 9:00', NOW), d2jspLineDate('12 Oct 2025', NOW), d2jspLineDate('2026-01-02', NOW), d2jspLineDate('Today, 9:12', NOW), d2jspLineDate('Yesterday', NOW), d2jspLineDate('Shako 20 fg', NOW)];
out.day = out.day.map(function (d) { return d == null ? null : new Date(d).toISOString().slice(0, 10); });
out.jalal = d2jspSearchWords("Jalal's Mane");
out.jmod = d2jspSearchWords("Jeweler's Monarch of Deflecting");
out.waterwalk = d2jspSearchWords('Waterwalk');
out.wwAsWaterwalk = d2jspRead('Oct 20, 2026\nWW 500 fg', 'Waterwalk', '2026-10-29T12:00:00.000Z');
out.jmodAsJalal = d2jspRead('Oct 20, 2026\njmod 900 fg', "Jalal's Mane", '2026-10-29T12:00:00.000Z');
out.newYear = d2jspRead('Dec 28, 2026\nShako 300 fg\nJan 2, 2027\nShako 250 fg', 'Harlequin Crest', '2027-01-03T10:00:00.000Z');
out.stale = d2jspRead('Jun 1, 2026\nShako 300 fg', 'Harlequin Crest', '2026-10-29T12:00:00.000Z');
out.mixed = d2jspRead('Oct 3, 2025\nShako 300 fg\nOct 3, 2026\nShako 200 fg\nHarlequin Crest 100 fg\nShakos 999 fg', 'Harlequin Crest', '2026-10-29T12:00:00.000Z');
out.undated = d2jspRead('Shako 300 fg', 'Harlequin Crest', 'x');
out.old = d2jspRead('Mar 1, 2025\nShako 300 fg', 'Harlequin Crest', '2026-10-29T12:00:00.000Z');
out.fg = ['300fg', '300 fg', '1,500 fg', '30,000fg', '1.5k', '25k fg', '10K', '2os 40ias 300ed', '35MF gheeds', '5 keys 20fg', '99999999 fg'].map(d2jspFgAmounts);
out.big = d2jspRead('Oct 20, 2026\nGlyph Scratch eth CS 25k\nGlyph Scratch 30,000 fg\nGlyph Scratch 1.5k', 'Glyph Scratch', '2026-10-29T12:00:00.000Z');
process.stdout.write(JSON.stringify(out));
"""
        cls.out = _node(cls.parser + "\n" + body)

    def test_the_query_is_the_slang_form_else_the_simplified_name(self):
        self.assertEqual(self.out["shako"]["query"], "shako")
        self.assertIn("harlequin crest", self.out["shako"]["forms"])
        self.assertEqual(self.out["gheeds"]["query"], "gheeds")
        self.assertEqual(self.out["reaper"]["query"], "reapers")
        self.assertEqual(self.out["plain"]["slang"], [])
        self.assertEqual(self.out["plain"]["query"], "stone of jordan ring thing")

    def test_the_notation_reads_tuples_sockets_and_short_words(self):
        n = self.out["note"]
        self.assertEqual(n["tuples"], [[20, 20, 10]])
        self.assertEqual(n["sockets"], 2)
        self.assertEqual(n["allRes"], 30)
        self.assertTrue(n["eth"] and n["perfect"] and n["upgraded"] and n["random"])
        self.assertIn("ethereal", n["words"])
        self.assertIn("open sockets", n["words"])

    def test_only_recent_posts_price_it(self):
        self.assertEqual(self.out["day"], ["2026-10-12", "2025-10-12", "2026-01-02", "2026-10-29", "2026-10-28", None])
        m = self.out["mixed"]
        self.assertEqual(m["reason"], "read")
        self.assertEqual((m["low"], m["high"], m["n"]), (100, 200, 2), "a 2025 post or a longer word priced it")
        self.assertEqual(m["board"], 268)
        self.assertEqual(self.out["undated"]["reason"], "no prices")
        self.assertIsNone(self.out["undated"]["fg"])
        self.assertEqual(self.out["old"]["reason"], "no prices")
        s = self.out["stale"]
        self.assertEqual(s["reason"], "no prices", "a post older than the window priced it")

    def test_the_window_rolls_past_new_year(self):
        y = self.out["newYear"]
        self.assertEqual(y["reason"], "read", "prices stopped on Jan 1")
        self.assertEqual((y["low"], y["high"], y["n"]), (250, 300, 2))

    def test_jmod_is_not_jalals_and_ww_is_not_waterwalk(self):
        self.assertNotIn("jmod", self.out["jalal"]["forms"], "jmod is Jeweler's Monarch of Deflecting, not Jalal's Mane")
        self.assertNotEqual(self.out["jalal"]["query"], "jmod")
        self.assertNotIn("ww", self.out["waterwalk"]["forms"], "ww is Whirlwind, not Waterwalk")
        self.assertNotEqual(self.out["waterwalk"]["query"], "ww")
        self.assertEqual(self.out["wwAsWaterwalk"]["reason"], "no prices", "a Whirlwind post priced Waterwalk")
        self.assertEqual(self.out["jmodAsJalal"]["reason"], "no prices", "a Jeweler's Monarch post priced Jalal's Mane")

    def test_large_fg_amounts_read_whole(self):
        self.assertEqual(self.out["fg"], [[300], [300], [1500], [30000], [1500], [25000], [10000], [], [], [20], []])
        b = self.out["big"]
        self.assertEqual((b["low"], b["high"], b["n"], b["fg"]), (1500, 30000, 3, 25000))

    def test_the_lexicon_carries_no_prices(self):
        lex = _block(self.parser, "var D2JSP_SLANG = {", "};")
        self.assertNotRegex(lex, r"\d+\s*fg", "a price rode into the lexicon")

    def test_the_reader_searches_board_268_with_the_slang_query(self):
        import d2jsp_chrome
        self.assertEqual(d2jsp_chrome.QUOTE_BOARD, 268)
        self.assertIn("f=268", d2jsp_chrome._search_url("Harlequin Crest"))
        self.assertEqual(d2jsp_chrome._search_keywords("Harlequin Crest"), "shako")
        self.assertIn(b"stext=shako", d2jsp_chrome._search_body("Harlequin Crest"))
        self.assertIn("d2jspSearchWords(item).query", _read(QUOTE))


@unittest.skipIf(NODE is None, "node is not on this machine")
class TheRollTierLine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        page = _read("bible.html")
        cls.page = page
        desk = _block(page, "/* ⟦D2JSP DESK BEGIN⟧ */", "/* ⟦D2JSP DESK END⟧ */")
        m = re.search(r'<script[^>]*id="cb-db"[^>]*>([\s\S]*?)</script>', page)
        body = r"""
var d = DBJSON; d.byName = {}; d.it.forEach(function(x){ d.byName[x[1].toLowerCase()] = d.byName[x[1].toLowerCase()] || x; });
d.anc = {}; Object.keys(d.ty).forEach(function(t){ var a = {}; (d.ty[t][4] || [t]).forEach(function(x){ a[x] = 1; }); d.anc[t] = a; });
var out = {};
out.anni = d2jspAffixRead("+20 to All Attributes\nAll Resistances +15\n+10% to Experience Gained\n+300-400% Enhanced Damage", d, 'Annihilus');
out.anniLine = d2jspTierLine(out.anni);
out.price = d2jspTierPrice({reason: 'read', fg: 200, low: 100, high: 300}, d2jspTierAvg(out.anni));
out.noRange = d2jspTierPrice({reason: 'read', fg: 200, low: 200, high: 200}, d2jspTierAvg(out.anni));
out.gc = d2jspAffixRead("+99 to Life", d, 'Grand Charm');
out.gcLine = d2jspTierLine(out.gc);
out.none = d2jspTierLine(d2jspAffixRead("Nothing a table names", d, 'Grand Charm'));
out.draft = d2jspDraft('Annihilus', 'Small Charm', "+20 to All Attributes", 1, 250);
process.stdout.write(JSON.stringify(out));
"""
        prog = "var window = {}, document = {};\n" + desk + "\nvar DBJSON = " + m.group(1).strip() + ";\n" + body
        cls.out = _node(prog)

    def test_each_mod_sits_in_its_rows_range(self):
        a = {r["line"]: r for r in self.out["anni"]}
        self.assertEqual(a["+20 to All Attributes"]["pct"], 100)
        self.assertEqual(a["All Resistances +15"]["pct"], 50)
        self.assertNotIn("+300-400% Enhanced Damage", a, "a line that is still a range was read as a roll")
        self.assertIn("Roll tier: mid, 83% up the rolls", self.out["anniLine"])
        self.assertIn("(3 mods read)", self.out["anniLine"])

    def test_the_tier_prices_inside_this_years_range(self):
        self.assertRegex(self.out["price"], r"^For a mid roll: about 267 fg of 100\u2013300\.$")
        self.assertEqual(self.out["noRange"], "")

    def test_an_impossible_value_is_a_warning_with_the_raw_read_kept(self):
        g = self.out["gc"][0]
        self.assertEqual(g["value"], 99, "the raw read was not kept")
        self.assertLess(g["legal"], 99)
        self.assertIn("likely misread", g["warn"])
        self.assertTrue(self.out["gcLine"].startswith("Check: +99 to Life is above every roll"))
        # v3849 (test_d2jsp_gross_outlier_and_key_weight): a line that names no row is kept and said, never silent
        self.assertEqual(self.out["none"], "Check: could not be read.")

    def test_the_post_template_is_unchanged(self):
        self.assertEqual(self.out["draft"]["body"], "Selling Annihilus Small Charm\n+20 to All Attributes\n250 fg")
        self.assertIn("+ tierHtml(n, mods)", self.page)
        self.assertNotIn("tier", self.out["draft"]["body"].lower())


class AShadowNeverHandsOverACopyReadout(unittest.TestCase):
    def test_the_copy_audit_hand_over_is_skipped_on_a_shadow(self):
        page = _read("bible.html")
        a = page.index("window.__tallyPersist = function(){")
        body = page[a:page.index("fetch('/api/board_tally'", a)]
        i = body.index("_body.copyAudit = (typeof window._vaultCopyAudit")
        self.assertIn("if (!window._tvdShadow) try {", body[:i])


if __name__ == "__main__":
    unittest.main()
