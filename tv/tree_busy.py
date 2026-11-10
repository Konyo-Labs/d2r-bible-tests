# -*- coding: utf-8 -*-
"""v3330 (#72) — IS THE TREE BEING GRADED RIGHT NOW? One definition, so nobody has to remember.

His ruling, from the #46 false-alarm incident: "do not write while a gate runs" must be a REFUSAL,
not a habit. The rule is already written down in CLAUDE.md, in regression-guard, and in every
staged apply-script — as PROSE, four times over. Prose is what fails.

⚠ WHY IT MATTERS, and it is not tidiness: `hooks/pre-push` grades the WORKING TREE, not the commit
(REG-1131). A version banked while the gate is mid-run gets a green verdict about bytes that are
not the ones shipping. That is the most expensive kind of wrong answer this repo produces, because
it looks exactly like a correct one.

TWO INDEPENDENT SIGNALS, because each misses a case the other catches:

  1. THE GATE LOCK. `run_gates._claim_the_tree` takes an exclusive flock on
     `<tmpdir>/d2r_gates_<resolved-tree-key>.lock`, keyed on `os.path.realpath(REPO)` so his two
     worktrees never collide. flock deliberately: the kernel drops it when the process dies, so a
     crashed run cannot leave a stale lock that refuses every future one — its own comment says
     "a pid file would need reaping logic, and reaping logic is how a lock starts lying."
     We try the SAME lock non-blocking and release it immediately; failure means a gate holds it.

  2. A RUNNING pre-push HOOK. The hook does more than run_gates — renders, console demos,
     Playwright smoke — and holds the tree across all of it, including stretches where the gate
     lock is not held. Checking only the lock would call the tree free during the smoke.

⚠⚠ ITS REACH, STATED RATHER THAN IMPLIED. This cannot be forced on an ad-hoc edit. A python
heredoc that writes bible.html directly will never consult a module it does not import, and a
guard that claimed otherwise would read as complete while being optional. What it CAN do is stand
at the one chokepoint every ship passes — `bump_version.py` — so the damaging case becomes
structurally impossible even when the discipline slips. [[the-unjoined-end]]
"""
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# This module PRINTS its reason (main() writes the busy sentence to stderr) and those sentences
# carry non-ASCII. On a cp1255 console that crash happens WHILE REPORTING, so a tree that is
# merely busy would exit non-zero for a reason unrelated to the check — the report killing the
# messenger. Caught by the pre-push encoding gate, which refused this version for exactly it.
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
REPO = os.path.dirname(HERE)


def _lock_path(repo=None):
    """The exact path run_gates locks. Keyed on the RESOLVED tree, same as the holder."""
    key = os.environ.get("D2R_GATE_LOCK_KEY") or os.path.realpath(repo or REPO)
    safe = re.sub(r"[^A-Za-z0-9]+", "_", key).strip("_")[-80:]
    return os.path.join(tempfile.gettempdir(), "d2r_gates_%s.lock" % safe)


def _gate_lock_held(repo=None):
    """-> (held, who). `held` is None when the question could not be asked at all.

    A lock file that is not there is a measurement: nobody holds it. That answer does not
    need fcntl. fcntl is asked only once a file exists, because that is the moment a holder
    might be inside it. A missing module with a present file stays UNKNOWN.
    """
    p = _lock_path(repo)
    if not os.path.exists(p):
        return False, ""
    try:
        import fcntl
    except Exception:
        return None, "fcntl is unavailable on this platform, so the gate lock cannot be asked"
    try:
        fh = open(p, "a+")
    except Exception as e:
        return None, "the gate lock file could not be opened (%s)" % type(e).__name__
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        # We got it, so nobody else holds it. Release AT ONCE — holding it here would make this
        # check the very collision it exists to prevent.
        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        return False, ""
    except OSError:
        try:
            fh.seek(0)
            who = (fh.read() or "").strip()
        except Exception:
            who = ""
        return True, (who or "an unnamed gate run")
    finally:
        try:
            fh.close()
        except Exception:
            pass


#: Commands that merely READ a file. Kept because it is the cheapest, clearest rejection.
_READERS = ("vi", "vim", "nvim", "nano", "pico", "emacs", "view",
            "less", "more", "cat", "bat", "head", "tail",
            "grep", "egrep", "fgrep", "rg", "ag", "ack",
            "open", "code", "subl", "diff", "wc", "md5", "shasum", "file", "stat",
            "find", "rsync", "tar", "cp", "mv", "ln", "du", "xargs", "node")

#: Things that legitimately EXECUTE something else. If one of these leads, whatever follows is
#: being RUN, even behind flags of its own (`stdbuf -o0 <hook>`).
_EXEC = ("sh", "bash", "zsh", "dash", "ksh", "perl",
         "nohup", "env", "stdbuf", "time", "sudo", "ionice", "nice", "setsid")

_HOOK = "hooks/pre-push"

#: git subcommands that legitimately take `push` as an ARGUMENT — a branch, a ref, a pattern.
#: ⚠⚠ v3336 — THIS REPLACED A FLAG-SKIPPING PARSE, AND A SECOND EYE MEASURED WHY.
#: v3334 found the subcommand by stepping over global flags, consuming one extra token for each
#: flag in a known list. That list can never be complete, and MEASURED 2 of 6 wrong — both FALSE
#: NEGATIVES, the direction that banks a version mid-grade:
#:     git --git-dir /path/with spaces push origin   -> subcommand read as 'spaces'
#:     git --super-prefix foo/ push origin           -> subcommand read as 'foo/'
#: A path containing a space, or any flag the list has not heard of, silently hid a real push.
#: THE SET OF VALUE-TAKING FLAGS IS OPEN; THE SET OF SUBCOMMANDS THAT TAKE `push` AS AN ARGUMENT
#: IS SMALL AND STABLE. So scan for whichever comes FIRST — `push`, or one of these — and let an
#: unrecognised bare token (a flag's value, an unknown subcommand) simply keep scanning.
_GIT_TAKES_PUSH_AS_ARG = (
    "branch", "checkout", "switch", "log", "tag", "config", "remote", "show", "diff",
    "add", "commit", "rebase", "merge", "status", "stash", "grep", "reflog", "describe",
    "rev-parse", "cherry-pick", "restore", "worktree", "notes", "bisect", "blame")


#: Global flags whose NEXT TOKEN is a value, never a subcommand.
#: ⚠ v3338 — WITHOUT THIS, A VALUE COULD IMPERSONATE A SUBCOMMAND. A second eye found it:
#: `git -C log push origin main` skipped the `-C` but then read the DIRECTORY `log` as the
#: subcommand, matched it in _GIT_TAKES_PUSH_AS_ARG and returned False on a real push. v3336
#: dropped value-consumption deliberately, because the flag list can never be complete — but the
#: fix for that was the SCAN-ONWARD fallback below, not blindness to the flags we DO know.
#: Both together: known value-flags consume their value; an unknown bare token keeps scanning.
_GIT_VALUE_FLAGS = ("-c", "-C", "--git-dir", "--work-tree", "--namespace",
                    "--exec-path", "--super-prefix", "--config-env")


def _git_runs_push(toks):
    """Does this git command line RUN `push`? -> bool

    Fails toward TRUE on an unknown bare token, because a missed push is the dangerous direction
    here and a spurious refusal only costs one re-run.

    ⚠ STATED LIMIT, NOT A BUG TO FIND LATER: an ALIAS cannot be seen from the command line.
    `git -c alias.p=push p` runs a push and reads as False here, because nothing in the argv says
    what `p` expands to. Resolving it would mean running `git config`, which is a second process on
    every liveness check. The flock signal covers the window this misses — and this is written down
    so the next reader does not rediscover it as a defect.
    """
    i = 1
    while i < len(toks):
        t = toks[i]
        if t in _GIT_VALUE_FLAGS:
            i += 2               # the next token is its VALUE and can never be the subcommand
            continue
        if t.startswith("-"):
            i += 1
            continue
        b = os.path.basename(t)
        if b == "push":
            return True
        if b in _GIT_TAKES_PUSH_AS_ARG:
            return False         # a later `push` is its ARGUMENT, not the subcommand
        i += 1                   # an unlisted flag's value looks like this — keep scanning
    return False


def _is_hook_invocation(cmd):
    """Does this command line RUN the pre-push hook, or merely NAME it? -> bool

    ⚠⚠ v3334 — THIRD CUT, AND THE SECOND EYE MEASURED THE SECOND ONE CLOSING THE LANE.
    v3331 allow-listed interpreters and failed OPEN (5 of 10 wrong, all false negatives).
    v3332 inverted to a reader deny-list and failed CLOSED far too hard: MEASURED 7 of 11 wrong,
    all FALSE POSITIVES — `find -path */hooks/pre-push`, `rsync -a hooks/pre-push /tmp/`,
    `git branch push`, `git log --grep push`, `node tool.js hooks/pre-push.json` each blocked
    every bump. A guard that refuses on ordinary inspection commands is an off switch.
    [[strictness-that-closes-the-lane]]

    NEITHER LIST WORKS ALONE. What decides it is POSITION: the hook counts only where it could
    plausibly BE the program — first token, or behind something that executes things. A token
    sitting after a flag is an ARGUMENT, not a program. Unknown leaders still fail CLOSED, so the
    dangerous direction stays guarded.
    """
    cmd = cmd or ""
    toks = [t for t in cmd.split() if t]
    # A leading `K=V` is an environment assignment, not the program.
    while toks and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", toks[0]):
        toks.pop(0)
    if not toks:
        return False
    base0 = os.path.basename(toks[0])

    if base0 == "git":
        # v3332 counted ANY bare `push` token, so `git branch push` read as a push.
        return _git_runs_push(toks)
    if base0 in _READERS:
        return False

    # The hook must END at a boundary: `hooks/pre-push.log` and `-pre-push.bak` are other files.
    m = re.search(re.escape(_HOOK) + r"(?![\w.\-])", cmd)
    if not m:
        return False
    if os.path.basename(toks[0]).endswith("pre-push") or toks[0].endswith(_HOOK):
        return True                      # executed directly
    if base0 in _EXEC:
        return True                      # a known runner leads
    # Anything flagged before the hook makes it an argument to that command.
    before = cmd[:m.start()].split()
    if any(t.startswith("-") for t in before[1:]):
        return False
    return True                          # unknown leader -> fail CLOSED


def _windows_command_lines():
    """Process id and command line on Windows. -> [str] | None

    pgrep is not on that machine. PowerShell's process list is. A non-zero exit is
    UNKNOWN, never an empty tree.
    """
    script = (
        "Get-CimInstance Win32_Process | "
        "ForEach-Object { '{0} {1}' -f $_.ProcessId, $_.CommandLine }"
    )
    r = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10,
    )
    if r.returncode != 0:
        return None
    return (r.stdout or "").splitlines()


def _command_lines():
    """-> [str] | None. None means the list could not be asked."""
    if sys.platform == "win32":
        return _windows_command_lines()
    r = subprocess.run(
        ["pgrep", "-fl", "hooks/pre-push|git"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10,
    )
    return (r.stdout or "").splitlines()


def _prepush_running(repo=None):
    """-> (running, detail). None when the process list could not be asked — never False on failure."""
    try:
        lines = _command_lines()
    except Exception as e:
        return None, "the process list could not be asked (%s)" % type(e).__name__
    if lines is None:
        return None, "the process list could not be asked"
    hits = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        pid, _, cmd = line.partition(" ")
        # REG-1846 - A LINE IS A PROCESS ONLY WHEN IT STARTS WITH A PID. pgrep -fl prints a process whose argv holds
        # newlines (a `grok -p <whole diff>` second eye) as several lines; each continuation line was parsed as its own
        # "pid cmd" record, so prose inside another program's prompt read as a running hook ("pid READ-ONLY") and
        # refused bump_version on 2026-10-06 while an eye looked at a diff that mentioned hooks/pre-push.
        if not pid.isdigit():
            continue
        if _is_hook_invocation(cmd):
            hits.append(pid)
    if not hits:
        return False, ""
    return True, "pid %s" % ", ".join(hits[:4])


def why(repo=None):
    """-> None when the tree is free to write, else ONE sentence naming the holder.

    ⚠ UNKNOWN IS NOT FREE. If neither signal can be asked, this returns a sentence saying so
    rather than None. A writer that cannot find out whether a gate is running must not assume the
    happy answer — that is the confident-zero shape this repo keeps paying for.
    [[unknown-stays-unknown]]
    """
    held, who = _gate_lock_held(repo)
    if held:
        return ("a gate run holds this tree (%s). It grades the WORKING TREE, so writing now "
                "makes its verdict describe bytes that are not the ones shipping." % who)
    running, detail = _prepush_running(repo)
    if running:
        return ("a pre-push hook is running (%s). It grades the WORKING TREE across renders, "
                "console demos and the Playwright smoke — writing now makes its green verdict "
                "about bytes that are not shipping." % detail)
    # ⚠⚠ `or`, NOT `and` — THE SECOND EYE FOUND THIS TOO (v3331). The first cut required BOTH
    # signals to be unaskable before saying UNKNOWN. So a blind flock plus a pgrep that cleanly
    # found nothing fell straight through to `return None` = FREE, with the PRIMARY signal dark.
    # That is the exact confident-zero this module was written to prevent, inside the module that
    # prevents it. One signal silent is enough to refuse. [[unknown-stays-unknown]]
    _dark = []
    if held is None:
        _dark.append(who or "the gate lock could not be read")
    if running is None:
        _dark.append(detail or "the process list could not be read")
    if _dark:
        return ("whether a gate is running could not be determined (%s). That is UNKNOWN, "
                "not free." % "; ".join(_dark))
    return None


def _is_ship_command(cmd):
    """card #200 guard 2 - a running ship: python running tv/ship_when_green.py (never a grep or an editor naming it)"""
    c = str(cmd or "")
    return "ship_when_green.py" in c and "python" in c.lower() and not c.lstrip().startswith(("grep", "ugrep", "rg "))


def ship_beside(rows, self_pid):
    """card #200 guard 2 (REG-3664) - ONE PUSH AT A TIME ON THIS MAC. Is a ship running here that is NOT an ancestor of
    self_pid (the ship's own main push runs this hook as its descendant, and that one is allowed)? rows:
    self_prove.process_rows() [(pid, ppid, age, cmd)]. -> (True | False | None, why). None = the list could not be read.
    MEASURED 11-10: Claude's feature-branch push sat 85 min in its pre-push gate beside v3894's ship pre-flight and turned
    two laws red there (a push grading), costing a whole attempt. Pure."""
    if rows is None:
        return None, "the process list could not be read - UNKNOWN, not free"
    parent = dict((str(p), str(pp)) for p, pp, _a, _c in rows)
    anc, cur = set(), str(self_pid)
    while cur and cur not in anc:
        anc.add(cur)
        cur = parent.get(cur)
    hits = [str(p) for p, _pp, _a, cmd in rows if _is_ship_command(cmd) and str(p) not in anc]
    if hits:
        return True, ("a ship is running on this Mac (pid %s) - its pre-flight and gates grade a tree this push would load; "
                      "push after it lands (card #200 guard 2)" % ", ".join(hits[:3]))
    return False, ""


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["--ship-beside"]:
        # card #200 guard 2 - the pre-push hook asks: exit 3 = a ship runs beside this push, 0 = none, 2 = UNKNOWN
        try:
            import self_prove as _sp
            busy, said = ship_beside(_sp.process_rows(), argv[1] if len(argv) > 1 else os.getppid())
        except Exception as e:
            busy, said = None, "the ship check failed (%s)" % type(e).__name__
        sys.stdout.write((said or "no ship runs beside this push") + "\n")
        return 3 if busy is True else (0 if busy is False else 2)
    w = why()
    if w:
        sys.stderr.write("tree is BUSY: %s\n" % w)
        return 1
    sys.stdout.write("tree is free\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
