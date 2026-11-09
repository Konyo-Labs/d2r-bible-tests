# -*- coding: utf-8 -*-
"""v3894 (#28, REG-3574) - THE CHARACTER WINDOW AGREES WITH CITED PLANNER BREAKPOINTS.

A bare Sorceress at 0% FCR is 13 frames on the maxroll Patch 2.4 tables
(fetched 2026-10-04) that d2planner uses. compare_window_to_planner reports agree.
No itemized d2planner sheet was invented; buff calibration stays later.
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


class TheCharacterWindowAgreesWithCitedPlannerBreakpoints(unittest.TestCase):

    def test_a_cited_sorceress_fcr_row_agrees(self):
        import char_window_vs_planner as CMP
        sheet = {"rows": [{"key": "fcr", "step": "13 frames. +9% more reaches the next step."}]}
        got = CMP.compare_window_to_planner(sheet, CMP.CITED_SORC_FCR_0)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["verdict"], "agree")
        self.assertEqual(got[0]["frames"], 13)
        self.assertIn("maxroll Patch 2.4", got[0]["source"])


RED_PROOF = [
    {"why": "v3894 (#28, REG-3574) - a matching cited breakpoint is no longer called agree",
     "file": "tv/char_window_vs_planner.py",
     "find": "            rec = {\"key\": key, \"verdict\": \"agree\", \"frames\": frames}\n",
     "replace": "            rec = {\"key\": key, \"verdict\": \"unknown\", \"frames\": frames}\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
