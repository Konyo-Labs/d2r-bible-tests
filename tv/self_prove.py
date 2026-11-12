# -*- coding: utf-8 -*-
"""#50 — EVERY PC PROVES ITS OWN INSTRUMENTS, IN THE BACKGROUND, WITHOUT BEING ASKED (REG-1447).

His ruling, 2026-09-29: *"i think it does need to get proved on the windows alt right? and on deans?"*
Measured the same morning, it does. A heart census proves that THIS machine's gates can still go red, and
the Mac's proof does not speak for Windows:
  · at the same clean commit the ALT's gate fingerprint was 2d9eff1d against the Mac's 56b2a8c3 - on
    Windows run_gates would not even import (REG-1445), and with that fixed it lists 679 gates to 678;
  · a one-law trial prove on the ALT found the river-outlet law BLIND there (green through its own
    sabotage) while it goes red on the Mac - the Mac's sandbox happened to carry one of HIS reels.

So the census is per-machine, and until today only the pre-push gate on his Mac ever wrote one. Every
other PC - the ALT, Dean's - had `.heart2.json` absent, so `self_arming.may()` answered "the heart has
never run here" and every lock stayed shut: 76 ALT reels at EMPTY never ROUTED.

This lane closes that. On an INSTALLED console (clean tree, at its upstream) whose census is absent or
stale for the gates now on disk, it starts `heart2.py --prove` in the background - hidden, at the lowest
ordinary priority, one lane - but only while the machine is idle. It never runs on a DEVELOPMENT tree:
there the pre-push gate is the prover, and a background prove would fight it for the CPU (a fleet during a
push starved the render gate, 2026-09-2x). Nothing here decides a verdict; heart2 writes the census and
self_arming reads it, exactly as on his Mac.

THE SHARED VOCABULARY (heart-first rule 3): on · worked · lastTs · owed, with owed None = UNKNOWN.
"""
import io
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
IS_WIN = os.name == "nt"

STORE = ".self_prove.json"
#: Busier than this (percent of the machine) and a proof does not START - he is playing, or the console is
#: working. A running proof is never killed for it: it already runs below everything he does.
#: ⚠ REG-2550 - 45 -> 75, HIS ORDER (2026-10-22): "raise the cap to 75% so it proves now". On macOS "busy" is the
#: one-minute load average over the core count (control_app._cpu_busy_pct), so every agent fleet, push gate and build
#: on his Mac counts as "not idle": it read 93% and 64% while fleets ran. MEASURED on his console that afternoon (10
#: cores): no game on screen, 4-5 GB free, his census stale (2 gates owed, 5 BLIND), and the lane said "the machine is
#: 46% busy", then "58% busy - a proof starts only when it is idle (busy for 7 min ...)" - at 45 it waited for a quiet a
#: working Mac does not have. What stands between a proof and his game is asked BEFORE this bar and is unchanged: is he
#: playing, is memory free; and a running proof still stands aside within 10 s of either (guard()). REG-1905's 6-hour
#: escape (BUSY_STARVE_S) stays for a machine busier than this for that long. On Windows "busy" is GetSystemTimes over a
#: short sample; the same bar applies there.
MAX_BUSY_TO_START = 75.0
#: REG-1905 - A WAIT FOR IDLE NEEDS A CEILING. GrokBot's PC read "the machine is 77% busy - a proof starts only when it is
#: idle" for 20 DAYS (#230, v3600 brief C2): its own driver keeps it above the bar around the clock, so no proof ever
#: started, its census never went current, and its river stayed shut the whole time while the doctor counted "busy" as a
#: healthy key. A proof already runs at nice 15 / BELOW_NORMAL with 4x deadlines (spawn), so past this many seconds of
#: UNBROKEN busy refusals - he is not playing, memory is fine - it starts anyway and says why. Proving under load can only
#: leave a gate unproved or red; it cannot open a lock a quiet proof would keep shut.
BUSY_STARVE_S = 6 * 3600
#: v3884 - BESIDE A CLOUD STREAM THE WAIT IS SHORT (his ruling 2026-11-05, "prove beside cloud"). MEASURED 11-08 ~11:00 on the
#: work ALT (an i3, SSH, read-only): 20 GetSystemTimes samples of 0.5 s read 82-88% busy (mean 84.7) - Boosteroid 60%, the
#: console's own capture of that stream 44% + 38%, its audio 33% - so MAX_BUSY_TO_START refused every proof for up to
#: BUSY_STARVE_S, and two stale BLIND verdicts v3882 had already fixed held all four of its locks shut. The load IS the
#: stream he asked proofs to run beside. While a cloud client runs (and no local game), a busy refusal starves its way in
#: after this much - the proof still runs BelowNormal / nice 15, every memory floor (REG-1502: dwm died at 690 MB free beside
#: a stream) and every stand-aside still apply, and a local game still stops it.
BUSY_STARVE_BESIDE_CLOUD_S = 30 * 60
#: A proof that ended without making the census current is not retried for this long - a failing prover
#: must not become a machine that proves in a loop all day.
RETRY_AFTER_FAIL_S = 3 * 3600
#: REG-1861 — a proof that ended because no lane could build a sandbox waits this long, not RETRY_AFTER_FAIL_S: the
#: cause is usually the copier's ceiling or the disk, both fixable within minutes. Bounded, never the 10 s rescue
#: cadence: check() can say yes while copytree still fails (an unreadable file), and that must not respawn a
#: ~220 MB sandbox every ten seconds on a PC with no RAM to spare.
RETRY_AFTER_SANDBOX_S = 15 * 60
#: Windows priority class for the prover: BELOW_NORMAL, so his game and the console always come first.
_BELOW_NORMAL = 0x00004000
_CREATE_NO_WINDOW = 0x08000000

# ⚠⚠ REG-1502 — A PROOF NEVER RUNS BESIDE HIS GAME. MEASURED 2026-09-29 on the ALT (7.9 GB): a Windows inventory prove
# (the job this lane automates, started by hand) ran five hours beside his Boosteroid session while RAM sat at 690 MB
# free; dwm.exe died of memory exhaustion eight times in an hour and Boosteroid crashed with it. The CPU gate below
# could not see it: a CLOUD client decodes on the GPU and leaves the CPU nearly idle. So "he is playing" is its own
# question - the game itself OR a client streaming it - and so is free memory. Either one stops a proof from starting,
# and either one stands a RUNNING proof aside; a proof that stood aside is not a failure and runs again once he stops.
#: exe names (lowercased) that mean "he is playing on this PC" - the game, or a cloud client streaming it
PLAY_EXES = ("boosteroid.exe", "geforcenow.exe", "nvidia geforce now.exe")
#: available memory, in MB, a proof needs to START, and below which a RUNNING proof stands aside
#: ⚠ REG-1624 (2026-09-30) - 2048 was set for a proof BESIDE a stream. MEASURED on the ALT with the game off, the
#: console relaunched and nothing else running: 1,781 MB available - so the one PC this lane exists for could never
#: start a proof at all, and he had to close things by hand. A proof never starts while he plays (the question above
#: this one), and guard() now stands a RUNNING proof aside within one rescue tick (10 s) of the game starting or
#: memory falling under the running floor. So the start bar only has to leave the proof room above that floor.
MIN_FREE_MB_TO_START = 1536
MIN_FREE_MB_WHILE_RUNNING = 1024
#: REG-1715 (#152 slice 6) - the running floor while he is MEASURED not playing. MEASURED 2026-10-02 on his ALT
#: (7.9 GB) after he closed the game: 2,070 MB free idle, and ONE proof took it to 990 MB - under the 1,024 floor
#: above - so the running proof stood aside, ten times, and 94 owed gates made no progress while the river waited
#: on them. The 1,024 floor exists for a proof BESIDE a stream (09-29: dwm died at 690 MB free with Boosteroid
#: streaming on an Iris Xe that borrows RAM as video memory). With no game and no stream, a proof may run down to
#: this; playing, it still stands aside at once, and an UNKNOWN 'is he playing' keeps the strict floor.
MIN_FREE_MB_WHILE_RUNNING_IDLE = 700
#: GBL census-lowmem - A PC THAT NEVER HAS 1,536 MB FREE STILL MAKES PROGRESS. MEASURED on his ALT 2026-10-27 (v3806,
#: 7.9 GB): 1,019 MB free with the window already sent away, "low-memory" on 69 ticks, 143 gates owed, census stale and
#: every river lock shut with no end. Under MIN_FREE_MB_TO_START, a MEASURED-idle PC with a sliceable owed list starts
#: a SMALL slice (one lane, SMALL_SLICE_MAX_GATES, SMALL_SLICE_BUDGET_S) down to this floor. It changes only whether
#: the census may make progress: frame.release still opens only on a census the proof wrote, and guard() still stands
#: the slice aside under MIN_FREE_MB_WHILE_RUNNING_IDLE or the moment he plays.
MIN_FREE_MB_TO_START_SMALL = 1000
SMALL_SLICE_MAX_GATES = 6
SMALL_SLICE_BUDGET_S = 180
#: REG-1670 — a PC proves on as many lanes as it has clear room for (heart2's HEART2_PROVE_WORKERS). His words,
#: 2026-10-01: "yea good idea" and "this is genius to scale even further maybe.. for DEANS pc he has like 16g ram or 32g
#: ram". MEASURED on his ALT that morning: one lane, a 40-gate slice in 82 minutes. One lane per LANE_BUDGET_MB free
#: (each lane runs one law at a time, a few hundred MB, so the budget keeps every lane well above the running floor),
#: one per two cores, at most MAX_PROVE_LANES (every lane is a copy of the tree on disk; heart2 caps that too). The
#: 10-second guard still stands the whole proof aside the moment memory falls under MIN_FREE_MB_WHILE_RUNNING or he
#: starts playing. His ALT at ~1.9 GB free: one lane. 3 GB and 4 cores: two. Dean's 16 GB PC: up to four.
LANE_BUDGET_MB = 1536
MAX_PROVE_LANES = 4

# ⚠⚠ REG-1511 — THE REVIEW OF v3524 FOUND THE STAND-ASIDE COULD KILL A STRANGER, FLAP, AND NEVER LET THE ALT PROVE.
#   · a finished prover's pid stayed in `_STARTED`, and the store's pid outlived a restart; `pid_alive` asks only
#     "is SOME process there", so a REUSED pid read as the running proof and got `taskkill /T /F` the first time he
#     played. Now a pid is the prover only when its BIRTH (process creation time, recorded at spawn) matches.
#   · a proof its own memory pushed under the line was killed, restarted once RAM came back, killed again - every ten
#     minutes, the census never current. Now nothing starts for STAND_ASIDE_COOLDOWN_S after a stand-aside.
#   · Boosteroid sitting in his tray counted as "playing" forever, so the ALT - the PC this lane exists for - never
#     proved and the doctor called it healthy. A cloud client then played only above a private-bytes bar - ⚠ which
#     REG-1666 MEASURED wrong (the tray held MORE than a stream): see CLOUD_EXES_JUDGED_ON_SCREEN.
#: after a proof stands aside, no new proof starts for this long (seconds) - whatever the reason was
STAND_ASIDE_COOLDOWN_S = 1800
#: #99 — ONE SLICE of a census: the owed gates, cheapest first, up to this many estimated seconds of proving (a gate's
#: registered cost x its red-proofs + 1, from gate_costs.json) and at most SLICE_MAX_GATES. A PC he plays on most of the
#: day never gave a whole census (~90 min on his Mac) one idle window, so it never wrote one and every lock stayed shut;
#: a slice fits an idle gap, and a stand-aside costs only the slice it ends.
SLICE_BUDGET_S = 600
#: REG-1454 / REG-1674 — every law run in a proof gets this many times its registered patience (the prover runs below
#: everything he does); ONE number, handed to heart2 by spawn() and used by silent_bound_s() to bound its silence
PROVER_DEADLINE_SCALE = 4
#: REG-1674 — the least a running prover may write nothing to its log before the lane calls it SILENT (seconds)
PROVER_SILENT_MIN_S = 1800
SLICE_MAX_GATES = 40
#: a gate gate_costs.json has never timed is planned at this many seconds per run
SLICE_UNKNOWN_COST_S = 30.0
#: a proof whose census is ALREADY current for its gates is left to finish its cleanup this long (seconds) before a
#: stand-aside may end it; one console tick is 600 s, so it gets exactly one tick
FINISH_GRACE_S = 600
# ⚠⚠ REG-1666 — A CLOUD CLIENT IS PLAY ONLY WHILE THE GAME IS ON HIS SCREEN, NOT WHILE THE APP IS OPEN. His words,
# 2026-10-01: "it needs to like register when im ingame and playing not just when its open" - and "make sure this logic
# is known to all routes... like nvidea play and also the local way of playing the game the way dean usually plays".
# MEASURED on his ALT that morning: the prover read "playing" from 02:29 to 10:49 and 178 proofs waited, while the
# shadow watch said "Boosteroid is open and the last reads showed no D2R HUD word" (the launcher) and later the app sat
# in the tray holding 2,190 MB private bytes - MORE than the ~2 GB a live stream was measured at, so the REG-1511
# memory bar (600 MB) could never tell idle from playing. Memory is not the signal; the screen is. THE ROUTES:
#   · the game itself (D2R.exe - Battle.net on his PC or Dean's, CrossOver on the Mac) is play while it runs, even at
#     its menu: it IS the game, and exclusive fullscreen often hides its window from the window walk (v1413), so the
#     process is the only honest witness. Battle.net alone is a launcher and was never play.
#   · a cloud client (Boosteroid, GeForce NOW) is play only while the console's ONE judge of "is the game on his
#     screen" - the shadow watch: the window finder, then the first reads of a bare Boosteroid window - says so. Its
#     library, launcher or tray icon is not the game. The judge is handed in as `game_on_screen`; when it cannot answer
#     (nobody looked, the look is stale, the shadow reader is off) the client counts as playing, as it always did.
#: exe names (lowercased) of the cloud clients judged by the screen rather than by the process - every one in PLAY_EXES
CLOUD_EXES_JUDGED_ON_SCREEN = PLAY_EXES
#: what the POSIX `ps` listing calls the game itself, as opposed to a cloud client
_POSIX_GAME = re.compile(r"D2R\.exe", re.I)
#: how long end_tree watches for the prover to be gone after it was told to end (seconds)
END_WAIT_S = 10.0


def _is_game_exe(n):
    return n.startswith("d2r") or "diabloii" in n.replace(" ", "")


#: REG-3748 (#188) - the LOCAL route's launcher: while it runs the game may start at any second (his 11-11 ruling)
LAUNCHER_EXES = ("battle.net.exe",)
_POSIX_LAUNCHER = re.compile(r"Battle\.net\.exe", re.I)


def launcher_state():
    """REG-3748 - is the local route's launcher (Battle.net) running on THIS machine? -> True | False | None (UNKNOWN)

    His words 11-12: "locally it opens battle.net and then it can be armed based on window already". MEASURED that night on
    Dean's PC: Battle.net launched the game at 17:38:18, the shadow watcher's 20-second look opened the reel 15 s later, and
    the D2 logo had already gone by. Battle.net open is the early warning; it never starts a session."""
    try:
        if IS_WIN:
            import tv_diablo as _tvd
            return _tvd._toolhelp_any(lambda name: (name or "").lower() in LAUNCHER_EXES)
        out = subprocess.run(["ps", "-Ao", "command="], capture_output=True, text=True, encoding="utf-8",
                             errors="replace", timeout=3)
        if out.returncode != 0 or not (out.stdout or "").strip():
            return None
        return any(_POSIX_LAUNCHER.search(ln) for ln in out.stdout.splitlines())
    except Exception:
        return None


def is_play_exe(name):
    """A process name (any case) that CAN mean he is playing here: the game, or a cloud client. Pure.
    Whether a cloud client is actually STREAMING is is_play_proc's question (REG-1511)."""
    n = (name or "").lower()
    return _is_game_exe(n) or n in PLAY_EXES


def is_play_proc(name, on_screen=None):
    """Does THIS process mean he is playing here? -> bool. Pure.

    REG-1666 — the game always counts (it IS the game, at its menu too). A cloud client counts only while the GAME is
    on his screen: `on_screen` False (the console looked: no game window, or the launcher) does not count; True counts;
    None (nobody could look) counts - the conservative answer, because a proof beside a live stream is what this lane
    must never be, and a proof deferred is only a proof later. Anything else (Battle.net, a browser) is not play."""
    n = (name or "").lower()
    if _is_game_exe(n):
        return True
    if n not in PLAY_EXES:
        return False
    return on_screen is not False             # every cloud client in PLAY_EXES is judged by the screen


#: what the POSIX `ps` listing is searched for - the same three names the Windows walk knows
_POSIX_PLAY = re.compile(r"D2R\.exe|Boosteroid|GeForceNOW", re.I)


def posix_play_line(line):
    """One `ps -Ao pid=,command=` line -> does it mean he is playing? Pure.

    REG-1511 — ⚠ NEVER A PYTHON PROCESS OR A .py FILE. MEASURED on his Mac: `pgrep -if` matched the prover's OWN law,
    `python .../tv/test_a_bare_boosteroid_window_must_show_the_hud.py`, so while heart2 ran it the lane read
    "playing" and stood its own proof aside - at the same offset on every restart, so the proof never finished."""
    parts = (line or "").split()
    if len(parts) < 2:
        return False
    argv = parts[1:]
    if not _POSIX_PLAY.search(" ".join(argv)):
        return False
    exe = os.path.basename(argv[0]).lower()
    if exe.startswith("python") or any(a.lower().endswith(".py") for a in argv):
        return False
    return True


def playing_state(game_on_screen=None, cloud=True):
    """Is he playing on THIS machine - the game itself, or a cloud client with the GAME on his screen?
    -> True | False | None (UNKNOWN)

    REG-1666 — `game_on_screen` is the console's one judge of whether the game is on his screen (a callable -> True |
    False | None). It is asked at most once, and only when a cloud client is running; without it, or when it cannot
    answer, a running cloud client counts as playing. The same rule on Windows and on the Mac.

    v3862 - `cloud=False` (HIS RULING 2026-11-05, "prove beside cloud"): only the LOCAL game counts; a cloud client never
    does, on screen or not. The proof lane asks it this way (proof_playing_state); every other lane keeps cloud=True."""
    seen = {}

    def _screen():
        if "v" not in seen:
            seen["v"] = _ask(game_on_screen, lambda: None)
        return seen["v"]
    try:
        if IS_WIN:
            import tv_diablo as _tvd

            def _pred(name):
                if not cloud and (name or "").lower() in PLAY_EXES:
                    return False                # v3862 - a cloud client never stops a proof
                if (name or "").lower() in CLOUD_EXES_JUDGED_ON_SCREEN:
                    return is_play_proc(name, _screen())
                return is_play_proc(name)
            return _tvd._toolhelp_any(_pred)
        out = subprocess.run(["ps", "-Ao", "pid=,command="], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=3)
        lines = [ln for ln in (out.stdout or "").splitlines() if ln.strip()]
        if out.returncode != 0 or not lines:
            return None                        # no listing is not "nobody is playing" [[zero-needs-a-denominator]]
        hits = [ln for ln in lines if posix_play_line(ln)]
        if any(_POSIX_GAME.search(ln) for ln in hits):
            return True                        # the game itself (D2R.exe under CrossOver)
        if not cloud:
            return False                       # v3862 - a cloud client never stops a proof
        return bool(hits) and _screen() is not False      # a cloud client: only with the game on his screen
    except Exception:
        return None


#: v3863 (#241, his ruling 2026-11-03 ~23:10 IST: "thats enough ram for his console to prove himself" - Dean's 32 GB PC had
#: 8.3 GB free with D2R open, and its prover had not run in 27 h because a local game stopped every proof and his PC is on
#: only while he plays). A proof may run BESIDE the local game while this much memory stays free; under it the game wins
#: and the proof stands aside, as REG-1624/1666 decided on the 8 GB ALT (which stays below it with the game open). The
#: prover already runs at BelowNormal / nice 15 with no window.
BESIDE_GAME_FREE_MB = 4096


def cloud_streaming():
    """v3884 - a cloud client (PLAY_EXES: Boosteroid, GeForce NOW) runs on this PC and the local game does not.
    -> True | False | None (the process list could not be read - UNKNOWN, so the long wait stands)"""
    try:
        if IS_WIN:
            import tv_diablo as _tvd
            cl = _tvd._toolhelp_any(lambda name: (name or "").lower() in PLAY_EXES)
            if cl is not True:
                return cl
            game = _tvd._toolhelp_any(lambda name: (name or "").lower() == "d2r.exe")
            return None if game is None else (not game)
        out = subprocess.run(["ps", "-Ao", "pid=,command="], capture_output=True, text=True, encoding="utf-8", errors="replace",
                             timeout=3)
        lines = [ln for ln in (out.stdout or "").splitlines() if ln.strip()]
        if out.returncode != 0 or not lines:
            return None
        hits = [ln for ln in lines if posix_play_line(ln)]
        return bool(hits) and not any(_POSIX_GAME.search(ln) for ln in hits)
    except Exception:
        return None


def proof_playing_state(game_on_screen=None, free=None):
    """v3862 - the PROOF lane's "is he playing here": the local game only (his ruling 2026-11-05, "prove beside cloud").
    MEASURED that morning: the work ALT's census was MISSING because Boosteroid + his AFK clicker read as playing forever,
    so its proof never started and its river stayed stuck. A cloud client streams a game that runs elsewhere.
    v3863 (#241) - and the local game stops a proof only while free memory is under BESIDE_GAME_FREE_MB. Free memory that
    cannot be read is UNKNOWN, so the game still wins. `free` is a law's seam; None reads free_mb()."""
    play = playing_state(game_on_screen=game_on_screen, cloud=False)
    if play is not True:
        return play
    f = free_mb() if free is None else free
    if isinstance(f, (int, float)) and not isinstance(f, bool) and f >= BESIDE_GAME_FREE_MB:
        return False                      # v3863 (#241) - the game is open, and there is room to prove beside it
    return True


_K32 = {}


def _k32():
    """Windows: a PRIVATE kernel32 with the handle prototypes set. Private because setting restype/argtypes on
    `ctypes.windll.kernel32` would change them for every other caller in the console process."""
    k = _K32.get("k")
    if k is None:
        import ctypes
        from ctypes import wintypes
        k = ctypes.WinDLL("kernel32", use_last_error=True)
        k.OpenProcess.restype = wintypes.HANDLE
        k.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        k.CloseHandle.argtypes = (wintypes.HANDLE,)
        k.GetProcessTimes.restype = wintypes.BOOL
        k.GetProcessTimes.argtypes = (wintypes.HANDLE,) + (ctypes.POINTER(wintypes.FILETIME),) * 4
        _K32["k"] = k
    return k


_PS_EXE = {"path": None, "looked": False}


def _ps_exe():
    """The ABSOLUTE path of ps, looked up once. -> str | None (REG-1653 - posix_spawn needs a directory in the exe)"""
    if not _PS_EXE["looked"]:
        _PS_EXE["looked"] = True
        try:
            import shutil as _sh
            for c in ("/bin/ps", "/usr/bin/ps", _sh.which("ps")):
                if c and os.path.isabs(c) and os.path.isfile(c) and os.access(c, os.X_OK):
                    _PS_EXE["path"] = c
                    break
        except Exception:
            _PS_EXE["path"] = None
    return _PS_EXE["path"]


# proc_birth returns this, and nothing else, when ps says the pid is a zombie. It is not a birth
# and it is not "ps did not answer": identity() treats it as ended. A failed read stays None.
_PROC_EXITED = object()


def proc_birth(pid):
    """When was process `pid` created? -> an opaque string that is equal only for the SAME process, or None when it
    cannot be told (dead, refused, no tool). A zombie returns _PROC_EXITED, never None and never its birth. Never raises.

    REG-1511 — a pid is a number the system hands out again; its creation time is not. Windows: OpenProcess +
    GetProcessTimes (100 ns ticks). POSIX: `ps -o stat=,lstart=` in UTC and the C locale, so a console restarted
    under another locale or zone reads the same string for the same process."""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return None
    if pid <= 0:
        return None
    try:
        if IS_WIN:
            import ctypes
            from ctypes import wintypes
            k = _k32()
            h = k.OpenProcess(0x1000, False, pid)       # PROCESS_QUERY_LIMITED_INFORMATION
            if not h:
                return None
            try:
                ft = [wintypes.FILETIME() for _ in range(4)]
                if not k.GetProcessTimes(h, *[ctypes.byref(f) for f in ft]):
                    return None
                v = (int(ft[0].dwHighDateTime) << 32) | int(ft[0].dwLowDateTime)
                return ("ft:%d" % v) if v else None
            finally:
                k.CloseHandle(h)
        # ⚠⚠ v3540 REG-1653 — SPAWN, NEVER FORK: this runs INSIDE his console (guard() on the 10 s rescue loop, since
        # REG-1643 on every healthy tick of a running proof), which has the Objective-C runtime loaded. A bare "ps" and
        # the default close_fds=True take fork_exec, and a fork of such a process can wedge between fork and exec at
        # 0% CPU - measured once for 28 minutes (test_the_doctor_never_forks_a_quartz_process). An ABSOLUTE exe,
        # close_fds=False and no cwd take posix_spawn. Raised by the v3537 cross-family eye.
        _ps = _ps_exe()
        if not _ps:
            return None                         # no absolute ps on this machine - who it is cannot be read
        r = subprocess.run([_ps, "-o", "stat=,lstart=", "-p", str(pid)], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", close_fds=False,
                           timeout=3, env=dict(os.environ, LC_ALL="C", TZ="UTC"))
        parts = (r.stdout or "").split()
        if r.returncode != 0 or len(parts) < 2:
            return None                         # gone, or ps did not answer: who it is cannot be read
        # A zombie still has its birth. kill(0) says it is alive, and this string would MATCH the birth
        # recorded at spawn, so identity() would keep the dead proof as running. Stat Z is an exit.
        # Measured: a defunct prover held the lane on "could not be read", the census stayed stale,
        # and the river locks stayed shut. [[the-unjoined-end]]
        if str(parts[0]).upper().startswith("Z"):
            return _PROC_EXITED
        return "ps:" + " ".join(parts[1:])
    except Exception:
        return None


def free_mb():
    """Available physical memory in MB, or None when it cannot be measured (UNKNOWN, never 'plenty').

    ⚠⚠ REG-1825 — ONE READER, AND IT IS child_guard's. This was a second copy, and its Linux arm read
    SC_AVPHYS_PAGES, which is MemFree: the pages nothing holds, page cache left out. MEASURED on GrokBot's box
    2026-10-06: `free -m` said 657 MB free and 4918 MB AVAILABLE, and this lane answered "only 643 MB of memory
    free - a proof starts at 1536 MB" on every tick, so the heart never proved there, reel.route stayed shut and
    its 8 reels sat at ROUTE for two days. child_guard._free_ram_mb_read already asks each OS for what it would
    hand out: Windows ullAvailPhys, Linux MemAvailable, macOS free + inactive + speculative. A Linux with no
    MemAvailable line is None (UNKNOWN), never MemFree dressed as available. [[copy-drift]]
    """
    try:
        import child_guard as _cg
        return _cg._free_ram_mb_read()
    except Exception:
        return None


#: REG-1845 — what heart2 prints when no lane could copy the repo: the proof then exits with the census unwritten.
NO_SANDBOX_MARK = "no lane could build a sandbox"


def sandbox_ready():
    """Can a proof copy this repo into a sandbox right now? -> (True, "") | (False, why) | (None, why) UNKNOWN

    REG-1845 — asked of safe_copy's own refusal rule (check(), the one copy() applies before it writes), toward the
    temp volume heart2 builds its sandboxes on. MEASURED on his Mac 2026-10-06: every lane of every proof was refused
    at 420.4 MB over the 400 MB ceiling, each proof exited with the census unwritten, and the lane booked that as a
    failed proof and waited 3 h before trying the same refused copy again."""
    try:
        import tempfile
        import safe_copy as _sc
        rc, why = _sc.check(REPO, os.path.join(tempfile.gettempdir(), "heart2.preflight", "repo"))
    except Exception as e:
        # REG-1861 - UNKNOWN, and a proof never starts on it: heart2 would fail to build its sandbox the same way
        return None, "the copier could not be asked (%s)" % type(e).__name__
    return (True, "") if rc == 0 else (False, str(why or "safe_copy refused with no reason"))


def _log_says_no_sandbox(log_path, start=None):
    """Did THIS run of the prover end because no lane could build a sandbox? -> bool. Never raises.

    REG-1862 (the v3598 cross-family eye) - it read the last 8 KB and took the mark anywhere after the last banner, so
    a prover that died before its banner (an import error's traceback) after an older run's mark was booked as a
    sandbox refusal. `start` is the log's size when this run was spawned: only the bytes this run wrote are read, and
    the mark must be their last non-empty line. A run that wrote nothing, or anything after the mark, is not this.
    `start` None (a record from before it was kept) reads the tail with the same last-line rule."""
    try:
        with io.open(log_path, "rb") as fh:
            fh.seek(0, 2)
            end = fh.tell()
            begin = start if isinstance(start, int) and not isinstance(start, bool) and 0 <= start <= end else None
            fh.seek(max(0 if begin is None else begin, end - 65536))
            text = fh.read().decode("utf-8", "replace")
    except Exception:
        return False
    lines = [ln for ln in text.splitlines() if ln.strip()]
    return bool(lines) and NO_SANDBOX_MARK in lines[-1]


#: #186 - the census's own summary line (heart2.prove, --reuse): served of asked, and what it banked; REG-3046 - and how
#: many of the served another PC carried (a prover before REG-3046 does not say, and that reads UNKNOWN, never 0)
_REUSE_LINE = re.compile(r"#186 CENSUS CACHE: (\d+) of (\d+) proof\(s\) reused"
                         r"(?:[^·\n]*?not re-run; (\d+) of them carried from another PC)?.*?· (\d+) proved and banked")


def _log_reuse(log_path, start=None):
    """#186 - what THIS run of the prover served from the cache and banked, in its own words. -> {served, of, banked} or
    None when this run said nothing (an older prover, the cache off, a run that died first) - UNKNOWN, never a zero.
    Only the bytes this run wrote are read (`start`, as _log_says_no_sandbox reads them); the last such line wins."""
    try:
        with io.open(log_path, "rb") as fh:
            fh.seek(0, 2)
            end = fh.tell()
            begin = start if isinstance(start, int) and not isinstance(start, bool) and 0 <= start <= end else None
            if begin is None:
                return None          # REG-2732 (the #231 eye on v3819) - the tail could be an EARLIER run's line
            fh.seek(max(begin, end - 262144))
            text = fh.read().decode("utf-8", "replace")
    except Exception:
        return None
    got = _REUSE_LINE.findall(text)
    if not got:
        return None
    a, b, k, c = got[-1]
    out = {"served": int(a), "of": int(b), "banked": int(c)}
    if k != "":
        out["carried"] = int(k)                     # REG-3046 - absent: this prover did not say (UNKNOWN)
    return out


def _memory_stall(mem, census, playing):
    """#193 (his ALT, 2026-10-27) - A MEMORY STAND-ASIDE NAMES THE GATES IT COULD NOT FINISH. -> None (mutates mem)

    MEASURED on the ALT: 23 stand-asides in a row, each a slice whose one gate - a recorded BLIND, so REG-1673 put it
    first and alone - took the PC under the 700 MB idle floor before it finished. The stand-aside booked a cooldown
    and forgot the slice, so 30 minutes later the planner picked the SAME gate first again: the census stayed stale,
    every lock stayed shut, and 139 cheaper gates never got a turn. A slice stood aside for MEMORY now leaves its gates
    in stalledGates for this census (merged with any already there), and the next slice proves the others first - the
    same "proved after the others" the silent-prover stall already uses. When every owed gate has stalled, the planner
    falls back to all of them. A stand-aside because he is PLAYING is not the gates' fault and names none."""
    if playing is True:
        return
    gates = [str(g) for g in (mem.get("sliceGates") or []) if g]
    if not gates:
        return
    fp = (census or {}).get("fingerprint")
    if not fp:
        return                                   # the Grok eye on v3810: an UNKNOWN census never holds a gate back
    prior = [str(g) for g in (mem.get("stalledGates") or []) if g] if mem.get("stalledFor") == fp else []
    mem.update(stalledGates=list(dict.fromkeys(prior + gates)), stalledFor=fp, stalledWhy="memory")


def stand_aside(playing, free, why=None):
    """Must a RUNNING proof stop now? -> (bool, why). Pure. UNKNOWN never stops it: it already runs below him.
    v3883 - `why` is the judge's own reason (_play_why): MEASURED 11-08 on both ALTs, no D2R.exe running and the record said
    "he started playing" at 09:23 and 09:38 - the console's judge had said yes for GitHub's import. The game's words only
    when the judge gave none."""
    if playing is True:
        return True, (why or "he started playing - a proof never runs beside his game")
    _floor = MIN_FREE_MB_WHILE_RUNNING_IDLE if playing is False else MIN_FREE_MB_WHILE_RUNNING   # REG-1715
    try:
        if free is not None and float(free) < _floor:
            return True, "only %d MB of memory left - the proof gives it back" % int(float(free))
    except (TypeError, ValueError):
        pass
    return False, ""


def identity(pid, birth):
    """Who holds `pid` now? -> True the prover this lane started · False not ours (gone, or the pid names another
    process) · None UNKNOWN (alive, and who it is cannot be read: no birth was recorded, or the read failed NOW).
    Never raises.

    ⚠⚠ v3540 REG-1652 — "COULD NOT READ" IS NOT "SOMEONE ELSE". The v3537 cross-family eye on REG-1643: is_ours()
    answered False both for a reused pid and for a proc_birth() that returned None - ps timing out at 3 s on a machine
    that is paging, ps refused, ps missing - while pid_alive() was still True. guard() and the tick read that False
    as "the proof ended": booked it, _forget() dropped the pid, and the prover went on running beside his game with
    nothing tracking it, which is the one thing this lane exists to prevent. The tick's own `unverified` branch kept
    a live pid only when NO birth had been stored, so a failed FRESH read fell through it. [[unknown-stays-unknown]]"""
    try:
        # Our own child is judged by its handle. kill(0) is true for a zombie, and a failed ps read
        # must stay UNKNOWN, so the handle is the reading that can reap an exited prover now.
        try:
            import child_guard as _cg
            held = _cg.held_exit("prover", pid)
        except Exception:
            held = None
        if held is True:
            return False
        if not pid_alive(pid):
            return False
        if birth is None:
            return None
        now = proc_birth(pid)
        if now is _PROC_EXITED:
            return False                    # ps says zombie: the prover exited, it is not still running
        if now is None:
            return None                     # alive, and who it is cannot be read right now - never "ended"
        return now == birth
    except Exception:
        return None


def is_ours(pid, birth):
    """Is `pid` alive AND the very process this lane started - the same BIRTH recorded at spawn? -> bool. Never raises.

    REG-1511 — `pid_alive` alone answers "is SOME process there". A pid is handed out again once its process ends
    (Windows reuses them quickly), so a stored pid that outlived its prover named whatever came next. No recorded
    birth (a store from before this fix, or a spawn whose birth could not be read) is NOT ours: an identity that
    cannot be checked is never trusted with a kill. REG-1652 — this is the KILL question; whether a proof is still
    running is identity(), where UNKNOWN keeps the proof tracked."""
    return identity(pid, birth) is True


def end_tree(pid, birth=None, wait_s=None):
    """End a proof THIS lane started, with its children (the laws it runs). Never raises.
    -> True when our prover is gone afterwards, False when it SURVIVED the kill.

    REG-1511 — ⚠⚠ ONLY A PID WHOSE BIRTH MATCHES IS EVER SIGNALLED. `taskkill /T /F` on a reused pid force-kills a
    stranger and everything under it (after a reboot the stale store pid can be explorer.exe). And a kill that did
    not take is reported, never assumed: taskkill can time out on a machine paging hard (the 690 MB-free afternoon),
    and a prover that survived must stay tracked, or the lane starts a second one beside it."""
    try:
        if not is_ours(pid, birth):
            return True                   # nothing of ours is there: nothing is signalled, nothing is left running
        if IS_WIN:
            subprocess.run(["taskkill", "/PID", str(int(pid)), "/T", "/F"], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=15, creationflags=_CREATE_NO_WINDOW)
        else:
            import signal
            try:
                os.killpg(int(pid), signal.SIGTERM)  # spawn() gave the prover its own session
            except ProcessLookupError:
                os.kill(int(pid), signal.SIGTERM)    # its birth matched, so this pid IS the prover; no group to end
    except Exception:
        pass
    deadline = time.time() + (END_WAIT_S if wait_s is None else float(wait_s))
    # REG-1652 - GONE MEANS PROVEN GONE: a read that fails after the signal is not a death certificate, so only a
    # definite "not ours" ends the wait; an unreadable identity runs out the clock and reports SURVIVED
    while identity(pid, birth) is not False:
        if time.time() >= deadline:
            return False                  # it SURVIVED: the caller keeps it, and asks again next tick
        time.sleep(0.2)
    return True


def enabled(env=None):
    """TV_SELF_PROVE=0 turns the lane off. -> bool"""
    return (env if env is not None else os.environ).get("TV_SELF_PROVE", "1") != "0"


def _store_path(path=None):
    if path:
        return path
    try:
        import tv_diablo as _tvd
        return os.path.join(_tvd._fixture_root(HERE), STORE)
    except ImportError:
        return os.path.join(HERE, STORE)


def load(path=None):
    """The lane's memory. -> dict ({} when it has never run; {"unreadable": why} when it would not read)"""
    p = _store_path(path)
    if not os.path.exists(p):
        return {}
    try:
        with io.open(p, encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else {"unreadable": "not an object"}
    except Exception as e:
        return {"unreadable": "%s" % type(e).__name__}


def save(d, path=None):
    p = _store_path(path)
    tmp = p + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as fh:
        json.dump(d, fh, indent=1, sort_keys=True)
    os.replace(tmp, p)


def pid_alive(pid):
    """Is `pid` a living process? -> bool. Safe on Windows.

    ⚠⚠ `os.kill(pid, 0)` IS NOT A PROBE ON WINDOWS. There, signal 0 is CTRL_C_EVENT, delivered with
    GenerateConsoleCtrlEvent - so the Unix idiom heart2 used to ask "is the sandbox owner alive?" would
    send a Ctrl-C instead. Windows asks with OpenProcess + GetExitCodeProcess, the way control_app does.
    """
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    if IS_WIN:
        try:
            import ctypes
            from ctypes import wintypes
            k32 = ctypes.windll.kernel32
            h = k32.OpenProcess(0x1000, False, pid)      # PROCESS_QUERY_LIMITED_INFORMATION
            if not h:
                return False
            try:
                code = wintypes.DWORD()
                if not k32.GetExitCodeProcess(h, ctypes.byref(code)):
                    return False
                return int(code.value) == 259          # STILL_ACTIVE
            finally:
                k32.CloseHandle(h)
        except Exception:
            return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _owed_of(h2, st):
    """#99 — the gates this census owes a proof, for the slice planner. -> {"owed", "owedGates", "owedWhy"} or {} when
    it cannot be asked (then the lane proves the whole census in one run, exactly as before - never a guess)."""
    try:
        so = h2.slice_owed(state=st)
    except Exception:
        return {}
    owed = [(str(n), int(k)) for n, k in (so.get("owed") or [])]
    return {"owed": len(owed), "owedGates": owed,
            "owedWhy": "%s; %d owed - proved a slice at a time while this PC is idle" % (so.get("why"), len(owed))}


def census_state():
    """Is THIS machine's census current for the gates on disk? -> dict

    state: current | stale | missing | unreadable | unknown. Only `current` means nothing is owed.
    """
    try:
        import heart2 as _h2
    except Exception as e:
        return {"state": "unknown", "why": "heart2 would not import (%s) - whether this PC is proven "
                                           "is UNKNOWN" % type(e).__name__}
    p = _h2.STATE
    if not os.path.exists(p):
        try:
            fp = _h2.gates_fingerprint()
        except Exception:
            fp = None
        return dict({"state": "missing", "why": "this PC has never proved its instruments", "fingerprint": fp,
                     "trustSig": (_trust_sig(_h2, fp) if fp else None)}, **_owed_of(_h2, {}))
    try:
        with io.open(p, encoding="utf-8") as fh:
            st = json.load(fh)
    except Exception as e:
        return {"state": "unreadable", "why": "the census would not parse (%s)" % type(e).__name__}
    try:
        have = _h2.gates_fingerprint()
    except Exception as e:
        return {"state": "unknown", "why": "the gate fingerprint could not be computed (%s)"
                                           % type(e).__name__}
    want = st.get("gatesFingerprint")
    out = {"proved": st.get("proved"), "declared": st.get("declared"),
           "blind": list(st.get("blind") or []), "ranAt": st.get("ranAt"),
           "fingerprint": have}
    if want != have:
        out.update(state="stale", why="the gates changed since this PC last proved them (%s != %s)"
                                      % (str(want)[:8], have[:8]))
        out.update(_owed_of(_h2, st))
    elif _rule_owed(_h2, st):
        # REG-2355 — the gates are unchanged but BLIND verdicts filed under an older heart2.BLIND_RULE are owed again:
        # without this a PC whose census already read current would keep them for ever under the fixed rule.
        _ro = _rule_owed(_h2, st)
        out.update(state="stale", why="%d BLIND verdict(s) were filed under an older blind rule and are judged again"
                                      % len(_ro))
        out.update(_owed_of(_h2, st))
    elif _env_er(_h2, st):
        # v3862 (item 4) - THIS PC'S ENVIRONMENT CHANGED: every law is proved once again under it, without the cache
        _er = _env_er(_h2, st)
        out.update(state="stale", why="this PC's environment changed (%s) - every law is proved once again under it, "
                                      "without the cache: %d owed" % (_h2.env_change_words(_er), len(_er["owed"])))
        out.update(_owed_of(_h2, st))
    else:
        out.update(state="current", why="proved for the gates on disk: %s of %s, %d blind"
                                        % (st.get("proved"), st.get("declared"), len(out["blind"])))
    out["envReprove"] = bool(_env_er(_h2, st))
    out.update(_net_of(_h2, st, out.get("state") == "current"))
    if out.get("state") == "stale":
        out["trustSig"] = _trust_sig(_h2, have)
    return out


def _trust_sig(h2, fp):
    """REG-3191 - what a trust pass would read: the gates on disk (their fingerprint) and the bank (its size and mtime).
    -> str | None (the bank cannot be read: no trust run is started on a guess). The lane starts one trust run per
    signature, so a bank an import (or a push) just grew is asked once, and an unchanged one is never asked twice."""
    try:
        bst = os.stat(h2.CACHE)
        return "%s|%d|%d" % (fp, int(bst.st_mtime_ns), int(bst.st_size))
    except Exception:
        return None


def _net_of(h2, st, current):
    """REG-3191 / REG-3192 - the safety net's view of this census. -> {"trusted", "netFinds", "netOwed"}; {} when it
    cannot be asked (an older heart2, or a census that will not answer) - then the lane runs exactly as before.

    `trusted`: the gates the census holds on another tree's proofs (REG-3191's trust pass); `netFinds`: what the net has
    FOUND here (a RED clean run, a BLIND, an INVALID) on files still on disk, each with its BUGS-ready line; `netOwed`:
    the trusted gates it has not judged yet - asked only of a CURRENT census, because the net never runs while a gate is
    owed (the census lane comes first)."""
    try:
        tr = st.get("trusted") if isinstance(st.get("trusted"), dict) else {}
        finds = h2.net_finds(st)
        unj = st.get("netUnjudged") if isinstance(st.get("netUnjudged"), dict) else {}
        out = {"trusted": len(tr),
               "netFinds": [{"gate": n, "verdict": f.get("verdict"), "at": f.get("at"), "since": f.get("since"),
                             "seen": f.get("seen"), "why": f.get("why"), "line": f.get("line")}
                            for n, f in sorted(finds.items())],
               # REG-3192 - a trusted gate the net could not judge here (an UNKNOWN or slow run): said, and asked again
               "netUnjudged": [{"gate": n, "verdict": u.get("verdict"), "at": u.get("at"), "tries": u.get("tries")}
                               for n, u in sorted(unj.items()) if isinstance(u, dict) and n in tr]}
        out["netOwed"] = [(str(n), int(k)) for n, k in h2.net_owed(st)] if current else []
        return out
    except Exception as e:
        # v3865 (GitHub's swallow ratchet) - the net's keys stay ABSENT (the wire reads that as UNKNOWN, never "no finds"),
        # and the reason is said, so "could not ask" never looks like a measured empty net
        return {"netWhy": "the safety net could not be read here (%s)" % type(e).__name__}


def _env_observe():
    """v3862 (item 4) - heart2.env_observe for THIS process; never raises, never blocks the tick."""
    try:
        import heart2 as _h2
        return _h2.env_observe()
    except Exception:
        return None, "the environment could not be observed"


def _env_er(h2, st):
    """v3862 (item 4) - heart2's open environment re-prove, or None (none open, or an older heart2 without one)."""
    try:
        er = h2.env_reprove_state(st)
    except Exception:
        return None
    return er if (er and er.get("owed")) else None


def _rule_owed(h2, st):
    """REG-2355 — heart2's own answer for the BLIND gates owed under a newer rule. -> set; empty when it cannot be asked
    (an older heart2 without the rule), so the census reads exactly as it did before."""
    try:
        return set(h2.blind_rule_owed(st))
    except Exception:
        return set()


def _git(*args, timeout=15):
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
    import git_quiet as _gq            # v3866 - on Windows a plain spawn opened a terminal over his game
    r = _gq.run(["git"] + list(args), cwd=REPO, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout, env=env)
    return r.returncode, (r.stdout or "").strip()


#: REG-1837 — TRACKED FILES THE RUNNING CONSOLE REWRITES ITSELF. `.status_worst.json` is tracked on purpose (a
#: kept evidence record, the .gitignore ruling) and control_app._status_worst_save rewrites it on every new
#: slowest request. MEASURED on his ALT 2026-10-06: its one local edit was ` M tv/.status_worst.json`, so this
#: lane said "the tree has local edits" on every tick, the census stayed STALE, frame.release stayed LOCKED and
#: the deleter refused all 416 releasable reels. The console's own record is not a development edit.
CONSOLE_OWN_RECORDS = ("tv/.status_worst.json",)


def _edits_beyond_own_records(porcelain, also=()):
    """The `git status --porcelain` lines that are not one of CONSOLE_OWN_RECORDS (or `also`). -> list. Pure.
    Callers outside this file ask tracked_edits(), which gives the rule ONE answer when it cannot be asked."""
    forgiven = set(CONSOLE_OWN_RECORDS) | set(also or ())
    out = []
    for ln in str(porcelain or "").splitlines():
        bits = ln.strip().split(None, 1)
        if not bits:
            continue
        path = bits[-1].strip().strip('"')
        # a rename is never forgiven: its other end is a file of the tree that moved
        # ⚠ REG-1927 — AND ONLY A REWRITE IS THE RECORD'S OWN. Its writers rewrite it in place (os.replace), which
        # git shows as M in either column. A deleted, added, unmerged or retyped record (` D`, `A `, `UU`, `AA`,
        # ` T`) is not that write, and every one of them was forgiven: measured, `UU tv/.status_worst.json` alone
        # gave tree_state "installed", so a tree mid-merge could prove in the background.
        if len(bits) < 2 or path not in forgiven or set(bits[0]) - {"M"}:
            out.append(ln)
    return out


def tracked_edits(porcelain, also=()):
    """REG-1898 — THE ONE DOOR EVERY READER OF A DIRTY TREE ASKS. -> (lines, None) | (None, why)

    `lines` are the porcelain rows that are local edits: the console's own records (CONSOLE_OWN_RECORDS, plus a
    caller's documented `also`) are forgiven. The v3600 cross-family look: the four readers each wrapped the rule
    themselves and gave its failure two different answers - launcher_pull blocked the pull, the fleet row, the ship
    audit and the verdict key kept the raw rows (and the key raised). ONE failure answer now: (None, why), UNKNOWN.
    What each caller DOES with UNKNOWN is its own safe direction, written at the call: the pull is blocked, the
    fleet's dirty flag is None (never clean), the ship audit claims nothing, the verdict key is None."""
    try:
        return _edits_beyond_own_records(porcelain, also), None
    except Exception as e:
        return None, "the console's own-records rule could not be asked (%s)" % type(e).__name__


def tree_state(git=None):
    """Is this an INSTALLED console (clean, at its upstream) or a development tree? -> (kind, why)

    kind: installed | dev | unknown. Only `installed` may prove in the background. A tracked record the
    console writes itself (CONSOLE_OWN_RECORDS) is not a local edit.
    """
    g = git or _git
    try:
        rc, dirty = g("status", "--porcelain", "--untracked-files=no")
        if rc != 0:
            return "unknown", "git status failed here, so this tree cannot be told apart from a dev tree"
        _ed, _ewhy = tracked_edits(dirty)
        if _ed is None:
            return "unknown", "%s, so this tree cannot be told apart from a dev tree" % _ewhy
        if _ed:
            return "dev", "the tree has local edits - the pre-push gate proves a development tree"
        rc, counts = g("rev-list", "--left-right", "--count", "@{upstream}...HEAD")
        against = ""
        if rc != 0 or not counts:
            # REG-1626 - A CHECKOUT WITH NO TRACKING BRANCH IS STILL COMPARED WITH ORIGIN. MEASURED 2026-09-30 in the
            # fleet: GrokBot's box said pull "level with origin" (fleet_origin_status compares HEAD with origin/main)
            # while this said tree-unknown and never proved - the same tree judged by two refs. Asked the fleet's ref.
            rc, counts = g("rev-list", "--left-right", "--count", "origin/main...HEAD")
            against = " (no tracking branch - compared with origin/main, as the fleet does)"
            if rc != 0 or not counts:
                return "unknown", "this checkout has no upstream and no origin/main to compare with"
        behind, ahead = [int(x) for x in counts.split()[:2]]
        if ahead:
            return "dev", "%d local commit(s) not yet on origin - the pre-push gate proves them%s" % (ahead, against)
        if behind:
            return "installed", "an installed console %d commit(s) behind origin%s" % (behind, against)
        return "installed", "an installed console, level with origin%s" % against
    except Exception as e:
        return "unknown", "git could not be asked (%s)" % type(e).__name__


#: REG-3191 - a trust run is not a proof: it reads the bank (tens of MB) and hashes the owed gates' inputs, and runs no law.
#: It needs memory for the bank, never the full proof's.
TRUST_MIN_FREE_MB = MIN_FREE_MB_TO_START_SMALL
#: REG-3191 - the refusals that hold a SLICE only because a slice is costly; a trust run is not held by them. Never his
#: game (playing), never a guess (play-unknown / mem-unknown), never a dev tree, never an environment re-prove.
TRUST_DESPITE = ("busy", "aside-cooldown", "backoff", "low-memory", "takes-fleet", "no-sandbox", "sandbox-unknown",
                 "load-unknown")


def decide(census, tree, running_pid, busy_pct, mem, now_s, on=True, playing=None, free=None, sandbox=None,
           takes_only=False, cloud=None):
    """THE ONE DECISION. Pure. -> {"start": bool, "key": str, "why": str}
    `playing` / `free` (REG-1502): None is UNKNOWN, and a proof is never started on a guess.

    REG-3191 - when a slice is held only by its own cost (TRUST_DESPITE), a stale census whose bank or gates moved since
    the last trust run starts THE TRUST PASS instead (`heart2.py --trust`: no law runs). MEASURED 2026-11-05 22:14 on
    his Mac: 'busy' for 34 min with 6 of 27 owed gates fully servable and unwritten, because the trust pass ran only
    inside a slice and a slice waits for idle."""
    d = _decide(census, tree, running_pid, busy_pct, mem, now_s, on=on, playing=playing, free=free, sandbox=sandbox,
                takes_only=takes_only, cloud=cloud)
    if d.get("start") or d.get("key") not in TRUST_DESPITE:
        return d
    t = trust_start(census, tree, mem, playing, free)
    return t if t is not None else d


def trust_start(census, tree, mem, playing, free):
    """REG-3191 - a trust run's decision, or None. Pure. Only a STALE (or missing) census, outside an environment
    re-prove, on an installed console, with him not playing and memory for the bank, and only once per trust signature
    (the gates on disk and the bank as they are now) - so an unchanged bank is never asked twice."""
    c = census or {}
    if c.get("state") not in ("stale", "missing") or c.get("envReprove"):
        return None
    sig = c.get("trustSig")
    if not sig or sig == (mem or {}).get("trustFor"):
        return None
    if not (isinstance(tree, (tuple, list)) and tree and tree[0] == "installed"):
        return None
    if playing is not False:
        return None
    try:
        free = float(free)
    except (TypeError, ValueError):
        return None
    if free != free or free < TRUST_MIN_FREE_MB:
        return None
    return {"start": True, "key": "trust", "trust": True,
            "why": "census %s (%s) - a slice is held, so THE TRUST PASS runs first: every owed gate the bank serves whole "
                   "over these bytes is written with no law run (REG-3191)" % (c.get("state"), c.get("why"))}


def _decide(census, tree, running_pid, busy_pct, mem, now_s, on=True, playing=None, free=None, sandbox=None,
            takes_only=False, cloud=None):
    """decide()'s rules for a slice (and the safety net), as they always were. Pure."""
    if not on:
        return {"start": False, "key": "off", "why": "the self-prove lane is off (TV_SELF_PROVE=0)"}
    if running_pid:
        return {"start": False, "key": "running",
                "why": "a proof is running (pid %s, since %s)" % (running_pid, mem.get("startedAt"))}
    st = (census or {}).get("state")
    _net = False
    if st == "current":
        # REG-3192 (his ruling 2026-11-05 (4)) - THE SAFETY NET: over a CURRENT census, the gates written on another
        # tree's proofs (REG-3191) are judged here, lowest priority, behind every stand-aside rule below. It holds nothing
        # shut while it waits, so with nothing for it to judge the lane is simply current.
        if not (isinstance((census or {}).get("netOwed"), list) and census.get("netOwed")):
            return {"start": False, "key": "current", "why": census.get("why") or "current"}
        _net = True
    if st == "unknown":
        return {"start": False, "key": "unknown", "why": census.get("why") or "UNKNOWN"}
    # v3844 (his ruling 2026-10-30: "the windows alt will never reach enough memory to prove itself.. maybe deans PC
    # just needs to be proving himself he has enough ram for it") - a PC named a fleet TAKER never starts a proof of
    # its own: the fleet prover (Dean) proves these bytes and the proof carrier brings them here. The status below is
    # still measured (playing, freeMb, owed), because the carrier's take waits on exactly those.
    if takes_only:
        return {"start": False, "key": "takes-fleet",
                "why": "this PC does not prove for itself - it takes the fleet prover's proofs at this HEAD "
                       "through the proof carrier"}
    kind, twhy = tree
    if kind != "installed":
        return {"start": False, "key": "dev" if kind == "dev" else "tree-unknown",
                "why": "not proving here: %s" % twhy}
    try:
        last_fail = float(mem.get("lastFailAt")) if mem.get("lastFailAt") is not None else None
    except (TypeError, ValueError):
        last_fail = now_s                                  # an unreadable failure time backs off, never races
    # REG-1845 — a proof that cannot copy the repo is not started, and the reason is the copier's own sentence. It is
    # asked again every tick, so the tick the cause is gone a proof starts: a refused copy is never the 3 h backoff.
    # `sandbox` None = not asked (a law's decide), which keeps the old behaviour.
    if isinstance(sandbox, tuple) and sandbox and sandbox[0] is False:
        return {"start": False, "key": "no-sandbox",
                "why": "a proof cannot build its sandbox here - %s. Asked again every tick; a proof starts the tick "
                       "it can" % str(sandbox[1] if len(sandbox) > 1 else "")[:220]}
    # REG-1861 - and a preflight that could not answer is UNKNOWN, never a yes
    if isinstance(sandbox, tuple) and sandbox and sandbox[0] is None:
        return {"start": False, "key": "sandbox-unknown",
                "why": "whether a proof can build its sandbox here is UNKNOWN - %s - so none is started on a guess"
                       % str(sandbox[1] if len(sandbox) > 1 else "")[:220]}
    # REG-1861 - ONE backoff, two lengths: a sandbox-class exit waits RETRY_AFTER_SANDBOX_S, every other kind 3 h
    _wait = RETRY_AFTER_SANDBOX_S if mem.get("lastFailKind") == "sandbox" else RETRY_AFTER_FAIL_S
    if last_fail is not None and mem.get("lastFailFingerprint") == (census or {}).get("fingerprint") \
            and now_s - last_fail < _wait:
        return {"start": False, "key": "backoff",
                "why": "the last proof for these gates ended without a census (%s); retrying after %s"
                       % (mem.get("lastFailWhy") or "?",
                          ("%d min" % (_wait // 60)) if _wait < 3600 else ("%d h" % (_wait // 3600)))}
    if playing is None:
        return {"start": False, "key": "play-unknown",
                "why": "whether he is playing here could not be asked - a proof is not started on a guess"}
    if playing:
        return {"start": False, "key": "playing",
                "why": "he is playing on this PC (the game or its cloud client) - a proof never starts beside it"}
    try:
        free = None if free is None else float(free)
    except (TypeError, ValueError):
        free = None
    if free is None or free != free:
        return {"start": False, "key": "mem-unknown",
                "why": "free memory could not be measured - a proof is not started on a guess"}
    _small = False
    if free < MIN_FREE_MB_TO_START and _net:
        return {"start": False, "key": "low-memory",
                "why": "only %d MB of memory free - the safety net starts only at %d MB (it is the lowest priority and "
                       "never takes a small slice)" % (int(free), MIN_FREE_MB_TO_START)}
    if free < MIN_FREE_MB_TO_START:
        _owed_g = (census or {}).get("owedGates")
        if not (playing is False and free >= MIN_FREE_MB_TO_START_SMALL and isinstance(_owed_g, list) and _owed_g):
            return {"start": False, "key": "low-memory",
                    "why": "only %d MB of memory free - a proof starts at %d MB (a small slice at %d MB when idle)"
                           % (int(free), MIN_FREE_MB_TO_START, MIN_FREE_MB_TO_START_SMALL)}
        _small = True
    # REG-1511 — A STAND-ASIDE HOLDS THE NEXT START. Simulated in the review of v3524: free RAM 2500 MB idle and 900 MB
    # with the proof running gave start, stood-aside, start, stood-aside... every 600 s tick - each run rebuilt its
    # sandbox and threw the work away, the census never went current, and the doctor called both keys healthy.
    try:
        last_aside = (float(mem.get("lastStoodAsideAt")) / 1000.0
                      if mem.get("lastStoodAsideAt") is not None else None)
    except (TypeError, ValueError):
        # the skeptic on fix24-selfprove: now_s here re-armed the cooldown on EVERY tick, so a corrupt value held the
        # lane shut for ever while the doctor called it healthy. Unreadable = no cooldown; the playing and memory
        # gates above still stand between a proof and his game.
        last_aside = None
    if last_aside is not None and now_s - last_aside < STAND_ASIDE_COOLDOWN_S:
        return {"start": False, "key": "aside-cooldown",
                "why": "a proof stood aside %d min ago (%s) - the next one waits %d min, so a proof that cannot "
                       "finish here does not start and die every tick"
                       % (int(max(0.0, now_s - last_aside) // 60), mem.get("lastStoodAsideWhy") or "?",
                          STAND_ASIDE_COOLDOWN_S // 60)}
    try:
        busy_pct = None if busy_pct is None else float(busy_pct)
    except (TypeError, ValueError):
        busy_pct = None
    if busy_pct is None or busy_pct != busy_pct:          # None, junk, or NaN: UNKNOWN, never idle
        return {"start": False, "key": "load-unknown",
                "why": "how busy this machine is could not be measured - a proof is not started on a guess"}
    if busy_pct >= MAX_BUSY_TO_START:
        try:
            _since = float(mem.get("busySince")) / 1000.0 if mem.get("busySince") is not None else None
        except (TypeError, ValueError):
            _since = None                          # unreadable: no starve claim on a guess - the run starts over
        _for = (now_s - _since) if _since is not None else None
        if _small or _net:                         # a small slice, or the safety net, never starves its way in
            _for = None
        _starve = BUSY_STARVE_BESIDE_CLOUD_S if cloud is True else BUSY_STARVE_S   # v3884 - beside a cloud stream
        if _for is not None and _for >= _starve:
            return {"start": True, "key": "start",
                    "why": ("the machine has been %.0f%% busy or more for %s - the load is a cloud stream (his ruling: prove "
                            "beside cloud), so it proves now at the lowest priority" % (MAX_BUSY_TO_START, _span(_for)))
                    if cloud is True else
                    ("the machine has been %.0f%% busy or more for %s without a break - a proof that waits for "
                     "idle here would never start, so it proves now at the lowest priority (REG-1905)"
                     % (MAX_BUSY_TO_START, _span(_for)))}
        return {"start": False, "key": "busy",
                "why": "the machine is %.0f%% busy - a proof starts only when it is idle%s" % (
                    busy_pct, (" (busy for %s; past %s it proves anyway, at the lowest priority%s)"
                               % (_span(_for), _span(_starve), " - a cloud stream is running" if cloud is True else ""))
                    if _for is not None else "")}
    if _small:
        return {"start": True, "key": "start-small", "small": True,
                "why": "census %s (%s) - only %d MB free, under the %d MB full start, so a small slice proves "
                       "(one lane, at most %d gates)" % (st, census.get("why"), int(free), MIN_FREE_MB_TO_START,
                                                         SMALL_SLICE_MAX_GATES)}
    if _net:
        return {"start": True, "key": "start", "net": True,
                "why": "census current; the SAFETY NET judges %d gate(s) another tree's proofs opened, here, at idle "
                       "(REG-3192) - a red it finds closes only the locks its law guards" % len(census.get("netOwed"))}
    return {"start": True, "key": "start",
            "why": "census %s (%s) on an idle installed console - proving" % (st, census.get("why"))}


def _span(sec):
    """A duration in his words: 40 min / 7 h / 20 d."""
    sec = max(0.0, float(sec))
    if sec < 3600:
        return "%d min" % (sec // 60)
    if sec < 2 * 86400:
        return "%d h" % (sec // 3600)
    return "%d d" % (sec // 86400)


def _gate_costs(path=None):
    """gate name -> measured seconds per run, from gate_costs.json. None when it cannot be read - UNKNOWN, not "no gate
    costs anything": every gate then plans at SLICE_UNKNOWN_COST_S and the slice's why says its sizes are a guess."""
    try:
        with io.open(path or os.path.join(HERE, "gate_costs.json"), encoding="utf-8") as fh:
            c = json.load(fh).get("costs")
        return c if isinstance(c, dict) else None
    except Exception:
        return None


def plan_slice(owed, costs=None, budget_s=None, max_gates=None, blind=None, first=None):
    """#99 — ONE SLICE of the owed gates. Pure. -> [names]

    `owed` is [(name, n_proofs)]. Cheapest first (a gate's cost x (n_proofs + 1): one clean run and one per tamper), up
    to `budget_s` and `max_gates`, and never empty while anything is owed - a gate costlier than the whole budget is a
    slice of its own rather than a gate no slice ever takes.

    REG-1673 — A RECORDED BLIND GOES FIRST, AND ALONE. `blind` is the census's BLIND list. One BLIND record shuts every
    lock on this PC (self_arming: "BLIND IS NOT STALE AND NEVER SOFTENS"), so re-proving it is the only proof that can
    change what the PC may do - and a slice writes its census only when ALL its gates are done. MEASURED on his ALT
    2026-10-01: the four REG-1668 gates proved PROVEN inside a 27-gate slice that ran 70+ minutes before any of them
    could reach the census, with the river shut the whole time. So an owed gate the census records BLIND is a slice of
    its own kind: only those gates, cheapest first, and the rest wait for the next one.

    #103-C - THEN THE SHUT LOCKS' GUARDS, ALSO A SLICE OF THEIR OWN. `first` is self_arming.owed_guard_rank()'s rank
    ({gate: n}, 0 = a guard of the lock that opens after the fewest proofs). A per-lock door opens the moment its own guards
    are proven (#156), and only when the slice holding them writes the census - so a slice of guards holds nothing else,
    the lock with the fewest owed guards first, cheapest first within it. MEASURED on the ALT 11-07: vault.sweep_start
    shut ~42 h on 26 owed guards while 71 owed laws went cheapest-first. A BLIND still goes before all of it."""
    _blind = {str(b) for b in (blind or ()) if b}
    _first = [t for t in (owed or []) if t and str(t[0]) in _blind]
    rank = {}
    if _first:
        owed = _first
    elif first:
        _guards = [t for t in (owed or []) if t and str(t[0]) in first]
        if _guards:
            owed, rank = _guards, first
    costs = costs if costs is not None else {}
    budget = SLICE_BUDGET_S if budget_s is None else budget_s
    cap = SLICE_MAX_GATES if max_gates is None else max_gates

    def est(item):
        n, k = item
        try:
            c = float(costs.get(n))
        except (TypeError, ValueError):
            c = SLICE_UNKNOWN_COST_S
        if not (c == c) or c < 0:
            c = SLICE_UNKNOWN_COST_S
        return c * (max(0, int(k)) + 1)
    out, spent = [], 0.0
    for item in sorted(owed or [], key=lambda t: (rank.get(str(t[0]), 0), est(t), t[0])):
        e = est(item)
        if out and (spent + e > budget or len(out) >= cap):
            break
        out.append(item[0])
        spent += e
    return out


def shut_lock_rank(ask=None):
    """#103-C - self_arming's rank of the owed laws that keep a door lock shut. -> {"rank", "locks", "why"}. Never raises;
    an empty rank (the lane's own order) when the ranking cannot be had. `ask` is the seam (owed_guard_rank)."""
    try:
        if ask is None:
            import self_arming as _sa
            ask = _sa.owed_guard_rank
        r = ask()
        if isinstance(r, dict) and isinstance(r.get("rank"), dict):
            return {"rank": dict(r["rank"]), "locks": list(r.get("locks") or []), "why": str(r.get("why") or "")}
    except Exception as e:
        return {"rank": {}, "locks": [], "why": "the shut locks could not be ranked (%s)" % type(e).__name__}
    return {"rank": {}, "locks": [], "why": "the shut locks' rank was not an answer"}


def lock_first_words(names, lf):
    """#103-C - what a slice drawn from the shut locks' guards says. -> str ("" when the slice holds no guard). Pure."""
    rank = (lf or {}).get("rank") or {}
    took = [n for n in (names or []) if n in rank]
    if not took:
        return ""
    want = sorted(set(rank[n] for n in took))
    locks = (lf or {}).get("locks") or []
    named = ["%s (%d owed guard(s))" % (locks[i][0], locks[i][1]) for i in want
             if i < len(locks) and isinstance(locks[i], (list, tuple)) and len(locks[i]) == 2]
    return ("the guards of the shut lock(s) first: %s - %d of this slice's %d gate(s)"
            % (", ".join(named) or "a door lock", len(took), len(names)))


def _slice_landed(census, names):
    """#99 — how many of a slice's gates the census no longer owes. -> int | None (None: the census cannot say)"""
    if not names:
        return None
    if (census or {}).get("state") == "current":
        return len(names)
    owed = (census or {}).get("owedGates")
    if not isinstance(owed, list):
        return None
    still = {str(t[0]) for t in owed if isinstance(t, (list, tuple)) and t}
    return sum(1 for n in names if n not in still)


#: What the PROVER needs that a console does not: the browser laws drive Chrome over DevTools with
#: websocket-client. MEASURED on the ALT (#50, REG-1457): once render_check could find Chrome there, all 8
#: browser cases of test_mask_encoders_agree failed with "No module named 'websocket'" - the installer never
#: put it on a Windows PC, because only the pre-push gate on his Mac had ever proved anything.
PROVER_DEPS = (("websocket", "websocket-client"),)


def ensure_prover_deps(find=None, run=None):
    """Make the prover's imports present before a proof starts. -> {"ok", "installed", "why"}. Never raises.

    The same shape as the console's boot Pillow install (control_app): hidden, bounded, `--user`, and it
    SAYS what it did. Only on Windows - his Mac and CI already carry these - and only once per missing
    package per process."""
    import importlib.util as _ilu
    find = find or _ilu.find_spec
    out = {"ok": True, "installed": [], "why": "every prover import is present"}
    missing = []
    for mod, pkg in PROVER_DEPS:
        try:
            if find(mod) is None:
                missing.append(pkg)
        except Exception:
            missing.append(pkg)
    if not missing:
        return out
    if not IS_WIN:
        out.update(ok=False, why="missing %s - not installed automatically off Windows" % ", ".join(missing))
        return out
    exe = sys.executable or "python"
    if exe.lower().endswith("pythonw.exe"):
        exe = exe[:-len("pythonw.exe")] + "python.exe"
    try:
        r = (run or subprocess.run)([exe, "-m", "pip", "install", "--user", "--quiet"] + missing,
                                    capture_output=True, text=True, encoding="utf-8", errors="replace",
                                    timeout=600, creationflags=_CREATE_NO_WINDOW if IS_WIN else 0)
        rc = getattr(r, "returncode", None)
    except Exception as e:
        out.update(ok=False, why="pip could not run (%s)" % type(e).__name__)
        return out
    if rc != 0:
        out.update(ok=False, why="pip exited %s installing %s" % (rc, ", ".join(missing)))
        return out
    out.update(installed=missing, why="installed %s for the prover" % ", ".join(missing))
    return out


def lanes_for(free, cpus):
    """REG-1670 — how many proving lanes this PC may run now. -> 1..MAX_PROVE_LANES. Pure.
    One per LANE_BUDGET_MB free, one per two cores, at most MAX_PROVE_LANES; unknown memory or cores is one lane."""
    try:
        f = None if free is None else float(free)
        c = None if cpus is None else int(cpus)
    except (TypeError, ValueError):
        return 1
    if f is None or f != f or c is None:
        return 1
    return max(1, min(int(f // LANE_BUDGET_MB), c // 2, MAX_PROVE_LANES))


#: REG-2613 (#34) - the marker that names a SELF-PROVER to child_guard's watchdog ("-X" options are free-form in
#: CPython and change nothing). Only self_prove.spawn's argv carries it: a pre-push or hand-run prover never matches.
PROVER_MARK = ("-X", "tvd_self_prove")

#: v3861 - how often the console reads the process list for a grading push (its guard runs every 10 s)
PUSH_ASK_EVERY_S = 20
#: v3861 - a hook alive this long is a push GRADING. A ci/ push's hook skips the Mac gates and exits in seconds; a stand-aside
#: books STAND_ASIDE_COOLDOWN_S, so a proof must not give up half an hour for a push that was over before the guard asked.
PUSH_GRADING_AFTER_S = 60


def _etime_s(v):
    """ps's etime ([[dd-]hh:]mm:ss) -> seconds, or None when it does not read. Pure."""
    try:
        v = str(v).strip()
        days, _, rest = v.rpartition("-")
        parts = [int(x) for x in rest.split(":")]
        if not 1 <= len(parts) <= 3:
            return None
        while len(parts) < 3:
            parts.insert(0, 0)
        return (int(days) if days else 0) * 86400 + parts[0] * 3600 + parts[1] * 60 + parts[2]
    except (TypeError, ValueError):
        return None


def process_rows(run=None):
    """v3861 - every process on this PC as [(pid, ppid, age_s | None, command)], or None when the list cannot be read.
    Never raises. posix asks ps; Windows asks CIM (no pgrep there), in a hidden window."""
    run = run or subprocess.run
    try:
        if IS_WIN:
            script = ("Get-CimInstance Win32_Process | ForEach-Object { $a = '-'; if ($_.CreationDate) { "
                      "$a = [int]((Get-Date) - $_.CreationDate).TotalSeconds }; "
                      "'{0} {1} {2} {3}' -f $_.ProcessId, $_.ParentProcessId, $a, $_.CommandLine }")
            r = run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script], capture_output=True, text=True,
                    encoding="utf-8", errors="replace", timeout=15, creationflags=_CREATE_NO_WINDOW)
        else:
            r = run(["ps", "-axo", "pid=,ppid=,etime=,command="], capture_output=True, text=True, encoding="utf-8",
                    errors="replace", timeout=15)
        if r.returncode != 0:
            return None
        rows = []
        for line in (r.stdout or "").splitlines():
            t = line.split(None, 3)
            if len(t) < 3 or not t[0].isdigit() or not t[1].isdigit():
                continue
            age = None if t[2] == "-" else (int(t[2]) if IS_WIN and t[2].isdigit() else _etime_s(t[2]))
            rows.append((t[0], t[1], age, t[3] if len(t) > 3 else ""))
        return rows
    except Exception:
        return None


def push_grading(rows, mark=PROVER_MARK[1], after_s=PUSH_GRADING_AFTER_S, self_pid=None, watching=None):
    """v3861 - IS A PUSH GRADING ON THIS PC, outside this lane's own prover? -> (True | False | None, detail). Pure.

    MEASURED 2026-11-05 ~02:00 on his Mac: the console's `heart2 --prove test_control` started 20 minutes before the
    v3860 push and kept running the same suite beside the push's own test_control. stand_aside() stops a running proof
    for two things only (his game, low memory) and decide() only refuses to START one on a busy machine, so a proof
    already running when a push begins runs through the whole gate. v3860's push #2 was refused on two timing cases that
    pass alone; that is the load that refuses a push. The push grades the bytes every PC is about to receive and the
    proof grades the bytes this PC already has, so the push goes first.

    rows: process_rows(). A pre-push hook or `git push` (tree_busy's ONE definition of running one) counts once it has
    run `after_s`, unless one of its ancestors is this lane's own prover: laws run the hook inside their fixture repos,
    and a proof that stood aside for its own law would end itself every slice. An unknown age counts: the hook IS
    running. rows None -> None (UNKNOWN), and the caller never stops a proof on a reading it never got.

    `self_pid`: a hook that is an ANCESTOR of the asking process is the push that is running it - a law inside the
    pre-push gate - never one to stand aside for. CAUGHT BY THE v3861 PUSH ITSELF: TheSelfProveYieldsToASweep asked
    _sp_yield_here() inside the pre-push, saw that very push and read "yield" on an idle fixture (green on CI, where no
    push runs). His real console is never a child of a hook, so it still yields.

    `watching` (v3898, card #206): the pids of ships that wrote they are past main and only watching GitHub's Publish
    (ships_only_watching()). Such a ship grades nothing here, so it never holds a proof or the proof import."""
    if rows is None:
        return None, "the process list could not be read"
    try:
        import tree_busy as _tb
        parent, cmd_of, age_of = {}, {}, {}
        for pid, ppid, age, cmd in rows:
            parent[str(pid)], cmd_of[str(pid)], age_of[str(pid)] = str(ppid), str(cmd or ""), age
        mine, p = set(), (str(self_pid) if self_pid is not None else None)
        while p and p not in mine and p != "0":
            mine.add(p)
            p = parent.get(p)
        hits, ships = [], []
        for pid, cmd in cmd_of.items():
            # v3896 (card #200 guard 9, REG-3678) - A SHIP COUNTS LIKE A PUSH. MEASURED 11-11 on v3895's first box
            # rehearsal (load 25): the console's `heart2 --prove test_control` slice ran beside the ship's own rehearsal
            # and the agreement laws timed out. A ship runs the main push's gates on this Mac (its readiness, its
            # rehearsal beside the CI wait, then the hook), so the proof gives it the cores for its whole run.
            ship = _tb._is_ship_command(cmd)
            if not (ship or _tb._is_hook_invocation(cmd)):
                continue
            if pid in mine:
                continue                       # the push that is running THIS process (a law inside the gate)
            # v3898 (card #206) - A SHIP THAT ONLY WATCHES PUBLISH GRADES NOTHING HERE. MEASURED 11-11 by GrokBot on his Mac:
            # 12:43, 12:48 and 13:01 IL the proof import read "a push is grading on this PC - the proof import waits for it"
            # while v3896's ship was past main and only polling GitHub's Publish (an hour on a slow one). REG-3678 counts a
            # ship for its whole run because its readiness, rehearsal and hook grade on this Mac; after main none of that runs.
            if ship and pid in (watching or ()):
                continue
            age = age_of.get(pid)
            # v3897 (REG-3705, the Grok CLI's look on v3896) - THE FLOOR IS FOR A HOOK, NEVER A SHIP. A ci/ push's hook exits in
            # seconds, so a proof does not give up half an hour for one younger than after_s; a ship runs for an hour, and its
            # first minute was a window in which the console's proof could start a slice and then grade beside the whole ship
            # (a proof already running is not stopped) - while guard 2 (tree_busy.ship_beside) has no floor at all.
            if not ship and age is not None and age < after_s:
                continue
            seen, p, ours = set(), parent.get(pid), False
            while p and p not in seen and p != "0":
                seen.add(p)
                if mark in cmd_of.get(p, "").split():
                    ours = True
                    break
                p = parent.get(p)
            if not ours:
                hits.append(pid)
                if ship:
                    ships.append(pid)
    except Exception as e:
        return None, "the process list could not be judged (%s)" % type(e).__name__
    if not hits:
        return False, ""
    if ships and len(ships) == len(hits):
        return True, "a ship is running on this PC (pid %s)" % ", ".join(sorted(ships, key=int)[:4])
    return True, "a push is grading on this PC (pid %s)" % ", ".join(sorted(hits, key=int)[:4])


#: v3898 (card #206) - a ship past its main push writes this in git's COMMON dir (every checkout and worktree of this PC reads
#: one file; never a tracked byte) while it only watches GitHub's Publish, and removes it when the watch ends
SHIP_PHASE_FILE = "ship_phase.json"
SHIP_WATCHING = "publish-watch"


def ship_phase_path(repo=None):
    """-> the marker's path in git's common dir for the checkout at `repo` (this file's own by default), or None. Read
    from the files git reads (heart2._git_common_dir), never by running git: inside a hook GIT_DIR is inherited."""
    try:
        import heart2 as _h2
        d, _why = _h2._git_common_dir(repo or os.path.dirname(HERE))
    except Exception:
        return None
    return os.path.join(d, SHIP_PHASE_FILE) if d else None


def mark_ship_watching(path, pid=None, sha=None, now=None):
    """The ship is past main and only watches Publish: say so. -> True if written. Never raises."""
    if not path:
        return False
    try:
        tmp = path + ".tmp"
        with io.open(tmp, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"pid": str(pid if pid is not None else os.getpid()), "phase": SHIP_WATCHING,
                                 "sha": str(sha or ""), "at": float(now if now is not None else time.time())}))
        os.replace(tmp, path)
        return True
    except Exception:
        return False


def clear_ship_watching(path, pid=None):
    """The watch ended: remove the marker if it is this ship's. -> True if removed. Never raises."""
    try:
        with io.open(path, encoding="utf-8") as fh:
            d = json.loads(fh.read())
        if str(d.get("pid")) != str(pid if pid is not None else os.getpid()):
            return False
        os.remove(path)
        return True
    except Exception:
        return False


def ships_only_watching(path):
    """-> the set of ship pids (strings) whose marker says they only watch Publish. An unreadable or absent marker is an
    empty set: the ship then counts as grading, which can only hold a proof longer, never run one beside a real grade."""
    try:
        with io.open(path, encoding="utf-8") as fh:
            d = json.loads(fh.read())
    except Exception:
        return set()
    return {str(d.get("pid"))} if d.get("phase") == SHIP_WATCHING and d.get("pid") else set()


def spawn(log_path, python=None, workers=None, popen=None, names=None, door=None, reuse=True, net=False, trust=False):
    """Start `heart2.py --prove` hidden and below everything he does. -> pid
    #99 — `names`: prove just these gates as ONE SLICE (`--prove NAMES --slice`); None proves the whole census.
    REG-1670 — `workers` None asks lanes_for() with the memory free right now.
    REG-3191 — `trust`: `heart2.py --trust` instead, the trust pass alone (no law runs), through the same door."""
    if workers is None:
        workers = lanes_for(free_mb(), os.cpu_count())
    py = python or sys.executable
    if IS_WIN and py.lower().endswith("pythonw.exe"):
        cand = py[:-len("pythonw.exe")] + "python.exe"   # pythonw has no stdout for the prover's log
        if os.path.exists(cand):
            py = cand
    # HEART2_DEADLINE_SCALE (REG-1454): this proof runs below everything he does, on whatever PC this is, so
    # every gate gets 4x its registered patience - measured on the ALT, a 120 s law timed out every time.
    # REG-1674 - PYTHONUNBUFFERED: the log is a FILE, so Python held heart2's verdicts in 8 KB blocks. MEASURED on his ALT
    # 2026-10-01: the log did not move from 13:13 to 14:25 while 15 gates were proved - a working prover and a hung one
    # looked the same. Unbuffered, every verdict is a line the moment it is judged, and the log's age is a heartbeat.
    env = dict(os.environ, HEART2_PROVE_WORKERS=str(int(workers)), PYTHONIOENCODING="utf-8",
               HEART2_DEADLINE_SCALE=str(PROVER_DEADLINE_SCALE), PYTHONUNBUFFERED="1")
    # v3860 - UTF-8 MODE ON WINDOWS, SAID HERE AND NOT INHERITED. The console's lane got PYTHONUTF8=1 only because
    # control_app.py puts it in os.environ at import; any other caller of spawn() (a hand runner, a script) did not,
    # and its census filed every law that pipes UTF-8 through a child as red in the ANSI codepage. MEASURED
    # 2026-11-04: the new ALT's hand-run census had at least 9 such laws UNPROVABLE, each OK under PYTHONUTF8=1 alone.
    if IS_WIN:
        env["PYTHONUTF8"] = "1"
    kw = {"cwd": HERE, "env": env, "stdin": subprocess.DEVNULL}
    if IS_WIN:
        kw["creationflags"] = _BELOW_NORMAL | _CREATE_NO_WINDOW
    else:
        # ⚠ `nice` THE COMMAND, not preexec_fn: this runs inside the console's threaded server, and
        # Python documents preexec_fn as unsafe when threads are running.
        kw["start_new_session"] = True
    # #186 (his ruling 2026-10-28) - --reuse: this census serves a PROVEN banked over byte-identical inputs and banks
    # what it proves; a plain --prove (run_gates, CI, a hand run) never opens the cache
    cmd = ([py] + list(PROVER_MARK) + [os.path.join(HERE, "heart2.py"), "--prove"]
           + ((list(names) + ["--slice"]) if names else [])
           # v3862 (item 4) - an environment re-prove never serves a proof earned under the old environment
           + (["--reuse"] if reuse else []))
    if net and names:
        cmd.append("--net")                               # REG-3192 - the safety net judges named trusted gates only
    if trust:
        cmd = [py] + list(PROVER_MARK) + [os.path.join(HERE, "heart2.py"), "--trust"]   # REG-3191 - no law runs
    if not IS_WIN and os.path.exists("/usr/bin/nice"):
        cmd = ["/usr/bin/nice", "-n", "15"] + cmd
    log = open(log_path, "ab")
    kw["stdout"] = log
    kw["stderr"] = subprocess.STDOUT
    try:
        if popen is None or door is not None:
            # REG-2613 (#34) - THE PROVER GOES THROUGH child_guard'S ONE DOOR: the console that spawns it OWNS it.
            # Windows: a Job Object with KILL_ON_JOB_CLOSE, so Dean's console closing ends heart2 AND every gate it
            # started; POSIX: its own session, ended as a tree. The door ends a previous prover of this checkout
            # first, and the watchdog ends one whose console is gone. Its creationflags (below normal, no window)
            # ride through unchanged. A law's recording `popen` alone never enters the real door's ledger: a fake
            # pid recorded there would be ended - by pid - on the next real spawn.
            p = (door or _guard_spawn)("prover", cmd, popen=popen, **kw)
        else:
            p = popen(cmd, **kw)
    finally:
        log.close()                       # the child holds its own handle
    return p.pid


def _guard_spawn(role, argv, popen=None, **kw):
    import child_guard                    # imported at spawn, never at import: the pre-push gate loads no guard
    return child_guard.spawn(role, argv, popen=popen, **kw)


_CONSOLE = []


def console_id():
    """REG-2613 - THIS console process: pid and birth. A prover started by another console life was ended with it
    (child_guard), which is a stand-aside, not a failed proof."""
    if not _CONSOLE:
        _CONSOLE.append("%d:%s" % (os.getpid(), proc_birth(os.getpid())))
    return _CONSOLE[0]


#: ⚠ second eye (Grok, 2026-09-29): the pid of a proof THIS process started, kept in memory too. If saving
#: the lane's store failed right after a spawn, the next tick read no pid and started a SECOND prover - and
#: another every ten minutes after that. The store is the record; this is the backstop.
#: REG-1511 — it carries the prover's BIRTH too, and is emptied the moment that proof ends (see _forget): a finished
#: prover's pid held here for the console's whole life was the pid a later stand-aside killed.
_STARTED = {"pid": None, "birth": None}

#: REG-2483 (#170) - the door a running proof's keep-awake hold goes through. None = keep_awake.hold_for_pid, asked
#: only for a REAL prover; a law's recording spawn hands a stand-in pid, and nothing is held for a process that is not
#: there. A law sets its own door here to watch both the spawn and the adopted-prover holds.
AWAKE_DOOR = None

#: REG-2483 (#170) - THE MACHINE DOORS AS THIS MODULE DEFINED THEM, captured at import. A pid is held awake for real
#: only when THESE started it or verified it. MEASURED in the review of the first cut, 2026-10-22: "real" was judged
#: from spawn_fn alone, and the REG-1628 chain law stubs SP.spawn instead (its spawn is "a recorder, never a process") -
#: every run started three REAL `caffeinate -i -w 5151`, and with any process holding pid 5151 the caffeinate was
#: reparented to launchd and kept the Mac awake after the law had exited, owned by nobody. A stand-in pid names
#: whatever process happens to own that number; holding it holds a stranger.
_REAL_DOORS = {"spawn": spawn, "pid_alive": pid_alive, "proc_birth": proc_birth, "identity": identity}


def _real_prover(spawn_fn, *doors):
    """REG-2483 - did this module's OWN doors start or verify the pid? -> bool. Never raises.

    False when a law handed its own spawn_fn, or put a stand-in on any of `doors` (spawn for a pid it just started;
    pid_alive, proc_birth and identity for a running prover it adopted) - each is looked up in this module as the tick
    calls it, so a stand-in is seen exactly where it acts."""
    try:
        if spawn_fn is not None:
            return False
        g = globals()
        return all(g.get(d) is _REAL_DOORS.get(d) for d in doors) and bool(doors)
    except Exception:
        return False


def _hold_awake(pid, real=True):
    """REG-2483 (#170) - his ruling 2026-10-21: keep the PC awake ONLY while a proof runs. -> the door's answer | None

    keep_awake binds the hold to the prover's pid (a watcher thread on Windows, `caffeinate -w` on macOS), so it is
    released when the prover ends - finished, stood aside, stalled or crashed - and never outlives the work. Never
    raises: a hold that could not be taken leaves the proof running and the PC sleeping as it always would."""
    door = AWAKE_DOOR
    if door is None:
        if not real or not pid:
            return None
        try:
            import keep_awake as _ka
            door = _ka.hold_for_pid
        except Exception as e:
            return {"held": False, "pid": pid, "why": "keep_awake would not import (%s)" % type(e).__name__}
    try:
        return door(pid, "a heart proof is running")
    except Exception as e:
        return {"held": False, "pid": pid, "why": "the keep-awake door raised (%s)" % type(e).__name__}


def tick(now_s=None, busy=None, tree=None, census=None, path=None, spawn_fn=None, env=None,
         playing=None, free=None, kill_fn=None, sandbox=None, takes_only=False, lock_rank=None, play_why=None,
         play_key=None):
    """One pass of the lane. NEVER raises - it runs inside the rescue loop that also watches whether the
    console can still answer its own port. -> the lane's status in the shared vocabulary.
    `playing` / `free` are callables or values (REG-1502); None asks this machine. #103-C - `lock_rank` (a callable,
    self_arming.owed_guard_rank's shape) ranks the shut locks' guards; None ranks them only for a census this tick read
    itself, so a census handed in is never ranked against this PC's real one."""
    try:
        return _tick(now_s, busy, tree, census, path, spawn_fn, env, playing, free, kill_fn, sandbox, takes_only,
                     lock_rank, play_why, play_key)
    except Exception as e:
        return {"on": enabled(env), "worked": None, "lastTs": None, "owed": None, "key": "raised",
                "say": "the self-prove tick raised %s - nothing was started" % type(e).__name__}


def guard(now_s=None, path=None, playing=None, free=None, kill_fn=None, _tick=None, busy=None):
    """REG-1624 — THE FAST STAND-ASIDE. -> None (no proof running, or nothing to do) | the tick's status

    His words, 2026-09-30: "the shadow reader is always on when the game is on regardless of the console" - "everything
    should work smoothly regardless of each other". The lane's tick runs every 10 minutes, so a proof could run beside
    his game for up to ten of them. This is asked on every rescue tick (10 s) WHILE a proof this lane started is
    running, and asks only the two cheap questions - is he playing, how much memory is left. When stand_aside() says
    go, it runs the whole tick at once, which kills the prover, books the stand-aside and starts the cooldown exactly
    as it always has: one door for the kill. Never raises."""
    try:
        mem = load(path)
        pid = mem.get("pid") or _STARTED.get("pid")
        if not pid:
            return None
        # REG-1643 (the v3535 cross-family eye) - "is a proof still running" asks WHO, not only whether some process
        # holds the number: Windows hands an ended prover's pid to the next process, so pid_alive() alone kept this
        # fast path reading a stranger as the prover and the ended slice waited for the 10-minute tick - the tick and
        # the kill both ask is_ours(). No recorded birth (a store from before REG-1511) keeps the old answer; the
        # tick then treats a live one as running-unverified.
        birth = mem.get("pidBirth") if mem.get("pid") else _STARTED.get("birth")
        # REG-1625 - CONSECUTIVE, NOT ONE A TICK. MEASURED on the ALT 2026-09-30: its first slice (40 gates) took about a
        # minute, then the lane waited out the rest of its 10-minute tick - 663 owed gates would have needed ~3 hours of
        # game-off time. A slice that has ENDED is booked now, and the tick starts the next one if the PC is still idle
        # (every start rule still applies: not playing, the memory bar, cooldowns, backoff).
        # REG-1628 - AND IT IS HANDED THE LOAD PROBE THE LANE'S OWN TICK USES. MEASURED on the ALT on v3534: slices still
        # started only on the 10-minute tick (23:13:24, then 23:23:32). This call booked the ended slice and then decide()
        # met busy=None - "load-unknown", never started on a guess - so the next slice waited for the tick after all.
        # REG-1652 - only a DEFINITE "not ours" is an ended proof; alive-but-unreadable is still running
        alive = identity(pid, birth) is not False
        # REG-1671 (the v3542 cross-family eye) - AND THE CONSOLE'S OWN "is he playing" JUDGE. Without it the chained tick
        # asked playing_state() with no screen judge, so Boosteroid or GeForce NOW merely open in the tray read as
        # playing and the next slice waited for the 10-minute tick - REG-1625 again, on the machine REG-1666 was for.
        if not alive:
            return (_tick or tick)(now_s=now_s, path=path, kill_fn=kill_fn, busy=busy, playing=playing, free=free)
        play_now = _ask(playing, proof_playing_state)
        play_why = _play_why(playing)
        play_key = _play_key(playing)
        free_now = _ask(free, free_mb)
        aside, _why = stand_aside(play_now, free_now, why=play_why)
        if not aside:
            return None
        return (_tick or tick)(now_s=now_s, path=path, playing=play_now, free=free_now, kill_fn=kill_fn, play_why=play_why,
                               play_key=play_key)
    except Exception as e:
        return {"on": None, "worked": None, "lastTs": None, "owed": None, "key": "raised",
                "say": "the self-prove guard raised %s - the tick will ask again" % type(e).__name__}


def log_silence(log_path, now_s):
    """REG-1674 — how long the prover's log has been still, and its last line. -> (seconds | None, str | None)

    None when the log cannot be read: UNKNOWN, never "silent" - a lane must not end a proof on a reading it never got."""
    try:
        age = max(0.0, float(now_s) - os.path.getmtime(log_path))
    except Exception:
        return None, None
    last = None
    try:
        with io.open(log_path, "rb") as fh:
            fh.seek(0, 2)
            fh.seek(max(0, fh.tell() - 4096))
            tail = fh.read().decode("utf-8", "replace").splitlines()
        tail = [ln.strip() for ln in tail if ln.strip()]
        last = tail[-1][:160] if tail else None
    except Exception:
        pass
    return age, last


def silent_bound_s(names, scale=None, timeouts=None):
    """REG-1674 — how long THIS slice's prover may write nothing and still be honest. -> int seconds. Never raises.

    heart2 kills every law run at its deadline (the gate's registered timeout x the deadline scale), and its log is
    unbuffered, so every proof verdict is a line when it is judged. The longest honest silence between two lines is
    three runs: one gate's closing clean run (REG-1669), then the next gate's clean run and its first tampered run.
    Past 3 x scale x the slice's largest timeout (+ 10 min for its sandbox), heart2 ITSELF is stuck, never a law. A
    gate the registry does not know is bounded by the largest timeout any gate carries."""
    try:
        if timeouts is None:
            import run_gates as _rg
            timeouts = {g.name: getattr(g, "timeout", 180) for g in _rg.GATES}
        top = max([float(v) for v in timeouts.values()] or [180.0])
        per = [float(timeouts.get(n, top)) for n in (names or [])] or [top]
        sc = float(PROVER_DEADLINE_SCALE if scale is None else scale)
        return int(max(PROVER_SILENT_MIN_S, 3 * sc * max(per) + 600))
    except Exception:
        return int(3 * PROVER_DEADLINE_SCALE * 900 + 600)       # the registry would not read: the widest honest bound


def _int(v):
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


def _play_why(v):
    """v3883 - the reason a callable stand-aside judge gave for its last yes (its `.why`, set on each call) -> str | None.
    None: no reason given, so the yes is the game's (the words before v3883)."""
    w = getattr(v, "why", None) if callable(v) else None
    return w if isinstance(w, str) and w.strip() else None


def _play_key(v):
    """v3898 (card #207) - the judge's own KEY for its last yes (its `.key`: push-grading, sweep-reading, import-first), read
    like its `.why`. -> a wire-safe key | None (None: the yes is the game's)."""
    k = getattr(v, "key", None) if callable(v) else None
    return k if isinstance(k, str) and re.match(r"^[a-z][a-z-]{0,31}$", k) and k != "playing" else None


def _ask(v, probe):
    try:
        return (v() if callable(v) else v) if v is not None else probe()
    except Exception:
        return None


def _forget(mem):
    """The proof this lane was tracking is over (ended, or stood aside and gone): drop every trace of it."""
    for k in ("pid", "pidBirth", "startedFor", "finishingSince", "standingAside", "standingAsideForMemory", "sliceGates",
              "logFrom", "startedBy", "net", "trust"):
        mem.pop(k, None)
    _STARTED.update(pid=None, birth=None)


def _tick(now_s, busy, tree, census, path, spawn_fn, env, playing=None, free=None, kill_fn=None, sandbox=None,
          takes_only=False, lock_rank=None, play_why=None, play_key=None):
    _rank_here = lock_rank is not None or census is None     # #103-C - the rank speaks only for the census it ranks
    now_s = time.time() if now_s is None else now_s
    now_ms = int(now_s * 1000)
    play_now = _ask(playing, proof_playing_state)
    play_why = play_why or _play_why(playing)              # v3883 - the judge's own reason, read right after its call
    play_key = play_key or _play_key(playing)              # v3898 (#207) - and its key, read with it
    free_now = _ask(free, free_mb)
    mem = load(path)
    if mem.get("unreadable"):
        return {"on": enabled(env), "worked": None, "lastTs": None, "owed": None, "key": "store-unreadable",
                "say": "the self-prove lane's memory would not read (%s) - UNKNOWN" % mem["unreadable"]}
    if census is None:
        _env_observe()                      # v3862 (item 4) - the console's own lane is the one judge of its environment
        census = census_state()
    if not isinstance(census, dict):
        census = {"state": "unknown", "why": "the census reading was not a record"}
    pid, birth = mem.get("pid"), mem.get("pidBirth")
    if not pid and _STARTED["pid"]:
        if identity(_STARTED["pid"], _STARTED.get("birth")) is not False:     # REG-1652 - unknown is not gone
            pid, birth = _STARTED["pid"], _STARTED.get("birth")   # the store lost it; this process did not
        else:
            _STARTED.update(pid=None, birth=None)          # it ended (or its pid moved on) while the store had lost it
    _who = identity(pid, birth) if pid else False
    running = pid if _who is True else None
    # the skeptic on fix24-selfprove: a store from before REG-1511 (or a spawn whose birth could not be read) holds a
    # LIVE pid with no birth. is_ours() rightly refuses to trust it with a kill, but the tick then booked it as ENDED -
    # a failure and a 3 h backoff, the pid forgotten, and a second prover could start beside the first. UNVERIFIED:
    # left alone, not booked, and no new proof until that pid is gone.
    # REG-1652 - AND THE SAME FOR A STORED BIRTH THAT CANNOT BE READ NOW (ps timing out under memory pressure): this
    # required `birth is None`, so a failed fresh read fell through to "ended" and the prover was forgotten alive.
    unverified = bool(pid) and _who is None
    # REG-1511 — A PROOF WHOSE CENSUS IS ALREADY CURRENT FOR ITS GATES HAS DONE ITS WORK; it is only cleaning up
    # (heart2 removes its sandbox after the write). Booked as worked NOW, once, and left to finish for one tick: a
    # kill there cost the booking, and one landing inside heart2's plain census write left it truncated for good.
    finishing = bool(running) and census.get("state") == "current" and mem.get("startedFor") is not None \
        and census.get("fingerprint") == mem.get("startedFor") and not mem.get("net")     # REG-3192 - not the net's
    if finishing and not mem.get("finishingSince"):
        mem.update(worked=_int(mem.get("worked")) + 1, lastTs=now_ms, lastOk=census.get("why"),
                   finishingSince=now_ms)
    aside, aside_why = stand_aside(play_now, free_now, why=play_why) if running else (False, "")
    if aside and finishing and now_ms - _int(mem.get("finishingSince")) < FINISH_GRACE_S * 1000:
        aside, aside_why = False, ""                       # finishing - still running a tick later is a hang
    # REG-1674 — A PROVER THAT HAS GONE SILENT IS ENDED THROUGH THE SAME DOOR, AND SAYS SO. His ask, 2026-10-01, after
    # the ALT's log sat still for 70 minutes and nobody could tell a working prover from a hung one: "a stale safeguard
    # for this so it doesnt happen future wise". The log is unbuffered (spawn), so its age is a heartbeat; past this
    # slice's honest bound (silent_bound_s) heart2 itself is stuck. It is ended, its gates stay owed and are proved
    # AFTER the others (a hung gate must not hold every other proof - and the river - behind it), and the lane's key
    # says "silent", which the console doctor, the fleet beacon and the river's stuck line all read.
    _quiet, _last = log_silence(_store_path(path) + ".log", now_s) if running else (None, None)
    _bound = silent_bound_s(mem.get("sliceGates")) if running else None
    silent = bool(running) and not aside and not finishing and _quiet is not None and _quiet > _bound
    stall_gone, stall_why = None, ""
    if silent:
        stall_why = ("the prover wrote nothing for %d min - past this slice's honest bound of %d min, so heart2 itself "
                     "was stuck, not a law (its last line: %s). It was ended; its %d gate(s) stay owed and are proved "
                     "after the others" % (_quiet // 60, _bound // 60, _last or "none",
                                           len(mem.get("sliceGates") or [])))
        stall_gone = bool((kill_fn or end_tree)(running, birth))
        if stall_gone:
            mem.update(stalled=_int(mem.get("stalled")) + 1, lastStallAt=now_ms, lastStallWhy=stall_why,
                       stalledGates=list(mem.get("sliceGates") or []), stalledFor=census.get("fingerprint"))
            _forget(mem)
            pid = running = None
        else:
            mem.update(stallSurvived=_int(mem.get("stallSurvived")) + 1, pid=running, pidBirth=birth)
    gone = None
    if aside:
        # REG-1502 — stood aside, not failed: no failure count, no 3 h backoff; REG-1511 — a cooldown, and a kill
        # that did not take keeps the prover tracked instead of forgetting a process that is still running.
        gone = bool((kill_fn or end_tree)(running, birth))
        if gone:
            mem.update(stoodAside=_int(mem.get("stoodAside")) + 1, lastStoodAsideAt=now_ms,
                       lastStoodAsideWhy=aside_why)
            _memory_stall(mem, census, play_now)               # #193 - before _forget drops the slice's gates
            _forget(mem)
            pid = running = None
        else:
            mem.update(asideSurvived=_int(mem.get("asideSurvived")) + 1, lastAsideSurvivedAt=now_ms,
                       standingAside=aside_why, standingAsideForMemory=(play_now is not True), pid=running,
                       pidBirth=birth)
    if pid and not running and not unverified:
        # #186 - what the ended prover served and banked, in its own words (kept until a later run says otherwise)
        _ru = _log_reuse(_store_path(path) + ".log", mem.get("logFrom"))
        if _ru is not None:
            mem["reuse"] = dict(_ru, at=now_ms)
        # the proof we started has ended (or its pid now names another process): did it leave a current census?
        if mem.get("finishingSince"):
            pass                                           # booked as worked the tick its census went current
        elif mem.get("net"):
            # REG-3192 - the safety net ended: booked on its own counters; what it judged is in the census (netFinds)
            mem.update(netWorked=_int(mem.get("netWorked")) + 1, netLastTs=now_ms)
        elif mem.get("trust"):
            # REG-3191 - the trust run ended: booked on its own counters, never a failed proof and never a backoff - what
            # it wrote is in the census, and it is asked again only when the bank or the gates move (trustFor)
            mem.update(trustWorked=_int(mem.get("trustWorked")) + 1, trustLastTs=now_ms)
        elif census.get("state") == "current":
            mem.update(worked=_int(mem.get("worked")) + 1, lastTs=now_ms, lastOk=census.get("why"))
        elif mem.get("standingAside"):
            # told to stand aside, survived that tick, ended since: a stand-aside, never a failure
            mem.update(stoodAside=_int(mem.get("stoodAside")) + 1, lastStoodAsideAt=now_ms,
                       lastStoodAsideWhy=mem.get("standingAside"))
            if mem.get("standingAsideForMemory"):
                _memory_stall(mem, census, False)              # #193 - the same naming for a slow stand-aside
        elif mem.get("sliceGates") and (_slice_landed(census, mem.get("sliceGates")) or 0) > 0:
            # #99 — a SLICE that proved its gates is progress, not a failure: the census is still owed the rest, and
            # the next slice starts on a later tick. (A slice that landed NONE falls through to the failure below.)
            _got = _slice_landed(census, mem.get("sliceGates"))
            mem.update(worked=_int(mem.get("worked")) + 1, lastTs=now_ms, slices=_int(mem.get("slices")) + 1,
                       lastOk="a slice proved %d of its %d gate(s); %s still owed"
                              % (_got, len(mem.get("sliceGates") or []), census.get("owed")))
        elif mem.get("startedFor") and census.get("fingerprint") != mem.get("startedFor"):
            # the console UPDATED while it proved: the proof spoke for the old gates. Not a failure -
            # the new gates are simply unproved, and are proved next, without the backoff.
            mem["lastMoved"] = "the gates changed during the proof (%s -> %s)" % (
                str(mem.get("startedFor"))[:8], str(census.get("fingerprint"))[:8])
        elif mem.get("startedBy") and mem.get("startedBy") != console_id():
            # REG-2613 (#34) - its console ended, and child_guard ended the prover WITH it (Windows: the Job closed;
            # POSIX: the watchdog's dead-parent sweep). Nothing was proved wrong: a stand-aside, never the 3 h backoff.
            mem.update(stoodAside=_int(mem.get("stoodAside")) + 1, lastStoodAsideAt=now_ms,
                       lastStoodAsideWhy="the console that started it ended, and the prover ended with it")
        elif _log_says_no_sandbox(_store_path(path) + ".log", mem.get("logFrom")):
            # REG-1845 — not a failed proof: no lane could copy the repo. Booked with its kind, so decide() asks the
            # copier again every tick instead of waiting 3 h for a copy that would be refused the same way.
            mem.update(lastFailAt=now_s, lastFailFingerprint=census.get("fingerprint"), lastFailKind="sandbox",
                       lastFailWhy="the proof exited because no lane could build a sandbox")
        else:
            mem.update(lastFailAt=now_s, lastFailFingerprint=census.get("fingerprint"), lastFailKind="proof",
                       lastFailWhy="census still %s after the proof exited" % census.get("state"))
        _forget(mem)
    if mem.get("lastFailAt") is not None and not mem.get("lastFailKind"):
        # REG-1845 - a record booked before the kind existed is classified once, from the proof's own log
        mem["lastFailKind"] = "sandbox" if _log_says_no_sandbox(_store_path(path) + ".log") else "proof"
    on = enabled(env)
    # REG-1845 — the copier's answer for a REAL start (a law's recording spawn hands its own, or none)
    _sb = sandbox if sandbox is not None else (
        sandbox_ready() if spawn_fn is None and not running and census.get("state") != "current" else None)
    d = decide(census, tree if tree is not None else tree_state(), running,
               busy() if callable(busy) else busy, mem, now_s, on=on, playing=play_now, free=free_now,
               sandbox=(_sb() if callable(_sb) else _sb), takes_only=takes_only,
               cloud=(cloud_streaming() if mem.get("busySince") is not None else None))   # v3884 - asked only while busy
    # v3898 (card #207, his 11-11 13:19 Fleet: his MacBook read "proving 22 checks · you are playing" - "thats not true my
    # alt windows pc ... is though") - A YIELD THAT IS NOT HIS GAME IS NEVER "playing". The console's judge says yes for a
    # push grading, a sweep reading or GitHub's import too (its .why / .key name which); decide() saw only the yes and filed
    # it as "he is playing on this PC". MEASURED on his Mac at 13:20: no D2R.exe running (proof_playing_state False), the
    # key "playing", the stand-aside "a push is grading on this PC" - v3896's ship. The judge's reason is the record's.
    if d.get("key") == "playing" and play_why:
        d = {"start": False, "key": play_key or "yield", "why": play_why}
    if stall_gone is True:
        d = {"start": False, "key": "silent", "why": stall_why}
    elif stall_gone is False:
        d = {"start": False, "key": "silent-survived",
             "why": "%s - but pid %s did not end; it stays tracked and is asked again next tick" % (stall_why, running)}
    elif d.get("key") == "running" and _quiet is not None:
        d = dict(d, why="%s - its log last moved %d min ago (this slice's bound: %d min)%s" % (
            d.get("why"), _quiet // 60, _bound // 60, ("; last line: " + _last) if _last else ""))
    if gone is True:
        d = {"start": False, "key": "stood-aside", "why": "the running proof stood aside: " + aside_why}
    elif gone is False:
        d = {"start": False, "key": "aside-survived",
             "why": "the running proof was told to stand aside (%s) but pid %s is still alive - it stays tracked, "
                    "is asked to end again next tick, and nothing new starts beside it" % (aside_why, running)}
    elif finishing and d["key"] == "running":
        d = dict(d, why="the proof made the census current (booked as worked) and is finishing its cleanup "
                        "(pid %s)" % running)
    if unverified:
        d = {"start": False, "key": "running-unverified",
             "why": ("proof pid %s is alive but its start time was never recorded (a store from before REG-1511) - it "
                     "is left to finish, never killed, and no second proof starts beside it" % pid) if birth is None
             else ("proof pid %s is alive but its start time could not be read right now - it stays tracked, is never "
                   "killed on a guess, and no second proof starts beside it; asked again next tick" % pid)}
    # REG-2483 (#170) - A PROOF THAT IS STILL RUNNING HOLDS THIS PC AWAKE, ASKED EVERY TICK. The hold is idempotent per
    # pid and ends by itself when the prover ends, so a relaunched console that ADOPTS a prover still running takes it
    # again on its first tick - the old console's hold died with it. Only a prover whose identity THIS module's own
    # doors verified: a law's stand-in process table names a pid that is not a prover at all.
    if running:
        _hold_awake(running, real=_real_prover(spawn_fn, "pid_alive", "proc_birth", "identity"))
    if d["start"]:
        try:
            if spawn_fn is None:                           # a real start, not a law's recording spawn
                mem["deps"] = ensure_prover_deps()
            log_path = _store_path(path) + ".log"
            try:
                mem["logFrom"] = os.path.getsize(log_path)    # REG-1862 - this run's output starts here
            except FileNotFoundError:
                mem["logFrom"] = 0                            # no log yet: this run's output starts at byte 0
            except OSError:
                mem["logFrom"] = None                         # start unknown: the last-line rule decides alone
            import functools as _ft
            _net = bool(d.get("net"))                         # REG-3192 - the safety net's slice
            _trust = bool(d.get("trust"))                     # REG-3191 - the trust pass alone, no slice
            _spawn_real = _ft.partial(spawn, reuse=not census.get("envReprove"))   # v3862 (item 4)
            if _net:
                _spawn_real = _ft.partial(_spawn_real, net=True)    # REG-3192 - spawned as --net over named gates
            _owed_g = census.get("netOwed") if _net else census.get("owedGates")
            _costs = _gate_costs() if isinstance(_owed_g, list) and _owed_g else None
            # REG-1674 - a slice whose prover went silent is proved AFTER every other owed gate (for these gates)
            _stuck = (set(mem.get("stalledGates") or []) if census.get("fingerprint")
                      and mem.get("stalledFor") == census.get("fingerprint") else set())
            _plan = ([t for t in _owed_g if str(t[0]) not in _stuck] or _owed_g) if isinstance(_owed_g, list) else _owed_g
            _sm = bool(d.get("small"))                     # GBL census-lowmem - short of the full start: a small slice
            # #103-C - the shut locks' guards before every other owed law (never for the net: it judges trusted gates)
            _lf = (shut_lock_rank(lock_rank) if (_rank_here and isinstance(_owed_g, list) and _owed_g and not _net)
                   else {"rank": {}, "locks": []})
            _slice = (plan_slice(_plan, _costs, blind=census.get("blind"), first=_lf["rank"])   # REG-1673 - a BLIND first
                      if isinstance(_owed_g, list) and _owed_g else None)
            if _slice and _sm:
                _slice = plan_slice(_plan, _costs, blind=census.get("blind"), first=_lf["rank"],
                                    budget_s=SMALL_SLICE_BUDGET_S, max_gates=SMALL_SLICE_MAX_GATES)
                _sp_one = spawn_fn or _spawn_real
                spawn_fn = lambda _lp, names=None, _f=_sp_one: _f(_lp, names=names, workers=1)  # noqa: E731
            _for_locks = lock_first_words(_slice, _lf)
            mem["lockFirst"] = _for_locks
            if _net and not _slice:
                raise ValueError("no safety-net slice could be planned")    # the net never proves a whole census
            if _trust:
                mem["pid"] = (spawn_fn or _spawn_real)(log_path, trust=True)
                mem["trust"] = True
                mem["trustFor"] = census.get("trustSig")       # one run per signature: a failed one is not retried
            elif _slice:
                mem["pid"] = (spawn_fn or _spawn_real)(log_path, names=_slice)
                mem["sliceGates"] = _slice
                if _net:
                    mem["net"] = True
                d = dict(d, why="%s - this slice: %d gate(s)%s%s" % (
                    census.get("owedWhy") or d["why"], len(_slice),
                    " - %s" % _for_locks if _for_locks else "",
                    "" if _costs is not None else " (gate costs unread - sized by the default guess)"))
            else:
                mem["pid"] = (spawn_fn or _spawn_real)(log_path)
            mem["pidBirth"] = proc_birth(mem["pid"])       # REG-1511 — who it is, not just its number
            if mem["pidBirth"] is _PROC_EXITED:
                # Died before ps could name it. The marker is not a birth, and the store cannot
                # hold it: the save would fail and the next tick would keep the previous record.
                mem["pidBirth"] = None
            mem["startedBy"] = console_id()                 # REG-2613 - the console that owns it (child_guard)
            _STARTED.update(pid=mem["pid"], birth=mem["pidBirth"])
            _hold_awake(mem["pid"], real=_real_prover(spawn_fn, "spawn"))  # REG-2483 - awake from its first second
            mem["startedFor"] = census.get("fingerprint")
            mem["startedAt"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now_s))
            mem["runs"] = _int(mem.get("runs")) + 1
        except Exception as e:
            d = {"start": False, "key": "spawn-failed", "why": "the prover would not start (%s)" % type(e).__name__}
            mem.update(lastFailAt=now_s, lastFailFingerprint=census.get("fingerprint"), lastFailWhy=d["why"],
                       lastFailKind="spawn")                # REG-1861 - never left as an older run's kind
            mem.pop("logFrom", None)
    # REG-1905 - the first tick of an UNBROKEN run of busy refusals; any other outcome (a start included) ends the run
    if d["key"] == "busy":
        if mem.get("busySince") is None:
            mem["busySince"] = now_ms
    elif d["key"] == "trust" or (d["key"] == "running" and mem.get("trust")):
        pass                                               # REG-3191 - a trust run is not a proof: the busy run goes on
    else:
        mem.pop("busySince", None)
    mem.update(lastKey=d["key"], lastWhy=d["why"], lastTick=now_ms)
    try:
        save(mem, path)
    except Exception:
        pass
    st = census.get("state")
    return {"on": on, "worked": _int(mem.get("worked")), "lastTs": mem.get("lastTs"),
            "owed": (0 if st == "current" else (None if st == "unknown" else
                     (census.get("owed") if isinstance(census.get("owed"), int) and census.get("owed") > 0 else 1))),
            "slices": _int(mem.get("slices")),
            # #186 - the last ended prover's own count: {served, of, banked, at}; None until one has said it (UNKNOWN)
            "reuse": (mem.get("reuse") if isinstance(mem.get("reuse"), dict) else None),
            "key": d["key"], "say": d["why"], "census": st, "blind": census.get("blind"),
            "running": bool(mem.get("pid")), "playing": play_now, "freeMb": free_now,
            "stoodAside": _int(mem.get("stoodAside")), "asideSurvived": _int(mem.get("asideSurvived")),
            # REG-1674 - the heartbeat, in the lane's own words: how long its log has been still, the bound, the stalls
            "logAgeS": (int(_quiet) if _quiet is not None else None), "silentBoundS": _bound,
            "stalled": _int(mem.get("stalled")), "lastStallWhy": mem.get("lastStallWhy"),
            # REG-3191 / REG-3192 - how many gates stand on another tree's proofs, and the safety net that judges them
            # here: owed None = UNKNOWN (an older heart2, or a census not current yet - the net waits for the census)
            "trusted": census.get("trusted") if isinstance(census.get("trusted"), int) else None,
            "netFinds": census.get("netFinds") if isinstance(census.get("netFinds"), list) else None,
            "net": {"on": on, "worked": _int(mem.get("netWorked")), "lastTs": mem.get("netLastTs"),
                    "running": bool(mem.get("pid")) and bool(mem.get("net")),
                    "owed": (len(census.get("netOwed")) if st == "current" and isinstance(census.get("netOwed"), list)
                             else None),
                    "unjudged": census.get("netUnjudged") if isinstance(census.get("netUnjudged"), list) else None},
            # REG-3191 - the lane's light trust run: owed 1 while a stale census has a bank it has not read yet
            "trust": {"on": on, "worked": _int(mem.get("trustWorked")), "lastTs": mem.get("trustLastTs"),
                      "running": bool(mem.get("pid")) and bool(mem.get("trust")),
                      "owed": (None if st == "unknown" or (st in ("stale", "missing") and not census.get("trustSig"))
                               else 1 if (st in ("stale", "missing") and census.get("trustSig") != mem.get("trustFor")
                                          and not census.get("envReprove"))
                               else 0)}}
