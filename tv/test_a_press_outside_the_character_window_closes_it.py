# -*- coding: utf-8 -*-
"""v3893 (#191, REG-3556) - A PRESS OUTSIDE THE CHARACTER WINDOW CLOSES IT.

#chx-win is a full-screen host (`position:fixed; inset:0`); the card itself is `.chx-win-box`.
A press on the backdrop — inside the host, outside the box — must peel it, the same way Esc
already asks `_chxClose`. A press inside the box leaves it open.
RED_PROOF below.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
NODE = shutil.which("node")


def _src():
    with io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8") as fh:
        return fh.read()


class APressOutsideTheCharacterWindowClosesIt(unittest.TestCase):

    def test_the_outside_handler_asks_chxclose_only_off_the_box(self):
        src = _src()
        i = src.index("function _tvOutsideCard(e){")
        body = src[i:src.index("window._tvOutsideCard = _tvOutsideCard;", i)]
        self.assertIn("getElementById('chx-win')", body)
        self.assertIn("!t.closest('.chx-win-box')", body)
        self.assertIn("window._chxClose()", body)
        self.assertIn("return 'chx-win'", body)

    def test_a_backdrop_press_closes_and_a_press_in_the_box_does_not(self):
        if not NODE:
            self.fail("node is not on this machine - this law does not skip")
        src = _src()
        i = src.index("function _tvOutsideCard(e){")
        fn = src[i:src.index("window._tvOutsideCard = _tvOutsideCard;", i)]
        js = (
            "var closed = 0;\n"
            "var box = { id: 'box' };\n"
            "var host = { hidden: false, contains: function(){ return true; } };\n"
            "var document = { getElementById: function(id){\n"
            "  if (id === 'chx-win') return host;\n"
            "  return { classList: { contains: function(){ return true; } }, hidden: true,\n"
            "           contains: function(){ return false; } };\n"
            "} };\n"
            "var window = { _chxClose: function(){ closed++; return true; } };\n"
            + fn + "\n"
            "var out = _tvOutsideCard({ button: 0, target: { closest: function(s){ return s === '.chx-win-box' ? null : null; } } });\n"
            "var inn = _tvOutsideCard({ button: 0, target: { closest: function(s){ return s === '.chx-win-box' ? box : null; } } });\n"
            "process.stdout.write(JSON.stringify({ out: out, inn: inn, closed: closed }));\n"
        )
        r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr[-400:])
        got = json.loads(r.stdout)
        self.assertEqual(got["out"], "chx-win")
        self.assertEqual(got["closed"], 1)
        self.assertEqual(got["inn"], "")


RED_PROOF = [
    {"why": "v3893 (#191, REG-3556) - a press on the #chx-win backdrop leaves the window open",
     "file": "bible.html",
     "find": "  if (chx && !chx.hidden && !t.closest('.chx-win-box')) {\n",
     "replace": "  if (false && chx && !chx.hidden && !t.closest('.chx-win-box')) {\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
