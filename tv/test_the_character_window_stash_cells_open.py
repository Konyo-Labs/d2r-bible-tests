# -*- coding: utf-8 -*-
"""v3894 (#234/#146, REG-3570) - EVERY STASH CELL IN THE CHARACTER WINDOW OPENS.

The window draws a 10x10 stash grid. A named item opens its card; an unseen
cell only speaks its sentence.
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


def _read(rel):
    path = os.path.join(HERE, os.path.basename(rel)) if rel.startswith("tv/") else os.path.join(ROOT, rel)
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


class TheCharacterWindowStashCellsOpen(unittest.TestCase):

    def test_stash_is_a_clickable_grid(self):
        src = _read("bible.html")
        self.assertIn("_chxBagHtml('stash', 10, 10, stsh)", src)
        self.assertIn('class="chx-grid-cell"', src)
        self.assertIn("_chxBagsHtml(G, t)", src)


RED_PROOF = [
    {"why": "v3894 (#234, REG-3570) - stash cells are no longer drawn",
     "file": "bible.html",
     "find": "      + _chxBagHtml('stash', 10, 10, stsh)\n",
     "replace": "      + ''\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
