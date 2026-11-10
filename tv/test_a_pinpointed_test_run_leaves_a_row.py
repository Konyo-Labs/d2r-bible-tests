# -*- coding: utf-8 -*-
"""v3895 (#26, REG-3597) - P4: A PINPOINTED TEST RUN LEAVES A ROW.

test_runs.jsonl holds START baselines and verdicts. A run with no verdict
is open. Unreadable is UNKNOWN. Wiring START buttons is later.
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

import ledger_test_runs as M  # noqa: E402


class Case(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="ledger_test_runs_")

    def test_a_written_row_is_read_back(self):
        row = M.record(self.root, "run-1", session="s1", verdict=None)
        self.assertEqual(row["id"], "run-1")
        self.assertEqual(M.runs_of(self.root, "run-1"), [row])
        self.assertEqual(M.runs_of(self.root, "run-other"), [])
        self.assertEqual(M.open_runs(self.root), [row])

    def test_absent_is_empty_and_unreadable_is_unknown(self):
        self.assertEqual(M.runs_of(self.root, "missing"), [])
        row = M.record(self.root, "run-1", session="s1", verdict=None)
        self.assertEqual(row["id"], "run-1")
        with open(M.store_path(self.root), "w", encoding="utf-8") as fh:
            fh.write("{not json\n")
        self.assertIsNone(M.runs_of(self.root, "x"))

    def test_a_row_needs_its_keys(self):
        with self.assertRaises(ValueError):
            M.record(self.root, "")


RED_PROOF = [
    {"why": "v3895 (#26, REG-3597) - P4: A PINPOINTED TEST RUN LEAVES A ROW. - an unreadable store returns [] as if nothing was owed",
     "file": "tv/ledger_test_runs.py",
     "find": "        except ValueError:\n            return None\n",
     "replace": "        except ValueError:\n            return []\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
