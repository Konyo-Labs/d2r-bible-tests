# ══════════════════════════════════════════════════════════════════════════════
# G5 · GROK EYES — SUBSCRIPTION CLI LANE  (self-contained, removable bolt-on)
# ══════════════════════════════════════════════════════════════════════════════
# Konyo (2026-07-25): optional parallel / future-primary vision brain via LOCAL
# SuperGrok login — same spirit as Claude's `claude -p` subscription lane.
#
#   POWER SOURCE:  `grok -p`  +  OIDC login (grok login / SuperGrok)
#   NOT:           XAI_API_KEY / console API tokens / api.x.ai Bearer calls
#
# EXTRA only. OFF by default. Claude path unchanged when OFF.
#
# Modes:
#   off      — instant no-op (default, cousin-safe)
#   shadow   — Claude still drives ON AIR; Grok also reads & is logged (no replace)
#   only     — #151 GROK ONLY (2026-10-01, his switch): the Grok CLI reads every frame and Claude is not asked at all -
#              not first, not as a backup. His words: "make the toggle optional to use GROK ONLY no claude as a secondary
#              at all ... so i can save and when you max out i can use just him". A failed Grok read is a FAILED read,
#              said and left owed - never handed to Claude, never an empty verdict. Chosen on a PC whose Grok cannot run,
#              the reads fail and SAY why: the switch is his, and quietly reading with Claude would spend the very
#              subscription he chose it to save. The default stays off (Claude only) - Dean's PC needs nothing.
#   primary  — RETIRED 2026-09-30. His ruling: "make sure the subscription CLI is using claude and not grok..
#              grok is just an extra layer if toggled on.. dean does not use grok.. so it shouldnt need both to work".
#              MEASURED that morning: his Mac and his ALT were both on primary (linking Grok auto-set it), so Grok
#              read every frame first - 3,150 of 6,132 calls on the Mac errored, most on a 140 s timeout, before
#              Claude took the read. Claude is THE reader on every PC; ON means shadow. A saved or requested
#              "primary" is read as shadow and said so (primaryRetired) - never silently.
#
# ┌─ HOW TO REMOVE THE ENTIRE G5 FEATURE (zero behavior change) ──────────────────┐
# │ 1. delete this file  (tv/g5_grok_eyes.py)                                     │
# │ 2. delete fenced blocks: # ══ GROK EYES (G5) ══ … # ══ END GROK EYES (G5) ══ │
# │ 3. delete tv/g5_sidecar/ + tv/G5_GROK_EYES_REMOVAL.md + G5_PHASE_CHECKLIST   │
# │ grep -rn "GROK EYES (G5)\|g5_grok_eyes\|/api/g5" tv/                         │
# └──────────────────────────────────────────────────────────────────────────────┘
#
# When OFF or not logged in: is_on() false, g5_vision_read() returns None, no CLI.

from __future__ import annotations

import hashlib
import json
import re as _re
import os
import atexit
import shutil
import subprocess
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
_STATE_FILE = os.path.join(HERE, "g5_grok_eyes.state")  # gitignored; per-machine
_SHADOW_LOG = os.path.join(HERE, "g5_shadow.jsonl")    # gitignored; shadow comparisons
_BUDGET_PATH = os.path.join(HERE, "g5_subscription_budget.json")

# ⚠⚠ v3092 — THESE WERE 30/200 AND THE CONSOLE WAS THE ONLY THING REFUSING HIS GROK READS.
# MEASURED the day this changed: 201 calls recorded against a _DAILY_MAX of 200, so _budget_ok()
# returned False on EVERY call and the lane read nothing — while the console's meter showed only
# the Claude lane, so nothing said so, and the Grok Bot posted "Quartz ON-SCREEN none — seat EMPTY"
# tick after tick. Konyo, looking at it: "i dont have a budget problem now though GROK should be
# working".
#
# He is right, and the asymmetry had no reason behind it. BOTH lanes are subscription CLIs that
# bill NO tokens — `grok -p` on his SuperGrok OIDC login, `claude -p` on his Claude login, with
# every API key stripped from the child env by design (see _API_STRIP). The Claude lane's ceiling
# is 4000/hour and 20000/day. This one was a hundred times tighter, and the two numbers here
# carried no comment, no measurement and no cited xAI limit — they were a guess that hardened into
# a throttle. [[feedback-threshold-above-the-ceiling]] [[unknown-stays-unknown]]
#
# ⚠ A REAL CEILING MUST COME FROM THE PROVIDER, NOT FROM US. If xAI rate-limits him, that arrives
# as an ERROR on the call and is recorded as one — visible, attributable, with a message. A local
# guess refuses BEFORE the call and records `skipped_budget`, which looks identical to an idle
# lane. The breaker stays (a runaway loop is still worth stopping) but it now sits where the Claude
# lane's does, so the provider is what limits him.
_HOURLY_MAX = max(0, int(os.environ.get("G5_GROK_HOURLY_MAX", "4000")))
_DAILY_MAX = max(0, int(os.environ.get("G5_GROK_DAILY_MAX", "20000")))
_TIMEOUT_S = float(os.environ.get("G5_GROK_TIMEOUT_S", "140"))
# REG-2040 (#239) - REASONING EFFORT. MEASURED 2026-10-08 on his Mac, one real Chronicle page (reel_s_1786999742937_35523
# f_1786999846054, uniques), this exact call twice per arm: default effort 115.4 s and 123.4 s - 82-88% of the 140 s
# timeout on an IDLE machine, which is why 3,608 of 7,832 console reads (46%) ended "grok -p timeout 140s"; --effort low
# 26.5 s and 37.2 s with the same names (Djinn Slayer, Doomslinger, Dreadfang, Duriel's Shell; one low run left out the
# half-cut bottom row - an omission, never an invention). n=2 per arm: a sample, not a proof. A read that times out
# answers nothing, so low wins. G5_GROK_EFFORT="" restores the CLI default.
_EFFORT = os.environ.get("G5_GROK_EFFORT", "low")


def _vision_args(bin_path, text_prompt, work):
    """The one argv for a G5 vision read. -> list"""
    args = [
        bin_path,
        "-p", text_prompt,
        "--output-format", "plain",
        "--always-approve",
        "--tools", "read_file",
        "--cwd", work,
        "--disable-web-search",
    ]
    if _EFFORT and not _EFFORT_STATE.get("refused"):
        args += ["--effort", _EFFORT]
    return args


_EFFORT_STATE = {"refused": None}


def _effort_refused(args, stderr):
    """True when this CLI refused the --effort flag itself (an older build), not when a read failed. -> bool"""
    if "--effort" not in (args or []):
        return False
    e = str(stderr or "").lower()
    return ("effort" in e) and any(w in e for w in ("unexpected argument", "unrecognized", "unknown argument",
                                                    "found argument", "invalid value", "unknown option"))
_MODES = ("off", "shadow", "primary", "only")

# API-style secrets we ALWAYS strip so vision cannot ride console tokens
_API_STRIP = (
    "XAI_API_KEY", "G5_XAI_KEY", "G4_XAI_KEY",
    "OPENAI_API_KEY", "OPENAI_BASE_URL",
    "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN",
)

_CALL_LOG: list[float] = []
_STATS = {
    "calls": 0, "ok": 0, "errors": 0, "skipped_budget": 0, "skipped_blocked": 0, "shadow": 0, "primary": 0, "only": 0,
    "backup_reads": 0, "backup_why": None,
    "last": None, "last_error": None, "last_error_ts": None, "lane": "subscription-cli",
}
_LOCK = threading.Lock()
_AUTH_LOGGED = False

_DEFAULT_VISION_PROMPT = (
    "Diablo II Resurrected (RoW) screenshot at path:\n{path}\n\n"
    "Open that image file with the read_file tool FIRST, then reply with STRICT JSON only, "
    "no markdown fences, no prose:\n"
    '{{"area":"","tz":[],"scene":"gameplay","stashTab":"","names":[],'
    '"names_loc":{{}},"sockets":{{}},"discovered":[],"conf":0.0}}\n'
    "scene = one of: town | stash | inventory | loot | gameplay | transition.\n"
    "transition = fullscreen loading/portal with NO bottom HUD; dark combat WITH HUD = gameplay.\n"
    "area = zone name if legible, else \"\".\n"
    "tz = purple terror-zone lines if any, else [].\n"
    "stashTab = only when scene=stash: personal | shared | gems | materials | runes | \"\".\n"
    "names = READABLE item name text only — never invent from icons; never complete partials.\n"
    "sockets = name -> N when Socketed (N) or N holes visible; else {{}}.\n"
    "names_loc = for each name: equipped | inventory | stash | floor.\n"
    "discovered = item names from chat discovery lines only; else [].\n"
    "conf = 0.0-1.0. Be precise."
)

# v1514 — THE SECOND EYE ON THE CHRONICLE. Konyo: "grok for me specifically i can use as a second
# pair of eyes and a different view for also these exact things! it must be also coded in so it is
# IDENTICALLY trying to read and retro chronicle these tallied in."
#
# "Identically" is the requirement AND the trap. The two lanes must answer the SAME question in the
# SAME shape — otherwise their answers cannot be compared, and cross-lane agreement (the strongest
# witness the gate has) would be measuring prompt differences instead of the screen. But they must
# not share a prompt WORDING either, or they inherit the same blind spots and the "independent"
# second opinion is theatre. So: same contract, same refusals, its own words.
CHRONICLE_VISION_PROMPT = (
    "Diablo II Resurrected (RotW mod) screenshot at path:\n{path}\n\n"
    "Open that image with the read_file tool FIRST, then reply with STRICT JSON only, no markdown "
    "fences, no prose:\n"
    '{{"ledger":"{ledger}","found":[],"notFound":[],"sets":[],'
    '"printedFound":null,"printedTotal":null,"stateVisible":true,"wrongTab":false,"notChronicle":false,'
    '"foundAt":{{}},"droppedBy":{{}},"conf":0.0}}\n'
    "This is the in-game CHRONICLE (holy grail) panel: a scrollable list of item names, each row "
    "showing whether the player has FOUND it — bright/coloured text vs grey/dim, a tick, a filled "
    "marker.\n"
    "found = ONLY names whose found-state is VISIBLY positive. notFound = names you can read whose "
    "state is dim, empty or ambiguous.\n"
    # v1839 — mirrored from the Claude lane so the two eyes answer in the same units (v1519's rule:
    # cross-lane agreement is only evidence if both lanes are answering the same question).
    "notChronicle = true when the picture is not a Chronicle panel at all - gameplay, a stash, a "
    "menu, or the TV DIABLO console window. That is a different answer from a Chronicle page whose "
    "rows you cannot judge.\n"
    "If you cannot tell found from unfound anywhere on the panel: set stateVisible=false and return "
    "found EMPTY. Do not assume everything shown is owned — this read is unattended and a confident "
    "wrong page permanently mis-tallies his grail.\n"
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
    "THE LEDGER YOU WERE GIVEN IS {ledger}. uniques = single unique items (Harlequin Crest, "
    "Windforce, Stormshield). sets = rows grouped under SET names (Tal Rasha's Wrappings, Immortal "
    "King). If the panel on screen is the OTHER one, set wrongTab=true and return found empty.\n"
    # v1566 — see tv_diablo.py: the second eye must speak the same shape as the first, or a
    # cross-lane agreement on a COMPLETE set is impossible by construction.
    "sets = only when ledger=sets: [{{\"set\":\"<set name>\",\"pieces\":[<found piece names>],\"complete\":true|false}}].\n"
    "set `complete` true ONLY when the panel itself marks that set finished — never inferred.\n"
    # v1826 — see tv_diablo.py: the same tell, worded the same way. Measured on his swept evidence,
    # 4 of 16 set groups were keyed by a PIECE name rather than a set. The second eye must describe
    # a group the same way the first does or the two can never agree about one.
    "A SETS page groups its rows under a set-name HEADING. The heading is centred, has NO item "
    "icon, NO `Dropped By:` line and NO `First Found:` line. Every PIECE row has all three. Put the "
    "HEADING in \"set\" and the rows beneath it in \"pieces\" — never a piece name in \"set\", and "
    "never a heading in \"pieces\". If you cannot see which heading a row belongs to, leave that "
    "row out rather than inventing a group for it.\n"
    "printedFound / printedTotal = the panel's own progress numbers if it prints any (\"243/403\", "
    "\"Found 108 of 135\") EXACTLY as shown, else null. They are checked against your own count — an "
    "honest mismatch is useful, a fabricated match is not.\n"
    "Only rows you can actually READ belong in either list. A half-remembered item, a plausible "
    "guess at a blurred row, a name you expect to be there — none of those. Leave it out.\n"
    # v1819 — see tv_diablo.py CHRONICLE_READ_PROMPT: the same three fields, worded the same way.
    # The second eye must speak the same shape as the first, or a cross-lane agreement on a find
    # DATE is impossible by construction — which is the same reason `complete` was mirrored here
    # in v1566.
    # v1828 — see tv_diablo.py: `sort` never once arrived (0 of 2358) and the per-row dates make it
    # unnecessary. Removed from both lanes together so the two keep asking for the same thing.
    "foundAt = map each FOUND name -> its exact `First Found:` stamp, copied digit for digit, e.g. "
    '{{"Razorswitch":"08/20/2026, 00:49"}}. Omit any row whose stamp is hidden behind a tooltip or '
    "cut off at the panel edge, and NEVER infer one from a row's position.\n"
    "droppedBy = map each FOUND name -> the monster on its `Dropped By:` line. Omit what you cannot "
    "read.\n"
    "⚠ THE TWO TABS PRINT THOSE LINES IN OPPOSITE ORDER. On UNIQUES a row reads: name / "
    "`First Found: ...` / `Dropped By: ...`. On SETS it reads: name / `Dropped By: ...` / "
    "`First Found: ...`. Read each line by its LABEL, never by its position under the name.\n"
    "conf = 0.0-1.0, your own honest confidence in this page."
)


def g5_chronicle_read(image_path, kind, *, force=True):
    """The Grok lane's chronicle read, in the v1510 worker's response shape.

    Returns None whenever Grok cannot or should not answer (off, not logged in, over budget, error).
    None is a REFUSAL, never an empty page: two_lane_read distinguishes "grok didn't run" from "grok
    saw nothing", and collapsing them would let a dead second lane read as silent agreement.
    """
    ledger = "sets" if str(kind or "").endswith("sets") else "uniques"
    import os as _os
    # v1519 — TV_STUB is the zero-cost seam the Claude lane already honours (v711). Without it here
    # the "free" end-to-end sweep test reached for the real grok CLI: a test that spends money is a
    # test nobody runs, and a second lane nobody exercises is a second lane nobody trusts.
    if _os.environ.get("TV_STUB"):
        try:
            import json as _json
            mp = _os.environ.get("TV_STUB_MANIFEST") or _os.path.join(HERE, "stub_manifest.json")
            with open(mp, encoding="utf-8") as fh:
                man = _json.load(fh)
        except Exception:
            man = {}
        base = _os.path.basename(str(image_path or ""))
        raw = man.get(base + "#chronicle-grok") or man.get("*#chronicle-grok")
        try:
            import chronicle_retro as _cr
        except Exception:
            return None
        # absent from the manifest ⇒ a SILENT lane, which two_lane_read already reports honestly
        return (_cr.normalize_page(raw, kind, "grok", framing="stub")
                if raw is not None else None)
    path = _os.path.abspath(str(image_path or ""))
    # ── v1901 — THE SECOND WITNESS GETS THE SAME PIXELS ───────────────────────────────────────
    # For eleven versions it did not. The Claude lane has cropped to the Chronicle list band since
    # v1780 — measured 0/6 pages full-frame against 5/6 cropped on his own reel — and this lane was
    # handed the whole 2940x1912 desktop grab every single time, because the crop lived inside the
    # Claude reader where nothing else could call it. Two lanes exist so that agreement between them
    # is evidence; agreement between witnesses shown different pictures is worth less than it reads.
    #
    # DUAL ROUTE, exactly as the Claude lane proves it: a refused crop retries the full frame, so
    # this can only ever add a read, never lose one. The retry is gated on g5's own budget — the
    # Claude lane's v1845 lesson was that a retry which never re-asks the cap turns one budget check
    # into a licence for two reads on every refused page.
    import chronicle_crop as _cc
    _read_path, _framing = _cc.list_crop(path)
    raw = g5_vision_read(_read_path,
                         prompt=CHRONICLE_VISION_PROMPT.format(path=_read_path, ledger=ledger),
                         force=force)
    if _read_path != path and _cc.crop_answer_refused(raw):
        _full = g5_vision_read(path, prompt=CHRONICLE_VISION_PROMPT.format(path=path, ledger=ledger),
                               force=force)
        if not _cc.crop_answer_refused(_full):
            raw = _full
            _framing = _cc.FULL
    # v1519 — ONE normalizer, shared with the Claude lane (chronicle_retro.normalize_page). If each
    # lane shaped its own answer, "witness: agree" would mean two different things depending on who
    # said it — and cross-lane agreement is only evidence when both lanes answer in the same units.
    try:
        import chronicle_retro as _cr
    except Exception:
        return None
    return _cr.normalize_page(raw, kind, "grok", framing=_framing)


# ── subscription auth (NOT API keys) ───────────────────────────────────────────
_GROK_CANDIDATES = (
    "~/.grok/bin/grok",            # the official installer's home — where Konyo's actually is
    # #225 — the Windows installer's home. MEASURED on the ALT box: C:\Users\USER-1\.grok\bin\grok.exe
    # exists and is on PATH, and a candidate list with no .exe could never name it.
    "~/.grok/bin/grok.exe",
    "~/.local/bin/grok",
    "/opt/homebrew/bin/grok",
    "/usr/local/bin/grok",
)


def _grok_bin():
    """v1501 — FIND IT THE WAY WE FIND CLAUDE. `shutil.which` searches the PATH OF THIS PROCESS, and
    the console runs as a GUI app under launchd/pywebview, whose PATH is the bare
    /usr/bin:/bin:/usr/sbin:/sbin — it does NOT inherit the shell PATH where ~/.grok/bin lives.

    Measured on Konyo's Mac: `which grok` in his shell resolves /Users/konyo/.grok/bin/grok, while
    the console reported cliInstalled=False. He had set the switch to PRIMARY — his mandated vision
    lane — and it had been silently dark ever since, with calls=0, errors=0 and last_error=None,
    because a lane that never ATTEMPTS never records a failure.

    control_app.py already carries `_find_claude_bin` for exactly this reason on Windows. The third
    eye gets the same courtesy: env override first, then PATH, then the known install locations."""
    for env in ("G5_GROK_BIN", "TV_GROK_BIN"):
        v = (os.environ.get(env) or "").strip()
        if v and os.path.isfile(os.path.expanduser(v)):
            return os.path.expanduser(v)
    hit = shutil.which("grok")
    if hit and os.path.isfile(hit):
        return hit
    for cand in _GROK_CANDIDATES:
        # v3886 (#107, windows-latest) - one spelling: "~/.grok/bin/grok.exe" expanded to C:\...\winhome/.grok/bin/grok.exe,
        # a path that works and compares unequal to the same file by its own name
        p = os.path.normpath(os.path.expanduser(cand))
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return ""


def _subscription_logged_in():
    """True if local SuperGrok/Grok Build OIDC session looks present."""
    auth = os.path.expanduser("~/.grok/auth.json")
    try:
        if not os.path.isfile(auth) or os.path.getsize(auth) < 40:
            return False
        with open(auth, encoding="utf-8") as fh:
            d = json.load(fh)
        if not isinstance(d, dict) or not d:
            return False
        # any entry with a key/token blob counts as logged in
        for v in d.values():
            if isinstance(v, dict) and (v.get("key") or v.get("refresh_token") or v.get("auth_mode")):
                return True
        return True  # non-empty auth.json
    except Exception:
        return False


def has_subscription():
    """CLI on PATH + logged in via grok login (SuperGrok). Never checks API keys."""
    return bool(_grok_bin() and _subscription_logged_in())


# Back-compat alias used by older UI/tests — means "can run Grok eyes", not API key
def _key():
    return "subscription" if has_subscription() else ""


def _real_grok_home():
    """His Grok home — config, login, sessions. Resolved from THIS process's env, never the child's."""
    return os.environ.get("GROK_HOME") or os.path.join(os.path.expanduser("~"), ".grok")


_LEAN_HOME = None


def _lean_home():
    """An EMPTY directory to stand in for HOME during a frame read - ONE fixed directory (a production mkdtemp per
    process with no cleanup is a scratch-dir leak), and EMPTIED before every use.

    ⚠ v3526 second eye (Grok CLI, 2026-09-30), reproduced before fixing: the fixed path was only ever MADE, never
    checked - makedirs(exist_ok=True) hands back a directory that already holds files, so one stray .claude.json /
    .grok / hooks file left there by a grok child, a crash or any other process of this user would be imported by
    EVERY later lean read: REG-1549's Chrome-per-read back, silently. So every call checks it: a symlink at the path is
    replaced by a real directory, anything inside is removed (nothing of his ever lives here - it is a stand-in HOME
    this module owns), and a directory that cannot be emptied is abandoned for a fresh mkdtemp removed at exit, with
    the reason in _STATS["lean_home"] - heavier, and said."""
    global _LEAN_HOME
    p = os.path.join(tempfile.gettempdir(), "tvd-g5-home")
    try:
        if os.path.islink(p):
            os.unlink(p)
        os.makedirs(p, exist_ok=True)
        for n in os.listdir(p):
            q = os.path.join(p, n)
            if os.path.isdir(q) and not os.path.islink(q):
                shutil.rmtree(q)
            else:
                os.unlink(q)
        if os.listdir(p):
            raise OSError("the stand-in home would not empty")
        _LEAN_HOME = p
        _STATS["lean_home"] = "fixed stand-in, emptied before the read"
        return p
    except Exception as e:
        d = tempfile.mkdtemp(prefix="tvd-g5-home-")
        atexit.register(shutil.rmtree, d, True)
        _LEAN_HOME = d
        _STATS["lean_home"] = "a fresh stand-in - the fixed one could not be emptied (%s: %s)" % (type(e).__name__, e)
        return d


def _grok_env(lean=False):
    """Env for grok -p: SuperGrok OIDC only — strip API tokens like Claude lane does.

    ⚠⚠ v3525 (REG-1549) — A FRAME READ DOES NOT LOAD HIS OTHER TOOLS' CONFIG. The Grok CLI imports Claude
    Code's and Cursor's MCP servers, skills and hooks by default (`[compat.claude] mcps/skills/hooks`,
    discovered under HOME). MEASURED on his ALT 2026-09-29 22:17: every read (1,258 in 24 h, one every
    ~70 s) started `npx -y chrome-devtools-mcp@latest` from ~/.claude.json and with it a whole Chrome - 7
    processes, 418 MB, on an 8 GB box with 346 MB free while Boosteroid ran - and loaded 72 skills into a
    call whose only tool is read_file. On the Mac the same call loaded 81 skills and 7 Claude hooks. Those
    compat switches are read from $GROK_HOME/config.toml only (a project .grok/config.toml and the
    GROK_CONFIG overlays were both measured NOT to reach them), so a read keeps GROK_HOME = his real home
    (his login, his config, untouched) and points HOME / USERPROFILE at an empty directory: nothing to
    import. Measured with `grok inspect`: MCP 1 -> 0, hooks 7 -> 0, skills 81 -> 33 (ALT 72 -> 22), and a
    live read answered in 4 s with no Chrome started and nothing written to the stand-in home.
    `grok login` is NOT lean: signing in is his, in his real home.
    """
    env = os.environ.copy()
    stripped = [k for k in _API_STRIP if env.pop(k, None) is not None]
    if lean:
        try:
            env["GROK_HOME"] = _real_grok_home()     # resolved BEFORE HOME moves - his login stays his
            h = _lean_home()
            env["HOME"] = h
            if os.name == "nt":
                env["USERPROFILE"] = h
            _STATS["read_env"] = "lean"
        except Exception as e:
            # the read still works on the plain env - heavier, and said so rather than hidden
            _STATS["read_env"] = "plain - the lean home could not be made (%s: %s)" % (type(e).__name__, e)
    return env, stripped


def _log_auth_once(stripped):
    global _AUTH_LOGGED
    if _AUTH_LOGGED:
        return
    _AUTH_LOGGED = True
    if stripped:
        _STATS["last_error"] = None; _STATS["last_error_ts"] = None  # not an error
        # leave a breadcrumb in stats
        _STATS["stripped_api_env"] = ",".join(stripped)


# ── mode / toggle ─────────────────────────────────────────────────────────────
def _load_state():
    try:
        with open(_STATE_FILE, encoding="utf-8") as fh:
            d = json.load(fh) or {}
        mode = str(d.get("mode") or "off").strip().lower()
        if mode not in _MODES:
            mode = "off"
        retired = mode == "primary"
        if d.get("on") and mode == "off":
            mode = "shadow"            # a legacy {"on": true} is the extra layer, never Grok-first (2026-09-30)
        if retired:
            mode = "shadow"            # primary is retired: Claude reads, Grok watches beside it
        return {"on": bool(d.get("on")) or mode in ("shadow", "only"), "mode": mode, "retired": retired}
    except Exception:
        return {"on": False, "mode": "off", "retired": False}


def switch_state():
    """#97 - can his reader switch be READ? -> "absent" | "ok" | "unreadable"

    _load_state() answers a missing file and an unreadable one alike ({on: False, mode: off}), and reader() then says
    "claude" for both - so a GROK ONLY PC whose switch file was half-written or corrupt started a PAID Claude sweep. An
    absent file is a PC that never chose (Claude, the default, is right); an unreadable one chose something nobody can
    read, which is UNKNOWN - and a paid sweep must not start on it."""
    try:
        with open(_STATE_FILE, encoding="utf-8") as fh:
            d = json.load(fh)
        return "ok" if isinstance(d, dict) else "unreadable"
    except FileNotFoundError:
        return "absent"             # never written - or removed mid-read (the v3818 second eye): never chose, not unreadable
    except Exception:
        return "unreadable"


def _save_state(on, mode):
    mode = str(mode or "off").strip().lower()
    if mode not in _MODES:
        mode = "off"
    if mode == "primary":
        mode = "shadow"                # 2026-09-30: nothing writes Grok-first again
    if mode == "off":
        on = False
    else:
        on = True
    try:
        with open(_STATE_FILE, "w", encoding="utf-8") as fh:
            json.dump({"on": bool(on), "mode": mode, "ts": time.time(), "lane": "subscription-cli"}, fh)
    except Exception:
        pass
    return status()


def switch_on():
    env = (os.environ.get("TV_G5_GROK_EYES") or "").strip().lower()
    if env in ("0", "off", "false", "no"):
        return False
    if env in ("1", "on", "true", "yes", "shadow", "primary", "only", "grok", "grok-only"):
        return True
    st = _load_state()
    return st["on"] and st["mode"] != "off"


def mode_intent():
    env = (os.environ.get("TV_G5_GROK_EYES") or "").strip().lower()
    if env in ("0", "off", "false", "no"):
        return "off"
    if env in ("shadow", "sh"):
        return "shadow"
    if env in ("only", "grok", "grok-only"):
        return "only"                  # #151 his switch: Grok reads every frame, Claude is not asked
    if env in ("1", "on", "true", "yes", "primary", "pri"):
        return "shadow"                # ON is the extra layer; "primary" is retired (2026-09-30)
    st = _load_state()
    if not st["on"]:
        return "off"
    return st["mode"] if st["mode"] in _MODES else "off"


def mode():
    """Effective mode: needs subscription login for shadow/primary."""
    intent = mode_intent()
    if intent == "off":
        return "off"
    if not has_subscription():
        return "off"
    return intent


def is_on():
    return mode() in ("shadow", "primary", "only")


#: #151 — what each position of his switch means, in his words, for the status line and the card
READER_RULES = {
    "claude": "Claude reads every frame; Grok is not asked",
    "both": "Claude reads every frame; Grok reads only a frame Claude could not, and never slows Claude",
    "grok": "Grok reads every frame; Claude is not asked at all - not first, not as a backup",
}


def reader():
    """#151 HIS SWITCH - who reads a frame on this PC. -> "claude" | "both" | "grok"

    From the INTENT (mode_intent), never the effective mode: Grok-only chosen on a PC whose Grok cannot run is still
    Grok-only - its reads fail and say why - because "no claude as a secondary at all" is the whole point of it."""
    try:
        m = mode_intent()
    except Exception:
        m = "off"
    return {"only": "grok", "shadow": "both", "primary": "both"}.get(m, "claude")


def grok_only_blocked_why():
    """#151 - with the switch at GROK ONLY, why Grok cannot read here right now. -> a sentence, or None when it can."""
    if not _grok_bin():
        return "GROK ONLY is chosen and the Grok CLI is not installed on this PC - frames wait unread (Claude is not used)"
    if not has_subscription():
        return ("GROK ONLY is chosen and Grok is not signed in on this PC (click ⚡ Authorize) - frames wait unread "
                "(Claude is not used)")
    return None


def is_primary():
    """RETIRED 2026-09-30 - always False. Claude is the reader on every PC. BOTH asks Grok only for a frame
    Claude did not read, and never beside a frame Claude already answered.
    Kept as a function so every caller that asked still gets an answer, and the answer is the ruling."""
    return False


def is_shadow():
    return mode() == "shadow"


def set_mode(mode_name, on=None):
    m = str(mode_name or "off").strip().lower()
    if m in ("0", "false", "no"):
        m = "off"
    if m in ("1", "true", "yes", "on"):
        m = "shadow"                   # ON is the extra layer; a "primary" request is mapped by _save_state, the one write guard
    if m not in _MODES:
        m = "off"
    return _save_state(m != "off", m)


def set_on(on):
    return set_mode("shadow" if on else "off")


def primary_retired_note():
    """-> the sentence a surface shows when this PC's saved choice still says primary, else ''."""
    try:
        if _load_state().get("retired"):
            return ("this PC was set to Grok-first; that mode is retired (2026-09-30) - Claude reads every frame "
                    "and Grok reads only a frame Claude could not")
    except Exception:
        pass
    return ""


# v1381.2 — no-spam login: one in-flight process; UI only prompts when needsLogin
_LOGIN_LOCK = threading.Lock()
_LOGIN_PROC = None  # type: ignore
_LOGIN_STARTED_AT = 0.0


def start_login(*, prefer_oauth=True, _popen=None, platform=None):
    """v1381.2 — launch `grok login` so the user can authorize SuperGrok in the browser.

    Pure side-effect helper for the console ⚡ Authorize button. Does NOT spam:
    if already logged in, returns ok without spawning; if a login is already in
    flight, returns the existing status. Never uses API keys.
    """
    global _LOGIN_PROC, _LOGIN_STARTED_AT
    plat = platform if platform is not None else ("win32" if os.name == "nt" else "other")
    bin_path = _grok_bin()
    if not bin_path:
        return {
            "ok": False, "started": False, "reason": "no-cli",
            "msg": "grok CLI not installed — re-run the TV installer or: "
                   "irm https://x.ai/cli/install.ps1 | iex   (Windows) / "
                   "curl -fsSL https://x.ai/cli/install.sh | bash   (Mac)",
            "hasSubscription": False, "cliInstalled": False,
        }
    # REG-1618 - an auth file the far end has stopped accepting is NOT authorized: reopen the browser for it
    if _subscription_logged_in() and not credentials_rejected():
        return {
            "ok": True, "started": False, "reason": "already-authorized",
            "msg": "Grok already authorized on this PC — no re-login needed",
            "hasSubscription": True, "cliInstalled": True,
        }
    with _LOGIN_LOCK:
        # still running?
        if _LOGIN_PROC is not None:
            try:
                if _LOGIN_PROC.poll() is None:
                    return {
                        "ok": True, "started": False, "reason": "in-flight",
                        "msg": "a sign-in window is already open on this PC - finish it there",
                        "hasSubscription": False, "cliInstalled": True,
                        "pid": getattr(_LOGIN_PROC, "pid", None),
                    }
            except Exception:
                pass
            _LOGIN_PROC = None
        env, _stripped = _grok_env()
        args = [bin_path, "login"]
        if prefer_oauth:
            args.append("--oauth")
        try:
            popen = _popen or subprocess.Popen
            if plat == "win32":
                # The CLI prints a URL and then waits for that address to be pasted back
                # when the browser cannot reach its own loopback. pythonw has no console,
                # so this opens one. stdio stays on that console: DEVNULL makes the paste
                # read EOF, and win_quiet hides a new console that brings no STARTUPINFO.
                # A .cmd is not a CreateProcess image. cmd.exe runs it in this same window.
                if str(bin_path).lower().endswith((".cmd", ".bat")):
                    args = ["cmd.exe", "/d", "/c"] + args
                si = subprocess.STARTUPINFO() if hasattr(subprocess, "STARTUPINFO") else None
                kw = {"creationflags": 0x00000010}   # CREATE_NEW_CONSOLE
                if si is not None:
                    si.dwFlags = int(getattr(si, "dwFlags", 0) or 0) | 0x00000001  # STARTF_USESHOWWINDOW
                    si.wShowWindow = 1  # SW_SHOWNORMAL
                    kw["startupinfo"] = si
                _LOGIN_PROC = popen(args, env=env, **kw)
                msg = ("a sign-in window opened on this PC. Finish in the browser. If it does not "
                       "connect, paste the address it shows into that window")
            else:
                _LOGIN_PROC = popen(
                    args, env=env,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                )
                msg = "browser authorize opened - finish the sign-in it opens"
            _LOGIN_STARTED_AT = time.time()
            _STATS["last"] = "login-started"
            _STATS["last_error"] = None; _STATS["last_error_ts"] = None
            return {
                "ok": True, "started": True, "reason": "spawned",
                "msg": msg,
                "hasSubscription": False, "cliInstalled": True,
                "pid": getattr(_LOGIN_PROC, "pid", None),
            }
        except Exception as e:
            _LOGIN_PROC = None
            _STATS["last_error_ts"] = int(time.time() * 1000)
            _STATS["last_error"] = f"login spawn failed: {e}"
            return {
                "ok": False, "started": False, "reason": "spawn-failed",
                "msg": str(e)[:200],
                "hasSubscription": False, "cliInstalled": True,
            }


def login_inflight():
    """True if a grok login process is still running."""
    global _LOGIN_PROC
    if _LOGIN_PROC is None:
        return False
    try:
        if _LOGIN_PROC.poll() is None:
            return True
    except Exception:
        pass
    _LOGIN_PROC = None
    return False


def note_backup(why):
    """One frame asked Grok because Claude did not read. The heart shows the count and the last why.

    Counted even when the backup itself fails: "how often Grok had to step in" includes the frames
    where it was asked and could not answer. A flush failure leaves the count in this process."""
    try:
        _STATS["backup_reads"] = int(_STATS.get("backup_reads") or 0) + 1
        _STATS["backup_why"] = str(why or "")[:160]
        _stats_flush()
    except Exception:
        pass


def status():
    hourly, daily = _budget_counts()
    _sv = stats_view() or {}
    cli = bool(_grok_bin())
    authorized = _subscription_logged_in()
    rejected = bool(cli and authorized and credentials_rejected())   # REG-1618: on disk, refused by the far end
    can_run = bool(cli and authorized)
    inflight = login_inflight()
    return {
        "present": True,
        "feature": "g5_grok_eyes",
        "lane": "subscription-cli",  # NOT api.x.ai
        "power": "grok -p + SuperGrok OIDC login (no API keys)",
        "switch": mode_intent(),
        "mode": mode(),
        # 2026-09-30 - his ruling, on every status: Claude is the reader, Grok only an extra layer when on
        # #151 - his switch: claude | both | grok, and what it means. readerBlocked is said whenever Grok-only cannot read.
        "reader": reader(),
        "readerRule": READER_RULES.get(reader(), READER_RULES["claude"]),
        # REG-2040 - which reasoning effort the reads ask for, and whether this PC's CLI refused it (older build)
        "effort": (None if _EFFORT_STATE.get("refused") else (_EFFORT or "default")),
        "effortRefused": _EFFORT_STATE.get("refused"),
        "readerBlocked": (grok_only_blocked_why() if reader() == "grok" else None),
        # BOTH: how often Grok had to read a frame Claude did not, and the last reason Claude did not.
        "backupReads": int(_sv.get("backup_reads") or 0),
        "backupWhy": _sv.get("backup_why") or None,
        "primaryRetired": primary_retired_note(),
        # v1501 — SAY IT WHEN INTENT AND REALITY DISAGREE. Konyo had this switched to PRIMARY while
        # the effective mode sat at off, and nothing said so: a lane that never attempts never
        # records an error, so calls/errors/last_error all read clean while the eye was dark. The
        # switch is a statement of intent; when the system cannot honour it, that is the headline.
        # v1767 — AND THE THIRD STATE: STARTS FINE, FAILS EVERY CALL. The two above are structural
        # (no binary, not signed in) and both resolve mode() to "off". A lane that is installed,
        # authorised and answering every request with "402 Payment Required" resolves to primary and
        # reported intentBlocked FALSE with an empty blockedWhy — measured live on his console at
        # 165 calls, 107 errors, last_error the 402. So the honesty field invented precisely to
        # publish intent-vs-reality said nothing was wrong while the eye had been dark for a hundred
        # calls. The v1501 note above describes the mirror ("a lane that never attempts never records
        # an error"); this is the case where it DOES attempt, DOES record, and the headline still
        # reads clean. A hard stop is not a flaky call: it is stated by the far end and it will not
        # clear by retrying, so it belongs in the headline exactly like the other two.
        "intentBlocked": bool(mode_intent() != "off" and (mode() == "off" or _hard_stop_why())),
        "blockedWhy": ("" if mode_intent() == "off"
                       else (_hard_stop_why() if mode() != "off"
                             else ("the grok CLI is not installed where this app can see it"
                             if not _grok_bin() else
                             ("not signed in to SuperGrok — click Authorize" if not _subscription_logged_in()
                              else "the lane is switched on but the app could not start it")))),
        # v2340 — CALLS THE BREAKER DID NOT SPEND. A saving nobody can see reads exactly like a
        # feature that was never built, and this one is the difference between 1 failed call and
        # the 1963 his console had banked. Named separately from skipped_budget because they are
        # different refusals: one is our own rationing, the other is the far end saying no.
        "skippedBlocked": int(_sv.get("skipped_blocked") or 0),
        "on": is_on(),
        "hasKey": can_run,       # UI compat: means "can run", not API key
        "hasSubscription": can_run,
        "cliInstalled": cli,
        "authorized": authorized,
        "needsInstall": not cli,
        "needsLogin": bool(cli and (not authorized or rejected)),
        "credentialsRejected": rejected,
        "loginInflight": inflight,
        "grokBin": _grok_bin() or None,
        "model": "subscription-cli",
        "budget": {
            "hourlyUsed": hourly, "hourlyMax": _HOURLY_MAX,
            "dailyUsed": daily, "dailyMax": _DAILY_MAX,
        },
        "stats": _sv,
        "sidecar": {
            "hint": "python3 tv/g5_sidecar/server.py  (uses same subscription CLI)",
        },
    }


# ── budget (local counters, like intake_local) ────────────────────────────────
# v1698 — TWO WRITERS, TWO CLOCKS, ONE FILE. g5_subscription_budget.json is written by BOTH this
# module (time.time() -> SECONDS) and tv/intake_grok_sub.mjs (Date.now() -> MILLISECONDS), and
# neither knew about the other. Both halves were broken, in opposite directions:
#
#   Python reading a Node row:  now(1786390330) - 1786385809525 = -1,784,599,419,194 -- hugely
#     NEGATIVE, so `< 86400` is ALWAYS true. Every ms row sits ~1.78 MILLION MILLION seconds in the
#     "future" and can never age out. hourlyUsed only ever CLIMBS.
#   Node reading a Python row:  now_ms - t ~= 20,655 days -- outside 24h, so DROPPED. Node deletes
#     every row Python writes and saves the pruned list back.
#
# At 30 accumulated rows _budget_ok() returns False forever and the second eye reports
# "grok-subscription hourly cap (30/30)" while the real call rate is ZERO. Measured 2026-08-10:
# 9 of 30, i.e. twenty-one Node calls from switching itself off. That is the exact failure this
# lane exists to prevent -- the eye goes dark behind a LEGITIMATE-LOOKING reason, same shape as
# v1501. The tell was on screen and walked past: hourlyUsed 9 alongside stats.calls 0.
#
# THE FIX IS ONE UNIT, DECLARED ONCE, NORMALISED ON READ -- never a conversion at a single call
# site, which is just the second writer again. Canonical is MILLISECONDS: his file already holds
# ms rows, so nothing has to be migrated and no real call is lost. A row in the other unit is
# still understood rather than dropped, because a budget that silently forgets calls is as wrong
# as one that never forgets them.
_MS_FLOOR = 1e11   # 1e11 ms = 1973; 1e11 s = year 5138. Nothing real lands between the two.


def _as_ms(t):
    """One timestamp -> milliseconds, whichever unit it was written in."""
    v = float(t)
    return v * 1000.0 if v < _MS_FLOOR else v


def _budget_path():
    """v1698 — overridable so a guard can run without touching his live budget file.
    Read per call, not frozen at import, so a test can point it somewhere after importing."""
    return os.environ.get("G5_BUDGET_PATH") or _BUDGET_PATH


def _budget_load():
    try:
        p = _budget_path()
        if not os.path.isfile(p):
            return {"calls": []}
        return json.loads(open(p, encoding="utf-8").read()) or {"calls": []}
    except Exception:
        return {"calls": []}


def _budget_save(state):
    try:
        with open(_budget_path(), "w", encoding="utf-8") as fh:
            json.dump(state, fh)
    except Exception:
        pass


# ── stats, SHARED ACROSS PROCESSES ────────────────────────────────────────────
# v1711 — stats.calls WAS PERMANENTLY 0 AND THE FILE ALREADY SAID SO.
# The note at the budget block above records the tell verbatim: "hourlyUsed 9 alongside
# stats.calls 0." Two counters over the same events disagreed, one was believed, and the
# contradiction sat in a comment instead of being the finding.
#
# The cause is a process boundary. The eye is CALLED from the agent (tv_diablo.py:4855),
# which control_app.py:1858 launches as a separate `subprocess.Popen`. Every _STATS["calls"] += 1
# lands in the AGENT's memory. /api/g5_status is served by CONTROL_APP, which imported its own
# copy of this module and reads its own dict — one that nothing ever increments. So the panel was
# not reporting a quiet eye; it was reporting a different process's blank counter.
#
# hourlyUsed was right for exactly one reason: the budget goes through a FILE. So the stats do too.
# Same shape, same override-per-call env hook, same swallow-on-failure — a stats write must never
# be able to break a vision call.
def _g5_stats_root():
    """v1869 — the same one rule: a fixture's reads are not his G5 statistics.

    v1883 — AND THE FALLBACK MUST APPLY THE RULE, NOT SURRENDER TO HIS TREE. This asked tv_diablo
    for the answer and, on any failure, returned his own directory — and the import CAN fail here,
    because a control app spawned by a harness imports these two modules in an order this one does
    not control. Measured after v1874 with his console down: six harnesses still rewrote his live
    g5_stats.json (test_console_fleet, robot_smoke, test_roundtrip_sim, test_button_matrix,
    test_vault_lane, test_inbox_engine), every one of them with TV_HIST correctly sandboxed.
    An `except: return his_directory` is a fallback that fails toward the thing being protected.
    The rule is six lines; it is inlined rather than surrendered. [[feedback-fixtures-never-touch-live-data]]
    """
    _here = os.path.dirname(os.path.abspath(__file__))
    try:
        import tv_diablo as _tvd
        return _tvd._fixture_root(_here)
    except Exception:
        pass
    # ⚠⚠ v2937 — blank-after-strip is nobody asking, and a RELATIVE value resolves against
    # the process CWD so it has no fixed meaning. MEASURED from the repo root with the import
    # forced to fail and TV_HIST="   ": this planted its file at `<repo>/   `. The narrowing
    # reached `_fixture_root` at v2932 and never reached the copies. [[copy-drift]]
    hist = (os.environ.get("TV_HIST") or "").strip()
    if hist and os.path.isabs(hist):
        try:
            # v1897 — the SAME comparison tv_diablo makes, and it must stay the same: on Windows a
            # raw startswith on paths of differing case decides a fixture is his real tree.
            import tv_diablo as _tvd2
            if not _tvd2._under(hist, _here):
                return os.path.realpath(hist)
        except Exception:
            try:
                a, b = os.path.normcase(os.path.realpath(hist)), os.path.normcase(os.path.realpath(_here))
                if not (a == b or a.startswith(b + os.sep)):
                    return a
            except Exception:
                pass
    return _here


_STATS_PATH = os.path.join(_g5_stats_root(), "g5_stats.json")
_COUNTERS = ("calls", "ok", "errors", "skipped_budget", "skipped_blocked", "shadow", "primary", "backup_reads")


def _stats_path():
    """Overridable per call so a guard never writes his live stats file (mirrors _budget_path)."""
    return os.environ.get("G5_STATS_PATH") or _STATS_PATH


def _stats_load():
    try:
        p = _stats_path()
        if not os.path.isfile(p):
            return {}
        return json.loads(open(p, encoding="utf-8").read()) or {}
    except Exception:
        return {}


def _stats_flush():
    """Publish this process's counters into the shared file, ADDING deltas rather than
    overwriting — control_app and the agent both call the eye, so a last-writer-wins save
    would silently erase the other process's calls (the very defect this replaces).

    ⚠ v2341 — IT TAKES _LOCK, AND _LOCK IS NOT REENTRANT. Never call this from inside a
    `with _LOCK:` block: threading.Lock() (line ~59) deadlocks on re-acquisition, and the lane
    would hang rather than fail, which is the worst failure a reader can have.

    This matters because a cross-family review of v2340 correctly observed that ~33 of the 34
    `_STATS` writes happen outside any lock, and the obvious remedy is to wrap them. Do not.
    The DURABLE record is already safe — the load, the merge, the write and the counter reset
    all happen inside this one lock — so the only thing that can race is an in-memory counter
    between two flushes, and it can drift by a count or two. Trading a cosmetic drift for a
    hang is a bad trade. If real serialisation is ever wanted here, change _LOCK to an RLock
    FIRST. Guard: TestV2341FlushIsNeverCalledHoldingTheLock."""
    try:
        with _LOCK:
            base = _stats_load()
            merged = dict(base)
            for k in _COUNTERS:
                merged[k] = int(base.get(k) or 0) + int(_STATS.get(k) or 0)
            for k in ("last", "last_error", "last_error_ts", "lane", "stripped_api_env", "backup_why"):
                if _STATS.get(k) is not None:
                    merged[k] = _STATS[k]
            merged["ts"] = time.time()
            with open(_stats_path(), "w", encoding="utf-8") as fh:
                json.dump(merged, fh)
            for k in _COUNTERS:          # deltas are banked; reset so they cannot double-count
                _STATS[k] = 0
    except Exception:
        pass


#: REG-1618 — the refusals that mean THE SIGN-IN ITSELF is dead. ~/.grok/auth.json can still be on disk while the
#: session behind it has been revoked or has expired, and then every call answers 401: that is a disconnection, the
#: only cure is signing in again, and the GROK lamp and the login button must both say so (they used to read "linked"
#: and start_login refused to reopen the browser because the file was there). One list, used by both.
_CRED_REJECT_SAY = "Grok rejected the credentials — sign in again"


def _status_code(n):
    """REG-1631 — a status code as the far end states it: a WHOLE number, never digits inside a longer one, and never a
    duration or a size. MEASURED on the substring needles (the Grok CLI look at v3534 pointed at them): "timed out after
    1401 ms" and a session id holding ...401... both read as a revoked sign-in and lit SIGN IN, and "read 34020 bytes"
    read as an exhausted balance - which also holds the lane for _HARD_STOP_RETRY_S."""
    return _re.compile(r"(?<![\w.])%s(?![\w.])(?!\s*(?:ms|s|secs?|seconds?|bytes?|[kmg]i?b)\b)" % n)


_CRED_REJECT_NEEDLES = (_status_code("401"), _re.compile(r"unauthori[sz]ed"), _re.compile(r"invalid api key"))

_HARD_STOPS = (
    # each pattern is a refusal the FAR END stated; retrying cannot clear any of them
    (_status_code("402"), "the Grok balance is exhausted — the second eye cannot read until it is topped up"),
    (_re.compile(r"payment required"), "the Grok balance is exhausted — the second eye cannot read until it is topped up"),
    (_re.compile(r"balance exhausted"), "the Grok balance is exhausted — the second eye cannot read until it is topped up"),
    # REG-1631 — "insufficient" alone is also Windows' own "insufficient system resources" (the 8 GB ALT under load):
    # only a shortfall of credit is this lane's refusal
    (_re.compile(r"insufficient[\s_-]*(?:credits?|balance|funds?|quota)"), "the Grok account has no credit left for this lane"),
) + tuple((_n, _CRED_REJECT_SAY) for _n in _CRED_REJECT_NEEDLES)


# v2341 — how long a stated refusal stands before the lane probes once more. Long enough that a
# dead balance costs 2 calls an hour instead of thousands; short enough that a top-up is noticed
# within half an hour without him having to press anything.
_HARD_STOP_RETRY_S = 1800.0


_LOOK_IT_UP = object()   # "consult the live stats" — distinct from an explicit None meaning "no error"


def _hard_stop_why(last_error=_LOOK_IT_UP):
    """A refusal the far end STATED, in his words rather than the CLI's.

    v1767 — only the LAST call is consulted, deliberately. A tally of historic errors cannot tell a
    lane that failed all morning and recovered from one that is dead right now, and a lane that has
    recovered must stop announcing a blockage. Silence here means the last call did not hard-stop;
    it never means the lane was checked and found healthy, which is what `calls`/`errors` are for.
    """
    try:
        if last_error is _LOOK_IT_UP:
            last_error = (stats_view() or {}).get("last_error")
    except Exception:
        return ""
    blob = str(last_error or "").lower()
    if not blob:
        return ""
    for needle, say in _HARD_STOPS:
        if needle.search(blob):
            return say
    return ""


def credentials_rejected(last_error=_LOOK_IT_UP):
    """REG-1618 — did the far end reject this PC's sign-in on the LAST call? -> bool

    Same one-call rule as _hard_stop_why: a lane that failed at noon and has read fine since is not signed out now."""
    try:
        if last_error is _LOOK_IT_UP:
            last_error = (stats_view() or {}).get("last_error")
    except Exception:
        return False
    blob = str(last_error or "").lower()
    return bool(blob) and any(n.search(blob) for n in _CRED_REJECT_NEEDLES)


def stats_view():
    """What /api/g5_status must show: the shared totals, plus anything this process holds
    that has not been flushed yet."""
    base = _stats_load()
    out = dict(_STATS)
    for k in _COUNTERS:
        out[k] = int(base.get(k) or 0) + int(_STATS.get(k) or 0)
    # v2119 (#121) — last_error_ts RIDES WITH last_error, or the sentence reads as now. _stats_flush
    # persists the stamp (it is in the flushed key list) but this hydration never restored it, so
    # after ANY restart the remembered error came back off disk with no stamp and the EYES card
    # printed "age unknown" — the exact phrase that card was built to remove. MEASURED on his live
    # console at v2119: the card still said "age unknown" beside a remembered 208/200 quota error.
    # [[stale-reading]] [[the-unjoined-end]]
    for k in ("last", "last_error", "last_error_ts", "backup_why"):
        if out.get(k) is None and base.get(k) is not None:
            out[k] = base[k]
    return out


def _budget_counts(now=None):
    now_ms = _as_ms(now) if now is not None else time.time() * 1000.0
    state = _budget_load()
    calls = [_as_ms(t) for t in (state.get("calls") or [])]
    calls = [t for t in calls if 0 <= now_ms - t < 86400.0 * 1000.0]
    hour = [t for t in calls if now_ms - t < 3600.0 * 1000.0]
    with _LOCK:
        _CALL_LOG[:] = calls
    return len(hour), len(calls)


def _budget_ok():
    if _HOURLY_MAX <= 0 or _DAILY_MAX <= 0:
        return False
    hourly, daily = _budget_counts()
    return hourly < _HOURLY_MAX and daily < _DAILY_MAX


def _budget_record():
    # v1698 — writes MILLISECONDS, the one canonical unit both writers now agree on.
    now_ms = time.time() * 1000.0
    state = _budget_load()
    calls = [_as_ms(t) for t in (state.get("calls") or [])]
    calls = [t for t in calls if 0 <= now_ms - t < 86400.0 * 1000.0]
    calls.append(now_ms)
    _budget_save({"calls": calls, "last": now_ms})
    with _LOCK:
        _CALL_LOG[:] = calls


# ── vision via grok -p (subscription) ─────────────────────────────────────────
def g5_vision_read(image_path, prompt=None, *, force=False):
    """Vision read via local `grok -p` SuperGrok login. No API keys.

    Returns None if OFF / not logged in / over budget / error.
    force=True: sidecar prove (ignore mode, still requires subscription login).
    """
    if not force and not is_on():
        return None
    if not has_subscription():
        return None
    # ══ v2340 — A REFUSAL THE FAR END STATED IS NOT WORTH ASKING AGAIN ════════════════════════
    # _HARD_STOPS has existed for a while and _hard_stop_why() reads it correctly — but the ONLY
    # two places that consulted it were both inside the STATUS payload. Nothing checked it before
    # spending a call. So the lane reported "the Grok balance is exhausted" honestly and then kept
    # asking anyway: measured on his live console, calls 2842 / errors 1963, a 69% failure rate
    # against a 402 that no amount of retrying can clear. A gate whose output nobody parses is not
    # a gate. [[the-unjoined-end]] [[paid-work-with-no-memory]]
    #
    # ⚠ IT MUST NOT TOUCH last_error, AND THAT IS THE WHOLE TRICK. _hard_stop_why() decides by
    # reading last_error, so writing a friendlier sentence here would erase the very evidence the
    # latch stands on and the breaker would open for exactly one call, then close, for ever. The
    # skip is recorded as its own COUNTER instead — a call refused is not a call failed, the same
    # distinction _budget_ok() draws two lines below.
    #
    # `force` still goes through: a sidecar prove is a person deliberately asking, and the answer
    # to "is it really still refusing" must come from the far end, not from this latch.
    if not force:
        _blocked = _hard_stop_why()
        if _blocked:
            # ⚠ v2341 — A BREAKER WITH NO WAY OUT IS A DEADLOCK, AND v2340 SHIPPED ONE.
            # The latch is decided by reading last_error, and v2340 then prevented the only call
            # that could ever update it. Measured: 20 reads after the refusal, 0 calls attempted,
            # latch still set — so the morning he tops the balance up, the lane would never find
            # out. It refused for the right reason and could not stop refusing.
            # One probe per window instead: 2 calls an hour while blocked rather than the 1963 it
            # had banked, and it heals itself the first time the far end says yes.
            # An error with no usable timestamp probes NOW — an unknown age must not read as
            # "recent". [[unknown-stays-unknown]] [[feedback-threshold-above-the-ceiling]]
            _ts = _STATS.get("last_error_ts") or 0
            try:
                _age_s = time.time() - (float(_ts) / 1000.0)
            except (TypeError, ValueError):
                _age_s = _HARD_STOP_RETRY_S + 1
            if _age_s < _HARD_STOP_RETRY_S:
                _STATS["skipped_blocked"] += 1
                _stats_flush()
                return None
            # fall through: ONE probe. Only the far end can say whether it is still refusing.
    if not _budget_ok():
        # v1711 — this returned None with last_error untouched, so a budget refusal was
        # INDISTINGUISHABLE on the panel from an eye that was simply never asked. "The eye is
        # quiet" and "the eye is rationed" are different facts and he acts on them differently.
        _STATS["skipped_budget"] += 1
        h, d = _budget_counts()          # (this hour, today)
        _STATS["last_error_ts"] = int(time.time() * 1000)
        _STATS["last_error"] = ("budget: %s/%s this hour, %s/%s today — refused, not failed"
                                % (h, _HOURLY_MAX, d, _DAILY_MAX))
        _stats_flush()
        return None

    path = os.path.abspath(str(image_path or ""))
    if not path or not os.path.isfile(path):
        return None

    bin_path = _grok_bin()
    if not bin_path:
        _STATS["last_error_ts"] = int(time.time() * 1000)
        _STATS["last_error"] = "grok CLI not on PATH"
        _stats_flush()
        return None

    text_prompt = (prompt or _DEFAULT_VISION_PROMPT)
    if "{path}" in text_prompt:
        text_prompt = text_prompt.format(path=path)
    else:
        text_prompt = (
            text_prompt
            + "\n\nThe screenshot is at: " + path
            + " — open it with read_file first. Reply STRICT JSON only."
        )

    # Work in throwaway cwd so monorepo project rules don't load
    work = tempfile.mkdtemp(prefix="tvd-g5-")
    env, stripped = _grok_env(lean=True)
    _log_auth_once(stripped)

    # Prefer adding image dir for tools
    img_dir = os.path.dirname(path)
    args = _vision_args(bin_path, text_prompt, work)
    # Allow reading the frame directory
    if img_dir and os.path.isdir(img_dir):
        # some builds support --add-dir; if not, path is absolute and read_file still works
        pass

    t0 = time.time()
    try:
        r = subprocess.run(
            args,
            capture_output=True,
            text=True, encoding="utf-8", errors="replace",
            timeout=_TIMEOUT_S,
            stdin=subprocess.DEVNULL,
            env=env,
            cwd=work,
        )
        # REG-2040 - AN OLDER CLI THAT DOES NOT KNOW --effort MUST NOT LOSE EVERY READ. Retry once without it and stop
        # sending it for this process; the reason is kept so the doctor can say which PC runs an older Grok.
        if r.returncode != 0 and not (r.stdout or "").strip() and _effort_refused(args, r.stderr):
            _EFFORT_STATE["refused"] = (r.stderr or "")[:160]
            args = _vision_args(bin_path, text_prompt, work)
            r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace",
                               timeout=_TIMEOUT_S, stdin=subprocess.DEVNULL, env=env, cwd=work)
    except subprocess.TimeoutExpired:
        _STATS["errors"] += 1
        _STATS["calls"] += 1
        _STATS["last_error_ts"] = int(time.time() * 1000)
        _STATS["last_error"] = f"grok -p timeout {_TIMEOUT_S:.0f}s"
        _stats_flush()
        _cleanup(work)
        return None
    except Exception as e:
        _STATS["errors"] += 1
        _STATS["calls"] += 1
        _STATS["last_error_ts"] = int(time.time() * 1000)
        _STATS["last_error"] = str(e)[:160]
        _stats_flush()
        _cleanup(work)
        return None

    _cleanup(work)
    out = (r.stdout or "").strip()
    _STATS["calls"] += 1
    _STATS["last"] = time.strftime("%Y-%m-%d %H:%M:%S")

    if r.returncode != 0 and not out:
        _STATS["errors"] += 1
        err = (r.stderr or "")[:200]
        _STATS["last_error_ts"] = int(time.time() * 1000)
        _STATS["last_error"] = f"grok exit {r.returncode}: {err}"
        _stats_flush()
        return None

    parsed = _loose_parse(out)
    if parsed is None:
        _STATS["errors"] += 1
        # v1759 — SAY WHAT THE CLI ACTUALLY SAID. The grok CLI reports an API refusal in its OUTPUT
        # and still exits 0, so the returncode check above never fires and this branch was the one
        # that ran — recording "no-json from grok -p", which points at a parser. Measured on his
        # machine while diagnosing a permanently silent second eye:
        #
        #     Internal error: {"message": "API error (status 402 Payment Required):
        #                      Grok Build usage balance exhausted", "http_status": 402}
        #
        # Every guard above was green (is_on, has_subscription, budget, binary found), so the lane
        # reported ready and answered nothing, and the one field that could have said why said
        # "no-json". A reader chasing that goes to the parser; the actual fix is a billing page.
        # The real message is now carried through, and an HTTP status is named explicitly.
        _err = (out or (r.stderr or ""))[:400].replace("\n", " ").strip()
        _status = None
        _m = _re.search(r"status (\d{3})", _err) or _re.search(r"http_status\"?\s*:\s*(\d{3})", _err)
        if _m:
            _status = _m.group(1)
        _STATS["last_error_ts"] = int(time.time() * 1000)
        _STATS["last_error"] = (("grok HTTP %s — %s" % (_status, _err[:220])) if _status
                                else ("grok gave no JSON — said: %s" % (_err[:220] or "(nothing)")))
        _stats_flush()
        return None

    _budget_record()
    _STATS["ok"] += 1
    # ⚠ v2341 — A LANE THAT HAS RECOVERED MUST STOP ANNOUNCING A BLOCKAGE. _hard_stop_why()'s own
    # docstring says exactly that, and nothing on this path had ever honoured it: after five
    # SUCCESSFUL reads it still reported "the Grok balance is exhausted". Harmless while it was
    # only a caption; the moment v2340 made that caption gate the calls, a successful probe would
    # re-latch on its own stale evidence and the window would reopen every 30 minutes for ever.
    # Two halves of one fix — the retry window cannot help if success never clears the reason.
    _STATS["last_error"] = None
    _STATS["last_error_ts"] = None
    m = mode() if not force else "force"
    if m == "shadow":
        _STATS["shadow"] += 1
    elif m == "primary":
        _STATS["primary"] += 1
    elif m == "only":
        _STATS["only"] += 1
    _stats_flush()
    parsed["model"] = "grok-subscription-cli"
    parsed["mode"] = "g5-" + m
    parsed["escalated"] = False
    parsed["ms"] = int((time.time() - t0) * 1000)
    parsed["_raw_txt"] = out[:2048]
    parsed["_g5"] = True
    parsed["_lane"] = "subscription-cli"
    return parsed


def picture_id(path):
    """-> a short content hash naming the PICTURE at `path`, or None when it cannot be read.

    ⚠⚠ #197 — A BASENAME NAMES A PATH, NOT A PICTURE. `read.jpg` is ONE scratch file the capture
    loop rewrites on every read (tv_diablo.py writes FRAMES/read.jpg at five sites), and
    `read_<rid>_<n>.jpg` is a per-reader scratch file; only `f_<epoch-ms>.jpg` is written once.
    MEASURED on his store: read.jpg carries 131 of 1,596 both-answered rows, and the reducer
    published them as ONE frame disagreeing with itself. A reducer cannot recover an identity the
    log never stored, so the writer stores one. None is UNKNOWN, never a match.
    [[heart-first]] [[zero-needs-a-denominator]]
    """
    try:
        h = hashlib.sha1()
        with open(str(path), "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 16), b""):
                h.update(chunk)
        return h.hexdigest()[:16]
    except Exception:
        return None


def snapshot_picture(path):
    """Copy the picture at `path` to a private file. -> (snapshot_path, picture_id) | (None, None)

    ⚠⚠ v3483 — THE SECOND EYE ON v3479 WAS RIGHT: the two hashes were not the bytes the two eyes
    read. g5_vision_read hands the Grok CLI the LIVE path, and the CLI opens it whenever it
    chooses during a call that can run for minutes, so a hash taken before the thread and another
    taken at log time bracket a window — they never name the picture Grok actually saw. The
    capture loop can rewrite read.jpg after Grok opened it and the row would read "moved" while
    both eyes saw one picture. So the shadow read is handed a SNAPSHOT taken right after Claude's
    read: both eyes see the same bytes by construction, and the id is computed from the copy.
    (None, None) when the copy cannot be made — the caller falls back to the live path and the
    row then carries no after-id, which is UNKNOWN, never a match. [[unknown-stays-unknown]]
    """
    try:
        fd, snap = tempfile.mkstemp(prefix="tvd-g5-shot-", suffix=os.path.splitext(str(path))[1])
        h = hashlib.sha1()
        with os.fdopen(fd, "wb") as out, open(str(path), "rb") as src:
            for chunk in iter(lambda: src.read(1 << 16), b""):
                h.update(chunk)
                out.write(chunk)
        return snap, h.hexdigest()[:16]
    except Exception:
        try:
            os.remove(snap)
        except Exception:
            pass
        return None, None


def g5_shadow_log(claude_result, grok_result, image_path="", picture=None, shown=None):
    # `picture` names the bytes Claude read: snapshot_picture()'s id (or picture_id() of the live
    # file when no snapshot could be made), taken by the CALLER before the shadow thread starts.
    # `picture_after` names the bytes GROK WAS SHOWN: the snapshot `shown`, re-hashed after its read.
    # ⚠ v3483 — with no snapshot there is NO after-id. Re-hashing the live path at log time (v3479)
    # measured a window, not what Grok saw; None says so, and the reducer puts that row in no frame.
    _after = picture_id(shown) if shown else None
    try:
        rec = {
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            "lane": "subscription-cli",
            "image": os.path.basename(str(image_path or "")),
            "picture": picture,
            "picture_after": _after,
            "claude_names": (claude_result or {}).get("names") if isinstance(claude_result, dict) else None,
            "grok_names": (grok_result or {}).get("names") if isinstance(grok_result, dict) else None,
            "claude_scene": (claude_result or {}).get("scene") if isinstance(claude_result, dict) else None,
            "grok_scene": (grok_result or {}).get("scene") if isinstance(grok_result, dict) else None,
        }
        with open(_SHADOW_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _cleanup(work):
    try:
        shutil.rmtree(work, ignore_errors=True)
    except Exception:
        pass
    # v3525 (REG-1549) — and the Grok session directory this read minted. Grok keeps one per cwd, and every
    # read has its own throwaway cwd, so they were never reused and never removed: 3,749 of them (4.7 GB) on
    # his Mac, 2,642 (932 MB) on the ALT. Matched by this read's unique tvd-g5- name only, so none of his
    # own sessions can match.
    try:
        base = os.path.basename(str(work).rstrip("/\\"))
        sd = os.path.join(_real_grok_home(), "sessions")
        if base.startswith("tvd-g5-") and len(base) > len("tvd-g5-") and os.path.isdir(sd):
            for name in os.listdir(sd):
                if session_tail(name) == base:
                    _drop_session_dir(os.path.join(sd, name))
            _sweep_stale_sessions(sd)
    except Exception:
        pass


#: REG-1687 — a read's own Grok session directory older than this is a leftover nobody will come back for
G5_SESSION_STALE_S = 600


def session_tail(name):
    """REG-2731 (the #231 eye on v3819) - THE LAST FOLDER OF THE CWD A GROK SESSION DIRECTORY WAS MINTED FOR. Grok names
    the directory after its --cwd, every separator encoded (%2F on a Mac, %5C on Windows). -> the last segment ('' for a
    name that is not an encoded path). The drop and the sweeps match on this, never on a substring of the whole name: a
    substring also matches a longer folder, or one of his own whose path merely contains the mark."""
    return _re.split(r"%2F|%5C", str(name or ""), flags=_re.I)[-1]
#: #151 — the throwaway --cwd names a Grok session directory can carry: a G5 read's (tvd-g5-) and the intake lane's
#: (intake_grok_sub.mjs, tvd-intake-g5-). Matching only the first left every intake session behind (55 on his Mac).
G5_SESSION_MARKS = ("tvd-g5-", "tvd-intake-g5-")


def _drop_session_dir(path, attempts=4, pause_s=0.25):
    """REG-1687 — remove one Grok session directory a read minted. -> True when it is gone.

    MEASURED on his ALT 2026-10-01: 111 of them (86.6 MB) survived 09-30/10-01 although every read "removed" its own,
    because rmtree(ignore_errors=True) failed SILENTLY while grok still held a file there (chat_history.jsonl.lock) -
    Windows cannot delete an open file. So: retry briefly, and when it is still there COUNT it, never pretend."""
    for k in range(max(1, int(attempts))):
        shutil.rmtree(path, ignore_errors=True)
        if not os.path.exists(path):
            return True
        if k + 1 < attempts:
            time.sleep(pause_s)
    _STATS["session_dirs_left"] = int(_STATS.get("session_dirs_left") or 0) + 1
    return False


def _sweep_stale_sessions(sd, now=None):
    """REG-1687 — every read also removes the leftovers of EARLIER reads: a session directory whose name carries a
    read's unique tvd-g5- cwd and is older than G5_SESSION_STALE_S. Matched by that name only, so none of his own
    sessions can match, and a concurrent read's fresh one is left alone. -> how many it removed, or None when the folder
    could not be listed (UNKNOWN, with the reason in _STATS["session_sweep_unread"] - never "0 swept")."""
    now = time.time() if now is None else float(now)
    gone = 0
    try:
        names = os.listdir(sd)
    except OSError as e:
        _STATS["session_sweep_unread"] = "%s: %s" % (type(e).__name__, str(e)[:80])
        return None
    for name in names:
        _tail = session_tail(name)
        if not any(_tail.startswith(m) for m in G5_SESSION_MARKS) or _tail == "tvd-g5-home":
            continue
        p = os.path.join(sd, name)
        try:
            if now - os.path.getmtime(p) < G5_SESSION_STALE_S:
                continue
        except OSError:
            continue
        if _drop_session_dir(p, attempts=2, pause_s=0.1):
            gone += 1
    if gone:
        _STATS["session_dirs_swept"] = int(_STATS.get("session_dirs_swept") or 0) + gone
    return gone


def _loose_parse(txt):
    if not txt:
        return None
    try:
        a, b = txt.find("{"), txt.rfind("}")
        if a < 0 or b <= a:
            return None
        j = json.loads(txt[a:b + 1])
        if not isinstance(j, dict):
            return None
        names = j.get("names")
        # REG-1716 — every rewrite below is RECORDED (`_g5_fixed`), because the read it leaves behind looks like one the
        # model really gave: names that were a string, a scene that was absent and a JSON true all became a bare,
        # confident gameplay row, and the launcher judge counts that shape as the game. tv_diablo carries this list
        # into the journal row's parse audit, beside _parse_read's own. [[unknown-stays-unknown]]
        _fixed = []
        if not isinstance(names, list):
            if names not in (None, "", []):
                _fixed.append({"field": "names", "why": "not-a-list", "from": str(names)[:40]})
            names = []
        if "scene" not in j:
            _fixed.append({"field": "scene", "why": "absent-scene-default"})
        # ⚠⚠ v3453 — A null IS NOT THE NAME "None", AND str() MANUFACTURES ONE.
        # v3450 taught names_key to skip `x is None`. That guard sits DOWNSTREAM of this line, and
        # by the time the reducer sees a row the null has already become the four-character string
        # "None" — which is truthy, survives the filter, and is counted as an item he owns. So the
        # guard could never fire on logged data: it defends a shape this pipeline never writes.
        # MEASURED: _loose_parse of {"names": ["Shako", null]} returned ['Shako', 'None'] and
        # names_key of that is ('none', 'shako').
        # ⚠ IT MUST BE FIXED HERE, not downstream. Once the null is the string "None" the fact
        # that it WAS a null is gone, and nothing can tell it from a model that literally answered
        # "None". [[heart-first]] §6 — persist what you knew. [[the-unjoined-end]]
        j["names"] = [str(x).strip() for x in names if x is not None and str(x).strip()][:60]
        j.setdefault("area", "")
        j.setdefault("scene", "gameplay")
        j.setdefault("tz", [])
        j.setdefault("stashTab", "")
        j.setdefault("names_loc", {})
        j.setdefault("sockets", {})
        j.setdefault("discovered", [])
        if not isinstance(j.get("tz"), list):
            j["tz"] = []
        if isinstance(j.get("conf"), bool):
            # REG-1721 (the #231 code seat + the v3556 eye) - refused, it stays UNKNOWN: the next lines used to turn it
            # into 0.0, a confidence the reader never gave (every consumer goes through _parse_read, which takes None)
            _fixed.append({"field": "conf", "why": "a-bool-is-not-a-confidence", "from": str(j.get("conf"))})
            j["conf"] = None
        else:
            try:
                j["conf"] = float(j.get("conf") if j.get("conf") is not None else 0.0)
            except Exception:
                j["conf"] = None        # REG-1723 - a conf that is not a number is UNKNOWN, never a measured 0.0
        if _fixed:
            j["_g5_fixed"] = _fixed
        return j
    except Exception:
        return None
