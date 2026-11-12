# -*- coding: utf-8 -*-
"""#208 (his ruling 2026-11-12 ~23:50 IST: "Pull to the Mac") - SHADOW SESSIONS PLAY EVERY FRAME, FROM THE MAC'S OWN COPY.

His ask (via GrokBot #230 6836226405): "shadow mode must render full screen and ALL frames of that session locally, and show
the game recording from when play starts". Each console listens only on its own PC and the site carries 3 small key frames a
session, so the frames come to the Mac: after a session is done on a PC, the Mac copies its frames over the network it already
reaches, and the shadow Theatre plays them from that copy.

MEASURED 11-12 on the work ALT's newest 16 reels: 1 to 1,558 frames, up to 528 MB a reel, ~1.2 GB in all - so the copy is
held to a BYTE budget, newest first, and never takes the Mac's free space under his 8 GB floor. Nothing on a PC is ever
deleted or written by this module; the PC keeps its reel.

Here: the pure planner (which reels are done, which frames to copy) - the lane, the ssh listing and the copy sit on top.
Every answer that cannot be measured is None (UNKNOWN), never an empty list that reads as "nothing to copy".
"""
import json
import os

QUIET_S = 600                       # a reel whose newest frame is 10+ min old is no longer being written
BUDGET_BYTES = 3 * 1024 ** 3        # the Mac's shadow copies, all PCs together
FLOOR_BYTES = 8 * 1024 ** 3         # his ON AIR floor: the copy never takes free space under it
CONFIG_NAME = ".shadow_pull.json"   # gitignored: each PC's ssh target never enters the public repo
REEL_PREFIX = "reel_s_"


def done_reels(listing, now_s, rolling=None, quiet_s=QUIET_S):
    """-> [reel] whose writing has ended, newest first; None when the listing is UNKNOWN.

    listing: [{"reel": name, "files": [{"name", "size", "mtime"}]}] as one PC reported it. A reel is done when it is not the
    PC's rolling reel and its newest frame is at least `quiet_s` old. A reel with no frames is not a session to copy."""
    if not isinstance(listing, list):
        return None
    out = []
    for r in listing:
        if not isinstance(r, dict):
            continue
        name = r.get("reel")
        files = r.get("files")
        if not (isinstance(name, str) and name.startswith(REEL_PREFIX)) or not isinstance(files, list) or not files:
            continue
        if rolling and name == rolling:
            continue
        try:
            newest = max(float(f.get("mtime")) for f in files if isinstance(f, dict))
        except (TypeError, ValueError):
            continue                 # a frame without a readable time: its reel's state is UNKNOWN, never copied on a guess
        if now_s - newest >= quiet_s:
            out.append((newest, name))
    return [n for _t, n in sorted(out, reverse=True)]


def plan(listing, done, have, budget_bytes=BUDGET_BYTES, held_bytes=0, free_bytes=None, floor_bytes=FLOOR_BYTES):
    """-> {"copy": [(reel, [file names])], "bytes": n, "why": str}; None when the Mac's free space is UNKNOWN.

    `done`: done_reels() newest first. `have`: {reel: set(file names already copied)}. `held_bytes`: the copies already on
    the Mac. A reel is copied whole or not started (a half reel plays as a hole), newest first, while the budget and the
    floor both hold; a reel already complete costs nothing; a reel bigger than the room left stops the walk (older ones
    are older still - the newest are what he plays)."""
    if free_bytes is None:
        return None
    by = {r.get("reel"): r for r in (listing or []) if isinstance(r, dict)}
    room = min(budget_bytes - held_bytes, free_bytes - floor_bytes)
    out, total, why = [], 0, "every done session is already here"
    for reel in done or []:
        files = by.get(reel, {}).get("files") or []
        got = (have or {}).get(reel) or set()
        want = [f for f in files if isinstance(f, dict) and f.get("name") not in got]
        if not want:
            continue
        cost = sum(int(f.get("size") or 0) for f in want)
        if cost > room - total:
            why = ("the budget (%d MB) is spent" % (budget_bytes // (1024 ** 2))
                   if budget_bytes - held_bytes <= free_bytes - floor_bytes
                   else "his 8 GB free floor would be crossed") + " - %s and older wait" % reel
            break
        out.append((reel, sorted(f.get("name") for f in want)))
        total += cost
        why = "%d session(s) to copy" % len(out)
    return {"copy": out, "bytes": total, "why": why}


def config_load(path):
    """-> {label: {"ssh": target, ...}} | {} (no file: no PC named yet) | None (a file that will not read: UNKNOWN)"""
    try:
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
    except FileNotFoundError:
        return {}
    except (OSError, ValueError):
        return None
    if not isinstance(d, dict):
        return None
    return {k: v for k, v in d.items() if isinstance(k, str) and isinstance(v, dict) and isinstance(v.get("ssh"), str)}


def local_have(root):
    """-> {reel: set(file names)} of the copies under root/<reel>/; {} when nothing is copied yet"""
    out = {}
    if not os.path.isdir(root):
        return out
    for reel in os.listdir(root):
        if not reel.startswith("reel_s_"):      # a literal prefix: the unkeyable-laws ratchet keys a listing by it
            continue
        d = os.path.join(root, reel)
        if os.path.isdir(d):
            out[reel] = set(n for n in os.listdir(d) if n.endswith(".jpg"))
    return out
