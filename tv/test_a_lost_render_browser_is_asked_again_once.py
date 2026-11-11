# -*- coding: utf-8 -*-
"""REG-3677 (card #200 guard 9e) - A RENDER WHOSE BROWSER WAS LOST IS ASKED AGAIN, ONCE.

MEASURED 2026-11-11 on v3895's first box rehearsal: tv/render_check.py answered UNKNOWN - "the browser connection was lost
mid-render" - and the rehearsal stopped the ship on it. render_check says such a run established NOTHING about the page and
asks for a re-run; preship.check_render now asks that re-run once. A second UNKNOWN stays UNKNOWN (never a pass), a red is
never asked again (a real defect is not retried away), and an UNKNOWN for any other reason (no Chrome) is not retried.

DRIVEN through check_render with preship._run stubbed to hand back render_check's own words. RED_PROOF below.
"""
import os
import subprocess
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import preship as P  # noqa: E402

LOST = "⚪ quick-wins UNKNOWN — the browser connection was lost mid-render (WebSocketConnectionClosedException: x)."
NO_CHROME = "⚪ render_check UNKNOWN - no headless Chrome on this machine"


class ALostRenderBrowserIsAskedAgainOnce(unittest.TestCase):
    def _check(self, answers):
        calls = []

        def fake_run(cmd, root, timeout, **kw):
            rc, out = answers[len(calls)]
            calls.append(cmd)
            return subprocess.CompletedProcess(cmd, rc, out, "")

        with mock.patch.object(P, "_run", fake_run):
            code, say = P.check_render("/nonexistent-root")
        return code, say, len(calls)

    def test_a_lost_browser_then_a_green_render_is_green_and_says_so(self):
        code, say, n = self._check([(2, LOST), (0, "🟢 every target rendered")])
        self.assertEqual((code, n), (0, 2), say)
        self.assertIn("asked again once", say)

    def test_two_lost_browsers_stay_unknown(self):
        code, say, n = self._check([(2, LOST), (2, LOST), (0, "never asked")])
        self.assertEqual((code, n), (2, 2), "a second lost browser was read as something other than UNKNOWN: %s" % say)

    def test_a_red_and_a_missing_chrome_are_never_asked_again(self):
        for rc, out in ((1, "🔴 quick-wins clipped 3"), (2, NO_CHROME)):
            with self.subTest(rc=rc):
                code, say, n = self._check([(rc, out), (0, "never asked")])
                self.assertEqual((code, n), (rc, 1), "it was asked again: %s" % say)


RED_PROOF = [
    {"why": "REG-3677 - a lost browser stops the rehearsal again (it is never asked a second time)",
     "file": "tv/preship.py",
     "find": "    if p.returncode == 2 and any(w in ((p.stdout or \"\") + (p.stderr or \"\")) for w in RENDER_LOST_BROWSER):\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "REG-3677 - every UNKNOWN and every red is asked again, so a real defect can be retried away",
     "file": "tv/preship.py",
     "find": "    if p.returncode == 2 and any(w in ((p.stdout or \"\") + (p.stderr or \"\")) for w in RENDER_LOST_BROWSER):\n",
     "replace": "    if p.returncode != 0:\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
