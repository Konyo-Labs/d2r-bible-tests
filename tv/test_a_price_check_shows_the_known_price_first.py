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
        self.assertIn("(j.reason === 'paused' || j.reason === 'need-login')", s)
        self.assertIn("d2jspBackendHtml(_db, null, {})", s, "the known price is not drawn with its posts")
        self.assertIn("out.innerHTML = _first + '<div>'", s, "the known price is not drawn ahead of the live line")


RED_PROOF = [
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
