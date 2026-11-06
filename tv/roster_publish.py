#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fleet 3.0 phase 1 — what this PC publishes, and when.

The presence beacon stays on /api/console and never carries an item name.
This module builds a separate body for POST /api/roster. The KV key is the
owner label, not an install id, a hostname, or a path.

A section that was not read is left out. An empty list is not a stand-in
for that. Pictures and frame bytes are dropped before the post. The post
itself is change-only, at most once an hour, plus one at boot. The boot post
goes even when nothing changed here (#95): the server skips the write when
its stored hash matches, and overwrites a row someone else wrote in this PC's
name. The server, not this file, enforces the daily cap.

#95 - every row the server returns carries intentVerified: true (signed by the
owner's registered key), false (published without a signature that key made),
or no field at all (published before signing), which every view here shows as
UNKNOWN and never as either answer. tv/roster_sign.py signs; this file carries
what the server said to every view, the panel's payload and the doctor.
"""

import html
import json
import os
import re

OWNERS = (
    "Konyo · Mac",
    "Konyo · ALT",
    "Konyo · GrokBot",
    "Dean",
    "Wife PC",
)
SECTIONS = ("characters", "vault", "stash", "owned", "chronicle", "reels")
HOUR_MS = 3600 * 1000
DAY_CAP = 25

_ROW_KEYS = ("name", "cls", "level", "title", "tier", "mule", "locker",
             "looks", "evidence", "date", "station", "provenance", "lane")
_INT_KEYS = ("level", "looks", "date", "x", "y", "w", "h")
_BUILD_SLOTS = ("head", "neck", "tors", "rarm", "larm", "rrin", "lrin", "belt", "feet", "glov")


def budget():
    """The write budget this publish is allowed to add. v3862 (Workers Paid, confirmed 2026-11-05): presence is
    4,896 a day for six PCs (functions/api/console.js REFRESH_S 220), and the ceiling is the fleet's own 10,000 a
    day - a third of the ~32,000 the plan includes (roster.js KV_WRITES). On the free plan: 768 and 1,000."""
    presence, pcs, per = 4896, 6, DAY_CAP
    return {"presence": presence, "pcs": pcs, "perPc": per, "roster": pcs * per,
            "ceiling": 10000, "together": presence + pcs * per}


def owner_of(name, platform=None):
    """The roster label for a name this PC already claims, or None.

    A name that is already one of the five labels is that label on every
    platform. The short name Konyo on a mac is the label Konyo · Mac.
    Windows stays unlabeled, and so does a mac named Grok: those machines
    are not this one, and a guess would publish them under the wrong key.
    A name is read trimmed, as the console page's _fleetRosterOwner reads a
    fleet row, so the two readers of one row never name different owners.
    """
    if isinstance(name, str):
        name = name.strip()
    if name in OWNERS:
        return name
    if name == "Konyo" and platform == "mac":
        return "Konyo · Mac"
    return None


def roster_key(owner):
    if owner not in OWNERS:
        return None
    return "roster:" + owner


def _dirty(v):
    if isinstance(v, str):
        low = v.lower()
        if "data:image" in low or "base64," in low:
            return True
        if any(ext in low for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp")):
            return True
        if len(v) > 400:
            return True
        return False
    if isinstance(v, dict):
        return any(_dirty(k) or _dirty(x) for k, x in v.items())
    if isinstance(v, list):
        return any(_dirty(x) for x in v)
    return False


def _short_text(v, n=80):
    if not isinstance(v, str):
        return None
    s = " ".join(v.split())
    if not s or len(s) > n or _dirty(s):
        return None
    return s


def _short_id(v):
    if not isinstance(v, str):
        return None
    s = v.strip()
    if not s or len(s) > 64 or _dirty(s):
        return None
    if any(c in s for c in "/\\."):
        return None
    return s


def _clean_row(row, allow=None):
    if not isinstance(row, dict):
        return None
    keys = allow or _ROW_KEYS
    out = {}
    for k in keys:
        if k not in row or _dirty(k):
            continue
        v = row[k]
        if k in _INT_KEYS:
            if isinstance(v, bool) or not isinstance(v, int) or v < 0:
                continue
            out[k] = v
            continue
        if k == "evidence":
            ids = []
            if isinstance(v, list):
                for item in v:
                    sid = _short_id(item)
                    if sid:
                        ids.append(sid)
            if ids:
                out[k] = ids[:8]
            continue
        text = _short_text(v)
        if text:
            out[k] = text
    return out or None


def section_of(raw, now_ms=None):
    """One section, or None when it was not read.

    A bare list, including [], is not a read. counts 0 is a read that found
    nothing, and it carries no rows key.
    """
    if not isinstance(raw, dict) or raw.get("read") is not True:
        return None
    as_of = raw.get("asOf")
    if isinstance(as_of, bool) or not isinstance(as_of, int) or as_of <= 0:
        as_of = now_ms if isinstance(now_ms, int) and not isinstance(now_ms, bool) else None
    if isinstance(as_of, bool) or not isinstance(as_of, int) or as_of <= 0:
        return None
    out = {"asOf": as_of}
    counts = raw.get("counts")
    if isinstance(counts, bool):
        counts = None
    if isinstance(counts, int) and counts >= 0:
        out["counts"] = counts
    elif isinstance(counts, dict):
        cleaned = {}
        for k, v in counts.items():
            if _dirty(k):
                continue
            if isinstance(v, dict):
                pair = {}
                have, total = v.get("have"), v.get("total")
                if isinstance(have, int) and not isinstance(have, bool) and have >= 0:
                    pair["have"] = have
                if isinstance(total, int) and not isinstance(total, bool) and total > 0:
                    pair["total"] = total
                if pair:
                    cleaned[str(k)[:40]] = pair
            elif isinstance(v, int) and not isinstance(v, bool) and v >= 0:
                cleaned[str(k)[:40]] = v
        if cleaned:
            out["counts"] = cleaned
    rows = raw.get("rows")
    allow = raw.get("allow")
    if isinstance(rows, list) and rows:
        kept = []
        for row in rows:
            if allow == ("build",):
                clean = clean_build(row)
            else:
                clean = _clean_row(row, allow if isinstance(allow, tuple) else None)
            if clean:
                kept.append(clean)
        if kept:
            out["rows"] = kept
    if "counts" not in out and "rows" not in out:
        return None
    # #200 (REG-2745) - when the rows were read, if that differs from asOf; never a hash input (for_hash below)
    rows_as_of = raw.get("rowsAsOf")
    if "rows" in out and isinstance(rows_as_of, int) and not isinstance(rows_as_of, bool) and rows_as_of > 0:
        out["rowsAsOf"] = rows_as_of
    sw = sweep_of(raw.get("sweep"))
    if sw is not None:
        out["sweep"] = sw
    return out


def sweep_of(sw):
    """v3866 (his call 2026-11-06: "show both numbers on the fleet row") - what the SWEEP's evidence ledger grounds
    (vault_accum.json: rows the AI sweep saw on his reels, REG-2817's "evidence, not truth"), carried beside the board's
    own records: {owned, asOf} - a count and that store's OWN age - or None when either will not read."""
    if not isinstance(sw, dict):
        return None
    n, at = sw.get("owned"), sw.get("asOf")
    if isinstance(n, bool) or not isinstance(n, int) or n < 0 or isinstance(at, bool) or not isinstance(at, int) or at <= 0:
        return None
    return {"owned": n, "asOf": at}


def sections_from(reads, now_ms=None):
    reads = reads if isinstance(reads, dict) else {}
    out = {}
    for name in SECTIONS:
        sec = section_of(reads.get(name), now_ms)
        if sec is not None:
            out[name] = sec
    return out


def characters_read(present, ledger, learned_rows, now_ms):
    if present is not True or not isinstance(ledger, dict) or learned_rows is None:
        return None
    chars = ledger.get("chars")
    if not isinstance(chars, dict):
        return None
    return {"read": True, "asOf": now_ms, "counts": len(chars), "rows": learned_rows,
            "allow": ("name", "cls", "level", "title")}


def _fold_name(name):
    """char_select._fold, the key a character name is matched on (the D2R font draws O as ⊕; readers vary in case)."""
    s = str(name or "").replace("\u2295", "O").replace("\u00d8", "O").replace("\u25ce", "O")
    return re.sub(r"[^a-z0-9]", "", s.lower())


def with_save_names(section, saves, now_ms):
    """#251 (REG-2929) - the characters section carries THIS PC's save names, spelled as its save folder spells them,
    and never an account id. -> section | None

    `saves` is control_app.saves_answer() (tv/d2s_read.saves). A learned row whose name folds to a save name takes the
    save's spelling; a save name no row holds joins as a row with its name only (class and level UNKNOWN, so absent).
    Saves that did not answer, or name nobody, leave the section as it was. A PC whose reels learned nothing gets a
    section from its saves alone. A builds book's section carries builds, not characters, and is left as it is."""
    if not (isinstance(saves, dict) and saves.get("ok") is True and isinstance(saves.get("chars"), list)):
        return section
    names = []
    for r in saves["chars"]:
        n = r.get("name") if isinstance(r, dict) else None
        if isinstance(n, str) and n.strip() and n not in names:
            names.append(n)
    if not names:
        return section
    allow = ("name", "cls", "level", "title")
    if section is None:
        if isinstance(now_ms, bool) or not isinstance(now_ms, int) or now_ms <= 0:
            return None
        return {"read": True, "asOf": now_ms, "counts": len(names), "rows": [{"name": n} for n in names], "allow": allow}
    if not isinstance(section, dict) or section.get("allow") == ("build",):
        return section
    rows = [dict(r) if isinstance(r, dict) else r for r in (section.get("rows") or [])]
    by = {}
    for r in rows:
        if isinstance(r, dict) and r.get("name"):
            by.setdefault(_fold_name(r["name"]), r)
    added = 0
    for n in names:
        hit = by.get(_fold_name(n))
        if hit is not None:
            hit["name"] = n
            continue
        row = {"name": n}
        rows.append(row)
        by[_fold_name(n)] = row
        added += 1
    out = dict(section)
    out["rows"] = rows
    c = out.get("counts")
    if isinstance(c, int) and not isinstance(c, bool):
        out["counts"] = c + added
    return out


def vault_read(state, rows, as_of, sweep=None):
    if state != "ok" or rows is None or not isinstance(rows, list):
        return None
    if isinstance(as_of, bool) or not isinstance(as_of, int) or as_of <= 0:
        return None
    out = {"read": True, "asOf": as_of, "counts": len(rows), "rows": rows,
           "allow": ("name", "tier", "mule", "locker", "looks", "evidence")}
    sw = sweep_of(sweep)
    if sw is not None:
        out["sweep"] = sw          # v3866 - the sweep ledger's count rides beside the board's records, its own age with it
    return out


def stash_read(rows, as_of):
    """A stash list this PC actually read. None means it was not read."""
    if rows is None or not isinstance(rows, list):
        return None
    if isinstance(as_of, bool) or not isinstance(as_of, int) or as_of <= 0:
        return None
    return {"read": True, "asOf": as_of, "counts": len(rows), "rows": rows,
            "allow": ("name", "id", "mule", "x", "y", "w", "h")}


def _gear_item(raw):
    """One worn or stored item: a name, and the id the board renderer already uses."""
    if not isinstance(raw, dict):
        return None
    name = _short_text(raw.get("name"), 80)
    if not name:
        return None
    out = {"name": name}
    ident = raw.get("id")
    if isinstance(ident, str):
        ident = _short_text(ident, 80)
        if ident:
            out["id"] = ident
    for key in ("x", "y", "w", "h"):
        num = raw.get(key)
        if isinstance(num, bool) or not isinstance(num, int) or num < 0 or num > 20:
            continue
        out[key] = num
    return out


def clean_build(raw):
    """One character build, small enough to publish and shaped for the board renderer."""
    if not isinstance(raw, dict):
        return None
    name = _short_text(raw.get("name"), 80)
    if not name:
        return None
    out = {"name": name}
    cls = _short_text(raw.get("cls"), 40)
    if cls:
        out["cls"] = cls
    level = raw.get("level")
    if isinstance(level, int) and not isinstance(level, bool) and 1 <= level <= 99:
        out["level"] = level
    sets = []
    for src in (raw.get("sets") or [])[:4]:
        if not isinstance(src, dict):
            continue
        slots = {}
        for slot, item in (src.get("slots") or {}).items():
            if slot not in _BUILD_SLOTS:
                continue
            clean = _gear_item(item)
            if clean:
                slots[slot] = {k: clean[k] for k in ("id", "name") if k in clean}
        inv = []
        for item in (src.get("inv") or [])[:40]:
            clean = _gear_item(item)
            if clean:
                inv.append(clean)
        sets.append({"name": _short_text(src.get("name"), 40) or "Set 1", "slots": slots, "inv": inv})
    if sets:
        out["sets"] = sets
    stash = []
    for item in (raw.get("stash") or [])[:80]:
        clean = _gear_item(item)
        if clean:
            stash.append(clean)
    if stash:
        out["stash"] = stash
    return out


def clean_book(raw):
    """The console book the page hands this PC. None means there was nothing to keep."""
    if not isinstance(raw, dict):
        return None
    builds = []
    for row in (raw.get("builds") or [])[:12]:
        clean = clean_build(row)
        if clean:
            builds.append(clean)
    owned = []
    for row in (raw.get("owned") or [])[:400]:
        if isinstance(row, str):
            name = _short_text(row, 80)
        elif isinstance(row, dict):
            name = _short_text(row.get("name"), 80)
        else:
            name = None
        if name:
            owned.append(name)
    if not builds and not owned:
        return None
    return {"builds": builds, "owned": owned}


def builds_read(book, now_ms):
    """Character builds the console actually stored. None means the book was not read."""
    if not isinstance(book, dict):
        return None
    builds = book.get("builds")
    if not isinstance(builds, list) or not builds:
        return None
    return {"read": True, "asOf": now_ms, "counts": len(builds), "rows": builds, "allow": ("build",)}


def stash_rows_of(book):
    """Flat stash and inventory cells from a console book. The grid painter uses x, y, w, h."""
    rows = []
    if not isinstance(book, dict):
        return rows
    # REG-2249 (#74b): names already published as a structured-stash row, so the flat `owned` pass
    # below cannot double-publish an item the book carries in BOTH places. This file folds neither
    # apostrophe nor case anywhere it matches names, and stash + owned names both arrive raw from the
    # same board pipeline, so the match is exact-string — the same text the rows already store.
    seen = set()
    for build in book.get("builds") or []:
        if not isinstance(build, dict):
            continue
        who = build.get("name") if isinstance(build.get("name"), str) else None
        items = list(build.get("stash") or [])
        for src in build.get("sets") or []:
            if isinstance(src, dict):
                items.extend(src.get("inv") or [])
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("name"), str):
                continue
            row = {"name": item["name"]}
            if isinstance(item.get("id"), str):
                row["id"] = item["id"]
            if who:
                row["mule"] = who
            for key in ("x", "y", "w", "h"):
                num = item.get(key)
                if isinstance(num, int) and not isinstance(num, bool):
                    row[key] = num
            rows.append(row)
            seen.add(item["name"])
    # REG-2247 (#74) - HIS 10-15 ruling: publish the stash on the roster too. His owned items (the
    # book's flat `owned` list, what the board already posts) are his stash contents, so a PC with no
    # per-build stash cells still publishes a stash the roster room can draw, same shape as the vault
    # section. A bare name is a valid stash row (the stash allow-list keeps name/id/mule/cell).
    # REG-2249 (#74b): an item the book carries in BOTH the structured stash and `owned` is ONE
    # physical item seen two ways, so skip an owned name a structured-stash row already published
    # (`seen`) — without it the roster drew two rows for one item. Two copies in `owned` alone stay
    # two rows (two physical items), and two mules holding the same item stay two rows (pass above
    # never dedupes against itself).
    for item in book.get("owned") or []:
        name = item if isinstance(item, str) else (item.get("name") if isinstance(item, dict) else None)
        if isinstance(name, str) and name and name not in seen:
            rows.append({"name": name})
    return rows


def _list_names(raw, limit=400):
    """Names from a store that was read. None means it was not read.

    A dict's keys are the names (found log, runewords made). A list is strings or
    {name}. An empty list is a read that found nothing, and it is not published as
    rows: an empty rows array does not survive the shaper, so it cannot mean zero.
    """
    if raw is None:
        return None
    if isinstance(raw, dict):
        src = list(raw.keys())
    elif isinstance(raw, list):
        src = []
        for item in raw:
            if isinstance(item, str):
                src.append(item)
            elif isinstance(item, dict) and isinstance(item.get("name"), str):
                src.append(item["name"])
    else:
        return None
    names = []
    seen = set()
    for name in src:
        text = _short_text(name, 80)
        if not text or text in seen:
            continue
        seen.add(text)
        names.append(text)
    # #200 (the v3802 look) - THE CAP KEPT THE OLDEST. A found log is {name: date} in the order he found them, newest
    # last, and the loop stopped at 400, so his 61 newest finds never reached the roster. The newest `limit` are kept;
    # chronicle_read publishes how many there were.
    return names[-limit:] if limit and len(names) > limit else names


def _list_count(raw):
    """#200 - how many distinct names a store that was read holds, or None when it was not read."""
    if raw is None:
        return None
    full = _list_names(raw, limit=0)
    return len(full) if isinstance(full, list) else None


def chronicle_rows(lists):
    """Found-item name rows. None means no list was read. An empty lane is not a row.

    The names travel on the chronicle section of the same roster post. A lane that
    was not read stays absent, so a reader cannot treat it as found-zero.
    """
    if not isinstance(lists, dict):
        return None
    rows = []
    for lane in ("uniques", "sets", "runewords"):
        names = lists.get(lane)
        if names is None:
            continue
        cleaned = _list_names(names)
        if not cleaned:
            continue
        for name in cleaned:
            rows.append({"lane": lane, "name": name})
    return rows or None


def chronicle_read(tally, now_ms, lists=None):
    """Counts from a tally that did not fail, plus name rows when those stores were read.

    REG-2200 (#94): this REQUIRED ok:true, but a banked board_tally.json (written by
    board_tally_merge, read via board_tally_load) carries the owner's sets/uniques/runewords with
    NO 'ok' key — so every PC's chronicle came back None and NO PC ever published its progress. A
    failed read (`{ok: False, why: ...}`) still has no counts and is refused below; an explicit
    ok:False is refused here. The counts themselves are the read; a missing 'ok' is not a failure.

    lists is the three found-item stores, or None when they were not read. A missing
    list does not become an empty rows array. Names that were read ride this same section.
    """
    if not isinstance(tally, dict) or tally.get("ok") is False:
        return None
    counts = {}
    for key in ("sets", "uniques", "runewords"):
        pair = tally.get(key)
        if not isinstance(pair, dict):
            continue
        have, total = pair.get("have"), pair.get("total")
        if isinstance(have, bool) or not isinstance(have, int) or have < 0:
            continue
        item = {"have": have}
        if isinstance(total, int) and not isinstance(total, bool) and total > 0:
            item["total"] = total
        counts[key] = item
    if not counts:
        return None
    at = tally.get("at")
    if isinstance(at, bool) or not isinstance(at, int) or at <= 0:
        at = now_ms
    # #200 - the rows carry at most 400 names a lane; the count of all of them rides beside the counts, so a reader can
    # say "the newest 400 of 461" instead of calling 400 the whole list
    if isinstance(lists, dict):
        for lane in ("uniques", "sets", "runewords"):
            n = _list_count(lists.get(lane))
            if isinstance(n, int) and n >= 0:      # Grok v3815 - a lane read with no names says 0, never absent
                counts[lane + "Named"] = n
    out = {"read": True, "asOf": at, "counts": counts}
    rows = chronicle_rows(lists)
    if rows:
        out["rows"] = rows
        out["allow"] = ("lane", "name")
        # #200 (REG-2745) - the names are read NOW, from the found stores, while asOf is when the counts were banked; the
        # rows carry their own age so a viewer never dates fresh names by old counts (or the other way round)
        if isinstance(now_ms, int) and not isinstance(now_ms, bool) and now_ms > 0:
            out["rowsAsOf"] = now_ms
    return out


def chronicle_within(sections, limit=60000):
    """Drop chronicle name rows when the packed sections would not fit the row cap.

    The counts stay. A list that cannot travel is absent, which the reader says,
    rather than refusing the whole publish.
    """
    if not isinstance(sections, dict) or not isinstance(limit, int) or limit < 1:
        return sections
    try:
        size = len(packed(sections).encode("utf-8"))
    except Exception:
        return sections
    if size <= limit:
        return sections
    chron = sections.get("chronicle")
    if not isinstance(chron, dict) or "rows" not in chron:
        return sections
    shrunk = dict(sections)
    chron = dict(chron)
    chron.pop("rows", None)
    shrunk["chronicle"] = chron
    return shrunk


def reels_read(names, stamps, station_counts, now_ms):
    """Newest rows from a shelf that was listed. names None means the shelf was not read."""
    if names is None or not isinstance(names, list):
        return None
    named = [n for n in names if isinstance(n, str)]
    ordered = list(named)
    try:
        import reel_retention as rr
        ordered = rr.recent_order(named)
    except Exception:
        pass
    newest = list(reversed(ordered))[:16]
    rows = []
    rr = None
    try:
        import reel_retention as rr
    except Exception:
        rr = None
    for reel in newest:
        row = {}
        ts = None
        if rr is not None:
            try:
                ts = rr._reel_ts(reel)
            except Exception:
                ts = None
        if isinstance(ts, int) and not isinstance(ts, bool):
            row["date"] = ts
        station = None
        if isinstance(stamps, dict):
            station = stamps.get(reel)
            if station is None and reel.startswith("reel_"):
                station = stamps.get(reel[len("reel_"):])
        if isinstance(station, str) and station and station != "UNKNOWN":
            row["station"] = station
        if row:
            rows.append(row)
    counts = {"reels": len(named)}
    # REG-2205 (#99) — a river stamp survives the reel's deletion, so station_counts (built upstream
    # from EVERY stamp) counted GONE reels: measured 198 stamps against 67 live reels. Count a station
    # only for a reel still on the shelf (named), resolved through the same stamps map the rows use.
    # station_counts is kept for the caller's contract but no longer the total. [[stale-reading]]
    if isinstance(stamps, dict):
        live = 0
        for reel in named:
            st = stamps.get(reel)
            if st is None and reel.startswith("reel_"):
                st = stamps.get(reel[len("reel_"):])
            if isinstance(st, str) and st and st != "UNKNOWN":
                live += 1
        counts["stations"] = live
    return {"read": True, "asOf": now_ms, "counts": counts, "rows": rows,
            "allow": ("date", "station")}


def for_hash(sections):
    out = {}
    for name in sorted((sections or {}).keys()):
        sec = sections[name]
        if not isinstance(sec, dict):
            continue
        kept = {k: sec[k] for k in sorted(sec) if k not in ("asOf", "rowsAsOf", "hash", "allow")}   # REG-2745
        if isinstance(kept.get("sweep"), dict):
            kept["sweep"] = {"owned": kept["sweep"].get("owned")}   # v3866 - the count, never its age (no churn)
        out[name] = kept
    return out


def packed(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def hash_of(text):
    """FNV-1a over UTF-16 code units, the units functions/api/roster.js hashOf walks (charCodeAt).

    REG-2511 (#95): this walked code POINTS. A character outside the BMP (an emoji) was one unit
    here and a surrogate pair in the worker, so 'Ber 🧿 rune' hashed a8b9dc5d here and 83534eb3
    there, and view_one marked that owner CORRUPT for every viewer. ASCII and BMP text hash exactly
    as before. surrogatepass keeps a lone surrogate as the one unit JavaScript sees."""
    h = 2166136261
    data = text.encode("utf-16-le", "surrogatepass")
    for i in range(0, len(data), 2):
        h ^= data[i] | (data[i + 1] << 8)
        h = (h * 16777619) & 0xFFFFFFFF
    return "%x" % h


def reads_due(state, now_ms, boot):
    """#200 - may this tick read the board at all? -> (open, why). The time half of due(), asked BEFORE the reads: the
    lane ticks every 60 s and read the whole board (board_ownership over 5,000 rows) on every tick, only for due() to
    say "within the hour". A boot always reads; a refusal waits the hour; otherwise the last post must be an hour old."""
    state = state if isinstance(state, dict) else {}
    if boot:
        return True, "boot"
    refused = state.get("refuseAt")
    if isinstance(refused, int) and not isinstance(refused, bool) and now_ms - refused < HOUR_MS:
        return False, state.get("why") or "the roster refused the last publish"
    last = state.get("at")
    if isinstance(last, int) and not isinstance(last, bool) and now_ms - last < HOUR_MS:
        return False, "within the hour"
    return True, "open"


def due(state, owner, sections, now_ms, boot):
    """-> (body or None, why). Unchanged and inside the hour do not post.

    Boot posts, changed or not, inside the hour or not. REG-2512 (#95): 'unchanged' was answered
    before boot was asked, so a row someone else wrote in this PC's name was never re-published
    over: the PC's digest still matched its own last post. The server skips the write when its
    stored hash matches, so an honest boot costs no write. A refusal is still not retried inside
    the hour. signedAt is the clock the signature covers.

    What a boot post heals, exactly: a SIGNED one that the server verifies replaces a row its key did
    not write whole - every section this PC did not send is dropped, `owned` included, which no PC
    sends (REG-2516, roster.js). An UNSIGNED one (no key here, or none usable) overwrites only the
    sections it sends; the rest of a planted row stays, and the row reads NOT signature-verified.
    """
    state = state if isinstance(state, dict) else {}
    if not roster_key(owner):
        return None, "the owner is not one of the five labels"
    if not sections:
        return None, "nothing on this PC was read"
    digest = hash_of(packed(for_hash(sections)))
    refused = state.get("refuseAt")
    if isinstance(refused, int) and not isinstance(refused, bool) and now_ms - refused < HOUR_MS:
        return None, state.get("why") or "the roster refused the last publish"
    if state.get("hash") == digest and not boot:
        return None, "unchanged"
    last = state.get("at")
    if (not boot and isinstance(last, int) and not isinstance(last, bool)
            and now_ms - last < HOUR_MS):
        return None, "within the hour"
    return {"owner": owner, "boot": True if boot else False, "signedAt": now_ms,
            "sections": sections}, "post"


#: What one POST did, in the receipt's own words. A transport failure is not a refusal.
OUTCOMES = ("stored", "skipped", "refused", "unreached")


def _words(v, n=200):
    if not isinstance(v, str):
        return None
    s = " ".join(v.split())
    return s[:n] if s else None


def short_key_id(v):
    """A key id as roster.js and roster_sign.key_id write it (12 hex), or None."""
    if not isinstance(v, str) or len(v) != 12:
        return None
    if any(c not in "0123456789abcdef" for c in v):
        return None
    return v


def verified_of(row):
    """True, False, or None. None is UNKNOWN: a row published before signing carries no field."""
    if not isinstance(row, dict):
        return None
    v = row.get("intentVerified")
    return v if isinstance(v, bool) else None


def post_record(reply, now_ms):
    """#95 - what this PC's last POST did, kept whole: the server's verdict and this PC's signing.

    `reply["signing"]` is written by the console's _roster_post, never by the server. It carries a
    key id and words only; no seed reaches it. -> dict"""
    reply = reply if isinstance(reply, dict) else {}
    signing = reply.get("signing") if isinstance(reply.get("signing"), dict) else {}
    stored = reply.get("stored") or []
    if reply.get("ok") is True and "roster" in stored:
        outcome, why = "stored", "published"
    elif reply.get("ok") is True:
        skipped = [s for s in (reply.get("skipped") or []) if isinstance(s, str)]
        outcome, why = "skipped", "skipped: " + ",".join(skipped)
    elif isinstance(reply.get("hint"), str):
        outcome, why = "refused", _words(reply.get("why")) or "refused, with no reason given"
    else:
        outcome = "unreached"
        why = _words(reply.get("why")) or "the roster could not be reached"
        code = reply.get("code")
        if isinstance(code, int) and not isinstance(code, bool):
            why = "%s (HTTP %d)" % (why, code)
    rec = {"at": now_ms, "outcome": outcome, "why": why[:200], "signed": signing.get("signed") is True}
    if not rec["signed"]:
        rec["sigWhy"] = _words(signing.get("why")) or "this publish carried no signature"
    kid = short_key_id(signing.get("keyId"))
    if kid:
        rec["keyId"] = kid
    signer = _words(signing.get("signer"), 60)
    if signer:
        rec["signer"] = signer
    agree = signing.get("agree")
    rec["agree"] = agree if isinstance(agree, bool) else None
    if signing.get("made") is True:
        rec["made"] = True
    iv = reply.get("intentVerified")
    rec["intentVerified"] = iv if isinstance(iv, bool) else None
    server_kid = short_key_id(reply.get("keyId"))
    if server_kid:
        rec["serverKeyId"] = server_kid
    if isinstance(reply.get("sig"), str):
        rec["serverSig"] = reply["sig"][:12]
    said = _words(reply.get("sigWhy"))
    if said:
        rec["serverSigWhy"] = said
    if reply.get("registered") is True:
        rec["registered"] = True
    return rec


def apply_reply(state, sections, reply, now_ms):
    """What the client remembers after the server answers. A skip is not a publish."""
    state = dict(state or {})
    reply = reply if isinstance(reply, dict) else {}
    state["post"] = post_record(reply, now_ms)
    digest = hash_of(packed(for_hash(sections or {})))
    stored = reply.get("stored") or []
    if reply.get("ok") is True and "roster" in stored:
        state["hash"] = digest
        state["at"] = now_ms
        state.pop("refuseAt", None)
        state["why"] = "published"
        return state
    if reply.get("ok") is True:
        skipped = [s for s in (reply.get("skipped") or []) if isinstance(s, str)]
        if "unchanged" in skipped:
            state["hash"] = digest
        state["at"] = now_ms
        state["why"] = "skipped: " + ",".join(skipped)
        return state
    state["refuseAt"] = now_ms
    why = reply.get("why")
    state["why"] = str(why)[:200] if isinstance(why, str) and why else "refused"
    return state


def publish_outcome(state, now_ms=None):
    """#95 - this PC's own last publish, from its own receipt (.tvd_roster.json). -> dict

    state is one of: signed (the site verified it), unverified (signed here, NOT verified there),
    unsigned (with why), refused (with why), unreached (with why), unknown. A receipt with no post
    record was written before signing shipped, or nothing has been posted since: UNKNOWN, never
    'signed'."""
    if not isinstance(state, dict):
        return {"state": "unknown", "why": "this PC has no publish receipt"}
    post = state.get("post")
    if not isinstance(post, dict) or post.get("outcome") not in OUTCOMES:
        last = _words(state.get("why"))
        return {"state": "unknown",
                "why": "no publish recorded since signing shipped" + ((" (last: %s)" % last) if last else "")}
    out = {"outcome": post["outcome"], "signed": post.get("signed") is True,
           "why": _words(post.get("why")) or post["outcome"]}
    at = post.get("at")
    if isinstance(at, int) and not isinstance(at, bool):
        out["at"] = at
        _state, words = _ago(at, now_ms)
        out["ago"] = words
    for k in ("keyId", "serverKeyId"):
        kid = short_key_id(post.get(k))
        if kid:
            out[k] = kid
    signer = _words(post.get("signer"), 60)
    if signer:
        out["signer"] = signer
    agree = post.get("agree")
    out["agree"] = agree if isinstance(agree, bool) else None
    iv = post.get("intentVerified")
    out["intentVerified"] = iv if isinstance(iv, bool) else None
    if post["outcome"] == "refused":
        out["state"] = "refused"
    elif post["outcome"] == "unreached":
        out["state"] = "unreached"
    elif not out["signed"]:
        out["state"] = "unsigned"
        out["why"] = _words(post.get("sigWhy")) or "this publish carried no signature"
    elif out["intentVerified"] is False:
        out["state"] = "unverified"
        out["why"] = _words(post.get("serverSigWhy")) or "the site did not verify the signature"
    else:
        out["state"] = "signed"
    return out


def _me_line(me):
    """The one line about THIS PC's own last publish. -> (css class, words) or None."""
    if not isinstance(me, dict):
        return None
    st = me.get("state")
    when = (" (%s)" % me["ago"]) if isinstance(me.get("ago"), str) else ""
    why = _words(me.get("why")) or ""
    if st == "signed":
        kid = me.get("keyId") or "?"
        if me.get("intentVerified") is True:
            said = "the site verified it"
        else:
            said = "the site did not say whether it verified it"
        tail = "; its two signers DISAGREE" if me.get("agree") is False else ""
        return "roster-me", "this PC's last publish%s: signed with key %s, %s, %s%s" % (when, kid, why, said, tail)
    if st == "unverified":
        return "roster-me roster-unverified", "this PC's last publish%s was signed but NOT verified by the site: %s" % (when, why)
    if st == "unsigned":
        return "roster-me roster-unverified", "this PC's last publish%s went UNSIGNED: %s" % (when, why)
    if st == "refused":
        return "roster-me roster-refused", "this PC's last publish%s was REFUSED: %s" % (when, why)
    if st == "unreached":
        return "roster-me roster-unknown", "this PC's last publish%s did not reach the site: %s" % (when, why)
    return "roster-me roster-unknown", "this PC's last publish: UNKNOWN (%s)" % (why or "no receipt")


#: REG-2867 - the two posts the roster lane makes after the rows (control_app._roster_publish_loop), each with its own receipt
#: on this PC: the profile (.roster_profile_state.json, console_snapshot.apply_reply) and the sessions digest
#: (.roster_frames_state.json, shadow_sessions.apply_reply)
LANE_LABELS = (("profile", "profile upload"), ("frames", "sessions upload"))


def _ms(v):
    return v if isinstance(v, int) and not isinstance(v, bool) and v > 0 else None


def lane_line(kind, state, now_ms):
    """REG-2867 - one line about this PC's last profile or sessions post, from its own receipt, so a refused post is said
    where the rows' own is (meLine); GrokBot found a refused frames post nowhere. -> {"cls", "words", "kind"} | None

    A held lane (the beacon suppressed) says HELD. Otherwise the receipt's newest event decides: a post that did not go
    through (refused, or the site unreached - the receipt keeps no difference between them), a post the site stored or
    skipped, or a look that posted nothing; each with its own age and the receipt's own words. No receipt is UNKNOWN."""
    label = dict(LANE_LABELS).get(kind)
    if not label:
        return None
    head = "this PC's %s" % label
    if not isinstance(state, dict) or not state:
        return {"kind": kind, "cls": "roster-me roster-unknown", "words": head + ": UNKNOWN (this PC has no receipt for it yet)"}
    why = _words(state.get("why")) or ""
    if why.startswith("suppressed"):
        return {"kind": kind, "cls": "roster-me roster-unknown", "words": "%s is HELD: %s" % (head, why)}

    def ago(t):
        return " (%s)" % (_ago(t, now_ms)[1] or "age unknown")
    post = state.get("post") if isinstance(state.get("post"), dict) else None
    if kind == "profile" and post is not None and _ms(post.get("at")):
        # the profile keeps its last POST whole ({at, ok, why}); a later gate reason never overwrites it
        said = _words(post.get("why")) or "no reason given"
        if post.get("ok") is not True:
            return {"kind": kind, "cls": "roster-me roster-refused",
                    "words": "%s did NOT go through%s: %s" % (head, ago(post["at"]), said)}
        return {"kind": kind, "cls": "roster-me", "words": "%s%s: %s" % (head, ago(post["at"]), said)}
    events = [(t, name) for t, name in ((_ms(state.get("refuseAt")), "refused"),
                                        (_ms(state.get("postedAt") if kind == "frames" else state.get("at")), "posted"),
                                        (_ms(state.get("checkedAt")), "checked")) if t]
    if not events:
        return {"kind": kind, "cls": "roster-me roster-unknown",
                "words": "%s: UNKNOWN (its receipt carries no time%s)" % (head, (": " + why) if why else "")}
    t, name = max(events)
    if name == "refused":
        said = why[len("refused: "):] if why.startswith("refused: ") else (why or "no reason given")
        return {"kind": kind, "cls": "roster-me roster-refused",
                "words": "%s did NOT go through%s: %s" % (head, ago(t), said)}
    if name == "posted":
        return {"kind": kind, "cls": "roster-me", "words": "%s%s: %s" % (head, ago(t), why or "posted")}
    return {"kind": kind, "cls": "roster-me", "words": "%s posted nothing%s: %s" % (head, ago(t), why or "no reason given")}


def lane_lines(states, now_ms):
    """REG-2867 - the profile and sessions lines, in the lane's order. states: {kind: receipt dict | None}. -> list"""
    states = states if isinstance(states, dict) else {}
    return [lane_line(kind, states.get(kind), now_ms) for kind, _label in LANE_LABELS]


def signature_words(row):
    """One published row's signature, in words. -> (css class, words). None stays UNKNOWN."""
    v = verified_of(row)
    kid = short_key_id((row or {}).get("keyId")) if isinstance(row, dict) else None
    if v is True:
        return "roster-verified", "signature verified" + ((" (key %s)" % kid) if kid else "")
    if v is False:
        return ("roster-unverified",
                "NOT signature-verified: published without a signature its owner's key made")
    return "roster-unknown", "signature UNKNOWN: published before signing"


def signing_verdict(payload, me, owner=None, own_key_id=None):
    """#95 doctor row: every published owner is signature-verified, and this PC's last publish was
    not refused. -> (state, why), state "ok" | "missing" | "unknown".

    MISSING names the PC or the owner and what is wrong. UNKNOWN is a row published before signing,
    a corrupt row, a roster this PC has not fetched, or no receipt yet - never OK. `owner` is this
    PC's roster label (None: this PC publishes nothing, so only the other owners are asked);
    `own_key_id` is the id of the key in this PC's own key file, compared with the id the roster
    names for that owner."""
    problems, unknown = [], []
    me = me if isinstance(me, dict) else {}
    st = me.get("state")
    if owner:
        why = _words(me.get("why")) or "no reason recorded"
        if st == "refused":
            problems.append("this PC's last publish was REFUSED (%s)" % why)
        elif st == "unsigned":
            problems.append("this PC's last publish went UNSIGNED (%s)" % why)
        elif st == "unverified":
            problems.append("this PC's last publish was signed but the site did NOT verify it (%s)" % why)
        elif st == "unreached":
            unknown.append("this PC's last publish did not reach the site (%s)" % why)
        elif st == "signed" and me.get("intentVerified") is not True:
            unknown.append("the site did not say whether it verified this PC's last publish")
        elif st != "signed":
            unknown.append("this PC has no publish on record since signing shipped")
        if me.get("agree") is False:
            problems.append("this PC's two signers DISAGREE on the same bytes (cryptography against the "
                            "RFC 8032 signer) - one of them is wrong")
    if not isinstance(payload, dict) or payload.get("fetched") is not True:
        unknown.append("this PC has not fetched the roster, so no owner's signature can be read")
        rows = []
    else:
        rows = payload.get("owners") if isinstance(payload.get("owners"), list) else []
    verified, unsigned, before, corrupt = [], [], [], []
    for row in rows:
        if not isinstance(row, dict) or row.get("owner") not in OWNERS:
            continue
        if row.get("published") is not True:
            continue
        name = row["owner"]
        if row.get("corrupt") is not False:       # corrupt, or a row that does not say: unreadable
            corrupt.append(name)
            continue
        v = verified_of(row)
        if v is True:
            verified.append(name)
            kid = short_key_id(row.get("keyId"))
            if owner and name == owner and own_key_id and kid and kid != own_key_id:
                problems.append("the roster names key %s for %s but this PC signs with %s - its next "
                                "publish is refused until Konyo resets that owner's key from the Mac"
                                % (kid, name, own_key_id))
        elif v is False:
            unsigned.append(name)
        else:
            before.append(name)
    if unsigned:
        problems.append("%d published owner(s) are NOT signature-verified: %s"
                        % (len(unsigned), ", ".join(unsigned)))
    if before:
        unknown.append("published before signing, so UNKNOWN: %s" % ", ".join(before))
    if corrupt:
        unknown.append("corrupt, so their signature cannot be read: %s" % ", ".join(corrupt))
    if problems:
        return "missing", "; ".join(problems + unknown)
    if unknown:
        return "unknown", "; ".join(unknown)
    if not verified:
        return "unknown", "the roster holds no published owner yet, so no signature has been read"
    mine = (" and this PC's last publish was signed with key %s and verified" % me.get("keyId")) if owner else ""
    return "ok", "all %d published owner(s) are signature-verified%s" % (len(verified), mine)


def doctor_row(ca, now_ms):
    """#95 - the doctor's question, asked of one console module (the control_app that serves). -> (state, why)

    It reads only: this PC's receipt, its fetched roster cache, and the PUBLIC half of its key. It never
    makes a key, posts, or fetches. console_doctor's row is this call and nothing else."""
    import roster_sign as _rs
    receipt = ca._roster_state_load()
    payload = ca._roster_cache_payload()
    owner = owner_of(ca._roster_claimed_name(), ca._roster_platform())
    mine, _why = _rs.public_view(_rs.key_path_in(ca._log_root()))
    return signing_verdict(payload, publish_outcome(receipt, now_ms), owner, (mine or {}).get("keyId"))


def _age_state(as_of, now_ms):
    """current, stale, or unknown. A missing clock is unknown, never current — and so is a FUTURE
    clock: REG-2201 (#99) a reading stamped ahead of now (skew) scored `now - as_of` negative, so it
    read 'current' / 'under 1 min ago' in _ago instead of being owned as unknown. [[stale-reading]]"""
    if isinstance(as_of, bool) or not isinstance(as_of, int):
        return "unknown"
    if isinstance(now_ms, bool) or not isinstance(now_ms, int):
        return "unknown"
    # stamped in the FUTURE beyond a minute of skew is a bad clock, not a fresh reading
    if as_of - now_ms > 60000:
        return "unknown"
    if now_ms - as_of > 2 * HOUR_MS:
        return "stale"
    return "current"


def view_one(owner, row, now_ms):
    """One owner's fetch row. A bad hash is corrupt and carries no sections."""
    if owner not in OWNERS:
        return None
    if not isinstance(row, dict) or row.get("owner") != owner or row.get("published") is not True:
        return {"owner": owner, "published": False}
    if row.get("corrupt") is True:
        return {"owner": owner, "published": True, "corrupt": True}
    raw = row.get("sections") if isinstance(row.get("sections"), dict) else {}
    kept = {}
    for name in SECTIONS:
        sec = raw.get(name)
        if isinstance(sec, dict) and sec:
            kept[name] = {k: sec[k] for k in sec if k != "age"}
    digest = hash_of(packed(for_hash(kept)))
    if row.get("hash") != digest:
        return {"owner": owner, "published": True, "corrupt": True}
    out = {"owner": owner, "published": True, "corrupt": False, "hash": digest,
           "age": _age_state(row.get("t"), now_ms)}
    # #95 - the signature verdict travels with the row: True, False, or None (published before signing).
    out["intentVerified"] = verified_of(row)
    kid = short_key_id(row.get("keyId"))
    if kid:
        out["keyId"] = kid
    if isinstance(row.get("t"), int) and not isinstance(row.get("t"), bool):
        out["t"] = row["t"]
    if kept:
        shown = {}
        for name, sec in kept.items():
            one = dict(sec)
            one["age"] = _age_state(sec.get("asOf"), now_ms)
            if "rowsAsOf" in sec:
                one["rowsAge"] = _age_state(sec.get("rowsAsOf"), now_ms)   # #200 (REG-2745) - the names' own age
            shown[name] = one
        out["sections"] = shown
    return out


def view_of(owners, now_ms):
    """Every label, in label order. An owner the reply left out was not published."""
    by = {}
    if isinstance(owners, list):
        for row in owners:
            if isinstance(row, dict) and row.get("owner") in OWNERS:
                by[row["owner"]] = row
    return [view_one(owner, by.get(owner), now_ms) for owner in OWNERS]


def cache_views(reply, now_ms):
    """Views to store, or None when this answer must not replace the cache.

    ok true with no owners list is not "nobody has published". view_of on a
    missing list would write that lie over the last good fetch.
    """
    if not isinstance(reply, dict) or reply.get("ok") is not True:
        return None
    owners = reply.get("owners")
    if not isinstance(owners, list):
        return None
    return view_of(owners, now_ms)


def never_published_line(owner, section):
    if owner not in OWNERS or section not in SECTIONS:
        return None
    return "%s has not published its %s yet" % (owner, section)


def cache_file_name(owner):
    if owner not in OWNERS:
        return None
    return owner.replace(" · ", "__").replace(" ", "_") + ".json"


def write_cache(directory, views):
    """Write one file per owner inside directory. A path that escapes it is skipped."""
    if not isinstance(directory, str) or not directory:
        return []
    os.makedirs(directory, exist_ok=True)
    root = os.path.abspath(directory)
    written = []
    for view in views or []:
        if not isinstance(view, dict):
            continue
        name = cache_file_name(view.get("owner"))
        if not name:
            continue
        if view.get("published") is True and view.get("corrupt") is not True:
            body = dict(view)
            # #95 - written every time, null when unknown, so a reader of the file never has to
            # guess whether an absent field meant "not verified".
            body["intentVerified"] = verified_of(view)
        elif view.get("corrupt") is True:
            body = {"owner": view.get("owner"), "published": True, "corrupt": True}
        else:
            body = {"owner": view.get("owner"), "published": False}
        path = os.path.abspath(os.path.join(directory, name))
        if os.path.dirname(path) != root:
            continue
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(body, fh, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        os.replace(tmp, path)
        written.append(name)
    return sorted(written)


def refresh_view(view, now_ms):
    """The stored row with ages recomputed from its clocks. A bad file is corrupt."""
    if not isinstance(view, dict):
        return None
    owner = view.get("owner")
    if owner not in OWNERS:
        return None
    if view.get("published") is not True:
        return {"owner": owner, "published": False}
    if view.get("corrupt") is True:
        return {"owner": owner, "published": True, "corrupt": True}
    sections = view.get("sections") if isinstance(view.get("sections"), dict) else {}
    kept = {}
    for name in SECTIONS:
        sec = sections.get(name)
        if not isinstance(sec, dict) or not sec:
            continue
        one = {k: sec[k] for k in sec if k != "age"}
        one["age"] = _age_state(sec.get("asOf"), now_ms)
        kept[name] = one
    out = {"owner": owner, "published": True, "corrupt": False,
           "age": _age_state(view.get("t"), now_ms)}
    out["intentVerified"] = verified_of(view)
    kid = short_key_id(view.get("keyId"))
    if kid:
        out["keyId"] = kid
    if isinstance(view.get("t"), int) and not isinstance(view.get("t"), bool):
        out["t"] = view["t"]
    if kept:
        out["sections"] = kept
    return out


def read_cache(directory, now_ms):
    """The files on disk. No directory means this PC has not fetched, not that the others are empty."""
    if not isinstance(directory, str) or not os.path.isdir(directory):
        return {"ok": True, "fetched": False, "owners": []}
    owners = []
    found = False
    root = os.path.abspath(directory)
    for owner in OWNERS:
        name = cache_file_name(owner)
        path = os.path.abspath(os.path.join(directory, name))
        if os.path.dirname(path) != root or not os.path.isfile(path):
            continue
        found = True
        try:
            with open(path, encoding="utf-8") as fh:
                view = json.load(fh)
        except Exception:
            owners.append({"owner": owner, "published": True, "corrupt": True})
            continue
        fresh = refresh_view(view, now_ms)
        owners.append(fresh if fresh else {"owner": owner, "published": True, "corrupt": True})
    if not found:
        return {"ok": True, "fetched": False, "owners": []}
    return {"ok": True, "fetched": True, "now": now_ms, "owners": owners}


def _ago(as_of, now_ms):
    state = _age_state(as_of, now_ms)
    if state == "unknown":
        return state, None
    minutes = (now_ms - as_of) // 60000
    if minutes < 1:
        words = "under 1 min ago"
    elif minutes < 120:
        words = "%d min ago" % minutes
    else:
        words = "%d hr ago" % (minutes // 60)
    return state, words


def _age_words(state, words):
    """The age phrase. A stale clock says stale. An unknown clock stays unknown."""
    if not words:
        return None
    if state == "stale":
        return words + " stale"
    return words


def _count_text(counts):
    """Words for a measured tally. Chronicle and reels store a dict, not one integer."""
    if isinstance(counts, bool) or counts is None:
        return None
    if isinstance(counts, int):
        return str(counts)
    if not isinstance(counts, dict) or not counts:
        return None
    parts = []
    for key, val in counts.items():
        if not isinstance(key, str) or not key:
            continue
        label = key[:40]
        if isinstance(val, bool) or val is None:
            continue
        if isinstance(val, int):
            parts.append("%s %s" % (label, val))
            continue
        if not isinstance(val, dict):
            continue
        have = val.get("have")
        if isinstance(have, bool) or not isinstance(have, int):
            continue
        total = val.get("total")
        if isinstance(total, int) and not isinstance(total, bool) and total > 0:
            parts.append("%s %s/%s" % (label, have, total))
        else:
            parts.append("%s %s" % (label, have))
    if not parts:
        return None
    return " · ".join(parts)


def _show_cell(value, now_ms=None, key=None):
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        if key == "date":
            _state, words = _ago(value, now_ms)
            if words:
                return words
            return "age unknown"
        return str(value)
    if not isinstance(value, str) or not value:
        return None
    low = value.lower()
    if (low.startswith("http") or low.startswith("/") or low.startswith("data:")
            or low.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif"))):
        return None
    return value[:80]


def _row_line(row, now_ms):
    if not isinstance(row, dict):
        return None
    cells = []
    for key in ("name", "cls", "level", "title", "tier", "mule", "locker", "station", "date", "provenance"):
        cell = _show_cell(row.get(key), now_ms, key)
        if cell:
            cells.append(cell)
    if not cells:
        return None
    return " · ".join(cells)


def roster_html(payload):
    """Read-only markup. A missing fetch is not five empty rosters.

    #95: when the caller hands over `me` (this PC's own last publish, publish_outcome), that line
    leads the markup, fetched or not, so a refused or unsigned publish is never left out of it."""
    lead = _me_html(payload.get("me")) if isinstance(payload, dict) else ""
    # REG-2867 - and the profile and sessions posts' own lines beside it
    for line in (payload.get("laneLines") or []) if isinstance(payload, dict) else []:
        if isinstance(line, dict) and isinstance(line.get("words"), str):
            lead += '<p class="%s">%s</p>' % (html.escape(str(line.get("cls") or "roster-me"), quote=True),
                                              html.escape(line["words"], quote=True))
    return lead + _owners_html(payload)


#: what a published row whose hash did not hold says about its signature (the doctor's word for it, too)
CORRUPT_SIGNATURE = "corrupt, so its signature cannot be read"


def row_age_words(row, now_ms):
    """REG-3037 (#218, GrokBot #230 6485639332) - what a roster row's age dates, named, from the row's own stamp.

    The site STORES a row only when it changes (roster.js answers an unchanged post "unchanged" and writes nothing, and
    a PC posts an unchanged row only at boot), so its `t` is the last change, not the last time its owner looked. The
    panel said "<owner> · stale" from it: at 03:31 the Mac's row read 22:00:41 and Fleet said stale while the Mac was
    online and its board snapshot was 02:18:54 - two records on two clocks (the board waits out its own 75 min gap,
    console_snapshot.MIN_GAP_MS), each read as one age. Now every surface that dates the row says it is the row's store.
    -> words (never None: a row whose clock is missing or ahead of now says its age is UNKNOWN)"""
    _state, words = _ago(row.get("t") if isinstance(row, dict) else None, now_ms)
    return ("roster row stored " + words) if words else "roster row stored, age UNKNOWN"


def vault_line(row, now_ms):
    """#250 (REG-3122) - ONE LINE FOR AN OWNER'S PUBLISHED VAULT, for a Fleet row and a roster person button, so a viewer
    sees whose vault is how big and how old without opening a shadow. From the row's own vault section (REG-2817: the copy
    records that board last handed, counts = rows, asOf = when it handed them): "vault N items · as of <age>", STALE past
    the roster's 2 h TTL (_age_state), UNKNOWN when the row or its count will not read, and "vault never published" when
    the row or its vault section is absent. The age is that section's own asOf - never this fetch's time, never the row's
    `t` (when the site stored the copy). -> {"cls", "state", "words"}, None for a row that is no owner's"""
    if not isinstance(row, dict) or row.get("owner") not in OWNERS:
        return None
    if row.get("published") is not True:
        return {"cls": "roster-never", "state": "never", "words": "vault never published"}
    if row.get("corrupt") is not False:
        return {"cls": "roster-unknown", "state": "unknown", "words": "vault UNKNOWN (the roster row is corrupt)"}
    sections = row.get("sections") if isinstance(row.get("sections"), dict) else {}
    sec = sections.get("vault")
    if not isinstance(sec, dict):
        return {"cls": "roster-never", "state": "never", "words": "vault never published"}
    n = sec.get("counts")
    if isinstance(n, bool) or not isinstance(n, int) or n < 0:
        return {"cls": "roster-unknown", "state": "unknown", "words": "vault UNKNOWN (its count would not read)"}
    state, words = _ago(sec.get("asOf"), now_ms)
    head = "vault %d item%s" % (n, "" if n == 1 else "s")
    # v3866 (his call 2026-11-06: "show both numbers on the fleet row") - the board's records (the vault) and what the
    # SWEEP's evidence ledger grounds are two stores; both are said, each with its own age, never one summed into the other
    sw = sweep_of(sec.get("sweep"))
    tail = ""
    if sw is not None:
        s_state, s_words = _ago(sw["asOf"], now_ms)
        tail = " \u00b7 sweep evidence %d (not filed) \u00b7 %s" % (sw["owned"], s_words if s_state != "unknown" else "age UNKNOWN")
    if state == "unknown":
        return {"cls": "roster-unknown", "state": "unknown", "words": head + " \u00b7 age UNKNOWN" + tail}
    if state == "stale":
        return {"cls": "roster-stale", "state": "stale", "words": head + " \u00b7 as of " + words + " \u00b7 STALE" + tail}
    return {"cls": "roster-sec", "state": "current", "words": head + " \u00b7 as of " + words + tail}


def panel_words(payload):
    """#95 (REG-2517) - the words the console's roster panel and shadow bar draw, made by the same functions roster_html
    uses (signature_words, _me_line), so the buttons, the bar and the page cannot say different things. -> payload

    Adds payload["meLine"] = {"cls", "words"}: THIS PC's own last publish (signed, unsigned, refused, ... with why),
    whenever payload["me"] is there. Adds row["sig"] = {"cls", "words"} to every PUBLISHED row: signature verified
    (key ...), NOT signature-verified, signature UNKNOWN (published before signing), or, for a corrupt row, that its
    signature cannot be read. An unpublished row gets none: nothing was published to be signed. REG-3037 - and
    row["ageWords"], the row's own age named as the row's store (row_age_words)."""
    if not isinstance(payload, dict):
        return payload
    if "me" in payload:
        line = _me_line(payload.get("me"))
        if line:
            payload["meLine"] = {"cls": line[0], "words": line[1]}
    for row in payload.get("owners") or []:
        if isinstance(row, dict) and row.get("owner") in OWNERS:
            row["vaultLine"] = vault_line(row, payload.get("now"))   # #250 (REG-3122) - its vault, aged by its own asOf
        if not isinstance(row, dict) or row.get("published") is not True:
            continue
        if row.get("corrupt") is not False:
            row["sig"] = {"cls": "roster-unknown", "words": CORRUPT_SIGNATURE}
            continue
        cls, words = signature_words(row)
        row["sig"] = {"cls": cls, "words": words}
    for row in payload.get("owners") or []:
        if isinstance(row, dict) and row.get("published") is True:
            row["ageWords"] = row_age_words(row, payload.get("now"))   # REG-3037 - the panel and the bar print it as given
    return payload


def _me_html(me):
    line = _me_line(me)
    if not line:
        return ""
    klass, words = line
    return '<p class="%s">%s</p>' % (klass, html.escape(words, quote=True))


def _owners_html(payload):
    if not isinstance(payload, dict) or payload.get("fetched") is not True:
        return '<div class="roster-none">this PC has not fetched a roster yet</div>'
    by = {}
    for row in payload.get("owners") or []:
        if isinstance(row, dict) and row.get("owner") in OWNERS:
            by[row["owner"]] = row
    parts = []
    for owner in OWNERS:
        row = by.get(owner)
        who = html.escape(owner, quote=True)
        if row is None:
            parts.append('<section class="roster-owner"><h3>%s</h3><p>%s was not in this fetch</p></section>'
                         % (who, who))
            continue
        if row.get("corrupt") is True:
            parts.append('<section class="roster-owner"><h3>%s</h3><p>roster is corrupt and rows are not shown</p></section>'
                         % who)
            continue
        if row.get("published") is not True:
            lines = []
            for section in SECTIONS:
                said = never_published_line(owner, section)
                lines.append("<li>%s</li>" % html.escape(said, quote=True))
            parts.append('<section class="roster-owner"><h3>%s</h3><ul>%s</ul></section>'
                         % (who, "".join(lines)))
            continue
        parts.append(_published_html(owner, row, payload.get("now")))
    return "".join(parts)


def _published_html(owner, row, now_ms):
    who = html.escape(owner, quote=True)
    state, _words = _ago(row.get("t"), now_ms)
    when = row_age_words(row, now_ms)   # REG-3037 - the row's store, named; "stale" no longer calls an unchanged row old
    klass = "roster-owner"
    if state == "stale":
        klass += " roster-stale"
    blocks = ['<section class="%s"><h3>%s</h3><p>%s</p>' % (klass, who, html.escape(when, quote=True))]
    sig_class, sig_said = signature_words(row)
    blocks.append('<p class="%s">%s</p>' % (sig_class, html.escape(sig_said, quote=True)))
    sections = row.get("sections") if isinstance(row.get("sections"), dict) else {}
    for name in SECTIONS:
        sec = sections.get(name)
        if not isinstance(sec, dict):
            said = never_published_line(owner, name)
            blocks.append("<p>%s</p>" % html.escape(said, quote=True))
            continue
        sec_state, sec_words = _ago(sec.get("asOf"), now_ms)
        label = html.escape(name, quote=True)
        sec_said = _age_words(sec_state, sec_words)
        if sec_said:
            age = "as of " + sec_said
        else:
            age = "age unknown"
        sec_class = "roster-stale" if sec_state == "stale" else "roster-sec"
        blocks.append('<div class="%s"><b>%s</b> %s' % (sec_class, label, html.escape(age, quote=True)))
        counted = _count_text(sec.get("counts"))
        if counted:
            blocks.append(" <span>%s</span>" % html.escape(counted, quote=True))
        rows = sec.get("rows") if isinstance(sec.get("rows"), list) else []
        if rows:
            items = []
            for item in rows:
                line = _row_line(item, now_ms)
                if line:
                    items.append("<li>%s</li>" % html.escape(line, quote=True))
            if items:
                blocks.append("<ul>%s</ul>" % "".join(items))
        blocks.append("</div>")
    blocks.append("</section>")
    return "".join(blocks)
