# -*- coding: utf-8 -*-
"""v3860 (#230) - ONE per-machine sync status that the recorder, the shadow reader and the Shelf all read.

His ask, 2026-11-03: "make sure the shadow reader recorder and the shelf and everything is synced meaning a joined logic
so its reading and registering the same for a status so we know". The ALT filmed every hour while its Shelf showed 08:00:
the recorder, the hourly seal, the digest publish and the Shelf's list each kept its own clock and none compared them.

judge(facts, now_ms) is pure: facts hold epoch-ms stamps (None = UNKNOWN, never guessed):
  gameUp        True/False/None  - the shadow watch's one judge of the game on screen
  frameAt       last frame the recorder wrote (frames/eye.jpg or live.*)
  rollingSince  the reel now rolling began (None = none rolling)
  rotateAfterS  the rollover limit
  sealAt        last reel the hourly seal CLOSED
  sealFailAt    last time a seal measured the reel still rolling
  publishAt     last digest the site stored (what every shadow's Shelf reads)
  shelfAt       when this PC's Shelf list was last built
  shelfNewestAt newest session start on that list
-> {level: "ok"|"warn"|"red"|"unknown", say, lanes:{recorder, seal, publish, shelf}, why:[...]}"""

RECORDER_SILENT_MS = 2 * 60 * 1000
SEAL_LATE_MS = 15 * 60 * 1000
PUBLISH_BEHIND_MS = 30 * 60 * 1000
SHELF_BEHIND_MS = 5 * 60 * 1000

_RANK = {"ok": 0, "unknown": 1, "warn": 2, "red": 3}


def _i(v):
    try:
        return int(v) if v is not None and not isinstance(v, bool) else None
    except (TypeError, ValueError):
        return None


def _mins(ms):
    return "%d min" % max(0, int(ms // 60000))


def judge(facts, now_ms):
    f = facts if isinstance(facts, dict) else {}
    now = int(now_ms)
    lanes, why = {}, []
    game = f.get("gameUp")
    frame, rolling = _i(f.get("frameAt")), _i(f.get("rollingSince"))
    seal, fail = _i(f.get("sealAt")), _i(f.get("sealFailAt"))
    pub, shelf, newest = _i(f.get("publishAt")), _i(f.get("shelfAt")), _i(f.get("shelfNewestAt"))
    limit_ms = int(float(f.get("rotateAfterS") or 3600) * 1000)

    # recorder: silent while the game is up is RED; with the game down silence is fine
    if game is True:
        if frame is None:
            lanes["recorder"] = "red"; why.append("the game is up and the recorder has written no frame")
        elif now - frame > RECORDER_SILENT_MS:
            lanes["recorder"] = "red"; why.append("the game is up and the recorder has been silent %s" % _mins(now - frame))
        else:
            lanes["recorder"] = "ok"
    else:
        lanes["recorder"] = "ok" if game is False else "unknown"

    # seal: a reel past its hour + grace, or a failed seal newer than the last good one
    if fail is not None and (seal is None or fail > seal):
        lanes["seal"] = "red"; why.append("the hourly seal failed %s ago and has not closed a reel since" % _mins(now - fail))
    elif rolling is not None and now - rolling > limit_ms + SEAL_LATE_MS:
        lanes["seal"] = "red"; why.append("a reel has rolled %s without a seal" % _mins(now - rolling))
    else:
        lanes["seal"] = "ok" if seal is not None or rolling is not None else "unknown"

    # publish: the site (every shadow's Shelf) must hold the last sealed reel
    if seal is not None and (pub is None or seal - pub > PUBLISH_BEHIND_MS):
        lanes["publish"] = "warn"; why.append("shadows read sessions %s behind the last sealed reel" % (
            "never published" if pub is None else _mins(seal - pub)))
    else:
        lanes["publish"] = "ok" if pub is not None else "unknown"

    # shelf: this PC's list must be built after the newest reel began
    if shelf is None:
        lanes["shelf"] = "unknown"
    elif rolling is not None and rolling - shelf > SHELF_BEHIND_MS:
        lanes["shelf"] = "warn"; why.append("the Shelf's list is %s older than the reel now rolling" % _mins(rolling - shelf))
    elif rolling is not None and newest is not None and rolling - newest > SHELF_BEHIND_MS and shelf > rolling + SHELF_BEHIND_MS:
        lanes["shelf"] = "warn"; why.append("the Shelf does not list the reel now rolling")
    else:
        lanes["shelf"] = "ok"

    level = max(lanes.values(), key=lambda v: _RANK[v]) if lanes else "unknown"
    say = "in sync" if level == "ok" else ("; ".join(why) if why else "some lanes could not be read")
    return {"level": level, "say": say, "lanes": lanes, "why": why, "at": now}
