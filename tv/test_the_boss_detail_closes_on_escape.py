# -*- coding: utf-8 -*-
"""v3892 (#191, REG-3539) - THE BOSS DETAIL CLOSES ON ESCAPE.

His rule: Esc peels one layer. MEASURED: `_tvEsc` peeled keyboard help, the help sheet, the
unique cards and the nav compass, but never `#boss-detail-overlay`. That overlay is in-flow
(inserted under the clicked boss card), so `__tvTopOverlay` cannot see it either. The card
already has its own ✕ (`clearActiveBoss`). `_tvEsc` now peels the overlay when it is not
hidden, with `{ noScroll: true }`, and returns so the nav compass stays.
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

PAGE = os.path.join(ROOT, "bible.html")


def _page():
    with io.open(PAGE, encoding="utf-8") as fh:
        return fh.read()


def _tv_esc(src):
    i = src.index("function _tvEsc(){")
    return src[i:src.index("window._tvEsc = _tvEsc;", i)]


class TheBossDetailClosesOnEscape(unittest.TestCase):

    def test_esc_peels_the_visible_boss_overlay(self):
        body = _tv_esc(_page())
        self.assertIn("getElementById('boss-detail-overlay')", body)
        self.assertIn("!bossOv.classList.contains('hidden')", body)
        self.assertIn("window.clearActiveBoss({ noScroll: true })", body)
        self.assertIn("return 'boss-detail'", body)

    def test_the_boss_peel_sits_between_the_unique_card_and_the_nav(self):
        body = _tv_esc(_page())
        self.assertLess(body.index("return 'item-detail'"), body.index("getElementById('boss-detail-overlay')"))
        self.assertLess(body.index("return 'boss-detail'"), body.index("getElementById('nav-widget')"))


RED_PROOF = [
    {"why": "v3892 (#191, REG-3539) - Escape no longer closes the boss detail",
     "file": "bible.html",
     "find": "  var bossOv = document.getElementById('boss-detail-overlay');\n  if (bossOv && !bossOv.classList.contains('hidden') && typeof window.clearActiveBoss === 'function') {\n    window.clearActiveBoss({ noScroll: true });\n    return 'boss-detail';\n  }\n",
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
