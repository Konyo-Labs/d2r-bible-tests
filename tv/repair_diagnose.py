# -*- coding: utf-8 -*-
"""v3862 (item 9) - A FAULT THE REPAIR BOOK DOES NOT KNOW IS DIAGNOSED BY THIS PC'S OWN CLAUDE, WHICH PROPOSES AND NEVER RUNS.

His ask 2026-11-05: "can this have been like done automatically by an AI claude on his own end?", then the ruling that
KNOWN errors fix themselves (tv/repair_book.py) while unknown ones are seen online. This is the second line for the
unknown ones: the PC's signed-in Claude reads the eagle check that went MISSING (tv/console_doctor.py) and what it reads,
and writes CAUSE / FIX / VERIFY. It may READ files only (--allowedTools Read): a new fix is never run by itself - it is
reviewed once and then joins the book, where it runs automatically everywhere.

The spend is bounded on purpose (MEASURED in October: a re-read loop maxed his weekly plan three times):
  · only a miss this PC has never diagnosed (a fault that clears and returns is new again);
  · at most MAX_PER_DAY a day per PC, one at a time, each bounded by TIMEOUT_S and MAX_TURNS;
  · never under D2R_NO_CLAUDE=1 (every law and every runner), never with no `claude` on PATH.
The proposal (scrubbed of paths) rides the presence row beside its miss, so it reaches the overwatch line.
"""
import io
import json
import os
import re
import shutil
import subprocess
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
STATE_NAME = ".repair_diagnoses.json"         # gitignored, per PC
MAX_PER_DAY = 2
#: REG-3251 (the Grok CLI on REG-3237, #231 6680104597) - {state file: {"seen": {...}, "failed": {...}}}: what landed in
#: THIS process and would not save, so the next pass does not ask it again. The day's spend is no longer kept here: each
#: ask is RESERVED on disk before it is made, so neither a failed save nor a kill can re-open the allowance.
_KEPT = {}
CUT_OFF = "its last ask was cut off before its answer was saved (the console stopped mid-ask) - it is asked again tomorrow"
TIMEOUT_S = 300
#: v3867 (#17) - MEASURED 2026-11-06: his Mac held 8 unknown faults, both of the day's asks were spent and NEITHER landed
#: (.repair_diagnoses.json: n 2, seen {}). A hand run of the same ask answered in 72 s and named the cause itself: 8 turns
#: of Read-only paging through a ~12k-line console_doctor.py, inside a repo whose CLAUDE.md orders skill loads before the
#: first tool call. The ask now runs OUTSIDE the project (tv_diablo's lean form: --add-dir, user settings only, no MCP, no
#: session) with Grep beside Read - still read-only - and 20 turns.
MAX_TURNS = 20
ALLOWED_TOOLS = "Read,Grep"
DEAD_SEAT = ("not logged in", "please run /login", "invalid api key", "usage limit", "rate limit", "credit balance")
_PATHISH = re.compile(r"([A-Za-z]:\\[^\s'\"]+|/(?:Users|home|private|tmp|var)/[^\s'\"]+)")


def scrub(text, limit):
    return _PATHISH.sub("<path>", str(text or ""))[:limit]


def day_of(now_s):
    return time.strftime("%Y-%m-%d", time.gmtime(now_s))


def due(misses, state, now_s, max_per_day=MAX_PER_DAY):
    """The misses to diagnose now: never diagnosed here (by check name), within today's allowance. -> [miss]. Pure."""
    st = state if isinstance(state, dict) else {}
    seen = st.get("seen") if isinstance(st.get("seen"), dict) else {}
    used = int(st.get("n") or 0) if st.get("day") == day_of(now_s) else 0
    left = max(0, max_per_day - used)
    failed = st.get("failed") if isinstance(st.get("failed"), dict) else {}
    today = day_of(now_s)

    def _failed_today(check):
        # v3868 (the Grok CLI on REG-3235) - one stuck fault took both of the day's asks while others waited
        at = (failed.get(check) or {}).get("at") if isinstance(failed.get(check), dict) else None
        return isinstance(at, (int, float)) and day_of(at / 1000.0) == today
    out = []
    for m in misses or []:
        if len(out) >= left:
            break
        if isinstance(m, dict) and m.get("check") and m["check"] not in seen and not _failed_today(m["check"]):
            out.append(m)
    return out


def forget_cleared(state, misses):
    """A fault that is no longer missing leaves `seen`, so if it comes back it is diagnosed again. Pure."""
    st = dict(state or {})
    now = set(m.get("check") for m in misses or [] if isinstance(m, dict))
    st["seen"] = {k: v for k, v in (st.get("seen") or {}).items() if k in now}
    if st.get("failed"):
        st["failed"] = {k: v for k, v in st["failed"].items() if k in now}
    return st


def prompt_for(miss, fn_name, platform):
    return ("You are diagnosing ONE fault on a TV DIABLO console PC (platform %s), in the repo you were given with "
            "--add-dir (it holds tv/console_doctor.py). "
            "Its eagle-eye check %r reads MISSING with this reason: %r. The check is %s in tv/console_doctor.py. "
            "Read that function and whatever it reads, find the most likely cause ON THIS PC, and answer in at most "
            "12 lines, exactly:\nCAUSE: <one sentence>\nFIX: <the smallest change or command that would repair it>\n"
            "VERIFY: <how to see it worked>\nCONFIDENCE: low|medium|high\nDo not change any file and do not run "
            "anything. If you cannot tell, say CAUSE: unknown and what to measure next."
            % (platform, miss.get("check"), scrub(miss.get("why"), 400), fn_name or "the function behind that row"))


def summary_of(text):
    """The CAUSE line (or the first line), short. Pure."""
    t = str(text or "")
    m = re.search(r"CAUSE:\s*(.+)", t)
    return scrub((m.group(1) if m else t.strip().split("\n")[0]).strip(), 200)


def _neutral_cwd():
    """v3867 (#17) - where the ask runs: outside the repo, so its CLAUDE.md and project settings never load. -> dir"""
    import tempfile
    return tempfile.gettempdir()


def diagnose(miss, fn_name, platform, run=None, env=None, which=None):
    """Ask this PC's Claude about one miss. -> record. Never raises; never under D2R_NO_CLAUDE."""
    env = os.environ if env is None else env
    rec = {"check": miss.get("check"), "at": int(time.time() * 1000), "ok": False, "summary": "", "text": ""}
    if env.get("D2R_NO_CLAUDE") == "1":
        rec["summary"] = "not asked: D2R_NO_CLAUDE is set here"
        return rec
    exe = (which or shutil.which)("claude")
    if not exe:
        rec["summary"] = "not asked: no claude on this PC"
        return rec
    try:
        # #17/#19 (GrokBot 6700580776: every self-ask failed - the Mac "stdin is unreadable (EBADF)", the ALT "Input must be
        # provided either through stdin or as a prompt argument when using --print") - THE PROMPT WAS SWALLOWED. It sat
        # last, after `--add-dir REPO`, and --add-dir takes SEVERAL values (`--add-dir <directories...>`), so the CLI read
        # the prompt as a second directory and -p had none: the ALT said so, the Mac fell back to reading a stdin a GUI
        # console does not have. The prompt now rides right after -p, as tv_diablo's one-shot read places it (v1463), and
        # stdin is empty on purpose, so nothing is ever read from it.
        p = (run or subprocess.run)(
            [exe, "-p", prompt_for(miss, fn_name, platform), "--allowedTools", ALLOWED_TOOLS, "--max-turns", str(MAX_TURNS),
             "--setting-sources", "user", "--strict-mcp-config", "--no-session-persistence", "--add-dir", REPO],
            cwd=_neutral_cwd(), stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=TIMEOUT_S, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        text = ((p.stdout or "") + "\n" + (p.stderr or "")).strip()
        rc = p.returncode
    except subprocess.TimeoutExpired:
        text, rc = "the diagnosis ran past %d s" % TIMEOUT_S, 124
    except Exception as e:
        text, rc = "claude could not be started (%s)" % type(e).__name__, 127
    low = text.lower()
    # v3868 (the Grok CLI on REG-3235, #231 6676508919) - AN ANSWER IS A CAUSE LINE. A dead-seat phrase dropped a real
    # proposal whose fault was itself about signing in ("CAUSE: the console is not logged in"), and an exit 0 that
    # never reached a CAUSE line was stored as diagnosed for good. Now: no CAUSE line is not an answer; a dead-seat
    # phrase marks a dead seat only when there is no CAUSE line; a non-zero exit is still not an answer.
    has_cause = re.search(r"(?m)^\s*CAUSE:\s*\S", text) is not None
    if rc != 0 or not has_cause:
        why = (next((s for s in DEAD_SEAT if s in low), None) if not has_cause else None)
        rec["summary"] = "not answered: " + (("%s - " % why) if why else "") + scrub(text.split("\n")[0], 160)
        return rec
    rec.update(ok=True, summary=summary_of(text), text=scrub(text, 4000))
    return rec


def load(path):
    """-> the state ({} when the file is absent) | None (it exists and will not read: UNKNOWN - nothing is asked over it,
    or a corrupt file would re-spend the day's allowance on faults already diagnosed)"""
    try:
        with io.open(path, encoding="utf-8") as fh:
            st = json.load(fh)
    except FileNotFoundError:
        return {}
    except (OSError, ValueError):
        return None
    return st if isinstance(st, dict) else None


def save(path, st):
    try:
        with io.open(path + ".tmp", "w", encoding="utf-8") as fh:
            json.dump(st, fh)
        os.replace(path + ".tmp", path)
        return True
    except Exception:
        return False


def run_due(misses, fn_of, platform, path=None, now_s=None, ask=None):
    """One pass: forget cleared faults, diagnose what is due, record. -> {check: summary} for every miss known here."""
    path = path or os.path.join(HERE, STATE_NAME)
    now_s = time.time() if now_s is None else now_s
    prev = load(path)
    if prev is None:
        # UNKNOWN state: spend nothing, overwrite nothing - and SAY it (v3868: it read as "not diagnosed yet" forever)
        return dict((m["check"], "UNKNOWN - this PC's diagnosis record will not read, so nothing was asked")
                    for m in (misses or ()) if isinstance(m, dict) and m.get("check"))
    st = forget_cleared(prev, misses)
    # REG-3251 - what landed in this process and would not save is laid back over the file, so it is not asked again.
    live = set(m.get("check") for m in misses or () if isinstance(m, dict))
    kept = _KEPT.get(path) or {}
    for k, v in (kept.get("seen") or {}).items():
        if k in live and k not in (st.get("seen") or {}):
            st.setdefault("seen", {})[k] = v
            (st.get("failed") or {}).pop(k, None)
    for k, v in (kept.get("failed") or {}).items():
        if k in live and k not in (st.get("seen") or {}):
            st.setdefault("failed", {})[k] = v
    said = {}
    today = day_of(now_s)
    for m in due(misses, st, now_s):
        check = m["check"]
        # REG-3251 - THE ASK IS RESERVED ON DISK BEFORE IT IS MADE. The count used to move only after the answer, so a
        # save that failed, or a kill before os.replace, lost the spend and the next pass (or process) spent it again.
        # The reservation also marks the fault: a kill mid-ask leaves "cut off", and the fault waits for tomorrow.
        before = (st.get("day"), st.get("n"), (st.get("failed") or {}).get(check))
        st["n"] = (int(st.get("n") or 0) if st.get("day") == today else 0) + 1
        st["day"] = today
        st.setdefault("failed", {})[check] = {"at": int(now_s * 1000), "summary": CUT_OFF, "pending": True}
        if not save(path, st):
            st["day"], st["n"] = before[0], before[1]
            if before[2] is None:
                st["failed"].pop(check, None)
            else:
                st["failed"][check] = before[2]
            said[check] = "not asked - this PC's diagnosis record will not write, so an ask could not be counted"
            break
        rec = (ask or diagnose)(m, fn_of(m.get("check")), platform)
        said[check] = rec.get("summary")
        if str(rec.get("summary") or "").startswith("not asked"):
            # nothing was spent: no claude, or a law's D2R_NO_CLAUDE - the reservation is given back
            st["day"], st["n"] = before[0], before[1]
            if before[2] is None:
                st["failed"].pop(check, None)
            else:
                st["failed"][check] = before[2]
            save(path, st)
            continue
        if not rec.get("ok"):
            # v3867 (#17) - THE REASON STAYS. A spent ask that did not land kept nothing, so the Fleet hover said "not
            # diagnosed yet" all day with the allowance gone and no why. It is kept per fault until a later ask lands.
            st["failed"][check] = {"at": rec.get("at") or int(now_s * 1000), "summary": rec.get("summary")}
        else:                                 # a seat that did not answer is asked again tomorrow, never marked done
            st["failed"].pop(check, None)
            st.setdefault("seen", {})[check] = {"at": rec.get("at"), "summary": rec.get("summary"),
                                                "text": rec.get("text")}
        if not save(path, st):
            box = _KEPT.setdefault(path, {"seen": {}, "failed": {}})
            if rec.get("ok"):
                box["seen"][check] = st["seen"][check]
                box["failed"].pop(check, None)
            else:
                box["failed"][check] = st["failed"][check]
        elif path in _KEPT:
            _KEPT[path]["seen"].pop(check, None)
            _KEPT[path]["failed"].pop(check, None)
    if save(path, st) and path in _KEPT:
        _KEPT.pop(path, None)                 # everything this process held is on disk now
    out = {k: (v or {}).get("summary") for k, v in (st.get("seen") or {}).items()}
    for k, v in (st.get("failed") or {}).items():
        if k not in out and any(m.get("check") == k for m in misses or ()):
            out[k] = (CUT_OFF if (v or {}).get("pending") else
                      "its last ask did not land - %s" % ((v or {}).get("summary") or "no reason was recorded"))
    for k, v in said.items():
        out.setdefault(k, v)
    return out
