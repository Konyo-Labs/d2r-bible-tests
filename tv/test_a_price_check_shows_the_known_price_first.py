# -*- coding: utf-8 -*-
"""REG-3249 / REG-3250 (his reports 2026-11-06 09:35-10:10) - A PRICE CHECK SHOWS THE KNOWN PRICE FIRST, AND SAYS WHOSE
SIGN-IN d2jsp TURNED AWAY.

His screenshots: "Price it" on shako read "paused while checks run" (his 10-31 ruling: a live read never competes with a
push), and with the pause gone every read came back need-login under a green D2JSP lamp. MEASURED on his Mac, read-only:
Chrome holds his three d2jsp cookies (member_id, msec, bnc-uuid; expiring 2027-11), the console sends all three, and
d2jsp answers the console's copy by overwriting member_id - while HIS Chrome stays signed in (his own check, ~10:10).
So "sign in to d2jsp first" was false and the lamp was right. His call (10:15): the price check brings up the price
already researched and verified in the console's database, with the posts behind it to open; the live read adds recent
posts and keeps waiting for checks.

  1. A read whose cookie came from his signed-in Chrome and whose page says signed out is need-login WITH copyRefused,
     and the page says d2jsp turned away the console's copy - never "sign in first". The lamp is not touched.
  2. A paused answer carries the item's STORED price and its posts (control_app._d2jsp_db_view: read-only, nothing
     folded or written); the live read still waits (his 10-31 ruling).
  3. The Price it painter draws that known price, with each post's link, ahead of the live line.
Fixture DB in a temp dir and stubbed transports only. RED_PROOF below.
"""
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import d2jsp_chrome as D  # noqa: E402

NODE = shutil.which("node")
COOKIE = "bnc-uuid=00000000-0000-0000-0000-000000000000; member_id=1234567; msec=0123456789abcdef0123456789abcdef"
SIGNED_OUT = ("<html><head><title>d2jsp Forums - Invalid Action - d2jsp</title></head><body>"
              "<a href='login.php'>Log In</a> <a href='register.php'>Register</a>"
              "<div>You do not have permission to view this page.</div></body></html>")


def _src(rel):
    with io.open(os.path.join(os.path.dirname(HERE), rel), encoding="utf-8") as fh:
        return fh.read()


class AReadTurnedAwaySaysWhose(unittest.TestCase):

    @unittest.skipUnless(NODE, "node is required for d2jsp's own quote parser")
    def test_a_refused_copy_is_said_as_one(self):
        code, out = D.d2jsp_quote("Harlequin Crest", "http://127.0.0.1:17772", "127.0.0.1:17772", 17772,
                                  cookie_get=lambda: (COOKIE, "ok"),
                                  transport=lambda m, u, h, b: (200, {}, SIGNED_OUT.encode("utf-8")),
                                  chrome_fetch=False, sec_fetch_site="same-origin")
        self.assertEqual(out.get("reason"), "need-login", "premise: d2jsp's signed-out page reads need-login: %r" % out)
        self.assertIs(out.get("copyRefused"), True, "a refused COPY of his signed-in Chrome reads as 'sign in first'")

    def test_the_page_never_tells_a_signed_in_man_to_sign_in(self):
        page = _src("bible.html")
        i = page.index("  if (q.reason === 'need-login' && q.copyRefused) return ")
        j = page.index("  if (q.reason === 'need-login') return 'Sign in to d2jsp first")
        self.assertLess(i, j, "the 'sign in first' line answers before the refused-copy line")
        self.assertIn("turned away the console", page[i:j])

    def test_the_lamp_is_not_touched(self):
        code = "\n".join(ln.split("#", 1)[0] for ln in _src("tv/d2jsp_chrome.py").split("\n"))
        self.assertNotIn("refused", code[code.index("def d2jsp_login_status"):code.index("def d2jsp_login_status") + 1800],
                         "the lamp judges by a refused read again - his Chrome IS signed in")


class TheKnownPriceComesFirst(unittest.TestCase):

    def test_the_stored_view_reads_and_writes_nothing(self):
        import control_app as CA
        import d2jsp_price_db as P
        d = tempfile.mkdtemp(prefix="pricedb-")
        self.addCleanup(shutil.rmtree, d, True)
        path = os.path.join(d, "d2jsp_price_db.json")
        db = P.empty()
        P.ingest(db, {"item": "shako", "reason": "read", "readAt": "2026-11-06T07:00:00.000Z",
                      "posts": [{"fg": 15, "day": "2026-11-05", "link": "https://forums.d2jsp.org/topic.php?t=1&f=268&p=2"}]},
                 "fixture-pc")
        P.save(path, db)
        before = io.open(path, encoding="utf-8").read()
        old = os.environ.get("TV_HIST")
        os.environ["TV_HIST"] = d
        try:
            got = CA._d2jsp_db_view("shako")
        finally:
            if old is None:
                os.environ.pop("TV_HIST", None)
            else:
                os.environ["TV_HIST"] = old
        self.assertEqual(io.open(path, encoding="utf-8").read(), before, "a price CHECK wrote the database")
        self.assertIn("proof", got)
        self.assertTrue(got.get("normal") or got.get("unknown") is None)

    def test_a_paused_answer_carries_the_stored_price(self):
        src = _src("tv/control_app.py")
        i = src.index('if path == "/api/d2jsp_quote":')
        block = src[i:src.index('if path in ("/", "/index.html", "/ui"):', i)]
        pause = block[block.index("if _PDB.checks_running() is not False:"):block.index("_d2jsp.d2jsp_quote(")]
        self.assertIn("_stored = _d2jsp_db_view(_item)", pause, "a paused answer has no stored price to show")
        self.assertIn('"db": _stored', pause)
        self.assertIn('"reason": "paused"', pause, "his 10-31 ruling: the live read still waits for checks")

    def test_the_painter_draws_the_known_price_before_the_live_line(self):
        page = _src("bible.html")
        s = page[page.index("    function show(j){"):page.index("    function step(){", page.index("    function show(j){"))]
        # REG-3326 (#94, his Shako search 11-06 22:46) - first WHENEVER the live read gave no number (paused, signed out,
        # the forum unread, a read that found none) - REG-3249 drew it only for paused / signed out
        self.assertIn("var _first = (_known && j && !(Number(j.fg) > 0))", s, "the known price waits for a pause again")
        self.assertIn("d2jspBackendHtml(_db, null, {})", s, "the known price is not drawn with its posts")
        self.assertIn("out.innerHTML = _first + '<div>'", s, "the known price is not drawn ahead of the live line")


    def test_an_unread_forum_says_so_and_why(self):
        """REG-3326 (#94) - 'unread' is the forum request failing, never 'a reading that returned no fg number'"""
        if not NODE:
            self.skipTest("no node - the price line is not driven here (UNMEASURED)")
        import subprocess
        page = _src("bible.html")
        def fn(head):
            a = page.index(head); depth = 0; i = page.index("{", a)
            for k in range(i, len(page)):
                if page[k] == "{": depth += 1
                elif page[k] == "}":
                    depth -= 1
                    if depth == 0: return page[a:k + 1]
        prog = ("function d2jspWhen(t){ return t ? 'Nov 6 22:46' : ''; }\n" + fn("function d2jspPriceLine(q) {") + "\n"
                "process.stdout.write(JSON.stringify([d2jspPriceLine({reason:'unread', readAt:'x', why:'the forum request raised TimeoutError twice'}),"
                " d2jspPriceLine({reason:'read', readAt:'x', fg:null, n:0})]));")
        r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        unread, empty = json.loads(r.stdout)
        self.assertIn("could not be read at Nov 6 22:46 (the forum request raised TimeoutError twice)", unread)
        self.assertNotIn("returned no fg number", unread, "an unread forum reads as a reading that found nothing")
        self.assertIn("returned no fg number", empty, "a real read that found no number lost its own words")

    def test_a_transport_that_raises_is_asked_once_more_and_names_its_step(self):
        """REG-3326 (#94) - MEASURED intermittent: one retry; a second raise answers unread with the step and the type only"""
        calls = []
        def flaky(method, url, headers, body=None):
            calls.append(1)
            if len(calls) == 1:
                raise TimeoutError("socket timed out with cookie=SECRET")
            return 200, {}, b"<html>no posts</html>"
        D.d2jsp_quote("shako", "http://127.0.0.1:17772", "127.0.0.1:17772", 17772, cookie_get=lambda: ("member_id=SECRET", "ok"),
                      transport=flaky, node_run=lambda *a, **k: None, chrome_fetch=False, sec_fetch_site="same-origin")
        self.assertEqual(len(calls), 2, "a transport that raised once was not asked again")
        def dead(method, url, headers, body=None):
            raise TimeoutError("socket timed out with cookie=SECRET")
        code, out = D.d2jsp_quote("shako", "http://127.0.0.1:17772", "127.0.0.1:17772", 17772,
                                  cookie_get=lambda: ("member_id=SECRET", "ok"), transport=dead,
                                  chrome_fetch=False, sec_fetch_site="same-origin")
        self.assertEqual(out.get("reason"), "unread")
        self.assertEqual(out.get("why"), "the forum request raised TimeoutError twice")
        self.assertNotIn("SECRET", json.dumps(out), "the answer carries the cookie or the error text")


    def test_a_search_the_forum_held_back_reads_unread_never_no_prices(self):
        """REG-3331 (#94, GrokBot 6700580776) - ten searches back to back: every second one sat ~21 s and answered
        'no prices'. A Chrome search whose page never became search results raises; the quote is unread, with why"""
        import contextlib
        clock = [100.0]
        naps = []

        class Page(object):
            def __init__(self, pages):
                self.pages = list(pages)
            def goto(self, url):
                pass
            def snapshot(self):
                return {"html": self.pages.pop(0) if len(self.pages) > 1 else self.pages[0]}
            def act(self, name, js):
                return "sent"

        def chrome_of(pages):
            @contextlib.contextmanager
            def chrome(cookie, prefix):
                yield Page(pages)
            return chrome

        def nap(t):
            naps.append(round(t, 1))
            clock[0] += t
        held = chrome_of(['<form action="search.php"><input name="stext"></form>', "<html>Board 268 - Topics</html>"])
        D._LAST_SEARCH[0] = None
        with self.assertRaises(OSError) as e:
            D._chrome_search("shako", "c=1", chrome=held, clock=lambda: clock[0], nap=nap)
        self.assertEqual(e.exception.args[0], "search: no results page",
                         "a page that never showed search results came back as if it were one")
        code, out = D.d2jsp_quote("Stone of Jordan", "http://127.0.0.1:17772", "127.0.0.1:17772", 17772,
                                  cookie_get=lambda: ("member_id=SECRET", "ok"),
                                  transport=lambda *a: (403, {}, b"<title>Just a moment...</title>"),
                                  chrome_fetch=lambda item, cookie: (_ for _ in ()).throw(OSError("search: no results page")),
                                  sec_fetch_site="same-origin")
        self.assertEqual(out.get("reason"), "unread", "a held-back search reads as a search that found no prices")
        self.assertIn("held back", out.get("why", ""))
        self.assertNotIn("SECRET", json.dumps(out))

    def test_forum_searches_run_one_at_a_time_fifteen_seconds_apart(self):
        """REG-3331 (#94) - MEASURED: the same items read when asked 15 s apart. The second search waits out the gap"""
        import contextlib
        clock = [500.0]
        naps = []

        class Page(object):
            n = 0
            def goto(self, url):
                pass
            def snapshot(self):
                Page.n += 1
                return {"html": '<form action="search.php"><input name="stext"></form>' if Page.n == 1
                        else "<h1>Search Results</h1> Shako 20fg"}
            def act(self, name, js):
                return "sent"

        @contextlib.contextmanager
        def chrome(cookie, prefix):
            Page.n = 0
            yield Page()

        def nap(t):
            naps.append(t)
            clock[0] += t
        D._LAST_SEARCH[0] = None
        D._chrome_search("shako", "c=1", chrome=chrome, clock=lambda: clock[0], nap=nap)
        first = list(naps)
        clock[0] += 3.0
        D._chrome_search("gull", "c=1", chrome=chrome, clock=lambda: clock[0], nap=nap)
        gap = [t for t in naps[len(first):] if t > 1.0]
        self.assertEqual(len(gap), 1, "the second search did not wait for the forum's gap: %r" % naps)
        self.assertAlmostEqual(gap[0], D._SEARCH_GAP_S - 3.0 - sum(first), delta=0.01)
        self.assertGreaterEqual(D._SEARCH_GAP_S, 15.0, "the measured gap is 15 s")


RED_PROOF = [
    {"why": "REG-3331 - a search the forum held back hands its page on and reads 'no prices' (GrokBot's every 2nd search)",
     "file": "tv/d2jsp_chrome.py",
     "find": "        raise OSError(\"search: no results page\" if sent else \"search: the search form never appeared\")\n",
     "replace": "        if html and not _challenge_page(html):\n            return html\n        raise OSError(\"search: no results page\" if sent else \"search: the search form never appeared\")\n",
     "matches": 1},
    {"why": "REG-3331 - two forum searches go out back to back again",
     "file": "tv/d2jsp_chrome.py",
     "find": "            if wait > 0:\n                nap(wait)\n",
     "replace": "            if wait > 0:\n                pass\n",
     "matches": 1},
    {"why": "REG-3326 - an unread forum reads as 'returned no fg number' again (his Shako search)",
     "file": "bible.html",
     "find": "  if (q.reason === 'unread') return 'Public price unknown. The forum could not be read'",
     "replace": "  if (false) return 'Public price unknown. The forum could not be read'",
     "matches": 1, "needs": "node"},
    {"why": "REG-3326 - a transport that raised once answers unread with no second ask",
     "file": "tv/d2jsp_chrome.py",
     "find": "    for _try in (1, 2):\n",
     "replace": "    for _try in (1,):\n",
     "matches": 1},
    {"why": "REG-3250 - a refused copy of his signed-in Chrome reads 'sign in to d2jsp first' again",
     "file": "tv/d2jsp_chrome.py",
     "find": "        out[\"copyRefused\"] = True\n",
     "replace": "        pass\n",
     "matches": 1},
    {"why": "REG-3249 - a paused answer carries no stored price, so the check shows nothing he has researched",
     "file": "tv/control_app.py",
     "find": "                                  \"high\": None, \"readAt\": \"\", \"board\": 268, \"db\": _stored})\n",
     "replace": "                                  \"high\": None, \"readAt\": \"\", \"board\": 268})\n",
     "matches": 1},
    {"why": "REG-3249 - the painter draws the live line only",
     "file": "bible.html",
     "find": "      out.innerHTML = _first + '<div>' + esc(d2jspSearchLine(j, sim, parsed)) + '</div>'",
     "replace": "      out.innerHTML = '<div>' + esc(d2jspSearchLine(j, sim, parsed)) + '</div>'",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
