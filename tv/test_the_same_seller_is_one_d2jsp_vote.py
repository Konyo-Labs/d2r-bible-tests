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


def _signed_in(topic, seller, when, body):
    """his signed-in results page, by shape (MEASURED 11-11 on his 5 kept pages): the header line carries the topic link "by"
    the seller (an icon <div> INSIDE the seller's anchor), the date sits on the NEXT line, then the body"""
    return ('<dl><dd><label class="srL"><input type="checkbox">'
            '<div class="p3 srH"><div><div class="sX s0b"></div> <a href="topic.php?t=%s&amp;f=268&amp;p=1">Selling stuff</a>'
            ' by <a href="user.php?i=7">%s<div class="sX s4"></div></a> in <a href="forum.php?f=268">D2:R Trading</a></div>'
            '<div class="desc"><div class="desc p3">\n\t%s\n</div></div></div>'
            '<div class="p3 bc1 bts srB">%s</div></label></dd></dl>' % (topic, seller, when, body))


class AHeaderFirstPageKeepsItsSeller(unittest.TestCase):
    """v3898 (#180, GrokBot #230 6798004838: no stored Enigma row had a seller). The signed-in page puts the seller on the line
    ABOVE the date and the date line wiped it: 0 of 42 rows on his 5 kept pages carried a seller, 5 lost their link."""

    def test_the_seller_on_the_header_line_reaches_the_row(self):
        html = (_signed_in("333333333", "SellerA", "Nov 8 2026 02:22am", "shako 400 fg<br>")
                + _signed_in("444444444", "SellerA", "Nov 9 2026 02:22am", "shako 410 fg<br>")
                + _signed_in("555555555", "SellerB", "Nov 9 2026 05:22am", "shako 380 fg<br>"))
        posts = D.parse_public_quote(html, ITEM, "2026-11-10T07:00:00Z")["posts"]
        got = sorted((p["link"].split("t=")[1].split("&")[0], p.get("author"), p["w"]) for p in posts)
        self.assertEqual(got, [("333333333", "SellerA", 0.5), ("444444444", "SellerA", 0.5), ("555555555", "SellerB", 1)],
                         "a header-first post lost its seller or its link: %s" % posts)

    def test_a_post_after_an_unpriced_post_keeps_its_own_link(self):
        """the 5 lost links: a header that follows a post with no priced row was folded into that post, then its own date
        line found no link left"""
        html = (_signed_in("333333333", "SellerA", "Nov 8 2026 02:22am", "wts lots of runes<br>")
                + _signed_in("444444444", "SellerB", "Nov 9 2026 02:22am", "shako 410 fg<br>"))
        posts = D.parse_public_quote(html, ITEM, "2026-11-10T07:00:00Z")["posts"]
        self.assertEqual([(p["link"].split("t=")[1].split("&")[0], p.get("author")) for p in posts], [("444444444", "SellerB")])

    def test_a_topic_link_in_a_shop_body_is_not_the_post(self):
        """MEASURED on his shako page: a shop post's "see topic.php?t=..." gave the Shako row that OTHER topic's link"""
        body = ('Protector Stone - BIN 2.5K <a href="https://forums.d2jsp.org/topic.php?t=999999999&amp;f=268">'
                'https://forums.d2jsp.org/topic.php?t=999999999&amp;f=268</a><br>Silkweave - 5fg<br>shako 138def - 20fg<br>')
        posts = D.parse_public_quote(_signed_in("333333333", "SellerA", "Nov 8 2026 02:22am", body), ITEM,
                                     "2026-11-10T07:00:00Z")["posts"]
        self.assertEqual([(p["fg"], p["link"].split("t=")[1].split("&")[0], p.get("author")) for p in posts],
                         [(20, "333333333", "SellerA")], posts)

    def test_a_body_mention_does_not_unname_the_seller(self):
        body = 'ask <a href="user.php?i=9">Mentioned</a> too<br>shako 400 fg<br>'
        posts = D.parse_public_quote(_signed_in("333333333", "SellerA", "Nov 8 2026 02:22am", body), ITEM,
                                     "2026-11-10T07:00:00Z")["posts"]
        self.assertEqual([p.get("author") for p in posts], ["SellerA"], posts)


class TheSameSellerIsOneVoteAcrossReadings(unittest.TestCase):
    """v3898 (#180) - the parser shares a seller's vote inside ONE read; the DB holds many reads. A seller's two topics
    stored from two reads (each w=1 at its read) share one vote in price() and in explain()."""

    def _db(self, rows):
        import time as _t
        now = _t.time()
        day = _t.strftime("%Y-%m-%d", _t.localtime(now))
        posts = {}
        for t, fg, who in rows:
            link = "https://forums.d2jsp.org/topic.php?t=%s&f=268" % t
            posts[link] = {"fg": fg, "day": day, "link": link, "w": 1.0, "perfect": True, "src": "t", "seenAt": now}
            if who:
                posts[link]["author"] = who
        return {"schema": DB.SCHEMA, "items": {"enigma": {"item": "Enigma", "readAt": now, "posts": posts}}}, now

    def test_one_sellers_relist_from_another_read_shares_one_vote(self):
        db, now = self._db([(1, 1850, "SellerA"), (2, 1850, "sellera"), (3, 1400, "SellerB")])
        pr = DB.price(db, "Enigma", now=now)["perfect"]
        self.assertEqual(pr["fg"], 1400, "one seller's relist out-voted another seller: %s" % pr)
        ws = sorted((r["fg"], r["vote"]) for r in DB.explain(db, "Enigma", now=now)["posts"])   # v3899: #151's vote_shares
        self.assertEqual(ws, [(1400, 1.0), (1850, 0.5), (1850, 0.5)], "the proof does not show the weights the price used")

    def test_unknown_or_different_sellers_keep_a_full_vote_each(self):
        """BASELINE - no stored author (every row before v3898) stays one vote per link; nothing is invented"""
        db, now = self._db([(1, 1850, None), (2, 1850, None), (3, 1400, "SellerB")])
        self.assertEqual(DB.price(db, "Enigma", now=now)["perfect"]["fg"], 1850)
        self.assertEqual(sorted(r["vote"] for r in DB.explain(db, "Enigma", now=now)["posts"]), [1.0, 1.0, 1.0])


RED_PROOF = [
    {"why": "v3893 (#180, REG-3554) - two topics from the same readable seller each keep a full vote",
     "file": "functions/api/d2jsp_quote.js",
     "find": "  if (a) return 'seller:' + a.toLowerCase();\n",
     "replace": "  if (false && a) return 'seller:' + a.toLowerCase();\n",
     "matches": 1},
    {"why": "v3894 - a new undated topic inherits the last seller (authors not reset when the link changes)",
     "file": "functions/api/d2jsp_quote.js",
     "find": "      if (when != null && !used && order !== 'link') { link = here; pending = ''; authors = []; }\n",
     "replace": "      if (when != null && !used && order !== 'link') { link = here; pending = ''; }\n",
     "matches": 1},
    {"why": "v3894 - a user.php mention in a post body becomes the seller again",
     "file": "functions/api/d2jsp_quote.js",
     "find": "    if (order === 'link' ? !!here : (!named && !/\\bfg\\b/i.test(line))) {\n      hereWho.forEach(function (n) { authors.push(n); });\n    }\n",
     "replace": "    hereWho.forEach(function (n) { authors.push(n); });\n",
     "matches": 1},
    {"why": "v3898 (#180) - the date line wipes the seller its header line just read (0 of 42 rows carried a seller)",
     "file": "functions/api/d2jsp_quote.js",
     "find": "      if (!kept) authors = [];   /* v3898 - a header-first post's seller came on its link line */\n",
     "replace": "      authors = [];\n",
     "matches": 1, "needs": "node"},
    {"why": "v3898 (#180) - a header-first page is read as date-first again: a post after an unpriced one loses its link",
     "file": "functions/api/d2jsp_quote.js",
     "find": "    if (!order && here && d == null && hereWho.length === 1) order = 'link';\n",
     "replace": "    if (false) order = 'link';\n",
     "matches": 1, "needs": "node"},
    {"why": "v3898 (#180) - a topic link in a shop's body takes the row's link again",
     "file": "functions/api/d2jsp_quote.js",
     "find": "    if (order === 'link' && here && !hereWho.length) here = '';\n",
     "replace": "    if (false) here = '';\n",
     "matches": 1, "needs": "node"},
    {"why": "v3898 (#180) - one seller's relist stored from another read keeps a full vote again",
     "file": "tv/d2jsp_price_db.py",
     "find": "            union(me, \"seller:\" + who.lower())\n",
     "replace": "            pass\n",
     "matches": 1},
    {"why": "v3898 (#180) - the price stops sharing the seller's vote while the proof still shows it shared",
     "file": "tv/d2jsp_price_db.py",
     "find": "        _age, w = _age_weight(p, now, share)\n        if w > 0:\n            pairs.append((p[\"fg\"], w))\n            votes += share\n",
     "replace": "        _age, w = _age_weight(p, now)\n        if w > 0:\n            pairs.append((p[\"fg\"], w))\n            votes += share\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
