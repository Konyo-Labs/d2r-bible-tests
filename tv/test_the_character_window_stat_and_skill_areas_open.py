# -*- coding: utf-8 -*-
"""v3894 (#234/#146, REG-3572) - STAT AND SKILL AREAS IN THE CHARACTER WINDOW OPEN.

Strength through IAS and the skill tree each have a data-cell (stat: / skill:)
that opens a detail sentence. A number is shown only when the character already
carries it; nothing here invents a stat.
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


class TheCharacterWindowStatAndSkillAreasOpen(unittest.TestCase):

    def test_stat_and_skill_areas_are_clickable(self):
        src = _read("bible.html")
        self.assertIn("function _chxStatHtml(t)", src)
        self.assertIn("['stat:str', 'Strength']", src)
        self.assertIn("['skill:tree', 'Skill tree']", src)
        self.assertIn('data-grid="stats"', src)
        # v3894 - the CALL, not the name: "_chxStatHtml(t)" alone is satisfied by the function's own definition, so a page
        # that stopped drawing the stat areas stayed green and proof [0] filed BLIND on GitHub (run 42884325588)
        self.assertEqual(src.count("+ _chxStatHtml(t)"), 1, "the character window no longer draws its stat and skill areas")


RED_PROOF = [
    {"why": "v3894 (#234, REG-3572) - stat and skill areas are no longer drawn",
     "file": "bible.html",
     "find": "      + _chxStatHtml(t)\n",
     "replace": "      + ''\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
