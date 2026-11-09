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
import json, math, os, tempfile, time

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
        try:
            fg = float(p.get("fg"))
        except (TypeError, ValueError):
            continue
        if fg <= 0 or _day_ts(p.get("day")) is None:
            continue
        pk = _post_key(p)
        row = {"fg": fg, "day": str(p.get("day"))[:10], "link": p.get("link") or "", "w": float(p.get("w", 1)),
               "perfect": p.get("perfect") is True, "src": str(src or "?"), "seenAt": now}
        if p.get("out"):
            row["out"] = str(p["out"])[:80]
        who = p.get("author")
        if isinstance(who, str) and who.strip():
            row["author"] = who.strip()[:32]
        if pk not in it["posts"]:
            new += 1
        it["posts"][pk] = row
    return new


def counts(p):
    """REG-3327 (#95 - his 11-06 ruling on the Advanced table: "i want the posts linked there anything without a post or a
    price is irrelevant"). A post weighs in a price only when it carries its forum link AND a price. -> bool
    MEASURED 11-07 on his DB: shako 14 posts, 9 with NO link (11-01 and 10-31, before links were kept; their key is
    fg|day|roll - no topic id to recover a link from). Those stay ON RECORD - nothing is deleted - and out of the price."""
    if not isinstance(p, dict) or not is_post_link(p.get("link")):
        return False
    fg = p.get("fg")
    if isinstance(fg, bool):
        return False                       # REG-3354 - float(True) is 1.0: a flag is not a price
    try:
        v = float(fg)
    except (TypeError, ValueError):
        return False
    return math.isfinite(v) and v > 0      # REG-3354 - "inf" parses as a price and would own every median


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


def _age_weight(p, now):
    """The same age and weight _tier uses. One formula, so a proof cannot drift from the price."""
    t = _day_ts(p["day"])
    age = max(0.0, (now - t) / 86400.0)
    w = max(0.0, min(1.0, p.get("w", 1))) * 0.5 ** (age / HALF_LIFE_DAYS)
    return age, w


def _tier(posts, now):
    pairs = []
    for p in posts:
        _age, w = _age_weight(p, now)
        if w > 0:
            pairs.append((p["fg"], w))
    if not pairs:
        return {"fg": None, "n": 0, "nEff": 0.0, "conf": 0.0}
    mid = _wmedian(pairs)
    sw = sum(w for _, w in pairs)
    n_eff = sw * sw / sum(w * w for _, w in pairs)
    ok = sum(w for v, w in pairs if abs(v - mid) <= AGREE * mid) / sw * n_eff
    fg = int(mid) if mid == int(mid) else round(mid, 1)
    return {"fg": fg, "n": len(pairs), "nEff": round(n_eff, 2), "conf": round(wilson_low(ok, n_eff), 3)}


def price(db, item, now=None, key=None):
    """-> {"item", "normal": tier, "perfect": tier, "stale": bool, "why"}; a tier with fg None is UNKNOWN.
    #96 - `key` is the item's canonical key (_keys): every entry the item is held under prices together."""
    now = time.time() if now is None else now
    held, _ra = _held(db, item, key)
    posts = list((held or {}).values())
    stale, why = is_stale(db, item, now, key)
    priced = [p for p in posts if counts(p)]                     # REG-3327 - a linked post with a price, or nothing
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
    for p in posts:
        _age, w = _age_weight(p, now)
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
    posts = [p for p in every if counts(p)]                       # REG-3327 - the rows the price weighed, no other
    normal = [p for p in posts if not p.get("perfect")]
    perfect = [p for p in posts if p.get("perfect")]
    mid_n = _median_of(normal, now)
    mid_p = _median_of(perfect, now)
    rows = []
    for p in posts:
        try:
            fg = float(p.get("fg"))
        except (TypeError, ValueError):
            continue
        age, w = _age_weight(p, now)
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


def fresh_refresh(db, fetch, now=None, env=None):
    """Re-ask only stale items. While checks run, or when that cannot be told, say so and fetch nothing."""
    busy = checks_running(env)
    if busy is None or busy:
        return {"say": PAUSE, "fetched": []}
    now = time.time() if now is None else now
    got = []
    for _k, it in ((db or {}).get("items") or {}).items():
        name = it.get("item") if isinstance(it, dict) else None
        if not name:
            continue
        stale, _why = is_stale(db, _k, now, key=_k)      # #96 - asked by the key it is stored under
        if not stale:
            continue
        fetch(name)
        got.append(name)
    return {"say": None, "fetched": got}
