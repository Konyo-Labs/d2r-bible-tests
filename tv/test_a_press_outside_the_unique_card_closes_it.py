# -*- coding: utf-8 -*-
"""v3892 (#191, REG-3535) - A PRESS OUTSIDE THE VISIBLE UNIQUE CARD PEELS IT.

His rule: every popup uses the same close; Esc peels one layer; a click outside the top overlay
closes it too. MEASURED: `__tvTopOverlay` only sees position:fixed / absolute boxes, and
`#item-detail-panel` is in-flow, so the overlay contract could never click its ✕. Escape already
peels the visible unique card (REG-3530). A pointerdown outside `#item-detail-panel` (when it is
not hidden) or outside `#item-detail` (when it has `.show`) now runs the same close those cards'
own ✕ and Esc already run. A press on the card itself is left alone so its buttons still work.
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


class APressOutsideTheUniqueCardClosesIt(unittest.TestCase):

    def test_a_press_outside_the_visible_panel_closes_it(self):
        body = _fn(_page())
        self.assertIn("getElementById('item-detail-panel')", body)
        self.assertIn("!idp.classList.contains('hidden')", body)
        self.assertIn("!idp.contains(t)", body)
        self.assertIn("window.closeItemDetail()", body)

    def test_a_press_outside_the_visible_drop_card_closes_it(self):
        body = _fn(_page())
        self.assertIn("getElementById('item-detail');", body)
        self.assertIn("drop.classList.contains('show')", body)
        self.assertIn("!drop.contains(t)", body)
        self.assertIn("window.closeDrop()", body)

    def test_the_listener_is_a_capturing_pointerdown(self):
        src = _page()
        self.assertIn("document.addEventListener('pointerdown', function(e){ _tvOutsideCard(e); }, true);", src)


RED_PROOF = [
    {"why": "v3892 (#191, REG-3535) - a press outside the bosses-tab unique panel no longer closes it",
     "file": "bible.html",
     "find": "  if (idp && !idp.classList.contains('hidden') && !idp.contains(t)) {\n    if (typeof window.closeItemDetail === 'function') {\n      window.closeItemDetail();\n      return 'item-detail-panel';\n    }\n  }\n",
     "replace": "",
     "matches": 1},
    {"why": "v3892 (#191, REG-3535) - a press outside #item-detail.show no longer closes it",
     "file": "bible.html",
     "find": "  if (drop && drop.classList.contains('show') && !drop.contains(t)) {\n    if (typeof window.closeDrop === 'function') {\n      window.closeDrop();\n      if (typeof clearActiveItem === 'function' && activeItem) clearActiveItem();\n      return 'item-detail';\n    }\n  }\n",
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
