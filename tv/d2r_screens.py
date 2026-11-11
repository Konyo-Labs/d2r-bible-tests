# -*- coding: utf-8 -*-
"""v3890 (#188, REG-3514) - THE GAME'S OWN DOOR: D2R's first logo, its title as the witness, then character select.

His words, 11-09: "for a logical thing to have here is for it to be able to identify this and not register them as a
session at all so the last real game sessions from the diablo ii logo game and then character selection screen it
should start from there" - "the recorder" - "if it were inteligent it would be able to register the sessions from the
diablo ii logo screen login regardless of the window being recorder wether it be boosteroid or nvideaplay or or
locally" - "there diablo ii twice... the fire logo and the screen logo for diablo ii that asks me to click any button
before continuing and then im at the character selection so there is a double logo double entrance to it" - "it can
register it the first and the second is the witness to it" - "and the third is the character selection screen" - "it
has no other way to go" - "its the process".

MEASURED on the OLD ALT's real GeForce NOW sessions (two reels, every frame around the start, 800x450, 1 fps): the
Battle.net launcher -> the blue Blizzard logo -> black with the small fire DIABLO II logo in the bottom-right corner
(4 frames each) -> the big fire title "Press Any Key to Begin" (14 and 4 frames) -> "Connecting to Battle.net" ->
character select. Fire = R>=170, R-B>=90, G>=50, R>=G>=B, on the frame scaled to 400 px wide:
    the corner logo   corner box 0.034-0.037 · centre 0 · rest 0 · dark 0.996
    the title         centre 0.22-0.26 · corner 0 · rest ~0.005 · dark ~0.775
    every other screen (the launcher, GeForce NOW's idle dialog, the Blizzard logo, black, character select)
                      centre <= 0.007 · corner 0
And the same day, from 07:41 to 12:30, that PC opened six "sessions" on GeForce NOW's "Your game session ended due to
inactivity" page - the tab still titled "Diablo II: Resurrected" - none of which ever showed one of these screens.

screen_of(src) -> ("logo" | "title" | "connecting" | "hud" | "char-select" | "lobby" | None, why) - "hud" is in a game (the two orbs). The
character select is char_select's own test, called, never copied. chain(marks) reads a reel's marks in order and names
where the game was entered.
"""
import os

FIRE_R, FIRE_RB, FIRE_G = 170, 90, 50
DARK = 40
WIDTH = 400                      # every frame is judged at this width: the corner logo is ~18 px wide there
CENTRE = (0.25, 0.10, 0.75, 0.65)   # x0, y0, x1, y1 as shares of the game area
CORNER = (0.85, 0.80, 1.0, 1.0)
TITLE_CENTRE_MIN = 0.10          # measured 0.22-0.26; every other screen <= 0.007
TITLE_REST_MAX = 0.03
TITLE_DARK_MIN = 0.55
LOGO_CORNER_MIN = 0.012          # measured 0.034-0.037
LOGO_DARK_MIN = 0.95             # measured 0.996
LOGO_ELSEWHERE_MAX = 0.003
CHAIN_GAP_S = 30 * 60            # he may sit at "Press Any Key" a long time; the door is still the door
# IN THE GAME: the red life orb at the bottom left and the blue mana orb at the bottom right. MEASURED on his Mac's reels
# (1440x904, bottom 22% band, each half): in a game red 0.038-0.040 at x~0.25 and blue 0.038-0.041 at x~0.79; GeForce
# NOW's idle page red 0.0071 (the red book in its art), blue 0; the lobby and black 0. One frame with the mana orb
# nearly empty read blue 0.0046 - a reel has thousands of frames, and one is enough.
ORB_BAND = 0.78
ORB_MIN = 0.015
# v3898 (#188, REG-3715) - "CONNECTING TO BATTLE.NET": a dark stone plaque laid over the CENTRE of the fire title, so the
# title test (centre fire) never fires on it and the frame read None - "not D2R" - on the one screen his 11-11 ruling
# makes a trigger. MEASURED on GrokBot's 3 real frames (Mac native, #230 6798662136): the plaque's inner box is colourless
# (saturation 0.008) and dark grey (brightness 0.084) where the title's fire reads 0.39-0.44 / 0.43-0.49; the fire D and O
# still flank it; 91% of the frame is dark. Both halves must meet: GeForce NOW's own loading and queue pages pass the plaque
# half alone (0.038-0.042 / 0.12-0.13) and fail the flanks (no fire). A frame is never called this on one half.
PLAQUE = (0.36, 0.42, 0.64, 0.54)
FLANKS = ((0.24, 0.40, 0.31, 0.56), (0.69, 0.40, 0.76, 0.56))
# The false-match count over EVERY reel frame on his Mac (44,818): 17 matched at the first cut - 16 identical real CONNECTING
# screens (saturation 0.008, brightness 0.084, dark 0.91, in 4 reels GrokBot had not packed) and ONE in-game River of Flame
# frame (0.019 / 0.126 / 0.79: the fire ring and lava played the flanks). Tightened so each bound alone refuses it, and an
# in-game frame (both orbs) is never this screen.
PLAQUE_SAT_MAX = 0.015
PLAQUE_L_MIN, PLAQUE_L_MAX = 0.06, 0.11
FLANK_FIRE_MIN = 0.05
CONNECT_DARK_MIN = 0.85


def _chrome_trim(a):
    """Cut the window's bright title bar / browser chrome off each edge (rows or columns that are bright and flat).
    Black is never cut: the logo and the title ARE black screens."""
    import numpy as np
    g = a.mean(axis=-1)
    h, w = g.shape

    def cut(m, s, n):
        lim = int(n * 0.2)
        lo = 0
        while lo < lim and m[lo] > 150 and s[lo] < 25:
            lo += 1
        hi = n
        while n - hi < lim and hi - 1 > lo and m[hi - 1] > 150 and s[hi - 1] < 25:
            hi -= 1
        return lo, hi
    y0, y1 = cut(g.mean(axis=1), g.std(axis=1), h)
    x0, x1 = cut(g[y0:y1].mean(axis=0), g[y0:y1].std(axis=0), w)
    if (y1 - y0) < h * 0.5 or (x1 - x0) < w * 0.5:
        return a
    return a[y0:y1, x0:x1]


def _small(src):
    """-> an RGB int array WIDTH px wide, the window chrome cut off. Raises when the frame will not open."""
    import numpy as np
    from PIL import Image
    im = src if hasattr(src, "convert") else Image.open(src)
    if not hasattr(src, "convert"):
        try:
            im.draft("RGB", (WIDTH, max(1, int(WIDTH * im.size[1] / float(im.size[0])))))
        except Exception:
            pass
    im = im.convert("RGB")
    a = _chrome_trim(np.asarray(im, dtype=np.int16))
    h, w = a.shape[:2]
    if w != WIDTH:
        im = Image.fromarray(a.astype("uint8")).resize((WIDTH, max(1, int(round(WIDTH * h / float(w))))))
        a = np.asarray(im, dtype=np.int16)
    return a


def stats_of_array(a):
    """-> {"centre", "corner", "rest", "dark"}: the fire share in each box, and the dark share of the whole game."""
    import numpy as np
    H, W = a.shape[:2]
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    fire = (R >= FIRE_R) & (R - B >= FIRE_RB) & (G >= FIRE_G) & (R >= G) & (G >= B)
    dark = a.max(axis=-1) < DARK
    cen = np.zeros(fire.shape, dtype=bool)
    cen[int(H * CENTRE[1]):int(H * CENTRE[3]), int(W * CENTRE[0]):int(W * CENTRE[2])] = True
    cor = np.zeros(fire.shape, dtype=bool)
    cor[int(H * CORNER[1]):, int(W * CORNER[0]):] = True
    rest = ~(cen | cor)
    y0 = int(H * ORB_BAND)
    red = (R >= 110) & (R - G >= 60) & (R - B >= 50)
    blue = (B >= 110) & (B - R >= 50) & (B - G >= 30)
    left, right = red[y0:, :W // 2], blue[y0:, W // 2:]

    def cx(m, off):
        xs = np.nonzero(m)[1]
        return round(float((xs.mean() + off) / W), 3) if len(xs) else None
    pl = a[int(H * PLAQUE[1]):int(H * PLAQUE[3]), int(W * PLAQUE[0]):int(W * PLAQUE[2])]
    fl = np.concatenate([fire[int(H * y0_):int(H * y1_), int(W * x0_):int(W * x1_)].ravel()
                         for (x0_, y0_, x1_, y1_) in FLANKS])
    return {"plaqueL": round(float(pl.sum(axis=-1).mean() / 765.0), 4) if pl.size else None,
            "plaqueSat": round(float((pl.max(axis=-1) - pl.min(axis=-1)).mean() / 255.0), 4) if pl.size else None,
            "flank": round(float(fl.mean()), 4) if fl.size else None,
            "centre": round(float(fire[cen].mean()), 4), "corner": round(float(fire[cor].mean()), 4),
            "rest": round(float(fire[rest].mean()), 4), "dark": round(float(dark.mean()), 4),
            "red": round(float(left.mean()), 4), "blue": round(float(right.mean()), 4),
            "redX": cx(left, 0), "blueX": cx(right, W // 2)}


def is_connecting_stats(st):
    """v3898 (#188, REG-3715) - BOTH halves: the plaque (colourless, dark grey) AND the fire title flanking it. -> bool"""
    try:
        return (st["plaqueSat"] is not None and st["plaqueSat"] < PLAQUE_SAT_MAX
                and PLAQUE_L_MIN <= st["plaqueL"] <= PLAQUE_L_MAX
                and st["flank"] is not None and st["flank"] >= FLANK_FIRE_MIN and st["dark"] >= CONNECT_DARK_MIN
                and not (st.get("red", 0) >= ORB_MIN and st.get("blue", 0) >= ORB_MIN))
    except (KeyError, TypeError):
        return False


def kind_of_stats(st):
    """-> ("logo" | "title" | None, why) from stats_of_array."""
    if not isinstance(st, dict):
        return None, "frame unreadable"
    if is_connecting_stats(st):
        return "connecting", ("CONNECTING TO BATTLE.NET: a colourless dark plaque (%.3f) over the fire title's centre, its fire "
                              "letters flanking it (%.3f)" % (st["plaqueL"], st["flank"]))
    if (st["centre"] >= TITLE_CENTRE_MIN and st["rest"] <= TITLE_REST_MAX and st["dark"] >= TITLE_DARK_MIN):
        return "title", "the fire DIABLO II title fills the centre of a dark screen (centre %.3f)" % st["centre"]
    if (st["corner"] >= LOGO_CORNER_MIN and st["dark"] >= LOGO_DARK_MIN
            and st["centre"] <= LOGO_ELSEWHERE_MAX and st["rest"] <= LOGO_ELSEWHERE_MAX):
        return "logo", "the small fire DIABLO II logo in the corner of a black screen (corner %.3f)" % st["corner"]
    if (st.get("red", 0) >= ORB_MIN and st.get("blue", 0) >= ORB_MIN
            and 0.08 <= (st.get("redX") or 0) <= 0.42 and 0.58 <= (st.get("blueX") or 0) <= 0.92):
        return "hud", "the red life orb and the blue mana orb at the bottom corners - in a game"
    return None, "not D2R's logo, title or in-game orbs"


def screen_of(src, array=None):
    """One frame -> ("logo" | "title" | "connecting" | "hud" | "char-select" | "lobby" | None, why). "frame unreadable" is UNKNOWN, never None-as-no.
    Decodes the frame once (v3894): logo/title/hud and the char-select/lobby look share that image.
    `array` (an RGB int array of the same frame) skips the file open entirely."""
    raw = None
    opened = None
    try:
        if array is not None:
            raw = Image_of(array)
        elif hasattr(src, "convert"):
            raw = src.convert("RGB")
        else:
            from PIL import Image
            opened = Image.open(src)
            raw = opened.convert("RGB")
        a = _small(raw)
    except Exception as e:
        if opened is not None:
            try:
                opened.close()
            except Exception:
                pass
        return None, "frame unreadable (%s)" % type(e).__name__
    if opened is not None:
        try:
            opened.close()
        except Exception:
            pass
    k, why = kind_of_stats(stats_of_array(a))
    if k:
        return k, why
    if raw is not None:
        try:
            import char_select as _cs
            ok, cwhy = _cs.looks_like_char_select(_cs.panel_stats(src if isinstance(src, str) else None, image=raw))
            if ok:
                return "char-select", "char_select: %s" % cwhy
            # the create-game lobby is the game client between games (REG-1873's own band test, called)
            ok, lwhy = _cs.looks_like_lobby(_cs.lobby_stats(src if isinstance(src, str) else None, image=raw))
            if ok:
                return "lobby", "char_select: %s" % lwhy
        except Exception:
            pass
    return None, why


def frozen_non_d2r(paths):
    """v3894 (#188) - True when every readable frame is not a D2R screen and they are the same picture
    (a frozen GeForce NOW / Boosteroid idle page or launcher). False if any frame is D2R, or the pictures
    differ (a loading animation still changing). None if fewer than two frames can be read."""
    kinds, prints = [], []
    for p in paths or []:
        try:
            a = _small(p)
        except Exception:
            continue
        k, why = screen_of(p, array=a)
        if str(why).startswith("frame unreadable"):
            continue
        kinds.append(k)
        prints.append(bytes(a.tobytes()))
    if len(kinds) < 2:
        return None
    if any(k in ("logo", "title", "hud", "char-select", "lobby", "town") for k in kinds):
        return False
    return len(set(prints)) == 1


def Image_of(a):
    from PIL import Image
    return Image.fromarray(a.astype("uint8"))


def chain(marks, gap_s=CHAIN_GAP_S):
    """A reel's marks in time order, [(ts_ms, kind), ...] -> where the game was ENTERED, or None.

    His process: the logo REGISTERS the session, the title is its WITNESS, character select is the door - "it has no
    other way to go". -> {"startTs": the logo (or the title when the logo fell between two frames), "logoTs", "titleTs",
    "charTs", "witnessed": a title after the logo, "entered": character select after the title}. A title alone still
    starts it (the recorder may have begun on the title); a logo with no title after it within gap_s is not a start."""
    ms = sorted([(int(t), k) for t, k in (marks or []) if isinstance(t, (int, float)) and k], key=lambda x: x[0])
    # v3898 (#188, REG-3715) - his 11-11 ruling: on every route the chain is the D2 logo -> CONNECTING TO BATTLE.NET ->
    # character select, starting at the first. CONNECTING witnesses the door the way the title does (it is drawn OVER the
    # title), so a reel whose title fell between two frames is still witnessed by it; the start stays the logo.
    for i, (t, k) in enumerate(ms):
        if k not in ("logo", "title", "connecting"):
            continue
        logo = t if k == "logo" else None
        title = t if k == "title" else None
        conn = t if k == "connecting" else None
        char = None
        for t2, k2 in ms[i + 1:]:
            if t2 - (title or conn or logo) > gap_s * 1000:
                break
            if k2 == "title" and title is None:
                title = t2
            elif k2 == "connecting" and conn is None:
                conn = t2
            elif k2 == "char-select" and (title is not None or conn is not None):
                char = t2
                break
        if title is None and conn is None:
            continue
        return {"startTs": logo if logo is not None else (title if title is not None else conn), "logoTs": logo,
                "titleTs": title, "connectingTs": conn, "charTs": char, "witnessed": logo is not None,
                "entered": char is not None}
    return None


# v3893 (#187/#185, REG-3550 / REG-3552) - THE SHARED SCREEN GATE, ON HIS SCENARIO TEMPLATES.
# Target order (his design): login → CONNECTING → character select (name + class) → lobby
# (game name typed or seen, then chosen) → game-entry portal → in-game in a TOWN (act 1–5).
# Only character names and game names vary across those screens. The D2R door in front of
# CONNECTING is still the fire logo then the title ("Continue" / press any button) from REG-3514.
# screen_of names logo, title, connecting (v3898, REG-3715: measured on real Mac-native frames), char-select, lobby and hud
# (orbs = in a game). This tree has no real Battle.net-login or game-entry-portal frames, and no act-1–5 town
# templates, so those steps are not invented as pixel tests (see SCENARIO_EVIDENCE). Character
# name+class reuse selected_of / logins; game names reuse game_name_of_row (run counting and
# corner-text confluence are later slices).
# Pre-game names — login, logo, title, connecting, char-select, lobby, portal — never reach the
# stash or inventory readers. A frame is in play when it is hud/town (mid-session evidence if
# the reel began in a game) or when the walk has already seen one, and this frame is not itself
# a pre-game screen. Character select is the login door, not yet in a town: it does not open
# the stash reader. Outside the shadow recorder's window the readers do not run.
SCENARIO_ORDER = (
    "login",        # Battle.net Diablo II login
    "logo",         # first fire DIABLO II logo
    "title",        # second logo / press any button
    "connecting",   # CONNECTING...
    "char-select",  # highlighted name + class
    "lobby",        # game name typed or seen, then chosen
    "portal",       # game-entry portal
    "town",         # in a town, act 1–5 (hud orbs witness in-game)
)

# What this tree can actually name. "none" means do not invent a pixel test.
SCENARIO_EVIDENCE = {
    "login": "none — no Battle.net Diablo II login frame on this tree",
    "logo": "measured fire-corner template (REG-3514)",
    "title": "measured fire-centre template (REG-3514)",
    "connecting": "measured plaque-over-title template (REG-3715): GrokBot's 3 Mac-native frames + 16 on his reels; UNKNOWN on GeForce NOW and Boosteroid (no Connecting frame filmed there)",
    "char-select": "char_select.looks_like_char_select (called); selected_of / logins read name + class",
    "lobby": "char_select.looks_like_lobby (called); game name varies — game_name_of_row reads it",
    "portal": "none — no game-entry portal frame measured on this tree",
    "town": "hud orbs (in-game witness); no act-1–5 town templates; corner-text confluence is a later slice",
}

KIND_TO_SCENARIO = {
    "login": "login", "logo": "logo", "title": "title", "connecting": "connecting",
    "char-select": "char-select", "lobby": "lobby", "portal": "portal",
    "hud": "town", "town": "town",
}

PRE_GAME = frozenset(("logo", "title", "char-select", "lobby", "portal", "connecting", "login"))
IN_PLAY = frozenset(("hud", "town"))


def scenario_of_kind(kind):
    """Map a screen_of / mark kind onto his ordered scenario, or None when unlabelled."""
    return KIND_TO_SCENARIO.get(kind)


def readers_may_run(kind, chain=None, recording=True):
    """May the stash / inventory readers see this frame? The shared gate, not a second filter.

    recording False (outside the shadow recorder's window) → no.
    login / logo / title / connecting / char-select / lobby / portal → no.
    hud / town → yes (in a game, including a reel that began mid-session).
    anything else (None: an unlabelled launcher, idle page, or a step we have no template for):
    yes only when `chain` says the walk is in play (`entered` here is that walk flag, set by
    play_after once a hud/town frame has been seen); when chain is omitted this does not invent a refuse.
    """
    if recording is False:
        return False
    if kind in PRE_GAME:
        return False
    if kind in IN_PLAY:
        return True
    if not isinstance(chain, dict):
        return True
    return chain.get("entered") is True


def play_after(kind, chain=None, was_in_play=False):
    """Whether later frames are in play, after seeing this one.

    In play starts at a town / hud frame (in a game). Character select, the lobby and the
    portal do not open it — those are still before the town. `chain` is accepted so the
    walker can pass the shared mark state; the char-select `entered` flag from chain() is
    the login door, not yet a town, so it does not flip this by itself.
    """
    if was_in_play:
        return True
    if kind in IN_PLAY:
        return True
    return False
