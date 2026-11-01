# -*- coding: utf-8 -*-
"""REG-1502 — ONE CAPTURE PER CONSOLE, AND A CAPTURE NOBODY OWNS LEAVES.

His words, 2026-09-29: *"my boosteroid app keeps crashing on me! something is related to the console i think"*.
MEASURED on the ALT that afternoon: FIVE capture_win.ps1 alive at once - four children of one console (10:23, 10:44,
14:31, 14:42) and one from the day before (22,052 s of CPU) - each PrintWindow-ing his Boosteroid window every 400 ms.
Windows logged a low-virtual-memory condition every ~5 min; dwm.exe died of memory exhaustion (0xc00001ad) eight
times in an hour and Boosteroid hung and crashed with it. The console's stop was a taskkill whose result nobody read,
and the spawn's "is one running?" check and its pid write were not atomic.

Four joints, each DRIVEN through the real function with the Windows edges stubbed (never a real process, never the
live tv/ pid file):
  · the spawn: two starts at once spawn ONE capture, and the capture is told which console started it;
  · the stop: a kill that did not land is counted and said, never assumed;
  · the boot sweep: ends a capture only when it is not ours AND its console is gone; an unreadable process table
    ends nothing and says UNKNOWN;
  · the capture itself (capture_win.ps1 Get-LeaseVerdict): leaves when its lease is withdrawn or handed
    on. v3850 (Elad 18:03 2026-10-31) — a dead console, or a reused console pid, is not a reason to leave
    while the lease still names this capture. Run in real PowerShell wherever one exists (Windows, CI),
    skipped by name on a Mac without one.

REG-1509 — the review of v3524 found six more, each now a driven case here:
  · THE STOP AND THE LAMP RACED. End Session stopped the capture while the mode still read 'live'; a status poll in
    between ran the lamp, which restarted a capture AFTER the stop - one holding its own valid lease, filming with no
    session (the reviewer drove it: 30/30 threaded trials). Replayed below through the real stop_agent,
    _force_kill_all_agents, _capture_health and _start_capture, in the three orders it can land in;
  · the sweep's query matched ITSELF (its -Command text holds the script path), so found/kept were one too high;
  · a console pid REUSED by a newer process read as the console being alive, so a day-old orphan was kept for good;
  · an UNKNOWN sweep read OK on the doctor, and a stop survivor warned forever after it had left;
  · a kill was judged microseconds after taskkill, and TerminateProcess is asynchronous;
  · this law's own spawn ran the unmocked priority step on fake pid 7001 - on Windows a pid's low two bits are
    ignored on lookup, so that opened pid 7000, which could be his game. The step is stubbed now, and a trap proves
    no priority call leaves the law (an odd fake pid alone would NOT have been safe).
RED_PROOF below.
"""
import calendar
import contextlib
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
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
import control_app as ca  # noqa: E402
import child_guard as _cg  # noqa: E402  - #83: the spawn door the capture now goes through


class _FakeProc(object):
    def __init__(self, pid):
        self.pid = pid

    def poll(self):
        return None


class _LiveProc(object):
    """A capture that is alive while its pid is in `live` - never a real process."""

    def __init__(self, pid, live):
        self.pid, self._live = pid, live

    def poll(self):
        return None if self.pid in self._live else 1


class _TrapPsutil(object):
    """Stands in for psutil while a law spawns. Anything that reaches it is the priority step touching a pid; it
    records the pid and does nothing, so even an unstubbed step never falls through to the ctypes OpenProcess path."""
    BELOW_NORMAL_PRIORITY_CLASS = 0x00004000

    def __init__(self):
        self.touched = []

    def Process(self, pid):
        self.touched.append(pid)
        return self

    def nice(self, *_a):
        return None


class _World(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="one_capture_")
        self.pidfile = os.path.join(self.d, "control_capture.pid")
        self.log = io.StringIO()
        self.saved = (ca._capture_proc, dict(ca._CAP_STOP), dict(ca._CAP_SWEEP))
        ca._capture_proc = None
        # #83 — the door remembers the capture the PREVIOUS case spawned (a fake whose poll() says alive for ever),
        # and would end it - through the unstubbed taskkill, which the patched Popen then counts as a spawn. Each
        # case starts with an empty door and its own ledger dir; never the process's real one.
        self.cg_saved = (_cg.LEDGER_DIR, dict(_cg._LIVE))
        _cg._LIVE.clear()
        _cg.LEDGER_DIR = os.path.join(self.d, "child_guard")

    def tearDown(self):
        _cg._LIVE.clear()
        _cg._LIVE.update(self.cg_saved[1])
        _cg.LEDGER_DIR = self.cg_saved[0]
        ca._capture_proc = self.saved[0]
        ca._CAP_STOP.clear()
        ca._CAP_STOP.update(self.saved[1])
        ca._CAP_SWEEP.clear()
        ca._CAP_SWEEP.update(self.saved[2])
        shutil.rmtree(self.d, ignore_errors=True)


class TheSpawnIsOneAtATime(_World):

    def _start_twice(self):
        spawned = []
        reniced = []
        self.trap = _TrapPsutil()
        pids = iter((7001, 7002, 7003))          # fake: they reach no OS call - _pid_alive and the priority step are stubbed

        def popen(args, **kw):
            time.sleep(0.3)                     # the window the race lived in
            p = _FakeProc(next(pids))
            spawned.append((p.pid, dict(kw.get("env") or {})))
            return p

        def alive(pid):
            return pid in [s[0] for s in spawned]

        with mock.patch.object(ca, "IS_WIN", True), \
                mock.patch.object(ca, "CAP_PID_PATH", self.pidfile), \
                mock.patch.object(ca.os.path, "isfile", lambda p: True if p == ca.CAPTURE_PS1 else os.path.exists(p)), \
                mock.patch.object(ca, "_stub_never_films", lambda **k: False), \
                mock.patch.object(ca, "_capture_off", lambda *a, **k: False), \
                mock.patch.object(ca, "_pid_alive", alive), \
                mock.patch.dict(sys.modules, {"psutil": self.trap}), \
                mock.patch.object(ca, "_lower_capture_priority", lambda pid: reniced.append(pid)), \
                mock.patch.object(ca.subprocess, "Popen", popen):
            ts = [threading.Thread(target=ca._start_capture, args=({"PATH": "x"}, self.log)) for _ in range(2)]
            for t in ts:
                t.start()
            for t in ts:
                t.join(10)
        self.reniced = reniced
        return spawned

    def test_two_starts_at_once_spawn_one_capture(self):
        spawned = self._start_twice()
        self.assertEqual(1, len(spawned),
                         "two starts at once spawned %d captures - the second pid write orphans the first" % len(spawned))

    def test_the_capture_is_told_which_console_started_it(self):
        spawned = self._start_twice()
        self.assertTrue(spawned)
        self.assertEqual(str(os.getpid()), spawned[0][1].get("TV_CONSOLE_PID"),
                         "the capture does not know its console - a crashed console leaves it filming forever")

    def test_the_law_never_reprioritises_a_real_process(self):
        # REG-1509 — the spawn lowers ITS capture's priority through one stubbed step, and nothing in this law reaches
        # psutil (or, behind it, OpenProcess) with a fake pid. On Windows 7001 opens pid 7000: that could be D2R.
        spawned = self._start_twice()
        self.assertEqual([], self.trap.touched,
                         "the law's spawn reached the real priority step with fake pid(s) %s - on Windows that "
                         "reprioritises whatever process holds pid & ~3" % self.trap.touched)
        self.assertEqual([spawned[0][0]], self.reniced, "the spawn no longer lowers its capture's priority (v1441)")


class TheStopChecksItsKill(_World):

    def _stop(self, alive, settle_s=0.3):
        ca._capture_proc = _FakeProc(8100)
        with io.open(self.pidfile, "w") as fh:
            fh.write("8100")
        with mock.patch.object(ca, "CAP_PID_PATH", self.pidfile), \
                mock.patch.object(ca, "CAP_KILL_SETTLE_S", settle_s), \
                mock.patch.object(ca, "_kill_pid", lambda pid, force=False: None), \
                mock.patch.object(ca, "_pid_alive", alive), \
                mock.patch.object(ca, "_log_fp", self.log):
            ca._CAP_STOP.update(survived=0, last=None)
            ca._stop_capture()

    def test_a_kill_that_did_not_land_is_counted_and_said(self):
        self._stop(alive=lambda pid: True)
        self.assertEqual(1, ca._CAP_STOP["survived"], "a capture that outlived its kill was assumed dead")
        self.assertIn("8100", (ca._CAP_STOP.get("last") or {}).get("say", ""))
        self.assertIn("outlived its kill", self.log.getvalue())
        self.assertFalse(os.path.exists(self.pidfile), "the lease was not withdrawn - the survivor would never leave")

    def test_a_kill_that_landed_says_nothing(self):
        self._stop(alive=lambda pid: False)
        self.assertEqual(0, ca._CAP_STOP["survived"])
        self.assertEqual("", self.log.getvalue())

    def test_a_kill_that_lands_a_moment_late_is_not_a_survivor(self):
        # REG-1509 — TerminateProcess is asynchronous: the pid still reads alive for a moment after taskkill returns.
        answers = [True, True]                  # alive for the first two asks, then gone - a kill that landed late

        def alive(pid):
            return answers.pop(0) if answers else False
        self._stop(alive=alive, settle_s=2.0)
        self.assertEqual(0, ca._CAP_STOP["survived"],
                         "a kill that landed ~0.2 s late was counted as one that did not land - the doctor would warn "
                         "about a pid that is gone")
        self.assertEqual([], answers, "premise: the stop never asked again, so it never saw the late death")


class TheDoctorRowSaysWhatIsTrueNow(_World):
    """REG-1509 — the one_capture row: UNKNOWN is not OK, and a survivor warns only while it lives."""

    def _row(self, sweep=None, stop=None, alive=lambda p: False, uptime_s=0):
        ca._CAP_SWEEP.clear()
        ca._CAP_SWEEP.update({"ran": None, "found": None, "killed": [], "kept": [], "failed": [],
                              "say": "not asked yet"})
        ca._CAP_SWEEP.update(sweep or {})
        ca._CAP_STOP.clear()
        ca._CAP_STOP.update({"survived": 0, "last": None})
        ca._CAP_STOP.update(stop or {})
        # uptime 0 is still inside the boot minute. A Windows process older than that minute,
        # whose sweep never ran, is the other law's case, not these.
        return ca._one_capture_check(alive=alive, uptime_s=uptime_s)

    def test_the_doctor_carries_this_row(self):
        self.assertIn("_one_capture_check", ca.doctor_payload.__code__.co_names,
                      "doctor_payload no longer asks the one_capture row")

    def test_a_sweep_that_could_not_ask_the_table_is_not_ok(self):
        row = self._row(sweep={"ran": 1, "found": None,
                               "say": "UNKNOWN - the process table could not be asked; nothing was ended"})
        self.assertFalse(row["ok"], "an UNKNOWN sweep read OK - orphans could film behind a green row: %r" % row)
        self.assertIn("UNKNOWN", row["detail"])
        self.assertIn("Restart TV DIABLO to ask again", row.get("fix") or "")

    def test_a_sweep_that_never_ran_is_fine_and_a_mac_never_runs_one(self):
        young = self._row(uptime_s=0)
        self.assertTrue(young["ok"], "a sweep that has not run yet, inside the boot minute, is not a fault")
        self.assertNotIn("boot sweep never ran", young["detail"])
        with mock.patch.object(ca, "IS_WIN", False):
            ca._sweep_orphan_captures()         # the Mac's own path: says why, runs nothing
            self.assertIsNone(ca._CAP_SWEEP.get("ran"))
            mac = ca._one_capture_check(alive=lambda p: False, uptime_s=4000)
        self.assertTrue(mac["ok"], "a Mac's one_capture row warned: %r" % mac)
        self.assertNotIn("boot sweep never ran", mac["detail"])

    def test_a_survivor_warns_only_while_it_is_alive(self):
        stop = {"survived": 1, "last": {"pid": 8100, "ts": 1, "say": "capture pid 8100 outlived its kill"}}
        live = self._row(stop=stop, alive=lambda p: p == 8100)
        self.assertFalse(live["ok"], "a capture that outlived its kill and still lives read OK")
        self.assertIn("Task Manager", live.get("fix") or "")
        gone = self._row(stop=stop, alive=lambda p: False)
        self.assertTrue(gone["ok"], "the row kept warning about pid 8100 after it left: %r" % gone)
        self.assertIn("has since left", gone["detail"])

    def test_an_orphan_that_would_not_end_warns_only_while_it_is_alive(self):
        sweep = {"ran": 1, "found": 1, "failed": [32], "say": "1 capture script(s) of this checkout: ended 0 orphan(s)"}
        self.assertFalse(self._row(sweep=sweep, alive=lambda p: p == 32)["ok"])
        self.assertTrue(self._row(sweep=sweep, alive=lambda p: False)["ok"],
                        "an orphan that left after the sweep kept the row warning forever")


class TheBootSweepEndsOnlyOrphans(_World):

    def test_the_rule(self):
        live = {10, 20}
        end, kept = ca.orphan_captures([(1, 10), (2, 99), (3, 0), (4, 20), (5, 99)], mine={4}, alive=lambda p: p in live)
        self.assertEqual([2, 3, 5], end, "the sweep ended the wrong captures")
        self.assertEqual([1, 4], [k for k, _w in kept])

    def test_a_console_pid_reused_by_a_newer_process_is_gone(self):
        # REG-1509 — (pid, parent, born_ms, parent_born_ms). Every parent pid here is ALIVE; only 51's was born after it.
        end, kept = ca.orphan_captures([(51, 900, 1000, 5000),       # parent born AFTER the capture: a reused pid
                                        (52, 901, 1000, 500),        # parent born before it: its real console
                                        (53, 902, 1000, None),       # parent's birth unknown: decides nothing
                                        (54, 903, None, 5000)],      # capture's birth unknown: decides nothing
                                       mine=set(), alive=lambda p: True)
        self.assertEqual([51], end, "a capture whose console pid now belongs to a NEWER process was kept - a day-old "
                                    "orphan films for good once Windows hands its console's pid to anything")
        self.assertEqual([52, 53, 54], [k for k, _w in kept])

    def test_the_sweep_ends_what_the_rule_says_and_says_what_would_not_end(self):
        gone = set()
        with mock.patch.object(ca, "CAP_PID_PATH", self.pidfile), mock.patch.object(ca, "_log_fp", self.log):
            st = ca._sweep_orphan_captures(rows_fn=lambda: [(31, 900), (32, 901), (33, 555)],
                                           kill=lambda pid: gone.add(pid) if pid != 32 else None,
                                           alive=lambda pid: pid == 555 or (pid in (31, 32, 33) and pid not in gone),
                                           now_ms=1, settle_s=0.3)
        self.assertEqual([31], st["killed"])
        self.assertEqual([32], st["failed"], "a capture that would not end was reported as ended")
        self.assertEqual([33], st["kept"], "a capture whose console lives was ended")
        self.assertIn("would NOT end", st["say"])

    def test_a_sweep_kill_that_lands_a_moment_late_is_ended_not_failed(self):
        # REG-1509 — the sibling of the stop's check: the same asynchronous TerminateProcess.
        asked = {"n": 0}

        def alive(pid):
            if pid == 41:
                asked["n"] += 1
                return asked["n"] <= 2          # still dying for two asks, then gone
            return False                        # its console (900) is gone
        with mock.patch.object(ca, "CAP_PID_PATH", self.pidfile), mock.patch.object(ca, "_log_fp", self.log):
            st = ca._sweep_orphan_captures(rows_fn=lambda: [(41, 900)], kill=lambda pid: None, alive=alive,
                                           now_ms=1, settle_s=2.0)
        self.assertEqual([41], st["killed"], "a kill that landed ~0.2 s late was reported as one that would not end")
        self.assertEqual([], st["failed"])

    def test_an_unreadable_process_table_ends_nothing(self):
        killed = []
        st = ca._sweep_orphan_captures(rows_fn=lambda: None, kill=killed.append, alive=lambda p: True, now_ms=1)
        self.assertEqual([], killed)
        self.assertIsNone(st["found"], "an unreadable table was reported as 'found 0'")
        self.assertIn("UNKNOWN", st["say"])

    def test_the_rescue_loop_runs_it_once_and_status_and_the_doctor_carry_it(self):
        import inspect
        loop = inspect.getsource(ca._console_rescue_loop)
        self.assertIn("== CAPTURE_SWEEP_TICK", loop, "nothing runs the boot sweep")
        self.assertIn("_sweep_orphan_captures()", loop)
        src = inspect.getsource(ca)
        self.assertIn('"captureSweep": dict(_CAP_SWEEP)', src)
        self.assertIn('return _chk("one_capture", not _c_bad', inspect.getsource(ca._one_capture_check))


class _QueryProc(object):
    """The sweep's PowerShell query, answered from a string - never a real process. Serves both _capture_rows'
    Popen/communicate and subprocess.run's context-manager use of the same Popen."""

    def __init__(self, pid, out, rc=0):
        self.pid, self._out, self.returncode, self.args = pid, out, rc, None

    def communicate(self, input=None, timeout=None):
        return self._out, ""

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        return self.returncode

    def kill(self):
        return None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class TheSweepsQueryCountsOnlyCaptures(unittest.TestCase):
    """REG-1509 — what _capture_rows hands the sweep, driven with the query answered from a string."""

    def _rows(self, out, rc=0, qpid=9001):
        calls = []

        def popen(args, **kw):
            calls.append(list(args))
            return _QueryProc(qpid, out, rc)
        with mock.patch.object(ca.subprocess, "Popen", popen):
            rows = ca._capture_rows(timeout=5)
        return rows, calls

    def test_the_query_leaves_itself_out_and_carries_birth_times(self):
        out = ("9001 4000 1790676000000 1790670000000\r\n"      # the query itself: its -Command text holds the path
               "5001 5000 1790676000000 1790683200000\r\n"
               "6001 6000 1790676000000 0\r\n"
               "WARNING: a line that is not a row\r\n")
        rows, calls = self._rows(out)
        self.assertNotIn(9001, [r[0] for r in (rows or [])],
                         "the sweep counted its own query as a capture - found/kept one too high, and his one real "
                         "capture reads as two")
        self.assertEqual([(5001, 5000, 1790676000000, 1790683200000), (6001, 6000, 1790676000000, None)], rows,
                         "the rows lost their birth times - a reused console pid cannot be told from a live console")
        self.assertEqual(ca._capture_query_ps(ca.CAPTURE_PS1), calls[0][-1],
                         "the query that runs is not the one this law proves")

    def test_a_query_that_fails_is_unknown_never_empty(self):
        rows, _c = self._rows("", rc=1)
        self.assertIsNone(rows, "a failed query was handed back as 'no captures'")


def _powershell():
    for exe in ("powershell.exe", "pwsh", "powershell"):
        p = shutil.which(exe)
        if p:
            return p
    return None


def _ps_lit(s):
    return "'" + s.replace("'", "''") + "'"


class TheQueryInRealPowerShell(unittest.TestCase):
    """REG-1509 — _capture_query_ps run in real PowerShell against a stubbed Get-CimInstance (a function shadows the
    cmdlet, so no real process table is read). Proves the PowerShell half: $PID left out, birth times printed.
    Skipped by name where there is no PowerShell (his Mac); runs on CI's pwsh and on Windows."""

    PATH = "C:\\Users\\Dean\\d2r bible\\tv\\capture_win.ps1"

    def test_the_query_against_a_stubbed_process_table(self):
        ps = _powershell()
        if not ps:
            self.skipTest("no PowerShell on this machine - the query is proven where it runs (Windows, CI)")
        cmd = _ps_lit("powershell.exe -NoProfile -File " + self.PATH)
        self_cmd = _ps_lit("powershell.exe -NoProfile -Command $t = '" + self.PATH + "'; Get-CimInstance ...")
        stub = "\n".join([
            "function New-StubRow([string]$name, [long]$id, [long]$parentId, [string]$cmd, [int]$hour) {",
            "  $d = $null",
            "  if ($hour -ge 0) { $d = [DateTime]::new(2026, 9, 29, $hour, 0, 0, [DateTimeKind]::Utc) }",
            "  return [pscustomobject]@{ Name = $name; ProcessId = [uint32]$id; ParentProcessId = [uint32]$parentId; "
            "CommandLine = $cmd; CreationDate = $d }",
            "}",
            "$script:StubRows = @(",
            "  (New-StubRow 'powershell.exe' $PID 4000 %s 10)," % self_cmd,
            "  (New-StubRow 'powershell.exe' 5001 5000 %s 10)," % cmd,
            "  (New-StubRow 'python.exe' 5000 4 'python control_app.py' 12),",
            "  (New-StubRow 'powershell.exe' 6001 6000 %s 10)," % cmd,
            "  (New-StubRow 'python.exe' 6000 4 'python control_app.py' 9),",
            "  (New-StubRow 'powershell.exe' 7001 7000 %s 10)," % cmd,
            "  (New-StubRow 'powershell.exe' 8001 6000 'powershell.exe -File C:\\other\\script.ps1' 10),",
            "  (New-StubRow 'powershell.exe' 8003 6000 '' 10)",
            ")",
            "function Get-CimInstance {",
            "  [CmdletBinding()]",
            "  param([Parameter(Position = 0)][string]$ClassName, [string]$Filter)",
            "  if ($Filter -match '^ProcessId=(\\d+)$') {",
            "    $id = [uint32]$Matches[1]",
            "    return @($script:StubRows | Where-Object { $_.ProcessId -eq $id })",
            "  }",
            "  return @($script:StubRows | Where-Object { $_.Name -eq 'powershell.exe' })",
            "}",
        ])
        d = tempfile.mkdtemp(prefix="capture_query_law_")
        try:
            script = os.path.join(d, "q.ps1")
            io.open(script, "w", encoding="utf-8").write(stub + "\n" + ca._capture_query_ps(self.PATH) + "\n")
            out = subprocess.run([ps, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", script],
                                 capture_output=True, text=True, timeout=120)
        finally:
            shutil.rmtree(d, ignore_errors=True)
        rows = ca._parse_capture_rows(out.stdout)

        def ms(hour):
            return calendar.timegm((2026, 9, 29, hour, 0, 0)) * 1000
        self.assertEqual([(5001, 5000, ms(10), ms(12)), (6001, 6000, ms(10), ms(9)), (7001, 7000, ms(10), None)], rows,
                         "the query's rows are wrong (stdout %r, stderr %r)" % (out.stdout[-400:], out.stderr[-400:]))
        end, kept = ca.orphan_captures(rows, mine=set(), alive=lambda p: p in (5000, 6000))
        self.assertEqual([5001, 7001], end, "reused console pid 5000 and gone console 7000 must both end")
        self.assertEqual([6001], [k for k, _w in kept])


class TheCaptureLeavesByItself(unittest.TestCase):
    """capture_win.ps1's own verdict, in real PowerShell. Seen on the ALT's Windows PowerShell 5.1: 7/7 (the first
    seven; the two REG-1509 start-time cases are proven on CI's pwsh and Windows, never on this Mac)."""

    CASES = (
        # v3850 — parent 999991 is dead, and the lease file still names this capture (4242). It stays.
        # A missing file is the withdrawn case below, not this one.
        ("dead console, my lease", "999991", 30, "4242", "", None),
        ("inside the grace", "$PID", 3, None, "", None),
        ("lease withdrawn", "$PID", 30, None, "withdrew", None),
        ("a newer capture holds it", "$PID", 30, "5151", "newer capture", None),
        ("my lease", "$PID", 30, "4242", "", None),
        ("unreadable lease", "$PID", 30, "garbage", "", None),
        ("no console pid given", "0", 30, "4242", "", None),
        # v3850 — the console pid is alive but its process started after this capture. The lease still
        # names 4242, so the capture stays. The yesterday start is what used to read as "started after me".
        ("a reused console pid", "$PID", 30, "4242", "", "((Get-Date).AddDays(-1))"),
        ("my console, older than me", "$PID", 30, "4242", "", "((Get-Process -Id $PID).StartTime.AddSeconds(1))"),
    )

    def test_the_loop_hands_the_verdict_its_own_start(self):
        # REG-1509 — the join, read on every machine: the verdict can only see a reused pid if the loop passes the
        # capture's own start, read once from its own process. Comments stripped; the full call, never a fragment.
        with io.open(os.path.join(HERE, "capture_win.ps1"), encoding="utf-8-sig") as fh:
            src = fh.read()
        code = "\n".join(l.split("#", 1)[0] for l in src.split("\n"))
        call = "Get-LeaseVerdict $leasePath $PID $consolePid (([DateTime]::UtcNow - $bornAt).TotalSeconds) 15 $myStart\n"
        self.assertEqual(1, code.count(call),
                         "the capture loop no longer hands Get-LeaseVerdict its own start - a reused console pid "
                         "reads as its console alive")
        self.assertIn("$myStart = (Get-Process -Id $PID -ErrorAction Stop).StartTime", code)

    def test_the_lease_verdict(self):
        ps = _powershell()
        if not ps:
            self.skipTest("no PowerShell on this machine - capture_win.ps1 is proven where it runs (Windows, CI)")
        src = io.open(os.path.join(HERE, "capture_win.ps1"), encoding="utf-8").read()
        m = re.search(r"(function Get-LeaseVerdict\(.*?\n\}\n)", src, re.S)
        self.assertIsNotNone(m, "capture_win.ps1 no longer defines Get-LeaseVerdict")
        self.assertRegex(src, r"Get-LeaseVerdict \$leasePath \$PID \$consolePid",
                         "the capture loop no longer asks its own lease")
        d = tempfile.mkdtemp(prefix="lease_law_")
        try:
            lf = os.path.join(d, "control_capture.pid")
            lines = [m.group(1), "$lf = '%s'" % lf.replace("'", "''")]
            for name, parent, age, lease, _want, start in self.CASES:
                lines.append("Remove-Item -LiteralPath $lf -ErrorAction SilentlyContinue")
                if lease is not None:
                    lines.append("Set-Content -LiteralPath $lf -Value '%s' -NoNewline" % lease)
                lines.append("$v = Get-LeaseVerdict $lf 4242 %s %d 15%s; Write-Output ('%s=' + $v)"
                             % (parent, age, (" " + start) if start else "", name))
            script = os.path.join(d, "t.ps1")
            io.open(script, "w", encoding="utf-8").write("\n".join(lines) + "\n")
            out = subprocess.run([ps, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", script],
                                 capture_output=True, text=True, timeout=120)
            got = dict(l.split("=", 1) for l in out.stdout.splitlines() if "=" in l)
            for name, _p, _a, _l, want, _s in self.CASES:
                self.assertIn(name, got, "PowerShell did not answer %r: %s" % (name, out.stderr[-400:]))
                if want:
                    self.assertIn(want, got[name], "%s: the capture stayed (%r)" % (name, got[name]))
                else:
                    self.assertEqual("", got[name].strip(), "%s: the capture left for no reason (%r)" % (name, got[name]))
        finally:
            shutil.rmtree(d, ignore_errors=True)


class TheStopEndsWhatTheLampRestarts(_World):
    """REG-1509 — End Session against the capture lamp, replayed through the REAL stop_agent / _force_kill_all_agents,
    _capture_health, _start_capture and _stop_capture. Stubbed: Popen (a capture is a pid in a set), _kill_pid,
    _pid_alive, the priority step, the agent's port/pids, and every path (a temp dir) - no process, no port, no live
    tv/ file. After every stop: no capture alive and no lease file, whatever order the lamp landed in."""

    SAVED = ("_agent_mode", "_agent_proc", "_stop_inflight", "_BOARD_OPENED", "_CAP_RESTART_N", "_CAP_RESTART_TS",
             "_log_fp", "_BRIDGE_LAST_OK")

    def setUp(self):
        super().setUp()
        self.g = {k: getattr(ca, k, None) for k in self.SAVED}
        self.live, self.spawned, self.polls, self.mode_at_capture_stop = set(), [], [], []
        self.pids = iter(range(9990001, 9990401, 2))
        self.on_spawn = self.on_off = self.after_stop = None
        self.stop_entered = threading.Event()
        self.real_stop_capture = ca._stop_capture

    def tearDown(self):
        for k, v in self.g.items():
            setattr(ca, k, v)
        super().tearDown()

    def _popen(self, args, **kw):
        hook, self.on_spawn = self.on_spawn, None
        if hook:
            hook()
        p = _LiveProc(next(self.pids), self.live)
        self.live.add(p.pid)
        self.spawned.append(p.pid)
        return p

    def _capture_off(self, env=None):
        hook, self.on_off = self.on_off, None       # health's first question after it has read the mode
        if hook:
            hook()
        return False

    def _stop_capture_spy(self):
        self.mode_at_capture_stop.append(ca._agent_mode)
        self.stop_entered.set()
        self.real_stop_capture()
        hook, self.after_stop = self.after_stop, None
        if hook:
            hook()

    @contextlib.contextmanager
    def _world(self):
        d = self.d
        with contextlib.ExitStack() as st:
            for name, val in (("IS_WIN", True), ("CAP_PID_PATH", self.pidfile),
                              ("PID_PATH", os.path.join(d, "control_agent.pid")),
                              ("CAP_KILL_SETTLE_S", 0.3), ("_log_fp", self.log),
                              ("_stub_never_films", lambda *a, **k: False), ("_capture_off", self._capture_off),
                              ("_pid_alive", lambda pid: pid in self.live),
                              ("_kill_pid", lambda pid, force=False: self.live.discard(pid)),
                              ("_lower_capture_priority", lambda pid: None),
                              ("_env_clean", lambda *a, **k: {"PATH": "x"}),
                              ("_collect_agent_pids", lambda: []), ("_port_listener_pid", lambda *a, **k: None),
                              ("_ask_agent_shutdown", lambda **k: True), ("_seal_sid_hint", lambda: None),
                              ("_prewarm_seal_cache", lambda: None), ("_pid_cache_seed", lambda pid: None),
                              # stop_agent's finally starts after_session_ended on a thread: the vault lane, the
                              # retention plan and the door store over the REAL tv/frames. Measured: unstubbed, it
                              # ran and printed "after the session: vault lane nudged" from inside this law.
                              ("after_session_ended", lambda *a, **k: None),
                              ("_stop_capture", self._stop_capture_spy)):
                st.enter_context(mock.patch.object(ca, name, val))
            st.enter_context(mock.patch.object(ca.subprocess, "Popen", self._popen))
            st.enter_context(mock.patch.object(
                ca.os.path, "isfile",
                lambda p: True if p == ca.CAPTURE_PS1 else (str(p).startswith(d) and os.path.exists(p))))
            st.enter_context(mock.patch.dict(sys.modules, {"psutil": _TrapPsutil()}))
            st.enter_context(mock.patch.dict(ca._BR_CACHE))
            st.enter_context(mock.patch.dict(ca._MINI))
            ca._agent_mode, ca._agent_proc, ca._stop_inflight = "live", None, False
            ca._CAP_RESTART_N, ca._CAP_RESTART_TS = 0, 0.0
            ca._CAP_STOP.update(survived=0, last=None)
            yield

    def _start_a(self):
        a = ca._start_capture({"PATH": "x"}, self.log)
        self.assertEqual(a, ca._read_pid(self.pidfile), "premise: the session's capture holds the lease")
        self.assertIn(a, self.live)
        return a

    def _assert_nothing_films(self, how):
        filming = sorted(p for p in self.spawned if p in self.live)
        self.assertEqual([], filming, "%s: capture %s is still filming after End Session - it holds its own lease, "
                                      "so nothing will ever end it" % (how, filming))
        self.assertFalse(os.path.exists(self.pidfile),
                         "%s: the lease file survived the stop (holds %r)" % (how, ca._read_pid(self.pidfile)))
        self.assertEqual("off", ca._agent_mode)

    def test_premise_a_capture_that_dies_mid_session_is_still_restarted(self):
        with self._world():
            a = self._start_a()
            self.live.discard(a)                        # it crashed; the session is on
            self.assertEqual("RESTARTED", ca._capture_health())
            b = ca._read_pid(self.pidfile)
            self.assertNotEqual(a, b)
            self.assertIn(b, self.live, "the fix disabled the lamp's restart - a crashed capture is never replaced")

    def _poll_right_after_the_capture_stops(self, stop, how):
        with self._world():
            self._start_a()
            self.after_stop = lambda: self.polls.append(ca._capture_health())
            stop()
            self.assertEqual(["off"], self.mode_at_capture_stop,
                             "%s stopped the capture while the mode still read %r - a status poll in that gap "
                             "restarts the capture behind the stop" % (how, self.mode_at_capture_stop))
            self._assert_nothing_films(how + " -> a status poll -> mode off")

    def test_force_stop_then_a_poll_then_mode_off(self):
        self._poll_right_after_the_capture_stops(ca._force_kill_all_agents, "_force_kill_all_agents")

    def test_end_session_then_a_poll_then_mode_off(self):
        self._poll_right_after_the_capture_stops(lambda: ca.stop_agent(farewell=False), "stop_agent")

    def test_a_lamp_that_read_live_before_the_stop_does_not_spawn_after_it(self):
        # the lamp reads 'live', the WHOLE stop runs, then the lamp reaches its spawn: it must ask again, under the lock
        with self._world():
            a = self._start_a()
            self.on_off = ca._force_kill_all_agents
            got = ca._capture_health()
            self.assertNotIn(a, self.live, "premise: the stop killed the session's capture")
            self._assert_nothing_films("the lamp read 'live', End Session ran, then the lamp spawned")
            self.assertEqual("", got, "the lamp reported %r for a session that had ended" % got)

    def test_a_spawn_in_flight_when_the_stop_begins_is_the_one_it_kills(self):
        # a crashed capture is being restarted (inside the spawn lock, before its lease is written) when End Session
        # begins: the stop must wait for that spawn and kill IT, not read an empty lease and leave
        spawning = threading.Event()

        def slow_spawn():
            spawning.set()
            self.stop_entered.wait(5)
            time.sleep(0.2)                             # a stop that does not wait is long finished by now
        with self._world():
            a = self._start_a()
            self.live.discard(a)                        # it crashed; the lamp will restart it
            self.stop_entered.clear()
            self.on_spawn = slow_spawn
            t = threading.Thread(target=lambda: self.polls.append(ca._capture_health()))
            t.start()
            self.assertTrue(spawning.wait(5), "premise: the lamp never began its restart")
            ca._force_kill_all_agents()
            t.join(10)
            self.assertFalse(t.is_alive(), "the lamp's restart hung")
            self.assertEqual(2, len(self.spawned), "premise: the lamp's restart spawned")
            self._assert_nothing_films("End Session began while the lamp's restart was spawning")


RED_PROOF = [
    {
        "why": "2026-09-29 - two starts at once each see no capture and each spawn one; the second pid write orphans the first",
        "file": "tv/control_app.py",
        "find": "    with _CAP_START_LOCK:\n        # REG-1509 — THE RESTART ASKS AGAIN, INSIDE THE LOCK.",
        "replace": "    if True:\n        # REG-1509 — THE RESTART ASKS AGAIN, INSIDE THE LOCK.",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - the capture is never told its console, so a crashed console leaves it filming forever",
        "file": "tv/control_app.py",
        "find": "        env2[\"TV_CONSOLE_PID\"] = str(os.getpid())\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - a kill that did not land is assumed to have landed (the five-capture shape)",
        "file": "tv/control_app.py",
        # REG-1550 - re-anchored: the settle check now runs only for a pid that WAS killed (`killed and`)
        "find": "    if pid and killed and not _gone_within(pid, _pid_alive, CAP_KILL_SETTLE_S):\n        _CAP_STOP[\"survived\"]",
        "replace": "    if False:\n        _CAP_STOP[\"survived\"]",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - the boot sweep ends a capture whose console is alive (another console's camera)",
        "file": "tv/control_app.py",
        "find": "        elif ppid and alive(ppid) and not reused:\n",
        "replace": "        elif False:\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - an unreadable process table is read as 'no captures' and the sweep says found 0",
        "file": "tv/control_app.py",
        "find": "    if rows is None:\n        _CAP_SWEEP.update(ran=now, found=None,",
        "replace": "    if rows is None:\n        rows = []\n    if False:\n        _CAP_SWEEP.update(ran=now, found=None,",
        "matches": 1,
    },
    {
        "why": "REG-1509 - _force_kill_all_agents stops the capture while the mode reads 'live'; a poll in the gap restarts it",
        "file": "tv/control_app.py",
        "find": "    with _lock:\n        _agent_mode = \"off\"         # REG-1509 — before the capture stops, or the lamp restarts it behind the stop\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "REG-1509 - stop_agent stops the capture while the mode reads 'live' (End Session's own order)",
        "file": "tv/control_app.py",
        "find": "        with _lock:\n            _agent_mode = \"off\"\n        _stop_capture()\n",
        "replace": "        _stop_capture()\n",
        "matches": 1,
    },
    {
        "why": "REG-1509 - the spawn never asks again under its lock, so a lamp that read 'live' spawns after the stop",
        "file": "tv/control_app.py",
        "find": "        if wanted is not None and not wanted():\n",
        "replace": "        if False:\n",
        "matches": 1,
    },
    {
        "why": "REG-1509 - the lamp's restart does not hand the spawn its question",
        "file": "tv/control_app.py",
        "find": "_log_fp, wanted=_capture_wanted)",
        "replace": "_log_fp)",
        "matches": 1,
    },
    {
        "why": "REG-1509 - the stop reads the lease before an in-flight spawn writes it, and the new capture outlives the stop",
        "file": "tv/control_app.py",
        "find": "    with _CAP_START_LOCK:\n        pass\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "REG-1509 - the sweep's query counts itself (its -Command text holds the path)",
        "file": "tv/control_app.py",
        "find": "        if self_pid is not None and pid == int(self_pid):\n            continue\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "REG-1509 - a console pid reused by a newer process reads as the console alive; the orphan films for good",
        "file": "tv/control_app.py",
        "find": "        elif ppid and alive(ppid) and not reused:\n",
        "replace": "        elif ppid and alive(ppid):\n",
        "matches": 1,
    },
    {
        "why": "REG-1509 - the capture loop never hands the lease verdict its own start, so the reuse test never runs",
        "file": "tv/capture_win.ps1",
        "find": ".TotalSeconds) 15 $myStart\n",
        "replace": ".TotalSeconds) 15\n",
        "matches": 1,
    },
    {
        "why": "REG-1509 - a sweep that could not ask the process table reads OK on the doctor",
        "file": "tv/control_app.py",
        "find": "    _unknown = _cs.get(\"ran\") is not None and _cs.get(\"found\") is None\n",
        "replace": "    _unknown = False\n",
        "matches": 1,
    },
    {
        "why": "REG-1509 - a stop survivor keeps the doctor row warning after it has left",
        "file": "tv/control_app.py",
        "find": "    _surv_live = bool(_surv) and _alive(_last.get(\"pid\"))\n",
        "replace": "    _surv_live = bool(_surv)\n",
        "matches": 1,
    },
    {
        "why": "REG-1509 - an orphan that left after the sweep keeps the doctor row warning",
        "file": "tv/control_app.py",
        "find": "    _failed_live = [p for p in (_cs.get(\"failed\") or []) if _alive(p)]\n",
        "replace": "    _failed_live = list(_cs.get(\"failed\") or [])\n",
        "matches": 1,
    },
    {
        "why": "REG-1509 - the stop judges its kill the instant taskkill returns; a late death counts as a survivor",
        "file": "tv/control_app.py",
        # REG-1550 - re-anchored to the `killed and` form (the tamper is the same: judged the instant taskkill returns)
        "find": "    if pid and killed and not _gone_within(pid, _pid_alive, CAP_KILL_SETTLE_S):\n",
        "replace": "    if pid and killed and _pid_alive(pid):\n",
        "matches": 1,
    },
    {
        "why": "REG-1509 - the sweep judges its kill the instant taskkill returns; a late death is reported as would-not-end",
        "file": "tv/control_app.py",
        "find": "        (killed if _gone_within(pid, alive, max(0.0, _settle_by - time.time())) else failed).append(pid)\n",
        "replace": "        (failed if alive(pid) else killed).append(pid)\n",
        "matches": 1,
    },
    {
        "why": "REG-1509 - this law's spawn runs the real priority step on a fake pid (on Windows 7001 opens pid 7000)",
        "file": "tv/test_one_capture_per_console.py",
        "find": "                mock.patch.object(ca, \"_lower_capture_priority\", lambda pid: reniced.append(pid)), \\\n",
        "replace": "",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
