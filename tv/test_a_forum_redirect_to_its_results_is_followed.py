# -*- coding: utf-8 -*-
"""v3881 (REG-3403) - A PRICE SEARCH THE FORUM ANSWERS WITH A REDIRECT TO ITS OWN RESULTS PAGE IS FOLLOWED, ONCE, ON THE
FORUM'S OWN HOST ONLY - SO A WINDOWS PC READS THE PRICE THE MAC READS.

His words, 11-08 00:46: "dean is trying to do d2jsp from his console and its not giving him prices for any searched item
hes doing.. for me it works for deans console it does not." MEASURED the same minutes over SSH: the Fleet beacon read
"read" on the Mac and "unread" on both Windows ALTs. On the Mac the forum answers the search POST with a challenge page
(403), so the console's own Chrome runs the search and reads it. On both ALTs it answers 302 -> search.php?c=..&r=.. - its
RESULTS page - and the quote read every redirect that was not to the login as 'unread', and stopped. Followed once with
the same cookie, the OLD ALT read Shako at 13 fg (5-75, 10 posts): the Mac's number from the same minute.

The cookie goes only where it came from: a Location off https://forums.d2jsp.org is never followed, and a second redirect
is not chased. A redirect to the login is still need-login. Drives d2jsp_quote itself with a stand-in transport and the
real quote parser (node). RED_PROOF below. [[the-unjoined-end]] [[unknown-stays-unknown]]
"""
import json
import os
import shutil
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import d2jsp_chrome as desk  # noqa: E402

NODE = shutil.which("node") or shutil.which("nodejs")
ORIGIN, HOST, PORT = "http://127.0.0.1:17772", "127.0.0.1:17772", 17772
COOKIE = "member_id=SECRETCOOKIE"
PAGE = "\n".join([
    "Oct 12, 2026",
    "Gheeds Fortune gc 106/35/13 - 20fg",
    "Gheeds Fortune gc 108/31/12 - 15fg",
    "Pcomb plain - 10fg x 1",
    "35MF gheeds",
    "Gheed's Fortune 10 fg",
    "Summon Skill Necro + 26 life - 25fg",
])


def _quote(answers, chrome_fetch=None):
    """d2jsp_quote over a transport that answers `answers` in order. -> (out, calls)"""
    calls = []
    todo = list(answers)

    def transport(method, url, headers, data):
        calls.append({"method": method, "url": url, "cookie": headers.get("Cookie"),
                      "ctype": headers.get("Content-Type"), "data": data})
        a = todo.pop(0)
        if isinstance(a, Exception):
            raise a
        return a

    def no_chrome(item, cookie):
        raise AssertionError("a results page that read does not need a second browser")

    code, out = desk.d2jsp_quote("Gheed's Fortune", ORIGIN, HOST, PORT, cookie_get=lambda: (COOKIE, "ok"),
                                 transport=transport, chrome_fetch=chrome_fetch or no_chrome)
    assert code == 200, code
    return out, calls


@unittest.skipUnless(NODE, "the quote parser is node - UNMEASURED here, not a pass")
class AForumRedirectToItsResultsIsFollowed(unittest.TestCase):

    def test_the_windows_redirect_is_followed_and_read(self):
        """* THE POINT - the ALTs' 302 -> search.php?c=7&r=.. is the results page, read like the Mac's"""
        out, calls = _quote([(302, {"Location": "search.php?c=7&r=123456"}, b""), (200, {}, PAGE.encode("utf-8"))])
        self.assertEqual((out["reason"], out["fg"], out["low"], out["high"], out["n"]), ("read", 15, 10, 20, 3), out)
        self.assertEqual([c["method"] for c in calls], ["POST", "GET"])
        self.assertEqual(calls[1]["url"], "https://forums.d2jsp.org/search.php?c=7&r=123456")
        self.assertEqual(calls[1]["cookie"], COOKIE, "the results page was asked without the sign-in")
        self.assertIsNone(calls[1]["ctype"], "a GET carries no form body type")
        self.assertIsNone(calls[1]["data"])
        self.assertNotIn("SECRETCOOKIE", json.dumps(out))

    def test_an_absolute_redirect_on_the_forum_is_followed_too(self):
        out, calls = _quote([(303, {"location": "https://forums.d2jsp.org/search.php?c=7&r=9"}, b""),
                             (200, {}, PAGE.encode("utf-8"))])
        self.assertEqual(out["reason"], "read")
        self.assertEqual(calls[1]["url"], "https://forums.d2jsp.org/search.php?c=7&r=9")

    def test_the_cookie_never_follows_a_redirect_off_the_forum(self):
        for loc in ("https://evil.example/search.php?r=1", "http://forums.d2jsp.org/search.php?r=1",
                    "//evil.example/x", "https://forums.d2jsp.org.evil.example/search.php",
                    "https://u:p@forums.d2jsp.org/search.php"):
            out, calls = _quote([(302, {"Location": loc}, b"")])
            self.assertEqual(out["reason"], "unread", loc)
            self.assertEqual(len(calls), 1, "%s was followed with his cookie" % loc)
            self.assertIn("off the forum", out.get("why") or "")

    def test_a_redirect_to_the_login_is_still_need_login(self):
        """baseline: the login redirect, before and after the follow"""
        out, calls = _quote([(302, {"Location": "https://forums.d2jsp.org/login.php?x=1"}, b"")])
        self.assertEqual((out["reason"], len(calls)), ("need-login", 1))
        out, calls = _quote([(302, {"Location": "search.php?r=1"}, b""), (302, {"Location": "login.php"}, b"")])
        self.assertEqual((out["reason"], len(calls)), ("need-login", 2))

    def test_a_second_redirect_is_not_chased_and_a_raise_is_named(self):
        out, calls = _quote([(302, {"Location": "search.php?r=1"}, b""), (302, {"Location": "search.php?r=2"}, b"")])
        self.assertEqual((out["reason"], len(calls)), ("unread", 2))
        self.assertIn("redirected again", out.get("why") or "")
        out, calls = _quote([(302, {"Location": "search.php?r=1"}, b""), TimeoutError("SECRETCOOKIE in a message")])
        self.assertEqual(out["reason"], "unread")
        self.assertEqual(out.get("why"), "the forum's results page raised TimeoutError")
        self.assertNotIn("SECRETCOOKIE", json.dumps(out))

    def test_a_challenge_on_the_results_page_goes_to_the_consoles_chrome(self):
        """the followed page meets the same door as the Mac's: a challenge is searched in the console's own Chrome"""
        seen = []

        def chrome_fetch(item, cookie):
            seen.append(item)
            return PAGE
        out, calls = _quote([(302, {"Location": "search.php?r=1"}, b""), (403, {}, b"<title>Just a moment...</title>")],
                            chrome_fetch=chrome_fetch)
        self.assertEqual((out["reason"], out["fg"], seen), ("read", 15, ["Gheed's Fortune"]))


RED_PROOF = [
    {"why": "REG-3403 - the forum's redirect to its results page is read as 'unread' again (Dean and both ALTs: no prices)",
     "file": "tv/d2jsp_chrome.py", "find": "        nxt = _forum_redirect(loc)\n", "replace": "        nxt = None\n",
     "matches": 1},
    {"why": "REG-3403 - the sign-in cookie follows a redirect to any host",
     "file": "tv/d2jsp_chrome.py",
     "find": '    if u.scheme != "https" or (u.hostname or "").lower() != "forums.d2jsp.org" or u.username or u.password:\n',
     "replace": "    if not u.scheme:\n", "matches": 1},
    {"why": "REG-3403 - the results page is asked without the sign-in",
     "file": "tv/d2jsp_chrome.py",
     "find": '        get_headers = dict((k, v) for k, v in headers.items() if k != "Content-Type")\n',
     "replace": '        get_headers = dict((k, v) for k, v in headers.items() if k not in ("Content-Type", "Cookie"))\n',
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
