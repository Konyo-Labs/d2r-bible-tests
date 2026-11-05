# -*- coding: utf-8 -*-
"""v3865 (his words 2026-11-05, REG-3217 + REG-3218) - THE TASK BOARD IS DERIVED FROM THE EVIDENCE, LIKE BLUEPRINT AND HEART.

His words: "make sure its derived always console and you and the taskboard synced.. so we are always with our finger on the
trigger and know whats still being worked on and not shipped". MEASURED that evening: the board (the task panel's cards,
read by tv/task_board.py and published to /d2r/tasks.html) had not been touched for 6 hours while the work moved - 25 cards
said in_progress, several describing work shipped days earlier ("v3862 ship", REG-3155's proof bank, REG-3157's
ship_when_green) and none naming the fleet that was running. A card's status is typed by hand; nothing compared it to the
tree. BLUEPRINT.md and HEART.md are derived and the pre-push refuses them stale; the board was the one map still typed.

So every card now carries a DERIVED PHASE (REG-3217), read from the evidence and never from the card's own words:
  * its KEYS - the REG ids its subject names (REG-3154/3156, REG-3193..3195, REG-2980, 2986, 3109 and
    REG-2914/3086-3089/3098 all expand), else a version leading the subject ("v3862 ship"), else a branch the subject names
    (claude/..., ci/..., grok/...), else the REG ids, then the branches, its description names (`basis` says which).
  * each key resolved against git in the console's own checkout - one bounded read of every commit message, cached per
    HEAD + origin/main and at most every 10 min: no commit names it (no-evidence) | only local branches or worktrees
    (building) | a ci/ branch (graded) | origin/main (shipped vN - N the stamp the first such main commit shipped in).
  * LIVE is its own reading, not origin/main again: the newest SUCCESSFUL Publish run on main (the workflow that deploys
    the site) names the commit the site serves, and that commit's tv/WINDOWS_SHIP.json stamp >= N is live. The console's
    publishedVer is origin/main's stamp - the same tree that decides "shipped" - so it cannot see the hour a Publish runs.
  * then the looks, each ABOUT what its heading line names (the first line naming a version or a REG id), never what its
    evidence list or a changelog recap repeats lower down: GrokBot's VISUAL seat on #230 after the ship (its coder seat
    posts plans, not looks), and the third eye - a SECOND-EYE row on #231, never a Grok CLI status note on #230. A look
    whose heading says it FAILS, or that names the key on a line saying it fails / is broken / DIFFERS / STILL, REFUTES it:
    the newest look about a key decides. A look that could not be read is UNKNOWN, never "not looked"; a ship older than
    the looks the cache holds is UNKNOWN.
  * the card's phase is its least-advanced key's. A description REG that is NEWER work than the subject's (a fix, not a
    precedent) and is behind it holds the card there. UNKNOWN when git would not answer - never "no-evidence".

And a card whose hand status disagrees with that evidence is FLAGGED with the reason (REG-3218), but only by evidence that
arrived AFTER the hand last set the card (the card file's time): a card touched after its evidence is the hand's word, and
touching it is how a reviewed flag is accepted. in_progress or pending but third-eyed -> "ready to close"; in_progress or
pending and shipped more than SHIPPED_OPEN_MS ago -> "shipped and still in progress / pending" (with what is left); completed with work in git that
never reached main -> "closed but never shipped" (red, whatever the card's time); pending with commits -> "work started on a
pending card"; in_progress with nothing in git for more than STALE_DAYS -> "in progress with nothing built". The derivation
SAYS; it never rewrites a card's status - Claude and he decide. The console's eagle row "the board agrees with the tree"
counts the flags (console_doctor).

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
LOOKS_SCHEMA = 3                     # a cache written by another shape is rebuilt, never read as this one
GH_TIMEOUT_S = 60
LOOK_HEAD_CHARS = 600                # a look is ABOUT what the first line naming a version or REG id names, inside its head
LOOK_BODY_CHARS = 20000              # how much of a look is searched for a line that says the key fails
GROKBOT_ISSUE, THIRD_ISSUE = 230, 231
ISSUES = (GROKBOT_ISSUE, THIRD_ISSUE)
REPO_SLUG = "KonyoDigital/d2r-bible-tests"
PUBLISH_WORKFLOW = "publish.yml"     # "Publish - gates, review, then deploy": the one workflow that deploys the site
STALE_DAYS = 2                       # an in_progress card with nothing in git for longer is flagged
SHIPPED_OPEN_MS = 6 * 3600 * 1000    # an in_progress card whose work reached main longer ago than this is flagged
RANGE_MAX = 25                       # REG-a..b expands only when b - a is at most this
KEYS_MAX = 12
DAY_MS = 24 * 3600 * 1000

DRIFT_SAY = {
    "closed-never-shipped": "closed but never shipped",
    "ready-to-close": "ready to close",
    "shipped-still-open": "shipped and still open",
    "work-started": "work started on a pending card",
    "nothing-built": "in progress with nothing built",
}
DRIFT_KINDS = tuple(DRIFT_SAY)

_REG_HEAD_RX = re.compile(r"\bREG-(\d{1,5})\b")
#: one more item of a list: "/3156", ", 2986", " and 3109", ", REG-3157"
_REG_ITEM_RX = re.compile(r"\s*(?:/|,|&|\band\b)\s*(REG-)?(\d{1,5})\b")
#: the far end of a range: "..3195", " to REG-3186", "-3089" (a hyphen only when it touches both numbers), " – 3186"
_REG_RANGE_RX = re.compile(r"(?:\s*(?:\.\.\.?|…|\bto\b|\bthrough\b|–)\s*|-)(REG-)?(\d{1,5})\b")
_VER_RX = re.compile(r"\bv(\d{4})\b")
_LEAD_VER_RX = re.compile(r"^\s*v(\d{4})\b(?![’']s)")
_BRANCH_RX = re.compile(r"(?<![\w/.-])((?:claude|ci|grok)/[A-Za-z0-9](?:[A-Za-z0-9._/-]*[A-Za-z0-9])?)")


def _range_end(lo_txt, hi_txt):
    """"3193".."95" -> 3195 (a short far end keeps the near end's leading digits); -> int"""
    if len(hi_txt) < len(lo_txt):
        return int(lo_txt[:len(lo_txt) - len(hi_txt)] + hi_txt)
    return int(hi_txt)


def regs_in(text):
    """Every REG id the text names, in order, lists and ranges expanded. -> ["REG-3154", ...]

    A list goes on while each next item is joined by / , & or "and" and is either written REG-n or has as many digits as
    the id that opened it ("REG-2980, 2986, 3109" is three; "REG-3090, 12 cards" is one). A range is a..b, a to b, a
    through b, a – b or a-b (touching), and expands when b - a <= RANGE_MAX; wider, both ends are still named. MEASURED
    (review of the first cut, 2026-11-05): "REG-2980, 2986, 3109 were never built" read as REG-2980 alone, and
    "REG-2914/2915/2976/3021/3086-3089/3098" lost 3087, 3088 and 3098."""
    s = str(text or "")
    out = []
    i = 0
    while True:
        m = _REG_HEAD_RX.search(s, i)
        if not m:
            break
        width = len(m.group(1))
        prev = m.group(1)
        got = [int(prev)]
        j = m.end()
        while True:
            r = _REG_RANGE_RX.match(s, j)
            # a short far end ("..95") borrows the near end's digits; after "to"/"through" it must be a whole id
            if r and (r.group(1) or len(r.group(2)) >= width or not re.search(r"to|through", r.group(0))):
                hi = _range_end(prev, r.group(2))
                lo = int(prev)
                if hi > lo:
                    got += list(range(lo + 1, hi + 1)) if hi - lo <= RANGE_MAX else [hi]
                    prev, j = str(hi), r.end()
                    continue
            it = _REG_ITEM_RX.match(s, j)
            if it and (it.group(1) or len(it.group(2)) == width):
                got.append(int(it.group(2)))
                prev, j = it.group(2), it.end()
                continue
            break
        for n in got:
            k = "REG-%d" % n
            if k not in out:
                out.append(k)
        i = max(j, m.end())
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
_SITE_VER_CACHE = {}


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
    """One bounded read of the checkout's evidence. -> {"ok": True, head, main, keys: {key: [(sha, ms)]}, main_ver,
    ver_at, ci, refs, ct, publishedVer} or {"ok": False, "why"} - a tree that would not answer is UNKNOWN, never empty."""
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
    # newest first, so the last stamp seen walking it is the nearest newer one). ver_at: when that version's newest commit
    # on main was made - the nearest the tree comes to the moment the version reached main.
    main_ver, ver_at, cur = {}, {}, None
    for sha in main_list:
        lv = lead_version(subj.get(sha, ""))
        if lv:
            cur = lv
            if lv not in ver_at and sha in ct:
                ver_at[lv] = ct[sha]
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
        pub = None                                        # UNKNOWN
    return {"ok": True, "head": head, "main": main, "keys": keys, "main_set": main_set, "main_ver": main_ver,
            "ver_at": ver_at, "ci": ci, "refs": refs, "ct": ct, "publishedVer": pub, "at": int(now_ms),
            "commits": len(ct)}


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


def site_view(cache, now_ms, repo, run=None, memo=None):
    """What the SITE serves, read apart from origin/main: the newest successful Publish run on main (refresh_looks keeps it)
    names a commit, and that commit's tv/WINDOWS_SHIP.json is the stamp it deployed. -> {ver, sha, at, run, why}; ver None
    (UNKNOWN) when the run could not be read, is stale, or its commit is not in this checkout yet."""
    memo = _SITE_VER_CACHE if memo is None else memo
    pl = ((cache or {}).get("publish") or {}) if isinstance(cache, dict) else {}
    out = {"ver": None, "sha": None, "at": None, "run": None, "why": None}
    if not isinstance(cache, dict):
        out["why"] = "the looks cache would not read, so the Publish run is UNKNOWN"
        return out
    if not (isinstance(pl.get("okAt"), int) and now_ms - pl["okAt"] < LOOKS_STALE_MS):
        out["why"] = pl.get("why") or "the Publish runs have not been read since this console started"
        return out
    sha = pl.get("sha")
    out.update(sha=(str(sha)[:9] if sha else None), at=pl.get("runAt"), run=pl.get("runId"))
    if not sha:
        out["why"] = pl.get("why") or "no successful Publish run on main"
        return out
    if sha not in memo:
        try:
            memo[sha] = json.loads(_git(repo, ["show", "%s:tv/WINDOWS_SHIP.json" % sha], run or _default_run())
                                   ).get("ver") or None
        except Exception as e:
            out["why"] = "the commit the site serves (%s) would not read here (%s)" % (str(sha)[:9], str(e)[:80])
            return out
    out["ver"] = memo[sha]
    if not out["ver"]:
        out["why"] = "the commit the site serves (%s) carries no stamp" % str(sha)[:9]
    return out


# -------------------------------------------------------------------------------------------------------------- looks

#: who posted a #230/#231 comment, off its first meaningful line. GrokBot's VISUAL seat only: "Seat: Grok Bot (code)" is
#: its coder seat posting plans. The third eye is a SECOND-EYE row (or the Grok CLI's cross-family / second-eye heading),
#: never "Seat: Grok CLI (third eye)" - that seat posts status notes ("origin/main moved", "has not read the range").
_SEAT_RX = (
    ("grokbot", re.compile(r"^(?:seat:\s*grok\s*bot\s*\((?!\s*code)|grokbot\s+eyes\b|gb-l\b|"
                           r"(?:@?claude\s*·\s*)?grok\s*bot\s+visual\b)", re.I)),
    ("third", re.compile(r"^(?:second-eye\b|grok\s*cli\s+second\s+eye\b|seat:\s*grok\s*cli\s*\(cross-family)", re.I)),
)
#: the heading says the look FAILED
_HEAD_FAIL_RX = re.compile(r"\b(?:fail(?:s|ed|ing)?|broken|reopen(?:s|ed)?|not\s+fixed|regress(?:ed|ion)?)\b", re.I)
#: a line that says what it names fails - its words, or GrokBot's DIFFERS / STILL tags (upper case, as it writes them)
_LINE_FAIL_RX = re.compile(r"\b(?:fail(?:s|ed|ing)?|broken|reopen(?:s|ed)?|not\s+fixed|regress(?:ed|ion)?)\b", re.I)
_TAG_FAIL_RX = re.compile(r"\b(?:DIFFERS|STILL)\b")
_VERDICT_RX = re.compile(r"(?im)^[\s*_#>-]*verdict[\s*_]*:[\s*_]*([A-Za-z][A-Za-z -]{0,30})")
#: v3866 - a row that RECORDS an eye which did not judge is no look at all: "cannot-tell" (the second-eye ledger's own
#: word - "recorded, and NOT a look"), an unreachable seat, no answer. MEASURED the night it shipped: the #231 row for
#: v3864 ("verdict **cannot-tell**") made four v3864 cards read "ready to close" on an eye that said it could not judge.
_NO_LOOK_RX = re.compile(r"\b(?:cannot[- ]tell|could\s+not\s+(?:tell|judge)|unreachable|empty\s+seat|no\s+answer)\b",
                         re.I)


def seat_of(body):
    """Who posted a #230/#231 comment, read off its first meaningful line (the seat tag). -> "grokbot"|"third"|None"""
    for raw in str(body or "").splitlines():
        line = raw.strip()
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


def about(body):
    """What a look is ABOUT: the versions and REG ids on the first line, inside its head, that names either.
    -> {"vers": [...], "regs": [...], "line": str}
    MEASURED on #230 2026-11-05: GrokBot's "# v3863 ship check" names "changelog-v3861-63.json" in its evidence list and
    recaps "- REG-3153..3165: prove beside cloud" from the changelog lower down. Counted, every version in its first 600
    characters made v3861 and v3862 "looked" (30 of 84 cards read "ready to close"), and every REG id in its body made
    cards #7-#18 "looked v3862" by a look at v3863. The heading says what was looked at; the evidence does not."""
    for line in str(body or "")[:LOOK_HEAD_CHARS].splitlines():
        vs, rs = versions_in(line), regs_in(line)
        if vs or rs:
            return {"vers": vs[:12], "regs": rs[:24], "line": line}
    return {"vers": [], "regs": [], "line": ""}


def about_versions(body):
    """-> the versions a look is about (its heading line's)"""
    return about(body)["vers"]


def refuted_in(body):
    """The REG ids a look names on a line that says they fail (fail / broken / reopen / not fixed / regressed, or the
    DIFFERS / STILL tags). -> ["REG-101"]"""
    out = []
    for line in str(body or "")[:LOOK_BODY_CHARS].splitlines():
        if _LINE_FAIL_RX.search(line) or _TAG_FAIL_RX.search(line):
            for k in regs_in(line):
                if k not in out:
                    out.append(k)
    return out[:60]


def look_row(comment, issue):
    """One GitHub comment -> the little it is kept as: {id, issue, at, seat, regs, vers, fail, refutes, verdict}, or None
    when it is no seat's look. A GrokBot look counts only on #230 and a third eye only on #231."""
    if not isinstance(comment, dict):
        return None
    body = str(comment.get("body") or "")
    seat = seat_of(body)
    if (seat, int(issue)) not in (("grokbot", GROKBOT_ISSUE), ("third", THIRD_ISSUE)):
        return None
    at = _iso_ms(comment.get("created_at"))
    if at is None or comment.get("id") is None:
        return None
    ab = about(body)
    vm = _VERDICT_RX.search(body[:LOOK_HEAD_CHARS * 2])
    verdict = vm.group(1).strip().lower()[:20] if vm else None
    return {"id": str(comment.get("id")), "issue": int(issue), "at": at, "seat": seat,
            "regs": ab["regs"], "vers": ab["vers"], "fail": bool(_HEAD_FAIL_RX.search(ab["line"])),
            "refutes": refuted_in(body), "verdict": verdict,
            "noLook": bool(_NO_LOOK_RX.search(ab["line"]) or (verdict and _NO_LOOK_RX.search(verdict)))}


def load_looks(path):
    """-> the cache dict; {} when there is none yet, or it was written in another shape (a fact: it is rebuilt); None when
    it exists and will not read (UNKNOWN)"""
    try:
        with io.open(path, encoding="utf-8") as fh:
            d = json.load(fh)
    except FileNotFoundError:
        return {}
    except Exception:
        return None
    if not isinstance(d, dict):
        return None
    return d if d.get("schema") == LOOKS_SCHEMA else {}


def _runs_of(got):
    """GitHub's answer for a workflow's runs -> [run dicts], or None when it is not that answer"""
    for doc in (got if isinstance(got, list) else [got]):
        if isinstance(doc, dict) and isinstance(doc.get("workflow_runs"), list):
            return [r for r in doc["workflow_runs"] if isinstance(r, dict)]
    return None


def _refresh_publish(cache, now_ms, gh, every_ms):
    pl = cache.setdefault("publish", {})
    if isinstance(pl.get("triedAt"), int) and now_ms - pl["triedAt"] < every_ms:
        return False
    pl["triedAt"] = int(now_ms)
    try:
        got = gh("repos/%s/actions/workflows/%s/runs?branch=main&status=success&per_page=1" % (REPO_SLUG, PUBLISH_WORKFLOW),
                 paginate=False)
    except Exception as e:
        pl["why"] = "GitHub would not answer the Publish runs (%s)" % str(e)[:120]
        return True
    runs = _runs_of(got)
    if runs is None:
        pl["why"] = "GitHub answered the Publish runs with something that is not a run list"
        return True
    r = runs[0] if runs else {}
    pl.update(okAt=int(now_ms), sha=(str(r.get("head_sha")) if r.get("head_sha") else None),
              runAt=_iso_ms(r.get("updated_at") or r.get("created_at")), runId=r.get("id"),
              why=(None if runs else "no successful Publish run on main"))
    return True


def refresh_looks(path, now_ms, gh, issues=ISSUES, every_ms=LOOKS_EVERY_MS):
    """Ask GitHub for the comments since the last read and the newest successful Publish run, at most every `every_ms`,
    into the cache at `path`. gh(api_path, paginate=True) returns the answer's dicts or raises. -> the cache dict, or None
    when the cache would not read (it is never written over a store this process could not read)."""
    cache = load_looks(path)
    if cache is None:
        return None
    cache["schema"] = LOOKS_SCHEMA
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
            else:
                rows.pop(str(c.get("id")), None)          # an edit that made it no look takes it back
        keep_from = int(now_ms - LOOKS_KEEP_DAYS * DAY_MS)
        lane["rows"] = sorted((r for r in rows.values() if r.get("at", 0) >= keep_from), key=lambda r: r["at"])
        # the cache holds every comment touched since its FIRST read's `since`, less what aged out of the keep window
        first = lane.get("from") if isinstance(lane.get("from"), int) else (_iso_ms(since) or keep_from)
        lane["from"] = max(int(first), keep_from)
        lane["since"] = newest
        lane["okAt"] = int(now_ms)
        lane["why"] = None
    changed = _refresh_publish(cache, now_ms, gh, every_ms) or changed
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
    return {"rows": rows, "known": {"grokbot": bool(fresh.get(GROKBOT_ISSUE)), "third": bool(fresh.get(THIRD_ISSUE))},
            "from": (max(froms) if froms else None), "why": "; ".join(whys) or None}


# ------------------------------------------------------------------------------------------------------------- derive

def _look_verdict(looks, seat, key, ver, since_ms):
    """The NEWEST look by `seat` after `since_ms` about this key or its version decides. -> (passing row, refuting row)"""
    about_it = []
    for r in looks.get("rows") or []:
        if r.get("seat") != seat or not isinstance(r.get("at"), int) or r["at"] < since_ms:
            continue
        if r.get("noLook"):
            continue                                      # v3866 - an eye that did not judge is no look, either way
        if key in (r.get("regs") or []) or (ver and ver in (r.get("vers") or [])):
            about_it.append(r)
    if not about_it:
        return None, None
    last = max(about_it, key=lambda r: (r["at"], r.get("id")))
    if last.get("fail") or key in (last.get("refutes") or []):
        return None, last
    return last, None


def _ref(r):
    return {"id": r["id"], "issue": r.get("issue"), "at": r["at"], "verdict": r.get("verdict")}


def _site(site):
    if isinstance(site, dict):
        return site
    return {"ver": site, "why": None if site else "the site's version was not read"}


def resolve_key(key, idx, site, looks):
    """One key against the evidence. -> {key, phase, sha, ver, at, atWhat, first, last, shipAt, look, third, refuted,
    unknown: [rungs], why}. `site` is site_view's answer (a bare version string is taken as one)."""
    site = _site(site)
    out = {"key": key, "phase": "no-evidence", "sha": None, "ver": None, "at": None, "atWhat": None, "first": None,
           "last": None, "shipAt": None, "look": None, "third": None, "refuted": None, "unknown": [], "why": None}
    main_set, ci = idx["main_set"], idx["ci"]
    if key.startswith("REG-") or _VER_RX.match(key):
        hits = idx["keys"].get(key) or []
        if not hits:
            out["why"] = "no commit names it"
            return out
        first_any, last_any = min(t for _s, t in hits), max(t for _s, t in hits)
        out.update(first=first_any, last=last_any)
        on_main = sorted((h for h in hits if h[0] in main_set), key=lambda h: h[1])
        if not on_main:
            on_ci = [h for h in hits if h[0] in ci]
            pick = max(on_ci or hits, key=lambda h: h[1])
            out.update(phase="graded" if on_ci else "building", sha=pick[0][:9], at=pick[1], atWhat="committed",
                       why="on a ci/ branch, not on main" if on_ci else "only on a local branch or worktree")
            return out
        sha, t_main = on_main[0]
        ver = key if key.startswith("v") else idx["main_ver"].get(sha)
    else:
        tip = idx["refs"].get(key)
        if not tip:
            out["why"] = "no branch of that name in this checkout"
            return out
        t_main = idx["ct"].get(tip)
        first_any = t_main or 0
        out.update(first=t_main, last=t_main)
        if tip not in main_set:
            out.update(phase="graded" if tip in ci else "building", sha=tip[:9], at=t_main, atWhat="committed",
                       why="its tip is on a ci/ branch, not on main" if tip in ci else "its tip is not on main")
            return out
        sha, ver = tip, idx["main_ver"].get(tip)
    ship_at = (idx.get("ver_at") or {}).get(ver) or t_main
    out.update(phase="shipped", sha=sha[:9], ver=ver, at=ship_at, atWhat="shipped", shipAt=ship_at, why="on origin/main")
    pv, nv = _vnum(site.get("ver")), _vnum(ver)
    if nv is None or pv is None:
        out["unknown"].append("live")
        out["why"] = "on origin/main; whether the site serves it is UNKNOWN (%s)" % (
            "the stamp it shipped in could not be read" if nv is None else (site.get("why") or "the site was not read"))
    elif pv < nv:
        out["why"] = "on origin/main; the site still serves %s (the newest successful Publish run)" % site.get("ver")
        return out
    else:
        out["phase"] = "live"
        out["why"] = "published (the site serves %s)" % site.get("ver")
    known = looks.get("known") or {}
    before_window = isinstance(looks.get("from"), int) and t_main is not None and t_main < looks["from"]
    look, l_ref = _look_verdict(looks, "grokbot", key, ver, t_main or 0) if known.get("grokbot") else (None, None)
    third, t_ref = _look_verdict(looks, "third", key, ver, first_any) if known.get("third") else (None, None)
    if look:
        out["look"] = _ref(look)
    elif l_ref:
        out["refuted"] = dict(_ref(l_ref), seat="GrokBot")
    elif not known.get("grokbot") or before_window:
        out["unknown"].append("looked")
    if third:
        out["third"] = _ref(third)
    elif t_ref:
        out["refuted"] = out["refuted"] or dict(_ref(t_ref), seat="the third eye")
    elif not known.get("third") or before_window:
        out["unknown"].append("third-eyed")
    if out["refuted"]:
        out["why"] = "%s's look (comment %s) says it still fails" % (out["refuted"]["seat"], out["refuted"]["id"])
    if look:
        out.update(phase="looked", at=look["at"], atWhat="looked")
        if third:
            out.update(phase="third-eyed", at=max(look["at"], third["at"]), atWhat="third-eyed")
    return out


def _utc(ms):
    return time.strftime("%m-%d %H:%MZ", time.gmtime(ms / 1000.0)) if isinstance(ms, (int, float)) else "?"


def _left(rows):
    """What a shipped card still waits for, in words, over EVERY key it was judged on (a card keyed on a defect and its
    fix waits for both). -> str"""
    out = []

    def add(s):
        if s not in out:
            out.append(s)
    for r in rows:
        unk, ref = r.get("unknown") or [], r.get("refuted") or {}
        if "live" in unk:
            add("whether the site serves %s (UNKNOWN)" % (r.get("ver") or r.get("key")))
        elif RANK.get(r.get("phase"), 0) < RANK["live"]:
            add("the site publishing %s" % (r.get("ver") or r.get("key")))
            continue                                      # nobody looks at a page the site does not serve yet
        if ref:
            add("%s's look (comment %s) says %s still fails" % (ref.get("seat"), ref.get("id"), r.get("key")))
        if not r.get("look") and not (ref and ref.get("seat") == "GrokBot"):
            add("GrokBot's look on #230" + (" (UNKNOWN - unread)" if "looked" in unk else ""))
        if not r.get("third") and not (ref and ref.get("seat") == "the third eye"):
            add("the third eye on #231" + (" (UNKNOWN - unread)" if "third-eyed" in unk else ""))
    return "; ".join(out) or "nothing the tree can see"


def drift(status, d, age_ms, now_ms=None):
    """REG-3218 - where the hand status disagrees with the evidence. -> {kind, say, basis} | None. Never on an UNKNOWN phase:
    a tree that did not answer cannot disagree with anything. Only evidence that arrived AFTER the hand last set the card
    (d["handAt"], the card file's time) raises a flag - a card touched after its evidence is the hand's word - except
    "closed but never shipped", which is wrong whenever it was closed."""
    ph = d.get("phase")
    if ph not in RANK:
        return None
    hi = d.get("hi") if d.get("hi") in RANK else ph
    hand = d.get("handAt") if isinstance(d.get("handAt"), (int, float)) and not isinstance(d.get("handAt"), bool) else None
    now_ms = now_ms if isinstance(now_ms, (int, float)) else int(time.time() * 1000)

    def newer(t):
        return isinstance(t, (int, float)) and (hand is None or t > hand)
    bott = d.get("bottleneck") or {}
    top = d.get("top") or {}
    where = "%s %s%s" % (bott.get("key") or "its key", bott.get("phase") or ph,
                         (" (" + str(bott.get("sha")) + ")") if bott.get("sha") else "")
    kind = say = None
    if status == "completed":
        if RANK[hi] >= RANK["building"] and RANK[ph] < RANK["shipped"]:
            kind, say = "closed-never-shipped", "closed but never shipped - %s: %s" % (where, bott.get("why") or "not on origin/main")
    elif ph == "third-eyed" and newer(d.get("evidenceAt")):
        lk, th = d.get("look") or {}, d.get("third") or {}
        kind, say = "ready-to-close", ("ready to close - shipped %s, looked by GrokBot (#230 comment %s), third-eyed (#231 "
                                       "comment %s%s), after this card was last set" % (
                                           d.get("ver") or "", lk.get("id"), th.get("id"),
                                           (", verdict " + str(th.get("verdict"))) if th.get("verdict") else ""))
    elif status in ("in_progress", "pending") and RANK["shipped"] <= RANK[ph] < RANK["third-eyed"] \
            and newer(d.get("shipAt")) and now_ms - d["shipAt"] > SHIPPED_OPEN_MS:
        # v3866 - measured on his board: a PENDING card whose every key is live read "work started on a pending card"
        kind, say = "shipped-still-open", "shipped and still %s - %s on main since %s; left: %s" % (
            "in progress" if status == "in_progress" else "pending",
            ", ".join(d.get("keys") or [])[:60] or "its key", _utc(d.get("shipAt")), d.get("left") or "UNKNOWN")
    elif status == "pending" and RANK[hi] >= RANK["building"] and newer(d.get("lastCommit")):
        kind, say = "work-started", "work started on a pending card - %s is %s%s, committed %s" % (
            top.get("key"), top.get("phase"), (" (" + str(top.get("sha")) + ")") if top.get("sha") else "",
            _utc(d.get("lastCommit")))
    elif status == "in_progress" and hi == "no-evidence" and isinstance(age_ms, (int, float)) \
            and not isinstance(age_ms, bool) and age_ms > STALE_DAYS * DAY_MS:
        kind, say = "nothing-built", "in progress with nothing built since %s - %s" % (
            _utc(hand),
            "it names no REG id, version or branch, so nothing in git can be found for it" if not d.get("keys")
            else "no commit or branch names %s" % ", ".join(d["keys"][:4]))
    if kind is None:
        return None
    if d.get("basis") == "description":
        # a description cites precedents as often as it names its own work: said, so the reader weighs it
        say += " (keyed on its description, which may only cite it)"
    return {"kind": kind, "say": say, "basis": d.get("basis")}


def _newest(*ts):
    got = [t for t in ts if isinstance(t, (int, float)) and not isinstance(t, bool)]
    return max(got) if got else None


def derive_card(card, idx, site, looks, now_ms):
    """-> {phase, keys, basis, ver, sha, at, atWhat, look, third, refuted, unknown, why, hi, bottleneck, top, shipAt,
    lastCommit, evidenceAt, handAt, drift}"""
    keys, basis = card_keys(card)
    mt = card.get("_mtime")
    hand = mt if isinstance(mt, (int, float)) and not isinstance(mt, bool) else None
    d = {"keys": keys, "basis": basis, "phase": UNKNOWN, "ver": None, "sha": None, "at": None, "atWhat": None,
         "look": None, "third": None, "refuted": None, "unknown": [], "why": None, "hi": None, "bottleneck": None,
         "top": None, "shipAt": None, "lastCommit": None, "evidenceAt": None, "left": None, "handAt": hand,
         "drift": None}
    if not isinstance(idx, dict) or not idx.get("ok"):
        d["why"] = (idx or {}).get("why") or "the tree was not read - UNKNOWN"
        return d
    if not keys:
        d.update(phase="no-evidence", hi="no-evidence", why="it names no REG id, version or branch")
    else:
        per = [resolve_key(k, idx, site, looks) for k in keys]
        lo = min(per, key=lambda r: RANK[r["phase"]])
        top = max(per, key=lambda r: RANK[r["phase"]])
        rows = list(per)
        if basis == "subject":
            # a card keyed on its subject may name, in its description, the REG that is fixing it ("REG-3110 is INERT ...
            # fixed by REG-3167"). A description REG that is NEWER work than the subject's (its newest commit is not older
            # than the subject's first, or it has none yet) and is behind the card holds the card where it is - on a
            # branch, on main but not published, not yet looked. One whose work all predates the subject's is a precedent
            # ("same class as REG-2203") and changes nothing.
            # When the subject's keys name nothing in git there is no "before" to measure, and only a description REG
            # still on a branch counts (work in flight for this card).
            subj_first = min(r["first"] for r in per if r["first"]) if any(r["first"] for r in per) else None
            for r in (resolve_key(k, idx, site, looks) for k in regs_in(card.get("description"))[:KEYS_MAX]
                      if k not in keys):
                if subj_first is None and r["phase"] not in ("building", "graded"):
                    continue
                if r["last"] is not None and subj_first is not None and r["last"] < subj_first:
                    continue                                  # a precedent: all its work came before the card's
                rows.append(r)
                if RANK[r["phase"]] < RANK[lo["phase"]]:
                    lo = dict(r, why="%s - its description's %s, newer work than the subject's, is %s" % (
                        r["why"], r["key"], r["phase"]))
                if RANK[r["phase"]] > RANK[top["phase"]]:
                    top = r
        unk = []
        for r in rows:
            for u in r["unknown"]:
                if u not in unk:
                    unk.append(u)
        shipped = [r for r in rows if r["shipAt"]]
        d.update(phase=lo["phase"], ver=lo["ver"], sha=lo["sha"], at=lo["at"], atWhat=lo["atWhat"], look=lo["look"],
                 third=lo["third"], refuted=lo["refuted"], unknown=unk, why=lo["why"], hi=top["phase"],
                 bottleneck=dict((k, lo[k]) for k in ("key", "phase", "sha", "why")),
                 top=dict((k, top[k]) for k in ("key", "phase", "sha")),
                 shipAt=(max(r["shipAt"] for r in shipped) if shipped and len(shipped) == len(rows) else None),
                 lastCommit=_newest(*[r["last"] for r in rows]), left=_left(rows),
                 evidenceAt=_newest(*[_newest((r["look"] or {}).get("at"), (r["third"] or {}).get("at")) for r in rows]))
    age = (now_ms - hand) if hand is not None else None
    d["drift"] = drift(card.get("status"), d, age, now_ms)
    return d


def derive(cards, idx, site, looks, now_ms):
    """The whole board against the evidence. -> {ok, why, head, publishedVer, mainVer, site, looks, byCard, summary}
    `site` is site_view's answer; publishedVer is the version the SITE serves (None = UNKNOWN), mainVer origin/main's."""
    site = _site(site)
    looks = looks or {"rows": [], "known": {}, "from": None, "why": "the looks were not read"}
    by = {}
    for c in cards or []:
        if isinstance(c, dict) and c.get("id") is not None:
            by[str(c.get("id"))] = derive_card(c, idx, site, looks, now_ms)
    ok = isinstance(idx, dict) and bool(idx.get("ok"))
    known = looks.get("known") or {}
    lk = "read" if known.get("grokbot") and known.get("third") else (
        "partly" if known.get("grokbot") or known.get("third") else UNKNOWN)
    return {"ok": ok, "why": None if ok else (idx or {}).get("why"),
            "head": (idx or {}).get("head", "")[:9] if ok else None, "publishedVer": site.get("ver"),
            "siteWhy": site.get("why"), "mainVer": (idx or {}).get("publishedVer") if ok else None, "looks": lk,
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
    """Print the newest session's cards with their derived phase and any drift - read-only (no GitHub; --looks-cache reads
    a cache the console wrote)."""
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
    t = derive(cards, git_index(a.repo, now), site_view(cache, now, a.repo), looks_view(cache, now), now)
    print("tree %s · site %s · main %s · looks %s" % (t.get("head") or "UNKNOWN (%s)" % t.get("why"),
                                                     t.get("publishedVer") or "UNKNOWN", t.get("mainVer"), t.get("looks")))
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
