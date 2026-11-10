# -*- coding: utf-8 -*-
"""v3892 (#191, REG-3540) - A PRESS OUTSIDE THE VISIBLE BOSS CARD PEELS IT.

His rule: a click outside the top overlay closes it. MEASURED: `#boss-detail-overlay` is
in-flow (inserted under the clicked boss), so `__tvTopOverlay` cannot see it. Escape now
peels it (REG-3539). A pointerdown outside the overlay now runs the same `clearActiveBoss`
its own ✕ already runs. A press on the card itself is left alone.
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


def _fn(src):
    i = src.index("function _tvOutsideCard(e){")
    return src[i:src.index("window._tvOutsideCard = _tvOutsideCard;", i)]


class APressOutsideTheBossCardClosesIt(unittest.TestCase):

    def test_a_press_outside_the_visible_boss_overlay_closes_it(self):
        body = _fn(_page())
        self.assertIn("getElementById('boss-detail-overlay')", body)
        self.assertIn("!bossOv.classList.contains('hidden')", body)
        self.assertIn("!bossOv.contains(t)", body)
        self.assertIn("window.clearActiveBoss({ noScroll: true })", body)
        self.assertIn("return 'boss-detail'", body)


RED_PROOF = [
    {"why": "v3892 (#191, REG-3540) - a press outside the boss detail no longer closes it",
     "file": "bible.html",
     "find": "  var bossOv = document.getElementById('boss-detail-overlay');\n  if (bossOv && !bossOv.classList.contains('hidden') && !bossOv.contains(t) && !(t.closest && t.closest('.boss-chip'))) {\n    if (typeof window.clearActiveBoss === 'function') {\n      window.clearActiveBoss({ noScroll: true });\n      return 'boss-detail';\n    }\n  }\n",
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
