# -*- coding: utf-8 -*-
"""v3892 (#191, REG-3538) - A CONSOLE TAB SWITCH ALSO CLOSES THE BOSS DETAIL.

His rule: a top-tab switch is a fresh start. MEASURED: navClean already calls
`clearActiveBoss({ noScroll: true })`, but `_headTabGo` (REG-3534) only asked the board iframe
for closeCharBuilder / closeItemDetail / closeDrop. A boss card left open in `#tvd-eng` rode
along to Sessions or Vault. `_headTabGo` now asks `clearActiveBoss` too, with the same noScroll
navClean uses so the board is not yanked to the boss nav as the console leaves.
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

PAGE = os.path.join(ROOT, "tv", "control_ui.html")


def _page():
    with io.open(PAGE, encoding="utf-8") as fh:
        return fh.read()


def _head(src):
    i = src.index("function _headTabGo(e){")
    return src[i:src.index("\n  if (_ht) {", i)]


class AConsoleTabSwitchClosesTheBossCard(unittest.TestCase):

    def test_a_real_tab_switch_asks_the_board_to_clear_the_boss(self):
        body = _head(_page())
        self.assertIn("w.clearActiveBoss({ noScroll: true })", body)
        self.assertIn("w.closeCharBuilder()", body)


RED_PROOF = [
    {"why": "v3892 (#191, REG-3538) - a console tab switch leaves the boss detail open in the board iframe",
     "file": "tv/control_ui.html",
     "find": "          try { if (typeof w.clearActiveBoss === 'function') w.clearActiveBoss({ noScroll: true }); } catch (_e4) {}\n",
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
