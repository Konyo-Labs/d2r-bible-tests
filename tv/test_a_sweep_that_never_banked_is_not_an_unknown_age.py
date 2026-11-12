# -*- coding: utf-8 -*-
"""#86 gap audit 26 (REG-1778) — A SWEEP THAT NEVER BANKED A READ IS NOT AN UNKNOWN AGE.

The reel-extract row took the sweep memory's mtime whenever reels still owed a read. Any failure,
including a file that was never written, came back UNKNOWN ("its age is unknown"). An unknown is
not counted, so a console that has never banked a read looked like one whose clock could not be
read.

  · DRIVEN: no chronicle_swept.json, one reel on a fixture shelf -> MISSING, and the sentence
    says no read has ever been banked. Not the age sentence.
  · DRIVEN: the file is there and will not stat -> UNKNOWN, and a retained read is still named.
  · DRIVEN: a bank that exists is still the age rule. Fresh stays the loop working. Older than
    two hours stays MISSING for that age, not for a memory that was never written.
Nothing here reads his sweep memory or his shelf. RED_PROOF below. [[unknown-stays-unknown]]
"""
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import console_doctor as cd  # noqa: E402
import control_app as ca  # noqa: E402


def _frame(reel_dir):
    os.makedirs(reel_dir)
    with open(os.path.join(reel_dir, "f_1780000000000.jpg"), "wb") as fh:
        fh.write(b"\xff\xd8\xff\xe0" + b"0" * 32)


class ASweepThatNeverBanked(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="never_banked_")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.hist = os.path.join(self.root, "hist")
        os.makedirs(self.hist)
        _frame(os.path.join(self.hist, "reel_never_banked"))
        self.swept = os.path.join(self.root, "chronicle_swept.json")
        self._saved = {k: os.environ.get(k) for k in ("TV_HIST", "TV_CHRON_SWEPT")}
        os.environ["TV_HIST"] = self.hist
        os.environ["TV_CHRON_SWEPT"] = self.swept
        self.addCleanup(self._restore_env)

    def _restore_env(self):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def _ask(self, getmtime=None):
        patch = mock.patch.object(ca, "_chron_reels_seen", return_value=set())
        if getmtime is None:
            with patch:
                return cd._check_the_reel_extract_is_moving()
        with patch, mock.patch.object(cd.os.path, "getmtime", getmtime):
            return cd._check_the_reel_extract_is_moving()

    def test_a_memory_that_was_never_written_is_missing(self):
        self.assertFalse(os.path.exists(self.swept))
        state, why = self._ask()
        self.assertEqual(state, cd.MISSING, why)
        self.assertIn("1 reel(s) owe a read and no read has ever been banked on this console", why)
        self.assertNotIn("age is unknown", why)
        self.assertNotIn("the loop is working", why)

    def test_a_memory_that_will_not_stat_stays_unknown(self):
        with open(self.swept, "w", encoding="utf-8") as fh:
            json.dump({"reel_pruned": {"pages": 22, "ts": 1}}, fh)

        def refuse(_path):
            raise PermissionError("stat refused")

        state, why = self._ask(getmtime=refuse)
        self.assertEqual(state, cd.UNKNOWN, why)
        self.assertIn("1 reel(s) owe a read and the sweep memory cannot be read, so its age "
                      "is unknown", why)
        self.assertIn("1 more entry retained for footage since pruned", why)
        self.assertNotIn("no read has ever been banked", why)

    def test_a_bank_that_exists_is_still_judged_by_its_age(self):
        with open(self.swept, "w", encoding="utf-8") as fh:
            json.dump({"reel_pruned": {"pages": 22, "ts": 1}}, fh)
        state, why = self._ask()
        self.assertEqual(state, cd.OK, why)
        self.assertIn("last banked", why)
        self.assertIn("the loop is working", why)
        self.assertIn("1 more entry retained for footage since pruned", why)
        self.assertNotIn("no read has ever been banked", why)

        old = time.time() - (3 * 3600)
        os.utime(self.swept, (old, old))
        state, why = self._ask()
        self.assertEqual(state, cd.MISSING, why)
        self.assertIn("nothing has been banked for", why)
        self.assertIn("1 more entry retained for footage since pruned", why)
        self.assertNotIn("no read has ever been banked", why)
        self.assertNotIn("age is unknown", why)


RED_PROOF = [
    {"why": "REG-1778 - a sweep memory that was never written reads as an unknown age, and an unknown is not counted",
     "file": "console_doctor.py",
     # v3901 (REG-3757) - re-anchored: the row now carries the signed-out note too
     "find": "    except FileNotFoundError:\n"
             "        return MISSING, (\"%d reel(s) owe a read and no read has ever been banked on this console%s%s\"\n"
             "                         % (len(owed), _paid_reads_blocked_note(), tail + _ret))   # REG-3757 - the sweep's reads are paid\n",
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
