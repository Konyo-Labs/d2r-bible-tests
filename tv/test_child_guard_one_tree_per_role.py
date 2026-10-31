# -*- coding: utf-8 -*-
"""#83 (REG-1515) — THE CHILD SUPERVISOR: ONE TREE PER ROLE, VERIFIED, AND A REUSED PID IS NEVER OURS.

His words, 2026-09-29, after five capture_win.ps1 leaked at once and crashed his Boosteroid: *"have a logic coded
for this so it bypasses it - architecture something smart to make the ascending of the reel sessions smooth"*.

tv/child_guard.py is that architecture; every joint below is DRIVEN through the real code:
  · the door, on REAL processes (POSIX, this machine's own temp processes): a fake role that spawns a grandchild is
    started twice through spawn(); after the second start exactly one tree is alive - the first parent AND its
    grandchild are gone - and end() ends the survivor's tree too;
  · a pid the OS reused is never ours: a record whose creation time no longer matches is dropped, not killed, and an
    UNKNOWN birth ends nothing;
  · Windows: the Job Object is created with KILL_ON_JOB_CLOSE, the child is assigned to it, and end() terminates the
    job and closes the handle - driven with a fake kernel32 on this Mac; a failed assignment is said and falls back;
  · the watchdog ends the recorded children of dead parents (verified by birth) and the UNRECORDED processes of
    known roles whose parent is gone or ours; a stranger's child is counted, never ended; an unreadable table is
    UNKNOWN, ends nothing, and owes None - never 0;
  · the census by family and the doctor's one_of_each row (through the real control_app function);
  · the memory policy: under the floor no secondary worker, UNKNOWN free RAM never refuses;
  · the console: _start_capture through the door ends a capture the lamp lost track of (the five-captures shape,
    replayed through the real _start_capture/_stop_capture with the Windows edges stubbed - never a real process);
  · the agent: VisionWorker and OcrWorker spawn/stop through the door, the stall reader releases its claude after
    each sweep, and neither the stall drain nor OCR starts a worker under the RAM floor.
Fake pids are >= 9990001: past macOS's pid ceiling (99998) and Linux's default pid_max (4194304), and every OS
door (kill / alive / birth / kernel32) is stubbed, so no law here ever touches a real pid it did not start.
RED_PROOF below. [[feedback-fixtures-never-touch-live-data]] [[unknown-stays-unknown]] [[heart-first]]
"""
import ctypes
import inspect
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
import child_guard as cg  # noqa: E402
import control_app as ca  # noqa: E402

import lane_ports as _lane_ports  # noqa: E402  #144 — 17973 with no lane; a lane takes its own base
_lane_ports.adopt_agent(17973)            # never a live agent's port (test_agent holds 17971)
import tv_diablo as tv  # noqa: E402
tv.JOURNAL = os.path.join(tempfile.gettempdir(), "tvd_child_guard_law_journal.jsonl")   # never the real journal

IS_POSIX = sys.platform != "win32"


class _FakeProc(object):
    """A child that is alive while its pid is in `live`. Never a real process."""

    def __init__(self, pid, live, handle=None):
        self.pid, self._live, self._handle = pid, live, handle
        self.stdin = self.stdout = self.stderr = None
        self.killed = 0

    def poll(self):
        return None if self.pid in self._live else 1

    def kill(self):
        self.killed += 1
        self._live.discard(self.pid)

    def wait(self, timeout=None):
        return self.poll()


class _World(unittest.TestCase):
    """A private ledger dir, an empty door, every OS door stubbed to a recorder."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="child_guard_law_")
        self.live = set()
        self.births = {}
        self.killed = []
        self.saved = (cg.LEDGER_DIR, dict(cg._LIVE), dict(cg._EXPECT), dict(cg.RECEIPT), dict(cg.WATCHDOG),
                      dict(cg.RAM), cg._SELF_BIRTH, cg._ADOPTED[0])
        cg.LEDGER_DIR = os.path.join(self.d, "ledger")
        cg._LIVE.clear()
        cg._EXPECT.clear()
        cg.WATCHDOG.update(on=True, worked=None, lastTs=None, owed=None, ended=[], kept=[], failed=[], strangers=[],
                           bypass=[], unknown=None, say="the watchdog has not ticked yet")
        cg.RECEIPT.update(spawns=0, ends=0, survivors=0, survivorPids=[], reused=0, adopted=0, worked=None,
                          lastTs=None, owed=None)
        cg._SELF_BIRTH = 100
        cg._ADOPTED[0] = True            # REG-1551 - a law adopts only when it says so
        self.stack = [
            mock.patch.object(cg, "_alive_default", self.alive),
            mock.patch.object(cg, "_birth_default", self.birth),
            mock.patch.object(cg, "_kill_tree_default", self.kill_tree),
        ]
        for p in self.stack:
            p.start()

    def tearDown(self):
        for p in reversed(self.stack):
            p.stop()
        cg.LEDGER_DIR = self.saved[0]
        cg._LIVE.clear(); cg._LIVE.update(self.saved[1])
        cg._EXPECT.clear(); cg._EXPECT.update(self.saved[2])
        cg.RECEIPT.clear(); cg.RECEIPT.update(self.saved[3])
        cg.WATCHDOG.clear(); cg.WATCHDOG.update(self.saved[4])
        cg.RAM.clear(); cg.RAM.update(self.saved[5])
        cg._SELF_BIRTH = self.saved[6]
        cg._ADOPTED[0] = self.saved[7]
        shutil.rmtree(self.d, ignore_errors=True)

    def alive(self, pid):
        return pid in self.live

    def birth(self, pid):
        return self.births.get(pid)

    def kill_tree(self, rec):
        self.killed.append(rec.get("pid"))
        self.live.discard(rec.get("pid"))
        return "stub"

    def kill(self, pid):
        self.killed.append(pid)
        self.live.discard(pid)

    def popen(self, pids, handle=None):
        it = iter(pids)

        def _popen(argv, **kw):
            p = _FakeProc(next(it), self.live, handle=handle)
            self.live.add(p.pid)
            self.births[p.pid] = 1000
            self.spawned.append((p.pid, list(argv), dict(kw)))
            return p
        self.spawned = []
        return _popen


# ── 1. the door on real processes ────────────────────────────────────────────────────────────────────────────

FAKE_ROLE = r'''
import subprocess, sys, time
gc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
with open(sys.argv[1], "w") as fh:
    fh.write(str(gc.pid))
time.sleep(120)
'''


def _pid_alive_real(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _gone(pid, within_s=5.0):
    deadline = time.time() + within_s
    while time.time() < deadline:
        if not _pid_alive_real(pid):
            return True
        time.sleep(0.05)
    return not _pid_alive_real(pid)


@unittest.skipUnless(IS_POSIX, "the POSIX tree (own session + killpg) is proven where it runs; Windows has the job law")
class TheDoorLeavesOneTreePerRole(unittest.TestCase):
    """REAL processes of this law's own: a fake role that spawns a grandchild, started twice through the door."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="child_guard_tree_")
        self.saved = (cg.LEDGER_DIR, dict(cg._LIVE), dict(cg.RECEIPT), cg._SELF_BIRTH)
        cg.LEDGER_DIR = os.path.join(self.d, "ledger")
        cg._LIVE.clear()
        cg._SELF_BIRTH = None
        self.fake = os.path.join(self.d, "fake_role.py")
        with io.open(self.fake, "w", encoding="utf-8") as fh:
            fh.write(FAKE_ROLE)
        self.mine = []

    def tearDown(self):
        for pid in self.mine:                       # never leave a process of ours behind, whatever the verdict
            try:
                os.killpg(int(pid), 9)
            except Exception:
                pass
            try:
                os.kill(int(pid), 9)
            except Exception:
                pass
        cg._LIVE.clear(); cg._LIVE.update(self.saved[1])
        cg.RECEIPT.clear(); cg.RECEIPT.update(self.saved[2])
        cg.LEDGER_DIR, cg._SELF_BIRTH = self.saved[0], self.saved[3]
        shutil.rmtree(self.d, ignore_errors=True)

    def _tree(self, n):
        pf = os.path.join(self.d, "gc%d.pid" % n)
        p = cg.spawn("law-fake", [sys.executable, self.fake, pf], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.mine.append(p.pid)
        deadline = time.time() + 20
        while time.time() < deadline:
            try:
                with io.open(pf) as fh:
                    gc = int(fh.read().strip())
                break
            except Exception:
                time.sleep(0.05)
        else:
            self.fail("premise: the fake role never reported its grandchild")
        self.mine.append(gc)
        self.assertTrue(_pid_alive_real(gc), "premise: the grandchild is alive")
        return p, gc

    def test_a_restart_leaves_exactly_one_tree_and_end_ends_it(self):
        p1, g1 = self._tree(1)
        rec = cg.record_of("law-fake")
        self.assertEqual((p1.pid, os.getpid(), True), (rec["pid"], rec["parent"], rec["session"]),
                         "the record does not say whose child this is, or it does not lead its own session: %r" % rec)
        self.assertIsNotNone(rec["birth"], "the child's creation time was not read - a reused pid could never be told")
        p2, g2 = self._tree(2)
        self.assertTrue(_gone(p1.pid), "the first parent outlived the restart")
        self.assertTrue(_gone(g1), "THE GRANDCHILD SURVIVED THE RESTART - the tree was not ended, only its head; this "
                                   "is the leak that stacked five captures on the ALT")
        self.assertIsNone(p2.poll(), "the restarted role is not running")
        self.assertTrue(_pid_alive_real(g2), "the new tree's grandchild is not running")
        self.assertEqual(p2.pid, cg.record_of("law-fake")["pid"])
        self.assertEqual((2, 1), (cg.RECEIPT["spawns"], cg.RECEIPT["ends"]), "the receipt did not count the restart")
        with io.open(os.path.join(cg.LEDGER_DIR, "%d.json" % os.getpid())) as fh:
            ledger = json.load(fh)
        self.assertEqual(p2.pid, ledger["children"]["law-fake"]["pid"], "the ledger does not carry the live record")
        r = cg.end("law-fake")
        self.assertTrue(r["ended"], "end() did not see the tree go: %r" % r)
        self.assertTrue(_gone(p2.pid) and _gone(g2), "end() left part of the tree alive")
        self.assertIsNone(cg.record_of("law-fake"))
        with io.open(os.path.join(cg.LEDGER_DIR, "%d.json" % os.getpid())) as fh:
            self.assertNotIn("law-fake", json.load(fh)["children"], "the ledger still names an ended role")


# ── 2. a reused pid is never ours ────────────────────────────────────────────────────────────────────────────

class AReusedPidIsNeverOurs(_World):

    def _previous_life(self, pid=9990011, birth=1000):
        # a record with no Popen of ours (a previous console's, read back from a ledger)
        cg._LIVE["capture"] = {"role": "capture", "pid": pid, "birth": birth, "parent": 9990009, "parentBirth": 50,
                               "argv0": "powershell.exe", "ts": 1, "session": False, "job": None, "proc": None}
        self.live.add(pid)

    def test_a_pid_born_at_another_time_is_dropped_not_killed(self):
        self._previous_life()
        self.births[9990011] = 5000                  # alive, but born later: Windows handed the pid to a browser
        r = cg.end("capture", kill=self.kill)
        self.assertEqual([], self.killed, "A REUSED PID WAS KILLED - that process was never ours")
        self.assertIn("reused", r["say"])
        self.assertIsNone(cg.record_of("capture"), "the stranger's pid is still recorded as ours")
        self.assertEqual(1, cg.RECEIPT["reused"])

    def test_an_unknown_birth_ends_nothing(self):
        self._previous_life()
        self.births.pop(9990011, None)               # the reader could not answer
        r = cg.end("capture", kill=self.kill)
        self.assertEqual([], self.killed, "a pid whose birth could not be read was ended on a guess")
        self.assertIn("never ended on a guess", r["say"])

    def test_a_pid_born_when_recorded_is_ours_and_ended(self):
        self._previous_life()
        self.births[9990011] = 1001                  # one second off: `ps -o lstart` resolution
        r = cg.end("capture", kill=self.kill, wait_s=0.5)
        self.assertEqual([9990011], self.killed)
        self.assertTrue(r["ended"])

    def test_our_own_exited_child_is_forgotten_without_a_kill(self):
        cg.spawn("ocr", ["x"], popen=self.popen([9990021]), kill=self.kill)
        self.live.discard(9990021)                    # it exited by itself
        r = cg.end("ocr", kill=self.kill)
        self.assertEqual([], self.killed)
        self.assertIn("already exited", r["say"])
        self.assertIsNone(cg.record_of("ocr"))


class TheBirthReaderStartsNoProcess(unittest.TestCase):
    """2026-09-30 - reading a pid's birth must never START a process. Every console law stubs subprocess.Popen and
    counts its calls as capture spawns, so a `ps` inside the door's birth read is a phantom second capture. On Linux
    the reader fell through to `ps` for any pid /proc does not list - every fake pid a law hands the door - and
    test_one_capture_per_console + test_a_stub_agent_never_films_his_screen went red on CI only (his Mac reads birth
    through sysctl and starts nothing)."""

    def _count_popen(self):
        calls = []
        real = subprocess.Popen

        def popen(*a, **k):
            calls.append(a[0] if a else k.get("args"))
            return real(*a, **k)
        return calls, popen

    def test_linux_with_proc_reads_a_missing_pid_as_unknown_and_starts_nothing(self):
        calls, popen = self._count_popen()
        missing = "/proc/%d/stat" % 9990031

        def fake_open(path, *a, **k):
            if path == missing:
                raise FileNotFoundError(path)
            raise AssertionError("the reader opened %r" % (path,))
        with mock.patch.object(cg.sys, "platform", "linux"), \
                mock.patch.object(cg.os.path, "isdir", lambda d: d == "/proc"), \
                mock.patch.object(cg, "open", fake_open, create=True), \
                mock.patch.object(cg.subprocess, "Popen", popen):
            got = cg._birth_posix(9990031)
        self.assertIsNone(got, "a pid /proc does not list has no birth - UNKNOWN, never a guess")
        self.assertEqual([], calls, "the birth read STARTED a process %s - a console law counts it as a second "
                                    "capture" % calls)

    def test_linux_with_proc_reads_the_birth_from_proc(self):
        calls, popen = self._count_popen()
        files = {"/proc/9990032/stat": "9990032 (powershell) S " + " ".join(["0"] * 18) + " 4200 0 0\n",
                 "/proc/stat": "cpu  1 2 3\nbtime 1700000000\n"}

        def fake_open(path, *a, **k):
            if path in files:
                return io.StringIO(files[path])
            raise FileNotFoundError(path)
        with mock.patch.object(cg.sys, "platform", "linux"), \
                mock.patch.object(cg.os.path, "isdir", lambda d: d == "/proc"), \
                mock.patch.object(cg, "open", fake_open, create=True), \
                mock.patch.object(cg.os, "sysconf", lambda k: 100), \
                mock.patch.object(cg.subprocess, "Popen", popen):
            got = cg._birth_posix(9990032)
        self.assertEqual(1700000042, got, "starttime 4200 ticks at 100 Hz after btime 1700000000")
        self.assertEqual([], calls)

    def test_this_machines_reader_starts_nothing_for_a_pid_that_does_not_exist(self):
        calls, popen = self._count_popen()
        with mock.patch.object(cg.subprocess, "Popen", popen):
            got = cg._birth_default(99999999)
        self.assertIsNone(got)
        if sys.platform == "darwin" or os.path.isdir("/proc") or cg.IS_WIN:
            self.assertEqual([], calls, "this machine's birth reader started %s" % calls)


# ── 3. the Windows job object ────────────────────────────────────────────────────────────────────────────────

class _FakeKernel32(object):
    """Records every call the door makes; the structure handed to SetInformationJobObject is read back."""

    def __init__(self, assign_ok=True):
        self.calls = []
        self.assign_ok = assign_ok
        self.flags = None
        self.info_class = None
        self.info_size = None

    def CreateJobObjectW(self, a, b):
        self.calls.append(("CreateJobObjectW", a, b))
        return 77

    def SetInformationJobObject(self, job, cls, ref, size):
        obj = getattr(ref, "_obj", None)
        self.flags = obj.BasicLimitInformation.LimitFlags if obj is not None else None
        self.info_class, self.info_size = cls, size
        self.calls.append(("SetInformationJobObject", job, cls))
        return 1

    def AssignProcessToJobObject(self, job, handle):
        self.calls.append(("AssignProcessToJobObject", job, handle))
        return 1 if self.assign_ok else 0

    def TerminateJobObject(self, job, code):
        self.calls.append(("TerminateJobObject", job, code))
        return 1

    def CloseHandle(self, h):
        self.calls.append(("CloseHandle", h))
        return 1

    def GetLastError(self):
        return 5


class TheWindowsJobObject(_World):

    def _spawn(self, k32):
        with mock.patch.object(cg, "IS_WIN", True), mock.patch.object(cg, "_kernel32", lambda: k32):
            p = cg.spawn("capture", ["powershell.exe"], popen=self.popen([9990031], handle=4242), kill=self.kill)
            rec = cg.record_of("capture")
            return p, rec

    def test_the_child_is_put_in_a_job_that_kills_on_close(self):
        k32 = _FakeKernel32()
        p, rec = self._spawn(k32)
        self.assertEqual(cg.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE, k32.flags,
                         "the job was created WITHOUT JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE (flags %r) - a grandchild "
                         "would outlive the handle, and the console's death would end nothing" % (k32.flags,))
        self.assertEqual(cg.JobObjectExtendedLimitInformation, k32.info_class)
        # sizeof(JOBOBJECT_EXTENDED_LIMIT_INFORMATION): 144 on 64-bit Windows, 112 on 32-bit - the SDK's numbers
        self.assertEqual(144 if ctypes.sizeof(ctypes.c_void_p) == 8 else 112, k32.info_size,
                         "the extended limit structure is not laid out as Windows expects (size %r)" % k32.info_size)
        self.assertIn(("AssignProcessToJobObject", 77, 4242), k32.calls, "the child was never assigned to the job")
        self.assertIn("KILL_ON_JOB_CLOSE", rec["jobSay"])
        self.assertNotIn("start_new_session", self.spawned[0][2], "a Windows spawn was handed a POSIX-only kwarg")

    def test_end_terminates_the_job_and_closes_the_handle(self):
        k32 = _FakeKernel32()
        self._spawn(k32)
        with mock.patch.object(cg, "IS_WIN", True), mock.patch.object(cg, "_kernel32", lambda: k32), \
                mock.patch.object(cg, "_kill_tree_default", self.saved_kill_tree()):
            r = cg.end("capture", wait_s=0)
        self.assertIn(("TerminateJobObject", 77, 1), k32.calls,
                      "end() did not terminate the job - the grandchildren (conhost, node helpers) live on")
        self.assertIn(("CloseHandle", 77), k32.calls, "the job handle leaked")
        self.assertEqual("job", r["how"])
        self.assertEqual([], self.killed, "the pid kill ran beside the job kill - two kills for one tree")

    def saved_kill_tree(self):
        # the REAL _kill_tree_default, but with taskkill (the no-job fallback) never reachable: this law's records
        # all hold a job, so the job branch is what runs
        real = self.stack[2].temp_original

        def _kt(rec):
            self.assertTrue(rec.get("job"), "the fallback taskkill would have run on a fake pid")
            return real(rec)
        return _kt

    def test_a_failed_assignment_is_said_and_the_pid_kill_is_the_fallback(self):
        k32 = _FakeKernel32(assign_ok=False)
        p, rec = self._spawn(k32)
        self.assertIsNone(cg._LIVE["capture"]["job"], "a job that failed to take is still held")
        self.assertIn("taskkill /T is the fallback", rec["jobSay"])
        self.assertIn(("CloseHandle", 77), k32.calls, "the unused job handle leaked")
        with mock.patch.object(cg, "IS_WIN", True), mock.patch.object(cg, "_kernel32", lambda: k32):
            r = cg.end("capture", kill=self.kill, wait_s=0)
        self.assertEqual([9990031], self.killed, "without a job, the caller's pid kill must still run")
        self.assertNotIn(("TerminateJobObject", 77, 1), k32.calls)


# ── 4. the watchdog ──────────────────────────────────────────────────────────────────────────────────────────

def _cap_cmd():
    return "powershell.exe -NoProfile -File " + os.path.join(HERE, "capture_win.ps1")


class TheWatchdogEndsOnlyWhatIsOurs(_World):

    def _ledger(self, parent, pborn, children):
        os.makedirs(cg.LEDGER_DIR, exist_ok=True)
        with io.open(os.path.join(cg.LEDGER_DIR, "%d.json" % parent), "w", encoding="utf-8") as fh:
            json.dump({"parent": parent, "parentBirth": pborn, "expect": {}, "children": children}, fh)

    def test_dead_parents_children_are_ended_by_birth_and_strangers_kept(self):
        self._ledger(9990099, 100, {"capture": {"role": "capture", "pid": 9990101, "birth": 1000, "session": True},
                                    "ocr": {"role": "ocr", "pid": 9990103, "birth": 1000, "session": True}})
        self._ledger(9990555, 100, {"capture": {"role": "capture", "pid": 9990105, "birth": 1000, "session": True}})
        # THIS process is alive (it is): with it dead, the 'unrecorded child of ours' branch went blind in the drill -
        # the orphan fallback ended 9990202 for the wrong reason. [[sabotage-is-usually-the-wrong-one]]
        self.live.update({9990101, 9990103, 9990105, 9990555, 9990777, 9990888, 9990201, 9990202, 9990203, 9990205,
                          os.getpid()})
        # REG-1550 - every pid the watchdog may end has a birth the reader can answer (a kill re-asks it), and a dead
        # parent's child is ended only when the TABLE shows it running our role's command (the pid is otherwise a
        # number in a file); the reused 9990103 holds a capture born at 7777 - another life's, never ours
        self.births.update({9990101: 1000, 9990103: 7777, 9990105: 1000, 9990555: 100, 9990888: 900,
                            9990201: 1000, 9990205: 500})
        rows = [
            (9990101, 9990099, 1000, _cap_cmd()),         # recorded by a DEAD parent's ledger, born as recorded
            (9990103, 9990099, 7777, _cap_cmd()),         # recorded by that ledger at 1000, but born 7777: reused
            (9990201, 999998, 1000, _cap_cmd()),          # unrecorded, parent dead: an orphan
            (9990202, os.getpid(), 1000, _cap_cmd()),     # unrecorded child of THIS process: outside the door
            (9990203, 9990777, 1000, _cap_cmd()),         # unrecorded, parent alive and not ours: a stranger's
            (9990204, 9990777, 1000, "python tv_diablo.py --watch " + HERE),   # not a known role
            (9990205, 9990888, 500, _cap_cmd()),          # parent born AFTER it: a reused parent pid, orphan
            (9990105, 9990555, 1000, _cap_cmd()),         # recorded by a live parent's ledger
        ]
        st = cg.watchdog_tick(rows_fn=lambda: rows, kill=self.kill, alive=self.alive, birth=self.birth, now_ms=1,
                              settle_s=0.3)
        self.assertEqual({9990101, 9990201, 9990205}, set(self.killed),
                         "the watchdog ended the wrong set: %r (say %r)" % (sorted(self.killed), st["say"]))
        self.assertEqual([9990203], [s[0] for s in st["strangers"]], "another console's capture was ended or lost")
        self.assertEqual([9990202], [b[0] for b in st["bypass"]],
                         "THIS process's own child outside the door was ended or lost - REG-1550: on his live Mac "
                         "that is the console's own OCR worker and warm reader")
        self.assertIn(9990103, [k[0] for k in st["kept"]], "the reused pid was not said")
        self.assertIn("reused", [k[2] for k in st["kept"] if k[0] == 9990103][0])
        self.assertIn(9990105, [k[0] for k in st["kept"]], "a live parent's recorded child was not kept")
        self.assertEqual((0, True), (st["owed"], st["worked"]))
        self.assertFalse(os.path.exists(os.path.join(cg.LEDGER_DIR, "9990099.json")),
                         "the dead parent's ledger was not removed once its children were ended")
        self.assertTrue(os.path.exists(os.path.join(cg.LEDGER_DIR, "9990555.json")), "a live parent's ledger was removed")

    def test_an_unreadable_table_ends_nothing_and_owes_none(self):
        self.live.update({9990301, 9990777})
        st = cg.watchdog_tick(rows_fn=lambda: None, kill=self.kill, alive=self.alive, birth=self.birth, now_ms=1)
        self.assertEqual([], self.killed)
        self.assertIsNone(st["owed"], "an unreadable table read as 'nothing owed' (0) - UNKNOWN is not 0")
        self.assertTrue(st["unknown"])
        self.assertIn("UNKNOWN", st["say"])

    def test_a_kill_that_would_not_land_is_owed(self):
        self.live.update({9990401})
        self.births[9990401] = 1000             # REG-1550 - the kill re-asks the birth; a readable one lets it fire
        rows = [(9990401, 999998, 1000, _cap_cmd())]
        st = cg.watchdog_tick(rows_fn=lambda: rows, kill=lambda pid: None, alive=self.alive, birth=self.birth,
                              now_ms=1, settle_s=0.2)
        self.assertEqual(1, st["owed"])
        self.assertFalse(st["worked"])
        self.assertEqual([9990401], [f[0] for f in st["failed"]])

    def test_the_role_of_a_command_line(self):
        self.assertEqual("capture", cg.role_of_command(_cap_cmd()))
        self.assertEqual("vision", cg.role_of_command("node claude -p --input-format stream-json --output-format "
                                                      "stream-json --add-dir " + HERE + "/frames"))
        self.assertEqual("ocr", cg.role_of_command(HERE + "/bin/ocr_mac --worker"))
        self.assertIsNone(cg.role_of_command("python " + HERE + "/tv_diablo.py --watch"))
        self.assertIsNone(cg.role_of_command("claude -p something " + HERE), "a plain claude session is not a role")


# ── 5. the census and the doctor row ─────────────────────────────────────────────────────────────────────────

class TheCensusAndTheDoctorRow(_World):

    def _ledger(self, parent, children, expect=None):
        os.makedirs(cg.LEDGER_DIR, exist_ok=True)
        with io.open(os.path.join(cg.LEDGER_DIR, "%d.json" % parent), "w", encoding="utf-8") as fh:
            json.dump({"parent": parent, "parentBirth": 100, "expect": expect or {}, "children": children}, fh)

    def test_two_captures_across_two_parents_is_over_the_ceiling(self):
        self._ledger(9990555, {"capture": {"role": "capture", "pid": 9990105, "birth": 1000}})
        self._ledger(9990556, {"capture": {"role": "capture", "pid": 9990106, "birth": 1000}})
        self.live.update({9990105, 9990106})
        c = cg.census(alive=self.alive)
        self.assertFalse(c["families"]["capture"]["ok"], "two live captures read OK: %r" % c["families"]["capture"])
        self.assertFalse(c["ok"])
        row = ca._one_of_each_check(alive=self.alive)
        self.assertFalse(row["ok"], "the doctor row read OK with two captures alive: %r" % row)
        self.assertIn("capture: 2 alive", row["detail"])
        self.assertIn("Task Manager", row.get("fix") or "")

    def test_the_agents_pool_ceiling_comes_from_its_ledger(self):
        self._ledger(9990557, {"vision-r0": {"role": "vision-r0", "pid": 9990110, "birth": 1000},
                               "vision-r1": {"role": "vision-r1", "pid": 9990111, "birth": 1000}},
                     expect={"vision": [0, 2]})
        self.live.update({9990110, 9990111})
        c = cg.census(alive=self.alive)
        self.assertTrue(c["families"]["vision"]["ok"], "a two-reader pool the agent declared read as over the ceiling")
        self.assertEqual([0, 2], c["families"]["vision"]["expected"])
        self.assertTrue(ca._one_of_each_check(alive=self.alive)["ok"])

    def test_a_clean_console_is_ok_and_an_unknown_watchdog_is_not(self):
        row = ca._one_of_each_check(alive=self.alive)
        self.assertTrue(row["ok"], "nothing recorded and no watchdog yet read as a fault: %r" % row)
        self.assertIn("watchdog not run yet", row["detail"])
        cg.WATCHDOG.update(lastTs=1, unknown=True, say="UNKNOWN - the process table could not be asked")
        row = ca._one_of_each_check(alive=self.alive)
        self.assertFalse(row["ok"], "an UNKNOWN table read OK - orphans could film behind a green row")
        self.assertIn("UNKNOWN", row["detail"])

    def test_a_would_not_end_warns_only_while_it_lives(self):
        cg.WATCHDOG.update(lastTs=1, unknown=False, failed=[(9990401, "capture", "would not end")], say="1 would not end")
        self.live.add(9990401)
        self.assertFalse(ca._one_of_each_check(alive=self.alive)["ok"])
        self.live.discard(9990401)
        row = ca._one_of_each_check(alive=self.alive)
        self.assertTrue(row["ok"], "the row kept warning about a pid that left: %r" % row)
        self.assertIn("has since left", row["detail"])

    def test_the_doctor_the_rescue_loop_and_status_carry_it(self):
        self.assertIn("_one_of_each_check", ca.doctor_payload.__code__.co_names, "doctor_payload no longer asks the row")
        loop = inspect.getsource(ca._console_rescue_loop)
        self.assertIn("_child_guard_tick()", loop, "nothing runs the watchdog")
        self.assertIn('"childGuard": _child_guard_status()', inspect.getsource(ca))
        self.assertEqual({"door", "watchdog", "ram"}, set(ca._child_guard_status()))

    def test_the_console_tick_uses_its_own_doors_and_never_raises(self):
        with mock.patch.object(cg, "watchdog_tick", lambda **k: (_ for _ in ()).throw(RuntimeError("x"))):
            self.assertIsNone(ca._child_guard_tick())
        self.assertIn("raised RuntimeError", cg.WATCHDOG["say"])
        seen = {}
        with mock.patch.object(cg, "watchdog_tick", lambda **k: seen.update(k) or {}):
            ca._child_guard_tick()
        self.assertIs(ca._pid_alive, seen.get("alive"), "the console's tick does not hand the watchdog its own alive")
        self.assertTrue(callable(seen.get("kill")))


# ── 6. the memory policy ─────────────────────────────────────────────────────────────────────────────────────

class TheMemoryPolicy(_World):

    def test_under_the_floor_no_secondary_worker(self):
        ok, why = cg.secondary_spawn_allowed(free_mb=300, floor_mb=1024)
        self.assertFalse(ok, "300 MB free cleared a 1024 MB floor")
        self.assertIn("under the 1024 MB floor", why)
        self.assertEqual(1, cg.RAM["refused"])

    def test_above_the_floor_is_allowed(self):
        self.assertTrue(cg.secondary_spawn_allowed(free_mb=2048, floor_mb=1024)[0])

    def test_unknown_free_ram_never_refuses_and_says_so(self):
        ok, why = cg.secondary_spawn_allowed(free_mb=None, floor_mb=1024)
        self.assertTrue(ok, "UNKNOWN free RAM refused the spawn - on a machine whose meter cannot be read the fast "
                            "lane and the stall drain would be off for ever")
        self.assertIn("UNKNOWN", why)

    def test_the_meter_is_cached_and_never_zero_for_unknown(self):
        cg.RAM.update(lastTs=None, lastFreeMb=None, unknown=0)
        reads = []
        self.assertEqual(1500, cg.free_ram_mb(now=100.0, read=lambda: reads.append(1) or 1500))
        self.assertEqual(1500, cg.free_ram_mb(now=102.0, read=lambda: reads.append(1) or 1))
        self.assertEqual(1, len(reads), "the meter was read again inside the cache window")
        self.assertIsNone(cg.free_ram_mb(now=200.0, read=lambda: None), "an unreadable meter did not read as UNKNOWN")
        self.assertEqual(1, cg.RAM["unknown"])

    def test_vm_stat_is_parsed_and_this_machines_meter_answers_or_says_unknown(self):
        sample = ("Mach Virtual Memory Statistics: (page size of 16384 bytes)\nPages free:      32418.\n"
                  "Pages active:    213812.\nPages inactive:  195691.\nPages speculative:  17107.\nPages wired down: 1.\n")
        self.assertEqual(int((32418 + 195691 + 17107) * 16384 // (1024 * 1024)), cg.parse_vm_stat(sample))
        self.assertIsNone(cg.parse_vm_stat("garbage"))
        cg.RAM.update(lastTs=None, lastFreeMb=None)
        v = cg.free_ram_mb()
        self.assertTrue(v is None or (isinstance(v, int) and v > 0), "free RAM read as %r" % (v,))
        print("free RAM on this machine: %s MB" % v)


# ── 7. the console's capture through the door ───────────────────────────────────────────────────────────────

class _TrapPsutil(object):
    BELOW_NORMAL_PRIORITY_CLASS = 0x00004000

    def __init__(self):
        self.touched = []

    def Process(self, pid):
        self.touched.append(pid)
        return self

    def nice(self, *_a):
        return None


class TheConsolesCaptureGoesThroughTheDoor(_World):
    """The five-captures shape, through the REAL _start_capture / _stop_capture: the lamp cleared the lease and
    dropped _capture_proc while the capture never died. Windows edges stubbed (a capture is a pid in a set)."""

    def setUp(self):
        super().setUp()
        self.pidfile = os.path.join(self.d, "control_capture.pid")
        self.log = io.StringIO()
        self.ca_saved = (ca._capture_proc, dict(ca._CAP_STOP))
        ca._capture_proc = None
        self.reniced = []
        self.ca_stack = [
            mock.patch.object(ca, "IS_WIN", True),
            mock.patch.object(ca, "CAP_PID_PATH", self.pidfile),
            mock.patch.object(ca, "CAP_KILL_SETTLE_S", 0.3),
            mock.patch.object(ca, "_log_fp", self.log),
            mock.patch.object(ca, "_stub_never_films", lambda *a, **k: False),
            mock.patch.object(ca, "_capture_off", lambda *a, **k: False),
            mock.patch.object(ca, "_pid_alive", self.alive),
            mock.patch.object(ca, "_kill_pid", lambda pid, force=False: self.kill(pid)),
            mock.patch.object(ca, "_lower_capture_priority", lambda pid: self.reniced.append(pid)),
            mock.patch.object(ca.os.path, "isfile",
                              lambda p: True if p == ca.CAPTURE_PS1 else (str(p).startswith(self.d) and os.path.exists(p))),
            mock.patch.dict(sys.modules, {"psutil": _TrapPsutil()}),
            mock.patch.object(ca.subprocess, "Popen", self.popen(range(9990601, 9990699, 2))),
        ]
        for p in self.ca_stack:
            p.start()

    def tearDown(self):
        for p in reversed(self.ca_stack):
            p.stop()
        ca._capture_proc = self.ca_saved[0]
        ca._CAP_STOP.clear(); ca._CAP_STOP.update(self.ca_saved[1])
        super().tearDown()

    def test_a_capture_the_lamp_lost_is_ended_before_the_next_one_starts(self):
        a = ca._start_capture({"PATH": "x"}, self.log)
        self.assertIn(a, self.live)
        self.assertEqual(a, (cg.record_of("capture") or {}).get("pid"), "the console's capture was not recorded")
        # v3850 - the capture outlives its console under a lease, so it is never put in a job; the log says so
        self.assertIn("no job: this role outlives its console (lease-held)", self.log.getvalue(),
                      "the spawn log does not say whether the job took")
        # the lamp's path: lease cleared, _capture_proc dropped - and the process is STILL ALIVE
        os.remove(self.pidfile)
        ca._capture_proc = None
        b = ca._start_capture({"PATH": "x"}, self.log)
        self.assertNotEqual(a, b)
        self.assertNotIn(a, self.live, "THE LOST CAPTURE SURVIVED THE NEXT START - two captures film at once; this is "
                                       "how five stacked up on the ALT")
        self.assertEqual([b], sorted(p for p in (s[0] for s in self.spawned) if p in self.live))
        self.assertEqual([a], self.killed, "the old capture was not ended through this console's own kill")
        self.assertEqual(b, cg.record_of("capture")["pid"])
        self.assertIn("after ending pid %d" % a, cg.RECEIPT["say"])
        self.assertEqual([], sys.modules["psutil"].touched, "the law reached the real priority step with a fake pid")

    def test_the_stop_ends_the_recorded_tree_once_and_forgets_it(self):
        a = ca._start_capture({"PATH": "x"}, self.log)
        ca._CAP_STOP.update(survived=0, last=None)
        ca._stop_capture()
        self.assertEqual([a], self.killed, "the stop killed the capture twice, or not at all: %r" % self.killed)
        self.assertIsNone(cg.record_of("capture"), "the stopped capture is still recorded")
        self.assertEqual(0, ca._CAP_STOP["survived"])
        self.assertFalse(os.path.exists(self.pidfile))

    def _lease(self, pid, rows):
        with io.open(self.pidfile, "w") as fh:
            fh.write(str(pid))
        self.live.add(pid)
        ca._CAP_STOP.update(survived=0, last=None, unverified=None)
        with mock.patch.object(ca, "_capture_rows", lambda timeout=30: rows):
            ca._stop_capture()

    def test_a_lease_the_door_never_recorded_is_killed_when_the_table_shows_a_capture(self):
        # REG-1550 - a previous life's lease: killed only because the process table shows that pid running THIS
        # checkout's capture_win.ps1
        self._lease(9990777, [(9990777, 9990001, 1000, 900)])
        self.assertEqual([9990777], self.killed, "a previous life's lease, shown by the table, was not killed")
        self.assertEqual(0, ca._CAP_STOP["survived"])
        self.assertFalse(os.path.exists(self.pidfile))

    def test_a_lease_pid_the_table_does_not_show_as_a_capture_is_not_killed(self):
        # REG-1550 - the lease file names a pid; Windows hands pids out again within minutes. Not a capture now ->
        # not killed, said, and never counted as a survivor (it was never ours to count)
        self._lease(9990778, [(9990001, 9990002, 1000, 900)])
        self.assertEqual([], self.killed, "A PID FROM A LEASE FILE WAS KILLED WITHOUT THE TABLE SHOWING A CAPTURE - "
                                          "that could be a stranger's tree (taskkill /T)")
        self.assertIn("not a capture", (ca._CAP_STOP.get("unverified") or {}).get("say", ""))
        self.assertEqual(0, ca._CAP_STOP["survived"], "an unkilled stranger's pid was counted as a capture that survived")
        self.assertFalse(os.path.exists(self.pidfile), "the lease was not withdrawn - a real capture leaves by it")

    def test_an_unknown_table_kills_no_lease_pid_and_says_so(self):
        self._lease(9990779, None)
        self.assertEqual([], self.killed, "a lease pid was killed on an UNKNOWN table")
        self.assertIn("UNKNOWN", (ca._CAP_STOP.get("unverified") or {}).get("say", ""))
        self.assertEqual(0, ca._CAP_STOP["survived"])

    def test_our_own_unreaped_capture_is_killed_without_asking_the_table(self):
        # the kernel holds an unreaped child's pid for us: no table can tell us more than poll() already does
        a = ca._start_capture({"PATH": "x"}, self.log)
        ca._CAP_STOP.update(survived=0, last=None, unverified=None)
        cg._LIVE.clear()                     # the door forgot it (an in-place relaunch's shape) but _capture_proc lives
        with mock.patch.object(ca, "_capture_rows", lambda timeout=30: (_ for _ in ()).throw(RuntimeError("no table"))):
            ca._stop_capture()
        self.assertEqual([a], self.killed, "our own unreaped Popen was not killed, or the table was asked for it")


# ── 8. the agent's workers through the door ──────────────────────────────────────────────────────────────────

class TheAgentsWorkersGoThroughTheDoor(_World):

    def setUp(self):
        super().setUp()
        self.tv_saved = (tv._STALL_WORKER, dict(tv._STALL_RELEASE), tv.OCR_ENABLED)
        self.popen_patch = mock.patch.object(subprocess, "Popen", self.popen(range(9990801, 9990899, 2)))
        self.popen_patch.start()

    def tearDown(self):
        self.popen_patch.stop()
        tv._STALL_WORKER = self.tv_saved[0]
        tv._STALL_RELEASE.clear(); tv._STALL_RELEASE.update(self.tv_saved[1])
        tv.OCR_ENABLED = self.tv_saved[2]
        super().tearDown()

    def test_a_vision_worker_spawns_and_stops_through_the_door(self):
        w = tv.VisionWorker(role="vision-law")
        w._spawn()
        rec = cg.record_of("vision-law")
        self.assertIsNotNone(rec, "the reader's claude was spawned outside the door - nothing ends its tree")
        self.assertEqual(w.p.pid, rec["pid"])
        if IS_POSIX:
            self.assertTrue(self.spawned[0][2].get("start_new_session"), "the reader does not lead its own session")
        self.assertIn("--input-format", self.spawned[0][1])
        w.stop()
        self.assertIsNone(cg.record_of("vision-law"), "stop() left the record - a restart would not end this tree")
        self.assertEqual([rec["pid"]], self.killed, "stop() did not end the tree through the door")

    def test_a_deaf_reader_is_buried_as_a_whole_tree(self):
        # the sweep's sibling: a write that never lands hands the worker to _bury_worker, which killed only the head
        w = tv.VisionWorker(role="vision-deaf")
        with mock.patch.object(tv, "_sub_budget_check", lambda *a, **k: None), \
                mock.patch.object(tv, "_pipe_write_by", lambda *a, **k: False):
            self.assertIsNone(w.ask("x", timeout=1))
        pid = self.spawned[0][0]
        self.assertEqual([pid], self.killed, "the deaf reader was not ended through the door - its helpers live on")
        self.assertIsNone(cg.record_of("vision-deaf"), "the buried reader is still recorded")
        self.assertIsNone(w.p)

    def test_pool_readers_and_the_stall_reader_hold_distinct_roles(self):
        roles = [w.role for w in tv._WORKERS]
        self.assertEqual(len(set(roles)), len(roles), "two pool readers share a role: %r" % roles)
        self.assertTrue(all(r.startswith("vision-r") for r in roles), roles)
        tv._STALL_WORKER = None
        self.assertEqual("vision-stall", tv._stall_worker().role)
        self.assertEqual([0, tv.POOL_N], cg._expected("vision"))

    def test_the_stall_reader_releases_its_claude_after_each_sweep(self):
        class _W(object):
            def __init__(self):
                self.p, self.stops = object(), 0

            def stop(self):
                self.stops += 1
                self.p = None
        w = _W()
        tv._STALL_RELEASE.update(n=0, lastTs=None)
        self.assertTrue(tv._stall_worker_release(w))
        self.assertEqual(1, w.stops)
        self.assertEqual(1, tv._STALL_RELEASE["n"])
        self.assertFalse(tv._stall_worker_release(w), "a reader with no process was 'released' again")
        # the join: the release runs where the sweep's busy flag clears, and nowhere else would see every sweep
        src = inspect.getsource(tv)
        anchor = 'globals()["_STALL_BUSY"] = False'
        self.assertEqual(1, src.count(anchor), "the sweep's busy-clear is no longer one site")
        after = src[src.index(anchor):src.index(anchor) + 200]
        self.assertIn("_stall_worker_release()", after,
                      "the stall reader is not released after the sweep - ~400 MB stays warm for a safety net")

    def test_the_stall_drain_does_not_fire_under_the_ram_floor(self):
        thr = tv.STALL_DRAIN_S * 1000
        self.assertTrue(tv._stall_drain_decision(1, 1, 1, thr, False))
        self.assertFalse(tv._stall_drain_decision(1, 1, 1, thr, False, ram_ok=False),
                         "the stall drain fires a second claude into memory pressure")
        asked = []
        self.assertFalse(tv._stall_drain_decision(1, 1, 1, thr, False, ram_ok=lambda: asked.append(1) and False))
        self.assertFalse(tv._stall_drain_decision(0, 1, 1, thr, False, ram_ok=lambda: asked.append(1) or True))
        self.assertEqual(1, len(asked), "the meter was asked before the cheaper gates had opened")
        with mock.patch.object(tv, "_text_eye_backlog_len", lambda: 1), \
                mock.patch.object(tv, "_vision_in_flight_n", lambda: tv.POOL_N), \
                mock.patch.object(tv, "_live_stall_ms", lambda: thr + 1), \
                mock.patch.object(tv, "_STALL_BUSY", False), \
                mock.patch.dict(os.environ, {"TV_STALL_DRAIN": "1"}):
            with mock.patch.object(cg, "secondary_spawn_allowed", lambda *a, **k: (False, "under")):
                self.assertFalse(tv._stall_drain_ready(), "the live glue does not ask the RAM policy")
            with mock.patch.object(cg, "secondary_spawn_allowed", lambda *a, **k: (True, "clear")):
                self.assertTrue(tv._stall_drain_ready())

    def test_the_ocr_worker_is_not_started_under_the_floor_and_goes_through_the_door_above_it(self):
        o = tv.OcrWorker()
        tv.OCR_ENABLED = True
        with mock.patch.object(tv, "_ocr_worker_cmd", lambda: ["ocr-fake", "--worker"]), \
                mock.patch.object(cg, "secondary_spawn_allowed", lambda *a, **k: (False, "under the floor")):
            self.assertFalse(o._spawn(), "the OCR worker started under the RAM floor")
            self.assertEqual([], self.spawned)
            self.assertFalse(o.ok)
        with mock.patch.object(tv, "_ocr_worker_cmd", lambda: ["ocr-fake", "--worker"]), \
                mock.patch.object(cg, "secondary_spawn_allowed", lambda *a, **k: (True, "clear")):
            self.assertTrue(o._spawn())
        self.assertEqual(o.p.pid, (cg.record_of("ocr") or {}).get("pid"), "the OCR worker was spawned outside the door")
        o.stop()
        self.assertIsNone(cg.record_of("ocr"))
        self.assertEqual([self.spawned[0][0]], self.killed, "stop() did not end the OCR tree through the door")


# ── 9. REG-1550: a live parent's child is never the watchdog's to end ───────────────────────────────────────

def _vision_cmd():
    return ("/usr/local/bin/claude -p --input-format stream-json --output-format stream-json --model sonnet "
            "--add-dir " + os.path.join(HERE, "frames") + " --add-dir " + os.path.join(HERE, "frames", "hist"))


def _ocr_cmd():
    return os.path.join(HERE, "bin", "ocr_mac") + " --worker"


class ALiveParentsChildIsNeverEnded(_World):
    """REG-1550 - MEASURED ON HIS LIVE MAC (2026-09-30, the console at pid 66440): its own KAI-closer OCR worker
    (`ocr_mac --worker`, ppid 66440) and its own warm chronicle reader (`claude -p --input-format stream-json
    --add-dir .../tv/frames`, ppid 66440) are legitimately outside the door, and the first cut's classifier
    returned BOTH as TO_END 'unrecorded child of ours'. The same rule would have ended a reader the agent spawned
    40 ms before the tick, its ledger write not yet landed. A live parent answers for its own children."""

    def _his_table(self):
        me = os.getpid()
        self.live.update({me, 9990601, 9990602})
        self.births.update({me: 100, 9990601: 1000, 9990602: 1000})
        return [(9990601, me, 1000, _ocr_cmd()), (9990602, me, 1000, _vision_cmd())]

    def test_the_consoles_own_workers_outside_the_door_are_said_never_ended(self):
        rows = self._his_table()
        st = cg.watchdog_tick(rows_fn=lambda: rows, kill=self.kill, alive=self.alive, birth=self.birth, now_ms=1,
                              settle_s=0.2)
        self.assertEqual([], self.killed, "THE CONSOLE ENDED ITS OWN LIVE WORKERS (%r) - the shape measured on his "
                                          "Mac: the closer's OCR worker and the warm reader, both its children" % self.killed)
        self.assertEqual({9990601, 9990602}, {b[0] for b in st["bypass"]}, "the workers outside the door were not said")
        self.assertIn("outside the door", st["say"])
        self.assertEqual((True, 0), (st["worked"], st["owed"]))
        c = cg.census(alive=self.alive)
        self.assertTrue(c["families"]["ocr"]["ok"], c["families"]["ocr"])
        self.assertEqual(1, c["families"]["ocr"]["owners"]["this process"]["outsideTheDoor"])
        self.assertIn("outside the door", c["families"]["ocr"]["say"])
        row = ca._one_of_each_check(alive=self.alive)
        self.assertTrue(row["ok"], "the doctor row faulted the console for its own closer worker: %r" % row)
        # the ROW's own sentence, not the census's (whose say also carries 'outside the door' - a proof that
        # deleted the row's sentence stayed green on the census's, [[source-reading-guard]] §4b in a receipt)
        self.assertIn("outside the door under a live parent of ours (left alone)", row["detail"])

    def test_a_recorded_childs_own_child_is_left_alone_too(self):
        cg.spawn("capture", ["x"], popen=self.popen([9990611]), kill=self.kill)
        self.births[9990611] = 1000
        self.live.update({9990612})
        self.births[9990612] = 1001
        rows = [(9990612, 9990611, 1001, _ocr_cmd())]          # a child of our recorded capture, unrecorded
        st = cg.watchdog_tick(rows_fn=lambda: rows, kill=self.kill, alive=self.alive, birth=self.birth, now_ms=1,
                              settle_s=0.2)
        self.assertEqual([], self.killed)
        self.assertEqual([9990612], [b[0] for b in st["bypass"]])

    def test_a_bypass_that_leaves_stops_being_counted(self):
        rows = self._his_table()
        cg.watchdog_tick(rows_fn=lambda: rows, kill=self.kill, alive=self.alive, birth=self.birth, now_ms=1, settle_s=0.2)
        self.live.discard(9990601)
        c = cg.census(alive=self.alive)
        self.assertEqual(0, c["families"]["ocr"]["alive"], "a closer worker that has exited is still counted")
        self.assertEqual(1, c["families"]["vision"]["alive"])


# ── 10. REG-1550: nothing is ended on a guess ──────────────────────────────────────────────────────────────

class TheWatchdogNeverEndsOnAGuess(_World):

    def _ledger(self, parent, pborn, children):
        os.makedirs(cg.LEDGER_DIR, exist_ok=True)
        with io.open(os.path.join(cg.LEDGER_DIR, "%d.json" % parent), "w", encoding="utf-8") as fh:
            json.dump({"parent": parent, "parentBirth": pborn, "expect": {}, "children": children}, fh)

    def _tick(self, rows, **kw):
        return cg.watchdog_tick(rows_fn=(lambda: rows), kill=self.kill, alive=self.alive, birth=self.birth, now_ms=1,
                                settle_s=0.2, **kw)

    def test_a_live_parent_whose_birth_cannot_be_read_now_keeps_its_children(self):
        # the ledger knows its parent's birth; the reader cannot answer for that pid NOW. The first cut read that as
        # 'gone' and ended the children of a live console.
        self._ledger(9990701, 100, {"capture": {"role": "capture", "pid": 9990702, "birth": 1000, "session": True}})
        self.live.update({9990701, 9990702})
        self.births[9990702] = 1000                    # the child's birth reads fine; the parent's does not
        st = self._tick([(9990702, 9990701, 1000, _cap_cmd())])
        self.assertEqual([], self.killed, "A LIVE PARENT'S CHILD WAS ENDED because the parent's birth read UNKNOWN")
        self.assertTrue(any("UNKNOWN" in k[2] for k in st["kept"]), st["kept"])
        self.assertTrue(os.path.exists(os.path.join(cg.LEDGER_DIR, "9990701.json")), "the live parent's ledger was removed")

    def test_a_dead_parents_child_is_ended_only_with_a_table_row_of_our_command_and_birth(self):
        self._ledger(9990711, 100, {
            "capture": {"role": "capture", "pid": 9990712, "birth": 1000, "session": True},      # in the table, ours
            "ocr": {"role": "ocr", "pid": 9990713, "birth": 1000, "session": True},              # alive, NO row
            "vision-r0": {"role": "vision-r0", "pid": 9990714, "birth": 1000, "session": True},  # a stranger's command
            "vision-stall": {"role": "vision-stall", "pid": 9990715, "birth": 1000, "session": True},  # born later: reused
        })
        self.live.update({9990712, 9990713, 9990714, 9990715})
        self.births.update({9990712: 1000, 9990713: 1000, 9990714: 1000, 9990715: 7777})
        rows = [(9990712, 9990711, 1000, _cap_cmd()),
                (9990714, 9990711, 1000, "notepad.exe " + os.path.join(HERE, "notes.txt")),
                (9990715, 9990711, 7777, _vision_cmd())]
        st = self._tick(rows)
        self.assertEqual([9990712], self.killed, "the dead parent's children ended: %r - only the one the table shows "
                                                 "running our command, born as recorded, may be ended" % self.killed)
        why = {k[0]: k[2] for k in st["kept"]}
        self.assertIn("no command of ours", why.get(9990713, ""), why)
        self.assertIn("stranger's command", why.get(9990714, ""), why)
        self.assertIn("reused", why.get(9990715, ""), why)
        self.assertFalse(os.path.exists(os.path.join(cg.LEDGER_DIR, "9990711.json")),
                         "nothing of ours is left under that parent - its file should be gone")

    def test_an_unknown_table_judges_no_dead_parents_child_and_keeps_the_file(self):
        self._ledger(9990721, 100, {"capture": {"role": "capture", "pid": 9990722, "birth": 1000, "session": True}})
        self.live.update({9990722})
        self.births[9990722] = 1000
        st = cg.watchdog_tick(rows_fn=lambda: None, kill=self.kill, alive=self.alive, birth=self.birth, now_ms=1)
        self.assertEqual([], self.killed, "a dead parent's child was ended with the table UNKNOWN - birth alone is a "
                                          "probability, the command line is the proof")
        self.assertIsNone(st["owed"])
        self.assertTrue(any("UNKNOWN" in k[2] for k in st["kept"]), st["kept"])
        self.assertTrue(os.path.exists(os.path.join(cg.LEDGER_DIR, "9990721.json")),
                        "the dead parent's file was removed while its child was never judged - the next tick would "
                        "never see it")

    def test_a_pid_reused_between_the_table_read_and_the_kill_is_not_ended(self):
        self.live.update({9990731})
        reads = []

        def birth(pid):
            if pid == 9990731:
                reads.append(1)
                return 1000 if len(reads) == 1 else 5000        # the table's re-read says 1000; the kill's asks again
            return self.births.get(pid)
        st = cg.watchdog_tick(rows_fn=lambda: [(9990731, 999998, 1000, _cap_cmd())], kill=self.kill, alive=self.alive,
                              birth=birth, now_ms=1, settle_s=0.2)
        self.assertEqual([], self.killed, "the pid was ended although it was reused after the table was read")
        self.assertTrue(any("reused since the table was read" in k[2] for k in st["kept"]), st["kept"])
        self.assertEqual(2, len(reads), "the kill did not re-ask the birth")

    def test_a_birth_that_cannot_be_read_at_the_kill_ends_nothing(self):
        self.live.update({9990741})
        st = self._tick([(9990741, 999998, 1000, _cap_cmd())])   # an orphan whose birth the reader cannot give
        self.assertEqual([], self.killed, "an orphan whose birth is UNKNOWN was ended on a guess")
        self.assertTrue(any("never ended on a guess" in k[2] for k in st["kept"]), st["kept"])

    def test_the_tables_births_are_read_through_the_records_own_reader(self):
        # the DST shape: `ps -o lstart` -> mktime reads an hour LESS than sysctl for a process born in the repeated
        # hour. A recorded worker of a live agent then matched no record, and its agent read as 'born after it'.
        self._ledger(9990751, 990, {"vision-r0": {"role": "vision-r0", "pid": 9990752, "birth": 1000, "session": True}})
        self.live.update({9990751, 9990752})
        self.births.update({9990751: 990, 9990752: 1000})
        st = self._tick([(9990752, 9990751, 1000 - 3600, _vision_cmd())])
        self.assertEqual([], self.killed, "A LIVE AGENT'S RECORDED READER WAS ENDED because the table's clock read its "
                                          "birth an hour off the reader that wrote the record")
        self.assertIn((9990752, "vision", "recorded"), st["kept"])

    def test_the_ocr_signature_names_the_worker_not_any_dash_dash_worker(self):
        self.assertIsNone(cg.role_of_command("python " + os.path.join(HERE, "run_gates.py") + " --workers=3"),
                          "'--workers=3' read as the OCR worker - an orphaned gate run of this checkout would be ended")
        self.assertEqual("ocr", cg.role_of_command(_ocr_cmd()))
        self.assertEqual("ocr", cg.role_of_command("powershell.exe -NoLogo -File " + os.path.join(HERE, "ocr_win.ps1")))
        self.assertIsNone(cg.role_of_command("/opt/custom/bin --worker " + HERE), "a custom TV_OCR_BIN is not a role")


# ── 11. REG-1551: the census grades each owner; the receipt owes what still lives; the lock; execv ──────────

class TheCensusGradesEachOwner(_World):

    def _ledger(self, parent, children, expect=None):
        os.makedirs(cg.LEDGER_DIR, exist_ok=True)
        with io.open(os.path.join(cg.LEDGER_DIR, "%d.json" % parent), "w", encoding="utf-8") as fh:
            json.dump({"parent": parent, "parentBirth": 100, "expect": expect or {}, "children": children}, fh)

    def test_the_consoles_reader_beside_the_agents_is_two_owners_not_one_over(self):
        # his Mac: the console's pool reader (chronicle/vault reads run in-process) AND the agent's, one each
        cg.spawn("vision-r0", ["claude"], popen=self.popen([9990801]), kill=self.kill)
        cg.expect("vision", 0, 1)
        self._ledger(9990802, {"vision-r0": {"role": "vision-r0", "pid": 9990803, "birth": 1000}}, expect={"vision": [0, 1]})
        self.live.add(9990803)
        c = cg.census(alive=self.alive)
        f = c["families"]["vision"]
        self.assertTrue(f["ok"], "ONE reader per owner read as over the ceiling: %r - the doctor row would be amber "
                                 "for ever on his Mac" % f)
        self.assertEqual(([0, 2], 2, "parent"), (f["expected"], f["alive"], f["scope"]))
        self.assertIn("across 2 owners", f["say"])
        self.assertTrue(ca._one_of_each_check(alive=self.alive)["ok"])

    def test_one_owner_over_its_own_ceiling_is_over(self):
        self._ledger(9990811, {"vision-r0": {"role": "vision-r0", "pid": 9990812, "birth": 1000},
                               "vision-r1": {"role": "vision-r1", "pid": 9990813, "birth": 1000}}, expect={"vision": [0, 1]})
        self.live.update({9990812, 9990813})
        f = cg.census(alive=self.alive)["families"]["vision"]
        self.assertFalse(f["ok"], "an agent holding two readers against its declared one read OK: %r" % f)
        self.assertIn("parent 9990811 holds 2 (declared at most 1)", f["say"])

    def test_a_bypass_row_counts_against_its_parents_ceiling(self):
        me = os.getpid()
        self.live.update({9990821, 9990822})
        cg.WATCHDOG.update(bypass=[(9990821, "ocr", me, "outside"), (9990822, "ocr", me, "outside")])
        f = cg.census(alive=self.alive)["families"]["ocr"]
        self.assertFalse(f["ok"], "two OCR workers of this process outside the door read OK: %r" % f)
        self.assertIn("2 outside the door", f["say"])
        cg.WATCHDOG.update(bypass=[(9990821, "ocr", me, "outside")])
        f = cg.census(alive=self.alive)["families"]["ocr"]
        self.assertTrue(f["ok"], f)
        self.assertIn("1 outside the door", f["say"])


class _Stubborn(_FakeProc):
    """A child that ignores its kill and leaves only when the law says so."""

    def __init__(self, pid, live):
        super().__init__(pid, live)
        import threading
        self.ev = threading.Event()

    def kill(self):
        self.killed += 1

    def wait(self, timeout=None):
        if timeout is None:
            self.ev.wait(5)
            return 0
        raise subprocess.TimeoutExpired("x", timeout)


class TheReceiptOwesOnlyWhatStillLives(_World):

    def test_a_survivor_that_finally_leaves_is_no_longer_owed(self):
        p = _Stubborn(9990831, self.live)
        self.live.add(9990831)
        cg.spawn("law-x", ["x"], popen=lambda argv, **kw: p, kill=self.kill)
        self.killed[:] = []
        r = cg.end("law-x", kill=lambda pid: None, alive=self.alive, birth=self.birth, wait_s=0.2)
        self.assertFalse(r["ended"], "premise: the child outlived the bounded wait")
        self.assertEqual((1, [9990831]), (cg.RECEIPT["owed"], cg.RECEIPT["survivorPids"]))
        self.live.discard(9990831)
        p.ev.set()
        deadline = time.time() + 3
        while time.time() < deadline and cg.RECEIPT["owed"]:
            time.sleep(0.02)
        self.assertEqual(0, cg.RECEIPT["owed"], "the survivor left (its wait() returned) and the receipt still owes it")
        self.assertEqual(1, cg.RECEIPT["survivors"], "the lifetime count is history and stays")

    def test_a_foreign_survivor_is_re_asked_not_remembered(self):
        cg._LIVE["capture"] = {"role": "capture", "pid": 9990841, "birth": 1000, "parent": 9990009, "parentBirth": 50,
                               "argv0": "powershell.exe", "ts": 1, "session": False, "job": None, "proc": None}
        self.live.add(9990841)
        self.births[9990841] = 1000
        r = cg.end("capture", kill=lambda pid: None, alive=self.alive, birth=self.birth, wait_s=0.2)
        self.assertFalse(r["ended"])
        self.assertEqual(1, cg.RECEIPT["owed"])
        self.live.discard(9990841)
        self.assertEqual(0, cg._owed(alive=self.alive), "a foreign survivor that left is still owed")
        self.assertEqual(0, cg.RECEIPT["owed"])


class _GuardedLive(dict):
    """A _LIVE whose every read-of-all and write records whether _LOCK was held."""

    def __init__(self):
        super().__init__()
        self.violations = []

    def _check(self, what):
        try:
            owned = cg._LOCK._is_owned()
        except Exception:
            owned = None
        if owned is False:
            self.violations.append(what)

    def items(self):
        self._check("items")
        return super().items()

    def values(self):
        self._check("values")
        return super().values()

    def __setitem__(self, k, v):
        self._check("set %s" % k)
        return super().__setitem__(k, v)

    def pop(self, k, *a):
        self._check("pop %s" % k)
        return super().pop(k, *a)


class TheLedgerIsWrittenUnderTheLock(_World):

    def test_every_walk_and_write_of_the_records_holds_the_lock(self):
        live = _GuardedLive()
        with mock.patch.object(cg, "_LIVE", live):
            cg.spawn("law-a", ["x"], popen=self.popen([9990851, 9990853]), kill=self.kill)
            cg.spawn("law-b", ["x"], popen=self.popen([9990855]), kill=self.kill)
            cg.census(alive=self.alive)
            cg.watchdog_tick(rows_fn=lambda: [], kill=self.kill, alive=self.alive, birth=self.birth, now_ms=1)
            cg.end("law-a", kill=self.kill, wait_s=0)
            cg._ledger_write()
        self.assertEqual([], live.violations,
                         "the records were walked or written OUTSIDE the lock: %r - a spawn on another thread "
                         "(the agent warms its pool from reader threads) raises 'dictionary changed size during "
                         "iteration' inside the ledger write, the write is swallowed, and the ledger goes stale"
                         % live.violations)


class APostExecvConsoleAdoptsItsPreviousLife(_World):
    """REG-1551 - os.execv keeps the pid and the creation time, empties the door, and the previous life's ledger file
    sits under OUR name where _ledger_read_others never looks."""

    def _previous_life(self, pborn, pid=9990901):
        os.makedirs(cg.LEDGER_DIR, exist_ok=True)
        with io.open(cg._ledger_path(), "w", encoding="utf-8") as fh:
            json.dump({"parent": os.getpid(), "parentBirth": pborn, "expect": {"vision": [0, 2]},
                       "children": {"capture": {"role": "capture", "pid": pid, "birth": 1000, "parent": os.getpid(),
                                                "parentBirth": pborn, "session": False, "argv0": "powershell.exe"}}}, fh)
        cg._ADOPTED[0] = False

    def test_the_previous_lifes_capture_is_ended_before_the_next_one_starts(self):
        self._previous_life(100)                        # _SELF_BIRTH is 100 in this fixture: the same process
        self.live.add(9990901)
        self.births[9990901] = 1000
        cg.spawn("capture", ["x"], popen=self.popen([9990903]), kill=self.kill)
        self.assertEqual([9990901], self.killed, "THE PREVIOUS LIFE'S CAPTURE SURVIVED THE FIRST SPAWN AFTER THE "
                                                 "RELAUNCH - two captures film, the shape of REG-1502")
        self.assertEqual(1, cg.RECEIPT["adopted"])
        self.assertEqual(9990903, cg.record_of("capture")["pid"])

    def test_a_file_of_another_process_that_held_this_pid_is_not_adopted(self):
        self._previous_life(50)                         # born at another time: a previous BOOT's console, not us
        self.live.add(9990901)
        self.births[9990901] = 1000
        cg.census(alive=self.alive)
        self.assertIsNone(cg.record_of("capture"), "a stranger's ledger under our pid was adopted")
        self.assertEqual(0, cg.RECEIPT["adopted"])

    def test_an_adopted_record_whose_pid_was_reused_is_dropped_not_killed(self):
        self._previous_life(100)
        self.live.add(9990901)
        self.births[9990901] = 5000
        r = cg.end("capture", kill=self.kill)
        self.assertEqual([], self.killed, "an adopted record's reused pid was killed")
        self.assertIn("reused", r["say"])

    def test_the_first_ledger_write_of_a_life_adopts_before_it_overwrites(self):
        self._previous_life(100)
        self.live.add(9990901)
        self.births[9990901] = 1000
        cg.expect("ocr", 0, 1)                          # tv_diablo declares at import: the first write of the life
        with io.open(cg._ledger_path(), encoding="utf-8") as fh:
            body = json.load(fh)
        self.assertIn("capture", body["children"], "the first write of the new life overwrote the previous life's "
                                                    "record before anything read it")


RED_PROOF = [
    {
        "why": "2026-09-30 - with /proc, a pid it does not list falls through to `ps` again: a console law counts that as a second capture (CI red, his Mac green)",
        "file": "tv/child_guard.py",
        "find": "        except Exception:\n            pass\n        return None\n    try:\n",
        "replace": "        except Exception:\n            pass\n    try:\n",
        "matches": 1,
    },
    {
        "why": "#83 - POSIX: the child no longer leads its own session, so a restart kills the head and the grandchild survives",
        "file": "tv/child_guard.py",
        "find": "    if not IS_WIN:\n        kw.setdefault(\"start_new_session\", True)\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#83 - a pid born at another time (reused by a newer process) is ended as if it were ours",
        "file": "tv/child_guard.py",
        "find": "    if _same_birth(rec.get(\"birth\"), now_birth):\n        return True, \"pid %s alive, born when recorded\" % pid\n",
        "replace": "    if True:\n        return True, \"pid %s alive, born when recorded\" % pid\n",
        "matches": 1,
    },
    {
        "why": "#83 - an UNKNOWN birth ends the pid on a guess",
        "file": "tv/child_guard.py",
        "find": "    if now_birth is None:\n        return False,",
        "replace": "    if False:\n        return False,",
        "matches": 1,
    },
    {
        "why": "#83 - Windows: the job is created without KILL_ON_JOB_CLOSE, so the tree outlives the handle",
        "file": "tv/child_guard.py",
        "find": "        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE\n",
        "replace": "        info.BasicLimitInformation.LimitFlags = 0\n",
        "matches": 1,
    },
    {
        "why": "#83 - Windows: end() closes the job handle without terminating the job (a closed handle kills only because of the flag; the law wants the explicit end)",
        "file": "tv/child_guard.py",
        "find": "                k.TerminateJobObject(job, 1)\n                k.CloseHandle(job)\n",
        "replace": "                k.CloseHandle(job)\n",
        "matches": 1,
    },
    {
        "why": "REG-1550 - a live parent's unrecorded child is ENDED again ('unrecorded child of ours'): the console ends its own closer OCR worker and warm reader",
        "file": "tv/child_guard.py",
        "find": "            bypass.append((pid, role, ppid,\n                           \"a live parent of ours (pid %s) spawned it outside the door - said, never ended\" % ppid))\n",
        "replace": "            to_end.append((pid, role, \"unrecorded child of ours (parent %s)\" % ppid))\n",
        "matches": 1,
    },
    {
        "why": "REG-1550 - the table's births are no longer re-read through the records' reader (the DST hour ends a live agent's reader)",
        "file": "tv/child_guard.py",
        "find": "            rows = _same_reader(rows, birth)\n",
        "replace": "            rows = list(rows)\n",
        "matches": 1,
    },
    {
        "why": "REG-1550 - a live parent whose birth cannot be read now reads as GONE and its children are ended",
        "file": "tv/child_guard.py",
        "find": "    if nb is None:\n        return \"unknown\"\n",
        "replace": "    if nb is None:\n        return \"gone\"\n",
        "matches": 1,
    },
    {
        "why": "REG-1550 - a dead parent's child is ended although the table shows its pid running a stranger's command",
        "file": "tv/child_guard.py",
        "find": "                if role_of_command(row[3]) is None:\n",
        "replace": "                if False:\n",
        "matches": 1,
    },
    {
        "why": "REG-1550 - an UNKNOWN table removes a dead parent's file with its child never judged",
        "file": "tv/child_guard.py",
        "find": "not judged this pass\" % parent))\n                    left += 1\n                    continue\n",
        "replace": "not judged this pass\" % parent))\n                    continue\n",
        "matches": 1,
    },
    {
        "why": "REG-1550 - the kill no longer notices a pid reused since the table was read",
        "file": "tv/child_guard.py",
        "find": "        if not _same_birth(born, now_birth):\n",
        "replace": "        if False:\n",
        "matches": 1,
    },
    {
        "why": "REG-1550 - a birth UNKNOWN at the kill fires the kill anyway",
        "file": "tv/child_guard.py",
        "find": "        if born is None or now_birth is None:\n            kept.append((pid, role, why + \" - birth UNKNOWN at the kill, never ended on a guess\"))\n            return None\n",
        "replace": "        if False:\n            return None\n",
        "matches": 1,
    },
    {
        "why": "REG-1550 - the OCR signature is `--worker` again, a substring of `--workers=3`",
        "file": "tv/child_guard.py",
        "find": "    \"ocr\": {\"expect\": [0, 1], \"scope\": \"parent\", \"signature\": ((\"ocr_mac --worker\", \"ocr_win.ps1\"),),\n",
        "replace": "    \"ocr\": {\"expect\": [0, 1], \"scope\": \"parent\", \"signature\": (\"--worker\",),\n",
        "matches": 1,
    },
    {
        "why": "REG-1550 - the stop kills a lease pid without the table showing it is a capture (a reused pid = a stranger's tree)",
        "file": "tv/control_app.py",
        "find": "            _v = _lease_pid_is_a_capture(pid)\n            if _v:\n",
        "replace": "            _v = True\n            if _v:\n",
        "matches": 1,
    },
    {
        "why": "REG-1550 - an unverified lease pid is watched for surviving as if it had been killed (a stranger counted as a capture that outlived its kill)",
        "file": "tv/control_app.py",
        "find": "    if pid and killed and not _gone_within(pid, _pid_alive, CAP_KILL_SETTLE_S):\n",
        "replace": "    if pid and not _gone_within(pid, _pid_alive, CAP_KILL_SETTLE_S):\n",
        "matches": 1,
    },
    {
        "why": "REG-1550 - the doctor row no longer says what runs outside the door",
        "file": "tv/control_app.py",
        "find": "    bypass = wd.get(\"bypass\") or []\n    if bypass:\n",
        "replace": "    bypass = []\n    if bypass:\n",
        "matches": 1,
    },
    {
        "why": "REG-1551 - the census grades a parent-scoped family across parents against one ceiling (console reader + agent reader = over)",
        "file": "tv/child_guard.py",
        "find": "            f[\"expected\"] = [sum(int(o[\"expected\"][0]) for o in owners.values()),\n                             sum(int(o[\"expected\"][1]) for o in owners.values())]\n",
        "replace": "            f[\"expected\"] = [0, max(int(o[\"expected\"][1]) for o in owners.values())]\n",
        "matches": 1,
    },
    {
        "why": "REG-1551 - one owner over its own declared ceiling is not flagged",
        "file": "tv/child_guard.py",
        "find": "        over = ([] if scope == \"checkout\" else\n",
        "replace": "        over = ([] if True else\n",
        "matches": 1,
    },
    {
        "why": "REG-1551 - the census no longer counts what the watchdog saw outside the door",
        "file": "tv/child_guard.py",
        "find": "    for row in (WATCHDOG.get(\"bypass\") or []):\n",
        "replace": "    for row in []:\n",
        "matches": 1,
    },
    {
        "why": "REG-1551 - a survivor that finally leaves stays owed for ever",
        "file": "tv/child_guard.py",
        "find": "        finally:\n            _survivor_left(getattr(pr, \"pid\", None))\n",
        "replace": "        finally:\n            pass\n",
        "matches": 1,
    },
    {
        "why": "REG-1551 - the receipt's debt is remembered, never re-asked",
        "file": "tv/child_guard.py",
        "find": "                if alive(pid):\n                    keep.append(pid)\n            except Exception:\n                keep.append(pid)\n",
        "replace": "                keep.append(pid)\n            except Exception:\n                keep.append(pid)\n",
        "matches": 1,
    },
    {
        "why": "REG-1551 - the ledger write walks the records outside the lock",
        "file": "tv/child_guard.py",
        "find": "        with _LOCK:                     # REG-1551 - a spawn on another thread mutates _LIVE; snapshot under the lock\n            body = {",
        "replace": "        if True:\n            body = {",
        "matches": 1,
    },
    {
        "why": "REG-1551 - a post-execv console adopts nothing: the previous life's capture films beside the next one",
        "file": "tv/child_guard.py",
        "find": "    if _ADOPTED[0]:\n        return 0\n    _ADOPTED[0] = True\n",
        "replace": "    if True:\n        return 0\n    _ADOPTED[0] = True\n",
        "matches": 1,
    },
    {
        "why": "REG-1551 - a stranger's ledger under our pid (a previous boot) is adopted as ours",
        "file": "tv/child_guard.py",
        "find": "        if body.get(\"parentBirth\") is None or not _same_birth(body.get(\"parentBirth\"), _self_birth()):\n            return 0\n",
        "replace": "        if False:\n            return 0\n",
        "matches": 1,
    },
    {
        "why": "#83 - a parent born after its child (a reused parent pid) reads as the child's live console",
        "file": "tv/child_guard.py",
        "find": "            if pborn is not None and pborn > born + BIRTH_TOL_S:\n",
        "replace": "            if False:\n",
        "matches": 1,
    },
    {
        "why": "#83 - an unreadable process table owes 0 instead of UNKNOWN",
        "file": "tv/child_guard.py",
        "find": "                        owed=(len(failed) if not unknown else None), ended=ended, kept=kept, failed=failed,\n",
        "replace": "                        owed=len(failed), ended=ended, kept=kept, failed=failed,\n",
        "matches": 1,
    },
    {
        "why": "#83 - a family over its ceiling reads OK on the census",
        "file": "tv/child_guard.py",
        "find": "        elif f[\"alive\"] > hi or over:\n            f[\"ok\"] = False\n",
        "replace": "        elif False:\n            f[\"ok\"] = False\n",
        "matches": 1,
    },
    {
        "why": "#83 - under the floor a secondary worker is still allowed",
        "file": "tv/child_guard.py",
        "find": "    if int(free) < floor:\n        RAM[\"refused\"]",
        "replace": "    if False:\n        RAM[\"refused\"]",
        "matches": 1,
    },
    {
        "why": "#83 - UNKNOWN free RAM refuses the spawn (a meter that cannot be read silences the lanes for ever)",
        "file": "tv/child_guard.py",
        "find": "    if free is None:\n        RAM[\"say\"] = \"free RAM UNKNOWN",
        "replace": "    if free is None:\n        return False, \"guess\"\n    if False:\n        RAM[\"say\"] = \"free RAM UNKNOWN",
        "matches": 1,
    },
    {
        "why": "#83 - the doctor's one_of_each row reads an UNKNOWN watchdog table as OK",
        "file": "tv/control_app.py",
        "find": "    wd_unknown = wd.get(\"lastTs\") is not None and bool(wd.get(\"unknown\"))\n",
        "replace": "    wd_unknown = False\n",
        "matches": 1,
    },
    {
        "why": "#83 - the console's capture is spawned outside the door: a capture the lamp lost survives the next start",
        "file": "tv/control_app.py",
        "find": "        _capture_proc = _child_guard.spawn(\n            \"capture\",\n",
        "replace": "        _capture_proc = subprocess.Popen(\n",
        "matches": 1,
    },
    {
        "why": "#83 - the stop no longer forgets the role, so the next spawn 'ends' a pid that is gone and the record lies",
        "file": "tv/control_app.py",
        "find": "        _r = _child_guard.end(\"capture\", kill=lambda p: _kill_pid(p, force=True), alive=_pid_alive, wait_s=0)\n        killed = _r.get(\"killedPid\") == pid\n",
        "replace": "        _r = {}\n        killed = False\n",
        "matches": 1,
    },
    {
        "why": "#83 - nothing runs the watchdog off the rescue loop",
        "file": "tv/control_app.py",
        "find": "                _child_guard_tick()         # #83",
        "replace": "                pass                        # #83",
        "matches": 1,
    },
    {
        "why": "#83 - the reader's claude is spawned outside the door (its tree is never ended on a restart)",
        "file": "tv/tv_diablo.py",
        "find": "        self.p = _child_guard.spawn(self.role,\n",
        "replace": "        self.p = subprocess.Popen(\n",
        "matches": 1,
    },
    {
        "why": "#83 - the stall reader stays warm (~400 MB) after its sweep",
        "file": "tv/tv_diablo.py",
        "find": "                    _stall_worker_release()     # #83",
        "replace": "                    pass                        # #83",
        "matches": 1,
    },
    {
        "why": "#83 - the stall drain fires a second claude regardless of free RAM",
        "file": "tv/tv_diablo.py",
        "find": "    if not ram_ok:\n        return False\n    return True\n",
        "replace": "    return True\n",
        "matches": 1,
    },
    {
        "why": "#83 - the live glue never asks the RAM policy",
        "file": "tv/tv_diablo.py",
        "find": "        ram_ok=lambda: _child_guard.secondary_spawn_allowed()[0],      # #83 — asked last, cached 5 s\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#83 - the OCR worker starts under the RAM floor",
        "file": "tv/tv_diablo.py",
        "find": "            if not _ram_ok:\n                self.ok = False\n",
        "replace": "            if False:\n                self.ok = False\n",
        "matches": 1,
    },
    {
        "why": "#83 - the OCR worker is spawned outside the door",
        "file": "tv/tv_diablo.py",
        "find": "            self.p = _child_guard.spawn(\"ocr\",\n",
        "replace": "            self.p = subprocess.Popen(\n",
        "matches": 1,
    },
    {
        "why": "#83 - a deaf reader is buried by p.kill() alone: the head dies, its helpers (the pipe's read end) live on",
        "file": "tv/tv_diablo.py",
        "find": "                    _bury_worker(p, role=self.role)     # not draining its input",
        "replace": "                    _bury_worker(p)     # not draining its input",
        "matches": 1,
    },
    {
        "why": "#83 - _bury_worker ignores the role it was handed and never reaches the door",
        "file": "tv/tv_diablo.py",
        "find": "    ended = False\n    if role:\n",
        "replace": "    ended = False\n    if False:\n",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
