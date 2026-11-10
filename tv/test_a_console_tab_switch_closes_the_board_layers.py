# -*- coding: utf-8 -*-
"""v3892 (#191, REG-3534) - A CONSOLE HEADER TAB SWITCH CLOSES THE BOARD'S OPEN LAYERS.

His rule: switching top tabs closes everything and gives a fresh start. MEASURED: bible.html's
`navClean` and `switchTab` already ask `closeCharBuilder` (REG-3524), but the console's own header
tabs run `_headTabGo` in control_ui.html and never talked to the board iframe. A character builder
or a unique card left open in `#tvd-eng` (or a shadow's `#shadow-eng`) rode along to Sessions,
Vault, or TV·D. `_headTabGo` now asks each board iframe to run the same three closes the board's
own tab switch already runs, and only when the click leaves the tab that is showing (a click on
the tab already showing still leaves the theatre and the board alone). RED_PROOF below.
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


class AConsoleTabSwitchClosesTheBoardLayers(unittest.TestCase):

    def test_a_real_tab_switch_asks_each_board_iframe_to_close_its_layers(self):
        body = _head(_page())
        self.assertIn("b.dataset.tab !== _shellTab", body)
        self.assertIn("['tvd-eng', 'shadow-eng']", body)
        self.assertIn("el.contentWindow", body)
        self.assertIn("w.closeCharBuilder()", body)
        self.assertIn("w.closeItemDetail()", body)
        self.assertIn("w.closeDrop()", body)

    def test_a_click_on_the_tab_already_showing_still_leaves_the_theatre_alone(self):
        body = _head(_page())
        self.assertIn("var _stay = (b.dataset.tab === _shellTab) || (b.dataset.tab === 'tvd')", body)
        self.assertIn("window.TH && window.TH.open && !_stay", body)
        self.assertIn("window.thClose()", body)


RED_PROOF = [
    {"why": "v3892 (#191, REG-3534) - a console tab switch leaves the character builder open in the board iframe",
     "file": "tv/control_ui.html",
     "find": "          try { if (typeof w.closeCharBuilder === 'function') w.closeCharBuilder(); } catch (_e1) {}\n",
     "replace": "",
     "matches": 1},
    {"why": "v3892 (#191, REG-3534) - a console tab switch leaves the unique card open in the board iframe",
     "file": "tv/control_ui.html",
     "find": "          try { if (typeof w.closeItemDetail === 'function') w.closeItemDetail(); } catch (_e2) {}\n",
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
