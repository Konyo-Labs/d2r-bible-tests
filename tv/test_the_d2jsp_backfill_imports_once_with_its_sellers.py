# -*- coding: utf-8 -*-
"""#151 (REG-3790) - THE BACKFILL'S PRICES FOLD INTO THE STORED DB ONCE, EVERY ROW SAYING ITS SELLER.

His rulings (11-08): every item, a ~2-year backfill, then the price DB the console prices from. The backfill wrote its own
prices-shard0.json (158 items, 1,832 rows on 11-11) and nothing folded it in. d2jsp_price_db.import_backfill does:
  * IDEMPOTENT - importing the same file again adds nothing and leaves the DB byte-identical;
  * every stored row carries "author": the seller, or None when the page did not name one - never invented, and a
    later file that names the seller fills a None, never replaces a known one;
  * a post without a price (or its forum link) is not a post: skipped whole, and counted.
Fixtures only; no network. RED_PROOF below.
"""
import copy
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import d2jsp_price_db as P  # noqa: E402

L = "https://forums.d2jsp.org/topic.php?t=%d&f=268&p=%d"


def _row(fg, t, day="2026-11-05", author=None, perfect=False, w=1.0, link=True):
    r = {"fg": fg, "day": day, "link": (L % (t, t * 10)) if link else "", "w": w, "perfect": perfect,
         "src": "backfill-shard0", "seenAt": 1794305904.9}
    if author is not None:
        r["author"] = author
    return r


def _file(rows, read_at=1794305904.9):
    posts = {}
    for r in rows:
        posts[r["link"] or "%s|%s|[]" % (r["fg"], r["day"])] = r
    return {"schema": 1, "items": {"enigma": {"item": "Enigma", "readAt": read_at, "posts": posts}}}


class TheBackfillImportsOnce(unittest.TestCase):

    def test_the_same_file_twice_adds_nothing(self):
        src = _file([_row(1850, 110552180, perfect=True), _row(280, 110577047), _row(360, 110576193)])
        db = P.empty()
        first = P.import_backfill(db, copy.deepcopy(src))
        self.assertEqual(first["new"], 3, first)
        once = json.dumps(db, sort_keys=True)
        again = P.import_backfill(db, copy.deepcopy(src))
        self.assertEqual(again["new"], 0, again)
        self.assertEqual(json.dumps(db, sort_keys=True), once, "a second import of the same file changed the DB")
        self.assertEqual(len(db["items"]["enigma"]["posts"]), 3)

    def test_every_row_says_its_seller_or_none(self):
        src = _file([_row(1850, 110552180, perfect=True), _row(280, 110577047, author="SellerB")])
        db = P.empty()
        P.import_backfill(db, src)
        rows = list(db["items"]["enigma"]["posts"].values())
        self.assertTrue(all("author" in r for r in rows), rows)
        self.assertEqual(sorted(str(r["author"]) for r in rows), ["None", "SellerB"], rows)

    def test_a_later_file_fills_a_missing_seller_and_never_clears_one(self):
        db = P.empty()
        P.import_backfill(db, _file([_row(1850, 110552180, perfect=True), _row(280, 110577047, author="SellerB")]))
        later = _file([_row(1850, 110552180, perfect=True, author="SellerA"), _row(280, 110577047)])
        got = P.import_backfill(db, later)
        self.assertEqual(got["authorFilled"], 1, got)
        by = {P.topic_of(r["link"]): r["author"] for r in db["items"]["enigma"]["posts"].values()}
        self.assertEqual(by, {"110552180": "SellerA", "110577047": "SellerB"}, by)

    def test_a_post_without_a_price_is_skipped_whole(self):
        src = _file([_row(1850, 1, perfect=True), _row(0, 2), _row("inf", 3), _row(True, 4), _row("nan", 5),
                     _row(500, 6, link=False)])
        db = P.empty()
        got = P.import_backfill(db, src)
        self.assertEqual(got["new"], 1, got)
        self.assertEqual(got["skippedNoPrice"], 4, got)
        self.assertEqual(got["skippedNoLink"], 1, got)
        self.assertEqual([P.topic_of(k) for k in db["items"]["enigma"]["posts"]], ["1"])

    def test_an_import_never_makes_an_item_look_fresher(self):
        db = P.empty()
        P.import_backfill(db, _file([_row(280, 1)], read_at=2000.0))
        P.import_backfill(db, _file([_row(280, 1)], read_at=1000.0))
        self.assertEqual(db["items"]["enigma"]["readAt"], 2000.0)


RED_PROOF = [
    {"why": "REG-3790 - a stored post is added again (and re-stamped) on every import of the same file",
     "file": "tv/d2jsp_price_db.py",
     "find": "            cur = it[\"posts\"].get(pk)\n            if cur is not None:\n",
     "replace": "            cur = it[\"posts\"].get(pk)\n            if False:\n",
     "matches": 1},
    {"why": "REG-3790 - a row with no seller is stored without its author field",
     "file": "tv/d2jsp_price_db.py",
     "find": "                   \"seenAt\": float(p.get(\"seenAt\") or 0), \"author\": author_of(p)}\n",
     "replace": "                   \"seenAt\": float(p.get(\"seenAt\") or 0)}\n            if author_of(p):\n                row[\"author\"] = author_of(p)\n",
     "matches": 1},
    {"why": "REG-3790 - a post without a price is imported",
     "file": "tv/d2jsp_price_db.py",
     "find": "            fg = price_of(p.get(\"fg\"))\n            if fg is None or _day_ts(p.get(\"day\")) is None:\n                stats[\"skippedNoPrice\"] += 1\n",
     "replace": "            fg = float(p.get(\"fg\") or 0)\n            if _day_ts(p.get(\"day\")) is None:\n                stats[\"skippedNoPrice\"] += 1\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
