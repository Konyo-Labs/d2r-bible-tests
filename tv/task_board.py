# -*- coding: utf-8 -*-
"""v3864 (his ask 2026-11-05, card 57) - THE TASK BOARD ONLINE: what the Mac's board says, readable from any of his PCs.

His words: "a link button ... it can open up as a browser in chrome or whatever is defaulted on that PC" and "i want it to work
on deans PC for instance". The board lives on his Mac (~/.claude/tasks/<session>/<n>.json, drawn by claude-task-viewer on
:17955, which no other PC can reach). So the Mac's console publishes a SCRUBBED copy through the roster worker it already
signs with (kind "tasks", his approver key only), the site renders it at /d2r/tasks.html behind the site password, and every
console's footer has a button that opens that page in the PC's own default browser.

THE SITE PASSWORD IS IN THE PUBLIC REPO, so the page is semi-public and every text is scrubbed before it leaves the Mac:
home paths, temp paths, Windows user paths, IP addresses, e-mail addresses, user@host, .local hostnames and token-shaped
strings never leave. Pure functions here; the console's lane does the reading, the posting and the pacing.
"""
import hashlib
import io
import json
import os
import re

TASKS_DIR = os.path.join(os.path.expanduser("~"), ".claude", "tasks")
NAMES_FILE = "_session_names.json"
MAX_CARDS = 200
SUBJECT_MAX = 300
ACTIVE_MAX = 120
DESC_MAX = 1500
BOARD_MAX_BYTES = 180 * 1024
POST_MIN_GAP_MS = 2 * 60 * 1000          # a change is published at most every 2 min
POST_REFRESH_MS = 30 * 60 * 1000         # an unchanged board is re-posted every 30 min (the page says how old it is)
STATUSES = ("in_progress", "pending", "completed")

_SCRUB = (
    (re.compile(r"/(?:Users|home)/[^/\s'\"`)]+(?:/[^\s'\"`)]*)?"), "<path>"),
    (re.compile(r"/(?:private/)?(?:tmp|var/folders)/[^\s'\"`)]*"), "<path>"),
    (re.compile(r"[A-Za-z]:\\\\?Users\\\\?[^\s'\"`)]+"), "<path>"),
    (re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b"), "<email>"),
    (re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b"), "<ip>"),
    (re.compile(r"\b[\w-]+@[\w.-]+\b"), "<login>"),
    (re.compile(r"\b[\w-]+\.local\b"), "<host>"),
    (re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,}|xox[abpr]-[A-Za-z0-9-]{10,})\b"), "<token>"),
)


def scrub(text):
    """A card's words with nothing that names a machine, a person's path or a secret. -> str"""
    s = str(text if text is not None else "")
    for rx, rep in _SCRUB:
        s = rx.sub(rep, s)
    return s


def _cut(text, n):
    s = scrub(text)
    return s if len(s) <= n else s[: n - 1] + "…"


def session_dirs(tasks_dir=None):
    """-> [(newest card mtime, dir name)] of the session dirs that hold at least one card, newest first; [] when the board
    dir does not exist (no board yet, a fact); None when it exists and will not list (UNKNOWN - never an empty board)"""
    root = tasks_dir or TASKS_DIR
    out = []
    try:
        names = os.listdir(root)
    except FileNotFoundError:
        return []
    except OSError:
        return None
    for d in names:
        p = os.path.join(root, d)
        if not os.path.isdir(p):
            continue
        newest = None
        try:
            for f in os.listdir(p):
                if f.endswith(".json"):
                    t = os.path.getmtime(os.path.join(p, f))
                    newest = t if newest is None or t > newest else newest
        except OSError:
            continue
        if newest is not None:
            out.append((newest, d))
    return sorted(out, reverse=True)


def session_name(session, tasks_dir=None):
    """The name he gave the session (_session_names.json), scrubbed, or None"""
    try:
        with io.open(os.path.join(tasks_dir or TASKS_DIR, NAMES_FILE), encoding="utf-8") as fh:
            names = json.load(fh)
        n = names.get(session) if isinstance(names, dict) else None
        return _cut(n, 120) if isinstance(n, str) and n.strip() else None
    except Exception:
        return None


def load_cards(session_dir):
    """-> [card dicts] read from one session dir, or None when the dir will not read (UNKNOWN, never an empty board)"""
    try:
        files = [f for f in os.listdir(session_dir) if f.endswith(".json")]
    except OSError:
        return None
    cards = []
    for f in files:
        try:
            with io.open(os.path.join(session_dir, f), encoding="utf-8") as fh:
                c = json.load(fh)
        except Exception:
            continue
        if isinstance(c, dict) and c.get("subject"):
            # REG-3218 - when the card last changed (its file's mtime, ms): how long an in_progress card has had nothing
            # built is measured from here; None when it will not stat (UNKNOWN, never "just now")
            try:
                c["_mtime"] = int(os.path.getmtime(os.path.join(session_dir, f)) * 1000)
            except OSError:
                c["_mtime"] = None
            cards.append(c)
    return cards


def _id_key(c):
    i = str(c.get("id") or "")
    return (0, int(i)) if i.isdigit() else (1, i)


def _chip(d):
    """REG-3217 - a card's DERIVED phase as the site keeps it (tv/task_truth.py), every text scrubbed like the card's own."""
    if not isinstance(d, dict):
        return None
    lk, th, rf = d.get("look") or {}, d.get("third") or {}, d.get("refuted") or {}
    # v3866 (the review of REG-3217) - `at` is WHEN the phase was reached and `w` says which moment that is (committed,
    # shipped, looked, third-eyed): the first cut published the first main commit's time under every phase
    return {"p": _cut(d.get("phase"), 20), "v": _cut(d.get("ver"), 12) if d.get("ver") else None,
            "sha": _cut(d.get("sha"), 12) if d.get("sha") else None,
            "at": d.get("at") if isinstance(d.get("at"), int) else None,
            "w": _cut(d.get("atWhat"), 12) if d.get("atWhat") else None,
            "keys": [_cut(k, 48) for k in (d.get("keys") or [])[:6]], "basis": d.get("basis"),
            "look": _cut(lk.get("id"), 20) if lk.get("id") else None,
            "third": _cut(th.get("id"), 20) if th.get("id") else None,
            "refuted": ({"id": _cut(rf.get("id"), 20), "seat": _cut(rf.get("seat"), 20)} if rf.get("id") else None),
            "unknown": [_cut(u, 20) for u in (d.get("unknown") or [])[:4]], "why": _cut(d.get("why"), 200)}


def _drift(d):
    """REG-3218 - the flag a card wears when its hand status disagrees with the evidence, scrubbed. -> {kind, say} | None"""
    dr = (d or {}).get("drift") if isinstance(d, dict) else None
    if not isinstance(dr, dict) or not dr.get("kind"):
        return None
    return {"kind": _cut(dr.get("kind"), 32), "say": _cut(dr.get("say"), 300)}


def board(cards, title, now_ms, truth=None):
    """-> the record the site keeps: {title, at, counts, cards: [{id, subject, status, active, description, phase, drift}],
    truth}. `truth` is tv/task_truth.derive's answer (REG-3217/3218); without one the cards carry no phase and the record no
    truth - never a phase nobody derived."""
    rows = []
    by = (truth or {}).get("byCard") if isinstance(truth, dict) else None
    for c in sorted(cards or [], key=_id_key)[:MAX_CARDS]:
        st = c.get("status") if c.get("status") in STATUSES else "pending"
        row = {"id": _cut(c.get("id"), 12), "subject": _cut(c.get("subject"), SUBJECT_MAX), "status": st,
               "active": _cut(c.get("activeForm"), ACTIVE_MAX), "description": _cut(c.get("description"), DESC_MAX)}
        if isinstance(by, dict):
            d = by.get(str(c.get("id")))
            row["phase"] = _chip(d) or {"p": "unknown", "why": "this card was not derived"}
            row["drift"] = _drift(d)
        rows.append(row)
    counts = dict((s, sum(1 for r in rows if r["status"] == s)) for s in STATUSES)
    out = {"title": _cut(title or "the task board", 120), "at": int(now_ms), "counts": counts, "cards": rows}
    if isinstance(truth, dict):
        sm = truth.get("summary") or {}
        out["truth"] = {"ok": bool(truth.get("ok")), "why": _cut(truth.get("why"), 200) if truth.get("why") else None,
                        "head": _cut(truth.get("head"), 12) if truth.get("head") else None,
                        "publishedVer": _cut(truth.get("publishedVer"), 12) if truth.get("publishedVer") else None,
                        "mainVer": _cut(truth.get("mainVer"), 12) if truth.get("mainVer") else None,
                        "looks": _cut(truth.get("looks"), 12), "owed": sm.get("owed") if truth.get("ok") else None,
                        "drift": dict((_cut(k, 32), int(v)) for k, v in (sm.get("drift") or {}).items()),
                        "phases": dict((_cut(k, 20), int(v)) for k, v in (sm.get("phases") or {}).items())}
    # a board past the site's cap gives up description words first, the longest first, never a card
    while len(json.dumps(out, ensure_ascii=False).encode("utf-8")) > BOARD_MAX_BYTES:
        longest = max(rows, key=lambda r: len(r["description"]), default=None)
        if not longest or len(longest["description"]) <= 80:
            break
        longest["description"] = longest["description"][: len(longest["description"]) // 2] + "…"
    return out


def digest(b):
    """the board's content fingerprint, its time left out (an unchanged board is not a new one)"""
    core = {k: v for k, v in (b or {}).items() if k != "at"}
    return hashlib.sha256(json.dumps(core, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def due(state, b, now_ms):
    """-> (True, why) when this board should be posted now, else (False, why). state: {hash, at} of the last post"""
    state = state if isinstance(state, dict) else {}
    last = state.get("at") if isinstance(state.get("at"), int) else None
    h = digest(b)
    if last is None:
        return True, "first post"
    gap = now_ms - last
    if h != state.get("hash"):
        return (gap >= POST_MIN_GAP_MS), ("changed" if gap >= POST_MIN_GAP_MS else "changed - waits out the 2 min gap")
    return (gap >= POST_REFRESH_MS), ("unchanged - refreshed every 30 min" if gap >= POST_REFRESH_MS else "unchanged")
