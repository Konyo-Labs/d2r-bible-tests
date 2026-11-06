# -*- coding: utf-8 -*-
"""Windows git children of TV DIABLO must not allocate a console.

Konyo, 2026-09-21: git.exe windows steal focus every couple of minutes, 2-3 in a
row, while the console is sitting idle. PATH git (`Git\\cmd\\git.exe`) is a CUI
wrapper; a spawn without CREATE_NO_WINDOW (and without preferring mingw64 git)
pops a real terminal and alt-tabs him off the game.

This guard reads control_app.py as a tree, not as a character window, and fails
when a git argv is handed to subprocess.run / Popen / check_output instead of
_git_run.
"""
import ast
import io
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))

# ⚠ HIS WINDOWS CONSOLE IS cp1255: a bare print of ⚠ or an em dash crashes the script
# WHILE REPORTING, so a clean tree exits non-zero for a reason unrelated to the check.
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
SRC_PATH = os.path.join(HERE, "control_app.py")

# ⚠⚠ v3409 — THE GATE READ ONE FILE AND THE FAULT LIVED IN TWO. The cross-family review of v3404
# named a site v3407 could not reach: console_doctor.py spawns git as well (`git show
# --name-only`, and `git rev-list --count HEAD..origin/main` on the eagle tick). This guard only
# ever opened control_app.py, so it was green while two more console-popping spawns survived in a
# file it never looked at. A guard's REACH is part of its verdict.
SRC_PATHS = (SRC_PATH, os.path.join(HERE, "console_doctor.py"),
             # v3866 (his work ALT, 2026-11-06 03:08: a terminal window kept popping over his game) - every module whose git
             # runs inside the console or its pythonw children on Windows: the self-prove lane, heart2 (the proof import and
             # prove), the gate ledger heart2 keys with, and the launcher's pull
             os.path.join(HERE, "self_prove.py"), os.path.join(HERE, "heart2.py"), os.path.join(HERE, "gate_ledger.py"),
             os.path.join(HERE, "launcher_pull.py"))
DOOR_PATH = os.path.join(HERE, "git_quiet.py")


def _is_git_argv(node):
    """True when the call's first positional arg is an argv whose first element is 'git'.

    ⚠⚠ v3407 — AND AN ARGV CAN BE *BUILT*, NOT ONLY WRITTEN. The first cut matched only a
    literal List/Tuple, so `["git", "-C", root, ...] + list(paths)` — a BinOp — was invisible to
    it. MEASURED the hour this shipped: the AST walk reported 13 sites clean while a far cruder
    regex in the heart row found a 14th, in `_tree_is_mid_edit`. Two checks disagreeing IS the
    finding; the stricter-looking instrument was the blind one. [[feedback-contradiction-is-the-finding]]
    """
    if not node.args:
        return False
    a0 = node.args[0]
    while isinstance(a0, ast.BinOp) and isinstance(a0.op, ast.Add):
        a0 = a0.left                      # ["git", ...] + list(paths) -> the literal on the left
    if isinstance(a0, (ast.List, ast.Tuple)) and a0.elts:
        e0 = a0.elts[0]
        return isinstance(e0, ast.Constant) and e0.value == "git"
    return False


def _git_names(tree):
    """v3866 - names a git argv is BOUND to: `for key, args in (("head", ["git", ...]), ...)` and `x = ["git", ...]`.
    MEASURED on his work ALT: control_app's fleet reader spawned `args` - a name - through subprocess.run, so the literal
    check above never saw it, and it opened a terminal over his game every 2 minutes. -> {name}"""
    out = set()

    def _gitlist(n):
        return isinstance(n, (ast.List, ast.Tuple)) and n.elts and isinstance(n.elts[0], ast.Constant) and n.elts[0].value == "git"
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and _gitlist(n.value):
            out.update(t.id for t in n.targets if isinstance(t, ast.Name))
        if isinstance(n, ast.For) and isinstance(n.iter, (ast.List, ast.Tuple)):
            pairs = [e for e in n.iter.elts if isinstance(e, (ast.List, ast.Tuple))]
            if pairs and any(any(_gitlist(x) for x in p.elts) for p in pairs) and isinstance(n.target, ast.Tuple):
                for i, t in enumerate(n.target.elts):
                    if isinstance(t, ast.Name) and any(len(p.elts) > i and _gitlist(p.elts[i]) for p in pairs):
                        out.add(t.id)
    return out


# Aliases the one door is imported under. `git_quiet.run` and `_gq.run` are the door;
# `subprocess.run` is the thing the door exists to replace.
DOOR_MODULES = ("git_quiet", "_git_quiet", "_gq", "GQ")


def _callee_name(node):
    """A DOTTED name, because the last segment alone cannot tell the door from the hole.

    ⚠⚠ v3409 — THIS EXACT BLINDNESS WAS CAUGHT BY heart2, ONE HOUR AFTER I INTRODUCED IT.
    Widening the gate to accept the door's new home, `_gq.run(...)`, I accepted the bare callee
    name "run" — and `subprocess.run(...)` is ALSO an Attribute whose attr is "run". So the guard
    admitted precisely the call it exists to ban, and its own red-proof stayed GREEN through its
    own defeat: `BLIND ← stayed GREEN through its own defeat (1 match(es))`. The match count was
    1, so the sabotage was sound and the LAW was weak. [[sabotage-is-usually-the-wrong-one]]
    (the mirror case) [[source-reading-guard]]
    """
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        base = func.value
        if isinstance(base, ast.Name):
            return "%s.%s" % (base.id, func.attr)
        return "?.%s" % func.attr
    return None


def _is_the_one_door(name):
    if name == "_git_run":
        return True
    if not name or "." not in name:
        return False
    mod, _, attr = name.rpartition(".")
    return attr == "run" and mod in DOOR_MODULES


class TheRealGitIsFoundInEveryLayout(unittest.TestCase):
    """v3866 - Git for Windows ships mingw64, ucrt64 and clang64 builds. His work ALT has ucrt64 and no mingw64, so the door
    fell back to PATH's Git\\cmd\\git.exe wrapper and every console git call opened a terminal over his game."""

    def _found(self, present, which=r"C:\Program Files\Git\cmd\git.exe", env=None):
        import sys
        sys.path.insert(0, HERE)
        import git_quiet as G
        return G.real_git(_isfile=lambda p: p in present, _which=lambda n: which,
                          _env={"ProgramFiles": r"C:\Program Files"} if env is None else env)

    def test_ucrt64_mingw64_and_clang64_are_each_found_beside_the_wrapper(self):
        for lay in ("ucrt64", "mingw64", "clang64"):
            p = r"C:\Program Files\Git\%s\bin\git.exe" % lay
            self.assertEqual(self._found({p}), p, "%s git was not found, so the wrapper runs and a window opens" % lay)

    def test_an_install_elsewhere_is_found_through_the_path(self):
        p = r"D:\Tools\Git\ucrt64\bin\git.exe"
        self.assertEqual(self._found({p}, which=r"D:\Tools\Git\cmd\git.exe", env={}), p)

    def test_no_real_git_is_none_never_the_wrapper(self):
        self.assertIsNone(self._found(set()))


class TestWindowsGitSpawnsHideTheConsole(unittest.TestCase):
    def test_every_git_argv_goes_through_the_ONE_door(self):
        offenders, total = [], 0
        for p in SRC_PATHS:
            with io.open(p, encoding="utf-8") as fh:
                src = fh.read()
            tree = ast.parse(src)
            # a name is a git argv only inside the function that binds it (taskkill's `args` is not the fleet's), and only
            # a SPAWNING call can pop a window (isinstance(args, ...) cannot)
            bound_calls = set()
            for fn in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
                names = _git_names(fn)
                for c in ast.walk(fn):
                    if (isinstance(c, ast.Call) and c.args and isinstance(c.args[0], ast.Name) and c.args[0].id in names
                            and (_callee_name(c) or "").rpartition(".")[2] in ("run", "Popen", "check_output", "call",
                                                                             "check_call", "_git_run")):
                        bound_calls.add(id(c))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                if not (_is_git_argv(node) or id(node) in bound_calls):
                    continue
                total += 1
                name = _callee_name(node)
                if not _is_the_one_door(name):
                    offenders.append("%s L%s %s(... ['git', ...])"
                                     % (os.path.basename(p), node.lineno, name or "?"))
        self.assertEqual(
            offenders,
            [],
            "git is spawned outside the one door, so Windows will pop a console and steal "
            "focus:\n  " + "\n  ".join(offenders),
        )
        self.assertGreaterEqual(total, 14,
                                "only %d git argv site(s) were found across %d file(s) — the walk "
                                "has stopped reaching them, which is a green that means nothing"
                                % (total, len(SRC_PATHS)))
        print("git argv sites across %d file(s): %d, all through the one door"
              % (len(SRC_PATHS), total))

    def test_there_is_exactly_ONE_door_body(self):
        """⚠ [[copy-drift]] — two bodies means one of them eventually stops matching."""
        bodies = []
        for name in sorted(os.listdir(HERE)):
            if not name.endswith(".py") or name.startswith("test_"):
                continue
            with io.open(os.path.join(HERE, name), encoding="utf-8") as fh:
                code = "\n".join(l.split("#", 1)[0] for l in fh.read().split("\n"))
            if "mingw64" in code and "STARTF_USESHOWWINDOW" in code:
                bodies.append(name)
        self.assertEqual(bodies, ["git_quiet.py"],
                         "the mingw redirect exists in more than one place, so a fix to one leaves "
                         "the other popping windows: %s" % bodies)

    def test_the_one_door_hides_the_window_on_windows(self):
        with io.open(DOOR_PATH, encoding="utf-8") as fh:
            src = fh.read()
        i = src.find("def run(")
        self.assertGreater(i, -1, "git_quiet.run is gone, so nothing hides git consoles")
        blk = src[i:src.find("\ndef ", i + 1)]
        self.assertIn("WIN_CREATE", blk, "the one door dropped CREATE_NO_WINDOW")
        self.assertIn("real_git()", blk, "the one door no longer calls the real git binary directly")
        self.assertNotIn("headless-git", blk,
                         "headless-git.exe still spawns a CUI git.exe child that WT focuses")
        self.assertIn("STARTF_USESHOWWINDOW", blk, "the one door dropped SW_HIDE")
        self.assertIn("GIT_TERMINAL_PROMPT", blk, "the one door can still prompt and steal focus")


RED_PROOF = [
    {
        "why": "v3866 - the door knows only mingw64 again: on his work ALT (ucrt64 Git) every console git call opened a "
               "terminal over his game, 7 in 8 seconds",
        "file": "git_quiet.py",
        "find": 'GIT_LAYOUTS = ("mingw64", "ucrt64", "clang64", "clangarm64", "mingw32")',
        "replace": 'GIT_LAYOUTS = ("mingw64",)',
        "matches": 1,
    },
    {
        "why": "v3866 - a git argv bound to a NAME goes back to subprocess.run (the fleet reader that popped every 2 min)",
        "file": "control_app.py",
        "find": "                r = _git_run(       # v3866 - a variable argv hid this plain spawn from the window law; it popped a terminal\n",
        "replace": "                r = subprocess.run(       # v3866 - a variable argv hid this plain spawn from the window law; it popped a terminal\n",
        "matches": 1,
    },
    {
        "why": "v3866 - heart2's own git question (the proof import, a pythonw child) spawns git plainly again",
        "file": "heart2.py",
        "find": '        r = _gq.run(["git", "-C", REPO] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE,\n',
        "replace": '        r = subprocess.run(["git", "-C", REPO] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE,\n',
        "matches": 1,
    },
    {
        "why": "v3407 — ONE SITE IS ENOUGH TO POP A WINDOW. Sending a single git argv back to "
               "subprocess.run restores a CUI child on Windows: `pythonw` owns no console, so the "
               "child ALLOCATES one, and that is a real terminal on top of D2R. Measured live "
               "2026-09-21 — 2-3 windows in a row, every couple of minutes, while the console sat "
               "idle. The AST walk must name the offender by line rather than pass because most "
               "sites are correct.",
        "file": "control_app.py",
        "find": '        r = _git_run(\n            ["git", "rev-list", "HEAD..origin/main", "--count"],',
        "replace": '        r = subprocess.run(\n            ["git", "rev-list", "HEAD..origin/main", "--count"],',
        "matches": 1,
    },
    {
        "why": "v3407 — WITHOUT THE MINGW REDIRECT THE FLAG PROTECTS THE WRONG BINARY. Git for "
               "Windows' PATH git is a 46 KB CUI WRAPPER that spawns the real git WITHOUT "
               "inheriting CREATE_NO_WINDOW, so hiding the wrapper hides nothing. Dropping "
               "_GIT_MINGW leaves a helper that looks careful and still alt-tabs him off the game.",
        "file": "git_quiet.py",
        "find": '            _rg = real_git()\n            if _rg:\n                argv[0] = _rg\n',
        # v3867 - a tamper must leave VALID code: "" left `if argv and argv[0] == "git":` with no body, so the law went red
        # on a SyntaxError (heart2's prover rightly calls that INVALID - v3866's proof shard 7 did)
        "replace": "            pass\n",
        "matches": 1,
    },
    {
        "why": "v3407 — SW_HIDE IS THE SECOND HALF. CREATE_NO_WINDOW governs whether a console is "
               "allocated; STARTF_USESHOWWINDOW + wShowWindow 0 governs whether any window the "
               "child does create is shown. Dropping it leaves the case that Windows Terminal "
               "takes the focus anyway.",
        "file": "git_quiet.py",
        "find": "        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW\n        si.wShowWindow = 0\n",
        "replace": "",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
