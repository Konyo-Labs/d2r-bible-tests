#!/usr/bin/env python3
"""WHAT DID I LEAVE RUNNING? — asked as a step, because he should never be the one who notices.

2026-08-29: he wrote "my pc is super hot.. something is open that isnt closed". A `python3 -c` I
had launched was at 99.7% CPU with an elapsed time of 1 DAY 4 HOURS — a
`glob('~/Library/Application Support/**', recursive=True)`, which over a tree that size never
finishes. It burned a core for 28 hours and the only alarm was the temperature of his laptop.

This reports. IT KILLS NOTHING — killing needs a human look at what the process actually is, and
`pkill -f` is banned on this machine because :17772 is his live console and a pattern cannot tell
his process from mine. [[process-port-discipline]] [[unbounded-search-orphans]]
"""
import io
import json
import os
import subprocess
import time
import sys

# Long-lived and busy by design; not mine and not news.
# ⚠ THIS LIST IS WHAT KEEPS THE SWEEP FROM BECOMING FURNITURE. macOS runs several daemons that are
# legitimately busy for hours — knowledge-agent and contactsd both showed up at >20% CPU on the
# first real run — and a check that flags Apple's own processes every time is one nobody reads by
# the end of the week. Anything added here must be something I did NOT start.
KNOWN = ("xprotect", "mds_stores", "WindowServer", "claude.exe", "Terminal", "spotlight",
         "mdworker", "sysmond", "winedevice", "WhatsApp", "WebKit", "control_app.py",
         "backupd", "photoanalysisd", "cloudd", "bird",
         "knowledge-agent", "contactsd", "suggestd", "corespotlightd", "AppleSpell",
         "com.apple.", "trustd", "syncdefaultsd", "accountsd", "distnoted",
         # v2281 — HIS GAME IS NOT AN ORPHAN. Measured 2026-08-30 while he was playing: D2R.exe at
         # 334% CPU for 100 minutes, flagged as "busy and old" by a sweep whose whole purpose is to
         # catch MY runaway processes. A watcher that cries about the thing the machine exists to
         # run teaches him to ignore it, which is how a real 28-hour core-burner gets missed.
         # CrossOver hosts it, so both spellings appear in the command line.
         "D2R.exe", "Diablo II Resurrected", "CrossOver", "wineserver")

BUSY_PCT = float(os.environ.get("TV_ORPHAN_CPU") or 20.0)
OLD_MIN = int(os.environ.get("TV_ORPHAN_MIN") or 20)


#: Ports that are HIS by definition. A process holding one of these is never "mine", whatever else
#: matches — his console, his Chrome, TradingView, his desktop app.
HIS_PORTS = (17772, 17781, 17955, 9222, 9223, 8848)

#: Executable prefixes that belong to macOS itself. A process running out of one of these is the
#: operating system, whatever it is doing. ⚠ `/usr/local` is NOT here (node, his tools) and neither
#: is /Library/Developer/CommandLineTools (the python I run under) — excusing those would make the
#: sweep unable to see its own author.
SYSTEM_PATHS = ("/System/", "/usr/sbin/", "/usr/libexec/", "/sbin/", "/Library/Apple/")

#: #171 (REG-2482) - why his ports are UNKNOWN on a Windows PC. "could not be asked" is what holds_his_port fails closed
#: on, so every Windows process is NEVER MINE and the spawn ledger and the tree are never asked about it.
WIN_PORTS_UNREAD = "his ports could not be asked on this PC - there is no lsof on Windows"

#: Where `claude-owns` records what it started. ⚠ INCOMPLETE BY NATURE: 53 rows, last written a day
#: before this was needed, and today's 52-minute runaway was never in it. Registration is a claim
#: about INTENT that has to be made at spawn — so its ABSENCE proves nothing at all.
_SPAWN_LEDGER = os.path.expanduser("~/.claude/claude_spawned.jsonl")


def _registered_pids():
    """Pids `claude-owns` recorded at spawn. -> set (empty if the ledger cannot be read).

    ⚠ AN EMPTY SET IS NOT "NOTHING IS OURS". It is "the ledger said nothing", and the caller must
    not read one as the other — which is exactly why attribution below has a third answer.
    """
    out = set()
    try:
        with io.open(_SPAWN_LEDGER, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                p = row.get("pid")
                if p is not None:
                    out.add(str(p))
    except Exception:
        return set()
    return out


def _parent_of(pid):
    """ppid of `pid`, as a string, or None. Bounded and failure-tolerant by design."""
    try:
        r = subprocess.run(["ps", "-o", "ppid=", "-p", str(pid)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5)
        v = (r.stdout or "").strip()
        return v or None
    except Exception:
        return None


def _listening_ports(pid):
    """Ports `pid` itself LISTENS on. -> (set, why)

    ⚠ `-a` ANDs the selectors. Without it lsof ORs them and hands back the whole machine.
    """
    if _platform() == "win32":
        # #171 (REG-2482, the review of the first cut) - THERE IS NO lsof ON WINDOWS, so his ports are never read there.
        # Asked anyway it failed as a bare FileNotFoundError on every suspect, a reason that read like a hiccup. This
        # says what it is and spawns nothing; holds_his_port fails CLOSED on it, so no Windows process is ever "mine".
        return set(), WIN_PORTS_UNREAD
    try:
        r = subprocess.run(["lsof", "-nP", "-a", "-p", str(pid), "-iTCP", "-sTCP:LISTEN"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10)
    except Exception as e:
        return set(), "lsof could not be asked (%s)" % type(e).__name__
    out = set()
    for line in (r.stdout or "").splitlines()[1:]:
        parts = line.split()
        if len(parts) < 2 or "(LISTEN)" not in line:
            continue
        name = parts[-2]
        if ":" not in name:
            continue
        try:
            out.add(int(name.rsplit(":", 1)[1]))
        except ValueError:
            continue
    return out, "read %d listening socket(s)" % len(out)


def holds_his_port(pid):
    """Is this process listening on one of HIS ports? -> (int|None, why)

    ★ THIS FUNCTION IS THE WHOLE POINT OF THIS FILE AND IT DID NOT EXIST.
    `HIS_PORTS` was declared at the top with the comment "a process holding one of these is never
    'mine', whatever else matches" — and MEASURED 2026-09-09: `grep -c HIS_PORTS` was **1**, its
    own definition. Nothing consulted it. `_attribute` promised three positive witnesses in its
    docstring, implemented two, and closed its refusal sentence with the words "holds none of our
    ports" — an assertion about a check that was never run.

    What that cost, the same day: his live console (`control_app.py --open`, holding :17772) came
    back from `_attribute` as `ours=None` — "busy and old, and nothing can say whose it is" — which
    is the shape this tool reports as a suspect. I had separately read one `ps` sample showing it
    at 108% CPU and 17h uptime and was one command from killing it. The guard written to prevent
    exactly that would have agreed with me.

    ⚠ IT FAILS CLOSED. If lsof cannot answer, the port is UNKNOWN and the caller must treat the
    process as NOT-MINE, because the cost of a wrong "mine" is his console and the cost of a wrong
    "not mine" is a process that lives five more minutes.
    [[plumbing-with-no-tap]] [[i-own-everything-i-start]] [[unknown-stays-unknown]]
    """
    # ⚠⚠ THROUGH `_listening_ports`, NOT A SECOND lsof OF ITS OWN. The first cut of this fix
    # inlined the call here AND kept the helper for the ancestry walk — two implementations of one
    # question, which is the drift that produced the stale path resolver earlier the same day. The
    # gate caught it immediately: a test that stubs `_listening_ports` could not move this branch.
    # [[copy-drift]]
    found, why = _listening_ports(pid)
    if not found and "could not be asked" in why:
        # ⚠ FAILS CLOSED. An unanswerable lsof means the port is UNKNOWN, and the caller must treat
        # the process as NOT-MINE: a wrong "mine" costs his console, a wrong "not mine" costs a
        # process five more minutes. [[unknown-stays-unknown]]
        return None, "%s — the port is UNKNOWN, so this is NOT mine" % why
    for port in HIS_PORTS:
        if port in found:
            return port, "listening on :%d, which is HIS by definition" % port
    # ⚠⚠ AND HIS PROCESS TREE, NOT JUST HIS LISTENER. MEASURED 2026-09-09: his console holds
    # :17772 on ONE pid and runs helpers beside it that hold nothing — pid 67244 came back port=0
    # while its parent was the console. Killing a child of his console breaks his console just as
    # surely as killing the listener, so the protection has to cover the tree the port anchors.
    # The walk is bounded and stops at pid 1; a cycle or a vanished parent ends it.
    _seen, _p = set(), pid
    for _ in range(12):
        _pp = _parent_of(_p)
        if not _pp or _pp in ("0", "1") or _pp in _seen:
            break
        _seen.add(_pp)
        _up, _upWhy = _listening_ports(_pp)
        for port in HIS_PORTS:
            if port in _up:
                return port, ("its ancestor pid %s listens on :%d — killing a child of his "
                              "console breaks his console" % (_pp, port))
        _p = _pp
    return 0, ("listens on none of his ports (found %s)"
               % (", ".join(":%d" % p for p in sorted(found)) or "no listening socket"))


def _attribute(pid, cmd):
    """Whose process is this? -> (True|False|None, why)

    True  — positively OURS: registered at spawn, or naming this tree, or holding one of our ports.
    None  — UNATTRIBUTED. Busy, old, not a known system process, and nothing can say whose it is.
            ⚠ THIS IS THE HONEST ANSWER FOR THE CASE THAT MATTERS MOST. Today's real runaway —
            `python3 -c` over bible.html, 100% CPU for 52 minutes — was in no ledger, named no tree
            path, and held no port. A rule that only reported POSITIVE ownership would have said
            nothing about it at all. [[unknown-stays-unknown]]
    """
    # ⚠⚠ HIS PORTS ARE ASKED FIRST, AND THE ANSWER IS FINAL. Ownership is not a majority vote:
    # a process on :17772 is his console even if it names this tree, even if a stale ledger row
    # claims it, even if it is burning a core. Putting this after the positive witnesses would let
    # "names this tree" win — and his console's command line IS this tree.
    _hp, _hpWhy = holds_his_port(pid)
    if _hp is None or _hp:
        return False, ("NEVER MINE — %s" % _hpWhy)
    if str(pid) in _registered_pids():
        return True, "registered by claude-owns at spawn"
    _here = os.path.dirname(os.path.abspath(__file__))
    _root = os.path.dirname(_here)
    if _here in cmd or _root in cmd:
        return True, "names this tree on its command line"
    return None, ("busy and old, and nothing can say whose it is — not in the spawn ledger, does "
                  "not name this tree, and %s" % _hpWhy)


def _elapsed_minutes(et):
    """`ps` elapsed -> minutes. Formats: MM:SS, HH:MM:SS, D-HH:MM:SS."""
    days = 0
    if "-" in et:
        d, et = et.split("-", 1)
        days = int(d)
    parts = [int(x) for x in et.split(":")]
    if len(parts) == 2:
        h, m, s = 0, parts[0], parts[1]
    else:
        h, m, s = parts[0], parts[1], parts[2]
    return days * 1440 + h * 60 + m + (s / 60.0)


def _cpu_sample():
    """{pid: pcpu} from one ps, or None if ps could not be asked. -> dict|None

    ⚠⚠ NONE, NOT `{}`. The swallow ratchet caught this the day it shipped — RANK 1, "a failed read
    handed back as DATA", baseline 74 -> 75, `tv/my_orphans.py 0 -> 1`. An empty dict from a failed
    `ps` is indistinguishable from a real sample of a machine with no processes, and this feeds the
    runaway sweep: a caller comparing against `{}` finds nothing busy and reports a clean machine.
    That is the exact shape of the defect this sweep exists to catch, inside the sweep itself.
    [[unknown-stays-unknown]]
    """
    try:
        raw = subprocess.run(["ps", "-Ao", "pid,pcpu"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20).stdout
    except Exception:
        return None
    out = {}
    for line in raw.splitlines()[1:]:
        p = line.split()
        if len(p) >= 2:
            try:
                out[p[0]] = float(p[1])
            except ValueError:
                pass
    return out


#: The previous CPU sample and when it was taken. ⚠ THE SECOND SAMPLE COMES FROM THE PREVIOUS
#: CALL, NOT FROM A SLEEP. The first cut slept 4 s inside this function to get its second reading —
#: and `suspects()` runs on the watchdog's TEN-MINUTE TIMER and at every console boot, so the
#: pre-push gate refused the ship with `armed migration (4359 ms, again 4324 ms)`. A supervisor
#: that costs four seconds every ten minutes to answer "is anything running away" is itself the
#: kind of cost it exists to find. Consecutive calls are separated by real time — far more than a
#: sleep would buy — so the samples are better AND free. [[poll-slower-than-its-interval]]
_LAST_SAMPLE = {"at": 0.0, "cpu": {}}
#: REG-3774 (11-12) - THE PREVIOUS SAMPLE ALSO LIVES ON DISK. Since REG-2987 a console runs each doctor pass in a SHORT-LIVED
#: CHILD, so the in-memory sample above died with every pass: his console's "stray processes" row read UNKNOWN ("only ONE
#: cpu sample is available") for 6 days across 885 asks, and Dean's Windows row the same. The last sample is kept beside the
#: memory copy (one file per machine, never in the repo's history) and a pass with no memory copy compares against it while
#: it is younger than PREV_MAX_AGE_S. Older, unreadable or from the future: no previous sample (UNKNOWN), never a guess.
SAMPLE_ENV = "TV_ORPHAN_SAMPLE"
PREV_MAX_AGE_S = 2 * 3600


def _sample_path():
    return os.environ.get(SAMPLE_ENV) or os.path.join(os.path.dirname(os.path.abspath(__file__)), ".orphan_cpu_sample.json")


def _prev_sample(kind, mem, now):
    """REG-3774 - (cpu, at): the in-memory previous sample, else the one on disk while it is fresh. Never raises."""
    if mem.get("cpu"):
        return mem.get("cpu") or {}, float(mem.get("at") or 0.0)
    try:
        with io.open(_sample_path(), encoding="utf-8") as fh:
            row = (json.load(fh) or {}).get(kind) or {}
        at, cpu = float(row.get("at") or 0.0), row.get("cpu")
        if isinstance(cpu, dict) and cpu and 0 < now - at <= PREV_MAX_AGE_S:
            return cpu, at
    except Exception:
        pass
    return {}, 0.0


def _keep_sample(kind, cpu, at):
    """REG-3774 - the sample just taken, kept for the next pass's process (atomic replace). Never raises."""
    path = _sample_path()
    try:
        try:
            with io.open(path, encoding="utf-8") as fh:
                body = json.load(fh)
            body = body if isinstance(body, dict) else {}
        except Exception:
            body = {}
        body[kind] = {"at": at, "cpu": cpu}
        tmp = "%s.%d.tmp" % (path, os.getpid())
        with io.open(tmp, "w", encoding="utf-8") as fh:
            json.dump(body, fh)
        os.replace(tmp, path)
    except Exception:
        pass
#: what the last sweep actually measured: how many processes, by which instrument, when. health_engine's OK sentence
#: reads it, so "nothing busy" always names its denominator. n None = no sweep has measured yet.
_SCAN = {"n": None, "how": None, "at": None, "portsSay": None}


def last_scan():
    """What the last suspects() call measured. -> {"n", "how", "at", "portsSay"} (a copy). portsSay None = the
    default sentence about his ports holds. [[zero-needs-a-denominator]]"""
    return dict(_SCAN)


def _platform():
    """A seam: the law drives the Windows sweep on any PC."""
    return sys.platform


def _now():
    return time.time()


# ══ #171 (REG-2482) — THE SAME SWEEP ON WINDOWS, MEASURED BY THE KERNEL'S OWN COUNTERS ══════════════════════════════
# MEASURED on Dean's PC 2026-10-22: 'stray processes' UNKNOWN for 45 days, "`ps` could not be asked for a CPU sample" -
# there is no ps on Windows, so the runaway watch was blind on every Windows PC while it read as an instrument hiccup.
# The Windows sweep asks the same question the same way: TWO samples, the second from the previous call (never a
# sleep), and a process is busy only on the CPU time it actually burned BETWEEN them. tv_diablo's one Toolhelp32 snapshot
# names every process; GetProcessTimes gives each one's CUMULATIVE CPU time. No process is spawned. Age comes from the
# creation time child_guard's birth reader already reads - one reader each, never a copy. [[copy-drift]]
_LAST_WIN = {"at": 0.0, "cpu": {}}
#: Windows' own images: %SystemRoot%'s system folders and Defender's platform folder. NEVER Program Files, AppData or
#: WindowsApps - python and node live there, and excusing them would blind the sweep to its own author.
WIN_SYSTEM_DIRS = ("\\windows\\system32\\", "\\windows\\syswow64\\", "\\windows\\winsxs\\",
                   "\\windows\\systemapps\\", "\\windows\\servicing\\", "\\windows\\microsoft.net\\",
                   "\\windows\\explorer.exe", "\\windows defender\\")
#: ...but the shells that live there run whatever they are handed, so their work is somebody's - mine, possibly - and
#: never the OS's: a `powershell -Command` runaway is exactly the 28-hour class, wearing a System32 path.
WIN_SCRIPT_HOSTS = ("powershell.exe", "pwsh.exe", "cmd.exe", "wscript.exe", "cscript.exe")
#: his game on Windows, and the cloud clients that stream it (self_prove.PLAY_EXES) - busy by design, never mine
WIN_KNOWN = ("d2r.exe", "boosteroid.exe", "geforcenow.exe", "nvidia geforce now.exe")
#: the kernel's pseudo-processes, which have no image and are the OS by definition
WIN_PSEUDO = ("System Idle Process", "System", "Registry", "Memory Compression", "Secure System")
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def _win_kernel():
    """kernel32 through its OWN ctypes handle (never the shared windll one), argument types declared here."""
    import ctypes
    from ctypes import wintypes
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k.OpenProcess.restype = wintypes.HANDLE
    k.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(ctypes.c_uint64)] * 4
    k.GetProcessTimes.restype = wintypes.BOOL
    k.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                             ctypes.POINTER(wintypes.DWORD)]
    k.QueryFullProcessImageNameW.restype = wintypes.BOOL
    k.CloseHandle.argtypes = [wintypes.HANDLE]
    k.CloseHandle.restype = wintypes.BOOL
    return k


def _win_cpu_sample():
    """{pid: {"cpuS", "ppid", "exe"}} - every process this user may open, with its CUMULATIVE CPU seconds - or None.

    The process list is tv_diablo._win_process_names(), the ONE Toolhelp32 snapshot reader (control_app's git census
    trusts it too) - never a second copy; each process's CPU time is GetProcessTimes (kernel + user). None, never {}: a
    snapshot that could not be taken is UNMEASURED, and a process that cannot be opened (a protected one) is left out
    of the sample rather than read as idle. Windows only; it raises nowhere."""
    try:
        import ctypes
        import tv_diablo as _tvd
        names = _tvd._win_process_names()
        if not names:
            return None
        k = _win_kernel()
        out = {}
        for pid, exe in names.items():
            if int(pid) in (0, 4) or exe in WIN_PSEUDO:
                continue                                            # the kernel itself, not a process of anyone's
            h = k.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
            if not h:
                continue
            try:
                c, x, kt, ut = (ctypes.c_uint64() for _ in range(4))
                if k.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(x), ctypes.byref(kt), ctypes.byref(ut)):
                    out[str(pid)] = {"cpuS": (kt.value + ut.value) / 1e7, "ppid": None, "exe": exe}
            finally:
                k.CloseHandle(h)
        return out
    except Exception:
        return None


def _win_birth(pid):
    """Creation time, epoch seconds, through child_guard's ONE birth reader. None = UNKNOWN. A seam."""
    try:
        import child_guard as _cg
        return _cg._birth_win(pid)
    except Exception:
        return None


def _win_command(pid):
    """The process's command line (ProcessCommandLineInformation, Windows 8.1+), else its image path, else None.
    KNOWN names things like `control_app.py`, which only a command line carries. A seam."""
    try:
        import ctypes
        from ctypes import wintypes
        k = _win_kernel()
        h = k.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
        if not h:
            return None
        try:
            nt = ctypes.WinDLL("ntdll")
            nt.NtQueryInformationProcess.argtypes = [wintypes.HANDLE, ctypes.c_ulong, ctypes.c_void_p,
                                                     ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong)]
            nt.NtQueryInformationProcess.restype = ctypes.c_long
            need = ctypes.c_ulong(0)
            nt.NtQueryInformationProcess(h, 60, None, 0, ctypes.byref(need))
            if 16 <= need.value <= 1 << 20:

                class UNICODE_STRING(ctypes.Structure):
                    _fields_ = [("Length", ctypes.c_ushort), ("MaximumLength", ctypes.c_ushort),
                                ("Buffer", ctypes.c_void_p)]
                buf = ctypes.create_string_buffer(need.value)
                if nt.NtQueryInformationProcess(h, 60, buf, need, ctypes.byref(need)) >= 0:
                    us = UNICODE_STRING.from_buffer(buf)
                    if us.Buffer and us.Length:
                        return ctypes.wstring_at(us.Buffer, us.Length // 2)
            size = wintypes.DWORD(32768)
            img = ctypes.create_unicode_buffer(size.value)
            if k.QueryFullProcessImageNameW(h, 0, img, ctypes.byref(size)):
                return img.value
            return None
        finally:
            k.CloseHandle(h)
    except Exception:
        return None


def _win_os_image(cmd):
    """Is this Windows' own work - an image out of Windows' own folders that is not a shell? -> bool
    The image is the quoted head of the command line, or everything up to its first `.exe` (an unquoted path may
    hold spaces: ...\\Windows Defender\\...\\MsMpEng.exe)."""
    low = str(cmd or "").strip().lower()
    if low.startswith('"'):
        first = low[1:].split('"', 1)[0]
    else:
        first = low[:low.find(".exe") + 4] if ".exe" in low else low.split(" ", 1)[0]
    if first.rsplit("\\", 1)[-1] in WIN_SCRIPT_HOSTS:
        return False                    # a shell's work is somebody's, never the OS's
    return any(d in first for d in WIN_SYSTEM_DIRS)


def _unmeasured_win(cur):
    return {"pid": None, "ours": None,
            "why": ("the Windows kernel's process counters %s, so nothing can be judged about runaways right now. "
                    "This is UNMEASURED, not clean."
                    % ("could not be read for a CPU sample" if cur is None else "answered for no process at all"))}


def _suspects_win(busy, old_min):
    """#171 (REG-2482) — suspects() on Windows: busy in the CPU time burned BETWEEN two samples, and old. -> rows"""
    now = _now()
    prev, prev_at = _prev_sample("win", _LAST_WIN, now)              # REG-3774 - memory, else the last pass's file
    cur = _win_cpu_sample()
    if not cur:
        return [_unmeasured_win(cur)]
    _LAST_WIN["cpu"], _LAST_WIN["at"] = cur, now
    _keep_sample("win", cur, now)
    _SCAN.update(n=len(cur), at=now,
                 how="the Windows kernel's own per-process CPU time (GetProcessTimes), two samples",
                 portsSay=("His ports cannot be read on this PC (there is no lsof on Windows), so no busy process is "
                           "ever counted as mine here, and the spawn ledger and this tree are never asked about one - "
                           "each is still reported, with that reason."))
    gap = now - prev_at
    if not prev or gap < 1.0:
        return [{"pid": None, "ours": None,
                 "why": ("only ONE cpu sample is available%s - a CPU time becomes a load only against a second "
                         "reading, so no runaway verdict is possible yet. Ask again in a moment and this becomes "
                         "measurable." % ("" if not prev else " (the previous one is %.1fs old)" % gap))}]
    out = []
    for pid, row in cur.items():
        first = prev.get(pid)
        if not first:
            continue                    # younger than the first sample: it cannot be a 20-minute runaway
        burned = float(row.get("cpuS") or 0.0) - float(first.get("cpuS") or 0.0)
        if burned < 0:
            continue                    # less CPU than before: the pid now names another process
        pct = 100.0 * burned / gap
        if pct < busy:
            continue
        born = _win_birth(pid)
        if born is None or born > prev_at:
            continue                    # unreadable, or born after the first sample: that reading was another's
        mins = (now - born) / 60.0
        if mins < old_min:
            continue
        cmd = _win_command(pid) or str(row.get("exe") or "")
        if any(k in cmd for k in KNOWN) or any(k in cmd.lower() for k in WIN_KNOWN):
            continue
        if _win_os_image(cmd):
            continue                    # Windows itself (never a shell: capture_win.ps1 runs in one)
        _own, _ownWhy = _attribute(pid, cmd)
        out.append({"pid": pid, "ppid": row.get("ppid"), "cpu": round(pct, 1), "samples": 2,
                    "sampleGapS": round(gap, 1), "minutes": round(mins, 1), "cmd": cmd[:150],
                    "ours": _own, "whose": _ownWhy})
    return out


def suspects(busy=BUSY_PCT, old_min=OLD_MIN, settle=0.0):
    """Processes that are BOTH busy and old — the shape a runaway has. -> list of dicts

    ⚠⚠ TWO CPU SAMPLES, NOT ONE, AND THAT IS THE HALF THAT NEARLY COST HIS CONSOLE.
    `ps` %CPU is a DECAYING AVERAGE, not an instantaneous load. MEASURED 2026-09-09 on his console:
    **108.4%**, then 9.0%, then 5.6% — three reads seconds apart, one process, nothing changed. I
    acted on the first, called it "an unbounded process pinning a core for 17 hours", and was one
    command from killing :17772.

    A runaway is busy in BOTH samples. A burst is busy in one. The row now carries both figures and
    `cpu` is the MINIMUM, so a spike cannot promote itself into a verdict.
    [[feedback-suspect-the-instrument]] [[unknown-stays-unknown]]
    """
    if _platform() == "win32":
        return _suspects_win(busy, old_min)     # #171 (REG-2482) - no ps there; the kernel's own counters
    out = []
    _now = time.time()
    _prev, _prevAt = _prev_sample("ps", _LAST_SAMPLE, _now)        # REG-3774 - memory, else the last pass's file
    _cur = _cpu_sample()
    if _cur is None:
        # the instrument could not be read — that is UNKNOWN, and the previous sample is NOT
        # replaced with an absence that would then look like a quiet machine next time.
        return [{"pid": None, "ours": None,
                 "why": "`ps` could not be asked for a CPU sample, so nothing can be judged about "
                        "runaways right now. This is UNMEASURED, not clean."}]
    _LAST_SAMPLE["cpu"], _LAST_SAMPLE["at"] = _cur, _now
    _keep_sample("ps", _cur, _now)
    _SCAN.update(n=len(_cur), at=_now, how="`ps` %CPU, two samples", portsSay=None)
    # ⚠ `settle` REMAINS, so a caller that genuinely wants an immediate second reading can ask for
    # one — but it is OFF by default, because the timer path must stay cheap.
    if settle:
        time.sleep(settle)
        _prev, _prevAt = _cpu_sample(), _now
    _gap = _now - _prevAt
    # ⚠⚠ NO PRIOR SAMPLE IS *UNKNOWN*, NOT "NOTHING IS WRONG". On the first call of a process there
    # is nothing to compare against, and a single decaying average is exactly what nearly cost his
    # console. So the pass reports that it could not judge rather than returning a confident empty
    # list. [[unknown-stays-unknown]] [[zero-needs-a-denominator]]
    if not _prev or _gap < 1.0:
        return [{"pid": None, "ours": None,
                 "why": ("only ONE cpu sample is available%s — a single `ps` %%CPU is a decaying "
                         "average, not a load, so no runaway verdict is possible yet. Ask again in "
                         "a moment and this becomes measurable."
                         % ("" if not _prev else " (the previous one is %.1fs old)" % _gap))}]
    _first = _prev
    try:
        raw = subprocess.run(["ps", "-Ao", "pid,ppid,pcpu,etime,command"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20).stdout
    except Exception as e:
        return [{"pid": None, "why": "could not ask ps: %s" % e}]
    for line in raw.splitlines()[1:]:
        parts = line.split(None, 4)
        if len(parts) < 5:
            continue
        pid, ppid, pcpu, et, cmd = parts
        try:
            cpu = float(pcpu)
            mins = _elapsed_minutes(et)
        except (TypeError, ValueError):
            continue
        # BOTH samples must clear the bar. An absent first sample means the process is younger
        # than this call, which cannot be a 20-minute runaway.
        cpu0 = _first.get(pid)
        cpu = min(cpu, cpu0) if cpu0 is not None else 0.0
        if cpu < busy or mins < old_min:
            continue
        if any(k in cmd for k in KNOWN):
            continue
        # ⚠⚠ v2847 — AN OS DAEMON IS NEVER MINE, AND A NAME LIST WOULD NOT HAVE COVERED IT.
        # MEASURED the first time this ran: `coreaudiod` — 22.8% and 23.5% across BOTH samples,
        # seven days old — was reported as "busy and old, and nothing can say whose it is". It is
        # busy because he is on a call. It also sits right at the 20% bar, so consecutive runs
        # disagreed about it, which is exactly how a watcher teaches him to ignore it.
        # A PATH RULE, not another name in KNOWN: anything executing out of the OS's own
        # directories belongs to macOS. `/usr/local` is deliberately NOT here — node and his own
        # tools live there — and neither is the CommandLineTools python I run under, so this
        # excuses the system without excusing me. [[unknown-stays-unknown]] [[label-outlived-referent]]
        _bin = cmd.split(None, 1)[0] if cmd else ""
        if _bin.startswith(SYSTEM_PATHS):
            continue
        # ⚠⚠ WHOSE IS IT? Until now this dict was labelled "ours" having tested nothing — `ppid` was
        # parsed on the line above and never read, and the only filter was a substring list that
        # flagged PID 1. Three POSITIVE witnesses are asked, and the answer travels with the row.
        _own, _ownWhy = _attribute(pid, cmd)
        out.append({"pid": pid, "ppid": ppid, "cpu": cpu,
                    "cpuFirst": cpu0, "cpuSecond": float(pcpu), "samples": 2,
                    "minutes": round(mins, 1),
                    "cmd": cmd[:150], "ours": _own, "whose": _ownWhy})
    return out


def main(argv=None):
    rows = suspects()
    if not rows:
        print("🟢 nothing of mine is both busy and old — no orphan burning a core.")
        return 0
    print("🔴 %d process(es) BUSY (>%.0f%% CPU) and OLD (>%d min) — one of these is why his machine "
          "is hot:" % (len(rows), BUSY_PCT, OLD_MIN))
    for r in rows:
        print("   pid %-7s %5.1f%% CPU  %8.1f min  %s" % (r["pid"], r["cpu"], r["minutes"], r["cmd"]))
    print("   ⚠ LOOK before killing: `ps -o command -p <pid>`, then `kill <pid>`. Never pkill -f — "
          ":17772 is his live console and a pattern cannot tell it from mine.")
    return 1


if __name__ == "__main__":
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import console_safe as _cs
        _cs.enable()
    except Exception:
        pass
    sys.exit(main(sys.argv[1:]))
