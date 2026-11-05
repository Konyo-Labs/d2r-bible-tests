# -*- coding: utf-8 -*-
"""REG-3208 / REG-3209 - WHAT KEEPS GROWING ON THIS DISK IS MEASURED, ITS INFORMATION SAVED AND READ BACK, THEN PRUNED.

His words, 2026-11-05: "whatever keeps growing needs to have a looped system in place that prunes and extracts and saves
any data informational that's needed". MEASURED that night: free disk 6.9 GiB, under his 8 GB ON AIR floor (the console
refuses to record below it). What had grown: 94 scratch dirs in the temp root; the Grok seat's leftover worktrees ~3.3 GB
(some merged and clean, some NOT merged, some not git trees at all, one a folder of 300 lock slots); seven of Claude's own
shipped worktrees (2.2 GB); a 2.7 GB local clone holding ONE commit not upstream by patch-id, which Claude salvaged by
hand (git cherry against origin/main, git format-patch + a README) before removing it. Nothing in the console measured or
pruned any of them: reel retention owns reels and frames only, grok_chat_prune owns his Grok chats only, and the doctor's
disk headroom row reports free GB only.

THE REGISTRY IS DECLARED, NEVER INFERRED (GROWERS below). An entry names its root token and globs, the platforms it
applies on, its owner seat, its kind (how to tell it is finished and what in it is informational), the age floor inside
which nothing is touched, the age bound past which it goes even on a roomy disk, and its mode. A directory no entry names
is never looked at; one an entry names but whose shape is not the entry's kind is left alone and said.

A NEW ENTRY STARTS IN DRY-RUN: it measures, salvages and reads the salvage back, and deletes nothing. It arms itself only
after ARM_AFTER_PASSES clean dry passes (every would-be prune salvaged and read back) spanning ARM_AFTER_H hours - his
ruling on the reel prune (test_self_arming): a prune is never armed by hand, it earns it.

EVERY PASS, IN THIS ORDER (REG-3209 - salvage before prune):
  measure  bytes, newest write, kind, who holds it.
  extract  into the salvage dir (tv/.salvage/, git-ignored) - git: every commit not upstream by patch-id (git cherry
           against origin/main) as a format-patch, the tracked dirty diff, untracked-not-ignored files under a size cap,
           and for a clone its stashes; scratch: a summary (count, bytes, newest, biggest files) and the entry's declared
           informational files (logs as their tail) under a size cap. Plus ONE manifest line per salvage.
  verify   every salvaged file read back and compared by sha256 and size, the meta and the manifest line too.
  prune    only then - `git worktree remove --force` for a linked worktree (so the repo's worktree list stays true), else
           a remove that never follows a link - and only when the disk it sits on is under WATERMARK_GB or it is past
           its age bound.
NEVER PRUNED: anything a live process holds (cwd or an open file), and NOTHING when holders cannot be read; a tree with a
running git (index.lock / HEAD.lock) or a locked worktree; the main tree of linked worktrees; his console's own tree and
anything containing it; tv/frames and his reels (reel retention owns them); the salvage dir itself; anything inside its
age floor; anything whose age could not be measured.

WHAT IT SAYS: the pass record (lane() turns it into the shared words on / worked / lastTs / owed - None is UNKNOWN, never
0) with the top growers by size and what waits on a salvage. Every filesystem and process touch is a parameter, so the
laws drive it on fixture trees in temp dirs and never on his disk. [[heart-first]] [[unknown-stays-unknown]]

CLI: python3 tv/disk_growers.py  -> measures and prints (ASCII); it never salvages or prunes.
"""
import fnmatch
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

KIND_GIT = "git-tree"
KIND_SCRATCH = "scratch"
DRY = "dry-run"
ARMED = "prune"

WATERMARK_GB = 16.0                  # the doctor's own line: under 16 GB is about two hours of recording
ARM_AFTER_PASSES = 3                 # clean dry passes before a dry-run entry arms itself
ARM_AFTER_H = 24                     # ... spanning at least this long
FILE_CAP = 2 * 1000 ** 2             # an untracked / informational file larger than this is named, not copied
SALVAGE_CAP = 20 * 1000 ** 2         # copied bytes per salvage
LOG_TAIL = 16 * 1024                 # a log is kept as its tail
BIGGEST_N = 20                       # files a scratch summary names
WALK_BUDGET_S = 30.0                 # per candidate; past it the size is "at least" and the age UNKNOWN
PASS_BUDGET_S = 300.0                # per pass; a candidate not reached is said, never guessed
GIT_TIMEOUT_S = 60
HOLDERS_TIMEOUT_S = 30
TOP_N = 5

_CLAUDE = ("claude-a[0-9]*", "claude-b[0-9]*", "claude-v[0-9]*", "claude-fx-*")
_GROK = ("grok-*",)
_GROK_SKIP = ("grok-file-lock-*",)   # the Grok CLI's own lock slots: live, never a grower
_KEEP = ("*.md", "*verdict*", "*.patch", "*.diff", "*.log", "*.txt", "*.jsonl")
_POSIX = ("darwin", "linux")
_WIN = ("win32",)

#: THE DECLARED REGISTRY. A new entry starts in DRY (see the module docstring); `why` is the measurement that put it here.
GROWERS = (
    {"name": "claude-trees", "platforms": _POSIX, "root": "TMP", "globs": _CLAUDE, "skip": (), "owner": "claude",
     "kind": KIND_GIT, "floorH": 24, "boundH": 168, "mode": DRY,
     "why": "Claude's fleet worktrees - seven shipped ones held 2.2 GB on 2026-11-05"},
    {"name": "claude-scratch", "platforms": _POSIX, "root": "TMP", "globs": _CLAUDE, "skip": (), "owner": "claude",
     "kind": KIND_SCRATCH, "floorH": 24, "boundH": 72, "mode": DRY, "keep": _KEEP,
     "why": "Claude's probe and leftover dirs that are not git trees"},
    {"name": "grok-trees", "platforms": _POSIX, "root": "TMP", "globs": _GROK, "skip": _GROK_SKIP, "owner": "grok",
     "kind": KIND_GIT, "floorH": 48, "boundH": 168, "mode": DRY,
     "why": "the Grok seat's leftover worktrees - ~3.3 GB on 2026-11-05, some not merged"},
    {"name": "grok-scratch", "platforms": _POSIX, "root": "TMP", "globs": _GROK, "skip": _GROK_SKIP, "owner": "grok",
     "kind": KIND_SCRATCH, "floorH": 48, "boundH": 72, "mode": DRY, "keep": _KEEP,
     "why": "the Grok seat's dirs that are not git trees"},
    {"name": "claude-trees-win", "platforms": _WIN, "root": "TEMP", "globs": _CLAUDE, "skip": (), "owner": "claude",
     "kind": KIND_GIT, "floorH": 24, "boundH": 168, "mode": DRY,
     "why": "the same seats on a Windows PC, whose scratch root is %TEMP%"},
    {"name": "claude-scratch-win", "platforms": _WIN, "root": "TEMP", "globs": _CLAUDE, "skip": (), "owner": "claude",
     "kind": KIND_SCRATCH, "floorH": 24, "boundH": 72, "mode": DRY, "keep": _KEEP,
     "why": "the same seats on a Windows PC, whose scratch root is %TEMP%"},
    {"name": "grok-trees-win", "platforms": _WIN, "root": "TEMP", "globs": _GROK, "skip": _GROK_SKIP, "owner": "grok",
     "kind": KIND_GIT, "floorH": 48, "boundH": 168, "mode": DRY,
     "why": "the same seats on a Windows PC, whose scratch root is %TEMP%"},
    {"name": "grok-scratch-win", "platforms": _WIN, "root": "TEMP", "globs": _GROK, "skip": _GROK_SKIP, "owner": "grok",
     "kind": KIND_SCRATCH, "floorH": 48, "boundH": 72, "mode": DRY, "keep": _KEEP,
     "why": "the same seats on a Windows PC, whose scratch root is %TEMP%"},
)

#: git's pointer variables: a console started from a hook would otherwise aim every git call at the hook's repo (REG-2360)
_GIT_POINTERS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_COMMON_DIR",
                 "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_NAMESPACE", "GIT_PREFIX")


def salvage_root(repo):
    """Where salvages go: TV_SALVAGE_DIR, else <repo>/tv/.salvage (git-ignored). -> path"""
    return os.environ.get("TV_SALVAGE_DIR") or os.path.join(repo, "tv", ".salvage")


def roots(platform=None, env=None):
    """The root tokens on this platform. -> {token: path}; a token whose folder is not set is absent."""
    platform = platform or sys.platform
    env = os.environ if env is None else env
    if platform.startswith("win"):
        t = env.get("TEMP") or env.get("TMP")
        return {"TEMP": t} if t else {}
    return {"TMP": "/private/tmp" if platform == "darwin" else "/tmp"}


def entries_for(platform=None, growers=None):
    """The registry entries that apply on this platform. -> [entry]"""
    platform = platform or sys.platform
    return [e for e in (GROWERS if growers is None else growers)
            if any(platform.startswith(p) for p in e["platforms"])]


def _real(p):
    return os.path.realpath(os.path.abspath(p))


def _inside(child, parent):
    """child is parent or under it (both real paths). -> bool"""
    return child == parent or child.startswith(parent.rstrip(os.sep) + os.sep)


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


# ── measure ─────────────────────────────────────────────────────────────────────────────────────────────────────────

def walk(path, budget_s=WALK_BUDGET_S, _now=time.time, collect=False):
    """Bytes, newest write, file list under `path`, never following a link. -> dict
    {bytes, newest, files, links, complete, nestedGit, list}. complete False: the budget ran out (bytes are AT LEAST,
    the newest write is unknown)."""
    t_end = _now() + float(budget_s)
    out = {"bytes": 0, "newest": None, "files": 0, "links": 0, "complete": True, "nestedGit": False, "list": []}
    try:
        newest = os.lstat(path).st_mtime
    except OSError:
        out.update(complete=False)
        return out
    stack = [path]
    while stack:
        if _now() > t_end:
            out["complete"] = False
            break
        d = stack.pop()
        try:
            with os.scandir(d) as it:
                for e in it:
                    try:
                        st = e.stat(follow_symlinks=False)
                    except OSError:
                        continue
                    newest = max(newest, st.st_mtime)
                    if e.is_symlink():
                        out["links"] += 1
                        continue
                    if e.is_dir(follow_symlinks=False):
                        if e.name == ".git" and d != path:
                            out["nestedGit"] = True
                        stack.append(e.path)
                        continue
                    if e.name == ".git" and d != path:
                        out["nestedGit"] = True
                    out["files"] += 1
                    out["bytes"] += st.st_size
                    if collect:
                        out["list"].append((os.path.relpath(e.path, path), st.st_size, st.st_mtime))
        except OSError:
            continue
    out["newest"] = newest if out["complete"] else None
    return out


def holders(platform=None, _run=None):
    """Every path a live process holds as its cwd or an open file. -> (set of real paths | None, why)
    None is UNKNOWN, and then NOTHING is pruned. POSIX: lsof over every process this user can see. Windows: psutil when
    it is installed, else UNKNOWN (there is no lsof there)."""
    platform = platform or sys.platform
    if platform.startswith("win"):
        try:
            import psutil  # optional
        except Exception:
            return None, "there is no lsof on Windows and psutil is not installed, so what holds a folder cannot be read"
        held, denied = set(), 0
        for p in psutil.process_iter():
            try:
                held.add(_real(p.cwd()))
                for f in p.open_files():
                    held.add(_real(f.path))
            except Exception:
                denied += 1
        return held, "psutil read %d path(s); %d process(es) would not answer" % (len(held), denied)
    run = _run or subprocess.run
    try:
        r = run(["lsof", "-n", "-P", "-w", "-F", "pn"], capture_output=True, timeout=HOLDERS_TIMEOUT_S)
    except Exception as e:
        return None, "lsof could not be asked (%s)" % type(e).__name__
    out = r.stdout.decode("utf-8", "replace") if isinstance(r.stdout, bytes) else str(r.stdout or "")
    procs = sum(1 for ln in out.splitlines() if ln.startswith("p"))
    if not procs:
        return None, "lsof named no process (exit %s), so what holds a folder is UNKNOWN" % getattr(r, "returncode", "?")
    held = {ln[1:] for ln in out.splitlines() if ln.startswith("n/")}
    return held, "lsof read %d process(es)" % procs


def _held_by(held, *paths):
    """Does any held path sit at or under one of `paths` (its real and its spelled form)? -> bool"""
    return any(_inside(h, p) for h in held for p in paths if p)


# ── git ─────────────────────────────────────────────────────────────────────────────────────────────────────────────

def _git_env():
    return {k: v for k, v in os.environ.items() if k not in _GIT_POINTERS}


def git(path, args, timeout=GIT_TIMEOUT_S):
    """One git call in `path`, through the ONE door (git_quiet), with git's pointer variables scrubbed.
    -> (returncode, stdout bytes, stderr text); (None, b"", why) when git could not run."""
    try:
        import git_quiet as _gq
        r = _gq.run(["git", "-C", path] + list(args), capture_output=True, timeout=timeout, env=_git_env())
    except Exception as e:
        return None, b"", "%s: %s" % (type(e).__name__, str(e)[:120])
    return r.returncode, r.stdout or b"", (r.stderr or b"").decode("utf-8", "replace")


def _line(path, args):
    rc, out, _err = git(path, args)
    if rc != 0:
        return None
    s = out.decode("utf-8", "replace").strip()
    return s or None


def git_facts(path):
    """What a git tree at `path` holds that is not upstream. -> dict (why set when it cannot be told)."""
    real = _real(path)
    f = {"top": None, "gitdir": None, "common": None, "linked": None, "head": None, "branch": None, "upstream": None,
         "plus": [], "dirty": b"", "untracked": [], "stashes": [], "running": None, "locked": False,
         "mainOf": 0, "finished": None, "why": None}
    top = _line(path, ["rev-parse", "--show-toplevel"])
    if top is None or _real(top) != real:
        f["why"] = "not the top of a git tree"
        return f
    f["top"] = real
    gd = _line(path, ["rev-parse", "--absolute-git-dir"])
    cd = _line(path, ["rev-parse", "--git-common-dir"])
    if gd is None or cd is None:
        f["why"] = "its git folder could not be read"
        return f
    f["gitdir"] = _real(gd)
    f["common"] = _real(cd if os.path.isabs(cd) else os.path.join(path, cd))
    f["linked"] = f["gitdir"] != f["common"]
    for lock in ("index.lock", "HEAD.lock"):
        if os.path.exists(os.path.join(f["gitdir"], lock)):
            f["running"] = lock
    f["locked"] = bool(f["linked"] and os.path.exists(os.path.join(f["gitdir"], "locked")))
    if not f["linked"]:
        wt = os.path.join(f["common"], "worktrees")
        try:
            f["mainOf"] = len([n for n in os.listdir(wt) if os.path.isdir(os.path.join(wt, n))])
        except OSError:
            f["mainOf"] = 0
    f["head"] = _line(path, ["rev-parse", "--verify", "-q", "HEAD"])
    f["branch"] = _line(path, ["symbolic-ref", "-q", "--short", "HEAD"])
    f["upstream"] = _line(path, ["rev-parse", "--verify", "-q", "origin/main"])
    if f["head"] is None:
        f["why"] = "it has no commit (HEAD does not resolve)"
        return f
    if f["upstream"] is None:
        f["why"] = "origin/main does not resolve here, so what is upstream cannot be told"
        return f
    refs = ["HEAD"]
    if not f["linked"]:
        heads = _line(path, ["for-each-ref", "--format=%(refname)", "refs/heads"])
        refs += (heads or "").split()
    plus = []
    for ref in refs:
        rc, out, err = git(path, ["cherry", "origin/main", ref])
        if rc != 0:
            f["why"] = "git cherry could not compare %s with origin/main (%s)" % (ref, err.strip()[:80])
            return f
        for ln in out.decode("utf-8", "replace").splitlines():
            if ln.startswith("+ "):
                sha = ln[2:].strip()
                if sha not in plus:
                    plus.append(sha)
    f["plus"] = plus
    rc, dirty, err = git(path, ["diff", "HEAD", "--binary"])
    if rc != 0:
        f["why"] = "the tracked diff could not be read (%s)" % err.strip()[:80]
        return f
    f["dirty"] = dirty
    rc, out, err = git(path, ["ls-files", "--others", "--exclude-standard", "-z"])
    if rc != 0:
        f["why"] = "the untracked files could not be listed (%s)" % err.strip()[:80]
        return f
    f["untracked"] = [n for n in out.decode("utf-8", "replace").split("\0") if n]
    if not f["linked"]:
        st = _line(path, ["stash", "list", "--format=%H"])
        f["stashes"] = (st or "").split()
    f["finished"] = not (f["plus"] or f["dirty"] or f["untracked"] or f["stashes"])
    return f


# ── extract + verify ────────────────────────────────────────────────────────────────────────────────────────────────

def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _safe_rel(name):
    n = os.path.normpath(name)
    return None if (os.path.isabs(n) or n.startswith("..") or n in (".", "")) else n


def _git_payload(path, facts):
    """The informational files of a git tree. -> (files [(rel, bytes)], notSaved [{path, bytes, why}], why | None)"""
    files, not_saved, total = [], [], 0
    for i, sha in enumerate(facts["plus"]):
        rc, out, err = git(path, ["format-patch", "-1", "--stdout", "--binary", sha])
        if rc != 0 or not out:
            rc, out, err = git(path, ["show", "--binary", "--first-parent", "--format=fuller", sha])
        if rc != 0 or not out:
            return files, not_saved, "commit %s could not be written as a patch (%s)" % (sha[:12], err.strip()[:80])
        files.append(("patches/%04d-%s.patch" % (i + 1, sha[:12]), out))
    if facts["dirty"]:
        files.append(("dirty.diff", facts["dirty"]))
    for j, s in enumerate(facts["stashes"]):
        rc, out, err = git(path, ["diff", "--binary", s + "^1", s])
        if rc != 0:
            return files, not_saved, "stash %s could not be read (%s)" % (s[:12], err.strip()[:80])
        files.append(("stash/%02d-%s.diff" % (j, s[:12]), out))
    for name in facts["untracked"]:
        rel = _safe_rel(name)
        full = os.path.join(path, name)
        try:
            st = os.lstat(full)
        except OSError:
            not_saved.append({"path": name, "bytes": None, "why": "gone before it could be read"})
            continue
        if rel is None:
            not_saved.append({"path": name, "bytes": st.st_size, "why": "a name outside the tree"})
        elif os.path.islink(full):
            not_saved.append({"path": name, "bytes": st.st_size, "why": "a link (to %s)" % os.readlink(full)[:120]})
        elif st.st_size > FILE_CAP or total + st.st_size > SALVAGE_CAP:
            not_saved.append({"path": name, "bytes": st.st_size, "why": "over the size cap"})
        else:
            with open(full, "rb") as fh:
                data = fh.read()
            total += len(data)
            files.append(("untracked/" + rel, data))
    return files, not_saved, None


def _scratch_payload(path, entry, w):
    """A scratch dir's informational files: its summary, and the entry's declared files under the cap. -> as above"""
    lst = w.get("list") or []
    biggest = sorted(lst, key=lambda t: -t[1])[:BIGGEST_N]
    summary = {"path": path, "files": w["files"], "bytes": w["bytes"], "links": w["links"], "newest": w["newest"],
               "biggest": [{"path": r, "bytes": b} for r, b, _m in biggest]}
    files = [("summary.json", json.dumps(summary, indent=1, sort_keys=True).encode("utf-8"))]
    not_saved, total = [], 0
    keep = entry.get("keep") or ()
    for rel, size, _m in sorted(lst):
        base = os.path.basename(rel)
        if not any(fnmatch.fnmatch(base, g) for g in keep):
            continue
        full = os.path.join(path, rel)
        is_log = base.endswith(".log")
        take = min(size, LOG_TAIL) if is_log else size
        if (not is_log and size > FILE_CAP) or total + take > SALVAGE_CAP:
            not_saved.append({"path": rel, "bytes": size, "why": "over the size cap"})
            continue
        try:
            with open(full, "rb") as fh:
                if is_log and size > LOG_TAIL:
                    fh.seek(size - LOG_TAIL)
                data = fh.read(take)
        except OSError:
            not_saved.append({"path": rel, "bytes": size, "why": "could not be read"})
            continue
        total += len(data)
        files.append(("kept/" + rel + (".tail" if is_log and size > LOG_TAIL else ""), data))
    return files, not_saved, None


def _readme(meta):
    lines = ["Salvaged by the disk growers lane (REG-3209) before %s was pruned." % meta["path"],
             "entry %s, owner %s, kind %s." % (meta["entry"], meta["owner"], meta["kind"])]
    if meta["kind"] == KIND_GIT:
        lines += ["HEAD %s on %s." % (meta.get("head"), meta.get("branch") or "a detached HEAD"),
                  "patches/  every commit not upstream by patch-id (git cherry origin/main) - restore with git am",
                  "dirty.diff  the tracked changes against HEAD - restore with git apply --binary",
                  "untracked/  untracked, not ignored files under the size cap; notSaved in meta.json names the rest"]
    else:
        lines += ["summary.json  what the folder held; kept/ the declared informational files (logs as their tail)"]
    return ("\n".join(lines) + "\n").encode("utf-8")


def _write(path, data):
    tmp = path + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(data)
    os.replace(tmp, path)


def verify(dest, meta=None):
    """Read a salvage back. -> (True, None) | (False, why). Every file meta.json lists must read back to its sha256 and
    size, and meta.json itself must parse (and equal `meta` when one is handed in)."""
    try:
        with open(os.path.join(dest, "meta.json"), "rb") as fh:
            got = json.loads(fh.read().decode("utf-8"))
    except Exception as e:
        return False, "meta.json did not read back (%s)" % type(e).__name__
    if meta is not None and got != meta:
        return False, "meta.json read back different from what was written"
    for rel, rec in sorted((got.get("files") or {}).items()):
        try:
            with open(os.path.join(dest, rel), "rb") as fh:
                b = fh.read()
        except Exception as e:
            return False, "%s did not read back (%s)" % (rel, type(e).__name__)
        if len(b) != rec.get("bytes") or _sha(b) != rec.get("sha256"):
            return False, "%s read back different from what was written" % rel
    return True, None


def _manifest_has(manifest, rel_dir, fp):
    try:
        with open(manifest, "rb") as fh:
            for ln in fh.read().decode("utf-8", "replace").splitlines():
                try:
                    r = json.loads(ln)
                except ValueError:
                    continue
                if r.get("event") == "salvage" and r.get("dir") == rel_dir and r.get("fingerprint") == fp:
                    return True
    except OSError:
        return False
    return False


def _fingerprint(c, facts, w):
    if c["kind"] == KIND_GIT:
        un = []
        for n in facts["untracked"]:
            try:
                st = os.lstat(os.path.join(c["path"], n))
                un.append([n, st.st_size, int(st.st_mtime)])
            except OSError:
                un.append([n, None, None])
        parts = [facts["head"], facts["plus"], _sha(facts["dirty"]), un, facts["stashes"]]
    else:
        parts = [w["bytes"], w["files"], w["newest"]]
    return _sha(json.dumps([c["kind"]] + parts, sort_keys=True, default=str).encode("utf-8"))


def salvage(c, facts, w, sroot, now_s):
    """Extract what is informational in candidate `c`, write it under the salvage root, read it back, and append one
    manifest line. -> {ok, dir, fingerprint, files, bytes, notSaved, reused, why}. ok False BLOCKS the prune."""
    entry = c["entry"]
    fp = _fingerprint(c, facts, w)
    rel_dir = os.path.join(entry["name"], "%s-%s" % (os.path.basename(c["path"]), fp[:12]))
    dest = os.path.join(sroot, rel_dir)
    manifest = os.path.join(sroot, "manifest.jsonl")
    res = {"ok": False, "dir": rel_dir, "fingerprint": fp, "files": 0, "bytes": 0, "notSaved": [], "reused": False,
           "why": None}
    try:
        if os.path.isdir(dest):
            ok, why = verify(dest)
            if ok and _manifest_has(manifest, rel_dir, fp):
                with open(os.path.join(dest, "meta.json"), "rb") as fh:
                    m = json.loads(fh.read().decode("utf-8"))
                res.update(ok=True, reused=True, files=len(m.get("files") or {}),
                           bytes=sum(int(r.get("bytes") or 0) for r in (m.get("files") or {}).values()),
                           notSaved=m.get("notSaved") or [])
                return res
        if c["kind"] == KIND_GIT:
            files, not_saved, why = _git_payload(c["path"], facts)
        else:
            files, not_saved, why = _scratch_payload(c["path"], entry, w)
        if why:
            res["why"] = why
            return res
        meta = {"entry": entry["name"], "owner": entry["owner"], "kind": c["kind"], "path": c["path"],
                "fingerprint": fp, "ts": int(now_s), "measuredBytes": w["bytes"], "newest": w["newest"],
                "head": facts.get("head") if facts else None, "branch": facts.get("branch") if facts else None,
                "notSaved": not_saved, "files": {}}
        files = list(files) + [("README.txt", None)]
        os.makedirs(dest, exist_ok=True)
        for rel, data in files:
            if data is None:
                data = _readme(meta)
            full = os.path.join(dest, rel)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            _write(full, data)
            meta["files"][rel] = {"bytes": len(data), "sha256": _sha(data)}
        _write(os.path.join(dest, "meta.json"), json.dumps(meta, indent=1, sort_keys=True).encode("utf-8"))
        ok, why = verify(dest, meta)
        if not ok:
            res["why"] = why
            return res
        line = {"ts": int(now_s), "event": "salvage", "entry": entry["name"], "owner": entry["owner"],
                "path": c["path"], "dir": rel_dir, "fingerprint": fp, "files": len(meta["files"]),
                "bytes": sum(r["bytes"] for r in meta["files"].values()), "notSaved": len(not_saved)}
        with open(manifest, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(line, sort_keys=True) + "\n")
        if not _manifest_has(manifest, rel_dir, fp):
            res["why"] = "the manifest line did not read back"
            return res
        res.update(ok=True, files=line["files"], bytes=line["bytes"], notSaved=not_saved)
        return res
    except Exception as e:
        res["why"] = "the salvage raised %s: %s" % (type(e).__name__, str(e)[:100])
        return res


# ── prune ───────────────────────────────────────────────────────────────────────────────────────────────────────────

def _main_tree(path):
    rc, out, _err = git(path, ["worktree", "list", "--porcelain"])
    if rc != 0:
        return None
    for ln in out.decode("utf-8", "replace").splitlines():
        if ln.startswith("worktree "):
            return ln[len("worktree "):]
    return None


def _listed(main, path_real):
    rc, out, _err = git(main, ["worktree", "list", "--porcelain"])
    if rc != 0:
        return None
    return any(_real(ln[len("worktree "):]) == path_real
               for ln in out.decode("utf-8", "replace").splitlines() if ln.startswith("worktree "))


def stale_worktrees(repo):
    """The repo's worktree entries whose folder is gone (someone removed the folder, not the worktree), which keep the
    worktree list untrue. Said, never acted on: `git worktree prune` clears them. -> (n | None, [names])"""
    rc, out, _err = git(repo, ["worktree", "list", "--porcelain"])
    if rc != 0:
        return None, []
    names, cur = [], None
    for ln in out.decode("utf-8", "replace").splitlines():
        if ln.startswith("worktree "):
            cur = ln[len("worktree "):]
        elif ln.startswith("prunable") and cur:
            names.append(os.path.basename(cur))
    return len(names), names


def prune(c, facts):
    """Remove one candidate. -> (True, None) | (False, why). A linked worktree goes through `git worktree remove
    --force` from its main tree, so the repo's worktree list stays true; anything else through shutil.rmtree, which
    unlinks a link and never follows it."""
    path = c["path"]
    if os.path.islink(path):
        return False, "it is a link"
    if c["kind"] == KIND_GIT and facts and facts.get("linked"):
        main = _main_tree(path)
        if not main:
            return False, "its main tree could not be found, so the worktree list could not be kept true"
        rc, _out, err = git(main, ["worktree", "remove", "--force", path])
        if rc != 0:
            return False, "git worktree remove refused (%s)" % err.strip()[:120]
        if os.path.exists(path):
            return False, "git worktree remove left the folder"
        if _listed(main, c["real"]):
            return False, "the folder is gone and the worktree list still names it"
        return True, None
    try:
        shutil.rmtree(path)
    except Exception as e:
        return False, "the remove raised %s: %s" % (type(e).__name__, str(e)[:100])
    return (not os.path.exists(path)), (None if not os.path.exists(path) else "the folder is still there")


# ── state (graduation, lifetime counters) ───────────────────────────────────────────────────────────────────────────

def load_state(path):
    """-> (state, why). A missing file is a fresh state; a corrupt one is moved aside and said, never overwritten."""
    fresh = {"entries": {}, "passes": 0, "worked": 0, "freedBytes": 0, "lastTs": None}
    if not os.path.exists(path):
        return fresh, None
    try:
        with open(path, "rb") as fh:
            st = json.loads(fh.read().decode("utf-8"))
        if not isinstance(st, dict) or not isinstance(st.get("entries"), dict):
            raise ValueError("not a state")
        for k, v in fresh.items():
            st.setdefault(k, v)
        return st, None
    except Exception as e:
        aside = "%s.corrupt-%d" % (path, int(time.time()))
        try:
            os.replace(path, aside)
        except OSError:
            pass
        return fresh, "the growers state did not read (%s) - moved aside, every entry is back in dry-run" % type(e).__name__


def effective_mode(entry, est):
    if entry.get("mode") == ARMED:
        return ARMED
    return ARMED if (est or {}).get("armedTs") else DRY


def _graduate(entry, est, outcome, now_s):
    """One dry pass's evidence for a dry-run entry. outcome: None (nothing to prove) | "clean" | "failed"."""
    if entry.get("mode") == ARMED or est.get("armedTs") or outcome is None:
        return
    if outcome == "failed":
        est.update(cleanPasses=0, firstCleanTs=None)
        return
    est["cleanPasses"] = int(est.get("cleanPasses") or 0) + 1
    est["firstCleanTs"] = est.get("firstCleanTs") or now_s
    if est["cleanPasses"] >= ARM_AFTER_PASSES and now_s - est["firstCleanTs"] >= ARM_AFTER_H * 3600:
        est["armedTs"] = now_s


# ── the pass ────────────────────────────────────────────────────────────────────────────────────────────────────────

def find(entries, root_map):
    """Every folder an entry's globs name directly under its root. -> {real path: {path, real, entries}}"""
    found = {}
    for e in entries:
        root = root_map.get(e["root"])
        if not root or not os.path.isdir(root):
            continue
        try:
            names = sorted(os.listdir(root))
        except OSError:
            continue
        for n in names:
            if not any(fnmatch.fnmatch(n, g) for g in e["globs"]) or any(fnmatch.fnmatch(n, s) for s in e.get("skip", ())):
                continue
            p = os.path.join(root, n)
            if os.path.islink(p) or not os.path.isdir(p):
                continue
            row = found.setdefault(_real(p), {"path": p, "real": _real(p), "root": root, "entries": []})
            row["entries"].append(e)
    return found


def run(entries=None, root_map=None, salvage_dir=None, protect=(), free_bytes=None, now_s=None, platform=None,
        held=None, measure_only=False, watermark_gb=None, budget_s=PASS_BUDGET_S, _now=time.time, repo=None):
    """One pass: measure -> extract -> verify -> prune. Never raises. -> the pass record.

    free_bytes: a callable(path) -> bytes (raising = UNKNOWN), or None (UNKNOWN). held: (set | None, why) to use instead
    of asking the machine. measure_only: no salvage, no prune, no state written (the CLI). repo: the console's repo,
    whose worktree entries that name a folder that is gone are counted and said."""
    now_s = _now() if now_s is None else now_s
    t0 = _now()
    rec = {"ts": int(now_s * 1000), "candidates": [], "removed": [], "waiting": [], "wouldPrune": [], "freed": 0,
           "growers": [], "held": None, "free": None, "watermark": None, "stateWhy": None, "error": None,
           "salvaged": 0, "owed": None, "say": None, "worked": None, "freedBytes": None, "dryRun": [],
           "salvageRoot": salvage_dir, "lastSalvage": None, "biggest": [],
           "salvageBytes": None, "salvageAtLeast": False, "staleWorktrees": None, "staleNames": []}
    try:
        _pass(rec, entries, root_map, salvage_dir, protect, free_bytes, now_s, platform, held, measure_only,
              watermark_gb, budget_s, t0, _now, repo)
    except Exception as e:
        rec.update(error="%s: %s" % (type(e).__name__, str(e)[:160]), owed=None,
                   say="the growers pass raised %s - nothing more was pruned" % type(e).__name__)
    return rec


def _pass(rec, entries, root_map, sroot, protect, free_bytes, now_s, platform, held, measure_only, watermark_gb,
          budget_s, t0, _now, repo=None):
    platform = platform or sys.platform
    entries = entries_for(platform) if entries is None else entries
    root_map = roots(platform) if root_map is None else root_map
    wm = float(WATERMARK_GB if watermark_gb is None else watermark_gb) * 1e9
    rec["watermark"] = wm
    guard = [_real(p) for p in tuple(protect) + ((sroot,) if sroot else ()) if p]
    state_path = os.path.join(sroot, "state.json") if sroot else None
    state, rec["stateWhy"] = load_state(state_path) if state_path else ({"entries": {}}, "no salvage dir")
    hs, hwhy = held if held is not None else holders(platform)
    rec["held"] = hwhy if hs is not None else ("UNKNOWN - " + hwhy)
    found = find(entries, root_map)
    free_by_root = {}
    per_entry = {e["name"]: {"name": e["name"], "owner": e["owner"], "kind": e["kind"], "n": 0, "bytes": 0,
                             "atLeast": False, "mode": effective_mode(e, state["entries"].get(e["name"]))}
                 for e in entries}
    rows = []
    for real, row in sorted(found.items()):
        c = {"path": row["path"], "real": real, "name": os.path.basename(row["path"]), "entry": None, "kind": None,
             "bytes": None, "atLeast": False, "ageH": None, "finished": None, "state": None, "why": None}
        rows.append(c)
        if _now() - t0 > budget_s:
            c.update(state="unknown", why="the pass ran out of its %d s before reaching it" % budget_s)
            continue
        if any(_inside(real, g) or _inside(g, real) for g in guard):
            c.update(state="protected", why="it is (or holds) the console's tree, its footage or the salvage dir")
            continue
        is_git = os.path.lexists(os.path.join(row["path"], ".git"))
        c["kind"] = KIND_GIT if is_git else KIND_SCRATCH
        ent = next((e for e in row["entries"] if e["kind"] == c["kind"]), None)
        if ent is None:
            c.update(state="unclaimed", why="a %s, and no entry for its name declares that kind" % c["kind"])
            continue
        c["entry"] = ent
        c["owner"] = ent["owner"]
        w = walk(row["path"], budget_s=WALK_BUDGET_S, collect=(c["kind"] == KIND_SCRATCH))
        c.update(bytes=w["bytes"], atLeast=not w["complete"])
        pe = per_entry[ent["name"]]
        pe["n"] += 1
        pe["bytes"] += w["bytes"]
        pe["atLeast"] = pe["atLeast"] or not w["complete"]
        facts = None
        newest = w["newest"]
        if c["kind"] == KIND_GIT:
            facts = git_facts(row["path"])
            if facts.get("gitdir"):
                for nm in ("index", "HEAD", "logs/HEAD"):
                    try:
                        newest = max(newest, os.stat(os.path.join(facts["gitdir"], nm)).st_mtime) if newest else newest
                    except OSError:
                        pass
        elif w["nestedGit"]:
            c.update(state="unclaimed", why="it holds a git repository inside, which a scratch entry does not understand")
            continue
        if newest is None:
            c.update(state="unknown", why="its walk did not finish in %d s, so its age is UNKNOWN" % WALK_BUDGET_S)
            continue
        age_h = max(0.0, (now_s - newest) / 3600.0)
        c["ageH"] = round(age_h, 1)
        if age_h < ent["floorH"]:
            c.update(state="young", why="written %.1f h ago, inside its %d h floor" % (age_h, ent["floorH"]))
            continue
        if hs is None:
            c.update(state="unknown", why="what holds it cannot be read (%s)" % hwhy)
            continue
        if _held_by(hs, real, os.path.abspath(row["path"])):
            c.update(state="held", why="a live process holds it (its cwd or an open file)")
            continue
        if facts is not None:
            if facts.get("why") and facts.get("top") is None:
                c.update(state="unclaimed", why=facts["why"])
                continue
            if facts.get("running"):
                c.update(state="held", why="a git is running in it (%s)" % facts["running"])
                continue
            if facts.get("locked"):
                c.update(state="held", why="the worktree is locked")
                continue
            if facts.get("mainOf"):
                c.update(state="protected", why="it is the main tree of %d linked worktree(s)" % facts["mainOf"])
                continue
            c["finished"] = facts.get("finished")
        else:
            c["finished"] = True
        c["_facts"], c["_walk"], c["_root"] = facts, w, row["root"]
        root = row["root"]
        if root not in free_by_root:
            try:
                free_by_root[root] = None if free_bytes is None else float(free_bytes(root))
            except Exception:
                free_by_root[root] = None
        c["_free"] = free_by_root[root]
        c["_bound"] = age_h >= ent["boundH"]
        c["state"] = "due?"
    frees = [v for v in free_by_root.values() if _num(v)]
    rec["free"] = min(frees) if frees else None
    # which of the past-floor candidates are DUE: past the bound always; under the watermark oldest first, until the
    # disk would be back over it
    due, freed_est = [], {}
    for c in sorted([c for c in rows if c["state"] == "due?"], key=lambda c: -(c["ageH"] or 0)):
        f = c["_free"]
        if c["_bound"]:
            due.append(c)
        elif _num(f) and f + freed_est.get(c["_root"], 0) < wm:
            due.append(c)
        elif f is None:
            c.update(state="kept", why="free space could not be read, and it is inside its %d h bound"
                     % c["entry"]["boundH"])
            continue
        else:
            c.update(state="kept", why="the disk is over its %.0f GB watermark, and it is inside its %d h bound"
                     % (wm / 1e9, c["entry"]["boundH"]))
            continue
        freed_est[c["_root"]] = freed_est.get(c["_root"], 0) + (c["bytes"] or 0)
    outcome = {}
    fresh = [None]                       # holders asked again just before the first prune of this pass
    for c in due:
        ent = c["entry"]
        mode = per_entry[ent["name"]]["mode"]
        trig = "past its %d h bound" % ent["boundH"] if c["_bound"] else "the disk is under its %.0f GB watermark" % (wm / 1e9)
        if measure_only:
            c.update(state="due", why="%s - measured only, nothing salvaged or pruned" % trig)
            continue
        if not sroot:
            c.update(state="waiting", why="no salvage dir, so nothing may be pruned")
            rec["waiting"].append({"name": c["name"], "entry": ent["name"], "why": c["why"]})
            continue
        if c["_facts"] is not None and c["_facts"].get("why"):
            # REG-3209 - a tree whose unmerged work cannot be READ cannot be salvaged, so it is never pruned
            c.update(state="waiting", why="its salvage cannot be made: %s" % c["_facts"]["why"])
            rec["waiting"].append({"name": c["name"], "entry": ent["name"], "why": c["_facts"]["why"]})
            outcome[ent["name"]] = "failed"
            continue
        s = salvage(c, c["_facts"], c["_walk"], sroot, now_s)
        c["salvage"] = {k: s[k] for k in ("ok", "dir", "files", "bytes", "reused", "why")}
        c["salvage"]["notSaved"] = len(s["notSaved"])
        if not s["ok"]:
            c.update(state="waiting", why="its salvage did not read back (%s) - it is not pruned" % s["why"])
            rec["waiting"].append({"name": c["name"], "entry": ent["name"], "why": s["why"]})
            outcome[ent["name"]] = "failed"
            continue
        if not s["reused"]:
            rec["salvaged"] += 1
        rec["lastSalvage"] = s["dir"]
        if outcome.get(ent["name"]) != "failed":
            outcome[ent["name"]] = "clean"
        if mode != ARMED:
            c.update(state="would-prune", why="%s; salvaged to %s and read back - dry-run, so it stays" % (trig, s["dir"]))
            rec["wouldPrune"].append({"name": c["name"], "entry": ent["name"], "bytes": c["bytes"]})
            continue
        if fresh[0] is None:
            fresh[0] = held if held is not None else holders(platform)
        if fresh[0][0] is None or _held_by(fresh[0][0], c["real"], os.path.abspath(c["path"])):
            c.update(state="held", why="salvaged to %s; a live process holds it now (or holders could not be read), "
                                       "so it stays" % s["dir"])
            continue
        ok, why = prune(c, c["_facts"])
        if not ok:
            c.update(state="failed", why="salvaged to %s, and the prune failed: %s" % (s["dir"], why))
            rec["waiting"].append({"name": c["name"], "entry": ent["name"], "why": why})
            continue
        c.update(state="pruned", why="%s; salvaged to %s first" % (trig, s["dir"]))
        rec["removed"].append({"name": c["name"], "entry": ent["name"], "bytes": c["bytes"], "salvage": s["dir"],
                               "finished": c["finished"]})
        rec["freed"] += int(c["bytes"] or 0)
        try:
            with open(os.path.join(sroot, "manifest.jsonl"), "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"ts": int(now_s), "event": "prune", "entry": ent["name"], "path": c["path"],
                                     "bytes": c["bytes"], "salvage": s["dir"], "finished": c["finished"]},
                                    sort_keys=True) + "\n")
        except OSError:
            pass
    for c in rows:
        for k in ("_facts", "_walk", "_free", "_bound", "_root"):
            c.pop(k, None)
        if c.get("entry"):
            c["entry"] = c["entry"]["name"]
    rec["candidates"] = rows
    rec["growers"] = sorted(per_entry.values(), key=lambda g: -g["bytes"])
    rec["biggest"] = [{"name": c["name"], "entry": c["entry"], "owner": c.get("owner"), "bytes": c["bytes"],
                       "atLeast": c["atLeast"], "state": c["state"]}
                      for c in sorted([c for c in rows if _num(c["bytes"])], key=lambda c: -c["bytes"])[:TOP_N]]
    if not measure_only and state_path:
        for e in entries:
            est = state["entries"].setdefault(e["name"], {})
            if per_entry[e["name"]]["mode"] != ARMED:
                _graduate(e, est, outcome.get(e["name"]), now_s)
        state["passes"] = int(state.get("passes") or 0) + 1
        if rec["removed"] or rec["salvaged"]:
            state["worked"] = int(state.get("worked") or 0) + 1
        state["freedBytes"] = int(state.get("freedBytes") or 0) + rec["freed"]
        state["lastTs"] = int(now_s)
        try:
            os.makedirs(sroot, exist_ok=True)
            _write(state_path, json.dumps(state, indent=1, sort_keys=True).encode("utf-8"))
            rec["worked"], rec["freedBytes"] = state["worked"], state["freedBytes"]
        except OSError as e:
            rec["stateWhy"] = "the growers state could not be written (%s)" % type(e).__name__
    for e in entries:
        est = state["entries"].get(e["name"]) or {}
        if effective_mode(e, est) != ARMED:
            rec["dryRun"].append({"entry": e["name"], "clean": int(est.get("cleanPasses") or 0),
                                  "of": ARM_AFTER_PASSES, "since": est.get("firstCleanTs")})
    if sroot and os.path.isdir(sroot):
        # the salvage dir is never pruned by this lane, so it is MEASURED every pass and said: it grows too
        sw = walk(sroot, budget_s=10.0)
        rec["salvageBytes"], rec["salvageAtLeast"] = sw["bytes"], not sw["complete"]
    if repo:
        rec["staleWorktrees"], rec["staleNames"] = stale_worktrees(repo)
    unknown = sum(1 for c in rows if c["state"] == "unknown")
    rec["owed"] = None if hs is None else len(rec["waiting"]) + len(rec["wouldPrune"])
    rec["say"] = _say(rec, unknown)


def _gb(b):
    return "%.2f GB" % ((b or 0) / 1e9)


def _say(rec, unknown):
    top = [g for g in rec["growers"] if g["n"]][:TOP_N]
    tops = ", ".join("%s %s%s (%d)" % (g["name"], "at least " if g["atLeast"] else "", _gb(g["bytes"]), g["n"])
                     for g in top) or "nothing a declared entry names"
    parts = ["growers: " + tops]
    if rec["removed"]:
        parts.append("pruned %d after salvage, %s freed" % (len(rec["removed"]), _gb(rec["freed"])))
    if rec["wouldPrune"]:
        parts.append("%d would go (salvaged and read back; dry-run, so they stay)" % len(rec["wouldPrune"]))
    if rec["waiting"]:
        parts.append("%d WAIT on a salvage or a prune that did not finish: %s" % (
            len(rec["waiting"]), ", ".join("%s (%s)" % (w["name"], str(w["why"])[:60]) for w in rec["waiting"][:3])))
    if unknown:
        parts.append("%d UNKNOWN (age or holders could not be read)" % unknown)
    if rec["held"] and rec["held"].startswith("UNKNOWN"):
        parts.append("nothing may be pruned: " + rec["held"])
    if rec.get("staleWorktrees"):
        parts.append("%d worktree entr%s name a folder that is gone (%s) - git worktree prune clears them" % (
            rec["staleWorktrees"], "y" if rec["staleWorktrees"] == 1 else "ies", ", ".join(rec["staleNames"][:4])))
    if _num(rec.get("salvageBytes")):
        parts.append("the salvage dir holds %s%.1f MB (never pruned)" % (
            "at least " if rec.get("salvageAtLeast") else "", rec["salvageBytes"] / 1e6))
    return "; ".join(parts)


def lane(rec, checked_ms=None):
    """The pass record in the shared lane words. -> {on, worked, lastTs, owed, say, top, waiting, dryRun, ...}"""
    top = [{"name": g["name"], "owner": g["owner"], "gb": round(g["bytes"] / 1e9, 2), "n": g["n"],
            "atLeast": g["atLeast"], "mode": g["mode"]} for g in (rec.get("growers") or []) if g.get("n")][:TOP_N]
    return {"on": True, "worked": rec.get("worked"), "lastTs": rec.get("ts"), "checkedTs": checked_ms or rec.get("ts"),
            "owed": rec.get("owed"), "say": rec.get("say"), "top": top, "waiting": list(rec.get("waiting") or []),
            "wouldPrune": len(rec.get("wouldPrune") or []), "removed": len(rec.get("removed") or []),
            "freed": rec.get("freed"), "freedBytes": rec.get("freedBytes"), "dryRun": list(rec.get("dryRun") or []),
            "biggest": [{"name": b["name"], "owner": b.get("owner"), "gb": round((b["bytes"] or 0) / 1e9, 2),
                         "state": b["state"]} for b in (rec.get("biggest") or [])],
            "lastSalvage": rec.get("lastSalvage"), "error": rec.get("error"),
            "staleWorktrees": rec.get("staleWorktrees"),
            "salvageMb": (None if not _num(rec.get("salvageBytes")) else round(rec["salvageBytes"] / 1e6, 1)), "stateWhy": rec.get("stateWhy"),
            "freeGb": (None if not _num(rec.get("free")) else round(rec["free"] / 1e9, 1))}


def _ascii(text):
    return str(text).encode("ascii", "replace").decode("ascii")


def main(argv=None):
    """Measure only and print, in ASCII (a Windows console prints cp1255, and a path may not be ASCII)."""
    try:
        import disk_room as _dr
        free = lambda p: _dr.free_bytes(p)[0]
    except Exception:
        free = lambda p: shutil.disk_usage(p).free
    rec = run(salvage_dir=None, measure_only=True, free_bytes=free,
              repo=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    out = ["disk growers (measure only, nothing salvaged or pruned)", "holders: %s" % rec["held"]]
    for g in rec["growers"]:
        out.append("  %-20s %-7s %-8s %3d dir(s)  %s%s" % (g["name"], g["owner"], g["mode"], g["n"],
                                                           "at least " if g["atLeast"] else "", _gb(g["bytes"])))
    for c in rec["candidates"]:
        out.append("    %-28s %-12s %s" % (c["name"][:28], c["state"], str(c["why"] or "")[:110]))
    out.append(rec["say"] or "")
    for ln in out:
        print(_ascii(ln))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
