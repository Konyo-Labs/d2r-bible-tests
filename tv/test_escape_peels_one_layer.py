# -*- coding: utf-8 -*-
"""v3891 (#191, REG-3528) - ESCAPE PEELS ONE LAYER, THE SAME SHAPE AS _cbEsc.

His rule: stacked popups close one layer at a time on Esc. MEASURED: the page's Esc listener hid
the keyboard-help modal, closed a latched material/rune card, AND collapsed the nav compass in the
same press, so two (or three) things went away together. `_cbEsc` already peels only the top
builder layer and returns. Now `_tvEsc` does the same for the page: keyboard help, then the help
sheet, then the unique panel, then the visible drop/unique card, then the nav compass — each branch returns after closing that
one layer. The listener stops the event so a later Esc handler cannot peel a second layer in the
same press. RED_PROOF below.
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

PAGE = os.path.join(ROOT, "bible.html")


def _page():
    with io.open(PAGE, encoding="utf-8") as fh:
        return fh.read()


def _tv_esc(src):
    i = src.index("function _tvEsc(){")
    return src[i:src.index("window._tvEsc = _tvEsc;", i)]


class EscapePeelsOneLayer(unittest.TestCase):

    def test_each_layer_returns_so_the_next_stays(self):
        body = _tv_esc(_page())
        order = [
            "getElementById('kbd-help-modal')",
            "return 'kbd-help'",
            "getElementById('help-modal')",
            "return 'help'",
            "getElementById('item-detail-panel')",
            "return 'item-detail-panel'",
            "getElementById('item-detail');",
            "return 'item-detail'",
            "getElementById('nav-widget')",
            "return 'nav'",
        ]
        at = [body.index(x) for x in order]
        self.assertEqual(at, sorted(at), "Esc no longer peels the page's layers from the top down: %s" % body)
        # a return after the first close means the later ones cannot run in the same press
        self.assertLess(body.index("return 'kbd-help'"), body.index("getElementById('help-modal')"),
                        "keyboard help no longer returns, so the next layer closes with it")

    def test_the_listener_stops_after_one_peel(self):
        src = _page()
        i = src.index("window._tvEsc = _tvEsc;")
        tail = src[i:i + 450]
        self.assertIn("if (_tvEsc())", tail)
        self.assertIn("stopImmediatePropagation", tail,
                      "a later Esc handler can still peel a second layer in the same press")


RED_PROOF = [
    {"why": "v3891 (#191, REG-3528) - keyboard help no longer returns, so the next layer closes with it",
     "file": "bible.html",
     "find": "    modal.classList.remove('show');\n    return 'kbd-help';\n",
     "replace": "    modal.classList.remove('show');\n",
     "matches": 1},
    {"why": "v3891 (#191, REG-3528) - the listener no longer stops the event, so a later handler peels another layer",
     "file": "bible.html",
     "find": "  if (_tvEsc()) {\n    if (e.preventDefault) e.preventDefault();\n    if (e.stopImmediatePropagation) e.stopImmediatePropagation();\n",
     "replace": "  if (_tvEsc()) {\n    if (e.preventDefault) e.preventDefault();\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
