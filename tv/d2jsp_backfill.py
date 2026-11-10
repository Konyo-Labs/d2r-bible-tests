# -*- coding: utf-8 -*-
"""#151 - A RESUMABLE, READ-ONLY d2jsp PRICE BACKFILL. TESTED OFFLINE. NEVER STARTS A LIVE SCRAPE.

His rulings (11-08 / 11-09): signed-in on HIS Mac's console, forum 268 (SC non-ladder), 1 search/min,
a ~2-year backfill then a monthly refresh; only priced posts, with links; the same seller is one post
and one price; never post or trade.

This module is the runner and the pager. It does not fetch the forum unless a `fetch` callback is
handed in. Importing it, constructing progress, or running its tests never opens a network socket
to d2jsp. The live 1-search/min lane is started only by the console after Elad says so.

Progress (JSON, beside the price DB) remembers the item, the next &o= offset, pages read and how
many posts were folded, so a killed run picks up where it left off.
"""
import json
import os
import re
import tempfile
import time

import d2jsp_price_db as P

SCHEMA = 1
SEARCH_GAP_S = 60.0
CUTOFF_YEARS = 2
FORUM = 268

#: a "Next" paging link on a signed-in results page (REG-3491 kept pages leave &o= intact)
_NEXT = re.compile(
    r"<a\s[^>]*href=[\"'][^\"']*search\.php[^\"']*[?&](?:amp;)?o=(\d+)[^\"']*[\"'][^>]*>\s*(?:Next|&#62;|&gt;|&raquo;)",
    re.I,
)


def pager_offset(html):
    """The next page's &o= from a results page, or None (last page, or no pager)."""
    m = _NEXT.search(str(html or ""))
    if not m:
        return None
    try:
        return int(m.group(1))
    except (TypeError, ValueError):
        return None


def empty_progress(items=None):
    queue = []
    for n in items or []:
        s = str(n or "").strip()
        if s and s not in queue:
            queue.append(s)
    return {"schema": SCHEMA, "lastAskAt": 0, "cursor": 0, "queue": queue, "items": {}}


def progress_load(path):
    """-> progress dict, or None when the file exists and cannot be read (UNKNOWN, never an empty reset)."""
    if not path or not os.path.exists(path):
        return empty_progress()
    try:
        with open(path, encoding="utf-8") as fh:
            rec = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(rec, dict) or rec.get("schema") != SCHEMA:
        return None
    rec.setdefault("items", {})
    rec.setdefault("queue", [])
    rec.setdefault("cursor", 0)
    rec.setdefault("lastAskAt", 0)
    return rec


def progress_save(path, rec):
    d = os.path.dirname(path) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".d2jsp_backfill.", dir=d)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, ensure_ascii=False, sort_keys=True)
    os.replace(tmp, path)


def _state_of(rec, name):
    k = P.key_of(name)
    items = rec.setdefault("items", {})
    st = items.get(k)
    if not isinstance(st, dict):
        st = {"item": name, "offset": 0, "pages": 0, "folded": 0, "done": False, "why": ""}
        items[k] = st
    return st


def run_once(progress_path, db_path, fetch=None, parse=None, fold=None, now=None,
             items=None, min_gap_s=SEARCH_GAP_S, src="backfill"):
    """One search. `fetch(item, offset) -> html | None`. No fetch => nothing is asked (no live scrape).

    `parse(html, item, read_at) -> reading` (a public quote dict). `fold(reading) -> n` new posts;
    when fold is omitted the reading is ingested into `db_path` through d2jsp_price_db.ingest.
    Never raises.
    """
    out = {"worked": False, "asked": None, "offset": None, "folded": 0, "done": False, "why": ""}
    try:
        if fetch is None:
            out["why"] = "no fetch handed in - nothing is asked (the live scrape is not started from here)"
            return out
        now = time.time() if now is None else now
        rec = progress_load(progress_path)
        if rec is None:
            out["why"] = "the progress file would not read - nothing is asked over it (UNKNOWN)"
            return out
        if items:
            for n in items:
                s = str(n or "").strip()
                if s and s not in rec["queue"]:
                    rec["queue"].append(s)
        queue = list(rec.get("queue") or [])
        if not queue:
            out["why"] = "no items queued - nothing is asked"
            return out
        last = rec.get("lastAskAt") or 0
        try:
            last = float(last)
        except (TypeError, ValueError):
            last = 0.0
        gap = float(min_gap_s)
        if last and now - last < gap:
            out["why"] = "the 1 search/min pace has %ds left" % int(gap - (now - last))
            return out
        try:
            cursor = int(rec.get("cursor") or 0) % len(queue)
        except (TypeError, ValueError, ZeroDivisionError):
            out["why"] = "the progress cursor would not read - nothing is asked (UNKNOWN)"
            return out
        picked = None
        for i in range(len(queue)):
            idx = (cursor + i) % len(queue)
            name = queue[idx]
            st = _state_of(rec, name)
            if not st.get("done"):
                picked, cursor = name, idx
                break
        if picked is None:
            out["why"] = "every queued item is done"
            rec["cursor"] = 0
            progress_save(progress_path, rec)
            return out
        st = _state_of(rec, picked)
        try:
            offset = int(st.get("offset") or 0)
        except (TypeError, ValueError):
            out["why"] = "the saved offset would not read - nothing is asked (UNKNOWN)"
            return out
        html = fetch(picked, offset)
        rec["lastAskAt"] = now
        rec["cursor"] = cursor
        out["worked"] = True
        out["asked"] = picked
        out["offset"] = offset
        if html is None:
            out["why"] = "fetch returned nothing for %s at o=%d - will retry" % (picked, offset)
            st["why"] = "empty fetch"
            progress_save(progress_path, rec)
            return out
        if parse is None:
            reading = {"reason": "read", "item": picked, "posts": []}
        else:
            reading = parse(html, picked, now)
        if not isinstance(reading, dict):
            reading = {"reason": "unread", "item": picked, "posts": []}
        reading.setdefault("item", picked)
        if reading.get("reason") == "need-login":
            out["why"] = "asked %s - sign-in is off, so the backfill waits (nothing posted)" % picked
            st["why"] = "need-login"
            progress_save(progress_path, rec)
            return out
        added = 0
        if fold is not None:
            added = fold(reading) or 0
        else:
            db = P.load(db_path)
            if db is None:
                out["why"] = "the price database would not read - nothing is folded over it (UNKNOWN)"
                progress_save(progress_path, rec)
                return out
            added = P.ingest(db, reading, src, now=now)
            P.save(db_path, db)
        try:
            added = int(added or 0)
        except (TypeError, ValueError):
            added = 0
        st["pages"] = int(st.get("pages") or 0) + 1
        st["folded"] = int(st.get("folded") or 0) + added
        out["folded"] = added
        nxt = pager_offset(html)
        if nxt is None or (isinstance(nxt, int) and nxt <= offset):
            st["done"] = True
            st["why"] = "last page"
            rec["cursor"] = (cursor + 1) % len(queue)
            out["done"] = True
            out["why"] = "asked %s at o=%d - last page, folded %d" % (picked, offset, added)
        else:
            st["offset"] = int(nxt)
            st["why"] = "next o=%d" % int(nxt)
            out["why"] = "asked %s at o=%d - next o=%d, folded %d" % (picked, offset, int(nxt), added)
        progress_save(progress_path, rec)
        return out
    except Exception as e:
        out["why"] = "the pass raised %s - nothing more was asked" % type(e).__name__
        return out
