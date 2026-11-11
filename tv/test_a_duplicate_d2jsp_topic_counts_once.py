# -*- coding: utf-8 -*-
"""#151 / #180 (REG-3792) - A DUPLICATE TOPIC COUNTS ONCE: ONE SELLER, ONE TOPIC, ONE VOTE - CAST AT PRICE TIME.

MEASURED 11-11 16:07 on his console DB (GrokBot 6798004838): Enigma perfect weighed topic 110566436 at w 0.5 beside its
duplicate 110552180 at w 1.0 - 1.5 votes for one listing - and 110566436's other half-vote had folded onto the same link.
The parser shares a vote only between rows on ONE page; a seller's two topics are rarely on one page and the stored
0.5 was a leftover. vote_shares groups every stored row of a tier: rows sharing a seller, a topic (t=), or a declared
same listing (sameAs) never weigh more than ONE vote together; a group under one keeps its stored w (a shop post's 1/28
row is not raised). Unknown sellers in different topics stay a group each - never guessed.
Fixtures only. RED_PROOF below.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import d2jsp_price_db as P  # noqa: E402

NOW = 1794412146.0          # 11-11
L = "https://forums.d2jsp.org/topic.php?t=%d&f=268&p=%d"


def _enigma(author_a=None, author_b=None, author_c=None):
    """His Enigma perfect tier as the console held it on 11-11 (fg, topic, w, day)."""
    rows = [(1850, 110566436, 0.5, "2026-11-08", author_a), (1400, 110563895, 1.0, "2026-11-06", author_c),
            (1850, 110552180, 1.0, "2026-11-05", author_b)]
    posts = {}
    for fg, t, w, day, who in rows:
        link = L % (t, t + 1)
        posts[link] = {"fg": float(fg), "day": day, "link": link, "w": w, "perfect": True, "src": "mac",
                       "seenAt": NOW - 3600, "author": who}
    return {"schema": 1, "items": {"enigma": {"item": "Enigma", "readAt": NOW - 3600, "posts": posts}}}


class ADuplicateTopicCountsOnce(unittest.TestCase):

    def test_the_same_seller_in_two_topics_is_one_vote(self):
        tier = P.price(_enigma("SellerA", "sellera", "SellerC"), "Enigma", NOW)["perfect"]
        self.assertEqual(tier["votes"], 2.0, tier)      # 110566436 + 110552180 = 1 vote (was 1.5); 110563895 = 1

    def test_a_declared_same_listing_is_one_vote_with_no_seller_read(self):
        db = _enigma()
        self.assertEqual(P.mark_same_listing(db, "Enigma", "110566436", "110552180"), 1)
        self.assertEqual(P.price(db, "Enigma", NOW)["perfect"]["votes"], 2.0)
        self.assertEqual(len(db["items"]["enigma"]["posts"]), 3, "a duplicate topic was deleted")
        rows = P.explain(db, "Enigma", NOW)["posts"]
        self.assertEqual(sorted(r["vote"] for r in rows), [0.333, 0.667, 1.0], rows)   # 0.5 : 1.0, scaled to one vote

    def test_unknown_sellers_in_different_topics_stay_one_vote_each(self):
        tier = P.price(_enigma(), "Enigma", NOW)["perfect"]
        self.assertEqual(tier["votes"], 2.5, tier)       # no seller read: never guessed the same - each keeps its w
        self.assertEqual(P.mark_same_listing(_enigma(), "Enigma", "110566436", "999"), 0, "marked a topic it lacks")

    def test_two_posts_in_one_topic_are_one_vote(self):
        db = _enigma()
        bump = L % (110552180, 777)
        db["items"]["enigma"]["posts"][bump] = {"fg": 1850.0, "day": "2026-11-07", "link": bump, "w": 1.0,
                                                "perfect": True, "src": "mac", "seenAt": NOW, "author": None}
        self.assertEqual(P.price(db, "Enigma", NOW)["perfect"]["votes"], 2.5)   # 110552180's two posts: 1 vote

    def test_different_sellers_keep_a_vote_each_and_an_outlier_stays_out(self):
        db = _enigma("SellerA", "SellerB", "SellerC")
        db["items"]["enigma"]["posts"]["x"] = {"fg": 9000.0, "day": "2026-11-07", "link": L % (1, 1), "w": 0.0,
                                               "perfect": True, "src": "mac", "seenAt": NOW, "author": "SellerA"}
        tier = P.price(db, "Enigma", NOW)["perfect"]
        self.assertEqual(tier["votes"], 2.5, tier)
        self.assertEqual(tier["n"], 3, tier)

    def test_a_shop_posts_part_vote_is_never_raised(self):
        posts = [{"fg": 2000.0, "day": "2026-10-10", "link": L % (110443322, 1), "w": 0.036, "author": None},
                 {"fg": 20.0, "day": "2026-11-09", "link": L % (110562822, 2), "w": 0.333, "author": None}]
        self.assertEqual(P.vote_shares(posts), [0.036, 0.333], "a 1/28 shop row was given a whole vote")


RED_PROOF = [
    {"why": "REG-3792 - a group's stored w is not capped at one vote: the duplicate weighs 1.5",
     "file": "tv/d2jsp_price_db.py",
     "find": "        out.append(w / t if t > 1.0 else w)\n",
     "replace": "        out.append(w)\n",
     "matches": 1},
    {"why": "REG-3792 - the same seller's two topics are two votes",
     "file": "tv/d2jsp_price_db.py",
     "find": "            union(me, \"seller:\" + who.lower())\n",
     "replace": "            pass\n",
     "matches": 1},
    {"why": "REG-3792 - two posts in one topic are two votes",
     "file": "tv/d2jsp_price_db.py",
     "find": "            union(me, \"topic:\" + t)\n",
     "replace": "            union(me, \"topic:\" + t + str(i))\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
