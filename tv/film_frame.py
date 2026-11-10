# -*- coding: utf-8 -*-
"""Map a captured client / game rect onto the 1920x1080 film canvas.

MEASURED 2026-11-07 (Claude, #255 / reader_parity / v3881): a Windows PC that plays D2R
windowed, client 1507x755. Elad recalled that as "about 1500 px wide". v3881 cropped to
the client (PW_CLIENTONLY) and stopped filming the desktop, but it did not normalize that
~2:1 client onto the 1920x1080 reference the Mac's templates use. A 1507x755 frame stayed
1507x755 (or was first capped at 800 px), so every full-frame fraction missed.

to_film_frame() trims window chrome / letterbox (char_select.game_box), resamples the
game with LANCZOS (including a smaller windowed client), and letterboxes onto 1920x1080
so the stored frame always has the same box. Aspect is kept — a 1507x755 client becomes
1920x961 centered on a 1920x1080 canvas (59 px black bars top and bottom).
"""
import os

from PIL import Image

try:
    _RESAMPLE = Image.Resampling.LANCZOS
except AttributeError:  # Pillow < 9
    _RESAMPLE = Image.LANCZOS

FILM_W, FILM_H = 1920, 1080
# Claude, 2026-11-07: "a windowed session at the Dean-shaped client (1507×755)"
DEAN_WINDOWED_CLIENT = (1507, 755)


def film_dest_size(src_w, src_h, film_w=FILM_W, film_h=FILM_H):
    """((nw, nh), (ox, oy)) of the game after fitting inside the film box. Aspect kept.

    Matches capture_win.ps1 SaveAll: scale = min(film/src), nw/nh truncated toward zero.
    A source of DEAN_WINDOWED_CLIENT lands at ((1920, 961), (0, 59)).
    """
    src_w, src_h = int(src_w), int(src_h)
    film_w, film_h = int(film_w), int(film_h)
    if src_w < 1 or src_h < 1 or film_w < 1 or film_h < 1:
        return (max(1, film_w), max(1, film_h)), (0, 0)
    scale = min(film_w / float(src_w), film_h / float(src_h))
    nw = max(1, int(src_w * scale))
    nh = max(1, int(src_h * scale))
    if nw > film_w:
        nw = film_w
    if nh > film_h:
        nh = film_h
    ox = (film_w - nw) // 2
    oy = (film_h - nh) // 2
    return (nw, nh), (ox, oy)


def to_film_frame(im, film_w=FILM_W, film_h=FILM_H, crop=True):
    """Crop chrome, resample the game into film_w x film_h, letterbox with black."""
    rgb = im.convert("RGB") if im.mode != "RGB" else im
    if crop and rgb.size != (film_w, film_h):
        from char_select import game_box
        box = game_box(rgb)
        if box != (0, 0) + rgb.size:
            x0, y0, x1, y1 = box
            if x1 > x0 and y1 > y0:
                rgb = rgb.crop((x0, y0, x1, y1))
    w, h = rgb.size
    if (w, h) == (film_w, film_h):
        return rgb
    (nw, nh), (ox, oy) = film_dest_size(w, h, film_w, film_h)
    canvas = Image.new("RGB", (film_w, film_h), (0, 0, 0))
    resized = rgb if (nw, nh) == (w, h) else rgb.resize((nw, nh), _RESAMPLE)
    canvas.paste(resized, (ox, oy))
    return canvas


def to_film_jpeg(src, dest, quality=82, film_w=FILM_W, film_h=FILM_H, crop=True):
    """Write src as a letterboxed film JPEG. True when the file landed and is not empty."""
    im = Image.open(src)
    if hasattr(im, "draft"):
        im.draft("RGB", (int(film_w), int(film_h)))
    out = to_film_frame(im, film_w=film_w, film_h=film_h, crop=crop)
    out.save(dest, "JPEG", quality=int(quality))
    return os.path.isfile(dest) and os.path.getsize(dest) > 4000
