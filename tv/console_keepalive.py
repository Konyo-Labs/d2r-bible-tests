# -*- coding: utf-8 -*-
"""REG-2614 - A WINDOWS CONSOLE THAT DIED IS BROUGHT BACK WITHIN MINUTES, WITH NO SIGN-IN.

2026-10-16: the ALT's console died with no error, and nothing relaunched it until someone next signed in to Windows -
it missed 302 commits of updates. The sign-in start (REG-1660) runs once, at sign-in; nothing watched a console that
died afterwards. This is the Windows cousin of tvd_supervisor.sh: Task Scheduler runs it every few minutes, hidden
(pythonw), as the signed-in user, and it starts the launcher with -Background only when the console is GONE.

    python console_keepalive.py           one pass: probe :17772, decide, maybe launch, log one line
    python console_keepalive.py --install-unattended USER [--password-env NAME]
                                          the owner's one-time install of the task that runs with nobody
                                          signed in (REG-2616); the password comes from $NAME, never argv

Safe to run any number of times, beside a running console or another pass:
  - a console that answers, or is merely slow (a connect that times out - the ALT stalls for minutes under load),
    is left alone; only a REFUSED port (nothing listening) is "gone";
  - a console closed on purpose (X / Quit writes .tvd_exited_on_purpose) or a stood-down supervisor
    (.tvd_supervisor_pause) is never relaunched - a choice is not a crash;
  - one launch per LAUNCH_COOLDOWN_S, so a console that dies at boot is not relaunched in a storm;
  - the launcher it starts holds its own mutex and leaves a running console exactly as it is (start_tvd_win.ps1).
Never raises; stdlib only; imports nothing of the console's. [[unknown-stays-unknown]]
"""
import json
import os
import socket
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from console_safe import enable; enable()  # noqa: E402  (v3850: it prints non-ASCII)

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = 17772
EXITED_ON_PURPOSE = os.path.join(HERE, ".tvd_exited_on_purpose")
PAUSE_FLAG = os.path.join(HERE, ".tvd_supervisor_pause")
STATE = os.path.join(HERE, ".tvd_keepalive.json")
LOG = os.path.join(HERE, "console_keepalive.log")
LOG_CAP = 256 * 1024
LAUNCH_COOLDOWN_S = 10 * 60
PROBE_TIMEOUT_S = 5.0
PASS_DEADLINE_S = 90        # the task runs with no time limit (review r1: a limit's job kill takes the console with it)
_CREATE_BREAKAWAY_FROM_JOB = 0x01000000
#: exit reasons a console records when its WINDOW LOOP ended under it (a WebView crash returns the loop the same way)
#: - never a choice, so never 'on purpose'. Kept equal to control_app._WINDOW_LOOP_EXITS (a law checks).
WINDOW_LOOP_EXITS = ("window-closed", "webview-finally", "main-after-window")
_CREATE_NO_WINDOW = 0x08000000
_CREATE_NEW_PROCESS_GROUP = 0x00000200


def probe(port=PORT, timeout=PROBE_TIMEOUT_S, connect=None):
    """Is anything listening on the console's port? -> "up" | "gone" | "slow" | "unknown". A connect only - never a
    request: a busy console is not asked to do work every few minutes."""
    try:
        s = (connect or socket.create_connection)(("127.0.0.1", int(port)), timeout)
    except ConnectionRefusedError:
        return "gone"
    except (socket.timeout, TimeoutError):
        return "slow"
    except OSError:
        return "unknown"
    try:
        s.close()
    except Exception:
        pass
    return "up"


def closed_on_purpose(path):
    """-> bool. The marker is '<epoch> <reason>'; a window-loop reason is a death, not a choice (review r1)."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            words = fh.read().split()
    except OSError:
        return os.path.exists(path)     # there but unreadable: the cautious answer is "he closed it"
    return (words[1] if len(words) > 1 else "") not in WINDOW_LOOP_EXITS


def decide(state, on_purpose, paused, last_launch_s, now_s):
    """PURE. -> (action, why); action is "launch" only for a console that is GONE, not closed on purpose, not stood
    down, and not launched within the cooldown."""
    if state == "up":
        return "leave", "the console answers on :%d" % PORT
    if state == "slow":
        return "leave", "the console's port did not answer the connect in time - slow is not gone"
    if state != "gone":
        return "leave", "whether the console is up is UNKNOWN - nothing is launched on a guess"
    if on_purpose:
        return "leave", "the console was closed on purpose - a choice is not a crash"
    if paused:
        return "leave", "the supervisor is stood down (.tvd_supervisor_pause)"
    if last_launch_s is not None and 0 <= now_s - last_launch_s < LAUNCH_COOLDOWN_S:
        return "held", "launched %ds ago - one launch per %d min" % (now_s - last_launch_s, LAUNCH_COOLDOWN_S // 60)
    return "launch", "nothing listens on :%d and nobody closed it on purpose - starting it in the background" % PORT


def launcher_argv(here=HERE):
    """The launcher, hidden, with -Background: the sign-in start's own shape (REG-1660)."""
    return ["powershell.exe", "-NoLogo", "-NoProfile", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass",
            "-File", os.path.join(here, "start_tvd_win.ps1"), "-Background"]


def launch(popen=None, here=HERE, is_win=None):
    """Start the launcher detached and windowless. -> (ok, why)"""
    is_win = (os.name == "nt") if is_win is None else is_win
    kw = {"cwd": os.path.dirname(here), "stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL,
          "stderr": subprocess.DEVNULL, "close_fds": True}
    if is_win:
        kw["creationflags"] = _CREATE_NO_WINDOW | _CREATE_NEW_PROCESS_GROUP
    popen = popen or subprocess.Popen
    p = None
    if is_win:
        # out of the task's job (review r1): whatever ends the task's job must not end the console it started
        try:
            p = popen(launcher_argv(here), **dict(kw, creationflags=kw["creationflags"] | _CREATE_BREAKAWAY_FROM_JOB))
        except OSError:
            p = None                    # the job forbids breakaway: started inside it (no time limit ends it)
    if p is None:
        try:
            p = popen(launcher_argv(here), **kw)
        except Exception as e:
            return False, "the launcher would not start (%s)" % type(e).__name__
    return True, "launcher pid %s" % getattr(p, "pid", "?")


def _read_state(path):
    """-> dict ({} = no pass has written it yet) | None (it is there and cannot be read)."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception:
        return None
    return d if isinstance(d, dict) else None


def _write_state(path, d):
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(d, fh)
        os.replace(tmp, path)
        return True
    except Exception:
        return False


def _log(path, line):
    try:
        if os.path.getsize(path) > LOG_CAP:
            with open(path, "rb") as fh:
                fh.seek(-LOG_CAP // 2, os.SEEK_END)
                keep = fh.read()
            with open(path, "wb") as fh:
                fh.write(keep[keep.find(b"\n") + 1:])
    except OSError:
        pass
    try:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("%s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), line))
    except OSError:
        pass


def recorder_beat(here=HERE, run=None):
    """v3850 - the console is not answering, so the recorder's heartbeat goes out from here (control_app
    .recorder_beacon_once, a recorderOnly patch). Bounded to 60 s, never raises. -> a short clause for the log."""
    try:
        r = (run or subprocess.run)([sys.executable, "-c", "import control_app as c, json; print(json.dumps(c.recorder_beacon_once()))"],
                                    cwd=here, capture_output=True, text=True, timeout=60)
        return " · recorder beat: " + (r.stdout or "").strip()[-120:]
    except Exception as e:
        return " · recorder beat raised %s" % type(e).__name__


def run_once(now_s=None, probe_fn=None, popen=None, here=HERE, state_path=None, log_path=None,
             on_purpose_path=None, pause_path=None):
    """One pass. -> {"action", "why", "state"}. Never raises."""
    now_s = time.time() if now_s is None else now_s
    state_path = state_path or STATE
    log_path = log_path or LOG
    try:
        st = (probe_fn or probe)()
        mem = _read_state(state_path)
        unread = mem is None
        if unread:
            # a torn memory must not stop a dead console coming back for ever: the launch rewrites it, and the
            # launcher's own mutex keeps a second console off - so the cooldown alone is given up, and said
            mem = {}
        action, why = decide(st, closed_on_purpose(on_purpose_path or EXITED_ON_PURPOSE),
                             os.path.exists(pause_path or PAUSE_FLAG), mem.get("lastLaunch"), now_s)
        if action == "launch":
            # the launch is booked BEFORE it is tried: a pass that dies mid-launch still holds the cooldown
            mem = dict(mem, lastLaunch=now_s, launches=int(mem.get("launches") or 0) + 1)
            _write_state(state_path, mem)
            ok, how = launch(popen=popen, here=here)
            why = "%s (%s)" % (why, how) if ok else "%s - FAILED: %s" % (why, how)
            if not ok:
                action = "failed"
        if action != "leave":
            why += recorder_beat(here)
        if unread:
            why += " (its memory %s could not be read, so the cooldown is not known)" % os.path.basename(state_path)
        if action != "leave" or unread or mem.get("lastAction") not in (None, "leave"):
            _log(log_path, "%s: %s" % (action, why))       # a quiet steady state writes nothing every 5 min
        if mem.get("lastAction") != action:
            # onto the memory just read or booked, never a re-read that could come back empty (review r1)
            _write_state(state_path, dict(mem, lastAction=action))
        return {"action": action, "why": why, "state": st}
    except Exception as e:
        return {"action": "error", "why": "the keepalive pass raised %s" % type(e).__name__, "state": None}


def main(run=None, deadline_s=None):
    """The task's entry. -> exit code (0 ok, 1 the pass erred; a pass past its deadline is ended with 3).

    The task has no time limit and ignores a new start while one runs (IgnoreNew), so a pass that hung would
    hold every later pass off for ever: a daemon timer ends the process itself (review r1; driven by the law,
    review r2)."""
    import threading
    _t = threading.Timer(PASS_DEADLINE_S if deadline_s is None else deadline_s, lambda: os._exit(3))
    _t.daemon = True
    _t.start()
    try:
        r = (run or run_once)()
    finally:
        _t.cancel()                     # review r3: a pass that ended must not leave a timer that ends its caller
    return 0 if r.get("action") != "error" else 1


PASSWORD_ENV = "TVD_KEEPALIVE_PASSWORD"


def install_main(argv, environ=None, install=None):
    """`console_keepalive.py --install-unattended USER [--password-env NAME]` -> exit code. REG-2616.

    The owner's one-time install of the keepalive that runs with nobody signed in. The password is read from the
    environment variable NAME (default TVD_KEEPALIVE_PASSWORD) - never from argv, so it is in no command line and no
    shell history - and handed on, never printed. Imports the doctor only here: a pass imports nothing of it."""
    environ = os.environ if environ is None else environ
    args = list(argv)
    try:
        user = args[args.index("--install-unattended") + 1]
    except (ValueError, IndexError):
        print("usage: console_keepalive.py --install-unattended USER [--password-env NAME]")
        return 2
    name = PASSWORD_ENV
    if "--password-env" in args:
        i = args.index("--password-env")
        if i + 1 >= len(args):
            print("usage: --password-env NAME")
            return 2
        name = args[i + 1]
    password = environ.get(name) or ""
    if not password:
        print("no password in $%s - nothing installed (the default signed-in mode is unchanged)" % name)
        return 2
    if install is None:
        sys.path.insert(0, HERE)
        import console_doctor as _cd
        install = _cd.install_unattended_keepalive
    r = install(user, password)
    print("%s: %s" % (r.get("did"), r.get("why")))
    return 0 if r.get("did") == "created" else 1


if __name__ == "__main__":
    if "--install-unattended" in sys.argv[1:]:
        sys.exit(install_main(sys.argv[1:]))
    sys.exit(main())
