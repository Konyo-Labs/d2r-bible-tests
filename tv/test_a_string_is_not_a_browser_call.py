# -*- coding: utf-8 -*-
"""v3901 (REG-3764, #200) - A STRING IS NOT A BROWSER CALL: THE PRE-FLIGHT RUNS A LAW THAT ONLY TALKS ABOUT ONE.

v3900's first GitHub round went red on two laws the Mac's pre-flight never ran: preflight.drives_browser filed them as
browser-driving, so they were "GitHub's". test_d2jsp_desk matched `--remote-debugging` inside
self.assertNotIn("--remote-debugging-port", ...) - a check that the desk does NOT open a debug port, over a stubbed
subprocess - and `Board()` inside the JavaScript it hands to node (d2jspBoard()); test_a_price_read_on_another_board_is_not_the_post_price
matched `Board()` only inside its RED_PROOF tamper text. Both run in under two seconds with node and no browser. Now a
browser CALL counts only as code (every string blanked), a launch FLAG may be a string (a real argv) but not one an assertion
checks or a red-proof carries; and code_text measures ast's UTF-8 byte offsets as characters on the source as written (a "·"
earlier on a line used to cut its blanks into the brackets, and the whole file fell back to raw text).

DRIVEN: preflight.drives_browser / code_text over synthetic law files in a temporary tv/. RED_PROOF below.
"""
import io
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

import preflight as PF  # noqa: E402

ASSERTS_A_FLAG = '''import unittest
class T(unittest.TestCase):
    def test_x(self):
        launched = [["chrome", "https://forums.d2jsp.org/"]]
        self.assertNotIn("--remote-debugging-port", " ".join(launched[-1]))
'''
HANDS_JS_TO_NODE = '''import subprocess
BODY = r"""
var main = d2jspBoard();
"""
def run(node):
    return subprocess.run([node, "-"], input=BODY, capture_output=True, text=True)
'''
TAMPER_TEXT = '''import unittest
RED_PROOF = [{"why": "x", "file": "bible.html", "find": "d2jspBoard()", "replace": "headless=new", "matches": 1}]
'''
NON_ASCII_LINE = '''import unittest
class T(unittest.TestCase):
    def test_x(self):
        a = "Konyo · ALT"; self.assertNotIn("--remote-debugging-port", a)
'''
REAL_LAUNCH = '''import subprocess
def go(chrome):
    return subprocess.Popen([chrome, "--headless=new", "--remote-debugging-port=9230", "about:blank"])
'''
HARNESS_CALL = '''import page_harness as H
def go():
    b = H.Board()
    return board()
'''
RENDER_CALL = '''import render_check
def go():
    return render_check.run(["vault"])
'''


class AStringIsNotABrowserCall(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="pf_browser_")
        self.addCleanup(shutil.rmtree, self.d, True)

    def _law(self, name, src):
        with io.open(os.path.join(self.d, name + ".py"), "w", encoding="utf-8") as fh:
            fh.write(src)
        return name

    def test_text_about_a_browser_is_not_a_browser(self):
        """* THE POINT - v3900's first round: two node-only laws filed as browser laws, never run here"""
        for name, src in (("test_asserts", ASSERTS_A_FLAG), ("test_js", HANDS_JS_TO_NODE), ("test_tamper", TAMPER_TEXT),
                          ("test_nonascii", NON_ASCII_LINE)):
            self.assertFalse(PF.drives_browser(self._law(name, src), self.d), "%s was filed as a browser law" % name)

    def test_baseline_a_real_launch_or_harness_call_is_a_browser(self):
        for name, src in (("test_launch", REAL_LAUNCH), ("test_harness", HARNESS_CALL), ("test_render", RENDER_CALL)):
            self.assertTrue(PF.drives_browser(self._law(name, src), self.d), "%s would start a browser on his Mac" % name)

    def test_a_non_ascii_line_does_not_drop_the_strip(self):
        out = PF.code_text(NON_ASCII_LINE)
        self.assertNotEqual(out, NON_ASCII_LINE, "a '·' earlier on a line threw the whole file back as raw text")
        self.assertNotIn("--remote-debugging-port", out)


RED_PROOF = [
    {"why": "REG-3764 - browser CALLS are matched inside strings again (d2jspBoard() in JS handed to node)",
     "file": "tv/preflight.py",
     "find": "    if BROWSER_FLAGS.search(code_text(src)) or BROWSER_CALL_ONLY.search(code_text(src, strings=False)):\n",
     "replace": "    if BROWSER_FLAGS.search(code_text(src)) or BROWSER_CALL_ONLY.search(code_text(src)):\n",
     "matches": 1},
    {"why": "REG-3764 - a string an assertion checks counts as a launch flag again",
     "file": "tv/preflight.py",
     "find": "            if str(fname).startswith(\"assert\"):\n",
     "replace": "            if False:\n",
     "matches": 1},
    {"why": "REG-3764 - ast's byte offsets are used as characters again (a '·' earlier on a line breaks the strip)",
     "file": "tv/preflight.py",
     "find": "        return len(row.encode(\"utf-8\")[:nbytes].decode(\"utf-8\", \"ignore\"))\n",
     "replace": "        return nbytes\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
