# -*- coding: utf-8 -*-
"""v3850 (Elad 17:51/17:53 2026-10-31) - ONE PRESENCE FUNCTION FOR EVERY SURFACE.

Dean's laptop slept at ~17:14 IDT. 33 min later the Fleet still listed him online and the Dean shadow bar said
"online now": the site keeps a presence key alive PRESENCE_TTL (40 min) after its last rewrite, and the shadow bar
asked only "is he in the online list". The rail's card used its own age rule (2*900+240 s). Two rules, two answers.

Now there is one: presence_of(row, listed_online, now_ms). /api/fleet stamps it on every row as `presence`; the
shadow banner (console_snapshot.online_of) and the UI's _fleetPresence only read it.

ONLINE = the console heartbeat is fresh OR the background recorder reports itself alive and fresh (game up, console
down -> "online · recording"). OFFLINE = both stale, worded with the newest last-seen age. A live console rewrites its
presence row at least every REFRESH_S (functions/api/console.js) and beacons every BEACON_S, so older than
STALE_AFTER_S has missed a refresh. A row with no readable time is UNKNOWN, never online. [[unknown-stays-unknown]]
"""
import time

#: v3862 Workers Paid: functions/api/console.js REFRESH_S 220 (was 900), so a row older than ~8.7 min (was 20) has
#: missed a refresh. The worst age of a LIVE row is one beacon (240) + the fleet's 60 s cache; the recorder's
#: keepalive posts every 5 min (300 + 60). test_every_surface_asks_one_presence holds REFRESH_S equal to the worker's.
REFRESH_S = 220
BEACON_S = 240
STALE_AFTER_S = REFRESH_S + BEACON_S + 60   # 520 s
#: worst age of a live heartbeat (one beacon + the fleet's 60 s cache). Older than this, and not
#: yet past STALE_AFTER_S, is late (the lamp's teal): check-ins are late, the PC is not yet offline.
FRESH_UNTIL_S = BEACON_S + 60   # 300 s


def _parse_iso_ms(s):
    if isinstance(s, (int, float)) and not isinstance(s, bool):
        return int(s)
    if not isinstance(s, str) or not s:
        return None
    try:
        from datetime import datetime
        return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp() * 1000)
    except Exception:
        return None


def ago_words(sec):
    m = int(max(0, sec) // 60)
    if m < 1:
        return "under 1 min ago"
    if m < 120:
        return "%d min ago" % m
    if m < 48 * 60:
        return "%d hr ago" % (m // 60)
    return "%d days ago" % (m // 1440)


def presence_of(row, listed_online, now_ms=None):
    """-> {state: online|offline|unknown, online: True|False|None, via: console|recorder|None, ageS, words}. Pure."""
    now = int(time.time() * 1000) if now_ms is None else int(now_ms)
    row = row if isinstance(row, dict) else {}
    con = _parse_iso_ms(row.get("t"))
    rec = row.get("recorder") if isinstance(row.get("recorder"), dict) else {}
    rec_t = _parse_iso_ms(rec.get("t")) if rec.get("alive") is True else None
    ages = {}
    if con is not None and con < now + 60000:
        ages["console"] = max(0.0, (now - con) / 1000.0)
    if rec_t is not None and rec_t < now + 60000:
        ages["recorder"] = max(0.0, (now - rec_t) / 1000.0)
    base = {"staleAfterS": STALE_AFTER_S, "freshUntilS": FRESH_UNTIL_S}
    if not ages:
        return dict(base, state="unknown", online=None, via=None, ageS=None,
                    words="presence UNKNOWN (no readable last check-in)")
    if listed_online is True and ages.get("console", 1e18) <= STALE_AFTER_S:
        return dict(base, state="online", online=True, via="console", ageS=round(ages["console"], 1), words="online now")
    if ages.get("recorder", 1e18) <= STALE_AFTER_S:
        return dict(base, state="online", online=True, via="recorder", ageS=round(ages["recorder"], 1),
                    words="online \u00b7 recording")
    newest = min(ages.values())
    return dict(base, state="offline", online=False, via=None, ageS=round(newest, 1),
                words="offline \u00b7 last seen " + ago_words(newest))


def stamp_fleet(fl, now_ms=None):
    """Stamp `presence` on every row of an /api/fleet payload, in place. -> fl"""
    if not isinstance(fl, dict):
        return fl
    for key, listed in (("online", True), ("offline", False)):
        for row in fl.get(key) or []:
            if isinstance(row, dict):
                row["presence"] = presence_of(row, listed, now_ms)
    return fl
