# -*- coding: utf-8 -*-
"""REG-3815 (#151, GrokBot's look 11-12 21:05 IST: "Sellers named on the row - NO. The row has no seller column. The data has
sellers, but the page doesn't show them") - THE PRICE TABLE NAMES EACH POST'S SELLER. d2jsp_price_db.explain() hands every
row its "author" (REG-3790: the seller, or None when the page did not name one); bible.html's d2jspBackendHtml now draws it
in its own column, and a row with no seller read says so in words - never a blank that reads as nobody.

DRIVEN: the shipped d2jspBackendHtml cut from bible.html with its three text helpers, run in node over one named row and one
unread row. RED_PROOF below.
"""
import io
import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
from cb_node_harness import NODE  # noqa: E402

BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")


def _fn(src, head):
    assert src.count(head) == 1, "PREMISE: %r is declared %d times" % (head, src.count(head))
    i = src.index(head)
    return src[i:src.index("\n}\n", i) + 3]


class APriceRowNamesItsSeller(unittest.TestCase):

    def test_each_row_names_its_seller_or_says_it_was_not_read(self):
        if NODE is None:
            raise AssertionError("node is not installed on this PC - this law runs the shipped table in node and does not skip")
        with io.open(BIBLE, encoding="utf-8") as fh:
            src = fh.read()
        js = "".join(_fn(src, h) for h in ("function d2jspEscText(s) {", "function d2jspFgText(n) {",
                                            "function d2jspSeenText(at) {", "function d2jspTierSay(", "function d2jspBackendHtml(db, painted, opts) {"))
        db = {"normal": {"fg": 15}, "perfect": None, "stale": False, "why": "fresh",
              "proof": {"halfLifeDays": 30, "agree": 0.25, "leftOut": 0,
                        "posts": [{"day": "2026-11-10", "fg": 15, "tier": "normal", "author": "TradeKnight", "ageDays": 2,
                                   "w": 1, "decayed": 0.95, "band": "in", "src": "backfill", "seenAt": None,
                                   "link": "https://forums.d2jsp.org/topic.php?t=1"},
                                  {"day": "2026-11-09", "fg": 14, "tier": "normal", "author": None, "ageDays": 3,
                                   "w": 1, "decayed": 0.93, "band": "in", "src": "backfill", "seenAt": None,
                                   "link": "https://forums.d2jsp.org/topic.php?t=2"}]}}
        prog = js + "\nprocess.stdout.write(d2jspBackendHtml(%s, null, {}));" % json.dumps(db)
        r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        html = r.stdout
        self.assertIn("<th>seller</th>", html, "the table has no seller column")
        self.assertIn("<td data-d2jsp-seller>TradeKnight</td>", html, "a row's seller is not on the page")
        self.assertIn("<td data-d2jsp-seller>seller not read</td>", html, "a row with no seller read is a blank, not said")
        self.assertEqual(html.count("<td data-d2jsp-seller>"), 2, "PREMISE: two rows, two seller cells")


RED_PROOF = [
    {"why": "REG-3815 - the price table drops each post's seller again (the data has it, the page does not show it)",
     "file": "bible.html",
     "find": "        + '</td><td data-d2jsp-seller>' + d2jspEscText(p.author ? p.author : 'seller not read')\n",
     "replace": "",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
