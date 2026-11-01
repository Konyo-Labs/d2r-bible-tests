"""v3845 - COMPACT ROLL COLUMNS ARE READ AND PRICED BY ROLL (Elad, 2026-10-30 09:29).
Simsalara, board 268, Oct 7 2026: "guardian's thunder +7 -5 4 41 27 15fg" ... "+7 -10 4 33 29 390fg". The numbers after
the name are the jewel's ranged mods in its own order (lightning skill damage, -enemy lightning resistance, then the
rest). The evidence drawer said "no roll written" for every post, weighed each 1.00, and set the best key roll (-10 at
390 fg) aside as "far from the middle". Now: each post's roll is read into the item's mods, each post is weighed by how
close its roll is to the one you hold (the key mods by how much they move the price), the price is fit against roll,
and a post is set aside only when its roll does not explain its price. The post's own date dates it.
NO CHROME = a declared skip, never a pass. RED_PROOF below. [[regression-guard]]"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import d2jsp_chrome as D  # noqa: E402
from test_a_sweep_never_reticks_what_he_unticked import Board  # noqa: E402
import test_found_ever_never_files_to_a_mule as _H  # noqa: E402

ITEM = "Guardian's Thunder"
LINES = ["+7 -5 4 41 27 15fg", "+7 -6 4 34 30 20fg", "+5 -8 3 37 29 20fg", "+6 -8 3 36 26 25fg", "+7 -7 4 42 23 25fg",
         "+8 -7 4 49 17 35fg", "+10 -6 3 30 30 100fg", "+8 -9 3 47 33 130fg", "+8 -9 4 40 28 140fg",
         "+8 -9 4 46 27 140fg", "+7 -10 4 33 29 390fg"]
POST = ('<div>Oct 7 2026 11:04pm <a href="topic.php?t=110445948&amp;f=268&amp;p=695336765">#1</a> Last post: Today</div>'
        "rotw softcore nonladder<br>colossal ancient jewels:<br>"
        + "".join("guardian's thunder %s<br>" % l for l in LINES)
        + "guardian's light -5 +5 3 40 26 10fg<br>")
#: Elad's jewel, as his card reads it
MODS = ("Adds 1-75 lightning damage\n+10% to Lightning Skill Damage\n-9% to Enemy Lightning Resistance\n"
        "+3% to Experience Gained\n31% Extra Gold from Monsters\n20% Better Chance of Getting Magic Items")


@unittest.skipUnless(os.path.exists(_H.RC.CHROME), "no Chrome on this machine (declared skip)")
class CompactRollColumns(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.q = D.parse_public_quote(POST, ITEM, "2026-10-30T07:00:00Z")
        b = Board()
        b.open()
        cls.o = b.run("var db = window._cbDb(); var reads = d2jspAffixRead(%s, db, %s);"
                      "OUT.sim = d2jspSimilarPrice(%s, null, %s, reads); OUT.html = d2jspEvidenceHtml(OUT.sim);"
                      % (json.dumps(MODS), json.dumps(ITEM), json.dumps(cls.q), json.dumps(ITEM)))

    def test_every_post_keeps_its_columns_and_its_own_date(self):
        posts = self.q["posts"]
        self.assertEqual(11, len(posts), "the Thunder lines did not all price (the Light line must not): %r" % posts)
        self.assertEqual([7, -10, 4, 33, 29], posts[-1].get("cols"), "the columns were not read: %r" % posts[-1])
        self.assertTrue(all(p["day"] == "2026-10-07" for p in posts), "a post is dated by 'Today', not its own date")
        self.assertTrue(all(p["w"] > 0 for p in posts), "a post with its roll written was trimmed by the middle")

    def test_the_drawer_shows_the_roll_as_read(self):
        h = self.o["html"]
        self.assertNotIn("no roll written", h)
        self.assertIn("+7 -10 4 33 29", h, "the roll as read is not shown")

    def test_the_minus_nine_and_ten_rows_carry_the_weight(self):
        rows = self.o["sim"]["posts"]
        w = dict((tuple(r["cols"]), r["w"]) for r in rows)
        nine = [w[(8, -9, 3, 47, 33)], w[(8, -9, 4, 40, 28)], w[(8, -9, 4, 46, 27)]]
        low = [w[tuple(int(x.replace("fg", "")) for x in l.split()[:5])] for l in LINES[:6]]
        self.assertGreater(min(nine), max(low) * 2, "a -9 row is not heavier than the -5..-8 rows: %r" % w)
        self.assertGreater(w[(7, -10, 4, 33, 29)], max(low), "the -10 row weighs no more than the low rolls: %r" % w)
        self.assertEqual("", [r for r in rows if r["cols"] == [7, -10, 4, 33, 29]][0]["out"],
                         "the best key roll was set aside although its roll explains its price")

    def test_the_quote_sits_well_above_the_plain_middle(self):
        s = self.o["sim"]
        self.assertGreaterEqual(s["fg"], 130, "the roll-weighted price is not with the -9 rows: %r" % s["fg"])
        self.assertGreater(s["fit"], 230, "the price-by-roll fit at +10/-9 is not well above the 115 middle: %r" % s["fit"])
        self.assertIn("data-d2jsp-rollprice", self.o["html"])


class PublicPostsLabelOnlyAReason(unittest.TestCase):
    def test_a_truthy_non_reason_out_is_no_label(self):
        rows = D._public_posts([{"fg": 10, "out": True}, {"fg": 11, "out": 1}, {"fg": 12, "out": "  "},
                                {"fg": 13, "out": "far from the middle 40 fg"}])
        self.assertEqual([r.get("out") for r in rows], [None, None, None, "far from the middle 40 fg"], rows)


RED_PROOF = [
    {"why": "any truthy out is a label again", "file": "tv/d2jsp_chrome.py",
     "find": "        if isinstance(_o, str) and _o.strip():", "replace": "        if _o:", "matches": 1},
    {"why": "the compact columns are not read off the line",
     "file": "functions/api/d2jsp_quote.js", "find": "  return cols.length >= 2 && cols.length <= 8 ? cols : null;",
     "replace": "  return null;", "matches": 1},
    {"why": "a post with its roll written is trimmed by distance from the middle again",
     "file": "functions/api/d2jsp_quote.js", "find": "  rows.forEach(function (r) {\n    if (r.cols) return;\n    var t = d2jspSlashOf(r);\n",
     "replace": "  rows.forEach(function (r) {\n    var t = d2jspSlashOf(r);\n", "matches": 1},
    {"why": "a relative 'Today' overrides the post's own written date",
     "file": "functions/api/d2jsp_quote.js", "find": "    } else if (rel && !explicit) when = d;",
     "replace": "    } else if (rel) when = d;", "matches": 1},
    {"why": "every post weighs the same, whatever its roll",
     "file": "bible.html", "find": "    r.w = 0.02 + 0.98 * Math.pow(r.sim, 4);", "replace": "    r.w = 1;", "matches": 1},
    {"why": "the card's reads never reach the column pricing",
     "file": "bible.html", "find": "  if (reads) { var byCols = d2jspColsPrice(q, reads, itemName); if (byCols) return byCols; }",
     "replace": "", "matches": 1},
    {"why": "the drawer shows no roll for a column post",
     "file": "bible.html", "find": "    var roll = (p.cols && p.cols.length) ? p.cols.map(",
     "replace": "    var roll = (false) ? p.cols.map(", "matches": 1},
]

if __name__ == "__main__":
    unittest.main()
