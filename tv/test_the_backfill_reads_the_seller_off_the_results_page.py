# -*- coding: utf-8 -*-
"""#151 (REG-3793) - THE BACKFILL READS EACH TOPIC'S SELLER OFF THE SIGNED-IN RESULTS PAGE'S OWN ROWS.

MEASURED 11-11 on the running backfill: 158 items, 1,832 priced rows, 3 with an author; every log line said authors=-.
The parser takes a seller only from a line that neither names the item nor carries a price (v3894, so a body mention
is never the seller) - and a results row names both. d2jsp_backfill.topic_authors reads the page's structure instead: a
topic belongs to the smallest <tr> that links to it, and that row names its seller only when it links to exactly one
topic and exactly one user.php name. Two names, two topics, none, or two rows that disagree: unknown, never guessed.
The runner fills only posts the parser left without a seller. Fixtures only. RED_PROOF below.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import d2jsp_backfill as B  # noqa: E402


def _tr(t, *names, title="WTS Enigma 1850 fg"):
    who = "".join(' <td><a href="user.php?i=%d">%s</a></td>' % (i + 1, n) for i, n in enumerate(names))
    return '<tr><td><a href="topic.php?t=%d&amp;f=268">%s</a></td>%s</tr>' % (t, title, who)


PAGE = ("<html><body>Viewing Search Results<table>"
        + _tr(110552180, "SellerA")
        + _tr(110566436, "SellerA")
        + _tr(110563895, "SellerC", "LastPoster")         # two names: not known which is the seller
        + _tr(110577047)                                   # no name
        + '<tr><td><a href="topic.php?t=1">a</a> <a href="topic.php?t=2">b</a> <a href="user.php?i=9">Mod</a></td></tr>'
        + "</table></body></html>")


def _post(t, author=None):
    p = {"fg": 1850, "day": "2026-11-05", "w": 1, "link": "https://forums.d2jsp.org/topic.php?t=%d&f=268&p=5" % t}
    if author:
        p["author"] = author
    return p


class TheBackfillReadsTheSeller(unittest.TestCase):

    def test_a_row_of_one_topic_and_one_name_names_its_seller(self):
        self.assertEqual(B.topic_authors(PAGE), {"110552180": "SellerA", "110566436": "SellerA"})

    def test_the_runner_fills_only_posts_with_no_seller(self):
        reading = {"reason": "read", "posts": [_post(110552180), _post(110566436, "Parsed"), _post(110563895),
                                               _post(110577047)]}
        self.assertEqual(B.fill_authors(reading, PAGE), 1)
        self.assertEqual([p.get("author") for p in reading["posts"]], ["SellerA", "Parsed", None, None])

    def test_two_rows_that_disagree_say_nothing(self):
        page = "<table>" + _tr(5, "A") + _tr(5, "B") + "</table>"
        self.assertEqual(B.topic_authors(page), {})

    def test_a_page_with_no_rows_names_no_one(self):
        self.assertEqual(B.topic_authors('<div><a href="topic.php?t=5">x</a> <a href="user.php?i=1">A</a></div>'), {})
        self.assertEqual(B.topic_authors(None), {})

    def test_a_name_in_a_nested_row_still_belongs_to_the_outer_topic_row(self):
        page = ('<table><tr><td><a href="topic.php?t=7">WTS</a><table><tr><td>by <a href="user.php?i=1">A</a></td></tr>'
                '</table> last <a href="user.php?i=2">B</a></td></tr></table>')
        self.assertEqual(B.topic_authors(page), {}, "a starter and a last poster were read as one seller")


RED_PROOF = [
    {"why": "REG-3793 - the runner never reads the seller off the page",
     "file": "tv/d2jsp_backfill.py",
     "find": "    who = topic_authors(html)\n    if not who:\n        return 0\n",
     "replace": "    who = {}\n    if not who:\n        return 0\n",
     "matches": 1},
    {"why": "REG-3793 - a row that names two people gives its topic the first one",
     "file": "tv/d2jsp_backfill.py",
     "find": "            if len(row[\"names\"]) > 1:\n                bad.add(t)                       # its own row names two people: which is the seller is not known\n                continue\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3793 - a seller the parser read is replaced by the page's",
     "file": "tv/d2jsp_backfill.py",
     "find": "        if not isinstance(post, dict) or P.author_of(post):\n",
     "replace": "        if not isinstance(post, dict):\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
