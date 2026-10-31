#!/usr/bin/env bash
# 📺 TV DIABLO — Mac launcher (Desktop app · v1379.1 native pywebview window)
# Real OS app window (not Chrome). Agent stays hidden behind ON/OFF/STOP/RESTART/SIM.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$HOME/Library/Python/3.9/bin:$PATH"
# user-site packages (pywebview) for system python3
export PYTHONPATH="${PYTHONPATH:-}"
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN 2>/dev/null || true
# v927.2 — arm the local Vision OCR fast lane (v925 LIGHT default ships it off;
# tv/bin/ocr_mac exists and reads a frame in ~10-50ms warm vs ~10s Sonnet-only)
export TV_OCR="${TV_OCR:-1}"
# v928.1 — arm the FILM thread too (same v925-LIGHT cut): without it the SIM/retro
# "visual debugger" gets zero f_*.jpg footage — sessions replay as sparse read-stills
# instead of the 1fps reel (Konyo 2026-07-20: "where are all the SCREENSHOTS?")
export TV_FILM="${TV_FILM:-1}"

# v3849 (Elad 11:31) - the Desktop/Applications TV DIABLO.app wears the shipped logo: install copied the icon once,
# so a later logo never reached the launcher. Best effort, icon resource only, never blocks the launch.
python3 "$HERE/launcher_icon.py" 2>/dev/null || true

# v2145 — THE CONSOLE FOLLOWS THE SHIPPED BUILD. Konyo: "yes it can definitely relaunch to other
# new builds. just make sure the other profile locking of the chronicles and everything is
# connected to the profile and pc related to it.. so nothing ever gets deleted or regressed."
#
# Fixing the reel extract in v2139 made this necessary: sweeps actually run now, and POST
# /api/relaunch correctly refuses while one is reading ("relaunching now would throw away a paid
# read"), so his window sat on v2139 while origin was at v2144. The drift watcher (v2072) has
# always been able to catch up on its own; it just refused to act without this flag.
#
# WHAT MAKES IT SAFE TO ARM, all pre-existing and all still in force:
#   · it refuses while a chronicle or vault sweep is reading (nothing_in_flight)
#   · it refuses while _agent_alive() — HE IS FILMING. A restart then orphans that session's
#     frames, because the reel fold runs at seal (v2071).
#   · webview.start(private_mode=False) means the board's storage survives the restart (v928/v2043)
#   · and v2145 remembers WHICH WORLD the board came back as, so a relaunch that returns a
#     different one is reported by the eagle instead of silently stranding his vault — which is
#     exactly the condition he attached to this.
# Set TV_AUTO_RELAUNCH=0 to go back to announce-only.
# ⚠ v2146 — DISARMED AGAIN, DELIBERATELY, ONE VERSION AFTER ARMING IT. He said yes to auto-relaunch
# ON A CONDITION: "just make sure the other profile locking of the chronicles and everything is
# connected to the profile and pc related to it.. so nothing ever gets deleted or regressed." A
# cross-family review of the v2145 guard showed that condition is NOT met, and the gap is not small:
#
#   · THE GUARD CANNOT SEE THE CASE IT WAS WRITTEN FOR. Identity is only {owner, pfx}, and a CLAIMED
#     board publishes pfx:'' — so a brand-new claimed store is byte-identical to the old one and
#     board_identity_drift() answers "ok" over an empty vault. The install id and profile that WOULD
#     tell them apart already sit on d2r_lsrRoute and this reader ignores them.
#   · AUTO-RELAUNCH NEVER ASKS IT. drift_may_relaunch() checks the env flag and nothing_in_flight();
#     it never calls board_identity_drift(), so an already-drifted world does not block the execv.
#   · AND THE FALLBACK PATH RUNS EPHEMERAL STORAGE. If webview.start() takes its TypeError fallback,
#     the board comes back WITHOUT private_mode=False — v2043 exactly — and auto-relaunch would then
#     repeat that every _DRIFT_EVERY_S (300s) instead of once.
#
# Announcing-only WAS the resting state, and this sentence outlived it — v2153 armed auto-relaunch
# ON BY DEFAULT, and the line 17 rows below already says so. Kept, corrected rather than deleted,
# because the reasoning above it is still the reason the guard is careful:
#   auto-relaunch is ON unless something turns it off. TV_AUTO_RELAUNCH=0 turns it off;
#   TV_AUTO_RELAUNCH=1 is only needed to force it back on OVER a saved OFF.
# v2153 — ARMED. Konyo, twice: "it can definitely relaunch to other new builds", and then
# "its still not auto relaunching for the newer updates. we said it should relaunch by itself
# based on updates we do. automatically."
#
# It was armed at v2145 and I DISARMED it at v2146, because the world guard it leans on could not
# yet tell two different CLAIMED stores apart — so a relaunch that came back as a new WebKit store
# would have read as the same world and his vault could have been stranded silently. That was the
# right call then. v2147 rebuilt the guard on d2r_lsrRoute's install id, and drift_may_relaunch()
# now REFUSES on drift. The reason for the 0 is gone, so the 0 goes.
#
# What still stops it, every one of them checked before any execv:
#   * the board's world has drifted           -> refuse (v2147)
#   * a chronicle sweep is reading            -> refuse
#   * a vault sweep is reading                -> refuse
#   * a mini is recording                     -> refuse
#   * the agent is alive, i.e. HE IS FILMING  -> refuse (killing it orphans that reel's frames)
# Set TV_AUTO_RELAUNCH=0 by hand to go back to announce-only.
# ⚠ v2181 — NO BLANKET EXPORT, same reason as tvd_supervisor.sh. Forcing the variable here
# outranks the SAVED setting, so a switch he turned off in the console would come back on the
# next time he launched from this script. control_app defaults the arming to ON (v2180), so the
# export bought nothing and cost him the ability to say no. A value a human already set is
# passed through untouched.
[ -n "${TV_AUTO_RELAUNCH:-}" ] && export TV_AUTO_RELAUNCH

# ── TCC SAFEGUARD (2026-07-20 WindowServer-crash lesson) ────────────────────
# Finder/double-click launches capture wallpaper-only: the wrapper .app is
# unsigned, so macOS strips its Screen Recording grant on a crash and silently
# refuses to re-prompt. Terminal holds a durable grant and children inherit it
# at spawn — so a no-TTY launch reroutes itself through Terminal, which hands
# off and closes its own window. Already in a terminal (TTY) → run direct.
if [[ ! -t 0 && -z "${TVD_VIA_TERMINAL:-}" ]]; then
  if /usr/bin/osascript >/dev/null 2>&1 <<OSA
tell application "Terminal"
  set bootTab to do script "export TVD_VIA_TERMINAL=1; nohup bash '$HERE/start_tvd_mac.sh' >/dev/null 2>&1 & disown; exit"
  delay 2
  try
    close (first window whose tabs contains bootTab) saving no
  end try
end tell
OSA
  then
    exit 0
  fi
  # Terminal reroute failed (Automation denied?) — fall through to direct
  # launch so the app still opens, even if capture ends up wallpaper-only.
fi

cd "$REPO"

# A tracked file that matches the fetched origin/main, CR ignored, is the update
# that already landed, not a person mid-edit. The running console knows this only
# once it is a build that has the rule. This launcher runs first. 0: pull.
# 2: local work, do not pull. Anything else: could not tell, and a dirty tree
# still does not pull.
_tvd_may_pull() {
  local rc why
  rc=0
  why=$(python3 "$HERE/launcher_pull.py" --repo "$REPO" --apply 2>/dev/null) || rc=$?
  if [ "$rc" -eq 0 ]; then
    case "$why" in
      ""|clean) ;;
      *) echo "$(date '+%Y-%m-%d %H:%M:%S') auto-pull: $why" >>"$HERE/control_app.log" 2>/dev/null || true ;;
    esac
    return 0
  fi
  if [ "$rc" -ne 2 ]; then
    if [ -z "$(git -C "$REPO" status --porcelain --untracked-files=no 2>/dev/null)" ]; then
      return 0
    fi
    why=${why:-could not tell whether the changed files are the update}
  fi
  why=${why:-tracked files modified (local work protected)}
  echo "$(date '+%Y-%m-%d %H:%M:%S') skip auto-pull: $why" >>"$HERE/control_app.log" 2>/dev/null || true
  return 1
}

# ── v2102 — RELAUNCHING ACTUALLY PULLS NOW ─────────────────────────────────
# Konyo, opening a second machine: "it's reading v945. why is it not auto
# updating itself." It never could. NO launcher pulled — only the one-time
# tv/install-tvd.sh did — while /api/update's own howTo told him "Relaunch TV
# DIABLO to auto-pull". That sentence was false on every machine, and the only
# way to even LEARN you were behind was to click the version in the footer,
# which nobody does. So a second console sat 1,150 versions back and no surface
# ever said so. [[the-unjoined-end]] [[label-outlived-referent]]
#
# ONLY on a clean tree, and only fast-forward: a machine mid-edit keeps its
# work and is told why it is not updating. Never a rebase, never a merge.
# v2120 (#88) — AND THIS ONE HONOURS THE PIN TOO. There are two pull sites in this file; the
# v1418 block 35 lines below tests TV_NO_AUTO_PULL and this one did not, so it ran FIRST and
# pulled on a machine deliberately held back. The Windows launcher has always honoured it.
if command -v git >/dev/null 2>&1 && [ -d "$REPO/.git" ] && [ -z "${TV_NO_AUTO_PULL:-}" ]; then
  _tvd_before="$(git -C "$REPO" rev-parse --short HEAD 2>/dev/null || echo '?')"
  if ! _tvd_may_pull; then
    echo "📺 local tracked edits — NOT auto-pulling. Commit or stash them to rejoin the fleet."
  else
    if git -C "$REPO" pull --ff-only --quiet 2>/dev/null; then
      _tvd_after="$(git -C "$REPO" rev-parse --short HEAD 2>/dev/null || echo '?')"
      if [ "$_tvd_before" != "$_tvd_after" ]; then
        echo "📺 fleet update: $_tvd_before → $_tvd_after"
      fi
    else
      echo "📺 could not fast-forward (offline, or history diverged) — running what is on disk."
    fi
  fi
fi

if ! command -v python3 >/dev/null 2>&1; then
  osascript -e 'display alert "TV DIABLO" message "python3 not found. Re-run: curl -fsSL https://bull-4-u.com/d2r/install-tvd.sh | bash" as critical' || true
  exit 1
fi

if ! command -v claude >/dev/null 2>&1; then
  osascript -e 'display alert "TV DIABLO" message "Claude Code not found. Re-run the installer, then log into claude once." as critical' || true
  exit 1
fi

# ensure pywebview (silent if already present)
python3 -c "import webview" 2>/dev/null || \
  python3 -m pip install --user --quiet 'pywebview>=5.0' 2>/dev/null || true

# pull-first (quiet) — v1418 multi-machine FLEET UNITY (parity with start_tvd_win.ps1):
#   • TV_NO_AUTO_PULL=1 → never pull (dev pin)
#   • Untracked junk (?? debug files) must NOT block pull
#   • Modified TRACKED files still block (protect real local work)
#   • fetch + ff-only; if diverged with no tracked edits, reset --hard origin/main
if [[ -d "$REPO/.git" && -z "${TV_NO_AUTO_PULL:-}" ]]; then
  if ! _tvd_may_pull; then
    :
  else
    if git -C "$REPO" fetch origin >/dev/null 2>&1; then
      if git -C "$REPO" merge --ff-only origin/main >/dev/null 2>&1; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') auto-pull: fast-forward ok" \
          >>"$HERE/control_app.log" 2>/dev/null || true
      else
        echo "$(date '+%Y-%m-%d %H:%M:%S') auto-pull: ff failed, reset --hard origin/main (no tracked edits)" \
          >>"$HERE/control_app.log" 2>/dev/null || true
        git -C "$REPO" reset --hard origin/main >/dev/null 2>&1 || true
        echo "$(date '+%Y-%m-%d %H:%M:%S') auto-pull: now on origin/main" \
          >>"$HERE/control_app.log" 2>/dev/null || true
      fi
    else
      echo "$(date '+%Y-%m-%d %H:%M:%S') auto-pull: fetch failed (offline?)" \
        >>"$HERE/control_app.log" 2>/dev/null || true
    fi
  fi
fi

# Foreground: this process IS the app window (must not nohup/disown).
# v1379.1 — before attach, free :17772 so double-click always boots THIS checkout
# (never window-only onto a stale headless that still holds the port).
LOG="$HERE/control_app.log"
VER=$(python3 -c "import re,pathlib; t=pathlib.Path('$HERE/control_app.py').read_text(); m=re.search(r'\"ver\": \"(v[\\d.]+)\"', t); print(m.group(1) if m else 'v?')" 2>/dev/null || echo "v?")
# ── v2012 — DO NOT KILL A CONSOLE THAT IS SECONDS OLD; IT IS THE ONE STARTING UP ────────────
#
# The kill below is right: a double-click must boot THIS checkout and never window-only onto a
# stale headless (v1379.1). But it is UNCONDITIONAL, and two launches close together therefore
# race — launch 2 kills launch 1, launch 3 kills launch 2.
#
# MEASURED on his machine, control_app.log 2026-08-23. He closed the window with ✕, and then:
#     01:30:01  auto-pull: fast-forward ok   → native window up
#     01:30:21  auto-pull: fast-forward ok   → window gone (signal-SIGTERM)
#     01:30:51  auto-pull: fast-forward ok   → window gone (signal-SIGTERM)
# Three launches in fifty seconds, each SIGTERMing the one before it, each stopping ON AIR through
# the exit safeguard. If he had been recording, that is a session killed by a race with itself.
#
# ⚠ AND IT WAS MISREAD ONCE ALREADY. Those three `auto-pull` lines look like a poller reacting to a
# git push; auto-pull runs ONCE PER LAUNCH, right above. Reading them as a timeline of cause pinned
# the blame on a push nine minutes earlier. The lines are a symptom of relaunching, not a cause.
#
# THE RULE: if something is already listening and it is YOUNGER than the grace window, another
# launch is still coming up — stand down rather than take the port from it. An incumbent that is
# genuinely old is stale and still gets replaced, exactly as before.
#
# TV_FORCE_PORT=1 restores the old unconditional behaviour, for the case this guard gets wrong:
# a console crash-looping would hold the port with a forever-young pid and block a manual launch.
_TVD_PORT_GRACE="${TV_PORT_GRACE_S:-25}"     # supervisor cycles at 20s; a console binds in a few

_tvd_age_secs() {   # elapsed seconds for a pid from macOS `ps -o etime=` ([[dd-]hh:]mm:ss); -1 unknown
  local e d h m s
  e=$(ps -o etime= -p "$1" 2>/dev/null | tr -d ' ')
  [ -z "$e" ] && { echo -1; return; }
  d=0; h=0; m=0; s=0
  case "$e" in *-*) d=${e%%-*}; e=${e#*-};; esac
  case "$e" in
    *:*:*) h=${e%%:*}; e=${e#*:}; m=${e%%:*}; s=${e#*:};;
    *:*)   m=${e%%:*}; s=${e#*:};;
    *)     s=$e;;
  esac
  echo $(( 10#$d*86400 + 10#$h*3600 + 10#$m*60 + 10#$s ))
}

if command -v lsof >/dev/null 2>&1 && [ -z "${TV_FORCE_PORT:-}" ]; then
  for pid in $(lsof -tiTCP:17772 -sTCP:LISTEN 2>/dev/null); do
    _age=$(_tvd_age_secs "$pid")
    if [ "$_age" -ge 0 ] && [ "$_age" -lt "$_TVD_PORT_GRACE" ]; then
      echo "$(date '+%Y-%m-%d %H:%M:%S') port :17772 held by pid $pid, ${_age}s old — STANDING DOWN. Another console is still coming up; taking the port now is the restart storm that killed a session on 2026-08-23. TV_FORCE_PORT=1 to override." \
        >>"$HERE/control_app.log" 2>/dev/null || true
      exit 0
    fi
  done
fi

# ── 2026-09-29 — A RUNNING CONSOLE IS BROUGHT FORWARD, NEVER REPLACED (REG-1514) ───────────────────────────
# ✕ sends the console to the BACKGROUND, where it keeps filming the shadow reel and running triage and drain;
# and a double-click while its window is simply UP used to fall through to the kill below too - a healthy
# console, maybe filming his session, replaced by a fresh one. The kill exists for one reason (v1379.1): never
# window-only onto a STALE console running older code, and the console answers that itself. One decision,
# tv/launcher_decide.py (driven by a law against a fake console): current code + a window -> brought forward
# and this launch ends; it SAYS it is stale or windowless, or nothing serves the port (rc 3) -> replaced below.
# REG-1940 - "could not tell" (rc 2: a timeout, an unreadable answer, a refused front request) is NOT consent:
# the console is left running and a notification says so. TV_FORCE_PORT=1 still replaces it unconditionally.
if [ -z "${TV_FORCE_PORT:-}" ]; then
  # ⚠ `set -e` is on (line 4): a bare `x=$(cmd)` whose cmd exits non-zero ENDS THE SCRIPT right here, so "replace
  # it" (the console is down, stale or windowless) launched nothing and the Desktop icon did nothing (v3524).
  _tvd_rc=0
  _tvd_why=$(python3 "$HERE/launcher_decide.py" --port 17772 --from mac-launcher 2>/dev/null) || _tvd_rc=$?
  echo "$(date '+%Y-%m-%d %H:%M:%S') launcher: ${_tvd_why:-no answer from launcher_decide}" >>"$HERE/control_app.log" 2>/dev/null || true
  if [ "$_tvd_rc" -eq 0 ]; then
    exit 0
  fi
  # the decision always prints why, so an empty answer with rc 2 is python failing to open the file, not a verdict
  if [ "$_tvd_rc" -eq 2 ] && [ -n "$_tvd_why" ]; then
    osascript -e 'display notification "the running console did not answer in time - left running, not replaced" with title "TV DIABLO"' 2>/dev/null || true
    exit 0
  fi
fi

# soft-kill anything still listening on the control port (not us — we have not bound yet)
if command -v lsof >/dev/null 2>&1; then
  for pid in $(lsof -tiTCP:17772 -sTCP:LISTEN 2>/dev/null); do
    kill "$pid" 2>/dev/null || true
  done
  sleep 0.4
  for pid in $(lsof -tiTCP:17772 -sTCP:LISTEN 2>/dev/null); do
    kill -9 "$pid" 2>/dev/null || true
  done
  sleep 0.2
fi
# brief dock notification so Konyo can SEE the ship stamp on every double-click
osascript -e "display notification \"starting ${VER}\" with title \"TV DIABLO\"" 2>/dev/null || true
exec python3 "$HERE/control_app.py" --open >>"$LOG" 2>&1
