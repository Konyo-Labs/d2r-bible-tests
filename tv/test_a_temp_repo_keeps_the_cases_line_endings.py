# -*- coding: utf-8 -*-
"""#107 (REG-3626) - A LAW'S OWN TEMP REPO KEEPS THE CASE'S LINE ENDINGS, NOT THE PC'S AUTOCRLF.

REG-3364 gave every checkout LF (`* text=auto eol=lf`) and left this batch: a law that `git init`s its own
temp repo still inherits the runner's global core.autocrlf. Git for Windows (and GitHub's windows-latest)
installs with that set to true, so a fixture written as LF is rewritten as CR LF the next time Git touches
it, and a "\n" byte assertion goes red only on Windows. tv/git_quiet.pin_lf (and init_repo) pins
core.autocrlf=false on the throwaway repo after init, and wins over a Windows-default global. Every test
function that git-inits a throwaway repo must pin (pin_lf, init_repo, or `config core.autocrlf`). Measured
here against a global autocrlf=true, the same default the work ALT ships. The census walks the AST in a
child without the proof tracer, so a function-level trace of test_control.py cannot stall the prove.
RED_PROOF below.
"""
import ast
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import git_quiet  # noqa: E402

GIT = shutil.which("git")

_INIT_FLAGS = frozenset({"-q", "--bare", "-b", "--quiet"})
_PIN_NAMES = frozenset({"pin_lf", "init_repo"})
_CENSUS_ENV = "_REG3626_CENSUS"
_TRACE_ENV = ("PYTHONPATH", "HEART2_TRACE_LOG", "HEART2_TRACE_SITE", "HEART2_TRACE_ROOT",
              "TV_GATE_TRACE", "TV_GATE_TRACE_ROOT")


def _const_str(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _arg_values(node):
    out = []
    for a in list(node.args) + [kw.value for kw in node.keywords]:
        if isinstance(a, (ast.List, ast.Tuple)):
            out.extend(a.elts)
        elif isinstance(a, ast.BinOp) and isinstance(a.op, ast.Add):
            for side in (a.left, a.right):
                if isinstance(side, (ast.List, ast.Tuple)):
                    out.extend(side.elts)
                else:
                    out.append(side)
        else:
            out.append(a)
    return out


def _is_git_init_argv(strs):
    if "init" not in strs:
        return False
    if any(s in _INIT_FLAGS or s.startswith("init.") for s in strs):
        return True
    return "git" in strs


def _is_git_init(node):
    """true when this Call (or a list it builds) is `git init` of a repo, not an HTTP `init` field"""
    if isinstance(node, (ast.List, ast.Tuple)):
        strs = [s for s in (_const_str(x) for x in node.elts) if s is not None]
        return _is_git_init_argv(strs)
    if not isinstance(node, ast.Call):
        return False
    strs = [s for s in (_const_str(a) for a in _arg_values(node)) if s is not None]
    if _is_git_init_argv(strs):
        return True
    if "init" in strs and (
        (isinstance(node.func, ast.Name) and node.func.id in ("_git", "git", "g"))
        or (isinstance(node.func, ast.Attribute) and node.func.attr in ("_git", "git", "g", "run",
                                                                       "check_call", "Popen"))):
        return True
    return False


def _is_pin(node):
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    name = ""
    if isinstance(func, ast.Name):
        name = func.id
    elif isinstance(func, ast.Attribute):
        name = func.attr
    if name in _PIN_NAMES:
        return True
    strs = [s for s in (_const_str(a) for a in _arg_values(node)) if s is not None]
    return any("core.autocrlf" in s for s in strs)


def _unpinned_worker(root):
    """[(file, function, first_init_line)] - AST census, run in a child without the proof tracer."""
    # REG-3626 - every function that git-inits a throwaway repo must pin core.autocrlf
    found = []
    for name in sorted(os.listdir(root)):
        if not (name.startswith("test_") and name.endswith(".py")):
            continue
        path = os.path.join(root, name)
        with io.open(path, encoding="utf-8") as fh:
            src = fh.read()
        if "init" not in src:
            continue
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            inits, pins = [], []
            for node in ast.walk(fn):
                if _is_git_init(node):
                    inits.append(getattr(node, "lineno", fn.lineno))
                if _is_pin(node):
                    pins.append(getattr(node, "lineno", fn.lineno))
            if inits and not pins:
                found.append((name, fn.name, min(inits)))
    return found


def unpinned_temp_inits(root=HERE):
    """[(file, function, first_init_line)] for tv/test_*.py functions that git-init a throwaway repo and never pin."""
    if os.environ.get(_CENSUS_ENV) == "1":
        return _unpinned_worker(root)
    env = {k: v for k, v in os.environ.items() if k not in _TRACE_ENV}
    env[_CENSUS_ENV] = "1"
    prog = (
        "import json,sys;"
        "sys.path.insert(0, %r);"
        "import test_a_temp_repo_keeps_the_cases_line_endings as T;"
        "print(json.dumps(T.unpinned_temp_inits(%r)))"
    ) % (root, root)
    r = subprocess.run([sys.executable, "-c", prog], env=env, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError("the LF census child failed: %s" % ((r.stderr or r.stdout)[-400:]))
    rows = json.loads(r.stdout)
    return [tuple(x) for x in rows]


def _isolated_env(home):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(
        HOME=home,
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_GLOBAL=os.path.join(home, "gitconfig"),
        GIT_AUTHOR_NAME="law",
        GIT_AUTHOR_EMAIL="law@x",
        GIT_COMMITTER_NAME="law",
        GIT_COMMITTER_EMAIL="law@x",
    )
    return env


def _checkout_bytes(repo, env, pin):
    """init, write LF, add, commit, checkout, and return the working-tree bytes of f.txt"""
    if pin:
        r = git_quiet.init_repo(repo, "-b", "main", env=env, capture_output=True)
        if r.returncode != 0:
            raise AssertionError("init_repo failed: %s" % (r.stderr or b"")[-400:])
    else:
        r = git_quiet.run(["git", "init", "-q", "-b", "main", repo], env=env, capture_output=True)
        if r.returncode != 0:
            raise AssertionError("git init failed: %s" % (r.stderr or b"")[-400:])
    path = os.path.join(repo, "f.txt")
    with io.open(path, "wb") as fh:
        fh.write(b"hello\n")
    for args in (["git", "-C", repo, "add", "f.txt"],
                 ["git", "-C", repo, "commit", "-q", "-m", "seed"]):
        r = git_quiet.run(args, env=env, capture_output=True)
        if r.returncode != 0:
            raise AssertionError("%s failed: %s" % (args, (r.stderr or b"")[-400:]))
    os.remove(path)
    r = git_quiet.run(["git", "-C", repo, "checkout", "--", "f.txt"], env=env, capture_output=True)
    if r.returncode != 0:
        raise AssertionError("checkout failed: %s" % (r.stderr or b"")[-400:])
    with io.open(path, "rb") as fh:
        return fh.read()


def _reg3626_fixture_repo():
    """Source for the census only: heart2's sandbox does not carry the other laws, so this file
    holds one throwaway init the census can see. Never called."""
    _git("init", "-q")
    _git("config", "core.autocrlf", "false")  # REG-3626 fixture pin


class ATempRepoKeepsTheCasesLineEndings(unittest.TestCase):


    @unittest.skipUnless(GIT, "git is absent - the pin is UNMEASURED here, never a pass")
    def test_init_repo_keeps_lf_against_a_windows_default(self):
        """* THE POINT: a Windows-default global autocrlf cannot rewrite a fixture this law inits"""
        d = tempfile.mkdtemp(prefix="tvd_temp_eol_")
        try:
            home = os.path.join(d, "home")
            os.makedirs(home)
            with io.open(os.path.join(home, "gitconfig"), "w", encoding="utf-8") as fh:
                fh.write("[core]\nautocrlf = true\n")
            env = _isolated_env(home)
            unpinned, pinned = os.path.join(d, "unpinned"), os.path.join(d, "pinned")
            os.makedirs(unpinned)
            os.makedirs(pinned)
            self.assertEqual(_checkout_bytes(unpinned, env, pin=False), b"hello\r\n",
                             "the contrast no longer holds: a Windows-default repo kept LF without a pin")
            self.assertEqual(_checkout_bytes(pinned, env, pin=True), b"hello\n",
                             "init_repo did not keep LF against a Windows-default autocrlf")
        finally:
            shutil.rmtree(d, True)

    def test_every_temp_repo_init_in_a_law_is_pinned(self):
        """* THE POINT: a law that builds its own temp repo cannot inherit the runner's autocrlf"""
        leftover = unpinned_temp_inits()
        self.assertEqual(leftover, [],
                         "a law git-inits a throwaway repo without pinning LF: %s"
                         % "; ".join("%s:%s:%s" % row for row in leftover[:12]))


RED_PROOF = [
    {"why": "#107 - pin_lf writes the Windows default again, so a fixture checkout becomes CR LF",
     "file": "tv/git_quiet.py",
     "find": "    # REG-3626 pin value: the local repo, never the runner's default\n"
             "    return run([\"git\", \"-C\", os.fspath(repo), \"config\", \"core.autocrlf\", \"false\"], **kw)\n",
     "replace": "    # REG-3626 pin value: the local repo, never the runner's default\n"
                "    return run([\"git\", \"-C\", os.fspath(repo), \"config\", \"core.autocrlf\", \"true\"], **kw)\n",
     "matches": 1},
    {"why": "#107 - this law's own fixture init loses its pin, and the census does not refuse",
     "file": "tv/test_a_temp_repo_keeps_the_cases_line_endings.py",
     "find": "    _git(\"config\", \"core.autocrlf\", \"false\")  # REG-3626 fixture pin\n",
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
