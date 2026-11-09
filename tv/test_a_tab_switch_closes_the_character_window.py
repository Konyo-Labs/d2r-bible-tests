# -*- coding: utf-8 -*-
"""v3893 (#191, REG-3555) - A TAB SWITCH CLOSES THE CHARACTER WINDOW TOO.

His unified close: switching tabs is a fresh start. navClean and switchTab already closed the
builder, the unique card, the drop and the boss card, and the console header asked the iframe
for those — but none of them asked `_chxClose`, so #chx-win rode along to the next room.
Now navClean, switchTab and `_headTabGo` all run the same close the window's own button runs.
RED_PROOF below.
"""
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()


def _read(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


class ATabSwitchClosesTheCharacterWindow(unittest.TestCase):

    def test_navclean_switchtab_and_the_header_all_ask_chxclose(self):
        src = _read(os.path.join(ROOT, "bible.html"))
        i = src.index("function navClean(name) {")
        nav = src[i:src.index("\n}\n", i)]
        self.assertIn('if (typeof window._chxClose === "function") window._chxClose();', nav)
        sw = src[src.index("function switchTab(name) {"):src.index("function switchTab(name) {") + 700]
        self.assertIn('if (typeof window._chxClose === "function") window._chxClose();', sw)
        ui = _read(os.path.join(HERE, "control_ui.html"))
        self.assertIn("try { if (typeof w._chxClose === 'function') w._chxClose(); } catch (_e5) {}", ui)


RED_PROOF = [
    {"why": "v3893 (#191, REG-3555) - navClean leaves #chx-win open",
     "file": "bible.html",
     "find": "  if (typeof window._chxClose === \"function\") window._chxClose();   /* v3893 (#191, REG-3555) */\n",
     "replace": "",
     "matches": 1},
    {"why": "v3893 (#191, REG-3555) - switchTab leaves #chx-win open",
     "file": "bible.html",
     "find": "  try { if (typeof window._chxClose === \"function\") window._chxClose(); } catch (_chxC) {}   /* v3893 (#191, REG-3555) */\n",
     "replace": "",
     "matches": 1},
    {"why": "v3893 (#191, REG-3555) - a console header tab leaves #chx-win open in the board iframe",
     "file": "tv/control_ui.html",
     "find": "          try { if (typeof w._chxClose === 'function') w._chxClose(); } catch (_e5) {}\n",
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
