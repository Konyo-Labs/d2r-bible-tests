"""ONE way to address a frame, because three ad-hoc ones invented three crises in a day.

WHY THIS EXISTS. A frame in this tree is referred to in THREE shapes, and every measurement that
knew only one of them produced an alarming number that was false:

    <n>_<ms>                        e.g. 21_1787522052389      (journal frameId, no extension)
    f_<ms>.jpg                      e.g. f_1788202324097.jpg   (top-level capture)
    <reel>/f_<ms>.jpg               e.g. reel_s_1784984019250_95276/f_1784984201778

Measured 2026-09-01, each of these was reported to Konyo before being checked, and each was wrong:

    "45% of cited frames are gone from disk"       -> resolver tested only `k == fid`
    "48% carry a reel id where a frame belongs"    -> they are PATHS, which carry more, not less
    "100% of named claims are unprovable"          -> endswith("/"+stem) needs a directory, and
                                                      top-level files have none

With a correct two-way index - full relative path AND bare stem - **every cited frame resolves.
0 gone, in both the named and unnamed sets.** There are no orphaned frameIds and no unprovable
claims. The corpus was never the problem; the questions were.

⚠ THE POINT IS NOT THE DATA, IT IS THE ARITHMETIC. A resolver that silently fails to match
answers "missing", and "missing" is indistinguishable from "deleted" to every caller. That is how
a healthy 9.6 GB archive read as 45% rotted three times in one evening.
[[feedback-suspect-the-instrument]] [[unknown-stays-unknown]]
"""

import os
import threading
import time

# ── REG-1412 (#66) — THE CONSOLE PATH, AND WHAT IT MAY REMEMBER ────────────────────────────────────
# MEASURED on his ALT (Windows + Boosteroid, ~30 reels, ~21,000 frames), 2026-09-29 01:25-01:45, right after
# v3522 landed: /api/river timed out at 90 s while THREE threads (tvd-retro-triage, tvd-eagle-watch and an
# HTTP request) were each inside Index.__init__ at the same moment, each re-listing every folder of the shelf
# from scratch. Only ONE of those folders was moving - the live shadow reel. A sealed reel's folder cannot
# change without its own mtime moving, so re-listing it answers a question already answered.
#
# ⚠ ONLY A CONSOLE REMEMBERS. control_app.main() calls mark_console_path() at boot. Everywhere else - every
# law, the gate, CI, a CLI run - lists exactly as before: a law may repoint, age (os.utime) or monkeypatch
# anything, and a cache cannot key on a monkeypatch. An input you cannot key on means no memo for that path.
_CONSOLE = {"on": False}


def mark_console_path(on=True):
    """This process IS a console (control_app.main() at boot). -> None. Off everywhere else."""
    _CONSOLE["on"] = bool(on)


def on_console_path():
    """Is this process a console? -> bool (False unless control_app.main() said so)."""
    return bool(_CONSOLE["on"])


#: A folder whose mtime (or, on POSIX, change time) is younger than this is MOVING: its listing is never kept.
#: 3 s covers the coarsest clock that stamps these folders (FAT's 2 s; NTFS is stamped from a ~15.6 ms
#: clock) - a second change inside one tick leaves the stamp unchanged, so a folder is trusted only once it
#: has been still for longer than any tick. The same rule git calls "racily clean".
RACY_S = 3.0
_LISTINGS = {}                  # absolute folder -> (folder key, entries)
_LISTINGS_MAX = 4096            # a bound, not a policy: past it the memory is simply dropped
_LIST_LOCK = threading.Lock()
#: what the per-folder memory did in this process - read by the law and by the measurement
LIST_STATS = {"listed": 0, "served": 0, "kept": 0, "moving": 0, "builds": 0}
#: One plan() shares the listings it just read, including a folder too new to keep. The console
#: memory above refuses a moving folder, so Index and _dir_mb each stat'd every frame in it.
_PASS = threading.local()


def folder_key(st):
    """The identity of a folder's CONTENTS as the file system stamps it. -> tuple

    mtime and (POSIX) ctime move on every create, delete and rename inside the folder; ino/dev change if the
    folder is replaced; size/nlink are extra witnesses where the platform fills them. On Windows st_ctime is
    the creation time, which is still an identity witness."""
    return (st.st_mtime_ns, getattr(st, "st_ctime_ns", 0), st.st_ino, st.st_dev, st.st_size, st.st_nlink)


def still(st, now_ns=None):
    """Has this path been still for RACY_S? -> bool. A stamp in the future is not still."""
    now_ns = time.time_ns() if now_ns is None else now_ns
    newest = max(st.st_mtime_ns, getattr(st, "st_ctime_ns", 0))
    return now_ns - newest >= int(RACY_S * 1e9)


def _is_junction(e):
    """REG-1668 - is this DirEntry a Windows directory JUNCTION? -> bool. Never raises.

    A junction is a linked folder exactly as a symlink is, and the index never enters either. os.walk DOES walk into
    one (os.path.islink is False for it), so this is the one place the index is deliberately stricter than the walk
    it replaced: a junction under the shelf would list a reel twice, and one pointing at an ancestor would never end.
    MEASURED on his ALT: Windows refuses an ordinary symlink without a privilege, so the symlink case skipped there
    and the heart called the gate BLIND - the junction is the linked folder that PC can actually make.
    DirEntry.is_junction is Python 3.12+; on an older Python (his Mac's 3.9) there are no junctions to find."""
    f = getattr(e, "is_junction", None)
    if f is None:
        return False
    try:
        return bool(f())
    except OSError:
        return False


def _scan(folder):
    """One folder, listed once. -> tuple of (name, kind, size) | None when it cannot be listed.

    kind: 'd' a folder to walk into, 'l' a symlinked folder or a Windows junction (never entered), 'f' a file
    (and anything whose type cannot be read, as before). size: from the listing, None when it cannot be read.
    ⚠ 2026-09-28 — ONE LISTING PER FOLDER, NEVER ONE STAT PER FILE: on Windows the listing already carries each
    file's size, so DirEntry.stat() costs nothing (REG-1360, 34,143 nt.stat calls on his ALT)."""
    try:
        with os.scandir(folder) as it:
            entries = list(it)
    except OSError:
        return None
    out = []
    for e in entries:
        try:
            is_dir = e.is_dir()
        except OSError:
            is_dir = False
        if is_dir:
            try:
                if not (e.is_symlink() or _is_junction(e)):
                    out.append((e.name, "d", None))
                else:
                    out.append((e.name, "l", None))
            except OSError:
                out.append((e.name, "?", None))
            continue
        try:
            size = e.stat().st_size
        except OSError:
            size = None
        out.append((e.name, "f", size))
    return tuple(out)


def folders(folder):
    """(name, kind, None) for one folder, or None when it cannot be listed. Never stats a file.

    kind is the same as _scan: 'd' a real folder, 'l' a symlink or junction, 'f' a file. The size
    slot is always None — a fingerprint only needs to know which folders exist, and a directory's
    own stamp already moves when a file inside it is added or removed. Statting every frame here
    made a river read scale with frames on a shelf whose reel count was the small one."""
    try:
        with os.scandir(folder) as it:
            entries = list(it)
    except OSError:
        return None
    out = []
    for e in entries:
        try:
            is_dir = e.is_dir()
        except OSError:
            is_dir = False
        if not is_dir:
            out.append((e.name, "f", None))
            continue
        try:
            if not (e.is_symlink() or _is_junction(e)):
                out.append((e.name, "d", None))
            else:
                out.append((e.name, "l", None))
        except OSError:
            out.append((e.name, "?", None))
    return tuple(out)


def begin_pass():
    """A plan() is about to read the shelf. Listings it takes are reused until end_pass. -> None"""
    depth = getattr(_PASS, "depth", 0) + 1
    _PASS.depth = depth
    if depth == 1:
        _PASS.memo = {}


def end_pass():
    """The plan() finished. Drop the listings it shared. -> None"""
    depth = getattr(_PASS, "depth", 0) - 1
    if depth <= 0:
        _PASS.depth = 0
        _PASS.memo = None
    else:
        _PASS.depth = depth


def listing(folder):
    """A folder's entries -> tuple of (name, kind, size) | None. The one listing Index and _dir_mb share.

    Off the console path: a fresh listing, always - exactly what the walk did before.
    On the console path: a listing is KEPT only when the folder had been still for RACY_S before it was read,
    was not changed while it was read (its key is taken again after), and holds no `*.tmp` (a write in flight -
    every writer into a reel folder writes a .tmp and os.replace()s it, and a frame is created whole). It is
    SERVED only while the folder's key (folder_key) is identical. So the key covers: which names are in the
    folder and whether each is a file or a folder. It does NOT cover a file rewritten IN PLACE in a folder that
    has been still for RACY_S - nothing in this tree writes a reel folder that way (frames are created whole,
    index.json and kai_report.json go through .tmp + os.replace), and such a file's SIZE would be the only
    thing out of date. A folder that cannot be stat'd is listed fresh and never kept.

    During begin_pass()/end_pass() the same folder is read once even when it is moving, so one plan does not
    stat every frame twice (the index, then each reel's size)."""
    memo = getattr(_PASS, "memo", None)
    if isinstance(memo, dict) and folder in memo:
        return memo[folder]
    got = _listing_once(folder)
    if isinstance(memo, dict):
        memo[folder] = got
    return got


def _listing_once(folder):
    if not _CONSOLE["on"]:
        return _scan(folder)
    try:
        st = os.stat(folder)
    except OSError:
        with _LIST_LOCK:
            _LISTINGS.pop(folder, None)
        return _scan(folder)
    key = folder_key(st)
    with _LIST_LOCK:
        hit = _LISTINGS.get(folder)
        if hit is not None and hit[0] == key:
            LIST_STATS["served"] += 1
            return hit[1]
    got = _scan(folder)
    with _LIST_LOCK:
        LIST_STATS["listed"] += 1
    if got is None:
        return None
    keep = still(st) and not any(n.endswith(".tmp") for n, _k, _s in got)
    if keep:
        try:
            keep = folder_key(os.stat(folder)) == key
        except OSError:
            keep = False
    with _LIST_LOCK:
        if keep:
            if len(_LISTINGS) >= _LISTINGS_MAX:
                _LISTINGS.clear()
            _LISTINGS[folder] = (key, got)
            LIST_STATS["kept"] += 1
        else:
            _LISTINGS.pop(folder, None)
            LIST_STATS["moving"] += 1
    return got


def _forget_listings():
    """Drop every kept listing (a law's clean slate). -> None"""
    with _LIST_LOCK:
        _LISTINGS.clear()
        for k in LIST_STATS:
            LIST_STATS[k] = 0

# a plausible capture epoch in ms: 2001-09-09 .. 2033-05-18. Wide on purpose - this rejects a
# reel's random suffix (5 digits) and an index (1-2 digits), not a real timestamp.
_MIN_TS_DIGITS = 12
_MAX_TS_DIGITS = 14


def timestamp_of(frame_ref):
    """The capture ms inside any of the three shapes. -> int | None.

    None means NOT ESTABLISHED. It never guesses: `reel_s_1788190210097_78660` has two numeric
    chunks and the LAST one is a random suffix, so a naive rsplit returns 78660 - a 1970
    timestamp presented as real. Only chunks of plausible epoch length are accepted.
    """
    if not frame_ref:
        return None
    base = str(frame_ref).replace("\\", "/")
    base = base.rsplit("/", 1)[-1]          # a path's frame is its last segment
    for chunk in reversed(base.replace(".", "_").split("_")):
        # ⚠ TAKE THE LEADING DIGIT RUN, not the whole chunk. 42 rows in his journal carry a
        # suffix - `15_1787496136628#v` - and a bare isdigit() test refuses them outright. The
        # timestamp is right there; refusing it is honest but needlessly lossy.
        run = ""
        for ch in chunk:
            if ch.isdigit():
                run += ch
            else:
                break
        if _MIN_TS_DIGITS <= len(run) <= _MAX_TS_DIGITS:
            try:
                return int(run)
            except ValueError:
                return None
    return None


def reel_of(frame_ref):
    """The reel a path-shaped ref names. -> str | None (a bare ref names no reel)."""
    if not frame_ref:
        return None
    s = str(frame_ref).replace("\\", "/")
    if "/" not in s:
        return None
    head = s.rsplit("/", 1)[0].rsplit("/", 1)[-1]
    return head or None


def stem_of(frame_ref):
    """The bare filename without directory or extension."""
    if not frame_ref:
        return ""
    s = str(frame_ref).replace("\\", "/").rsplit("/", 1)[-1]
    return os.path.splitext(s)[0]


class Index(object):
    """A resolver over one frame root. Built once, asked many times.

    Indexes BOTH ways a frame is addressed, because that is the whole point: by full relative
    path, and by bare stem. A stem can be ambiguous (the same capture ms under two reels); the
    index keeps every hit and `resolve` prefers an exact path match before falling back.
    """

    def __init__(self, root):
        self.root = root
        self.by_path = {}
        self.by_stem = {}
        self.files = 0
        self.bytes = 0
        if not root or not os.path.isdir(root):
            return
        # ⚠ 2026-09-28 — ONE LISTING PER FOLDER, NEVER ONE STAT PER FILE. MEASURED on his ALT (Windows +
        # Boosteroid, 14 reels): /api/river took 32.8 s there against 4.1 s for 66 reels on the Mac, and a
        # profile put 4.1 s of an 8.2 s lane view in 34,143 nt.stat calls from os.path.getsize here, plus 1.7 s
        # in 21,349 relpath calls. On Windows the directory listing already carries each file's size, so
        # DirEntry.stat() costs nothing; the relative path is the folder's prefix plus the name. Same walk
        # order as os.walk(topdown) - a folder's files, then its subfolders in listing order - and a symlinked
        # folder is not entered, as os.walk does not.
        # ⚠ REG-1412 — the listing comes from listing(), which on a CONSOLE serves a still folder's last
        # listing instead of reading it again (see its docstring for exactly what its key covers).
        with _LIST_LOCK:
            LIST_STATS["builds"] += 1
        todo = [(root, "")]
        while todo:
            here, prefix = todo.pop()
            entries = listing(here)
            if entries is None:
                continue
            sub = []
            for name, kind, size in entries:
                if kind == "d":
                    sub.append((os.path.join(here, name), prefix + name + "/"))
                    continue
                if kind != "f":
                    continue
                full = os.path.join(here, name)
                rel = (prefix + name).replace("\\", "/")
                self.by_path[rel] = full
                self.by_stem.setdefault(stem_of(rel), []).append(rel)
                self.files += 1
                if size is not None:
                    self.bytes += size
            todo.extend(reversed(sub))

    def resolve(self, frame_ref):
        """-> the relative path on disk, or None. Exact path wins; stem is the fallback."""
        if not frame_ref:
            return None
        f = str(frame_ref).replace("\\", "/").strip()
        for cand in (f, f + ".jpg", f + ".png"):
            if cand in self.by_path:
                return cand
        hits = self.by_stem.get(stem_of(f)) or []
        if not hits:
            return None
        if len(hits) == 1:
            return hits[0]
        # ambiguous: if the ref names a reel, honour it; otherwise refuse rather than pick
        r = reel_of(f)
        if r:
            for h in hits:
                if h.startswith(r + "/"):
                    return h
        return None

    def exists(self, frame_ref):
        return self.resolve(frame_ref) is not None


def cited_frames(rows):
    """Split a journal into the frames it cites, by whether the row NAMED an item.

    -> (named:set, other:set). A prune gate must never delete anything in `named` - that is the
    receipt for a claim. `other` is fair game once its reel is sealed.
    """
    named, other = set(), set()
    for r in (rows or []):
        fid = r.get("frameId") or r.get("frame")
        if not fid:
            continue
        (named if (r.get("items") or r.get("names")) else other).add(str(fid))
    return named, other


def prunable(index, rows):
    """Which files on disk no claim depends on. -> (prunable:list, protected:int, why)

    The receipt rule, stated once: a frame cited by a row that NAMED an item is PROOF of that
    claim and may not be deleted while the claim stands. Everything else is prunable.
    """
    named, _other = cited_frames(rows)
    protect = set()
    for fid in named:
        hit = index.resolve(fid)
        if hit:
            protect.add(hit)
    out = [p for p in index.by_path if p not in protect]
    return out, len(protect), ("%d file(s) on disk; %d hold the proof of a named claim and are "
                               "protected; %d prunable" % (index.files, len(protect), len(out)))


if __name__ == "__main__":
    try:
        from console_safe import enable
        enable()
    except Exception:
        pass
    import io as _io, json as _json, sys as _sys
    _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import control_app as ca
    idx = Index(ca.HIST_DIR)
    rows = []
    for p in ca._journal_ring():
        if not os.path.isfile(p):
            continue
        with _io.open(p, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(_json.loads(line))
                except Exception:
                    pass
    named, other = cited_frames(rows)
    gone_named = [f for f in named if not idx.exists(f)]
    gone_other = [f for f in other if not idx.exists(f)]
    pr, protected, why = prunable(idx, rows)
    print("frames on disk : %d  (%.2f GB)" % (idx.files, idx.bytes / 1e9))
    print("journal rows   : %d across the ring" % len(rows))
    print("cited by a NAMED row : %d   unresolvable: %d" % (len(named), len(gone_named)))
    print("cited by any other   : %d   unresolvable: %d" % (len(other), len(gone_other)))
    print(why)
