# -*- coding: utf-8 -*-
"""v3894 (#234/#146, REG-3571) - EVERY BELT CELL IN THE CHARACTER WINDOW OPENS.

The window draws a 4x4 belt grid (the character screen's belt). A named item
opens its card; an unseen cell only speaks its sentence.
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


class TheCharacterWindowBeltCellsOpen(unittest.TestCase):

    def test_belt_is_a_clickable_grid(self):
        src = _read("bible.html")
        self.assertIn("_chxBagHtml('belt', 4, 4, belt)", src)


RED_PROOF = [
    {"why": "v3894 (#234, REG-3571) - belt cells are no longer drawn",
     "file": "bible.html",
     "find": "      + _chxBagHtml('belt', 4, 4, belt)\n",
     "replace": "      + ''\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
