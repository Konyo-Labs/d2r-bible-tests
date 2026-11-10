# -*- coding: utf-8 -*-
"""v3895 (#26, REG-3588) - P2: A SEALED REEL LEAVES A ROUTE RECEIPT.

reel_routes.jsonl is append-only. A receipt names the reel and where it routed.
An unreadable store is UNKNOWN (None), never an empty list that would look like
'no receipts, nothing owed'. Wiring the sealer and the shelf door is the rest of P2.
RED_PROOF below.
"""
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _enable  # noqa: E402
_enable()

import reel_routes as RR  # noqa: E402


class ASealedReelLeavesARouteReceipt(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="reel_routes_")

    def test_a_written_receipt_is_read_back(self):
        row = RR.record(self.root, "reel_s_1", name="Shako", frameKey="f_1",
                        routedTo="vault", why="a unique", gate="stash")
        self.assertEqual(row["reel"], "reel_s_1")
        got = RR.routes_of(self.root, "reel_s_1")
        self.assertEqual(got, [row])
        self.assertEqual(RR.routes_of(self.root, "reel_s_other"), [])

    def test_absent_is_empty_and_unreadable_is_unknown(self):
        self.assertEqual(RR.routes_of(self.root, "reel_s_1"), [])
        self.assertEqual(RR.missing_receipts(self.root, ["reel_s_1"]), ["reel_s_1"])
        RR.record(self.root, "reel_s_1", routedTo="vault")
        self.assertEqual(RR.missing_receipts(self.root, ["reel_s_1", "reel_s_2"]), ["reel_s_2"])
        with open(RR.store_path(self.root), "w", encoding="utf-8") as fh:
            fh.write("{not json\n")
        self.assertIsNone(RR.routes_of(self.root, "reel_s_1"))
        self.assertIsNone(RR.missing_receipts(self.root, ["reel_s_1"]))

    def test_a_receipt_needs_a_reel(self):
        with self.assertRaises(ValueError):
            RR.record(self.root, "")


RED_PROOF = [
    {"why": "v3895 (#26, REG-3588) - an unreadable store returns [] as if nothing was owed",
     "file": "tv/reel_routes.py",
     "find": "        except ValueError:\n            return None\n",
     "replace": "        except ValueError:\n            return []\n",
     "matches": 2},
]


if __name__ == "__main__":
    unittest.main()
