# -*- coding: utf-8 -*-
"""#96 (his 11-06: "so slowly after time the prices just slowly calibrate themselves ... and for price check it should be
joined logic to the database so this is a communicating and whole system") - A PRICE CHECK REFRESHES THE STALE ITEM IT READS.

Claim refuted on main (GrokBot, #96 build): d2jsp_price_db.fresh_refresh and is_stale had no caller outside their module,
their tests and the timer lane - the /api/d2jsp_quote door searched the forum on every click, fresh or stale, and never
asked the DB first. Now:
  1. fresh_refresh(only=[item], pace=...) is the price check's own refresher: only the item asked, only when stale, one
     forum search per REFRESH_GAP_S (60 s - the backfill's pace) across every check, never a timer of its own;
  2. control_app._d2jsp_price_check_plan reads the DB first: a held stale item -> "refresh" (this check's search), the
     same inside the minute -> "stored" with the wait said, a fresh one -> "stored" (nothing asked), one the DB does not
     hold -> "live" (a first read);
  3. the quote door runs the plan BEFORE d2jsp_quote and answers "stored" without a search.
Fixture DB in a temp dir; nothing is fetched. RED_PROOF below.
"""
import io
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
            link = "https://forums.d2jsp.org/topic.php?t=%d&f=268" % (1000 * (i + 1) + j)
            posts[link] = {"fg": 20, "day": time.strftime("%Y-%m-%d", time.localtime(NOW - post_ago * DAY)), "link": link,
                           "w": 1, "perfect": False, "src": "mac", "seenAt": NOW - read_ago * DAY}
        db["items"][P.key_of(name)] = {"item": name, "readAt": NOW - read_ago * DAY, "posts": posts}
    return db


class _Free(unittest.TestCase):
    def setUp(self):
        self._cr = P.checks_running
        P.checks_running = lambda env=None: False
        self.addCleanup(setattr, P, "checks_running", self._cr)


class FreshRefreshIsThePriceChecksOwn(_Free):

    def test_only_the_item_asked_is_refreshed(self):
        db = _db([("Shako", 5, 1), ("Gull", 9, 2)])
        got = []
        r = P.fresh_refresh(db, got.append, NOW, only=["shako"])
        self.assertEqual(got, ["Shako"], "a price check for Shako refreshed every stale item in the DB")
        self.assertEqual(r["fetched"], ["Shako"])

    def test_a_fresh_item_is_not_asked(self):
        got = []
        P.fresh_refresh(_db([("Shako", 1, 1)]), got.append, NOW, only=["Shako"])
        self.assertEqual(got, [], "a fresh item was asked again")

    def test_one_search_a_minute(self):
        db = _db([("Shako", 5, 1), ("Gull", 9, 2)])
        pace, got = {"at": 0.0}, []
        P.fresh_refresh(db, got.append, NOW, only=["Shako"], pace=pace)
        self.assertEqual(pace["at"], NOW, "the refresh did not stamp its pace")
        r = P.fresh_refresh(db, got.append, NOW + 30, only=["Gull"], pace=pace)
        self.assertEqual(got, ["Shako"], "a second refresh went inside the minute")
        self.assertEqual(r.get("wait"), 30, r)
        P.fresh_refresh(db, got.append, NOW + 61, only=["Gull"], pace=pace)
        self.assertEqual(got, ["Shako", "Gull"], "the next refresh never went after the minute")

    def test_a_paced_pass_fetches_one(self):
        got = []
        P.fresh_refresh(_db([("Shako", 5, 1), ("Gull", 9, 2)]), got.append, NOW, pace={"at": 0.0})
        self.assertEqual(len(got), 1, "a paced pass searched more than once")

    def test_an_item_the_db_lacks_is_not_refreshed_here(self):
        got = []
        P.fresh_refresh(_db([("Shako", 5, 1)]), got.append, NOW, only=["Gull"])
        self.assertEqual(got, [])

    def test_checks_running_fetches_nothing(self):
        P.checks_running = lambda env=None: True
        got = []
        r = P.fresh_refresh(_db([("Shako", 5, 1)]), got.append, NOW, only=["Shako"], pace={"at": 0.0})
        self.assertEqual((got, r["say"]), ([], P.PAUSE))


class ThePriceCheckPlansFromTheDatabase(_Free):

    def setUp(self):
        super().setUp()
        import control_app as CA
        self.CA = CA
        self.d = tempfile.mkdtemp(prefix="price-plan-")
        self.addCleanup(shutil.rmtree, self.d, True)
        P.save(os.path.join(self.d, "d2jsp_price_db.json"), _db([("Gull", 9, 2), ("Arachnid Mesh", 1, 1)]))
        old = os.environ.get("TV_HIST")
        os.environ["TV_HIST"] = self.d
        self.addCleanup(lambda: os.environ.pop("TV_HIST", None) if old is None else os.environ.__setitem__("TV_HIST", old))
        self._canon = CA._d2jsp_canon
        CA._d2jsp_canon = lambda item: P.key_of(item)          # no node in a law: the asked name is its own key
        self.addCleanup(setattr, CA, "_d2jsp_canon", self._canon)
        self._pace = dict(CA._D2JSP_REFRESH_PACE)
        CA._D2JSP_REFRESH_PACE["at"] = 0.0
        self.addCleanup(CA._D2JSP_REFRESH_PACE.update, self._pace)

    def test_a_stale_held_item_is_refreshed_by_this_check(self):
        plan = self.CA._d2jsp_price_check_plan("Gull", now=NOW)
        self.assertEqual(plan["do"], "refresh", plan)
        self.assertEqual(plan["dbFirst"]["verdict"], "known", plan)

    def test_inside_the_minute_it_answers_from_the_db_and_says_the_wait(self):
        self.CA._d2jsp_price_check_plan("Gull", now=NOW)
        plan = self.CA._d2jsp_price_check_plan("Gull", now=NOW + 20)
        self.assertEqual(plan["do"], "stored", plan)
        self.assertEqual(plan["answer"]["reason"], "stored")
        self.assertEqual(plan["answer"].get("wait"), 40, plan["answer"])

    def test_a_fresh_held_item_is_answered_from_the_db(self):
        plan = self.CA._d2jsp_price_check_plan("Arachnid Mesh", now=NOW)
        self.assertEqual(plan["do"], "stored", plan)
        self.assertIn("dbFirst", plan["answer"])
        self.assertIsNone(plan["answer"]["fg"], "a stored answer claimed a live fg")

    def test_an_item_the_db_lacks_is_read_live(self):
        self.assertEqual(self.CA._d2jsp_price_check_plan("Shako", now=NOW)["do"], "live")


class TheQuoteDoorAsksThePlanFirst(unittest.TestCase):

    def test_the_plan_runs_before_the_search_and_stored_never_searches(self):
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            src = fh.read()
        i = src.index('if path == "/api/d2jsp_quote":')
        block = src[i:src.index('if path == "/api/d2jsp_price_db":', i)]
        plan = block.index("_plan = _d2jsp_price_check_plan(_item)")
        search = block.index("_d2jsp.d2jsp_quote(")
        self.assertLess(plan, search, "the price check searches the forum before it reads the DB")
        stored = block[block.index('if _plan["do"] == "stored":'):search]
        self.assertIn("return", stored, "a stored answer still searches the forum")


RED_PROOF = [
    {"why": "#96 - fresh_refresh ignores `only`: a price check refreshes every stale item",
     "file": "d2jsp_price_db.py",
     "find": "        if want is not None and _k not in want:\n            continue\n        name = it.get(\"item\")",
     "replace": "        name = it.get(\"item\")", "matches": 1},
    {"why": "#96 - no pace: a second refresh goes inside the minute",
     "file": "d2jsp_price_db.py",
     "find": "        if left > 0:\n", "replace": "        if False:\n", "matches": 1},
    {"why": "#96 - the plan never refreshes a stale held item (fresh_refresh has no caller again)",
     "file": "control_app.py",
     "find": "        r = _PDB.fresh_refresh(db, chosen.append, now, env=env, only=[key, item], pace=_D2JSP_REFRESH_PACE)\n",
     "replace": "        r = {\"say\": None, \"fetched\": []}\n", "matches": 1},
    {"why": "#96 - the quote door searches before it reads the DB",
     "file": "control_app.py",
     "find": "            if _plan[\"do\"] == \"stored\":\n                self._json(200, _quote_names_its_item(_plan[\"answer\"], _item))\n                return\n",
     "replace": "", "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
