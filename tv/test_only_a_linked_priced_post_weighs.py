# -*- coding: utf-8 -*-
"""REG-3327 (#95 - his 11-06 ruling on the D2JSP Advanced table: "good that its saving data for perfect tier and normal
tier, just i want the posts linked there anything without a post or a price is irrelevant") - A POST WEIGHS IN A PRICE
ONLY WITH ITS FORUM LINK AND A PRICE; THE REST STAY ON RECORD, OUT OF THE TABLE AND THE PRICE, AND ONE LINE SAYS HOW MANY.

MEASURED 11-07 on his DB: shako 14 posts, 9 with no link (11-01 and 10-31, recorded before links were kept; their key is
fg|day|roll, so no link can be recovered). Linked only, shako's normal price stays 15 fg (7/10/15/40/80) and its perfect
tier - two unlinked posts - is UNKNOWN, never a number nobody can open.

Held here: d2jsp_price_db.price and explain on a DB that mixes linked and unlinked posts; the records are untouched; the
page's Advanced table (d2jspBackendHtml, driven in node) says how many were left out. RED_PROOF below.
"""
import copy
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import d2jsp_price_db as P  # noqa: E402

NODE = shutil.which("node") or shutil.which("nodejs")
NOW = time.mktime((2026, 11, 7, 0, 0, 0, 0, 0, -1))
L = "https://forums.d2jsp.org/topic.php?t=1&f=268&p=%d"


def _db():
    posts = {}
    for i, fg in enumerate((80, 7, 15, 40, 10)):
        posts[L % i] = {"fg": fg, "day": "2026-11-03", "link": L % i, "w": 1, "src": "mac", "seenAt": NOW - 86400}
    for i, (fg, perf) in enumerate(((110, False), (15, False), (150, True), (60, True))):
        posts["%d|2026-10-31|" % fg + str(i)] = {"fg": fg, "day": "2026-10-31", "link": "", "w": 1, "perfect": perf,
                                                  "src": "mac", "seenAt": NOW - 7 * 86400}
    posts[L % 99] = {"fg": None, "day": "2026-11-03", "link": L % 99, "w": 1, "src": "mac"}     # a link with no price
    return {"schema": P.SCHEMA, "items": {P.key_of("shako"): {"posts": posts, "readAt": NOW}}}


class OnlyALinkedPricedPostWeighs(unittest.TestCase):

    def test_the_price_weighs_linked_priced_posts_only(self):
        db = _db()
        before = copy.deepcopy(db)
        pr = P.price(db, "shako", now=NOW)
        self.assertEqual(pr["normal"]["fg"], 15, "the normal price weighed a post with no link: %r" % pr["normal"])
        self.assertEqual(pr["normal"]["n"], 5)
        self.assertIsNone(pr["perfect"]["fg"], "two unlinked perfect posts priced the perfect tier")
        self.assertEqual(pr["leftOut"], 5, "the price does not say how many it left out")
        self.assertEqual(db, before, "pricing changed the records - nothing is deleted")

    def test_the_table_holds_the_same_posts_the_price_weighed(self):
        ex = P.explain(_db(), "shako", now=NOW)
        self.assertEqual(sorted(r["link"] for r in ex["posts"]), sorted(L % i for i in range(5)))
        self.assertEqual(ex["leftOut"], 5)

    def test_the_page_says_how_many_were_left_out(self):
        if not NODE:
            self.skipTest("no node - the Advanced table is not driven here (UNMEASURED)")
        with io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8") as fh:
            page = fh.read()
        a = page.index("function d2jspBackendHtml(db, painted, opts) {")
        depth, i = 0, page.index("{", a)
        for k in range(i, len(page)):
            if page[k] == "{":
                depth += 1
            elif page[k] == "}":
                depth -= 1
                if depth == 0:
                    fn = page[a:k + 1]
                    break
        stubs = ("function d2jspEscText(s){ return String(s == null ? '' : s); }\n"
                 "function d2jspFgText(n){ return String(n); } function d2jspSeenText(){ return 'x'; }\n"
                 "function d2jspPriceSyncLine(){ return ''; } function d2jspDatabaseButton(){ return ''; }\n"
                 "function d2jspTierSay(){ return ''; }\n")
        prog = (stubs + fn + "\nvar ex = %s;\n" % json.dumps(P.explain(_db(), "shako", now=NOW))
                + "process.stdout.write(d2jspBackendHtml({item:'shako', normal:{fg:15,n:5}, perfect:{fg:null,n:0}, proof: ex}, null, {}));")
        r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-1200:])
        self.assertIn("5 posts have no forum link - kept on record, left out of this table and of the price.", r.stdout)
        self.assertEqual(r.stdout.count("data-d2jsp-post>"), 5, "the table drew a post the price did not weigh")
        self.assertNotIn(">no link<", r.stdout)


RED_PROOF = [
    {"why": "REG-3327 - a post with no link weighs in the price again (his 'anything without a post is irrelevant')",
     "file": "tv/d2jsp_price_db.py",
     "find": "    if not isinstance(p, dict) or not str(p.get(\"link\") or \"\").startswith(\"http\"):\n",
     "replace": "    if not isinstance(p, dict):\n",
     "matches": 1},
    {"why": "REG-3327 - the Advanced table drops the unlinked posts and never says how many",
     "file": "bible.html",
     "find": "  var _left = Number(proof.leftOut) > 0 ? Number(proof.leftOut) : 0;\n",
     "replace": "  var _left = 0;\n",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
