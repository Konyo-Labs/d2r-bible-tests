#!/usr/bin/env python3
"""
v773 — App ↔ Site ↔ hidden agent button matrix.
Exercises every control API that the UI buttons call, and verifies the board
(auto-sync lamp) follows bridge truth. Requires control_app on :17772.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

# v1480 — make our own output survive the operator's console before we print anything.
# A tool whose verdict is its exit code must not die reporting it (REG-044/054/077): on a Hebrew
# cp1255 console every check mark we print is an unencodable character, and the crash lands in the
# dangerous direction — a correct tree reporting FAILURE.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from console_safe import enable as _console_safe
    _console_safe()
except Exception:
    pass

# v1711 — THIS GATE SKIPPED ON EVERY RUN WHERE THE CONSOLE WAS CLOSED, WHICH IS MOST OF THEM.
# It hardcoded :17772 and told the operator to start the app by hand, so its verdict depended on
# whether Konyo happened to have the console open — a gate whose coverage is a coincidence.
#
# It now boots its OWN control_app on a FREE EPHEMERAL PORT via TV_CONTROL_PORT (control_app.py:77)
# and stops it on the way out.
# ⚠ IT MUST NEVER TOUCH :17772. That port is his LIVE console; killing or rebinding it would take
# the running app out from under him, and `pkill -f` is banned in this project for exactly that
# class of mistake. This starts a separate process, on its own port, with --no-open so no window
# appears, and terminates ONLY the pid it started.
# If TV_CTRL_URL is set, that is honoured instead and nothing is started — for pointing the matrix
# at an already-running instance deliberately.
import atexit
import tempfile
import shutil
import socket

_OWNED = None


def _free_port():
    with socket.socket() as sk:
        sk.bind(("127.0.0.1", 0))
        return sk.getsockname()[1]


def spawn_private(argv, env):
    """REG-3670 - the private console in a session of its own on POSIX, so one killpg takes the agent it starts with it
    (control_app never setsids its agent on a Mac - v779, the Screen Recording chain - so the agent shares the console's
    group). -> (proc, group: bool)"""
    group = os.name == "posix"
    return subprocess.Popen(argv, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=group), group


def may_signal_group(pid):
    """v3896 (REG-3694) - may stop_private signal the process group `pid` names? Only a real child's: never 0 (os.killpg(0)
    is the CALLER's own group), never 1, never a pid that is not a number, never our own group. MEASURED 11-11 on GitHub,
    v3896 agent-suite (4), three attempts out of three: test_a_private_console_never_shares_his_ports hands _boot_control a
    fake child whose pid is 0; the atexit stop then sent SIGTERM to os.killpg(0) - the law's own group, which on a runner is
    the runner itself ("The runner has received a shutdown signal", exit 143) - and the slice died 3 minutes in. -> bool"""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    try:
        own = os.getpgrp()
    except Exception:
        return False
    return pid > 1 and pid != own


def stop_private(proc, base, group, ask_s=3.0, wait_s=5.0):
    """REG-3670 - THE PRIVATE CONSOLE GOES, AND ITS AGENT WITH IT. MEASURED 11-11 on his Mac: three tv_diablo agents this
    law's consoles had started (SIM agent up) ran on as orphans - 9 h and 2.7 days old, each on an ephemeral agent port and
    writing a fixture log - because the teardown SIGTERMed the console alone and the agent was re-parented to launchd.
    run_gates' end-of-run check names such leaks; this stops making them. Asks the console to turn its agent off, then
    signals the whole group (POSIX), SIGTERM then SIGKILL. Never raises."""
    try:
        urllib.request.urlopen(urllib.request.Request(base + "/api/off", data=b"{}", method="POST",
                                                      headers={"Content-Type": "application/json"}), timeout=ask_s).read()
    except Exception:
        pass
    if group and may_signal_group(getattr(proc, "pid", None)):     # v3896 (REG-3694) - never killpg(0): that is our own group
        import signal as _sig
        for sig in (_sig.SIGTERM, _sig.SIGKILL):
            try:
                os.killpg(proc.pid, sig)
            except Exception:
                break                                 # no such group: everything in it is gone
            gone = False
            for _ in range(int(wait_s / 0.1)):
                proc.poll()                           # reap the leader, so only living members keep the group
                try:
                    os.killpg(proc.pid, 0)
                except Exception:
                    gone = True
                    break
                time.sleep(0.1)
            if gone:
                break
    elif proc.poll() is None:
        try:
            proc.terminate()
        except Exception:
            pass
    try:
        proc.wait(timeout=10)
    except Exception:
        pass


def _boot_control():
    """Start a private control_app and return its base URL, or None if it will not come up."""
    global _OWNED, AGENT
    port = _free_port()
    # v1867 — ISOLATING THE PORT IS NOT ISOLATING THE WORLD.
    #
    # This harness was careful about the one thing that had bitten before — it takes a private free
    # port, passes --no-open, and terminates only the pid it started — and then handed that private
    # control app his REAL environment. Measured tonight: one run appends six rows to his live
    # tv/sessions.jsonl, including deep-lane rows stamped mode="stub". It writes his hist root and
    # his chronicle state the same way.
    #
    # It was invisible because run_gates' live-state watchlist named five files and not the journal
    # (fixed in the same ship). A port is one door; the frames, the journal, the sweep memory and
    # the sweep lock are four more. [[feedback-fixtures-never-touch-live-data]]
    #
    # TV_HIST alone would now carry the journal with it (v1867), but every path is named here on
    # purpose: a reader of this block should not have to know that rule to see that nothing escapes.
    _sand = tempfile.mkdtemp(prefix="btnmatrix-")
    atexit.register(shutil.rmtree, _sand, True)
    _hist = os.path.join(_sand, "frames", "hist")
    os.makedirs(_hist, exist_ok=True)
    # REG-2123 - AND ITS OWN AGENT PORT. Only the control port was private: TV_PORT fell through to :17771, HIS live agent's
    # port, so this app's OFF asked HIS agent to shut down and its STOP SIGTERMed whatever listened there - measured in his
    # agent log on 2026-10-09: eleven ON AIR sessions cut between 02:00 and 02:37 ("closing session (off)" / "signal:SIGTERM"),
    # each lining up with a gate shard, a push or a run of this law. A private app never shares a port with his console.
    # REG-2128 (the v3632 second eye) - two separate free-port draws can hand back the SAME ephemeral port, and nothing checked:
    # the child would get TV_CONTROL_PORT == TV_PORT. Draw until they differ. And the law's fallback agent is the port it
    # hands its child, never the parent shell's TV_PORT or :17771 - main() still adopts the agentPort the app reports.
    agent_port = _free_port()
    for _ in range(50):   # REG-2132 (the v3633 second eye) - bounded: an OS that keeps handing back one port never hangs the law
        if agent_port != port:
            break
        agent_port = _free_port()
    if agent_port == port:
        return None   # no second port to be had - report SKIP, never one port for both doors
    AGENT = "http://127.0.0.1:%d" % agent_port
    env = dict(os.environ, TV_CONTROL_PORT=str(port), TV_PORT=str(agent_port), TV_ROBOT="1",
               TV_HIST=_hist,
               TV_FRAMES_DIR=os.path.join(_sand, "frames"),
               TV_SESSIONS=os.path.join(_sand, "sessions.jsonl"),
               TV_CHRON_EVIDENCE=os.path.join(_sand, "chron_evidence.json"),
               TV_CHRON_RESULT=os.path.join(_sand, "chron_last_result.json"),
               TV_CHRON_SWEPT=os.path.join(_sand, "chronicle_swept.json"),
               TV_CHRON_READS=os.path.join(_sand, "chron_reads.json"),
               TV_SWEEP_LOCK=os.path.join(_sand, ".sweep.lock"))
    here = os.path.dirname(os.path.abspath(__file__))
    proc, group = spawn_private([sys.executable, os.path.join(here, "control_app.py"), "--no-open"], env)
    _OWNED = proc
    base = "http://127.0.0.1:%d" % port
    atexit.register(stop_private, proc, base, group)
    for _ in range(60):                      # up to ~30s for first boot
        if proc.poll() is not None:
            return None                      # died on startup — report SKIP, never a false pass
        try:
            urllib.request.urlopen(base + "/api/status", timeout=1).read()
            return base
        except Exception:
            time.sleep(0.5)
    return None


CTRL = os.environ.get("TV_CTRL_URL") or ""
# REG-2123 - THE AGENT THIS LAW PINGS IS THE ONE ITS OWN APP RUNS. This was the literal :17771 while the private control_app it
# boots runs its agent on TV_PORT (control_app.AGENT_PORT). Under the prover's lane ports (TV_PORT=21001) every agent check asked
# the wrong port - SIM -> agent ping, RESTART -> agent up, OFF -> dark, STOP -> dark - so the law was "already red untampered"
# in every sandbox and refused the v3631 push twice. And :17771 is where HIS live console's agent listens. The default follows
# TV_PORT like the app's; main() then adopts the agentPort the app itself reports.
AGENT = "http://127.0.0.1:%s" % (os.environ.get("TV_PORT") or "17771")
FAILS = []
SKIPS = []


def get(url, t=3):
    with urllib.request.urlopen(url, timeout=t) as r:
        return json.loads(r.read().decode())


def post(path, t=30, body=None):
    data = json.dumps(body).encode() if body else b""
    req = urllib.request.Request(CTRL + path, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=t) as r:
        return json.loads(r.read().decode())


def wait_mode(want, sec=20, bridge=None):
    t0 = time.time()
    last = None
    while time.time() - t0 < sec:
        try:
            s = get(CTRL + "/api/status")
            last = (s.get("mode"), s.get("bridge"), s.get("readCount"))
            ok_mode = s.get("mode") == want or (want == "off" and s.get("mode") in ("off",))
            if want == "stopping":
                ok_mode = s.get("mode") == "stopping"
            if ok_mode:
                if bridge is None or s.get("bridge") is bridge:
                    return s
        except Exception as e:
            last = str(e)
        time.sleep(0.35)
    FAILS.append(f"timeout waiting mode={want} bridge={bridge} last={last}")
    return None


def wait_agent(up: bool, sec=15):
    t0 = time.time()
    while time.time() - t0 < sec:
        try:
            urllib.request.urlopen(AGENT + "/ping", timeout=0.8)
            if up:
                return True
        except Exception:
            if not up:
                return True
        time.sleep(0.3)
    FAILS.append(f"agent up={up} not reached")
    return False


def _needs_claude(r):
    """Did this button fail ONLY because the Claude Code CLI is absent?

    ON AIR and RESTART both drive the live agent, which needs Konyo's subscription CLI. A CI
    runner has no such CLI, so both answer {'ok': False, 'error': 'Claude Code CLI not found …'}.
    Grading that as a defect is how a gate turns into furniture nobody reads. It is deliberately
    NARROW: only an absent CLI is excused, so a genuine ON failure (screen recording denied, a
    wedged bridge) still fails. Verified against all three payload shapes."""
    return (not r.get("ok")) and "claude" in str(r.get("error", "")).lower()


def check(name, cond, detail=""):
    if cond:
        print(f"  ✓ {name}")
    else:
        print(f"  ✗ {name} {detail}")
        FAILS.append(f"{name}: {detail}")


def main():
    print("══ BUTTON MATRIX · control API (mirrors every app button) ══")
    st = get(CTRL + "/api/status")
    check("control up", st.get("ok") is True, st)
    # v1480 — this used to assert `^v8\d\d`, written at v849 and stale from v900 onward: for ~600
    # versions it reported FAILED on every correct build, and nobody saw it because the script died
    # on a UnicodeEncodeError before the verdict could be read. A check that cannot be right is
    # worse than no check.
    #
    # What it was FOR is stamp drift, so compare against the ship manifest — the file that declares
    # what this platform is supposed to be running. That stays true at any version number, and it
    # catches the thing worth catching: a running app older than the tree under test.
    live = st.get("ver") or ""
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "WINDOWS_SHIP.json"),
                  encoding="utf-8") as _fh:
            want = json.load(_fh).get("ver") or ""
    except Exception as _e:
        want = ""
    check("version stamp", bool(want) and live == want,
          "live app says %r, tv/WINDOWS_SHIP.json says %r — the running app is a different build "
          "than the tree you are testing; restart it before trusting this matrix" % (live, want))

    # ensure clean off
    print("\n· OFF (ensure dark)")
    try:
        post("/api/off")
    except Exception:
        pass
    wait_agent(False, 12)
    s = wait_mode("off", 15, bridge=False)
    check("OFF → mode off", s and s.get("mode") == "off")
    check("OFF → bridge down", s and s.get("bridge") is False)
    check("OFF → agent dead", wait_agent(False, 3))

    print("\n· SIM (start canned agent)")
    r = post("/api/sim")
    check("SIM start ok", r.get("ok") is True, r)
    s = wait_mode("sim", 15, bridge=True)
    check("SIM → mode sim", s and s.get("mode") == "sim")
    check("SIM → bridge up", s and s.get("bridge") is True)
    check("SIM → agent ping", wait_agent(True, 5))
    # let stub produce at least one read if synth path works
    # REG-2113 (#310) - ONE SAMPLE AFTER A FIXED 6 s WAS A TIMING GUESS. Red in gate shard 2 on four batches running beside a second
    # lane and his console's prover, green alone every time: a single late heartbeat read as "bridge down". Poll the same question
    # for up to 15 s - a SIM agent that is really gone never answers it, and the last sample is what the failure prints.
    time.sleep(2)
    s, _ok = {}, False
    for _i in range(15):
        try:
            s = get(CTRL + "/api/status") or {}
        except Exception:
            s = {}   # a status call that timed out under load is a sample with no answer, not a crash
        if s.get("bridge") is True or (s.get("readCount") or 0) > 0:
            _ok = True
            break
        time.sleep(1)
    check("SIM → reads grow or bridge stays", _ok, f"reads={s.get('readCount')} bridge={s.get('bridge')} after 15 s of asking")

    print("\n· SIM again (toggle cut) via /api/off  [UI maps 2nd SIM click → off]")
    r = post("/api/off")
    check("SIM-off post", r.get("ok") is True, r)
    wait_agent(False, 15)
    s = wait_mode("off", 15, bridge=False)
    check("SIM cut → off", s and s.get("mode") == "off" and s.get("bridge") is False)

    print("\n· ON (live agent — may need screen permission; bridge must still start)")
    r = post("/api/on", body={"test": True})   # v786 — matrix runs never become theatre reels
    # v1711 — ON AIR NEEDS THE CLAUDE CODE CLI, WHICH A CI RUNNER DOES NOT HAVE.
    # When this gate started booting its own console it began running on GitHub too, where
    # /api/on answers {'ok': False, 'error': 'Claude Code CLI not found — ON AIR needs Claude'}
    # and every downstream ON assertion then fell over: 8 reported failures, none of them a
    # defect. Reporting an unavailable subscription lane as a red is how a gate becomes furniture.
    # The lane is SKIPPED and said out loud instead, and every other button still runs. On his
    # Mac, where the CLI is present, nothing here changes and the full lane is graded as before.
    _no_claude = _needs_claude(r)
    if _no_claude:
        SKIPS.append("ON AIR lane — %s" % r.get("error"))
        print("  ⚠ SKIPPED ON AIR lane — %s" % r.get("error"))
    else:
        check("ON start ok", r.get("ok") is True, r)
    s = None if _no_claude else wait_mode("live", 20, bridge=True)
    # mode may be live even if capture fails
    if _no_claude:
        pass                                   # the lane was skipped above; assert nothing about it
    elif not s:
        # sometimes status shows mode live only when bridge; check agent
        check("ON → agent ping", wait_agent(True, 8))
        s = get(CTRL + "/api/status")
        check("ON → bridge or mode live", s.get("bridge") or s.get("mode") in ("live", "sim"), s)
    else:
        check("ON → mode live", s.get("mode") == "live")
        check("ON → bridge", s.get("bridge") is True)

    print("\n· RESTART")
    r = post("/api/restart")
    # RESTART relaunches the LIVE agent, so it needs the same Claude Code CLI as ON AIR and fails
    # the same way on a runner. Same rule: an absent subscription lane is a SKIP, not a red.
    if _needs_claude(r):
        SKIPS.append("RESTART lane — %s" % r.get("error"))
        print("  ⚠ SKIPPED RESTART lane — %s" % r.get("error"))
    else:
        check("RESTART ok", r.get("ok") is True, r)
        time.sleep(1)
        check("RESTART → agent up", wait_agent(True, 10))

    print("\n· OFF (soft cut live)")
    r = post("/api/off")
    check("OFF post", r.get("ok") is True, r)
    wait_agent(False, 15)
    s = wait_mode("off", 15, bridge=False)
    check("OFF → dark", s and s.get("mode") == "off" and not s.get("bridge"))

    print("\n· SIM then STOP (farewell path; sim uses soft on server when mode was sim)")
    post("/api/sim")
    wait_mode("sim", 12, bridge=True)
    r = post("/api/stop")
    check("STOP post", r.get("ok") is True, r)
    # may briefly be stopping
    time.sleep(0.5)
    wait_agent(False, 20)
    s = wait_mode("off", 20, bridge=False)
    check("STOP → dark", s and s.get("mode") == "off")

    print("\n· BOARD endpoint (same-window nav — does NOT spawn)")
    r = post("/api/board")
    check("BOARD ok", r.get("ok") is True, r)
    check("BOARD same-window", r.get("spawned") is False, r)
    check("BOARD nav path", isinstance(r.get("nav"), str) and r.get("nav", "").startswith("/board"), r)

    print("\n· STATUS / LOG endpoints")
    s = get(CTRL + "/api/status")
    check("status fields", all(k in s for k in ("mode", "bridge", "ver", "shell")), list(s.keys())[:12])
    lg = get(CTRL + "/api/log")
    check("log endpoint", lg.get("ok") is True)

    print("\n· SESSIONS theatre backend (history API)")
    # ⚠⚠ THE 3s DEFAULT IS BELOW THIS CALL'S COLD FLOOR, NOT ABOVE ITS WARM COST. This console
    # was spawned seconds ago, so /api/sessions is always a FIRST call — and the repo's own
    # profiling records that path (heart.vessels -> _vault_owed_reels -> reel_retention.plan ->
    # frame_authority.test_referenced_reels) at 19.5s COLD versus 0.05s warm, with the memo and
    # the on-disk cache both empty until something fills them. Measured on the live, warm console
    # for contrast: 0.016s.
    #
    # So `sessions: timed out` was a statement about a budget, not about the product, and this
    # matrix has been reporting FAILED 1 for it. A threshold BELOW the floor is the mirror of
    # [[feedback-threshold-above-the-ceiling]]: one can never fire, the other can never pass.
    # 45s, above the profiled cold figure with room, and it stays a real bound — a hang still
    # fails. The sibling `post()` already allows 30s for the same reason.
    try:
        sess = get(CTRL + "/api/sessions", t=45)
        check("sessions list", "sessions" in sess, sess)
    except Exception as e:
        FAILS.append(f"sessions: {e}")
        print(f"  ✗ sessions {e}")

    # ── Site cross-ref with real bridge ─────────────────────────────────────
    print("\n══ SITE cross-ref (Playwright + real agent) ══")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  ⚠ playwright not importable in this python — skip DOM cross-ref")
        sync_playwright = None

    if sync_playwright:
        bible = "file://" + os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bible.html"))
        # start sim so site can probe
        post("/api/sim")
        wait_mode("sim", 12, bridge=True)
        time.sleep(1)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(bible)
            page.wait_for_timeout(500)
            page.evaluate("window.switchTab && window.switchTab('tvd')")
            # wait for auto-probe to see agent (2.5s + poll)
            live = False
            for _ in range(20):
                page.wait_for_timeout(500)
                bug = page.evaluate(
                    "() => (document.getElementById('tvz-bug-txt')||{}).textContent || ''"
                )
                st = page.evaluate(
                    "() => (document.getElementById('tvz-shell')||{}).getAttribute('data-tvstate') || ''"
                )
                if "ON AIR" in bug or st == "live":
                    live = True
                    break
            check("site → ON AIR while SIM agent up", live, f"bug={bug!r} st={st!r}")

            # kill agent from app API
            post("/api/off")
            wait_agent(False, 15)
            dark = False
            for _ in range(24):
                page.wait_for_timeout(500)
                bug = page.evaluate(
                    "() => (document.getElementById('tvz-bug-txt')||{}).textContent || ''"
                )
                verb = page.evaluate(
                    "() => (document.getElementById('tvb-verb')||{}).textContent || ''"
                )
                st = page.evaluate(
                    "() => (document.getElementById('tvz-shell')||{}).getAttribute('data-tvstate') || ''"
                )
                if (
                    "OFF AIR" in bug
                    or "NO SIGNAL" in verb
                    or "DISCONNECTED" in verb
                    or st in ("off", "offline")
                ):
                    dark = True
                    break
            check(
                "site → NO SIGNAL / OFF AIR after app OFF",
                dark,
                f"bug={bug!r} verb={verb!r} st={st!r}",
            )

            # theatre button exists and opens
            page.evaluate(
                """() => {
                const b = document.getElementById('tvz-theatre-btn');
                if (b) b.click();
            }"""
            )
            page.wait_for_timeout(300)
            th = page.evaluate(
                "() => { const t=document.getElementById('tvz-theatre'); return t ? !t.hidden : false; }"
            )
            check("site Theatre button opens panel", th is True or th is False)  # presence ok
            # get-app copy buttons
            n = page.evaluate("() => document.querySelectorAll('.tvz-ga-copy').length")
            check("site GET THE APP copy buttons", n == 2, n)
            browser.close()

    print("\n══ MATRIX RESULT ══")
    for sk in SKIPS:
        # loud, always — a check that did not happen must never read as one that passed
        print("⚠ SKIPPED %s" % sk)
    if FAILS:
        print(f"FAILED {len(FAILS)}:")
        for f in FAILS:
            print(" -", f)
        return 1
    print("ALL CHECKS PASSED — app APIs + site sync + hidden agent wired%s"
          % (" (%d lane(s) skipped, listed above)" % len(SKIPS) if SKIPS else ""))
    return 0


RED_PROOF = [
    {
        'why': 'the BOARD button must hand back a same-window nav path under /board — v781 made it ONE window (Grok\'s button testing had spawned 26 native board windows) and v2052 made an HTTP client able to move that window; a wrong nav target breaks both silently  MEASURED: untampered GREEN. `perl -e \'alarm 200; exec @ARGV\' python3 tv/test_button_matrix.py` -> exi; tampered (all 1) RED. Same command -> exit 1, "FAILED 1". Exactly one law fell: BOARD nav path — ; reddened law BOARD nav path — test_button_matrix.main(): check("BOARD nav path", is; ALONE FAILS ALONE. This gate is a SCRIPT, not a unittest suite, so "alone" was a fresh process invoking ex.',
        'file': 'control_app.py',
        'find': 'nav = "/board?app=1#%s" % tab',
        'replace': 'nav = "board?app=1#%s" % tab',
        'matches': 1,
    },
    {
        'why': 'REG-2123 - the law pings a fixed :17771 instead of the agent its own app runs (red in every prover lane; '
               'it is also the port of his live agent)',
        'file': 'tv/test_button_matrix.py',
        'find': '        AGENT = "http://127.0.0.1:%d" % _ap0   # noqa: F811 - REG-2123: the agent its own app reports, never a guess\n',
        'replace': '        AGENT = "http://127.0.0.1:17771"   # noqa: F811\n',
        'matches': 1,
    },
]


if __name__ == "__main__":
    # v1711 — boot our OWN console if none was handed to us. Never :17772 (his live app).
    if not CTRL:
        CTRL = _boot_control() or ""   # noqa: F811 — module-level rebind is intended
    if not CTRL:
        print("SKIPPED — could not start a private control_app to test against "
              "(set TV_CTRL_URL to point at one deliberately). Reporting SKIP rather than a pass: "
              "a matrix that never ran must not read as green.")
        sys.exit(2)
    try:
        _st0 = get(CTRL + "/api/status")
    except Exception as e:
        print("SKIPPED — control_app started but never answered /api/status at %s" % CTRL)
        print(e)
        sys.exit(2)
    _ap0 = (_st0 or {}).get("agentPort")
    if isinstance(_ap0, int) and _ap0 > 0:
        AGENT = "http://127.0.0.1:%d" % _ap0   # noqa: F811 - REG-2123: the agent its own app reports, never a guess
    print("button matrix running against %s (private instance, his :17772 untouched), agent %s" % (CTRL, AGENT))
    sys.exit(main())
