# -*- coding: utf-8 -*-
"""REG-2360 — A TEST RUN WITH A LEAKED GIT_DIR NEVER WRITES THE REAL REPO, AND NEVER SETS core.bare.

⚠ WHAT IT COST. Inside a git hook, git exports GIT_DIR - absolute, `<main>/.git/worktrees/<name>` when the push comes
from a linked worktree - and GIT_DIR beats cwd= (and -C) in every git child. On the v3783 pushes (2026-10-21) a law that
builds a temp repo committed two fixture commits onto the push branch, so the commit-stamps law read a half-bumped HEAD
and refused pushes #10 and #11; and a `git init` in a temp dir re-initialised the REAL repo's common config to
core.bare=true - his main checkout answered "this operation must be run in a work tree" to every git command for 2.5 h,
and his console's pull lane failed, before anyone looked. Measured again for this law on a fixture standing in for his
repo: each of the first five laws below, unscrubbed, either moved the worktree branch or set core.bare=true (or both);
the sixth is test_control's grok-seat case, the one that committed onto his push branch that night.

THE CLASS FIX IS THE HOOK. hooks/pre-push reads the one thing it needs from that pointer (the git dir), then unsets
every variable git itself calls local to a repository (`git rev-parse --local-env-vars`, plus GIT_DIR / GIT_WORK_TREE /
GIT_INDEX_FILE by name) before any stage runs. The commit-stamps law reached the pushed commit ONLY through that leak
inside heart2's sandbox (a copy with no .git), so the hook hands it the commit by name instead: TV_PUSHED_GIT_DIR +
TV_PUSHED_COMMIT. And each law that builds a temp repo scrubs GIT_* for its OWN scope (a module-wide strip once made the
commit-stamps law skip), so a run outside the hook - by hand, from another hook, a census - is safe as well.

REG-2394 / REG-2395 (the cross-family review of Push A2, 2026-10-22). The first cut unset GIT_CONFIG_PARAMETERS and
GIT_CONFIG_COUNT with the pointer - git's list names them - and they are how `git -c k=v push` reaches a hook: MEASURED
on a throwaway repo, `git -c push.default=upstream push origin HEAD:main` had @{push} = origin/main before the loop and
"cannot resolve" after it, so every stage after the scrub ran without the push's own options. They carry options, never
a pointer, and they stay. And the tv-suites lane asked `git diff @{push}..` with no fallback and no word: on a branch
whose @{push} does not resolve (his push branches track origin/main and push as HEAD:main) every suite in it was
skipped in silence. The hook now asks the range once, at the top (@{push}, else origin/main), and the lane RUNS when the
range is unknown and names the range it read. Both are driven here: a REAL `git -c` push through a hook built from the
hook's own marked blocks, and the lane's three outcomes on fixture branches shaped like his.

REG-2551 (the Grok CLI review of Push A2, MEDIUM M2). The scrub cases run ONLY the marked block, so an `export
GIT_DIR=...` - or a `GIT_DIR=... cmd` prefix, or the same for GIT_WORK_TREE / GIT_INDEX_FILE / GIT_OBJECT_DIRECTORY /
GIT_COMMON_DIR - written anywhere in the hook AFTER `# <<< scrub-git-env` kept every one of them green while each stage
after it got the pointer back. NoStageAfterTheScrubPointsGitBack reads the WHOLE hook after the block as code: comments
out, quotes followed the way bash nests them, and every heredoc body read whole - none is excluded, so none has to be
shown to be data. Its reader is driven on every form, and on the shapes that must stay quiet, before its verdict counts.

These cases DRIVE all three halves against a FIXTURE repo with a linked worktree, leaked exactly the way git leaks it:
the hook's marked blocks in a real bash, the commit-stamps law on a named fixture commit, and every temp-repo law
run whole under GIT_DIR=<the fixture worktree's git dir>, after which the fixture must be byte-for-byte what it was.
Its reach, stated: the 14 other laws that `git init` a temp dir (test_a_suite_run_is_reused_only_on_identical_bytes,
test_a_version_bump_carries_..., test_the_eye_reads_the_commit_read_only, ...) are covered at push time by the hook's
scrub, not by a scope-scrub of their own - not swept here, because each edit would put a law in a push's proving set.
[[regression-guard]] [[feedback-fixtures-never-touch-live-data]] RED_PROOF below.
"""
import ast
import hashlib
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import warnings

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()       # these print non-ASCII; a cp1255 console must not crash while REPORTING
except Exception:
    pass

#: a literal path, so the heart keys this law on the hook's bytes (a join of "hooks" and "pre-push" names no file)
HOOK_REL = "hooks/pre-push"
HOOK = os.path.join(ROOT, *HOOK_REL.split("/"))

#: the laws that build a temp repo, with the unittest selection each is driven through: the first five were each
#: MEASURED writing the fixture when unscrubbed, the sixth wrote his real push branch on the v3783 pushes. File names
#: are literals so the heart keys this law on their bytes.
TEMP_REPO_LAWS = (
    ("test_the_author_is_read_from_the_stamp.py", "test_the_author_is_read_from_the_stamp"),
    ("test_a_landed_update_is_not_an_edit.py", "test_a_landed_update_is_not_an_edit.TheLauncherUsesTheSameRule"),
    ("test_a_proven_verdict_is_reused_only_on_identical_bytes.py",
     "test_a_proven_verdict_is_reused_only_on_identical_bytes.TheKeyNamesEveryInput"
     ".test_a_named_file_git_does_not_track_is_not_a_key_input"),
    ("test_every_pc_proves_itself.py", "test_every_pc_proves_itself.TheTreeIsToldApart"),
    ("test_a_stale_git_lock_is_cleared_and_said.py", "test_a_stale_git_lock_is_cleared_and_said"),
    ("test_control.py", "test_control.TestV2143TheSecondEyeCannotBeSkippedQuietly"
                        ".test_a_claude_look_counts_when_the_commit_is_the_grok_seat"),
)
#: the variables a hook must not hand a stage (git's own list is asked at run time; these three by name)
POINTERS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE")
#: REG-2394 - on git's list, but they carry the push's own `git -c` options, never a pointer: the scrub keeps them
CARRIERS = ("GIT_CONFIG_PARAMETERS", "GIT_CONFIG_COUNT")
#: REG-2551 - the pointers no line after the scrub may assign or export again: git's own list is asked at run time (less
#: CARRIERS), and these five are named so the law keeps them whatever a git version lists
REEXPORTED = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_COMMON_DIR")
#: REG-2551 - planted in a copy of the REAL hook where the reader could lose its place (the first line after the scrub,
#: after each heredoc, the end): a quoted `#` comes first, so a reader that took it for a comment would miss the export
#: behind it and read the hook clean
CANARY = 'echo "a #b"; export GIT_DIR=/tmp/canary\n'
#: the fixture's git never reads his global or system config (a push.default there would decide @{push} for it)
_HERMETIC = {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_TERMINAL_PROMPT": "0"}
_IDENT = ["-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid", "-c", "commit.gpgsign=false",
          "-c", "init.defaultBranch=main"]


def _clean_env(**extra):
    """os.environ without one GIT_* variable, plus `extra` - a child run gets exactly the leak it is handed. -> dict"""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(extra)
    return env


def _git(*args, **kw):
    """the fixture's own git: never his global or system config, never a prompt"""
    r = subprocess.run(["git"] + _IDENT + list(args), capture_output=True, text=True, timeout=60,
                       env=_clean_env(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT="0"),
                       **kw)
    if r.returncode != 0:
        raise AssertionError("fixture git %s failed: %s" % (" ".join(args), (r.stderr or "").strip()[-300:]))
    return (r.stdout or "").strip()


def _sha(path):
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except OSError:
        return None


class _Fixture(object):
    """A repo standing in for HIS: one commit, and a linked worktree whose git dir is what the hook would leak."""

    def __init__(self, root):
        self.real = os.path.join(root, "real")
        self.wt = os.path.join(root, "wt")
        os.makedirs(self.real)
        _git("init", "-q", self.real)
        _git("-C", self.real, "config", "core.autocrlf", "false")  # #107 REG-3626 - the fixture's bytes, not the PC's git default
        with io.open(os.path.join(self.real, "f.txt"), "w", encoding="utf-8") as fh:
            fh.write(u"one\n")
        _git("-C", self.real, "add", "f.txt")
        _git("-C", self.real, "commit", "-q", "-m", "one")
        _git("-C", self.real, "worktree", "add", "-q", self.wt, "-b", "wtb")
        self.gitdir = os.path.realpath(_git("-C", self.wt, "rev-parse", "--absolute-git-dir"))

    def state(self):
        """Every write a fixture git call could make shows here: refs, objects, the common config, both indexes."""
        return {
            "refs": _git("-C", self.real, "for-each-ref", "--format=%(refname) %(objectname)"),
            "objects": _git("-C", self.real, "count-objects", "-v"),
            "wtHEAD": _git("--git-dir=" + self.gitdir, "rev-parse", "HEAD"),
            "bare": _git("-C", self.real, "config", "--get", "core.bare"),
            "config": _sha(os.path.join(self.real, ".git", "config")),
            "index": _sha(os.path.join(self.real, ".git", "index")),
            "wtIndex": _sha(os.path.join(self.gitdir, "index")),
        }


class _PushFixture(object):
    """REG-2395 - a repo standing in for HIS with a bare remote standing in for GitHub (main pushed there), and a linked
    worktree on a branch that TRACKS origin/main - his push branches' shape: under push.default=simple its @{push} does
    not resolve ("cannot resolve 'simple' push to a single destination"). remote=False: no remote at all."""

    def __init__(self, root, remote=True):
        self.real = os.path.join(root, "real")
        self.wt = os.path.join(root, "wt")
        self.remote = os.path.join(root, "remote.git") if remote else None
        os.makedirs(self.real)
        _git("init", "-q", self.real)
        _git("-C", self.real, "config", "core.autocrlf", "false")  # #107 REG-3626 - the fixture's bytes, not the PC's git default
        with io.open(os.path.join(self.real, "f.txt"), "w", encoding="utf-8") as fh:
            fh.write(u"one\n")
        _git("-C", self.real, "add", "f.txt")
        _git("-C", self.real, "commit", "-q", "-m", "one")
        if remote:
            _git("init", "-q", "--bare", self.remote)
            _git("-C", self.remote, "config", "core.autocrlf", "false")  # #107 REG-3626 - the fixture's bytes, not the PC's git default
            _git("-C", self.real, "remote", "add", "origin", self.remote)
            _git("-C", self.real, "push", "-q", "origin", "main")
            _git("-C", self.real, "fetch", "-q", "origin")
        _git("-C", self.real, "worktree", "add", "-q", self.wt, "-b", "wtb")
        if remote:
            _git("-C", self.wt, "branch", "-q", "--set-upstream-to=origin/main")

    def commit(self, rel):
        """one commit on the worktree branch that changes `rel` (repo-relative)"""
        p = os.path.join(self.wt, *rel.split("/"))
        if not os.path.isdir(os.path.dirname(p)):
            os.makedirs(os.path.dirname(p))
        with io.open(p, "a", encoding="utf-8") as fh:
            fh.write(u"x\n")
        _git("-C", self.wt, "add", rel)
        _git("-C", self.wt, "commit", "-q", "-m", "change " + rel)


def _bash():
    import posix_shell as _PS   # REG-1642 - a real POSIX bash; on a Windows PC `bash` is the WSL launcher
    return _PS.bash()


def _block(name):
    with io.open(HOOK, encoding="utf-8") as fh:
        src = fh.read()
    i = src.index("# >>> %s\n" % name)
    j = src.index("# <<< %s\n" % name, i)
    return src[i:j], src[:i].count("\n")


#: REG-2551 - where a `#` starts a WORD in bash (and so a comment): after a blank, a line start or an operator
_WORD_START = " \t\n;&|()<>"
_HEREDOC = re.compile(r"<<(-?)[ \t]*(?:'([^'\n]*)'|\"([^\"\n]*)\"|\\?([A-Za-z_][A-Za-z0-9_]*))")


def _shell_code(src, kinds=None):
    """REG-2551 - bash source as bash reads it: every comment out, every heredoc body kept WHOLE.
    -> (code, pos, heredocs, open) - pos[k] is the index in `src` of code[k], heredocs [(delimiter, closed, the index
    just past its last line)], and open the quote / substitution frames still open at the end (anything but [] means
    this reader lost bash's place).

    A `#` opens a comment only at the start of a word and outside quotes, so "#42", $#, ${#a} and ${x#y} stay code.
    Quotes are followed the way bash nests them: '...' is literal; $'...' takes backslash escapes, an escaped quote
    included; "..." takes backslash escapes and opens $(...) and `...`; $(...) is a fresh command context, where quotes
    and comments start again. A backslash-newline joins its two lines, as bash does. A heredoc body (the lines after its
    opener's line, up to its delimiter) is NOT stripped: under an unquoted delimiter bash expands every $(...) in it,
    and a quoted one is data whose text costs nothing to read. Its reach, stated: a `case` pattern's `)` inside $(...)
    is read as that $(...)'s close (the hook has none).

    REG-2454 - `kinds`, when a list, gets the frame each code character was read in (top, cmd, sq, dq, ansi,
    bq), so a reader can tell a word bash RUNS from a word inside quotes."""
    out, pos, heredocs, pending = [], [], [], []
    stack = [["top", 0]]
    i, n = 0, len(src)

    def put(text, at):
        for k, ch in enumerate(text):
            out.append(ch)
            pos.append(at + k)
            if kinds is not None:
                kinds.append(stack[-1][0])

    while i < n:
        c, kind = src[i], stack[-1][0]
        if kind == "sq":
            put(c, i)
            i += 1
            if c == "'":
                stack.pop()
            continue
        if kind == "ansi":                               # $'...': a backslash escapes the next character, \' too
            step = 2 if c == "\\" else 1
            put(src[i:i + step], i)
            i += step
            if c == "'":
                stack.pop()
            continue
        if c == "\n":
            put(c, i)
            i += 1
            if pending and kind in ("top", "cmd"):      # the opener's line has ended: its bodies follow, in order
                for delim, tabs in pending:
                    closed = False
                    while i < n and not closed:
                        j = src.find("\n", i)
                        nxt = n if j < 0 else j + 1
                        line = src[i:nxt].rstrip("\n")
                        put(src[i:nxt], i)
                        i = nxt
                        closed = (line.lstrip("\t") if tabs else line) == delim
                    heredocs.append((delim, closed, i))
                pending = []
            continue
        if c == "\\":
            if src[i + 1:i + 2] == "\n":
                put(" ", i)                              # a line continuation: one logical line, as bash reads it
            else:
                put(src[i:i + 2], i)
            i += 2
            continue
        if kind == "bq":
            put(c, i)
            i += 1
            if c == "`":
                stack.pop()
            continue
        if kind == "dq":
            if src.startswith("$(", i):
                stack.append(["cmd", 0])
                put("$(", i)
                i += 2
                continue
            if c == '"':
                stack.pop()
            elif c == "`":
                stack.append(["bq", 0])
            put(c, i)
            i += 1
            continue
        # a command context: the top level, or inside $(...)
        if c == "#" and (i == 0 or src[i - 1] in _WORD_START):
            j = src.find("\n", i)
            i = n if j < 0 else j
            continue
        if src.startswith("$(", i):
            stack.append(["cmd", 0])
            put("$(", i)
            i += 2
            continue
        if src.startswith("$'", i):
            stack.append(["ansi", 0])
            put("$'", i)
            i += 2
            continue
        if src.startswith("<<", i) and not src.startswith("<<<", i) and (i == 0 or src[i - 1] != "<"):
            m = _HEREDOC.match(src, i)
            if m:
                pending.append((next(g for g in m.groups()[1:] if g is not None), bool(m.group(1))))
                put(m.group(0), i)
                i = m.end()
                continue
        if c == "'":
            stack.append(["sq", 0])
        elif c == '"':
            stack.append(["dq", 0])
        elif c == "`":
            stack.append(["bq", 0])
        elif c == "(" and kind == "cmd":
            stack[-1][1] += 1
        elif c == ")" and kind == "cmd":
            if stack[-1][1]:
                stack[-1][1] -= 1
            else:
                stack.pop()
        put(c, i)
        i += 1
    return "".join(out), pos, heredocs, [f[0] for f in stack[1:]]


#: REG-2454 (A2's Grok low 1) - THE HOOK'S STAGE GRAMMAR. The first cut counted a line as a stage only when it held
#: `gate_run "` or `python3 "$REPO/`, so a stage spelled any other way - `node tv/x.mjs`, `npx playwright test`,
#: `bash tools/x.sh`, `python3 -m unittest`, `$(python tv/y.py)` - could run before the scrub while the law stayed green.
#: A stage is any of these programs run as a command word, read the way _shell_code reads bash: comments out, quotes,
#: $(...) and heredoc bodies followed as bash nests them, and a word inside quotes is data. Its reach, stated: a program
#: named through a variable ("$PY" -c ...) is not seen, and a word in a heredoc body is read as code (as the re-export
#: reader reads it) - such a word before the scrub reads RED, never green.
STAGE_PROGRAMS = ("gate_run", "python3", "python", "node", "bash", "npx")
#: the frames whose words bash never runs: '...', "..." outside its $(...) and `...`, and $'...'
QUOTED = ("sq", "dq", "ansi")


def _stages(src, first_line=1):
    """REG-2454 - every place `src` (bash, whose first line is hook line `first_line`) runs a stage, in order.
    -> (hits, open); a hit is (hook line, program, that line's text), and open is _shell_code's (anything but [] means
    this reader lost bash's place, so its answer is UNKNOWN)"""
    rx = re.compile(r"(?:^|(?<=[\s;&|(`{]))(%s)(?=[\s;&|)`}]|$)" % "|".join(re.escape(x) for x in STAGE_PROGRAMS),
                    re.M)
    kinds = []
    code, pos, _heredocs, still_open = _shell_code(src, kinds)
    lines = src.split("\n")
    hits = []
    for m in rx.finditer(code):
        if kinds[m.start(1)] in QUOTED:
            continue                                     # a word inside quotes is data: bash runs nothing there
        at = src.count("\n", 0, pos[m.start(1)])
        hits.append((first_line + at, m.group(1), lines[at].strip()[:160]))
    return hits, still_open


def _pointer_names():
    """REG-2551 - every variable that points git at a repository: git's own list, REEXPORTED by name, less CARRIERS"""
    return (set(_git("rev-parse", "--local-env-vars").split()) | set(POINTERS) | set(REEXPORTED)) - set(CARRIERS)


def _reexports(src, first_line, names):
    """REG-2551 - every place `src` (bash, whose first line is hook line `first_line`) assigns or exports a pointer.
    -> (hits, code, heredocs, open); a hit is (hook line, form, name, that line's text)

    The forms bash itself assigns or exports with: NAME= / NAME+= (a plain assignment, a `NAME=... cmd` prefix, `env
    NAME=...`, `${NAME=...}` / `${NAME:=...}`); export / declare / typeset / local / readonly naming it; read /
    printf -v / mapfile naming it. Strings are read too - `env "GIT_DIR=$x" cmd` and `eval "export GIT_DIR=..."` are
    real re-exports. REG-2552 (GB-L, second eye on 8ddee4d1): a name SPLIT by quotes (`export GIT_D''IR=...`, bash
    joins the parts into GIT_DIR) is read on the code with its quote characters dropped, and a name held in a
    variable (`_n=GIT_DIR; export "$_n=..."`, `for _v in GIT_DIR; do export "${_v}=..."`) is followed: a variable
    whose value or loop list names a pointer, then exported, declared, read or printf -v'd through `$_n` / `${_n}`.
    Its reach, stated: a name assembled from parts at run time (`a=GIT_; export "${a}DIR=..."`) is not seen."""
    alt = "|".join(re.escape(x) for x in sorted(names, key=len, reverse=True))
    forms = (("assigns", re.compile(r"(?<![\w$])(%s)[+:]?=" % alt)),
             ("exports", re.compile(r"\b(?:export|declare|typeset|local|readonly)\b[^\n;&|]*?(?<![\w${])(%s)\b" % alt)),
             ("reads into", re.compile(r"\b(?:read|printf[ \t]+-v|mapfile|readarray)\b[^\n;&|]*?(?<![\w${])(%s)\b"
                                       % alt)))
    code, pos, heredocs, still_open = _shell_code(src)
    # REG-2552 - the code as bash sees a WORD after quote removal: every ' and " dropped, so GIT_D''IR reads GIT_DIR
    # REG-2556 (second eye on v3787) - and a $ that opens a quote ($'..' / $"..") goes with it: quote removal deletes
    # the marker too, so `export $'GIT_DIR=..'` and `GIT_D$''IR` are GIT_DIR to bash
    keep = [k for k, ch in enumerate(code)
            if ch not in "'\"" and not (ch == "$" and code[k + 1:k + 2] in ("'", '"'))]
    bare = "".join(code[k] for k in keep)
    bpos = [pos[k] for k in keep]
    lines = src.split("\n")
    hits = set()
    for form, rx in forms:
        for m in rx.finditer(bare):
            at = src.count("\n", 0, bpos[m.start(1)])
            hits.add((first_line + at, form, m.group(1), lines[at].strip()[:160]))
    # REG-2552 - a pointer named through a variable: bound by `v=NAME` or `for v in ... NAME ...`, then used as the
    # name of an export / declare / read / printf -v / assignment through $v or ${v}
    # REG-2557 (second eye on v3787) - a binding is POSITIONAL and only at a statement start: the latest `v=...` (or
    # `for v in ...`) before a use decides what $v names, so `_n=GIT_DIR; _n=PATH` holds PATH and `echo '_n=GIT_DIR'`
    # binds nothing. `env` / `eval` count only when the held name is ASSIGNED (`env "$_n=.."`), never on a mere value use.
    binds = []
    stmt = r"(?:^|(?<=[;&|(\n])|(?<=\bthen)|(?<=\bdo)|(?<=\belse))[ \t]*"
    for m in re.finditer(stmt + r"(?:(?:local|declare|typeset|readonly|export)(?:[ \t]+-\w+)*[ \t]+)?"
                         r"([A-Za-z_]\w*)=([^\s;&|)]*)", bare, re.M):
        binds.append((m.start(1), m.group(1), m.group(2) if m.group(2) in names else None))
    for m in re.finditer(stmt + r"for[ \t]+([A-Za-z_]\w*)[ \t]+in\b([^;\n]*)", bare, re.M):
        named = [w for w in m.group(2).split() if w in names]
        binds.append((m.start(1), m.group(1), named[0] if named else None))
    binds.sort()
    for var in sorted({v for _, v, n in binds if n}):
        ref = r"\$(?:\{%s\}|%s\b)" % (re.escape(var), re.escape(var))
        rx = re.compile(r"(?:\b(?:export|declare|typeset|local|readonly|read|printf[ \t]+-v|mapfile|readarray)\b"
                        r"[^\n;&|]*?%s|\benv\b[^\n;&|]*?%s[+]?=|%s[+]?=)" % (ref, ref, ref))
        for m in rx.finditer(bare):
            name = None
            for at_b, v, n in binds:
                if at_b >= m.start():
                    break
                if v == var:
                    name = n
            if name:
                at = src.count("\n", 0, bpos[m.start()])
                hits.add((first_line + at, "exports via $%s" % var, name, lines[at].strip()[:160]))
    return sorted(hits), code, heredocs, still_open


class _Case(unittest.TestCase):

    def setUp(self):
        # this law builds repos too: under a hook's leak its own fixture git calls must not reach the real one
        _gitenv = {_k: os.environ.pop(_k) for _k in list(os.environ) if _k.startswith("GIT_")}
        self.addCleanup(os.environ.update, _gitenv)
        self.root = tempfile.mkdtemp(prefix="leaked_gitdir_")
        self.addCleanup(shutil.rmtree, self.root, True)


class ATempRepoLawNeverWritesTheRealRepo(_Case):

    def test_every_temp_repo_law_passes_under_a_leaked_git_dir_and_leaves_the_repo_as_it_was(self):
        """★ each law, run WHOLE under GIT_DIR=<the fixture worktree's git dir>: green, and the fixture unchanged -
        no commit on the branch, no object, no index write, and core.bare still false"""
        for fname, selection in TEMP_REPO_LAWS:
            with self.subTest(law=fname):
                self.assertTrue(os.path.isfile(os.path.join(HERE, fname)), "PREMISE: %s is gone" % fname)
                fx = _Fixture(os.path.join(self.root, fname[:-3]))
                before = fx.state()
                self.assertEqual(before["bare"], "false", "PREMISE: the fixture repo starts bare")
                r = subprocess.run([sys.executable, "-B", "-m", "unittest", selection], cwd=HERE,
                                   capture_output=True, text=True, timeout=600, encoding="utf-8", errors="replace",
                                   env=_clean_env(GIT_DIR=fx.gitdir))
                after = fx.state()
                moved = sorted(k for k in before if before[k] != after[k])
                self.assertEqual(moved, [], "%s WROTE the repo its leaked GIT_DIR points at (%s moved; core.bare is "
                                            "now %r) - in a push that is his live checkout:\n%s"
                                 % (fname, ", ".join(moved), after["bare"], (r.stderr or "")[-1500:]))
                self.assertEqual(r.returncode, 0, "%s is RED under a leaked GIT_DIR (a git answer about its temp "
                                                  "dir came from the real repo):\n%s" % (fname, (r.stderr or "")[-2000:]))
                self.assertRegex(r.stderr or "", r"Ran [1-9]\d* tests?",
                                 "%s ran nothing - a selection that matches no test proves nothing" % fname)

    def test_each_scrub_is_scoped_to_a_test_never_the_module(self):
        """a module-wide strip of GIT_* made the commit-stamps law skip inside heart2's sandbox (push #12); each scrub
        sits in a function and is put back by addCleanup"""
        for fname, _sel in TEMP_REPO_LAWS:
            with io.open(os.path.join(HERE, fname), encoding="utf-8") as fh:
                src = fh.read()
            with warnings.catch_warnings():          # test_control's own escape sequences are not this law's finding
                warnings.simplefilter("ignore")
                tree = ast.parse(src)
            scoped, loose = 0, []
            for node in tree.body:
                funcs = [n for n in ast.walk(node) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                if not funcs:
                    if "startswith" in ast.dump(node) and "'GIT_'" in ast.dump(node):
                        loose.append(getattr(node, "lineno", 0))
                    continue
                for f in funcs:
                    body = ast.dump(f)
                    if "'GIT_'" in body and "attr='pop'" in body and "addCleanup" in body:
                        scoped += 1
            self.assertEqual(loose, [], "%s strips GIT_* at MODULE level (line %s)" % (fname, loose))
            self.assertGreaterEqual(scoped, 1, "%s builds a temp repo and scrubs GIT_* in no test's scope" % fname)


class TheHookUnsetsThePointerBeforeAnyStage(_Case):

    def test_the_scrub_block_unsets_every_pointer_and_names_the_git_dir(self):
        bash = _bash()
        if bash is None:
            self.skipTest("no real POSIX bash on this PC - the hook's scrub is UNMEASURED, not passing")
        fx = _Fixture(self.root)
        block, _line = _block("scrub-git-env")
        script = block + '\nenv | grep "^GIT_" || true\necho "TV_PUSHED_GIT_DIR=$TV_PUSHED_GIT_DIR"\n'
        r = subprocess.run([bash, "-c", "set -u\n" + script], cwd=fx.wt, capture_output=True, text=True, timeout=60,
                           env=_clean_env(GIT_DIR=fx.gitdir, GIT_WORK_TREE=fx.wt,
                                          GIT_INDEX_FILE=os.path.join(fx.gitdir, "index"),
                                          GIT_COMMON_DIR=os.path.join(fx.real, ".git")))
        self.assertEqual(r.returncode, 0, "the hook's scrub block did not run - UNKNOWN, not passing: %s" % r.stderr)
        left = sorted(set(re.findall(r"^(GIT_[A-Z_]+)=", r.stdout, re.M)))
        local = (set(_git("rev-parse", "--local-env-vars").split()) | set(POINTERS)) - set(CARRIERS)
        self.assertEqual(sorted(set(left) & local), [],
                         "the hook hands its stages a pointer at the real repo: %s" % sorted(set(left) & local))
        m = re.search(r"^TV_PUSHED_GIT_DIR=(.*)$", r.stdout, re.M)
        self.assertTrue(m and m.group(1), "the scrub block names no git dir for the commit-stamps law")
        self.assertEqual(os.path.realpath(m.group(1)), fx.gitdir,
                         "TV_PUSHED_GIT_DIR is not the git dir the push came from")

    def test_the_scrub_comes_before_the_first_stage(self):
        with io.open(HOOK, encoding="utf-8") as fh:
            src = fh.read()
        _b, at = _block("scrub-git-env")
        hits, still_open = _stages(src)
        self.assertEqual(still_open, [], "the stage reader lost bash's place in the hook (%s still open at the end) - "
                                         "its verdict is UNKNOWN, not passing" % still_open)
        self.assertTrue(hits, "the stage grammar finds no stage in the hook at all - it is blind, not passing")
        line, prog, text = hits[0]
        self.assertLess(at + 1, line, "a stage (hooks/pre-push:%d, %s: %r) runs before the hook unsets git's pointer "
                                      "(line %d)" % (line, prog, text, at + 1))

    def test_a_stage_spelled_any_way_before_the_scrub_is_found(self):
        """REG-2454 - a fixture hook whose first stage is spelled otherwise than `gate_run "` / `python3 "$REPO/` must
        read red, and a comment, a function's definition, a quoted word or a plain git line before the scrub must not"""
        scrub = "# >>> scrub-git-env\nunset GIT_DIR\n# <<< scrub-git-env\ngate_run \"late\" \"late\" 30 -- true\n"
        head = "#!/usr/bin/env bash\nset -u\n"
        for early in ('node "$REPO/tv/demo_console.mjs"', "npx playwright test tests/x.spec.ts", "bash tools/x.sh",
                      "python3 -m unittest test_x", '  _out="$(python tv/y.py 2>/dev/null)"', "cd tv && python3 x.py",
                      "_v=`node -e 1`", "{ npx tsc; }", "python3 - <<'PY'\nprint(1)\nPY",
                      'gate_run "early" "x" 30 -- true'):
            with self.subTest(early=early):
                hits, still_open = _stages(head + early + "\n" + scrub)
                self.assertEqual(still_open, [])
                self.assertTrue(hits and hits[0][0] == 3, "a stage spelled %r before the scrub was not found first: %s"
                                % (early, hits))
        quiet = (head + "# node, npx, bash and python3 named in a comment\n"
                 'REPO="$(git rev-parse --show-toplevel)" || exit 1  # not a stage either: bash, node\n'
                 "gate_run() { \"$@\"; }\n"
                 'echo "run node later"; _python3_ok=1; cd node_modules\n' + scrub)
        hits, still_open = _stages(quiet)
        self.assertEqual(still_open, [])
        self.assertEqual([h[2] for h in hits], ['gate_run "late" "late" 30 -- true'],
                         "a comment, a definition, a quoted word or a plain git line was read as a stage: %s" % hits)


class ThePushsOwnOptionsSurviveTheScrub(_Case):
    """REG-2394 - a `git -c` option reaches the hook in GIT_CONFIG_PARAMETERS (the env form in GIT_CONFIG_COUNT with
    GIT_CONFIG_KEY_i / GIT_CONFIG_VALUE_i). git's --local-env-vars names both carriers and the first cut unset them."""

    def test_the_scrub_block_keeps_the_options_and_still_unsets_every_pointer(self):
        bash = _bash()
        if bash is None:
            self.skipTest("no real POSIX bash on this PC - the hook's scrub is UNMEASURED, not passing")
        fx = _Fixture(self.root)
        block, _line = _block("scrub-git-env")
        script = (block + 'echo "PROBE=[$(git config --get tv.probe)]"\n'
                  'echo "COUNTED=[$(git config --get tv.counted)]"\nenv | grep "^GIT_" || true\n')
        r = subprocess.run([bash, "-c", "set -u\n" + script], cwd=fx.wt, capture_output=True, text=True, timeout=60,
                           env=_clean_env(GIT_DIR=fx.gitdir, GIT_INDEX_FILE=os.path.join(fx.gitdir, "index"),
                                          GIT_CONFIG_PARAMETERS="'tv.probe'='kept'", GIT_CONFIG_COUNT="1",
                                          GIT_CONFIG_KEY_0="tv.counted", GIT_CONFIG_VALUE_0="yes", **_HERMETIC))
        self.assertEqual(r.returncode, 0, "the hook's scrub block did not run - UNKNOWN, not passing: %s" % r.stderr)
        self.assertIn("PROBE=[kept]", r.stdout, "a `git -c` option is gone after the scrub - every later stage runs "
                                                "without the push's own options:\n%s" % r.stdout)
        self.assertIn("COUNTED=[yes]", r.stdout, "a GIT_CONFIG_COUNT option is gone after the scrub:\n%s" % r.stdout)
        left = set(re.findall(r"^(GIT_[A-Z0-9_]+)=", r.stdout, re.M))
        self.assertEqual(sorted(left & {"GIT_DIR", "GIT_INDEX_FILE"}), [],
                         "keeping the options let a pointer through: %s" % sorted(left))

    def test_a_real_git_c_push_keeps_its_options_past_the_scrub(self):
        """★ on a throwaway repo: a REAL `git -c push.default=upstream -c tv.probe=kept push origin HEAD:main` (plus
        the env form) from a linked worktree whose branch tracks origin/main, through a hook made of the real hook's
        push-range and scrub blocks - after the scrub git still answers both options, @{push} is origin/main, the push
        base is origin/main's commit, and no pointer is left. The fixture hook refuses, so nothing reaches the remote."""
        if _bash() is None:
            self.skipTest("no real POSIX bash on this PC - git cannot run the hook; UNMEASURED, not passing")
        fx = _PushFixture(self.root)
        fx.commit("tv/x.py")
        hooks = os.path.join(self.root, "hooks")
        os.makedirs(hooks)
        rng, _l1 = _block("push-range")
        scrub, _l2 = _block("scrub-git-env")
        hook = os.path.join(hooks, "pre-push")
        with io.open(hook, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(u"#!/usr/bin/env bash\nset -u\n" + rng + scrub
                     + u'echo "PROBE=[$(git config --get tv.probe)]"\n'
                       u'echo "COUNTED=[$(git config --get tv.counted)]"\n'
                       u"echo \"PUSH=[$(git rev-parse --abbrev-ref '@{push}' 2>&1)]\"\n"
                       u'echo "BASE=[$TV_PUSH_BASE]"\n'
                       u'env | grep "^GIT_" | sed "s/^/LEFT /"\n'
                       u"exit 1\n")
        os.chmod(hook, 0o755)
        _git("-C", fx.real, "config", "core.hooksPath", hooks)
        on_remote = _git("-C", fx.remote, "rev-parse", "main")
        r = subprocess.run(["git", "-c", "push.default=upstream", "-c", "tv.probe=kept", "push", "origin", "HEAD:main"],
                           cwd=fx.wt, capture_output=True, text=True, timeout=120, encoding="utf-8", errors="replace",
                           env=_clean_env(GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="tv.counted",
                                          GIT_CONFIG_VALUE_0="yes", **_HERMETIC))
        out = (r.stdout or "") + (r.stderr or "")
        self.assertIn("PROBE=[", out, "PREMISE: git never ran the fixture hook:\n%s" % out[-800:])
        self.assertNotEqual(r.returncode, 0, "PREMISE: the fixture hook refuses every push:\n%s" % out[-800:])
        self.assertIn("PROBE=[kept]", out, "the push's own `git -c` option is gone after the scrub - every stage after "
                                           "it runs without it:\n%s" % out[-1500:])
        self.assertIn("COUNTED=[yes]", out, "the push's GIT_CONFIG_COUNT option is gone after the scrub:\n%s"
                      % out[-1500:])
        self.assertIn("PUSH=[origin/main]", out, "after the scrub @{push} no longer resolves - push.default=upstream "
                                                 "was lost with GIT_CONFIG_PARAMETERS:\n%s" % out[-1500:])
        self.assertIn("BASE=[%s]" % _git("-C", fx.wt, "rev-parse", "origin/main"), out,
                      "the push base is not origin/main's commit:\n%s" % out[-1500:])
        left = set(re.findall(r"^LEFT (GIT_[A-Z0-9_]+)=", out, re.M))
        self.assertIn("GIT_CONFIG_PARAMETERS", left, "PREMISE: git handed this hook no `git -c` options at all")
        local = (set(_git("rev-parse", "--local-env-vars").split()) | set(POINTERS)) - set(CARRIERS)
        self.assertEqual(sorted(left & local), [], "a pointer at the real repo outlived the scrub: %s" % sorted(left))
        self.assertEqual(_git("-C", fx.remote, "rev-parse", "main"), on_remote, "the fixture push reached its remote")


#: REG-2551 - the reader's reach, DRIVEN: (a hook's text after the scrub, does it point git at a repository again?)
_REACH = (
    ("export GIT_DIR=/tmp/x\n", True),
    ("GIT_WORK_TREE=/tmp/x git status\n", True),
    ("x=1 GIT_INDEX_FILE=/tmp/i git add -A\n", True),
    ("env GIT_OBJECT_DIRECTORY=/tmp/o git fsck\n", True),
    ("declare -x GIT_COMMON_DIR=/tmp/c\n", True),
    ("export GIT_COMMON_DIR\n", True),
    ("typeset -x GIT_INDEX_FILE\n", True),
    ("readonly GIT_OBJECT_DIRECTORY\n", True),
    ("local GIT_DIR\n", True),
    ("GIT_INDEX_FILE+=.lock git add -A\n", True),
    ('read -r GIT_DIR < "$_f"\n', True),
    ("printf -v GIT_WORK_TREE '%s' /tmp/x\n", True),
    ("mapfile -t GIT_INDEX_FILE < /tmp/f\n", True),
    ('git log "${GIT_DIR:=/tmp/x}"\n', True),
    ("export \\\n  GIT_WORK_TREE\n", True),
    ("# don't\nexport GIT_DIR=/tmp/x\n", True),
    ("echo \"it's #1\"; export GIT_DIR=/tmp/x\n", True),
    ("echo 'a #b'; export GIT_DIR=/tmp/x\n", True),
    ("echo $'it\\'s'; export GIT_DIR=/tmp/x\n", True),                  # $'...' escapes its own quote
    ("echo `echo a #b`; export GIT_DIR=/tmp/x\n", True),                # a '#' inside `...` ends nothing past it
    ('_v="$(echo "# x"; GIT_DIR=/tmp/x git rev-parse HEAD)"\n', True),
    ('_v="$(printf \'%s\' "a #b"; GIT_DIR=/tmp/x git log)"\n', True),      # quotes nest inside $(...) inside "..."
    ("cat <<EOF\n$(GIT_DIR=/tmp/x git log)\nEOF\n", True),
    ("cat <<EOF\n# $(GIT_DIR=/tmp/x git log)\nEOF\n", True),          # no comment in a heredoc: bash runs that $(...)
    ("echo $# ${_f#stale|} a#b; export GIT_DIR=/tmp/x\n", True),       # a '#' inside a word opens no comment
    ("python3 - <<'PY' 2>/dev/null\nimport os\nPY\nexport GIT_INDEX_FILE=/tmp/i\n", True),
    # each delimiter spelling, over a body whose lone ' would hold a reader that missed the heredoc inside a quote
    ("cat <<'EOF'\nit's data\nEOF\nexport GIT_DIR=/tmp/x\n", True),
    ('cat <<"EOF"\nit\'s data\nEOF\nexport GIT_DIR=/tmp/x\n', True),
    ("cat <<\\EOF\nit's data\nEOF\nexport GIT_DIR=/tmp/x\n", True),
    ("cat <<-EOF\n\tit's data\n\tEOF\nexport GIT_DIR=/tmp/x\n", True),        # <<- : the delimiter line is tab-indented
    # REG-2552 - a name split by quotes, and a name held in a variable
    ("export GIT_D''IR=/tmp/x\n", True),
    ("export $'GIT_DIR=/tmp/x'\n", True),
    ('declare -x $"GIT_WORK_TREE=/tmp"\n', True),
    ("env $'GIT_INDEX_FILE=/tmp/i' git add\n", True),
    ("export GIT_D$''IR=/tmp/x\n", True),
    ("_n=$'GIT_DIR'; export \"$_n=/tmp/x\"\n", True),
    ('env "GIT_D"IR=/tmp/x git log\n', True),
    ("declare -x 'GIT_WORK'_TREE=/tmp/x\n", True),
    ('_n=GIT_DIR; export "$_n=/tmp/x"\n', True),
    ('_n="GIT_INDEX_FILE"\nprintf -v "$_n" %s /tmp/i\n', True),
    ('for _v in GIT_WORK_TREE GIT_DIR; do export "${_v}=/tmp/x"; done\n', True),
    ('_n=GIT_DIR; echo "$_n is what git hands a hook"\n', False),
    ('_n=GIT_DIR; _n=PATH; export "$_n=/usr/bin"\n', False),
    ("echo '_n=GIT_DIR'; export \"$_n=/tmp/x\"\n", False),
    ('_n=GIT_DIR; env echo "$_n"\n', False),
    ('_n=GIT_DIR; env "$_n=/tmp/x" git log\n', True),
    ('_n=PATH; _n=GIT_DIR; export "$_n=/tmp/x"\n', True),
    ('for _v in GIT_DIR GIT_WORK_TREE; do unset "$_v"; done\n', False),
    ("# export GIT_DIR=/tmp/x\n", False),
    ("echo ok  # GIT_DIR=/tmp/x is what git hands a hook\n", False),
    ('echo "TV_PUSHED_GIT_DIR=$TV_PUSHED_GIT_DIR"\nexport TV_PUSHED_GIT_DIR\n', False),
    ('git --git-dir="$TV_PUSHED_GIT_DIR" show HEAD:bible.html\n', False),
    ('[ -n "${GIT_DIR:-}" ] && echo "a pointer leaked"\n', False),
    ('echo "$#" "${#_a}" "${_f#stale|}"\n', False),
    ("unset GIT_DIR GIT_WORK_TREE\n", False),
)


class NoStageAfterTheScrubPointsGitBack(_Case):
    """REG-2551 (the Grok CLI review of Push A2, MEDIUM M2) - the scrub cases run only the marked block, so a re-export
    of a pointer anywhere AFTER it kept them green while every later stage got the pointer back."""

    def test_the_reader_finds_every_form_and_no_comment(self):
        """its reach first, on text whose answer is known: each re-export form is found, and a comment, a use of the
        value (`${GIT_DIR:-}`), an unset, TV_PUSHED_GIT_DIR and `git --git-dir=` are not - a reader that misses here
        would read the hook clean"""
        names = _pointer_names()
        for text, want in _REACH:
            with self.subTest(text=text):
                hits, _code, heredocs, still_open = _reexports(text, 1, names)
                self.assertEqual(still_open, [], "the reader lost bash's place in %r" % text)
                self.assertTrue(all(h[1] for h in heredocs), "the reader found no end to a heredoc in %r" % text)
                self.assertEqual(bool(hits), want, "%r - the reader says %s" % (text, hits or "nothing"))

    def test_no_line_after_the_scrub_points_git_at_a_repo_again(self):
        """★ the WHOLE hook after `# <<< scrub-git-env`, comments out and heredoc bodies in: no line assigns or exports
        GIT_DIR, GIT_WORK_TREE, GIT_INDEX_FILE, GIT_OBJECT_DIRECTORY, GIT_COMMON_DIR or any pointer on git's list"""
        with io.open(HOOK, encoding="utf-8") as fh:
            src = fh.read()
        for marker in ("# >>> scrub-git-env\n", "# <<< scrub-git-env\n"):
            self.assertEqual(src.count(marker), 1, "PREMISE: %r is not in the hook exactly once" % marker)
        end = src.index("# <<< scrub-git-env\n") + len("# <<< scrub-git-env\n")
        tail, first, names = src[end:], src[:end].count("\n") + 1, _pointer_names()
        hits, _code, heredocs, still_open = _reexports(tail, first, names)
        self.assertEqual(still_open, [], "this reader lost bash's place in the hook (%s still open at the end) - its "
                                         "verdict is UNKNOWN, not passing" % still_open)
        self.assertTrue(all(h[1] for h in heredocs), "the reader found no end to a heredoc in the hook (%s) - its "
                                                     "verdict is UNKNOWN, not passing" % [h[0] for h in heredocs])
        # the reader's place, checked on the REAL text: a canary planted where it could be lost must be found there
        for at in [0] + [h[2] for h in heredocs] + [len(tail)]:
            sep = "" if at == 0 or tail[at - 1] == "\n" else "\n"
            planted = tail[:at] + sep + CANARY + tail[at:]
            got = _reexports(planted, first, names)[0]
            self.assertIn((first + planted.count("\n", 0, at + len(sep)), "GIT_DIR"), set((h[0], h[2]) for h in got),
                          "PREMISE: a canary re-export planted at hook offset %d was not found - the reader has lost "
                          "bash's place there, so its verdict is UNKNOWN: %s" % (end + at, got))
        self.assertEqual(hits, [], "a line after the scrub points git at a repository AGAIN - every stage after it "
                                   "inherits the pointer the scrub removed (REG-2360):\n%s"
                         % "\n".join("  hooks/pre-push:%d  %s %s  | %s" % h for h in hits))


class TheTvLaneReadsAKnownRangeOrRuns(_Case):
    """REG-2395 - the tv-suites lane's trigger was `git diff --name-only @{push}..` alone: no fallback, no word. These
    drive the hook's push-range and tv-lane blocks in bash on fixture branches shaped like his."""

    def _lane(self, cwd):
        bash = _bash()
        if bash is None:
            self.skipTest("no real POSIX bash on this PC - the hook's tv lane is UNMEASURED, not passing")
        rng, _l1 = _block("push-range")
        lane, _l2 = _block("tv-lane")
        script = "set -u\n_pp_el() { printf '0m00s'; }\n" + rng + lane + 'echo "LANE=[$_tv_lane]"\n'
        r = subprocess.run([bash, "-c", script], cwd=cwd, capture_output=True, text=True, timeout=60,
                           encoding="utf-8", errors="replace", env=_clean_env(**_HERMETIC))
        self.assertEqual(r.returncode, 0, "the hook's tv-lane blocks did not run - UNKNOWN, not passing: %s" % r.stderr)
        m = re.search(r"^LANE=\[(.*)\]$", r.stdout, re.M)
        self.assertIsNotNone(m, "the lane decided nothing: %r" % r.stdout)
        return m.group(1), r.stdout

    def test_a_branch_whose_push_does_not_resolve_reads_origin_main(self):
        """★ his push branches' shape: @{push} fails, so the old trigger matched nothing and skipped all six suites"""
        fx = _PushFixture(self.root)
        fx.commit("tv/x.py")
        old = subprocess.run(["git", "-C", fx.wt, "diff", "--name-only", "@{push}.."], capture_output=True, text=True,
                             timeout=60, env=_clean_env(**_HERMETIC))
        self.assertNotEqual(old.returncode, 0, "PREMISE: @{push} resolves in this fixture, so it cannot show the old "
                                               "trigger's silent skip")
        lane, out = self._lane(fx.wt)
        self.assertEqual(lane, "touched", "a tv/*.py change on a branch whose @{push} does not resolve did not run the "
                                          "tv suites from origin/main:\n%s" % out)
        self.assertIn("tv/ python touched in origin/main..HEAD", out, "the lane does not name the range it read:\n%s"
                      % out)

    def test_an_unknown_range_runs_the_lane_and_says_so(self):
        """no @{push} and no origin/main: nobody can tell whether tv/ python changed, so the suites RUN"""
        fx = _PushFixture(self.root, remote=False)
        fx.commit("docs.txt")
        lane, out = self._lane(fx.wt)
        self.assertEqual(lane, "unknown", "an UNKNOWN push range skipped the tv suites:\n%s" % out)
        self.assertIn("UNKNOWN range is never a skip", out, "the lane ran on an unknown range without saying so:\n%s"
                      % out)

    def test_a_known_range_says_whether_the_lane_runs(self):
        """@{push} resolves (push.default=upstream): no tv/*.py in it is a skip SAID with its range; one is a run"""
        fx = _PushFixture(self.root)
        _git("-C", fx.real, "config", "push.default", "upstream")
        fx.commit("docs.txt")
        lane, out = self._lane(fx.wt)
        self.assertEqual(lane, "", "a push with no tv/*.py in a known range ran the tv suites:\n%s" % out)
        self.assertIn("no tv/*.py changed in @{push}..HEAD (@{push} = origin/main)", out,
                      "the lane skipped without a word:\n%s" % out)
        fx.commit("tv/y.py")
        lane, out = self._lane(fx.wt)
        self.assertEqual(lane, "touched", "a tv/*.py change in @{push}..HEAD did not run the tv suites:\n%s" % out)
        self.assertIn("tv/ python touched in @{push}..HEAD", out)


class ThePushedCommitIsHandedOverByName(_Case):

    def _pushed(self, refs, cwd, out=None):
        bash = _bash()
        if bash is None:
            self.skipTest("no real POSIX bash on this PC - the hook's pushed-commit block is UNMEASURED, not passing")
        block, _line = _block("pushed-commit")
        script = ("_pp_el() { printf '0m00s'; }\n_PUSH_REFS=%s\n%s\necho \"TV_PUSHED_COMMIT=$TV_PUSHED_COMMIT\"\n"
                  % (_sq(refs), block))
        r = subprocess.run([bash, "-c", "set -u\n" + script], cwd=cwd, capture_output=True, text=True, timeout=60,
                           encoding="utf-8", errors="replace", env=_clean_env())
        self.assertEqual(r.returncode, 0, "the hook's pushed-commit block did not run: %s" % r.stderr)
        m = re.search(r"^TV_PUSHED_COMMIT=(.*)$", r.stdout, re.M)
        self.assertIsNotNone(m, "the block exported nothing: %r" % r.stdout)
        if out is not None:
            out.append(r.stdout)
        return m.group(1)

    def test_every_ref_the_stamps_law_does_not_read_is_named(self):
        """REG-2456 (A2's Grok low 4) - the stamps law reads ONE commit; a push of several refs with no main ref handed it
        the first ref's sha and said nothing of the rest. The block now names, in the hook's own output, every ref that
        ships bytes and is not the commit the law reads - beside main too."""
        fx = _Fixture(self.root)
        z = "0" * 40
        a, b, c = "a" * 40, "b" * 40, "c" * 40
        said = []
        got = self._pushed("refs/heads/x %s refs/heads/x %s\nrefs/heads/y %s refs/heads/y %s\n"
                           "refs/heads/w %s refs/heads/w %s\n" % (a, z, b, z, c, z), fx.wt, said)
        self.assertEqual(got, a)
        self.assertIn("NOT read by it", said[-1], "two refs the stamps law never reads went unnamed:\n%s" % said[-1])
        for ref in ("refs/heads/y@bbbbbbbbb", "refs/heads/w@ccccccccc"):
            self.assertIn(ref, said[-1], "%s ships bytes the stamps law never reads, and the hook did not say so" % ref)
        self.assertNotIn("refs/heads/x@", said[-1], "the ref the law DOES read was named as unread")
        self._pushed("refs/heads/x %s refs/heads/x %s\nrefs/heads/v %s refs/heads/v %s\n" % (a, z, a, z), fx.wt, said)
        self.assertNotIn("NOT read by it", said[-1], "a ref pushing the very commit the law reads was named as unread")
        self._pushed("refs/heads/x %s refs/heads/x %s\n" % (a, z), fx.wt, said)
        self.assertNotIn("NOT read by it", said[-1], "a one-ref push was told a ref went unread")
        self._pushed("refs/heads/x %s refs/heads/x %s\nrefs/heads/y %s refs/heads/main %s\n" % (a, z, b, z), fx.wt, said)
        self.assertIn("refs/heads/x@aaaaaaaaa", said[-1], "beside main, a ref the stamps law does not read went unnamed")

    def test_main_wins_then_the_first_ref_that_ships_then_head(self):
        fx = _Fixture(self.root)
        head = _git("-C", fx.wt, "rev-parse", "HEAD")
        z = "0" * 40
        a, b = "a" * 40, "b" * 40
        self.assertEqual(self._pushed("refs/heads/x %s refs/heads/x %s\nrefs/heads/y %s refs/heads/main %s\n"
                                      % (a, z, b, z), fx.wt), b, "the ref pushed to main is not the pushed commit")
        self.assertEqual(self._pushed("refs/heads/x %s refs/heads/x %s\n" % (a, z), fx.wt), a,
                         "a push with no main ref names no commit")
        self.assertEqual(self._pushed("(delete) %s refs/heads/main %s\nrefs/heads/x %s refs/heads/x %s\n"
                                      % (z, a, a, z), fx.wt), a, "a deletion of main was read as the pushed commit")
        self.assertEqual(self._pushed("(delete) %s refs/heads/main %s\n" % (z, a), fx.wt), head,
                         "a push that ships no bytes does not fall back to HEAD")


def _sq(s):
    return "'" + s.replace("'", "'\"'\"'") + "'"


class TheCommitStampsLawReadsTheNamedCommit(_Case):

    def _commit(self, repo, stamps, msg):
        b, c, t, w = stamps
        os.makedirs(os.path.join(repo, "tv"), exist_ok=True)
        for rel, text in (("bible.html", u"window.D2R_BUILD = {id:'%s', name:'x'};\n" % b),
                          ("tv/control_app.py", u'X = {"ver": "%s"}\n' % c),
                          ("tv/tv_diablo.py", u'VERSION = "%s"\n' % t),
                          ("tv/WINDOWS_SHIP.json", u'{"ver": "%s"}\n' % w)):
            with io.open(os.path.join(repo, rel), "w", encoding="utf-8") as fh:
                fh.write(text)
        _git("-C", repo, "add", "-A")
        _git("-C", repo, "commit", "-q", "-m", msg)
        return _git("-C", repo, "rev-parse", "HEAD")

    def _run(self, gitdir, sha):
        return subprocess.run([sys.executable, "-B", os.path.join(HERE, "test_control.py"),
                               "TestTheStampsAgreeInTheCOMMITNotJustTheWorktree"], cwd=HERE, capture_output=True,
                              text=True, timeout=300, encoding="utf-8", errors="replace",
                              env=_clean_env(TV_PUSHED_GIT_DIR=gitdir, TV_PUSHED_COMMIT=sha))

    def test_a_named_coherent_commit_passes_and_a_named_half_bump_refuses(self):
        repo = os.path.join(self.root, "stamps")
        os.makedirs(repo)
        _git("init", "-q", repo)
        _git("-C", repo, "config", "core.autocrlf", "false")  # #107 REG-3626 - the fixture's bytes, not the PC's git default
        ok = self._commit(repo, ("v0042",) * 4, "coherent")
        half = self._commit(repo, ("v0042", "v0042", "v0042", "v0043"), "half-bumped")
        gd = os.path.join(repo, ".git")
        r = self._run(gd, ok)
        self.assertEqual(r.returncode, 0, "a coherent named commit was refused:\n%s" % r.stderr[-1500:])
        self.assertRegex(r.stderr, r"Ran 2 tests", "the commit-stamps law did not run both of its tests")
        self.assertNotIn("skipped", r.stderr, "the commit-stamps law SKIPPED on a commit it was handed by name")
        r = self._run(gd, half)
        self.assertNotEqual(r.returncode, 0, "a half-bumped commit, handed over by name, passed - the law read "
                                             "something other than the pushed commit")
        self.assertIn("HALF-BUMPED", r.stderr)
        r = self._run(gd, "f" * 40)
        self.assertNotEqual(r.returncode, 0, "a named commit git cannot read was let through")
        self.assertNotIn("skipped", r.stderr, "a named commit git cannot read was a SKIP - the push said which "
                                              "bytes ship, so not reading them is a failure")


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {
        "why": "REG-2360 - the hook no longer unsets git's pointer: every stage inherits GIT_DIR pointing at his repo",
        "file": "hooks/pre-push",
        "find": "  unset \"$_pp_v\"\n",
        "replace": "  : \"$_pp_v\"\n",
        "matches": 1,
        "needs": "bash",
    },
    {
        "why": "REG-2360 - the pushed commit is the first ref, not the one pushed to main",
        "file": "hooks/pre-push",
        "find": "  if [ \"$_pc_rr\" = \"refs/heads/main\" ]; then TV_PUSHED_COMMIT=\"$_pc_ls\"; break; fi\n",
        "replace": "",
        "matches": 1,
        "needs": "bash",
    },
    {
        "why": "REG-2360 - the commit-stamps law ignores the commit it was handed and reads HEAD of whatever tree it is in",
        "file": "test_control.py",
        "find": "        if gd and sha:\n",
        "replace": "        if False:\n",
        "matches": 1,
    },
    {
        "why": "REG-2360 - the author-stamp law builds its temp repo with the hook's GIT_DIR: commits land on the branch",
        "file": "test_the_author_is_read_from_the_stamp.py",
        "find": "        _gitenv = {_k: os.environ.pop(_k) for _k in list(os.environ) if _k.startswith(\"GIT_\")}\n",
        "replace": "        _gitenv = {}\n",
        "matches": 1,
    },
    {
        "why": "REG-2360 - the stale-lock law's `git init --bare` runs under the leak: core.bare=true on the real config",
        "file": "test_a_stale_git_lock_is_cleared_and_said.py",
        "find": "        _gitenv = {_k: os.environ.pop(_k) for _k in list(os.environ) if _k.startswith(\"GIT_\")}\n",
        "replace": "        _gitenv = {}\n",
        "matches": 1,
    },
    {
        "why": "REG-2360 - TheLauncherUsesTheSameRule builds its repos under the leak (and reads the real repo as its own)",
        "file": "test_a_landed_update_is_not_an_edit.py",
        "find": "        _gitenv = {_k: os.environ.pop(_k) for _k in list(os.environ) if _k.startswith(\"GIT_\")}\n",
        "replace": "        _gitenv = {}\n",
        "matches": 1,
    },
    {
        "why": "REG-2360 - TheTreeIsToldApart's `git init --bare` and commits run under the leak",
        "file": "test_every_pc_proves_itself.py",
        "find": "        _gitenv = {_k: os.environ.pop(_k) for _k in list(os.environ) if _k.startswith(\"GIT_\")}\n",
        "replace": "        _gitenv = {}\n",
        "matches": 1,
    },
    {
        "why": "REG-2360 - the P3 tracked-files case asks git about its throwaway repo under the leak",
        "file": "test_a_proven_verdict_is_reused_only_on_identical_bytes.py",
        "find": "        _gitenv = {_k: os.environ.pop(_k) for _k in list(os.environ) if _k.startswith(\"GIT_\")}\n",
        "replace": "        _gitenv = {}\n",
        "matches": 1,
    },
    {
        "why": "REG-2394 - the scrub unsets the push's own options again: a `git -c` push loses push.default, @{push} "
               "stops resolving, and every stage after the scrub runs without the caller's options",
        "file": "hooks/pre-push",
        "find": "  case \"$_pp_v\" in GIT_CONFIG_PARAMETERS|GIT_CONFIG_COUNT) continue ;; esac\n",
        "replace": "",
        "matches": 1,
        "needs": "bash",
    },
    {
        "why": "REG-2395 - an UNKNOWN push range skips the tv suites again, the way the bare @{push} trigger did",
        "file": "hooks/pre-push",
        "find": "if [ -z \"${TV_PUSH_BASE:-}\" ]; then\n  _tv_lane=\"unknown\"\n",
        "replace": "if [ -z \"${TV_PUSH_BASE:-}\" ]; then\n  _tv_lane=\"\"\n",
        "matches": 1,
        "needs": "bash",
    },
    {
        "why": "REG-2395 - the push range loses its origin/main fallback: a branch whose @{push} does not resolve (his "
               "push branches) reads UNKNOWN instead of the range it ships",
        "file": "hooks/pre-push",
        "find": "elif _pr_b=\"$(git rev-parse --verify --quiet 'origin/main' 2>/dev/null)\" && [ -n \"$_pr_b\" ]; then\n",
        "replace": "elif false; then\n",
        "matches": 1,
        "needs": "bash",
    },
    {
        "why": "REG-2395 - the lane skips in silence again: a push with no tv/*.py says nothing about the six suites",
        "file": "hooks/pre-push",
        "find": "  echo \"pre-push: [$(_pp_el)] \u23ed  no tv/*.py changed in ${TV_PUSH_RANGE:-?} - the tv suites do not run.\"\n",
        "replace": "  :\n",
        "matches": 1,
        "needs": "bash",
    },
    {
        "why": "REG-2551 - the line after the scrub exports GIT_DIR again: every stage inherits a pointer at a repository, "
               "and the cases that run only the scrub block stay green",
        "file": "hooks/pre-push",
        "find": "# <<< scrub-git-env\n",
        "replace": "# <<< scrub-git-env\nexport GIT_DIR=/tmp/x\n",
        "matches": 1,
    },
    {
        "why": "REG-2552 - the reader stops dropping quote characters: `export GIT_D''IR=...` (bash joins it into GIT_DIR) "
               "reads clean again",
        "file": "tv/test_a_leaked_git_dir_never_writes_the_real_repo.py",
        "find": "            if ch not in \"'\\\"\" and not (ch == \"$\" and code[k + 1:k + 2] in (\"'\", '\"'))]\n",
        "replace": "            if ch == ch]\n",
        "matches": 1,
    },
    {
        "why": "REG-2556 - the reader keeps the $ of a $'..' quote: `export $'GIT_DIR=...'` reads clean again",
        "file": "tv/test_a_leaked_git_dir_never_writes_the_real_repo.py",
        "find": "            if ch not in \"'\\\"\" and not (ch == \"$\" and code[k + 1:k + 2] in (\"'\", '\"'))]\n",
        "replace": "            if ch not in \"'\\\"\"]\n",
        "matches": 1,
    },
    {
        "why": "REG-2557 - the first binding wins again: `_n=GIT_DIR; _n=PATH; export \"$_n=...\"` reads as GIT_DIR",
        "file": "tv/test_a_leaked_git_dir_never_writes_the_real_repo.py",
        "find": "                if v == var:\n                    name = n\n",
        "replace": "                if v == var and name is None:\n                    name = n\n",
        "matches": 1,
    },
    {
        "why": "REG-2557 - a mention inside a string binds again: `echo '_n=GIT_DIR'; export \"$_n=...\"` reads as GIT_DIR",
        "file": "tv/test_a_leaked_git_dir_never_writes_the_real_repo.py",
        "find": "    stmt = r\"(?:^|(?<=[;&|(\\n])|(?<=\\bthen)|(?<=\\bdo)|(?<=\\belse))[ \\t]*\"\n",
        "replace": "    stmt = r\"(?<![\\w$])\"\n",
        "matches": 1,
    },
    {
        "why": "REG-2552 - the reader stops following a pointer held in a variable: `_n=GIT_DIR; export \"$_n=...\"` reads "
               "clean again",
        "file": "tv/test_a_leaked_git_dir_never_writes_the_real_repo.py",
        "find": "        binds.append((m.start(1), m.group(1), m.group(2) if m.group(2) in names else None))\n",
        "replace": "        pass\n",
        "matches": 1,
    },
    {
        "why": "REG-2551 - a stage far past the scrub (after the hook's heredoc, inside $(...) in a string) hands its git "
               "the pushed git dir as a `GIT_DIR=... cmd` prefix",
        "file": "hooks/pre-push",
        "find": "    changed=\"$(git diff --name-only \"$remote_sha\"..\"$local_sha\" 2>/dev/null)\"\n",
        "replace": "    changed=\"$(GIT_DIR=\"$TV_PUSHED_GIT_DIR\" git diff --name-only \"$remote_sha\"..\"$local_sha\" "
                   "2>/dev/null)\"\n",
        "matches": 1,
    },
    {
        "why": "REG-2454 - the stage grammar narrows back to one spelling: a stage spelled `node ...` / `npx ...` / "
               "`bash ...` / `python3 -m ...` before the scrub passes again",
        "file": "test_a_leaked_git_dir_never_writes_the_real_repo.py",
        "find": "STAGE_PROGRAMS = (\"gate_run\", \"python3\", \"python\", \"node\", \"bash\", \"npx\")\n",
        "replace": "STAGE_PROGRAMS = (\"gate_run\",)\n",
        "matches": 1,
    },
    {
        "why": "REG-2454 - a word inside quotes is read as a stage: an `echo \"... node ...\"` before the scrub "
               "reads red with no stage there, and a spurious red costs a whole push",
        "file": "test_a_leaked_git_dir_never_writes_the_real_repo.py",
        "find": "        if kinds[m.start(1)] in QUOTED:\n",
        "replace": "        if False:\n",
        "matches": 1,
    },
    {
        "why": "REG-2456 - a multi-ref push says nothing of the refs the commit-stamps law never reads",
        "file": "hooks/pre-push",
        "find": "  echo \"          only ${TV_PUSHED_COMMIT:-?}; NOT read by it:$_pc_unseen\"\n",
        "replace": "  true\n",
        "matches": 1,
    },
]
