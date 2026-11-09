# -*- coding: utf-8 -*-
"""v3894 (#153, REG-3567) - A SPEED ROW NAMES ITS CURRENT TIER AND THE NEXT STEP.

_cbBpHtml prepends "tier k/T · " from _cbBpTiers onto eng.bp.say, so the stats
column shows the current tier and still says how much more reaches the next step.
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


class TheStatsRowNamesTheBreakpointTier(unittest.TestCase):

    def test_the_row_asks_the_tiers_and_prints_them(self):
        src = _read("bible.html")
        self.assertIn("function _cbBpHtml(eng, g, kind, row, b)", src)
        self.assertIn("say = 'tier ' + k + '/' + T + ' \\u00b7 ' + say", src)
        self.assertIn("_cbBpHtml(eng, r.bp, r.key, r, b)", src)
        self.assertIn("_cbBpTiers(kind, b, eng)", src)


RED_PROOF = [
    {"why": "v3894 (#153, REG-3567) - the stats row no longer names the current tier",
     "file": "bible.html",
     "find": "      say = 'tier ' + k + '/' + T + ' \\u00b7 ' + say;\n",
     "replace": "      say = say;\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
