# -*- coding: utf-8 -*-
"""v3893 (#180, REG-3554) - THE SAME SELLER IS ONE POST AND ONE PRICE.

His ruling: the same seller counts as one post and one price. Dedupe D2JSP price votes by seller
when a stored or signed-out readable author proves they are the same seller. An unknown author
stays one vote per link. Topics are never hard-deleted or merged by id — two topics remain two
rows of evidence, and they share a weight of 1 only when the author is known.

Law: two topics whose user.php name is the same seller share one vote and both stay; two topics
with no author, or two different authors, each keep a full vote; the parser does not name those
topics by id. RED_PROOF below.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import d2jsp_chrome as D  # noqa: E402
import d2jsp_price_db as DB  # noqa: E402

ITEM = "Harlequin Crest"
READ_AT = "2026-10-30T07:00:00Z"


def _card(day, topic, body, author=None, extra_author=None):
    who = ''
    if author:
        who += ' <a href="user.php?i=1">%s</a>' % author
    if extra_author:
        who += ' <a href="user.php?i=2">%s</a>' % extra_author
    return ('<div>%s <a href="topic.php?t=%s&amp;f=268">#1</a>%s</div>%s'
            % (day, topic, who, body))


class TheSameSellerIsOneVote(unittest.TestCase):

    def test_two_topics_from_the_same_readable_seller_share_one_vote(self):
        html = (_card("Oct 7 2026 11:04pm", "111111111", "shako 400 fg<br>", "SellerA")
                + _card("Oct 8 2026 12:04pm", "222222222", "shako 410 fg<br>", "SellerA"))
        q = D.parse_public_quote(html, ITEM, READ_AT)
        posts = q["posts"]
        self.assertEqual(len(posts), 2, posts)
        self.assertEqual({p.get("author") for p in posts}, {"SellerA"})
        self.assertEqual(sorted(p["link"] for p in posts), [
            "https://forums.d2jsp.org/topic.php?t=111111111&f=268",
            "https://forums.d2jsp.org/topic.php?t=222222222&f=268",
        ])
        self.assertTrue(all(abs(p["w"] - 0.5) < 0.001 for p in posts), posts)

    def test_unknown_or_different_authors_stay_one_vote_per_link(self):
        bare = (_card("Oct 7 2026 11:04pm", "111111111", "shako 400 fg<br>")
                + _card("Oct 8 2026 12:04pm", "222222222", "shako 410 fg<br>"))
        q = D.parse_public_quote(bare, ITEM, READ_AT)
        self.assertEqual(len(q["posts"]), 2, q["posts"])
        self.assertTrue(all(p.get("author") in (None, "") for p in q["posts"]), q["posts"])
        self.assertTrue(all(p["w"] == 1 for p in q["posts"]), q["posts"])

        two = (_card("Oct 7 2026 11:04pm", "111111111", "shako 400 fg<br>", "SellerA")
               + _card("Oct 8 2026 12:04pm", "222222222", "shako 410 fg<br>", "SellerB"))
        q = D.parse_public_quote(two, ITEM, READ_AT)
        self.assertEqual({p.get("author") for p in q["posts"]}, {"SellerA", "SellerB"})
        self.assertTrue(all(p["w"] == 1 for p in q["posts"]), q["posts"])

        mixed = _card("Oct 7 2026 11:04pm", "111111111", "shako 400 fg<br>", "SellerA", "LastPoster")
        q = D.parse_public_quote(mixed, ITEM, READ_AT)
        self.assertEqual(len(q["posts"]), 1, q["posts"])
        self.assertTrue(q["posts"][0].get("author") in (None, ""), q["posts"])
        self.assertEqual(q["posts"][0]["w"], 1)

    def test_topics_are_not_hard_deleted_or_merged_by_id(self):
        with open(os.path.join(os.path.dirname(HERE), "functions", "api", "d2jsp_quote.js"),
                  encoding="utf-8") as fh:
            src = fh.read()
        self.assertNotIn("110566436", src)
        self.assertNotIn("110552180", src)
        self.assertIn("function d2jspVoteKey(r)", src)
        self.assertIn("seller:", src)

    def test_a_new_undated_topic_does_not_inherit_the_last_seller(self):
        """v3894 - authors reset whenever the topic link changes (the `here !== link` / `when && !used` branch)"""
        html = (_card("Oct 7 2026 11:04pm", "111111111", "", "SellerA")
                + '<div><a href="topic.php?t=222222222&amp;f=268">#1</a></div>shako 410 fg<br>')
        q = D.parse_public_quote(html, ITEM, READ_AT)
        posts = q["posts"]
        self.assertTrue(posts, posts)
        self.assertTrue(all(p.get("author") in (None, "") for p in posts),
                        "a new undated topic inherited the last seller: %s" % posts)

    def test_a_user_php_mention_in_the_body_is_not_the_seller(self):
        """v3894 - a user.php mention in a post body must not become the seller when the seller's name is plain text"""
        html = ('<div>Oct 7 2026 11:04pm <a href="topic.php?t=111111111&amp;f=268">#1</a> SellerA</div>'
                'I agree with <a href="user.php?i=9">Mentioned</a> — shako 400 fg<br>'
                '<div>Oct 8 2026 12:04pm <a href="topic.php?t=222222222&amp;f=268">#1</a> SellerB</div>'
                'see <a href="user.php?i=9">Mentioned</a> shako 410 fg<br>')
        q = D.parse_public_quote(html, ITEM, READ_AT)
        posts = q["posts"]
        self.assertEqual(len(posts), 2, posts)
        self.assertTrue(all(p.get("author") in (None, "") for p in posts),
                        "a body mention became the seller: %s" % posts)
        self.assertTrue(all(p["w"] == 1 for p in posts),
                        "two topics collapsed into one vote via the mentioned name: %s" % posts)

    def test_a_stored_author_is_kept_and_the_topic_key_stays_its_link(self):
        html = (_card("Oct 7 2026 11:04pm", "111111111", "shako 400 fg<br>", "SellerA")
                + _card("Oct 8 2026 12:04pm", "222222222", "shako 410 fg<br>", "SellerA"))
        q = D.parse_public_quote(html, ITEM, READ_AT)
        db = {"items": {}}
        DB.ingest(db, q, "test", now=1, key="harlequin crest")
        posts = db["items"]["harlequin crest"]["posts"]
        self.assertEqual(len(posts), 2, posts)
        for row in posts.values():
            self.assertEqual(row.get("author"), "SellerA")
            self.assertTrue(row["link"].startswith("https://forums.d2jsp.org/topic.php?t="))


RED_PROOF = [
    {"why": "v3893 (#180, REG-3554) - two topics from the same readable seller each keep a full vote",
     "file": "functions/api/d2jsp_quote.js",
     "find": "  if (a) return 'seller:' + a.toLowerCase();\n",
     "replace": "  if (false && a) return 'seller:' + a.toLowerCase();\n",
     "matches": 1},
    {"why": "v3894 - a new undated topic inherits the last seller (authors not reset when the link changes)",
     "file": "functions/api/d2jsp_quote.js",
     "find": "      if (when != null && !used) { link = here; pending = ''; authors = []; }\n",
     "replace": "      if (when != null && !used) { link = here; pending = ''; }\n",
     "matches": 1},
    {"why": "v3894 - a user.php mention in a post body becomes the seller again",
     "file": "functions/api/d2jsp_quote.js",
     "find": "    if (!named && !/\\bfg\\b/i.test(line)) {\n      hereWho.forEach(function (n) { authors.push(n); });\n    }\n",
     "replace": "    hereWho.forEach(function (n) { authors.push(n); });\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
