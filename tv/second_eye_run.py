#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run the second eye over a shipped version, end to end, in one command.

    python3 tv/second_eye_run.py v2802
    python3 tv/second_eye_run.py --backlog        # every version that still OWES a look
    python3 tv/second_eye_run.py v2802 --dry      # build and MEASURE the payload, send nothing

WHY THIS EXISTS. Every look used to be assembled by hand: find the commit, pull the diff, strip the
comments, paste it into a chat, read the answer back, and type the ledger row. Six manual steps per
version, and versions ship in batches of three or four.

⚠⚠ THE HAND-ASSEMBLY DID NOT MERELY COST TIME — IT PUT A FABRICATED NUMBER IN AN EVIDENCE LEDGER.
Recording v2801 by hand, the `sentCode` field was filled with `{"chars": 7250, "fences": 3}` typed
from an estimate, because `code_was_transmitted()` takes the PROMPT TEXT and returns that dict, and
it was handed a dict instead. It returned `{"chars": 0, "fences": 0}` — the honest answer to the
wrong question — and the invented value went into the row. The real figure, measured afterwards
from the actual payload, was 7,366. The ledger exists precisely so a claim of "a different family
looked at this" is checkable, and the one field that proves code was really transmitted had been
typed rather than measured. A number nobody measured is not evidence, however plausible it looks.
[[unknown-stays-unknown]] [[paid-work-with-no-memory]]

So: the payload is built by this script, MEASURED by this script from the bytes it is about to
send, and recorded by this script from what actually came back. There is no step where a human
number enters the row.

⚠ COLD MEANS COLD. The framing below is fixed and says nothing about what the code should do, what
changed, or what anyone suspects. The diff's own comments are stripped, because this repo's comments
routinely NAME the defect and its fix — handing them over would be asking the eye to agree with the
author rather than to look. [[feedback-comments-vs-code]]

⚠ AN UNREACHABLE EYE IS AN EMPTY SEAT. A CLI that fails, times out, or answers nothing is recorded
with reached=False and NO verdict. It is never silence-as-agreement.
[[feedback-silence-is-not-evidence]]
"""
import argparse
import io
import json
import os
import re
import subprocess
import time
import tempfile
import shutil
import atexit
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import second_eye_ledger as SEL  # noqa: E402

# The eye. Overridable so this is not welded to one vendor — a previous version of this lane was
# hardwired to one CLI and was therefore PERMANENTLY EMPTY on every machine but his.
# ⚠⚠ v3425 — THE CLI SUBSCRIPTION IS THE DEFAULT TRANSPORT. HIS RULING, 2026-09-23:
# *"make it the xAI subscription as a default"*, said the moment the paid API lane went dark.
# It restates what he already ruled on 2026-08-05 — *"i rather have them by default do the CLI
# obviously, but its there the MCP if its needed only"* — and the reason is not preference: the CLI
# needs no MCP connection, so a seat still fills in a headless or cron run, and it costs nothing
# per look because it is his subscription rather than metered API credits.
#
# MEASURED THE SAME HOUR, and it is why the ruling arrived: `mcp__grok-mcp__upload_file` returned
# PERMISSION_DENIED — *"has either used all available credits or reached its monthly spending
# limit"* — while this CLI answered v3421 at 95% reach with a schema-constrained verdict. The paid
# lane is DARK and the subscription lane is the one that works.
#
# ⚠ A CARVED SKILL SAID THE EXACT OPPOSITE. `human-eyes-harness` carried *"the CLI is currently out
# of build balance, HTTP 402; the MCP transport works"* — true when written, INVERTED now, and it
# would have sent the next session to the dead lane. Corrected in the same version. [[stale-reading]]
def _default_eye_cli():
    """#225 — ASK THE ONE RESOLVER, do not hardcode a second path. This was `~/.grok/bin/grok` with no
    `.exe`, so on the Windows ALT box — where C:\\Users\\USER-1\\.grok\\bin\\grok.exe exists and is on
    PATH — the doctor said "no binary there" and the second opinion read MISSING. g5_grok_eyes._grok_bin
    already resolves env override -> PATH (finds grok.exe) -> known install locations. [[copy-drift]]"""
    try:
        import g5_grok_eyes as _g5
        hit = _g5._grok_bin()
        if hit:
            return hit
    except Exception:
        pass
    return os.path.expanduser("~/.grok/bin/grok" + (".exe" if os.name == "nt" else ""))


# expanduser: an override written as ~/.grok/bin/grok names a path, and a bare string compare
# against the disk would call it missing. (It also keeps this constant visible to
# test_import_bound_paths, which registers every env-bound PATH constant bound at import.)
EYE_CLI = os.path.expanduser(os.environ.get("THIRD_EYE_CLI") or _default_eye_cli())
EYE_MODEL = os.environ.get("THIRD_EYE_MODEL") or "grok-4-1-fast-reasoning"
# ⚠⚠ v3408 — 300 s WAS TOO SHORT, AND THE COST WAS A BLOCKED SHIP. The eye is a subscription
# CLI, and a CLI is an AGENT: it reasons and calls tools, it does not stream a completion. MEASURED
# 2026-09-22 on a 22,519-char v3404 payload — it ran past 300 s, was killed, and the ledger
# correctly recorded an EMPTY SEAT. Correct, and useless: the pre-push gate then refused the ship
# for want of a look the harness had not waited for. A bound below what the instrument actually
# takes does not measure the instrument, it measures the bound. [[feedback-threshold-above-the-ceiling]]
EYE_TIMEOUT_S = float(os.environ.get("THIRD_EYE_TIMEOUT_S") or 1200)

# ⚠⚠ v3408 — THE EYE STANDS OUTSIDE THE REPO. A CLI eye is an AGENT with tools, and pointed at
# this checkout it can EDIT IT. That is not hypothetical: on 2026-09-22 a Grok CLI session was
# writing to tv/ while a ship was mid-flight, and Konyo had to be the one who noticed
# ("i think grok might be editing now the repo so check to see"). The payload is a DIFF and the
# prompt already says to judge only what is shown, so a working directory is not something the
# review needs — it is only something a reviewer can damage. [[execs-the-working-tree]]
# ⚠⚠ v3422 — THIS WAS `tempfile.mkdtemp(...)` AND IT RAN AT **IMPORT**, NOT AT USE.
# MEASURED 2026-09-23: three BARE imports — no look asked, no eye run — minted three directories.
# THIRTY-ONE modules import this one (every gate that touches the eye, the ledger, corroborate,
# console_doctor, run_gates), and each gate runs as its own subprocess, so ONE full gate run left
# ~30 behind. 115 were on his Mac from two days, 33 of them that day. #170 filed this as "a temp
# dir per look"; the measurement refutes that — the looks were never the cause, the import was.
#
# So EYE_CWD is now a PATH THAT IS COMPUTED, and the directory is created by the one function that
# actually needs one, then removed. Computing a path allocates nothing, which is why this is the
# fix rather than a reaper: the cheapest cleanup is not accumulating. [[process-port-discipline]]
#
# ⚠ IT MUST STAY AN ABSOLUTE PATH OUTSIDE THE REPO, and three readers depend on that being true of
# the ATTRIBUTE, not of some inner variable: console_doctor's `the eye stands outside the repo`
# row, v3408's gate, and `cwd=EYE_CWD` on the Popen — which v3408's red-proof pins as a literal.
# ⚠ PER-PROCESS, because a fixed name would be shared by concurrent gate subprocesses and one
# finishing would delete the directory another was still using.
EYE_CWD = (os.environ.get("THIRD_EYE_CWD")
           or os.path.join(tempfile.gettempdir(), "second_eye_%d" % os.getpid()))

# Only a directory WE minted may be removed. A THIRD_EYE_CWD he set is his, and an override that
# silently rmtree'd the folder he pointed at would be a far worse bug than the leak.
_EYE_CWD_IS_OURS = not os.environ.get("THIRD_EYE_CWD")
_EYE_CWD_MADE = False


def _eye_cwd_ready():
    """Create the eye's working directory, at the moment a look actually needs one.

    ⚠ Returns the path either way. If it cannot be created the eye still runs — with its cwd
    inherited, which v3408 argues is a risk, but a look refused for want of a scratch folder is a
    SILENT EMPTY SEAT, and this file's whole subject is that silence reads as agreement.
    """
    global _EYE_CWD_MADE
    try:
        os.makedirs(EYE_CWD, exist_ok=True)
        _EYE_CWD_MADE = True
    except Exception:
        pass
    return EYE_CWD


def eye_cwd_cleanup():
    """Remove the scratch directory, if we are the ones who made it.

    ⚠ REGISTERED WITH atexit AND CALLED IN A `finally`, because neither alone is enough: a
    `finally` never runs when the process is killed (the eye is bounded and gets killed), and
    atexit never runs on SIGKILL. Two ropes, one knot. [[i-own-everything-i-start]]
    """
    global _EYE_CWD_MADE
    if not (_EYE_CWD_IS_OURS and _EYE_CWD_MADE):
        return False
    _rm_snapshot(EYE_CWD)
    _EYE_CWD_MADE = False
    drop_eye_session(EYE_CWD)              # REG-2731 - and the Grok session folder this look's cwd minted
    return True


def _grok_sessions_dir():
    """His Grok sessions folder - the G5 lane's own answer, never a second copy of where Grok lives. -> path"""
    import g5_grok_eyes as _g5
    return os.path.join(_g5._real_grok_home(), "sessions")


def drop_eye_session(cwd, sd=None):
    """REG-2731 (#151, measured 2026-10-28) - A LOOK LEAVES NO GROK SESSION BEHIND. The Grok CLI mints a session folder
    named for its --cwd, and every look has its own second_eye_<pid> cwd: 250 of those folders (52 MB) sat in his
    sessions folder since 10-21, one more per look, while this lane removed only the cwd itself. On 09-01 that folder
    reached 11 GB and ENOSPC. Matched by the cwd's LAST folder exactly (g5_grok_eyes.session_tail). -> how many it
    removed, or None when the folder could not be read (UNKNOWN, never "0")."""
    base = os.path.basename(str(cwd or "").rstrip("/\\"))
    if not base.startswith("second_eye_") or len(base) <= len("second_eye_"):
        return 0
    try:
        import g5_grok_eyes as _g5
        sd = sd or _grok_sessions_dir()
        names = os.listdir(sd)
    except Exception:
        return None
    n = 0
    for name in names:
        if _g5.session_tail(name) == base and _g5._drop_session_dir(os.path.join(sd, name), attempts=2, pause_s=0.1):
            n += 1
    return n


def sweep_stale_eye_sessions(sd=None, now=None):
    """REG-2731 - the Grok session folders earlier looks left (a look killed before its cleanup): a cwd tail of exactly
    second_eye_<pid> - this lane's own name, so a folder of his that merely starts with the words is never matched -
    whose owner is dead, or a day old. Never this process's, never a live owner's younger one: a look runs for up to
    EYE_TIMEOUT_S, which is why this lane does not join the G5 sweep's 600 s rule.
    -> [(path, why)] removed; None when the folder could not be read."""
    now = time.time() if now is None else now
    try:
        import g5_grok_eyes as _g5
        sd = sd or _grok_sessions_dir()
        names = os.listdir(sd)
    except Exception:
        return None
    gone = []
    for n in sorted(names):
        tail = _g5.session_tail(n)
        if not tail.startswith("second_eye_"):
            continue
        pid = tail[len("second_eye_"):]
        if not pid.isdigit() or pid == str(os.getpid()):
            continue
        p = os.path.join(sd, n)
        try:
            age = now - os.path.getmtime(p)
        except OSError:
            continue
        if age < EYE_CWD_STALE_S and _pid_alive(pid):
            continue
        why = ("%.0f h old - no look lives that long" % (age / 3600.0)) if age >= EYE_CWD_STALE_S else ("its owner (pid %s) is dead" % pid)
        if _g5._drop_session_dir(p, attempts=2, pause_s=0.1):
            gone.append((p, why))
    return gone


def _rm_snapshot(path):
    """Remove a snapshot folder. -> True when it is gone.

    #169 Win 2 — the snapshot is made READ-ONLY on purpose, and a read-only directory cannot have its entries unlinked:
    write access comes back first, or a bare rmtree fails SILENTLY (ignore_errors). ⚠ 2026-09-26 (#243) — ONE removal
    for the live cleanup and the stale sweep: the sweep's first cut skipped the chmod and removed 3 of 120, reporting
    only what it managed. [[copy-drift]]"""
    for _root, _dirs, _files in os.walk(path):
        for _n in _dirs + _files:
            try:
                os.chmod(os.path.join(_root, _n), 0o700)
            except Exception:
                pass
    try:
        os.chmod(path, 0o700)
    except Exception:
        pass
    shutil.rmtree(path, ignore_errors=True)
    return not os.path.exists(path)


#: #169 Win 2 — a file larger than this is left out of the eye's snapshot and NAMED as left out.
#: bible.html is ~9 MB; handing the eye a file it cannot read in its budget is how a look stalls.
EYE_SNAPSHOT_MAX_BYTES = 2_000_000


#: #259 - an over-limit file is not dropped: its hunks' enclosing blocks go in as a NAMED excerpt, bounded.
EXCERPT_WINDOW = 80          # non-Python: lines either side of a changed line
EXCERPT_MAX_BLOCK = 400      # the most of any one block (a 2,000-line def is cut around its hunk)
EXCERPT_MAX_CHARS = 150000   # the whole excerpt file
_PY_TOP = re.compile(r"^(def |class |async def |@)")
_PY_DEF = re.compile(r"^(def |class |async def )")
#: REG-2026 - a line that cannot START a top-level statement: indented, blank, or a closing bracket at column 0
_PY_CONT = re.compile(r"^(?:[ \t]|[)\]}]|$)")


def excerpt_blocks(text, lines, is_py, window=None, max_block=None, max_chars=None):
    """#259 - the code around each changed line, numbered, merged and bounded. -> str ("" for no lines)

    MEASURED 2026-10-07: control_ui.html (2.2 MB) and control_app.py (2.7 MB) are both over the 2 MB snapshot
    limit, so every console change reached the eye as bare hunks; v3607's look answered cannot-tell ("I could not
    see the caller that concatenates the version word onto the lag span") and v3608's push was refused until a
    re-ask. A Python hunk gets its enclosing top-level def/class (with its decorators), a module-level line its whole
    statement plus a window; anything else a window either side."""
    window = EXCERPT_WINDOW if window is None else int(window)
    max_block = EXCERPT_MAX_BLOCK if max_block is None else int(max_block)
    max_chars = EXCERPT_MAX_CHARS if max_chars is None else int(max_chars)
    src = text.split("\n")
    n = len(src)
    spans = []
    for ln in sorted(set(int(x) for x in lines if isinstance(x, int) and 1 <= x <= n)):
        i = ln - 1
        # REG-2018 (the #231 eye on v3614) - a MODULE-LEVEL edit (a non-blank column-0 line that is not a def/class/
        # decorator) has no enclosing def: walking up would glue it to the previous function. It gets a window.
        # REG-2026 (the #231 eye on v3615) - an INDENTED, blank or closing-bracket line belongs to the statement it
        # sits in: `    limit=5,` inside `SETTINGS = dict(` is module-level too, and was glued to the previous def.
        # h = that statement's first line (the nearest column-0 line of code above; comments are stepped over).
        h = i
        if is_py and _PY_CONT.match(src[i]):
            while h > 0 and (_PY_CONT.match(src[h]) or src[h].startswith("#")):
                h -= 1
        _module_level = is_py and src[h][:1] not in ("", " ", "\t") and not _PY_TOP.match(src[h])
        if is_py and not _module_level:
            a = i
            while a > 0 and not _PY_TOP.match(src[a]):
                a -= 1
            _in_decorator = src[a].startswith("@")         # the changed line is a decorator, or inside one's arguments
            # REG-2026 - step up over the decorators above the def/class, each of which may run over several lines
            # (`@app.route(\n    "/x",\n)`): an @ line is the next statement up past only continuation lines.
            while a > 0:
                k = a - 1
                while k > 0 and (_PY_CONT.match(src[k]) or src[k].startswith("#")):
                    k -= 1
                if not src[k].startswith("@"):
                    break
                a = k
            b = i + 1
            # REG-2018 - a hunk on a decorator carries the function it decorates. REG-2026 - step past every decorator
            # line AND its continuation lines to the def/class line, then past that, before the next top-level marker.
            if _in_decorator:
                while b < n and not _PY_DEF.match(src[b]):
                    b += 1
                b = min(n, b + 1)
            while b < n and not _PY_TOP.match(src[b]):     # the next top-level def / class / decorator ends it
                b += 1
        else:
            a, b = max(0, i - window), min(n, i + window + 1)
            if is_py:
                # REG-2026 - a module-level line gets its whole statement, first line to last (a 268-line `CHECKS = [`
                # read as a window only never said which list it was); the max_block cut below still bounds it.
                e = i + 1
                while e < n and (_PY_CONT.match(src[e]) or src[e].startswith("#")):
                    e += 1
                a, b = min(a, h), max(b, e)
        if b - a > max_block:                        # a huge block: keep the part around the hunk
            a, b = max(a, i - max_block // 2), min(b, i + max_block // 2)
        spans.append([a, b])
    merged = []
    for a, b in sorted(spans):
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    out, used = [], 0
    for a, b in merged:
        part = "--- lines %d-%d ---\n" % (a + 1, b) + "\n".join("%6d: %s" % (k + 1, src[k]) for k in range(a, b))
        if used + len(part) > max_chars:
            if not out:
                # REG-2018 - a FIRST block over the cap used to leave only this banner: a file "excerpted" with no code.
                # Keep as much of it as fits, around its start, and say it was cut.
                out.append(part[:max_chars])
                out.append("--- (cut: this block alone passed %d characters; the rest is in the diff only) ---" % max_chars)
                break
            out.append("--- (cut: the excerpt reached %d characters; later blocks are in the diff only) ---" % max_chars)
            break
        out.append(part)
        used += len(part)
    return "\n".join(out)


def _hunk_new_lines(sha, path):
    """#259 - the new-side line numbers this look's diff touches in `path`. -> list[int] | None (diff unreadable)"""
    # ⚠ the path goes AFTER the sha: _changes() appends the sha last, so `"--", path` inside it made git read the sha
    # as a second PATH and diff HEAD instead (caught by the first dry run - the excerpt held the stamp line).
    d, _w = _sh(_changes(sha, "-U0") + ["--", path], timeout=60)
    if d is None:
        return None
    got = []
    for m in re.finditer(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", d, re.M):
        start, count = int(m.group(1)), int(m.group(2) if m.group(2) is not None else 1)
        got.extend(range(start, start + max(1, count)))
    return got


def eye_snapshot(sha, max_bytes=None):
    """#169 WIN 2 — GIVE THE EYE THE FILES IT IS REVIEWING, READ-ONLY. -> dict

    His ruling, 2026-09-25: "forget this use the grok cli instead". The eye was run in an EMPTY
    folder on pasted text, so it could not read a line of context around a hunk. This fills
    EYE_CWD with exactly the files the reviewed commit changed, AS THEY STAND AT THAT COMMIT
    (`git archive`, never the live checkout - v3408's reason stands: an agent pointed at the tree
    can edit it, and Grok was caught doing so mid-ship), and makes every entry read-only.
    MEASURED the same day: with an open folder the CLI spends its whole budget exploring
    ("I'll measure ... Next I'll crop ...", rc=142), so the prompt also NAMES the files and says
    not to look further - the instruction bounds it, the folder only makes the reading possible.
    ⚠ Anything left out is NAMED (too large / not in the archive), never silently absent.
    """
    lim = EYE_SNAPSHOT_MAX_BYTES if max_bytes is None else max_bytes
    out = {"ok": False, "included": [], "skipped": [], "why": ""}
    names, why = _sh(_changes(sha, "--name-only") + _pathspec([]), timeout=60)
    if names is None:
        out["why"] = "could not list the %s's files: %s" % ("range" if REVIEW_BASE else "commit", why)
        return out
    want, big = [], []
    for n in [x.strip() for x in names.splitlines() if x.strip()]:
        sz, _w = _sh(["git", "cat-file", "-s", "%s:%s" % (sha, n)], timeout=30)
        try:
            size = int((sz or "").strip())
        except ValueError:
            out["skipped"].append("%s (deleted or not a file at this commit)" % n)
            continue
        if size > lim:
            big.append((n, size))
            continue
        want.append(n)
    if not want and not big:
        out["why"] = "no file of this commit fits the snapshot"
        return out
    tar = b""
    if want:
        tar, why = _sh_bytes(["git", "archive", "--format=tar", sha, "--"] + want, timeout=120)
        if tar is None:
            out["why"] = "git archive failed: %s" % why
            return out
    import tarfile
    _eye_cwd_ready()
    # #259 - an over-limit file goes in as the blocks around its hunks, NAMED as an excerpt, never as nothing.
    excerpts = []
    for n, size in big:
        lines = _hunk_new_lines(sha, n)
        body, _w = _sh(["git", "show", "%s:%s" % (sha, n)], timeout=60)
        text = excerpt_blocks(body or "", lines or [], n.endswith(".py")) if (body and lines) else ""
        if not text:
            out["skipped"].append("%s (%d bytes, over the %d-byte snapshot limit; no excerpt could be cut)" % (n, size, lim))
            continue
        ex = n + ".EXCERPT.txt"
        try:
            os.makedirs(os.path.join(EYE_CWD, os.path.dirname(ex)), exist_ok=True)
            with io.open(os.path.join(EYE_CWD, ex), "w", encoding="utf-8") as fh:
                fh.write("EXCERPT of %s at %s - %d bytes is over the snapshot limit, so these are the blocks around "
                         "its changed lines, numbered as in the file. Anything outside them is NOT here.\n\n%s\n"
                         % (n, sha[:12], size, text))
            excerpts.append(ex)
            out["skipped"].append("%s (%d bytes, over the limit - the blocks around its hunks are in %s)" % (n, size, ex))
        except Exception as e:
            out["skipped"].append("%s (%d bytes, over the limit; the excerpt could not be written: %s)"
                                  % (n, size, type(e).__name__))
    try:
        with tarfile.open(fileobj=io.BytesIO(tar)) if tar else _NoTar() as tf:
            for m in tf.getmembers():
                if not (m.isfile() or m.isdir()) or m.name.startswith("/") or ".." in m.name.split("/"):
                    continue
                tf.extract(m, EYE_CWD)
    except Exception as e:
        out["why"] = "the snapshot could not be unpacked: %s" % str(e)[:120]
        return out
    for _root, _dirs, _files in os.walk(EYE_CWD, topdown=False):
        for _n in _files:
            try:
                os.chmod(os.path.join(_root, _n), 0o444)
            except Exception:
                pass
        for _n in _dirs:
            try:
                os.chmod(os.path.join(_root, _n), 0o555)
            except Exception:
                pass
    out.update(ok=bool(want or excerpts), included=want + excerpts, excerpts=excerpts)
    return out


class _NoTar(object):
    """#259 - a snapshot with only excerpts has no archive to unpack."""

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def getmembers(self):
        return []


def snapshot_note(snap):
    """The sentence the prompt carries about the folder. Empty when there is no snapshot."""
    if not (isinstance(snap, dict) and snap.get("ok") and snap.get("included")):
        return ""
    note = ("\n\nREAD-ONLY CONTEXT: your working folder holds exactly the files this commit changed, "
            "as they stand AT this commit: %s. You may open these files to read the code around a "
            "hunk. Do NOT open anything else, do not run code, do not crop or measure - answer from "
            "what you read." % ", ".join(snap["included"]))
    if snap.get("skipped"):
        note += " Left out of the folder (judge those from the diff only): %s." % "; ".join(snap["skipped"])
    return note


atexit.register(eye_cwd_cleanup)

#: a snapshot folder older than this is stale whoever its name says owns it - no look lives a day, so past it a
#: "live" pid is a REUSED one (heart2's REG-1309 rule, one tool over)
EYE_CWD_STALE_S = 24 * 3600


def _pid_alive(pid):
    if os.name == "nt":                 # REG-1725 - os.kill(pid, 0) is a Ctrl-C there (CTRL_C_EVENT), not a probe
        try:
            import self_prove as _sp
            return _sp.pid_alive(pid)
        except Exception:
            return True                 # cannot ask: a snapshot that may be live is never removed
    try:
        os.kill(int(pid), 0)
        return True
    except PermissionError:
        return True
    except (OSError, ValueError):
        return False


def _on_fatal_signal(signum, _frame):
    """⚠⚠ 2026-09-26 (#243) - A BOUNDED EYE IS A KILLED EYE, AND NEITHER ROPE RUNS UNDER A SIGNAL. eye_cwd_cleanup rides
    a `finally` and atexit; a process killed by SIGALRM (a perl bound) or SIGTERM runs neither. MEASURED: 120
    second_eye_<pid> snapshots (~1.4 MB each) in his temp dir, every owner dead, 93 of them from one day. The signal
    now removes the snapshot, then exits as the signal meant. [[i-own-everything-i-start]]"""
    try:
        eye_cwd_cleanup()
    finally:
        os._exit(128 + int(signum))


def install_cleanup_on_signals():
    """-> the signals now handled. Called by main() only - an importer keeps its own handlers."""
    import signal
    got = []
    for name in ("SIGTERM", "SIGALRM", "SIGHUP"):
        sig = getattr(signal, name, None)
        if sig is None:
            continue
        try:
            signal.signal(sig, _on_fatal_signal)
            got.append(name)
        except (ValueError, OSError):
            continue                       # not the main thread, or not this OS - the ropes above still hold
    return got


def sweep_stale_eye_cwds(tmp=None, now=None):
    """-> [(path, why)] removed: every second_eye_<pid> snapshot whose owner is dead, or a day old whoever it names.
    Never this process's own, never a live owner's younger one (another look, mid-run)."""
    tmp = tmp or tempfile.gettempdir()
    now = time.time() if now is None else now
    gone = []
    try:
        names = os.listdir(tmp)
    except OSError:
        return gone
    for n in sorted(names):
        if not n.startswith("second_eye_"):
            continue
        pid = n[len("second_eye_"):]
        root = os.path.join(tmp, n)
        if not pid.isdigit() or int(pid) == os.getpid() or not os.path.isdir(root):
            continue
        try:
            age = now - os.path.getmtime(root)
        except OSError:
            continue
        if _pid_alive(pid) and age < EYE_CWD_STALE_S:
            continue
        why = ("%.0f h old - no look lives that long" % (age / 3600.0)) if age >= EYE_CWD_STALE_S else ("its owner (pid %s) is dead" % pid)
        if _rm_snapshot(root):
            gone.append((root, why))
    return gone

# A prompt has to fit. Truncation is allowed; SILENT truncation is not — what was dropped is
# reported in the row, so a thin look can never read as a thorough one.
#
# ⚠⚠ v3418 — 9,000 -> 26,000, HIS RULING, 2026-09-22: *"raise the cap to 26000"*. v3299 had left
# the cost with him and #143 had been waiting on exactly this call.
#
# ⚠ AND THE OLD NUMBER'S OWN REASONING HAD EXPIRED. The comment here read: *"24,000 chars timed
# out at 240s and was correctly recorded as an EMPTY SEAT"*. True when written — and measured
# against a 240s bound THAT NO LONGER EXISTS. `EYE_TIMEOUT_S` is 1200 (see above, raised after a
# 22,519-char v3404 payload was killed at 300s), so the evidence for 9,000 was evidence about a
# bound, not about the eye. A comment stating a rule the code no longer follows is worse than no
# comment: it makes the next reader re-derive a conclusion that is already dead.
# [[feedback-comments-vs-code]] [[stale-reading]]
#
# ⚠ WHAT THE COST OF 9,000 ACTUALLY WAS, measured on three versions in one day — at the old cap
# the eye never saw the subject of the change, and at full reach it found real defects every time:
#     v3413   8,622 chars -> cannot-tell, 0 findings   |   25,074 -> 5 findings, 3 real
#     v3414   8,947 chars -> control_ui.html, the file the version is ABOUT, never sent
#     v3417   8,976 chars -> 4 of 5 changed files never sent   |   31,930 -> 7 findings
#
# ⚠ AND 26,000 IS INSIDE WITNESSED TERRITORY, not a guess. The ledger holds SEVEN completed looks
# at >= 26,000 chars, the largest 37,973 (v2824, clean). That is the law the new gate pins: a cap
# may only be a size the eye has actually been SEEN to finish at, so this can never be raised
# blindly into "threshold above the ceiling" — nor lowered back without noticing what it costs.
# [[feedback-threshold-above-the-ceiling]] [[unknown-stays-unknown]]
MAX_FENCE_CHARS = 26000

# ⚠ THAT CEILING BELONGS TO ONE TRANSPORT, NOT TO THE TRUTH. 9,000 is what the CLI can chew in an
# INLINE fence. A file-upload transport is a different pipe with a different ceiling, and holding
# every transport to the narrowest one is why v2806 and v2807 were both looked at through ~32% of
# their diffs — which is how two FALSE high-severity findings got manufactured this session, each
# reasoning correctly about a function my own cap had cut in half.
#
# So the cap is now an ARGUMENT with the CLI's value as its default. It is not raised blindly:
# whatever is actually sent is measured from the bytes and recorded, so a look through a third of
# a diff can never be filed as a look at all of it. [[unknown-stays-unknown]]
def _cap():
    return int(os.environ.get("SECOND_EYE_MAX_CHARS") or MAX_FENCE_CHARS)


COLD_FRAMING = (
    "Code review. The following is a diff of source that has already shipped.\n\n"
    "List concrete defects, ranked by severity, each with the specific scenario in which it "
    "fails. Include races, unreachable states, resource leaks, and any place a caller and a "
    "callee disagree about a contract. If you believe it is correct, say so plainly rather than "
    "inventing a finding.\n\n"
    # ⚠⚠ v3394 — THE READER EXISTED AND NOTHING ASKED FOR THE FIELD. v3376 built
    # `_stated_verdict` to read a DECLARED verdict line precisely so prose would never have to
    # be matched, and its own comment says "the review prompt itself contains the line
    # 1. VERDICT: clean / findings" — but COLD_FRAMING never contained it. A reader with no
    # writer. MEASURED: 35 of 659 findings-rows (v2805..v3391) are answers that DECLARE the
    # change clean in prose and were filed as findings, so agreement(), the eagle rows and the
    # heart are wrong on every one. [[the-unjoined-end]] [[plumbing-with-no-tap]]
    # ⚠ THE ALTERNATIVE WAS REFUSED BY ITS OWN MEASUREMENT. A first-sentence prose rule moved
    # 35 rows with 0 real findings eaten, but #76 measured that widening the prose matcher
    # cannot be made safe and this file says in as many words that prose is never consulted
    # here. Asking for the field is the fix the design already chose.
    # ⚠ ONE verdict word per line: `_stated_verdict` ignores any line naming two or more as a
    # MENU, so an instruction listing the options would defeat itself if echoed.
    # ⚠ THE OPTIONS AND THE FIELD MUST NOT SHARE A LINE. _stated_verdict ignores any line
    # naming two or more verdict words as a MENU, so "VERDICT: clean / findings" - or an
    # instruction phrased that way and echoed back - is discarded. The law caught this on
    # its first run, in the very instruction written to avoid the trap.
    "Choose exactly one of these three words: clean, findings, cannot-tell.\n"
    "Then end your answer with a line naming only that one word, like  VERDICT: <your "
    "choice>  and put nothing else on that line.\n"
)


def _sh(args, timeout=60):
    out, why = _sh_bytes(args, timeout=timeout)
    return (None, why) if out is None else (out.decode("utf-8", "replace"), "")


def _sh_bytes(args, timeout=60):
    """-> (bytes | None, why). The ONE runner: `_sh` decodes it, `eye_snapshot` keeps the tar bytes."""
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO)
    try:
        out, err = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        # ⚠⚠ v3421 — kill() SIGNALS; IT DOES NOT REAP. Found by the second eye reviewing v3420,
        # in the same session a zombie was traced to exactly this shape in the closer loop: the
        # normal path reaps via communicate(), but on THIS path communicate() is what raised, so
        # without a second call the child sits <defunct> for the life of the process. Python's own
        # docs prescribe kill-then-communicate for precisely this.
        p.kill()
        _reap_after_kill(p)
        return None, "timed out after %ss" % timeout
    if p.returncode != 0:
        return None, (err or b"").decode("utf-8", "replace")[:300]
    return out, ""


# ⚠ ANCHORED AT THE START, because the repo stamps a ship as "v2853 — ..." while a follow-up
# says "fix: the v2804 row narrated the catcher". MEASURED over 400 subjects: 252 start with
# a version, 19 merely mention one. The loose form counted v1554 as a ship because a later
# commit talked about it. [[label-outlived-referent]]
# ⚠⚠ v2862 — AND A COMMIT MAY SHIP MORE THAN ONE VERSION. The v2854 anchor was right to
# reject "fix: the v2804 row narrated the catcher" — but it took only the FIRST token, so a
# subject reading "v2859+v2860 — ..." registered v2859 and made v2860 INVISIBLE to the queue.
# MEASURED 2026-09-09: the pre-push gate refused with "v2860 OWES A LOOK" while --backlog
# listed v2861 and v2859 and could not see v2860 at all. Two checks disagreed and the quiet
# one was wrong again, for a NEW reason. [[feedback-contradiction-is-the-finding]]
#
# The LEADING RUN only: v2859+v2860 both count, and a version mentioned later in the same
# subject still does not — which is the protection the anchor was added for.
_VER_LEADING_RUN = re.compile(r"^(v\d{4}(?:\s*[+,&]\s*v\d{4})*)\b")
_VER_TOKEN = re.compile(r"v\d{4}")


#: ⚠⚠ v3316 — A HYPHEN IS A RANGE, AND THIS REPO WRITES ONE. `_VER_LEADING_RUN` accepts `+`, `,`
#: and `&` between versions because v2862 was bitten by "v2859+v2860 — ..." registering only
#: v2859. The SAME defect returned with a hyphen: `0bf8cb6d` is titled "v3304-v3307" and ships
#: FOUR versions, of which the parser saw one — so v3305 and v3306 were invisible to the backlog
#: and shipped with no second-eye look at all. Measured over 200 subjects on origin/main: 1
#: hyphen range, hiding 3 versions.
#:
#: ⚠ THE SEPARATOR MUST NOT EAT THE TITLE. Subjects read "v3312 — the river ..." with a spaced
#: EM-DASH; a range is a bare hyphen-minus with no spaces between two version tokens. Requiring
#: `v\d{4}-v\d{4}` adjacency is what keeps the two apart, and the title case is pinned in the law.
_VER_RANGE = re.compile(r"^v(\d{4})-v(\d{4})\b")


def versions_in_run(subject):
    """Every version a commit subject SHIPS, expanding a range. -> [vNNNN]

    Only the LEADING run counts, which is v2854's protection and it survives unchanged: a subject
    reading "fix: the v2804 row narrated the catcher" ships nothing.
    """
    s = str(subject or "").strip()
    m = _VER_RANGE.match(s)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        # A backwards or absurd range is not a range. Refusing beats inventing 900 versions.
        if b < a or (b - a) > 24:
            return ["v%04d" % a]
        return ["v%04d" % n for n in range(a, b + 1)]
    m = _VER_LEADING_RUN.match(s)
    if not m:
        return []
    out, seen = [], set()
    for tok in _VER_TOKEN.findall(m.group(1)):
        if tok not in seen:
            seen.add(tok)
            out.append(tok)
    return out


def versions_in_history(n=400):
    """Every version stamped by a commit subject, newest first. -> ([version], why)

    ⚠⚠ v2854 — `--backlog` READ THE LEDGER, AND A VERSION WITH NO ROW HAS NOTHING TO READ.
    audit()'s own docstring says its scope out loud: "Every version mentioned in the ledger". A
    version that shipped and was never looked at produces NO row, so the one command whose job is
    "what is stacking up" could not see the single case that matters most — the newest unlooked
    version, which is exactly the one that blocks the next push.

    MEASURED 2026-09-09: `--backlog` reported "3 version(s) owe a look: v2772, v2774, v2776" and did
    not name v2852. I trusted it, pushed v2853, and the gate refused with "v2852 OWES A LOOK —
    nothing was ever recorded for it". Two checks disagreed and the quiet one was wrong.
    [[silence-is-not-evidence]] [[zero-needs-a-denominator]]
    """
    out, why = _sh(["git", "log", "--format=%s", "-%d" % int(n)])
    if out is None:
        return [], why
    seen, vs = set(), []
    for line in out.splitlines():
        # v3316 — ONE parser for "what does this subject ship", so the backlog and any future
        # range-aware gate cannot disagree about it. [[copy-drift]]
        for tok in versions_in_run(line):
            if tok not in seen:
                seen.add(tok)
                vs.append(tok)
    return vs, ""


def _bound_commit(version):
    """The commit TASKS.md says this version shipped as. -> sha | None

    ⚠⚠ v3266 — `bump_version.py` ALREADY WRITES THIS AND NOBODY ASKED IT. Every bump prints
    "bound N version row(s) to a commit" and leaves a row in TASKS.md:

        | **v3265** | `25a6ad2b` | v3265 — HEART: lane_health gains a third state ...

    `commit_for` re-derived the same fact by string-matching COMMIT SUBJECTS, so a version whose
    subject did not happen to contain its own stamp was invisible to its own runner. MEASURED
    2026-09-17: v3265 shipped as *"fix: BLOCKED is not STOPPED — the chronicle lane was never
    stopped"*, which names the defect and not the version, and `second_eye_run v3265` answered
    "no commit subject names v3265 in the last 400". The look could not be taken, so the NEXT
    push would have been refused at the gate for a version that was sitting right there, bound,
    in a file written by the tool that stamped it. Two halves of one fact, never joined.
    [[the-unjoined-end]] [[copy-drift]]
    """
    path = os.path.join(REPO, "TASKS.md")
    try:
        with io.open(path, encoding="utf-8") as fh:
            body = fh.read()
    except Exception:
        return None
    return _sha_named_by_tasks(version, body)


# The bump writes the newest row as `(this commit)` because that commit does not exist yet, and the
# next bump is what replaces it. Until then a subject scan cannot see the ship: subjects must not
# lead with the version. MEASURED 2026-10-27: v3805's row was still `(this commit)`, its subject is
# "Stamp the auto intake move", and the runner refused with "cannot find the commit".
_STAMP_ADDED = re.compile(r'^\+VERSION = "(v\d{4})"')


def _sha_named_by_tasks(version, body):
    """The sha cell, or the stamp commit when the cell is still `(this commit)`. -> sha | None"""
    m = re.search(r"\|\s*\*\*%s\*\*\s*\|\s*`([0-9a-f]{7,40})`" % re.escape(version), body)
    if m:
        return m.group(1)
    if re.search(r"\|\s*\*\*%s\*\*\s*\|\s*`\(this commit\)`" % re.escape(version), body):
        return _sha_from_version_stamp(version)
    return None


def _sha_from_version_stamp(version):
    """Newest commit that added this version's VERSION line in tv/tv_diablo.py. None if that is not shown.

    Same added line stamp_versions.version_commits reads, asked for one version. A commit that only
    drops the line, or mentions it, is not the ship.
    """
    if not re.fullmatch(r"v\d{4}", str(version or "")):
        return None
    needle = 'VERSION = "%s"' % version
    out, _why = _sh(["git", "log", "--format=%H", "-S", needle, "--", "tv/tv_diablo.py"], timeout=60)
    if not out:
        return None
    for sha in out.splitlines():
        sha = sha.strip()
        if not re.fullmatch(r"[0-9a-f]{7,40}", sha):
            continue
        diff, _dw = _sh(["git", "show", "--format=", "--unified=0", sha, "--", "tv/tv_diablo.py"], timeout=60)
        if diff is None:
            return None
        for line in diff.splitlines():
            added = _STAMP_ADDED.match(line)
            if added and added.group(1) == version:
                return sha
    return None


def commit_for(version):
    """The commit that shipped this version. -> (sha | None, why)

    Asks the BINDING first (see _bound_commit), then falls back to scanning subjects — a repo
    without a TASKS.md row still works exactly as it did.
    """
    bound = _bound_commit(version)
    if bound:
        # ⚠ trust it only if the object actually exists; a stale or hand-edited row must not
        # send the runner at a sha that is not there. [[unknown-stays-unknown]]
        _ok, _ = _sh(["git", "cat-file", "-e", "%s^{commit}" % bound])
        if _ok is not None:
            return bound, ""
    out, why = _sh(["git", "log", "--format=%H %s", "-400"])
    if out is None:
        return None, why
    # ⚠⚠ 2026-09-26 — A SUBJECT THAT MENTIONS A VERSION DID NOT SHIP IT. This matched `\bvNNNN\b` ANYWHERE, so with
    # v3511's row still `(this commit)` the runner took "ledger: the self-arming rows the v3511 gate set recorded" -
    # the commit AFTER the ship - and built a 1-character payload for it. Measured over the last 400 subjects: "merge:
    # ... onto v3508", "fix: two v3494 contract holes", "re-bless ... after v3480" would each be taken the same way.
    # versions_in_run() already answers "which versions does this commit SHIP" (the leading run, ranges expanded, a
    # mid-subject mention ships nothing) - one rule, not two. [[copy-drift]] [[a-presence-law-is-not-a-reachability-law]]
    for line in out.splitlines():
        sha, _, subject = line.partition(" ")
        if version in versions_in_run(subject):
            return sha, ""
    return None, ("no TASKS.md row binds %s to a commit, and no commit subject SHIPS it (its leading version run) in "
                  "the last 400 - a subject that only mentions it is not its ship" % version)


#: ⚠⚠ 2026-09-27 — A BATCH BUILT ON AN INTEGRATION BRANCH SHIPS ITS CODE IN COMMITS THE BUMP DOES NOT CARRY.
#: v3515-v3517 were built in worktrees, merged, then stamped as three bump-only commits. The bound commit
#: for v3517 (1abddaf2) is 2,692 chars of version strings, so the eye answered cannot-tell - correctly -
#: and re-asking it could only ever answer the same. `--base REV` widens the look to every change between
#: REV and the bound commit (`git diff REV sha`), and the row says so; without it nothing changes.
REVIEW_BASE = None
#: v3897 (REG-3699, card #196) - a FOLLOW-UP look names its files (`--files`): only those paths, *.html included, so a file
#: the budget dropped from a version's look can be shown on its own. None: the version's whole change, as before.
REVIEW_FILES = None


def _pathspec(default):
    """v3897 (REG-3699) - the git pathspec a look reads: the named files of a follow-up look, else `default`. -> list"""
    return (["--"] + list(REVIEW_FILES)) if REVIEW_FILES else list(default)
#: ⚠⚠ v3526 (#42) — AND WITHOUT --base EVERY VERSION WAS LOOKED AT THROUGH ITS BUMP ALONE. v3523, v3524 and v3525 each
#: came back cannot-tell on their first ask (a bump commit is version strings), and a re-ask only gambles on the same
#: keyhole. v3525 with `--base 47a5ac37` returned FIVE findings, four of them real. So the default look is now the
#: version's own range — from the commit that shipped the version before it — and `--bump-only` keeps the old keyhole.
BUMP_ONLY = False


def _default_base(version, sha):
    """The commit that shipped the PREVIOUS version, when it is an ancestor of `sha`. -> (sha | None, why)."""
    try:
        n = int(str(version)[1:])
    except (TypeError, ValueError):
        return None, "the version is not vNNNN, so the version before it is UNKNOWN"
    prev = "v%d" % (n - 1)
    psha, pwhy = commit_for(prev)
    if not psha:
        return None, "the commit that shipped %s was not found (%s)" % (prev, pwhy)
    _full, _fw = _sh(["git", "rev-parse", "--verify", "%s^{commit}" % psha], timeout=30)
    if not _full:
        return None, "%s's commit %s does not resolve (%s)" % (prev, psha, _fw)
    psha = _full.strip()
    _anc, _aw = _sh(["git", "merge-base", "--is-ancestor", psha, sha], timeout=30)
    if _anc is None:
        return None, "%s's commit %s is not an ancestor of %s (%s)" % (prev, psha[:8], sha[:8], _aw)
    return psha, "%s..%s — every change since %s shipped" % (psha[:8], sha[:8], prev)


def _first_parent_of_merge(sha):
    """The first parent when `sha` is a MERGE, else None (and None when git cannot say).

    2026-09-28 - two #231 rows on merge commits (e81dde8f, 44f6b389) read "cannot-tell, chars 0, git show
    combined diff is empty". `git show` prints a COMBINED diff for a merge, which is empty whenever the merge
    was clean - so the eye was handed nothing and could only answer cannot-tell, while the merge carried
    bible.html, control_app.py and six more files onto main. What a merge brings onto its line is its
    first-parent diff."""
    out, _why = _sh(["git", "rev-list", "--parents", "-n", "1", sha], timeout=20)
    parts = (out or "").split()
    # only a real answer counts: every token a full commit id. Anything else (an error, a stub, a
    # diff) says nothing about parents, and the plain `git show` path stands.
    if len(parts) > 2 and all(re.match(r"^[0-9a-f]{40}$", x) for x in parts):
        return parts[1]
    return None


def _changes(sha, *tail):
    """The git argv for "what this look covers": the bound commit alone, or REVIEW_BASE..sha.
    A merge commit alone is its first-parent diff (what it brought onto main), never git show's
    combined diff, which is empty for a clean merge."""
    if REVIEW_BASE:
        return ["git", "diff"] + [t for t in tail if t != "--format="] + [REVIEW_BASE, sha]
    _fp = _first_parent_of_merge(sha)
    if _fp:
        return ["git", "diff"] + [t for t in tail if t != "--format="] + [_fp, sha]
    return ["git", "show", "--format="] + [t for t in tail if t != "--format="] + [sha]


_PY_COMMENT = re.compile(r"^\s*#")
_JS_COMMENT = re.compile(r"^\s*(/\*|\*|//)")


# ⚠⚠ v3375 — THE ROSTER OF EVERY TRANSFORMATION `payload_for` APPLIES TO THE BODY BEFORE THE CAP.
# Each entry MUST be counted in `_stripped` and MUST get its own conditional declaration in the
# header, and `test_a_payload_names_what_it_left_out.py` checks all three against each other. A
# strip added without an entry here is a reach reduction the eye is never told about — which is
# exactly what the ship-note strip was for 15 versions. [[the-unjoined-end]]
_STRIPS_APPLIED = ("comments", "notes")


def _strip_comments(diff):
    """Drop comment-only ADDED lines. The code still reads; the author's account of it does not.

    ⚠⚠ v3203 — IT DROPPED THE OPENER AND KEPT THE BODY, AND THAT MANUFACTURED A P1.
    MEASURED 2026-09-16 on the v3201 look. Grok returned a fatal finding: *"the edit inserts a
    block of explanatory prose directly into the JavaScript source without an opening `/*` ...
    the resulting string is not syntactically valid JS."* It was reading the payload correctly.
    The FILE is fine — `js_syntax_gate.py` parses it in a real JS engine — and the real diff
    carried 4 added lines with the warning glyph while the payload carried 1.

    THE MECHANISM: the old loop matched each added line against `_JS_COMMENT` INDEPENDENTLY. This
    codebase writes block comments as

        /* ⚠⚠ TITLE — first line
           continuation prose with NO leading asterisk
           ... */

    so the opener matched and was dropped, and every continuation line did not match and was
    KEPT. The eye was then handed orphaned prose sitting in the middle of executable code — a
    syntax error the transport invented. That is not a one-off: it is EVERY multi-line block
    comment in this repo, on EVERY look this instrument has ever done, including the ones it
    called clean. An instrument that corrupts its own input has no verdict worth the name.
    [[feedback-suspect-the-instrument]] [[unknown-stays-unknown]]

    ⚠ THE STATE RESETS AT EVERY HUNK AND FILE BOUNDARY. A diff shows hunks, so a block comment
    can be opened inside one and closed in a part that is not shown; without a reset an unclosed
    opener would swallow the whole remainder of the payload — trading manufactured findings for
    silently missing code, which is the worse direction.
    """
    keep = []
    in_block = False
    for ln in diff.splitlines():
        # continuity is only claimable inside one hunk of one file
        if ln.startswith("diff --git") or ln.startswith("@@") or ln.startswith("+++") \
                or ln.startswith("---"):
            in_block = False
            keep.append(ln)
            continue
        if ln.startswith("+"):
            body = ln[1:]
            if in_block:
                if "*/" in body:
                    in_block = False
                    tail = body.split("*/", 1)[1]
                    if tail.strip():          # real code sharing the closing line survives
                        keep.append("+" + tail)
                continue
            if _PY_COMMENT.match(body) or _JS_COMMENT.match(body) or not body.strip():
                if _opens_block(body):
                    in_block = True
                continue
            if _opens_block(body):            # code, then a block comment that runs on
                head = body.split("/*", 1)[0]
                in_block = True
                if head.strip():
                    keep.append("+" + head)
                continue
        keep.append(ln)
    return "\n".join(keep)


def _opens_block(body):
    """Does this line open a /* block that does NOT close on the same line?"""
    i = body.find("/*")
    return i >= 0 and "*/" not in body[i + 2:]


def uncovered_commits(sha):
    """-> list of "sha subject" lines that ship WITH `sha` but are NOT in its payload, or None.

    ⚠⚠ v3299 — THE LOOK COVERS ONE COMMIT AND THE PUSH CARRIES MANY. `payload_for` runs
    `git show <sha>` on the single commit that carries the version stamp, so every `fix:` commit
    landing after the bump and before the push is NEVER SEEN BY ANY EYE — while the row that lands
    reads as though the push was reviewed.

    MEASURED 2026-09-18 on v3298: FOUR commits shipped in one push and the eye saw ONE. The unseen
    three included the membership discriminator, which took THREE cuts (two of them wrong) and was
    the most consequential change in the push. The verdict then attacked `_fnew > _dm + 0.5` — code
    SUPERSEDED two commits later. That is not the eye being wrong; it is the gate handing it bytes
    that no longer ship.

    ⚠ None means "the range could not be listed", which is UNKNOWN and must never be rendered as
    "nothing was missed". An empty list means MEASURED-AND-NONE. Those are different facts and the
    caller must not collapse them. [[zero-needs-a-denominator]] [[source-reading-guard]]
    """
    out, _why = _sh(["git", "log", "--oneline", "%s..HEAD" % sha], timeout=30)
    if out is None:
        return None
    return [l.strip() for l in out.splitlines() if l.strip()]


def absent_from(sha, body):
    """-> (absent, why). Which of `sha`'s changed code files are NOT present in `body`.

    THREE STATES, and collapsing any two is the defect this exists to prevent:
        a LIST  -> these changed files never reached the eye at all
        []      -> MEASURED AND NONE: every changed code file is in the payload
        None    -> the roster could not be read; UNKNOWN, never "nothing was missed"

    ⚠ THE ROSTER COMES FROM GIT, NEVER FROM WHAT WAS FETCHED. When the python diff alone already
    exceeds the cap, payload_for never runs the *.html show — so a dropped .html is not missing
    from any buffer to compare against, it is missing from the QUESTION. Deriving this from the
    fetched text would report 0 for exactly the v3333 case that prompted it.
    [[unknown-stays-unknown]] [[the-unjoined-end]]
    """
    names, why = _sh(_changes(sha, "--name-only") +
                     _pathspec(["--", "*.py", "*.js", "*.mjs", "*.sh", "*.html",
                                ":(exclude)_archive/*"]), timeout=90)
    if names is None:
        return None, (why or "the changed-file roster could not be read")
    sent = set(re.findall(r"(?m)^diff --git a/(\S+)", body or ""))
    return [f for f in (l.strip() for l in names.splitlines()) if f and f not in sent], ""


#: a `why=` in run_gates.py is a SHIP NOTE — prose wearing code's clothes. `_strip_comments`
#: cannot touch it because it is a string LITERAL, so the eye pays full price for it out of a
#: budget that truncates. MEASURED over the last 24 versions: run_gates.py took 31.5% of v3354's
#: whole payload and the file that version exists to change reached 0% of it.
#: ⚠⚠ NO PARENTHESES IN THIS PATTERN, AND THE LAW CAUGHT WHY ON ITS FIRST RUN. The first cut
#: allowed an optional `(` before the chunks and an optional `)` after them, and on
#: `why="a one line note"),` it ATE THE CLOSING PAREN — handing the eye a diff whose `Gate(...)`
#: call no longer closes. Mangling registration structure is the `gate_insert_missing_comma`
#: family, and the file-header count I measured with could not see it: a broken diff still has
#: its `diff --git` lines. The pattern now touches the `why=` and its string chunks and nothing
#: else; a parenthesised note is simply left alone, which costs reach and cannot cost correctness.
_WHY_NOTE_RX = re.compile(
    r'why=\s*(?:"(?:[^"\\]|\\.)*"\s*|\'(?:[^\'\\]|\\.)*\'\s*)+', re.S)


def _strip_ship_notes(diff):
    """Replace every `why=` ship note in a diff with a stub, KEEPING THE LINE COUNT.

    ⚠⚠ THE NEWLINES ARE THE WHOLE TRICK, AND MY FIRST CUT LOST THEM. Collapsing a multi-line
    `why=` onto one line pulls the NEXT `diff --git` off the start of its own line, and every
    line-anchored reader — including the one measuring whether this change helps — stops seeing
    that file. That instrument reported the strip making THREE versions blinder; with the line
    count preserved the same measurement says 65 missed files -> 58 over 24 versions, 6 better
    and ZERO worse. The regression was mine, in the measuring tool, not in the idea.
    [[feedback-suspect-the-instrument]] [[source-reading-guard]]

    ⚠ ONLY THE NOTE. The `Gate(...)` registrations around it are real code — a missing separating
    comma there is a live defect class in this repo — so nothing else in run_gates.py is touched.

    ⚠⚠ AND IT REMOVES LESS THAN IT LOOKS LIKE, STATED SO THE NUMBER IS NOT OVER-READ. In a DIFF
    every continuation line begins with `+`, `-` or a space, and the pattern's `\\s*` cannot cross
    that marker — so a note spanning five lines loses its FIRST quoted chunk and keeps the rest.
    That is deliberate: widening the pattern to eat `^[+- ]\\s*"..."` would start eating ordinary
    string literals in ordinary code, and the 65 -> 58 measurement above is of THIS narrow form,
    not of a fuller one. A wider strip needs its own measurement before it is worth anything.

    ⚠⚠⚠ SCOPED TO run_gates.py, AND THE CROSS-FAMILY EYE FOUND WHY ON v3360 — a real defect I
    shipped. `why=` is a ship note ONLY in run_gates.py. MEASURED across tv/*.py: 188 occurrences
    sit outside any `Gate(` call, and many are live message strings — `why="boot"`,
    `why="a session ended"`, `why="disk too full"`, `why="the second-family CLI is not installed
    here"`. Stripping those replaces the very bytes a version about wording exists to change, and
    hands the eye a stub in place of the subject. That is the defect this whole area exists to
    prevent, re-created by the fix for it. So the strip walks the diff FILE BY FILE and only
    touches the run_gates.py hunks. [[the-unjoined-end]] [[sweep-dont-ask]]

    ⚠ The eye's other two findings on the same diff were REFUTED by measurement and are recorded
    so nobody re-derives them: it said the replacement drops newlines (the shipped `_repl` appends
    `"\n" * m.group(0).count("\n")`, verified 4 -> 4) and that the strip is a no-op after
    `_strip_comments` (measured on v3360's own payload: 18,647 -> 11,433 chars, 7,214 removed).
    It was judging a TRUNCATED payload that cut the replacement line.
    """
    def _repl(m):
        return 'why="<ship note stripped for the eye>"' + "\n" * m.group(0).count("\n")
    d = diff or ""
    out, i = [], 0
    for path, a, b in _file_sections(d):
        out.append(d[i:a])
        hunk = d[a:b]
        out.append(_WHY_NOTE_RX.sub(_repl, hunk) if path.endswith("run_gates.py") else hunk)
        i = b
    out.append(d[i:])
    return "".join(out)


def _file_sections(diff):
    """-> [(path, start, end)] over a diff's OWN `diff --git a/<path>` headers.

    v3363 - ONE WALK, TWO READERS. `_strip_ship_notes` already walked the diff file by file, and
    `reach_of` below needs the identical boundaries. Two copies of a boundary rule disagree the
    day one is edited, and this particular rule is subtle enough to have been got wrong once
    already: the end of a file's section is the NEXT header's line start, not the match start,
    and a section that runs to EOF has no next header at all. [[copy-drift]]
    """
    d = diff or ""
    outs = []
    for m in re.finditer(r"(?m)^diff --git a/(\S+)", d):
        j = d.find("\ndiff --git a/", m.start())
        outs.append((m.group(1), m.start(), len(d) if j < 0 else j + 1))
    return outs


def reach_of(full_body, final_body):
    """-> {path: {"got": int, "total": int}} | None. How much of each ARRIVED file the eye got.

    ⚠⚠ THIS IS A DIFFERENT QUESTION FROM `absent_from`, AND THAT GAP IS THE WHOLE DEFECT.
    `absent` answers "did this file reach the payload at all", measured by the presence of its
    `diff --git` header. Truncation cuts MID-FILE, so a file whose header arrived and whose body
    was chopped is `absent`-clean and unread. Every reach check built before this says it was
    seen.

    MEASURED 2026-09-19 WITH THIS FUNCTION over 16 versions. 67 files ARRIVED; 8 of them arrived
    under half their bytes:
        v3356  bible.html                                        259 /  8,629    3.0%
        v3349  test_a_partial_look_is_not_agreement.py           428 / 11,337    3.8%
        v3350  test_the_shelf_tabs_are_the_real_sessions.py      196 /  3,406    5.8%
        v3358  test_the_shelf_shows_reels_before_analysis.py   1,224 / 12,586    9.7%
        v3348  visual_lock_invariant.py                           64 /    516   12.4%
        v3352  test_the_shelf_tabs_are_the_real_sessions.py    1,464 /  5,915   24.8%
        v3347  prune_wilson.py                                 8,318 / 27,748   30.0%
        v3354  second_eye_ledger.py                            3,499 /  7,200   48.6%

    ⚠⚠ v3354 IS THE ROW THAT SETTLES IT. `second_eye_ledger.py` is the file that version exists
    to change; its header arrived, so the row was filed `blind_to: []` and `verdict: clean` while
    the eye held under half of its subject. v3361 did the same: the answer's OWN first line read
    "REACH: 19/92 hunks" and the row said clean.

    ⚠ THE FRACTION IS STORED, NEVER A BOOLEAN AGAINST A BAKED CONSTANT. A hardcoded 0.5 here
    would be a bar nobody measured and nobody can move - the shape of the $5 he corrected me on
    and of the 0.22 threshold that sat above a signal maxing at 0.133. Store got/total; let the
    reader decide and let the bar be tuned once there are rows to tune it against.
    [[feedback-threshold-above-the-ceiling]]

    THREE STATES, and collapsing any two is the defect this exists to prevent:
        a DICT  -> measured; compare got against total per file
        None    -> the full body could not be established; UNKNOWN, never "all complete"
    A file present in `final` but not in `full` cannot happen (final is a prefix of full) and is
    recorded at its own length rather than silently dropped, so an instrument fault shows up as
    got > total instead of disappearing.
    """
    if full_body is None or final_body is None:
        return None
    full = {}
    for path, a, b in _file_sections(full_body):
        full[path] = full.get(path, 0) + (b - a)
    if not full:
        return None
    got = {}
    for path, a, b in _file_sections(final_body):
        got[path] = got.get(path, 0) + (b - a)
    # ⚠⚠ A FILE WITH ZERO BYTES HERE DID NOT *ARRIVE SHORT* — IT DID NOT ARRIVE, and
    # `absent_from` already names it. Including those made this counter 71% NOISE the first time
    # it was pointed at real data: 41 of 100 files flagged over 16 versions, 33 of them at exactly
    # 0.0%, every one already in the row's `absent` list. That is v3354's defect - a warning that
    # fires on most rows is furniture - re-created two versions after I fixed it, and only a
    # measurement against his real history caught it. The fixture could not: a fixture built to
    # show a half-cut file has no wholly-cut file in it. [[regression-guard]] §5
    # So `reach` answers exactly one question: OF THE FILES THAT ARRIVED, how much arrived.
    # {} is therefore MEASURED-AND-NONE-ARRIVED (and `absent` carries them), which is still a
    # different state from None = nobody could measure.
    return dict((p, {"got": int(got[p]), "total": int(n)})
                for p, n in full.items() if int(got.get(p, 0)) > 0)



# ── v3370 (#116) — THE BUDGET IS SHARED, NOT SPENT ALPHABETICALLY ───────────────────────────
# MEASURED on v3368: the admitted set was EXACTLY sorted(changed files)[:5]. Nothing weighed
# relevance, size or risk — git's default sort decided who got reviewed, so the files late in the
# alphabet were never reviewed at all. TWENTY-THREE engine files sort behind all 460 tv/test_*.py,
# and they are the whole vault lane plus tree_busy, tv_diablo, unknown_age, verdict_provenance,
# window_visibility, write_census, write_witness.
#
# The feedback loop made it worse: the standing order is JOIN -> GATE -> HEART -> BANK, so nearly
# every version adds a large new tv/test_*.py, which alphabetically lands AHEAD of the engine it
# protects and pushes it past the cap. The law crowded out its own subject. v3368 lost
# vault_retro.py and tv_diablo.py — its entire fix — and the eye said so itself: "the only consumer
# of the three new fields is the new doctor check; its producer lives in the missing files."
#
# MEASURED over 30 real versions / 182 changed code files:
#     alphabetical prefix (before)    68/182  37.4%   median cov   -    slivers <15%:  0
#     engine-first ordering           74/182  40.7%                     <- refuted, barely moves
#     fair share, no floor           182/182 100.0%   median cov  66%   slivers <15%: 26
#     fair share, floor 1500         151/182  83.0%   median cov 100%   slivers <15%:  1
#
# ⚠⚠ THE NO-FLOOR VARIANT IS A TRAP, AND THIS FILE ALREADY RECORDS WHY. v2803: the payload ended
# at `+    return ` and the eye returned TWO high-severity defects about a function whose last two
# characters the cap had removed. v2850: `drift` reported as never declared, when the declaration
# sat above the first changed line. A SLIVER OF A FILE DOES NOT MERELY FAIL TO HELP — IT
# MANUFACTURES FINDINGS, and each false one has to be chased and refuted by hand. So a file gets a
# USEFUL slice or none at all, and the ones that get none are named by the v3341 mechanism.
MIN_USEFUL_SLICE = 1500


def _share_the_budget(body, cap):
    """-> (body, cut_note, absent_extra). Every file gets a useful slice of the cap, or none.

    Max-min fair: the smallest diffs complete cheaply and donate what they do not need. When the
    remaining pool cannot give everyone a USEFUL slice, the largest file is dropped rather than
    everyone being shaved into slivers — a partial file the eye can reason about beats several it
    cannot.
    """
    secs = _file_sections(body)
    if len(secs) < 2:
        cut = body.rfind("\n", 0, cap)
        return body[:cut if cut > 0 else cap], None, []
    sized = [(p, a, b, b - a) for p, a, b in secs]
    # ⚠ THE PREAMBLE COMES OUT OF THE POOL. Anything before the first `diff --git` is emitted
    # below, so leaving it out of the accounting lets the ONE promise this function makes — the
    # cap — be exceeded by however many leading bytes happen to be there. Measured by a
    # cross-family review of v3370: cap 5000, a 361-char preamble, 5319 chars returned.
    lead = sized[0][1]
    take, pool, cand = {}, max(0, cap - lead), sorted(sized, key=lambda x: x[3])
    while cand:
        share = pool // len(cand)
        if share < MIN_USEFUL_SLICE:
            cand.pop()                      # cannot serve everyone usefully; drop the largest
            continue
        p, a, b, n = cand[0]
        if n <= share:
            take[p] = n; pool -= n; cand.pop(0); continue
        for p, a, b, n in cand:
            take[p] = share
        break
    out, cuts, absent = [], [], []
    if lead > 0:
        # ⚠ NO SEPARATE EMISSION BOUND HERE, AND THAT IS DELIBERATE — I WROTE ONE AND MEASURED IT
        # DEAD. A cross-family review of v3372 was right that the preamble could escape the cap, so
        # the first fix cut it to `cap` here. Its red-proof then came back BLIND with a correct
        # match count, which by the taxonomy means the SUBJECT is inert, not the law — and it is:
        # when lead >= cap the pool is 0, every file starves, the body carries no `diff --git`, and
        # the code-free refusal below returns "" regardless. 108 shapes measured, 0 exceeding the
        # cap either way. The branch could only ever trim a body about to be discarded.
        #
        # Dead code behind a proof that proves nothing is worse than no code — that is the inert
        # red-proof scar. ONE fix closes both findings, and it is the refusal below.
        out.append(body[:lead])
    for p, a, b, n in sized:                # ORIGINAL order on the wire, not the allocation order
        want = int(take.get(p, 0))
        if want <= 0:
            absent.append(p); continue
        seg = body[a:b]
        if want < n:
            # ⚠ LINE BOUNDARY, same as the single cut it replaces — a mid-statement cut is what
            # manufactured the v2803 findings.
            #
            # ⚠⚠ AND THE SLICE MUST KEEP ITS TRAILING NEWLINE. Cutting BEFORE it leaves the next
            # file header appended to a half-line, so `diff --git` is no longer at line start: the
            # two files merge on the wire and the second becomes INVISIBLE to the eye and to every
            # parser downstream, including the absent-file accounting. Caught by re-parsing this
            # function own output and finding vault_retro.py missing while the note claimed 45%.
            # ⚠ `>= 0`, NOT `> 0`, AND NO UNTERMINATED FALLBACK. When there is no newline in the
            # first `want` bytes, seg[:want] does not end on a line boundary, so the NEXT file's
            # `diff --git` header lands mid-line and stops being a header: the two files merge and
            # the second disappears from the payload AND from `absent`, which is the exact defect
            # this function exists to remove. Reproduced on a section whose header is followed by
            # one unbroken 40,000-char line — tv/two.py vanished entirely and was never named.
            # An empty slice falls through to the floor below, which drops and NAMES it.
            c = seg.rfind("\n", 0, want)
            seg = seg[:c + 1] if c >= 0 else ""
            # ⚠ A LINE-BOUNDARY CUT CAN COLLAPSE. WINDOWS_SHIP.json is one long line, so the cut
            # landed at 6% of it — a sliver, which is what the floor exists to prevent. Judge the
            # slice AFTER the cut, not by the share that was allocated, and drop it if it is not
            # useful. An absent file is named; a sliver manufactures findings.
            if len(seg) < MIN_USEFUL_SLICE:
                absent.append(p); continue
            cuts.append("%s %d%%" % (p, int(round(100.0 * len(seg) / float(n)))))
        out.append(seg)
    note = None
    if cuts:
        note = "shown in part: %s" % ", ".join(cuts)
    body_out = "".join(out)
    # ⚠ A PAYLOAD WITH NO CODE IS NOT A SMALL LOOK, IT IS NO LOOK. When the preamble alone eats
    # the cap, every file starves into `absent` and what remains is context with nothing to review
    # — measured cap=1600 -> 361 chars, 0 files emitted, 2 named absent. The accounting stays
    # truthful, but paying an eye to read it can only produce a confident nothing, so return an
    # empty body and let the caller's existing `sent["chars"] == 0` refusal fire.
    if not SER_has_any_section(body_out):
        return "", note, absent
    return body_out, note, absent


def SER_has_any_section(body):
    """-> True when at least one `diff --git` header survived into the emitted body."""
    return bool(_file_sections(body))


def payload_for(sha):
    """-> (prompt, dropped_note, absent, reach, stripped). Code only, strips declared."""
    # ⚠ PYTHON FIRST, and the reason is measurable: control_ui.html diffs in this repo run to tens
    # of thousands of characters that are largely prose, so a single combined diff spends the whole
    # budget on comments the stripper cannot remove (they sit inside string literals and JS block
    # comments spanning lines) and the eye never reaches the logic. Ask for the code first.
    # ⚠⚠ v3388 — `*.js` WAS NEVER HERE, AND THE EYE ITSELF FOUND IT. Reviewing v3387 — a
    # version whose entire subject is two Cloudflare function files — it answered: "Also absent:
    # any Cloudflare worker / functions code that actually performs the lastseen/webseen lookup,
    # key matching, throttling, null-handling". MEASURED on that payload: webSeenSlug 0,
    # recordWebSeen 0, _fleetSeen 0, webOnly 0. functions/_middleware.js appeared ZERO times and
    # was not even listed as omitted, because a file excluded by the pathspec is never a
    # candidate to be reported missing — a false NEGATIVE in the instrument v3341 and v3354 built
    # to catch exactly this. `*.mjs` was here; the plain extension never was.
    # ⚠ _archive/ is excluded with it: 67 tracked .js, the bulk archived build chunks under
    # _archive/phase_z_20260715/assets/. 0 of the last 60 versions touch that tree, so the
    # exclusion is a measured no-op today and a guard against one archived rebuild flooding a
    # payload and starving the real files — the failure v3370 fixed for the allocator.
    # ⚠ BLAST RADIUS IS SMALL AND STATED: 1 of the last 60 versions had an unseen .js change, and
    # it is v3387. My first count said 60 of 60; that was my own broken loop, not the defect.
    # [[the-unjoined-end]] [[zero-needs-a-denominator]] [[feedback-suspect-the-instrument]]
    out, why = _sh(_changes(sha, "--unified=3") +
                   _pathspec(["--", "*.py", "*.js", "*.mjs", "*.sh",
                              ":(exclude)_archive/*"]), timeout=90)
    if out is None:
        return None, why
    # ⚠⚠ v3360 — THE SHIP NOTES GO BEFORE THE CAP DOES. run_gates.py carries one `why=` per gate
    # and each is a paragraph of prose the eye never needs to review; `_strip_comments` cannot
    # reach them because they are string LITERALS. MEASURED on v3354: corroborate.py 59.3%,
    # run_gates.py 31.5%, control_app.py 9.2% — and tv/second_eye_ledger.py, the file that version
    # exists to change, got 0%. Over the last 24 versions this recovers 7 changed files that never
    # reached the eye (65 missed -> 58), 6 versions better and none worse.
    # ⚠ It does NOT widen the cap. v3299 ruled that cost is HIS; this only stops spending the
    # budget on prose. [[the-unjoined-end]]
    # ⚠⚠ v3375 — AND EVERY STRIP IS COUNTED AS IT IS APPLIED, because the header has to declare
    # it and a declaration nobody measured is prose. `_STRIPS_APPLIED` is the roster the law
    # checks against: adding a third stripper without an entry here is a reach reduction the eye
    # is never told about. [[the-unjoined-end]] [[unknown-stays-unknown]]
    _stripped = dict((_k, 0) for _k in _STRIPS_APPLIED)

    def _prep(_raw):
        # ⚠⚠ THE DELTA IS TAKEN ON rstrip("\n") BOTH SIDES, AND MY OWN FIXTURE CAUGHT WHY.
        # `_strip_comments` ends `return "\n".join(keep)`: splitlines() drops the trailing
        # newline and the join never restores it, so a diff with NO comments in it still came
        # back exactly 1 character shorter. A bare `if _stripped["comments"]` would then have
        # declared a comment strip on every payload ever built, including the ones where nothing
        # was stripped — a false statement about THIS payload, which is the defect one door down
        # from the one this version exists to fix. [[unknown-stays-unknown]]
        _c = _strip_comments(_raw)
        _n = _strip_ship_notes(_c)
        _stripped["comments"] += len(_raw.rstrip("\n")) - len(_c.rstrip("\n"))
        _stripped["notes"] += len(_c.rstrip("\n")) - len(_n.rstrip("\n"))
        return _n

    body = _prep(out)
    _full_len_holder = [body]
    if len(body) < _cap() and not REVIEW_FILES:       # v3897 (REG-3699) - a follow-up look already named its html
        _more, _ = _sh(_changes(sha, "--unified=3") + ["--", "*.html"],
                       timeout=90)
        if _more:
            body = body + "\n" + _prep(_more)
    _full_len_holder = [body]
    dropped = ""
    if len(body) > _cap():
        # ⚠⚠ CUT ON A LINE BOUNDARY, AND SAY SO IN THE PROMPT — because a mid-statement cut
        # MANUFACTURES FINDINGS. Measured on v2803: the payload ended at exactly `+    return `
        # and the eye returned TWO high-severity defects — "gate_files() returns None on every
        # execution", "the documented contract is violated" — reasoning correctly about a
        # function whose last two characters my own cap had removed. The real line is
        # `return out` and it returns 247 gates.
        #
        # The record already declared the truncation, which is the only reason it was caught. But
        # a declaration in the LEDGER does not help the EYE: it was never told, so it treated an
        # artefact of the transport as a defect in the code. An instrument that fabricates
        # findings costs more than one that finds nothing, because each false one has to be
        # chased down and refuted by hand. [[feedback-suspect-the-instrument]]
        body, _cut_note, _cut_absent = _share_the_budget(body, _cap())
        dropped = ("shared %d of %d diff chars across the changed files, each cut at a line "
                   "boundary" % (len(body), len(_full_len_holder[0])))
        if _cut_note:
            dropped += " — " + _cut_note
    # ⚠⚠ v2851 — THE SCOPE WARNING BELONGS ON EVERY DIFF, NOT ONLY A TRUNCATED ONE.
    # It used to live entirely inside `if dropped:`. But a diff is ALWAYS partial — it shows
    # HUNKS, never whole functions — so a complete, untruncated diff invites the same false
    # finding, and got one. MEASURED on the v2850 look: the reviewer reported at HIGH severity
    # that `drift` was "referenced but never declared" in a function it had seen three hunks of.
    # `var drift = ...` is declared once and referenced four times, above the first changed line
    # — unchanged context, therefore absent from the diff BY CONSTRUCTION. The reviewer
    # reasoned correctly from what it was shown; the PAYLOAD misled it. A false finding at high
    # severity costs more than a missed one, because it has to be chased and refuted by hand.
    # [[feedback-suspect-the-instrument]] [[unknown-stays-unknown]]
    # v3341 - A CHAR COUNT CANNOT NAME WHAT IS MISSING, AND 22 OF 36 VERSIONS LOST A CODE FILE.
    # The declaration above says "truncated to 8142 of N diff chars", which is true and unusable:
    # the eye cannot tell from it that control_ui.html is wholly absent, so it answers "the diff is
    # correct as shown" in perfect good faith about a payload containing none of the fix. MEASURED
    # across v3300-v3340 by rebuilding this function per commit: 22 of 36 versions with code changes
    # had at least one changed code file never reach the eye. v3330 lost tree_busy.py and v3315 lost
    # second_eye_run.py - in both cases the file the version exists to change.
    #
    # THE WANTED SET COMES FROM GIT, NEVER FROM WHAT WAS FETCHED. When the python diff alone already
    # exceeds the cap, the *.html show above is never run at all - so a dropped .html is not missing
    # from any buffer here, it is missing from the QUESTION. Only git can see it. Deriving the list
    # from `body` would silently report 0 for exactly the v3333 case that prompted this.
    # [[unknown-stays-unknown]] [[the-unjoined-end]]
    # ⚠ REG-1739 - WAS THE PAYLOAD CUT? Asked HERE, before the batch label below joins `dropped`: that label made
    # every --base (and every default-range) look tell the eye "IT IS ALSO TRUNCATED" when nothing was cut, and the
    # v3561 eye answered cannot-tell from that false warning ("the combined diff is truncated mid-file").
    _cut = bool(dropped)
    absent, _nwhy = absent_from(sha, body)
    # v3363 - AND HOW MUCH OF EACH FILE THAT DID ARRIVE. Measured against the pre-truncation body,
    # so it isolates what the TRANSPORT lost; the comment strip and the ship-note strip are
    # deliberate and are declared separately below, and charging them here would read as loss.
    # ⚠⚠ v3375 — THIS COMMENT USED TO END "and already declared", AND THAT WAS FALSE FOR 15
    # VERSIONS. The header declared three things (diff / truncated / absent files) and neither
    # strip. A comment stating a rule the adjacent code does not implement is the same as not
    # having the rule. [[stale-reading]] [[presence-law-vs-reachability-law]]
    reach = reach_of(_full_len_holder[0], body)

    note = ("\nNOTE: this is a DIFF, not whole files. A name used in one hunk may be DECLARED "
            "or ASSIGNED in a part of the same function the diff does not show, because "
            "unchanged context is omitted by construction. Do not report a variable as "
            "unbound, undefined, undeclared or unpacked-from-nowhere unless you can see its "
            "whole scope here. Judge only what is fully shown, and say so when a judgement "
            "would need code that is not in front of you.\n")
    if REVIEW_BASE:
        _span, _ = _sh(["git", "rev-list", "--count", "%s..%s" % (REVIEW_BASE, sha)], timeout=30)
        _span = (_span or "").strip() or "UNKNOWN"
        note += ("\nTHIS DIFF SPANS %s COMMITS (%s..%s), combined: a version whose code landed in "
                 "commits before its version stamp. Judge the combined change.\n"
                 % (_span, REVIEW_BASE[:8], sha[:8]))
        dropped = ((dropped + " - ") if dropped else "") + (
            "covers %s..%s (%s commits), not the bound commit alone" % (REVIEW_BASE[:8], sha[:8], _span))
    if REVIEW_FILES:
        note += ("\nTHIS IS A FOLLOW-UP LOOK AT %d NAMED FILE(S) ONLY (%s): the version's other changes were shown to an "
                 "earlier look. Judge these files.\n" % (len(REVIEW_FILES), ", ".join(REVIEW_FILES)))
        dropped = ((dropped + " - ") if dropped else "") + (
            "a follow-up look at %d named file(s) only: %s" % (len(REVIEW_FILES), ", ".join(REVIEW_FILES)))
    if _cut:
        note += ("\nAND IT IS ALSO TRUNCATED — it stops part-way through, mid-file at a line "
                 "boundary. Do not report a function, statement or block as incomplete, "
                 "unterminated or missing a return merely because the excerpt stops before it "
                 "does.\n")
    # ⚠⚠ v3375 — THE AUTHOR'S ACCOUNT OF THE CHANGE IS REMOVED BEFORE THE EYE SEES IT, AND
    # UNTIL NOW NOBODY TOLD THE EYE. MEASURED on v3374's own look: the ship-note strip removed
    # 7,885 chars (22% of the raw diff) and the comment strip 2,049, and the cross-family answer
    # came back with "the test file claims panel-sourced names auto-bank; the banking step is not
    # present" — a claim-versus-delivery finding invented from a docstring, because the author's
    # real note said the opposite and had been replaced by a stub. Over 39 version commits the
    # comment strip fired 39/39 and the ship-note strip 22/39.
    # ⚠ CONDITIONAL AND MEASURED. A strip that removed nothing is not declared: saying "notes were
    # stripped" about a payload where none were is a false statement about THIS payload, which is
    # the defect one door down. [[unknown-stays-unknown]]
    if _stripped.get("notes"):
        note += ("\nAND THE AUTHOR'S OWN SHIP NOTE IS NOT IN THIS PAYLOAD - %d characters of it "
                 "were replaced with the stub why=\"<ship note stripped for the eye>\" before you "
                 "were sent this. You cannot see what the author CLAIMED this change does, so do "
                 "not report a claim as undelivered, and do not infer the author's intent from "
                 "whatever prose happens to remain. Judge the code.\n" % _stripped["notes"])
    if _stripped.get("comments"):
        note += ("\nAND COMMENT-ONLY ADDED LINES WERE REMOVED (%d characters). You are reading the "
                 "code, not the author's account of it. Do not report a change as undocumented or "
                 "unexplained on the strength of this payload.\n" % _stripped["comments"])
    if absent is None:
        note += ("\nThe roster of changed files could not be read (%s), so WHICH of this commit's "
                 "files reached you is UNKNOWN. Do not treat this payload as complete.\n"
                 % (_nwhy or "no reason given"))
    elif absent:
        note += ("\nAND THESE CHANGED FILES ARE NOT IN THIS PAYLOAD AT ALL - not truncated, absent. "
                 "Treat them as UNKNOWN rather than as unchanged, say so if a judgement would need "
                 "them, and do not call the change correct on their behalf: %s\n"
                 % ", ".join(absent))
    # The ROW must carry it too, or a later reader sees a clean verdict with no way to know its
    # reach without rebuilding the payload by hand - which is how this went unnoticed for 22 ships.
    if absent:
        dropped = ((dropped + " - ") if dropped else "") + (
            "%d changed file(s) never reached the eye: %s" % (len(absent), ", ".join(absent)))
    elif absent is None:
        dropped = ((dropped + " - ") if dropped else "") + (
            "which changed files reached the eye is UNKNOWN (%s)" % (_nwhy or "unreadable"))
    # ⚠⚠ v3349 — THE LIST TRAVELS, NOT ONLY THE SENTENCE. `dropped` is PROSE, and the row was
    # carrying it as a 400-char-capped suffix on `asked`, so the one-to-many fact "these files
    # never reached the eye" arrived at the ledger flattened into another field and truncated.
    # The comment above this line already says "the ROW must carry it too"; the intent was right
    # and the STORE was wrong. [[one-to-one-store-for-a-one-to-many-fact]]
    # `absent` keeps its THREE states all the way to the row: a LIST (measured, these are missing),
    # [] (measured, nothing missing) and None (nobody could ask). [[unknown-stays-unknown]]
    # ⚠⚠ v3375 — `stripped` TRAVELS TOO, and the comment 20 lines up is the precedent: "the ROW
    # must carry it too, or a later reader sees a clean verdict with no way to know its reach
    # without rebuilding the payload by hand". That was written about `absent`. The strips are the
    # same class of fact and were left in the PROMPT ONLY, so no reader of the ledger could ask
    # how much of the author's account the eye never saw. [[the-unjoined-end]]
    return (COLD_FRAMING + note + "\n```diff\n" + body + "\n```\n",
            dropped, absent, reach, dict(_stripped))


def _unwrap_eye_envelope(raw):
    """-> (answer text, structured dict or None).

    Grok's envelope uses structuredOutput and text. Claude's uses structured_output
    and result. A body that is not that JSON stays prose, and structured stays None.
    """
    ans, structured = raw, None
    try:
        _env = json.loads(raw)
    except Exception:
        _env = None
    if isinstance(_env, dict):
        _so = _env.get("structuredOutput")
        if not isinstance(_so, dict):
            _so = _env.get("structured_output")
        if isinstance(_so, dict) and str(_so.get("verdict") or "").strip():
            structured = _so
        _txt = _env.get("text")
        if not (isinstance(_txt, str) and _txt.strip()):
            _txt = _env.get("result")
        if isinstance(_txt, str) and _txt.strip():
            ans = _txt.strip()
    return ans, structured


def _eye_argv(prompt):
    """Argv for the binary that will actually run.

    Grok's CLI takes a repeated --deny. Claude's CLI has no --deny flag; passing
    one makes the seat exit before it looks. --restricted drops the command
    tools. --disallowedTools is the file-edit block, so a later settings change
    that allows tools still cannot Edit or Write. Claude's schema result arrives
    as structured_output under --output-format json.
    """
    low = (EYE_CLI or "").lower()
    # Grok and codex win before claude. A home folder that contains the word
    # claude must not hand a codex binary Claude-only flags.
    if "claude" in low and "grok" not in low and "codex" not in low and "chatgpt" not in low:
        return [EYE_CLI, "-p", prompt, "--json-schema", EYE_VERDICT_SCHEMA,
                "--output-format", "json", "--restricted",
                "--permission-mode", "dontAsk", "--disable-slash-commands",
                "--disallowedTools", "Edit,Write,MultiEdit,NotebookEdit"]
    argv = [EYE_CLI, "-p", prompt, "--json-schema", EYE_VERDICT_SCHEMA,
            "--deny", "Edit", "--deny", "Write", "--deny", "MultiEdit",
            "--disable-web-search"]
    # REG-1999 - A BIG PASTED DIFF AT DEFAULT EFFORT ANSWERS NOTHING. MEASURED 2026-10-07: a 10.7k-char slice returned 0 bytes
    # at 420 s three times; with --effort low it answered in 192 s with 6 findings. `-p` prints nothing until it finishes, so
    # a timeout reads as an empty seat. Grok only (a codex binary shares this branch); THIRD_EYE_EFFORT overrides.
    if "grok" in low:
        argv += ["--effort", os.environ.get("THIRD_EYE_EFFORT") or "low"]
    return argv


def _model_from_transport():
    """Which family answered, read from WHICH BINARY WAS EXECUTED. -> model id or ""

    ⚠⚠ v3229 — WITHOUT THIS THE LANE WAS REACHABLE AND STILL USELESS TO THE GATE. Measured
    2026-09-16: v3224 and v3225 both got genuine cross-family reviews through the CLI door — 6 and
    12 real findings — and BOTH landed as `model='' family=None`, because this Grok CLI prints no
    model header and `_model_from_answer` had nothing to read. `family_of(None)` is None by
    design, an unattributable look cannot discharge a cross-family debt, and so the push gate went
    on reporting **"v3224 OWES A LOOK — nothing was ever recorded for it"** about a look that had
    just happened. Two eyes ran for 15 minutes each and bought nothing.

    ⚠ AND IT MUST NOT BECOME THE BUG IT IS FIXING. v3214-v3216 recorded `model=EYE_MODEL` — the
    CONFIGURED default — no matter who answered, so three OpenAI looks were filed `family=xai`.
    The lesson there was *read it from the evidence, not the config*. **This is evidence**: it is
    not what we hoped to run, it is which executable the subprocess actually launched, and a
    same-family agent cannot produce a row through a path it never took. That is why it derives
    from `EYE_CLI` alone and never from `EYE_MODEL`.

    It stays a FALLBACK: `record_answer` prefers the model the answer names, always. And every row
    it attributes carries `modelSource="transport"`, so the ledger says which kind of evidence it
    had. [[derived-correctly-from-a-guess]] [[unknown-stays-unknown]]
    """
    low = (EYE_CLI or "").lower()
    if "grok" in low:
        return "grok-cli"          # family_of() -> xai
    if "codex" in low or "chatgpt" in low:
        return "codex-cli"         # family_of() -> openai
    # The binary is the evidence, same as the two above. A path that also says grok was
    # already returned as grok-cli, so this arm cannot launder a Grok binary as Claude.
    if "claude" in low:
        return "claude-cli"        # family_of() -> anthropic
    return ""                      # UNKNOWN transport -> stays unattributable, fails closed


# ⚠⚠ v3420 — THE VERDICT IS A FIELD THE MODEL IS CONSTRAINED TO EMIT, NOT A WORD PARSED OUT OF
# ITS PROSE. Everything below `_claims_a_defect` is a decade of patches on that one mistake, and
# the docstrings there are the receipts: v2808 filed a CLEAN look as `findings`; v3198's fix was
# "wrong in BOTH directions" and a declaration followed by exactly ONE listed P1 was filed CLEAN;
# a review saying NO DEFECTS was filed `findings` because the word after `defects` was `meeting`;
# an eye that ended its answer "VERDICT: clean" was filed `findings`. Each patch was correct about
# the case it saw and wrong about the next one, because PROSE IS NOT A VERDICT FIELD.
#
# MEASURED before building on it (`grok --json-schema` probe, 2026-09-23): the CLI answers with an
# envelope carrying `text`, `thought`, `usage` and `structuredOutput`, and structuredOutput is the
# schema-constrained object. The model cannot emit a verdict outside the enum.
#
# ⚠ THE PROSE PARSER IS NOT DELETED. The MCP/API transport has no schema, and a look taken through
# it must still be recordable. What changes is that the row now SAYS WHICH ROUTE PRODUCED ITS
# VERDICT — `verdictFrom: "schema"` or `"prose"` — because a verdict the model was constrained to
# emit and one inferred from its sentences are different evidential objects, and collapsing them
# is how the ledger came to assert things the eye never said. [[unknown-stays-unknown]]
EYE_VERDICT_SCHEMA = json.dumps({
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["clean", "findings", "cannot-tell"],
                    "description": "clean = looked and it is fine. findings = real defects listed. "
                                   "cannot-tell = you could NOT SEE enough of the change to judge "
                                   "it. cannot-tell is NOT clean."},
        "findings": {"type": "array", "items": {"type": "string"},
                     "description": "one entry per concrete defect, each with the scenario in "
                                    "which it fails. Empty when the verdict is clean."},
        "unseen": {"type": "string",
                   "description": "what you were NOT shown, in your own words. Empty if you "
                                  "believe you saw the whole change."},
    },
    "required": ["verdict", "findings", "unseen"],
})


def _reap_after_kill(p, drain_s=10.0, reap_s=10.0):
    """Collect a child we have just SIGKILLed. -> True if it was reaped.

    ⚠⚠ v3424 - `kill()` THEN `communicate(timeout=N)` IS NOT A REAP, AND v3421 SHIPPED BELIEVING
    IT WAS. The second eye found this reviewing v3421 and the claim was then MEASURED rather than
    argued. On CPython 3.9 `Popen.communicate` runs its select loop FIRST and only reaches
    `self.wait(...)` afterwards, so a second TimeoutExpired escapes before any wait() happens:

        child forks a grandchild that inherits the stdout pipe, parent kills the child
        -> communicate(timeout=4) TIMED OUT AGAIN after 4.0s
        -> p.returncode is None,  ps says `Z    <defunct>`
        -> an explicit p.wait(timeout=5) returns -9 and ps says <not in table - REAPED>

    Python's own docs write `proc.kill(); proc.communicate()` with NO timeout, which never has this
    hole - but an unbounded drain in a console that stays up for days is a hang, so the bound
    stays and the wait is made UNCONDITIONAL instead. The drain is only there to release the pipes;
    the wait is the reap, and it runs whether the drain worked, timed out, or raised.

    ⚠ THE CHILD IS ALREADY SIGKILLed, so wait() returns immediately in every ordinary case. The
    bound exists only for a process stuck in uninterruptible sleep, which no wait can help anyway.
    """
    try:
        p.communicate(timeout=drain_s)      # release the pipes if the child will let us
    except Exception:
        pass                                # a failed DRAIN must never skip the REAP below
    try:
        p.wait(timeout=reap_s)
        return True
    except Exception:
        return False                        # unkillable; there is nothing further a caller can do


def ask(prompt, sha=None):
    """-> (answer, reached, why, structured). An unreachable eye returns reached=False, NO verdict.

    #169 Win 2 — given the reviewed commit, the eye's folder holds that commit's changed files,
    read-only, and the prompt names them (eye_snapshot / snapshot_note).

    `structured` is the schema-constrained object when the transport produced one, else None.
    None is a THIRD STATE: it means nobody constrained this answer, not that the answer was bad.
    """
    if not os.path.exists(EYE_CLI):
        return "", False, "no eye at %s (set THIRD_EYE_CLI)" % EYE_CLI, None
    _t0 = time.time()
    try:
        # ⚠⚠ v3420 — READ-ONLY BY FLAG, NOT BY AN EMPTY FOLDER. v3408 put EYE_CWD outside the
        # repo because "a CLI eye is an AGENT with tools, and pointed at this checkout it can
        # EDIT IT" — and Grok WAS caught writing to tv/ mid-ship on 2026-09-22. An empty cwd is
        # a hiding place, not a guard: nothing stops the agent walking to an absolute path.
        # These three denials are the SHIPPED pattern from kai-achilles/tools/claude_vision.sh
        # (--deny Edit --deny Write --deny MultiEdit), copied rather than re-derived, and they
        # are what makes it safe to hand the eye real code in a later version. [[grok-second-eye]]
        if sha:
            prompt = prompt + snapshot_note(eye_snapshot(sha))
        _argv = _eye_argv(prompt)
        _eye_cwd_ready()          # v3422 — made HERE, at use, never at import
        p = subprocess.Popen(_argv,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=EYE_CWD)
        out, err = p.communicate(timeout=EYE_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        # ⚠⚠ v3421 — kill() SIGNALS; IT DOES NOT REAP. Same shape as the handler above and as the
        # ocr worker in the closer loop: communicate() reaps on the normal path and is exactly what
        # raised here, so the eye left one <defunct> child behind per timeout. Measured this
        # session: the eye timed out repeatedly while the cap was still 9,000.
        p.kill()
        _reap_after_kill(p)
        # ⚠ SAY HOW LONG IT ACTUALLY WAITED. "did not answer" with no number cannot be told apart
        # from "was never started", and the reader cannot judge whether the bound was the problem.
        return "", False, ("the eye did not answer within %.0fs (waited %.0fs) — an EMPTY SEAT, "
                           "never agreement" % (EYE_TIMEOUT_S, time.time() - _t0)), None
    except Exception as e:
        return "", False, "the eye could not be run: %s" % type(e).__name__, None
    finally:
        # ⚠ v3422 — atexit IS NOT ENOUGH ON ITS OWN. It fires when the PROCESS ends, and the
        # console is a process that stays up for days asking for look after look; relying on
        # it there would leak one directory per look for the life of the window. This runs on
        # every exit from the call, including the timeout and the failure paths.
        eye_cwd_cleanup()
    raw = (out or b"").decode("utf-8", "replace").strip()
    if p.returncode != 0:
        return raw, False, ("the eye exited %d: %s"
                            % (p.returncode, (err or b"").decode("utf-8", "replace")[:200])), None
    # ⚠⚠ v3420 — WITH A SCHEMA THE TRANSPORT RETURNS AN ENVELOPE, NOT PROSE, AND THE GUARDS BELOW
    # WERE WRITTEN FOR PROSE. MEASURED shape (probe, 2026-09-23): a single JSON object carrying
    # `text`, `thought`, `usage`, `modelUsage`, `total_cost_usd` and `structuredOutput`. The
    # human-readable reply is `text`; `structuredOutput` is the schema-constrained object.
    #
    # So the envelope is UNWRAPPED here and everything downstream still sees prose. If it does not
    # parse, that is not an error — it is an older transport, and `structured` stays None so the
    # row records `prose` rather than claiming a constraint nobody applied. A fallback that
    # silently pretends to be the real thing is the defect this whole file is a monument to.
    ans, structured = _unwrap_eye_envelope(raw)
    # ⚠ EXIT 0 IS NOT AN ANSWER. This CLI has been measured exiting 0 on "Not signed in"; an empty
    # or near-empty body is an empty seat however clean the status code looked.
    # ⚠ AND THE LENGTH IS MEASURED ON THE UNWRAPPED REPLY, never on the envelope: a 2 KB envelope
    # around a 12-character refusal would sail past a guard that counted the wrapper.
    if len(ans) < 40 and not structured:
        return ans, False, "the eye answered %d chars — too little to be a look" % len(ans), None
    return ans, True, "", structured


# ⚠⚠ v3198 — THE ADJECTIVE WAS THE WHOLE BUG, AND IT MADE THE LEDGER LIE IN THE DIRECTION
# THE LEDGER EXISTS TO PREVENT. Measured 2026-09-16 on a real cross-family look at v3189: Grok
# opened with **"No concrete defects found in the diff."** and the row was filed
# `verdict=findings, findings=4`. The four "findings" were its own summary of what the diff
# CHANGED — the first of them literally reading "No concrete defects found."
#
# The pattern demanded `no <noun> found` with nothing between, so one adjective — concrete,
# obvious, real, apparent, actual — defeated it. This is `label-outlived-referent` inside the
# instrument itself: the ledger whose entire job is to record what another family concluded
# recorded the opposite of what it concluded, and the ship gate reads this ledger.
#
# ⚠ TWO ADJECTIVES, NOT UNBOUNDED. `\w+\s+` repeated without a ceiling would let
# "no ... found" span a whole sentence and match "there is no way to tell whether the bugs the
# reviewer found are real" — the exact inversion. Bounded at 2 it covers every real phrasing
# measured and cannot swallow a clause. [[unknown-stays-unknown]] [[source-reading-guard]]
# A provider-level refusal — rate limit, auth, a model the account may not use. These arrive as
# ordinary stdout and can be any length, so a size test will not catch them. They are NOT a review
# and must never be recorded as one: the seat was never occupied. [[unknown-stays-unknown]]
# ⚠⚠ v3223 — ANCHORED, AND THE VOCABULARY IS OPENERS NOT TOPICS. The v3220 version searched for
# "quota", "unauthor", "authentication", "rate-limit" ANYWHERE in the first 400 characters, so a
# genuine review saying "authentication is not checked" or "quota is never decremented" was filed
# as a provider refusal and DISCARDED. A cross-family look named it, and pointed out that a review
# of that very diff would trip it. Over-refusing is the worse direction of the two: a false LOOKED
# is visible in the ledger, a discarded real look is not.
# These are how a PROVIDER opens when it produced nothing else. A reviewer does not begin a review
# with "You have hit your usage limit". [[unknown-stays-unknown]] [[source-reading-guard]]
_PROVIDER_ERROR_RX = re.compile(
    r"(?is)\s*(?:"
    r"ERROR\b|error:|\{\s*\"type\"\s*:\s*\"error\"|"
    r"you(?:'ve| have) hit your usage limit|"
    r"(?:you are|you're) being rate[- ]limited|"
    r"rate[- ]limit(?:ed|-exceeded)?\b|"
    r"quota exceeded|"
    r"please (?:sign|log) in\b|"
    r"authentication (?:failed|required)\b|"
    r"unauthorized\b|"
    r"the '[^']+' model is not supported"
    r")")


_NO_DEFECT_RX = re.compile(
    # ⚠⚠ v3268 — THE TRAILING `\s+` HERE IS WHY THE BARE FORM COULD NEVER MATCH, and it is also
    # why v3268's first cut LOOKED like it worked. "No concrete defects." puts a `.` straight
    # after the noun, so a REQUIRED space fails before the tail is ever tried. The optional-tail
    # branch added below was therefore unreachable for exactly the input it was written for — and
    # the test passed anyway, because `_findings_from` returns NO blocks for a one-line answer and
    # `_verdict_for` reads "a declaration with nothing listed" as clean. A green arrived by a
    # route that had nothing to do with the fix. [[matches-once-can-still-prove-nothing]]
    # The separator moves INTO the verb branch, where it belongs: a verb needs a space before it,
    # a full stop does not.
    r"\bno\s+(?:\w+\s+){0,2}(?:defects?|issues?|bugs?|problems?)\b"
    # ⚠ v3216 — `evident` AND `present` ADDED, and `is` to the copula list. An OpenAI seat wrote
    # "No concrete functional defect is evident in this diff", every block scored
    # claims_a_defect=False, and the row STILL said verdict=findings — because the declaration
    # used a verb this list did not carry. Widening here is safe by construction: the pattern only
    # ever GRANTS clean, and only when `claims` is simultaneously empty, so a miss costs a noisy
    # row and a false match still cannot clear a real finding. [[unknown-stays-unknown]]
    # ⚠⚠ v3267 — A THIRD VERB, AND IT IS THE SAME DEFECT A THIRD TIME. Grok answered v3266 with
    # "The diff is correct as shown (no concrete defects meeting the criteria)." — a flat clean —
    # and the row was filed verdict=findings, because the word after `defects` was `meeting`,
    # which this list did not carry. v3216 added `evident`/`present` for the same reason. The
    # instrument keeps failing on the one axis nobody can enumerate in advance: how a different
    # model phrases "nothing is wrong".
    # ⚠ Widening stays safe by construction, and that is WHY it is the right fix rather than a
    # looser pattern: this regex only ever GRANTS clean, only when no block makes a defect claim
    # (`_DEFECT_MARK_RX`), so a false match cannot clear a real finding — it can only spare a
    # clean look from the stricter bucket. [[feedback-blind-fixture-green-gate]]
    # ⚠⚠⚠ v3268 — AND THE VERB CAN BE ABSENT ENTIRELY. Widening the participle list in v3267 was
    # still chasing vocabulary. Taking the very next look, Grok opened with "**No concrete
    # defects.**" — full stop, no verb at all — and the row was filed verdict=findings AGAIN. That
    # is four phrasings in three versions (v3216 `evident`, v3216 `present`, v3267 `meeting`, this).
    # The lesson is that enumerating how a model says "nothing is wrong" does not converge: the
    # declaration is the NOUN PHRASE, and everything after it is optional decoration.
    # So the tail is now `verb | end-of-clause`, which covers the bare form and every future one.
    # ⚠ Still safe by construction, and the guard is unchanged: this only ever GRANTS clean, and
    # only when NO block makes a defect claim. A red-proof asserts that a P1 following the
    # declaration is still filed as findings. [[unknown-stays-unknown]]
    r"(?:"
    r"\s+(?:were\s+|are\s+|was\s+|is\s+)?"
    r"(?:found|identified|detected|visible|apparent|evident|present|noted|observed|seen|"
    r"reported|meeting|matching|warranting|meriting)\b"
    r"|\s*(?:\*+\s*)?(?:[.;:!]|$)"      # "No concrete defects." / "**No concrete defects.**"
    r")",
    re.I)

#: ⚠⚠⚠ v3315 — THE FIFTH PHRASING, AND IT IS A DIFFERENT PART OF SPEECH. `_NO_DEFECT_RX` is a
#: NOUN-PHRASE pattern: it needs `no <...> defects|issues|bugs|problems`. Four versions widened its
#: vocabulary (v3216 `evident`, v3216 `present`, v3267 `meeting`, v3268 the bare full stop) and the
#: lesson drawn was "the declaration is the NOUN PHRASE". This shape has no such noun at all.
#:
#: MEASURED 2026-09-18 on the real v3301 look. Grok answered:
#:
#:     **Findings**
#:
#:     none found
#:
#: and the row was filed verdict="findings", findings=2 — the ledger asserting the eye found two
#: things when it had answered the opposite. The blocks were `**Findings** none found …` and
#: `**Visibility note** …`; `_claims_a_defect` was FALSE for both, so the only failing condition
#: was the declaration itself never matching. A reviewer told to say "none found" per category
#: says exactly that, and the prompt this repo sends ASKS for that wording.
#:
#: ⚠ SAFE BY CONSTRUCTION, on the same argument every prior widening used: this can only ever
#: GRANT clean, and only when `_claims_a_defect` is false for EVERY block. A review that says
#: "off-by-one: none found" and then lists a real P1 still lands in `findings`, because the claim
#: check is unchanged. A miss costs a noisy row; a false match cannot clear a real defect.
_NO_FINDING_RX = re.compile(
    r"(?:\bnone\s+found\b"
    r"|\bnothing\s+(?:found|wrong|to\s+report|of\s+note|to\s+flag)\b"
    r"|\bfindings?\b\s*[:\-\u2013\u2014]?\s*none\b"
    r"|\bnone\s*(?:\*+\s*)?(?:[.;:!]|$))", re.I)


def _declares_none(text):
    """Does this text DECLARE that nothing was found? -> bool

    Two shapes, and they are different parts of speech:
      · the NOUN PHRASE  — "no concrete defects found" (`_NO_DEFECT_RX`)
      · the PRONOUN      — "none found", "findings: none" (`_NO_FINDING_RX`)

    Kept as two named patterns rather than one, because the noun-phrase one has been corrected
    four times and restructuring it to carry a different part of speech is how the fifth
    correction becomes a sixth. [[copy-drift]]
    """
    t = text or ""
    return bool(_NO_DEFECT_RX.search(t) or _NO_FINDING_RX.search(t))


# a block that carries one of these is making a CLAIM about a defect, not describing a change.
# Used only to refuse a clean verdict, never to grant one — so a miss here costs nothing and a
# false hit only keeps a look in the stricter bucket.
_DEFECT_MARK_RX = re.compile(
    r"\b(?:P[0-9]\b|severity|critical|race\s+condition|deadlock|leak|crash|"
    r"unreachable|mismatch|disagree|fails?\b|breaks?\b|vulnerab)", re.I)

# ⚠⚠ A NEGATED MARKER IS THE OPPOSITE OF A MARKER, AND IT COST A CLEAN VERDICT. Measured on the
# real v3189 answer: its closing line is *"No caller/callee contract mismatches, races, leaks, or
# unreachable states are visible in the provided hunks."* — four marker words in one sentence,
# every one of them DENIED. Matching them read a reviewer listing what it did NOT find as a
# reviewer finding it. The clause is cut at the first `.`/`;`/`:` so a genuine claim sharing the
# block ("No defects found. P1: ...") still survives the strip. [[measured-true-read-wrong]]
# ⚠⚠ v3255 — AND "NOTHING" IS A NEGATION TOO. THIRD TIME THIS CLASS HAS BITTEN THIS FILE (v2808,
# v3198, now). Measured on the real v3252 answer, whose FIRST LINE is "**No concrete defects
# found.**": its closing sentence is *"Nothing in the shown hunks indicates a caller/callee
# contract violation, a race, a leak, an unreachable state, or any other observable defect."*
# `\bno\b` does not match "Nothing" — there is no word boundary after the "no" — so three marker
# words survived the strip and a review that said NO DEFECTS was filed as verdict="findings", in
# the ledger whose entire job is recording what another family concluded. Exactly the v2808
# defect, through a door the v3189 fix did not cover.
#
# ⚠ THIS WIDENS THE STRIP, WHICH IS THE DANGEROUS DIRECTION, AND IT IS BOUNDED ON PURPOSE. The
# strip is only consulted by `_verdict_for` AFTER the answer has already DECLARED no defects in
# its first block; an answer with no such declaration never reaches it. Measured both ways before
# shipping: "No defects found. P1: the caller crashes on empty input." still files as findings,
# and "Nothing validates the payload, so it crashes" (no declaration) still files as findings.
# [[measured-true-read-wrong]] [[strictness-that-closes-the-lane]]
_NEGATED_RX = re.compile(r"\b(?:nothing|no|not|none|never|without|free\s+of)\b[^.;:]*", re.I)


def _claims_a_defect(block):
    """does this block CLAIM a defect — as opposed to naming one it rules out?"""
    return bool(_DEFECT_MARK_RX.search(_NEGATED_RX.sub(" ", block or "")))


# ⚠⚠ v3376 — THE LEDGER VOCABULARY IS `clean`, THE PROMPT ASKS FOR `clean`, AND THE PARSER DID
# NOT KNOW THE WORD. MEASURED on v3375 own look: the answer first line was literally
# "VERDICT: clean", `_declares_none` returned False, and the row was filed verdict=findings with
# FOUR findings — every one of them the answer explaining why it is clean. agreement() reads
# verdicts, so the ledger asserted four defects in v3375 that do not exist. Sixth phrasing to
# defeat this check (#67 was the fifth at v3315). [[the-unjoined-end]]
#
# ⚠ THIS IS NOT A WIDENING OF `_declares_none`, AND MUST NOT BECOME ONE. #76 measured that
# widening the prose matcher cannot be made safe, and #117 measured that a bullet filter would EAT
# A REAL FINDING. This reads a DECLARED FIELD instead: a line that states the verdict in the
# ledger own vocabulary, anchored at line start. Prose is never consulted here.
#
# ⚠⚠ AND A MENU IS NOT A DECLARATION. The review prompt itself contains the line
# "1. VERDICT: clean / findings", so an eye that echoes its instructions would otherwise be read
# as declaring CLEAN. Any line naming two or more verdict words is a menu and is ignored.
_VERDICT_LINE_RX = re.compile(r"(?im)^[\s>*_#\-]*verdict\b\s*[:\u2013\u2014\-]\s*(.+)$")
_VERDICT_WORD_RX = re.compile(r"\b(clean|findings|cannot[-\s]tell)\b", re.I)


def _stated_verdict(answer):
    """-> "clean" | "findings" | "cannot-tell" | None when the answer states no verdict.

    None means NOBODY DECLARED ONE, which is different from declaring clean, and the caller
    falls back to the prose path unchanged. [[unknown-stays-unknown]]
    """
    for m in _VERDICT_LINE_RX.finditer(answer or ""):
        words = [w.group(1).lower() for w in _VERDICT_WORD_RX.finditer(m.group(1))]
        words = ["cannot-tell" if w.startswith("cannot") else w for w in words]
        if len(set(words)) == 1:
            return words[0]
    return None


def _verdict_for(answer, findings):
    """"clean" or "findings" — and a declaration alone can never clear a real defect claim.

    ⚠ v2808 — A CLEAN LOOK WAS BEING FILED AS ONE THAT FOUND DEFECTS. `_findings_from` folds an
    unenumerated answer into a single block, so "No defects found." came back as findings=[<the
    whole answer>] and the row read verdict="findings". The v2807 row said the eye had found
    something when it had said the opposite, in the ledger whose entire job is to record what
    another family concluded. [[label-outlived-referent]]

    ⚠⚠ v3198 — THAT FIX WAS `len(findings) > 1`, AND IT WAS WRONG IN BOTH DIRECTIONS. Measured,
    2026-09-16, by probing it with four hand-built answers:

        "No concrete defects found."  + 3 blocks describing the diff   -> findings   WRONG
        "No defects found." + ONE listed P1                            -> clean      WRONG, and
                                                                          this is the dangerous
                                                                          direction

    The second is the one that matters. A declaration followed by exactly ONE defect produced
    `len(findings) == 1`, which is not `> 1`, so the declaration cleared it and a real P1 was
    filed as a clean look. The docstring above says "a model that declares no defects and then
    lists three stays findings" — true for three, FALSE for one, and nothing measured the claim.
    [[feedback-blind-fixture-green-gate]] — a rule nobody ever saw refuse.

    THE RULE NOW HAS THREE PARTS, and all three must hold before a look is cleared:
      1. the answer DECLARES no defects, and
      2. the declaration is in the FIRST block — a list of defects does not begin with
         "no defects found", so order is the measurable tell, and
      3. no block makes a defect CLAIM (`_DEFECT_MARK_RX`).
    Anything else stays "findings". That is deliberately asymmetric: over-reporting a finding
    costs a re-read, under-reporting one ships a defect with a clean stamp on it.
    """
    # ⚠ v3376 — A STATED VERDICT IS READ FIRST, AND IT STILL CANNOT CLEAR A REAL CLAIM.
    # The asymmetry of this function is preserved exactly: a declaration of cleanliness is
    # overruled by any block that CLAIMS a defect, so this can never become an off switch.
    stated = _stated_verdict(answer)
    if stated == "findings":
        return "findings", findings
    if stated == "cannot-tell":
        return "cannot-tell", []
    if stated == "clean":
        _claimed = [f for f in findings if _claims_a_defect(f)]
        if _claimed:
            return "findings", findings
        return "clean", []

    decl_anywhere = _declares_none(answer)
    if not decl_anywhere:
        # ⚠⚠ v3346 — AN UNPARSED ANSWER IS `cannot-tell`, NEVER A DEFECT. This branch fires when the
        # answer does not DECLARE cleanliness in a phrasing _declares_none recognises. v3343 landed
        # here saying "The diff is correct. No defects, races, contract mismatches, leaks, or
        # unreachable states are present" — a comma-tail #76 measured and REFUSED to widen for, and
        # rightly: _claims_a_defect covers only 103 of 628 findings-rows, so the narrow declaration
        # IS the safety.
        #
        # So the fix is not in the declaration. It is that the "finding" here was the WHOLE ANSWER:
        # no line started a finding, so _findings_from had nothing to split on and swallowed it. A
        # parse that found no structure is UNKNOWN, and the ledger already has the word for it —
        # `cannot-tell` is in PARSER_VERDICTS and 13 rows use it.
        #
        # ⚠ ALL THREE CONDITIONS, because this function has been wrong here twice (v2808, v3198 —
        # "wrong in both directions"). It fires ONLY when nothing parsed AND nothing is claimed:
        #   · a real findings answer NUMBERS its findings -> has structure -> untouched
        #   · a prose answer that CLAIMS a defect          -> stays `findings`, never downgraded
        #   · v3341/v3342/v3344 declare cleanliness        -> never reach this branch at all
        # MEASURED across the four looks taken today: exactly ONE (v3343) satisfies all three.
        # `cannot-tell` is not clean either, so nothing is cleared by it. [[unknown-stays-unknown]]
        if findings and not _has_finding_structure(answer) \
                and not any(_claims_a_defect(f) for f in findings) \
                and _SAYS_NO_DEFECT_RX.search(answer):
            return "cannot-tell", []
        return ("findings" if findings else "clean"), findings
    if not findings:
        return "clean", []
    opens_clean = _declares_none(findings[0])
    claims = [f for f in findings if _claims_a_defect(f)]
    if opens_clean and not claims:
        return "clean", []
    return "findings", findings


def _model_from_answer(answer):
    """Which model actually produced this answer? -> slug or None. Read from the BYTES.

    ⚠⚠ v3216 — IN HANDOFF MODE THE LEDGER RECORDED THE CONFIGURED GROK DEFAULT NO MATTER WHO
    ANSWERED. `--answer-in` passed `model=EYE_MODEL`, which is `grok-4-1-fast-reasoning` unless
    THIRD_EYE_MODEL is set — so three real OpenAI looks (v3214, v3215, v3216, all produced by
    `gpt-5.6-terra`) were filed as **family=xai**. The ledger's own docstring says family "is
    derived from the model id, not asserted" because "a same-family agent writing plausible
    strings must never be mistakable for a cross-family look" — and that derivation was correct
    while its INPUT was a guess. The one question this file exists to answer was being answered
    from configuration rather than from evidence.

    ⚠ AND IT FAILS CLOSED. If the answer does not say, this returns None and the caller records an
    UNKNOWN model rather than inheriting the default — an unattributable look must not be able to
    discharge a cross-family debt. [[unknown-stays-unknown]] [[the-unjoined-end]]
    """
    head = (answer or "")[:4000]
    m = re.search(r"(?mi)^\s*(?:\x1b\[[0-9;]*m)?model:(?:\x1b\[[0-9;]*m)?\s*([A-Za-z0-9._-]+)", head)
    return m.group(1) if m else None


def _strip_echo(answer, prompt):
    """Drop a prompt the tool echoed back before its reply. -> str

    ⚠⚠ v3216 — THE ECHO WAS BEING COUNTED AS FINDINGS. `codex exec` prints the whole prompt —
    including the DIFF — before its answer, and `_findings_from` split that too. Every handoff row
    came back with exactly **12** findings (the `[:12]` cap) whose text was
    `'--- a/tv/control_app.py'` and `'Reading prompt from stdin...'`, and a reply that said
    *"No concrete functional defect is evident in this diff"* was filed as `verdict=findings`.
    A constant is not a measurement. [[zero-needs-a-denominator]] [[feedback-suspect-the-instrument]]
    """
    a = answer or ""
    tail = (prompt or "").strip()[-160:]
    if tail and tail in a:
        a = a[a.rindex(tail) + len(tail):]
    # ⚠⚠ AND THE TERMINAL CONTROL BYTES, which is why the first cut of this still mis-read a
    # CLEAN answer. `codex exec` writes its reply behind an ANSI colour run and a `codex` speaker
    # label, so `findings[0]` began `\x1b[35m\x1b[3mcodex\x1b[0m ... No concrete functional
    # defect is evident` — and `_NO_DEFECT_RX`, which anchors near the start, never matched. The
    # row then said verdict=findings over a reply that found nothing. Over-reporting is the safe
    # direction, but a verdict that disagrees with its own answerHead is still a broken instrument.
    a = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", a)
    a = re.sub(r"(?m)\A\s*(codex|assistant)\s*$", "", a).lstrip()
    return a.lstrip()


#: ⚠⚠ DOWNGRADE-ONLY, AND THAT IS THE WHOLE SAFETY ARGUMENT. This may move a row from `findings`
#: to `cannot-tell`. It may NEVER produce `clean`, and `_declares_none` — the function that DOES
#: decide clean — is untouched. #76 measured that widening _declares_none cannot be made safe
#: (_claims_a_defect covers only 103 of 628 findings-rows), and that ruling stands; this is a
#: different question asked in a different direction.
#:
#: ⚠ SIZED AGAINST THE REAL LEDGER BEFORE SHIPPING, because my first cut was REFUTED by it. Without
#: this phrase test the structure-absence rule alone would have reclassified 172 of 637 findings
#: rows — including v2180 "FINDING 1: Saved OFF is overruled by an env ON", a real defect. With it,
#: 13 flip, and reading them: v2805 "No defects found", v2850/v2851/v3207/v3266 "The diff is correct
#: as shown", v3147 "No concrete defects found" — clean looks that were misfiled as findings, the
#: same defect as v3343. ONE is a wrong flip, v2837 ("real hazard, cache never cleared"), and it
#: lands on cannot-tell rather than clean, so nothing is cleared and a re-read is prompted. That is
#: the safe direction this function's own docstring names. [[regression-guard]] §5a
_SAYS_NO_DEFECT_RX = re.compile(
    r"(no\s+(concrete\s+)?(defects?|issues?|problems?|bugs?)\b"
    r"|the\s+diff\s+is\s+correct"
    r"|is\s+correct\s+(on|as)\s+(the\s+)?(bytes|shown)"
    r"|correct\s+as\s+shown)", re.I)

#: What STARTS a finding. ONE definition — _findings_from splits on it and _has_finding_structure
#: asks whether it ever matched, and a second copy is how the two disagree about the same answer.
#: [[copy-drift]]
_FINDING_START_RX = re.compile(r"^(\d+[\.\)]|[-*•]|\*\*\d+)")


def _has_finding_structure(answer):
    """Did ANY line start a finding? -> bool

    ⚠ v3346 — THIS IS THE DIFFERENCE BETWEEN A DEFECT AND AN UNPARSED ANSWER. _findings_from joins
    every non-starting line onto the block above, so an answer with NO numbered or bulleted line
    comes back as ONE finding whose text is the WHOLE ANSWER — REACH line, verdict and all. That is
    not something the eye reported; it is a parse that found no structure, and it read as the worse
    of the two. MEASURED on v3343: the eye said "The diff is correct. No defects, races, contract
    mismatches, leaks, or unreachable states are present" and the row was filed verdict=findings,
    findings=1. [[unknown-stays-unknown]]
    """
    for ln in (answer or "").splitlines():
        if _FINDING_START_RX.match(ln.strip()):
            return True
    return False


def _findings_from(answer):
    """Split the answer into findings without interpreting them. Numbered or bulleted lines start
    a finding; everything else joins the one above."""
    out, cur = [], []
    for ln in answer.splitlines():
        s = ln.strip()
        if _FINDING_START_RX.match(s) and cur:
            out.append(" ".join(cur).strip())
            cur = [s]
        elif s:
            cur.append(s)
    if cur:
        out.append(" ".join(cur).strip())
    return [f for f in out if len(f) > 30][:12]


# ⚠⚠ THE CLI ON THIS MACHINE IS AGENTIC, NOT ONE-SHOT — MEASURED, and it changes the design.
# Given a 3,052-char prompt and 120s it replied: "I'll review the snippet against the surrounding
# source... I'll read the rest of the function... I'll inspect hover_mode, the GET status path,
# occupancy parsing, and tests" — and was still exploring the repository when the budget expired.
# It is not slow at answering; it is doing a different job. A one-shot chat endpoint answered the
# same class of payload in seconds.
#
# So the eye has TWO shapes and this script supports both rather than pretending one exists:
#   · CLI mode      — unattended, long budget, deeper because it reads the tree. Background it.
#   · handoff mode  — --prompt-out / --answer-in. The payload is still assembled and MEASURED
#                     here, and the answer is still recorded from the bytes that came back; only
#                     the transport is external. Every number in the row stays measured.
# The one thing neither mode may do is let an unanswered ask read as agreement.


def record_answer(version, answer, sent, dropped="", prompt_text="", answer_model="",
                  sha="", absent=None, reach=None, stripped=None, structured=None):
    """Record an answer obtained by ANY transport, with the payload's measured `sent`."""
    version = SEL.norm_version(version)
    answer = (answer or "").strip()
    # ⚠⚠⚠ v3220 — THE EMPTINESS TEST MUST RUN ON THE REPLY, NOT ON THE ECHO. v3216 taught this
    # function to strip the tool's echoed prompt — and left this guard ABOVE the strip, reading the
    # raw bytes. `codex exec` prints the whole payload before replying, so a run that produced NO
    # REPLY AT ALL still arrived here as ~10,000 characters and sailed past `len(answer) < 40`.
    #
    # MEASURED 2026-09-16, and it filed two lies: the Codex seat answered
    # "ERROR: You've hit your usage limit … try again at Oct 12th" for BOTH v3217 and v3218, and
    # each was recorded as **LOOKED — 1 finding**. The ledger's whole purpose is that an
    # unreachable eye is an EMPTY SEAT and never agreement, and the push gate reads `reached`.
    # A false LOOKED does not merely mis-report — it opens a gate that should have stayed shut.
    #
    # So: strip FIRST, then judge what is left, and treat a provider-level refusal as unreached
    # however long it is. [[unknown-stays-unknown]] [[grok-second-eye]]
    _reply = _strip_echo(answer, prompt_text) if prompt_text else answer
    # ⚠⚠⚠ v3223 — A REFUSAL *IS* THE WHOLE ANSWER; A REVIEW MERELY MENTIONS THESE WORDS.
    # v3220's regex matched "quota", "rate-limit", "unauthor", "authentication", "please sign in"
    # ANYWHERE in the first 400 chars. A cross-family look at v3221 named the trap: a genuine
    # review that says *"authentication is not checked"* or *"quota is never decremented"* would be
    # discarded as a provider refusal — and a review OF THIS VERY DIFF would contain those words.
    # That is the over-refusing direction `AProviderRefusalIsAnEmptySeat` names in its own
    # docstring: it would turn every real eye into an empty seat, which is worse than the false
    # LOOKED it was written to stop, because a discarded look is invisible.
    #
    # A provider refusal is SHORT and it is the ENTIRE reply — the tool printed nothing else.
    # A review is long and discusses many things. So: an explicit `ERROR:` opener always counts,
    # and the softer vocabulary only counts when the whole reply is too short to be a review.
    # [[unknown-stays-unknown]] [[feedback-blind-fixture-green-gate]]
    # ⚠ ANCHORED AT THE OPENING, NOT LENGTH. My first cut added "…or it matches anywhere and the
    # reply is under 600 chars", and a 434-char REVIEW about authentication was refused by it.
    # Length is the wrong instrument: a short review is still a review. What separates the two is
    # that a provider refusal is the FIRST thing the tool says, because it never got further.
    _refused = bool(_PROVIDER_ERROR_RX.match(_reply.lstrip()))
    if len(_reply) < 40 or _refused:
        _why = ("the provider refused: %s" % _reply.strip().splitlines()[0][:110]) if _refused \
               else ("the answer was %d chars" % len(_reply))
        SEL.record(version=version, model=(_model_from_answer(answer) or answer_model or ""),
                   verdict="", findings=[], images=[],
                   asked=COLD_FRAMING.strip()[:200], answer_head=_reply, head_cap=200, reached=False,
                   path=None, seen_path=None, sent=sent, sha=sha)
        print("  %s: %s — EMPTY SEAT, not agreement" % (version, _why))
        return False
    # ⚠⚠ v3216 — STRIP THE ECHO AND READ WHO ACTUALLY ANSWERED, because handoff mode was doing
    # neither. `codex exec` prints the whole prompt — diff included — before its reply, so the
    # splitter counted the ECHO: every handoff row came back with exactly 12 findings (the cap)
    # reading `'--- a/tv/control_app.py'`, and a reply saying "No concrete functional defect is
    # evident" was filed as verdict=findings. And `model=EYE_MODEL` recorded the configured GROK
    # default no matter who answered, so three real `gpt-5.6-terra` looks were filed family=xai —
    # the ledger asserting a Grok seat that was never occupied. [[unknown-stays-unknown]]
    # ⚠ ORDER MATTERS, AND I GOT IT WRONG FIRST: the tool prints its `model:` header BEFORE the
    # echoed prompt, so stripping the echo first throws away the one piece of evidence that says
    # who answered. Read the model from the RAW bytes, then strip.
    _model = _model_from_answer(answer) or answer_model or ""
    answer = _strip_echo(answer, prompt_text)
    findings = _findings_from(answer)
    # ⚠⚠ v3420 — A CONSTRAINED FIELD BEATS A PARSED SENTENCE, AND THE ROW SAYS WHICH IT GOT.
    # `_verdict_for` and everything it leans on is a decade of patches on reading prose, and its
    # own docstrings are the receipts: a CLEAN look filed as `findings`; a fix that was "wrong in
    # BOTH directions"; a declaration plus exactly ONE listed P1 filed CLEAN; a review saying NO
    # DEFECTS filed `findings` because the word after `defects` was `meeting`. Each patch was right
    # about the case in front of it and wrong about the next, because PROSE IS NOT A FIELD.
    #
    # When the transport constrained the model to a schema, the verdict is READ, not inferred. The
    # prose path stays for transports that cannot constrain (the MCP door), and the row records
    # `verdictFrom` so the two can never be mistaken for each other: a verdict the model was FORCED
    # into an enum and a verdict a regex guessed from sentences are different evidential objects.
    # Collapsing them is how this ledger came to assert things the eye never said.
    # [[unknown-stays-unknown]] [[label-outlived-referent]]
    _verdict_from = "prose"
    if isinstance(structured, dict) and str(structured.get("verdict") or "").strip():
        _v = str(structured["verdict"]).strip().lower()
        if _v in ("clean", "findings", "cannot-tell"):
            _verdict = _v
            _sf = structured.get("findings")
            findings = [str(x) for x in _sf if str(x).strip()] if isinstance(_sf, list) else []
            _unseen = str(structured.get("unseen") or "").strip()
            if _unseen:
                # what it was NOT shown is part of the look, not a footnote — it is the only thing
                # that separates a clean verdict from one taken through a keyhole.
                findings = findings + [SEL.NOT_SHOWN_PREFIX + _unseen]   # one spelling, the ledger's (REG-2740)
            _verdict_from = "schema"
    if _verdict_from == "prose":
        _verdict, findings = _verdict_for(answer, findings)
    SEL.record(version=version, model=_model,
               verdict=_verdict,
               findings=findings, images=[],
               asked=(COLD_FRAMING.strip() + (" [%s]" % dropped if dropped else ""))[:400],
               answer_head=answer, head_cap=400, reached=True, path=None, seen_path=None, sent=sent,
               sha=sha, absent=absent, reach=reach, stripped=stripped, verdict_from=_verdict_from)
    print("  %s: LOOKED — %d finding(s) recorded" % (version, len(findings)))
    return True


def _run_with_base(base, version, sha, dry, prompt_out, answer_in, answer_model):
    """run_one with REVIEW_BASE set for THIS look only (a --backlog pass gives every version its own range)."""
    global REVIEW_BASE
    REVIEW_BASE = base
    try:
        return run_one(version, dry=dry, prompt_out=prompt_out, answer_in=answer_in, answer_model=answer_model)
    finally:
        REVIEW_BASE = None


def run_one(version, dry=False, prompt_out=None, answer_in=None, answer_model=""):
    version = SEL.norm_version(version)
    sha, why = commit_for(version)
    if not sha:
        print("  %s: cannot find the commit — %s" % (version, why))
        return False
    if REVIEW_BASE:
        _anc, _aw = _sh(["git", "merge-base", "--is-ancestor", REVIEW_BASE, sha], timeout=30)
        if _anc is None:
            print("  %s: --base %s is not an ancestor of %s - NOT asked (%s)"
                  % (version, REVIEW_BASE, sha[:8], _aw))
            return False
    elif not BUMP_ONLY:
        _db, _dwhy = _default_base(version, sha)
        if _db:
            print("  %s: the look covers the version's range, %s" % (version, _dwhy))
            return _run_with_base(_db, version, sha, dry, prompt_out, answer_in, answer_model)
        print("  %s: the look is the bound commit alone — %s" % (version, _dwhy))
    prompt, dropped, absent, reach, stripped = payload_for(sha)
    if prompt is None:
        print("  %s: cannot build the payload — %s" % (version, dropped))
        return False
    sent = SEL.code_was_transmitted(prompt)
    print("  %s  %s  payload: %d chars in %d fence(s)%s"
          % (version, sha[:8], sent["chars"], sent["fences"],
             ("  ⚠ " + dropped) if dropped else ""))
    # ⚠⚠ v3299 — SAY WHAT THIS LOOK DOES **NOT** COVER. `payload_for` runs `git show <sha>` on the
    # ONE commit carrying the version stamp, so every `fix:` commit landing after the bump and
    # before the push is NEVER SEEN BY ANY EYE — and the row that lands reads as though the push
    # was reviewed.
    # MEASURED 2026-09-18, v3298: four commits shipped in one push and the eye saw ONE of them.
    # The unseen three included the membership discriminator, which went through THREE cuts (two
    # wrong) and is the most consequential change in the push. The verdict then attacked
    # `_fnew > _dm + 0.5` — code SUPERSEDED two commits later. That is not the eye being wrong;
    # it is the gate handing it bytes that no longer ship.
    # ⚠ This prints the gap rather than closing it. Closing it means a wider payload, and the
    # payload already truncates at ~35% — the two are one problem and the cost is HIS call.
    # A guard that cannot state its own reach is the defect this repo keeps re-learning.
    # [[source-reading-guard]] [[zero-needs-a-denominator]]
    _rows = uncovered_commits(sha)
    if _rows is None:
        print("     ⚠ could not list commits after %s — what this look MISSES is UNKNOWN, not zero"
              % sha[:8])
    elif _rows:
        print("     ⚠ THIS LOOK COVERS %s ONLY. %d later commit(s) ship with it and are NOT "
              "reviewed:" % ((("%s..%s" % (REVIEW_BASE[:8], sha[:8])) if REVIEW_BASE else sha[:8]),
                             len(_rows)))
        for _r in _rows[:6]:
            print("        %s" % _r[:96])
        if len(_rows) > 6:
            print("        ... +%d more" % (len(_rows) - 6))
    if sent["chars"] == 0:
        print("     nothing to look at — the diff carried no code. NOT recorded.")
        return False
    if prompt_out:
        with io.open(prompt_out, "w", encoding="utf-8") as fh:
            fh.write(prompt)
        print("     payload written to %s — ask any eye, then --answer-in" % prompt_out)
        return True
    if answer_in:
        with io.open(answer_in, encoding="utf-8") as fh:
            # the PROMPT is passed so the echo can be stripped, and the model is read from the
            # answer's own bytes rather than inherited from whatever THIRD_EYE_MODEL happens to be
            # v3364 - AND `reach` TRAVELS TOO. v3363 added the parameter to record_answer and
            # the forwarding INTO the ledger, and wired NEITHER CALLER - so every row it wrote
            # carried reach=None, which is byte-identical to a row written before the field
            # existed. Found by using it: v3363's OWN row came back reach=NoneType while the eye
            # had said "REACH 2/7". [[the-unjoined-end]] - third time in this one area.
            return record_answer(version, fh.read(), sent, dropped,
                                 prompt_text=prompt, answer_model=answer_model, sha=sha,
                                 absent=absent, reach=reach, stripped=stripped)
    if dry:
        return True
    answer, reached, awhy, structured = ask(prompt, sha=sha)
    if not reached:
        SEL.record(version=version, model=EYE_MODEL, verdict="", findings=[], images=[],
                   asked=COLD_FRAMING.strip()[:200],
                   answer_head=(answer or ""), head_cap=200, reached=False,
                   path=None, seen_path=None, sent=sent, sha=sha)
        print("     EMPTY SEAT — %s  (recorded as unreached, never as agreement)" % awhy)
        return False
    # ⚠⚠⚠ v3221 — ONE RECORDER, NOT TWO. v3220 fixed the empty-seat guard in `record_answer` and
    # this path never called it: the CLI door recorded inline, so it stripped no echo and ran no
    # `_PROVIDER_ERROR_RX`. `ask()` treats "exit 0 and >= 40 chars" as a look — and a Grok CLI that
    # exits 0 with a long usage-limit or auth body is exactly that. So the SAME false-LOOKED bug
    # REG-1017 documents was still live on the DEFAULT door (and on `--backlog`), one function
    # away from its own fix. Found by the Grok seat reviewing v3220, which is the version that
    # fixed the other half.
    #
    # Fixing one copy of a rule and leaving its twin is the defect this repo keeps finding. The
    # answer is not a second guard here — it is routing both doors through the one guard.
    # [[copy-drift]] [[sweep-dont-ask]] [[the-unjoined-end]]
    # v3229 — the transport names the family when the answer does not. FALLBACK ONLY:
    # record_answer prefers the model the answer's own bytes name.
    return record_answer(version, answer, sent, dropped, prompt_text=prompt,
                         answer_model=_model_from_transport(), sha=sha,
                         absent=absent, reach=reach,
                         stripped=stripped, structured=structured)


def main(argv):
    install_cleanup_on_signals()
    sweep_stale_eye_cwds()
    sweep_stale_eye_sessions()          # REG-2731
    ap = argparse.ArgumentParser()
    ap.add_argument("version", nargs="?")
    ap.add_argument("--backlog", action="store_true",
                    help="every version the ledger still says OWES a look")
    ap.add_argument("--dry", action="store_true", help="build and measure, send nothing")
    ap.add_argument("--prompt-out", help="write the measured payload here instead of asking")
    ap.add_argument("--answer-in", help="record this answer against the measured payload")
    # ⚠ v3216 — for an eye whose output does not NAME its model. Without it the row records an
    # empty model, family_of() returns None, and the look does NOT discharge a cross-family debt —
    # which is the right way to fail: an unattributable answer is not evidence about who looked.
    ap.add_argument("--answer-model", default="",
                    help="the model that produced --answer-in, when the answer does not say")
    ap.add_argument("--base", help="widen the look to every change from this commit to the version's "
                                   "bound commit (a batch whose code landed before its stamp)")
    ap.add_argument("--files", nargs="+", default=None,
                    help="v3897 (REG-3699) - a follow-up look at only these paths (*.html included): the files a "
                         "version's look was not shown")
    ap.add_argument("--bump-only", action="store_true",
                    help="look at the bound commit alone (the pre-v3526 keyhole); the default is the version's range")
    a = ap.parse_args(argv)
    if a.files:
        global REVIEW_FILES
        REVIEW_FILES = [f for f in a.files if f and not f.startswith("-")]
        if not REVIEW_FILES:
            print("  --files named no path - NOT asked")
            return 2
    if a.bump_only:
        global BUMP_ONLY
        BUMP_ONLY = True
    if a.base:
        global REVIEW_BASE
        _full, _bw = _sh(["git", "rev-parse", "--verify", "%s^{commit}" % a.base], timeout=30)
        if not _full:
            print("  --base %s is not a commit (%s) - NOT asked" % (a.base, _bw))
            return 2
        REVIEW_BASE = _full.strip()
    if a.backlog:
        # ⚠⚠ v2848 — THE BACKLOG COMMAND HAS BEEN CRASHING, SO NOTHING REPORTED THE QUEUE.
        # `SEL.audit(None)` returns a list of DICTS — {version, attempts, empty, author, looks,
        # bound, unbound} — and this unpacked each row into `v, st`. Iterating a dict yields its
        # KEYS, and seven keys will not unpack into two, so every invocation died with
        # `ValueError: too many values to unpack (expected 2)`. The one command whose entire job is
        # "show me what is stacking up" answered nothing but a traceback, which is why the second
        # eye backlog was only ever discovered by a push being REFUSED at the gate.
        # ⚠ A version OWES a look when it has ZERO real looks. `empty` (a seat that was offered and
        # came back dark) and `author` (a look by the same family that wrote the code) are NOT
        # looks — counting them would clear the queue without anyone having looked.
        # [[the-unjoined-end]] [[unknown-stays-unknown]]
        _rows = SEL.audit(None) if callable(getattr(SEL, "audit", None)) else []
        _known = {r.get("version") for r in _rows if isinstance(r, dict)}
        owed = [r.get("version") for r in _rows
                if isinstance(r, dict) and not int(r.get("looks") or 0)]
        # ⚠⚠ AND THE VERSIONS THE LEDGER HAS NEVER HEARD OF. See versions_in_history(): a shipped
        # version with no row is the STRONGEST case of owing a look, and it was the only one this
        # command could not report. Ask the same predicate the gate asks.
        _shipped, _why = versions_in_history()
        for _v in _shipped:
            if _v not in _known and SEL.owes_a_look(_v):
                owed.append(_v)
        owed = sorted(set(owed), key=lambda x: -int(x[1:]) if x[1:].isdigit() else 0)
        if not owed:
            # ⚠ a zero carries its denominator, or it is UNKNOWN rather than clean.
            print("  nothing owes a look — %d ledger row(s), %d shipped version(s) examined.%s"
                  % (len(_rows), len(_shipped), (" (%s)" % _why) if _why else ""))
            return 0
        print("  %d version(s) owe a look: %s     [%d ledger row(s), %d shipped version(s) examined]"
              % (len(owed), ", ".join(owed), len(_rows), len(_shipped)))
        # 2026-10-02 (REG-1703) - `--backlog --dry` SENT A REAL LOOK. This called run_one(v) and dropped --dry, so the
        # flag documented as "build and measure, send nothing" asked Grok for real; a caller's time bound then killed
        # this process and orphaned the grok child, whose answer nothing could record.
        ok = all(run_one(v, dry=a.dry) for v in owed)
        return 0 if ok else 1
    if not a.version:
        ap.print_help()
        return 2
    return 0 if run_one(a.version, dry=a.dry, prompt_out=a.prompt_out,
                        answer_model=a.answer_model,
                        answer_in=a.answer_in) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
