# -*- coding: utf-8 -*-
"""v3881 (REG-3389, GrokBot's v3878 pass #56) - THE D2JSP PRICE READ SAYS WHICH BOARD IT READS, AND A LADDER CONSOLE IS TOLD.

GrokBot, on Dean's shadow D2JSP tab: "Board 271, D2:R RotW Softcore Ladder Trading." next to "Reads d2jsp posts dated 2026 or
later, board 268 only." - a contradiction on one screen. Both lines were TRUE: a ladder console posts on board 271
(d2jspBoard), while the price search reads board 268 whatever the profile (tv/d2jsp_chrome.py QUOTE_BOARD). So a ladder
console's quotes are NON-ladder posts, and nothing said so. Now the idle read line, on a ladder console, names both boards and
says ladder posts are not read yet; on main it reads exactly as before. A search result is never overwritten by it.
The law drives the page's own functions (cut from bible.html) through node. RED_PROOF below. [[unknown-stays-unknown]]
"""
import io
import json
import os
import re
import shutil
import subprocess
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

NODE = shutil.which("node") or shutil.which("nodejs")
BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")


def _src():
    return io.open(BIBLE, encoding="utf-8").read()


def _cut(src, start, end):
    if src.count(start) != 1:
        raise AssertionError("anchor moved (%d): %r" % (src.count(start), start[:60]))
    i = src.index(start)
    return src[i:src.index(end, i) + len(end)]


def _say(profile):
    s = _src()
    js = ("var window = {D2R_PROFILE: %s};\n" % json.dumps(profile)
          + _cut(s, "var D2JSP_BOARD = 268;", "var D2JSP_LADDER_BOARD = 271;") + "\n"
          + _cut(s, "function d2jspBoard(){", "\n}") + "\n"
          + _cut(s, "var D2JSP_READ_IDLE = ", ";\n")
          + _cut(s, "function d2jspReadSay(){", "\n}") + "\n"
          + "process.stdout.write(JSON.stringify(d2jspReadSay()));")
    r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=60, encoding="utf-8")
    if r.returncode != 0:
        raise AssertionError("node could not drive the read line: " + r.stderr[-500:])
    return json.loads(r.stdout)


@unittest.skipUnless(NODE, "node drives the page's own functions - UNMEASURED here, not a pass")
class TheReadLineNamesItsBoard(unittest.TestCase):

    def test_a_ladder_console_is_told_its_prices_are_the_main_boards(self):
        """* THE POINT: Dean's ladder shadow no longer says 'board 268 only' under a 271 header with nothing between"""
        t = _say("ladder")
        self.assertIn("board 268", t)
        self.assertIn("board 271", t)
        self.assertIn("not read yet", t)
        self.assertIn("non-ladder", t)

    def test_baseline_a_main_console_reads_exactly_as_before(self):
        t = _say("main")
        self.assertEqual(t, "Reads d2jsp posts dated 2026 or later, board 268 only. Nothing is posted.")
        self.assertIn('id="d2jsp-price-out" aria-live="polite">' + t + "</div>", _src(), "the static line and the idle say drift")
        self.assertEqual(_say(""), t)

    def test_the_tab_refreshes_the_idle_line_and_never_a_result(self):
        s = _src()
        body = _cut(s, "  window._d2jspShow = function(){", "\n  };")
        code = "\n".join(l.split("/*", 1)[0] for l in body.split("\n"))
        self.assertIn("readLine.textContent = d2jspReadSay();", code)
        self.assertIn("readLine.textContent === D2JSP_READ_IDLE || /^Prices are read from board /.test(readLine.textContent)",
                      code, "the refresh can overwrite a search result")

    def test_the_reader_still_reads_268(self):
        """the line describes the reader: if the search ever follows the profile, this law must move with it"""
        src = io.open(os.path.join(HERE, "d2jsp_chrome.py"), encoding="utf-8").read()
        self.assertEqual(re.findall(r"^QUOTE_BOARD = (\d+)$", src, re.M), ["268"])


RED_PROOF = [
    {"why": "REG-3389 - a ladder console reads 'board 268 only' under its board 271 header again",
     "file": "bible.html", "find": "  if (d2jspBoard() !== D2JSP_LADDER_BOARD) return D2JSP_READ_IDLE;\n",
     "replace": "  return D2JSP_READ_IDLE;\n", "matches": 1},
    {"why": "REG-3389 - the tab never refreshes the read line for its board",
     "file": "bible.html", "find": "      readLine.textContent = d2jspReadSay();\n", "replace": "      void 0;\n", "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
