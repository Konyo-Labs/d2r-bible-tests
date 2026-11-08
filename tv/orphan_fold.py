#!/usr/bin/env python3
"""AN UNSEALED SESSION'S FOOTAGE IS NOT LOST — IT IS JUST NOT IN A REEL YET.

Reel directories exist because of a REEL FOLD that runs at SEAL time (tv_diablo.py, v883): it moves
loose `f_<ms>.jpg` frames whose timestamps fall in the session window into `frames/hist/reel_<sid>/`
with os.replace. v883's own note says why — "loose f_*.jpg footage was a shared pool the reaper shed
FIRST, so every sealed run went hollow within hours."

Nobody handled the session that DIES BEFORE IT SEALS. Its frames stay loose forever, and loose
frames are invisible to every lane and every deleter BY CONSTRUCTION: the vault and chronicle sweeps
iterate `reel_*`, frame_authority.plan_frames globs `hist/reel_*`, and space_warden has `tv/frames`
on its NEVER list. Not protected — UNSEEN, which reads as protected and is worse.

MEASURED on his tree 2026-08-24: 2,385 loose recording frames, 3.15 GB, spanning 01:15:00 to
02:06:22 — a fifty-one minute recording no lane could see.

⚠ THE ONE WAY THIS COULD DO REAL HARM, and it is why the overlap rule below exists.
`reel_index.ensure_reel_index` writes an index via `chronicle_retro.reconstruct_index`, which sets
`sessionId` from the DIRECTORY NAME with `reel_` stripped. PROVEN, not assumed:

    reel_orphan_1787523300658_1  ->  sessionId 'orphan_1787523300658_1'
    reel_s_1787523300658_1       ->  sessionId 's_1787523300658_1'

So folding leftovers of an ALREADY-SEALED session into a new directory mints a NEW SESSION ID for
pixels that came from one recording — which forges exactly the independence the keep gate exists to
demand (KEEP_MIN_WITNESSES counts distinct looks, and the throw bar counts distinct SESSIONS). A
later sweep would then ground rows, or suggest binning an item, on evidence that is one recording
wearing two names. Hence: **a cluster whose window overlaps ANY existing reel is REPORTED AND NEVER
MOVED.**

And the name is `reel_s_<t0>_<n>`, never `reel_orphan_…`, because v2065's recording parser is
`^s_(\\d{10,16})(?:_|$)` — an orphan-named reel would read as UNKNOWN time in the ledger and undo a
fix that shipped the same week.

This module DECIDES and MOVES. It never deletes a frame, never touches a file already inside a
`reel_*` directory, and refuses to act without an explicit --yes.

REG-2463 (#168) - AND NOW IT IS A LANE. His ruling 2026-10-21: "FOLD + LANE". Before, nothing folded
on its own on any PC: the healer remedy runs only with TV_AUTO_HEAL=1 (unset everywhere), and even
armed, one fold would disarm it for good (the doctor's row stays MISSING on frames an overlap refuses -
Dean, after a fold of 65,457 frames by hand: 2,468 left loose in 18 refused clusters). run_once() is
one pass of control_app's tvd-orphan-fold lane; it asks what is in flight first, folds only what
apply_plan calls eligible, and names what it leaves loose.
"""

import argparse
import glob
import json
import os
import threading
import time
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:                                   # the report prints a box-file glyph; a CLI that crashes
    from console_safe import enable    # while REPORTING makes a clean tree exit non-zero
    enable()
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))

# A NEW CLUSTER STARTS AFTER THIS MUCH SILENCE. It is vault_retro.REOPEN_GAP_MS — his number for
# "this is a new look" — rather than one invented here, and the data says the choice is not delicate:
# across his 2,384 loose-frame gaps the LARGEST is 7.4 s (p50 1.1 s, p99 4.7 s) against a
# FOOTAGE_INTERVAL_S of 1.0. Anything from ~30 s upward yields the same single cluster.
GAP_MS = 180_000

FRAME_RE = re.compile(r"^f_(\d{10,16})\.jpg$")

#: REG-2463 (#168) - the lane's name, its first look after boot and its period (control_app's loop reads these)
LANE = "tvd-orphan-fold"
FIRST_S = 300.0
EVERY_S = 1800.0

#: REG-2463 - ONE FOLD AT A TIME. The lane and the opt-in healer remedy (console_healer's
#: _remedy_fold_orphan_footage, TV_AUTO_HEAL=1) both move loose frames. apply_plan holds this for the
#: whole of a fold, and run_once holds it from its plan to the end of its fold, so the two never move the
#: same frames at once (two os.replace of one frame, two writers of one reel's index).
_FOLD_LOCK = threading.RLock()


def _one_fold_at_a_time(fn):
    """REG-2463 - run a fold under _FOLD_LOCK (the remedy's apply_plan and the lane's both come here)."""
    import functools

    @functools.wraps(fn)
    def _run(*a, **k):
        with _FOLD_LOCK:
            return fn(*a, **k)
    return _run


def _reel_windows(hist):
    """Every existing reel's real frame window, read from the filenames rather than its index —
    an index can be missing or stale, and the pixels cannot."""
    out = []
    for d in sorted(glob.glob(os.path.join(hist, "reel_*"))):
        if not os.path.isdir(d):
            continue
        ts = []
        try:
            for n in os.listdir(d):
                m = FRAME_RE.match(n)
                if m:
                    ts.append(int(m.group(1)))
        except OSError:
            continue
        if not ts:
            # v2128 (#11) — A REEL THAT HAS LOST ITS JPEGS STILL OWNS ITS WINDOW. The reaper sheds
            # frames and leaves index.json behind, so a hollow reel contributed NO window at all
            # and every cluster inside its span read `eligible` — the overlap refusal, the one
            # thing standing between this module and a forged session id, was silently absent for
            # exactly the reels most likely to have leftovers. The index carries the timestamps the
            # pixels no longer can. [[unknown-stays-unknown]]
            try:
                with open(os.path.join(d, "index.json"), "r") as fh:
                    ts = [int(r.get("ts")) for r in (json.load(fh).get("frames") or [])
                          if isinstance(r, dict) and r.get("ts")]
            except Exception:
                ts = []
        if ts:
            out.append((os.path.basename(d), min(ts), max(ts)))
    return out


def _join_target(lo, hi, hit):
    """v3883 (#128, his 11-08 "do whatever is recommended regardless") - THE ONE REEL A REFUSED CLUSTER BELONGS TO.
    -> (reel name, gap ms) | (None, why). `hit` is [(reel, t_lo, t_hi)] - the reels within the pad of [lo, hi].

    MEASURED on the work ALT 11-08 (orphan_fold.plan, read-only): 8 clusters refused for an overlap, every one OUTSIDE the
    reels it touched - seven 1-frame slivers 2-4 s after a reel's last frame (the hourly hand-off) and one 39-frame cluster
    43 s before a reel's first - so they lay loose for days, read by nothing and deleted by nothing. Folding one into a NEW
    reel mints a second session id for one recording (this module's docstring), and that stays refused. Moving it INTO the
    reel it sits against mints nothing: the frames take that reel's own session id and leave with it when the drain
    prunes the reel. Only when the answer is one reel: the cluster lies wholly outside every reel it touches (a cluster
    that straddles a reel's own frames is not a sliver), and one reel's edge is strictly nearest (a tie refuses)."""
    if not hit:
        return None, None
    near = []
    for name, wlo, whi in hit:
        if hi < wlo:
            near.append((wlo - hi, name))
        elif lo > whi:
            near.append((lo - whi, name))
        else:
            return None, "it lies across %s's own frames - not a sliver beside it" % name
    near.sort()
    if len(near) > 1 and near[0][0] == near[1][0]:
        return None, "it sits %.0fs from %s and from %s alike - a tie is not one reel" % (
            near[0][0] / 1000.0, near[0][1], near[1][1])
    return near[0][1], near[0][0]


def plan(hist_dir=None, gap_ms=GAP_MS):
    """What WOULD be folded, and what is refused and why. Writes nothing, moves nothing."""
    hist = hist_dir or os.path.join(HERE, "frames", "hist")
    try:
        names = os.listdir(hist)
    except OSError as e:
        return {"ok": False, "why": "cannot read %s: %s" % (hist, e), "clusters": []}

    # ONE classifier, not two. frame_authority.loose_frames already splits recording frames from
    # probe artifacts and is guarded; a second copy of that rule is how the two drift. [[copy-drift]]
    arte = None
    try:
        import frame_authority as _fa
        lf = _fa.loose_frames(hist)
        if lf.get("ok"):
            arte = len(lf.get("artifact") or [])
    except Exception:
        arte = None

    ts = sorted(int(m.group(1)) for m in (FRAME_RE.match(n) for n in names) if m)
    windows = _reel_windows(hist)
    clusters = []
    if ts:
        start = prev = ts[0]
        run = [ts[0]]
        for t in ts[1:]:
            if t - prev > gap_ms:
                clusters.append((start, prev, run))
                start, run = t, []
            run.append(t)
            prev = t
        clusters.append((start, prev, run))

    # ── v2080 — A RECORDING IN PROGRESS *IS* A PILE OF LOOSE FRAMES ──────────────────────────
    # That is not a race, it is the steady state: while he films, every new frame lands directly in
    # hist/ as `f_<ms>.jpg` and only becomes a reel at SEAL. Which is exactly the population this
    # module folds. A fold running unattended would therefore move the frames of the session he is
    # filming RIGHT NOW into a reel and seal it as a finished recording — and v2080 put this behind
    # an automatic healer on a ten-minute timer, so it would have done it on its own.
    #
    # The cluster boundary cannot tell a finished recording from one still being written: both end
    # at "the newest frame I can see". So the rule is TIME, not shape — a window whose last frame is
    # newer than the same gap that defines a cluster boundary has not been shown to be over.
    # A frame that is still arriving is UNKNOWN, and unknown means leave it alone.
    # [[unknown-stays-unknown]] [[feedback-fixtures-never-touch-live-data]]
    now_ms = int(time.time() * 1000)
    out = []
    for lo, hi, run in clusters:
        # v2082 — AND A CALLER MAY NOT DISABLE THIS BY PASSING ZERO. `--gap-s 0` reaches gap_ms=0,
        # where `(now_ms - hi) < 0` is never true and the refusal vanishes entirely. Measured on six
        # frames of a recording in progress: at the default it refuses; at gap_ms=0 it minted SIX
        # separate session ids for that one recording and moved every frame — exactly the forgery
        # this module's docstring exists to prevent. The window a caller may tune is how far apart
        # two clusters must be; it is NOT how recent a recording may be before we call it finished.
        if (now_ms - hi) < max(gap_ms, GAP_MS):
            out.append({"t0": lo, "t1": hi, "frames": len(run), "bytes": 0,
                        "reel": "reel_s_%d_1" % lo, "overlaps": [], "eligible": False,
                        "why": "REFUSED \u2014 the newest frame here is %.0fs old, inside the %.0fs "
                               "gap that defines a cluster. This may be a recording STILL IN "
                               "PROGRESS, and a recording in progress is indistinguishable from "
                               "loose frames. Folding it would seal a session he is still filming."
                               % ((now_ms - hi) / 1000.0, gap_ms / 1000.0)})
            continue
        # v2128 (#11) — ADJACENT IS NOT SEPARATE. v883's seal fold already moved every IN-window
        # frame into reel_<sid>/, so the leftovers of an ALREADY-SEALED session lie OUTSIDE that
        # reel's remaining min/max BY CONSTRUCTION — the case this module's own docstring names as
        # the one that can do real harm, and the one an exact-interval test can never refuse. The
        # same silence that separates two clusters has to separate a cluster from a reel.
        pad = max(gap_ms, GAP_MS)
        _hitw = [w for w in windows if not (w[2] < lo - pad or w[1] > hi + pad)]
        hit = [w[0] for w in _hitw]
        join, jgap = _join_target(lo, hi, _hitw)
        size = 0
        for t in run:
            try:
                size += os.path.getsize(os.path.join(hist, "f_%d.jpg" % t))
            except OSError:
                pass
        out.append({
            "t0": lo, "t1": hi, "frames": len(run), "bytes": size,
            "reel": "reel_s_%d_1" % lo,
            "overlaps": hit,
            "eligible": not hit,
            "join": join,
            "why": (("JOINS %s - it sits %.0fs %s that reel's frames: one recording, so it takes that reel's own "
                     "session id (no new reel, no second session id) and leaves with the reel when the drain prunes it."
                     % (join, jgap / 1000.0, "after" if any(w[0] == join and hi > w[2] for w in _hitw) else "before"))
                    if join else
                    ("REFUSED — this window is already covered by %s. Folding it would mint a second "
                     "session id for one recording, which forges the independence the keep and throw "
                     "bars exist to demand%s." % (", ".join(hit), (" - and it cannot join one: %s" % jgap) if jgap else ""))
                    ) if hit else
                   ("no reel covers this window — it is an unsealed recording and folding it makes "
                    "it readable by the lanes for the first time"),
        })
    return {"ok": True, "hist": hist, "clusters": out, "gapMs": gap_ms,
            "artifacts": arte,
            "say": (("%d cluster(s) of loose footage; %d foldable, %d join the reel they sit against, %d refused for "
                     "overlapping an existing reel." % (len(out), sum(1 for c in out if c["eligible"]),
                                                        sum(1 for c in out if c.get("join")),
                                                        sum(1 for c in out if not c["eligible"] and not c.get("join"))))
                    if out else "no loose recording frames — every frame on disk belongs to a reel")
                   + ("" if arte is None else
                      " %d probe artifact(s) left alone; they are not a recording." % arte)}


@_one_fold_at_a_time
def apply_plan(p, yes=False):
    """Fold the ELIGIBLE clusters. Refuses without an explicit yes — this moves his footage."""
    if not yes:
        return {"ok": False, "why": "refusing to move footage without --yes; run without --apply to "
                                    "read the plan"}
    hist = p["hist"]
    moved, made, failed = 0, [], []
    for c in p.get("clusters") or []:
        if not c.get("eligible"):
            continue                       # never fold a window a reel already covers
        dest = os.path.join(hist, c["reel"])
        try:
            os.makedirs(dest, exist_ok=True)
        except OSError as e:
            failed.append({"reel": c["reel"], "why": str(e)[:120]})
            continue
        n = 0
        for name in sorted(os.listdir(hist)):
            m = FRAME_RE.match(name)
            if not m:
                continue                   # artifacts and anything unparsable stay exactly where they are
            t = int(m.group(1))
            if not (c["t0"] <= t <= c["t1"]):
                continue
            try:
                os.replace(os.path.join(hist, name), os.path.join(dest, name))
                n += 1
            except OSError as e:
                failed.append({"frame": name, "why": str(e)[:120]})
        moved += n
        made.append({"reel": c["reel"], "frames": n})
        # the index IS the reel (v1608) — without it the lanes still cannot read what we just folded
        try:
            import reel_index
            reel_index.ensure_reel_index(dest)
        except Exception as e:
            failed.append({"reel": c["reel"], "why": "index not written: %s" % str(e)[:100]})
    # v3883 (#128) - a sliver JOINS the one reel it sits against (plan's `join`): moved into that reel's directory, never
    # over a frame already there, its index left as sealed (reel_index never rewrites a good index - so nothing re-reads
    # the reel for it, the river re-read loop's lesson), and it leaves with the reel when the drain prunes it
    joined = []
    for c in p.get("clusters") or []:
        tgt = c.get("join")
        if c.get("eligible") or not tgt or not str(tgt).startswith("reel_") or os.sep in str(tgt) or "/" in str(tgt):
            continue
        dest = os.path.join(hist, tgt)
        if not os.path.isdir(dest):
            failed.append({"reel": tgt, "why": "the reel to join is gone"})
            continue
        n = 0
        for name in sorted(os.listdir(hist)):
            m = FRAME_RE.match(name)
            if not m or not (c["t0"] <= int(m.group(1)) <= c["t1"]):
                continue
            if os.path.exists(os.path.join(dest, name)):
                failed.append({"frame": name, "why": "the reel already holds a frame of that name - left loose"})
                continue
            try:
                os.replace(os.path.join(hist, name), os.path.join(dest, name))
                n += 1
            except OSError as e:
                failed.append({"frame": name, "why": str(e)[:120]})
        moved += n
        joined.append({"reel": tgt, "frames": n})
    return {"ok": not failed, "moved": moved, "reels": made, "joined": joined, "failed": failed}


def run_once(hist_dir=None, in_flight=None, now_ms=None):
    """REG-2463 (#168) - ONE PASS OF THE ORPHAN-FOLD LANE. Never raises.
    -> {on, worked, lastTs, owed, folded, reels, refused, why} (the heart's lane vocabulary)

      1. ASK WHAT IS IN FLIGHT FIRST - `in_flight()` -> (ok, why); the console hands it nothing_in_flight.
         A refusal, a raise, or nobody to ask moves nothing: an answer nobody could get is not permission.
      2. ONE FOLD AT A TIME - while the healer remedy is folding, this pass moves nothing and says so.
      3. plan(), then apply_plan(p, yes=True), which folds the ELIGIBLE clusters only. A cluster a reel already
         covers (folding it would mint a second session id for one recording) and one whose newest frame is still
         inside the gap (it may still be filming) stay loose - counted, and named in `refused` with plan's reason.
    `worked` and `folded` are the frames moved this pass (worked is None when the pass did not run); `owed` is the
    clusters this lane will fold later - still inside the gap, or not fully moved - and None when it is UNKNOWN. A
    cluster refused for an overlap is never owed: no pass of this lane will fold it, a person decides."""
    now_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
    out = {"on": True, "worked": None, "lastTs": now_ms, "owed": None, "folded": 0, "reels": [], "refused": [],
           "why": ""}
    try:
        if in_flight is None:
            out["why"] = "not folding: nothing could be asked what is in flight, and that is not permission"
            return out
        try:
            ok, why = in_flight()
        except Exception as e:
            ok, why = False, "the in-flight check raised %s" % type(e).__name__
        if not ok:
            out["why"] = "not folding while %s" % (why or "something is in flight")
            return out
        if not _FOLD_LOCK.acquire(blocking=False):
            out["why"] = "not folding: another fold is moving frames right now"
            return out
        try:
            p = plan(hist_dir)
            if not p.get("ok"):
                out["why"] = "the footage could not be read: %s" % str(p.get("why"))[:160]
                return out
            res = apply_plan(p, yes=True)
        finally:
            _FOLD_LOCK.release()
        clusters = p.get("clusters") or []
        made = {r.get("reel"): int(r.get("frames") or 0) for r in (res.get("reels") or []) if isinstance(r, dict)}
        moved = int(res.get("moved") or 0)
        out["worked"] = out["folded"] = moved
        out["reels"] = sorted(r for r, n in made.items() if n)
        out["joined"] = [j for j in (res.get("joined") or []) if isinstance(j, dict) and j.get("frames")]
        out["folded"] = moved - sum(int(j.get("frames") or 0) for j in out["joined"])   # v3883 - into NEW reels; worked is all moved
        out["refused"] = [{"t0": c.get("t0"), "t1": c.get("t1"), "frames": c.get("frames"),
                           "kind": "overlap" if c.get("overlaps") else "growing", "why": c.get("why")}
                          for c in clusters if not c.get("eligible") and not c.get("join")]
        short = [c for c in clusters if c.get("eligible") and made.get(c.get("reel"), 0) < int(c.get("frames") or 0)]
        growing = [r for r in out["refused"] if r["kind"] == "growing"]
        overlap = [r for r in out["refused"] if r["kind"] == "overlap"]
        out["owed"] = len(growing) + len(short)
        _jn = sum(int(j.get("frames") or 0) for j in out["joined"])
        parts = [("folded %d loose frame(s) into %d reel(s)" % (moved - _jn, len(out["reels"]))) if moved - _jn
                 else "folded nothing"]
        if _jn:
            parts.append("%d sliver frame(s) joined the reel each sits against (%s) - that reel's own session id"
                         % (_jn, ", ".join(sorted(set(j["reel"] for j in out["joined"])))[:160]))
        if overlap:
            parts.append("%d cluster(s) (%d frame(s)) left loose: a reel already covers each window, and folding "
                         "would mint a second session id for one recording - a person decides"
                         % (len(overlap), sum(int(r.get("frames") or 0) for r in overlap)))
        if growing:
            parts.append("%d cluster(s) left loose for now: the newest frame is inside the gap, so it may still be "
                         "filming" % len(growing))
        if res.get("failed"):
            parts.append("%d move(s) failed: %s" % (len(res["failed"]), str(res["failed"][0])[:120]))
        if not clusters:
            parts = ["nothing loose to fold - every recording frame is in a reel"]
        out["why"] = "; ".join(parts)
    except Exception as e:
        out.update(worked=None, owed=None, why="the fold pass raised %s: %s" % (type(e).__name__, str(e)[:120]))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Make an unsealed session's footage visible again.")
    ap.add_argument("--hist", default=None)
    ap.add_argument("--gap-s", type=float, default=GAP_MS / 1000.0)
    ap.add_argument("--apply", action="store_true", help="actually fold (needs --yes)")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args(argv)
    p = plan(a.hist, int(a.gap_s * 1000))
    if not p["ok"]:
        print("refusing: %s" % p["why"])
        return 1
    import datetime
    fmt = lambda t: datetime.datetime.fromtimestamp(t / 1000).strftime("%Y-%m-%d %H:%M:%S")
    print("\U0001f9f5  ORPHAN FOLD — footage belonging to no reel")
    print("   %s" % p["say"])
    for c in p["clusters"]:
        print("   %s  %s -> %s  %4d frame(s)  %6.2f GB  -> %s"
              % ("FOLD  " if c["eligible"] else ("JOIN  " if c.get("join") else "REFUSE"), fmt(c["t0"]), fmt(c["t1"]),
                 c["frames"], c["bytes"] / 1e9, c.get("join") or c["reel"]))
        print("          %s" % c["why"])
    if a.apply:
        r = apply_plan(p, a.yes)
        print("\n%s" % (("folded %d frame(s) into %d reel(s)" % (r["moved"], len(r["reels"])))
                        if r["ok"] else (r.get("why") or "some moves failed")))
        for f in r.get("failed") or []:
            print("   FAILED %s" % f)
        return 0 if r["ok"] else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
