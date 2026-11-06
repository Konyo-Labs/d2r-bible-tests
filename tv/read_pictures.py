#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A READ THAT NAMED AN ITEM KEEPS ITS PICTURE — and when it did not, this says who took it.

His words, 2026-09-28: "where is the ledger proof of these two items? i cant find it.. how can i see the evidence
and picture pixels from the session it was extracted from", and "reverse engineer them to the session they are
from and check the frames".

MEASURED that day (read-only, a copy of his tree): the reads that named String of Ears and the seven Chronicle-page
items were taken 02:32-02:42, and NONE of their frames were on disk. The session's reel held frames only from
02:44. Three deleters, none of which asked whether a frame was evidence:
  · the recorder, under MIN_FREE_GB, refused to archive film at all (_FOOTAGE_WHY "disk-full") while the live
    reader went on reading;
  · an in-loop reaper deleted up to 600 loose f_*.jpg older than 15 min every 120 s under the floor, with NO
    evidence check (its sibling eviction already protected _journal_frame_ids());
  · the disk-floor REEL reaper spared only sessions cited in vault_accum.json — not frame_authority's witness
    index, not chron_evidence's reels — and took reel_s_1786385768689_67392, whose frames chron_evidence cites.

This module is the ONE place that answers "is the picture of this read on disk, and if not, WHY": the doctor row
'a read left no picture', the console's /api/picture_status (the board's evidence panel asks it before it ever
draws an image), and the recorder's own refusal record all read and write through here. [[the-unjoined-end]]
Every answer that could not be established is UNKNOWN — never "fine", never 0. [[unknown-stays-unknown]]
"""
import io
import json
import os
import re
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

#: below this, the recorder writes NO picture at all — the journal and the ledgers need the last gigabyte more
HARD_FLOOR_GB = 1.0
#: under MIN_FREE_GB a read's picture is still saved, SMALL: this many pixels on the long side, this quality
FLOOR_MAX_PX = 1024
FLOOR_JPEG_Q = 70
#: ... and at most this many megabytes of read pictures per rolling hour while under the floor
FLOOR_BUDGET_MB_PER_HOUR = 150
REFUSALS = "read_pictures.jsonl"
REAPS = "reel_reaps.jsonl"
DAY_MS = 24 * 3600 * 1000
#: the doctor's vocabulary, so a row can hand these straight through
OK, MISSING, UNKNOWN = "ok", "missing", "unknown"


def root_of(hist_dir):
    """The directory the recorder's own records live in, derived from the hist it deletes from — the same
    derivation tv_diablo._reap_record uses (…/frames/hist -> …/), so a fixture shelf reads its own records."""
    h = os.path.abspath(hist_dir)
    return os.path.dirname(os.path.dirname(h))


def record_refusal(hist_dir, frame_id, why, free_gb=None, session=None):
    """One line for every read picture the recorder did NOT write. -> None (never raises into the scan loop)."""
    try:
        row = {"ts": int(time.time() * 1000), "frameId": str(frame_id or ""), "why": str(why),
               "freeGb": (round(float(free_gb), 2) if free_gb is not None else None), "session": session}
        with open(os.path.join(root_of(hist_dir), REFUSALS), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        pass


def budget_spent_mb(hist_dir, now_ms=None):
    """MB of read pictures written under the floor in the last hour, from the recorder's own record.
    -> float | None (None = the record could not be read)."""
    rows = load_jsonl(os.path.join(root_of(hist_dir), REFUSALS))
    if rows is None:
        return None
    now_ms = now_ms or int(time.time() * 1000)
    return sum(float(r.get("mb") or 0) for r in rows
               if r.get("why") == "saved-small" and now_ms - int(r.get("ts") or 0) <= 3600 * 1000)


def load_jsonl(path):
    """-> list (absent file = [] — a record nobody wrote holds nothing) | None (it exists and will not read)."""
    if not os.path.exists(path):
        return []
    try:
        out = []
        with io.open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    v = json.loads(line)
                except ValueError:
                    continue          # one torn line is not an unreadable record
                if isinstance(v, dict):
                    out.append(v)
        return out
    except Exception:
        return None


def load_tombstones(hist_dir):
    """reel_tombstones.json rows for this shelf. -> list | None"""
    try:
        import reel_retention as _rr
        p = _rr._tombstone_path(hist_dir)
    except Exception:
        p = os.path.join(os.path.dirname(os.path.abspath(hist_dir)), "reel_tombstones.json")
    if not os.path.exists(p):
        return []
    try:
        with io.open(p, encoding="utf-8") as fh:
            blob = json.load(fh)
        rows = blob.get("reels") if isinstance(blob, dict) else None
        return [r for r in (rows or []) if isinstance(r, dict)]
    except Exception:
        return None


def _stem(ref):
    s = str(ref or "").replace("\\", "/").rsplit("/", 1)[-1]
    return os.path.splitext(s)[0]


def _when(ms):
    try:
        return time.strftime("%d %b %Y %H:%M", time.localtime(int(ms) / 1000.0))
    except Exception:
        return "an unknown date"


def _ms_of(stem):
    """The capture clock a frame's own name carries (f_<ms>, <n>_<ms>). -> int | None (a name without one)"""
    m = re.search(r"(?<!\d)(\d{13})(?!\d)", str(stem or ""))
    return int(m.group(1)) if m else None


def _ts(v):
    """A record's epoch-ms stamp, or None when it carries none (never 0, which would sort as 'first')."""
    return int(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0 else None


def _kept_stems(row):
    """The frames a trim KEPT, by stem. -> set

    REG-3207 - reel_retention writes `kept` as bare file names (sorted listdir names); this read only
    {"frame": ...} dicts, a shape the writer never wrote, so every trim read as keeping nothing. Both are read."""
    out = set()
    for k in (row.get("kept") or []):
        if isinstance(k, dict):
            k = k.get("frame")
        if isinstance(k, str) and k:
            out.add(_stem(k))
    return out


def index(reaps, tombstones):
    """The deleters' records, indexed once: reap rows by every frame stem they NAME, whole-reel reap rows by reel,
    tombstones by reel and by session. -> dict. Rows keep their record order (both stores are append-only)."""
    names, whole, tombs = {}, {}, {}
    for r in (reaps or []):
        if not isinstance(r, dict):
            continue
        for n in (r.get("names") or []):
            names.setdefault(_stem(n), []).append(r)
        # a whole-reel reap carries no `kept`; a partial release names exactly what it took, so it is matched by name
        if r.get("removed") and "kept" not in r and r.get("reel") not in (None, "", "loose"):
            whole.setdefault(str(r.get("reel")), []).append(r)
    for t in (tombstones or []):
        if not isinstance(t, dict):
            continue
        for key in set(str(x) for x in (t.get("reel"), t.get("session")) if x):
            tombs.setdefault(key, []).append(t)
    return {"names": names, "whole": whole, "tombs": tombs}


def judge(frame_id, idx, refusals, read_ts=None, session=None, unread=()):
    """Why a frame is not on disk. -> {code, words, ts, when, by}

    code: 'never-written' (the recorder refused it - disk floor / hard floor / budget), 'reaped' (the recorder's floor
    reaper took it - loose film or a whole reel), 'released' (retention released or trimmed its reel), 'unknown'.

    REG-3207 - THE EARLIEST DELETER THAT COULD HAVE TAKEN IT IS THE ONE THAT DID. The retention lane trims one reel
    again and again (measured on his record: one reel, 92 tombstones - the first took 2,847 frames down to 49, each
    later one ~50 of what remained), and the reader took the LAST, dating a frame's prune 19 days late. Now a
    tombstone counts only when it was written after the frame was filmed and its kept list does not hold the frame,
    and of every deleter that qualifies, the earliest wins. `unread` names records that would not read."""
    stem = _stem(frame_id)
    ref = str(frame_id or "").replace("\\", "/").lstrip("/")
    reel = ref.split("/", 1)[0] if ("/" in ref and ref.startswith("reel_")) else None
    if not session and reel:
        session = reel[len("reel_"):]
    for r in (refusals or []):
        if r.get("why") == "saved-small":
            continue
        same = (stem and _stem(r.get("frameId")) == stem)
        # a refused picture leaves the read with NO frame id, so it is matched by its own clock (the recorder stamps
        # the would-be id with the read's capture time) — within 5 s, and in the same session when both say one
        if not same and not stem and read_ts:
            try:
                same = abs(int(r.get("ts") or 0) - int(read_ts)) <= 5000 and (not session or not r.get("session")
                                                                                or r.get("session") == session)
            except (TypeError, ValueError):
                same = False
        if same:
            return {"code": "never-written", "ts": _ts(r.get("ts")), "when": (_when(r.get("ts")) if _ts(r.get("ts")) else None),
                    "by": "the recorder's disk floor",
                    "words": "never written — the recorder was under its disk floor (%s, %s GB free) "
                             "when this read was taken" % (r.get("why"), r.get("freeGb"))}
    filmed = _ms_of(stem)
    # v3868 (the Grok CLI on REG-3207, #231 6675925066) - a path that NAMES its reel is that reel's frame: unioning the
    # caller's session let another reel's earlier trim win the earliest-deleter rule.
    keys = ([reel] if reel else
            [k for k in (("reel_" + str(session)) if session else None, str(session) if session else None) if k])
    events, seen = [], set()
    if stem:
        for r in idx["names"].get(stem, ()):
            seen.add(id(r))
            events.append((_ts(r.get("ts")), "reaped", "the recorder's disk-floor reaper",
                           "taken by the recorder's disk-floor reaper on %s (%s)"
                           % (_when(r.get("ts")), r.get("by") or "recorder"), "named"))
    for k in keys:
        for r in idx["whole"].get(k, ()):
            if id(r) in seen:
                continue
            seen.add(id(r))
            t = _ts(r.get("ts"))
            if filmed and t and t < filmed:
                continue                      # it ran before this frame was filmed: it cannot have taken it
            events.append((t, "reaped", "the recorder's disk-floor reaper",
                           "released with its reel on %s by the recorder's disk-floor reaper" % _when(r.get("ts"))))
        for tb in idx["tombs"].get(k, ()):
            if id(tb) in seen:
                continue
            seen.add(id(tb))
            if stem and stem in _kept_stems(tb):
                continue                      # this trim KEPT it
            t = _ts(tb.get("deletedTs"))
            if filmed and t and t < filmed:
                continue
            events.append((t, "released", "the retention lane",
                           "released with its reel on %s (%s)" % (_when(tb.get("deletedTs")), tb.get("why") or "retention")))
    if events:
        # earliest stamp first; a row with no stamp sorts after every stamped one; ties keep record order
        pool = range(len(events))
        if filmed is None:
            # v3868 - with no capture time, a reap that NAMES the frame is the only evidence that dates it: the frame still
            # existed when it was taken, so no earlier trim could have taken it
            named = [j for j in pool if len(events[j]) > 4 and events[j][4] == "named"]
            pool = named or pool
        i = min(pool, key=lambda j: (events[j][0] is None, events[j][0] or 0, j))
        t, code, by, words = events[i][:4]
        out = {"code": code, "ts": t, "when": (_when(t) if t else None), "by": by, "words": words}
        unnamed = [e for e in events if len(e) < 5 or e[4] != "named"]
        if filmed is None and (len(events[i]) < 5 or events[i][4] != "named") and len(unnamed) > 1:
            # v3868 (the Grok CLI on REG-3207) - A FRAME WITH NO CAPTURE TIME CANNOT BE DATED AGAINST SEVERAL TRIMS.
            # The filmed-after guard never ran, so the reel's FIRST trim won even for a frame filmed after it. One trim
            # alone is the only deleter that could have taken it, so it keeps its date; a reap that NAMES the frame is
            # direct evidence and keeps its date.
            out.update(ts=None, when=None,
                       words="%s - which of its trims took it cannot be told: its name carries no capture time" % (
                           "released with its reel by the retention lane" if code == "released"
                           else "taken with its reel by the recorder's disk-floor reaper"))
        if unread:
            # v3868 (the Grok CLI on REG-3207) - an unreadable record may hold an EARLIER deleter: said, never hidden
            out["words"] += " (%s could not be read, so an earlier deleter cannot be ruled out)" % ", ".join(unread)
            out["unread"] = list(unread)
        return out
    if unread:
        return {"code": "unknown", "ts": None, "when": None, "by": None,
                "words": "UNKNOWN — %s could not be read" % ", ".join(unread)}
    return {"code": "unknown", "ts": None, "when": None, "by": None,
            "words": "UNKNOWN — no deleter recorded taking it and no refusal recorded for it"}


def _unread(reaps, tombstones, refusals):
    return [n for n, v in (("the reap record", reaps), ("the tombstones", tombstones), ("the refusal record", refusals))
            if v is None]


def who_took(frame_id, reaps, tombstones, refusals, read_ts=None, session=None):
    """Why a read's picture is not on disk. -> (code, words)

    code: 'never-written' (the recorder refused it — disk floor / hard floor / budget), 'reaped' (the recorder's
    floor reaper took it — loose film or a whole reel), 'released' (retention released its reel), 'unknown'.
    Each input may be None (that record could not be read); then the answer can only be UNKNOWN for it.
    """
    g = judge(frame_id, index(reaps, tombstones), refusals, read_ts, session, _unread(reaps, tombstones, refusals))
    return g["code"], g["words"]


_RECORDS_MEMO = {"key": None, "val": None}
_RECORDS_LOCK = threading.Lock()


def _stat_key(path):
    try:
        st = os.stat(path)
        return (path, st.st_mtime_ns, st.st_size)
    except OSError:
        return (path, None, None)


def records(hist_dir):
    """(reaps, tombstones, refusals, index) for this shelf, read again only when one of the three files changes.

    REG-3207 - /hist asks this for EVERY frame it cannot serve, and a pruned reel's scrub strip asks for dozens at
    once; the reap record names tens of thousands of frames, so it is read and indexed once per change, never per
    request."""
    root = root_of(hist_dir)
    try:
        import reel_retention as _rr
        tomb = _rr._tombstone_path(hist_dir)
    except Exception:
        tomb = None          # v3868 (the Grok CLI on REG-3207) - a key over a path the loader may not read is no key
    key = (tuple(_stat_key(p) for p in (os.path.join(root, REAPS), tomb, os.path.join(root, REFUSALS)))
           if tomb else None)
    with _RECORDS_LOCK:
        if key is not None and _RECORDS_MEMO["key"] == key:
            return _RECORDS_MEMO["val"]
    reaps = load_jsonl(os.path.join(root, REAPS))
    tombs = load_tombstones(hist_dir)
    refusals = load_jsonl(os.path.join(root, REFUSALS))
    val = (reaps, tombs, refusals, index(reaps, tombs))
    with _RECORDS_LOCK:
        _RECORDS_MEMO["key"], _RECORDS_MEMO["val"] = key, val
    return val


def gone_for(frame_ref, hist_dir):
    """/hist's question: this frame is not on disk - who took it, and when? -> judge()'s dict.
    The same judge the doctor row and /api/picture_status use, over the memoized records."""
    reaps, tombs, refusals, idx = records(hist_dir)
    return judge(frame_ref, idx, refusals, None, None, _unread(reaps, tombs, refusals))


def named_reads(rows, now_ms=None, window_ms=DAY_MS):
    """Reads that named something, inside the window. -> [{frameId, sessionId, ts, names}]
    A read names something when its own `names` (or names_new) list is non-empty — the sighting the vault and the
    chronicle are built from. Provisional and simulated rows are not reads of his game."""
    now_ms = now_ms or int(time.time() * 1000)
    out, seen = [], set()
    for r in rows or []:
        if not isinstance(r, dict) or r.get("provisional") or r.get("sim"):
            continue
        names = [n for n in (r.get("names") or r.get("names_new") or []) if isinstance(n, str) and n.strip()]
        if not names:
            continue
        try:
            ts = int(r.get("captureTs") or r.get("ts") or 0)
        except (TypeError, ValueError):
            ts = 0
        if not ts or now_ms - ts > window_ms:
            continue
        fid = str(r.get("frameId") or "")
        key = fid or ("?%s" % ts)
        if key in seen:
            continue
        seen.add(key)
        out.append({"frameId": fid, "sessionId": str(r.get("sessionId") or ""), "ts": ts, "names": names[:6]})
    return out


def locator(hist_dir):
    """frame ref -> bool | None. None = the shelf could not be read at all.

    ⚠ PROBES, NEVER WALKS. frame_ref.Index stats every file on the shelf (tens of thousands of his frames) and the
    doctor asks this every tick — "a watcher over a growing folder hangs a gate with a clean diff" is a scar in
    this tree. Only the frames actually asked about are looked for: the exact relative path (flat `<n>_<ms>` read
    frames, `reel_<sid>/f_<ms>` paths), then the bare STEM — at the top level and inside every reel directory.

    ⚠ M5 (review of 77d8d8b5, reproduced) — A REEL-RELATIVE REF WHOSE FILE IS STILL LOOSE READ AS MISSING. The journal
    names a frame `reel_<sid>/f_<ms>` the moment it is read, but the file may still sit loose at the top level (it is
    moved into its reel when the reel is sealed), and this returned False right after the exact miss for any ref with a
    '/' in it — so the doctor said 'a read left no picture' about a picture that was on disk. frame_ref.Index.resolve
    has always answered this: exact path first, the stem as the fallback. The probe now does the same, without the
    walk: the stem at the top level, then in every reel. A stem found in more than one place is still ON DISK (the same
    capture ms) — presence is the question here, not which path. [[feedback-suspect-the-instrument]]"""
    try:
        reels = sorted(d for d in os.listdir(hist_dir) if d.startswith("reel_"))
    except OSError:
        return None

    def present(ref):
        s = str(ref or "").replace("\\", "/").strip().lstrip("/")
        if not s or ".." in s.split("/"):
            return False
        rel = s if s.lower().endswith((".jpg", ".png")) else s + ".jpg"
        try:
            if os.path.isfile(os.path.join(hist_dir, rel)):
                return True
            # the exact path missed: the bare stem, top level first, then every reel (frame_ref.Index.resolve's order)
            base = rel.rsplit("/", 1)[-1]
            if "/" in rel and os.path.isfile(os.path.join(hist_dir, base)):
                return True
            return any(os.path.isfile(os.path.join(hist_dir, r, base)) for r in reels)
        except OSError:
            return None
    return present


def verdict(reads, present, reaps, tombstones, refusals):
    """The doctor row 'a read left no picture'. PURE. -> (status, why, counts)
    status: OK | MISSING | UNKNOWN (the doctor's own three words). `present` is locator()'s answer or None."""
    if reads is None:
        return UNKNOWN, "the reader's journal could not be read, so which reads named things is unknown", {}
    if present is None:
        return UNKNOWN, "the frame shelf could not be indexed, so whether any picture is on disk is unknown", {}
    gone, unknown_n = [], 0
    for r in reads:
        fid = r.get("frameId")
        if not fid:
            code, words = who_took("", reaps, tombstones, refusals, r.get("ts"), r.get("sessionId"))
            gone.append((r, "no frame id — " + (words if code == "never-written" else "the read was journaled without a picture")))
            continue
        p = present(fid)
        if p is None:
            unknown_n += 1
            continue
        if not p:
            code, words = who_took(fid, reaps, tombstones, refusals, r.get("ts"), r.get("sessionId"))
            gone.append((r, words))
    counts = {"reads": len(reads), "gone": len(gone), "unknown": unknown_n}
    if not reads:
        return OK, "no read named anything in the last 24 h (0 reads with names — nothing to keep)", counts
    if gone:
        first = gone[:3]
        return MISSING, ("%d of %d read(s) with names in the last 24 h left no picture: %s"
                           % (len(gone), len(reads), " · ".join("%s (%s) — %s" % (r.get("frameId") or "?", ", ".join(r["names"][:2]), w)
                                                             for r, w in first))), counts
    if unknown_n:
        return UNKNOWN, ("%d read(s) with names — whether %d of their pictures are on disk could not be established"
                           % (len(reads), unknown_n)), counts
    return OK, "every read with names in the last 24 h has its picture on disk (%d of %d)" % (len(reads), len(reads)), counts


def status_for(ids, hist_dir):
    """/api/picture_status — for each frame id: {present, code, why}. An id the shelf cannot answer for is UNKNOWN."""
    present = locator(hist_dir)
    reaps = load_jsonl(os.path.join(root_of(hist_dir), REAPS))
    refusals = load_jsonl(os.path.join(root_of(hist_dir), REFUSALS))
    tombs = load_tombstones(hist_dir)
    out = {}
    for fid in ids[:40]:
        fid = str(fid or "").strip()
        if not fid:
            continue
        p = present(fid) if present else None
        if p:
            out[fid] = {"present": True, "code": "present", "why": None}
            continue
        if p is None:
            out[fid] = {"present": None, "code": "unknown", "why": "UNKNOWN — the frame shelf could not be read"}
            continue
        sess = None
        try:
            import frame_ref as _fr
            reel = _fr.reel_of(fid)
            sess = reel[5:] if reel and reel.startswith("reel_") else None
        except Exception:
            sess = None
        code, words = who_took(fid, reaps, tombs, refusals, None, sess)
        out[fid] = {"present": False, "code": code, "why": words}
    return {"ok": True, "pictures": out}
