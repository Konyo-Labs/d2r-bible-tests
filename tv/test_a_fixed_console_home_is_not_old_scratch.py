#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v3900 (REG-3738) - A FIXED WORKING HOME THE CONSOLE REUSES IS NOT "OLD SCRATCH NOBODY COLLECTS".

MEASURED 11-11 on his Mac (the fleet error feed, then the temp folder itself): "4 of 165 scratch director(ies) WE made are older
than 3 days - oldest 6.0 days. Nothing is collecting them". Two of the four were tvd-g5-home and tvd-vision-cwd - the stand-in
HOME g5_grok_eyes empties and reuses before every lean read, and tv_diablo's vision cwd - FIXED paths by design, whose mtime
ages while they work. Deleting them to quiet the row would have broken his console's vision lane. The other two were real
litter of ours (law-run ledgers) and went to the Trash. The row now skips exactly the fixed homes; their mkdtemp fallbacks
("tvd-g5-home-xxxx") are still litter and still counted.

DRIVEN: the real check over a fixture temp root. And each fixed name is tied to the line in its owning module that makes it, so
a renamed home cannot hide behind a stale list. RED_PROOF below.
"""
import io
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

import console_doctor as CD  # noqa: E402

OLD_S = 6 * 86400


def _root(names_old, names_new):
    d = tempfile.mkdtemp(prefix="fixedhome_")
    for n in names_old + names_new:
        os.makedirs(os.path.join(d, n))
    t = time.time() - OLD_S
    for n in names_old:
        os.utime(os.path.join(d, n), (t, t))
    return d


class AFixedConsoleHomeIsNotOldScratch(unittest.TestCase):

    def _check(self, root):
        with mock.patch("tempfile.gettempdir", lambda: root):
            return CD._check_nothing_we_made_is_still_on_his_disk_days_later()

    def test_the_fixed_homes_are_not_counted_but_their_fallback_is(self):
        """* THE POINT - his Mac's shape: two old fixed homes, one old mkdtemp fallback, one fresh dir"""
        root = _root(["tvd-g5-home", "tvd-vision-cwd", "tvd-g5-home-ab12cd"], ["tvd-fresh-1"])
        self.addCleanup(shutil.rmtree, root, True)
        st, say = self._check(root)
        self.assertEqual(st, CD.MISSING, say)
        self.assertTrue(say.startswith("1 of 2 scratch"), "a fixed console home was counted as old litter: %s" % say)

    def test_only_fixed_homes_old_is_not_a_finding(self):
        root = _root(["tvd-g5-home", "tvd-vision-cwd"], ["tvd-fresh-1"])
        self.addCleanup(shutil.rmtree, root, True)
        st, say = self._check(root)
        self.assertNotEqual(st, CD.MISSING, "two fixed homes in use read as uncollected scratch: %s" % say)

    def test_baseline_old_litter_is_still_a_finding(self):
        root = _root(["tvd-gate-ledgers-xyz", "tmpabc"], ["tvd-fresh-1"])
        self.addCleanup(shutil.rmtree, root, True)
        st, say = self._check(root)
        self.assertEqual(st, CD.MISSING, say)
        self.assertTrue(say.startswith("2 of 3 scratch"), say)

    def test_each_fixed_name_is_made_by_its_owner(self):
        def src(name):
            with io.open(os.path.join(HERE, name), encoding="utf-8") as fh:
                return fh.read()
        self.assertIn('os.path.join(tempfile.gettempdir(), "tvd-g5-home")', src("g5_grok_eyes.py"),
                      "g5_grok_eyes no longer makes the fixed home this row skips - the skip list is stale")
        self.assertIn('os.path.join(tempfile.gettempdir(), "tvd-vision-cwd")', src("tv_diablo.py"),
                      "tv_diablo no longer makes the vision cwd this row skips - the skip list is stale")


RED_PROOF = [
    {"why": "REG-3738 - the console's fixed working homes read as old uncollected scratch again (his Mac, 11-11)",
     "file": "tv/console_doctor.py",
     "find": "                if not e.name.startswith(MINE) or e.name in FIXED_HOMES:\n",
     "replace": "                if not e.name.startswith(MINE):\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
