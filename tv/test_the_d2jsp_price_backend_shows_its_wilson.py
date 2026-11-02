"""The D2JSP Advanced door shows the price database, its Wilson score, and the posts that score was weighed from.

A painted search price stays the reading. The database price is the age-weighted median. A set-aside post stays
on the record and does not move the price. An unknown price is not 0 fg and does not print a Wilson of 0.
"""
from __future__ import annotations

import os
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import d2jsp_price_db as P  # noqa: E402

NOW = time.mktime(time.strptime("2026-10-31", "%Y-%m-%d"))
DAY = 86400.0
CALL = "d2jspBackendHtml(j && j.db, j && j.fg, {sync:true, say:j && j.say})"


def _day(age):
    return time.strftime("%Y-%m-%d", time.localtime(NOW - age * DAY))


def _post(fg, age, i, w=1, perfect=False):
    row = {"fg": fg, "day": _day(age), "w": w, "link": "https://forums.d2jsp.org/topic.php?t=%d" % i}
    if perfect:
        row["perfect"] = True
    return row


def _ingest(db, posts, item="Shako", src="mac", now=None):
    P.ingest(db, {"reason": "read", "item": item, "posts": posts}, src, NOW if now is None else now)


def _page():
    with open(os.path.join(REPO, "bible.html"), encoding="utf-8") as fh:
        return fh.read()


class ThePriceBackendShowsItsWilson(unittest.TestCase):
    def test_three_agreeing_posts_score_lower_than_thirty(self):
        few, many = P.empty(), P.empty()
        _ingest(few, [_post(100, 1, i) for i in range(3)])
        _ingest(many, [_post(100, 1, i) for i in range(30)])
        a, b = P.price(few, "Shako", NOW)["normal"], P.price(many, "Shako", NOW)["normal"]
        self.assertEqual(a["fg"], 100)
        self.assertEqual(b["fg"], 100)
        self.assertAlmostEqual(a["conf"], 0.438, places=3)
        self.assertAlmostEqual(b["conf"], 0.886, places=3)
        self.assertLess(a["conf"], b["conf"])

    def test_a_set_aside_post_stays_on_the_record_and_does_not_move_the_price(self):
        db = P.empty()
        _ingest(db, [_post(100, 1, 1), _post(9000, 1, 2, w=0)])
        priced = P.price(db, "Shako", NOW)
        proof = P.explain(db, "Shako", NOW)
        self.assertEqual(priced["normal"]["fg"], 100)
        aside = [p for p in proof["posts"] if p["band"] == "aside"]
        self.assertEqual(len(aside), 1)
        self.assertEqual(aside[0]["fg"], 9000)
        self.assertEqual(aside[0]["decayed"], 0)

    def test_a_perfect_post_does_not_lift_the_normal_price(self):
        db = P.empty()
        _ingest(db, [_post(100, 1, 1), _post(100, 1, 2), _post(900, 1, 3, perfect=True)])
        priced = P.price(db, "Shako", NOW)
        self.assertEqual(priced["normal"]["fg"], 100)
        self.assertEqual(priced["perfect"]["fg"], 900)

    def test_an_unknown_price_is_not_zero(self):
        db = P.empty()
        row = P.price(db, "Shako", NOW)
        self.assertIsNone(row["normal"]["fg"])
        self.assertNotEqual(row["normal"]["fg"], 0)
        view = P.view({"schema": 0})
        self.assertEqual(view["reason"], "unknown")
        self.assertEqual(view["items"], [])

    def test_the_tab_has_the_advanced_door_and_fills_it_from_the_database(self):
        page = _page()
        form = page[page.index('id="d2jsp-price-form"'):page.index('id="d2jsp-find"')]
        self.assertIn('id="d2jsp-price-advanced"', form)
        self.assertIn('id="d2jsp-price-backend"', form)
        self.assertIn('id="d2jsp-price-db-show"', form)
        self.assertIn("Reads d2jsp posts dated 2026 or later, board 268 only. Nothing is posted.", form)
        search = page[page.index("function priceSearch(){"):page.index("window._d2jspPriceSearch = priceSearch;")]
        self.assertNotIn("/api/d2jsp_post", search)
        self.assertIn(CALL, search)
        self.assertIn("function d2jspLoadDatabase()", page)
        self.assertIn("Wilson lower bound is the database score of the posts marked agrees.", page)

    def test_the_quote_still_folds_and_the_database_route_does_not_fetch_the_forum(self):
        with open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            app = fh.read()
        self.assertEqual(app.count('_out["db"] = _d2jsp_db_fold(_out)'), 1)
        self.assertIn('priced["proof"] = _PDB.explain', app)
        route = app[app.index('if path == "/api/d2jsp_price_db"'):app.index('if path in ("/", "/index.html", "/ui")')]
        self.assertNotIn("d2jsp_quote", route)
        self.assertIn("_PDB.view(_db)", route)
        self.assertIn('reason": "paused"', route)


RED_PROOF = [
    {"why": "the Advanced door is gone, so the database cannot be opened",
     "file": "bible.html",
     "find": 'id="d2jsp-price-advanced"',
     "replace": 'id="d2jsp-price-advanced-gone"',
     "matches": 1},
    {"why": "a search no longer fills the panel from the database",
     "file": "bible.html",
     "find": "d2jspBackendHtml(j && j.db, j && j.fg, {sync:true, say:j && j.say})",
     "replace": "d2jspBackendHtml(null, null, {sync:true})",
     "matches": 1},
    {"why": "the quote fold no longer attaches the posts the price was weighed from",
     "file": "tv/control_app.py",
     "find": 'priced["proof"] = _PDB.explain(db, reading.get("item"), now)\n',
     "replace": "priced['proof'] = None\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
