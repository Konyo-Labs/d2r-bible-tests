# -*- coding: utf-8 -*-
"""#91 — HIS CHARACTERS LEARN THEMSELVES FROM THE REELS.

Konyo, 2026-09-30, on the Character Builder's "From your characters (class + level)" list: "for character build
based on the reels and character selection it should also learn the character and sync them in automatically after
being witnessed a few times over."

That list was four HAND-TYPED rows in the page source (CHARS: Konyolock Warlock 88, Konyodin Paladin 82 ...). Nothing
ever updated them, so a level he gained stayed unsaid and a character he made never appeared.

MEASURED before building (2026-09-30, his Mac, 30 reels, 14,208 frames):
  · the character-select screen IS filmed — reel_s_1790675069096 opens on it: nine rows, "SOCKET / LEVEL 1 AMAZON",
    "OSENBEICHAN / LEVEL 31 WARLOCK" (title CHAMPION), a LEVEL 81 SORCERESS (title MATRIARCH) under the cursor ...
  · the local OCR CANNOT READ it (the D2R font: tv_diablo.py already records "defeated by the D2R FONT, not by
    resolution"): the list crop came back "LEvEL I BAKBARIAH", "LEVEL. SI Vi*RL•CK" (31 read as SI), "K•NY•Ku>".
    A whole-reel OCR hunt for "Level N <Class>" found NOTHING in 3,051 frames — the instrument, not the footage.
  · and the OCR is no DETECTOR either: shifting the crop 3 pixels swung it from 4 "LEVEL" rows to 1.
  · the PIXELS are: the list panel is flat grey stone — mean saturation 0.036-0.041, brightness 0.36-0.37 on his
    film — while every other screen measured sits far away (title 0.97 sat, Boosteroid queue 0.33, inventory 0.18,
    gameplay 0.11-0.33 at brightness <= 0.24). ~5 ms a frame, so EVERY frame is checked (his visit lasted 2 s).
    The READ is the console's own vision reader, on the panel crop only, and its "screen" answer is the second,
    independent witness: a grey panel that is not the list costs one refused read, never a character.

THE RULE HE ASKED FOR — "after being witnessed a few times over":
  · a VISIT is one stay on the character-select screen (candidate frames within VISIT_GAP_S of each other);
  · a character is LEARNED once it was read on MIN_VISITS separate visits, with a class;
  · its LEVEL is the highest level that MIN_VISITS visits saw it at or above — a level-up is confirmed the next time
    he opens the screen, and a single misread (88 read as 98) never becomes his level: it waits as `pendingLevel`;
  · within one visit the reads are not independent (the same screen), so a visit claims the LOWEST level its reads
    agree on.
PER PC by construction: each console scans its OWN reels into its OWN ledger (tv/.char_roster.json, gitignored), and
the page asks its own console. Nothing here writes a build: the 👤 Characters / builder stores stay manual (#245).

#149 — THE LOBBY NAMES HIM TOO. The create-game screen between games is not the character-select list (the bands
above already refuse it: left val 0.153). A frame that misses the list and matches the lobby bands gets one read of
the whole frame. The answer is a witness row on that character, citing the frame, not a second way to become learned.
The in-game character panel is the same row when a reader says that is the screen. No pixel band was measured for it.
"""
import difflib
import glob
import json
import os
import re
import shutil
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CLASSES = ("Amazon", "Assassin", "Barbarian", "Druid", "Necromancer", "Paladin", "Sorceress", "Warlock")
TITLES = ("Slayer", "Champion", "Patriarch", "Matriarch", "Destroyer", "Conqueror", "Guardian", "Count", "Countess",
          "Baron", "Baroness", "Lord", "Lady", "Duke", "Duchess", "King", "Queen", "Sir", "Dame")

PANEL_W_H = 0.385        # the list panel's width as a fraction of the frame HEIGHT: D2R scales its UI with height
                         # and anchors this panel to the right edge. MEASURED on his 1440x904 film: the OCR found 4
                         # LEVEL rows at x0 = 0.76w (= w - 0.385h), 0 at 0.70w and 0 at 0.80w — the crop IS the read.
SAMPLE_EVERY = 1         # every frame (~1 fps): MEASURED, his visit on reel_s_1790675069096 lasted 2 frames
# BOTH stone panels, measured on all 45,555 frames of his 30 reels (2026-09-30): 8 real character-select visits read
# right sat 0.022-0.052 / val 0.355-0.361 and left sat 0.086-0.109 / val 0.215-0.219. With the right panel alone the
# scan also flagged two blank white browser pages (val 0.999 / left 1.0), a snow field in play (right val 0.461, left
# sat 0.217) and the game LOBBY (left val 0.153). The bands keep a margin because another PC films at another size.
RIGHT_SAT_MAX = 0.07
RIGHT_VAL = (0.30, 0.45)
LEFT_SAT = (0.05, 0.16)
LEFT_VAL = (0.17, 0.27)
# Create-game lobby, draft decode at 1/4 (the same decode panel_stats uses), measured 2026-10-03 on
# reel_s_1790978096994 frame f_1790978100063 and the screens beside it in that reel:
#   lobby  full sat 0.158 val 0.192, bot val 0.183, right sat 0.083
#   loading full sat 0.094 val 0.085, bot val 0.000, right sat 0.014
#   skill   full sat 0.177 val 0.255, bot val 0.229, right sat 0.116
#   play    full sat 0.596 val 0.156, bot val 0.170, right sat 0.556
# ALT, 800x450, 2026-10-04, the same draft and the same crops (REG-1764):
#   quiet lobby  f_1790634727494  0.158 / 0.189 / 0.182 / 0.089  (passes 0.17)
#   chatty lobby f_1790597040521  0.196 / 0.182 / 0.153 / 0.098  (the chat lifts full sat)
#   skill tree   f_1790666327755  0.323 / 0.208 / 0.155 / 0.085  (val, bot and right pass)
# The chatty cluster reached 0.199. 0.22 sits above that and below the skill tree, which
# is the screen the other three bands do not refuse at this size. An 800x400 frame in the
# same pass was the launcher, not the game. No character-panel frame was filmed.
# Bot is y 0.78-0.98. Right is x 0.72-0.98, y 0.15-0.75 (the create-game pane).
LOBBY_FULL_SAT_MAX = 0.22
LOBBY_FULL_VAL = (0.16, 0.22)
LOBBY_BOT_VAL_MIN = 0.10
LOBBY_RIGHT_SAT_MAX = 0.10
# v3890 (#183, his 11-09 "make sure its working and calliberated plaese") - A RICHER-COLOUR LOBBY, AND ONLY THE LOBBY.
# MEASURED 11-09 over SSH on both ALTs' own frames. The bands above were set on Boosteroid's compressed 800x450 picture. The
# work ALT's local D2R draws the same lobby at 1440x810 with right sat 0.111 (0.011 over the band) and full sat 0.216, so
# 9,427 frames there matched 0 and it learned no character (Konyorian, Barbarian 87, on screen in every one); its own
# 800x450 stream drew it at full sat 0.22-0.23. Simply widening the two bands is WRONG: on the OLD ALT it let in 355 more
# frames, 11 of 12 opened were dark night-town gameplay. What only the lobby has is its PANELS: the create-game pane is a
# flat grey (value 0.17-0.19, spread 0.085-0.10), the chat pane the same (0.165-0.18, spread 0.06-0.08), and the top
# strip carries the lit Lobby / Create Game headers (value 0.224-0.226; dark scenery 0.167). So a frame the bands refuse
# only on these two colour limits passes when its panels read as the lobby's. On the work ALT that admits every new
# candidate sampled (800 of 800, all lobbies opened) and on the OLD ALT 34 of 355 (16 opened: 15 lobbies, and the 16th, a
# dark street, is refused by the top strip). [[unknown-stays-unknown]]
LOBBY_PANEL_FULL_SAT_MAX = 0.24
LOBBY_PANEL_RIGHT_SAT_MAX = 0.13
LOBBY_PANEL_RIGHT_VAL = (0.165, 0.20)
LOBBY_PANEL_RIGHT_SD = (0.08, 0.105)
LOBBY_PANEL_LEFT_VAL = (0.155, 0.195)
LOBBY_PANEL_LEFT_SD = (0.055, 0.095)
LOBBY_PANEL_TOP_VAL_MIN = 0.20
# REG-1874 — WHAT EACH FILM SIZE IS, LOOKED AT (2026-10-07). The bands are fractions of the frame, so one set can
# serve every size the game is filmed at, and where it has been seen the counts say it does: the ALT matched 10,101 of 118,097 at 800x450, his Mac
# matched at 1440x904, 1440x936, 1440x841, 1440x857, 2940x1912 and three more. Seven ALT lobby frames of 2026-10-06
# (three reels, 800x450) pass today - full sat 0.145-0.155, val 0.169-0.185 - and the loading card filmed between
# them (f_1791319507226, full sat 0.108 val 0.073) does not. A size with checked > 0 and matched 0 is either a
# screen with no game on it or a band that is blind there, and the count alone cannot say which. These were opened:
#   ALT 800x400 and 800x420 (10,698 checked, 0 matched): Boosteroid's own window - "WHERE HAVE YOU BEEN? Session has
#     been terminated due to no activity" - on all five frames opened across three reels and both sizes
#   Mac 1440x1327 (17,711, 0): GeForce NOW's own app, its library page, on 20 frames across 14 reels
#   Mac 1440x813 (5,619, 0): GeForce NOW in Chrome - its spinner and "return to fullscreen" - 20 frames, 4 reels
#   Mac 1440x861 (1,650, 0): Boosteroid's own app, sign-in and library, 20 frames across 2 reels
# No game is drawn at those sizes, so per-size bands are not owed. A zero-match size not listed here has not been
# looked at, and the lane says that it is UNKNOWN rather than letting "matched 0" read as "no lobby".
LOBBY_SIZES_SEEN = {
    "800x400": "Boosteroid's own window (its no-activity screen) - no game is drawn at this size",
    "800x420": "Boosteroid's own window (its no-activity screen) - no game is drawn at this size",
    "1440x1327": "GeForce NOW's own app (its library page) - no game is drawn at this size",
    "1440x813": "GeForce NOW in Chrome (its spinner, return to fullscreen) - no game is drawn at this size",
    "1440x861": "Boosteroid's own app (sign-in and library) - no game is drawn at this size",
    # v3890 (#183) - opened 11-09 on the work ALT (LT-Issta): 12 frames across 41 reels at 1440x809 and 12 across 33 at
    # 800x449 - Boosteroid's "WHERE HAVE YOU BEEN? Session has been terminated due to no activity" and its library page
    "1440x809": "Boosteroid's own window (its no-activity screen) - no game is drawn at this size",
    "800x449": "Boosteroid's own window (its no-activity screen and library) - no game is drawn at this size",
}
LOBBY_SIZE_UNSEEN = ("nobody has looked at this size, so whether the bands see the lobby here is UNKNOWN")
# The character panel stays a reader answer. This sentence is the lane, not a pixel band.
CPANEL_SAY = "The character panel has no pixel band. It is kept only when a reader says that is the screen."
SURFACE_TIERS = {"lobby": 1.0, "c-panel": 1.0}
VISIT_GAP_S = 90         # candidate frames further apart than this are separate visits
MIN_VISITS = 2           # "witnessed a few times over"
MAX_READS_PER_VISIT = 2
ON_FRAME_KEEP = 12      # #211 - per-read name lists a visit keeps; a visit read more often is UNKNOWN past it
CLOSE_READ_GAP_MS = 3000  # #103 step B: a visit whose last frame came this long after its last read gets ONE more read
                          # of that last frame - the row highlighted when he pressed Play is the character he entered with
READS_PER_HOUR = 8       # the paid reader is his subscription; this lane never spends more than this
TICK_BUDGET_S = 8.0      # wall time one tick may spend scanning (it rides a 45 s loop: <20% of one core, and less
                         # on the ALT, where the game shares an 8 GB box)

_FRAME_TS = re.compile(r"f_(\d{10,})\.(?:jpg|jpeg|png)$", re.I)


def _world():
    """His tree, or the fixture's when TV_HIST names one (tv_diablo._fixture_root - called, not copied).

    ⚠ REG-1583, MEASURED 2026-09-30 on the v3526 gate run: test_roundtrip_sim's fixture console created .char_roster.json in
    the tree it ran from - on his checkout that is HIS roster, and the tick would also have dropped every reel
    position the fixture world does not hold. A fixture console keeps its own roster."""
    try:
        import tv_diablo as _tvd
        return _tvd._fixture_root(HERE)
    except Exception:
        _h = (os.environ.get("TV_HIST") or "").strip()
        return _h if (_h and os.path.isabs(_h)) else HERE


def store_path():
    return os.environ.get("TV_CHARS_LEARNED") or os.path.join(_world(), ".char_roster.json")


def hist_root():
    try:
        import tv_diablo as _td
        return _td.HIST_DIR
    except Exception:
        return os.environ.get("TV_HIST") or os.path.join(HERE, "frames", "hist")


# ── the detector (free) ─────────────────────────────────────────────────────────────────────────────────────
# v3856 - WINDOWED FRAMES. Dean plays D2R in a window: his reels are the game plus the window's title bar, border and
# letterbox (799x434, 800x402, 800x409 ... checked 118,420 at 800x402, matched 150). The bands are fractions of the
# GAME, so measured on the whole frame the title bar lifted the full value and the right pane slid, and no size of that
# family reached two clean lobby reads. game_box() finds the game inside the frame: it trims edge rows and columns that
# are window chrome (flat and very bright, or flat black letterbox), never more than GAME_TRIM_MAX of a side, and keeps
# the whole frame when the trim would leave less than GAME_MIN_AREA. Both scanners measure inside that box.
GAME_TRIM_MAX = 0.25
GAME_MIN_AREA = 0.5
_CHROME_STD = 14.0


def _chrome(mean, std):
    return std < _CHROME_STD and (mean > 150 or mean < 10)


def game_box(im):
    """(x0, y0, x1, y1) of the game inside an RGB frame: window chrome and letterbox trimmed from each edge."""
    import numpy as np
    w, h = im.size
    a = np.asarray(im.convert("L"), dtype=np.float32)
    if a.size == 0:
        return 0, 0, w, h
    rows_m, rows_s = a.mean(axis=1), a.std(axis=1)

    def trim(ms, ss, n):
        lim = int(n * GAME_TRIM_MAX)
        lo = 0
        while lo < lim and _chrome(ms[lo], ss[lo]):
            lo += 1
        hi = n
        while n - hi < lim and hi - 1 > lo and _chrome(ms[hi - 1], ss[hi - 1]):
            hi -= 1
        return lo, hi
    y0, y1 = trim(rows_m, rows_s, h)
    band = a[y0:y1] if y1 > y0 else a      # the columns are read below the title bar, not through it
    x0, x1 = trim(band.mean(axis=0), band.std(axis=0), w)
    if (x1 - x0) * (y1 - y0) < GAME_MIN_AREA * w * h:
        return 0, 0, w, h
    return x0, y0, x1, y1


def _in_game(im):
    """The frame cut to its game area (game_box): a full-screen frame comes back whole."""
    box = game_box(im)
    return im if box == (0, 0) + im.size else im.crop(box)


def windowed_fixture(path, frame=(800, 409), title=31, game=(672, 378), sat=0.05, val=0.19):
    """v3856 - a windowed-mode lobby frame for the law and the doctor: a flat lobby plaque of `game` size inside a
    `frame` with a bright window title bar of `title` px on top and black letterbox around it (Dean's 800x409 family)."""
    from PIL import Image
    w, h = frame
    im = Image.new("RGB", (w, h), (0, 0, 0))
    im.paste(Image.new("RGB", (w, title), (236, 236, 236)), (0, 0))
    plaque = Image.new("HSV", game, (0, int(sat * 255), int(val * 255))).convert("RGB")
    im.paste(plaque, ((w - game[0]) // 2, title + (h - title - game[1]) // 2))
    im.save(path, quality=95)
    return path


def _sv(im, box):
    from PIL import ImageStat
    st = ImageStat.Stat(im.crop(tuple(int(v) for v in box)).resize((20, 40)).convert("HSV"))
    return st.mean[1] / 255.0, st.mean[2] / 255.0


def panel_stats(path):
    """(right_sat, right_val, left_sat, left_val), 0..1: the list panel on the right and the menu column on the
    left, or None when the frame cannot be opened. JPEG draft mode decodes at 1/4 size — both panels are flat
    stone, so a quarter of the pixels says the same thing (measured ~7 ms a frame over his 45,555)."""
    try:
        from PIL import Image
        with Image.open(path) as im:
            im.draft("RGB", (max(1, im.size[0] // 4), max(1, im.size[1] // 4)))
            im = _in_game(im.convert("RGB"))
            w, h = im.size
            rs, rv = _sv(im, (max(0, w - PANEL_W_H * h), 0.07 * h, w, 0.93 * h))
            ls, lv = _sv(im, (0.02 * h, 0.40 * h, 0.30 * h, 0.95 * h))
            return rs, rv, ls, lv
    except Exception:
        return None


def looks_like_char_select(stats):
    """(bool, why) from panel_stats(): the grey stone list on the right AND the stone menu column on the left."""
    if not stats:
        return False, "frame unreadable"
    rs, rv, ls, lv = stats
    right = rs < RIGHT_SAT_MAX and RIGHT_VAL[0] < rv < RIGHT_VAL[1]
    left = LEFT_SAT[0] < ls < LEFT_SAT[1] and LEFT_VAL[0] < lv < LEFT_VAL[1]
    say = "right sat %.3f val %.3f · left sat %.3f val %.3f" % (rs, rv, ls, lv)
    if right and left:
        return True, "both stone panels (%s)" % say
    return False, ("no list panel" if not right else "no menu column") + " (%s)" % say


def lobby_stats(path):
    """(full_sat, full_val, bot_val, right_sat, right_val, right_sd, left_val, left_sd, top_val), or None when the frame
    cannot be opened. The first four are the bands; the last five are the lobby's panels (v3890 #183).

    Draft decode at 1/4, then the whole frame, the bottom strip, and the create-game pane. A frame that
    is not an image is None, the same as an unreadable character-select frame, never a lobby."""
    try:
        from PIL import Image, ImageStat
        with Image.open(path) as im:
            im.draft("RGB", (max(1, im.size[0] // 4), max(1, im.size[1] // 4)))
            im = _in_game(im.convert("RGB")).convert("HSV")
            w, h = im.size

            def sv(box):
                st = ImageStat.Stat(im.crop(tuple(int(v) for v in box)).resize((20, 40)))
                return st.mean[1] / 255.0, st.mean[2] / 255.0, st.stddev[2] / 255.0

            fs, fv, _f = sv((0, 0, w, h))
            _bs, bv, _b = sv((0, 0.78 * h, w, 0.98 * h))
            rs, rv, rsd = sv((0.72 * w, 0.15 * h, 0.98 * w, 0.75 * h))
            _ls, lv, lsd = sv((0.02 * w, 0.15 * h, 0.28 * w, 0.75 * h))
            _ts, tv, _t = sv((0.02 * w, 0.02 * h, 0.98 * w, 0.10 * h))
            return fs, fv, bv, rs, rv, rsd, lv, lsd, tv
    except Exception:
        return None


def file_wh(path):
    """The file's own pixel size, before the draft decode. None when it is not an image.

    A size that cannot be read is not a size, so it is not recorded as 0."""
    try:
        from PIL import Image
        with Image.open(path) as im:
            w, h = im.size
            w, h = int(w), int(h)
            if w > 0 and h > 0:
                return w, h
    except Exception:
        return None
    return None


def note_lobby_size(st, wh, matched):
    """One lobby check at this file size. An unreadable size is not counted."""
    if not isinstance(st, dict) or not wh or len(wh) != 2:
        return
    try:
        key = "%dx%d" % (int(wh[0]), int(wh[1]))
    except (TypeError, ValueError):
        return
    if int(wh[0]) <= 0 or int(wh[1]) <= 0:
        return
    book = st.setdefault("lobbyBySize", {})
    if not isinstance(book, dict):
        return
    row = book.get(key)
    if not isinstance(row, dict):
        row = {"checked": 0, "matched": 0}
        book[key] = row
    row["checked"] = int(row.get("checked") or 0) + 1
    if matched:
        row["matched"] = int(row.get("matched") or 0) + 1


def lobby_by_size(d):
    """Checked and matched per file size.

    None when the ledger was not read, or when this console has not counted yet.
    A size is absent until a frame of that size was opened. Never a matched 0 for
    a size nobody checked."""
    if not isinstance(d, dict):
        return None
    stt = d.get("stats")
    if not isinstance(stt, dict) or "lobbyBySize" not in stt:
        return None
    raw = stt.get("lobbyBySize")
    if not isinstance(raw, dict):
        return None
    out = []
    for key, row in raw.items():
        if not isinstance(row, dict):
            continue
        try:
            checked = int(row["checked"])
            matched = int(row["matched"])
        except (KeyError, TypeError, ValueError):
            continue
        if checked < 0 or matched < 0 or matched > checked:
            continue
        row = {"size": str(key), "checked": checked, "matched": matched}
        if matched == 0 and checked > 0:
            # REG-1874 - a zero says what the size is, looked at, or that nobody looked
            row["seen"] = LOBBY_SIZES_SEEN.get(str(key)) or LOBBY_SIZE_UNSEEN
        out.append(row)
    out.sort(key=lambda r: r["size"])
    return out


def looks_like_lobby(stats):
    """(bool, why) from lobby_stats(). The create-game lobby, and not the loading card, the skill tree, or play."""
    if not stats or len(stats) not in (4, 9):
        return False, "frame unreadable"
    fs, fv, bv, rs = stats[:4]
    ok = (fs < LOBBY_FULL_SAT_MAX and LOBBY_FULL_VAL[0] < fv < LOBBY_FULL_VAL[1]
          and bv > LOBBY_BOT_VAL_MIN and rs < LOBBY_RIGHT_SAT_MAX)
    say = "full sat %.3f val %.3f, bot val %.3f, right sat %.3f" % (fs, fv, bv, rs)
    if ok:
        return True, "create-game lobby (%s)" % say
    # v3890 (#183) - the same lobby in richer colour: the two colour limits relax ONLY when the panels read as the lobby's
    if len(stats) == 9:
        rv, rsd, lv, lsd, tv = stats[4:]
        if (fs < LOBBY_PANEL_FULL_SAT_MAX and LOBBY_FULL_VAL[0] < fv < LOBBY_FULL_VAL[1] and bv > LOBBY_BOT_VAL_MIN
                and rs < LOBBY_PANEL_RIGHT_SAT_MAX
                and LOBBY_PANEL_RIGHT_VAL[0] < rv < LOBBY_PANEL_RIGHT_VAL[1] and LOBBY_PANEL_RIGHT_SD[0] < rsd < LOBBY_PANEL_RIGHT_SD[1]
                and LOBBY_PANEL_LEFT_VAL[0] < lv < LOBBY_PANEL_LEFT_VAL[1] and LOBBY_PANEL_LEFT_SD[0] < lsd < LOBBY_PANEL_LEFT_SD[1]
                and tv > LOBBY_PANEL_TOP_VAL_MIN):
            return True, "create-game lobby, by its panels (%s; panels %.3f/%.3f %.3f/%.3f, top %.3f)" % (say, rv, rsd, lv, lsd, tv)
    return False, "not the lobby (%s)" % say


def panel_crop(path, out_dir):
    """Crop the character list (right-hand panel) to its own file. Returns the crop path, or None — a frame that
    cannot be opened is not a frame that showed nothing."""
    try:
        from PIL import Image
        with Image.open(path) as im:
            w, h = im.size
            box = (max(0, int(w - (PANEL_W_H + 0.02) * h)), 0, w, h)
            dst = os.path.join(out_dir, "cs_" + os.path.basename(path))
            im.crop(box).convert("RGB").save(dst, quality=88)
            return dst
    except Exception:
        return None


# ── the reader's answer, normalized ─────────────────────────────────────────────────────────────────────────
def _fold(name):
    """The key a name is matched on: the D2R font draws O as ⊕, readers vary in case."""
    s = str(name or "").replace("⊕", "O").replace("Ø", "O").replace("◎", "O")
    return re.sub(r"[^a-z0-9]", "", s.lower())


#: GrokBot bug 11 (2026-10-27) - "KOnyORush", "SOcket", "ArmOr", "WeapOn", "SetOnami" on the Mac's list. Both reader
#: prompts say to write the font's O as the letter O, so a mixed-case answer carries a capital O inside a word. Socket,
#: Armor and Weapon are his real level-1 mules (this file's own SOCKET example), so this is the SPELLING, never a refusal.
#: A capital O after a letter and before a lower-case one, or after a lower-case one, is a lower-case o. An all-caps
#: answer still goes through .title(); a name's leading O stays (OsenbeiChan).
_O_INSIDE = re.compile(r"(?<=[A-Za-z])O(?=[a-z])|(?<=[a-z])O")


def _o_case(name):
    s = str(name or "")
    return s if s.isupper() else _O_INSIDE.sub("o", s)


def _shown(c):
    """The name a character is SHOWN as: its spelling vote, each form read through _o_case, the stored name winning a tie.

    The vote is re-run on every read, so a ledger that stored "SOcket" (a tie that sorted 'O' before 'o' after a save)
    shows "Socket" with nothing rewritten."""
    forms = (c or {}).get("forms") or {}
    stored = _o_case((c or {}).get("name")) if (c or {}).get("name") else (c or {}).get("name")
    if not forms:
        return stored
    tally = {}
    for f, n in forms.items():
        k = _o_case(f)
        try:
            tally[k] = tally.get(k, 0) + int(n or 0)
        except (TypeError, ValueError):
            tally[k] = tally.get(k, 0)
    best = max(tally.values())
    tops = [f for f in tally if tally[f] == best]
    return stored if stored in tops else sorted(tops)[0]


def _clean_name(name):
    s = str(name or "").replace("⊕", "O").replace("Ø", "O").replace("◎", "O").strip()
    s = re.sub(r"\s+", " ", s)
    # D2R names: 2-15 characters, letters plus at most one '-' or '_'; anything else is a misread
    if not re.fullmatch(r"[A-Za-z][A-Za-z\-_]{1,14}", s):
        return None
    # the game's font is small capitals, so an all-caps answer ("RUNEWORDER") says nothing about the real case:
    # shown as "Runeworder". A mixed-case answer ("OsenbeiChan") is kept as the reader saw it. The KEY folds case.
    return s.title() if s.isupper() else _o_case(s)


def _clean_class(cls):
    c = str(cls or "").strip()
    if not c:
        return None
    for k in CLASSES:
        if c.lower() == k.lower():
            return k
    m = difflib.get_close_matches(c.title(), CLASSES, n=1, cutoff=0.75)
    return m[0] if m else None


def _clean_level(v):
    try:
        n = int(str(v).strip())
    except (TypeError, ValueError):
        return None
    return n if 1 <= n <= 99 else None


def normalize(raw):
    """The reader's JSON -> (rows, why). rows: [{name, key, cls, level, title}] for every row that is a character.
    `why` names a refusal; ([], 'other screen') is a MEASURED answer, (None, why) is not an answer at all."""
    if raw is None:
        return None, "no answer"
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return None, "not JSON"
    if not isinstance(raw, dict):
        return None, "not an object"
    if raw.get("note"):
        return None, str(raw.get("note"))[:120]
    if str(raw.get("screen") or "").lower() != "character-select":
        return [], "other screen"
    rows = []
    for r in raw.get("chars") or []:
        if not isinstance(r, dict):
            continue
        name = _clean_name(r.get("name"))
        if not name:
            continue
        title = str(r.get("title") or "").strip().title() or None
        rows.append({"name": name, "key": _fold(name), "cls": _clean_class(r.get("cls")),
                     "level": _clean_level(r.get("level")), "title": title if title in TITLES else None})
    return rows, ("%d rows" % len(rows))


def partial_of(raw):
    """Did the reader see the WHOLE list? -> False (whole), True (cut off / scrolled / a row covered), None (it did not
    say, or the answer is not an object) - UNKNOWN, which no look may count as a miss."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return None
    if not isinstance(raw, dict):
        return None
    p = raw.get("partial")
    return p if isinstance(p, bool) else None


def selected_of(raw, rows):
    """#103 step B — the row the screen shows HIGHLIGHTED: the character the game enters with. -> (name, why)

    Only a name that is one of the rows THIS read listed counts, folded as the learner folds: a highlighted name the list
    does not carry is a misread, and a guessed character would file his gear under the wrong one. None + why is UNKNOWN."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return None, "the answer is not JSON"
    if not isinstance(raw, dict):
        return None, "the answer is not an object"
    sel = raw.get("selected")
    if sel is None or (isinstance(sel, str) and not sel.strip()):
        return None, "the reader saw no highlighted row"
    name = _clean_name(sel)
    if not name:
        return None, "the highlighted name is not a D2R name"
    for r in rows or []:
        if r.get("key") == _fold(name):
            return r["name"], None
    return None, "the highlighted name %r is not one of the rows this read listed" % name


# ── the ledger ──────────────────────────────────────────────────────────────────────────────────────────────
def _empty():
    return {"version": 1, "chars": {}, "visits": {}, "reels": {},
            "stats": {"ticks": 0, "frames": 0, "reads": 0, "refused": 0, "lastTs": None, "lastWhy": "", "readTs": []}}


def load():
    """The ledger, or None when it exists and cannot be read — UNKNOWN, never an empty ledger (an empty one would
    be written back over the real one on the next tick)."""
    p = store_path()
    if not os.path.exists(p):
        return _empty()
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        if not isinstance(d, dict) or not isinstance(d.get("chars"), dict):
            return None
        base = _empty()
        for k in base:
            d.setdefault(k, base[k])
        return d
    except Exception:
        return None


def save(d):
    p = store_path()
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, p)


def record(d, visit_id, rows, meta=None):
    """Fold one read of one visit into the ledger. Within a visit a character keeps the LOWEST level its reads
    agree on (two reads of one screen are not two witnesses)."""
    v = d["visits"].setdefault(visit_id, {"reads": 0, "rows": 0, "onFrame": []})
    v["reads"] = int(v.get("reads") or 0) + 1
    # #211 (GrokBot's v3817 pass) - WHICH NAMES ONE READ SAW TOGETHER. A read is one frame; two names on one frame are two
    # characters, two names on two frames of one visit may be one name read two ways. Only a visit that began with this
    # list keeps it (an older visit's earlier reads are gone), so a list as long as the visit's reads is the whole visit.
    if isinstance(v.get("onFrame"), list):
        v["onFrame"].append(sorted({r["key"] for r in rows or [] if r.get("key")}))
        del v["onFrame"][:-ON_FRAME_KEEP]
    v["rows"] = max(int(v.get("rows") or 0), len(rows or []))
    v.update({k: meta[k] for k in (meta or {}) if k in ("reel", "ts", "tab", "frames", "reader")})
    if meta and meta.get("selected"):
        sel = v.setdefault("sel", [])
        sel.append({"ts": meta.get("ts"), "name": meta["selected"], "reader": meta.get("reader")})
        del sel[:-6]
    if meta and "partial" in meta:
        # #103 - was the whole list on screen? One read that saw it whole makes the visit complete; a cut-off read
        # (scrolled, a row covered) makes it partial only while no read saw it whole; nobody said -> None (UNKNOWN)
        p, prev = meta.get("partial"), v.get("partial")
        v["partial"] = False if (p is False or prev is False) else (True if (p is True or prev is True) else None)
    for r in rows or []:
        c = d["chars"].setdefault(r["key"], {"name": r["name"], "cls": {}, "visitLevel": {}, "titles": {},
                                             "firstTs": None, "lastTs": None})
        # the SPELLING is voted too: MEASURED on his reels one character came back "SOCKET" (-> "Socket") on one
        # read and "SOcket" on another, and last-read-wins showed whichever was newest. The shown name is the form
        # most reads agree on (the first seen on a tie); the KEY never depended on it.
        forms = c.setdefault("forms", {})
        forms[r["name"]] = int(forms.get(r["name"]) or 0) + 1
        best = max(forms.values())
        c["name"] = next(f for f in forms if forms[f] == best)
        if r.get("cls"):
            per = c["cls"].setdefault(r["cls"], [])
            if visit_id not in per:
                per.append(visit_id)
        if r.get("level"):
            prev = c["visitLevel"].get(visit_id)
            c["visitLevel"][visit_id] = r["level"] if prev is None else min(prev, r["level"])
        else:
            c["visitLevel"].setdefault(visit_id, None)
        if r.get("title"):
            c["titles"][r["title"]] = int(c["titles"].get(r["title"]) or 0) + 1
        ts = (meta or {}).get("ts")
        if ts:
            c["firstTs"] = ts if not c.get("firstTs") else min(c["firstTs"], ts)
            c["lastTs"] = ts if not c.get("lastTs") else max(c["lastTs"], ts)
    return d


def _visit_ts(vid, v):
    """A visit's time: the ts its reads stored, else the one its id carries ("reel#ts"). None when neither says."""
    ts = (v or {}).get("ts") if isinstance(v, dict) else None
    if isinstance(ts, (int, float)) and not isinstance(ts, bool):
        return int(ts)
    try:
        return int(str(vid).rsplit("#", 1)[1])
    except (IndexError, ValueError):
        return None


def tier_bars():
    """The vault's bars, read from the vault's own module: {proven, hardened, wilson}, or None when it cannot load."""
    try:
        import vault_evidence as _ve
        return {"proven": _ve.TRIALS_PROVEN, "hardened": _ve.TRIALS_HARDENED, "wilson": _ve.WILSON_BAR}
    except Exception:
        return None


def proof(d, c):
    """#103 — HOW FAR A CHARACTER HAS PROVEN ITSELF, THE WAY THE VAULT'S FILINGS DO. Konyo, 2026-09-30: "they slowly
    prove themselves from reels sessions and harden same way as vault".

    A LOOK is one visit to the character-select screen that read a roster (a refused read is no look). Its SUCCESSES are
    the looks that read it. Its TRIALS are those plus its MISSES: looks since it first appeared that saw the WHOLE list
    (the reader said partial: false) and not this character. A list cut off or scrolled - MEASURED on his: 9 rows of 13
    characters - is no evidence against a character it did not show, so it is not a trial; nor is a look from before the
    reader was asked (partial unknown). The tier is vault_evidence.tier - the vault's own function, bars and Wilson
    bound, CALLED and never copied: WATCHED under 10 looks, PROVEN at 10, HARDENED at 20; a character a whole list stops
    showing (deleted in game) falls back as its misses pile up. -> {tier, looks, trials, misses, bound, why}; tier None
    is UNKNOWN, never WATCHED."""
    first = c.get("firstTs") if isinstance(c, dict) else None
    looks = len((c or {}).get("visitLevel") or {}) if isinstance(c, dict) else 0
    if not isinstance(first, (int, float)) or isinstance(first, bool):
        return {"tier": None, "looks": looks, "trials": None, "misses": None, "bound": None,
                "why": "when it first appeared is not recorded, so its looks cannot be counted - UNKNOWN"}
    read_it = set((c or {}).get("visitLevel") or {})
    misses = 0
    for vid, v in (d.get("visits") or {}).items():
        if vid in read_it:
            continue
        ts = _visit_ts(vid, v)
        if ts is None:
            return {"tier": None, "looks": looks, "trials": None, "misses": None, "bound": None,
                    "why": "a visit carries no time, so the looks since it appeared cannot be counted - UNKNOWN"}
        if ts >= int(first) and isinstance(v, dict) and v.get("partial") is False:
            misses += 1
    trials = looks + misses
    try:
        import vault_evidence as _ve
        got = _ve.tier(looks, trials)
    except Exception as e:
        return {"tier": None, "looks": looks, "trials": trials, "misses": misses, "bound": None,
                "why": "the vault's tier could not be asked (%s) - UNKNOWN" % type(e).__name__}
    b = got.get("bound")
    return {"tier": got.get("tier"), "looks": looks, "trials": trials, "misses": misses,
            "bound": round(b, 3) if isinstance(b, float) else None, "why": got.get("why") or ""}


def _cls_winner(c):
    votes = {k: len(set(v)) for k, v in ((c or {}).get("cls") or {}).items()}
    if not votes:
        return None
    best = max(votes.values())
    w = [k for k, n in votes.items() if n == best]
    return w[0] if len(w) == 1 else None


def _read_together(d, vid, a, b, keys_in, always, visits_of):
    """#211 (GrokBot's v3817 pass) - did ONE read of visit `vid` see a name of key set `a` AND a name of key set `b`?
    -> True / False / None (UNKNOWN).

    A visit is several frames of one lobby, and the reader spells one row two ways across them: on the ALT, 9-row lobbies
    carried 10 to 27 names a visit, and Konylock shared 11 visits with Konyolock. Only a read that saw both proves two
    characters. Exact where the visit kept its per-read lists (onFrame, as long as its reads). An older visit proves it
    when it had one read, when its names fit in its largest read (rows), or when one of the names was read on every read
    of every visit it is in. Anything else is UNKNOWN, and UNKNOWN is not a read that saw both."""
    v = (d.get("visits") or {}).get(vid)
    v = v if isinstance(v, dict) else {}
    reads, on = v.get("reads"), v.get("onFrame")
    if isinstance(reads, int) and reads > 0 and isinstance(on, list) and len(on) == reads:
        return any((set(f) & a) and (set(f) & b) for f in on)
    if reads == 1:
        return True
    rows = v.get("rows")
    if isinstance(rows, int) and rows > 0 and len(keys_in.get(vid) or ()) <= rows:
        return True
    if any(m in always and vid in visits_of.get(m, ()) for m in (a | b)):
        return True
    return None


def _always_read(chars, visits):
    """#211 - the keys read on EVERY read of every visit they are in: each row a read returns is one count in `forms`, so
    a name whose forms add up to the reads of its visits was never missed. -> set. A visit with no read count is UNKNOWN
    and keeps its names out."""
    out = set()
    for k, c in chars.items():
        vids = list(((c or {}).get("visitLevel") or {}))
        if not vids:
            continue
        rs = [((visits.get(v) or {}) if isinstance(visits.get(v), dict) else {}).get("reads") for v in vids]
        if not all(isinstance(r, int) and not isinstance(r, bool) and r > 0 for r in rs):
            continue
        n = sum(int(x or 0) for x in ((c or {}).get("forms") or {}).values())
        if n >= sum(rs):
            out.add(k)
    return out


def _merge_groups(d):
    """#211 (the ALT's 45 'characters') - SPELLING VARIANTS OF ONE CHARACTER ARE ONE CHARACTER. -> {head key: [keys]}

    The reader misspells a name now and then (Konylock, Konyblock for Konyolock); every spelling folded to its own key and
    each with 2 visits became its own learned character, while the visits it was read under counted as MISSES against
    the real one. Read-time only - the ledger is never rewritten. A key joins a head when chronicle_resolve.canonical (the
    chronicle's own near-name rule: NEAR_CUTOFF, AMBIGUITY_GAP) names that head, both carry the same winning class, and
    NO read ever saw both - two names on one screen are two characters (_read_together; GrokBot's v3817 pass found the
    first cut refusing on a shared VISIT, which split Konylock from Konyolock on the ALT). Heads are taken most-visited
    first."""
    chars = (d or {}).get("chars") or {}
    try:
        import chronicle_resolve as _cr
    except Exception:
        return {k: [k] for k in chars}
    order = sorted(chars, key=lambda k: (-len((chars[k] or {}).get("visitLevel") or {}),
                                         (chars[k] or {}).get("firstTs") or 0, k))
    visits = (d or {}).get("visits") or {}
    visits_of = {k: set((chars[k] or {}).get("visitLevel") or {}) for k in chars}
    keys_in = {}
    for k, vs in visits_of.items():
        for v in vs:
            keys_in.setdefault(v, set()).add(k)
    always = _always_read(chars, visits)
    groups, seen_by, heads = {}, {}, []
    for k in order:
        c = chars[k] or {}
        mine = set(c.get("visitLevel") or {})
        kc = _cls_winner(c)
        h = None
        if heads and kc is not None:
            roster = {_cr._norm(_shown(chars[x]) or x): x for x in heads}
            h = _cr.canonical(_shown(c) or k, roster)
        if h and h != k and _cls_winner(chars[h]) == kc and not any(
                _read_together(d, v, set(groups[h]), {k}, keys_in, always, visits_of) is True for v in (mine & seen_by[h])):
            groups[h].append(k)
            seen_by[h] |= mine
        else:
            heads.append(k)
            groups[k] = [k]
            seen_by[k] = set(mine)
    return groups


def _merged(chars, keys):
    """One record for a head and its variants: visits, class votes, titles unioned; first/last seen spanned; the head's
    own spelling vote. -> dict"""
    if len(keys) == 1:
        return chars[keys[0]]
    head = chars[keys[0]] or {}
    m = {"name": head.get("name"), "forms": dict(head.get("forms") or {}), "cls": {}, "visitLevel": {}, "titles": {},
         "firstTs": None, "lastTs": None}
    firsts, lasts = [], []
    for k in keys:
        c = chars[k] or {}
        for cl, vs in (c.get("cls") or {}).items():
            per = m["cls"].setdefault(cl, [])
            for v in vs or []:
                if v not in per:
                    per.append(v)
        for v, lv in (c.get("visitLevel") or {}).items():
            prev = m["visitLevel"].get(v)
            m["visitLevel"][v] = lv if prev is None else (prev if lv is None else min(prev, lv))
        for t, n in (c.get("titles") or {}).items():
            m["titles"][t] = int(m["titles"].get(t) or 0) + int(n or 0)
        if isinstance(c.get("firstTs"), (int, float)) and not isinstance(c.get("firstTs"), bool):
            firsts.append(c["firstTs"])
        if isinstance(c.get("lastTs"), (int, float)) and not isinstance(c.get("lastTs"), bool):
            lasts.append(c["lastTs"])
    m["firstTs"] = min(firsts) if firsts else None
    m["lastTs"] = max(lasts) if lasts else None
    return m


def learned(d, min_visits=MIN_VISITS):
    """The characters the reels have witnessed enough: [{name, key, cls, level, pendingLevel, visits, title,
    lastTs, tier, looks, trials, bound}], highest level first. None when the ledger is UNKNOWN.

    #211 - spelling variants of one character are merged first (_merge_groups); a merged row names its variants in
    `aliases` [{key, name, visits}] so a build linked to one still finds it, and the merge is never silent."""
    if d is None:
        return None
    out = []
    _chars = d.get("chars") or {}
    _groups = _merge_groups(d)
    for key, _members in _groups.items():
        c = _merged(_chars, _members)
        visits = sorted(c.get("visitLevel") or {})
        if len(visits) < min_visits:
            continue
        cls_votes = {k: len(set(v)) for k, v in (c.get("cls") or {}).items()}
        if not cls_votes:
            continue
        best = max(cls_votes.values())
        winners = sorted(k for k, n in cls_votes.items() if n == best)
        if len(winners) != 1 or best < min_visits:
            continue                      # two classes tie, or the class itself is not witnessed enough
        seen = sorted([lv for lv in (c.get("visitLevel") or {}).values() if lv], reverse=True)
        level = seen[min_visits - 1] if len(seen) >= min_visits else None
        pending = seen[0] if seen and (level is None or seen[0] > level) else None
        titles = c.get("titles") or {}
        p = proof(d, c)
        row = {"name": _shown(c), "key": key, "cls": winners[0], "level": level, "pendingLevel": pending,
               "visits": len(visits), "title": (max(titles, key=titles.get) if titles else None),
               "lastTs": c.get("lastTs"), "tier": p["tier"], "looks": p["looks"], "trials": p["trials"],
               "misses": p["misses"], "bound": p["bound"], "tierWhy": p["why"]}
        if len(_members) > 1:
            row["aliases"] = [{"key": k, "name": _shown(_chars[k]), "visits": len((_chars[k] or {}).get("visitLevel") or {})}
                              for k in _members[1:]]
        out.append(row)
    out.sort(key=lambda r: (-(r["level"] or 0), str(r["name"]).lower()))
    return out


def surface_of(raw):
    """One lobby or character-panel read -> (row, why).

    row is {name, key, cls, level, kind} or None. screen other and a name the game would refuse bank
    nothing. A note, or an answer that is not JSON, is not an answer: (None, why) with why other than
    "other screen" or "no name". The character panel is accepted only because the reader said so."""
    if raw is None:
        return None, "no answer"
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return None, "not JSON"
    if not isinstance(raw, dict):
        return None, "not an object"
    if raw.get("note"):
        return None, str(raw.get("note"))[:120]
    kind = {"lobby": "lobby", "c-panel": "c-panel", "cpanel": "c-panel"}.get(
        str(raw.get("screen") or "").lower().strip())
    if not kind:
        return None, "other screen"
    name = _clean_name(raw.get("name"))
    if not name:
        return None, "no name"
    return {"name": name, "key": _fold(name), "cls": _clean_class(raw.get("cls")),
            "level": _clean_level(raw.get("level")), "kind": kind}, "one witness"


def surface_confluence(rows):
    """The kinds of surface that named this character, weighted by SURFACE_TIERS. An unknown kind adds 0."""
    import confidence as _cf
    tags = []
    for r in rows or []:
        k = r.get("kind") if isinstance(r, dict) else None
        if k and k not in tags:
            tags.append(k)
    return _cf.confluence(tags, SURFACE_TIERS)


def bank_surface(d, row, image, ts=None, reel=None):
    """Store one witness per (kind, image) on chars[key]["witnesses"]. The same image twice stays one row.

    This does not open a character-select visit and does not set a level, so one lobby frame does not
    teach a character. None when there is nothing to bank.

    #36 (REG-2906) - `reel` is the reel folder the frame was read in, so the witness names the SESSION it saw the
    character in (session_characters). A row banked before it carries none and is placed by its frame."""
    if not isinstance(d, dict) or not isinstance(row, dict):
        return None
    kind = row.get("kind")
    key = row.get("key")
    image = os.path.basename(str(image or ""))
    if kind not in SURFACE_TIERS or not key or not image:
        return None
    c = d["chars"].setdefault(key, {"name": row.get("name"), "cls": {}, "visitLevel": {}, "titles": {},
                                    "firstTs": None, "lastTs": None})
    if not c.get("name"):
        c["name"] = row.get("name")
    witnesses = c.setdefault("witnesses", [])
    for w in witnesses:
        if isinstance(w, dict) and w.get("kind") == kind and w.get("image") == image:
            return w
    stored = {"kind": kind, "image": image, "name": row.get("name"), "cls": row.get("cls"),
              "level": row.get("level"), "ts": ts}
    if reel:
        stored["reel"] = os.path.basename(str(reel))   # REG-2906 the session it was read in
    witnesses.append(stored)
    return stored


def surface_witnesses(d):
    """Every banked surface row, each carrying the confluence of the kinds that named that character.

    None when the ledger is UNKNOWN, never an empty list standing in for a ledger that could not be read."""
    if d is None:
        return None
    out = []
    for key, c in (d.get("chars") or {}).items():
        if not isinstance(c, dict):
            continue
        ws = [w for w in (c.get("witnesses") or []) if isinstance(w, dict)]
        if not ws:
            continue
        conf = surface_confluence(ws)
        for w in ws:
            out.append({"key": key, "name": w.get("name") or c.get("name"), "kind": w.get("kind"),
                        "image": w.get("image"), "cls": w.get("cls"), "level": w.get("level"),
                        "ts": w.get("ts"), "confluence": conf})
    out.sort(key=lambda r: (str(r.get("name")).lower(), str(r.get("kind")), str(r.get("image"))))
    return out


# ── the scan (one bounded tick) ─────────────────────────────────────────────────────────────────────────────
def _default_reader(crop_path):
    import tv_diablo as _td
    return _td.charselect_read(crop_path)


def _default_lobby_reader(frame_path):
    """The whole frame, not the character-select crop. A separate function so a tick test that injects the
    list reader is not retargeted onto the lobby."""
    import tv_diablo as _td
    return _td.surface_read(frame_path)


def _surface_unread(raw):
    """Silence, or a note that the reader did not look, is not a look. A JSON object with no note is an
    answer, including one that names nothing."""
    if raw is None:
        return True
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return False
    return isinstance(raw, dict) and bool(raw.get("note"))


def _surface_call_was_spent(raw):
    """The reader was asked and came back empty. That spends one hourly slot. A throttle, a budget
    note, a missing frame, or a stub that was never asked does not.

    REG-1941 - the reader says so itself (`asked`, tv_diablo._panel_note). The exact note string is only the fallback
    for a reader that does not say: under BOTH the note is the backup's own words, so a Claude timeout was never
    counted and the same frame was re-asked, paid, on every tick."""
    if raw is None:
        return True
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return False
    if isinstance(raw, dict) and "asked" in raw:
        return bool(raw.get("asked"))
    return isinstance(raw, dict) and raw.get("note") == "the reader returned nothing"


def _surface_later(raw):
    """The reader cannot be asked NOW (throttled, over budget, no stub to read). That says nothing about the frame, so
    it never counts toward passing the frame. -> bool"""
    if not isinstance(raw, dict):
        return False
    if "later" in raw:
        return bool(raw.get("later"))
    n = str(raw.get("note") or "")
    return "throttled" in n or n.startswith("not read - ")


#: REG-1941 - a lobby frame whose read keeps not happening (an empty answer, a reader that raises, a frame the reader
#: cannot open) is tried this many times and then PASSED, said in lastWhy and counted in stats.lobbyPassed. It used to
#: hold its reel for ever: the cursor rewound onto it on every tick, no later frame of that reel was ever scanned, and
#: owed() never reached 0. A throttle or a budget block is not the frame's fault and does not count.
LOBBY_TRIES_PER_FRAME = 3


def _ask(reader, path):
    """REG-1941 - THE READER DOOR. A reader that RAISES is a read that did not happen, never an exception out of the tick:
    a subprocess.TimeoutExpired (or a missing CLI's OSError) used to escape tick()'s try/finally, so save() never ran
    and every read already paid for in that tick lost its hourly slot. -> the reader's answer, or a note that says it
    raised (a timeout is a call that ran, so it is `asked`)."""
    try:
        return reader(path)
    except Exception as e:
        import subprocess as _sp
        return {"note": "the reader raised %s - not read" % type(e).__name__,
                "asked": isinstance(e, _sp.TimeoutExpired), "later": False}


def _lobby_tries(rs, p):
    """Count one more read of this lobby frame that did not happen. -> the count for this frame."""
    name = os.path.basename(p)
    lt = rs.get("lobbyTry") if isinstance(rs.get("lobbyTry"), dict) else {}
    n = int(lt.get("n") or 0) + 1 if lt.get("frame") == name else 1
    rs["lobbyTry"] = {"frame": name, "n": n}
    return n


def _rewind_unread(rs, i):
    """The frame was not read. The cursor waits on it."""
    rs["pos"] = i - SAMPLE_EVERY


def _frame_ts(p):
    m = _FRAME_TS.search(os.path.basename(p))
    return int(m.group(1)) if m else None


def _whole_and_empty(raw, rwhy):
    """#114 (REG-1620) - did this read see the WHOLE character list, and nobody on it? -> bool

    normalize() answers ([], "other screen") for a screen that is not the character select - that is no list at all.
    A character-select read with no rows is a list of nobody, and it counts only when the reader said it saw it whole
    (partial False): a cut-off or unsaid list is no evidence against anyone."""
    return rwhy != "other screen" and partial_of(raw) is False


def _close_owed(vid, v):
    """Does this visit still owe a closing read? Its last frame came CLOSE_READ_GAP_MS or more after its last read."""
    lf = v.get("lastFrame") if isinstance(v, dict) else None
    if not isinstance(lf, dict) or v.get("closed"):
        return False
    if v.get("closeOwed"):
        return True                     # #234 - a back-filled visit owes its close whatever the gap (see below)
    return int(lf.get("ts") or 0) - int(v.get("ts") or 0) >= CLOSE_READ_GAP_MS


#: v3888 (REG-3478, the doctor on Dean's PC: our temp dirs older than 3 days - tvd-cs- among them, newest that same day). The
#: tick's crop dir is removed in a finally, and on Windows rmtree(ignore_errors=True) fails SILENTLY while a reader still has
#: a crop open (the same as g5_grok_eyes' REG-1687). So the remove is retried and a leftover counted, and each tick sweeps
#: the crop dirs EARLIER ticks left - matched by this prefix only, and only past CS_SCRATCH_STALE_S, so a concurrent tick's
#: fresh dir is never touched.
CS_SCRATCH_PREFIX = "tvd-cs-"
CS_SCRATCH_STALE_S = 3600


def _clean_scratch_dir(path, attempts=4, pause_s=0.25, sleep=time.sleep):
    """Remove one crop dir. -> True when it is gone (retried: Windows cannot delete an open file)."""
    for k in range(max(1, int(attempts))):
        shutil.rmtree(path, ignore_errors=True)
        if not os.path.exists(path):
            return True
        if k + 1 < attempts:
            sleep(pause_s)
    return False


def _sweep_stale_scratch(root=None, now=None, drop=None):
    """The crop dirs earlier ticks left in the temp dir. -> (removed, left), or None when the dir could not be listed
    (UNKNOWN, never "0 swept")."""
    root = root or tempfile.gettempdir()
    now = time.time() if now is None else float(now)
    drop = drop or (lambda p: _clean_scratch_dir(p, attempts=1))
    try:
        names = [n for n in os.listdir(root) if n.startswith(CS_SCRATCH_PREFIX)]
    except OSError:
        return None
    removed = left = 0
    for n in names:
        p = os.path.join(root, n)
        try:
            if not os.path.isdir(p) or now - os.path.getmtime(p) < CS_SCRATCH_STALE_S:
                continue
        except OSError:
            continue
        if drop(p):
            removed += 1
        else:
            left += 1
    return removed, left


def _backfill_last_frames(d, root, stats, t0, budget_s, clock):
    """#234 step 1 - A VISIT FILED BEFORE v3530 NEVER GETS ITS CLOSING READ. -> (n_found, why)

    MEASURED on his Mac 2026-10-01: the learner knew 12 characters from 5 visits and had 0 logins, so the gear ledger filed
    every worn read UNATTRIBUTED (19 reads, 0 characters) and the in-game cards stayed empty. Each of those visits was
    recorded before v3530 began keeping a visit's lastFrame and the highlighted row (`sel`); with no lastFrame
    _close_owed answers no, and the reel's scan cursor walked past them long ago - so the one read that names the
    character he entered with could never run. This finds such a visit's LAST character-select frame in its own reel,
    once, and owes it one closing read (the hourly cap and tick budget still decide when). A visit that already named its
    row, or whose reel is gone (closed with that reason), is left as it is. [[the-unjoined-end]]"""
    n = 0
    for vid, v in list((d.get("visits") or {}).items()):
        if not isinstance(v, dict) or v.get("closed") or isinstance(v.get("lastFrame"), dict) or v.get("sel"):
            continue
        reel = str(v.get("reel") or str(vid).split("#")[0])
        rd = os.path.join(root, reel)
        if not os.path.isdir(rd):
            v["closed"] = "the reel is gone - its last frame cannot be read"
            continue
        try:
            first = int(str(vid).split("#", 1)[1])
        except (IndexError, ValueError):
            first = int(v.get("ts") or 0)
        # the v3548 eye: the walk RESUMES where a spent budget left it (a cut used to restart the reel from its first
        # frame on every tick, holding the closing reads and the live scan behind it for ever)
        bf = v.get("bf") if isinstance(v.get("bf"), dict) else {}
        start = int(bf.get("pos") or first)
        last = tuple(bf["last"]) if isinstance(bf.get("last"), list) and len(bf["last"]) == 2 else None
        for p in sorted(glob.glob(os.path.join(rd, "f_*.jpg"))):
            ts = _frame_ts(p) or 0
            if ts < start:
                continue
            # the visit is over VISIT_GAP_S after its last select frame - or after it BEGAN, when none is seen (the v3548
            # eye: with no hit near its start the walk ran on and took the NEXT visit's screen as this one's)
            if ts - (last[1] if last else first) > VISIT_GAP_S * 1000:
                break
            if clock() - t0 > budget_s:
                v["bf"] = {"pos": ts, "last": list(last) if last else None}
                return n, "tick budget spent"
            hit, _w = looks_like_char_select(stats(p))
            if hit:
                last = (os.path.basename(p), ts)
        v.pop("bf", None)
        if last is None:
            v["closed"] = "no character-select frame of this visit is left in its reel"
            continue
        v["lastFrame"] = {"reel": reel, "frame": last[0], "ts": last[1]}
        v["closeOwed"] = "backfill"
        n += 1
    return n, ""


def _closing_reads(d, root, reader, st, now_s, work, t0, budget_s, clock):
    """#103 step B — read the LAST frame of every finished visit that ran past its reads, once. -> (n_read, why)

    He may move the cursor before pressing Play; the first reads saw the row the game highlighted on arrival. A visit
    is finished once the scan has walked VISIT_GAP_S of frame time past its last frame, or its reel is fully walked and
    that long has passed. Same hourly cap and tick budget as every read; a visit whose last frame is gone is closed
    with that reason, never read from a guess."""
    n, why = 0, ""
    now_ms = int(now_s * 1000)
    for vid, v in list((d.get("visits") or {}).items()):
        if not _close_owed(vid, v):
            continue
        lf = v["lastFrame"]
        rs = (d.get("reels") or {}).get(lf.get("reel"))
        if not isinstance(rs, dict):
            v["closed"] = "the reel is gone - its last frame cannot be read"
            continue
        lts = int(lf.get("ts") or 0)
        over = (int(rs.get("scannedTs") or 0) - lts > VISIT_GAP_S * 1000
                or (int(rs.get("pos") or 0) >= int(rs.get("frames") or 0) and now_ms - lts > VISIT_GAP_S * 1000))
        if not over:
            continue
        if clock() - t0 > budget_s:
            return n, "tick budget spent"
        if len(st["readTs"]) >= READS_PER_HOUR:
            return n, "hourly read cap (%d) reached" % READS_PER_HOUR
        path = os.path.join(root, str(lf.get("reel")), str(lf.get("frame")))
        crop = panel_crop(path, work) if os.path.exists(path) else None
        if not crop:
            v["closed"] = "its last frame could not be opened"
            continue
        raw = _ask(reader, crop)
        if _surface_later(raw):
            # REG-1945 - the reader cannot be asked now: the visit keeps its closing read owed, never closed "refused"
            return n, "closing read not read: " + str((raw or {}).get("note") or "")[:120]
        st["readTs"].append(now_s)
        rows, rwhy = normalize(raw)
        if rows is None:
            st["refused"] = int(st.get("refused") or 0) + 1
            st["lastWhy"] = "closing read refused: " + rwhy
            v["closed"] = "refused: " + rwhy[:80]
            continue
        st["reads"] = int(st.get("reads") or 0) + 1
        n += 1
        if rows:
            sel, _sw = selected_of(raw, rows)
            record(d, vid, rows, {"reel": lf.get("reel"), "ts": lts, "reader": "vision-close",
                                  "frames": [lf.get("frame")], "partial": partial_of(raw), "selected": sel})
        elif _whole_and_empty(raw, rwhy):
            record(d, vid, [], {"reel": lf.get("reel"), "ts": lts, "reader": "vision-close",
                                "frames": [lf.get("frame")], "partial": False})
        v["closed"] = "read"
    return n, why


def logins(d):
    """#103 step B — THE SESSION'S CHARACTER, AS A LOGIN. Konyo: "a sessions character selection then moving forward..
    scenarios future wise are linked to that character ... same logic getting routed down".

    Every visit whose screen said which row was highlighted -> {reel, sessionId, ts, character, visit, reader}. The LATEST
    read that named one decides (the closing read, when the visit ran past its first reads). A visit whose closing read
    is still owed is left out until it is read - its first highlight may not be the character he entered with. The
    sessionId is the reel's folder without its "reel_" (the journal's own key). None when the ledger is UNKNOWN."""
    if d is None:
        return None
    out = []
    for vid, v in (d.get("visits") or {}).items():
        if not isinstance(v, dict) or _close_owed(vid, v):
            continue
        sel = [x for x in (v.get("sel") or []) if isinstance(x, dict) and x.get("name")]
        if not sel:
            continue
        best = max(sel, key=lambda x: int(x.get("ts") or 0))
        reel = str(v.get("reel") or str(vid).split("#")[0])
        row = {"reel": reel, "sessionId": reel[5:] if reel.startswith("reel_") else reel,
               "ts": int(best.get("ts") or 0) or _visit_ts(vid, v), "character": best["name"],
               "visit": vid, "reader": best.get("reader")}
        # #115 (REG-1619, the #231 eye on v3529) - A CLOSE THAT WAS TRIED AND NAMED NO ROW CONFIRMS NOTHING. `closed` is set
        # only for a visit that ran past its reads; when the closing read was refused, its frame would not open, its reel
        # was gone, or it saw no highlighted row, the newest name is still the ARRIVAL highlight - the one this wait
        # exists to distrust. Said as `unconfirmed`, never as the character: login_rows skips it, so the session's gear
        # is unattributed (with its denominator) instead of filed under a guess. [[unknown-stays-unknown]]
        if v.get("closed") and best.get("reader") != "vision-close":
            row.update(character=None, unconfirmed=best["name"],
                       why="the closing read named no row (%s) - the first highlight may not be the character he entered "
                           "with" % str(v.get("closed"))[:80])
        out.append(row)
    out.sort(key=lambda r: (r["ts"] or 0))
    return out


# ── #36 (REG-2906): WHICH CHARACTER A SESSION IS ON ────────────────────────────────────────────────────────────────
#: His ruling, 2026-10-28 11:30: read the character from the screens he already passes through - the character-select
#: screen at login and the in-game C panel - into ONE logic that binds a session's reads to that character, so each reel
#: knows whose stash it filmed. The two halves existed apart: logins() named the row highlighted at character select
#: (#103 step B), the lobby / C-panel reader banked a witness naming the character (#149), and neither said which reel it
#: was read in for the vault - its sightings carried no holder. This joins them, read-only, over the learner's ledger.
#: REG-2910 - THE C PANEL'S PIXEL BAND: None until a filmed C panel measures one (CPANEL_SAY). While it is None no scan
#: asks the reader about a C panel, so an ask to open it cannot name a session, and the guided ask never names it.
CPANEL_BAND = None
SESSION_SAY_NONE = "no character-select, lobby or C-panel read names a character in this session"


def session_ask():
    """#36 (REG-2910) - the screen a guided ask may send him to: one a scan actually reads. -> (ask, why)

    His rule is that a doubt becomes a guided ask, and an ask he follows that cannot work is a promise the board breaks.
    Character select and the lobby have measured pixel bands and are read on every scan; the C panel is named only once
    CPANEL_BAND exists."""
    if CPANEL_BAND:
        return "open the C panel once", None
    return ("open character select, or the lobby, once",
            "the C panel is not asked for: no pixel band finds it yet, so a scan never reads one")


def _reel_start(name):
    m = re.match(r"^reel_s_(\d{10,})$", str(name or ""))
    return int(m.group(1)) if m else None


def reel_of_frame(root=None):
    """-> f(image) naming the reel folder that holds that frame, or None. For a witness banked before REG-2906, which
    stored only the frame's file name: the frame's own time (f_<ms>) names the newest reel that started at or before
    it, and the file must be there - a frame no reel on this PC holds is unplaced, never guessed into a neighbour."""
    root = root or hist_root()
    try:
        starts = sorted((s, n) for n in os.listdir(root) for s in [_reel_start(n)] if s is not None)
    except Exception:
        starts = None       # the reel tree would not list: every old witness is unplaced (counted), never "no reels"

    def f(image):
        ts = _frame_ts(str(image or ""))
        if ts is None or not starts:
            return None
        best = None
        for s, n in starts:
            if s <= ts:
                best = n
            else:
                break
        if best and os.path.isfile(os.path.join(root, best, os.path.basename(str(image)))):
            return best
        return None
    return f


def _sid(reel):
    r = str(reel or "")
    return r[5:] if r.startswith("reel_") else r


def session_characters(d, reel_of=None, carried=None, report=None):
    """#36 (REG-2906) - the character each SESSION (one reel: the journal's sessionId) is on. -> {sessionId: [span]} or
    None when the ledger is UNKNOWN.

    A span is {from, character, key, via, at, why}: a character-select login opens one at its frame time (`from`) - a
    login is a boundary, he can change character only there - and the rows before the reel's first login are the span
    with from None. A lobby or C-panel read names the span it falls in. The name goes through the learner's own fold
    (_merge_groups: Konylock / Konyblock are KonyoLock), so every surface says one character one way. Two reads naming
    different characters in one span leave it UNKNOWN with both names - never the newer one guessed over the older.
    A login whose closing read named no row (logins' `unconfirmed`) is a boundary with an UNKNOWN character. The span
    before the first login takes `carried` (sessionId -> name, the rollover chain the gear ledger already keeps) when
    nothing in it names anyone, said as `carried`. A session no read names is absent: UNKNOWN to every caller.
    `report` (a dict, when given) gets `unplaced`: the witnesses no reel on this PC holds."""
    if d is None:
        return None
    chars = d.get("chars") or {}
    groups = _merge_groups(d)
    head = {}
    for h, ks in groups.items():
        for k in ks:
            head[k] = h

    def named(raw):
        k = _fold(raw)
        if not k:
            return None, None
        h = head.get(k, k)
        c = chars.get(h)
        return (_shown(c) if isinstance(c, dict) else None) or _clean_name(raw) or raw, h

    ev = {}
    for L in logins(d) or []:
        sid = str(L.get("sessionId") or "")
        if not sid:
            continue
        nm, key = named(L.get("character")) if L.get("character") else (None, None)
        ev.setdefault(sid, []).append({"ts": int(L.get("ts") or 0) or None, "kind": "char-select", "name": nm, "key": key,
                                       "why": L.get("why") if not nm else None})
    unplaced = 0
    for key, c in chars.items():
        for w in ((c or {}).get("witnesses") or []) if isinstance(c, dict) else []:
            if not isinstance(w, dict) or w.get("kind") not in SURFACE_TIERS:
                continue
            reel = w.get("reel") or (reel_of(w.get("image")) if reel_of else None)
            if not reel:
                unplaced += 1
                continue
            nm, k = named(w.get("name") or (c or {}).get("name") or key)
            ts = w.get("ts") if isinstance(w.get("ts"), (int, float)) and not isinstance(w.get("ts"), bool) else None
            ev.setdefault(_sid(reel), []).append({"ts": int(ts) if ts else None, "kind": w.get("kind"), "name": nm,
                                                  "key": k, "why": None})
    out = {}
    for sid, es in ev.items():
        es.sort(key=lambda e: (e["ts"] is None, e["ts"] or 0))
        spans = [{"from": None, "character": None, "key": None, "via": None, "at": None, "why": SESSION_SAY_NONE}]
        for e in es:
            if e["kind"] == "char-select":
                spans.append({"from": e["ts"], "character": e["name"], "key": e["key"], "via": "char-select",
                              "at": e["ts"], "why": None if e["name"] else (e.get("why") or "the login named no row")})
                continue
            sp = spans[-1]
            if sp.get("conflict"):
                sp["conflict"] = sorted(set(sp["conflict"]) | {e["name"]})
            elif sp["key"] is None:
                sp.update(character=e["name"], key=e["key"], via=e["kind"], at=e["ts"], why=None)
            elif sp["key"] is not None and sp["key"] != e["key"]:
                sp.update(conflict=sorted({sp["character"], e["name"]}), character=None, key=None, via=None,
                          why="two screens in one span named different characters (%s)"
                              % " / ".join(sorted({str(sp["character"]), str(e["name"])})))
        first = spans[0]
        if first["character"] is None and not first.get("conflict") and carried and carried.get(sid):
            first.update(character=str(carried[sid]), via="carried", why=None,
                         key=head.get(_fold(carried[sid]), _fold(carried[sid])))
        if first["character"] is None and not first.get("conflict") and len(spans) > 1:
            spans = spans[1:]                  # nothing before the login: the session is the login's
        out[sid] = spans
    if isinstance(report, dict):
        report["unplaced"] = unplaced
    return out


def session_view(d, gd=None):
    """#36 (REG-2909) - the ONE view of which character each session is on, asked by the console's answer and by the
    doctor: the learner's ledger `d`, the reels' frames on this PC, and the gear ledger `gd`'s rollover chain as `carried`
    (each game session's later reels carry its login's character). -> (sessions | None, report)"""
    carried = {}
    for gs in ((gd or {}).get("gameSessions") or {}).values() if isinstance(gd, dict) else []:
        if isinstance(gs, dict) and gs.get("character"):
            for rs in (gs.get("reels") or [])[1:]:
                carried[str(rs)] = gs["character"]
    report = {}
    return session_characters(d, reel_of=reel_of_frame(), carried=carried, report=report), report


def session_character_at(sessions, sid, ts=None):
    """The character a read at `ts` in session `sid` was taken on, from session_characters' map. -> (name, why)

    The span with the newest `from` at or before ts; a read with no time takes the session's character only when every
    span names the same one. (None, why) is UNKNOWN - never the nearest name."""
    spans = (sessions or {}).get(str(sid or ""))
    if not isinstance(spans, list) or not spans:
        return None, SESSION_SAY_NONE
    if ts is None:
        names = {s.get("character") for s in spans}
        if len(names) == 1 and None not in names:
            return spans[0]["character"], None
        return None, "the read has no time and the session names more than one span"
    pick = session_span_at(sessions, sid, ts)
    if pick is None:
        return None, "the read came before the session's first login, and nothing before it names a character"
    return pick.get("character"), (None if pick.get("character") else pick.get("why"))


def session_span_at(sessions, sid, ts):
    """#36 (REG-2911) - the span of session `sid` the moment `ts` falls in: the one with the newest `from` at or before
    it (a span with no `from` is the session's start). -> the span, or None (the session is absent, ts is None, or the
    moment came before the session's first span). The one pick the gear ledger and session_character_at share."""
    spans = (sessions or {}).get(str(sid or ""))
    if not isinstance(spans, list) or not spans or ts is None:
        return None
    pick = None
    for s in spans:
        if isinstance(s, dict) and (s.get("from") is None or (isinstance(s.get("from"), (int, float)) and s["from"] <= ts)):
            pick = s
    return pick


def scanned_reel(d, reel):
    """#103 step B — has the learner said everything it will say about this reel? -> True / False / None (UNKNOWN)

    The printer's order: the character a session entered with is the TEMPLATE every later station routes by, so the gear
    ledger files a reel only once this station has spoken for it - every frame on disk walked, no visit in it still
    owing its closing read."""
    if d is None:
        return None
    rs = (d.get("reels") or {}).get(reel)
    if not isinstance(rs, dict):
        return False
    if int(rs.get("pos") or 0) < int(rs.get("frames") or 0):
        return False
    for vid, v in (d.get("visits") or {}).items():
        if str(vid).split("#")[0] == reel and _close_owed(vid, v):
            return False
    return True


def _safe_wh(size_of, path):
    if not size_of:
        return None
    try:
        return size_of(path)
    except Exception:
        return None


def _open_lobby_cursors(rs, nframes):
    """First time this code sees the reel, split what the char cursor already passed from what it has not.

    A finished reel is lobby-checked from the start: its char cursor is done, and a lobby it filmed
    before this check existed would otherwise stay a zero. A reel in the middle keeps that prefix
    and continues the live edge at pos. A reel at 0 starts at 0."""
    if rs.get("lobbyOpened"):
        return
    rs["lobbyOpened"] = True
    pos = int(rs.get("pos") or 0)
    if pos < 0:
        pos = 0
    if pos > nframes:
        pos = nframes
    if pos <= 0 or pos >= nframes:
        rs["lobbyPos"] = 0
        return
    rs["lobbyPrefix"] = pos
    rs["lobbyPrefixPos"] = 0
    rs["lobbyPos"] = pos


def _lobby_mark(rs, fi, matched, size_of, path, st):
    """Count this frame once, on the cursor that is sitting on it, then move that cursor past it."""
    step = fi + SAMPLE_EVERY
    if int(rs.get("lobbyPrefixPos") or 0) == fi and int(rs.get("lobbyPrefix") or 0) > fi:
        note_lobby_size(st, _safe_wh(size_of, path), matched)
        rs["lobbyPrefixPos"] = step
        return
    if int(rs.get("lobbyPos") or 0) == fi:
        note_lobby_size(st, _safe_wh(size_of, path), matched)
        rs["lobbyPos"] = step


def _lobby_skip(rs, fi):
    """A character-list frame is not a lobby check. Move the cursor past it without a count."""
    step = fi + SAMPLE_EVERY
    if int(rs.get("lobbyPrefixPos") or 0) == fi and int(rs.get("lobbyPrefix") or 0) > fi:
        rs["lobbyPrefixPos"] = step
        return
    if int(rs.get("lobbyPos") or 0) == fi:
        rs["lobbyPos"] = step


def _lobby_handle(rs, p, fi, st, d, surface_stats, surface_reader, size_of, now_s, acc, rewind_i=None):
    """One frame that is not the character list. The read rules are the live scan's rules.

    acc keys: reads, surfaces, why, stop. A read that did not happen does not move the lobby
    cursor. On the live scan, rewind_i is the char cursor after it stepped, and that cursor
    waits on the frame. A backfill leaves the char cursor where it is."""
    lhit, _lw = looks_like_lobby(surface_stats(p))
    ts = _frame_ts(p) or 0
    if lhit:
        lop = rs.get("lobby")
        if (not isinstance(lop, dict)
                or ts - int(lop.get("lastTs") or 0) > VISIT_GAP_S * 1000):
            lop = {"firstTs": ts, "lastTs": ts, "reads": 0}
        lop["lastTs"] = ts
        rs["lobby"] = lop
        if int(lop.get("reads") or 0) < 1:
            if len(st["readTs"]) >= READS_PER_HOUR:
                if rewind_i is not None:
                    _rewind_unread(rs, rewind_i)
                acc["why"] = "hourly read cap (%d) reached" % READS_PER_HOUR
                acc["stop"] = True
                return
            raw = _ask(surface_reader, p)
            row, rwhy = surface_of(raw)
            if _surface_unread(raw):
                if _surface_call_was_spent(raw):
                    st["readTs"].append(now_s)
                if not _surface_later(raw) and _lobby_tries(rs, p) >= LOBBY_TRIES_PER_FRAME:
                    # REG-1941 - the frame keeps failing: pass it, say so, and let the scan go on. The visit stays
                    # unread (lobby reads 0), so the next frame of the same visit is still asked.
                    rs.pop("lobbyTry", None)
                    st["lobbyPassed"] = int(st.get("lobbyPassed") or 0) + 1
                    st["lobbyPassedLast"] = {"reel": os.path.basename(os.path.dirname(p)), "frame": os.path.basename(p),
                                             "tries": LOBBY_TRIES_PER_FRAME, "why": rwhy, "ts": int(now_s * 1000)}
                    st["lastWhy"] = "lobby frame %s passed after %d reads that did not happen: %s" % (
                        os.path.basename(p), LOBBY_TRIES_PER_FRAME, rwhy)
                    _lobby_mark(rs, fi, lhit, size_of, p, st)
                    return
                if rewind_i is not None:
                    _rewind_unread(rs, rewind_i)
                acc["why"] = "surface not read: " + rwhy
                acc["stop"] = True
                return
            rs.pop("lobbyTry", None)
            st["readTs"].append(now_s)
            lop["reads"] = 1
            if row is None and rwhy not in ("other screen", "no name"):
                st["refused"] = int(st.get("refused") or 0) + 1
                st["lastWhy"] = "surface read refused: " + rwhy
            else:
                st["reads"] = int(st.get("reads") or 0) + 1
                acc["reads"] = int(acc.get("reads") or 0) + 1
                if row:
                    bank_surface(d, row, os.path.basename(p), ts, reel=os.path.basename(os.path.dirname(p)))
                    acc["surfaces"] = int(acc.get("surfaces") or 0) + 1
    _lobby_mark(rs, fi, lhit, size_of, p, st)


def _lobby_backfill(d, reels, stats, surface_stats, surface_reader, size_of, st, now_s, t0, budget_s, clock, acc):
    """Lobby-check frames the char cursor already passed. Half the tick, then the live scan keeps the rest.

    Stopping here for the half budget is not a reason to stop the live scan. A cap or a read that
    did not happen is, and acc says so."""
    # deadline is an absolute clock reading. Elapsed seconds are never larger
    # than it, so the half budget never returned and the full budget then
    # skipped the live scan.
    deadline = t0 + (float(budget_s) * 0.5)
    for rd in reels:
        if clock() > deadline:
            return
        name = os.path.basename(rd)
        frames = sorted(glob.glob(os.path.join(rd, "f_*.jpg")))
        rs = d["reels"].setdefault(name, {"pos": 0, "frames": 0, "open": None})
        rs["frames"] = len(frames)
        _open_lobby_cursors(rs, len(frames))
        ranges = []
        if int(rs.get("lobbyPrefix") or 0) > int(rs.get("lobbyPrefixPos") or 0):
            ranges.append("prefix")
        if int(rs.get("pos") or 0) >= len(frames) and int(rs.get("lobbyPos") or 0) < len(frames):
            ranges.append("done")
        for which in ranges:
            while True:
                if clock() > deadline:
                    return
                if which == "prefix":
                    fi = int(rs.get("lobbyPrefixPos") or 0)
                    end = int(rs.get("lobbyPrefix") or 0)
                else:
                    fi = int(rs.get("lobbyPos") or 0)
                    end = len(frames)
                if fi >= end or fi >= len(frames):
                    break
                if clock() - t0 > budget_s:
                    acc["why"] = "tick budget spent"
                    acc["stop"] = True
                    return
                p = frames[fi]
                hit, _w = looks_like_char_select(stats(p))
                if hit:
                    _lobby_skip(rs, fi)
                    if (which == "prefix" and int(rs.get("lobbyPrefixPos") or 0) == fi) or (
                            which == "done" and int(rs.get("lobbyPos") or 0) == fi):
                        if which == "prefix":
                            rs["lobbyPrefixPos"] = fi + SAMPLE_EVERY
                        else:
                            rs["lobbyPos"] = fi + SAMPLE_EVERY
                    continue
                _lobby_handle(rs, p, fi, st, d, surface_stats, surface_reader, size_of, now_s, acc)
                if acc.get("stop"):
                    return
                if which == "prefix" and int(rs.get("lobbyPrefixPos") or 0) == fi:
                    rs["lobbyPrefixPos"] = fi + SAMPLE_EVERY
                elif which == "done" and int(rs.get("lobbyPos") or 0) == fi:
                    rs["lobbyPos"] = fi + SAMPLE_EVERY


def tick(root=None, stats=None, reader=None, now=None, budget_s=TICK_BUDGET_S, clock=time.time,
         surface_stats=None, surface_reader=None, size_of=None):
    """One bounded pass: continue scanning the reels (newest first) for candidate frames, read at most
    MAX_READS_PER_VISIT per visit and READS_PER_HOUR in all, fold the answers in, save. Returns a status dict.

    A frame that is not the character-select list is asked whether it is the create-game lobby. One read of
    that whole frame per lobby visit, on the same hourly cap. The cap rewinds onto the frame it did not read.
    A note, or no answer, is a read that did not happen: the cursor waits on that frame and the visit stays
    unread. A call that came back empty spends one hourly slot, so a timeout cannot retry without limit.
    A throttle or a budget note does not. An answer that names nothing is a look, and it is not retried.
    A lobby frame that fails LOBBY_TRIES_PER_FRAME times for any other reason is passed and said (REG-1941),
    a reader that raises is a read that did not happen, and any stop ends the whole scan.
    Each lobby check is counted by the file's pixel size. Frames the char cursor already finished are
    checked on a backfill, so a reel scanned before the lobby rule is not a zero."""
    d = load()
    if d is None:
        return {"ok": False, "why": "the ledger could not be read — UNKNOWN, nothing written"}
    _console_tick = root is None
    root = root or hist_root()
    stats = stats or panel_stats
    reader = reader or _default_reader
    surface_stats = surface_stats or lobby_stats
    surface_reader = surface_reader or _default_lobby_reader
    size_of = size_of or file_wh
    now_s = float(now if now is not None else clock())
    t0 = clock()
    st = d["stats"]
    st["ticks"] = int(st.get("ticks") or 0) + 1
    st["readTs"] = [t for t in (st.get("readTs") or []) if now_s - float(t) < 3600]
    reels = sorted(glob.glob(os.path.join(root, "reel_*")), reverse=True)
    alive = set(os.path.basename(r) for r in reels)
    for gone in [k for k in d["reels"] if k not in alive]:
        d["reels"].pop(gone, None)            # the FIFO deleted it; its visits stay in the ledger
    # v3888 (REG-3478) - an earlier tick's crop dir that Windows would not let go of is swept here, by its own name. Only the
    # console's own tick sweeps (it hands no root): a law that hands its own hist never reaches the machine's temp dir.
    _cs_gone = _sweep_stale_scratch(now=now_s) if _console_tick else None
    if _cs_gone is not None:
        st["scratchSwept"] = int(st.get("scratchSwept") or 0) + _cs_gone[0]
    work = tempfile.mkdtemp(prefix=CS_SCRATCH_PREFIX)
    scanned = candidates = reads = closed = surfaces = 0
    finished = []
    why = ""
    try:
        # #234 - a visit filed before v3530 is given its last frame first, so the close below can read it
        _bf, why = _backfill_last_frames(d, root, stats, t0, budget_s, clock)
        if _bf:
            st["backfilled"] = int(st.get("backfilled") or 0) + _bf
        # #103 step B - a visit that ended in an earlier tick and still owes its closing read goes first
        if not why:
            closed, why = _closing_reads(d, root, reader, st, now_s, work, t0, budget_s, clock)
        if not why:
            acc = {"reads": 0, "surfaces": 0, "why": "", "stop": False}
            _lobby_backfill(d, reels, stats, surface_stats, surface_reader, size_of, st, now_s,
                            t0, budget_s, clock, acc)
            reads += int(acc.get("reads") or 0)
            surfaces += int(acc.get("surfaces") or 0)
            if acc.get("stop"):
                why = acc.get("why") or why
        for rd in ([] if why else reels):
            name = os.path.basename(rd)
            frames = sorted(glob.glob(os.path.join(rd, "f_*.jpg")))
            rs = d["reels"].setdefault(name, {"pos": 0, "frames": 0, "open": None})
            rs["frames"] = len(frames)
            _open_lobby_cursors(rs, len(frames))
            i = int(rs.get("pos") or 0)
            pos0 = i
            while i < len(frames):
                if clock() - t0 > budget_s:
                    why = "tick budget spent"
                    break
                p = frames[i]
                fi = i
                i += SAMPLE_EVERY
                rs["pos"] = i
                scanned += 1
                # #103 step B - how far in FRAME time the cursor has walked: a visit is over once the scan is past it
                rs["scannedTs"] = max(int(rs.get("scannedTs") or 0), _frame_ts(p) or 0)
                hit, _w = looks_like_char_select(stats(p))
                if not hit:
                    acc = {"reads": 0, "surfaces": 0, "why": "", "stop": False}
                    _lobby_handle(rs, p, fi, st, d, surface_stats, surface_reader, size_of, now_s,
                                  acc, rewind_i=i)
                    reads += int(acc.get("reads") or 0)
                    surfaces += int(acc.get("surfaces") or 0)
                    if acc.get("stop"):
                        why = acc.get("why") or why
                        break
                    continue
                _lobby_skip(rs, fi)
                candidates += 1
                ts = _frame_ts(p) or 0
                op = rs.get("open")
                if not op or ts - int(op.get("lastTs") or 0) > VISIT_GAP_S * 1000:
                    op = {"id": "%s#%d" % (name, ts), "firstTs": ts, "lastTs": ts, "reads": 0}
                op["lastTs"] = ts
                op["lastFrame"] = os.path.basename(p)
                rs["open"] = op
                # #103 step B - the visit's LAST frame on the screen is the row he pressed Play on
                _vrec = d["visits"].get(op["id"])
                if isinstance(_vrec, dict):
                    _vrec["lastFrame"] = {"reel": name, "frame": op["lastFrame"], "ts": ts}
                if op["reads"] >= MAX_READS_PER_VISIT:
                    continue
                if len(st["readTs"]) >= READS_PER_HOUR:
                    # #231 5909410674 — THE CAP IS A RATE, SO IT STOPS THE SCAN ON THIS FRAME. It used to `continue`
                    # after the cursor had stepped past it, walking every later frame and reel unread and saving those
                    # cursors: a visit found after the cap fell out of owed() for good. The frame waits for the hour.
                    why = "hourly read cap (%d) reached" % READS_PER_HOUR
                    rs["pos"] = i - SAMPLE_EVERY
                    break
                crop = panel_crop(p, work)
                if not crop:
                    continue
                raw = _ask(reader, crop)
                if _surface_later(raw):
                    # REG-1945 (the #231 eye on v3574) - a throttle or a budget block is a read that did not happen,
                    # not a refusal. It spent one of the visit's MAX_READS_PER_VISIT and an hourly slot, so a throttle
                    # across a visit's frames used both reads and the visit was never read once it lifted (measured:
                    # 2 reads spent, 0 visits recorded). The frame waits for the reader, like the lobby's.
                    rs["pos"] = i - SAMPLE_EVERY
                    why = "list not read: " + str((raw or {}).get("note") or "")[:120]
                    break
                st["readTs"].append(now_s)
                op["reads"] += 1
                rows, rwhy = normalize(raw)
                if rows is None:
                    st["refused"] = int(st.get("refused") or 0) + 1
                    st["lastWhy"] = "read refused: " + rwhy
                    continue
                st["reads"] = int(st.get("reads") or 0) + 1
                reads += 1
                if rows:
                    sel, _sw = selected_of(raw, rows)
                    record(d, op["id"], rows, {"reel": name, "ts": ts, "reader": "vision",
                                               "frames": [os.path.basename(p)], "partial": partial_of(raw),
                                               "selected": sel})
                    d["visits"][op["id"]]["lastFrame"] = {"reel": name, "frame": os.path.basename(p), "ts": ts}
                elif _whole_and_empty(raw, rwhy):
                    # #114 (REG-1620, the #231 eye on v3528) - A WHOLE LIST THAT SHOWS NOBODY IS A LOOK. It was never
                    # stored (only `if rows:` recorded), so it could not count against the characters it stopped
                    # showing; proof() needs the visit, with partial False, to call it a miss. Another screen is not.
                    record(d, op["id"], [], {"reel": name, "ts": ts, "reader": "vision",
                                             "frames": [os.path.basename(p)], "partial": False})
                    d["visits"][op["id"]]["lastFrame"] = {"reel": name, "frame": os.path.basename(p), "ts": ts}
            if pos0 < len(frames) <= int(rs.get("pos") or 0):
                finished.append(name)
            # REG-1941 (the #231 eye on v3574) - EVERY stop ends the scan, not only the budget and the cap. A lobby read
            # that did not happen broke this reel's loop and the next reel was scanned with `why` already set: its
            # char-select reads ran against the same throttle and were counted as refusals (a visit's reads and the
            # hourly cap spent on reads that never happened), the closing reads were skipped, and a later note
            # overwrote the first failure's reason.
            if why:
                break
        if not why:
            n_close, cwhy = _closing_reads(d, root, reader, st, now_s, work, t0, budget_s, clock)
            closed += n_close
            why = cwhy or why
    finally:
        # the crops are throwaway; a nested dir must not strand it. v3888 (REG-3478): retried, and one that will not go is
        # COUNTED - rmtree(ignore_errors=True) failed silently on Windows while a reader still held a crop open
        if not _clean_scratch_dir(work):
            st["scratchLeft"] = int(st.get("scratchLeft") or 0) + 1
    st["frames"] = int(st.get("frames") or 0) + scanned
    st["lastTs"] = int(now_s * 1000)
    if why:
        st["lastWhy"] = why
    save(d)
    return {"ok": True, "scanned": scanned, "candidates": candidates, "reads": reads, "closed": closed,
            "surfaces": surfaces, "finished": finished, "why": why or "scanned"}


def owed(d, root=None):
    """Frames not yet scanned, over the reels on disk. None when either side cannot be counted."""
    if d is None:
        return None
    try:
        n = 0
        for rd in glob.glob(os.path.join(root or hist_root(), "reel_*")):
            total = len(glob.glob(os.path.join(rd, "f_*.jpg")))
            pos = int(((d.get("reels") or {}).get(os.path.basename(rd)) or {}).get("pos") or 0)
            n += max(0, -(-(total - pos) // SAMPLE_EVERY))
        return n
    except Exception:
        return None


def status(root=None):
    """The heart's vocabulary: on · worked · lastTs · owed — plus what was learned. UNKNOWN is a state."""
    d = load()
    if d is None:
        return {"on": True, "worked": None, "lastTs": None, "owed": None, "learned": None,
                "say": "the character ledger could not be read — UNKNOWN"}
    st = d.get("stats") or {}
    got = learned(d) or []
    return {"on": True, "worked": int(st.get("reads") or 0), "lastTs": st.get("lastTs"), "owed": owed(d, root),
            "learned": len(got), "seen": len(d.get("chars") or {}), "visits": len(d.get("visits") or {}),
            "ticks": int(st.get("ticks") or 0), "refused": int(st.get("refused") or 0),
            "lobbyBySize": lobby_by_size(d),
            # REG-1941 - lobby frames passed after LOBBY_TRIES_PER_FRAME reads that did not happen, and the last one
            "lobbyPassed": int(st.get("lobbyPassed") or 0), "lobbyPassedLast": st.get("lobbyPassedLast"),
            "say": st.get("lastWhy") or ""}
