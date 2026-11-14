# -*- coding: utf-8 -*-
"""#151 (GrokBot's grok/ lane, his 13 Nov "yea go for it") - THE BACKFILL FOLLOWS THE FORUM'S OWN NEXT PAGE.

The 12 Nov backfill read 1-2 result pages for 581 of 676 items. 199 of them stopped at o=10 holding page 1's own posts
and page 1's own "Next o=10" (Annihilus o=0: 3 posts, o=10: the same 3, then "last page"), while a live probe at 00:52 IST
13 Nov opened Annihilus's real page 2 from that Next href: 18 new topics, pager to o=240. A fallback that opened the
results WITHOUT &o= (or page 1 standing in for a failed paged GET) was read as the last page.

The laws: a later page is the pager's own Next href; a fallback opens that page; a page that answers an earlier one is
asked again and never ends the item (STUCK_MAX tries); a real last page still ends it; a nickname entry
('Annihilus |q=annihilus') searches its own words and folds under the item's ONE canonical key. Fixtures only, every
fetch handed in, no socket opens. RED_PROOF below.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
os.environ.pop("D2JSP_BACKFILL_LOG", None)
from console_safe import enable as _console_safe_enable  # noqa: E402 - a cp1255 console must survive its own report
_console_safe_enable()
import d2jsp_backfill as B  # noqa: E402
import d2jsp_backfill_run as R  # noqa: E402
import d2jsp_price_db as P  # noqa: E402

FORUM = "https://forums.d2jsp.org/"


def page(words, topics, nxt=None, prev=None, href=None):
    """A results page shaped like the forum's: pager links, then one row per topic."""
    pager = ""
    if prev is not None:
        pager += '<a href="search.php?c=8&amp;r=1&amp;o=%d">Prev</a> ' % prev
    if nxt is not None:
        pager += '<a href="%s">Next</a>' % (href or "search.php?c=8&amp;r=1&amp;o=%d" % nxt)
    rows = "".join('<tr><td><a href="topic.php?t=%d&amp;f=268">WTS %s</a></td></tr>' % (t, words) for t in topics)
    return ("<html><body>Post Search Results for: %s in D2:R RotW Softcore Trading %s<table>%s</table></body></html>"
            % (words, pager, rows))


class FakeChrome(object):
    QUOTE_BOARD = 268

    def __init__(self, answers):
        self.answers = list(answers)      # [(status, headers, html)] in order
        self.calls = []
        self.opened = []

    def _search_keywords(self, item, node_run=None):
        return {"Annihilus": "anni", "Harlequin Crest": "shako"}.get(item, item.lower())

    def live_cookie_header(self):
        return "fixture=1", None

    def _headers(self, cookie):
        return {}

    def _search_url(self, item):
        return FORUM + "search.php?c=7&f=268&t=0"

    def _search_body(self, item):
        return ("stext=" + self._search_keywords(item)).encode()

    def _transport(self, method, url, headers, body):
        self.calls.append((method, url, body))
        st, hd, html = self.answers.pop(0)
        return st, hd, html.encode()

    def _forum_redirect(self, loc):
        import urllib.parse
        return urllib.parse.urljoin(FORUM + "search.php", loc) if loc else None

    def _challenge_page(self, text):
        return False

    def _chrome_search(self, item, cookie):
        raise OSError("search: no results page")

    def _chrome_open_results(self, url, cookie):
        self.opened.append(url)
        return self.chrome_page

    def keep_results_page(self, *a, **k):
        return None


REDIRECT = (302, {"Location": "search.php?c=8&r=1"}, "")


class TheBackfillFollowsTheRealNextPage(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="d2jsp_next_")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.prog = os.path.join(self.d, "progress.json")
        self.db = os.path.join(self.d, "prices.json")
        self.urls = os.path.join(self.d, "urls.json")

    def lane(self, C):
        return R.FetchLane(C, self.d, self.urls, {})

    def test_page_two_is_the_pagers_own_next_href(self):
        odd = "search.php?c=8&amp;r=1&amp;o=10&amp;sk=t"           # not what with_offset would build
        C = FakeChrome([REDIRECT, (200, {}, page("anni", [1, 2, 3], nxt=10, href=odd)),
                        (200, {}, page("anni", [4, 5, 6], nxt=20, prev=0))])
        lane = self.lane(C)
        self.assertIn("topic.php?t=1", lane.fetch("Annihilus", 0))
        got = lane.fetch("Annihilus", 10)
        self.assertIn("topic.php?t=4", got)
        self.assertEqual(C.calls[-1][:2], ("GET", FORUM + "search.php?c=8&r=1&o=10&sk=t"),
                         "page 2 was a built URL, not the pager's own Next href")

    def test_a_hollow_page_two_opens_page_two_in_chrome_never_page_one(self):
        C = FakeChrome([REDIRECT, (200, {}, page("anni", [1, 2, 3], nxt=10)),
                        (200, {}, "<html>Search Results</html>")])
        C.chrome_page = page("anni", [4, 5, 6], nxt=20, prev=0)
        lane = self.lane(C)
        lane.fetch("Annihilus", 0)
        got = lane.fetch("Annihilus", 10)
        self.assertEqual(C.opened, [FORUM + "search.php?c=8&r=1&o=10"], "the fallback dropped &o=: %s" % C.opened)
        self.assertIn("topic.php?t=4", got)

    def test_a_failed_paged_get_is_not_read_never_page_one_in_its_place(self):
        class Boom(FakeChrome):
            def _transport(self, method, url, headers, body):
                if method == "GET" and "o=10" in url:
                    self.calls.append((method, url, body))
                    raise OSError("reset")
                return FakeChrome._transport(self, method, url, headers, body)
        C = Boom([REDIRECT, (200, {}, page("anni", [1, 2, 3], nxt=10))])
        lane = self.lane(C)
        lane.urls = {}
        self.assertIsNone(lane.fetch("Annihilus", 10), "page 1 stood in for a paged GET that failed")

    def test_another_searchs_results_are_not_this_items_page(self):
        C = FakeChrome([REDIRECT, (200, {}, page("anni", [1, 2, 3], nxt=10)),
                        (200, {}, page("ber", [7, 8], nxt=20, prev=0))])
        lane = self.lane(C)
        lane.fetch("Annihilus", 0)
        self.assertIsNone(lane.fetch("Annihilus", 10), "another search's page was read as Annihilus page 2")
        self.assertNotIn("Annihilus", lane.urls, "the stale results URL was kept, so the next pass pages it again")

    def run_pages(self, pages, item="Annihilus", passes=None):
        seen = []

        def fetch(entry, offset):
            seen.append(offset)
            return pages.pop(0)

        def parse(html, entry, read_at):
            return {"reason": "read", "item": entry, "posts": []}
        t = 1000.0
        outs = []
        for _ in range(passes or 10):
            if not pages:
                break
            outs.append(B.run_once(self.prog, self.db, fetch=fetch, parse=parse, items=[item], now=t, min_gap_s=60))
            t += 61
        return seen, outs, B.progress_load(self.prog)["items"][P.key_of(item)]

    def test_page_one_again_at_o10_is_asked_again_not_the_last_page(self):
        p1 = page("anni", [1, 2, 3], nxt=10)
        seen, outs, st = self.run_pages([p1, p1, page("anni", [4, 5], nxt=20, prev=0), page("anni", [6], prev=10)])
        self.assertEqual(seen, [0, 10, 10, 20], "the copy of page 1 ended paging or skipped o=10: %s" % seen)
        self.assertEqual(st["pages"], 3)
        self.assertTrue(st["done"])
        self.assertEqual(st["why"], "last page")

    def test_the_same_topics_twice_is_not_a_new_page(self):
        p2 = page("anni", [4, 5], nxt=20, prev=0)
        same = page("anni", [4, 5], prev=10)            # no Next, but page 2's topics again
        seen, outs, st = self.run_pages([page("anni", [1, 2], nxt=10), p2, same, page("anni", [9], prev=10)])
        self.assertEqual(seen, [0, 10, 20, 20])
        self.assertEqual(st["why"], "last page")

    def test_it_gives_up_after_stuck_max_copies(self):
        p1 = page("anni", [1, 2, 3], nxt=10)
        seen, outs, st = self.run_pages([p1] + [p1] * B.STUCK_MAX)
        self.assertEqual(seen, [0] + [10] * B.STUCK_MAX)
        self.assertTrue(st["done"])
        self.assertIn("did not advance", st["why"])

    def test_a_real_last_page_and_an_empty_page_still_end_it(self):
        _s, _o, st = self.run_pages([page("anni", [1, 2], nxt=10), page("anni", [3], prev=0)])
        self.assertEqual((st["done"], st["why"], st["pages"]), (True, "last page", 2))
        os.remove(self.prog)
        empty = "<html><body>Post Search Results for: anni - No results found.</body></html>"
        _s, _o, st = self.run_pages([page("anni", [1, 2], nxt=10), empty], item="Annihilus")
        self.assertEqual((st["done"], st["why"]), (True, "last page"))


class ANicknameEntryFoldsUnderTheOneKey(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="d2jsp_nick_")
        self.addCleanup(shutil.rmtree, self.d, True)

    def test_the_entry_splits_and_never_names_a_second_item(self):
        self.assertEqual(R.split_entry("Annihilus |q=annihilus"), ("Annihilus", "annihilus"))
        self.assertEqual(R.split_entry("Annihilus"), ("Annihilus", None))
        self.assertEqual(R.entry_for("Annihilus", "annihilus"), "Annihilus |q=annihilus")
        self.assertEqual(R.alt_queries({"query": "anni", "slang": ["anni"], "simple": "annihilus"}), ["annihilus"])
        self.assertEqual(R.alt_queries({"query": "gface", "slang": ["gface", "griffons"], "simple": "griffon eye"}),
                         ["griffon eye", "griffons"])
        self.assertEqual(R.alt_queries({"query": "grief", "slang": [], "simple": "grief"}), [])

    def test_the_search_sends_the_entrys_words(self):
        C = FakeChrome([REDIRECT, (200, {}, page("annihilus", [11, 12], nxt=10))])
        R.FetchLane(C, self.d, os.path.join(self.d, "u.json"), {}).fetch("Annihilus |q=annihilus", 0)
        self.assertEqual(C.calls[0][2], b"stext=annihilus")

    def test_both_searches_fold_into_the_canonical_key(self):
        class NodeC(FakeChrome):
            def _node_bin(self):
                return "node"

            def _node_run(self, node, prog, text):
                import re
                self.read_as = json.loads(prog.rsplit("readFileSync(0,'utf8'),", 1)[1].split(",", 1)[0])
                posts = [{"fg": 500 + int(t), "day": "2026-11-11", "w": 1, "author": "S%s" % t,
                          "link": "https://forums.d2jsp.org/topic.php?t=%s" % t}
                         for t in re.findall(r"topic\.php\?t=(\d+)", text)]
                return type("P", (), {"returncode": 0, "stdout": json.dumps({"reason": "read", "posts": posts})})()

            def _public_fields(self, parsed, item, read_at):
                return dict(parsed, item=item)
        repo = os.path.join(self.d, "repo")
        os.makedirs(os.path.join(repo, "functions", "api"))
        with open(os.path.join(repo, "functions", "api", "d2jsp_quote.js"), "w", encoding="utf-8") as fh:
            fh.write("/* ⟦D2JSP QUOTE BEGIN⟧ */\nfunction d2jspRead(){}\n/* ⟦D2JSP QUOTE END⟧ */\n")
        C = NodeC([])
        holder = {}
        parse = R.make_parse(C, repo, holder)
        dbp = os.path.join(self.d, "prices.json")
        P.save(dbp, {"schema": P.SCHEMA, "items": {"annihilus": {"item": "Annihilus", "readAt": 1, "posts": {}}}})
        fold = R.make_fold(dbp, holder)
        a = parse(page("anni", [1, 2]), "Annihilus", "2026-11-13T00:00:00Z")
        self.assertEqual((C.read_as, a["searched"]), ("Annihilus", "anni"))
        fold(a)
        b = parse(page("annihilus", [2, 3]), "Annihilus |q=annihilus", "2026-11-13T00:00:00Z")
        self.assertEqual((C.read_as, b["item"], b["searched"]), ("Annihilus", "Annihilus", "anni"),
                         "the nickname entry reached the reader or the key")
        fold(b)
        db = P.load(dbp)
        self.assertEqual(sorted(db["items"]), ["anni"], "a second entry was made: %s" % sorted(db["items"]))
        self.assertEqual(len(db["items"]["anni"]["posts"]), 3, "the two searches did not union once each")


RED_PROOF = [
    {"why": "#151 rerun - a later page that repeats an earlier one ends the item as its last page again",
     "file": "tv/d2jsp_backfill.py",
     "find": "        if page_did_not_advance(html, offset, st.get(\"fp\")):\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "#151 rerun - the fallback opens the results without &o= (page 1) again",
     "file": "tv/d2jsp_backfill_run.py",
     "find": "                opened = self._open_via_chrome(\"results\", page_url or results_url, cookie)\n",
     "replace": "                opened = self._open_via_chrome(\"results\", results_url or page_url, cookie)\n",
     "matches": 1},
    {"why": "#151 rerun - page 2 is built from &o= again, never the pager's own Next href",
     "file": "tv/d2jsp_backfill_run.py",
     "find": "        if held and held[0] == int(offset) and held[1]:\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "#151 rerun - a nickname entry's words reach the reader and the key (a second DB entry)",
     "file": "tv/d2jsp_backfill_run.py",
     "find": "        item = split_entry(item)[0]\n",
     "replace": "        pass\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
