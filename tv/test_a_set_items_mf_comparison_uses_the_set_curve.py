# -*- coding: utf-8 -*-
"""v3892 (#43, REG-3545) - THE CALCULATOR'S MF COMPARISON USES THE SET CURVE FOR A SET PIECE.

REG-3506 taught effChance the unique-first quality roll (a set gets rarer with more MF at Hell
bosses). MEASURED: the power-user MF comparison (puv-mf-compare) still called adjustChance on the
raw 1:N — the unique curve — so a set piece's "+200 MF / 1000 MF" cells got better as MF rose.
It now asks setMfChance with the selected item and the compared farm first, and only falls back
to adjustChance when that farm is not a measured set fit.
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


class ASetItemsMfComparisonUsesTheSetCurve(unittest.TestCase):

    def test_the_comparison_asks_setMfChance_before_adjustChance(self):
        src = _src()
        i = src.index("id=\"puv-mf-compare\"")
        end = "(_setCh !== undefined) ? _setCh : adjustChance(rawChance, mfVal)"
        chunk = src[i:src.index(end, i) + len(end)]
        self.assertIn("setMfChance(rawChance, selectedItem, best.bossId, best.diffKey, mfVal)", chunk)
        self.assertIn("(_setCh !== undefined) ? _setCh : adjustChance(rawChance, mfVal)", chunk)
        self.assertLess(chunk.index("setMfChance("), chunk.index("adjustChance(rawChance, mfVal)"))


RED_PROOF = [
    {"why": "v3892 (#43, REG-3545) - the MF comparison scales a set piece by the unique curve again",
     "file": "bible.html",
     "find": "            const _setCh = (typeof setMfChance === 'function') ? setMfChance(rawChance, selectedItem, best.bossId, best.diffKey, mfVal) : undefined;\n"
             "            const ch = (_setCh !== undefined) ? _setCh : adjustChance(rawChance, mfVal);\n",
     "replace": "            const ch = adjustChance(rawChance, mfVal);\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
