#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════════════
# 📺 TV DIABLO — Autopilot scanner (v740)
#
#   You play Diablo II. This watches the screen, reads the items you're looking
#   at, and feeds the tally to the Farming Bible's 📺 panel — automatically.
#
#   READ-ONLY BY CONSTRUCTION (the compliance doctrine):
#     · launched by YOU, separately, in a terminal — never bundled into the game
#     · it only takes screenshots of what is already on your screen
#     · it NEVER touches the game process: no memory reading, no injection,
#       no input automation, no overlay. Pure screen capture + external notes.
#     (Same class as manually screenshotting your stash — just automated.)
#
#   SUBSCRIPTION, NOT API KEYS: vision reads run through the Claude Code CLI
#   (`claude -p`), billed to YOUR Claude subscription. Your cousin runs the
#   same file on Windows with HIS Claude Code login — his reads, his plan.
#
#   Zero dependencies — python3 stdlib only.
#
#   Run:            python3 tv/tv_diablo.py
#   Windows:        run tv/capture_win.ps1 in one terminal (frames), then
#                   python3 tv/tv_diablo.py --watch  in another (reads+bridge)
#   Then in the bible: ⚡ session → 📺 TV DIABLO → flip the switch.
#
#   ONE logical AI path (scout secondary is DEAD forever):
#     settle / queue / heartbeat → dual-lane (OCR flash + Claude deep).
#   v863+ READER POOL: up to TV_POOL concurrent warm Claude workers with capture-order
#   apply (not a second freestyle scout engine). Film is high-FPS HD; ON AIR status is a
#   tiny chip. OFF/STOP seal session_end into sessions.jsonl. Claude deep is multi-second
#   by nature — OCR chips + smooth film are the live-drive feel.
# ═══════════════════════════════════════════════════════════════════════════════
import tempfile
import json, os, re, subprocess, sys, threading, time, hashlib, signal, heapq, tempfile
# ⚠⚠ REG-1307 — NO CHILD OF THIS PROCESS MAY OPEN A WINDOW ON WINDOWS, INSTALLED BEFORE ANY SPAWN.
# His report: a terminal window "keeps jumping up and alt tabbing me and even deans computer ... exits us from
# the game". Replaces subprocess.Popen for this process so every child starts with CREATE_NO_WINDOW + SW_HIDE
# (a no-op off Windows). One door instead of 82 call sites - see tv/win_quiet.py.
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import win_quiet as _win_quiet
    _win_quiet.install()
except Exception:
    pass
# #83 (REG-1515) — THE CHILD SUPERVISOR. Every warm reader and the OCR worker is spawned and ended through one
# door that ends the role's previous tree first (Windows: a Job Object with KILL_ON_JOB_CLOSE; POSIX: its own
# session + killpg) and refuses a SECONDARY worker while free RAM is under a floor. See tv/child_guard.py.
import child_guard as _child_guard

from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def _intake_result_fields(body):
    """REG-2914 (#158) - the intake record the board's /intake_result POST becomes on this agent's journal. -> dict

    The board posts each tally read here FIRST (the bridge port), and only to the console's own route when this one is not
    listening. The console's copy of the route kept the reason since v1945 (err, guardHeld) and REG-2730 (errWhy: WHICH image
    error); this one built its record from seven fields and dropped the rest, so a receipt from the agent read "read failed
    (1 image error)" and never said which. The reason fields ride as sent; the sentence is made where it is read
    (control_app._intake_why, one rule), never a second copy here."""
    body = body if isinstance(body, dict) else {}
    out = {
        "tab": str(body.get("tab") or "")[:24],
        "kind": str(body.get("kind") or "")[:16],
        "counts": body.get("counts") if isinstance(body.get("counts"), dict) else {},
        "total": int(body.get("total") or 0),
        "errors": int(body.get("errors") or 0),
        "items": (body.get("items") or [])[:60],
        "ok": bool(body.get("ok", True)),
    }
    if body.get("guardHeld"):
        out["guardHeld"] = True
    if body.get("err"):
        out["err"] = str(body.get("err"))[:200]
    if body.get("errWhy"):
        out["errWhy"] = str(body.get("errWhy"))[:160]
    return out


# v1402 — Windows Hebrew/cp1255 consoles crash on emoji boot prints
# (UnicodeEncodeError) and die before the agent bridge opens. Force UTF-8
# stdio with replace so ON AIR never dies on a logo line.
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONUTF8", "1")
    for _stream_name in ("stdout", "stderr"):
        _stream = getattr(sys, _stream_name, None)
        try:
            if _stream is not None and hasattr(_stream, "reconfigure"):
                _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

VERSION = "v3895"   # board first slices
HERE   = os.path.dirname(os.path.abspath(__file__))
FRAMES = os.environ.get("TV_FRAMES_DIR") or os.path.join(HERE, "frames")   # v752 — replay feeds its own watch dir


_FOOTAGE_RETRY_S = 30.0   # v3410 — a broken tree is re-attempted at most this often, never per frame



def _disk_free_bytes(path):
    """#151 (REG-2742) - free space at `path` as macOS counts it for a write that matters: purgeable space included
    (disk_room.free_bytes). Every floor in this file reads it, so the ON AIR floor, the picture size and the health
    figure beside the floor agree. Raises what shutil.disk_usage raises."""
    import disk_room as _dr
    return _dr.free_bytes(path)[0]


def _establish_footage():
    """v3405 — the film/archive writers walk ONE door. Looking never provisions.

    Cached on (TV_HIST, TV_FRAMES_DIR) so the film loop does not prove-write a probe
    file on every frame. A harness that changed isolation mid-process gets a fresh call.
    """
    key = (os.environ.get("TV_HIST") or "", os.environ.get("TV_FRAMES_DIR") or "")
    if globals().get("_FOOTAGE_ESTABLISHED") == key:
        return
    # ⚠⚠ v3410 — A FAILED CREATE WAS CACHED AS DONE, AND THE FILM WENT SILENT FOR THE PROCESS.
    # establish() reports a create/prove-write failure as a ROW and never raises
    # (machine_tree.py FAILED / UNUSABLE), so stamping the cache on the strength of "it
    # returned" recorded a broken tree as an established one. MEASURED: with
    # TV_HIST=/dev/null/nope/hist, establish() returned normally with a FAILED row and the
    # stamp landed anyway — call #2 was a CACHE HIT, and nothing in this tree ever clears the
    # global. _archive_footage_copy then reaches shutil.disk_usage(hist_dir) on a directory
    # that is not there, which raises FileNotFoundError, which is swallowed as `return False`:
    # every film frame dropped, silently, for the life of the process. v3404's per-frame
    # os.makedirs(hist_dir, exist_ok=True) used to heal that the moment a drive remounted.
    #
    # ⚠ THREE STATES, NOT TWO, AND THE THIRD IS WHY THIS IS NOT A ONE-LINER. Simply refusing to
    # stamp on any bad row retries at FILM CADENCE, and on the live lane establish() falls
    # through to ensure(create=True) which walks ALL SIX roots — a prove-write storm on every
    # frame. So:
    #   FAILED / UNUSABLE -> transient (a drive remounts, a permission clears). Do not stamp,
    #                        but do not retry faster than _FOOTAGE_RETRY_S either.
    #   REFUSED           -> NOT transient. Its anchor could not be established and will not
    #                        become establishable by asking again, so it stamps. Retrying a
    #                        refusal forever is the storm wearing a fix's clothes.
    #   created / found   -> stamp, exactly as before.
    # [[unknown-stays-unknown]] [[a-gate-can-perturb-what-it-measures]]
    _now = time.time()
    if globals().get("_FOOTAGE_BROKEN_KEY") == key:
        if (_now - (globals().get("_FOOTAGE_LAST_TRY") or 0.0)) < _FOOTAGE_RETRY_S:
            return
    globals()["_FOOTAGE_LAST_TRY"] = _now
    import machine_tree as _mt
    rows = _mt.establish() or []
    _hurt = [r for r in rows
             if r.get("root") in ("frames", "frames/hist")
             and r.get("state") in (_mt.FAILED, _mt.UNUSABLE)]
    if _hurt:
        globals()["_FOOTAGE_BROKEN_KEY"] = key
        return
    globals()["_FOOTAGE_BROKEN_KEY"] = None
    globals()["_FOOTAGE_ESTABLISHED"] = key

# ══ v2324 — THE LIVE FRAME IS NO LONGER A FILENAME, IT IS A QUESTION ═══════════════════════════
# The capture path used to be spelled `live.bmp` in five places, which baked the FORMAT into the
# NAME: to stop paying 46ms and 12MB per frame for a conversion that recovers nothing (see
# _capture_window_to_file), every one of those spellings had to change together or the readers
# would look for a file the writer had stopped producing. That is precisely the shape that goes
# wrong silently — the writer succeeds, the reader finds nothing, and the eye simply goes blind
# with no error anywhere. [[the-unjoined-end]]
#
# So the name stops being a constant. WRITE goes to JPEG; READ takes the NEWEST of the candidates,
# which means a leftover live.bmp from a previous build is still read rather than ignored, and an
# older build sharing the directory keeps working. Order is by mtime, never by preference — the
# freshest frame is the true one, whatever it is called. [[stale-reading]]
LIVE_FRAME_NAMES = ("live.jpg", "live.png", "live.bmp")
LIVE_FRAME_WRITE = "live.jpg"


def live_frame_path(frames_dir=None, for_write=False):
    """Where the live frame is (newest that EXISTS), or where to write a new one.

    for_write=True always answers LIVE_FRAME_WRITE, so there is exactly one writer name.
    for_write=False returns the newest existing candidate, or the write path when none exist —
    never None, because every caller here goes on to os.path.isfile() it anyway.
    """
    d = frames_dir or FRAMES
    if for_write:
        return os.path.join(d, LIVE_FRAME_WRITE)
    best, best_mt = None, -1.0
    for nm in LIVE_FRAME_NAMES:
        p = os.path.join(d, nm)
        try:
            if os.path.isfile(p):
                mt = os.path.getmtime(p)
                if mt > best_mt:
                    best, best_mt = p, mt
        except OSError:
            continue
    return best or os.path.join(d, LIVE_FRAME_WRITE)


def live_frame_all(frames_dir=None):
    """Every candidate path, existing or not — for boot cleanup, which must sweep the names this
    build no longer writes or a stale BMP would outlive the switch and be served as the eye."""
    d = frames_dir or FRAMES
    return [os.path.join(d, nm) for nm in LIVE_FRAME_NAMES]
def _under(path, root):
    """Is `path` inside `root`? Case-normalised, because HIS WINDOWS MACHINE IS THE OTHER HALF.

    v1897 — this comparison was written four times tonight as `h.startswith(root + os.sep)`, and on
    Windows that is a coin flip: the same directory arrives as C:\\Users\\... from one call and
    c:\\users\\... from another, `startswith` says no, and the isolation rule silently decides a
    FIXTURE is his real tree — which is the exact class the whole night was spent closing, arriving
    on the machine I cannot run the suite on.

    os.path.normcase is a no-op on macOS and Linux and lowercases + normalises separators on
    Windows, so this is correct everywhere and changes nothing here. [[dual-machine-setup]]
    """
    try:
        a = os.path.realpath(path)
        b = os.path.realpath(root)
    except Exception:
        return False
    # THE FILESYSTEM IS THE AUTHORITY WHEN IT CAN ANSWER. os.path.samefile compares inodes, so it
    # is right on a case-INSENSITIVE volume (his Mac's APFS by default) where two spellings are one
    # directory — normcase alone says "different" there and would call his own tree a fixture.
    # Measured: TV_HIST set to the uppercased form of tv/frames/hist was treated as isolated, and
    # "isolated" writes would have landed in his real directory under a different spelling.
    try:
        if os.path.exists(a) and os.path.exists(b) and os.path.samefile(a, b):
            return True
    except Exception:
        pass
    # walk up: is any ancestor of `a` the same file as `b`? Handles the nested case with the same
    # authority, and stops at the root rather than looping.
    try:
        cur = a
        while True:
            parent = os.path.dirname(cur)
            if parent == cur:
                break
            cur = parent
            if os.path.exists(cur) and os.path.exists(b) and os.path.samefile(cur, b):
                return True
    except Exception:
        pass
    # neither exists yet (a fixture dir about to be created): fall back to normcase, which is a
    # no-op on posix and lowercases + normalises separators on Windows.
    a, b = os.path.normcase(a), os.path.normcase(b)
    return a == b or a.startswith(b + os.sep)


def _fixture_root(here):
    """The directory live state belongs in: his tree normally, the FIXTURE's when TV_HIST is one.

    v1869 — one rule, four files. A caller that repoints TV_HIST outside this module has said "this
    is not his world"; his console log, his engine state, his G5 stats and his subscription meter
    must not then describe a fixture's run. Measured tonight: a single gate run rewrote all four,
    and the pollution of ONE of them — control_agent.log — cost a wrong diagnosis, because the
    sim/live start banners I read as HIS button presses were written by my own test-spawned control
    apps. [[feedback-fixtures-never-touch-live-data]] [[feedback-suspect-the-instrument]]
    """
    hist = os.environ.get("TV_HIST")
    # ⚠⚠ v2932 (REG-875) — BLANK IS NOT A PATH, AND RELATIVE IS NOT A DECISION.
    # MEASURED 2026-09-11 by driving BOTH this rule and control_app's fallback across three working
    # directories: with cwd at the REPO ROOT and `TV_HIST="   "`, both returned
    # `<repo>/   ` — a whitespace-named directory INSIDE his tree, handed back as an isolation
    # root. `TV_HIST="relative/path"` did the same with `<repo>/relative/path`. The cause is
    # `os.path.realpath()` resolving a non-absolute value against whatever CWD the process happened
    # to start in, so the isolation decision was a function of the caller's shell.
    # A request for isolation must not be answered with a guess: blank-after-strip means nobody
    # asked, and a relative value cannot be honoured because its meaning is not fixed.
    # [[unknown-stays-unknown]] [[feedback-fixtures-never-touch-live-data]]
    if hist and hist.strip() and os.path.isabs(hist.strip()):
        hist = hist.strip()
        try:
            if not _under(hist, here):
                return os.path.realpath(hist)
        except Exception:
            pass
    return here


STATE  = os.path.join(_fixture_root(HERE), "state.json")
# ── v2000 — THE SHADOW SWITCH. ONE WRITER, ONE READER, ITS OWN FILE ─────────────────────────────
# Konyo: "is there a way to like have an AI lurking in the shadows reading the game ingame and
# sometimes firing whats needed? … for this it should have an ON/OFF for shadow AI a button to
# click a cool widget."
#
# The lurking AI already exists and has since v932: the TEXT EYE OCRs the live frame continuously
# and turns new item-ish text into a PRIORITY read. What it never had was a switch he could reach.
# TV_TEXT_EYE is read ONCE, before the loop starts, so it is a boot flag and an env var of a running
# process cannot be changed from outside anyway.
#
# NOT state.json, deliberately. The agent WRITES that file; a console that also wrote it is the
# pt_signals.json shape exactly — four programs whole-file-writing one path and erasing each other's
# rows seconds later. This file has exactly ONE writer (the console) and ONE reader (this process),
# so no lock is needed and no write can be lost.
#
# It rides _fixture_root for the same reason STATE does: a test that repoints TV_HIST has said "this
# is not his world", and must not be able to switch off the eye in his real one.
# [[feedback-fixtures-never-touch-live-data]] [[achilles-trading-book-shrank]]
SHADOW = os.path.join(_fixture_root(HERE), "shadow_ai.json")
_SHADOW_CACHE = {"mtime": -1.0, "on": True}


def shadow_ai_on():
    """Is the lurking reader allowed to fire right now? ALWAYS ON (his ruling 2026-11-03: "shadow reader shouldnt be able
    to be turned on or off"). A missing, unreadable or stale OFF file reads ON, and control_app._shadow_set writes ON
    whatever it is asked; only the TV_TEXT_EYE=0 boot override turns it off. (v3866: this said "Off is only ever
    something he chose" after v3859 made OFF impossible - the #231 eye on v3860 read the prose as the contract.)

    Cached on mtime because the caller polls this every 0.7s; a stat is cheap, a json parse 86,000
    times an hour is not.
    """
    if os.environ.get("TV_TEXT_EYE", "1") == "0":
        return False           # the boot override still wins, so nothing that worked stops working
    try:
        m = os.path.getmtime(SHADOW)
    except OSError:
        _SHADOW_CACHE["mtime"] = -1.0
        _SHADOW_CACHE["on"] = True
        return True
    if m != _SHADOW_CACHE["mtime"]:
        _SHADOW_CACHE["mtime"] = m
        try:
            with open(SHADOW, encoding="utf-8") as fh:
                json.load(fh)
                _SHADOW_CACHE["on"] = True   # v3859 - always on (Elad 2026-11-03); a stale OFF is ignored
        except Exception:
            # an unreadable switch is not an OFF switch — a truncated write mid-save must not
            # silently blind the eye until someone notices
            _SHADOW_CACHE["on"] = True
    return _SHADOW_CACHE["on"]
_STATE_DEFAULT = STATE     # what import time chose, so a later explicit override is recognisable
_TEST_STATE_DIR = [None]


def _under_test():
    """True when this process is a test run.

    PYTEST_CURRENT_TEST is set by pytest for the duration of each test; `pytest` in sys.modules
    covers collection and module import, which is when several suites already write. Both are
    checked because either alone leaves a window, and the cost of a false positive here is a state
    file in a temp directory — while the cost of a false negative is his real one.
    """
    return bool(os.environ.get("PYTEST_CURRENT_TEST")) or ("pytest" in sys.modules)


def _test_state_dir():
    """One temp directory per test process, created lazily and never cleaned up by us — a test that
    wants to inspect what was written must still be able to find it."""
    if _TEST_STATE_DIR[0] is None:
        import tempfile
        _TEST_STATE_DIR[0] = tempfile.mkdtemp(prefix="tvd-test-state-")
    return _TEST_STATE_DIR[0]


def _state_path():
    """Where live state belongs RIGHT NOW — not where it belonged at import.

    ⚠ v1924 — THE v1869 RULE ABOVE WAS CORRECT AND UNREACHABLE HALF THE TIME. `STATE` is computed
    once, when this module is first imported, so a caller that repoints TV_HIST *afterwards* — which
    is what a test method does, because the import happened during collection — got his real tree
    anyway. The redirect looked applied and was not.

    Measured on his own machine, 2026-08-21: one gate run wrote **39 stub reads into his live
    tv/state.json**, replaced his session id, and left `readCount: 39` against a `cap: 240` — the
    tests spent a sixth of his daily read budget and the file grew 3,867 -> 49,080 bytes. Every one
    of those reads was `mode: "stub"`. It had been happening on every local run.

    Explicit still wins: a test that assigns `tv_diablo.STATE = <tmp>` has said exactly where it
    wants state, and that is honoured untouched. Only the untouched default re-reads the environment.
    [[feedback-fixtures-never-touch-live-data]]
    """
    if STATE != _STATE_DEFAULT:
        return STATE
    root = _fixture_root(HERE)
    if root == HERE and _under_test():
        # ⚠ NOTHING REDIRECTED, AND WE ARE IN A TEST. v1869 only moves live state when TV_HIST says
        # so, and most suites never set it — so `test_agent`, `test_routes` and `test_control` each
        # wrote stub reads straight into his real state.json, measured at roughly 1.7 KB a suite,
        # every local run, for as long as they have existed. A default that is safe only when the
        # caller remembers to redirect is not a default, it is a trap. [[feedback-fixtures-never-touch-live-data]]
        return os.path.join(_test_state_dir(), "state.json")
    return os.path.join(root, "state.json")


PORT   = int(os.environ.get("TV_PORT", "17771"))   # v711 — overridable (tests · port conflicts)
# v780 — one ON cycle = one theatre session. Every journal row carries this id so SIM/theatre
# never glues multiple restarts into one mega-run (the 10min gap alone was too soft).
SESSION_ID = ""
# v901 — PRODUCT: Auto Intake (default) vs Robot (FROZEN unless TV_ROBOT=1).
# Intake = settle on stash/loot → deep read → board feeds locked Tools/Vault 📸 pipelines.
ROBOT_MODE = str(os.environ.get("TV_ROBOT", "0") or "0").strip().lower() in ("1", "true", "yes", "on")
# v925 LIGHT (Konyo, acceptance day: 'so laggy i cant play a game even… like a reader, not
# needing to process so heavy… like screenshot not record… 1 claude is enough'). LIGHT is the
# DEFAULT product now: a gentle screenshot reader, not a screen recorder. No continuous film,
# a slow sensor tick, no OCR lane. Heavy capture (film/OCR/fast poll) is opt-in for the SIM
# debugger via TV_LIGHT=0. Robot mode implies heavy.
LIGHT_MODE = (not ROBOT_MODE) and str(os.environ.get("TV_LIGHT", "1") or "1").strip().lower() not in ("0", "false", "no", "off")
MIN_GAP_S    = float(os.environ.get("TV_MIN_GAP", "3.5" if not ROBOT_MODE else "1.5") or 3.5)
HEARTBEAT_S = max(1.0, min(20.0, float(os.environ.get("TV_HEARTBEAT", "8.0" if not ROBOT_MODE else "3.0") or 8.0)))
PRIORITY_GAP_S = float(os.environ.get("TV_PRIORITY_GAP", "1.0" if not ROBOT_MODE else "0.7") or 1.0)
SESSION_CAP  = 240
# v925 — the sensor tick: LIGHT samples the screen ~every 1.8s (loot waits on the ground), not
# ~7×/second. This poll capture (Grok: cut #2) is the biggest steady lag after the film loop.
POLL_S       = float(os.environ.get("TV_POLL", ("1.8" if LIGHT_MODE else "0.15") if not ROBOT_MODE else "0.12") or 0.15)
# v926.2 ADAPTIVE CADENCE (Konyo: 'once im in the game the screenshotter loops again and slows
# it') — a full-screen grab forces the Mac to read back the framebuffer, and doing that while a
# GPU game renders causes a brief hitch. So during ACTIVE play (screen changing = you're moving/
# fighting, nothing readable anyway) the reader backs off to PLAY_GAP_S; the instant you PAUSE
# (screen settles = loot/stash) it drops back to POLL_S and reads. Capture load is near-zero when
# you're playing hard, and only picks up when you stop to look — the one time a read matters.
PLAY_GAP_S   = float(os.environ.get("TV_PLAY_GAP", "4.0" if LIGHT_MODE else "1.0") or 4.0)
WATCH_MODE   = "--watch" in sys.argv

# ── v1595 — THE MINI FLAG. control_app has appended --mini=<secs> --mini-focus=<what> to this
# agent's argv since the mini endpoint landed, and this file parsed argv with bare `in sys.argv`
# checks, so BOTH were read as unknown words and dropped. The consequence was quiet and total: a
# mini run behaved exactly like ON AIR, and — the part that mattered — NO REEL WAS EVER STAMPED as
# mini, so vault_retro.is_mini_reel() could never once return True and its mini-first ordering was
# unreachable code sitting behind a condition nothing could satisfy.
#
# A parked stash session is the densest evidence in the whole archive: he is not fighting, the
# panel is held still, and every frame is a clean look at what he owns. That is exactly the footage
# the accumulator wants first, and it was indistinguishable from a boss run.
def _argv_val(flag, default=None):
    """--flag=value or --flag value. Returns default when absent or malformed."""
    pre = flag + "="
    for i, a in enumerate(sys.argv):
        if a.startswith(pre):
            return a[len(pre):]
        if a == flag and i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith("--"):
            return sys.argv[i + 1]
    return default

_mini_raw   = _argv_val("--mini")
MINI_MODE   = _mini_raw is not None
try:
    MINI_SECONDS = max(10, min(40, int(float(_mini_raw)))) if MINI_MODE else 0
except Exception:
    MINI_SECONDS = 25 if MINI_MODE else 0        # a garbled number is still a mini run
# ── v2027 — A DECLARED FOCUS IS A DECLARATION WHATEVER THE SESSION LENGTH ────────────────────
# Konyo, after filming a reel with the Tools -> "Vault items (auto-file to mules)" card: "when i
# click this it doesnt need the same logic to read the items and vault them automatically ... it
# should understand its focused and i am working together with it on a focused task".
#
# He was right that it was coded — and right to check, because it only ever reached MINI. This read
# --mini-focus ONLY `if MINI_MODE`, so a full ON AIR session dropped the flag on the floor and wrote
# focus:"" into index.json. MEASURED on the reel he had just filmed
# (reel_s_1787508759592_46621, 80 frames, 30 of 40 sampled frames showing a stash panel):
# index.json keys were ['blank','blankPass','frames','n','sessionId'] — no focus at all. So the
# sweep paid a classifier to work out what he had already told the console he was doing.
#
# The bound (MINI_SECONDS) is genuinely mini-only and stays that way. The FOCUS is not about
# duration; it is about what he says he is looking at.
_FOCUS_ARG  = _argv_val("--mini-focus")
MINI_FOCUS  = _FOCUS_ARG or ("stash" if MINI_MODE else "")
# v1783 — the FLAG BEING PRESENT is the choice. "stash" also arrives as the fallback above and as
# the console's pre-selected button, so the value alone cannot say whether he picked it.
# vault_retro._declared_surface() enforces exactly this: focusChosen false -> the focus is NOT
# trusted, so a defaulted "stash" can never label town as a stash panel.
MINI_FOCUS_CHOSEN = bool(_FOCUS_ARG)
if MINI_MODE:
    print(f"⏱ MINI CAPTURE — {MINI_SECONDS}s, focus={MINI_FOCUS}", flush=True)
MOTION_PEAK  = 0.10
SETTLE       = 0.03
_FILM_FPS = max(4, min(30, int(float(os.environ.get("TV_FILM_FPS", "5" if not ROBOT_MODE else "8") or 5))))
FILM_INTERVAL_S = 1.0 / float(_FILM_FPS)
_FOOTAGE_FPS = max(1, min(5, int(float(os.environ.get("TV_FOOTAGE_FPS", "1") or 1))))
FOOTAGE_INTERVAL_S = 1.0 / float(_FOOTAGE_FPS)
# v3894 — every PC's film is 1920x1080 (Elad, 2026-11-10: Dean's shadow theatre was a magnified
# 160 px thumb of an 800 px Windows eye). A windowed client (Dean-shaped 1507x755, #255) is
# resampled and letterboxed onto this box so readers share the Mac's reference coordinates.
# TV_FILM_MAX_PX still caps the longest side when set.
FILM_W, FILM_H = 1920, 1080
FILM_MAX_PX = max(1280, min(3840, int(os.environ.get("TV_FILM_MAX_PX", "1920") or 1920)))
FILM_JPEG_Q = max(55, min(95, int(os.environ.get("TV_FILM_Q", "82" if not ROBOT_MODE else "82") or 82)))
_FILM_TIMES = deque(maxlen=64)

# v710.1 — SCENARIO ENGINE (Konyo: "once those moments are captured it can automatically be
# coded to flag farming when not in town — the corner always shows where we are on the map").
# Every read extracts WHERE (area = the zone name on the HUD/automap corner) and WHICH MOMENT
# (scene: town/loot/inventory/stash/gameplay) alongside the item names.
# Prompt truths calibrated on Konyo's REAL session videos (2026-07-15, town + Cold Plains runs):
#  · top-right block = "Game: <name>" then the CURRENT AREA, then purple lines = today's terror
#    zones — persistent during play, hidden when a right-side panel (inventory) covers it
#  · zone transitions flash a red "ENTERING <ZONE>" banner
#  · panel grids show item ICONS with no text — names ONLY come from hover tooltips (first line
#    = name), ground labels (loot key held), waypoint labels ("<Zone> Waypoint"), and the
#    DETACHED top-left hover label (ground item hovered while a panel is open)
# v730 — shorter prompt (run #4: inventory 25.8s was too hot; less prose → faster JSON)
# v734 — stashTab when scene=stash (RotW left tabs: Personal·Shared·Gems·Materials·Runes)
PROMPT_VER = "p3552"   # v3552 — #234: every named item's POINT and its doll SLOT are asked (names_xy / names_slot); bump whenever READ_PROMPT changes
#: v3552 — HIS RULING, 2026-10-01 ("thats even better": the points are asked FROM NOW ON, no re-read of old footage). The
#: reader versions whose answers still answer the question PROMPT_VER asks: p3552 only ADDED each item's point and slot;
#: the scene, the Chronicle verdict and every name are asked exactly as p1839 asked them. So a p1839 seal still stands and
#: its per-frame read count still counts - nothing he filmed is bought again. A prompt that changes the QUESTION is a new
#: version with NOTHING listed here. control_app._chron_seal_stands and _chron_read_count read this. [[stale-reading]]
PROMPT_ANSWERS_SAME_AS = ("p1839",)
_LAST_RAW = ""        # v832 (SIMULATION_SPEC) — the model's literal words for the read in flight
READ_PROMPT = (
    "Image {path} = Diablo II Resurrected (RoW). Reply with STRICT JSON only, no markdown, no prose:\n"
    "{{\"area\":\"\",\"tz\":[],\"scene\":\"gameplay\",\"stashTab\":\"\",\"chronicleTab\":\"\",\"gameName\":\"\",\"cls\":\"\",\"level\":0,\"avatarClass\":\"\",\"names\":[],\"names_loc\":{{}},\"names_slot\":{{}},\"names_xy\":{{}},\"sockets\":{{}},\"discovered\":[],\"conf\":0.0}}\n"
    "scene = one of: town | stash | inventory | loot | gameplay | transition | chronicle.\n"
    # v1509 — THE CHRONICLE SCENE. Konyo: "when chronicle/menu is clicked ingame it should
    # automatically know we are about to register and read and analyze the CHRONICLE lists."
    # This is the scene the whole auto-tally arc hangs off: nothing downstream can fire while the
    # classifier has no word for the screen. The UNIQUES/SETS split is not cosmetic — they are two
    # different ledgers (d2r_foundLog vs d2r_setPieces, 243/403 and 108/135), and a Sets screen
    # tallied as Uniques is worse than no tally at all, so the tell is spelled out rather than left
    # to the model's judgement.
    "chronicle = the in-game HOLY GRAIL / CHRONICLE panel: a scrollable LIST of item names with "
    "found/unfound styling, opened from the menu. It is NOT the stash and NOT the inventory — there "
    "is no grid of item icons to pick up, only rows of names. "
    # v1773 — MEASURED, NOT IMAGINED. Called directly on his 08-17 frames: a page where his cursor
    # rested on a row — so the game painted a large item stat tooltip over the list — came back
    # scene='transition' at conf 0.85 with zero names, while two clean pages from the same reel came
    # back chronicle/uniques with 6 names each. The tell for `transition` two paragraphs down is the
    # ABSENT bottom HUD, and that frame showed the life orb, the mana orb and the belt row plainly;
    # the popup simply dominated the picture. classify() runs once per RUN, so that one answer
    # discarded up to 44 Chronicle pages behind it. v1773 gives a refused run a second opinion, but
    # a workaround downstream is not a reason to leave the reader wrong here.
    "A large ITEM TOOLTIP (a floating stat block: damage, requirements, blue affix lines) often "
    "covers part of this panel when the cursor rests on a row. That is still scene=chronicle — the "
    "CHRONICLE title bar, the Unique/Sets/Runewords tabs and the rows around the popup are the tell. "
    "It is NEVER a transition: a transition has no bottom HUD, and this panel is drawn over a live "
    "game with the life and mana orbs still on screen. Read whatever rows the popup leaves visible.\n"
    "chronicleTab = ONLY when scene=chronicle: which ledger is on screen. "
    "\"uniques\" = the unique-item list (single items: Shako, Windforce, Stormshield). "
    "\"sets\"    = the set list (rows grouped under set NAMES: Tal Rasha, Immortal King, Tancred). "
    "If you cannot tell which of the two it is, leave chronicleTab \"\" — an unknown ledger is "
    "recoverable, a wrong one silently corrupts the other ledger.\n"
    "When scene=chronicle put EVERY item name you can read in names[], in the order shown, and put "
    "the found/claimed ones in discovered[]. A partial or scrolled list is expected and fine — "
    "never invent names to fill a page.\n"
    "chronicleSort = ONLY when scene=chronicle: the sort control at the TOP RIGHT of the panel, read "
    "literally. \"newest\" if it says Newest to Oldest, \"oldest\" if Oldest to Newest, \"other\" for any "
    "other ordering, \"\" if it is not visible. This is what decides whether the TOP of the list is his "
    "most recent finds, so guessing it is worse than leaving it blank.\n"
    "foundAt = ONLY when scene=chronicle: map each item name -> its exact 'First Found:' stamp, copied "
    "digit for digit, e.g. {{\"Razorswitch\":\"08/20/2026, 00:49\"}}. NEVER infer a date from a row's "
    "position in the list, and omit any row whose stamp is covered by a tooltip or cut off at the panel "
    "edge — a missing stamp is recoverable, an invented one is a false find date forever.\n"
    "droppedBy = ONLY when scene=chronicle: map each item name -> the monster on its 'Dropped By:' line, "
    "e.g. {{\"Razorswitch\":\"Infector of Souls\"}}. Omit what you cannot read.\n"
    "⚠ THE TWO TABS PRINT THOSE LINES IN OPPOSITE ORDER — measured on his frames, not assumed. On "
    "UNIQUE a row reads: name / 'First Found: ...' / 'Dropped By: ...'. On SETS it reads: name / "
    "'Dropped By: ...' / 'First Found: ...'. Read each line by its LABEL, never by its position under "
    "the name, or every set piece gets a monster where its date belongs.\n"
    "transition = fullscreen loading/portal art: the burning fire portal, act loading screen, or a "
    "dark frame with NO bottom HUD. THE DECIDING TELL: if the bottom HUD (belt row / red life + blue "
    "mana orbs / skill bar) is ABSENT the frame is transition; a dark COMBAT frame (night, a cave, a "
    "dim boss room) STILL shows that HUD, so it stays gameplay. The player is entering a portal, "
    "waypoint, or a new game — names are expected empty; if an 'ENTERING <zone>' banner is legible put "
    "that zone in area, else leave area \"\".\n"
    "area = zone name from top-right Game block / ENTERING banner / automap, else \"\".\n"
    # v3855 - identity signals (read_identity.parse_identity); the game PASSWORD is never asked for or returned
    "gameName = the game's NAME only when printed (create/join game screen, Esc overlay, chat 'joined game'), else \"\". "
    "NEVER the password: leave any password out entirely.\n"
    "cls / level = ONLY on the login character-select screen or the character panel: the selected character's "
    "class (Amazon|Assassin|Barbarian|Druid|Necromancer|Paladin|Sorceress) and level, else \"\" and 0.\n"
    "avatarClass = the class of the player's own in-game avatar when it is clear, else \"\".\n"
    "tz = purple terror-zone lines in that block, else [].\n"
    "stashTab = ONLY when scene=stash: which LEFT stash tab is active — "
    "personal | shared | gems | materials | runes | \"\" if unknown. "
    "Stash tell: left panel tabs + inventory often open on the right.\n"
    "names = READABLE text labels only (tooltips first line, ground loot labels, open inventory/stash "
    "name text). Never invent from icons alone. Never complete partial names.\n"
    "sockets = for any item whose tooltip shows a 'Socketed (N)' line OR N visible empty socket "
    "holes, map its exact name -> N (integer), e.g. {{\"Diadem\":3}}. Omit items with no sockets; "
    "{{}} if none. Read the number from the tooltip, never guess from the base type.\n"
    "names_loc = for EVERY name: WHERE its tooltip/label lives — one of "
    "equipped | inventory | stash | floor. Tells: tooltip says 'to Unequip' or hovers the character "
    "equipment doll = equipped (the player's WORN gear, not loot). Tooltip anchored over the RIGHT "
    "inventory grid = inventory (charms saying 'Keep in Inventory' are inventory). Tooltip over the "
    "LEFT stash panel grid = stash. Ground label / detached top-left label = floor. When stash+inventory "
    "are BOTH open, judge by WHICH panel the tooltip covers — never assume stash.\n"
    # v3552 (#234) — WHERE EACH ITEM WAS SEEN. His words: "the items being witnessed also need coordinates based on
    # where they were witnessed". The point is the ITEM, never its tooltip: the tooltip floats wherever the game puts it,
    # the item sits in one cell or one doll slot, and that cell is what his character window draws.
    "names_xy = for EVERY name you can point to: the [x, y] pixel position IN THIS IMAGE of the ITEM ITSELF - the icon "
    "under the cursor whose tooltip you read, the item's cell in the stash or inventory grid, the item on the equipment "
    "doll, or the centre of a ground label. NEVER the tooltip box. Whole pixels from the image's top-left corner. Omit a "
    "name you cannot point to - a missing point costs nothing, a wrong one files the item in the wrong cell.\n"
    "names_slot = ONLY for a name whose names_loc is equipped: the doll slot that holds it - one of helm | amulet | "
    "weapon | torso | off-hand | gloves | ring1 | belt | ring2 | boots (ring1 = the ring LEFT of the belt on screen, "
    "ring2 = the ring RIGHT of it). Omit when unsure.\n"
    "Never put merc/NPC/player names, HP bars, waypoint labels, or chat into names.\n"
    "discovered = ITEM names from chat DISCOVERY broadcasts only (lines like "
    "'<player> has found <item>' / 'has discovered'). Just the item names; [] if none. "
    "Normal chat/trade text is NEVER a discovery.\n"
    "inventory/stash: list anchors (Horadric Cube, Tome of Town Portal, Tome of Identify) when visible "
    "BUT prioritize NEW tooltips / names that are not the always-on cube+tomes.\n"
    "conf = 0.0-1.0 confidence. Be fast and precise."
)

# v926 SECOND LOOK (Konyo: 'it can check and verify and recheck and reverify and literally be
# more accurate') — LIGHT freed the machine, so the reader spends the idle gap DOUBLE-CHECKING
# each item read against the SAME archived screenshot. A closed-set confirm first, then a tight
# open pass for anything clearly missed. Corrections flow through the SAME lifecycle/funnel pipes.
VERIFY_ON = str(os.environ.get("TV_VERIFY", "1" if LIGHT_MODE else "0")).strip().lower() in ("1", "true", "yes", "on")
VERIFY_PROMPT = (
    "Image {path} = the SAME Diablo II Resurrected screenshot a first reader already looked at.\n"
    "It reported these item names: {prior}.\n"
    "Look at the screenshot AGAIN, carefully, and correct that reading. STRICT JSON only:\n"
    "{{\"confirm\":[],\"missed\":[],\"not_present\":[],\"conf\":0.0}}\n"
    "confirm = names from the reported list that ARE clearly present on screen.\n"
    "not_present = names from the reported list that are NOT actually on screen (misreads/hallucinations).\n"
    "missed = item names CLEARLY readable on screen but absent from the reported list (max 5). "
    "Only add a name you can actually read as text — never from an icon, never a guess.\n"
    "conf = 0.0-1.0 confidence in this correction. Be strict: when unsure, prefer confirm over change."
)

# v752 — persistent session journal (tv/sessions.jsonl, gitignored): every published read
# appended as one JSON line. This is what `tvd replay` re-runs — real frames, real reads.
def _journal_path():
    """Where session rows are appended — and NEVER his live journal when the frames are a fixture.

    v1866 — MEASURED, NOT SUSPECTED: 1,729 rows in tv/sessions.jsonl carry a `_dur` session id and
    the note "durability-harness". That is test_reel_index_durability.py, which correctly gives its
    child an isolated TV_HIST and TV_FRAMES_DIR — and never knew there was a THIRD path to isolate.
    75% of the session_end rows in his journal are from a test harness, still arriving during gate
    runs tonight.

    The fix is the one his scar names: GUARD THE FIXTURE, NOT THE CALL SITE. A caller that isolates
    the frames has said, unmistakably, "this is not his world"; a journal beside those frames is the
    only journal that can describe them. So an overridden hist that does not live under this module
    implies an overridden journal, and a test that forgets is protected anyway.

    TV_SESSIONS still wins when set explicitly — the CI harness has always used it and knows what it
    is asking for. [[feedback-fixtures-never-touch-live-data]]
    """
    explicit = os.environ.get("TV_SESSIONS")
    if explicit:
        return explicit
    # ⚠⚠ v2937 — CALL THE ONE RESOLVER; DO NOT RE-IMPLEMENT IT. This carried its own copy of the
    # rule, so v2932's narrowing (blank or relative TV_HIST is not a request for isolation) reached
    # `_fixture_root` and never reached here. MEASURED from the repo root with TV_HIST="   ":
    # this returned `<repo>/   /sessions.jsonl` — the exact REG-937 harm, still live, beside the two
    # lines that ship changed. `_log_root` already records this shape: v2783/v2785 fixed one copy
    # and neither swept to the other. Caught by the cross-family eye on v2932. [[copy-drift]]
    return os.path.join(_fixture_root(HERE), "sessions.jsonl")


JOURNAL = _journal_path()   # v877 — CI harness override; v1866 — an isolated hist isolates this too
_JOURNAL_WARNED = False
_JQ = None   # v879 (Grok A-(a)) — ONE writer thread preserves apply order; emit never blocks on fsync
def _journal_writer_loop():
    while True:
        rec = _JQ.get()
        if rec is None:
            _JQ.task_done()
            return
        try:
            _journal_write(rec)
        except Exception as e:
            # v886 — a lost journal row is a lost read FOREVER: say so, loudly
            try:
                print(f"  ⚠ JOURNAL WRITE FAILED ({type(e).__name__}: {str(e)[:120]}) — read row lost", flush=True)
                ev("cap", f"journal write failed: {type(e).__name__}")
            except Exception:
                pass
        _JQ.task_done()


def _journal_flush(timeout=10.0):
    """v880 (Grok back-pass #3) — a REAL join: queue.empty() goes true before the fsync
    finishes; task_done() fires only after the write. join() in a helper thread + timeout."""
    try:
        if _JQ is None:
            return
        done = threading.Event()
        def _j():
            try:
                _JQ.join()
            except Exception:
                pass
            done.set()
        threading.Thread(target=_j, daemon=True).start()
        done.wait(timeout)
    except Exception:
        pass


# v2687 — WHICH DOOR OPENED THIS REEL. control_app knows it at spawn (start_agent's `origin`,
# v2362) and until now it stayed in the PARENT's memory: it was served to the UI and never written
# where the reel itself could carry it. Measured 2026-09-05: 0 of 10,121 journal rows carried a
# door, so no reel could answer "which door did I come through" and nothing downstream could route
# by entry. Three layers each knew the answer and none of them wrote it down. [[the-unjoined-end]]
#
# ⚠ THE FIELD IS `door`, NOT `origin`. This module already has an `origin` on its dispatch context
# ("settle" | "heartbeat" | "text-eye" | "farewell"), which answers a DIFFERENT question — what
# woke this read, not what opened this reel. Reusing the word would put two quantities under one
# label on the same row. [[label-outlived-referent]]
_DOOR = (os.environ.get("TV_DOOR") or "").strip().lower()


def _journal(rec):
    """v879 — enqueue when the writer runs; direct write otherwise (tests/replay).

    v1866 — EVERY ROW A SIMULATION WRITES SAYS SO. Konyo's own journal holds 414 rows produced
    under TV_STUB across ten days, sitting beside real ones with nothing on them to tell the
    difference except `mode: "stub"` on the deep-read rows — and a session's summary rows carry no
    mode at all, so a whole SIM session was indistinguishable from a live one that saw nothing.

    That mattered tonight: while MINI was dead (v1863) he pressed buttons, and control_agent.log
    records five starts in 64 seconds alternating sim · live · live · sim. He then reported "i did
    a regular LIVE SESSION it worked" and asked why the readers had not read his Sets chronicle.
    Under TV_STUB the deep reader returns canned rows whose scene defaults to "gameplay", so a
    Chronicle page open on screen is journaled as gameplay and nothing is wrong with the reader.

    THE EXPOSURE IS REAL AND HAS NOT FIRED — say both halves. stub_manifest.json carries real item
    names ("Ars Dul'Mephistos", "Skin of the Vipermagi", "Ist Rune"), and nothing excluded a sim
    reel from a sweep. It never landed because the manifest is keyed by basenames his reels never
    use (pit_loot.jpg, town_stash.jpg) and the "*" fallback returns names: []. Measured: 0 of 414
    stub rows carry a canned name. A guard that depends on a filename not colliding is not a guard,
    so the flag is the guard. [[feedback-fixtures-never-touch-live-data]]
    """
    try:
        if os.environ.get("TV_STUB") and isinstance(rec, dict) and "sim" not in rec:
            rec = dict(rec)
            rec["sim"] = True
    except Exception:
        pass
    # v2687 — the entry stamp, on EVERY row, for the same reason `sim` is: a property of the whole
    # session belongs on each row or a row read on its own cannot be placed. Absent door = absent
    # key, never a guessed default: a reel filmed before this shipped must read as UNKNOWN, not as
    # "onair". [[unknown-stays-unknown]]
    try:
        if _DOOR and isinstance(rec, dict) and "door" not in rec:
            rec = dict(rec)
            rec["door"] = _DOOR
    except Exception:
        pass
    if _JQ is not None:
        try:
            _JQ.put(dict(rec) if isinstance(rec, dict) else rec)
            return
        except Exception:
            pass
    _journal_write(rec)


def _journal_write(rec):
    global _JOURNAL_WARNED
    if os.environ.get("TV_NO_JOURNAL"):   # v753 — a REPLAY is a re-broadcast, never a new session
        return
    try:
        if isinstance(rec, dict) and SESSION_ID and not rec.get("sessionId"):
            rec = dict(rec)
            rec["sessionId"] = SESSION_ID
        need_nl = False
        try:
            if os.path.getsize(JOURNAL) > 0:
                with open(JOURNAL, "rb") as f:
                    f.seek(-1, 2); need_nl = f.read(1) != b"\n"
        except Exception:
            pass
        with open(JOURNAL, "a", encoding="utf-8") as f:
            if need_nl: f.write("\n")
            f.write(json.dumps(rec) + "\n")
            f.flush(); os.fsync(f.fileno())   # v779 (Grok R5/R7) — durable append: a crash mid-write can't erase the night
        try:
            _fid = isinstance(rec, dict) and rec.get("frameId")
            if _fid and isinstance(_JFID_STATE.get("ids"), set) and _JFID_STATE.get("path") == JOURNAL:
                _JFID_STATE["ids"].add(str(_fid) + ".jpg")   # v877 — grows AT APPEND; suffix matches the shield
        except Exception:
            pass
        if os.path.getsize(JOURNAL) > 4_000_000:   # ~4MB → ROTATE (never half-truncate the live file)
            # v811 (Grok R8 #6 + sleeper) — GENERATIONS, not one slot: .1 is newest rotation,
            # older shift up to .5 (~20MB ≈ months). A second heavy night can no longer erase
            # the first with zero lamp.
            _root, _ext = os.path.splitext(JOURNAL)
            for _g in range(4, 0, -1):
                _src = _root + ".%d" % _g + _ext
                if os.path.exists(_src):
                    os.replace(_src, _root + ".%d" % (_g + 1) + _ext)
            os.replace(JOURNAL, _root + ".1" + _ext)
            try: ev("cap", "journal rotated — generation ring .1-.5 (~20MB of nights kept)")
            except Exception: pass
    except Exception as e:
        if not _JOURNAL_WARNED:
            _JOURNAL_WARNED = True
            try: ev("cap", f"journal write failed ({e}) — replay of this session won't be available")
            except Exception: pass

_state_lock = threading.Lock()
_STATE_MEM = None          # v879 (Grok A) — the AUTHORITATIVE state lives in memory
_STATE_PATH = None         # path key: tests/replay repoint STATE — the cache follows
_STATE_DIRTY = [False]
def _load():
    """v879 — one cold disk read per process; every later _load() is the in-memory dict.
    The old per-call json.load ran at 4Hz from /state AND inside every apply."""
    global _STATE_MEM, _STATE_PATH
    _p = _state_path()
    if _STATE_MEM is None or _STATE_PATH != _p:
        _STATE_PATH = _p
        _STATE_MEM = None
    if _STATE_MEM is None:
        try:
            with open(_p, encoding="utf-8") as f:
                _STATE_MEM = json.load(f)
        except Exception:
            _STATE_MEM = {"online": True, "startedAt": int(time.time()*1000), "reads": [], "readCount": 0}
    return _STATE_MEM

def _save(st):
    """v879 — WRITE-BEHIND: callers mark dirty; the saver thread (or a flush) hits disk.
    st is the in-memory dict (or replaces it — replay/tests pass fresh dicts)."""
    global _STATE_MEM, _STATE_PATH
    _STATE_MEM = st
    _STATE_PATH = _state_path()
    _STATE_DIRTY[0] = True

def _state_flush():
    """Serialize the in-memory state to disk (atomic replace). Called by the saver thread,
    at seal, and at farewell — Grok flush list items 3/6."""
    st = _STATE_MEM
    if st is None:
        return
    _p = _state_path()
    tmp = _p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(st, f)
    os.replace(tmp, _p)
    _STATE_DIRTY[0] = False

def _state_saver_loop():
    while True:
        time.sleep(1.0)
        try:
            if _STATE_DIRTY[0]:
                with _state_lock:
                    _state_flush()
        except Exception:
            pass

_BEAT = {"ts": 0, "phase": "idle", "motion": 0.0}
_EVENTS = []
# v727 Autopilot HUD — continuous driver state (Tesla stack, screen edition)
_AP = {
    "mode": "boot",          # boot|drive|hunt|settle|read|load
    "interest": 0.0,         # 0–1 how badly we want a vision fire
    "peak": 0.0,             # recent max motion (hunting for a stop)
    "priority": False,       # next settle uses short gap
    "emptyStreak": 0,
    "namedStreak": 0,
    "lastNamed": "",
    "gap": MIN_GAP_S,
    "ver": VERSION,
}
def ev(kind, text):
    """v710.6 — the BRAIN LOG: the scanner's real decisions, streamed to the board
    (in-memory ring like the beat; /state merges it — no disk churn)."""
    _EVENTS.append({"ts": int(time.time()*1000), "k": kind, "t": str(text)[:120]})
    del _EVENTS[:-60]
def beat(phase, motion):
    """v710.4 — the LIVE pulse, IN MEMORY only (Grok audit: rewriting state.json twice a
    second thrashed disk + the lock). /state merges it at request time; reads still persist."""
    _BEAT["ts"] = int(time.time()*1000); _BEAT["phase"] = phase; _BEAT["motion"] = round(float(motion), 3)
    _AP["mode"] = {"loading": "load", "watching": "drive", "reading": "read"}.get(phase, phase)

def ap_interest(peak, stable_ticks, priority, empty_streak, named_recent, parts=None):
    """0–1 score: hard motion → stop is the 'money moment' (pile / panel).
    v833 (Grok addendum A2.1) — pass parts={} to receive the DECOMPOSITION: almost every real
    fire scores 1.0, so forensics need the inputs that built it, not the flat number."""
    s = 0.15
    p = {"base": 0.15, "peak": 0.0, "priority": 0.0, "named": 0.0, "empty": 0.0, "stable": 0.0}
    if peak >= MOTION_PEAK: s += 0.45; p["peak"] = 0.45
    elif peak >= 0.06: s += 0.2; p["peak"] = 0.2
    if priority: s += 0.25; p["priority"] = 0.25
    if named_recent: s += 0.1; p["named"] = 0.1
    if empty_streak >= 3: s -= 0.08; p["empty"] = -0.08   # slight downrank only — never blocks
    if stable_ticks >= 1: s += 0.1; p["stable"] = 0.1
    if isinstance(parts, dict):
        parts.update(p)
    return max(0.0, min(1.0, s))

def _film_fps_now():
    """Rolling film FPS over the last ~1.5s of successful eye frames."""
    try:
        now = time.time()
        recent = [t for t in _FILM_TIMES if now - t <= 1.5]   # v877 — deque, no destructive prune
        n = len(recent)
        if n < 2:
            return 0.0
        span = max(0.001, recent[-1] - recent[0])
        return round((n - 1) / span, 1)
    except Exception:
        return 0.0


def _health(st):
    """v789 (Grok R4 #1) — one small truth object for the fault lamp. A 2-hour farm used to
    die quietly (vision stall, game quit, capture death) while the lamp said ON AIR."""
    now = time.time()
    # v877 (army audit #5) — footage fps from the in-memory archive deque; the old
    # os.listdir over ~30k files ran 4×/s from the board poll.
    _foot_fps = _foot_fps_now()
    # v863 (READER POOL) — busy lamp = oldest in-flight reader's age; expose pool depth.
    _pool_pin, _pool_oldest = 0, 0
    try:
        with _pool_lock:
            _pool_pin = len(_in_flight)
            if _in_flight:
                _pool_oldest = min(int(j.get("startedAt") or 0) for j in _in_flight.values())
    except Exception:
        pass
    try:
        import shutil as _shf
        _free_gb = round(_disk_free_bytes(FRAMES) / 1e9, 1)
    except Exception:
        _free_gb = None
    h = {"eyeAgeMs": _eye_age_ms(), "captureMode": (_CAP_TARGET or {}).get("mode", ""),
         "freeGB": _free_gb, "minFreeGB": MIN_FREE_GB,   # v872.1 — disk emergency is LOUD, never silent
         "throttled": _is_throttled(),   # v891 — the 🐢 chip's truth
         "footageFps": _foot_fps,   # v861 — the archive floor, alarmed by the UI
         "visionBusyMs": (max(0, int(now * 1000) - _pool_oldest) if (_pool_pin and _pool_oldest) else 0),
         "poolInFlight": _pool_pin, "poolN": POOL_N,
         "poolWarm": sum(1 for _w9 in _WORKERS if getattr(_w9, "warm_ok", False)),   # v870
         "sessionMs": 0, "lastReadAgeMs": -1, "named": 0, "vaulted": 0,
         # v846 — Tesla-drive dashboard truth
         "filmFps": _film_fps_now(), "filmTargetFps": _FILM_FPS,
         "footageTargetFps": _FOOTAGE_FPS,   # REG-1948 — "footageFps" is set once, above (it was set twice here)
         "filmLane": globals().get("_FILM_LANE", ""), "filmCapMs": globals().get("_FILM_CAP_MS"),   # v867
         "footageWhy": globals().get("_FOOTAGE_WHY", ""),   # v947 — grab|bridge-last-good|disk-full
         "footageBridges": int(globals().get("_FOOTAGE_BRIDGES") or 0),
         "filmWhiteRejects": int(globals().get("_FILM_WHITE_REJECTS") or 0),
         "filmMaxPx": FILM_MAX_PX, "pollMs": int(POLL_S * 1000),
         # v944 — brains 1+2: live settle ring depth + un-read text-eye sweep backlog
         "settleQueue": len(_SETTLE_QUEUE), "textEyeBacklog": len(_TEXT_EYE_BACKLOG),
         "gapCruiseS": MIN_GAP_S, "gapPriorityS": PRIORITY_GAP_S,
         "heartbeatS": HEARTBEAT_S,
         # v899 — no-game guard: UI shows a sticky notice; AI stays dark until D2R.exe appears
         "gameOk": bool(globals().get("_GAME_OK", True)),
         "gameMsg": str(globals().get("_GAME_MSG") or ""),
         "aiPaused": bool(globals().get("_AI_PAUSED", False)),
         # v901 — product mode (Robot frozen unless TV_ROBOT=1)
         "productMode": ("robot" if ROBOT_MODE else "intake"),
         "robotMode": bool(ROBOT_MODE)}
    try:
        if st.get("startedAt"):
            h["sessionMs"] = max(0, int(now * 1000) - int(st["startedAt"]))
        reads = st.get("reads") or []
        if reads:
            h["lastReadAgeMs"] = max(0, int(now * 1000) - int(reads[-1].get("ts") or 0))
            h["named"] = sum(1 for r in reads if r.get("names"))
            h["vaulted"] = sum(len(r.get("vault_names") or []) for r in reads)
    except Exception:
        pass
    return h


def _eye_age_ms():
    """v785 — how old is the film frame? -1 = no eye at all. The stage uses this to DROP
    film-on instead of claiming LIVE on a dead frame (round-2 sleeper: eye.jpg had no
    lifecycle discipline — it outlived sessions and froze silently when capture died)."""
    try:
        eye = os.path.join(FRAMES, "eye.jpg")
        if not os.path.isfile(eye):
            return -1
        return max(0, int((time.time() - os.path.getmtime(eye)) * 1000))
    except Exception:
        return -1


def _eye_clear():
    """v785 — a session's film dies with the session; next ON never flashes yesterday."""
    try:
        eye = os.path.join(FRAMES, "eye.jpg")
        if os.path.isfile(eye):
            os.remove(eye)
    except Exception:
        pass


def bridge():
    """localhost bridge the bible polls. GET /state → JSON. CORS: any origin may READ."""
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def _hdr(self, code=200, ctype="application/json"):
            self.send_response(code)
            self.send_header("content-type", ctype)
            self.send_header("access-control-allow-origin", "*")
            self.send_header("cache-control", "no-store")
            self.end_headers()
        def do_OPTIONS(self):
            # v927.5 — CORS PREFLIGHT: the board (:17772 / bull-4-u.com) POSTs /intake_result
            # cross-origin with a JSON content-type, which triggers a preflight. Without this
            # handler every preflight 501'd, the POST died in the board's .catch, and
            # "TALLIES · synced" sat at 0 on EVERY surface while tallies actually landed.
            self.send_response(204)
            self.send_header("access-control-allow-origin", "*")
            self.send_header("access-control-allow-methods", "GET, POST, OPTIONS")
            self.send_header("access-control-allow-headers", "content-type")
            self.send_header("access-control-max-age", "3600")
            self.end_headers()
        def do_POST(self):
            # v902 (Konyo: 'wire the library to the AI READER and automatic intake') —
            # the board posts each auto-intake RESULT here; it becomes a journaled beat
            # (lane 'intake') time-synced to the frame the shot came from, so the SIM reel
            # and the session library show WHAT INTAKE DID, cross-referenced to the photo.
            if self.path.startswith("/intake_result"):
                try:
                    ln = int(self.headers.get("Content-Length") or 0)
                    body = json.loads(self.rfile.read(ln).decode("utf-8", "replace") or "{}") if ln else {}
                    now_ms = int(time.time() * 1000)
                    _ts = int(body.get("ts") or now_ms)
                    _fid = str(body.get("frameId") or "")[:48]
                    # A0 fix (2026-07-21, arch panel Q5 blocker): captureTs must be the FRAME's
                    # capture ms, not `_ts` (the receipt-landing time) — retro joins on captureTs,
                    # never ts, so a receipt stamped with receipt time desyncs from the frame it
                    # describes on the scrub. Only fall back to `_ts` when no frameId was sent
                    # (can't do better); capSrc flags which happened so retro readers know honestly.
                    _cap_from_frame = _capture_ts_from_frame_id(_fid)
                    _cap_ts = _cap_from_frame if _cap_from_frame is not None else _ts
                    _cap_src = "frame" if _cap_from_frame is not None else "receipt-fallback"
                    rec = {
                        "ts": _ts, "captureTs": _cap_ts,
                        "completedTs": now_ms,
                        "n": 0, "scene": "intake", "lane": "intake", "mode": "intake",
                        "names": [], "area": "", "sessionId": SESSION_ID,
                        "intake": _intake_result_fields(body),
                        "frameId": _fid,
                        "capSrc": _cap_src,
                        "note": ("📸 intake · " + str(body.get("tab") or body.get("kind") or "shot"))[:80],
                    }
                    _journal(rec)
                    with _state_lock:
                        st = _load()
                        st.setdefault("intakes", [])
                        st["intakes"].append({k: rec[k] for k in ("ts", "intake", "frameId", "note")})
                        st["intakes"] = st["intakes"][-60:]
                        _save(st)
                    self._hdr(); self.wfile.write(b'{"ok":true}')
                except Exception as e:
                    try:
                        self._hdr(); self.wfile.write(json.dumps({"ok": False, "msg": str(e)[:120]}).encode())
                    except Exception:
                        pass
                return
            self._hdr(); self.wfile.write(b'{"ok":false,"msg":"unknown"}')

        def do_GET(self):
            from urllib.parse import urlparse, parse_qs
            if self.path.startswith("/state"):
                # v770 (Grok R4 perf) — ?since=<ts> returns a THIN delta: full reads ring only
                # when asked from cold; 4 polls/sec no longer parse 200 rich reads every tick.
                # v1435/v1440 — ?lite=1 for control prober: readCount + eye + pin + beat, no fat rings.
                _q = parse_qs(urlparse(self.path).query or "")
                _since = 0
                try: _since = int((_q.get("since") or ["0"])[0])
                except Exception: _since = 0
                _lite = (_q.get("lite") or ["0"])[0] in ("1", "true", "yes")
                # v1419 — every state poll re-reads Windows pin so UI never sticks on eye arming
                if WATCH_MODE:
                    try:
                        _refresh_cap_target_from_disk()
                    except Exception:
                        pass
                with _state_lock:
                    st = _load(); st["online"] = True; st["now"] = int(time.time()*1000)
                    st["beat"] = dict(_BEAT); st["events"] = list(_EVENTS); st["ap"] = dict(_AP)
                    st["stopping"] = _STOPPING   # v777.2 — 1-1 sync: the board drops the INSTANT the farewell begins
                    st["captureTarget"] = dict(_CAP_TARGET)  # v772 — window pin (CrossOver/D2R) or full
                    st["eyeAgeMs"] = _eye_age_ms()   # v785 — film honesty: stage drops LIVE when this goes stale
                    st["health"] = _health(st)   # v789 — fault-lamp truth (Grok R4 #1)
                    st["sessionId"] = SESSION_ID
                    # v880 (Grok back-pass P0) — _STATE_MEM is AUTHORITATIVE now: the ?since=
                    # thin-delta must filter a COPY (the old code truncated the live ring and
                    # popped seen/farmed from the real state), and serialization happens under
                    # the lock so a concurrent apply can't resize dicts mid-dump.
                    if _lite:
                        # v1440 — tiny payload for control_app prober (~smooth under D2R)
                        _rc = st.get("readCount")
                        if _rc is None:
                            _rc = len(st.get("reads") or [])
                        out = {
                            "online": True,
                            "now": st["now"],
                            "ver": VERSION,
                            "readCount": int(_rc or 0),
                            "eyeAgeMs": st["eyeAgeMs"],
                            "captureTarget": st["captureTarget"],
                            "beat": st["beat"],
                            "sessionId": st.get("sessionId") or "",
                            "gameOk": st.get("gameOk", True),
                            "aiPaused": st.get("aiPaused", False),
                            "gameMsg": st.get("gameMsg") or "",
                            "health": {
                                "eyeAgeMs": (st.get("health") or {}).get("eyeAgeMs", st["eyeAgeMs"]),
                                "footageFps": (st.get("health") or {}).get("footageFps"),
                                "visionBusyMs": (st.get("health") or {}).get("visionBusyMs"),
                                "sessionMs": (st.get("health") or {}).get("sessionMs"),
                                "lastReadAgeMs": (st.get("health") or {}).get("lastReadAgeMs"),
                                "aiPaused": (st.get("health") or {}).get("aiPaused"),
                                "gameOk": (st.get("health") or {}).get("gameOk", True),
                                "gameMsg": (st.get("health") or {}).get("gameMsg") or "",
                            },
                            "events": list(_EVENTS)[-4:],
                            "stopping": st["stopping"],
                            "lite": True,
                        }
                    else:
                        out = dict(st)
                        if _since:
                            out["reads"] = [r for r in (st.get("reads") or []) if (r.get("ts") or 0) > _since]
                            out.pop("seen", None); out.pop("farmed", None)
                    payload = json.dumps(out).encode()
                try:
                    self._hdr(); self.wfile.write(payload)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
                    # v1430 — control aborts slow /state under D2R; never traceback-spam the log
                    pass
            elif self.path.startswith("/ping"):
                try:
                    self._hdr(); self.wfile.write(b'{"ok":true,"tv":"diablo"}')
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
                    # v1430 — Windows clients abort mid-write under load (WinError 10053 spam)
                    pass
            elif self.path.startswith("/shutdown"):
                # v847 — control OFF/STOP asks politely: save session, optional farewell, exit.
                # ?farewell=1 (STOP) · ?farewell=0 (OFF soft cut — still seals the reel)
                _q = parse_qs(urlparse(self.path).query or "")
                fare = (_q.get("farewell") or ["1"])[0] not in ("0", "false", "no")
                reason = (_q.get("reason") or ["stop"])[0][:40]
                try:
                    self._hdr()
                    self.wfile.write(json.dumps({
                        "ok": True, "msg": "shutdown accepted",
                        "farewell": fare, "sessionId": SESSION_ID,
                    }).encode())
                except Exception:
                    pass
                def _go():
                    try:
                        close_session(reason=reason, farewell=fare)
                    except Exception:
                        os._exit(0)
                threading.Thread(target=_go, daemon=True, name="tv-shutdown").start()
            elif self.path.startswith("/frame"):
                # v724 — last vision JPEG · v735 — ?id=N_ts for per-read hist archive (1920 eye)
                # v779 — bare /frame prefers the LIVE eye preview (eye.jpg) so fingerprint-skip
                # never freezes the film on a stale desktop read.jpg.
                from urllib.parse import urlparse, parse_qs
                qs = parse_qs(urlparse(self.path).query or "")
                fid = (qs.get("id") or qs.get("frame") or [None])[0]
                if fid:
                    # only allow simple ids: digits_digits (no path traversal)
                    safe = str(fid).strip()
                    if not all(c.isdigit() or c == "_" for c in safe) or ".." in safe or "/" in safe:
                        self._hdr(400); self.wfile.write(b'{"error":"bad frame id"}'); return
                    jp = os.path.join(FRAMES, "hist", safe + ".jpg")
                else:
                    eye = os.path.join(FRAMES, "eye.jpg")
                    read = os.path.join(FRAMES, "read.jpg")
                    want = (qs.get("which") or [""])[0].strip().lower()
                    if want == "read":
                        jp = read
                    elif want == "eye":
                        jp = eye
                    elif os.path.isfile(eye) and (
                        (not os.path.isfile(read))
                        or os.path.getmtime(eye) >= os.path.getmtime(read)
                    ):
                        jp = eye
                    else:
                        jp = read
                if os.path.isfile(jp):
                    try:
                        with open(jp, "rb") as f: data = f.read()
                        self.send_response(200)
                        self.send_header("content-type", "image/jpeg")
                        self.send_header("access-control-allow-origin", "*")
                        # v1440 — no-store keeps film live; max-age=0 is belt for WebView2
                        self.send_header("cache-control", "no-store, max-age=0")
                        self.send_header("content-length", str(len(data)))
                        self.end_headers()
                        self.wfile.write(data)
                    except (BrokenPipeError, ConnectionResetError):
                        pass
                    except Exception:
                        try:
                            self._hdr(500); self.wfile.write(b'{"error":"frame read failed"}')
                        except Exception:
                            pass
                else:
                    self._hdr(404); self.wfile.write(b'{"error":"no frame yet"}')
            else:
                self._hdr(404); self.wfile.write(b'{"error":"not found"}')
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    except OSError as e:
        print(f"⛔ cannot bind 127.0.0.1:{PORT} — another TV DIABLO / simulate.py is already running. Ctrl-C it first (or TV_PORT={PORT+1}).\n   {e}")
        sys.exit(2)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv

# ── v772.1 / v843 — capture target ───────────────────────────────────────────
# Konyo Mac play path (HARDCODED — agents must never invent another):
#   Desktop/CrossOver_patched.app → bottle "Battle.net Desktop App" → Battle.net
#   tile → Diablo II Resurrected Play. Bottle lives at ~/CXPBottles/…
# TV_CAPTURE=full|auto|window — default AUTO: pin D2R.exe game window only.
# NEVER pin: CrossOver Home UI, Battle.net lobby shell, browsers, TV DIABLO UI.
# TV_WINDOW_MATCH=extra,comma,tokens  (only used when window/auto)
# v935.7 — boot safe: never "full" until a real pin exists (text-eye / film obey this)
_CAP_TARGET = {"mode": "waiting", "label": "eye arming…", "wid": None}


# Owner / title tokens — game process first. Bare "wine" alone is too broad.
_PICK_WHY = ""   # v779-pre diag — why the last pick returned None
_PICK_UNKNOWN = False   # 2026-09-27 — True when the last Windows pick could not LOOK (never "no game")
#: 2026-09-28 — WHICH WAY the last successful pick was the game, written by the finder at the moment it knew:
#: {"route": "native"|"geforce-now"|"boosteroid"|"unknown", "ts": epoch ms} | None (no pick in this process).
#: The console's fleet beacon reads it (system.capture) and never calls a finder to get it. [[heart-first]] §6
_PICK_ROUTE = None
_CAP_WHY = ""
_LAST_GOOD_WIN = None   # v779 — the pin survives flaky window listings
_D2R_OWNER_HINTS = (
    "d2r.exe", "d2r", "diablo",
    # host apps only as last-resort match tokens (scoring still rejects bare Home)
    "crossover", "cross over", "cxpatcher",
)
_D2R_TITLE_HINTS = (
    "diablo ii: resurrected", "diablo ii resurrected", "diablo ii", "diablo 2",
    "d2r", "resurrected",
)
# Prefer these process/owner names when several match (game exe first)
_D2R_OWNER_PRIORITY = (
    "d2r.exe", "d2r", "diablo", "wine", "wineloader", "cxstart",
)
# v779.1 (live test): Chrome tab "Konyo's D2R Farming Bible" out-scored D2R.exe because
# title tokens matched. Browsers / editors / our own chrome are NEVER the eye.
_PICK_OWNER_BLOCK = (
    "google chrome", "chrome", "chromium", "safari", "firefox", "arc", "brave browser",
    "microsoft edge", "opera", "vivaldi", "orion", "comet",
    "code", "cursor", "visual studio code", "sublime text", "atom",
    "terminal", "iterm2", "warp", "kitty", "alacritty",
    "slack", "discord", "zoom", "figma", "notion",
    # v843 — CrossOver *app* and Battle.net *shell* are never the film target
    "crossover", "cross over",
    "battle.net.exe", "battle.net", "battle net",
)
_PICK_TITLE_BLOCK = (
    "farming bible", "d2r bible", "tv diablo", "localhost", "127.0.0.1",
    "crossover", "battle.net", "battle net",  # Home / lobby chrome titles
)
# Bare CrossOver shell / launcher Home — never the game (D2R.exe owns the real window).
_PICK_LAUNCHER_TITLES = (
    "crossover", "cross over", "battle.net", "battle net", "home",
)


#: ⚠⚠ #232 — HIS ORDER, 2026-09-24: "needs to target diablo ii resurrected in macbook like it is
#: crossover or nvideaplay chrome or boosteroid so windows also regularly for those options + the
#: usual route on windows locally. and linux cant open those they lock automatically".
#: He plays D2R three ways, and the eye must find the GAME on each: locally (D2R.exe, CrossOver-hosted
#: on the Mac), and streamed from GeForce NOW or Boosteroid — in their own app OR in a browser tab.
#: A browser was blocked wholesale (a guide tab titled "Diablo II: Resurrected build guide" must never
#: pin), which made every streamed session invisible. A browser now qualifies ONLY with the SERVICE's
#: name AND the GAME's name in its title. MEASURED ONCE, 2026-09-24, on his screen while he played
#: (caught by test_agent's live-screen case during a push): Google Chrome · "Diablo II: Resurrected –
#: Infernal Edition on GeForce NOW", pinned as geforce-now. ⚠ Boosteroid and both native apps are
#: still UNMEASURED: when a service window is open without the game in its title, the picker says so
#: (_PICK_WHY) instead of guessing, so the first real session teaches us its title.
#: [[unknown-stays-unknown]]
_CLOUD_ROUTES = (
    # (route, owner tokens of the service's own app, title markers of the service in a browser tab)
    ("geforce-now", ("geforcenow", "geforce now", "nvidia geforce now"), ("geforce now", "geforcenow")),
    ("boosteroid", ("boosteroid",), ("boosteroid",)),
)
_BROWSER_OWNERS = ("google chrome", "chrome", "chromium", "microsoft edge", "msedge", "safari",
                   "firefox", "brave browser", "brave", "arc", "opera", "vivaldi", "orion")
_GAME_WORDS = ("diablo ii", "diablo 2", "d2r")
#: ⚠ #232 — THE SECOND EYE ON v3496 (grok-4.7), reproduced: substring game words pinned "GeForce NOW -
#: Resurrected" (no Diablo), "GeForce NOW - Diablo 2024" ("diablo 2" inside "diablo 2024") and
#: "Boosteroid - ranked d2races" ("d2r" inside a longer word) as the game. A game word is now a WORD:
#: `diablo ii` / `diablo 2` / `d2r` with a boundary on both sides, and "resurrected" alone proves nothing.
_GAME_RX = re.compile(r"\bdiablo\s*(?:ii|2)\b|\bd2r\b")
#: ⚠⚠ 2026-09-27 — MEASURED, THE FIRST REAL BOOSTEROID SESSION TAUGHT US ITS TITLE, AS THE NOTE ABOVE SAID IT WOULD.
#: His Windows ALT plays D2R through Boosteroid's own app. Its capture eye, 2026-09-25 (frames/cap_target.json on
#: that PC): "a cloud window is open but its title does not name the game: Boosteroid 'Boosteroid'; Boosteroid
#: 'QTrayIconMessageWindow'". The app's window is titled with the service's name and NOTHING else while a game
#: streams, so the rule "the title must name the game" held that PC's eye shut for every session. A NATIVE app
#: window whose whole title is exactly one of these pins as that route; a browser tab never does (a tab titled
#: "Boosteroid" is their website), and any other bare title stays a named near-miss.
#: #147 — HIS RULE, 2026-10-01: "it should be universal though... nvidea play also if it opens it can be dual on macbook and
#: on windows alt and also on deans". Boosteroid's bare title was MEASURED; GeForce NOW's own app was never given the same
#: rule, so a stream window titled only with its service's name was a near-miss on every PC (no reels, and the provers
#: did not stand aside). Every cloud route's own app now pins on a bare service-name title, and _is_bare_cloud below
#: makes the "first reads must show the D2R HUD" check hold for whichever service it is. One table, every PC.
_NATIVE_BARE_TITLES = {"boosteroid": ("boosteroid",),
                       "geforce-now": ("geforce now", "geforcenow", "nvidia geforce now")}


def _norm_title(t):
    """Lowercase, and drop the marks a store page puts in the name: 'Diablo® II: Resurrected™' must
    read 'diablo ii: resurrected', or 'diablo ii' never matches a streamed title."""
    t = (t or "").lower()
    for ch in ("\u00ae", "\u2122", "\u00a9"):
        t = t.replace(ch, "")
    return " ".join(t.split())


def game_route(owner, title):
    """-> which way this window is the GAME ('local'|'crossover'|'geforce-now'|'boosteroid'), a
    near-miss string starting with 'near:' (a service window whose title does not name the game), or
    None. Pure; the scorer and the picker both ask it, so they cannot disagree."""
    ol = (owner or "").strip().lower()
    tl = _norm_title(title)
    if _is_d2r_game_owner(ol):
        return "local"
    has_game = bool(_GAME_RX.search(tl))
    if any(w in ol for w in ("crossover", "wine", "cxstart", "cxpatcher")) and has_game:
        return "crossover"
    # ⚠ a browser is its NAME, whole: prefix matching made "Archive Utility" an Arc tab and
    # "Operational Log" an Opera tab (second eye on v3496, reproduced).
    browser = any(ol == b or ol.startswith(b + " ") for b in _BROWSER_OWNERS)
    full, near = [], []
    for route, owners, markers in _CLOUD_ROUTES:
        native = any(o in ol for o in owners)
        tab = browser and any(m in tl for m in markers)
        if native or tab:
            bare = native and not browser and tl in _NATIVE_BARE_TITLES.get(route, ())
            (full if (has_game or bare) else near).append(route)
    if len(full) == 1:
        return full[0]
    if len(full) > 1:
        # a title naming TWO services (a Boosteroid tab mentioning GeForce NOW, a comparison page)
        # cannot say which one is streaming: reported, never pinned as the first one listed
        return "near:ambiguous"
    if near:
        return "near:%s" % near[0]
    return None


# ⚠ The pin above is not a content check. Boosteroid's own app titles the stream AND the launcher
# with nothing but "Boosteroid" (measured 2026-09-27), so both pin. A shadow reel may treat that
# window as the game only when the FIRST reads show a D2R HUD word — a zone name the top-right
# block prints, the same names _AREA_ACT already trusts. Fewer than a full first window, or no
# reads at all, is UNKNOWN: a loading frame has no zone yet, and an unread window is not the launcher.
_FIRST_HUD_READS = 3
# A journal also carries kai / intake / skip rows. Those are not the eye's reads, and on a real
# session they are the FIRST rows. Counting them filled the window with empty area and called a
# live game the launcher (measured on tv/sessions.jsonl: scenes kai and intake, area empty).
_HUD_SCENES = ("town", "stash", "inventory", "loot", "gameplay", "transition", "chronicle")
#: #148 — THE READER'S OWN TEMPLATES. A read the reader filed under one of D2R's own panels - the stash, the inventory,
#: the Chronicle, loot on the ground, a town - IS the game, zone name or not: his stash and inventory print no zone.
#: MEASURED on his Mac, 2026-10-01 20:00-20:10: four Boosteroid reels were sealed as "the launcher" within 23 s-2 min on
#: first reads the reader itself had filed as stash / inventory / loot, naming Horadric Cube, Nokozan Relic, Storm
#: Scarab and Thul Rune. "gameplay" and "transition" are the reader's fallbacks (a failed read is journalled as
#: gameplay - REG-1603), so they prove nothing by themselves. ONE vocabulary: these are the words
#: reel_segments._ACTIVITY_LANE keys on, and a law holds the two equal. [[copy-drift]]
_GAME_PANEL_SCENES = tuple(s for s in _HUD_SCENES if s not in ("gameplay", "transition"))
#: REG-1711 — the confidence a "gameplay" read with nothing to name must carry to count as the game (his live session at
#: 10:42 was read at 0.85; a fallback row carries None and never counts)
_GAMEPLAY_CONF_MIN = 0.7
#: #148 — items every character carries. A read naming one is the game even though no roster lists a base item.
_D2R_ALWAYS_ITEMS = frozenset(("horadric cube", "tome of town portal", "tome of identify", "scroll of town portal",
                               "scroll of identify"))


def label_is_bare_boosteroid(label):
    """True when a pinned label names only Boosteroid. A title that also names the game is not bare."""
    parts = [p for p in _norm_title(label).replace("·", " ").replace(":", " ").split() if p]
    return bool(parts) and all(p == "boosteroid" for p in parts)


def label_is_bare_cloud(label):
    """#147 — True when a pinned label names ONE cloud service and nothing else (its app window carries no game words),
    for every route in _NATIVE_BARE_TITLES: "Boosteroid · Boosteroid", "GeForce NOW · GeForce NOW". Such a window may be
    the stream or the service's launcher, so the first reads must show a D2R HUD word before a shadow reel calls it the
    game - the same rule Boosteroid's window was measured into, now for every service on every PC."""
    segs = [s.strip() for s in _norm_title(label).replace(":", " ").split("·")]
    segs = [" ".join(s.split()) for s in segs if s.strip()]
    if not segs:
        return False
    for route, names in _NATIVE_BARE_TITLES.items():
        if all(s in names or s == route for s in segs):
            return True
    return False


def _first_line(text):
    """The first non-empty line of a reader's words, trimmed - '' when there is none."""
    for ln in str(text or "").splitlines():
        if ln.strip():
            return ln.strip()[:200]
    return ""


def _is_content_read(row):
    """A vision read of the frame, not a skip, a kai row, or an intake row.

    Strings count. A dict counts only when its scene is one the HUD reader emits - AND a reader actually
    read it. REG-1603, MEASURED 2026-09-30 on his ALT: Claude was signed out ("Failed to authenticate: OAuth
    session expired"), every read failed and was journalled as the fallback row - scene "gameplay", mode
    "empty", nothing in it - and a black loading frame the local lane labels "transition" sat between them.
    Three of those read as "the Boosteroid launcher, not the game", so every shadow reel was sealed after a
    few minutes and the next opened 120 s later: a day of 2-4-min reels with 2-min holes. A read that did not
    happen is UNKNOWN, never a look that saw no HUD. [[unknown-stays-unknown]]
    """
    if isinstance(row, str):
        return bool(row.strip())
    if not isinstance(row, dict) or row.get("kind") == "skip":
        return False
    if row.get("readFailed") or row.get("mode") in ("empty", "near-black"):
        return False
    return str(row.get("scene") or "") in _HUD_SCENES


def _read_blob(row):
    if isinstance(row, str):
        return row
    if not isinstance(row, dict):
        return ""
    parts = [str(row.get("area") or "")]
    for key in ("names", "raw_lines", "tz"):
        val = row.get(key) or []
        if isinstance(val, str):
            parts.append(val)
        else:
            parts.extend(str(x) for x in val)
    return " ".join(parts)


def text_has_d2r_hud_word(text, words):
    """A HUD word is a known zone, whole, on both sides. 'pit' is not inside 'capital'."""
    hay = " " + _norm_title(text) + " "
    if not hay.strip():
        return False
    for w in words or ():
        needle = _norm_title(w)
        if needle and (" " + needle + " ") in hay:
            return True
    return False


def read_shows_the_game(row, words=None, items=None):
    """#148 — WHAT, in one content read, shows the game. -> a short reason, or "" when nothing does.

    A zone the HUD prints (`words`), a D2R panel the reader filed the read under (_GAME_PANEL_SCENES), or an item D2R
    has: the always-carried bases, a rune, or any name in `items` (folded, lower-case). Not a content read -> "".
    The reason is what the judge was FED, so a seal row can say why the session was the game - or why it was not."""
    if not _is_content_read(row):
        return ""
    if isinstance(row, str):
        return "a zone name" if (words and text_has_d2r_hud_word(row, words)) else ""
    if words and text_has_d2r_hud_word(_read_blob(row), words):
        return "the zone %s" % (str(row.get("area") or "").strip()[:40] or "named in the read")
    sc = str(row.get("scene") or "")
    if sc in _GAME_PANEL_SCENES:
        return "a read filed as the %s" % sc
    for n in row.get("names") or ():
        k = " ".join(str(n or "").lower().split())
        if not k:
            continue
        if k in _D2R_ALWAYS_ITEMS or (items and k in items) or (k.endswith(" rune") and len(k.split()) == 2):
            return "the item %s" % str(n).strip()[:40]
    # REG-1711 — A REAL READ OF A GAME SCENE WITH NOTHING ON IT TO NAME IS THE GAME. His ALT, 2026-10-02 10:42 and 10:50:
    # the reader filed every read of two reels as "gameplay" (conf 0.85) - the frame was the Rogue Encampment, Deckard
    # Cain, both orbs and the belt - with no zone on screen and nothing to name, and the judge sealed his live session as
    # "the launcher" twice in eight minutes. Over three days of his ALT's seals the launcher itself was read as
    # "transition" (39 of the 39 that recorded what they were fed), and the laws' launcher reads name its own words
    # (Play, Library, Boosteroid). So "gameplay" counts only when the reader REALLY read it - its own confidence, which no
    # fallback row carries (they say conf None) - and named nothing that is not the game. [[unknown-stays-unknown]]
    _c = row.get("conf")
    if (sc == "gameplay" and not (row.get("names") or []) and not str(row.get("area") or "").strip()
            and isinstance(_c, (int, float)) and not isinstance(_c, bool) and _c >= _GAMEPLAY_CONF_MIN
            and _the_reader_said_it(row)):
        return "a read filed as gameplay with nothing else to name (conf %.2f)" % float(_c)
    return ""


def _the_reader_said_it(row):
    """REG-1716 — DID THE READER SAY THIS SCENE, THESE NAMES AND THIS CONFIDENCE, OR DID THE PARSE MAKE THEM? -> bool

    The v3555 eye, reproduced the same hour: _parse_read clamps any scene it does not know (null, "menu", "transition "
    with a space) to "gameplay", replaces names that are not a list (a launcher word sent as a string) with [], and so
    builds exactly the bare, confident gameplay row REG-1711 counts as the game - {"names":"Play","scene":null,
    "conf":true} came out as gameplay, no names, conf 1.0, and the judge said "the game". The parse already writes
    every clamp and drop into its audit, and the journal row carries it as `parse`; this asks it. A row with no audit
    cannot show the words were the reader's own, so it does not count (his five real rows on the Mac carry
    {"ok": true, "normalized": [], "dropped": []}). [[unknown-stays-unknown]]"""
    p = row.get("parse") if isinstance(row, dict) else None
    if not isinstance(p, dict) or p.get("ok") is not True:
        return False
    for _fix in list(p.get("normalized") or ()) + list(p.get("dropped") or ()):
        if isinstance(_fix, dict) and _fix.get("field") in ("scene", "names", "conf"):
            return False
    return True


def reads_show_the_game(reads, words=None, items=None):
    """#148 — HIS RULE, 2026-10-01: "regardless it needs to know if im in a session even if i alt tabbed... thats still a
    session for until 3 minutes goes by". -> True | False | None over EVERY content read given.

    True  — any read shows the game (read_shows_the_game).
    False — at least _FIRST_HUD_READS content reads, and none shows it.
    None  — fewer reads than that and none showing it, or nothing to judge with: UNKNOWN, never the launcher."""
    if not isinstance(reads, (list, tuple)) or not words:
        return None
    n = 0
    for row in reads:
        if not _is_content_read(row):
            continue
        n += 1
        if read_shows_the_game(row, words, items):
            return True
    return False if n >= _FIRST_HUD_READS else None


def first_reads_show_d2r_hud(reads, words=None, items=None):
    """-> True | False | None for the first _FIRST_HUD_READS content rows.

    True  — one of them shows the game: a zone word, a D2R panel the reader filed it under, or a D2R item (#148).
    False — that window is full and none do (the launcher).
    None  — no reads, not a list, no words to judge with, or the window is not full yet.
    """
    if not isinstance(reads, (list, tuple)):
        return None
    if not words:
        return None
    taken = []
    for row in reads:
        if not _is_content_read(row):
            continue
        taken.append(row)
        if len(taken) >= _FIRST_HUD_READS:
            break
    if not taken:
        return None
    for row in taken:
        if read_shows_the_game(row, words, items):
            return True
    if len(taken) >= _FIRST_HUD_READS:
        return False
    return None


def read_evidence(reads, limit=_FIRST_HUD_READS):
    """#148 — what the judge was FED, one short line per content read (scene · zone · first names), for the seal row."""
    out = []
    for row in reads or ():
        if not _is_content_read(row) or not isinstance(row, dict):
            continue
        names = [str(n).strip()[:28] for n in (row.get("names") or ()) if str(n or "").strip()][:3]
        out.append("%s%s%s" % (str(row.get("scene") or "?"),
                               (" · " + str(row.get("area")).strip()[:28]) if str(row.get("area") or "").strip() else "",
                               (" · " + ", ".join(names)) if names else ""))
        if len(out) >= limit:
            break
    return out


def _match_tokens():
    extra = [t.strip().lower() for t in (os.environ.get("TV_WINDOW_MATCH") or "").split(",") if t.strip()]
    return list(_D2R_TITLE_HINTS) + list(_D2R_OWNER_HINTS) + extra


def _is_d2r_game_owner(owner_l):
    """True when the process is the real game binary (CrossOver-hosted D2R.exe)."""
    ol = (owner_l or "").strip().lower()
    if not ol:
        return False
    if ol == "d2r.exe" or ol.endswith("/d2r.exe") or ol.endswith("\\d2r.exe"):
        return True
    if ol.endswith(".exe") and ("d2r" in ol or "diablo ii" in ol or "diabloii" in ol):
        return True
    return False


def _is_launcher_shell(owner_l, title_l):
    """v843 — CrossOver Home / Battle.net lobby / thin chrome — NEVER the eye."""
    ol, tl = (owner_l or "").lower(), (title_l or "").lower()
    if ol in ("crossover", "cross over") or ol.startswith("crossover"):
        return True
    if "battle.net" in ol or ol in ("battle.net.exe", "battle net"):
        return True
    if tl in _PICK_LAUNCHER_TITLES:
        return True
    if tl in ("home", "crossover", "battle.net"):
        return True
    return False


def score_d2r_window_candidate(owner, title, width, height, onscreen=True):
    """v843 — pure scorer for unit tests + find_d2r_window_mac.
    Returns int score, or None if this window must never be pinned.
    Absolute winner: D2R.exe with a Diablo/Resurrected title and game-sized bounds."""
    ol = (owner or "").strip().lower()
    # ⚠ NORMALIZED ONCE, FIRST (second eye on v3496): the store marks were only stripped on the cloud
    # branch, so a CrossOver window titled "Diablo® II" read as not-the-game here while game_route
    # called it crossover - two answers from one module about one window.
    tl = _norm_title(title)
    ww, hh = int(width or 0), int(height or 0)
    if ww < 640 or hh < 480:
        return None
    if ol == "python" and "tv diablo" in tl:
        return None
    # v852 (Grok R17 (b) — browsers re-entered the pin race): the game-title override applies
    # ONLY to wine-family owners; Chrome/Safari/editors stay hard-dead no matter the title.
    # ⚠ #232 — NARROWED BY HIS ORDER, NOT REPEALED: a browser is still dead on a game TITLE alone
    # (the guide tab R17 caught). It lives only as a GeForce NOW / Boosteroid tab carrying BOTH the
    # service's name and the game's — decided by game_route(), never by a title hint here.
    _wine_owner = any(w in ol for w in ("crossover", "wine", "cxstart", "cxpatcher"))
    _title_is_game = (("resurrected" in tl or "diablo ii" in tl or tl == "d2r")
                      and ww >= 800 and hh >= 500 and _wine_owner)
    _route = game_route(owner, title)
    _cloud = _route in ("geforce-now", "boosteroid")
    if any(b in ol for b in _PICK_OWNER_BLOCK) and not _is_d2r_game_owner(ol):
        # block list includes crossover/battle.net — game exe still allowed
        # v849 — and an unambiguous game TITLE at game size passes even under a wine/CrossOver owner
        if not (_title_is_game or _cloud):
            return None
    # the title block applies to a streamed window too: "battle.net" or "localhost" in a cloud title is
    # the launcher or our own page, never the game (it used to be bypassed for any cloud route)
    if any(b in tl for b in _PICK_TITLE_BLOCK) and not _is_d2r_game_owner(ol):
        return None
    if _is_launcher_shell(ol, tl) and not _is_d2r_game_owner(ol):
        # v849 (audit-core #4) — an unambiguous GAME TITLE on a game-sized window overrides
        # the shell reject: Quartz sometimes reports the game's owner as CrossOver/wine.
        if not _title_is_game:
            return None
    # Must be the game process OR a clear Diablo game title (never lobby alone)
    is_game = _is_d2r_game_owner(ol)
    title_game = ("diablo" in tl or "resurrected" in tl or tl == "d2r"
                  or any(t in tl for t in _D2R_TITLE_HINTS))
    if not is_game and not title_game and not _cloud:
        # ⚠ `_cloud` because game_route already judged it: a routed stream IS the game even when the
        # service's own app names only itself (Boosteroid, measured 2026-09-27)
        return None
    # ⚠⚠ #223 — A TITLE IS NOT AN OWNER. MEASURED 2026-09-24: with no game open, the eye pinned a
    # FINDER window titled "tv-diablo-mailbox" as the game (score 1602 — `"diablo" in title` was
    # the whole qualification), and a stub console filmed it. Finder "d2r notes" and Preview
    # "diablo map.png" scored the same. A window whose TITLE merely mentions the game is not the
    # game unless its OWNER is: the game binary, a wine/CrossOver host, a process named for
    # d2r/diablo, or an owner he named in TV_WINDOW_MATCH. Recording the wrong window is footage
    # of his desktop, not of his run.
    _named = [t.strip().lower() for t in (os.environ.get("TV_WINDOW_MATCH") or "").split(",") if t.strip()]
    owner_ok = (is_game or _wine_owner or _cloud or "d2r" in ol or "diablo" in ol
                or any(t in ol for t in _named))
    if not owner_ok:
        return None
    # Title-only without game owner: reject if it still looks like a shell —
    # v849: UNLESS the title is unambiguously the game at game size (wine-owner case)
    if not is_game and _is_launcher_shell(ol, tl) and not _title_is_game:
        return None
    score = 0
    if is_game:
        score += 10000          # absolute — always beats CrossOver/Battle.net/Chrome
    if "d2r.exe" in ol:
        score += 2000
    if title_game:
        score += 1500
    if "diablo ii: resurrected" in tl or "diablo ii resurrected" in tl:
        score += 500
    if any(t in ol for t in _D2R_OWNER_PRIORITY):
        score += 30
    if onscreen:
        score += 40
    area = ww * hh
    score += min(area // 100000, 20)
    # Prefer taller gameplay view over thin bars that slip past min height
    if hh >= 700:
        score += 50
    return score


def _pick_game_window(rows):
    """ONE judge for every platform's window list. rows: [{owner, title, w, h, onscreen, wid}]
    -> (best (score, area, wid, label) | None, near [str]). Pure; the Mac and Windows finders only
    differ in how they LIST windows, never in which one is the game. [[copy-drift]]"""
    best = None  # (score, area, wid, label)
    near = []    # #232 — service windows that do not name the game: reported, never pinned
    for r in rows:
        try:
            owner, title = r.get("owner") or "", r.get("title") or ""
            ww, hh = int(r.get("w") or 0), int(r.get("h") or 0)
            sc = score_d2r_window_candidate(owner, title, ww, hh, onscreen=bool(r.get("onscreen")))
            if sc is None:
                _nr = game_route(owner, title)
                if isinstance(_nr, str) and _nr.startswith("near:"):
                    near.append("%s %s '%s'" % (_nr[5:], owner, title[:60]))
                elif _nr in ("geforce-now", "boosteroid"):
                    # ⚠ a cloud window NAMING the game that the scorer refused (size, offscreen, a
                    # blocked phrase) was dropped with the generic why - reported now, never pinned
                    near.append("%s %s '%s' (names the game but is not pinnable: %dx%d%s)"
                                % (_nr, owner, title[:60], ww, hh,
                                   "" if r.get("onscreen") else ", offscreen"))
                continue
            wid = r.get("wid")
            if not wid:
                continue
            area = ww * hh
            label = f"{owner}" + (f" · {title}" if title else "")
            _rt = game_route(owner, title)
            if _rt in ("geforce-now", "boosteroid"):
                label = ("GeForce NOW" if _rt == "geforce-now" else "Boosteroid") + " · " + label
            cand = (sc, area, int(wid), label[:80])
            if best is None or cand > best:
                best = cand
        except Exception:
            continue
    return best, near


def _note_pick_route(rows, best):
    """Record WHICH WAY the picked window is the game, from the row the judge chose. -> None

    ⚠ 2026-09-28 — PERSIST WHAT THE FINDER KNEW. game_route() already answers local / crossover /
    geforce-now / boosteroid for every row, and the pick kept only a display label, so no reader could
    ask "how does this machine film D2R" without re-parsing a label (a second decoder that would drift).
    local and crossover are both NATIVE play (D2R.exe on this machine); a row game_route() cannot
    place is "unknown", never a guess. [[heart-first]] §6 [[copy-drift]] [[unknown-stays-unknown]]

    The same row already measured the window label and the client size. Those ride with the route
    so the seal can copy them. A size of 0 is not a size."""
    global _PICK_ROUTE
    label = ""
    ww = hh = None
    try:
        wid = best[2]
        if len(best) > 3 and isinstance(best[3], str):
            label = best[3].strip()
        row = next((r for r in rows or [] if r.get("wid") is not None and int(r.get("wid")) == int(wid)), None)
        rt = game_route(row.get("owner"), row.get("title")) if row else None
        if row:
            ww = int(row.get("w") or 0)
            hh = int(row.get("h") or 0)
    except Exception:
        rt = None
        ww = hh = None
    rec = {"route": {"local": "native", "crossover": "native", "geforce-now": "geforce-now",
                     "boosteroid": "boosteroid"}.get(rt, "unknown"),
           "ts": int(time.time() * 1000)}
    if label:
        rec["windowLabel"] = label[:120]
    if ww and hh and ww > 0 and hh > 0:
        rec["w"] = ww
        rec["h"] = hh
    _PICK_ROUTE = rec


def _capture_for_seal():
    """The capture facts this process can honestly put on a reel it is sealing. -> dict | None

    The finder's last pin, then the Windows capture half's own file when that file names a
    window (it is the process that filmed). A waiting or missing file does not erase the pin.
    os is this process. dpi only when the file says the API returned it.
    """
    import capture_stamp as _cs
    measured = {}
    pr = _PICK_ROUTE if isinstance(_PICK_ROUTE, dict) else {}
    for k in ("route", "windowLabel", "w", "h"):
        if pr.get(k) not in (None, ""):
            measured[k] = pr.get(k)
    try:
        with open(os.path.join(FRAMES, "cap_target.json"), encoding="utf-8-sig") as fh:
            j = json.load(fh)
    except Exception:
        j = None
    if isinstance(j, dict) and str(j.get("mode") or "").lower() == "window":
        route = j.get("route")
        if route == "local":
            route = "native"
        if route in ("native", "geforce-now", "boosteroid", "unknown"):
            measured["route"] = route
        label = j.get("windowLabel")
        if isinstance(label, str) and label.strip():
            measured["windowLabel"] = label.strip()
        jw, jh = j.get("w"), j.get("h")
        if (isinstance(jw, int) and not isinstance(jw, bool) and isinstance(jh, int)
                and not isinstance(jh, bool) and jw > 0 and jh > 0):
            measured["w"] = jw
            measured["h"] = jh
        if j.get("dpiMeasured") is True and isinstance(j.get("dpi"), int) and not isinstance(j.get("dpi"), bool):
            measured["dpi"] = j["dpi"]
            measured["dpiMeasured"] = True
    measured["os"] = _cs.os_of_this_process()
    cap = _cs.from_measured(measured)
    return cap or None


def find_d2r_window_mac():
    """Return (window_id:int, label:str) for the best on-screen D2R game window, or None.
    Uses Quartz. Read-only. NEVER returns CrossOver Home or Battle.net shell.
    v783 — short TTL cache so capture doesn't re-scan every frame.
    v843 — score_d2r_window_candidate hard-prefers D2R.exe · Diablo II: Resurrected."""
    global _PICK_WHY, _PICK_CACHE, _PICK_UNKNOWN
    # #232 — his words: "linux cant open those they lock automatically". There is no game and no
    # cloud route to find on Linux, so say THAT instead of a Quartz import error.
    if sys.platform.startswith("linux"):
        _PICK_WHY = ("Linux: D2R and its cloud routes (GeForce NOW, Boosteroid) cannot run on this "
                     "machine - nothing to pin")
        return None
    now = time.monotonic()
    if _PICK_CACHE and (now - _PICK_CACHE[1]) < _PICK_TTL_S:
        return _PICK_CACHE[0]
    try:
        from Quartz import (
            CGWindowListCopyWindowInfo,
            kCGWindowListOptionAll,
            kCGNullWindowID,
        )
    except Exception as e:
        _PICK_WHY = "quartz-import: %s" % e
        _PICK_UNKNOWN = True                    # could not LOOK - never "no game" (second eye on v3520)
        return None
    try:
        # Fullscreen D2R can live on its own Space — list ALL spaces.
        wins = CGWindowListCopyWindowInfo(kCGWindowListOptionAll, kCGNullWindowID) or []
    except Exception as e:
        _PICK_WHY = "winlist: %s" % e
        _PICK_UNKNOWN = True
        return None
    if not wins:
        # the second eye on v3521: an EMPTY list is not a look either. A process with no window server behind it (an
        # agent context, no desktop session) answers [] - his GUI session always lists the menu bar and the dock - and
        # the Windows twin already reads 0 windows as "could not see". Not cached, so the next call looks again.
        _PICK_WHY = "the window list came back EMPTY - no desktop was visible to this process, so it says nothing about the game"
        _PICK_UNKNOWN = True
        return None
    _PICK_UNKNOWN = False                       # a real look: whatever it finds is a measurement
    rows = []
    for w in wins:
        try:
            # ⚠ v2351 — DO NOT SKIP ON LAYER. This used to be `if layer != 0: continue` with
            # the note "skip menus/overlays", and it meant the chooser could NEVER pin his game.
            # Measured 2026-08-31 while D2R was on screen and he was playing:
            #     owner=D2R.exe  title=Diablo II: Resurrected  1470x956  onscreen=True
            #     kCGWindowLayer = 26        <- skipped, every time
            # CrossOver puts the fullscreen game on layer 26; only ordinary windows sit at 0. The
            # LAYER was never the discriminator - the SCORER is. [[feedback-suspect-the-instrument]]
            b = w.get("kCGWindowBounds") or {}
            rows.append({"owner": (w.get("kCGWindowOwnerName") or "").strip(),
                         "title": (w.get("kCGWindowName") or "").strip(),
                         "w": int(b.get("Width") or 0), "h": int(b.get("Height") or 0),
                         "onscreen": bool(w.get("kCGWindowIsOnscreen")),
                         "wid": w.get("kCGWindowNumber")})
        except Exception:
            continue
    best, near = _pick_game_window(rows)
    if best:
        _note_pick_route(rows, best)
    if not best:
        _PICK_WHY = "no D2R.exe game window (CrossOver Home / Battle.net never pin)"
        if near:
            # UNMEASURED titles: the first real streamed session tells us what the service shows
            _PICK_WHY += ("; a cloud window is open and was NOT pinned (its title does not name the game, "
                          "names two services, or it is not a pinnable size): %s - if that IS the game, its "
                          "exact title is what the route must learn" % "; ".join(near[:3]))
        _PICK_CACHE = (None, now)
        return None
    hit = (best[2], best[3])
    _PICK_CACHE = (hit, now)
    return hit



def _win_process_names():
    """-> {pid: exe name} from one Toolhelp32 snapshot (never tasklist.exe - it hangs under D2R, v1414),
    or None when the snapshot could not be taken. Windows only."""
    try:
        import ctypes
        from ctypes import wintypes

        class PROCESSENTRY32W(ctypes.Structure):
            _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                        ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                        ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                        ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
                        ("dwFlags", wintypes.DWORD), ("szExeFile", wintypes.WCHAR * 260)]
        k32 = ctypes.windll.kernel32
        snap = k32.CreateToolhelp32Snapshot(0x00000002, 0)
        if snap == ctypes.c_void_p(-1).value or snap == -1:
            return None
        out = {}
        try:
            pe = PROCESSENTRY32W()
            pe.dwSize = ctypes.sizeof(PROCESSENTRY32W)
            ok = k32.Process32FirstW(snap, ctypes.byref(pe))
            while ok:
                out[int(pe.th32ProcessID)] = pe.szExeFile or ""
                ok = k32.Process32NextW(snap, ctypes.byref(pe))
        finally:
            k32.CloseHandle(snap)
        return out
    except Exception:
        return None


def _win_owner(exe):
    """A Windows exe name as the judge reads an owner: the game binary keeps its '.exe' (that is how
    _is_d2r_game_owner knows it), every other process drops it so 'chrome.exe' is the browser 'chrome'
    and 'Boosteroid.exe' is the service's own app."""
    e = (exe or "").strip()
    if _is_d2r_game_owner(e.lower()):
        return e
    return e[:-4] if e.lower().endswith(".exe") else e


def game_window_rows_win(win_rows, procs):
    """Pure: window_visibility's Win32 rows + {pid: exe} -> the rows _pick_game_window judges.
    A row whose pid has no process name keeps an EMPTY owner, never a guessed one."""
    rows = []
    for r in win_rows or []:
        try:
            b = r.get("kCGWindowBounds") or {}
            title = r.get("kCGWindowOwnerName") or ""          # window_visibility puts the TITLE here
            rows.append({"owner": _win_owner((procs or {}).get(int(r.get("kCGWindowOwnerPID", -1)), "")),
                         "title": "" if title == "(untitled)" else title,
                         "w": int(b.get("Width") or 0), "h": int(b.get("Height") or 0),
                         "onscreen": not r.get("iconic"), "wid": r.get("hwnd")})
        except Exception:
            continue
    return rows


def find_d2r_window_win(win=None, procs=None):
    """⚠⚠ 2026-09-27 — THE WINDOWS TWIN OF find_d2r_window_mac, FOR THE DOORS THAT DECIDE WHETHER TO ROLL.

    MEASURED over SSH on his ALT: shadow ON and "armed", the game on screen through Boosteroid, and its watcher
    wrote "Diablo is not on screen" every 20 s. capture_preflight asked find_d2r_window_mac(), which opens with
    `from Quartz import ...` - on Windows that import fails, the finder returns None, and None read as "no game".
    So the shadow reader could never roll a reel on ANY Windows PC, whatever was running. (The reel's own capture
    half, capture_win.ps1, has always had a Windows finder; the door in front of it never did.)

    Lists windows with window_visibility's Win32 walk (the one already proven on the ALT), names each owner from
    one process snapshot, and judges them with _pick_game_window - the same judge the Mac uses.
    -> (hwnd, label) | None, with _PICK_WHY saying why. `win` / `procs` are seams for the law.
    """
    global _PICK_WHY, _PICK_UNKNOWN
    # ⚠ UNKNOWN IS NOT "NO GAME" — set on every path that could not LOOK, cleared only by a real look.
    # MEASURED on the ALT: run from an SSH session this walk lists 0 windows (another session's desktop),
    # and "no game window among 0 listed" read exactly like a desktop with the game shut. A real desktop
    # always lists windows (the shell alone is several), so zero is blindness. [[unknown-stays-unknown]]
    _PICK_UNKNOWN = True
    if win is None:
        if not sys.platform.startswith("win"):
            _PICK_WHY = "find_d2r_window_win: not Windows"
            return None
        try:
            import window_visibility as _wv
            win = _wv._Win32()
        except Exception as e:
            _PICK_WHY = "win32-walk: %s" % e
            return None
    try:
        listed = list(win.rows() or [])
    except Exception as e:
        _PICK_WHY = "win32-walk: %s" % str(e)[:80]
        return None
    if procs is None:
        procs = _win_process_names()
        if procs is None:
            _PICK_WHY = "the process snapshot could not be taken, so no window has an owner"
            return None
    if not listed:
        _PICK_WHY = ("the window walk listed NO windows at all - this process cannot see a desktop (a service "
                     "or SSH session), so whether the game is on screen is UNKNOWN")
        return None
    _PICK_UNKNOWN = False
    _rows = game_window_rows_win(listed, procs)
    best, near = _pick_game_window(_rows)
    if best:
        _note_pick_route(_rows, best)
    if not best:
        _PICK_WHY = "no game window among %d listed (D2R.exe, GeForce NOW, Boosteroid)" % len(listed)
        if near:
            _PICK_WHY += ("; a cloud window is open and was NOT pinned (its title does not name the game, names "
                          "two services, or it is not a pinnable size): %s" % "; ".join(near[:3]))
        return None
    _PICK_WHY = ""
    return (best[2], best[3])

def screen_recording_ok():
    """v779 — macOS TCC: when Python is the responsible process (control→agent), Terminal's
    Screen Recording grant does NOT cover us. Preflight + request the system prompt."""
    if sys.platform != "darwin":
        return True
    try:
        from Quartz import CGPreflightScreenCaptureAccess, CGRequestScreenCaptureAccess
        if CGPreflightScreenCaptureAccess():
            return True
        # Shows the system dialog once; user must tick Python / TV DIABLO in Settings if denied.
        CGRequestScreenCaptureAccess()
        return bool(CGPreflightScreenCaptureAccess())
    except Exception:
        # Older macOS / no Quartz — fall through; screencapture will succeed or fail on its own.
        return True


def open_screen_recording_settings():
    """Deep-link System Settings → Privacy → Screen Recording (best-effort)."""
    if sys.platform != "darwin":
        return
    try:
        subprocess.Popen(
            ["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except Exception:
        try:
            subprocess.Popen(
                ["open", "x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension?Privacy_ScreenCapture"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass


def _cap_tmp(path):
    """Unique sibling temp path — never write onto the durable target first."""
    return "%s.tmp.%d.%s" % (path, os.getpid(), str(time.time_ns() if hasattr(time, "time_ns") else int(time.time() * 1000)))


def _cap_promote(tmp, path, min_bytes=10000):
    """v779 — THE STALE-FILE LIE: screencapture can exit 1 WITHOUT touching `path`, leaving a
    previous desktop BMP in place. Trusting `os.path.exists(path)` then claims window-pin success
    on last night's wallpaper. Capture into tmp; only promote when THIS call wrote real bytes."""
    try:
        if not (os.path.exists(tmp) and os.path.getsize(tmp) > min_bytes):
            return False
        os.replace(tmp, path)   # atomic on same volume
        return True
    except Exception:
        return False
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass


def _quartz_grab_screen(dest_path, uti="public.jpeg"):
    """v867 — full-screen grab via Quartz (no subprocess): ~50ms vs screencapture's ~300ms.
    The film loop's full-screen lane runs here first; screencapture stays as fallback."""
    try:
        from Quartz import (
            CGWindowListCreateImage, CGRectInfinite,
            kCGWindowListOptionOnScreenOnly, kCGWindowImageDefault, kCGNullWindowID,
            CGImageDestinationCreateWithURL, CGImageDestinationAddImage,
            CGImageDestinationFinalize, CGImageGetWidth,
            CFURLCreateFromFileSystemRepresentation,
        )
        import objc as _objc   # v868 (Grok h) — 15fps retina CGImages need a pool, not GC luck
        with _objc.autorelease_pool():
            return _quartz_finish_screen(dest_path, uti)
    except Exception:
        return False


def _quartz_finish_screen(dest_path, uti="public.jpeg"):
    try:
        from Quartz import (
            CGWindowListCreateImage, CGRectInfinite,
            kCGWindowListOptionOnScreenOnly, kCGWindowImageDefault, kCGNullWindowID,
            CGImageDestinationCreateWithURL, CGImageDestinationAddImage,
            CGImageDestinationFinalize, CGImageGetWidth,
            CFURLCreateFromFileSystemRepresentation,
        )
        img = CGWindowListCreateImage(
            CGRectInfinite, kCGWindowListOptionOnScreenOnly, kCGNullWindowID, kCGWindowImageDefault)
        if img is None or int(CGImageGetWidth(img) or 0) < 32:
            return False
        dest_path = os.path.abspath(dest_path)
        part = dest_path + ".part"
        try:
            if os.path.exists(part):
                os.remove(part)
        except Exception:
            pass
        bpath = part.encode("utf-8")
        url = CFURLCreateFromFileSystemRepresentation(None, bpath, len(bpath), False)
        if url is None:
            return False
        dest = CGImageDestinationCreateWithURL(url, uti, 1, None)
        if dest is None:
            return False
        CGImageDestinationAddImage(dest, img, None)
        if not CGImageDestinationFinalize(dest):
            return False
        if not (os.path.isfile(part) and os.path.getsize(part) > 4000):
            return False
        os.replace(part, dest_path)
        return True
    except Exception:
        return False


def _quartz_grab_window(wid, dest_path, uti="public.png"):
    """v844 — grab a single window via CGWindowListCreateImage. v868 — body under an
    autorelease pool: this is the 15fps lane; retina CGImages must not wait for GC."""
    if not wid:
        return False
    try:
        import objc as _objc
        with _objc.autorelease_pool():
            return _quartz_finish_window(wid, dest_path, uti)
    except Exception:
        return False


def _quartz_finish_window(wid, dest_path, uti="public.png"):
    try:
        from Quartz import (
            CGWindowListCreateImage, CGRectNull,
            kCGWindowListOptionIncludingWindow, kCGWindowImageDefault,
            CGImageDestinationCreateWithURL, CGImageDestinationAddImage,
            CGImageDestinationFinalize, CGImageGetWidth, CGImageGetHeight,
            CFURLCreateFromFileSystemRepresentation,
        )
        img = CGWindowListCreateImage(
            CGRectNull, kCGWindowListOptionIncludingWindow, int(wid), kCGWindowImageDefault)
        if img is None:
            return False
        w, h = int(CGImageGetWidth(img) or 0), int(CGImageGetHeight(img) or 0)
        if w < 32 or h < 32:
            return False
        dest_path = os.path.abspath(dest_path)
        parent = os.path.dirname(dest_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        # write atomically via .part then replace
        part = dest_path + ".part"
        try:
            if os.path.exists(part):
                os.remove(part)
        except Exception:
            pass
        bpath = part.encode("utf-8")
        url = CFURLCreateFromFileSystemRepresentation(None, bpath, len(bpath), False)
        if url is None:
            return False
        dest = CGImageDestinationCreateWithURL(url, uti, 1, None)
        if dest is None:
            return False
        CGImageDestinationAddImage(dest, img, None)
        if not CGImageDestinationFinalize(dest):
            return False
        if not (os.path.isfile(part) and os.path.getsize(part) > 4000):
            return False
        os.replace(part, dest_path)
        return True
    except Exception:
        try:
            part = dest_path + ".part"
            if os.path.exists(part):
                os.remove(part)
        except Exception:
            pass
        return False


def _screencapture_window(wid, tmp_path, fmt="bmp", timeout=2.0):
    """Try macOS screencapture -l. Short default timeout — CrossOver D2R.exe often hangs -l forever."""
    try:
        r = subprocess.run(
            ["screencapture", "-l", str(int(wid)), "-o", "-x", "-t", fmt, tmp_path],
            capture_output=True, timeout=timeout, **NICE_KW)
        return os.path.isfile(tmp_path) and os.path.getsize(tmp_path) > 10000
    except Exception:
        return False


def _capture_window_to_file(wid, path, timeout=12):
    """v898 — pin a window for the intelligence loop. The OUTPUT FORMAT IS THE DESTINATION'S
    EXTENSION: `.jpg` keeps what Quartz already produced, anything else is converted.

    Quartz FIRST (D2R.exe under CrossOver: ~0.2-0.8s). screencapture -l is last-resort with a
    short timeout — it hangs 5-12s on this surface and starved the live frame / NO EYE.

    ══ v2324 — THE CONVERSION WAS THE LAG, AND IT BOUGHT NOTHING ═══════════════════════════════
    Konyo, repeatedly: "its really laggy", "it was soo slow and laggy i couldnt evne move", "also
    thiss farewell i didnt move past 4-5 items".

    Quartz hands us a JPEG. This function then spawned `sips` to expand that JPEG into a BMP.
    MEASURED on a 2560x1600 frame with real texture:

        source JPEG (already in hand)      587 KB
        sips jpeg -> bmp    46 ms       12,000 KB      20x bigger
        keep the JPEG      1.3 ms          587 KB      no subprocess at all

    46 ms of subprocess and 12 MB of disk per frame, at ~2.5 fps, to produce a LOSSLESS COPY OF AN
    ALREADY-LOSSY JPEG. It cannot recover a single pixel the JPEG threw away, so the picture is
    bit-for-bit as good either way; the only difference is what it costs.

    ⚠ The BMP is still written when the destination asks for one — path 3 (screencapture) and any
    caller still naming a .bmp keep exactly today's behaviour. This changes what the format
    DEPENDS ON, not what any existing caller gets. [[label-outlived-referent]]"""
    tmp = _cap_tmp(path)
    keep_jpeg = str(path or "").lower().endswith((".jpg", ".jpeg"))
    try:
        # 1) Quartz JPEG (fast). Converted only if the destination is not itself a JPEG.
        qj = path + ".qz.jpg"
        if _quartz_grab_window(wid, qj, uti="public.jpeg"):
            if keep_jpeg:
                # no subprocess, no 20x inflation — the bytes we want are already on disk
                try:
                    os.replace(qj, tmp)
                except Exception:
                    pass
            else:
                try:
                    subprocess.run(
                        ["sips", "-s", "format", "bmp", qj, "--out", tmp],
                        capture_output=True, timeout=min(8, max(3, timeout)), **NICE_KW)
                except Exception:
                    pass
            try:
                if os.path.exists(qj):
                    os.remove(qj)
            except Exception:
                pass
            if _cap_promote(tmp, path, min_bytes=8000):
                return True
        # 2) Quartz PNG (heavier, still better than hung screencapture). Converted to whatever
        #    the destination asks for — including JPEG, which is the cheap direction.
        png = path + ".qz.png"
        if _quartz_grab_window(wid, png, uti="public.png"):
            try:
                subprocess.run(
                    ["sips", "-s", "format", "jpeg" if keep_jpeg else "bmp", png, "--out", tmp],
                    capture_output=True, timeout=min(8, max(3, timeout)), **NICE_KW)
            except Exception:
                pass
            try:
                if os.path.exists(png):
                    os.remove(png)
            except Exception:
                pass
            if _cap_promote(tmp, path, min_bytes=8000):
                return True
        # 3) screencapture -l last, hard-capped (never block the poll loop)
        sc_t = min(2.0, float(timeout) if timeout else 2.0)
        if _screencapture_window(wid, tmp, fmt=("jpg" if keep_jpeg else "bmp"), timeout=sc_t):
            if _cap_promote(tmp, path):
                return True
        return False
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass


_EYE_PREVIEW_AT = 0.0
_FILM_THREAD = None
_PICK_CACHE = None   # (hit, monotonic_t) — avoid Quartz every frame
_PICK_TTL_S = 0.55   # v846 — re-pin faster when windows flip

def _sips_pixel_size(src):
    """Return (w, h) from sips, or (0, 0) on failure. Used to avoid upsample."""
    try:
        r = subprocess.run(
            ["sips", "-g", "pixelWidth", "-g", "pixelHeight", src],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5, **NICE_KW)
        w = h = 0
        for line in (r.stdout or "").splitlines():
            if "pixelWidth:" in line:
                try: w = int(line.split(":")[-1].strip())
                except Exception: pass
            elif "pixelHeight:" in line:
                try: h = int(line.split(":")[-1].strip())
                except Exception: pass
        return w, h
    except Exception:
        return 0, 0


def _sips_hd_jpeg(src, dest, max_px=None, quality=None, timeout=6):
    """HD+ JPEG for film stage. Default 2560px / q82 (4K-class polish, still WebView-friendly).

    v1450 — only pass --resampleHeightWidthMax when the source is LARGER than max_px.
    On current macOS, sips *upsamples* small images to that max (48×48 → 2560×2560),
    which bloated hist frames and broke the 'JPEG smaller than BMP' archive invariant."""
    max_px = FILM_MAX_PX if max_px is None else max_px
    quality = FILM_JPEG_Q if quality is None else quality
    try:
        cmd = ["sips", "-s", "format", "jpeg", "-s", "formatOptions", str(quality)]
        w, h = _sips_pixel_size(src)
        if max_px and w and h and max(w, h) > int(max_px):
            cmd += ["--resampleHeightWidthMax", str(int(max_px))]
        cmd += [src, "--out", dest]
        r = subprocess.run(cmd, capture_output=True, timeout=timeout, **NICE_KW)
        return r.returncode == 0 and os.path.isfile(dest) and os.path.getsize(dest) > 4000
    except Exception:
        return False


def _is_white_backing(path, size_ceiling=300_000):
    """v944 (Konyo live 'FOOTAGE STARVE — 0.2fps'): the Metal fullscreen surface hands
    Quartz a BLANK WHITE backing that still 'succeeds' (v930.3). The old guard rejected
    EVERY window grab under 150KB — but a legit DARK stash / loading frame ALSO compresses
    small, so his stash-heavy session starved: real dark frames were rejected -> demote ->
    the slow screencapture fallback cascade (2s+5s timeouts) -> ~0.45fps of full-screen frames.

    Smarter blank test: a grab is the artifact ONLY when it is near-uniform AND bright.
      · Legit game frame  -> UI/text/icons -> WIDE pixel spread          -> KEEP
      · Legit dark stash  -> orbs/belt/items on a dark field -> spread    -> KEEP
      · Legit black screen (loading/transition) -> near-uniform but DARK  -> KEEP
      · Metal white backing (mean~255, spread~0)                          -> REJECT
    Proven: 0 false-positives across 1736 real archived frames; the known ~93577-byte white
    class (mean~255, spread~0) still fails. Keeps the real-pixels law (REG-033) intact."""
    try:
        if os.path.getsize(path) > size_ceiling:
            return False   # real game frames run ~300KB-1.9MB; never the ~93KB white artifact
    except Exception:
        return True        # unreadable grab == unusable, treat as failure
    try:
        from PIL import Image, ImageStat
        with Image.open(path) as im:
            im.draft("L", (64, 64))       # fast partial decode (~11ms even on a 1.9MB retina jpg)
            g = im.convert("L")
            g.thumbnail((48, 48))
            lo, hi = g.getextrema()
            if (hi - lo) >= 24:           # wide spread -> real pixels, keep
                return False
            return ImageStat.Stat(g).mean[0] > 230   # near-uniform AND bright = white Metal backing
    except Exception:
        # PIL unavailable/corrupt: fall back to the pre-v944 size law so the white class is
        # still rejected (no worse than before) rather than the loop trusting a blank frame.
        try:
            return os.path.getsize(path) < 150_000
        except Exception:
            return True


def refresh_eye_preview(bmp_path, min_interval=0.12):
    """v779/v846 — fallback eye from intelligence frame (film thread is primary). HD."""
    global _EYE_PREVIEW_AT
    now = time.time()
    if now - _EYE_PREVIEW_AT < min_interval:
        return
    if not bmp_path or not os.path.isfile(bmp_path):
        return
    try:
        eye = os.path.join(FRAMES, "eye.jpg")
        if _sips_hd_jpeg(bmp_path, eye):
            _EYE_PREVIEW_AT = now
            _FILM_TIMES.append(now)
    except Exception:
        pass


_FOOT_TIMES = deque(maxlen=60)   # v871 — archive timestamps (footage fps without dir scans)


def _foot_fps_now():
    """v871 — archived-footage fps over the last 10s (None until 2 archives)."""
    now = time.time()
    recent = [t for t in _FOOT_TIMES if now - t <= 10.0]
    if len(recent) < 2:
        return None
    return round(len(recent) / 10.0, 2)


# v2063 — how many frames to keep after the D2R window disappears. The window vanishing IS the
# event worth filming (a crash, an alt-tab, a Space transition), so recording stops a few frames
# late rather than instantly. Small enough that a closed game costs kilobytes, not gigabytes.
NOGAME_TAIL_FRAMES = int(os.environ.get("TV_NOGAME_TAIL", "6") or 6)


def _archive_footage_copy(src_path, now_f, why="ok", _consume_due=True):
    """v947 — 1fps archive helper. Always advances the due clock; never blocks on sips.

    v1190 — promote-via-tmp: this was the one archive writer in the file that skipped the
    _cap_promote law every window/screen grab already follows ('write tmp, only promote when
    THIS call wrote real bytes' — see _cap_promote's own docstring on 'the stale-file lie').
    A copyfile() interrupted partway (ENOSPC, a kill, disk yanked) used to leave a truncated
    fragment sitting under the FINAL f_<ms>.jpg name — worse than a dropped frame, since nothing
    downstream re-checks size before treating a file at that name as a real archived frame; it
    silently pollutes the film reel forever. Now: copy to a private tmp, verify real bytes,
    os.replace (atomic on the same volume) into the final name — same law, same pattern as
    _cap_promote. Applied to the eye.last.jpg starve-bridge source too, since a corrupt bridge
    source would re-propagate into every later 'bridge-last-good' frame until film recovers.

    v1195 — _consume_due=False: the film loop's never-starve path can call this TWICE for the
    SAME now_f in one tick — a fresh grab first, then a bridge-last-good fallback if that fresh
    write fails (disk pressure, a torn copy). Both calls used to run the full due-gate: the
    first one (whether it went on to succeed or fail) already advanced _FOOTAGE_DUE past now_f,
    so the second call's OWN due-gate check (`now_f < _due`) then always rejected it before it
    could even try — the exact fallback this file's anti-starve law exists for was silently
    dead code whenever the primary write failed for a reason unrelated to frame content. The
    caller now owns the due-gate/advance for that one shared now_f slot and passes
    _consume_due=False to both attempts, so whichever one actually has bytes to write gets to."""
    try:
        if _consume_due:
            _iv = FOOTAGE_INTERVAL_S
            _due = globals().get("_FOOTAGE_DUE", 0.0)
            if now_f < _due:
                return False
            globals()["_FOOTAGE_DUE"] = max(_due + _iv, now_f - (_iv - 0.01)) if _due else now_f + _iv
        globals()["_FOOTAGE_AT"] = now_f
        globals()["_FOOTAGE_WHY"] = why
        if not src_path or not os.path.isfile(src_path) or os.path.getsize(src_path) < 4000:
            globals()["_FOOTAGE_REJECTS"] = int(globals().get("_FOOTAGE_REJECTS") or 0) + 1
            return False
        # ── v2063 — DO NOT RECORD A GAME THAT IS NOT RUNNING ────────────────────────────────────
        # Konyo: "the shadow reader when toggled on, it needs to know when diablo ii window is open
        # so it doesnt just record for free ... so it doesnt record for nothing".
        #
        # v899 built exactly this check and spent it on the wrong half. Its own comment says so:
        # "NO D2R WINDOW: film may keep running, but AI reads stay OFF". So the expensive lane was
        # protected and the DISK lane was not — with the game shut, frames kept landing at the full
        # rate, and the only thing that ever stopped them was MIN_FREE_GB, i.e. running out.
        #
        # THE TAIL IS DELIBERATE, and it is v1548's reasoning applied to the other end of a session.
        # v1548 refuses blank frames only during warm-up because "a blank frame LATER is not startup
        # noise, it is the game crashing or the window vanishing, and that is evidence worth keeping
        # rather than a fault to suppress". The same holds here: the first frames after the window
        # disappears are the most informative ones in the whole reel, so a short tail is archived and
        # only then does recording stop.
        #
        # Fail-OPEN by construction: _GAME_OK is unset until _set_game_gate has run, and an unset
        # gate reads True. A lane that has not measured yet must never be the reason footage is lost.
        # The gate it reads is already debounced (6s), so one flaky Quartz poll mid-play cannot stop
        # the film. [[feedback-silence-is-not-evidence]]
        if not (os.environ.get("TV_STUB") or os.environ.get("TV_NO_GAME_GUARD") == "0"):
            if globals().get("_GAME_OK", True):
                globals()["_NOGAME_TAIL_KEPT"] = 0
            else:
                _kept = int(globals().get("_NOGAME_TAIL_KEPT") or 0)
                if _kept < NOGAME_TAIL_FRAMES:
                    globals()["_NOGAME_TAIL_KEPT"] = _kept + 1
                    globals()["_FOOTAGE_WHY"] = ("no D2R window — keeping frame %d of %d as evidence "
                                                 "of what happened" % (_kept + 1, NOGAME_TAIL_FRAMES))
                else:
                    globals()["_NOGAME_SKIPPED"] = int(globals().get("_NOGAME_SKIPPED") or 0) + 1
                    globals()["_FOOTAGE_WHY"] = "no D2R window — not recording (%d frame(s) skipped)" % (
                        globals()["_NOGAME_SKIPPED"])
                    return False
        # ── v1548 — THE WARM-UP GATE ────────────────────────────────────────────────────────────
        # 16 of the 17 blank captures in his worst reel land in the FIRST NINETEEN SECONDS: capture
        # starts while D2R is still launching, so the window exists — the grab succeeds, the file is
        # a perfectly valid 2940x1912 JPEG well past the 4000-byte floor — and it is blank.
        #
        # v1543 stopped paying to classify them and v1545 marked them at seal. This stops making
        # them, which is the only one of the three that costs nothing at all.
        #
        # It gates ONLY the warm-up. Once one painted frame has landed the gate opens for the rest of
        # the session, permanently — a blank frame LATER is not startup noise, it is the game
        # crashing or the window vanishing, and that is evidence worth keeping rather than a fault to
        # suppress. Suppressing it would hide the very thing a watchdog exists to notice.
        if not globals().get("_FOOTAGE_WARM"):
            try:
                import chronicle_retro as _cr
                if _cr.is_dead_frame(src_path):
                    globals()["_FOOTAGE_WARMSKIP"] = int(globals().get("_FOOTAGE_WARMSKIP") or 0) + 1
                    globals()["_FOOTAGE_WHY"] = "warming-up (window not painted yet)"
                    return False
                globals()["_FOOTAGE_WARM"] = True
            except Exception:
                # cannot measure -> cannot refuse. An unmeasurable frame is archived, because
                # dropping what we could not judge is how real footage goes missing.
                globals()["_FOOTAGE_WARM"] = True
        hist_dir = HIST_DIR
        _establish_footage()
        import shutil as _sh
        if _disk_free_bytes(hist_dir) / 1e9 < MIN_FREE_GB:
            globals()["_FOOTAGE_WHY"] = "disk-full"
            return False
        dest = os.path.join(hist_dir, "f_%d.jpg" % int(now_f * 1000))
        tmp = _cap_tmp(dest)
        try:
            # ── v2320 — THE FILM IS DOWNSCALED, AND THE MEASUREMENT SAYS IT IS FREE ────────────
            # This was `_sh.copyfile(src_path, tmp)` — a RAW COPY of the full-resolution capture.
            # FILM_MAX_PX (1440) and FILM_JPEG_Q (72) have existed since v310 and this path never
            # applied either, so his reels landed at 2940x1912 / ~1,378 KB a frame: 147 MB for a
            # two-minute MINI, ~1.2 MB/s of disk while he plays. He reported it twice — "its
            # really laggy", "i didnt move past 4-5 items.. it was soo slow i couldnt even move".
            #
            # ⚠ I DID NOT SHRINK IT UNTIL IT WAS MEASURED, because the tooltip is the ONLY place an
            # item name appears. Measured on the frame that actually produced a read
            # (2_1788104655412.jpg, Crescent Moon), OCR of the same frame at six scales:
            #     2560px 1541KB  1920px 707KB  1440px 427KB  1280px 345KB  1024px 241KB  800px 143KB
            # and the local OCR returned 'I CkES<tNT rn••N' at EVERY one of them, including full
            # size. It is defeated by the D2R FONT, not by resolution, so the film's two consumers
            # — theatre playback and the local OCR — are both indifferent to this change.
            #
            # ⚠ AND IT IS SCOPED TO THE FILM ON PURPOSE. The PAID AI read is a different consumer
            # and `_readable_frame()` only downscales a .bmp (`if not ap.endswith(".bmp"): return
            # ap`), so a jpg reaches the model at full size. Whether the model still reads the name
            # smaller is UNMEASURED and costs a paid read to find out, so it is left alone here.
            # [[feedback-verify-not-proxy]] [[unknown-stays-unknown]]
            if not _film_shrink(src_path, tmp, FILM_MAX_PX, FILM_JPEG_Q):
                _sh.copyfile(src_path, tmp)     # never lose a frame to a failed re-encode
            if not (os.path.isfile(tmp) and os.path.getsize(tmp) >= 4000):
                raise IOError("short/failed footage copy — not promoting a fragment")
            os.replace(tmp, dest)   # dest only ever holds complete bytes, never a torn write
        finally:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:
                pass
        _FOOT_TIMES.append(now_f)
        # remember last GOOD archive source for starve-bridge — same tmp+promote law
        last = os.path.join(FRAMES, "eye.last.jpg")
        last_tmp = _cap_tmp(last)
        try:
            # #255 - a .bmp source (Windows' full frame) is not a jpeg: the last-good copy is the archived film frame
            _sh.copyfile(dest if str(src_path).lower().endswith(".bmp") else src_path, last_tmp)
            if os.path.isfile(last_tmp) and os.path.getsize(last_tmp) >= 4000:
                os.replace(last_tmp, last)
                globals()["_FILM_LAST_GOOD"] = last
            else:
                globals()["_FILM_LAST_GOOD"] = src_path
        except Exception:
            globals()["_FILM_LAST_GOOD"] = src_path
        finally:
            try:
                if os.path.exists(last_tmp):
                    os.remove(last_tmp)
            except Exception:
                pass
        return True
    except Exception:
        return False


def _grab_full_screen_frame(tmp):
    """v1181 — full-screen grab + the SAME white-Metal-backing guard the window lane already
    applies via _is_white_backing (v944). Without this, the full-screen lane could archive a
    blank frame as real film: it is invoked specifically WHEN the window lane just white-rejected
    (demoted for the next 5s), i.e. exactly the moment a Metal transition is most likely to hand
    the desktop compositor the same blank surface — the gap the window lane was built to close,
    left open one lane over. Returns True only when a real (non-blank) frame is sitting at tmp;
    on reject/failure the tmp file is cleaned up so callers can treat False uniformly."""
    wrote = _quartz_grab_screen(tmp, uti="public.jpeg")
    if not wrote:
        try:
            subprocess.run(
                ["screencapture", "-x", "-t", "jpg", tmp],
                capture_output=True, timeout=1.5, **NICE_KW)
            wrote = os.path.exists(tmp) and os.path.getsize(tmp) > 4000
        except Exception:
            wrote = False
    if wrote:
        try:
            if _is_white_backing(tmp):
                wrote = False
                globals()["_FILM_WHITE_REJECTS"] = int(globals().get("_FILM_WHITE_REJECTS") or 0) + 1
        except Exception:
            wrote = False
    if not wrote:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
    return wrote


def _capture_is_off():
    '''TV_CAPTURE=off|none: this console never reads the screen - not capture_mac, not the film thread,
    not any grabber (#236 + the second eye on 298de387).'''
    return (os.environ.get("TV_CAPTURE") or "").strip().lower() in ("off", "none")


def _stub_capture_only():
    '''#63 - A TV_STUB AGENT NEVER READS THE REAL SCREEN. -> True when this agent must synthesize its frames.

    MEASURED 2026-09-28: under TV_STUB the live loop tried the REAL capture_mac(frame) FIRST and fell
    back to capture_stub_synth only when that FAILED - so on his Mac, where Screen Recording is granted,
    a stub agent filmed and OCR'd whatever was on his screen, and a harness verdict depended on it.
    His words: "make sure nothing is running on my pc for nothing". Stub means synthetic frames now,
    on the live loop, the farewell look and the film thread alike; TV_STUB_REAL_CAPTURE=1 is the one
    explicit way back to the old behaviour (real capture first, synthetic on failure).
    Windows' screen is read by the capture half (capture_win.ps1), which control_app no longer starts
    for a stub agent; WATCH_MODE here still consumes FILES from TV_FRAMES_DIR, which is how replay.py
    feeds recorded truth to a stub agent, so that door is deliberately untouched.'''
    if (os.environ.get("TV_STUB_REAL_CAPTURE") or "").strip() == "1":
        return False
    return bool(os.environ.get("TV_STUB"))


def _may_ask_for_screen_recording():
    '''#63 follow-up - may this agent ask macOS for Screen Recording at all? -> bool

    screen_recording_ok() calls CGRequestScreenCaptureAccess (the system dialog when the grant is
    missing) and its caller then opens System Settings. A stub agent (#63) and a capture-off agent
    (#236) never read the screen, so they have nothing to ask for; the review of #63 found both still
    asking, at the boot preflight and again in the capture-fail branch, which is a dialog on a PC whose
    Python has no grant. Both sites ask this one predicate.'''
    return not _stub_capture_only() and not _capture_is_off()


def _boot_screen_recording_preflight(platform=None):
    '''v779 - ask for Screen Recording UP FRONT (Python-as-responsible needs its own grant; Terminal's
    checkbox does not cover the control-app child agent). -> True granted / False denied / None not asked

    Never asked by an agent that never reads the screen (_may_ask_for_screen_recording), nor off a Mac.
    `platform` is a test seam, so the refusal is a law on every OS and not only on his Mac.'''
    if WATCH_MODE or (sys.platform if platform is None else platform) != "darwin":
        return None
    if not _may_ask_for_screen_recording():
        ev("boot", "Screen Recording not asked - this agent never reads the screen (stub or TV_CAPTURE=off)")
        return None
    if screen_recording_ok():
        ev("boot", "Screen Recording OK — eye can pin the D2R window")
        return True
    ev("cap", "⚠ Screen Recording DENIED for this Python — open System Settings → Privacy → Screen Recording, enable Python / TV DIABLO, then RESTART")
    open_screen_recording_settings()
    print("  ⚠ Screen Recording not granted to this process — film will stay dark until you enable Python in System Settings → Privacy → Screen Recording")
    return False


def _film_loop():
    """v846/v947 TESLA DRIVE film — high-FPS HD JPEG of the pinned D2R window.
    Target TV_FILM_FPS (~5). Intelligence still uses BMP+frame_sig on the poll loop.
    Claude thinking never freezes this thread.

    v947 FOOTAGE STARVE fix (Konyo live 0.4fps):
      · white-backing reject → immediate full-screen Quartz (no 3-fail wait)
      · demote window lane 5s (was 15s)
      · never-starve screencapture timeout 1.5s (was 5s) — a long hang IS the starve
      · when grab fails but archive is DUE, bridge with last-good eye (better than a gap)
    """
    eye = os.path.join(FRAMES, "eye.jpg")
    tmp = eye + ".part.jpg"
    _lane_fail = 0
    _lane_full_until = 0.0
    while True:
        # v1199 — monotonic, not wall-clock: t0 only ever measures THIS iteration's own elapsed
        # time (capture duration + the cadence sleep below), never a stamp anyone else reads.
        # time.time() can jump BACKWARD (NTP correction, sleep/wake resync — routine on a Mac
        # left running for hours) — when it does, `dt = time.time() - t0` goes deeply negative
        # and `time.sleep(max(0.02, FILM_INTERVAL_S - dt))` turns into a sleep of however long
        # the clock jumped, freezing the film thread (0 real frames) for the whole gap. monotonic
        # never jumps backward, so cadence pacing can't be hijacked by a wall-clock correction.
        t0 = time.monotonic()
        try:
            if globals().get("_AI_PAUSED") and not WATCH_MODE:
                time.sleep(1.5)
                continue
            # ⚠ THE SECOND EYE ON 298de387 (grok-4.7): TV_CAPTURE=off stopped capture_mac ONLY. This thread
            # idled on "waiting" alone, so under capture-off (mode "off", no window id) every tick fell through
            # to the fullscreen fallback and - with D2R.exe running and Screen Recording granted - filmed the
            # whole display into the harness sandbox. Off means this console never reads the screen, in any
            # mode, WATCH_MODE included.
            if _capture_is_off() or (_CAP_TARGET or {}).get("mode") == "off":
                time.sleep(1.5)
                continue
            # #63 — and a stub agent (without TV_STUB_REAL_CAPTURE=1) never films the real screen either,
            # even with a window pinned. Its own statement, so the capture-off guard above keeps its shape.
            if _stub_capture_only():
                time.sleep(1.5)
                continue
            if not WATCH_MODE and (_CAP_TARGET or {}).get("mode") == "waiting":
                time.sleep(1.5)
                continue
            _establish_footage()
            wid = (_CAP_TARGET or {}).get("wid")
            if (_CAP_TARGET or {}).get("mode") == "waiting":
                wid = None
            if time.time() < _lane_full_until:
                wid = None
            wrote = False
            white_reject = False
            if wid:
                wrote = _quartz_grab_window(wid, tmp, uti="public.jpeg")
                if wrote:
                    try:
                        if _is_white_backing(tmp):
                            wrote = False
                            white_reject = True
                            globals()["_FILM_WHITE_REJECTS"] = int(globals().get("_FILM_WHITE_REJECTS") or 0) + 1
                    except Exception:
                        wrote = False
                if wrote:
                    _lane_fail = 0
                else:
                    _lane_fail += 1
                    # v947 — white Metal backing: skip doomed -l retries, go full-screen now
                    if white_reject or _lane_fail >= 2:
                        try:
                            r = subprocess.run(
                                ["screencapture", "-l", str(wid), "-o", "-x", "-t", "jpg", tmp],
                                capture_output=True, timeout=1.5, **NICE_KW)
                            wrote = os.path.exists(tmp) and os.path.getsize(tmp) > 4000
                            if wrote:
                                try:
                                    if _is_white_backing(tmp):
                                        wrote = False
                                        white_reject = True
                                except Exception:
                                    wrote = False
                        except Exception:
                            wrote = False
                        if wrote:
                            _lane_fail = 0
                    if not wrote:
                        # demote 5s (was 15) — recover window pin fast when surface returns
                        _need = 1 if (white_reject or globals().get("_LANE_DEMOTED_ONCE")) else 2
                        if _lane_fail >= _need:
                            _lane_full_until = time.time() + 5.0
                            _lane_fail = 0
                            globals()["_LANE_DEMOTED_ONCE"] = True
                            globals()["_FILM_LANE"] = "full(demoted)"
            if not wrote:
                # full-screen lane (demoted OR no wid OR white reject recovery)
                # v1251 — never wallpaper the film: full-screen only when D2R.exe is alive
                # and Screen Recording is granted (same law as capture_mac).
                if _allow_fullscreen_game_fallback("film"):
                    wrote = _grab_full_screen_frame(tmp)
                else:
                    wrote = False
            globals()["_FILM_LANE"] = (
                "window" if (wid and wrote and not white_reject and time.time() >= _lane_full_until)
                else ("full(demoted)" if time.time() < _lane_full_until else "full")
            )
            globals()["_FILM_CAP_MS"] = int((time.monotonic() - t0) * 1000)
            if wrote and os.path.exists(tmp) and os.path.getsize(tmp) > 4000:
                now_f = time.time()
                _archive_footage_copy(tmp, now_f, why="grab")
                # reap old film if disk tight
                try:
                    if now_f >= globals().get("_REAP_DUE", 0.0):
                        globals()["_REAP_DUE"] = now_f + 120.0
                        hist_dir = HIST_DIR
                        import shutil as _shu2
                        if _disk_free_bytes(hist_dir) / 1e9 < MIN_FREE_GB:
                            # 2026-09-28 — (b) it used to delete up to 600 loose frames here with NO evidence
                            # check; now it spares every read-bearing and every cited frame, refuses when the
                            # authority cannot answer, and records what it took. See _reap_loose_film.
                            _reap_loose_film(hist_dir)
                except Exception:
                    pass
                # Retina polish for live stage (after archive so SIM never starves)
                if os.path.getsize(tmp) > 450_000:
                    if _sips_hd_jpeg(tmp, eye):
                        try: os.remove(tmp)
                        except Exception: pass
                    else:
                        try: os.replace(tmp, eye)
                        except Exception: pass
                else:
                    try: os.replace(tmp, eye)
                    except Exception: pass
                globals()["_EYE_PREVIEW_AT"] = time.time()
                _FILM_TIMES.append(now_f)
            else:
                # v947 — never-starve: short timeouts + last-good bridge so FOOTAGE STARVE
                # never drops below ~1fps because a grab hung for 5s
                try:
                    now_f2 = time.time()
                    _due2 = globals().get("_FOOTAGE_DUE", 0.0)
                    if now_f2 >= _due2:
                        # v1195 — the due-gate/advance for this now_f2 slot is paid ONCE here,
                        # up front, so a fresh-grab attempt AND a bridge-last-good fallback can
                        # both try to fill it (_consume_due=False on both archive calls below);
                        # previously the first call's own internal advance silently locked the
                        # second one out of the very slot it was meant to rescue.
                        _iv2 = FOOTAGE_INTERVAL_S
                        globals()["_FOOTAGE_DUE"] = (
                            max(_due2 + _iv2, now_f2 - (_iv2 - 0.01)) if _due2 else now_f2 + _iv2)
                        got = False
                        # v1251 — never-starve must NOT wallpaper the reel with the desktop
                        if _allow_fullscreen_game_fallback("never-starve"):
                            if _grab_full_screen_frame(tmp):
                                got = _archive_footage_copy(tmp, now_f2, why="never-starve-full",
                                                            _consume_due=False)
                                try:
                                    os.replace(tmp, eye)
                                    globals()["_EYE_PREVIEW_AT"] = now_f2
                                except Exception:
                                    pass
                        if not got:
                            # bridge: re-archive last good game frame rather than a hole
                            last = globals().get("_FILM_LAST_GOOD") or (
                                eye if os.path.isfile(eye) else None)
                            if last and os.path.isfile(last):
                                bridged = _archive_footage_copy(last, now_f2, why="bridge-last-good",
                                                                _consume_due=False)
                                if bridged:
                                    globals()["_FOOTAGE_BRIDGES"] = int(globals().get("_FOOTAGE_BRIDGES") or 0) + 1
                except Exception:
                    pass
                try:
                    if os.path.exists(tmp):
                        os.remove(tmp)
                except Exception:
                    pass
        except Exception:
            pass
        dt = time.monotonic() - t0
        time.sleep(max(0.02, FILM_INTERVAL_S - dt))


def start_film_thread():
    global _FILM_THREAD
    if WATCH_MODE or sys.platform != "darwin":
        return
    # v925 LIGHT — the continuous full-screen recorder is the #1 lag; OFF by default. Every
    # actual READ still archives its own frame (per-read hist .jpg), so the SIM retro-debugger
    # keeps a screenshot of every read — just no smooth film between reads. TV_FILM=1 (or the
    # heavy TV_LIGHT=0 / robot mode) brings the cinematic film back for debugging.
    if str(os.environ.get("TV_FILM", "1") or "1").strip().lower() in ("0", "false", "no", "off"):   # v941 — film ON by default (same law as OCR)
        return
    if _FILM_THREAD and _FILM_THREAD.is_alive():
        return
    _FILM_THREAD = threading.Thread(target=_film_loop, daemon=True, name="tv-film")
    _FILM_THREAD.start()


def _pgrep_d2r_state():
    """Is D2R.exe running ON THIS MACHINE, asked with pgrep (Mac/Linux). -> True | False | None

    ⚠ 2026-09-28 — THREE ANSWERS, NOT TWO. pgrep exits 0 (a match) or 1 (no match); anything else —
    a timeout, a missing binary (Windows has NO pgrep, and FileNotFoundError is exactly how it says
    so), an unexpected exit code — is None: the probe could not RUN, which is UNKNOWN and never "the
    game is shut". _d2r_process_alive() below keeps its two-valued answer for its callers.
    [[unknown-stays-unknown]]"""
    try:
        out = subprocess.run(["pgrep", "-f", "D2R.exe"], capture_output=True, timeout=2)
    except Exception:
        return None
    if out.returncode == 0:
        return True
    if out.returncode == 1:
        return False
    return None


def _d2r_process_alive():
    """v1251 — cheap pgrep for the real game binary (CrossOver-hosted D2R.exe).

    Two-valued on purpose for its callers (the Mac full-screen fallback): a probe that cannot run
    reads False here. A caller that must tell UNKNOWN from "not running" asks _pgrep_d2r_state()."""
    return _pgrep_d2r_state() is True


def _screen_recording_preflight():
    """v1251 — silent TCC check (no dialog). Hot-path safe for film/capture loops."""
    if sys.platform != "darwin":
        return True
    try:
        from Quartz import CGPreflightScreenCaptureAccess
        return bool(CGPreflightScreenCaptureAccess())
    except Exception:
        return True


def _allow_fullscreen_game_fallback(why=""):
    """v1251 — full-screen is ONLY legal when it is actually the game (Metal fullscreen /
    Space transition), never a wallpaper dump of the Mac desktop.

    Blocked when:
      · Screen Recording is denied (Quartz window grab fails; full-screen = desktop)
      · D2R.exe is not running (Battle.net lobby alone is not the game)
    Allowed when SR is OK AND the game process is alive (window unlisted / white Metal)."""
    if not _screen_recording_preflight():
        return False
    if not _d2r_process_alive():
        return False
    return True


def capture_mac(path, timeout=12):
    """Full-screen capture by default (fullscreen D2R / CrossOver).
    Optional TV_CAPTURE=window|auto pins CrossOver/D2R window. v753 hard timeout.
    v779 — always capture to a temp path first (stale-target trust gate killed).
    v1251 — NEVER fall through to full-screen DESKTOP when window pin fails without
    Screen Recording / without a live D2R.exe (Konyo live: eye stuck on wallpaper)."""
    global _CAP_TARGET, _CAP_WHY, _LAST_GOOD_WIN
    _CAP_WHY = ""
    mode = (os.environ.get("TV_CAPTURE") or "auto").strip().lower()   # v777.1 (Konyo live: 'it's showing the desktop') — AUTO pins the D2R window when one exists; full-screen only as fallback
    # ⚠⚠ #236 — TV_CAPTURE=off NEVER TOUCHES THE SCREEN. MEASURED 2026-09-24 during a push: the render
    # gate's private (stub) console went live by itself, pinned HIS GeForce NOW stream as the game and
    # captured it frame after frame into its sandbox — 84% CPU on the console, the render step starved
    # at load 12.6 and the push was refused. A throwaway console has no business filming his screen.
    # `off` refuses every capture, says so, and calls nothing that reads a window.
    if mode in ("off", "none"):
        _CAP_WHY = "capture is OFF (TV_CAPTURE=%s) - this console never reads the screen" % mode
        _CAP_TARGET = {"mode": "off", "label": "capture off (TV_CAPTURE)", "wid": None}
        return False
    # Optional window pin only when explicitly asked (or auto)
    if mode in ("auto", "window", "win", "game"):
        hit = find_d2r_window_mac()
        # v779 — LAST-GOOD CACHE: Quartz listing is flaky from the agent's context; a window
        # that pinned once stays pinned until a capture with it actually fails.
        if hit:
            _LAST_GOOD_WIN = hit
        elif _LAST_GOOD_WIN:
            hit = _LAST_GOOD_WIN
        if not hit:
            _CAP_WHY = "no game window: %s" % (_PICK_WHY or "no match in list")
        if hit:
            wid, label = hit
            try:
                # v844 — screencapture -l OR Quartz CGWindowListCreateImage (SC alone was
                # dying all night with rc=1 size=0 while D2R.exe was right there)
                if _capture_window_to_file(wid, path, timeout=timeout):
                    if _CAP_TARGET.get("wid") != wid or _CAP_TARGET.get("mode") != "window":
                        try: ev("cap", "🎯 eye pinned to %s" % label)
                        except Exception: pass
                    _CAP_TARGET = {"mode": "window", "label": label, "wid": wid}
                    return True
                # window grab failed — drop stale last-good so we re-list next tick
                _CAP_WHY = "window capture failed (quartz+sc) wid=%s" % wid
                try:
                    # force re-pick next frame (stale wid is the common fail mode)
                    globals()["_PICK_CACHE"] = None
                except Exception:
                    pass
                # v1251 — only fall through to full when the game is truly alive + SR ok
                # (Metal fullscreen). Otherwise HOLD the eye — never wallpaper/desktop.
                if not _allow_fullscreen_game_fallback(_CAP_WHY):
                    _LAST_GOOD_WIN = None
                    _CAP_TARGET = {
                        "mode": "waiting",
                        "label": ("eye held — " + _CAP_WHY +
                                  " · open D2R in-game + grant Screen Recording to Python"),
                        "wid": None,
                    }
                    return False
                _CAP_TARGET = {"mode": "full", "label": "full screen (%s)" % _CAP_WHY,
                               "wid": wid}   # v898 — keep game wid so film still tries D2R.exe
            except Exception as e:
                _CAP_WHY = "window capture exc: %s" % e
                if not _allow_fullscreen_game_fallback(_CAP_WHY):
                    _LAST_GOOD_WIN = None
                    _CAP_TARGET = {"mode": "waiting",
                                   "label": "eye held — %s" % _CAP_WHY, "wid": None}
                    return False
        if mode in ("window", "win", "game"):
            _CAP_TARGET = {"mode": "waiting", "label": "Diablo II / CrossOver not found", "wid": None}
            return False
        # v929.1 (Grok third-eye P0) — AUTO with no window AND no last-good pin must NOT
        # fall through to a full-screen DESKTOP grab: with the v927.5 process-alive gate
        # keeping reads armed, this lane quietly re-created the privacy leak v928.2 closed
        # (desktop frames read + archived while the game window is unlisted). No pin → no eye.
        if not hit:
            # v1251 — process-alive Metal fullscreen exception (window unlisted but D2R.exe up)
            if _allow_fullscreen_game_fallback("no-window-process-alive"):
                _CAP_WHY = "D2R.exe alive · window unlisted — fullscreen game lane"
                # fall through to full-screen grab below
            else:
                _CAP_TARGET = {"mode": "waiting",
                               "label": "D2R window not listed — eye held", "wid": None}
                return False
        # auto with a pinned-but-unGRABbable window → fall through to full screen ONLY when
        # _allow_fullscreen_game_fallback said yes (game owns the display)
    # DEFAULT / fallback: entire display (Quartz first — SC full can also hang under load)
    tmp = _cap_tmp(path)
    try:
        qj = path + ".full.jpg"
        if _quartz_grab_screen(qj, uti="public.jpeg"):
            try:
                subprocess.run(
                    ["sips", "-s", "format", "bmp", qj, "--out", tmp],
                    capture_output=True, timeout=min(8, max(3, timeout)), **NICE_KW)
            except Exception:
                pass
            try:
                if os.path.exists(qj):
                    os.remove(qj)
            except Exception:
                pass
            if _cap_promote(tmp, path, min_bytes=8000):
                _wid_keep = (_CAP_TARGET or {}).get("wid") or (
                    _LAST_GOOD_WIN[0] if _LAST_GOOD_WIN else None)
                _CAP_TARGET = {
                    "mode": "full",
                    "label": ("full screen" + ((" (" + _CAP_WHY + ")") if _CAP_WHY else "")),
                    "wid": _wid_keep,
                }
                return True
        try:
            r = subprocess.run(
                ["screencapture", "-x", "-t", "bmp", tmp],
                capture_output=True, timeout=min(4, timeout), **NICE_KW)
        except Exception:
            r = None
        ok = _cap_promote(tmp, path)
        if ok:
            _wid_keep = (_CAP_TARGET or {}).get("wid") or (
                _LAST_GOOD_WIN[0] if _LAST_GOOD_WIN else None)
            _CAP_TARGET = {
                "mode": "full",
                "label": ("full screen" + ((" (" + _CAP_WHY + ")") if _CAP_WHY else "")),
                "wid": _wid_keep,
            }
        else:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:
                pass
        return ok
    except Exception:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
        return False

# v771.2 — SIM without Screen Recording: synthetic BMPs so settle+stub reads still fire.
# Real play never sets TV_STUB; this only kicks in when capture fails under stub.
_STUB_CAP_I = 0
def capture_stub_synth(path):
    """Write a valid 24-bit BMP that alternates (motion) then holds (settle).
    Hold ~8 polls (~2s) then hard-switch palette so sig_diff ≫ SETTLE/MOTION_PEAK."""
    global _STUB_CAP_I
    import struct
    _STUB_CAP_I += 1
    slot = (_STUB_CAP_I // 8) % 4
    # far-apart RGB so every sampled byte jumps well past tol=28
    palette = [
        (255, 0, 0),
        (0, 255, 0),
        (0, 0, 255),
        (255, 255, 0),
    ]
    r, g, b = palette[slot]
    w, h = 640, 400
    row = w * 3
    pad = (4 - (row % 4)) % 4
    pixel_size = (row + pad) * h
    file_size = 54 + pixel_size
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "wb") as f:
            f.write(b"BM")
            f.write(struct.pack("<IHHI", file_size, 0, 0, 54))
            f.write(struct.pack("<IIIHHIIIIII", 40, w, h, 1, 24, 0, pixel_size, 2835, 2835, 0, 0))
            # BGR rows — solid block, maximum sig_diff between slots
            row_bytes = bytes([b, g, r]) * w + (b"\x00" * pad)
            for _y in range(h):
                f.write(row_bytes)
        return os.path.isfile(path) and os.path.getsize(path) > 200000
    except Exception:
        return False

def newest_watched_frame():
    """Windows mode: capture_win.ps1 drops frames into tv/frames — consume the newest."""
    try:
        # Prefer live.bmp (intelligence); ignore eye.jpg / read.jpg (film / vision transport)
        skip = {"read.jpg", "eye.jpg", "cap_target.json"}
        fs = [os.path.join(FRAMES, f) for f in os.listdir(FRAMES)
              if f.lower().endswith((".bmp", ".png", ".jpg", ".jpeg"))
              and f.lower() not in skip
              and not f.lower().endswith(".part.jpg")
              and "tmp" not in f.lower()]
        return max(fs, key=os.path.getmtime) if fs else None
    except Exception:
        return None


def _refresh_cap_target_from_disk():
    """v784/v1419 — Windows capture_win.ps1 writes frames/cap_target.json; surface it on /state.
    utf-8-sig: PowerShell Set-Content -Encoding UTF8 writes a BOM that plain utf-8 json.load can miss,
    leaving UI stuck on default 'eye arming…' while live.png is pure D2R."""
    global _CAP_TARGET
    try:
        p = os.path.join(FRAMES, "cap_target.json")
        if not os.path.isfile(p):
            return
        with open(p, encoding="utf-8-sig") as f:
            raw = f.read()
        if not raw or not raw.strip():
            return
        j = json.loads(raw)
        mode = (j.get("mode") or "full").strip()
        label = (j.get("label") or mode)[:120]
        # Prefer window pin when capture half is healthy
        nxt = {"mode": mode, "label": label, "wid": j.get("wid")}
        if nxt != _CAP_TARGET:
            if mode == "window" and label and (_CAP_TARGET or {}).get("label") != label:
                try:
                    ev("cap", "🎯 eye pinned to %s" % label)
                except Exception:
                    pass
            _CAP_TARGET = nxt
    except Exception:
        pass

def frame_sig(path):
    """~4k byte samples across the BMP pixel data — cheap fuzzy fingerprint, stdlib only.
    v877 (army audit #2) — SAMPLED SEEKS: the old full-file read + slice churned ~0.5-1GB/s
    of memory at poll cadence on retina BMPs. Same fingerprint, 4096 × 1-byte reads."""
    try:
        import mmap as _mmap
        with open(path, "rb") as f:
            mm = _mmap.mmap(f.fileno(), 0, access=_mmap.ACCESS_READ)
            try:
                body = memoryview(mm)[54:]
                step = max(1, len(body) // 4096)
                out = bytes(body[::step][:4096])
                body.release()
                return out
            finally:
                mm.close()
    except Exception:
        with open(path, "rb") as f:
            data = f.read()
        body = data[54:]
        step = max(1, len(body) // 4096)
        return bytes(body[::step][:4096])

def sig_diff(a, b, tol=28):
    """fraction of samples that MEANINGFULLY differ. Real-game calibration (Konyo's town
    video): render/recording noise nudges nearly every pixel a little each frame, and the
    background always animates — so equality is useless. A sample counts as changed only
    when its value moved by more than `tol` (ambient flicker stays under it; opening a
    panel / a tooltip / walking moves whole regions far past it)."""
    if a is None or b is None or len(a) == 0 or len(b) == 0: return 1.0
    if a is b or a == b: return 0.0   # v877 — identical frames skip the 4096-sample loop
    m = min(len(a), len(b))
    return sum(1 for i in range(m) if abs(a[i] - b[i]) > tol) / m

# v735 — per-read frame ring for session history (human eye ~1920; AI still uses 1568)
HIST_DIR = os.environ.get("TV_HIST") or os.path.join(FRAMES, "hist")   # v886 — ONE hist root, harness-overridable
try:
    HIST_KEEP = max(10, int(os.environ.get("TV_HIST_KEEP", "800")))   # v840 — more AI-read photos protected
    HIST_MB = max(50, int(os.environ.get("TV_HIST_MB", "1500")))      # v839 — footage era: ceiling raised (REG-025)
    FOOT_MB = max(50, int(os.environ.get("TV_FOOT_MB", "400")))       # v840 — footage dies sooner (was 900; 2600 f_ drowned the night)
    FOOT_KEEP = max(60, int(os.environ.get("TV_FOOT_KEEP", "28800")))  # v860 (Konyo: 'change the global cap!') — ~4h @2fps; the MB budget (FOOT_MB) is the real guard, count can never eat older sessions
    MIN_FREE_GB = max(2, int(os.environ.get("TV_MIN_FREE_GB", "8")))   # v861.1 — the ONLY retention governor
except Exception:
    HIST_KEEP = 800
    HIST_MB = 1500
    FOOT_MB = 400
    FOOT_KEEP = 28800
    MIN_FREE_GB = 8
# 2026-10-24 (Elad: "cap at 8") — a SIZE CAP on frames/hist beside the free-disk floor. The floor alone let hist
# grow to 14 GB on a disk with room; over the cap, the SAME evidence-aware shed below runs (footage first, youth
# shield, cited pictures spared, never the two newest reels). TV_HIST_CAP_GB=0 turns the cap off.
try:
    HIST_CAP_GB = max(0.0, float(os.environ.get("TV_HIST_CAP_GB", "8")))
except Exception:
    HIST_CAP_GB = 8.0
# MacBook-ish display width for click-to-enlarge (not the AI vision input size)
HIST_MAX_PX = int(os.environ.get("TV_HIST_PX", "2560"))   # v753 — retina-crisp fullscreen (was 1920)

# v741 — KNOWN-DEAD FRAMES (Konyo: the loading/portal screen 'is always the same photo — it
# should be recognized'): an empty deep read teaches the agent that frame's signature; when it
# reappears (any zone transition), it is recognized locally in ~0ms — no vision spent, and the
# history registers an honest '⏳ transition' row instead of another 'nothing readable'.
KNOWN_DEAD_CAP = 8
_KNOWN_DEAD = []
# v1902 — ISOLATED LIKE EVERY OTHER LEARNED FILE. This is WRITTEN (_known_dead_save), and it
# was built from a bare HERE, so a run driven against a fixture hist taught HIS agent the
# fixture's dead frames — permanently, since the whole point of the file is that learning
# survives restarts. Guard the PATH, not the call site.
def _known_dead_file():
    """v2423 — IMPORT-BOUND WAS THE WHOLE DEFECT, even though the root rule was already right.

    This resolved `_fixture_root(HERE)` correctly — ONCE, at import. So a suite that sets TV_HIST in
    setUp, after the module is loaded, got the LIVE path and believed it was isolated. CI's
    per-gate attribution named test_agent as the writer of `known_frames.json`, and this is why:
    the rule was correct and the moment it was applied was not.

    That is exactly the class the import-bound-path registry exists to name — "a redirect that
    silently does not take". Resolved at call time now, like its four siblings fixed this session.
    """
    return (os.environ.get("TV_KNOWN_FRAMES")
            or os.path.join(_fixture_root(HERE), "known_frames.json"))


#: kept so existing readers of the module attribute resolve; the CALLABLE is the source of truth.
_KNOWN_DEAD_FILE = (os.environ.get("TV_KNOWN_FRAMES")
                    or os.path.join(_fixture_root(HERE), "known_frames.json"))
def _known_dead_load():
    """v742 — learning survives restarts: the loading screen is learned ONCE, ever."""
    try:
        import base64
        with open(_known_dead_file(), encoding="utf-8") as f:
            for b in json.load(f)[:KNOWN_DEAD_CAP]:
                _KNOWN_DEAD.append(bytes(base64.b64decode(b)))
    except Exception:
        pass

def _known_dead_save():
    try:
        import base64
        with open(_known_dead_file(), "w", encoding="utf-8") as f:
            json.dump([base64.b64encode(bytes(k)).decode() for k in _KNOWN_DEAD], f)
    except Exception:
        pass

def learn_dead_frame(sig):
    if sig is None: return
    for k in _KNOWN_DEAD:
        if sig_diff(sig, k) <= 0.04: return   # already known
    _KNOWN_DEAD.append(sig)
    del _KNOWN_DEAD[:-KNOWN_DEAD_CAP]
    _known_dead_save()

# v746 — the transition label reads the story so far (Konyo: 'ENTERING a PORTAL or ENTERING A
# NEW GAME, depending on the photos beforehand'). LAST_AREA is the last zone a deep read saw.
LAST_AREA = ""
def transition_note(last_area, n_reads):
    if last_area: return f"through the portal — leaving {last_area}"
    if n_reads == 0: return "entering a new game"
    return "loading — next area coming"

def should_learn_dead(rd):
    """v794 (Grok R5 #4) — learn a dead frame ONLY on an explicit vision-confirmed transition.
    The old gate also learned mode:empty / parse-fail shapes — ONE chatty-CLI hiccup on a real
    inventory freeze wrote that panel into known_frames.json and the eye stayed blind to that
    whole panel class for the rest of the night (and across restarts)."""
    if rd.get("names") or rd.get("area"):
        return False
    if rd.get("mode") in ("empty", "error", "timeout"):
        return False
    return rd.get("scene") == "transition"

def known_dead_match(sig):
    if sig is None: return None
    for k in _KNOWN_DEAD:
        if sig_diff(sig, k) <= 0.04: return k
    return None

def _is_real_jpeg(path, min_bytes=32):
    """True only when the file on disk is JPEG SOI magic — not a BMP/PNG renamed .jpg."""
    try:
        if not path or not os.path.isfile(path) or os.path.getsize(path) < min_bytes:
            return False
        with open(path, "rb") as f:
            return f.read(3) == b"\xff\xd8\xff"
    except Exception:
        return False


def _win_image_to_jpeg(src, dest, max_px=1568, quality=80):
    """v1421 — Windows portable JPEG convert via System.Drawing (same stack as capture_win.ps1).
    Zero pip deps. Returns True only when dest is a real JPEG."""
    if sys.platform != "win32" or not src or not os.path.isfile(src):
        return False
    try:
        os.makedirs(os.path.dirname(os.path.abspath(dest)) or ".", exist_ok=True)
        # PowerShell 5.1 + System.Drawing — always present with .NET Framework on Windows desktop.
        # FromFile locks src until Dispose; scale like sips --resampleHeightWidthMax.
        ps = (
            "$ErrorActionPreference='Stop'; "
            "Add-Type -AssemblyName System.Drawing; "
            "$src = $env:TV_JPEG_SRC; $dest = $env:TV_JPEG_DEST; "
            "$max = [int]$env:TV_JPEG_MAX; $q = [int]$env:TV_JPEG_Q; "
            "$img = [System.Drawing.Image]::FromFile($src); "
            "try { "
            "  $w = $img.Width; $h = $img.Height; "
            "  if ($w -gt $max -or $h -gt $max) { "
            "    $scale = [Math]::Min($max / [double]$w, $max / [double]$h); "
            "    $nw = [Math]::Max(1, [int]($w * $scale)); $nh = [Math]::Max(1, [int]($h * $scale)); "
            "    $bmp = New-Object System.Drawing.Bitmap $nw, $nh; "
            "    $g = [System.Drawing.Graphics]::FromImage($bmp); "
            "    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic; "
            "    $g.DrawImage($img, 0, 0, $nw, $nh); $g.Dispose(); $img.Dispose(); $img = $bmp; "
            "  } "
            "  $tmp = $dest + '.part.jpg'; "
            "  $codec = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | "
            "    Where-Object { $_.MimeType -eq 'image/jpeg' } | Select-Object -First 1; "
            "  $ep = New-Object System.Drawing.Imaging.EncoderParameters 1; "
            "  $ep.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter "
            "    ([System.Drawing.Imaging.Encoder]::Quality, [long]$q); "
            "  $img.Save($tmp, $codec, $ep); "
            "  if (Test-Path -LiteralPath $dest) { Remove-Item -LiteralPath $dest -Force -EA SilentlyContinue }; "
            "  Move-Item -LiteralPath $tmp -Destination $dest -Force; "
            "} finally { try { $img.Dispose() } catch {} }"
        )
        env = os.environ.copy()
        env["TV_JPEG_SRC"] = os.path.abspath(src)
        env["TV_JPEG_DEST"] = os.path.abspath(dest)
        env["TV_JPEG_MAX"] = str(int(max_px))
        env["TV_JPEG_Q"] = str(int(max(40, min(95, quality))))
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", ps],
            capture_output=True, timeout=25, env=env,
            **{k: v for k, v in (NICE_KW.items() if isinstance(globals().get("NICE_KW"), dict) else {})
               if k in ("creationflags", "start_new_session")})
        return r.returncode == 0 and _is_real_jpeg(dest)
    except Exception:
        return False


def _to_jpeg(src, dest, max_px=1568, quality=80):
    """Mac sips first; Windows System.Drawing; never claim success on non-JPEG bytes.

    v1450 — sips --resampleHeightWidthMax UPSAMPLES small sources on current macOS
    (48px → max_px). Only pass the flag when the source actually exceeds max_px (downscale)."""
    if not src or not os.path.isfile(src):
        return False
    # Already a real JPEG and dest==src path intent — copy if needed.
    if _is_real_jpeg(src) and os.path.abspath(src) == os.path.abspath(dest):
        return True
    if _is_real_jpeg(src) and max(os.path.getsize(src), 1) < 2_500_000:
        try:
            import shutil
            os.makedirs(os.path.dirname(os.path.abspath(dest)) or ".", exist_ok=True)
            # still downscale oversized JPEGs (big eye frames) when max_px set
            w, h = _sips_pixel_size(src)
            # ⚠ v2417 — "CANNOT TELL" USED TO COPY THE FRAME VERBATIM AND REPORT SUCCESS.
            # The old condition was `if max_px and w and h and max(w,h) > max_px: pass` with a copy
            # in the else — so UNKNOWN dimensions took the copy branch and returned True. On any
            # host without `sips`, _sips_pixel_size always returns (None, None), which means an
            # oversized JPEG was copied AT FULL SIZE and the caller was told it had been
            # normalised. That is worse than returning False: a false success cannot be detected
            # downstream, and every one is a paid read at three times the pixels.
            #
            # Found by a test written to prove the new PIL fallback worked — it failed at
            # `2940 != 1568` because control never reached the fallback at all. The copy shortcut
            # is now taken ONLY on positive evidence that the frame is already within spec.
            # [[unknown-stays-unknown]]
            _known = bool(w and h)
            if max_px and (not _known or max(w, h) > int(max_px)):
                pass  # oversized, or size UNKNOWN — either way, normalise rather than assume
            else:
                shutil.copy2(src, dest)
                return _is_real_jpeg(dest)
        except Exception:
            pass
    try:
        os.makedirs(os.path.dirname(os.path.abspath(dest)) or ".", exist_ok=True)
        cmd = ["sips", "-s", "format", "jpeg", "-s", "formatOptions", str(int(quality))]
        w, h = _sips_pixel_size(src)
        if max_px and w and h and max(w, h) > int(max_px):
            cmd += ["--resampleHeightWidthMax", str(int(max_px))]
        elif max_px and not (w and h):
            # unknown dims — only resample when source file is large enough to need it
            try:
                if os.path.getsize(src) > 400_000:
                    cmd += ["--resampleHeightWidthMax", str(int(max_px))]
            except Exception:
                pass
        cmd += [src, "--out", dest]
        r = subprocess.run(cmd, capture_output=True, timeout=25, **NICE_KW)
        if r.returncode == 0 and _is_real_jpeg(dest):
            return True
    except Exception:
        pass
    if _win_image_to_jpeg(src, dest, max_px=max_px, quality=quality):
        return True
    # ⚠ v2417 — A THIRD PATH, BECAUSE THE "LOCKED" SPEC WAS ONLY ENFORCEABLE ON TWO PLATFORMS.
    # sips is macOS and _win_image_to_jpeg is Windows; on anything else this returned False, and
    # _readable_frame's caller then sent the ORIGINAL frame to a paid read. Measured on CI (ubuntu):
    # a 2940x1912 source reaches the model at 2940 — three times the pixels the locked intake spec
    # allows, on every read, silently. The test that catches it has been red there since before
    # 2026-09-01T18:14 and I had not looked at CI.
    #
    # ⚠ HIS PRODUCTION BEHAVIOUR IS UNCHANGED AND THAT IS THE POINT. His machines are Mac and
    # Windows, where sips or System.Drawing succeed FIRST and this branch is never reached — proven
    # by the platform test below. This does not alter the locked intake; it makes the lock hold on
    # a host where it currently does not. PIL is already imported elsewhere in this file, so it
    # adds no dependency. [[d2r-intake-LOCKED]] [[feedback-blind-fixture-green-gate]]
    try:
        from PIL import Image as _PI
        os.makedirs(os.path.dirname(os.path.abspath(dest)) or ".", exist_ok=True)
        with _PI.open(src) as _im:
            _im = _im.convert("RGB")
            if max_px and max(_im.size) > int(max_px):
                _im.thumbnail((int(max_px), int(max_px)), _PI.LANCZOS)
            _im.save(dest, "JPEG", quality=int(quality))
        return _is_real_jpeg(dest)
    except Exception:
        pass
    return False


def _film_shrink(src, dest, max_px, quality):
    """Downscale one film frame as cheaply as this machine can. -> bool

    v2320 — MEASURED, because the obvious implementation costs more than it saves. `_to_jpeg`
    shells out to `sips`, and a subprocess SPAWN dominates the work:

        raw copyfile                    0.5 ms/frame  -> 1541 KB
        _to_jpeg (sips)                87.5 ms/frame  ->  427 KB
        PIL draft-mode decode          32.2 ms/frame  ->  245 KB

    PIL's `draft()` tells the JPEG decoder to decompress at a reduced scale in the first place, so
    it never builds the full 2940x1912 bitmap it is about to throw away. Faster AND smaller than
    the subprocess.

    ⚠ THIS IS A DISK FIX, NOT A LAG FIX, AND SAYING SO MATTERS. At his measured 0.74 fps it costs
    about +24 ms/s of CPU and saves about 1 MB/s of writes — and an SSD does not care about 1 MB/s.
    What it does buy is real: 910 MB of reels in one day becomes roughly 160 MB, on a machine that
    hit a disk-full warning today. The console pinning a core during capture is a DIFFERENT
    problem and this does not touch it. [[feedback-verify-not-proxy]]
    """
    try:
        from film_frame import to_film_jpeg, FILM_W as _FW, FILM_H as _FH
        try:
            mp = int(max_px)
        except Exception:
            mp = _FW
        if mp < _FW:
            fw, fh = mp, max(1, int(mp * _FH / float(_FW)))
        else:
            fw, fh = _FW, _FH
        return bool(to_film_jpeg(src, dest, quality=quality, film_w=fw, film_h=fh))
    except Exception:
        pass
    try:
        return bool(_to_jpeg(src, dest, max_px=max_px, quality=quality))
    except Exception:
        return False


def _readable_frame(ap, out_jpg=None):
    """v710.6 LIVE-SESSION FIX (Konyo's first real run): claude's Read tool chokes on a 16MB
    raw BMP — both live reads timed out at 180s. Convert to a 1568px JPEG (the locked intake
    spec) before the vision call. Mac: sips. Windows v1421: System.Drawing (not live.png alone —
    PNG can still be multi-MB and some readers expect JPEG). Falls back to live.png then original.

    ══ v2327 — IT TESTED THE FORMAT WHEN IT MEANT THE SIZE, AND v2324 WALKED INTO IT ══════════
    The guard here was `if not ap.lower().endswith(".bmp"): return ap`, written when the only
    oversized frame in the tree WAS a bmp. v2324 stopped inflating captures into BMPs and began
    writing live.jpg — correct on its own terms, and it silently changed what the PAID model
    receives, because a .jpg now walks straight through this early return.

    MEASURED on one of his real frames:
        live.bmp -> read.jpg   1568x1019    555 KB   <- the locked intake spec
        live.jpg -> live.jpg   2940x1912   1819 KB   <- what v2324 started sending

    Three times the pixels and 3.3x the bytes on every paid read, and the intake is LOCKED
    (Sonnet + crop, do not change) — so this was not a tuning choice, it was a spec being broken
    by a change made two files away. [[label-outlived-referent]] [[sweep-dont-ask]]

    So the question becomes the one it always meant: IS THIS FRAME BIGGER THAN THE SPEC? A frame
    already within it passes through untouched (re-encoding a JPEG only loses quality); anything
    over it is normalised, whatever it is called.
    """
    try:
        _READ_MAX_PX = 1568          # the locked intake spec, named rather than repeated
        _needs = None
        try:
            from PIL import Image as _I
            with _I.open(ap) as _im:              # header only — does not decode the pixels
                _needs = max(_im.size) > _READ_MAX_PX
        except Exception:
            _needs = None                          # cannot tell: fall back to the old format test
        if _needs is False:
            return ap                              # already within spec
        if _needs is None and not ap.lower().endswith(".bmp"):
            return ap                              # unreadable header: behave exactly as before
        jp = out_jpg or os.path.join(FRAMES, "read.jpg")
        if _to_jpeg(ap, jp, max_px=1568, quality=80):
            global _JPEG_LOGGED
            if not globals().get("_JPEG_LOGGED"):
                _JPEG_LOGGED = True
                try:
                    was = os.path.getsize(ap)
                    now = os.path.getsize(jp)
                    ev("boot", "vision transport OK — frame \u2192 read.jpg %dKB (was %dMB)"
                       % (now // 1024, max(1, was // 1024 // 1024)))
                except Exception:
                    pass
            return jp
        # v1709 — do NOT substitute frames/eye.jpg. That is a DIFFERENT photo
        # (the live eye, not this settle frame). A convert-fail returns the
        # original path — honest BMP passthrough — never another file's pixels.
        png = os.path.join(os.path.dirname(ap), "live.png")   # Windows: saved by capture_win.ps1
        if os.path.isfile(png):
            return png
    except Exception:
        pass
    return ap

_JFID_STATE = {"path": None, "ids": None}   # v877 — cold parse keyed on the journal PATH
# The v849 mtime-key cache defeated itself: every append changed the live journal's mtime,
# so the "cache" re-parsed ~24MB of JSONL on nearly every read, forever.
#: ⚠⚠ SESSIONS THE VAULT STILL CITES AS EVIDENCE. Measured 2026-09-05: `vault_accum.json` names 4
#: sessions in its `witnesses` lists and TWO OF THEM ARE ALREADY GONE — including "Chaotic Grand
#: Charm", whose frame `f_1787520901207.jpg` the ledger still points at and which no longer exists.
#: His ruling on those: *"its fine just make sure going forward it will be.. whats in the past is
#: the past."* So nothing is back-filled; this only stops it happening again.
_WACC_STATE = {"sess": None, "mtime": None}


def _witness_protected_sessions():
    """Sessions a vault witness still references. -> set | None (None = COULD NOT ASK)

    ⚠ 2026-09-28 — NO LONGER THE REAPER'S AUTHORITY. It asks vault_accum.json alone, and on that day the reel
    reaper took a reel chron_evidence cites. The reaper asks _reel_evidence() now (frame_authority's witness
    index + chron_evidence); this stays for the laws that pin its UNKNOWN-is-not-empty contract.

    ⚠ None IS NOT AN EMPTY SET, and the caller must treat it as "refuse to reap". An unreadable
    ledger means we do not know what is cited, and deleting footage on the strength of a question
    we could not ask is the whole failure this guards. [[unknown-stays-unknown]]
    """
    # ⚠ DERIVED FROM HIST_DIR, NOT FROM HERE. HIST_DIR is TV_HIST-overridable, and a fixture run
    # pointed at a scratch shelf must read that shelf's ledger — not his. Anchoring on HERE would
    # make every fixture consult his live vault_accum.json, which is the crossing this repo has
    # been bitten by repeatedly. [[feedback-fixtures-never-touch-live-data]]
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(HIST_DIR))),
                        "vault_accum.json")
    try:
        mt = os.path.getmtime(path)
    except OSError:
        return set()          # no ledger at all = nothing is cited. A real, measured answer.
    if _WACC_STATE["sess"] is not None and _WACC_STATE["mtime"] == mt:
        return _WACC_STATE["sess"]
    try:
        with open(path, encoding="utf-8") as _fh:
            blob = json.load(_fh)
    except Exception:
        return None           # ⚠ COULD NOT ASK. Never an empty set.
    out = set()
    try:
        for row in (blob.get("owned") or []):
            for w in (row.get("witnesses") or []):
                sid = (w or {}).get("session")
                if sid:
                    out.add(str(sid))
    except Exception:
        return None
    _WACC_STATE["sess"] = out
    _WACC_STATE["mtime"] = mt
    return out


def _dbg(msg):
    """Say it. ⚠ The reaper used to fail inside `except: pass`, which made "it broke" and "it had
    nothing to do" the same event. Anything this path does or refuses to do gets said out loud."""
    try:
        print("[reap] %s" % msg, flush=True)
    except Exception:
        pass


def _test_pinned_reels():
    """Reel ids the test suite pins as real footage (test_reel_refs.json 'accepted'). -> set | None

    None means the list could not be read - the reaper then only knows what the vault cites."""
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_reel_refs.json"),
                  encoding="utf-8") as fh:
            return set(json.load(fh).get("accepted") or [])
    except Exception:
        return None


def _reap_log_path(hist=None):
    """Where the recorder's reap log lives, for its writer AND its readers (REG-1615: the river closes a reaped reel out
    from this log, so the path is one function, never two spellings). -> path, beside the shelf's parent."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(hist or HIST_DIR))), "reel_reaps.jsonl")


def _reap_record(reel, frames, removed, shelf, by="recorder-disk-floor", names=None, kept=None, spared=None,
                 river=None):
    """A durable line for every emergency reel deletion. -> None

    ⚠⚠ THIS IS NOT THE TOMBSTONE STORE, ON PURPOSE. `reel_retention._tombstone` is the ONE writer
    of `reel_tombstones.json`; a second writer would put two authorities on one store, which is
    the defect this repo keeps paying for. This is a separate, clearly-named record of what the
    RECORDER took under disk pressure, so an emergency deletion can never again leave no trace.
    Joining it into the tombstone proper is the retention lane's job, not the recorder's.
    ⚠ `frames=-1` means the count could not be taken — never a confident 0.
    """
    try:
        path = _reap_log_path()
        row = {"ts": int(time.time() * 1000), "reel": str(reel), "frames": int(frames),
               "removed": bool(removed), "shelfBefore": int(shelf), "by": str(by),
               "agentVer": VERSION, "minFreeGB": MIN_FREE_GB}
        # 2026-09-28 — WHICH frames, by name (bounded), so 'who took this picture' has an answer
        if names is not None:
            row["names"] = [str(x) for x in list(names)[:1200]]
        if kept is not None:
            row["kept"] = [str(x) for x in list(kept)[:1200]]
        if spared is not None:
            row["spared"] = int(spared)
        # REG-1678 — what the river said about the reel at the moment it was taken: its last stamped station and
        # whether a read was still owed (None = the river could not be asked - said as null, never as false)
        if river is not None:
            row["riverStation"] = river.get("station")
            row["readOwed"] = river.get("readOwed")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _reel_capture_ms(name):
    """The reel's own capture clock from its id. -> int (0 when absent, which sorts FIRST)"""
    import re as _re
    m = _re.search(r"(\d{13})", str(name or ""))
    return int(m.group(1)) if m else 0


def _journal_frame_ids():
    """v840 — every frameId still referenced by the session journal is UN-PRUNABLE.
    v877 — incremental: one cold parse per process; appends feed the set directly."""
    if _JFID_STATE["ids"] is None or _JFID_STATE["path"] != JOURNAL:
        ids = set()
        try:
            paths = [JOURNAL]
            try:
                d = os.path.dirname(JOURNAL) or "."
                base = os.path.basename(JOURNAL)
                for name in os.listdir(d):
                    if name.startswith(base) or (name.startswith("sessions") and name.endswith(".jsonl")):
                        paths.append(os.path.join(d, name))
            except Exception:
                pass
            seen_p = set()
            for jp in paths:
                if jp in seen_p or not os.path.isfile(jp):
                    continue
                seen_p.add(jp)
                try:
                    with open(jp, encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                fid = json.loads(line).get("frameId")
                            except Exception:
                                continue
                            if fid:
                                # v940.4 — shield the BASE jpeg too. Verify journals
                                # frameId 'N_ts#v' but the file is always 'N_ts.jpg';
                                # protecting only 'N_ts#v.jpg' left the real photo killable.
                                base = str(fid).split("#", 1)[0]
                                ids.add(str(fid) + ".jpg")
                                if base:
                                    ids.add(base + ".jpg")
                                    # reel-relative ids: reel_<sid>/f_<ts>
                                    if "/" in base:
                                        ids.add(os.path.basename(base) + ".jpg")
                except Exception:
                    pass
        except Exception:
            pass
        _JFID_STATE["path"], _JFID_STATE["ids"] = JOURNAL, ids
    ids = _JFID_STATE["ids"]
    # ⚠ L1 (review of bd976210) — THE SHIELD IS THE NEWEST 2,000 READ FRAMES, AND THAT IS A KNOWN LIMIT, NOT A PROMISE.
    # The board's evidence card cites receipt frameIds from d2r_vaultProv — the BOARD's store, which this process cannot
    # read. What it CAN see is this journal (capped below) and the evidence authority (_reel_evidence: the witness index
    # + chron_evidence's receipts). So a receipt's frame older than the newest 2,000 journal ids, and cited by neither,
    # can still be reaped under the disk floor. The card then says "picture not on this machine — <who took it>" in
    # words (picture_status / reel_reaps.jsonl), never a broken image. Shielding the board's receipts here would need a
    # store the console does not have, and the brief ruled out building one. REG-1387. [[unknown-stays-unknown]]
    PROTECT_CAP = max(200, int(os.environ.get("TV_PROTECT_CAP", "2000") or 2000))
    if len(ids) > PROTECT_CAP:
        def _fid_ms(x):
            # v2372 — one resolver. Sort key only: 0 keeps an unparseable id at the OLDEST end,
            # which is what the previous `except: return 0` did, so the cap still drops the ones
            # it always dropped.
            try:
                import frame_ref as _fr
                ts = _fr.timestamp_of(x)
            except Exception:
                ts = None
            return ts if ts is not None else 0
        ids = set(sorted(ids, key=_fid_ms)[-PROTECT_CAP:])
    return set(ids)


def _reel_evidence(hist_dir=None):
    """2026-09-28 — WHICH PICTURES ARE EVIDENCE, asked of the ONE authority. -> dict | None

    {"sessions": the sessions frame_authority's witness index names, "frames": every cited frame by file name
     (witness frames, the WATCHED/PROVEN/HARDENED citations, chron_evidence's receipts), "reels": the reels
     chron_evidence cites}. None = COULD NOT ASK (a ledger exists and will not read) — every caller refuses to
    delete on None. The disk-floor reaper used to ask only vault_accum.json's witness sessions, and on
    2026-09-28 it took a reel chron_evidence cites. [[the-unjoined-end]] [[unknown-stays-unknown]]

    ⚠ ROOTED ON THE SHELF, the same derivation as _witness_protected_sessions and _reap_record, so a fixture
    shelf asks its own ledgers and never his. [[feedback-fixtures-never-touch-live-data]]
    """
    hist_dir = hist_dir or HIST_DIR
    root = os.path.dirname(os.path.dirname(os.path.abspath(hist_dir)))
    try:
        import frame_authority as _fa
        wi = _fa.witness_index(root)
    except Exception:
        return None
    if not isinstance(wi, dict) or not wi.get("ok") or wi.get("cited") is None:
        return None
    # ⚠ M1 (review of 77d8d8b5, reproduced) — NO DURABLE STORE AT ALL IS NOT "NOTHING IS CITED". witness_index says ok
    # over a shelf where neither vault ledger exists (an absent store is a measurement of nothing), and its own
    # `haveIndex` exists for exactly this: without anything that COULD name a witness, "not a witness" is unprovable,
    # and frame_authority's rule is to err toward keeping. A deleter asks this, so it answers COULD NOT ASK.
    if not wi.get("haveIndex"):
        return None
    frames = set(os.path.basename(str(f)) for f in (wi.get("frames") or ()))
    frames |= set(os.path.basename(str(f)) for f in (wi.get("cited") or ()))
    sessions = set(str(s) for s in (wi.get("sessions") or ()))
    try:
        import reel_retention as _rr
        rows, _why = _rr.evidence_rows_at(root)
    except Exception:
        return None
    if rows is None:
        return None
    reels = set()
    for r in rows:
        fid = str(r.get("frameId") or "").replace("\\", "/")
        b = fid.rsplit("/", 1)[-1]
        if b:
            frames.add(b if b.endswith(".jpg") else b + ".jpg")
        rl = str(r.get("reel") or (fid.split("/")[0] if "/" in fid else "") or "")
        if rl:
            reels.add(rl if rl.startswith("reel_") else "reel_" + rl)
    # M1 — AND THE PICTURES A READ WAS TAKEN FROM. _reap_loose_film and the read eviction already spare the journal's
    # frames; the reel pick did not, so a partial release could take the very frame a read named. The journal's ids
    # come in both shapes (a bare f_<ms>.jpg and reel_<sid>/f_<ms>.jpg), so the reels it names are kept too.
    try:
        reads = set(str(x) for x in (_journal_frame_ids() or ()))
    except Exception:
        return None
    read_reels = set(x.split("/", 1)[0] for x in reads if "/" in x and x.startswith("reel_"))
    return {"sessions": sessions, "frames": frames, "reels": reels, "reads": reads, "readReels": read_reels}


def _river_positions():
    """REG-1678 — where the river last stamped each reel, for the disk floor. -> dict reel -> station | None

    The cheap read river_stamp keeps for a lane that ticks (one walk of its own store, no router pass). None = the
    store could not be asked, and the reaper then keeps its old order and says so - never "nothing is owed"."""
    try:
        import river_stamp as _rs
        pos, _why = _rs.positions()
    except Exception:
        return None
    return pos if isinstance(pos, dict) else None


def _reel_reap_pick(hist_dir, candidates, ev, pinned=None, river=None):
    """2026-09-28 — (c) the disk-floor reel reaper's choice, oldest first. -> dict | None

    A reel holding a CITED picture keeps those files and releases the rest (reel_retention.release_uncited's
    shape — the reel directory stays with its evidence in it). A reel whose session or reel id is cited but
    whose cited picture is not one of its files is kept WHOLE: which picture matters cannot be told, so none
    goes. A reel nothing cites may go whole. A reel that already holds nothing but evidence is skipped. An
    unreadable reel is never taken. `candidates` must already exclude the two newest.

    REG-1361 (merged from main, 2026-09-28) — a reel a law pins (`pinned`, test_reel_refs.json 'accepted') is asked
    only after every unpinned one, oldest first within each; a pinned reel still goes when nothing else may, because a
    full disk stops recording. None = the pin list could not be read = plain oldest-first. The answer says "pinned".

    REG-1678 (2026-10-01) — INSIDE each of those two tiers, a reel the river has FINISHED (`river` = reel ->
    station, its last stamp at one of reel_router.READ_DONE) goes before one that still owes a survey, a read, a
    seal or a join - or was never walked, which is not finished. Oldest first within each. The 09-28 reaps took the
    oldest reels whatever the river said; his chain is extract, tombstone, THEN delete, and a full disk still stops
    recording, so an owed reel still goes when nothing finished may - and the answer says so (`readOwed`).
    `river` None = the stamp store could not be asked: the old order, and `readOwed` None (UNKNOWN, not false)."""
    pinned = pinned or set()
    done = None
    if river is not None:
        try:
            import reel_router as _rtr
            done = frozenset(_rtr.READ_DONE)
        except Exception:
            done = None
    asked = river is not None and done is not None

    def _rank(c):
        return (c in pinned, (river.get(c) not in done) if asked else False)

    order = sorted(candidates, key=_rank)     # stable: the caller's oldest-first order holds inside each tier
    for cand in order:
        sid = cand[5:] if cand.startswith("reel_") else cand
        path = os.path.join(hist_dir, cand)
        try:
            jpgs = sorted(f for f in os.listdir(path) if f.endswith(".jpg"))
        except OSError:
            continue
        cited = [f for f in jpgs if f in ev["frames"]]
        # M1 — a frame a READ was taken from is kept like a cited one: by its own name, or by its reel-relative path
        reads = ev.get("reads") or set()
        named_here = set(x.split("/", 1)[1] for x in reads if x.startswith(cand + "/"))
        read_kept = [f for f in jpgs if (f in named_here or f in reads) and f not in cited]
        keep = cited + read_kept
        if keep:
            _keep = set(keep)
            gone = [f for f in jpgs if f not in _keep]
            if not gone:
                continue
            return {"reel": cand, "mode": "partial", "gone": gone, "kept": sorted(keep), "frames": len(jpgs),
                    "pinned": cand in pinned, "station": river.get(cand) if asked else None,
                    "readOwed": (river.get(cand) not in done) if asked else None}
        if sid in ev["sessions"] or cand in ev["reels"]:
            continue
        # M1 — NAMED BUT ABSENT: the journal names a picture of THIS reel that is not among its files, so which
        # picture matters cannot be told — the reel is kept whole, exactly like a reel cited by its session.
        if named_here or cand in (ev.get("readReels") or set()):
            continue
        return {"reel": cand, "mode": "whole", "gone": jpgs, "kept": [], "frames": len(jpgs), "pinned": cand in pinned,
                "station": river.get(cand) if asked else None,
                "readOwed": (river.get(cand) not in done) if asked else None}
    return None


def _reap_loose_film(hist_dir, now_s=None, limit=600, young_s=900.0):
    """2026-09-28 — (b) THE IN-LOOP FLOOR REAPER, and it asks now. -> {"removed", "spared", "refused"}

    Under MIN_FREE_GB, every 120 s, it deleted up to 600 loose f_*.jpg older than 15 minutes with NO evidence
    check — while the eviction beside it already protected _journal_frame_ids(). Measured 2026-09-28: the reads
    of String of Ears and seven Chronicle items (02:32-02:42) left no picture; the session's reel began at 02:44.
    Now: a frame the journal names (a read was taken from it) or the evidence authority cites is SPARED; when
    the authority cannot answer, NOTHING is deleted and it says so; every frame it takes is recorded by name in
    reel_reaps.jsonl so the doctor can say who took a picture. [[unknown-stays-unknown]]"""
    now_s = now_s or time.time()
    ev = _reel_evidence(hist_dir)
    if ev is None:
        _dbg("loose-film reap REFUSED: the evidence authority would not answer, so whether any loose frame "
             "is cited is UNKNOWN — nothing deleted, the disk stays tight")
        return {"removed": 0, "spared": 0, "refused": "the evidence authority would not answer"}
    try:
        protected = set(_journal_frame_ids()) | set(ev["frames"])
    except Exception as _e:
        _dbg("loose-film reap REFUSED: the journal shield would not load (%s)" % str(_e)[:80])
        return {"removed": 0, "spared": 0, "refused": "the journal shield would not load"}
    cut = (now_s - young_s) * 1000
    ff = []
    for f in os.listdir(hist_dir):
        if not (f.startswith("f_") and f.endswith(".jpg")):
            continue
        try:
            ms = int(f[2:-4])
        except ValueError:
            continue          # an unparseable stamp is not a frame this reaper may judge
        if ms < cut:
            ff.append(f)
    ff.sort()
    removed, spared = [], 0
    for dead in ff:
        if len(removed) >= limit:
            break
        if dead in protected:
            spared += 1
            continue
        try:
            os.remove(os.path.join(hist_dir, dead))
            removed.append(dead)
        except OSError:
            pass
    if removed or spared:
        _reap_record("loose", len(removed), bool(removed), -1, by="recorder-loose-floor", names=removed,
                     spared=spared)
        _dbg("loose-film reap took %d frame(s), spared %d read-bearing or cited" % (len(removed), spared))
    return {"removed": len(removed), "spared": spared, "refused": None}


def _read_picture_floor(hist_dir):
    """2026-09-28 — (a) may a read's picture be written now, and how big? -> (mode, why, free_gb)

    mode 'full' (the disk is healthy, or it cannot be measured — then behave exactly as before), 'small'
    (under MIN_FREE_GB: the read still keeps its picture, downscaled, inside a per-hour budget), 'refuse'
    (below the hard floor, or the budget is spent — the refusal is recorded so the doctor can say the picture
    was never written, and why)."""
    try:
        import read_pictures as _rp
        import shutil as _shp
        free = _disk_free_bytes(hist_dir) / 1e9
    except Exception:
        return ("full", "", None)
    if free < _rp.HARD_FLOOR_GB:
        return ("refuse", "hard-floor", free)
    if free >= MIN_FREE_GB:
        return ("full", "", free)
    spent = _rp.budget_spent_mb(hist_dir)
    # L2 (review of 77d8d8b5) — a budget record that will not read is "budget UNKNOWN", never "nothing spent": the
    # budget exists to stop floor-time pictures eating the last gigabytes, and an unread record would lift it.
    if spent is None:
        return ("refuse", "budget-unknown", free)
    if spent >= _rp.FLOOR_BUDGET_MB_PER_HOUR:
        return ("refuse", "floor-budget-spent", free)
    return ("small", "", free)


def _hist_over_cap(hist_dir=None):
    """Bytes frames/hist holds beyond HIST_CAP_GB (GiB), reels and caches included; 0 when under or off."""
    if not HIST_CAP_GB:
        return 0
    tot = 0
    for r, _d, fs in os.walk(hist_dir or HIST_DIR):
        for f in fs:
            try:
                tot += os.lstat(os.path.join(r, f)).st_size
            except OSError:
                pass
    return max(0, int(tot - HIST_CAP_GB * (1 << 30)))


def archive_read_frame(src_path, n, ts_ms=None):
    """v735 — snapshot the settled screen into frames/hist/{n}_{ts}.jpg (~1920 JPEG).
    Returns frame id string for /frame?id=… so each history row can reopen what the AI saw.
    Keeps last HIST_KEEP files. Never raises into the scan loop.

    v1421 Windows truth: the old portable fallback copied live.bmp bytes into a .jpg name
    (magic 42 4D). Claude Read + Theatre then choked on multi-MB BMP-as-jpg (70–180s reads).
    Archive MUST land real JPEG SOI (FF D8 FF) — convert via sips/System.Drawing, else copy
    eye.jpg / read.jpg, never a raw BMP body under a .jpg name when a real JPEG path exists."""
    ts_ms = ts_ms if ts_ms is not None else int(time.time() * 1000)
    fid = "%d_%d" % (int(n), int(ts_ms))
    try:
        _establish_footage()
        # 2026-09-28 — (a) THE READER HOLDS THE FRAME IT READ, SO THIS IS WHERE ITS PICTURE IS KEPT. Under the
        # disk floor the film stops ("disk-full") but a read still keeps its picture, small and inside a budget;
        # below the hard floor it does not, and the refusal is RECORDED — never a silent missing picture.
        _pmode, _pwhy, _pfree = _read_picture_floor(HIST_DIR)
        # ⚠ M2 (review of 77d8d8b5, reproduced) — A REFUSED PICTURE MAY NOT SKIP THE SHEDDING. This returned "" before
        # the eviction/reap block, so once free space sat under the hard floor (or the hour's budget was spent) every read
        # was refused AND nothing was ever shed again: the one state that most needs space was the one that never freed
        # any. Only the picture WRITE is refused now; the eviction and the reel reaper below still run, under the same
        # evidence shield. [[the-unjoined-end]]
        _out = fid
        if _pmode == "refuse":
            try:
                import read_pictures as _rpr
                _rpr.record_refusal(HIST_DIR, fid, _pwhy, _pfree, SESSION_ID)
            except Exception:
                pass
            _out = ""
        if _out:
            _px, _pq = (HIST_MAX_PX, 82)
            if _pmode == "small":
                try:
                    import read_pictures as _rps
                    _px, _pq = (_rps.FLOOR_MAX_PX, _rps.FLOOR_JPEG_Q)
                except Exception:
                    pass
            dest = os.path.join(HIST_DIR, fid + ".jpg")
            src = os.path.abspath(src_path) if src_path else ""
            ok = False
            if src and os.path.isfile(src):
                # Prefer full capture → HIST_MAX_PX JPEG for human eyes (AI path stays 1568 via _readable_frame)
                if src.lower().endswith((".bmp", ".png", ".jpg", ".jpeg")):
                    ok = _to_jpeg(src, dest, max_px=_px, quality=_pq)
                if not ok:
                    # portable fallback #1: the vision JPEG (already converted+downscaled)
                    jp = os.path.join(FRAMES, "read.jpg")
                    if _is_real_jpeg(jp):
                        import shutil
                        shutil.copy2(jp, dest)
                        ok = _is_real_jpeg(dest)
                if not ok:
                    # portable fallback #2: capture film eye (always real JPEG from capture_win)
                    eye = os.path.join(FRAMES, "eye.jpg")
                    if _is_real_jpeg(eye):
                        import shutil
                        shutil.copy2(eye, dest)
                        ok = _is_real_jpeg(dest)
                if not ok:
                    # portable fallback #3: live.png → JPEG convert (Windows capture twin)
                    png = os.path.join(FRAMES, "live.png")
                    if os.path.isfile(png):
                        ok = _to_jpeg(png, dest, max_px=_px, quality=_pq)
                if not ok:
                    # last resort: raw copy ONLY if source is already JPEG; never plant BMP as .jpg
                    if _is_real_jpeg(src):
                        try:
                            import shutil
                            shutil.copy2(src, dest)
                            ok = _is_real_jpeg(dest)
                        except Exception:
                            ok = False
                    elif src.lower().endswith(".png") and os.path.isfile(src):
                        # PNG body behind .jpg name still renders in browsers (legacy v755.3)
                        try:
                            import shutil
                            shutil.copy2(src, dest)
                            ok = os.path.isfile(dest) and os.path.getsize(dest) > 32
                        except Exception:
                            ok = False
            if not ok:
                return ""
            if _pmode == "small":
                # the budget's own ledger: what a floor-time picture cost, so the next one can be refused honestly
                try:
                    import read_pictures as _rpb
                    _mb = os.path.getsize(dest) / 1e6
                    with open(os.path.join(_rpb.root_of(HIST_DIR), _rpb.REFUSALS), "a", encoding="utf-8") as _fhb:
                        _fhb.write(json.dumps({"ts": int(time.time() * 1000), "frameId": fid, "why": "saved-small",
                                               "mb": round(_mb, 3), "freeGb": round(float(_pfree or 0), 2),
                                               "session": SESSION_ID}) + "\n")
                except Exception:
                    pass
        # v877 (army #6) — the eviction below only ever ACTS when free < MIN_FREE_GB; skip the
        # whole 30k-file listing + mtime sort + journal-shield load when the disk is healthy.
        try:
            import shutil as _shq
            if _disk_free_bytes(HIST_DIR) / 1e9 >= MIN_FREE_GB \
                    and time.time() < globals().get("_ORPHAN_DUE", 0.0):
                return _out   # healthy disk + orphans swept recently → skip the 30k-file walk
            globals()["_ORPHAN_DUE"] = time.time() + 600.0   # full sweep at most every 10min
        except Exception:
            pass
        # prune oldest beyond HIST_KEEP — and beyond the TV_HIST_MB disk ceiling (v753)
        # v813 (Grok R8 #7) — ONE budget: theatre derivative caches (cache1280/cache160) are
        # counted in the ceiling AND deleted with their source frame — no more disk lie.
        try:
            files = [os.path.join(HIST_DIR, f) for f in os.listdir(HIST_DIR)
                     if f.lower().endswith(".jpg")]
            files.sort(key=lambda p: os.path.getmtime(p))
            cache_dirs = [os.path.join(HIST_DIR, d) for d in ("cache1280", "cache160")
                          if os.path.isdir(os.path.join(HIST_DIR, d))]
            def _twins(src):
                b = os.path.basename(src)
                return [os.path.join(cd, b) for cd in cache_dirs]
            def _size_all(src):
                t = 0
                for f in [src] + _twins(src):
                    try: t += os.path.getsize(f)
                    except Exception: pass
                return t
            # v826 — footage frames (f_*.jpg) have their OWN count cap
            read_files = [f for f in files if not os.path.basename(f).startswith("f_")]
            foot_files = [f for f in files if os.path.basename(f).startswith("f_")]
            # v840 — journal shield: never delete a read frame still named in sessions.jsonl
            protected = _journal_frame_ids()
            # v861.1 (Konyo: 'so much smarter without a cap — it's locally stored') — COUNT CAPS
            # ABOLISHED. The one governor is FREE DISK: evict only when under MIN_FREE_GB,
            # footage first (oldest→newest), then oldest UNPROTECTED reads. Every frame that
            # fits on disk LIVES. Journal-named frames stay shielded.
            doomed = set()
            _shield, _ev_spared = set(protected), 0     # H2 — widened with the cited frames once the authority answers
            unprotected = [f for f in read_files if os.path.basename(f) not in protected]
            try:
                import shutil as _shu
                free_gb = _disk_free_bytes(HIST_DIR) / 1e9
            except Exception:
                free_gb = 999
            try:
                _over = _hist_over_cap(HIST_DIR)
            except Exception:
                _over = 0
            if _over:
                _dbg("hist over its %sGB cap by %dMB - shedding oldest under the same shields as the floor"
                     % (HIST_CAP_GB, _over >> 20))
            if free_gb < MIN_FREE_GB or _over:
                # v883 — REELS DIE WHOLE, LAST: if loose shedding still can't breathe, retire
                # the OLDEST sealed reels in one piece (a run keeps its full video or is gone —
                # never a half-eaten reel).
                # ⚠⚠ v2639 — THIS BLOCK DELETED A WHOLE REEL WITH NOTHING ASKED AND NOTHING SAID.
                # Measured 2026-09-05. The comment above promises "the OLDEST *sealed* reels", and
                # the word "sealed" appeared ONLY in that comment — there was no seal check, no
                # witness check, no retention call and no tombstone. `TV_AUTO_PRUNE` occurs ZERO
                # times in this file, so "the prune stays OFF" never reached here: this path is
                # armed and needs no switch. `ignore_errors=True` inside `except: pass` made a
                # partial or failed delete silent, and `sorted()` is LEXICOGRAPHIC, so "oldest"
                # held only while every name kept the same shape.
                #
                # AND IT WAS ABOUT TO TAKE EVIDENCE. `vault_accum.json` cites 4 sessions as
                # witnesses; 2 are already gone (his ruling: *"whats in the past is the past"*),
                # and of the 2 still on disk one is `reel_s_1784984019250_95276` — the OLDEST reel
                # on the shelf, i.e. exactly `reels[0]`. The next time free space crossed the
                # floor, the first reel deleted would have been the one the vault still cites for
                # "Chaotic Grand Charm". [[the-unjoined-end]] [[unknown-stays-unknown]]
                #
                # THE EMERGENCY IS KEPT. A full disk stops recording entirely, which is worse than
                # losing a reel — so this still reaps, it simply refuses to reap EVIDENCE, and it
                # says what it did either way.
                _ev = None      # H2 — asked once, below; None = COULD NOT ASK, and every shed under it refuses
                try:
                    # 2026-09-28 — (c) THE ONE AUTHORITY, not one ledger. It asked vault_accum.json's witness
                    # sessions only, and took reel_s_1786385768689_67392, whose frames chron_evidence cites.
                    # _reel_evidence = frame_authority.witness_index (sessions · frames · cited) + chron_evidence.
                    _ev = _reel_evidence()
                    _all = [d2 for d2 in os.listdir(HIST_DIR) if d2.startswith("reel_")]
                    # ⚠⚠ THE REEL'S OWN CLOCK, and an UNREADABLE clock sorts LAST, not first.
                    # `_reel_capture_ms` answers 0 when a name carries no 13-digit stamp, and a
                    # bare `key=_reel_capture_ms` would put every un-datable reel at the FRONT —
                    # making the reel we know least about the preferred victim. Caught by this
                    # fix's own test. Same rule as the router's FIFO queue, pointing the other
                    # way: unknown never jumps the queue, in either direction.
                    _all.sort(key=lambda _r: (_reel_capture_ms(_r) == 0, _reel_capture_ms(_r)))
                    # loose pool empty → a whole reel may go. Over the size CAP, the pool counts only footage older than the
                    # youth shield: the session being recorded always has young loose frames, and they must not
                    # keep the cap from ever reaching a sealed reel.
                    _old_cut = time.time() - 900.0
                    _pool = [x for x in foot_files if not _over or os.path.getmtime(x) < _old_cut]
                    if len(_all) > 2 and not _pool:
                        if _ev is None:
                            # ⚠ COULD NOT ASK is not "nothing is cited". Refuse and be loud.
                            _dbg("reel-reap REFUSED: the evidence authority (frame_authority's witness "
                                 "index and chron_evidence) would not answer, so whether any reel holds "
                                 "evidence is UNKNOWN")
                        else:
                            # never the two newest; never a cited picture; a reel a law pins (test_reel_refs.json)
                            # only when nothing else may go (REG-1361) - one chooser, the evidence-aware pick
                            _pick = _reel_reap_pick(HIST_DIR, _all[:-2], _ev, _test_pinned_reels(),
                                                    river=_river_positions())
                            _rv = None if _pick is None else {"station": _pick.get("station"),
                                                              "readOwed": _pick.get("readOwed")}
                            if _pick is not None and _pick.get("readOwed"):
                                _dbg("reel-reap: no reel the river has finished may go - taking %s, which the river "
                                     "has at %s (a read is still owed), because a full disk stops recording"
                                     % (_pick["reel"], _pick.get("station") or "no stamp at all"))
                            elif _pick is not None and _pick.get("readOwed") is None:
                                _dbg("reel-reap: the river's stamp store could not be asked, so whether %s still owes "
                                     "a read is UNKNOWN - oldest first, as before" % _pick["reel"])
                            if _pick is not None and _pick.get("pinned"):
                                _dbg("reel-reap: every reel it may take is pinned by a law - taking the oldest "
                                     "pinned one, because a full disk stops recording")
                            if _pick is None:
                                _dbg("reel-reap found NOTHING it may take: %d reel(s), every "
                                     "candidate holds only cited pictures, is cited whole, or is one of "
                                     "the two newest. Disk stays tight; no evidence was destroyed."
                                     % len(_all))
                            elif _pick["mode"] == "whole":
                                import shutil as _shr
                                _vp = os.path.join(HIST_DIR, _pick["reel"])
                                _n = _pick["frames"]
                                _shr.rmtree(_vp, ignore_errors=True)
                                _gone = not os.path.exists(_vp)
                                _reap_record(_pick["reel"], _n, _gone, len(_all), names=_pick["gone"], river=_rv)
                                _dbg("reel-reap took %s (%s frame(s)) under the disk floor; "
                                     "removed=%s" % (_pick["reel"], _n, _gone))
                            else:
                                # the evidence pictures STAY; the rest of the reel goes — the shape
                                # reel_retention.release_uncited uses when retention releases a reel
                                _vp = os.path.join(HIST_DIR, _pick["reel"])
                                _took = []
                                for _f in _pick["gone"]:
                                    try:
                                        os.remove(os.path.join(_vp, _f))
                                        _took.append(_f)
                                    except OSError:
                                        _dbg("reel-reap could not release %s/%s" % (_pick["reel"], _f))
                                _reap_record(_pick["reel"], len(_took), bool(_took), len(_all),
                                             names=_took, kept=_pick["kept"], river=_rv)
                                _dbg("reel-reap released %d frame(s) of %s and KEPT its %d cited picture(s)"
                                     % (len(_took), _pick["reel"], len(_pick["kept"])))
                except Exception as _e:
                    # ⚠ NOT `pass`. A reaper that fails silently is indistinguishable from one
                    # that had nothing to do, and that ambiguity is how this went unseen.
                    try:
                        _dbg("reel-reap raised and did nothing: %s" % str(_e)[:160])
                    except Exception:
                        pass
                # v873 (THE 4GB NIGHT) — YOUTH SHIELD: an emergency may NEVER eat the session
                # being recorded. Frames younger than 15min survive every shed; old sessions
                # die first. If everything is young, we shed nothing and the DISK FULL fault
                # (v872.1) tells Konyo the truth instead of silently chewing his recording.
                _young_cut = time.time() - 900.0
                def _is_old(_f):
                    try:
                        return os.path.getmtime(_f) < _young_cut
                    except Exception:
                        return True
                # ⚠⚠ H2 (review of 77d8d8b5, reproduced) — THIS SHED WAS THE THIRD DELETER AND IT NEVER ASKED.
                # (b) and (c) above were taught to spare a read-bearing or cited picture; this loop, one screen below
                # them, still took loose f_*.jpg under the floor on age alone — and the belt beneath it EXEMPTED f_
                # names from its own journal check, so a frame chron_evidence cites could go here and nothing said so.
                # Now it asks the SAME shield _reap_loose_film asks (the journal's read frames | the evidence
                # authority's cited frames); an authority that cannot answer sheds NOTHING (None = refuse, never
                # "nothing is cited"); and what it takes is recorded by name, so the doctor can say who took a picture.
                # [[the-unjoined-end]] [[unknown-stays-unknown]]
                if _ev is None:
                    _dbg("read-eviction REFUSED: the evidence authority would not answer, so whether any loose "
                         "picture is cited is UNKNOWN — nothing shed, the disk stays tight")
                else:
                    _shield = set(protected) | set(_ev.get("frames") or ())
                    need = max((MIN_FREE_GB - free_gb) * 1e9, _over)
                    freed = 0
                    for f in [x for x in foot_files if _is_old(x)] + [x for x in unprotected if _is_old(x)]:
                        if freed >= need:
                            break
                        if os.path.basename(f) in _shield:
                            _ev_spared += 1
                            continue
                        freed += _size_all(f)
                        doomed.add(f)
            _ev_took = []
            for old in doomed:
                if os.path.basename(old) in _shield:
                    continue  # belt: never unlink a read-bearing or cited picture — f_ names included (H2)
                for f in [old] + _twins(old):
                    try: os.remove(f)
                    except Exception: pass
                if not os.path.exists(old):
                    _ev_took.append(os.path.basename(old))
            if _ev_took or _ev_spared:
                _reap_record("loose", len(_ev_took), bool(_ev_took), -1, by="recorder-read-eviction",
                             names=_ev_took, spared=_ev_spared)
                _dbg("read-eviction took %d picture(s) under the floor, spared %d read-bearing or cited"
                     % (len(_ev_took), _ev_spared))
            # orphan derivatives (source already gone) die too
            keep = {os.path.basename(f) for f in files if f not in doomed}
            keep |= protected
            for cd in cache_dirs:
                for f in os.listdir(cd):
                    if f.lower().endswith(".jpg") and f not in keep:
                        try: os.remove(os.path.join(cd, f))
                        except Exception: pass
        except Exception:
            pass
        return _out
    except Exception:
        return ""

def _resolve_read_ts(cap_ts_override=None):
    """v1187 — captureTs join law: the timestamp stamped into a read's frame_id/captureTs must
    be the FRAME's actual capture clock, never the moment a caller got around to reading it
    (same law as the intake-result A0 fix above: 'retro joins on captureTs, never receipt
    time'). A queue/backlog drain (_fire_read's settle-queue / text-eye-sweep-* origins) reads
    a snapshot captured EARLIER — held while readers were busy, up to SETTLE_QUEUE_STALE_MS —
    so it must pass that entry's own tracked capture clock as cap_ts_override. A fresh/live read
    has no earlier clock to report, so it falls back to now()."""
    return int(cap_ts_override) if cap_ts_override else int(time.time() * 1000)


def frame_path_for_id(fid):
    """Resolve hist id → absolute path, or '' if missing/unsafe."""
    safe = str(fid or "").strip()
    if not safe or not all(c.isdigit() or c == "_" for c in safe):
        return ""
    p = os.path.join(HIST_DIR, safe + ".jpg")
    return p if os.path.isfile(p) else ""


# ═══ v713 — PERSISTENT VISION WORKER (the SPEED fix). One long-lived claude session in
# stream-json mode: each frame is a TURN, not a cold start (live run #1: cold starts + a
# broken transport = 180s hangs). The worker restarts itself every N turns so conversation
# context never bloats a read, and ANY wobble (timeout · dead process · bad JSON) kills it
# and falls back to the one-shot path. TV_CLAUDE_BIN overrides the binary — the TDD seam
# (tests run a fake bin that speaks stream-json).
CLAUDE_BIN = os.environ.get("TV_CLAUDE_BIN", "claude")
try:
    import shutil as _shw
    CLAUDE_BIN = _shw.which(CLAUDE_BIN) or CLAUDE_BIN   # v877 — resolves claude.cmd on Windows npm installs
except Exception:
    pass
WORKER_MAX_TURNS = 8
# v723/v725 — SPEED + GENIUS LADDER (subscription only):
#   LIVE RUN #3 finding: Haiku warm was 13–16s; Sonnet warm was 6–10s — economics flipped.
#   FAST_MODEL default is now SONNET (felt speed). Haiku remains opt-in via TV_MODEL=haiku.
#   GENIUS escalate only fires when FAST != GENIUS (e.g. haiku→sonnet experiments).
# Override: TV_MODEL=sonnet|haiku  TV_MODEL_ESCALATE=sonnet  TV_ESCALATE_CAP=40
FAST_MODEL = os.environ.get("TV_MODEL", "sonnet").strip() or "sonnet"
GENIUS_MODEL = os.environ.get("TV_MODEL_ESCALATE", "sonnet").strip() or "sonnet"
try:
    ESCALATE_CAP = max(0, int(os.environ.get("TV_ESCALATE_CAP", "40")))
except Exception:
    ESCALATE_CAP = 40
_ESCALATE_N = [0]

# v948.17 — Grok P1-5 (2026-07-21 fast-run soak): claude_read()'s warm ask() used the
# VisionWorker default (timeout=75) and its one-shot fallback used 90s — a single frame
# (a scene-transition still) legitimately took 68,978ms and, with POOL_N=1 outside robot
# mode, that one read holds the ENTIRE live lane hostage (no new live read, no idle-gap
# second-eye sweep) for up to 75+90=165s worst case. Per the Master Brain law ("a 66s live
# stall is a signal to route to retro, not a failure" — ENGINE_ARCHITECTURE.md §Master Brain
# law a), cap a single live read's in-flight time much tighter: every named read this soak
# finished in 9-15s, so a generous-but-bounded ceiling lets the lane free up and hand the
# frame to the retro/KAI layers instead of blocking on an outlier. TV_LIVE_READ_TIMEOUT_S
# overrides for tuning; genius-escalate (a secondary, capped, optional pass) is untouched.
try:
    LIVE_READ_TIMEOUT_S = max(5.0, float(os.environ.get("TV_LIVE_READ_TIMEOUT_S", "35") or 35))
except Exception:
    LIVE_READ_TIMEOUT_S = 35.0

# v720 — AUTH PATH FIX (live run #2): if ANTHROPIC_API_KEY (or sibling API tokens) is set in
# the shell, every headless `claude -p` prefers that key over the user's Claude subscription
# login. A dead/rate-limited key hangs past 40–90s with empty stdout — exactly run #2's
# warm + oneshot timeouts. Strip API-key auth so vision rides the *logged-in* claude plan
# (the product contract: "your subscription, not API keys"). Keep OAuth tokens if present.
# v879 (army §2) — EVERY helper subprocess yields to the game. Mac/Linux: nice(10) via
# preexec_fn. Windows: BELOW_NORMAL_PRIORITY_CLASS folded into creationflags.
if sys.platform == "win32":
    NICE_KW = {"creationflags": 0x4000}   # BELOW_NORMAL_PRIORITY_CLASS
else:
    NICE_KW = {"preexec_fn": (lambda: os.nice(10))}

_API_AUTH_ENV = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")
def _claude_env():
    """Env for vision subprocesses: subscription login, not shell API keys."""
    env = os.environ.copy()
    stripped = [k for k in _API_AUTH_ENV if env.pop(k, None) is not None]
    # v1379 — agent-teams auto mode must never ride vision children (subscription burn)
    env.pop("CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS", None)
    return env, stripped

def _log_auth_once(stripped):
    if not stripped or globals().get("_AUTH_LOGGED"):
        return
    globals()["_AUTH_LOGGED"] = True
    ev("boot", f"vision auth: stripped {','.join(stripped)} — using Claude subscription login")

# v1379 LEAK FIX — every cold/warm `claude -p` used to inherit cwd=d2r_bible_tests + full
# project settings (CLAUDE.md, agent teams, high effort). Each screenshot became a
# ~1.3MB Claude Code session with 20k+ cache tokens. Lean args skip project context, do
# not persist sessions, keep effort low, and ALWAYS pin --model so the global Claude
# default (fable in ~/.claude/settings.json) never hijacks vision. Product model = sonnet.
# Auth stays subscription OAuth (not --bare).
_VISION_CWD = os.environ.get("TV_VISION_CWD") or os.path.join(tempfile.gettempdir(), "tvd-vision-cwd")
try:
    os.makedirs(_VISION_CWD, exist_ok=True)
except Exception:
    _VISION_CWD = tempfile.gettempdir()

def _vision_model(model=None):
    """Pin vision to sonnet (product). Never allow empty/fable to inherit user settings."""
    m = str(model or FAST_MODEL or "sonnet").strip() or "sonnet"
    lo = m.lower()
    if "fable" in lo:
        return "sonnet"
    return m

def _argv_seam(env_name, default):
    """v1461 — optional JSON-list override for a spawn's argv PREFIX. Unset => `default`.

    TV_CLAUDE_BIN / TV_OCR_BIN hold a single executable PATH, which cannot express "run this
    script under THIS interpreter". The suites' fakes are .py files: on the Mac a shebang
    makes them directly executable, but on Windows a bare .py is not a valid CreateProcess
    image ([WinError 193] %1 is not a valid Win32 application), so every fake-worker test
    failed there. Wrapping the fake in a .cmd is NOT a fix: it inserts an extra process that
    survives p.kill(), leaving the real child orphaned on the pipe — which is precisely the
    leak the v1204/v1206 shutdown tests exist to catch, and it hangs them.

    So allow the prefix itself to be a list, exactly as _ocr_worker_cmd already does for the
    Windows OCR lane (powershell + .ps1). Production never sets these, so behaviour is
    byte-identical; only the suites do.
    """
    raw = os.environ.get(env_name)
    if raw:
        try:
            v = json.loads(raw)
            if isinstance(v, list) and v:
                return [str(x) for x in v]
        except Exception:
            pass
    return list(default)


def _claude_lean_args(model, *, stream=False, add_dirs=None):
    """CLI argv for vision/intake calls that must not load the monorepo project."""
    args = _argv_seam("TV_CLAUDE_ARGV", [CLAUDE_BIN]) + ["-p"]
    if stream:
        args += ["--input-format", "stream-json", "--output-format", "stream-json", "--verbose"]
    else:
        args += ["--output-format", "text"]
    args += [
        "--model", _vision_model(model),
        "--allowedTools", "Read",
        "--strict-mcp-config",
        "--no-session-persistence",
        "--setting-sources", "user",
        "--effort", os.environ.get("TV_VISION_EFFORT", "low") or "low",
    ]
    for d in (add_dirs or []):
        if d and os.path.isdir(d):
            args += ["--add-dir", d]
    return args

# v1379 — hard subscription circuit breaker for cold oneshots + warm budget log.
# Armed only for REAL claude CLI vision — never for TV_STUB / fake_claude (tests would
# burn the hourly cap on themselves and return None without spawning a worker).
def _sub_budget_path():
    """Where the subscription meter lives — and never HIS meter when the world is a fixture.

    v1869 — MEASURED: one full 32-gate run spends ONE REAL VISION CALL against his subscription and
    writes it into this file. Every push runs those gates, so every push quietly bought a read he
    did not ask for. Small; unasked; and the meter is the one thing that must describe his account
    and nothing else.

    Same rule as the journal (v1867), for the same reason: a caller that isolates TV_HIST has said
    "this is not his world", and a meter counting reads made in a fixture is not a meter of his
    account. TV_SUB_BUDGET wins when named explicitly. [[feedback-fixtures-never-touch-live-data]]
    """
    explicit = os.environ.get("TV_SUB_BUDGET")
    if explicit:
        return explicit
    # ⚠⚠ v2937 — CALL THE ONE RESOLVER; DO NOT RE-IMPLEMENT IT. This carried its own copy of the
    # rule, so v2932's narrowing (blank or relative TV_HIST is not a request for isolation) reached
    # `_fixture_root` and never reached here. MEASURED from the repo root with TV_HIST="   ":
    # this returned `<repo>/   /.subscription_budget.json` — the exact REG-937 harm, still live, beside the two
    # lines that ship changed. `_log_root` already records this shape: v2783/v2785 fixed one copy
    # and neither swept to the other. Caught by the cross-family eye on v2932. [[copy-drift]]
    return os.path.join(_fixture_root(HERE), ".subscription_budget.json")


_SUB_BUDGET_PATH = _sub_budget_path()
# v1777 — THE CAPS WERE SIZED FOR A LIVE SESSION, NOT FOR READING HIS FOOTAGE BACK.
# 60/hour and 250/day fit a farm session sipping the odd frame. A Chronicle catch-up is the opposite
# shape: ONE reel of his thorough scroll is ~290 pages, so the very first honest sweep could not fit
# inside a day's allowance — and because a capped read used to answer scene='gameplay' instead of
# refusing (fixed below), it looked like his footage was empty rather than like the meter was full.
# Measured tonight: 250/250 at 01:00, every read returning in 0.0s with nothing, for hours.
#
# Raised to 4000/hour and 20000/day. These are OUR OWN guard rails, not Anthropic's — they exist so
# a runaway loop cannot spend his subscription unattended, and that job is done just as well by a
# number that does not also block the one workload the feature exists for. The REAL pace limit is
# the throttle detector (_note_slot_death), which watches actual worker deaths and is untouched.
try:
    _SUB_HOURLY_MAX = max(0, int(os.environ.get("TV_VISION_HOURLY_MAX", "4000") or 4000))
except Exception:
    _SUB_HOURLY_MAX = 4000
try:
    _SUB_DAILY_MAX = max(0, int(os.environ.get("TV_VISION_DAILY_MAX", "20000") or 20000))
except Exception:
    _SUB_DAILY_MAX = 20000
_sub_budget_lock = threading.Lock()


def _sub_budget_load():
    """v1472 — read the subscription-budget file WITHOUT leaking a handle.

    The two call sites used a bare `open(...).read()`, which relies on refcount GC to close.
    This runs on every vision read, so during a long farm session it churns thousands of
    handles — and on Windows an open handle also blocks replacing the file underneath it.
    """
    try:
        if not os.path.isfile(_SUB_BUDGET_PATH):
            return {}
        with open(_SUB_BUDGET_PATH, encoding="utf-8") as fh:
            return json.loads(fh.read()) or {}
    except Exception:
        return {}

def _vision_budget_armed():
    """True only when a real subscription-costing Claude binary is in play.

    v1463 — judge the argv that is ACTUALLY SPAWNED, not just CLAUDE_BIN. v1461 added the
    TV_CLAUDE_ARGV seam, which decides the real command, while this guard still read only
    CLAUDE_BIN's basename — so the two could disagree: TV_CLAUDE_BIN=.../fake_claude.py with
    TV_CLAUDE_ARGV=["claude"] disarmed the hourly/daily subscription cap while every spawn was
    the real CLI burning real quota. Fail SAFE: the circuit stays armed unless the thing being
    executed is genuinely a fake.
    """
    if os.environ.get("TV_STUB") or os.environ.get("TV_NO_BUDGET") == "1":
        return False
    try:
        argv = _argv_seam("TV_CLAUDE_ARGV", [CLAUDE_BIN])
    except Exception:
        argv = [CLAUDE_BIN]
    try:
        blob = " ".join(os.path.basename(str(a or "")).lower() for a in argv)
    except Exception:
        blob = ""
    if "fake_claude" in blob:
        return False
    return True

def _sub_budget_calls(st, now, as_written=False):
    """The call timestamps that still count, in SECONDS, with nonsense dropped.

    v1868 — HIS LIVE BUDGET FILE HELD A MILLISECOND TIMESTAMP AMONG SECONDS. Measured:
    1787177667153.0 sitting in `calls` beside 404 ordinary seconds-scale entries. Both filters here
    are written as `now - t < WINDOW`, and for a value ~55,000 years in the future that difference
    is hugely NEGATIVE — so it passes every window, forever. One permanent slot off the hourly cap
    AND the daily cap, invisible, and it can never age out on its own.

    Harmless at 4000/hour and 20000/day; not harmless as a mechanism, and not new — this is the same
    unit collision already recorded against the G5 lane. A meter that cannot be corrected by the
    passage of time is a meter that only ever goes one way.

    So: a value that looks like milliseconds IS milliseconds (nothing in 2026 is 1.7e12 seconds), a
    value in the future beyond a minute of clock skew is dropped rather than trusted, and the window
    is a two-sided one — `0 <= now - t < WINDOW` — because "not older than a day" and "not in the
    future" are two conditions and the one-sided test only ever checked one of them.
    [[d2r-g5-budget-unit-collision]] [[unknown-stays-unknown]]

    REG-2387 — as_written=True returns the SAME rows in the unit their writer used, for the one caller that writes
    them back (_sub_budget_record). The millisecond rows have a writer: tv/intake_local.mjs records every intake read
    here as Date.now() and counts only millisecond rows against its own cap. Written back divided by 1000, they were
    rows that cap no longer counts, so ONE vision read reset the intake cap (reproduced on a fixture: 20 intake rows,
    the 21st read refused 429; one vision read recorded; the 21st admitted). Which rows count is decided here, in
    seconds, either way.
    """
    out = []
    for raw in (st.get("calls") or []):
        try:
            t = float(raw)
        except Exception:
            continue
        v = t                   # REG-2387 — the row as its writer wrote it
        if t > 1e12:            # milliseconds, written by something that used a different clock
            t = t / 1000.0
        if t > now + 60:        # beyond clock skew: a timestamp we cannot place, not a call
            continue
        if now - t < 86400:
            out.append(v if as_written else t)
    return out


def _sub_budget_check(kind="vision"):
    """Return None if allowed, else a short reason string (circuit open)."""
    if not _vision_budget_armed():
        return None
    if _SUB_HOURLY_MAX <= 0 or _SUB_DAILY_MAX <= 0:
        return "subscription circuit open (TV_VISION_*_MAX=0)"
    now = time.time()
    with _sub_budget_lock:
        try:
            st = _sub_budget_load()   # v1472 — was a bare open().read(); the vision lane hits this
                                      # on EVERY read, so the leaked handle recurred per frame
        except Exception:
            st = {}
        calls = _sub_budget_calls(st, now)
        hour = [t for t in calls if now - t < 3600]
        if len(hour) >= _SUB_HOURLY_MAX:
            return "subscription hourly cap %d/%d (%s)" % (len(hour), _SUB_HOURLY_MAX, kind)
        if len(calls) >= _SUB_DAILY_MAX:
            return "subscription daily cap %d/%d (%s)" % (len(calls), _SUB_DAILY_MAX, kind)
        return None

def _sub_budget_record():
    if not _vision_budget_armed():
        return
    now = time.time()
    with _sub_budget_lock:
        try:
            st = _sub_budget_load()   # v1472 — was a bare open().read(); the vision lane hits this
                                      # on EVERY read, so the leaked handle recurred per frame
        except Exception:
            st = {}
        # v1868 — the WINDOW applies on write too, or a row that can never age out is rewritten every time a read is
        # recorded. REG-2387 — but each row goes back in the unit its writer used: the intake lane's millisecond rows
        # stay milliseconds, or one vision read resets the intake cap (see _sub_budget_calls).
        calls = _sub_budget_calls(st, now, as_written=True)
        calls.append(now)
        try:
            # v1779 — ATOMIC, because a torn write here silently DISARMS the circuit breaker.
            # _sub_budget_load returns {} on any parse failure, so a half-written file makes the
            # cap restart from zero with no message anywhere — the guard protecting his account
            # fails OPEN. The file is rewritten on every vision read and holds up to _SUB_DAILY_MAX
            # timestamps, so an interrupted sweep is a realistic way to get there. Every other state
            # file in this lane already uses tmp+replace; this one was missed. Found by review.
            _tmp = _SUB_BUDGET_PATH + ".tmp"
            with open(_tmp, "w", encoding="utf-8") as _bf:
                _bf.write(json.dumps({"calls": calls, "last": now}))
                _bf.flush()
                try:
                    os.fsync(_bf.fileno())
                except Exception:
                    pass
            os.replace(_tmp, _SUB_BUDGET_PATH)
        except Exception:
            pass


# ⚠⚠ REG-1300 — THE WRITE TO A WARM WORKER IS BOUNDED TOO, AND ITS DEADLINE STARTS BEFORE IT.
# v3391 fixed exactly this in control_app._ocr_ask and left its two twins here: VisionWorker.ask
# and OcrWorker.read both did `self.p.stdin.write(...); flush()` and only THEN computed the
# deadline their docstrings promise. A blocking write does not raise, so the try/except around it
# could never fire, and a worker that stops draining its stdin held the caller - the whole vision
# or OCR lane - for ever, with a bound that had not started. The "a worker read has a deadline"
# doctor row named both lines (tv_diablo.py:3614, :4428) on the Mac AND the ALT, 2026-09-25.
# ⚠ Moving the `deadline =` line above the write turns that row green and bounds NOTHING - the row
# grades ORDER because order is what it can see; the write itself is what has to be bounded.
# [[copy-drift]] [[the-unjoined-end]]
def _pipe_write_by(proc, data, deadline):
    """Write + flush `data` to proc.stdin on a helper thread; True only if it landed before
    `deadline` (time.monotonic()). False means the worker is not draining its input: the caller
    must abandon it (_bury_worker), because the abandoned write may still land later and pair a
    stale request with the next reply."""
    import queue as _q
    done = _q.Queue()

    def _send():
        try:
            proc.stdin.write(data)
            proc.stdin.flush()
            done.put(True)
        except Exception:
            done.put(False)

    try:
        threading.Thread(target=_send, daemon=True, name="worker-send").start()
        return done.get(timeout=max(0.05, deadline - time.monotonic())) is True
    except Exception:
        return False


def _bury_worker(p, role=None):
    """Kill a worker whose write never landed and close its pipes OFF the caller's thread.

    stop() closes stdin on the caller's thread, and closing a stream another thread is still
    blocked writing to waits on that writer's lock - so a child whose pipe outlives it (a
    grandchild holding the read end) would move the hang into stop() instead of ending it.

    #83 — with a `role`, the door ends the WHOLE tree first (job / process group) and forgets the
    role: `p.kill()` alone ended a deaf claude's head and left its node helpers - the very grandchild
    holding the read end that the paragraph above is about. The wait below still reaps the head."""
    if not p:
        return
    ended = False
    if role:
        try:
            _child_guard.end(role, proc=p, wait_s=0)
            ended = True
        except Exception:
            ended = False
    if not ended:
        try:
            p.kill()
        except Exception:
            pass

    def _bury(pr):
        try:
            pr.wait()
        except Exception:
            pass
        for stream in (pr.stdin, pr.stdout, pr.stderr):
            try:
                if stream:
                    stream.close()
            except Exception:
                pass

    try:
        threading.Thread(target=_bury, args=(p,), daemon=True, name="bury-deaf-worker").start()
    except Exception:
        pass


_VISION_ROLE_N = [0]     # #83 — each VisionWorker without a name takes the next "vision-r<n>" role


def _stop_worker_process(role, p, wait_s=2.0):
    """#83 — ONE stop for both worker classes. The door ends the WHOLE tree (job / process group), waits `wait_s`
    for it, and hands a survivor to a reaper thread; then the pipes are closed.

    v2352's lesson lives inside the door now: a swallowed wait() timeout was a zombie for ever (20 <defunct>
    children after 20 h, measured), and the block that fixed it existed TWICE, in two worker classes, and both
    leaked. [[copy-drift]] — one routine, one home."""
    try:
        _child_guard.end(role, proc=p, wait_s=wait_s)
    except Exception:
        pass
    for stream in (p.stdin, p.stdout, p.stderr):
        try:
            if stream:
                stream.close()
        except Exception:
            pass


class VisionWorker:
    def __init__(self, model=None, role=None):
        # v720.1 — lock: warm thread + settle-read must never interleave on one stream
        self.model = model or FAST_MODEL
        self.p = None; self.q = None; self.turns = 0; self.lock = threading.Lock()
        # #83 — the ROLE this worker's claude holds at the child_guard door: one process per role, ever. The pool's
        # readers are vision-r0..vision-r<n>; the stall-drain reader names itself vision-stall.
        if role is None:
            role = "vision-r%d" % _VISION_ROLE_N[0]
            _VISION_ROLE_N[0] += 1
        self.role = role
    def _spawn(self):
        import queue
        env, stripped = _claude_env()
        _log_auth_once(stripped)
        # Allow Read on frames + hist so absolute paths resolve even with empty vision cwd
        add = [FRAMES]
        hist = os.path.join(FRAMES, "hist")
        if os.path.isdir(hist):
            add.append(hist)
        # #83 — through the door: the role's previous claude (and every helper it spawned) is ended first, the new
        # one leads its own session (POSIX) or job (Windows), and the record says which pid this role holds.
        self.p = _child_guard.spawn(self.role,
            _claude_lean_args(self.model, stream=True, add_dirs=add),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8", errors="replace", bufsize=1, env=env, cwd=_VISION_CWD,
            preexec_fn=(None if sys.platform == "win32" else (lambda: os.nice(10))))   # v876 — D2R owns the CPU
        self.q = queue.Queue(); self.turns = 0
        def _pump(proc, q):
            try:
                for line in proc.stdout: q.put(line)
            except Exception: pass
            q.put(None)
        threading.Thread(target=_pump, args=(self.p, self.q), daemon=True).start()
    def stop(self):
        """Kill the warm claude child and close pipes (avoids ResourceWarning leaks)."""
        p = self.p
        self.p = None
        if not p:
            return
        _stop_worker_process(self.role, p)
    def ask(self, prompt, timeout=75):
        """one turn → the result text, or None (caller falls back to one-shot). Serialized."""
        blocked = _sub_budget_check("warm")
        if blocked:
            try:
                ev("cap", blocked)
            except Exception:
                pass
            return None
        with self.lock:
            try:
                if self.p is None or self.p.poll() is not None or self.turns >= WORKER_MAX_TURNS:
                    self.stop(); self._spawn()
                msg = {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": prompt}]}}
                # REG-1300 — the deadline starts BEFORE the write, and the write is bounded by it.
                deadline = time.monotonic() + timeout
                if not _pipe_write_by(self.p, json.dumps(msg) + "\n", deadline):
                    p, self.p = self.p, None
                    _bury_worker(p, role=self.role)     # not draining its input - never reuse it; #83 the whole tree
                    return None
                # v1200 — monotonic, not wall-clock: this deadline is the LITERAL enforcement of
                # LIVE_READ_TIMEOUT_S, the Master Brain law rounds 1-4 all protected from other
                # angles. time.time() can jump BACKWARD (NTP resync on sleep/wake — routine over
                # a multi-hour session, same class engine-capture just fixed in _film_loop
                # v1199); mid-read, that makes `deadline - time.time()` balloon to the size of
                # the jump, so `self.q.get(timeout=...)` blocks for however long the clock
                # jumped — reintroducing the exact "hang the entire live lane" failure this whole
                # arc exists to eliminate, in the ONE place that's supposed to guarantee it can't.
                # (REG-1300: `deadline` is now set above the write, on the same monotonic clock.)
                while time.monotonic() < deadline:
                    try: line = self.q.get(timeout=max(0.1, deadline - time.monotonic()))
                    except Exception: break
                    if line is None: break
                    line = line.strip()
                    if not line: continue
                    try: j = json.loads(line)
                    except Exception: continue
                    if j.get("type") == "result":
                        self.turns += 1
                        _sub_budget_record()
                        return j.get("result") or ""
                self.stop()   # timed out / stream ended — never reuse a wedged worker
                return None
            except Exception:
                self.stop()
                return None
_WORKER = VisionWorker()
# v782 — vision must NOT freeze the eye: capture loop keeps writing live.bmp/eye.jpg while
# Claude thinks. (Konyo: ON AIR + moving but film stuck on READING.)
_VISION_BUSY = False
_VISION_BUSY_AT = 0.0   # v789 — when the in-flight vision call started (stall detection)

# v863 (READER POOL) — up to POOL_N concurrent Claude vision readers with ORDERED APPLY.
# Each reader keeps its OWN warm VisionWorker (Popen/lock/turns/restart-at-8) and reads a
# PRIVATE snap/read file, so two readers never collide on snap.bmp/read.jpg. Completions are
# buffered by captureTs and applied only when no OLDER read is still in flight (the
# floor-before-stash lock). Worker 0 == _WORKER (the farewell / POOL_N=1 fast path).
# OWNER DEFAULT = 8 readers. MEMORY: each warm `claude -p` child is ~200-600MB, so a full
# pool of 8 can hold ~1.6-4.8GB resident — set TV_POOL lower on a tight machine. Fail-soft:
# a throttled/queued reader's ask() returns None → one-shot bridge + THAT slot rewarms; the
# slot is always released in finally, so a degraded reader shrinks effective capacity, never
# stalls the pool.
def _pool_default():
    """v900 — pool fits the MACHINE (Konyo: 4 workers made MacBook + CrossOver unplayable).
    ≤16GB → 2 · 17–31GB → 3 · ≥32GB → 4. TV_POOL always wins (max 6)."""
    gb = 0.0
    try:
        gb = float(os.environ.get("TV_POOL_ASSUME_GB", "") or 0)   # test hook
    except Exception:
        gb = 0.0
    if not gb:
        try:
            if sys.platform == "darwin":
                gb = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], timeout=3)) / 1e9
            else:
                gb = (os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")) / 1e9
        except Exception:
            gb = 16
    if gb >= 32:
        return 4
    if gb >= 20:
        return 3
    return 2


_TP_ENV = os.environ.get("TV_POOL", "").strip()
if ROBOT_MODE:
    POOL_N = max(1, min(6, int(_TP_ENV))) if _TP_ENV else max(1, min(6, _pool_default()))
else:
    # v901 Auto Intake: ONE Claude always. TV_POOL ignored unless TV_ROBOT=1 (Robot frozen).
    POOL_N = 1
ORDER_HOLD_MS = max(5000, int(os.environ.get("TV_ORDER_HOLD_MS", "20000" if not ROBOT_MODE else "45000") or 20000))
_WORKERS = [_WORKER] + [VisionWorker() for _ in range(max(0, POOL_N - 1))]
# #83 — tell the door how many live readers this agent may hold, so the console's census (which reads this
# agent's ledger) grades vision against POOL_N and not against the default ceiling of one.
try:
    _child_guard.expect("vision", 0, POOL_N)
except Exception:
    pass
_pool_lock = threading.Lock()
_pool_free = list(range(POOL_N))   # reader ids currently idle
_in_flight = {}                    # job_id -> {readerId, captureTs, sig, origin, startedAt}
_order_buf = []                    # heapq of (captureTs, seq, payload) awaiting ordered apply
_order_seq = [0]
_emit_lock = threading.Lock()
_job_seq = [0]


def _job_files(rid, n):
    """PRIVATE per-job capture + read paths — concurrent readers never share one snap/read file.

    v2324 — the snap takes its extension from the LIVE WRITE NAME rather than hardcoding .bmp.
    These files are copies of the live frame; naming a JPEG's bytes ".bmp" is the exact defect
    v1421 recorded on Windows ("the old portable fallback copied live.bmp bytes into a .jpg
    name"). Consumers match on the "snap_" prefix, never on the extension, so this is safe.
    """
    _ext = os.path.splitext(LIVE_FRAME_WRITE)[1] or ".jpg"
    return (os.path.join(FRAMES, "snap_%d_%d%s" % (int(rid), int(n), _ext)),
            os.path.join(FRAMES, "read_%d_%d.jpg" % (int(rid), int(n))))


def _vision_in_flight_n():
    with _pool_lock:
        return len(_in_flight)


def _vision_busy():
    """Compat shim for the old single-reader gate: True only when EVERY reader is busy."""
    return _vision_in_flight_n() >= POOL_N


def _heartbeat_cap():
    """v900 — lean concurrent heartbeats. Pool 2 machines stay at 1 in-flight heartbeat so
    Claude + capture never thrash D2R. Bigger pools can earn 2."""
    hi = max(1, POOL_N // 2)
    if _is_throttled():
        return 1
    fps = _foot_fps_now()
    cap_ms = globals().get("_FILM_CAP_MS") or 0
    if (fps is not None and fps < 0.6) or cap_ms > 800:
        return 1
    if POOL_N >= 3 and fps is not None and fps >= 0.9 and cap_ms < 250:
        return min(hi, 2)
    return 1


def _heartbeat_in_flight_n():
    with _pool_lock:
        return sum(1 for j in _in_flight.values() if j.get("origin") == "heartbeat")


# v1576 — `_heartbeat_in_flight()` (a bare `_heartbeat_in_flight_n() > 0` wrapper) was removed:
# zero callers repo-wide; the one live consumer (the ROBOT_MODE heartbeat gate) counts with
# `_heartbeat_in_flight_n() < _heartbeat_cap()` and never asked the boolean question.


def _in_flight_has_sig(sig):
    """Anti double-spend: is this exact view already on a reader?"""
    with _pool_lock:
        for j in _in_flight.values():
            try:
                if sig_diff(sig, j.get("sig")) <= SETTLE:
                    return True
            except Exception:
                pass
    return False


def _in_flight_min_capture():
    with _pool_lock:
        if not _in_flight:
            return None
        return min(int(j.get("captureTs") or 0) for j in _in_flight.values())


def _pool_acquire():
    """Reserve a free reader id (caller must release via _pool_release), or None if all busy."""
    with _pool_lock:
        if not _pool_free:
            return None
        return _pool_free.pop(0)


def _pool_release(rid):
    """Return `rid` to the free list. v948.17 — sentinel/override ids (e.g. the stall-drain
    worker's negative _STALL_RID) are never pool members and must never leak in here; a real
    pool slot is always in range(POOL_N)."""
    with _pool_lock:
        if rid is None or rid < 0:
            return
        if rid not in _pool_free:
            _pool_free.append(rid)
            _pool_free.sort()


# ── v948.17 STALL-DRAIN — a PARALLEL second-eye worker for a hung live lane (Grok P1-4,
# 2026-07-21 fast-run soak). Outside ROBOT_MODE, POOL_N==1 by design ("ONE Claude always"),
# so the old second-eye sweep gate (`_vision_in_flight_n() < POOL_N`) can NEVER open while
# the single live reader is busy — even when that read has been stuck in flight for a minute.
# A hung live read is not an "idle gap"; it's exactly the case the backlog most needs draining
# in. This dedicated worker lives entirely OUTSIDE POOL_N/_pool_free bookkeeping (sentinel
# reader id _STALL_RID, never returned to `_pool_free`) so it can never be claimed by ordinary
# live dispatch and never steals the "one Claude" live slot — it only ever fires the bounded,
# already-captured backlog sweep while the live eye is demonstrably stalled.
_STALL_RID = -1                 # sentinel reader id — always outside range(POOL_N)
_STALL_WORKER = None
_STALL_BUSY = False
STALL_DRAIN_S = max(1.0, float(os.environ.get("TV_STALL_DRAIN_S", "20") or 20))


def _stall_worker():
    """Lazily-created, dedicated VisionWorker for stall-drain sweeps only — never shared
    with the live reader pool, so a hung live subprocess can't also silence this one."""
    global _STALL_WORKER
    if _STALL_WORKER is None:
        _STALL_WORKER = VisionWorker(role="vision-stall")
    return _STALL_WORKER


#: #83 — the stall reader's releases: how many times it let its claude go after a sweep, and when.
_STALL_RELEASE = {"n": 0, "lastTs": None, "say": "the stall reader has not swept yet"}


def _stall_worker_release(worker=None):
    """#83 — MEMORY-AWARE: after each stall-drain sweep the dedicated reader lets its claude process go instead of
    staying warm. -> True when a process was ended.

    A warm `claude -p` is ~400 MB (measured on his PC), and the stall reader is a SAFETY NET that fires once in a
    long while - keeping it warm between sweeps was ~400 MB held for nothing beside the live pool's own reader(s),
    on the machine where dwm.exe died of memory exhaustion (REG-1502). The next sweep pays a cold start (~6-16 s)
    against a backlog that by definition has already waited STALL_DRAIN_S; the sweep still fires, it does not
    fire warm. ask() re-spawns on its own (`self.p is None`), so nothing else needs to know."""
    w = worker if worker is not None else globals().get("_STALL_WORKER")
    if w is None or getattr(w, "p", None) is None:
        return False
    try:
        w.stop()
    except Exception:
        return False
    _STALL_RELEASE["n"] = int(_STALL_RELEASE.get("n") or 0) + 1
    _STALL_RELEASE["lastTs"] = int(time.time() * 1000)
    _STALL_RELEASE["say"] = "the stall reader released its claude after sweep #%d (memory)" % _STALL_RELEASE["n"]
    try:
        ev("cap", _STALL_RELEASE["say"])
    except Exception:
        pass
    return True


def _live_stall_ms():
    """Age (ms) of the OLDEST in-flight read, or 0 if the pool is idle. Used to detect a
    genuinely hung live read (not just a normal-length one) before parallel-draining."""
    with _pool_lock:
        if not _in_flight:
            return 0
        oldest = min(int(j.get("startedAt") or 0) for j in _in_flight.values())
    return max(0, int(time.time() * 1000) - oldest) if oldest else 0


def _stall_drain_decision(backlog_len, in_flight_n, pool_n, stall_ms, stall_busy,
                           enabled=True, threshold_ms=None, ram_ok=True):
    """PURE decision (Grok P1-4 pin target) — fire the parallel stall-drain sweep only when:
      • the feature is enabled;
      • the backlog actually has something piling up (backlog_len > 0);
      • the live pool is FULLY busy (in_flight_n >= pool_n) — when a slot is free the ordinary
        '< POOL_N' idle-gap sweep already covers it, no need for a second worker;
      • the oldest in-flight read has been running >= threshold_ms — a genuine stall, not an
        ordinary 9-15s named read;
      • no stall-sweep is already running (bounded to exactly one parallel sweep at a time);
      • #83 — `ram_ok`: free RAM clears the floor (child_guard.secondary_spawn_allowed). A bool, or a
        callable asked LAST so the meter is only read once every other gate has opened - this runs on
        every busy tick. The stall reader is a second ~400 MB claude; it does not start into the memory
        pressure that killed dwm.exe.
    """
    if not enabled:
        return False
    if stall_busy:
        return False
    if backlog_len <= 0:
        return False
    if in_flight_n < pool_n:
        return False
    thr = (STALL_DRAIN_S * 1000.0) if threshold_ms is None else float(threshold_ms)
    if float(stall_ms) < thr:
        return False
    if callable(ram_ok):
        ram_ok = ram_ok()
    if not ram_ok:
        return False
    return True


def _stall_drain_ready():
    """Thin glue over `_stall_drain_decision` reading the live globals."""
    return _stall_drain_decision(
        backlog_len=_text_eye_backlog_len(),
        in_flight_n=_vision_in_flight_n(),
        pool_n=POOL_N,
        stall_ms=_live_stall_ms(),
        stall_busy=globals().get("_STALL_BUSY", False),
        enabled=os.environ.get("TV_STALL_DRAIN", "1") != "0",
        ram_ok=lambda: _child_guard.secondary_spawn_allowed()[0],      # #83 — asked last, cached 5 s
    )


def _order_push(capture_ts, job, rd, ocr_rd):
    """v863 — enqueue a completed deep read for ordered apply, keyed by captureTs."""
    with _emit_lock:
        _order_seq[0] += 1
        heapq.heappush(_order_buf, (int(capture_ts), _order_seq[0],
                       {"job": job, "rd": rd, "ocr_rd": ocr_rd,
                        "captureTs": int(capture_ts), "bufferedAt": int(time.time() * 1000)}))


def _order_drain():
    """v863 — apply buffered deep reads in captureTs order. A buffered completion emits only when
    NO in-flight reader holds a strictly SMALLER captureTs (floor-before-stash lock); a completion
    that has waited past ORDER_HOLD_MS applies anyway (dispatch.orderSkip='straggler'). Returns
    the list of records applied this call."""
    applied = []
    with _emit_lock:
        now_ms = int(time.time() * 1000)
        while _order_buf:
            capture_ts, seq, payload = _order_buf[0]
            floor = _in_flight_min_capture()
            straggler = (now_ms - int(payload.get("bufferedAt") or now_ms)) >= ORDER_HOLD_MS
            if floor is not None and floor < capture_ts and not straggler:
                break   # an OLDER read is still pending — hold the line
            heapq.heappop(_order_buf)
            job = payload["job"]
            disp = dict(job.get("dispatch") or {})
            if straggler:
                disp["orderSkip"] = "straggler"
                journal_skip("order-straggler", "applied out of order after hold")   # v880 A2.8
            disp["appliedTs"] = now_ms
            disp["orderHoldMs"] = ORDER_HOLD_MS
            try:
                rec = emit_deep_read(payload["rd"], n=job.get("n"), frame_id=job.get("fid"),
                                     interest=job.get("interest", 0.0),
                                     used_priority=job.get("priority", False),
                                     ocr_rd=payload.get("ocr_rd"), farewell=False,
                                     capture_ts=int(capture_ts),
                                     dispatch=disp, raw=job.get("raw"))
                if rec is not None:
                    applied.append(rec)
            except Exception as e:
                try: ev("cap", "ordered apply failed: %s" % e)
                except Exception: pass
    return applied


_POOL_STOPPING = False
# v899 — farewell/pool join hard-cap (was 90s; 400-read desktop sessions hung SIGNING OFF forever)
# v925 LIGHT — shorter cap; the farewell VISION read is OFF by default now (see close_session):
# it was the "END SESSION stuck" bug — a final Claude read stacked on pool-join + flush + fold
# past the console's ~22s wait. LIGHT END = seal the reel and exit, instant, no vision call.
FAREWELL_MAX_S = max(3.0, min(45.0, float(os.environ.get("TV_FAREWELL_S", "6") or 6)))
FAREWELL_READ_ON = str(os.environ.get("TV_FAREWELL", "0" if LIGHT_MODE else "1")).strip().lower() in ("1", "true", "yes", "on")


def _pool_shutdown(timeout=None, keep_worker0=True):
    """v864/v899 — join in-flight briefly, then inert late threads. Hard-capped (default ~12s).
    v1200 — `deadline` here is monotonic (see the `_verify_drain` note below): a shutdown that
    straddles a backward wall-clock jump must not join in-flight reads for the length of the
    jump instead of FAREWELL_MAX_S.

    v1206 — `keep_worker0`: Worker 0 (`_WORKER`) is exempted from the stop sweep below ONLY
    because farewell_read() needs it warm right after this call returns (v863: 'Worker 0 ==
    _WORKER, the farewell / POOL_N=1 fast path'). But v925 LIGHT made the farewell vision read
    OPT-IN — FAREWELL_READ_ON defaults False outside ROBOT_MODE — so in Konyo's actual default
    config `close_session` never runs a farewell read at all, and `_WORKER`'s warm `claude -p`
    child was NEVER being stopped by anything: close_session ends in os._exit(0) right after,
    same orphan-process leak as the round-6 stall-worker fix, except this sibling leaks on
    EVERY session close instead of only when the stall-drain safety net fires. The caller
    (`close_session`) knows by this point whether a real farewell read is actually coming —
    pass keep_worker0=False whenever it isn't, and worker 0 gets swept too."""
    if timeout is None:
        timeout = FAREWELL_MAX_S
    globals()["_POOL_STOPPING"] = True
    deadline = time.monotonic() + max(0.0, float(timeout))
    while time.monotonic() < deadline:
        with _pool_lock:
            if not _in_flight:
                break
        time.sleep(0.1)
    try:
        _prev = ORDER_HOLD_MS
        globals()["ORDER_HOLD_MS"] = 0
        _order_drain()
        globals()["ORDER_HOLD_MS"] = _prev
    except Exception:
        pass
    # v1179 CLOSER — a verify job for the last read(s) of the session was silently dropped when
    # the process exited with `_VERIFY_Q` non-empty (nothing ever drains it but the main loop's
    # idle gap, which a closing session no longer reaches). That item's second-look correction
    # then never runs at all — a silent starve, not an honest miss. Spend only what's LEFT of
    # this function's own `deadline` (never extends shutdown time): if the in-flight join above
    # finished early, as it usually does, there's a few spare seconds to spend here instead of
    # going idle; if it already ate the whole budget, `time.monotonic() < deadline` is false and
    # this is a no-op.
    try:
        if VERIFY_ON and _VERIFY_Q and time.monotonic() < deadline:
            _verify_drain(worker=_WORKER, budget=len(_VERIFY_Q),
                          timeout=max(3.0, deadline - time.monotonic()), deadline=deadline)
    except Exception:
        pass
    for w in _WORKERS[1:]:
        try: w.stop()
        except Exception: pass
    if not keep_worker0:
        try: _WORKER.stop()
        except Exception: pass
    # v1204 — the stall-drain worker (`_stall_worker()`) is a SEPARATE VisionWorker deliberately
    # kept OUTSIDE _WORKERS/_pool_free (never claimed by ordinary live dispatch — see the
    # v948.17 STALL-DRAIN block above), so a hung live reader can never also silence it. That
    # also means it's outside THIS sweep: if the stall-drain safety net ever fired even once
    # this session, its warm `claude -p` child (a ~200-600MB subprocess, same as any pool
    # worker) is a genuine ORPHAN at shutdown — close_session ends in os._exit(0), which skips
    # __del__/atexit entirely, so nothing else was ever going to kill it. Stop it here too, only
    # if it was ever actually created (the common case: the stall-drain path never fired).
    _sw = globals().get("_STALL_WORKER")
    if _sw is not None:
        try: _sw.stop()
        except Exception: pass
    # v1206 — a second sibling: `_OCR` (the persistent OcrWorker behind the fast/text-eye lane)
    # is likewise never stopped anywhere in the file. Unlike `_WORKER`, it has no "keep it warm
    # for farewell" reason to survive shutdown — farewell_read() explicitly skips OCR ("deep
    # only — farewell must land; OCR is optional and can wait") — so it's always safe to stop.
    try: _OCR.stop()
    except Exception: pass


def _win_d2r_process_alive():
    """v1413/v1414 — Windows: is D2R.exe running?
    v1414: NEVER use tasklist (hangs under D2R load and freezes the agent/UI).
    Prefer cap_target.json from capture_win, then Win32 process snapshot."""
    if not sys.platform.startswith("win"):
        return False
    # 1) capture half already wrote the truth (no process scan)
    try:
        tp = os.path.join(FRAMES, "cap_target.json")
        if os.path.isfile(tp):
            with open(tp, encoding="utf-8") as f:
                j = json.load(f) or {}
            if j.get("d2rProcess") is True:
                return True
            lab = str(j.get("label") or "").lower()
            mode = str(j.get("mode") or "").lower()
            if mode == "window" and ("d2r" in lab or "diablo" in lab):
                return True
    except Exception:
        pass
    # 2) Toolhelp32 snapshot (no tasklist.exe) — the LOCAL process half, shared with the triage lane
    return _toolhelp_d2r_state() is True


def _toolhelp_d2r_state():
    """Windows: is D2R.exe running ON THIS MACHINE? One Toolhelp32 snapshot. -> True | False | None

    ⚠ 2026-09-28 — THE PROCESS HALF OF _win_d2r_process_alive, ON ITS OWN, AND THREE-VALUED. The
    triage lane stands aside while he plays D2R natively (Dean, a Windows laptop — "usually" how he
    plays), and it asked tv_diablo._d2r_process_alive(), i.e. `pgrep`, which does not exist on
    Windows: FileNotFoundError, swallowed, False on every Windows PC — so triage walked reels beside
    his LOCAL game. This asks the process table itself.
    ⚠ It deliberately does NOT read cap_target.json's label the way _win_d2r_process_alive does
    first: on his ALT the capture half pins a BOOSTEROID window titled "Diablo...", and a label step
    would call that local play and starve triage there again. A cloud stream runs no D2R.exe here.
    None = the snapshot could not be taken or walked (no ctypes.windll, a refused snapshot): UNKNOWN,
    which a caller must never read as "not running". [[unknown-stays-unknown]] [[copy-drift]]"""
    return _toolhelp_any(lambda n: n in ("d2r.exe",) or n.startswith("d2r") or "diabloii" in n.replace(" ", ""))


def _toolhelp_any(pred, with_pid=False):
    """Windows: ONE Toolhelp32 snapshot - does any running exe's lowercased name satisfy `pred`? -> True | False | None

    REG-1502 — the walk _toolhelp_d2r_state always did, with the name test handed in, so the self-prove lane can ask
    "is he playing - the game OR a cloud client streaming it" through the same snapshot instead of a second copy.
    REG-1511 — `with_pid=True` hands `pred(name, pid)` the process id too: a cloud client idling in his tray is not a
    stream, and only its pid lets the lane read how much memory it holds. None = UNKNOWN (no ctypes.windll, a refused
    or empty snapshot). [[copy-drift]]"""
    try:
        import ctypes
        from ctypes import wintypes
        TH32CS_SNAPPROCESS = 0x00000002
        class PROCESSENTRY32W(ctypes.Structure):
            _fields_ = [
                ("dwSize", wintypes.DWORD),
                ("cntUsage", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD),
                ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                ("th32ModuleID", wintypes.DWORD),
                ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD),
                ("pcPriClassBase", ctypes.c_long),
                ("dwFlags", wintypes.DWORD),
                ("szExeFile", wintypes.WCHAR * 260),
            ]
        k32 = ctypes.windll.kernel32
        snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if snap == ctypes.c_void_p(-1).value or snap == -1:
            return None
        try:
            pe = PROCESSENTRY32W()
            pe.dwSize = ctypes.sizeof(PROCESSENTRY32W)
            if not k32.Process32FirstW(snap, ctypes.byref(pe)):
                return None           # a snapshot with no first process was not a look
            while True:
                n = (pe.szExeFile or "").lower()
                if (pred(n, int(pe.th32ProcessID)) if with_pid else pred(n)):
                    return True
                if not k32.Process32NextW(snap, ctypes.byref(pe)):
                    break
        finally:
            k32.CloseHandle(snap)
    except Exception:
        return None
    return False


def _game_window_present():
    """v899 — True when the real D2R game window is pin-able (Mac Quartz / Win watch target).
    Stub/SIM always True so harnesses never trip the no-game pause.
    v1413 — Windows: process-alive OR window pin (exclusive fullscreen often has no EnumWindows hit).
    #63 follow-up — TV_CAPTURE=off answers True too, WITHOUT walking his windows or his processes: an
    agent that never reads the screen has no business listing what is on it, and with no frames it
    has no reads for this gate to hold."""
    if os.environ.get("TV_STUB") or _capture_is_off() or os.environ.get("TV_NO_GAME_GUARD") == "0":
        return True
    if WATCH_MODE:
        # Windows: capture half owns pin; also honor D2R.exe process (v1413)
        try:
            tp = os.path.join(FRAMES, "cap_target.json")
            if os.path.isfile(tp):
                with open(tp, encoding="utf-8") as f:
                    j = json.load(f) or {}
                mode = str(j.get("mode") or "").lower()
                if mode in ("window", "game", "d2r"):
                    return True
                if j.get("d2rProcess") is True:
                    return True
                if mode in ("waiting", "none", "missing"):
                    # still open if process is alive (pin lag / exclusive FS)
                    if _win_d2r_process_alive():
                        return True
                    return False
        except Exception:
            pass
        if _win_d2r_process_alive():
            return True
        # eye fresh + large enough → assume capture half is alive (don't block Win falsely)
        try:
            eye = os.path.join(FRAMES, "eye.jpg")
            if os.path.isfile(eye) and (time.time() - os.path.getmtime(eye)) < 3.0:
                return True
        except Exception:
            pass
        return True  # fail-open on Windows unless explicitly waiting
    # Mac: only D2R.exe (never CrossOver Home / Battle.net)
    try:
        if find_d2r_window_mac() is not None:
            return True
    except Exception:
        pass
    # v927.5 — PROCESS-ALIVE FALLBACK: during loading screens / Space transitions macOS
    # drops the game-sized window from CGWindowList for minutes (live evidence 15:45:
    # 224s HOLD mid-session; D2R spawns 6 windows and only the 1470×956 one qualifies).
    # If the D2R.exe process is alive the game exists — keep the gate open and let the
    # full-screen capture lane carry the feed until the window re-lists.
    _pn = time.time()
    _pc = globals().get("_D2R_PROC_CACHE")
    if _pc and (_pn - _pc[1]) < 5.0:
        return _pc[0]
    alive = False
    try:
        out = subprocess.run(["pgrep", "-f", "D2R.exe"], capture_output=True, timeout=3)
        alive = out.returncode == 0
    except Exception:
        alive = False
    globals()["_D2R_PROC_CACHE"] = (alive, _pn)
    return alive


def _no_game_words():
    """What the film loop says when it holds live reads for want of a game window. -> (banner, skip kind, skip line)

    The second eye on v3521: capture_preflight and lane_health already read _PICK_UNKNOWN as "could not look", while
    this loop still announced "D2R.exe window not found" for the same blind finder - two surfaces, one fact, opposite
    words. Reads are still HELD (a blind finder is no licence to read an unknown screen); only the claim changes.
    Windows fails open before it gets here, so this is the Mac's sentence. [[unknown-stays-unknown]]"""
    if _PICK_UNKNOWN and not WATCH_MODE:
        why = _PICK_WHY or "the window finder could not look"
        return ("Could not look for the D2R window (%s) — live reads are held until it can; this is not 'no game'" % why,
                "no-game-unknown", "could not look for the D2R window (%s) — AI paused, UNKNOWN" % why)
    return ("D2R window missing — open Diablo II: Resurrected (in-game, not only Battle.net) for live reads",
            "no-game", "D2R.exe window not found — AI paused")


def _set_game_gate(ok, msg=""):
    """Publish no-game pause into health/state for the console banner."""
    globals()["_GAME_OK"] = bool(ok)
    globals()["_AI_PAUSED"] = not bool(ok)
    globals()["_GAME_MSG"] = (msg or "")[:160]
    try:
        with _state_lock:
            st = _load()
            st["gameOk"] = bool(ok)
            st["aiPaused"] = not bool(ok)
            st["gameMsg"] = globals()["_GAME_MSG"]
            if not ok:
                st["phase"] = "hold"
            _save(st)
    except Exception:
        pass
_REFIRE_SIG = None      # v795 (Grok R5 #2) — OCR saw names, deep came back empty: allow ONE re-read of that view

# v845 — ONE AI READER: settle freeze → dual-lane (OCR flash + Claude deep).
# Scout mid-play secondary reader removed (Konyo: too slow / complicated).
# Hard limit: icons alone never invent names (read-only screen truth).

# v825 (Grok R5 #1 / R9 #2) — SETTLE QUEUE ring buffer ──────────────────────────
# A 7–90s Claude vision call runs on a background thread; meanwhile the main loop keeps
# capturing. Distinct freezes that landed during that window used to hit the `if _VISION_BUSY:`
# `continue` and vanish forever (hover A→B→C while A is read: B, C never reached OCR / hist /
# lifecycle / journal). We ring-buffer a COPIED snapshot of each new freeze (the live frame is
# about to be overwritten) and, the instant the in-flight read frees up, drain the NEWEST held
# view (Konyo's most-current screen) through the same dual-lane pipeline.
SETTLE_QUEUE_CAP = max(1, int(os.environ.get("TV_SETTLE_QUEUE_CAP", "4") or 4))
# v944 EVICTION JUSTICE — a hover streak floods the ring with text-eye freezes (one per new
# tooltip). The base cap must NEVER shed one text-eye freeze to make room for another; grant
# the priority (text-eye) class this many EXTRA slots before it may shed its own oldest.
PRIORITY_CAP_BONUS = max(0, int(os.environ.get("TV_PRIORITY_CAP_BONUS", "6") or 6))
SETTLE_QUEUE_STALE_MS = max(1000, int(os.environ.get("TV_SETTLE_QUEUE_STALE_MS", "120000") or 120000))
_SETTLE_QUEUE = []              # FIFO, newest last; each: {"path","sig","ts","interest","priority","origin"}
# v944 SECOND-EYE SWEEP — text-eye freezes superseded by the newest-wins live drain are NOT
# deleted (that was KAI's 'missed-text'); they wait here, files on disk, for the verify-gap
# sweeper to read them one at a time before seal. Bounded; stale-pruned; dies with the session.
_TEXT_EYE_BACKLOG = []
# v946 — slightly deeper backlog so hover-streak freezes survive longer for the sweeper
TEXT_EYE_BACKLOG_CAP = max(4, int(os.environ.get("TV_TEXT_EYE_BACKLOG_CAP", "32") or 32))
_settle_q_lock = threading.Lock()

def _settle_queue_dir():
    _establish_footage()
    d = os.path.join(FRAMES, "queue")
    try: os.makedirs(d, exist_ok=True)
    except Exception: pass
    return d

def _settle_file_del(entry):
    try:
        p = entry.get("path") if isinstance(entry, dict) else entry
        if p and os.path.isfile(p): os.remove(p)
    except Exception:
        pass

def _text_eye_backlog_add(entry):
    """v944 — hold an un-read text-eye freeze the newest-wins drain superseded, so the
    second-eye sweeper can still read it. Caller holds _settle_q_lock. Deduped by sig;
    bounded (oldest sheds only if the sweeper falls TEXT_EYE_BACKLOG_CAP behind)."""
    try:
        for b in _TEXT_EYE_BACKLOG:
            if sig_diff(entry.get("sig"), b.get("sig")) <= SETTLE:
                _settle_file_del(entry)   # already backlogged this exact view
                return
        _TEXT_EYE_BACKLOG.append(entry)
        while len(_TEXT_EYE_BACKLOG) > TEXT_EYE_BACKLOG_CAP:
            _settle_file_del(_TEXT_EYE_BACKLOG.pop(0))
    except Exception:
        _settle_file_del(entry)

def _text_eye_backlog_pop():
    """v944 — pop the OLDEST un-read text-eye freeze (earliest at-risk item first). Stale
    entries (>SETTLE_QUEUE_STALE_MS) are pruned. Returns the entry (file still on disk) or None."""
    now = int(time.time() * 1000)
    with _settle_q_lock:
        fresh, dropped = [], 0
        for e in _TEXT_EYE_BACKLOG:
            if now - e["ts"] > SETTLE_QUEUE_STALE_MS:
                _settle_file_del(e); dropped += 1
            else:
                fresh.append(e)
        _TEXT_EYE_BACKLOG[:] = fresh
        if dropped:
            ev("cap", "text-eye backlog — dropped %d stale freeze(s) (>%ds) unswept before seal"
               % (dropped, SETTLE_QUEUE_STALE_MS // 1000))
        if not _TEXT_EYE_BACKLOG:
            return None
        return _TEXT_EYE_BACKLOG.pop(0)

def _text_eye_backlog_len():
    """v948.17 (Grok P1-4) — peek the backlog size without popping (decision-only, no mutation)."""
    with _settle_q_lock:
        return len(_TEXT_EYE_BACKLOG)

def _settle_enqueue(src_frame, sig, interest=0.0, priority=False, origin="settle"):
    """Unit-engine work queue: copy live frame to frames/queue/<sig8>.bmp. Scout text freezes
    and settle freezes share this ring — same clock, same drain. Deduped by sig; FIFO cap;
    stale pruned. Never raises into the scan loop."""
    try:
        now = int(time.time() * 1000)
        reading = globals().get("_LAST_EMIT_SIG")
        if reading is not None and sig_diff(sig, reading) <= SETTLE:
            return   # this is the very view being read — don't re-queue it
        with _settle_q_lock:
            fresh, dropped = [], 0
            for e in _SETTLE_QUEUE:
                if now - e["ts"] > SETTLE_QUEUE_STALE_MS:
                    _settle_file_del(e); dropped += 1
                else:
                    fresh.append(e)
            _SETTLE_QUEUE[:] = fresh
            if dropped:
                ev("cap", "unit-queue — dropped %d stale freeze(s) (>%ds) waiting for a read"
                   % (dropped, SETTLE_QUEUE_STALE_MS // 1000))
            for e in _SETTLE_QUEUE:
                if sig_diff(sig, e["sig"]) <= SETTLE:
                    return   # already holding this view
            sig8 = hashlib.md5(bytes(sig)).hexdigest()[:8]
            # v2324 — carry the SOURCE's extension. This is a hardlink to the live frame, so a
            # fixed ".bmp" would put JPEG bytes behind a BMP name the moment the writer changed.
            dest = os.path.join(_settle_queue_dir(),
                                sig8 + (os.path.splitext(src_frame)[1] or ".jpg"))
            try:
                import shutil
                try:
                    if os.path.exists(dest):
                        os.remove(dest)
                    os.link(src_frame, dest)   # v877 — held freezes link, not copy
                except Exception:
                    shutil.copy2(src_frame, dest)
            except Exception:
                return
            _SETTLE_QUEUE.append({"path": dest, "sig": sig, "ts": now,
                                  "interest": round(float(interest), 3), "priority": bool(priority),
                                  "origin": str(origin or "settle")})
            # v944 EVICTION JUSTICE (Konyo: "catch these BEFORE KAI") — the old `pop(0)` shed the
            # oldest freeze regardless of origin, so a hover streak ate its own earlier text-eye
            # freezes → KAI's 'missed-text'. Now: evict the oldest NON-priority (ambient settle)
            # view first; a text-eye freeze is shed only when the ring is ALL text-eye AND past
            # the raised cap (CAP + PRIORITY_CAP_BONUS). Files are tiny — disk is not the limit.
            while len(_SETTLE_QUEUE) > SETTLE_QUEUE_CAP:
                _victim = next((i for i, e in enumerate(_SETTLE_QUEUE) if not e.get("priority")), None)
                if _victim is not None:
                    _settle_file_del(_SETTLE_QUEUE.pop(_victim))
                    continue
                # all-priority ring: hold up to the raised cap before shedding the oldest text-eye
                if len(_SETTLE_QUEUE) > SETTLE_QUEUE_CAP + PRIORITY_CAP_BONUS:
                    _settle_file_del(_SETTLE_QUEUE.pop(0))
                else:
                    break
    except Exception:
        pass

def _settle_drain_pop():
    """Pop the NEWEST held freeze (most-current view). Stale entries (>SETTLE_QUEUE_STALE_MS)
    are dropped first with a `cap` ev; the remaining older views are superseded, so their files
    are cleaned too. Returns the entry dict (its snapshot file still on disk) or None."""
    now = int(time.time() * 1000)
    with _settle_q_lock:
        fresh, dropped = [], 0
        for e in _SETTLE_QUEUE:
            if now - e["ts"] > SETTLE_QUEUE_STALE_MS:
                _settle_file_del(e); dropped += 1
            else:
                fresh.append(e)
        _SETTLE_QUEUE[:] = fresh
        if dropped:
            ev("cap", "settle-queue — dropped %d stale freeze(s) (>%ds) before a read freed up"
               % (dropped, SETTLE_QUEUE_STALE_MS // 1000))
        if not _SETTLE_QUEUE:
            return None
        entry = _SETTLE_QUEUE.pop()      # newest = most-current view (first eye reads this live)
        for e in _SETTLE_QUEUE:          # older held views are superseded for LIVE currency…
            if e.get("origin") == "text-eye" and e.get("path") and os.path.isfile(e.get("path")):
                _text_eye_backlog_add(e)   # …but an un-read item-text is NOT moot — sweep it later
            else:
                _settle_file_del(e)        # ambient settle views really are moot once newer exists
        _SETTLE_QUEUE[:] = []
        return entry

def _settle_queue_clear():
    """v825 — the queue dies with the session (farewell/shutdown), _eye_clear-style: drop every
    held file so a fresh ON never drains yesterday's freezes. Never raises."""
    with _settle_q_lock:
        for e in _SETTLE_QUEUE:
            _settle_file_del(e)
        _SETTLE_QUEUE[:] = []
        for e in _TEXT_EYE_BACKLOG:   # v944 — the sweep backlog dies with the session too
            _settle_file_del(e)
        _TEXT_EYE_BACKLOG[:] = []
    try:
        d = os.path.join(FRAMES, "queue")
        if os.path.isdir(d):
            for f in os.listdir(d):
                if f.endswith(".bmp"):
                    try: os.remove(os.path.join(d, f))
                    except Exception: pass
    except Exception:
        pass

# ═══ v732 — OCR FAST LANE (Konyo: pile→chip in ~0.1–0.2s; LLM floors at 3–6s)
# Local macOS Vision OCR (warm worker ~10–50ms). Claude stays the deep brain.
# Honesty: OCR names are provisional (review-first, never vault_names) until deep/lifecycle.
OCR_BIN = os.environ.get("TV_OCR_BIN") or os.path.join(HERE, "bin", "ocr_mac")
OCR_WIN_PS1 = os.path.join(HERE, "ocr_win.ps1")   # v818 — cousin twin (Windows.Media.Ocr)


def _ocr_worker_cmd():
    """v818 (Grok R8 #3) — the fast lane exists on BOTH platforms. Mac: ocr_mac --worker.
    Windows: powershell ocr_win.ps1 speaking the SAME stdin-path → stdout-JSON protocol.
    Returns None when no worker is available (fast lane off, vision-only)."""
    # v1463 — only take this branch when the seam yields a USABLE argv. v1461 returned
    # _argv_seam(...) unconditionally, so a malformed value (TV_OCR_ARGV=1, [], {}, "claude")
    # fell back to [OCR_BIN, "--worker"] and jumped the queue: on Windows that skipped the
    # ocr_win.ps1 branch below and tried to exec the checked-in Mach-O `bin/ocr_mac`, and on
    # Mac it skipped the isfile/X_OK guard. A bad env var must never beat the platform lane.
    _ocr_argv = _argv_seam("TV_OCR_ARGV", []) if os.environ.get("TV_OCR_ARGV") else []
    if _ocr_argv:
        return _ocr_argv
    if os.environ.get("TV_OCR_BIN"):
        return [os.environ["TV_OCR_BIN"], "--worker"]
    if sys.platform.startswith("win"):
        if os.path.isfile(OCR_WIN_PS1):
            return ["powershell.exe", "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", OCR_WIN_PS1]
        return None
    if os.path.isfile(OCR_BIN) and os.access(OCR_BIN, os.X_OK):
        return [OCR_BIN, "--worker"]
    return None
# v925 LIGHT — OCR lane OFF by default (Grok cut #4): the "1 claude" product doesn't need the
# extra grab+process per candidate. TV_OCR=1 (or heavy/robot) re-arms it.
# v941 — LANES ON BY DEFAULT, PERIOD. The v925-LIGHT off-defaults bit FOUR times (OCR
# twice, FILM twice) — every new launch path that skipped the launcher's exports silently
# killed the fast lane + text eye + footage. Disable explicitly (TV_OCR=0) or not at all.
OCR_ENABLED = os.environ.get("TV_OCR", "1") != "0"

class OcrWorker:
    """Persistent `ocr_mac --worker` — one process, many frames. Stdlib only."""
    def __init__(self):
        self.p = None
        self.q = None
        self.lock = threading.Lock()
        self.ok = False
        self.ram_refused = ""     # REG-2003 - why the last spawn was refused for memory; "" once a spawn is not
        self.ram_refused_at = 0.0  # REG-2005 - WHEN it was refused, so a probe blames only a refusal made during it

    def available(self):
        return bool(OCR_ENABLED and _ocr_worker_cmd() is not None)   # v818 — platform-aware

    def _spawn(self):
        import queue
        if not self.available():
            self.ok = False
            return False
        try:
            cmd = _ocr_worker_cmd()
            if not cmd:
                self.ok = False
                return False
            # #83 — a SECONDARY worker never starts into memory pressure: under the floor the fast lane stays
            # off for this ask (deep lane only) and says why once; ask() tries again on its next call.
            _ram_ok, _ram_why = _child_guard.secondary_spawn_allowed()
            if not _ram_ok:
                self.ok = False
                self.ram_refused = str(_ram_why or "memory is short")   # REG-2003 - the canary names it
                self.ram_refused_at = time.time()
                if not globals().get("_OCR_RAM_SAID"):
                    globals()["_OCR_RAM_SAID"] = True
                    ev("cap", "ocr worker not started: " + _ram_why)
                return False
            globals()["_OCR_RAM_SAID"] = False
            self.ram_refused = ""
            self.p = _child_guard.spawn("ocr",
                cmd,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, encoding="utf-8", errors="replace", bufsize=1)
            self.q = queue.Queue()
            def _pump(proc, q):
                try:
                    for line in proc.stdout:
                        q.put(line)
                except Exception:
                    pass
                q.put(None)
            threading.Thread(target=_pump, args=(self.p, self.q), daemon=True).start()
            self.ok = True
            return True
        except Exception:
            self.ok = False
            self.p = None
            return False

    def stop(self):
        p = self.p
        self.p = None
        self.ok = False
        if not p:
            return
        # ⚠ #224 — NO `quit\n` WRITE HERE ANY MORE. It had no deadline and was overridden by the kill on the
        # very next line, so it bought nothing and could hang the caller on a full pipe — and the caller is now
        # every os.execv relaunch (exec_hygiene.quiesce_before_exec). The kill is the stop; the door collects it.
        # #83 — the same stop as VisionWorker's (v2352's block existed twice and both leaked): one routine.
        _stop_worker_process("ocr", p)

    def read(self, path, timeout=1.2):
        """Return {ms, lines, confs, mode} or None. Never raises into the scan loop."""
        # REG-2271 — BOUND THE LOCK ACQUIRE. This lock serialises the one OCR worker's pipe. If the
        # holder is wedged (a subprocess op that never returns), a plain `with self.lock` makes a SECOND
        # caller — a sweep's grouping tile sharing the module _OCR singleton with the live text-eye lane
        # — block UNINTERRUPTIBLY, which no in-thread per-reel deadline can fire on (its check() never
        # runs) and only the 240s river watchdog could end. Acquiring with a timeout makes a contended
        # read return None (an honest miss, never invented loot) so on_tile fires and the grouping's
        # no-progress deadline / the phase-scoped watchdog can interrupt the frame in ~budget. Released
        # in a finally so a return or raise in the body never leaks the lock. [[heart-first]] [[the-unjoined-end]]
        if not self.lock.acquire(timeout=max(1.0, timeout)):
            return None
        try:
            try:
                if self.p is None or self.p.poll() is not None:
                    self.stop()
                    if not self._spawn():
                        return None
                ap = os.path.abspath(path)
                # v1200 — same class as VisionWorker.ask(): monotonic, not wall-clock, so a
                # backward NTP jump mid-poll can't balloon the wait past the intended budget
                # (short window here, 1.2-1.5s, but the OCR/text-eye lane depends on it staying
                # fast every single poll — a stuck wait here starves the whole fast lane).
                # REG-1300 — and it starts BEFORE the write, which it now bounds.
                deadline = time.monotonic() + timeout
                if not _pipe_write_by(self.p, ap + "\n", deadline):
                    p, self.p = self.p, None
                    _bury_worker(p, role="ocr")     # not draining its input - never reuse it; #83 the whole tree
                    return None
                while time.monotonic() < deadline:
                    try:
                        line = self.q.get(timeout=max(0.05, deadline - time.monotonic()))
                    except Exception:
                        break
                    if line is None:
                        self.stop()
                        return None
                    line = (line or "").strip()
                    if not line:
                        continue
                    try:
                        j = json.loads(line)
                    except Exception:
                        continue
                    if isinstance(j, dict) and "lines" in j:
                        # v1709 — mode=err with lines=[] is a FAILED read, not loot.
                        # Returning it let ocr_fast stamp scene=loot / conf=0.45 / mode=ocr.
                        if str(j.get("mode") or "") == "err":
                            return None
                        return j
                self.stop()
                return None
            except Exception:
                self.stop()
                return None
        finally:
            self.lock.release()

_OCR = OcrWorker()

# HUD / shell noise that is never a D2 item label
_OCR_NOISE = (
    "http", "localhost", "claude", "python", "terminal", "settings", "safari",
    "chrome", "wrangler", "github", "localhost", "127.0.0.1", "subscription",
    "screenshot", "screencapture", "grok", "cursor", "vscode",
    # v935.7 — console chrome (text-eye burned a Sonnet read on STANDBY/LIVE at boot)
    "standby", "on air", "off air", "watching", "signal idle", "press on",
    "live eye", "second eye", "three eyes", "auto intake", "tv diablo",
    "simulation", "farm day", "last thought",
)

def filter_ocr_lines(lines):
    """Keep item-ish strings; drop UI chrome. Board vocab does the real route match."""
    out, seen = [], set()
    for raw in lines or []:
        s = str(raw or "").strip()
        if len(s) < 3 or len(s) > 48:
            continue
        lo = s.lower()
        if lo in seen:
            continue
        if any(n in lo for n in _OCR_NOISE):
            continue
        if sum(c.isdigit() for c in s) > max(3, len(s) // 2):
            continue
        # need at least one letter run of 2+
        if not any(len(p) >= 2 and p.isalpha() for p in lo.replace("'", " ").split()):
            continue
        seen.add(lo)
        out.append(s)
        if len(out) >= 16:
            break
    return out

def _text_eye_loop():
    """v932 — 👁‍🗨 THE TEXT-TRIGGERED EYE (Konyo forensic case: '20 items shown, 4 reads').
    The motion-settle detector is blind to tooltips and tab swaps — small pixel deltas on a
    static stash view never trip a read. This lane OCR-scans the live eye continuously
    (local Vision, ~50-150ms) and turns NEW item-ish text into an immediate PRIORITY read
    of the frozen frame via _settle_enqueue (whose drain path bypasses the same-view gate,
    so these can never be deduped away). Text re-arms after a TTL so revisits re-read."""
    # v2000 — the OCR check stays at the top: no local Vision means this lane can never work and
    # the thread should not exist. The ON/OFF moved INSIDE the loop, because a switch he can only
    # use by restarting the agent is not a switch. TV_TEXT_EYE=0 still short-circuits everything.
    if os.environ.get("TV_TEXT_EYE", "1") == "0" or not _OCR.available():
        return
    eye = os.path.join(FRAMES, "eye.jpg")
    seen = {}          # normalized text → last-seen monotonic ts
    TTL = 150.0
    last_area = None
    while True:
        try:
            time.sleep(0.7)
            # v937.1 — NEW AREA = fresh eyes: the same item names in a new run must
            # re-trigger (a second Shako in the next Baal run is a new event, not a dup).
            _ar = globals().get("LAST_AREA")
            if _ar != last_area:
                last_area = _ar
                if seen:
                    seen.clear()
            if globals().get("_AI_PAUSED") or not os.path.isfile(eye):
                continue
            # v2000 — HIS SWITCH, honoured live. Checked here rather than at thread start so
            # flipping it takes effect on the next 0.7s tick instead of at the next ON AIR.
            # Costs one cached stat; the file is absent on a normal run and absent means ON.
            if not shadow_ai_on():
                continue
            # v934.2 / v935.7 — NO PIN, NO SCAN. Boot default used to be mode="full", so the
            # text eye OCR'd console chrome (STANDBY / LIVE) and burned a Sonnet read.
            # Only a real D2R *window* pin is allowed — never full-screen / waiting / none.
            _cap = _CAP_TARGET or {}
            if not WATCH_MODE and (_cap.get("mode") != "window" or not _cap.get("wid")):
                continue
            if (time.time() - os.path.getmtime(eye)) > 3.0:
                continue   # film cold — nothing fresh under the eye
            raw = _OCR.read(eye, timeout=1.5)
            if not raw:
                continue
            names = filter_ocr_lines(raw.get("lines") or [])
            now = time.monotonic()
            for k in [k for k, t in seen.items() if now - t > TTL]:
                del seen[k]
            fresh = []
            for nm in names:
                key = _norm_name(nm)
                if not key:
                    continue
                # v1379 — OCR garble ("haTrng1.. Lobby", "'Ii'", "ING THe R") was enqueuing
                # priority Sonnet reads every ~0.7s. Gate on _text_eye_worthy (stricter than
                # _itemish) so only real-looking item labels burn a subscription vision turn.
                if not _text_eye_worthy(nm):
                    seen[key] = now   # still mark seen so garble doesn't re-arm forever
                    continue
                if key not in seen:
                    fresh.append(nm)
                seen[key] = now
            if not fresh:
                continue
            # v1379 — cooldown: after a text-eye fire, wait before another (cap spam)
            last_fire = globals().get("_TEXT_EYE_LAST_FIRE") or 0.0
            try:
                min_gap = float(os.environ.get("TV_TEXT_EYE_MIN_GAP_S", "4") or 4)
            except Exception:
                min_gap = 4.0
            if now - last_fire < min_gap:
                continue
            try:
                sig = frame_sig(eye)
            except Exception:
                continue
            globals()["_TEXT_EYE_LAST_FIRE"] = now
            _settle_enqueue(eye, sig, interest=0.95, priority=True, origin="text-eye")
            ev("settle", "👁‍🗨 text eye — new text: " + ", ".join(fresh[:3])
               + (" …" if len(fresh) > 3 else "") + " → priority read of the frozen frame")
            # v937 — the trigger is EVIDENCE: journal it so SIM shows WHY a priority read
            # fired at this instant, and the Watchdog can assert text-eye liveness.
            try:
                journal_skip("text-eye", "👁‍🗨 triggered by: " + ", ".join(fresh[:4]))
            except Exception:
                pass
        except Exception:
            time.sleep(2.0)


def ocr_fast(path):
    """Fast lane: local OCR → provisional names. Target warm p50 < 50ms, p99 < 200ms."""
    if not OCR_ENABLED or os.environ.get("TV_OCR") == "0":
        return None
    t0 = time.time()
    raw = _OCR.read(path)
    wall = int((time.time() - t0) * 1000)
    if not raw or str(raw.get("mode") or "") == "err":
        return None
    _raw_lines = [str(x)[:60] for x in (raw.get("lines") or [])][:40]
    lines = filter_ocr_lines(raw.get("lines") or [])
    _kept = set(lines)
    _ocr_dropped = [{"line": x, "why": "line-filter"} for x in _raw_lines if x not in _kept][:20]
    confs = raw.get("confs") or []
    avg_c = None
    if confs:
        try:
            avg_c = round(sum(float(c) for c in confs[: len(lines) or 1]) / max(1, min(len(confs), max(1, len(lines)))), 3)
        except Exception:
            avg_c = None
    return {
        "names": lines,
        "raw_lines": _raw_lines,        # v853 (A2.7) — what the OCR literally saw
        "dropped": _ocr_dropped,        # v853 — what the line-filter ate, with why
        "ms": int(raw.get("ms") or wall),
        "wall_ms": wall,
        "conf": avg_c if avg_c is not None else 0.45,
        "mode": "ocr",
        "lane": "ocr",
        "model": "ocr-mac",
        "scene": "loot",          # provisional — deep lane will set real scene
        "area": "",
        "tz": [],
        "intent": "seen",         # never farmed from OCR alone
        "provisional": True,
        "escalated": False,
        "raw_n": len(raw.get("lines") or []),
    }

_REWARM_T = [0.0]        # legacy compat (unused by the pool path)
_REWARM_AT = {}          # v863 — per-worker last-rewarm ts (id(worker) -> time), independent debounce
def _rewarm(worker=None):
    """v863 — after a reader death/throttle, quietly warm THAT slot's fresh session (60s
    per-worker debounce). One-shot is a bridge; a degraded reader recovers on its own without
    ever stalling the other 7. Defaults to worker 0 for old callers.

    v1192 — that "other 7" is the whole premise: this only helps when OTHER pool slots are
    free to keep serving live traffic while this one warms in the background. Outside
    ROBOT_MODE, POOL_N==1 ("ONE Claude always" — Konyo's actual live config) means there IS
    no other slot; `w` here is the SAME VisionWorker every live read uses, and `w.ask()`
    below holds `w.lock` for up to 60s — a `Reply with exactly: ok` ping that a live read
    arriving moments later would silently queue behind, waiting on the lock BEFORE its own
    LIVE_READ_TIMEOUT_S budget even starts counting. That defeats the Master Brain law
    (v948.17) worse than the outage it's meant to route around: a dead worker already
    self-heals for free (`ask()`'s own `self.p.poll() is not None` respawn, first thing on the
    very next call), so a POOL_N==1 background ping only adds contention with no upside. Skip
    it there; keep it for the real multi-reader pool it was written for."""
    if POOL_N <= 1:
        return
    if _reader_choice() == "grok":   # #151 Grok only: a Claude reader is never pinged awake
        return
    w = worker or _WORKER
    key = id(w)
    if time.time() - _REWARM_AT.get(key, 0.0) < 60: return
    _REWARM_AT[key] = time.time()
    def _run():
        t0 = time.time()
        try:
            if w.ask("Reply with exactly: ok", timeout=60) is not None:
                ev("boot", f"vision re-warmed in {int(time.time()-t0)}s — that reader is fast again")
        except Exception:
            pass
    threading.Thread(target=_run, daemon=True).start()

_STASH_TABS = frozenset(("personal", "shared", "gems", "materials", "runes"))
_STASH_TAB_ALIASES = {
    "rune": "runes", "runes": "runes",
    "gem": "gems", "gems": "gems",
    "mat": "materials", "mats": "materials", "material": "materials", "materials": "materials",
    "personal": "personal", "shared": "shared",
}

def _norm_stash_tab(raw, scene=None):
    """v734 — active RotW stash tab, or \"\" if not stash / unknown."""
    if scene is not None and scene != "stash":
        return ""
    lo = str(raw or "").strip().lower()
    if not lo:
        return ""
    # allow "Runes Tab" / "Materials stash"
    for key in ("materials", "material", "runes", "rune", "gems", "gem", "personal", "shared"):
        if key in lo:
            return _STASH_TAB_ALIASES.get(key, key if key in _STASH_TABS else "")
    return _STASH_TAB_ALIASES.get(lo, "") if lo in _STASH_TAB_ALIASES else ""


# v1818 — the panel's sort order, and the shape a First Found stamp must have.
#
# _CHRON_STAMP_RX is not decoration. The UNIQUE and SETS tabs print `First Found:` and
# `Dropped By:` in OPPOSITE orders (verified on his 08-20 frames), so the single most likely
# reader error is filling foundAt with a monster name. A stamp that is not a date is DROPPED and
# audited rather than stored: a wrong find-date would outlive every later correction, because
# nothing downstream re-reads a date it already has.
# Compiled on first use, not at import: this module has NO module-level `re` (its convention is a
# local `import re as _re` inside the functions that need it), and a top-level re.compile here
# raised NameError at import — caught by running the parser rather than by reading it.
_CHRON_STAMP_RX = None


def _chron_stamp_ok(v):
    """True when v looks like the game's own `First Found` stamp, e.g. 08/20/2026, 00:49."""
    global _CHRON_STAMP_RX
    if _CHRON_STAMP_RX is None:
        import re as _re
        _CHRON_STAMP_RX = _re.compile(r"^\s*\d{1,2}/\d{1,2}/\d{4}\s*,?\s*\d{1,2}:\d{2}(:\d{2})?\s*$")
    return bool(_CHRON_STAMP_RX.match(v or ""))


def _norm_chron_sort(raw, scene=None):
    """newest | oldest | other | "" — and "" whenever the scene is not a chronicle page."""
    if scene is not None and scene != "chronicle":
        return ""
    v = str(raw or "").strip().lower()
    if not v:
        return ""
    if "newest" in v and "oldest" in v:
        return "newest" if v.index("newest") < v.index("oldest") else "oldest"
    if v in ("newest", "oldest", "other"):
        return v
    if "newest" in v:
        return "newest"
    if "oldest" in v:
        return "oldest"
    return "other"


def _norm_chron_tab(raw, scene=None):
    """v1512 — WHICH CHRONICLE LEDGER is on screen: "uniques" | "sets" | "".

    Only meaningful when scene=chronicle, and deliberately STRICT: anything the reader was not sure
    about comes back "" rather than a guess. The two ledgers are two different stores (d2r_foundLog
    vs d2r_setPieces) — an unknown ledger just costs a re-read, a WRONG one writes set pieces into
    his grail. So the fuzzy matching that serves the stash tabs well would be the wrong instinct here.
    """
    if scene is not None and scene != "chronicle":
        return ""
    lo = str(raw or "").strip().lower()
    if lo in ("uniques", "unique", "holy grail", "grail"):
        return "uniques"
    if lo in ("sets", "set", "set pieces", "setpieces"):
        return "sets"
    return ""


# v946.1 — STASH TAB IDENTITY (live farm: gems/materials never journaled when model said only
# "shared"/empty). Tab-strip OCR + sticky walk so tally tabs stick for driver/KAI time-map.
_STASH_TAB_STICKY = {"open": False, "tab": "", "ts": 0}
_TALLY_STASH_TABS = frozenset(("runes", "gems", "materials"))


def _tab_from_ocr_lines(lines):
    """Pure: active RotW tab from OCR. Multi-tab chrome → '' (stash_eye / v947)."""
    try:
        from stash_eye import tab_from_ocr_lines as _se_tab
        return _se_tab(lines)
    except Exception:
        import re as _re
        blob = " ".join(str(t).lower() for t in (lines or []))
        if not blob.strip():
            return ""
        order = (
            ("materials", "materials"), ("material", "materials"),
            ("runes", "runes"), ("gems", "gems"),
            ("personal", "personal"), ("shared", "shared"),
            ("rune", "runes"), ("gem", "gems"), ("mat", "materials"),
        )
        hits = []
        for key, canon in order:
            if _re.search(r"(?<![a-z])" + _re.escape(key) + r"(?![a-z])", blob):
                if canon not in hits:
                    hits.append(canon)
        return hits[0] if len(hits) == 1 else ""


def _crop_left_tab_strip(src_path, dest_path, frac=0.20):
    """Legacy left-20% crop (fallback). Prefer stash_eye.prep_tab_chrome for v947 eyes."""
    try:
        from PIL import Image  # type: ignore
        im = Image.open(src_path)
        w, h = im.size
        if w < 32 or h < 32:
            return None
        box = (0, 0, max(8, int(w * frac)), h)
        im.crop(box).convert("RGB").save(dest_path, format="JPEG", quality=90)
        return dest_path
    except Exception:
        return None


def _stash_tab_ocr_path(frame_path, model_tab=""):
    """v947 — intake-style tab chrome + grid fingerprint (no intake calls).

    Mimics bible `_tallyPrepImage` crop band: upscaled tab chrome above left grid,
    then pixel grid class (runes/gems/materials). Used by live deep journal stashTab.

    v948.20 — model_tab corroboration: the caller (_resolve_stash_tab) only reaches
    here having ALREADY confirmed scene=='stash' from the model read, i.e. the stash
    panel IS open. Passing that through as model_tab lets the grid fingerprint's
    confident tally read (esp. the moderate-chroma GEMS grid) satisfy fuse_tab_signals'
    stash-open corroboration instead of being dropped for lack of a live journal sticky
    — WITHOUT relaxing the live loading-screen guard (which keys off the panel being
    open, which we know it is). Chrome OCR can't disambiguate the active tab (it prints
    ALL five labels → ambiguous → ''), so the grid is the real gems signal.
    """
    if not frame_path or not os.path.isfile(frame_path):
        return ""
    try:
        from stash_eye import analyze_frame

        def _read(p):
            if not _OCR.available():
                return {}
            try:
                return _OCR.read(p, timeout=1.5) or {}
            except Exception:
                return {}

        res = analyze_frame(
            frame_path,
            ocr_lines=None,
            journal_tab="",
            model_tab=(model_tab or "stash"),
            ocr_worker_read=_read if _OCR.available() else None,
            work_dir=HIST_DIR,
        )
        tab = str(res.get("tab") or "")
        if tab in ("runes", "gems", "materials", "personal", "shared"):
            return tab
        # fallback: legacy left strip if eyes returned empty
        if not _OCR.available():
            return ""
        crop = os.path.join(HIST_DIR, ".tabstrip_ocr.jpg")
        _establish_footage()
        use = _crop_left_tab_strip(frame_path, crop) or frame_path
        j = _OCR.read(use, timeout=1.5)
        return _tab_from_ocr_lines((j or {}).get("lines") or [])
    except Exception:
        return ""


# ══ v1522 — THE LIVE CHRONICLE VISIT ══════════════════════════════════════════════════════════
# Konyo: "when chronicle/menu is clicked ingame it should automatically know we are about to register
# and read and analyze the CHRONICLE lists."
#
# WHAT IT DOES AND DELIBERATELY DOES NOT DO. It RECORDS the visit — every frame, which ledger, how
# long — and that costs nothing. It does NOT fire chronicle reads mid-farm: that would spend his
# subscription reads without asking, in the middle of a run, on frames he is scrolling past. The
# recorded visit becomes an offer ("📜 a Chronicle visit was captured — 14 frames, Holy Grail ledger"),
# and the read is the same priced, reviewable, gated sweep the retro lane already uses. Same doctrine
# everywhere: see the price, then decide.
#
# THE STICKY exists because the ledger is read off the panel's tab header, and mid-scroll frames often
# do not show it. Losing the ledger halfway through a visit would split one visit into an identified
# half and an unidentified half — so the first confident answer holds for the whole visit, and a
# CONTRADICTING answer ends it (he switched tabs; that is genuinely a new visit).
_CHRON_VISIT = {"open": False, "ledger": "", "since": 0, "last": 0, "frames": []}
_CHRON_VISIT_MAX = 400   # a visit is minutes of frames, not a session; the cap is a memory guard


def _chron_visit_step(scene, chron_tab, frame_id=None, ts=None):
    """Advance the live visit state machine. Returns a CLOSED visit dict when one just ended, else None.

    Closing on the way OUT (rather than reporting continuously) is what makes the visit a single
    reviewable thing with a real frame count — a half-open visit has no honest number to show."""
    ts = int(ts or time.time() * 1000)
    scene = str(scene or "").lower()
    tab = _norm_chron_tab(chron_tab, "chronicle" if scene == "chronicle" else None)

    def _close():
        if not _CHRON_VISIT["open"]:
            return None
        out = {"ledger": _CHRON_VISIT["ledger"], "since": _CHRON_VISIT["since"],
               "until": _CHRON_VISIT["last"], "frames": list(_CHRON_VISIT["frames"])}
        out["n"] = len(out["frames"])
        _CHRON_VISIT.update({"open": False, "ledger": "", "since": 0, "last": 0, "frames": []})
        return out

    if scene != "chronicle":
        return _close()
    # a CONTRADICTING ledger means he switched tabs — that is a new visit, not a confused one
    if _CHRON_VISIT["open"] and tab and _CHRON_VISIT["ledger"] and tab != _CHRON_VISIT["ledger"]:
        closed = _close()
        _CHRON_VISIT.update({"open": True, "ledger": tab, "since": ts, "last": ts,
                             "frames": [frame_id] if frame_id else []})
        return closed
    if not _CHRON_VISIT["open"]:
        _CHRON_VISIT.update({"open": True, "ledger": tab, "since": ts, "last": ts, "frames": []})
    if tab and not _CHRON_VISIT["ledger"]:
        _CHRON_VISIT["ledger"] = tab          # the sticky: first confident answer holds the visit
    _CHRON_VISIT["last"] = ts
    if frame_id and len(_CHRON_VISIT["frames"]) < _CHRON_VISIT_MAX:
        _CHRON_VISIT["frames"].append(frame_id)
    return None


def chron_visit_open():
    """Is a Chronicle panel open RIGHT NOW — the 'we are about to register' signal, for the console."""
    return {"open": bool(_CHRON_VISIT["open"]), "ledger": _CHRON_VISIT["ledger"],
            "since": _CHRON_VISIT["since"], "frames": len(_CHRON_VISIT["frames"])}


def chron_visit_flush():
    """v1689 — SEAL A STILL-OPEN CHRONICLE VISIT AT SESSION CLOSE, so it reaches the journal.

    The state machine above only closes a visit on the way OUT — i.e. when a LATER deep read
    returns a non-chronicle scene. That lost the most natural way to use the feature: looking at
    the Chronicle LAST and then stopping. Measured on his session s_1786385768689_67392
    (2026-08-10 21:16-21:19): 8 deep frames scene='chronicle' / chronicleTab='uniques', the visit
    still {open:True, frames:8} at the end, and ZERO {lane:'chronicle', kind:'visit'} rows written
    — so /api/chronicle_visits (which filters on exactly that row) stayed [] and the v1527 "read
    this visit for ZERO classifies" offer could never appear.

    Session close is the honest seam: the reel stops growing there, so the frame count is final.
    Doctrine is unchanged — recording is FREE, reading is OFFERED. This journals the visit and says
    so; it never calls claude_chronicle_read / g5_chronicle_read and never spends a classify.
    Idempotent: closing leaves the visit shut, so a second call journals nothing.

    Returns the closed visit dict when one was journalled, else None.
    (The ev/_journal pair below is deliberately NOT shared with the live seam at the deep-read
    call site: test_agent.py slices that seam's SOURCE TEXT to prove the live lane never fires a
    read, and folding it into a helper would erase the text it reads.)"""
    try:
        _closed_visit = _chron_visit_step(None, None)
    except Exception:
        return None
    if not (_closed_visit and _closed_visit.get("n")):
        return None
    _lg = _closed_visit.get("ledger") or ""
    try:
        ev("read", "📜 Chronicle visit captured — %d frames%s · ask the console to read it"
           % (_closed_visit["n"], (" · " + ("Holy Grail" if _lg == "uniques" else "Set pieces"))
              if _lg else " · ledger unread"))
        _journal({"lane": "chronicle", "kind": "visit", "ts": int(time.time() * 1000),
                 "ledger": _lg, "frames": _closed_visit["frames"][:120],
                 "n": _closed_visit["n"], "since": _closed_visit["since"],
                 "until": _closed_visit["until"]})
    except Exception:
        pass
    return _closed_visit


def _resolve_stash_tab(scene, model_tab, frame_path=None, ocr_rd=None, ts=None):
    """v946.1 — final stashTab for journal/driver: model + tab-strip OCR + sticky walk.

    Rules:
      · leave stash → clear sticky
      · tally-tab words from OCR beat a vague model 'shared'/'personal'/empty (farm proof)
      · while still on stash with no new signal, hold last sticky tab (tab walk)
    """
    ts = int(ts or time.time() * 1000)
    scene = str(scene or "")
    if scene != "stash":
        if scene in ("town", "loot", "gameplay", "transition"):
            _STASH_TAB_STICKY["open"] = False
            _STASH_TAB_STICKY["tab"] = ""
            _STASH_TAB_STICKY["ts"] = 0
        return ""

    model = _norm_stash_tab(model_tab, "stash")
    ocr_tab = ""
    try:
        lines = []
        if isinstance(ocr_rd, dict):
            lines = list(ocr_rd.get("raw_lines") or ocr_rd.get("lines") or [])
        if lines:
            ocr_tab = _tab_from_ocr_lines(lines)
        if not ocr_tab and frame_path:
            # v948.20 — pass the model tab (or bare 'stash', panel is open) so a
            # confident grid gems/materials/runes read isn't dropped for want of a sticky.
            ocr_tab = _stash_tab_ocr_path(frame_path, model_tab=model)
    except Exception:
        ocr_tab = ""

    tab = model
    # OCR tally tabs win over model vault/empty (console "saw gems" but journal said shared)
    if ocr_tab in _TALLY_STASH_TABS and model not in _TALLY_STASH_TABS:
        tab = ocr_tab
    elif ocr_tab and not model:
        tab = ocr_tab
    elif ocr_tab and model and ocr_tab != model and ocr_tab in _TALLY_STASH_TABS:
        tab = ocr_tab
    elif not tab and ocr_tab:
        tab = ocr_tab

    # sticky walk: hold last tab while still on stash if nothing new
    if not tab and _STASH_TAB_STICKY.get("open") and _STASH_TAB_STICKY.get("tab"):
        if ts - int(_STASH_TAB_STICKY.get("ts") or 0) <= 25_000:
            tab = _STASH_TAB_STICKY["tab"]

    if tab:
        _STASH_TAB_STICKY["open"] = True
        _STASH_TAB_STICKY["tab"] = tab
        _STASH_TAB_STICKY["ts"] = ts
    else:
        _STASH_TAB_STICKY["open"] = True  # in stash, tab still unknown
    return tab


def _parse_read(out):
    """extract + normalize the read JSON from model text; None if no JSON object found.
    v794 (Grok R5 #4) — first-{ to last-} dies on worker chatter/truncation around the real
    payload. Scan for BALANCED candidate objects (right-to-left) and take the first that
    parses AND looks like a read (has a known key).
    v835 (Grok addendum A2.2) — PARSE AUDIT: every clamp/normalize/drop is recorded so SIM
    shows what the model SAID vs what survived (silent clamps burned us before: v769)."""
    j = None
    _audit = {"ok": False, "strategy": "none", "rawLen": len(out or ""), "dropped": [], "normalized": []}
    try:
        a, b = out.find("{"), out.rfind("}")
        if a < 0 or b <= a:
            return None
        try:
            j = json.loads(out[a:b + 1])
            _audit["strategy"] = "first-last"
        except Exception:
            j = None
        if j is None:
            # right-to-left balanced scan: the REAL payload is usually the last clean object
            starts = [k for k, ch in enumerate(out) if ch == "{"]
            for st in reversed(starts):
                depth = 0
                for k in range(st, len(out)):
                    if out[k] == "{":
                        depth += 1
                    elif out[k] == "}":
                        depth -= 1
                        if depth == 0:
                            try:
                                cand = json.loads(out[st:k + 1])
                                if isinstance(cand, dict) and any(x in cand for x in ("names", "scene", "area", "conf")):
                                    j = cand
                                    _audit["strategy"] = "balanced"
                            except Exception:
                                pass
                            break
                if j is not None:
                    break
        if not isinstance(j, dict):
            return None
    except Exception:
        return None
    _names_raw = j.get("names")
    if not isinstance(_names_raw, (list, tuple)):   # v877 fuzz — null/str names crashed or char-split
        if _names_raw not in (None, [], ""):
            _audit["dropped"].append({"field": "names", "why": "not-a-list", "from": str(_names_raw)[:40]})
        _names_raw = []
    # ⚠⚠ v3453 — A null IS NOT THE NAME "None". str(None) is "None", which is truthy and passes
    # the filter below as an item he owns. v3450's guard lives in the reducer, DOWNSTREAM of this
    # line, so it never saw a null — only the string this line made. Dropped nulls are RECORDED,
    # never silently discarded: a name the model declined to give is a fact about the read.
    # [[the-unjoined-end]] [[feedback-silence-is-not-evidence]]
    _nulls = sum(1 for x in _names_raw if x is None)
    if _nulls:
        _audit["dropped"].append({"field": "names", "why": "null-is-not-a-name", "count": _nulls})
    _all_names = [str(x).strip() for x in _names_raw if x is not None and str(x).strip()]
    names = _all_names[:60]
    if len(_all_names) > 60:
        _audit["dropped"].append({"field": "names", "why": "truncated-at-60", "count": len(_all_names) - 60})
    _scene_raw = str(j.get("scene", "gameplay")).lower()
    scene = _scene_raw
    if "scene" not in j:   # REG-1716 — an absent scene is a default, not the reader's word: said in the audit
        _audit["normalized"].append({"field": "scene", "from": "(absent)", "to": "gameplay", "why": "absent-scene-default"})
    if scene not in ("town", "loot", "inventory", "stash", "gameplay", "transition", "chronicle", "char-select"):
        _audit["normalized"].append({"field": "scene", "from": _scene_raw, "to": "gameplay", "why": "unknown-scene-clamp"})
        scene = "gameplay"   # v769 — transition is a REAL scene (the parse was silently killing v746)
    _tz_raw = j.get("tz")
    if not isinstance(_tz_raw, (list, tuple)):
        _tz_raw = []
    tz = [str(x).strip()[:40] for x in _tz_raw if str(x).strip()][:8]
    conf = j.get("conf", None)
    if isinstance(conf, bool):   # REG-1716 — float(True) is 1.0: a JSON true is not a confidence
        _audit["dropped"].append({"field": "conf", "from": str(conf), "why": "a-bool-is-not-a-confidence"})
        conf = None
    try:
        _conf_raw = conf
        conf = float(conf) if conf is not None else None
        if conf is not None:
            if conf < 0.0 or conf > 1.0:
                _audit["normalized"].append({"field": "conf", "from": str(_conf_raw)[:12], "to": str(max(0.0, min(1.0, conf))), "why": "clip-0-1"})
            conf = max(0.0, min(1.0, conf))
    except Exception:
        conf = None
        _audit["dropped"].append({"field": "conf", "from": str(_conf_raw)[:12], "why": "not-a-number"})
    stash_tab = _norm_stash_tab(j.get("stashTab") or j.get("stash_tab"), scene)
    chron_tab = _norm_chron_tab(j.get("chronicleTab") or j.get("chronicle_tab"), scene)
    discovered = [str(x).strip() for x in (j.get("discovered") or []) if str(x).strip()][:12]
    # v1818 — the chronicle's own dates, kept only when they are actually dates
    chron_sort = _norm_chron_sort(j.get("chronicleSort") or j.get("chronicle_sort"), scene)
    found_at, dropped_by = {}, {}
    try:
        _fa = j.get("foundAt") or j.get("found_at") or {}
        if isinstance(_fa, dict):
            for k3, v3 in list(_fa.items())[:80]:
                k3 = str(k3).strip()[:64]
                v3 = str(v3).strip()[:32]
                if not k3 or not v3:
                    continue
                if _chron_stamp_ok(v3):
                    found_at[k3] = v3
                else:
                    _audit["dropped"].append({"field": "foundAt", "from": v3[:24],
                                              "why": "not-a-timestamp"})
        _db = j.get("droppedBy") or j.get("dropped_by") or {}
        if isinstance(_db, dict):
            for k4, v4 in list(_db.items())[:80]:
                k4 = str(k4).strip()[:64]
                v4 = str(v4).strip()[:48]
                if k4 and v4 and not _chron_stamp_ok(v4):
                    dropped_by[k4] = v4
                elif k4 and v4:
                    _audit["dropped"].append({"field": "droppedBy", "from": v4[:24],
                                              "why": "looks-like-a-timestamp"})
    except Exception:
        found_at, dropped_by = {}, {}
    # ══ #54 — WHO IS WEARING IT, AND IN WHICH SLOT ═══════════════════════════════════════════════
    # REG-340 measured that the character's name is not on screen in play; it IS on the login /
    # character-select screen, and that screen had no scene word, so the classifier clamped it to
    # `gameplay` and the name it printed went nowhere. `char-select` is now a scene the parse keeps,
    # and a `character` is kept ONLY on that scene — on any other scene it is text the model saw
    # somewhere else (a merc, chat, another player) and is dropped with its reason.
    # `names_slot` (name -> doll slot) and `names_xy` (name -> [x, y] in frame pixels) are the two
    # independent answers equipped_ledger corroborates; the slot vocabulary is the doll's own
    # (slot_identity.DOLL_SLOTS), never a second list typed here. An unknown slot word is dropped,
    # a point that is not two numbers is dropped, and every drop is in the audit. Nothing here changes
    # READ_PROMPT: asking the model for these fields means bumping PROMPT_VER, which voids every
    # zero-page chronicle seal (control_app._chron_seal_current) — his call, REG-1522.
    # [[unknown-stays-unknown]] [[copy-drift]]
    # ⚠ REG-1558 — THE EXCEPT ARMS SAY UNKNOWN, NEVER A MEASURED EMPTY. A parse that raised did not
    # find "no character" / "no slot words" / "no points": it found nothing, and a caller reading ""
    # or {} cannot tell those apart. None is the honest answer, the audit says why, and every caller
    # (emit_deep_read -> the journal row -> equipped_ledger.worn_from_row) carries it as UNKNOWN.
    # The swallow census ratchets exactly this shape. This block sits ABOVE names_loc on purpose:
    # the census reads names_loc's `{}` arm as a checked sentinel only while the return that carries
    # it is within three statements, and #54's first cut, inserted below it, pushed that return out
    # of the window (a census +1 on a site nobody changed). [[unknown-stays-unknown]]
    character = ""
    try:
        _ch = j.get("character")
        if scene == "char-select" and isinstance(_ch, str) and _ch.strip():
            character = _ch.strip()[:32]
        elif _ch not in (None, "", {}, []):
            _audit["dropped"].append({"field": "character", "from": str(_ch)[:20],
                                      "why": ("not-a-login-scene" if scene != "char-select" else "not-a-name")})
    except Exception as _e_ch:
        _audit["dropped"].append({"field": "character", "why": "parse-raised", "err": type(_e_ch).__name__})
        character = None            # UNKNOWN — not "" (no name), which a login row would read as measured
    names_slot = {}
    try:
        raw_slot = j.get("names_slot") or {}
        if isinstance(raw_slot, dict):
            try:
                import slot_identity as _SI_slots
                _doll = _SI_slots.DOLL_SLOTS
            except Exception:
                _doll = None
            if _doll is None:
                # the vocabulary is what a slot word MEANS; with none, no word can be checked, so the
                # whole field is UNKNOWN — not {} ("the reader named no slots"), which is what it read as
                _audit["dropped"].append({"field": "names_slot", "why": "slot-vocabulary-unavailable",
                                          "count": len(raw_slot)})
                names_slot = None
            else:
                for k5, v5 in list(raw_slot.items())[:60]:
                    v5 = str(v5).strip().lower()
                    if v5 in _doll:
                        names_slot[str(k5).strip()] = v5
                    else:
                        _audit["dropped"].append({"field": "names_slot." + str(k5)[:30], "from": v5[:20], "why": "invalid-slot"})
    except Exception as _e_sl:
        _audit["dropped"].append({"field": "names_slot", "why": "parse-raised", "err": type(_e_sl).__name__})
        names_slot = None
    names_xy = {}
    try:
        raw_xy = j.get("names_xy") or {}
        if isinstance(raw_xy, dict):
            for k6, v6 in list(raw_xy.items())[:60]:
                try:
                    if isinstance(v6, (list, tuple)) and len(v6) == 2:
                        names_xy[str(k6).strip()] = [float(v6[0]), float(v6[1])]
                        continue
                except (TypeError, ValueError):
                    pass
                _audit["dropped"].append({"field": "names_xy." + str(k6)[:30], "from": str(v6)[:20], "why": "not-a-point"})
    except Exception as _e_xy:
        _audit["dropped"].append({"field": "names_xy", "why": "parse-raised", "err": type(_e_xy).__name__})
        names_xy = None
    names_loc = {}
    try:
        raw_loc = j.get("names_loc") or {}
        if isinstance(raw_loc, dict):
            for k2, v2 in list(raw_loc.items())[:60]:
                v2 = str(v2).strip().lower()
                if v2 in ("equipped", "inventory", "stash", "floor"):
                    names_loc[str(k2).strip()] = v2
                else:
                    _audit["dropped"].append({"field": "names_loc." + str(k2)[:30], "from": v2[:20], "why": "invalid-loc"})
    except Exception:
        names_loc = {}
    # v946.5 (Konyo: "was the Diadem read 3 socketed?") — capture the socket count per item.
    # name -> N (1..6). Read from the tooltip's 'Socketed (N)' line, never guessed from base type.
    sockets = {}
    try:
        raw_sk = j.get("sockets") or {}
        if isinstance(raw_sk, dict):
            for k3, v3 in list(raw_sk.items())[:60]:
                try:
                    n3 = int(v3)
                except Exception:
                    _audit["dropped"].append({"field": "sockets." + str(k3)[:30], "from": str(v3)[:12], "why": "not-an-int"})
                    continue
                if 1 <= n3 <= 6:   # every D2R socketable item holds 1..6
                    sockets[str(k3).strip()] = n3
                else:
                    _audit["dropped"].append({"field": "sockets." + str(k3)[:30], "from": str(n3), "why": "out-of-range-1-6"})
    except Exception:
        sockets = {}
    return {"area": str(j.get("area", "")).strip()[:48], "scene": scene, "names": names,
            "tz": tz, "conf": conf, "stashTab": stash_tab,
            "chronicleTab": chron_tab,   # v1512 — WHICH ledger; "" when unsure, never a guess
            "discovered": discovered,
            "names_loc": names_loc,
            "character": character,        # #54 — the login screen's name; "" everywhere else
            **_identity_fields(j, scene),  # v3855 - gameName / cls / level / avatarClass, never a password
            "names_slot": names_slot,      # #54 — name -> doll slot, the reader's word
            "names_xy": names_xy,          # #54 — name -> [x, y] frame point, the geometry's evidence
            "sockets": sockets,
            "chronicleSort": chron_sort,   # v1818 — newest|oldest|other|""
            "foundAt": found_at,           # v1818 — name -> the row's own First Found stamp
            "droppedBy": dropped_by,       # v1818 — name -> the monster on its Dropped By line
            "_parse_audit": dict(_audit, ok=True)}   # v835 — what the model SAID vs what survived

def _identity_fields(j, scene):
    """v3855 - read_identity.parse_identity, or nothing when it cannot load (the row stays UNKNOWN)."""
    try:
        import read_identity as _RI
        return _RI.parse_identity(j, scene)
    except Exception:
        return {}


def _intent_for(scene):
    """v723 — loot lifecycle: floor labels = seen (not farmed); inv/stash = farmed for real."""
    if scene in ("inventory", "stash"): return "farmed"
    if scene == "loot": return "seen"
    return "context"

# ═══ v731 — COMMITMENT VAULT (Konyo: ID→throw must NOT vault)
# floor SEEN → inv HOLDING (pending) → vault only after HOLD_MS still in bag OR town STASH
# drop to floor again = THROW-OUT (cancel pending / reverse mistaken vault)
# GONE alone never vaults. Junk never vaults. Anchors never vault.
# ═══ v738 — RUN #4 FIX (Konyo: Colossus Crossbow + Jewel)
# Stash panel must NOT vault random tooltip text (Blood Shield / Compendium / Unidentified).
# Stash-commit ONLY if name was SEEN (floor), HOLDING (inv), or gone-candidate this session.
# Never vault "Unidentified" / bare generics without a chain.
try:
    HOLD_MS = max(5000, int(os.environ.get("TV_HOLD_MS", "30000")))  # 30s default hold
except Exception:
    HOLD_MS = 30000

_JUNK_SUBSTR = (
    "healing potion", "mana potion", "rejuv", "rejuvenation", "stamina potion",
    "antidote potion", "thawing potion", "energy potion", "rancid", "bile", "gas potion",
    "arrows", "bolts", "quill", " gold",
)
# Bare / vision-fluff labels.
# v1576 HONESTY — this comment used to read "must never auto-vault without a real identity
# chain", which described a guard that NOTHING ENFORCES. Its only consumer is _is_weak_name()
# below, and _is_weak_name() has ZERO callers in the repo (grep: tv/, bible.html — one hit, its
# own def). Executed proof: LootLifecycle._on_loot(["Ring","Jewel"], ...) tags both "seen" (not
# "skip-weak") and the resulting chain carries them straight into _on_stash → _commit. The rule
# that IS live is the v738 universal chain gate in _on_stash (SEEN/HOLDING/candidate required
# for EVERY name) — which happens to be exactly what _is_weak_name's docstring asked for, so
# behaviour is unchanged; only the claim was false. Whether these bare labels should ALSO be
# barred from BUILDING that provenance in _on_loot is a product call — PARKED for Konyo, since
# a real D2R jewel's floor label literally is "Jewel" and gating it would lose true drops.
# Kept (not deleted) because the curated list is the input any future gate would use.
_WEAK_EXACT = frozenset({
    "jewel", "ring", "amulet", "shield", "armor", "sword", "bow", "helm", "boots",
    "gloves", "belt", "item", "charm", "scrollof", "scroll", "tome", "key",
    "superior", "ethereal", "unidentified", "unid", "great", "super", "greater",
    "waypoint", "portal",
})
def _norm_name(n):
    s = str(n or "").strip().lower()
    if s.endswith(")") and "(" in s:
        s = s[:s.rfind("(")].strip()
    # v796 (Grok R5 #3) — floor says 'Superior Colossus Crossbow', panel says 'Colossus
    # Crossbow': same physical item, two ledger keys, broken chain. Strip leading quality
    # prefixes (compound-safe, repeatable).
    for _ in range(2):
        for pre in ("ethereal ", "superior ", "eth "):
            if s.startswith(pre):
                s = s[len(pre):]
    return s

def _is_anchor(n):
    lo = _norm_name(n)
    return any(a in lo for a in (
        "horadric cube", "tome of town portal", "tome of identify",
    ))


# ── v948 SESSION STICKY (Konyo: shared/stash always-there items re-read every deep) ──
# Learns which names are stable this session (cube/tomes on inventory, worn gear, stash
# rows already hovered). Re-reports as ECHO (not NEW) until they MOVE or leave.
# New items + location changes stay first-class. Cleared on new SESSION_ID.
_SESSION_STICKY = {}   # norm_name -> {name, loc, tab, firstTs, lastTs, count}
_SESSION_STICKY_SID = ""


def _sticky_reset_if_new_session():
    global _SESSION_STICKY, _SESSION_STICKY_SID
    sid = SESSION_ID or ""
    if sid != _SESSION_STICKY_SID:
        _SESSION_STICKY = {}
        _SESSION_STICKY_SID = sid


def _classify_name_sticky(names, names_loc, stash_tab, scene, now_ms):
    """Split names into new / echo / moved for this session.
    Policy (brains 1–5 filter):
      1. first sighting of a name → NEW
      2. same name, different loc or stash tab → MOVED (re-report)
      3. anchors + equipped after first → ECHO (always-on UI)
      4. inventory non-anchor after first → ECHO (charms already held)
      5. stash same tab after first → ECHO (shared grid re-hover)
      floor / loot always prefers NEW if area changed (handled by text-eye clear);
      floor re-sight same area without gap → ECHO after first.
    Returns (names_new, names_echo, names_moved, tags_extra).
    """
    _sticky_reset_if_new_session()
    names = list(names or [])
    names_loc = names_loc or {}
    tab = str(stash_tab or "").lower()
    scene = str(scene or "")
    new, echo, moved = [], [], []
    tags = {}
    for n in names:
        k = _norm_name(n)
        if not k:
            continue
        loc = str(names_loc.get(n) or "").lower()
        # default loc by scene when model omitted names_loc
        if not loc:
            if scene == "stash":
                loc = "stash"
            elif scene == "inventory":
                loc = "inventory"
            elif scene == "loot":
                loc = "floor"
        prev = _SESSION_STICKY.get(k)
        if not prev:
            _SESSION_STICKY[k] = {
                "name": n, "loc": loc, "tab": tab if loc == "stash" else "",
                "firstTs": now_ms, "lastTs": now_ms, "count": 1,
            }
            new.append(n)
            tags[n] = "first-seen"
            continue
        prev["lastTs"] = now_ms
        prev["count"] = int(prev.get("count") or 0) + 1
        prev_loc = str(prev.get("loc") or "")
        prev_tab = str(prev.get("tab") or "")
        loc_changed = prev_loc and loc and prev_loc != loc
        tab_changed = (loc == "stash" and prev_tab and tab and prev_tab != tab)
        if loc_changed or tab_changed:
            prev["loc"] = loc
            if loc == "stash":
                prev["tab"] = tab
            moved.append(n)
            new.append(n)  # still "newsworthy"
            tags[n] = "moved:" + (prev_loc or "?") + "→" + (loc or "?")
            continue
        # stable position — sticky echo for always-on UI pieces
        if _is_anchor(n) or loc == "equipped":
            echo.append(n)
            tags[n] = "echo-sticky"
            continue
        if loc == "inventory":
            echo.append(n)
            tags[n] = "echo-sticky"
            continue
        if loc == "stash" and tab:
            # same tab re-hover of same name (shared grid always shows many items)
            echo.append(n)
            tags[n] = "echo-sticky"
            continue
        if loc == "floor":
            # re-seen on floor without area clear — still echo after first
            echo.append(n)
            tags[n] = "echo-sticky"
            continue
        # unknown loc: treat as echo after first to kill spam
        echo.append(n)
        tags[n] = "echo-sticky"
    return new, echo, moved, tags

def _is_junk(n):
    lo = _norm_name(n)
    if lo in ("arrows", "bolts", "key", "gold") or lo.endswith(" gold") or lo.isdigit():
        return True
    if lo.endswith("gold") and any(c.isdigit() for c in lo):
        return True
    return any(j in lo for j in _JUNK_SUBSTR)

def _is_never_vault(n):
    """Hard ban — never farmed/vaulted even if 'seen' as label (run #4 Unidentified)."""
    lo = _norm_name(n)
    if not lo:
        return True
    if "unidentified" in lo or lo in ("unid", "unidentified item"):
        return True
    if lo in ("waypoint", "portal", "identify", "repair"):
        return True
    return False

def _is_weak_name(n):
    """UNREACHABLE as of v1576 — kept as the reference predicate for _WEAK_EXACT, NOT a live gate.

    Original claim: "Too generic alone — only stash-commits if already SEEN/HOLDING/candidate."
    That rule is real and IS enforced — but by the v738 chain gate in _on_stash, for every name,
    not by this function. This function has no caller (see the _WEAK_EXACT block above for the
    grep + executed evidence). Do not read a call to it into the pipeline; there isn't one.
    If you wire it up, that is a behaviour change: it would also reject bare-but-genuine floor
    labels ("Jewel"), which is the parked product question, not a bug fix."""
    lo = _norm_name(n)
    if _is_never_vault(n):
        return True
    if lo in _WEAK_EXACT:
        return True
    # single short token with no space (e.g. OCR crumbs)
    if " " not in lo and len(lo) < 5:
        return True
    return False

def _area_key(a):
    return str(a or "").strip().lower()

def _is_town_area(area):
    """UNREACHABLE as of v1576 — zero callers repo-wide (grep tv/ bible.html: one hit, this def).
    No town-specific branch exists anywhere in the engine; nothing suppresses reads or loot
    provenance in town today. Kept as the town-name table any such gate would need. Whether the
    engine SHOULD gate on town is a product call — PARKED, not guessed at here."""
    lo = _area_key(area)
    return any(t in lo for t in (
        "rogue encampment", "lut gholein", "kurast docks", "kurast",
        "pandemonium fortress", "harrogath", "town",
    ))

class LootLifecycle:
    """Object permanence + commitment: pending hold → vault; throw-out cancels."""
    def __init__(self):
        self.seen = {}           # floor ledger
        self.candidates = {}     # gone-from-floor pickup candidates
        self.pending = {}        # inv-held, NOT vaulted yet {name, firstHeld, lastHeld, tag}
        self.vaulted = {}        # committed {name, reason, ts}
        self.thrown = []         # ring of throw-out events
        self.confirmed = []      # ring of vault commits

    def restore(self, snap, keyfn):
        """v768 (Grok R2) — the lifecycle survives OFF→ON/crash restarts: rehydrate the chain
        from the last persisted snapshot so a stash read after a restart still finds its
        floor-proven names (no more 'stash-no-chain' for items the run honestly SAW)."""
        try:
            now_ms = int(time.time() * 1000)
            for v in (snap.get("seen") or []):
                n = v.get("name");  k = keyfn(n)
                if n and k not in self.seen:
                    self.seen[k] = {"name": n, "area": v.get("area", ""), "ts": now_ms}
            for v in (snap.get("pending") or []):
                n = v.get("name");  k = keyfn(n)
                if n and k not in self.pending:
                    self.pending[k] = {"name": n, "firstHeld": now_ms, "lastHeld": now_ms,
                                       "tag": v.get("tag", "")}
            for v in (snap.get("candidates") or []):
                n = v.get("name");  k = keyfn(n)
                if n and k not in self.candidates:
                    self.candidates[k] = {"name": n, "ts": now_ms}
            for v in (snap.get("vaulted") or []):
                n = v.get("name");  k = keyfn(n)
                if n and k not in self.vaulted:
                    self.vaulted[k] = {"name": n, "reason": v.get("reason", ""), "ts": now_ms}
            return True
        except Exception:
            return False

    def snapshot(self):
        return {
            "holdMs": HOLD_MS,
            "pending": [{"name": v["name"], "heldMs": 0, "tag": v.get("tag", "")}
                        for v in list(self.pending.values())[-40:]],
            "vaulted": [{"name": v["name"], "reason": v.get("reason", "")}
                        for v in list(self.vaulted.values())[-40:]],
            "seen": [{"name": v["name"], "area": v.get("area", "")}
                     for v in list(self.seen.values())[-40:]],
            "candidates": [{"name": v["name"]} for v in self.candidates.values()],
            "thrown": self.thrown[-20:],
            "confirmed": self.confirmed[-40:],
        }

    def process(self, scene, names, area, conf, now_ms=None, names_loc=None):
        now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
        names = [str(n).strip() for n in (names or []) if str(n).strip()]
        # v830 (Konyo forensics) — LOCATION TRUTH: equipped gear is the player's OWN worn kit
        # (never vault, never hold — tag only); an inventory-side tooltip while the stash is
        # open is HELD loot (hold flow), not a stash commit.
        names_loc = names_loc or {}
        equipped = [n for n in names if names_loc.get(n) == "equipped"]
        inv_side = [n for n in names if names_loc.get(n) == "inventory"]
        if equipped:
            names = [n for n in names if n not in equipped]
        out = {
            "vault_names": [],      # ONLY these may hit tvVaultRegister
            "pending_names": [],    # holding — show HOLDING, not vault
            "thrown_names": [],
            "farmed_names": [],     # alias of vault_names for board compat
            "lifecycle_tags": {},
            "anchor": "n/a",
            "gone_candidates": [],
        }
        if scene == "loot":
            self._on_loot(names, area, now_ms, out)
        elif scene == "inventory":
            self._on_inventory(names, area, conf, now_ms, out)
        elif scene == "stash":
            # v830 — inventory-side names route to the HOLD flow; only true stash-panel
            # names may commit to the vault.
            if inv_side:
                stash_side = [n for n in names if n not in inv_side]
                self._on_inventory(inv_side, area, conf, now_ms, out)
                self._on_stash(stash_side, area, conf, now_ms, out)
            else:
                self._on_stash(names, area, conf, now_ms, out)
        # refresh pending heldMs for snapshot consumers
        for k, p in self.pending.items():
            p["heldMs"] = max(0, now_ms - p["firstHeld"])
        for n in equipped:
            out["lifecycle_tags"][n] = "equipped"   # v830 — worn gear: tag only, chronicle-tally on the board
        out["farmed_names"] = list(out["vault_names"])
        out["pending_names"] = [p["name"] for p in self.pending.values()]
        return out

    def _has_chain(self, n):
        """v738 — floor SEEN, inv HOLDING, or gone-candidate this session."""
        k = _norm_name(n)
        return bool(k) and (k in self.seen or k in self.pending or k in self.candidates)

    def _commit(self, n, reason, now_ms, out, tag=None):
        k = _norm_name(n)
        if k and n not in (out.get("chain") or {}):
            out.setdefault("chain", {})[n] = self._chain_snapshot(k, n)   # v856 — hold-commit path snapshots pre-pop
        if not k or _is_junk(n) or _is_anchor(n) or _is_never_vault(n):
            if _is_never_vault(n) and not _is_anchor(n) and not _is_junk(n):
                out["lifecycle_tags"][n] = "skip-weak"
            return
        if k in self.vaulted:
            # v796 (Grok R5 #3) — MULTISET: a SECOND physical drop of the same name re-enters
            # the chain (commit cleared its provenance, so seen/candidates/pending presence
            # means a genuinely new sighting). Re-vault + count. No fresh provenance = the
            # same instance echoing → still already-vaulted.
            if not (k in self.seen or k in self.candidates or k in self.pending):
                out["lifecycle_tags"][n] = "already-vaulted"
                return
            v = self.vaulted[k]
            v["count"] = int(v.get("count") or 1) + 1
            v["ts"] = now_ms
            self.pending.pop(k, None); self.candidates.pop(k, None); self.seen.pop(k, None)
            self.confirmed.append({"ts": now_ms, "name": n, "reason": reason, "tag": tag or reason, "instance": v["count"]})
            del self.confirmed[:-80]
            out["vault_names"].append(n)
            out["lifecycle_tags"][n] = "vault:" + reason + " ×" + str(v["count"])
            return
        self.vaulted[k] = {"name": n, "reason": reason, "ts": now_ms, "count": 1}
        self.pending.pop(k, None)
        self.candidates.pop(k, None)
        self.seen.pop(k, None)   # v796 — commit consumes provenance; only a FRESH sighting re-vaults
        self.confirmed.append({"ts": now_ms, "name": n, "reason": reason, "tag": tag or reason})
        del self.confirmed[:-80]
        out["vault_names"].append(n)
        out["lifecycle_tags"][n] = "vault:" + reason

    def _throw_out(self, n, now_ms, out, why="dropped"):
        k = _norm_name(n)
        if not k:
            return
        was_pending = k in self.pending
        was_vaulted = k in self.vaulted
        self.pending.pop(k, None)
        self.candidates.pop(k, None)
        if was_vaulted:
            self.vaulted.pop(k, None)
            out.setdefault("unvault_names", []).append(n)
        if was_pending or was_vaulted:
            self.thrown.append({"ts": now_ms, "name": n, "why": why})
            del self.thrown[:-40]
            out["thrown_names"].append(n)
            out["lifecycle_tags"][n] = "throw-out"

    def _on_loot(self, names, area, now_ms, out):
        present = {}
        for n in names:
            if _is_anchor(n) or _is_junk(n):
                if _is_junk(n):
                    out["lifecycle_tags"][n] = "junk"
                continue
            if _is_never_vault(n):
                out["lifecycle_tags"][n] = "skip-weak"
                continue
            k = _norm_name(n)
            if not k:
                continue
            present[k] = n
            # THROW-OUT: was holding or vaulted, now on floor again
            if k in self.pending or k in self.vaulted:
                self._throw_out(n, now_ms, out, why="floor-again")
            e = self.seen.get(k)
            if not e:
                self.seen[k] = {"name": n, "area": area or "", "firstSeen": now_ms,
                                "lastSeen": now_ms, "count": 1, "miss": 0}
            else:
                e["lastSeen"] = now_ms
                e["count"] = e.get("count", 0) + 1
                e["miss"] = 0
                if area:
                    e["area"] = area
            if n not in out["lifecycle_tags"]:
                out["lifecycle_tags"][n] = "seen"
        ak = _area_key(area)
        if not ak:
            return
        for k, e in list(self.seen.items()):
            if _area_key(e.get("area")) != ak or k in present:
                continue
            e["miss"] = e.get("miss", 0) + 1
            if e["miss"] == 1:
                continue
            self.candidates[k] = {"name": e["name"], "area": e.get("area", ""), "goneAt": now_ms}
            out["gone_candidates"].append(e["name"])
            out["lifecycle_tags"][e["name"]] = "gone-candidate"

    def _track_pending(self, n, tag, now_ms, out):
        k = _norm_name(n)
        if not k:
            return
        if k in self.vaulted and not (k in self.seen or k in self.candidates):
            out.setdefault("chain", {})[n] = self._chain_snapshot(k, n)   # v856 — echo path snapshots too
            out["lifecycle_tags"][n] = "already-vaulted"   # v796 — fresh floor provenance may hold a 2nd instance
            return
        if _is_never_vault(n):
            out["lifecycle_tags"][n] = "skip-weak"
            return
        p = self.pending.get(k)
        if not p:
            self.pending[k] = {"name": n, "firstHeld": now_ms, "lastHeld": now_ms, "tag": tag}
            out["lifecycle_tags"][n] = "holding"
        else:
            p["lastHeld"] = now_ms
            p["name"] = n
            held = now_ms - p["firstHeld"]
            if held >= HOLD_MS:
                self._commit(n, "hold", now_ms, out, tag=p.get("tag") or tag)
            else:
                out["lifecycle_tags"][n] = "holding"
                out.setdefault("_holding_ms", {})[n] = held

    def _on_inventory(self, names, area, conf, now_ms, out):
        anchors_hit = [n for n in names if _is_anchor(n)]
        out["anchor"] = "ok" if anchors_hit else "missing"
        low_conf = out["anchor"] == "missing" and (conf is None or conf < 0.75)
        present = set()
        for n in names:
            if _is_anchor(n):
                out["lifecycle_tags"][n] = "anchor"
                continue
            if _is_junk(n):
                out["lifecycle_tags"][n] = "junk"
                continue
            k = _norm_name(n)
            if not k:
                continue
            present.add(k)
            if low_conf:
                out["lifecycle_tags"][n] = "hold-low-conf"
                out["apply_held"] = "anchor-missing"
                continue
            was_cand = k in self.candidates
            was_seen = k in self.seen
            if was_cand:
                tag = "seen→gone→inventory"
            elif was_seen:
                tag = "seen→inventory"
            else:
                tag = "inventory-only"
            self._track_pending(n, tag, now_ms, out)
        # pending items missing from inv — not throw-out yet (may be stash/cube); leave pending
        # (throw-out only when we SEE them on the floor again)
        for k, p in list(self.pending.items()):
            if k not in present and k not in self.vaulted:
                # keep pending; user may have put in cube or closed panel mid-ID
                pass

    def _chain_snapshot(self, k, n):
        """v855 (A2.4) — provenance AT DECISION TIME, so 'stash-no-chain' is diagnosable:
        never-seen vs seen-then-lost vs already-owned. Journaled with the read."""
        c = {"seen": k in self.seen, "pending": k in self.pending,
             "candidate": k in self.candidates, "vaulted": k in self.vaulted}
        try:
            e = self.seen.get(k) or {}
            if e.get("firstSeen"):
                c["firstSeen"] = e["firstSeen"]
                c["seenArea"] = e.get("area", "")
                c["seenCount"] = e.get("count", 1)
            p = self.pending.get(k) or {}
            if p.get("firstHeld"):
                c["firstHeld"] = p["firstHeld"]
            v = self.vaulted.get(k) or {}
            if v.get("ts"):
                c["vaultedTs"] = v["ts"]
                c["vaultCount"] = v.get("count", 1)
        except Exception:
            pass
        # v856 (Grok R18a) — one-glance failure class, closed enum
        if c["vaulted"] and not (c["seen"] or c["pending"] or c["candidate"]):
            c["class"] = "wiped-by-commit"
        elif c["pending"]:
            c["class"] = "hold-chain"
        elif c["seen"] or c["candidate"]:
            c["class"] = "full-chain"
        else:
            c["class"] = "never-seen"
        c["path"] = ("seen→gone→stash" if c["candidate"] else
                     "holding→stash" if c["pending"] else
                     "seen→stash" if c["seen"] else "")
        return c

    def _on_stash(self, names, area, conf, now_ms, out):
        # v738 — stash-commit ONLY with object-permanence chain (SEEN / HOLDING / candidate).
        # Panel-greedy vault of random shared-tab tooltips caused run #4 false farmed.
        out["anchor"] = "ok" if names else "missing"
        out.setdefault("chain", {})
        for n in names:
            if _is_anchor(n):
                out["lifecycle_tags"][n] = "anchor"
                continue
            if _is_junk(n):
                out["lifecycle_tags"][n] = "junk"
                continue
            if _is_never_vault(n):
                out["lifecycle_tags"][n] = "skip-weak"
                continue
            k = _norm_name(n)
            if not k:
                continue
            out["chain"][n] = self._chain_snapshot(k, n)   # v855 — provenance at the moment of decision
            if k in self.vaulted and not (k in self.candidates or k in self.seen or k in self.pending):
                out["lifecycle_tags"][n] = "already-vaulted"   # v796 — a fresh 2nd instance flows to _commit instead
                continue
            was_cand = k in self.candidates
            was_seen = k in self.seen
            was_pend = k in self.pending
            if not (was_cand or was_seen or was_pend):
                # no floor/inv provenance this session — do NOT vault (Blood Shield class)
                out["lifecycle_tags"][n] = "stash-no-chain"
                continue
            if was_cand:
                tag = "seen→gone→stash"
            elif was_pend:
                tag = "holding→stash"
            elif was_seen:
                tag = "seen→stash"
            else:
                tag = "stash-commit"
            self._commit(n, "stash", now_ms, out, tag=tag)

_LIFECYCLE = LootLifecycle()

def _read_score(rd):
    if not rd: return -1
    conf = rd.get("conf")
    if conf is None: conf = 0.5
    return len(rd.get("names") or []) * 10 + conf * 10 + (2 if rd.get("area") else 0)

def _needs_escalate(rd):
    """Haiku → Sonnet when accuracy is suspect. Empty gameplay/town is honest, not a miss."""
    if rd is None: return True
    conf = rd.get("conf")
    scene = rd.get("scene") or "gameplay"
    names = rd.get("names") or []
    # ground loot should show labels if the player paused on a pile
    if scene == "loot" and not names: return True
    # any claimed names with low conf — recheck before we trust them
    if names and conf is not None and conf < 0.55: return True
    # farmed panels with shaky conf on non-empty claims — recheck before auto-vault
    if scene in ("inventory", "stash") and names and conf is not None and conf < 0.7: return True
    return False

_SLOT_DEATHS = deque(maxlen=8)   # v891 (Grok C1) — timestamps of worker deaths
_THROTTLED_UNTIL = [0.0]
def _note_slot_death():
    """v891 — 2+ worker deaths inside 60s = subscription throttle cascade: soft-degrade for
    120s (heartbeat sheds to 1 via the cap, gap breathes) and SAY SO instead of silent empties."""
    now = time.time()
    _SLOT_DEATHS.append(now)
    recent = [t for t in _SLOT_DEATHS if now - t <= 60.0]
    if len(recent) >= 2 and now >= _THROTTLED_UNTIL[0]:
        _THROTTLED_UNTIL[0] = now + 120.0
        ev("cap", "🐢 THROTTLED — 2+ reader deaths in 60s (subscription pace?) · soft-degrade 120s, reads breathe")
        print("  🐢 throttle cascade detected — degrading softly for 120s")


def _is_throttled():
    return time.time() < _THROTTLED_UNTIL[0]


#: BOTH — after this many Claude misses in a row, the lane is down. One miss is one backup.
CLAUDE_LANE_DOWN_AFTER = 3
#: One frame asks Claude again after this long. An answer puts Claude back first.
CLAUDE_LANE_PROBE_S = 180.0
_CLAUDE_LANE = {"streak": 0, "until": 0.0, "why": None}
_CLAUDE_LANE_LOCK = threading.Lock()
_CLAUDE_PROBE = object()


def _claude_lane_skip_why():
    """BOTH only. None: ask Claude. _CLAUDE_PROBE: this one frame asks Claude again.
    A string: do not call Claude; hand that why to the backup."""
    if _reader_choice() != "both":
        return None
    with _CLAUDE_LANE_LOCK:
        if int(_CLAUDE_LANE["streak"] or 0) < CLAUDE_LANE_DOWN_AFTER:
            return None
        now = time.monotonic()
        if now >= float(_CLAUDE_LANE["until"] or 0.0):
            _CLAUDE_LANE["until"] = now + CLAUDE_LANE_PROBE_S
            return _CLAUDE_PROBE
        return _CLAUDE_LANE["why"] or "claude not reading"


def _claude_lane_observe(answered, why=None):
    """A parsed Claude answer clears the down lane. A miss counts toward it."""
    with _CLAUDE_LANE_LOCK:
        if answered:
            _CLAUDE_LANE["streak"] = 0
            _CLAUDE_LANE["until"] = 0.0
            _CLAUDE_LANE["why"] = None
            return
        _CLAUDE_LANE["streak"] = int(_CLAUDE_LANE["streak"] or 0) + 1
        if _CLAUDE_LANE["streak"] >= CLAUDE_LANE_DOWN_AFTER:
            _CLAUDE_LANE["why"] = "claude not reading"
            _CLAUDE_LANE["until"] = time.monotonic() + CLAUDE_LANE_PROBE_S
        else:
            _CLAUDE_LANE["why"] = str(why or "claude no answer")


_ONESHOT_GATE = threading.Semaphore(1)   # v864 — a throttled pool must not herd 8 oneshots
_ASK_NONE_STREAK = 0
def _reader_choice():
    """#151 HIS SWITCH, read at the moment of each read. -> "claude" | "both" | "grok" ("claude" when the Grok module is
    absent, which is also the only position a PC without it can be on)."""
    try:
        import g5_grok_eyes as _G5r
        return _G5r.reader()
    except Exception:
        return "claude"


#: #151 — at most this many Grok-only reads at once (Claude's one-shot gate is about Claude's throttle, not Grok's)
_GROK_ONLY_GATE = threading.BoundedSemaphore(2)
#: #151 — why the last Grok-only read did not happen, for the deep-read row that says so
_GROK_ONLY_LAST = {"why": None}
#: BOTH — one shared cell, and the live path does not record through it. Each read carries
#: its own why/fail. This name stays so a proof can point a backup back at the shared cell.
_BACKUP_LAST = {"why": None, "fail": None}
#: the keys g5_vision_read stamps on its answer - not the reader's words
_G5_STAMP_KEYS = ("model", "mode", "escalated", "ms", "_raw_txt", "_g5", "_lane", "_g5_fixed")


def _with_xy_space(rd, ap):
    """v3552 (#234) — a read that POINTED at items carries the size of the picture it pointed in (`xySpace` [w, h]).
    The reader may see a downscaled copy (the 1568px read spec) while the reel keeps a larger frame, so a point is only
    a place once its space is known; equipped_ledger scales it to the frame it files against. -> rd, unchanged otherwise.
    A size that cannot be read is None (UNKNOWN), never the frame's size assumed."""
    if not isinstance(rd, dict) or not rd.get("names_xy"):
        return rd
    try:
        import equipped_ledger as _EL
        _sz = _EL.jpeg_size(ap)
    except Exception:
        _sz = None
    rd["xySpace"] = [int(_sz[0]), int(_sz[1])] if _sz else None
    return rd


def _grok_only_failed(why):
    why = str(why or "the Grok CLI gave no answer")[:200]
    _GROK_ONLY_LAST["why"] = why
    ev("cap", "GROK ONLY - not read: %s" % why)
    journal_skip("grok-only", why)
    return None


def _grok_oneshot(ap, timeout=90, prompt=None, raw_json=False, backed=None):
    """#151 — one read on the Grok CLI ALONE (his switch at GROK ONLY). -> what _oneshot returns, or None with the reason
    said. NEVER hands the frame to Claude: a failed Grok read is a failed read, left owed for the next pass.
    REG-1941 - `backed["asked"]` is set only once the Grok read is really called (see _oneshot)."""
    try:
        import g5_grok_eyes as _G5o
    except Exception as e:
        return _grok_only_failed("the Grok module would not load (%s)" % type(e).__name__)
    _why = _G5o.grok_only_blocked_why()
    if _why:
        return _grok_only_failed(_why)
    if not _GROK_ONLY_GATE.acquire(timeout=max(1.0, float(timeout or 90))):
        return _grok_only_failed("two Grok reads were already running for the whole wait")
    try:
        if isinstance(backed, dict):
            backed["asked"] = "grok"
        gr = _G5o.g5_vision_read(ap, prompt=(prompt if prompt else READ_PROMPT.format(path=ap)))
    except Exception as e:
        gr = None
        _G5o._STATS["last_error"] = "%s: %s" % (type(e).__name__, str(e)[:120])
    finally:
        _GROK_ONLY_GATE.release()
    if not isinstance(gr, dict):
        return _grok_only_failed(_G5o._STATS.get("last_error"))
    _GROK_ONLY_LAST["why"] = None
    body = {k: v for k, v in gr.items() if k not in _G5_STAMP_KEYS}
    globals()["_LAST_RAW"] = str(gr.get("_raw_txt") or "")[:2048]
    if raw_json:
        return body
    pr = _parse_read(json.dumps(body, ensure_ascii=False))
    if pr is not None:
        # REG-1716 — what Grok's own parse rewrote before this one saw it goes into the same audit the journal carries
        _gfix = [x for x in (gr.get("_g5_fixed") or []) if isinstance(x, dict)]
        if _gfix and isinstance(pr.get("_parse_audit"), dict):
            pr["_parse_audit"]["dropped"] = list(pr["_parse_audit"].get("dropped") or []) + _gfix
        pr["_raw_txt"] = str(gr.get("_raw_txt") or "")[:2048]
        pr["model"] = "grok-subscription-cli"
        pr["mode"] = "g5-only"
    return pr


def _claude_miss_why():
    """Why the Claude read that just returned nothing did not happen. A label, not a guess of the picture."""
    try:
        blocked = _sub_budget_check("oneshot")
    except Exception:
        blocked = None
    if blocked:
        return "claude over budget"
    raw = str(globals().get("_LAST_RAW") or "").lower()
    if any(w in raw for w in ("authenticate", "oauth", "not logged", "signed out", "unauthorized")):
        return "claude signed out"
    if "command not found" in raw or "no such file or directory" in raw:
        return "claude cli missing"
    return "claude no answer"


def _note_claude_miss(why):
    """Say the Claude miss on the reel. The backup has not been asked yet, and this does not ask it."""
    why = str(why or "claude no answer")
    try:
        if why == "claude throttled":
            journal_skip("throttled", why)
        elif why == "claude over budget":
            blocked = _sub_budget_check("oneshot") or why
            ev("cap", blocked)
            journal_skip("sub-budget", blocked)
        elif why == "claude timed out":
            ev("cap", "vision timed out - Claude did not answer")
            journal_skip("timeout", why)
        elif why == "claude not reading":
            ev("cap", "BOTH - Claude is not reading, so this frame goes to Grok")
            journal_skip("claude-down", why)
        else:
            journal_skip("parse-null", why)
    except Exception:
        pass
    return why


def _not_read_note(fallback, backed=None):
    """The panel-lane refusal. A backup that also failed replaces the generic sentence with its why."""
    fail = (backed or {}).get("fail")
    return str(fail)[:200] if fail else fallback


def _unread_frame(empty, why, backed=None):
    """BOTH, and neither reader answered. UNKNOWN: mode empty, the reason said, never a gameplay verdict."""
    backed = backed or {}
    label = backed.get("why") or ("backup: %s" % (why or "claude no answer"))
    fail = backed.get("fail") or label
    globals()["_LAST_RAW"] = str(fail)[:400]
    return dict(empty, mode="empty", readFailed=True, readErr=str(fail)[:200],
                eye="unread", backup=str(label)[:160])


def _grok_backup(ap, claude_why, prompt=None, raw_json=False, timeout=90, backed=None):
    """ONE Grok read of a frame Claude did not read. Never called when Claude answered.

    The Claude gate is already released, so the next frame's Claude read does not wait on this one.
    One attempt: no second call when this one fails or hangs. The hourly cap is the one inside
    g5_vision_read, shared with every other Grok read. The reason is written on `backed`, the dict
    this call was handed, because up to eight frames run at once and a shared cell would cross them."""
    if backed is None:
        backed = {"why": None, "fail": None}
    claude_why = str(claude_why or "claude no answer")
    label = "backup: %s" % claude_why
    backed["why"] = label
    backed["fail"] = None
    try:
        import g5_grok_eyes as _G5b
    except Exception as e:
        backed["fail"] = "%s — the Grok module would not load (%s)" % (label, type(e).__name__)
        journal_skip("backup", backed["fail"])
        return None
    if not _G5b._grok_bin():
        backed["fail"] = "%s — Grok is not installed on this PC" % label
        journal_skip("backup", backed["fail"])
        return None
    if not _G5b.has_subscription():
        backed["fail"] = "%s — Grok is not signed in on this PC" % label
        journal_skip("backup", backed["fail"])
        return None
    if not _GROK_ONLY_GATE.acquire(timeout=max(1.0, float(timeout or 90))):
        backed["fail"] = "%s — a Grok read was already running for the whole wait" % label
        journal_skip("backup", backed["fail"])
        return None
    try:
        # REG-2006 (the #231 eye on v3576) - "Grok stepped in" counts frames Grok was ASKED (note_backup's own contract):
        # counted here, past the install, sign-in and one-Grok gate, never for a frame refused before any ask.
        _G5b.note_backup(label)
    except Exception:
        pass
    try:
        backed["asked"] = backed.get("asked") or "grok"   # REG-1941 - a Claude call that already ran stays the spend
        gr = _G5b.g5_vision_read(ap, prompt=(prompt if prompt else READ_PROMPT.format(path=ap)))
    except Exception as e:
        gr = None
        _G5b._STATS["last_error"] = "%s: %s" % (type(e).__name__, str(e)[:120])
    finally:
        _GROK_ONLY_GATE.release()
    if not isinstance(gr, dict):
        err = _G5b._STATS.get("last_error") or "Grok gave no answer"
        backed["fail"] = "%s — %s" % (label, err)
        journal_skip("backup", backed["fail"])
        return None
    kept = {}
    for k, v in gr.items():
        if k not in _G5_STAMP_KEYS:
            kept[k] = v
    body = kept
    globals()["_LAST_RAW"] = str(gr.get("_raw_txt") or "")[:2048]
    if raw_json:
        if isinstance(body, dict):
            body["eye"] = "grok"
            body["backup"] = label
        return body
    pr = _parse_read(json.dumps(body, ensure_ascii=False))
    if pr is None:
        backed["fail"] = "%s — Grok gave no readable answer" % label
        journal_skip("backup", backed["fail"])
        return None
    _gfix = [x for x in (gr.get("_g5_fixed") or []) if isinstance(x, dict)]
    if _gfix and isinstance(pr.get("_parse_audit"), dict):
        pr["_parse_audit"]["dropped"] = list(pr["_parse_audit"].get("dropped") or []) + _gfix
    pr["_raw_txt"] = str(gr.get("_raw_txt") or "")[:2048]
    pr["model"] = "grok-subscription-cli"
    pr["mode"] = "g5-backup"
    pr["eye"] = "grok"
    pr["backup"] = label
    return pr


def _oneshot(ap, model, timeout=90, prompt=None, raw_json=False, allow_backup=True, claude_miss=None, backed=None, lane_probe=False):
    """v864 — serialized: under subscription throttle all 8 workers can time out together;
    eight parallel one-shot bridges would herd the same throttle. One at a time.

    v1196 — the gate wait and the subprocess call each got the FULL `timeout` independently:
    a caller queued behind another one-shot (exactly the throttle-cascade this gate exists
    for — the scenario where several readers ALL fall to the bridge at once) could wait up to
    `timeout` just to acquire the gate, then get a fresh `timeout` for the run itself — up to
    2×timeout wall-clock for one call. Every caller passes LIVE_READ_TIMEOUT_S here specifically
    so a single live read can't exceed that budget (the Master Brain law); silently doubling it
    under the exact contention this gate was built to serialize defeated that. Spend the two
    phases OUT OF the same budget instead: whatever the wait cost, the run gets what's left.

    v1200 — `t0`/elapsed here is monotonic, not wall-clock: a backward NTP jump during the
    gate wait would otherwise make the wall-clock elapsed calculation go negative, INFLATING
    `remaining` well past the caller's intended budget — the same clock-skew class as
    VisionWorker.ask(), just bending the number the other way (too much budget instead of
    too little)."""
    # REG-1941 - `backed["asked"]` says which reader was ACTUALLY called ("claude" / "grok"), or None when none was:
    # the gate stayed busy for the whole wait, the budget stopped it, Grok was blocked. char_select spends an hourly slot
    # on a read that came back empty only when it was asked - it used to match one note string, which the BOTH backup's
    # own words never were, so a Claude timeout under BOTH was re-asked on every tick with no slot spent.
    if backed is None:
        backed = {"why": None, "fail": None}
    backed["asked"] = None
    if _reader_choice() == "grok":   # #151 his switch at GROK ONLY: this frame goes to the Grok CLI and nowhere else
        return _grok_oneshot(ap, timeout=timeout, prompt=prompt, raw_json=raw_json, backed=backed)
    # The Claude call finishes, and the gate is released, before any backup. A frame Claude
    # answered — names or "nothing here" — returns here and Grok is not asked. A timeout is a
    # non-read, caught here so it can be that one backup instead of escaping the caller.
    # `backed` belongs to THIS call. Eight frames can be in flight; the Claude call is the only
    # part that runs one at a time, so a module cell would hand one frame another's reason.
    backed["why"] = None
    backed["fail"] = None
    why = str(claude_miss) if claude_miss else None
    if not why and not lane_probe and allow_backup:
        _lane = _claude_lane_skip_why()
        if _lane is _CLAUDE_PROBE:
            lane_probe = True
        elif _lane:
            why = _lane
    result = None
    if why:
        _note_claude_miss(why)
    else:
        t0 = time.monotonic()
        if not _ONESHOT_GATE.acquire(timeout=timeout):
            why = "claude no answer"
        else:
            try:
                remaining = max(1.0, float(timeout) - (time.monotonic() - t0))
                backed["asked"] = "claude"
                try:
                    result = _oneshot_inner(ap, model, remaining, prompt=prompt, raw_json=raw_json)
                except subprocess.TimeoutExpired:
                    result = None
                    why = "claude timed out"
            finally:
                _ONESHOT_GATE.release()
            if result is None and not why:
                why = _claude_miss_why()
                if why == "claude over budget":
                    backed["asked"] = None   # _oneshot_inner's own budget check stopped it before any call
        if _reader_choice() == "both" and allow_backup:
            _claude_lane_observe(result is not None, why)
    if result is not None:   # Claude answered, even with nothing here: Grok is not asked
        if isinstance(result, dict):
            result.setdefault("eye", "claude")
        return result
    if not allow_backup or _reader_choice() != "both":
        return None
    return _grok_backup(ap, why or "claude no answer", prompt=prompt, raw_json=raw_json,
                        timeout=timeout, backed=backed)


def _oneshot_inner(ap, model, timeout=90, prompt=None, raw_json=False):
    """v1519 — `prompt` / `raw_json` are the CHRONICLE seam, and both default to the old behaviour so
    every existing caller is byte-identical. The chronicle read asks a different question (found-state
    per row, not item names) and its answer must NOT go through _parse_read, which would shape it into
    the item contract and throw the found/notFound split away."""
    """One cold `claude -p` on subscription (strict-mcp, no API key).

    v1379 — circuit-breaker + lean CLI (no monorepo project load / no session persist)."""
    blocked = _sub_budget_check("oneshot")
    if blocked:
        ev("cap", blocked)
        journal_skip("sub-budget", blocked)
        return None
    env, stripped = _claude_env()
    _log_auth_once(stripped)
    add = [FRAMES]
    ap_dir = os.path.dirname(os.path.abspath(ap)) if ap else ""
    if ap_dir and os.path.isdir(ap_dir):
        add.append(ap_dir)
    args = _claude_lean_args(model, stream=False, add_dirs=add)
    # v1463 — insert the prompt after the "-p" FLAG, located by index. The old
    # `args[:2] + [PROMPT] + args[2:]` hard-coded "the binary is exactly argv[0]", which
    # v1461's TV_CLAUDE_ARGV seam broke: a multi-element prefix like
    # [python, -u, fake_claude.py] put the prompt at index 2 and produced
    # [python, -u, <PROMPT>, fake_claude.py, -p, ...] — the interpreter then treated the
    # prompt as the script name and every one-shot read exited 2. Production (seam unset)
    # was unaffected because the prefix is 1 long, which is exactly why no test caught it.
    try:
        _p_at = args.index("-p")
    except ValueError:
        _p_at = 0
    args = args[:_p_at + 1] + [prompt if prompt else READ_PROMPT.format(path=ap)] + args[_p_at + 1:]
    r = subprocess.run(
        args,
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, stdin=subprocess.DEVNULL, env=env,
        cwd=_VISION_CWD,
        preexec_fn=(None if sys.platform == "win32" else (lambda: os.nice(10))))   # v876
    out = (r.stdout or "").strip()
    a, b = out.find("{"), out.rfind("}")
    if a < 0 or b <= a:
        err = (r.stderr or "").strip()
        # REG-1603 - the CLI prints its REASON on stdout ("Failed to authenticate: OAuth session expired and
        # could not be refreshed") and only a stdin warning on stderr, so the log said "claude exit 1" with no
        # reason for hours on his ALT. The first stdout line is the reason when stderr carries none.
        if (not err or err.startswith("Warning: no stdin data")) and out:
            err = _first_line(out) or err
        err = err[:160]
        # this read's own words (empty when it printed none) - never the previous read's, which the deep-read row
        # would otherwise carry as this failure's readErr
        globals()["_LAST_RAW"] = str(out)[:2048]
        ev("cap", f"vision returned no JSON ({model} exit {r.returncode})" + (f": {err}" if err else ""))
        journal_skip("parse-null", f"{model} exit {r.returncode}")   # v880 A2.8
        if r.returncode != 0:
            print(f"  ⚠ claude exit {r.returncode}" + (f": {err}" if err else ""))
        return None
    _sub_budget_record()
    globals()["_LAST_RAW"] = str(out)[:2048]   # v832 — THE THOUGHT (one-shot lane)
    if raw_json:
        try:
            return json.loads(out[a:b + 1])
        except Exception:
            journal_skip("parse-null", "%s raw-json unparseable" % model)
            return None
    _pr = _parse_read(out)
    if _pr is not None:
        _pr["_raw_txt"] = str(out)[:2048]
    return _pr

# v1519 — THE CHRONICLE LANE, Claude side. Konyo's PRIMARY reader: if this lane does not answer,
# there is no page (two_lane_read never pays Grok to second-guess a refusal).
#
# It is deliberately NOT READ_PROMPT with an extra field. READ_PROMPT asks "what items are on screen";
# this asks "which rows are marked FOUND", which is a different question with a different failure
# mode, and folding it into the live prompt would make every farming read carry chronicle instructions
# it can never use.
# ── v1785 — THE VAULT READER SEAM, WHICH HAD NEVER BEEN BUILT ────────────────────────────────────
# vault_retro.sweep() reads resp["items"] and the vault sweep was wired to claude_chronicle_read,
# whose answer has keys found/notFound/sets and no `items` at all. `note` is None on a GOOD chronicle
# read, so it was not even treated as a refusal: the page counted as read, the reel was marked swept,
# and no row could ever be produced. `grep -rn "def claude_vault"` returned nothing — the seam was
# missing, not broken. Found by an adversarial review of this lane.
#
# The contract is vault_retro's, not this file's: normalize_item() takes {name, lane, kind, count,
# conf, throwOut, throwWhy} and REFUSES a row with no name, so an invented row is impossible by
# construction. lane ∈ (stash, inventory, equipment); kind ∈ (rune, gem, material, item); both fall
# back to the surface's own default when the reader does not say, and never invent an item.
# v2002 — THE VAULT READER HAD NO VERSION AT ALL, so nothing could tell an old read from a new one.
# The chronicle side has had PROMPT_VER since v832 and uses it to REOPEN reels a weaker reader sealed
# with nothing; the vault side recorded only a timestamp, which makes its seal permanent however much
# the reader improves. That is the same "a stale verdict made permanent" defect v1830 fixed on the
# other lane, still live on this one. BUMP THIS WHENEVER VAULT_READ_PROMPT CHANGES.
VAULT_PROMPT_VER = "vp-reg3248"   # REG-3248 (#67) — the highlighted stash TAB and a shared tab's page are asked; bump whenever VAULT_READ_PROMPT changes
#: REG-3248 (#67, his call 2026-11-06 07:10 Israel: "the vault reader names the tab, and the reels are re-read with paid
#: Claude reads") - a witness recorded session, frame, point and cell but NOT which stash tab the cell was on, so on his
#: Mac 11 stash cells were claimed by two or three owned names (stash:c6r3 Blood Finger and Doom Grip inside ONE session):
#: a missing key dimension, not two owners. The sweep's surface never names one (OWNERSHIP_SURFACES has "stash", not
#: personal / shared), so only the read can. This version ADDS tab and page. A reel that FOUND items under an older
#: reader reopens once (control_app._vault_tab_owed, VAULT_TAB_ASKED_BY below) so its witnesses gain their tab; a reel that
#: found nothing keeps its seal (the older versions are in VAULT_PROMPT_ANSWERS_SAME_AS).
#: v3554 — HIS RULING (2026-10-01, "thats even better"): points are asked FROM NOW ON, no re-read of old footage. vp3554
#: only ADDED each item's point; the name, kind, count, sockets, eth, quality and throw-out are asked exactly as vp3368
#: asked them. So a vp3368 seal still stands (control_app._vault_still_sealed) and its rows still count as this prompt's
#: (the sockets/eth/quality doctor row). A prompt that changes the QUESTION lists nothing here. [[stale-reading]]
#: REG-2915 (#158.7) - vp-reg2915 only ADDED the tooltip box ("tip"): every other key is asked exactly as vp3554 asked it, and
#: vp3554 asked the same as vp3368. Its seals stand; the box (and its crop) comes from reads made from now on. [[stale-reading]]
VAULT_PROMPT_ANSWERS_SAME_AS = ("vp3554", "vp3368", "vp-reg2915")
#: REG-3248 (#67) - vp-reg3248 asks everything vp-reg2915 asked, plus the tab. So for a reel that FOUND NOTHING the old
#: answer still answers (the tab cannot turn "nothing was here" into items) and that seal stands - the list above. A
#: reel that FOUND items under a reader that never asked the tab is what his call re-reads: control_app._vault_tab_owed
#: reopens it ONCE, and its new seal (a version in VAULT_TAB_ASKED_BY) stands for good. MEASURED 11-06: 99 seals, 66 took
#: nothing; 17 reels hold stash witnesses of his owned items, 8 of them still on disk - a full re-read would have spent
#: its reads on the barren 66 and gained no tab for anything.
VAULT_TAB_ASKED_BY = ("vp-reg3248",)

VAULT_READ_PROMPT = (
    # ── v2016 — THE VAULT READER WAS NEVER TOLD ABOUT THE HOVER TOOLTIP ──────────────────────
    # This file already states the fact, at line ~305, as a calibrated truth from his real videos:
    #     "panel grids show item ICONS with no text — names ONLY come from hover tooltips
    #      (first line = name), ground labels, waypoint labels…"
    # READ_PROMPT (the chronicle lane) acts on it in four places — "names = READABLE text labels
    # only (tooltips first line, …)", the sockets rule, names_loc. VAULT_READ_PROMPT mentioned
    # tooltip or hover ZERO times and described only "a grid of item icons… with a name label".
    #
    # So on a frame where he HOVERS an item, the reader was asked about the grid, correctly answered
    # items:[] because a grid prints no names, and the fully legible tooltip beside it was never
    # requested. MEASURED by opening one of his own frames: f_1784984209709 carries a complete
    # tooltip — "Annihilus / Small Charm / Keep in Inventory to Gain Bonus / Required Level: 70 /
    # +1 to All Skills…" — in a frame the sweep had already PAID to read.
    #
    # That is why vault_doctor reports 220 occupied cells and zero names, and why the advice "film
    # the tooltip" was wrong: he already did. The same asymmetry as v2002 — the chronicle lane
    # learned something and the vault lane never got it. [[the-unjoined-end]] [[copy-drift]]
    "A HOVER TOOLTIP, when one is on screen, is the MOST RELIABLE name in the frame — the grid "
    "itself prints none. Its FIRST LINE is the item name; return that item like any other, with the "
    "kind you can tell from the tooltip and conf high, because the name is written out rather than "
    "inferred from an icon. A tooltip that is cut off at the panel edge is not readable — leave it "
    "out. Never merge the tooltip's stat lines into the name.\n"
    "Image {path} = a Diablo II Resurrected (RotW mod) {surface} panel: a grid of item icons, some "
    "with a name label or a stack count.\n"
    "Reply with STRICT JSON only, no markdown, no prose:\n"
    '{{"surface":"{surface}","tab":"personal|shared|runes|gems|materials|null","page":<int or null>,"items":[],"conf":0.0}}\n'
    # REG-3248 (#67) - the TAB the panel shows, read off the tab row, so each item's cell is a cell OF A TAB
    'tab = the stash TAB that is selected (highlighted) in the row of tabs along the top of the stash panel: personal, '
    'shared, runes, gems or materials. null when no tab row is visible or you cannot tell which tab is selected. '
    'page = for a shared tab ONLY, its position among the SHARED tabs counting from the left (1 = the first shared tab); '
    'null for any other tab or when you cannot tell. Read both from the tab row alone - never from the items: a wrong '
    'tab files his items on the wrong page, a null only costs a question.\n'
    # ── v2011 — `throwWhy` WAS IN THE PROSE AND NOWHERE IN THE SHAPE ──────────────────────────
    # The exact mirror of v1903, which found `throwOut` in the schema and nowhere in the prose. The
    # instruction below says "When you set it true, also give throwWhy = a short reason in your own
    # words" — and the JSON template it must match listed four keys, none of them throwWhy. A model
    # told to reply with STRICT JSON matching a template emits the template's keys.
    #
    # vault_retro:260 then reads it with `or "the reader flagged it as junk"`, so the loss is
    # INVISIBLE: every throw-out suggestion in his review bucket carried the same generic sentence,
    # and it read like the reader's opinion rather than a default standing in for one.
    # [[the-unjoined-end]] [[unknown-stays-unknown]]
    # ⚠⚠ v3368 (#60) — SOCKETS, ETHEREAL AND QUALITY ARE THE THREE FACTS THAT DECIDE WHAT A BASE
    # ITEM IS WORTH, and until now this lane READ them and THREW THEM AWAY. They appear in this
    # prompt only as throw-out criteria ("sockets and no magical text", "white base, no sockets"),
    # so the reader used them to form a junk opinion and returned a bare name. MEASURED on his real
    # stores: 44 sighting rows, and "socket"/"ethereal"/"quality" occur ZERO times in any of them.
    # A plain Gorgon Crossbow and an ethereal 4-socket one arrive as the SAME ROW, and no price list
    # can ever separate them because the distinguishing fact was never stored.
    # His ask names this case outright: "even base item with buffs socketed items", and his own
    # vocabulary for it: "white/blue/gold/unique/green for set", plus socketed and ethereal.
    # [[heart-first]] §6 — persist what you KNEW, not a summary of it. Third instance of that shape.
    #
    # ⚠ THE KEYS GO IN THE TEMPLATE OR THEY WILL NOT COME BACK. v2011 measured exactly this on
    # `throwWhy`: it was read by the parser, absent from this template, and therefore never emitted
    # — "a model told to reply with STRICT JSON matching a template emits the template's keys".
    # ⚠ NULL IS THE HONEST DEFAULT, NOT ZERO. `"sockets":0` is a CLAIM that the item has none;
    # null means the reader could not tell. Collapsing them would invent a fact about his loot.
    'Each item = {{"name":"<exact text you can read>","kind":"rune|gem|material|item",'
    '"count":<int or null>,"sockets":<int or null>,"eth":<true|false|null>,'
    '"quality":"white|blue|gold|unique|set|null","xy":[<x>,<y>] or null,'
    '"tip":[<left>,<top>,<right>,<bottom>] or null,'
    '"throwOut":false,"throwWhy":""}}\n'
    'sockets = how many socket holes you can SEE, or null if you cannot tell. 0 means you can see '
    'it has none. eth = true only if the tooltip or label says Ethereal, false only if you can see '
    'it does not, else null. quality = the item colour: white normal, blue magic, gold rare, unique, '
    'set(green) - null if the colour is not legible. NEVER GUESS ANY OF THESE FROM THE ICON ALONE: '
    'null costs a second look, a wrong one is banked against his loot forever.\n'
    # v3554 (#146 3b) — WHERE EACH ITEM WAS SEEN. The point is the ITEM, never its tooltip: the tooltip floats wherever
    # the game puts it; the item sits in one cell of the grid or one slot of the doll, and that cell is what the
    # character window and the organizer draw. Whole pixels of THIS image, from its top-left corner.
    'xy = the [x, y] pixel position IN THIS IMAGE of the ITEM ITSELF: the centre of its icon in the grid, or on the '
    'equipment doll - NEVER the tooltip box. null when you cannot point to it: a missing point costs nothing, a wrong '
    'one files the item in the wrong cell.\n'
    # REG-2915 (#158.7) - THE TOOLTIP'S OWN BOX, so the picture that NAMED the item can be kept beside it. Frame differencing
    # cannot find it on his reels (the world animates behind the panel: change boxes cover 53-91% of the frame), and this
    # read is the one that already saw it. The box is evidence for him to look at, never a second witness.
    'tip = the [left, top, right, bottom] pixel box IN THIS IMAGE of the hover tooltip you read this item\'s name from, '
    'the whole tooltip and nothing else. null when the name did not come from a tooltip, or you cannot box it.\n'
    # v2017 — NEVER COMPLETE A PARTIAL NAME. READ_PROMPT has said this since the chronicle lane
    # existed ("Never invent from icons alone. Never complete partial names."). The vault prompt
    # covered the first half in its own words — "an icon you recognise but whose label you cannot
    # read is not a row" — and never the second. An UNREADABLE label is refused; a HALF-readable one
    # was never addressed, and completing it is the most plausible-looking fabrication there is,
    # precisely because the model is right about most of the letters.
    #
    # v2016 made this MORE likely, not less: now that a tooltip is requested, a tooltip clipped at
    # the panel edge is a partial name sitting in the most authoritative place on the frame.
    "NEVER COMPLETE A PARTIAL NAME. Half a label, a name clipped by the panel edge, or one covered "
    "by another window is NOT a name — leave the row out. Being right about most of the letters is "
    "what makes a completed name convincing, and convincing is what makes it permanent.\n"
    "NAME IS THE ONLY THING THAT MATTERS AND THE ONLY THING YOU MAY NOT GUESS. Return a row ONLY "
    "when you can actually READ its name on this image. An icon you recognise but whose label you "
    "cannot read is NOT a row — leave it out. This read runs unattended over old footage and writes "
    "into the player's owned-item ledger, so a confident wrong name is permanent and an omission is "
    "not: the next session re-reads the same shelf.\n"
    "count = the stack number printed on the icon, or null when there is none. Never infer a count "
    "from how full the grid looks.\n"
    "kind: rune = a rune (El, Eth, Ist, Ber...). gem = a gem (chipped/flawed/perfect ruby, skull...). "
    "material = a crafting/upgrade material. item = anything else (armour, weapon, charm, jewel).\n"
    "conf = your own confidence 0.0-1.0 that the names you returned are what is on the image. Be "
    "honest and low rather than generous: two sessions must agree before anything is kept, so an "
    "unsure read costs nothing and a confidently wrong one costs the shelf.\n"
    # ── v1903 — `throwOut` WAS IN THE SCHEMA AND NOWHERE IN THE PROMPT ────────────────────────
    # It appeared exactly once, inside the JSON template, printed as `false`. Nothing told the
    # reader what it meant, when to set it, or that `throwWhy` existed at all — and vault_retro
    # consumes both, gates them behind a higher confidence floor and three separate recordings,
    # and rides them out to him as suggestions. An elaborate safety mechanism fed by a field
    # nobody was ever asked to fill. [[the-unjoined-end]]
    #
    # The definition below is deliberately NARROW, and the code does not rely on it: a grail name
    # is refused by vault_retro._grail_guard() whatever the reader says. Konyo decides how wide
    # "junk" should be; this is the floor, not his policy.
    "throwOut = true ONLY for an item that is plainly worthless: a WHITE or GREY base with no "
    "sockets and no magical text. Never for a named unique or set item, never for a rune, a gem, "
    "a jewel, a charm or a crafting material, and never because you do not recognise something. "
    'When you set it true, also give throwWhy = a short reason in your own words, e.g. "white '
    'base, no sockets". Default false. THERE IS NO UN-THROW IN DIABLO: a suggestion to bin '
    "something he wanted is the one mistake here that cannot be taken back, so when in doubt "
    "leave it false. His roster is checked again afterwards and a grail name is refused whatever "
    "you say.\n"
    "If this is NOT a {surface} panel, or you cannot read any name on it, return items EMPTY. An "
    "empty answer is recoverable; a wrong one is not."
)


CHRONICLE_READ_PROMPT = (
    "Image {path} = the in-game CHRONICLE (holy grail) panel of Diablo II Resurrected (RotW mod): a "
    "long scrollable list of item names where each row shows whether the player has FOUND it — "
    "bright/coloured text vs grey/dim, a tick, or a filled marker.\n"
    "Reply with STRICT JSON only, no markdown, no prose:\n"
    '{{"ledger":"{ledger}","found":[],"notFound":[],"sets":[],"printedFound":null,'
    '"printedTotal":null,"stateVisible":true,"wrongTab":false,"notChronicle":false,'
    '"foundAt":{{}},"droppedBy":{{}},"conf":0.0}}\n'
    "found = ONLY names whose found-state is VISIBLY positive. notFound = names you can read whose "
    "state is dim, empty or ambiguous.\n"
    # v1839 — "THIS IS NOT THE CHRONICLE" AND "I CANNOT JUDGE THESE ROWS" ARE DIFFERENT FACTS.
    # A reel is a screen recording: it opens and closes on his TV DIABLO console window and on
    # ordinary gameplay. Those frames are correctly refused — but they came back stateVisible=false,
    # the SAME answer as a legible Chronicle page whose rows could not be judged, so the refusal
    # count mixed healthy refusals with lost pages and could be read as neither. Opening six of his
    # refused frames settled it: three were the console window or gameplay (right to refuse), three
    # were legible sets pages carrying First Found dates (lost). One number, two opposite meanings.
    "notChronicle = true when the picture is not a Chronicle panel at all - gameplay, a stash, a "
    "menu, or the TV DIABLO console window. That is a different answer from a Chronicle page whose "
    "rows you cannot judge, and saying which costs nothing while guessing costs a page.\n"
    "If you cannot tell found from unfound ANYWHERE on this panel, set stateVisible=false and return "
    "found EMPTY. This read runs unattended over old footage, so a confident wrong page permanently "
    "mis-tallies a grail nobody is watching. An empty answer is recoverable; a wrong one is not.\n"
    # v1827 — A `First Found:` LINE IS ITSELF THE FOUND-STATE, and not saying so was throwing away
    # readable pages. Konyo's sets reel refused 20 of 35 attempts; pulling one of the refusals and
    # LOOKING at it settled why. The frame is a perfectly legible SETS page - M'avina's Tenet
    # (Demon Imp, 05/19/2026), M'avina's Icy Clutch (The Cow King, 05/18/2026), the Trang-Oul's
    # Avatar heading, then Girth and Claws each with their own date - and the reader returned
    # stateVisible=false.
    # The rule above was written for the UNIQUES panel, where unfound rows are dim silhouettes
    # sitting next to bright found ones, so "can you tell them apart" is answerable by contrast. A
    # SETS page showing only owned rows has nothing to contrast against, and an honest reader
    # following that rule literally must refuse it. The refusal was correct behaviour from an
    # incomplete instruction.
    "A row that prints a `First Found:` date IS found - that line is the found-state by itself, and "
    "needs nothing to compare against. A page where EVERY visible row carries one is a page where "
    "every visible row is found; report them and do NOT set stateVisible=false. Only say "
    "stateVisible=false when the rows carry no found-state you can read at all - no dates, no ticks, "
    "no bright/dim distinction.\n"
    "THE LEDGER YOU WERE ASKED FOR IS {ledger}. uniques = single unique items (Harlequin Crest, "
    "Windforce, Stormshield). sets = rows grouped under SET names (Tal Rasha's Wrappings, Immortal "
    "King). If the panel is the OTHER one, set wrongTab=true and return found empty — never tally "
    "set pieces as uniques or the reverse.\n"
    # v1566 — `complete` is READ in three places and was EMITTED by none of the reader lanes.
    # intake.js:691 reads g.complete === true, chronicle_retro.py:427 reads g.get("complete") is
    # True, and bible.html's chronicleApply expands a COMPLETE set into all its pieces (v1530).
    # Neither this lane nor the Grok one ever asked for it, so prop["completeSets"] was always
    # empty and v1530 has never fired once from a sweep. A page that says a set is done is one row
    # worth five, and it was being thrown away at the only point that could have captured it.
    'sets = only when ledger=sets: [{{"set":"<set name>","pieces":["<found piece>"],"complete":true|false}}].\n'
    'set `complete` true ONLY when the panel itself marks that set finished — never inferred from '
    'the pieces you happen to see.\n'
    # v1826 — A SET HEADING IS NOT A PIECE, and the readers confused the two about a quarter of the
    # time. Measured on his own swept evidence: of 16 set groups, 4 were keyed by something that is
    # not a set — "M'avina's True Sight", "M'avina's Tenet" and "Cleglaw's Claw" are PIECES, and
    # "Cathan's" is a truncation. It wrote no bad data (a heading that matches no set expands to
    # nothing, and the apply only ever wrote real roster pieces), but a quarter of the groups being
    # junk is a reader that has not been told what a heading looks like.
    # The tell is unambiguous on his frames, so it is spelled out rather than left to judgement.
    "A SETS page groups its rows under a set-name HEADING. The heading is centred, has NO item "
    "icon, NO `Dropped By:` line and NO `First Found:` line. Every PIECE row has all three. Put the "
    "HEADING in \"set\" and the rows beneath it in \"pieces\" — never a piece name in \"set\", and "
    "never a heading in \"pieces\". If you cannot see which heading a row belongs to, leave that "
    "row out rather than inventing a group for it.\n"
    "printedFound / printedTotal = the panel's own progress numbers if it shows any (\"243/403\", "
    "\"Found 108 of 135\") EXACTLY as printed, else null. They are checked against your own count as "
    "a second witness, so an honest mismatch is worth more than a flattering match.\n"
    "Read only rows you can actually see. Do not complete a set from memory or fill a page.\n"
    # v1819 — THE DATES THAT WERE ALWAYS ON THE PAGE. Konyo: "there is an option for newest found ...
    # so they know what they registered yesterday and whats new today". Checked against his own
    # 20-Aug frames first: every row carries its own `First Found:` stamp and a `Dropped By:` line,
    # and the sort control prints "Newest to Oldest" at the top right. The sweep was reading these
    # pages and keeping only the names, so nothing downstream could distinguish a FRESH find from
    # one that had simply never been read before — the question he is actually asking.
    # v1828 — `sort` IS GONE, because it never once arrived. Asked for on every chronicle read since
    # v1819 and returned EMPTY 2358 times out of 2358 - then tested directly against a frame that
    # plainly shows "Newest to Oldest" at its top right, which came back sort="" while correctly
    # returning four found names and four dates from the same picture. The field was plumbed end to
    # end; the readers simply never fill it.
    # It is not worth another attempt at the wording either, because the thing it was for is already
    # solved better: every row now carries its own `First Found:` stamp, so the ORDER of the list is
    # derivable from the data instead of read off a control. A prompt line that has never produced a
    # value is not free - it is paid for on every page of every sweep, and it reads to the next
    # person as a capability that exists.
    "foundAt = map each FOUND name -> its exact `First Found:` stamp, copied digit for digit, e.g. "
    '{{"Razorswitch":"08/20/2026, 00:49"}}. Omit any row whose stamp is hidden behind a tooltip or '
    "cut off at the panel edge, and NEVER infer one from a row's position. A missing stamp is "
    "recoverable; an invented one is a false find-date that nothing later re-reads.\n"
    "droppedBy = map each FOUND name -> the monster on its `Dropped By:` line. Omit what you cannot "
    "read.\n"
    "⚠ THE TWO TABS PRINT THOSE LINES IN OPPOSITE ORDER — measured on his frames, not assumed. On "
    "UNIQUES a row reads: name / `First Found: ...` / `Dropped By: ...`. On SETS it reads: name / "
    "`Dropped By: ...` / `First Found: ...`. Read each line by its LABEL, never by its position "
    "under the name, or every set piece gets a monster where its date belongs.\n"
    "conf = 0.0-1.0, your honest confidence in THIS page."
)


def _crop_answer_refused(raw, ledger_lane=True):
    """v1901 — ONE COPY, in chronicle_crop. The rule and every measurement behind it live in
    `chronicle_crop.crop_answer_refused`; this name stays because both crop routes below and the
    v1829 guards call it. A second copy of a refusal rule is how the two lanes drift apart, which
    is the exact defect v1901 was fixing when it moved this. [[copy-drift]]"""
    import chronicle_crop as _cc
    return _cc.crop_answer_refused(raw, ledger_lane=ledger_lane)


#: REG-1713 - the locked intake spec (_readable_frame's _READ_MAX_PX): a reader shrinks anything larger by its own rule
_VAULT_READ_SPEC_PX = 1568


def _vault_xy_map(frame_path, read_path, crop_box=None):
    """v3554 (#146 3b) — WHERE a vault reader's points live. -> {"space", "origin", "extent", "frame"} or None

    A point (px, py) in the picture the reader SAW is the frame point origin + p * extent / space: `space` is the
    [w, h] of the file sent, `extent` the [w, h] of the frame region it shows (the whole frame, or a tally band's
    crop box), `origin` that region's top-left in the frame. None when either size cannot be read - the points are
    then UNPLACED with that reason, never placed on an assumed size. [[unknown-stays-unknown]]"""
    try:
        import equipped_ledger as _EL
        _fs = _EL.jpeg_size(frame_path)
        _ss = _EL.jpeg_size(read_path)
    except Exception:
        return None
    if not _fs or not _ss:
        return None
    # REG-1713 (the v3554 eye) - A PICTURE OVER THE READ SPEC IS ONE THE READER SHRANK BY ITS OWN RULE. _readable_frame
    # hands back the ORIGINAL when it cannot open the frame (no Pillow - the ALT is already treated that way in
    # jpeg_size), so a 2560 px frame went out and `space` recorded 2560 while the reader measured its points in a
    # shrunken copy: every point filed at the wrong scale, in a real cell, with why None. The space it saw is then
    # UNKNOWN, and the points stay unplaced with that reason. [[unknown-stays-unknown]]
    if max(int(_ss[0]), int(_ss[1])) > _VAULT_READ_SPEC_PX:
        return None
    if crop_box:
        _ox, _oy = int(crop_box[0]), int(crop_box[1])
        _ew, _eh = int(crop_box[2]) - _ox, int(crop_box[3]) - _oy
    else:
        _ox, _oy, _ew, _eh = 0, 0, int(_fs[0]), int(_fs[1])
    return {"space": [int(_ss[0]), int(_ss[1])], "origin": [_ox, _oy], "extent": [_ew, _eh],
            "frame": [int(_fs[0]), int(_fs[1])]}


def claude_vault_read(image_path, surface, timeout=None):
    """One ownership panel, read on Konyo's Claude subscription, in vault_retro's `items` shape.

    v1785 — THE SEAM THAT WAS NEVER BUILT. vault_retro.sweep() reads resp["items"]; the vault sweep
    was wired to claude_chronicle_read, which returns found/notFound/sets and no items key, so the
    sweep spent real page reads, could never ground a single row, and then marked the reels swept.

    Returns {"items": [...], "conf": float} on a read, or {"note": "..."} on a refusal — the shape
    vault_retro already understands as NOT read, so a blocked lane can never be mistaken for an
    empty shelf. That is REG-180/181's rule, applied at birth rather than retrofitted.
    """
    backed = {"why": None, "fail": None}
    _miss = None
    if _reader_choice() == "both" and _is_throttled():
        _miss = "claude throttled"
    elif _reader_choice() == "both" and _sub_budget_check("oneshot"):
        _miss = "claude over budget"
    if _miss is None and _reader_choice() != "grok" and _is_throttled():   # #151 Claude's throttle gates Claude's reads only
        return {"note": "reader throttled — not read"}
    _blocked = None if _reader_choice() == "grok" else _sub_budget_check("oneshot")   # #151 Claude's cap, Claude's reads
    if _miss is None and _blocked:
        return {"note": "not read — %s" % _blocked}

    surface = str(surface or "stash").strip().lower()
    # ── v2029 — A STASH TAB IS NOT A SURFACE, AND THE PROMPT SAYS THE WORD OUT LOUD ───────────
    # stash_screen_open answers with a TAB name (personal / shared / gems / materials / runes).
    # OWNERSHIP_SURFACES has no "personal" or "shared" — those are tabs of the stash — and this
    # prompt renders the value literally: "a Diablo II Resurrected (RotW mod) {surface} panel".
    # Asked about "a personal panel", which is not a thing, the model correctly finds nothing.
    #
    # MEASURED, same frame, one word changed:
    #     surface=personal -> 0 item(s), conf 0.0
    #     surface=stash    -> 1 item,    conf 0.9   ·  Annihilus
    #
    # vault_retro._surface_of() already filters tabs out on the sweep path, so this is defensive
    # rather than a live bug — but the failure it prevents is the exact shape this lane's doctrine
    # forbids: a lane that could not answer looking identical to an empty shelf. Normalising costs
    # nothing and removes a silent wrong answer from a plausible caller mistake. [[the-unjoined-end]]
    if surface in ("personal", "shared"):
        surface = "stash"
    # REG-2013 (the #231 eye on v3576) - a STUBBED run that hits a Claude miss returns not-read, like claude_read;
    # skipping the stub on a miss fell through to _oneshot -> _grok_backup, a LIVE Grok read from a stubbed sweep.
    if _miss and os.environ.get("TV_STUB"):
        return {"note": "not read - %s under TV_STUB (vault: a stubbed run never calls a live model)" % _miss}
    if os.environ.get("TV_STUB") and not _miss:
        # the same TDD seam the other readers have: drivable end to end at zero vision cost
        try:
            man_path = os.environ.get("TV_STUB_MANIFEST") or os.path.join(HERE, "stub_manifest.json")
            with open(man_path, encoding="utf-8") as f:
                man = json.load(f)
        except Exception:
            man = {}
        raw = man.get(os.path.basename(image_path) + "#vault") or man.get("*#vault")
        if raw is None:
            return None
        _xy_map = _vault_xy_map(image_path, image_path)    # a stub answers about the frame itself
    else:
        ap = os.path.abspath(str(image_path or ""))
        if not os.path.isfile(ap):
            return None
        # CROP TO THE PANEL, for the reason v1780 measured on the chronicle lane: his frames are
        # full-desktop grabs and the panel is a fraction of them, so the rest is noise that costs
        # time AND blinds the read. stash_eye already owns this geometry, calibrated and locked on
        # his Mac — borrowed rather than re-derived, and it returns None when no honest band exists.
        _read_path = ap
        _crop_box = None
        try:
            import stash_eye as _se
            from PIL import Image as _Im
            _im = _Im.open(ap).convert("RGB")
            _W, _H = _im.size
            # v1861 — THE INVENTORY IS THE PANEL ON THE RIGHT, and this cropped it to the left one.
            #
            # Every surface that was not a tally tab fell to the "runes" band — the LEFT stash
            # panel. For surface="stash" that is roughly right. For surface="inventory" it handed
            # the reader HIS STASH and asked it to read his inventory, so the honest answer was
            # always "this is not an inventory panel, items empty" — a lane that could never ground
            # a row, reported as an empty shelf. Measured on 6_1784984233446.jpg, the frame that is
            # exactly the stash+inventory template he asked for.
            #
            # The inventory band is not calibrated anywhere in stash_eye — the tally crops were
            # measured for the left panel only. So the honest move is NOT to invent one: read the
            # FULL FRAME for inventory. It costs more tokens and it is the only rectangle known to
            # contain the panel. [[unknown-stays-unknown]] — an uncalibrated band is not a band.
            # ── v2029 — AN ITEM'S NAME IS IN A TOOLTIP, AND A TOOLTIP IS NOT IN THE GRID ─────
            # v2028 taught the GATE that a tooltip covering the tab strip is not an absent stash.
            # The frames then reached this reader and it still returned items:[] at conf 0.9 —
            # confident there was nothing — because THIS CROP had already thrown the tooltip away.
            #
            # MEASURED on the two frames the gate had been refusing:
            #     crop band  x 8%..40%   y 20%..47%
            #     "Sullied Grand Charm of Blight"   tooltip at y ~2..12%   ENTIRELY ABOVE IT
            #     "Marshal's Amulet"                tooltip at y ~4..13%   ENTIRELY ABOVE IT
            # The model never saw them. It was asked to read a grid, and it read the grid honestly.
            #
            # THE DOMAIN DECIDES THE RULE. A tally tab (runes/gems/materials) is COUNTED from the
            # grid, and its band is genuinely calibrated on his Mac. An ITEM's identity exists only
            # in the hover tooltip, which follows the cursor and can be anywhere on screen — so no
            # band can be right for it, and the only rectangle known to contain it is the frame.
            #
            # This is v1861's own reasoning applied one surface wider: "an uncalibrated band is not
            # a band". It costs more tokens on the item lanes and buys the only thing those lanes
            # are for. [[unknown-stays-unknown]]
            _TALLY = ("runes", "gems", "materials")
            _layout = surface if surface in _TALLY else "runes"
            # REG-1875 - the band follows the route this agent filmed through (its own pin, or the Windows capture
            # half's cap_target.json): the ALT's Boosteroid film holds its panels to the edges, measured
            _route = None
            try:
                _route = (_capture_for_seal() or {}).get("route")
            except Exception:
                _route = None
            _band = (_se.crops_for_aspect(_layout, float(_W) / float(_H), route=_route)
                     if surface in _TALLY else None)
            if _band:
                _box = (int(_W * _band[0]), int(_H * _band[1]), int(_W * _band[2]), int(_H * _band[3]))
                _c = _im.crop(_box)
                if _c.width > 200 and _c.height > 200:
                    # v3554 (#146 3b) — a crop over the reader's 1568 px would be scaled BY THE READER, invisibly; scale
                    # it here, so the size of the file sent is the space its points live in
                    if max(_c.size) > 1568:
                        _c.thumbnail((1568, 1568))
                    _cp = os.path.join(tempfile.gettempdir(), "tvd_vault_crop_%d.jpg" % os.getpid())
                    _c.save(_cp, quality=94)
                    _read_path = _cp
                    _crop_box = _box
        except Exception:
            _read_path, _crop_box = ap, None
        if _read_path == ap:
            # v3554 (#146 3b) — THE ITEM LANES SENT THE RAW FRAME, up to HIST_MAX_PX (2560), and the reader scales
            # anything over 1568 px down before it looks: a point it returned would live in a space nobody recorded.
            # The frame now goes at the read spec - what the reader would have seen anyway - and its size is recorded.
            _read_path = _readable_frame(ap, os.path.join(tempfile.gettempdir(), "tvd_vault_read_%d.jpg" % os.getpid()))
        _xy_map = _vault_xy_map(ap, _read_path, _crop_box)
        raw = _oneshot(_read_path, GENIUS_MODEL,
                       timeout=float(timeout or 120),
                       prompt=VAULT_READ_PROMPT.format(path=_read_path, surface=surface),
                       raw_json=True, backed=backed, **({"claude_miss": _miss} if _miss else {}))
        # the dual route v1780 proved out: a refused CROP gets one full-frame retry, so cropping
        # can only ever add reads. v1829 — "refused" now covers a crop that ANSWERS and refuses,
        # not only one that returns nothing (see _crop_answer_refused).
        # A frame Claude could not read already spent its one backup inside the call above.
        # The full-frame retry is a second Claude attempt, and it does not ask Grok again.
        if (_miss is None and not backed.get("why")
                and _read_path != ap and _crop_answer_refused(raw, ledger_lane=False)
                and not _sub_budget_check("oneshot")):
            # same cap re-check as the chronicle route above — one budget check may not license two
            # reads now that the retry fires on a refusal rather than only on a crash.
            _fp = _readable_frame(ap, os.path.join(tempfile.gettempdir(), "tvd_vault_read_%d.jpg" % os.getpid()))
            _full = _oneshot(_fp, GENIUS_MODEL,
                             timeout=float(timeout or 120),
                             prompt=VAULT_READ_PROMPT.format(path=_fp, surface=surface),
                             raw_json=True, allow_backup=False)
            # Only if it is actually BETTER. A full frame that also refuses must never overwrite
            # the crop's answer — a retry that can lose information is not a retry.
            if not _crop_answer_refused(_full, ledger_lane=False):
                raw = _full
                _xy_map = _vault_xy_map(ap, _fp)   # v3554 — the answer kept is the frame's, so are its points

    if raw is None:
        if backed.get("fail"):
            return {"note": _not_read_note("the reader returned nothing", backed)}
        return None
    try:
        d = raw if isinstance(raw, dict) else json.loads(str(raw))
    except Exception:
        return {"note": "the reader did not return JSON — not read"}
    if not isinstance(d, dict):
        return {"note": "the reader did not return an object — not read"}
    items = d.get("items")
    if not isinstance(items, list):
        items = []
    # Pass rows through UNTOUCHED except for shape: normalize_item is vault_retro's job and it is
    # the thing that refuses a nameless row. Typing them here would put the contract in two places.
    out = [x for x in items if isinstance(x, dict)]
    try:
        conf = float(d.get("conf"))
    except Exception:
        conf = None
    answered = {"items": out, "conf": conf, "surface": surface, "xy": _xy_map}
    # REG-3248 (#67) - the tab and a shared tab's page, passed RAW: vault_retro.read_tab is their one parser
    for _tk in ("tab", "page"):
        if d.get(_tk) is not None:
            answered[_tk] = d.get(_tk)
    if d.get("eye"):
        answered["eye"] = d.get("eye")
    if d.get("backup"):
        answered["backup"] = str(d.get("backup"))[:160]
    # The reel's own stamp, when this frame lives in a sealed reel. A loose frame has no
    # reel yet. A reel that recorded nothing does not inherit the pin this process holds now.
    try:
        import capture_stamp as _cs
        _cap = _cs.beside_frame(image_path)
        if _cap:
            answered["capture"] = _cap
    except Exception:
        pass
    return answered


def claude_chronicle_read(image_path, kind, timeout=None):
    """One chronicle page, read on Konyo's Claude subscription, in the v1510 shape.

    Returns None on any refusal/failure — never an empty page, for the same reason the Grok lane
    does: a dead lane must not read as "saw nothing"."""
    # v1774 — A THROTTLED READER MUST REFUSE OUT LOUD, NOT ANSWER EMPTY.
    # _note_slot_death() flips this when 2+ workers die inside 60s and its own docstring promises to
    # "SAY SO instead of silent empties" — but only the live heartbeat cap and a status chip ever
    # read the flag. The retro sweep did not, so during a throttle it kept calling, the readers
    # degraded to scene='gameplay', conf=None, names=[], and every layer downstream treated that as
    # a real answer: classify said "not a Chronicle page", the page read counted as read-with-no-
    # names, the sweep finished "successfully" with zero findings — and since v1766 the reels were
    # then MARKED SWEPT and never looked at again. Measured directly: three sweeps in a row returned
    # 39, then 22, then 0 names as the throttle deepened, and a frame that read chronicle/uniques
    # with 6 names came back gameplay/0 minutes later.
    # A `note` is the shape chronicle_retro already understands as "not read" — it counts as refused
    # rather than as an empty page, so nothing downstream mistakes a silence for an answer.
    backed = {"why": None, "fail": None}
    _miss = None
    if _reader_choice() == "both" and _is_throttled():
        _miss = "claude throttled"
    elif _reader_choice() == "both" and _sub_budget_check("oneshot"):
        _miss = "claude over budget"
    if _miss is None and _reader_choice() != "grok" and _is_throttled():   # #151 Claude's throttle gates Claude's reads only
        return {"note": "reader throttled — not read"}
    # v1777 — a page the SUBSCRIPTION CAP refused is not a page that held nothing. This one already
    # returned None (its own contract), but saying WHICH refusal it was is the difference between
    # "your footage is empty" and "you are out of reads until the window rolls".
    _blocked = None if _reader_choice() == "grok" else _sub_budget_check("oneshot")   # #151 Claude's cap, Claude's reads
    if _miss is None and _blocked:
        return {"note": "not read — %s" % _blocked}
    # REG-2013 (the #231 eye on v3576) - a STUBBED run that hits a Claude miss returns not-read, like claude_read;
    # skipping the stub on a miss fell through to _oneshot -> _grok_backup, a LIVE Grok read from a stubbed sweep.
    if _miss and os.environ.get("TV_STUB"):
        return {"note": "not read - %s under TV_STUB (chronicle: a stubbed run never calls a live model)" % _miss}
    if os.environ.get("TV_STUB") and not _miss:
        # the TDD seam: the sweep must be drivable end-to-end with zero vision cost, exactly like
        # the live loop is (TV_STUB, v711)
        try:
            man_path = os.environ.get("TV_STUB_MANIFEST") or os.path.join(HERE, "stub_manifest.json")
            with open(man_path, encoding="utf-8") as f:
                man = json.load(f)
        except Exception:
            man = {}
        raw = man.get(os.path.basename(image_path) + "#chronicle") or man.get("*#chronicle")
        if raw is None:
            return None
        _framing = "stub"   # v1901 — a stubbed read saw no pixels at all; say so rather than lie
    else:
        ap = os.path.abspath(str(image_path or ""))
        if not os.path.isfile(ap):
            return None
        ledger = "sets" if str(kind or "").endswith("sets") else "uniques"
        # ── v1780 — READ THE LIST, NOT THE LIVING ROOM ────────────────────────────────────────
        # His frames are 2940x1912 full-desktop grabs; the Chronicle list is 26% of that. The other
        # 74% is town, his character, the life orbs and the dock — and it does not merely cost time,
        # it BLINDS the read. Measured over six frames of his thorough reel, same reader, same day:
        #
        #     full frame : 0/6 pages read, 0 names, six "no-found-state" refusals
        #     list crop  : 5/6 pages read, 17 names, one refusal
        #
        # That is the whole difference between a sweep that finds his items and one that reports
        # empty footage. chronicle_template already measured this band on his own calibration film
        # (LIST_BAND, aspect-corrected by _scale_band_for_aspect) and used it only to CLASSIFY
        # frames — never to crop what gets read. The stash lane has cropped since v947 and its own
        # notes say chrome only becomes readable "via a deliberate crop + 3x upscale".
        #
        # DUAL ROUTE, accuracy first: if the crop comes back refused we retry the FULL frame, so
        # this can only add reads, never remove one. Upscaling was measured too and did not help on
        # top of the crop, so it is not done — the win is the framing, not the pixels.
        # v1901 — ONE CROP, SHARED WITH THE GROK LANE. This block used to live here alone, which
        # is precisely why the second lane never had it: a crop nobody else can call is a crop only
        # one witness gets. The band, the aspect correction and the fallback are in chronicle_crop.
        import chronicle_crop as _cc
        _read_path, _framing = _cc.list_crop(ap)
        raw = _oneshot(_read_path, GENIUS_MODEL,
                       timeout=float(timeout or 120),
                       prompt=CHRONICLE_READ_PROMPT.format(path=_read_path, ledger=ledger),
                       raw_json=True, backed=backed, **({"claude_miss": _miss} if _miss else {}))
        # the dual route: a refused CROP gets one full-frame retry, so cropping can only add reads.
        # v1829 — "refused" now covers a crop that ANSWERS and refuses, which is what was denying
        # legible sets pages their second attempt. NOTE the correction in _crop_answer_refused: the
        # crop framing is NOT the cause — measured, the crop reads the canonical failing frame fine.
        # This buys a retry against a TRANSIENT refusal, and the source of that transience is open.
        # A backup already asked is this frame's one Grok attempt; the retry does not ask again.
        if (_miss is None and not backed.get("why")
                and _read_path != ap and _crop_answer_refused(raw) and not _sub_budget_check("oneshot")):
            # v1845 — THE RETRY MUST ASK THE CAP AGAIN. The budget is checked once, at the top of
            # this read, and before v1829 the full-frame retry fired only on a hard crash, so one
            # check covered one read in practice. v1829 made the retry fire on a REFUSAL, which is
            # common, so a single budget check now licenses two reads on every refused page. Under
            # the subscription cap that is a bounded but systematic overrun, and the cap is the one
            # guard between a long sweep and his whole allowance.
            # Skipping the retry simply leaves the crop's answer standing, which is exactly the
            # pre-v1829 behaviour — an honest refusal rather than a read he could not afford.
            _full = _oneshot(ap, GENIUS_MODEL,
                             timeout=float(timeout or 120),
                             prompt=CHRONICLE_READ_PROMPT.format(path=ap, ledger=ledger),
                             raw_json=True, allow_backup=False)
            if not _crop_answer_refused(_full):
                raw = _full
                _framing = _cc.FULL   # v1901 — the page records the pixels that ANSWERED it
    if raw is None and backed.get("fail"):
        return {"note": _not_read_note("the reader returned nothing", backed)}
    try:
        import chronicle_retro as _cr
    except Exception:
        return None
    _lane = "grok" if isinstance(raw, dict) and raw.get("eye") == "grok" else "claude"
    page = _cr.normalize_page(raw, kind, _lane, framing=_framing)
    if isinstance(page, dict) and isinstance(raw, dict):
        if raw.get("eye"):
            page["eye"] = raw.get("eye")
        if raw.get("backup"):
            page["backup"] = str(raw.get("backup"))[:160]
    return page


# ── #91 — THE CHARACTER-SELECT LIST, READ ON HIS SUBSCRIPTION (tv/char_select.py decides WHICH frames) ────────
# The local OCR cannot read the D2R font (see _film_shrink's note), but it finds the screen for free; this is the
# one paid read per visit that turns the panel crop into names, classes and levels. Same refusals as the chronicle
# read: throttled and capped say so out loud, and the stub seam drives it with zero vision cost.
CHARSEL_READ_PROMPT = (
    "Image {path} is cropped from a Diablo II: Resurrected screenshot.\n"
    "If it shows the CHARACTER SELECTION list (a stone panel with ONLINE / OFFLINE tabs, one row per character: the "
    "character NAME, under it 'LEVEL <n> <CLASS>', sometimes a title such as SLAYER, CHAMPION, PATRIARCH or "
    "MATRIARCH above the name, and a CREATE NEW button at the bottom), reply with STRICT JSON only:\n"
    '{{"screen":"character-select","tab":"online","chars":[{{"name":"","cls":"","level":0,"title":null}}],'
    '"selected":null,"partial":false}}\n'
    "Rules: the game font draws the letter O as a circle with a cross in it - write it as the letter O. Copy each "
    "NAME letter for letter as shown; never correct or complete a name. cls is one of Amazon, Assassin, Barbarian, "
    "Druid, Necromancer, Paladin, Sorceress, Warlock. A row you cannot read with certainty (covered by the mouse "
    "cursor, cut off, blurred): leave it OUT - never guess. tab is online, offline or unknown. partial is true when "
    "the list is scrolled, cut off or a row is covered. selected is the NAME of the one row drawn HIGHLIGHTED - the "
    "character the game will enter with, its row framed brighter than the others - copied exactly as that row's name; "
    "null when no row is visibly highlighted or you cannot tell which.\n"
    'If the image is NOT the character selection list, reply {{"screen":"other","chars":[]}}. JSON only, no prose.'
)


def _panel_note(note, asked=False, later=False):
    """REG-1941 - a panel-lane note says what char_select needs to spend and retry honestly. -> dict

    asked  the reader was really called and came back empty (a timeout counts) - that spends an hourly slot.
    later  the reader cannot be asked NOW (throttled, over budget, no stub to read) - nothing about the frame,
           so the frame is not passed for it."""
    return {"note": str(note), "asked": bool(asked), "later": bool(later)}


def charselect_read(image_path, timeout=None):
    """One character-select panel crop -> the reader's JSON (char_select.normalize() judges it), or a {"note"} that
    says why it was NOT read. Never an empty list for a read that did not happen."""
    backed = {"why": None, "fail": None}
    _miss = "claude throttled" if (_reader_choice() == "both" and _is_throttled()) else None
    if _miss is None and _reader_choice() != "grok" and _is_throttled():   # #151 Claude's throttle gates Claude's reads only
        return _panel_note("reader throttled - not read", later=True)
    _blocked = None if _reader_choice() == "grok" else _sub_budget_check("oneshot")
    if _blocked and _reader_choice() != "both":
        return _panel_note("not read - %s" % _blocked, later=True)
    if _blocked and _miss is None and _reader_choice() == "both":
        _miss = "claude over budget"
    # REG-2013 (the #231 eye on v3576) - a STUBBED run that hits a Claude miss returns not-read, like claude_read;
    # skipping the stub on a miss fell through to _oneshot -> _grok_backup, a LIVE Grok read from a stubbed sweep.
    if _miss and os.environ.get("TV_STUB"):
        return _panel_note("%s under TV_STUB - not read (charselect: a stubbed run never calls a live model)" % _miss, later=True)
    if os.environ.get("TV_STUB") and not _miss:
        try:
            man_path = os.environ.get("TV_STUB_MANIFEST") or os.path.join(HERE, "stub_manifest.json")
            with open(man_path, encoding="utf-8") as f:
                man = json.load(f)
        except Exception as e:
            # an unreadable stub is NOT a stub with no answer — say which, never hand back {} as if it were read
            return _panel_note("stub manifest unreadable (%s) - not read" % type(e).__name__, later=True)
        raw = man.get(os.path.basename(str(image_path or "")) + "#charselect") or man.get("*#charselect")
        return raw if raw is not None else _panel_note("stub has no #charselect answer")
    ap = os.path.abspath(str(image_path or ""))
    if not os.path.isfile(ap):
        return _panel_note("no such frame")
    raw = _oneshot(ap, GENIUS_MODEL, timeout=float(timeout or 120),
                   prompt=CHARSEL_READ_PROMPT.format(path=ap), raw_json=True,
                   backed=backed,
                   **({"claude_miss": _miss} if _miss else {}))
    return raw if raw is not None else _panel_note(_not_read_note("the reader returned nothing", backed),
                                                   asked=backed.get("asked"))


# #149 — the lobby plaque and the in-game character panel. char_select.py decides WHICH frames.
# This prompt is not the character-select prompt: a lobby sent to that one must still answer screen other.
SURFACE_READ_PROMPT = (
    "Image {path} is a Diablo II: Resurrected screenshot.\n"
    "If it shows the LOBBY / CREATE GAME screen between games (a character plaque with the character NAME, "
    "LEVEL and CLASS, beside a CREATE GAME panel), reply with STRICT JSON only:\n"
    '{{"screen":"lobby","name":"","cls":"","level":0}}\n'
    "If it shows the in-game CHARACTER panel (the C panel: the character NAME, LEVEL and CLASS on that sheet), "
    "reply:\n"
    '{{"screen":"c-panel","name":"","cls":"","level":0}}\n'
    "Rules: the game font draws the letter O as a circle with a cross in it - write it as the letter O. Copy the "
    "NAME letter for letter as shown. Never correct or complete a name. cls is one of Amazon, Assassin, Barbarian, "
    "Druid, Necromancer, Paladin, Sorceress, Warlock. A field you cannot read: null. Never guess.\n"
    'If the image is neither of those screens, reply {{"screen":"other"}}. JSON only, no prose.'
)


def surface_read(image_path, timeout=None):
    """One whole frame of the lobby or the character panel -> the reader's JSON, or a {"note"} that says why
    it was not read. char_select.surface_of judges the answer. Never a name for a read that did not happen."""
    backed = {"why": None, "fail": None}
    _miss = "claude throttled" if (_reader_choice() == "both" and _is_throttled()) else None
    if _miss is None and _reader_choice() != "grok" and _is_throttled():
        return _panel_note("reader throttled - not read", later=True)
    _blocked = None if _reader_choice() == "grok" else _sub_budget_check("oneshot")
    if _blocked and _reader_choice() != "both":
        return _panel_note("not read - %s" % _blocked, later=True)
    if _blocked and _miss is None and _reader_choice() == "both":
        _miss = "claude over budget"
    # REG-2013 (the #231 eye on v3576) - a STUBBED run that hits a Claude miss returns not-read, like claude_read;
    # skipping the stub on a miss fell through to _oneshot -> _grok_backup, a LIVE Grok read from a stubbed sweep.
    if _miss and os.environ.get("TV_STUB"):
        return _panel_note("%s under TV_STUB - not read (surface: a stubbed run never calls a live model)" % _miss, later=True)
    if os.environ.get("TV_STUB") and not _miss:
        try:
            man_path = os.environ.get("TV_STUB_MANIFEST") or os.path.join(HERE, "stub_manifest.json")
            with open(man_path, encoding="utf-8") as f:
                man = json.load(f)
        except Exception as e:
            return _panel_note("stub manifest unreadable (%s) - not read" % type(e).__name__, later=True)
        raw = man.get(os.path.basename(str(image_path or "")) + "#surface") or man.get("*#surface")
        return raw if raw is not None else _panel_note("stub has no #surface answer")
    ap = os.path.abspath(str(image_path or ""))
    if not os.path.isfile(ap):
        return _panel_note("no such frame")
    raw = _oneshot(ap, GENIUS_MODEL, timeout=float(timeout or 120),
                   prompt=SURFACE_READ_PROMPT.format(path=ap), raw_json=True,
                   backed=backed,
                   **({"claude_miss": _miss} if _miss else {}))
    return raw if raw is not None else _panel_note(_not_read_note("the reader returned nothing", backed),
                                                   asked=backed.get("asked"))


def _maybe_genius(ap, parsed, t0, mode):
    """v723 — automatic Sonnet escalate when Haiku looks weak (session-capped)."""
    if not _needs_escalate(parsed):
        if parsed is not None:
            parsed["ms"] = int((time.time() - t0) * 1000)
            parsed["mode"] = mode
            parsed["model"] = FAST_MODEL
            parsed["intent"] = _intent_for(parsed.get("scene"))
            parsed["escalated"] = False
        return parsed
    if FAST_MODEL == GENIUS_MODEL or ESCALATE_CAP <= 0 or _ESCALATE_N[0] >= ESCALATE_CAP:
        if parsed is not None:
            parsed["ms"] = int((time.time() - t0) * 1000)
            parsed["mode"] = mode
            parsed["model"] = FAST_MODEL
            parsed["intent"] = _intent_for(parsed.get("scene"))
            parsed["escalated"] = False
        return parsed
    _ESCALATE_N[0] += 1
    ev("boot", f"genius escalate → {GENIUS_MODEL} (#{_ESCALATE_N[0]}/{ESCALATE_CAP}) — accuracy pass")
    try:
        # v1188 — the Master Brain law (v948.17: "cap a single live read's in-flight time much
        # tighter" — LIVE_READ_TIMEOUT_S, default 35s) bounded the warm read AND its one-shot
        # fallback, but this THIRD call (fired on top of either of those, whenever a low-conf/
        # empty-loot read needs a second opinion) was still hardcoded at timeout=90 — inert
        # today only because FAST_MODEL==GENIUS_MODEL by default (see _maybe_genius's early-out
        # above), but the instant escalate is turned on (TV_MODEL_ESCALATE != TV_MODEL — exactly
        # the haiku→sonnet ladder these globals exist for) a single live claude_read() could
        # again hold the lane hostage for up to LIVE_READ_TIMEOUT_S + 90s ≈ 125s — WORSE than the
        # 66s stall that law was written to eliminate. Bound it by the same live-lane budget.
        better = _oneshot(ap, GENIUS_MODEL, timeout=LIVE_READ_TIMEOUT_S, allow_backup=False)
    except subprocess.TimeoutExpired:
        better = None
        ev("cap", f"genius {GENIUS_MODEL} timed out — keeping {FAST_MODEL} result")
    except Exception as e:
        better = None
        ev("cap", f"genius fail: {e}")
    if better is not None and _read_score(better) >= _read_score(parsed):
        better["ms"] = int((time.time() - t0) * 1000)
        better["mode"] = "genius"
        better["model"] = GENIUS_MODEL
        better["intent"] = _intent_for(better.get("scene"))
        better["escalated"] = True
        return better
    if parsed is not None:
        parsed["ms"] = int((time.time() - t0) * 1000)
        parsed["mode"] = mode
        parsed["model"] = FAST_MODEL
        parsed["intent"] = _intent_for(parsed.get("scene"))
        parsed["escalated"] = False
    return parsed

def claude_read(path, worker=None, out_jpg=None):
    """One vision read on YOUR Claude subscription. Fast model first; genius escalate if needed."""
    # v1774 — see claude_chronicle_read: a throttled classify that answers "gameplay" is how a
    # whole reel gets skipped and then marked swept. None here means "no answer", which the sweep's
    # classifier() already treats as unknown rather than as a verdict.
    backed = {"why": None, "fail": None}
    _miss = "claude throttled" if (_reader_choice() == "both" and _is_throttled()) else None
    if _miss is None and _reader_choice() != "grok" and _is_throttled():   # #151 Claude's throttle gates Claude's reads only
        return None
    if _miss and os.environ.get("TV_STUB"):
        return None
    # v1777 — AND THE SAME DEFECT THROUGH THE OTHER DOOR: THE SUBSCRIPTION CAP.
    # _sub_budget_check is a circuit breaker protecting his account, and it works. What did not work
    # is the SHAPE of the refusal: _oneshot returns None when the cap is hit, and the parse below
    # then produced {"scene": "gameplay", "names": [], "conf": None} — a confident-looking verdict
    # that classify reads as "not a Chronicle page". Measured tonight: the cap sat at 250/250, every
    # read returned that dict in 0.0s, and a sweep "ran" for fifty minutes reading nothing while
    # reporting success. v1774 closed this for the throttle and left the budget door open, which is
    # the door we actually walked through.
    # v1778 — moved BELOW the G5 lane; see the guard just before the Claude worker call.
    # v711 — TV_STUB: the TDD seam. TV_STUB=1 returns canned reads from tv/stub_manifest.json
    # (keyed by frame basename, '*' fallback) — the FULL agent loop runs end-to-end with zero
    # vision cost, in tests and in CI. Never set in real play.
    if os.environ.get("TV_STUB"):
        try:
            man_path = os.environ.get("TV_STUB_MANIFEST") or os.path.join(HERE, "stub_manifest.json")
            with open(man_path, encoding="utf-8") as f: man = json.load(f)
        except Exception:
            man = {}
        base = os.path.basename(path)
        rd = man.get(base) or man.get("*") or {}
        scene = rd.get("scene", "gameplay")
        globals()["_LAST_RAW"] = "«stub read — no model call»"
        return {"area": rd.get("area", ""), "scene": scene,
                "names": rd.get("names", []), "tz": rd.get("tz", []),
                "conf": rd.get("conf", 1.0), "intent": _intent_for(scene),
                "stashTab": _norm_stash_tab(rd.get("stashTab") or rd.get("stash_tab"), scene),
                "chronicleTab": _norm_chron_tab(rd.get("chronicleTab") or rd.get("chronicle_tab"), scene),
                "model": "stub", "mode": "stub", "escalated": False, "ms": 0}
    ap = _readable_frame(os.path.abspath(path), out_jpg)
    EMPTY = {"area": "", "scene": "gameplay", "names": [], "tz": [], "conf": None,
             "intent": "context", "stashTab": "",
             "model": FAST_MODEL, "mode": "empty", "escalated": False, "ms": 0}
    if not os.path.isfile(ap):
        print(f"  ⚠ image missing: {ap}")
        return None if _miss else EMPTY

    # ══ GROK EYES (G5) — REMOVABLE ════════════════════════════════════════════
    # 2026-10-03 — CLAUDE READS EVERY FRAME. Grok is not started beside it. On BOTH, Grok reads only
    # a frame Claude could not, and that one call happens inside _oneshot after Claude has returned.
    # Nothing here waits on a Grok process. OFF or a missing module changes nothing on this path.
    try:
        import g5_grok_eyes as _G5
    except Exception:
        _G5 = None
    # ══ END GROK EYES (G5) ════════════════════════════════════════════════════
    # #151 HIS SWITCH AT GROK ONLY: the frame is read by the Grok CLI and nobody else - no warm Claude reader, no Claude
    # one-shot, no genius escalation. A Grok read that did not happen is the failed-read row (mode "empty", its reason
    # in readErr) - REG-1603's shape, so nothing downstream mistakes it for a look that saw nothing.
    if _reader_choice() == "grok":
        _gp = _grok_oneshot(ap, timeout=LIVE_READ_TIMEOUT_S)
        if _gp is None:
            return dict(EMPTY, model="grok-subscription-cli", readFailed=True,
                        readErr=str(_GROK_ONLY_LAST.get("why") or "the Grok read did not happen")[:200])
        return _with_xy_space(_gp, ap)

    t0 = time.time()
    # v1778 — THE CLAUDE CAP GATES THE CLAUDE PATH, AND ONLY IT. v1777 put this check at the top of
    # the function, above the G5 block — and Grok runs on its OWN quota
    # (g5_subscription_budget.json), so a full CLAUDE budget silently disabled the GROK primary eye.
    # A per-lane circuit breaker that takes down the other lane is worse than no breaker: it removes
    # the independent witness precisely when the main lane is struggling. Caught by code review.
    #
    # None (not EMPTY) is still the answer, because classifier() treats None as "no answer" while a
    # dict is the verdict "not a Chronicle page" — that shape is REG-181 itself. And the cap is
    # ANNOUNCED here, because returning early used to skip _oneshot_inner's ev()/journal_skip and
    # made the classify door quieter after the fix than before it.
    _blocked = _sub_budget_check("oneshot")
    if _blocked and _reader_choice() == "both":
        _miss = _miss or "claude over budget"
    elif _blocked:
        try:
            ev("cap", _blocked)
            journal_skip("sub-budget", _blocked)
        except Exception:
            pass
        return None
    _lane_probe = False
    if not _miss and _reader_choice() == "both":
        _lane = _claude_lane_skip_why()
        if _lane is _CLAUDE_PROBE:
            _lane_probe = True
        elif _lane:
            _miss = _lane
    if _miss:
        got = _oneshot(ap, FAST_MODEL, timeout=LIVE_READ_TIMEOUT_S, claude_miss=_miss, backed=backed)
        if isinstance(got, dict):
            return _with_xy_space(got, ap)
        return _unread_frame(EMPTY, _miss, backed)
    w = worker or _WORKER
    out_w = w.ask(READ_PROMPT.format(path=ap), timeout=LIVE_READ_TIMEOUT_S)
    if out_w is not None:
        globals()["_LAST_RAW"] = str(out_w)[:2048]   # v832 — THE THOUGHT, verbatim (single-reader compat)
        _raw_local = str(out_w)[:2048]
        parsed = _parse_read(out_w)
        if parsed is not None:
            parsed["_raw_txt"] = _raw_local   # v864 — raw travels WITH the result, no global race
        if parsed is not None:
            if _reader_choice() == "both":
                _claude_lane_observe(True)
            out = _maybe_genius(ap, parsed, t0, "warm") or EMPTY
            if out.get("mode") != "empty":
                out["eye"] = "claude"
            return _with_xy_space(out, ap)
        ev("cap", "worker returned non-JSON — falling back to one-shot")
    else:
        ev("skip", "vision worker died (timeout/stream end) — one-shot for this read, re-warming behind it")
        _note_slot_death()   # v891 (Grok C1) — cascade detector
        _rewarm(w)  # v718 (Grok R10 pick #2) + v863: rewarm THIS reader's slot only, pool degrades soft
    try:
        # v948.17 — same lane-block cap applies to the one-shot fallback: a wedged warm
        # worker must not be followed by ANOTHER unbounded (90s) attempt on the live lane.
        parsed = _oneshot(ap, FAST_MODEL, timeout=LIVE_READ_TIMEOUT_S, backed=backed, lane_probe=_lane_probe)
        if parsed is None:
            if _reader_choice() == "both":
                return _unread_frame(EMPTY, "claude no answer", backed)
            return EMPTY
        out = _maybe_genius(ap, parsed, t0, "oneshot") or EMPTY
        if isinstance(out, dict) and out.get("mode") != "empty":
            out.setdefault("eye", "claude")
        return _with_xy_space(out, ap)
    except subprocess.TimeoutExpired:
        ev("cap", f"vision timed out ({LIVE_READ_TIMEOUT_S:.0f}s) — if this repeats, run: python3 tv/tv_diablo.py --test <img>")
        print(f"  ⚠ vision timed out ({LIVE_READ_TIMEOUT_S:.0f}s)")
        if _reader_choice() == "both":
            return _unread_frame(EMPTY, "claude timed out", backed)
        return EMPTY
    except Exception as e:
        ev("cap", f"read failed: {e}")
        print(f"  ⚠ read failed: {e}")
        if _reader_choice() == "both":
            return _unread_frame(EMPTY, "claude no answer", backed)
        return EMPTY


# ── v926 SECOND LOOK — the reader's second-layer accuracy pass ──────────────────────────────
_VERIFY_Q = deque(maxlen=32)   # jobs: {"fid","names","n","sid","scene","cap_ms"}


def verify_read(path, prior_names, worker=None, timeout=75):
    """Re-read the SAME archived screenshot to correct a prior read. Returns
    {confirm, missed, not_present, conf} or None. Honours TV_STUB (keyed '<base>#verify')."""
    if os.environ.get("TV_STUB"):
        try:
            man_path = os.environ.get("TV_STUB_MANIFEST") or os.path.join(HERE, "stub_manifest.json")
            with open(man_path, encoding="utf-8") as f:
                man = json.load(f)
        except Exception:
            man = {}
        rd = man.get(os.path.basename(path) + "#verify") or man.get("*#verify") or {}
        return {"confirm": rd.get("confirm", list(prior_names)),
                "missed": rd.get("missed", []), "not_present": rd.get("not_present", []),
                "conf": rd.get("conf", 1.0)}
    ap = _readable_frame(os.path.abspath(path))
    if not os.path.isfile(ap):
        return None
    if _reader_choice() == "grok":   # #151 Grok only: the re-read goes to Grok too, never to a warm Claude reader
        _gj = _grok_oneshot(ap, timeout=timeout, raw_json=True,
                            prompt=VERIFY_PROMPT.format(path=ap, prior=json.dumps(list(prior_names))))
        out = json.dumps(_gj, ensure_ascii=False) if isinstance(_gj, dict) else None
    else:
        w = worker or _WORKER
        try:
            out = w.ask(VERIFY_PROMPT.format(path=ap, prior=json.dumps(list(prior_names))), timeout=timeout)
        except Exception:
            return None
    if out is None:
        return None
    try:
        txt = str(out)
        i, j = txt.find("{"), txt.rfind("}")
        d = json.loads(txt[i:j + 1]) if i >= 0 and j > i else None
    except Exception:
        d = None
    if not isinstance(d, dict):
        return None
    return {"confirm": [x for x in (d.get("confirm") or []) if _itemish(x)],
            "missed": [x for x in (d.get("missed") or []) if _itemish(x)][:5],
            "not_present": [x for x in (d.get("not_present") or []) if _itemish(x)],
            "conf": float(d.get("conf") or 0.0)}


def _verify_apply(job, worker=None, timeout=75):
    """v926 — run one verify job: re-read the frame, compute the delta, journal a `lane=verify`
    beat on a distinct sub-frame id (so the funnel's exactly-once holds), and route the
    correction through the SAME lifecycle pipes. REMOVE (misread) is the default correction;
    ADD (missed) is conservative — only high-confidence, clearly-readable names."""
    fid = str(job.get("fid") or "")
    prior = [x for x in (job.get("names") or []) if _itemish(x)]
    if not fid or not prior:
        return None
    src = os.path.join(HIST_DIR, fid + ".jpg")
    if not os.path.isfile(src):
        return None
    v = verify_read(src, prior, worker=worker, timeout=timeout)
    if not v:
        return None
    conf = v.get("conf") or 0.0
    # v926-R4 (Grok) — REMOVE-ONLY second look: only UN-tally a name that (a) the verify rejects,
    # (b) was in the original read, AND (c) was actually VAULTED by that read. ADD is deferred to
    # a future pass-3 — force-vaulting a "missed" hallucination is a permanent false +1 footgun.
    _vaulted = {str(x).lower() for x in (job.get("vaulted") or [])}
    _priorset = {str(x).lower() for x in prior}
    remove = [x for x in v.get("not_present", [])
              if conf >= 0.7 and str(x).lower() in _priorset and str(x).lower() in _vaulted]
    missed = [x for x in v.get("missed", [])]   # surfaced for the debugger; NOT applied at pass-2
    add = []   # ADD off until pass-3 (scene gate + readable-text proof) owns it
    # v926 — the board ingests reads by ts > SEEN, so a verify beat MUST carry ts=now (else the
    # board skips it as already-seen). captureTs stays the ORIGINAL frame clock so the SIM keeps
    # the second look pinned to the exact frame it re-checked.
    cap_ms = int(job.get("cap_ms") or time.time() * 1000)
    now_ms = int(time.time() * 1000)
    if not remove:
        # a clean confirm (or a low-conf/unvaulted rejection we won't act on) — journal the
        # second look anyway so the debugger shows the read was verified. `missed` is surfaced
        # for the human/pass-3, never tallied here.
        _journal({"ts": now_ms, "captureTs": cap_ms, "completedTs": now_ms, "n": job.get("n"),
                  "scene": job.get("scene") or "loot", "names": [], "sessionId": job.get("sid") or SESSION_ID,
                  "frameId": fid + "#v", "lane": "verify", "mode": "verify",
                  "verify": {"confirm": v.get("confirm", []), "missed": missed, "not_present": [], "conf": conf},
                  "vault_names": [], "unvault_names": [],
                  "note": ("✓ second look — read confirmed" if not missed else "✓ second look — %d maybe-missed (flagged)" % len(missed))})
        return {"delta": 0, "add": [], "remove": [], "missed": missed}
    # REMOVE routes through the SAME board pipe: a lane=verify beat with unvault_names decrements
    # the funnel/vault exactly like a real correction (distinct #v frameId → exactly-once holds).
    _journal({"ts": now_ms, "captureTs": cap_ms, "completedTs": now_ms, "n": job.get("n"),
              "scene": job.get("scene") or "loot",
              "names": [], "sessionId": job.get("sid") or SESSION_ID,
              "frameId": fid + "#v", "lane": "verify", "mode": "verify",
              "verify": {"confirm": v.get("confirm", []), "missed": missed, "not_present": remove, "conf": conf},
              "vault_names": [], "unvault_names": remove,
              "note": "🔎 second look — corrected −%d (conf %.2f)" % (len(remove), conf)})
    ev("cap", "second look @%s — −%d misread (conf %.2f)" % (fid, len(remove), conf))
    return {"delta": len(remove), "add": [], "remove": remove, "missed": missed}


def _verify_drain(worker=None, budget=1, timeout=75, deadline=None):
    """Drain up to `budget` verify jobs. Called from the main loop's idle gap (default: one
    job, no deadline) AND — v1179 CLOSER — from `_pool_shutdown` with a `deadline` so a job
    queued for the last read(s) before session close still gets its second-look correction
    instead of vanishing with the queue when the process exits.

    v1200 — `deadline` is a time.monotonic() value (the caller, `_pool_shutdown`, computes it
    that way) specifically so a backward wall-clock jump mid-shutdown can't turn 'spend the
    leftover shutdown budget' into 'wait out however long the clock jumped'."""
    if not VERIFY_ON:
        return
    n = 0
    while _VERIFY_Q and n < budget:
        if deadline is not None and time.monotonic() >= deadline:
            break   # out of shutdown budget — leave the rest un-drained rather than overrun
        try:
            _verify_apply(_VERIFY_Q.popleft(), worker=worker, timeout=timeout)
        except Exception as e:
            try: ev("skip", "verify failed: %s" % e)
            except Exception: pass
        n += 1


def _ocr_worker_wanted():
    """REG-2380 - the OCR worker THIS platform runs when it has one. -> str (repo-relative, never a home path)"""
    if os.environ.get("TV_OCR_ARGV") or os.environ.get("TV_OCR_BIN"):
        return "the TV_OCR_ARGV / TV_OCR_BIN worker"
    return "tv/ocr_win.ps1" if sys.platform.startswith("win") else "tv/bin/ocr_mac"


def _ocr_lane_tag():
    """REG-2380 - THE BANNER NAMES THE OCR WORKER THAT RUNS, NOT THE MAC'S BINARY. -> str

    The banner printed `"ON " + OCR_BIN` whenever the lane was available, and OCR_BIN is always tv/bin/ocr_mac. On
    Windows _ocr_worker_cmd() runs ocr_win.ps1 instead, so every Windows agent announced a Mach-O path that can never run
    there. MEASURED on a copy of Dean's control_agent.log (2026-10-21): 139 agent boots, v2246 to v3767, every one
    "ocr lane: ON ...\\tv\\bin\\ocr_mac", beside a lane reading at 34-50 ms through the PowerShell worker. The tag is
    built from the argv _ocr_worker_cmd() hands the spawn - the same answer OcrWorker._spawn acts on - and an OFF
    says which switch or which missing worker turned it off. [[label-outlived-referent]]"""
    cmd = _ocr_worker_cmd() if _OCR.available() else None
    if cmd:
        return "ON " + " ".join(str(x) for x in cmd)
    if not OCR_ENABLED:
        return "OFF (TV_OCR=0)"
    return "OFF (no worker: %s is missing here)" % _ocr_worker_wanted()


def _hold_agent_lease():
    """v3850 (Elad 18:16) - ONE REEL-CUTTER. The console hands the sibling lease path in TVD_AGENT_LEASE; a second
    agent that finds a live, fresh holder leaves here, before it binds the bridge or reads a frame. No path = an agent
    started by hand or by a law: no lease, the old behaviour."""
    import recorder_lease as _rl
    path = os.environ.get(_rl.AGENT_LEASE_ENV) or ""
    if not path:
        return None
    v = _rl.agent_hold(path, on_lost=lambda: os._exit(3))
    if v == "refuse":
        print("  ✋ agent lease held by another live reel-cutter - this one leaves (one agent, never two)", flush=True)
        sys.exit(3)
    import atexit
    atexit.register(_rl.release, path, os.getpid())
    return v


def main():
    global _LIFECYCLE, _VISION_BUSY, SESSION_ID
    _hold_agent_lease()
    _establish_footage()
    # v840 — clean stuck capture temps (live night left many live.bmp.tmp.* ghosts)
    try:
        for name in os.listdir(FRAMES):
            # ⚠ v2320 — `.endswith(".part")` MISSED EVERY REAL ONE. macOS ImageIO does not
            # finalise onto the path you hand it; CGImageDestinationFinalize writes an atomic
            # sibling with a RANDOM SUFFIX, so the leftovers are named ".part-0QOX", ".part-1WK8",
            # ".part-Swgx" — and none of them end with ".part". MEASURED in his frames dir:
            # 23 orphans, 12.1 MB, every single one older than an hour, sitting beside a cleaner
            # written to remove exactly them. A sweeper whose pattern cannot match what the writer
            # produces reads as "nothing to clean". [[source-reading-guard]]
            # Safe as a substring here: this directory holds live.bmp, eye.jpg, read_*.jpg and
            # snap_*.bmp, and none of those carry ".part" in the name.
            if ".tmp." in name or ".part" in name:
                try:
                    os.remove(os.path.join(FRAMES, name))
                except Exception:
                    pass
    except Exception:
        pass
    _LIFECYCLE = LootLifecycle()
    # v768 (Grok R2) — restart continuity: if the previous run ended within the session window,
    # rehydrate the loot chain so OFF→ON / crash restarts don't orphan floor-proven items.
    try:
        prev = _load()
        prev_ts = 0
        for r in (prev.get("reads") or [])[-1:]:
            prev_ts = r.get("ts") or 0
        if prev_ts and (int(time.time() * 1000) - prev_ts) < 10 * 60 * 1000 and prev.get("lifecycle"):
            if _LIFECYCLE.restore(prev["lifecycle"], _norm_name):
                print("  ♻ lifecycle rehydrated from the last run (%d seen · %d holding)" % (
                    len(_LIFECYCLE.seen), len(_LIFECYCLE.pending)))
    except Exception:
        pass
    SESSION_ID = "s_%d_%d" % (int(time.time() * 1000), os.getpid())
    globals()["_SESSION_T0_MS"] = int(time.time() * 1000)   # v885 (Grok #2) — reel fold spans from BOOT, not first read
    _VISION_BUSY = False
    with _pool_lock:
        _in_flight.clear()
        _pool_free[:] = list(range(POOL_N))
    with _emit_lock:
        _order_buf[:] = []
    with _state_lock:
        _save({"online": True, "startedAt": int(time.time()*1000), "reads": [], "readCount": 0,
               "cap": SESSION_CAP, "seen": [], "farmed": [], "model": FAST_MODEL, "genius": GENIUS_MODEL,
               "lifecycle": _LIFECYCLE.snapshot(), "sessionId": SESSION_ID, "ver": VERSION})
    bridge()
    try:
        if sys.platform == "darwin":
            os.nice(5)   # v877 (army §2) — the whole agent yields to D2R; workers add nice(10) on top
    except Exception:
        pass
    import queue as _qmod
    globals()["_JQ"] = _qmod.Queue()
    threading.Thread(target=_journal_writer_loop, daemon=True, name="tv-journal").start()   # v879 — Grok A(a): one ordered writer
    threading.Thread(target=_state_saver_loop, daemon=True, name="tv-statesave").start()    # v879 — write-behind 1s
    start_film_thread()
    ev("boot", f"scanner online — session {SESSION_ID} · eyes {POLL_S}s · film ~{int(1/FILM_INTERVAL_S)}fps · fast={FAST_MODEL} · genius={GENIUS_MODEL} · lifecycle v2")
    _known_dead_load()
    if _KNOWN_DEAD: ev("boot", f"{len(_KNOWN_DEAD)} learned transition frame(s) loaded — they cost 0ms now")
    if not os.environ.get("TV_STUB"):
        def _warm():
            if _reader_choice() == "grok":   # #151 Grok only: the Claude readers stay cold, and say so once
                ev("boot", "GROK ONLY - the Claude readers stay cold (your switch); every frame goes to the Grok CLI")
                return
            # v870 (farm-video run 2: pool cold 60s, reads blind) — the v863 warm was
            # SEQUENTIAL: each reader's boot blocked the next (~8×8s). Now the STARTS stagger
            # 400ms (no login herd) but the boots run in parallel — full pool warm in ~boot+3s.
            t0 = time.time()
            _wt = []
            def _warm_one(_wk):
                try:
                    if _wk.ask("Reply with exactly: ok", timeout=60) is not None:
                        setattr(_wk, "warm_ok", True)
                except Exception:
                    pass
            for i, _wk in enumerate(_WORKERS):
                if i:
                    time.sleep(0.4)
                _t = threading.Thread(target=_warm_one, args=(_wk,), daemon=True)
                _t.start()
                _wt.append(_t)
            for _t in _wt:
                _t.join(timeout=75)
            ok = sum(1 for _wk in _WORKERS if getattr(_wk, "warm_ok", False))
            if ok:
                ev("boot", f"vision warm — {ok}/{POOL_N} reader(s) ready in {int(time.time()-t0)}s (first reads fast)")
            else:
                ev("skip", "warm-up didn't answer — first reads may be slow (one-shot fallback armed)")
        threading.Thread(target=_warm, daemon=True).start()
    if os.environ.get("CLAUDECODE"):
        ev("cap", "⚠ launched INSIDE a Claude session — vision calls can hang. Run me in a bare Terminal.")
        print("  ⚠ you're inside a Claude Code session — claude -p may hang nested. Use a BARE Terminal window.")
    if ROBOT_MODE:
        print(f"📺 TV DIABLO {VERSION} — ROBOT (TV_ROBOT=1) · pool={POOL_N} · film ~{_FILM_FPS}fps")
        print(f"   cadence: gap={MIN_GAP_S}s · heartbeat={HEARTBEAT_S}s · priority={PRIORITY_GAP_S}s")
    else:
        print(f"📺 TV DIABLO {VERSION} — AUTO INTAKE · Robot FROZEN · pool=1 · " + ("⚡ LIGHT reader" if LIGHT_MODE else f"film ~{_FILM_FPS}fps"))
        print(f"   product: pause on stash/loot → same AI as Tools 📸 (runes/gems/materials/vault)")
        print(f"   cadence: settle gap={MIN_GAP_S}s · no continuous heartbeat")
        print(f"   unlock robot later: TV_ROBOT=1 (frozen until playable unfreeze gate)")
    print(f"   bridge: http://127.0.0.1:{PORT}/state  ·  mode: {'watch (Windows frames)' if WATCH_MODE else 'mac screencapture'}")
    print("   capture: AUTO (pins D2R.exe only — never CrossOver Home / Battle.net)")
    print(f"   models: fast={FAST_MODEL} · genius={GENIUS_MODEL}")
    _film_on = (not LIGHT_MODE) or str(os.environ.get("TV_FILM", "0")).strip().lower() in ("1", "true", "yes", "on")
    if LIGHT_MODE:
        # ⚠⚠ v2799 — THIS LINE SAID "film OFF · OCR OFF" AND BOTH HALVES WERE HARDCODED CLAIMS,
        # ONE OF THEM FALSE. Measured 2026-09-08 while he was reporting "its not reading anything":
        #     OCR_ENABLED = os.environ.get("TV_OCR", "1") != "0"      <- ON by default, and it has
        #                                                                NOTHING to do with LIGHT
        #     ocr lane: {ocr_tag}                                     <- printed FIVE LINES BELOW,
        #                                                                measured, and says ON
        # So the banner announced OCR OFF and OCR ON in one breath, and I chased the wrong thing
        # for two minutes on the strength of the false half. A reader who trusts a log is entitled
        # to have it be true. [[label-outlived-referent]]
        # ⚠ AND `_film_on` WAS ALREADY COMPUTED ON THE LINE ABOVE AND THROWN AWAY — a real
        # measurement sitting unused beside a hardcoded claim about the same thing.
        # [[plumbing-with-no-tap]]
        _ocr_here = "ON" if (OCR_ENABLED and _OCR.available()) else (
            "OFF (TV_OCR=0)" if not OCR_ENABLED else "OFF (the reader binary is not available)")
        print(f"   ⚡ LIGHT reader — screenshot every ~{POLL_S:.1f}s · film {'ON' if _film_on else 'OFF'}"
              f" · OCR {_ocr_here} · 1 claude · plays nice with the game")
        print(f"      intake fires once per SETTLE (still for ~{PLAY_GAP_S:.1f}s) — a session spent"
              f" clicking never settles, and reads stay 0 with nothing wrong")
        print("      (heavy cinematic capture for the SIM debugger: TV_LIGHT=0)")
    else:
        print(f"   film: live ~{_FILM_FPS}fps · SIM {_FOOTAGE_FPS}fps · max {FILM_MAX_PX}px · q{FILM_JPEG_Q}")
    ocr_tag = _ocr_lane_tag()   # REG-2380 - the worker that runs (ocr_win.ps1 on Windows), never OCR_BIN by default
    print(f"   ocr lane: {ocr_tag}")
    if ROBOT_MODE:
        print("   tip: ROBOT lane — continuous reads are the truth; stash-pause intake ALSO fires (governed by the debt law)")
    else:
        print("   tip: open Runes/Gems/Materials/stash and PAUSE — intake fires once per settle")
    print("   in the bible: SESSIONS tab → ON AIR. Ctrl-C to stop.\n")
    ev("boot", "product=" + ("robot" if ROBOT_MODE else "auto-intake") + " · robot_frozen=" + ("0" if ROBOT_MODE else "1"))
    # v779 — ask for Screen Recording UP FRONT (Python-as-responsible needs its own grant;
    # Terminal's checkbox does not cover the control-app child agent). #63 follow-up: never by an
    # agent that never reads the screen (a TV_STUB agent, a TV_CAPTURE=off agent).
    _boot_screen_recording_preflight()
    ev("boot", f"autopilot {VERSION} — farewell on stop · chain vault · OCR · priority gap {PRIORITY_GAP_S}s")
    if _OCR.available():
        def _warm_ocr():
            try:
                # warm Vision frameworks so first pile isn't cold
                # v1431 — Windows: prefer eye.jpg / live.png (always real images) before BMP;
                # path spaces + BMP→OCR cold paths used to log "ocr warm failed" every boot.
                jp = os.path.join(FRAMES, "read.jpg")
                probe = jp if os.path.isfile(jp) else None
                if not probe:
                    # v2324 — the live names come from ONE list now (LIVE_FRAME_NAMES); this
                    # hand-written copy predated it and would have gone stale on the next rename.
                    for cand in [os.path.join(FRAMES, "eye.jpg")] + live_frame_all():
                        if os.path.isfile(cand):
                            probe = cand
                            break
                if probe:
                    r = _OCR.read(probe, timeout=5.0 if sys.platform.startswith("win") else 3.0)
                    if r is not None:
                        ev("boot", f"ocr warm — Vision ready ({r.get('ms', '?')}ms probe)")
                    else:
                        # soft: not a fault lamp — deep lane still works
                        ev("boot", "ocr warm soft-miss — deep lane armed (fast lane may lag first settle)")
                else:
                    ev("boot", "ocr warm skipped — no frame yet (will arm on first capture)")
            except Exception as e:
                ev("boot", f"ocr warm soft-error — continuing ({type(e).__name__})")
        threading.Thread(target=_warm_ocr, daemon=True).start()
        threading.Thread(target=_text_eye_loop, daemon=True, name="tv-text-eye").start()
        ev("boot", "👁‍🗨 text eye armed — new on-screen text triggers priority reads (TV_TEXT_EYE=0 to disable)")
    else:
        # v927.2 — say WHY the fast lane is off: the v925 LIGHT default disables it even
        # when the binary exists (chased as a phantom "never compiled" for days).
        if not OCR_ENABLED:
            ev("skip", "ocr lane off (LIGHT default) — set TV_OCR=1 to arm the fast lane")
        else:
            # REG-2380 - this said tv/bin/ocr_mac on Windows too, where the missing worker is ocr_win.ps1
            ev("skip", "ocr worker missing — Claude-only until %s is present" % _ocr_worker_wanted())

    frame = live_frame_path(for_write=True)   # v2324 — JPEG: no 46ms/12MB conversion per frame
    # v927.3 — boot with a clean slate: a stale frame from a previous session (e.g. the
    # TCC-denied wallpaper era) kept showing as the board preview while the eye was
    # dormant — repeatedly read as "capture still broken". Missing frames render as the
    # normal STANDBY/IDLE splash; stale photos lie.
    # v2324 — sweep EVERY candidate name, not just the one this build writes: a live.bmp left by
    # an older build is newer than nothing and would be served as the eye forever.
    for _stale in live_frame_all() + [os.path.join(FRAMES, "eye.jpg")]:
        try:
            if os.path.isfile(_stale) and os.path.getmtime(_stale) < time.time() - 30:
                os.remove(_stale)
        except OSError:
            pass
    # v870 — last_read_t starts NOW, not 0: the heartbeat's `and last_read_t` guard meant a
    # constant-motion session (his farm video, run 2) stayed BLIND until the first settle read.
    last_md5, stable, last_sent_md5, last_read_t, reads = None, 0, None, time.time(), 0
    peak = 0.0            # recent max motion while hunting
    priority = False      # hard motion seen since last read → short gap + 1-tick settle
    empty_streak = 0
    named_until = 0.0     # boost interest after a named hit

    def _launch_vision(snap_src, cur_snap, n_this, fid_this, interest_this, used_priority, read_ts,
                       rid_override=None):
        """v863 READER POOL — one reader ACT on ITS OWN worker + PRIVATE snap/read files. Builds
        the job (captureTs, origin, dispatch, sig) at fire time and carries it through to the
        ordered apply. Acquires a free reader id; the main loop gates on a free slot.

        v948.17 (Grok P1-4) — rid_override bypasses the pool entirely: it's how the stall-drain
        sweep gets a genuinely PARALLEL worker (`_stall_worker()`) even when every normal pool
        slot is busy. The override id is never returned to `_pool_free` (it isn't a pool member),
        so it can never leak into ordinary live dispatch."""
        global _VISION_BUSY, _STALL_BUSY
        import shutil
        if rid_override is not None:
            rid = rid_override
            _STALL_BUSY = True
        else:
            rid = _pool_acquire()
            if rid is None:
                # defensive — the main loop only fires with a free slot; hold the freeze instead
                _settle_enqueue(snap_src, cur_snap, interest_this, used_priority, origin="settle")
                return snap_src
        snap_path, read_jpg = _job_files(rid, n_this)
        try:
            try:
                if os.path.exists(snap_path):
                    os.remove(snap_path)
                os.link(snap_src, snap_path)   # v877 (army #8) — 0-byte snapshot vs a 17-60MB copy
            except Exception:
                shutil.copy2(snap_src, snap_path)
        except Exception:
            snap_path = snap_src
        _job_seq[0] += 1
        job_id = "j%d_%d" % (rid, _job_seq[0])
        _base_ctx = dict(globals().get("_DISPATCH_CTX") or {})
        _origin = _base_ctx.get("origin") or "settle"
        _disp = dict(_base_ctx)
        _disp["readerId"] = rid
        _disp["poolN"] = POOL_N
        with _pool_lock:
            _disp["poolInFlight"] = len(_in_flight) + 1
            _in_flight[job_id] = {"readerId": rid, "captureTs": int(read_ts), "sig": cur_snap,
                                  "origin": _origin, "startedAt": int(time.time() * 1000)}
        job = {"n": n_this, "fid": fid_this, "interest": interest_this,
               "priority": used_priority, "dispatch": _disp, "raw": "",
               "captureTs": int(read_ts), "readerId": rid}
        _VISION_BUSY = True
        globals()["_VISION_BUSY_AT"] = time.time()

        def _vision_job():
            nonlocal empty_streak, named_until
            global _VISION_BUSY
            try:
                # ── FAST LANE: local OCR first (same dual-lane, not a second reader) ──
                ocr_rd = ocr_fast(snap_path)
                if ocr_rd is not None:
                    oms = ocr_rd.get("ms") or ocr_rd.get("wall_ms") or 0
                    onames = [n for n in (ocr_rd.get("names") or []) if _itemish(n)]   # v852 — one predicate everywhere; garbage never flashes seen
                    ev("ocr", f"⚡ocr {oms}ms · {len(onames)} name(s)" +
                       ((" — " + ", ".join(onames[:4])) if onames else " — no item-ish text") +
                       f" (raw {ocr_rd.get('raw_n', 0)})")
                    print(f"  ⚡ ocr {oms}ms  {('· ' + ' · '.join(onames[:6])) if onames else '· no item-ish text'}")
                    if onames:
                        with _state_lock:
                            st = _load()
                            st.setdefault("seen", []); st.setdefault("farmed", [])
                            prec = {
                                "ts": read_ts, "names": onames, "n": n_this,
                                "area": "", "scene": "loot", "tz": [],
                                "ms": oms, "mode": "ocr", "lane": "ocr", "model": "ocr-mac",
                                "conf": ocr_rd.get("conf"), "intent": "seen",
                                "escalated": False, "interest": interest_this, "priority": used_priority,
                                "provisional": True,
                                "frameId": fid_this, "sessionId": SESSION_ID,
                                "vault_names": [], "farmed_names": [],
                                "pending_names": [], "thrown_names": [], "unvault_names": [],
                                "lifecycle_tags": {nm: "ocr" for nm in onames},
                                "anchor": "n/a", "gone_candidates": [], "holdMs": HOLD_MS,
                            }
                            _journal(dict(prec))   # v886 (Konyo: 'reads must be SYNCED') — a
                            # counted read that never journals can never appear in the SIM reel;
                            # the provisional flag travels so the theatre shows the fast lane honestly.
                            st["reads"].append(prec)
                            st["reads"] = st["reads"][-200:]
                            st["readCount"] = n_this
                            st["ap"] = dict(_AP)
                            st["lifecycle"] = _LIFECYCLE.snapshot()
                            for nm in onames:
                                if not _is_anchor(nm) and not _is_junk(nm):
                                    st["seen"].append({"ts": prec["ts"], "name": nm, "area": "", "scene": "loot", "src": "ocr"})
                                    del st["seen"][:-200]
                            _save(st)
                        empty_streak = 0
                        named_until = time.time() + 45
                        _AP["namedStreak"] = _AP.get("namedStreak", 0) + 1
                        _AP["lastNamed"] = ", ".join(onames[:4])

                # ── DEEP LANE: Claude (this reader's OWN worker + private read.jpg) ──
                _job_worker = _stall_worker() if rid_override is not None else _WORKERS[rid]
                # ⚠⚠ v2724 — STAMP THE OWING **BEFORE** THE CALL, NOT AFTER THE ANSWER.
                # 14 of his 40 reels resolve to zone UNKNOWN with 0 segments, and the correlation
                # is perfect: zone UNKNOWN == segments 0 == never deep-read. Their lane mix is
                # kai 169 · intake 43 · system 13 · ocr 8 · skip 6 · DEEP **0**.
                #
                # But an absent `deep` row is consistent with TWO different histories and nothing
                # written down could tell them apart:
                #     (a) this frame was never dispatched to the reader at all
                #     (b) it WAS dispatched, and the answer was thrown away
                # (b) is real and lives eleven lines below: `if _POOL_STOPPING: return` drops a
                # completed read on shutdown — correct, because applying a stale read after close
                # corrupts the session — but it leaves NO trace that a read was ever owed.
                #
                # So the owing is recorded at the moment of COMMITMENT, before the network call.
                # A read discarded by the shutdown guard, or lost to an exception, still leaves a
                # `deep-owed` row saying it was attempted. Then `deep-owed` beside `deep` separates
                # "never asked" from "asked and lost", which is the whole question this row exists
                # to answer. [[unknown-stays-unknown]] [[the-unjoined-end]]
                #
                # ⚠ A NEW LANE, NOT A FLAG ON THE DEEP ROW — because the deep row is exactly what
                # does not exist in the case being measured. And `reel_segments` filters
                # `lane == "deep"`, so this cannot be mistaken for a read: it says a read was OWED,
                # never that one happened.
                #
                # ⚠ IT CANNOT BE BACKFILLED for the existing 14, and must not be: nothing recorded
                # at the time distinguishes (a) from (b) for them, so they stay UNKNOWN. This is
                # the same rule `door` states in its own words one file over — "absent door =
                # absent key, never a guessed default".
                # ⚠ THE FRAME IS NAMED FROM `snap_path`, NOT FROM A LOCAL THAT DOES NOT EXIST.
                # My first cut used `fid_this` — which has ZERO bindings in _vision_job (verified by
                # parsing, not by eye). Wrapped in this try/except, that NameError would have been
                # swallowed and the stamp would have written NOTHING, FOREVER: the exact defect
                # fixed one hour earlier in the Doctor hookup, repeated. `snap_path` is the file the
                # reader is about to be handed, so its basename IS the frame.
                # [[feedback-suspect-the-instrument]]
                try:
                    _journal({"lane": "deep-owed",
                              # #238 — WHEN it was committed: every journal row carries its own time,
                              # and this one reached a sort with None
                              "ts": int(time.time() * 1000),
                              "frameId": os.path.basename(str(snap_path or "")),
                              "sessionId": SESSION_ID,
                              "why": "committed to the deep reader; a matching lane=deep row for "
                                     "this frame means the answer landed, and its absence means "
                                     "the read was attempted and lost"})
                except Exception:
                    pass
                rd = claude_read(snap_path, worker=_job_worker, out_jpg=read_jpg)
                job["raw"] = (rd or {}).get("_raw_txt") or globals().get("_LAST_RAW", "") or ""   # v864 — result-carried raw wins; global only as single-reader fallback
                if should_learn_dead(rd):
                    learn_dead_frame(cur_snap)
                # v863 — ORDERED APPLY: buffer this completion; emit only when no OLDER read is
                # still in flight (the floor-before-stash lock). Stragglers apply after ORDER_HOLD_MS.
                if globals().get("_POOL_STOPPING"):
                    return   # v864 — shutdown in progress: release the slot (finally), never apply late
                _order_push(int(read_ts), job, rd, ocr_rd)
                for rec in _order_drain():
                    names = (rec or {}).get("names") or []
                    if names:
                        empty_streak = 0
                        named_until = time.time() + 45
                        _AP["namedStreak"] = _AP.get("namedStreak", 0) + 1
                        _AP["lastNamed"] = ", ".join(names[:4])
                    else:
                        if not (ocr_rd and ocr_rd.get("names")):
                            empty_streak += 1
                            _AP["namedStreak"] = 0
                _AP["emptyStreak"] = empty_streak
            except Exception as e:
                try: ev("cap", "vision job failed: %s" % e)
                except Exception: pass
            finally:
                try:   # v864 (Grok c) — private job files die with the job (BMP×8×reads was disk growth)
                    for _jf in (locals().get("snap_path"), locals().get("read_jpg")):
                        if _jf and isinstance(_jf, str) and ("snap_" in os.path.basename(_jf) or "read_" in os.path.basename(_jf)) and os.path.isfile(_jf):
                            os.remove(_jf)
                except Exception:
                    pass
                with _pool_lock:
                    _in_flight.pop(job_id, None)
                    if rid_override is None and rid not in _pool_free:
                        _pool_free.append(rid); _pool_free.sort()
                    _VISION_BUSY = len(_in_flight) >= 1
                if rid_override is not None:
                    globals()["_STALL_BUSY"] = False
                    _stall_worker_release()     # #83 — the stall reader lets its ~400 MB claude go after each sweep
                _AP["mode"] = "drive"
                beat("watching", 0.0)
                try:
                    _order_drain()   # a slot freed → a held straggler may now apply
                except Exception:
                    pass

        threading.Thread(target=_vision_job, daemon=True, name="tv-vision-r%d" % rid).start()
        return snap_path

    def _fire_read(origin, snap_src, sig, interest_this, used_priority, note="",
                   motion_v=0.0, peak_v=0.0, settle_ticks=0, gap_ms=0,
                   empty_s=0, named_s=0, ap_mode="", interest_parts=None, rid_override=None,
                   cap_ts_override=None):
        """ONE AI reader arm: settle or queue drain → shared last_read_t + dual-lane.

        v1187 — captureTs join law (A0 fix, 2026-07-21, applied here too): a queue/backlog
        drain reads a snapshot that was captured EARLIER (held while readers were busy, up to
        SETTLE_QUEUE_STALE_MS), but this function used to stamp it with `time.time()` at DRAIN
        time regardless — the receipt-landing time, not the frame's capture time. Every queue
        drain caller already tracks the entry's real capture clock as `ts` (that's exactly what
        `gap_ms` below is computed from) but never carried it into the frame_id/captureTs that
        the retro debugger actually joins on. cap_ts_override lets a drain caller pass that real
        clock through; live/fresh reads (no override) keep the old now() stamp unchanged."""
        nonlocal last_read_t, last_sent_md5, reads, peak, priority
        soft_over = reads - SESSION_CAP
        if soft_over >= 0:
            time.sleep(min(30.0, 6.0 + soft_over * 0.05))
        last_read_t, last_sent_md5 = time.time(), sig
        globals()["_LAST_EMIT_SIG"] = sig
        reads += 1
        read_ts = _resolve_read_ts(cap_ts_override)
        frame_id = archive_read_frame(snap_src, reads, read_ts)
        tag = "⏭ queue" if "queue" in origin else "👁 settle"
        print(f"  {tag} — dual-lane #{reads}/{SESSION_CAP}"
              + (f" · {note}" if note else "")
              + (f" · frame={frame_id}" if frame_id else ""))
        ev("settle", f"{tag} · dual-lane read #{reads}"
           + (f" · {note}" if note else "")
           + (f" · frame {frame_id}" if frame_id else ""))
        beat("reading", 0.0)
        _AP["mode"] = "read"
        # v849 (audit-core #2 · 'no invented data') — a queued freeze was never measured for
        # motion/peak/settle: OMIT them instead of journaling 0.0000 as if measured.
        _ctx = {
            "interest": round(float(interest_this), 3),
            "interestParts": dict(interest_parts or {}),
            "priority": bool(used_priority),
            "gapMs": int(gap_ms),
            "emptyStreak": int(empty_s),
            "namedStreak": int(named_s),
            "apMode": str(ap_mode or origin),
            "queueDepth": len(_SETTLE_QUEUE),
            "frameSrc": "settle-queue" if "queue" in origin else "live",
            "origin": origin,
            "note": note or ("one AI reader — " + origin),
        }
        if "queue" not in origin:
            _ctx.update({"motion": round(float(motion_v), 4), "peak": round(float(peak_v), 4),
                         "settleTicks": int(settle_ticks)})
        else:
            _ctx["note"] = "queued freeze — motion fields n/a by nature"
        globals()["_DISPATCH_CTX"] = _ctx
        used = _launch_vision(snap_src, sig, reads, frame_id, interest_this, used_priority, read_ts,
                              rid_override=rid_override)
        if "queue" in origin:
            peak = 0.0
            priority = False
        return used

    while True:
        # v926.2 — adaptive sleep: long during active play (back off, don't stutter the game),
        # responsive when settled. _ADAPT_GAP is set from motion at the end of each iteration.
        # v1438 — Windows smooth: when a deep read is in flight, back off the sensor a bit so
        # capture + control UI get CPU (baby-bottom: no hitch mid-reading).
        _gap = float(globals().get("_ADAPT_GAP", POLL_S) or POLL_S)
        if sys.platform.startswith("win") and globals().get("_VISION_BUSY"):
            _gap = max(_gap, min(2.8, _gap * 1.4))
        time.sleep(_gap)
        # ── straggler flush + queue drain: freezes held while readers were busy ──
        try: _order_drain()
        except Exception: pass
        # v944 SECOND EYE AS SWEEPER (Konyo: "calibrate the first and second brain to catch
        # these BEFORE KAI") — the idle gap (worker free, no fresh live settle waiting) belongs
        # FIRST to the un-read text-eye backlog: freezes the newest-wins live drain skipped past.
        # The second eye reads that missed-text DURING the session, before verify re-checks and
        # before seal. Debt/pacing laws hold: never steal a live slot, one freeze at a time.
        try:
            if _vision_in_flight_n() < POOL_N and not _SETTLE_QUEUE:
                _swept = False
                _bl = _text_eye_backlog_pop()
                if _bl is not None:
                    if _in_flight_has_sig(_bl["sig"]):
                        _settle_file_del(_bl)   # this exact view is already on a reader
                    else:
                        _bused = _fire_read(
                            "text-eye-sweep-queue", _bl["path"], _bl["sig"],
                            _bl.get("interest", 0.9), True,
                            note="second eye — swept un-read text-eye backlog",
                            gap_ms=max(0, int(time.time() * 1000) - _bl.get("ts", 0)),
                            ap_mode="sweep-drain",
                            cap_ts_override=_bl.get("ts"),
                        )
                        if _bused != _bl["path"]:
                            _settle_file_del(_bl)
                    _swept = True
                # verify re-checks take the gap ONLY after the sweep backlog is clear
                if not _swept and VERIFY_ON and _VERIFY_Q:
                    _verify_drain(worker=_WORKER, budget=1)
            elif _stall_drain_ready():
                # v948.17 (Grok P1-4) — every normal slot is busy AND the oldest in-flight
                # read has been stuck past STALL_DRAIN_S: the old gate above will NEVER open
                # for this session (a hung live read is not an idle gap). Drain the backlog
                # anyway, on the dedicated PARALLEL stall worker — never on the live reader.
                _bl2 = _text_eye_backlog_pop()
                if _bl2 is not None:
                    if _in_flight_has_sig(_bl2["sig"]):
                        _settle_file_del(_bl2)   # this exact view is already on a reader
                    else:
                        _stall_ms = _live_stall_ms()
                        _bused2 = _fire_read(
                            "text-eye-sweep-stall", _bl2["path"], _bl2["sig"],
                            _bl2.get("interest", 0.9), True,
                            note=f"second eye — parallel stall-drain (live stalled {_stall_ms/1000:.0f}s)",
                            gap_ms=max(0, int(time.time() * 1000) - _bl2.get("ts", 0)),
                            ap_mode="stall-drain",
                            rid_override=_STALL_RID,
                            cap_ts_override=_bl2.get("ts"),
                        )
                        if _bused2 != _bl2["path"]:
                            _settle_file_del(_bl2)
        except Exception: pass
        _drained_any = False
        while _vision_in_flight_n() < POOL_N and _SETTLE_QUEUE:
            _q = _settle_drain_pop()
            if _q is None:
                break
            if _in_flight_has_sig(_q["sig"]):
                _settle_file_del(_q)   # this exact view is already on a reader
                continue
            used = _fire_read(
                "settle-queue", _q["path"], _q["sig"],
                _q.get("interest", 0.0), bool(_q.get("priority")),
                note="held while readers busy · drained on free",
                gap_ms=max(0, int(time.time() * 1000) - _q.get("ts", 0)),
                ap_mode="queue-drain",
                cap_ts_override=_q.get("ts"),
            )
            if used != _q["path"]:
                try: os.remove(_q["path"])
                except Exception: pass
            _drained_any = True
        if _drained_any:
            continue
        # v926.2 DORMANT-WHEN-NO-GAME (Konyo, acceptance day: "i cant open my game... it needs to
        # be smoother and more optimized"). For most of a launch the D2R window is missing. Do the
        # CHEAP Quartz window check FIRST, and while there's no game SKIP the expensive full-screen
        # capture entirely and idle longer. This stops the agent grabbing the whole screen every
        # ~2s while you're trying to launch — which burned CPU and fought the game's own render.
        if not WATCH_MODE and not os.environ.get("TV_STUB"):
            _ng = time.time()
            if _ng >= float(globals().get("_GAME_CHECK_DUE", 0.0) or 0.0):
                globals()["_GAME_CHECK_DUE"] = _ng + 1.5
                if _game_window_present():
                    globals()["_GAME_MISS_SINCE"] = 0.0
                    if globals().get("_AI_PAUSED"):
                        ev("cap", "🎯 D2R window found — AI reads live again")
                        print("  🎯 D2R window found — AI reads live again")
                    _set_game_gate(True, "")
                else:
                    # v927.4 DEBOUNCE (Konyo mid-session: "diablo ii window not open — but
                    # obviously it is"). CGWindowListCopyWindowInfo intermittently returns an
                    # incomplete list for CrossOver fullscreen, so a single bad poll used to
                    # tear the board down to the WATCHING/HOLD splash and pause reads for
                    # seconds at a time. One miss means nothing: keep the gate, the capture
                    # and the preview rolling; go dormant only after the window stays gone
                    # for a full grace window (genuine game exit still detected in ~6s).
                    _ms = float(globals().get("_GAME_MISS_SINCE", 0.0) or 0.0)
                    if not _ms:
                        globals()["_GAME_MISS_SINCE"] = _ng
                    elif (_ng - _ms) >= 6.0:
                        _msg = "D2R window missing — open Diablo II: Resurrected (in-game, not only Battle.net) for live reads"
                        if not globals().get("_AI_PAUSED"):
                            ev("cap", "⏸ " + _msg)
                            print("  ⏸ " + _msg)
                        _set_game_gate(False, _msg)
                        if _ng >= float(globals().get("_NOGAME_SKIP_DUE", 0.0) or 0.0):
                            globals()["_NOGAME_SKIP_DUE"] = _ng + 30.0
                            try: journal_skip("no-game", "D2R window not found — AI dormant (no capture)")
                            except Exception: pass
            if globals().get("_AI_PAUSED"):
                beat("hold", 0.0)
                _AP.update({"mode": "hold", "interest": 0.0, "peak": 0.0, "priority": False})
                time.sleep(3.0)   # DORMANT — no full-screen capture while there is no game
                continue
        if _stub_capture_only() and not WATCH_MODE:
            # #63 — A STUB AGENT NEVER CALLS capture_mac. It used to try the REAL grab first and use
            # these synthetic frames only when that failed, so with Screen Recording granted a TV_STUB
            # agent filmed + OCR'd his real desktop (see _stub_capture_only). TV_STUB_REAL_CAPTURE=1
            # restores the old order through the branch below.
            if not capture_stub_synth(frame):
                time.sleep(0.2)
                continue
            if not globals().get("_STUB_CAP_WARNED"):
                globals()["_STUB_CAP_WARNED"] = True
                ev("cap", "SIM synthetic frames — a TV_STUB agent never reads the real screen "
                          "(TV_STUB_REAL_CAPTURE=1 to film it)")
                print("  📺 SIM: synthetic frames — a TV_STUB agent never reads the real screen")
        elif WATCH_MODE:
            # v784 — Windows capture half reports pin status via cap_target.json
            _refresh_cap_target_from_disk()
            f = newest_watched_frame()
            if not f: continue
            frame = f
            # v879/v897 — WINDOWS FOOTAGE PARITY: archive eye.jpg on FOOTAGE_INTERVAL_S (1fps).
            # v1428 — FOOTAGE STARVE 0.4fps live proof: allow eye age ≤5s (was 3s) and always
            # stamp _FOOTAGE_WHY + use promote-safe archive helper when available.
            try:
                _weye = os.path.join(FRAMES, "eye.jpg")
                _wnow = time.time()
                _wiv = FOOTAGE_INTERVAL_S
                # #255 (v3881) - THE REEL IS FILMED FROM THE FULL FRAME, AT THE MAC'S SIZE. This archived eye.jpg - the
                # console's 800 px / q72 thumbnail (capture_win.ps1 SaveAll) - so every Windows reel held 800 px frames
                # while the Mac's hold 1440 px (FILM_MAX_PX). MEASURED on the bench (tv/reader_parity.py, 48 real
                # frames): at 800 px the inventory-title eye lost 7 of 16 frames and the runes enlarge changed on 8 of
                # 16, and the Grok CLI read the same header "crisp" at 1440 and "soft" at 800. live.bmp is the full
                # capture capture_win.ps1 promotes every second grab; _archive_footage_copy shrinks it to FILM_MAX_PX
                # exactly as the Mac's film is. The eye stays the fallback when the full frame is not fresh.
                _wfull = os.path.join(FRAMES, "live.bmp")
                _wsrc, _wwhy = _weye, "win-eye"
                if os.path.isfile(_wfull) and (_wnow - os.path.getmtime(_wfull)) < 5.0:
                    _wsrc, _wwhy = _wfull, "win-full"
                if os.path.isfile(_wsrc) and (_wnow - os.path.getmtime(_wsrc)) < 5.0 \
                        and _wnow >= globals().get("_FOOTAGE_DUE", 0.0):
                    try:
                        _archive_footage_copy(_wsrc, _wnow, why=_wwhy)
                    except Exception:
                        globals()["_FOOTAGE_DUE"] = max(globals().get("_FOOTAGE_DUE", 0.0) + _wiv, _wnow - (_wiv - 0.01)) \
                            if globals().get("_FOOTAGE_DUE") else _wnow + _wiv
                        import shutil as _shwz
                        _whd = HIST_DIR
                        _establish_footage()
                        if _disk_free_bytes(_whd) / 1e9 >= MIN_FREE_GB:
                            _FOOT_TIMES.append(_wnow)
                            globals()["_FOOTAGE_WHY"] = "win-eye-copy"
                            _shwz.copyfile(_weye, os.path.join(_whd, "f_%d.jpg" % int(_wnow * 1000)))
            except Exception:
                pass
            # prefer the stable live-frame path for settle when present (v2324 — by newest
            # candidate, so the switch to JPEG does not blind a machine still holding a .bmp)
            _live = live_frame_path()
            if os.path.isfile(_live):
                frame = _live
        elif not capture_mac(frame):
            if os.environ.get("TV_STUB"):
                # SIM: no Screen Recording on the control app's Python.app — still drive the loop
                if not capture_stub_synth(frame):
                    time.sleep(0.2)
                    continue
                if not globals().get("_STUB_CAP_WARNED"):
                    globals()["_STUB_CAP_WARNED"] = True
                    ev("cap", "SIM synthetic frames — grant Screen Recording to Python for live play")
                    print("  📺 SIM: no Screen Recording for this process — using synthetic frames + canned reads")
            elif not _may_ask_for_screen_recording():
                # #63 follow-up — capture_mac refused because this agent never reads the screen
                # (TV_CAPTURE=off, e.g. a TV_STUB console's live agent). That is not a missing grant:
                # the branch below would call CGRequestScreenCaptureAccess and open System Settings.
                if not globals().get("_CAP_OFF_SAID"):
                    globals()["_CAP_OFF_SAID"] = True
                    ev("cap", "capture is OFF - this agent never reads the screen and never asks for Screen Recording")
                    print("  📺 capture is OFF (TV_CAPTURE) - this agent never reads the screen")
                time.sleep(0.5)
                continue
            else:
                # v840 — do NOT spam the log every poll (last night: thousands of identical lines)
                now = time.time()
                last = float(globals().get("_PERM_WARN_AT") or 0)
                if now - last > 30:
                    globals()["_PERM_WARN_AT"] = now
                    if not globals().get("_PERM_WARNED"):
                        globals()["_PERM_WARNED"] = True
                        # v946.4 (Konyo: "the settings tab keeps popping up every launch though the
                        # grant is done") — capture_mac ALSO fails when D2R simply isn't in the window
                        # list (the 'waiting' state), not only on a missing grant. Only blame + OPEN
                        # the Screen Recording settings when the grant is ACTUALLY missing; a closed or
                        # unfocused D2R must never pop System Settings. screen_recording_ok() returns
                        # True instantly (no dialog) when already granted.
                        _sr_ok = True
                        try:
                            _sr_ok = screen_recording_ok()
                        except Exception:
                            _sr_ok = True
                        if not _sr_ok:
                            try: open_screen_recording_settings()
                            except Exception: pass
                            ev("cap", "⚠ Screen Recording not granted — tick Python / TV DIABLO in System Settings → Privacy → Screen Recording, then RESTART")
                        else:
                            ev("cap", "waiting for the Diablo II window — Screen Recording is granted; open & focus D2R")
                    else:
                        ev("cap", "⚠ capture still failing — is the Diablo II window open & focused?")
                    print("  ⚠ screencapture failed (grant Screen Recording to the TV DIABLO / Python app in System Settings → Privacy)")
                time.sleep(0.5)
                continue
        elif (not WATCH_MODE) and os.path.getsize(frame) < 200000:
            if os.environ.get("TV_STUB") and capture_stub_synth(frame):
                if not globals().get("_STUB_CAP_WARNED"):
                    globals()["_STUB_CAP_WARNED"] = True
                    ev("cap", "SIM synthetic frames (tiny capture) — Screen Recording likely missing")
            else:
                if not globals().get("_PERM_WARNED"):
                    globals()["_PERM_WARNED"] = True
                    ev("cap", "capture looks EMPTY — grant Screen Recording to TV DIABLO / Python (System Settings → Privacy) and relaunch")
                    print("  ⚠ capture is suspiciously tiny — screen-recording permission is probably missing")
                continue
        else:
            # v783 — film thread owns eye.jpg; only backfill if film thread is cold
            if not WATCH_MODE and (time.time() - _EYE_PREVIEW_AT) > 1.5:
                try: refresh_eye_preview(frame, min_interval=0.5)
                except Exception: pass
        try: cur = frame_sig(frame)
        except Exception: continue
        motion = sig_diff(cur, last_md5)
        # v926.2 — adaptive next-gap: back off capture during active play, stay responsive when
        # settled so a pause on loot/stash is caught quickly. Never back off while a settle is
        # pending (we want to confirm it and fire the read).
        globals()["_ADAPT_GAP"] = PLAY_GAP_S if (motion >= MOTION_PEAK and not _SETTLE_QUEUE) else POLL_S
        # v899 — NO D2R WINDOW: film may keep running, but AI reads stay OFF and the UI
        # shouts to open the game. Prevents 400-read desktop burn while working.
        _now_g = time.time()
        if _now_g >= float(globals().get("_GAME_CHECK_DUE", 0.0) or 0.0):
            globals()["_GAME_CHECK_DUE"] = _now_g + 1.2
            _gok = _game_window_present()
            if _gok:
                globals()["_GAME_MISS_SINCE"] = 0.0
                if globals().get("_AI_PAUSED"):
                    ev("cap", "🎯 D2R window found — AI reads live again")
                    print("  🎯 D2R window found — AI reads live again")
                _set_game_gate(True, "")
            else:
                # v927.4 DEBOUNCE — same grace as the dormant lane: one flaky Quartz poll
                # mid-play must not pause reads or flash the missing banner.
                _ms = float(globals().get("_GAME_MISS_SINCE", 0.0) or 0.0)
                if not _ms:
                    globals()["_GAME_MISS_SINCE"] = _now_g
                elif (_now_g - _ms) >= 6.0:
                    _msg, _skind, _sline = _no_game_words()
                    if not globals().get("_AI_PAUSED"):
                        ev("cap", "⏸ " + _msg)
                        print("  ⏸ " + _msg)
                    _set_game_gate(False, _msg)
                    # rare skip ticks so SIM shows why the night was quiet (not every poll)
                    if _now_g >= float(globals().get("_NOGAME_SKIP_DUE", 0.0) or 0.0):
                        globals()["_NOGAME_SKIP_DUE"] = _now_g + 30.0
                        try:
                            journal_skip(_skind, _sline)
                        except Exception:
                            pass
        if globals().get("_AI_PAUSED"):
            beat("hold", motion)   # not "watching" — source-shape tests lock the real watch→heartbeat path
            last_md5 = cur
            peak = 0.0
            priority = False
            stable = 0
            _AP.update({"mode": "hold", "interest": 0.0, "peak": 0.0, "priority": False})
            continue
        # loading screens between zones are static + near-black — they settle but hold nothing
        # readable. v1379 B5-lite: on ENTERING the loading phase, stamp a local transition row
        # (0 vision cost) so LIVE/native flips to ENTERING <area> instead of stuck "gameplay".
        # Continuous near-black only beats "loading" after that one stamp — no journal spam.
        if sum(cur) / max(1, len(cur)) < 14:
            entering_load = _BEAT.get("phase") != "loading"
            if entering_load:
                note = transition_note(LAST_AREA, reads)
                ev("transition", f"⏳ {note} · near-black loading (local · 0 vision)")
                print(f"  ⏳ {note}  [near-black · 0ms]")
                t_ts = int(time.time() * 1000)
                try:
                    t_fid = archive_read_frame(frame, reads + 1, t_ts)
                except Exception:
                    t_fid = ""
                try:
                    _journal({"ts": t_ts, "n": reads + 1, "scene": "transition", "names": [],
                              "area": "", "frameId": t_fid, "note": note,
                              "transition_from": LAST_AREA, "ms": 0,
                              "mode": "near-black", "lane": "known", "sessionId": SESSION_ID})
                except Exception:
                    pass
                try:
                    with _state_lock:
                        st = _load()
                        st["reads"].append({
                            "ts": t_ts, "names": [], "n": reads + 1, "area": "",
                            "scene": "transition", "tz": [], "ms": 0,
                            "mode": "near-black", "lane": "known", "model": "local",
                            "conf": 1.0, "intent": "context",
                            "transition_from": LAST_AREA, "note": note,
                            "frameId": t_fid, "sessionId": SESSION_ID,
                            "escalated": False, "interest": 0.0, "priority": False,
                            "provisional": False,
                            "vault_names": [], "farmed_names": [], "pending_names": [],
                            "thrown_names": [], "unvault_names": [], "lifecycle_tags": {},
                            "anchor": "n/a", "gone_candidates": [], "holdMs": HOLD_MS,
                        })
                        st["reads"] = st["reads"][-200:]
                        reads += 1
                        st["readCount"] = reads
                        st["ap"] = dict(_AP)
                        _save(st)
                except Exception:
                    pass
                last_read_t = time.time()
            beat("loading", motion); last_md5 = cur; peak = 0.0; stable = 0
            _AP.update({"mode": "load", "interest": 0.0, "peak": 0.0}); continue
        # L2 prediction: track motion peaks (drive → stop is the pile/panel moment)
        if motion > peak: peak = motion
        if motion >= MOTION_PEAK:
            priority = True
            if _AP.get("mode") != "hunt":
                _AP["mode"] = "hunt"
        named_recent = time.time() < named_until
        _iparts = {}
        interest = ap_interest(peak, stable, priority, empty_streak, named_recent, parts=_iparts)
        _AP.update({"interest": round(interest, 3), "peak": round(peak, 3), "priority": priority,
                    "emptyStreak": empty_streak, "gap": PRIORITY_GAP_S if priority else MIN_GAP_S})
        # ── all readers busy: queue distinct freezes only (never a duplicate concurrent read) ──
        if _vision_busy():
            beat("reading", motion)
            if motion > SETTLE:
                stable = 0
                last_md5 = cur
            else:
                stable = stable + 1
                last_md5 = cur
                _settle_enqueue(frame, cur, interest, priority, origin="settle")
            continue
        beat("watching", motion)

        # v901 — HEARTBEAT dual-lane is ROBOT-only (FROZEN by default). Auto Intake waits for settle.
        if ROBOT_MODE and (_vision_in_flight_n() < POOL_N) and (_heartbeat_in_flight_n() < _heartbeat_cap()) \
                and last_read_t and (time.time() - last_read_t) >= HEARTBEAT_S and not _SETTLE_QUEUE \
                and not _in_flight_has_sig(cur):
            _hb_gap = int((time.time() - last_read_t) * 1000)
            reads += 1
            read_ts = int(time.time() * 1000)
            frame_id = archive_read_frame(frame, reads, read_ts)
            _hb_static = sig_diff(cur, last_sent_md5) <= SETTLE if last_sent_md5 else False
            ev("heartbeat", f"💓 heartbeat · {_hb_gap/1000:.1f}s since last · dual-lane #{reads} · pool {_vision_in_flight_n()}/{POOL_N}"
               + (" · static re-sample" if _hb_static else ""))
            print(f"  💓 heartbeat read #{reads} — {_hb_gap/1000:.1f}s since last · pool {_vision_in_flight_n()}/{POOL_N}")
            beat("reading", motion)
            last_read_t = time.time()
            last_sent_md5 = cur
            last_md5 = cur   # v868 (Grok #4) — no phantom motion spike on the next poll
            globals()["_LAST_EMIT_SIG"] = cur
            globals()["_DISPATCH_CTX"] = {"origin": "heartbeat", "apMode": "heartbeat",
                                          "frameSrc": "live", "gapMs": _hb_gap,
                                          "heartbeatS": HEARTBEAT_S,
                                          "motion": round(float(motion), 4), "peak": round(float(peak), 4),
                                          "settleTicks": int(stable),
                                          "priority": bool(priority), "queueDepth": len(_SETTLE_QUEUE),
                                          "note": "ROBOT forced read every %.1fs" % HEARTBEAT_S}
            _launch_vision(frame, cur, reads, frame_id, 0.6, priority, read_ts)
            continue

        if motion > SETTLE:
            stable = 0
            last_md5 = cur
            if priority: _AP["mode"] = "hunt"
            else: _AP["mode"] = "drive"
            continue
        stable = stable + 1
        last_md5 = cur
        # settle: priority (hard motion→stop) = 1 tick; low-interest = 2 ticks
        need_ticks = 1 if (priority or interest >= 0.55) else 2
        if stable < need_ticks:
            _AP["mode"] = "settle"
            continue
        # v866 — heartbeat moved ABOVE the motion gate (see the watching block)
        if sig_diff(cur, last_sent_md5) <= SETTLE:
            # v795 — OCR-won / Claude-lost views get ONE re-fire instead of a permanent burn
            global _REFIRE_SIG
            if _REFIRE_SIG is not None and sig_diff(cur, _REFIRE_SIG) <= SETTLE:
                _REFIRE_SIG = None
                ev("cap", "🔁 re-reading — OCR saw names the deep read missed")
            else:
                if stable == need_ticks:
                    ev("skip", "settled, but same view I already read — waiting for something new")
                peak = max(0.0, peak * 0.5)
                continue
        # v746 — LEARNED dead frame: local 0ms transition, no vision spend
        if known_dead_match(cur) is not None:
            note = transition_note(LAST_AREA, reads)
            ev("transition", f"⏳ {note} · recognized instantly (learned frame)")
            print(f"  ⏳ {note}  [known frame · 0ms]")
            t_ts = int(time.time() * 1000)
            t_fid = archive_read_frame(frame, reads + 1, t_ts)
            _journal({"ts": t_ts, "n": reads + 1, "scene": "transition", "names": [], "area": "",
                      "frameId": t_fid, "note": note, "transition_from": LAST_AREA, "ms": 0,
                      "mode": "known", "lane": "known", "sessionId": SESSION_ID})
            with _state_lock:
                st = _load()
                st["reads"].append({
                    "ts": t_ts, "names": [], "n": reads + 1, "area": "", "scene": "transition",
                    "tz": [], "ms": 0, "mode": "known", "lane": "known", "model": "learned",
                    "conf": 1.0, "intent": "context", "transition_from": LAST_AREA,
                    "note": note, "frameId": t_fid, "sessionId": SESSION_ID,
                    "escalated": False, "interest": interest, "priority": False,
                    "provisional": False,
                    "vault_names": [], "farmed_names": [], "pending_names": [],
                    "thrown_names": [], "unvault_names": [], "lifecycle_tags": {},
                    "anchor": "n/a", "gone_candidates": [], "holdMs": HOLD_MS,
                })
                st["reads"] = st["reads"][-200:]
                reads += 1
                st["readCount"] = reads
                st["ap"] = dict(_AP)
                _save(st)
            beat("loading", motion)
            _AP["mode"] = "load"
            last_sent_md5 = cur
            last_read_t = time.time()   # v897 — known transitions count toward 1–2s cadence
            peak = 0.0
            priority = False
            continue
        gap = PRIORITY_GAP_S if priority else MIN_GAP_S
        if time.time() - last_read_t < gap:
            if stable == need_ticks:
                ev("skip", f"settled, but only {int(time.time()-last_read_t)}s since last read (gap {gap}s · {'PRIORITY' if priority else 'cruise'})")
                journal_skip("gap-wait", f"{int(time.time()-last_read_t)}s since last · gap {gap}s")   # v880 A2.8
            continue
        # v863 — anti double-spend: never fire a view another reader is already reading
        if _in_flight_has_sig(cur):
            if stable == need_ticks:
                ev("skip", "already reading this exact view on another reader — waiting for something new")
            continue
        # soft session throttle — eye never hard-stops
        soft_over = reads - SESSION_CAP
        if soft_over >= 0:
            if soft_over == 0:
                ev("cap", f"soft threshold {SESSION_CAP} reads — cruise throttle on (eye never stops)")
                print(f"  🌙 soft threshold ({SESSION_CAP} reads) — cruising slower, never stopping")
        _d_gap = int((time.time() - last_read_t) * 1000) if last_read_t else 0
        _d_apmode = str(_AP.get("mode", ""))
        used_priority = priority
        used_peak = peak
        used_interest = interest
        used_parts = dict(_iparts)
        peak = 0.0
        priority = False
        _fire_read(
            "settle", frame, cur, used_interest, used_priority,
            note=("PRIORITY " if used_priority else "") + f"interest {used_interest:.2f} · peak {used_peak:.2f}",
            motion_v=motion, peak_v=used_peak, settle_ticks=stable,
            gap_ms=_d_gap, empty_s=empty_streak,
            named_s=1 if named_recent else 0,
            ap_mode=_d_apmode, interest_parts=used_parts,
        )
        continue

def _itemish(name):
    """v848 — OCR garbage gate for the SEED path + short displays ('QvfST L•' reached the
    stage). Item names are wordy: mostly letters, a vowel, no glyph junk. The drawer keeps
    RAW ocr truth — this only guards what gets seeded/headlined."""
    t = str(name or "").strip()
    # v852 (Grok R17) — bare runes are REAL loot names ('Ist', 'Ber', 'Io', 'El'…)
    _RUNES = {"el","eld","tir","nef","eth","ith","tal","ral","ort","thul","amn","sol","shael",
              "dol","hel","io","lum","ko","fal","lem","pul","um","mal","ist","gul","vex","ohm",
              "lo","sur","ber","jah","cham","zod"}
    if t.lower() in _RUNES or t.lower().replace(" rune", "") in _RUNES:
        return True
    if len(t) < 4 or len(t) > 40:
        return False
    if any(c in t for c in "•*&#@$%{}[]<>|\\_=+~^"):
        return False
    letters = sum(1 for c in t if c.isalpha() or c in " '-")
    if letters / max(1, len(t)) < 0.8:
        return False
    if not any(c in "aeiouAEIOU" for c in t):
        return False
    return True


def _text_eye_worthy(name):
    """v1379 — STRICTER than _itemish. Text-eye fires a full Sonnet subscription read;
    OCR garble like 'haTrng1.. Lobby' / 'ING THe R' / \"'Ii'\" must NEVER open that valve.
    Real item names are clean letter words (optionally multi-word); bare runes pass."""
    t = str(name or "").strip().strip("'\"`").strip()
    if not t:
        return False
    lo = t.lower()
    _RUNES = {"el","eld","tir","nef","eth","ith","tal","ral","ort","thul","amn","sol","shael",
              "dol","hel","io","lum","ko","fal","lem","pul","um","mal","ist","gul","vex","ohm",
              "lo","sur","ber","jah","cham","zod"}
    if lo in _RUNES or lo.replace(" rune", "").strip() in _RUNES:
        return True
    if not _itemish(t):
        return False
    # reject digit-heavy leetspeak / dotted OCR trash
    if sum(c.isdigit() for c in t) >= 1 and sum(c.isalpha() for c in t) < 8:
        return False
    if ".." in t or ",," in t:
        return False
    # pure letter words only (no leftover punctuation)
    words = [w for w in "".join(c if c.isalpha() or c == " " or c == "-" else " " for c in t).split() if w]
    if not words:
        return False
    alpha_n = sum(len(w) for w in words)
    if alpha_n < 4:
        return False
    # Real D2 names: one solid word (≥5, e.g. Shako) OR ≥2 words with a ≥4 letter piece
    # (Arachnid Mesh / Call to Arms). OCR crumbs like "ING THe R" fail this.
    long4 = sum(1 for w in words if len(w) >= 4)
    long5 = sum(1 for w in words if len(w) >= 5)
    if not (long5 >= 1 or (len(words) >= 2 and long4 >= 2) or (len(words) == 1 and len(words[0]) >= 5)):
        return False
    # reject all-caps single short fragments that are almost never full item names
    if len(words) == 1 and len(words[0]) <= 5 and words[0].isupper():
        return False
    # reject fragments with no real word shape (too few vowels relative to length)
    vowels = sum(1 for c in t if c.lower() in "aeiou")
    if vowels < 1 or (alpha_n >= 6 and vowels / alpha_n < 0.15):
        return False
    return True


def _pre_triage(deep_names, ocr_rd):
    """v853 (Grok R17 c / A2.3) — the SILENT FILTERS get a journal: every name that hit a
    gate (itemish/junk/anchor/never-vault) is recorded with its verdict, so SIM can prove
    'the gate saved us' vs 'the gate ate a Ber'."""
    pre = []
    seen = set()
    def _gate(n, lane):
        k = (str(n), lane)
        if k in seen:
            return
        seen.add(k)
        if not _itemish(n):
            g = "not-itemish"
        elif _is_junk(n):
            g = "junk"
        elif _is_anchor(n):
            g = "anchor"
        elif _is_never_vault(n):
            g = "never-vault"
        else:
            g = "pass"
        pre.append({"name": str(n)[:48], "gate": g, "lane": lane})
    for n in (deep_names or []):
        _gate(n, "deep")
    for n in ((ocr_rd or {}).get("names") or []):
        _gate(n, "ocr")
    for d in ((ocr_rd or {}).get("dropped") or [])[:12]:
        pre.append({"name": str(d.get("line", ""))[:48], "gate": "ocr-line-filter", "lane": "ocr"})
    return pre[:40]


def _reason_for(tag, loc=""):
    """v836 (SIMULATION_SPEC) — every verdict tag gets a WHY in the owner's language.
    Tags say WHAT the pipeline did; these say WHY, for the SIM decision chain."""
    t = str(tag or "")
    if t == "equipped":
        return "worn gear (unequip tell) — never farms; chronicle tally only"
    if t.startswith("vault:stash"):
        return "seen earlier this session, then read in the stash panel — committed to the vault"
    if t.startswith("vault:"):
        return "committed to the vault (" + t.split(":", 1)[1] + ")"
    if t == "already-vaulted":
        return "this name already vaulted this session and no fresh sighting since — not counted twice"
    if t == "echo-sticky":
        return "same item still where it was this session (anchor/inventory/stash tab) — not re-counted as new"
    if t == "first-seen":
        return "first time this name was read this session"
    if t.startswith("moved:"):
        return "item location changed this session (" + t.split(":", 1)[1] + ") — re-reported"
    if t == "stash-no-chain":
        return "read in the stash but NEVER seen on floor/inventory this session — no provenance, blocked"
    if t == "skip-weak":
        return "matched the never-vault list (junk/basic) — ignored on purpose"
    if t == "seen":
        return "floor label — entered the SEEN ledger, waiting for pickup"
    if t == "ocr-pending":
        return "the fast OCR lane saw it while the deep read missed — floor-seeded, one re-read armed"
    if t == "holding" or "inventory" in t:
        return "in the inventory (" + (t or "holding") + ") — HOLDING until it reaches the stash"
    if t.startswith("throw-out") or t == "floor-again":
        return "seen on the floor AFTER being held/vaulted — treated as thrown out"
    if loc == "inventory":
        return "inventory-side tooltip — holds, never vaults from here"
    return t or "no verdict this frame"


def effective_lc_scene(scene, names):
    """v753 — run-#8 lesson: a pile read Sonnet labels 'gameplay' but NAMES items is loot-class
    for the lifecycle (else stash can never vault what was honestly seen). Display keeps the label."""
    scene = scene or "gameplay"
    return "loot" if (scene == "gameplay" and names) else scene

def _capture_ts_from_frame_id(frame_id):
    """frameId = '{n}_{captureMs}' — the exact settle freeze time of the archived photo.

    v2372 — DELEGATES to tv/frame_ref.py, which is the one resolver. This was a byte-identical
    twin of control_app's copy: two implementations of one rule, in two files, each free to drift
    from the other. It is stricter in one way and that way is correct — an id carrying no capture
    time (`1_5`) now answers None instead of 5, because a one-digit number is not a timestamp.
    Every real frameId, which is `{n}_{13-digit epoch}`, resolves exactly as before.
    [[copy-drift]]"""
    try:
        import frame_ref as _fr
        return _fr.timestamp_of(frame_id)
    except Exception:
        return None


_SKIP_AT = {}
def journal_skip(why, detail=""):
    """v880 (SIM spec A2.8) — negative events: the reel must show 'agent chose to wait' as a
    dim tick, not a 40s hole that reads as blindness. Throttled 5s per why."""
    try:
        now = time.time()
        if now - _SKIP_AT.get(why, 0.0) < 5.0:
            return
        _SKIP_AT[why] = now
        _journal({"ts": int(now * 1000), "kind": "skip", "lane": "skip", "why": str(why)[:40],
                  "note": str(detail)[:120], "sessionId": SESSION_ID, "n": 0})
    except Exception:
        pass


def emit_deep_read(rd, n, frame_id, interest=0.0, used_priority=False, ocr_rd=None, farewell=False, capture_ts=None, dispatch=None, raw=None):
    """Publish one deep-lane record (main settle + v740 farewell). Returns the record dict.

    v784 — ACCURACY: journal `ts` is the CAPTURE/settle clock (matches frameId suffix and the
    hist JPEG). `completedTs` is when Claude finished. Theatre scrubs by capture time so the
    photo and the AI row are the same moment, not 'photo at T, answer at T+8s' confusion.
    """
    global LAST_AREA
    rd = rd or {"area": "", "scene": "gameplay", "names": [], "tz": [], "conf": None, "mode": "empty"}
    if os.environ.get("TV_NO_JOURNAL"):
        rd = dict(rd)
        rd["sim"] = True   # v787 (R3 sleeper) — a replay/harness read must TELL the board it is not real loot
    if rd.get("area"): LAST_AREA = rd["area"]
    names = rd.get("names") or []
    # v863 — feed the CAPTURE clock into the lifecycle so out-of-order reader completions still
    # age holds by when the shot was TAKEN, not when the AI answered.
    _cap_ms = capture_ts or _capture_ts_from_frame_id(frame_id) or int(time.time() * 1000)
    intent = rd.get("intent") or _intent_for(rd.get("scene"))
    # v795 (Grok R5 #2) — OCR truth is not garbage: when the deep read comes back EMPTY but
    # the fast lane read real names, seed them as floor-SEEN (never vault from here) so a later
    # stash of that item still has its chain, and arm one re-read of this view.
    _ocr_seed = []
    if not names:
        _ocr_seed = [x for x in ((ocr_rd or {}).get("names") or []) if _itemish(x)][:12]   # v848 — garbage never seeds the chain
    if _ocr_seed:
        try:
            _LIFECYCLE.process("loot", _ocr_seed, rd.get("area") or "", None, now_ms=_cap_ms)
            globals()["_REFIRE_SIG"] = globals().get("_LAST_EMIT_SIG")
        except Exception:
            pass
    lc = _LIFECYCLE.process(effective_lc_scene(rd.get("scene"), names), names, rd.get("area") or "", rd.get("conf"),
                            now_ms=_cap_ms, names_loc=rd.get("names_loc") or {})
    vault_names = lc.get("vault_names") or lc.get("farmed_names") or []
    pending_names = lc.get("pending_names") or []
    thrown_names = lc.get("thrown_names") or []
    unvault_names = lc.get("unvault_names") or []
    if vault_names:
        tag = "🏦 vaulted"
    elif pending_names or (intent == "farmed" and names):
        tag = "⏳ holding"
    elif intent == "seen":
        tag = "👁 seen"
    elif thrown_names:
        tag = "🗑 throw"
    elif lc.get("gone_candidates"):
        tag = "👻 gone?"
    else:
        tag = "·"
    model_tag = rd.get("model") or FAST_MODEL
    esc = " ⬆genius" if rd.get("escalated") else ""
    pri = " ⚡" if used_priority else ""
    fare = " 👋FAREWELL" if farewell else ""
    lc_note = ""
    if vault_names:
        lc_note = " · VAULT " + ", ".join(vault_names[:3])
    elif pending_names:
        lc_note = " · HOLDING " + ", ".join(pending_names[:3]) + f" (≥{HOLD_MS//1000}s or stash)"
    elif thrown_names:
        lc_note = " · THROW-OUT " + ", ".join(thrown_names[:3])
    elif lc.get("gone_candidates"):
        lc_note = " · candidate gone " + ", ".join(lc["gone_candidates"][:3])
    elif lc.get("apply_held"):
        lc_note = " · hold apply (" + lc["apply_held"] + ")"
    ocr_ms = (ocr_rd or {}).get("ms")
    # v946.1 — tab-strip OCR + sticky walk so gems/materials don't vanish into shared/empty
    _model_tab = _norm_stash_tab(rd.get("stashTab"), rd.get("scene"))
    _fp = frame_path_for_id(frame_id) if frame_id else ""
    _cap_for_tab = capture_ts or _capture_ts_from_frame_id(frame_id) or int(time.time() * 1000)
    stash_tab = _resolve_stash_tab(
        rd.get("scene"), rd.get("stashTab"),
        frame_path=_fp if (_fp and os.path.isfile(_fp)) else None,
        ocr_rd=ocr_rd, ts=_cap_for_tab)
    try:
        rd["stashTab"] = stash_tab  # lifecycle / state ring match journal
    except Exception:
        pass
    # v1522 — the live Chronicle visit. Recording is free; the READ is offered, never auto-fired.
    try:
        _closed_visit = _chron_visit_step(rd.get("scene"), rd.get("chronicleTab"),
                                          frame_id=frame_id, ts=_cap_for_tab)
        if _closed_visit and _closed_visit.get("n"):
            _lg = _closed_visit.get("ledger") or ""
            ev("read", "📜 Chronicle visit captured — %d frames%s · ask the console to read it"
               % (_closed_visit["n"], (" · " + ("Holy Grail" if _lg == "uniques" else "Set pieces"))
                  if _lg else " · ledger unread"))
            _journal({"lane": "chronicle", "kind": "visit", "ts": int(time.time() * 1000),
                     "ledger": _lg, "frames": _closed_visit["frames"][:120],
                     "n": _closed_visit["n"], "since": _closed_visit["since"],
                     "until": _closed_visit["until"]})
    except Exception:
        pass
    ocr_set = {_norm_name(x) for x in ((ocr_rd or {}).get("names") or [])}
    confirmed = [nm for nm in names if _norm_name(nm) in ocr_set]
    conf_note = ((" · ✓ocr " + ", ".join(confirmed[:3])) if confirmed else "")
    tab_note = (f" · tab:{stash_tab}" if stash_tab else "")
    if stash_tab and stash_tab != _model_tab:
        tab_note += "↻"  # tab identity refined (OCR/sticky) vs model alone
    # v948 — session sticky: split always-there Cube/Tomes/shared echoes from NEW/MOVED
    _now_sticky = int(time.time() * 1000)
    names_new, names_echo, names_moved, sticky_tags = _classify_name_sticky(
        names, rd.get("names_loc") or {}, stash_tab, rd.get("scene"), _now_sticky)
    # merge sticky tags into lifecycle (don't overwrite vault/throw verdicts)
    _lt = lc.get("lifecycle_tags") or {}
    for _nm, _tg in (sticky_tags or {}).items():
        if _nm not in _lt or _lt.get(_nm) in ("seen", "holding", ""):
            _lt[_nm] = _tg
    try:
        lc["lifecycle_tags"] = _lt
    except Exception:
        pass
    sticky_note = ""
    if names_new or names_moved:
        sticky_note = " · NEW " + ", ".join((names_new or names_moved)[:4])
        if names_echo:
            sticky_note += " · echo " + str(len(names_echo))
    elif names_echo and names:
        sticky_note = " · sticky echo ×" + str(len(names_echo)) + " (no new items)"
    # mind line prefers new/moved over cube spam
    _show = names_new if names_new else (names_moved if names_moved else names)
    line = ((("🗺 "+rd.get("area","")+" · ") if rd.get("area") else "") + tag + " " + str(rd.get("scene") or "")
            + tab_note + " — "
            + (", ".join(_show[:5]) + ("…" if len(_show) > 5 else "") if _show else "no readable item text (honest empty)")
            + sticky_note + lc_note + conf_note
            + (" ["+str(rd.get("mode","?"))+" "+model_tag+esc+pri+fare+" "+str(round((rd.get("ms") or 0)/1000,1))+"s]" if rd.get("ms") else fare)
            + (f" · ocr {ocr_ms}ms" if ocr_ms is not None else ""))
    if farewell:
        ev("read", "👋 farewell · " + line)
        print(f"  👋 farewell · {(rd.get('area') or '?')} · {tag} {rd.get('scene')}{tab_note}  "
              f"{'📦 ' + ' · '.join(names[:6]) + (' …' if len(names) > 6 else '') if names else '· nothing readable'}"
              f"{lc_note}{conf_note}  [{model_tag}]")
    else:
        ev("read", line)
        print(f"  🗺 {(rd.get('area') or '?')} · {tag} {rd.get('scene')}{tab_note}  "
              f"{'📦 ' + ' · '.join(names[:6]) + (' …' if len(names) > 6 else '') if names else '· nothing readable'}"
              f"{lc_note}{conf_note}  [{model_tag}{esc}{pri}]")
    completed_ts = int(time.time() * 1000)
    # capture clock wins: frameId suffix → explicit capture_ts → completed (last resort)
    cap_ts = capture_ts or _capture_ts_from_frame_id(frame_id) or completed_ts
    vision_ms = int(rd.get("ms") or 0) or max(0, completed_ts - cap_ts)
    rec = {
        "ts": cap_ts,                    # v784 — CAPTURE moment (matches hist photo)
        "captureTs": cap_ts,
        "completedTs": completed_ts,     # when AI answer landed
        "names": names, "n": n, "area": rd.get("area") or "",
        "scene": rd.get("scene") or "gameplay", "tz": rd.get("tz", []), "ms": vision_ms,
        "mode": rd.get("mode", ""), "lane": "deep", "model": model_tag, "conf": rd.get("conf"),
        # REG-1603 - a read that did not happen says so, with the reader's own first line, instead of passing
        # for an empty "gameplay" look (the ALT: "Failed to authenticate: OAuth session expired ...")
        **({"readFailed": True, "readErr": _first_line(rd.get("readErr"))
            or _first_line(raw if raw is not None else globals().get("_LAST_RAW", ""))
            or "the reader returned nothing"} if rd.get("mode") == "empty" and not farewell else {}),
        **({"eye": rd.get("eye")} if rd.get("eye") else {}),
        **({"backup": str(rd.get("backup"))[:160]} if rd.get("backup") else {}),
        "intent": intent, "stashTab": stash_tab, "frameId": frame_id, "sessionId": SESSION_ID,
        "escalated": bool(rd.get("escalated")), "interest": interest, "priority": used_priority,
        "provisional": False, "farewell": bool(farewell),
        "sim": bool(rd.get("sim")),      # v787 — replay/harness truth travels WITH the read (R3 sleeper)
        "names_loc": rd.get("names_loc") or {},   # v830 — per-name location truth
        # #54 / REG-1558 — per-name doll slot (the reader's word) and frame point (the geometry's
        # evidence), carried AS PARSED: {} is "the read named none", None is UNKNOWN (the parse
        # raised, the vocabulary was unavailable, or this read never went through _parse_read).
        # An `or {}` here would turn UNKNOWN back into a measured empty one frame up.
        "names_slot": rd.get("names_slot"),
        "names_xy": rd.get("names_xy"),
        "xySpace": rd.get("xySpace"),     # v3552 — the [w, h] the points above were measured in (None: unknown)
        # v948 — session sticky split (full names kept for vision truth; new/echo for boards)
        "names_new": names_new,
        "names_echo": names_echo,
        "names_moved": names_moved,
        "sockets": rd.get("sockets") or {},        # v946.5 — per-item socket count (name -> N, 1..6)
        "raw": ("" if farewell else (raw if raw is not None else globals().get("_LAST_RAW", ""))) or ("«farewell read»" if farewell else ""),
        "dispatch": dict((dispatch if dispatch is not None else globals().get("_DISPATCH_CTX")) or ({"origin": "farewell"} if farewell else {})),
        "promptVer": PROMPT_VER,   # v832 — which prompt read this frame
        "agentVer": VERSION,
        "promptHash": hashlib.md5(READ_PROMPT.encode()).hexdigest()[:10],   # v838 (A2.9) — bisectable eyes
        "parse": rd.get("_parse_audit") or {},   # v835 — the clamp/drop audit
        "pre": _pre_triage(names, ocr_rd),                       # v853 — the gates, journaled
        "chain": lc.get("chain") or {},                          # v855 — provenance at decision time
        "ocr_raw": ((ocr_rd or {}).get("raw_lines") or [])[:16], # v853 — OCR's literal sight
        "decisions": {n: {"loc": (rd.get("names_loc") or {}).get(n, ""),
                          "tag": (lc.get("lifecycle_tags") or {}).get(n, ""),
                          "why": _reason_for((lc.get("lifecycle_tags") or {}).get(n, ""),
                                             (rd.get("names_loc") or {}).get(n, "")),
                          "chain": (lc.get("chain") or {}).get(n)}
                      for n in names},   # v836/v856 — THE DECISION CHAIN with provenance nested
        "equipped_names": [n for n in names if (rd.get("names_loc") or {}).get(n) == "equipped"],
        "ocr_seeded": _ocr_seed,         # v795 — names the fast lane saved from an empty deep read
        "ocr_ms": ocr_ms, "ocr_names": (ocr_rd or {}).get("names") or [],
        "confirmed_names": confirmed,
        "discovered_names": rd.get("discovered") or [],   # v763 — chat discovery broadcasts: chronicle-only, never vault
        # #118 — the row's own First Found stamp, dropper and sort word. _parse_read has
        # kept them since v1818 and the journal row is what the live lane reads. A date
        # that never lands here cannot reach a sighting. None: this read did not parse
        # the field. {} or "": parsed, and nothing that dated survived.
        "chronicleSort": rd.get("chronicleSort"),
        "foundAt": rd.get("foundAt"),
        "droppedBy": rd.get("droppedBy"),
        "vault_names": vault_names, "farmed_names": vault_names,
        "pending_names": pending_names, "thrown_names": thrown_names,
        "unvault_names": unvault_names,
        "lifecycle_tags": lc.get("lifecycle_tags") or {},
        "anchor": lc.get("anchor", "n/a"),
        "gone_candidates": lc.get("gone_candidates") or [],
        "holdMs": HOLD_MS,
        # v880 (SIM spec A2.5) — BOARD: what actually left the agent, per name. Verdict ≠
        # board effect; this is the effect, with 'nothing' names carrying their why.
        "board": {
            "vault": list(vault_names),
            "chronicle": sorted(set((rd.get("discovered") or [])
                                    + [n for n in names_new if (rd.get("names_loc") or {}).get(n) == "equipped"]
                                    + [n for n in names if (rd.get("names_loc") or {}).get(n) == "equipped"
                                       and n not in names_echo])),
            # v948 — only NEW/MOVED feed seen/chronicle boards; sticky echo stays off the noise path
            "seen": ([n for n in names_new if not _is_anchor(n) and not _is_junk(n)] if intent == "seen" else []),
            "unvault": list(unvault_names),
            "nothing": [{"name": n, "why": (lc.get("lifecycle_tags") or {}).get(n, "no-verdict")}
                        for n in names
                        if n not in vault_names and n not in (unvault_names or [])
                        and n not in names_echo
                        and not (intent == "seen" and not _is_anchor(n) and not _is_junk(n))],
            "echo": list(names_echo),
            "new": list(names_new),
            "moved": list(names_moved),
        },
        # v880 (SIM spec A2.6) — VISION: which image the model actually ate
        "vision": {
            "path": ("frames/hist/%s.jpg" % frame_id) if frame_id else "",
            "bytes": (os.path.getsize(os.path.join(HIST_DIR, str(frame_id) + ".jpg"))
                      if frame_id and os.path.isfile(os.path.join(HIST_DIR, str(frame_id) + ".jpg")) else 0),
            "timeoutMs": 75000,
            "escalated": bool(rd.get("escalated")),
            "finalModel": model_tag,
        },
    }
    if (rd.get("scene") or "") == "transition":
        rec["transition_from"] = LAST_AREA
        rec["note"] = transition_note(LAST_AREA, n)
    # #54 — THE LOGIN ROW CARRIES THE NAME. Written only when the parse kept one (a char-select scene
    # with a readable name), so 10,000 rows of play do not carry an empty key that reads like a
    # character nobody named. equipped_ledger.character_of_row is the one reader of this key.
    if rd.get("character"):
        rec["character"] = rd.get("character")
    elif rd.get("scene") == "char-select" and "character" in rd and rd.get("character") is None:
        rec["character"] = None   # REG-1558 — a login row whose name the parse could not read: UNKNOWN, on the row
    for _k in ("gameName", "cls", "level", "avatarClass"):   # v3855 - identity signals, never a password
        if rd.get(_k):
            rec[_k] = rd.get(_k)
    _journal(rec)
    with _state_lock:
        st = _load()
        st.setdefault("seen", []); st.setdefault("farmed", [])
        st["reads"].append(dict(rec, raw=""))   # v832 — the ring stays thin; the JOURNAL keeps the thought
        st["reads"] = st["reads"][-200:]
        st["readCount"] = n
        st["ap"] = dict(_AP)
        st["lifecycle"] = _LIFECYCLE.snapshot()
        def _push(arr, name, extra):
            arr.append({"ts": rec["ts"], "name": name, "area": rd.get("area") or "", **extra})
            del arr[:-200]
        if intent == "seen":
            for nm in names:
                if not _is_anchor(nm) and not _is_junk(nm):
                    _push(st["seen"], nm, {"scene": "loot", "src": "deep"})
        for nm in vault_names:
            st["seen"] = [s for s in st["seen"] if s.get("name", "").lower() != nm.lower()]
            _push(st["farmed"], nm, {"scene": rd.get("scene") or "inventory",
                                     "tag": (lc.get("lifecycle_tags") or {}).get(nm, "vault")})
        _save(st)
    # v926 SECOND LOOK — queue a verify pass on any REAL item read (not sim/farewell/verify).
    # It runs in the next idle gap and corrects this exact frame's read.
    try:
        _itemish_names = [x for x in names if _itemish(x)]
        _fidk = str(frame_id)
        if (VERIFY_ON and _itemish_names and frame_id and not farewell
                and not rd.get("sim") and not _fidk.endswith("#v")
                and not any(j.get("fid") == _fidk for j in _VERIFY_Q)):   # fid-dedup: one look per frame
            if len(_VERIFY_Q) >= _VERIFY_Q.maxlen:
                try: ev("skip", "verify backlog full — dropped a second look")
                except Exception: pass
            _VERIFY_Q.append({"fid": _fidk, "names": _itemish_names, "vaulted": list(vault_names),
                              "n": n, "sid": SESSION_ID, "scene": rd.get("scene") or "loot", "cap_ms": _cap_ms})
    except Exception:
        pass
    return rec

def farewell_read(force_frame=None):
    """v740 — one last capture + deep read on shutdown so end-of-run stash is never lost.

    Run #7 miss: garbage stashed then agent killed within seconds → no settle/gap/read.
    Farewell bypasses settle/gap and always publishes (flag farewell=true).
    force_frame: test seam (path to image); skips capture.
    Returns the published record, or None on hard failure.
    """
    print("\n  👋 farewell read — one last look so end-of-run stash is not lost…")
    ev("boot", "farewell read — capturing final frame")
    beat("reading", 0.0)
    _AP["mode"] = "read"
    frame = force_frame
    if not frame:
        frame = live_frame_path()
        try:
            if WATCH_MODE:
                f = newest_watched_frame()
                if f:
                    frame = f
                elif not os.path.isfile(frame):
                    ev("cap", "farewell: no watch frame")
                    print("  👋 farewell: no frame available — skipping")
                    return None
            elif _stub_capture_only():
                # #63 — a stub agent's last look is synthetic too; it never grabs the real screen
                if not capture_stub_synth(frame):
                    ev("cap", "farewell: synthetic frame could not be written")
                    print("  👋 farewell: synthetic frame could not be written — skipping")
                    return None
            else:
                if not capture_mac(frame):
                    # fall back to last vision JPEG if capture fails mid-shutdown
                    jp = os.path.join(FRAMES, "read.jpg")
                    if os.path.isfile(jp):
                        frame = jp
                        ev("skip", "farewell: capture failed — using last read.jpg")
                    else:
                        # v753 — deepest fallback: the newest archived hist frame
                        try:
                            hs = sorted((os.path.join(HIST_DIR, f) for f in os.listdir(HIST_DIR)
                                         if f.lower().endswith(".jpg")), key=os.path.getmtime)
                        except Exception:
                            hs = []
                        if hs:
                            frame = hs[-1]
                            ev("skip", "farewell: capture failed — using newest archived frame")
                        else:
                            ev("cap", "farewell capture failed")
                            print("  👋 farewell: capture failed — skipping")
                            return None
        except Exception as e:
            ev("cap", f"farewell capture error: {e}")
            print(f"  👋 farewell: capture error — {e}")
            return None
    if not os.path.isfile(frame):
        print("  👋 farewell: frame missing — skipping")
        return None
    with _state_lock:
        try:
            n = int((_load().get("readCount") or 0)) + 1
        except Exception:
            n = 1
    read_ts = int(time.time() * 1000)
    frame_id = archive_read_frame(frame, n, read_ts) or ""
    try:
        # deep only — farewell must land; OCR is optional and can wait
        rd = claude_read(frame)
    except Exception as e:
        ev("cap", f"farewell vision failed: {e}")
        print(f"  👋 farewell: vision failed — {e}")
        return None
    if not rd:
        rd = {"area": "", "scene": "gameplay", "names": [], "tz": [], "conf": None,
              "mode": "empty", "model": FAST_MODEL, "ms": 0}
    rec = emit_deep_read(rd, n=n, frame_id=frame_id, interest=1.0,
                         used_priority=True, ocr_rd=None, farewell=True,
                         capture_ts=read_ts)
    names = rec.get("names") or []
    scene = rec.get("scene") or "?"
    tab = rec.get("stashTab") or ""
    vault = rec.get("vault_names") or []
    summary = scene + (f"/{tab}" if tab else "")
    if vault:
        summary += " · VAULT " + ", ".join(vault[:4])
    elif names:
        summary += " — " + ", ".join(names[:4])
    else:
        summary += " — empty"
    print(f"  👋 farewell read done: {summary}")
    ev("boot", f"farewell done · {summary}"[:120])
    return rec

_FAREWELL_DONE = False
_STOPPING = False

def close_session(reason="stop", farewell=True):
    """v847/v899 — seal the theatre reel then exit.
    Always journals session_end. Farewell vision is hard-capped (FAREWELL_MAX_S, default 12s)
    so End Session after a long run never sticks on SIGNING OFF for 90s+."""
    global _FAREWELL_DONE, _STOPPING
    if _FAREWELL_DONE:
        os._exit(0)
    _FAREWELL_DONE = True
    _STOPPING = True
    reason = str(reason or "stop")[:60]
    print(f"\n  👋 closing session ({reason})" + (" — farewell read…" if farewell else " — sealing reel…"))
    ev("boot", "session close · " + reason + (" · farewell" if farewell else " · soft off"))
    # v1689 — flush a Chronicle visit that is STILL OPEN. It goes BEFORE session_end so the visit
    # row lands inside the session it belongs to; without it, looking at the Chronicle last (the
    # natural way to register finds) journalled nothing at all. Free — no read is fired.
    try:
        chron_visit_flush()
    except Exception:
        pass
    # Seal the reel FIRST so a force-kill mid-farewell still leaves a complete session on disk
    try:
        _journal({
            "ts": int(time.time() * 1000),
            "n": 0,
            "scene": "session_end",
            "names": [],
            "sessionId": SESSION_ID,
            "note": reason,
            "farewell": bool(farewell),
            "mode": "session_end",
            "lane": "system",
            "ver": VERSION,
        })
    except Exception as e:
        print(f"  👋 session_end journal failed: {e}")
    # v925 LIGHT — the farewell VISION read is opt-in now (TV_FAREWELL=1). Default END SESSION
    # just seals + exits so it can NEVER hang on a Claude call (the "button stuck" bug).
    if farewell and not FAREWELL_READ_ON:
        farewell = False
        print("  👋 light end — sealed, no farewell read")
    try:
        # v925-R4 (Grok) — a light end must not join a stuck mid-flight read for 8s. Give the
        # pool ~2s to wind down; a full farewell run still gets the longer cap.
        # v1206 — keep_worker0 only when a real farewell read is actually about to run right
        # after this call; otherwise `_WORKER`'s warm claude -p child gets swept too instead of
        # orphaned (see _pool_shutdown's v1206 note).
        _pool_shutdown(timeout=(min(FAREWELL_MAX_S, 8.0) if farewell else 2.0), keep_worker0=farewell)
    except Exception:
        pass
    if farewell:
        # v899 — never block exit on a hung Claude farewell: race with hard deadline
        _fare_box = {"done": False}

        def _fare_run():
            try:
                with _emit_lock:
                    farewell_read()
            except Exception as e:
                print(f"  👋 farewell failed: {e}")
            finally:
                _fare_box["done"] = True

        _ft = threading.Thread(target=_fare_run, daemon=True, name="tv-farewell")
        _ft.start()
        _ft.join(timeout=FAREWELL_MAX_S)
        if not _fare_box["done"]:
            print(f"  👋 farewell timed out after {int(FAREWELL_MAX_S)}s — sealing without it")
            ev("skip", "farewell timed out · seal continues")
    _journal_flush(timeout=5.0)
    try:
        # v883 (Konyo: 'sessions are not showing the real frame-by-frame') — REEL FOLD: loose
        # f_*.jpg footage was a shared pool the reaper shed FIRST, so every sealed run went
        # hollow within hours. Fold this session's window into frames/hist/reel_<sid>/ —
        # rename on the same volume, instant — and the reaper retires whole old reels last.
        _hd = HIST_DIR
        _t0 = int(globals().get("_SESSION_T0_MS") or (SESSION_ID.split("_")[1] if "_" in SESSION_ID else 0) or 0)
        _t1 = int(time.time() * 1000) + 2000
        if os.path.isdir(_hd) and _t0:
            _reel = os.path.join(_hd, "reel_" + SESSION_ID)
            _moved = 0
            for _fn in os.listdir(_hd):
                if not (_fn.startswith("f_") and _fn.endswith(".jpg")):
                    continue
                try:
                    _fts = int(_fn[2:-4])
                except Exception:
                    continue
                if _t0 - 2000 <= _fts <= _t1:
                    if not _moved:
                        os.makedirs(_reel, exist_ok=True)
                    try:
                        os.replace(os.path.join(_hd, _fn), os.path.join(_reel, _fn))
                        _moved += 1
                    except Exception:
                        pass
            if _moved:
                # v894 — write reel index so SIM loads without scanning every jpg name
                #
                # v1608 (Konyo: 'still a black screen when trying to record') — THE INDEX *IS*
                # THE REEL, SO IT GOES DOWN FIRST. TWO PHASES. DO NOT RE-INVERT THEM.
                #
                # Measured on his real footage: chronicle_retro.is_dead_frame() costs ~0.076 s per
                # frame, so the blank pass below runs ~7.4 s on a 98-frame reel. Meanwhile
                # control_app.stop_agent() asks for shutdown (timeout 1.0 s), waits wait_s = 2.5 s
                # and then SIGKILLs every agent pid — the hard kill lands ~3.5 s after the ask.
                # Writing index.json only AFTER the blank pass therefore put the one artefact the
                # reel cannot exist without ~4 s the WRONG side of the kill: the 01:04 session
                # sealed 98 real jpgs and no index at all, and theatre / read_reel / sweep_hist all
                # read index.json — an index-less reel plays BLACK. The 1-frame reels survived only
                # because their pass finished in ~0.1 s. It is not deterministic (three older
                # 114/126/153-frame reels did get indexes; /api/off, window close and atexit give
                # different grace) — but the ordering is the whole difference:
                #   phase 1  filenames only, milliseconds, atomic  -> the reel is PLAYABLE
                #   phase 2  blank enrichment, time-boxed, atomic  -> the reel is nicer
                # The blank flags are an optimisation. The index is the reel's existence.
                _blank = 0
                _idx = []
                try:
                    _idx = sorted(
                        f for f in os.listdir(_reel)
                        if f.startswith("f_") and f.endswith(".jpg")
                    )
                except Exception as _e:
                    print(f"  ⛔ REEL LISTING FAILED for reel_{SESSION_ID}: {_e!r} — "
                          f"no index can be written, reel is UNPLAYABLE until repaired")

                def _reel_index_write(_doc):
                    # atomic: same-dir tmp -> flush -> fsync -> os.replace. A SIGKILL landing at any
                    # instant leaves either the previous index or the new one, never a half file.
                    _tmp = os.path.join(_reel, "index.json.tmp")
                    with open(_tmp, "w", encoding="utf-8") as _jf:
                        json.dump(_doc, _jf)
                        _jf.flush()
                        os.fsync(_jf.fileno())
                    # REG-1679 — the ONE replace rule: a brief lock (an indexer, an antivirus on his ALT) is waited out.
                    # An immediate retry hit the same lock and left the NEWER index stranded in index.json.tmp.
                    try:
                        import reel_index as _rix
                        _rix.replace_with_retry(_tmp, os.path.join(_reel, "index.json"))
                    except ImportError:
                        os.replace(_tmp, os.path.join(_reel, "index.json"))

                # ── phase 1: filenames only ───────────────────────────────────────────────
                _meta = []
                for _fn in _idx:
                    try:
                        _meta.append({"f": _fn, "ts": int(_fn[2:-4])})
                    except Exception:
                        continue      # unparseable stamp is not a frame — same as v894
                _ixdoc = {"sessionId": SESSION_ID, "n": len(_meta),
                          "blank": 0, "frames": _meta, "blankPass": False}
                _cap = _capture_for_seal() or {}
                try:
                    import capture_stamp as _cs
                    _film = None
                    for _fn in _idx:
                        _film = _cs.film_size_from_jpeg(os.path.join(_reel, _fn))
                        if _film:
                            break
                    if _film:
                        _merged = dict(_cap)
                        _merged["filmW"], _merged["filmH"] = _film
                        _cap = _cs.from_measured(_merged)
                except Exception:
                    pass
                if _cap:
                    _ixdoc["capture"] = _cap
                # v1595 — STAMP THE MINI. Without this the flag changes nothing that
                # outlives the process: vault_retro reads the sealed reel, not the argv of
                # a run that has already exited.
                # ── v2031 — THE FOURTH JOIN, AND v2027 LEFT IT ───────────────────────────────
                # v2027 fixed three links so a lane card could declare a focus on a FULL session:
                # tv_diablo parses --mini-focus outside MINI mode, /api/on accepts a focus, and the
                # card sends one. Then the STAMP stayed behind `if MINI_MODE:` — so the flag was
                # parsed correctly and never written down, and vault_retro reads the sealed reel,
                # not the argv of a process that has already exited.
                #
                # MEASURED on the reel he filmed at 22:18 under a console that already had v2027:
                # index.json keys were ['blank','blankPass','frames','n','sessionId'] — no focus at
                # all, not even an empty one. Four links in a chain, three joined, and the whole
                # thing still carries nothing. That is the defining property of this class: it
                # reads as wired from both ends. [[the-unjoined-end]]
                #
                # mini / miniSeconds stay MINI-only because they genuinely are about the bound.
                # The FOCUS is about what he says he is looking at, which has nothing to do with
                # how long the recording runs.
                if MINI_FOCUS:
                    _ixdoc["focus"] = MINI_FOCUS
                if MINI_MODE:
                    _ixdoc["mini"] = True
                    # v1783 — RECORD WHETHER HE CHOSE THIS. The retro sweep skips the classifier
                    # for a declared focus on the v1603 premise that pressing MINI TELLS the app
                    # what he is parked on. That holds for a focus he picked and fails for one he
                    # never touched: "stash" is the default here, the console pre-selects it, and
                    # an untouched default then labels town, a fight and a Chronicle page as a
                    # stash panel without any of them being looked at. An untouched default is not
                    # a statement, so the sweep is told which kind of stamp this is.
                    _ixdoc["miniSeconds"] = MINI_SECONDS
                # v2031 — focusChosen travels with the FOCUS, never with the mini. The sweep keys
                # its trust on it (_declared_surface: focusChosen false -> not trusted), so a focus
                # stamped without it would be trusted by default — the exact inversion v1783 built
                # this field to prevent.
                if MINI_FOCUS:
                    _ixdoc["focusChosen"] = MINI_FOCUS_CHOSEN
                _indexed = False
                for _attempt in (1, 2):     # one retry, then say so out loud
                    try:
                        _reel_index_write(_ixdoc)
                        _indexed = True
                        break
                    except Exception as _e:
                        if _attempt == 2:
                            print(f"  ⛔ REEL INDEX WRITE FAILED for reel_{SESSION_ID}: {_e!r} — "
                                  f"reel is UNPLAYABLE until repaired")
                if _indexed:
                    print(f"  🗂 reel index written — reel_{SESSION_ID} lists "
                          f"{len(_meta)} frame(s)")

                # ── phase 2: blank enrichment ─────────────────────────────────────────────
                # v1545 — MARK THE BLANK CAPTURES, ONCE, HERE.
                #
                # 18 of the 394 frames in his sealed footage are the window grabbed with nothing
                # on it, and 16 of the 17 in the worst reel land in the FIRST NINETEEN SECONDS:
                # capture starts while D2R is still launching, so the window exists (the grab
                # succeeds) and is blank until the title screen paints.
                #
                # Marking beats deleting — that footage is real, the SIM replays it, and throwing
                # away evidence to tidy a count is the wrong trade. Marking beats measuring later
                # too: the flatness is computed once at seal instead of on every sweep, and a
                # blank frame sitting inside a real Chronicle visit no longer splits that visit
                # into two runs and charges for two classifies.
                #
                # v1608 — and TIME-BOXED at 2.0 s, under the console's 2.5 s force-kill. Unbounded,
                # this pass is guaranteed to be killed on any real reel; whatever it cannot reach
                # in time simply stays unmarked (blankPartial), which is honest, and the phase-1
                # index is already on disk so the reel plays either way.
                if _indexed and _meta:
                    _t_blank = time.time()
                    _scanned = 0
                    _partial = False
                    try:
                        import chronicle_retro as _cr
                        for _row in _meta:
                            if time.time() - _t_blank > 2.0:
                                _partial = True
                                break
                            try:
                                if _cr.is_dead_frame(os.path.join(_reel, _row["f"])):
                                    _row["blank"] = True
                                    _blank += 1
                            except Exception:
                                pass      # unmeasurable stays unmarked — never guessed blank
                            _scanned += 1
                        _ixdoc["blank"] = _blank
                        _ixdoc["blankPass"] = True
                        if _partial:
                            _ixdoc["blankPartial"] = True
                            _ixdoc["blankScanned"] = _scanned
                        _reel_index_write(_ixdoc)
                    except Exception as _e:
                        print(f"  ⚠ reel_{SESSION_ID}: blank-capture pass incomplete ({_e!r}) — "
                              f"index stands, those frames are just unmarked")
                print(f"  🎞 reel folded — {_moved} footage frames sealed into reel_{SESSION_ID}")
                # v1548 — the warm-up gate is only trustworthy if it says what it withheld
                _ws = int(globals().get("_FOOTAGE_WARMSKIP") or 0)
                if _ws:
                    print(f"  ⏳ {_ws} frame(s) held back while D2R was still painting — "
                          f"blank captures that never reached the reel")
                # ── v1608.1 — THE LATE SWEEP. Phase 2 runs up to 2 s AFTER the fold above, and the
                # film thread keeps writing f_<ms>.jpg into FRAMES the whole time. Those frames land
                # after the fold has already walked the directory, so they stay loose — outside the
                # reel, in the shared pool the reaper sheds FIRST (the exact v883 bug: sessions going
                # hollow within hours). test_roundtrip_sim caught it as "loose frames survived the
                # fold inside the session window", which is footage he would simply never see again.
                #
                # So sweep once more, with the SAME window rule as the fold, and re-index if anything
                # moved. Cheap (one listdir, a rename each) and it closes the window no matter how
                # long phase 2 took — which matters because phase 2's duration is deliberately
                # variable.
                try:
                    _late = 0
                    _t1b = int(time.time() * 1000) + 2000
                    for _fn in os.listdir(_hd):
                        if not (_fn.startswith("f_") and _fn.endswith(".jpg")):
                            continue
                        try:
                            _fts = int(_fn[2:-4])
                        except Exception:
                            continue
                        if _t0 - 2000 <= _fts <= _t1b:
                            try:
                                os.replace(os.path.join(_hd, _fn), os.path.join(_reel, _fn))
                                _late += 1
                                _meta.append({"f": _fn, "ts": _fts})
                            except Exception:
                                pass
                    if _late:
                        _meta.sort(key=lambda _r: _r["ts"])
                        _ixdoc["frames"] = _meta
                        _ixdoc["n"] = len(_meta)
                        _ixdoc["lateFolded"] = _late
                        _reel_index_write(_ixdoc)
                        print(f"  🧹 {_late} late frame(s) folded in after the seal pass")
                except Exception as _e:
                    print(f"  ⚠ late fold sweep skipped ({_e!r}) — some frames may remain loose")

                # said out loud, because a capture lane producing blank frames is a fault that would
                # eat a real Chronicle page exactly as happily as it eats a loading screen
                if _blank:
                    print(f"  ⚠ {_blank} blank capture(s) in this reel — the window was grabbed with "
                          f"nothing painted on it (usually D2R still launching)")
    except Exception as _e:
        # v1608 — a reel fold that dies silently is how footage disappears without a trace
        print(f"  ⛔ REEL FOLD FAILED for reel_{SESSION_ID}: {_e!r} — "
              f"this session's footage may be unsealed or unindexed")
    with _state_lock:
        try:
            st = _load()
            st["online"] = False
            st["stopping"] = False
            st["sessionId"] = SESSION_ID
            _save(st)
            _state_flush()   # v879 — Grok flush list #3/#6: never exit with a dirty write-behind
        except Exception:
            pass
    try:
        _eye_clear()
    except Exception:
        pass
    try:
        _settle_queue_clear()
    except Exception:
        pass
    print("\n📺 TV DIABLO off — session saved · good hunting.")
    os._exit(0)


def _shutdown_handler(signum, frame):
    """SIGINT/SIGTERM/SIGBREAK → close session (farewell when possible)."""
    global _STOPPING
    _STOPPING = True
    if _FAREWELL_DONE:
        os._exit(0)
    # Force-kill paths often send a second SIGKILL — first signal gets full farewell when possible
    sig_name = "SIGINT" if signum == signal.SIGINT else (
        "SIGTERM" if signum == signal.SIGTERM else (
            "SIGBREAK" if getattr(signal, "SIGBREAK", None) == signum else str(signum)))
    # Env TV_FAREWELL=0 lets control request a soft seal without vision (OFF button)
    fare = os.environ.get("TV_FAREWELL", "1") not in ("0", "false", "no")
    try:
        close_session(reason="signal:" + sig_name, farewell=fare)
    except Exception:
        os._exit(0)

if __name__ == "__main__":
    # one-shot validation: python3 tv/tv_diablo.py --test <image>  (run in YOUR terminal —
    # a Claude Code session cannot nest another; from a normal shell this is a plain call)
    if "--test" in sys.argv:
        try:
            img = sys.argv[sys.argv.index("--test") + 1]
        except IndexError:
            print("usage: python3 tv/tv_diablo.py --test <image.jpg>"); sys.exit(2)
        print("📺 test read:", os.path.abspath(img))
        print(json.dumps(claude_read(img), indent=1))
        sys.exit(0)
    # v740 — farewell on Ctrl-C AND tvd stop (SIGTERM)
    try:
        signal.signal(signal.SIGINT, _shutdown_handler)
        signal.signal(signal.SIGTERM, _shutdown_handler)
        # v760.1 — Windows: the control app's soft-stop arrives as CTRL_BREAK (SIGBREAK);
        # without this the farewell NEVER fires on the cousin's box (taskkill-soft can't
        # reach a windowless console app, and SIGTERM does not exist on Windows).
        if hasattr(signal, "SIGBREAK"):
            signal.signal(signal.SIGBREAK, _shutdown_handler)
    except Exception:
        pass
    try:
        main()
    except KeyboardInterrupt:
        # fallback if signal handler not installed (rare)
        if not _FAREWELL_DONE:
            _shutdown_handler(signal.SIGINT, None)
