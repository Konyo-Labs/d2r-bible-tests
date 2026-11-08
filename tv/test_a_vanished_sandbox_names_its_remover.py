# -*- coding: utf-8 -*-
"""REG-2612 (#71) - WHEN A SANDBOX FILE VANISHES, THE SANDBOX SAYS WHAT IT SAW, AND EVERY SWEEP LEAVES A LINE.

#144 recurred on the Linux box (2026-10-23 01:11-02:21 IDT stage run, lane 4): every root .md/.html/.json and 13 tv
files went in one gate, while a gate that touches no files was running, and the sandbox it left had lost its owner
file. That box has no dirhelper, cron or tmpreaper, so REG-2438's macOS atime theory is not the whole cause. The pattern
is a whole-sandbox rmtree's, and nothing recorded who ran one.

  · DRIVEN: the stale sweep writes a journal line (sweeper pid, sandbox, owner, why) in the temp dir before it removes,
    and a run that drops its own sandbox writes one too, so the two can be told apart.
  · DRIVEN: every new sandbox writes a birth line; a vanish reports whether the owner file and the root survive, the
    birth (never an mtime any unlink moves), and every journal line naming exactly this sandbox. It never raises.
  · DRIVEN: a vanish with the owner file in place and no journal line says so, rather than guessing a remover.
RED_PROOF below. [[unknown-stays-unknown]]
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

import heart2 as H  # noqa: E402

GATE = (
    "import os, sys\n"
    "here = os.path.dirname(os.path.abspath(__file__))\n"
    "os.remove(os.path.join(here, 'victim.py'))\n"
    "if os.environ.get('ALSO_OWNER') == '1':\n"
    "    os.remove(os.path.join(os.path.dirname(os.path.dirname(here)), '.heart2-owner'))\n"
    "print('OK')\n"
)


class AVanishedSandboxNamesItsRemover(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="h2witness_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.real = os.path.join(self.tmp, "real")
        self.box = os.path.join(self.tmp, "heart2.wit0001")
        self.sb = os.path.join(self.box, "repo", "tv")
        for d in (os.path.join(self.real, "tv"), self.sb):
            os.makedirs(d)
            with io.open(os.path.join(d, "victim.py"), "w") as fh:
                fh.write("X = 1\n")
        with io.open(os.path.join(self.sb, "test_zz_gone.py"), "w") as fh:
            fh.write(GATE)
        with io.open(os.path.join(self.box, H._SANDBOX_OWNER), "w") as fh:
            fh.write(str(os.getpid()))
        p = mock.patch.object(H, "REPO", self.real)
        p.start()
        self.addCleanup(p.stop)
        del H._VANISHED[:]
        self.addCleanup(lambda: H._VANISHED.__delitem__(slice(None)))
        self.addCleanup(os.environ.pop, "ALSO_OWNER", None)

    def _journal(self):
        path = os.path.join(self.tmp, H._SWEEP_JOURNAL)
        if not os.path.exists(path):
            return ""                                   # nothing written yet - a read error still raises
        with io.open(path) as fh:
            return fh.read()

    def test_a_sweep_writes_who_removed_which_sandbox_and_why(self):
        old = os.path.join(self.tmp, "heart2.old0002")
        os.makedirs(os.path.join(old, "repo"))
        then = time.time() - H.SANDBOX_STALE_S - 3600
        os.utime(old, (then, then))
        gone = H.sweep_stale_sandboxes(tmp=self.tmp)
        self.assertIn(old, [p for p, _w in gone], "PREMISE: the stale sandbox was not swept")
        j = self._journal()
        self.assertIn("\tswept\tpid=%d\theart2.old0002\t" % os.getpid(), j,
                      "a sweep removed a sandbox and did not write down which process removed which sandbox")
        self.assertIn("\tstale-24h\n", j, "the journal does not say why")
        self.assertNotIn("heart2.wit0001", j, "a live sandbox was journaled as swept")

    def test_the_sweep_line_is_written_before_the_remove(self):
        old = os.path.join(self.tmp, "heart2.old0003")
        os.makedirs(old)
        then = time.time() - H.SANDBOX_STALE_S - 3600
        os.utime(old, (then, then))
        seen = []

        def _boom(path):
            seen.append(self._journal())
            raise RuntimeError("rmtree stopped here")
        with mock.patch.object(H, "_rmtree_hard", _boom):
            with self.assertRaises(RuntimeError):
                H.sweep_stale_sandboxes(tmp=self.tmp)
        self.assertTrue(seen, "PREMISE: the sweep never reached its remove")
        self.assertIn("\theart2.old0003\t", seen[0], "the remove ran before its journal line was written")

    def test_a_raw_owner_file_never_reaches_the_journal(self):
        old = os.path.join(self.tmp, "heart2.old0004")
        os.makedirs(old)
        with io.open(os.path.join(old, H._SANDBOX_OWNER), "w") as fh:
            fh.write("Ran 3 tests skipped=3")
        then = time.time() - H.SANDBOX_STALE_S - 3600
        os.utime(old, (then, then))
        H.sweep_stale_sandboxes(tmp=self.tmp)
        j = self._journal()
        self.assertIn("\theart2.old0004\towner=?\t", j, "PREMISE: no line for the swept sandbox")
        self.assertNotIn("skipped=", j, "an owner file's raw text reached the journal the gate tail is built from")

    def test_the_journal_is_private(self):
        H._sweep_journal(self.tmp, "created", self.box, "new", "1", time.time())
        if os.name != "nt":
            mode = os.stat(os.path.join(self.tmp, H._SWEEP_JOURNAL)).st_mode & 0o777
            self.assertEqual(mode & 0o077, 0, "the journal is readable by other users (mode %o)" % mode)

    def test_a_run_that_drops_its_own_sandbox_says_so_too(self):
        H._drop_sandbox(self.box)
        self.assertFalse(os.path.exists(self.box), "PREMISE: the drop did not remove the sandbox")
        j = self._journal()
        self.assertIn("\tdropped\tpid=%d\theart2.wit0001\t" % os.getpid(), j,
                      "a run's own cleanup is not told apart from a sibling's sweep")

    def test_a_drop_writes_its_line_before_the_remove(self):
        seen = []

        def _boom(path):
            seen.append(self._journal())
            raise RuntimeError("rmtree stopped here")
        with mock.patch.object(H, "_rmtree_hard", _boom):
            with self.assertRaises(RuntimeError):
                H._drop_sandbox(self.box)
        self.assertIn("\tdropped\tpid=%d\theart2.wit0001\t" % os.getpid(), seen[0],
                      "the run's own remove ran before its journal line was written")

    def test_a_capped_journal_keeps_its_newest_lines_and_stays_private(self):
        # review r3: a keep size off the line length, so the kept window starts mid-line and the torn-line strip
        # is what keeps every line whole
        with mock.patch.object(H, "_JOURNAL_CAP", 400), mock.patch.object(H, "_JOURNAL_KEEP", 201):
            for i in range(40):
                H._sweep_journal(self.tmp, "created", os.path.join(self.tmp, "heart2.cap%04d" % i), "new", "1", 1)
        path = os.path.join(self.tmp, H._SWEEP_JOURNAL)
        j = self._journal()
        self.assertLessEqual(os.path.getsize(path), 400, "the journal grew past its cap")
        self.assertIn("\theart2.cap0039\t", j, "the cap dropped the newest line")
        self.assertIn("\theart2.cap0038\t", j, "the cap kept only the last line")
        self.assertNotIn("\theart2.cap0000\t", j, "PREMISE: the cap never ran")
        self.assertTrue(all(len(ln.split("\t")) == 6 for ln in j.splitlines()), "the cap left a torn line: %r" % j)
        if os.name != "nt":
            self.assertEqual(os.stat(path).st_mode & 0o077, 0, "the capped journal is readable by other users")

    def test_the_cap_never_shows_a_reader_an_empty_journal(self):
        # review r3: truncating BEFORE the kept tail was written left a window where the journal read empty
        path = os.path.join(self.tmp, H._SWEEP_JOURNAL)
        seen = []
        real = os.ftruncate

        def _peek(fd, n):
            out = real(fd, n)
            with io.open(path, "rb") as fh:            # what a reader sees the moment the cut lands
                seen.append(fh.read())
            return out
        for i in range(12):
            H._sweep_journal(self.tmp, "created", os.path.join(self.tmp, "heart2.cap%04d" % i), "new", "1", 1)
        with mock.patch.object(H, "_JOURNAL_CAP", 400), mock.patch.object(H, "_JOURNAL_KEEP", 201):
            with mock.patch.object(H.os, "ftruncate", _peek):
                H._sweep_journal(self.tmp, "swept", self.box, "owner-dead", "1", 2)
        self.assertTrue(seen, "PREMISE: the cap never ran")
        for snap in seen:
            self.assertIn(b"\tswept\tpid=", snap, "a reader during the cap saw no line for the sweep just made")

    def test_a_short_write_is_finished_not_lost(self):
        real = os.write
        with mock.patch.object(H.os, "write", lambda fd, b: real(fd, bytes(b[:7]))):
            H._sweep_journal(self.tmp, "swept", self.box, "owner-dead", "77", 5)
        self.assertEqual(H._journal_lines_for(self.tmp, "heart2.wit0001"),
                         [(5, "swept", os.getpid(), "77", "owner-dead")])

    def test_windows_writers_take_turns_on_a_byte_no_reader_reads(self):
        calls = []
        fake = mock.Mock(LK_NBLCK=2, LK_UNLCK=0)
        fake.locking.side_effect = lambda fd, mode, n: calls.append((os.lseek(fd, 0, os.SEEK_CUR), mode, n))
        with mock.patch.dict(sys.modules, {"fcntl": None, "msvcrt": fake}):
            H._sweep_journal(self.tmp, "swept", self.box, "owner-dead", "77", 5)
        self.assertEqual(calls, [(H._JOURNAL_LOCK_AT, 2, 1), (H._JOURNAL_LOCK_AT, 0, 1)])
        self.assertGreater(H._JOURNAL_LOCK_AT, H._JOURNAL_CAP * 4)
        self.assertEqual(len(H._journal_lines_for(self.tmp, "heart2.wit0001")), 1, "the line went to the lock byte")

    def test_a_windows_lock_not_had_appends_but_never_cuts(self):
        # review r4: LK_LOCK gave up after ~10 s and the writer then capped unlocked, beside a holder
        path = os.path.join(self.tmp, H._SWEEP_JOURNAL)
        with io.open(path, "wb") as fh:
            fh.write(b"x" * (H._JOURNAL_CAP + 10) + b"\n")
        fake = mock.Mock(LK_NBLCK=2, LK_UNLCK=0)
        fake.locking.side_effect = OSError("held by another writer")
        err = io.StringIO()
        with mock.patch.dict(sys.modules, {"fcntl": None, "msvcrt": fake}), \
                mock.patch.object(H, "_JOURNAL_LOCK_WAIT_S", 0.0), mock.patch.object(H.sys, "stderr", err):
            H._sweep_journal(self.tmp, "swept", self.box, "owner-dead", "77", 5)
        self.assertGreater(os.path.getsize(path), H._JOURNAL_CAP, "a writer without the lock cut the journal")
        self.assertEqual(H._journal_lines_for(self.tmp, "heart2.wit0001"),
                         [(5, "swept", os.getpid(), "77", "owner-dead")], "the line was lost with the lock")
        self.assertIn("lock was not had", err.getvalue(), "a lockless write was not said")

    def test_a_windows_lock_is_polled_not_given_up_on(self):
        tries = []

        def _busy_twice(fd, mode, n):
            tries.append(mode)
            if mode == 2 and len(tries) <= 2:
                raise OSError("busy")
        fake = mock.Mock(LK_NBLCK=2, LK_UNLCK=0)
        fake.locking.side_effect = _busy_twice
        with mock.patch.dict(sys.modules, {"fcntl": None, "msvcrt": fake}), mock.patch.object(H.time, "sleep"):
            H._sweep_journal(self.tmp, "swept", self.box, "owner-dead", "77", 5)
        self.assertEqual(tries, [2, 2, 2, 0], "the lock was not polled until free, then released")

    def test_an_owner_files_text_never_reaches_the_gate_tail(self):
        # review r3: the text is IN the owner file the gate's sandbox carries, and the sweep line was written
        # from it, so both ways in are driven
        with io.open(os.path.join(self.box, H._SANDBOX_OWNER), "w") as fh:
            fh.write("Ran 1 test skipped=9")
        H._sweep_journal(self.tmp, "swept", self.box, "owner-dead", "Ran 1 test skipped=9", time.time())
        ok, tail = H._run_gate(self.sb, "test_zz_gone.py", timeout=60)
        self.assertIn("removal: swept by pid", tail, "PREMISE: the witness did not read the line")
        self.assertNotIn("skipped=", tail, "an owner file's text reached the tail heart2 scans for skipped=")
        self.assertFalse(H._skipped_every_law(tail), "an owner file's text made the gate read as all-skipped")

    def test_a_tracked_sandbox_writes_its_birth(self):
        box = os.path.join(self.tmp, "heart2.new0005")
        os.makedirs(box)
        H._track_sandbox(box)
        self.addCleanup(H._SANDBOXES.discard, box)
        self.assertIn("\tcreated\tpid=%d\theart2.new0005\t" % os.getpid(), self._journal(),
                      "a new sandbox left no birth line, so its age is read off an mtime any unlink moves")

    def test_a_vanish_after_a_sweep_says_the_owner_file_went_and_names_the_sweep(self):
        with io.open(os.path.join(self.tmp, H._SWEEP_JOURNAL), "w") as fh:
            fh.write("%d\tcreated\tpid=77\theart2.wit0001\towner=77\tnew\n" % (int(time.time()) - 600))
            fh.write("1\tswept\tpid=4242\theart2.wit0001\towner=77\towner-dead\n")
        os.environ["ALSO_OWNER"] = "1"
        ok, tail = H._run_gate(self.sb, "test_zz_gone.py", timeout=60)
        self.assertIs(ok, True, tail)
        self.assertIn("owner file GONE", tail)
        self.assertIn("swept by pid 4242 (its owner pid was dead, owner 77)", tail,
                      "the vanish does not name the sweep that removed its sandbox")
        self.assertRegex(tail, r"created (59\d|60\d)s ago by pid 77", "the sandbox's age is not read from its birth line")

    def test_a_vanish_with_the_owner_gone_and_no_line_says_so(self):
        os.environ["ALSO_OWNER"] = "1"                 # the 2026-10-23 leftover: owner gone, nothing on record
        ok, tail = H._run_gate(self.sb, "test_zz_gone.py", timeout=60)
        self.assertIs(ok, True, tail)
        self.assertIn("owner file GONE", tail)
        self.assertIn("no created line", tail)
        self.assertIn("no sweep journal line names it", tail, "a remover was invented for a vanish nothing recorded")

    def test_a_vanish_with_no_remover_on_record_says_so(self):
        with io.open(os.path.join(self.tmp, H._SWEEP_JOURNAL), "w") as fh:     # a SIBLING's sweep is not this one's
            fh.write("1\tswept\tpid=4242\theart2.wit00012\towner=77\towner-dead\n")
        ok, tail = H._run_gate(self.sb, "test_zz_gone.py", timeout=60)
        self.assertIs(ok, True, tail)
        self.assertIn("owner file present", tail)
        self.assertIn("sandbox root present", tail)
        self.assertIn("no sweep journal line names it", tail, "a sibling sandbox's sweep was pinned on this one")

    def test_a_root_gone_before_the_restore_is_said_gone(self):
        seen = {}
        real_once = H._run_gate_once

        def _once(*a, **k):
            r = real_once(*a, **k)
            if not seen:
                seen["x"] = 1
                shutil.rmtree(self.box)            # the whole sandbox went while the gate ran
            return r
        with mock.patch.object(H, "_run_gate_once", _once):
            ok, tail = H._run_gate(self.sb, "test_zz_gone.py", timeout=60)
        self.assertIn("sandbox root GONE", tail, "the restore rebuilt the root before the witness looked")

    def test_an_unreadable_journal_never_skips_the_restore(self):
        with io.open(os.path.join(self.tmp, H._SWEEP_JOURNAL), "wb") as fh:
            fh.write(b"\xff\xfe\x00garbage\n")
        with mock.patch.object(H, "_journal_lines_for", mock.Mock(side_effect=MemoryError())):
            ok, tail = H._run_gate(self.sb, "test_zz_gone.py", timeout=60)
        self.assertIs(ok, True, tail)
        self.assertIn("witness unreadable (MemoryError)", tail)
        self.assertTrue(os.path.isfile(os.path.join(self.sb, "victim.py")),
                        "a witness that raised skipped the restore - the vanished file stayed gone")


RED_PROOF = [
    {"why": "REG-2612 - the sweep removes a sandbox without writing it down",
     "file": "heart2.py",
     "find": "        _sweep_journal(tmp, \"swept\", root,",
     "replace": "        (lambda *a: None)(tmp, \"swept\", root,",
     "matches": 1},
    {"why": "REG-2612 - the witness reads the owner file in the wrong place, so a swept sandbox looks owned",
     "file": "heart2.py",
     "find": "(\"present\" if os.path.isfile(os.path.join(base, _SANDBOX_OWNER)) else \"GONE\")",
     "replace": "(\"present\" if True else \"GONE\")",
     "matches": 1},
    {"why": "REG-2612 - a run's own cleanup leaves no line, so it cannot be told apart from a sibling's sweep",
     "file": "heart2.py",
     "find": "    _sweep_journal(os.path.dirname(root), \"dropped\"",
     "replace": "    (lambda *a: None)(os.path.dirname(root), \"dropped\"",
     "matches": 1},
    {"why": "REG-2612 - the vanish note drops the witness",
     "file": "heart2.py",
     "find": "    note = note[:-1] + \" - \" + _witness + \"]\"\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-2612 - the journal line is matched loosely, so a sibling sandbox's sweep is pinned on this one",
     "file": "heart2.py",
     "find": "if len(f) != 6 or f[3] != name or",
     "replace": "if len(f) != 6 or",
     "matches": 1},
    {"why": "REG-2612 - review r1: the remove runs before its journal line",
     "file": "heart2.py",
     "find": "        _sweep_journal(tmp, \"swept\", root, \"owner-dead\" if age < SANDBOX_STALE_S else \"stale-24h\", owner, now)  # REG-2612\n        #           ^ written BEFORE the remove, so a half-done one shows\n        if _rmtree_hard(root):",
     "replace": "        _ok = _rmtree_hard(root)\n        _sweep_journal(tmp, \"swept\", root, \"owner-dead\" if age < SANDBOX_STALE_S else \"stale-24h\", owner, now)\n        if _ok:",
     "matches": 1},
    {"why": "REG-2612 - review r1: a raw owner file is copied into the journal",
     "file": "heart2.py",
     "find": "own if own.isdigit() else (\"?\" if own else \"-\")",
     "replace": "own or \"-\"",
     "matches": 1},
    {"why": "REG-2612 - review r1: the journal is created world-readable",
     "file": "heart2.py",
     "find": "os.O_RDWR | os.O_CREAT | getattr(os, \"O_BINARY\", 0), 0o600)",   # v3886 (#107) O_BINARY
     "replace": "os.O_RDWR | os.O_CREAT | getattr(os, \"O_BINARY\", 0), 0o666)",
     "matches": 1},
    {"why": "REG-2612 - review r1: a new sandbox writes no birth line",
     "file": "heart2.py",
     "find": "    _sweep_journal(os.path.dirname(root), \"created\", root,",
     "replace": "    (lambda *a: None)(os.path.dirname(root), \"created\", root,",
     "matches": 1},
    {"why": "REG-2612 - review r1: the witness reads after the restore, which rebuilt the root",
     "file": "heart2.py",
     "find": "    _witness = _vanish_witness(_sb_root)     # REG-2612 (#71) - read BEFORE the restore touches it; never raises\n    for n in gone:\n",
     "replace": "    for n in gone:\n        _witness = _vanish_witness(_sb_root)\n",
     "matches": 1},
    {"why": "REG-2612 - review r1: a witness that raises skips the restore",
     "file": "heart2.py",
     "find": "    except Exception as e:\n        return \"witness unreadable (%s)\" % type(e).__name__\n",
     "replace": "    except OSError as e:\n        return \"witness unreadable (%s)\" % type(e).__name__\n",
     "matches": 1},
    {"why": "REG-2612 - review r2: the run's own drop removes before its journal line",
     "file": "heart2.py",
     "find": "    _sweep_journal(os.path.dirname(root), \"dropped\", root, \"own-drop\", str(os.getpid()), time.time())   # REG-2612\n    if not _rmtree_hard(root):",
     "replace": "    _gone = _rmtree_hard(root)\n    _sweep_journal(os.path.dirname(root), \"dropped\", root, \"own-drop\", str(os.getpid()), time.time())\n    if not _gone:",
     "matches": 1},
    {"why": "REG-2612 - review r2: the journal is never capped",
     "file": "heart2.py",
     "find": "                if held and os.fstat(fd).st_size > _JOURNAL_CAP:\n",
     "replace": "                if False:\n",
     "matches": 1},
    {"why": "REG-2612 - review r2: the cap keeps a torn first line",
     "file": "heart2.py",
     "find": "                    keep = keep[keep.find(b\"\\n\") + 1:]\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-2612 - review r3: the journal opened O_APPEND, so the cap's offset-0 write lands at the end",
     "file": "heart2.py",
     "find": "os.O_RDWR | os.O_CREAT | getattr(os, \"O_BINARY\", 0), 0o600)",   # v3886 (#107) O_BINARY
     "replace": "os.O_RDWR | os.O_APPEND | os.O_CREAT | getattr(os, \"O_BINARY\", 0), 0o600)",
     "matches": 1},
    {"why": "REG-2612 - review r3: the file is cut before the kept tail is written, so a reader can see it empty",
     "file": "heart2.py",
     "find": "                    os.lseek(fd, 0, os.SEEK_SET)\n                    _write_all(fd, keep)\n                    os.ftruncate(fd, len(keep))\n",
     "replace": "                    os.ftruncate(fd, 0)\n                    os.lseek(fd, 0, os.SEEK_SET)\n                    _write_all(fd, keep)\n",
     "matches": 1},
    {"why": "REG-2612 - review r3: a short write is taken as the whole line",
     "file": "heart2.py",
     "find": "        view = view[n:]\n",
     "replace": "        view = view[len(view):]\n",
     "matches": 1},
    {"why": "REG-2612 - review r3: Windows writers never lock",
     "file": "heart2.py",
     "find": "            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)\n",
     "replace": "            pass\n",
     "matches": 1},
    {"why": "REG-2612 - review r3: Windows locks byte 0, which every reader reads",
     "file": "heart2.py",
     "find": "_JOURNAL_LOCK_AT = 0x7FFFFFF0",
     "replace": "_JOURNAL_LOCK_AT = 0",
     "matches": 1},
    {"why": "REG-2612 - review r4: a writer that never had the lock still caps, cutting beside a holder",
     "file": "heart2.py",
     "find": "                if held and os.fstat(fd).st_size > _JOURNAL_CAP:\n",
     "replace": "                if os.fstat(fd).st_size > _JOURNAL_CAP:\n",
     "matches": 1},
    {"why": "REG-2612 - review r4: the Windows lock is tried once and given up on",
     "file": "heart2.py",
     "find": "            if time.time() >= deadline:\n                return None\n",
     "replace": "            return None\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main()
