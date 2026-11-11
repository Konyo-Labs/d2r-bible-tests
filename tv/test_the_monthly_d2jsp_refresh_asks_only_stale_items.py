# -*- coding: utf-8 -*-
"""#151 (REG-3794) - THE MONTHLY REFRESH RE-ASKS ONLY THE STALE ITEMS, AT THE SAME 1 SEARCH A MINUTE.

His 11-08 ruling: a ~2-year backfill, then a monthly refresh. Nothing re-opened a finished item: once every queued
item was done the runner said "every queued item is done" forever. d2jsp_backfill.queue_monthly_refresh re-opens an
item only when its backfill finished and the price file last read it over MONTHLY_DAYS ago (or never); it pages back
only to the day before that read ("caught up"), and the pace is run_once's own lastAskAt. Fixtures only; every fetch is
handed in, nothing opens a socket. RED_PROOF below.
"""
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import d2jsp_backfill as B  # noqa: E402
import d2jsp_price_db as P  # noqa: E402

DAY = 86400.0
NOW = 1794412146.0                                   # 2026-11-11
NEXT = '<a href="search.php?f=268&amp;o=%d">Next</a>'


def _db(read_ats):
    items = {}
    for name, ra in read_ats.items():
        link = "https://forums.d2jsp.org/topic.php?t=%d&f=268" % (abs(hash(name)) % 10 ** 8)
        items[P.key_of(name)] = {"item": name, "readAt": ra, "posts": {link: {
            "fg": 10.0, "day": "2026-09-01", "link": link, "w": 1, "perfect": False, "src": "t", "seenAt": ra,
            "author": None}}}
    return {"schema": 1, "items": items}


class TheMonthlyRefresh(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="d2jsp_mr_")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.prog = os.path.join(self.d, "progress.json")
        self.db = os.path.join(self.d, "prices.json")
        rec = B.empty_progress(["Shako", "Ber", "Jah", "Cruel"])
        for n in ("Shako", "Ber", "Jah"):
            rec["items"][P.key_of(n)] = {"item": n, "offset": 40, "pages": 3, "folded": 5, "done": True, "why": "last page"}
        rec["items"]["cruel"] = {"item": "Cruel", "offset": 20, "pages": 2, "folded": 1, "done": False, "why": "next o=20"}
        rec["lastAskAt"] = NOW - 10
        B.progress_save(self.prog, rec)
        P.save(self.db, _db({"Shako": NOW - 40 * DAY, "Ber": NOW - 2 * DAY, "Cruel": NOW - 90 * DAY}))   # Jah: never

    def test_only_finished_stale_items_are_reopened(self):
        got = B.queue_monthly_refresh(self.prog, self.db, now=NOW)
        self.assertEqual(sorted(got["queued"]), ["Jah", "Shako"], got)
        rec = B.progress_load(self.prog)
        self.assertEqual(rec["items"]["shako"]["offset"], 0)
        self.assertEqual(rec["items"]["shako"]["since"], "2026-10-01")       # the day before its last read
        self.assertNotIn("since", rec["items"]["jah"], "a never-read item must read its whole window")
        self.assertTrue(rec["items"]["ber"]["done"], "a fresh item was re-opened")
        self.assertEqual(rec["items"]["cruel"]["offset"], 20, "a mid-backfill item lost its offset")
        again = B.queue_monthly_refresh(self.prog, self.db, now=NOW)
        self.assertEqual(again["queued"], [], "an item already re-opened was re-opened again")
        self.assertEqual(B.progress_load(self.prog)["items"]["shako"]["since"], "2026-10-01")

    def test_the_refresh_keeps_the_one_search_a_minute_pace(self):
        B.queue_monthly_refresh(self.prog, self.db, now=NOW)
        out = B.run_once(self.prog, self.db, fetch=lambda i, o: "<html></html>", now=NOW + 30)
        self.assertFalse(out["worked"], out)
        self.assertIn("1 search/min", out["why"])

    def test_a_refresh_stops_paging_at_its_last_read(self):
        B.queue_monthly_refresh(self.prog, self.db, now=NOW)
        rec = B.progress_load(self.prog)
        rec["cursor"] = rec["queue"].index("Shako")
        B.progress_save(self.prog, rec)
        asked = []

        def fetch(item, offset):
            asked.append((item, offset))
            return "<html>Search Results %s</html>" % (NEXT % (offset + 25))

        def parse(html, item, read_at):
            day = "2026-11-02" if not asked[-1][1] else "2026-09-20"
            return {"reason": "read", "item": item, "posts": [{"fg": 12, "day": day, "w": 1,
                    "link": "https://forums.d2jsp.org/topic.php?t=%d&f=268" % (5 + len(asked))}]}

        B.run_once(self.prog, self.db, fetch=fetch, parse=parse, now=NOW + 60)
        second = B.run_once(self.prog, self.db, fetch=fetch, parse=parse, now=NOW + 120)
        self.assertEqual(asked, [("Shako", 0), ("Shako", 25)], asked)
        self.assertTrue(second["done"], second)
        self.assertIn("caught up", second["why"])


RED_PROOF = [
    {"why": "REG-3794 - the refresh re-opens a fresh item too",
     "file": "tv/d2jsp_backfill.py",
     "find": "        if held is not None and read_at > 0 and now - read_at <= days * 86400:\n            continue\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3794 - a refreshed item pages back its whole 2 years again",
     "file": "tv/d2jsp_backfill.py",
     "find": "        if since and nxt is not None and days and all(d < since for d in days):\n",
     "replace": "        if False:\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
