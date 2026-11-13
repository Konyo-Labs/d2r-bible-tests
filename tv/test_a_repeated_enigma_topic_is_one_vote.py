# -*- coding: utf-8 -*-
"""#180 (the open half of REG-3792) - A MEASURED REPOST IS ONE VOTE ON EVERY DB, AND A DECLARED ONE SURVIVES A RE-READ.

GrokBot's look on the three non-ladder Enigma topics (#230): t=110566436 repeats t=110552180's two lines word for word -
one ask, listed twice - yet the stored Enigma "perfect" weighed it beside the original (1.5 votes, 11-11 16:07). REG-3792
gave the DB a way to say so (a row's sameAs, mark_same_listing), but nothing in the console ever called it, and ingest
rewrote a re-read row without its sameAs. Now:
  1. SAME_TOPICS (d2jsp_price_db) holds the measured repost; every DB that is LOADED or FOLDED declares it
     (declare_same_topics -> mark_same_listing, its first caller), so vote_shares makes it one vote on every PC with the
     seller unread - both topics stay on record, and no unmeasured topic is ever guessed the same;
  2. a sameAs written on a row is kept when the topic is read again.
Enigma's NORMAL tier stays UNKNOWN while every kept Enigma post states the 775 roll (REG-3441 files those perfect) - the
DB never prices a normal Enigma from perfect posts, and says UNKNOWN instead of 0. RED_PROOF below.
"""
import os
import shutil
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import d2jsp_price_db as P  # noqa: E402

NOW = time.mktime(time.strptime("2026-11-13", "%Y-%m-%d"))


def _link(t, p):
    return "https://forums.d2jsp.org/topic.php?t=%d&f=268&p=%d" % (t, p)


def _enigma():
    """His console's Enigma rows as GrokBot read them on 11-09 (sellers unread, as they were stored)."""
    db = P.empty()
    rows = [(1850, 110566436, 696103201, 1.0, "2026-11-08"), (1400, 110563895, 696084987, 1.0, "2026-11-06"),
            (1850, 110552180, 696008307, 1.0, "2026-11-05")]
    posts = {}
    for fg, t, p, w, day in rows:
        posts[_link(t, p)] = {"fg": fg, "day": day, "link": _link(t, p), "w": w, "perfect": True, "src": "mac",
                              "seenAt": NOW, "author": None}
    db["items"]["nigma"] = {"item": "Enigma", "readAt": NOW, "posts": posts}
    return db


class AMeasuredRepostIsOneVote(unittest.TestCase):

    def _loaded(self, db):
        d = tempfile.mkdtemp(prefix="enigma-")
        self.addCleanup(shutil.rmtree, d, True)
        path = os.path.join(d, "d2jsp_price_db.json")
        P.save(path, db)
        return P.load(path)

    def test_his_loaded_db_casts_the_repost_and_its_original_as_one_vote(self):
        db = self._loaded(_enigma())
        tier = P.price(db, "Enigma", NOW, key="nigma")["perfect"]
        self.assertEqual(tier["votes"], 2.0, "110566436 and 110552180 (one listing) weighed as two: %r" % tier)
        self.assertEqual(tier["n"], 3, "a topic was dropped from the record")

    def test_a_fold_that_brings_both_halves_declares_them(self):
        db = P.empty()
        posts = [{"fg": 1850, "day": "2026-11-05", "link": _link(110552180, 1), "perfect": True},
                 {"fg": 1850, "day": "2026-11-08", "link": _link(110566436, 2), "perfect": True}]
        P.ingest(db, {"item": "Enigma", "reason": "read", "searched": "nigma", "posts": posts}, "mac", now=NOW)
        self.assertEqual(P.price(db, "Enigma", NOW, key="nigma")["perfect"]["votes"], 1.0, "a fold kept the repost apart")

    def test_unmeasured_topics_still_count_apart(self):
        db = _enigma()
        for p in list(db["items"]["nigma"]["posts"].values()):
            p["link"] = p["link"].replace("t=110566436", "t=110566437")
        db["items"]["nigma"]["posts"] = {p["link"]: p for p in db["items"]["nigma"]["posts"].values()}
        self.assertEqual(P.price(self._loaded(db), "Enigma", NOW, key="nigma")["perfect"]["votes"], 3.0,
                         "an unmeasured topic was guessed the same")

    def test_the_normal_tier_is_unknown_never_zero(self):
        pr = P.price(_enigma(), "Enigma", NOW, key="nigma")
        self.assertIsNone(pr["normal"]["fg"], "perfect posts priced a normal Enigma")
        self.assertIn("UNKNOWN", P.db_first({"schema": P.SCHEMA, "items": {"nigma": {"item": "Enigma", "readAt": NOW,
                      "posts": {}}}}, "Enigma", NOW, key="nigma")["say"])


class ADeclaredSameListingSurvivesARead(unittest.TestCase):

    def test_a_reread_keeps_the_rows_same_as(self):
        db = P.empty()
        reading = {"item": "Shako", "reason": "read", "searched": "shako",
                   "posts": [{"fg": 20, "day": "2026-11-10", "link": _link(5001, 1)},
                             {"fg": 20, "day": "2026-11-11", "link": _link(5002, 2)}]}
        P.ingest(db, reading, "mac", now=NOW)
        self.assertEqual(P.mark_same_listing(db, "Shako", "5002", "5001", key="shako"), 1)
        P.ingest(db, reading, "mac", now=NOW + 60)
        self.assertEqual(db["items"]["shako"]["posts"][_link(5002, 2)].get("sameAs"), "5001",
                         "a re-read wiped the declared same listing")
        self.assertEqual(P.price(db, "Shako", NOW + 60, key="shako")["normal"]["votes"], 1.0)


RED_PROOF = [
    {"why": "#180 - a loaded DB weighs the measured Enigma repost as a second listing again",
     "file": "d2jsp_price_db.py",
     "find": "        return None\n    declare_same_topics(db)\n", "replace": "        return None\n", "matches": 1},
    {"why": "#180 - a fold that brings both halves of the repost keeps them apart",
     "file": "d2jsp_price_db.py",
     "find": "    declare_same_topics({\"items\": {k: it}})", "replace": "    pass", "matches": 1},
    {"why": "#180 - no repost is measured",
     "file": "d2jsp_price_db.py",
     "find": "SAME_TOPICS = {\"110566436\": \"110552180\"}", "replace": "SAME_TOPICS = {}", "matches": 1},
    {"why": "#180 - a re-read wipes a declared same listing",
     "file": "d2jsp_price_db.py",
     "find": "            row[\"sameAs\"] = str(old_row[\"sameAs\"]).strip()   # #180 - a declared same listing survives a re-read\n",
     "replace": "            pass\n", "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
