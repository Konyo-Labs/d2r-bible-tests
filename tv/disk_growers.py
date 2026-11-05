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
NEVER PRUNED: anything a live process holds (cwd or an open file) - lsof is asked again before EACH prune, after that
grower's own salvage - and NOTHING when holders cannot be read; a tree with a running git (index.lock / HEAD.lock) or a
locked worktree; the main tree of linked worktrees; his console's own tree and anything containing it; tv/frames and his
reels (reel retention owns them); the salvage dir itself; anything inside its age floor; anything whose age could not be
measured. AGE is the newest of every file's mtime AND ctime: a copy that keeps mtimes (cp -p, tar, unzip, rsync -a) is new.

A SALVAGE NEVER COSTS THE DISK MORE THAN IT IS MEANT TO RELIEVE (the REG-3208 review): every byte written counts against
SALVAGE_CAP - unmerged work past it is never cut short, the tree WAITS for a hand; a single diff whose touched files sum
past READ_CAP is not even read; nothing is written that would leave the salvage disk under SALVAGE_MIN_FREE, or the
salvage dir past SALVAGE_DIR_CAP. A merge commit (which git cherry skips) is salvaged as a bundle of the unmerged history.
A law fixture holds nothing informational: its salvage is one manifest RECORD line (what it was, how big), no folder.

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

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402 - it prints non-ASCII; a cp1255 console must not crash
_console_safe_enable()

KIND_GIT = "git-tree"
KIND_SCRATCH = "scratch"
DRY = "dry-run"
ARMED = "prune"

WATERMARK_GB = 16.0                  # the doctor's own line: under 16 GB is about two hours of recording
ARM_AFTER_PASSES = 3                 # clean dry passes before a dry-run entry arms itself
ARM_AFTER_H = 24                     # ... spanning at least this long
COPY = "copy"                        # salvage: a folder of the informational files, a meta.json and a README
RECORD = "record"                    # salvage: ONE manifest line (what it was, how big) - for a grower that holds nothing else

FILE_CAP = 2 * 1000 ** 2             # an untracked / informational file larger than this is named, not copied
SALVAGE_CAP = 20 * 1000 ** 2         # bytes WRITTEN per salvage; unmerged work past it is never cut short - the tree waits
READ_CAP = 200 * 1000 ** 2           # a single diff whose touched files sum past this is never read into memory at all
SALVAGE_MIN_FREE = 1000 ** 3         # a salvage never leaves the salvage disk with less than this free
SALVAGE_DIR_CAP = 2 * 1000 ** 3      # the salvage dir (never pruned) past this takes no new salvage, and says so
PRUNES_PER_PASS = 200                # growers handled per pass: each prune asks lsof again (0.27 s measured on his Mac)
RESET_SAY_H = 24                     # a growers state that was reset is said for this long after
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
#: REG-3208 review - law fixture dirs in the per-user temp dir. EACH prefix is one a tv/test_*.py law passes to mkdtemp
#: (grep-verified 2026-11-05), plus Playwright's own per-run artifact dirs. MEASURED in his $TMPDIR that night: vault-law-
#: 518, playwright-artifacts- 414, reg2271-iso- 77, tvd-nogit- 73, each left by a run that was killed. NOT declared, on
#: purpose: Chrome's own temp entries (a live Chrome uses them), tvd-child-guard- (one per checkout - his console's own
#: among them), tvd-* (the shadow reader's live profile is tvd-shadow-chrome) and tmp* (every program's default prefix).
_LAW = ("vault-law-*", "reg2271-iso-*", "tvd-nogit-*", "budget-law-*", "tvd-plainrun-*", "tvd-par-dirty-*",
        "g5-effort-law-*", "growers-law-*", "growers-doctor-*", "playwright-artifacts-*")
_POSIX = ("darwin", "linux")
_WIN = ("win32",)

#: THE DECLARED REGISTRY. A new entry starts in DRY (see the module docstring); `why` is the measurement that put it here.
GROWERS = (
    {"name": "claude-trees", "platforms": _POSIX, "root": "TMP", "globs": _CLAUDE, "skip": (), "owner": "claude",
     "kind": KIND_GIT, "floorH": 24, "boundH": 168, "mode": DRY, "salvage": COPY,
     "why": "Claude's fleet worktrees - seven shipped ones held 2.2 GB on 2026-11-05"},
    {"name": "claude-scratch", "platforms": _POSIX, "root": "TMP", "globs": _CLAUDE, "skip": (), "owner": "claude",
     "kind": KIND_SCRATCH, "floorH": 24, "boundH": 72, "mode": DRY, "keep": _KEEP, "salvage": COPY,
     "why": "Claude's probe and leftover dirs that are not git trees"},
    {"name": "grok-trees", "platforms": _POSIX, "root": "TMP", "globs": _GROK, "skip": _GROK_SKIP, "owner": "grok",
     "kind": KIND_GIT, "floorH": 48, "boundH": 168, "mode": DRY, "salvage": COPY,
     "why": "the Grok seat's leftover worktrees - ~3.3 GB on 2026-11-05, some not merged"},
    {"name": "grok-scratch", "platforms": _POSIX, "root": "TMP", "globs": _GROK, "skip": _GROK_SKIP, "owner": "grok",
     "kind": KIND_SCRATCH, "floorH": 48, "boundH": 72, "mode": DRY, "keep": _KEEP, "salvage": COPY,
     "why": "the Grok seat's dirs that are not git trees"},
    {"name": "claude-trees-win", "platforms": _WIN, "root": "TEMP", "globs": _CLAUDE, "skip": (), "owner": "claude",
     "kind": KIND_GIT, "floorH": 24, "boundH": 168, "mode": DRY, "salvage": COPY,
     "why": "the same seats on a Windows PC, whose scratch root is %TEMP%"},
    {"name": "claude-scratch-win", "platforms": _WIN, "root": "TEMP", "globs": _CLAUDE, "skip": (), "owner": "claude",
     "kind": KIND_SCRATCH, "floorH": 24, "boundH": 72, "mode": DRY, "keep": _KEEP, "salvage": COPY,
     "why": "the same seats on a Windows PC, whose scratch root is %TEMP%"},
    {"name": "grok-trees-win", "platforms": _WIN, "root": "TEMP", "globs": _GROK, "skip": _GROK_SKIP, "owner": "grok",
     "kind": KIND_GIT, "floorH": 48, "boundH": 168, "mode": DRY, "salvage": COPY,
     "why": "the same seats on a Windows PC, whose scratch root is %TEMP%"},
    {"name": "grok-scratch-win", "platforms": _WIN, "root": "TEMP", "globs": _GROK, "skip": _GROK_SKIP, "owner": "grok",
     "kind": KIND_SCRATCH, "floorH": 48, "boundH": 72, "mode": DRY, "keep": _KEEP, "salvage": COPY,
     "why": "the same seats on a Windows PC, whose scratch root is %TEMP%"},
    {"name": "law-scratch", "platforms": _POSIX, "root": "TMPDIR", "globs": _LAW, "skip": (), "owner": "laws",
     "kind": KIND_SCRATCH, "floorH": 24, "boundH": 72, "mode": DRY, "keep": (), "salvage": RECORD,
     "why": "law fixtures a killed run left in the per-user temp dir - 1,100+ of these prefixes on 2026-11-05"},
    {"name": "law-scratch-win", "platforms": _WIN, "root": "TEMP", "globs": _LAW, "skip": (), "owner": "laws",
     "kind": KIND_SCRATCH, "floorH": 24, "boundH": 72, "mode": DRY, "keep": (), "salvage": RECORD,
     "why": "the same law fixtures on a Windows PC, where tempfile writes to %TEMP%"},
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
    tmp = "/private/tmp" if platform == "darwin" else "/tmp"
    # REG-3208 review - the per-user temp dir, where tempfile, the laws and Playwright leave theirs ($TMPDIR on a Mac is
    # /var/folders/../T); unset, tempfile falls back to the shared temp root itself
    return {"TMP": tmp, "TMPDIR": (env.get("TMPDIR") or tmp).rstrip("/") or "/"}


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

def _stamp(st):
    """When a file was last written OR came to be where it is. -> epoch seconds. REG-3208 review: mtime alone read a folder
    made seconds ago by cp -Rp from a 10-day-old one as 240 h old, and an armed entry pruned it at once. A copy that keeps
    mtimes (cp -p, tar, unzip, rsync -a) cannot keep the ctime - setting a time is itself a change - so the newer of the
    two is the age. A metadata change (chmod, a rename) reads younger, which only keeps a grower longer."""
    return max(st.st_mtime, st.st_ctime)


def walk(path, budget_s=WALK_BUDGET_S, _now=time.time, collect=False):
    """Bytes, newest write, file list under `path`, never following a link. -> dict
    {bytes, newest, files, links, complete, nestedGit, list}. complete False: the budget ran out (bytes are AT LEAST,
    the newest write is unknown)."""
    t_end = _now() + float(budget_s)
    out = {"bytes": 0, "newest": None, "files": 0, "links": 0, "complete": True, "nestedGit": False, "list": []}
    try:
        newest = _stamp(os.lstat(path))
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
                    newest = max(newest, _stamp(st))
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


def git(path, args, timeout=GIT_TIMEOUT_S, input=None):
    """One git call in `path`, through the ONE door (git_quiet, which also sets GIT_OPTIONAL_LOCKS=0, so a read never
    rewrites a grower's index), with git's pointer variables scrubbed.
    -> (returncode, stdout bytes, stderr text); (None, b"", why) when git could not run."""
    try:
        import git_quiet as _gq
        r = _gq.run(["git", "-C", path] + list(args), capture_output=True, timeout=timeout, env=_git_env(), input=input)
    except Exception as e:
        return None, b"", "%s: %s" % (type(e).__name__, str(e)[:120])
    return r.returncode, r.stdout or b"", (r.stderr or b"").decode("utf-8", "replace")


def _line(path, args):
    rc, out, _err = git(path, args)
    if rc != 0:
        return None
    s = out.decode("utf-8", "replace").strip()
    return s or None


def _raw(out):
    """git's --raw -z records. -> [(old sha, new sha, path)]; a zero new sha is the working tree's side."""
    parts, rows, i = out.split(b"\0"), [], 0
    while i < len(parts):
        head = parts[i]
        if head.startswith(b":") and i + 1 < len(parts):
            f = head[1:].split()
            if len(f) >= 4:
                rows.append((f[2].decode("ascii", "replace"), f[3].decode("ascii", "replace"),
                             parts[i + 1].decode("utf-8", "replace")))
            i += 2
            continue
        i += 1
    return rows


def change_bound(path, args):
    """REG-3209 review - the bytes the files a change touches hold, both sides summed: an upper bound on what its diff can
    be, read BEFORE the diff is, so a regenerated 2 GB binary is never pulled into the console's memory.
    args: a diff / diff-tree spec. -> (bytes | None, why)"""
    rc, out, err = git(path, list(args) + ["--raw", "-z", "--no-abbrev", "--no-renames"])
    if rc != 0:
        return None, "its change could not be listed (%s)" % err.strip()[:80]
    total, shas = 0, []
    for old, new, name in _raw(out):
        for sha in (old, new):
            if sha.strip("0"):
                shas.append(sha)
        if not new.strip("0"):
            try:
                total += os.lstat(os.path.join(path, name)).st_size
            except OSError:
                pass
    if shas:
        rc, out, err = git(path, ["cat-file", "--batch-check=%(objectsize)"],
                           input=("\n".join(shas) + "\n").encode("ascii"))
        if rc != 0:
            return None, "the sizes of its files could not be read (%s)" % err.strip()[:80]
        for ln in out.decode("ascii", "replace").splitlines():
            total += int(ln) if ln.strip().isdigit() else 0
    return total, None


def git_facts(path):
    """What a git tree at `path` holds that is not upstream. -> dict (why set when it cannot be told)."""
    real = _real(path)
    f = {"top": None, "gitdir": None, "common": None, "linked": None, "head": None, "branch": None, "upstream": None,
         "plus": [], "merges": [], "refs": [], "dirty": b"", "untracked": [], "nested": [], "stashes": [],
         "running": None, "locked": False, "mainOf": 0, "finished": None, "why": None}
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
        except FileNotFoundError:
            f["mainOf"] = 0                 # no worktrees folder at all: a measured none (a plain clone)
        except OSError:
            # v3865 (GitHub's swallow ratchet) - a folder that exists and will not list is UNKNOWN, never "it holds no
            # worktrees": the prune keeps a tree whose linked worktrees could not be counted, as it keeps the main tree
            f["mainOf"] = None
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
    f["plus"], f["refs"] = plus, refs
    # REG-3209 review - git cherry SKIPS merge commits, so the work done inside a merge (a conflict resolution, an edit made
    # while merging) is in no patch; a tree that holds one is salvaged as a bundle of its unmerged history as well
    rc, out, err = git(path, ["rev-list", "--merges", "^origin/main"] + refs)
    if rc != 0:
        f["why"] = "its merge commits could not be listed (%s)" % err.strip()[:80]
        return f
    f["merges"] = out.decode("ascii", "replace").split()
    # the tracked change is LISTED here (the diff itself is read only after its size is bounded, in the salvage)
    rc, raw, err = git(path, ["diff", "HEAD", "--raw", "-z", "--no-abbrev", "--no-renames"])
    if rc != 0:
        f["why"] = "the tracked diff could not be read (%s)" % err.strip()[:80]
        return f
    f["dirty"] = raw
    rc, out, err = git(path, ["ls-files", "--others", "--exclude-standard", "-z"])
    if rc != 0:
        f["why"] = "the untracked files could not be listed (%s)" % err.strip()[:80]
        return f
    names = [n for n in out.decode("utf-8", "replace").split("\0") if n]
    # REG-3208 review - git lists an untracked repository inside the tree as "dir/"; opening it raised IsADirectoryError and
    # a patch could never carry its history anyway
    f["nested"] = [n for n in names if n.endswith("/")]
    f["untracked"] = [n for n in names if not n.endswith("/")]
    if not f["linked"]:
        st = _line(path, ["stash", "list", "--format=%H"])
        f["stashes"] = (st or "").split()
    f["finished"] = not (f["plus"] or f["merges"] or f["dirty"] or f["untracked"] or f["nested"] or f["stashes"])
    if f["nested"]:
        f["why"] = ("it holds a git repository inside that it does not track (%s) - a patch cannot carry another "
                    "repository's history, so it waits for a hand" % ", ".join(f["nested"][:3]))
    return f


# ── extract + verify ────────────────────────────────────────────────────────────────────────────────────────────────

def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _safe_rel(name):
    n = os.path.normpath(name)
    return None if (os.path.isabs(n) or n.startswith("..") or n in (".", "")) else n


def _git_payload(path, facts, scratch=None, rm=None):
    """The informational files of a git tree. -> (files [(rel, bytes)], notSaved [{path, bytes, why}], why | None, blocked)
    blocked True: a DECLARED refusal (over a cap) - the tree waits for a hand; False with a why: the salvage failed.
    REG-3209 review: every byte of unmerged work counts against SALVAGE_CAP and is never cut short; each diff is bounded
    by its touched files' sizes before it is read; untracked files over the cap are named, the rest are copied."""
    files, not_saved, total = [], [], [0]

    def take(rel, data):
        if total[0] + len(data) > SALVAGE_CAP:
            return ("its unmerged work is over the %d MB salvage cap (%s alone is %.1f MB) - salvage it by hand"
                    % (SALVAGE_CAP // 1000 ** 2, rel, len(data) / 1e6))
        total[0] += len(data)
        files.append((rel, data))
        return None

    def read(what, spec, args):
        b, bwhy = change_bound(path, spec)
        if b is None:
            return None, "%s: %s" % (what, bwhy), False
        if b > READ_CAP:
            return None, ("%s touches %.0f MB of files, more than the lane reads (%d MB) - salvage it by hand"
                          % (what, b / 1e6, READ_CAP // 1000 ** 2)), True
        rc, out, err = git(path, args)
        if rc != 0:
            return None, "%s could not be read (%s)" % (what, err.strip()[:80]), False
        return out, None, False

    for i, sha in enumerate(facts["plus"]):
        out, why, blocked = read("commit %s" % sha[:12], ["diff-tree", "-r", "--root", "--no-commit-id", sha],
                                 ["format-patch", "-1", "--stdout", "--binary", sha])
        if why:
            return files, not_saved, why, blocked
        if not out:
            rc, out, err = git(path, ["show", "--binary", "--first-parent", "--format=fuller", sha])
            if rc != 0 or not out:
                return files, not_saved, "commit %s could not be written as a patch (%s)" % (sha[:12], err.strip()[:80]), False
        why = take("patches/%04d-%s.patch" % (i + 1, sha[:12]), out)
        if why:
            return files, not_saved, why, True
    if facts.get("merges"):
        rc, out, err = git(path, ["rev-list", "--objects", "--disk-usage", "^origin/main"] + list(facts["refs"]))
        b = int(out.strip()) if rc == 0 and out.strip().isdigit() else None
        if b is None:
            return files, not_saved, ("it holds %d merge commit(s) not upstream, and the size of that history could not "
                                      "be told (%s)" % (len(facts["merges"]), err.strip()[:60] or "git rev-list")), True
        if b > SALVAGE_CAP:
            return files, not_saved, ("its unmerged history (with %d merge commit(s)) is %.1f MB, over the %d MB salvage "
                                      "cap - salvage it by hand" % (len(facts["merges"]), b / 1e6,
                                                                    SALVAGE_CAP // 1000 ** 2)), True
        why = _room_refuses(rm, b)              # the bundle is written to a file before it is read
        if why:
            return files, not_saved, why, True
        scratch = scratch or os.path.dirname(path)
        os.makedirs(scratch, exist_ok=True)
        tmp = os.path.join(scratch, ".growers-%d-history.bundle" % os.getpid())
        try:
            rc, _out, err = git(path, ["bundle", "create", "-q", tmp, "^origin/main"] + list(facts["refs"]))
            data = None
            if rc == 0:
                with open(tmp, "rb") as fh:
                    data = fh.read()
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass
        if not data:
            return files, not_saved, "its unmerged history could not be bundled (%s)" % err.strip()[:80], False
        why = take("history.bundle", data)
        if why:
            return files, not_saved, why, True
    if facts["dirty"]:
        out, why, blocked = read("the tracked change", ["diff", "HEAD"], ["diff", "HEAD", "--binary"])
        if why:
            return files, not_saved, why, blocked
        why = take("dirty.diff", out) if out else None
        if why:
            return files, not_saved, why, True
    for j, st in enumerate(facts["stashes"]):
        out, why, blocked = read("stash %s" % st[:12], ["diff", st + "^1", st], ["diff", "--binary", st + "^1", st])
        if why:
            return files, not_saved, why, blocked
        why = take("stash/%02d-%s.diff" % (j, st[:12]), out)
        if why:
            return files, not_saved, why, True
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
        elif not os.path.isfile(full):
            return files, not_saved, "untracked %s is not a regular file, so what it holds cannot be told" % name, True
        elif st.st_size > FILE_CAP or total[0] + st.st_size > SALVAGE_CAP:
            not_saved.append({"path": name, "bytes": st.st_size, "why": "over the size cap"})
        else:
            with open(full, "rb") as fh:
                data = fh.read()
            total[0] += len(data)
            files.append(("untracked/" + rel, data))
    return files, not_saved, None, False


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
    return files, not_saved, None, False


def _readme(meta):
    lines = ["Salvaged by the disk growers lane (REG-3209) before %s was pruned." % meta["path"],
             "entry %s, owner %s, kind %s." % (meta["entry"], meta["owner"], meta["kind"])]
    if meta["kind"] == KIND_GIT:
        lines += ["HEAD %s on %s." % (meta.get("head"), meta.get("branch") or "a detached HEAD"),
                  "patches/  every commit not upstream by patch-id (git cherry origin/main) - restore with git am",
                  "history.bundle  (when it held a merge commit, which git cherry skips) every commit not on "
                  "origin/main - restore with git fetch <bundle> HEAD:refs/heads/salvaged",
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


def _stat_key(full):
    try:
        st = os.lstat(full)
        return [st.st_size, st.st_mtime_ns, st.st_ctime_ns]
    except OSError:
        return [None, None, None]


def _fingerprint(c, facts, w):
    """What the grower holds that a salvage must match: a reused salvage is one whose fingerprint still is. A write
    moves mtime and ctime, and a copy that keeps mtimes still moves ctime."""
    if c["kind"] == KIND_GIT:
        un = [[n] + _stat_key(os.path.join(c["path"], n)) for n in facts["untracked"]]
        dirty = [[n] + _stat_key(os.path.join(c["path"], n)) for _o, new, n in _raw(facts["dirty"]) if not new.strip("0")]
        parts = [facts["head"], facts["plus"], facts.get("merges") or [], _sha(facts["dirty"]), dirty, un,
                 facts["stashes"]]
    else:
        parts = [w["bytes"], w["files"], w["newest"]]
    return _sha(json.dumps([c["kind"]] + parts, sort_keys=True, default=str).encode("utf-8"))


def append_line(manifest, data):
    """Append one line and read exactly that line back from where it was written. -> bool"""
    with open(manifest, "ab") as fh:
        off = fh.seek(0, os.SEEK_END)
        fh.write(data)
        fh.flush()
    with open(manifest, "rb") as fh:
        fh.seek(off)
        return fh.read(len(data)) == data


def room(free_fn, sroot, dir_bytes):
    """What a pass may still write into the salvage dir. -> dict (free asked once, lazily; spent counted as written)"""
    return {"fn": free_fn, "root": sroot, "free": None, "asked": False, "dir": dir_bytes, "spent": 0}


def _room_refuses(rm, n):
    """REG-3208 review - a salvage runs exactly when the disk is short, so it never writes what would leave the salvage
    disk under SALVAGE_MIN_FREE or the salvage dir past SALVAGE_DIR_CAP. -> why | None"""
    if rm is None:
        return None
    if not rm["asked"]:
        rm["asked"] = True
        try:
            rm["free"] = None if rm["fn"] is None else float(rm["fn"](rm["root"]))
        except Exception:
            rm["free"] = None
    if not _num(rm["free"]):
        return "the salvage disk's free space could not be read, so nothing is written to it"
    if rm["free"] - rm["spent"] - n < SALVAGE_MIN_FREE:
        return ("writing %.1f MB would leave the salvage disk under %.1f GB free"
                % (n / 1e6, SALVAGE_MIN_FREE / 1e9))
    if _num(rm["dir"]) and rm["dir"] + rm["spent"] + n > SALVAGE_DIR_CAP:
        return ("the salvage dir holds %.0f MB, at its %.1f GB cap - nothing new is salvaged until it is read and "
                "cleared" % ((rm["dir"] + rm["spent"]) / 1e6, SALVAGE_DIR_CAP / 1e9))
    return None


def _record(c, fp, w, sroot, now_s, rm, recorded):
    """A RECORD entry's salvage: one manifest line saying what the folder was, read back. A folder whose fingerprint was
    recorded already is not recorded again, so a dry-run's every-30-min pass writes nothing new. -> as salvage()"""
    entry = c["entry"]
    res = {"ok": False, "dir": None, "fingerprint": fp, "files": 0, "bytes": 0, "notSaved": [], "reused": False,
           "why": None, "blocked": False, "record": True}
    if recorded is not None and recorded.get(c["path"]) == fp:
        res.update(ok=True, reused=True)
        return res
    biggest = sorted(w.get("list") or [], key=lambda t: -t[1])[:3]
    line = {"ts": int(now_s), "event": "record", "entry": entry["name"], "owner": entry["owner"], "path": c["path"],
            "fingerprint": fp, "bytes": w["bytes"], "files": w["files"], "newest": w["newest"],
            "biggest": [[r, b] for r, b, _m in biggest]}
    data = (json.dumps(line, sort_keys=True) + "\n").encode("utf-8")
    why = _room_refuses(rm, len(data))
    if why:
        res.update(why=why, blocked=True)
        return res
    try:
        os.makedirs(sroot, exist_ok=True)
        if not append_line(os.path.join(sroot, "manifest.jsonl"), data):
            res["why"] = "the record line did not read back"
            return res
    except Exception as e:
        res["why"] = "the record raised %s: %s" % (type(e).__name__, str(e)[:100])
        return res
    if rm is not None:
        rm["spent"] += len(data)
    if recorded is not None:
        recorded[c["path"]] = fp
    res.update(ok=True, files=1, bytes=len(data))
    return res


def salvage(c, facts, w, sroot, now_s, rm=None, recorded=None):
    """Extract what is informational in candidate `c`, write it under the salvage root, read it back, and append one
    manifest line. -> {ok, dir, fingerprint, files, bytes, notSaved, reused, why, blocked}. ok False BLOCKS the prune;
    blocked True says it was a declared refusal (a cap, the disk) rather than a salvage that failed."""
    entry = c["entry"]
    fp = _fingerprint(c, facts, w)
    if entry.get("salvage") == RECORD:
        return _record(c, fp, w, sroot, now_s, rm, recorded)
    rel_dir = os.path.join(entry["name"], "%s-%s" % (os.path.basename(c["path"]), fp[:12]))
    dest = os.path.join(sroot, rel_dir)
    manifest = os.path.join(sroot, "manifest.jsonl")
    res = {"ok": False, "dir": rel_dir, "fingerprint": fp, "files": 0, "bytes": 0, "notSaved": [], "reused": False,
           "why": None, "blocked": False}
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
            files, not_saved, why, blocked = _git_payload(c["path"], facts, scratch=sroot, rm=rm)
        else:
            files, not_saved, why, blocked = _scratch_payload(c["path"], entry, w)
        if why:
            res.update(why=why, blocked=blocked)
            return res
        meta = {"entry": entry["name"], "owner": entry["owner"], "kind": c["kind"], "path": c["path"],
                "fingerprint": fp, "ts": int(now_s), "measuredBytes": w["bytes"], "newest": w["newest"],
                "head": facts.get("head") if facts else None, "branch": facts.get("branch") if facts else None,
                "merges": (facts.get("merges") or []) if facts else [], "notSaved": not_saved, "files": {}}
        planned = sum(len(d) for _r, d in files) + 64 * 1024        # + the README, meta.json and the manifest line
        why = _room_refuses(rm, planned)
        if why:
            res.update(why=why, blocked=True)
            return res
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
        if rm is not None:
            rm["spent"] += planned
        ok, why = verify(dest, meta)
        if not ok:
            res["why"] = why
            return res
        line = {"ts": int(now_s), "event": "salvage", "entry": entry["name"], "owner": entry["owner"],
                "path": c["path"], "dir": rel_dir, "fingerprint": fp, "files": len(meta["files"]),
                "bytes": sum(r["bytes"] for r in meta["files"].values()), "notSaved": len(not_saved)}
        if not append_line(manifest, (json.dumps(line, sort_keys=True) + "\n").encode("utf-8")):
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
        why = "the growers state did not read (%s) - moved aside, every entry is back in dry-run" % type(e).__name__
        # REG-3208 review - kept in the fresh state, so the passes after this one still say it (for RESET_SAY_H)
        fresh.update(resetWhy=why)
        return fresh, why


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

    free_bytes: a callable(path) -> bytes (raising = UNKNOWN), or None (UNKNOWN); it reads the growers' disks and the
    salvage disk. held: (set | None, why) to use instead of asking the machine, every time it would be asked.
    measure_only: no salvage, no prune, no state written (the CLI). repo: the console's repo, whose worktree entries that
    name a folder that is gone are counted and said."""
    now_s = _now() if now_s is None else now_s
    t0 = _now()
    rec = {"ts": int(now_s * 1000), "candidates": [], "removed": [], "waiting": [], "wouldPrune": [], "deferred": [],
           "freed": 0, "growers": [], "held": None, "holdersAsked": 0, "free": None, "watermark": None,
           "stateWhy": None, "error": None, "salvaged": 0, "owed": None, "say": None, "worked": None,
           "freedBytes": None, "dryRun": [], "salvageRoot": salvage_dir, "lastSalvage": None, "biggest": [],
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
    if state.get("resetWhy") and not state.get("resetTs"):
        state["resetTs"] = now_s                  # the pass's own clock, which the laws can move
    if not rec["stateWhy"] and state.get("resetWhy") and now_s - float(state.get("resetTs") or 0) < RESET_SAY_H * 3600:
        rec["stateWhy"] = state["resetWhy"]
    recorded_all = state.setdefault("recorded", {})

    def ask():
        """REG-3208 review - holders are asked LAZILY (a PC with nothing past its floor never needs them, so a Windows
        PC without psutil is not UNKNOWN forever) and AGAIN before each prune."""
        r = held if held is not None else holders(platform)
        rec["holdersAsked"] += 1
        return r

    meas = [None]                          # the measure-time holders reading, asked at the first grower past its floor
    rec["held"] = "not asked - no grower was past its age floor"
    found = find(entries, root_map)
    # REG-3208 review - what the salvage dir already holds is what SALVAGE_DIR_CAP holds it to (none yet: 0)
    rm = room(free_bytes, sroot, walk(sroot, budget_s=10.0)["bytes"] if os.path.isdir(sroot) else 0) if sroot else None
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
                        newest = max(newest, _stamp(os.stat(os.path.join(facts["gitdir"], nm)))) if newest else newest
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
        if meas[0] is None:
            meas[0] = ask()
            rec["held"] = meas[0][1] if meas[0][0] is not None else ("UNKNOWN - " + str(meas[0][1]))
        if meas[0][0] is None:
            c.update(state="unknown", why="what holds it cannot be read (%s)" % meas[0][1])
            continue
        if _held_by(meas[0][0], real, os.path.abspath(row["path"])):
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
            if "mainOf" in facts and facts.get("mainOf") is None:
                c.update(state="protected", why="whether it is the main tree of linked worktrees could not be read - kept")
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
    outcome, handled = {}, 0
    for c in due:
        ent = c["entry"]
        mode = per_entry[ent["name"]]["mode"]
        trig = "past its %d h bound" % ent["boundH"] if c["_bound"] else "the disk is under its %.0f GB watermark" % (wm / 1e9)
        if measure_only:
            c.update(state="due", why="%s - measured only, nothing salvaged or pruned" % trig)
            continue
        if handled >= PRUNES_PER_PASS or _now() - t0 > budget_s:
            # bounded: a backlog drains over several passes instead of one pass holding the machine
            c.update(state="deferred", why="%s - this pass reached its %d-grower / %d s bound, so it goes on a later "
                                           "pass" % (trig, PRUNES_PER_PASS, budget_s))
            rec["deferred"].append({"name": c["name"], "entry": ent["name"]})
            continue
        handled += 1
        if not sroot:
            c.update(state="waiting", why="no salvage dir, so nothing may be pruned")
            rec["waiting"].append({"name": c["name"], "entry": ent["name"], "why": c["why"]})
            continue
        if c["_facts"] is not None and c["_facts"].get("why"):
            # REG-3209 - a tree whose unmerged work cannot be READ cannot be salvaged, so it is never pruned. A declared
            # wait, not a failed salvage: the trees beside it still earn their entry's arming (REG-3208 review)
            c.update(state="waiting", why="its salvage cannot be made: %s" % c["_facts"]["why"])
            rec["waiting"].append({"name": c["name"], "entry": ent["name"], "why": c["_facts"]["why"]})
            continue
        s = salvage(c, c["_facts"], c["_walk"], sroot, now_s, rm=rm,
                    recorded=recorded_all.setdefault(ent["name"], {}))
        c["salvage"] = {k: s[k] for k in ("ok", "dir", "files", "bytes", "reused", "why")}
        c["salvage"]["notSaved"] = len(s["notSaved"])
        if not s["ok"]:
            c.update(state="waiting", why="its salvage %s (%s) - it stays on disk" % (
                "was not made" if s["blocked"] else "did not finish", s["why"]))
            rec["waiting"].append({"name": c["name"], "entry": ent["name"], "why": s["why"]})
            if not s["blocked"]:
                outcome[ent["name"]] = "failed"       # the lane's own salvage broke: the entry does not arm on it
            continue
        if not s["reused"]:
            rec["salvaged"] += 1
        if s["dir"]:
            rec["lastSalvage"] = s["dir"]
        if outcome.get(ent["name"]) != "failed":
            outcome[ent["name"]] = "clean"
        where = s["dir"] or "the manifest (a record line)"
        if mode != ARMED:
            c.update(state="would-prune", why="%s; salvaged to %s and read back - dry-run, so it stays" % (trig, where))
            rec["wouldPrune"].append({"name": c["name"], "entry": ent["name"], "bytes": c["bytes"]})
            continue
        fresh = ask()                      # REG-3208 review - asked again before EACH prune, after its own salvage
        if fresh[0] is None or _held_by(fresh[0], c["real"], os.path.abspath(c["path"])):
            c.update(state="held", why="salvaged to %s; a live process holds it now (or holders could not be read), "
                                       "so it stays" % where)
            continue
        ok, why = prune(c, c["_facts"])
        if not ok:
            c.update(state="failed", why="salvaged to %s, and the prune failed: %s" % (where, why))
            rec["waiting"].append({"name": c["name"], "entry": ent["name"], "why": why})
            continue
        c.update(state="pruned", why="%s; salvaged to %s first" % (trig, where))
        rec["removed"].append({"name": c["name"], "entry": ent["name"], "bytes": c["bytes"], "salvage": s["dir"],
                               "finished": c["finished"]})
        rec["freed"] += int(c["bytes"] or 0)
        recorded_all.get(ent["name"], {}).pop(c["path"], None)
        try:
            with open(os.path.join(sroot, "manifest.jsonl"), "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"ts": int(now_s), "event": "prune", "entry": ent["name"], "path": c["path"],
                                     "bytes": c["bytes"], "salvage": s["dir"], "finished": c["finished"]},
                                    sort_keys=True) + "\n")
        except OSError:
            pass
    # a record kept only for folders still there, so the map is as big as the population and never more
    alive = {}
    for c in rows:
        if c.get("entry") and os.path.lexists(c["path"]):
            alive.setdefault(c["entry"]["name"], set()).add(c["path"])
    for name in list(recorded_all):
        kept = {p: f for p, f in recorded_all[name].items() if p in alive.get(name, ())}
        if kept:
            recorded_all[name] = kept
        else:
            recorded_all.pop(name)
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
    # REG-3208 review - owed is UNKNOWN when any grower's decision rested on something that could not be read (its age,
    # its holders); a pass that never needed holders owes a measured number
    rec["owed"] = None if unknown else len(rec["waiting"]) + len(rec["wouldPrune"]) + len(rec["deferred"])
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
    if rec.get("deferred"):
        parts.append("%d more due, deferred to a later pass (each pass is bounded)" % len(rec["deferred"]))
    if rec.get("stateWhy"):
        parts.append(rec["stateWhy"])
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
            "deferred": len(rec.get("deferred") or []),
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
