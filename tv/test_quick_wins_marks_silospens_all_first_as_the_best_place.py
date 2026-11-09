# -*- coding: utf-8 -*-
"""v3894 (#85 / gh#254, REG-3564) - THE CARD'S BEST PLACE IS SILOSPEN'S ALL #1.

Bane Ash's All #1 is Coldcrow / Cave Level 1, not Andariel. The first boss row
keeps "1st · best run" and qw-best only when it IS All #1; otherwise it reads
"1st · best boss". A qw-best-place banner names silospen's All #1 above the lists.
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


class QuickWinsMarksSilospensAllFirstAsTheBestPlace(unittest.TestCase):

    def test_the_banner_and_the_boss_label_follow_all_first(self):
        src = _read("bible.html")
        self.assertIn("qw-best-place", src)
        self.assertIn("Best place", src)
        self.assertIn("silospen\\u2019s All", src)
        self.assertIn("isBest === undefined", src)
        self.assertIn("1st · best boss", src)
        self.assertIn("r.p.label === bestLabel", src)
        self.assertIn("(isBest ? '1st · best run' : '1st · best boss')", src)


RED_PROOF = [
    {"why": "v3894 (#85, REG-3564) - the card no longer names silospen All #1 as the best place",
     "file": "bible.html",
     "find": "      ? '<div class=\"qw-best-place\">Best place \\u00b7 silospen\\u2019s All: ' + esc(bestP.label) + (bestP.area ? ' \\u00b7 ' + esc(bestP.area) : '') + '</div>'\n",
     "replace": "      ? ''\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
