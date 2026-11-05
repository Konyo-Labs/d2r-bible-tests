# -*- coding: utf-8 -*-
"""v3864 (GrokBot Batch A 8, #230 6656116697) - EVERY CLIPBOARD COPY HANDLES ITS REFUSAL.

GrokBot counted 17 unhandled Clipboard rejections: navigator.clipboard.writeText is a promise, and a `try { } catch` around it
catches nothing when the browser refuses the copy. Two of the three bare calls then printed COPIED regardless (the machine
name pill on the console, the board's share chip). Now every writeText on the console and the board carries a rejection
handler - .then(ok, refused) or .catch - and the two pills say COPY REFUSED when it was. Source law over every call site.
RED_PROOF below.
"""
import io
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
FILES = (os.path.join(HERE, "control_ui.html"), os.path.join(os.path.dirname(HERE), "bible.html"))
CALL = "navigator.clipboard.writeText("


def _close(s, i):
    """index just past the ')' that closes the '(' at s[i-1] (paren depth, strings ignored roughly)"""
    d, q = 1, None
    while i < len(s) and d:
        c = s[i]
        if q:
            if c == "\\":
                i += 2
                continue
            if c == q:
                q = None
        elif c in "'\"`":
            q = c
        elif c == "(":
            d += 1
        elif c == ")":
            d -= 1
        i += 1
    return i


def _args(s, i):
    """the top-level argument count of the call whose '(' is at s[i-1]"""
    j = _close(s, i)
    body, d, n, q, k = s[i:j - 1], 0, 1, None, 0
    if not body.strip():
        return 0
    while k < len(body):
        c = body[k]
        if q:
            if c == "\\":
                k += 2
                continue
            if c == q:
                q = None
        elif c in "'\"`":
            q = c
        elif c in "([{":
            d += 1
        elif c in ")]}":
            d -= 1
        elif c == "," and d == 0:
            n += 1
        k += 1
    return n


def unanswered():
    out, seen = [], 0
    for f in FILES:
        s = io.open(f, encoding="utf-8").read()
        at = 0
        while True:
            i = s.find(CALL, at)
            if i < 0:
                break
            seen += 1
            j = _close(s, i + len(CALL))
            rest = s[j:j + 12]
            ok = False
            if rest.startswith(".catch("):
                ok = True
            elif rest.startswith(".then("):
                k = j + len(".then(")
                ok = _args(s, k) >= 2 or s[_close(s, k):].startswith(".catch(")
            if not ok:
                out.append("%s:%d" % (os.path.basename(f), s.count("\n", 0, i) + 1))
            at = j
    return out, seen


class NoClipboardCopyGoesUnanswered(unittest.TestCase):

    def test_every_copy_handles_a_refusal(self):
        bad, seen = unanswered()
        self.assertGreaterEqual(seen, 8, "PREMISE: the clipboard calls were not found (%d)" % seen)
        self.assertEqual(bad, [], "a clipboard copy whose refusal nobody handles (an unhandled rejection): %s" % bad)

    def test_the_pills_say_a_refused_copy(self):
        for f in FILES:
            s = io.open(f, encoding="utf-8").read()
            if "_say('COPIED')" in s:
                self.assertIn("_say('COPY REFUSED')", s, "%s claims COPIED for a refused copy" % os.path.basename(f))
        self.assertEqual(sum(io.open(f, encoding="utf-8").read().count("_say('COPY REFUSED'); }); }") for f in FILES), 2)


RED_PROOF = [
    {"why": "v3864 - the console's name pill copies with no refusal handler and claims COPIED again",
     "file": "tv/control_ui.html",
     "find": "    try { navigator.clipboard.writeText(t.split('\\n\\n')[0]).then(function () { _say('COPIED'); }, function () { _say('COPY REFUSED'); }); }\n",
     "replace": "    try { navigator.clipboard.writeText(t.split('\\n\\n')[0]); _say('COPIED'); }\n",
     "matches": 1},
    {"why": "v3864 - the board's share chip copies with no refusal handler again",
     "file": "bible.html",
     "find": ".then(function () { _say('COPIED'); }, function () { _say('COPY REFUSED'); }); }\n      catch (e) { _say('COPY REFUSED'); }",
     "replace": "; _say('COPIED'); }\n      catch (e) { _say('COPY REFUSED'); }",
     "matches": 1},
    {"why": "v3864 - the film-folder path copy goes unanswered again",
     "file": "tv/control_ui.html",
     "find": "navigator.clipboard.writeText(j.path).then(null, function () {",
     "replace": "navigator.clipboard.writeText(j.path); (function () {",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
