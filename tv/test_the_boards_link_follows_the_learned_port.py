# -*- coding: utf-8 -*-
"""v3896 (REG-3700) - THE BOARD'S TV·D LINK FOLLOWS THE AGENT PORT IT LEARNED, NEVER A HARDCODED :17771.

MEASURED 11-11 on his Mac: test_button_matrix's site half - a board opened from disk beside a private console whose SIM agent
runs on its own port - read OFF AIR on v3895's code and on v3896's. v2224 taught the console's status to hand the board its
agent's port (window._tvdBridgePort), and one frame grab read it; the probe (`/ping`), the `/state` poll and the live
picture (FRAME0) kept http://127.0.0.1:17771, so a board whose agent runs anywhere else could never go live, and a board
beside a law's private agent asked HIS live agent instead. Now one helper, _tvdSyncPorts(), refreshes URL0 and FRAME0 from
the learned port, and the probe and the poll both call it before they fetch. test_button_matrix drives it for real where
Python Playwright is installed (his Mac); this law holds the joins on every runner, GitHub's included.

Source-reading, per source-reading-guard: the page's script with comments stripped, each anchor a unique call. RED_PROOF below.
"""
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass


def _code():
    import js_strip
    with io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8") as fh:
        return js_strip.strip_js_comments(fh.read())                       # the one stripper the laws share


def _body(code, head):
    i = code.index(head)
    j = code.find("\n  function ", i + len(head))
    return code[i:j if j > 0 else i + 4000]


class TheBoardsLinkFollowsTheLearnedPort(unittest.TestCase):
    def setUp(self):
        self.code = _code()

    def test_the_helper_takes_the_learned_port_for_state_and_picture(self):
        """* THE POINT"""
        self.assertEqual(self.code.count("function _tvdSyncPorts(){"), 1, "the board has no one helper for its link")
        h = _body(self.code, "function _tvdSyncPorts(){")
        self.assertIn("var bp = window._tvdBridgePort;", h)
        self.assertIn("URL0 = 'http://127.0.0.1:' + bp + '/state';", h, "the /state poll keeps :17771")
        self.assertIn("FRAME0 = 'http://127.0.0.1:' + bp + '/frame';", h, "the live picture keeps :17771")

    def test_the_probe_and_the_poll_refresh_it_before_they_fetch(self):
        probe = _body(self.code, "function _tvdProbe(){")
        self.assertLess(probe.index("_tvdSyncPorts();"), probe.index("fetch("), "the probe fetches before it learns the port")
        self.assertIn("fetch(URL0.replace(/\\/state$/, '/ping'),", probe, "the probe asks a fixed port again")
        self.assertNotIn("127.0.0.1:17771/ping", probe, "the probe still names :17771")
        poll = _body(self.code, "function poll(){")
        self.assertLess(poll.index("_tvdSyncPorts();"), poll.index("fetch("), "the poll fetches before it learns the port")


RED_PROOF = [
    {"why": "v3896 (REG-3700) - the board's probe asks :17771 again whatever port it learned",
     "file": "bible.html",
     "find": "    fetch(URL0.replace(/\\/state$/, '/ping'), { signal: ac && ac.signal, cache:'no-store' })\n",
     "replace": "    fetch('http://127.0.0.1:17771/ping', { signal: ac && ac.signal, cache:'no-store' })\n",
     "matches": 1},
    {"why": "v3896 (REG-3700) - the /state poll never takes the learned port (the board polls his agent)",
     "file": "bible.html",
     "find": "  function poll(){\n    _tvdSyncPorts();\n",
     "replace": "  function poll(){\n",
     "matches": 1},
    {"why": "v3896 (REG-3700) - the live picture keeps :17771",
     "file": "bible.html",
     "find": "URL0 = 'http://127.0.0.1:' + bp + '/state'; FRAME0 = 'http://127.0.0.1:' + bp + '/frame';",
     "replace": "URL0 = 'http://127.0.0.1:' + bp + '/state';",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
