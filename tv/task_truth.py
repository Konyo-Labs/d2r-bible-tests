# -*- coding: utf-8 -*-
"""v3865 (his words 2026-11-05, REG-3217 + REG-3218) - THE TASK BOARD IS DERIVED FROM THE EVIDENCE, LIKE BLUEPRINT AND HEART.

His words: "make sure its derived always console and you and the taskboard synced.. so we are always with our finger on the
trigger and know whats still being worked on and not shipped". MEASURED that evening: the board (the task panel's cards,
read by tv/task_board.py and published to /d2r/tasks.html) had not been touched for 6 hours while the work moved - 25 cards
said in_progress, several describing work shipped days earlier ("v3862 ship", REG-3155's proof bank, REG-3157's
ship_when_green) and none naming the fleet that was running. A card's status is typed by hand; nothing compared it to the
tree. BLUEPRINT.md and HEART.md are derived and the pre-push refuses them stale; the board was the one map still typed.

So every card now carries a DERIVED PHASE (REG-3217), read from the evidence and never from the card's own words:
  * its KEYS - the REG ids its subject names (REG-3154/3156 and REG-3193..3195 expand), else a version leading the subject
    ("v3862 ship"), else a branch the subject names (claude/..., ci/..., grok/...), else the REG ids, then the branches, its
    description names. Which of those it keyed on is said (`basis`), because a description cites precedents.
  * each key resolved against git in the console's own checkout - one bounded read of every commit message, cached per
    HEAD + origin/main and at most every 10 min: no commit names it (no-evidence) | only local branches or worktrees
    (building) | a ci/ branch (graded) | origin/main (shipped vN - N the stamp the first such main commit shipped in) |
    and the published version >= N (live vN).
  * then the looks: GrokBot's (#230) after the ship, and the Grok CLI / second eye's (#231, or its seat on #230) that cite
    the key or that version - read through tv/handoff.py's one GitHub reader into a small cache, at most every 10 min.
    A look that could not be read is UNKNOWN, never "not looked"; a ship older than the looks the cache holds is UNKNOWN.
  * the card's phase is its least-advanced key's (two REG ids are shipped only when both are). UNKNOWN when git would not
    answer - never "no-evidence", which is a measured fact about a tree that answered.

And a card whose hand status disagrees with that evidence is FLAGGED with the reason (REG-3218): in_progress or pending
but shipped + looked + third-eyed -> "ready to close"; completed with work in git that never reached main -> "closed but
never shipped" (red); pending with commits -> "work started on a pending card"; in_progress with nothing in git for more
than STALE_DAYS -> "in progress with nothing built". The derivation SAYS; it never rewrites a card's status - Claude and
he decide. The console's eagle row "the board agrees with the tree" counts the flags (console_doctor).

Pure functions here, the readers take their runner (git) and reader (GitHub) as arguments so a law drives them on a temp
repo and fixture comments; control_app.task_truth_derive wires the real ones. Prior art under another word:
tv/board_sync.py derives a DIFFERENT board (the artifact database) from TASKS.md + git; this one reads the panel's cards.
"""
import io
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

#: the ladder, least to most advanced. A card's phase is the highest rung all of its keys reached.
PHASES = ("no-evidence", "building", "graded", "shipped", "live", "looked", "third-eyed")
RANK = dict((p, i) for i, p in enumerate(PHASES))
UNKNOWN = "unknown"

GIT_TTL_MS = 10 * 60 * 1000          # the git index is re-read when HEAD or origin/main moves, else at most every 10 min
GIT_TIMEOUT_S = 30
LOOKS_EVERY_MS = 10 * 60 * 1000      # GitHub is asked at most every 10 min
LOOKS_STALE_MS = 35 * 60 * 1000      # a lane last read longer ago than this is UNKNOWN, not "not looked"
LOOKS_WINDOW_DAYS = 14               # the first read goes back this far; the cache keeps LOOKS_KEEP_DAYS
LOOKS_KEEP_DAYS = 45
GH_TIMEOUT_S = 60
LOOK_HEAD_CHARS = 600                # a look is ABOUT the versions on its first line that names one, inside its head
ISSUES = (230, 231)
REPO_SLUG = "KonyoDigital/d2r-bible-tests"
STALE_DAYS = 2                       # an in_progress card with nothing in git for longer is flagged
RANGE_MAX = 25                       # REG-a..b expands only when b - a is at most this
KEYS_MAX = 12
DAY_MS = 24 * 3600 * 1000

DRIFT_SAY = {
    "closed-never-shipped": "closed but never shipped",
    "ready-to-close": "ready to close",
    "work-started": "work started on a pending card",
    "nothing-built": "in progress with nothing built",
}
DRIFT_KINDS = tuple(DRIFT_SAY)

_REG_RX = re.compile(r"\bREG-(\d{1,5})((?:\s*/\s*\d{1,5}\b)*)"
                     r"(?:(?:\s*(?:\.\.\.?|…|\bto\b|\bthrough\b)\s*|[–-])(?:REG-)?(\d{1,5})\b)?")
_VER_RX = re.compile(r"\bv(\d{4})\b")
_LEAD_VER_RX = re.compile(r"^\s*v(\d{4})\b(?![’']s)")
_BRANCH_RX = re.compile(r"(?<![\w/.-])((?:claude|ci|grok)/[A-Za-z0-9](?:[A-Za-z0-9._/-]*[A-Za-z0-9])?)")


def regs_in(text):
    """Every REG id the text names, in order, ranges and slash lists expanded. -> ["REG-3154", ...]"""
    out = []
    for m in _REG_RX.finditer(str(text or "")):
        lo = int(m.group(1))
        got = [lo] + [int(x) for x in re.findall(r"\d+", m.group(2) or "")]
        if m.group(3):
            hi = int(m.group(3))
            if lo < hi <= lo + RANGE_MAX:
                got += list(range(lo + 1, hi + 1))
            elif hi != lo and len(m.group(3)) >= len(m.group(1)):
                got.append(hi)                            # too wide to expand: both ends are still named
        for n in got:
            k = "REG-%d" % n
            if k not in out:
                out.append(k)
    return out


def versions_in(text):
    """-> ["v3864", ...] every version stamp the text names, in order"""
    out = []
    for m in _VER_RX.finditer(str(text or "")):
        k = "v" + m.group(1)
        if k not in out:
            out.append(k)
    return out


def lead_version(subject):
    """The version a subject LEADS with ("v3862 ship", "v3865: ..."), never a possessive ("v3864's first run"). -> str|None"""
    m = _LEAD_VER_RX.match(str(subject or ""))
    return ("v" + m.group(1)) if m else None


def branches_in(text):
    out = []
    for m in _BRANCH_RX.finditer(str(text or "")):
        b = m.group(1).rstrip("./-")
        if b and b not in out:
            out.append(b)
    return out


def card_keys(card):
    """-> (keys, basis): what the card is ABOUT, from its subject first; basis "subject" | "description" | None"""
    subj = str((card or {}).get("subject") or "")
    desc = str((card or {}).get("description") or "")
    lv = lead_version(subj)
    for basis, keys in (("subject", regs_in(subj)), ("subject", [lv] if lv else []), ("subject", branches_in(subj)),
                        ("description", regs_in(desc)), ("description", branches_in(desc))):
        if keys:
            return keys[:KEYS_MAX], basis
    return [], None


def _vnum(v):
    try:
        return int(str(v).lstrip("v"))
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------------------------------------------- git

_GIT_CACHE = {}


def _git_env():
    # a git hook leaks GIT_DIR / GIT_INDEX_FILE into every child; a reader that inherited them would read ANOTHER repo
    env = dict((k, v) for k, v in os.environ.items() if not k.startswith("GIT_"))
    env["GIT_OPTIONAL_LOCKS"] = "0"
    return env


def _default_run():
    try:
        import git_quiet as _gq
        return _gq.run
    except Exception:
        import subprocess
        return subprocess.run


def _git(repo, args, run, stdin=None):
    kw = dict(cwd=repo, capture_output=True, encoding="utf-8", errors="replace", timeout=GIT_TIMEOUT_S, env=_git_env())
    if stdin is not None:
        kw["input"] = stdin
    p = run(["git"] + list(args), **kw)
    if p.returncode != 0:
        raise RuntimeError("git %s answered %s: %s" % (args[0], p.returncode, (p.stderr or "").strip()[:160]))
    return p.stdout or ""


def read_git(repo, now_ms, run=None):
    """One bounded read of the checkout's evidence. -> {"ok": True, head, main, keys: {key: [(sha, ms)]}, main_ver, ci, local,
    refs, ct, publishedVer} or {"ok": False, "why"} - a tree that would not answer is UNKNOWN, never an empty one."""
    run = run or _default_run()
    try:
        heads = _git(repo, ["rev-parse", "HEAD", "refs/remotes/origin/main"], run).split()
        if len(heads) != 2:
            return {"ok": False, "why": "git did not name HEAD and origin/main"}
        head, main = heads
        log = _git(repo, ["log", "--all", "--format=%H%x1f%ct%x1f%s%x1f%b%x1e"], run)
        main_list = _git(repo, ["rev-list", main], run).split()
        refs_raw = _git(repo, ["for-each-ref", "--format=%(refname)%1f%(objectname)", "refs/heads", "refs/remotes"], run)
    except Exception as e:
        return {"ok": False, "why": "git would not answer (%s)" % str(e)[:160]}
    keys, ct, subj = {}, {}, {}
    for rec in log.split("\x1e"):
        parts = rec.strip("\n").split("\x1f")
        if len(parts) < 3 or len(parts[0].strip()) < 7:
            continue
        sha = parts[0].strip()
        try:
            t = int(parts[1]) * 1000
        except ValueError:
            continue
        s, b = parts[2], (parts[3] if len(parts) > 3 else "")
        ct[sha], subj[sha] = t, s
        named = regs_in(s + "\n" + b)
        lv = lead_version(s)
        if lv:
            named.append(lv)
        for k in named:
            keys.setdefault(k, []).append((sha, t))
    main_set = set(main_list)
    # the version each main commit shipped in: its own leading stamp, else the next newer stamped commit's (rev-list is
    # newest first, so the last stamp seen walking it is the nearest newer one)
    main_ver, cur = {}, None
    for sha in main_list:
        lv = lead_version(subj.get(sha, ""))
        if lv:
            cur = lv
        main_ver[sha] = lv or cur
    refs, ci_tips = {}, []
    for line in refs_raw.splitlines():
        if "\x1f" not in line:
            continue
        name, sha = line.split("\x1f", 1)
        if name.startswith("refs/heads/"):
            short = name[len("refs/heads/"):]
        elif name.startswith("refs/remotes/origin/"):
            short = name[len("refs/remotes/origin/"):]
        else:
            continue
        if short == "HEAD":
            continue
        refs.setdefault(short, sha.strip())
        if short.startswith("ci/"):
            ci_tips.append(sha.strip())
    ci = set()
    if ci_tips:
        try:
            ci = set(_git(repo, ["rev-list", "--stdin"], run,
                          stdin="\n".join(sorted(set(ci_tips))) + "\n^" + main + "\n").split())
        except Exception as e:
            return {"ok": False, "why": "git would not list the ci/ branches (%s)" % str(e)[:160]}
    pub = None
    try:
        pub = json.loads(_git(repo, ["show", main + ":tv/WINDOWS_SHIP.json"], run)).get("ver") or None
    except Exception:
        pub = None                                        # UNKNOWN; the console's fleet reading may still name it
    return {"ok": True, "head": head, "main": main, "keys": keys, "main_set": main_set, "main_ver": main_ver,
            "ci": ci, "refs": refs, "ct": ct, "publishedVer": pub, "at": int(now_ms), "commits": len(ct)}


def git_index(repo, now_ms, run=None, cache=None):
    """read_git, cached per (HEAD, origin/main) and at most every GIT_TTL_MS. -> the index dict"""
    cache = _GIT_CACHE if cache is None else cache
    run = run or _default_run()
    try:
        heads = tuple(_git(repo, ["rev-parse", "HEAD", "refs/remotes/origin/main"], run).split())
    except Exception as e:
        return {"ok": False, "why": "git would not answer (%s)" % str(e)[:160]}
    held = cache.get(repo)
    if held and held.get("heads") == heads and now_ms - held.get("at", 0) < GIT_TTL_MS and held["idx"].get("ok"):
        return held["idx"]
    idx = read_git(repo, now_ms, run)
    if idx.get("ok"):
        cache[repo] = {"heads": heads, "at": int(now_ms), "idx": idx}
    return idx


# -------------------------------------------------------------------------------------------------------------- looks

_SEAT_RX = (
    ("grokbot", re.compile(r"^(?:seat:\s*grok\s*bot\b|grokbot\b|gb-[a-z0-9])", re.I)),
    ("third", re.compile(r"^(?:second-eye\b|seat:\s*grok\s*cli\b|grok\s*(?:→|->))", re.I)),
    ("claude", re.compile(r"^(?:seat:\s*claude\b|claude\s*(?:→|->))", re.I)),
)


def seat_of(body):
    """Who posted a #230/#231 comment, read off its first meaningful line (the seat tag). -> "grokbot"|"third"|"claude"|None"""
    for raw in str(body or "").splitlines():
        line = raw.strip().lstrip("#*> ").strip()
        while line and not line[0].isalnum():
            line = line[1:].lstrip()
        if not line:
            continue
        for seat, rx in _SEAT_RX:
            if rx.match(line):
                return seat
        return None
    return None


def _iso_ms(s):
    try:
        import calendar
        return int(calendar.timegm(time.strptime(str(s), "%Y-%m-%dT%H:%M:%SZ")) * 1000)
    except Exception:
        return None


def _ms_iso(ms):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ms / 1000.0))


def look_row(comment, issue):
    """One GitHub comment -> the little it is kept as: {id, at, seat, regs, vers}, or None when it is no seat's look."""
    if not isinstance(comment, dict):
        return None
    body = str(comment.get("body") or "")
    seat = seat_of(body)
    if seat not in ("grokbot", "third"):
        return None
    at = _iso_ms(comment.get("created_at"))
    if at is None or comment.get("id") is None:
        return None
    return {"id": str(comment.get("id")), "issue": int(issue), "at": at, "seat": seat,
            "regs": regs_in(body)[:60], "vers": about_versions(body)}


def about_versions(body):
    """The versions a look is ABOUT: those on the first line, inside its head, that names any. -> ["v3863"]
    MEASURED on #230 2026-11-05: GrokBot's "# v3863 ship check" names "changelog-v3861-63.json" in its evidence list four
    lines down, and a look counted for every version in its first 600 characters made v3861 and v3862 "looked" by a look
    at v3863 - 30 of 84 cards read "ready to close". The heading says what was looked at; the evidence does not."""
    for line in str(body or "")[:LOOK_HEAD_CHARS].splitlines():
        got = versions_in(line)
        if got:
            return got[:12]
    return []


def load_looks(path):
    """-> the cache dict; {} when there is none yet (a fact); None when it exists and will not read (UNKNOWN)"""
    try:
        with io.open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else None
    except FileNotFoundError:
        return {}
    except Exception:
        return None


def refresh_looks(path, now_ms, gh, issues=ISSUES, every_ms=LOOKS_EVERY_MS):
    """Ask GitHub for the comments since the last read, at most every `every_ms`, into the cache at `path`. gh(api_path)
    returns the comment dicts or raises. -> the cache dict, or None when the cache would not read (it is never written
    over a store this process could not read)."""
    cache = load_looks(path)
    if cache is None:
        return None
    lanes = cache.setdefault("issues", {})
    changed = False
    for n in issues:
        lane = lanes.setdefault(str(n), {})
        if isinstance(lane.get("triedAt"), int) and now_ms - lane["triedAt"] < every_ms:
            continue
        lane["triedAt"] = int(now_ms)
        changed = True
        since = lane.get("since") or _ms_iso(now_ms - LOOKS_WINDOW_DAYS * DAY_MS)
        try:
            got = gh("repos/%s/issues/%d/comments?per_page=100&since=%s" % (REPO_SLUG, n, since))
        except Exception as e:
            lane["why"] = "GitHub would not answer #%d (%s)" % (n, str(e)[:120])
            continue
        if not isinstance(got, list):
            lane["why"] = "GitHub answered #%d with something that is not a list" % n
            continue
        rows = dict((r.get("id"), r) for r in (lane.get("rows") or []) if isinstance(r, dict))
        newest = since
        for c in got:
            if not isinstance(c, dict):
                continue
            u = str(c.get("updated_at") or c.get("created_at") or "")
            if u > newest:
                newest = u
            r = look_row(c, n)
            if r:
                rows[r["id"]] = r
        keep_from = int(now_ms - LOOKS_KEEP_DAYS * DAY_MS)
        lane["rows"] = sorted((r for r in rows.values() if r.get("at", 0) >= keep_from), key=lambda r: r["at"])
        # the cache holds every comment touched since its FIRST read's `since`, less what aged out of the keep window
        first = lane.get("from") if isinstance(lane.get("from"), int) else (_iso_ms(since) or keep_from)
        lane["from"] = max(int(first), keep_from)
        lane["since"] = newest
        lane["okAt"] = int(now_ms)
        lane["why"] = None
    if changed:
        try:
            with io.open(path + ".tmp", "w", encoding="utf-8") as fh:
                json.dump(cache, fh)
            os.replace(path + ".tmp", path)
        except Exception:
            pass                                          # the next tick asks again; what was read is still used now
    return cache


def looks_view(cache, now_ms, issues=ISSUES):
    """-> {rows, known: {grokbot, third}, from, why}: what the looks can be trusted to say right now"""
    if cache is None:
        return {"rows": [], "known": {"grokbot": False, "third": False}, "from": None,
                "why": "the looks cache would not read - UNKNOWN"}
    lanes = cache.get("issues") or {}
    fresh, rows, froms, whys = {}, [], [], []
    for n in issues:
        lane = lanes.get(str(n)) or {}
        ok = isinstance(lane.get("okAt"), int) and now_ms - lane["okAt"] < LOOKS_STALE_MS
        fresh[n] = ok
        if ok:
            rows.extend(r for r in (lane.get("rows") or []) if isinstance(r, dict))
            if isinstance(lane.get("from"), int):
                froms.append(lane["from"])
        else:
            whys.append(lane.get("why") or ("#%d has not been read since this console started" % n))
    return {"rows": rows, "known": {"grokbot": bool(fresh.get(230)), "third": bool(fresh.get(230) and fresh.get(231))},
            "from": (max(froms) if froms else None), "why": "; ".join(whys) or None}


# ------------------------------------------------------------------------------------------------------------- derive

def _first_look(looks, seat, key, ver, since_ms):
    best = None
    for r in looks.get("rows") or []:
        if r.get("seat") != seat or not isinstance(r.get("at"), int) or r["at"] < since_ms:
            continue
        if key in (r.get("regs") or []) or (ver and ver in (r.get("vers") or [])):
            if best is None or r["at"] < best["at"]:
                best = r
    return best


def resolve_key(key, idx, published, looks):
    """One key against the evidence. -> {key, phase, sha, ver, at, look, third, unknown: [rungs], why}"""
    out = {"key": key, "phase": "no-evidence", "sha": None, "ver": None, "at": None, "look": None, "third": None,
           "unknown": [], "why": None}
    main_set, ci = idx["main_set"], idx["ci"]
    if key.startswith("REG-") or _VER_RX.match(key):
        hits = idx["keys"].get(key) or []
        if not hits:
            out["why"] = "no commit names it"
            return out
        first_any = min(t for _s, t in hits)
        on_main = sorted((h for h in hits if h[0] in main_set), key=lambda h: h[1])
        if not on_main:
            on_ci = [h for h in hits if h[0] in ci]
            pick = max(on_ci or hits, key=lambda h: h[1])
            out.update(phase="graded" if on_ci else "building", sha=pick[0][:9], at=pick[1],
                       why="on a ci/ branch, not on main" if on_ci else "only on a local branch or worktree")
            return out
        sha, at = on_main[0]
        ver = key if key.startswith("v") else idx["main_ver"].get(sha)
    else:
        tip = idx["refs"].get(key)
        if not tip:
            out["why"] = "no branch of that name in this checkout"
            return out
        at = idx["ct"].get(tip)
        first_any = at or 0
        if tip not in main_set:
            out.update(phase="graded" if tip in ci else "building", sha=tip[:9], at=at,
                       why="its tip is on a ci/ branch, not on main" if tip in ci else "its tip is not on main")
            return out
        sha, ver = tip, idx["main_ver"].get(tip)
    out.update(phase="shipped", sha=sha[:9], ver=ver, at=at, why="on origin/main")
    pv, nv = _vnum(published), _vnum(ver)
    if pv is None or nv is None:
        out["unknown"].append("live")
        out["why"] = "on origin/main; %s, so whether it is live is UNKNOWN" % (
            "the published version could not be read" if pv is None else "the stamp it shipped in could not be read")
        return out
    if pv < nv:
        out["why"] = "on origin/main, the published version is still %s" % published
        return out
    out["phase"] = "live"
    out["why"] = "published (the site is %s)" % published
    known = looks.get("known") or {}
    before_window = isinstance(looks.get("from"), int) and at is not None and at < looks["from"]
    look = _first_look(looks, "grokbot", key, ver, at or 0) if known.get("grokbot") else None
    third = _first_look(looks, "third", key, ver, first_any) if known.get("third") else None
    if look:
        out["look"] = {"id": look["id"], "issue": look.get("issue"), "at": look["at"]}
    elif not known.get("grokbot") or before_window:
        out["unknown"].append("looked")
    if third:
        out["third"] = {"id": third["id"], "issue": third.get("issue"), "at": third["at"]}
    elif not known.get("third") or before_window:
        out["unknown"].append("third-eyed")
    if look:
        out["phase"] = "looked"
        if third:
            out["phase"] = "third-eyed"
    return out


def drift(status, d, age_ms, now_ms=None):
    """REG-3218 - where the hand status disagrees with the evidence. -> {kind, say, basis} | None. Never on an UNKNOWN phase:
    a tree that did not answer cannot disagree with anything."""
    ph = d.get("phase")
    if ph not in RANK:
        return None
    hi = d.get("hi") if d.get("hi") in RANK else ph
    bott = d.get("bottleneck") or {}
    top = d.get("top") or {}
    where = "%s %s%s" % (bott.get("key") or "its key", bott.get("phase") or ph,
                         (" (" + str(bott.get("sha")) + ")") if bott.get("sha") else "")
    kind = say = None
    if status == "completed":
        if RANK[hi] >= RANK["building"] and RANK[ph] < RANK["shipped"]:
            kind, say = "closed-never-shipped", "closed but never shipped - %s: %s" % (where, bott.get("why") or "not on origin/main")
    elif RANK[ph] >= RANK["third-eyed"]:
        kind, say = "ready-to-close", ("ready to close - shipped %s, looked by GrokBot (comment %s), third-eyed (comment %s)"
                                       % (d.get("ver") or "", (d.get("look") or {}).get("id"), (d.get("third") or {}).get("id")))
    elif status == "pending" and RANK[hi] >= RANK["building"]:
        kind, say = "work-started", "work started on a pending card - %s is %s%s" % (
            top.get("key"), top.get("phase"), (" (" + str(top.get("sha")) + ")") if top.get("sha") else "")
    elif status == "in_progress" and hi == "no-evidence" and isinstance(age_ms, (int, float)) \
            and not isinstance(age_ms, bool) and age_ms > STALE_DAYS * DAY_MS:
        kind, say = "nothing-built", "in progress with nothing built for %.0f days - %s" % (
            age_ms / float(DAY_MS),
            "it names no REG id, version or branch, so nothing in git can be found for it" if not d.get("keys")
            else "no commit or branch names %s" % ", ".join(d["keys"][:4]))
    if kind is None:
        return None
    if d.get("basis") == "description":
        # a description cites precedents as often as it names its own work: said, so the reader weighs it
        say += " (keyed on its description, which may only cite it)"
    return {"kind": kind, "say": say, "basis": d.get("basis")}


def derive_card(card, idx, published, looks, now_ms):
    """-> {phase, keys, basis, ver, sha, at, look, third, unknown, why, hi, bottleneck, top, drift}"""
    keys, basis = card_keys(card)
    d = {"keys": keys, "basis": basis, "phase": UNKNOWN, "ver": None, "sha": None, "at": None, "look": None,
         "third": None, "unknown": [], "why": None, "hi": None, "bottleneck": None, "top": None, "drift": None}
    if not isinstance(idx, dict) or not idx.get("ok"):
        d["why"] = (idx or {}).get("why") or "the tree was not read - UNKNOWN"
        return d
    if not keys:
        d.update(phase="no-evidence", hi="no-evidence", why="it names no REG id, version or branch")
    else:
        per = [resolve_key(k, idx, published, looks) for k in keys]
        lo = min(per, key=lambda r: RANK[r["phase"]])
        top = max(per, key=lambda r: RANK[r["phase"]])
        if basis == "subject":
            # a card keyed on its subject may name, in its description, the REG that is fixing it ("REG-3110 is INERT ...
            # fixed by REG-3167 on claude/v3863"): work for this card still IN FLIGHT holds the card where that work is,
            # so an old shipped key never reads "ready to close" over a fix that has not landed. A description REG that
            # is shipped (a precedent) or names nothing changes nothing.
            sec = [resolve_key(k, idx, published, looks) for k in regs_in(card.get("description"))[:KEYS_MAX]
                   if k not in keys]
            moving = [r for r in sec if r["phase"] in ("building", "graded")]
            if moving:
                m = min(moving, key=lambda r: RANK[r["phase"]])
                if RANK[m["phase"]] < RANK[lo["phase"]]:
                    lo = dict(m, why="%s - its description's %s is still moving" % (m["why"], m["key"]))
                if RANK[m["phase"]] > RANK[top["phase"]]:
                    top = m
        unk = []
        for r in per:
            for u in r["unknown"]:
                if u not in unk:
                    unk.append(u)
        d.update(phase=lo["phase"], ver=lo["ver"], sha=lo["sha"], at=lo["at"], look=lo["look"], third=lo["third"],
                 unknown=unk, why=lo["why"], hi=top["phase"],
                 bottleneck=dict((k, lo[k]) for k in ("key", "phase", "sha", "why")),
                 top=dict((k, top[k]) for k in ("key", "phase", "sha")))
    mt = card.get("_mtime")
    age = (now_ms - mt) if isinstance(mt, (int, float)) and not isinstance(mt, bool) else None
    d["drift"] = drift(card.get("status"), d, age, now_ms)
    return d


def derive(cards, idx, published, looks, now_ms):
    """The whole board against the evidence. -> {ok, why, head, publishedVer, looks, byCard: {id: derived}, summary}"""
    pub = published or (idx or {}).get("publishedVer")
    looks = looks or {"rows": [], "known": {}, "from": None, "why": "the looks were not read"}
    by = {}
    for c in cards or []:
        if isinstance(c, dict) and c.get("id") is not None:
            by[str(c.get("id"))] = derive_card(c, idx, pub, looks, now_ms)
    ok = isinstance(idx, dict) and bool(idx.get("ok"))
    known = looks.get("known") or {}
    lk = "read" if known.get("grokbot") and known.get("third") else ("partly" if known.get("grokbot") else UNKNOWN)
    return {"ok": ok, "why": None if ok else (idx or {}).get("why"),
            "head": (idx or {}).get("head", "")[:9] if ok else None, "publishedVer": pub, "looks": lk,
            "looksWhy": looks.get("why"), "byCard": by, "summary": summarize(cards, by, ok)}


def summarize(cards, by, ok=True):
    """-> {cards, phases, drift: {kind: n}, owed, first: [{id, kind, say}]} - owed None when the tree was not read"""
    phases, kinds, first = {}, dict((k, 0) for k in DRIFT_KINDS), []
    order = dict((k, i) for i, k in enumerate(DRIFT_KINDS))
    flagged = []
    for c in cards or []:
        d = by.get(str((c or {}).get("id")))
        if not d:
            continue
        phases[d["phase"]] = phases.get(d["phase"], 0) + 1
        if d.get("drift"):
            kinds[d["drift"]["kind"]] += 1
            flagged.append((order[d["drift"]["kind"]], str(c.get("id")), d["drift"]))
    for _o, cid, dr in sorted(flagged, key=lambda x: (x[0], _idnum(x[1]))):
        if len(first) < 6:
            first.append({"id": cid, "kind": dr["kind"], "say": dr["say"][:200]})
    return {"cards": len(by), "phases": phases, "drift": kinds, "owed": (sum(kinds.values()) if ok else None),
            "first": first}


def _idnum(i):
    return (0, int(i)) if str(i).isdigit() else (1, str(i))


def say_line(phase, d):
    """The chip's words: "live v3864", "building", "third-eyed v3862", "UNKNOWN". -> str"""
    if phase == UNKNOWN:
        return "UNKNOWN"
    v = d.get("ver")
    return phase + ((" " + v) if v and RANK.get(phase, 0) >= RANK["shipped"] else "")


def main(argv=None):
    """Print the newest session's cards with their derived phase and any drift - read-only (no GitHub unless --looks)."""
    import argparse
    try:
        from console_safe import enable as _cs
        _cs()
    except Exception:
        pass
    import task_board as _tb
    ap = argparse.ArgumentParser(description=main.__doc__)
    ap.add_argument("--tasks", default=None, help="a tasks dir (default: the Mac's board)")
    ap.add_argument("--repo", default=os.path.dirname(HERE))
    ap.add_argument("--looks-cache", default=None, help="a looks cache to read (the console keeps tv/.task_truth_looks.json)")
    a = ap.parse_args(argv)
    now = int(time.time() * 1000)
    sessions = _tb.session_dirs(a.tasks)
    if not sessions:
        print("no session holds a card" if sessions == [] else "the board dir would not list - UNKNOWN")
        return 1
    cards = _tb.load_cards(os.path.join(a.tasks or _tb.TASKS_DIR, sessions[0][1])) or []
    cache = load_looks(a.looks_cache) if a.looks_cache else {}
    t = derive(cards, git_index(a.repo, now), None, looks_view(cache, now), now)
    print("tree %s · published %s · looks %s" % (t.get("head") or "UNKNOWN (%s)" % t.get("why"), t.get("publishedVer"),
                                                  t.get("looks")))
    for c in sorted(cards, key=lambda c: _idnum(c.get("id"))):
        d = t["byCard"].get(str(c.get("id"))) or {}
        print("#%-4s %-11s %-18s %s" % (c.get("id"), c.get("status"), say_line(d.get("phase"), d),
                                         str(c.get("subject") or "")[:70]))
        if d.get("drift"):
            print("      ! " + d["drift"]["say"][:160])
    print("owed: %s · %s" % (t["summary"]["owed"], t["summary"]["drift"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
