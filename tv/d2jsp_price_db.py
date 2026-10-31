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


def ingest(db, reading, src, now=None):
    """Fold one public reading (d2jsp_chrome._public_fields) into db. -> number of posts new to the DB."""
    now = time.time() if now is None else now
    if not isinstance(reading, dict) or reading.get("reason") != "read":
        return 0
    k = key_of(reading.get("item"))
    if not k:
        return 0
    it = db.setdefault("items", {}).setdefault(k, {"item": str(reading.get("item")), "posts": {}, "readAt": 0})
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
        if pk not in it["posts"]:
            new += 1
        it["posts"][pk] = row
    return new


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


def _tier(posts, now):
    pairs = []
    for p in posts:
        t = _day_ts(p["day"])
        age = max(0.0, (now - t) / 86400.0)
        w = max(0.0, min(1.0, p.get("w", 1))) * 0.5 ** (age / HALF_LIFE_DAYS)
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


def price(db, item, now=None):
    """-> {"item", "normal": tier, "perfect": tier, "stale": bool, "why"}; a tier with fg None is UNKNOWN."""
    now = time.time() if now is None else now
    it = (db.get("items") or {}).get(key_of(item))
    posts = list((it or {}).get("posts", {}).values())
    stale, why = is_stale(db, item, now)
    return {"item": str(item), "normal": _tier([p for p in posts if not p.get("perfect")], now),
            "perfect": _tier([p for p in posts if p.get("perfect")], now), "stale": stale, "why": why}


def is_stale(db, item, now=None):
    now = time.time() if now is None else now
    it = (db.get("items") or {}).get(key_of(item))
    if not it:
        return True, "never read"
    if now - float(it.get("readAt") or 0) > REFRESH_DAYS * 86400:
        return True, "read more than %g days ago" % REFRESH_DAYS
    days = [_day_ts(p["day"]) for p in it["posts"].values()]
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
    for it in ((db or {}).get("items") or {}).values():
        name = it.get("item") if isinstance(it, dict) else None
        if not name:
            continue
        stale, _why = is_stale(db, name, now)
        if not stale:
            continue
        fetch(name)
        got.append(name)
    return {"say": None, "fetched": got}
