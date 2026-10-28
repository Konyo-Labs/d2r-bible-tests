# -*- coding: utf-8 -*-
"""REG-2491 / REG-2492 / REG-2493 - NO d2jsp COOKIE COPY, SCRATCH CHROME OR WINDOW OUTLIVES A READ.

#112 and #83 (Reviewer D, GrokBot #230), measured at v3784 (7285e7efc):
  - _read_rows backed the whole Chrome Cookies database up into a d2jsp-cookies-*.db file in $TMPDIR
    and removed it only in a finally, so a console killed mid-read left every site's encrypted
    cookies on disk (on Linux, under Chrome's published fallback key). The sweep's prefixes did not
    name that file, and its rmtree(ignore_errors=True) cannot remove a file but counted it anyway.
  - pgrep read the sweep's `--user-data-dir=...` pattern as an option of its own and listed nothing,
    so REG-2190's sweep never killed a stale scratch Chrome.
  - a price read that came back need-login opened the forum login in his Chrome, with no click, and
    Chrome came to the front over the console ("That frame shows Chrome's forums.d2jsp.org page
    covering the whole console", v3707).
  - nothing ended a scratch Chrome the console still had in flight when it exited.

Every file this law plants is under its own mkdtemp, found by its exact path; it lists no folder.
  - a cookie read leaves its temp dir untouched (the folder's mtime does not move), and reads the rows.
  - a planted stale d2jsp-cookies-*.db is removed and counted; a fresh one and another name stay; one
    that cannot be removed stays and is not counted.
  - a stale profile's holder (a harmless sleeper carrying its --user-data-dir) is killed, and one
    whose profile path only starts with it is not.
  - the room's login check sweeps; a need-login price read opens nothing, while the lamp and a Post
    click still open the login.
  - a child python that exits with a scratch Chrome in flight ends it and removes its profile.
RED_PROOF below.
"""
from __future__ import annotations

import contextlib
import os
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402  #171 - this run's scratch dirs leave with it
_fx_tmp.contain()
from console_safe import enable  # noqa: E402
enable()

import d2jsp_chrome as desk  # noqa: E402

PAST = 1000000000           # 2001-09-09: a folder's mtime pinned here moves the moment anything is made in it
OLD = 3600                  # a planted leftover is an hour old: past the sweep's stale bound

CHILD = r'''
import os, subprocess, sys
sys.path.insert(0, sys.argv[1])
import d2jsp_chrome as desk
profile, token = sys.argv[2], sys.argv[3]
os.mkdir(profile)
# its own session, and none of this child's pipes: a helper left running must not hold the law's
helper = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)", token],
                          stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                          start_new_session=True)
desk._track_scratch(helper, profile)
print(helper.pid, flush=True)
'''


def _command_of(pid):
    """The command line of pid: '' when there is no such process, None when ps could not be asked.

    REG-2498: a ps that could not run (or gave no answer in 10 s) read '' as well, which says the
    process is gone, so the in-flight case passed without asking anything."""
    try:
        return subprocess.run(["ps", "-p", str(int(pid)), "-o", "command="], capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=10).stdout.strip()
    except Exception:
        return None


class NoCookieCopyOrWindowOutlivesARead(unittest.TestCase):

    def scratch(self, prefix="d2jsp-law-"):
        path = tempfile.mkdtemp(prefix=prefix)
        self.addCleanup(shutil.rmtree, path, True)
        return path

    def patch(self, obj, name, value):
        old = getattr(obj, name)
        setattr(obj, name, value)
        self.addCleanup(setattr, obj, name, old)

    @contextlib.contextmanager
    def temp_root(self, path):
        """tempfile's default folder is `path` for the block."""
        old = tempfile.tempdir
        tempfile.tempdir = path
        try:
            yield path
        finally:
            tempfile.tempdir = old

    def plant(self, folder, name, age=OLD):
        path = os.path.join(folder, name)
        with open(path, "wb") as fh:
            fh.write(b"SQLite format 3\x00 every site's encrypted cookies")
        stamp = time.time() - age
        os.utime(path, (stamp, stamp))
        return path

    def test_a_cookie_read_writes_no_copy_to_disk(self):
        profile = self.scratch("d2jsp cookie law ")
        db = os.path.join(profile, "Cookies")
        con = sqlite3.connect(db)
        try:
            con.execute("create table cookies (host_key text, name text, encrypted_value blob, expires_utc integer)")
            con.execute("insert into cookies values (?,?,?,?)", (".d2jsp.org", "sid", b"v10sealed", 0))
            con.execute("insert into cookies values (?,?,?,?)", ("example.com", "other", b"v10sealed", 0))
            con.commit()
        finally:
            con.close()
        probe = self.scratch()
        os.utime(probe, (PAST, PAST))
        with self.temp_root(probe):
            handle, made = tempfile.mkstemp(prefix="d2jsp-cookies-", suffix=".db")
            os.close(handle)
            os.remove(made)
        self.assertNotEqual(int(os.stat(probe).st_mtime), PAST,
                            "premise: a file made and removed in a folder left its mtime alone - this "
                            "instrument cannot see a copy, so its silence below would mean nothing")
        watched = self.scratch()
        os.utime(watched, (PAST, PAST))
        with self.temp_root(watched):
            rows = desk._read_rows(db)
        self.assertEqual(sorted(r[0] for r in rows), [".d2jsp.org", "example.com"])
        self.assertEqual(int(os.stat(watched).st_mtime), PAST,
                         "a cookie read wrote into the temp dir: a copy of his whole cookie database "
                         "touched the disk")

    def test_a_stale_cookie_copy_is_removed_and_counted(self):
        root = self.scratch()
        stale = self.plant(root, "d2jsp-cookies-k3j2x9.db")
        journal = self.plant(root, "d2jsp-cookies-k3j2x9.db-journal")
        fresh = self.plant(root, "d2jsp-cookies-inflight.db", age=0)
        other = self.plant(root, "other-cookies.db")
        gone = desk._sweep_stale_scratch(now=time.time(), tmp=root)
        self.assertFalse(os.path.exists(stale), "a stale copy of his cookie database was left in the temp dir")
        self.assertFalse(os.path.exists(journal))
        self.assertTrue(os.path.exists(fresh), "a copy seconds old was swept")
        self.assertTrue(os.path.exists(other), "a file that is not a d2jsp cookie copy was swept")
        self.assertEqual(gone, 2)

    def test_a_copy_that_cannot_be_removed_is_not_counted(self):
        if os.name == "nt":
            self.skipTest("a read-only folder still lets Windows remove a file in it")
        locked = self.scratch()
        stuck = self.plant(locked, "d2jsp-cookies-stuck.db")
        os.chmod(locked, 0o500)
        self.addCleanup(os.chmod, locked, 0o700)
        try:
            with open(os.path.join(locked, "probe"), "w"):
                pass
            self.skipTest("this account writes into a read-only folder (root?), so no removal can fail here")
        except PermissionError:
            pass
        gone = desk._sweep_stale_scratch(now=time.time(), tmp=locked)
        self.assertTrue(os.path.exists(stuck))
        self.assertEqual(gone, 0, "the sweep counted a copy it could not remove")

    def test_a_stale_profile_holder_is_killed_and_a_longer_path_is_not(self):
        if os.name == "nt" or not shutil.which("pgrep"):
            self.skipTest("no pgrep here, and no scratch Chrome either (this console has no d2jsp reader)")
        root = self.scratch()
        profile = os.path.join(root, "d2jsp-post-k3j2x9")
        os.mkdir(profile)
        stamp = time.time() - OLD
        os.utime(profile, (stamp, stamp))
        quiet = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)
        holder = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)",
                                   "--user-data-dir=" + profile], **quiet)
        bystander = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)",
                                      "--user-data-dir=" + profile + "-longer"], **quiet)
        for proc in (holder, bystander):
            self.addCleanup(proc.wait)
            self.addCleanup(lambda p=proc: p.poll() is None and p.kill())
        deadline = time.time() + 20
        while time.time() < deadline and profile not in (_command_of(bystander.pid) or ""):
            time.sleep(0.1)
        held = _command_of(holder.pid)
        self.assertIsNotNone(held, "UNKNOWN, not a pass: ps could not be asked about the planted holder")
        self.assertIn(profile, held, "premise: the planted holder never showed its profile")
        gone = desk._sweep_stale_scratch(now=time.time(), tmp=root)
        try:
            code = holder.wait(timeout=10)
        except subprocess.TimeoutExpired:
            code = None
        self.assertEqual(code, -signal.SIGKILL, "the Chrome still holding a stale profile was left running")
        # a kill lands a moment after it is sent, so the bystander is given one second to die in
        try:
            bystander.wait(timeout=1.0)
            survived = False
        except subprocess.TimeoutExpired:
            survived = True
        self.assertTrue(survived, "a process whose profile only starts with the stale one was killed")
        self.assertFalse(os.path.exists(profile))
        self.assertEqual(gone, 1)

    def test_a_pgrep_that_cannot_run_is_unknown_not_no_holder(self):
        # REG-2498: a pgrep that could not be asked is None. [] would say no Chrome held the profile.
        def no_pgrep(*args, **kwargs):
            raise FileNotFoundError("pgrep")
        self.patch(desk.subprocess, "run", no_pgrep)
        self.assertIsNone(desk._kill_profile_holders(os.path.join(self.scratch(), "d2jsp-post-unasked")),
                          "a pgrep that never ran read as 'no Chrome held this profile'")

    def test_the_room_login_check_sweeps(self):
        root = self.scratch()
        left = self.plant(root, "d2jsp-cookies-left.db")
        self.patch(desk, "live_cookie_header", lambda now_utc=None: (None, "need-login"))
        with self.temp_root(root):
            out = desk.d2jsp_login_status()
        self.assertEqual(out["state"], "off")
        self.assertFalse(os.path.exists(left), "opening the room did not sweep the cookie copy a killed console left")

    def test_a_need_login_price_read_opens_nothing(self):
        opened = []

        def door(*args, **kwargs):
            opened.append(1)
            return True
        self.patch(desk, "_open_chrome_login", door)
        code, out = desk.d2jsp_quote("Grief", "http://127.0.0.1:17772", "127.0.0.1:17772", 17772,
                                     cookie_get=lambda: (None, "need-login"))
        self.assertEqual(out["reason"], "need-login")
        self.assertIs(desk.open_quote_login_once(), False)
        self.assertIs(desk.open_quote_login_once(), False)
        self.assertEqual(opened, [], "a price read opened the forum login in his Chrome, over the console")
        # the doors that stay: the lamp click, and a Post click
        self.assertTrue(desk.open_d2jsp_login()["opened"])
        desk._SENT.clear()
        self.addCleanup(desk._SENT.clear)
        code, sent = desk.d2jsp_send({"subject": "Selling Grief", "body": "Selling Grief\n30 fg", "forum": 268},
                                     "http://127.0.0.1:17772", "127.0.0.1:17772", 17772,
                                     cookie_get=lambda: (None, "need-login"))
        self.assertEqual(sent["reason"], "need-login")
        self.assertTrue(sent["opened"])
        self.assertEqual(len(opened), 2)

    def test_a_scratch_chrome_in_flight_at_exit_is_ended(self):
        if os.name == "nt":
            self.skipTest("no scratch Chrome on a Windows console (it has no d2jsp reader)")
        root = self.scratch()
        profile = os.path.join(root, "d2jsp-post-inflight")
        token = "d2jsp-law-inflight-" + uuid.uuid4().hex
        run = subprocess.run([sys.executable, "-c", CHILD, HERE, profile, token], capture_output=True,
                             text=True, encoding="utf-8", errors="replace", timeout=60)
        self.assertEqual(run.returncode, 0, "the child did not run - UNKNOWN, not a pass: " + run.stderr[-800:])
        pid = int(run.stdout.split()[0])

        def end_it():
            if token in (_command_of(pid) or ""):
                try:
                    os.killpg(pid, signal.SIGKILL)
                except OSError:
                    pass
        self.addCleanup(end_it)
        self.assertFalse(os.path.exists(profile), "a scratch profile in flight at exit was left on disk")
        left = _command_of(pid)
        self.assertIsNotNone(left, "UNKNOWN, not a pass: ps could not be asked whether the scratch Chrome is gone")
        self.assertNotIn(token, left, "a scratch Chrome in flight at exit was left running")


RED_PROOF = [
    {
        "why": "REG-2492 - the cookie database is backed up into a d2jsp-cookies-*.db file in $TMPDIR again",
        "file": "tv/d2jsp_chrome.py",
        "find": '        dst = sqlite3.connect(":memory:")\n',
        "replace": '        _copy = tempfile.NamedTemporaryFile(prefix="d2jsp-cookies-", suffix=".db", delete=False)\n'
                   "        _copy.close()\n"
                   "        dst = sqlite3.connect(_copy.name)\n",
        "matches": 1,
    },
    {
        "why": "REG-2491 - a need-login price read opens the forum login in his Chrome again, over the "
               "console, with no click",
        "file": "tv/d2jsp_chrome.py",
        "find": '    Chrome login on this machine.\n    """\n    return False\n',
        "replace": '    Chrome login on this machine.\n    """\n    return bool(_open_chrome_login())\n',
        "matches": 1,
    },
    {
        "why": "REG-2492 - the sweep goes back to rmtree for a cookie copy, which cannot remove a file",
        "file": "tv/d2jsp_chrome.py",
        "find": "        try:\n            os.remove(f)\n        except OSError:\n            pass\n",
        "replace": "        shutil.rmtree(f, ignore_errors=True)\n",
        "matches": 1,
    },
    {
        "why": "REG-2492 - the sweep counts the copies it tried, not the ones that are gone",
        "file": "tv/d2jsp_chrome.py",
        "find": "        if not os.path.lexists(f):\n            removed += 1\n",
        "replace": "        removed += 1\n",
        "matches": 1,
    },
    {
        "why": "REG-2492 - the sweep stops naming the cookie copies, so a killed console's copy stays",
        "file": "tv/d2jsp_chrome.py",
        "find": '_COOKIE_COPY_PREFIX = "d2jsp-cookies-"\n',
        "replace": '_COOKIE_COPY_PREFIX = "d2jsp-cookie-copy-"\n',
        "matches": 1,
    },
    {
        "why": "REG-2493 - pgrep reads the --user-data-dir pattern as an option again, so a stale Chrome "
               "holding his session is never killed",
        "file": "tv/d2jsp_chrome.py",
        "find": '["pgrep", "-f", "--", "--user-data-dir="',
        "replace": '["pgrep", "-f", "--user-data-dir="',
        "matches": 1,
    },
    {
        "why": "REG-2493 - the pattern stops at no boundary, so a live profile whose path starts with a "
               "stale one is killed with it",
        "file": "tv/d2jsp_chrome.py",
        "find": ' + _ere(profile) + "( |$)"]',
        "replace": " + _ere(profile)]",
        "matches": 1,
    },
    {
        "why": "REG-2492 - the room's login check no longer sweeps",
        "file": "tv/d2jsp_chrome.py",
        "find": "    try:\n        _sweep_stale_scratch()\n    except Exception:\n        pass\n"
                "    said = []\n",
        "replace": "    said = []\n",
        "matches": 1,
    },
    {
        "why": "REG-2492 - nothing ends a scratch Chrome still in flight when the console exits",
        "file": "tv/d2jsp_chrome.py",
        "find": "atexit.register(_reap_in_flight)\n",
        "replace": "_ = _reap_in_flight\n",
        "matches": 1,
    },
    {
        "why": "REG-2498 - a pgrep that could not be asked reads as 'no Chrome held this profile' again",
        "file": "tv/d2jsp_chrome.py",
        "find": "    except Exception:\n        return None\n    hit = []\n",
        "replace": "    except Exception:\n        return []\n    hit = []\n",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
