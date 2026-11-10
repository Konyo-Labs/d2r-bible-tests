# -*- coding: utf-8 -*-
"""v3895 (#26, REG-3596) - P3: A TIER CROSSING LEAVES A LOG ROW.

ledger.tier crossings append to tier_log.jsonl when a merge changes a tier.
Unreadable is UNKNOWN, not an empty owed-nothing. Wiring vault_retro is later.
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

import tier_log as M  # noqa: E402


class Case(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="tier_log_")

    def test_a_written_row_is_read_back(self):
        row = M.record(self.root, "Shako", "keep", from_tier="found", reel="reel_s_1")
        self.assertEqual(row["toTier"], "keep")
        self.assertEqual(M.crossings_of(self.root, "Shako"), [row])
        self.assertEqual(M.crossings_of(self.root, "Enigma"), [])

    def test_absent_is_empty_and_unreadable_is_unknown(self):
        self.assertEqual(M.crossings_of(self.root, "missing"), [])
        row = M.record(self.root, "Shako", "keep", from_tier="found", reel="reel_s_1")
        self.assertEqual(row["toTier"], "keep")
        with open(M.store_path(self.root), "w", encoding="utf-8") as fh:
            fh.write("{not json\n")
        self.assertIsNone(M.crossings_of(self.root, "x"))

    def test_a_row_needs_its_keys(self):
        with self.assertRaises(ValueError):
            M.record(self.root, "", "keep")


RED_PROOF = [
    {"why": "v3895 (#26, REG-3596) - P3: A TIER CROSSING LEAVES A LOG ROW. - an unreadable store returns [] as if nothing was owed",
     "file": "tv/tier_log.py",
     "find": "        except ValueError:\n            return None\n",
     "replace": "        except ValueError:\n            return []\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
