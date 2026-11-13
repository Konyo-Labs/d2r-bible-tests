# -*- coding: utf-8 -*-
"""v3849 (Elad) - THE d2jsp PRICE DB: every priced post the desk ever read, kept, aged and weighed.

A reading used to live only on its card: the next search started from nothing and an old post weighed as much as
today's. The DB keeps each post once (its forum link is its key; a post with no link is keyed by fg|day|roll), from
every PC (src), and prices an item from them:
  * AGE DECAY - a post weighs w * 0.5 ** (age_days / HALF_LIFE_DAYS); the parser's own w (0 = set aside as an outlier
    whose roll does not explain it) multiplies in, so an outlier never moves the price, but it stays on record.
  * WILSON - the confidence is the Wilson lower bound of "posts that agree with the price" (within AGREE of it) over
    the effective post count, so 3 agreeing posts say less than 30.
  * PERFECT TIER - posts that say perf/perfect are priced on their own and never lift the normal price.
  * FRESH REFRESH - stale(...) says when an item must be asked again: never read, read longer ago than REFRESH_DAYS,
    or its newest post is older than STALE_POST_DAYS. fresh_refresh asks those. While a gate or heart2 run holds
    the tree it says "paused while checks run" and does not fetch. Unknown is not free.
  * FLEET-READY - schema 1 is a plain JSON of items -> posts keyed by link with src and seenAt, and merge(a, b) is a
    commutative union (newest seenAt wins per post), so PCs can trade their DBs without losing or doubling a post.
No number is invented: an item with no weighted post prices as None (UNKNOWN), never 0.
"""
import json, math, os, re, tempfile, time

SCHEMA = 1
HALF_LIFE_DAYS = 30.0
REFRESH_DAYS = 3.0
STALE_POST_DAYS = 45.0
AGREE = 0.25          # a post agrees with the price when it is within 25 % of it
Z = 1.96


def empty():
    return {"schema": SCHEMA, "items": {}}


def key_of(item):
    return " ".join(str(item or "").lower().replace("'", "").split())


def _keys(item, key=None):
    """#96 (his 11-06: "price check ... joined logic to the database so this is a communicating and whole system") - the
    keys one item is held under: its CANONICAL key first (the forum words the desk searches it by - Harlequin Crest and
    Shako both search "shako", so GrokBot 6700580776 read the same 10 posts for both while the DB kept two entries,
    Shako 15 fg n 13 and Harlequin 40 fg n 5), then the asked name's own key (an entry written before the canonical key)."""
    ks = []
    for x in (key, item):
        k = key_of(x) if x else ""
        if k and k not in ks:
            ks.append(k)
    return ks


def _held(db, item, key=None):
    """-> (posts {post key: post} | None when no entry holds the item, readAt) - the union of every entry the item is held
    under, the newest seenAt winning per post. Read-only."""
    items = (db.get("items") or {}) if isinstance(db, dict) else {}
    out, read_at, found = {}, 0.0, False
    for k in _keys(item, key):
        it = items.get(k)
        if not isinstance(it, dict):
            continue
        found = True
        read_at = max(read_at, float(it.get("readAt") or 0))
        for pk, p in (it.get("posts") or {}).items():
            q = out.get(pk)
            if q is None or float(p.get("seenAt") or 0) > float(q.get("seenAt") or 0):
                out[pk] = p
    return (out if found else None), read_at


def _post_key(p):
    link = str(p.get("link") or "")
    if link.startswith("https://forums.d2jsp.org/"):
        return link
    return "%s|%s|%s" % (p.get("fg"), p.get("day"), json.dumps(p.get("roll") or []))


def _day_ts(day):
    try:
        return time.mktime(time.strptime(str(day)[:10], "%Y-%m-%d"))
    except (TypeError, ValueError):
        return None


#: v3881 (GrokBot's v3878 pass on his D2JSP database: its SOURCE column printed this PC's HOST NAME on every row) - a source
#: is said by the PC's Fleet NICKNAME. {host: nickname}, registered by the console from its own install identity; the DB is
#: this PC's own, so a row written before under its host name is said by the name too. Anything else is said as stored.
SOURCE_NAMES = {}


def source_name(src):
    s = str(src or "")
    return SOURCE_NAMES.get(s, s)


def ingest(db, reading, src, now=None, key=None):
    """Fold one public reading (d2jsp_chrome._public_fields) into db. -> number of posts new to the DB.

    #96 - `key` (or the reading's own `searched` words) is the item's canonical key; an entry the asked name was kept
    under before is folded into it (every post once, the newest seenAt wins) and removed, so one item is one entry."""
    now = time.time() if now is None else now
    if not isinstance(reading, dict) or reading.get("reason") != "read":
        return 0
    key = key or reading.get("searched")
    k = key_of(key or reading.get("item"))
    if not k:
        return 0
    items = db.setdefault("items", {})
    it = items.setdefault(k, {"item": str(reading.get("item")), "posts": {}, "readAt": 0})
    old_k = key_of(reading.get("item"))
    if old_k and old_k != k and isinstance(items.get(old_k), dict):
        old = items.pop(old_k)
        it["readAt"] = max(float(it.get("readAt") or 0), float(old.get("readAt") or 0))
        for pk, p in (old.get("posts") or {}).items():
            q = it["posts"].get(pk)
            if q is None or float(p.get("seenAt") or 0) > float(q.get("seenAt") or 0):
                it["posts"][pk] = p
    it["readAt"] = max(float(it.get("readAt") or 0), now)
    new = 0
    for p in reading.get("posts") or []:
        if not isinstance(p, dict):
            continue
        fg = price_of(p.get("fg"))                  # REG-3791 - a post without a price is not a post: skipped whole
        if fg is None or _day_ts(p.get("day")) is None:
            continue
        pk = _post_key(p)
        row = {"fg": fg, "day": str(p.get("day"))[:10], "link": p.get("link") or "", "w": float(p.get("w", 1)),
               "perfect": p.get("perfect") is True, "src": str(src or "?"), "seenAt": now,
               "author": author_of(p)}                # REG-3790 - every row says its seller; None = not read, never invented
        if p.get("out"):
            row["out"] = str(p["out"])[:80]
        old_row = it["posts"].get(pk)
        if old_row is None:
            new += 1
        elif row["author"] is None and author_of(old_row):
            row["author"] = author_of(old_row)       # REG-3790 - a re-read that did not see the seller keeps the known one
        it["posts"][pk] = row
    return new


def price_of(fg):
    """REG-3791 (#151, his rule: "a post without a price is not a post") - the post's price as a finite fg > 0, or None.
    ingest kept any float(fg) > 0: "inf", "nan" (nan <= 0 is False) and True (float(True) == 1.0) were stored as posts,
    though counts() never priced them. One test for both, so the DB never holds a row the price would not weigh."""
    if isinstance(fg, bool):
        return None
    try:
        v = float(fg)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) and v > 0 else None


def author_of(p):
    """REG-3790 - the seller a stored or read row names, folded to its written form, or None (unknown; never invented)."""
    who = p.get("author") if isinstance(p, dict) else None
    if isinstance(who, str) and who.strip():
        return who.strip()[:32]
    return None


def counts(p):
    """REG-3327 (#95 - his 11-06 ruling on the Advanced table: "i want the posts linked there anything without a post or a
    price is irrelevant"). A post weighs in a price only when it carries its forum link AND a price. -> bool
    MEASURED 11-07 on his DB: shako 14 posts, 9 with NO link (11-01 and 10-31, before links were kept; their key is
    fg|day|roll - no topic id to recover a link from). Those stay ON RECORD - nothing is deleted - and out of the price."""
    if not isinstance(p, dict) or not is_post_link(p.get("link")):
        return False
    return price_of(p.get("fg")) is not None   # REG-3354 - True / "inf" are not prices (one test with ingest, REG-3791)


def is_post_link(link):
    """REG-3354 (the Grok CLI on v3877) - a forum post's link: http(s) on d2jsp.org, with a host. -> bool. It was
    `startswith("http")`, so "httpnot-a-url" or a bare "http://" weighed as a linked post. MEASURED 11-07 on his DB: 31 of
    45 posts link to forums.d2jsp.org, the other 14 carry no link - nothing real is left out by this."""
    try:
        from urllib.parse import urlparse
        u = urlparse(str(link or "").strip())
        host = (u.hostname or "").lower()
    except Exception:
        return False
    return u.scheme in ("http", "https") and (host == "d2jsp.org" or host.endswith(".d2jsp.org"))


def _wmedian(pairs):
    pairs = sorted(pairs)
    tot = sum(w for _, w in pairs)
    acc = 0.0
    for v, w in pairs:
        acc += w
        if acc >= tot / 2.0:
            return v
    return None


def wilson_low(ok, n, z=Z):
    if n <= 0:
        return 0.0
    ph = ok / n
    d = 1 + z * z / n
    c = ph + z * z / (2 * n)
    m = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n))
    return max(0.0, (c - m) / d)


def _age_weight(p, now, share=None):
    """The same age and weight _tier uses. One formula, so a proof cannot drift from the price.
    REG-3792 - `share` is the row's part of its one vote (vote_shares); None reads the stored w as before."""
    t = _day_ts(p["day"])
    age = max(0.0, (now - t) / 86400.0)
    base = share if share is not None else max(0.0, min(1.0, p.get("w", 1)))
    w = base * 0.5 ** (age / HALF_LIFE_DAYS)
    return age, w


_TOPIC = re.compile(r"[?&;]t=(\d+)")


def topic_of(link):
    """The forum topic a post link opens (t=...), or None. Two posts in one topic are one listing."""
    m = _TOPIC.search(str(link or ""))
    return m.group(1) if m else None


def vote_shares(posts):
    """REG-3792 (#151 / #180, his rule: "the same seller is one post and one price"; a duplicate topic counts once) ->
    [share per post, in order]. MEASURED 11-11 on his console DB: Enigma perfect weighed topic 110566436 at w 0.5 beside its
    duplicate 110552180 at w 1.0 - 1.5 votes for one listing. The parser shares a vote only between rows on ONE page
    (d2jspOneVotePerPost), and a seller's two topics are rarely on one page. The vote is cast here, over every stored row
    of the tier: rows that share a seller (author), a topic (t=), or a topic declared the same listing (sameAs) are ONE
    group, and a group never weighs more than one vote - when its rows' stored w add up to more than 1 they are scaled to
    1, in proportion. A group at or under 1 keeps its stored w (a shop post's 1/28 row stays 1/28: its other rows were
    other prices). A row set aside (w 0) stays 0. Unknown sellers in different topics stay a group each - never guessed.
    Topics stay on record; nothing is deleted."""
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    base = []
    for i, p in enumerate(posts):
        try:
            w = float(p.get("w", 1))
        except (TypeError, ValueError):
            w = 0.0
        w = max(0.0, min(1.0, w)) if math.isfinite(w) else 0.0
        base.append(w)
        if w <= 0:
            continue
        me = "row:%d" % i
        find(me)
        who = author_of(p)
        if who:
            union(me, "seller:" + who.lower())
        t = topic_of(p.get("link"))
        if t:
            union(me, "topic:" + t)
        same = str(p.get("sameAs") or "").strip()
        if same.isdigit():
            union(me, "topic:" + same)
    total = {}
    for i, w in enumerate(base):
        if w > 0:
            r = find("row:%d" % i)
            total[r] = total.get(r, 0.0) + w
    out = []
    for i, w in enumerate(base):
        if w <= 0:
            out.append(0.0)
            continue
        t = total[find("row:%d" % i)]
        out.append(w / t if t > 1.0 else w)
    return out


def _tier(posts, now):
    pairs = []
    votes = 0.0
    for p, share in zip(posts, vote_shares(posts)):
        _age, w = _age_weight(p, now, share)
        if w > 0:
            pairs.append((p["fg"], w))
            votes += share
    if not pairs:
        return {"fg": None, "n": 0, "nEff": 0.0, "conf": 0.0, "votes": 0.0}
    mid = _wmedian(pairs)
    sw = sum(w for _, w in pairs)
    n_eff = sw * sw / sum(w * w for _, w in pairs)
    ok = sum(w for v, w in pairs if abs(v - mid) <= AGREE * mid) / sw * n_eff
    fg = int(mid) if mid == int(mid) else round(mid, 1)
    return {"fg": fg, "n": len(pairs), "nEff": round(n_eff, 2), "conf": round(wilson_low(ok, n_eff), 3),
            "votes": round(votes, 3)}


def price(db, item, now=None, key=None):
    """-> {"item", "normal": tier, "perfect": tier, "stale": bool, "why"}; a tier with fg None is UNKNOWN.
    #96 - `key` is the item's canonical key (_keys): every entry the item is held under prices together."""
    now = time.time() if now is None else now
    held, _ra = _held(db, item, key)
    posts = list((held or {}).values())
    stale, why = is_stale(db, item, now, key)
    priced = [p for p in posts if counts(p)]     # REG-3327; one vote per seller/topic is cast in _tier (vote_shares)
    return {"item": str(item), "normal": _tier([p for p in priced if not p.get("perfect")], now),
            "perfect": _tier([p for p in priced if p.get("perfect")], now), "stale": stale, "why": why,
            "leftOut": len(posts) - len(priced)}


def _band(fg, w, mid):
    """aside: it does not weigh. in: within AGREE of the median _tier used. out: it weighs and disagrees."""
    if w <= 0 or mid is None:
        return "aside"
    if abs(fg - mid) <= AGREE * mid:
        return "in"
    return "out"


def _median_of(posts, now):
    pairs = []
    for p, share in zip(posts, vote_shares(posts)):
        _age, w = _age_weight(p, now, share)
        if w > 0:
            pairs.append((p["fg"], w))
    return _wmedian(pairs) if pairs else None


def explain(db, item, now=None, key=None):
    """The posts price() weighed, with the age weight and the band. The fg and the Wilson stay on price().

    A missing post list is not an empty price. This does not invent a fg. An item with no row has no posts.
    """
    now = time.time() if now is None else now
    held, _ra = _held(db, item, key)
    every = list((held or {}).values())
    posts = [p for p in every if counts(p)]       # REG-3327 - the rows price() weighed; their votes below (vote_shares)
    normal = [p for p in posts if not p.get("perfect")]
    perfect = [p for p in posts if p.get("perfect")]
    mid_n = _median_of(normal, now)
    mid_p = _median_of(perfect, now)
    rows = []
    share_of = {}
    for tier in (normal, perfect):
        for p, share in zip(tier, vote_shares(tier)):
            share_of[id(p)] = share
    for p in posts:
        try:
            fg = float(p.get("fg"))
        except (TypeError, ValueError):
            continue
        age, w = _age_weight(p, now, share_of.get(id(p)))
        perfect_row = bool(p.get("perfect"))
        seen = p.get("seenAt")
        try:
            seen_n = float(seen) if seen is not None else None
        except (TypeError, ValueError):
            seen_n = None
        rows.append({
            "fg": fg,
            "day": str(p.get("day") or "")[:10],
            "link": p.get("link") or "",
            "w": p.get("w", 1),
            "perfect": perfect_row,
            "src": source_name(p.get("src")),
            "seenAt": seen_n,
            "out": str(p.get("out") or "")[:80],
            "author": author_of(p),                               # REG-3790 - None: the seller was not read
            "vote": round(share_of.get(id(p), 0.0), 3),           # REG-3792 - its part of one seller/topic vote
            "ageDays": round(age, 2),
            "decayed": round(w, 4),
            "tier": "perfect" if perfect_row else "normal",
            "band": _band(fg, w, mid_p if perfect_row else mid_n),
        })
    rows.sort(key=lambda r: (r["day"], str(r["link"]), r["fg"]), reverse=True)
    return {
        "posts": rows,
        "leftOut": len(every) - len(posts),                       # REG-3327 - kept on record, out of the price
        "halfLifeDays": HALF_LIFE_DAYS,
        "agree": AGREE,
        "refreshDays": REFRESH_DAYS,
        "stalePostDays": STALE_POST_DAYS,
        "z": Z,
    }


def view(db, now=None):
    """Every item in one DB, each with price() and explain(). An unreadable shape is unknown, never a zero price."""
    if not isinstance(db, dict) or db.get("schema") != SCHEMA:
        return {"reason": "unknown", "say": "the price DB would not read", "items": []}
    now = time.time() if now is None else now
    items = []
    for _k, it in sorted((db.get("items") or {}).items(), key=lambda kv: kv[0]):
        if not isinstance(it, dict):
            continue
        name = it.get("item")
        if not name:
            continue
        row = price(db, _k, now, key=_k)          # #96 - priced by the key it is stored under, said by its name
        row["item"] = str(name)
        row["proof"] = explain(db, _k, now, key=_k)
        items.append(row)
    return {"reason": "read", "items": items}


def is_stale(db, item, now=None, key=None):
    now = time.time() if now is None else now
    held, read_at = _held(db, item, key)
    if held is None:
        return True, "never read"
    if now - read_at > REFRESH_DAYS * 86400:
        return True, "read more than %g days ago" % REFRESH_DAYS
    days = [_day_ts(p["day"]) for p in held.values()]
    days = [d for d in days if d is not None]
    if not days or now - max(days) > STALE_POST_DAYS * 86400:
        return True, "no post in the last %g days" % STALE_POST_DAYS
    return False, "fresh"


def merge(a, b):
    """Commutative union of two DBs (fleet sync): every post once, the newest seenAt wins, readAt is the max."""
    out = empty()
    for db in (a, b):
        if not isinstance(db, dict) or db.get("schema") != SCHEMA:
            continue
        for k, it in (db.get("items") or {}).items():
            o = out["items"].setdefault(k, {"item": it.get("item", k), "posts": {}, "readAt": 0})
            o["readAt"] = max(float(o["readAt"] or 0), float(it.get("readAt") or 0))
            for pk, p in (it.get("posts") or {}).items():
                cur = o["posts"].get(pk)
                if cur is None or (p.get("seenAt", 0), json.dumps(p, sort_keys=True)) > (cur.get("seenAt", 0), json.dumps(cur, sort_keys=True)):
                    o["posts"][pk] = p
    return out


def import_backfill(db, other, now=None):
    """REG-3790 (#151) - fold a backfill's price file (prices-shard*.json, schema 1) into the stored DB. -> stats dict.

    IDEMPOTENT: a post already stored (same post key) is never added again and never re-stamped, so importing the same
    file twice changes nothing (stats "new" 0, the DB byte-identical). The one thing a later file may add to a stored
    row is its seller, when the stored row has none - a known seller is never replaced or cleared.
    Every row carries "author": the seller, or None when the page did not name one (the 11-11 snapshot: 1,832 rows, 3
    with an author) - None is kept as None, never filled from a guess.
    A post without a price (or without its forum link - counts()) is not a post: it is skipped whole and counted.
    readAt is the newer of the two, so an import never makes an item look fresher than its real last read."""
    stats = {"items": 0, "new": 0, "authorFilled": 0, "kept": 0, "skippedNoPrice": 0, "skippedNoLink": 0}
    if not isinstance(db, dict) or db.get("schema") != SCHEMA:
        raise ValueError("the stored price DB is not schema %d" % SCHEMA)
    if not isinstance(other, dict) or other.get("schema") != SCHEMA:
        raise ValueError("the backfill file is not schema %d" % SCHEMA)
    items = db.setdefault("items", {})
    for k0, src_it in sorted((other.get("items") or {}).items()):
        if not isinstance(src_it, dict):
            continue
        k = key_of(k0)
        if not k:
            continue
        it = items.get(k)
        touched = False
        for pk, p in sorted((src_it.get("posts") or {}).items()):
            if not isinstance(p, dict):
                continue
            fg = price_of(p.get("fg"))
            if fg is None or _day_ts(p.get("day")) is None:
                stats["skippedNoPrice"] += 1
                continue
            if not is_post_link(p.get("link")):
                stats["skippedNoLink"] += 1
                continue
            if it is None:
                it = items.setdefault(k, {"item": str(src_it.get("item") or k0), "posts": {}, "readAt": 0})
            cur = it["posts"].get(pk)
            if cur is not None:
                if cur.get("author") is None and "author" not in cur:
                    cur["author"] = None                  # an old row learns the field, with no seller invented
                    touched = True
                if author_of(cur) is None and author_of(p):
                    cur["author"] = author_of(p)
                    stats["authorFilled"] += 1
                    touched = True
                else:
                    stats["kept"] += 1
                continue
            row = {"fg": fg, "day": str(p.get("day"))[:10], "link": str(p.get("link")), "w": float(p.get("w", 1)),
                   "perfect": p.get("perfect") is True, "src": str(p.get("src") or "backfill"),
                   "seenAt": float(p.get("seenAt") or 0), "author": author_of(p)}
            if p.get("out"):
                row["out"] = str(p["out"])[:80]
            if str(p.get("sameAs") or "").strip().isdigit():
                row["sameAs"] = str(p["sameAs"]).strip()
            it["posts"][pk] = row
            stats["new"] += 1
            touched = True
        if it is not None:
            ra = max(float(it.get("readAt") or 0), float(src_it.get("readAt") or 0))
            if ra != float(it.get("readAt") or 0):
                it["readAt"] = ra
                touched = True
            if touched:
                stats["items"] += 1
    return stats


def mark_same_listing(db, item, topic, of_topic, key=None):
    """REG-3792 - declare that `topic` is the same listing as `of_topic` (a repost the forum shows, its seller unread).
    Both rows stay on record; vote_shares makes them one vote. -> number of rows marked. Nothing is deleted or guessed:
    the caller names both topic ids, and a topic the item does not hold marks nothing."""
    topic, of_topic = str(topic).strip(), str(of_topic).strip()
    if not (topic.isdigit() and of_topic.isdigit()) or topic == of_topic:
        return 0
    n = 0
    have_of = False
    for k in _keys(item, key):
        it = ((db or {}).get("items") or {}).get(k)
        for p in ((it or {}).get("posts") or {}).values():
            if topic_of(p.get("link")) == of_topic:
                have_of = True
    if not have_of:
        return 0
    for k in _keys(item, key):
        it = ((db or {}).get("items") or {}).get(k)
        for p in ((it or {}).get("posts") or {}).values():
            if topic_of(p.get("link")) == topic and p.get("sameAs") != of_topic:
                p["sameAs"] = of_topic
                n += 1
    return n


def load(path):
    """-> db, or None when the file exists and cannot be read (UNKNOWN - never silently an empty DB)."""
    if not os.path.exists(path):
        return empty()
    try:
        with open(path, encoding="utf-8") as f:
            db = json.load(f)
    except (OSError, ValueError):
        return None
    return db if isinstance(db, dict) and db.get("schema") == SCHEMA else None


def save(path, db):
    d = os.path.dirname(path) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".d2jsp_db.", dir=d)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, sort_keys=True)
    os.replace(tmp, path)


PAUSE = "paused while checks run"


def _held_for_key(key):
    """Ask whether one gate-lock key is held, then put this process's environment back."""
    import tree_busy
    old = os.environ.get("D2R_GATE_LOCK_KEY")
    os.environ["D2R_GATE_LOCK_KEY"] = key
    try:
        return tree_busy._gate_lock_held()
    finally:
        if old is None:
            os.environ.pop("D2R_GATE_LOCK_KEY", None)
        else:
            os.environ["D2R_GATE_LOCK_KEY"] = old


def checks_running(env=None):
    """True while heart2 or a gate holds the tree, False when it is free, None when it cannot be told.

    None is not free. A caller that passes its own env (not os.environ) and names D2R_GATE_LOCK_KEY is
    asked about that lock only, so a law can prove the pause without consulting a live pre-push. The
    console calls this with no env, so it sees the real lock and tree_busy.why().
    """
    env = os.environ if env is None else env
    lanes = env.get("HEART2_LANES")
    if lanes is not None and str(lanes) != "0":
        return True
    if env is not os.environ and env.get("D2R_GATE_LOCK_KEY"):
        try:
            held, _who = _held_for_key(env["D2R_GATE_LOCK_KEY"])
        except Exception:
            return None  # the gate lock could not be asked, so this is not free
        if held is None:
            return None
        if held:
            return True
        return False  # this lock is free, so the refresh may fetch
    try:
        import tree_busy
        sentence = tree_busy.why()
    except Exception:
        return None  # why() could not be asked, so this is not free
    if sentence:
        return True
    return False


#: #96 (his 11-06: "for price check it should be joined logic to the database so this is a communicating and whole system") -
#: a price check that finds its item STALE refreshes it at the backfill's pace: one forum search a minute, never a burst.
REFRESH_GAP_S = 60.0


def fresh_refresh(db, fetch, now=None, env=None, only=None, pace=None, gap_s=REFRESH_GAP_S):
    """Re-ask only stale items. While checks run, or when that cannot be told, say so and fetch nothing.

    #96 - THE PRICE CHECK IS ITS CALLER. `only` (keys or names) limits the pass to the item a price check reads, so a stale
    item is refreshed by the check that asks for it, never by a timer of its own. `pace` ({"at": seconds}, the caller's
    own memory of its last refresh search) holds the pass to one fetch per `gap_s`: inside the gap nothing is fetched and
    the answer says when the next read may go ("wait": seconds left). An item the DB does not hold is not refreshed here -
    a first read is the price check's own search."""
    busy = checks_running(env)
    if busy is None or busy:
        return {"say": PAUSE, "fetched": []}
    now = time.time() if now is None else now
    want = None
    if only is not None:
        want = set()
        for x in only:
            want.update(_keys(x))
    if pace is not None:
        try:
            last = float(pace.get("at") or 0)
        except (TypeError, ValueError, AttributeError):
            last = 0.0
        if not math.isfinite(last):
            last = 0.0
        left = gap_s - (now - last)
        if left > 0:
            stale_here = []
            for _k, it in ((db or {}).get("items") or {}).items():
                if want is not None and _k not in want:
                    continue
                if isinstance(it, dict) and it.get("item") and is_stale(db, _k, now, key=_k)[0]:
                    stale_here.append(_k)
            if stale_here:
                return {"say": "refresh due - the next forum read may go in %d s (one search a minute)" % math.ceil(left),
                        "fetched": [], "wait": math.ceil(left)}
    got = []
    for _k, it in ((db or {}).get("items") or {}).items():
        if want is not None and _k not in want:
            continue
        name = it.get("item") if isinstance(it, dict) else None
        if not name:
            continue
        stale, _why = is_stale(db, _k, now, key=_k)      # #96 - asked by the key it is stored under
        if not stale:
            continue
        if pace is not None:
            pace["at"] = now                             # #96 - stamped BEFORE the search: a read that raises still paces
        fetch(name)
        got.append(name)
        if pace is not None:
            break                                        # #96 - one search a pass when paced
    return {"say": None, "fetched": got}


#: #96 - a tier priced from fewer weighted posts than this is THIN: the price check says UNKNOWN beside its lean
THIN_POSTS = 3


def db_first(db, item, now=None, key=None):
    """#96 - what the DB already holds for an item, READ BEFORE the price check asks the forum. Read-only.

    -> {"verdict": "known" | "thin" | "unknown", "fg", "lean", "tier", "conf", "n", "nEff", "posts", "stale", "why", "say"}
    `fg` is a number only when known: an empty DB is UNKNOWN and a thin one (a tier under THIN_POSTS weighted posts) is
    UNKNOWN with its lean beside it - never a confident 0, never a confident 3-post number. `n` counts only priced posts
    (REG-3791: a post without a price is not a post)."""
    out = {"verdict": "unknown", "fg": None, "lean": None, "tier": None, "conf": None, "n": 0, "nEff": 0.0,
           "posts": 0, "stale": True, "why": "never read", "say": ""}
    if not isinstance(db, dict) or db.get("schema") != SCHEMA:
        out["why"] = "the price DB would not read"
        out["say"] = "Database: UNKNOWN - the price DB would not read."
        return out
    now = time.time() if now is None else now
    pr = price(db, item, now, key)
    out["stale"], out["why"] = pr["stale"], pr["why"]
    nrm, prf = pr["normal"], pr["perfect"]
    out["posts"] = int(nrm["n"]) + int(prf["n"])
    tier_name, tier = ("normal", nrm) if nrm["fg"] is not None else (("perfect", prf) if prf["fg"] is not None else (None, None))
    name = str(item)
    if tier is None:
        out["say"] = "Database: UNKNOWN - no priced post is kept for %s." % name
        return out
    out.update({"tier": tier_name, "conf": tier["conf"], "n": int(tier["n"]), "nEff": tier["nEff"]})
    if tier["n"] < THIN_POSTS:
        out["verdict"], out["lean"] = "thin", tier["fg"]
        out["say"] = ("Database: UNKNOWN - only %d priced %s for %s (leans %s fg, Wilson %s)."
                      % (tier["n"], "post" if tier["n"] == 1 else "posts", name, tier["fg"], tier["conf"]))
        return out
    out["verdict"], out["fg"] = "known", tier["fg"]
    out["say"] = ("Database: %s fg (%s), Wilson lower bound %s, from %d priced posts%s."
                  % (tier["fg"], tier_name, tier["conf"], tier["n"], "" if not pr["stale"] else " - due a refresh"))
    return out
