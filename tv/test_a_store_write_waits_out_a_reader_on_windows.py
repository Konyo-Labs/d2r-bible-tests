# -*- coding: utf-8 -*-
"""v3886 (#107, the Grok CLI's triage of windows-latest) - A STORE WRITE ON WINDOWS WAITS OUT A READER; IT IS NOT REFUSED.

windows-latest, test_provenance's concurrent reader: "PermissionError: [WinError 5] Access is denied: store.json.<x>.tmp ->
store.json". Windows refuses to replace a file another handle holds open, so bump_version.atomic_write (the one torn-read-
safe write: provenance.save_json and the four stamps go through it) refused a store while it was being read - and on his
PCs the console's own threads are that reader. atomic_write now replaces through _replace_held: a held target is retried
for a bounded second on Windows; one still held after that raises as before (never a silent skip), and off Windows the
replace runs once.

Drives the SHIPPED _replace_held with os.replace refusing the way Windows does. RED_PROOF below.
"""
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import bump_version as BV  # noqa: E402


class AStoreWriteWaitsOutAReaderOnWindows(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="tvd_held_")
        self.addCleanup(shutil.rmtree, self.tmp, True)   # its own temp folder, removed whole - nothing is listed
        self.src, self.dst = os.path.join(self.tmp, "a.tmp"), os.path.join(self.tmp, "store.json")
        with open(self.src, "w") as fh:
            fh.write("new")
        with open(self.dst, "w") as fh:
            fh.write("old")
        self.real = os.replace
        self.slept = []

    def _held_for(self, n):
        calls = []

        def _replace(a, b):
            calls.append(1)
            if len(calls) <= n:
                raise PermissionError(13, "[WinError 5] Access is denied")
            return self.real(a, b)
        return _replace, calls

    def test_a_reader_that_lets_go_is_waited_out_on_windows(self):
        """* THE POINT - held for 3 tries, then free: the write lands, after 3 short waits"""
        rep, calls = self._held_for(3)
        with mock.patch.object(BV.os, "replace", rep), mock.patch.object(BV.os, "name", "nt"):
            BV._replace_held(self.src, self.dst, sleep=self.slept.append)
        self.assertEqual(len(calls), 4)
        self.assertEqual(len(self.slept), 3)
        with open(self.dst) as fh:
            self.assertEqual(fh.read(), "new", "the store was not written")

    def test_a_target_held_past_the_bound_still_raises(self):
        """never a silent skip: a reader that never lets go is the old refusal, after the bound"""
        rep, calls = self._held_for(10 ** 6)
        with mock.patch.object(BV.os, "replace", rep), mock.patch.object(BV.os, "name", "nt"):
            with self.assertRaises(PermissionError):
                BV._replace_held(self.src, self.dst, tries=5, sleep=self.slept.append)
        self.assertEqual((len(calls), len(self.slept)), (5, 4))

    def test_off_windows_it_runs_once(self):
        """baseline: a POSIX PermissionError is a real refusal (a read-only dir), never retried"""
        rep, calls = self._held_for(1)
        with mock.patch.object(BV.os, "replace", rep), mock.patch.object(BV.os, "name", "posix"):
            with self.assertRaises(PermissionError):
                BV._replace_held(self.src, self.dst, sleep=self.slept.append)
        self.assertEqual((len(calls), self.slept), (1, []))

    def test_the_one_write_replaces_through_it(self):
        import inspect
        self.assertIn("_replace_held(tmp, path)", inspect.getsource(BV.atomic_write),
                      "atomic_write replaces some other way - a held store refuses the write on Windows again")


RED_PROOF = [
    {"why": "v3886 (#107) - a Windows store write is refused by any reader again (no wait)",
     "file": "tv/bump_version.py",
     "find": "            if os.name != \"nt\" or i >= int(tries) - 1:\n",
     "replace": "            if True:\n",
     "matches": 1},
    {"why": "v3886 (#107) - atomic_write stops replacing through the reader-safe step",
     "file": "tv/bump_version.py",
     "find": "        _replace_held(tmp, path)\n",
     "replace": "        os.replace(tmp, path)\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
