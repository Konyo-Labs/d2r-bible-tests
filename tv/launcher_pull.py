# -*- coding: utf-8 -*-
"""A tracked file that matches the fetched update is not a local edit.

The running console already treats a file whose bytes match origin/main, CR
ignored, as an update (_matches_fetched_origin). That code runs only inside a
process that has it. The launcher runs first, from the files on disk, and used
to skip the pull whenever git status showed any tracked change. A restart then
left the checkout where it was.

This does not fetch. It reads the origin/main ref already on disk. A blob that
cannot be read is not an update. A history that cannot fast-forward is not
reset. Unknown stays unknown: the caller skips the pull.

Exit codes of --apply: 0 the tree is clean, or the changed files were the
update and now sit on that commit; 2 local work, or not a fast-forward, nothing
was reset; 1 the tree could not be read, or the update matched and the reset
itself failed. A failed reset says so. It is not an unread tree.
"""
import os
import stat
import subprocess
import sys


def bytes_match_ignoring_cr(left, right):
    """Same rule as the console: equal, or equal once CR at end of line is ignored."""
    if left == right:
        return True

    def _norm(raw):
        return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")

    return _norm(left) == _norm(right)


def _run(repo, args):
    try:
        import git_quiet as _gq        # v3866 - on Windows a plain spawn opened a terminal over his game
        r = _gq.run(
            ["git", "-C", repo] + list(args),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20,
        )
    except Exception:
        return 1, b"", b""
    return r.returncode, r.stdout or b"", r.stderr or b""


def _safe_rel(name):
    name = str(name or "").replace("\\", "/").strip()
    if not name or name.startswith("/") or name.startswith("~") or name.startswith('"'):
        return None
    if ".." in name.split("/") or ":" in name:
        return None
    return name


def _plain_modification(status):
    """A content change of a tracked file. Adds, deletes and renames block."""
    if len(status) < 2:
        return False
    return status[0] in " M" and status[1] in " M" and status != "  "


def _porcelain(repo):
    """Tracked porcelain rows, or None when git could not be read."""
    rc, out, _err = _run(repo, ["status", "--porcelain", "--untracked-files=no"])
    if rc != 0:
        return None
    rows = []
    for line in out.decode("utf-8", "replace").splitlines():
        if len(line) < 4:
            continue
        status, path = line[:2], line[3:]
        if status == "??":
            continue
        rows.append((status, path))
    return rows


def _matches(repo, rel):
    rc, blob, _err = _run(repo, ["show", "origin/main:" + rel])
    if rc != 0:
        return False
    try:
        with open(os.path.join(repo, rel), "rb") as fh:
            disk = fh.read()
    except Exception:
        return False
    return bytes_match_ignoring_cr(disk, blob)


def _is_ancestor(repo):
    """True when HEAD can fast-forward to origin/main. False when it cannot. None when unknown."""
    rc, _out, _err = _run(repo, ["merge-base", "--is-ancestor", "HEAD", "origin/main"])
    if rc == 0:
        return True
    if rc == 1:
        return False
    return None


def _real_dir(path):
    """A directory, not a symlink to one. isdir() follows the link."""
    try:
        return stat.S_ISDIR(os.lstat(path).st_mode)
    except OSError:
        return False


def _index_has(repo, rel):
    """True when the index tracks rel or a path under it. None when git could not be asked.

    --literal-pathspecs: notes[1].txt is a path, not a wildcard. Without it,
    ls-files matches notes1.txt and an untracked notes[1].txt looks tracked.
    """
    rc, out, _err = _run(repo, ["--literal-pathspecs", "ls-files", "-z", "--", rel])
    if rc != 0:
        return None
    return bool(out)


def _untracked_inside(repo, rel):
    """True when an untracked file sits at rel or under it. None when git could not be asked.

    No --exclude-standard: an ignored file is still local. reset deletes it
    with the directory, so it is in the way.
    """
    rc, out, _err = _run(repo, ["--literal-pathspecs", "ls-files", "-z", "-o",
                                "--", rel])
    if rc != 0:
        return None
    return bool(out)


def _untracked_occupies(repo, rel):
    """True when an untracked file would be replaced here. None when that cannot be read.

    A tracked file is the update. A tracked directory is the update only when
    nothing untracked sits inside it, because reset deletes that directory.
    """
    full = os.path.join(repo, rel)
    if not os.path.lexists(full):
        return False
    tracked = _index_has(repo, rel)
    if tracked is None:
        return None
    if not tracked:
        return True
    if not _real_dir(full):
        return False
    inside = _untracked_inside(repo, rel)
    if inside is None:
        return None
    return bool(inside)


def _untracked_in_the_way(repo):
    """True when origin adds a path that already exists and is not tracked.

    `git reset --hard` replaces that file and exits 0. A fast-forward used to
    refuse. A tracked path is the update itself, so it is not in the way.
    None means git could not be asked, which is not a clear way.
    """
    # --no-renames: a rename is an add of the new path. Without it, diff.renames
    # hides that path and reset --hard replaces an untracked file there.
    # -z: without it several names arrive as one string, so a file among them
    # is missed and reset --hard replaces it.
    rc, out, _err = _run(repo, ["diff", "-z", "--name-only", "--diff-filter=A",
                                "--no-renames", "HEAD", "origin/main"])
    if rc != 0:
        return None
    for raw in out.split(b"\0"):
        # replace would turn a name git stored as raw bytes into a different
        # path, lexists would miss the file, and the reset would replace it.
        # A name that cannot be read stops the reset.
        try:
            rel = raw.decode("utf-8")
        except UnicodeDecodeError:
            return None
        if not rel:
            continue
        if _safe_rel(rel) is None:
            return None
        parts = rel.split("/")
        acc = ""
        for part in parts[:-1]:
            acc = part if not acc else acc + "/" + part
            parent = os.path.join(repo, acc)
            if not (os.path.lexists(parent) and not _real_dir(parent)):
                continue
            occupied = _untracked_occupies(repo, acc)
            if occupied is None:
                return None
            if occupied:
                return True
        occupied = _untracked_occupies(repo, rel)
        if occupied is None:
            return None
        if occupied and not _is_the_updates_own_file(repo, rel):
            return True
    return False


def _is_the_updates_own_file(repo, rel):
    """REG-3740 - an untracked REGULAR file whose bytes are origin/main's own blob at that path (CR ignored) is the
    update already on disk, not his work: the reset writes the same bytes over it. -> bool, False when unsure.

    MEASURED 11-11/12 on Dean's PC and the OLD ALT: an update stopped mid-checkout left 53 of main's new files on disk
    as untracked and HEAD unmoved, and every later pull refused 'an untracked file is in the way' - for ever, both PCs
    sat 97 behind until a hand reset. A file with different bytes, a directory or a link is still in the way."""
    try:
        if not stat.S_ISREG(os.lstat(os.path.join(repo, rel)).st_mode):
            return False
    except OSError:
        return False
    return _matches(repo, rel)


def _own_record(status, path):
    """REG-1865 - is this porcelain row one of the console's own tracked records? -> True | False | None (UNKNOWN)

    ONE rule, self_prove's (CONSOLE_OWN_RECORDS through _edits_beyond_own_records). His ALT sat on v3595, 123
    behind, because its only edit was ` M tv/.status_worst.json` - the record the console rewrites itself - and
    this read it as local work. A rule that cannot be asked forgives nothing."""
    try:
        import self_prove as _sp
        lines, _why = _sp.tracked_edits("%s %s" % (status, path))
    except Exception:
        lines = None
    # REG-1898 - UNKNOWN IS NOT AN ANSWER THE PULL ACTS ON: classify() says it could not tell, and the pull is blocked
    return None if lines is None else (lines == [])


def classify(repo):
    """-> {ok, block, update, own, ancestor, way}. Does not fetch and does not write."""
    rows = _porcelain(repo)
    if rows is None:
        return {"ok": False, "block": [], "update": [], "own": [], "ancestor": None, "way": None}
    block, update, own = [], [], []
    for status, path in rows:
        _own = _own_record(status, path)
        if _own is None:
            return {"ok": False, "block": [], "update": [], "own": [], "ancestor": None, "way": None}
        if _own:
            own.append(path)
            continue
        safe = _safe_rel(path)
        if safe is None or not _plain_modification(status) or " -> " in path:
            block.append(path or "?")
            continue
        if _matches(repo, safe):
            update.append(safe)
        else:
            block.append(safe)
    ancestor = _is_ancestor(repo) if update and not block else None
    way = False
    if update and not block and ancestor is True:
        way = _untracked_in_the_way(repo)
        if way is None:
            return {"ok": False, "block": [], "update": [], "own": [], "ancestor": None, "way": None}
    return {"ok": True, "block": block, "update": update, "own": own, "ancestor": ancestor, "way": bool(way)}


def _reset_failed(err, out):
    """The update matched. The reset did not. Quote the head of git's own error."""
    raw = err or out or b""
    text = raw.decode("utf-8", "replace").replace("\r", "\n")
    line = ""
    for part in text.split("\n"):
        part = part.strip()
        if part:
            line = part
            break
    if not line:
        line = "git gave no reason"
    if len(line) > 180:
        line = line[:180]
    return "the update matched but the reset failed: %s" % line


def _decision(found):
    """(code, message) or (None, None) when a reset is still the narrow case."""
    if not found["ok"]:
        return 1, "could not tell whether the changed files are the update"
    if found.get("way"):
        return 2, "an untracked file is in the way of the update, so nothing was reset"
    if found["block"]:
        return 2, "tracked files modified (local work protected)"
    if not found["update"]:
        if found.get("own"):
            # REG-1865 - not local work: the caller's fast-forward decides, and git refuses it by itself if origin
            # changed that record. Nothing here resets or checks out his record.
            return 0, "only the console's own record differs (%s) - the fast-forward decides" % ", ".join(found["own"][:3])
        return 0, "clean"
    if found.get("own"):
        # a reset --hard would overwrite the record, which is never this file's to do
        return 2, ("the console's own record differs (%s) and the reset onto the update would overwrite it, so "
                   "nothing was reset" % ", ".join(found["own"][:3]))
    if found["ancestor"] is not True:
        return 2, "the fast-forward was refused; nothing was reset"
    return None, None


def apply(repo, speak=False):
    """Put a tree that IS the fetched update onto that commit. Never fetches.

    0 clean, or reset onto the update. 2 local work, an untracked file in the
    way, or not a fast-forward. 1 could not tell, or the update matched and the
    reset itself failed. A reset happens only when a second read, immediately
    before it, still says every tracked change matches origin/main, HEAD is an
    ancestor, and no untracked path would be replaced.
    """
    code, msg = _decision(classify(repo))
    if code is None:
        # The tree can change between the two reads. The second one is the one
        # the reset is allowed to trust.
        code, msg = _decision(classify(repo))
    if code is None:
        rc, out, err = _run(repo, ["reset", "--hard", "origin/main"])
        if rc != 0:
            msg = _reset_failed(err, out)
            code = 1
        else:
            msg = "the changed files matched the update"
            code = 0
    if speak:
        print(msg)
    return code


def main(argv):
    repo = "."
    if "--repo" in argv:
        repo = argv[argv.index("--repo") + 1]
    if "--apply" in argv:
        return apply(repo, speak=True)
    found = classify(repo)
    if not found["ok"]:
        print("could not tell whether the changed files are the update")
        return 1
    anc = {True: "yes", False: "no"}.get(found["ancestor"], "unknown")
    print("block=%d update=%d ancestor=%s" % (len(found["block"]), len(found["update"]), anc))
    return 0 if not found["block"] else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
