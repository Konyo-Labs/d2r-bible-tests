# -*- coding: utf-8 -*-
"""v3895 (#26, REG-3598) - P5: A SURGICAL RETRO FIX LEAVES A RECEIPT.

ledger_fixes.jsonl journals plan/apply. A fix without a proof frame is
refused (no receipt = STOPPED). Unreadable is UNKNOWN. Wiring apply is later.
RED_PROOF below.
"""
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _enable  # noqa: E402
_enable()

import ledger_fixes as M  # noqa: E402


class Case(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="ledger_fixes_")

    def test_a_written_row_is_read_back(self):
        row = M.record(self.root, "fix-1", "frame_1", plan="move Shako")
        self.assertEqual(row["frame"], "frame_1")
        self.assertEqual(M.fixes_of(self.root, "fix-1"), [row])
        self.assertEqual(M.fixes_of(self.root, "fix-other"), [])

    def test_absent_is_empty_and_unreadable_is_unknown(self):
        self.assertEqual(M.fixes_of(self.root, "missing"), [])
        row = M.record(self.root, "fix-1", "frame_1", plan="move Shako")
        self.assertEqual(row["frame"], "frame_1")
        with open(M.store_path(self.root), "w", encoding="utf-8") as fh:
            fh.write("{not json\n")
        self.assertIsNone(M.fixes_of(self.root, "x"))

    def test_a_row_needs_its_keys(self):
        with self.assertRaises(ValueError):
            M.record(self.root, "fix-1", "")


RED_PROOF = [
    {"why": "v3895 (#26, REG-3598) - P5: A SURGICAL RETRO FIX LEAVES A RECEIPT. - an unreadable store returns [] as if nothing was owed",
     "file": "tv/ledger_fixes.py",
     "find": "        except ValueError:\n            return None\n",
     "replace": "        except ValueError:\n            return []\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
