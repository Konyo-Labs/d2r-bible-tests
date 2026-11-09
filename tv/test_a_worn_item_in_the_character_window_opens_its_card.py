# -*- coding: utf-8 -*-
"""v3892 (#28/#146, REG-3546) - CLICKING A WORN ITEM IN THE CHARACTER WINDOW OPENS ITS CARD.

The character window (#146) draws the Vault doll and speaks a sentence for the picked cell.
MEASURED: `_chxPick` only refreshed that sentence. A worn named item now also opens its item
card (`openItemDetail`), the same door the rest of the board uses. An unseen or UNKNOWN cell
still only speaks its sentence and does not invent a card.
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


def _pick(src):
    i = src.index("  window._chxPick = function(cell){")
    return src[i:src.index("\n  window._chxClose = function(){", i)]


class AWornItemInTheCharacterWindowOpensItsCard(unittest.TestCase):

    def test_a_named_worn_item_opens_its_card(self):
        body = _pick(_src())
        self.assertIn("window.openItemDetail(row.item)", body)
        self.assertIn("row && row.item && typeof window.openItemDetail === 'function'", body)
        self.assertIn("_chxCell.slice('equipped:'.length)", body)


RED_PROOF = [
    {"why": "v3892 (#28/#146, REG-3546) - picking a worn item only refreshes the sentence again",
     "file": "bible.html",
     "find": "    if (row && row.item && typeof window.openItemDetail === 'function') {\n"
             "      try { window.openItemDetail(row.item); } catch (e) {}\n"
             "    }\n",
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
