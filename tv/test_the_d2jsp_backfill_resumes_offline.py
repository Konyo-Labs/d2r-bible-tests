# -*- coding: utf-8 -*-
"""#151 (REG-3620) - THE d2jsp BACKFILL RESUMES OFFLINE AND NEVER STARTS A LIVE SCRAPE.

His rulings: signed-in, 1 search/min, a ~2-year backfill then a monthly refresh; only priced posts
with links; the same seller is one post and one price; never post or trade. Step 1 (REG-3491) keeps
scrubbed results pages so a pager can be built. This law is step 2: the runner walks &o= from those
pages, folds priced posts into the price DB, and a killed run picks up at the saved offset.

Every fetch is handed in. The tests never open a network socket. A call with no fetch asks nothing.
Fixtures only. RED_PROOF below.
"""
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import d2jsp_backfill as B  # noqa: E402
import d2jsp_price_db as P  # noqa: E402

PAGE1 = ('<html><body>Search Results '
         '<a href="search.php?f=268&amp;o=25">Next</a>'
         '<div>Enigma 775 - 1.4k fg</div></body></html>')
PAGE2 = ('<html><body>Search Results '
         '<div>Enigma 500 - 400 fg</div></body></html>')


def _reading(html, item, read_at, fg=1400, topic=1, author="SellerA"):
    return {"reason": "read", "item": item, "searched": "enigma",
            "posts": [{"fg": fg, "day": "2026-01-15", "w": 1,
                       "link": "https://forums.d2jsp.org/topic.php?t=%d" % topic,
                       "author": author, "perfect": fg >= 1400}]}


class TheBackfillResumesOffline(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="d2jsp_bf_")
        self.addCleanup(lambda: __import__("shutil").rmtree(self.d, True))
        self.prog = os.path.join(self.d, "progress.json")
        self.db = os.path.join(self.d, "prices.json")

    def test_no_fetch_asks_nothing(self):
        out = B.run_once(self.prog, self.db, items=["Enigma"])
        self.assertFalse(out["worked"], out)
        self.assertIn("no fetch handed in", out["why"])
        self.assertFalse(os.path.exists(self.db), "a no-fetch pass wrote a price database")

    def test_the_pager_reads_next_and_a_last_page_has_none(self):
        self.assertEqual(B.pager_offset(PAGE1), 25)
        self.assertIsNone(B.pager_offset(PAGE2), "a last page invented a next offset")
        self.assertIsNone(B.pager_offset(""), "an empty page invented a next offset")

    def test_a_killed_run_resumes_at_the_saved_offset(self):
        seen = []

        def fetch(item, offset):
            seen.append((item, offset))
            return PAGE1 if offset == 0 else PAGE2

        def parse(html, item, read_at):
            return _reading(html, item, read_at, fg=1400 if "Next" in html else 400,
                            topic=1 if "Next" in html else 2,
                            author="SellerA" if "Next" in html else "SellerB")

        first = B.run_once(self.prog, self.db, fetch=fetch, parse=parse, now=1_700_000_000,
                           items=["Enigma"], min_gap_s=0)
        self.assertTrue(first["worked"], first)
        self.assertEqual(first["asked"], "Enigma")
        self.assertEqual(first["offset"], 0)
        self.assertFalse(first["done"], first)
        rec = B.progress_load(self.prog)
        self.assertEqual(rec["items"][P.key_of("Enigma")]["offset"], 25, rec)
        self.assertFalse(rec["items"][P.key_of("Enigma")]["done"], rec)

        second = B.run_once(self.prog, self.db, fetch=fetch, parse=parse, now=1_700_000_120,
                            min_gap_s=0)
        self.assertEqual(seen, [("Enigma", 0), ("Enigma", 25)], "the second pass did not resume at o=25: %s" % seen)
        self.assertTrue(second["done"], second)
        rec = B.progress_load(self.prog)
        self.assertTrue(rec["items"][P.key_of("Enigma")]["done"], rec)
        db = P.load(self.db)
        posts = (db["items"].get("enigma") or {}).get("posts") or {}
        self.assertEqual(len(posts), 2, "both pages' priced posts were not folded: %s" % list(posts))

    def test_the_pace_is_one_search_a_minute(self):
        def fetch(item, offset):
            return PAGE2

        first = B.run_once(self.prog, self.db, fetch=fetch, parse=lambda *a: _reading(*a),
                           now=1_700_000_000, items=["Enigma"], min_gap_s=60)
        self.assertTrue(first["worked"], first)
        again = B.run_once(self.prog, self.db, fetch=fetch, parse=lambda *a: _reading(*a),
                           now=1_700_000_030, items=["Enigma"], min_gap_s=60)
        self.assertFalse(again["worked"], again)
        self.assertIn("1 search/min", again["why"])

    def test_the_same_seller_is_one_vote_in_the_folded_db(self):
        """#180 / #30: two topics from SellerA share one vote once the existing weigher sees the author."""
        pages = [
            _reading("x", "Enigma", 0, fg=500, topic=110552180, author="SellerA"),
            _reading("x", "Enigma", 0, fg=500, topic=110566436, author="SellerA"),
        ]
        n = [0]

        def fetch(item, offset):
            return PAGE2 if n[0] else PAGE1

        def parse(html, item, read_at):
            i = n[0]
            n[0] += 1
            return pages[min(i, 1)]

        B.run_once(self.prog, self.db, fetch=fetch, parse=parse, now=1_700_000_000,
                   items=["Enigma"], min_gap_s=0)
        B.run_once(self.prog, self.db, fetch=fetch, parse=parse, now=1_700_000_120,
                   min_gap_s=0)
        db = P.load(self.db)
        held, _ra = P._held(db, "Enigma")
        authors = {p.get("author") for p in (held or {}).values()}
        self.assertEqual(authors, {"SellerA"}, held)
        # both topic rows stay (evidence); the weigher (REG-3554) shares their vote when asked
        self.assertEqual(len(held or {}), 2, held)


RED_PROOF = [
    {"why": "REG-3620 - a pass with no fetch is marked as if the forum was asked",
     "file": "tv/d2jsp_backfill.py",
     "find": '            out["why"] = "no fetch handed in - nothing is asked (the live scrape is not started from here)"\n            return out\n',
     "replace": '            out["why"] = "fetch skipped"\n            out["worked"] = True\n            return out\n',
     "matches": 1},
    {"why": "REG-3620 - a killed run forgets its offset and starts the item again at o=0",
     "file": "tv/d2jsp_backfill.py",
     "find": '            st["offset"] = int(nxt)\n',
     "replace": "            st[\"offset\"] = 0\n",
     "matches": 1},
    {"why": "REG-3620 - the 1 search/min pace is not honoured",
     "file": "tv/d2jsp_backfill.py",
     "find": "        if last and now - last < gap:\n",
     "replace": "        if False and last and now - last < gap:\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
