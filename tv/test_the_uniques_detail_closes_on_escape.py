# -*- coding: utf-8 -*-
"""v3891 (#191, REG-3530) - THE UNIQUES DETAIL CLOSES ON ESCAPE (AND ITS OWN CLOSE).

v3889: the Uniques detail only went away on a tab switch. Two cards paint it:
`#item-detail-panel` (`openItemDetail` / `renderItemDetailCard`) and `#item-detail`
(`navigateToItem` / `renderDetail` / a set piece). MEASURED: Escape called `clearActiveItem`
(the top bar) and never `closeItemDetail`; it closed `#item-detail` only when a material/rune
latch was set, and `renderDetail` clears that latch, so a unique card could not close on Esc.
`_tvEsc` now peels the visible panel (`#item-detail-panel` not hidden) and the visible drop
(`#item-detail.show`), then returns, so one Esc closes that one card. RED_PROOF below.
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


class TheUniquesDetailClosesOnEscape(unittest.TestCase):

    def test_esc_peels_the_visible_unique_panel(self):
        body = _tv_esc(_page())
        self.assertIn("getElementById('item-detail-panel')", body)
        self.assertIn("!idp.classList.contains('hidden')", body)
        self.assertIn("window.closeItemDetail()", body)
        self.assertIn("return 'item-detail-panel'", body)

    def test_esc_peels_the_visible_unique_card_not_a_leftover_latch(self):
        body = _tv_esc(_page())
        self.assertIn("getElementById('item-detail');", body)
        self.assertIn("drop.classList.contains('show')", body)
        self.assertIn("window.closeDrop()", body)
        self.assertIn("return 'item-detail'", body)
        self.assertNotIn("window.__activeMaterial || window.__activeRune", body,
                         "Escape closed #item-detail by a leftover latch again")


RED_PROOF = [
    {"why": "v3891 (#191, REG-3530) - Escape no longer closes the bosses-tab unique panel",
     "file": "bible.html",
     "find": "  var idp = document.getElementById('item-detail-panel');\n  if (idp && !idp.classList.contains('hidden') && typeof window.closeItemDetail === 'function') {\n    window.closeItemDetail();\n    return 'item-detail-panel';\n  }\n",
     "replace": "",
     "matches": 1},
    {"why": "v3891 (#191, REG-3530) - Escape closes #item-detail only when a leftover latch is set",
     "file": "bible.html",
     "find": "  var drop = document.getElementById('item-detail');\n  if (drop && drop.classList.contains('show') && typeof window.closeDrop === 'function') {\n    window.closeDrop();\n    if (typeof clearActiveItem === 'function' && activeItem) clearActiveItem();\n    return 'item-detail';\n  }\n",
     "replace": "  if ((window.__activeMaterial || window.__activeRune) && typeof window.closeDrop === 'function') {\n    window.closeDrop();\n    return 'drop';\n  }\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
