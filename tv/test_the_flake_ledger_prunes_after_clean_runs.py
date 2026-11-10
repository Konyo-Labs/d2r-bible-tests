# -*- coding: utf-8 -*-
"""REG-3644 - A HEALED FLAKE DROPS OUT OF THE LEDGER AFTER N CLEAN RUNS.

A known flake is auto-rerun once. After nClean (3) consecutive green runs it is
removed, so a healed test does not buy a silent retry forever. A name that was
never a flake is not added on a clean run. A runner shutdown is always rerun-worthy,
ledger or not.
"""
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import flake_ledger as FL  # noqa: E402


class TheLawHolds(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="flake-")
        os.makedirs(os.path.join(self.d, "tv"))
        self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)

    def test_a_flake_is_pruned_after_n_cleans(self):
        FL.record("shard 15", failed=True, root=self.d, save_file=True, now=1)
        self.assertTrue(FL.is_flake("shard 15", root=self.d))
        for i in range(FL.N_CLEAN - 1):
            FL.record("shard 15", failed=False, root=self.d, save_file=True, now=2 + i)
            self.assertTrue(FL.is_flake("shard 15", root=self.d), "still a flake after %d clean(s)" % (i + 1))
        FL.record("shard 15", failed=False, root=self.d, save_file=True, now=10)
        self.assertFalse(FL.is_flake("shard 15", root=self.d), "should have been pruned")

    def test_a_fail_resets_the_clean_streak(self):
        FL.record("job", failed=True, root=self.d, now=1)
        FL.record("job", failed=False, root=self.d, now=2)
        FL.record("job", failed=False, root=self.d, now=3)
        FL.record("job", failed=True, root=self.d, now=4)
        row = (FL.load(self.d)["entries"]["job"])
        self.assertEqual(row["cleans"], 0)
        self.assertEqual(row["fails"], 2)

    def test_a_clean_unknown_name_is_not_added(self):
        FL.record("never-seen", failed=False, root=self.d, now=1)
        self.assertFalse(FL.is_flake("never-seen", root=self.d))

    def test_a_runner_kill_is_rerun_without_being_a_named_flake(self):
        ok, why = FL.should_rerun("shard 7", log_text="The runner has received a shutdown signal", root=self.d)
        self.assertTrue(ok, why)
        ok2, why2 = FL.should_rerun("agent-suite", log_text="tests failed: 3", root=self.d)
        self.assertFalse(ok2, why2)


if __name__ == "__main__":
    unittest.main()
