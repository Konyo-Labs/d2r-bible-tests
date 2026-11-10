# -*- coding: utf-8 -*-
"""REG-3643 - THE SHARD BALANCE FILE NAMES EVERY PROOF TEST.

A proof with no measured price used to ride a default and could unbalance a shard
(v3878: test_control priced at 19 s when it took 226-263 s). tv/shard_timings.json
holds a row for every proof test the plan would cut, measured when a green round
has measured it, otherwise the median of the measured set. This law refuses a
missing row.
"""
import sys
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import shard_timings as ST  # noqa: E402


class TheLawHolds(unittest.TestCase):
    def test_every_proof_test_has_a_row(self):
        ok, missing, _ = ST.coverage()
        self.assertTrue(ok, "shard_timings.json is missing %d proof(s): %s"
                        % (len(missing), ", ".join(missing[:15])))

    def test_measured_rows_are_preferred(self):
        doc = ST.load()
        self.assertIsNotNone(doc, "the timings file will not read - UNKNOWN, not empty")
        proofs = doc.get("proofs") or {}
        measured = sum(1 for v in proofs.values() if (v or {}).get("src") == "measured")
        self.assertGreater(measured, 300, "the timings file lost the measured runner prices")


if __name__ == "__main__":
    unittest.main()
