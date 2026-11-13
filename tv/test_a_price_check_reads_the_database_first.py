# -*- coding: utf-8 -*-
"""#96 (his 11-06: "for price check it should be joined logic to the database so this is a communicating and whole
system") - EVERY PRICE CHECK READS THE DATABASE FIRST AND SHOWS ITS PRICE BESIDE THE LIVE POSTS.

d2jsp_price_db.db_first is what the DB held BEFORE the check asked the forum: its price, Wilson lower bound and priced-post
count. An empty DB is UNKNOWN, a thin one (a tier under THIN_POSTS weighted posts) is UNKNOWN with its lean beside it -
never a confident 0, never a confident 2-post number. His rule stands: a post without a price is not a post (REG-3791) and
never counts. The quote door carries it as dbFirst on every answer and the page draws it beside the live line (priceSearch
and the trade card's priceText). RED_PROOF below.
"""
import io
import json
import os
import shutil
import subprocess
import sys
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

NODE = shutil.which("node")
NOW = time.mktime(time.strptime("2026-11-13", "%Y-%m-%d"))


def _db(prices, priceless=0):
    db = P.empty()
    posts = {}
    for i, fg in enumerate(prices):
        link = "https://forums.d2jsp.org/topic.php?t=%d&f=268" % (500 + i)
        posts[link] = {"fg": fg, "day": "2026-11-12", "link": link, "w": 1, "perfect": False, "src": "mac", "seenAt": NOW}
    for j in range(priceless):
        link = "https://forums.d2jsp.org/topic.php?t=%d&f=268" % (900 + j)
        posts[link] = {"fg": None, "day": "2026-11-12", "link": link, "w": 1, "perfect": False, "src": "mac", "seenAt": NOW}
    db["items"]["shako"] = {"item": "Shako", "readAt": NOW, "posts": posts}
    return db


class TheDatabaseComesFirst(unittest.TestCase):

    def test_an_empty_db_is_unknown_never_zero(self):
        f = P.db_first(P.empty(), "Shako", NOW)
        self.assertEqual(f["verdict"], "unknown")
        self.assertIsNone(f["fg"], "an empty DB answered a number")
        self.assertIn("UNKNOWN", f["say"])

    def test_an_unreadable_db_is_unknown(self):
        self.assertEqual(P.db_first(None, "Shako", NOW)["verdict"], "unknown")

    def test_a_thin_db_says_unknown_beside_its_lean(self):
        f = P.db_first(_db([20, 22]), "Shako", NOW)
        self.assertEqual(f["verdict"], "thin", f)
        self.assertIsNone(f["fg"], "two posts were said as a confident price")
        self.assertEqual(f["n"], 2)
        self.assertIsNotNone(f["lean"])
        self.assertIn("UNKNOWN", f["say"])

    def test_a_known_db_says_price_wilson_and_count(self):
        f = P.db_first(_db([20, 20, 21, 19, 20]), "Shako", NOW)
        self.assertEqual(f["verdict"], "known", f)
        self.assertEqual(f["fg"], 20)
        self.assertEqual(f["n"], 5)
        self.assertGreater(f["conf"], 0)
        self.assertIn("Wilson", f["say"])

    def test_a_post_without_a_price_never_counts(self):
        f = P.db_first(_db([20, 22], priceless=5), "Shako", NOW)
        self.assertEqual(f["n"], 2, "a post without a price was counted")
        self.assertEqual(f["verdict"], "thin", "priceless posts lifted a thin DB to known")


class TheDoorAndThePageCarryIt(unittest.TestCase):

    def _src(self, rel):
        with io.open(os.path.join(os.path.dirname(HERE), rel), encoding="utf-8") as fh:
            return fh.read()

    def test_the_door_carries_db_first_on_a_live_answer(self):
        src = self._src("tv/control_app.py")
        i = src.index('if path == "/api/d2jsp_quote":')
        block = src[i:src.index('if path == "/api/d2jsp_price_db":', i)]
        self.assertIn('_out["dbFirst"] = _plan["dbFirst"]', block, "a live answer no longer says what the DB held")
        plan = src[src.index("def _d2jsp_price_check_plan("):src.index("def _fixture_root_for_state(")]
        self.assertIn('"dbFirst": first', plan, "a stored answer no longer says what the DB held")

    @unittest.skipUnless(NODE, "node drives the page's own line")
    def test_the_page_draws_it_beside_the_live_line(self):
        page = self._src("bible.html")
        a = page.index("function d2jspDbFirstLine(q) {")
        fn = page[a:page.index("\n}\n", a) + 3]
        prog = fn + (
            "var out = [d2jspDbFirstLine({dbFirst: {verdict: 'known', fg: 20, conf: 0.5, n: 5, say: 'Database: 20 fg'}}),"
            " d2jspDbFirstLine({dbFirst: {verdict: 'thin', fg: null, lean: 20, say: 'Database: UNKNOWN - only 2'}}),"
            " d2jspDbFirstLine({dbFirst: {verdict: 'unknown', fg: 0}}), d2jspDbFirstLine({})];"
            "process.stdout.write(JSON.stringify(out));")
        r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr[-600:])
        got = json.loads(r.stdout)
        self.assertEqual(got[0], "Database: 20 fg")
        self.assertIn("UNKNOWN", got[1])
        self.assertIn("UNKNOWN", got[2], "a zero DB price was drawn as a price")
        self.assertEqual(got[3], "")
        show = page[page.index("    function show(j){"):page.index("    function step(){", page.index("    function show(j){"))]
        self.assertIn("data-d2jsp-db-first", show, "the price search no longer draws the DB beside the live line")
        pt = page[page.index("  function priceText(n){"):page.index("  function priceText(n){") + 600]
        self.assertIn("d2jspDbFirstLine(quoted[n])", pt, "the trade card no longer says the DB beside its live line")


RED_PROOF = [
    {"why": "#96 - a thin DB is said as a confident price",
     "file": "d2jsp_price_db.py",
     "find": "    if tier[\"n\"] < THIN_POSTS:\n", "replace": "    if False:\n", "matches": 1},
    {"why": "#96 - the live answer drops what the DB held",
     "file": "control_app.py",
     "find": "                _out[\"dbFirst\"] = _plan[\"dbFirst\"]   # #96 - what the DB held BEFORE this read, beside the live posts\n",
     "replace": "                pass\n", "matches": 1},
    {"why": "#96 - the page draws a zero DB price as known",
     "file": "bible.html",
     "find": "  if (f.verdict === 'known' && Number(f.fg) > 0) return",
     "replace": "  if (true) return", "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
