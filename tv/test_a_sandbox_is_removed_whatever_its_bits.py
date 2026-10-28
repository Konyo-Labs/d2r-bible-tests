# -*- coding: utf-8 -*-
"""REG-1746 — A PROVER SANDBOX IS REMOVED WHATEVER ITS PERMISSION BITS, AND "REMOVED" MEANS THE PATH IS GONE.

MEASURED on the ALT, 2026-10-02: 72 heart2.* sandboxes in its TEMP since 09-29 - 20,345 MB, with 25.8 GB free.
Each held the three files of a git pack, ~280 MB: git writes packs READ-ONLY, Windows refuses to unlink a
read-only file ("[WinError 5] Access is denied"), and every removal was rmtree(ignore_errors=True). The drop
deleted the owner file first, so the stale sweep read each leftover as ownerless and then failed on the same pack.
The sweep's own run removed 1 of 29 sandboxes older than a day - the one that still had its owner file and no pack.

  · DRIVEN: a planted sandbox whose bits block a plain rmtree (a read-only file for Windows, a read-only directory
    for POSIX - the same failure on each machine) is removed by the drop, by the stale sweep, and by the helper.
  · BASELINE first: a plain rmtree(ignore_errors=True) must LEAVE the planted tree, or the case cannot tell the two
    apart (running as an administrator/root, permissions do not bind - then it says so and skips).
  · DRIVEN: the helper's answer is whether the path still exists, and a drop that still fails says so on stderr.
RED_PROOF below. [[unknown-stays-unknown]] [[process-port-discipline]]
"""
import io
import os
import shutil
import stat
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
import fixture_tmp as _fx_tmp  # noqa: E402  #173 - its scratch is its own, so listing it keeps the law keyable
_fx_tmp.contain()

import heart2 as H  # noqa: E402


def _plant(root):
    """A sandbox the way the ALT's look: an owner file and a read-only git pack in a read-only directory."""
    pack = os.path.join(root, "repo", ".git", "objects", "pack")
    os.makedirs(pack)
    with io.open(os.path.join(root, H._SANDBOX_OWNER), "w") as fh:
        fh.write("999999")
    for n in ("pack-law.idx", "pack-law.pack"):
        p = os.path.join(pack, n)
        with io.open(p, "wb") as fh:
            fh.write(b"\0" * 64)
        os.chmod(p, stat.S_IREAD)                 # Windows: a read-only FILE cannot be unlinked
    os.chmod(pack, stat.S_IREAD | stat.S_IEXEC)   # POSIX: entries of a read-only DIRECTORY cannot be unlinked
    return root


def _force_clean(path):
    # #173 - walked through fixture_tmp.list_own: the folder is this run's own scratch, so the law stays keyable
    stack = [path]
    while stack:
        d = stack.pop()
        try:
            names = _fx_tmp.list_own(d)
        except (OSError, ValueError):
            continue
        for n in names:
            q = os.path.join(d, n)
            try:
                os.chmod(q, 0o700)
            except OSError:
                pass
            if os.path.isdir(q) and not os.path.islink(q):
                stack.append(q)
    shutil.rmtree(path, ignore_errors=True)


class _Tmp(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sandbox_bits_")
        self.addCleanup(_force_clean, self.tmp)

    def sandbox(self, name="heart2.law0001"):
        return _plant(os.path.join(self.tmp, name))


class TheBitsDoNotKeepASandbox(_Tmp):

    def test_baseline_a_plain_rmtree_leaves_it(self):
        root = self.sandbox("heart2.baseline")
        shutil.rmtree(root, ignore_errors=True)
        if not os.path.exists(root):
            self.skipTest("permissions do not bind for this user (administrator/root) - the planted tree cannot "
                          "tell a plain rmtree from the fix here; UNMEASURED on this machine, not passed")
        self.assertFalse(os.path.exists(os.path.join(root, H._SANDBOX_OWNER)),
                         "PREMISE: the plain pass deletes the owner file first and leaves the pack - the ALT's shape")

    def test_the_helper_removes_it_and_says_so(self):
        root = self.sandbox()
        self.assertTrue(H._rmtree_hard(root))
        self.assertFalse(os.path.exists(root), "the helper said gone and the sandbox is still on disk")

    def test_a_dropped_sandbox_is_gone(self):
        root = self.sandbox()
        H._SANDBOXES.add(root)
        H._drop_sandbox(root)
        self.assertFalse(os.path.exists(root), "a dropped sandbox is still on disk - one ~280 MB pack each on the ALT")
        self.assertNotIn(root, H._SANDBOXES)

    def test_the_stale_sweep_removes_an_old_one(self):
        root = self.sandbox("heart2.oldone1")
        later = time.time() + H.SANDBOX_STALE_S + 60
        gone = H.sweep_stale_sandboxes(tmp=self.tmp, now=later)
        self.assertFalse(os.path.exists(root), "the stale sweep left an old sandbox on disk")
        self.assertEqual([os.path.basename(p) for p, _ in gone], ["heart2.oldone1"],
                         "the sweep's report does not match what it removed: %r" % gone)


class TheAnswerIsThePath(_Tmp):

    def test_a_removal_that_failed_answers_false(self):
        root = self.sandbox()
        with mock.patch.object(H.shutil, "rmtree", lambda *a, **k: None):
            self.assertFalse(H._rmtree_hard(root), "the helper reported a sandbox gone that is still on disk")

    def test_a_drop_that_failed_says_so(self):
        root = self.sandbox()
        err = io.StringIO()
        with mock.patch.object(H.shutil, "rmtree", lambda *a, **k: None), mock.patch.object(sys, "stderr", err):
            H._drop_sandbox(root)
        self.assertIn("could not be removed", err.getvalue(),
                      "a sandbox that stayed on disk was dropped in silence - which is how 72 piled up")


RED_PROOF = [
    {"why": "REG-1746 - no second pass: the bits that blocked a plain rmtree still block it",
     "file": "heart2.py",
     "find": "    for dp, dns, fns in os.walk(path):\n        for n in dns:\n",
     "replace": "    for dp, dns, fns in []:\n        for n in dns:\n",
     "matches": 1},
    {"why": "REG-1746 - the stale sweep back on a plain rmtree",
     "file": "heart2.py",
     "find": "        if _rmtree_hard(root):                  # REG-1746 — a read-only git pack kept 71 of these on the ALT\n",
     "replace": "        shutil.rmtree(root, ignore_errors=True)\n        if not os.path.exists(root):\n",
     "matches": 1},
    {"why": "REG-1746 - the drop back on a plain rmtree, in silence",
     "file": "heart2.py",
     "find": "    if not _rmtree_hard(root):\n        sys.stderr.write(",
     "replace": "    shutil.rmtree(root, ignore_errors=True)\n    if False:\n        sys.stderr.write(",
     "matches": 1},
    {"why": "REG-1746 - the helper answers that the call returned, not that the path is gone",
     "file": "heart2.py",
     "find": "    shutil.rmtree(path, ignore_errors=True)\n    return not os.path.exists(path)\n",
     "replace": "    shutil.rmtree(path, ignore_errors=True)\n    return True\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
