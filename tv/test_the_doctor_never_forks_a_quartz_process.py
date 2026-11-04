# -*- coding: utf-8 -*-
"""v3429 (#150) — THE DOCTOR MUST NOT fork() A PROCESS THAT HAS LOADED THE OBJECTIVE-C RUNTIME.

`test_control HUNG — killed after 1500s on an IDLE machine` has refused FOUR pushes since
2026-09-20, and the standing diagnosis ("the cheap subset is over budget") was wrong. MEASURED
2026-09-23, back to back, same idle machine:

    run 1 — cd.run(include_slow=False) hung 28 MINUTES at 0.0% CPU and had to be killed
    run 2 — the SAME call FINISHED IN 15.4 SECONDS, 107 rows

⚠ SO IT IS A DEADLOCK, NOT A COST, and RESUME_HERE's ">8 min alone" measured the HUNG case. Its
own puzzle — "the whole is minutes; every part is seconds" — dissolves: the parts ARE seconds. A
hang must never be averaged with a cost.

WHAT IT IS, from the stuck process: the hung parent had exactly ONE child, at 0.0% CPU, with no
grandchildren, **wearing the PARENT'S OWN ARGV** — the signature of a `subprocess.Popen` caught
BETWEEN fork and exec — and holding Quartz / CoreGraphics / QuickLookUI / PyObjC. control_app and
health_engine import those, so by the time any check shells out the Obj-C runtime is initialised,
and forking such a process without immediately exec'ing is the macOS fork-safety deadlock. 0% CPU
for 28 minutes is a lock wait; a busy loop cannot produce it.

THE ESCAPE, PROVEN BY RECORDING WHICH SYSCALL CPYTHON ACTUALLY TAKES rather than reading its
conditions:

    close_fds default (True)          -> fork_exec x1, posix_spawn x0      <- the hang
    absolute exe + close_fds=False    -> posix_spawn x1, fork_exec x0
    bare name "ps" + close_fds=False  -> fork_exec x1                      <- dirname condition

⚠ BOTH HALVES ARE LOAD-BEARING and `close_fds` DEFAULTS TO TRUE, which is why every ordinary call
forks. ⚠ AND close_fds=False IS SCOPED TO SHORT-LIVED READS: the child inherits open descriptors,
which for a long-lived worker would mean holding this console's listening socket past a restart.

==========================================================================================
v3435 (#150, reopened) — **THE CLASS LAW RECORDED TWO OF THE CONDITIONS CPYTHON CHECKS, AND
CPYTHON CHECKS FOURTEEN.**

The v3429 class law asked one question — "is the keyword `close_fds` present?" — and it asked it
only of receivers spelled `subprocess` / `_sp` / `sp`. Both halves of that were too narrow, and
each hid live forking sites:

  · **PRESENCE IS NOT VALUE.** `if "close_fds" not in kws` accepts `close_fds=True`, which is the
    fork. It also never looked at the dirname half at all, though this file's OWN sibling case
    (`test_a_BARE_executable_name_still_forks`) proves dirname is fatal on its own.
  · **THE RECEIVER SET WAS A SPELLING LIST.** `console_doctor` reaches subprocess through
    `git_quiet.run` (imported as `_gq`), a one-door wrapper that forwards `**kw` straight into
    `subprocess.run`. `_gq` is not `subprocess`, so SIX git spawns were skipped outright — and
    every one of them passes `cwd=ROOT`, which is condition six.

⚠ THE FIX IS NOT "ADD `run` TO AN ALLOWLIST". `subprocess.run` and `_gq.run` are both spelled
`run`; a guard widened on the bare attribute admits whatever else is spelled that way. Receivers
are resolved to **DOTTED module names** through the file's own import aliases, and the wrapper is
**DISCOVERED** — any module imported from `tv/` whose function forwards its `**kwargs` into a
subprocess spawner is a door, so the next `git_quiet` is seen without anyone remembering to list
it. [[a-widened-guard-admits-what-it-bans]]

⚠ AND THE NINE ARE NOT A NUMBER I TYPED. `_cpython_guard_vars()` parses
`subprocess.Popen._execute_child` **on the running interpreter** and returns the actual identifiers
its posix_spawn gate reads (14 clauses on CPython 3.9.6). A condition this file does not classify
is a RED, so a future CPython that adds one cannot silently widen the blind spot.
[[feedback-comments-vs-code]]

⚠ THE PREMISE CASES NOW CLASSIFY THE HOST, AND THEY SAY WHICH WORD THEY MEAN. The fork/spawn
premise is macOS-shaped; the gate set runs on `ubuntu-latest`. A premise case that simply passed
there would be a green that measured nothing, and one that simply skipped would be a silence.
`_host_probe()` MEASURES both control shapes at import and each host-dependent case records exactly
one of **MEASURED / NOT-APPLICABLE / UNKNOWN** with its reason, printed, and a completeness law
fails if any case recorded nothing. `0` measured is not `None` unmeasured.
[[unknown-stays-unknown]]

==========================================================================================
v3443 (#150, still open) — **THE NINE-CONDITION CLASSIFIER SHIPPED WITH SIX FALSE ALL-CLEARS IN
IT, AND THE CROSS-FAMILY EYE FOUND THEM IN TWENTY MINUTES.**

v3441 shipped the classifier; v3442 fixed one hole (identity vs truthiness — `user=0` read SPAWNS
while CPython tests `uid is None`). Five remained, and **every one graded a FORKING shape as
spawn-eligible** — the dangerous direction for a gate whose only job is catching forking sites:

  · **F3 — THE FIRST ARGV0, NOT THE LIVE ONE.** `_argv0` kept the first assignment that yielded an
    element and dropped the rest, and `_assigned_values` walked STRAIGHT THROUGH nested `def`s. So
    `args = ["/usr/bin/git", ...]` then `args = ["git", ...]` was graded on the dead spelling, and
    an inner function's argv answered for the outer one's. A one-to-many fact in a one-to-one
    store. [[one-to-one-store-for-a-one-to-many-fact]]
  · **F4 — A BARE BRANCH EXCUSED BY A STATE THAT WAS ONLY A NOTE.** `["/usr/bin/git" if ok else
    "git"]` collapsed to ABSOLUTE_IF_INSTALLED, which adds a note and no violation, so the verdict
    stayed SPAWNS while the else-branch forks. It was not even self-consistent: {BARE,
    ABSOLUTE_IF_INSTALLED} fell through to UNKNOWN and {BARE, ABSOLUTE} did not. Only a ternary
    whose CONDITION asks whether the tool is installed — console_doctor's own `_PS` line — keeps
    that state now.
  · **F5 — A JOIN IS NOT A DIRNAME.** Every `os.path.join` mapped to ABSOLUTE. `os.path.join("git")`
    returns `"git"`.
  · **F6 — THE DOOR ITSELF WAS MIS-READ.** Any `**kw`-forwarding wrapper was treated as
    transparent and only the CALL SITE was graded. A wrapper doing `kw.setdefault("cwd", REPO)`
    injects condition six into every call through it and the call site cannot show it. That is
    git_quiet's exact mechanism — it writes `kw["creationflags"]`, `kw["env"]`, `kw["startupinfo"]`
    — and it is transparent only because none of those three moves CPython off posix_spawn.
  · **F7 — A WHOLE IMPORT SPELLING COULD NOT FAIL THIS GATE.** `from git_quiet import run` binds
    its alias to the dotted name `git_quiet.run`; the module scan did `if "." in mod: continue`, so
    the module was never opened and the call matched no door. `async def` wrappers were skipped
    too. Door DISCOVERY missing a door is not a green — it is the same defect class as the
    receiver allowlist that hid six forking sites. [[presence-law-vs-reachability-law]]

⚠ **F6 AND F7 ARE THE STRUCTURAL PAIR.** F3/F4/F5 mis-grade a door that was found; F6 and F7 mean
the door is never found, or is found and then graded on half of itself.

⚠ **EVERY FIX CARRIES ITS BASELINE, because the cure here kills the patient very easily.** The ten
live console_doctor sites go through `_spawnable()` and `git_quiet.run`; a classifier tightened
without care reddens or blanks all of them and the gate becomes an alarm nobody can act on. Each
new case therefore asserts the CORRECT shape still reads SPAWNS: one absolute assignment, a
closure reading its enclosing scope, the `_PS = "/bin/ps" if os.path.exists(...) else "ps"`
ternary, a real absolute join, a site that passes `cwd` itself past a `setdefault` wrapper, and
git_quiet's own write-only-Windows-keys shape. [[the-cure-that-kills-the-patient]]
"""
import ast
import collections
import inspect
import io
import ntpath
import os
import posixpath
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

DOCTOR = os.path.join(HERE, "console_doctor.py")
with io.open(DOCTOR, encoding="utf-8", errors="replace") as _fh:
    SRC = _fh.read()


# =========================================================================================
# 1. THE SPAWN-ELIGIBILITY CLASSIFIER — one function, every condition CPython actually checks
# =========================================================================================

# Every keyword of `Popen.__init__` that can, on its own, push CPython off posix_spawn and onto
# fork_exec. The names on the LEFT are the local variables read by the guard in
# `Popen._execute_child`; `_cpython_guard_vars()` proves this map is complete on the running
# interpreter, so it cannot silently fall behind the language.
#
#   guard variable      what a CALL SITE writes it with          how it is violated
GUARD_VAR_TO_CONDITION = {
    "executable":        "executable-has-a-dirname",   # argv[0] or executable=
    "preexec_fn":        "preexec_fn-is-None",
    "close_fds":         "close_fds-is-False",         # ⚠ DEFAULTS TO TRUE -> absent == violated
    "pass_fds":          "no-pass_fds",
    "cwd":               "cwd-is-None",                # ⚠ the six git spawns
    "p2cread":           "stdin-is-not-fd-0-1-2",
    "c2pwrite":          "stdout-is-not-fd-0-1-2",
    "errwrite":          "stderr-is-not-fd-0-1-2",
    "start_new_session": "start_new_session-is-falsy",
    "uid":               "user-is-None",
    "gid":               "group-is-None",
    "gids":              "extra_groups-is-None",
    "umask":             "umask-is-negative",
    "process_group":     "process_group-is-default",   # CPython 3.11+
    # CPython 3.13+: `(not close_fds or _HAVE_POSIX_SPAWN_CLOSEFROM)` - a module flag that only
    # WIDENS the close_fds condition (posix_spawn can close fds itself where libc has closefrom,
    # e.g. glibc 2.34+; never macOS). It is part of the close_fds condition, not a new one.
    "_HAVE_POSIX_SPAWN_CLOSEFROM": "close_fds-is-False",
}

# The NINE that a call site in this repo can realistically trip, in the order CPython tests them.
# (uid/gid/gids/umask/process_group are the identity tail — classified, never yet used here.)
NINE_CONDITIONS = (
    "executable-has-a-dirname",
    "preexec_fn-is-None",
    "close_fds-is-False",
    "no-pass_fds",
    "cwd-is-None",
    "stdin-is-not-fd-0-1-2",
    "stdout-is-not-fd-0-1-2",
    "stderr-is-not-fd-0-1-2",
    "start_new_session-is-falsy",
)

# Keyword -> the condition it can violate. `executable` and the three streams are handled by hand.
KW_TO_CONDITION = {
    "preexec_fn": "preexec_fn-is-None",
    "close_fds": "close_fds-is-False",
    "pass_fds": "no-pass_fds",
    "cwd": "cwd-is-None",
    "stdin": "stdin-is-not-fd-0-1-2",
    "stdout": "stdout-is-not-fd-0-1-2",
    "stderr": "stderr-is-not-fd-0-1-2",
    "start_new_session": "start_new_session-is-falsy",
    "user": "user-is-None",
    "group": "group-is-None",
    "extra_groups": "extra_groups-is-None",
    "umask": "umask-is-negative",
    "process_group": "process_group-is-default",
}

SPAWNERS = ("run", "Popen", "call", "check_call", "check_output",
            "getoutput", "getstatusoutput")

# Helpers that turn a bare command into a path WITH a dirname when the tool is installed, and fall
# back to the bare name when it is not. `_spawnable()` in console_doctor is exactly this shape, as
# is `_PS = "/bin/ps" if os.path.exists("/bin/ps") else "ps"`.
PATH_RESOLVERS = ("_spawnable", "shutil.which", "which", "distutils.spawn.find_executable")

# executable-resolution states
ABSOLUTE = "ABSOLUTE"                            # always has a dirname
ABSOLUTE_IF_INSTALLED = "ABSOLUTE_IF_INSTALLED"  # which()-style: dirname whenever the tool exists
BARE = "BARE"                                    # never has a dirname -> ALWAYS forks
EXE_UNKNOWN = "UNKNOWN"                          # nobody can tell from here

FORKS = "FORKS"
SPAWNS = "SPAWNS"
UNKNOWN = "UNKNOWN"


def _cpython_guard_vars():
    """The identifiers the RUNNING interpreter's posix_spawn gate actually reads. -> set or None

    ⚠ READ FROM THE COMPILER, NOT FROM A COMMENT. This file used to record two conditions because
    two is what somebody remembered. `Popen._execute_child` is the only authority on how many
    there are, and it moves between versions (3.11 added `process_group`). None means the source
    was not available — UNKNOWN, never "there are none". [[unknown-stays-unknown]]
    """
    try:
        src = inspect.getsource(subprocess.Popen._execute_child)
    except (OSError, TypeError):
        return None
    try:
        tree = ast.parse("if 1:\n" + "\n".join("    " + l for l in src.splitlines()))
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if not isinstance(node, ast.If) or not isinstance(node.test, ast.BoolOp):
            continue
        if not isinstance(node.test.op, ast.And):
            continue
        ids = {n.id for n in ast.walk(node.test) if isinstance(n, ast.Name)}
        if "_USE_POSIX_SPAWN" in ids:
            # `os` is the module in `os.path.dirname(executable)`; the condition it belongs to is
            # already carried by `executable`.
            return ids - {"_USE_POSIX_SPAWN", "os"}
    return None


def _import_aliases(tree):
    """Every name this module binds to a module, mapped to the DOTTED module it names. -> dict

    ⚠ THE WHOLE POINT OF THE DOTTED FORM. `subprocess.run` and `_gq.run` are both spelled `run`,
    and a guard widened on the bare attribute admits whatever else is spelled that way. Resolving
    `_gq` -> `git_quiet` and `_sp` -> `subprocess` through the file's own imports keeps them two
    different names. Function-local imports count: console_doctor does `import git_quiet as _gq`
    inside five separate check bodies. [[a-widened-guard-admits-what-it-bans]]
    """
    aliases = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.asname:
                    aliases[a.asname] = a.name
                else:
                    aliases[a.name.split(".")[0]] = a.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            for a in node.names:
                aliases[a.asname or a.name] = node.module + "." + a.name
    return aliases


def _dotted(node, aliases):
    """The dotted name a Name/Attribute expression denotes, with aliases resolved. -> str or None"""
    parts = []
    cur = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if not isinstance(cur, ast.Name):
        return None
    parts.append(aliases.get(cur.id, cur.id))
    return ".".join(reversed(parts))


# Every keyword a wrapper can write into the forwarded kwargs that CHANGES WHICH SYSCALL RUNS.
# `env`, `creationflags`, `startupinfo`, `timeout`, `capture_output` and friends are deliberately
# NOT here — git_quiet writes three of those on Windows and is still transparent for this purpose.
FORK_RELEVANT_KWS = tuple(sorted(set(KW_TO_CONDITION) | {"executable", "shell"}))

# How sure we are that the wrapper's write reaches a given call:
INJECT_ALWAYS = "always"          # unconditional -> the condition holds at EVERY call site
INJECT_SETDEFAULT = "setdefault"  # only when the call site did not pass it itself
INJECT_MAYBE = "maybe"            # written under a branch -> the site cannot be graded


def _condition_of_kw(kw):
    """The CPython condition a wrapper-injected keyword violates. -> str"""
    if kw in ("executable", "shell"):
        return "executable-has-a-dirname"
    return KW_TO_CONDITION[kw]


def _subscript_key(node):
    """The literal string key of `d["k"]`, through 3.8's ast.Index as well. -> str or None"""
    sl = node.slice
    sl = sl.value if sl.__class__.__name__ == "Index" else sl
    known, val = _literal(sl)
    return val if known and isinstance(val, str) else None


def _wrapper_injections(fn, spawn_call, kwarg):
    """Every fork-relevant keyword this wrapper writes into its own **kwargs. -> {kw: (mode, how)}

    ⚠⚠ v3443 (F6) — THE STRUCTURAL ONE. Discovery called a `**kw`-forwarding wrapper TRANSPARENT
    and then graded only the CALL SITE. A wrapper that does

        kw.setdefault("cwd", REPO)            or      subprocess.run(argv, cwd=REPO, **kw)

    injects condition six into every call through it, and NOTHING at the call site can show it —
    the site reads `run([abs, ...], close_fds=False)` and grades SPAWNS while every call forks.
    That is the same defect class as the receiver allowlist that hid six forking sites: the door
    itself was mis-read, so no amount of care at the call site could help.

    ⚠ IT IS NOT A HYPOTHETICAL SHAPE. git_quiet.run writes `kw["creationflags"]`, `kw["env"]` and
    `kw["startupinfo"]` — the exact mechanism — and stays transparent only because none of those
    three can move CPython off posix_spawn. One `kw["cwd"] = ROOT` and it would.
    """
    parents = {}
    for node in ast.walk(fn):
        for child in ast.iter_child_nodes(node):
            parents[child] = node

    def conditional(node):
        cur = parents.get(node)
        while cur is not None and cur is not fn:
            if isinstance(cur, (ast.If, ast.For, ast.While, ast.Try, ast.IfExp,
                                ast.ExceptHandler, ast.With)):
                return True
            cur = parents.get(cur)
        return False

    found = {}

    def note(kw, mode, how):
        if kw not in FORK_RELEVANT_KWS:
            return
        prev = found.get(kw)
        order = {INJECT_MAYBE: 0, INJECT_SETDEFAULT: 1, INJECT_ALWAYS: 2}
        if prev is None or order[mode] > order[prev[0]]:
            found[kw] = (mode, how)

    for node in ast.walk(fn):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if (isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name)
                        and t.value.id == kwarg):
                    key = _subscript_key(t)
                    if key:
                        known, val = _literal(node.value)
                        if known and val is None:
                            continue        # writing None is writing the compliant value
                        note(key, INJECT_MAYBE if conditional(node) else INJECT_ALWAYS,
                             'sets %s["%s"]' % (kwarg, key))
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and isinstance(node.func.value, ast.Name) and node.func.value.id == kwarg:
            attr = node.func.attr
            if attr in ("setdefault", "pop") and node.args:
                known, val = _literal(node.args[0])
                if known and isinstance(val, str):
                    mode = INJECT_MAYBE if conditional(node) else (
                        INJECT_SETDEFAULT if attr == "setdefault" else INJECT_ALWAYS)
                    note(val, mode, "%s.%s(%r)" % (kwarg, attr, val))
            elif attr == "update":
                for k in node.keywords:
                    if k.arg:
                        note(k.arg, INJECT_MAYBE if conditional(node) else INJECT_ALWAYS,
                             "%s.update(%s=...)" % (kwarg, k.arg))
                for a in node.args:
                    if isinstance(a, ast.Dict):
                        for key_node in a.keys:
                            known, val = _literal(key_node)
                            if known and isinstance(val, str):
                                note(val, INJECT_MAYBE if conditional(node) else INJECT_ALWAYS,
                                     "%s.update({%r: ...})" % (kwarg, val))
    # The forwarding call itself: `subprocess.run(argv, cwd=REPO, **kw)` is an injection too, and
    # it is the shape that reads most innocent.
    for k in spawn_call.keywords:
        if k.arg:
            known, val = _literal(k.value)
            if known and val is None:
                continue
            note(k.arg, INJECT_MAYBE if conditional(spawn_call) else INJECT_ALWAYS,
                 "passes %s= at the forwarding call" % k.arg)
    return found


def discover_spawn_doors(tree, where=HERE):
    """Every dotted callable in this tree that ends up in `subprocess`. -> dict name -> record

    A record is `{"why": str, "injects": {kw: (mode, how)}}`.

    Two kinds:
      · DIRECT   — `subprocess.run`, `subprocess.Popen`, ... under whatever alias.
      · WRAPPER  — a module imported from `tv/` with a function that forwards its own `**kwargs`
                   into a subprocess spawner. `git_quiet.run` is one. DISCOVERED, not listed, so
                   the next one-door wrapper is seen without anybody remembering to add it.

    ⚠ A WRAPPER THAT FORWARDS `**kw` FORWARDS THE HAZARD, AND MAY ALSO ADD ONE. git_quiet.run
    does `return subprocess.run(argv, **kw)` and writes only Windows-shaped keys, so on this
    condition set it is transparent and the CALL SITE decides the syscall. `injects` records what
    a wrapper writes that the call site cannot show — see `_wrapper_injections`.

    ⚠⚠ v3443 (F7) — A WHOLE IMPORT SPELLING COULD NOT BECOME A DOOR. The module scan did
    `if "." in mod: continue`, and `from git_quiet import run` binds the alias `run` to the DOTTED
    name `git_quiet.run` — so the module was never opened, `run(...)` matched no door, and a
    forking site written that way could not fail this gate at all. Discovery is only as good as
    the spellings it can see. `async def` wrappers were skipped for the same kind of reason.
    """
    aliases = _import_aliases(tree)
    doors = {}
    for alias, mod in aliases.items():
        if mod == "subprocess":
            for fn in SPAWNERS:
                doors["subprocess." + fn] = {"why": "direct", "injects": {}}
        elif mod.startswith("subprocess."):
            doors[mod] = {"why": "direct", "injects": {}}
    candidates = set()
    for mod in aliases.values():
        if mod == "subprocess" or mod.startswith("subprocess."):
            continue
        # `from git_quiet import run` -> "git_quiet.run"; the MODULE is everything before the last
        # dot. `import os.path` -> "os" (no dot) and simply finds no tv/os.py.
        candidates.add(mod.rsplit(".", 1)[0] if "." in mod else mod)
    for mod in sorted(candidates):
        path = os.path.join(where, mod + ".py")
        if not os.path.isfile(path):
            continue
        try:
            with io.open(path, encoding="utf-8", errors="replace") as fh:
                wtree = ast.parse(fh.read())
        except SyntaxError:
            continue
        waliases = _import_aliases(wtree)
        for fn in ast.walk(wtree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            kwarg = fn.args.kwarg.arg if fn.args.kwarg else None
            if not kwarg:
                continue
            for call in ast.walk(fn):
                if not isinstance(call, ast.Call):
                    continue
                d = _dotted(call.func, waliases) or ""
                if not d.startswith("subprocess.") or d.split(".")[-1] not in SPAWNERS:
                    continue
                forwards = any(k.arg is None and isinstance(k.value, ast.Name)
                               and k.value.id == kwarg for k in call.keywords)
                if forwards:
                    injects = _wrapper_injections(fn, call, kwarg)
                    why = "wrapper -> %s (forwards **%s)" % (d, kwarg)
                    if injects:
                        why += " AND INJECTS " + ", ".join(
                            "%s [%s]" % (k, v[0]) for k, v in sorted(injects.items()))
                    doors["%s.%s" % (mod, fn.name)] = {"why": why, "injects": injects}
    return doors


# A nested `def`, `lambda` or `class` is a DIFFERENT scope. Walking through one is how a name
# that never reaches the call site gets read as if it did.
_NESTED_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)


def _walk_scope(scope):
    """ast.walk, but it STOPS at a nested def / lambda / class. -> iterator of ast nodes

    ⚠ v3443 (F3) — `ast.walk` DESCENDS INTO NESTED FUNCTIONS, and `_assigned_values` used it. A
    helper spelled

        def outer():
            def inner():
                args = ["/usr/bin/git", "status"]     # never runs at the call site below
            args = ["git", "status"]
            subprocess.run(args, close_fds=False)     # argv0 is bare "git" -> FORKS

    handed the classifier `inner`'s absolute spelling, which has no bearing on the call, and the
    site read SPAWNS. A scope-blind reader answers a question nobody asked.
    [[a-law-about-a-row-must-drive-the-row]]
    """
    todo = collections.deque(ast.iter_child_nodes(scope))
    while todo:
        node = todo.popleft()
        if isinstance(node, _NESTED_SCOPES):
            continue
        todo.extend(ast.iter_child_nodes(node))
        yield node


def _scope_chain(func, tree):
    """The scopes a name lookup may legally read, innermost first. -> list of ast nodes

    `func` may be a single scope node or the whole enclosing chain (innermost first). Anything
    that is not an AST node — some cases pass a label — is dropped rather than walked.
    """
    given = list(func) if isinstance(func, (list, tuple)) else [func]
    chain = [s for s in given if isinstance(s, ast.AST)]
    if isinstance(tree, ast.AST) and tree not in chain:
        chain.append(tree)
    return chain


def _assigned_values(name, func, tree):
    """Every value `name` is assigned in the innermost scope that binds it. -> list of ast nodes

    ⚠ ALL OF THEM, NOT THE FIRST. A name rebound twice is a one-to-many fact; keeping one value
    and dropping the rest is how `args = [ABS]` hid `args = ["git"]`.
    [[one-to-one-store-for-a-one-to-many-fact]]
    """
    for scope in _scope_chain(func, tree):
        out = []
        for node in _walk_scope(scope):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name) and t.id == name:
                        out.append(node.value)
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                if isinstance(node.target, ast.Name) and node.target.id == name:
                    out.append(node.value)
        if out:
            return out
    return []


# `os.path.join` is NOT a synonym for "absolute". Evaluated with the right module, because
# `ntpath.join` and `posixpath.join` do not agree about what a dirname is.
JOIN_MODULES = {"os.path.join": os.path, "posixpath.join": posixpath, "ntpath.join": ntpath,
                "os.sep.join": os.path}

# Calls that ask "is this tool actually on this machine?". A `X if <one of these> else <bare X>`
# ternary is the AUDITED resolver shape — `_spawnable()` and console_doctor's
# `_PS = "/bin/ps" if os.path.exists("/bin/ps") else "ps"` are both exactly it.
INSTALL_TESTS = ("exists", "isfile", "isdir", "islink", "access", "which", "find_executable",
                 "_spawnable")


def _combine_exe_states(seen, label):
    """Fold several possible spellings of ONE argv0 into one state. -> (state, how)

    ⚠ FAILS TO UNKNOWN, NEVER TO THE BEST BRANCH. {ABSOLUTE, BARE} is not "absolute when
    installed"; it is a site where one spelling provably forks and nobody here can say which one
    runs. UNKNOWN is not green in this file, so it blocks instead of reassuring.
    [[unknown-stays-unknown]]
    """
    if not seen:
        return EXE_UNKNOWN, "unresolvable"
    states = {s for s, _ in seen}
    if len(states) == 1:
        if len(seen) == 1:
            return seen[0][0], seen[0][1]
        return seen[0][0], "%s (all %d spellings agree)" % (label, len(seen))
    if states <= {ABSOLUTE, ABSOLUTE_IF_INSTALLED}:
        return ABSOLUTE_IF_INSTALLED, label
    return EXE_UNKNOWN, label


def _tests_whether_the_tool_is_installed(test, aliases):
    """Does this ternary's condition ASK whether the absolute spelling exists? -> bool"""
    for n in ast.walk(test):
        if isinstance(n, ast.Call):
            d = _dotted(n.func, aliases) or ""
            if d and d.split(".")[-1] in INSTALL_TESTS:
                return True
    return False


def _join_state(d, node):
    """`os.path.join(...)` -> (state, how). ⚠ A JOIN IS NOT A DIRNAME.

    v3443 (F5): every join mapped to ABSOLUTE. `os.path.join("git")` returns `"git"` and
    `os.path.join("", "git")` returns `"git"` — no dirname, so CPython forks — and both read as
    spawn-eligible. The join is EVALUATED where it can be, and is UNKNOWN where it cannot.
    """
    mod = JOIN_MODULES[d]
    parts, all_literal = [], True
    for a in node.args:
        known, val = _literal(a)
        if known and isinstance(val, str):
            parts.append(val)
        else:
            all_literal = False
            break
    if all_literal and parts and not node.keywords:
        joined = mod.join(*parts)
        return (ABSOLUTE if mod.dirname(joined) else BARE), "%s -> %r" % (d, joined)
    if node.args:
        # A LAST component that already carries a dirname survives any prefix; an absolute FIRST
        # component can only be appended to or replaced by another absolute path. Either way the
        # result has a dirname whatever the unknown parts hold.
        known, val = _literal(node.args[-1])
        if known and isinstance(val, str) and mod.dirname(val):
            return ABSOLUTE, "%s(..., %r)" % (d, val)
        known, val = _literal(node.args[0])
        if known and isinstance(val, str) and mod.isabs(val):
            return ABSOLUTE, "%s(%r, ...)" % (d, val)
    return EXE_UNKNOWN, d + "(...)"


def _exe_state(node, func, tree, aliases, depth=0):
    """Does this expression name an executable WITH a dirname? -> (state, how)"""
    if node is None or depth > 4:
        return EXE_UNKNOWN, "unresolvable"
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return (ABSOLUTE if os.path.dirname(node.value) else BARE), repr(node.value)
    if isinstance(node, ast.Call):
        d = _dotted(node.func, aliases) or ""
        if d in PATH_RESOLVERS or d.split(".")[-1] in ("which", "_spawnable"):
            return ABSOLUTE_IF_INSTALLED, d + "(...)"
        if d in JOIN_MODULES:
            return _join_state(d, node)
        return EXE_UNKNOWN, (d or type(node).__name__) + "(...)"
    if isinstance(node, ast.Attribute):
        d = _dotted(node, aliases) or ""
        if d in ("sys.executable",):
            return ABSOLUTE, d
        return EXE_UNKNOWN, d or "attribute"
    if isinstance(node, ast.IfExp):
        a, ha = _exe_state(node.body, func, tree, aliases, depth + 1)
        b, hb = _exe_state(node.orelse, func, tree, aliases, depth + 1)
        how = "%s / %s" % (ha, hb)
        # ⚠ v3443 (F4) — A BARE BRANCH IS A FORK, AND "ABSOLUTE_IF_INSTALLED" WAS ONLY A NOTE.
        # `subprocess.run(["/usr/bin/git" if ok else "git"], close_fds=False)` read
        # ABSOLUTE_IF_INSTALLED and therefore SPAWNS, while it forks every time the else-branch
        # runs. It was also inconsistent with its own sibling: {BARE, ABSOLUTE_IF_INSTALLED} fell
        # through to UNKNOWN, {BARE, ABSOLUTE} did not.
        # The ONE ternary that really is "absolute whenever installed" asks whether the tool is
        # there — console_doctor's `_PS = "/bin/ps" if os.path.exists("/bin/ps") else "ps"` and
        # `_spawnable()`. That shape keeps its old state; an arbitrary condition does not, because
        # nobody has shown the bare branch is unreachable. [[unknown-stays-unknown]]
        if BARE in (a, b) and (ABSOLUTE in (a, b) or ABSOLUTE_IF_INSTALLED in (a, b)) \
                and _tests_whether_the_tool_is_installed(node.test, aliases):
            return ABSOLUTE_IF_INSTALLED, how + " [guarded by an is-it-installed test]"
        return _combine_exe_states([(a, ha), (b, hb)], how)
    if isinstance(node, ast.Name):
        vals = _assigned_values(node.id, func, tree)
        if not vals:
            return EXE_UNKNOWN, node.id + " (never assigned in reach)"
        seen = [_exe_state(v, func, tree, aliases, depth + 1) for v in vals]
        state, how = _combine_exe_states(seen, node.id)
        return state, ("%s = %s" % (node.id, how) if len(seen) == 1 else how)
    return EXE_UNKNOWN, type(node).__name__


def _argv0_nodes(node, func, tree, aliases, depth=0):
    """EVERY expression that could be argv[0] here. -> list of ast nodes

    ⚠⚠ v3443 (F3) — IT USED TO RETURN THE FIRST ONE IT FOUND AND DROP THE REST, and the first one
    is not the one that runs:

        args = ["/usr/bin/git", "status"]
        args = ["git", "status"]                     <- the live argv0
        subprocess.run(args, close_fds=False)        <- classified SPAWNS, forks every time

    A name rebound twice is a ONE-TO-MANY fact and `-> ast node or None` was a one-to-one store,
    so the classifier answered about a spelling that never reaches the syscall. Every candidate is
    returned and `_combine_exe_states` folds them; disagreement is UNKNOWN, which blocks.
    [[one-to-one-store-for-a-one-to-many-fact]]
    """
    if node is None or depth > 4:
        return []
    if isinstance(node, (ast.List, ast.Tuple)):
        return [node.elts[0]] if node.elts else []
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _argv0_nodes(node.left, func, tree, aliases, depth + 1) or \
            _argv0_nodes(node.right, func, tree, aliases, depth + 1)
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node]                   # a plain string command
    if isinstance(node, ast.IfExp):
        return (_argv0_nodes(node.body, func, tree, aliases, depth + 1) +
                _argv0_nodes(node.orelse, func, tree, aliases, depth + 1))
    if isinstance(node, ast.Name):
        out = []
        for v in _assigned_values(node.id, func, tree):
            out.extend(_argv0_nodes(v, func, tree, aliases, depth + 1))
        return out
    return []


def _literal(node):
    """-> (known, value). A non-literal expression is UNKNOWN, never assumed."""
    try:
        return True, ast.literal_eval(node)
    except Exception:
        return False, None


def _stream_verdict(node, aliases):
    """Does this stdin/stdout/stderr argument land the child's fd on 0, 1 or 2? -> 'ok'/'bad'/'?'"""
    known, val = _literal(node)
    if known:
        if val is None:
            return "ok"                                   # inherited -> the guard sees -1
        if isinstance(val, int):
            # PIPE(-1) / STDOUT(-2) / DEVNULL(-3) all produce a fresh fd or -1.
            return "bad" if 0 <= val <= 2 else "ok"
        return "?"
    d = _dotted(node, aliases) or ""
    if d.startswith("subprocess.") and d.split(".")[-1] in ("PIPE", "STDOUT", "DEVNULL"):
        return "ok"
    return "?"


def classify_spawn_call(call, func, tree, aliases, door=None):
    """THE ONE CLASSIFIER. Will CPython posix_spawn this call, or fork it? -> dict

    Returns {"verdict": FORKS|SPAWNS|UNKNOWN, "violations": [...], "unknowns": [...], "exe": ...}

    ⚠ ABSENCE IS A VALUE. `close_fds` defaults to **True**, so a call that never mentions it is
    violating the condition just as loudly as one that writes `close_fds=True`. That is the whole
    reason the v3429 presence-check passed six forking sites: it asked whether the word was there.
    [[a-law-about-a-row-must-drive-the-row]]
    """
    violations, unknowns, notes = [], [], []

    kws = {}
    star = False
    for k in call.keywords:
        if k.arg is None:
            star = True
        else:
            kws[k.arg] = k.value

    # ---- condition 1: the executable must have a dirname --------------------------------
    exe_node = kws.get("executable")
    how = ""
    if exe_node is None:
        shell_known, shell_val = _literal(kws["shell"]) if "shell" in kws else (True, False)
        if shell_known and shell_val:
            state, how = ABSOLUTE, "shell=True -> /bin/sh"
        else:
            pos = call.args[0] if call.args else None
            cands = _argv0_nodes(pos, func, tree, aliases)
            seen = [_exe_state(c, func, tree, aliases) for c in cands]
            state, how = _combine_exe_states(
                seen, "argv[0] has %d possible spelling(s): %s"
                      % (len(seen), " / ".join(h for _, h in seen) or "none resolvable"))
    else:
        state, how = _exe_state(exe_node, func, tree, aliases)
    if state == BARE:
        violations.append("executable-has-a-dirname")
    elif state == EXE_UNKNOWN:
        unknowns.append("executable-has-a-dirname")
    elif state == ABSOLUTE_IF_INSTALLED:
        notes.append("dirname holds whenever the tool is installed (%s)" % how)

    # ---- condition 3: close_fds must be present AND False -------------------------------
    if "close_fds" not in kws:
        violations.append("close_fds-is-False")
        notes.append("close_fds is ABSENT and defaults to True")
    else:
        known, val = _literal(kws["close_fds"])
        if not known:
            unknowns.append("close_fds-is-False")
        elif val:
            violations.append("close_fds-is-False")

    # ---- conditions 2, 4, 5, 9 and the identity tail ------------------------------------
    # ⚠⚠ v3442 — IDENTITY AND TRUTHINESS ARE NOT THE SAME CONDITION, AND CONFLATING THEM WAS A
    # FALSE ALL-CLEAR. Found by the cross-family eye on the SHIPPED v3441 bytes. CPython 3.9.6's
    # guard, read verbatim from inspect.getsource(subprocess.Popen._execute_child), is:
    #     preexec_fn is None · cwd is None · gid is None · gids is None · uid is None   <- IDENTITY
    #     not close_fds · not pass_fds · not start_new_session                          <- falsy
    # The first cut ran all seven through one `elif val:` — a TRUTHINESS test — and the loop
    # variable `must_be_falsy` was declared and NEVER READ, so the distinction its own name
    # promises was not encoded anywhere.
    # THE COST, and it is the dangerous direction: user=0 (run as root — the realistic case),
    # group=0, cwd="" and extra_groups=() are all FALSY, so they passed and the site was reported
    # SPAWNS. CPython tests `uid is None`, and 0 is not None, so every one of them FORKS.
    # A gate written to catch forking sites was blind to a whole family of them.
    IDENTITY_KWS = ("preexec_fn", "cwd", "user", "group", "extra_groups")
    FALSY_KWS = ("pass_fds", "start_new_session")
    for kw in IDENTITY_KWS + FALSY_KWS:
        if kw not in kws:
            continue
        must_be_none = kw in IDENTITY_KWS
        known, val = _literal(kws[kw])
        if not known:
            # ⚠ DELIBERATELY FAILS CLOSED, and this is NOT the same defect as the one above.
            # A non-literal `cwd=ROOT` or `preexec_fn=_nice` is overwhelmingly a real value, and
            # calling it UNKNOWN would have let the six console_doctor sites v3441 just repaired
            # sail through — the gate would have been honest and useless in the same breath.
            # The residual false positive is `x = None` then `cwd=x`, which is rare and SAFE:
            # it over-reports a fork that is not there, never under-reports one that is.
            # [[the-cure-that-kills-the-patient]] [[unknown-stays-unknown]]
            violations.append(KW_TO_CONDITION[kw])
            notes.append("%s=<expression> cannot be proven %s"
                         % (kw, "None" if must_be_none else "falsy"))
        elif (val is not None) if must_be_none else bool(val):
            violations.append(KW_TO_CONDITION[kw])
            if must_be_none and not val:
                # the exact case the truthiness test missed — say so, because `user=0` reads
                # harmless and is not
                notes.append("%s=%r is FALSY BUT NOT None, and CPython tests `is None`"
                             % (kw, val))
    if "umask" in kws:
        known, val = _literal(kws["umask"])
        if not known:
            unknowns.append("umask-is-negative")
        elif not (isinstance(val, int) and val < 0):
            violations.append("umask-is-negative")
    if "process_group" in kws:
        known, val = _literal(kws["process_group"])
        if not known:
            unknowns.append("process_group-is-default")
        elif val != -1:
            violations.append("process_group-is-default")

    # ---- conditions 6, 7, 8: no standard stream may land on fd 0/1/2 --------------------
    for kw in ("stdin", "stdout", "stderr"):
        if kw not in kws:
            continue
        v = _stream_verdict(kws[kw], aliases)
        if v == "bad":
            violations.append(KW_TO_CONDITION[kw])
        elif v == "?":
            unknowns.append(KW_TO_CONDITION[kw])

    if star:
        unknowns.append("**kwargs could carry any of them")

    # ---- what the DOOR adds that this call site cannot show -----------------------------
    # ⚠ v3443 (F6) — GRADING ONLY THE CALL SITE IS GRADING HALF THE CALL. A wrapper that writes
    # a fork-relevant keyword into the forwarded kwargs decides the syscall from a file the
    # reader of this line never opens. `always` is a violation (it holds on every call through
    # that door), `setdefault` only when the site did not pass the keyword itself, and a write
    # under a branch is UNKNOWN — which is not green here either. [[the-unjoined-end]]
    for kw, (mode, how) in sorted((door or {}).get("injects", {}).items()):
        if mode == INJECT_SETDEFAULT and kw in kws:
            continue                      # the call site's own value wins; nothing is injected
        cond = _condition_of_kw(kw)
        if mode == INJECT_MAYBE:
            if cond not in unknowns:
                unknowns.append(cond)
        elif cond not in violations:
            violations.append(cond)
        notes.append("the door itself %s — invisible from this call site (%s)"
                     % (how, (door or {}).get("why", "?")))

    verdict = FORKS if violations else (UNKNOWN if unknowns else SPAWNS)
    return {"verdict": verdict, "violations": violations, "unknowns": unknowns,
            "exe": state, "how": how, "notes": notes}


def _import_aliases_here(scope):
    """Imports bound in this scope alone, not in a nested function. -> dict

    console_doctor binds `_sp` to subprocess inside several checks, then later to self_prove.
    A file-wide map keeps the last binding, so every earlier `_sp.run` resolved as
    self_prove.run and was not a spawn door. The close_fds=True tamper on the gh call then
    stayed green (doctor law [3])."""
    aliases = {}
    for node in _walk_scope(scope):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.asname:
                    aliases[a.asname] = a.name
                else:
                    aliases[a.name.split(".")[0]] = a.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            for a in node.names:
                aliases[a.asname or a.name] = node.module + "." + a.name
    return aliases


def spawn_sites(src, where=HERE):
    """Every spawn door in `src`, classified. -> list of dicts (sorted by line)"""
    tree = ast.parse(src)
    module_aliases = _import_aliases_here(tree)
    doors = discover_spawn_doors(tree, where)
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node

    def enclosing_scopes(node):
        """The whole chain, INNERMOST FIRST — a closure may read its enclosing function's names,
        but a SIBLING nested def's names are not in reach. Returning only the innermost scope
        would lose the closure; returning the module would keep the sibling. Both are wrong."""
        chain, cur = [], parents.get(node)
        while cur is not None:
            if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                chain.append(cur)
            cur = parents.get(cur)
        return chain

    scope_aliases = {}

    def aliases_at(scopes):
        merged = dict(module_aliases)
        for scope in reversed(scopes):
            got = scope_aliases.get(id(scope))
            if got is None:
                got = _import_aliases_here(scope)
                scope_aliases[id(scope)] = got
            merged.update(got)
        return merged

    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        scopes = enclosing_scopes(node)
        aliases = aliases_at(scopes)
        d = _dotted(node.func, aliases)
        if d not in doors:
            continue
        got = classify_spawn_call(node, scopes, tree, aliases, doors[d])
        got["line"] = node.lineno
        got["door"] = d
        got["why_door"] = doors[d]["why"]
        out.append(got)
    return sorted(out, key=lambda r: r["line"])


# =========================================================================================
# 2. THE HOST PROBE — what this machine can and cannot be asked
# =========================================================================================

def _fork_exec_binding():
    """-> (owner, attribute, spelling) — the fork_exec NAME Popen._execute_child actually calls —
    or None when neither known spelling is in its source.

    ⚠⚠ #150 — THE SPY WATCHED A DOOR NOBODY WALKS THROUGH ON CI. It patched
    `_posixsubprocess.fork_exec`, which is how CPython 3.9 (his Mac) calls it. ubuntu-latest's system
    python3 is 3.12, whose subprocess does `from _posixsubprocess import fork_exec as _fork_exec` and
    calls `_fork_exec(...)` — so the patch landed on a name nothing reads, every fork count was 0,
    and CI run 35943284218 went red with "neither syscall was observed" on BOTH premise cases. The
    premise case below predicted exactly this in its own docstring and fired honestly. Read the
    binding from the running interpreter's source instead of from memory. [[a-probe-licenses-only-what-it-tested]]
    """
    import _posixsubprocess
    try:
        src = inspect.getsource(subprocess.Popen._execute_child)
    except (OSError, TypeError):
        return None
    if "_posixsubprocess.fork_exec(" in src:
        return (_posixsubprocess, "fork_exec", "_posixsubprocess.fork_exec")
    if "_fork_exec(" in src and hasattr(subprocess, "_fork_exec"):
        return (subprocess, "_fork_exec", "subprocess._fork_exec")
    return None


class _SyscallSpy(object):
    """Record which of fork_exec / posix_spawn CPython actually reaches for.

    ⚠ It patches the binding _fork_exec_binding() found. When none was found it patches NOTHING for
    fork and says so in `self.fork_binding` (None), so a zero count can never be read as a
    measurement — the premise case refuses that state by name."""

    def __enter__(self):
        self.counts = {"spawn": 0, "fork": 0}
        self.fork_binding = _fork_exec_binding()
        self._rs = os.posix_spawn
        self._rf = None

        def spawn(*a, **k):
            self.counts["spawn"] += 1
            return self._rs(*a, **k)

        os.posix_spawn = spawn
        if self.fork_binding is not None:
            owner, attr, _spelling = self.fork_binding
            self._rf = getattr(owner, attr)

            def fork(*a, **k):
                self.counts["fork"] += 1
                return self._rf(*a, **k)

            setattr(owner, attr, fork)
        return self

    def __exit__(self, *e):
        os.posix_spawn = self._rs
        if self.fork_binding is not None:
            setattr(self.fork_binding[0], self.fork_binding[1], self._rf)
        return False


def _probe_command():
    """An absolute, silent, instant command plus a bare spelling of it. -> (abs, args, bare)"""
    for cand, args in (("true", []), ("ps", ["-o", "pid="])):
        found = shutil.which(cand)
        if found:
            return found, args, cand
    return sys.executable, ["-c", ""], None


PROBE_ABS, PROBE_ARGS, PROBE_BARE = _probe_command()

MEASURED = "MEASURED"
NOT_APPLICABLE = "NOT-APPLICABLE"

# case name -> (state, reason). Written by `_record`; a completeness law reads it back.
LEDGER = {}
# v3860 - WINDOWS HAS NO fork(). CreateProcess is the only path there, so the Quartz fork deadlock this file guards cannot
# happen, and `_posixsubprocess` does not exist to be spied on. MEASURED on the new Konyo · ALT, 2026-11-04: the
# host-dependent cases died of ModuleNotFoundError before they could record a word. They now record NOT-APPLICABLE.
NO_FORK = not hasattr(os, "fork")
NO_FORK_WHY = "this OS has no fork() - CreateProcess is the only path, so there is no fork to take and no deadlock"
HOST_DEPENDENT = (
    "test_the_baseline_shape_REALLY_DOES_fork",
    "test_a_BARE_executable_name_still_forks",
    "test_the_corpse_row_takes_posix_spawn_and_never_forks",
)


def _record(case, state, reason):
    """Say, out loud, which word this case means. Never a silent skip, never a bare pass."""
    LEDGER[case] = (state, reason)
    sys.stderr.write("  [%s] %s :: %s\n" % (state, case, reason))
    sys.stderr.flush()
    return state


def _fork_count(argv, **kw):
    """Drive a real spawn and report (fork, spawn) or None if it could not run at all."""
    kw.setdefault("stdout", subprocess.DEVNULL)
    kw.setdefault("stderr", subprocess.DEVNULL)
    kw.setdefault("timeout", 20)
    try:
        with _SyscallSpy() as spy:
            try:
                subprocess.run(argv, **kw)
            except (OSError, subprocess.SubprocessError):
                pass                      # the SYSCALL choice is the measurement, not the exit code
            return spy.counts["fork"], spy.counts["spawn"]
    except Exception:
        return None


def _host_probe():
    """MEASURE this host's two control shapes instead of assuming them from sys.platform. -> dict

    ⚠ THE PREMISE CASES ARE macOS-SHAPED AND THE GATE SET RUNS ON ubuntu-latest. Rather than
    branch on the platform string and hope, both control shapes are driven here: the default
    (close_fds=True) which must fork, and the escape (absolute exe + close_fds=False) which must
    spawn. If this interpreter does not discriminate them, the premise cannot be pinned here and
    the honest word is UNKNOWN, not a pass. If it does discriminate but there is no Objective-C
    runtime on this platform, the hazard itself does not exist and the word is NOT-APPLICABLE.
    """
    default = _fork_count([PROBE_ABS] + PROBE_ARGS)
    escape = _fork_count([PROBE_ABS] + PROBE_ARGS, close_fds=False)
    objc = sys.platform == "darwin"
    info = {"platform": sys.platform, "objc_runtime": objc,
            "use_posix_spawn": bool(getattr(subprocess, "_USE_POSIX_SPAWN", False)),
            "default_shape": default, "escape_shape": escape, "probe": PROBE_ABS}
    if default is None or escape is None:
        info["verdict"] = UNKNOWN
        info["reason"] = ("neither control shape could be driven on this host (%r), so nothing "
                          "about fork vs posix_spawn was measured here" % (PROBE_ABS,))
    elif not (default[0] >= 1 and escape[1] >= 1 and escape[0] == 0):
        info["verdict"] = UNKNOWN
        info["reason"] = ("this interpreter does not separate the two shapes: default -> "
                          "fork=%d spawn=%d, escape -> fork=%d spawn=%d. The premise cannot be "
                          "pinned here." % (default + escape))
    elif not objc:
        info["verdict"] = NOT_APPLICABLE
        info["reason"] = ("%s has no Objective-C / Quartz runtime, so the fork-safety deadlock "
                          "this file exists to prevent cannot happen here. The syscall split WAS "
                          "measured (default fork=%d, escape spawn=%d); it is the HAZARD that is "
                          "absent, not the measurement." % (sys.platform, default[0], escape[1]))
    else:
        info["verdict"] = MEASURED
        info["reason"] = ("darwin, and both control shapes discriminate: default fork=%d, escape "
                          "spawn=%d" % (default[0], escape[1]))
    return info


HOST = _host_probe()


# =========================================================================================
# 3. THE LAWS
# =========================================================================================

class TestTheDoctorNeverForksAQuartzProcess(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        sys.stderr.write("\nHOST: %s | verdict=%s | %s\n"
                         % (HOST["platform"], HOST["verdict"], HOST["reason"]))

    # ---- driven on the real syscall ------------------------------------------------------

    def test_the_corpse_row_takes_posix_spawn_and_never_forks(self):
        """THE ONE THAT MATTERS. Not "does it pass the conditions" — does CPython take the
        non-forking path when this row actually runs."""
        case = "test_the_corpse_row_takes_posix_spawn_and_never_forks"
        if NO_FORK:
            _record(case, NOT_APPLICABLE, NO_FORK_WHY)
            return
        import console_doctor as cd
        fn = dict(cd.CHECKS)["nothing we started is a corpse"]
        with _SyscallSpy() as spy:
            st, say = fn()
        if HOST["verdict"] == UNKNOWN:
            _record(case, UNKNOWN, "%s — the row was driven and took fork=%d spawn=%d, but this "
                                   "host cannot tell the two paths apart, so that pair grades "
                                   "nothing" % (HOST["reason"], spy.counts["fork"],
                                                spy.counts["spawn"]))
            self.assertGreaterEqual(spy.counts["fork"] + spy.counts["spawn"], 1,
                                    "the row spawned nothing at all, so this case measured "
                                    "nothing — 0 with no denominator")
            return
        _record(case, MEASURED, "fork=%d spawn=%d (%s)"
                % (spy.counts["fork"], spy.counts["spawn"],
                   "the hazard is real here" if HOST["objc_runtime"] else
                   "the syscall law still holds off darwin; only the DEADLOCK is macOS-only"))
        self.assertEqual(spy.counts["fork"], 0,
                         "the doctor still fork()s a Quartz-loaded process — that is the 28-minute "
                         "deadlock path, and it refused four pushes (%s)" % say)
        self.assertGreaterEqual(spy.counts["spawn"], 1,
                                "nothing was spawned at all, so this case measured nothing")

    def test_the_baseline_shape_REALLY_DOES_fork(self):
        """⚠ THE PREMISE, PINNED. If a future CPython made close_fds=True spawn anyway, the case
        above would pass for a reason that has nothing to do with this fix, and the comments here
        would be describing a hazard that no longer exists.

        ⚠ v3435 — AND IT SAYS WHICH WORD IT MEANS OFF darwin. The gate set runs on ubuntu-latest,
        where there is no Quartz to deadlock. The measurement is still taken and still printed;
        what changes is that it is recorded as NOT-APPLICABLE instead of graded as if the hazard
        were present. NOT a skip, NOT a bare pass."""
        case = "test_the_baseline_shape_REALLY_DOES_fork"
        if NO_FORK:
            _record(case, NOT_APPLICABLE, NO_FORK_WHY)
            return
        got = _fork_count([PROBE_ABS] + PROBE_ARGS, stdout=subprocess.PIPE)
        self.assertIsNotNone(got, "the baseline shape could not be driven at all, so the premise "
                                  "is UNMEASURED rather than confirmed")
        if HOST["verdict"] == MEASURED:
            _record(case, MEASURED, "default shape -> fork=%d spawn=%d" % got)
            self.assertEqual(got[0], 1,
                             "the default shape no longer forks on this interpreter — re-measure "
                             "before trusting anything else in this file")
        else:
            _record(case, HOST["verdict"],
                    "default shape -> fork=%d spawn=%d, but %s" % (got[0], got[1], HOST["reason"]))
            self.assertGreaterEqual(sum(got), 1,
                                    "neither syscall was observed, so nothing was measured here "
                                    "— that is not the same as NOT-APPLICABLE")

    def test_a_BARE_executable_name_still_forks(self):
        """The dirname condition is half the fix and it is invisible: `close_fds=False` alone reads
        like a complete change and still forks."""
        case = "test_a_BARE_executable_name_still_forks"
        if NO_FORK:
            _record(case, NOT_APPLICABLE, NO_FORK_WHY)
            return
        if PROBE_BARE is None:
            _record(case, UNKNOWN, "no PATH-resolvable probe command on this host, so the bare-name "
                                   "trap could not be driven")
            self.assertIsNone(PROBE_BARE)
            return
        got = _fork_count([PROBE_BARE] + PROBE_ARGS, close_fds=False, stdout=subprocess.PIPE)
        self.assertIsNotNone(got, "the bare-name shape could not be driven at all")
        if HOST["verdict"] == MEASURED:
            _record(case, MEASURED, "bare %r + close_fds=False -> fork=%d spawn=%d"
                    % (PROBE_BARE, got[0], got[1]))
            self.assertEqual(got[0], 1,
                             "a bare executable name no longer forks — the dirname condition "
                             "changed")
        else:
            _record(case, HOST["verdict"],
                    "bare %r -> fork=%d spawn=%d, but %s" % (PROBE_BARE, got[0], got[1],
                                                             HOST["reason"]))
            self.assertGreaterEqual(sum(got), 1,
                                    "neither syscall was observed for the bare-name shape")

    def test_every_host_dependent_case_said_which_word_it_meant(self):
        """⚠ UNKNOWN IS A STATE, AND A STATE HAS TO BE WRITTEN DOWN. A case that quietly returns
        leaves no trace at all, which reads exactly like a case that measured and agreed. This
        fails if any host-dependent case recorded nothing, or recorded a word outside the three.
        [[unknown-stays-unknown]]

        ⚠ IT DRIVES THE CASES RATHER THAN READING WHAT HAPPENED TO RUN FIRST. unittest orders
        methods by string sort, so the first version of this law ran BEFORE two of the three cases
        it grades and reported them missing. A law that depends on its neighbours' run order is
        measuring the sort, not the behaviour. [[a-law-about-a-row-must-drive-the-row]]"""
        suite = unittest.TestSuite(TestTheDoctorNeverForksAQuartzProcess(n)
                                   for n in HOST_DEPENDENT)
        buf = io.StringIO()
        res = unittest.TextTestRunner(stream=buf, verbosity=0).run(suite)
        self.assertEqual(res.errors, [], "a host-dependent case ERRORED when driven directly, so "
                                         "its state was never written: %r" % (res.errors,))
        missing = [c for c in HOST_DEPENDENT if c not in LEDGER]
        self.assertEqual(missing, [], "these host-dependent cases recorded no state at all, so "
                                      "nobody can tell whether they measured or declined: %r"
                                      % (missing,))
        bad = {c: LEDGER[c] for c in HOST_DEPENDENT
               if LEDGER[c][0] not in (MEASURED, NOT_APPLICABLE, UNKNOWN) or not LEDGER[c][1]}
        self.assertEqual(bad, {}, "a host-dependent case recorded a word that is not one of "
                                  "MEASURED / NOT-APPLICABLE / UNKNOWN, or gave no reason: %r"
                                  % (bad,))

    # ---- the instrument, watching itself -------------------------------------------------

    @unittest.skipIf(NO_FORK, "POSIX only: no fork_exec or posix_spawn guard to read on this OS")
    def test_the_syscall_spy_sees_the_name_subprocess_actually_calls(self):
        """⚠ SUSPECT THE INSTRUMENT FIRST. The spy patches `os.posix_spawn` and
        `_posixsubprocess.fork_exec`. If `subprocess` ever binds either at import time
        (`from _posixsubprocess import fork_exec`), the patch would land on a name nobody reads and
        every case in this file would report fork=0 forever — a green measuring nothing."""
        # ⚠ #150 — the spy now FOLLOWS the binding (3.9 `_posixsubprocess.fork_exec`, 3.12
        # `subprocess._fork_exec`); this case still refuses the one state it exists for: a
        # subprocess whose fork call the spy cannot find at all.
        got = _fork_exec_binding()
        self.assertIsNotNone(got, "subprocess calls fork_exec by neither known spelling "
                                  "(`_posixsubprocess.fork_exec(` / `_fork_exec(`), so the spy "
                                  "patches nothing for fork — every fork=0 in this file is now "
                                  "unmeasured, not clean")
        self.assertIn(got[2].split(".")[-1] + "(",
                      inspect.getsource(subprocess.Popen._execute_child),
                      "the binding the spy patches (%s) is not the name _execute_child calls"
                      % got[2])
        self.assertIn("os.posix_spawn", inspect.getsource(subprocess.Popen._posix_spawn),
                      "subprocess no longer calls `os.posix_spawn` by that dotted name")

    # ---- the classifier, pinned to CPython rather than to memory ------------------------

    @unittest.skipIf(NO_FORK, "POSIX only: no fork_exec or posix_spawn guard to read on this OS")
    def test_the_classifier_covers_every_condition_CPYTHON_ACTUALLY_CHECKS(self):
        """⚠ THE REASON THIS GATE WAS BLIND: IT RECORDED TWO CONDITIONS AND CPYTHON CHECKS
        FOURTEEN. The count is not a number anybody types here — `Popen._execute_child` is parsed
        on the running interpreter and every identifier its posix_spawn gate reads must map to a
        condition this file classifies. A new CPython condition turns this RED instead of quietly
        widening the blind spot."""
        got = _cpython_guard_vars()
        self.assertIsNotNone(got, "the posix_spawn guard's source was not readable on this "
                                  "interpreter, so how many conditions it checks is UNKNOWN — "
                                  "this file's classifier is unverified, not verified")
        uncovered = sorted(v for v in got if v not in GUARD_VAR_TO_CONDITION)
        self.assertEqual(uncovered, [], "CPython's posix_spawn guard reads condition variable(s) "
                                        "%r that this classifier does not model, so a call "
                                        "violating one of them would be graded SPAWNS and would "
                                        "fork" % (uncovered,))
        self.assertGreaterEqual(len(got), 9, "the guard reported only %d condition variables, "
                                             "which is fewer than the nine this file names — the "
                                             "extractor is the suspect, not CPython" % len(got))
        for c in NINE_CONDITIONS:
            self.assertIn(c, set(GUARD_VAR_TO_CONDITION.values()),
                          "%r is named as one of the nine but no guard variable maps to it" % c)

    def test_the_receiver_is_a_DOTTED_name_so_two_run_functions_stay_two(self):
        """⚠ `subprocess.run` AND `_gq.run` ARE BOTH CALLED `run`. The v3429 gate matched on the
        RECEIVER SPELLING (`subprocess` / `_sp` / `sp`) and skipped `_gq` entirely; the obvious
        widening — allow the attribute `run` — would admit every unrelated `.run()` in the file.
        Aliases are resolved to dotted module names, so the two stay distinguishable.
        [[a-widened-guard-admits-what-it-bans]]"""
        tree = ast.parse("import subprocess as _sp\nimport git_quiet as _gq\n"
                         "class T:\n    def run(self): pass\n"
                         "_sp.run(['/bin/true'])\n_gq.run(['git'])\nT().run()\nself.runner.run()\n")
        aliases = _import_aliases(tree)
        names = [_dotted(n.func, aliases) for n in ast.walk(tree) if isinstance(n, ast.Call)]
        self.assertIn("subprocess.run", names)
        self.assertIn("git_quiet.run", names)
        self.assertNotEqual("subprocess.run", "git_quiet.run")
        self.assertIn("self.runner.run", names,
                      "an unrelated `.run()` must still resolve to its OWN dotted name so it can "
                      "be excluded by name rather than by hope")
        doors = discover_spawn_doors(tree)
        self.assertNotIn("self.runner.run", doors,
                         "an unrelated `.run()` was admitted as a spawn door — that is the "
                         "cry-wolf failure of widening on the bare attribute")

    def test_the_wrapper_door_is_DISCOVERED_not_listed(self):
        """⚠ A LIST OF WRAPPERS IS A LIST OF THE ONES SOMEBODY REMEMBERED. `git_quiet.run` is found
        by reading git_quiet.py and seeing that it forwards its own `**kwargs` into
        `subprocess.run` — so the next one-door wrapper is a door the moment it is imported.

        This also fails if the discovery finds NOTHING, which is the shape a blind gate takes."""
        tree = ast.parse(SRC)
        doors = discover_spawn_doors(tree)
        self.assertIn("subprocess.run", doors, "the direct subprocess door was not discovered at "
                                               "all — the classifier is blind, not clean")
        self.assertIn("git_quiet.run", doors,
                      "git_quiet.run is no longer recognised as a subprocess wrapper, so the six "
                      "git spawns in console_doctor are invisible again. Discovered doors: %r"
                      % (sorted(doors),))
        self.assertTrue(doors["git_quiet.run"]["why"].startswith("wrapper"),
                        "git_quiet.run was admitted for the wrong reason: %r"
                        % doors["git_quiet.run"])
        self.assertEqual(doors["git_quiet.run"]["injects"], {},
                         "git_quiet now writes a fork-relevant keyword into the kwargs it "
                         "forwards, so the CALL SITE no longer decides the syscall and every "
                         "site through it is graded on a file its reader never opens: %r"
                         % (doors["git_quiet.run"],))
        with io.open(os.path.join(HERE, "git_quiet.py"),
                     encoding="utf-8", errors="replace") as fh:
            gq = ast.parse(fh.read())
        injects = [k.arg for n in ast.walk(gq) if isinstance(n, ast.Call)
                   for k in n.keywords if k.arg == "close_fds"]
        self.assertEqual(injects, [], "git_quiet now sets close_fds itself, which changes who is "
                                      "responsible for that condition — this classifier grades "
                                      "the CALL SITE and would start crying wolf")

    def test_the_classifier_goes_FORKING_on_each_condition_ALONE(self):
        """⚠ A CLASSIFIER NOBODY SAW SAY NO IS A CLASSIFIER THAT SAYS YES. One synthetic call per
        condition, violating that condition and nothing else, must come back FORKS — and the
        control, violating none, must come back SPAWNS."""
        head = "import subprocess\n"
        control = "subprocess.run(['/bin/true'], close_fds=False)"

        def verdict(expr):
            tree = ast.parse(head + expr + "\n")
            sites = spawn_sites(head + expr + "\n")
            self.assertEqual(len(sites), 1, "the probe %r produced %d sites, not 1 — the SABOTAGE "
                                            "is the suspect" % (expr, len(sites)))
            del tree
            return sites[0]

        got = verdict(control)
        self.assertEqual(got["verdict"], SPAWNS,
                         "the CONTROL call was not classified spawn-eligible (%r), so every red "
                         "below would be attributable to the control, not to the condition"
                         % (got,))

        # ⚠ ABSENCE AND VALUE ARE TWO DIFFERENT SHAPES OF THE SAME VIOLATION, AND ONLY ONE OF
        # THEM WAS THE v3429 DEFECT. MEASURED: sabotaging the classifier back to the old
        # presence-only test left this law GREEN, because its close_fds probe omitted the keyword
        # — the branch that reads the VALUE was never reached. Cause (b): the test could not reach
        # the line, not a weak guard. Both shapes are probed now.
        # [[a-law-about-a-row-must-drive-the-row]]
        probes = {
            "executable-has-a-dirname": [
                "subprocess.run(['true'], close_fds=False)",
                "subprocess.run(['/bin/sh'], close_fds=False, executable='true')",
            ],
            "preexec_fn-is-None": [
                "subprocess.run(['/bin/true'], close_fds=False, preexec_fn=len)"],
            "close_fds-is-False": [
                "subprocess.run(['/bin/true'])",                        # ABSENT -> defaults True
                "subprocess.run(['/bin/true'], close_fds=True)",        # PRESENT and True
            ],
            "no-pass_fds": ["subprocess.run(['/bin/true'], close_fds=False, pass_fds=(7,))"],
            "cwd-is-None": ["subprocess.run(['/bin/true'], close_fds=False, cwd='/tmp')"],
            "stdin-is-not-fd-0-1-2": ["subprocess.run(['/bin/true'], close_fds=False, stdin=0)"],
            "stdout-is-not-fd-0-1-2": ["subprocess.run(['/bin/true'], close_fds=False, stdout=1)"],
            "stderr-is-not-fd-0-1-2": ["subprocess.run(['/bin/true'], close_fds=False, stderr=2)"],
            "start_new_session-is-falsy": [
                "subprocess.run(['/bin/true'], close_fds=False, start_new_session=True)"],
            "user-is-None": ["subprocess.run(['/bin/true'], close_fds=False, user=501)"],
            "group-is-None": ["subprocess.run(['/bin/true'], close_fds=False, group=20)"],
            "extra_groups-is-None": [
                "subprocess.run(['/bin/true'], close_fds=False, extra_groups=[20])"],
            "umask-is-negative": ["subprocess.run(['/bin/true'], close_fds=False, umask=0o022)"],
            "process_group-is-default": [
                "subprocess.run(['/bin/true'], close_fds=False, process_group=0)"],
        }
        self.assertEqual(len(probes["close_fds-is-False"]), 2,
                         "close_fds must be probed BOTH absent AND present-but-True — the "
                         "present-but-True shape is the one the v3429 gate could not see")
        for cond in sorted(set(GUARD_VAR_TO_CONDITION.values())):
            self.assertIn(cond, probes, "condition %r has no probe, so it was never seen refuse"
                          % cond)
            for expr in probes[cond]:
                got = verdict(expr)
                self.assertEqual(got["verdict"], FORKS,
                                 "violating %r ALONE (%s) was not classified FORKS: %r"
                                 % (cond, expr, got))
                self.assertEqual(got["violations"], [cond],
                                 "%s was classified as violating %r — the probe is impure, so "
                                 "the red is not attributable to %r"
                                 % (expr, got["violations"], cond))

    def test_a_FALSY_BUT_NOT_NONE_value_is_a_fork_not_a_pass(self):
        """IDENTITY IS NOT TRUTHINESS, and conflating them was a FALSE ALL-CLEAR.

        ⚠⚠ Found by the cross-family eye on the SHIPPED v3441 bytes, not by this suite. The first
        classifier ran preexec_fn / cwd / user / group / extra_groups through one `elif val:` — a
        truthiness test — while CPython 3.9.6 tests `uid is None`, `gid is None`, `gids is None`,
        `cwd is None`, `preexec_fn is None`. So `user=0` (running as ROOT — the realistic case),
        `group=0`, `cwd=""` and `extra_groups=()` are all FALSY, passed the check, and the site was
        reported SPAWNS. Every one of them forks. A gate written to catch forking sites was blind
        to an entire family of them, and its loop variable `must_be_falsy` was declared and never
        read — the distinction was named and not encoded.

        ⚠ THE BASELINE IS HALF THIS CASE: cwd=None and preexec_fn=None must still read SPAWNS, and
        a non-literal cwd=ROOT must still read FORKS. A fix that reddened those would have blinded
        the gate to the six console_doctor sites v3441 had just repaired — the cure killing the
        patient. [[the-cure-that-kills-the-patient]]
        """
        import ast as _ast
        cases = [
            # the four the truthiness test waved through — ALL fork
            ('subprocess.run(["/usr/bin/git"], close_fds=False, user=0)', "FORKS"),
            ('subprocess.run(["/usr/bin/git"], close_fds=False, group=0)', "FORKS"),
            ('subprocess.run(["/usr/bin/git"], close_fds=False, cwd="")', "FORKS"),
            ('subprocess.run(["/usr/bin/git"], close_fds=False, extra_groups=())', "FORKS"),
            # the baseline — these genuinely satisfy the condition and must stay green
            ('subprocess.run(["/usr/bin/git"], close_fds=False)', "SPAWNS"),
            ('subprocess.run(["/usr/bin/git"], close_fds=False, cwd=None)', "SPAWNS"),
            ('subprocess.run(["/usr/bin/git"], close_fds=False, preexec_fn=None)', "SPAWNS"),
            # still caught: the shape the six repaired sites had
            ('subprocess.run(["/usr/bin/git"], close_fds=False, cwd=ROOT)', "FORKS"),
            # truthiness conditions keep working
            ('subprocess.run(["/usr/bin/git"], close_fds=False, start_new_session=True)', "FORKS"),
        ]
        for srcline, want in cases:
            tree = _ast.parse(srcline)
            got = classify_spawn_call(tree.body[0].value, "subprocess.run", tree, {})
            self.assertEqual(
                got.get("verdict"), want,
                "%s\n  classified %s, expected %s\n  violations=%s notes=%s"
                % (srcline, got.get("verdict"), want, got.get("violations"), got.get("notes")))

    def test_the_classifier_agrees_with_the_REAL_SYSCALL_on_each_condition(self):
        """⚠ CLASSIFY, THEN DRIVE. An AST predicate that nobody ever compared against the
        interpreter is arithmetic about behaviour. Each condition is violated for real, once, and
        the syscall CPython takes is recorded next to what the classifier said.

        ⚠ TWO ARE NOT DRIVABLE AND SAY SO. `extra_groups` needs setgroups() (root), and `pass_fds`
        cannot be isolated at runtime because `Popen.__init__` FORCES close_fds=True when it is
        set — so it would prove two conditions at once, not one. Those stay classifier-only and
        are recorded as such rather than quietly counted as driven."""
        if HOST["verdict"] == UNKNOWN:
            _record("test_the_classifier_agrees_with_the_REAL_SYSCALL_on_each_condition",
                    UNKNOWN, HOST["reason"])
            self.skipTest("host cannot discriminate fork from spawn: " + HOST["reason"])
        base = [PROBE_ABS] + PROBE_ARGS
        bare = ([PROBE_BARE] + PROBE_ARGS) if PROBE_BARE else None
        supported = set(inspect.signature(subprocess.Popen.__init__).parameters)

        drivable = [
            ("executable-has-a-dirname", bare, {"close_fds": False}),
            ("preexec_fn-is-None", base, {"close_fds": False, "preexec_fn": os.getpid}),
            ("close_fds-is-False", base, {}),
            ("cwd-is-None", base, {"close_fds": False, "cwd": "/"}),
            ("stdin-is-not-fd-0-1-2", base, {"close_fds": False, "stdin": 2}),
            ("stdout-is-not-fd-0-1-2", base, {"close_fds": False, "stdout": 2}),
            ("stderr-is-not-fd-0-1-2", base, {"close_fds": False, "stderr": 2}),
            ("start_new_session-is-falsy", base, {"close_fds": False, "start_new_session": True}),
            ("umask-is-negative", base, {"close_fds": False, "umask": 0o022}),
            ("user-is-None", base, {"close_fds": False, "user": os.getuid()}),
            ("group-is-None", base, {"close_fds": False, "group": os.getgid()}),
        ]
        driven, declined = [], []
        for cond, argv, kw in drivable:
            if argv is None:
                declined.append((cond, "no PATH-resolvable probe command on this host"))
                continue
            need = {"user": "user", "group": "group", "umask": "umask"}
            missing = [k for k in kw if k in need and k not in supported]
            if missing:
                declined.append((cond, "CPython %s has no %r keyword" % (sys.version.split()[0],
                                                                        missing)))
                continue
            got = _fork_count(list(argv), **dict(kw))
            if got is None:
                declined.append((cond, "the shape could not be driven"))
                continue
            self.assertEqual(got[0], 1,
                             "violating %r did NOT make CPython fork: fork=%d spawn=%d. Either "
                             "this interpreter dropped the condition, or the TEST could not reach "
                             "it, or the sabotage was inert — diagnose which before changing the "
                             "classifier." % (cond, got[0], got[1]))
            driven.append(cond)

        _record("classifier-vs-syscall", MEASURED,
                "%d condition(s) driven on the real syscall: %s%s"
                % (len(driven), ", ".join(driven),
                   ("; DECLINED: %r" % (declined,)) if declined else ""))
        self.assertGreaterEqual(len(driven), 8,
                                "only %d conditions were driven on the real syscall (declined: "
                                "%r) — a classifier compared against almost nothing is arithmetic"
                                % (len(driven), declined))
        # The two that cannot be isolated at runtime, said out loud rather than counted as driven.
        _record("conditions-not-drivable", NOT_APPLICABLE,
                "extra_groups needs setgroups()/root; pass_fds forces close_fds=True inside "
                "Popen.__init__ so it can never violate alone. Both are classifier-only.")

    # ---- the class law, now able to see what it was skipping -----------------------------

    def test_EVERY_subprocess_call_in_the_doctor_is_spawn_eligible(self):
        """A law about one row would have the reach the fix did. Any NEW shell-out added to this
        module is a new deadlock site unless every condition holds.

        ⚠ v3435 — THIS READS ALL FOURTEEN CONDITIONS AND EVERY DOOR, INCLUDING THE WRAPPER. The
        v3429 version asked only whether the word `close_fds` appeared, and only of receivers
        spelled `subprocess`/`_sp`/`sp` — so `_gq.run(..., cwd=ROOT)` was skipped six times over,
        and `bad` came back `[]` while six live git spawns forked on every eagle tick."""
        sites = spawn_sites(SRC)
        self.assertGreaterEqual(len(sites), 10,
                                "only %d spawn sites were found in console_doctor — the walker "
                                "is the suspect, not the file (a law that matches nothing passes "
                                "forever)" % len(sites))
        forking = [s for s in sites if s["verdict"] == FORKS]
        report = "\n".join(
            "    line %-6d %-16s violates %s%s"
            % (s["line"], s["door"], ", ".join(s["violations"]),
               ("  [%s]" % "; ".join(s["notes"])) if s["notes"] else "")
            for s in forking)
        self.assertEqual(
            forking, [],
            "%d spawn site(s) in console_doctor.py FORK a process that has the Objective-C "
            "runtime loaded — the 28-minute hang:\n%s\n"
            "⚠ `cwd=` is condition six of CPython's posix_spawn gate and a bare `git` fails the "
            "dirname condition; both are as fatal as a missing close_fds.\n"
            "THE SHAPE THIS CLASSIFIER CAN VERIFY, per site:\n"
            "    _gq.run([_spawnable(\"git\"), \"-C\", ROOT, ...], close_fds=False, ...)\n"
            "  · `git -C <dir>` replaces `cwd=<dir>` — same directory, no cwd keyword.\n"
            "  · `_spawnable(\"git\")` gives argv[0] a dirname. ⚠ Resolving git INSIDE git_quiet\n"
            "    instead would be invisible from the call site and this gate would report the\n"
            "    site UNKNOWN, not green — a fix the reader cannot see is not one it can grade.\n"
            "  · `close_fds=False` is still the call site\'s to declare: git_quiet forwards **kw\n"
            "    and injects nothing on POSIX (pinned by test_the_wrapper_door_is_DISCOVERED)."
            % (len(forking), report))

    def test_no_spawn_site_in_the_doctor_is_UNCLASSIFIABLE(self):
        """⚠ UNKNOWN IS NOT GREEN. A site the classifier cannot read is a site nobody has graded,
        and folding it into the pass column is exactly how `bad == []` meant nothing. It gets its
        own verdict so a real blind spot cannot hide behind a clean forking count.
        [[unknown-stays-unknown]]"""
        sites = spawn_sites(SRC)
        # ⚠ ZERO NEEDS A DENOMINATOR. MEASURED: forcing the walker to match nothing left this law
        # GREEN — "0 unclassifiable of 0 sites" reads exactly like "0 of 12". Cause (a), a blind
        # guard, and the population is now part of the verdict. [[zero-needs-a-denominator]]
        self.assertGreaterEqual(len(sites), 10,
                                "only %d spawn sites were examined, so '0 unclassifiable' is a "
                                "statement about an empty population" % len(sites))
        unknown = [s for s in sites if s["verdict"] == UNKNOWN]
        report = "\n".join("    line %-6d %-16s unknown: %s"
                           % (s["line"], s["door"], ", ".join(s["unknowns"])) for s in unknown)
        self.assertEqual(unknown, [], "%d of %d spawn site(s) in console_doctor.py cannot be "
                                      "classified either way, so whether they fork is "
                                      "UNMEASURED:\n%s" % (len(unknown), len(sites), report))

    def test_the_class_law_would_SEE_a_cwd_added_to_any_door(self):
        """⚠ THE v3429 GATE WENT GREEN ON SIX FORKING SITES, so "it passes" is not evidence that it
        can fail. This drives the classifier over a synthetic copy of each door shape carrying the
        exact defect that was invisible — `cwd=` on a wrapper call — and requires FORKS."""
        for door in ("subprocess.run", "_sp.run", "_gq.run"):
            src = ("import subprocess\nimport subprocess as _sp\nimport git_quiet as _gq\n"
                   "%s(['/bin/git', 'status'], close_fds=False, cwd='/tmp')\n" % door)
            sites = spawn_sites(src)
            self.assertEqual(len(sites), 1, "%s was not recognised as a spawn door at all" % door)
            self.assertEqual(sites[0]["verdict"], FORKS,
                             "%s(..., cwd=...) was not classified as forking: %r"
                             % (door, sites[0]))
            self.assertIn("cwd-is-None", sites[0]["violations"])

    # ---- v3443: the five FALSE ALL-CLEARS the cross-family eye found in the shipped v3441 ----

    def _drive(self, table, where=None):
        """Classify each source and require the stated verdict. -> None

        ⚠ DRIVE THE CLASSIFIER, NEVER ASSERT ARITHMETIC ABOUT IT, and assert the PREMISE first:
        a probe that produces no site at all would satisfy `verdict != SPAWNS` by producing
        nothing, which is a green measuring an empty population. [[zero-needs-a-denominator]]"""
        for src, want, why in table:
            sites = spawn_sites(src, where or HERE)
            self.assertEqual(len(sites), 1,
                             "the probe produced %d sites, not 1 — the PROBE is the suspect "
                             "before the classifier is:\n%s" % (len(sites), src))
            self.assertEqual(
                sites[0]["verdict"], want,
                "%s\n  classified %s, wanted %s — %s\n  violations=%s unknowns=%s how=%r"
                % (src, sites[0]["verdict"], want, why, sites[0]["violations"],
                   sites[0]["unknowns"], sites[0]["how"]))

    def test_the_LIVE_argv0_is_not_the_FIRST_one_the_reader_happened_to_find(self):
        """v3443 (F3) — A REBOUND NAME IS A ONE-TO-MANY FACT.

        `_argv0` returned the first assignment that yielded an element and dropped the rest, and
        `_assigned_values` walked THROUGH nested `def`s. So an absolute spelling that is dead —
        overwritten, or sitting in an inner function that never runs here — answered for a live
        bare one, and the site read SPAWNS while every call forked.

        ⚠ THE BASELINE IS HALF THIS CASE. A single absolute assignment must still read SPAWNS,
        and a closure reading its ENCLOSING function's argv must still resolve — a scope reader
        tightened until it sees nothing is a gate that accuses everything.
        [[one-to-one-store-for-a-one-to-many-fact]] [[the-cure-that-kills-the-patient]]"""
        self._drive([
            ("import subprocess\n"
             "def f():\n"
             "    args = ['/usr/bin/git', 'status']\n"
             "    args = ['git', 'status']\n"
             "    subprocess.run(args, close_fds=False)\n",
             UNKNOWN,
             "the live argv0 is bare 'git'; SPAWNS here is the false all-clear"),
            ("import subprocess\n"
             "def f():\n"
             "    def inner():\n"
             "        args = ['/usr/bin/git', 'status']\n"
             "    args = ['git', 'status']\n"
             "    subprocess.run(args, close_fds=False)\n",
             FORKS,
             "inner()'s argv is in another scope and cannot excuse this bare name"),
            # ---- baselines: the correct shapes must survive ----
            ("import subprocess\n"
             "def f():\n"
             "    args = ['/usr/bin/git', 'status']\n"
             "    subprocess.run(args, close_fds=False)\n",
             SPAWNS, "one absolute assignment, nothing to disagree with"),
            ("import subprocess\n"
             "def outer():\n"
             "    args = ['/usr/bin/git', 'status']\n"
             "    def inner():\n"
             "        subprocess.run(args, close_fds=False)\n",
             SPAWNS, "a CLOSURE may read its enclosing function's argv — losing that would make "
                     "every nested spawn site unreadable"),
            ("import subprocess\n"
             "def f():\n"
             "    args = ['git', 'status']\n"
             "    args = ['git', 'log']\n"
             "    subprocess.run(args, close_fds=False)\n",
             FORKS, "both spellings are bare, so there is nothing unknown about it"),
        ])

    def test_a_BARE_BRANCH_of_a_ternary_is_not_absolute_if_installed(self):
        """v3443 (F4) — AND THE STATE THAT EXCUSED IT WAS ONLY A NOTE.

        `["/usr/bin/git" if ok else "git"]` collapsed to ABSOLUTE_IF_INSTALLED, which adds a note
        and no violation, so the verdict stayed SPAWNS — while the else-branch forks every time it
        runs. It was not even self-consistent: {BARE, ABSOLUTE_IF_INSTALLED} fell through to
        UNKNOWN and {BARE, ABSOLUTE} did not.

        ⚠ THE BASELINE IS THE WHOLE RISK HERE. console_doctor really does write
        `_PS = "/bin/ps" if os.path.exists("/bin/ps") else "ps"`, and `_spawnable()` is the same
        shape — a ternary whose CONDITION asks whether the tool is installed. Reddening those
        would have accused the live, measured-non-forking corpse row. Only an UNGUARDED condition
        loses the excuse. [[the-cure-that-kills-the-patient]]"""
        self._drive([
            ("import subprocess\n"
             "ok = True\n"
             "subprocess.run(['/usr/bin/git' if ok else 'git'], close_fds=False)\n",
             UNKNOWN, "nobody has shown the bare branch is unreachable"),
            ("import subprocess\n"
             "import shutil\n"
             "ok = True\n"
             "subprocess.run([shutil.which('git') if ok else 'git'], close_fds=False)\n",
             UNKNOWN, "{BARE, ABSOLUTE_IF_INSTALLED} was already UNKNOWN and must stay so"),
            # ---- baselines: the AUDITED resolver shape keeps its state ----
            ("import subprocess\n"
             "import os\n"
             "subprocess.run(['/bin/ps' if os.path.exists('/bin/ps') else 'ps'], close_fds=False)\n",
             SPAWNS, "this is console_doctor's own _PS line — reddening it blinds the gate to the "
                     "corpse row it exists for"),
            ("import subprocess\n"
             "import os\n"
             "subprocess.run(['/usr/bin/git' if os.path.isfile('/usr/bin/git') else 'git'],\n"
             "               close_fds=False)\n",
             SPAWNS, "the same shape under a different existence test"),
            ("import subprocess\n"
             "ok = True\n"
             "subprocess.run(['/usr/bin/git' if ok else '/bin/git'], close_fds=False)\n",
             SPAWNS, "both branches carry a dirname, so the condition holds whichever runs"),
        ])

    def test_os_path_join_is_not_a_synonym_for_a_dirname(self):
        """v3443 (F5) — EVERY join MAPPED TO ABSOLUTE.

        `os.path.join("git")` returns `"git"` and `os.path.join("", "git")` returns `"git"`.
        Neither has a dirname, both fork, and both read spawn-eligible. The join is EVALUATED
        where every component is a literal, and is UNKNOWN — never ABSOLUTE — where it is not.

        ⚠ BASELINE: a real `join("/usr/bin", "git")`, and a join whose LAST literal component
        already carries a dirname, must still read SPAWNS."""
        self._drive([
            ("import subprocess\n"
             "import os\n"
             "subprocess.run([os.path.join('git')], close_fds=False)\n",
             FORKS, "join of one bare component IS that bare component"),
            ("import subprocess\n"
             "import os\n"
             "subprocess.run([os.path.join('', 'git')], close_fds=False)\n",
             FORKS, "an empty prefix adds no dirname"),
            ("import subprocess\n"
             "import posixpath\n"
             "subprocess.run([posixpath.join('git')], close_fds=False)\n",
             FORKS, "the same through posixpath"),
            ("import subprocess\n"
             "import os\n"
             "def f(x):\n"
             "    subprocess.run([os.path.join(x, 'git')], close_fds=False)\n",
             UNKNOWN, "an unresolvable prefix is UNKNOWN, and UNKNOWN is not green here"),
            # ---- baselines ----
            ("import subprocess\n"
             "import os\n"
             "subprocess.run([os.path.join('/usr/bin', 'git')], close_fds=False)\n",
             SPAWNS, "a real absolute join"),
            ("import subprocess\n"
             "import os\n"
             "def f(x):\n"
             "    subprocess.run([os.path.join(x, 'bin/git')], close_fds=False)\n",
             SPAWNS, "a LAST component that already has a dirname survives any prefix"),
        ])

    def test_a_wrapper_that_INJECTS_a_condition_is_not_transparent(self):
        """⚠⚠ v3443 (F6) — THE STRUCTURAL ONE, AND THE SAME CLASS AS THE RECEIVER ALLOWLIST.

        Discovery treated ANY `**kw`-forwarding wrapper as transparent and then graded only the
        CALL SITE. A wrapper doing `kw.setdefault("cwd", REPO)` or `subprocess.run(argv, cwd=REPO,
        **kw)` injects condition six into every call through it, and nothing at the call site can
        show it: the site reads `run([abs, ...], close_fds=False)` and grades SPAWNS while every
        call forks. The door was mis-read, so no care at the call site could help.

        ⚠ git_quiet.run IS THIS SHAPE — it writes `kw["creationflags"]`, `kw["env"]` and
        `kw["startupinfo"]` into the kwargs it forwards. It stays transparent only because none of
        those three can move CPython off posix_spawn, and the baseline below pins that: a wrapper
        that writes a NON-fork keyword must not start crying wolf over the ten live sites.
        [[the-unjoined-end]] [[a-widened-guard-admits-what-it-bans]]"""
        mods = {
            "wrap_setdefault": ("import subprocess\n"
                                "REPO = '/repo'\n"
                                "def run(argv, **kw):\n"
                                "    kw.setdefault('cwd', REPO)\n"
                                "    return subprocess.run(argv, **kw)\n"),
            "wrap_explicit": ("import subprocess\n"
                              "REPO = '/repo'\n"
                              "def run(argv, **kw):\n"
                              "    return subprocess.run(argv, cwd=REPO, **kw)\n"),
            "wrap_pop": ("import subprocess\n"
                         "def run(argv, **kw):\n"
                         "    kw.pop('close_fds', None)\n"
                         "    return subprocess.run(argv, **kw)\n"),
            "wrap_maybe": ("import subprocess\n"
                           "REPO = '/repo'\n"
                           "def run(argv, **kw):\n"
                           "    if REPO:\n"
                           "        kw['cwd'] = REPO\n"
                           "    return subprocess.run(argv, **kw)\n"),
            "wrap_quiet": ("import subprocess\n"
                           "def run(argv, **kw):\n"
                           "    kw['env'] = {}\n"
                           "    kw['creationflags'] = 0\n"
                           "    return subprocess.run(argv, **kw)\n"),
        }
        with tempfile.TemporaryDirectory() as tmp:
            for name, body in sorted(mods.items()):
                with io.open(os.path.join(tmp, name + ".py"), "w", encoding="utf-8") as fh:
                    fh.write(body)
            # ⚠ PREMISE FIRST. If the fixtures were not written or not parsed, discovery finds
            # nothing and every `!= SPAWNS` below would hold for the wrong reason.
            doors = discover_spawn_doors(ast.parse("import wrap_setdefault\nimport wrap_quiet\n"),
                                         tmp)
            self.assertIn("wrap_setdefault.run", doors,
                          "the injecting wrapper was not even discovered as a door, so nothing "
                          "below measures injection: %r" % (sorted(doors),))
            self.assertEqual(doors["wrap_setdefault.run"]["injects"].get("cwd", (None,))[0],
                             INJECT_SETDEFAULT,
                             "the setdefault injection was not recorded: %r"
                             % (doors["wrap_setdefault.run"],))
            self.assertEqual(doors["wrap_quiet.run"]["injects"], {},
                             "env/creationflags are NOT fork conditions; recording them would "
                             "make this guard cry wolf on git_quiet and on the ten live sites: %r"
                             % (doors["wrap_quiet.run"],))
            self._drive([
                ("import wrap_setdefault\n"
                 "wrap_setdefault.run(['/usr/bin/git', 'status'], close_fds=False)\n",
                 FORKS, "the wrapper adds cwd and the call site cannot show it"),
                ("import wrap_explicit\n"
                 "wrap_explicit.run(['/usr/bin/git', 'status'], close_fds=False)\n",
                 FORKS, "cwd= at the forwarding call is an injection too"),
                ("import wrap_pop\n"
                 "wrap_pop.run(['/usr/bin/git'], close_fds=False)\n",
                 FORKS, "the wrapper DELETES the site's close_fds, which defaults back to True"),
                ("import wrap_maybe\n"
                 "wrap_maybe.run(['/usr/bin/git'], close_fds=False)\n",
                 UNKNOWN, "written under a branch — nobody here can say, and UNKNOWN blocks"),
                # ---- baselines ----
                ("import wrap_setdefault\n"
                 "wrap_setdefault.run(['/usr/bin/git'], close_fds=False, cwd=None)\n",
                 SPAWNS, "the site passed cwd itself, so setdefault injects nothing"),
                ("import wrap_quiet\n"
                 "wrap_quiet.run(['/usr/bin/git', 'status'], close_fds=False)\n",
                 SPAWNS, "git_quiet's exact shape — a wrapper writing only non-fork keywords is "
                         "still transparent"),
            ], where=tmp)

    def test_a_door_is_found_under_EVERY_import_spelling(self):
        """⚠⚠ v3443 (F7) — `from git_quiet import run` COULD NOT FAIL THIS GATE AT ALL.

        The module scan did `if "." in mod: continue`, and a from-import binds its alias to the
        DOTTED name `git_quiet.run`. So the module was never opened, `run(...)` matched no door,
        and a forking site written that way was invisible — not green-because-checked, invisible.
        `async def` wrappers were skipped by the same kind of omission. Door DISCOVERY missing a
        door is the same defect class as the receiver allowlist that hid six forking sites.

        ⚠ BASELINE: the correct shape through the same spelling must still read SPAWNS, and an
        unrelated `from x import run` where x is not a wrapper must NOT become a door.
        [[presence-law-vs-reachability-law]]"""
        mods = {
            "wrap_plain": ("import subprocess\n"
                           "def run(argv, **kw):\n"
                           "    return subprocess.run(argv, **kw)\n"),
            "wrap_async": ("import subprocess\n"
                           "async def run(argv, **kw):\n"
                           "    return subprocess.run(argv, **kw)\n"),
            "wrap_none": ("def run(argv):\n"
                          "    return len(argv)\n"),
        }
        with tempfile.TemporaryDirectory() as tmp:
            for name, body in sorted(mods.items()):
                with io.open(os.path.join(tmp, name + ".py"), "w", encoding="utf-8") as fh:
                    fh.write(body)
            doors = discover_spawn_doors(
                ast.parse("from wrap_plain import run\nfrom wrap_async import run as arun\n"
                          "from wrap_none import run as nrun\n"), tmp)
            self.assertIn("wrap_plain.run", doors,
                          "a from-imported wrapper is still not a door: %r" % (sorted(doors),))
            self.assertIn("wrap_async.run", doors,
                          "an `async def` wrapper is still not a door: %r" % (sorted(doors),))
            self.assertNotIn("wrap_none.run", doors,
                             "a module that never touches subprocess was admitted as a door — "
                             "that is the cry-wolf direction: %r" % (sorted(doors),))
            self._drive([
                ("from wrap_plain import run\n"
                 "run(['git', 'status'], close_fds=False)\n",
                 FORKS, "a bare argv0 through a from-imported door"),
                ("import wrap_async\n"
                 "wrap_async.run(['git'], close_fds=False)\n",
                 FORKS, "the same through an async wrapper"),
                # ---- baselines ----
                ("from wrap_plain import run\n"
                 "run(['/usr/bin/git', 'status'], close_fds=False)\n",
                 SPAWNS, "the correct shape must survive the same spelling"),
            ], where=tmp)


RED_PROOF = [
    {
        "why": "#150 - the spy stops patching the fork_exec binding it found: every fork count reads 0, so the baseline shape that really does fork is reported as never having forked — the CI false-red shape, and on any interpreter a spy that measures nothing",
        "file": "test_the_doctor_never_forks_a_quartz_process.py",
        "needs": "posix",   # v3860 - the spy patches fork_exec, which only a POSIX interpreter has
        "find": "        if self.fork_binding is not None:\n            owner, attr, _spelling = self.fork_binding",
        "replace": "        if False:\n            owner, attr, _spelling = self.fork_binding",
        "matches": 1,
    },
    {
        "why": "v3429 - close_fds REMOVED. CPython takes posix_spawn only when close_fds is false, "
               "and it DEFAULTS TO TRUE - so dropping the keyword silently restores the fork that "
               "deadlocked for 28 minutes at 0% CPU and refused four pushes.",
        "file": "console_doctor.py",
        "find": "                      close_fds=False, timeout=15).stdout.decode(\"utf-8\", \"replace\")",
        "replace": "                      timeout=15).stdout.decode(\"utf-8\", \"replace\")",
        "matches": 1,
    },
    {
        "why": "v3429 - THE ABSOLUTE PATH REMOVED. The other half, and the invisible one: with a "
               "bare name the executable has no dirname, CPython's gate fails, and it forks again "
               "while close_fds=False makes the call LOOK fixed.",
        "file": "console_doctor.py",
        "find": "    _PS = \"/bin/ps\" if os.path.exists(\"/bin/ps\") else \"ps\"",
        "replace": "    _PS = \"ps\"",
        "matches": 1,
    },
    {
        "why": "v3435 - close_fds SET TO TRUE RATHER THAN REMOVED. This is the tamper the v3429 "
               "gate could not see at all: it asked `if \"close_fds\" not in kws`, which is a "
               "PRESENCE test, so `close_fds=True` - the literal fork - read as compliant. The "
               "classifier now reads the VALUE, and this proof fails if it ever stops doing so.",
        "file": "console_doctor.py",
        "find": "        p = _sp.run([_spawnable(\"gh\"), \"api\", \"rate_limit\"], capture_output=True,\n"
                "                    encoding=\"utf-8\", errors=\"replace\", close_fds=False, timeout=12)",
        "replace": "        p = _sp.run([_spawnable(\"gh\"), \"api\", \"rate_limit\"], capture_output=True,\n"
                   "                    encoding=\"utf-8\", errors=\"replace\", close_fds=True, timeout=12)",
        "matches": 1,
    },
    {
        "why": "v3435 - A cwd= ADDED TO A DIRECT subprocess CALL. cwd is condition SIX of "
               "CPython's posix_spawn gate and the v3429 gate never looked at it, which is how "
               "six `_gq.run(..., cwd=ROOT)` git spawns sat forking in a LIVE doctor row. The "
               "classifier must go red on a cwd anywhere, not only on the wrapper.",
        "file": "console_doctor.py",
        "find": "        frames = subprocess.run([_spawnable(\"du\"), \"-sk\", os.path.join(HERE, \"frames\")],\n"
                "                                capture_output=True, text=True, encoding=\"utf-8\", errors=\"replace\", close_fds=False,\n"
                "                                timeout=60)",
        "replace": "        frames = subprocess.run([_spawnable(\"du\"), \"-sk\", os.path.join(HERE, \"frames\")],\n"
                   "                                capture_output=True, text=True, encoding=\"utf-8\", errors=\"replace\", close_fds=False,\n"
                   "                                cwd=HERE, timeout=60)",
        "matches": 1,
    },
    # ---- v3443: the five FALSE ALL-CLEARS, each tampered back into the classifier itself -----
    # ⚠ THESE TAMPER THIS FILE, NOT console_doctor. The five holes were defects in the CLASSIFIER,
    # so a proof that edits the subject would prove the wrong thing: each one restores the exact
    # line that graded a forking shape as spawn-eligible. Every one was driven and SEEN RED.
    {
        "why": "v3443 (F3) - _argv0 KEEPS ONLY THE FIRST ASSIGNMENT AGAIN. `args = [ABS]` followed "
               "by `args = ['git']` then handed the classifier the dead absolute spelling and the "
               "site read SPAWNS while every call forked. A one-to-many fact in a one-to-one store.",
        "file": "test_the_doctor_never_forks_a_quartz_process.py",
        "find": "        for v in _assigned_values(node.id, func, tree):\n"
                "            out.extend(_argv0_nodes(v, func, tree, aliases, depth + 1))\n"
                "        return out",
        "replace": "        for v in _assigned_values(node.id, func, tree):\n"
                   "            got = _argv0_nodes(v, func, tree, aliases, depth + 1)\n"
                   "            if got:\n"
                   "                return got[:1]\n"
                   "        return out",
        "matches": 1,
    },
    {
        "why": "v3443 (F3, second half) - THE SCOPE READER WALKS THROUGH NESTED defs AGAIN. "
               "`ast.walk` descends into an inner function, so an argv assigned in a `def inner()` "
               "that never runs at the call site answered for the bare one that does. A "
               "scope-blind reader answers a question nobody asked.",
        "file": "test_the_doctor_never_forks_a_quartz_process.py",
        "find": "        if isinstance(node, _NESTED_SCOPES):\n"
                "            continue",
        "replace": "        if isinstance(node, _NESTED_SCOPES):\n"
                   "            pass",
        "matches": 1,
    },
    {
        "why": "v3443 (F4) - EVERY ABSOLUTE/BARE TERNARY EXCUSED AGAIN. `['/usr/bin/git' if ok "
               "else 'git']` collapsed to ABSOLUTE_IF_INSTALLED, which is a NOTE and not a "
               "violation, so the verdict stayed SPAWNS while the else-branch forks whenever it "
               "runs. Only a condition that ASKS whether the tool is installed earns that state.",
        "file": "test_the_doctor_never_forks_a_quartz_process.py",
        # ⚠ SPLIT ACROSS TWO LITERALS ON PURPOSE. A self-targeting proof whose `find` is one plain
        # line matches TWICE — once in the code and once in this declaration — and the
        # well-formedness gate refuses it. Concatenation keeps the joined form out of the bytes.
        "find": "        if BARE in (a, b) and (ABSOLUTE in (a, b) or ABSOLUTE_IF_INSTALLED in (a, b)) \\\n"
                "                and _tests_whether_the_tool_is_installed(node.test, aliases):",
        "replace": "        if BARE in (a, b) and (ABSOLUTE in (a, b) or ABSOLUTE_IF_INSTALLED in (a, b)) \\\n"
                   "                and (True or _tests_whether_the_tool_is_installed(node.test, aliases)):",
        "matches": 1,
    },
    {
        "why": "v3443 (F5) - EVERY os.path.join MAPPED TO ABSOLUTE AGAIN. `os.path.join('git')` "
               "returns 'git' and forks; so does `os.path.join('', 'git')`. A join is not a "
               "dirname, and assuming it is was a false all-clear on the executable condition.",
        "file": "test_the_doctor_never_forks_a_quartz_process.py",
        "find": "    mod = JOIN_MODULES[d]\n    parts, all_literal = [], True",
        "replace": "    mod = JOIN_MODULES[d]\n    return ABSOLUTE, d + \"(...)\"\n    parts, all_literal = [], True",
        "matches": 1,
    },
    {
        "why": "v3443 (F6) - WRAPPER INJECTIONS IGNORED AGAIN. A one-door wrapper doing "
               "`kw.setdefault('cwd', REPO)` or `subprocess.run(argv, cwd=REPO, **kw)` injects "
               "condition six into every call through it, and the CALL SITE cannot show it. "
               "Grading only the call site is grading half the call - the same defect class as "
               "the receiver allowlist that hid six forking sites.",
        "file": "test_the_doctor_never_forks_a_quartz_process.py",
        "find": "    for kw, (mode, how) in sorted((door or {}).get(\"injects\", {}).items()):",
        "replace": "    for kw, (mode, how) in sorted({}.items()):",
        "matches": 1,
    },
    {
        "why": "v3443 (F7) - DOTTED IMPORT SPELLINGS SKIPPED AGAIN. `from git_quiet import run` "
               "binds its alias to the dotted name `git_quiet.run`, the module scan did "
               "`if '.' in mod: continue`, and so a forking site written that way could not fail "
               "this gate AT ALL. Door discovery missing a door is not a green, it is a blind spot.",
        "file": "test_the_doctor_never_forks_a_quartz_process.py",
        "find": "        candidates.add(mod.rsplit(\".\", 1)[0] if \".\" in mod else mod)",
        "replace": "        candidates.add(mod)",
        "matches": 1,
    },
    {
        "why": "v3443 (F7, second half) - `async def` WRAPPERS SKIPPED AGAIN. The discovery loop "
               "tested only ast.FunctionDef, so an async one-door wrapper was never a door.",
        "file": "test_the_doctor_never_forks_a_quartz_process.py",
        # split across two literals for the same reason as F4 above
        "find": "            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):\n"
                "                continue",
        "replace": "            if not isinstance(fn, ast.FunctionDef):\n"
                   "                continue",
        "matches": 1,
    },
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
