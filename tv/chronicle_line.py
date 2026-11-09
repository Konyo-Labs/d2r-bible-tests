# -*- coding: utf-8 -*-
"""v3890 (#184, REG-3512) - A CHRONICLE FIND IS THE GREEN LINE UNDER THE RED "UNIDENTIFIED".

His rule, 11-09: "FOUND should be chronicle found meaning the keyword in green for unidentified items before being
identified". His screenshots of the game (Greaves, Chaos Armor, a Halberd, a Jewel; a Ring without it) show one
shape on every unidentified set or unique item, ethereal or not: the red "Unidentified" line, and DIRECTLY under it
the green "Eligible for Chronicle" line, both centred in the tooltip's dark box. An unidentified item that is not
eligible (the Ring) has the red line and no green line under it.

session_route.chronicle_eligible needs a colour for that line, and no reader in the tree ever wrote one (the journal
held 0 "Unidentified" rows in ~33,000), so every session's chronicle count stayed UNKNOWN. This reads the PIXELS of
one frame instead of text - no OCR, no model:

  * red text pixels and green text pixels, each grouped into text lines (runs joined across rows, then words on one
    row joined into a line);
  * a line is text only when it is short and wide (a word, not a health globe) and sits on the tooltip's dark ground;
  * a find is a red line with a green line directly under it (a gap under one line height), on the same centre, the
    green one about 1.8x as wide ("Eligible for Chronicle" over "Unidentified": measured 1.76 on his screenshot).

read(path_or_image) -> {"checked": True, "chronicle": witness-or-None} - the witness names both boxes in the frame's
own pixels so a person can look; {"checked": False, "why": ...} when the frame could not be read (UNKNOWN, never a
measured "no"). Pure besides opening the image; numpy + PIL, as char_select already needs.
"""
import os

# The colours, measured on his screenshot: "Unidentified" (225, 111, 107), "Eligible for Chronicle" (113, 238, 76),
# "Hold Shift to Compare" (166, 166, 166). The bands are wide on purpose: a stream (Boosteroid, GeForce NOW) and a
# JPEG reel darken and blur a 1-px stroke, and the line SHAPE below is what makes the read specific, not the hue.
RED_MIN, RED_OVER_G, RED_OVER_B, RED_MAX_G = 100, 35, 30, 160
GREEN_MIN, GREEN_OVER_R, GREEN_OVER_B = 95, 35, 45
DARK = 72                    # the tooltip's ground: every channel under this
WIDTH_RATIO = (1.35, 2.4)    # green width over red width; 1.76 measured
RED_ASPECT = (5.0, 17.0)     # "Unidentified": width over height, ~10 measured
GREEN_ASPECT = (9.0, 30.0)   # "Eligible for Chronicle": ~17 measured
MIN_H, MAX_H_FRAC = 4, 0.10  # a text line is 4 px tall at the least, and under 10% of the frame
MIN_DARK_GROUND = 0.40       # share of a line's non-text pixels that are the tooltip's dark ground


def _np():
    import numpy as np
    return np


def _array(src):
    np = _np()
    from PIL import Image
    im = src if hasattr(src, "convert") else Image.open(src)
    if not hasattr(src, "convert"):
        try:   # a big frame decodes at half size - a text line stays 7+ px tall at 1440 and up
            if im.size[0] >= 1600:
                im.draft("RGB", (im.size[0] // 2, im.size[1] // 2))
        except Exception:
            pass
    return np.asarray(im.convert("RGB"), dtype=np.int16)


def masks(a):
    """-> (red, green, dark) boolean masks of an RGB int array."""
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    red = (R >= RED_MIN) & (R - G >= RED_OVER_G) & (R - B >= RED_OVER_B) & (G <= RED_MAX_G)
    green = (G >= GREEN_MIN) & (G - R >= GREEN_OVER_R) & (G - B >= GREEN_OVER_B)
    dark = a.max(axis=-1) < DARK
    return red, green, dark


def _runs(mask, bridge=1):
    """Horizontal runs of a mask, gaps of up to 2*bridge px closed: -> list of (y, x0, x1) (x1 exclusive)."""
    np = _np()
    h, w = mask.shape
    m = mask.astype(np.int32)
    c = np.zeros((h, w + 1), dtype=np.int32)
    c[:, 1:] = np.cumsum(m, axis=1)
    lo = np.clip(np.arange(w) - bridge, 0, w)
    hi = np.clip(np.arange(w) + bridge + 1, 0, w)
    dil = (c[:, hi] - c[:, lo]) > 0
    pad = np.zeros((h, w + 2), dtype=np.int8)
    pad[:, 1:-1] = dil
    d = np.diff(pad, axis=1)
    ys, xs = np.nonzero(d == 1)
    ye, xe = np.nonzero(d == -1)
    out = []
    for y, x0, x1 in zip(ys.tolist(), xs.tolist(), xe.tolist()):
        out.append((y, max(0, x0 + bridge), max(x0 + bridge + 1, x1 - bridge)))
    # np.nonzero walks row-major, so starts and ends pair up in order
    return out


def _blobs(mask, bridge=1):
    """Connected blobs of a mask (runs joined where they overlap on neighbouring rows) -> [x0, y0, x1, y1] boxes."""
    runs = _runs(mask, bridge)
    if not runs:
        return []
    parent = list(range(len(runs)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    by_row = {}
    for i, (y, x0, x1) in enumerate(runs):
        by_row.setdefault(y, []).append(i)
    for i, (y, x0, x1) in enumerate(runs):
        for j in by_row.get(y - 1, ()):
            _, a0, a1 = runs[j]
            if a0 < x1 + bridge and x0 < a1 + bridge:
                ri, rj = root(i), root(j)
                if ri != rj:
                    parent[ri] = rj
    box = {}
    for i, (y, x0, x1) in enumerate(runs):
        r = root(i)
        b = box.get(r)
        if b is None:
            box[r] = [x0, y, x1, y + 1]
        else:
            b[0], b[1], b[2], b[3] = min(b[0], x0), min(b[1], y), max(b[2], x1), max(b[3], y + 1)
    return list(box.values())


def _lines(boxes):
    """Words on one row joined into a text line: blobs whose rows overlap by half and whose gap is under 3 line
    heights merge (a blurred stream loses whole thin letters, so a word can arrive in pieces). -> [x0, y0, x1, y1] boxes, smallest first in y."""
    bs = sorted([list(b) for b in boxes if b[3] - b[1] >= 2], key=lambda b: (b[1], b[0]))
    merged = True
    while merged:
        merged = False
        out = []
        for b in bs:
            for o in out:
                h = max(b[3] - b[1], o[3] - o[1])
                ov = min(b[3], o[3]) - max(b[1], o[1])
                gap = max(b[0], o[0]) - min(b[2], o[2])
                if ov >= 0.5 * min(b[3] - b[1], o[3] - o[1]) and gap <= 3.0 * h:
                    o[0], o[1], o[2], o[3] = min(o[0], b[0]), min(o[1], b[1]), max(o[2], b[2]), max(o[3], b[3])
                    merged = True
                    break
            else:
                out.append(b)
        bs = out
    return sorted(bs, key=lambda b: (b[1], b[0]))


def _text_line(b, mask, dark, frame_h, aspect):
    """Is this box a line of tooltip text: a word's shape, on the dark ground? -> facts dict or None."""
    x0, y0, x1, y1 = b
    h, w = y1 - y0, x1 - x0
    if h < MIN_H or h > MAX_H_FRAC * frame_h or not (aspect[0] <= w / float(h) <= aspect[1]):
        return None
    lit = mask[y0:y1, x0:x1]
    n_lit = int(lit.sum())
    fill = n_lit / float(w * h)
    if not (0.06 <= fill <= 0.65):
        return None
    rest = w * h - n_lit
    ground = int((dark[y0:y1, x0:x1] & ~lit).sum()) / float(max(1, rest))
    if ground < MIN_DARK_GROUND:
        return None
    return {"box": [int(x0), int(y0), int(x1), int(y1)], "h": int(h), "w": int(w),
            "fill": round(fill, 3), "ground": round(ground, 3)}


GREEN_FLOOR = 25             # a frame with fewer bright-green pixels than this holds no green line: done in one mask


def find(a):
    """The chronicle witness in an RGB int array, or None. -> {"red": facts, "green": facts, "ratio", "gap"}."""
    G = a[..., 1]
    if int(((G >= GREEN_MIN) & (G - a[..., 0] >= GREEN_OVER_R) & (G - a[..., 2] >= GREEN_OVER_B)).sum()) < GREEN_FLOOR:
        return None
    red, green, dark = masks(a)
    fh = a.shape[0]
    # the green line is the rare one in a game frame: look for it first, and only then for the red line above it
    greens = [t for t in (_text_line(b, green, dark, fh, GREEN_ASPECT) for b in _lines(_blobs(green))) if t]
    if not greens:
        return None
    reds = [t for t in (_text_line(b, red, dark, fh, RED_ASPECT) for b in _lines(_blobs(red))) if t]
    best = None
    for r in reds:
        rx0, ry0, rx1, ry1 = r["box"]
        rcx = (rx0 + rx1) / 2.0
        for g in greens:
            gx0, gy0, gx1, gy1 = g["box"]
            gap = gy0 - ry1
            if gap < 0 or gap > 1.0 * r["h"] + 3:
                continue
            if not (0.65 <= g["h"] / float(r["h"]) <= 1.5):
                continue
            ratio = g["w"] / float(r["w"])
            if not (WIDTH_RATIO[0] <= ratio <= WIDTH_RATIO[1]):
                continue
            if abs((gx0 + gx1) / 2.0 - rcx) > 0.08 * g["w"] + 3:
                continue
            w = {"red": r, "green": g, "ratio": round(ratio, 3), "gap": int(gap)}
            if best is None or abs(ratio - 1.76) < abs(best["ratio"] - 1.76):
                best = w
    return best


def read(src):
    """One frame (a path or a PIL image) -> {"checked": True, "chronicle": witness-or-None, "wh": [w, h]}, or
    {"checked": False, "why": ...} when the frame could not be opened - UNKNOWN, never a measured "no line"."""
    try:
        a = _array(src)
    except Exception as e:
        return {"checked": False, "why": "%s: %s" % (type(e).__name__, str(e)[:120])}
    out = {"checked": True, "wh": [int(a.shape[1]), int(a.shape[0])], "chronicle": None}
    try:
        out["chronicle"] = find(a)
    except Exception as e:
        return {"checked": False, "why": "%s: %s" % (type(e).__name__, str(e)[:120])}
    # v3890 (#188) - the same decoded frame answers "is this D2R itself": its logo, its title, its character select, or
    # in a game (d2r_screens). One decode, two questions.
    try:
        import d2r_screens as _DS
        out["screen"] = _DS.screen_of(src if isinstance(src, str) else None, array=a)[0]
    except Exception:
        out["screen"] = None
    return out


# ===================================================================================================== THE LANE
# Every reel frame this PC films is walked ONCE, newest reel first, by a cursor per reel - the character learner's
# shape (char_select.tick) and the same 45 s ride. A frame with the line is banked with its witness and COPIED to
# frames/chronicle, so the proof outlives the reel FIFO. A session's chronicle count is then the distinct items its
# window holds - and UNKNOWN (None) until every reel that filmed the window has been walked.
LEDGER_NAME = ".chronicle_lines.json"
TICK_BUDGET_S = 6.0          # wall time one tick may spend (a 45 s loop: ~13% of one core while there is a backlog)
HITS_KEEP = 2000             # the newest banked sightings
REELS_KEEP = 3000            # reel records kept after the FIFO deleted the reel: they are what says a window was walked
PROOF_KEEP = 300             # proof frames kept in frames/chronicle, newest first
LIVE_REELS = 2               # the newest reels may still grow: they are never marked done
INVENTORY_SIDE = 0.5         # the tooltip of an item in the inventory sits right of the frame's middle; left of it is the
                             # stash, the cube, a vendor or a trade - items that were not farmed this run (session_route)
SAME_ITEM_FRAC = 0.03        # two sightings whose red line sits within 3% of the frame of each other ...
SAME_ITEM_GAP_MS = 120000    # ... and no more than two minutes apart are ONE item hovered twice

HERE = os.path.dirname(os.path.abspath(__file__))


def _frame_ts(p):
    import re
    m = re.search(r"f_(\d{10,})\.(?:jpg|jpeg|png)$", os.path.basename(str(p)), re.I)
    return int(m.group(1)) if m else None


def _world():
    """His tree, or the fixture's when TV_HIST names one (char_select._world - called, not copied)."""
    try:
        import char_select as _cs
        return _cs._world()
    except Exception:
        return HERE


def ledger_path():
    return os.environ.get("TV_CHRONICLE_LINES") or os.path.join(_world(), LEDGER_NAME)


def proof_dir():
    return os.path.join(os.path.dirname(ledger_path()), "frames", "chronicle")


def hist_root():
    try:
        import char_select as _cs
        return _cs.hist_root()
    except Exception:
        return os.environ.get("TV_HIST") or os.path.join(HERE, "frames", "hist")


def _empty():
    return {"v": 1, "reels": {}, "hits": [],
            "stats": {"ticks": 0, "frames": 0, "hits": 0, "unread": 0, "lastTs": None, "lastWhy": ""}}


def load(path=None):
    """-> the ledger, a fresh one when there is none yet, or None when it exists and cannot be read (UNKNOWN)."""
    import json
    p = path or ledger_path()
    if not os.path.exists(p):
        return _empty()
    try:
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception:
        return None
    if not isinstance(d, dict) or not isinstance(d.get("reels"), dict) or not isinstance(d.get("hits"), list):
        return None
    base = _empty()
    base["stats"].update(d.get("stats") or {})
    d["stats"] = base["stats"]
    return d


_CACHE = {"key": None, "d": None}


def load_cached():
    """load(), kept while the ledger's size and mtime stand still: a digest asks once per session."""
    p = ledger_path()
    try:
        st = os.stat(p)
        key = (p, st.st_size, st.st_mtime)
    except OSError:
        key = (p, None, None)
    if _CACHE["key"] != key:
        _CACHE["key"], _CACHE["d"] = key, load(p)
    return _CACHE["d"]


def cache_key():
    """What can flip a sealed session's answer: (sightings banked, reels walked to their end). None: no ledger read."""
    d = load_cached()
    if d is None:
        return None
    return (len(d.get("hits") or []), sum(1 for rs in (d.get("reels") or {}).values() if rs.get("done")))


def save(d, path=None):
    """Written to a temp file and moved over the ledger: a reader never meets half a file."""
    import json
    p = path or ledger_path()
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(d, fh)
    os.replace(tmp, p)


def side_of(hit):
    """'inventory' when the tooltip's red line is centred right of the frame's middle, else 'left-panel'."""
    try:
        w = float(hit["wh"][0])
        cx = (hit["red"][0] + hit["red"][2]) / 2.0 / w
    except Exception:
        return None
    return "inventory" if cx >= INVENTORY_SIDE else "left-panel"


def _keep_proof(p, reel):
    """Copy the frame beside the ledger so the proof outlives the reel. -> (name or None, why)."""
    import shutil
    dst_dir = proof_dir()
    try:
        os.makedirs(dst_dir, exist_ok=True)
        name = "%s__%s" % (reel, os.path.basename(p))
        shutil.copy2(p, os.path.join(dst_dir, name))
        kept = sorted((f for f in os.listdir(dst_dir) if f.lower().endswith(".jpg")),
                      key=lambda f: _frame_ts(f) or 0, reverse=True)
        for old in kept[PROOF_KEEP:]:
            try:
                os.remove(os.path.join(dst_dir, old))
            except OSError:
                pass
        return name, ""
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, str(e)[:120])


def _bank(d, p, reel, r):
    w = r["chronicle"]
    hit = {"ts": _frame_ts(p), "reel": reel, "frame": os.path.basename(p), "wh": list(r["wh"]),
           "red": list(w["red"]["box"]), "green": list(w["green"]["box"]), "ratio": w["ratio"]}
    hit["side"] = side_of(hit)
    hit["proof"], why = _keep_proof(p, reel)
    if why:
        hit["proofWhy"] = why
    d["hits"].append(hit)
    del d["hits"][:-HITS_KEEP]
    return hit


def tick(root=None, budget_s=TICK_BUDGET_S, clock=None, reader=None, now_ms=None):
    """One bounded pass over the reels, newest first: every frame not yet walked is read once. -> status dict.

    A frame that will not open is a read that did not happen: the newest frame of a live reel waits for the next tick
    (it may still be being written); any other is passed, counted and said. A reel the FIFO deleted keeps its record,
    because the record is what says its window was walked."""
    import glob
    import time as _time
    clock = clock or _time.time
    reader = reader or read
    d = load()
    if d is None:
        return {"ok": False, "why": "the ledger could not be read - UNKNOWN, nothing written"}
    root = root or hist_root()
    t0 = clock()
    st = d["stats"]
    st["ticks"] = int(st.get("ticks") or 0) + 1
    reels = sorted(glob.glob(os.path.join(root, "reel_*")), reverse=True)
    alive = set(os.path.basename(r) for r in reels)
    for name, rs in d["reels"].items():
        if name not in alive:
            rs["gone"] = True
    if len(d["reels"]) > REELS_KEEP:
        for name in sorted(d["reels"])[:len(d["reels"]) - REELS_KEEP]:
            d["reels"].pop(name, None)
    scanned = new_hits = unread = 0
    why = ""
    for k, rd in enumerate(reels):
        name = os.path.basename(rd)
        rs = d["reels"].setdefault(name, {"pos": 0})
        rs.pop("gone", None)
        if rs.get("done"):
            continue
        frames = sorted(glob.glob(os.path.join(rd, "f_*.jpg")))
        rs["frames"] = len(frames)
        if frames:
            rs["firstTs"], rs["lastTs"] = _frame_ts(frames[0]), _frame_ts(frames[-1])
        i = int(rs.get("pos") or 0)
        while i < len(frames):
            if clock() - t0 > budget_s:
                why = "tick budget spent"
                break
            p = frames[i]
            r = reader(p)
            if not r.get("checked"):
                if i == len(frames) - 1 and k < LIVE_REELS:
                    break                              # the live edge: it may still be being written
                unread += 1
                st["lastWhy"] = "%s/%s not read: %s" % (name, os.path.basename(p), r.get("why"))
            else:
                if r.get("chronicle"):
                    _bank(d, p, name, r)
                    new_hits += 1
                if r.get("screen"):
                    _mark(rs, _frame_ts(p), r["screen"])
            i += 1
            rs["pos"] = i
            scanned += 1
            ts = _frame_ts(p)
            if ts:
                rs["scannedTs"] = max(int(rs.get("scannedTs") or 0), ts)
        if why:
            break
        if k >= LIVE_REELS and int(rs.get("pos") or 0) >= len(frames):
            rs["done"] = True
    st["frames"] = int(st.get("frames") or 0) + scanned
    st["hits"] = int(st.get("hits") or 0) + new_hits
    st["unread"] = int(st.get("unread") or 0) + unread
    st["lastTs"] = int(now_ms if now_ms is not None else clock() * 1000)
    save(d)
    return {"ok": True, "scanned": scanned, "hits": new_hits, "unread": unread, "why": why,
            "owedReels": owed(d, alive)}


MARKS_KEEP = 120   # a reel's door marks (logo, title, character select) kept in order: the chain needs the first few


def _mark(rs, ts, kind):
    """v3890 (#188) - count a D2R screen in this reel's film; keep the door marks in order and re-read the chain."""
    c = rs.setdefault("d2r", {})
    c[kind] = int(c.get(kind) or 0) + 1
    if isinstance(ts, int):
        if not isinstance(rs.get("firstD2rTs"), int) or ts < rs["firstD2rTs"]:
            rs["firstD2rTs"] = ts
        if not isinstance(rs.get("lastD2rTs"), int) or ts > rs["lastD2rTs"]:
            rs["lastD2rTs"] = ts
        if kind in ("logo", "title", "char-select"):
            m = rs.setdefault("marks", [])
            if len(m) < MARKS_KEEP:
                m.append([ts, kind])
                try:
                    import d2r_screens as _DS
                    rs["chain"] = _DS.chain(m)
                except Exception:
                    pass


def reel_shows_d2r(name, d=None):
    """v3890 (#188) - did this reel's film show D2R itself? -> True (its logo, title, character select or the in-game
    orbs, at least once), False (the lane walked every frame to the reel's end and saw none of them), None (not walked
    to its end yet, no frames, or no ledger - UNKNOWN, never "not the game")."""
    d = d if d is not None else load_cached()
    if d is None:
        return None
    rs = (d.get("reels") or {}).get(name)
    if not isinstance(rs, dict):
        return None
    if sum(int(v or 0) for v in (rs.get("d2r") or {}).values()) > 0:
        return True
    n = int(rs.get("frames") or 0)
    if rs.get("done") and n > 0 and int(rs.get("pos") or 0) >= n:
        return False
    return None


LIVE_GAME_MS = 5 * 60 * 1000   # the live film shows the game when a D2R frame is among its last five walked minutes


def live_game(name, d=None, fresh_ms=LIVE_GAME_MS):
    """v3890 (#189) - does the reel rolling NOW show the game? -> True (a D2R screen - logo, title, character select,
    lobby, the in-game orbs - within the last fresh_ms of the film the lane has walked), False (the lane walked at least
    fresh_ms of this reel's film since the last D2R frame, or since its start), None (not walked that far yet)."""
    d = d if d is not None else load_cached()
    rs = ((d or {}).get("reels") or {}).get(name)
    if not isinstance(rs, dict):
        return None
    walked = rs.get("scannedTs")
    if not isinstance(walked, int):
        return None
    last = rs.get("lastD2rTs")
    if isinstance(last, int) and walked - last <= fresh_ms:
        return True
    since = last if isinstance(last, int) else rs.get("firstTs")
    if isinstance(since, int) and walked - since >= fresh_ms:
        return False
    return None


def game_door(name, d=None):
    """v3890 (#188) - where this reel entered the game (d2r_screens.chain), or None."""
    d = d if d is not None else load_cached()
    rs = ((d or {}).get("reels") or {}).get(name)
    return rs.get("chain") if isinstance(rs, dict) else None


def owed(d, alive=None):
    """Reels on this machine whose frames are not all walked yet (a live reel counts while it has unread frames)."""
    n = 0
    for name, rs in (d.get("reels") or {}).items():
        if alive is not None and name not in alive:
            continue
        if not rs.get("done") and int(rs.get("pos") or 0) < int(rs.get("frames") or 0):
            n += 1
    if alive is not None:
        n += len([a for a in alive if a not in (d.get("reels") or {})])
    return n


def finds(hits, t0=None, t1=None):
    """The distinct items among the INVENTORY sightings in [t0, t1]: one item hovered across frames, or hovered again
    within SAME_ITEM_GAP_MS at the same place, is one find. -> list of {firstTs, lastTs, n, reel, frame, proof}."""
    rows = []
    for h in hits or []:
        ts = h.get("ts") if isinstance(h, dict) else None
        if not isinstance(ts, int) or (t0 is not None and ts < t0) or (t1 is not None and ts > t1):
            continue
        if (h.get("side") or side_of(h)) != "inventory":
            continue
        rows.append(h)
    items = []
    for h in sorted(rows, key=lambda x: x["ts"]):
        w, ht = float(h["wh"][0]), float(h["wh"][1])
        cx, cy = (h["red"][0] + h["red"][2]) / 2.0 / w, h["red"][1] / ht
        for it in items:
            if (abs(it["cx"] - cx) <= SAME_ITEM_FRAC and abs(it["cy"] - cy) <= SAME_ITEM_FRAC
                    and h["ts"] - it["lastTs"] <= SAME_ITEM_GAP_MS):
                it["lastTs"], it["n"] = h["ts"], it["n"] + 1
                break
        else:
            items.append({"cx": cx, "cy": cy, "firstTs": h["ts"], "lastTs": h["ts"], "n": 1,
                          "reel": h.get("reel"), "frame": h.get("frame"), "proof": h.get("proof")})
    return [{k: v for k, v in it.items() if k not in ("cx", "cy")} for it in items]


def session_count(t0, t1, d=None):
    """-> (count, why) for one session window on THIS machine. count None = UNKNOWN: no reel filmed the window, or a
    reel that did has not been walked through it yet. 0 = walked, and no inventory tooltip carried the line."""
    if not isinstance(t0, (int, float)) or not isinstance(t1, (int, float)):
        return None, "the session has no time window"
    d = d if d is not None else load_cached()
    if d is None:
        return None, "the chronicle ledger could not be read"
    cover = [rs for rs in (d.get("reels") or {}).values()
             if isinstance(rs.get("firstTs"), int) and isinstance(rs.get("lastTs"), int)
             and rs["firstTs"] <= t1 and rs["lastTs"] >= t0]
    if not cover:
        return None, "no reel on this machine filmed this session"
    for rs in cover:
        if int(rs.get("scannedTs") or 0) < min(t1, rs["lastTs"]):
            return None, "the chronicle lane has not walked this session's footage yet"
    return len(finds(d.get("hits"), t0, t1)), ""


if __name__ == "__main__":
    import json
    import sys
    for p in sys.argv[1:]:
        print(os.path.basename(p), json.dumps(read(p)))
