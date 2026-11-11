#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v3899 (REG-3729) - A CHRONICLE PAGE OF "NOT FOUND" READINGS IS TESTIMONY, NEVER THE EMPTIED-LEDGER SHAPE.

MEASURED 11-11 on the work ALT (SSH, read-only): its evidence ledger is new - one Chronicle page banked today, 0 names read
FOUND and 6 uniques read NOT FOUND. The doctor's evidence-ledger row counted only found names, so it called that ledger
"the v1779 shape: a ledger emptied after the reading happened" on every look, and the fleet's error feed carried it as a
new UNKNOWN. A red that is always wrong teaches everyone to skip the row on the day it is right.

Now a not-found name counts as a reading the page gave; a ledger with no name of EITHER kind after banked pages is still the
emptied shape. DRIVEN: the real _check_the_evidence_ledger_is_readable over fixture ledgers. RED_PROOF below.
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import console_doctor as CD  # noqa: E402


def _ledger(found_u=(), not_found_u=(), pages=1):
    return {"uniques": dict((n, [{"reel": "r", "frame": "f"}]) for n in found_u), "sets": {},
            "notFound": {"uniques": list(not_found_u), "sets": []}, "pagesRead": pages}


class ANotFoundPageIsTestimony(unittest.TestCase):

    def _check(self, ev):
        tmp = tempfile.mkdtemp(prefix="evidledger_")
        self.addCleanup(shutil.rmtree, tmp, True)
        with io.open(os.path.join(tmp, "chron_evidence.json"), "w", encoding="utf-8") as fh:
            json.dump(ev, fh)
        with mock.patch.object(CD, "HERE", tmp):
            return CD._check_the_evidence_ledger_is_readable()

    def test_a_page_read_all_not_found_is_not_an_emptied_ledger(self):
        """* THE POINT - the work ALT's real shape: 1 page, 0 found, 6 not found"""
        st, say = self._check(_ledger(not_found_u=("Ali Baba", "Atma's Wail", "Blinkbat's Form", "Bloodfist",
                                                   "Boneflame", "Bul-Kathos' Wedding Band")))
        self.assertEqual(st, CD.OK, "a page of not-found readings was called an emptied ledger: %s" % say)
        self.assertIn("6 name(s) read NOT FOUND", say)

    def test_baseline_a_banked_page_with_no_name_at_all_is_still_the_emptied_shape(self):
        st, say = self._check(_ledger())
        self.assertEqual(st, CD.MISSING, "a ledger with no name of either kind after a banked page reads healthy: %s" % say)
        self.assertIn("v1779 shape", say)

    def test_found_names_stay_ok(self):
        st, say = self._check(_ledger(found_u=("Shako",), pages=3))
        self.assertEqual(st, CD.OK, say)
        self.assertNotIn("NOT FOUND", say, "a ledger with no not-found reading claims one")


RED_PROOF = [
    {"why": "REG-3729 - the evidence-ledger row counts only found names again, and a page of not-found readings reads as "
            "the emptied-ledger shape (the work ALT, 11-11)",
     "file": "tv/console_doctor.py",
     "find": "    n_nf = sum(len(v) for v in _nf.values() if isinstance(v, (list, dict)))\n",
     "replace": "    n_nf = 0\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
