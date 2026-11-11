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
from html.parser import HTMLParser

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


class _RowLinks(HTMLParser):
    """Each <tr> of a page with the topic ids and the user.php names its whole subtree links to."""

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.stack, self.rows, self._user = [], [], None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.stack.append({"topics": set(), "names": set(), "own": set()})
            return
        if tag != "a" or not self.stack:
            return
        href = dict(attrs).get("href") or ""
        m = re.search(r"topic\.php\?(?:[^\"'>]*?[&;])?t=(\d+)", href.replace("&amp;", "&"))
        if m:
            self.stack[-1]["topics"].add(m.group(1))
            self.stack[-1]["own"].add(m.group(1))
        elif "user.php" in href:
            self._user = []

    def handle_data(self, data):
        if self._user is not None:
            self._user.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._user is not None:
            name = " ".join("".join(self._user).split())
            self._user = None
            if name and len(name) <= 32 and self.stack:
                self.stack[-1]["names"].add(name)
            return
        if tag == "tr" and self.stack:
            row = self.stack.pop()
            self.rows.append(row)
            if self.stack:
                self.stack[-1]["topics"] |= row["topics"]
                self.stack[-1]["names"] |= row["names"]


def topic_authors(html):
    """REG-3793 (#151) - {topic id: seller} read off a signed-in results page. MEASURED 11-11 on the running backfill: 158
    items, 1,832 priced rows, 3 with an author - the log said authors=- on every page, because the parser takes a seller
    only from a line that neither names the item nor carries a price (v3894), and a results row names both.

    The rule is the page's own structure, never a guess: a topic belongs to the smallest table row (<tr>) that links to
    it, and that row names its seller when it links to exactly ONE topic and exactly ONE user.php name. A row with two
    names (the starter and a last poster), two topics, or none says nothing; a topic two rows give different sellers
    says nothing. Unknown stays unknown. -> dict (empty when the page has no such rows)"""
    p = _RowLinks()
    try:
        p.feed(str(html or ""))
        p.close()
    except Exception:
        return {}
    while p.stack:                       # an unclosed row is still a row
        p.handle_endtag("tr")
    out, bad = {}, set()
    for row in p.rows:
        for t in row["own"]:
            if len(row["topics"]) != 1:
                continue                         # a row of many topics names no one's seller
            if len(row["names"]) > 1:
                bad.add(t)                       # its own row names two people: which is the seller is not known
                continue
            if not row["names"]:
                continue
            name = next(iter(row["names"]))
            if t in out and out[t].lower() != name.lower():
                bad.add(t)
            out.setdefault(t, name)
    for t in bad:
        out.pop(t, None)
    return out


def fill_authors(reading, html):
    """REG-3793 - give each read post with no seller the seller its topic's row names. -> number of posts filled.
    A seller the parser already read is never replaced."""
    if not isinstance(reading, dict):
        return 0
    who = topic_authors(html)
    if not who:
        return 0
    n = 0
    for post in reading.get("posts") or []:
        if not isinstance(post, dict) or P.author_of(post):
            continue
        name = who.get(P.topic_of(post.get("link")) or "")
        if name:
            post["author"] = name
            n += 1
    return n


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
        since = str(st.get("since") or "")
        days = [str(p.get("day") or "")[:10] for p in (reading.get("posts") or []) if isinstance(p, dict) and p.get("day")]
        if since and nxt is not None and days and all(d < since for d in days):
            # REG-3794 - a monthly refresh pages back only to its last read
            st["done"] = True
            st["why"] = "caught up to %s" % since
            st.pop("since", None)
            rec["cursor"] = (cursor + 1) % len(queue)
            out["done"] = True
            out["why"] = "asked %s at o=%d - caught up to %s, folded %d" % (picked, offset, since, added)
        elif nxt is None or (isinstance(nxt, int) and nxt <= offset):
            st["done"] = True
            st["why"] = "last page"
            st.pop("since", None)
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


#: REG-3794 (#151, his 11-08 ruling: "a ~2-year backfill then a monthly refresh") - an item is asked again once a month
MONTHLY_DAYS = 30.0


def queue_monthly_refresh(progress_path, db_path, now=None, days=MONTHLY_DAYS):
    """REG-3794 - re-open ONLY the stale items for the same paced runner. -> {"queued": [names], "why"}

    An item is stale when its backfill finished (done) and the price file last read it more than `days` ago, or never
    did. Each stale item restarts at o=0 and pages back only until a page is wholly older than the day before its last read
    ("since" - those posts are already held), then it is done again. A fresh item, and an item still mid-backfill, are left alone.
    The pace is run_once's own (lastAskAt in the same progress file): 1 search a minute, whatever is queued. Asks nothing
    itself; never raises on a bad row (that row is left as it is)."""
    now = time.time() if now is None else now
    out = {"queued": [], "why": ""}
    rec = progress_load(progress_path)
    if rec is None:
        out["why"] = "the progress file would not read - nothing is queued (UNKNOWN)"
        return out
    db = P.load(db_path)
    if db is None:
        out["why"] = "the price file would not read - nothing is queued (UNKNOWN)"
        return out
    for name in list(rec.get("queue") or []):
        st = _state_of(rec, name)
        if not st.get("done"):
            continue
        held, read_at = P._held(db, name)
        try:
            read_at = float(read_at or 0)
        except (TypeError, ValueError):
            read_at = 0.0
        if held is not None and read_at > 0 and now - read_at <= days * 86400:
            continue
        st["done"] = False
        st["offset"] = 0
        st["why"] = "monthly refresh"
        if held is not None and read_at > 0:
            # what was posted after the last read: a day of margin, so a post made that day is read again, not missed
            st["since"] = time.strftime("%Y-%m-%d", time.gmtime(read_at - 86400))
        else:
            st.pop("since", None)                # never read: the whole window, as the backfill does
        out["queued"].append(name)
    progress_save(progress_path, rec)
    out["why"] = "%d stale of %d queued" % (len(out["queued"]), len(rec.get("queue") or []))
    return out
