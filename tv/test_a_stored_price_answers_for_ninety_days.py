# -*- coding: utf-8 -*-
"""Job E item 1 (Claude's #230 6849292433) - A PRICE CHECK ANSWERS FROM THE STORED PRICE WHILE ITS READ IS UNDER 90 DAYS OLD.

His 11-13 words on #96: "even for like 3 months.. price database going back to 2025 so those prices should be correct and
good to use". The branch searched d2jsp on click for any item read more than 3 days ago (REFRESH_DAYS = 3) - and for any
item whose newest post was over 45 days old (STALE_POST_DAYS), which made every quiet item searched on every click. Now:
  * d2jsp_price_db.REFRESH_DAYS is 90, and the newest post's age no longer makes an item stale (the backfill reaches 2025:
    an old post is still a good price, and the age decay already weighs it);
  * the price check's plan answers a held item read 60 days ago from the database ("stored"), searching nothing, and its
    answer says how old the read is and when d2jsp is searched again;
  * an item read 95 days ago is searched on that click - one search a minute, as #96 built (that pace is
    test_a_price_check_refreshes_the_stale_item_it_reads's).
Fixture DB in a temp dir; nothing is fetched. RED_PROOF below (hand-proven red/green, GrokBot box build).
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
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import d2jsp_price_db as P  # noqa: E402

NOW = time.mktime(time.strptime("2026-11-13", "%Y-%m-%d"))
DAY = 86400.0


def _db(items):
    db = P.empty()
    for i, (name, read_ago, post_ago) in enumerate(items):
        posts = {}
        for j in range(4):
            link = "https://forums.d2jsp.org/topic.php?t=%d&f=268" % (2000 * (i + 1) + j)
            posts[link] = {"fg": 30, "day": time.strftime("%Y-%m-%d", time.localtime(NOW - post_ago * DAY)), "link": link,
                           "w": 1, "perfect": False, "src": "mac", "seenAt": NOW - read_ago * DAY}
        db["items"][P.key_of(name)] = {"item": name, "readAt": NOW - read_ago * DAY, "posts": posts}
    return db


class TheStoredPriceIsGoodForNinetyDays(unittest.TestCase):

    def test_ninety_days_is_the_line(self):
        self.assertEqual(P.REFRESH_DAYS, 90.0, "the stored price is not trusted for his 3 months")
        db = _db([("Shako", 0, 0)])
        self.assertFalse(P.is_stale(db, "Shako", NOW + 4 * DAY)[0], "a 4-day-old read is searched again (the old 3 days)")
        self.assertFalse(P.is_stale(db, "Shako", NOW + 89 * DAY)[0], "an 89-day-old read is searched again")
        self.assertTrue(P.is_stale(db, "Shako", NOW + 91 * DAY)[0], "a read past 90 days is still trusted")

    def test_an_old_newest_post_does_not_make_an_item_stale(self):
        db = _db([("Tyrael's Might", 2, 300)])        # read 2 days ago; its newest post is from 2025
        self.assertEqual(P.is_stale(db, "Tyrael's Might", NOW), (False, "fresh"),
                         "a quiet item read this week is searched again because its posts are old (the retired 45-day rule)")


class ThePriceCheckAnswersFromTheStoredPrice(unittest.TestCase):

    def setUp(self):
        self._cr = P.checks_running
        P.checks_running = lambda env=None: False
        self.addCleanup(setattr, P, "checks_running", self._cr)
        import control_app as CA
        self.CA = CA
        self.d = tempfile.mkdtemp(prefix="price-90-")
        self.addCleanup(shutil.rmtree, self.d, True)
        P.save(os.path.join(self.d, "d2jsp_price_db.json"), _db([("Shako", 60, 70), ("Gull", 95, 2)]))
        old = os.environ.get("TV_HIST")
        os.environ["TV_HIST"] = self.d
        self.addCleanup(lambda: os.environ.pop("TV_HIST", None) if old is None else os.environ.__setitem__("TV_HIST", old))
        self._canon = CA._d2jsp_canon
        CA._d2jsp_canon = lambda item: P.key_of(item)
        self.addCleanup(setattr, CA, "_d2jsp_canon", self._canon)
        self._pace = dict(CA._D2JSP_REFRESH_PACE)
        CA._D2JSP_REFRESH_PACE["at"] = 0.0
        self.addCleanup(CA._D2JSP_REFRESH_PACE.update, self._pace)

    def test_a_60_day_old_read_is_answered_stored_and_says_its_age(self):
        plan = self.CA._d2jsp_price_check_plan("Shako", now=NOW)
        self.assertEqual(plan["do"], "stored", "a 60-day-old read was searched again: %r" % (plan.get("why"),))
        say = plan["answer"]["say"]
        self.assertIn("read 60 days ago", say, "the stored answer does not say how old its read is")
        self.assertIn("only after 90 days", say, "the stored answer does not say when d2jsp is searched again")
        self.assertEqual(self.CA._D2JSP_REFRESH_PACE["at"], 0.0, "a stored answer spent the minute's search")

    def test_a_95_day_old_read_is_searched_on_the_click(self):
        plan = self.CA._d2jsp_price_check_plan("Gull", now=NOW)
        self.assertEqual(plan["do"], "refresh", plan)


RED_PROOF = [
    {"why": "Job E - the stored price is trusted for 3 days again",
     "file": "tv/d2jsp_price_db.py",
     "find": "REFRESH_DAYS = 90.0\n",
     "replace": "REFRESH_DAYS = 3.0\n",
     "matches": 1},
    {"why": "Job E - the 45-day newest-post rule comes back (every quiet item searched on every click)",
     "file": "tv/d2jsp_price_db.py",
     "find": "    # Job E (his 11-13 ruling) - the age of the newest POST no longer makes an item stale",
     "replace": "    if not [d for d in (_day_ts(p[\"day\"]) for p in held.values()) if d is not None and now - d <= 45 * 86400]:\n"
                "        return True, \"no post in the last 45 days\"\n"
                "    # Job E (his 11-13 ruling) - the age of the newest POST no longer makes an item stale",
     "matches": 1},
    {"why": "Job E - the stored answer stops saying how old its read is",
     "file": "tv/control_app.py",
     "find": "    _age = (\"read %d %s ago\" % (_age_d, \"day\" if _age_d == 1 else \"days\")) if _age_d is not None else \"read time UNKNOWN\"\n",
     "replace": "    _age = \"fresh\"\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
