# -*- coding: utf-8 -*-
"""REG-2094 - ESCAPE CLOSES THE CARD THE LATCH NAMES, NEVER AN ITEM CARD OPENED AFTER IT.

The #231 code seat on May's 0133be32 and 113be899, re-measured at the v3630 tip: a material or rune card sets
window.__activeMaterial / __activeRune so Escape can close it (closeDrop empties #item-detail). navigateToItem - a grail
chip, a search pick, openDrop's grail branch - painted an ITEM card over it through renderDetail and left the latch set,
so the next Escape wiped the item card he had just opened. MEASURED on the real page as the owner: HEAD left the latch
'Key of Terror' under a Harlequin Crest card and Escape emptied it; this tree clears the latch and the card survives.
The reset lives in renderDetail, the one place an item card is painted, so every caller is covered. The browser half -
Escape driven for real, with a baseline that it still closes a material card - is tests/reg2094_escape_keeps_the_item_card.
"""
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

PAGE = os.path.join(os.path.dirname(HERE), "bible.html")
START = "function renderDetail() {\n"
NO_ITEM = '  if (!item) { panel.classList.remove("show"); return; }\n'
RESET = "  window.__activeMaterial = null; window.__activeRune = null;\n  const adjusted = item.sources.map("
ESCAPE = "  if (drop && drop.classList.contains('show') && typeof window.closeDrop === 'function') {"


def _src():
    with io.open(PAGE, encoding="utf-8") as f:
        return f.read()


class EscapeClosesOnlyTheCardItNames(unittest.TestCase):

    def test_an_item_card_clears_the_latch_it_paints_over(self):
        s = _src()
        self.assertEqual(s.count(START), 1, "renderDetail's anchor moved - re-point this law")
        i = s.index(START)
        body = s[i:s.index("\nfunction ", i + 1)]
        self.assertEqual(body.count(RESET), 1, "an item card painted by renderDetail leaves the material/rune latch set")
        self.assertEqual(body.count(NO_ITEM), 1, "premise: renderDetail refuses a name ITEMS does not hold")
        self.assertLess(body.index(NO_ITEM), body.index(RESET),
                        "the latch is cleared before renderDetail knows it will paint an item card")

    def test_escape_closes_the_visible_card(self):
        """v3891 (#191, REG-3530) - Uniques must close on Esc. The layer is the visible card
        (`#item-detail.show`), not a leftover latch: a hidden card with a stale name is not closed,
        and a visible unique card (whose latch renderDetail already cleared) is."""
        self.assertEqual(_src().count(ESCAPE), 1, "Escape no longer closes the visible #item-detail card")
        self.assertNotIn(
            "if ((window.__activeMaterial || window.__activeRune) && typeof window.closeDrop === 'function') {",
            _src(),
            "Escape closed by a leftover latch again, so a unique card painted over a material would be wiped for the wrong reason - or a unique card with no latch would not close")


RED_PROOF = [
    {"why": "REG-2094 - an item card painted over a material card leaves its latch, and Escape wipes the item card",
     "file": "bible.html",
     "find": "  window.__activeMaterial = null; window.__activeRune = null;\n  const adjusted = item.sources.map(",
     "replace": "  const adjusted = item.sources.map(",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
