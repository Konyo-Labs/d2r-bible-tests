#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════════════════════
# REFRESH THE GUEST FROM LIVE — the one command, run on the MAC, no mouse required.
#
#   bash tv/sync_guest_api.sh            # pull live -> ./guest-mirror/
#   bash tv/sync_guest_api.sh --to-box   # ...and copy it to the box
#
# HIS BRIEF (GB-CLAUDE-GROK-PROFILE-SYNC): *"Keep/improve sync_guest_api.sh (Mac curls :17772 ->
# mirror) + CopyToBox into /workspace/tv-diablo-guest/api-live/ ... Document one command
# Elad/Diablo can run: 'refresh guest from live' without Mac mouse."*
#
# ⚠ IT DID NOT EXIST. The brief says "keep/improve"; a search of this repo and the whole home
# directory found no sync_guest_api.sh and no tv-diablo-guest tree — the box has the bridge, the
# Mac had nothing to feed it. That is why the guest VAULT renders every locker as "empty locker":
# not a bug in the vault, an absent mirror. [[zero-needs-a-denominator]]
#
# ⚠⚠ READ-ONLY BY ALLOWLIST, NOT BY INTENTION. Every endpoint below is a GET that reports. The
# mutating doors — board_tick, chronicle_apply, vault_apply, vault_forget, session/delete,
# relaunch, restart, quit, update — are deliberately ABSENT and must stay absent: his brief puts
# "mutating vault possession from guest smokes" out of scope, and a mirror that carried a write
# door would let an eyes-loop change what he owns.
#
# ⚠⚠ AND IT SCRUBS. This repo is public and the brief says "No install ids, hostnames, tokens, or
# home paths". His /api/status carries an install id, a .local hostname, a unix user and absolute
# home paths; fixture packs and evidence screenshots are built from this mirror. guest_profile.py
# does the redaction and the run REFUSES to copy anything that still leaks.
set -uo pipefail

LIVE="${TV_LIVE_URL:-http://127.0.0.1:17772}"
OUT="${GUEST_MIRROR:-$(cd "$(dirname "$0")/.." && pwd)/guest-mirror}"
BOX_HOST="${GUEST_BOX_HOST:-}"
BOX_PATH="${GUEST_BOX_PATH:-/workspace/tv-diablo-guest/api-live}"
# REG-3206 - THE ART THE BOARD ASKS FOR TRAVELS WITH THE BOARD. Every refresh shipped a NEW board.html
# and never the pictures it names, so the guest kept an art tree older than its board: GrokBot logged
# ~103 distinct /art/* 404s there (boss, HD and gem keys) while his Mac served every one. The repo's
# art/ is public content (no scrub needed); it goes to GUEST_BOX_ART, where the box's bridge serves /art/.
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BOX_ART="${GUEST_BOX_ART:-$BOX_PATH/art}"
TO_BOX=0
[ "${1:-}" = "--to-box" ] && TO_BOX=1

# READ-ONLY ALLOWLIST. Add here only after checking the route is a GET that reports.
READ_ONLY=(
  # identity + health — the box doctor asserts on status
  "api/status" "api/doctor" "api/heart" "api/eagle" "api/meter" "api/fleet"
  # SHELF
  "api/sessions" "api/river" "api/tombstones"
  # VAULT
  "api/vault_ledger" "api/vault_sweep" "api/tallies" "api/board_tally"
)

mkdir -p "$OUT/api"
echo "  live : $LIVE"
echo "  out  : $OUT"

ok=0; bad=0
for ep in "${READ_ONLY[@]}"; do
  dest="$OUT/${ep}.json"
  mkdir -p "$(dirname "$dest")"
  body="$(curl -sS --max-time 20 "$LIVE/$ep" 2>/dev/null)"
  if [ -z "$body" ]; then
    # ⚠ FAIL CLOSED. An endpoint that did not answer writes an explicit unreadable record, never
    # an empty object — on the guest an empty vault and an unread vault look identical and only
    # one of them means "you own nothing".
    python3 -c "
import json,sys
sys.path.insert(0,'$(cd "$(dirname "$0")" && pwd)')
import guest_profile as gp
open('$dest','w').write(json.dumps(gp.unreadable('$ep','the live console did not answer'),indent=1))
"
    echo "  ✗ $ep — no answer (wrote an unreadable record, not an empty one)"
    bad=$((bad+1)); continue
  fi
  printf '%s' "$body" | python3 -c "
import json,sys,io,os
sys.path.insert(0,'$(cd "$(dirname "$0")" && pwd)')
import guest_profile as gp
raw=sys.stdin.read()
try: obj=json.loads(raw)
except Exception as e:
    obj=gp.unreadable('$ep','the live console answered with something that is not JSON: %s'%e)
    io.open('$dest','w',encoding='utf-8').write(json.dumps(obj,indent=1)); raise SystemExit(0)
live=(obj or {}).get('identity') if isinstance(obj,dict) else None
obj = gp.rewrite_status(obj, live) if '$ep'=='api/status' else gp.scrub(obj, live)
io.open('$dest','w',encoding='utf-8').write(json.dumps(obj,ensure_ascii=False,indent=1))
" && { echo "  ✓ $ep"; ok=$((ok+1)); } || { echo "  ✗ $ep — rewrite failed"; bad=$((bad+1)); }
done

# the board itself — the big HTML the guest iframes.
# ⚠ SCRUBBED LIKE EVERYTHING ELSE. Measured on the first run: the raw board carried FOUR of his
# machine's identifiers. It is 6.4 MB of HTML rather than JSON, so it needs the string scrub
# explicitly — and it is the single largest carrier of home paths in the whole mirror.
if curl -sS --max-time 40 "$LIVE/board" -o "$OUT/board.raw.html" 2>/dev/null; then
  python3 - "$OUT" "$LIVE" <<'PYB'
import io, json, os, sys, urllib.request
sys.path.insert(0, os.path.join(os.getcwd(), "tv"))
import guest_profile as gp
out, live_url = sys.argv[1], sys.argv[2]
live = {}
try:
    live = (json.load(urllib.request.urlopen(live_url + "/api/status", timeout=10)) or {}).get("identity") or {}
except Exception:
    pass
raw = io.open(os.path.join(out, "board.raw.html"), encoding="utf-8", errors="replace").read()
io.open(os.path.join(out, "board.html"), "w", encoding="utf-8").write(gp.scrub(raw, live))
os.remove(os.path.join(out, "board.raw.html"))
PYB
  echo "  ✓ board ($(wc -c <"$OUT/board.html" | tr -d ' ') bytes, scrubbed)"
else
  echo "  ✗ board — no answer"
fi

echo "  ── $ok endpoint(s) mirrored, $bad unreadable (recorded as such, not as empty)"

# ══ THE PROGRESS SEED — why the guest board is not empty ════════════════════════════════════
# The guest runs on Linux, and bible.html places every non-Mac machine in the ISOLATED cousin
# world, which starts from zero. That is deliberate: "a machine wrongly placed in the OWNER's
# world sees someone else's chronicle". So the seat is FILLED rather than re-labelled — this
# writes a snapshot in the board's own exportProgress schema, which Grok Bot imports through the
# board's own Tools -> Backup door. No Mac mouse.
python3 - "$OUT" <<'PYS'
import glob, io, json, os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "tv"))
import guest_profile as gp
out = sys.argv[1]
live = {}
try:
    import urllib.request
    live = (json.load(urllib.request.urlopen(
        os.environ.get("TV_LIVE_URL", "http://127.0.0.1:17772") + "/api/status",
        timeout=10)) or {}).get("identity") or {}
except Exception:
    pass
backs = sorted(glob.glob(os.path.expanduser("~/d2r_ledger_backups/ledger_*.json")))
if not backs:
    print("  seed: NO ledger backup found — the guest board will start empty, and that is "
          "reported rather than silently shipped")
else:
    seed = gp.progress_seed(backs[-1], live)
    io.open(os.path.join(out, "seed_progress.json"), "w", encoding="utf-8").write(
        json.dumps(seed, ensure_ascii=False, indent=1))
    if gp.is_unreadable(seed):
        print("  ✗ seed: %s" % seed.get("why"))
    else:
        d = seed.get("data") or {}
        try:
            owned = len(json.loads(d.get("d2r_owned") or "[]"))
        except Exception:
            owned = "?"
        print("  ✓ seed_progress.json — %d store(s), %s owned item(s), from %s"
              % (len(d), owned, os.path.basename(backs[-1])))
PYS

# ══ FIXTURE PACKS — his recorded runs, restaged on every refresh ════════════════════════════
# A pull overwrites api/sessions.json with the live list, which would silently drop every staged
# scenario. So packs are (re)loaded AFTER the pull, every time — the refresh is one command and
# it must leave the guest in the state the last refresh left it, plus whatever is newer.
FIXTURES="${GUEST_FIXTURES:-$(cd "$(dirname "$0")/.." && pwd)/fixtures}"
if [ -d "$FIXTURES" ]; then
  python3 - "$FIXTURES" "$OUT" <<'PYF'
import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "tv"))
import guest_fixture_pack as fx
root, mirror = sys.argv[1], sys.argv[2]
packs = sorted(d for d in os.listdir(root)
               if os.path.isfile(os.path.join(root, d, "pack.json")))
if not packs:
    print("  fixtures: none staged (0 packs in %s)" % root)
for p in packs:
    d = os.path.join(root, p)
    try:
        r = fx.load(d, mirror)
        print("  ✓ fixture %-22s +%d session(s), %d reel(s)"
              % (p, r["sessionsAdded"], r["reelsCopied"]))
    except Exception as e:
        # a bad pack must not take the refresh down with it, and must not pass silently
        print("  ✗ fixture %-22s REFUSED: %s" % (p, str(e)[:90]))
PYF
fi

# ⚠ THE LEAK GATE. Nothing reaches the box until the mirror is clean.
python3 - "$OUT" <<'PYEOF'
import io, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tv"))
sys.path.insert(0, os.path.join(os.getcwd(), "tv"))
import guest_profile as gp
root = sys.argv[1]
live = {}
try:
    import urllib.request
    live = (json.load(urllib.request.urlopen(os.environ.get("TV_LIVE_URL",
            "http://127.0.0.1:17772") + "/api/status", timeout=10)) or {}).get("identity") or {}
except Exception:
    pass
bad = []
n = 0
for dirpath, _d, files in os.walk(root):
    for f in files:
        p = os.path.join(dirpath, f)
        n += 1
        try:
            txt = io.open(p, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        found = gp.leaks(txt, live)
        if found:
            bad.append((os.path.relpath(p, root), len(found)))
print("  leak gate: %d file(s) scanned against %d secret(s)"
      % (n, len(gp._secrets(live))))
if bad:
    for p, c in bad[:8]:
        print("  ✗ LEAK %s (%d)" % (p, c))
    print("  REFUSING to copy — the mirror still carries his machine's identifiers")
    raise SystemExit(2)
print("  ✓ clean — nothing of his machine survives in the mirror")
PYEOF
leak_rc=$?
[ $leak_rc -ne 0 ] && { echo "  ABORTED before copy."; exit $leak_rc; }

# REG-3206 - every picture the mirrored board and this console can ask /art/ for, checked against the
# art tree that ships with it. A missing picture is not a leak, so it is REPORTED, never a refusal.
_board="$OUT/board.html"; [ -f "$_board" ] || _board="$REPO_ROOT/bible.html"
python3 "$REPO_ROOT/tv/art_names.py" --board "$_board" --art "$REPO_ROOT/art" \
  || echo "  ✗ art: the names above will 404 on the guest until art/ carries them"

if [ "$TO_BOX" = "1" ]; then
  if [ -z "$BOX_HOST" ]; then
    echo "  --to-box needs GUEST_BOX_HOST (e.g. GUEST_BOX_HOST=box ...). Mirror is ready at $OUT"
    exit 0
  fi
  echo "  copying -> $BOX_HOST:$BOX_PATH"
  # --exclude keeps the box's art/ (when GUEST_BOX_ART sits inside BOX_PATH) out of this --delete
  rsync -a --delete --exclude '/art/' "$OUT/" "$BOX_HOST:$BOX_PATH/" && echo "  ✓ copied" || { echo "  ✗ copy failed"; exit 1; }
  echo "  art     -> $BOX_HOST:$BOX_ART"
  rsync -a --delete "$REPO_ROOT/art/" "$BOX_HOST:$BOX_ART/" && echo "  ✓ art copied" || { echo "  ✗ art copy failed"; exit 1; }
fi
echo "  done."
