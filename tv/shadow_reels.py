# -*- coding: utf-8 -*-
"""#208 (his 11-13 calls) - THIS PC'S SESSIONS, UP TO THE PRIVATE BUCKET: THE NEWEST 3 WHOLE, THE REST AS SUMMARY REELS.

His words: "when a player is offline to see his last 16 reels somehow", then "maybe just the last 3 sessions recorded for
each pc so those are online and always reachable even when a user is offline ... a type of summary almost like it is now
just not 3 frames for each session when the user is offline". The site's reel door (functions/api/roster.js, kind "reel")
keeps each PC's newest 16 sessions and holds the bucket under its 9 GB cap; this module decides what this PC sends.

  - a session is DONE when it is not the reel rolling now and its newest frame is QUIET_S old (a reel still being written
    is never sent);
  - the newest FULL_SESSIONS done sessions go up with every frame, each re-encoded to FRAME_PX wide; sessions 4..16 go up
    as a SUMMARY: the first and last frame, the frame play starts on, every frame where the screen changes door (logo,
    title, character select, lobby, in game - chronicle_line's marks), and one frame per SUMMARY_EVERY_MS of film,
    thinned evenly to SUMMARY_MAX;
  - a session already in the bucket with the same mode and the same frame count is not sent again; one that slid from
    the newest 3 to the rest is re-begun as a summary (the door drops the frames not on the new list);
  - play starts on the first D2 logo frame (his 11-11 ruling: "one trigger on every route ... starts at the first logo");
    a reel with no logo (GrokBot 11-13: the ALT reels open mid-play) starts on its first frame.

Read-only on his footage: frames are read and re-encoded into this module's own scratch folder, removed after each
session. UNKNOWN stays UNKNOWN: an unreadable reel store or a bucket that will not answer plans nothing.
"""
import base64
import json
import os
import re
import shutil
import tempfile
import time

FULL_SESSIONS = 3
KEEP_SESSIONS = 16
SUMMARY_EVERY_MS = 20 * 1000
SUMMARY_MAX = 80
FULL_MAX = 2000
FRAME_PX = 1280
FRAME_Q = 75
BATCH_BYTES = 8 * 1024 * 1024
QUIET_S = 600
SCRATCH_PREFIX = "tvd-reelup-"
FRAME_SHAPE = re.compile(r"^f_(\d{10,16})\.jpg$")
SESSION_SHAPE = re.compile(r"^s_(\d{10,16})_\d{1,6}$")
DOOR_MARKS = ("logo", "title", "char-select", "lobby", "hud")


def frames_of(names):
    """-> [(ts_ms, name)] of the f_<ms>.jpg frames among names, oldest first (thumbnails and side files are not frames)"""
    out = []
    for n in names or []:
        m = FRAME_SHAPE.match(str(n))
        if m:
            out.append((int(m.group(1)), str(n)))
    return sorted(out)


def session_ms(session):
    m = SESSION_SHAPE.match(str(session or ""))
    return int(m.group(1)) if m else None


def done_sessions(hist, now_s, rolling=None, quiet_s=QUIET_S, listdir=os.listdir, getmtime=os.path.getmtime):
    """-> [(session, [frame names])] newest first, or None when the reel store will not list (UNKNOWN)."""
    try:
        names = listdir(hist)
    except OSError:
        return None
    out = []
    for n in names:
        if not n.startswith("reel_s_"):
            continue
        ses = n[len("reel_"):]
        if session_ms(ses) is None or (rolling and ses == rolling):
            continue
        d = os.path.join(hist, n)
        try:
            fr = frames_of(listdir(d))
        except OSError:
            continue
        if not fr:
            continue
        try:
            newest = max(getmtime(os.path.join(d, name)) for _t, name in fr[-3:])
        except OSError:
            continue                    # a frame without a readable time: UNKNOWN, never sent on a guess
        if now_s - newest >= quiet_s:
            out.append((ses, [name for _t, name in fr]))
    out.sort(key=lambda x: session_ms(x[0]), reverse=True)
    return out


def writing_now(hist, now_s, quiet_s=QUIET_S, listdir=os.listdir, getmtime=os.path.getmtime):
    """Is a reel being written right now (he is playing)? -> True | False | None (the store will not list: UNKNOWN).
    The lane sends nothing while one is: re-encoding and uploading beside a cloud-gaming stream is his lag, not ours."""
    try:
        names = listdir(hist)
    except OSError:
        return None
    for n in names:
        if not n.startswith("reel_s_"):
            continue
        d = os.path.join(hist, n)
        try:
            fr = frames_of(listdir(d))
            if fr and now_s - getmtime(os.path.join(d, fr[-1][1])) < quiet_s:
                return True
        except OSError:
            continue
    return False


def start_frame(frames, marks):
    """The frame play starts on: the first at or after the first logo mark, else the reel's first frame. -> name | None"""
    fr = frames_of(frames)
    if not fr:
        return None
    logos = sorted(t for t, kind in (marks or []) if kind == "logo" and isinstance(t, int))
    if logos:
        for t, name in fr:
            if t >= logos[0]:
                return name
    return fr[0][1]


def logo_frame(frames, marks):
    """-> the first frame at or after the first logo mark, or None (this reel shows no logo)"""
    logos = sorted(t for t, kind in (marks or []) if kind == "logo" and isinstance(t, int))
    if not logos:
        return None
    for t, name in frames_of(frames):
        if t >= logos[0]:
            return name
    return None


def summary_frames(frames, marks=None, every_ms=SUMMARY_EVERY_MS, cap=SUMMARY_MAX):
    """-> the summary's frame names, oldest first, at most cap: the must-haves (first, last, start, each door change)
    then one per every_ms of film, thinned evenly so the must-haves always survive."""
    fr = frames_of(frames)
    if not fr:
        return []
    by_ts = dict(fr)
    ts_list = [t for t, _n in fr]

    def at_or_after(t):
        for x in ts_list:
            if x >= t:
                return x
        return None
    must = {ts_list[0], ts_list[-1]}
    st = start_frame(frames, marks)
    if st:
        must.add(int(FRAME_SHAPE.match(st).group(1)))
    prev = None
    for t, kind in sorted((m for m in (marks or []) if isinstance(m, (list, tuple)) and len(m) == 2
                           and isinstance(m[0], int) and m[1] in DOOR_MARKS)):
        if kind != prev:
            x = at_or_after(t)
            if x is not None:
                must.add(x)
        prev = kind
    paced, nxt = [], ts_list[0]
    for t in ts_list:
        if t >= nxt:
            paced.append(t)
            nxt = t + every_ms
    rest = [t for t in paced if t not in must]
    must = sorted(must)
    if len(must) >= cap:
        keep = set(_even(must, cap))
    else:
        keep = set(must) | set(_even(rest, cap - len(must)))
    return [by_ts[t] for t in sorted(keep)]


def _even(xs, k):
    """k items of xs spread evenly, ends kept. -> list"""
    if k <= 0:
        return []
    if len(xs) <= k:
        return list(xs)
    if k == 1:
        return [xs[0]]
    step = (len(xs) - 1) / float(k - 1)
    return [xs[int(round(i * step))] for i in range(k)]


def plan(local, server, marks_of=None, full=FULL_SESSIONS, keep=KEEP_SESSIONS):
    """-> [{session, mode, frames, logo, start}] to send, newest first.

    local: done_sessions() (newest first). server: {session: {"mode", "frames": count}} - the bucket's sealed sessions
    for this PC, or None when the bucket did not answer (UNKNOWN: nothing is planned). marks_of(session) -> marks."""
    if local is None or server is None:
        return None
    out = []
    for i, (ses, names) in enumerate(local[:keep]):
        marks = (marks_of or (lambda s: None))(ses)
        mode = "full" if i < full else "summary"
        want = [n for _t, n in frames_of(names)][-FULL_MAX:] if mode == "full" else summary_frames(names, marks)
        if not want:
            continue
        have = server.get(ses) or {}
        if have.get("mode") == mode and have.get("frames") == len(want):
            continue
        st = start_frame(want, marks)
        out.append({"session": ses, "mode": mode, "frames": want, "logo": logo_frame(want, marks), "start": st})
    return out


def batches(paths, limit=BATCH_BYTES, size=os.path.getsize):
    """[(name, path)] -> [[(name, path)]] each under limit bytes of frames (one frame alone may fill a batch)"""
    out, cur, n = [], [], 0
    for name, p in paths:
        b = size(p)
        if cur and n + b > limit:
            out.append(cur)
            cur, n = [], 0
        cur.append((name, p))
        n += b
    if cur:
        out.append(cur)
    return out


# ── the I/O: re-encode into our own scratch, post through the signed door, one session at a time ─────────────────────
def scratch():
    return tempfile.mkdtemp(prefix=SCRATCH_PREFIX)


def derive(src_dir, names, dst_dir, make=None):
    """-> [(name, derived path)] for every frame that re-encoded; a frame that would not is left out (and named)"""
    if make is None:
        import shadow_sessions as _ss
        make = lambda s, d: _ss.make_derivative(s, d, FRAME_PX, FRAME_Q)
    got, failed = [], []
    for n in names:
        dst = os.path.join(dst_dir, n)
        if make(os.path.join(src_dir, n), dst) and os.path.isfile(dst):
            got.append((n, dst))
        else:
            failed.append(n)
    return got, failed


def upload(item, hist, post, owner, now_ms=None, make=None):
    """Send one planned session: begin, its frames in batches, seal. -> {ok, why, sent, bytes}

    post(body) -> the door's reply (signed by the caller). Never raises; the scratch folder is removed either way."""
    now = (lambda: int(time.time() * 1000)) if now_ms is None else now_ms
    d = scratch()
    try:
        src = os.path.join(hist, "reel_" + item["session"])
        got, failed = derive(src, item["frames"], d, make)
        if failed:
            # a summary re-plans without them next tick; a full session is never sealed with a hole in it
            return {"ok": False, "why": "%d frame(s) would not re-encode (%s)" % (len(failed), failed[0]), "sent": 0}
        sizes = {n: os.path.getsize(p) for n, p in got}
        base = {"kind": "reel", "owner": owner, "session": item["session"]}
        r = post(dict(base, op="begin", signedAt=now(), mode=item["mode"], frames=[n for n, _p in got],
                      logo=item.get("logo"), start=item.get("start"), estBytes=max(1, sum(sizes.values()))))
        if not (isinstance(r, dict) and r.get("ok")):
            return {"ok": False, "why": "begin refused: %s" % ((r or {}).get("why") if isinstance(r, dict) else r),
                    "sent": 0}
        want = set(r.get("want") or [])
        todo = [(n, p) for n, p in got if n in want]
        sent = 0
        for b in batches(todo):
            frames = []
            for n, p in b:
                with open(p, "rb") as fh:
                    frames.append({"name": n, "b64": base64.b64encode(fh.read()).decode("ascii")})
            r = post(dict(base, op="frames", signedAt=now(), frames=frames))
            if not (isinstance(r, dict) and r.get("ok")):
                return {"ok": False, "why": "frames refused: %s" % ((r or {}).get("why") if isinstance(r, dict) else r),
                        "sent": sent}
            sent += len(b)
        r = post(dict(base, op="seal", signedAt=now()))
        if not (isinstance(r, dict) and r.get("ok")):
            return {"ok": False, "why": "seal refused: %s" % ((r or {}).get("why") if isinstance(r, dict) else r),
                    "sent": sent}
        return {"ok": True, "why": "sealed", "sent": sent, "bytes": (r.get("manifest") or {}).get("bytes")}
    except Exception as e:
        return {"ok": False, "why": "the upload raised %s" % type(e).__name__, "sent": 0}
    finally:
        shutil.rmtree(d, ignore_errors=True)


def server_index(reply):
    """GET ?reels=<owner> -> {session: {"mode", "frames"}} | None (the bucket did not answer: UNKNOWN, never empty)"""
    if not (isinstance(reply, dict) and reply.get("ok") is True and isinstance(reply.get("sessions"), list)):
        return None
    out = {}
    for s in reply["sessions"]:
        if isinstance(s, dict) and SESSION_SHAPE.match(str(s.get("session") or "")):
            out[s["session"]] = {"mode": s.get("mode"), "frames": s.get("frames")}
    return out
