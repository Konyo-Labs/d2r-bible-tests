# -*- coding: utf-8 -*-
"""#172 PHASE B - A SOURCE AUDIT RUNS IN A SHORT-LIVED CHILD, SO ITS PARSE MEMORY LEAVES WITH THE CHILD.

MEASURED 2026-10-27 (#172, a private console on a no-.git copy of his main tree, 150 s, tracemalloc): the console spent
its memory PARSING ITS OWN SOURCE. chronicle_routes.routes() read ~1,400 tv/*.py, held 45.8 MB of decommented text and
ast.parsed them all (939k objects); health_engine._lane_spans() ast.parsed the 49k-line control_app.py (930k objects).
ast.parse builds C-level arenas tracemalloc does not see, and the freed big blocks stay resident: vmmap on his Mac showed
1.2 GB of freed-but-resident MALLOC_LARGE 55 s after a start, and the ALT kept 1.28 GB private on 7.9 GB. Phase A
(REG-2638, v3812) memoised the per-file parses; this is the first parse after an update.

    python3 audit_child.py routes        # derives chronicle_routes.routes() and writes its own disk cache
    python3 audit_child.py lane_spans    # derives health_engine's lane spans and writes LANE_SPANS_CACHE
    python3 audit_child.py red_proofs    # every gate file's RED_PROOF list (heart2.red_proofs_in), per file stamp
    python3 audit_child.py swallow ROOT  # the swallow census's rows of every .py under ROOT, per file stamp

#172 PHASE C (REG-2985, measured 2026-10-29 on a scratch console of his Mac, Python 3.9, his data, no .git, 300 s): the
console still called ast.parse 4,508 times over 118 MB of source in its own heap - the swallow census 1,488 files, and
heart2.red_proofs_in 2,473 times (1,237 gate files, read once for the self-arming owed list and once more for the attack
tally, each with its own memo). RSS rose in spikes to 550-1,028 MB; macOS hands that back within seconds, and the ALT's
console (Python 3.12, 7.9 GB) holds 1,118 MB working set / 1,565 MB private. With those two answered from a separate
process instead: 540 parses (33 MB), max RSS 376 MB. Both are kept per file and keyed on the file's own stamp
(mtime_ns, size); a stale entry is never served, and a file the child could not read is not kept (it is asked again).

The child writes the SAME cache the console reads, keyed on the same source stamps, then exits - and its memory with it.

⚠ ONLY A CONSOLE SPAWNS (frame_ref.on_console_path(), set by control_app.main()). Every law, the gate, CI and a CLI run
derive in their own process exactly as before: a law may monkeypatch a module, and a child cannot see a monkeypatch.
⚠ FAILS OPEN: a child that times out, exits non-zero or writes nothing leaves the caller to derive in-process as it
always did, and the failure is recorded here - on / worked / lastTs / say, the heart's vocabulary - never read as clean.
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable     # a child on a cp1255 console must never crash while it reports
    _enable()
except Exception:
    pass

#: the marker a child carries, so a child never spawns a child
CHILD_ENV = "TVD_AUDIT_CHILD"
#: a cold route census measured 16.1 s on his Mac (v2692); the ALT is slower. Past this the console derives itself.
TIMEOUT_S = 180
AUDITS = ("routes", "lane_spans", "red_proofs", "swallow")
#: the per-file caches a child writes for the console to read (beside the route census's own, fixture-aware)
RP_CACHE = ".red_proofs_cache.json"
SW_CACHE = ".swallow_rows_cache.json"
#: a cold miss asks the child at most once in this long; between, the caller derives what it still lacks itself
ASK_EVERY_S = 600

#: what each audit last did in THIS console: {name: {runs, hits, fails, lastTs, lastMs, lastOk, say}}
STATE = {}


def wanted():
    """Does this process send a cold source audit to a child? -> bool. A console only, and never a child itself."""
    if os.environ.get(CHILD_ENV) == "1":
        return False
    try:
        import frame_ref as _fr
        return bool(_fr.on_console_path())
    except Exception:
        return False


def _row(name):
    return STATE.setdefault(name, {"runs": 0, "hits": 0, "fails": 0, "lastTs": None, "lastMs": None,
                                   "lastOk": None, "say": "not asked since this console started"})


def hit(name):
    """The cache already held the answer: nothing was spawned."""
    _row(name)["hits"] += 1


def run(name, timeout=TIMEOUT_S, _spawn=None, args=()):
    """Derive audit `name` in a short-lived child. -> (ok, why). Never raises; the caller reads the cache after."""
    r = _row(name)
    if name not in AUDITS:
        return False, "no audit named %r" % (name,)
    # REG-3102 - A CHILD NEVER SPAWNS A CHILD, AT THE SPAWN ITSELF. wanted() was the only thing holding it: with that one
    # line gone, every child's own _lane_spans() saw no cache and spawned the next - measured 2026-10-29, one level every
    # ~0.19 s at ~72 MB each, nothing derived until the 180 s timeout - and a red-proof doing exactly that ran a hosted
    # runner out of memory twice (publish 40812615686, proof shard 7). Refused here, the child derives in its own process.
    if os.environ.get(CHILD_ENV) == "1":
        return False, "a child never spawns a child - it derives in its own process (REG-3102)"
    env = dict(os.environ)
    env[CHILD_ENV] = "1"
    t0 = time.time()
    try:
        p = (_spawn or subprocess.run)([sys.executable, os.path.abspath(__file__), name] + [str(a) for a in args], cwd=HERE, env=env,
                                       capture_output=True, text=True, timeout=timeout,
                                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        ok = p.returncode == 0
        # REG-2733 - the child's OWN sentence first: on the ALT (Python 3.12) stderr carried SyntaxWarnings from the files
        # it parsed, and the last of them stood in for "the routes were derived but their cache was not written"
        _said = ((p.stdout or "").strip().splitlines() or (p.stderr or "").strip().splitlines() or ["-"])[-1][:160]
        why = ("derived in a child process (%.1f s)" % (time.time() - t0) if ok else
               "the child exited %s: %s" % (p.returncode, _said))
    except subprocess.TimeoutExpired:
        ok, why = False, "the child did not finish in %d s" % timeout
    except Exception as e:
        ok, why = False, "the child could not be started (%s)" % type(e).__name__
    r["runs"] += 1
    r["lastTs"] = int(time.time() * 1000)
    r["lastMs"] = int((time.time() - t0) * 1000)
    r["lastOk"] = ok
    if not ok:
        r["fails"] += 1
    r["say"] = why if ok else (why + " - this console derived it itself, in its own memory")
    return ok, why


def status():
    """The heart's vocabulary for the doctor: on / worked / lastTs / say per audit. lastOk None = never asked."""
    on = wanted()
    out = {"on": on, "audits": {}}
    for name in AUDITS:
        r = dict(_row(name))
        r["worked"] = r["runs"] - r["fails"]
        out["audits"][name] = r
    return out


def _cache_root():
    """Where a child's per-file caches live: beside the route census's own cache (a fixture world keeps them in its root)."""
    try:
        import chronicle_routes as _cr
        return _cr._routes_cache_root()
    except Exception:
        return HERE


_DISK = {}
_LOCKS = {}


def _lock(name):
    import threading
    return _LOCKS.setdefault(name, threading.Lock())


def _disk(cache):
    """A child-written cache, read once per its own file stamp. -> dict, or None when it is absent or will not read: no
    answer here, so the caller asks the child (and derives itself after) - never an empty cache read as a real one"""
    p = os.path.join(_cache_root(), cache)
    try:
        st = os.stat(p)
        mk = (p, st.st_mtime_ns, st.st_size)
    except OSError:
        return None
    got = _DISK.get(cache)
    if got is not None and got[0] == mk:
        return got[1]
    try:
        with open(p, encoding="utf-8") as fh:
            blob = json.load(fh)
    except Exception:
        return None
    if not isinstance(blob, dict):
        return None
    _DISK[cache] = (mk, blob)
    return blob


def _write_cache(cache, blob):
    p = os.path.join(_cache_root(), cache)
    try:
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(blob, fh)
        os.replace(tmp, p)              # atomic: a half-written cache is never readable
        return True
    except Exception:
        return False


def _per_file(name, cache, pick, key, args=()):
    """#172 phase C - a console's per-file answer from the cache a child wrote, asking the child at most once per
    ASK_EVERY_S when the file is missing or stale there. -> the answer, or None: the caller derives it itself (a law, the
    gate, CI, a CLI, a child, or a file the child could not read)."""
    if not wanted():
        return None
    want = [int(key[0]), int(key[1])]
    _pick = lambda: (lambda d: None if d is None else pick(d))(_disk(cache))
    e = _pick()
    if _fresh(e, want):
        hit(name)
        return e[2]
    with _lock(name):
        e = _pick()                                  # another thread's child may have written it meanwhile
        if _fresh(e, want):
            hit(name)
            return e[2]
        if time.time() - (_row(name).get("askedAt") or 0) < ASK_EVERY_S:
            return None
        _row(name)["askedAt"] = time.time()
        run(name, args=args)
        e = _pick()
        if _fresh(e, want):
            return e[2]
    return None


def _fresh(e, want):
    """A cache entry [mtime_ns, size, answer] is served only for the very stamp the caller holds; another is stale."""
    return isinstance(e, list) and len(e) == 3 and e[:2] == want


def red_proofs_for(filename, key):
    """heart2.red_proofs_in's console door: this gate file's RED_PROOF list at this stamp, or None (derive it)."""
    return _per_file("red_proofs", RP_CACHE, lambda d: (d.get("files") or {}).get(filename), key)


def swallow_rows_for(path, root, key):
    """swallow_census._file_rows's console door: this file's rows under this root at this stamp, or None (derive them)."""
    return _per_file("swallow", SW_CACHE,
                     lambda d: ((d.get("roots") or {}).get(root) or {}).get(path), key, args=(root,))


def _write_lane_spans(he):
    """The child's half: write the spans it just derived, keyed on the stat they were derived from, where the engine reads
    them (health_engine._lane_spans_disk). health_engine itself never writes - it reports. -> bool"""
    snap = getattr(he, "_LANE_SPAN_CACHE", None) or {}
    p = he._lane_spans_cache_path()
    if not p or snap.get("val") is None or not snap.get("key"):
        return False
    try:
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"key": [int(snap["key"][0]), int(snap["key"][1])],
                       "val": {k: list(v) for k, v in snap["val"].items()}}, fh)
        os.replace(tmp, p)              # atomic: a half-written cache is never readable
        return True
    except Exception:
        return False


def _child(name, argv=()):
    if name == "routes":
        import chronicle_routes as _cr
        d = _cr.routes()
        if _cr.cached() is None:
            print("the routes were derived but their cache was not written (an unkeyable source?)")
            return 3
        print(json.dumps({"ok": True, "audit": name, "routes": len((d or {}).get("routes") or [])}))
        return 0
    if name == "lane_spans":
        import health_engine as _he
        spans, _src = _he._lane_spans()
        if not _write_lane_spans(_he):
            print("the lane spans were derived but their cache could not be written")
            return 3
        print(json.dumps({"ok": True, "audit": name, "lanes": len(spans)}))
        return 0
    if name == "red_proofs":
        import heart2 as _h2
        files = {}
        for _n, f in _h2.gate_files(say=lambda *a, **k: None):
            p = os.path.join(_h2.HERE, f)
            try:
                st = os.stat(p)
            except OSError:
                continue
            got = _h2.red_proofs_in(f)
            if got is not None:                      # an unreadable file is not kept: it is asked again next time
                files[f] = [st.st_mtime_ns, int(st.st_size), got]
        if not _write_cache(RP_CACHE, {"v": 1, "files": files}):
            print("the red-proof lists were derived but their cache could not be written")
            return 3
        print(json.dumps({"ok": True, "audit": name, "files": len(files)}))
        return 0
    if name == "swallow":
        import swallow_census as _sc
        root = argv[0] if argv else None
        root = root or _sc.REPO
        _sc.scan(root)
        blob = _disk(SW_CACHE)
        roots = dict(blob.get("roots") or {}) if isinstance(blob, dict) else {}   # no cache yet: this root starts it
        roots[root] = dict((p, [k[0], k[1], list(rows)]) for (p, r), (k, rows) in _sc._FILE_ROWS.items() if r == root)
        if not _write_cache(SW_CACHE, {"v": 1, "roots": roots}):
            print("the census rows were derived but their cache could not be written")
            return 3
        print(json.dumps({"ok": True, "audit": name, "files": len(roots[root])}))
        return 0
    print("no audit named %r" % name)
    return 2


if __name__ == "__main__":
    os.environ[CHILD_ENV] = "1"
    sys.exit(_child(sys.argv[1] if len(sys.argv) > 1 else "", sys.argv[2:]))
