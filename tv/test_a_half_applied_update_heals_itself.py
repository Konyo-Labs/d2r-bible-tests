# -*- coding: utf-8 -*-
"""v3900 (REG-3740) - AN UPDATE STOPPED MID-CHECKOUT HEALS ON THE NEXT PULL: MAIN'S OWN NEW FILES ARE NOT "IN THE WAY".

MEASURED 11-11/12 on two PCs (SSH, backed up byte-exact first): the OLD ALT and then Dean's PC sat 97 commits behind with
"pull refused" for good. Dean: HEAD 294de4f25 (11-10's main), 85 tracked files changed, 53 untracked, no index.lock. Every
one of the 85 changed files and all 43 update-added untracked files are byte-for-byte origin/main ad5945968 (v3898) - an
update to v3898 that wrote part of the tree and never moved HEAD (the other 10 untracked are the console's own runtime
files). launcher_pull.apply resets only a tree whose changes ARE the update - and it refused here because main's new files,
already on disk, read as "an untracked file is in the way". So the console stood down as 'dirty' every 15 minutes, and its
proof import refused the edited tree, until a hand reset. An untracked REGULAR file whose bytes are origin/main's own blob at
that path (CR ignored) is the update itself: the reset writes those same bytes. Different bytes, a directory or a link is
still his and still stops the reset.

DRIVEN: the real apply() over a real git fixture. RED_PROOF below.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

import launcher_pull as lp  # noqa: E402


def _git(d, *a):
    subprocess.check_call(["git", "-C", d] + list(a))


def _out(d, *a):
    return subprocess.check_output(["git", "-C", d] + list(a), text=True).strip()


class AHalfAppliedUpdateHealsItself(unittest.TestCase):

    def setUp(self):
        # REG-2360 - inside a git hook GIT_DIR points at the REAL repo and beats -C; dropped for these cases only
        _gitenv = {_k: os.environ.pop(_k) for _k in list(os.environ) if _k.startswith("GIT_")}
        self.addCleanup(os.environ.update, _gitenv)
        self.d = tempfile.mkdtemp(prefix="halfapply_")
        self.addCleanup(shutil.rmtree, self.d, True)
        d = self.d
        subprocess.check_call(["git", "init", "-q"], cwd=d)
        _git(d, "config", "core.autocrlf", "false")
        _git(d, "config", "user.email", "t@example.com")
        _git(d, "config", "user.name", "t")
        self._write("a.txt", b"one\n")
        _git(d, "add", "a.txt")
        _git(d, "commit", "-q", "-m", "one")
        self.head = _out(d, "rev-parse", "HEAD")
        # main moves on: a.txt changes and a NEW file arrives
        self._write("a.txt", b"two\n")
        os.makedirs(os.path.join(d, "tv"))
        self._write("tv/new_law.py", b"print('from main')\n")
        _git(d, "add", "-A")
        _git(d, "commit", "-q", "-m", "two")
        self.main = _out(d, "rev-parse", "HEAD")
        _git(d, "update-ref", "refs/remotes/origin/main", self.main)
        _git(d, "reset", "-q", "--hard", self.head)
        self.assertFalse(os.path.exists(os.path.join(d, "tv", "new_law.py")), "PREMISE: the fixture did not go back")

    def _write(self, rel, data):
        p = os.path.join(self.d, rel)
        if not os.path.isdir(os.path.dirname(p)):
            os.makedirs(os.path.dirname(p))
        with open(p, "wb") as fh:
            fh.write(data)

    def _read(self, rel):
        with open(os.path.join(self.d, rel), "rb") as fh:
            return fh.read()

    def _half_apply(self, new_bytes=b"print('from main')\n"):
        """Dean's shape: the update wrote a.txt and the new file, and HEAD never moved."""
        self._write("a.txt", b"two\n")
        self._write("tv/new_law.py", new_bytes)

    def test_a_half_applied_update_lands_on_the_next_pull(self):
        """* THE POINT - Dean 11-12: main's own files on disk, HEAD unmoved, every pull refused for good"""
        self._half_apply()
        self.assertEqual(lp.apply(self.d), 0, "a tree that IS the update was refused")
        self.assertEqual(_out(self.d, "rev-parse", "HEAD"), self.main)
        self.assertEqual(_out(self.d, "status", "--porcelain"), "", "the tree is not clean on main after the heal")

    def test_the_same_new_file_written_with_CR_is_still_the_update(self):
        """a Windows checkout (autocrlf=true) writes CR LF - the console's one byte rule ignores CR"""
        self._half_apply(new_bytes=b"print('from main')\r\n")
        self.assertEqual(lp.apply(self.d), 0)
        self.assertEqual(_out(self.d, "rev-parse", "HEAD"), self.main)

    def test_baseline_a_new_file_with_his_own_bytes_still_stops_the_reset(self):
        self._half_apply(new_bytes=b"his own work\n")
        self.assertEqual(lp.apply(self.d), 2)
        self.assertEqual(_out(self.d, "rev-parse", "HEAD"), self.head, "his file's path was reset over")
        self.assertEqual(self._read("tv/new_law.py"), b"his own work\n")

    @unittest.skipIf(os.name == "nt", "a symlink needs a privilege on Windows - the regular-file rule is the same code")
    def test_a_link_where_main_adds_the_file_still_stops_the_reset(self):
        self._write("a.txt", b"two\n")
        self._write("elsewhere.txt", b"print('from main')\n")
        os.makedirs(os.path.join(self.d, "tv"))     # the fixture's reset took the empty folder away
        os.symlink(os.path.join(self.d, "elsewhere.txt"), os.path.join(self.d, "tv", "new_law.py"))
        self.assertEqual(lp.apply(self.d), 2, "a link whose target holds main's bytes was taken as the update")
        self.assertEqual(_out(self.d, "rev-parse", "HEAD"), self.head)
        self.assertTrue(os.path.islink(os.path.join(self.d, "tv", "new_law.py")))


RED_PROOF = [
    {"why": "REG-3740 - main's own new files on disk read as 'in the way' again, so a half-applied update never lands "
            "(Dean and the OLD ALT, 97 behind, 11-11/12)",
     "file": "tv/launcher_pull.py",
     "find": "        if occupied and not _is_the_updates_own_file(repo, rel):\n",
     "replace": "        if occupied:\n",
     "matches": 1},
    {"why": "REG-3740 - a link (or any non-regular file) whose target holds main's bytes is taken as the update",
     "file": "tv/launcher_pull.py",
     "find": "        if not stat.S_ISREG(os.lstat(os.path.join(repo, rel)).st_mode):\n",
     "replace": "        if not stat.S_ISREG(os.stat(os.path.join(repo, rel)).st_mode):\n",
     "matches": 1, "needs": "posix"},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
