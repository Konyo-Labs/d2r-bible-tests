# -*- coding: utf-8 -*-
"""#96 (one reader) - A PRICE CHECK THE DATABASE ANSWERED POSTS THE DATABASE'S PRICE.

A fresh item is now answered from the price DB (reason "stored", no forum search). The trade card's post price
(d2jspQuotedForBoard -> sendOf) read only the live reading's fg, so a stored answer would post nothing and he would
type a number the DB already holds. It now takes the DB's own NORMAL price when that is known (never thin, never unknown,
never the perfect tier for a plain post); a live reading keeps its own number, and every other board rule stands.
The trade list's ask() takes "stored" as an answer (it fell through to the site path, a 404 on the console). RED_PROOF.
"""
import io
import json
import os
import shutil
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
NODE = shutil.which("node")


def _page():
    with io.open(os.path.join(os.path.dirname(HERE), "bible.html"), encoding="utf-8") as fh:
        return fh.read()


class AStoredCheckPostsTheDatabasePrice(unittest.TestCase):

    @unittest.skipUnless(NODE, "node drives the page's own function")
    def test_the_post_price_comes_from_the_database_when_it_answered(self):
        page = _page()
        a = page.index("function d2jspQuotedForBoard(q, board) {")
        fn = page[a:page.index("\n}\n", a) + 3]
        prog = fn + (
            "var known = {verdict: 'known', tier: 'normal', fg: 40};"
            "var out = ["
            " d2jspQuotedForBoard({reason: 'stored', board: 268, fg: null, dbFirst: known}, 268),"
            " d2jspQuotedForBoard({reason: 'stored', board: 268, fg: null, dbFirst: {verdict: 'thin', tier: 'normal', fg: null, lean: 40}}, 268),"
            " d2jspQuotedForBoard({reason: 'stored', board: 268, fg: null, dbFirst: {verdict: 'known', tier: 'perfect', fg: 90}}, 268),"
            " d2jspQuotedForBoard({reason: 'stored', board: 268, fg: null, dbFirst: known}, 271),"
            " d2jspQuotedForBoard({reason: 'read', board: 268, fg: 35, dbFirst: known}, 268)];"
            "process.stdout.write(JSON.stringify(out));")
        r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr[-600:])
        got = json.loads(r.stdout)
        self.assertEqual(got[0], 40, "a stored answer posts nothing although the DB holds a known price")
        self.assertIsNone(got[1], "a thin DB set a post price")
        self.assertIsNone(got[2], "the perfect tier priced a plain post")
        self.assertIsNone(got[3], "another board's DB price was posted")
        self.assertEqual(got[4], 35, "a live reading lost its own number")

    def test_the_trade_list_takes_stored_as_an_answer(self):
        page = _page()
        a = page.index("  function ask(name, done, force){")
        self.assertIn("j.reason === 'stored'", page[a:a + 1600], "a stored answer falls through to the site path")
        self.assertIn("if (q.reason === 'stored') return", page, "a stored answer has no line of its own")


RED_PROOF = [
    {"why": "#96 - a stored answer's DB price never becomes the post price",
     "file": "bible.html",
     "find": "  if (!(fg > 0) && q.reason === 'stored' && q.dbFirst && q.dbFirst.verdict === 'known' && q.dbFirst.tier === 'normal') fg = Number(q.dbFirst.fg);\n",
     "replace": "", "matches": 1},
    {"why": "#96 - the trade list drops a stored answer to the site path",
     "file": "bible.html",
     "find": " || j.reason === 'paused' || j.reason === 'stored')) { finish(j); return; }",
     "replace": " || j.reason === 'paused')) { finish(j); return; }", "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
