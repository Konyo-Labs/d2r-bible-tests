# -*- coding: utf-8 -*-
"""v3894 (#28, REG-3578) - A PLANNER COMPARE DOES NOT INVENT MISSING NUMBERS.

A sheet row that disagrees with a cited planner value is a conflict. A planner
key without frames, or a window row without frames, is unknown. Nothing is filled in.
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


class APlannerCompareDoesNotInventMissingNumbers(unittest.TestCase):

    def test_conflict_and_unknown_are_not_filled_in(self):
        import char_window_vs_planner as CMP
        conflict = CMP.compare_window_to_planner(
            {"rows": [{"key": "fcr", "frames": 11}]},
            {"fcr": {"frames": 13, "source": "cited"}})
        self.assertEqual(conflict[0]["verdict"], "conflict")
        self.assertEqual(conflict[0]["window"], 11)
        self.assertEqual(conflict[0]["planner"], 13)
        missing = CMP.compare_window_to_planner({"rows": []}, {"fcr": {"frames": 13}})
        self.assertEqual(missing[0]["verdict"], "unknown")
        noframes = CMP.compare_window_to_planner(
            {"rows": [{"key": "fcr", "step": "no count"}]}, {"fcr": {"note": "x"}})
        self.assertEqual(noframes[0]["verdict"], "unknown")
        empty = CMP.compare_window_to_planner({"rows": []}, None)
        self.assertEqual(empty[0]["verdict"], "unknown")


RED_PROOF = [
    {"why": "v3894 (#28, REG-3578) - a mismatch is reported as agree",
     "file": "tv/char_window_vs_planner.py",
     "find": "            rec = {\"key\": key, \"verdict\": \"conflict\",\n                   \"window\": frames, \"planner\": ref[\"frames\"]}\n",
     "replace": "            rec = {\"key\": key, \"verdict\": \"agree\",\n                   \"window\": frames, \"planner\": ref[\"frames\"]}\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
