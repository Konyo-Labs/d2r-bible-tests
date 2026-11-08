#!/usr/bin/env python3
"""Copy this repo somewhere scratch WITHOUT the things that will fill his disk.

⚠⚠ WHY THIS EXISTS, MEASURED. On 2026-09-03 three review agents were each told, in my own workflow
prompt, to "work on COPIES under /tmp if you need to sabotage something". Each ran

    cp -R /Users/konyo/d2r_bible_tests/tv /tmp/skep_<n>/tv

`tv/` holds the reel JPEG store (5.8 GB) and, at the time, a Chrome profile the render gate never
cleaned (1.4 GB). Three copies wrote **20.5 GB in four minutes** onto a volume with about 9 GB
free. It hit ENOSPC, and then every Bash call in the session — mine and every agent's — failed
before it ran, because the harness could not create its own output file. Nobody could even run
`df` to see what had happened, let alone `rm`.

The prompt was the defect. "Copy it to /tmp" is a reasonable instruction that happens to be
catastrophic in a repo carrying gigabytes of footage, and no amount of remembering fixes that.
So: a copier that CANNOT carry the heavy directories, and REFUSES rather than filling the disk.

    python3 tv/safe_copy.py /tmp/my_scratch          # the whole repo, minus the heavy parts
    python3 tv/safe_copy.py /tmp/my_scratch tv       # just tv/, same exclusions

⚠ IT IS NOT A GENERAL COPIER AND MUST NOT BECOME ONE. It has one job: make the copy a sabotage
test needs, which is source and config, never footage.
"""
import argparse
import io
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

#: Directory NAMES never copied, at any depth. Each is here because it is large and regenerable —
#: a sabotage test reads source, never footage.
HEAVY = (
    "frames",           # the reel JPEG store — 5.8 GB, and it is HIS footage
    ".render_shots",    # render gate output: PNGs plus, until v2476, a 1.4 GB Chrome profile
    ".git",             # a full object store, and no sabotage test needs history
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "test-results",
    "playwright-report",
    "backups",
    "_archive",
    # 2026-09-25 — `.claude/worktrees` holds the isolated git worktrees of agents running IN THIS REPO
    # (639 MB with two live). Copied, it pushed every sandbox over the 400 MB refusal, so while any
    # isolated agent ran, EVERY heart2 --prove on this Mac returned "no lane could build a sandbox".
    # A worktree is a whole second checkout; no sabotage test reads another agent's tree.
    # ⚠ Like every name here it matches AT ANY DEPTH, so any directory called `worktrees` is skipped,
    # not only `.claude/worktrees` - deliberate (the Grok CLI's lens review flagged the breadth; there
    # is no other `worktrees` dir in the repo, and a checkout is never sabotage-test input).
    "worktrees",
    # REG-2340 (R9) - heart2's per-machine stores when no git dir could be found (a pointer that will not read): the
    # proofs and red memory of THIS checkout, never source a sabotage test reads
    ".heart2_v2",
)

#: FILE names never copied, at any depth, and file SUFFIXES never copied. REG-1845 — MEASURED on his Mac 2026-10-06:
#: the plan of the repo was 420.4 MB against the 400 MB ceiling, so every lane of every heart2 proof answered
#: "safe_copy REFUSED the sandbox (exit 1)", the census stayed STALE, and frame.release and vault.sweep_start stayed
#: locked behind it. The two largest files were runtime data, both gitignored and neither read by a law: heart2's own
#: per-machine proof cache (105.9 MB) and a reel-seed archive of his sessions (97.8 MB). Without them: 216.7 MB.
HEAVY_FILES = (".heart2_cache.json",)
HEAVY_SUFFIXES = (".tgz",)
#: REG-2340 (R9) - A STORE NEVER TRAVELS, IN ANY GENERATION. The exact name let every sibling through: a writer's
#: per-process tmp (`.heart2_cache.json.<pid>.<tid>.tmp` - a 320 MB tmp left in main's tv/ would push every main-tree
#: sandbox over the 400 MB refusal again, REG-1845), a `.prev`, an `.unreadable-<ms>` kept aside, Windows' lock file
#: (`.heart2_cache.lock`), the red memory, and this checkout's gate ledger and input map with their tmps. They are
#: records of this machine's runs, never source a sabotage test reads.
STORE_PREFIXES = (".heart2_cache", ".heart2_red", ".gate_ledger.json", ".gate_inputs.json")
#: REG-2123 - FILES THAT NAME A LIVE PROCESS ON THIS MACHINE NEVER TRAVEL. tv/control_agent.pid holds HIS live agent's pid;
#: copied into a prover sandbox, a private control_app there read it as its own agent, and its STOP path SIGTERMed it -
#: measured on 2026-10-09: "closing session (signal:SIGTERM)" in his agent log at 02:16 and 02:26, both during a push-time
#: prove of test_button_matrix. A copy is a tree of source and state, never a handle on his processes.
LIVE_SUFFIXES = (".pid",)


def _heavy_file(name):
    return (name in HEAVY_FILES or name.startswith(STORE_PREFIXES) or name.endswith(HEAVY_SUFFIXES)
            or name.endswith(LIVE_SUFFIXES))


#: Refuse outright above this. A sabotage copy that needs a gigabyte is not a sabotage copy, it is
#: the accident this file exists to prevent. Deliberately well under any plausible free-space
#: margin: the point is to fail while the machine is still usable, not at the last byte.
MAX_MB = 400

#: And never write a copy that would take the machine below this. Measured the hard way: at zero
#: bytes free, the tool cannot create its own output file, so NOTHING can run — not df, not rm.
#: A guard that only refuses at ENOSPC refuses too late to be fixed.
KEEP_FREE_MB = 4096


def _free_mb(path):
    """Free MB on the volume that will hold `path`. -> int | None

    ⚠⚠ IT MUST CLIMB TO AN EXISTING ANCESTOR, AND THE FIRST VERSION DID NOT. `os.statvfs`
    raises on a directory that does not exist yet, so this returned None for exactly the
    invocation this file's own docstring recounts as the disaster:

        python3 tv/safe_copy.py /tmp/skep_3/tv tv     # /tmp/skep_3 not created yet

    None then skipped the floor entirely (`if free is not None and ...`) while
    `shutil.copytree` happily called `os.makedirs` and wrote anyway. The 4 GB floor — the
    whole reason this file exists — was OFF on the one command shape that caused the
    ENOSPC. `copytree` creates the intermediates, so the volume that matters is the one
    under the nearest ancestor that already exists. Climb to it.
    """
    p = os.path.abspath(path)
    while True:
        try:
            # #229 — shutil.disk_usage, not os.statvfs: statvfs does not exist on Windows, so this read UNKNOWN on every Windows console. disk_usage.free is f_bavail * f_frsize on POSIX.
            return shutil.disk_usage(p).free // (1024 * 1024)
        except Exception:
            parent = os.path.dirname(p)
            if parent == p:       # reached the root and still nothing — genuinely unknown
                return None
            p = parent


def plan(src):
    """-> (files, bytes, skipped_dirs). Walks once, counting what WOULD be copied."""
    files, total, skipped = 0, 0, []
    for root, dirs, names in os.walk(src):
        drop = [d for d in dirs if d in HEAVY]
        for d in drop:
            skipped.append(os.path.relpath(os.path.join(root, d), src))
        dirs[:] = [d for d in dirs if d not in HEAVY]
        for n in names:
            if _heavy_file(n):
                skipped.append(os.path.relpath(os.path.join(root, n), src))
                continue
            p = os.path.join(root, n)
            try:
                if os.path.islink(p):
                    continue          # a symlink is copied as a link; it carries no bytes
                total += os.path.getsize(p)
                files += 1
            except Exception:
                pass
    return files, total, sorted(skipped)


def check(src, dst, force=False, say=None):
    """The refusals copy() applies BEFORE it writes. -> (rc, why). rc 0 = it would copy; why is the refusal.

    REG-1845 — one rule for the copy and for anyone who must know first whether a copy can be made (the self-prove
    lane asks this before it starts a proof whose every lane would be refused). `say` hears the plan lines."""
    return _check(src, dst, force, say)[:2]


def _check(src, dst, force=False, say=None):
    """check(), with the plan's file count and MB copy() reports. -> (rc, why, files, mb)"""
    say = say or (lambda *a, **k: None)
    src = os.path.abspath(src)
    dst = os.path.abspath(dst)
    if not os.path.isdir(src):
        return 2, "no such source: %s" % src, 0, 0.0
    if dst.startswith(REPO + os.sep) or dst == REPO:
        return 2, ("REFUSED — the destination is inside the repo (%s). A scratch copy belongs outside it, "
                   "or the next walk copies the copy." % dst), 0, 0.0

    files, total, skipped = plan(src)
    mb = total / (1024.0 * 1024.0)
    free = _free_mb(os.path.dirname(dst) or "/")
    say("plan: %d file(s), %.1f MB, skipping %d heavy director%s"
        % (files, mb, len(skipped), "y" if len(skipped) == 1 else "ies"))
    for s in skipped[:8]:
        say("   skipped: %s" % s)
    if len(skipped) > 8:
        say("   ... and %d more" % (len(skipped) - 8))

    if mb > MAX_MB and not force:
        return 1, ("REFUSED — %.1f MB is over the %d MB ceiling. This copier is for source, not data. "
                   "If you really mean it, pass --force, and check `df` first." % (mb, MAX_MB)), files, mb
    # ⚠ AND UNKNOWN IS NOT PERMISSION. If the free space could not be established at all,
    # refuse — a floor that abstains whenever it cannot measure is not a floor. Reaching
    # here means statvfs failed on every ancestor up to the root, which is not a normal
    # state and is not a reason to write gigabytes. [[unknown-stays-unknown]]
    if free is None:
        return 1, ("REFUSED — could not establish free space for %s (statvfs failed on every "
                   "ancestor up to the root). That is UNKNOWN, not enough room." % dst), files, mb
    if (free - mb) < KEEP_FREE_MB:
        return 1, ("REFUSED — the volume has %d MB free and this would leave %d MB, under the %d MB "
                   "floor. At zero bytes nothing can run at all, not even the command that would clean "
                   "up: on 2026-09-03 every shell in the session died at spawn."
                   % (free, int(free - mb), KEEP_FREE_MB)), files, mb
    return 0, "", files, mb


def copy(src, dst, force=False, say=print):
    """-> exit code. Refuses before writing anything if the plan is too big."""
    src = os.path.abspath(src)
    dst = os.path.abspath(dst)
    rc, why, files, mb = _check(src, dst, force, say)
    if rc:
        say(why)
        return rc

    def _ignore(_d, names):
        return {n for n in names if n in HEAVY or _heavy_file(n)}

    if os.path.exists(dst):
        say("REFUSED — %s already exists. Remove it yourself, deliberately." % dst)
        return 2
    # REG-3416 (v3882) - EVERY FILE IS COPIED WITH FRESH TIMES (shutil.copy: bytes + mode), never the source's (copy2).
    # MEASURED on his Mac 11-08 03:44: the safety net's heart2 sandbox in $TMPDIR lost 1,328 files mid-run - every one
    # with an access time of 3.2+ days in the repo, none under 3 (571 of 1,924 tv/*.py read in 3 days all stayed). macOS
    # sweeps $TMPDIR files unread for 3 days, and copy2 had carried each file's OLD access time into the sandbox, so the
    # sweeper deleted a live prover's files; test_control's closing clean run went RED (14 failures, 29 errors) and the
    # net shut every lock for 6 h. A git checkout and CI stamp fresh times too, so no law reads a copy's old ones.
    shutil.copytree(src, dst, ignore=_ignore, symlinks=True, copy_function=shutil.copy)
    say("copied %d file(s), %.1f MB -> %s" % (files, mb, dst))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Copy the repo to scratch without the heavy parts.")
    ap.add_argument("dest")
    ap.add_argument("subdir", nargs="?", default="",
                    help="copy only this subdirectory of the repo (e.g. tv)")
    ap.add_argument("--force", action="store_true",
                    help="ignore the size ceiling (never ignores the free-space floor)")
    ap.add_argument("--plan", action="store_true", help="say what it would copy and stop")
    a = ap.parse_args(argv)

    src = os.path.join(REPO, a.subdir) if a.subdir else REPO
    if a.plan:
        files, total, skipped = plan(src)
        print("would copy %d file(s), %.1f MB" % (files, total / (1024.0 * 1024.0)))
        for s in skipped:
            print("   skipping %s" % s)
        return 0
    # ⚠ `force` was parsed and dropped here, so the refusal message advised a flag that did
    # nothing: over the ceiling, `--force` printed the identical refusal and exited 1.
    return copy(src, a.dest, force=a.force)


if __name__ == "__main__":
    try:
        from console_safe import enable
        enable()
    except Exception:
        pass
    sys.exit(main())
