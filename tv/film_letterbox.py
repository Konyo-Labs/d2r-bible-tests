# -*- coding: utf-8 -*-
"""#115 - LETTERBOX A WINDOWED CLIENT ONTO THE 1920x1080 FILM AND COUNT SKIPS BY REASON.

Matches capture_win.ps1 (v3894): scale = min(filmW/srcW, filmH/srcH), centre the result, never
stretch the aspect. A Dean-shaped 1507x755 client becomes 1920x961 with bars top and bottom.
Panel-relative bands (inventory, stash, character select) are mapped through the same place so
a reader crop stays on the game, not on the black bar or a pre-letterbox coordinate.

Skip events the recorder already names are counted by reason so a desktop-refused frame is not
the same number as a missing game window.
"""

FILM_W, FILM_H = 1920, 1080
DEAN_CLIENT = (1507, 755)

SKIP_REASONS = (
    "no-game-window",
    "desktop-refused",
    "client-empty",
    "encode-failed",
    "stood-aside",
)


def letterbox_place(src_w, src_h, film_w=FILM_W, film_h=FILM_H):
    """Where a source of src_w x src_h sits inside the film. -> dict | None (no pixels)."""
    try:
        src_w, src_h = int(src_w), int(src_h)
        film_w, film_h = int(film_w), int(film_h)
    except (TypeError, ValueError):
        return None
    if src_w <= 0 or src_h <= 0 or film_w <= 0 or film_h <= 0:
        return None
    scale = min(film_w / float(src_w), film_h / float(src_h))
    nw = int(src_w * scale)
    nh = int(src_h * scale)
    if nw > film_w:
        nw = film_w
    if nh > film_h:
        nh = film_h
    return {"scale": scale, "nw": nw, "nh": nh,
            "ox": (film_w - nw) // 2, "oy": (film_h - nh) // 2,
            "filmW": film_w, "filmH": film_h}


def map_panel_band(band, src_size, film_w=FILM_W, film_h=FILM_H):
    """A panel-relative (x, y, w, h) on the client, mapped onto the letterboxed film. -> dict | None."""
    if not (isinstance(band, (tuple, list)) and len(band) == 4):
        return None
    if not (isinstance(src_size, (tuple, list)) and len(src_size) == 2):
        return None
    place = letterbox_place(src_size[0], src_size[1], film_w, film_h)
    if place is None:
        return None
    try:
        x, y, w, h = [float(v) for v in band]
    except (TypeError, ValueError):
        return None
    s = place["scale"]
    return {"x": int(round(place["ox"] + x * s)),
            "y": int(round(place["oy"] + y * s)),
            "w": max(0, int(round(w * s))),
            "h": max(0, int(round(h * s)))}


def count_skips(events):
    """-> {reason: n} for every declared reason plus 'other'. Unknown stays in other, never invented."""
    out = {r: 0 for r in SKIP_REASONS}
    out["other"] = 0
    for e in events or []:
        r = e.get("reason") if isinstance(e, dict) else e
        if not isinstance(r, str) or not r:
            continue
        if r in SKIP_REASONS:
            out[r] += 1
        else:
            out["other"] += 1
    return out
