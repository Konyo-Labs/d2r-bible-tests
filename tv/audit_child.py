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
    python3 audit_child.py doctor OUT NONCE TICK SLOW PERIODIC CONSOLE [ONLY]   # the eagle's pass (REG-2987)

#172 PHASE C (REG-2985, measured 2026-10-29 on a scratch console of his Mac, Python 3.9, his data, no .git, 300 s): the
console still called ast.parse 4,508 times over 118 MB of source in its own heap - the swallow census 1,488 files, and
heart2.red_proofs_in 2,473 times (1,237 gate files, read once for the self-arming owed list and once more for the attack
tally, each with its own memo). RSS rose in spikes to 550-1,028 MB; macOS hands that back within seconds, and the ALT's
console (Python 3.12, 7.9 GB) holds 1,118 MB working set / 1,565 MB private. With those two answered from a separate
process instead: 540 parses (33 MB), max RSS 376 MB. Both are kept per file and keyed on the file's own stamp
(mtime_ns, size); a stale entry is never served, and a file the child could not read is not kept (it is asked again).

The child writes the SAME cache the console reads, keyed on the same source stamps, then exits - and its memory with it.

#172 REG-2987 (measured 2026-10-29, REG-2985's spike profile on a scratch console): with the parses gone, every RSS spike
past 450 MB sat inside the eagle's in-process console_doctor.run - corroborate's readings, the eye audit, the run census,
the evidence tiers, health_engine.report. The console now asks that pass of a child (doctor_rows) and asks only
console_doctor.IN_PROCESS itself. It is NOT fail-open: the rows are a verdict, so a child that fails, times out or
answers for another ask leaves the pass UNKNOWN until the eagle's next tick - never derived in the console, never an
older pass's rows. One pass at a time; the result file carries the nonce of the ask that made it.

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
AUDITS = ("routes", "lane_spans", "red_proofs", "swallow", "doctor", "lock_index")
#: the per-file caches a child writes for the console to read (beside the route census's own, fixture-aware)
RP_CACHE = ".red_proofs_cache.json"
SW_CACHE = ".swallow_rows_cache.json"
#: #103 item 3 (REG-3484) - each BROAD gate's lock index (self_arming.lock_index), per file stamp
LI_CACHE = ".lock_index_cache.json"
#: a cold miss asks the child at most once in this long; between, the caller derives what it still lacks itself
ASK_EVERY_S = 600
#: REG-2987 - the eagle's pass in a child: the ALT measured 229 s (every-tick checks) + 143 s (periodic) standalone
DOCTOR_TIMEOUT_S = 900
DOCTOR_OUT = ".eagle_child_%s.json"          # one per ask, named by its nonce; removed once read
DOCTOR_PROGRESS = ".eagle_child_progress.json"
#: the pass a child is running now: {nonce, since} - None while none is
DOCTOR = {"nonce": None, "since": None}

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


def run(name, timeout=TIMEOUT_S, _spawn=None, args=(), fails_open=True, low=False):
    """Derive audit `name` in a short-lived child. -> (ok, why). Never raises; the caller reads the cache after.
    `fails_open` False (the doctor, REG-2987): a failure is said as UNKNOWN, never as derived in the console.
    `low` (the doctor): the child runs below normal priority - it is a cold pass every eagle tick, and his game is not."""
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
                                       creationflags=(getattr(subprocess, "CREATE_NO_WINDOW", 0)
                                                      | (getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0) if low else 0)))
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
    r["say"] = why if ok else (why + (" - this console derived it itself, in its own memory" if fails_open
                                      else " - UNKNOWN until it is asked again, never derived in the console"))
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
        # v3863 - a fixture world's TV_HIST is still its root when the census module will not load (never his tv/)
        return os.environ.get("TV_HIST") or HERE


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
    return _write_json(os.path.join(_cache_root(), cache), blob)


def _write_json(p, blob):
    try:
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(blob, fh, default=str)
        os.replace(tmp, p)              # atomic: a half-written cache is never readable
        return True
    except Exception:
        return False


def _doctor_fail(why):
    """The child exited 0 and its rows still cannot be served: recorded as a failure, said as UNKNOWN."""
    r = _row("doctor")
    r["fails"] += 1
    r["lastOk"] = False
    r["say"] = why + " - UNKNOWN until it is asked again, never derived in the console"
    return None, why


def sweep_doctor_orphans(root=None, now=None, older_s=None):
    """REG-3780 (11-12) - an answer nobody will read is removed. -> how many went (None when the dir will not list).

    doctor_rows removes its child's answer in a `finally`, and a console KILLED mid-ask (every update relaunch) never runs
    it: the child finishes and writes rows no process will read. MEASURED on his Mac: three .eagle_child_<nonce>.json
    (~50 KB each) from 11-06, 11-08 and 11-10 - one per relaunch - and nothing ever took them. An answer older than twice
    the child's own timeout belongs to no live ask, so it goes; the progress file and anything younger stay."""
    import re as _re
    root = root or _cache_root()
    now = time.time() if now is None else now
    older_s = 2 * DOCTOR_TIMEOUT_S if older_s is None else older_s
    try:
        names = os.listdir(root)
    except OSError:
        return None
    gone = 0
    for nm in names:
        if not _re.match(r"^\.eagle_child_[0-9a-f]{32}\.json(\.tmp)?$", nm):
            continue
        p = os.path.join(root, nm)
        try:
            if now - os.path.getmtime(p) <= older_s:
                continue
            os.remove(p)
            gone += 1
        except OSError:
            continue
    return gone


def doctor_rows(include_slow, include_periodic, tick, console=None, only=None, timeout=DOCTOR_TIMEOUT_S, _spawn=None):
    """REG-2987 (#172) - the eagle's doctor pass, asked of a short-lived child. -> (rows | None, why)

    rows: every row the child asked (console_doctor.run with IN_PROCESS skipped), from THIS ask only. None is UNKNOWN: the
    child failed, timed out, wrote nothing, or wrote rows for another ask - or another pass is in a child right now (one at
    a time; this one is not asked). `console` is the doctor's console URL in the caller, handed down unchanged."""
    lk = _lock("doctor")
    if not lk.acquire(False):
        since = DOCTOR.get("since")
        return None, "another pass is already running in a child%s" % (
            " (for %d s)" % int(time.time() - since) if since else "")
    root = _cache_root()
    try:
        sweep_doctor_orphans(root)        # REG-3780 - what a killed console's asks left behind
    except Exception:
        pass
    import uuid
    nonce = uuid.uuid4().hex
    out = os.path.join(root, DOCTOR_OUT % nonce)
    DOCTOR.update(nonce=nonce, since=time.time())
    try:
        ok, why = run("doctor", timeout=timeout, _spawn=_spawn, fails_open=False, low=True,
                      args=(out, nonce, int(tick or 0), int(bool(include_slow)), int(bool(include_periodic)), console or "",
                            ",".join(only or ())))
        if not ok:
            return None, why
        try:
            with open(out, encoding="utf-8") as fh:
                blob = json.load(fh)
        except Exception:
            return _doctor_fail("the child exited 0 and wrote no rows")
        if not isinstance(blob, dict) or blob.get("nonce") != nonce:
            return _doctor_fail("the child's rows answer another ask")      # a stale answer is never served
        rows = blob.get("rows")
        if not isinstance(rows, list):
            return _doctor_fail("the child's rows will not read")
        return rows, why
    finally:
        DOCTOR.update(nonce=None, since=None)
        for p in (out, out + ".tmp"):
            try:
                os.remove(p)
            except OSError:
                pass
        lk.release()


def doctor_progress():
    """The check the child's pass sits in now. -> {check, since, tick, nonce} | None (no pass is in a child).
    `check` None: the child has not reached its first check yet (it is starting)."""
    nonce, since = DOCTOR.get("nonce"), DOCTOR.get("since")
    if not nonce:
        return None
    got = None
    try:
        with open(os.path.join(_cache_root(), DOCTOR_PROGRESS), encoding="utf-8") as fh:
            got = json.load(fh)
    except Exception:
        got = None
    if not isinstance(got, dict) or got.get("nonce") != nonce:
        return {"check": None, "since": since, "tick": None, "nonce": nonce}
    return {"check": got.get("check"), "since": got.get("since") or since, "tick": got.get("tick"), "nonce": nonce}


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


def lock_index_for(filename, key):
    """#103 item 3 (REG-3484) - self_arming.lock_index's console door: this BROAD gate file's lock index at this stamp, or
    None (not answered yet - the lock narrows nothing until it is). Parsing test_control in the console's heap is ~140 MB."""
    return _per_file("lock_index", LI_CACHE, lambda d: (d.get("files") or {}).get(filename), key)


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
    if name == "lock_index":
        import heart2 as _h2
        import self_arming as _sa
        files = {}
        for _n, f in _h2.gate_files(say=lambda *a, **k: None):
            p = f if os.path.isabs(f) else os.path.join(_h2.HERE, f)
            try:
                st = os.stat(p)
                with open(p, encoding="utf-8") as fh:
                    text = fh.read()
            except (OSError, ValueError):
                continue
            # only a BROAD gate is ever narrowed: the cheap text rule first, the parse for those alone
            if sum(1 for lk in _sa.LOCK_DOORS if _sa._guards_lock(text, lk, _sa.LOCK_DOORS[lk])) < _sa.NET_NARROW_MIN_LOCKS:
                continue
            got = _sa.lock_index(text)
            if got is not None:                      # a file that will not parse is not kept: it is asked again next time
                files[f] = [st.st_mtime_ns, int(st.st_size), got]
        if not _write_cache(LI_CACHE, {"v": 1, "files": files}):
            print("the lock indexes were derived but their cache could not be written")
            return 3
        print(json.dumps({"ok": True, "audit": name, "files": len(files)}))
        return 0
    if name == "doctor":
        out, nonce, tick, slow, periodic, console, only = (list(argv) + [""] * 7)[:7]
        if hasattr(os, "nice"):
            try:
                os.nice(10)                          # below normal, as the Windows spawn flag sets it there
            except OSError:
                pass
        import console_doctor as _cd
        if console:
            _cd.CONSOLE = console                    # the caller's own URL, unchanged
        prog = os.path.join(_cache_root(), DOCTOR_PROGRESS)

        class _Progress(dict):
            """console_doctor.CURRENT, also written where the console reads it (eagle_state's `measuring`)"""
            def update(self, *a, **k):
                dict.update(self, *a, **k)
                _write_json(prog, {"nonce": nonce, "check": self.get("check"), "since": self.get("since"),
                                   "tick": self.get("tick")})
        _cd.CURRENT = _Progress(_cd.CURRENT)
        try:
            tick = int(tick or 0) or None
        except ValueError:
            tick = None
        rows = _cd.run(include_slow=slow == "1", include_periodic=periodic == "1", tick=tick,
                       only=(set(only.split(",")) if only else None), skip=set(getattr(_cd, "IN_PROCESS", ())))
        if not _write_json(out, {"v": 1, "nonce": nonce, "rows": rows}):
            print("the pass ran but its rows could not be written")
            return 3
        print(json.dumps({"ok": True, "audit": name, "rows": len(rows)}))
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
