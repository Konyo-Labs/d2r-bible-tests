# -*- coding: utf-8 -*-
"""v3892 (#191/#146, REG-3548) - ESCAPE CLOSES THE IN-GAME CHARACTER WINDOW.

His rule: Esc peels only the top layer. MEASURED: `_tvEsc` peeled keyboard help, the help
sheet, the unique cards, the boss detail and the nav compass, but never `#chx-win` (the window
a click on an in-game character opens). That dialog is now a layer: Esc runs `_chxClose` when
the host is not hidden, after the unique and boss cards so a card opened from a worn item peels
first, and before the nav compass.
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

BIBLE = os.path.join(ROOT, "bible.html")


def _src():
    with io.open(BIBLE, encoding="utf-8") as fh:
        return fh.read()


def _esc(src):
    i = src.index("function _tvEsc(){")
    return src[i:src.index("\nwindow._tvEsc = _tvEsc;", i)]


class TheCharacterWindowClosesOnEscape(unittest.TestCase):

    def test_escape_peels_the_open_character_window(self):
        body = _esc(_src())
        self.assertIn("getElementById('chx-win')", body)
        self.assertIn("window._chxClose()", body)
        self.assertIn("return 'chx-win'", body)
        self.assertLess(body.index("return 'boss-detail'"), body.index("getElementById('chx-win')"))
        self.assertLess(body.index("return 'chx-win'"), body.index("getElementById('nav-widget')"))


RED_PROOF = [
    {"why": "v3892 (#191/#146, REG-3548) - Escape no longer peels the character window",
     "file": "bible.html",
     "find": "  var chx = document.getElementById('chx-win');\n"
             "  if (chx && !chx.hidden && typeof window._chxClose === 'function') {\n"
             "    window._chxClose();\n"
             "    return 'chx-win';\n"
             "  }\n",
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
