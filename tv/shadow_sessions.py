# -*- coding: utf-8 -*-
"""#218 (his ruling 2026-10-28, phase 1) - THE OWNER'S SESSIONS, SUMMARIZED SO A SHADOW CAN SHOW THEM.

His words: a shadow must render the owner's exact data one to one - and his ruling on the size: summarized frames, "a
few small key frames per session", because a full reel is 8-12 GB and never leaves its PC (his 10-07 ruling stands).
v3894 (Elad, 2026-11-10): those key frames and the vault's evidence must be the film itself - 1920x1080, the size
every PC now records - not the theatre's 160 px scrub thumb magnified onto the stage. A full REEL still never
leaves its PC; only the same few key frames ride, at film size.

This builds the digest a shadow can carry: the owner's newest sessions (replay.split_sessions, newest first), each
dated by what it captured (replay.session_moments, REG-2736), its read count by the Shelf's own rule (control_app's
_is_a_live_read, passed in - one predicate, never a copy), the names its reads saw, and up to 3 key frames as
1920x1080 (or smaller, never enlarged) JPEGs in tv/frames/hist/cache1920/<frameId>.jpg - frames whose read named
something first, else first / middle / last. A frame with no derivative is made by `sips` on a Mac, else by Pillow
(REG-3033: a Windows owner had sips alone to ask and sent no picture); a PC with no resizer carries the session
without pictures and says why. A source smaller than 1920x1080 is never upscaled (sips on current macOS would).

Caps (the record is KV-bound): a frame over 800 KB is left out and named, and the total stays under 12 MB by
dropping the OLDEST sessions' pictures first, each drop counted. Phase 2 signs and publishes it as the owner's own
roster record; phase 3 draws it in the shadow's Shelf and TV·D. Never raises; writes only the theatre's cache.
"""
import base64
import re
import json
import os
import shutil
import subprocess
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

MAX_SESSIONS = 16
MAX_FRAMES = 3
# v3894 - film-size key frames, not 160 px / 20 KB thumbs (those magnified into an unreadable theatre)
MAX_THUMB = 800 * 1024
MAX_TOTAL = 12 * 1024 * 1024
#: v3859 (b) item 18 - the vault's witnessed frames ride the upload too, at most this many (their bytes count in MAX_TOTAL)
WITNESS_MAX = 8
_FID_SHAPE = re.compile(r"^\d{1,6}_\d{13}$")
MAX_NAMES = 8
# A gap between two captured moments longer than this is time away, not time played. It sits under
# replay.SESSION_GAP_MS (10 min, which starts another unstamped session) so a pause that stays inside
# one reel still counts as away. Fewer than two moments is not a span: play and AFK stay unknown.
AFK_GAP_MS = 90 * 1000


THUMB_PX = 160
# v3894 - what a shadow's theatre and evidence play: the film frame, never a 160 px scrub thumb
SHADOW_FRAME_PX = 1920
SHADOW_FRAME_H = 1080
SHADOW_JPEG_Q = 82
SHADOW_CACHE = "cache1920"


def _image_size(src):
    """-> (w, h) | None. Pillow if it imports; never raises."""
    try:
        from PIL import Image
        with Image.open(src) as im:
            return im.size
    except Exception:
        return None


def _sips_thumb(src, dst, max_px=THUMB_PX, quality=68, timeout=8):
    """The theatre's own derivative, by the theatre's own sips call (160 px by default). -> bool

    v3894 - never pass --resampleHeightWidthMax when the source already fits: on current macOS
    sips *upsamples* a small image to that max (the same trap _sips_hd_jpeg documented at v1450).
    """
    if sys.platform != "darwin":
        return False
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        cmd = ["sips", "-s", "format", "jpeg", "-s", "formatOptions", str(int(quality))]
        size = _image_size(src)
        if size and max(size) > int(max_px):
            cmd += ["--resampleHeightWidthMax", str(int(max_px))]
        elif size is None and int(max_px) <= THUMB_PX:
            # unknown size, small shelf thumb: keep the old resample (may shrink)
            cmd += ["--resampleHeightWidthMax", str(int(max_px))]
        cmd += [src, "--out", dst]
        r = subprocess.run(cmd, capture_output=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return False
    # REG-3039 - _serve_hist judged sips by its exit code before REG-3038 shared this call; a failed sips is no derivative
    return r.returncode == 0 and os.path.isfile(dst)


def _pil_thumb(src, dst, max_px=THUMB_PX, quality=68):
    """REG-3033 - the same JPEG (160 px by default) on a PC with no sips. -> bool

    The default resizer was sips alone, and sips is macOS: on GrokBot's v3836 glass pass every one of the ALT's 16
    sessions said "no thumbnail resizer" and the site's ALT frames record held 0 pictures. Every Windows boot installs
    Pillow (start_tvd_win.ps1, #227), so the resizer was there and never asked. Written beside and moved into place: a
    half-written file in cache160 would be taken as the thumbnail from then on. REG-3038 - and named per thread: the
    theatre's GET makes these while the Shelf scrub asks for many at once, and two writers of one shared part file could
    move a mix of both into place."""
    try:
        from PIL import Image
    except Exception:
        return False
    tmp = "%s.%d.%d.part" % (dst, os.getpid(), threading.get_ident())
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with Image.open(src) as im:
            im.draft("RGB", (max_px, max_px))   # a JPEG decodes at 1/2..1/8 scale: no full-size decode per frame
            small = im.convert("RGB")
            small.thumbnail((max_px, max_px))  # never enlarges a small frame
            small.save(tmp, "JPEG", quality=int(quality))
        with open(tmp, "rb") as fh:
            if fh.read(3) != b"\xff\xd8\xff":
                raise ValueError("not a JPEG")
        os.replace(tmp, dst)
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        return False
    return os.path.isfile(dst)


def resizers():
    """-> the names of the thumbnail resizers this PC has: sips on a Mac, Pillow wherever it imports."""
    out = ["sips"] if sys.platform == "darwin" and shutil.which("sips") else []
    try:
        import PIL.Image  # noqa: F401
        out.append("Pillow")
    except Exception:
        pass
    return out


def _make_thumb(src, dst):
    """sips first on a Mac (the theatre's own resizer), else Pillow. -> bool
    v3894 - the shadow theatre's frame is the film size (1920), never a 160 px thumbnail."""
    return _sips_thumb(src, dst, SHADOW_FRAME_PX, SHADOW_JPEG_Q) or _pil_thumb(src, dst, SHADOW_FRAME_PX, SHADOW_JPEG_Q)


def make_derivative(src, dst, max_px, quality, timeout=10):
    """REG-3038 - one of the theatre's derivatives (cache160 for the Shelf scrub, cache1280 for play) on any PC: sips on
    a Mac, the call the theatre always made, else Pillow. The theatre made none off a Mac (control_app's IS_WIN guards),
    so a Windows console served the Shelf scrub and the theatre every frame at full size - "a decoded 2560px JPEG is
    ~14MB RGBA in the WebView" (_serve_hist's own note) - on the ALT, whose free memory fell 1.5 GB -> 560 MB in an
    hour. -> bool"""
    return _sips_thumb(src, dst, max_px, quality, timeout) or _pil_thumb(src, dst, max_px, quality)


def thumb_bytes(hist_dir, frame_id, make=_make_thumb):
    """The film-size JPEG of one read frame (1920 px, never enlarged). -> (bytes | None, why | None)"""
    base = "%s.jpg" % frame_id
    cached = os.path.join(hist_dir, SHADOW_CACHE, base)
    if not os.path.isfile(cached):
        src = os.path.join(hist_dir, base)
        if not os.path.isfile(src):
            return None, "its picture is not on disk"
        if not (make and make(src, cached)):
            if make is _make_thumb and resizers():
                # REG-3033 - a resizer that failed on this frame is not a PC without one
                return None, "its thumbnail could not be made (%s failed on it)" % " and ".join(resizers())
            return None, "this PC has no thumbnail resizer, so no picture rides (a full frame never does)"
    try:
        with open(cached, "rb") as fh:
            data = fh.read()
    except OSError as e:
        return None, "its thumbnail would not read (%s)" % type(e).__name__
    if len(data) > MAX_THUMB:
        return None, "its thumbnail is %d KB, over the %d KB a summarized frame may be" % (len(data) // 1024, MAX_THUMB // 1024)
    return data, None


def _names(r):
    v = r.get("names")
    if isinstance(v, str):
        v = [v] if v and not v.startswith("[") else []
    return [str(x) for x in (v or []) if isinstance(x, str) and x.strip()]


def _play_afk(moments):
    """-> (playMs, afkMs). Both are None when fewer than two captured moments exist (never a made-up 0).

    Play is the sum of the gaps at or under AFK_GAP_MS. Away is the sum of the longer gaps. The wall
    from the first moment to the last is not playtime: that span is where a reel of a few minutes of
    reading was dated as many hours."""
    ms = [t for t in (moments or []) if isinstance(t, int) and not isinstance(t, bool) and t > 0]
    if len(ms) < 2:
        return None, None
    ms.sort()
    play = afk = 0
    for a, b in zip(ms, ms[1:]):
        gap = b - a
        if gap > AFK_GAP_MS:
            afk += gap
        else:
            play += gap
    return play, afk


#: v3855 - the five act towns by the name a read gives its area (D2 facts, lower case)
TOWN_AREAS = ("rogue encampment", "lut gholein", "kurast docks", "the pandemonium fortress", "pandemonium fortress", "harrogath")
FIELD_SCENES = ("gameplay", "loot")


def _where(r):
    """-> 'town', 'field' or None. A read's scene 'town' or a town area is town; a gameplay/loot scene or any other
    named area is out of town. A read that names neither is not placed (never guessed)."""
    sc = str(r.get("scene") or "").strip().lower()
    area = str(r.get("area") or "").strip().lower()
    if sc == "town" or (area and area in TOWN_AREAS):
        return "town"
    if area or sc in FIELD_SCENES:
        return "field"
    return None


#: v3855 - unchanged town reads for longer than this are AFK (idle in town), not town time (Elad 2026-11-02)
TOWN_IDLE_MS = 3 * 60 * 1000


def _town_sig(r):
    """What a town read saw: area, scene, its names, and its frame hash when the read carries one."""
    return (str(r.get("area") or "").strip().lower(), str(r.get("scene") or "").strip().lower(),
            tuple(sorted(_names(r))), r.get("frameHash") or r.get("hash") or None)


def game_timeline(rows):
    """v3855 (Elad 2026-11-02: "it's AFK until it's not") - the whole game's reads, every session together, cut into
    segments [(a, b, kind)] with kind 'afk', 'town', 'field' or None (the opening read was not placed).

    AFK is one continuous state, never reset at a session boundary: a gap over AFK_GAP_MS is AFK, and a run of
    consecutive town reads that saw the same thing (_town_sig) for longer than TOWN_IDLE_MS is AFK from its first read
    to the first read that differs (area/scene, names, frame hash, or out of town). A brief town visit stays town."""
    import replay as _rp
    pts = []
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        try:
            t = _rp._session_moment(r)
        except Exception:
            t = 0
        if isinstance(t, int) and not isinstance(t, bool) and t > 0:
            pts.append((t, _where(r), _town_sig(r)))
    pts.sort(key=lambda x: x[0])
    kinds = [("afk" if b[0] - a[0] > AFK_GAP_MS else a[1]) for a, b in zip(pts, pts[1:])]
    i = 0
    while i < len(pts):
        if pts[i][1] != "town":
            i += 1
            continue
        k = i
        while k + 1 < len(pts) and pts[k + 1][1] == "town" and pts[k + 1][2] == pts[i][2]:
            k += 1
        if pts[k][0] - pts[i][0] > TOWN_IDLE_MS:
            for g in range(i, k):
                kinds[g] = "afk"
        i = k + 1
    return [(a[0], b[0], kd) for (a, b, kd) in zip(pts, pts[1:], kinds)]


def afk_stretches(segs):
    """Consecutive afk segments merged into stretches [(a, b)]."""
    out = []
    for a, b, kd in segs or []:
        if kd != "afk":
            continue
        if out and out[-1][1] == a:
            out[-1] = (out[-1][0], b)
        else:
            out.append((a, b))
    return out


def session_split(segs, t0, t1):
    """-> {townMs, fieldMs, awayMs, afkFrom, afkInto} for the session [t0, t1], each segment clipped to it by overlap.
    All None when the session has no span or none of its time was placed (UNKNOWN, never 0). afkFrom / afkInto: an AFK
    stretch that was already running at t0 / still running at t1 (it crosses into the neighbour session)."""
    none = {"townMs": None, "fieldMs": None, "awayMs": None, "afkFrom": False, "afkInto": False}
    if not isinstance(t0, int) or not isinstance(t1, int) or t1 <= t0:
        return none
    got = {"town": 0, "field": 0, "afk": 0}
    for a, b, kd in segs or []:
        ov = min(b, t1) - max(a, t0)
        if ov > 0 and kd in got:
            got[kd] += ov
    if not any(got.values()):
        return none
    st = afk_stretches(segs)
    return {"townMs": got["town"], "fieldMs": got["field"], "awayMs": got["afk"],
            "afkFrom": any(a < t0 < b or (a < t0 and b == t0) for a, b in st),
            "afkInto": any(a < t1 < b or (b > t1 and a == t1) for a, b in st)}


# v3855 - who played and in which games: the console-wide shared extractor (read_identity)
from read_identity import (game_name_of_row, character_signals, attribute_character, game_runs,  # noqa: E402,F401
                           say_games, CLASSES, identity_ledger, who_at, summary as identity_summary, scenario_of,
                           class_crosscheck, soft_understanding)


def character_from_select(sid, t0=None, t1=None):
    """v3893 (REG-3551) - the highlighted name from this reel's character-select login.

    Recording starts before character select, so who_at(t0) only sees earlier characters (signals
    with ts <= t0). char_select.selected_of already reads the highlighted row; logins and
    session_characters already bind that name to the reel's sessionId. Reuse those — do not invent
    a new pixel reader. None when this session has no login (the caller may then ask who_at);
    a dict (name may be None) when a login exists, so an unconfirmed close is not replaced by
    the previous character.
    """
    if not sid:
        return None
    try:
        import char_select as CS
        d = CS.load()
        if d is None:
            return None
        # logins() already picks the latest confirmed highlighted row per visit
        # (selected_of + the closing read). session_characters binds the same
        # name to this reel; we ask logins so a login that happened after t0
        # (the recorder started at the logo) still tags the session.
        pick = None
        for L in CS.logins(d) or []:
            if str(L.get("sessionId") or "") == str(sid):
                pick = L
        if pick is None:
            return None
        name = pick.get("character")
        if name:
            return {"name": name, "cls": None, "level": None, "sources": ["select-screen"],
                    "conflict": None,
                    "seen": [{"source": "select-screen", "name": name, "cls": None, "level": None}],
                    "seenN": 1}
        return {"name": None, "cls": None, "level": None, "sources": ["select-screen"],
                "conflict": None, "seen": [], "seenN": 0, "why": pick.get("why")}
    except Exception:
        return None


def _key_frames(reads):
    """Up to MAX_FRAMES frame ids: those whose read named something first (newest name first), else first/middle/last."""
    ids = [r.get("frameId") for r in reads if isinstance(r.get("frameId"), str) and r.get("frameId")]
    named = [r.get("frameId") for r in reads if _names(r) and isinstance(r.get("frameId"), str)]
    out = []
    for f in list(reversed(named)) + ([ids[0], ids[len(ids) // 2], ids[-1]] if ids else []):
        if f and f not in out:
            out.append(f)
        if len(out) >= MAX_FRAMES:
            break
    return out


def characters_rollup(rows):
    """v3855 (Elad pt1198u) - the Characters tab / builder consumer: per character, over EVERY session of this console's
    journal: sessions, the last level seen, total played (town + field) and AFK, and leveling (Baal) vs farming runs.
    A session nobody names counts under no character (UNKNOWN), never the nearest name.
    -> {name: {sessions, level, cls, playMs, afkMs, leveling, farming, lastT}}"""
    import replay as _rp
    try:
        groups = _rp.split_sessions(list(rows or []))
    except Exception:
        return {}
    ident = identity_ledger(rows)
    timeline = game_timeline(rows)
    out = {}
    for g in groups:
        moments = _rp.session_moments(g) or []
        if not moments:
            continue
        t0, t1 = min(moments), max(moments)
        sig = character_signals(g)
        _sid = next((r.get("sessionId") for r in g if r.get("sessionId")), None)
        _pick = None if sig else character_from_select(_sid, t0, t1)
        ch = attribute_character(sig) if sig else (_pick if _pick is not None else who_at(ident, t0))
        name = (ch or {}).get("name")
        if not name:
            continue
        sp = session_split(timeline, t0, t1)
        games = []
        for r in g:
            n = game_name_of_row(r)
            if n and n not in games:
                games.append(n)
        sc = scenario_of(games) or ""
        o = out.setdefault(name, {"sessions": 0, "level": None, "cls": None, "playMs": 0, "afkMs": 0,
                                  "leveling": 0, "farming": 0, "lastT": 0})
        o["sessions"] += 1
        o["playMs"] += (sp.get("townMs") or 0) + (sp.get("fieldMs") or 0)
        o["afkMs"] += sp.get("awayMs") or 0
        o["leveling"] += 1 if sc.startswith("Leveling") else 0
        o["farming"] += 1 if sc.startswith("Farming") else 0
        if t1 >= o["lastT"]:
            o["lastT"] = t1
            if ch.get("level"):
                o["level"] = ch["level"]
            if ch.get("cls"):
                o["cls"] = ch["cls"]
    return out


def session_facts(g, reads, timeline, chron_count=None):
    """v3859 (#230) - THE ONE ANSWER FOR A SESSION, for the owner's Sessions tab and every shadow alike: playtime and
    AFK, town / out of town / AFK split, and the route ledger (tv/session_route.py) - farmed, stashed, trashed and the
    chronicle finds from the green 'Eligible for Chronicle' line. g: the session's rows; reads: its live reads.

    v3890 (#184, REG-3513) - chron_count(t0, t1) -> (count or None, why): the pixel lane's answer for this window
    (chronicle_line.session_count). The two console call sites hand it, because both build sessions from THIS
    console's own journal and the lane walks THIS console's own reels; a caller that hands nothing keeps the route's
    answer. The route's own (OCR line colours) wins when it has one."""
    import replay as _rp
    import session_route as _SR
    moments = _rp.session_moments(g) or []
    play_ms, afk_ms = _play_afk(moments)
    rt = _SR.route(reads)
    chron = len(rt["chronicle"]) if rt["chronicle"] is not None else None
    chron_why = None
    if chron is None and chron_count is not None:
        try:
            chron, chron_why = chron_count(min(moments) if moments else None, max(moments) if moments else None)
        except Exception as e:
            chron, chron_why = None, "the chronicle lane raised %s" % type(e).__name__
    f = {"playMs": play_ms, "afkMs": afk_ms,
         "chroniclesFound": chron,
         "itemsFarmed": rt["itemsFarmed"],
         "farmed": rt["farmed"],
         "chronicleNames": rt["chronicle"][:MAX_NAMES] if rt["chronicle"] is not None else None,
         "stashed": rt["stashed"],
         "trashed": rt["trashed"][:MAX_NAMES] if rt["trashed"] is not None else None}
    if chron is None and chron_why:
        f["chroniclesWhy"] = str(chron_why)[:160]
    f.update(session_split(timeline, min(moments) if moments else None, max(moments) if moments else None))
    return f


def witness_frames(ids, hist_dir, make=_make_thumb):
    """v3859 (b) - the vault's witnessed frame ids as film-size JPEGs. -> (list of {id, jpg}, {id: why left out})"""
    got, whys = [], {}
    for fid in list(ids or []):
        fid = str(fid or "")
        if not _FID_SHAPE.match(fid):
            continue                                   # not a read frame's id: nothing to send, nothing to explain
        if len(got) >= WITNESS_MAX:
            whys[fid] = "only %d witnessed frames ride one upload" % WITNESS_MAX
            continue
        data, why = thumb_bytes(hist_dir, fid, make)
        if data is None:
            whys[fid] = str(why)[:160]
            continue
        got.append({"id": fid, "jpg": base64.b64encode(data).decode("ascii")})
    return got, whys


def digest(rows, hist_dir, is_read, now_ms, make=_make_thumb, witness_ids=None, chron_count=None, is_game=None,
           game_of=None):
    """rows: the journal's rows. is_read: the Shelf's read rule. -> {v, sessions: [...], bytes, dropped, left}

    ⚠ REG-2772 - NO BUILD TIME IN IT. The first cut carried `at`, so its hash moved on every build and the publish lane's
    change-only rule could never hold (its law caught a second post of an unchanged digest). The site record keeps its
    own time; `now_ms` stays in the signature for the callers that date their checks."""
    import replay as _rp
    import farmed_names as _FN
    out = {"v": 1, "sessions": [], "bytes": 0, "dropped": 0, "left": []}
    try:
        groups = _rp.split_sessions(list(rows or []))
    except Exception as e:
        out["why"] = "the journal would not split into sessions (%s)" % type(e).__name__
        return out
    runs = game_runs(rows)
    ident = identity_ledger(rows)   # v3855 - built here, on this console, from its own reads
    timeline = game_timeline(rows)   # v3855 - AFK over the whole game, then each session takes its share
    # v3860 (#230, ALT 2026-11-03) - a journal slice with no read is a ghost row (a restart or a heartbeat between reads
    # of the same reel). The ALT's 16 published slots held 7 such rows at 0 frames, pushing real hours off the Shelf.
    # v3859 - a GHOST is no read AND no captured frame. A skip-only session filmed real frames (v3847: it must say
    # why it has no picture), so it keeps its slot; only a heartbeat/restart slice with nothing filmed is dropped.
    _kept = [g for g in groups if any(is_read(r) or r.get("captureTs") or r.get("frameId") for r in g)]
    out["ghosts"] = len(groups) - len(_kept)
    # v3890 (#188) - is_game(g) -> True | False | None (control_app._session_is_the_game): a run whose film never showed
    # D2R itself is not a session on any shadow either; None keeps it
    if is_game is not None:
        _game = [g for g in _kept if is_game(g) is not False]
        out["notGame"] = len(_kept) - len(_game)
        _kept = _game
    groups = _kept
    for g in groups[:MAX_SESSIONS]:
        reads = [r for r in g if is_read(r)]
        moments = _rp.session_moments(g) or []
        # v3850 - a read word is snapped to a known D2 name or dropped; UI words, NPCs and consumables never show
        names = _FN.clean([n for r in reads for n in _names(r)])
        sid = next((r.get("sessionId") for r in g if r.get("sessionId")), None)
        s = {"sessionId": sid, "t0": min(moments) if moments else None, "t1": max(moments) if moments else None,
             "reads": len(reads), "names": names[:MAX_NAMES], "namesMore": max(0, len(names) - MAX_NAMES),
             "frames": [], "why": None}
        s.update(session_facts(g, reads, timeline, chron_count=chron_count))
        games = []
        for r in g:
            n = game_name_of_row(r)
            if n and n not in games:
                games.append(n)
        s["games"] = games
        s["gamesSay"] = say_games(games) if games else None
        # v3898 (#188, REG-3713) - the part of ONE game this session is (control_app._shelf_games, the equipped ledger's
        # chain), so a shadow draws the same "part k of m" the owner's Shelf draws; nothing when the game has one part
        try:
            _gp = game_of(str(sid)) if (game_of is not None and sid) else None
        except Exception:
            _gp = None
        if isinstance(_gp, dict) and _gp.get("parts", 0) > 1:
            s["game"] = {"part": _gp.get("part"), "parts": _gp.get("parts"), "character": _gp.get("character")}
        _then = _gp.get("then") if isinstance(_gp, dict) else None
        if isinstance(_then, dict) and (_then.get("parts") or 0) > 1:   # REG-3742 - the game this part STARTS, mid-reel
            s.setdefault("game", {})["then"] = {"part": _then.get("part"), "parts": _then.get("parts"),
                                                "character": _then.get("character")}
        s["scenario"] = scenario_of(games)
        s["gameRunSessions"] = max([len(runs[k]["sessions"]) for k in runs
                                    if any(x in runs[k]["names"] for x in games)] or [0]) or None
        _sig = character_signals(g)
        s["classCheck"] = class_crosscheck(_sig)
        s["understanding"] = soft_understanding(g)
        _from_select = None if _sig else character_from_select(sid, s.get("t0"), s.get("t1"))
        if not _sig and _from_select is None and s["t0"]:
            # a session whose own reads named nobody takes who was playing when it began (the game-wide ledger)
            s["character"] = who_at(ident, s["t0"])
            if s["character"]:
                s["character"]["sources"] = ["earlier read"] + [x for x in s["character"]["sources"] if x != "earlier read"]
        elif _sig:
            s["character"] = attribute_character(_sig)
        else:
            s["character"] = _from_select
        whys = []
        for fid in _key_frames(reads):
            data, why = thumb_bytes(hist_dir, fid, make)
            if data is None:
                whys.append("%s: %s" % (fid, why))
                if "KB, over" in (why or ""):
                    out["left"].append(fid)
                continue
            s["frames"].append({"id": fid, "jpg": base64.b64encode(data).decode("ascii")})
        if not s["frames"] and whys:
            s["why"] = whys[0]
        elif not s["frames"]:
            # v3847 - a session with no read has no key frame; "why UNKNOWN" under it read as a broken shadow Shelf
            s["why"] = ("no frame of this session was read, so it has no key frame" if not reads
                        else "its reads carry no frame id, so it has no key frame")
        out["sessions"].append(s)
    out["identity"] = identity_summary(ident)   # the only identity other consoles see; never a password
    out["characters"] = characters_rollup(rows)   # v3855 pt1198u - the Characters tab's per-character answer
    total = sum(len(f["jpg"]) for s in out["sessions"] for f in s["frames"])
    if witness_ids:
        out["witness"], out["witnessWhy"] = witness_frames(witness_ids, hist_dir, make)
    wbytes = sum(len(f["jpg"]) for f in out.get("witness") or [])
    budget = MAX_TOTAL - wbytes                                # the vault's witnesses are kept; session frames make room
    for s in reversed(out["sessions"]):                       # the oldest sessions give their pictures up first
        if total <= budget:
            break
        for f in list(s["frames"]):
            if total <= budget:
                break
            s["frames"].remove(f)
            total -= len(f["jpg"])
            out["dropped"] += 1
        if not s["frames"] and not s["why"]:
            s["why"] = "its pictures were left out to keep the record under %d KB (newer sessions keep theirs)" % (MAX_TOTAL // 1024)
    out["bytes"] = total + wbytes
    return out


# ── #218 phase 2b (REG-2772): publishing the digest beside the roster row and the profile ──────────────────────
#: change-only and at most hourly unless the console just started - v3862 Workers Paid (it was 3 h on the free plan);
#: the worker's own floor is 50 min (roster.js frames door), so the console's pace is the pace
MIN_GAP_MS = 60 * 60 * 1000
#: an unchanged digest is not rebuilt every minute: the lane looks again after this long
LOOK_AGAIN_MS = 30 * 60 * 1000


def digest_hash(d):
    """The hash the owner signs: console_snapshot.digest, the Python twin of roster.js hashOf(stable(..))."""
    import console_snapshot as _cs
    return _cs.digest(d)


def _int(v):
    return v if isinstance(v, int) and not isinstance(v, bool) else None


#: v3860 (#230) - a reel that SEALED after the last post may publish once this long after it, not 3 h later
SEAL_GAP_MS = 10 * 60 * 1000


def may_build(state, now_ms, boot, sealed_at=None):
    """Before a single thumbnail is made: could an upload go now? A boot always may. -> bool

    v3860 (#230, ALT 2026-11-03) - the Shelf read the ALT 2-3 h behind its play because only the 3 h gap opened the
    lane. A reel sealed AFTER the last post (sealed_at) now opens it, rate-limited to SEAL_GAP_MS since that post."""
    state = state if isinstance(state, dict) else {}
    if boot:
        return True
    _sealed, _posted = _int(sealed_at), _int(state.get("postedAt"))
    if _sealed is not None and (_posted is None or _sealed > _posted):
        _refused = _int(state.get("refuseAt"))
        if (_posted is None or now_ms - _posted >= SEAL_GAP_MS) and (_refused is None or now_ms - _refused >= SEAL_GAP_MS):
            return True
    for k, gap in (("refuseAt", MIN_GAP_MS), ("postedAt", MIN_GAP_MS), ("checkedAt", LOOK_AGAIN_MS)):
        t = _int(state.get(k))
        if t is not None and now_ms - t < gap:
            return False
    return True


def due(state, owner, d, now_ms, boot):
    """-> (body | None, why). The body is what roster.js's frames door checks; signedAt is now."""
    import console_snapshot as _cs
    state = state if isinstance(state, dict) else {}
    if not _cs.profile_key(owner):
        return None, "the owner is not one of the owner labels"
    if not isinstance(d, dict) or not d.get("sessions"):
        return None, (d or {}).get("why") if isinstance(d, dict) and d.get("why") else "no session to summarize"
    h = digest_hash(d)
    if state.get("hash") == h:
        return None, "unchanged"
    return {"kind": "frames", "owner": owner, "boot": bool(boot), "signedAt": int(now_ms), "hash": h, "digest": d}, "post"


def apply_reply(state, h, reply, now_ms):
    """What the worker's answer teaches the lane. -> the new state (never raises)"""
    s = dict(state) if isinstance(state, dict) else {}
    if isinstance(reply, dict) and reply.get("ok"):
        stored = "frames" in (reply.get("stored") or [])
        skipped = reply.get("skipped") or []
        if stored or "unchanged" in skipped:
            s["hash"] = h                                   # the site holds these bytes
        s["postedAt"] = int(now_ms)
        s.pop("refuseAt", None)
        s["why"] = "stored" if stored else ("skipped: " + ", ".join(str(x) for x in skipped))[:200]
    else:
        s["refuseAt"] = int(now_ms)
        s["why"] = ("refused: " + str((reply or {}).get("why") or "no answer"))[:200] if isinstance(reply, dict) \
            else "refused: no answer"
    return s


# ── #218 phase 3a (REG-2773): what the viewer draws, and this PC's last copy of an owner's digest ───────────────
def record_ok(rec, owner):
    """A frames record the site served as this owner's, in the digest's shape. -> bool"""
    return (isinstance(rec, dict) and rec.get("owner") == owner and rec.get("published") is True
            and not rec.get("corrupt") and isinstance(rec.get("digest"), dict)
            and isinstance(rec["digest"].get("sessions"), list) and isinstance(rec.get("t"), int))


def cache_path(directory, owner):
    import console_snapshot as _cs
    if owner not in _cs.OWNERS:
        return None
    return os.path.join(directory, "%s.json" % owner.replace(" ", "_").replace("\u00b7", "-"))


def write_cache(directory, rec):
    p = cache_path(directory, rec.get("owner"))
    if not p:
        return False
    os.makedirs(directory, exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({"owner": rec["owner"], "t": rec["t"], "hash": rec.get("hash"), "digest": rec["digest"],
                   "published": True}, fh)
    os.replace(tmp, p)
    return True


def read_cache(directory, owner):
    """-> this PC's last copy of the owner's record, or None (absent or unreadable - never an empty digest)"""
    p = cache_path(directory, owner)
    if not p or not os.path.isfile(p):
        return None
    try:
        with open(p, encoding="utf-8") as fh:
            rec = json.load(fh)
    except (OSError, ValueError):
        return None
    return rec if record_ok(rec, owner) else None


def viewed_sessions(sessions):
    """v3850 - an owner whose console predates the farmed summary published raw read words. The viewer snaps them
    by the same rule (farmed_names) before drawing: junk, UI words and consumables never reach the card. Each name
    counts once (the old record kept no per-read order). A session that already carries `farmed` is shown as given."""
    import farmed_names as _FN
    if not isinstance(sessions, list):
        return sessions
    out = []
    for s in sessions:
        if isinstance(s, dict) and "farmed" not in s and isinstance(s.get("names"), list):
            s = dict(s)
            raw = [n for n in s["names"] if isinstance(n, str)]
            s["names"] = _FN.clean(raw)
            s["namesMore"] = None
            s["farmed"] = _FN.group([raw])
        out.append(s)
    return out


def view(owner, rec, now_ms, source="worker", fetch_why=None):
    """-> {ok, owner, published, sessions, t, ageS, source, why}. A copy says it is one and how old; no record says why."""
    if not isinstance(rec, dict):
        return {"ok": False, "owner": owner, "published": None, "sessions": None, "t": None, "ageS": None,
                "source": None, "why": fetch_why or "no record of %s's sessions could be read" % owner}
    t = rec.get("t")
    import console_snapshot as _cs
    return {"ok": True, "owner": owner, "published": True, "sessions": viewed_sessions(rec["digest"]["sessions"]), "t": t,
            "ageS": max(0, (int(now_ms) - t) // 1000) if isinstance(t, int) else None, "source": source,
            # REG-2810 - the record's age in words, by the profile view's one rule; the shadow's list prints it as given
            "ago": _cs._ago_words(int(now_ms) - t) if isinstance(t, int) else None,
            "why": fetch_why if source == "cache" else None,
            # v3859 (b) - the owner's witnessed frames, as the record carries them (the worker checked their shape)
            "witness": viewed_witness(rec["digest"].get("witness")),
            "witnessWhy": rec["digest"].get("witnessWhy") if isinstance(rec["digest"].get("witnessWhy"), dict) else None}


def viewed_witness(w):
    """-> {frame id: base64 JPEG} for each entry in a witness list that is a read frame's small JPEG, else nothing"""
    out = {}
    for f in w if isinstance(w, list) else []:
        if (isinstance(f, dict) and _FID_SHAPE.match(str(f.get("id") or "")) and isinstance(f.get("jpg"), str)
                and f["jpg"].startswith("/9j/") and len(f["jpg"]) <= 27400
                and re.match(r"^[A-Za-z0-9+/]+={0,2}$", f["jpg"])):
            out[f["id"]] = f["jpg"]
    return out
