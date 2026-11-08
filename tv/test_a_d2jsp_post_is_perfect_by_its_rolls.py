# -*- coding: utf-8 -*-
"""v3885 (#30, his 11-08 "do it and fix this and take care of it with grokbot") - A d2jsp POST IS PERFECT BY ITS ROLLS, EACH POST
IS ONE VOTE, AND EACH CLAUSE IS READ ON ITS OWN.

GrokBot read 16 real d2jsp topics (#230 6720536745, 11-08 12:43-12:55, read-only) against the console's price check:
  * "Shako 137 DEF / Perfect Topaz 30 FG" was tagged PERFECT (the socketed Perfect Topaz said "perfect") - a perfect Shako is 141;
  * the normal Enigma price, 1,400, came from "15/12/775 mp nigma 1.4k" - a 775 (maximum) roll; real normal Enigmas sell for
    275-575; and "15/0/775" posts read normal;
  * "20/-20" Griffon's Eyes read normal - the slash reader took no signed number, so no Griffon roll was ever read;
  * one shop post supplied 9 of the 10 Griffon's Eye prices; a line with two items gave both the first one's roll.
Now: a post's roll is perfect when every roll it states that falls in one of the item's variable ranges sits at that range's
maximum (d2jspRollPerfect, the table D2JSP_ROLLS built from the page's own ITEM_CODEX / RUNEWORD_TIP / BASE_DB by
tv/d2jsp_rolls.py - held equal here); a line stating no roll falls back to its words, never a gem's; each clause keeps its
own words; a repeated line at the same price in one post counts once; the rows of one post share ONE vote.
Runs the shipped worker in node on GrokBot's real lines. RED_PROOF below. [[unknown-stays-unknown]]
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
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
import d2jsp_rolls as R  # noqa: E402

WORKER = os.path.join(ROOT, "functions", "api", "d2jsp_quote.js")
NODE = shutil.which("node")
DAY = "Nov 7, 2026"
L1, L2 = "https://forums.d2jsp.org/topic.php?t=1&p=695856632", "https://forums.d2jsp.org/topic.php?t=2&p=696103201"

DRIVER = r"""
const fs = require('fs'), vm = require('vm');
const src = fs.readFileSync(process.argv[2], 'utf8');
const ctx = { console, Date, Math, JSON, String, Number, Object, Array, RegExp, parseInt, isFinite };
vm.createContext(ctx);
vm.runInContext(src.replace(/^export\s+/mg, '') + '\nthis.d2jspPosts = d2jspPosts;', ctx);
const CASES = JSON.parse(process.argv[3]);
const out = {};
for (const [k, item, text] of CASES) {
  out[k] = ctx.d2jspPosts(text, item, Date.UTC(2026, 10, 8)).map(r => ({ fg: r.fg, perfect: !!r.perfect, w: r.w, roll: r.roll }));
}
process.stdout.write(JSON.stringify(out));
"""


def _a(href, text):
    return '<a href="%s">%s</a>' % (href, text)


CASES = [
    ["shako", "Harlequin Crest", "\n".join([DAY, "Shako 137 DEF / Perfect Topaz 30 FG", DAY, "Shako 141def (perfect) 80fg",
                                             DAY, "Shako 124def 10fg", DAY, "perf shako ea 75fg",
                                             DAY, "Shako socketed Perfect Topaz 20fg"])],
    ["enigma", "Enigma", "\n".join([DAY, "15/12/775 mp nigma 1.4k", DAY, "enigma 15/0/750 mage plate 500 fg"])],
    ["griffon", "Griffon's Eye", "\n".join([DAY, "Griffon's Eye 12/-20 95fg", DAY, "Griffon's Eye 15/-20 350fg"])],
    ["clauses", "Enigma", "\n".join([DAY, "Wire Fleece Enigma 15/0/775 2000 fg ; Wyrmhide Enigma 15/0/760 1850 fg"])],
    ["shop", "Griffon's Eye", "\n".join([_a(L1, "Griffons for sale"), DAY, "Griffon's Eye 12/-20 95fg",
                                          "Griffon's Eye 14/-18 75fg", "Griffon's Eye 13/-17 80fg", "Griffon's Eye 12/-20 95fg",
                                          _a(L2, "one griffon"), DAY, "Griffon's Eye 11/-16 60fg"])],
]


@unittest.skipUnless(NODE, "node is required to run the shipped d2jsp parser")
class AD2jspPostIsPerfectByItsRolls(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        r = subprocess.run([NODE, "-", WORKER, json.dumps(CASES)], input=DRIVER, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise AssertionError("node could not run the shipped parser - UNKNOWN, not passing: " + r.stderr[-800:])
        cls.o = json.loads(r.stdout)

    def test_a_gem_is_not_the_roll_and_141_is(self):
        """* THE POINT (GrokBot) - "137 DEF / Perfect Topaz" is a normal Shako; 141 is the perfect one"""
        # the last line states no roll, so only its words could say "perfect" - and a Perfect Topaz is a gem, not the roll
        self.assertEqual([(x["fg"], x["perfect"]) for x in self.o["shako"]], [(30, False), (80, True), (10, False), (75, True), (20, False)],
                         "Shako: %r" % self.o["shako"])

    def test_the_775_enigma_is_perfect_and_the_750_normal(self):
        self.assertEqual([(x["fg"], x["perfect"]) for x in self.o["enigma"]], [(1400, True), (500, False)],
                         "the 1.4k post is a 775 (maximum) roll - it must not set the NORMAL price: %r" % self.o["enigma"])

    def test_a_signed_griffon_roll_is_read(self):
        g = self.o["griffon"]
        self.assertEqual([x["roll"] for x in g], [[[12, -20]], [[15, -20]]], "the signed roll was not read: %r" % g)
        self.assertEqual([x["perfect"] for x in g], [False, True])

    def test_each_clause_keeps_its_own_roll(self):
        c = self.o["clauses"]
        self.assertEqual([(x["fg"], x["roll"], x["perfect"]) for x in c],
                         [(2000, [[15, 0, 775]], True), (1850, [[15, 0, 760]], False)], "a clause borrowed its neighbour's roll: %r" % c)

    def test_one_post_is_one_vote_and_a_repeat_counts_once(self):
        s = self.o["shop"]
        self.assertEqual([x["fg"] for x in s], [95, 75, 80, 60], "the repeated '12/-20 95fg' line in the same post counted twice: %r" % s)
        self.assertEqual([x["w"] for x in s], [0.333, 0.333, 0.333, 1], "one shop post outweighed the others: %r" % s)

    def test_the_roll_table_is_the_pages_own(self):
        with io.open(WORKER, encoding="utf-8") as fh:
            js = fh.read()
        got = json.loads(re.search(r"var D2JSP_ROLLS = (\{.*?\});\n", js[js.index(R.BEGIN):js.index(R.END)], re.S).group(1))
        self.assertEqual(got, R.build(), "the worker's roll table is not the page's - run: python3 tv/d2jsp_rolls.py --emit")
        self.assertEqual((got.get("harlequin crest"), got.get("enigma")), ([[98, 141]], [[750, 775]]),
                         "premise: the Shako's base defence and Enigma's defence roll are the page's maxima")
        self.assertNotIn("stone of jordan", got, "a fixed damage add read as a roll")


RED_PROOF = [
    {"why": "v3885 - a socketed Perfect Topaz makes the Shako perfect again",
     "file": "functions/api/d2jsp_quote.js",
     "find": "(?!\\s*(?:topaz|ruby|amethyst|sapphire|emerald|diamond|skull|gem)s?\\b)",
     "replace": "", "matches": 1, "needs": "node"},
    {"why": "v3885 - perfect is the words' alone again (the 775 Enigma sets the normal price)",
     "file": "functions/api/d2jsp_quote.js",
     "find": "      if (byRoll === true || (byRoll === null && note.perfect)) row.perfect = true;\n",
     "replace": "      if (note.perfect) row.perfect = true;\n", "matches": 1, "needs": "node"},
    {"why": "v3885 - a signed roll is not read (no Griffon's Eye roll at all)",
     "file": "functions/api/d2jsp_quote.js",
     "find": "  var m, re = /(-?\\d+(?:\\s*\\/\\s*-?\\d+)+)/g;\n",
     "replace": "  var m, re = /(\\d+(?:\\/\\d+)+)/g;\n", "matches": 1, "needs": "node"},
    {"why": "v3885 - a clause borrows the whole line's roll",
     "file": "functions/api/d2jsp_quote.js",
     "find": "      var note = d2jspNotation(x.text || line);\n",
     "replace": "      var note = d2jspNotation(line);\n", "matches": 1, "needs": "node"},
    {"why": "v3885 - a repeated line in one post counts twice",
     "file": "functions/api/d2jsp_quote.js",
     "find": "      if (seen[dup]) { used = true; return; }\n",
     "replace": "", "matches": 1, "needs": "node"},
    {"why": "v3885 - one shop post outweighs every other post again",
     "file": "functions/api/d2jsp_quote.js",
     "find": "  return d2jspOneVotePerPost(d2jspTrim(rows));\n",
     "replace": "  return d2jspTrim(rows);\n", "matches": 1, "needs": "node"},
    {"why": "v3885 - the worker's roll table is emptied (every roll unknown)",
     "file": "functions/api/d2jsp_quote.js",
     "find": "var D2JSP_ROLLS = {",
     "replace": "var D2JSP_ROLLS = {\"zz\":[[1,2]]};var _GONE = {", "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
