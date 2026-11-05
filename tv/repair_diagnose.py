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
TIMEOUT_S = 300
MAX_TURNS = 8
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
    out = []
    for m in misses or []:
        if len(out) >= left:
            break
        if isinstance(m, dict) and m.get("check") and m["check"] not in seen:
            out.append(m)
    return out


def forget_cleared(state, misses):
    """A fault that is no longer missing leaves `seen`, so if it comes back it is diagnosed again. Pure."""
    st = dict(state or {})
    now = set(m.get("check") for m in misses or [] if isinstance(m, dict))
    st["seen"] = {k: v for k, v in (st.get("seen") or {}).items() if k in now}
    return st


def prompt_for(miss, fn_name, platform):
    return ("You are diagnosing ONE fault on a TV DIABLO console PC (platform %s), repo at the current directory. "
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
        p = (run or subprocess.run)(
            [exe, "-p", "--allowedTools", "Read", "--max-turns", str(MAX_TURNS), prompt_for(miss, fn_name, platform)],
            cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=TIMEOUT_S,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        text = ((p.stdout or "") + "\n" + (p.stderr or "")).strip()
        rc = p.returncode
    except subprocess.TimeoutExpired:
        text, rc = "the diagnosis ran past %d s" % TIMEOUT_S, 124
    except Exception as e:
        text, rc = "claude could not be started (%s)" % type(e).__name__, 127
    low = text.lower()
    if rc != 0 or any(s in low for s in DEAD_SEAT):
        rec["summary"] = "not answered: " + scrub(text.split("\n")[0], 160)
        return rec
    rec.update(ok=True, summary=summary_of(text), text=scrub(text, 4000))
    return rec


def load(path):
    try:
        with io.open(path, encoding="utf-8") as fh:
            st = json.load(fh)
        return st if isinstance(st, dict) else {}
    except Exception:
        return {}


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
    st = forget_cleared(load(path), misses)
    said = {}
    for m in due(misses, st, now_s):
        rec = (ask or diagnose)(m, fn_of(m.get("check")), platform)
        said[m["check"]] = rec.get("summary")
        if str(rec.get("summary") or "").startswith("not asked"):
            continue                          # nothing was spent: no claude, or a law's D2R_NO_CLAUDE
        today = day_of(now_s)
        st["n"] = (int(st.get("n") or 0) if st.get("day") == today else 0) + 1
        st["day"] = today
        if rec.get("ok"):                     # a seat that did not answer is asked again tomorrow, never marked done
            st.setdefault("seen", {})[m["check"]] = {"at": rec.get("at"), "summary": rec.get("summary"),
                                                     "text": rec.get("text")}
        save(path, st)
    save(path, st)
    out = {k: (v or {}).get("summary") for k, v in (st.get("seen") or {}).items()}
    for k, v in said.items():
        out.setdefault(k, v)
    return out
