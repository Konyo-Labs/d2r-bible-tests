#!/usr/bin/env python3
"""v2026 — 🦅 THE EAGLE EYE: one pass over the WHOLE console, from above.

    python3 tv/console_doctor.py            report
    python3 tv/console_doctor.py --json     machine-readable (the /api/doctor payload)

Konyo, 2026-08-23: *"is there a MANAGER for the AI console? ... dont we need like a type of EAGLE
EYE kind of style management system here? eyes from above it all like that can see bugs happening
or something and fix it when its out of line?"*

WHY THIS, WHEN THERE ARE ALREADY DOCTORS. `chronicle_doctor` and `vault_doctor` each answer a
question about ONE lane, and `run_gates` answers a question about the SOURCE before a push. Nothing
looked at the RUNNING SYSTEM as a whole, and every defect found on the night this was written was
exactly that shape — no single lane was wrong, two correct things disagreed:

    the console served v2018 while the tree was v2024, for two hours, unnoticed
    the vault sweep read 0 pages while 4 reels on disk were 40-100% stash panels
    G5 said mode=off while the lane list still shipped a grok lane
    the vault pill said a lane was dark while the reel filed into it anyway
    the free cost pass called his footage worthless, from its own refusing stub

Not one of those is visible from inside the component that owns it. They are only visible from
above, which is what this is.

DOCTRINE, inherited wholesale from the other two doctors and NOT re-argued here:
  * it REPORTS. `--fix` exists but touches only the provably-reversible, and says what it did.
  * every check answers OK / MISSING (with the action) / UNKNOWN (with why), never a bare boolean.
  * an UNKNOWN is not a failure. "I could not check" and "it is broken" are different sentences,
    and collapsing them is the lie this whole codebase audits out. [[unknown-stays-unknown]]
  * it never re-implements a check that already exists — it CALLS the other doctors. Two copies of
    one rule is two things that drift apart, and only one of them gets fixed. [[copy-drift]]

FREE BY CONSTRUCTION: filesystem, git and localhost only. No model turn, no network, no paid read.
"""
import contextlib
import csv
import glob
import json
import ntpath
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

OK, MISSING, UNKNOWN, UNMEASURED = "ok", "missing", "unknown", "unmeasured"
#: REG-3203 - the page's own bound on an "opening" Shelf (control_ui TH_SHELF_OPEN_BOUND_MS, 60 s) plus a beat's slack
SHELF_OPENING_BOUND_S = 75


def _this_os():
    """sys.platform, through one seam (#171): a law drives a Windows-only branch of a row on any PC."""
    return sys.platform

#: ⚠ #229 — WHAT THE PASS IS DOING RIGHT NOW. MEASURED 2026-09-24 on his Windows ALT: the eagle's first
#: pass said "not measured yet" for 14+ minutes after boot, while the SAME checks finished standalone in
#: 229 s (cheap) + 143 s (periodic). A pass that never ends could only say "not measured yet", so nothing
#: could name the check it sat in. run() writes the running check here; the console publishes it.
#: [[heart-first]] [[in-progress-must-carry-what-is-moving]]
CURRENT = {"check": None, "since": None, "tick": None}
ICON = {OK: "🟢", MISSING: "🟠", UNKNOWN: "⚪", UNMEASURED: "◻"}
# REG-2998 - the console THIS process belongs to (TV_CONTROL_PORT, inherited by a child), never :17772 by name: a scratch
# console's doctor read his live console - /api/board_ownership runs JavaScript in his window. "" = no console to ask.
import console_port as _cport   # noqa: E402
CONSOLE = _cport.url() or ""


def _get(path, timeout=4):
    """GET a console route. Absent console is UNKNOWN, never a failure."""
    import urllib.request
    try:
        with urllib.request.urlopen(CONSOLE + path, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return None


def _serving_console(imported):
    """The control_app that is SERVING in this process, else the module handed in. -> module

    REG-1881 (#86 gap audit 21, the rows REG-1776 did not reach). The console runs control_app.py as
    __main__, so `import control_app` here builds a SECOND module whose state is its literals (v3012).
    Eight presence reads took `_FLEET_PRESENCE_CACHE` through that import, and the eagle runs inside the
    console. MEASURED 2026-10-07: with the serving module holding a roster, the fleet-lane row said "this
    console has not asked the site for the roster yet". The roster the card paints from is the one in
    __main__. Outside the console (a test, a harness, a launcher that imported control_app itself) the
    imported module is the one that serves, so it is handed back unchanged. A doctor run as its own
    process holds no roster the card painted either way. [[the-unjoined-end]] [[copy-drift]]"""
    m = sys.modules.get("__main__")
    if (m is not None and m is not imported
            and os.path.basename(str(getattr(m, "__file__", "") or "")) == "control_app.py"
            and hasattr(m, "_FLEET_PRESENCE_CACHE")):
        return m
    return imported


def _post(path, body=None, timeout=20):
    """POST a console route. Absent console is UNKNOWN, never a failure."""
    import urllib.request
    try:
        req = urllib.request.Request(
            CONSOLE + path, data=json.dumps(body or {}).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return None


#: ⚠ ONE READ OF HIS LIVE BOARD PER TICK. THREE checks now need /api/board_ownership, and that
#: route EVALUATES JAVASCRIPT IN THE WINDOW HE IS LOOKING AT. Two of the three predate this fold —
#: so the rail was already poking his board twice every ten minutes and nothing said so. Asking
#: three times buys no new information. Short TTL, so a human pressing the button twice still gets
#: a fresh answer. [[borrowed-surface]] — his window is not free to poke.
#: ⚠ SHARED FOR THE LENGTH OF ONE TICK, NEVER LONGER. My first cut memoised on a 5-SECOND TTL and
#: broke EIGHT existing guards at once — they stub `_post` and call a check directly, and a
#: module-level cache swallows the stub and serves the previous test's answer. THE COUNT WAS THE
#: TELL: eight failures from one edit is a shape mistake, not eight defects. So the share is scoped
#: to `run()`, which is the only place three checks are asked back to back; a check called on its
#: own always reads fresh, which is what every caller outside the rail expects.
#: [[feedback-suspect-the-instrument]]
_board_cache = {"active": False, "got": None}


def _board_read():
    if _board_cache["active"]:
        return _board_cache["got"]
    return _post("/api/board_ownership", {"sample": 0})


def _check_the_board_world_is_claimed():
    """An UNCLAIMED board lives in a guest world, and everything applied there is lost.

    This is the failure that cost a whole night: `bible.html` resolves `_D2R_OWNER` only from a
    clicked `d2r_ownerClaim`. Without it `_D2R_PFX` becomes 'I·<installId>·' — a per-install world.
    An apply into it returns ok:true, writes real rows, and they are unreachable from the next load.

    It is SILENT BY CONSTRUCTION: the ledger counts read exactly the same in a doomed world as in a
    real one, so nothing on any screen distinguishes them. That is precisely what a doctor is for.
    [[the-unjoined-end]]
    """
    got = _board_read()
    if not got:
        return UNKNOWN, "the console did not answer — nobody asked, so nothing is known"
    # v2147 — ASK THE MEMORY FIRST. The v2145 branch that "reports drift even when the board is
    # closed" was UNREACHABLE: a closed window answers ok:False, and both early returns below fired
    # before it. Measured by injecting worldDrift onto that payload — still UNKNOWN. And a closed
    # board is precisely the moment a relaunch just happened, so the remembered world is the only
    # thing that can speak. The verdict is read before anything is allowed to give up.
    _d = got.get("worldDrift") if isinstance(got, dict) else None
    if isinstance(_d, dict) and _d.get("state") == "drift":
        return MISSING, _d.get("why")
    if not got.get("ok"):
        return UNKNOWN, "the board refused the read: %s" % str(got.get("why"))[:90]
    # v2055 — "THE BOARD IS NOT OPEN" IS NOT "THE BOARD IS DOOMED".
    # _D2R_OWNER/_D2R_PFX are bible.html globals. On the console rail they do not exist, both read
    # falsy, and this check used to answer MISSING with "anything applied here is lost on the next
    # launch" — about a world that was claimed, on disk, and perfectly safe. After the night his
    # ledger actually was emptied, that is the last sentence that should ever be shown wrongly.
    if got.get("boardLoaded") is False:
        # v2145 — A CLOSED BOARD IS EXACTLY WHEN A RELAUNCH HAPPENED, so ask the REMEMBERED world
        # before giving up. Konyo armed auto-relaunch on the condition that nothing gets deleted or
        # regressed; what could regress is the board coming back as a DIFFERENT world, and that is
        # knowable from the record even with the window shut.
        _d = got.get("worldDrift") if isinstance(got, dict) else None
        if isinstance(_d, dict) and _d.get("state") == "drift":
            return MISSING, _d.get("why")
        return UNKNOWN, ("the board is not open in the window — ownership lives in bible.html's "
                         "globals, so it cannot be read from the console rail. Open the board to "
                         "find out."
                         + ("" if not _d else "  Last recorded: " + str(_d.get("why"))[:120]))
    if "owner" not in got:
        # v2044 added the field. An older console cannot answer, and MUST NOT read as a pass.
        return UNKNOWN, ("this console predates the ownership field (v2044) — restart it to find "
                         "out whether the board world persists")
    counts = got.get("counts") or {}
    total = sum(int(counts.get(k) or 0) for k in ("foundLog", "owned", "setPieces"))
    if got.get("owner"):
        # "claimed" and "the SAME world his vault is in" are different facts, and only the second
        # survives a relaunch. v2043 was silent precisely because the first one stayed true.
        _d = got.get("worldDrift") if isinstance(got, dict) else None
        if isinstance(_d, dict) and _d.get("state") == "drift":
            return MISSING, _d.get("why")
        _tail = "" if not (isinstance(_d, dict) and _d.get("state") == "ok") else " · " + str(_d.get("why"))
        return OK, ("the board is CLAIMED — it writes the bare keys, so what is applied persists"
                    + _tail)
    # ⚠ #239 — SAY WHAT THE AUTOMATIC CLAIM DECIDED. The console's own window now claims a board
    # with no claim by itself, unless this machine held a populated board before (restore, never
    # reseed). Still unclaimed means one of: that refusal, a board open in a browser rather than the
    # console window, or a claim that belongs to another install. The row names the first, because
    # it is the one with an action. [[the-unjoined-end]]
    _auto = ""
    try:
        import control_app as _ca
        _v = _ca.own_board_may_autoclaim()
        if isinstance(_v, dict) and _v.get("may") is False:
            _auto = "  The console's own window did NOT claim it by itself: " + str(_v.get("why"))[:220]
    except Exception:
        _auto = "  Whether the console's own window may claim it is UNKNOWN (the verdict would not run)."
    return MISSING, ("the board is an UNCLAIMED guest world (prefix %r) holding %d ledger entries — "
                     "anything applied here is lost on the next launch. Open the board and press "
                     "'This browser is mine'.%s" % (got.get("pfx"), total, _auto))


def _tree_version():
    # v2026 — READ THE WHOLE FILE. The first cut read 400KB and returned None, because D2R_BUILD
    # sits ~1.1MB into a 5.8MB file. A version check that answers None is a check that never fires,
    # and this one exists precisely to catch the drift that cost two hours. Caught by its own first
    # run, which is the argument for running a new doctor before believing it.
    try:
        with open(os.path.join(ROOT, "bible.html"), encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        m = re.search(r"D2R_BUILD\s*=\s*\{\s*id:'(v\d+)'", text)
        return m.group(1) if m else None
    except Exception:
        return None


# ── the checks ───────────────────────────────────────────────────────────────────────────────

def _check_version_drift():
    """THE ONE THAT COST TWO HOURS. A long-lived console keeps serving the code it booted with,
    and every stamp on the page still reads from disk — so the UI can show a version the running
    process has never executed. Nothing else can see this: the process is healthy and the tree is
    healthy, and only the pair is wrong."""
    st = _get("/api/status")
    tree = _tree_version()
    if st is None:
        return UNKNOWN, "the console is not answering on %s — nothing to compare a tree against" % (CONSOLE or "no port")
    running = st.get("ver")
    if not running or not tree:
        return UNKNOWN, "could not read one of the two versions (running=%r tree=%r)" % (running, tree)
    if running == tree:
        return OK, "the running console and the tree are both %s" % running
    return MISSING, ("the console is RUNNING %s while the tree is %s — every fix since %s is on "
                     "disk and not in the process. Restart it in your own window: bash "
                     "tv/tvd-scan.sh (never --force; headless cannot hold Screen Recording)"
                     % (running, tree, running))


def _check_behind_the_fleet():
    """IS THIS CHECKOUT BEHIND ORIGIN? The one kind of out-of-sync nothing here could see.

    ⚠ "version drift" IS A DIFFERENT QUESTION AND IT PASSES WHILE THIS FAILS. That check compares
    the RUNNING process against the TREE ON DISK. Dean's console sat at v2161 while origin was at
    v2246 — 85 versions — and drift was GREEN the whole time, correctly: his process and his disk
    agreed with each other. They were simply agreeing on old bytes. Konyo, on the phone with him:
    "there is no reason he isnt on my version and we arent synced." Nothing in these 22 checks
    asked the only question that would have caught it. [[the-unjoined-end]]

    ⚠ AND IT MUST NOT FETCH. The obvious implementation asks /api/update, which force-fetches, so
    it would belong in SLOW — and SLOW is exactly where "sweep would find" went to die: the eagle
    runs with include_slow=False, so a SLOW check never runs on the timer at all. This one reads
    the origin/main ref that is already on disk, which costs nothing and runs every tick. The
    console's own fleet banner refreshes that ref every 15 minutes (control_ui.html, v2248).

    ⚠ SO THE ANSWER CARRIES THE AGE OF THE REF, NOT THE AGE OF THE READ. "0 behind" against a ref
    last fetched three days ago means "0 behind what I knew three days ago", and saying it plainly
    is the difference between a fact and a reassurance. [[stale-reading]]
    """
    import time as _t
    import git_quiet as _gq

    def _git(*args):
        try:
            # v3409 — the THIRD git spawn in this module, found only after the one-door gate
            # stopped accepting `subprocess.run` as the door. See tv/git_quiet.py.
            # ⚠ v3437 — THREE of CPython's NINE posix_spawn conditions were violated here and
            # this site forked after v3429, because only close_fds was ever recorded as the law.
            # `git -C ROOT` replaces cwd=ROOT (condition six); _spawnable gives argv[0] a dirname.
            # ⚠ Resolved AT THE CALL SITE on purpose — doing it inside git_quiet would be invisible
            # here and the gate would have to report this site UNKNOWN rather than green.
            r = _gq.run([_spawnable("git"), "-C", ROOT] + list(args), close_fds=False,
                        capture_output=True, text=True, timeout=15)
            return (r.stdout or "").strip() if r.returncode == 0 else None
        except Exception:
            return None

    # a linked worktree or submodule carries `.git` as a FILE pointing at the real git dir — still a checkout
    if not os.path.exists(os.path.join(ROOT, ".git")):
        return UNKNOWN, "this install is not a git checkout, so there is no origin to be behind"
    if _git("rev-parse", "--verify", "--quiet", "origin/main") is None:
        return UNKNOWN, "no origin/main ref on disk yet — nothing has ever fetched here"

    # how old is what we are comparing against?
    age = ""
    for nm in ("FETCH_HEAD", os.path.join("refs", "remotes", "origin", "main")):
        p = os.path.join(ROOT, ".git", nm)
        if os.path.exists(p):
            mins = int(max(0, _t.time() - os.path.getmtime(p)) // 60)
            age = ("%d min" % mins) if mins < 120 else ("%.1f h" % (mins / 60.0))
            break
    against = (" (against an origin/main ref last refreshed %s ago)" % age) if age else \
              " (the age of that ref is UNKNOWN)"

    behind = _git("rev-list", "--count", "HEAD..origin/main")
    if behind is None or not behind.isdigit():
        return UNKNOWN, "could not count the commits between this checkout and origin/main"
    n = int(behind)
    if n == 0:
        return OK, "this checkout is level with origin/main%s" % against
    return MISSING, ("this checkout is %d commit%s behind origin/main%s. The console pulls on its "
                     "own every 15 minutes and restarts itself when the new build lands; if it has "
                     "not, the fleet banner's UPDATE NOW does it, or: git pull --ff-only"
                     % (n, "s" if n != 1 else "", against))


def _check_lane_intent():
    """A switch he turned off that is still being counted. `has_subscription()` answers CAN it run,
    `switch_on()` answers does he WANT it to, and for a long time only the first was asked."""
    try:
        import g5_grok_eyes as g5
    except Exception as e:
        return UNKNOWN, "g5_grok_eyes will not import: %s" % str(e)[:90]
    try:
        capable = bool(g5.has_subscription())
        wanted = bool(g5.switch_on())
        mode = g5.mode_intent()
    except Exception as e:
        return UNKNOWN, "could not read the G5 switch: %s" % str(e)[:90]
    st = _get("/api/status")
    lanes = None
    if st is not None:
        lanes = (st.get("lanes") or None)
    if not capable:
        return OK, "no Grok CLI here, so this machine is claude-only by capability (mode=%s)" % mode
    if capable and not wanted:
        return OK, "Grok is installed and you switched it OFF (mode=%s) — claude-only, by choice" % mode
    return OK, "Grok installed and switched on (mode=%s) — dual lane%s" % (
        mode, ("; console reports %s" % lanes) if lanes else "")


def _measured_write_rate():
    """GB/hour measured from HIS newest reels, or None when it cannot be measured.

    v2046 — this used to be the constant "roughly 9GB/hour". That number is real: v2019 clocked
    +37MB in 15s on a busy scene. So is 5.0-6.6GB/hour, measured 2026-08-24 across the three newest
    reels at 1.44-1.90 MB/frame and 55-60 frames/min. Both are true, because JPEG size tracks scene
    complexity and the rate swings ~2x with what he is looking at.

    A single constant therefore cannot describe it, and quoting one as if it could is the shape of
    [[label-outlived-referent]] — a right number under a word that stopped being true. So: measure
    his actual footage, say the figure is measured, and fall back to the documented worst case
    while SAYING it is a worst case. Returns (gb_per_hour, n_reels) or (None, 0).
    """
    import glob
    best = []
    reels = sorted(glob.glob(os.path.join(HERE, "frames", "hist", "reel_*")),
                   key=lambda d: -os.stat(d).st_mtime)[:3]
    for d in reels:
        fr = glob.glob(os.path.join(d, "*.jpg"))
        if len(fr) < 40:
            continue                      # too few frames to time anything honestly
        try:
            st = [os.stat(q) for q in fr]
        except OSError:
            continue
        ts = sorted(x.st_mtime for x in st)
        mins = (ts[-1] - ts[0]) / 60.0
        if mins < 1.0:
            continue
        gb = sum(x.st_size for x in st) / float(1 << 30)
        best.append(gb * (60.0 / mins))
    if not best:
        return None, 0
    return sum(best) / len(best), len(best)


def _check_disk_headroom():
    """/api/on refuses below an 8GB floor. Finding that out when you press ON AIR is too late."""
    try:
        import shutil
        import disk_room as _dr   # #151 (REG-2742) - the doctor reads the figure /api/on refuses on
        free = _dr.free_bytes(HERE)[0] / 1e9
    except Exception as e:
        return UNKNOWN, "could not read disk usage: %s" % str(e)[:90]
    try:
        frames = subprocess.run([_spawnable("du"), "-sk", os.path.join(HERE, "frames")],
                                capture_output=True, text=True, encoding="utf-8", errors="replace", close_fds=False,
                                timeout=60)
        used = int(frames.stdout.split()[0]) / 1e6 if frames.stdout.strip() else None
    except Exception:
        used = None
    tail = (" · footage is %.1fGB" % used) if used is not None else ""
    if free < 8.0:
        return MISSING, ("%.1fGB free — BELOW the 8GB floor, so /api/on will refuse to record%s"
                         % (free, tail))
    rate, n = _measured_write_rate()
    if rate:
        rate_says = "your last %d reel(s) averaged %.1fGB/hour" % (n, rate)
    else:
        rate, rate_says = 9.0, "no reel was long enough to measure; using the 9GB/hour worst case"
    if free < 16.0:
        return MISSING, ("%.1fGB free — %s, so this is about %.1f hour(s) of recording%s"
                         % (free, rate_says, free / rate, tail))
    return OK, "%.1fGB free%s" % (free, tail)


#: REG-3208 - the growers lane rides the disk sign's 30-minute pass; a pass (or a wait) older than this is a stopped loop
GROWERS_STALE_S = 3 * 1800 + 600
#: REG-3208 review - a loop that only WAITS (his game, a busy machine) still moves checkedTs; a lane whose last MEASURING
#: pass is older than this is not measuring, and the sizes it last said are that old
GROWERS_UNMEASURED_H = 24


def _check_the_disk_growers_are_salvaged_then_pruned(status=None, now_ms=None, salvage_dir=None):
    """REG-3208 / REG-3209 - WHAT KEEPS GROWING ON THE DISK, AND WHAT WAITS ON A SALVAGE.

    His words 2026-11-05: "whatever keeps growing needs to have a looped system in place that prunes and extracts and
    saves any data informational that's needed". `disk headroom` above says how much is free; this row says WHAT is
    growing (the top growers of disk_growers' declared registry, by size), which link of measure -> salvage -> read
    back -> prune broke, and it corroborates the lane against the disk: a salvage the lane says it wrote must be on
    disk under the salvage dir. A console that is not answering, or a lane that never ran, is UNKNOWN, never OK.
    [[heart-first]] [[unknown-stays-unknown]]"""
    # REG-2202's lesson: /api/status can take 11.6 s cold, so this periodic row waits 15 s for it, not the 4 s default
    st = _get("/api/status", timeout=15) if status is None else status
    if not isinstance(st, dict):
        return UNKNOWN, "the console is not answering - what grows on the disk cannot be said"
    g = (st.get("diskSign") or {}).get("growers")
    if not isinstance(g, dict):
        return UNKNOWN, "this console publishes no growers lane - what grows on the disk is not measured here"
    say = str(g.get("say") or "")[:200]
    now = int(time.time() * 1000) if now_ms is None else int(now_ms)
    seen = g.get("checkedTs") if isinstance(g.get("checkedTs"), (int, float)) else g.get("lastTs")
    if not isinstance(seen, (int, float)) or isinstance(seen, bool):
        return UNKNOWN, "the growers lane has not run a pass yet - %s" % say
    if now - seen > GROWERS_STALE_S * 1000:
        return MISSING, ("the growers lane last looked %d min ago - its loop (the disk sign's 30-minute pass) is not "
                         "running, so nothing that grows is salvaged or pruned" % ((now - seen) // 60000))
    ran = g.get("lastTs")
    if not isinstance(ran, (int, float)) or isinstance(ran, bool):
        return UNKNOWN, "the growers lane has waited every pass and never measured yet - %s" % say
    age_m = max(0, (now - int(ran)) // 60000)
    if now - ran > GROWERS_UNMEASURED_H * 3600 * 1000:
        return MISSING, ("the growers lane has not MEASURED for %.0f h - every pass since waited (%s), so nothing that "
                         "grows was salvaged or pruned and the sizes it last said are that old" % (age_m / 60.0, say))
    if g.get("error"):
        return MISSING, "the growers lane's last pass raised %s - %s" % (g.get("error"), say)
    top = ", ".join("%s %.2f GB (%s, %d)" % (t.get("name"), t.get("gb") or 0, t.get("owner"), t.get("n") or 0)
                    for t in (g.get("top") or [])[:3]) or "nothing a declared entry names"
    top += " (measured %d min ago)" % age_m
    sw = (" - " + str(g.get("stateWhy"))[:160]) if g.get("stateWhy") else ""
    last = g.get("lastSalvage")
    if last:
        try:
            import disk_growers as _dg
            root = salvage_dir or _dg.salvage_root(os.path.dirname(HERE))
            if not os.path.isfile(os.path.join(root, str(last), "meta.json")):
                return MISSING, ("the growers lane says it salvaged %s, and that salvage is not on disk under %s - a "
                                 "prune that trusted it saved nothing" % (last, os.path.basename(root)))
        except Exception as e:
            return UNKNOWN, "the salvage dir could not be read (%s) - top growers: %s" % (type(e).__name__, top)
    wait = g.get("waiting") or []
    if wait:
        return MISSING, ("%d grower(s) wait on a salvage or a prune that did not finish: %s - each stays on disk "
                         "until its salvage is made and reads back. Top growers: %s%s" % (
                             len(wait), "; ".join("%s (%s)" % (w.get("name"), str(w.get("why"))[:70]) for w in wait[:3]),
                             top, sw))
    if g.get("owed") is None:
        return UNKNOWN, "top growers: %s - %s%s" % (top, say, sw)
    dry = g.get("dryRun") or []
    tail = (" - %d entr%s still dry-run (arms after %d clean passes)" % (
        len(dry), "y" if len(dry) == 1 else "ies", (dry[0] or {}).get("of") or 0)) if dry else ""
    return OK, "top growers: %s%s - %s%s" % (top, tail, say, sw)


def _check_subscription_burn():
    """Reads against the window. Not tokens — this lane bills none.

    REG-2389 — THE REFUSAL'S OPERANDS, NOT A HAND FILTER (control_app._meter_state learned it in v3099). This counted
    `now - c <= 3600` over the raw rows, and the ledger is shared with tv/intake_local.mjs, whose rows are MILLISECONDS:
    for those `now - c` is hugely negative, so every intake read still in the ledger - up to a day old - counted as a
    read "this hour". MEASURED on a fixture: 30 intake rows 5-20 h old and 2 vision reads in the last 10 min said
    "32 read(s) this hour", where the cap counts 2 - and since REG-2387 keeps those rows in milliseconds for a day, it
    would have said so all day. The rows are counted through tv._sub_budget_calls, the call _sub_budget_check counts."""
    try:
        import tv_diablo as tv
        path = getattr(tv, "_SUB_BUDGET_PATH", "")
        hourly = int(getattr(tv, "_SUB_HOURLY_MAX", 0) or 0)
        daily = int(getattr(tv, "_SUB_DAILY_MAX", 0) or 0)
    except Exception as e:
        return UNKNOWN, "tv_diablo will not import: %s" % str(e)[:90]
    if not path or not os.path.isfile(path):
        return UNKNOWN, "no vision read has been recorded on this machine yet"
    now = time.time()
    try:
        with open(path, encoding="utf-8") as fh:
            calls = tv._sub_budget_calls(json.load(fh) or {}, now)
    except Exception as e:
        return UNKNOWN, "budget file unreadable: %s" % str(e)[:90]
    hour = sum(1 for c in calls if now - c < 3600)
    day = len(calls)
    pct = (100.0 * hour / hourly) if hourly else 0.0
    if hourly and pct >= 85:
        return MISSING, ("%d reads this hour of %d (%.0f%%) — close to the cap; a sweep started now "
                         "may be cut off" % (hour, hourly, pct))
    return OK, "%d read(s) this hour of %d · %d today of %d — subscription, no API tokens" % (
        hour, hourly, day, daily)


def _check_his_reader_switch_can_read():
    """#151 - HIS SWITCH (CLAUDE · + GROK · GROK ONLY) and whether the reader it names can read on this PC.

    At GROK ONLY nothing falls back to Claude - his rule, "no claude as a secondary at all" - so a Grok that cannot
    read here means frames wait unread. That has to reach him as a row the heart carries, not only as a line on the
    EYES card he may never open. [[heart-first]] [[unknown-stays-unknown]]"""
    try:
        import g5_grok_eyes as g5
    except Exception as e:
        return UNKNOWN, "the Grok module will not import (%s) - which reader is on cannot be said" % type(e).__name__
    try:
        who = g5.reader()
    except Exception as e:
        return UNKNOWN, "the reader switch could not be read (%s)" % type(e).__name__
    label = {"claude": "CLAUDE", "both": "+ GROK", "grok": "GROK ONLY"}.get(who, str(who))
    rule = g5.READER_RULES.get(who, "")
    if who != "grok":
        return OK, "EYES at %s - %s" % (label, rule)
    try:
        why = g5.grok_only_blocked_why()
    except Exception as e:
        return UNKNOWN, "GROK ONLY is on and Grok's readiness could not be read (%s)" % type(e).__name__
    if why:
        return MISSING, why
    return OK, "EYES at GROK ONLY - %s" % rule


def _check_a_reel_is_not_recording_unattended():
    """v2019's class. A reel that outlives the thing that started it burns ~9GB/hour in silence."""
    sh = _get("/api/shadow")
    if sh is None:
        return UNKNOWN, "the console is not answering — cannot say whether a reel is rolling"
    rec = bool(sh.get("recording"))
    on = bool(sh.get("on"))
    if rec and not on:
        return MISSING, ("a reel IS RECORDING while the shadow reader is OFF — nothing is reading "
                         "what it films. Seal it from ON AIR, or switch the reader on")
    if rec:
        return OK, "a reel is rolling and the reader is watching it"
    return OK, "nothing is recording"


def _check_the_sweep_would_find_something():
    """REG-384's class, and the one no lane can see: a sweep that spends its budget on footage
    with nothing in it. This is FREE — the panel gate is a crop and an OCR, no model call."""
    try:
        import chronicle_retro as cr
        import vault_retro as vr
        import control_app as ca
    except Exception as e:
        return UNKNOWN, "could not import the sweep modules: %s" % str(e)[:90]
    hist = os.path.join(HERE, "frames", "hist")
    if not os.path.isdir(hist):
        return UNKNOWN, "no frames/hist on this machine"
    try:
        dirs = cr.reel_dirs(hist)
    except Exception as e:
        return UNKNOWN, "could not list reels: %s" % str(e)[:90]
    if not dirs:
        return MISSING, "no reels on disk — record one: open TV DIABLO and press ON AIR"
    # ⚠ v3297 — THE INSTRUMENT, NOT THE FOOTAGE. stash_screen_open returns None when its
    # imports break, and panel_density returns 0.0 for an unreadable reel — so a dead OCR
    # toolchain and a shelf with no stash panels used to print the IDENTICAL sentence.
    # gate_failures() is the truth channel built for exactly this (v1854: "310 versions of every
    # caller reading None as an answer about his footage when it was really an answer about a
    # NameError") and this verdict was never joined to it. Snapshot it around the density pass:
    # a zero taken while the gate was failing is an answer about the INSTRUMENT and must say so.
    # [[unknown-stays-unknown]] [[the-unjoined-end]]
    # ⚠⚠ v3304 (#55) — THIS THREAD'S TALLY, NOT THE PROCESS'S. v3297 (mine) took this delta from
    # the PROCESS counter, so a chronicle or vault sweep breaking a frame on another thread during
    # the density pass was charged to the density pass — and this check then answered UNKNOWN
    # ("the instrument failed") over a footage answer that was perfectly measured, suppressing the
    # very MISSING it exists to raise. gate_failures_here() is thread-local, so only a failure this
    # pass actually caused can convict it. [[unknown-stays-unknown]]
    try:
        _gb0 = int(ca.gate_failures_here())
    except Exception:
        _gb0 = None
    try:
        dens = {d: vr.panel_density(d, ca.stash_screen_open_cached) for d in dirs}
    except Exception as e:
        return UNKNOWN, "the panel gate would not run: %s" % str(e)[:90]
    try:
        _gb = (int(ca.gate_failures_here()) - _gb0) if _gb0 is not None else None
    except Exception:
        _gb = None
    withpanel = [d for d, v in dens.items() if v > 0]
    if not withpanel and _gb:
        return UNKNOWN, ("the stash gate FAILED %d time(s) during the density pass — this zero "
                         "is an answer about the INSTRUMENT, not the footage; no reel was judged"
                         % _gb)
    if not withpanel:
        return MISSING, ("%d reel(s) on disk and NONE shows a stash panel — a vault sweep would "
                         "read nothing. Open the stash (and hover items) while a reel is rolling"
                         % len(dirs))
    # v3171 — ONE RANKER, TWO CALLERS. This used to sort inline while _vault_sweep_run picked
    # reels in directory order; the console then held two answers to "which reel next", and the
    # sweeper's answer was the wrong one. Both now call vault_retro.rank_by_panel. [[copy-drift]]
    best = vr.rank_by_panel(list(dens.keys()), ca.stash_screen_open_cached)[:3] \
        if hasattr(vr, "rank_by_panel") else sorted(dens.items(), key=lambda kv: -kv[1])[:3]
    return OK, ("%d of %d reel(s) show a stash panel; a sweep would start with %s"
                % (len(withpanel), len(dirs),
                   ", ".join("%s (%.0f%%)" % (os.path.basename(d), 100 * v) for d, v in best)))


def _check_the_stash_bank():
    """Is the stash-side bank being FED? -> (state, line)

    HIS ORDER, 2026-09-15: *"all information that can be extracted should be backend tallied
    regardless of the ledger... the backend that approves and routes it eventuall to the front
    end"* — and it exists, starved. MEASURED: the chronicle bank holds 324 uniques / 8517
    sightings / 262 refusals; the stash bank held TWELVE keys, because the sweeper read reels in
    directory order and never reached the ten that show a stash panel. v3171 joined the ranker.

    ⚠ ONE READER. This asks vault_bank.state() rather than re-deriving the counts, so the doctor,
    the heart, the watchdog and the eagle cannot drift into four answers. [[copy-drift]]
    """
    try:
        import vault_bank as _vb
    except Exception as exc:
        return UNKNOWN, ("vault_bank would not import (%s), so whether the stash bank is fed is "
                         "UNKNOWN" % type(exc).__name__)
    try:
        word, line = _vb.headline()
        st = _vb.state()
    except Exception as exc:
        return UNKNOWN, "the stash bank would not answer (%s) - UNKNOWN, not clean" % type(exc).__name__
    tail = ("  (the chronicle bank next door holds %s sighting(s) over %s name(s) - that is the "
            "shape this one should grow into)" % (st.get("chronSightings"), st.get("chronUniques")))
    if word == "OK":
        return OK, line + tail
    if word == "WARN":
        return MISSING, line + tail
    return UNKNOWN, line


def _check_the_other_doctors(_run=None):
    """Call them, never re-implement them. [[copy-drift]]

    #86 gap audit 24 (REG-1726) — A DOCTOR THAT SAID NOTHING IS NOT A CLEAN REPORT. The count of its marks was the
    whole verdict, so a sub-doctor that crashed (a traceback, no marks) read "0 green / 0 needs-you" and the row was
    OK. Zero marks is now "it gave no verdict", with its exit code, and that is UNKNOWN. `_run` is a law's seam."""
    _run = _run or subprocess.run
    out = []
    for mod, label in (("vault_doctor", "vault"), ("chronicle_doctor", "chronicle")):
        try:
            r = _run([sys.executable, os.path.join(HERE, mod + ".py")],
                     capture_output=True, text=True, encoding="utf-8", errors="replace", close_fds=False,
                     timeout=600)
            txt = (r.stdout or "") + (r.stderr or "")
            bad = txt.count("🟠") + txt.count("🔴")
            good = txt.count("🟢")
            if not (good or bad):
                out.append((label, None, "it exited %s and gave no verdict" % getattr(r, "returncode", "?")))
                continue
            out.append((label, good, bad))
        except Exception as e:
            out.append((label, None, str(e)[:60]))
    parts = []
    worst = OK
    for label, good, bad in out:
        if good is None:
            parts.append("%s doctor would not run (%s)" % (label, bad))
            worst = UNKNOWN if worst == OK else worst
        else:
            parts.append("%s %d green / %d needs-you" % (label, good, bad))
            if bad:
                worst = MISSING
    return worst, " · ".join(parts) + "  (run them for the detail)"


# ── v2078 — EVERYTHING THE NIGHT OF 2026-08-24 BUILT, WATCHED FROM ABOVE ─────────────────────
# Konyo: "put it all under eagle eye and watchdog so if something within the console is out of
# sync it can catch it."
#
# Each check below exists because a REAL defect of that exact shape shipped and HE found it. None
# of them tests code — they test whether the RUNNING SYSTEM still agrees with itself, which is the
# one thing no unit test and no gate can see.
#
# Every one errs the same way: what it cannot measure is UNKNOWN, never OK. A watchdog that reports
# "fine" because it could not look is the defect it was built to catch.


def _check_the_visual_lock_holds():
    """The board's meaning-bearing CSS — weight, structure, rarity COLOUR, the sealed title, and
    every Sessions card owning a grid area. He found all of those by eye first."""
    import subprocess
    lock = os.path.join(os.path.dirname(HERE), "visual_lock_invariant.py")
    if not os.path.isfile(lock):
        return UNKNOWN, "visual_lock_invariant.py is not on this machine, so nothing is pinning the board's type or colour"
    try:
        p = subprocess.run([sys.executable, lock], capture_output=True, text=True, encoding="utf-8", errors="replace",
                           close_fds=False, timeout=90)
    except Exception as e:
        return UNKNOWN, "the visual lock could not run (%s) — that is unmeasured, not clean" % str(e)[:70]
    if p.returncode == 0:
        return OK, "weight, structure, rarity colour and the sealed title all still pinned"
    bad = [l.strip(" \u2022") for l in (p.stdout or "").split("\n") if l.strip().startswith("\u2022")]
    return MISSING, ("the board's visual lock has DRIFTED: %s"
                     % ("; ".join(bad)[:230] or "see visual_lock_invariant.py"))


def _check_every_reel_can_date_itself():
    """Can every reel on disk still yield a clock from its own id? -> (state, why)

    v3333 (#80) — THE PRECONDITION THE CARD FIX RESTS ON, WATCHED RATHER THAN ASSUMED.
    MEASURED on his console: 2 of 422 sessions carry no `t0` at all (n=30, 753 frames; n=50, 10
    frames), so the card had a session and no clock and rendered an em-dash where a date belongs.
    The fix falls back to the epoch ms embedded in the id — `s_<ms>_<n>` — which is sound because
    on all 12 sessions checked where BOTH exist the two agree to the minute.

    ⚠ THE GATE PINS THE CODE; THIS ASKS WHETHER THE DATA STILL SATISFIES IT. If reels ever start
    being named differently, the fallback stops working SILENTLY: no test changes, no error, and
    a card quietly loses its date again. A guard that only reads source cannot see that.

    ⚠ mtime IS NOT AN ALTERNATIVE and that is measured, not assumed: all 19 reels on disk carry an
    mtime from a single bulk pass on 16 Sep 18:10-20:14, skews of 1.8 to 53.1 days. It reports two
    months of footage as simultaneous, so a clock taken from it cannot order anything.
    [[stale-reading]] [[unknown-stays-unknown]]
    """
    import glob
    import re as _re
    hist = os.path.join(HERE, "frames", "hist")
    if not os.path.isdir(hist):
        return UNKNOWN, ("there is no frames/hist on this machine, so whether a reel can date "
                         "itself is unmeasured here - not clean")
    reels = [os.path.basename(p) for p in glob.glob(os.path.join(hist, "reel_s_*"))]
    if not reels:
        return UNKNOWN, ("frames/hist holds no reels, so the id-clock has nothing to be measured "
                         "against. A zero here is an empty room, not a clean one")
    rx = _re.compile(r"^reel_s_(\d{10,})_")
    mute = [r for r in reels if not rx.match(r)]
    if mute:
        return MISSING, ("%d of %d reel(s) cannot yield a clock from their id (%s) - a card for "
                         "one of these has no date to fall back on and renders an em-dash where "
                         "a time belongs"
                         % (len(mute), len(reels), ", ".join(sorted(mute)[:3])))
    return OK, ("all %d reel(s) carry a parseable epoch in their id, so every card can date "
                "itself even when its session lost t0" % len(reels))


def _check_the_art_corpus():
    """1,233 sprites the board draws. A prune, a bad sync or a rename takes them with nothing
    failing — the page just starts drawing placeholders where it drew items."""
    import glob
    art = os.path.join(os.path.dirname(HERE), "art")
    if not os.path.isdir(art):
        return UNKNOWN, "the art directory is not on this machine"
    n = len(glob.glob(os.path.join(art, "*.png")))
    gems = [g for g in ("amethyst", "ruby", "emerald", "saphire")
            if not glob.glob(os.path.join(art, "hd_perfect_%s*.png" % g))]
    if gems:
        return MISSING, ("%d sprite(s) on disk but the craft gems %s are GONE — every craft card "
                         "silently reverts to one alembic emoji" % (n, ", ".join(gems)))
    if n < 1233:
        return MISSING, ("the art corpus is %d files, down from 1233 — the board will draw "
                         "placeholders where it used to draw items" % n)
    return OK, "%d sprite(s), and the four craft gems are all present" % n


def _check_footage_belongs_to_a_reel():
    """A session that dies before it SEALS leaves its frames loose in hist/, where no lane and no
    deleter can see them — 3.15 GB of his footage was invisible that way."""
    try:
        sys.path.insert(0, HERE)
        import frame_authority as fa
    except Exception as e:
        return UNKNOWN, "frame_authority did not import (%s)" % str(e)[:70]
    hist = os.environ.get("TV_HIST") or os.path.join(HERE, "frames", "hist")
    if not os.path.isdir(hist):
        return UNKNOWN, "no frames/hist on this machine"
    try:
        lf = fa.loose_frames(hist)
    except Exception as e:
        return UNKNOWN, "could not read the loose frames (%s)" % str(e)[:70]
    if not lf.get("ok"):
        return UNKNOWN, lf.get("say") or "the loose-frame scan could not answer"
    rec = len(lf.get("recording") or [])
    if rec:
        return MISSING, ("%d frame(s) (%.2f GB) belong to NO reel — an unsealed recording no sweep "
                         "can reach. `python3 tv/orphan_fold.py` shows the plan."
                         % (rec, (lf.get("recordingBytes") or 0) / 1e9))
    return OK, "every recording frame belongs to a reel"


def _check_the_evidence_ledger_is_readable():
    """v2730 — 310 NAMES OF TESTIMONY AND NOTHING WAS LOOKING AT THEM.

    Konyo: *"the join the heart of the console connect and wire whatever is needed so its all not
    in the dark"*. `chron_evidence.json` is what makes cross-reel corroboration possible — its own
    writer says so — and no Doctor row, no invariant and no census entry mentioned it.

    ⚠ AN UNREADABLE LEDGER MUST NEVER READ AS AN EMPTY ONE. v1779 recorded the real event: one
    torn read returned {}, the merge saved {} as the whole accumulated ledger, and every sighting
    ever collected was gone with nothing on any screen to say so.
    ⚠ AND THE TELL IS INTERNAL: `pagesRead` counts pages the reader got through. Pages banked with
    ZERO names left is not a quiet day — it is the signature of a ledger that was emptied after
    the reading happened. That comparison is free and it is the one this row exists to make.
    """
    import json as _j
    fp = os.path.join(HERE, "chron_evidence.json")
    if not os.path.exists(fp):
        return UNKNOWN, ("chron_evidence.json has never been written — there is no testimony to "
                         "lose yet, which is different from having lost it")
    try:
        with open(fp, encoding="utf-8") as fh:
            ev = _j.load(fh)
    except Exception as e:
        return MISSING, ("chron_evidence.json will not parse (%s) — every sighting ever banked is "
                         "INCOMPLETE, not empty, and nothing downstream may treat it as zero"
                         % str(e)[:60])
    if not isinstance(ev, dict):
        return MISSING, ("chron_evidence.json is a %s, not an object — the ledger's shape is gone"
                         % type(ev).__name__)
    n_u = len(ev.get("uniques") or {})
    n_s = len(ev.get("sets") or {})
    pages = ev.get("pagesRead")
    if (n_u + n_s) == 0 and isinstance(pages, int) and pages > 0:
        return MISSING, ("%d page(s) were read and banked, and the ledger now holds ZERO names — "
                         "that is the v1779 shape: a ledger emptied after the reading happened"
                         % pages)
    return OK, ("%d unique(s) and %d set(s) carry testimony across %s page(s) read"
                % (n_u, n_s, pages if pages is not None else "an unrecorded number of"))


def _check_the_ledger_backup_covers_every_store():
    """v2730 — THE AUTOMATIC BACKUP HAS NEVER CAPTURED TWO OF HIS SIX LEDGERS.

    MEASURED on his 60 real backup files, 2026-09-06: every one carries foundLog (419), owned (169)
    and setPieces (123) — and NOT `rwMade` (his 99 runewords) or `gameFound` (29). No file records
    which PROFILE it came from either.

    ⚠⚠ AND IT BLINDS A WATCHER. tv/ledger_highwater.py ratchets
    KEYS = (foundLog, setPieces, rwMade, owned) against each key's historic max — but since no
    snapshot has ever carried `rwMade`, that column can only read UNKNOWN, forever, and an UNKNOWN
    column looks exactly like a column with nothing wrong. A backup that runs every ten minutes and
    writes a plausible file is the most convincing kind of gap there is.
    [[unknown-stays-unknown]] [[the-unjoined-end]]
    """
    import json as _j, glob as _g
    d = os.path.expanduser("~/d2r_ledger_backups")
    if not os.path.isdir(d):
        return UNKNOWN, "no ledger-backup directory yet — nothing has been snapshotted"
    files = sorted(_g.glob(os.path.join(d, "ledger_*.json")), key=os.path.getmtime, reverse=True)
    if not files:
        return UNKNOWN, "the backup directory is empty — no snapshot has ever been written"
    try:
        with open(files[0], encoding="utf-8") as fh:
            b = _j.load(fh)
    except Exception as e:
        return MISSING, ("the newest ledger backup will not parse (%s) — the copy of his ledgers "
                         "cannot be trusted" % str(e)[:50])
    led = (b.get("ledger") or {}) if isinstance(b, dict) else {}
    WANT = ("foundLog", "owned", "setPieces", "rwMade", "gameFound")
    missing = [k for k in WANT if k not in led]
    routed = any(k in (b or {}) for k in ("route", "profile", "who", "machine"))
    if missing:
        return MISSING, ("the newest backup carries %d of %d ledgers — MISSING %s. Those stores "
                         "have no automatic copy at all, and ledger_highwater ratchets rwMade "
                         "against snapshots that never contain it."
                         % (len(WANT) - len(missing), len(WANT), ", ".join(missing)))
    if not routed:
        return MISSING, ("the newest backup records no route/profile, so nothing says WHOSE "
                         "ledgers it holds and a restore cannot tell one profile from another")
    return OK, ("the newest backup carries all %d ledgers and names its profile (%d file(s) kept)"
                % (len(WANT), len(files)))


#: What the backup loop is allowed to have done last. Anything else is a REFUSAL, and a refusal
#: repeating every ten minutes is an outage. ⚠ Kept as a closed allowlist rather than a list of
#: known error strings: an unrecognised message must read as a failure, never as "probably fine".
_BACKUP_BENIGN = ("wrote ", "unchanged since")


def _check_this_versions_ci(rec=None, now=None):
    """REG-3213 - THIS VERSION'S CI, RED PAST 75 MINUTES. His words (2026-11-05): "why has it been stuck for so long and
    not triggered at an alert somewhere at 75 minutes which was max?" - on v3864 shard 10 of ci/proof-keys-v3864 ran 87 min
    (the run 2 h 10 min, then Publish 56 min more) and no row, no script, nothing said so. The console's CI tick
    (control_app._ci_watch_tick) reads GitHub's public Actions API for the
    commit it runs, every 5 minutes; this row reads what it recorded (status.ciWatch, the serving console's _CI_WATCH):
      overrun / slow / red  -> MISSING, naming the runs past the max and the jobs still running
      unknown, never read, or a reading older than 3 ticks -> UNKNOWN (an unread GitHub is never green)
      running inside the max, none, green -> OK, with the minutes"""
    if rec is None:
        try:
            import control_app as _ca
            rec = dict(getattr(_serving_console(_ca), "_CI_WATCH", None) or {})
        except Exception as e:
            return UNKNOWN, "the console's CI watch could not be read (%s) - this version's CI is UNMEASURED" % type(e).__name__
    now = time.time() if now is None else now
    try:
        import ci_watch as _cw
        every, red = _cw.CI_WATCH_EVERY_S, _cw.RED_STATES
    except Exception:
        every, red = 300, ("overrun", "slow", "red")
    ts = rec.get("lastTs")
    if not isinstance(ts, (int, float)) or isinstance(ts, bool):
        return UNKNOWN, "the console has not read this version's CI yet (%s)" % (rec.get("why") or "no reading")
    age = now - ts / 1000.0
    st = rec.get("state")
    if st in red:
        return MISSING, "this version's CI: %s" % (rec.get("why") or st)
    if age > 3 * every + 60:
        return UNKNOWN, ("the last reading of this version's CI is %d min old - the watch stopped reading, so it is "
                         "UNKNOWN, not green" % int(age // 60))
    if rec.get("worked") is not True or st in (None, "unknown"):
        return UNKNOWN, "this version's CI: %s" % (rec.get("why") or "UNKNOWN")
    return OK, "this version's CI: %s" % (rec.get("why") or st)


def _check_the_backup_loop_is_actually_WRITING():
    """v2735 — THE BACKUP LOOP REFUSED EVERY SNAPSHOT FOR A DAY AND NOTHING ASKED.

    Konyo, on being shown the restore wire: *"and all connected to the heart of the console
    obviously right? is it needed?"* — this check is the answer, and it went RED the moment it
    existed.

    MEASURED on his live console, 2026-09-06 18:15:

        ledgerBackup.writes   0
        ledgerBackup.why      "Can't find variable: dump"
        newest backup file    80 minutes old, still the pre-v2731 three-store shape

    v2731 added `rwMadeFull:(dump?rwFull:null)` to the board read. No such JS variable exists —
    `dump_stores` is interpolated as a bare true/false LITERAL — so the entire read threw and every
    snapshot was refused from that ship onward.

    ⚠⚠ EVERY GATE WAS GREEN THROUGHOUT, and correctly:
    `test_ledger_backup_covers_every_store` grades the SOURCE, and source is not a running board.
    The refusal existed in exactly one place — a string in `_LEDGER_BACKUP_STATE["why"]`, published
    at `/api/status.ledgerBackup` and read by NOBODY. A loop that fails silently every ten minutes
    is indistinguishable from a loop with nothing to do, and the newest file it left behind looks
    like a healthy backup right up until the day it is needed.
    [[the-unjoined-end]] [[feedback-verify-not-proxy]] [[zero-needs-a-denominator]]

    THE LAW: the last thing the loop did must be a write or a benign skip. Not "no exception was
    raised" — the loop swallows everything by design so one bad read cannot end it.
    """
    # ⚠ 15s, NOT the 4s default. MEASURED: /api/status takes 11.6s COLD and 0.26s warm — it folds
    # a fleet read and a drift check. At the default this check reported "the console is not
    # answering" against a console that was answering fine, which is a false UNKNOWN blaming the
    # wrong thing, and it is how a real red would get dismissed as flakiness. [[stale-reading]]
    st = _get("/api/status", timeout=15)
    if not isinstance(st, dict) or not st.get("ok"):
        return UNKNOWN, ("the console did not answer /api/status within 15s, so what the backup "
                         "loop last did is UNMEASURED — which is not the same as healthy")
    lb = st.get("ledgerBackup")
    if not isinstance(lb, dict):
        return MISSING, ("/api/status no longer publishes `ledgerBackup`, so the only place the "
                         "backup loop's refusals are visible is gone and this check is blind")
    why = str(lb.get("why") or "")
    writes = lb.get("writes")
    if writes is None:
        return UNKNOWN, "the backup state reports no write count, so nothing can be concluded"
    if not why:
        # ⚠ A GENUINE UNKNOWN, NOT A PASS. The first snapshot comes 45s after boot; before that the
        # loop has done nothing and has nothing to report. Grading that as OK would make a
        # freshly-restarted console always look healthy — the one moment it is least proven.
        return UNKNOWN, ("the loop has not reported a snapshot yet (%d write(s) so far) — too early "
                         "to say, and that is not the same as working" % int(writes or 0))
    # ⚠⚠ v2736 — `why` IS STICKY, AND WITHOUT THIS THE WHOLE CHECK WAS DEFEATED BY A DEAD LOOP.
    # REPRODUCED: a loop that wrote once and then stopped three days ago left
    # why="wrote ledger_2026-09-03_010101.json" in place, and this row graded it **OK**. Nothing
    # clears the string, and the loop swallows every exception by design so one bad read cannot
    # end it — so the last benign message outlives the loop that wrote it.
    # Found by handing the shipped diff to a different model family and asking it to refute.
    # ⚠ THIS IS [[stale-reading]] COMMITTED INSIDE THE WATCHER BUILT TO CATCH A SILENT FAILURE:
    # the age of the THING, not the age of the fetch. The message was fresh; the act was not.
    try:
        age_ms = lb.get("lastTryMs")
        if age_ms is None:
            return UNKNOWN, ("the loop publishes no last-attempt time, so whether it is still "
                             "running is UNMEASURED — a sticky `why` cannot answer it")
        age_s = max(0.0, time.time() - (float(age_ms) / 1000.0))
    except (TypeError, ValueError):
        return UNKNOWN, "the loop's last-attempt time is unreadable, so its liveness is UNKNOWN"
    # three intervals: one missed tick is scheduling noise, three is a loop that is gone
    if age_s > 3 * 600:
        return MISSING, ("the backup loop has not RUN for %d minute(s) — it fires every 10, so it "
                         "is not running at all. Its last message is %r, which is sticky and says "
                         "nothing about whether the loop still exists."
                         % (int(age_s / 60), why[:60]))
    if not why.startswith(_BACKUP_BENIGN):
        return MISSING, ("the backup loop is REFUSING every snapshot: %r. It has written %d file(s) "
                         "this run, and it retries every %d minutes, so this repeats silently. His "
                         "ledgers have no fresh automatic copy while this stands."
                         % (why[:90], int(writes or 0), 10))
    return OK, ("the loop's last act was %r after %d write(s) this run"
                % (why[:60], int(writes or 0)))


#: A backup the watcher has not judged is "stopped" only past this age. The loop writes the file and
#: judges it in the same breath, so a few seconds of lag is a race, not an outage.
_DROP_JUDGE_GRACE_S = 300.0


def _check_no_ledger_store_dropped_unseen(bdir=None, drops_path=None, now=None):
    """2026-09-27 — A STORE FELL TO ZERO AND NOTHING SAID SO.

    MEASURED on his real backups (shape only): ledger_..._024127 held setPieces 134 / owned 223, the
    033127 file held 0 / 0 — a vault reset — and every backup after it held 0. Three rows could have
    seen it and none did: `ledger entries` compares only the TWO NEWEST snapshots, so one snapshot
    after the drop it went clean with the pieces still gone; `store emptied` reads a flag the board
    writes only when the FOUND ledger comes up empty at load; and the restore door took the NEWEST
    backup, which held nothing to put back. The 02:41 file survived because the prune had not
    reached it — luck, not policy.

    This row reads the backup loop's own DURABLE drop record (`_ledger_drop_watch`), which opens an
    episode on a drop and closes it only when the store is back to >= where it fell from. So an
    open drop stays red across any number of later snapshots — a peak, not a pairwise diff.

    ⚠ UNKNOWN, never clean: no readable backup dir, no record yet (the watcher never ran), or a
    record that will not parse. And the watcher is watched: a newest backup it never judged means
    it has stopped, and a drop since then would be unseen. [[heart-first]] [[unknown-stays-unknown]]
    """
    now = time.time() if now is None else now
    try:
        import control_app as _ca
        bdir = bdir or _ca._LEDGER_BACKUP_DIR
        drops_path = drops_path or _ca._ledger_drops_path()
        _load = _ca.ledger_drops_load
        import ledger_restore as _LR      # REG-1481 — which stores are hand-made, and their door
    except Exception as e:
        return UNKNOWN, ("the console's drop watcher will not import (%s), so whether a ledger "
                         "store dropped is UNKNOWN" % str(e)[:60])
    try:
        names = sorted(n for n in os.listdir(bdir) if n.startswith("ledger_") and n.endswith(".json"))
    except Exception as e:
        return UNKNOWN, ("the ledger-backup directory cannot be read (%s), so a drop would be "
                         "invisible — UNKNOWN, not clean" % type(e).__name__)
    if not names:
        return UNKNOWN, "no ledger backup is on disk, so there is nothing a drop could be measured in"
    doc, why = _load(drops_path)
    if doc is None:
        return UNKNOWN, ("%s, so which stores dropped is UNKNOWN. The next snapshot sets it aside "
                         "and rebuilds it from the backups themselves" % why)
    if why == "absent":
        return UNKNOWN, ("the drop watcher has never written its record (%d backup(s) on disk), so "
                         "whether a store dropped is UNMEASURED — not clean" % len(names))
    episodes = [e for e in doc.get("episodes") or [] if isinstance(e, dict)]
    open_eps = [e for e in episodes if e.get("open")]

    # the watchdog on the watcher: the newest backup must have been judged
    stopped = ""
    judged = [str(v) for v in (doc.get("lastJudged") or {}).values() if v]
    newest = names[-1]
    if newest not in judged and newest > max(judged or [""]):
        try:
            age_s = now - os.path.getmtime(os.path.join(bdir, newest))
        except Exception:
            age_s = None
        if age_s is None or age_s > _DROP_JUDGE_GRACE_S:
            stopped = ("the drop watcher has NOT judged the newest backup %s (%s; last judged %s) "
                       "— it has stopped, so a drop since then is UNSEEN"
                       % (newest, ("%d min old" % int(age_s / 60)) if age_s is not None
                          else "age unreadable", max(judged) if judged else "nothing"))

    if open_eps:
        def _when(e):
            try:
                return time.strftime("%Y-%m-%d %H:%M", time.localtime(float(e.get("at")) / 1000.0))
            except Exception:
                return "in %s" % e.get("afterFile")
        open_eps.sort(key=lambda e: (str(e.get("afterFile")), str(e.get("store"))))
        parts = ["%s fell %s -> %s at %s (last backup before it: %s)"
                 % (e.get("store"), e.get("from"), e.get("to"), _when(e), e.get("beforeFile"))
                 for e in open_eps]
        via_chronicle = sorted(set(str(e.get("store")) for e in open_eps
                                   if e.get("store") in ("foundLog", "setPieces")))
        owned = any(e.get("store") == "owned" for e in open_eps)
        # the second eye on v3521: an rwMade-only (or owned-only) drop still LED with the chronicle door and its
        # "take every store from that one file" - a door that puts back none of what fell. The chronicle plan is
        # named only when a dropped store actually goes through it; a store with its own door leads with that door.
        _own_doors = ("owned", "rwMade", "gameFound")
        # REG-1481 — a hand-made store (his builds, his placements) has no API door at all; the FILE is
        # the door, and sending him to the chronicle plan for it would put back none of what fell.
        _hand = [e for e in open_eps if e.get("store") in _LR.HAND_MADE]
        _via_plan = [e for e in open_eps if e.get("store") not in _own_doors and e.get("store") not in _LR.HAND_MADE]
        doors = []
        for _e in _hand:
            doors.append("RESTORE %s by hand: %s — the file is %s"
                         % (_e.get("store"), _LR.HAND_MADE_DOOR.get(_e.get("store"), "no door is declared for it"),
                            _e.get("beforeFile")))
        if _via_plan:
            # the second eye on v3519 (11c3e2f5): a named file wins OUTRIGHT in ledger_restore.plan - every store comes
            # from it and the per-store choice (_sources_after_drops) never runs. Offering the FIRST episode's
            # beforeFile when two stores fell against different backups told him to put the later store back from an
            # older snapshot, losing what it gained in between. One file is offered only when there IS one file.
            _bfs = sorted(set(str(e.get("beforeFile")) for e in _via_plan))
            if len(_bfs) == 1:
                _file_hint = "(add \"file\": \"%s\" to take every store from that one file)" % _bfs[0]
            else:
                _file_hint = ("(the drops fell against %d different backups - %s - so do NOT add \"file\": one file "
                              "would put a later store back from an older snapshot)" % (len(_bfs), ", ".join(_bfs)))
            doors.append("RESTORE: POST /api/ledger_restore_plan to see it, then /api/ledger_restore_apply "
                         "{\"confirm\": true} — the plan reads %s from the last backup BEFORE each drop %s"
                         % (", ".join(via_chronicle) or ", ".join(sorted(set(str(e.get("store")) for e in _via_plan))),
                            _file_hint))
        if owned:
            doors.append(("owned is a possession record and is NOT put back by that door — "
                          if _via_plan else "RESTORE owned (a possession record): ")
                         + "/api/owned_restore is its own, confirm required")
        # the second eye on v3520 (read against ledger_restore.RESTORABLE): runewords are BACKED_UP_ONLY - the
        # chronicle door never carries them, so sending him there for an rwMade drop restores nothing
        if any(e.get("store") == "rwMade" for e in open_eps):
            doors.append(("rwMade (runewords made) is NOT put back by that door either — "
                          if _via_plan else "RESTORE rwMade (runewords made): ")
                         + "/api/rw_restore is its own, confirm required")
        door = "; ".join(doors) if doors else "no restore door carries the store(s) that fell"
        door += (". A deliberate clear is not a loss to undo: POST /api/ledger_drop_accept "
                 "{\"store\": %r, \"reason\": \"why\", \"confirm\": true}"
                 % open_eps[0].get("store"))
        if any(e.get("store") == "gameFound" for e in open_eps):
            door += "; gameFound has NO restore door yet — it is backed up, not restorable"
        return MISSING, ("A LEDGER STORE DROPPED and has not come back: %s. %s. Nothing is put back "
                         "on its own; the backup it needs is kept from the prune while the drop is "
                         "open.%s" % ("; ".join(parts), door, (" ⚠ " + stopped) if stopped else ""))
    if stopped:
        return MISSING, stopped
    n_closed = len(episodes) - len(open_eps)
    return OK, ("no ledger store has an open drop — %d drop(s) on record, all back to where they "
                "fell from; the newest backup %s was judged" % (n_closed, newest))


#: Stations that owe something NO automatic lane can deliver, and why each is by design rather than
#: a gap. ⚠ Without this split the row cries wolf on 40 of 40 and gets ignored — and a distrusted
#: instrument is a switched-off instrument, which is how the defects below survived in the first place.
_BY_DESIGN_STATIONS = {
    "JOIN": "sealed AND the names are on disk; the seal does not carry them — that is a CODE change",
    # ⚠ v3020 — NOT REG-340. That rules the CHARACTER name; these reels lack ITEM names, and an
    # item's name is only ever in its tooltip. The capture that helps is HOVER, not the C panel.
    "CAPTURE": "the capture itself must change — HOVER coverage so the tooltips that carry item "
               "names are filmed — not the lane that reads it",
}


def _grail_of(names):
    """-> how many of `names` resolve to one of his rosters, or None if none can be read.

    ⚠ None, never 0. "No roster on this machine" and "no name matched" are different answers and
    a 0 here would understate the lane instead of admitting it could not look.
    [[unknown-stays-unknown]]
    """
    import json as _j
    import os as _o
    table = {}
    for _f, _keys in (("unique_roster.json", ("names",)),
                      ("runeword_roster.json", ("names",)),
                      ("set_roster.json", ("pieces", "sets"))):
        _p = _o.path.join(HERE, _f)
        if not _o.path.isfile(_p):
            continue
        try:
            with open(_p, "rb") as _fh:
                _d = _j.loads(_fh.read().decode("utf-8", "replace"))
        except Exception:
            continue
        # ⚠ set_roster keys its data as `pieces`/`sets`, NOT `names`. Asking the wrong key returns
        # None and silently resolves ZERO set items — measured, it hid five Disciple pieces and
        # made the grail count read 4 instead of 10. A resolver pointed at the wrong key answers
        # plausibly and no safety net fires. [[a-wrong-answer-skips-the-fallback]]
        for _k in _keys:
            for _n in (_d.get(_k) or []):
                table[str(_n).strip().lower().replace("\u2019", "'")] = True
    if not table:
        return None
    hit = 0
    for _n in set(names or []):
        _k = str(_n).strip().lower().replace("\u2019", "'")
        if _k in table or any(_r.split(" (")[0] == _k for _r in table):
            hit += 1
    return hit

def _check_read_names_are_actually_banked():
    """v2751 — 119 ITEM NAMES WERE READ FROM HIS FOOTAGE AND NONE OF THEM ARE BANKED.

    Konyo, 2026-09-07: *"the routing and funnel and main pipeline should still go through it
    regardless of the paid reads.. i want it filtered and then stamped unified logic"*. Following
    that instead of the paid-read question is what found this.

    MEASURED across all 40 reels, printer.stream() joined to reel_router.route():
        PRINTER   11 reels   64 names read, and the session carries NO SEAL AT ALL
        JOIN       4 reels   55 names read, sealed — and the seal does not carry them
        CAPTURE/EMPTY/STATION            0 names
    The printer says it per reel: *"23 item name(s) were read, but this session has no seal at all,
    so the extraction contract was never even asked about it."*

    ⚠⚠ THE READING ALREADY HAPPENED. The names are in the JOURNAL RING right now, retrievable by
    session id — Andariel's Visage, Atma's Wail, Bartuc's Cut-Throat, Sandstorm Trek, Tearhaunch.
    No paid read is owed for any of them; the pipeline is stalled AFTER the read.

    ⚠ AND HIS FILTER DECIDES WHICH ONES COUNT, which is why this row reports PANEL separately.
    extract_gap's taxonomy (his own words: *"if its a FLOOR ITEM with no stash/inventory open then
    obviously it cant be in the same exact route"*) splits 472 corpus names PANEL 110 / FLOOR 208 /
    CHRONICLE 154 — 77% filtered. A floor name has no cell to name, so it is a sighting and not a
    holding. Reporting one number over both would overstate the work owed.

    ⛔ IT REPORTS AND NEVER WRITES. Banking means landing in vault_accum/vault_seen, which is gated
    on witnesses deliberately, and footage has no un-delete. This row makes the stall visible; the
    existing witnessed machinery stays the only thing that writes.
    """
    try:
        import extract_gap as _EG
    except Exception as exc:
        return UNKNOWN, ("the router could not be imported (%s), so whether read names are "
                         "banked is UNKNOWN" % type(exc).__name__)
    # REG-2181 - route() already walked the printer and copied names and sealed onto each reel.
    # Asking printer.stream() again was a second shelf walk (9.3 s cold beside a 3 s budget).
    _EG._named_hold(True)
    try:
        try:
            rt = _reel_route_read()
        except Exception as exc:
            return UNKNOWN, "the router raised (%s) - UNKNOWN, not clean" % type(exc).__name__
        if not isinstance(rt, dict) or not rt.get("ok"):
            return UNKNOWN, "the router would not answer, so nothing is known about banking"
        unsealed = sealed_blind = 0
        reels = set()
        for r in (rt.get("reels") or []):
            n, sld = r.get("names"), r.get("sealed")
            if not isinstance(n, int) or not n:
                continue
            s = r.get("station")
            if sld is False:
                unsealed += n; reels.add(str(r.get("reel")))
            elif s == "JOIN":
                sealed_blind += n; reels.add(str(r.get("reel")))
        total = unsealed + sealed_blind
        if not total:
            return OK, "every item name the readers produced is carried by a seal"
        # his filter: only PANEL names can become a holding
        panel = None
        distinct = grail = None
        try:
            named, _why = _EG._named_sessions()
            panel = sum(int((v or {}).get("panel") or 0) for v in (named or {}).values())
            # v3374 - the panel count is not the number of holdings. The placed list is what
            # can be addressed, and a name with no roster stays out of the holding figure.
            _names = [n for v in (named or {}).values()
                      for n, t in ((v or {}).get("placed") or []) if t == "panel"]
            distinct = len(set(_names))
            grail = _grail_of(_names)          # None when no roster can be read — never a guess
        except Exception:
            panel = distinct = grail = None
        if panel is None:
            tail = ""
        elif grail is None:
            tail = (" Of the corpus's names, %d were read with a container OPEN (stash/inventory)"
                    "%s; how many are grail-relevant is UNKNOWN here — no roster could be read."
                    % (panel, "" if distinct is None else " (%d distinct)" % distinct))
        else:
            tail = (" Of the corpus's names, %d were read with a container OPEN (stash/inventory) — "
                    "%d distinct, of which %d resolve to a roster and can become a holding; the rest "
                    "are furniture, consumables and bare bases. Floor sightings have no cell to name."
                    % (panel, distinct, grail))
        return MISSING, ("%d item name(s) were READ from %d reel(s) and NONE are banked: %d sit in "
                         "sessions with NO SEAL AT ALL, and %d are under a seal that does not carry "
                         "them. The reading already happened - the names are in the journal ring - so "
                         "no paid read is owed here.%s"
                         % (total, len(reels), unsealed, sealed_blind, tail))
    finally:
        _EG._named_hold(False)


def _check_the_printer_can_reach_the_corpus():
    """v2749 — ZERO CONTRADICTIONS BECAUSE THE CONTRACT REFUSES EVERY SEAL.

    His ask, 2026-09-03: *"i want this related to the 3/4D printer it should be in the same zone.
    that unified printer needs to be built, that processing system for the reels all need a unified
    logic coming in and out"*. `printer_reach` answers the question that opens: HOW MUCH OF THE
    CORPUS CAN THE PIPELINE ACT ON AT ALL. Nothing read it — `grep -c printer_reach` was 0 across
    control_app.py, console_doctor.py, corroborate.py and control_ui.html, the same shape as
    end_routes one version ago. [[the-unjoined-end]] [[sweep-dont-ask]]

    MEASURED on his tree: reels 437 · seals 31 · joined 21 · **sealsSatisfyingContract 0**, with
    name, location AND provenance missing on all 31.

    ⚠⚠ THE READING THAT MAKES THIS WORTH A ROW: a downstream reader sees ZERO CONTRADICTIONS and
    concludes the pipeline is healthy. It is not — the contract refuses every seal, so the
    contradiction CANNOT ARISE. A zero that means "nothing qualified" wearing the clothes of a zero
    that means "nothing wrong". [[zero-needs-a-denominator]]

    ⚠ IT NAMES THE MISSING FACTS, never a bare count, because the facts imply DIFFERENT WORK: a
    missing `name` is a reader change, while a missing `location` is a CAPTURE question — 0 of 1,065
    deep rows carry a cell — and that is HIS ruling, not something code decides.
    ⛔ No wilson lock: reachability is a READING, not a claim attacks can refute.
    """
    try:
        import printer_reach as _PR
    except Exception as exc:
        return UNKNOWN, ("printer_reach would not import (%s), so how much of the corpus the "
                         "pipeline can reach is UNKNOWN" % type(exc).__name__)
    try:
        r = _PR.report()
    except Exception as exc:
        return UNKNOWN, "the printer-reach report raised (%s) - UNKNOWN, not clean" % type(exc).__name__
    if not isinstance(r, dict) or not r.get("counts"):
        # ⚠ `(r or {}).get(...)` RAISES when r is a truthy NON-dict — a bare string report walks
        # straight past the isinstance guard and into AttributeError. Caught by this row's own gate
        # before it shipped: an UNKNOWN path that crashes reports nothing, which is strictly worse
        # than the unknown it was written to express. [[unknown-stays-unknown]]
        _why = r.get("why") if isinstance(r, dict) else None
        return UNKNOWN, str(_why or "the printer-reach report carried no counts")
    c = r.get("counts") or {}
    seals = c.get("seals")
    ok_n = c.get("sealsSatisfyingContract")
    if seals is None or ok_n is None:
        # a count nobody took is not zero
        return UNKNOWN, "the report carried no seal counts, so nothing is known about reach"
    # ⚠ v3297 — DO NOT RE-MANUFACTURE THE ZERO. printer_reach already distinguishes the two
    # zeros: its empty arm returns state=UNKNOWN with "there is no seal store to read — 0 seals,
    # so the contract was never asked to admit anything". This row used to branch on COUNTS only
    # and print the populated-case sentence over an EMPTY world — "NOT ONE of 0 seal(s) …
    # refused everything" — a false confession seen verbatim on the guest board 2026-09-18.
    # With 0 seals nothing was refused; the honest sentence exists upstream, so pass it through.
    # [[zero-needs-a-denominator]] [[the-unjoined-end]]
    if str(r.get("state") or "") == "UNKNOWN" or not seals:
        return UNKNOWN, str(r.get("why") or "0 seals — the contract was never asked, so nothing "
                                            "about this corpus was established")
    if ok_n:
        return OK, ("%s of %s seal(s) satisfy the extraction contract, so the pipeline can act on "
                    "the corpus" % (ok_n, seals))
    facts = r.get("missingByFact") or {}
    named = ", ".join("%s %s" % (k, v) for k, v in sorted(facts.items(), key=lambda kv: -kv[1]))
    return MISSING, ("NOT ONE of %s seal(s) satisfies the extraction contract, so no reel can be "
                     "judged disposable and a contradiction cannot arise AT ALL - zero here means "
                     "the contract refused everything, not that nothing is wrong. Missing: %s. "
                     "(reels %s, joined %s.) ⚠ `location` is a CAPTURE question, not a reader one."
                     % (seals, named or "unrecorded", c.get("reels"), c.get("joined")))


def _check_every_reel_can_still_reach_an_end_route():
    """v2748 — THE DERIVED END-ROUTE PREDICATE WAS READ BY NOTHING.

    MEASURED before writing this: `grep -c end_routes` was **0** in control_app.py, console_doctor.py,
    corroborate.py and control_ui.html. Built, correct, covered by 27 of its own tests, and invisible
    to every surface and every supervision layer — the SAME defect this heart caught in reel_router
    one version ago, in its sibling. I fixed the river's unjoined end and left its twin running.
    [[the-unjoined-end]] [[sweep-dont-ask]]

    Konyo's ruling settled the DESTINATION and named the METHOD: *"it should be also eventually
    tombstoned though why is not also processed through the printer to get routed back at the end
    routes they should. reverse engineeer it if needed the ones that are working"*. So the door was
    read back off the 410 reels that already went through it, not invented — 99.27% coverage against
    a declared floor of 95%.

    ⚠⚠ THE SPLIT THIS ROW EXISTS TO KEEP VISIBLE, because collapsing it is how 40 reels became one
    undifferentiated bucket:
      · DEAD-ENDED     every door refused, with numbers. THIS is what his ruling forbids.
      · FINISHED-WAITING  a door OPENED and only circumstance holds it. His ruling does not forbid
                          this, and counting it here would make the row read 40 of 40 — true,
                          useless, and ignored within a week.

    ⚠ RED TODAY ON PURPOSE, at 32 of 40. A check that could only ever be green measures nothing. It
    goes green when reels stop dead-ending, not when someone edits a list.
    ⛔ NO WILSON LOCK: "these reels cannot reach an end route" is a READING, not a claim attacks can
    refute. Manufacturing attacks to score a state is the inflation `_hardening_gap` refuses.
    """
    try:
        import end_routes as _ER
    except Exception as exc:
        return UNKNOWN, ("end_routes would not import (%s), so whether any reel can reach an end "
                         "route is UNKNOWN" % type(exc).__name__)
    try:
        r = _ER.report()
    except Exception as exc:
        return UNKNOWN, "the end-route report raised (%s) - UNKNOWN, not clean" % type(exc).__name__
    # ⚠ SAME SHAPE AS THE printer-reach ROW, found by sweeping this file the moment that one was
    # fixed rather than a version later. `r.get("ok")` raises on a truthy NON-dict, and so does the
    # `(r or {})` fallback beside it — so an UNKNOWN path written to survive a bad report would
    # itself crash on one. An UNKNOWN that raises reports nothing at all. [[sweep-dont-ask]]
    if not isinstance(r, dict) or not r.get("ok"):
        _why = r.get("why") if isinstance(r, dict) else None
        return UNKNOWN, str(_why or "the end-route report could not be taken")
    dead = r.get("deadEnded")
    waiting = r.get("finishedWaiting")
    walked = r.get("walked")
    if dead is None or walked is None:
        # a count nobody took is not zero
        return UNKNOWN, "the report carried no dead-ended count, so nothing is known"
    # ⚠⚠ REG-1277 (#221) — THE DELETER AND THESE DOORS MUST AGREE BEFORE ANYTHING LEAVES, and this
    # leads the row because a tombstone cannot be taken back. 13 reels left on 2026-09-10 while this
    # module refused every one; the two answers were never compared. [[the-unjoined-end]]
    _released_unextracted = r.get("deleterWouldRelease")
    if _released_unextracted:
        return MISSING, ("the reel deleter would RELEASE %d reel(s) every end-route door refuses (%s) - "
                         "they hold panels nothing extracted, and a tombstone is for ever. The two "
                         "authorities disagree; the deleter's rule is the one to read (reel_retention)."
                         % (len(_released_unextracted),
                            ", ".join(str(x) for x in _released_unextracted[:3])))
    if not dead:
        return OK, ("no reel is dead-ended: %s of %s finished and waiting only on circumstance"
                    % (waiting, walked))
    # name WHAT they lack — a count alone is not actionable
    lack = {}
    for x in (r.get("rows") or []):
        if not x.get("deadEnded"):
            continue
        for g in (x.get("missing") or []):
            w = g.get("what") if isinstance(g, dict) else str(g)
            lack[str(w)] = lack.get(str(w), 0) + 1
    named = ", ".join("%s %d" % (k, v) for k, v in sorted(lack.items(), key=lambda kv: -kv[1]))
    # ══ v3181 — AND SAY WHAT WOULD UNSTICK THEM. end_routes.reprocessing_list() answers exactly
    # that — "which reels would reach the end route if the missing thing were supplied", sorted by
    # unread panels — and MEASURED 2026-09-15 it appeared EXACTLY ONCE in the whole codebase: its
    # own `def`. Built, documented, correct, called by nothing. This row has been reporting the
    # DEAD-ENDED count for versions while the function naming the remedy sat unread beside it.
    #
    # ⚠ THE SAME DEFECT THIS CHECK'S OWN DOCSTRING WAS WRITTEN ABOUT. v2748: "THE DERIVED
    # END-ROUTE PREDICATE WAS READ BY NOTHING ... I fixed the river's unjoined end and left its
    # twin running." Its twin had a twin. [[the-unjoined-end]] [[sweep-dont-ask]]
    #
    # ⚠ IT NAMES AND STOPS. reprocessing_list runs nothing and spends nothing; reading those
    # panels is a paid lane behind his standing ruling. The row gets the remedy, not the act.
    _fix = ""
    try:
        _rp = _ER.reprocessing_list()
        if _rp.get("n"):
            _top = (_rp.get("reels") or [{}])[0]
            _fix = ("  \u2192 %d of them hold %d unread panel frame(s); reading those is the only "
                    "thing between them and the end route the finished reels went through. "
                    "Biggest: %s with %s."
                    % (_rp["n"], _rp.get("panels") or 0,
                       str(_top.get("reel") or "?"), _top.get("panels")))
    except Exception:
        pass   # a remedy we could not compute must not take the finding down with it
    return MISSING, ("%s of %s reel(s) are DEAD-ENDED - every end-route door refused them, with "
                     "numbers. What they lack: %s. (%s more are finished and waiting only on "
                     "circumstance, which his ruling does not forbid.)"
                     % (dead, walked, named or "unrecorded", waiting)) + _fix


def _check_the_console_painted_all_of_itself():
    """v2747 — THE WITNESS COULD NOT SEE HALF A BLANK CONSOLE, AND HIS SIGHTING WAS EXACTLY THAT.

    Konyo, 2026-09-06, with a screenshot: *"theres a big empty space here im pretty sure there was
    something here"*. The Sessions tab's right rail rendered correctly — relaunch, eagle, repair,
    THE FLEET, THE SHELF — while ~1080x560 of the MAIN COLUMN was blank.

    ⚠⚠ THE BLINDNESS IS MEASURED, NOT ARGUED. `paint_witness.blank_strikes` asks about the WHOLE
    WINDOW: *"look N of M found content ON THE WINDOW, so it is not blank"*. His rail was painting,
    so the window HAD content, so the witness said PAINTED — correctly, for the question it asks.
    `tv/ui_faults.jsonl` settles it: on the day of the sighting it recorded 21 faults, SIXTEEN of
    them `console-pixels-blank-nothing-else-saw-it`, and ZERO within 45 minutes of 20:14. The
    instrument was working and blind at the same time. [[gate-blind-to-unexercised-input]]

    ⚠ THIS ROW READS A STATE, IT DOES NOT ACT. region_witness never focuses, reloads or restarts —
    the rescue decides. A witness that acts is a witness nobody can trust to abstain.
    ⚠ AND IT ABSTAINS OFTEN, ON PURPOSE: an OCCLUDED window (Safari over his console) or a failed
    capture is UNKNOWN, never OK and never a fault. Measured live — Safari and Terminal covered
    100% of his console while this was being built, and a one-sided cover would otherwise have
    read blank-left/painted-right and fired about a perfectly healthy window.
    """
    try:
        import region_witness as _RW
    except Exception as exc:
        return UNKNOWN, ("the region witness would not import (%s), so nothing is known about "
                         "which parts of the console painted" % type(exc).__name__)
    pid = os.getpid()
    try:
        r = _RW.half_blank_strikes(pid)
    except Exception as exc:
        return UNKNOWN, ("the region witness raised (%s) - UNKNOWN, not clean"
                         % type(exc).__name__)
    if not r.get("ok"):
        # a covered or unphotographable window is not evidence about painting
        _seen = str(r.get("why") or "the window could not be looked at")
        _os = _this_os()
        if _os != "darwin":
            # #171 (REG-2481) - ON WINDOWS THE WITNESS IS MISSING, NOT THE PAINT. MEASURED on Dean's PC 2026-10-22:
            # "Quartz is not importable here", unaskable for 45 days. The row stays UNKNOWN - never OK without a
            # look - and says which witness this PC lacks, so the 45 days read as an instrument nobody built for it
            # rather than a window that could not be seen this tick. [[quartz-only-probe-reads-as-a-verdict-on-windows]]
            return UNKNOWN, ("no witness can look at this console's window on %s yet: the region and paint "
                             "witnesses read macOS's window server (Quartz), and a Windows grab of the console's "
                             "own window has not been built, so NOTHING is known about whether it painted "
                             "whole - UNKNOWN, never OK without a look (the witness said: %s)"
                             % ("Windows" if _os.startswith("win") else _os, _seen[:160]))
        return UNKNOWN, _seen
    # ⚠⚠ v2752 — "NOT PARTLY DRAWN" IS TWO OPPOSITE FACTS AND THIS RETURNED OK FOR BOTH.
    # region_witness answers half=False both when everything is drawn AND when NOTHING is, because
    # a fully blank window is the whole-window witness's job. MEASURED on his black console: all six
    # cells blank, ink 0.0000 — and this row returned OK, while paint_witness said PAINTED off two
    # rows of title-bar border. Two instruments, one blind and one deferring to it, and a black
    # screen reported no fault at all. The deferral is still right about WHO RESCUES; it was wrong
    # about staying silent. [[the-unjoined-end]] [[unknown-stays-unknown]]
    if not r.get("half"):
        _g = r.get("grid") or {}
        _b, _p = _g.get("blank"), _g.get("painted")
        if isinstance(_b, int) and isinstance(_p, int) and _b and not _p:
            return MISSING, ("EVERY measurable cell of the console is blank (%d of %d) - the window "
                             "is drawing nothing at all. The whole-window witness owns the rescue "
                             "for this; this row exists so it is never SILENT while that one is "
                             "deciding." % (_b, _b + _p))
        return OK, str(r.get("why") or "every measurable part of the window is drawn")
    return MISSING, ("the console is PARTLY DRAWN and its beat cannot see it: %s. This is the shape "
                     "he reported - the DOM intact, the rail painting, and a whole column empty. "
                     "The whole-window witness reads this as healthy by design."
                     % str(r.get("why"))[:220])


def _check_the_river_is_moving():
    """v2742 — 40 OF 40 REELS SIT AT A STATION NO AUTOMATIC LANE TAKES ITS INPUT FROM.

    Konyo: *"something needs to run that river ... something needs to automate this puppy if its
    not wired connect and wire it properly"*.

    MEASURED across his 40 reels: EMPTY 6 · STATION 7 · PRINTER 11 · JOIN 4 · CAPTURE 12.
    Two are by design. Two are real, and this row exists to keep them visible:
      · STATION (7, the PAID queue) HAS a reel-reading lane — chronicle_autoreel_tick — but it
        selects on the durable sweep memory rather than on this station, so the queue and the
        reader never meet.
      · PRINTER (11) owes a SEAL only the vault lane can write, and its work list is retention's
        `vault-owes` — measured 0 of 40 PERMANENTLY, because that tag is the LAST rule in a
        first-match-wins list and every reel matches something earlier. Eleven reels are waiting
        for a seal nothing will ever write.

    ⚠ THIS ROW IS RED TODAY AND THAT IS CORRECT. A check that could only ever be green measures
    nothing. It goes green when a lane actually drains a station, not when someone edits a list.
    ⚠ IT IS A STATE, NOT A LOCK. No wilson score belongs here: a score belongs on a claim that can
    be ATTACKED, and "the river is moving" is a reading. Inventing attacks to give a state a number
    is the inflation `_hardening_gap` refuses. [[build-the-heart-and-census-everywhere]]
    """
    try:
        import reel_router as _rr
        d = _reel_route_read()
    except Exception as e:
        return UNKNOWN, "reel_router will not answer (%s), so the river is UNMEASURED" % str(e)[:60]
    if not isinstance(d, dict) or not d.get("ok"):
        return UNKNOWN, ((d or {}).get("why") or "reel_router did not answer")
    rows = d.get("reels")
    if not isinstance(rows, list) or not rows:
        return UNKNOWN, "no reel was stationed, so nothing can be concluded about the river"
    stuck = {}
    at = {}
    for r in rows:
        # the list is guarded above; its ELEMENTS are not, and `(r or {}).get` raises on a truthy
        # non-dict exactly as it did in the two rows above
        if not isinstance(r, dict):
            continue
        st = r.get("station")
        if not st or st in _BY_DESIGN_STATIONS or st in ("ROUTED", "TOMBSTONE"):
            continue
        if r.get("owes"):
            if st in _PER_REEL_STATIONS and r.get("reel"):
                at.setdefault(st, []).append(str(r.get("reel")))
            else:
                stuck[st] = stuck.get(st, 0) + 1
    # REG-3201 - AT PRINTER AND STATION, WHETHER A LANE DELIVERS IS A FACT ABOUT EACH REEL. MEASURED on his Mac
    # 2026-11-05: "3 of 42 reel(s) ... no automatic lane delivers (PRINTER 2, STATION 1)" - and the STATION reel was the
    # vault lane's own, quarantined after an 854 s hang; the two PRINTER reels were in no lane's queue. A reel its lane
    # will start, or that waits on a hold that clears by itself (a hang's backoff, a cooldown, a recording still
    # rolling), is not undelivered; every other wait is counted and NAMED. Who-delivers UNKNOWN keeps the old reading.
    waits = []
    unknown = 0
    for st in sorted(at):
        ids = at[st]
        dl = _river_delivery(st, ids)
        if not isinstance(dl, dict):
            # v3867 (the Grok CLI on REG-3201, #231 6674616604) - who delivers them could not be asked (the vault store
            # would not load, or the ask raised): counted, as the station reads, and SAID UNKNOWN - never "no lane"
            stuck[st] = stuck.get(st, 0) + len(ids)
            unknown += len(ids)
            continue
        for w in (dl.get("waits") or []):
            if isinstance(w, dict) and not w.get("selfClearing"):
                stuck[st] = stuck.get(st, 0) + len(w.get("reels") or [])
                # r4 review - a reel whose lane check could not be asked keeps the station reading (counted), and
                # the sentence says it is UNKNOWN rather than letting the count read as "no lane"
                if w.get("key") == "unknown":
                    unknown += len(w.get("reels") or [])
        if dl.get("waits"):
            waits.append(str(dl.get("why") or ""))
    said = (" Per reel: %s." % "; ".join(waits)) if waits else ""
    if unknown:
        said = (" %d of them %s UNKNOWN: whether a lane holds %s could not be asked, so %s the station's "
                "reading.%s" % (unknown, "is" if unknown == 1 else "are", "it" if unknown == 1 else "them",
                                "it keeps" if unknown == 1 else "they keep", said))
    if not stuck:
        return OK, ("every stationed reel has a lane that can take it (%d reel(s) walked)%s"
                    % (len(rows), (" - waiting only on holds that clear by themselves." + said) if waits else ""))
    total = sum(stuck.values())
    named = ", ".join("%s %d" % (k, v) for k, v in sorted(stuck.items(), key=lambda kv: -kv[1]))
    return MISSING, ("%d of %d reel(s) sit at a station that owes work no automatic lane delivers "
                     "(%s). They are not stuck on evidence — nothing is scheduled to move them.%s"
                     % (total, len(rows), named, said))


#: REG-3201 - the stations whose lane may or may not hold a given reel, so delivery is asked per reel
_PER_REEL_STATIONS = ("PRINTER", "STATION")


def _river_delivery(station, reels):
    """REG-3201 - who delivers each reel (control_app._station_delivery). -> dict | None (UNKNOWN). A seam.

    v3865 - asked of the IMPORTED module once it has restored the vault lane's store from disk, never of the serving
    console: "the river" runs in the eagle's child (REG-2987), where the console's memory is out of reach, and asking it
    in the console instead would walk the river there - one reel_router.route() measured +197 MB on his Mac, the spike
    REG-2987 moved out. Every input of the picker rule is persisted in that store (retired, cooldown, hung), so it answers
    as the console would. A store that exists and will not read is UNKNOWN, never "no lane"."""
    try:
        import control_app as _ca
        if _ca._vault_autoread_load() is None:
            return None
        return _ca._station_delivery(station, reels)
    except Exception:
        return None


def _check_the_vault_stores_are_readable():
    """His ledger is the whole point of the vault manager. An unreadable store must never read as
    an empty one — that difference is what the free ledger view exists to keep."""
    import json as _j
    names = ("vault_accum.json", "vault_seen.json", "vault_swept.json")
    absent, broken, counts = [], [], {}
    for n in names:
        fp = os.path.join(HERE, n)
        if not os.path.exists(fp):
            absent.append(n)
            continue
        try:
            with open(fp, encoding="utf-8") as fh:
                blob = _j.load(fh)
            rows = blob.get("owned") if isinstance(blob, dict) and "owned" in blob else (
                blob.get("rows") if isinstance(blob, dict) and "rows" in blob else blob)
            counts[n] = len(rows) if hasattr(rows, "__len__") else 0
        except Exception as e:
            broken.append("%s (%s)" % (n, str(e)[:40]))
    if broken:
        return MISSING, ("a vault store will not parse: %s — everything downstream is INCOMPLETE, "
                         "not empty" % "; ".join(broken))
    if absent:
        return UNKNOWN, ("%s has never been written, so there is nothing to compare against yet"
                         % ", ".join(absent))
    return OK, ("%d grounded row(s), %d sighting(s) waiting, %d sealed recording(s)"
                % (counts.get("vault_accum.json", 0), counts.get("vault_seen.json", 0),
                   counts.get("vault_swept.json", 0)))


def _check_his_progress_number_has_not_been_overwritten():
    """THE WATCHDOG HE ASKED FOR, and the fault it was built the morning of 2026-08-28 to catch.

    He opened the board and saw "0/0 ... some bug.. browser is wiped", then 117/135 sets and 266/403
    uniques against a real 120 and 280. Nothing was wiped: his ledger read foundLog 391, setPieces
    120, rwMade 99 all morning, and rendering that exact store on a clean board gives 120/135 and
    280/403. What went wrong was the BANKING — bible.html posts its counts to the console and the
    console wrote them into one global slot, so a second page in a different world overwrote his.
    board_tally.json carried route id 77f6..., his board's store is c5c2....

    His ask, verbatim: "this needs to get updated and locked going up like watchdog eagleeye should
    be updating the real count going up once every day atleast ... so when i log in now or this ever
    happens it saves from the 278/403 and the 120/135".

    So the tally is banked per world with a per-world high-water mark, and THIS is the surface that
    tells him when something falls. It reports, it does not heal: silently restoring the high number
    would hide the thing that made it fall, and a wrong number that looks right survives for weeks.
    [[feedback-silence-is-not-evidence]] [[unknown-stays-unknown]]
    """
    import json as _j
    fp = os.path.join(HERE, "board_tally.json")
    if not os.path.exists(fp):
        return UNKNOWN, ("no board tally has ever been banked — open the board once so it can "
                         "publish what it holds")
    try:
        with open(fp, encoding="utf-8") as fh:
            doc = _j.load(fh)
    except Exception as e:
        return MISSING, ("board_tally.json will not parse (%s) — his progress numbers are "
                         "UNREADABLE, which is not the same as zero" % str(e)[:50])
    if not isinstance(doc, dict):
        return MISSING, "board_tally.json is not an object"

    if doc.get("contested"):
        rows = doc["contested"]
        say = " vs ".join("%s sets=%s uniques=%s"
                          % (str(r.get("route") or "?").split("|")[0][:8],
                             r.get("sets"), r.get("uniques")) for r in rows[:3])
        # ⚠⚠ v2643 — THIS `return` USED TO SIT HERE AND IT BLINDED EVERYTHING BELOW IT.
        # The high-water/drop check further down — "his published progress is BELOW its own
        # high-water mark", the one that catches a ledger entry vanishing — was UNREACHABLE for
        # 7.8 days behind a contested alarm that was itself false (a week-stale row from a world
        # `ownerId` had already excluded). A warning is not a verdict, and a warning that returns
        # before a detector has silently switched that detector off.
        # It is carried in `notes` and reported WITH whatever the real check concludes.
        _contested_say = ("⚠ two worlds are both claiming to be him and they disagree: %s. The "
                          "newest is published, which may be the wrong one — open the board and "
                          "check the number before trusting anything downstream" % say)
    else:
        _contested_say = ""

    high = doc.get("high") if isinstance(doc.get("high"), dict) else {}
    drops = doc.get("drops") if isinstance(doc.get("drops"), list) else []
    # ⚠⚠ v2643 — PICK HIS WORLD BY `ownerId`, NOT BY DICT ORDER. This took the FIRST row whose
    # `who.pfx` is "" and stopped. Measured 2026-09-05: it happens to land on 77f641… , which IS
    # `ownerId` — but by luck of iteration order across 404 routes, not by a decision. `ownerId` is
    # resolved authoritatively upstream and sits right here in the doc; using anything else to
    # answer "whose high-water mark" is a guess wearing a measurement's clothes.
    _own = str(doc.get("ownerId") or "")
    key = ""
    # REG-2460 round 2 - THE MARK OF THE WORLD THAT IS PUBLISHED, NOT OF THE FIRST OWNER-SHAPED ROW.
    # The top-level lanes compared below are the world board_tally_merge PUBLISHED (ownerId when it
    # is known, else the newest pfx "" post). Without ownerId (Windows has no WebKit store) the
    # first-in-dict-order row could be a different world: Dean's ladder world (newest, reads 0) was
    # compared against his main world's 261, and re-basing the ladder world could never clear it.
    _pub = doc.get("who") if isinstance(doc.get("who"), dict) else doc.get("route")
    if isinstance(_pub, dict):
        _pk = "%s|%s" % (str(_pub.get("id") or "")[:40], str(_pub.get("p") or "")[:16])
        if _pk in (doc.get("byRoute") or {}) and (not _own or str(_pub.get("id") or "") == _own):
            key = _pk
    for k, row in (doc.get("byRoute") or {}).items() if not key else ():
        w = row.get("who") or row.get("route") or {}
        if isinstance(w, dict) and _own and str(w.get("id") or "") == _own:
            key = k
            break
    if not key:
        for k, row in (doc.get("byRoute") or {}).items():
            w = row.get("who") or row.get("route") or {}
            if isinstance(w, dict) and w.get("pfx") == "":
                key = k
                break
    below = []
    for lane in ("sets", "uniques", "runewords"):
        now = (doc.get(lane) or {}).get("have")
        top = ((high.get(key) or {}).get(lane) or {}).get("have")
        if isinstance(now, int) and isinstance(top, int) and now < top:
            below.append("%s %d (best %d)" % (lane, now, top))
    if below:
        # ⚠⚠ v2643 — THE LAST DROP OF *HIS* WORLD, NOT THE LAST ROW IN THE FILE.
        # `drops[-1]` was literally a test fixture on his live store:
        #     {"route": "real-1|main", "lane": "runewords", "from": 42, "to": 0, "at": null}
        # so the first time his progress ever fell, this sentence would have reported a FIXTURE'S
        # fall as his — "the last recorded fall was runewords 42 -> 0", dated 1970 because `at` is
        # null. ⚠ THAT PATH WAS UNREACHABLE UNTIL THIS SAME VERSION UN-BLINDED IT: the contested
        # early-return above meant this branch never ran. Un-blinding a check makes everything it
        # says reachable, so what it says has to be true on the same day. [[sweep-dont-ask]]
        # ⚠ The fixture row is NOT removed — it is his file and nothing here prunes it; it is
        # simply no longer read as his.
        _mine = [d for d in drops if isinstance(d, dict) and (not key or d.get("route") == key)]
        recent = _mine[-1] if _mine else {}
        # ══ 2026-09-28 (Ledger fix, finding 2b) — NEVER "? None -> None" ══════════════════════
        # With no episode on record for his world (a file from before episodes, or a fall the
        # record never saw) this printed "The last recorded fall was ? None -> None": an unknown
        # dressed as a reading. It now says plainly that none is recorded. [[unknown-stays-unknown]]
        _from, _to = recent.get("from"), recent.get("to")
        if isinstance(_from, int) and isinstance(_to, int) and not isinstance(_from, bool):
            _last = "The last recorded fall was %s %d -> %d." % (
                recent.get("lane") or "an unnamed lane", _from, _to)
        else:
            _last = ("No drop episode is recorded for his world, so when and how far it fell is "
                     "UNKNOWN.")
        # REG-2460 - a mark that came from data that was never this world's (Dean's uniques 261 from
        # Konyo's seed) has one ruled door; the row names it so the fall is not "explained" by hiding it.
        return MISSING, ("his published progress is BELOW its own high-water mark: %s. %s "
                         "Nothing has been auto-restored, because putting the number back would "
                         "hide whatever took it away. If that mark was set by data that was never "
                         "this world's, POST /api/board_tally_rebase {\"world\", \"lane\", \"reason\", "
                         "\"confirm\": true} re-bases it to this reading and keeps the old mark beside it."
                         % ("; ".join(below), _last))
    if not high:
        return UNKNOWN, ("no high-water mark banked yet — it fills on the next tally the board "
                         "posts" + ((" · " + _contested_say) if _contested_say else ""))
    parts = []
    for lane in ("sets", "uniques", "runewords"):
        top = ((high.get(key) or {}).get(lane) or {}).get("have")
        if isinstance(top, int):
            parts.append("%s %d" % (lane, top))
    return OK, ("his progress is at its own best: %s — banked per world, so another browser cannot "
                "overwrite it" % (", ".join(parts) or "nothing banked yet"))


def _check_no_ledger_ENTRY_has_silently_vanished():
    """His 20-minute ledger snapshots are what made 2026-08-28 recoverable. Nothing SHOUTED.

    Overnight his bare d2r_foundLog went 391 -> 383 and d2r_setPieces 120 -> 117. The snapshots
    recorded every step of it and no surface said a word, so he found out by opening the board and
    asking "where is al my uniques and runeword and set items?". A record that captures a loss
    without reporting it is an autopsy, not a guard.

    THIS COMPARES THE TWO NEWEST SNAPSHOTS AND NAMES WHAT WENT. Names, not counts: "you are down 8"
    is not actionable and "Atma's Scarab, Gheed's Fortune, Frostburn ..." is. The names it printed
    that morning were the diagnosis — one carried a CURLY apostrophe and three were the exact
    entries d2r_setRepairKept is supposed to protect, which is what turned a mystery into a class.

    ⚠ IT NEVER RESTORES. Putting the entries back here would hide whatever removed them, and a
    ledger that heals itself silently is how a defect survives for months. It reports; the restore
    is a deliberate act through the board's own gated path. [[feedback-silence-is-not-evidence]]

    ⚠ AND A SHRINKING LEDGER IS NOT THE SAME AS A CHANGING ONE. Items ARRIVE constantly — 9 set
    pieces were registered in the very window 17 uniques vanished — so only REMOVALS are reported.
    """
    import glob as _glob
    import json as _j
    d = os.path.expanduser("~/d2r_ledger_backups")
    if not os.path.isdir(d):
        return UNKNOWN, ("no ledger snapshot directory — nothing to compare, so a loss would be "
                         "invisible. `python3 ~/d2r_ledger_backups/snapshot_ledger.py` starts it")
    files = sorted(_glob.glob(os.path.join(d, "ledger_*.json")))
    if len(files) < 2:
        return UNKNOWN, "fewer than two snapshots — there is nothing to compare against yet"

    def _load(p):
        try:
            with open(p, encoding="utf-8") as fh:
                doc = _j.load(fh)
        except Exception:
            return None
        led = doc.get("ledger") if isinstance(doc.get("ledger"), dict) else doc
        if not isinstance(led, dict):
            return None
        out = {}
        for k in ("foundLog", "setPieces", "rwMade", "owned"):
            v = led.get(k)
            if isinstance(v, dict):
                out[k] = set(v)
            elif isinstance(v, list):
                out[k] = {str(x) for x in v}
        return out or None

    new = _load(files[-1])
    old = _load(files[-2])
    if new is None or old is None:
        return UNKNOWN, ("a snapshot will not parse, so the comparison is UNKNOWN — which is not "
                         "the same as 'nothing was lost'")

    lost = {}
    for k in ("foundLog", "setPieces", "rwMade"):
        if k in new and k in old:
            gone = sorted(old[k] - new[k])
            if gone:
                lost[k] = gone
    if not lost:
        n = len(new.get("foundLog") or ())
        return OK, ("nothing has disappeared between the last two snapshots (%d found-ledger "
                    "entries, %d set pieces)" % (n, len(new.get("setPieces") or ())))

    parts = []
    for k, gone in lost.items():
        shown = ", ".join(gone[:6]) + (" +%d more" % (len(gone) - 6) if len(gone) > 6 else "")
        parts.append("%s lost %d: %s" % (k, len(gone), shown))
    return MISSING, ("ENTRIES DISAPPEARED between %s and %s — %s. Nothing has been put back: "
                     "restoring here would hide whatever removed them. To recover: "
                     "python3 ~/d2r_ledger_backups/restore_ledger.py --file %s --apply "
                     "(it goes through the board's own dated, merge-max, undoable apply)"
                     % (os.path.basename(files[-2]), os.path.basename(files[-1]),
                        " | ".join(parts), os.path.basename(files[-2])))


def _check_the_board_store_did_not_come_up_empty():
    """The event that cost him 17 uniques on 2026-08-28, made loud.

    His board's localStorage went empty overnight; the boot seed floor refilled it from the seeds
    compiled into bible.html, and the board came up reading a plausible 383/117. Nothing was
    reported. The rebuild is what hid the loss — a store that had lost EVERYTHING repainted itself
    into something that looked merely slightly behind.

    bible.html now writes d2r_storeEmptied when it seeds over a store that had clearly run before.
    This is the surface that reads it, because a flag nobody looks at is the same as no flag.
    """
    got = _board_read()
    if not got:
        return UNKNOWN, "the console did not answer — nobody asked, so nothing is known"
    if got.get("ok") is False:
        return UNKNOWN, "the board refused the read: %s" % str(got.get("why"))[:90]
    if not got.get("boardLoaded"):
        return UNKNOWN, ("the board is not loaded in the window, so its store cannot be asked — "
                         "which is not the same as 'it is fine'")
    if "storeEmptied" not in got:
        return UNKNOWN, ("this console predates the storeEmptied field (v2216) — restart it, or an "
                         "emptied store stays invisible here")
    ev = got.get("storeEmptied")
    if not ev:
        return OK, "the board's store has not come up empty"
    # ⚠⚠ v2991 — THIS SENTENCE DESCRIBED BEHAVIOUR v2988 REMOVED, AND IT IS THE ONE HE READS.
    # It said the store "was refilled from the built-in seeds". Since v2988 the floor REFUSES to
    # run over a store that became empty, so the board shows 0 — while this row told him it had
    # been refilled to a plausible 383/117. The eye put the cost plainly: "the operator is pointed
    # at 17 items missing from a full-looking store when the actual state is an obviously empty
    # board." Restore was still the right action; the diagnosis was the old one.
    # ⚠ The WRITER's two sentences were corrected in v2990 and this READER was not — a
    # caller/callee split where the contract changed and the surface describing it did not.
    # [[label-outlived-referent]] [[the-unjoined-end]]
    # ⚠⚠ v2993 — A RECOVERED STORE MUST STOP READING AS MISSING. The record had no exit: the
    # advertised restore (`restore_ledger.py --apply`, a merge-max chronicleApply) puts the NAMES
    # back and never removes `d2r_storeEmptied`, so this row reported MISSING for ever — including
    # after a successful recovery. A permanent alarm is one he learns to ignore, which is worse
    # than no alarm at all. bible.html now stamps `recoveredAt` when the store has contents again,
    # and keeps the record as history rather than deleting his evidence.
    _rec = ev.get("recoveredAt") if isinstance(ev, dict) else None
    if isinstance(_rec, (int, float)) and _rec > 0:
        import datetime as _dt2
        # ⚠ v3005 — THE COUNTS RIDE WITH THE CLAIM. Eye finding 3: `recoveredAt` means "a ledger
        # key exists", which one hand-added name satisfies — so "no longer needs action" could
        # stand over a store holding 1 of 20 lost items. The magnitude is what lets HIM judge
        # whether the recovery is real; a claim without its number cannot be argued with.
        # [[zero-needs-a-denominator]]
        _c2 = got.get("counts") if isinstance(got.get("counts"), dict) else {}
        # ⚠⚠ v3030 (#81) — AND NOW THE DENOMINATOR, because v3005's own sentence named the gap it
        # could not close: "one recovered name stamps it just as fully as four hundred". It printed
        # what the store holds NOW with nothing to hold it against, so 440-back-out-of-445 and
        # 440-back-out-of-900 read identically. The number he needs is what he HAD, and it is on
        # disk: v3009's retention keeps the newest snapshot PREDATING the episode alive for exactly
        # this question. [[zero-needs-a-denominator]]
        _before, _bwhy = (None, "")
        try:
            import control_app as _ca2
            _before, _bwhy = _ca2.ledger_counts_before(ev.get("at") if isinstance(ev, dict) else None)
        except Exception as _e2:
            _before, _bwhy = None, "the predating backup could not be read (%s)" % type(_e2).__name__
        # ⚠ AN UNREADABLE DENOMINATOR IS SAID, NEVER SUBSTITUTED. Falling back to the current
        # counts would make every recovery look total, which is the flattering direction.
        if isinstance(_before, dict):
            _mag = []
            for _k, _lbl in (("foundLog", "foundLog"), ("setPieces", "setPieces")):
                _n, _m = _c2.get(_k), _before.get(_k)
                if isinstance(_n, (int, float)) and isinstance(_m, (int, float)) and _m > 0:
                    _mag.append("%d of %d %s" % (int(_n), int(_m), _lbl))
                else:
                    _mag.append("%s of UNKNOWN %s" % (_said(_n), _lbl))
            _gap = ""
            _fn, _fm = _c2.get("foundLog"), _before.get("foundLog")
            if isinstance(_fn, (int, float)) and isinstance(_fm, (int, float)):
                if _fm > _fn:
                    _gap = (" ⚠ %d name(s) have NOT come back." % int(_fm - _fn))
                elif _fm < _fn:
                    # ⚠⚠ v3032 — "440 of 400" IS NOT A COMPLETE RECOVERY, IT IS A BROKEN
                    # DENOMINATOR. Found by the post-ship review of v3030: once the episode CLOSES
                    # the open-episode guard lifts, the true newest-before snapshot ages past 48h
                    # and is pruned, and an older FIRST-OF-DAY keeper inherits the role. The helper
                    # still finds a predating file so it never says UNKNOWN — it just answers with
                    # a smaller, older number, and the shortfall test above is False, so a degraded
                    # comparison reads as a MORE than full recovery with no warning.
                    # A before-picture smaller than the present cannot measure a shortfall. It may
                    # be innocent (he found new items after recovering) or it may be the degraded
                    # keeper — and those are different facts, so this says which it cannot tell.
                    # [[zero-needs-a-denominator]] [[stale-reading]]
                    _gap = (" ⚠ the before-picture holds FEWER (%d) than the store does now, so "
                            "this is not a shortfall measure: either names arrived after the "
                            "recovery, or the closest snapshot before the loss has been pruned "
                            "and an older keeper is standing in for it." % int(_fm))
            return OK, ("the board's store came up empty once and has contents again since %s UTC "
                        "— %s, against what it held before the loss (%s).%s The record is kept as "
                        "history — it is what says which backup predates the loss."
                        % (_dt2.datetime.utcfromtimestamp(_rec / 1000.0).strftime("%Y-%m-%d %H:%M"),
                           " / ".join(_mag), _bwhy, _gap))
        return OK, ("the board's store came up empty once and has contents again since %s UTC — "
                    "now %s foundLog / %s setPieces. ⚠ What it held BEFORE the loss is UNKNOWN "
                    "(%s), so how much came back cannot be judged from here — one recovered name "
                    "stamps the flag just as fully as four hundred. The record is kept as history."
                    % (_dt2.datetime.utcfromtimestamp(_rec / 1000.0).strftime("%Y-%m-%d %H:%M"),
                       _said(_c2.get("foundLog")), _said(_c2.get("setPieces")), _bwhy))
    # ⚠⚠ v3004 — THE ADVERTISED RESTORE COULD NOT CLEAR THE ALARM UNTIL A RELOAD. Found by the
    # cross-family eye on v2993: `restore_ledger.py --apply` writes names through chronicleApply
    # into the ALREADY-LOADED board, while `recoveredAt` is stamped only in bible.html's load-time
    # block — so he runs the exact command the MISSING row prints, the store genuinely refills,
    # and this row keeps saying MISSING and keeps telling him to run it again for the rest of the
    # session. The original bug was "forever, across boots"; v2993 made it "until the document
    # reloads", which --apply does not do. The evidence was in hand the whole time: _board_read()
    # already carries counts (measured live: foundLog=440 / setPieces=129 beside the event).
    # ⚠ My first draft of this comment claimed the LIVE event was still open — it was not: an
    # 80-char print truncation had hidden its recoveredAt, stamped at the 08:11 board reload. The
    # counts path below is therefore verified by STUB (an open event beside non-zero counts), not
    # by the live board, and saying otherwise would be a probe artifact wearing a measurement's
    # clothes. [[source-window-shortcut]] [[inherited-claim-is-not-evidence]]
    # ⚠ Only a MEASURED count exits; absent counts fall through, because "could not count" must
    # never read as "has contents". [[the-unjoined-end]] [[unknown-stays-unknown]]
    _cnt = got.get("counts") if isinstance(got.get("counts"), dict) else {}
    _fl, _sp = _cnt.get("foundLog"), _cnt.get("setPieces")
    if ((isinstance(_fl, (int, float)) and _fl > 0)
            or (isinstance(_sp, (int, float)) and _sp > 0)):
        return OK, ("the board's store came up empty once and HOLDS CONTENTS AGAIN — measured "
                    "this read: %s foundLog / %s setPieces. The episode is not closed yet "
                    "(recoveredAt stamps at board load, and this board has not reloaded since "
                    "the names came back), so the record stays as history and the next board "
                    "load closes it. No action needed."
                    % (_said(_fl), _said(_sp)))
    _at = ev.get("at") if isinstance(ev, dict) else None
    _boots = ev.get("boots") if isinstance(ev, dict) else None
    _when = ""
    if isinstance(_at, (int, float)) and _at > 0:
        import datetime as _dt
        _when = (" First seen %s UTC"
                 % _dt.datetime.utcfromtimestamp(_at / 1000.0).strftime("%Y-%m-%d %H:%M"))
        if isinstance(_boots, int) and _boots > 1:
            _when += " and still empty %d boots later" % _boots
        _when += "."
    return MISSING, ("THE BOARD'S STORE CAME UP EMPTY — it lost its contents on a load that had "
                     "run before. The seed floor is REFUSING to run over it, so the store stays "
                     "EMPTY rather than being papered over with defaults: an empty store you can "
                     "see is recoverable, a seeded one is not.%s That is how 17 uniques and 3 set "
                     "pieces went missing on 2026-08-28 while the board still read a plausible "
                     "383/117. Recover with: "
                     "python3 ~/d2r_ledger_backups/restore_ledger.py --apply" % _when)


def _check_the_shadow_gate_is_learning():
    """The Wilson lane, in the console. Konyo: "make it self improving and really accurate so its
    locked and locks in the console."

    It accumulates on every sweep through apply_proposal — the one door every proposal passes — so
    its sample is not a function of which call sites someone remembered to wire. This is where the
    record becomes visible, because a lane that only answers when asked by hand is a lane nobody
    asks.

    ⚠ IT NEVER PROMOTES ITSELF, and this check never recommends that it should. Reaching the
    threshold means the record is worth reading. A gate that switched on its own agreement
    statistics would be marking its own homework, and the failure lands as a wrong verdict written
    into his grail — the one place a wrong answer is invisible.
    """
    try:
        sys.path.insert(0, HERE)
        import shadow_ledger as _sl
        st = _sl.state()
    except Exception as e:
        return UNKNOWN, "the shadow lane could not be asked: %s" % str(e)[:90]
    if not st.get("ok"):
        return MISSING, st.get("say") or "the shadow ledger is unreadable"
    state = st.get("state")
    if state == "empty":
        return UNKNOWN, st.get("say")
    if state == "disagrees":
        return MISSING, st.get("say")
    # thin and agrees are both OK — one of them is just younger
    return OK, st.get("say")


def _check_the_tooltip_finder_is_honest():
    """v2321 — is the tooltip finder locating tooltips, or the HUD?

    Text density alone returns the same top-right corner box on every unhovered frame — measured,
    five in a row on a reel that registered nothing. The 8% area floor separates his real tooltip
    (33.4% of the frame) from that impostor (2.8%). This reports whether the floor is still doing
    its job and what the located tooltips actually yielded.
    """
    try:
        import tooltip_find as tf
    except Exception as e:
        return MISSING, "the tooltip finder will not import: %s" % str(e)[:70]
    try:
        r = tf.report()
    except Exception as e:
        return MISSING, "its ledger could not be read: %s" % str(e)[:70]
    if not r.get("attempts"):
        # ⚠⚠ v3179 — UNKNOWN, NOT MISSING, AND THE ROW'S OWN WORDS SAID SO. It read "nothing is
        # known about it either way" while rendering as a FAULT in his WHAT NEEDS YOU count. He
        # caught it: "everything should be reading healthy if its not missing ... so its honest".
        # A lane nobody has exercised is not a broken lane, and this console's whole doctrine is
        # that the two must never look the same. Counting it as needing him also inflated the one
        # number he acts on. [[unknown-stays-unknown]] [[zero-needs-a-denominator]]
        return UNKNOWN, ("the finder has never been asked — no frame has been put through it, so "
                         "nothing is known about it either way")
    if r.get("judged"):
        return OK, r["say"]
    return MISSING, ("%d located, %d refused, but none judged yet — nobody has said whether a "
                     "located tooltip yielded a name" % (r.get("located") or 0, r.get("refused") or 0))


def _check_his_gear_is_being_learned():
    """v2320 — is the main-character ledger actually accumulating, or silently empty?

    The LANE rule protects the equipment panel while it is on screen. This ledger is what protects
    the same item in a frame that only shows the stash — and it is only worth anything if sightings
    are reaching it. An empty ledger after a session of farming is a lane that is not being fed,
    which looks exactly like a lane with nothing to say.
    """
    try:
        import main_character as mc
    except Exception as e:
        return MISSING, "the main-character ledger will not import: %s" % str(e)[:70]
    try:
        r = mc.report()
    except Exception as e:
        return MISSING, "the ledger could not be read: %s" % str(e)[:70]
    tracked, locked = int(r.get("tracked") or 0), len(r.get("locked") or [])
    if tracked == 0:
        return MISSING, ("nothing has been recorded yet — no sighting has reached the ledger, so "
                         "no item can earn a lock. That is UNKNOWN, not 'he owns nothing'.")
    # ⚠ "0 locked" HAD TWO MEANINGS AND THIS RAIL REPORTED BOTH AS OK. One is "no item has
    # cleared the floor yet", which more farming fixes. The other is "no item can ever clear it",
    # which no amount of farming fixes — and that was the true one: `equip` only increments for
    # lane "equipment", and reel_segments has no such activity, so the input is pinned at zero.
    # Measured on his ledger: 4 tracked, every row equip:0, reported OK. [[label-outlived-referent]]
    if r.get("blockedWhy"):
        return MISSING, ("%d item(s) tracked and NOTHING CAN LOCK — %s"
                         % (tracked, r["blockedWhy"]))
    return OK, ("%d item(s) tracked, %d locked as his gear (floor %.2f, %d-look minimum, "
                "%d equipment sighting(s))"
                % (tracked, locked, r.get("floor") or 0.0, r.get("minSightings") or 0,
                   r.get("equipSightings") or 0))


def _check_the_locked_lanes_still_refuse():
    """He ruled it plainly: equipment and inventory are never to be told to move. The BOARD has
    carried _LOCKED_LANES since v1712; the engine that PRODUCES the suggestions did not until
    v2075, and a non-grail item he was WEARING could clear the throw bar."""
    try:
        sys.path.insert(0, HERE)
        import vault_retro as vr
    except Exception as e:
        return UNKNOWN, "vault_retro did not import (%s)" % str(e)[:70]
    locked = tuple(getattr(vr, "LOCKED_LANES", ()) or ())
    if not locked:
        return MISSING, ("vault_retro has no LOCKED_LANES — an item on his character or in his "
                         "inventory can be suggested for the bin again")
    for lane in ("equipment", "inventory"):
        if lane not in locked:
            return MISSING, "the %s lane is no longer locked against throw suggestions" % lane
    # ⚠⚠ v2771 — THIS ROW WAS CRYING WOLF ABOUT HIS OWN RULING, and a distrusted instrument is a
    # switched-off one. It required the throw bar to be strictly above the keep bar ON WITNESSES,
    # and reported MISSING when he levelled them on 2026-09-07:
    #   *"make it two also.. its fine.. i will review what i throw regardless.. as long as it in
    #    that bin"* · *"i will decide if to throw it out or not to"*
    # The DANGER the row exists for is real and unchanged — there is no un-throw in Diablo — but
    # the protection is not carried by the witness count alone. Throwing still demands STRICTLY
    # more CONFIDENCE (0.85 vs 0.55), and `witness_field="session"` makes the throw bar count
    # independent RECORDINGS where the keep bar counts looks. So the bars are still ordered; they
    # are ordered on a different axis than this row was checking.
    # ⇒ The invariant is now "strictly above on AT LEAST ONE axis, and never below on either".
    #   A true inversion — throw becoming EASIER than keep — still goes red.
    _tw = getattr(vr, "THROWOUT_MIN_WITNESSES", 0)
    _kw = getattr(vr, "KEEP_MIN_WITNESSES", 0)
    _tc = getattr(vr, "THROWOUT_CONF_FLOOR", 0.0)
    _kc = getattr(vr, "KEEP_CONF_FLOOR", 0.0)
    if _tw < _kw or _tc < _kc:
        return MISSING, ("THE THROW BAR IS NOW EASIER THAN THE KEEP BAR — witnesses %s vs %s, "
                         "confidence %.2f vs %.2f. An item could be thrown on evidence that would "
                         "not have kept it, and there is no un-throw in Diablo."
                         % (_tw, _kw, _tc, _kc))
    if _tw == _kw and _tc == _kc:
        return MISSING, ("the throw bar and the keep bar are IDENTICAL on both axes (%s witnesses, "
                         "%.2f confidence) — nothing anywhere makes throwing harder than keeping, "
                         "and there is no un-throw in Diablo" % (_tw, _tc))
    return OK, ("%s locked; keep needs %d look(s) at conf %.2f, throw needs %d recording(s) at "
                "conf %.2f — throw is stricter on %s"
                % (" + ".join(locked), _kw, _kc, _tw, _tc,
                   "witnesses and confidence" if (_tw > _kw and _tc > _kc)
                   else ("witnesses" if _tw > _kw else "confidence")))


def _check_the_two_surfaces_agree():
    """EVERY DOOR LEADS TO A ROOM, AND A MOVE LEFT EXACTLY ONE COPY.

    Konyo: "i want it all under management so nothing gets buged."

    This exists because ONE failure shape produced four separate defects he had to find himself,
    in a single arc, and not one gate saw any of them:
      · v2085 built the Vault tab on the BOARD and never added it to the CONSOLE header — the room
        existed with no door on the surface that asks for rooms;
      · v2085 COPIED the shadow/tooltip switches into the console drawer instead of MOVING them, so
        Tools kept rendering them and the job read as done;
      · the header hid the seventh tab instead of shrinking it, silently;
      · demo_console's PANE_TABS never walked the tab that had just shipped, so J1 reported a
        confident green about the four it already knew.
    Every one is the same thing: ADDED in the new place, NOT FINISHED in the old one. Silent by
    construction, which is the defining property. [[the-unjoined-end]] [[copy-drift]]

    Cheap on purpose — it reads three files and runs no subprocess, so it belongs in the fast set
    the eagle ticks on its timer, not in SLOW.

    All five arms are PROVEN RED, each by a sabotage asserted to have changed the bytes first:
        a console tab with no board room      -> MISSING
        J1 stops walking a shipped tab        -> MISSING
        a moved control reappears on the board-> MISSING
        the console loses a drawer switch     -> MISSING
        the signpost points at a dead room    -> MISSING
    and the healthy tree still reads OK. [[feedback-blind-fixture-green-gate]]
    """
    repo = os.path.dirname(HERE)
    try:
        board = open(os.path.join(repo, "bible.html"), encoding="utf-8").read()
        ui = open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()
    except Exception as e:
        return UNKNOWN, "could not read both surfaces (%s)" % str(e)[:70]

    faults = []
    # session and tvd are console-NATIVE: they deliberately open no board pane.
    NATIVE = {"session", "tvd"}
    shell = [m.group(1) for m in
             re.finditer(r'<button class="ht" type="button" data-tab="(\w+)"', ui)]
    panes = set(re.findall(r'id="tab-([\w-]+)"', board))
    for tab in shell:
        if tab not in NATIVE and tab not in panes:
            faults.append("the console offers a '%s' tab and the board has no #tab-%s to open"
                          % (tab, tab))

    try:
        demo = open(os.path.join(HERE, "demo_console.mjs"), encoding="utf-8").read()
        m = re.search(r"const PANE_TABS = \[([^\]]*)\]", demo)
        walked = set(re.findall(r"'(\w+)'", m.group(1))) if m else set()
        for tab in shell:
            if tab not in NATIVE and tab not in walked:
                faults.append("J1 never walks the '%s' tab — it ships ungated" % tab)
    except Exception:
        faults.append("demo_console.mjs could not be read to check its tab coverage")

    # A MOVED CONTROL MUST NOT BE BACK IN THE ROOM IT LEFT.
    # Pinned to TOOLS specifically, which is the room he named: "why is it still located in the
    # tools tab?". NOT pinned to "absent from the board", and the reason is worth recording —
    # v2093 tried exactly that and it was WRONG. toggleTooltipPass is not a painter: it arms the
    # vault mini-lane, POSTs /api/shadow AND POSTs /api/on, which STARTS A RECORDING, and it
    # tracks `startedReel` so switching OFF gives back the reel it started (a scar: 9GB/hour he
    # never asked for). The console drawer's twin only POSTs /api/shadow — and the server ignores
    # the `lane` field entirely, so BOTH drawer buttons write one shadow flag and neither performs
    # a tooltip pass. Deleting the board copies would have silently downgraded a real capability.
    # Tighten this to "absent from the board" only once the drawer drives the real orchestration.
    # [[the-unjoined-end]] [[unknown-stays-unknown]]
    # v2097 — TIGHTENED, now that the move is actually finished. This asked only "not in Tools"
    # because deleting the rows would have dropped a capability: /api/shadow ignores `lane`, so the
    # drawer's Tooltip button performed no pass. v2095 wired that button to the board's real
    # toggleTooltipPass through the iframe, and v2097 removed the rows, their four painters and 27
    # CSS rules. So the invariant is now the strong one: NEITHER switch may exist on the board at
    # all — the drawer beside the Grok eyes is their only home, which is where he asked twice for
    # them to be. [[the-unjoined-end]]
    for cid in ("shadow-ai", "tip-pass"):
        if ('id="%s"' % cid) in board:
            faults.append("#%s is on the BOARD again — ⚙ ADVANCED is its only home now, and two "
                          "copies is exactly how the last one hid" % cid)

    for cid in ("sadv-sha", "sadv-tip"):
        n = ui.count('id="%s"' % cid)
        if n != 1:
            faults.append("the console has %d copies of #%s (expected 1)" % (n, cid))

    if 'id="vault-moved-note"' in board:
        i = board.find('id="vault-moved-note"')
        m = re.search(r"switchTab\('(\w+)'\)", board[i:i + 1400])
        room = m.group(1) if m else None
        if not room or ('id="tab-%s"' % room) not in board:
            faults.append("the Tools signpost points at a room that does not exist (%r)" % room)
    else:
        faults.append("the Tools signpost is gone — anyone looking where the vault used to be is "
                      "told nothing")

    if faults:
        return MISSING, " · ".join(faults)[:400]
    return OK, ("%d console tab(s) all reach a board room, J1 walks every one, no moved control "
                "left a second copy" % len([t for t in shell if t not in NATIVE]))


# v2183 — several times one honest pass (8 names x 18 frames = 144 reads, measured on his log),
# and far below the 3,434 total the runaway reached. Asserted from BOTH sides by
# TestV2182TheHuntEyeMeasuresTHISRunNotEver so it can never become a threshold above its own
# signal. [[feedback-threshold-above-the-ceiling]]
_ONE_PASS_IS_ABSURD = 600


def _check_the_hunt_is_buying_something():
    """Is the name-hunt still paying for reads that find nothing? -> (state, say)

    v2174 — MEASURED ON HIS OWN LOG, and it is why "chronicle is reading" never stopped:

        28 hunt passes · 3,434 PAID reads · 2 new sightings   =   1,717 reads per sighting

    with pass after pass reading "hunt done: 144 read(s), new sightings for 0 name". The hunt took
    the same first eight held names alphabetically every run, failed, and the next sweep bought the
    identical 144 reads. Nothing watched the ECONOMY of it, so it ran for hours looking exactly
    like healthy activity — the console said "a chronicle sweep is reading", which was true.

    v2174 gave the hunt a memory of what came back empty. This is the eye on it: if the ratio
    climbs again, something has broken the memory (an unwritable file, a fingerprint that moves
    every run) and he is paying for it. A guard on the FIX is not the same as a guard on the COST.
    """
    log = os.path.join(HERE, "control_app.log")
    if not os.path.isfile(log):
        return "unknown", "no console log on this machine, so the hunt's cost cannot be read"
    try:
        with open(log, encoding="utf-8", errors="replace") as fh:
            txt = fh.read()[-2000000:]          # the tail is the recent behaviour
    except Exception as e:
        return "unknown", "the console log could not be read (%s)" % str(e)[:60]
    import re as _re
    # ⚠ v2182 — MEASURE **THIS RUN**, NOT THE WHOLE TAIL.
    # The 2MB tail spans hours and many process lifetimes. Right after the v2176 fix landed and
    # his console was relaunched onto it, this still reported "paying 2,149 reads per new
    # sighting" — TRUE of the log, FALSE of the running build, because the runaway it measured had
    # happened before the relaunch. A reading carries the age of the thing it measured, not of the
    # fetch. And a check that stays red after the repair becomes furniture, which is the same
    # defect as one that is always green. [[stale-reading]]
    # ⚠ v2183 — ANCHOR THE MARKER. A plain substring search for "CONSOLE BOOT " is matched by
    # ITEM NAMES: this log carries names an AI read off his game screenshots, and a review pointed
    # out that one containing that text would move the slice past every real hunt line and report
    # a live runaway as "no hunt has run". The check's OWN failure prose names the marker too, so
    # a log that ever quoted it would blind the check permanently. Require the whole shape at the
    # start of a line: the emoji, a version, and a pid. [[source-reading-guard]]
    _boots = [m.start() for m in _re.finditer(
        "(?m)^\\s*\\U0001f680 CONSOLE BOOT \\S+ pid=\\d+", txt)]
    _window = "since this console booted"
    if _boots:
        txt = txt[_boots[-1]:]
    else:
        # No marker in the tail: either an older build is running, or the tail is long enough that
        # the boot scrolled out. Either way the window is UNKNOWN and must be named as such rather
        # than quietly presented as current. [[unknown-stays-unknown]]
        _window = ("across a log window of unknown age — no CONSOLE BOOT marker in the tail, so "
                   "this may include runs from before a fix")
    # ⚠ v2183 — AND SO MUST THE PASS LINES BE ANCHORED, for the same reason. Unanchored, a single
    # OCR'd line quoting the phrase counted as a second pass, and TWO passes with no sightings is
    # exactly the trigger — so one honest miss plus one unlucky item name read as the runaway.
    # The real line is `   🔎 [uniques] hunt done: N read(s), new sightings for M name(s)`.
    passes = _re.findall(
        "(?m)^\\s*\\U0001f50e \\[(?:uniques|sets)\\] hunt done: (\\d+) read\\(s\\), "
        "new sightings for (\\d+) name", txt)
    if not passes:
        # ⚠ v2175.3 — "I CANNOT PARSE IT" IS NOT "NOTHING IS HAPPENING". This branch returned a
        # confident green, so one edit to the hunt's log line would have retired the check in
        # silence while the loop it was built for kept spending. If the log shows the hunt STARTING
        # and no pass line can be read, that is UNKNOWN and it must say so. A guard that cannot
        # fail is the same defect as one that is always red. [[feedback-blind-fixture-green-gate]]
        if _re.search(r"hunting\s+\S", txt) or "HIT " in txt:
            return "unknown", ("the hunt is running in the log but no 'hunt done:' line can be "
                               "parsed, so its cost cannot be read — the line this check reads "
                               "may have changed (chronicle_hunt.py, log('hunt done: ...'))")
        return "ok", "no hunt has run %s — nothing is being bought" % _window
    reads = sum(int(a) for a, _ in passes)
    sightings = sum(int(b) for _, b in passes)

    # ⚠ v2175.3 — PIN THE LAW, NOT THE NUMBER. The floor was `reads < 200` and ONE REAL PASS OF
    # THE VERY LOOP THIS CHECK EXISTS FOR IS 144 READS (8 names x 18 frames, measured). So the
    # trigger sat above its own per-pass ceiling: nothing could fire until the loop had already
    # paid twice, and on a log rotated per run it could never fire at all. Same shape as
    # STILL_MAX_DIFF=0.22 against a signal whose maximum is 0.133.
    # [[feedback-threshold-above-the-ceiling]]
    #
    # The law is not a read count. It is: THE HUNT WENT BACK AND BOUGHT AGAIN, AND STILL BROUGHT
    # NOTHING HOME. One empty pass is a normal miss. Two is the loop, at any price.
    # ⚠ v2183 — A SPEND THIS CHECK CANNOT ATTRIBUTE TO THE RUNNING BUILD IS UNKNOWN, NOT MISSING.
    # Without a boot marker the window may be entirely pre-fix — which is precisely the reading
    # that made this check wrong on his machine. Saying "missing" then is the stale verdict again,
    # wearing more words. [[stale-reading]] [[unknown-stays-unknown]]
    _verdict = "missing" if _boots else "unknown"

    # ⚠ v2183 — AND ONE PASS IS A MISS ONLY AT A SANE PRICE. The review found that a single pass
    # of any size returned "ok": `hunt done: 3434 read(s), new sightings for 0 name` was a miss,
    # not a loop. One honest pass is 8 names x 18 frames = 144 reads (measured). A single pass
    # costing several times that and bringing nothing home is not a miss, whatever the pass count.
    if sightings == 0 and len(passes) == 1 and reads >= _ONE_PASS_IS_ABSURD:
        return _verdict, ("a single hunt pass spent %d PAID reads %s and found NOTHING. One honest "
                          "pass is about 144 reads (8 names x 18 frames), so this is not a miss — "
                          "something is searching far more film than the cap should allow."
                          % (reads, _window))
    if sightings == 0 and len(passes) >= 2:
        return _verdict, ("the hunt has run %d pass(es) for %d PAID read(s) %s and found "
                           "NOTHING. That is the v2174 loop: it is re-buying names that already "
                           "came back empty. Check the hunt memory is being written "
                           "(tv/chron_hunt_memory.json, or beside chronicle_swept.json under "
                           "TV_HIST)." % (len(passes), reads, _window))
    # ⚠ NOT `and reads < 200`. A single pass with sightings==0 falls past every branch below and
    # reaches the `%.0f` tail with per=None, which raises inside a health check — the doctor
    # reporting an exception instead of a verdict. One pass is a miss at ANY price.
    if len(passes) < 2:
        return "ok", ("%d hunt pass(es), %d paid read(s), %d sighting(s) %s — a single pass is "
                      "a miss, not a loop" % (len(passes), reads, sightings, _window))
    per = reads / float(sightings) if sightings else None
    if per and per > 400:
        return _verdict, ("the hunt is paying %.0f reads per new sighting (%d reads, %d "
                           "sighting(s)) %s. The empty-hunt memory is not holding — a name that "
                           "found nothing is being bought again."
                           % (per, reads, sightings, _window))
    return "ok", ("the hunt is paying %.0f read(s) per new sighting across %d pass(es) %s"
                  % (per, len(passes), _window))


def _check_every_reel_on_disk_is_accounted_for():
    """Does the population on disk add up, and can the console SAY what each reel is doing here?

    ⚠⚠ v3278 — THREE NUMBERS REACHED A SCREEN AND NOTHING RELATED THEM. Konyo reported it as
    *"Shelf shows 13, disk holds 20"*, and his spec is *"only 8 reel session ... and obivously
    those 8 hidden fixtures are bakcend purpose also kept.. thats all 16 in total"*.

    MEASURED: his 8 + 8 is already exactly right. The river shows 8, the console's `onDisk` shows
    12 (the fixture filter moved every figure with it, v2877), and the disk holds 20. Any two of
    those read as a contradiction while nothing published the third fact — that 3 reels are
    waiting on the vault and 1 is releasable.

    ⚠ THE RED CONDITION IS THE SUM, not the number. 20 is not wrong and 16 is not a target to
    enforce; reels pass through. What would be wrong is a total whose parts do not add up, or a
    retention tag this console cannot name — both of which make every figure downstream suspect.
    [[zero-needs-a-denominator]] [[unknown-stays-unknown]]
    """
    try:
        import control_app as ca
        c = ca.reel_census()
    except Exception as e:
        return UNKNOWN, "the reel census could not be taken: %s" % str(e)[:80]
    if not isinstance(c, dict) or c.get("onDisk") is None:
        return UNKNOWN, (str((c or {}).get("why"))[:150]
                         or "the population could not be read, which is UNKNOWN and not an empty disk")
    if not c.get("sums"):
        return MISSING, c.get("why") or "the reel population does not add up"
    if c.get("other"):
        return UNKNOWN, ("%s — and %s is a retention tag this census has never met, so what those "
                         "reel(s) are doing here is UNKNOWN"
                         % (c["why"], ", ".join(sorted(c["other"]))))
    return OK, c["why"]


def _check_the_reel_extract_is_moving():
    """v2139 — IS THE EXTRACT ACTUALLY MOVING, and do the two memories still agree?

    THE FAULT THIS EXISTS FOR ran for 40 hours with every lamp green. The reel auto-sweep's
    private list claimed all 30 reels on disk were done; the durable memory had 12 of them never
    swept; the retention panel told him 11 were waiting. The loop asked only the private list, so
    it answered "no unswept reel" every 20 seconds and read nothing. He found it by reading a
    tooltip.

    The eagle could not have caught it. Its only sweep-named check, "sweep would find", is in SLOW
    and _eagle_once calls run(include_slow=False) — so on the ten-minute timer it never ran at all
    — and its subject is vault stash-panel density, not whether extract is moving. A gate joined to
    its caller and unjoined from its subject. Meanwhile "disk headroom" returned OK sixteen times
    while this was silent. [[the-unjoined-end]] [[feedback-silence-is-not-evidence]]

    CHEAP BY CONSTRUCTION so it can live on the timer: one directory listing and one small JSON
    read. No model call, no du, no subprocess.
    """
    try:
        import control_app as ca
        import chronicle_retro as cr
    except Exception as e:
        return UNKNOWN, "could not import the sweep modules: %s" % str(e)[:90]
    hist = os.environ.get("TV_HIST") or os.path.join(HERE, "frames", "hist")
    if not os.path.isdir(hist):
        return UNKNOWN, "no frames/hist on this machine"
    try:
        dirs = [os.path.basename(str(d)) for d in (cr.reel_dirs(hist, newest_first=True) or [])]
    except Exception as e:
        return UNKNOWN, "could not list reels: %s" % str(e)[:90]
    if not dirs:
        # REG-1811 — reel_dirs returns [] when the shelf will not list. [] is
        # also a shelf that holds no reels, and this row called that a pass.
        try:
            os.listdir(hist)
        except OSError as e:
            return UNKNOWN, ("could not list reels (%s: %s) — an unread shelf is not "
                             "an empty one" % (type(e).__name__, str(e)[:60]))
        return OK, "no reels on disk — nothing to extract"
    try:
        mem = ca._chron_swept_mem()
        owed = [r for r in dirs if ca._chron_reel_owes_a_read(r, mem)]
        private = ca._chron_reels_seen()
    except Exception as e:
        return UNKNOWN, "could not read the sweep memory: %s" % str(e)[:90]

    # THE SPLIT is CONTEXT, NOT THE VERDICT — and saying otherwise would be the same mistake
    # twice. Before v2139 the private list GATED the loop, so a split meant "these will never be
    # started" and was the whole fault. v2139 moved every decision onto the durable memory, so the
    # private list is now write-only: a stale entry is a file that lies, not a stall. Reporting it
    # as MISSING would be a label that outlived its referent — a true count under a sentence that
    # stopped being true — which is the class this console keeps paying for. So it rides in `why`,
    # and the fault that can still hurt him is the one that decides the verdict.
    split = [r for r in owed if r in private]
    tail = ("" if not split else
            " · the auto-sweep's own list still calls %d of them done — inert since v2139, "
            "nothing gates on it" % len(split))
    # v2221 — NAME THE RETAINED ENTRIES. chronicle_swept.json holds MORE entries than there are
    # reels on disk (36 vs 30, measured 2026-08-28) and nothing said why, so the file read as a
    # record that disagrees with the disk — which is what #167 was reopened on, and what nearly got
    # them "cleaned". They are reads whose footage was later pruned: pages 22/35/21/22/22/140, the
    # extract-then-prune loop working. An unexplained true number invites a destructive fix.
    try:
        _sp = ca._chron_swept_split(mem, dirs)
        _ret = ("" if not _sp.get("retained") else
                " · %d more entr%s retained for footage since pruned (the read is the record)"
                % (_sp["retained"], "y" if _sp["retained"] == 1 else "ies"))
    except Exception:
        _ret = ""
    # ⚠ v2225 — _ret rides on EVERY return below, not only the clean one. The first cut appended it
    # to the OK path alone, so the moment any reel owed a read the explanation for the 36-vs-30 gap
    # vanished — exactly when he is most likely to be reading the line and most likely to conclude
    # the record disagrees with the disk. An explanation that disappears under load is not one.
    if not owed:
        return OK, "all %d reel(s) have been read%s%s" % (len(dirs), tail, _ret)

    # OWED BUT NOT MOVING. The AGE is the finding — "the loop is alive" is not evidence that it is
    # doing anything, which is exactly how this went unnoticed for two days.
    # A memory that was never written has no age. Filing that as UNKNOWN (the eagle does not count
    # an unknown) let a console that has never banked a read look like one whose clock could not
    # be read. Absent is MISSING. A file that is there and will not stat stays UNKNOWN.
    path = ca._chron_swept_path()
    try:
        last = os.path.getmtime(path)
    except FileNotFoundError:
        return MISSING, ("%d reel(s) owe a read and no read has ever been banked on this console%s"
                         % (len(owed), tail + _ret))
    except Exception:
        return UNKNOWN, ("%d reel(s) owe a read and the sweep memory cannot be read, so its age "
                         "is unknown%s" % (len(owed), tail + _ret))
    hours = (time.time() - last) / 3600.0
    if hours > 2.0:
        return MISSING, ("%d of %d reel(s) owe a read and nothing has been banked for %.1f hours%s"
                         % (len(owed), len(dirs), hours, tail + _ret))
    return OK, ("%d reel(s) owe a read, last banked %.1fh ago — the loop is working through them%s"
                % (len(owed), hours, tail + _ret))


def _check_the_vault_proposal_still_clears_todays_bar():
    """★ THE STORED VAULT PROPOSAL, RE-GATED AGAINST TODAY'S BARS.

    Konyo, 2026-09-07: *"the vault accumalator that should be connected to the heart of the console
    with the vault and joined obivously too"* and *"just make sure its all wired and not stale and
    connected to the heart.. we soon will hit the VAULT and start debugging that"*.

    ⚠⚠ WHY A ROW AND NOT A FIX. A proposal is a PHOTOGRAPH of a decision made under the bars that
    existed when it was taken. The bars can move afterwards, and then the panel shows rows labelled
    OWNED that today's own rule would not accept — a stale display over a correct gate. Nothing
    watched that: `console_doctor` had exactly one vault row (`vault stores`, which asks only
    whether the files are READABLE), and the proposal itself was supervised by nothing.

    ⚠ AND THE DRIFT IS REAL AND HAS ALREADY HAPPENED IN BOTH DIRECTIONS. When this task was
    written the bar was 3 and 6 of his 7 stored rows failed it. Re-measured when it came to be
    built: `KEEP_MIN_WITNESSES` is 2 again ("HIS RULING, 2026-09-07") and all 7 pass. The task's
    own premise had expired — which is exactly the argument FOR this row rather than against it.
    A number I measured once is not evidence later. [[inherited-claim-is-not-evidence]]

    ⚠ IT NEVER RE-GRADES HIS STORED ROWS, and it never touches the bar. The write path already
    re-gates at the WRITE (`vault_apply`, v1595) and is ALL-OR-NOTHING, so a stale proposal cannot
    land badly — pressing register would REFUSE ALL SEVEN rather than write six wrong ones. What
    was missing was only that nobody was told. This says the delta out loud and stops there.
    ⛔ Lowering KEEP_MIN_WITNESSES to make stored rows pass would be repairing the bar to fit the
    data. The bar guards a deleter.
    """
    try:
        import vault_retro as _vr
    except Exception as e:
        return UNKNOWN, "vault_retro will not import (%s), so the proposal is ungraded" % str(e)[:60]
    import io as _io
    import json as _json
    import os as _os
    # ⚠⚠ THE PATH AUTHORITY, NOT A SECOND JOIN. Found by the post-ship review: this hardcoded
    # os.path.join(HERE, ...) while control_app resolves the ledger through TV_VAULT_LEDGER /
    # _fixture_root_for_state(). With either set, the row graded a file the register button would
    # never write — and a gate run reached into his REAL 7-row ledger instead of the fixture.
    # The comment above control_app's own definition says it outright: "Guard the PATH, not the
    # call site." [[feedback-fixtures-never-touch-live-data]]
    p = None
    try:
        import control_app as _ca
        p = getattr(_ca, "VAULT_LEDGER_PATH", None)
    except Exception:
        p = None
    if not p:
        p = _os.environ.get("TV_VAULT_LEDGER") or _os.path.join(HERE, "vault_accum.json")
    if not _os.path.isfile(p):
        # ⚠ NO STORE IS NOT A CLEAN BILL AND NOT A FAULT. Nothing has been accumulated yet.
        # ⚠⚠ AND IT NAMES THE PATH IT LOOKED AT. Raised by the second eye: the control_app import
        # above is wrapped in a bare except, so a broken import silently falls back to a DIFFERENT
        # path — which is exactly the bug this row was just fixed for. "Nothing is stored" and
        # "I looked in the wrong place" produce the same sentence unless the place is in it.
        return OK, ("no vault proposal is stored at %s, so there is nothing whose grading could "
                    "have drifted — an empty queue, not a measured agreement" % p)
    try:
        d = _json.load(_io.open(p, encoding="utf-8"))
    except Exception as e:
        return UNKNOWN, ("vault_accum.json could not be read (%s), so whether its rows still "
                         "clear today's bar is UNKNOWN — it is NOT 'they do'" % str(e)[:60])
    rows = (d.get("result") or {}).get("owned") if isinstance(d.get("result"), dict) else d.get("owned")
    rows = [r for r in (rows or []) if isinstance(r, dict)]
    if not rows:
        return OK, ("the stored proposal holds no OWNED rows, so nothing is being offered for "
                    "registration — an empty proposal, not a disagreement")
    bad = []
    for r in rows:
        try:
            # ⚠ gate() TAKES THE SIGHTING LIST, NOT THE ROW, and its verdict key is "pass", not
            # "ok". My first cut passed the row dict: iterating a dict yields its KEYS, so `ev`
            # filtered to [] and every row came back "no evidence at all" — a confident 0 of 7 that
            # was purely an instrument failure. The suspiciously clean number was the tell.
            # [[feedback-suspect-the-instrument]]
            # ⚠⚠ THE BARS ARE PASSED EXPLICITLY, and that is not decoration. `gate()`
            # declares them as DEFAULT ARGUMENTS (min_witnesses=KEEP_MIN_WITNESSES), and
            # Python binds a default ONCE at def time — so calling gate() bare grades
            # against the bar as it was when the module was imported, while the sentence
            # below quotes `_vr.KEEP_MIN_WITNESSES` as it is NOW. Those can differ, and a
            # row whose verdict and whose stated bar disagree is worse than no row.
            # Found by the gate for this file failing: the simulated bar move did not
            # reach the comparison at all. [[label-outlived-referent]]
            g = _vr.gate(r.get("witnesses") or [],
                         conf_floor=_vr.KEEP_CONF_FLOOR,
                         min_witnesses=_vr.KEEP_MIN_WITNESSES)
        except Exception as e:
            return UNKNOWN, ("the vault gate raised %s while re-grading the stored proposal, so "
                             "the comparison is unmeasured" % type(e).__name__)
        if not g.get("pass"):
            bad.append((r.get("name") or "?", g.get("why") or ""))
    n = len(rows)
    if not bad:
        return OK, ("all %d stored OWNED row(s) still clear today's bar (conf %.2f, %d witnesses) "
                    "— the proposal on screen and the rule that would accept it agree"
                    % (n, _vr.KEEP_CONF_FLOOR, _vr.KEEP_MIN_WITNESSES))
    return MISSING, ("%d of %d stored OWNED row(s) NO LONGER clear today's bar (conf %.2f, %d "
                     "witnesses) — the panel labels them corroborated and the current rule calls "
                     "them unsure; pressing register now HOLDS THESE BACK and names them (#246 — the "
                     "stored sweep is re-gated row by row), and files the rest. First: %s — %s"
                     % (len(bad), n, _vr.KEEP_CONF_FLOOR, _vr.KEEP_MIN_WITNESSES,
                        bad[0][0], bad[0][1][:110]))


def _main_locked_py(name, lane_lock=None):
    """#246 — the MAIN lock, asked on the console side from the SAME three sources the board joins. -> (bool, why)

    furniture (inventory_law) · the MAIN ledger (main_character.is_locked) · a d2r_laneLock row with his
    3 distinct sessions. The board's `_laneLockWhy` asks the same three, in the same order.
    """
    try:
        import inventory_law as _il
        if _il.is_locked(name):
            return True, "inventory furniture — locked by law"
    except Exception:
        pass
    try:
        import main_character as _mc
        ok, why = _mc.is_locked(name)
        if ok:
            return True, why
    except Exception:
        pass
    r = (lane_lock or {}).get(str(name or "").strip()) if isinstance(lane_lock, dict) else None
    if isinstance(r, dict) and len(r.get("sessions") or []) >= 3:
        return True, "seen in his %s in %d separate sessions" % (r.get("lane"), len(r.get("sessions") or []))
    return False, ""


_SHARED_STASH_RE_LINE = re.compile(r"var SHARED_STASH_RE = /(.+?)/([a-z]*);\n")


def _fold_piece(name):
    """A read name and a roster piece name, folded to one key: curly apostrophes straight, the trailing
    (slot) suffix off, lower case — the board's own _cnV fold."""
    s = str(name or "").replace("‘", "'").replace("’", "'").replace("`", "'")
    return re.sub(r"\s*\([^)]*\)\s*$", "", s).strip().lower()


def _vault_route_fn():
    """#246 review — WHERE THE WITNESSED LANE CAN FILE A NAME, from the board's own two facts. -> route(name)

    route(name) -> (routable, canonical): routable is False for a shared-stash name (suggestMule's ONE null —
    the door answers it 'no-home', so no press of register can ever file it), True otherwise, and None when the
    rule could not be read (UNKNOWN, never "routable"). canonical is the slot-suffixed set piece the lane files
    a bare piece under ("Tal Rasha's Horadric Crest" -> "... (helm)"), else the name itself.
    Each fact is READ from its one source, never copied: SHARED_STASH_RE out of bible.html, and the pieces
    out of tv/set_roster.json, which roster_sync GENERATES from bible.html's __allSets() and a law holds equal.
    [[copy-drift]] [[unknown-stays-unknown]]
    """
    shared = pieces = None
    try:
        with open(os.path.join(ROOT, "bible.html"), encoding="utf-8", errors="replace") as fh:
            found = _SHARED_STASH_RE_LINE.findall(fh.read())
        if len(found) == 1:
            body, flags = found[0]
            shared = re.compile(body, (re.I if "i" in flags else 0) | re.A)
    except Exception:
        shared = None
    try:
        with open(os.path.join(HERE, "set_roster.json"), encoding="utf-8") as fh:
            sets = (json.load(fh) or {}).get("sets") or {}
        pieces = {}
        for plist in sets.values():
            for p in plist or []:
                pieces[_fold_piece(p)] = p
    except Exception:
        pieces = None

    def route(name):
        nm = str(name or "").strip()
        canon = (pieces or {}).get(_fold_piece(nm), nm)
        if shared is None:
            return None, canon
        straight = nm.replace("‘", "'").replace("’", "'")
        return (not (shared.search(nm) or shared.search(straight))), canon
    route.readable = shared is not None and pieces is not None
    return route


def arm3_row_class(r, assign, route_fn, locked_fn, gate_fn, held_by_reset=None):
    """ONE stash row of the witness ledger, as arm 3 of the 'vault provenance' row classes it. PURE.

    ⚠ round-5 review (MED, reproduced) — THE JOINT'S TWO SIDES ASKED TWO FILTERS. corroborate's
    `a-reset-hold-is-not-a-register-prompt` counted on its LEFT every reset-held stash row the gate passes,
    while the doctor (RIGHT) reached the reset-held bucket only after these pre-filters — so a held row that
    routes to the SHARED stash (a Sunder charm), a rune tally row, or a locked name was counted left and
    skipped right: DISAGREE over a healthy board (left 3, right 1), the cried-wolf class. Both sides ask this
    one predicate now; only the RECORDS they hand it differ (backup snapshot vs live board).
    -> None (not a candidate: not an unfiled stash ITEM row, furniture, locked, or the gate does not pass)
       | 'no-mule' | 'route-unknown' | 'reset-held' | 'unfiled'
    """
    if not isinstance(r, dict):
        return None
    assign = assign if isinstance(assign, dict) else {}
    held_by_reset = held_by_reset if isinstance(held_by_reset, dict) else {}
    nm = str(r.get("name") or "").strip()
    if not nm or str(r.get("lane") or "").lower() != "stash" or nm in assign:
        return None
    if str(r.get("kind") or "item").lower() != "item":
        return None               # the lane files grail ITEMS; a rune / gem / material row is a tally, never a filing
    routable, canon = route_fn(nm)
    if canon in assign:
        return None               # filed under its slot-suffixed set-piece name — the lane's canonical form
    try:
        import inventory_law as _il2
        if not _il2.worth_registering(nm)[0]:
            return None           # furniture and consumables are never filed — not a gap
    except Exception:
        pass
    if locked_fn(nm)[0]:
        return None
    gv = gate_fn(r.get("witnesses") or [])
    if not gv.get("pass"):
        return None
    if routable is False:
        return "no-mule"          # the shared stash: no mule exists for it, so it is not a gap
    if routable is None:
        return "route-unknown"    # the rule could not be read: UNKNOWN, never counted either way
    if nm in held_by_reset or canon in held_by_reset:
        return "reset-held"       # rank 1: his reset's plan held it — said beside, never a gap
    return "unfiled"


def _arm3_defaults(lane_lock, locked_fn=None, route_fn=None, gate_fn=None):
    """The three predicates arm 3 runs with when the caller hands none — ONE place, so the joint's left side
    runs exactly the doctor's own (round-5 review, MED)."""
    locked_fn = locked_fn or (lambda n: _main_locked_py(n, lane_lock))
    route_fn = route_fn or _vault_route_fn()
    if gate_fn is None:
        import vault_retro as _vr
        gate_fn = lambda ev: _vr.gate(ev, _vr.KEEP_CONF_FLOOR, _vr.KEEP_MIN_WITNESSES)
    return locked_fn, route_fn, gate_fn


def vault_provenance_verdict(assign, prov, lane_lock, accum_rows, feeder, locked_fn=None, gate_fn=None,
                             route_fn=None, main_state=None, reset_held=None):
    """#246 W7 — THE HEART OF THE ONE DOOR: does every mule filing carry its witness? -> (status, why, counts)

    PURE — every input is handed in, so a law can drive each arm with a fixture and a sabotage.
      assign      d2r_muleAssign {name: home}          (the board's map)
      prov        d2r_vaultProv  {name: row}           (the witness beside each filing)
      lane_lock   d2r_laneLock   {name: {lane, sessions}}
      accum_rows  vault_accum.json 'owned' rows, or None when unreadable (UNKNOWN, never [])
      feeder      .read_names_feeder.json {runs, banked}, or None when unreadable
    Four answers, each its own arm:
      1. filings with NO witness row            — must be 0 (his false vault reads 173 here, honestly)
      2. MAIN-locked names sitting in a mule    — must be 0
      3. stash rows that CLEAR TODAY'S GATE and are not filed — the witnessed lane that cannot land
      4. the unattended feeder: banked vs runs  — reported beside, never the verdict alone
      route_fn    route(name) -> (routable, canonical) — _vault_route_fn() when not handed in
      main_state  main_character.locks_payload(), or None when the caller did not measure it
      reset_held  #41 rank 1 (2026-09-29): {name: why} — the rows the last full reset's evidence plan HELD (its
                  persisted receipt, d2r_vaultLastReset.heldNames), or None when no receipt could be read

    #41 rank 1 — A ROW HIS RESET HELD IS NOT A "PRESS REGISTER" PROMPT. Arm 3 told him to press register for
    rows that cleared the 2-look door while the reset's Wilson plan had just HELD them (under 10 visits) — advice
    that would undo the hold. Two admission bars, one vault: the row now says both facts beside, never as a gap
    ("held by your reset ... the 2-look door would file them on register"), and the joint
    `a-reset-hold-is-not-a-register-prompt` (corroborate) keeps that count honest.

    #246 review — arm 3 counts only rows the lane COULD file: a shared-stash name has no mule (the door refuses
    it 'no-home', so "press register" was advice that could never work) and is reported beside, never as a
    gap; a set piece filed under its slot-suffixed name IS filed. And arm 2's OK is only as wide as what locks:
    a MAIN ledger that locks nothing (every row under 3 sightings) with no 3-session lane lock measured
    NOTHING, so with filings in the mules the row is UNKNOWN — it never says "no MAIN item sits in a mule".
    """
    locked_fn, route_fn, gate_fn = _arm3_defaults(lane_lock, locked_fn, route_fn, gate_fn)
    assign = assign if isinstance(assign, dict) else {}
    prov = prov if isinstance(prov, dict) else {}
    # 2026-09-28 — an owned RECEIPT (kind 'owned', written by window._ownedAdd) says who put a name in `owned`;
    # it is never a filing witness, so a filing whose only row is a receipt still counts as unwitnessed here.
    prov = {k: v for k, v in prov.items() if not (isinstance(v, dict) and v.get("kind") == "owned")}
    filings = sorted(n for n, h in assign.items() if h and h != "__throwout")
    unwitnessed = [n for n in filings if n not in prov]
    in_mule = []
    for n in filings:
        h = assign.get(n)
        if h == "__keep":
            continue
        ok, why = locked_fn(n)
        if ok:
            in_mule.append((n, h, why))
    gate_unfiled, gate_known = [], accum_rows is not None
    gate_no_mule, gate_route_unknown, gate_reset_held = [], [], []
    held_by_reset = reset_held if isinstance(reset_held, dict) else {}
    _bucket = {"no-mule": gate_no_mule, "route-unknown": gate_route_unknown, "reset-held": gate_reset_held,
               "unfiled": gate_unfiled}
    for r in (accum_rows or []):
        cls = arm3_row_class(r, assign, route_fn, locked_fn, gate_fn, held_by_reset)
        if cls:
            _bucket[cls].append(str(r.get("name") or "").strip())
    # what the MAIN arm could see at all: the ledger's locks and every 3-session lane lock
    main_locks = main_tracked = None
    main_why = ""
    if isinstance(main_state, dict):
        _lk = main_state.get("locked")
        if main_state.get("ok") and isinstance(_lk, list):
            main_locks, main_tracked = len(_lk), main_state.get("tracked")
            main_why = str(main_state.get("blockedWhy") or "")
        else:
            main_why = str(main_state.get("why") or "the MAIN ledger could not be read")
    lane_locks = sum(1 for v in (lane_lock.values() if isinstance(lane_lock, dict) else [])
                     if isinstance(v, dict) and len(v.get("sessions") or []) >= 3)
    runs = banked = None
    if isinstance(feeder, dict):
        runs, banked = feeder.get("runs"), feeder.get("banked")
    counts = {"filings": len(filings), "witnessed": len(filings) - len(unwitnessed),
              "unwitnessed": len(unwitnessed), "mainInMule": len(in_mule),
              "gatePassingUnfiled": (len(gate_unfiled) if gate_known else None),
              "gatePassingNoMule": (len(gate_no_mule) if gate_known else None),
              "gatePassingRouteUnknown": (len(gate_route_unknown) if gate_known else None),
              "gatePassingResetHeld": (len(gate_reset_held) if gate_known else None),
              "gatePassingResetHeldNames": (list(gate_reset_held) if gate_known else None),
              "mainLedgerLocks": main_locks, "laneLocks": lane_locks,
              "feederRuns": runs, "feederBanked": banked}
    parts, bad = [], False
    if unwitnessed:
        bad = True
        parts.append("%d of %d mule filing(s) carry NO witness row (first: %s) — filed before the witness "
                     "rule; the fresh vault is your ruling, backed up first"
                     % (len(unwitnessed), len(filings), ", ".join(unwitnessed[:3])))
    if in_mule:
        bad = True
        parts.append("%d MAIN-locked name(s) sit in a mule (first: %s in %s — %s)"
                     % (len(in_mule), in_mule[0][0], in_mule[0][1], in_mule[0][2]))
    if gate_unfiled:
        bad = True
        parts.append("%d stash row(s) clear today's gate and are NOT filed (first: %s) — press register on "
                     "the vault card and the witnessed lane files them" % (len(gate_unfiled), ", ".join(gate_unfiled[:3])))
    if gate_reset_held:
        parts.append("%d gate-passing stash row(s) are held by your reset's evidence plan (under the Wilson bar: %s) — "
                     "the 2-look door would file them on register; held by your reset, not a gap (first: %s)"
                     % (len(gate_reset_held), str(held_by_reset.get(gate_reset_held[0]) or "WATCHED")[:60],
                        ", ".join(gate_reset_held[:3])))
    if gate_no_mule:
        parts.append("%d gate-passing stash row(s) belong in the shared stash — no mule exists for them, so they "
                     "are not a gap (first: %s)" % (len(gate_no_mule), ", ".join(gate_no_mule[:3])))
    if gate_route_unknown:
        parts.append("%d gate-passing stash row(s) are not filed and whether a mule exists for them is UNKNOWN — "
                     "the board's shared-stash rule or its set roster could not be read (first: %s)"
                     % (len(gate_route_unknown), ", ".join(gate_route_unknown[:3])))
    if not gate_known:
        parts.append("the stash ledger could not be read, so whether a witnessed row is waiting is UNKNOWN")
    if runs is None:
        parts.append("the unattended feeder's store could not be read — its record is UNKNOWN")
    else:
        parts.append("the unattended feeder has banked %s row(s) in %s run(s)" % (banked, runs))
    if bad:
        return MISSING, "; ".join(parts), counts
    if main_state is not None and filings and not main_locks and not lane_locks:
        # #246 review — THE MAIN ARM MEASURED NOTHING. His real ledger tracks 7 rows and locks 0 (each under 3
        # sightings), and this line read "no MAIN item sits in a mule" over the three filings the forensics names
        # as MAIN gear. Zero locks is not zero MAIN items. [[zero-needs-a-denominator]] [[unknown-stays-unknown]]
        src = (("the MAIN ledger locks 0 of %s tracked row(s)%s" % (main_tracked, (" — " + main_why) if main_why else ""))
               if main_locks == 0 else main_why)
        return UNKNOWN, ("all %d mule filing(s) carry their witness, but whether a MAIN item sits in a mule is "
                         "UNKNOWN — %s, and no lane lock has 3 sessions, so nothing could say which filing is "
                         "MAIN gear; %s" % (len(filings), src, "; ".join(parts))), counts
    if main_locks:
        main_say = ("no MAIN-locked name sits in a mule (the MAIN ledger locks %d of %s tracked row(s), %d lane "
                    "lock(s))" % (main_locks, main_tracked, lane_locks))
    elif lane_locks:
        main_say = ("no LOCKED name sits in a mule (%d lane lock(s); %s)"
                    % (lane_locks, ("the MAIN ledger locks 0 of %s" % main_tracked) if main_locks == 0
                       else (main_why or "the MAIN ledger was not read")))
    else:
        main_say = "no LOCKED name sits in a mule"
    return OK, ("all %d mule filing(s) carry their witness and %s; %s"
                % (len(filings), main_say, "; ".join(parts))), counts


def _evidence_ledger_path():
    return os.environ.get("TV_VAULT_LEDGER") or os.path.join(HERE, "vault_accum.json")


def _last_reset_receipt():
    """#41 rank 2 — the last reset's receipt, off the board's persisted d2r_vaultLastReset through the ONE board read.
    -> (receipt, before, after) | ("no-console", why) | ("none", why) | ("unreadable", why)"""
    got = _board_read()
    if not got:
        return "no-console", ("the console did not answer — nobody asked the board, so no reset receipt could be read: "
                              "cleared, rebuilt and held are UNKNOWN, not 0")
    if got.get("ok") is False:
        return "no-console", ("the board refused the read (%s), so no reset receipt could be read: cleared, rebuilt and held "
                              "are UNKNOWN, not 0" % str(got.get("why"))[:90])
    fs = got.get("fullStores")
    if not isinstance(fs, dict):
        return "no-console", ("the board read carried no stores, so no reset receipt could be read: cleared, rebuilt and held "
                              "are UNKNOWN, not 0")
    raw = fs.get("d2r_vaultLastReset")
    if raw is None:
        return "none", ("this board holds no reset receipt (d2r_vaultLastReset) — no reset has run here since receipts "
                        "were persisted, so cleared, rebuilt and held are UNKNOWN, not 0")
    try:
        rec = raw if isinstance(raw, dict) else json.loads(raw)
    except Exception:
        return "unreadable", "the board's reset receipt would not parse — UNKNOWN, not 0"
    if not isinstance(rec, dict):
        return "unreadable", "the board's reset receipt is not a receipt — UNKNOWN, not 0"
    before, after = rec.get("keepsBefore"), rec.get("keepsAfter")
    return rec, (before if isinstance(before, dict) else None), (after if isinstance(after, dict) else None)


def _check_the_vault_reset(receipt=None, before=None, after=None):
    """The last vault reset: cleared, kept, rebuilt, held.

    #41 rank 2 (2026-09-29): registered with no arguments, this row could never read a receipt — it
    was permanently UNKNOWN while two comments said it read one, and his real 09-27 reset left no
    trace. With no arguments it now reads the receipt the reset PERSISTS (d2r_vaultLastReset, with a
    digest of every kept store before the clears and after the rebuild) through the shared board
    read, and carries the reset's own time. No console, no receipt, or one that will not parse is
    UNKNOWN, not a report of 0 rebuilt. A kept store whose digest changed is named.

    REG-2335 (v3782) - this row also watches the items-only wipe (door vaultWipeItems): it never
    rebuilds, so it is judged like Reset assignments, on the stores it keeps (runes / gems / materials,
    set pieces, the chronicle) - a wipe that touched one of them reads MISSING here.
    """
    at = None
    if receipt is None and before is None and after is None:
        got0 = _last_reset_receipt()
        if isinstance(got0[0], str):
            return UNKNOWN, got0[1]
        receipt, before, after = got0
        at = receipt.get("at")
    import vault_evidence as _ve
    got = _ve.reset_receipt(receipt, before, after)
    if at:
        got = dict(got, why=("reset at %s (%s door) · " % (at, receipt.get("door") or "?")) + str(got.get("why") or ""))
    if got.get("notApplicable"):
        # Reset assignments never rebuilds: judged on the kept stores alone (vault_evidence.reset_receipt says so)
        return (OK if got.get("ok") else MISSING), got.get("why") or "Reset assignments never rebuilds · kept stores unchanged"
    if got.get("rebuilt") is None or got.get("held") is None:
        return UNKNOWN, got.get("why") or "the reset receipt could not be read"
    if got.get("touched") or got.get("unknown"):
        return MISSING, got.get("why") or "a kept store changed"
    # 2026-09-28 (Ledger fix round 2, finding B): the receipt's rebuiltFailed — a plan row the
    # board's door refused is named here, never a silent gap between rebuilt and held
    if got.get("refused") is None:
        return UNKNOWN, got.get("why") or "whether the door refused a plan row is UNKNOWN"
    if got.get("refused"):
        return MISSING, got.get("why") or "the door refused a plan row"
    return OK, got.get("why") or "kept stores unchanged"


def _check_the_evidence_tiers(path=None, root=None):
    """vault-body — how many items each evidence tier holds, and which cited pictures are gone.

    The count is vault_evidence.tier, corroborated by rebuild_plan on the same ledger. An
    unreadable ledger is UNKNOWN, never 0. A shelf that was not opened leaves the broken-link
    count UNKNOWN, never 0.

    2026-09-28 (Ledger P0) — the tiers are counted in VISITS, never frames (his §34.2 ruling),
    and the row says how many items the frame math filed above that — the retro flags. Those
    stay filed by his ruling, so a flag is reported, not a failure. [[unknown-stays-unknown]]
    """
    import vault_evidence as _ve
    if path is None and root is None:
        # 2026-09-28 second eye (v3520, 7fcb836c): the heart registers this row with NO arguments, so root
        # stayed None, the shelf was never opened, and the row said UNKNOWN for ever while 20 of the 27
        # pictures his ledger cites were gone from the Mac's shelf. The live call opens the real shelf.
        root = os.environ.get("TV_HIST") or os.path.join(HERE, "frames", "hist")
    got = _ve.tier_census(path if path is not None else _evidence_ledger_path())
    if not got.get("ok"):
        return UNKNOWN, got.get("why") or "the evidence tiers could not be read"
    if got.get("disagree"):
        return MISSING, got.get("why") or "the tier table and the witness ledger disagree"
    # ══ #41 rank 4 (2026-09-29) — A LOSS NOTHING CAN REPAIR IS NOT A RED THAT HIDES THE NEXT ONE ═══
    # This returned MISSING with a 180-character frame list the moment any cited picture was gone —
    # before the tier counts and the retro flags were ever printed. On his shelf 21 of 29 cited frames
    # went with 13 reels drained between 08-30 and 09-10, BEFORE the keep landed (vault_evidence.
    # KEEP_LANDED_MS), so the row was red for ever, the whole Ledger 3.0 report never reached the
    # eagle, and a new loss would have hidden inside it. Now every gone frame is dated by its reel's
    # tombstone: gone before the keep is BASELINE (said beside an OK, with the count); gone after it is
    # MISSING and names the item it stands on; a loss no tombstone dates is MISSING as UNKNOWN-when.
    # The counts, the tiers and the retro flags are always printed. [[unknown-stays-unknown]]
    pics = _ve.picture_losses(path if path is not None else _evidence_ledger_path(), root)
    bad_pics = None
    if pics.get("n") is None:
        pic = "evidence links whose picture is gone: UNKNOWN"
    elif pics["n"]:
        after, undated, base = pics.get("after") or [], pics.get("undated") or [], pics.get("baseline") or []
        pic = "pictures gone %d of cited %d" % (pics["n"], pics.get("cited") or 0)
        if base:
            pic += " (%d before the keep landed — a baseline nothing can repair)" % len(base)
        if after:
            # round-5 review (LOW): the keep's commit time is a lower bound — said, never pretended exact
            bad_pics = "%d cited picture(s) lost AFTER the keep landed (%s): %s" % (
                len(after), _ve.KEEP_LANDED_WHY,
                "; ".join("%s (%s, reel %s)" % (r["item"], r["frame"], r.get("reel") or "?") for r in after[:4]))
        if undated:
            bad_pics = ((bad_pics + "; ") if bad_pics else "") + (
                "%d cited picture(s) gone and no tombstone dates the loss — when is UNKNOWN: %s" % (
                    len(undated), "; ".join("%s (%s)" % (r["item"], r["frame"]) for r in undated[:4])))
    else:
        pic = "pictures gone 0 of cited %d" % (pics.get("cited") or 0)
    if got.get("retro") is None:
        retro = "retro flags: UNKNOWN"
    elif got["retro"]:
        _rheld = got.get("retroHeldNames") or []
        _kept = [n for n in (got.get("retroNames") or []) if n not in _rheld]
        retro = ("retro flags %d (%s) — filed above what their visits earn, kept filed by his "
                 "ruling" % (got["retro"], ", ".join(_kept[:4]) or "none kept"))
        if _rheld:
            # finding B (round 2): a flagged row no visit saw is HELD, never claimed as kept
            retro += ("; %d of them held — no visit saw it (%s)" % (len(_rheld), ", ".join(_rheld[:4])))
    else:
        retro = "retro flags 0"
    # #51 — THE SAME COUNT, SPLIT BY WHAT EACH ITEM IS. His ask: magic (blue) and rare (gold)
    # items tallied like uniques. The split is the census's own byRarity (vault_evidence.rarity_of
    # per item, never a second count here); a name whose rarity nothing could tell is counted
    # under "rarity UNKNOWN", never folded into white. [[unknown-stays-unknown]]
    line = ("tiers by visit, never frame: WATCHED %d · PROVEN %d · HARDENED %d · unreadable %d · %s · %s · %s"
            % (got["watched"], got["proven"], got["hardened"], got["unknown"],
               _ve.rarity_tally_say(got.get("byRarity")), retro, pic))
    # ══ #41 rank 19 (2026-09-29) — WHAT THE TIERS OWE, AND WHEN A LOOK LAST LANDED, ON THE EAGLE LINE ══
    # The counts above said 15 WATCHED and stopped: which items, how many looks each still needs, and
    # whether any look has landed lately were published nowhere. This is the lane's owed and lastTs
    # (vault_evidence.tiers_watch — the ONE reader; control_app.evidence_tiers_state quotes the same
    # dict). The age is measured from the newest LOOK the ledger carries, never from this tick.
    line += " · " + _tiers_lane_clause(_ve.tiers_watch(path if path is not None else _evidence_ledger_path()))
    if bad_pics:
        return MISSING, bad_pics + " · " + line
    return OK, line


def _tiers_lane_clause(lane):
    """The owed / last-look half of the 'evidence tiers' row, from the lane's own dict. -> str

    `lastTs` is the newest look's own time, so the age is the age of the EVIDENCE; None reads UNKNOWN,
    never "just now". `owed` None (a row could not be measured) says UNKNOWN and what was counted.
    [[stale-reading]] [[unknown-stays-unknown]]"""
    if not isinstance(lane, dict) or lane.get("on") is None:
        return "owed UNKNOWN · last look UNKNOWN (%s)" % str((lane or {}).get("say") or "the lane could not be read")[:120]
    say = str(lane.get("say") or "")
    head = say.split(" · last look")[0] if say else "owed UNKNOWN"
    ts = lane.get("lastTs")
    if isinstance(ts, (int, float)) and not isinstance(ts, bool):
        age_h = max(0.0, (time.time() * 1000.0 - float(ts)) / 3600000.0)
        last = "last look %.1fh ago" % age_h
    else:
        last = "last look UNKNOWN (no look carries a time)"
    return head + " · " + last


def _check_the_ledger3_trail_can_be_drawn():
    """ledger3 — can the per-session extraction record be drawn for every sealed reel on the shelf?

    2026-09-29 (#58, Ledger 3.0 first slice). The record (tv/ledger3.py, GET /api/ledger3/session)
    joins the journal ring, the chronicle book, the vault witness ledger, the shelf, the river
    stamps, the survey and the tombstones for ONE reel. The link that breaks silently is the
    JOURNAL: the ring rotates by size while the shelf drains by count, so a sealed reel can still
    sit on the shelf with its reader's rows gone — footage he still has whose trail cannot be
    drawn. That is MISSING, named per reel. An unreadable journal or shelf is UNKNOWN, never
    "0 trails". The row also prints the agreement census — the reader's names against the vault
    sweep's witnesses, side by side, never averaged — so a sweep that stops witnessing what the
    reader names shows up here before it shows up as an empty vault. [[unknown-stays-unknown]]

    PERIODIC on merit: it reads the whole ring and joins ~32 reels (measured 0.40 s on his shelf,
    read-only, 2026-09-29) and the cheap tick already sits at 8.9 s of its 9 s budget; its answer
    moves only as the ring rotates or the shelf drains, so hourly loses nothing.
    """
    import control_app as _ca
    import ledger3 as _l3
    stores = _ca._ledger3_stores()
    got = _l3.census(stores)
    if not got.get("ok"):
        return UNKNOWN, got.get("why") or "the extraction record could not be drawn — UNKNOWN"
    ag = got.get("agreement") or {}
    line = ("%s · reader-vs-vault names: both %s · reader only %s · vault only %s"
            % (got.get("why"), ag.get("both"), ag.get("journalOnly"), ag.get("vaultOnly")))
    if stores.get("unknown"):
        line += " · UNKNOWN sides: " + "; ".join(str(u)[:90] for u in stores["unknown"][:3])
    if got.get("noTrail"):
        return MISSING, ("%d sealed reel(s) on the shelf have NO journal rows — the trail for footage he "
                         "still has cannot be drawn (%s) · %s"
                         % (len(got["noTrail"]), ", ".join(got["noTrail"][:4]), line))
    return OK, line


def _check_vault_provenance():
    """#246 W7 — 'vault provenance': the one door, watched. Reads the board ONCE (the shared tick read),
    the stash ledger and the feeder's store; judges with vault_provenance_verdict. UNKNOWN when the board
    cannot be asked — never OK on a board nobody read."""
    st, why, _c = _vault_provenance_counts()
    return st, why


def _vault_provenance_counts():
    """The 'vault provenance' row with its counts: (status, why, counts | None). #41 rank 1 — the corroborator's
    `a-reset-hold-is-not-a-register-prompt` reads the counts off this very verdict (the doctor's side of the joint)."""
    got = _board_read()
    if not got:
        return UNKNOWN, "the console did not answer — nobody asked the board, so nothing is known", None
    if got.get("ok") is False:
        return UNKNOWN, "the board refused the read: %s" % str(got.get("why"))[:90], None
    fs = got.get("fullStores")
    if not isinstance(fs, dict):
        return UNKNOWN, "the board read carried no stores, so its mule map could not be judged", None

    def _j(k, dflt):
        v = fs.get(k)
        if v is None:
            return dflt
        if isinstance(v, (dict, list)):
            return v
        try:
            return json.loads(v)
        except Exception:
            return None
    assign, prov, lane = _j("d2r_muleAssign", {}), _j("d2r_vaultProv", {}), _j("d2r_laneLock", {})
    if assign is None or prov is None:
        return UNKNOWN, "the board's mule map or its witness store would not parse — UNKNOWN, not clean", None
    # #41 rank 1 — the rows his last full reset HELD, off its persisted receipt (the same board read)
    reset_held = None
    _rc = _j("d2r_vaultLastReset", None)
    if isinstance(_rc, dict) and _rc.get("door") == "vaultClearHistory" and isinstance(_rc.get("heldNames"), list):
        reset_held = {str(n): "held by your reset at %s" % (_rc.get("at") or "?") for n in _rc["heldNames"] if n}
    rows = None
    try:
        import control_app as _ca
        p = getattr(_ca, "VAULT_LEDGER_PATH", None) or os.path.join(HERE, "vault_accum.json")
        if os.path.isfile(p):
            d = json.load(open(p, encoding="utf-8"))
            rows = (d.get("result") or {}).get("owned") if isinstance(d.get("result"), dict) else d.get("owned")
            rows = [r for r in (rows or []) if isinstance(r, dict)]
        else:
            rows = []
    except Exception:
        rows = None
    feeder = None
    try:
        import control_app as _ca2
        fp = _ca2._rnf_path()
        feeder = json.load(open(fp, encoding="utf-8")) if os.path.isfile(fp) else {"runs": 0, "banked": 0}
    except Exception:
        feeder = None
    # #246 review — what the MAIN arm can see: the ledger's locks and their denominator, or why it could not be read
    try:
        import main_character as _mc
        main_state = _mc.locks_payload()
    except Exception as e:
        main_state = {"ok": False, "locked": None,
                      "why": "main_character would not answer (%s) — nothing is known about MAIN gear" % type(e).__name__}
    st, why, _counts = vault_provenance_verdict(assign, prov, lane, rows, feeder, main_state=main_state,
                                                reset_held=reset_held)
    return st, why, _counts


def _row_says_who(row):
    """A provenance row that names who or what filed the item — a filing witness or an owned receipt."""
    return isinstance(row, dict) and bool(str(row.get("source") or "").strip())


def owned_provenance_verdict(owned, prov):
    """2026-09-28 — 'a vault item with no provenance'. PURE. -> (status, why, counts)

    His words, looking at Grief and Plague: "where is the ledger proof of these two items? i cant find it". Every
    name in d2r_owned must carry a d2r_vaultProv row that says who or what filed it — a mule filing's witness, or
    the RECEIPT window._ownedAdd writes at every owned door. MISSING names them; UNKNOWN when either store could
    not be read (never "0 missing" about a board nobody read). [[unknown-stays-unknown]]
    """
    if owned is None or prov is None:
        return UNKNOWN, "the board's owned list or its provenance store would not read — UNKNOWN, not clean", {}
    if not isinstance(owned, list) or not isinstance(prov, dict):
        return UNKNOWN, "the board's owned list or its provenance store is not the shape this row grades", {}
    names = sorted(set(n.strip() for n in owned if isinstance(n, str) and n.strip()))
    missing = [n for n in names if not _row_says_who(prov.get(n))]
    receipts = sum(1 for n in names if isinstance(prov.get(n), dict) and prov[n].get("kind") == "owned")
    counts = {"items": len(names), "missing": len(missing), "receipts": receipts,
              "filings": len(names) - len(missing) - receipts}
    if not names:
        return OK, "the vault holds nothing yet — 0 items, nothing to account for", counts
    if missing:
        more = (" (+%d more)" % (len(missing) - 6)) if len(missing) > 6 else ""
        return MISSING, ("%d of %d vault item(s) have no provenance — nothing recorded who or what filed them: %s%s"
                         % (len(missing), len(names), ", ".join(missing[:6]), more)), counts
    return OK, ("every one of the %d vault item(s) says who filed it (%d filing witness(es) · %d owned receipt(s))"
                % (len(names), counts["filings"], receipts)), counts


def _check_vault_items_carry_provenance():
    """2026-09-28 — reads the board's persisted stores through the ONE shared board read, like 'vault provenance'."""
    got = _board_read()
    if not got:
        return UNKNOWN, "the console did not answer — nobody asked the board, so nothing is known"
    if got.get("ok") is False:
        return UNKNOWN, "the board refused the read: %s" % str(got.get("why"))[:90]
    fs = got.get("fullStores")
    if not isinstance(fs, dict):
        return UNKNOWN, "the board read carried no stores, so its vault could not be judged"

    def _j(k, dflt):
        v = fs.get(k)
        if v is None:
            return dflt
        if isinstance(v, (dict, list)):
            return v
        try:
            return json.loads(v)
        except Exception:
            return None
    st, why, _c = owned_provenance_verdict(_j("d2r_owned", []), _j("d2r_vaultProv", {}))
    return st, why


def _check_a_read_left_no_picture(rows=None, hist=None, now_ms=None):
    """2026-09-28 — 'a read left no picture': every read that NAMED something in the last 24 h has its frame on disk,
    and when one does not, the row names who took it (the recorder's reap record, a tombstone) or says it was never
    written (the disk floor). The journal, the shelf and the records are read here; the judging is
    read_pictures.verdict. UNKNOWN when the journal or the shelf cannot be read. [[unknown-stays-unknown]]"""
    import read_pictures as _rp
    if rows is None:
        try:
            import control_app as _ca
            rows, jwhy = _ca._kai_journal_rows(want_why=True)
            if jwhy:
                rows = None
        except Exception:
            rows = None
    if hist is None:
        try:
            import frame_authority as _fa
            hist = _fa._hist_dir(None)
        except Exception:
            hist = None
    if not hist or not os.path.isdir(hist):
        return UNKNOWN, "the frame shelf is not on this machine, so whether any read kept its picture is unknown"
    reads = _rp.named_reads(rows, now_ms) if rows is not None else None
    present = _rp.locator(hist)
    reaps = _rp.load_jsonl(os.path.join(_rp.root_of(hist), _rp.REAPS))
    refusals = _rp.load_jsonl(os.path.join(_rp.root_of(hist), _rp.REFUSALS))
    tombs = _rp.load_tombstones(hist)
    st, why, _c = _rp.verdict(reads, present, reaps, tombs, refusals)
    return st, why


def _check_reel_custody(src=None):
    """2026-09-29 (#55, first slice) — 'reel custody': every reel this PC has a record of (on the shelf or in the
    tombstone ledger) has a chain of custody its stores AGREE on. The five stores each hold one fragment
    (river_stamp, retro_triage, chronicle_swept, vault_swept, reel_tombstones — plus the recorder's own reap and
    refusal records), keyed three ways; reel_custody joins them and this row shouts when two writers contradict
    each other about one reel (a tombstone claiming seals the seal stores never wrote, a ledger removal the shelf
    still shows, a TOMBSTONE stamp with no ledger row). UNKNOWN when any of those stores could not be read — a
    chain with an unreadable link is partial, and partial is not clean. The judging is reel_custody.doctor; this
    only hands the answer through. [[unknown-stays-unknown]] [[heart-first]]"""
    try:
        import reel_custody as _rc
        return _rc.doctor(src=src)
    except Exception as e:
        return UNKNOWN, ("the custody record could not be assembled (%s) — whether every reel's custody chain "
                         "holds is UNKNOWN, never clean" % type(e).__name__)


def _check_the_river_has_an_outlet():
    """★ THE RIVER COULD NOT FINISH A REEL, AND THE STATION THAT SAYS SO READ 0 FOR ITS WHOLE LIFE.

    Konyo's architecture: *"it just flows and eats session reels regardless of the route it come
    from initially… it just gets spit out properly"*, and *"there is no loop or worry because it
    gets eventually tombstoned and deleted and wiped completely. only the data and information gets
    extracted before hand."*

    `river_walk.py` recorded the weld in its own note: the ONLY writer of a tombstone row lives
    inside the deleter (`reel_retention.apply_plan` -> `_tombstone`), so a reel could not be
    recorded as CLOSED OUT without being REMOVED — and removal is behind the arming lock, which is
    False and stays False. Being finished and being deleted were one event. Measured on his shelf
    at the time: 40 reels, ROUTED 0, TOMBSTONE 0.

    ⚠ THIS ROW REPORTS FLOW, NOT REACHABILITY. Whether ROUTED can be reached at all is a structural
    fact and belongs in a gate, where it can be proven red — `test_the_river_has_an_outlet.py` does
    that. A doctor row that tried to assert reachability from live counts would grade a quiet shelf
    as a broken outlet every time nothing happened to qualify.

    ⚠⚠ IT ALWAYS PUBLISHES THE DECLINED COUNT. 12 of his reels sit at CAPTURE, which owes
    "CAPTURE, then ROUTE" — they cannot be closed out and never will be by a lane. Reporting only
    the routable number would say "0 waiting" on a shelf where 12 reels are permanently stuck, and
    that reads as done. [[zero-needs-a-denominator]]
    """
    try:
        import reel_router as _rr
    except Exception as e:
        return UNKNOWN, "reel_router will not import (%s), so the outlet is unmeasured" % str(e)[:60]
    try:
        rep = _reel_route_read()
    except Exception as e:
        return UNKNOWN, "the router raised (%s) — unmeasured, not clean" % str(e)[:60]
    if not rep.get("ok"):
        return UNKNOWN, ("the router did not answer (%s), so nothing here was measured"
                         % str(rep.get("why") or "no reason given")[:80])
    # ⚠ A STAMP STORE THAT COULD NOT BE READ MAKES ROUTED 0 A GUESS, NOT A COUNT. `route()`
    # publishes `outletReadable` precisely so this row does not have to infer it from a zero.
    if not rep.get("outletReadable", False):
        return UNKNOWN, ("the stamp store could not be read, so how many reels have been closed "
                         "out is UNKNOWN and specifically not zero — %s"
                         % str(rep.get("outletWhy") or "")[:90])
    counts = rep.get("counts") or {}
    routed = int(counts.get("ROUTED") or 0)
    shelf = int(rep.get("shelf") or 0)
    try:
        import reel_route_lane as _lane
        p = _lane.plan(rep)
    except Exception as e:
        return UNKNOWN, ("the route lane will not import (%s), so who is waiting to be closed out "
                         "is unmeasured" % str(e)[:60])
    if not p.get("ok"):
        return UNKNOWN, ("the route lane could not plan (%s)" % str(p.get("why") or "")[:80])
    waiting = len(p.get("route") or [])
    declined = len(p.get("declined") or [])
    # ⚠ v3020 — was "(REG-340)", which cites the CHARACTER-name ruling at an ITEM-name problem.
    tail = (" · %d at CAPTURE owe a capture change first — hover coverage, so the tooltips that "
            "carry item names are filmed — and no lane can move them" % declined) if declined else ""
    # ⚠⚠ v2770 — ASK THE DRIVER, NOT ONLY THE QUEUE. Until v2770 nothing CALLED the lane, so this
    # row could only ever say "they have not been closed out" without being able to say WHY — and
    # the answer was "because no code anywhere runs it". Now the triage tick drives it, and a
    # waiting queue means something different depending on whether the driver is alive:
    #   driver never ran   -> the loop is dead or the wiring broke. That is the finding.
    #   driver ran recently-> the reels arrived since, and the next tick will take them.
    # Collapsing those two into one sentence is how a dead loop reads as a busy one.
    # ⚠ THE WIRE, NEVER a second import of the console. The console runs as __main__, so importing
    # it here builds another module whose route-lane counters stay at zero. A reel waiting to be
    # closed out then read as a process too young to have ticked, for the whole life of a lane
    # that was running, and the RAISED and HAS NEVER RUN sentences could not be reached. The
    # serving process publishes routeLane on /api/river. No pulse is UNKNOWN: the young-process
    # sentence is a measurement, not the shape of a miss.
    # [[the-unjoined-end]] [[feedback-suspect-the-instrument]]
    pulse = None
    if waiting:
        riv = _get("/api/river", timeout=8)
        got = riv.get("routeLane") if isinstance(riv, dict) else None
        if isinstance(got, dict) and got.get("ok") is not False and "runs" in got:
            pulse = got
    if waiting and pulse is None:
        return UNKNOWN, ("%d of %d reel(s) can be closed out RIGHT NOW, and the route lane's "
                         "pulse is not on the wire, so whether anything is driving them is "
                         "UNKNOWN — not a young process, and not a lane that has never run. "
                         "ROUTED holds %d%s" % (waiting, shelf, routed, tail))

    # ⚠ v3297 — runs==0 used to CONFLATE THREE OPPOSITE FACTS: a lane the roster stood down
    # by design (TV_STUB), a process younger than the sleep-first 90s tick, and a tick that
    # raises upstream of the runs counter every round for ever. A dead loop, a deliberate
    # absence and a failing loop are different findings and must not share a sentence — the
    # guest board read a stood-down driver as "nothing is driving the river" 2026-09-18.
    # A bool is an int in Python, and True must not read as one run.
    _runs = pulse.get("runs") if waiting else 0
    drv_runs = _runs if isinstance(_runs, int) and not isinstance(_runs, bool) else None
    if waiting and drv_runs is None:
        return UNKNOWN, ("%d of %d reel(s) can be closed out RIGHT NOW, and the route lane's "
                         "run count could not be read, so whether anything is driving them is "
                         "UNKNOWN. ROUTED holds %d%s" % (waiting, shelf, routed, tail))
    if waiting and not drv_runs:
        head = ("%d of %d reel(s) can be closed out RIGHT NOW and have not been"
                % (waiting, shelf))
        _att = pulse.get("attempts")
        att = _att if isinstance(_att, int) and not isinstance(_att, bool) else None
        if pulse.get("stoodDown") is True:
            return MISSING, ("%s — the route lane's driver is STOOD DOWN in this world (TV_STUB "
                             "harness): it will never run here BY DESIGN, which is not a dead "
                             "loop. ROUTED holds %d%s" % (head, routed, tail))
        if att is None:
            return UNKNOWN, ("%s — the triage tick's attempt count is not on the pulse, so a "
                             "young process, a failing tick and a lane that has never run cannot "
                             "be told apart. UNKNOWN. ROUTED holds %d%s" % (head, routed, tail))
        if att and pulse.get("raised"):
            return MISSING, ("%s — the triage tick has ATTEMPTED %d time(s) in this process and "
                             "RAISED before reaching the route lane (last: %s): a FAILING driver, "
                             "not a dead one. ROUTED holds %d%s"
                             % (head, att, str(pulse.get("raised"))[:90], routed, tail))
        if not att:
            _every = pulse.get("everyS")
            every = _every if isinstance(_every, int) and not isinstance(_every, bool) else None
            if every is None:
                return MISSING, ("%s — no triage tick has been ATTEMPTED yet in this process "
                                 "(the first-tick sleep was not published), so 'never ran' may "
                                 "only mean the process is young. ROUTED holds %d%s"
                                 % (head, routed, tail))
            return MISSING, ("%s — no triage tick has been ATTEMPTED yet in this process (the "
                             "loop sleeps %ss before its first tick), so 'never ran' may only "
                             "mean the process is young. ROUTED holds %d%s"
                             % (head, every, routed, tail))
        return MISSING, ("%s, and the route lane HAS NEVER RUN in this process — nothing is "
                         "driving the river. ROUTED holds %d%s" % (head, routed, tail))
    if waiting:
        at = pulse.get("at")
        age = (int(time.time() - float(at))
               if isinstance(at, (int, float)) and not isinstance(at, bool) else None)
        return MISSING, ("%d of %d reel(s) are waiting to be closed out; the route lane last ran "
                         "%s and reported: %s. ROUTED holds %d%s"
                         % (waiting, shelf,
                            ("%ds ago" % age) if age is not None else "at an unrecorded time",
                            str(pulse.get("why") or "nothing"), routed, tail))
    if routed:
        return OK, ("%d of %d reel(s) closed out and none waiting — the river has an outlet and "
                    "it is being used%s" % (routed, shelf, tail))
    return OK, ("nothing currently qualifies to be closed out: no reel is at a station that owes a "
                "route outright%s. The outlet is reachable (proven in the gate), it simply has "
                "nothing to carry" % tail)


def _check_the_river_joints_carry():
    """★ v2761 — THE RIVER'S OWN DIAGNOSIS REACHES A SCREEN FOR THE FIRST TIME.

    Konyo: *"fix the gaps. connect it all to the heart of the console"*.

    MEASURED before writing this: `tv/river.py` measures all ELEVEN joints of the pipeline, names
    the first blockage in a sentence, and is imported by EXACTLY ONE FILE — its own test.
    `grep -rl 'import river' tv/*.py` -> test_the_river_carries_a_stamp.py. Neither corroborate.py
    nor console_doctor.py has ever asked it anything.

    ⚠ AND THERE IS ALREADY A ROW CALLED "the river" — it reads `reel_router` and answers WHERE
    REELS ARE STATIONED. That is a different question from WHETHER THE JOINTS CARRY. The console
    watched position and was blind to flow, and the two look similar enough that the gap survived.
    A sentence like "blocked at 'surface' — 0 of 14,034 sightings carry one" has never been on a
    screen he looks at. [[the-unjoined-end]] [[plumbing-with-no-tap]]

    ⚠ DRY IS NOT AUTOMATICALLY A FAILURE, and this must not cry wolf. Some joints are dry because
    the work genuinely has not been done and he can act; `gate` was dry because nothing NEW was
    proposed. So the row reports the CENSUS and names the first blockage, and grades on whether
    the river's own first-blockage sentence exists — never on a bare count.
    """
    try:
        import river as _rv
    except Exception as e:
        return UNKNOWN, "river.py will not import (%s), so no joint could be measured" % str(e)[:60]
    # ⚠ river.py's API is trace() + summary(rows) — NOT survey()/run(). My first cut guessed those
    # two names behind a hasattr, so the check would have returned UNKNOWN for ever while looking
    # like a wired watcher. Caught by grepping the module instead of trusting the guess.
    # [[feedback-suspect-the-instrument]]
    try:
        joints = _rv.trace()
        rep = _rv.summary(joints)
    except Exception as e:
        return UNKNOWN, "the river survey raised (%s) — unmeasured, not clean" % str(e)[:60]
    if not joints or not isinstance(rep, dict):
        return UNKNOWN, "the river reported no joints at all, so nothing here was measured"
    by = {}
    for j in joints:
        by[str(j.get("state"))] = by.get(str(j.get("state")), 0) + 1
    n = len(joints)
    dry = by.get("DRY", 0)
    unk = by.get("UNKNOWN", 0)
    # ⚠⚠ v3267 — THE THIRD CONSUMER OF A NEW STATE WORD, AND THE ONE THAT WOULD HAVE LIED.
    # river.py learned UNBUILT this version (a joint whose PRODUCER has never been switched on,
    # as opposed to a join that is broken). This row counted only DRY and UNKNOWN, so the moment
    # that word shipped, the `slot` joint would have dropped out of both buckets and this would
    # have returned OK, "all 11 river joint(s) carry" — over a joint that has never carried
    # anything in its life. Twice today a new verdict word went green at a consumer nobody
    # joined; this is the third and it was found BEFORE shipping by grepping for the old word.
    # [[the-unjoined-end]] [[regression-guard]]
    ub = by.get("UNBUILT", 0)
    say = str(rep.get("say") or "").strip()
    first = rep.get("firstBlockage")
    if dry:
        return MISSING, ("%d of %d joint(s) DRY%s — %s"
                         % (dry, n, (", %d unmeasured" % unk) if unk else "",
                            say or ("first blockage: %s" % first)))
    if unk:
        # ⚠⚠ v3269 — AND THIS SENTENCE SWALLOWED THE ONE v3267 ADDED. The branches are ordered
        # unk-before-ub, which is right (unmeasured outranks unbuilt), but the sentence named only
        # the unmeasured ones — so on his live tree, with `gate` UNKNOWN and `slot` UNBUILT, the
        # row read "1 of 11 joint(s) could not be measured" and the unbuilt joint was INVISIBLE.
        # That is the quiet corner v3267's own comments warn about, built one branch above the
        # guard that was supposed to prevent it. A precedence rule decides which fact LEADS, never
        # which facts are REPORTED. [[the-unjoined-end]] [[zero-needs-a-denominator]]
        return UNKNOWN, ("%d of %d joint(s) could not be measured%s"
                         % (unk, n,
                            ("" if not ub else
                             # ⚠ v3270 — the cross-family eye: "a further 2 HAS never been built"
                             # is ungrammatical at ub>=2. Cosmetic, real, and its twin below had
                             # the same shape — so both agree the verb with the count now.
                             "; a further %d %s never been built or switched on — %s"
                             % (ub, "has" if ub == 1 else "have", say or "see the river"))))
    if ub:
        # ⚠ NOT MISSING. Nothing is broken and nothing here is mine to fix.
        # ⚠⚠ v3270 — AND THE REMEDY IS NOT "A DECISION HE HAS NOT MADE". v3267 wrote that and it
        # was already false: he RULED AGAINST the hover autopilot on 2026-09-09 ("i decided MINI
        # automatic isnt needed.. the whole button surgically remvoe it"). v2856 removed the
        # button, lamp, mode block, CSS and consent chip; v2857 gutted the handlers (REG-823),
        # which now refuse by name. Re-confirmed by him 2026-09-17: the recording options are
        # ON AIR, MINI and SHADOW READER — AUTOMATIC is not among them. So `slot` is not awaiting
        # authorisation, it is PERMANENTLY UNBUILT by his decision, and a comment inviting someone
        # to switch it on is an invitation to undo a ruling.
        # [[label-outlived-referent]] [[design-is-fine-until-he-says]]
        # Reporting it red would
        # train him to ignore a red; reporting it green would hide a joint that cannot carry.
        return UNKNOWN, ("%d of %d joint(s) carry; %d %s never been built or switched on — %s"
                         % (n - ub, n, ub, "has" if ub == 1 else "have",
                            say or "see the river"))
    return OK, "all %d river joint(s) carry" % n


def _check_the_console_UI_has_not_faulted():
    """Has the console reported a fault about ITSELF recently?

    ⚠ v2228 — THE EAGLE COULD NOT SEE THE SCREEN, so a display-side failure was invisible to every
    check here. He found the black-screen stage himself, twice, and reported it with screenshots
    while nothing in the tree knew anything was wrong. His instruction: "watch dog it and eagle
    eye it."

    The console now POSTs /api/ui_fault when it heals itself, and this reads that record. A fault
    that healed is still a fault — the point is that it stops being HIS job to notice.

    REG-2321 (v3778) - this is also the watcher for the shell tab route: a board tab that cannot
    open after its one reload records `shell-route-gave-up`, and it lands here by kind.
    """
    try:
        import control_app as ca
        rows, why = ca.ui_faults_recent(24)
    except Exception as e:
        return UNKNOWN, "the fault log could not be read: %s" % str(e)[:80]
    if rows is None:
        return UNKNOWN, why or "the fault log is unreadable — which is not the same as no faults"
    if not rows:
        return OK, "the console has reported no fault about itself in 24h"
    import collections
    by = collections.Counter(r.get("kind") for r in rows)
    top = ", ".join("%s x%d" % (k, n) for k, n in by.most_common(3))
    newest = rows[-1]
    return MISSING, ("the console healed itself from %d fault(s) in 24h (%s) — most recently: %s. "
                     "It recovered, but this is the class he had to report by hand."
                     % (len(rows), top, str(newest.get("why"))[:110]))



def _check_the_vault_can_say_what_it_proves():
    """Can the vault's proof chip be answered at all, and does the answer say anything?

    ⚠⚠ WHY THIS IS A HEART ROW. v3247 put a `⚖ N` chip beside each vault locker saying how many of
    its items the ledger can prove. Its failure mode is SILENCE BY DESIGN: when the ask fails the
    chip is absent, which is correct on the public site and indistinguishable — on HIS console —
    from a route that 404s, a ledger that will not parse, or a bar nothing clears. Every one of
    those renders exactly like "no console here". A gate can only say the code is present.
    [[the-unjoined-end]] [[zero-needs-a-denominator]]

    ⚠ THREE OUTCOMES. An unreadable ledger is UNKNOWN, not clear. A ledger that parses and proves
    NOTHING is also UNKNOWN rather than OK — "nothing earned admission" and "nobody could look"
    are different facts and the chip renders them identically.
    """
    # ⚠ ASK THE CONSOLE, the way every sibling here does. This first called
    # `vault_proven_names()` directly and raised NameError: console_doctor is its own module and
    # cannot see control_app's namespace. Measured immediately — "the vault proof door raised
    # NameError" — because the check reports its own failure rather than assuming success.
    # ⚠ `_post`, not `_get`: the route takes a body (the bar travels on the request).
    r = _post("/api/vault_proven", {})
    if r is None:
        return UNKNOWN, ("the console did not answer /api/vault_proven, so whether the chip can "
                         "be answered at all is unmeasured — not clear. On a console started "
                         "before v3247 the route does not exist yet; restart it.")
    if not isinstance(r, dict) or not r.get("ok"):
        return UNKNOWN, ("the vault ledger could not be read (%s), so how many of his items carry "
                         "a proof is UNKNOWN — the chip would simply be absent, which looks the "
                         "same as having no console"
                         % str((r or {}).get("why") or "no reason given")[:110])
    n = int(r.get("provenN") or 0)
    rows = int(r.get("ledgerRows") or 0)
    if not rows:
        return UNKNOWN, ("the vault ledger holds no rows at all, so there is nothing to prove "
                         "from — an empty chip here is not a clean bill of health")
    if not n:
        return UNKNOWN, ("%d ledger row(s) and NOT ONE clears the %d-witness bar, so every locker "
                         "would show an empty chip — which reads exactly like a missing console"
                         % (rows, int(r.get("bar") or 2)))
    return OK, ("%d of %d ledger row(s) clear the %d-witness bar, so the chip has something to "
                "say" % (n, rows, int(r.get("bar") or 2)),
                ["proven: " + ", ".join(x["name"] for x in (r.get("proven") or [])[:6])])


def _check_the_shelf_tabs_are_alive():
    """Is the SHELF's tab row actually made of his reels, right now — or is it empty and quiet?

    ⚠⚠ WHY THIS IS A HEART ROW AND NOT ONLY A GATE, and it is the whole reason it exists.
    v3202/v3204 shipped the station chips with a source-level law behind them, and that law can
    only ever answer "the code that would build the chips is present". It cannot answer the
    question he actually asks when he opens the door: ARE THERE TABS THERE. The bar hides itself
    when nothing is stamped — deliberately, because an empty row would read as "no stations
    exist" — so the failure mode is SILENT BY DESIGN: a broken join renders exactly like a
    console that has not been asked yet, and every gate stays green through it.
    [[the-unjoined-end]] [[zero-needs-a-denominator]]

    So this asks the RIVER, which is the same source the chips are built from, and compares the
    two populations. A shelf whose river reports stamped reels while no station can be named is
    the unjoined end, and it is invisible from the source.

    ⚠ THREE OUTCOMES, NEVER TWO. An unreachable console is UNKNOWN. A river that answers with
    nothing stamped is UNKNOWN — not clean — because "nothing to show" and "failed to show it"
    are different facts and only one of them is his problem.
    """
    riv = _get("/api/river")
    if not isinstance(riv, dict) or not riv.get("ok"):
        return UNKNOWN, ("the river did not answer, so whether the shelf has tabs at all is "
                         "unmeasured — not clear")
    lanes = ((riv.get("lanes") or {}).get("lanes")) or []
    if not lanes:
        return UNKNOWN, "the river answered with no lanes, so there is nothing to build tabs from"
    stamped, named = 0, []
    for l in lanes:
        by = l.get("byStation") or {}
        for st, n in by.items():
            if n:
                stamped += n
                named.append(st)
    if not stamped:
        return UNKNOWN, ("the river has stamped no reel at any station, so an empty tab row is "
                         "the honest answer and not a defect")
    labels = riv.get("labels") or {}
    unlabelled = sorted({st for st in named if st not in labels})
    if unlabelled:
        # a station the label map does not name would render as a raw key beside his words
        return MISSING, ("%d reel(s) sit at station(s) the label map does not name (%s), so the "
                         "tab row would print a raw key beside his own vocabulary"
                         % (stamped, ", ".join(unlabelled[:4])),
                         ["stations with reels: " + ", ".join(sorted(set(named)))])
    return OK, ("%d reel(s) across %d station(s), every one named in his vocabulary"
                % (stamped, len(set(named))),
                ["tabs he would see: "
                 + ", ".join(sorted({labels.get(st, st) for st in named}))])


def _check_no_panel_is_dark_with_its_content_in_hand():
    """A panel that HAS rows and is not on screen — the failure a green suite cannot see.

    WHY THIS IS A DOCTOR CHECK AND NOT ONLY A TEST. Konyo reported it twice: "daily tasks and
    chronicle tallys are not rendering here in this section", then "black space but image
    tooltips are still rendering". Both sightings were real and BOTH TIMES THE DATA WAS FINE.
    The roster was built, the tooltip drawn from the same rows worked, and the panel holding
    them carried a stale `hidden` attribute because the repaint memo returned before the
    un-hide. Every DOM-text assertion passed, because the text existed — it was never painted.

    So the honest place to catch it is the running page, which the UI heartbeat already is. The
    page classifies each panel itself (empty / shown / DARK) and this reads that verdict back.

    ⚠ THREE OUTCOMES, NEVER TWO. A console that has never beaten is UNKNOWN, not healthy — the
    same rule ui_beat_age() states about its own None. And a console older than v2336 reports no
    panels at all, which is also UNKNOWN and must never read as "all clear".
    [[unknown-stays-unknown]] [[regression-guard]]
    """
    st = _get("/api/status") or {}
    ub = st.get("uiBeat") if isinstance(st.get("uiBeat"), dict) else None
    if not ub:
        return UNKNOWN, "the console did not report a heartbeat, so nothing is known about his screen"
    if not ub.get("n"):
        return UNKNOWN, "no console has ever checked in — that is a headless run, not a healthy screen"
    panels = ub.get("panels")
    if not isinstance(panels, dict) or not panels:
        return UNKNOWN, ("this console is older than v2336 and does not report its panels — "
                         "unknown, not clear")
    dark = sorted([k for k, v in panels.items() if v == "DARK"])
    if dark:
        return MISSING, ("%s built its rows and is NOT on screen — the panel is dark with its "
                         "content in hand, which is the class he had to report by hand twice "
                         "(REG-415)" % ", ".join(dark))
    shown = sorted([k for k, v in panels.items() if v == "shown"])
    empty = sorted([k for k, v in panels.items() if v == "empty"])
    return OK, ("every panel holding content is on screen (%d shown%s%s)"
                % (len(shown), (": " + ", ".join(shown)) if shown else "",
                   ("; %d legitimately empty" % len(empty)) if empty else ""))



# `playwright test` reached the way a script actually invokes it. `playwright install` and any
# sentence merely NAMING playwright must not match — see browser_suites_among.
# #171 (REG-2481) — AND THE WINDOWS SPELLINGS OF THE SAME INVOCATION, because Task Scheduler is judged by this ONE rule
# too: `npx.cmd`, a quoted `"...\npx.cmd" playwright test`, `node_modules\.bin\playwright(.cmd) test`.
_RUNS_A_BROWSER_SUITE = re.compile(
    r"(?:npx(?:\.cmd|\.exe)?[\"']?\s+|yarn(?:\.cmd)?[\"']?\s+|pnpm(?:\.cmd)?[\"']?\s+|bunx(?:\.exe)?[\"']?\s+"
    r"|node_modules[\\/]\.bin[\\/]|bin[\\/])playwright(?:\.cmd|\.exe)?[\"']?\s+test\b")
#: a path a command line names: POSIX (/...) or Windows (C:\..., C:/...)
_ABSOLUTE_PATH = re.compile(r"^(?:/|[A-Za-z]:[\\/])")


def _paths_named_in(command):
    """Every absolute path `command` names - quoted (a Windows path with spaces) or bare. -> [path]"""
    found = [q.strip() for q in re.findall(r'"([^"]+)"', command)] + command.replace('"', " ").split()
    return [t for t in found if _ABSOLUTE_PATH.match(t)]


def reaches_a_browser_suite(command):
    """#171 (REG-2481) — THE ONE RULE both schedulers are judged by. -> bool

    Does `command` - with the first 200 KB of every script it names by an absolute path - INVOKE a browser suite?
    launchd hands it a plist's arguments, Task Scheduler a task's 'Task To Run'. One rule, so a fix to it (the
    routine_Q lesson: an invocation, not a mention) reaches both. Bounded: 200 KB per file."""
    blob = command
    for tok in _paths_named_in(command):
        if os.path.isfile(tok):
            try:
                with open(tok, encoding="utf-8", errors="replace") as fh:
                    blob += "\n" + fh.read(200000)
            except OSError:
                pass
    # ⚠ AN INVOCATION, NOT A MENTION. The first cut matched the bare substring "npx
    # playwright" and immediately accused routine_Q — a WATCHDOG whose only crime is the
    # alert string `run \`npx playwright install\``. It monitors the suites; it does not run
    # one. A guard that reads prose about the thing as the thing is the same defect that has
    # blinded three source guards in this repo already. [[feedback-comments-vs-code]]
    return bool(_RUNS_A_BROWSER_SUITE.search(blob))


def browser_suites_among(labels, agents_dir=None):
    """Which of `labels` have a launchd plist whose command reaches a BROWSER suite. -> [label]

    Split out of the check so it can be driven by a fixture. A guard whose only input is his real
    machine can never be seen RED on purpose, and one that has not been seen red is measuring
    nothing. [[regression-guard]]

    Bounded: 200 KB per file. An unbounded sweep of this shape once pinned a core for 28 hours.
    """
    agents_dir = agents_dir or os.path.join(os.path.expanduser("~"), "Library", "LaunchAgents")
    guilty = []
    for lbl in labels:
        p = os.path.join(agents_dir, lbl + ".plist")
        if not os.path.isfile(p):
            continue
        # ⚠ `open`, not `io.open`: this module never imports io, so io.open raised NameError —
        # which the bare `except Exception: continue` below swallowed, making the scan return []
        # for EVERY job. The check would have shipped answering "no browser suite here" forever,
        # whatever was actually scheduled: a guard that can only say OK. Caught only because the
        # fixture demanded it be seen RED. And the except is narrowed for the same reason — an
        # OSError is a plist we cannot read; a NameError is a bug wearing its clothes.
        try:
            with open(p, encoding="utf-8", errors="replace") as fh:
                plist = fh.read(200000)
        except OSError:
            continue
        # #171 - the plist's arguments, judged by the one rule Task Scheduler's commands are judged by
        if reaches_a_browser_suite(plist.replace("<string>", " ").replace("</string>", " ")):
            guilty.append(lbl)
    return guilty


#: #171 (REG-2481) — how long one Task Scheduler listing answers for. The question changes only when somebody schedules
#: a job, and `schtasks /v` costs seconds on a Windows PC, so the every-tick row reads it at most hourly - and says how
#: old the listing it judged was. [[stale-reading]]
_TASKS_TTL_S = 3600
#: ...and a listing that could NOT be taken is asked again only after this long: a schtasks that hangs under his game
#: (tasklist did, REG-1414) must cost one bounded wait per eagle tick, never one per row asked.
_TASKS_FAIL_TTL_S = 600
_TASKS = {"at": None, "text": None, "err": None}


def _schtasks_csv():
    """Task Scheduler's own verbose listing, as CSV. -> text. Raises when it cannot be asked.
    Through git_quiet's door: on Windows the child gets CREATE_NO_WINDOW + SW_HIDE, never a console over his game."""
    import git_quiet as _gq
    r = _gq.run([_spawnable("schtasks"), "/query", "/fo", "CSV", "/v"], close_fds=False,
                capture_output=True, timeout=15)
    if r.returncode != 0:
        raise OSError("schtasks exited %s" % r.returncode)
    return _decode_listing(r.stdout or b"")


def _decode_listing(raw):
    """REG-2481 round 2 - a Windows tool's piped bytes -> text. A UTF-16 listing (a BOM, or the NUL every ASCII
    character carries in UTF-16-LE) is decoded as UTF-16 first: read as utf-8/mbcs it 'decodes' into text with a NUL
    between every letter, no 'Task To Run' header, and an UNKNOWN row that never ends. Otherwise utf-8, then the
    console's OEM page, then the ANSI page (both exist only on Windows), then utf-8 with replacement."""
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff") or b"\x00" in raw[:200]:
        try:
            return raw.decode("utf-16")
        except UnicodeDecodeError:
            pass
    for enc in ("utf-8", "oem", "mbcs"):
        try:
            return raw.decode(enc)
        except (LookupError, UnicodeDecodeError):
            continue
    return raw.decode("utf-8", "replace")


def windows_tasks_from_csv(text):
    """`schtasks /query /fo CSV /v` -> [(task name, its 'Task To Run')], one per task. Raises ValueError when no
    'Task To Run' column can be found - a listing this check cannot read is UNKNOWN, never an empty schedule."""
    import csv as _csv
    import io as _io
    tasks, seen, cols = [], set(), None
    for row in _csv.reader(_io.StringIO(text)):
        if not row:
            continue
        if "Task To Run" in row:                       # the header, repeated once per task folder
            cols = (row.index("TaskName") if "TaskName" in row else 1, row.index("Task To Run"))
            continue
        if cols is None or len(row) <= max(cols):
            continue
        name, cmd = row[cols[0]].strip(), row[cols[1]].strip()
        if (name, cmd) not in seen:
            seen.add((name, cmd))
            tasks.append((name, cmd))
    if cols is None:
        raise ValueError("no 'Task To Run' column in the listing (a Windows in another language?)")
    return tasks


def _ntpath_base(p):
    """The last part of a path in either OS's spelling (C:\\Users\\<name>\\...\\grok.exe -> grok.exe)."""
    return str(p).replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]


def _venue_on_windows(query=None, now=None):
    """#171 (REG-2481) — the venue row on Windows: Task Scheduler, judged by the one rule. -> (state, why)
    `query` is the listing seam (a law hands in its fixture CSV); None reads Task Scheduler, at most hourly."""
    now = time.time() if now is None else now
    try:
        if query is not None:
            text, age = query(), 0.0
        elif _TASKS["text"] is not None and now - _TASKS["at"] < _TASKS_TTL_S:
            text, age = _TASKS["text"], now - _TASKS["at"]
        elif _TASKS["err"] is not None and now - _TASKS["at"] < _TASKS_FAIL_TTL_S:
            return UNKNOWN, ("Task Scheduler could not be read %d min ago (%s) and is asked again within %d min, so "
                             "whether a browser suite is scheduled on this PC is UNKNOWN"
                             % (int((now - _TASKS["at"]) // 60), _TASKS["err"], _TASKS_FAIL_TTL_S // 60))
        else:
            try:
                text, age = _schtasks_csv(), 0.0
                tasks = windows_tasks_from_csv(text)
            except Exception as e:
                # REG-2481 round 2 - a listing that would not PARSE is a failed read too: cached on the short TTL,
                # never kept as a good listing for an hour
                _TASKS.update(at=now, text=None, err="%s: %s" % (type(e).__name__, str(e)[:90]))
                raise
            _TASKS.update(at=now, text=text, err=None)
        tasks = windows_tasks_from_csv(text)
    except Exception as e:
        return UNKNOWN, ("Task Scheduler could not be read (%s: %s), so whether a browser suite is scheduled on "
                         "this PC is UNKNOWN" % (type(e).__name__, str(e)[:90]))
    if not tasks:
        return UNKNOWN, ("Task Scheduler listed no task at all - every Windows schedules its own, so the listing "
                         "is the suspect and the venue is UNKNOWN")
    guilty = sorted({name for name, cmd in tasks if reaches_a_browser_suite(os.path.expandvars(cmd))})
    when = "read just now" if age < 60 else "read %d min ago" % int(age // 60)
    if guilty:
        return MISSING, ("%d scheduled task(s) run a BROWSER suite on this PC instead of on GitHub: %s. They "
                         "have CI twins; a local copy only adds heat and starves the push gate (REG-416) - "
                         "Task Scheduler, %s" % (len(guilty), ", ".join(guilty[:6]), when))
    # a task with several actions shows "Multiple actions" in place of its commands: unseen, so never judged clean.
    # Windows' own folder (\Microsoft\) schedules the OS's work, never a suite of ours.
    unseen = sorted({name for name, cmd in tasks if cmd.strip().lower() == "multiple actions"
                     and not name.lower().startswith("\\microsoft\\")})
    if unseen:
        return UNKNOWN, ("%d scheduled task(s) hold several actions Task Scheduler's listing does not show (%s), so "
                         "whether they run a browser suite here is UNKNOWN - Task Scheduler, %s"
                         % (len(unseen), ", ".join(unseen[:6]), when))
    return OK, ("no scheduled task runs a browser suite here \u2014 all %d Task Scheduler task(s) were judged by the "
                "same rule as launchd's jobs ('Task To Run' and the scripts it names, %s), and the suites stay on "
                "GitHub" % (len({n for n, _c in tasks}), when))


def _check_no_browser_suite_is_scheduled_on_this_mac():
    """Is any scheduled job running a BROWSER suite on his laptop? They belong on GitHub.

    Konyo's standing order, given six times: the browser suites run in CI, never on his Mac.
    On 2026-08-31 that order had been quietly broken for an unknown length of time and NOTHING
    could see it. Five launchd jobs — routine_H, I, J, K and L — each fired locally at the same
    minute as its own GitHub twin (`routine-i-playwright.yml` is `cron: '0 6 * * *'`, which is
    09:00 IDT, exactly what `ai.konyo.d2r.routine_I.plist` was set to). Someone had already made
    `.disabled` COPIES of all five, intending to switch them off, and never unloaded the live
    ones. Both copies sat side by side in ~/Library/LaunchAgents for months.

    WHAT IT COST, measured the morning it was found: eight chrome-headless-shell processes, three
    of them at 132%, 99% and 96% CPU at once on a 10-core machine, load average 8.75. He reported
    it as "my pc is hot and kinda laggy". It also blocked every push that morning — the pre-push
    hook bounds test_control at 600s, and a saturated machine cannot finish it in 600s, so two
    ships died with "⏱ test_control HUNG" and the cause looked like a test problem.

    A duplicated job is invisible in the worst way: BOTH copies work. CI is green, the local run
    is green, and the only symptom is heat. So the guard cannot ask "does it pass" — it has to
    ask WHERE IT RUNS. [[test-venue]] [[feedback-generalize-fixes]]

    ⚠ Bounded on purpose: at most 60 jobs, and only the first 200 KB of any script is read. An
    unbounded sweep of this shape once held a core at 99% for 28 hours on this same machine.
    """
    import subprocess as _sp
    _os = _this_os()
    if _os.startswith("win"):
        return _venue_on_windows()     # #171 (REG-2481) - Task Scheduler, judged by the same rule
    if _os != "darwin":
        return UNKNOWN, ("this check knows launchd (macOS) and Task Scheduler (Windows), and this machine is "
                         "neither, so it cannot speak for it")
    try:
        out = _sp.run([_spawnable("launchctl"), "list"], capture_output=True, text=True,
                      close_fds=False, timeout=10)
    except Exception as e:
        return UNKNOWN, "launchctl could not be asked: %s" % str(e)[:70]
    if out.returncode != 0:
        return UNKNOWN, "launchctl refused to list the jobs, so the venue is unknown"
    labels = []
    for ln in out.stdout.split("\n")[1:]:
        parts = ln.split("\t")
        if len(parts) >= 3 and parts[2].startswith(("ai.konyo", "com.konyo")):
            labels.append(parts[2].strip())
    labels = sorted(set(labels))[:60]
    if not labels:
        return OK, "no konyo job is scheduled on this machine at all"
    guilty = browser_suites_among(labels)
    if guilty:
        return MISSING, ("%d scheduled job(s) run a BROWSER suite on this Mac instead of on "
                         "GitHub: %s. They have CI twins; a local copy only adds heat and "
                         "starves the push gate (REG-416)" % (len(guilty), ", ".join(guilty)))
    return OK, ("no scheduled job runs a browser suite here \u2014 all %d are python or "
                "non-browser, and the suites stay on GitHub" % len(labels))

def _check_the_engines_CORROBORATE_each_other():
    """Do the engines agree with EACH OTHER, not merely with themselves?

    ⚠ v2228 — THE GAP THE OTHER TWENTY CHECKS CANNOT SEE. Every check above asks whether ONE engine
    is well. Every serious defect found on 2026-08-28 was a pair of numbers that were each correct
    and wrong TOGETHER, and not one of them could have been caught by asking either side alone:

        19 vs 2      the vault watchdog against reel_retention — seventeen unnecessary paid sweeps,
                     three of them over test fixtures
        1263 vs 403  the shadow ledger against the item universe — arithmetically impossible, and it
                     had already crossed the threshold that says "the record is worth a decision"
        157 vs 7     two payload fields both named `owned`
        36 vs 30     the sweep memory against the disk — nearly six read-records deleted as ghosts

    His words: "the system needs an eagle eye corroborator, the engines all communicating."

    tv/corroborate.py holds the invariants and NEVER writes, never averages, and never picks a side.
    UNKNOWN on either side is UNKNOWN here, never agreement.
    """
    try:
        sys.path.insert(0, HERE)
        import corroborate as _co
        st, say = _co.verdict()
    except Exception as e:
        return UNKNOWN, "the corroborator could not run: %s" % str(e)[:90]
    if st == _co.DISAGREE:
        return MISSING, say
    if st == _co.UNKNOWN:
        return UNKNOWN, say
    return OK, say


# ══ v2277 — THE HEALTH ENGINE, FOLDED INTO THE ONE EAGLE EYE ═══════════════════════════════════
#
# Konyo asked for "a system that does red/green flag us... one unit system engine locked in".
# The first cut of that was a SEPARATE module with its own CLI and its own four-state vocabulary —
# which would have been the FIFTH thing on this machine implementing "report, never repair, and
# never call an unmeasured thing fine". That is [[copy-drift]] exactly: one method in five places,
# four of which he would have to know to run.
#
# So `health_engine` keeps the CHECKS (it is unit-testable in isolation and every law in it is
# sabotage-proven) and this file keeps the SURFACE. Same pattern as "the other doctors": the eagle
# eye CALLS rather than re-implements. One rail, one payload, one place he looks.
#
# ⚠ THE STATE MAP LOSES A DISTINCTION AND THAT IS DELIBERATE. health_engine separates WARN from
# BLOCKED; this rail has only OK / MISSING / UNKNOWN, and adding a fourth state here would ripple
# through the healer's recheck map, the icon table and every consumer of /api/eagle. The severity
# survives in the DETAIL string, which is the part he actually reads. What must NOT be lost is
# UNKNOWN, and it is not: it maps to itself.
#: ⚠ ONE REPORT PER TICK, NOT FOUR. Each adapter would otherwise re-run the whole engine, and
#: `armed_migration` reads the 6MB bible.html — so four flags cost four full-file reads on a rail
#: that runs on a ten-minute timer at every console boot. The v2080 scar was exactly this shape:
#: two correct fixes that together put 17 seconds into the boot path. Short TTL, so a human
#: pressing the button twice still gets a fresh answer. [[two-fixes-broke-each-other]]
_health_cache = {"active": False, "rep": None}


def _health_report():
    import health_engine as HE
    if _health_cache["active"] and _health_cache["rep"] is not None:
        return _health_cache["rep"]
    # v2277 — HAND IT THE REAL BOARD READ. Without this the board_join flag is UNKNOWN for ever,
    # and a flag that can only ever say one thing is furniture, not a check.
    rep = HE.report(board=_board_read())
    if _health_cache["active"]:
        _health_cache["rep"] = rep
    return rep


def _clip(x, n):
    t = str(x)
    return t if len(t) <= n else t[:n - 1] + "\u2026"


def _health(check_id):
    """One health_engine check, in this rail's vocabulary. -> (state, detail)"""
    def run():
        try:
            import health_engine as HE
        except Exception as e:
            return UNKNOWN, "health_engine will not import: %s" % str(e)[:90]
        try:
            row = [r for r in _health_report()["rows"] if r["id"] == check_id]
        except Exception as e:
            return UNKNOWN, "the health engine raised: %s" % str(e)[:90]
        if not row:
            # a check that vanished must not read as a check that passed
            return UNKNOWN, "the health engine no longer reports '%s'" % check_id
        r = row[0]
        detail = r["line"]
        if r["evidence"]:
            # ⚠ ELLIPSIS, NOT A BARE CUT. The first cut printed "stamped-somewhere=T" — a
            # truncated True that reads as a value in its own right, which is exactly the shape
            # of a right number under a word that stopped being true. [[label-outlived-referent]]
            detail = "%s  [%s]" % (detail, "; ".join(_clip(x, 110) for x in r["evidence"][:2]))
        return ({HE.OK: OK, HE.WARN: MISSING, HE.BLOCKED: MISSING,
                 HE.UNKNOWN: UNKNOWN}.get(r["state"], UNKNOWN), detail)
    return run


#: ══ v2284 — WHOSE PROBLEM IS IT? ═══════════════════════════════════════════════════════════════
#:
#: Konyo, reading "4 need you": "4 need me? make sure to verify and fix what needs me for real".
#:
#: Measured the same minute — of the three the rail was counting against him, TWO were mine:
#:   extraction lanes  a code defect (#75): the vault lane cannot seal "examined, nothing here",
#:                     so it holds reels for ever. No amount of clicking fixes that.
#:   board join        a code defect (#76): _BOARD_WIN is assigned in a CHILD PROCESS the server
#:                     can never read. Also not his to fix.
#:   shadow gate       genuinely his — the Wilson rule and the live gate disagree on 38 of 401
#:                     names, and which rule to adopt is a judgement nobody else can make.
#:
#: A rail that bills him for my bugs teaches him the number is noise, and then the one line that
#: really is his gets skimmed with the rest. [[label-outlived-referent]]
#:
#: ⚠ THIS IS NOT A MUTE BUTTON. A check named here still renders, at its real state and colour —
#: it simply stops inflating the count of things HE can act on, and is listed under its own
#: heading with the task that owns it. Anything not named here counts as his, so a new check is
#: his by default and has to be argued out rather than in.
#: ── v3307 (#62) — RED ON PURPOSE IS NOT WAITING ON HIM ──────────────────────────────────────
#: HIS STANDING RULE, 2026-09-18: "WAITING ON YOU MEANS ACTION IS NEEDED FROM HIM RIGHT NOW. Not
#: 'was red once'. Not 'might need looking at'... If nothing is actually required of him, it does
#: not belong in the count he acts on." And: a count that mixes the two "trains him to stop reading
#: it — which is the same failure as a gate that is always red."
#:
#: MEASURED on his live console 2026-09-18: needsYou=9, and two of the nine were rows we had
#: already CLOSED as not-defects, months of ruling ago. They were billing him for design.
#:
#: ⚠ SAME SEMANTICS AS MINE BELOW, DELIBERATELY — it renders, at its real state and colour, and
#: simply stops inflating the count. NOT a mute button. A row removed is a row nobody can reopen.
#:
#: ⚠⚠ AND THE ONE THAT IS DELIBERATELY *NOT* HERE: 'river joints'. It is red for a STATE-DEPENDENT
#: reason — "blocked at 'prune' — the planner's own reading: NOTHING is safe to delete yet", which
#: the planner itself finishes with "and that is an answer, not a failure". By-design TODAY and
#: genuinely his the day something IS safe to delete. A static entry would silence it permanently,
#: including when it becomes real — turning the rule into the mute button this comment forbids.
#: That one needs the CHECK to answer conditionally, which is a different and smaller job.
BY_DESIGN = {
    "end routes reachable":
        "#29 — a state display that is RED ON PURPOSE. 11 of 19 reels are dead-ended BY the "
        "end-route rules, with numbers; the row exists to show the shape, not to ask for a fix.",
    "the river":
        "#30 — an exact subset of #29 with the same by-design exemptions. Closed as NOT A DEFECT "
        "after measuring that every reel it names is held by a rule that is working.",
}

MINE = {
    # #41 rank 16 (REG-1560) — a row of their planner's tooltip that ours does not compose is my composition
    # defect, and a receipt the page has moved from is my lane's to re-measure; nothing here is his to rule on.
    "their tooltip rows":
        "#41 rank 16 — the tooltip composition is generated from HIS install and judged against their planner's "
        "measured text; a row that is not theirs, or a stale receipt, is my work. He cannot act on a wrong line "
        "in a hover box except by trusting it.",
    # ⚠⚠ v3321 — SIX MORE, AND HIS OWN RULING IS WHAT DEMANDS IT. #35: "WAITING ON YOU means
    # action needed FROM HIM RIGHT NOW". MEASURED on his live console 2026-09-18, the panel
    # headed WAITING ON YOU carried EIGHT rows and `owner_of` answered "you" for every one —
    # while exactly ONE of them was his. He read the panel and asked "this is the missing on me?"
    #
    # A column that cries for him on seven rows he cannot act on is the same defect as a gate
    # that is always red: he stops reading it, and the one row that IS his goes with it.
    #
    # ⚠ NOT A MUTE BUTTON, same semantics as the two above: each still renders, at its real state
    # and colour. What changes is only whose name is on it. A row removed is a row nobody can
    # reopen. [[regression-guard]] [[feedback-contradiction-is-the-finding]]
    "the seed was checked against his board":
        "#159 — drift between the shipped seed and his board is a bake owed, and baking (plus "
        "re-reading the three spec constants it moves) is my work, not a decision he makes.",
    "two eyes compared":
        "#188 — two model families disagreeing about his screen IS the finding, exactly "
        "like 'engines corroborate': which eye is right is not knowable from the pair alone, "
        "and whether they were asked the same question is my work. A stale comparison is "
        "mine too: the evidence stopped arriving, and finding out why is not his errand.",
    "engines corroborate":
        "#81 — two engines disagreeing IS the finding, and the check says so itself: 'the one "
        "that is wrong is not knowable from the pair alone'. He cannot arbitrate a pair neither "
        "side can settle; joining them is my work.",
    "console UI faults":
        "#24 — its own sentence is 'the console healed itself from N fault(s) in 24h ... It "
        "recovered'. A thing that already repaired itself is a report, not an errand.",
    "ledger provenance":
        "#71 — the row carries its own named fix ('publish the provenance on the board POST too, "
        "and per ledger'). A defect that names its own patch is mine by definition.",
    "footage has a reel":
        "#80 — an unsealed recording no sweep can reach. `orphan_fold.py` shows the plan; "
        "running it is my job, not a decision he makes.",
    # v3378 (#28) — MINE, and it is the same territory as "names banked" just below: a river
    # printing owed work its own engine contradicts is a wiring defect with a named fix, not a
    # decision he can make. Nothing here asks him to authorise or rule on anything.
    # v3379 (#128) — MINE. A console that counts and cannot name is a wiring defect with a
    # named fix; there is nothing here for him to rule on or authorise.
    # v3380 — MINE. A browser launched without its own session is a wiring defect with a named
    # fix; there is nothing here for him to rule on or authorise.
    # v3381 — MINE. An unbounded pipe read is a wiring defect with a named fix.
    # v3384 — MINE. A refusal that names no action is a wiring defect with a named fix.
    "a look keeps its evidence":
        "v3386 - discarding an answer the caller already handed over is a wiring defect. "
        "The fix is code and it is mine.",

    "a present machine has a fresh last-seen":
        "v3390 - the beacon write condition is code. The fix is mine.",

    "a tally agrees with its own ledger verdict":
        "v3389 - sealing the tally verdict and rendering it is code. The fix is mine.",

    "the eye asks for every code extension":
        "v3388 - the pathspec the second eye hands git is code. The fix is mine.",

    "a presence reading names its door":
        "v3387 - joining the two presence stores and rendering both ages is code. The fix "
        "is mine.",

    "a fleet row identifies its machine":
        "v3385 - a label that cannot tell two machines apart is a wiring defect. The fix "
        "is code and it is mine.",

    "a fleet refusal names an action":
        "v3384 — forwarding the peer version and preferring the actionable reason is code. "
        "The fix is mine.",

    "a worker read has a deadline":
        "v3381 — a subprocess pipe read with no deadline is a wiring defect. The fix is code "
        "and it is mine.",

    "no browser is launched unreaped":
        "v3380 — a launcher that can outlive its timeout is a wiring defect. The fix is code "
        "and it is mine.",

    "fleet can name what it counts":
        "#128 — a ledger publishing a count and no list is a cut hand-over, not a decision. "
        "The fix is code and it is mine.",

    "picker census":
        "#41 rank 22 — a picker offering other than what its own database holds is a wiring defect "
        "on that PC's page (its list function or its rail), and a PC that reports no census is a "
        "build to update. The fix is code and it is mine.",

    "river owes what its engine says":
        "#28 — the river re-derived a verdict extract_gap had already given, and disagreed with "
        "it on one reel. Forwarding a value the printer already puts on the row is my work; "
        "there is nothing here for him to rule on.",

    "names banked":
        "#28 — names were READ and none are banked. The check itself states 'no paid read is "
        "owed here', so there is nothing for him to authorise; the banking lane is mine to widen.",
    "stage shows the dom":
        "#24 — 'a stale composite, which every rect/content guard reports as success'. He is not "
        "the detector [[visual-regression-detector]]; a guard that reports success over blank "
        "cells is my defect to fix.",

    "item facts captured":
        "#60 — capturing what the reader already SEES is MY job. He asked for garbage vs\n"
        "HIGH QUALITY and named socketed bases; a row that drops sockets cannot answer it,\n"
        "and no price he could supply would help.",
    "capture root live":
        "#115 — following the seat when it moves where it writes is MY job. He cannot act\n"
        "on a detector that spent 7.5 days reporting FROZEN off an abandoned folder, and\n"
        "the failure was silent: nothing errored, it simply answered about the wrong one.",
    "fault evidence":
        "#24 — a recorder that destroys its own evidence before writing the row is MY\n"
        "defect. He reported the black stage twice with screenshots; the machine had 27\n"
        "of them on file and could say nothing useful about any.",
    "save reader tables":
        "#174 — the .d2s reader's tables are generated from HIS install and kept in step\n"
        "with a game patch by me; a stale bit width is not something he can act on.",
    "character sheet data":
        "#174 v-B2 — the character sheet sums the item properties generated from HIS install;\n"
        "keeping that block in step with a game patch is my job. A stale res-all range is not\n"
        "something he can act on - he would read a wrong resistance and trust it.",
    "builder item data":
        "#174 v-B2 fix round — the builder's picker and tooltip list the item database generated\n"
        "from HIS install; keeping that block in step with a game patch is my job. A stale name or\n"
        "range is not something he can act on - he would pick and read it with confidence.",
    "item vocabulary":
        "#60 — generating the vocabulary from HIS install and keeping it in step with a\n"
        "game patch is MY job. He asked for the feature; a stale affix table is not\n"
        "something he can act on, and a silently-unconsulted lexicon even less so.",
    "verdict matches the answer":
        "#125 — how MY parser reads another family answer is mine to get right. He cannot\n"
        "act on a verdict I misread, and a clean look filed as findings quietly becomes a\n"
        "disagreement in the confluence figures he does read.",
    "eye told what was stripped":
        "#122 — what my own transport removes before the eye sees it is mine, not his. He\n"
        "cannot act on a review of a diff with the author's account cut out of it, and a row\n"
        "that silently stops carrying the map looks exactly like one written before v3375.",
    "eye reach per file":
        "#114 — whether the eye actually READ the bytes I paid for is mine to measure. He\n"
        "cannot act on a payload that was cut in transit, and a row that silently stops\n"
        "carrying the measurement looks exactly like one written before it existed.",
    "second eye asked twice":
        "#56 — asking the eye twice is MY job, not his. He cannot act on a look I did not take, "
        "so a SINGLE look must never appear in the count he reads. ⚠ It still renders red, "
        "because the omission is real and I spent a whole arc reporting pairs I had not recorded.",
    "shelf order and guard":
        "#112 — his shelf order is HIS ruling, given twice. Losing it, or losing the scroll guard "
        "that pays for it, is MY regression to catch before he sees furniture instead of reels.",
    "swallowed reads":
        "#108 — a failed read handed back as data is a defect in MY code, never a thing he can "
        "act on. It went red in CI for ten runs with no surface at all; this row is the surface.",
        "extraction lanes": "#75 — the vault lane cannot seal 'examined, nothing here'",
    "board join": "#76 — _BOARD_WIN is set in a child process the server cannot read",
}


#: ══ #223/#226 — A ROW IS HIS ONLY WHEN IT ASKS HIM SOMETHING ════════════════════════════════════
#: HIS RULING, 2026-09-24: "it should only really be waiting on me if its something i need to do".
#: MEASURED on his live console the same morning: WAITING ON YOU read 5 and ONE was his — the
#: shadow gate, a judgement nobody else can make. The other four were a lane I had not drained, a
#: parser owed a declared field, a seed bake owed, and a river the planner itself calls "an answer,
#: not a failure". v2284 made every unlisted check his BY DEFAULT and asked each defect to be argued
#: OUT; that is how the count kept filling with my work. The default is inverted here: a red row
#: bills him only while its check DECLARES a question for him — what exactly is needed, why, and
#: the answers he can give. Everything else is Claude's, and says so under WAITING ON CODE.
#:
#: ⚠ NOT A MUTE BUTTON, same as MINE and BY_DESIGN: every row still renders at its real state and
#: colour. ⚠ AND IT FAILS LOUD: a row whose ask cannot be computed carries `askWhy`, and a surface
#: that cannot read this registry (or a row saved before it existed) bills him as before, so the
#: number he acts on can never shrink for a reason nobody can see. [[unknown-stays-unknown]]
ASK_KINDS = ("decide", "do")
ASK_EFFECTS = ("ruled", "handoff", "verify", "snooze")
ASK_LABEL_MAX = 28


def _ask_shadow_gate(row):
    """The one question that is genuinely his: which gate ticks a grail item by itself."""
    if row.get("state") != MISSING:
        return []
    direction, why = "unknown", ""
    try:
        import shadow_ledger as _sl
        _st = _sl.state() or {}
        _bd = _st.get("byDirection") or {}
        _h, _g = int(_bd.get("shadowWouldHold") or 0), int(_bd.get("shadowWouldGround") or 0)
        direction = ("wouldHold" if _h and not _g else "wouldGround" if _g and not _h
                     else "both" if (_h and _g) else "none")
        _dn, _n = _st.get("disagreeNames"), _st.get("names")
        # ⚠ #228 — HIS WORDS, NOT THE LEDGER'S. A cross-family look at the card read "tick", "Wilson"
        # and "hold a name, never ground one" as house jargon; he asked for TV·D to read human. The
        # measured numbers stay; the sentence says what each choice DOES to him.
        if _dn is not None and _n:
            if direction == "wouldHold":
                why = ("On %d of the %d item names the reader has ever scored, the console ticked the "
                       "item by itself where a stricter rule would have asked you first - never the "
                       "other way round. Stricter means fewer automatic ticks and more items waiting "
                       "for you to confirm. Nothing changes until you choose." % (_dn, _n))
            else:
                why = ("On %d of the %d item names the reader has ever scored, the automatic rule and "
                       "a stricter one disagree about ticking the item by itself. Nothing changes "
                       "until you choose." % (_dn, _n))
    except Exception:
        pass                      # the fingerprint says UNKNOWN; the question is still his
    return [{
        "id": "shadow-gate",
        "kind": "decide",
        "q": "Should the console ask you before it ticks a grail item by itself?",
        "why": why or row.get("why") or "",
        # the identity of the QUESTION: it changes only if the disagreement changes direction
        "fp": "shadow-gate:%s" % direction,
        "answers": [
            {"key": "keep", "label": "Keep it as it is", "effect": "ruled"},
            {"key": "stricter", "label": "Ask me more often", "effect": "handoff"},
            {"key": "week", "label": "Remind me in a week", "effect": "snooze"},
        ],
    }]


def _page_age_days(reading):
    """Days since the Remaining page was FILMED, from its own stamp. -> float | None

    ⚠ NOT the stored `ageDays`: that is measured when the sweep ran and saved with it, so a result
    restored ten days later still said 24.5 days about a page that was 34. [[stale-reading]]"""
    rd = reading or {}
    ra = rd.get("readAt")
    if ra:
        try:
            from datetime import datetime
            t = datetime.fromisoformat(str(ra).replace("Z", "+00:00")).timestamp()
            return max(0.0, (time.time() - t) / 86400.0)
        except Exception:
            pass
    try:
        return None if rd.get("ageDays") is None else float(rd.get("ageDays"))
    except Exception:
        return None


def _remaining_page_reading():
    """#228 — the last chronicle sweep's comparison of his board against the game's Remaining page,
    read from the SAME saved result the sweep panel renders (never re-derived here). -> dict

      state   OK | MISSING | UNKNOWN
      why     the sentence, in his words
      n       rows on his board the page still called missing (MISSING only)
      readAt  the page's own stamp: the identity of the question (a new page is a new question)

    ⚠ A sweep that never ran, or a result that cannot be read, is UNKNOWN and asks him nothing:
    a question built on an absent comparison would bill him for a reading nobody took."""
    try:
        import control_app as _ca
        path = _ca._CHRON_RESULT_PATH
    except Exception as e:
        return {"state": UNKNOWN, "why": "the console app will not import, so the saved sweep "
                                        "cannot be found: %s" % str(e)[:80]}
    if not os.path.exists(path):
        return {"state": UNKNOWN, "why": "no chronicle sweep has been saved on this console, so nothing "
                                        "has compared your board with the game's Remaining page"}
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
    except Exception as e:
        return {"state": UNKNOWN, "why": "the saved sweep is unreadable (%s)" % str(e)[:80]}
    # the second eye on v3498: a readable but WRONG-SHAPED file raised on .get before any return; every
    # level is type-checked, so a shape nobody wrote is UNKNOWN, never a traceback
    res = d.get("result") if isinstance(d, dict) else None
    cal = res.get("calibration") if isinstance(res, dict) else None
    cal = cal if isinstance(cal, dict) else {}
    ex = cal.get("exact") if isinstance(cal.get("exact"), dict) else {}
    if ex.get("ok") is True:
        return {"state": OK, "why": "your board and the last Remaining page add up (%s found, %s missing, "
                                   "%s in the roster)" % (ex.get("boardFound"), ex.get("gameMissing"),
                                                          ex.get("rosterTotal"))}
    if ex.get("ok") is not False:
        return {"state": UNKNOWN, "why": ex.get("say") or cal.get("say")
                or "the last sweep did not compare your board with a Remaining page"}
    rd = ex.get("reading") if isinstance(ex.get("reading"), dict) else {}
    _nm = ex.get("named")
    named = [x.get("name") for x in (_nm if isinstance(_nm, list) else []) if isinstance(x, dict) and x.get("name")]
    try:
        sur = int(ex.get("surplus") or 0)
    except Exception:
        # an unreadable surplus is UNKNOWN, never a zero - "could not read" is not "the page agrees"
        return {"state": UNKNOWN, "why": "the saved sweep's surplus is not a number (%r), so how many "
                                        "of your rows the page disputes is unknown" % (ex.get("surplus"),)}
    n = len(named) or abs(sur)
    age = _page_age_days(rd)
    # half-UP, as the card's Math.round: Python's round() is half-even, so a 2.5-day page read "2 days"
    # here and "3 days" on the card (the second eye on v3498)
    old = "of unknown age" if age is None else ("from today" if age < 1 else "%d days old" % int(age + 0.5))
    if ex.get("boardFound") is None or ex.get("gameMissing") is None:
        # the second eye on v3498: without the counts this printed "Your board has None set pieces" and
        # still asked him to confirm a count the sweep never recorded
        return {"state": UNKNOWN, "why": "the last sweep says your board and the Remaining page differ, but "
                                        "it did not record the counts, so there is nothing to confirm yet"}
    if sur > 0 or named:
        why = ("Your board has %s set pieces ticked. The last Remaining page (%s) still listed %s as "
               "missing, so %d of your ticked rows are ones that page called missing - most likely "
               "found since it was filmed." % (ex.get("boardFound"), old, ex.get("gameMissing"), n))
    else:
        why = ("Your board has %s set pieces ticked; the last Remaining page (%s) implies %s."
               % (ex.get("boardFound"), old, ex.get("impliedFound")))
    bar = cal.get("bar") or {}
    if bar.get("ok") is True and bar.get("frames"):
        why += (" The game's own progress bar, read on %d recent frame(s), agrees with your board."
                % int(bar.get("frames")))
    why += " A new Remaining page settles it."
    return {"state": MISSING, "why": why, "n": n, "readAt": str(rd.get("readAt") or "")}


def _check_a_fresh_remaining_page_would_settle_the_sets_count():
    """#228 — does his board agree with the game's own Remaining page?

    The chronicle-sweep panel showed this as a RED card that read as if he had done something
    wrong ("the board and the game do not add up"). Measured on his live result, 2026-09-24: the
    page was filmed 2026-08-21 and the game's own bar agreed with his board. Only one line of it was
    his - film a new Remaining page - so it is asked here, as his question, and the card is calm."""
    r = _remaining_page_reading()
    return r["state"], r["why"]


def _ask_remaining_page(row):
    """The one line of the chronicle-sweep card that was genuinely his: film a new Remaining page."""
    if row.get("state") != MISSING:
        return []
    r = _remaining_page_reading()
    if r.get("state") != MISSING:
        return []
    n = int(r.get("n") or 0)
    q = ("Film a new Remaining page so the console can confirm %d set row%s?" % (n, "" if n == 1 else "s")
         if n else "Film a new Remaining page so the console can check your set count?")
    return [{
        "id": "remaining-page",
        "kind": "do",
        "q": q,
        "why": r.get("why") or row.get("why") or "",
        # the identity of the QUESTION: a new page is a new question, and an answer to the old one
        # must not close it
        "fp": "remaining-page:%s" % (r.get("readAt") or "unknown"),
        "answers": [
            {"key": "filmed", "label": "I filmed one", "effect": "verify"},
            {"key": "week", "label": "Remind me in a week", "effect": "snooze"},
            {"key": "skip", "label": "Not needed", "effect": "ruled"},
        ],
    }]


def _mid_restart_peers(roster=None, now=None):
    """-> {"state", "quiet": [{machine, nickname, ver, diskVer, ageS}], "off": int, "why"} from the cached roster.

    ⚠ `relaunch.armed` IS NOT "ABOUT TO RESTART". MEASURED on his roster 2026-09-24: armed is True on
    EVERY console, online or off - it means "will follow a new build", nothing more. The restart
    signature is the LAST beacon holding a newer build on disk than the one running (diskVer != ver)
    with the restart allowed (may True): that console was on its way out, and then nothing arrived.
    A machine that is simply switched off (Dean: v3404 running, v3404 on disk) is NOT this, and must
    never become a question - his wife's PC being off is not an errand."""
    if roster is None:
        try:
            import control_app as _ca
            roster = (_serving_console(_ca)._FLEET_PRESENCE_CACHE or {}).get("d")
        except Exception as e:
            return {"state": UNKNOWN, "quiet": [], "off": 0,
                    "why": "the roster could not be read (%s)" % type(e).__name__}
    if not isinstance(roster, dict):
        return {"state": UNMEASURED, "quiet": [], "off": 0,
                "why": "this console holds no fleet roster yet - an absent question, not a clean answer"}
    now = time.time() if now is None else now
    me = roster.get("me")
    off = [r for r in (roster.get("offline") or []) if isinstance(r, dict) and r.get("machine") != me]
    quiet = []
    for r in off:
        ver, disk = r.get("ver"), r.get("diskVer")
        rl = r.get("relaunch") if isinstance(r.get("relaunch"), dict) else {}
        if not (ver and disk and disk != ver and rl.get("may") is True):
            continue
        age = None
        try:
            import calendar as _cal
            age = int(now - _cal.timegm(time.strptime(str(r.get("t"))[:19], "%Y-%m-%dT%H:%M:%S")))
        except Exception:
            pass                                   # undatable is not "just now" [[unknown-stays-unknown]]
        quiet.append({"machine": r.get("machine"), "nickname": r.get("nickname") or r.get("machine"),
                      "ver": ver, "diskVer": disk, "ageS": age})
    if quiet:
        return {"state": MISSING, "quiet": quiet, "off": len(off),
                "why": "; ".join("%s went quiet while restarting from %s into %s%s"
                                 % (q["nickname"], q["ver"], q["diskVer"],
                                    " (last heard %dh ago)" % (q["ageS"] // 3600) if q["ageS"] is not None else "")
                                 for q in quiet[:4])}
    if not off:
        return {"state": UNMEASURED, "quiet": [], "off": 0,
                "why": "no other machine is offline, so none can have died mid-restart"}
    return {"state": OK, "quiet": [], "off": len(off),
            "why": ("%d machine(s) are offline and none went quiet mid-restart - each was running the build "
                    "on its disk when it was last heard, so it was switched off, not stuck" % len(off))}


def _check_no_machine_went_quiet_mid_restart():
    """#223 / #227 item 2 — DID A PEER DIE IN THE MIDDLE OF RESTARTING?

    MEASURED 2026-09-19 (#225): the Windows ALT died relaunching into v3419 and the roster read it as
    'switched off' - the one state that looks exactly like a machine he turned off on purpose. Only a
    person at that machine can bring it back, so this is the fleet's only 'is it on?' question, and it
    is asked ONLY on the restart signature (see _mid_restart_peers), never for a machine that is off.
    It reads the presence cache, never the network."""
    r = _mid_restart_peers()
    return r["state"], r["why"]


def _ask_mid_restart(row):
    """One question per machine and per build it was restarting into: a new stall is a new question."""
    if row.get("state") != MISSING:
        return []
    out = []
    for q in _mid_restart_peers().get("quiet") or []:
        out.append({
            "id": "mid-restart-%s" % q["machine"],
            "kind": "do",
            "q": "%s went quiet while restarting into %s. Is it on?" % (q["nickname"], q["diskVer"]),
            "why": ("its last report said it was running %s with %s on disk and free to restart - then "
                    "nothing arrived. A machine switched off on purpose never looks like this."
                    % (q["ver"], q["diskVer"])),
            "fp": "mid-restart:%s:%s" % (q["machine"], q["diskVer"]),
            "answers": [
                {"key": "on", "label": "It's back on", "effect": "verify"},
                {"key": "off", "label": "It's off on purpose", "effect": "ruled"},
                {"key": "later", "label": "Remind me tomorrow", "effect": "snooze"},
            ],
        })
    return out


#: #229 — the scheduled task a "yes" would create. One name, so the check and the setup agree.
SIGN_IN_TASK = "TV DIABLO at sign-in"


LAUNCH_MARKERS = ("start_tvd_win", "control_app.py")


def _launches_this_console(path):
    """Does this Startup entry launch THIS console? -> True / False / None (could not read it)."""
    try:
        with open(path, "rb") as fh:
            raw = fh.read(262144).lower()
    except OSError:
        return None
    return any(m.encode("ascii") in raw or m.encode("utf-16-le") in raw for m in LAUNCH_MARKERS)


def _sign_in_start(run=None, startup_dir=None, is_win=None):
    """-> {"state", "how", "why"}: does THIS Windows console come back by itself after a restart?

    MEASURED 2026-09-20 over SSH on the ALT: zero scheduled tasks, zero startup entries. The console
    survives its own relaunch (#224) but not a reboot or a sign-out - after either, nothing films
    and nothing pulls until he double-clicks. Whether it SHOULD start by itself is a standing change
    on his PC, so that is his call; this only says which way it is today."""
    is_win = sys.platform.startswith("win") if is_win is None else is_win
    if not is_win:
        return {"state": UNMEASURED, "how": None,
                "why": "only a Windows console needs a sign-in start - this machine starts through its own launcher"}
    if startup_dir is None:
        startup_dir = os.path.join(os.environ.get("APPDATA") or "", "Microsoft", "Windows",
                                   "Start Menu", "Programs", "Startup")
    # ⚠⚠ REG-1282 — AN ENTRY COUNTS WHEN IT LAUNCHES THIS CONSOLE, NOT WHEN ITS NAME SOUNDS LIKE IT. This
    # accepted any Startup name containing "diablo" or starting "tvd", so the game's own shortcut, a note or
    # an old copy read OK, the question was never asked, and after a reboot the console stayed off with a
    # quiet mailbox (the cross-family eye on #231, look at 34129c99). His real entry would be a copy of the
    # installer's "TV DIABLO.lnk", whose arguments name start_tvd_win.ps1 - a .lnk stores that UTF-16LE.
    # An entry that cannot be read is UNKNOWN, never OK. [[unknown-stays-unknown]]
    unread = []
    try:
        for n in sorted(os.listdir(startup_dir)):
            launches = _launches_this_console(os.path.join(startup_dir, n))
            if launches is True:
                return {"state": OK, "how": "startup:" + n,
                        "why": "this console starts at sign-in from the Startup folder (%s)" % n}
            if launches is None:
                unread.append(n)
    except OSError:
        pass                                        # no Startup folder is not an answer yet
    try:
        if run is None:
            import git_quiet as _gq
            run = _gq.run
        r = run(["schtasks", "/Query", "/TN", SIGN_IN_TASK], capture_output=True, text=True, timeout=20)
    except Exception as e:
        return {"state": UNKNOWN, "how": None,
                "why": "could not ask Windows for its scheduled tasks (%s), so whether this console starts "
                       "at sign-in is UNKNOWN" % type(e).__name__}
    if getattr(r, "returncode", 1) == 0:
        return {"state": OK, "how": "task:" + SIGN_IN_TASK,
                "why": "this console starts at sign-in (scheduled task '%s')" % SIGN_IN_TASK}
    if unread:
        return {"state": UNKNOWN, "how": None,
                "why": "no '%s' task, and %d Startup entr%s could not be read (%s), so whether one of them "
                       "starts this console is UNKNOWN" % (SIGN_IN_TASK, len(unread),
                                                           "y" if len(unread) == 1 else "ies", ", ".join(unread[:3]))}
    return {"state": MISSING, "how": None,
            "why": ("nothing starts this console when the PC signs in: no '%s' task and nothing in the "
                    "Startup folder - after a reboot it stays off until someone opens it" % SIGN_IN_TASK)}


def _check_this_console_starts_at_sign_in():
    """#229 — AFTER A REBOOT, DOES THIS CONSOLE COME BACK BY ITSELF? (Windows; his call whether it should)"""
    r = _sign_in_start()
    return r["state"], r["why"]


def _ask_sign_in_start(row):
    """His call, so a question: yes hands the setup to Claude; no is his ruling and stands."""
    if row.get("state") != MISSING:
        return []
    return [{
        "id": "sign-in-start",
        "kind": "decide",
        "q": "Start TV DIABLO on this PC when you sign in?",
        "why": row.get("why") or "",
        "fp": "sign-in-start:%s" % SIGN_IN_TASK,
        "answers": [
            {"key": "yes", "label": "Yes, set it up", "effect": "handoff"},
            {"key": "no", "label": "No, I open it myself", "effect": "ruled"},
            {"key": "later", "label": "Ask me next week", "effect": "snooze"},
        ],
    }]


#: REG-1660 — the Startup entry a console makes for itself, named like the task so the two read as one thing.
SIGN_IN_LNK = SIGN_IN_TASK + ".lnk"


def _psq(s):
    """One PowerShell single-quoted literal: a quote inside is doubled, nothing else is special."""
    return "'" + str(s).replace("'", "''") + "'"


def _make_sign_in_shortcut(startup_dir, repo_dir, run=None):
    """Write <Startup>\\TV DIABLO at sign-in.lnk, the installer's own shortcut shape, with -Background. -> (ok, why)

    The same target the Desktop icon uses (install-tvd.ps1: hidden powershell running start_tvd_win.ps1), plus
    -Background, so a sign-in start opens the console HIDDEN - the service runs and the Desktop icon brings the
    window. A Startup-folder shortcut needs no administrator, which a sign-in scheduled task does."""
    launcher = os.path.join(repo_dir, "tv", "start_tvd_win.ps1")
    if not os.path.isfile(launcher):
        return False, "the launcher is not at %s, so there is nothing to start at sign-in" % launcher
    if not os.path.isdir(startup_dir):
        return False, "the Startup folder %s does not exist" % startup_dir
    args = '-NoLogo -WindowStyle Hidden -ExecutionPolicy Bypass -File "%s" -Background' % launcher
    ico = os.path.join(repo_dir, "tv", "appicon.ico")
    ps = ("$ws = New-Object -ComObject WScript.Shell; $l = $ws.CreateShortcut(%s); $l.TargetPath = 'powershell.exe'; "
          "$l.Arguments = %s; $l.WorkingDirectory = %s; $l.WindowStyle = 7; %s$l.Description = %s; $l.Save()"
          % (_psq(os.path.join(startup_dir, SIGN_IN_LNK)), _psq(args), _psq(repo_dir),
             ("$l.IconLocation = %s; " % _psq(ico)) if os.path.isfile(ico) else "",
             _psq("TV DIABLO - starts hidden in the background when you sign in (the Desktop icon brings the window)")))
    try:
        if run is None:
            import git_quiet as _gq
            run = _gq.run                           # no console window of its own on Windows
        r = run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    except Exception as e:
        return False, "PowerShell could not be started to write the shortcut (%s)" % type(e).__name__
    if getattr(r, "returncode", 1) != 0:
        return False, ("PowerShell refused to write the shortcut: %s"
                       % ((str(getattr(r, "stderr", "") or "").strip()[-160:]) or "it gave no reason"))
    return True, ""


def _sign_in_marker_read(path):
    """What this console recorded about the entry it made. -> dict ({} = never made one) | None (unreadable)"""
    try:
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
    except FileNotFoundError:
        return {}
    except Exception:
        return None
    return d if isinstance(d, dict) else None


def _sign_in_ruled_no(answers_path, now_ms=None):
    """Did this PC answer the sign-in question "No, I open it myself", standing now? -> True | False | None (unreadable)"""
    if not answers_path:
        return False
    import his_answers as _ha
    answers, _why = _ha.load(answers_path)
    if answers is None:
        return None
    ask = _ask_sign_in_start({"state": MISSING, "why": ""})[0]
    st = _ha.standing(ask, answers, now_ms)
    return bool(st and st.get("key") == "no")


def ensure_sign_in_start(marker, answers_path=None, run=None, startup_dir=None, is_win=None, make=None,
                         repo_dir=None, now_ms=None):
    """REG-1660 — THIS WINDOWS CONSOLE MAKES ITS OWN START AT SIGN-IN, ONCE, AND NEVER FIGHTS A REMOVAL. -> {"did", "why"}

    His ruling, 2026-10-01, answering #229's question for every PC at once: "set it up there and for dean too..
    like in general ... so it starts at startup". MEASURED the same morning on his Windows PC: no task, nothing in
    the Startup folder - "after a reboot it stays off until someone opens it" - and Dean's laptop had last reported
    on 09-29, on v3522, since nothing brings a console back after a reboot. A console that is not running has no
    shadow reader, no beacon and no pull, so it can neither film, show its lights nor update itself.

      did "created"  the entry is made (the launcher, -Background) and the check now SEES it; the marker records it
      did "already"  something already starts this console at sign-in - left exactly as it is
      did "left"     the entry this console made is gone (someone removed it), or this PC answered "No, I open it
                     myself": never made again - a removal is a choice, and fighting it would be a bug with a timer
      did "failed"   it could not be made, or was written and the check still cannot see it - said, never claimed
      did None       not Windows, or whether it starts at sign-in is UNKNOWN - nothing is made on a guess
    [[unknown-stays-unknown]] [[the-unjoined-end]]"""
    is_win = sys.platform.startswith("win") if is_win is None else is_win
    if not is_win:
        return {"did": None, "why": "only a Windows console needs a sign-in start"}
    if startup_dir is None:
        startup_dir = os.path.join(os.environ.get("APPDATA") or "", "Microsoft", "Windows",
                                   "Start Menu", "Programs", "Startup")
    st = _sign_in_start(run=run, startup_dir=startup_dir, is_win=True)
    if st["state"] == OK:
        return {"did": "already", "why": st["why"]}
    if st["state"] != MISSING:
        return {"did": None, "why": "whether this console starts at sign-in is %s (%s) - nothing is made on a guess"
                                    % (st["state"], st["why"])}
    m = _sign_in_marker_read(marker)
    if m is None:
        return {"did": None, "why": "the record of an earlier sign-in entry cannot be read, so whether one was "
                                    "removed on purpose is UNKNOWN - nothing is made"}
    if m.get("madeMs"):
        return {"did": "left", "why": "the sign-in entry this console made is gone - someone removed it, so it is not "
                                      "made again"}
    no = _sign_in_ruled_no(answers_path, now_ms)
    if no is None:
        return {"did": None, "why": "this PC's answers cannot be read, so whether it said no is UNKNOWN - nothing is made"}
    if no:
        return {"did": "left", "why": "this PC answered 'No, I open it myself' - that stands"}
    repo_dir = repo_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ok, why = (make or _make_sign_in_shortcut)(startup_dir, repo_dir)
    if not ok:
        return {"did": "failed", "why": why}
    st2 = _sign_in_start(run=run, startup_dir=startup_dir, is_win=True)
    if st2["state"] != OK:
        return {"did": "failed", "why": "the entry was written but the check still cannot see it: %s" % st2["why"]}
    rec = {"madeMs": int(now_ms if now_ms is not None else time.time() * 1000), "how": st2.get("how"),
           "why": "made by this console on his 2026-10-01 ruling (REG-1660)"}
    try:
        tmp = marker + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(rec, fh)
        os.replace(tmp, marker)
    except Exception as e:
        return {"did": "created", "why": "%s - but its record could not be kept (%s), so a later removal may be "
                                         "re-made once" % (st2["why"], type(e).__name__)}
    return {"did": "created", "why": st2["why"]}


#: REG-2614 — the task that brings a dead Windows console back. Its own name: the sign-in start is a different thing.
KEEPALIVE_TASK = "TV DIABLO keepalive"
KEEPALIVE_EVERY_MIN = 5


def _xml_esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def _keepalive_pythonw(python=None, isfile=os.path.isfile):
    """The windowless interpreter beside the console's own: pythonw.exe next to python.exe (no window flashes every
    five minutes), else the console's own interpreter - a flash beats a console that never comes back."""
    py = python or sys.executable or "pythonw.exe"
    d, b = ntpath.split(py)
    if b.lower() == "python.exe" and isfile(ntpath.join(d, "pythonw.exe")):
        return ntpath.join(d, "pythonw.exe")
    return py


def keepalive_task_xml(pythonw, tv_dir, start_local, run_as=None):
    """PURE. The Task Scheduler definition of the keepalive. -> str

    Every KEEPALIVE_EVERY_MIN minutes, for ever, as the signed-in user (InteractiveToken - no password is stored and
    no administrator is needed), hidden, ON BATTERY TOO (schtasks /SC MINUTE would default to AC-only, and Dean's PC is
    a laptop), never two at once, with NO time limit (PT0S: a limit job-kills the console a pass starts, review r1 -
    a pass ends itself after console_keepalive.PASS_DEADLINE_S instead). A pass is console_keepalive.py: it launches only a console
    that is GONE (REG-2614). XML rather than /TR: /TR is capped at 261 characters and a repo under a long path with
    spaces would not fit.

    run_as (REG-2616, his 2026-10-23 ruling): the UNATTENDED mode - the task runs whether or not anyone is signed in
    (LogonType Password, as that account), so a console that dies, or a PC that reboots to the sign-in screen, still
    gets its console back. The XML names only the account; the password is given to Task Scheduler at install time
    (install_unattended_keepalive) and is never in the XML, the repo or a log. None = the default, signed-in or
    locked only (InteractiveToken)."""
    script = ntpath.join(tv_dir, "console_keepalive.py")
    if run_as:
        principal = ('<Principal id="Author"><UserId>%s</UserId><LogonType>Password</LogonType>'
                     '<RunLevel>LeastPrivilege</RunLevel></Principal>' % _xml_esc(run_as))
    else:
        principal = ('<Principal id="Author"><LogonType>InteractiveToken</LogonType>'
                     '<RunLevel>LeastPrivilege</RunLevel></Principal>')
    return ('<?xml version="1.0" encoding="UTF-16"?>\n'
            '<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">\n'
            '  <RegistrationInfo><Description>TV DIABLO - brings the console back within %d minutes if it dies '
            '(REG-2614). Never starts one that was closed on purpose.</Description></RegistrationInfo>\n'
            '  <Triggers><TimeTrigger><StartBoundary>%s</StartBoundary><Enabled>true</Enabled>'
            '<Repetition><Interval>PT%dM</Interval><StopAtDurationEnd>false</StopAtDurationEnd></Repetition>'
            '</TimeTrigger></Triggers>\n'
            '  <Principals>%s</Principals>\n'
            '  <Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>'
            '<DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>'
            '<StopIfGoingOnBatteries>false</StopIfGoingOnBatteries><StartWhenAvailable>true</StartWhenAvailable>'
            '<Hidden>true</Hidden><ExecutionTimeLimit>PT0S</ExecutionTimeLimit><Enabled>true</Enabled></Settings>\n'
            '  <Actions Context="Author"><Exec><Command>%s</Command><Arguments>%s</Arguments>'
            '<WorkingDirectory>%s</WorkingDirectory></Exec></Actions>\n'
            '</Task>\n') % (KEEPALIVE_EVERY_MIN, _xml_esc(start_local), KEEPALIVE_EVERY_MIN, principal, _xml_esc(pythonw),
                             _xml_esc('"%s"' % script), _xml_esc(tv_dir))


def _schtasks_text(out):
    """bytes | str | None -> str. schtasks output read in whatever it was written in (review r2).

    Piped, schtasks may write UTF-16 LE (BOM or a NUL every other byte) or the console's OEM code page - never
    reliably the ANSI page text=True decodes with: on a Hebrew Windows (cp1255) that decode RAISED, so the list
    read as UNKNOWN and the task was never made; on cp1252 it passed NULs to csv, which raised. So the bytes are
    taken raw: UTF-16 when they look like it, else UTF-8, else the locale page with every bad byte replaced. Only
    the ASCII task name is ever matched, so a replaced localized status word costs nothing."""
    if out is None:
        return ""
    if isinstance(out, str):
        return out.replace("\x00", "")
    b = bytes(out)
    if b[:2] == b"\xff\xfe" or b[:2] == b"\xfe\xff":
        return b.decode("utf-16", "replace").replace("\x00", "")
    if len(b) >= 4 and b[1:2] == b"\x00" and b[3:4] == b"\x00":
        return b.decode("utf-16-le", "replace").replace("\x00", "")
    try:
        return b.decode("utf-8").replace("\x00", "")
    except UnicodeDecodeError:
        pass
    import locale
    enc = locale.getpreferredencoding(False) or "latin-1"
    try:
        return b.decode(enc, "replace").replace("\x00", "")
    except LookupError:
        return b.decode("latin-1").replace("\x00", "")


def _keepalive_task_exists(run):
    """-> True | False | None (UNKNOWN). A named query that answers 0 is a yes in any language. Anything else is
    settled by the FULL list (review r1: 'cannot find' is English only - a Hebrew or German schtasks never matched,
    so the task was never made): the name absent from a list that answered is a no; a list that failed is UNKNOWN."""
    try:
        # raw bytes, never text=True: the decode is _schtasks_text's, and the parse is inside this try (review r2)
        r = run(["schtasks", "/Query", "/TN", KEEPALIVE_TASK], capture_output=True, timeout=20)
        if getattr(r, "returncode", 1) == 0:
            return True
        lst = run(["schtasks", "/Query", "/FO", "CSV", "/NH"], capture_output=True, timeout=60)
        if getattr(lst, "returncode", 1) != 0:
            return None
        want = ("\\" + KEEPALIVE_TASK).lower()
        for row in csv.reader(_schtasks_text(getattr(lst, "stdout", None)).splitlines()):
            if row and row[0].strip().lower() == want:
                return True
        return False
    except Exception:                   # csv.Error, a decode, a timeout: UNKNOWN, never a guessed "no"
        return None


def ensure_keepalive_task(marker, sign_in_did, run=None, is_win=None, tv_dir=None, python=None, now_ms=None,
                          write_xml=None, isfile=os.path.isfile):
    """REG-2614 — A CONSOLE THAT STARTS AT SIGN-IN ALSO COMES BACK WHEN IT DIES. -> {"did", "why"}

    2026-10-16: the ALT's console died with no error and stayed dead until the next Windows sign-in - 302 commits
    missed. The sign-in start (REG-1660) only runs at sign-in. This rides THE SAME CONSENT: the keepalive exists
    only while the sign-in start does, so a PC that said "No, I open it myself", or removed the entry, is never
    given a console that starts itself every five minutes instead.

      did "created"    the task is made and the check now SEES it; the marker records it
      did "already"    the task exists - left exactly as it is
      did "left"       the task this console made is gone (someone removed it): never made again
      did "withdrawn"  the sign-in start is gone or ruled out, so the keepalive this console made is removed with it
      did "failed"     it could not be made or removed - said, never claimed
      did None         not Windows, or the sign-in start / the task is UNKNOWN - nothing is done on a guess
    [[unknown-stays-unknown]]"""
    is_win = sys.platform.startswith("win") if is_win is None else is_win
    if not is_win:
        return {"did": None, "why": "only a Windows console needs a keepalive task"}
    if run is None:
        import git_quiet as _gq
        run = _gq.run
    consent = sign_in_did in ("created", "already")
    if sign_in_did not in ("created", "already", "left"):
        return {"did": None, "why": "whether this console starts at sign-in is not settled (%s) - the keepalive "
                                    "follows it, so nothing is done" % (sign_in_did,)}
    rec = _sign_in_marker_read(marker)
    if rec is None:
        return {"did": None, "why": "the record of an earlier keepalive cannot be read - nothing is done"}
    exists = _keepalive_task_exists(run)
    if exists is None:
        return {"did": None, "why": "whether the '%s' task exists is UNKNOWN - nothing is done" % KEEPALIVE_TASK}
    if not consent:
        if exists and rec.get("madeMs") and _keepalive_task_logon(run) != "InteractiveToken":
            # review r3: the owner re-registered it unattended (or it cannot be read) - his task, never removed
            return {"did": "left", "why": "the '%s' task is the owner's unattended install (or could not be read) - "
                                          "left as it is" % KEEPALIVE_TASK}
        if exists and rec.get("madeMs"):
            try:
                r = run(["schtasks", "/Delete", "/TN", KEEPALIVE_TASK, "/F"], capture_output=True, timeout=30)
                ok = getattr(r, "returncode", 1) == 0
            except Exception:
                ok = False
            if not ok:
                return {"did": "failed", "why": "the sign-in start is gone but its keepalive could not be removed"}
            return {"did": "withdrawn", "why": "the sign-in start is gone, so the keepalive this console made went "
                                               "with it"}
        return {"did": "left", "why": "this console does not start at sign-in, so it has no keepalive"}
    if exists:
        return {"did": "already", "why": "the '%s' task brings this console back if it dies" % KEEPALIVE_TASK}
    if rec.get("madeMs"):
        return {"did": "left", "why": "the keepalive this console made is gone - someone removed it, so it is not "
                                      "made again"}
    tv_dir = tv_dir or os.path.dirname(os.path.abspath(__file__))
    now_ms = int(now_ms if now_ms is not None else time.time() * 1000)
    start = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(now_ms / 1000.0))
    xml = keepalive_task_xml(_keepalive_pythonw(python, isfile), tv_dir, start)
    xml_path = marker + ".task.xml"
    try:
        if write_xml is not None:
            write_xml(xml_path, xml)
        else:
            with open(xml_path, "w", encoding="utf-16") as fh:   # the BOM Task Scheduler expects
                fh.write(xml)
        r = run(["schtasks", "/Create", "/TN", KEEPALIVE_TASK, "/XML", xml_path, "/F"],
                capture_output=True, timeout=30)
    except Exception as e:
        return {"did": "failed", "why": "the keepalive task could not be written (%s)" % type(e).__name__}
    finally:
        try:
            os.remove(xml_path)
        except OSError:
            pass
    if getattr(r, "returncode", 1) != 0:
        return {"did": "failed", "why": "Windows refused the keepalive task: %s"
                                        % (("%s %s" % (_schtasks_text(getattr(r, "stdout", None)),
                                                       _schtasks_text(getattr(r, "stderr", None))))
                                           .strip()[-160:] or "no reason given")}
    if _keepalive_task_exists(run) is not True:
        return {"did": "failed", "why": "the keepalive task was written but the check still cannot see it"}
    try:
        tmp = marker + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"madeMs": now_ms, "task": KEEPALIVE_TASK, "why": "REG-2614"}, fh)
        os.replace(tmp, marker)
    except Exception as e:
        return {"did": "created", "why": "made, but its record could not be kept (%s)" % type(e).__name__}
    return {"did": "created", "why": "the '%s' task now brings this console back within %d minutes if it dies"
                                     % (KEEPALIVE_TASK, KEEPALIVE_EVERY_MIN)}


#: Register-ScheduledTask taking every value from ITS OWN environment - the password included - never from argv: a
#: command line lands in process-creation audit logs (event 4688, Sysmon) and is listed by WMI; an environment block
#: is not logged and is readable only by the same user or an administrator. (Review r3: stdin read with
#: [Console]::In under `-Command` is not what Windows PowerShell hands a piped line to, so the password never
#: arrived; the environment is UTF-16 on Windows, so a non-ASCII password survives as typed.)
_UNATTENDED_PS = ("$ErrorActionPreference='Stop'; "
                  "$x = Get-Content -Raw -Encoding Unicode -LiteralPath $env:TVD_KA_XML; "
                  "Register-ScheduledTask -TaskName $env:TVD_KA_TASK -Xml $x.TrimStart([char]0xFEFF) "
                  "-User $env:TVD_KA_USER -Password $env:TVD_KA_PW -Force | Out-Null")
#: the only parts of the caller's environment PowerShell is given - never the variable the password came from
_UNATTENDED_ENV_KEEP = ("PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "SYSTEMDRIVE", "TEMP", "TMP", "USERPROFILE",
                        "COMSPEC", "PSMODULEPATH")


def _without_secret(text, secret):
    """-> text with every copy of the secret replaced. Whatever Windows says back is said - the password never is.
    PowerShell's captured errors are CLIXML, which writes '<' as _x003C_ and non-ASCII as _xHHHH_: unescaped first,
    or an escaped copy of the password would slip past (review r3)."""
    import re as _re
    text = _re.sub(r"_x([0-9A-Fa-f]{4})_", lambda m: chr(int(m.group(1), 16)), str(text or ""))
    return text.replace(secret, "***") if secret else text


def _keepalive_task_logon(run):
    """-> the registered task's LogonType ('InteractiveToken', 'Password', ...) or None (UNKNOWN). Read from the
    task's own /XML through _schtasks_text."""
    try:
        r = run(["schtasks", "/Query", "/TN", KEEPALIVE_TASK, "/XML"], capture_output=True, timeout=20)
        if getattr(r, "returncode", 1) != 0:
            return None
        import re as _re
        m = _re.search(r"<LogonType>\s*([A-Za-z0-9]+)\s*</LogonType>", _schtasks_text(getattr(r, "stdout", None)))
        return m.group(1) if m else None
    except Exception:                   # an unreadable task is UNKNOWN, never "not his"
        return None


def install_unattended_keepalive(user, password, run=None, is_win=None, tv_dir=None, python=None, now_ms=None,
                                 write_xml=None, isfile=os.path.isfile, env=None):
    """REG-2616 - THE KEEPALIVE THAT ALSO RUNS WITH NOBODY SIGNED IN. -> {"did", "why"}  (never the password)

    His 2026-10-23 ruling: the ALT must get its console back after a reboot that stops at the sign-in screen, which
    the default task (signed-in or locked only) cannot do. An install-time act by the owner, not the console's: run
    once (console_keepalive.py --install-unattended USER), it (re)registers the same task as USER with the stored
    password. Nothing in the console calls this; with no password the default mode stays exactly as it was.

      did "created"   registered and the check SEES it
      did "failed"    refused / could not be checked - Windows' words are said, the password is replaced by ***
      did None        not Windows, or no user / no password given - nothing is done on a guess

    The password goes to that one PowerShell child in its environment only (TVD_KA_PW; the caller's variable is not
    passed on) - never argv, the XML, the marker, a log or the return value. A task this installs is the owner's:
    ensure_keepalive_task finds it 'already' there, and never removes a task whose LogonType is not InteractiveToken,
    even one the console first made (review r3)."""
    is_win = sys.platform.startswith("win") if is_win is None else is_win
    if not is_win:
        return {"did": None, "why": "only a Windows console has a keepalive task"}
    if not user or not password:
        return {"did": None, "why": "the unattended keepalive needs the account and its password - nothing is done"}
    if run is None:
        import git_quiet as _gq
        run = _gq.run
    tv_dir = tv_dir or os.path.dirname(os.path.abspath(__file__))
    now_ms = int(now_ms if now_ms is not None else time.time() * 1000)
    start = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(now_ms / 1000.0))
    xml = keepalive_task_xml(_keepalive_pythonw(python, isfile), tv_dir, start, run_as=user)
    import tempfile
    fd, xml_path = tempfile.mkstemp(prefix="tvd-keepalive-", suffix=".xml")
    os.close(fd)
    try:
        if write_xml is not None:
            write_xml(xml_path, xml)
        else:
            with open(xml_path, "w", encoding="utf-16") as fh:
                fh.write(xml)
        src = os.environ if env is None else env
        e = {k: v for k, v in src.items() if k.upper() in _UNATTENDED_ENV_KEEP}
        e.update(TVD_KA_TASK=KEEPALIVE_TASK, TVD_KA_XML=xml_path, TVD_KA_USER=user, TVD_KA_PW=password)
        r = run(["powershell", "-NoProfile", "-NonInteractive", "-Command", _UNATTENDED_PS],
                stdin=subprocess.DEVNULL, capture_output=True, timeout=60, env=e)
    except Exception as ex:
        return {"did": "failed", "why": "the unattended keepalive could not be registered (%s)" % type(ex).__name__}
    finally:
        try:
            os.remove(xml_path)
        except OSError:
            pass
    if getattr(r, "returncode", 1) != 0:
        said = ("%s %s" % (_schtasks_text(getattr(r, "stdout", None)), _schtasks_text(getattr(r, "stderr", None))))
        return {"did": "failed", "why": "Windows refused the unattended keepalive: %s"
                                        % (_without_secret(said, password).strip()[-200:] or "no reason given")}
    if _keepalive_task_logon(run) != "Password":
        # review r3: read the task back - one that is missing, unreadable, or needs someone signed in is not made
        return {"did": "failed", "why": "the '%s' task is not there running with nobody signed in" % KEEPALIVE_TASK}
    return {"did": "created", "why": "the '%s' task now runs every %d minutes as %s, signed in or not"
                                     % (KEEPALIVE_TASK, KEEPALIVE_EVERY_MIN, user)}


#: check name -> fn(row) -> [ask]. A check absent from here asks him nothing.
ASKS = {
    "shadow gate": _ask_shadow_gate,
    # #228 — the one line of the chronicle-sweep card that was his
    "a fresh remaining page": _ask_remaining_page,
    # #223 — the fleet's only 'is it on?': a peer that went quiet mid-restart, never one switched off
    "no machine went quiet mid-restart": _ask_mid_restart,
    # #229 — a standing change on his PC is his call; the console only asks
    "this console starts at sign-in": _ask_sign_in_start,
}


def ask_problems(ask):
    """-> [str] what is wrong with one declared ask ([] when it is well formed)."""
    bad = []
    if not isinstance(ask, dict):
        return ["not a dict"]
    for k in ("id", "kind", "q", "fp", "answers"):
        if not ask.get(k):
            bad.append("no %s" % k)
    if ask.get("kind") not in ASK_KINDS:
        bad.append("kind %r" % ask.get("kind"))
    ans = ask.get("answers") or []
    if not isinstance(ans, (list, tuple)):
        # the second eye on v3494: `len()` of a non-list raised OUT of attach_asks and took the whole
        # doctor pass with it, instead of landing on the one row as its contract says
        return bad + ["answers is %s, not a list" % type(ans).__name__]
    if not 1 <= len(ans) <= 4:
        bad.append("%d answers (1-4)" % len(ans))
    keys = [a.get("key") for a in ans if isinstance(a, dict)]
    if len(set(keys)) != len(ans):
        bad.append("answer keys not unique")
    for a in ans:
        if not isinstance(a, dict):
            continue
        if len(a.get("label") or "") > ASK_LABEL_MAX or not a.get("label"):
            bad.append("label %r" % a.get("label"))
        if a.get("effect") not in ASK_EFFECTS:
            bad.append("effect %r" % a.get("effect"))
    return bad


def attach_asks(rows):
    """Give every row its declared questions (`asks`, [] when none). -> rows

    A row whose ask throws or is malformed gets `asks: []` AND `askWhy`, so it lands under
    Claude's work with the reason printed, never silently in or out of his count."""
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        fn = ASKS.get(r.get("check"))
        if fn is None:
            r["asks"] = []
            continue
        try:
            got = list(fn(r) or [])
        except Exception as e:
            r["asks"], r["askWhy"] = [], "its question could not be computed: %s" % str(e)[:120]
            continue
        try:
            probs = ["%s: %s" % ((a or {}).get("id") if isinstance(a, dict) else "?", "; ".join(ask_problems(a)))
                     for a in got if ask_problems(a)]
        except Exception as e:
            r["asks"], r["askWhy"] = [], "its declared question could not be graded: %s" % str(e)[:120]
            continue
        if probs:
            r["asks"], r["askWhy"] = [], "its declared question is malformed (%s)" % " | ".join(probs)[:200]
            continue
        r["asks"] = got
    return rows


def owner_of(name):
    """-> 'you' only for a check that can ASK him something (#226), else 'me'.

    Name-level: whether THIS tick bills him is decided per row by its `asks` (attach_asks)."""
    if name in MINE:
        return "me"
    return "you" if name in ASKS else "me"


def _check_what_runs_without_him():
    """Nine loops run with no prompt from him, one of them a DELETION lane, and until v2293 nothing
    on this console could say what any of them would touch. The cold read asked "if this app were
    about to do something on your behalf, could you tell what it would do and what it would leave
    alone?" and answered CANNOT TELL. This reports the answer, and goes MISSING when a lane's own
    BODY contradicts the promise it publishes."""
    try:
        import auto_scope
    except Exception as e:
        return UNKNOWN, "auto_scope will not import, so nothing here knows what runs unprompted: %s" % str(e)[:80]
    try:
        import control_app
        broken = auto_scope.check_declarations(control_app)
        lanes = auto_scope.LANES
    except Exception as e:
        return UNKNOWN, "could not read the lane declarations: %s" % str(e)[:90]
    if not lanes:
        return UNKNOWN, "no lane declared a scope — a reader that finds nothing is broken, not clean"
    if broken:
        return MISSING, "%d lane(s) do what they promise never to do: %s" % (
            len(broken), "; ".join(broken)[:200])
    deleters = sorted(n for n, d in lanes.items() if "delete" not in (d.get("forbids") or []))
    return OK, "%d lanes run without you; %d can delete (%s), and no lane's own body contradicts " \
               "its promise" % (len(lanes), len(deleters), ", ".join(deleters) or "none")


def _check_every_ledger_can_say_WHERE_IT_CAME_FROM():
    """v2746 — ONE BOOLEAN IS ANSWERING A THREE-LEDGER QUESTION, AND ON THIS MACHINE IT IS NULL.

    Konyo, on Dean's fleet card: *"it should read he hasnt yet synced his uniques.. sets and
    runewords has been verified by him already and accepted"*. Three ledgers, three different
    sentences, and `control_ui.html:19562` renders one blanket band above all three from a single
    `t.onOwnerSeed`.

    ⚠⚠ THE DEFECT THIS ROW EXISTS FOR IS A DISAGREEMENT NO SINGLE COMPONENT CAN SEE, and it was
    live on his own console. OBSERVED 2026-09-06T18:49Z, on a tally 0.0 h old — not a stale read:

        /api/board_ownership        onOwnerSeed: true   (seedsBelongHere true, ledger KonyoEndgame)
        his own row on /api/fleet   tally.onOwnerSeed: null

    Sixteen minutes later the same two reads both said `true`, so the field FLICKERS rather than
    being permanently absent — which is worse to diagnose and is why this belongs in a doctor.

    THE MECHANISM, proven structurally rather than by timing: there are TWO tally producers and
    only one carries the field. `grail_tally()` reads the live board and publishes it
    (control_app.py:2010); when the app window is not showing the board it falls back to
    `_tally_from_board_store()`, whose returned keys are exactly

        ['at', 'ok', 'profile', 'runewords', 'sets', 'source', 'uniques', 'why']

    — measured on his tree, no provenance among them — because the record it reads is banked by
    `/api/board_tally` from six keys (`who, route, sets, uniques, runewords, at`,
    control_app.py:26538) and the board never posts the rest. So whichever producer answers decides
    whether the warning can appear at all, and UNKNOWN renders as no warning.
    [[the-unjoined-end]] [[copy-drift]]

    ⚠ AND UNKNOWN IS NOT CLEAN. A console that cannot say where its rows came from is exactly as
    unable to warn as one that is wrong about it — the difference is only that nobody can tell.
    [[unknown-stays-unknown]]

    FREE: one shared board read (the same one three other checks already fold into) plus the
    fleet payload this console already holds. No second poke at the window he is looking at.
    [[borrowed-surface]]
    """
    try:
        import ledger_authority as LA
    except Exception as e:
        return UNKNOWN, "ledger_authority will not import, so nothing can say where a row came " \
                        "from: %s" % str(e)[:80]

    tbl = LA.seed_table()
    if not tbl.get("ok"):
        # a parser that cannot find its subject must never read as "there are no seeds"
        return MISSING, ("the seed literals could not be read out of bible.html, so no ledger can "
                         "be told inherited from earned: %s" % str(tbl.get("why"))[:180])
    seeds = "; ".join("%s %d" % (k, v["n"]) for k, v in sorted(tbl["seeds"].items()))

    got = _board_read()
    fleet = _get("/api/fleet")
    if not got and not fleet:
        return UNKNOWN, "neither the board nor the fleet answered — nobody looked, so nothing is " \
                        "known about any ledger's provenance"

    board_seed = (got or {}).get("onOwnerSeed") if isinstance(got, dict) else None
    board_loaded = (got or {}).get("boardLoaded") if isinstance(got, dict) else None

    me = (fleet or {}).get("me") if isinstance(fleet, dict) else None
    rows = list((fleet or {}).get("online") or []) + list((fleet or {}).get("offline") or [])
    mine = next((m for m in rows if isinstance(m, dict) and m.get("machine") == me), None)
    wire_seed = ((mine or {}).get("tally") or {}).get("onOwnerSeed") if mine else None

    # ── THE CONTRADICTION, which is the finding rather than an error bar ─────────────────────
    if isinstance(got, dict) and got.get("ok") and board_loaded and board_seed is not None \
            and mine is not None and wire_seed != board_seed:
        return MISSING, (
            "this console's BOARD says onOwnerSeed=%r and its own FLEET ROW publishes %r — the "
            "card he reads is fed by the row, so right now the warning cannot appear here whatever "
            "the board says. Two tally producers, one field: grail_tally() carries it "
            "(control_app.py:2010) and _tally_from_board_store() cannot, because /api/board_tally "
            "banks only who/route/sets/uniques/runewords/at (control_app.py:26538), so the flag "
            "flickers with whichever producer answered. Fix: publish the provenance on the board's "
            "POST too, and per ledger. Seeds parsed: %s"
            % (board_seed, wire_seed, seeds))

    # ── the per-ledger sentence, derived from counts only; no name crosses the boundary ──────
    flagged, unknown_rows, deficits = [], [], []
    for m in rows:
        t = (m or {}).get("tally")
        if not isinstance(t, dict) or not t.get("ok"):
            continue
        who = (m.get("nickname") or m.get("machine") or "?")
        v = LA.classify_row(t, table=tbl)
        if t.get("onOwnerSeed") is None:
            unknown_rows.append(who)
            continue
        for led in v.get("ledgers") or []:
            if led.get("beyondSeed") is not None and led["beyondSeed"] < 0:
                deficits.append("%s %s %d/%s vs a seed of %s"
                                % (who, led["ledger"], led["have"], led["total"], led["seedN"]))
            elif led.get("provenance") == LA.SEEDED:
                flagged.append("%s %s %s of %s inherited"
                               % (who, led["ledger"], led["seedN"], led["have"]))

    if deficits:
        return MISSING, ("a board reports FEWER rows than the owner's seed would have written into "
                         "it, so its own progress cannot be separated from the seed by counting: "
                         "%s. That is a real gap in that store, not a rounding artefact — the "
                         "figure is negative and is reported as such rather than clamped to zero."
                         % "; ".join(deficits[:4]))
    if board_seed is None and not flagged and unknown_rows:
        return UNKNOWN, ("no console on the fleet could say whether its rows came from the owner's "
                         "seed (%s) — UNKNOWN, not clean. Seeds parsed: %s"
                         % (", ".join(sorted(set(unknown_rows))[:4]), seeds))
    return OK, ("every ledger can state its provenance; %d parsed seed(s) [%s]%s"
                % (len(tbl["seeds"]), seeds,
                   ("; flagged: " + "; ".join(flagged[:4])) if flagged else "; none inherited"))


def _check_no_ledger_FIGURE_has_gone_stale_unnoticed():
    """v2746 — THE SEED SAT 46 FINDS BEHIND FOR MONTHS AND NOTHING WAS WATCHING AGE AT ALL.

    Konyo: *"_GRAIL_SEED 245 uniques but this is my owner seed.. and even that is so outdated.. its
    at 292/403 we already said and sets 123/135.... it needs to auto update and not be stale"* and
    then *"connect it all to the heart of the console so nothing becomes stale again"*.

    ⚠⚠ THIS IS DELIBERATELY NOT A SEED CHECK. A seed-specific row would fix one frozen constant and
    leave the next one to rot identically. It walks EVERY ledger figure by KIND — live reads, other
    machines' beacons, hardcoded constants — so a constant added tomorrow is graded the day it
    appears.

    ⚠⚠ AND THE FROZEN ONES ARE GRADED BY **DRIFT**, NEVER BY AGE. This is the single way the whole
    fix could have gone quietly vacuous: re-parsing bible.html every tick makes the READ fresh and
    leaves the VALUE exactly as old, so a watchdog that timed the read would report every seed as
    seconds old forever while it drifted by fifty finds. Nothing anywhere records when a seed was
    transcribed, so its age is not merely unknown — it is unmeasurable, and `ageKnown` is False for
    that KIND regardless of any timestamp. What IS measurable is how far it has fallen behind the
    live figure. MEASURED on his board: uniques seed 246 against a live 292 (46 behind), sets seed
    108 against 123 (15 behind), runewords 99 against 99 (level).
    [[stale-reading]] [[unknown-stays-unknown]]

    ⚠ THE BEACON THRESHOLD IS DERIVED FROM THE PIPELINE IT GRADES, not invented: the beacon fires
    every 240 s, `_TALLY_TTL_S` caches the tally, `fleet_presence` caches the roster 60 s, so a
    perfectly healthy figure is legitimately that sum old. The stale line is a multiple of the whole
    chain and the row shows its arithmetic — a threshold under the floor cries wolf and one over the
    ceiling never fires, and both look exactly like no threshold at all.
    [[feedback-threshold-above-the-ceiling]]

    FREE: reuses the one shared board read and the fleet payload the console already holds.
    """
    try:
        import ledger_authority as LA
    except Exception as e:
        return UNKNOWN, "ledger_authority will not import, so no figure's age is known: %s" % str(e)[:80]

    got = _board_read()
    fleet = _get("/api/fleet")
    if not got and not fleet:
        return UNKNOWN, ("neither the board nor the fleet answered — no figure could be dated, "
                         "which is UNKNOWN and not the same as everything being fresh")
    try:
        st = LA.staleness(own=got if isinstance(got, dict) else None,
                          fleet=fleet if isinstance(fleet, dict) else None)
    except Exception as e:
        return UNKNOWN, "the staleness walk raised: %s" % str(e)[:110]

    rows = st.get("rows") or []
    if not rows:
        # a reader that finds nothing to grade is broken, not clean
        return UNKNOWN, "no ledger figure could be enumerated at all — a watchdog with nothing in " \
                        "front of it is not a pass"
    ceil = st["ceiling"]
    drifted = [r for r in rows if r.get("kind") == LA.FROZEN and r.get("stale") is True]
    # ⚠⚠ v3268 — A SWITCHED-OFF LAPTOP IS NOT A LEDGER FIGURE OUT OF DATE. This row said
    # "3 of 10 ledger figure(s) are out of date" and the third was Dean's Windows machine, off
    # since 2026-09-15 — a fact `/api/fleet` already publishes by putting it in `offline`.
    # Counting it here inflates the number he acts on with something no action of his can fix,
    # and buries the two that he CAN act on. [[label-outlived-referent]] [[zero-needs-a-denominator]]
    # ⚠ AND IT IS NOT SILENCED: `off` gets its own sentence below. A peer that is ONLINE and has
    # gone quiet stays in `old`, which is the real fault this check exists to catch.
    off = [r for r in rows if r.get("machineOff")]
    old = [r for r in rows
           if r.get("kind") == LA.BEACON and r.get("stale") is True and not r.get("machineOff")]
    # ⚠⚠ v3313 — A COMPARISON THAT WAS NEVER VALID IS NOT AN UNKNOWN AGE. `uniques seed` carried
    # a permanent `+N behind` because its live figure is a ROSTER WALK and the seed is a NAME LIST.
    # It billed him every tick with a number no action could move, and it billed ME: it is why 67
    # names were written into the seed on 2026-09-18. Excluded here with its reason stated, the
    # same discipline as `off` above and `_BY_DESIGN_STATIONS` on the river row — an exemption that
    # can be audited instead of silently growing.
    nocmp = [r for r in rows if r.get("comparable") is False]
    # ⚠⚠ v3317 — SUBTRACT A SET, NOT TWO COUNTS. Found by the second eye on v3314: a row that is
    # BOTH machineOff and non-comparable would be subtracted TWICE from "how many are current",
    # under-reporting the figure and, on a small ledger, underflowing past zero.
    # MEASURED on the live walk when it was found: rows=10, off=1, nocmp=1, BOTH=0 — so the
    # printed number was correct THAT DAY. It was correct by accident: `machineOff` is stamped in
    # the fleet-beacon loop and `comparable` in the FROZEN seed loop, and nothing makes those two
    # populations disjoint. A count that is right only because two builders happen not to overlap
    # is a count waiting to diverge from the thing it counts. Identity, not equality: two distinct
    # rows may legitimately carry the same name. [[zero-needs-a-denominator]]
    _excluded = {id(r) for r in off} | {id(r) for r in nocmp}
    _nocmpsay = ("" if not nocmp else
                 " · %d figure(s) are not comparable by construction rather than out of date: %s"
                 % (len(nocmp), "; ".join(str(r.get("comparableWhy") or r["name"])
                                          for r in nocmp[:2])))
    dark = [r for r in rows if r.get("stale") is None and not r.get("machineOff")
            and r.get("comparable") is not False]

    if drifted or old:
        bits = []
        for r in drifted:
            # NAME the figure and say HOW FAR, never a count — a count alone is not actionable
            _ts = r.get("transcribedAt")
            if isinstance(_ts, (int, float)) and _ts > 0:
                bits.append("%s is %+d behind the live figure (value %s, newest date it records "
                            "%s, transcribed %s — %.1f day(s) before this read; drift, not age, "
                            "is still the verdict)"
                            % (r["name"], r["drift"], r["value"],
                               r.get("newestFindDate") or "none",
                               time.strftime("%Y-%m-%d", time.gmtime(_ts / 1000.0)),
                               max(0.0, (time.time() * 1000.0 - _ts) / 86400000.0)))
            else:
                bits.append("%s is %+d behind the live figure (value %s, newest date it records "
                            "%s, AGE UNKNOWN — a hardcoded literal records no transcription time)"
                            % (r["name"], r["drift"], r["value"], r.get("newestFindDate") or "none"))
        for r in old:
            bits.append("%s last spoke %.1f min ago (stale past %.1f min)"
                        % (r["name"], (r["ageMs"] or 0) / 60000.0, ceil["staleMs"] / 60000.0))
        # ⚠ the offline peers ride along in the same sentence rather than in a second row, so
        # the count in front and the explanation behind can never drift apart.
        _offsay = ("" if not off else
                   " · %d peer(s) are switched off rather than stale: %s"
                   % (len(off), "; ".join(str(r.get("why") or r["name"]) for r in off[:2])))
        return MISSING, ("%d of %d ledger figure(s) are out of date: %s.%s%s Threshold arithmetic: "
                         "beacon %.0fs + tally TTL %.0fs + fleet cache %.0fs = %.0fs ceiling, "
                         "x%d = %.0fs stale line (%s)."
                         % (len(drifted) + len(old), len(rows), "; ".join(bits[:4]), _offsay,
                            _nocmpsay,
                            ceil["parts"]["beaconPeriodS"], ceil["parts"]["tallyTtlS"],
                            ceil["parts"]["fleetCacheS"], ceil["ceilingMs"] / 1000.0,
                            ceil["parts"]["multiple"], ceil["staleMs"] / 1000.0, ceil["how"]))
    if off:
        # ⚠ NOT OK. Nothing is broken and nothing here is this console's to fix, but a figure whose
        # machine is dark is not a current one, and "every beacon is inside N min" would be a
        # measured claim about a peer nobody has heard from. Same call as the river's UNBUILT.
        # ⚠ v3313 — the exempt rows come OUT of "are current" here too. Counting a figure that
        # was never comparable as a current one is the same over-claim the OK branch carried, one
        # branch away, and this is the branch that fires on his console today.
        return UNKNOWN, ("%d of %d ledger figure(s) are current; %d peer(s) are switched off, so "
                         "their figures are last-known rather than stale: %s%s"
                         % (len(rows) - len(_excluded), len(rows), len(off),
                            "; ".join(str(r.get("why") or r["name"]) for r in off[:2]),
                            _nocmpsay))
    if dark:
        return UNKNOWN, ("%d of %d ledger figure(s) could not be dated at all (%s) — UNKNOWN age is "
                         "not a fresh one.%s" % (len(dark), len(rows),
                                                 ", ".join(r["name"] for r in dark[:4]), _nocmpsay))
    # ⚠ v3313 — THE CLEAN SENTENCE MUST NOT OVER-CLAIM. "every frozen constant is level with its
    # live figure" would be false the moment one of them is exempt from the comparison, and a
    # clean verdict that quietly covers an unexamined row is the green that lies.
    return OK, ("%d of %d ledger figure(s) are current; every COMPARABLE frozen constant is level "
                "with its live figure and every beacon is inside %.0f min.%s"
                % (len(rows) - len(_excluded), len(rows), ceil["staleMs"] / 60000.0, _nocmpsay))


def _check_read_names_lane(*_a, **_k):
    """Where the already-read names would go: the auto door, or his hand.

    ⛔ THIS ROW GOES RED ONLY ON MACHINE WORK. Names waiting on HIM are not a fault — his ruling of
    2026-09-07 makes the manual lane the correct destination for a rare (*"manual is the path for
    rares"*), so counting them as red would make the row cry wolf about the design working. Same
    discipline as `_BY_DESIGN_STATIONS` on the river row: an exemption with a stated reason, so it
    can be audited instead of silently growing.

    ⚠ WHAT WOULD MAKE IT RED: a name that CLEARS the witness bar, IS on a roster, has ONE
    referent, and still is not banked — the auto lane owing work it can do for free.

    ⚠ v3008 — HELD IS NOT OWED, AND THE DOOR NOW SAYS WHY. Measured live: ONE name clears the bar
    (Crescent Moon), and its name has multiple referents (two uniques share it, plus the
    Shael+Um+Tir runeword) — two witnesses corroborate a NAME, not an ITEM, so auto-banking would
    pick one of three referents on evidence that cannot distinguish them. The refusal was always
    correct; before this, the row reported it as owed work ("can take those for free"), which is
    a correct hold wearing a fault's clothes. (The earlier docstring's "today that count is 0"
    was measured true when written and is not now — judge the measurement, not the prose.)
    """
    try:
        import read_names_lane as _RNL
    except Exception as exc:
        return UNKNOWN, ("read_names_lane could not be imported (%s), so where the read names "
                         "would go is UNKNOWN" % type(exc).__name__)
    try:
        sp = _RNL.split()
    except Exception as exc:
        return UNKNOWN, "the read-names lane raised (%s) - UNKNOWN, not clean" % type(exc).__name__
    if not isinstance(sp, dict) or not sp.get("ok"):
        return UNKNOWN, ("the read-names lane could not measure: %s"
                         % str((sp or {}).get("why") or "no reason given")[:130])
    # ⚠ None is not 0. An unreadable roster means the classification never happened.
    if sp.get("tickable") is None:
        return UNKNOWN, ("the rosters could not be read (%s), so which read names could ever tick "
                         "is UNKNOWN" % str(sp.get("rosterWhy") or "")[:90])
    auto_t = sp.get("autoTickable") or 0
    tick = sp.get("tickable") or 0
    furn = sp.get("furniture") or 0
    _owed = sp.get("autoOwed")
    _held = sp.get("autoHeld")
    if _owed is None or _held is None:
        # an older lane (or an unreadable roster) cannot say held-vs-owed — fall back to the
        # blunt count rather than inventing the distinction
        if auto_t:
            return MISSING, ("%d read name(s) clear %d witness(es), are on a roster, and are "
                             "still not banked - and this lane predates the held/owed split, so "
                             "WHY cannot be told from here" % (auto_t, sp.get("minWitnesses")))
    else:
        if _owed:
            return MISSING, ("%d read name(s) clear %d witness(es), are on a roster with ONE "
                             "referent each, and are still not banked - the auto door can take "
                             "%s for free, the reading is already paid for"
                             % (len(_owed), sp.get("minWitnesses"), ", ".join(_owed[:6])))
        if _held:
            _v = "; ".join("%s (%d referents: %s)"
                           % (h.get("name"), len(h.get("referents") or []),
                              "/".join(h.get("referents") or []))
                           for h in _held[:4])
            return OK, ("the auto door is HOLDING %d name(s), and says why: %s. Two witnesses "
                        "corroborate a NAME, not an ITEM - banking would pick one referent on "
                        "evidence that cannot distinguish them. Correct hold, not owed work; his "
                        "hand stays the only door for these." % (len(_held), _v))
    return OK, ("no read name is owed to the auto lane. %d of %d read name(s) could ever tick and "
                "all of them fall to HIS hand (single-sighting, which is the normal case for a "
                "rare); %d more are locked-inventory fixtures that can never tick and account for "
                "over half of every sighting."
                % (tick, sp.get("names"), furn))


def _check_the_stage_shows_what_the_dom_claims(*_a, **_k):
    """Does the SCREEN agree with the DOCUMENT about the room? The contradiction is the finding.

    His words, 2026-09-07, over a photograph of a black room with the shelf open: *"connect it to
    the heart of the console too"*.

    MEASURED at that moment: shelf {open, filled, cards 3090} and theatre {open, loaded, painted,
    ink} — 3,090 cards built and the console calling itself painted, while he looked at black.

    ⚠⚠ THE SHELF DOOR HAS BEEN HARDENED THREE TIMES FOR THIS SAME COMPLAINT (v2446 swallowed,
    v2451 toggles, v2666 prove-from-the-rect), and every one of those guards proves the DOCUMENT.
    `painted` and `ink` are DOM measurements wearing pixel names. This row is the first thing in
    the console that holds the DOM's claim and the screen's reading side by side.

    ⚠ RED ONLY ON DISAGREEMENT. A dark room with nothing open is correct; an unlookable or covered
    window is UNKNOWN. Neither is a fault, and grading either as one would make this row cry wolf
    on the homepage. [[feedback-contradiction-is-the-finding]] [[unknown-stays-unknown]]
    """
    try:
        import stage_witness as _SW
    except Exception as exc:
        return UNKNOWN, ("stage_witness could not be imported (%s), so whether the screen agrees "
                         "with the DOM is UNKNOWN" % type(exc).__name__)
    try:
        v = _SW.verdict()
    except Exception as exc:
        return UNKNOWN, "the stage witness raised (%s) - UNKNOWN, not clean" % type(exc).__name__
    st = str((v or {}).get("state") or "UNKNOWN")
    why = str((v or {}).get("why") or "no reason given")[:300]
    if st == "CONTRADICTION":
        return MISSING, why
    if st == "AGREE":
        return OK, why
    return UNKNOWN, why


def _check_the_river_walk_is_walking(*_a, **_k):
    """Is anything actually WATCHING the river, and when did it last look?

    Konyo, 2026-09-07: *"honest and accurate and pinpointed of course.. i want it visually synced
    to the backend"* — of the shelf-as-river view he asked for.

    ⚠⚠ THE SILENCE THIS BREAKS. `_retro_triage_loop` walks the river every tick and reports two of
    three outcomes: it prints transitions when something MOVED and "NOT WALKED" when the walk
    FAILED. A successful walk finding NOTHING printed nothing and stored nothing. MEASURED before
    this row existed: 40 stamps, all `by: claude:first-wiring`, newest 12.8h old, 0 carrying a
    `from` — not one row written by the loop. That is equally consistent with "the river is still"
    and "the loop never runs", and nothing could tell them apart.

    ⛔ IT DOES NOT GO RED ON A STILL RIVER. `moved: 0` is a perfectly good answer — most ticks find
    nothing, by design, and a row that reddens on the normal case is a row he stops reading. It
    goes red on the WATCHING stopping, not on the water being calm.
    [[feedback-silence-is-not-evidence]] [[unknown-stays-unknown]]
    """
    # ⚠⚠ v3012 — THIS ROW MEASURED A DEAD TWIN FOR ITS ENTIRE LIFE. It did `import control_app`
    # and read `river_walk_state()` — a MODULE GLOBAL. The console runs control_app as its own
    # process entry, so that import builds a SECOND module instance whose _RIVER_WALK is the empty
    # literal: at=None, in every process, since the row was born. PROVEN by one payload read two
    # ways at the same instant: /api/status.riverWalk said walks=13, at 15s old, while this row's
    # eagle copy said "has not completed a tick in this process — unaskable for 4d (1468
    # attempts)". Four days of UNKNOWN about a walk that ran the whole time. The WIRE is the one
    # authority — the serving process publishes its own _RIVER_WALK there — and it is honest from
    # a standalone doctor process too, which the import never was.
    # [[the-unjoined-end]] [[feedback-suspect-the-instrument]]
    _stw = _get("/api/status") or {}
    st = _stw.get("riverWalk")
    if st is None:
        return UNKNOWN, ("the console did not answer (or predates the riverWalk field), so "
                         "whether the river is being walked is UNKNOWN")
    if not isinstance(st, dict):
        return UNKNOWN, "the river walk state is unreadable"
    if st.get("at") is None:
        # ⚠ NEVER "no movement". Nobody has looked yet in that process.
        return UNKNOWN, str(st.get("why") or "the river walk has never completed a tick there")
    import time as _t
    age = round(max(0.0, _t.time() - float(st["at"])), 1)
    if st.get("ok") is False:
        return MISSING, ("the last river walk FAILED %ss ago: %s"
                         % (age, str(st.get("why"))[:150]))
    # a walk older than several ticks means the loop has stopped, not that the water is calm
    if isinstance(age, (int, float)) and age > 900:
        return MISSING, ("nothing has walked the river for %.0f minute(s) — the loop reports every "
                         "tick, so this is the WATCHER stopping rather than a still river"
                         % (age / 60.0))
    return OK, ("walked %ss ago: %s reel(s) compared, %s moved (%s walk(s) this process). A still "
                "river is the normal answer; this row goes red when the WATCHING stops."
                % (age, st.get("reels"), st.get("moved"), st.get("walks")))


def _check_the_retention_drain_is_draining(*_a, **_k):
    """2026-09-27 — DOES THE RIVER EMPTY AT ITS MOUTH, PASS AFTER PASS?

    Konyo: *"session reels in shelf registered by FIFO first in first out and getting extracted and
    tallied and ledgered accoridngly to its won indivudal console ... and allproeprly getting delted
    after the 8 sessions"* — and *"the heart too dont forget"*.

    ⚠ WHAT NOTHING WATCHED. The retention pass releases every finished reel older than the newest
    KEEP_RECENT on every pass. If the deleter stops — a lock that holds, a board world that never
    confirms, a switch left off, an rmtree that keeps failing — reels pile up at the mouth and every
    other row stays green: shelf_driver's `deleter` lane declares no work period, so it can only
    ever say UNTIMED. This row reads the drain's own contract (reel_retention.drain_state, published
    on /api/status.retention.drain) and goes red when releasable reels have been carried through
    `stoppedAfter` consecutive passes with nothing released — the brief's "owed > 0 for longer than
    two passes". A drain that is merely busy (new reels finishing every pass and being released)
    does NOT go red: each of those passes released what it owed. A pass deferred because the
    console is ON AIR or a sweep is reading is DEFERRED, and this row stays OK. STOPPED is only
    a run of passes that owed reels, released nothing, and carried no deferral.

    ⚠ IT READS THE WIRE, NEVER `import control_app` — that builds a second module whose state is
    the empty literal, the four-day twin (test_the_doctor_reads_the_console_not_a_twin).
    ⚠ UNKNOWN when the plan cannot run, UNMEASURED on a console that has never filmed, and UNKNOWN
    again when the newest reading is older than `stoppedAfter` periods — a stale reading may not
    certify the drain, and whether the LOOP is alive is lane_liveness's question, not this row's.
    ⚠ #84 (REG-1517) — BLOCKED is the river holding reels older than the newest keep window
    UPSTREAM of the mouth (the drain's `upstream` reading, from the river's own positions). This
    row goes MISSING when the longest-waiting one has sat past the console's declared bar (6 h),
    OK inside it, and UNKNOWN when the wait cannot be read — a CLEAR that only counted the mouth
    read OK over the ALT's 110 blocked reels.
    [[heart-first]] [[unknown-stays-unknown]] [[feedback-silence-is-not-evidence]]
    """
    _stw = _get("/api/status") or {}
    rt = _stw.get("retention")
    if rt is None:
        return UNKNOWN, ("the console did not answer (or predates the retention field), so whether "
                         "the drain is moving is UNKNOWN")
    if not isinstance(rt, dict):
        return UNKNOWN, "the retention state is unreadable, so the drain is UNKNOWN"
    dr = rt.get("drain")
    if not isinstance(dr, dict):
        return UNKNOWN, ("the console publishes no drain contract (it predates it), so whether "
                         "releasable reels are leaving is UNKNOWN")
    if dr.get("neverRecorded"):
        return UNMEASURED, ("nothing has ever been recorded on this console, so there is no shelf to "
                            "drain yet — a console that has not filmed, not a drain that stopped")
    state = dr.get("state")
    _after = dr.get("stoppedAfter")
    _every = dr.get("everyS")
    _at = dr.get("at")
    if (isinstance(_at, (int, float)) and isinstance(_every, (int, float)) and _every > 0
            and isinstance(_after, int) and _after > 0):
        _age_s = max(0.0, time.time() - float(_at) / 1000.0)
        # ⚠ A STALE DRAIN IS UNKNOWN, NOT MISSING. Past its own cadence the reading describes a
        # moment that is gone, so it may not certify the drain — but calling it STOPPED would be a
        # finding about the LOOP, and whether that thread is alive is lane_liveness's question
        # (`_lane_tick('tvd-retention')`), not this row's. It also keeps a false red off his screen
        # after the Mac sleeps: the retention thread's sleep does not advance while the machine
        # does, so the first eagle tick after waking sees an old `at` from a healthy loop.
        # [[stale-reading]] §4 [[copy-drift]]
        if _age_s > float(_every) * _after:
            return UNKNOWN, ("the drain's newest reading is %.0f minute(s) old — older than %d "
                             "retention periods of %.0fs — so whether the shelf is still draining "
                             "is UNKNOWN (it last said %s); whether the loop itself is alive is "
                             "the lane liveness row's to say"
                             % (_age_s / 60.0, _after, float(_every), str(state)))
    _worked = dr.get("worked")
    _tail = (" · the deleter has released %s reel(s) on this console%s"
             % (_worked if _worked is not None else "an UNKNOWN number of",
                "" if dr.get("lastTs") is None else
                ", the last %.1fh ago" % max(0.0, (time.time() * 1000.0 - float(dr["lastTs"]))
                                              / 3600000.0)))
    if state == "STOPPED":
        return MISSING, str(dr.get("why") or "the drain has stopped") + _tail
    if state == "BLOCKED":
        # #84 (REG-1517) — reels older than the newest keep window are waiting UPSTREAM of the mouth
        # (the ALT: EMPTY 91 / PRINTER 33 behind a closed reel.route lock, and this row read OK over
        # a CLEAR that counted only the mouth). The wait is the river's own arrival stamp for the
        # longest-waiting blocked reel (`upstream.oldestS`), held against the bar the console
        # declared (`upstream.afterS`, its RIVER_STUCK_AFTER_S) — never a clock this doctor keeps,
        # which a relaunch would reset. A wait that cannot be read is UNKNOWN, never a pass.
        _up = dr.get("upstream") if isinstance(dr.get("upstream"), dict) else {}
        _oldest, _after = _up.get("oldestS"), _up.get("afterS")
        _num = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)  # noqa: E731
        if not (_num(_oldest) and _num(_after) and _after > 0):
            return UNKNOWN, (str(dr.get("why") or "reels are blocked upstream") +
                             " — how long they have waited could not be read (oldestS %r, bar %r), "
                             "so whether this is a stall is UNKNOWN" % (_oldest, _after) + _tail)
        if float(_oldest) > float(_after):
            return MISSING, (str(dr.get("why") or "reels are blocked upstream") +
                             " — the longest wait is %.1fh, past the %.0fh bar"
                             % (float(_oldest) / 3600.0, float(_after) / 3600.0) + _tail)
        return OK, (str(dr.get("why") or "reels are blocked upstream") +
                    " — the longest wait is %.1fh, inside the %.0fh bar; this row goes MISSING past it"
                    % (float(_oldest) / 3600.0, float(_after) / 3600.0) + _tail)
    if state in ("CLEAR", "OWED", "DORMANT", "DEFERRED"):
        return OK, str(dr.get("why") or state) + _tail
    return UNKNOWN, str(dr.get("why") or "the drain's state is UNKNOWN") + _tail


#: a reel may wait in TRIAGE this long with no reel walked before the lane counts as STARVED. At
#: the measured ~0.02 s/frame one tick walks a whole reel, so 3 h is ~120 ticks of 90 s — not jitter.
TRIAGE_STARVED_AFTER_S = 3 * 3600
#: ⚠ 2026-09-28 — STANDING ASIDE FOR HIS GAME HAS ITS OWN BAR. Dean plays D2R natively for hours
#: ("usually" how he plays) and the lane refuses 'playing' on every tick BY DESIGN, catching up when
#: he stops — so a 3.5 h evening session read MISSING against the 3 h starve bar. While the lane's
#: LAST outcome is 'playing', the row is judged by how long the UNBROKEN run of 'playing' has lasted
#: (the console's playingForS) against this bar instead: OK up to it, MISSING past it — a D2R.exe left
#: open for days still starves the river, and still goes red. An adversarial review reproduced both.
TRIAGE_PLAYING_BAR_S = 12 * 3600
#: the triage loop's cadence (control_app._TRIAGE_EVERY_S) - the doctor never imports control_app
TRIAGE_EVERY_S_FOR_DOCTOR = 90


def _skips_dominated_by(skips, key):
    """Is `key` MORE THAN HALF of the lane's refusals in this process? -> (bool, n_key, n_all)"""
    n_key, n_all = 0, 0
    for k, v in (skips or {}).items():
        try:
            c = int(v or 0)
        except (TypeError, ValueError):
            continue
        n_all += c
        if k == key:
            n_key = c
    return (n_key > 0 and 2 * n_key > n_all), n_key, n_all


def _river_triage_count(riv):
    """Reels the river holds at TRIAGE right now. -> int | None (the river could not say)

    Summed from the four lanes' byStation — reel_router's live answer with the fixture reels already
    subtracted, the same population the shelf draws. None, never 0, when no lane answered."""
    lanes = riv.get("lanes") if isinstance(riv, dict) else None
    if not isinstance(lanes, dict) or not lanes.get("ok"):
        return None
    rows = lanes.get("lanes")
    if not isinstance(rows, list) or not rows:
        return None
    n, seen = 0, False
    for l in rows:
        by = (l or {}).get("byStation")
        if isinstance(by, dict) and "TRIAGE" in by:
            seen = True
            try:
                n += int(by.get("TRIAGE") or 0)
            except (TypeError, ValueError):
                return None
    return n if seen else None


def _check_triage_is_not_starved(*_a, **_k):
    """2026-09-28 — ARE REELS WAITING IN TRIAGE WHILE THE LANE THAT MOVES THEM IS NOT MOVING ANY?

    MEASURED over SSH on his Windows ALT (Boosteroid, shadow reader on, the hourly rollover live):
    7 of its 10 reels sat in TRIAGE — "the template is known and retro_triage has not walked its
    frames" — and nothing reached TOMBSTONE, so the FIFO drain correctly released nothing. The lane
    refused every 90 s tick beside a shadow reel that never stopped rolling, and printed only on
    success, and published nothing: a lane refusing for ever read exactly like a lane with nothing
    to do. His words: "this needs to be automated flow", "not stacking up".

    MISSING when the river holds reels at TRIAGE and they have waited more than
    TRIAGE_STARVED_AFTER_S with no reel walked — naming the lane's last refusal, how often each
    reason fired, and the backlog it counted. ⚠ 2026-09-28: the wait is the console's `waitS`,
    counted from the LATEST of the last walk, the last tick that found nothing owed and the first
    tick that found this backlog — not from the last walk alone, which after an idle day read a
    reel folded a minute ago as starved for a day. ⚠ 2026-10-06: that first-backlog mark survives
    a relaunch, and when the oldest waiting reel's own capture (`reelWaitS`) is the longer age the
    row judges by the reel, not by a process that just started. Process start is not the wait
    clock. A console that predates waitS and publishes no reel age is judged the old way (last
    walk, else process uptime).
    UNKNOWN when the lane's state cannot be read (no answer, a console that predates the field, an
    unreadable state), the river cannot say how many reels sit at TRIAGE, or the lane has not had
    two intervals to tick since its process started (the first periodic look at boot).
    UNMEASURED when the lane is stood down in this world BY DESIGN (a TV_STUB harness).
    OK otherwise — nothing waits in TRIAGE, or a reel was walked inside the bar.
    ⚠ 2026-09-28 — A LANE WHOSE LAST OUTCOME IS 'playing' is judged by its UNBROKEN run of play
    (playingForS) against TRIAGE_PLAYING_BAR_S (12 h): OK "standing aside for his game" up to it,
    MISSING past it. Standing aside while D2R.exe runs is by design; a game left open for days is not.
    And when 'playing-unknown' is MORE THAN HALF the refusals, the row says the play probe cannot run
    on this machine — a distinct sentence, since that lane is blind rather than busy.

    ⚠ IT READS THE WIRE, NEVER `import control_app` — that builds a second module whose
    _TRIAGE_LANE is the empty literal (test_the_doctor_reads_the_console_not_a_twin).
    ⚠ PERIODIC: /api/river recomputes reel_router over every reel on every call (REG-1305), and an
    hourly look loses nothing against a three-hour bar. [[heart-first]] [[unknown-stays-unknown]]
    [[feedback-silence-is-not-evidence]] [[the-unjoined-end]]
    """
    riv = _get("/api/river", timeout=8)
    if not isinstance(riv, dict):
        return UNKNOWN, ("the console did not answer /api/river, so whether reels are stacking up "
                         "in TRIAGE behind a starved lane is UNKNOWN")
    tri = riv.get("triage")
    if not isinstance(tri, dict):
        return UNKNOWN, ("the console publishes no triage lane state on /api/river (it predates "
                         "it), so whether the lane is walking reels is UNKNOWN")
    if tri.get("ok") is False:
        return UNKNOWN, ("the triage lane's state could not be read (%s), so whether it is starved "
                         "is UNKNOWN" % str(tri.get("why") or "no reason given")[:110])
    if tri.get("stoodDown"):
        return UNMEASURED, ("the triage lane is stood down in this world BY DESIGN (a TV_STUB "
                            "harness) — it will never walk a reel here, which is not a starved lane")
    n = _river_triage_count(riv)
    if n is None:
        return UNKNOWN, ("the river could not say how many reels sit in TRIAGE (%s), so whether "
                         "the lane is starved is UNKNOWN"
                         % str(((riv.get("lanes") or {}).get("why")) or riv.get("why")
                               or "no lanes answered")[:110])
    skips = tri.get("skips") if isinstance(tri.get("skips"), dict) else {}
    top = ", ".join("%s ×%s" % (k, v) for k, v in
                    sorted(skips.items(), key=lambda kv: -int(kv[1] or 0))[:5])
    backlog = tri.get("backlog")
    since = tri.get("sinceSurveyS")
    up = tri.get("upS")
    detail = ["refusals in this process: " + (top or "none recorded"),
              "backlog the lane counted: %s" % ("UNKNOWN (no tick has counted it yet)"
                                                if backlog is None else backlog),
              "last walk: %s" % ("never" if tri.get("lastSurveyTs") is None else
                                 "%s via %s" % (tri.get("lastReel") or "a reel",
                                                tri.get("lastSurveySource") or "?"))]
    if isinstance(tri.get("waitS"), (int, float)):
        detail.append("the wait is counted from %s (%.1f h ago)"
                      % (tri.get("waitFrom") or "?", float(tri["waitS"]) / 3600.0))
    if not n:
        return OK, ("no reel waits in TRIAGE — nothing is stacking up behind the triage lane", detail)
    # ⚠ 2026-09-28 (L1) — AT BOOT THE FIRST PERIODIC LOOK LANDS BEFORE THE LOOP'S FIRST TICK (it sleeps
    # _TRIAGE_EVERY_S before ticking), and the row read "NONE RECORDED — the loop may not be running"
    # after every relaunch. A lane that has not had two intervals to tick is not yet a lane that
    # failed to. `ticks` is absent on a console that predates it, so only an explicit 0 counts.
    _every = tri.get("everyS")
    if (tri.get("ticks") == 0 and isinstance(up, (int, float))
            and isinstance(_every, (int, float)) and float(up) < 2.0 * float(_every)):
        return UNKNOWN, ("%d reel(s) wait in TRIAGE and the triage lane has not ticked yet in this "
                         "process (up %.0f s; it first ticks after %.0f s) — whether it is walking "
                         "them is UNKNOWN, not starved" % (n, float(up), float(_every)), detail)
    # ⚠ 2026-09-28 — STANDING ASIDE FOR HIS GAME IS BY DESIGN, UP TO A BAR OF ITS OWN. While the lane's
    # LAST outcome is 'playing' (D2R.exe runs on that machine), the reels wait because he is playing,
    # not because the lane is broken: judged by the 3 h starve bar, Dean's 3.5 h evening session read
    # MISSING. So a 'playing' lane is judged by how long the UNBROKEN run of 'playing' has lasted
    # (playingForS, counted by the console: the first tick of the run, cleared by any other outcome)
    # against TRIAGE_PLAYING_BAR_S — OK up to it, MISSING past it, because a D2R.exe left open for
    # days starves the river as surely as a dead loop. A console that predates playingForS falls
    # through to the old judgement below. [[unknown-stays-unknown]]
    _pf = tri.get("playingForS")
    # ⚠ review round 2: the 'playing' sentence is true only while the lane is still ticking. A dead loop or a
    # hung walk after a 'playing' tick read OK "standing aside for his game" for up to 12 h (the game long shut);
    # a tick older than 2 x the cadence falls through to the wait judgement, which names the stale tick.
    _la = tri.get("lastAgoS")
    _fresh = (isinstance(_la, (int, float)) and not isinstance(_la, bool)
              and _la <= 2 * float(tri.get("everyS") or TRIAGE_EVERY_S_FOR_DOCTOR))
    if (tri.get("lastKey") == "playing" and isinstance(_pf, (int, float))
            and not isinstance(_pf, bool) and _fresh):
        _pf = float(_pf)
        detail.append("an unbroken run of 'playing' for %.1f h (bar %.0f h)"
                      % (_pf / 3600.0, TRIAGE_PLAYING_BAR_S / 3600.0))
        if _pf <= TRIAGE_PLAYING_BAR_S:
            return OK, ("standing aside for his game - %d reel(s) wait, %.1f h of unbroken play "
                        "(D2R.exe runs on this machine; bar %.0f h) - triage catches up when he stops"
                        % (n, _pf / 3600.0, TRIAGE_PLAYING_BAR_S / 3600.0), detail)
        return MISSING, ("%d reel(s) wait in TRIAGE and the lane has stood aside for his game for %.1f h "
                         "without a break (bar %.0f h) - a D2R.exe left open that long starves the "
                         "river. Its last refusal: %s [playing]. Backlog: %s reel(s) owed a survey."
                         % (n, _pf / 3600.0, TRIAGE_PLAYING_BAR_S / 3600.0,
                            str(tri.get("lastWhy") or "he is playing")[:140],
                            "UNKNOWN" if backlog is None else backlog), detail)
    # ⚠ 2026-09-28 — A PLAY PROBE THAT CANNOT RUN IS ITS OWN SENTENCE. 'playing-unknown' refuses every
    # tick on purpose (it will not guess whether he is playing), so a lane whose refusals are mostly
    # that is not "starved by load" or "starved by a camera" — it is blind on this machine, and will
    # stay blind until the probe can answer. Still refusing; the row says WHICH kind of stuck.
    _blind, _n_pu, _n_all = _skips_dominated_by(skips, "playing-unknown")
    probe_blind = ("the play probe cannot run on this machine - %d of %d refusals were "
                   "'playing-unknown', so every tick refuses rather than guess whether he is "
                   "playing, and it will keep refusing until the probe can answer (%s)"
                   % (_n_pu, _n_all, str((tri.get("lastSkipWhy") if tri.get("lastSkipKey") ==
                                          "playing-unknown" else "") or "no reason recorded")[:120])
                   if _blind else "")
    wait = tri.get("waitS")
    if isinstance(wait, (int, float)) and not isinstance(wait, bool):
        # ⚠ 2026-09-28 (M2) — HOW LONG THE REELS HAVE WAITED, NOT HOW LONG SINCE THE LAST WALK. After an
        # idle day the last walk is a day old, so a reel folded 30 s ago (still settling) or held ten
        # minutes behind 'playing' read MISSING "24.0 h" — every evening he plays. waitS counts from
        # the LATEST of the last walk, the last tick that found nothing owed and the first tick
        # that found this backlog (see triage_lane_state). Not this process starting: a relaunch
        # made that the newest mark and a standing backlog never reached the bar.
        # The reel's own capture is the longer age when the mark was only just written and the
        # reel has been waiting. A young reel stays inside the bar. [[stale-reading]]
        age_s = float(wait)
        _from = str(tri.get("waitFrom") or "an unnamed mark")
        reel_wait = tri.get("reelWaitS")
        if isinstance(reel_wait, (int, float)) and not isinstance(reel_wait, bool):
            if float(reel_wait) > age_s:
                age_s = float(reel_wait)
                _from = "the oldest waiting reel's own capture"
        _re = tri.get("relaunches")
        _across = (" across %d relaunches" % _re
                   if isinstance(_re, int) and not isinstance(_re, bool) and _re >= 2 else "")
        if _from == "the oldest waiting reel's own capture":
            if tri.get("lastSurveyTs") is None:
                span = ("has NEVER walked a reel, and the oldest waiting reel was filmed %.1f h "
                        "ago%s" % (age_s / 3600.0, _across))
            else:
                span = ("has left the oldest waiting reel unwalked for the %.1f h since it was "
                        "filmed%s" % (age_s / 3600.0, _across))
        elif tri.get("lastSurveyTs") is None:
            span = ("has NEVER walked a reel, and %.1f h have passed since %s%s"
                    % (age_s / 3600.0, _from, _across))
        else:
            span = ("has walked no reel in the %.1f h since %s%s"
                    % (age_s / 3600.0, _from, _across))
    elif since is not None:
        age_s = float(since)
        span = "has not walked a reel for %.1f h" % (age_s / 3600.0)
    elif up is not None:
        age_s = float(up)
        span = "has NEVER walked a reel, in the %.1f h this process has run" % (age_s / 3600.0)
    else:
        return UNKNOWN, ("%d reel(s) wait in TRIAGE and the lane reports neither its last walk nor "
                         "how long it has been up, so how long they have waited is UNKNOWN" % n)
    bar_h = TRIAGE_STARVED_AFTER_S / 3600.0
    if age_s > TRIAGE_STARVED_AFTER_S:
        if probe_blind:
            return MISSING, ("%d reel(s) wait in TRIAGE and the triage lane %s (bar %.0f h): %s. "
                             "Backlog: %s reel(s) owed a survey."
                             % (n, span, bar_h, probe_blind,
                                "UNKNOWN" if backlog is None else backlog), detail)
        last = tri.get("lastSkipWhy") or tri.get("lastWhy")
        said = ("%s [%s]" % (str(last)[:140], tri.get("lastSkipKey") or tri.get("lastKey"))
                if last else "NONE RECORDED — no tick has reported at all, so the loop itself may "
                             "not be running")
        return MISSING, ("%d reel(s) wait in TRIAGE and the triage lane %s (bar %.0f h). Its last "
                         "refusal: %s. Backlog: %s reel(s) owed a survey."
                         % (n, span, bar_h, said, "UNKNOWN" if backlog is None else backlog), detail)
    return OK, ("%d reel(s) wait in TRIAGE and the lane %s — inside the %.0f h bar%s"
                % (n, span, bar_h, ("; but " + probe_blind) if probe_blind else ""), detail)


#: ══ v#### — THE FOUR ROUTES GET FOUR ROWS, SO ONE CAN GO RED ALONE ════════════════════════════
#:
#: ⚠⚠ MEASURED 2026-09-08 over the fifty rows below: the ones that touch a reel's route are
#: `extraction lanes`, `vault stores`, `vault proposal`, `read names lane` and `names banked`, and
#: NOT ONE of them is per-route. `extraction lanes` watches lane_health's two SWEEP lanes
#: (chronicle, vault) — a different axis entirely — and inventory and stash shared its single
#: "vault" bucket. chronicle-sets and chronicle-uniques were indistinguishable to every supervisor
#: in this file. If exactly one of the four routes died, every row here stayed green. A rail that
#: cannot name WHICH of four things broke is not watching four things.
#:
#: ⚠ AND THESE FOUR SHOW UNKNOWN ON HIS OWN MACHINE, WHICH IS THE POINT AND NOT A GAP. Measured
#: over his 49 reels: stash 11, inventory 2, chronicle 1 — and that one chronicle reel recorded no
#: ledger, so both chronicle routes are taken by ZERO reels. A row that could only ever read his
#: live store would be green forever and prove nothing; it reads UNKNOWN, and the gate
#: (test_the_four_routes_go_red_alone) supplies the input his footage never has.
#: [[gate-blind-to-unexercised-input]] [[unknown-stays-unknown]]
_routes_cache = {"active": False, "got": None}


def _route_census_once():
    """The four-route census, live. -> dict. An owner that will not answer is UNKNOWN, never OK."""
    try:
        import reel_templates as _RT
        return _RT.route_census()
    except Exception as e:
        return {"ok": False, "state": "UNKNOWN", "order": [], "routes": {},
                "why": "reel_templates would not answer (%s), so nothing is known about any "
                       "route" % str(e)[:90]}


def _route_read():
    """ONE census per tick. Four checks ask the same question and the answer walks the river.

    ⚠ SCOPED TO `run()` EXACTLY LIKE `_board_read`, and for the reason written there: a
    module-level cache with a TTL swallows a test's stub and serves the previous test's answer.
    A check called on its own always reads fresh, which is what every caller outside the rail
    expects. [[feedback-suspect-the-instrument]]
    """
    if _routes_cache["active"]:
        return _routes_cache["got"]
    return _route_census_once()


# REG-1840 - ONE reel_router.route() PER TICK. Four river checks ("the river", "river outlet", "river joints",
# "river owes what its engine says") each walked the whole shelf through route() on their own: measured on his Mac
# 2026-10-06 with 80 reels on disk, 1.4-2.4 s of CPU EACH, and the cheap-subset law read 10.1 s against its 9 s budget
# while the v3596 push ran its shards - so the stuck river made its own watchdog four times dearer. Scoped to run()
# exactly like _route_read: a check called on its own still asks route() fresh (every guard that patches route keeps
# working), a raise is re-raised to each caller as before, and each caller gets its OWN copy so no check can edit
# another's reading. [[feedback-suspect-the-instrument]]
_rroute_cache = {"active": False, "got": None}


def _reel_route_once():
    try:
        import reel_router as _rr
        return ("ok", _rr.route())
    except Exception as e:
        return ("err", e)


def _reel_route_read():
    """reel_router.route(), once per tick inside run(); fresh when a check is called on its own. -> dict (raises as route does)"""
    if _rroute_cache["active"]:
        got = _rroute_cache["got"]
        if got is None:
            got = _rroute_cache["got"] = _reel_route_once()
        kind, val = got
        if kind == "err":
            raise val
        import copy as _copy
        return _copy.deepcopy(val)
    import reel_router as _rr
    return _rr.route()


def _route_health(route):
    """One of the four reel routes, ALONE. -> (name-bound fn) -> (state, detail)"""
    def run():
        cen = _route_read()
        rows = (cen or {}).get("routes") if isinstance(cen, dict) else None
        if not isinstance(rows, dict) or not rows:
            return UNKNOWN, ("the four-route census could not be read, so nothing is known about "
                             "the %s route: %s" % (route, str((cen or {}).get("why"))[:110]))
        r = rows.get(route)
        if not isinstance(r, dict):
            # a route that VANISHED from the census must never read as a route that passed
            return UNKNOWN, ("reel_templates no longer reports a %r route — it declares %s. A "
                             "route that disappeared is not a route that is well"
                             % (route, ", ".join(sorted(rows)) or "none"))
        st = str(r.get("state") or "")
        return ({"OK": OK, "BROKEN": MISSING}.get(st, UNKNOWN),
                str(r.get("why") or "the census gave no reason, so this route is UNKNOWN"))
    return run


def picker_census_verdict(rows, me=None, local=None):
    """#41 rank 22 (REG-1564) — every PC's picker census against its own database, one verdict. Pure over the rows.
    -> (state, why)

    `rows` are the fleet rows (online + offline) as /api/fleet carries them; `local` is THIS console's own banked
    census (_picker_for_wire), laid over the row named `me` exactly as the card gets it. Three lists, three states:
      MISSING  any PC whose picker offers other than what its own database holds - named, with both numbers - or
               whose board MEASURED its picker broken (a banked ok:false with its why: `broken`, h22 verifier)
      UNKNOWN  no PC reported a census, or one has not (an older build, an unreadable database) - named
      OK       every PC agrees, with the numbers
    A PC whose census is ok:false is UNKNOWN with that PC's own why, never a disagreement and never an agreement.
    [[heart-first]] [[unknown-stays-unknown]] [[feedback-contradiction-is-the-finding]]"""
    agree, differ, unknown, broken = [], [], [], []
    for row in (rows or []):
        if not isinstance(row, dict):
            continue
        name = str(row.get("nickname") or row.get("machine") or "?")
        pk = row.get("picker")
        # his own row takes his BANKED census, ok or broken (h22 verifier: a banked ok:false lost to the site's older
        # ok:true 45/45 and graded OK); nothing banked leaves the row's copy - absent is not zero
        if me and isinstance(local, dict) and (local.get("ok") or local.get("broken")) \
                and str(row.get("machine") or "") == str(me):
            pk = local
        if not isinstance(pk, dict):
            unknown.append("%s (no census reported - an older build)" % name)
            continue
        offers, holds = pk.get("offers"), pk.get("holds")
        if pk.get("ok") is not True and pk.get("broken") is True:
            broken.append("%s (%s)" % (name, str(pk.get("why") or "its board reported a failed count")[:90]))
            continue
        if pk.get("ok") is not True or not isinstance(offers, int) or not isinstance(holds, int) \
                or isinstance(offers, bool) or isinstance(holds, bool):
            unknown.append("%s (%s)" % (name, str(pk.get("why") or "could not count its picker")[:90]))
            continue
        slot = str(pk.get("label") or pk.get("slot") or "the slot")
        if offers == holds:
            agree.append("%s %d/%d" % (name, offers, holds))
        else:
            differ.append("%s: picker offers %d base(s) for %s, its database holds %d" % (name, offers, slot, holds))
    if broken:
        return MISSING, ("on %d PC(s) the board counted its character picker and the count FAILED - %s. That is a "
                         "measured broken picker, not a missing report: update and restart that console, then open a "
                         "Body Armor slot%s" % (len(broken), "; ".join(broken)[:240],
                                                ("; also: " + "; ".join(differ)[:120]) if differ else ""))
    if differ:
        return MISSING, ("on %d PC(s) the character picker does not offer what that PC's own database holds - %s. "
                         "The picker there is hiding rows (or its rail names a type its tree does not): update and "
                         "restart that console, then open a Body Armor slot and count"
                         % (len(differ), "; ".join(differ)[:300]))
    if unknown:
        return UNKNOWN, ("%d PC(s) have not said what their character picker offers: %s%s"
                         % (len(unknown), "; ".join(unknown)[:240],
                            (" - the rest agree: " + ", ".join(agree)[:120]) if agree else ""))
    if not agree:
        return UNKNOWN, "no PC is on the roster, so there is no picker to compare with its database"
    return OK, ("on every PC (%d) the character picker offers exactly what its own database holds for Body Armor: %s "
                "(the list function answers for that slot; no slot was clicked, and the mule host is not counted)"
                % (len(agree), ", ".join(agree)[:200]))


def _check_the_picker_census_agrees_on_every_pc():
    """★ #41 rank 22 (REG-1564) — WHAT EACH PC'S CHARACTER PICKER OFFERS, AGAINST WHAT ITS OWN DATABASE HOLDS.

    His ALT showed an empty picker for every mule slot for days (#174 v-B4) and nothing on any screen carried the
    number: the picker's offer was measured by nobody. Now every board hands its console a census (window
    ._cbPickerCensus('tors'): the picker's Base Items rows for the Body Armor slot as its own list function counts
    them, beside the bases its own type table folds to that slot), the beacon carries it per PC, and this row reads
    it back off the roster: MISSING when any PC's two numbers disagree (that PC's picker is hiding rows), UNKNOWN when
    a PC has not reported one, OK when every PC agrees.

    ⚠ IT READS THE CACHE AND NEVER FETCHES, and it never pokes the board - the same rule as the fleet row below:
    `_FLEET_PRESENCE_CACHE` is what /api/fleet serves the panel from, and his own row is overlaid from the banked
    local file exactly as the card is. A roster never asked for is UNKNOWN, not OK. [[heart-first]]
    [[unknown-stays-unknown]] [[borrowed-surface]]"""
    try:
        import control_app as _ca
    except Exception as e:
        return UNKNOWN, "control_app will not import (%s), so no PC's picker census is measured" % str(e)[:60]
    try:
        cache = _serving_console(_ca)._FLEET_PRESENCE_CACHE
    except Exception as e:
        return UNKNOWN, ("control_app no longer exposes _FLEET_PRESENCE_CACHE (%s), so no PC's picker census can "
                         "be read" % type(e).__name__)
    last = cache.get("d")
    if last is None:
        return UNKNOWN, ("this console has not asked the site for the roster yet, so what any PC's character "
                         "picker offers is UNKNOWN")
    if last.get("ok") is False:
        good = cache.get("goodD")
        if good is None:
            return UNKNOWN, ("the fleet is unreachable and no roster was ever received, so what any PC's "
                             "character picker offers is UNKNOWN")
        last = good
    rows = list(last.get("online") or []) + list(last.get("offline") or [])
    me, local = None, None
    try:
        import socket as _sk
        me = _sk.gethostname().split(".")[0]
        local = _ca._picker_for_wire()
    except Exception:
        me, local = None, None
    return picker_census_verdict(rows, me=me, local=local)


def _check_the_fleet_lane_is_reachable():
    """★ THE FLEET WENT UNREACHABLE ON HIS SCREEN AND NOTHING IN THE HEART KNEW THE WORD.

    2026-09-09 11:07, photographed from his own console: the FLEET card read
    `fleet unreachable — <urlopen error _ssl.c:1112: The handshake operation timed out>` while the
    heart's own footer two inches below said `♥ 8 dark` — and not one of those 8 was the fleet.
    Measured at the time: `grep -c fleet` was **0** in heart.py AND in lane_census.py, and CHECKS
    carried no fleet row. The lane was not failing its supervision; it HAD none. That is the
    registered-vs-existing gap (21 threads, 11 registered) with a name on it, and it is the first
    of the unregistered ten to fail somewhere he could see. [[the-unjoined-end]]

    ⚠⚠ IT READS THE CACHE AND NEVER FETCHES. fleet_presence() spends up to 6 SECONDS against an
    unreachable site, and that is the exact condition this row exists to notice — so a check that
    called it would add its own six-second stall to every doctor pass at precisely the moment the
    console is already degraded. Same rule _heart2_census() follows: read what the producer last
    wrote; never re-run the producer inside a request. [[poll-slower-than-its-interval]]

    ⚠⚠ IT IS DERIVED FROM THE SAME STATE THE CARD PAINTS, ON PURPOSE. His complaint was not that
    the fleet was down — it was that the SCREEN and the HEART disagreed while sitting two inches
    apart. A row computed from a second source could reproduce that disagreement in a new place, so
    this one reads `_FLEET_PRESENCE_CACHE`, which is what `/api/fleet` serves the panel from.

    ⚠ FOUR OUTCOMES, NOT TWO. "Never asked" is not "reachable"; and "unreachable holding a roster"
    is not "unreachable holding nothing" — the first still has something honest to put on the card,
    the second leaves him with a blank and is the only unrecoverable one. Collapsing them would
    grade a cold console as a broken one and hide the case that actually cannot be rendered.
    [[unknown-stays-unknown]] [[zero-needs-a-denominator]]
    """
    import time as _t
    try:
        import control_app as _ca
    except Exception as e:
        return UNKNOWN, "control_app will not import (%s), so the fleet lane is unmeasured" % str(e)[:60]
    try:
        cache = _serving_console(_ca)._FLEET_PRESENCE_CACHE
    except Exception as e:
        return UNKNOWN, ("control_app no longer exposes _FLEET_PRESENCE_CACHE (%s) — a cache that "
                         "vanished is not a fleet that is well" % type(e).__name__)
    last = cache.get("d")
    good, good_t = cache.get("goodD"), float(cache.get("goodT") or 0.0)
    now = _t.time()

    if last is None:
        # ⚠ NOT OK. A console that has never asked knows nothing about the fleet, and saying "ok"
        # here would mean the row reads green for the entire window in which it is most blind.
        return UNMEASURED, ("this console has not asked the site for the roster yet, so whether the "
                            "fleet is reachable is UNKNOWN — it is not 'reachable'")

    if last.get("ok") is not False:
        on = len(last.get("online") or [])
        off = len(last.get("offline") or [])
        age = round(max(0.0, now - float(cache.get("t") or 0.0)), 1)
        return OK, ("the site answered %ss ago — %d online, %d offline, %d machine(s) known"
                    % (age, on, off, on + off))

    why = str(last.get("error") or "no reason given")[:90]
    if good is None:
        return MISSING, ("the fleet is UNREACHABLE and this console has never received a roster, so "
                         "the panel has nothing honest to show at all — not a stale list, not a "
                         "count. Reason: %s" % why)
    g_on = len(good.get("online") or [])
    g_off = len(good.get("offline") or [])
    dur = round(max(0.0, now - good_t), 1) if good_t else None
    return MISSING, ("the fleet is UNREACHABLE%s, but a roster from that last contact is still in "
                     "hand — %d online, %d offline, %d machine(s) — so the panel can degrade to a "
                     "STALE list instead of a blank. Reason: %s"
                     % (("" if dur is None else " and has been for %ss" % dur),
                        g_on, g_off, g_on + g_off, why))


def _check_the_shelf_lanes_are_still_reading():
    """★ A LANE THAT STOPS READING MUST GO RED ON ITS OWN — Konyo, 2026-09-10, which is what
    `shelf_driver.py` was written for at v2909 (REG-908). It shipped 773 lines, a registered gate
    and 11 declared red-proofs, and then nothing ran it unattended.

    MEASURED 2026-09-11: `control_app.py` imports the module under TWO aliases (`_sd`, `_sd_lane`)
    and calls NOTHING on either — it reads only the constants `OWED_BY` and `READ_CLEARS`. An
    import with no call is the purest form of [[the-unjoined-end]]. His stored beat was **31.6
    hours old** and no supervisor anywhere said so: the lane was not failing its supervision, it
    HAD none — the same registered-vs-existing gap the fleet row above was added for.

    ⚠⚠ IT READS THE STORED BEAT AND NEVER RE-RUNS THE PRODUCER. `lane_census()` walks the lanes;
    calling it inside a doctor pass would add that walk to every request at exactly the moment the
    console is already degraded — the rule `_check_the_fleet_lane_is_reachable` states in its own
    docstring, and the one `_heart2_census()` follows. A stale beat IS the finding; re-running the
    producer would erase the very evidence this row exists to report. [[poll-slower-than-its-interval]]

    ⚠ AN ABSENT BEAT IS UNMEASURED, NOT HEALTHY. A driver that has never run says nothing about
    the lanes, and reporting that as OK is the zero-with-no-denominator this repo keeps paying for.
    [[unknown-stays-unknown]] [[zero-needs-a-denominator]]
    """
    try:
        import shelf_driver as _sd
    except Exception as e:
        return UNKNOWN, ("shelf_driver will not import (%s), so whether the lanes are still "
                         "reading is UNMEASURED" % str(e)[:60])
    try:
        beat = _sd.last_beat()
    except Exception as e:
        return UNKNOWN, ("the shelf driver could not be asked for its last beat (%s) — UNMEASURED, "
                         "not clean" % type(e).__name__)
    if not isinstance(beat, dict) or not beat.get("at"):
        return UNMEASURED, ("the shelf driver has never recorded a beat, so whether any lane is "
                            "still reading is UNKNOWN — it is not 'fine'")
    try:
        age_h = (time.time() * 1000.0 - float(beat["at"])) / 3600000.0
    except Exception:
        return UNKNOWN, "the stored beat carries an unreadable timestamp, so its age is UNKNOWN"
    owed = beat.get("owed")
    held = beat.get("held")
    tail = ("" if owed is None and held is None
            else " — it last reported %s owed, %s held, %s on disk"
                 % (owed, held, beat.get("onDisk")))
    if age_h >= _SHELF_BEAT_STALE_H:
        return MISSING, ("the shelf driver last beat %.1f HOURS ago (bar: %.0fh), so a lane that "
                         "stopped reading would not have been noticed%s"
                         % (age_h, _SHELF_BEAT_STALE_H, tail))
    if beat.get("neverRecorded"):
        # v3400 (#141) — #138's ruling, reaching the shelf at last. Nothing has ever been
        # recorded on this machine, so retention has no shelf to read. That is a NEW CONSOLE,
        # not a stalled lane, and calling it MISSING put a red row on his ALT box that he could
        # not act on and did not cause.
        return UNMEASURED, ("nothing has ever been recorded on this machine, so retention has "
                            "no shelf to read yet — that is a console that has not filmed, not "
                            "a lane that stopped")
    # REG-1783 (#86 gap 25) — `ok` defaulted to True, and a beat with no laneCounts
    # returned OK while its own sentence said UNKNOWN. The eagle colours the state word.
    # A plan that was not called readable, and a beat that counted no lanes, are UNKNOWN.
    # A plan that said not-ok stays MISSING. A counted DARK or STALLED lane stays MISSING.
    _told = beat["ok"] if "ok" in beat else None
    if _told is None:
        return UNKNOWN, (
            "the shelf driver beat %.1fh ago and did not say whether its plan was readable, "
            "so whether each lane is reading is UNKNOWN%s" % (age_h, tail))
    if _told is not True:
        return MISSING, ("the shelf driver's last beat %.1fh ago reported NOT ok: %s"
                         % (age_h, str(beat.get("why") or "no reason given")[:90]))
    # ⚠⚠ v2957 — `ok` IS ABOUT THE PLAN, NOT ABOUT A LANE, AND THIS ROW IS ABOUT LANES.
    # `beat["ok"]` is true whenever retention's plan was READABLE. A lane can be DARK or STALLED
    # underneath a perfectly readable plan, and until now this row would have said "reported ok"
    # over the top of it. That is REG-908's original complaint intact: `vaultAutoread` read 0 with
    # lastTs null for weeks and nothing said so. Wiring a producer WITHOUT this widen would have
    # flipped the row from permanently-MISSING to permanently-OK and left the fault unsurfaced —
    # a green that lies, bought with a fix. [[zero-needs-a-denominator]]
    _lc = beat.get("laneCounts")
    if isinstance(_lc, dict) and _lc:
        _bad = {k: v for k, v in _lc.items()
                if str(k).upper() in ("DARK", "STALLED") and isinstance(v, int) and v > 0}
        if _bad:
            return MISSING, ("the shelf driver beat %.1fh ago, but %s — a lane in that state has "
                             "stopped reading and the plan being readable does not cover it%s"
                             % (age_h, ", ".join("%d %s" % (v, k) for k, v in sorted(_bad.items())),
                                tail))
        return OK, ("the shelf driver beat %.1fh ago and every lane it counted is reading (%s)%s"
                    % (age_h, ", ".join("%s %s" % (v, k) for k, v in sorted(_lc.items())), tail))
    return UNKNOWN, ("the shelf driver beat %.1fh ago and reported ok; it recorded no per-lane counts, "
                     "so whether each lane is reading is UNKNOWN rather than confirmed%s" % (age_h, tail))


#: How old a shelf beat may be before a lane that stopped reading would go unnoticed. His driver
#: is a per-session tool, not a timer, so this is deliberately generous — it exists to catch a
#: driver that has FALLEN SILENT FOR A DAY, not one that has not run in an hour.
_SHELF_BEAT_STALE_H = 12.0

def _check_the_running_code_is_the_code_on_disk():
    """★ IS THE CONSOLE EXECUTING WHAT THE FILE SAYS? — task #67, and the one question the drift
    lane cannot answer.

    `drift_state()` compares the RUNNING version stamp against the DISK version stamp. Both are
    LABELS. Two different images can carry the same stamp, and he EXECS THE WORKING TREE — so every
    save to control_app.py that does not bump a version is a change the drift lane is blind to and
    this one can see.

    ⚠ IT ASKS THE CONSOLE, IT DOES NOT HASH ITS OWN IMPORT. This doctor may run in a different
    process; hashing `control_app` from here would measure THIS process's import and report it as
    the console's. Only the console knows what the console loaded, so the sha comes over the wire
    from `/api/status`'s `proc` block. [[borrowed-surface]]
    ⚠ AN OLDER CONSOLE HAS NO `srcSha`, AND THAT IS UNMEASURED, NOT CLEAN. A console started before
    v2961 publishes no such key; reporting that as OK would be the zero-with-no-denominator this
    file keeps paying for. [[unknown-stays-unknown]]
    """
    d = _get("/api/status")
    if not isinstance(d, dict):
        return UNKNOWN, ("the console could not be asked what code it is running, so whether it "
                         "matches the disk is UNMEASURED")
    # v3404b — AN ORGAN CAN BE STALE WHILE control_app.py IS NOT.
    # Measured 2026-09-20: moduleFreshness.stale=false (control_app sha matched) while
    # eagle "this machine keeps itself current" threw NameError on REPO inside
    # console_doctor that had already been fixed on disk. proc.srcSha only hashes
    # control_app.py, so it cannot see that miss. Read the freshness the console
    # already published rather than hashing a second copy. [[the-unjoined-end]]
    _mf = d.get("moduleFreshness") if isinstance(d, dict) else None
    if isinstance(_mf, dict) and _mf.get("stale") is True:
        _org = _mf.get("organs") if isinstance(_mf.get("organs"), list) else []
        _names = [str(o.get("src")) for o in _org
                  if isinstance(o, dict) and o.get("stale") is True and o.get("src")]
        _say = str(_mf.get("say") or
                   "the console reports its loaded code is not the files on disk")
        if _names:
            _say = _say + " (organs: %s)" % ", ".join(_names)
        return MISSING, _say
    proc = d.get("proc")
    if not isinstance(proc, dict) or not proc.get("srcSha"):
        return UNMEASURED, ("this console publishes no source hash — it was started before the "
                            "check existed, so what it is running cannot be compared to the disk. "
                            "That is UNMEASURED, not a match")
    name = str(proc.get("src") or "control_app.py")
    disk = None
    try:
        import hashlib
        with open(os.path.join(HERE, name), "rb") as fh:
            disk = hashlib.sha1(fh.read()).hexdigest()
    except Exception as e:
        return UNKNOWN, ("%s could not be read from disk (%s), so the comparison is UNMEASURED"
                         % (name, type(e).__name__))
    running = str(proc.get("srcSha"))
    if running != disk:
        return MISSING, ("the console is running BYTES THAT ARE NO LONGER ON DISK: it loaded %s "
                         "(%s...) and the file now hashes %s... — every save to this file is a "
                         "deploy here, and this one has not been picked up. Relaunch to adopt it."
                         % (name, running[:10], disk[:10]))
    return OK, ("the console is running exactly what %s holds on disk (%s...)" % (name, disk[:10]))


def _check_the_window_runs_the_document_on_disk():
    """IS THE PAGE IN FRONT OF HIM THE PAGE ON DISK? -> (state, why)

    ⚠⚠ THE QUESTION FOUR VERSION READINGS COULD NOT ANSWER. This console publishes `ver` (the
    working tree this process imports), `liveVer` (what origin/main last shipped), `bibleVer` and
    `agentVer` — and every one of them describes a FILE. None describes the DOCUMENT the webview
    is actually rendering, which is the only one that matters here, because his console execs the
    working tree and every save is a deploy.

    It cost real time. On 2026-09-12 and again on 2026-09-13 a `liveVer` trailing the tree was
    read — by me, and repeated back through the eyes queue — as "the reload did not take". It was
    nothing of the kind: `liveVer` lagging disk is CORRECT and EXPECTED for every commit not yet
    pushed, and `test_live_version_is_not_the_working_tree` exists to keep it that way. A question
    with no instrument gets answered by the nearest number that resembles one.
    [[label-outlived-referent]] [[inherited-claim-is-not-evidence]] [[unknown-stays-unknown]]

    v3057 puts the document's own D2R_BUILD id on the beat, so this row compares like with like.
    """
    st = _get("/api/status") or {}
    ub = st.get("uiBeat") if isinstance(st.get("uiBeat"), dict) else None
    if not ub:
        return UNKNOWN, "the console did not report a heartbeat, so no document version is known"
    if not ub.get("n"):
        return UNKNOWN, "no console has ever checked in — headless, not healthy"
    # ⚠ ITS OWN CONSTANT, DELIBERATELY. The 3600.0 twelve hundred lines below is a LOCAL inside
    # another check, so referencing it here would have raised NameError on the first live call —
    # caught before this shipped. 300s, not an hour: a document stamp answers "is what he is
    # looking at current", and a five-minute-old beat is already too old to say that.
    _DOC_STALE_S = 300.0
    age = ub.get("ageS")
    if age is None:
        return UNKNOWN, ("the console reports no beat age, so how old this document reading is "
                         "cannot be told — and a verdict on a reading of unknown age is a guess")
    if age > _DOC_STALE_S:
        return UNKNOWN, ("the console's last beat is %.0fs old, so its document stamp describes a "
                         "window nobody has heard from since" % age)
    doc = ub.get("docVer")
    if not doc:
        return UNKNOWN, ("this console does not report the document it is rendering (uiBeat.docVer "
                         "is absent) — it predates v3057, or the page had not assigned D2R_BUILD "
                         "when it beat. UNKNOWN, which is not the same as in step")
    # ⚠ COMPARE AGAINST THE FILE NOW, NOT AGAINST A VERSION LABEL. control_ui.html is not one of
    # the four surfaces bump_version stamps, so a version alone cannot tell a saved edit from no
    # edit. doc_signature() is the hash of the served BYTES — v3063 dropped the version from it, so
    # a version-only bump cannot false-alarm a window that is current — and it is what the
    # server stamped into
    # the document it handed this window.
    try:
        import control_app as _ca
        disk = _ca.doc_signature()
    except Exception as _e:
        return UNKNOWN, ("the served document could not be signed here (%s), so there is nothing "
                         "to compare against" % type(_e).__name__)
    if not disk:
        return UNKNOWN, "the console document could not be read from disk, so nothing can be compared"
    if str(doc) == str(disk):
        return OK, ("the window is rendering %s and that is exactly what this server would serve "
                    "now — the page in front of him IS the page on disk" % doc)
    return MISSING, ("THE WINDOW IS RUNNING AN OLDER DOCUMENT THAN THE TREE — it was handed %s and "
                     "this server would now serve %s. His console execs the working tree, so every "
                     "UI change since then is on disk and NOT on his screen; a reload that does not "
                     "move this value did not take. This is about the DOCUMENT, not about shipping "
                     "— liveVer trailing disk is a different fact and is normal for unpushed work."
                     % (doc, disk))


def _check_the_shelf_is_where_it_says_it_is():
    """THE CORROBORATOR FOR HIS BLANK STAGE — a fill and a rect that can contradict each other.

    GROKBOT, 2026-09-12, with `ver` and `liveVer` BOTH v2988: the shelf stage is an EMPTY DARK
    PANEL — no cards, no headings — and two stage crops 5s apart are BYTE-IDENTICAL, so it is not
    a slow paint. At that same moment the console's own beat said `filled=true, cards~535,
    ink=true`, and a headless probe against the same server built 530 cards with no JS error.

    Both readings were honest. A DOM can be fully built inside a container that occupies no
    pixels, and the beat published a FILL and never a RECT — so nothing in it could contradict
    his eyes. v2996 puts the overlay's rect on the wire; this is the row that reads the two
    together, because either half alone says nothing. [[the-unjoined-end]]

    ⚠ CLOSED IS NOT A FAULT. The shelf is an on-demand overlay and is shut almost always. This
    row fires only when it is OPEN and not on screen.
    """
    st = _get("/api/status") or {}
    ub = st.get("uiBeat") if isinstance(st.get("uiBeat"), dict) else None
    if not ub:
        return UNKNOWN, "the console did not report a heartbeat, so nothing is known about the shelf"
    if not ub.get("n"):
        return UNKNOWN, "no console has ever checked in — headless, not healthy"
    # ⚠⚠ v3002 — THIS ROW ISSUED TWO BRAND-NEW `MISSING` VERDICTS OFF A BEAT OF UNKNOWN AGE, in
    # the same file whose sibling row hard-codes STALE_S for exactly this reason. `ub["n"]` only
    # says a console checked in ONCE, EVER. Close the console with the shelf open and a card below
    # the fold — or let WebKit suspend the beat's setInterval, the documented v2348 failure — and
    # three hours later this would still read that frozen panels dict and report THE SHELF OPENS ON
    # NOTHING about a window that is not on screen at all. [[stale-reading]]
    _bage = ub.get("ageS")
    if _bage is None:
        return UNKNOWN, ("the console reports no beat age, so how old this panels reading is "
                         "cannot be told — and a verdict on a reading of unknown age is a guess")
    if _bage > 300.0:
        return UNKNOWN, ("the console's last beat is %.0fs old, so its panels reading describes a "
                         "window nobody has heard from since. Nothing is known about the shelf NOW."
                         % _bage)
    panels = ub.get("panels")
    if not isinstance(panels, dict) or not panels:
        return UNKNOWN, "this console does not report its panels — unknown, not clear"
    shelf = panels.get("shelf")
    if shelf is None:
        return UNKNOWN, ("this console reports no shelf overlay at all (o.shelf is null) — it is "
                         "not in this build, which is not the same as it being fine")
    if not isinstance(shelf, dict):
        return UNKNOWN, ("the shelf field is %s, not the {open, filled, cards, why} object this "
                         "row reads — something changed its TYPE" % type(shelf).__name__)
    state = shelf.get("box")
    if state is None:
        return UNKNOWN, ("this console predates v2996 and publishes a shelf FILL with no RECT — "
                         "the exact gap that let a blank stage and cards~535 coexist. Restart it, "
                         "or where the overlay sits stays unmeasurable from here.")
    if state == "closed":
        return OK, "the shelf overlay is shut — a fact, not a fault"
    cards = shelf.get("cards")
    grid = shelf.get("gridCards")
    if state == "shown":
        # ⚠⚠ v2998 — "THE PAIR IS THE POINT" AND THE PAIR WAS ONLY EVER PRINTED. `box == "shown"`
        # returned OK whatever the fill said, so an overlay that is open, on screen and EMPTY —
        # which is the failure he photographed — read as healthy. The page already computes the
        # verdict in `why` ("the shelf overlay is open and carries no cards and no text") and this
        # file had ZERO readers of it. A corroborator whose second half never reaches the verdict
        # is one half wearing the name of two. [[the-unjoined-end]] [[plumbing-with-no-tap]]
        # ⚠⚠ v3001 — THE v2998 PREDICATE FIRED ON A CORRECT UI STATE AND COULD NOT FIRE ON THE
        # REAL ONE. `filled` is `!!(_cards > 0 || _txt > 40)` and the overlay always ships its own
        # heading and status chrome, so `filled` is ALWAYS true while open and `why` is ALWAYS
        # null — the first disjunct was unreachable, and the second (`cards == 0 and grid == 0`)
        # matches the DELIBERATE "No runs recorded yet" hero. So it reported MISSING about a
        # console behaving correctly, while printing "the page itself says: filled=false" over a
        # payload that said filled=true. A row that cries wolf is one he learns to skip.
        _vis = shelf.get("visibleCards")
        # REG-3203 (GrokBot on v3864: his Mac's Shelf sat on "opening the shelf..." while the guest's filled) - AN
        # OPENING SHELF WORE THE EMPTY-HERO BOX, so this row called a stuck open "no runs to show yet - the correct
        # state". The page now publishes `opening` and how long it has said so; the page's own bound
        # (TH_SHELF_OPEN_BOUND_MS) turns a stuck one into the UNKNOWN shelf, and past that bound this row says MISSING.
        # REG-3203 - AND THE UNKNOWN SHELF IS NOT THE EMPTY ONE. What a stuck opening becomes at the page's bound (and
        # REG-3050's failed list) is `.sh-empty-hero.sh-unknown`: "your runs: UNKNOWN ... This is not an empty shelf".
        # The beat counted it as the empty hero, so this row answered "no runs to show yet - the correct state" over it.
        # The page now publishes `unknown` with its own why; his runs are not on the shelf, which is the fault.
        if shelf.get("unknown") is True:
            _uw = shelf.get("unknownWhy")
            return MISSING, ("THE SHELF IS OPEN AND SAYS HIS RUNS ARE UNKNOWN - the sessions list did not reach it "
                             "(the page's why: %s). The page says so honestly, and his runs are still not on the "
                             "shelf." % (_uw if isinstance(_uw, str) and _uw else "none given"))
        if shelf.get("opening") is True:
            _os = shelf.get("openingS")
            if not isinstance(_os, (int, float)):
                return UNKNOWN, ("the shelf is open and still says it is opening, and how long it has said so "
                                 "is UNKNOWN (no start stamp on the beat)")
            # [[stale-reading]] openingS is the age AT THE BEAT, and the beat itself may be up to 300 s old: past the
            # bound by the beat's own words is MISSING; past it only once the beat's age is added is UNKNOWN (no newer
            # beat says whether it still says "opening"); inside it either way is OK.
            if _os > SHELF_OPENING_BOUND_S:
                return MISSING, ("THE SHELF HAS SAID 'opening' FOR %ds (on a beat %ds old) - past the %ds bound in "
                                 "which it must show his runs or say why. The list never arrived, and the page's "
                                 "own bound did not end it." % (int(_os), int(_bage), SHELF_OPENING_BOUND_S))
            if _os + _bage > SHELF_OPENING_BOUND_S:
                return UNKNOWN, ("the shelf said 'opening' for %ds on a beat that is %ds old - %ds by now if it still "
                                 "says so, past the %ds bound, and no newer beat says whether it does"
                                 % (int(_os), int(_bage), int(_os + _bage), SHELF_OPENING_BOUND_S))
            return OK, ("the shelf is open and still opening (%ds so far, counting the beat's own %ds age; bound "
                        "%ds) - waiting on the sessions list, not a fault yet"
                        % (int(_os + _bage), int(_bage), SHELF_OPENING_BOUND_S))
        if shelf.get("emptyHero") is True:
            return OK, ("the shelf is open and on screen and has no runs to show yet — the empty "
                        "hero is rendered, which is the correct state, not a fault")
        _empty = (isinstance(_vis, int) and _vis == 0) or (cards == 0 and grid == 0)
        if _empty:
            return MISSING, ("THE SHELF IS OPEN AND ON SCREEN AND SHOWS NO REEL — %sx%s at top %s; "
                             "%s card(s) built, %s visible. The box is real and the empty-hero is "
                             "NOT rendered, so this is neither a layout fault nor an honest empty "
                             "shelf: something was built and none of it is on screen."
                             % (shelf.get("w"), shelf.get("h"), shelf.get("top"),
                                "UNKNOWN" if grid is None else grid,
                                "UNKNOWN" if _vis is None else _vis))
        # ⚠⚠ v2999 — A REAL BOX WITH EVERY CARD BELOW ITS OWN FOLD IS THE FAULT HE PHOTOGRAPHED.
        # v2996 proved the overlay is `shown`; his eyes still read an empty dark stage, and the two
        # were both honest because nothing asked where the first CARD sits inside the scroller.
        # firstCardTop >= clientH at rest means he opens THE SHELF and sees no reel at all.
        _ft, _ch = shelf.get("firstCardTop"), shelf.get("clientH")
        if (isinstance(_ft, (int, float)) and isinstance(_ch, (int, float)) and _ch > 0
                and not shelf.get("scrollTop") and _ft >= _ch):
            return MISSING, ("THE SHELF OPENS ON NOTHING — the box is real (%sx%s) and %s card(s) "
                             "are built, but the first one starts %dpx down a %dpx window, so at "
                             "rest he sees only furniture. %spx of content sits below the fold. "
                             "This is a LAYOUT fault, not a paint failure — the cards are there."
                             % (shelf.get("w"), shelf.get("h"),
                                "UNKNOWN" if cards is None else cards, _ft, _ch,
                                _said(shelf.get("belowFoldPx"))))
        return OK, ("the shelf is open and on screen (%sx%s at top %s, viewport %s) — %s card(s) "
                    "by the panel count, %s by the grid count, first card %spx into a %spx window"
                    % (shelf.get("w"), shelf.get("h"), shelf.get("top"), shelf.get("vh"),
                       "UNKNOWN" if cards is None else cards,
                       "UNKNOWN" if grid is None else grid,
                       "UNKNOWN" if _ft is None else _ft,
                       "UNKNOWN" if _ch is None else _ch))
    _n = ("an UNKNOWN number of" if cards is None else ("%d" % cards))
    _why = ("OFF-VIEW means an ancestor is display:none — the overlay generates no layout boxes "
            "at all, which is why nothing paints while the DOM is perfectly built"
            if state == "OFF-VIEW" else
            "it is laid out, but not where a reader can reach it")
    return MISSING, ("THE SHELF IS OPEN AND NOT ON SCREEN — %s, holding %s card(s) (%s by the "
                     "grid count). h=%s top=%s viewport=%s boxes=%s. %s. ⚠ This is the pair his "
                     "eyes and this beat were disagreeing about."
                     % (state, _n, "UNKNOWN" if grid is None else grid, shelf.get("h"),
                        shelf.get("top"), shelf.get("vh"), shelf.get("boxes"), _why))


def _said(n):
    """-> the number, or the word UNKNOWN. Never `or 0`.

    ⚠ `x or 0` prints "0 of 0 series frozen" and "0px sits below the fold" when the producer
    deliberately published null, turning a refusal to measure into an affirmative measurement —
    inside the very sentence declaring a fault. 0 is measured-and-zero; None is nobody looked.
    [[unknown-stays-unknown]] [[zero-needs-a-denominator]]
    """
    return "UNKNOWN" if n is None else n


def _check_the_screen_is_still_painting():
    """THE ONE CHECK THAT DOES NOT ASK THE PAGE. (#34)

    Measured on his machine 2026-09-10 from Grok Bot's captures: the TV DIABLO window was a DARK
    BLANK at 19:08 and a WHITE BLANK at 16:16 — titlebar and nothing else — while every text-based
    check reported health (`GET / 200 in 16ms - 1,744,954 bytes`, `GET /api/status 200 in 68ms`,
    "quiet hold - HEART census held - did not kill"). A page that answers 200 can paint nothing, so
    every other check in this file is blind to a dead compositor by construction. This one reads
    the BYTES of screencaptures of the real window.

    ⚠ FRESHNESS IS PART OF THE ANSWER, NOT A FOOTNOTE. A frozen pair from four hours ago is a true
    statement about four hours ago and says NOTHING about the screen now. Grok Bot captures on a
    ~10 minute loop, so once the newest frame is over an hour old nobody is watching and the honest
    verdict about NOW is UNKNOWN — with the stale finding still reported, because it is evidence.
    [[stale-reading]] [[unknown-stays-unknown]]

    ⚠ FROZEN is not BLANK. This says two captures are identical; whether the screen is empty is a
    claim about content that needs an eye on the frame.
    """
    try:
        import frozen_frame_watch as FFW
    except Exception as e:
        return UNKNOWN, ("the frozen-frame watch could not be imported (%s), so the pixels went "
                         "unread" % type(e).__name__)
    try:
        r = FFW.report()
    except Exception as e:
        return UNKNOWN, "the frozen-frame watch raised %s, so nothing was measured" % type(e).__name__

    c = r.get("counts") or {}
    if r.get("state") == FFW.UNKNOWN:
        return UNKNOWN, ("no capture of his window could be compared here (%d png(s), %d window "
                         "series). That is not a clean bill — it is nobody looking."
                         % (c.get("pngs") or 0, c.get("standing") or 0))

    STALE_S = 3600.0
    _series = [x for x in (r.get("series") or []) if isinstance(x.get("ageS"), (int, float))]
    frozen = [x for x in _series if x.get("state") == FFW.FROZEN]

    # ⚠⚠ v2998 GRADED FRESHNESS BY min(ageS) ACROSS *ALL* SERIES, so a five-hour-old freeze read as
    # a live fault whenever any other geometry had a recent capture. v3001 fixed that by taking
    # `frozen[0]` — and frozen[0] is the series with the MOST FRAMES, because report() sorts by
    # -len(rows) and never by age. Reproduced 2026-09-12: a 95-frame freeze 5h old beside a
    # 12-frame freeze 60 SECONDS old returned UNKNOWN, and the live fault this row exists for was
    # never reported. Twice now the freshness question has been answered by whichever series
    # happened to sort first. The evidence for a FAULT is the FRESHEST fault.
    # [[stale-reading]] [[feedback-suspect-the-instrument]]
    if frozen:
        f = min(frozen, key=lambda x: x.get("ageS"))
        age = f.get("ageS")
        if age > STALE_S:
            return UNKNOWN, ("the freshest frozen window series (%s) was last captured %.1fh ago, "
                             "so nothing is known about the screen NOW. %d series were frozen when "
                             "anyone last looked. Grok Bot captures on a ~10 minute loop; this old "
                             "means it is not watching."
                             % (f.get("geom"), age / 3600.0, len(frozen)))
        return MISSING, ("HIS SCREEN STOPPED PAINTING — %s is byte-identical across %.0fs (%s, "
                         "captured %.0fs ago); %d of %s comparable window series frozen. A live "
                         "console never captures twice to the same bytes. ⚠ FROZEN is measured; "
                         "BLANK is not — go look at the frame."
                         % (f.get("geom"), f.get("gapS") or 0, f.get("sha"), age, len(frozen),
                            _said(c.get("standing"))))

    # ⚠⚠ AND THE HEALTHY PATH HAD THE MIRROR OF THE SAME BUG. An OK here is a claim about EVERY
    # series, so it cannot rest on the freshest one: his console has 8 geometries, and with one
    # captured 2 minutes ago and another untouched for 5 hours, min(ageS) said 120 and the row
    # returned "8 window series compared, all painting" — a clean bill for a window nobody had
    # looked at since morning. A verdict is only as fresh as the OLDEST evidence it covers, so the
    # stale ones are excluded from the claim and COUNTED rather than quietly included.
    fresh = [x for x in _series if x.get("ageS") <= STALE_S]
    stale = [x for x in _series if x.get("ageS") > STALE_S]
    if not fresh:
        return UNKNOWN, ("every comparable window series was last captured over %.0fh ago (%d of "
                         "them), so nothing is known about the screen now"
                         % (STALE_S / 3600.0, len(stale)))
    return OK, ("%d window series compared from %s capture(s), all painting%s"
                % (len(fresh), _said(c.get("pngs")),
                   "" if not stale else
                   " — %d further series excluded, last captured over %.0fh ago and too old to "
                   "speak for now" % (len(stale), STALE_S / 3600.0)))


def _check_the_shelf_keeps_his_order_and_its_guard():
    """His shelf order, and the scroll guard that pays for it — both, or neither is safe.

    ⚠⚠ v3359 — THIS ROW SHIPPED IN v3358 ASSERTING THE OPPOSITE AND IT WAS WRONG. It reported
    MISSING whenever any analytic block led the reel cards, which is exactly the layout he asked
    for twice: *"the row where it says BEST RUN MOST READS TOP READS BEST COVERAGE AND STREAK i
    want at the tippy top of the SHELF TAB above the sessions reels"*, then *"and the activity i
    want uptop under the BEST RUNS row"*. v3289 granted it and paid for it with
    `window._shOpenOnAReel`, a scroll guard re-run AFTER `_shTimeline()` so the shelf still opens
    ON A REEL — measured then at firstCardTop 235, visible, against 815 and invisible without it.

    I probed his console, saw the guard working at scrollTop 497, RESET the scroll to 0, measured
    708 in a 660 viewport and called it the defect. The measurement was mine, not his console's.
    [[stale-reading]] [[feedback-suspect-the-instrument]]

    So the row now watches what actually protects him: HIS order, and the guard that makes it
    safe. Losing either is the regression — the order drifting back is one, and the guard going
    missing while the order stays is the one that puts furniture on screen and no reels.
    """
    try:
        import io as _io
        ui = _io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()
    except Exception as e:
        return UNKNOWN, "control_ui.html could not be read (%s)" % str(e)[:80]
    i = ui.find("ov.innerHTML = '<button class=\"sh-x th-x\" id=\"th-shelf-x\"")
    if i < 0:
        return UNKNOWN, "the shelf overlay assembly could not be found, so its order is UNKNOWN"
    seg = ui[i:i + 40000]
    hi, tl, lst = seg.find("_shHighlights()"), seg.find("+ timelineDiv"), seg.find("+ searchBar + body")
    if min(hi, tl, lst) < 0:
        return UNKNOWN, "one of the three shelf blocks is not in the assembly window"
    drift = []
    if not hi < lst:
        drift.append("the BEST RUN / STREAK strip no longer leads the list")
    if not tl < lst:
        drift.append("ACTIVITY no longer leads the list")
    if not hi < tl:
        drift.append("ACTIVITY is above the BEST RUNS row, not under it")
    guard = "window._shOpenOnAReel = function (ov)" in ui
    _t = ui.find("_shTimeline();")
    after = ui.find("window._shOpenOnAReel(ov)", _t) if _t > -1 else -1
    if drift:
        return MISSING, ("the shelf order drifted from what he asked for twice: %s"
                         % "; ".join(drift))
    if not guard or after < 0:
        return MISSING, ("his order is intact but the opening-scroll guard is %s — the strip and "
                         "the chart sit above the list, so without it the shelf opens on "
                         "furniture and shows him no reels"
                         % ("gone" if not guard else "no longer re-run after _shTimeline()"))
    return OK, "the strip and the chart lead the list, as he asked, and the opening-scroll guard still re-runs after the chart fills"

def _check_a_failed_read_is_never_handed_back_as_data():
    """The swallow ratchet's RANK 1 — a failed read served to a caller as 0 / {} / [] / ''.

    ⚠⚠ v3355 — THIS RATCHET WAS RED IN CI FOR TEN CONSECUTIVE RUNS AND NOTHING SAID SO. Routine M
    runs `tv/swallow_census.py --check` and reported 76 against a baseline of 74 on every push from
    at least v3344 to v3353. The pre-push hook derives its gates from CHANGED TEST FILES and never
    runs the full set, so the only reader was a CI page nobody opened. A red nobody reads is the
    same as a green. [[regression-guard]] §2 [[the-unjoined-end]]

    WHAT THE TWO EXTRA SITES WERE, when they were finally read: three loaders written by v3325 to
    refuse an unread store, each saying `except IOError: return {}`. `IOError is OSError` in
    Python 3, so an EXISTING store that merely could not be READ took the ABSENT arm — and every
    one of those loaders feeds a caller that writes the whole dict back. Measured on a real file
    holding watermarks 179, 180 and 230 at mode 000: `--mark` would have written `{"999": 1}`
    over all three.

    ⚠ IT REPORTS THE BASELINE BESIDE THE COUNT, ALWAYS. "76 sites" alone is not a verdict about
    anything; 76 against 74 is. [[zero-needs-a-denominator]]
    """
    try:
        import swallow_census as _sc
    except Exception as e:
        return UNKNOWN, "the swallow census will not import: %s" % str(e)[:90]
    try:
        # ⚠ LOCAL IMPORTS. This module does not import `io` or `json` at the top, and the first
        # cut of this row used a bare `io.open`. The UNKNOWN arm below caught it and NAMED the
        # NameError rather than swallowing it — which is the only reason it took one run instead
        # of forever. The same slip in this same file once made a guard answer "no browser suite
        # here" for every input, because a bare `except Exception: continue` ate it. [[test-venue]]
        import io as _io
        import json as _json
        _bp = _sc._baseline_path()
        _base = _json.load(_io.open(_bp, encoding="utf-8"))
    except Exception as e:
        # ⚠ A count with no baseline is not a verdict, so this is UNKNOWN rather than a number.
        return UNKNOWN, ("the ratchet baseline could not be read (%s), so a site count has "
                         "nothing to be measured against" % str(e)[:90])
    try:
        _by = _sc._rank1_by_file(_sc.scan())
    except Exception as e:
        return UNKNOWN, "the census raised: %s" % str(e)[:110]
    _now = sum(_by.values())
    # ⚠ THE BASELINE IS NESTED, and reading it flat is how a count becomes a type error. The file
    # carries `_why`, `counts` and `rank1ByFile`; the ratchet's number is counts.rank1 and the
    # per-file breakdown is rank1ByFile. Summing the top level once produced
    # `int() argument must be ... not 'dict'`, caught on the first run of this row.
    _was_by = dict(_base.get("rank1ByFile") or {})
    _was = int((_base.get("counts") or {}).get("rank1") or 0)
    if not _was:
        return UNKNOWN, ("the baseline records no rank-1 total, so %d site(s) here has nothing to "
                         "be measured against" % _now)
    if _now > _was:
        _rose = sorted(((f, n, int(_was_by.get(f, 0))) for f, n in _by.items()
                        if n > int(_was_by.get(f, 0))), key=lambda t: t[2] - t[1])
        _where = ", ".join("%s %d->%d" % (f, w, n) for f, n, w in _rose[:3])
        return MISSING, ("%d site(s) hand a failed read back as DATA, against a baseline of %d — "
                         "a caller cannot tell that from a real measurement (%s)"
                         % (_now, _was, _where or "no single file rose"))
    if _now < _was:
        return MISSING, ("down to %d from a baseline of %d — good, and the baseline must move with "
                         "it (python3 tv/swallow_census.py --write-baseline) or the gap becomes "
                         "slack a future regression can hide inside" % (_now, _was))
    return OK, "no failed read is handed back as data beyond the %d known site(s)" % _was


def _check_the_second_eye_was_asked_twice():
    """v3310 (#56) — was the last shipped version looked at TWICE, and did the looks AGREE?

    His #56 ruling: *ask the second eye TWICE and keep both; wire the disagreement to the heart.*

    ⚠⚠ THIS CHECK EXISTS BECAUSE I WAS NOT DOING IT AND REPORTED THAT I WAS. Through the whole
    v3301-v3309 arc I wrote "asked twice, both looks agree" — while pasting the second look INTO
    the first answer's text. `record_answer` then wrote ONE row carrying both, so the ledger has
    no pairs, nothing can compute agreement, and no disagreement could ever reach the heart. A
    second opinion that lives inside the first opinion's prose is not data. This is heart-first
    rule 6 committed inside the mechanism built to catch it. [[the-unjoined-end]]

    FOUR STATES, and collapsing any two is the defect this file is full of:
      AGREE    -> two reached looks, same verdict, and at least two DIFFERENT families named. Two
                  witnesses, and the eye is steady on this payload.
                  ⚠ v3466 — an AGREE in which ANY look names a family nobody could attribute reads
                  MISSING here, not OK. This line used to admit that case "stated rather than
                  assumed" — and OK is the one state the panel does not draw, so the statement
                  reached no screen. MEASURED 2026-09-24: all 7 AGREE versions of 904 on his ledger
                  were exactly that shape (one xai look + one unattributed), so this row had never
                  once shown OK for two IDENTIFIABLE families. Found by the eye on v3439.
      DISAGREE -> two reached looks, different verdicts. ⚠ THE FINDING IS ABOUT THE INSTRUMENT:
                  which verdict shipped was decided by timing, not by the code.
      SINGLE   -> asked once. Not a failure of the code and NOT his to act on — it is mine, so
                  this check is named in MINE and does not bill him. [[his #35 ruling]]
      ECHO     -> v3439 (#182). Asked twice, both looks agree, and every one of them MEASURED to
                  be the SAME family. One witness asked twice. That is SINGLE wearing a second
                  coat, and it reaches him as the SAME state for the same reason: the
                  corroborating look was never taken, and taking it is MINE.

    ⚠⚠ ECHO IS `MISSING`, AND IT IS NOT A FIFTH WORD. BOTH HALVES WERE MEASURED, NOT ARGUED.

    1. A FIFTH WORD IS INVISIBLE TO THE EAGLE — MEASURED 2026-09-23 by DRIVING
       `control_app.eagle_partition()` and the `unk` line of `_eagle_once` with a row named
       "second eye asked twice", one state per run:

           state        bad  mine  byDesign  unk   the eagle's own sentence
           ok            0    0      0        0    "all clear across N check(s)"
           missing       0    1      0        0    "all clear across N check(s)"   (MINE, see 2)
           unknown       0    0      0        1    "1 check(s) could not be measured"
           unmeasured    0    0      0        1    "1 check(s) could not be measured"
           echo          0    0      0        0    "all clear across N check(s)"   ⚠⚠
           any new word  0    0      0        0    "all clear across N check(s)"   ⚠⚠

       The eagle buckets on exactly four literal strings. A word it has never heard is counted by
       NOTHING and folds straight into ALL CLEAR — while `control_ui.html._vxHealthRow` still
       DRAWS the row (it hides only `state === 'ok'`), under the fallback word 'UNKNOWN', and
       `_sortRow` files it in `youRows` = WAITING ON YOU, because `mineWhat` only ever carries
       rows whose state is `missing`. So a new word would be simultaneously uncounted and shown
       as HIS — which is the v3309 counter-vs-panel divergence rebuilt by hand. Same shape as the
       UNMEASURED row that tripped `test_UNKNOWN_is_never_folded_into_all_clear` and stopped the
       live site deploying for a whole day while the code was right throughout.
       [[unknown-stays-unknown]] [[zero-needs-a-denominator]]

    2. "EIGHT HISTORICAL VERSIONS TURN RED" IS TRUE AND IS NOT WOLF-CRYING HERE — MEASURED over
       all 877 versions on his 942-row ledger, 2026-09-23:

           SINGLE 842 · DISAGREE 14 · ECHO 8 · AGREE 7 · NONE 6
           this row today (ECHO -> UNKNOWN):   ok 7 · missing 856 (97.6%) · unknown 14
           this row after (ECHO -> MISSING):   ok 7 · missing 864 (98.5%) · unknown  6

       +8 rows, +0.9 of a percentage point, on a row that is ALREADY red on 97.6% of versions —
       and the eight land beside the 842 SINGLEs they are a variant of. ⚠ AND IT NEVER REACHES
       THE COUNT HE ACTS ON: this check is in MINE, so `bad` stays 0, `needsYou` does not move
       and the eagle sentence is unchanged (table above). The MINE entry for this exact row
       already rules it: *"It still renders red, because the omission is real."* A row he is
       never billed for cannot be silenced by him.

    3. WHY NOT THE OTHER THREE. `ok` is refused because `_vxHealthRow` returns '' for it — the
       row would not be drawn at all, so the ledger's sentence would reach no screen, and the
       check would be asserting the corroboration #182 measured was never earned. `unknown`
       (CAN'T ASK) and `unmeasured` (NEVER / NOT THIS TICK) are refused because both are FALSE:
       the eye WAS asked, twice, both looks reached, both carried a verdict, and the family was
       re-derived from the model id. ECHO is a measurement. UNKNOWN means nobody could look, and
       collapsing those two is the lie this file exists to refuse.
    """
    try:
        import second_eye_ledger as L
    except Exception as e:
        return UNKNOWN, "the second-eye ledger will not import: %s" % str(e)[:90]
    try:
        v = L.current_version()
    except Exception as e:
        return UNKNOWN, "could not read the current version: %s" % str(e)[:90]
    if not v:
        return UNKNOWN, "no current version could be read, so there is nothing to ask about"
    try:
        a = L.agreement(v)
        c = L.agreement_census()
    except Exception as e:
        return UNKNOWN, "the agreement reader raised: %s" % str(e)[:110]
    # ⚠ THE DENOMINATOR TRAVELS WITH THE VERDICT, always. [[zero-needs-a-denominator]]
    tail = " · " + c.get("say", "")
    st = a.get("state")
    if st == "DISAGREE":
        return MISSING, a.get("say", "two looks disagree") + tail
    if st == "AGREE":
        # v3466 — AN UNATTRIBUTED FAMILY HAS NOT EARNED CORROBORATION. Same reasoning as ECHO
        # below: the looks agree, but whether they are two WITNESSES is not established, and the
        # corroborating look from an identifiable different family is MINE to take.
        if (a.get("familyUnknown") or 0) > 0:
            return MISSING, ((a.get("say") or "the looks agree")
                             + " — but %d look(s) name no model family anyone could attribute, so "
                               "whether these are two WITNESSES is not established; one more look "
                               "from an IDENTIFIABLE different family is MINE to take"
                             % int(a.get("familyUnknown") or 0)) + tail
        return OK, a.get("say", "the looks agree") + tail
    if st == "SINGLE":
        return MISSING, a.get("say", "looked at once") + tail
    # ⚠⚠ v3439 (#182) — AN ECHO IS A MEASURED FACT, SO IT MUST NOT LEAVE HERE AS UNKNOWN.
    # Before this branch existed ECHO fell through to the line below and reached his screen as
    # CAN'T ASK, carrying the ledger's own (correct) sentence underneath a word that contradicts
    # it. Not a false OK and not a false red — WRONG IN KIND, which is the collapse this file
    # spends forty other checks refusing. The state and the two measurements behind it are in the
    # docstring above; this branch only has to keep the SAY naming what the state does not.
    # ⚠⚠ #168 (v3459) — INCOMPARABLE IS `MISSING`, FOR ECHO'S REASON EXACTLY.
    # Two looks whose payloads differ 2x+ answered different questions, so the corroborating look
    # at COMPARABLE reach was never taken — and taking it is MINE, like SINGLE and ECHO. It must
    # NOT fall through to UNKNOWN: UNKNOWN means nobody could ask, and this is a MEASUREMENT (the
    # ratio is on the row). MEASURED when this shipped: SEVEN versions moved out of DISAGREE into
    # it, so seven "the eye is not steady" verdicts were payload differences wearing the
    # instrument's name. [[unknown-stays-unknown]] [[label-outlived-referent]]
    if st == "INCOMPARABLE":
        return MISSING, ((a.get("say") or "two looks over payloads too different to compare")
                         + " · the half that is missing is MINE to take: one more look at "
                           "COMPARABLE reach, recorded as its own ledger row") + tail
    if st == "ECHO":
        return MISSING, ((a.get("say") or
                          ("two or more looks at this version agree and every one of them is the "
                           "SAME family — one witness asked twice, which is measured, and is not "
                           "corroboration"))
                         # ⚠ A REFUSAL THAT NAMES NO ACTION IS FURNITURE. The row is in MINE, so
                         # the sentence has to say whose move it is and what the move IS, or it
                         # reads as a complaint nobody can close.
                         + " · the half that is missing is MINE to take: one more look from a "
                           "DIFFERENT model family, recorded as its own ledger row"
                         + tail)
    return UNKNOWN, (a.get("say") or "nothing recorded") + tail


#: v3365 (#24) — the instant the console gained the ability to send a pre-rescue snapshot.
#: A fault row older than this CANNOT carry one, so counting it would make the heart row
#: red on the day it was born. Historical boundary, not a threshold: it never moves.
EVIDENCE_SINCE_MS = 1789833019729


def _check_the_item_facts_are_reaching_the_row():
    """v3368 (#60) — ARE SOCKETS / ETHEREAL / QUALITY ACTUALLY LANDING ON NEW SIGHTINGS?

    A base item's value is decided by those three facts, not by its name. Until v3368 the reader
    was TOLD to look at sockets, used them to form a junk opinion, and discarded the fact: 44 rows
    on his disk, ZERO carrying any of the three.

    ⚠⚠ THE FAILURE MODE IS SILENT AND LOOKS EXACTLY LIKE THE PAST. If the model stops honouring the
    template keys, or a parse regression drops them, new rows simply arrive with all three null —
    byte-identical to every row written before the field existed. Nothing errors. The sweep keeps
    sweeping. It just stops recording the only facts that let a price be applied.
    [[heart-first]] §2 — ON is not WORKING.

    THREE STATES:
      OK       -> sightings read by this prompt DO carry at least one of the three; says how many
      MISSING  -> sightings were read by THIS prompt and NOT ONE carries any — the keys stopped
                  coming back, and a null from the new prompt is indistinguishable from an old row
      UNKNOWN  -> no sighting has been read by this prompt yet. ⚠ NEVER OK: that is an absent
                  denominator, not a clean bill. [[zero-needs-a-denominator]]
    """
    import json as _json
    import os as _os
    try:
        import tv_diablo as _td
        ver = str(getattr(_td, "VAULT_PROMPT_VER", "") or "")
    except Exception as e:
        return UNKNOWN, "tv_diablo will not import, so the prompt version is unknown: %s" % str(e)[:70]
    if not ver:
        return UNKNOWN, "the vault prompt declares no version, so no row can be attributed to it"
    p = _os.path.join(HERE, "vault_seen.json")
    if not _os.path.isfile(p):
        return UNKNOWN, "no sighting store on this machine, so nothing can be counted"
    try:
        with open(p, "rb") as _fh:
            rows = (_json.loads(_fh.read().decode("utf-8", "replace")) or {}).get("rows") or []
    except Exception as e:
        return UNKNOWN, "the sighting store will not read: %s" % str(e)[:90]
    # ⚠ ONLY ROWS THIS PROMPT PRODUCED. Rows from vp2017 and earlier were read by a prompt that
    # never asked, so counting them would make this row red on the day it was born — the mistake
    # the `fault evidence` row made and had to be given a boundary for.
    # ⚠⚠ v3369 — ASK WHERE THE FACTS ACTUALLY LIVE. This check was written at v3368 against a shape
    # that did not exist yet: it read promptVer and the three facts OFF THE ROW. v3369 built the
    # projections and deliberately put them on the WITNESS — promptVer because different sightings
    # of one name can come from different prompts, and the facts because one (name, lane) key holds
    # SEVERAL PHYSICAL ITEMS and a single row-level `sockets` would silently pick a winner.
    #
    # Left as it was, `mine` would be empty forever and this row would read UNKNOWN for good: a
    # supervisor pointed at an address the data never moves to. That is the same defect the row
    # exists to catch, wearing the supervisor's own clothes. [[the-unjoined-end]]
    def _wits(r):
        return [w for w in (r.get("witnesses") or []) if isinstance(w, dict)]

    # v3554 — the versions that ask the same question count as this prompt's (VAULT_PROMPT_ANSWERS_SAME_AS)
    _vers = (ver,) + tuple(str(v) for v in (getattr(_td, "VAULT_PROMPT_ANSWERS_SAME_AS", ()) or ()))
    # REG-1713 (the v3554 eye) - THE CURRENT READER IS MEASURED ON ITS OWN WITNESSES. Pooling vp3368's (the same
    # question) with vp3554's let one old witness with sockets keep this row OK after a vp3554 read had dropped all
    # three facts, and the sentence called the pool "read by vp3554". The same-question readers stand in only while
    # the current one has read nothing - and the sentence names which population it measured.
    # REG-1718 - a fact a later reader filled into an earlier look is that later reader's (`filledBy`)
    def _readers(w):
        # REG-1722 (the #231 code seat on 1bb86d6c) - a later reader joins a look's population only for a FACT it
        # supplied: one that only filled the cell would put a look in its population whose sockets/eth/quality are the
        # first reader's, and call it MISSING facts it never dropped
        fb = w.get("filledBy") or {}
        return {str(w.get("promptVer") or "")} | {str(fb[f]) for f in ("sockets", "eth", "quality") if fb.get(f)}

    def _fact_by(w, vs):
        fb = w.get("filledBy") or {}
        return any(w.get(f) is not None and str(fb.get(f) or w.get("promptVer") or "") in vs
                   for f in ("sockets", "eth", "quality"))

    def _by(vs):
        return [r for r in rows if isinstance(r, dict)
                and any(_readers(w) & set(vs) for w in _wits(r))]
    mine, said = _by((ver,)), ver
    if not mine and len(_vers) > 1:
        mine = _by(_vers[1:])
        said = "%s (asks the same question; %s has read nothing yet)" % ("/".join(_vers[1:]), ver)
    if not mine:
        return UNKNOWN, ("no sighting has been read by prompt %s yet, so whether the three facts "
                         "travel is UNMEASURED - not clean, and not a defect either" % ver)
    _vs_said = (ver,) if said == ver else _vers[1:]
    # a row "has" the facts when a sighting carried one AND the row reflects it as a variant, which
    # is the whole six-link chain end to end rather than either half of it
    have = [r for r in mine
            if (r.get("variants") or [])
            or any(_fact_by(w, _vs_said) for w in _wits(r))]
    if not have:
        return MISSING, ("%d sighting(s) read by %s and NOT ONE carries sockets, eth or quality. "
                         "The template keys have stopped coming back, and a null from this prompt "
                         "looks exactly like a row from before the fields existed"
                         % (len(mine), said))
    return OK, ("%d of %d sighting(s) read by %s carry at least one of sockets/eth/quality"
                % (len(have), len(mine), said))


def _check_the_capture_root_is_still_being_written():
    """v3366 (#115) — IS THE FOLDER THE SCREEN-WATCHER READS STILL RECEIVING CAPTURES?

    This row is the supervision that was missing for 7.5 days. The seat moved where it writes; the
    frozen-screen detector kept reading the folder it left behind; and because a folder nobody
    writes to has a newest-two that are BYTE-IDENTICAL by construction, it reported FROZEN the
    whole time — a confident claim about a screen it was not looking at.

    MEASURED 2026-09-19, same code, two roots: the abandoned one said FROZEN (425 PNGs, newest
    178.9 h old); the live one said MOVING (2,692 PNGs, newest 0.4 h old).

    ⚠⚠ NOTHING WAS BROKEN. No exception, no empty result, no missing file. The detector ran every
    time it was asked and answered fluently about the wrong folder. That is the failure this row
    exists for, and it is why the question here is about the RECORDER, never about his screen:
    a detector reading a dead folder is not a detector. [[stale-reading]] [[heart-first]] §2

    THREE STATES:
      OK       -> captures are arriving; says how old the newest one is
      MISSING  -> the root has gone quiet past the measured bound — the RECORDER stopped, and any
                  FROZEN verdict drawn from it is about then, not now
      UNKNOWN  -> no root exists here, or it holds no captures at all. ⚠ NEVER OK: a machine with
                  no capture folder cannot report on his screen. [[zero-needs-a-denominator]]
    """
    try:
        import frozen_frame_watch as W
    except Exception as e:
        return UNKNOWN, "the frozen-frame watcher will not import: %s" % str(e)[:90]
    try:
        root = W.shelf_dir()
        age = W.newest_capture_age_s(root)
    except Exception as e:
        return UNKNOWN, "the capture root could not be resolved: %s" % str(e)[:110]
    short = os.path.basename(root.rstrip("/")) or root
    if not os.path.isdir(root):
        return UNKNOWN, ("no capture folder on this machine (%s), so nothing here can say whether "
                         "his screen is painting - that is not a clean bill" % short)
    if age is None:
        return UNKNOWN, ("the capture folder %s holds no captures at all, so its liveness is "
                         "UNMEASURED - not clean" % short)
    if age > W.STALE_ROOT_S:
        return MISSING, ("the capture folder %s has received nothing for %.1f h (bound %.1f h). "
                         "Any frozen-screen verdict from it describes THEN, not now - and a folder "
                         "nobody writes to always looks frozen"
                         % (short, age / 3600.0, W.STALE_ROOT_S / 3600.0))
    return OK, ("captures are arriving in %s - newest is %.1f min old (bound %.1f h)"
                % (short, age / 60.0, W.STALE_ROOT_S / 3600.0))


def _check_a_ui_fault_keeps_its_evidence():
    """v3365 (#24) — ARE NEW UI FAULTS STILL ARRIVING WITH A PRE-RESCUE SNAPSHOT?

    A console fault row that records only THAT nothing painted, never WHAT was there, cannot tell a
    stage that never painted from one that painted off-screen — and that is the single question #24
    turned on for 27 events. MEASURED when this shipped: 200 rows, 8 carrying evidence (4%).

    ⚠⚠ THE FAILURE MODE IS SILENT AND LOOKS EXACTLY LIKE HEALTH. If the JS stops measuring, or the
    route goes back to dropping `before`, new rows simply arrive without it — byte-identical to the
    192 historical rows that never had one. Nothing errors. The lane keeps recording. It just stops
    recording the only field that made the rows usable. That is the vault-lane shape: on for months,
    reads 0, and truthfully reported. [[heart-first]] §2

    THREE STATES:
      OK       -> faults recorded since this version DO carry evidence; says how many
      MISSING  -> faults arrived since this version and NOT ONE carries it — a writer stopped
      UNKNOWN  -> no fault has been recorded since this version, or the ledger cannot be read.
                  ⚠ NEVER OK: no rows is an absent denominator, not a clean bill of health.
                  [[zero-needs-a-denominator]]
    """
    try:
        import control_app as CA
    except Exception as e:
        return UNKNOWN, "control_app will not import: %s" % str(e)[:90]
    # ⚠ IT RETURNS (rows, why), NOT rows. Its own docstring states the contract this file is full
    # of — "UNKNOWN is None, never an empty list" — and my first cut treated the TUPLE as the list
    # and died on `'list' object has no attribute 'get'`. It surfaced only because the unpacking
    # sat outside the try; swallowed, this row would have answered about nothing forever.
    try:
        rows, why = CA.ui_faults_recent(hours=24 * 14)
    except Exception as e:
        return UNKNOWN, "the fault ledger will not read: %s" % str(e)[:110]
    if rows is None:
        return UNKNOWN, ("the fault ledger could not be read (%s), so evidence cannot be counted"
                         % (why or "no reason given"))
    # Only the console-reported kinds can carry a snapshot; a server-side row has no DOM to measure.
    # ⚠⚠ AND ONLY ROWS WRITTEN AFTER THE FIX SHIPPED. Without this boundary the row read MISSING
    # the moment it was born — 35 console faults in 14 days, none carrying evidence, every one of
    # them recorded by code that could not yet send any. That is a TRUE sentence about the WRONG
    # POPULATION, and a row that is red on arrival is furniture: it would be ignored long before
    # it had anything real to say. Rows before the boundary are EXPECTED to lack evidence.
    # The constant is a HISTORICAL boundary — the instant the writer gained the ability — so
    # unlike a freshness threshold it legitimately never moves. [[zero-needs-a-denominator]]
    mine = [r for r in rows
            if str((r or {}).get("where") or "").startswith("control_ui")
            and ((r or {}).get("at") or 0) >= EVIDENCE_SINCE_MS]
    if not mine:
        return UNKNOWN, ("no console-reported fault since the snapshot shipped, so whether it "
                         "travels is UNMEASURED - not clean, and not a defect either")
    have = [r for r in mine if isinstance((r or {}).get("before"), dict)]
    if not have:
        return MISSING, ("%d console-reported fault(s) in 14 days and NOT ONE carries a pre-rescue "
                         "snapshot. The measurement or the route has stopped, and a stopped one is "
                         "byte-identical to the 192 rows that never had one" % len(mine))
    return OK, ("%d of %d console-reported fault(s) carry a pre-rescue snapshot (was 8 of 200 "
                "across all kinds when this shipped)" % (len(have), len(mine)))


def _check_the_save_reader_matches_the_install():
    """#174 — CAN A CHARACTER SAVE STILL BE READ, AND ARE ITS TABLES STILL THE INSTALL'S?

    tv/d2s_read.py reads a D2R .d2s (format 105) byte-exact against tv/item_tables.json - stat bit widths, item
    codes, unique/set/runeword names - generated ONCE from his 28 GB install. A game patch that moves a stat's
    Save Bits makes every later import decode WRONG (the property lists shift) while every row still looks like
    an item. So the tables' sourceHash is re-derived here and compared, exactly as `item vocabulary` does for the
    affix lexicon. The reader was built without this row; the heart-first rule is that it ships with one.
    THREE STATES: OK tables match the install · MISSING the install changed (STALE - regenerate) ·
    UNKNOWN no tables / no install to compare against (a CI runner) - never OK.
    """
    try:
        import item_tables as IT
        import d2s_read  # noqa: F401  (a reader that will not import cannot read anything)
    except Exception as e:
        return UNKNOWN, "the save reader or its tables will not import: %s" % str(e)[:90]
    try:
        code, say = IT.verify()
    except Exception as e:
        return UNKNOWN, "the item-table verifier raised: %s" % str(e)[:110]
    if code == getattr(IT, "SKIP", 77):
        return UNKNOWN, say
    if code != 0:
        return MISSING, say + " - every .d2s import would decode against last patch's bit widths"
    return OK, say


def _check_the_character_sheet_data_matches_the_install():
    """#174 v-B2 — DOES THE CHARACTER SHEET STILL SUM THE GAME'S OWN PROPERTY DATA?

    window.D2R_CHAR_ENGINE sums a build's resistances, absorbs, PDR, FCR, MF, skills and the rest from a block
    tv/char_props.py writes into bible.html between CHAR_PROPS markers, generated ONCE from his install
    (uniqueitems / setitems / sets / runes / gems / properties / itemstatcost / difficultylevels and the base
    tables). A game patch that moves a range (res-all 20-30 -> 25-35) or a penalty (Hell -100) makes every sheet
    read a confident wrong number while each row still carries its source. So the block is re-derived here and
    compared - the engine ships WITH this row (heart-first), not after.
    THREE STATES: OK the block is what the install says · MISSING the install or the generator moved (STALE -
    run tv/char_props.py --write) · UNKNOWN no install to compare against (a CI runner) - never OK.
    """
    try:
        import char_props as CP
    except Exception as e:
        return UNKNOWN, "the character-sheet generator will not import: %s" % str(e)[:90]
    try:
        code, say = CP.check()
    except Exception as e:
        return UNKNOWN, "the character-sheet check raised: %s" % str(e)[:110]
    if code == getattr(CP, "SKIP", 77):
        return UNKNOWN, say
    if code != 0:
        return MISSING, say + " - every character sheet sums last patch's ranges"
    return OK, say


def _check_the_builder_database_matches_the_install():
    """#174 v-B2 fix round — DOES THE CHARACTER BUILDER STILL LIST THE GAME'S OWN ITEM DATABASE?

    The builder's picker, its roll boxes, its tooltip and the mule window's hover all read the CB_DB block
    tv/char_builder_db.py writes into bible.html from his install (bases, uniques, set items, runewords, crafted
    recipes, runes and gems, each line in the game's own words with its range). It came from the SAME install as
    the character sheet's CHAR_PROPS block and had no row: after a patch 'character sheet data' would go MISSING
    while the picker's names and ranges drifted with nothing watching them. This is its sibling.
    THREE STATES: OK the block is what the install says · MISSING the install or the generator moved (STALE - run
    tv/char_builder_db.py --write) · UNKNOWN no install to compare against (a CI runner) - never OK.
    """
    try:
        import char_builder_db as CB
    except Exception as e:
        return UNKNOWN, "the builder-database generator will not import: %s" % str(e)[:90]
    try:
        code, say = CB.check()
    except Exception as e:
        return UNKNOWN, "the builder-database check raised: %s" % str(e)[:110]
    if code == getattr(CB, "SKIP", 77):
        return UNKNOWN, say
    if code != 0:
        return MISSING, say + " - the picker and every tooltip list last patch's items and ranges"
    return OK, say


def _check_the_mule_slot_rules_match_the_install():
    """#41 rank 15 (2026-09-29) — 'mule slot rules': DOES THE MULE WINDOW STILL WEAR, HOLD AND CLASS-LOCK WHAT THE GAME
    SAYS?

    The mule window's picker offers a slot only the bases the game wears there, refuses a second weapon beside a
    two-hander, names a bow's quiver and locks an orb to the Sorceress - all from the MULE_BASE_SLOT / MULE_NAMED_BASE /
    MULE_BASE_RULES blocks tv/mule_slot_map.py writes into bible.html from his install. They came from the SAME install
    as the builder's CB_DB block and had no row: this file had 0 references to mule_slot_map, and the only caller of its
    check() was a gate that skips without an install - so after a patch 'builder item data' would go MISSING while the
    mule's slots, hands and class rules drifted with nothing watching. This is its sibling, PERIODIC for the same reason
    (it pulls four tables plus itemtypes.txt from the install).
    THREE STATES: OK the blocks are what the install says · MISSING they are not (STALE - run tv/mule_slot_map.py
    --write) · UNKNOWN no install to compare against (a CI runner, the Mac) - never OK. What only a gate can hold, with
    no install: that CB_DB's hands and class equal MULE_BASE_RULES for every base
    (test_the_mule_rules_and_the_builder_agree_on_hands_and_class).
    """
    try:
        import mule_slot_map as MS
    except Exception as e:
        return UNKNOWN, "the mule slot-map generator will not import: %s" % str(e)[:90]
    try:
        code, say = MS.check()
    except Exception as e:
        return UNKNOWN, "the mule slot-map check raised: %s" % str(e)[:110]
    if code == getattr(MS, "SKIP", 77):
        return UNKNOWN, say
    if code != 0:
        return MISSING, say + " - the mule picker's slots, hands and class locks are last patch's"
    return OK, say


def characters_room_verdict(builds_raw, main_raw, vault_main_raw):
    """#41 rank 12 + 13 (2026-09-29) — the 👤 Characters room's stores, judged: -> (status, why).

    `builds_raw` is the board's d2r_charBuilds as stored (a JSON string, or None when the key is absent), `main_raw`
    its d2r_cbMain (the ★ MAIN build's id, a bare string or None) and `vault_main_raw` its d2r_mainCharacter (the
    vault's MAIN, {name, ...} JSON or None). Pure, so a law can drive every branch over fixtures.

    THREE STATES, and what each means for HIM:
      MISSING · d2r_charBuilds will not parse or is not a set of builds — the room reads UNKNOWN and refuses every
                write (a delete over it would write {} over his builds), so nothing he does there lands until the
                store is put back (the ledger backup carries it since REG-1481);
              · d2r_cbMain names a build that is not saved — the room marks no card MAIN and the planner's dropdown
                leads with none, while the pointer looks set;
      OK      · an absent or empty store is MEASURED empty (the room itself reads null / '' as "No characters yet");
                otherwise the count, the ★ MAIN and whether it is the vault's MAIN too;
              · rank 13 — ★ MAIN (d2r_cbMain, a build) and the vault's MAIN (d2r_mainCharacter, the lock's owner)
                NAMING DIFFERENT CHARACTERS is SAID, naming both, on the OK line. They are two stores under one
                word, separated by his ruling (bible.html 'chars-tab-js'): marking a build ★ MAIN locks none of its
                gear, the lock follows the vault's MAIN. Nothing said so anywhere; this does.
                ⚠ REG-1553 — SAID, NEVER RED. The planner names a build '<Class> build' (his one saved build: 'Amazon
                build') and the vault's MAIN is a character name he typed in the lock panel: two hand-typed strings in
                two vocabularies, and no reader can tell whether they are one character. The first cut went MISSING
                here and told him he could leave it — a red he is told to ignore carries nothing.
    A vault MAIN with no name yet is not a disagreement: said, never red. [[unknown-stays-unknown]]
    """
    if builds_raw is None or builds_raw == "":
        builds = {}
    else:
        try:
            builds = builds_raw if isinstance(builds_raw, dict) else json.loads(builds_raw)
        except Exception as e:
            return MISSING, ("d2r_charBuilds would not parse (%s) — the 👤 Characters room reads UNKNOWN and refuses every "
                             "write; put the store back from a ledger backup (the backup lane carries it)" % str(e)[:80])
        if not isinstance(builds, dict):
            return MISSING, ("d2r_charBuilds is %s, not a set of builds — the 👤 Characters room reads UNKNOWN and refuses "
                             "every write; put the store back from a ledger backup" % type(builds).__name__)
    n = len(builds)
    vault_name = None
    if vault_main_raw not in (None, ""):
        try:
            vm = vault_main_raw if isinstance(vault_main_raw, dict) else json.loads(vault_main_raw)
            vault_name = str(vm.get("name")).strip() if isinstance(vm, dict) and vm.get("name") else None
        except Exception:
            vault_name = None
    vault_say = ("the vault's MAIN is %s" % vault_name) if vault_name else "the vault's MAIN has no name yet (the lock panel takes one)"
    main_id = None if main_raw in (None, "") else str(main_raw)
    if main_id is not None and main_id not in builds:
        return MISSING, ("d2r_cbMain names build %r, which is not among the %d saved build%s — the room marks no card "
                         "★ MAIN and the planner leads with none; press ★ Set as MAIN on the build you play (%s)"
                         % (main_id, n, "" if n == 1 else "s", vault_say))
    if main_id is None:
        return OK, ("%d build%s, none marked ★ MAIN · %s" % (n, "" if n == 1 else "s", vault_say)) if n else \
            ("no builds yet (0 builds — the store is empty, not unread) · %s" % vault_say)
    b = builds.get(main_id) if isinstance(builds.get(main_id), dict) else {}
    main_name = str(b.get("name") or "").strip() or ("(unnamed build %s)" % main_id)
    if vault_name and main_name.lower() != vault_name.lower():
        # REG-1553 — said on the OK line, never MISSING (see the docstring): two vocabularies, one word, the door named
        return OK, ("%d build%s · ★ MAIN %s · the vault's MAIN is %s — two stores under one word: ★ MAIN locks no gear, the "
                    "lock follows the vault's MAIN (d2r_mainCharacter, the Vault's lock panel)"
                    % (n, "" if n == 1 else "s", main_name, vault_name))
    if vault_name:
        return OK, "%d build%s · ★ MAIN %s is also the vault's MAIN" % (n, "" if n == 1 else "s", main_name)
    return OK, "%d build%s · ★ MAIN %s · %s" % (n, "" if n == 1 else "s", main_name, vault_say)


#: #36 (REG-2909) - his rule: a doubt becomes a guided ask. REG-2910 - and the ask names only a screen a scan reads
#: (char_select.session_ask): character select or the lobby today, the C panel once its pixel band exists.
SESSION_RECENT = 10


def _session_ask():
    try:
        import char_select as _cs
        return _cs.session_ask()
    except Exception as e:
        return ("open character select, or the lobby, once",
                "which screens a scan reads is UNKNOWN - the learner will not import (%s)" % type(e).__name__)


def session_character_verdict(sessions, reels, why=None, ask=None):
    """#36 (REG-2909) - 'which character each session is on': IS THE NEWEST SESSION ON A CHARACTER THE BOARD CAN NAME?

    `sessions` is char_select.session_view's map (sessionId -> spans), `reels` this PC's reel folder names. The character
    a session is on NOW is its last span's. OK names it, how it is known (char-select / lobby / c-panel / carried) and how
    many of the last SESSION_RECENT sessions are named; MISSING asks him, in his words, when the newest session names
    nobody - every look in it reads holder UNKNOWN on the vault (REG-2908); UNKNOWN when the ledger would not read, never
    "no session". No reel at all is measured empty. -> (state, say)"""
    if sessions is None:
        return UNKNOWN, ("which character each session is on is UNKNOWN - %s"
                         % (why or "the character-select ledger could not be read"))
    starts = []
    for n in reels or []:
        m = re.match(r"^reel_s_(\d{10,})$", str(n))
        if m:
            starts.append((int(m.group(1)), str(n)))
    starts.sort()
    if not starts:
        return OK, "no session is recorded on this PC yet (0 reels) - nothing to name"
    recent = starts[-SESSION_RECENT:]

    def now_on(n):
        sp = sessions.get(n[5:])
        if not isinstance(sp, list) or not sp or not isinstance(sp[-1], dict):
            return None, None
        return sp[-1].get("character"), sp[-1].get("via")

    named = sum(1 for _s, n in recent if now_on(n)[0])
    tail = "%d of the last %d sessions name their character" % (named, len(recent))
    newest = recent[-1][1]
    who, via = now_on(newest)
    if not who:
        a_say, a_why = ask if ask is not None else _session_ask()   # REG-2910 the ask names a screen a scan reads
        return MISSING, ("session %s: character UNKNOWN - %s (%s%s)"
                         % (newest[5:], a_say, tail, ("; " + a_why) if a_why else ""))
    return OK, "session %s: %s (%s) - %s" % (newest[5:], who, via or "named", tail)


def _check_which_character_each_session_is_on():
    """#36 (REG-2909) - the live row: the learner's ledger and the gear ledger's chain through char_select.session_view
    (the one view the console's /api/chars_learned answer serves), and this PC's reel folders. UNKNOWN when the learner
    will not load, its ledger will not read, or the reel folder cannot be listed - never "0 sessions"."""
    try:
        import char_select as _cs
    except Exception as e:
        return UNKNOWN, "the character-select learner will not import: %s" % str(e)[:90]
    try:
        d = _cs.load()
        try:
            import equipped_ledger as _el
            gd, _gw = _el.load()
        except Exception:
            gd = None
        sessions, _rep = _cs.session_view(d, gd)
        root = _cs.hist_root()
        reels = sorted(n for n in os.listdir(root) if n.startswith("reel_")) if os.path.isdir(root) else None
    except Exception as e:
        return UNKNOWN, "the session characters raised %s" % type(e).__name__
    if reels is None:
        return UNKNOWN, "this PC's reel folder could not be listed - which sessions exist is UNKNOWN, not 0"
    return session_character_verdict(sessions, reels)


def _check_the_characters_room():
    """#41 rank 12 (2026-09-29) — 'characters room': DOES THE 👤 CHARACTERS TAB STILL READ HIS BUILDS, AND DO ITS TWO
    MAINS AGREE?

    The feature's heart was one proven law (test_the_characters_tab_is_manual_and_separate) and nothing at runtime: no
    doctor row named a broken link, nothing reached the eagle, and he has a real build in the store (backup 09-29
    01:10). This row reads d2r_charBuilds, d2r_cbMain and d2r_mainCharacter off the shared board read (the same
    fullStores the vault rows read — one read per tick, never a second) and judges them with characters_room_verdict.
    No console, a refused read, or a read that carried no stores is UNKNOWN — never "0 builds".
    ⚠ WHAT IT CANNOT SEE: whether #tab-chars is on the rendered board. The doctor reads stores, not the DOM; the tab's
    presence and its console door are pinned by the room's own law, and a pixel look is the eye's.
    """
    got = _board_read()
    if not got:
        return UNKNOWN, "the console did not answer — nobody asked the board, so his builds are UNKNOWN, not 0"
    if got.get("ok") is False:
        return UNKNOWN, "the board refused the read (%s), so his builds are UNKNOWN, not 0" % str(got.get("why"))[:90]
    fs = got.get("fullStores")
    if not isinstance(fs, dict):
        return UNKNOWN, "the board read carried no stores, so his builds are UNKNOWN, not 0"
    return characters_room_verdict(fs.get("d2r_charBuilds"), fs.get("d2r_cbMain"), fs.get("d2r_mainCharacter"))


def _check_their_tooltip_rows_are_ours():
    """#41 rank 16 (REG-1560) — IS THE SHIPPED TOOLTIP STILL THEIR TOOLTIP, ON THE PAGE ON DISK?

    The one independent engine the character builder has is their planner's in-game tooltip, measured once as text
    (203 rows over 6 runewords) - and until this row it was compared only by a gate at push time. The
    tvd-tooltip-oracle lane now runs the shipped composition over that oracle in node on this console's own cadence
    and writes a PER-ROW receipt; this row reads the receipt and the bible.html on disk, never node.
    THREE STATES: OK every oracle row judged and theirs (the build, the age and the oracle's limit said) ·
    MISSING a row never judged or a row that is not theirs, NAMED · UNKNOWN no receipt, node absent (a PC without
    node), a receipt the page has moved from, a summary in place of rows - never 0, never OK.
    """
    try:
        import tooltip_oracle_lane as _tol
    except Exception as e:
        return UNKNOWN, "the tooltip oracle lane will not import: %s" % str(e)[:90]
    try:
        st, why = _tol.verdict()
    except Exception as e:
        return UNKNOWN, "the lane's verdict raised: %s" % str(e)[:110]
    return {_tol.OK: OK, _tol.MISSING: MISSING}.get(st, UNKNOWN), why


def _check_the_item_vocabulary_can_name_his_loot():
    """v3364 (#60) — CAN THE VAULT NAME A MAGIC OR RARE ITEM, AND IS THE LEXICON STILL THE INSTALL'S?

    His ask: the vault and the AI item checker must know every item, and must know what to route to
    garbage. The roster names uniques, sets and runewords. MAGIC and RARE names are COMPOSED at drop
    time from four affix tables plus a base type, so they can never be a list — `affix_lexicon`
    carries that vocabulary, generated from his own install.

    ⚠⚠ TWO WAYS THIS GOES QUIETLY WRONG, AND BOTH ARE WHY THIS ROW EXISTS.
      · THE STORE GOES STALE. It is generated ONCE from a 28 GB install. A game patch moves the
        affix tables and nothing tells anyone: every classification keeps answering confidently out
        of last month's vocabulary. `sourceHash` is re-derived here and compared.
      · THE LEXICON STOPS BEING CONSULTED. If the soft import breaks, every name silently reads
        UNKNOWN — which is indistinguishable from a machine that simply has no install. So this
        counts how many of his CURRENT unsure rows can actually be named, and a sudden collapse to
        zero is visible instead of looking like an ordinary CI box.

    THREE STATES:
      OK       -> lexicon matches the install; says how many unsure names it can read
      MISSING  -> the install has changed since the lexicon was generated (STALE, act on it)
      UNKNOWN  -> no lexicon here, or it cannot be re-derived on this machine. ⚠ NEVER OK: a CI
                  runner has no game install, and "I could not look" is not "all is well".
    """
    try:
        import affix_lexicon as AL
    except Exception as e:
        return UNKNOWN, "the affix lexicon will not import: %s" % str(e)[:90]
    try:
        code, say = AL.verify()
    except Exception as e:
        return UNKNOWN, "the lexicon verifier raised: %s" % str(e)[:110]
    if code == getattr(AL, "SKIP", 77):
        return UNKNOWN, say
    if code != 0:
        return MISSING, say
    # It is fresh. Now: does anything actually READ it? Count against his live unsure rows.
    named = total = 0
    try:
        import json
        p = os.path.join(os.path.dirname(os.path.abspath(AL.__file__)), "vault_last_result.json")
        # ⚠ `io` IS NOT IMPORTED IN THIS MODULE and the first cut of this row used io.open.
        # The check still answered OK - with "(name 'io' is not defined)" in its own
        # sentence, which is the only reason it was caught. This is the scar from
        # [[test-venue]] verbatim: an io.open in a module that never imports io, whose
        # NameError got swallowed and left the check answering forever about nothing.
        with open(p, "rb") as _fh:
            _raw = _fh.read().decode("utf-8", "replace")
        rows = ((json.loads(_raw) or {}).get("result") or {}).get("unsure") or []
        for r in rows:
            nm = (r or {}).get("name")
            if not nm:
                continue
            total += 1
            k, _w = AL.classify(nm)
            if k and k != "UNKNOWN":
                named += 1
    except Exception as e:
        return OK, say + (" \u00b7 how many of his unsure names it can read is UNKNOWN (%s)"
                          % str(e)[:60])
    if not total:
        # ⚠ A ZERO NEEDS A DENOMINATOR. No unsure rows is not evidence the lexicon works.
        return OK, say + " \u00b7 no unsure rows on disk to read, so its live reach is UNMEASURED"
    return OK, say + (" \u00b7 it can name %d of %d unsure name(s)" % (named, total))


def _check_the_eye_reach_is_still_being_measured():
    """v3363 (#114) — IS THE PER-FILE REACH MEASUREMENT STILL LANDING ON NEW ROWS?

    `absent` says which changed files never reached the eye; `reach` says how much of the ones
    that DID reach it actually arrived. Truncation cuts mid-file, so a file whose `diff --git`
    header arrived and whose body was chopped is absent-clean and unread — measured at 8 of 67
    arrived files over 16 versions, including tv/second_eye_ledger.py on v3354 at 48.6%, the file
    that version exists to change, filed clean.

    ⚠⚠ THIS ROW EXISTS BECAUSE ON ≠ WORKING. If `payload_for` ever stops handing the map back —
    a refactor, a caller that drops the fourth value, an exception swallowed upstream — every new
    row simply carries `reach: null`, which is the SAME BYTES a row written before this version
    carries. A measurement that quietly stops looks exactly like a measurement nobody has needed
    yet. That is the vault-lane shape: on for months, reads 0, and truthfully reported.
    [[heart-first]] §2

    THREE STATES:
      OK       -> looks recorded since this version DO carry the map; says how many hit a cut file
      MISSING  -> looks were recorded since this version and NOT ONE carries it — the wire broke
      UNKNOWN  -> no look has been recorded since this version, so there is nothing to conclude.
                  ⚠ Never OK: zero rows is an absent denominator, not a clean bill of health.
                  [[zero-needs-a-denominator]]
    """
    try:
        import second_eye_ledger as L
    except Exception as e:
        return UNKNOWN, "the second-eye ledger will not import: %s" % str(e)[:90]
    try:
        rows = L._rows()
    except Exception as e:
        return UNKNOWN, "the ledger will not read: %s" % str(e)[:110]
    if rows is None:
        return UNKNOWN, "the ledger read returned nothing, so reach cannot be counted"
    SINCE = 3363
    def _n(r):
        v = str(r.get("version") or "").lstrip("v")
        return int(v) if v.isdigit() else -1
    fresh = [r for r in rows if _n(r) >= SINCE and r.get("reached") is not False]
    if not fresh:
        return UNKNOWN, ("no look has been recorded since v%d, so whether the per-file reach map "
                         "is still being written is UNMEASURED - not clean" % SINCE)
    carry = [r for r in fresh if isinstance(r.get("reach"), dict)]
    if not carry:
        return MISSING, ("%d look(s) since v%d and NOT ONE carries a per-file reach map. The "
                         "measurement has stopped, and a stopped one is byte-identical to a row "
                         "written before it existed" % (len(fresh), SINCE))
    bar = getattr(L, "REACH_CUT_BAR", 0.5)
    hit = []
    for r in carry:
        for p, v in (r.get("reach") or {}).items():
            if isinstance(v, dict) and (v.get("total") or 0) > 0 \
                    and float(v.get("got") or 0) / float(v["total"]) < bar:
                hit.append("%s@%s" % (p.split("/")[-1], r.get("version")))
    return OK, ("%d of %d look(s) since v%d carry a per-file reach map; %d arrived file(s) came "
                "in under %d%%%s"
                % (len(carry), len(fresh), SINCE, len(hit), int(bar * 100),
                   (" (%s)" % ", ".join(sorted(set(hit))[:4])) if hit else ""))


def _check_no_row_contradicts_its_own_stated_verdict():
    """v3376 (#125) — DOES A ROW WRITTEN BY TODAY PARSER AGREE WITH THE ANSWER IT CAME FROM?

    TWO INDEPENDENT SIDES:
        side A — `verdict`, what OUR parser concluded
        side B — the verdict the OTHER FAMILY stated in its own words, re-read from `answerHead`

    ⚠⚠ SCOPED TO THE CURRENT PARSER GENERATION, AND MY FIRST CUT WAS NOT. Without that scope this
    row reports 118 rows the ledger ALREADY accounts for: `verdict_provenance()` re-judges every
    stored verdict and reports "331 could be re-judged; 213 still agree with today parser and 118
    DO NOT". Those are old rows honestly stamped with the parser that judged them — that is
    re-judgement DEBT, already measured, and repeating it here would be a second derivation of one
    reader wearing two names. [[copy-drift]] [[heart-first]] rule 1
    MEASURED: v3375 carries judgedBy=v3315 and PARSER_GEN is now v3376, so it is exactly one of
    that 118 and belongs to that reader, not to this one.

    So this asks the question NOTHING ELSE asks: has the parser running RIGHT NOW written a row
    that its own answer denies? That is a live break rather than history.

    THREE STATES:
      OK       -> rows written by this generation were re-read and none contradicts itself
      MISSING  -> this generation wrote a row its own answer denies; NAMES the versions
      UNKNOWN  -> no row carries this generation stamp AND an answer yet, so there is nothing to
                  conclude. ⚠ Never OK: zero comparable rows is an absent denominator, and a
                  freshly bumped PARSER_GEN legitimately starts here.
                  [[zero-needs-a-denominator]] [[unknown-stays-unknown]]
    """
    try:
        import second_eye_ledger as L
        import second_eye_run as R
    except Exception as e:
        return UNKNOWN, "the second-eye modules will not import: %s" % str(e)[:90]
    try:
        rows = L._rows()
    except Exception as e:
        return UNKNOWN, "the ledger will not read: %s" % str(e)[:110]
    if rows is None:
        return UNKNOWN, "the ledger read returned nothing, so no verdict can be corroborated"
    if not hasattr(R, "_stated_verdict"):
        return UNKNOWN, ("this build has no _stated_verdict reader, so side B cannot be computed "
                         "- the comparison is UNMEASURED, not clean")

    gen = getattr(L, "PARSER_GEN", "")
    mine = [r for r in rows
            if str(r.get("judgedBy") or "") == gen and (r.get("answerHead") or "").strip()]
    older = len([r for r in rows
                 if str(r.get("judgedBy") or "") not in ("", gen)])
    if not mine:
        return UNKNOWN, ("no look carrying this parser generation (%s) has stored an answer yet, "
                         "so whether today parser contradicts itself is UNMEASURED - not clean. "
                         "%d row(s) from earlier generations are re-judgement debt and belong to "
                         "verdict_provenance()" % (gen, older))
    bad = []
    for r in mine:
        try:
            stated = R._stated_verdict(r.get("answerHead") or "")
        except Exception:
            continue
        stored = str(r.get("verdict") or "")
        if stated and stored and stated != stored:
            bad.append("%s(stored %s, said %s)" % (r.get("version"), stored, stated))
    if bad:
        return MISSING, ("%d of %d look(s) judged by %s store a verdict their own answer denies: "
                         "%s" % (len(bad), len(mine), gen, ", ".join(sorted(set(bad))[:5])))
    return OK, ("%d look(s) judged by %s were re-read against their own words; none contradicts "
                "itself (%d older row(s) are re-judgement debt, counted by verdict_provenance)"
                % (len(mine), gen, older))


def _check_a_worker_read_has_a_deadline():
    """v3381 — IS ANY SUBPROCESS PIPE STILL READ WITHOUT A DEADLINE?

    THE SECOND WEDGE IN ONE SESSION, AND THE ONE MY OWN SWEEP MISSED. v3380 fixed a browser
    launch that hung because subprocess.run could not reach the grandchildren holding its pipe.
    I then swept the class as "browsers" and as "lsof calls" — and the very next gate run hung
    again, on three bare `wp.stdout.readline()` calls in control_app.py that neither sweep could
    see. MEASURED: the suite's cumulative CPU went FLAT at 3:19 while an idle `ocr_mac --worker`
    held the pipe, and the hook reported "test_control HUNG — killed after 1500s on an IDLE
    machine (load 2.34)". The bound was innocent both times (2.66x margin).

    So the class is neither browsers nor lsof. It is A READ FROM A SUBPROCESS WITH NO DEADLINE,
    and this row watches exactly that, by the one pattern that is concrete enough to grade:
    `.stdout.readline()` on a pipe.

    ⚠⚠ NO GATE CAN ASK THIS. test_a_worker_read_has_a_deadline proves the three known sites are
    bounded TODAY. This asks whether a FOURTH has appeared anywhere in tv/ — a failure that is
    silent by construction, because an unbounded readline works perfectly until the day the
    worker goes quiet, and then presents as a timeout in an unrelated gate. [[heart-first]] §2

    FOUR STATES:
      OK         -> no unbounded pipe read anywhere in tv/; says how many modules were read
      MISSING    -> a bare .stdout.readline() exists — NAMES the file and line
      UNMEASURED -> no module could be read at all
      UNKNOWN    -> the scan itself failed. Never OK. [[zero-needs-a-denominator]]
    """
    import ast as _ast
    import glob as _glob
    import io as _io

    def _code(src):
        """Comments AND docstrings removed — a docstring is not a comment, and grading one as
        code produced four false readings in a single session."""
        out = "\n".join(l.split("#", 1)[0] for l in src.split("\n"))
        try:
            t = _ast.parse(src)
        except Exception:
            return out
        L = out.split("\n")
        for nd in _ast.walk(t):
            if not isinstance(nd, (_ast.Module, _ast.FunctionDef, _ast.AsyncFunctionDef, _ast.ClassDef)):
                continue
            b = getattr(nd, "body", None)
            if not b:
                continue
            f = b[0]
            if not (isinstance(f, _ast.Expr) and isinstance(getattr(f, "value", None), _ast.Constant)
                    and isinstance(f.value.value, str)):
                continue
            for i in range(f.lineno - 1, min((getattr(f, "end_lineno", None) or f.lineno), len(L))):
                L[i] = ""
        return "\n".join(L)

    def _write_before_bound(src, base):
        """v3391 — A PIPE WRITE THAT PRECEDES ITS OWN DEADLINE IS AN UNBOUNDED WRITE.

        v3381 bounded the READ and left the WRITE unbounded, with the deadline computed on the
        line AFTER it. A write to a worker's stdin blocks once the pipe buffer fills (measured:
        16,384 bytes on this Mac), so a worker that never reads its input holds the caller for
        ever - and the caller's own deadline, computed later, never gets to run.

        ⚠ THE OBVIOUS RULE IS HOLLOW. "does the enclosing function mention a deadline" was GREEN
        on the pre-fix code, because it mentioned one - one line too late. ORDER is the property,
        so order is what this grades.
        """
        out = []
        try:
            t = _ast.parse(src)
        except Exception:
            return out
        for fn in [n for n in _ast.walk(t)
                   if isinstance(n, (_ast.FunctionDef, _ast.AsyncFunctionDef))]:
            writes, bounds = [], []
            for nd in _ast.walk(fn):
                if isinstance(nd, _ast.Call):
                    f = nd.func
                    if (isinstance(f, _ast.Attribute) and f.attr == "write"
                            and isinstance(f.value, _ast.Attribute) and f.value.attr == "stdin"):
                        writes.append(nd.lineno)
                if isinstance(nd, _ast.Assign):
                    for tg in nd.targets:
                        if isinstance(tg, _ast.Name) and "deadline" in tg.id.lower():
                            bounds.append(nd.lineno)
            if not writes or not bounds:
                continue
            first = min(bounds)
            for w in writes:
                if w < first:
                    out.append("%s:%d" % (base, w))
        return out

    try:
        scanned, hits, whits = 0, [], []
        for path in sorted(_glob.glob(os.path.join(HERE, "*.py"))):
            base = os.path.basename(path)
            if base.startswith("test_") or base == "console_doctor.py":
                continue
            try:
                # closed here, not by the collector: this row opens every tv/ module on each pass
                with _io.open(path, encoding="utf-8", errors="replace") as _fh:
                    src = _fh.read()
            except Exception:
                continue
            scanned += 1
            whits.extend(_write_before_bound(src, base))
            if ".stdout.readline()" not in src:
                continue
            # ⚠ AST CALL SITES, NOT TEXT. The text version's first run accused run_gates.py,
            # whose only occurrence is a gate `why=` string quoting this very defect — prose read
            # as code, for the fifth time in one session. Measured there: 0 real .readline() calls
            # in the AST, 1 occurrence in raw text. Grading the parse tree is immune to prose
            # anywhere, including a docstring, a comment, or a quoted example.
            # [[source-reading-guard]]
            try:
                _t = _ast.parse(src)
            except Exception:
                continue
            for _nd in _ast.walk(_t):
                if not isinstance(_nd, _ast.Call):
                    continue
                f = _nd.func
                if not (isinstance(f, _ast.Attribute) and f.attr == "readline"):
                    continue
                v = f.value
                if isinstance(v, _ast.Attribute) and v.attr == "stdout" and not _nd.args:
                    hits.append("%s:%d" % (base, getattr(_nd, "lineno", 0)))
        if scanned == 0:
            return ("unknown", "no module in tv/ could be read, so this is unmeasured rather than clean")
        if whits and not hits:
            return ("missing",
                    "%d pipe WRITE(s) that precede their own deadline - a worker that never "
                    "reads its input blocks the writer, and the caller's later deadline never "
                    "runs: %s" % (len(whits), ", ".join(whits[:6])))
        if hits:
            return ("missing",
                    "%d unbounded pipe read(s) — a bare .stdout.readline() waits for ever if the "
                    "worker goes quiet, and surfaces as someone else's timeout: %s"
                    % (len(hits), ", ".join(hits[:6])))
        return ("ok",
                "no unbounded .stdout.readline() anywhere in %d module(s) — every subprocess pipe "
                "read carries a deadline, so a quiet worker cannot hold a caller for ever" % scanned)
    except Exception as e:
        return ("unknown", "the pipe-read scan did not run (%s), so this is unmeasured rather "
                           "than clean" % (e.__class__.__name__,))


def _check_no_browser_is_launched_unreaped():
    """v3380 — IS EVERY BROWSER LAUNCH IN tv/ STILL KILLED BY ITS GROUP?

    THE INCIDENT. Five consecutive pushes were refused as "test_control DID NOT FINISH in 1500s"
    at load averages 9.44, 16.50 and 9.43 — two of the three a QUIET machine, which is what
    finally killed the venue explanation. Two faulthandler dumps 120s apart named one frame:
    js_syntax_gate.check -> subprocess.run -> communicate -> select. subprocess.run(browser,
    timeout=T) kills the LAUNCHER and then drains the pipes again, but Chrome's renderer helpers
    INHERIT the stdout pipe and at least one reparents to launchd (measured: a live pid with
    PPID 1 while its launcher was gone), so that second drain never returns.

    ⚠⚠ NO GATE CAN ASK THIS. test_a_browser_is_killed_by_its_group proves js_syntax_gate is
    correct TODAY, at the one site it names. This asks a different question: has a NEW browser
    launch appeared anywhere in tv/ without the discipline? That failure is silent by
    construction — the new site works on every quiet machine, and surfaces weeks later as a push
    that will not finish, with the bound taking the blame. The cure for this exact shape already
    existed at test_control.py:129 (_reap, v1925) and js_syntax_gate referenced it ZERO times for
    four hundred versions. One file knowing is not the codebase knowing. [[the-unjoined-end]]

    WHAT IT ASKS, of the CODE and never of the prose: for every function in tv/ that launches a
    subprocess AND mentions a browser, does that function also carry the reaping discipline —
    its own session, a group kill, or a call to a named reaper?

    FOUR STATES:
      OK         -> every browser-launching function is group-reaped; says how many
      MISSING    -> a function launches a browser with no reaping discipline — NAMES it
      UNMEASURED -> no browser-launching function found at all, which is itself worth saying
      UNKNOWN    -> the scan could not parse the tree. Never OK. [[zero-needs-a-denominator]]
    """
    import ast as _ast
    import io as _io          # console_doctor does not import io at module scope; without this
                              # every read raised NameError into the inner except and the scan
                              # saw ZERO files — caught only because the UNKNOWN arm refuses to
                              # report OK on an empty denominator. [[zero-needs-a-denominator]]

    # ⚠⚠ STATED LIMIT, BECAUSE THE HONEST NARROW ROW BEATS THE DISHONEST WIDE ONE.
    # Two wider designs were built and both were wrong, in opposite directions:
    #   * per-FUNCTION browser hints could not see _run_browser_bounded at all — the helper takes
    #     its argv as a parameter, so it carries no browser flag and the row watched ITSELF plus
    #     one bystander while being blind to the very function the fix lives in;
    #   * per-MODULE hints then flagged four `node --check` launches, which cannot wedge because
    #     node forks no pipe-holding helpers. A row that reds on correct code gets deleted, and
    #     tuning it further would have been fitting the rule to the answer.
    # So this asks ONE reachable, true question instead: does js_syntax_gate still route its
    # browser launch through a helper that carries BOTH halves of the discipline? A browser
    # launcher added to some OTHER module is NOT covered by this row, and that gap is named here
    # rather than hidden behind a green. [[source-reading-guard]] [[unknown-stays-unknown]]
    GATE = os.path.join(HERE, "js_syntax_gate.py")
    HELPER = "_run_browser_bounded"

    try:
        with _io.open(GATE, encoding="utf-8", errors="replace") as _fh:
            src = _fh.read()
        tree = _ast.parse(src)
        lines = src.split("\n")
    except Exception as e:
        return ("unknown", "js_syntax_gate.py could not be read or parsed (%s), so whether the "
                           "browser launch is still group-reaped is unmeasured, not clean"
                           % (e.__class__.__name__,))

    def _body(name):
        """The function's CODE — docstring and comments both removed.

        ⚠ A DOCSTRING IS NOT A COMMENT. Stripping "#" leaves it untouched, and
        _run_browser_bounded's docstring quotes _reap's line "ONE killpg reaches the renderer
        grandchildren". So the first version of this row answered its own question out of its own
        prose: deleting the real os.killpg call left the law GREEN. That is the same trap, for the
        third time in one session — [[source-reading-guard]] section 4b, a positive assertion
        satisfied by the sentence that explains it.
        """
        for n in _ast.walk(tree):
            if isinstance(n, _ast.FunctionDef) and n.name == name:
                end = getattr(n, "end_lineno", None) or n.lineno
                start = n.lineno
                b = n.body
                if b and isinstance(b[0], _ast.Expr) and \
                   isinstance(getattr(b[0], "value", None), _ast.Constant) and \
                   isinstance(b[0].value.value, str):
                    start = (getattr(b[0], "end_lineno", None) or b[0].lineno)
                seg = "\n".join(lines[start:end]) if start >= n.lineno else \
                      "\n".join(lines[n.lineno - 1:end])
                return "\n".join(l.split("#", 1)[0] for l in seg.split("\n"))
        return None

    helper = _body(HELPER)
    check = _body("check")
    if helper is None:
        return ("missing", "%s is gone from js_syntax_gate.py — the browser launch is no longer "
                           "routed through a group-reaping helper, which is the v3380 wedge "
                           "returning" % HELPER)
    if check is None:
        return ("unknown", "js_syntax_gate.check() could not be located, so its launch path is "
                           "unmeasured rather than clean")

    missing = []
    if "start_new_session" not in helper:
        missing.append("no own session (killpg would then signal THIS process's group)")
    if "killpg" not in helper:
        missing.append("no group kill (the pipe-holding grandchild survives and communicate() "
                       "never returns)")
    if HELPER + "(" not in check:
        missing.append("check() no longer calls it, so the helper is inert")
    if missing:
        return ("missing",
                "the browser launch in js_syntax_gate is not fully group-reaped: %s. That is the "
                "v3380 wedge exactly — it passes every quiet run and then hangs a push, and the "
                "1500s bound takes the blame for a hang it did not cause." % "; ".join(missing))
    return ("ok",
            "js_syntax_gate routes its browser launch through %s, which starts the launcher in "
            "its own session and kills by GROUP on timeout — a launcher that outlives its "
            "timeout cannot leave a pipe-holding grandchild behind. ⚠ This row watches that one "
            "launcher; a browser started from another module is not covered." % HELPER)




def _check_a_look_keeps_its_evidence():
    """v3386 (#129) — CAN THE LOOKS IN THE LEDGER STILL BE RE-JUDGED?

    `answerHead` is a PREFIX. MEASURED before v3386: 898 rows, 876 with an answer, median 400
    chars, max 600 — the cap — and the text past it stored nowhere, so no parser change could
    EVER be validated against what the eyes actually said.

    ⚠ THE 898 OLDER ROWS ARE NOT A FAULT AND THIS MUST NOT SAY THEY ARE. They predate the field;
    their evidence is gone and cannot be recovered. Reporting them as broken would make this row
    permanently red and therefore furniture. What it watches is the WRITER: a row that carries a
    length but no full text means the keeping stopped working.

    ⚠ NO GATE CAN ASK THIS. The gate proves record() stores the evidence today. This asks whether
    his actual ledger is accumulating re-judgeable rows — a number that moves on its own with
    every look, and the only thing that ever makes a parser change arguable from data.

    FOUR STATES:
      ok         -> every row that carries an answer length also carries the text; says how many
      missing    -> a row has answerChars and no answerFull, so the writer stopped keeping it
      unmeasured -> no ledger yet, so there is no look to keep evidence for
      unknown    -> the reader would not run. Never ok. [[zero-needs-a-denominator]]
    """
    try:
        import second_eye_ledger as _L
    except Exception as e:
        return UNKNOWN, "second_eye_ledger will not import (%s), so evidence is unmeasured" % str(e)[:60]
    if not hasattr(_L, "answer_for_rejudge"):
        return MISSING, ("the ledger no longer answers answer_for_rejudge, so nothing can tell a "
                         "stored answer from a stored prefix")
    p = str(getattr(_L, "LEDGER_PATH", "") or "")
    if not p or not os.path.exists(p):
        return UNMEASURED, ("no second-eye ledger exists yet, so there is no look whose evidence "
                            "could be kept - an absent question, not a clean answer")
    import io as _io
    import json as _json
    rows, broken = [], []
    try:
        with _io.open(p, encoding="utf-8") as fh:
            for ln in fh:
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    rows.append(_json.loads(ln))
                except Exception:
                    continue
    except Exception as e:
        return UNKNOWN, "the ledger would not read (%s), so this is unmeasured" % type(e).__name__
    if not rows:
        return UNMEASURED, "the ledger is empty, so there is no evidence to keep"
    kept = 0
    for r in rows:
        if not isinstance(r, dict):
            continue
        chars = r.get("answerChars")
        full = r.get("answerFull")
        if isinstance(chars, int) and chars > 0 and not (isinstance(full, str) and full):
            broken.append(str(r.get("version") or "?"))
        txt, _complete = _L.answer_for_rejudge(r)
        if txt:
            kept += 1
    if broken:
        return MISSING, ("%d row(s) carry an answer length but no answer text (%s) - the writer "
                         "stopped keeping the evidence it was handed"
                         % (len(broken), ", ".join(broken[:4])))
    old = len(rows) - kept
    return OK, ("%d of %d look(s) can be re-judged; the other %d predate the field and their "
                "evidence is gone for good - UNKNOWN by construction, not a fault"
                % (kept, len(rows), old))


def _check_a_present_machine_has_a_fresh_last_seen():
    """v3390 (#135) — IS ANY MACHINE ALIVE IN PRESENCE BUT FROZEN IN LAST-SEEN?

    Konyo watched Dean in the console app while his fleet row said 26 hours. Cause: the roster
    wrote `lastseen:` only on a MATERIAL change, so an idle console checked in every ~4 minutes
    and left no trace. Presence refreshed on a timer; the durable stamp did not.

    ⚠ NO GATE CAN ASK THIS. The gate proves the handler records an idle beacon TODAY, against a
    stub KV. Whether the rows this console is holding RIGHT NOW are internally consistent depends
    on which build each peer is running and how long each has idled — it moves on its own.

    ⚠ THE TWO SIDES ARE INDEPENDENT BY CONSTRUCTION: `online` membership comes from the `console:`
    presence key (TTL-bounded, refreshed on a timer), and `t` comes from the `lastseen:` record.
    Different keys, different write conditions. A machine that is ONLINE cannot honestly carry a
    last-seen older than the presence TTL, because it must have beaconed inside that window to
    still be listed. [[heart-first]] rule 1

    ⚠ IT READS THE PRESENCE CACHE, NEVER THE NETWORK.

    FOUR STATES:
      ok         -> every online row's last-seen is inside the window it must have beaconed in
      missing    -> an online row's stamp is older than that; names the machines and the ages
      unmeasured -> nothing is online, so there is no row that MUST be fresh
      unknown    -> a reader would not run. Never ok.
    """
    try:
        import control_app as _ca
    except Exception as e:
        return UNKNOWN, ("control_app will not import (%s), so presence cannot be read"
                         % str(e)[:60])
    try:
        cache = _serving_console(_ca)._FLEET_PRESENCE_CACHE
    except Exception as e:
        return UNKNOWN, ("control_app no longer exposes _FLEET_PRESENCE_CACHE (%s)"
                         % type(e).__name__)
    last = cache.get("d") if isinstance(cache, dict) else None
    if not isinstance(last, dict):
        return UNMEASURED, ("this console holds no fleet roster yet, so no row can be checked - "
                            "an absent question, not a clean answer")
    online = [r for r in (last.get("online") or []) if isinstance(r, dict)]
    if not online:
        return UNMEASURED, ("no machine is online, so no row is obliged to carry a fresh "
                            "last-seen - offline rows are ALLOWED to be old")
    # The presence key's own TTL is the bound: to be listed online at all, a machine beaconed
    # within it. A stamp older than that is two keys disagreeing about one machine.
    PRESENCE_TTL_S = 2400
    import calendar as _cal
    # ⚠⚠ REG-1302 — AGED AT THE SNAPSHOT'S OWN CLOCK, NOT AT THIS CHECK'S. Both sides of this
    # corroborator (online membership and `t`) come from ONE cached roster, so the question "was a
    # machine listed online with a stale stamp" must be asked at the moment that roster was
    # listed. Aged against time.time() instead, it measured THE CACHE: MEASURED 2026-09-25 on his
    # console, "GrokBot (57m); Konyo ALT TEST (58m); Konyo (59m)" - while a fresh /api/fleet showed
    # the same three rows 133-226 s old. His roster had simply not been re-fetched for ~55 min, and
    # the row told him three present machines were away. The server's own `now` is preferred (same
    # clock as `t`); the local fetch time is the fallback; neither -> UNKNOWN, never a guess.
    snap_now, clock = None, None
    try:
        if last.get("now"):
            snap_now = _cal.timegm(time.strptime(str(last.get("now"))[:19], "%Y-%m-%dT%H:%M:%S"))
            clock = "the roster's own clock"
    except Exception:
        snap_now = None
    if snap_now is None:
        try:
            _ct = float(cache.get("t") or 0)
            if _ct > 0:
                snap_now, clock = _ct, "the time this console fetched the roster"
        except Exception:
            snap_now = None
    if snap_now is None:
        return UNKNOWN, ("the cached roster carries no clock (no `now`, no fetch time), so a "
                         "last-seen cannot be aged at the moment its machine was listed online - "
                         "UNKNOWN, not stale")
    held = max(0, int((time.time() - snap_now) // 60))
    stale = []
    for r in online:
        t = r.get("t")
        if not t:
            continue                       # no stamp to judge; a different row's question
        try:
            age = snap_now - _cal.timegm(time.strptime(str(t)[:19], "%Y-%m-%dT%H:%M:%S"))
        except Exception:
            continue                       # undatable, not stale. [[unknown-stays-unknown]]
        if age > PRESENCE_TTL_S:
            stale.append("%s (%dm)" % (r.get("nickname") or r.get("machine"), int(age // 60)))
    if stale:
        return MISSING, ("%d of %d online machine(s) carry a last-seen older than the %dm "
                         "presence window they must have beaconed inside, so the roster is "
                         "telling him they are away while they are here: %s (aged at %s; this "
                         "roster is %dm old)"
                         % (len(stale), len(online), PRESENCE_TTL_S // 60, "; ".join(stale[:4]),
                            clock, held))
    return OK, ("all %d online machine(s) carry a last-seen inside the %dm window their presence "
                "implies (aged at %s; this roster is %dm old)"
                % (len(online), PRESENCE_TTL_S // 60, clock, held))


def _check_a_tally_agrees_with_its_own_ledger_verdict():
    """v3389 (#133) — DOES A ROW'S HEADLINE CLAIM AGREE WITH THE VERDICT INSIDE IT?

    Konyo: *"ok: True with have: 0 - a confident zero - while the mask says the board has handed
    over nothing... join it connect it the heart properly just like everything else"*.

    TWO GENUINELY INDEPENDENT SIDES, which is the whole bar for a corroborator:
      · the OUTER claim  - ok / sets.have / uniques.have / runewords.have, written by the tally
      · the NESTED verdict - ledgerVerdict, written by ledger_authority.classify_row
    Different engines, and on his live roster right now they DISAGREE: row "Konyo ALT TEST"
    carries ok:True with three have:0 beside ledgerVerdict.ok:False and three UNSYNCED
    provenances. So this row can be seen red on real input, not only on a fixture.
    [[heart-first]] rule 1

    ⚠ AN OLDER PEER IS A REAL CAUSE, NOT AN EXCUSE. A console below v3389 seals no `measured`
    field, so its zeros arrive unqualified. That IS the disagreement — and naming it is the
    actionable half, because the fix is that machine updating.

    ⚠ IT READS THE PRESENCE CACHE, NEVER THE NETWORK.
    [[a-gate-can-perturb-what-it-measures]]

    FOUR STATES:
      ok         -> every judged ledger's headline agrees with its own provenance, both ways
      missing    -> a ledger disagrees - a never-synced 0 shown as a count, or (#240) a real
                    count hidden as never synced; names the machine and the ledger
      unmeasured -> no roster, or no row carries a verdict to compare against
      unknown    -> a reader would not run. Never ok.
    """
    try:
        import control_app as _ca
    except Exception as e:
        return UNKNOWN, ("control_app will not import (%s), so no tally can be compared"
                         % str(e)[:60])
    try:
        cache = _serving_console(_ca)._FLEET_PRESENCE_CACHE
    except Exception as e:
        return UNKNOWN, ("control_app no longer exposes _FLEET_PRESENCE_CACHE (%s)"
                         % type(e).__name__)
    last = cache.get("d") if isinstance(cache, dict) else None
    if not isinstance(last, dict):
        return UNMEASURED, ("this console holds no fleet roster yet, so there are no two sides "
                            "to compare - an absent question, not a clean answer")
    rows = [r for r in ((last.get("online") or []) + (last.get("offline") or []))
            if isinstance(r, dict) and isinstance(r.get("tally"), dict)]
    if not rows:
        return UNMEASURED, "no row on the roster carries a tally at all"
    # ⚠⚠ #240 — JUDGED PER LEDGER, IN BOTH DIRECTIONS. This compared the headline against
    # `ledgerVerdict.ok`, which answers "did the row answer" (classify_row copies the tally's ok),
    # never "is it a count" - so it could only ever catch a zero shown as progress, and it was
    # BLIND to the opposite defect by construction: on 2026-09-25 every current console hid real
    # counts (134, 312, 99 ...) as "never synced" and this row stayed quiet. The authority's word
    # for each ledger is the independent side; the headline for that ledger (`measuredBy`, or the
    # row bit on a peer too old to send it) must agree with it either way.
    _MEAS = {"SYNCED": True, "SEEDED": True, "MANUAL": True, "UNSYNCED": False}
    judged, bad = [], []
    for r in rows:
        t = r["tally"]
        lv = t.get("ledgerVerdict")
        led_rows = [L for L in ((lv or {}).get("ledgers") or []) if isinstance(L, dict)
                    and L.get("ledger") in ("sets", "uniques", "runewords")
                    and isinstance(t.get(L.get("ledger")), dict)
                    and str(L.get("provenance") or "").upper() in _MEAS]
        if not isinstance(lv, dict) or not led_rows:
            continue                      # no verdict to disagree WITH
        judged.append(r)
        by = t.get("measuredBy") if isinstance(t.get("measuredBy"), dict) else None
        who = r.get("nickname") or r.get("machine")
        for L in led_rows:
            led = L["ledger"]
            want = _MEAS[str(L.get("provenance")).upper()]
            # ⚠ REG-1301 — AN OLD SEAL IS NOT THE SAME FACT AS A HIDDEN COUNT ANY MORE. Since
            # e81d7aab the card reads a peer with no `measuredBy` through its own provenance
            # (_measOf), so an old seal's contradiction no longer reaches the glass of a current
            # console - it reaches only an older card. MEASURED 2026-09-25 on his live roster: Konyo
            # (a console still running the pre-#240 seal) published measured=False beside three
            # SYNCED ledgers while every current card showed 134/309/99, and this row said "hidden
            # as never synced" - true of the payload, false of the screen. Found by the #231 eye.
            # Still MISSING (the payload contradicts itself and older peers still hide it); the
            # sentence now says what is true and what clears it.
            old_seal = not (by is not None and led in by)
            said = t.get("measured") if old_seal else by.get(led)
            if want is False and said is not False:
                if old_seal:
                    bad.append("%s %s is %s but its old seal does not say so (measured=%r, no "
                               "measuredBy) - current cards read the provenance, an older card "
                               "shows the 0 as a count; that console needs the per-ledger seal"
                               % (who, led, L.get("provenance"), said))
                else:
                    bad.append("%s %s is %s but reads as a count (measured=%r)"
                               % (who, led, L.get("provenance"), said))
            elif want is True and said is False:
                if old_seal:
                    bad.append("%s %s is %s but its old seal says never synced (measured=False, "
                               "no measuredBy) - current cards read the provenance and show %s, an "
                               "older card still hides it; restarting that console onto the "
                               "per-ledger seal clears it"
                               % (who, led, L.get("provenance"), (t.get(led) or {}).get("have")))
                else:
                    bad.append("%s %s is %s but its %s figure is hidden as never synced"
                               % (who, led, L.get("provenance"), (t.get(led) or {}).get("have")))
    if not judged:
        return UNMEASURED, ("%d row(s) carry a tally but none carries a ledger verdict, so the "
                            "two sides cannot be compared - UNKNOWN, not agreement" % len(rows))
    if bad:
        return MISSING, ("%d ledger(s) across %d judged row(s) disagree with their own ledger "
                         "verdict - a never-synced 0 read as progress, or a real count hidden as "
                         "never synced: %s" % (len(bad), len(judged), "; ".join(bad[:4])))
    return OK, ("all %d judged row(s) agree with their own ledger verdict (%d row(s) carry no "
                "verdict and were not judged)" % (len(judged), len(rows) - len(judged)))


def _check_the_eye_asks_for_every_code_extension():
    """v3388 (#134) — DOES THE EYE'S PATHSPEC STILL COVER THE CODE THIS REPO ACTUALLY SHIPS?

    v3387 changed two Cloudflare function files and the eye saw NEITHER: both git pathspecs
    listed *.py, *.mjs, *.sh (and *.html for the roster) and `*.js` was never there. Worse than a
    dropped file — a file the pathspec excludes is never a CANDIDATE, so the omitted-file report
    said 0 truthfully, about a question it was never asked. [[zero-needs-a-denominator]]

    ⚠ NO GATE CAN ASK THIS. The gate proves the pathspec covers the extensions it names TODAY.
    This asks whether the repo has started shipping an extension nobody added — which changes
    on its own, silently, the first time a new kind of file lands.

    ⚠⚠ AND IT CARRIES NO SECOND COPY OF THE LIST. The expected extensions are PARSED OUT OF THE
    SHIPPED PATHSPEC, then compared against what the last looked version actually changed. A row
    holding its own hardcoded list would drift from the thing it watches and agree with itself
    for ever — one number wearing two names. [[copy-drift]] [[heart-first]] rule 1

    FOUR STATES:
      ok         -> every code file the last looked version changed is an extension the eye asks for
      missing    -> it changed a code extension the pathspec does not name; says which
      unmeasured -> nothing has been looked at yet, or that sha is not in this checkout
      unknown    -> a reader would not run. Never ok.
    """
    import io as _io
    import re as _re
    import subprocess as _sp
    here = os.path.dirname(os.path.abspath(__file__))
    try:
        src = _io.open(os.path.join(here, "second_eye_run.py"), encoding="utf-8").read()
    except Exception as e:
        return UNKNOWN, ("second_eye_run.py would not read (%s), so its reach is unmeasured"
                         % type(e).__name__)
    asked = set(m.lower() for m in _re.findall(r'"\*(\.[a-z0-9]+)"', src))
    if not asked:
        return UNKNOWN, ("no extension pathspec could be parsed out of second_eye_run.py, so "
                         "what the eye asks for is unmeasured - never assume it asks for all")
    # What this repo counts as CODE a reviewer must see. Deliberately narrow: data and config
    # are not review subjects, and a broad list would cry wolf on every workflow edit.
    code = {".py", ".js", ".mjs", ".cjs", ".ts", ".sh", ".html"}
    try:
        import second_eye_ledger as _L
        rows = [json.loads(l) for l in _io.open(_L.LEDGER_PATH, encoding="utf-8") if l.strip()]
    except Exception as e:
        return UNKNOWN, ("the second-eye ledger would not read (%s), so no looked version can "
                         "be checked" % type(e).__name__)
    looked = [r for r in rows if isinstance(r, dict) and r.get("sha")]
    if not looked:
        return UNMEASURED, ("no version has been looked at yet, so there is no changed-file set "
                            "to compare the pathspec against")
    sha = str(looked[-1].get("sha"))
    ver = str(looked[-1].get("version") or "?")
    try:
        import git_quiet as _gq
        p = _gq.run([_spawnable("git"), "-C", os.path.dirname(here),
                     "show", "--format=", "--name-only", sha],
                    close_fds=False, capture_output=True, text=True, timeout=60)
    except Exception as e:
        return UNKNOWN, "git would not run (%s), so the changed-file set is unmeasured" % type(e).__name__
    if p.returncode != 0:
        return UNMEASURED, ("%s (%s) is not in this checkout - a shallow clone cannot answer "
                            "this, and that is not a clean answer" % (ver, sha[:8]))
    files = [f.strip() for f in (p.stdout or "").splitlines() if f.strip()]
    if not files:
        return UNMEASURED, "%s changed no files this checkout can see" % ver
    blind = sorted({f for f in files
                    if not f.startswith("_archive/")
                    and os.path.splitext(f)[1].lower() in code
                    and os.path.splitext(f)[1].lower() not in asked})
    if blind:
        return MISSING, ("%s changed %d code file(s) whose extension the eye never asks git for, "
                         "so they were not even candidates to be reported missing: %s"
                         % (ver, len(blind), ", ".join(blind[:4])))
    return OK, ("%s: every one of %d changed file(s) is either an extension the eye asks for "
                "(%s) or not code at all" % (ver, len(files), " ".join(sorted(asked))))


def _check_a_presence_reading_names_its_door():
    """v3387 (#131) — DOES THE ROSTER THIS CONSOLE HOLDS CARRY BOTH DOORS, OR ONLY ONE?

    Konyo: *"he was logged in literally 6 hours ago i saw him with my eyes.. something is not
    rendering to you properly or fethchin from the right information data"*. He was right and
    nothing was broken: Dean's console APP really had not beaconed in 26h, and Dean really had
    been on the bible four hours earlier in a BROWSER. The site records both; THE FLEET read one.

    ⚠ NO GATE CAN ASK THIS. The gate proves the handler joins correctly on fixtures. Whether the
    roster THIS console is currently holding carries the joined field depends on which version
    of the Pages function answered — a deploy that has not landed, or a cached pre-v3387 payload,
    leaves the rail reading exactly as it did when it misled me, with every test still green.
    That is the difference between "the code is right" and "the thing is working".

    ⚠ IT READS THE PRESENCE CACHE, NEVER THE NETWORK. Asking Cloudflare from a health check
    would make the check a source of the traffic it measures.
    [[a-gate-can-perturb-what-it-measures]]

    FOUR STATES:
      ok         -> the rows carry a web half and the rail renders the joined phrase; says how
                    many people the second door actually accounts for
      missing    -> rows arrived with no webAt key at all (the endpoint answering this console
                    predates the join), or they carry it and the UI never renders it
      unmeasured -> no roster yet, so there is nothing to be joined or unjoined
      unknown    -> a reader would not run. Never ok. [[zero-needs-a-denominator]]
    """
    try:
        import control_app as _ca
    except Exception as e:
        return UNKNOWN, ("control_app will not import (%s), so presence cannot be read at all"
                         % str(e)[:60])
    try:
        cache = _serving_console(_ca)._FLEET_PRESENCE_CACHE
    except Exception as e:
        return UNKNOWN, ("control_app no longer exposes _FLEET_PRESENCE_CACHE (%s), so neither "
                         "door is readable from here" % type(e).__name__)
    last = cache.get("d") if isinstance(cache, dict) else None
    if not isinstance(last, dict):
        return UNMEASURED, ("this console holds no fleet roster yet, so there is no presence "
                            "reading to name a door for - an absent question, not a clean answer")
    rows = [r for r in ((last.get("online") or []) + (last.get("offline") or []))
            if isinstance(r, dict)]
    if not rows:
        return UNMEASURED, "the roster is empty, so no row can carry either door"
    joined = [r for r in rows if "webAt" in r]
    if not joined:
        return MISSING, ("all %d roster row(s) arrived with no webAt field, so the endpoint "
                         "answering this console still reports console beacons ONLY - the rail "
                         "is showing the same one-door age that read Dean as 26h away while he "
                         "was on the site" % len(rows))
    try:
        # ⚠ `io` is NOT module-level in this file — the sibling row above hit NameError on
        # exactly this line and was correctly reported UNKNOWN by its own arm.
        import io as _io
        ui = _io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "control_ui.html"), encoding="utf-8").read()
    except Exception as e:
        return UNKNOWN, ("the console UI would not read (%s), so whether the joined age reaches "
                         "his screen is unmeasured" % type(e).__name__)
    if "escC(_fleetSeen(m))" not in ui:
        return MISSING, ("the roster carries both doors on %d of %d row(s) and the rail never "
                         "renders the joined phrase - the second door is fetched and thrown "
                         "away" % (len(joined), len(rows)))
    withweb = [r for r in joined if r.get("webAt")]
    webnewer = [r for r in withweb if str(r.get("seenVia") or "") == "web"]
    extra = [w for w in (last.get("webOnly") or []) if isinstance(w, dict)]
    return OK, ("%d of %d roster row(s) carry both doors; %d have a browser half and %d are "
                "freshest THROUGH the browser rather than the console; %d person(s) read the "
                "bible with no console here at all"
                % (len(joined), len(rows), len(withweb), len(webnewer), len(extra)))


def fleet_label(m, rows):
    """The label a fleet row ACTUALLY RENDERS — a Python twin of control_ui's `_fleetName`.

    ⚠⚠ v3411 — AMBIGUITY IS A PROPERTY OF THE RENDERED STRING, NOT OF THE NICKNAME. His finding,
    carried since v3385. The old row counted shared non-empty NICKNAMES, which misses two whole
    populations: two rows whose nickname is EMPTY both render "?" and were skipped by
    construction, and a shared nickname where the UI adds the machine is NOT ambiguous at all.
    REPRODUCED on the shipped helper over a 5-row roster: two seats rendered the identical string
    'GrokBot · vm-1' and two more rendered '?', while the row answered OK because it found the
    disambiguator in control_ui.html. A FALSE OK on his screen.

    ⚠⚠ THIS IS A SECOND COPY OF A RULE THAT LIVES IN JAVASCRIPT, which is [[copy-drift]] by
    construction — so it is not left on trust. `test_two_seats_cannot_render_the_same_label`
    executes the SHIPPED `_fleetName` in node over a 9-roster table and asserts this function
    agrees on every row of every one. MEASURED before it shipped: rosters 9, AGREE 9, DIFFER 0,
    including whitespace-padded nicknames, a shared nickname where one machine is empty, two
    blank rows, a solo row with no machine, and an empty roster.
    """
    nick = str((m or {}).get("nickname") or "").strip()
    mach = str((m or {}).get("machine") or "")
    if not nick:
        return mach or "?"
    seen = 0
    for r in (rows or ()):
        if str((r or {}).get("nickname") or "").strip() == nick:
            seen += 1
    return (nick + " \u00b7 " + mach) if (seen > 1 and mach) else nick


def _check_a_fleet_row_identifies_its_machine():
    """v3385 (#130) — CAN HE TELL TWO ROWS APART WHEN THEY SHARE A NICKNAME?

    Konyo: *"two grokbot account si see in fleet"*. MEASURED the same minute — two REAL seats,
    both belonging there, sharing one nickname AND one install id:
        GrokBot  grok-bot-vm-346371813  v3383  install 1bba07477e40  online
        GrokBot  cursor                 v3377  install 1bba07477e40  offline
    Nothing may be merged; `machine` is the only field that differs.

    ⚠ NO GATE CAN ASK THIS. The gate proves the helper is correct and wired TODAY. Whether his
    roster CURRENTLY contains an ambiguous nickname moves on its own, as seats come and go, and
    it is exactly what decides whether the rail is readable this minute.

    ⚠ IT MATTERS BECAUSE OF v3384. The peer VERSION now decides whether item names can be
    published, so two identical labels hide WHICH seat is the stale one.

    ⚠ IT READS THE PRESENCE CACHE, NEVER THE NETWORK. [[a-gate-can-perturb-what-it-measures]]

    FOUR STATES:
      ok         -> either no nickname is shared, or the surface can disambiguate; names them
      missing    -> a nickname is shared and control_ui carries no disambiguator - his screen
      unmeasured -> no roster yet, so there is no pair to be ambiguous
      unknown    -> the readers would not run. Never ok. [[zero-needs-a-denominator]]
    """
    try:
        import control_app as _ca
    except Exception as e:
        return UNKNOWN, "control_app will not import (%s), so fleet labels are unmeasured" % str(e)[:60]
    try:
        cache = _serving_console(_ca)._FLEET_PRESENCE_CACHE
    except Exception as e:
        return UNKNOWN, ("control_app no longer exposes _FLEET_PRESENCE_CACHE (%s), so this "
                         "cannot see a single row" % type(e).__name__)
    last = cache.get("d") if isinstance(cache, dict) else None
    if not isinstance(last, dict):
        return UNMEASURED, ("this console holds no fleet roster yet, so no two rows can be "
                            "ambiguous - an absent question, not a clean answer")
    rows = [r for r in ((last.get("online") or []) + (last.get("offline") or []))
            if isinstance(r, dict)]
    if not rows:
        return UNMEASURED, "the roster is empty, so there is no label to be ambiguous"
    try:
        # ⚠ `io` IS NOT MODULE-LEVEL IN THIS FILE — every other reader imports it locally, and the
        # first cut of this row did not, hit NameError, and was correctly reported as UNKNOWN by
        # its own arm rather than as clean. The guard worked; the row was still wrong.
        import io as _io
        ui = _io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "control_ui.html"), encoding="utf-8").read()
    except Exception as e:
        return UNKNOWN, ("the console UI would not read (%s), so what his rows actually RENDER "
                         "is unmeasured" % type(e).__name__)
    if "_fleetName(" not in ui:
        return MISSING, ("the UI carries no _fleetName rule at all, so every row draws its bare "
                         "nickname and two seats sharing one cannot be told apart on his screen")
    labels = {}
    for r in rows:
        labels.setdefault(fleet_label(r, rows), []).append(r)
    collide = {k: v for k, v in labels.items() if len(v) > 1}
    if not collide:
        return OK, ("every row RENDERS a label no other row renders, so no two seats are "
                    "indistinguishable on his screen (%d row(s) read)" % len(rows))
    told = []
    for k in sorted(collide):
        vers = sorted(set(str(r.get("ver") or "?") for r in collide[k]))
        told.append("%r x%d on %s" % (k, len(collide[k]), "/".join(vers)))
    return MISSING, ("%d rendered label(s) are drawn by more than one seat, so those rows are "
                     "INDISTINGUISHABLE on his screen: %s"
                     % (len(collide), "; ".join(told)[:200]))


def _check_a_fleet_refusal_names_an_action():
    """v3384 (#128) — WHEN A PEER CANNOT PUBLISH NAMES, DOES THIS CONSOLE SAY WHAT WOULD FIX IT?

    Konyo: *"fleet still not working"*. MEASURED the same hour: the peer he meant was offline
    since 2026-09-19T03:38Z on v3342, and its beacon carries maskWhy "no board window" — which
    his panel rendered verbatim. True, and naming no action, which his #35 ruling forbids.

    ⚠⚠ THE SIBLING ROW ASKS THE OTHER HALF. `_check_the_fleet_can_name_what_it_counts` asks
    whether THIS console publishes a list for every count it publishes. This asks whether a PEER
    that publishes no list is described in terms the reader can act on. Same panel, opposite end
    of the wire, and neither covers the other.

    ⚠ NO GATE CAN ASK THIS. The gate proves the forward and the wording are correct today. This
    asks what his RUNNING roster actually contains — and the number moves on its own as other
    machines update, which is the whole point of watching it.

    ⚠ IT READS THE PRESENCE CACHE, NEVER THE NETWORK OR A BOARD. Asking the site on a heartbeat
    would perturb the thing it measures. [[a-gate-can-perturb-what-it-measures]]

    FOUR STATES:
      ok         -> every peer below the bar carries a reason that names the fix; says how many
      missing    -> a peer is below the bar and gets no actionable reason - his exact screen
      unmeasured -> no roster received yet, so there is no peer to describe
      unknown    -> the readers would not run. Never ok. [[zero-needs-a-denominator]]
    """
    try:
        import control_app as _ca
    except Exception as e:
        return UNKNOWN, "control_app will not import (%s), so peer refusals are unmeasured" % str(e)[:60]
    try:
        cache = _serving_console(_ca)._FLEET_PRESENCE_CACHE
    except Exception as e:
        return UNKNOWN, ("control_app no longer exposes _FLEET_PRESENCE_CACHE (%s), so this "
                         "cannot see a single peer" % type(e).__name__)
    if not hasattr(_ca, "peer_can_publish_names"):
        return MISSING, ("control_app no longer answers peer_can_publish_names, so every peer "
                         "below the bar is back to the bare sentence its own console wrote")
    last = cache.get("d") if isinstance(cache, dict) else None
    if not isinstance(last, dict):
        return UNMEASURED, ("this console holds no fleet roster yet, so there is no peer refusal "
                            "to describe - that is an absent question, not a clean answer")
    me = str(getattr(_ca, "MACHINE", "") or "")
    rows = [r for r in ((last.get("online") or []) + (last.get("offline") or []))
            if isinstance(r, dict) and str(r.get("machine") or "") != me]
    if not rows:
        return UNMEASURED, ("the roster names no machine but this one, so there is no peer to "
                            "describe")
    below, unnamed, unknown_ver = [], [], []
    for r in rows:
        ver = str(r.get("ver") or "").strip()
        try:
            can, why = _ca.peer_can_publish_names(ver)
        except Exception as e:
            return UNKNOWN, ("peer_can_publish_names raised on %r (%s), so this is unmeasured"
                             % (ver[:12], type(e).__name__))
        name = str(r.get("nickname") or r.get("machine") or "?")[:24]
        if can is None:
            unknown_ver.append(name)
        elif can is False:
            below.append("%s %s" % (name, ver))
            if not why:
                unnamed.append(name)
    if unnamed:
        return MISSING, ("%d peer(s) are below v%d and carry NO reason naming the fix (%s), so "
                         "the panel shows them the unactionable sentence their own console wrote"
                         % (len(unnamed), _ca.MASK_WITHOUT_BOARD_SINCE, ", ".join(unnamed[:4])))
    tail = ""
    if unknown_ver:
        tail = ("; %d report no readable version and stay UNKNOWN rather than being called out "
                "of date (%s)" % (len(unknown_ver), ", ".join(unknown_ver[:3])))
    # ⚠ THE DENOMINATOR IS THE PEERS THIS COULD READ, NOT EVERY PEER. A fixture caught the first
    # cut saying "all 1 peer(s) are at or above v3379" in the same breath as "1 report no readable
    # version" — a true count under a claim that was not true of it. An unmeasured peer belongs in
    # neither half. [[label-outlived-referent]] [[zero-needs-a-denominator]]
    known = len(rows) - len(unknown_ver)
    if not known:
        return UNMEASURED, ("no peer reports a readable version, so whether any of them could "
                            "publish item names is UNKNOWN rather than fine%s" % tail)
    if not below:
        return OK, ("all %d peer(s) with a readable version are at or above v%d, so none of them "
                    "is told it cannot publish item names%s"
                    % (known, _ca.MASK_WITHOUT_BOARD_SINCE, tail))
    return OK, ("%d of %d peer(s) with a readable version are below v%d and each is told what "
                "would fix it (%s)%s"
                % (len(below), known, _ca.MASK_WITHOUT_BOARD_SINCE, ", ".join(below[:4]), tail))


def _check_every_roster_publish_is_signed():
    """#95 - EVERY PUBLISHED OWNER IS SIGNATURE-VERIFIED, AND THIS PC'S LAST PUBLISH WAS NOT REFUSED.

    The site's Basic password is public, so a roster row is the owner's only when the owner's key
    signed it (functions/api/roster.js, tv/roster_sign.py). This row reads THIS PC's own two stores and
    never the network: its publish receipt (.tvd_roster.json, what the site said to its last POST) and
    its fetched roster cache (what the site holds for every owner), plus the PUBLIC half of its own key.
      missing -> this PC's last publish was refused or went unsigned, its two signers disagreed, a
                 published owner is NOT signature-verified, or the roster names a key for this PC's
                 owner that is not the key on this PC (refused until Konyo resets that owner's key from
                 the Mac - the command is in functions/api/roster.js)
      unknown -> a row published before signing, a corrupt row, no fetch yet, no receipt yet. Never ok.
    [[unknown-stays-unknown]] [[heart-first]]"""
    try:
        import control_app as _ca
        import roster_publish as _rp
    except Exception as e:
        return UNKNOWN, ("control_app or roster_publish will not import (%s), so no roster signature "
                         "is read" % str(e)[:60])
    try:
        state, why = _rp.doctor_row(_serving_console(_ca), int(time.time() * 1000))
    except Exception as e:
        return UNKNOWN, ("this PC's roster receipt, cache or key could not be read (%s), so no roster "
                         "signature is read" % type(e).__name__)
    return {"ok": OK, "missing": MISSING}.get(state, UNKNOWN), why


def _check_a_queue_zero_came_from_a_read_that_WORKED():
    """v3395 — WHEN THE DRAIN SAYS "NOTHING NEW", DID ANYONE ACTUALLY LOOK?

    FOUND BY THE WIN-1 SEAT on his Windows box. The drain's reader thread died with
    UnicodeDecodeError (cp1255, byte 0x9f), stdout came back EMPTY with returncode 0, and the tool
    printed "nothing new. That is a measured zero, not a failure to look." It was exactly a failure
    to look, and the sentence asserting otherwise is what makes it worse than silence.

    ⚠⚠ NO GATE CAN ASK THIS. test_a_failed_read_never_reaches_a_zero_claim proves the CODE refuses
    an empty stdout and decodes as UTF-8. It cannot know whether `gh` is reachable, authenticated,
    or rate-limited RIGHT NOW on THIS machine - and a drain that cannot run is exactly the state
    that used to report itself as clean.

    ⚠ IT ASKS THE CHEAPEST QUESTION THAT DISCRIMINATES: can the reader produce a parseable answer
    at all? It does NOT drain the queue - that is the seat's job and it costs paid calls.

    FOUR STATES:
      OK         -> the reader answered and its output parsed
      MISSING    -> the reader ran and produced NOTHING, which is the shape that lied
      UNMEASURED -> gh is not installed on this machine, so there is no question to ask
      UNKNOWN    -> the probe itself failed. Never OK. [[zero-needs-a-denominator]]
    """
    import json as _json
    import subprocess as _sp
    try:
        p = _sp.run([_spawnable("gh"), "api", "rate_limit"], capture_output=True,
                    encoding="utf-8", errors="replace", close_fds=False, timeout=12)
    except FileNotFoundError:
        return UNMEASURED, ("gh is not installed on this machine, so whether a queue zero came "
                            "from a working read is not a question that exists here")
    except Exception as e:
        return UNKNOWN, ("the reader probe did not run (%s), so whether a drain could look is "
                         "unmeasured rather than fine" % e.__class__.__name__)
    if p.returncode != 0:
        return MISSING, ("the reader cannot reach GitHub (%s), so any drain right now would "
                         "report nothing new WITHOUT HAVING LOOKED"
                         % (p.stderr or "").strip().replace("\n", " ")[:90])
    body = (p.stdout or "").strip()
    if not body:
        return MISSING, ("the reader exited 0 and printed NOTHING - the exact shape that made a "
                         "dead decode read as a measured zero on his Windows box")
    try:
        _json.loads(body)
    except Exception:
        return MISSING, ("the reader answered but its output does not parse, so a drain would see "
                         "no rows and could not tell that from an empty queue")
    return OK, ("the queue reader answers and its output parses (%d bytes), so a zero from the "
                "drain would be a measurement rather than a silence" % len(body))


def _check_a_verdict_comes_from_a_declared_field():
    """v3394 — IS THE EYE ACTUALLY DECLARING ITS VERDICT, OR IS THE PARSER STILL GUESSING?

    v3376 built `_stated_verdict` so a DECLARED verdict line is read first and prose is never
    matched. Its own comment claims the review prompt contains that line. IT DID NOT — COLD_FRAMING
    never asked for it, so the reader had no writer and every answer fell through to the prose path.
    [[the-unjoined-end]] [[plumbing-with-no-tap]]

    MEASURED on the ledger: 35 rows from v2805 to v3391 DECLARE the change clean in prose
    ("No defects found.", "No concrete defects.", "The change is correct.") and are filed as
    FINDINGS. agreement(), the eagle rows and the heart are wrong on every one of them.

    ⚠⚠ NO GATE CAN ASK THIS. test_the_eye_is_asked_for_the_verdict_it_is_read_for proves the prompt
    ASKS and that the reader reads. It cannot know whether a real eye, on a real look, actually
    emitted the line — only the ledger knows, and only after a look has been taken. A prompt that
    asks and an answer that never complies is the same unjoined end one step further along.

    ⚠ IT JUDGES ONLY LOOKS TAKEN SINCE THE ASK EXISTS. Rows recorded before v3394 could not have
    carried the field, and counting them would make a true history look like a live fault.
    [[stale-reading]]

    FOUR STATES:
      OK         -> every recent look carries a declared verdict; says how many
      MISSING    -> recent looks carry none, so the parser is back to guessing — names how many
      UNMEASURED -> no look has been taken since the ask existed; an absent question
      UNKNOWN    -> the ledger could not be read. Never OK. [[zero-needs-a-denominator]]
    """
    import io as _io2          # ⚠ io is NOT module-level in this file - third invented helper
    import json as _json
    import re as _re2
    try:
        import second_eye_ledger as _L
        import second_eye_run as _SE
    except Exception as e:
        return UNKNOWN, ("the second-eye modules could not be imported (%s), so whether a verdict "
                         "is declared is unmeasured rather than fine" % e.__class__.__name__)
    if "VERDICT:" not in getattr(_SE, "COLD_FRAMING", ""):
        return MISSING, ("the review prompt does not ask for a VERDICT line, so _stated_verdict "
                         "can never fire and every answer falls back to prose matching")
    try:
        # ⚠ LEDGER_PATH. I guessed LEDGER/PATH twice and got a confident "0 rows" both times —
        # a wrong-key zero, while investigating a parser that mis-reads answers.
        rows = []
        with _io2.open(_L.LEDGER_PATH, encoding="utf-8") as fh:
            for ln in fh:
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    rows.append(_json.loads(ln))
                except Exception:
                    continue
    except Exception as e:
        return UNKNOWN, ("the second-eye ledger could not be read (%s), so nothing is known about "
                         "how its verdicts were reached" % e.__class__.__name__)

    # ⚠ THE NEWEST LOOKS, NOT THE NEWEST SUBJECTS. My first version keyed on the version
    # being REVIEWED (>= 3394) and so reported UNMEASURED while a compliant look at v3393,
    # taken after the ask existed, sat in the ledger. What matters is WHEN THE LOOK WAS
    # TAKEN, not how old its subject is - a look at an ancient version taken today still
    # carries the field. [[stale-reading]] [[label-outlived-referent]]
    rows.sort(key=lambda r: str(r.get("ts") or ""))
    fresh = [r for r in rows[-6:] if (r.get("answerFull") or r.get("answerHead"))]
    if not fresh:
        return UNMEASURED, ("no look carries a stored answer, so whether the eye declares its "
                            "verdict is not yet knowable - an absent question, not a clean answer")
    # ⚠ REG-1267 — A DRAINED ROW'S VERDICT CAME FROM A FIELD, AND THIS READ THE WRONG ONE. MEASURED on
    # his console 2026-09-25: "6 of the 6 most recent look(s) carry NO declared verdict" - and all six
    # were drained from #231 (verdictFrom "gh#231 comment <id>"), whose look format carries a required
    # `verdict:` line that second_eye_drain reads as a FIELD, never as prose. The stored answer is only
    # the findings paragraph, so re-parsing it for a VERDICT line could never succeed and every drained
    # row read as "the parser is guessing" when nothing had guessed. schema is a declared route too.
    def _declared(r):
        vf = str(r.get("verdictFrom") or "")
        if vf == "schema" or vf.startswith("gh#231 comment"):
            return True
        return bool(_SE._stated_verdict(r.get("answerFull") or r.get("answerHead") or ""))
    declared = [r for r in fresh if _declared(r)]
    if len(declared) == len(fresh):
        return OK, ("all %d of the most recent look(s) carry a DECLARED verdict, so the parser "
                    "never had to guess from prose" % len(fresh))
    return MISSING, ("%d of the %d most recent look(s) carry NO declared verdict, so the parser "
                     "is back to matching prose on them - the shape that misfiled 35 rows from "
                     "v2805 to v3391" % (len(fresh) - len(declared), len(fresh)))


def _check_this_console_tree_is_established():
    """v3393 — DOES THIS MACHINE HAVE ITS OWN TREE, AND DID A WRITE ACTUALLY LAND IN IT?

    HIS RULING: fix "any machine establishes its own tree", never "the Windows PC", so Dean's PC is
    fixed BY PULLING with nobody touching it.

    MEASURED on his Windows ALT box, live: tv 756 entries, but tv\\frames and tv\\frames\\hist
    MISSING - while <home>\\d2r_ledger_backups existed AND had been written that same day. The
    machine provisions and writes perfectly well; it is the FRAME writers that establish nothing
    (control_app 15 scattered makedirs, frame_authority 0, reel_retention 0). Every reader of that
    tree then fails and the shelf opens into a 0x0 box.

    ⚠⚠ NO GATE CAN ASK THIS. test_a_machine_establishes_its_own_tree proves the CONTRACT - refusals
    carry no path, found means a write landed, a frozen build refuses the repo anchor. It cannot
    know whether THIS machine's tree exists, and it must not: a fresh machine is a legitimate state,
    not a test failure. That question is only answerable where the machine is. [[heart-first]]

    ⚠ IT REPORTS, IT NEVER PROVISIONS. ensure(create=False). A row that fixed the thing it measures
    would destroy the only evidence that the fault was ever there.

    FOUR STATES:
      OK         -> every root established AND a write proven at each; says how many
      MISSING    -> names the roots that are not established, and why each
      UNMEASURED -> no root could even be resolved, so there is nothing to judge
      UNKNOWN    -> the scan itself failed. Never OK. [[zero-needs-a-denominator]]
    """
    try:
        import machine_tree as _mt
    except Exception as e:
        return UNKNOWN, ("the tree discoverer could not be imported (%s), so whether this console "
                         "has its own tree is unmeasured rather than fine" % e.__class__.__name__)
    try:
        rows = _mt.ensure(create=False)
    except Exception as e:
        return UNKNOWN, ("the tree scan did not run (%s), so this is unmeasured rather than clean"
                         % e.__class__.__name__)
    if not rows:
        return UNMEASURED, ("no root could be resolved on this machine, so there is nothing to "
                            "judge - an absent question, not a clean answer")
    bad = [r for r in rows
           if r.get("state") in (_mt.UNUSABLE, _mt.FAILED, _mt.REFUSED)]
    if not bad:
        return OK, ("all %d root(s) are established and a write was PROVEN at each - existence "
                    "alone was not accepted" % len(rows))

    # ⚠⚠ THIS ROW'S OWN FIRST VERSION HAD THE DEFECT v3393 EXISTS TO FIX. The footage tree is
    # created inside tv_diablo._film_loop, so on a console that has never filmed it is absent BY
    # DESIGN. Calling that MISSING is TRUE and MISLEADING - it is the ordinary state of every
    # machine before its first recording, and reporting it as a fault is what sent him hunting a
    # sync defect that does not exist. A row that cries wolf on a normal state is a row he learns
    # to ignore. [[unknown-stays-unknown]] [[zero-needs-a-denominator]]
    _FILM_MADE = ("frames", "frames/hist")
    film = [b for b in bad if b.get("root") in _FILM_MADE]
    other = [b for b in bad if b.get("root") not in _FILM_MADE]
    if film and not other:
        return OK, ("%d of %d root(s) are established; the footage tree is not yet on this "
                    "machine, which is what a console looks like BEFORE its first recording - "
                    "_film_loop makes it when something films, so this is not a fault"
                    % (len(rows) - len(film), len(rows)))
    return MISSING, ("%d of %d root(s) are NOT established, so every reader of them fails: %s%s"
                     % (len(other), len(rows),
                        "; ".join("%s (%s) %s" % (b.get("root"), b.get("state"),
                                                  _mt._ascii(b.get("why")))
                                  for b in other[:4]),
                        " (the footage tree is also absent, but that is normal before a first "
                        "recording)" if film else ""))


def _check_the_compare_panel_can_name_a_difference():
    """v3392 — DOES THE CROSS-REFERENCE PANEL ACTUALLY NAME ANYTHING, ON HIS REAL FLEET?

    v3392 made the three columns invariant: they have - you do not, you have - they do not, you
    both need. A column whose names are unknown is REFUSED with its reason instead of being swapped
    for an easier question. That is CORRECT, and correctness is not the same as useful.

    ⚠⚠ NO GATE CAN ASK THIS. test_the_compare_columns_ask_one_question proves the labels are
    invariant in the SOURCE. It cannot see that every peer on his live fleet refuses every column,
    which would leave a panel that is perfectly right and tells him nothing - the exact state he
    photographed. A law about the code cannot measure the data. [[heart-first]] section 2

    FOUR STATES:
      OK         -> at least one peer yields a NAMED column; says how many of how many
      MISSING    -> peers exist and NONE names anything - correct and useless, and he should know
      UNMEASURED -> no peers to compare against, so there is no denominator
      UNKNOWN    -> the console or the route did not answer. Never OK.
                    [[zero-needs-a-denominator]] [[unknown-stays-unknown]]
    """
    fleet = _get("/api/fleet")
    if not isinstance(fleet, dict):
        return UNKNOWN, ("the console did not answer /api/fleet, so whether the compare panel can "
                         "name anything is unmeasured rather than fine")
    me = fleet.get("me")
    rows = list(fleet.get("online") or []) + list(fleet.get("offline") or [])
    peers = [r for r in rows
             if isinstance(r, dict) and r.get("machine") and r.get("machine") != me]
    if not peers:
        return UNMEASURED, ("no peer machines are on the fleet, so there is nothing to compare "
                            "against and a named column is not possible yet")
    named, refused, unreachable, mute = [], [], [], []
    for r in peers:
        m = r.get("machine")
        from urllib.parse import quote as _q
        j = _get("/api/fleet_compare?machine=" + _q(str(m), safe=""), timeout=6)
        if not isinstance(j, dict):
            unreachable.append(str(r.get("nickname") or m)[:28])
            continue
        if j.get("ok"):
            named.append(str(r.get("nickname") or m)[:28])
        else:
            # ⚠⚠ v3396 — A REFUSAL MUST STILL CARRY A REASON HE CAN ACT ON. The reason used to be
            # printed inside EACH refused column; his screenshot showed v3384's sentence three
            # times over, so it now renders ONCE above them. That makes it a SINGLE POINT OF
            # FAILURE: if the route stops forwarding a reason, the columns fall back to a bare
            # "no names published" and the actionable half — WHICH machine, WHICH version, WHAT
            # unblocks it — is gone, while the panel still looks deliberate.
            # [[the-unjoined-end]] [[unknown-stays-unknown]]
            if not (j.get("theirCanPublishWhy") or j.get("maskWhy") or j.get("why")):
                mute.append(str(r.get("nickname") or m)[:28])
            refused.append(str(r.get("nickname") or m)[:28])
    tot = len(peers)
    if unreachable and not named and not refused:
        return UNKNOWN, ("the compare route answered for none of the %d peer(s), so nothing is "
                         "known about what the panel can name: %s"
                         % (tot, ", ".join(unreachable[:5])))
    if mute:
        return MISSING, ("%d of %d peer(s) refuse WITHOUT A REASON, so the panel draws a bare "
                         "refusal and he cannot tell which machine or what unblocks it: %s"
                         % (len(mute), tot, ", ".join(mute[:5])))
    if named:
        return OK, ("the panel names a real difference for %d of %d peer(s): %s%s"
                    % (len(named), tot, ", ".join(named[:5]),
                       " - %d refuse (no names published)" % len(refused) if refused else ""))
    return MISSING, ("all %d peer(s) refuse every column, so the panel is CORRECT and tells him "
                     "nothing - each says why, but no difference can be named: %s"
                     % (tot, ", ".join(refused[:6]) or ", ".join(unreachable[:6])))


def _check_the_fleet_can_name_what_it_counts():
    """v3379 (#128) — DOES THIS CONSOLE PUBLISH A LIST FOR EVERY LEDGER IT PUBLISHES A COUNT FOR?

    Konyo, 2026-09-20, on his own fleet panel: *"we cant see or cross reference the items we each
    have or both need"*. The panel showed a peer at 131 of 135 beside "not published - no board
    window" in BOTH list columns — a COUNT with no LIST, which is the asymmetry this row exists
    to name out loud from now on.

    ⚠⚠ NO GATE CAN ASK THIS. The gates prove the hand-over and the fallback are correct TODAY.
    This asks whether his RUNNING console is still being handed the stores — and the failure is
    silent by construction: if the board stops posting them, the fallback correctly reports
    UNKNOWN, the count keeps publishing, and the panel goes back to exactly the screen he
    photographed with nothing anywhere reporting a fault. That is the same shape as `reach`
    dropping between v3363 and v3364. [[heart-first]] section 2 [[the-unjoined-end]]

    ⚠ IT READS DISK, NEVER THE BOARD. Asking the live board would cost a window evaluation on a
    heartbeat and would perturb the very thing it measures. board_tally.json is what the board
    last said it COUNTS; board_stores.json is what it last HANDED OVER; the question is whether
    the second can answer for every ledger the first speaks for.
    [[a-gate-can-perturb-what-it-measures]]

    FOUR STATES:
      OK         -> every ledger with a count can also be named; says how many bits each carries
      MISSING    -> a ledger publishes a COUNT and no LIST — the exact screen he reported
      UNMEASURED -> this console publishes no counts yet, so there is no asymmetry to have
      UNKNOWN    -> the readers would not run. Never OK. [[zero-needs-a-denominator]]
    """
    try:
        import control_app as _CA
        import fleet_mask as _FM
    except Exception as e:
        return UNKNOWN, "the fleet readers will not import: %s" % str(e)[:90]
    try:
        tally = _CA.board_tally_load()
    except Exception as e:
        return UNKNOWN, "the banked tally would not read (%s)" % type(e).__name__
    if not isinstance(tally, dict):
        return UNMEASURED, ("this console has no banked tally, so it publishes no count and "
                            "there is no count-without-a-list to find")
    counted = [k for k in sorted(_FM.LEDGERS)
               if isinstance(tally.get(k), dict)
               and isinstance((tally.get(k) or {}).get("have"), int)]
    if not counted:
        return UNMEASURED, ("the banked tally carries no readable count for any ledger the fleet "
                            "compares, so there is nothing to be missing a list for")
    named, blind = [], []
    for k in counted:
        try:
            mask, why = _CA._mask_from_board_store(k)
        except Exception as exc:
            mask, why = None, "the reader raised %s" % type(exc).__name__
        if mask:
            named.append("%s %d/%s" % (k, mask.get("have"), mask.get("n")))
        else:
            blind.append("%s (%s)" % (k, str(why or "no reason given")[:70]))
    if blind:
        return MISSING, ("%d ledger(s) publish a COUNT and no LIST — %s. That is the panel he "
                         "photographed: a peer at 131 of 135 with both cross-reference columns "
                         "empty. The board is not handing its stores to this console."
                         % (len(blind), "; ".join(blind)))
    return OK, ("every ledger this console counts it can also name: %s" % ", ".join(named))


def _check_a_reel_owes_what_its_engine_says():
    """v3378 (#28) — IS THE RIVER STILL CARRYING extract_gap's VERDICT, OR HAS IT GONE BACK TO
    RE-DERIVING ONE?

    `printer.py:508` has put `extract_gap`'s five-state answer on every printed row as
    `stations.extract.say` since v2572. `reel_router` read `sealed` and `names` off that same
    dict, threw the verdict away, and re-derived `sealed AND names -> JOIN, owes code`. MEASURED
    2026-09-20 on his 19 reels, the two disagreed on one:

        reel_s_1786385768689_67392   45 names, every one on a Chronicle page
            extract_gap:  NOT_A_HOLDING — "neither a join nor a capture gap"
            the river:    "sealed AND the names are on disk; the seal does not carry them. Code."

    ⚠⚠ THIS ROW EXISTS BECAUSE THE WIRE CAN BREAK SILENTLY AND LOOK EXACTLY LIKE BEFORE. If
    `_evidence` ever stops forwarding `say`, every reel arrives with `extractSay=None`, the
    decider's UNKNOWN arm correctly keeps the standing gate, and the screen goes back to the old
    wrong sentence with NOTHING anywhere reporting a fault — the fix would simply stop applying.
    That is the same shape as `reach` dropping between v3363 and v3364, and no gate can see it:
    a gate proves the code is right today, this asks whether his running river still carries it.
    [[heart-first]] §2 [[the-unjoined-end]]

    FOUR STATES:
      OK       -> every reel agrees with its own engine; says how many, and the JOIN split
      MISSING  -> a reel printed a verdict the row did not carry (the wire), or a row prints
                  owed work its own evidence does not derive (the decider)
      UNMEASURED -> the shelf is readable and holds no reel at this station — nothing to grade
      UNKNOWN  -> the route or the printer could not be read. ⚠ Never OK: an unreadable shelf
                  is an absent denominator, not a clean bill. [[zero-needs-a-denominator]]
    """
    try:
        import reel_router as _RR
        import printer as _P
    except Exception as e:
        return UNKNOWN, "the river will not import: %s" % str(e)[:90]
    try:
        rep = _reel_route_read()
    except Exception as e:
        return UNKNOWN, "the route raised %s, so no reel could be graded" % type(e).__name__
    if not rep.get("ok"):
        return UNKNOWN, ("the route could not be read (%s), so whether the river still carries "
                         "the verdict is UNKNOWN" % str(rep.get("why") or "no reason given")[:90])
    rows = rep.get("reels") or []
    if not rows:
        return UNMEASURED, ("the shelf is readable and holds no reel, so there is no row to grade "
                            "— that is an empty denominator, not agreement")

    # ⚠ THE SECOND SIDE IS THE PRINTER ITSELF, not this module re-deriving the verdict. A row is
    # only accused of a cut wire when the PRINTED station demonstrably carried a `say` the routed
    # row does not — otherwise a reel the engine genuinely could not answer for would be filed as
    # a broken join. [[unknown-stays-unknown]]
    printed = {}
    try:
        pr = _P.stream()
        if pr.get("ok"):
            for r in (pr.get("rows") or []):
                printed[str(r.get("reel") or "")] = (
                    ((r.get("stations") or {}).get("extract") or {}).get("say"))
    except Exception:
        printed = {}

    cut, wrong, join, nothing = [], [], 0, 0
    for r in rows:
        want, _why = _RR._owes_of(r.get("station"), r)
        if r.get("owes") != want:
            wrong.append(str(r.get("reel")))
        if r.get("station") == "JOIN":
            join += 1
            if r.get("owes") == _RR.NOTHING_OWED:
                nothing += 1
        p_say = printed.get(str(r.get("reel")))
        if p_say is not None and r.get("extractSay") is None:
            cut.append(str(r.get("reel")))

    if cut:
        return MISSING, ("%d reel(s) were PRINTED with an engine verdict the routed row does not "
                         "carry (%s) — the forward from printer to evidence is cut, so the river "
                         "is silently back to re-deriving its own answer"
                         % (len(cut), ", ".join(cut[:3])))
    if wrong:
        return MISSING, ("%d reel(s) print owed work their own evidence does not derive (%s) — "
                         "the row and the decider disagree about the same reel"
                         % (len(wrong), ", ".join(wrong[:3])))
    return OK, ("%d reel(s) on the shelf, every one printing the owed work its own engine "
                "derives; %d at JOIN, of which %d owe nothing because extract_gap ruled their "
                "names can never become a holding" % (len(rows), join, nothing))


def _check_the_eye_is_told_what_was_stripped():
    """v3375 (#122) — IS THE EYE STILL BEING TOLD WHAT WAS REMOVED FROM ITS PAYLOAD?

    `payload_for` strips two things before the eye ever sees the diff: comment-only added lines,
    and (in run_gates.py only) the `why=` ship notes. Both are deliberate and both are a REACH
    REDUCTION — the author's own account of the change is taken out — and for 15 versions neither
    was declared anywhere. A comment in second_eye_run.py even asserted they were "already
    declared", which was false the whole time.

    MEASURED on v3374: notes 7,885 chars (22% of the raw diff), comments 2,049. Across 39 version
    commits the comment strip fired 39/39 and the ship-note strip 22/39. THE COST IS NOT
    HYPOTHETICAL: v3374's own cross-family look came back reporting that "the test file claims
    panel-sourced names auto-bank; the banking step is not present" — a claim-versus-delivery
    finding assembled from a docstring, because the author's real note said the OPPOSITE and had
    been replaced by a stub the eye was never told about.

    ⚠⚠ THIS ROW EXISTS BECAUSE ON ≠ WORKING. The declaration lives in the PROMPT, which nothing
    keeps; the only durable trace is the `stripped` map on the row. If payload_for stops handing
    it back, or a caller drops it — which is exactly what happened to `reach` between v3363 and
    v3364 — every new row simply carries `stripped: null`, the same bytes a row written before
    this version carries. A measurement that quietly stops is indistinguishable from one nobody
    has needed yet. [[heart-first]] §2 [[the-unjoined-end]]

    THREE STATES:
      OK       -> looks since this version DO carry the map; says how much the eye never saw
      MISSING  -> looks were recorded since this version and NOT ONE carries it — the wire broke
      UNKNOWN  -> no look recorded since this version. ⚠ Never OK: zero rows is an absent
                  denominator, not a clean bill of health. [[zero-needs-a-denominator]]
    """
    try:
        import second_eye_ledger as L
    except Exception as e:
        return UNKNOWN, "the second-eye ledger will not import: %s" % str(e)[:90]
    try:
        rows = L._rows()
    except Exception as e:
        return UNKNOWN, "the ledger will not read: %s" % str(e)[:110]
    if rows is None:
        return UNKNOWN, "the ledger read returned nothing, so the strip map cannot be counted"
    SINCE = 3375

    def _n(r):
        v = str(r.get("version") or "").lstrip("v")
        return int(v) if v.isdigit() else -1

    fresh = [r for r in rows if _n(r) >= SINCE and r.get("reached") is not False]
    if not fresh:
        return UNKNOWN, ("no look has been recorded since v%d, so whether the eye is still told "
                         "what was stripped from its payload is UNMEASURED - not clean" % SINCE)
    carry = [r for r in fresh if isinstance(r.get("stripped"), dict)]
    if not carry:
        return MISSING, ("%d look(s) since v%d and NOT ONE carries a strip map. The eye is being "
                         "handed a diff with the author's own account removed and is not being "
                         "told, which is the v3374 shape" % (len(fresh), SINCE))
    tot = 0
    worst, worst_n = "", -1
    for r in carry:
        s = r.get("stripped") or {}
        n = sum(int(v or 0) for v in s.values() if isinstance(v, (int, float)))
        tot += n
        if n > worst_n:
            worst, worst_n = str(r.get("version") or "?"), n
    return OK, ("%d of %d look(s) since v%d carry a strip map; %s characters of the author's own "
                "account were removed before the eye saw them%s"
                % (len(carry), len(fresh), SINCE, "{:,}".format(tot),
                   (" (worst %s at %s)" % (worst, "{:,}".format(worst_n))) if worst_n > 0 else ""))


def _check_a_held_relaunch_is_not_stuck():
    """v3301 (#38) — THE INTERLOCK'S OWN SUPERVISOR: is the GREEN LIGHT still firing?

    The corroborator's two sides are genuinely independent, which is the whole point:

        side A — our own register says a relaunch is HELD
        side B — `nothing_in_flight()`, computed by control_app from the sweep / mini / agent
                 state, which knows nothing about the register

    A hold while side B says BUSY is the interlock working, and must read green. A hold that
    persists while side B has said CLEAR past the grace means the release path has stopped being
    called — the request will sit there and expire UNFIRED, which is the pre-v3301 abandon coming
    back through a different door. That is the one state nobody would otherwise notice, because a
    held relaunch looks pending right up until it silently is not.

    ⚠ A CONSOLE THAT IS NOT UP IS UNKNOWN, NEVER OK. Nothing can be held in a process that does
    not exist, and reporting that as healthy is a zero with no denominator.
    [[heart-first]] [[unknown-stays-unknown]] [[zero-needs-a-denominator]]
    """
    try:
        import control_app as ca
        import relaunch_hold as rh
    except Exception as e:
        return UNKNOWN, "could not import the interlock: %s" % str(e)[:90]
    try:
        st = getattr(ca, "_RELAUNCH_HOLD", None)
        if not isinstance(st, dict):
            return UNKNOWN, ("this console has no relaunch register, so whether a relaunch is "
                             "being held cannot be asked")
        if not st.get("held"):
            n = int(st.get("fired") or 0)
            d = int(st.get("dropped") or 0)
            return OK, ("no relaunch is held (fired %d, dropped-unfired %d since boot)" % (n, d))
        try:
            ok, _why = ca.nothing_in_flight("relaunch the console")
        except Exception as e:
            return UNKNOWN, ("a relaunch is held and what is in flight could not be read (%s), "
                             "so whether the green light is late is UNKNOWN" % type(e).__name__)
        bad, say = rh.stuck(st, ok)
        if bad:
            return MISSING, say
        return OK, say
    except Exception as e:
        return UNKNOWN, "the interlock could not be read: %s" % str(e)[:90]


#: 2026-09-28 — how long a build may sit on disk unadopted before that is a FAULT and not a wait.
#: MEASURED on his ALT: v3520 running beside v3521 on disk for over two hours, because a shadow
#: reel rolling every hour of play read as "you are filming" and the relaunch never landed.
BEHIND_THE_DISK_MAX_S = 2 * 3600


def _behind_ago(sec):
    sec = int(max(0, sec))
    return ("%dm" % (sec // 60)) if sec < 5400 else ("%.1fh" % (sec / 3600.0))


def behind_the_disk_verdict(running, disk, since_ms, now_ms, relaunch=None, watch=None,
                            written_ms=None, loaded_ms=None):
    """THE PURE HALF of 'the running build is behind the disk'. -> (state, why)

    running     the stamp the RUNNING process compiled in (/api/status `ver`), or None
    disk        the stamp the file on disk carries (control_app._disk_ver), or None
    since_ms    when this process first saw itself behind (/api/status drift.since) — None from a
                console that predates the reading
    relaunch    /api/status drift.relaunch — what the drift lane last decided and WHY (blocker)
    watch       the shadow watcher's record — an early close that FAILED is written there
    written_ms / loaded_ms   moduleFreshness' srcWrittenMs / loadedAtMs: for an OLDER console with
                no `since`, the disk file's last write is a LOWER bound on the wait and the
                process's load an UPPER bound. Past the bar on the lower bound is MISSING for sure;
                inside it on the upper bound is OK for sure; between them is UNKNOWN, said so.

    ⚠ TWO INDEPENDENT SOURCES: the running process's own compiled stamp, over the wire, against the
    literal in the file on disk — neither can be derived from the other. UNKNOWN when either cannot
    be read; never a green over a version nobody read. [[unknown-stays-unknown]] [[heart-first]]

    ⚠ MISSING NAMES WHY, because "it did not update" is not a location: his session (ON AIR / MINI,
    which never ends mid-film), the shadow close failed (an update waited on the shadow reel and
    it did not close), the relaunch did not take (it fired and this process is still here), or the
    relaunch refused (a sweep, a tree mid-edit, the switch, an unreadable world).
    """
    if not running or not disk:
        return UNKNOWN, ("%s cannot be read, so whether the running build is behind the disk is "
                         "UNKNOWN" % ("the running build" if not running else "the build on disk"))
    if running == disk:
        return OK, "running %s, which is the build on disk" % running
    now_ms = int(now_ms)
    age_s, bound = None, ""
    if isinstance(since_ms, (int, float)) and since_ms > 0:
        age_s = (now_ms - float(since_ms)) / 1000.0
    else:
        lower = ((now_ms - float(written_ms)) / 1000.0
                 if isinstance(written_ms, (int, float)) and written_ms > 0 else None)
        upper = ((now_ms - float(loaded_ms)) / 1000.0
                 if isinstance(loaded_ms, (int, float)) and loaded_ms > 0 else None)
        if lower is not None and lower > BEHIND_THE_DISK_MAX_S:
            age_s, bound = lower, "at least "
        elif upper is not None and upper <= BEHIND_THE_DISK_MAX_S:
            return OK, ("running %s while %s is on disk, for at most %s — inside the %s a build may "
                        "wait" % (running, disk, _behind_ago(upper), _behind_ago(BEHIND_THE_DISK_MAX_S)))
        else:
            return UNKNOWN, ("running %s while %s is on disk, and this console does not publish "
                             "when it fell behind (it predates that reading), so whether the wait "
                             "is past %s is UNKNOWN" % (running, disk, _behind_ago(BEHIND_THE_DISK_MAX_S)))
    rl = relaunch if isinstance(relaunch, dict) else None
    rwhy = str((rl or {}).get("why") or "").strip()
    if age_s <= BEHIND_THE_DISK_MAX_S:
        return OK, ("running %s while %s has been on disk %s — inside the %s a build may wait%s"
                    % (running, disk, _behind_ago(age_s), _behind_ago(BEHIND_THE_DISK_MAX_S),
                       (": " + rwhy) if rwhy else ""))
    head = ("running %s while %s has been on disk %s%s — past the %s a build may wait. "
            % (running, disk, bound, _behind_ago(age_s), _behind_ago(BEHIND_THE_DISK_MAX_S)))
    blocker = (rl or {}).get("blocker")
    w = watch if isinstance(watch, dict) else {}
    began = now_ms - age_s * 1000.0
    failed = w.get("updateCloseFailedAt")
    if isinstance(failed, (int, float)) and failed >= began:
        return MISSING, head + ("SHADOW CLOSE FAILED: the shadow reel would not close for the "
                                "waiting update — %s" % str(w.get("updateCloseWhy") or "no reason "
                                                            "was recorded")[:200])
    if blocker == "shadow":
        closed = w.get("updateClosedAt")
        return MISSING, head + ("SHADOW CLOSE FAILED: the update has been held on the shadow reel "
                                "and the reel never closed for it (%s)"
                                % ("its last early close was %s ago" % _behind_ago((now_ms - closed) / 1000.0)
                                   if isinstance(closed, (int, float)) else
                                   "no early close has ever been recorded"))
    if blocker == "his-session":
        return MISSING, head + ("HIS SESSION: %s — it never ends mid-film; the build lands when he "
                                "ends the session" % (rwhy or "a session he opened is rolling"))
    if blocker == "exec-failed" or (rl or {}).get("may") is True:
        return MISSING, head + ("THE RELAUNCH DID NOT TAKE: %s"
                                % (rwhy or "it was allowed and this process is still the old build"))
    if rl is None:
        return MISSING, head + ("RELAUNCH REFUSED, and this console does not publish why (it "
                                "predates the reason) — its fleet beacon's relaunch.why carries it")
    return MISSING, head + "RELAUNCH REFUSED: %s" % (rwhy or "no reason was recorded")


def _check_the_running_build_is_not_behind_the_disk():
    """★ HAS A NEW BUILD SAT ON DISK UNADOPTED FOR MORE THAN TWO HOURS — AND WHY? -> (state, why)

    MEASURED 2026-09-28 on his ALT (Windows + Boosteroid, shadow reader always on): the fleet row
    read ver v3520 / diskVer v3521 for over two hours, relaunch {armed: true, may: false, why: 'the
    console is ON AIR (live) — you are filming'}. Nothing on HIS side said so; the fleet row was
    the only place it showed, and it read as a normal wait. His words: "the logic needs to be
    individually placed and working for each console".

    ⚠ IT ASKS THE CONSOLE, never an in-memory import: this doctor may run in a different process,
    and a second copy of control_app would answer about itself. The running stamp and the drift
    lane's `since`/`relaunch` come over the wire from /api/status; the disk stamp is the file's own
    literal, read through control_app._disk_ver (one definition); the failed early close is the
    shadow watcher's record on disk. [[the-unjoined-end]] [[borrowed-surface]]
    """
    st = _get("/api/status")
    if not isinstance(st, dict):
        return UNKNOWN, ("the console did not answer /api/status, so which build it is running "
                         "cannot be read — whether it is behind the disk is UNKNOWN")
    try:
        import control_app as ca
        disk = ca._disk_ver()
    except Exception as e:
        return UNKNOWN, ("the build on disk could not be read (%s), so whether the running build "
                         "is behind it is UNKNOWN" % type(e).__name__)
    try:
        watch = ca.shadow_watch_state()
    except Exception:
        watch = None               # only names a cause; the verdict does not depend on it
    dr = st.get("drift") if isinstance(st.get("drift"), dict) else {}
    mf = st.get("moduleFreshness") if isinstance(st.get("moduleFreshness"), dict) else {}
    return behind_the_disk_verdict(st.get("ver"), disk, dr.get("since"), int(time.time() * 1000),
                                   relaunch=dr.get("relaunch"), watch=watch,
                                   written_ms=mf.get("srcWrittenMs"), loaded_ms=mf.get("loadedAtMs"))



def defeated_hidden(src):
    """Which elements carry `hidden` while an AUTHOR rule forces them to stay laid out?

    `[hidden] { display: none }` lives in the USER-AGENT stylesheet, and author rules beat UA
    rules regardless of specificity — so any author `display:` on the same element DEFEATS the
    attribute. v2443 found this on `button.act` AND HE IS THE ONE WHO NOTICED; it shipped a fix,
    wrote the law into a comment, and shipped NO GATE. v3271 then added `.win-ctl` with exactly
    the same defect, so his window controls rendered whether or not they could act.

    Takes SOURCE TEXT so one implementation serves two different subjects: the gate hands it the
    bytes on disk, the heart row hands it the bytes the live console actually serves. Two
    questions, one scanner — the alternative is two copies that disagree. [[copy-drift]]

    ⚠ THE SELECTOR SUBJECT IS WHAT MATTERS. `.bar > i` sets display on a CHILD, which a hidden
    PARENT already suppresses. Matching anywhere in the selector reported 10 offenders where
    there are 7 — the instrument, not the file. [[feedback-suspect-the-instrument]]

    ⚠ COMMENTS ARE STRIPPED FIRST, AND THE TRAP IS MEASURED, NOT THEORETICAL. The v2443 comment
    quotes `.sigil[hidden]`, `.stage-hold[hidden]` and the rule itself, so an unstripped scan
    credits guards that exist only in prose: `chron-waiting` is credited by a COMMENT and by
    nothing else. A scanner that reads its own documentation is too lenient in the quiet
    direction. [[source-reading-guard]]
    ⚠ And the strip is BOUNDED. An unbounded /*.*?*/ over this 5MB mixed file matches from a `/*`
    inside a string to the next `*/` anywhere and removed 16.9% of it once.

    -> {token: set(selectors)}; empty dict means every `hidden` in this source can actually hide.
    """
    import re as _re
    css = "\n".join(_re.findall(r"<style[^>]*>(.*?)</style>", src, _re.S))
    # v3397 — a NAMED switch, so the gate can PROVE the strip matters instead of asserting it.
    # Flipping it to False must make `chron-waiting` read as guarded, because a COMMENT is the
    # only place its guard exists. A red-proof is only as good as the anchor it can reach.
    STRIP_COMMENTS = True
    if STRIP_COMMENTS:
        css = _re.sub(r"/\*.{0,4000}?\*/",
                      lambda m: "\n" * m.group(0).count("\n"), css, flags=_re.S)

    def _subject(part):
        return _re.split(r"[\s>+~]+", part.strip())[-1]

    rules, guards = [], set()
    for m in _re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        sel, body = m.group(1).strip(), m.group(2)
        if "[hidden]" in sel and _re.search(r"display\s*:\s*none", body):
            for p in sel.split(","):
                guards.update(_re.findall(r"[.#]([A-Za-z0-9_-]+)\[hidden\]", _subject(p)))
        d = _re.search(r"(?:^|;)\s*display\s*:\s*([a-z-]+)", body)
        if d and d.group(1) != "none":
            for p in sel.split(","):
                if "[hidden]" not in p:
                    rules.append((p.strip(), _subject(p)))

    out = {}
    for _tag, attrs in _re.findall(r"<(\w+)([^>]*\shidden(?:\s[^>]*)?)>", src):
        if _re.search(r'hidden\s*=\s*"(?:false)?"', attrs):
            continue
        toks = []
        mi = _re.search(r'id="([A-Za-z0-9_-]+)"', attrs)
        if mi:
            toks.append(mi.group(1))
        mc = _re.search(r'class="([^"]+)"', attrs)
        if mc:
            toks += mc.group(1).split()
        on_el = set(toks)
        for t in toks:
            if t in guards:
                continue
            for full, subj in rules:
                if not _re.search(r"[.#]%s(?![A-Za-z0-9_-])" % _re.escape(t), subj):
                    continue
                # every token in the subject must be on THIS element, or the rule cannot match it
                if not set(_re.findall(r"[.#]([A-Za-z0-9_-]+)", subj)) <= on_el:
                    continue
                out.setdefault(t, set()).add(full[:60])
    return out


def _check_a_hidden_element_is_actually_hidden():
    """v3397 — CAN THE CONSOLE HE IS LOOKING AT ACTUALLY HIDE WHAT IT MARKS HIDDEN?

    ⚠ THIS ASKS A DIFFERENT QUESTION FROM ITS GATE, DELIBERATELY. The gate scans the bytes ON
    DISK. A console is a reading of its source taken at import, and it serves what it holds — so
    a corrected file and a console still serving the old CSS look identical from the tree. This
    row scans THE BYTES ON THE WIRE. [[stale-reading]]

    An absent console is UNKNOWN. It is never a pass.
    """
    import urllib.request as _ur
    try:
        with _ur.urlopen(CONSOLE + "/", timeout=8) as r:
            page = r.read().decode("utf-8", "replace")
    except Exception as e:
        return UNKNOWN, ("the console did not serve its own page (%s), so whether a `hidden` "
                         "element can actually hide is UNKNOWN, not clean"
                         % type(e).__name__)
    if len(page) < 50000:
        return UNKNOWN, ("the console served only %d bytes, which is not the console page, so "
                         "nothing was measured" % len(page))
    bad = defeated_hidden(page)
    if bad:
        names = ", ".join(sorted(bad)[:6])
        return MISSING, ("%d element(s) carry `hidden` while an author display rule keeps them "
                         "laid out, so marking them hidden does nothing: %s. `[hidden]` is a "
                         "USER-AGENT rule and any author `display:` beats it — add "
                         "`<sel>[hidden] { display: none !important; }`" % (len(bad), names))
    # v3402 — A VERDICT WITH NO WHY IS A LAMP, and this was the LAST one in the file. It survived
    # because the contract that refuses empty reasons runs `cd.run(include_slow=False)`, and this
    # row is not in that path — so the law grades a SAMPLE, not the population. The row now names
    # its DENOMINATOR too: "nothing was defeated" means nothing without saying what was scanned.
    # [[zero-needs-a-denominator]] [[regression-guard]]
    return OK, ("no element carries `hidden` while an author display rule keeps it laid out, "
                "measured across the %d bytes the console actually served" % len(page))


def _check_this_machine_is_keeping_itself_current():
    """v3404 — IS THIS MACHINE STILL PULLING, OR HAS IT QUIETLY FALLEN BEHIND THE FLEET?

    ⚠ HIS EXACT COMPLAINT, 2026-09-20: the KONYO ALT TEST box read CHILIAD 395 while his Mac read
    401, "moving even further away and still not being updated automatically". MEASURED there over
    SSH: zero scheduled tasks matching d2r/claude/konyo/pull/bible/tv, zero startup entries, and
    both console processes launched as raw `pythonw`. Every automatic pull in this codebase lives
    in a LAUNCHER, so a machine started any other way bypasses all of them — and is current only
    for as long as a human keeps pulling by hand.

    ⚠ ON IS NOT WORKING. A pull lane that is on and has never moved HEAD is perfectly fine while
    nothing is owed; it is a defect only when something IS. `behind` is the denominator that tells
    those apart, and without it "0 pulls" is unreadable. [[heart-first]] [[zero-needs-a-denominator]]

    ⚠ IT NEVER FETCHES. A heart row that hits the network on every eagle tick is a new cost on a
    surface that runs constantly, so this reads the ref the last fetch LEFT BEHIND and dates it
    from .git/FETCH_HEAD. A reading carries the age of the thing it measured. [[stale-reading]]
    """
    import subprocess as _sp
    g = os.path.join(ROOT, ".git")
    if not os.path.isdir(g):
        return UNKNOWN, ("this tree is not a git checkout, so whether it is current is UNKNOWN")
    try:
        import git_quiet as _gq
        r = _gq.run([_spawnable("git"), "-C", ROOT, "rev-list", "--count", "HEAD..origin/main"],
                    close_fds=False, capture_output=True, text=True, timeout=20)
        if r.returncode != 0:
            return UNKNOWN, ("git could not compare this tree against origin/main (%s), so how far "
                             "behind it is UNKNOWN, not zero"
                             % ((r.stderr or "").strip().splitlines() or [""])[-1][:80])
        behind = int((r.stdout or "0").strip() or 0)
    except Exception as e:
        return UNKNOWN, ("could not ask git how far behind this machine is (%s) — UNKNOWN, never "
                         "a measured zero" % type(e).__name__)
    # ⚠⚠ v3409 — TWO AGES, TWO QUESTIONS, AND THE OLD ROW ATTACHED ONE TO THE OTHER. `behind` is
    # `rev-list HEAD..origin/main`, which reads the LOCAL refs/remotes/origin/main and never
    # touches the network. Dating THAT number from FETCH_HEAD was dating a different file: any
    # `git fetch origin some-feature` rewrites FETCH_HEAD and leaves origin/main where it was, so
    # a machine whose main is a day stale could report "level ... fetched 0.0h ago". Named by the
    # cross-family review of v3404. [[stale-reading]] §1 — stamp the measurement, not the fetch.
    #
    # ⚠⚠ AND THE OBVIOUS FIX WAS WORSE, MEASURED BEFORE IT SHIPPED. Swapping in the REF's mtime
    # made this row read MISSING "32.1h (by packed-refs)" on a machine that had fetched minutes
    # earlier — because a fetch that brings nothing NEW does not rewrite the ref at all. That is a
    # row crying wolf on correct behaviour, which is the row someone silences.
    # [[strictness-that-closes-the-lane]]
    #
    # So both are reported and NEITHER is allowed to answer the other's question:
    #   FETCH_HEAD age  -> IS ANYTHING STILL FETCHING HERE   (the lane-alive question)
    #   ref age         -> WHEN origin/main ITSELF LAST MOVED (not when we last looked)
    fetch_h = ref_h = None
    try:
        fh = os.path.join(g, "FETCH_HEAD")
        if os.path.exists(fh):
            fetch_h = (time.time() - os.path.getmtime(fh)) / 3600.0
    except Exception:
        fetch_h = None
    for _p in (os.path.join(g, "refs", "remotes", "origin", "main"),
               os.path.join(g, "packed-refs")):
        try:
            if os.path.exists(_p):
                ref_h = (time.time() - os.path.getmtime(_p)) / 3600.0
                break
        except Exception:
            pass
    if fetch_h is None:
        return UNKNOWN, ("this checkout has never recorded a fetch, so whether anything pulls here "
                         "is UNKNOWN — not a clean bill")
    _moved = ("origin/main last moved %.1fh ago" % ref_h) if ref_h is not None \
        else "when origin/main last moved is UNKNOWN"
    if behind > 0:
        return MISSING, ("this machine is %d commit(s) BEHIND origin/main and the last fetch of "
                         "any ref was %.1fh ago, so it is running code the fleet has moved past. "
                         "Every automatic pull lives in a launcher — if this console was started "
                         "another way (raw pythonw, a shortcut, a supervisor) nothing here pulls "
                         "at all" % (behind, fetch_h))
    if fetch_h > 24:
        return MISSING, ("nothing has fetched here in %.1fh, so 'not behind' is a statement about "
                         "the last time anyone looked, not about now (%s)" % (fetch_h, _moved))
    # ⚠ "NOTHING TO PULL", NOT "LEVEL". `rev-list HEAD..origin/main` counts only what is BEHIND,
    # so it answers 0 for a machine that is level AND for one that is several commits AHEAD — his
    # Mac is normally ahead, mid-arc. Saying "level" there is a right number under a word that no
    # longer describes it. [[label-outlived-referent]]
    return OK, ("nothing to pull — this machine is not behind origin/main. Last fetch of any ref "
                "%.1fh ago, and %s. ⚠ neither age dates the other: a fetch that brings nothing "
                "new leaves the ref untouched" % (fetch_h, _moved))


#: #64 — the /api/status key the console publishes its pull lane under (control_app.pull_state()).
_PULL_LANE_KEY = "pullLane"
#: used ONLY when a console publishes a lane without its own bar (it predates `failBarS`)
_PULL_FAIL_BAR_FALLBACK_S = 3600


def pull_lane_verdict(pl, now_ms=None):
    """THE PURE HALF of 'this checkout can update'. -> (state, why)

    `pl` is the console's pull lane as /api/status publishes it. OK when the last attempt worked or
    the lane is standing down ON PURPOSE (TV_NO_AUTO_PULL, local tracked edits) and says so; MISSING
    when attempts have failed for longer than the lane's own bar, naming the reason and since when,
    and at once when an update was INTERRUPTED mid-checkout (a stale 0-byte lock beside a dirty tree);
    UNKNOWN when nobody has tried, when failures are still younger than the bar, or when the lane
    reports something this row cannot grade. [[unknown-stays-unknown]]
    """
    if not isinstance(pl, dict):
        return UNKNOWN, ("the console published no readable pull lane, so whether this checkout can "
                         "update is UNKNOWN")
    now_ms = pl.get("now") if isinstance(pl.get("now"), (int, float)) else now_ms
    now_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
    say = str(pl.get("say") or "no sentence recorded")[:220]
    rec = pl.get("lockCleared") if isinstance(pl.get("lockCleared"), dict) else None
    receipt = (" · last lock receipt: %s" % str(rec.get("say") or "")[:160]) if rec else ""
    if pl.get("on") is False or pl.get("outcome") == "off":
        return OK, "auto-pull is deliberately OFF on this machine: %s" % say
    oc = pl.get("outcome")
    if pl.get("checked") is None or oc is None:
        return UNKNOWN, ("nobody has tried to pull on this console yet, so whether this checkout can "
                         "update is UNKNOWN — not a clean bill")
    # ⚠⚠ #64 follow-up — AN UPDATE CUT OFF MID-CHECKOUT IS NOT A STAND-DOWN. A SIGKILLed fast-forward
    # leaves a 0-byte index.lock and a half-written tree; the lane used to call that tree 'dirty' and
    # this row graded it OK "on purpose", while the checkout could never update again. No bar: it does
    # not heal by itself, so the first sighting is the finding.
    if oc == "interrupted":
        return MISSING, ("an automatic update was INTERRUPTED mid-checkout, so this checkout cannot "
                         "update itself until a person looks: %s" % say)
    if oc == "dirty":
        return OK, "the pull lane is standing down ON PURPOSE: %s%s" % (say, receipt)
    if oc in ("pulled", "level"):
        _ago = ""
        if isinstance(pl.get("lastTs"), (int, float)):
            _ago = ", %.0f min ago" % max(0.0, (now_ms - pl["lastTs"]) / 60000.0)
        return OK, "the last automatic pull worked (%s%s)%s" % (say, _ago, receipt)
    if oc == "failed":
        since = pl.get("failSince")
        if not isinstance(since, (int, float)):
            return UNKNOWN, ("the last pull failed and the lane did not record since when, so how long "
                             "this checkout has been stuck is UNKNOWN: %s" % say)
        bar = pl.get("failBarS")
        bar = float(bar) if isinstance(bar, (int, float)) and bar > 0 else float(_PULL_FAIL_BAR_FALLBACK_S)
        fail_s = max(0.0, (now_ms - since) / 1000.0)
        n = int(pl.get("failures") or 0)
        when = time.strftime("%Y-%m-%d %H:%M", time.localtime(since / 1000.0))
        if fail_s > bar:
            return MISSING, ("automatic pulls have FAILED for %.1fh (since %s, %d attempt(s)), so this "
                             "checkout cannot update itself and every version shipped passes it by. "
                             "Reason: %s%s" % (fail_s / 3600.0, when, n, say, receipt))
        return UNKNOWN, ("the last %d pull attempt(s) failed, for %.0f min so far (since %s) — under "
                         "the %.0f min bar, so not yet a finding: %s"
                         % (n, fail_s / 60.0, when, bar / 60.0, say))
    return UNKNOWN, "the pull lane reported %r, which this row cannot grade: %s" % (oc, say)


def _check_this_checkout_can_update():
    """#64 — CAN THIS CHECKOUT STILL UPDATE ITSELF, OR HAVE ITS PULLS BEEN FAILING?

    ⚠ MEASURED 2026-09-29 on his ALT: a 0-byte .git/index.lock from 14:09 the day before, no git
    running, and every automatic pull since failing "Unable to create ... index.lock: File exists" —
    11 hours on v3521. The pull lane RECORDED it in _PULL.say and NO row read it. 'this machine keeps
    itself current' asks git how far behind HEAD is; it cannot say WHY the pulls stopped landing, and
    that is the half he needs. [[the-unjoined-end]] [[heart-first]]

    ⚠⚠ IT ASKS THE CONSOLE OVER THE WIRE, NOT `import control_app`. The console runs as `__main__`,
    so an import gives this process a SECOND copy of the module whose _PULL reads "nobody has looked
    yet" forever — measured, the imported copy is a different object. The same rule as
    'the running build is behind the disk'. The lane is published on /api/status as `pullLane`.
    """
    st = _get("/api/status")
    if not isinstance(st, dict):
        return UNKNOWN, ("the console did not answer /api/status, so whether this checkout can update "
                         "is UNKNOWN")
    if _PULL_LANE_KEY not in st:
        return UNKNOWN, ("this console does not publish its pull lane (it predates #64), so whether "
                         "its pulls are failing is UNKNOWN — restart it onto the current build")
    return pull_lane_verdict(st.get(_PULL_LANE_KEY))


def _check_his_window_has_a_keyboard_door():
    """v3402 — IS THE W SHORTCUT ACTUALLY ON THE WIRE?

    ⚠ A KEY IS INVISIBLE, AND THAT ASYMMETRY IS THE WHOLE REASON THIS ROW EXISTS. A button that
    disappears is noticed the next time he looks for it. A keyboard shortcut that disappears is
    noticed by NOBODY: he presses W, nothing happens, and he is back to being trapped in
    fullscreen — which is the complaint that started this. His words: "it opens and it like traps
    you in".

    ⚠ It reads THE BYTES ON THE WIRE, not the file. Its gate already scans the source; a console
    is a reading of its source taken at import and serves what it holds, so a corrected file and
    a console still serving the old page look identical from the tree. [[stale-reading]]
    """
    import urllib.request as _ur
    try:
        with _ur.urlopen(CONSOLE + "/", timeout=8) as r:
            page = r.read().decode("utf-8", "replace")
    except Exception as e:
        return UNKNOWN, ("the console did not serve its own page (%s), so whether W still toggles "
                         "his window is UNKNOWN, not clean" % type(e).__name__)
    if len(page) < 50000:
        return UNKNOWN, ("the console served only %d bytes, which is not the console page, so "
                         "nothing was measured" % len(page))
    if "k.toLowerCase() !== 'w'" not in page:
        return MISSING, ("the console is serving a page with NO W shortcut, so the only way out of "
                         "fullscreen is a button he has already reported being unable to find")
    _gone = [n for n in ("ev.ctrlKey || ev.metaKey || ev.altKey", "'TEXTAREA'", "ev.isComposing")
             if n not in page]
    if _gone:
        return MISSING, ("W is served WITHOUT its guard(s): %s. A bare letter key that does not "
                         "exempt modifiers eats Cmd+W (close window), and one that does not yield "
                         "to focus steals a keystroke from whatever he is typing into"
                         % ", ".join(_gone))
    return OK, ("W is on the wire and carries both guards, so he has a keyboard door out of "
                "fullscreen, measured across the %d bytes served" % len(page))


def _check_his_window_can_be_measured():
    """v3398 — WHEN HE PRESSES THE WINDOW BUTTON, CAN ANYONE TELL WHETHER IT WORKED?

    v3271 shipped the minimise / fullscreen controls and said so honestly: "pywebview exposes no
    reliable post-hoc read of the frame state", so the route reported WHAT IT CALLED and could
    not say whether the window obeyed. v3398 measured that claim and it was too pessimistic —
    `Window.width` / `Window.height` call `gui.get_size()` live — so the route now reports the
    frame before and after.

    ⚠ THIS ROW EXISTS BECAUSE A MEASUREMENT CAN GO QUIETLY DECORATIVE. If the frame stops being
    readable, every answer keeps its `ok: true` and simply loses the numbers, which reads exactly
    like a working control. Asking `frame` — a READ, never an action — is the only way to notice.

    ⚠ It must never act on his window. The action it sends is `frame` for that reason.
    """
    r = _post("/api/window", {"do": "frame"}, timeout=10)
    if not isinstance(r, dict):
        return UNKNOWN, ("the console did not answer /api/window, so whether his window can be "
                         "measured is UNKNOWN, not clean")
    if not r.get("ok"):
        why = str(r.get("why") or "")
        if "no native window" in why:
            return UNMEASURED, ("this console has no native window (headless or --no-open), so "
                                "there is no frame to measure — not applicable, not a fault")
        # ⚠ A CONSOLE OLDER THAN THIS CHECK IS NOT A BROKEN ONE. A running console is a reading
        # of its source taken at import, so one started before v3398 answers "not a window
        # action" — correctly, about code it has never seen. Reporting that as MISSING shows him
        # a red he cannot interpret and did not cause. [[stale-reading]] [[unknown-stays-unknown]]
        if "not a window action" in why:
            return UNKNOWN, ("this console started before v3398 and does not know the read-only "
                             "frame request, so its window cannot be measured yet — relaunch it "
                             "to pick up the new code. That is version skew, not a fault")
        return MISSING, ("the console refused a read-only frame request: %s" % why[:120])
    if not r.get("measured"):
        return MISSING, ("his window is open but its frame could not be read, so the window "
                         "buttons report ok without anyone being able to tell whether the "
                         "window obeyed — the measurement v3398 added is decorative here")
    # ⚠⚠ THE FRAME WAS MEASURED AND THEN THROWN AWAY. v3398 read `from` and returned an EMPTY
    # why, so the one row whose entire job is proving the measurement is still alive said nothing
    # about it — and `fr` sat assigned and unused, which is the same defect in miniature. A
    # verdict with no why is a lamp; the size IS the evidence that the read worked, so it belongs
    # in the row. MEASURED 2026-09-20: this failed the eagle-eye contract
    # (test_it_runs_and_every_row_is_a_named_state) the first time the suite ran far enough.
    # ⚠ `from` is a 2-tuple (w, h) — _win_frame returns (int(win.width), int(win.height)). It is
    # NOT a 4-element rect, and slicing it as one would print a confident wrong number.
    fr = r.get("from") or []
    try:
        _w, _h = int(fr[0]), int(fr[1])
    except Exception:
        _w = _h = None
    if _w is None:
        return OK, ("his window answered a read-only frame request and said the frame could be "
                    "measured, but named no size — the control is live and the numbers are "
                    "UNKNOWN, which is not the same as clean")
    return OK, ("his window answered a read-only frame request and reported %dx%d, so a window "
                "button's claim can still be checked against the frame it actually produced"
                % (_w, _h))


#: REG-1640 — the bound on the sweep harness child (one console-module import + one stubbed door
#: call). A child that has not answered by then is UNKNOWN, never a pass, and it is killed.
REACH_PROBE_S = 30


def _check_an_attack_can_still_reach_the_door_it_scores():
    """v3406 — CAN THE SWEEP HARNESS STILL REACH THE DOOR IT CLAIMS TO HAVE PROVEN?

    `chronicle_sweep_start` asks `self_arming.may("vault.sweep_start")` BEFORE it reads the lane
    list. That lock FAILS CLOSED on a stale heart census — its state for the whole of any session
    that has touched a gate file — so an attack aimed at a guard BELOW the lock gets back a
    perfectly good ok:False that has nothing to do with the guard.

    MEASURED 2026-09-22 in a sandbox: reverting the door's own lane guard left sweep_wilson GREEN
    at exit 0, with lanesnone/lanesraise/lanesstr/lanesdict all still reading PROVEN. Four claims
    were scoring a guard they could not see, and banking attacks=1 each into the very lock that
    was answering them.

    ⚠ ONE door call, with the worker stubbed by `_guarded`, so this costs a heart tick nothing and
    spends no paid read. It asks the question the harness cannot ask about itself: not "did the
    guard refuse" but "did the attack ARRIVE".

    ⚠ SHUT IS NOT BROKEN. A closed lock is the system working; the row says UNKNOWN and names what
    re-opens it, because a heart row that reds on a correct refusal is one someone silences.
    [[zero-needs-a-denominator]] [[unknown-stays-unknown]] [[gate-blind-to-unexercised-input]]

    ⚠⚠ REG-1640 (2026-10-01) — THE ATTACK RUNS IN A CHILD, NEVER IN HIS CONSOLE. This row called
    `_refused_quiet` right here, and the eagle runs every row INSIDE the console process. `_guarded`
    swaps `threading.Thread` for the whole process while the door is called, so any thread the
    console started in that window got a stand-in that never runs — the vault lamp's refresh set its
    one-at-a-time flag, never started, never cleared it, and his Mac's vault lamp froze until a
    restart. A doctor that breaks what it watches is worse than none. The child is bounded, and the
    scratch dir is made and removed HERE so a child killed at its bound leaves nothing behind.
    [[the-cure-that-kills-the-patient]]
    """
    import shutil as _sh
    import tempfile
    try:
        import sweep_wilson as _sw
    except Exception as e:
        return UNKNOWN, ("the sweep harness would not import (%s), so whether its attacks reach "
                         "the door is UNKNOWN, not fine" % type(e).__name__)
    for _n in ("_lock_answered", "_tally", "_refused_quiet"):
        if not hasattr(_sw, _n):
            return MISSING, ("sweep_wilson has no %s, so a refusal issued by the LOCK is counted as a "
                          "refusal by the DOOR again — the v3406 defect, restored" % _n)
    if not hasattr(_sw, "reach_probe"):
        return UNKNOWN, ("sweep_wilson has no child-side probe, so asking would mean running its thread "
                         "swap inside this console — not asked, and UNKNOWN is what that is")
    # 2026-09-26 — the throwaway history dir was never removed: 853 heartlane_* in his temp dir, 196 in a day
    d = tempfile.mkdtemp(prefix="heartlane_")
    try:
        p = subprocess.run([sys.executable, os.path.join(HERE, "sweep_wilson.py"), "--reach-probe", d],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           close_fds=False, timeout=REACH_PROBE_S)   # no cwd: spawn, never fork (Quartz law)
    except subprocess.TimeoutExpired:
        return UNKNOWN, ("the sweep harness child did not answer within %d s, so whether its attacks "
                         "reach the door is UNKNOWN, not fine" % REACH_PROBE_S)
    except Exception as e:
        return UNKNOWN, ("the sweep harness child would not start (%s), so whether its attacks reach "
                         "the door is UNKNOWN, not fine" % type(e).__name__)
    finally:
        _sh.rmtree(d, ignore_errors=True)
    ans = None
    for _line in reversed((p.stdout or "").splitlines()):
        try:
            ans = json.loads(_line)
        except ValueError:
            continue
        if isinstance(ans, dict):
            break
        ans = None
    if not isinstance(ans, dict):
        return UNKNOWN, ("the sweep harness child answered nothing readable (exit %s), so whether its "
                         "attacks reach the door is UNKNOWN, not fine" % p.returncode)
    if "unimportable" in ans:
        return UNKNOWN, ("the console module would not import in the harness child (%s), so whether its "
                         "attacks reach the door is UNKNOWN, not fine" % ans["unimportable"])
    if "raised" in ans:
        return MISSING, ("driving one lane attack raised %s, so the harness cannot answer for itself"
                      % ans["raised"])
    if "reach" not in ans:
        return UNKNOWN, ("the sweep harness child refused the question (%s), so whether its attacks "
                         "reach the door is UNKNOWN, not fine" % str(ans)[:80])
    verdict = ans["reach"]
    if verdict is None:
        return UNKNOWN, ("the sweep harness cannot currently REACH the door it scores — "
                         "vault.sweep_start answers first, so its four lane claims are UNPROVEN, "
                         "not passed. That lock fails closed on a stale heart census; "
                         "`python3 tv/heart2.py --prove` is what lets those attacks arrive")
    if verdict is True:
        return OK, ("the lane attack REACHED the door and the door refused it, so lanesnone and "
                    "its three siblings are scoring the guard they name")
    return MISSING, ("the lane attack reached the door and the door ACCEPTED an unreadable lane "
                  "list — a paid sweep would start with nothing to read with")


def _check_no_git_child_can_steal_his_screen():
    """v3407 — CAN A GIT SPAWN STILL POP A CONSOLE OVER THE GAME HE IS PLAYING?

    MEASURED on the Windows box 2026-09-21: `git.exe` windows stealing focus 2-3 in a row, every
    couple of minutes, while TV DIABLO sat idle. Parent was `pythonw control_app.py --open`. Git
    for Windows' PATH git is a 46 KB CUI WRAPPER; `pythonw` owns no console, so a CUI child
    ALLOCATES one — a real terminal on top of D2R.

    ⚠ ONE OF THE TWO BURSTS WAS MINE. v3404 put `_pull_once()` in the drift beat at 300 s beside
    the 120 s fleet cache — exactly the cadence he reported. A fix that keeps a machine current
    must not cost him the window he is playing in.

    ⚠ REACH IS STATED, NOT ASSUMED. The console-allocation half is Windows-only, so on a Mac this
    row can never go red for it and must not imply otherwise — it grades the JOIN (every git argv
    goes through the one door) on every platform, and says plainly that the rest is UNEXERCISED
    here. A green that quietly means "not applicable" is the green that lies.
    [[gate-blind-to-unexercised-input]] [[zero-needs-a-denominator]]
    """
    import re as _re
    p = os.path.join(HERE, "control_app.py")
    try:
        with open(p, encoding="utf-8") as fh:
            raw = fh.read()
    except Exception as e:
        return UNKNOWN, ("control_app.py could not be read (%s), so whether a git child can own a "
                         "console is UNKNOWN, not fine" % type(e).__name__)
    code = "\n".join(l.split("#", 1)[0] for l in raw.split("\n"))
    if "def _git_run(" not in code:
        return MISSING, ("_git_run is gone, so every git spawn is back to whatever flags its own call "
                      "site remembered — on Windows that pops a console over his game")
    loose = _re.findall(r'(?:subprocess\.run|subprocess\.Popen|subprocess\.check_output)\(\s*\n?\s*\[\s*"git"',
                        code)
    total = len(_re.findall(r'\(\s*\n?\s*\[\s*"git"', code))
    if loose:
        return MISSING, ("%d of %d git argv site(s) still spawn outside _git_run, so on Windows a CUI "
                      "child allocates its own console and alt-tabs him off the game"
                      % (len(loose), total))
    if not sys.platform.startswith("win"):
        return OK, ("all %d git argv site(s) go through the one door — but the console-allocation "
                    "fault is Windows-only and is NOT EXERCISED on this machine, so this row "
                    "grades the join here and the behaviour only there" % total)
    if not os.path.isfile(r"C:\Program Files\Git\mingw64\bin\git.exe"):
        return MISSING, ("all %d git argv site(s) go through _git_run, but mingw64 git is not at "
                         "the expected path, so the redirect silently falls back to the PATH "
                         "wrapper — the 46 KB CUI stub that spawns the real git without the flag"
                         % total)
    return OK, ("all %d git argv site(s) go through _git_run and mingw64 git is present, so no git "
                "child allocates a console on this machine" % total)


def _check_this_machine_can_get_a_second_opinion():
    """v3408 — CAN *THIS* PC REACH AN EYE AT ALL, AND DOES THAT EYE STAND OUTSIDE THE REPO?

    His architecture ruling is that every console answers for ITS OWN machine, so "we have a second
    eye" is not a fact about the fleet — it is a fact about one PC. His Mac has a signed-in Grok
    CLI; a freshly-installed box has not, and that machine's looks are EMPTY SEATS whatever the
    ledger's totals say.

    ⚠ NO NETWORK, NO SPAWN. This runs on the eagle tick, so it asks only what can be answered from
    disk: is there a binary where the eye is configured, and is its working directory outside this
    checkout. Whether the seat is signed in is a different question and is answered by an actual
    look, never guessed here.

    ⚠ AN API KEY IS NOT A SEAT. A metered endpoint answers "out of credits" and blocks a ship while
    proving nothing — measured 2026-09-22, mid-ship. [[feedback-silence-is-not-evidence]]
    """
    try:
        import second_eye_run as _eye
    except Exception as e:
        return UNKNOWN, ("the second-eye lane would not import (%s), so whether this machine can "
                         "get a cross-family look is UNKNOWN, not fine" % type(e).__name__)
    cli = getattr(_eye, "EYE_CLI", "") or ""
    cwd = os.path.abspath(getattr(_eye, "EYE_CWD", "") or "")
    for host in ("api.x.ai", "api.openai.com", "api.anthropic.com"):
        if host in cli:
            return MISSING, ("the eye on this machine is a METERED API (%s), not a subscription "
                             "CLI — it can answer 'out of credits' and block a ship while proving "
                             "nothing" % host)
    if not cli:
        return MISSING, ("no eye is configured on this machine, so every version ships with an "
                         "EMPTY SEAT rather than a cross-family look")
    if not os.path.exists(cli):
        return MISSING, ("the eye is configured at %s and there is no binary there, so this "
                         "machine cannot get a second opinion — set THIRD_EYE_CLI or install it"
                         % cli)
    if not cwd:
        return MISSING, ("the eye has no working directory of its own, so it inherits whatever "
                         "directory the caller stood in — which can be this repo")
    if cwd == os.path.abspath(ROOT) or cwd.startswith(os.path.abspath(ROOT) + os.sep):
        return MISSING, ("the eye runs INSIDE this checkout (%s), and a CLI eye is an AGENT with "
                         "tools — it can write to the tree it is grading" % cwd)
    return OK, ("this machine has an eye at %s, standing outside the repo, with a %.0fs bound "
                "— whether that seat is SIGNED IN is answered by a real look, never assumed here"
                % (cli, float(getattr(_eye, "EYE_TIMEOUT_S", 0) or 0)))


#: #227 — control_app._ensure_pillow_at_boot's attempt on THIS console ({ts, tried, ok, why}); None = never tried
PILLOW_BOOT = None
#: REG-1719 — control_app._ensure_numpy_at_boot's attempt on THIS console, the same shape; None = never tried
NUMPY_BOOT = None


#: #54 — a sealed reel the equipped ledger has not filed within this long of its seal means the nudge
#: at seal did not run; the nudge is synchronous inside after_session_ended, so ten minutes is not jitter.
_EQUIPPED_OWED_GRACE_MS = 10 * 60 * 1000


def _check_the_equipped_ledger_files_every_sealed_reel(now_ms=None):
    """#54 — WHAT HE WEARS, PER CHARACTER, IS FILED AT EVERY SEAL — and this asks whether it still is.

    Reads equipped_ledger.contract() over the console's own journal ring and store: `owed` is the
    sealed reels not yet in the ledger. A lane that runs at seal and owes a reel sealed more than
    _EQUIPPED_OWED_GRACE_MS ago has stopped. UNKNOWN when the journal or the store cannot be read —
    an empty ledger with no journal is not a clean one. [[heart-first]] [[zero-needs-a-denominator]]

    ⚠ It says out loud that `characters` is empty BY DESIGN until READ_PROMPT asks for the login
    name (REG-1522): an empty ledger is expected today, and a row that read it as a fault would be
    furniture within the week.
    """
    try:
        import equipped_ledger as _el
    except Exception as e:
        return UNKNOWN, ("equipped_ledger will not import (%s), so whether his gear is being filed is "
                         "UNKNOWN" % type(e).__name__)
    try:
        import control_app as _ca
        journals, hist = _ca._journal_ring(), _ca.HIST_DIR
    except Exception as e:
        return UNKNOWN, ("the console's journal ring could not be resolved (%s), so what the equipped "
                         "ledger owes is UNKNOWN" % type(e).__name__)
    try:
        c = _el.contract(journals, now_ms=now_ms, hist_dir=hist)
    except Exception as e:
        return UNKNOWN, "the equipped ledger's contract raised %s — UNKNOWN, not idle" % type(e).__name__
    lane = "lane: on=%s worked=%s lastTs=%s owed=%s" % (c.get("on"), c.get("worked"), c.get("lastTs"), c.get("owed"))
    if c.get("owedUndated"):
        lane += " (%d owed reel(s) carry no seal time)" % c["owedUndated"]
    if c.get("owed") is None:
        return UNKNOWN, "%s — %s" % (str(c.get("say") or "")[:160], lane)
    now = float(now_ms if now_ms is not None else time.time() * 1000.0)
    # #103 step B — a reel that waits for the character-select learner is the printer's order, not a stopped nudge:
    # it is late only past the wait's own bound (CS_WAIT_MS), and said by name either way.
    _waiting = set(c.get("waitingOnCharSelect") or [])
    if _waiting:
        lane += " · %d owed reel(s) wait for the character-select learner" % len(_waiting)
    if c["owed"] > len(_waiting):
        # REG-1559 — THE OLDEST OWED SEAL DECIDES. The first cut read the NEWEST seal of ALL reels, so a
        # lane that failed at every seal read OK for as long as reels kept sealing: each fresh seal hid
        # the hour-old one beside it. Driven: two owed reels, 61 min and 1 min old -> MISSING.
        oldest = c.get("oldestNotWaitingSealTs") if _waiting else c.get("oldestOwedSealTs")
        if not isinstance(oldest, (int, float)):
            return UNKNOWN, ("%d sealed reel(s) are owed and none of them carries a readable seal time, so "
                             "whether the nudge is late is UNKNOWN — not idle. %s" % (c["owed"], lane))
        if (now - float(oldest)) > _EQUIPPED_OWED_GRACE_MS:
            return MISSING, ("%d sealed reel(s) are not in the equipped ledger and the oldest of them sealed "
                             "%.0f min ago — the nudge at seal (after_session_ended -> _equipped_ledger_nudge) "
                             "did not file it; `python3 tv/equipped_ledger.py --ingest <journal> <hist>` files "
                             "them. %s" % (c["owed"], (now - float(oldest)) / 60000.0, lane))
    # #103 step B (REG-1601): the character a session entered with now comes from the character-select learner, so an
    # empty book says where the names will come from - not that nothing could ever fill it
    tail = ("" if c.get("characters") else
            " · no character on record yet: they come from the character-select learner once a session's highlighted "
            "row is read (REG-1601)")
    return OK, "%s%s · %s" % (str(c.get("say") or "")[:160], tail, lane)


def _check_this_machines_reader_can_read():
    """#105 (REG-1604) — CAN THIS PC'S READER READ? MEASURED 2026-09-30 on his ALT: its Claude CLI was signed out
    ("Failed to authenticate: OAuth session expired and could not be refreshed"), every frame it filmed for hours was
    read as nothing, and no surface said so - the log line carried no reason and every doctor row read fine.

    One measure, control_app._reader_health (the lamps under the corner chip ask the same one): the newest Claude read
    in the last 2 h decides. MISSING when it failed - with the reader's own words, and the sign-in step when the words
    are a sign-in failure; OK when it returned; UNKNOWN when nothing was read to judge (not reading is not "fine").
    Grok's lamp is said beside it. [[heart-first]] [[unknown-stays-unknown]]"""
    try:
        import control_app as _ca
        h = _ca._reader_health()
    except Exception as e:
        return UNKNOWN, ("the reader's health could not be measured (%s), so whether this PC can read is UNKNOWN - "
                         "not fine" % type(e).__name__)
    c = (h or {}).get("claude") or {}
    g = (h or {}).get("grok") or {}
    tail = " · Grok: %s" % (g.get("why") or g.get("state") or "UNKNOWN")
    if c.get("state") == "off":
        return MISSING, "%s (%s failed, %s returned in 2 h)%s" % (c.get("why"), c.get("failed"), c.get("ok"), tail)
    if c.get("state") == "on":
        return OK, "%s%s" % (c.get("why"), tail)
    return UNKNOWN, "%s%s" % (c.get("why") or "no Claude read to judge on this PC", tail)


def _check_this_machine_can_cross_check_an_inventory():
    """REG-1719 — CAN THIS MACHINE MEASURE AN INVENTORY'S GRID? (the vault's grid measure needs numpy)

    MEASURED 2026-10-02 over SSH: the ALT (Python 3.12.10) has no numpy - the Windows installer never listed it - so
    every lattice answered "unreadable: No module named 'numpy'" and the vault's pixel cross-check had never run on a
    Windows PC, silently. The console now installs it at boot like Pillow; this row says whether that worked, here."""
    try:
        import numpy as _np
        _np.median(_np.asarray([[1.0, 2.0], [3.0, 4.0]]), axis=0)
    except Exception as e:
        b = NUMPY_BOOT
        if isinstance(b, dict) and b.get("tried"):
            did = "this console tried to install it at boot and %s" % (b.get("why") or "said nothing")
        elif isinstance(b, dict):
            did = "this console's boot check ran but did not try to install (%s)" % (b.get("why") or "no reason")
        else:
            did = "this console has not tried to install it (only Windows consoles do, at boot)"
        return MISSING, ("numpy will not import on this machine (%s), so no inventory grid can be measured and the "
                         "vault's pixel cross-check never runs - %s; by hand: %s -m pip install --user numpy"
                         % (type(e).__name__, did, sys.executable))
    return OK, "numpy imports and measures, so the vault can cross-check an inventory on this machine"


def _check_this_machine_can_decode_a_frame():
    """#227 — CAN THIS MACHINE READ THE FRAMES IT FILMS?

    MEASURED 2026-09-24 over SSH: his Windows ALT ran Python 3.12.10 with pywebview and NO Pillow.
    Every frame reader in the chain (tv_diablo, chronicle_calibrate) imports PIL, so every frame that
    box captured was unreadable - and no row anywhere said so, because each reader swallows the
    ImportError where it happens. The Windows launcher installs Pillow on a double-click and the console
    itself does at boot (REG-1260: a self-updated console never re-runs the launcher); this row is what says
    whether that worked, on THIS machine, where the answer lives. [[heart-first]]

    It round-trips a 4x3 BMP in memory (the format the Windows capture writes) and checks a pixel,
    so "imports" is not mistaken for "decodes". No disk, no network, milliseconds."""
    try:
        from PIL import Image
    except Exception as e:
        # REG-1260 — this used to promise "the Windows launcher installs it on its next start": a
        # self-updated console never runs the launcher, so the promise never came true. Say what
        # THIS console's own boot attempt did.
        b = PILLOW_BOOT
        if isinstance(b, dict) and b.get("tried"):
            did = "this console tried to install it at boot and %s" % (b.get("why") or "said nothing")
        elif isinstance(b, dict):
            did = "this console's boot check ran but did not try to install (%s)" % (b.get("why") or "no reason")
        else:
            did = "this console has not tried to install it (only Windows consoles do, at boot)"
        return MISSING, ("Pillow will not import on this machine (%s), so no frame this console films "
                         "can be read - %s; by hand: %s -m pip install --user Pillow"
                         % (type(e).__name__, did, sys.executable))
    try:
        import io as _io
        buf = _io.BytesIO()
        Image.new("RGB", (4, 3), (200, 40, 10)).save(buf, format="BMP")
        buf.seek(0)
        im = Image.open(buf)
        im.load()
        size, px = im.size, im.convert("RGB").getpixel((1, 1))
    except Exception as e:
        return MISSING, ("Pillow imports but could not decode a 4x3 BMP (%s: %s), so a captured frame "
                         "cannot be read either" % (type(e).__name__, str(e)[:80]))
    if size != (4, 3) or tuple(px) != (200, 40, 10):
        return MISSING, ("Pillow decoded a 4x3 BMP as %r with pixel %r - the pixels do not survive a "
                         "round trip" % (size, px))
    try:
        import PIL as _pil
        ver = getattr(_pil, "__version__", "UNKNOWN")
    except Exception:
        ver = "UNKNOWN"
    return OK, ("this machine decodes a frame: Pillow %s round-tripped a BMP (the format the Windows "
                "capture writes) pixel for pixel" % ver)


def _check_the_door_and_the_writers_name_the_same_tree():
    """v3410 — DOES THE TREE THE DOOR ESTABLISHES EQUAL THE TREE THE WRITERS ACTUALLY USE?

    Two INDEPENDENT sides, which is what makes this a corroborator rather than one number wearing
    two names: `machine_tree.footage_hist()/footage_frames()` is what the PLANNERS ask
    (frame_authority, reel_retention), and `tv_diablo.HIST_DIR/FRAMES` is what the WRITERS
    actually open. Nothing had ever compared them.

    MEASURED 2026-09-22 across all four env shapes: they agree in three. The one that diverges is
    TV_FRAMES_DIR set with TV_HIST unset — exactly `replay.py:217` — where the door used to skip
    the hist root entirely while tv_diablo still computed join(FRAMES, "hist"). v3410 makes the
    door DERIVE that root instead of skipping it, and this row is what would notice if the two
    sides ever part again.

    ⚠ DIVERGENCE IS NOT AUTOMATICALLY A FAULT. A harness that deliberately isolates one root is a
    legitimate state, so a mismatch is reported with BOTH paths named and left for a human, never
    silently repaired — repairing it here would be this module's risk 1 arriving as a doctor.
    [[heart-first]] §1 (two genuinely independent sides) [[unknown-stays-unknown]]
    """
    try:
        import machine_tree as _mt
        import tv_diablo as _td
    except Exception as e:
        return UNKNOWN, ("the footage door or its writer would not import (%s), so whether they "
                         "name the same tree is UNKNOWN, not fine" % type(e).__name__)
    pairs = []
    try:
        pairs.append(("frames", _mt.footage_frames(), getattr(_td, "FRAMES", None)))
        pairs.append(("frames/hist", _mt.footage_hist(), getattr(_td, "HIST_DIR", None)))
    except Exception as e:
        return UNKNOWN, ("could not ask both sides for their path (%s) — UNKNOWN, never a "
                         "measured agreement" % type(e).__name__)
    bad = []
    for name, planner, writer in pairs:
        if not planner or not writer:
            return UNKNOWN, ("the %s root has no path on one side (planner=%r writer=%r), so "
                             "agreement cannot be measured" % (name, planner, writer))
        # ⚠ v3412 — realpath RAISES on a path with an embedded NUL (ValueError) and on a symlink
        # parent this process cannot search (OSError). v3410 left it outside the try, so either
        # aborted the whole check instead of reporting that agreement was NOT MEASURED. Named by
        # the cross-family review of v3410. A row that dies is not a row that answered UNKNOWN.
        try:
            same = os.path.realpath(planner) == os.path.realpath(writer)
        except Exception as e:
            return UNKNOWN, ("the %s root's path could not be resolved (%s), so whether the door "
                             "and the writers agree is UNKNOWN, not measured"
                             % (name, type(e).__name__))
        if not same:
            bad.append("%s: the planners read %s and the writers open %s"
                       % (name, planner, writer))
    if bad:
        return MISSING, ("the door and the writers name DIFFERENT trees, so what retention plans "
                         "is not what the film wrote — %s. If a harness set only one of "
                         "TV_HIST / TV_FRAMES_DIR that is expected; both paths are named here "
                         "rather than repaired, because provisioning the other half from inside "
                         "an isolated harness is how a test plants a tree in the live one"
                         % " · ".join(bad))
    return OK, ("the door and the writers name the same tree at both roots (%s), so retention "
                "plans exactly what the film wrote" % pairs[1][1])


def _check_the_resume_agrees_with_git_right_now():
    """v3413 — DOES THE FILE A RESUMING SESSION READS FIRST STILL MATCH WHAT GIT SAYS?

    A CORROBORATOR with two genuinely independent sides: the CLAIM rendered into
    RESUME_HERE.md's derived block, against what git answers now. Nothing had ever compared them.

    ⚠ WHY THIS ROW EXISTS AT ALL. v3413 fixed `_git()` handing a failed run back as "", which
    made that block render `working tree CLEAN` and `✅ Nothing is waiting to be pushed` on a git
    that could not answer — the opposite of the truth, on the one file that carries *"Nothing has
    shipped until origin/main equals HEAD"*. The gate pins the generator; this asks whether the
    FILE ON DISK currently agrees, which no gate can answer because the file is an artefact.

    ⚠ A DISAGREEMENT IS NOT AUTOMATICALLY A FAULT — the block is regenerated by a version bump,
    so between a commit and the next bump it is legitimately behind. The row reports WHAT differs
    and leaves it; it never rewrites his resume. [[heart-first]] §1 [[stale-reading]]

    ⚠ PERIODIC on purpose: it shells out to git twice, and the cheap subset is already measured
    at 14,168 ms against a 9,000 ms budget (#150).
    """
    p = os.path.join(ROOT, "RESUME_HERE.md")
    try:
        with open(p, encoding="utf-8") as fh:
            txt = fh.read()
    except Exception as e:
        return UNKNOWN, ("RESUME_HERE.md could not be read (%s), so whether it agrees with git "
                         "is UNKNOWN, not fine" % type(e).__name__)
    import re as _re
    m = _re.search(r"<!-- fp: head=(\S+) origin=(\S+) ver=(\S+) -->", txt)
    if not m:
        # ⚠⚠ v3474 (#164) — THE FINGERPRINT NOW CARRIES ONLY WHAT ITS WRITER CAN KNOW: `ver=`. HEAD
        # and origin cannot be known inside the commit that carries them, so the block no longer
        # states them — `resume_state.py --live` asks git at read time. The one claim left to check
        # is that ver matches the stamp on disk. The head/origin branch below stays for a resume
        # written by an older writer (another machine that has not pulled yet).
        mv = _re.search(r"<!-- fp: ver=(\S+) -->", txt)
        if mv:
            said = mv.group(1)
            try:
                with open(os.path.join(ROOT, "tv", "tv_diablo.py"), encoding="utf-8") as fh:
                    stamps = _re.findall(r'(?m)^VERSION\s*=\s*"(v[0-9.]+)"', fh.read())
            except Exception as e:
                return UNKNOWN, ("the version stamp could not be read (%s), so whether the resume "
                                 "names the right version is UNKNOWN" % type(e).__name__)
            if len(stamps) != 1:
                return UNKNOWN, ("tv_diablo.py carries %d VERSION line(s), so which version the "
                                 "resume should name is UNKNOWN" % len(stamps))
            if said != stamps[0]:
                return MISSING, ("RESUME_HERE.md names %s but the stamp on disk is %s — it was not "
                                 "regenerated after the bump: run python3 tv/resume_state.py"
                                 % (said, stamps[0]))
            return OK, ("the resume states only what it can know when written (ver=%s, which "
                        "matches the stamp on disk); HEAD, origin and what is unpushed are asked "
                        "live — python3 tv/resume_state.py --live — never written down" % said)
        return UNKNOWN, ("the derived block carries no fingerprint, so there is no claim to "
                         "check against git")
    said_head, said_origin = m.group(1), m.group(2)
    # ⚠⚠ v3416 — AN UNKNOWN FINGERPRINT IS NOT A BLANKET EXEMPTION, AND IT WAS ONE. This
    # returned OK right here, BEFORE the all-clear sentence was ever looked at, so a file whose
    # fingerprint git could not fill read fine forever no matter what the rest of it claimed —
    # honest about the fingerprint, silent about the sentence beside it. The COMPARISON is still
    # skipped below, because there is nothing to compare; the SENTENCE no longer is.
    # Found by the second eye at full reach. [[unknown-stays-unknown]]
    fp_unknown = (said_head == "UNKNOWN" or said_origin == "UNKNOWN")
    try:
        import git_quiet as _gq
        _h = _gq.run([_spawnable("git"), "-C", ROOT, "rev-parse", "--short", "HEAD"],
                     close_fds=False, capture_output=True, text=True, timeout=20)
        _o = _gq.run([_spawnable("git"), "-C", ROOT, "rev-parse", "--short", "origin/main"],
                     close_fds=False, capture_output=True, text=True, timeout=20)
        # ⚠⚠ v3416 — COUNT THE UNPUSHED COMMITS; THE HASHES WERE A PROXY AND THE PROXY WAS
        # WRONG. "Nothing is waiting to be pushed" is a claim about UNPUSHED COMMITS, and
        # derived() writes it whenever `origin/main..HEAD` is empty — which is ALSO true when
        # HEAD is strictly BEHIND origin/main. So `head != origin` called a perfectly correct
        # file a FALSE all-clear on every behind tree, and behind is the ordinary state here
        # the moment the Windows box or the other family pushes before this machine pulls.
        # Ask the question the sentence actually makes. [[feedback-verify-not-proxy]]
        _a = _gq.run([_spawnable("git"), "-C", ROOT, "rev-list", "--count", "origin/main..HEAD"],
                     close_fds=False, capture_output=True, text=True, timeout=20)
    except Exception as e:
        return UNKNOWN, ("git could not be asked (%s), so whether the resume agrees with it is "
                         "UNKNOWN" % type(e).__name__)
    if _h.returncode != 0 or _o.returncode != 0 or _a.returncode != 0:
        return UNKNOWN, ("git exited non-zero, so the comparison could not be made — UNKNOWN, "
                         "never an agreement")
    head, origin = (_h.stdout or "").strip(), (_o.stdout or "").strip()
    # ⚠ THE FALSE ALL-CLEAR IS THE ONE THAT MATTERS. A resume claiming nothing is unpushed while
    # HEAD is ahead of origin is the exact sentence v3413 exists to stop being written falsely.
    claims_clear = "Nothing is waiting to be pushed" in txt
    try:
        ahead = int((_a.stdout or "").strip())
    except Exception:
        return UNKNOWN, ("git answered %r when asked how many commits are unpushed, which is "
                         "not a count — so whether the all-clear is true is UNKNOWN, never "
                         "assumed" % ((_a.stdout or "").strip()[:30],))
    if claims_clear and ahead > 0:
        # ⚠ v3419 - AND SAY THAT THE THREE NUMBERS ARE THREE READS. `rev-parse HEAD`,
        # `rev-parse origin/main` and `rev-list --count` are separate processes; a commit landing
        # between them makes this sentence quote figures that were never simultaneously true. The
        # verdict still stands (the count is the claim being judged), but the reader is told the
        # three were not one snapshot rather than being left to assume they were. [[stale-reading]]
        return MISSING, ("RESUME_HERE.md says nothing is waiting to be pushed, but git counts "
                         "%d unpushed commit(s) (HEAD %s against origin/main %s, three separate "
                         "reads) — that is the false all-clear on the file a resuming session "
                         "reads first" % (ahead, head, origin))
    # ⚠⚠ v3419 - AN UNKNOWN FIELD EXEMPTS ITSELF, NOT THE WHOLE FINGERPRINT. v3416 moved
    # this below the all-clear check but still returned OK for the WHOLE row the moment EITHER
    # field read UNKNOWN - so a fingerprint of head=abc123 origin=UNKNOWN reported AGREEMENT even
    # when the concrete stored head disagreed with git outright. A field nobody could measure is
    # UNKNOWN; a field that WAS measured and differs is a difference, and one does not excuse the
    # other. [[unknown-stays-unknown]]
    _head_differs = (said_head != "UNKNOWN" and said_head != head)
    _origin_differs = (said_origin != "UNKNOWN" and said_origin != origin)
    if _head_differs or _origin_differs:
        return UNMEASURED, ("the resume was derived at head=%s origin=%s and git now reads "
                            "head=%s origin=%s — it is BEHIND, which is normal between a commit "
                            "and the next version bump, not a fault"
                            % (said_head, said_origin, head, origin))
    if fp_unknown:
        # ⚠ v3419 - AND THE REASON MUST NOT VOUCH FOR A SENTENCE THAT IS NOT THERE. This used
        # to say "so the sentence is true" on EVERY path, including a file carrying no all-clear
        # claim at all - a message asserting what it never checked. [[label-outlived-referent]]
        return OK, ("the resume says UNKNOWN for what git could not answer, which is the honest "
                    "reading — %s"
                    % (("its all-clear sentence was checked anyway: %d commit(s) are unpushed, so "
                        "that sentence is true" % ahead) if claims_clear
                       else ("it makes no all-clear claim to check, and git counts %d unpushed "
                             "commit(s)" % ahead)))
    return OK, ("the resume's fingerprint matches git exactly (head=%s origin=%s), so the file a "
                "resuming session reads first is telling it the truth" % (head, origin))

def _check_the_chip_can_say_nobody_looked():
    """v3414 - CAN THE HEART CHIP STILL TELL HIM NOBODY LOOKED?

    THE DOCTOR HALF of v3414. The gate drives `_heartChipPaint` and proves the two faces differ;
    this asks the question a gate cannot reach: on THIS console, right now, does the engine the
    chip reads actually hand it a census - and if not, WHICH LINK BROKE.

    The chip has exactly one scheduled read (`/api/heart`, deferred 4 s). Everything it can say
    comes from that payload, so when `heart_state()` answers without counts the chip is stuck
    reading `not taken` and nothing on his screen says why. That is the engine's fault, not the
    chip's, and this row is the only place the difference is visible.

    ⚠ THIS ROW CAN GO RED FOR A REAL REASON, which is the whole point of writing it: the census
    walks the source and can refuse. When it does, `heart_state` carries its own `why`, and that
    string is republished here rather than re-derived. [[heart-first]] §4 - a doctor names the
    broken link instead of saying it does not work.

    ⚠ PERIODIC on purpose. The census costs ~2.5 s cold (45 s memo), and the cheap subset is
    already measured at 14,168 ms against a 9,000 ms budget (#150). A supervision row that pays
    2.5 s on every eagle tick is the defect `poll-slower-than-its-interval` is carved over.
    """
    try:
        import control_app as _ca
    except Exception as e:
        return UNKNOWN, ("this process cannot import the console (%s), so whether the chip can be "
                         "fed is UNKNOWN, not fine" % type(e).__name__)
    fn = getattr(_ca, "heart_state", None)
    if not callable(fn):
        return MISSING, ("the console no longer exposes heart_state(), which is the chip's only "
                         "source - the chip will read 'not taken' forever and say nothing about why")
    try:
        d = fn()
    except Exception as e:
        return UNKNOWN, ("the census refused to derive (%s: %s), so the chip has nothing to paint "
                         "and this console cannot say whether that is new"
                         % (type(e).__name__, str(e)[:70]))
    if not isinstance(d, dict):
        return MISSING, ("the census answered %s, not a payload - the chip reads no counts from "
                         "that and falls back to 'not taken'" % type(d).__name__)
    if not d.get("ok"):
        return MISSING, ("the census answered NOT OK (%s) - his chip is showing 'not taken' and "
                         "this is the reason" % (str(d.get("why") or "no reason given")[:90]))
    c = d.get("counts")
    if not isinstance(c, dict) or not c:
        return MISSING, ("the census carries no counts, so the chip cannot tell a clean heart "
                         "from one nobody took - it will read 'not taken' while the console is "
                         "answering perfectly well")
    # ⚠⚠ v3417 - AN ABSENT KEY IS NOT A MEASURED ZERO, AND THIS ROW OF ALL ROWS PRINTED IT AS
    # ONE. `c.get("FLOWING") or 0` rendered a missing key, a null and a real zero identically, so
    # a census carrying only {"DARK": 2} reported as a full four-way count with three zeros in it.
    # That is the defect this row exists to watch, committed by the row itself.
    # [[unknown-stays-unknown]]
    def _n(k):
        v = c.get(k)
        return str(v) if isinstance(v, int) and not isinstance(v, bool) else "?"
    return OK, ("the chip can be fed: %s flowing, %s watched, %s dark, %s unknown (? = the census "
                "carried no such key, which is not a zero) - and a census that stopped answering "
                "would leave the chip on the last one it saw, never a clean face"
                % (_n("FLOWING"), _n("WATCHED"), _n("DARK"), _n("UNKNOWN")))


def _check_the_eye_audit_agrees_with_the_ship_gate():
    """v3415 - DO THE TWO SURFACES READ ONE LEDGER ROW THE SAME WAY?

    A TRUE CORROBORATOR: `audit()` classifies rows itself, and `owes_a_look()` goes through
    `looked_at()`. Two engines, one question - which is the [[heart-first]] 1 test, and the pair
    was never compared until a push was refused by one while the other called the row fine.

    MEASURED on v3413 before the fix: looked_at() 0, owes_a_look() True, audit() looks=1. The
    gate refused, and its own refusal message told the reader to run --audit, the single screen
    that disagreed with it.

    ⚠ ITS REACH IS BOUNDED AND SAID OUT LOUD. The full comparison costs 9,234 ms - more than the
    ENTIRE 9,000 ms cheap-subset budget (#150) - because owes_a_look walks the ledger per version
    across 1,083 of them. So it examines the newest 80 (686 ms measured) PLUS every version
    carrying a could-not-judge, wherever it sits in history, and the answer names both numbers. A
    row that quietly looked at a subset would be the defect this file keeps paying for.

    ⚠ ORDERED BY NUMBER, NEVER BY THE RENDERED STRING. audit() sorts by the version TEXT, where
    v999 sorts above v1000, so "the newest 80" taken off that order would be the wrong 80.
    [[stale-reading]] 3

    ⚠ PERIODIC: the answer can only change when an eye writes a row, which happens a few times a
    day at most. Hourly is honest; 686 ms on every eagle tick is not.
    """
    try:
        import second_eye_ledger as _sel
    except Exception as e:
        return UNKNOWN, ("this process cannot import the eye ledger (%s), so whether its two "
                         "surfaces agree is UNKNOWN, not fine" % type(e).__name__)
    try:
        rows = _sel.audit()
    except Exception as e:
        return UNKNOWN, ("the audit refused to build (%s: %s), so there is nothing to compare the "
                         "ship gate against" % (type(e).__name__, str(e)[:60]))
    if not rows:
        return UNKNOWN, ("the ledger is empty, so the two surfaces have nothing to disagree "
                         "about - that is silence, not agreement")
    NEWEST = 80
    try:
        ordered = sorted(rows, key=lambda s: _sel._vnum(s.get("version")))
    except Exception:
        ordered = list(rows)
    scope = list(ordered[-NEWEST:])
    seen = set(s.get("version") for s in scope)
    for s in ordered:
        if s.get("cannot") and s.get("version") not in seen:
            scope.append(s)
            seen.add(s.get("version"))
    bad = []
    for s in scope:
        v = s.get("version")
        try:
            gate_ok = not _sel.owes_a_look(v)
        except Exception as e:
            return UNKNOWN, ("the ship gate predicate refused on %s (%s), so agreement is UNKNOWN "
                             "rather than proven" % (v, type(e).__name__))
        if bool(s.get("looks")) != gate_ok:
            bad.append("%s (audit %s, gate %s)"
                       % (v, "OK" if s.get("looks") else "OWED", "OK" if gate_ok else "OWED"))
    cant = sum(1 for s in scope if s.get("cannot"))
    if bad:
        return MISSING, ("%d of %d version(s) examined are read ONE way by --audit and the other "
                         "by the ship gate - one row, two readings, and the gate sends him to the "
                         "audit to understand its own refusal: %s"
                         % (len(bad), len(scope), "; ".join(bad[:4])))
    return OK, ("the audit and the ship gate agree on all %d version(s) examined - the newest %d "
                "of %d, plus every one carrying a could-not-judge wherever it sits; %d such "
                "row(s) in scope, and both surfaces call every one a non-look"
                % (len(scope), min(NEWEST, len(ordered)), len(ordered), cant))


def _check_the_eye_cap_is_a_size_the_eye_has_finished():
    """v3418 - IS THE SHIPPED SECOND-EYE CAP A SIZE THE EYE HAS ACTUALLY FINISHED AT?

    THE DOCTOR HALF of v3418. The gate pins the LAW on a temp ledger; this asks the live
    question a gate cannot, because `tv/.second_eye.jsonl` is untracked and a case reading it
    would skip on a runner - and a skip reads as a pass.

    Konyo raised the cap 9,000 -> 26,000 on 2026-09-22. The number it replaced was justified by
    "24,000 chars timed out at 240s" - measured against an EYE_TIMEOUT_S that was later raised to
    1200, so the evidence had expired while the number stayed. This row exists so that can never
    happen quietly again in either direction: it compares the SHIPPED cap against the largest
    payload the eye has actually been seen to answer, on THIS machine, now.

    ⚠ AN EMPTY SEAT IS NOT A WITNESS, and `cap_is_witnessed` already refuses to count one. A
    payload that was sent and never answered is evidence the eye could NOT chew that size.

    ⚠ UNKNOWN IS A REAL ANSWER HERE. A machine whose ledger has no finished look cannot vouch for
    any cap, and saying so is the honest reading - not a fault, and never an OK.
    [[feedback-threshold-above-the-ceiling]] [[unknown-stays-unknown]]
    """
    try:
        import second_eye_ledger as _sel
        import second_eye_run as _ser
    except Exception as e:
        return UNKNOWN, ("this process cannot import the eye (%s), so whether its cap is "
                         "reachable is UNKNOWN, not fine" % type(e).__name__)
    cap = getattr(_ser, "MAX_FENCE_CHARS", None)
    if not isinstance(cap, int) or isinstance(cap, bool):
        return MISSING, ("the eye no longer exposes a numeric MAX_FENCE_CHARS (%r), so nothing "
                         "bounds what is sent and nothing can be checked against it" % (cap,))
    fn = getattr(_sel, "cap_is_witnessed", None)
    big_fn = getattr(_sel, "largest_finished_look", None)
    if not callable(fn) or not callable(big_fn):
        return MISSING, ("the ledger no longer answers whether a cap has been witnessed, so the "
                         "cap is back to being a number nobody measured")
    try:
        big = big_fn()
        ok = fn(cap)
    except Exception as e:
        return UNKNOWN, ("the ledger refused to answer (%s: %s), so whether the cap is reachable "
                         "is UNKNOWN" % (type(e).__name__, str(e)[:60]))
    if ok is None:
        return UNKNOWN, ("this machine has no FINISHED look on record, so it cannot vouch for a "
                         "cap of %d - that is silence, not agreement. An empty seat does not "
                         "count, on purpose." % cap)
    if ok is False:
        return MISSING, ("the shipped cap is %d but the largest payload this eye has ever "
                         "ANSWERED is %s - a threshold above the ceiling, which turns every look "
                         "into a non-look. Raise the evidence or lower the cap."
                         % (cap, big))
    return OK, ("the cap is %d and the eye has finished a look at %s, so the bound is inside "
                "witnessed territory - and an empty seat was never allowed to vouch for it"
                % (cap, big))


#: v3466 — the scratch walk's ceiling, named so a gate can drive the capped branch without
#: making 400,000 directories. Reaching it is a SAMPLE, and the row says so.
_SCRATCH_SCAN_CAP = 400000


def _check_nothing_we_made_is_still_on_his_disk_days_later():
    """v3422 - IS OUR SCRATCH BEING COLLECTED, OR JUST ACCUMULATING?

    THE CLASS BEHIND #170, WHICH WAS FILED AS ONE PREFIX AND IS NOT. Fixing `second_eye_run` took
    the eye's 115 directories off the machine; MEASURED THE SAME HOUR, TMPDIR held **110,447
    directories and 4.8 GB**, ours, over twenty days - `veto-` 2,580, `shape-` 1,984,
    `tvd-gates-` 1,945, `board_sweep_gate.` 1,564, and 89,181 bare `mkdtemp()` calls with no
    prefix at all to name their author. His free space was 12 GB against an 8 GB ON AIR floor,
    so this is not tidiness; a console that cannot record is the symptom waiting at the end of it.

    ⚠ THE LAW IS NOT A COUNT, AND THAT IS THE DESIGN DECISION WORTH READING. We mint roughly
    15,000 a day, so ANY ceiling on the population is either always red or never red - a threshold
    under the normal floor is an alarm nobody can act on, which is the same defect as one above
    the ceiling. [[feedback-threshold-above-the-ceiling]] The rate-independent question is whether
    anything ever COLLECTS them: nothing we make should still be here days later. macOS's own
    policy is three days, and these had been sitting for twenty, so the OS is not doing it either.

    ⚠ A COUNT WITH NO AGE WOULD ALSO HAVE READ FINE ON A FRESH MACHINE. The denominator is the
    total; the finding is the old tail. [[zero-needs-a-denominator]]

    ⚠⚠ AND IT COUNTS ONLY WHAT IT CAN ATTRIBUTE TO US, WHICH THE FIRST VERSION OF THIS ROW DID NOT.
    Written to count every old directory, it read `missing` with 130 survivors after the sweep and
    the sentence "they are made by us" — and all 130 were **macOS's own**: 69 `com.apple.*`, plus
    `talagent`, `studentd`, `gamed`, `mobiletimerd` and twelve more daemon containers, every one
    minted at boot 20 days ago and none of them litter. A row that can never go green is a row
    nobody reads within a week, and this one would have shipped permanently red while blaming us
    for Apple's directories. [[a-law-about-a-row-must-drive-the-row]] [[label-outlived-referent]]

    So the population is named POSITIVELY. `tmp` is Python's default `mkdtemp` prefix and no system
    daemon uses it — it alone covered 89,181 of the 110,447 found — and the rest are prefixes our
    own code passes. An unknown new prefix escapes this, which is stated rather than hidden, and is
    exactly what #171 fixes by making every call site name its author.
    """
    import tempfile as _tf
    horizon = 3 * 86400.0
    root = _tf.gettempdir()
    # ⚠ MEASURED PREFIXES, not guessed ones — these are what the 2026-09-23 scan actually found.
    MINE = ("tmp", "second_eye_", "veto-", "shape-", "tvd-", "board_sweep_gate.", "counterledger-",
            "statepath", "isorule-", "isolaw-", "atomicwrite-", "framelabel.", "g5_", "frameref",
            "diskrep_", "triage_", "heart2.", "TemporaryDirectory.",
            # 2026-09-26 — three more of ours were still minting daily and this row could not see them
            "heartlane_", "sweeplink_", "scarledger")
    now, total, old, oldest, capped = time.time(), 0, 0, 0.0, False
    try:
        with os.scandir(root) as it:
            for e in it:
                if not e.name.startswith(MINE):
                    continue          # somebody else's container; not ours to report on
                # ⚠ BOUNDED. This runs on a machine he is using; a scan with no ceiling is the
                # unbounded-search scar, and a partial answer with a stated reach beats a hang.
                if total >= _SCRATCH_SCAN_CAP:
                    capped = True
                    break
                try:
                    if not e.is_dir(follow_symlinks=False):
                        continue
                    age = now - e.stat(follow_symlinks=False).st_mtime
                except Exception:
                    continue
                total += 1
                if age > horizon:
                    old += 1
                    oldest = max(oldest, age)
    except Exception as e:
        return UNKNOWN, ("this machine's scratch directory could not be read (%s), so whether our "
                         "litter is being collected is UNKNOWN, not fine" % type(e).__name__)
    if not total:
        # ⚠ NOT "clean". Zero attributable directories on a machine that runs gates every day means
        # the prefix list has stopped matching what we make, which is the instrument failing.
        return UNKNOWN, ("no directory under the scratch root matched any prefix this repo is "
                         "known to create, so whether our litter is collected is UNKNOWN - on a "
                         "machine that runs gates daily that points at the prefix list, not the disk")
    if old:
        return MISSING, ("%d of %d scratch director(ies) WE made are older than 3 days - oldest "
                         "%.1f days. Nothing is collecting them; macOS's own policy is three days "
                         "and it is not keeping up either" % (old, total, oldest / 86400.0))
    if capped:
        # ⚠ v3466 — A SCAN THAT STOPPED IS A SAMPLE, NOT A VERDICT. The bound is right (an
        # unbounded walk on his machine is the 28-hour-search scar); calling the sample "being
        # collected" was not. Found by the eye on v3422. [[regression-guard]] §1
        return UNKNOWN, ("stopped counting at %d scratch director(ies) of ours - the scan is bounded "
                         "on purpose, none of those %d was older than 3 days, and the age of the "
                         "rest was never examined, so 'being collected' is NOT established. A "
                         "population this large is itself the #171 finding" % (total, total))
    return OK, ("0 of %d scratch director(ies) attributable to us are older than 3 days - what we "
                "make is being collected" % (total,))


def _spawnable(name):
    """Resolve a bare command to a path WITH A DIRNAME, so CPython can posix_spawn it. -> str

    ⚠ HALF THE FIX, AND THE INVISIBLE HALF. `Popen._execute_child` takes posix_spawn only when
    `os.path.dirname(executable)` is truthy AND close_fds is false; with a bare name it FORKS even
    though the call reads as fixed. MEASURED: `["ps", ...], close_fds=False` -> fork_exec x1.

    Falls back to the bare name when the command is not on this machine, so a missing tool still
    reaches its own FileNotFoundError handler instead of becoming a path that does not exist
    either. [[unknown-stays-unknown]]
    """
    import shutil as _sh
    try:
        return _sh.which(name) or name
    except Exception:
        return name


def _check_nothing_this_console_started_is_a_corpse_right_now():
    """v3421 - IS THERE A DEAD CHILD ON THIS MACHINE THAT NOBODY COLLECTED?

    THE DOCTOR HALF of v3421, and the ONLY half that could have found the original. The gate
    grades the SOURCE - it proves the closer reaps and that no timeout handler kills without
    reaping - and a gate can only ever pin the shapes somebody already thought of. This asks the
    live question: on THIS machine, at THIS moment, how many of our own children are <defunct>.

    ⚠ IT IS THE LIVE LOOK THAT SETTLED #166, NOT THE SOURCE. Four rounds of reading could not
    choose between three Popen sites; catching `ocr_mac --worker` pid 88160 ALIVE, with its parent
    already gone, named the site in one step. A zombie holds no memory and no cpu - it is a row in
    a table - so nothing on his machine gets slower and nothing errors. It accumulates, silently,
    for the life of a console he leaves up for days, and the only symptom is the process table
    filling. He should never be the one who notices. [[i-own-everything-i-start]]

    ⚠ ONLY OUR OWN. A zombie parented by something else is not ours to report, and a session-wide
    count would turn a neighbour's housekeeping into our red.

    ⚠ ZERO NEEDS A DENOMINATOR. "0 zombies" is worth nothing without how many children were
    examined: a console with no children at all reads exactly the same as one reaping perfectly,
    and only the second is evidence. [[zero-needs-a-denominator]]
    """
    import subprocess as _sp
    # ⚠⚠ v3429 — posix_spawn, NOT fork. THIS PROCESS HAS THE OBJECTIVE-C RUNTIME LOADED
    # (control_app and health_engine import Quartz/CoreGraphics), and forking such a process
    # without immediately exec'ing is the macOS fork-safety deadlock. MEASURED by recording which
    # syscall CPython actually takes:
    #     close_fds default (True)        -> fork_exec x1, posix_spawn x0      <- the hang
    #     absolute exe + close_fds=False  -> posix_spawn x1, fork_exec x0
    #     bare name "ps" + close_fds=False-> fork_exec x1   (the dirname condition bites)
    # A run of cd.run(include_slow=False) hung 28 MINUTES at 0.0% CPU with one child stuck between
    # fork and exec, then finished in 15.4s on the retry. #150.
    #
    # ⚠ BOTH HALVES ARE LOAD-BEARING. CPython 3.9 takes posix_spawn only when the executable has a
    # dirname AND close_fds is false; either alone still forks.
    # ⚠ AND THE COST OF close_fds=False IS SMALLER THAN I FIRST WROTE HERE — MEASURED AFTER I HAD
    # ALREADY PUT THE WRONG CAUTION IN THIS COMMENT. PEP 446 (Python 3.4+) makes every descriptor
    # Python creates NON-INHERITABLE by default, so this passes on only what was DELIBERATELY
    # marked inheritable. Driven end to end: a child handed the fd number of a LIVE LISTENING
    # SOCKET answered `CHILD CANNOT SEE FD -> OSError`. That is not a licence to copy it onto
    # the ocr worker — its LIFETIME is the argument there — but the fd story was not the reason,
    # and a caution that cites a mechanism which does not apply is how a real constraint stops
    # being believed. [[feedback-suspect-the-instrument]]
    _PS = "/bin/ps" if os.path.exists("/bin/ps") else "ps"
    try:
        out = _sp.run([_PS, "-eo", "pid,ppid,stat,comm"], stdout=_sp.PIPE, stderr=_sp.DEVNULL,
                      close_fds=False, timeout=15).stdout.decode("utf-8", "replace")
    except Exception as e:
        return UNKNOWN, ("this machine's process table could not be read (%s), so whether a corpse "
                         "is sitting in it is UNKNOWN - not clear" % type(e).__name__)
    rows = []
    for ln in out.splitlines()[1:]:
        f = ln.split(None, 3)
        if len(f) < 4:
            continue
        try:
            rows.append((int(f[0]), int(f[1]), f[2], f[3]))
        except ValueError:
            continue
    if not rows:
        return UNKNOWN, ("the process table parsed to nothing, so the instrument is the suspect "
                         "here and the answer is UNKNOWN")
    me = os.getpid()
    # ⚠ OUR OWN SUBTREE, not the machine. Walk parents so a grandchild still counts as ours.
    ours, mine = {me}, True
    while mine:
        mine = False
        for pid, ppid, _st, _c in rows:
            if ppid in ours and pid not in ours:
                ours.add(pid)
                mine = True
    kids = [r for r in rows if r[0] != me and r[0] in ours]
    dead = [r for r in kids if r[2].startswith("Z")]
    if dead:
        return MISSING, ("%d of our %d live child process(es) are <defunct> - killed or exited and "
                         "never collected: %s. A corpse costs nothing and accumulates forever. "
                         "MEASURED 2026-09-24 (#224): an in-place os.execv relaunch that left a "
                         "warm worker alive - every exec site now quiesces first and the next image "
                         "reaps what it inherits, so this should clear on the next relaunch; if it "
                         "GROWS between relaunches, something else is letting go of its children"
                         % (len(dead), len(kids), ", ".join("%s(pid %d)" % (c, p)
                                                            for p, _pp, _s, c in dead[:6])))
    return OK, ("0 of %d process(es) in our own subtree are <defunct> - every child this console "
                "has ended was collected" % (len(kids),))


def _check_this_process_runs_the_code_on_disk():
    """v3432 (#179) - IS THIS INTERPRETER EXECUTING THE FILES, OR A CACHED IMAGE OF THEM?

    MEASURED 2026-09-23: three pushes of the IDENTICAL tree read green, RED, green - and the red
    one's traceback named `test_control.py line 11902 ... assertIn('spec["store"]', fn`, where the
    file on disk has that assertion at line 11938 using `helper`. That older shape is exactly the
    PRE-v3427 code, and the same run also reported an older second-eye version. A suite executing
    code that is not on disk is WORSE than a red one: its verdict is about a file nobody has, and
    it cost a real push while pointing at a line that does not exist.

    ⚠ THIS IS NOT THE `running code matches disk` ROW WEARING A SECOND HAT. That one asks the
    CONSOLE over the wire for `proc.srcSha` and `moduleFreshness` - a different process and a
    different question, and it is right that it hashes control_app rather than guessing from here.
    This one asks about THE INTERPRETER THAT IS RUNNING RIGHT NOW, which is the only process that
    can answer it. [[copy-drift]] 1 - one source per question, and these are two questions.

    ⚠ IT CANNOT BE DONE WITH mtime AND SIZE, which is exactly what CPython uses to call a `.pyc`
    fresh - a check from the same two inputs agrees with it by construction, collisions included.
    `co_firstlineno` comes from the BYTECODE while the source is read fresh; a disagreement is
    decisive.

    ⚠ AND THE CACHE IS NOT IN `__pycache__` ON THIS MAC - `sys.pycache_prefix` puts it under
    ~/Library/Caches/com.apple.python, so deleting `__pycache__` clears nothing and a reader who
    looks there concludes wrongly. [[python-pycache-prefix-mac]]
    """
    try:
        import code_identity as _ci
    except Exception as e:
        return UNKNOWN, ("this process cannot import the code-identity reader (%s), so whether it "
                         "is running the files on disk is UNKNOWN" % type(e).__name__)
    mods = [m for m in ("control_app", "console_doctor", "second_eye_run", "lane_census",
                        "health_engine", "corroborate")
            if m in sys.modules]
    if not mods:
        return UNKNOWN, ("none of the modules this row watches are imported in this process, so "
                         "there is nothing to compare - unmeasured, not agreement")
    try:
        ok, text = _ci.say(mods)
    except Exception as e:
        return UNKNOWN, ("the code-identity reader refused (%s), so this is UNMEASURED"
                         % type(e).__name__)
    if ok is None:
        return UNKNOWN, text
    if not ok:
        return MISSING, text
    return OK, text


def _check_the_board_build_door_is_open():
    """v3428 (#37) - IS THE LIVE-BUILD DOOR ACTUALLY SERVED, OR HAS IT GONE 404 AGAIN?

    The GrokBot seat probed for an eval door on THREE separate ticks and got **404 every time**,
    and #37 stayed blocked on one value for weeks because of it. The failure mode is not that the
    reader is wrong - it is that there is NO DOOR AT ALL, which from outside is indistinguishable
    from a console that refused to answer.

    ⚠ IT CHECKS THE ROUTE, NOT THE VALUE, AND THAT IS DELIBERATE. Calling `board_build()` here
    would evaluate JavaScript in the window HE IS LOOKING AT on every periodic tick, to fetch a
    number nothing on this machine consumes - a watch with nothing watching, paid for out of his
    window's responsiveness. What must never regress is that the door EXISTS and is wired into the
    GET table; whether the board answers is the SEAT's question, and it can now ask.

    ⚠ THREE STATES: the reader missing is one finding, the route unwired is a different one, and a
    source this process cannot read is UNKNOWN.
    """
    # ⚠ A GUARDED IMPORT, NOT AN INVENTED HELPER. The first cut of this row called `_ca_mod()`,
    # which does not exist in this module — a NameError that would have taken the whole doctor pass
    # down rather than answering. The same class as the `io.open` slip three rows up, and the
    # fourth time in this file.
    try:
        import control_app as _ca
    except Exception as e:
        return UNKNOWN, ("this process cannot import the console module (%s), so whether the "
                         "live-build door exists is UNKNOWN, not fine" % type(e).__name__)
    if not callable(getattr(_ca, "board_build", None)):
        return MISSING, ("the console has no board_build reader, so the one value #37 is blocked "
                         "on cannot be read from the live window at all")
    ui = os.path.join(HERE, "control_app.py")
    try:
        with open(ui, encoding="utf-8", errors="replace") as _fh:
            body = _fh.read()
    except Exception as e:
        return UNKNOWN, ("the console source could not be read (%s), so whether the live-build "
                         "door is served is UNKNOWN" % type(e).__name__)
    if '"/api/board_build"' not in body:
        return MISSING, ("board_build exists but no route serves it - that is exactly the 404 the "
                         "seat hit on three ticks, and it reads from outside like a console that "
                         "would not answer")
    return OK, ("the live-build door is wired and served at /api/board_build - the seat can ask "
                "the window itself instead of reading the served HTML")


def _check_every_hell_first_hunt_can_name_a_quicker_route():
    """v3426 - DOES THE FILE HE IS ACTUALLY SERVED STILL TELL HIM WHEN SOMEWHERE ELSE IS QUICKER?

    His report, 2026-09-23: MY HUNT sent him to HELL for Cow King's Hooves and called it the
    fastest path, while the Sets chronicle ranked the same piece in NORMAL. The Hell-first headline
    is HIS OWN RULING (v1555) and stays. The missing half is the disclosure that same ruling
    promised - *"he can still choose, he just is not choosing blind"* - which v2281 built on the
    grail hero and which the sets hero went 1,145 versions without.

    ⚠ WHY A LIVE ROW WHEN A GATE ALREADY DRIVES THE EXPRESSION. The gate grades the REPO. This
    console EXECS THE WORKING TREE - every save is a deploy, and two regressions have already been
    real on his screen while absent from a clean checkout. So this reads the file the app actually
    serves and asks whether the disclosure is REACHABLE there. [[execs-the-working-tree]]

    ⚠ REACHABILITY, NOT PRESENCE - and that distinction is not theoretical here: the gate's first
    form asserted these very strings were PRESENT, and both of its red-proofs came back BLIND,
    because `_elsewhere = null` still contains `_elsewhere` and `false ? '...quicker below Hell...'`
    still contains the sentence. [[presence-law-vs-reachability-law]]
    """
    ui = os.path.join(HERE, "control_ui.html")
    try:
        # ⚠ v3426 — `open`, NOT `io.open`: this module does not import `io`, and the first draft of
        # this row used it. The row answered UNKNOWN with `NameError` rather than a false clean,
        # which is the three-state design paying for itself — the SAME mistake once sat behind a
        # bare `except Exception: continue` in the venue check and returned "no browser suite here"
        # forever, whatever was scheduled. [[feedback-blind-fixture-green-gate]]
        with open(ui, encoding="utf-8", errors="replace") as _fh:
            body = _fh.read()
    except Exception as e:
        return UNKNOWN, ("the served console source could not be read (%s), so whether his hunt "
                         "can name a quicker route is UNKNOWN, not fine" % type(e).__name__)
    # ⚠⚠ v3429 — BOUNDED BY THE NEXT HERO, NOT BY A FIXED 14,000 CHARS. The second eye found this
    # reviewing v3426: a fixed slice can read the OTHER hero's text and pass one function on its
    # sibling's evidence, or stop short of a real render and fail a healthy one. MEASURED the same
    # hour: the two are 16,781 chars apart against a 14,000 window — so today it does not overlap,
    # but the margin is 2,781 characters and one paragraph of comment closes it. A law whose
    # correctness depends on a gap nobody watches is a coincidence.
    heroes, blind = ("hubNextGrail", "hubNextSet"), []
    # ⚠ v3429 — THE OPEN PAREN IS LOAD-BEARING. `find("function hubNextSet")` is a SUBSTRING
    # search, so it matches `function hubNextSetRENAMED` too — the row would bind to a renamed or
    # differently-named function and report the hunt healthy on the strength of the wrong one.
    # Caught by this version's own new drive case, not by reasoning about it.
    _starts = sorted((body.find("function " + h + "("), h) for h in heroes)
    if any(i < 0 for i, _h in _starts):
        _gone = [h for i, h in _starts if i < 0]
        return MISSING, ("%s is not in the file this console serves, so the hunt he is looking at "
                         "is not the one the gates grade" % ", ".join(_gone))
    _bounds = {}
    for _n, (_i, _h) in enumerate(_starts):
        _end = _starts[_n + 1][0] if _n + 1 < len(_starts) else len(body)
        _bounds[_h] = (_i, _end)
    for fn in heroes:
        i, _e = _bounds[fn]
        seg = body[i:_e]
        # the assignment must be reachable, and the render must be gated on the value - not on a
        # constant. Either one neutered leaves the sentence in the file and the advice off screen.
        assigns = ("_elsewhere = {" in seg)
        # ⚠ v3426 — GATED ON THE VALUE, ANY MARKUP. The first cut demanded `<span` and reported
        # the GRAIL hero blind, which was my instrument: that card renders a `<div class=
        # "hh-faster">` block. Suspect the instrument first — the count was 1 of 2, and the one it
        # accused was the hero that had HAD this since v2281. [[feedback-suspect-the-instrument]]
        renders = ("(_elsewhere ? '<" in seg) or ('(_elsewhere ? "<' in seg)
        if not (assigns and renders):
            blind.append("%s(%s)" % (fn, "no assignment" if not assigns else "render not gated on it"))
        # ⚠⚠ v3431 — THE CROSS-ITEM HALF IS A SECOND SURFACE AND IT NEEDS ITS OWN WATCH. Each hero
        # answers TWO questions: is the SAME item quicker at a lower difficulty (`_elsewhere`), and
        # is a DIFFERENT item quicker anywhere (`_alt` on the grail hero, `_altPiece` on the sets
        # one). v3426 built only the first on hubNextSet, and the second eye found the gap; a row
        # that watched one of the two would have called that card healthy while it stayed silent
        # about a piece at a fifth of the hours. The names differ per hero and that is not
        # cosmetic — they are the names the shipped code uses. [[the-unjoined-end]]
        _cross = "_altPiece" if fn == "hubNextSet" else "_alt"
        if not (("var %s = " % _cross) in seg
                and (("(%s ? '<" % _cross) in seg or ('(%s ? "<' % _cross) in seg)):
            blind.append("%s(no cross-item alternative)" % fn)
    if blind:
        return MISSING, ("%d of %d Hell-first hunt card(s) cannot name a quicker lower-difficulty "
                         "route: %s. The headline stays Hell by his ruling - what must never go "
                         "with it is the part that stops him choosing blind"
                         % (len(blind), len(heroes), ", ".join(blind)))
    # ⚠ v3431 — THE SENTENCE NAMES WHAT IT NOW MEASURES. It said "a lower-difficulty alternative"
    # while the row had just been widened to check a SECOND one, so a reader would have credited it
    # with half its reach. A row that outgrows its own say is how a check quietly stops meaning what
    # it claims. [[label-outlived-referent]]
    return OK, ("both %d Hell-first hunt cards compute BOTH alternatives - the same piece at a "
                "lower difficulty, and a different piece that is quicker anywhere - and render "
                "each from its own value" % (len(heroes),))


def _check_the_eyes_default_seat_can_still_be_filled():
    """v3425 - CAN THE DEFAULT TRANSPORT BE REACHED AT ALL, ON THIS MACHINE, RIGHT NOW?

    HIS RULING, 2026-09-23: the xAI CLI SUBSCRIPTION is the default transport, said the hour the
    paid API lane went dark (`upload_file` -> PERMISSION_DENIED, all credits used). A default is
    only a default if it is reachable, and this is the one question neither neighbouring row asks:
    `the eye audit agrees with the gate` asks whether looks are being TAKEN, `the eye answers in a
    field` asks whether their verdicts are CONSTRAINED. Both are silent when the binary is simply
    gone, because a lane that never attempts never records a failure.

    ⚠⚠ THAT IS NOT HYPOTHETICAL AND IT IS THE REASON THIS ROW EXISTS. G5 was pinned PRIMARY on the
    TV-D console and silently dark for WEEKS, reporting `mode=off, cli=False, calls=0, errors=0,
    last_error=None` - every honesty surface clean BECAUSE the eye was dark. The cause was
    `shutil.which` searching the calling process's PATH while the console runs under launchd with a
    bare `/usr/bin:/bin`. So this asks the ABSOLUTE path the runner actually uses, which is immune
    to that, rather than re-deriving it from PATH. [[grok-second-eye]] 2

    ⚠ THREE STATES. Absent is a finding; unreadable is UNKNOWN, never fine.
    """
    try:
        import second_eye_run as _eye
    except Exception as e:
        return UNKNOWN, ("this process cannot import the eye runner (%s), so whether its default "
                         "seat can be filled is UNKNOWN, not fine" % type(e).__name__)
    path = getattr(_eye, "EYE_CLI", "") or ""
    if not path:
        return MISSING, ("the eye runner names no default transport at all, so every look would "
                         "record an EMPTY SEAT and nothing would say why")
    try:
        there = os.path.exists(path)
        runnable = there and os.access(path, os.X_OK)
    except Exception as e:
        return UNKNOWN, ("the default transport at %s could not be examined (%s) - UNKNOWN, which "
                         "is not the same as working" % (path, type(e).__name__))
    if not there:
        return MISSING, ("the default transport is not on this machine: %s is absent. His ruling "
                         "of 2026-09-23 makes the CLI subscription the default, and the paid API "
                         "lane is out of credits, so there is no second seat to fall back to"
                         % path)
    if not runnable:
        return MISSING, ("the default transport at %s exists but is not executable, so every look "
                         "would fail at exec and read as an unreachable eye rather than a broken "
                         "install" % path)
    return OK, ("the default transport is present and executable at %s - his 2026-09-23 ruling "
                "that the CLI subscription is the default is satisfiable on this machine" % path)


def _check_the_eye_is_still_answering_in_a_constrained_field():
    """v3420 - ARE THE EYE'S VERDICTS STILL BEING READ, OR HAVE THEY GONE BACK TO BEING GUESSED?

    THE DOCTOR HALF of v3420. The gate pins the LAW on a temp ledger; this asks the live question
    a gate cannot: on THIS machine, are the looks actually arriving with a constrained verdict.

    ⚠ WHY THIS CAN GO DARK SILENTLY, WHICH IS THE WHOLE REASON IT EXISTS. The fallback is
    deliberate and correct - a transport that cannot constrain must still be recordable - so if
    `--json-schema` stops being accepted, the envelope shape changes, or the CLI is swapped for one
    that ignores it, EVERY look quietly reverts to the prose parser and nothing errors. The rows
    keep arriving, the ship gate keeps passing, and the verdicts go back to being inferred by the
    machinery whose own docstrings record a CLEAN look filed as `findings`. A lane that never
    attempts never records a failure. [[heart-first]] 2 - ON is not WORKING.

    ⚠ THREE STATES, and UNKNOWN is a real answer: a machine with no recent look cannot say whether
    the constraint is being applied, and saying so is honest rather than fine.
    """
    try:
        import second_eye_ledger as _sel
    except Exception as e:
        return UNKNOWN, ("this process cannot import the eye ledger (%s), so whether verdicts are "
                         "constrained is UNKNOWN, not fine" % type(e).__name__)
    try:
        rows = [r for r in _sel._rows() if isinstance(r, dict) and r.get("reached") is True
                and str(r.get("verdict") or "").strip()]
    except Exception as e:
        return UNKNOWN, ("the ledger refused to answer (%s), so the route its verdicts came by is "
                         "UNKNOWN" % type(e).__name__)
    recent = rows[-12:]
    if not recent:
        return UNKNOWN, ("no answered look is on record, so whether the eye is being constrained "
                         "cannot be established - that is silence, not agreement")
    schema = sum(1 for r in recent if str(r.get("verdictFrom") or "") == "schema")
    prose = sum(1 for r in recent if str(r.get("verdictFrom") or "") == "prose")
    silent = len(recent) - schema - prose
    tally = ("%d of the last %d answered look(s) constrained, %d parsed from prose, %d predate the "
             "field" % (schema, len(recent), prose, silent))

    # ⚠⚠ v3423 - THE VERDICT IS THE NEWEST LOOK'S, NOT A TALLY'S, AND THE SECOND EYE FOUND THAT.
    # v3420 wrote `if schema: return OK`, so ONE constrained row anywhere in the last twelve held
    # this green - and since a window of twelve spans weeks, the transport could break today and
    # this row would keep saying OK until eleven more looks had pushed the good one out. A check
    # that answers about a POPULATION cannot detect a CHANGE. [[a-law-about-a-row-must-drive-the-row]]
    newest = recent[-1]                     # _rows() is file order, ascending - verified, not assumed
    route = str(newest.get("verdictFrom") or "")

    # ⚠ AND IT NEVER READ A TIME. A route is a fact about the look that carried it, and a look from
    # last month says nothing about whether the eye is constrained NOW. [[stale-reading]] 4 - a
    # verdict with no expiry is not a verdict.
    # ⚠ `ts` IS MILLISECONDS. The G5 budget lane already cost a reading by treating one unit as
    # the other; divide once, here, and never compare a ms stamp to a seconds clock.
    try:
        age_d = (time.time() - (float(newest.get("ts") or 0) / 1000.0)) / 86400.0
    except Exception:
        age_d = None
    if age_d is None or age_d < 0 or not newest.get("ts"):
        return UNKNOWN, ("the newest answered look carries no usable timestamp, so whether the eye "
                         "is being constrained TODAY cannot be established (%s)" % tally)
    if age_d > 7.0:
        return UNKNOWN, ("the newest answered look is %.1f days old, so this says nothing about "
                         "the eye's route today - a lane that is not being asked cannot report "
                         "that it broke (%s)" % (age_d, tally))

    # ⚠ A ROW FROM BEFORE v3420 CARRIES NO verdictFrom AT ALL, and that is not "prose" - nobody
    # recorded how it was obtained. Reading it either way would invent evidence.
    if route == "schema":
        return OK, ("the newest look (%.1f days old) carried a CONSTRAINED verdict; %s"
                    % (age_d, tally))
    if route == "prose":
        return MISSING, ("the newest look (%.1f days old) was PARSED FROM PROSE, not constrained - "
                         "the schema has stopped being applied and the verdict is back to being "
                         "inferred by the parser whose own history includes filing a clean look as "
                         "findings; %s" % (age_d, tally))
    return UNKNOWN, ("the newest look (%.1f days old) predates the route field, so how its verdict "
                     "was obtained is unrecorded - not prose, not schema, unknown; %s"
                     % (age_d, tally))


#: v3467 — how old a two-eye comparison may be while the lane is PRIMARY. A LABELLED judgement, not
#: a measurement: the same three days this file uses for "nothing we made is still on his disk".
_EYES_STALE_DAYS = 3.0


def _check_the_two_eyes_are_compared():
    """#188 — the G5 eye runs PRIMARY on a two-family comparison NOBODY READ. This reads it.

    ⚠⚠ THE PLUMBING HAD NO TAP. v3450 built tv/g5_shadow_reducer.py and its `divergence_row()` —
    "one row a console doctor can render" — and NOTHING outside its own tests ever called it, so
    the 6,082-row shadow log went on being written and read by no surface.
    [[the-unjoined-end]] [[plumbing-with-no-tap]]

    UNKNOWN  no shadow store here (normal on CI — gitignored), no row where BOTH eyes answered, or
             a newest row whose time cannot be read. Silence is not agreement.
    MISSING  (MINE) the lane is PRIMARY and either the newest both-answered read is older than
             _EYES_STALE_DAYS — PRIMARY on evidence that stopped arriving, a verdict with no
             expiry — or the eyes disagree on MORE THAN HALF of what both answered by BOTH
             denominators, reads AND distinct frames. One alone is not enough: MEASURED
             2026-09-24, 1,078/1,596 READS disagree (67.5%) while 66/165 FRAMES do (40.0%),
             because each frame is read ~9.7 times. Published, never averaged.
             [[feedback-contradiction-is-the-finding]] [[zero-needs-a-denominator]] [[stale-reading]]
    OK       otherwise — and the figures still travel in the sentence.

    ⚠ It never prefers a lane. Which eye is right is not knowable from the pair alone; whether they
    were even asked the same question is the first thing to find out, and that is MINE.
    """
    try:
        import g5_shadow_reducer as _R
    except Exception as e:
        return UNKNOWN, ("the shadow reducer will not import (%s), so whether the two eyes agree "
                         "is UNKNOWN" % type(e).__name__)
    try:
        row = _R.divergence_row()
    except Exception as e:
        return UNKNOWN, "the shadow reducer raised (%s) - UNKNOWN, not clean" % type(e).__name__
    st, mode = (row or {}).get("state"), (row or {}).get("mode")
    if st != "measured":
        return UNKNOWN, ("%s - nothing has compared the two eyes here, which is not agreement"
                         % ((row or {}).get("detail") or st))
    names = (((row.get("report") or {}).get("fields") or {}).get("names")) or {}
    reads, frames = names.get("disagree") or {}, names.get("frames_disagree") or {}

    def _frac(f):
        n, d = f.get("n"), f.get("d")
        return ("%d/%d (%.1f%%)" % (n, d, 100.0 * n / d)) if d else "?/0 (no denominator)"

    def _maj(f):
        return bool(f.get("d")) and 2 * int(f.get("n") or 0) > int(f.get("d"))

    last = reads.get("last_ts")
    try:
        # the writer stamps LOCAL time (g5_grok_eyes: time.strftime), so it is read back as local
        age = (time.time() - time.mktime(time.strptime(str(last), "%Y-%m-%d %H:%M:%S"))) / 86400.0
    except Exception:
        return UNKNOWN, ("the newest both-answered read carries no readable time (%r), so how old "
                         "this comparison is is UNKNOWN" % (last,))
    say = ("the two eyes disagree on %s of READS and %s of distinct FRAMES where both answered "
           "(newest %s, %.1f day(s) old) · lane mode=%s" % (_frac(reads), _frac(frames), last, age, mode))
    # #197 — a read placed in NO frame is said out loud, or the frame fraction reads as covering
    # every read when it does not. [[zero-needs-a-denominator]]
    # ⚠ v3483 — BY REASON. v3479 printed the whole unplaced total as "reused scratch names", which
    # also swallowed rows whose picture changed or whose shown picture is unknown (the eye on v3479,
    # finding [2]). Three facts, three counts.
    _unattr = names.get("frames_unattributed_rows")
    if _unattr:
        _whys = names.get("frames_unattributed_why") or {}
        say += " · %d read(s) are attributed to no frame (%s)" % (
            _unattr, ", ".join("%d: %s" % (n, w) for w, n in sorted(_whys.items(), key=lambda x: -x[1]))
            or "reason not recorded")
    if mode == "primary":
        if age > _EYES_STALE_DAYS:
            # ⚠ AND IT CANNOT REFRESH ITSELF. The beside-every-frame shadow read is retired:
            # the live read no longer calls g5_shadow_log, so a PRIMARY comparison cannot grow
            # a new row from the frames going by. Saying so is what keeps this row from being furniture.
            return MISSING, ("the G5 eye is PRIMARY on a two-family comparison last taken %.1f day(s) "
                             "ago - and the beside-every-frame shadow read is retired, so nothing "
                             "writes that comparison from the live read anymore · %s" % (age, say))
        if _maj(reads) and _maj(frames):
            return MISSING, ("the G5 eye is PRIMARY and the two eyes disagree on more than half of "
                             "what both answered, by reads AND by frames · %s" % say)
    return OK, say


#: v3475 — how old the last seed-vs-board check may be before it no longer speaks for now. A LABELLED
#: judgement, not a measurement.
_SEED_CHECK_STALE_DAYS = 7.0


def _check_the_seed_was_checked_against_his_board():
    """#159 — WHEN was the shipped seed last checked against HIS board, and what did it find?

    ⚠⚠ THE VERDICT USED TO BE PRINTED AND THEN GONE: bake_seed.py answered "no drift" to stdout and
    left nothing behind, so this question had no source. It now writes a dated receipt on every
    run (report-only included), and this row READS THE RECEIPT. ⚠ It never re-runs the baker: the
    baker opens his WebKit localstorage under ~/Library, which exists on no runner and is costly on
    his Mac — a row that re-derived would be machine-specific and a permanent skip in CI.
    [[stale-reading]] §4 — a verdict with no expiry is not a verdict.

    UNKNOWN    no receipt (never checked here), an unreadable one, or the last run could not read
               his board store at all.
    MISSING    (MINE) the last check found drift — a bake is owed, with the spec constants it moves.
    UNMEASURED the last check is older than _SEED_CHECK_STALE_DAYS; it carries its last verdict and
               does not bill him.
    OK         checked recently, no drift (or freshly written).
    ⛔ It does NOT widen the seed and does NOT exempt sets — that planned fix was refuted by the
    comment above the seed comparison (it would blind the row to Dean's missing runewords).
    """
    # ⚠ #219 follow-up — the WRITER's own resolver, never a second copy of the path (the second
    # eye on ea3f05da: a patched RECEIPT moved the writer and not this reader). [[copy-drift]]
    try:
        import bake_seed as _bs
        p = _bs.receipt_path()
    except Exception as e:
        return UNKNOWN, ("the seed baker will not import (%s), so where its receipt lives is "
                         "UNKNOWN — not 'never checked'" % type(e).__name__)
    try:
        with open(p, encoding="utf-8") as fh:
            r = json.load(fh)
    except FileNotFoundError:
        return UNKNOWN, ("the seed has never been checked against his board on this machine — no "
                         "receipt yet; `python3 tv/bake_seed.py` (report-only, free) writes one")
    except Exception as e:
        return UNKNOWN, "the seed-check receipt could not be read (%s) — UNKNOWN, not fine" % type(e).__name__
    try:
        age = (time.time() * 1000.0 - float(r.get("ts"))) / 86400000.0
    except Exception:
        return UNKNOWN, "the seed-check receipt carries no readable time, so its age is UNKNOWN"
    out = r.get("outcome")
    if out == "no-store":
        return UNKNOWN, ("the last seed check (%.1f day(s) ago) could not find his board store, so "
                         "whether the seed matches his board is UNKNOWN" % age)
    if out == "drift":
        return MISSING, ("the last seed check (%.1f day(s) ago, %s) found %s name(s) of drift between "
                         "the shipped seed and his board — a bake is owed (bake_seed.py --write, then "
                         "the three spec constants it prints)" % (age, r.get("mode"), r.get("drift")))
    if out not in ("no-drift", "written"):
        return UNKNOWN, "the seed-check receipt reports an outcome this row does not know (%r)" % (out,)
    if age > _SEED_CHECK_STALE_DAYS:
        return UNMEASURED, ("the seed was last checked against his board %.1f day(s) ago (%s) — older "
                            "than %d days, so it no longer speaks for now; re-run bake_seed.py"
                            % (age, out, _SEED_CHECK_STALE_DAYS))
    return OK, ("the seed was checked against his board %.1f day(s) ago: %s — board setPieces %s · "
                "foundLog %s" % (age, out, r.get("boardSetPieces"), r.get("boardFoundLog")))


def _check_the_handoff_lanes_are_being_drained():
    """Are #230 and #231 being READ, or are answers piling up in a queue nobody opens?

    ⚠⚠ HIS ORDER, 2026-09-23, after #230 reached FORTY-ONE unread: *"make sure they both get done
    inbetween and DONT stack up like it just did 41 times"*. The reason it stacked is that NOTHING
    WAS WATCHING — the drainer existed and only ran when someone remembered, which is not a
    mechanism. This row is the watcher. It reads; it never drains and never marks anything read,
    because a check that silenced the backlog would be the truncation regression-guard names.

    ⚠ MEASURED when this was written: #230's watermark sat at 05:40:31Z against a 20:43 clock —
    FIFTEEN HOURS — and the 41 unread ticks carried live answers to open items: #172's theatre
    freeze still firing at v3456 (`freeze=AFTER_REOPEN_PAINT·58756`), the `Fleet PARTIAL` state
    that #157 needs, and ASK digests for #37/#45/#113. Not noise. Answers.

    ⚠ THREE STATES, AND UNKNOWN IS ONE. A lane whose watermark cannot be read is UNKNOWN, never
    "nothing pending" — an unreadable store must not look like an empty queue.
    [[unknown-stays-unknown]] [[the-unjoined-end]]
    """
    import calendar as _cal
    import time as _t
    try:
        import handoff as _H
    except Exception as _e:
        return UNKNOWN, ("handoff.py would not import (%s), so whether the lanes are being drained "
                         "is UNMEASURED — not clear" % type(_e).__name__)
    marks = _H._marks()
    if marks is None:
        return UNKNOWN, ("the handoff watermark store could not be read, so the backlog on #230 "
                         "and #231 is UNKNOWN rather than empty")
    now = _t.time()
    stale, said, _unreachable = [], [], []
    _filed = None

    # ⚠⚠ THE TWO LANES ARE READ BY DIFFERENT MECHANISMS AND ASKING ONE STORE ABOUT BOTH CRIES WOLF.
    # #231 is drained by tv/second_eye_drain.py, which is idempotent through the LEDGER (verdictFrom
    # "gh#231 comment <id>") and never touches handoff's watermark — deliberately, so a human drain
    # of the same issue cannot be silently skipped. So handoff has NO mark for 231 and never will.
    # The first cut of this row asked handoff about both and reported "#231 has NO watermark at
    # all" while the drain was working perfectly. A row that accuses a healthy lane is one he stops
    # reading, which costs more than the backlog it was written to catch.
    # [[strictness-that-closes-the-lane]] [[the-obvious-fix-cried-wolf]]
    try:
        import second_eye_drain as _SD
        _filed = len(_SD.already_recorded())
        _pending = None
        try:
            # ⚠ BOUNDED, BELT AND BRACES. Moving off the every-tick roster stops a stall
            # reaching console boot; it does not stop a stall hanging the PERIODIC tick. `gh` has
            # no deadline of its own, so one is imposed here. A timeout lands in the `except`
            # below and reports UNKNOWN, which is the honest answer for a lane nobody reached.
            _rows = _SD._handoff._gh("repos/%s/issues/%d/comments?per_page=100"
                                     % (_SD._handoff.REPO, _SD.ISSUE),
                                     timeout=_LANE_GH_TIMEOUT)
            import second_eye_ledger as _SL
            _seen = _SD.already_recorded()
            _pending = 0
            for _c in _rows:
                _got = _SD.parse_comment(_c.get("body"))
                if not _got:
                    continue
                # ⚠ A LOOK NAMING NO VERSION IS DELIBERATELY NEVER FILED (the seat writes
                # `version: unknown` for a stampless commit). Counting those as "pending" would
                # make this row nag forever about work that is correctly refused — the first cut
                # did exactly that and reported 5. Never-filed is not a backlog.
                if _SL.norm_version(_got.get("version")) == "":
                    continue
                if str(_c.get("id")) not in _seen:
                    _pending += 1
        except Exception:
            _pending = None            # GitHub unreachable: UNKNOWN, never "nothing pending"
        if _pending is None:
            # ⚠⚠ v3462 — AN UNREACHABLE #231 USED TO FALL THROUGH TO OK. The branch said
            # "could not be asked" and did NOT mark the lane stale, so with a fresh #230 watermark
            # the row printed "both handoff lanes read recently" about a lane it never reached —
            # while the comment three lines up says an unreachable GitHub is UNKNOWN, never
            # nothing pending. The comment and the code disagreed, in code written the same night.
            # [[feedback-comments-vs-code]] [[feedback-silence-is-not-evidence]]
            said.append("#231 could NOT BE ASKED (%d look(s) already filed) — UNKNOWN, not clear"
                        % _filed)
            _unreachable.append("231")
        elif _pending:
            said.append("#231 has %d look(s) NOT yet in the ledger" % _pending)
            stale.append("231")
        else:
            said.append("#231 fully drained (%d filed)" % _filed)
    except Exception as _e:
        said.append("#231 drain could not be asked (%s)" % type(_e).__name__)

    # ⚠⚠ #141 — A MACHINE THAT HAS NEVER DRAINED EITHER LANE IS NOT A DRAINER. MEASURED over SSH on
    # the ALT, 2026-09-25: this row read MISSING - "#231 has 105 look(s) NOT yet in the ledger; #230
    # has NO watermark at all" - on a box where nobody works the lanes; draining happens where the
    # code is worked. No watermark was ever written AND not one look was ever filed, so there is no
    # drain here to fall behind. That is UNMEASURED, not a backlog: whether the drainer keeps up is
    # a fact about ANOTHER machine. A machine that drained even once keeps the full bar, so a lane
    # that stopped is still caught. [[strictness-that-closes-the-lane]] [[unknown-stays-unknown]]
    if not (marks.get("230") or {}).get("ts") and _filed == 0:
        return UNMEASURED, ("this machine has never drained either lane (no #230 watermark, no #231 "
                            "look filed), so it is not where the lanes are worked; whether the "
                            "machine that works them keeps up is not measurable from here")
    for issue in ("230",):
        ts = (marks.get(issue) or {}).get("ts")
        if not ts:
            stale.append(issue)
            said.append("#%s has NO watermark at all" % issue)
            continue
        try:
            # ⚠⚠ v3462 — `mktime(...) + time.timezone` IS AN HOUR WRONG UNDER DST, and this row
            # exists to stop cry-wolf. `time.timezone` is the STANDARD offset (-7200 here) while
            # DST is in effect (`altzone` -10800, tm_isdst=1). MEASURED on a real watermark: the
            # formula said 1.385h where the true age was 0.385h — exactly 1.000h high. A lane read
            # 5.1h ago then reports 6.1h and trips the 6h bar. The stamp is UTC, so the UTC-native
            # inverse is the right tool and it needs no offset arithmetic at all.
            # ⚠ The first tests used 0.5h and 40h, which cannot see a one-hour error.
            # Found by the cross-family eye on the SHIPPED v3458 bytes.
            age_h = (now - _cal.timegm(_t.strptime(ts, "%Y-%m-%dT%H:%M:%SZ"))) / 3600.0
        except Exception:
            said.append("#%s watermark %r will not parse" % (issue, ts))
            stale.append(issue)
            continue
        said.append("#%s last read %.1fh ago" % (issue, age_h))
        if age_h > _LANE_STALE_HOURS:
            stale.append(issue)
    # ⚠ AN UNREACHED LANE IS UNKNOWN, AND UNKNOWN OUTRANKS A CLEAN OK. It is NOT reported as
    # piling up either — nobody measured whether it is.
    if _unreachable and not stale:
        return UNKNOWN, ("a handoff lane could not be reached, so whether it is piling up is "
                         "UNMEASURED — not clear: %s" % "; ".join(said))
    if stale:
        return MISSING, ("a handoff lane is piling up: %s. These carry ANSWERS — the 41-comment "
                         "backlog on #230 held #172's live freeze and the Fleet PARTIAL state #157 "
                         "needs. Drain with: python3 tv/handoff.py --issue <n>  (and "
                         "tv/second_eye_drain.py for #231). Reading does NOT mark them read."
                         % "; ".join(said))
    return OK, "both handoff lanes read recently (%s)" % "; ".join(said)


#: a lane read less often than this is piling up. 6h is generous: #230 ticks every
#: ~15-20 minutes, so six hours is already ~20 unread.
_LANE_STALE_HOURS = 6.0
#: `gh` has no deadline of its own; without this a GitHub stall becomes a doctor stall.
_LANE_GH_TIMEOUT = 20


#: REG-3218 - the board lane derives every minute; a record older than this is a stale reading, not an agreeing board
_BOARD_TRUTH_STALE_MS = 10 * 60 * 1000


def _board_tree_verdict(rec, now_ms):
    """REG-3218 - the eagle's verdict on the lane's record (control_app._task_truth_settle). Pure. -> (state, line)"""
    if not isinstance(rec, dict):
        return UNKNOWN, "the board lane's record is not a record - whether the board agrees with the tree is UNKNOWN"
    lane = "lane: on=%s worked=%s lastTs=%s owed=%s" % (rec.get("on"), rec.get("worked"), rec.get("lastTs"), rec.get("owed"))
    say = str(rec.get("say") or "")[:160]
    if rec.get("on") is False:
        return UNMEASURED, ("this PC does not compare the board with the tree (%s); the board lives on his Mac, and the "
                            "Future button at the console's bottom-left opens it here · %s" % (say, lane))
    if rec.get("on") is not True:
        return UNKNOWN, "whether the board agrees with the tree is UNKNOWN: %s · %s" % (say, lane)
    ts = rec.get("lastTs")
    if not isinstance(ts, (int, float)) or isinstance(ts, bool):
        return UNKNOWN, "the board lane is on and has never compared the board with the tree: %s · %s" % (say, lane)
    age = now_ms - float(ts)
    if age > _BOARD_TRUTH_STALE_MS:
        return UNKNOWN, ("the board was last compared with the tree %.0f min ago - a stale reading, not an agreeing "
                         "board: %s · %s" % (age / 60000.0, say, lane))
    owed = rec.get("owed")
    if not isinstance(owed, int) or isinstance(owed, bool):
        return UNKNOWN, "the tree could not be read, so whether the board agrees with it is UNKNOWN: %s · %s" % (say, lane)
    looks = rec.get("looks")
    looks_say = "looks %s" % looks if looks == "read" else "looks %s (%s)" % (looks, str(rec.get("looksWhy") or "")[:90])
    if owed:
        kinds = rec.get("drift") or {}
        parts = ["%d %s" % (n, k.replace("-", " ")) for k, n in kinds.items() if isinstance(n, int) and n]
        first = "; ".join("#%s %s" % (f.get("id"), str(f.get("say") or "")[:90])
                          for f in (rec.get("first") or [])[:3] if isinstance(f, dict))
        return MISSING, ("%d of %s card(s) disagree with the tree (%s) - the derivation SAYS, nothing rewrites a card: "
                         "%s · %s · %s" % (owed, rec.get("cards"), ", ".join(parts), first, looks_say, lane))
    return OK, ("all %s card(s) agree with the tree at %s (%s) · %s · %s"
                % (rec.get("cards"), rec.get("head"),
                   ", ".join("%s %s" % (n, k) for k, n in sorted((rec.get("phases") or {}).items())), looks_say, lane))


def _check_the_board_agrees_with_the_tree():
    """REG-3217/3218 (his words 2026-11-05: "make sure its derived always console and you and the taskboard synced.. so we
    are always with our finger on the trigger and know whats still being worked on and not shipped").

    MEASURED that evening: the board had not been touched for 6 hours while the work moved - 25 cards said in_progress,
    several describing work shipped days earlier. The board lane (control_app._task_board_loop) now derives every card's
    phase from git and the #230/#231 looks (tv/task_truth.py) and flags a hand status that disagrees; this row reads the
    record it writes (.task_truth.json - the lane runs in the console, this pass in its child) and goes MISSING while any
    card disagrees. On a PC that does not hold the board it is UNMEASURED, said; a stale or unreadable record is UNKNOWN,
    never an agreeing board. [[unknown-stays-unknown]] [[heart-first]]"""
    import control_app as _ca
    try:
        with open(_ca._task_truth_state_path(), encoding="utf-8") as fh:
            rec = json.load(fh)
    except FileNotFoundError:
        return UNKNOWN, ("the board lane has not written its record on this PC yet (it starts 45 s after the console) - "
                         "whether the board agrees with the tree is UNKNOWN")
    except Exception as e:
        return UNKNOWN, "the board lane's record would not read (%s) - UNKNOWN" % type(e).__name__
    return _board_tree_verdict(rec, time.time() * 1000.0)


def _check_a_windowed_frame_is_read_inside_its_game():
    """v3856 - a windowed-mode frame (title bar + letterbox, Dean's 800x409 family) is measured inside its game area."""
    import tempfile, shutil
    try:
        import char_select as CS
    except Exception as e:
        return UNKNOWN, "char_select would not load (%s), so windowed frames are unknown" % type(e).__name__
    d = tempfile.mkdtemp(prefix="doc_win_")
    try:
        try:
            p = CS.windowed_fixture(os.path.join(d, "f_1.jpg"))
        except Exception as e:
            return UNKNOWN, "the windowed lobby frame could not be built here (%s), so it was not measured" % type(e).__name__
        # v3866 (the #231 eye on v3858) - a reader that RAISES on the frame this check just built is a reader that fails,
        # not an unknown: it was UNKNOWN, so the row could never go red for the defect it watches
        try:
            ok, why = CS.looks_like_lobby(CS.lobby_stats(p))
        except Exception as e:
            return MISSING, ("the lobby reader raised %s on a windowed frame this check built - a lobby filmed in a window "
                             "is not seen" % type(e).__name__)
    finally:
        shutil.rmtree(d, True)
    if not ok:
        return MISSING, "a lobby filmed in a window (title bar and black bars) is not seen: " + why
    return OK, "a lobby filmed in a window is read inside its game area"


def _check_the_d2jsp_price_backend_matches_its_database():
    """The Advanced door on the D2JSP tab shows the price database the quote already computes."""
    try:
        with open(os.path.join(ROOT, "bible.html"), encoding="utf-8", errors="replace") as fh:
            page = fh.read()
    except OSError:
        return UNKNOWN, "bible.html could not be read, so the price database door is unknown"
    if 'id="d2jsp-price-advanced"' not in page or 'id="d2jsp-price-backend"' not in page:
        return MISSING, "the D2JSP tab has no Advanced door onto the price database"
    call = "d2jspBackendHtml(j && j.db, j && j.fg, {sync:true, say:j && j.say})"
    if call not in page or "function d2jspBackendHtml" not in page:
        return MISSING, "a search does not fill the price database panel"
    try:
        with open(os.path.join(HERE, "control_app.py"), encoding="utf-8", errors="replace") as fh:
            app = fh.read()
    except OSError:
        return UNKNOWN, "control_app.py could not be read, so the price fold is unknown"
    if '_out["db"] = _d2jsp_db_fold(_out)' not in app:
        return MISSING, "the quote no longer folds the price database"
    import d2jsp_price_db as pdb
    db = pdb.empty()
    now = 1793397600.0
    day = "2026-10-31"
    for fg, w, n in ((100, 1, 1), (100, 1, 2), (9000, 0, 3)):
        pdb.ingest(db, {"item": "Shako", "reason": "read", "posts": [{
            "fg": fg, "day": day, "w": w,
            "link": "https://forums.d2jsp.org/topic.php?t=%d" % n,
        }]}, "mac", now)
    priced = pdb.price(db, "Shako", now)
    proof = pdb.explain(db, "Shako", now)
    aside = [p for p in proof.get("posts") or [] if p.get("band") == "aside"]
    normal = priced.get("normal") or {}
    if normal.get("fg") != 100 or not (normal.get("conf") or 0) > 0:
        return MISSING, "two agreeing posts did not price at 100 fg"
    if len(aside) != 1 or aside[0].get("decayed") != 0:
        return MISSING, "a set-aside post moved the price or left the record"
    return OK, "the D2JSP tab shows the database price and the posts it was weighed from"

def _check_quick_wins_places_have_their_pictures():
    """#85 (REG-3269) - every picture the Quick wins grid names is in art/: each super-unique's sprite or portrait
    (_QW_SU_ART) and every zone's level art (TZ_INFO's slugs, art/tz_<slug>.jpg). A tile whose file is gone renders as an
    empty dark square under a confident name - an art clean-up is exactly what would do it, and no gate opens the page."""
    try:
        with open(os.path.join(ROOT, "bible.html"), encoding="utf-8", errors="replace") as fh:
            page = fh.read()
    except OSError:
        return UNKNOWN, "bible.html could not be read, so the Quick wins pictures are unknown"
    m = re.search(r"var _QW_SU_ART = \{(.*?)\};", page, re.S)
    t = re.search(r"var TZ_INFO = (\{.*?\});", page)
    if not m or not t:
        return MISSING, "the Quick wins grid's picture map (_QW_SU_ART) or the zone table (TZ_INFO) is gone from the page"
    files = re.findall(r"'([^']+\.(?:gif|png|jpg))'", m.group(1))
    try:
        slugs = sorted(set(v[2] for v in json.loads(t.group(1)).values() if isinstance(v, list) and len(v) > 2))
    except ValueError:
        return UNKNOWN, "the zone table would not parse, so the zone pictures are unknown"
    want = ["art/" + f for f in files] + ["art/tz_%s.jpg" % s for s in slugs]
    gone = [w for w in want if not os.path.isfile(os.path.join(ROOT, w))]
    if not files:
        return MISSING, "the Quick wins grid names no monster picture - its map is empty"
    if gone:
        return MISSING, "%d of the %d pictures the Quick wins grid names are not in art/: %s" % (
            len(gone), len(want), ", ".join(gone[:6]))
    return OK, "all %d pictures the Quick wins grid names are in art/ (%d monsters, %d zones)" % (len(want), len(files), len(slugs))


def _check_the_macs_own_d2jsp_window_keeps_its_session():
    """#87 (REG-3253) - the Mac signs in to d2jsp through a profile the console owns. That sign-in survives closing the
    window only while the profile continues where it left off (a session-only cookie is then written to disk), and the
    lamp's opener must start that profile, never his own Chrome. Read-only: nothing is opened, written or launched."""
    if sys.platform != "darwin":
        return OK, "not a Mac - this PC signs in to d2jsp through its own lane"
    try:
        import d2jsp_chrome as dj
    except Exception as e:
        return UNKNOWN, "the d2jsp desk would not import (%s), so its own window is unknown" % type(e).__name__
    root = dj.login_profile_dir(platform="darwin")
    seen = []
    try:
        dj._open_chrome_login(platform="darwin", run=lambda argv, **kw: seen.append(list(argv)) or
                              type("P", (), {"returncode": 0})())
    except Exception as e:
        return UNKNOWN, "the lamp's opener raised %s when asked for its command, so its own window is unknown" % (
            type(e).__name__)
    argv = seen[-1] if seen else []
    if not root or ("--user-data-dir=%s" % root) not in argv:
        return MISSING, "the D2JSP lamp opens his own Chrome, whose sign-in d2jsp turns away, not the console's own window"
    if any("9222" in a or "remote-debugging" in a for a in argv):
        return MISSING, "the D2JSP lamp's window asks for a debugging port (9222 is his Chrome's)"
    if not os.path.isdir(root):
        return OK, "the console's own d2jsp window has not been opened on this Mac yet - the lamp says to click it"
    prefs_path = os.path.join(root, "Default", "Preferences")
    try:
        with open(prefs_path, encoding="utf-8") as fh:
            prefs = json.load(fh)
    except FileNotFoundError:
        return MISSING, "the console's own d2jsp profile has no Preferences, so a sign-in there dies with the window"
    except (OSError, ValueError) as e:
        return UNKNOWN, "the console's own d2jsp profile settings would not read (%s)" % type(e).__name__
    if ((prefs.get("session") or {}) if isinstance(prefs, dict) else {}).get("restore_on_startup") != 1:
        return MISSING, ("the console's own d2jsp profile no longer continues where it left off, so the sign-in's session "
                         "cookie dies when that window closes")
    return OK, "the D2JSP lamp opens the console's own d2jsp window, and that profile keeps its sign-in when it closes"

CHECKS = [
    # v2961 (#67) — the drift lane compares version LABELS; this compares the BYTES, which is the
    # only way an unstamped save can be seen. See the docstring for why it asks the console rather
    # than hashing its own import.
    ("running code matches disk", _check_the_running_code_is_the_code_on_disk),
    # v3458 — his 2026-09-23 order after #230 reached 41 unread: the lanes must not stack up.
    # Nothing was watching them, so nothing noticed. This watches.
    ("handoff lanes drained", _check_the_handoff_lanes_are_being_drained),
    # v3467 (#188) — the two-eye comparison the G5 lane was promoted on, finally READ.
    ("two eyes compared", _check_the_two_eyes_are_compared),
    # v3475 (#159) — the seed's last check against his board, read from the baker's receipt.
    ("the seed was checked against his board", _check_the_seed_was_checked_against_his_board),
    # v3406 (#152) — the harness that proves the paid sweep door can be answered by the
    # LOCK instead of the door. One call, worker stubbed, and it distinguishes UNREACHED
    # from refused. See the docstring for the sandbox measurement that found it.
    ("sweep attack reaches its door", _check_an_attack_can_still_reach_the_door_it_scores),
    # v3407 (#155) — PERIODIC on purpose: it reads the whole of control_app.py, and the cheap
    # subset runs on EVERY eagle tick and in the boot path of every console a test spawns.
    ("no git child steals his screen", _check_no_git_child_can_steal_his_screen),
    # v3408 (#154) — per MACHINE, not per fleet: a box with no signed-in CLI files empty seats
    # however healthy the ledger totals look. Disk only, no network, no spawn.
    ("this machine can get a second opinion", _check_this_machine_can_get_a_second_opinion),
    # #227 — per MACHINE: the ALT had no Pillow, so every frame it filmed was unreadable, silently
    ("this machine can decode a frame", _check_this_machine_can_decode_a_frame),
    # REG-1719 — per MACHINE: the ALT had no numpy, so no inventory grid could ever be measured there, silently
    ("this machine can cross-check an inventory", _check_this_machine_can_cross_check_an_inventory),
    # #105 (REG-1604) — per MACHINE: the ALT's Claude was signed out and read nothing for hours, silently.
    ("this machine's reader can read", _check_this_machines_reader_can_read),
    # #54 — what he wears, per character, filed at every seal; owes the reels the seal nudge missed.
    ("equipped ledger files every seal", _check_the_equipped_ledger_files_every_sealed_reel),
    # v3301 (#38) — his ruling built a HOLD with a GREEN LIGHT; this asks whether the green light
    # still fires. A held relaunch looks pending right up until it expires unfired, so the only
    # way to see the release path die is to corroborate the register against the world.
    ("relaunch green light", _check_a_held_relaunch_is_not_stuck),
    # 2026-09-28 — the build that never landed on his ALT: v3520 beside v3521 for 2+ h, a shadow
    # reel read as "you are filming". MISSING past two hours, naming WHY.
    ("the running build is behind the disk", _check_the_running_build_is_not_behind_the_disk),
    # v3310 (#56) — his ruling is ask TWICE and keep both. Named in MINE below: a single look is
    # MY omission, not something he can act on.
    ("shelf order and guard", _check_the_shelf_keeps_his_order_and_its_guard),
    ("swallowed reads", _check_a_failed_read_is_never_handed_back_as_data),
    ("second eye asked twice", _check_the_second_eye_was_asked_twice),
    ("eye reach per file", _check_the_eye_reach_is_still_being_measured),
    # v3375 (#122) — a SIBLING question, not the same one: "eye reach per file" asks how much
    # of each file ARRIVED; this asks whether the eye is told what was deliberately REMOVED
    # before transport. A payload can be 100% reach and still have the author's note stripped.
    ("eye told what was stripped", _check_the_eye_is_told_what_was_stripped),
    # v3376 (#125) — the parser output against the other family OWN WORDS. A misread verdict
    # is laundered straight into agreement(), so this asks the one question the ledger cannot
    # ask itself: does the row agree with the answer it was written from?
    ("verdict matches the answer", _check_no_row_contradicts_its_own_stated_verdict),
    # v3378 (#28) — the RIVER half, and a different question from every gate on it: the gates
    # prove _owes_of is correct, this asks whether his running river is still BEING HANDED the
    # verdict. A cut forward reverts the sentence and raises nothing.
    # v3379 (#128) — the FLEET half, and no gate can ask it: the gates prove the hand-over is
    # correct today, this asks whether his running console is still BEING handed the stores.
    # A cut hand-over publishes a count for ever and a list never, silently.
    ("a look keeps its evidence", _check_a_look_keeps_its_evidence),
    ("a present machine has a fresh last-seen", _check_a_present_machine_has_a_fresh_last_seen),
    # #223 — reads the presence cache (no network), so it runs every tick and its ask never flickers
    ("no machine went quiet mid-restart", _check_no_machine_went_quiet_mid_restart),
    # #229 — one Startup-folder listing and one schtasks query; every tick so his question never flickers
    ("this console starts at sign-in", _check_this_console_starts_at_sign_in),
    ("a tally agrees with its own ledger verdict", _check_a_tally_agrees_with_its_own_ledger_verdict),
    ("the eye asks for every code extension", _check_the_eye_asks_for_every_code_extension),
    ("a presence reading names its door", _check_a_presence_reading_names_its_door),
    ("a fleet row identifies its machine", _check_a_fleet_row_identifies_its_machine),
    ("a fleet refusal names an action", _check_a_fleet_refusal_names_an_action),
    # #95 - two local reads (the publish receipt and the fetched roster cache), no network: every tick.
    ("every roster publish is signed", _check_every_roster_publish_is_signed),
    ("a worker read has a deadline", _check_a_worker_read_has_a_deadline),
    ("no browser is launched unreaped", _check_no_browser_is_launched_unreaped),
    ("fleet can name what it counts", _check_the_fleet_can_name_what_it_counts),
    ("the compare panel can name a difference",
     _check_the_compare_panel_can_name_a_difference),
    ("this console tree is established",
     _check_this_console_tree_is_established),
    # v3410 — its SIBLING, and a different question: that row asks whether the roots EXIST,
    # this one asks whether the PLANNERS and the WRITERS are looking at the same ones.
    ("the door and the writers agree", _check_the_door_and_the_writers_name_the_same_tree),
    # v3413 (#160) — PERIODIC: it shells out to git twice, and the cheap subset is already
    # 14,168 ms against a 9,000 ms budget (#150).
    ("the resume agrees with git", _check_the_resume_agrees_with_git_right_now),
    ("the chip can say nobody looked", _check_the_chip_can_say_nobody_looked),
    ("the eye audit agrees with the gate", _check_the_eye_audit_agrees_with_the_ship_gate),
    ("the eye cap is a size it has finished", _check_the_eye_cap_is_a_size_the_eye_has_finished),
    ("the eye answers in a field", _check_the_eye_is_still_answering_in_a_constrained_field),
    ("the eye seat can be filled", _check_the_eyes_default_seat_can_still_be_filled),
    ("the hunt names a quicker route", _check_every_hell_first_hunt_can_name_a_quicker_route),
    ("the board build door is open", _check_the_board_build_door_is_open),
    ("this process runs the code on disk", _check_this_process_runs_the_code_on_disk),
    ("nothing we started is a corpse", _check_nothing_this_console_started_is_a_corpse_right_now),
    ("our scratch is collected", _check_nothing_we_made_is_still_on_his_disk_days_later),
    ("a verdict comes from a declared field",
     _check_a_verdict_comes_from_a_declared_field),
    ("a queue zero came from a read that worked",
     _check_a_queue_zero_came_from_a_read_that_WORKED),
    ("river owes what its engine says", _check_a_reel_owes_what_its_engine_says),
    ("item vocabulary", _check_the_item_vocabulary_can_name_his_loot),
    ("save reader tables", _check_the_save_reader_matches_the_install),
    ("character sheet data", _check_the_character_sheet_data_matches_the_install),
    ("builder item data", _check_the_builder_database_matches_the_install),
    # #41 rank 15 (2026-09-29) — the mule window's slot / hands / class blocks, from the same install, had no row.
    ("mule slot rules", _check_the_mule_slot_rules_match_the_install),
    # #41 rank 12 + 13 (2026-09-29) — the 👤 Characters room had no row: an unparseable d2r_charBuilds, a dangling
    # d2r_cbMain, and two MAINs naming different characters were all silent. Off the shared board read, every tick.
    ("characters room", _check_the_characters_room),
    # #36 (REG-2909) - a session no screen named asks him, in his words: "open the C panel once"
    ("which character each session is on", _check_which_character_each_session_is_on),

    # #41 rank 16 (REG-1560) — the composition against THEIR planner's measured tooltip, off the lane's per-row
    # receipt. Cheap: a small file and a hash of bible.html; the node run belongs to the lane.
    ("their tooltip rows", _check_their_tooltip_rows_are_ours),
    # #246 W7 — the one door into the mule map, watched: every filing carries its witness, no MAIN item in
    # a mule, no gate-passing stash row left unfiled, the feeder's banked vs runs.
    ("vault provenance", _check_vault_provenance),
    # 2026-09-28 — every name in `owned` says who filed it; every read that named something kept its picture.
    ("a vault item with no provenance", _check_vault_items_carry_provenance),
    ("a read left no picture", _check_a_read_left_no_picture),
    # 2026-09-29 (#55) — the reel's chain of custody: five stores, one record, and the contradictions named.
    ("reel custody", _check_reel_custody),
    ("vault reset receipt", _check_the_vault_reset),
    ("evidence tiers", _check_the_evidence_tiers),
    # 2026-09-29 (#58) — Ledger 3.0: a sealed reel on the shelf whose reader rows rotated out of the
    # ring is a trail that cannot be drawn for footage he still has. PERIODIC (see its docstring).
    ("ledger3 sessions", _check_the_ledger3_trail_can_be_drawn),
    ("fault evidence", _check_a_ui_fault_keeps_its_evidence),
    ("capture root live", _check_the_capture_root_is_still_being_written),
    ("item facts captured", _check_the_item_facts_are_reaching_the_row),
    # v2942 (#59) — THE DRIVER EXISTED, WAS GATED, AND NOTHING RAN IT. See the docstring: his
    # stored beat was 31.6h old while control_app imported the module under two aliases and called
    # nothing on either. [[the-unjoined-end]]
    ("shelf lanes reading", _check_the_shelf_lanes_are_still_reading),
    # v2843 — THE FLEET, WHICH THE HEART HAD NEVER HEARD OF. `grep -c fleet` was 0 across
    # heart.py and lane_census.py while his card sat on "unreachable" and the footer said 8 dark.
    ("fleet reachable", _check_the_fleet_lane_is_reachable),
    # #41 rank 22 (REG-1564) — each PC's character picker against its own database, off the same roster
    ("picker census", _check_the_picker_census_agrees_on_every_pc),
    # v2277 — four questions nobody was asking. Each was found BY HAND this session, and each was
    # silent by construction: an armed one-shot that would have dropped 273 of his 280 owned names,
    # a lane that had said nothing for 137h, a console asking ITSELF for the board, and my own
    # unbounded glob holding a core at 99.7% for 28 hours.
    ("armed migration", _health("armed_migration")),
    ("extraction lanes", _health("lanes")),
    # v2304 — the watcher that makes playing enough. It reaches the ONE surface in the same
    # breath as the lanes it belongs beside, or it is a feature only a log knows about.
    ("shadow watch", _health("shadowWatch")),
    # v2310 — the two game readers, on the one surface he reads
    ("readers agree", _health("readers")),
    ("board join", _health("board_join")),
    ("stray processes", _health("orphans")),
    # ⚠ v2228 — (NAME, FN) TUPLES. My first cut added these two as BARE FUNCTIONS and broke the
    # `for n, fn in CHECKS` unpacking in nine places at once, including the healer's recheck map.
    # THE COUNT WAS THE TELL: nine errors from one edit is a shape mistake, not nine defects.
    ("engines corroborate", _check_the_engines_CORROBORATE_each_other),
    # v2336 — the eagle can see his SCREEN, not only his engines
    ("panels on screen", _check_no_panel_is_dark_with_its_content_in_hand),
    ("the shelf tabs are his stations", _check_the_shelf_tabs_are_alive),
    ("the vault can say what it proves", _check_the_vault_can_say_what_it_proves),
    # v2336 — the suites belong on GitHub; this notices when one comes back to his laptop
    ("test venue", _check_no_browser_suite_is_scheduled_on_this_mac),
    # #151 - his reader switch: at GROK ONLY a Grok that cannot read leaves frames unread, and nothing falls back
    ("reader switch", _check_his_reader_switch_can_read),
    # v2761 — the river's ELEVEN joints reach a screen; the existing "the river" row
    # watches reel_router (WHERE reels are stationed), which is a different question.
    ("river joints", _check_the_river_joints_carry),
    # the outlet — ROUTED was unreachable while its only writer lived inside the deleter, so no
    # reel could ever be recorded as finished. This watches whether the river actually drains.
    ("river outlet", _check_the_river_has_an_outlet),
    # the accumulator's stored proposal, re-gated against today's bars. `vault stores` above asks
    # only whether the files are readable; this asks whether what they OFFER is still acceptable.
    ("vault proposal", _check_the_vault_proposal_still_clears_todays_bar),
    ("console UI faults", _check_the_console_UI_has_not_faulted),
    ("version drift", _check_version_drift),
    # v2248 — the OTHER out-of-sync: drift is process-vs-disk, this is disk-vs-origin, and
    # Dean sat 85 versions behind with drift green because his two agreed on old bytes.
    ("behind the fleet", _check_behind_the_fleet),
    ("lane intent", _check_lane_intent),
    ("what runs without you", _check_what_runs_without_him),
    ("disk headroom", _check_disk_headroom),
    # REG-3208 - WHAT grows, and what waits on a salvage; the row above only says how much is free
    ("disk growers", _check_the_disk_growers_are_salvaged_then_pruned),
    ("subscription", _check_subscription_burn),
    ("unattended reel", _check_a_reel_is_not_recording_unattended),
    ("reel population", _check_every_reel_on_disk_is_accounted_for),
    ("reel extract", _check_the_reel_extract_is_moving),
    ("hunt economy", _check_the_hunt_is_buying_something),
    ("sweep would find", _check_the_sweep_would_find_something),
    ("stash bank", _check_the_stash_bank),
    ("board is claimed", _check_the_board_world_is_claimed),
    # v2746 — WHERE each ledger's rows came from, per ledger. `board is claimed` above asks whether
    # this world PERSISTS; this asks whether its rows are its OWN. Different sentences, and the
    # second was answered by one boolean over three ledgers until now.
    ("ledger provenance", _check_every_ledger_can_say_WHERE_IT_CAME_FROM),
    # v2746 — the GENERAL form of the seed defect. `ledger provenance` asks WHERE a figure came
    # from; this asks HOW OLD it is, for every ledger figure and not only the seeds. His words:
    # "connect it all to the heart of the console so nothing becomes stale again".
    ("ledger staleness", _check_no_ledger_FIGURE_has_gone_stale_unnoticed),
    ("visual lock", _check_the_visual_lock_holds),
    ("reel clocks", _check_every_reel_can_date_itself),
    ("art corpus", _check_the_art_corpus),
    ("footage has a reel", _check_footage_belongs_to_a_reel),
    ("vault stores", _check_the_vault_stores_are_readable),
    # v2730 — his "so its all not in the dark": the evidence ledger and the backup that is meant
    # to protect it both had ZERO rows in this list until now.
    ("evidence ledger", _check_the_evidence_ledger_is_readable),
    ("ledger backup", _check_the_ledger_backup_covers_every_store),
    ("backup loop", _check_the_backup_loop_is_actually_WRITING),
    # REG-3213 (v3865) - v3864's shard 10 ran 87 min and nothing said so; red past his 75-minute max, every tick
    ("this version's CI", _check_this_versions_ci),
    # 2026-09-27 — a store that FELL (setPieces 134 -> 0, owned 223 -> 0) and every row above was
    # green: `ledger entries` diffs only the two newest snapshots. This reads the loop's durable
    # drop record, which stays open until the store is back — and watches the watcher.
    ("ledger drop", _check_no_ledger_store_dropped_unseen),
    ("console painted whole", _check_the_console_painted_all_of_itself),
    ("names banked", _check_read_names_are_actually_banked),
    ("read names lane", _check_read_names_lane),
    ("stage shows the dom", _check_the_stage_shows_what_the_dom_claims),
    ("river walk", _check_the_river_walk_is_walking),
    # 2026-09-27 — the MOUTH of the river: releasable reels carried through `stoppedAfter` passes
    # with nothing released is a drain that stopped. Reads the wire, one cheap GET per tick.
    ("retention drain", _check_the_retention_drain_is_draining),
    # 2026-09-28 — the river's SOURCE end: reels waiting in TRIAGE while the lane that walks them
    # has walked none for three hours. His ALT held 7 of 10 there, silently. PERIODIC (see below).
    ("triage starved", _check_triage_is_not_starved),
    # v#### — ONE ROW PER REEL ROUTE. ⚠ THE NAMES ARE HARD-CODED ON PURPOSE, so they are
    # greppable and so the rail cannot silently grow a row nobody argued for; the gate asserts
    # this list covers every entry in reel_templates.ROUTES, which is where a fifth route would
    # otherwise arrive unwatched. [[the-unjoined-end]]
    ("route stash", _route_health("stash")),
    ("route chronicle · sets", _route_health("chronicle · sets")),
    ("route chronicle · uniques", _route_health("chronicle · uniques")),
    ("route inventory", _route_health("inventory")),
    ("printer reach", _check_the_printer_can_reach_the_corpus),
    ("end routes reachable", _check_every_reel_can_still_reach_an_end_route),
    ("the river", _check_the_river_is_moving),
    # v2995 (#34) — THE ONLY CHECK THAT DOES NOT ASK THE PAGE. Every other entry in this list can
    # be answered 200 by a console that is painting nothing; measured on his machine 2026-09-10,
    # that is exactly what happened twice in one day. This one hashes screencaptures of the real
    # window. [[the-blank-console-detector]]
    ("screen still painting", _check_the_screen_is_still_painting),
    # v2996 (#58/#34) — THE FILL AND THE RECT, TOGETHER. Grokbot saw an empty stage while this
    # same beat reported cards~535; both were honest, because a DOM can be built inside a
    # container that occupies no pixels and nothing ever asked WHERE it was. [[the-unjoined-end]]
    ("window runs the document on disk", _check_the_window_runs_the_document_on_disk),
    ("shelf is where it says", _check_the_shelf_is_where_it_says_it_is),
    ("progress number", _check_his_progress_number_has_not_been_overwritten),
    ("ledger entries", _check_no_ledger_ENTRY_has_silently_vanished),
    ("store emptied", _check_the_board_store_did_not_come_up_empty),
    ("shadow gate", _check_the_shadow_gate_is_learning),
    # #228 — his question, not a red card. EVERY TICK, NOT PERIODIC, and that was measured: a
    # skipped PERIODIC row is UNMEASURED and attach_asks gives an UNMEASURED row no question, so
    # his ask would leave WAITING ON YOU on 5 of every 6 ticks. It reads the saved sweep (11 ms).
    ("a fresh remaining page", _check_a_fresh_remaining_page_would_settle_the_sets_count),
    ("locked lanes", _check_the_locked_lanes_still_refuse),
    ("his gear", _check_his_gear_is_being_learned),
    ("tooltip finder", _check_the_tooltip_finder_is_honest),
    ("surfaces agree", _check_the_two_surfaces_agree),
    ("the other doctors", _check_the_other_doctors),
    # v3397 — scans the bytes the console SERVES, not the file on disk: a console holds its
    # source from import, so a fixed file and a stale console are indistinguishable from the
    # tree. The gate grades disk; this grades the wire.
    ("a hidden element is actually hidden", _check_a_hidden_element_is_actually_hidden),
    # v3398 — the window controls can now say what the window DID, not what was called.
    # This asks whether that measurement still works; a frame that stops being readable
    # loses the numbers and keeps the ok, which looks exactly like a working control.
    ("his window can be measured", _check_his_window_can_be_measured),
    # v3402 — a SIBLING question, not the same one: that row asks whether the frame can be READ;
    # this asks whether the KEY that changes it is still being served.
    ("his window has a keyboard door", _check_his_window_has_a_keyboard_door),
    # v3404 — the fleet question, asked of THIS machine: a console that stops pulling
    # looks identical to one that is up to date, until he notices the version gap.
    ("this machine keeps itself current", _check_this_machine_is_keeping_itself_current),
    # #64 — the WHY behind the row above: the pull lane's own record of whether its pulls land.
    ("this checkout can update", _check_this_checkout_can_update),
    ("the d2jsp price database is on its tab", _check_the_d2jsp_price_backend_matches_its_database),
    ("the Mac signs in to d2jsp through its own window", _check_the_macs_own_d2jsp_window_keeps_its_session),
    ("quick wins places have their pictures", _check_quick_wins_places_have_their_pictures),
    ("a windowed frame is read inside its game", _check_a_windowed_frame_is_read_inside_its_game),
    # REG-3218 (his words 2026-11-05) - the task board compared with the tree; a card that disagrees is said, never rewritten
    ("the board agrees with the tree", _check_the_board_agrees_with_the_tree),
]


# v2026 — the sub-doctor call shells out to two full diagnostics and costs ~2 minutes. That is
# fine for a human pressing the button and NOT fine on every CI run, so callers can ask for the
# cheap subset. The slow one is named rather than guessed at, so adding a check never silently
# joins the slow set.
# v2080 — AND "sweep would find" WAS NEVER CHEAP. Measured on a fixture tree: 16,585 ms of a
# 17,069 ms "cheap subset" — 97% of it, in the set that runs on a ten-minute timer at every console
# boot. It cost a gate: v2080 made the eagle measure BEFORE it sleeps (right) and start in headless
# consoles too (right), and together those two correct fixes put a 17-second tick in the boot path
# of every console a test spawns, pushing test_roundtrip_sim's stub read past its 60s deadline.
# Two fixes breaking each other, and neither was wrong on its own. [[two-fixes-broke-each-other]]
#
# The SLOW set being NAMED rather than guessed was the right design and it did not save me, because
# nobody had timed the members. A list is a claim; the guard below now MEASURES it.
# v2801 — AND "engines corroborate" WAS NEVER CHEAP EITHER. The exact same defect as the line
# above, found the same way: by timing the members rather than trusting the list. Measured
# 2026-09-08 across fresh processes: **7,672 ms · 6,638 ms · 7,692 ms**, and 13,038 ms inside a
# test process — against a subset budget of 3,000 ms per check. It was the largest single cost in
# the "cheap" set every time it was the largest cost in anything.
#
# ⚠ THE REASON IT HID FOR SO LONG IS WORTH MORE THAN THE FIX. The cheap-subset gate names its
# culprits, and the name it printed CHANGED EVERY RUN — 'stage shows the dom (7301 ms)' once,
# 'armed migration (3645 ms)' and 'panels on screen (3384 ms)' the next, 141 ms each minutes later.
# Attention went to whichever name was printed, and each of those was innocent: re-timed on the
# spot they cost 75-146 ms. The one check that was slow in EVERY reading was rarely the one
# accused, because a burst on a busy machine lands wherever it lands. A flapping gate does not
# merely fail to catch a defect - it actively points away from it.
# [[feedback-suspect-the-instrument]] [[regression-guard]]
#
# It stays on the roster and the full doctor run still performs it (the mirror gate
# test_a_check_moved_to_SLOW_is_still_RUN_somewhere enforces exactly that); it simply stops
# running on the ten-minute timer and in the boot path of every console a test spawns.
# ⚠ v3014 — "sweep would find" LEFT SLOW FOR PERIODIC. SLOW means NEVER RUNS UNATTENDED
# (_eagle_once calls include_slow=False), so the one sweep-shaped eagle check ran only when a
# human pressed the button — the census named it the #3 organ gap. Cost, both figures honest:
# 16,585 ms once measured on a full shelf (why it went to SLOW), 1,660 ms measured 2026-09-12 on
# today's 24-reel shelf. At PERIODIC's ~hourly unattended cadence either figure is the same class
# as 'engines corroborate' (6,638-13,038 ms), which is the precedent tier for exactly this shape.
SLOW = ("the other doctors",)

# ══ v2802 — A THIRD TIER, AND THE REASON IS A REGRESSION I SHIPPED YESTERDAY ══════════════════
# v2801 measured `engines corroborate` at 6,638-13,038 ms in the CHEAP subset and moved it into
# SLOW. The cost was real and the move was wrong, and a cross-family review of the pushed diff is
# what said so: `_eagle_once` calls `run(include_slow=False)`, so SLOW does not mean "runs less
# often" — it means **NEVER RUNS UNATTENDED**. That check is the sole caller of
# `corroborate.verdict()`, which holds every cross-engine invariant there is: owned-is-contained,
# chronicle-owed, swept-split-adds-up, evidence-survived-its-sweep. A 19-vs-2 or 1263-vs-403
# disagreement would have stopped being detected by anything except him pressing the eagle button.
#
# ⚠ THE MIRROR GATE PASSED THE WHOLE TIME. `test_a_check_moved_to_SLOW_is_still_RUN_somewhere`
# asks whether the FULL run still performs it — it does — and that question cannot see the thing
# that was removed, which is the SUPERVISION LOOP. "Runs somewhere" and "runs unwatched" are
# different properties and only one of them was guarded. [[build-the-heart-and-census-everywhere]]
#
# So: SLOW keeps its meaning (on demand only, ~2 minutes, a human is waiting). PERIODIC is the
# honest tier for a check that is too expensive for every ten-minute tick and too important to go
# unwatched — it runs unattended on a longer cadence instead of not at all.
# ⚠⚠ v3355 — "swallowed reads" JOINED PERIODIC BECAUSE THE PUSH GATE REFUSED IT, correctly.
# The row parses every .py in the tree to recount the swallow census, and that costs
# 2,436 / 2,436 / 2,455 / 2,433 ms measured four times on an IDLE machine against a 3,000 ms
# budget. It PASSED a full test_control run minutes earlier and then failed the gate at
# 3,668 ms and 3,272 ms on retry — so the earlier pass was ~550 ms of headroom, not cheapness.
# A check that clears a budget only while nothing else is running is not cheap, it is lucky, and
# the cheap subset runs on the ten-minute timer AND at every console boot.
# ⚠ PERIODIC, not SLOW: SLOW means NEVER RUNS UNATTENDED, and a ratchet nobody reads is the exact
# defect this row was added for — it had been red in CI for ten runs with no surface at all.
# Precedent tier: engines corroborate at 6,638-13,038 ms and sweep would find at 1,660-16,585 ms.
# ⚠ v3393 — "the compare panel can name a difference" JOINED PERIODIC, AND IT IS MY OWN
# REGRESSION. I added it in v3392 and it makes ONE /api/fleet call plus ONE
# /api/fleet_compare PER PEER, each with a 6s timeout. MEASURED: 1,877 ms - roughly 39% of
# the cheap subset, which runs in the BOOT PATH. v3392 squeaked under the 9,000 ms budget
# and v3393 tipped it to 9,591, refusing a legitimate push. A network sweep is not cheap by
# nature and must say so rather than quietly spending the boot budget.
# ⚠ PERIODIC, NOT SLOW. This file says it plainly at :205 - the eagle runs with
# include_slow=False, so "SLOW is exactly where sweep would find went to die". A row moved
# to SLOW stops being supervision. PERIODIC keeps it running on a cadence.
PERIODIC = ("engines corroborate", "sweep would find", "swallowed reads",
            # ⚠ REG-1305 — MEASURED, AND IT REFUSED TWO PUSHES ON 2026-09-25. This row GETs
            # /api/river, which recomputes reel_router over every reel on every call ("recomputed
            # every call, stored nowhere"): 2.2-2.6 s on his idle console at 216 reels, and its own
            # 4 s _get timeout under the gate's load ("4003 ms, again 4002 ms"). MOVED ON MERIT:
            # what it asks - does every stamped station have a name in his vocabulary - changes
            # only when the station keys or the label map change, and both are CODE; a code change
            # re-execs the console and re-runs every row anyway. Hourly loses nothing.
            "the shelf tabs are his stations",
            # 2026-09-28 — the same /api/river GET, for the same reason. Its bar is THREE HOURS, so
            # an hourly look loses nothing, and the every-tick subset pays no 2-4 s river read.
            "triage starved",
            # 2026-09-29 (#58) — reads the whole journal ring and joins ~32 reels (0.40 s measured on
            # his shelf); the ring rotates and the shelf drains on the hour scale, so hourly loses nothing.
            "ledger3 sessions",
            # ⚠⚠ v3462 — THIS ROW SHELLS OUT TO `gh` AND WAS ON THE EVERY-TICK ROSTER.
            # A stalled gh would stall the whole doctor tick — which runs at every console
            # BOOT and on the ten-minute watchdog — so a GitHub hiccup could hold up his
            # console. It also billed a network round trip to the cheap subset that #194
            # is about. The staleness bar is SIX HOURS, so an hourly cadence loses nothing.
            # Found by the cross-family eye on the SHIPPED v3458 bytes.
            "handoff lanes drained",
            # v3467 — reads a per-machine store; its age is measured in DAYS, so hourly
            # loses nothing and the every-tick subset (#194) pays nothing.
            "two eyes compared",
            # v3475 — reads a receipt whose age is measured in days.
            "the seed was checked against his board",
            "the compare panel can name a difference",
            # v3397 — MEASURED 268 ms on this file. The cheap subset runs every eagle
            # tick, and v3392 already cost that subset 1,877 ms by not measuring first.
            "a hidden element is actually hidden",
            # v3402 — MEASURED, NOT ASSUMED, AND MY FIRST NUMBER WAS WRONG. One cold call to this
            # row answered 38.7 ms, which read as free. A/B'd INSIDE the real subset — same
            # process, same population, lower of two passes — it costs 1,249 ms, because the
            # served page is 2 MB and the cheap subset runs on EVERY eagle tick and in the boot
            # path of every console a test spawns. A single isolated call is not the cost of a
            # thing in the loop it lives in. Its sibling above is here for the same reason.
            "his window has a keyboard door",
            # ⚠⚠ v3405 — MOVED ON MERIT, NOT TO GET UNDER A NUMBER. The question PERIODIC asks is
            # "must this be asked every ~10 minutes, or is hourly honest?" — never "which rows are
            # biggest". Both of these are SCANS OF THINGS THAT DO NOT CHANGE BETWEEN TICKS:
            #   · `item vocabulary` re-derives sourceHash FROM THE 28 GB INSTALL to catch a game
            #     patch moving the affix tables. A patch is a monthly event; hashing an install
            #     every ten minutes to notice one is not supervision, it is a treadmill.
            #   · `a worker read has a deadline` greps all of tv/ for a new unbounded
            #     .stdout.readline(). Source only changes when code changes — and a code change
            #     re-execs this console, which re-runs the check anyway.
            # MEASURED in the real subset, lower of two passes: 1,651 ms and 1,494 ms.
            #
            # ⚠ NEITHER GOES TO SLOW, AND v2802 IS WHY. SLOW does not mean "runs less often", it
            # means NEVER RUNS UNATTENDED — `engines corroborate` was moved there for a real cost
            # and stopped being detected by anything except him pressing the eagle button, while
            # the mirror gate passed the whole time. PERIODIC still runs on its own, every
            # PERIODIC_EVERY ticks.
            "item vocabulary",
            "save reader tables",      # #174 — re-derives from the install, same reason as its sibling
            "character sheet data",    # #174 v-B2 — pulls 19 tables from the install (~3 s); a patch is monthly
            "builder item data",       # #174 v-B2 fix round — its sibling: 20 tables from the same install (~3.5 s)
            "mule slot rules",         # #41 rank 15 — its sibling: 4 tables + itemtypes.txt from the same install
            "a worker read has a deadline",
            "no git child steals his screen",
            "the door and the writers agree",
            "the resume agrees with git",
            # v3414 - the census costs ~2.5 s cold; the chip reads it once, 4 s after boot.
            "the chip can say nobody looked",
            # v3415 - 686 ms for the newest 80; the FULL compare is 9,234 ms, over the
            # whole cheap-subset budget. It can only change when an eye writes a row.
            "the eye audit agrees with the gate",
            # ⚠ v3421 — MOVED ON MERIT, AND THE MERIT IS THE CADENCE, NOT THE COST.
            # MEASURED 76 ms median / 115 ms worst at load 14 — small against the cheap
            # subset, and NOT why test_control timed out (that was a 280%-CPU game in the
            # foreground, four orders of magnitude away). So this is not a row hidden to
            # get under a number. The honest question PERIODIC asks is whether a corpse
            # must be caught within ten minutes: it must not. Zombies are the slowest
            # possible signal — 22 HOURS of uptime produced 12 of them — they cost no
            # memory and no cpu, and nothing downstream degrades while one waits an hour
            # to be named. Forking `ps` every eagle tick to watch a thing that moves once
            # an hour is the treadmill this tuple exists to refuse.
            "nothing we started is a corpse",
            # v3422 - it enumerates the whole scratch root (110,447 entries when
            # found). A population that moves over DAYS does not need a ten-minute beat.
            "our scratch is collected",
            # #54 — it parses the whole journal ring (his live file plus five rotated
            # generations) to count sealed reels the ledger owes, and the ledger only moves at
            # a SEAL. A reel seals once an hour; an hourly look loses nothing.
            "equipped ledger files every seal",
            # REG-2202 (#124) — this GETs /api/status, which is 11.6s COLD (0.26s warm), so a cold
            # call tripped the cheap subset's pathological ceiling (BUDGET_MS*5) and flapped the
            # push gate. PERIODIC, not SLOW: a backup loop that fails silently is the "backed up
            # nothing for 18 days" scar, so it MUST keep running unattended — just hourly, off the
            # ten-minute cheap timer. The 15s _get timeout stays; it just no longer races the budget.
            "backup loop",
            # REG-3208 - this GETs /api/status too, and the lane it reads moves every 30 min
            "disk growers",
            "the d2jsp price database is on its tab")
PERIODIC_EVERY = 6      # eagle ticks. The eagle sleeps ~10 min, so this is roughly hourly.

#: ══ REG-2987 (#172) — THE ROWS ASKED IN THE CONSOLE'S OWN PROCESS ══════════════════════════════════════════════════
#: A console sends the eagle's pass to a short-lived child (audit_child.py doctor), so the memory a pass builds leaves
#: with the child. MEASURED 2026-10-29 on a scratch console of his Mac (REG-2985's spike profile): every RSS spike past
#: 450 MB sat inside this pass - corroborate's readings (engines corroborate), the eye audit (ask_an_eye_row), the run
#: census (what runs without you), the evidence tiers and health_engine.report. These rows read the PROCESS they run in,
#: so a child would answer about itself: the serving module's fleet and presence state (_serving_console), this
#: process's modules against the disk, this console's own children, its own paint, the boot installs the console
#: records here (PILLOW_BOOT, NUMPY_BOOT), and a memo kept across ticks (test venue reads Task Scheduler hourly; a child
#: would spawn schtasks every tick). The console asks them itself, after the child, and asks nothing else.
#: test_the_eagles_pass_runs_in_a_child holds every check whose code reads its own process (_serving_console,
#: os.getpid, sys.modules, a record the console sets, a module memo it writes) to this list.
IN_PROCESS = ("a present machine has a fresh last-seen", "no machine went quiet mid-restart",
              "a tally agrees with its own ledger verdict", "a presence reading names its door",
              "a fleet row identifies its machine", "a fleet refusal names an action", "every roster publish is signed",
              "fleet reachable", "picker census", "this process runs the code on disk", "console painted whole",
              "nothing we started is a corpse", "this machine can decode a frame",
              "this machine can cross-check an inventory", "test venue", "this version's CI")


def _slow_path():
    env = os.environ.get("TV_EAGLE_SLOW")
    if env:
        return env
    return os.path.join(HERE, ".eagle_slow.json")


def _load_slow():
    """-> dict | None. None is UNKNOWN. {} is measured-empty (no sidecar yet).

    A missing sidecar is NEVER (no full pass stored). A file that exists and will not
    parse is None — slow_surface still paints NEVER, and must not look like a stored pass.
    """
    p = _slow_path()
    if not os.path.exists(p):
        return {}
    try:
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else None
    except Exception:
        return None


def _persist_slow(rows):
    """CF-12 — the two SLOW checks reach a durable sidecar, not the cheap pass.

    v3298 (#35): PERIODIC rows persist here too (merged by check), so a skipped tick can
    quote a last-known reading with its age. eagle-ran-every-check now expects the SAME
    population on every labelled pass — the not-asked placeholder rows keep the count
    constant, so the old skipped-tick subtraction (and the 53-vs-54 alarm it compensated
    for) retired with the defect. `slow_surface()` stays the SLOW tap.
    """
    # ⚠ v3298 — #35: PERIODIC results persist here too, so a skipped tick can say "last asked
    # <age> ago, last state <s>" instead of nothing. MERGE by check, never replace: a
    # periodic-only pass carries no SLOW rows, and a whole-blob rewrite would erase the
    # last-known SLOW state — the sidecar forgetting a reading it was built to keep. Each row
    # carries its OWN `at`; the top-level `at` (slow_surface's age source) moves only when a
    # SLOW row was actually measured this pass. A `notAsked` placeholder is a row about NOT
    # looking and must never persist as a measurement. [[stale-reading]] [[copy-drift]]
    now = int(time.time() * 1000)
    prev = _load_slow()
    prev = prev if isinstance(prev, dict) else {}
    by = {r.get("check"): dict(r) for r in (prev.get("rows") or []) if isinstance(r, dict)}
    fresh = [dict(r) for r in (rows or [])
             if (r.get("check") in SLOW or r.get("check") in PERIODIC)
             and not r.get("notAsked")]
    for r in fresh:
        r["at"] = now
        by[r["check"]] = r
    slow_here = any(r.get("check") in SLOW for r in fresh)
    blob = {"at": now if slow_here else prev.get("at"),
            "rows": [by[k] for k in sorted(by, key=lambda x: str(x))]}
    p = _slow_path()
    tmp = p + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(blob, fh, indent=1, sort_keys=True)
        os.replace(tmp, p)
    except Exception:
        try:
            os.remove(tmp)
        except Exception:
            pass


def slow_surface(now_ms=None):
    """The two checks the timer never runs, last-known or NEVER. Always len(SLOW) rows.

    Tradeoff: they are not live on the 10-minute pass. They are last-known-with-age, or
    UNMEASURED if no full pass has ever been stored. The cheap `run()` row count stays
    len(CHECKS)-len(SLOW).
    """
    now = int(now_ms if now_ms is not None else time.time() * 1000)
    persist = _load_slow()
    if not isinstance(persist, dict):
        persist = {}
    by = {r.get("check"): r for r in (persist.get("rows") or []) if isinstance(r, dict)}
    at = persist.get("at")
    out = []
    for name in SLOW:
        prev = by.get(name)
        if not prev:
            out.append({
                "check": name, "state": UNMEASURED,
                "why": ("not in the unattended pass (SLOW; ~2 min). never stored from a full "
                        "pass. NEVER, not missing."),
            })
            continue
        age = "UNKNOWN"
        try:
            import unknown_age as _ua
            age = _ua.age_say(at, now)
        except Exception:
            pass
        out.append({
            "check": name,
            "state": prev.get("state"),
            "why": (prev.get("why") or "") + " · last full pass %s ago" % age,
            "lastFullPassTs": at,
        })
    return out


@contextlib.contextmanager
def tick_caches():
    """Prime the per-tick caches exactly as a production tick does, then reset them. -> None

    ⚠⚠ v2815 — THE TIMING GATE WAS MEASURING THE BRANCH THE CONSOLE NEVER TAKES.
    `run()` is the ONLY caller of a check in production, and before iterating CHECKS it primes
    three caches. So `_board_read()` in production ALWAYS returns the cached value:

        if _board_cache["active"]:            <- production: always True, inside run()
            return _board_cache["got"]
        return _post("/api/board_ownership", ...)   <- the gate: always THIS one

    `test_the_cheap_subset_is_actually_CHEAP` calls each check directly and never sets `active`,
    so it exercised the uncached branch exclusively. Roughly 9-15 of ~34 checks read through these
    caches (_board_read ~5, _health_report ~6, _route_read ~4). Break the cached line and every
    real watchdog tick would feed None into five checks forever while the gate stayed green — the
    broken line is simply never executed under test.

    ★ WHY THIS IS A CONTEXT MANAGER AND NOT "MAKE THE GATE CALL run()". run()'s own comment states
    the constraint: "Opened HERE and nowhere else, so a check called on its own still reads fresh —
    which is what every guard that stubs _post expects, and what my first cut broke eight of."
    Calling checks BARE is deliberate and eight guards depend on it. So the priming becomes
    shareable rather than moving, and only the gate that measures TIMING opts in — because timing
    is the one question whose answer differs between the two branches.
    [[feedback-blind-fixture-green-gate]] [[gate-blind-to-unexercised-input]]
    """
    # ⚠ REG-1268 — THE PRIMING NAMES ITSELF TOO. v3500 made a pass say which CHECK it sits in, and the
    # ALT's first live read after it showed the blind spot: "not measured yet", tick 1, and NO
    # `measuring` at all - CURRENT is set only inside the check loop, and these three reads run
    # BEFORE it. A stall here looked exactly like a pass that never started. [[heart-first]]
    CURRENT.update(check="priming: the board-ownership read", since=time.time(), tick=None)
    _board_cache["active"], _board_cache["got"] = True, _post("/api/board_ownership", {"sample": 0})
    # ⚠⚠ v3199 — THE THIRD CACHE WAS MARKED ACTIVE AND LEFT EMPTY, AND THAT IS WHY THE TIMING
    # GATE KEPT ACCUSING INNOCENT CHECKS. Its two siblings above are PRIMED with a real read;
    # this one set `rep = None`, so the first health-backed check to run built the entire report
    # and was billed for all of it. MEASURED 2026-09-16 inside this very context manager:
    #
    #     armed migration, call 1:  3654 ms      <- the whole health report
    #     armed migration, call 2:     0 ms      <- cached
    #     armed migration, call 3:     0 ms
    #     check_armed_migrations() direct:  15 ms (6.4 MB read 7 ms + three regexes at 3 ms)
    #
    # So `armed migration` costs FIFTEEN MILLISECONDS and the gate reported 3,654 — the cost of
    # every other health check, wearing the name of whichever one the roster happened to put
    # first. That is precisely the flapping this file already documented at :3465 ("the name it
    # printed CHANGED EVERY RUN ... each of those was innocent"), and the reason it was never
    # solved is that the note blamed machine bursts while the real mechanism was sitting three
    # lines from the two caches that do it correctly. [[label-outlived-referent]]
    # [[feedback-suspect-the-instrument]]
    #
    # ⚠⚠ PRIMING IT DOES NOT MAKE THE COST GO AWAY AND MUST NOT BE ALLOWED TO. The 3.6 s is REAL
    # and production pays it once per tick. It now lands on the priming, where it can be measured
    # under its own name with its own budget, instead of being charged to a rotating scapegoat.
    # `test_the_cheap_subset_is_actually_CHEAP` asserts exactly that, so this can never become a
    # way of hiding it. [[regression-guard]] [[zero-needs-a-denominator]]
    _health_cache["active"], _health_cache["rep"] = True, None
    CURRENT.update(check="priming: the health report", since=time.time())
    _health_cache["rep"] = _health_report()
    CURRENT.update(check="priming: the route census", since=time.time())
    _routes_cache["active"], _routes_cache["got"] = True, _route_census_once()
    CURRENT.update(check="priming: the reel route", since=time.time())
    _rroute_cache["active"], _rroute_cache["got"] = True, _reel_route_once()
    CURRENT.update(check=None, since=None)
    try:
        yield
    finally:
        _board_cache["active"], _board_cache["got"] = False, None
        _health_cache["active"], _health_cache["rep"] = False, None
        _routes_cache["active"], _routes_cache["got"] = False, None
        _rroute_cache["active"], _rroute_cache["got"] = False, None


# ══ #171 (REG-2480) — AN EYE ROW ASKS ONLY A PC THAT SHIPS ══════════════════════════════════════════════════════════
#: The thirteen rows that grade the SHIP-TIME instrument: the second eye (the cross-family look the pre-push gate takes
#: before a version ships) and the ledger it writes. MEASURED on Dean's PC 2026-10-22 02:44 - a PC that has never
#: shipped a version and whose EYES is Claude-only: two of them MISSING ("there is no binary there" - grok.exe) and the
#: other eleven UNKNOWN, "unaskable for 31d" over an absent ledger. Thirteen rows billing a healthy PC, every tick, for
#: an instrument it does not own.
SHIP_EYE_ROWS = (
    "this machine can get a second opinion", "the eye seat can be filled", "second eye asked twice",
    "eye reach per file", "verdict matches the answer", "a look keeps its evidence",
    "the eye asks for every code extension", "a verdict comes from a declared field", "eye told what was stripped",
    "the eye audit agrees with the gate", "the eye cap is a size it has finished", "the eye answers in a field",
    "two eyes compared")
#: the one reason every eye row gives on a PC that does not ship - ONE predicate, one sentence, never a fifth state word
NOT_SHIPPING_SAY = ("this PC has never shipped a version and has no eye - the second eye is the shipping PC's "
                    "instrument; nothing is owed here")
_EYE_API_HOSTS = ("api.x.ai", "api.openai.com", "api.anthropic.com")


def _ship_git(*args):
    """git for self_prove.tree_state, through this module's own spawn-safe door (git_quiet, a git with a dirname,
    close_fds=False - the console has Quartz loaded, see _spawnable). -> (rc, stdout)"""
    import git_quiet as _gq
    r = _gq.run([_spawnable("git"), "-C", ROOT] + list(args), close_fds=False,
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15)
    return r.returncode, (r.stdout or "").strip()


def this_pc_ships(ledger_path=None, eye_cli=None, tree=None):
    """#171 (REG-2480) — ONE MEASURED PREDICATE: does THIS PC ship versions, and so owe the second eye?
    -> (True | False | None, why)

    True   its second-eye ledger exists, OR its eye binary exists (an eye configured as an API counts), OR its tree is
           a development tree (self_prove.tree_state says 'dev' - the pre-push gate proves and ships from it)
    False  all three were READ and none holds: it has never shipped and has no eye
    None   one of them could not be read - and then nothing is relabelled; every eye row asks its own question, as before

    The seams: `ledger_path` and `eye_cli` default to second_eye_ledger.LEDGER_PATH and second_eye_run.EYE_CLI, read
    at call time; `tree` is a callable -> (kind, why), default self_prove.tree_state through _ship_git. Asked in the
    order that costs least: two stats first, and git only on a PC with neither a ledger nor an eye.
    [[unknown-stays-unknown]] [[per-pc-personal-data]]"""
    said = []
    try:
        if ledger_path is None:
            import second_eye_ledger as _sel
            ledger_path = _sel.LEDGER_PATH
        os.stat(ledger_path)
        return True, "its second-eye ledger exists (%s)" % os.path.basename(str(ledger_path))
    except (FileNotFoundError, NotADirectoryError):
        said.append("no second-eye ledger (%s)" % os.path.basename(str(ledger_path)))
    except Exception as e:
        return None, "the second-eye ledger could not be read (%s)" % type(e).__name__
    try:
        if eye_cli is None:
            import second_eye_run as _eye
            eye_cli = getattr(_eye, "EYE_CLI", "") or ""
        eye_cli = str(eye_cli or "")
        if eye_cli and ("://" in eye_cli or any(h in eye_cli for h in _EYE_API_HOSTS)):
            return True, "an eye is configured here as an API (%s)" % eye_cli
        if eye_cli:
            os.stat(eye_cli)
            return True, "its eye binary exists (%s)" % _ntpath_base(eye_cli)   # a basename: never a home path
        said.append("no eye configured")
    except (FileNotFoundError, NotADirectoryError):
        said.append("no eye binary (%s)" % _ntpath_base(eye_cli))   # REG-2480 round 2: a basename, never a home path
    except Exception as e:
        return None, "whether an eye is on this PC could not be read (%s)" % type(e).__name__
    try:
        if tree is None:
            import self_prove as _sp
            kind, twhy = _sp.tree_state(git=_ship_git)
        else:
            kind, twhy = tree()
    except Exception as e:
        return None, "whether this tree ships could not be read (%s)" % type(e).__name__
    if kind == "dev":
        return True, "its tree is a development tree (%s)" % twhy
    if kind != "installed":
        return None, "whether this tree ships could not be read (%s)" % twhy
    said.append(twhy)
    return False, "; ".join(said)


def ask_an_eye_row(fn, ships=None):
    """#171 — an eye row as the eagle asks it. -> (state, why)

    On a PC this_pc_ships() MEASURED as not shipping: OK, with the one reason and what was measured. Anywhere else -
    a PC that ships, or one whose answer could not be read - the row's own question, exactly as before. `ships` is
    this_pc_ships()'s answer, asked here when None."""
    s, swhy = ships if ships is not None else this_pc_ships()
    if s is False:
        return OK, "%s (measured: %s)" % (NOT_SHIPPING_SAY, swhy)
    return fn()


def run(include_slow=True, include_periodic=None, tick=None, only=None, skip=None):
    """-> rows. `include_periodic` defaults to `include_slow` so every existing caller keeps its
    exact behaviour; the eagle passes it explicitly on its own cadence. `tick` is the eagle's
    tick counter (v3298) — without it a skipped PERIODIC row says next-ask UNKNOWN, never a
    guessed number.

    REG-2987 (#172) - a PART of the roster, for a pass split between a child and the console: `skip` names checks that
    emit no row at all (the child skips IN_PROCESS), `only` names the only checks asked (the console asks IN_PROCESS).
    A part never reaches a check another part asks, not even as a not-asked row. `only` primes no per-tick cache: no
    IN_PROCESS row reads one, and the priming (his board read, the health report) is what the child is for."""
    if include_periodic is None:
        include_periodic = include_slow
    rows = []
    # v2277 — ONE TICK, ONE READ OF HIS BOARD. Three checks need /api/board_ownership and that
    # route EVALUATES JAVASCRIPT IN THE WINDOW HE IS LOOKING AT; asking three times buys nothing.
    # Opened HERE and nowhere else, so a check called on its own still reads fresh — which is what
    # every guard that stubs _post expects, and what my first cut broke eight of.
    # v2815 — THROUGH tick_caches(), so the gate that measures this tick's cost can prime it the
    # same way instead of timing a different branch. One source; a divergence is now impossible
    # rather than merely unlikely.
    with (tick_caches() if only is None else contextlib.nullcontext()):
        _last = _load_slow()
        _last = _last if isinstance(_last, dict) else {}
        _last_by = {r.get("check"): r for r in (_last.get("rows") or []) if isinstance(r, dict)}
        _ships = []         # #171 - this_pc_ships(), asked once per pass by the first eye row
        for name, fn in CHECKS:
            if (only is not None and name not in only) or (skip and name in skip):
                continue        # REG-2987 another part of this pass asks it
            if not include_slow and name in SLOW:
                continue
            if not include_periodic and name in PERIODIC:
                # ⚠ v3298 — #35: A SKIPPED PERIODIC CHECK EMITS A ROW, NEVER SILENCE. On 5 of
                # every 6 eagle ticks this branch used to `continue`, so the check vanished from
                # the pass entirely — indistinguishable from a check nobody wrote. 'engines
                # corroborate' is the SOLE caller of corroborate.verdict(), so every tick it was
                # absent was supervision downtime wearing the shape of a clean board. The row is
                # UNMEASURED (this tick did not look), the WHY carries the cadence, the next ask,
                # and the last-known reading off the sidecar — a reading carries the age of the
                # thing it measured. [[stale-reading]] [[unknown-stays-unknown]]
                _nxt = "next ask tick UNKNOWN — caller passed no tick"
                if isinstance(tick, int) and tick > 0 and PERIODIC_EVERY:
                    _nxt = "next ask in %d tick(s)" % (PERIODIC_EVERY - (tick % PERIODIC_EVERY))
                _why = "not asked this tick (PERIODIC — every %d eagle ticks; %s)" % (
                    PERIODIC_EVERY, _nxt)
                _prev = _last_by.get(name)
                if _prev:
                    _age = "UNKNOWN"
                    try:
                        import unknown_age as _ua
                        _age = _ua.age_say(_prev.get("at") or _last.get("at"),
                                           int(time.time() * 1000))
                    except Exception:
                        pass
                    _why += " · last asked %s ago, last state %s" % (_age, _prev.get("state"))
                else:
                    _why += " · never asked since the sidecar began. NEVER, not missing."
                # ⚠⚠ v3309 (#35) — PERSIST THE DISTINCTION, DO NOT MAKE THE SCREEN RE-DERIVE IT
                # FROM PROSE. His screenshot: "ENGINES CORROBORATE **NEVER** — not asked this tick
                # ... last asked 2m ago, last state missing". The SENTENCE was right and the WORD
                # was wrong, because the panel maps `unmeasured` to NEVER unconditionally and the
                # payload gave it no way to tell the two cases apart. They are different facts:
                #   everAsked False -> genuinely NEVER asked since the sidecar began
                #   everAsked True  -> asked before, just NOT ON THIS TICK; it carries its last
                #                      verdict and its age, and does NOT bill him (his #35 rule)
                # A reader that has to parse a sentence to recover a fact the writer already knew
                # is the defect heart-first rule 6 is about. [[label-outlived-referent]]
                rows.append({"check": name, "state": UNMEASURED, "why": _why,
                             "notAsked": True,
                             "everAsked": bool(_prev),
                             "lastState": (_prev.get("state") if _prev else None),
                             "surfaces": list(WATCHES.get(name, ())),
                             "ms": None})
                continue
            t0 = time.time()
            CURRENT.update(check=name, since=t0, tick=tick)
            try:
                if name in SHIP_EYE_ROWS:
                    # #171 (REG-2480) - one predicate per pass, asked by the first eye row (whose ms carries it)
                    if not _ships:
                        _ships.append(this_pc_ships())
                    state, why = ask_an_eye_row(fn, _ships[0])
                else:
                    state, why = fn()
            except Exception as e:
                state, why = UNKNOWN, "this check itself threw: %s" % str(e)[:120]
            # v3404c — THE WHOLE IS MINUTES AND EVERY PART IS SECONDS. RESUME_HERE named this
            # unfinished: cd.run(include_slow=False) > 8 min, 93 checks timed standalone ~24s.
            # Without a duration ON THE ROW, the next hang cannot name which check sat, so the
            # bound takes the blame again. Persist ms. None is not-asked, never 0.
            # [[heart-first]] [[unknown-stays-unknown]]
            _ms = int(round((time.time() - t0) * 1000))
            # ⚠ THE SAME DECLARATION run() PUBLISHES, because the EAGLE is this doctor's
            # run output: control_app._eagle_once() calls _cd.run() and stores the rows,
            # and organ_matrix reads them as the eagle's answer. Without this the eagle
            # column stays UNKNOWN forever while the doctor's resolves — two columns
            # disagreeing about one organ's vocabulary. [[copy-drift]]
            rows.append({"check": name, "state": state, "why": why,
                         "surfaces": list(WATCHES.get(name, ())),
                         "ms": _ms})
    CURRENT.update(check=None, since=None, tick=None)     # the pass is over: nothing is running
    # #226 — every row carries its declared questions BEFORE it is banked or partitioned
    attach_asks(rows)
    if include_slow or include_periodic:
        _persist_slow(rows)   # v3298 — periodic-inclusive passes bank their reading too
    try:
        import unknown_age as _ua
        _ua.attach(rows)
    except Exception:
        pass
    return rows


#: ══ WHAT EACH CHECK WATCHES, IN THE REGISTRY'S OWN WORDS ═════════════════════════════════════
#: organ_matrix measured the gap plainly: "doctor names 59 thing(s), and NONE of them resolves to
#: any of the 58 surfaces — it is naming a different KIND of thing (concerns, not code objects)".
#: A check is called "shelf lanes reading"; a surface is called "shelf-cards". Those never meet,
#: so the doctor's entire column read UNKNOWN while the doctor itself worked perfectly.
#:
#: ⚠⚠ IT CANNOT BE DERIVED, AND THAT WAS MEASURED BEFORE IT WAS AUTHORED. A first attempt parsed
#: each check's body for unambiguous surface-shaped tokens (dotted, hyphenated, /api/ and #id
#: forms). Result on a 12-check sample: 4 reached anything at all, and what they reached was
#: `control_app.py`, `status`, `per-lane`, `REG-415` — not one registry surface. The relationship
#: simply is not present in the code, so no parser can find it. It has to be stated.
#:
#: ⚠ SO EVERY ENTRY HERE IS A CLAIM, AND THE RULES KEEP IT HONEST:
#:   · a check absent from this map FAILS THE GATE — silence is never "covers nothing";
#:   · a check that genuinely watches no registry surface declares an EMPTY tuple, on purpose,
#:     and reads ABSENT. Under-claiming is the intended bias: organ_matrix's own rule is that a
#:     table reporting coverage it cannot demonstrate is worse than the empty one he was shown;
#:   · a declared name that is not in the registry FAILS THE GATE — a typo would otherwise sit
#:     here forever matching nothing and looking like considered coverage.
#: [[unknown-stays-unknown]] [[the-unjoined-end]] [[source-reading-guard]]
WATCHES = {
    # ⚠⚠ v3409 — THREE OF MINE SHIPPED INTO CHECKS WITHOUT A DECLARATION HERE, AND THE
    # CROSS-FAMILY REVIEW OF v3404 IS WHAT CAUGHT THEM. `set(CHECKS) - set(WATCHES)` must be
    # empty; a MISSING key reads ABSENT in the organ table, which is indistinguishable from a
    # check nobody wrote — the exact state v3190 and v3340 were carved over. The empty tuple is
    # not an omission, it is the honest DECLARATION that the row owns no element of its own.
    # v3406 — it drives one stubbed call at the real sweep door and grades the harness that
    # scores it; there is no element of its own.
    "sweep attack reaches its door": (),
    # v3407 — it counts git argv sites in source text; no element of its own.
    "no git child steals his screen": (),
    # v3408 — it asks whether THIS machine has a CLI eye on disk; no element of its own.
    "this machine can get a second opinion": (),
    # #227 — DECLARED, NOT OMITTED. It decodes a BMP in memory; no element of its own.
    "this machine can decode a frame": (),
    # REG-1719 — DECLARED, NOT OMITTED. It imports numpy and takes one median; no element of its own.
    "this machine can cross-check an inventory": (),
    # #105 — DECLARED, NOT OMITTED. It reads the journal tail through _reader_health; its element is the lamps under
    # the corner chip (#reader-lamps), which the same measure paints.
    "this machine's reader can read": (),
    # v3410 — DECLARED, NOT OMITTED. It compares two module paths; no element of its own.
    "the door and the writers agree": (),
    # v3413 — DECLARED, NOT OMITTED. It compares a generated file against git; no element.
    "the resume agrees with git": (),
    # #123 — was ("heart-chip",): a DOM id, not a registry surface, so it could never match and sat
    # here looking like coverage (test_the_doctor_says_what_it_watches, red since v3414). The row
    # supervises heart_state()'s census — the payload the `heart` surface renders; the chip only
    # opens it.
    "the chip can say nobody looked": ("heart",),
    "the eye audit agrees with the gate": (),
    "the eye cap is a size it has finished": (),
    "the eye answers in a field": (),
    "the eye seat can be filled": (),
    "the hunt names a quicker route": (),
    "the board build door is open": (),
    "this process runs the code on disk": (),
    "nothing we started is a corpse": (),
    "our scratch is collected": (),
    # ⚠ v3190 — FILED WITH ITS CHECK, WHICH IS THE POINT OF THIS MAP. `check_stash_bank` shipped
    # into CHECKS with the vault_bank reader and was never declared here, so it read ABSENT in the
    # organ table for a version — a claim nobody made, indistinguishable from a check nobody
    # wrote. The empty tuple is the honest answer and a DECLARATION: vault_bank reads the sweep's
    # own accumulation off disk and renders on no screen of its own yet.
    # v3378 (#28) — DECLARED, NOT OMITTED. This row has no element of its OWN: it grades the
    # `owes` sentence the shelf already renders per reel, so the empty tuple is the honest answer
    # and saying so is what keeps it out of the ABSENT column v3340 was carved over.
    # v3379 (#128) — DECLARED, NOT OMITTED. It grades what the fleet card already renders per
    # peer, so it owns no element of its own and the empty tuple is the honest answer.
    # v3380 — DECLARED, NOT OMITTED. It grades source text across tv/, so it owns no element
    # of its own and the empty tuple is the honest answer.
    # v3381 — DECLARED, NOT OMITTED. It grades source text, so it owns no element of its own.
    # v3384 — DECLARED, NOT OMITTED. It reads the presence cache, not an element.
    "a look keeps its evidence": (),
    # v3387 — DECLARED, NOT OMITTED. It reads the presence cache and the UI source, not an element.
    # v3388 — DECLARED, NOT OMITTED. It reads a source pathspec and git, not an element.
    # v3389 — DECLARED, NOT OMITTED. It reads the presence cache, not an element.
    # v3390 — DECLARED, NOT OMITTED. It reads the presence cache, not an element.
    "a present machine has a fresh last-seen": (),
    "no machine went quiet mid-restart": (),
    "this console starts at sign-in": (),
    "a tally agrees with its own ledger verdict": (),
    "the eye asks for every code extension": (),
    "a presence reading names its door": (),
    "a fleet row identifies its machine": (),
    "a fleet refusal names an action": (),
    # #95 — DECLARED, NOT OMITTED. It reads the publish receipt and the roster cache; the panel
    # line it supervises is drawn by roster_html, which is no registry surface of its own.
    "every roster publish is signed": (),
    "a worker read has a deadline": (),
    "no browser is launched unreaped": (),
    "fleet can name what it counts": (),
    "the compare panel can name a difference": (),
    "this console tree is established": (),
    # v3404 — DECLARED, NOT OMITTED. It reads git (behind + FETCH_HEAD age), not a screen
    # element, so the empty tuple is the honest answer. Shipping the check without this
    # line made the organ table claim ABSENT for a row nobody had described.
    "this machine keeps itself current": (),
    # #64 — DECLARED, NOT OMITTED. It reads the pull lane, which runs inside the drift beat.
    "this checkout can update": ("_drift_loop",),
    "a verdict comes from a declared field": (),
    "a queue zero came from a read that worked": (),
    "river owes what its engine says": (),
    "stash bank":                  (),
    # ⚠ v3340 — DECLARED, NOT OMITTED, and it was omitted first. v3333 added `reel clocks` as
    # the HEART half of #80 and never entered it here, so the organ table read ABSENT for it —
    # a claim nobody made, indistinguishable from a check nobody wrote. CI said so within hours,
    # and the net count hid it: 27 -> 27, because that ship fixed two gates and broke two.
    # The empty tuple is the honest answer: this row has no screen element of its OWN. It asks
    # whether every reel on disk can still yield an epoch from its id, and it reaches him through
    # the eagle line rather than through a element of its own.
    "reel clocks":                  (),
    # v3304 (#55/#38) — the interlock has no screen element of its OWN yet. The empty tuple is a
    # DECLARATION, not an omission (see the note above this map): its state reaches him through
    # the eagle row and relaunch_hold_state()'s shared on/worked/lastTs/owed contract, not through
    # a element id anyone can point at. When it gets a lamp, name it here.
    "relaunch green light":        (),
    # 2026-09-28 — DECLARED, NOT OMITTED. It compares the running stamp (over the wire) against the
    # disk literal; no element of its own — it reaches him through the eagle row.
    "the running build is behind the disk": (),
    # v3310 — the ledger is a file, not a screen. Empty tuple as a DECLARATION, not an omission.
    # ⚠⚠ v3363 — WAS ("th-shelfov",) AND THAT WAS A CATEGORY ERROR OF MINE IN v3359. This
    # registry is `organ_matrix.surfaces()`, derived from render targets, valves, routes and
    # vessels — 60 names, and MEASURED: ZERO of them are DOM element ids. `th-shelfov` is a real
    # element (control_ui.html:7611) and was never a registry surface, so the declaration could
    # match nothing and sat there for four versions looking exactly like considered coverage —
    # the precise failure `test_every_declared_surface_is_a_real_surface` exists to catch.
    # ⚠ AND IT WAS INVISIBLE ON EVERY ONE OF THOSE PUSHES: the pre-push derives its gates from
    # CHANGED TEST FILES, and nothing since v3359 touched that law. A sample is not a verdict.
    # [[regression-guard]] §1
    # ⚠ THE EMPTY TUPLE IS THE HONEST ANSWER, not a smaller lie. `shelf-cards`, `shelf.rows` and
    # `shelf.scene` are all real surfaces — and this row CONSULTS NONE OF THEM. It reads the
    # assembly order out of the source. Naming a surface it never asks would be the over-claim
    # this law's own docstring rules against: under-claiming is the intended bias.
    "shelf order and guard":       (),
    # v3355 — a source census, not a screen. Empty tuple as a DECLARATION, not an omission.
    "swallowed reads":             (),
    "second eye asked twice":      (),
    # v3463 — v3458 registered this row in CHECKS and PERIODIC and never declared it here, so
    # CI's test_no_check_is_missing_from_WATCHES went red on the version that shipped it. It
    # reads two GitHub lanes (#230 watermark, #231 ledger) and owns no element of its own:
    # empty tuple as a DECLARATION, not an omission.
    "handoff lanes drained":       (),
    # v3467 — a per-machine store and a reducer; no element of its own. DECLARED.
    "two eyes compared":           (),
    # v3475 — reads a receipt file; no element of its own. DECLARED.
    "the seed was checked against his board": (),
    # v3363 (#114) — the reach map is a LEDGER FIELD, not a screen element. Empty tuple as a
    # DECLARATION, not an omission: it reaches him through the eagle line, and the day it gets
    # a lamp of its own, name it here.
    "eye reach per file":          (),
    # v3375 (#122) — no lamp of its own; it reaches him through the eagle line, same as its
    # sibling above. Empty tuple as a DECLARATION, not an omission.
    "eye told what was stripped":  (),
    # v3376 (#125) — no lamp of its own; reaches him through the eagle line. DECLARATION.
    "verdict matches the answer":  (),
    # v3364 (#60) — the lexicon is a generated FILE and a classifier, with no screen
    # element of its own. Empty tuple as a DECLARATION, not an omission: it reaches him
    # through the eagle line today, and through the unsure rows once they render a vocab.
    "item vocabulary":             (),
    "save reader tables":          (),
    # #174 v-B2 — a generated block inside bible.html, read by the engine; no element of its own. DECLARED.
    "character sheet data":        (),
    # #174 v-B2 fix round — the builder's CB_DB block, a generated block with no element of its own. DECLARED.
    "builder item data":           (),
    # #41 rank 15 — the mule window's MULE_BASE_* blocks, generated into bible.html with no element of their own. DECLARED.
    "mule slot rules":             (),
    # #41 rank 12 — reads three of the board's stores through the shared tick read. Its elements (#tab-chars,
    # #chars-list) live on the BOARD, which this registry (organ_matrix surfaces, console-side) does not list; it
    # reaches him through the eagle line. Empty tuple as a DECLARATION, not an omission.
    "characters room":             (),
    # #36 (REG-2909) - reads the learner's ledger and the reel folders; its ask reaches him through the eagle line, and
    # the holders it explains are drawn on the vault's looks (REG-2908). No element of its own: DECLARED, not omitted.
    "which character each session is on": (),

    # #41 rank 16 (REG-1560) — reads the receipt the tvd-tooltip-oracle lane writes; that loop is the vessel it watches.
    "their tooltip rows":          ("_tooltip_oracle_loop",),
    # #54 — reads the equipped ledger against the console's own journal ring (equipped_ledger.contract); it owns no
    # element of its own and reaches him through the eagle line. Empty tuple as a DECLARATION, not an omission.
    "equipped ledger files every seal": (),
    # #41 rank 22 (REG-1564/1584) — reads the fleet roster cache and this console's banked census (_picker_for_wire);
    # it owns no loop of its own and reaches him through the fleet card's picker line and the row's word.
    # Empty tuple as a DECLARATION, not an omission.
    "picker census": (),
    # #246 W7 — reads the board's stores through the shared tick read; it owns no element of its own and
    # reaches him through the eagle line. Empty tuple as a DECLARATION, not an omission.
    "vault provenance":            (),
    # 2026-09-28 — both read stores and files through shared reads; neither owns a screen element of its own.
    # Empty tuples as DECLARATIONS, not omissions.
    "a vault item with no provenance": (),
    "a read left no picture":      (),
    # 2026-09-29 (#55) — reads five stores through their owners' loaders; no element of its own yet (the
    # custody map is a later slice). Empty tuple as a DECLARATION, not an omission: it reaches him through
    # the eagle line, and /api/custody answers per reel.
    "reel custody":                (),
    # 2026-09-27 — the reset receipt and the tier census. Neither owns a screen element of its
    # own; both reach him through the eagle line. Empty tuple as a DECLARATION, not an omission.
    "vault reset receipt":         (),
    "evidence tiers":              (),
    # 2026-09-29 (#58) — the Ledger 3.0 record is served on GET /api/ledger3/session and has no
    # console element yet (the 📒 room is a later slice). Empty tuple as a DECLARATION, not an omission.
    "ledger3 sessions":            (),
    # v3365 (#24) — the fault ledger is a FILE. Empty tuple as a DECLARATION, not an
    # omission: it reaches him through the eagle line, not through an element of its own.
    "fault evidence":              (),
    # v3366 (#115) — a folder on disk, with no element of its own. Empty tuple as a
    # DECLARATION: it reaches him through the eagle line.
    "capture root live":           (),
    # v3368 (#60) — a STORE field, no element of its own yet. Empty tuple as a
    # DECLARATION: it reaches him through the eagle line until the vault panel shows it.
    "item facts captured":         (),
    "running code matches disk":   (),                       # code integrity, not a surface
    # ⚠ v3098 — AND THIS ONE IS NOT `()` LIKE ITS SIBLING ABOVE, WHICH IS THE WHOLE POINT OF THE
    # PAIR. "running code matches disk" compares this PROCESS's modules to the files; it never
    # involves a screen. This check compares the DOCUMENT THE WEBVIEW IS RENDERING to the file on
    # disk — the only reading that can tell him the page in front of him is stale — so the panels
    # it can speak for are the rendered console itself. Missing entirely until now, which left
    # `test_the_doctor_says_what_it_watches` RED on the tree.
    "window runs the document on disk": ("console", "page"),
    "shelf lanes reading":         ("shelf-cards",),
    # v3232 — filed WITH its check, which is the point of this map. `_check_the_shelf_tabs_are_alive`
    # asks /api/river and compares the stamped population against the label map, so what it covers
    # is the station-chip row on the SHELF and the river strip those chips are drawn from. Named,
    # not empty: this check does render on a screen he opens, which is why it exists at all.
    # ⚠ v3257 — `sh-stationbar` JOINED. It is the element this row is actually named after: the
    # station chips he reads the river off. It was painted, it could state a falsehood about the
    # whole system (it told him "NO reel has reached JOIN" while 14 reels sat at JOIN with none
    # ever leaving), and no organ named it. A surface that can lie earns a watcher - that is the
    # heart's own rule, and the gap was on the one surface this check exists for.
    # ⚠ v3313 (#63) — `sh-stationbar` WAS DECLARED HERE AND NEVER MATCHED ANYTHING. This map
    # speaks SURFACE names (organ_matrix.surfaces(), 60 of them); `sh-stationbar` is a DOM id in
    # control_ui.html. Two vocabularies in one map, so the entry read as considered coverage while
    # providing none — the exact green that lies `test_every_declared_surface_is_a_real_surface`
    # exists to catch, and it HAS been red for it. Not a typo: there is no near-match in the
    # registry (closest are `shelf-cards`, `state-panel`, `heart-stored`), and no surface contains
    # "station" at all. Removing it loses NO coverage because it never provided any, and the
    # station bar is painted inside `shelf-cards`, which is still declared.
    # ⚠ THE INTENT IS KEPT AS A NOTE RATHER THAN AS A DEAD DECLARATION: if the station bar should
    # be watched in its own right, it needs a SURFACE in organ_matrix first — and adding one
    # creates a real obligation for every organ to name it, which is a deliberate act, not a
    # side effect of fixing a registry gap.
    "the shelf tabs are his stations": ("shelf-cards", "river-strip", "console-tabs"),
    # v3247 — the chip renders on the BOARD (bible.html), which this console does not paint, so
    # it names no console surface. The empty tuple is a DECLARATION, not an oversight: what this
    # check watches is the DOOR that feeds it, and that door has no id of its own.
    "the vault can say what it proves": (),
    "fleet reachable":             ("advanced-fleet", "advanced-fleet-down"),
    "armed migration":             (),
    "extraction lanes":            (),
    "shadow watch":                ("advanced-shadow", "_shadow_watch_loop"),
    "readers agree":               (),
    "board join":                  (),
    "stray processes":             ("_orphan_watch", "_orphan_exit_loop"),
    "engines corroborate":         (),
    "panels on screen":            ("console", "page"),
    "test venue":                  (),
    "reader switch":               ("advanced",),    # #151 - the 👁 EYES card under ⚙ ADVANCED
    "river joints":                ("river-strip",),
    "river outlet":                ("river-strip",),
    "vault proposal":              ("vault.apply",),
    "console UI faults":           ("console",),
    "version drift":               ("_drift_loop",),
    "behind the fleet":            ("advanced-fleet",),
    "lane intent":                 (),
    "what runs without you":       (),
    "disk headroom":               ("prune.reports",),
    # REG-3208 - DECLARED, NOT OMITTED. It reads the growers lane from /api/status; no element of its own.
    "disk growers":                (),
    "subscription":                (),
    "unattended reel":             (),
    "reel extract":                ("reel.route",),
    "hunt economy":                (),
    "sweep would find":            ("vault.sweep_start",),
    "board is claimed":            (),
    "ledger provenance":           (),
    "ledger staleness":            ("_ledger_backup_loop",),
    "visual lock":                 (),
    "art corpus":                  (),
    "footage has a reel":          ("reel.route",),
    "vault stores":                ("vault", "vault-full"),
    "evidence ledger":             (),
    "ledger backup":               ("_ledger_backup_loop",),
    "backup loop":                 ("_ledger_backup_loop",),
    # REG-3213 (v3865) - it reads /api/status.ciWatch (the console's CI tick) and reaches him through the eagle line; it
    # owns no element of its own. Empty tuple as a DECLARATION, not an omission.
    "this version's CI":           (),
    "ledger drop":                 ("_ledger_backup_loop",),
    "console painted whole":       ("console", "page"),
    "names banked":                (),
    "read names lane":             (),
    "stage shows the dom":         (),
    "river walk":                  ("river-strip",),
    # 2026-09-27 — the drain contract rides /api/status.retention.drain and reaches him through the
    # eagle line; it owns no element of its own. Empty tuple as a DECLARATION, not an omission.
    "retention drain":             (),
    # 2026-09-28 — it watches the LOOP that walks TRIAGE reels (its refusals, its last walk).
    "triage starved":              ("_retro_triage_loop",),
    "route stash":                 (),
    "route chronicle \u00b7 sets":    ("chronicle.set",),
    "route chronicle \u00b7 uniques": ("chronicle.unique",),
    "route inventory":             (),
    "printer reach":               ("printer.stream",),
    "end routes reachable":        (),
    "the river":                   ("river-strip",),
    "screen still painting":       ("console",),
    # v3313 (#63) — `reel population` shipped into CHECKS and was declared in NEITHER registry,
    # which turned TWO gates permanently red for one omission. Its three numbers (the river shows
    # 8, the console's onDisk shows 12, the disk holds 20) land on exactly these two surfaces, so
    # this is a MEASUREMENT of where it renders, not an empty declaration.
    "reel population":             ("shelf-cards", "river-strip"),
    "shelf is where it says":      ("shelf-cards",),
    "progress number":             (),
    "ledger entries":              (),
    "store emptied":               (),
    "shadow gate":                 ("advanced-shadow",),
    # #228 — its numbers are the sets roster's, the surface the Remaining page is filmed from
    "a fresh remaining page":      ("chronicle.set",),
    "locked lanes":                ("locks",),
    "his gear":                    ("vault",),
    "tooltip finder":              (),
    "surfaces agree":              (),
    "the other doctors":           (),
    # v3397 — DECLARED, NOT OMITTED. It grades the served stylesheet, so it owns no
    # element of its own and the empty tuple is the honest answer.
    "a hidden element is actually hidden": (),
    # v3398 — DECLARED, NOT OMITTED. It grades the native window frame, which is not an
    # element on any page, so the empty tuple is the honest answer.
    "his window can be measured": (),
    # v3402 — DECLARED, NOT OMITTED. It grades the served script, so it owns no element of its
    # own and the empty tuple is the honest answer.
    "his window has a keyboard door": (),
    "the d2jsp price database is on its tab": (),
    # #87 (REG-3253) - it asks the lamp's opener for its command and reads the profile's own settings; no element of its own.
    "the Mac signs in to d2jsp through its own window": (),
    # #85 (REG-3269) - it reads the page's picture map and checks art/ on disk; no element of its own.
    "quick wins places have their pictures": (),
    "a windowed frame is read inside its game": (),
    # REG-3218 - DECLARED, NOT OMITTED. It reads the board lane's record (a file the console writes); the board it judges is
    # a page on the site, not a registry surface, so the empty tuple is the honest answer.
    "the board agrees with the tree": (),
}


def report(deep=False):
    """The organ interface — what this doctor WATCHES. -> {"ok", "rows", "why"}

    Every other organ publishes one of these (`health_engine.report()`,
    `control_app.eagle_state()`), and until v2496 this one did not, so `organ_matrix` answered
    "console_doctor has no report()" and painted the doctor's column UNKNOWN across all 44
    surfaces — a quarter of that table unanswerable because one function was absent.

    ⚠⚠ IT DOES NOT RUN THE CHECKS BY DEFAULT, AND THAT IS THE DESIGN, NOT A SHORTCUT.
    `run()` opens /api/board_ownership, and that route EVALUATES JAVASCRIPT IN THE WINDOW HE IS
    LOOKING AT [[borrowed-surface]]; the two SLOW checks add ~2 minutes on top. An organ asked
    "what do you watch?" must be able to answer without reaching into his screen, because the
    asker — a matrix, the heart, a status poll — is asking about COVERAGE, not about findings.
    Pass deep=True when you want the live states; that is `run()`, and it answers a different
    question.

    So every row here carries state UNMEASURED, which is a real state in this module's own
    vocabulary and NOT a pass: it says this check exists and was not run just now.
    [[unknown-stays-unknown]] — the gap between "we did not look" and "we looked and it was
    fine" is the whole point of having a separate word for it.
    """
    if deep:
        rows = run()
        return {"ok": True, "rows": rows,
                "why": "%d check(s), run live just now" % len(rows)}
    rows = []
    for name, _fn in CHECKS:
        rows.append({
            # ⚠ `check` IS THIS MODULE'S WORD AND IT STAYS. The matrix learned to read it
            # (v2496) rather than this file learning to speak someone else's vocabulary — a
            # synonym list belongs in the READER, or every organ ends up carrying a second
            # copy of its own name for each consumer. [[copy-drift]] §1
            "check": name,
            # ⚠ THE ORGAN'S OWN ANSWER TO "WHAT DO YOU WATCH", in the registry's vocabulary.
            # Declared in WATCHES above, never inferred here: an empty list means this check
            # genuinely covers no registry surface, and a MISSING key fails the gate rather
            # than defaulting to empty. [[unknown-stays-unknown]]
            "surfaces": list(WATCHES.get(name, ())),
            "slow": name in SLOW,
            "owner": owner_of(name),
            "state": UNMEASURED,
            "why": ("named by this doctor; not run by this call. UNMEASURED, not OK — "
                    "pass deep=True to run it."),
        })
    return {"ok": True, "rows": rows,
            "why": ("%d check(s) named without running any of them, because running them "
                    "reaches into the window he is looking at" % len(rows))}


def main(argv):
    rows = run()
    if "--json" in argv:
        print(json.dumps({"ok": True, "checks": rows,
                          "generatedTs": int(time.time() * 1000)}, ensure_ascii=False))
        return 0
    print("\n🦅 EAGLE EYE — the whole console, from above\n")
    for r in rows:
        print("  %s %-18s %s" % (ICON.get(r["state"], "⚪"), r["check"], r["why"]))
    # v2284 — split by OWNER before counting. His number must mean "things you can do".
    needs = [r for r in rows if r["state"] == MISSING and owner_of(r["check"]) == "you"]
    mine = [r for r in rows if r["state"] == MISSING and owner_of(r["check"]) == "me"]
    unk = [r for r in rows if r["state"] == UNKNOWN]
    print()
    if needs:
        print("⚠ %d thing(s) need you. Nothing above is a guess: each line names what it measured."
              % len(needs))
    if mine:
        # ⚠ SHOWN, NOT SWALLOWED. These are real and red; they are simply not his to do, and each
        # one names the task that owns it so "mine" cannot become a place things go to be forgotten.
        print("🔧 %d known defect(s) — mine, already queued, not yours to do:" % len(mine))
        for r in mine:
            print("     %-18s %s" % (r["check"], MINE.get(r["check"], "")))
    if needs or mine:
        pass
    elif unk:
        print("✅ nothing is out of line. %d check(s) could not be determined — that is not a pass, "
              "it is a gap." % len(unk))
    else:
        print("✅ every check green.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
