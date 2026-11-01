# -*- coding: utf-8 -*-
"""v3850 (Elad 18:03 IDT 2026-10-31) - THE RECORDER OUTLIVES ITS CONSOLE, UNDER ONE LEASE.

The recorder is capture_win.ps1, the ON AIR / shadow screenshotter. Until v3850 it left when the console that started
it was gone (REG-1502), because 2026-09-29 on the ALT five of them ran at once and dwm.exe died eight times in an
hour. His ruling: keep recording through a console restart, and keep exactly ONE recorder. So the rule moved from
"my parent is alive" to "I hold the lease":

  control_capture.lease holds "pid=<pid> t=<epoch ms>". The holder rewrites it every RENEW_S. A recorder that starts
  and finds a lease held by ANOTHER pid that is alive and fresher than STALE_S leaves at once (the five-captures
  shape). A lease that is stale, or whose pid is dead, is taken over. The console adopts a live lease's pid instead
  of spawning. OFF AIR still withdraws control_capture.pid, which still makes the holder leave.

capture_win.ps1 carries the same rule in PowerShell (Get-RecorderLeaseVerdict); this module is the Python side the
console, the beacon (`recorder` field for fleet_presence) and the laws read. [[copy-drift]] - the two constants are
pinned equal by test_the_recorder_holds_one_lease.
"""
import os
import re
import time

LEASE_NAME = "control_capture.lease"
RENEW_S = 30
STALE_S = 90

_RX = re.compile(r"pid=(\d+)\s+t=(\d+)")


def fmt(pid, t_ms):
    return "pid=%d t=%d" % (int(pid), int(t_ms))


def parse(text):
    """-> {"pid": int, "t": int} or None (an unreadable lease is no lease)."""
    m = _RX.search(text or "")
    if not m:
        return None
    return {"pid": int(m.group(1)), "t": int(m.group(2))}


def verdict(text, my_pid, now_ms, alive):
    """Who may record. -> "hold" (it is mine) | "refuse" (another live, fresh recorder holds it) | "take" (free)."""
    lease = parse(text)
    if not lease:
        return "take"
    if my_pid and lease["pid"] == int(my_pid):
        return "hold"
    fresh = 0 <= (int(now_ms) - lease["t"]) <= STALE_S * 1000
    if fresh and alive(lease["pid"]):
        return "refuse"
    return "take"


def read(path, alive, now_ms=None):
    """The beacon's `recorder` field. -> {"alive": bool, "pid": int|None, "t": iso|None, "ageS": float|None}"""
    now = int(time.time() * 1000) if now_ms is None else int(now_ms)
    try:
        with open(path, encoding="utf-8-sig") as f:
            lease = parse(f.read())
    except Exception:
        lease = None
    if not lease:
        return {"alive": False, "pid": None, "t": None, "ageS": None}
    from datetime import datetime, timezone
    age = (now - lease["t"]) / 1000.0
    ok = bool(0 <= age <= STALE_S and alive(lease["pid"]))
    return {"alive": ok, "pid": lease["pid"], "ageS": round(age, 1),
            "t": datetime.fromtimestamp(lease["t"] / 1000.0, tz=timezone.utc).isoformat().replace("+00:00", "Z")}


def adoptable(path, alive, now_ms=None):
    """The console's question before it spawns: is a live recorder already holding the lease? -> pid | None"""
    now = int(time.time() * 1000) if now_ms is None else int(now_ms)
    try:
        with open(path, encoding="utf-8-sig") as f:
            text = f.read()
    except Exception:
        return None
    if verdict(text, 0, now, alive) == "refuse":
        return parse(text)["pid"]
    return None


def lease_path(here):
    return os.path.join(here, LEASE_NAME)


# ── v3850 (Elad 18:16) - THE REEL-CUTTER HOLDS A SIBLING LEASE ─────────────────────────────────────────────────────
# tv_diablo.py --watch (the agent that cuts the reels) outlives the console under the same rule as the recorder:
# control_agent.lease, same format, same RENEW_S / STALE_S, same verdict. The console passes the path in
# TVD_AGENT_LEASE; an agent that finds a live, fresh sibling holding it leaves at once, so two consoles (or a console
# restart racing a survivor) can never run two reel-cutters.
AGENT_LEASE_NAME = "control_agent.lease"
AGENT_LEASE_ENV = "TVD_AGENT_LEASE"


def agent_lease_path(here):
    return os.path.join(here, AGENT_LEASE_NAME)


def claim(path, my_pid, alive, now_ms=None):
    """Take or renew the lease at `path` for my_pid. -> "hold" | "take" (written) | "refuse" (nothing written)."""
    now = int(time.time() * 1000) if now_ms is None else int(now_ms)
    try:
        with open(path, encoding="utf-8-sig") as f:
            text = f.read()
    except FileNotFoundError:
        text = ""
    except Exception:
        return "refuse"
    v = verdict(text, my_pid, now, alive)
    if v == "refuse":
        return v
    tmp = "%s.%d.tmp" % (path, int(my_pid))
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(fmt(my_pid, now))
    os.replace(tmp, path)
    return v


def release(path, my_pid):
    """Remove the lease only if it is still mine. Never raises."""
    try:
        with open(path, encoding="utf-8-sig") as f:
            lease = parse(f.read())
        if lease and lease["pid"] == int(my_pid):
            os.remove(path)
    except Exception:
        pass


def pid_alive(pid):
    """Portable liveness for the agent side (it has no console helpers). -> bool"""
    try:
        pid = int(pid)
    except Exception:
        return False
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        k = ctypes.windll.kernel32
        h = k.OpenProcess(0x1000, False, pid)   # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        try:
            code = ctypes.c_ulong()
            ok = k.GetExitCodeProcess(h, ctypes.byref(code))
            return bool(ok) and code.value == 259     # STILL_ACTIVE
        finally:
            k.CloseHandle(h)
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except Exception:
        return False


def agent_hold(path, my_pid=None, alive=None, sleep=time.sleep, on_lost=None, rounds=None):
    """The agent's side: claim once (refuse -> return "refuse" so the caller exits), then renew every RENEW_S on a
    daemon thread. If a renew is refused (we were hung past STALE_S and a sibling took over) on_lost() runs, because
    the one-lease rule says the newer holder cuts the reels now. -> the first verdict."""
    import threading
    my_pid = int(my_pid or os.getpid())
    alive = alive or pid_alive
    first = claim(path, my_pid, alive)
    if first == "refuse":
        return first

    def _renew():
        n = 0
        while rounds is None or n < rounds:
            n += 1
            sleep(RENEW_S)
            try:
                if claim(path, my_pid, alive) == "refuse":
                    if on_lost:
                        on_lost()
                    return
            except Exception:
                pass
    t = threading.Thread(target=_renew, name="tvd-agent-lease", daemon=True)
    t.start()
    return first
