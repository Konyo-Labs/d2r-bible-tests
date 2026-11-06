# -*- coding: utf-8 -*-
"""#50 — THE GATES LOAD ON WINDOWS, SO EVERY PC CAN PROVE ITS OWN INSTRUMENTS (REG-1445).

2026-09-29, measured on the ALT at v3522 (562b1687, clean tree): `run_gates will not import: No module
named 'fcntl'`. heart2.gate_files() therefore saw ZERO gates on Windows, the gate fingerprint covered
heart2.py alone, and no Windows PC could ever write a census that speaks for its instruments. Every
self-arming lock stayed shut there - `reel.route` refused with "the heart has never run here" - so 76
reels sat at EMPTY and the river never reached TOMBSTONE. With fcntl stubbed the same tree lists 679
gates, so the only thing standing between a Windows PC and its own proof was one top-level import.

His ruling the same morning: every PC proves itself (a Mac proof does not speak for Windows - the
river-outlet law stayed GREEN through its own sabotage on the ALT while going red on the Mac).

DRIVEN: run_gates and heart2 imported in a child python where `import fcntl` RAISES, exactly as on
Windows; the msvcrt lock path driven with a recording msvcrt; an AST sweep over every tv/ module for a
bare top-level import of a Unix-only module. RED_PROOF below.
"""
import ast
import io
import os
import subprocess
import sys
import tempfile
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402  #171 — this run's scratch dirs leave with it
_fx_tmp.contain()
try:
    from console_safe import enable as _enable   # its messages carry non-ASCII; a cp1255 console crashes REPORTING them
    _enable()
except Exception:
    pass

#: Modules that exist on macOS/Linux and not on Windows. A bare top-level import of any of these makes
#: the importing module - and everything that imports IT - unloadable on every Windows PC.
UNIX_ONLY = ("fcntl", "termios", "pwd", "grp", "resource", "tty", "pty")

_CHILD = r'''
import os, sys
sys.modules["fcntl"] = None          # `import fcntl` now raises ImportError, exactly as on Windows
sys.path.insert(0, %(here)r)
os.chdir(%(here)r)
import run_gates
import heart2
n = len(heart2.gate_files(say=lambda *a, **k: None))
print("GATES", n)
print("FCNTL", run_gates.fcntl)
'''


class TheGatesLoadWithoutFcntl(unittest.TestCase):

    def test_run_gates_and_the_heart_import_where_fcntl_does_not_exist(self):
        fd, path = tempfile.mkstemp(suffix=".py", prefix="gates_on_windows_")
        try:
            with io.open(fd, "w", encoding="utf-8") as fh:
                fh.write(_CHILD % {"here": HERE})
            r = subprocess.run([sys.executable, path], capture_output=True, text=True, timeout=180)
        finally:
            os.unlink(path)
        self.assertEqual(r.returncode, 0,
                         "run_gates/heart2 would not import where fcntl is absent (every Windows PC):\n%s"
                         % (r.stderr or r.stdout)[-900:])
        got = [ln for ln in r.stdout.splitlines() if ln.startswith("GATES ")]
        self.assertTrue(got, "the child printed no gate count: %r" % r.stdout[-400:])
        n = int(got[0].split()[1])
        self.assertGreater(n, 100, "the heart saw only %d gate(s) without fcntl - a Windows PC would "
                                   "prove next to nothing and call it a census" % n)
        self.assertIn("FCNTL None", r.stdout, "PREMISE: the child did not actually run without fcntl")


class _RecordingMsvcrt(types.ModuleType):
    LK_NBLCK = 2

    def __init__(self, refuse=False):
        types.ModuleType.__init__(self, "msvcrt")
        self.calls = []
        self.refuse = refuse

    def locking(self, fd, mode, nbytes):
        self.calls.append((os.lseek(fd, 0, os.SEEK_CUR), mode, nbytes))
        if self.refuse:
            raise OSError(36, "Resource deadlock avoided")


class TheWindowsLockLeavesTheHolderReadable(unittest.TestCase):

    def setUp(self):
        import run_gates
        self.rg = run_gates
        self._saved = (run_gates.fcntl, run_gates.msvcrt, run_gates._LOCK_FH)
        run_gates.fcntl = None
        self.env_saved = os.environ.get("D2R_GATE_LOCK_KEY")
        os.environ["D2R_GATE_LOCK_KEY"] = os.path.join(tempfile.gettempdir(),
                                                       "d2r_win_lock_law_%d" % os.getpid())

    def tearDown(self):
        fh = self.rg._LOCK_FH
        self.rg.fcntl, self.rg.msvcrt, self.rg._LOCK_FH = self._saved
        if fh is not None and fh is not self._saved[2]:
            try:
                fh.close()
            except Exception:
                pass
        if self.env_saved is None:
            os.environ.pop("D2R_GATE_LOCK_KEY", None)
        else:
            os.environ["D2R_GATE_LOCK_KEY"] = self.env_saved

    def test_the_lock_is_taken_through_msvcrt_past_the_text(self):
        fake = _RecordingMsvcrt()
        self.rg.msvcrt = fake
        self.assertIsNone(self.rg._claim_the_tree(), "a lone run was refused on the msvcrt path")
        self.assertEqual(len(fake.calls), 1, "msvcrt.locking was not asked for the tree lock")
        at, mode, n = fake.calls[0]
        self.assertEqual(mode, fake.LK_NBLCK, "the Windows lock BLOCKS - a second run would hang, not refuse")
        self.assertGreaterEqual(at, 1 << 20,
                                "the Windows lock sits on the holder's own text (offset %d): a refused run "
                                "could not read who holds the tree" % at)
        self.rg._LOCK_FH.seek(0)
        self.assertIn("pid %d" % os.getpid(), self.rg._LOCK_FH.read(),
                      "the holder did not write its line after taking the lock")

    def test_a_held_tree_is_refused_and_names_the_holder(self):
        path = os.path.join(tempfile.gettempdir(), "d2r_gates_%s.lock" % __import__("re").sub(
            r"[^A-Za-z0-9]+", "_", os.environ["D2R_GATE_LOCK_KEY"]).strip("_")[-80:])
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write("pid 4242, started 2026-09-29 10:50:00, tree X\n")
        self.rg.msvcrt = _RecordingMsvcrt(refuse=True)
        try:
            why = self.rg._claim_the_tree()
        finally:
            os.unlink(path)
        self.assertIsNotNone(why, "a tree another run holds was NOT refused on Windows")
        self.assertIn("pid 4242", why, "the refusal did not name who holds the tree: %r" % why)


class TheSandboxGetsItsNeedsWithoutCp(unittest.TestCase):
    """REG-1448 - heart2 brought PROOF_NEEDS across with `cp -c -R`, which does not exist on Windows, so no
    sandbox there carried `.git` and `test_eye_declares_reach` read BLIND on the ALT. Driven OFF the Mac
    (sys.platform patched) on a real temporary repository."""

    def _git(self, cwd, *a):
        return subprocess.run(["git"] + list(a), cwd=cwd, capture_output=True, text=True, timeout=60)

    def setUp(self):
        import heart2
        self.h2 = heart2
        self.root = tempfile.mkdtemp(prefix="bring_across_")
        self.repo = os.path.join(self.root, "repo")
        os.makedirs(self.repo)
        self._git(self.repo, "init", "-q")
        for k, v in (("user.email", "law@x"), ("user.name", "law")):
            self._git(self.repo, "config", k, v)
        io.open(os.path.join(self.repo, "a.txt"), "w").write("a\n")
        self._git(self.repo, "add", "a.txt")
        self._git(self.repo, "commit", "-qm", "v9999 the law's commit")
        self.head = self._git(self.repo, "rev-parse", "HEAD").stdout.strip()
        self.box = os.path.join(self.root, "box")
        os.makedirs(self.box)
        self.said = []

    def _bring(self, src, dst, need):
        from unittest import mock
        with mock.patch.object(self.h2.sys, "platform", "win32"):
            self.h2._bring_across(src, dst, need, lambda *a, **k: self.said.append(" ".join(map(str, a))))

    def test_the_git_history_arrives_and_the_real_repo_cannot_be_written(self):
        self._bring(os.path.join(self.repo, ".git"), os.path.join(self.box, ".git"), "../.git")
        log = self._git(self.box, "log", "--format=%s").stdout
        self.assertIn("v9999 the law's commit", log, "the sandbox has no git history off the Mac: %r %r"
                      % (log, self.said))
        self.assertIn("a.txt", self._git(self.box, "ls-files").stdout, "the sandbox index is empty - "
                      "`git ls-files` laws would read nothing")
        self.assertTrue(os.path.isfile(os.path.join(self.box, ".git", "objects", "info", "alternates")),
                        "the history was COPIED, not borrowed - on his repo that is 1.8 GB per sandbox")
        io.open(os.path.join(self.box, "b.txt"), "w").write("b\n")
        self._git(self.box, "add", "b.txt")
        self._git(self.box, "-c", "user.email=l@x", "-c", "user.name=l", "commit", "-qm", "sandbox")
        self.assertEqual(self._git(self.repo, "rev-parse", "HEAD").stdout.strip(), self.head,
                         "a commit INSIDE the sandbox moved the real repository's HEAD")
        self.assertNotIn("b.txt", self._git(self.repo, "ls-files").stdout, "the sandbox wrote the real index")

    def test_a_file_is_copied_and_an_oversize_need_is_refused(self):
        src = os.path.join(self.root, "spec.ts")
        io.open(src, "w").write("x" * 10)
        self._bring(src, os.path.join(self.box, "spec.ts"), "../tests/spec.ts")
        self.assertTrue(os.path.isfile(os.path.join(self.box, "spec.ts")), "a small need was not copied")
        from unittest import mock
        with mock.patch.object(self.h2, "_NEED_COPY_MAX_FILE", 5):
            self._bring(src, os.path.join(self.box, "big.ts"), "big")
        self.assertFalse(os.path.exists(os.path.join(self.box, "big.ts")), "an oversize need was copied")
        self.assertTrue(any("too large" in x for x in self.said), "the refusal said nothing")


class ABrowserIsFoundOnWindows(unittest.TestCase):
    """REG-1457 - render_check._find_chrome knew his Mac, Playwright's cache and Linux names, and NO Windows
    path: every law that renders a page SKIPPED on the ALT and a proof whose laws all skipped read BLIND
    (test_mask_encoders_agree[3], 8 of 12). Driven as Windows with fake install folders."""

    def _find(self, present, env_extra=None):
        import render_check as RC
        from unittest import mock
        root = tempfile.mkdtemp(prefix="find_chrome_")
        env = {"PROGRAMFILES": os.path.join(root, "pf"), "PROGRAMFILES(X86)": os.path.join(root, "pf86"),
               "LOCALAPPDATA": os.path.join(root, "lad")}
        env.update(env_extra or {})
        for rel in present:
            f = os.path.join(root, rel)
            os.makedirs(os.path.dirname(f), exist_ok=True)
            io.open(f, "w").write("x")
        real_exists = os.path.exists
        mac = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        with mock.patch.object(RC.os, "name", "nt"), mock.patch.dict(os.environ, env, clear=False), \
                mock.patch.object(RC.os.path, "exists", lambda p: False if p == mac else real_exists(p)):
            os.environ.pop("TV_CHROME", None) if "TV_CHROME" not in (env_extra or {}) else None
            return RC._find_chrome(), root

    def test_edge_is_found_when_chrome_is_not(self):
        got, root = self._find([os.path.join("pf86", "Microsoft", "Edge", "Application", "msedge.exe")])
        self.assertTrue(got.endswith("msedge.exe") and got.startswith(root),
                        "Windows Edge was not found - every rendering law skips on a Windows PC: %r" % got)

    def test_chrome_wins_over_edge(self):
        got, _ = self._find([os.path.join("pf", "Google", "Chrome", "Application", "chrome.exe"),
                             os.path.join("pf86", "Microsoft", "Edge", "Application", "msedge.exe")])
        self.assertTrue(got.endswith("chrome.exe"), got)


class NoModuleImportsAUnixOnlyModuleBare(unittest.TestCase):

    def test_every_top_level_unix_only_import_is_guarded(self):
        bad = []
        for name in sorted(os.listdir(HERE)):
            if not name.endswith(".py") or name.startswith("test_"):
                continue
            try:
                tree = ast.parse(io.open(os.path.join(HERE, name), encoding="utf-8").read())
            except (SyntaxError, UnicodeDecodeError):
                continue
            for node in tree.body:               # TOP LEVEL only: a guarded one sits inside a Try
                mods = []
                if isinstance(node, ast.Import):
                    mods = [a.name.split(".")[0] for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    mods = [node.module.split(".")[0]]
                for m in mods:
                    if m in UNIX_ONLY:
                        bad.append("%s:%d import %s" % (name, node.lineno, m))
        self.assertEqual(bad, [], "a bare top-level import of a Unix-only module makes these unloadable "
                                  "on every Windows PC - guard it with try/except ImportError:\n  %s"
                                  % "\n  ".join(bad))


class TheSimulatorsPopenCanBeSubclassed(unittest.TestCase):
    """REG-1451 - ci_sim replaced subprocess.Popen with a plain FUNCTION. On Windows `asyncio.windows_utils`
    runs `class Popen(subprocess.Popen)` on first import (unittest.mock imports asyncio), so the simulator
    died with "function() argument 'code' must be code, not str" on every Windows PC. Driven in a child
    python so the interception never leaks into this process."""

    def test_after_the_stub_a_module_may_still_subclass_popen(self):
        code = ("import sys, subprocess; sys.path.insert(0, %r)\n"
                "import ci_sim\n"
                "ci_sim._install_path_interception(False)\n"
                "assert getattr(subprocess.Popen, '_ci_sim_path_stub', False), 'PREMISE: not installed'\n"
                "class Sub(subprocess.Popen):\n    pass\n"
                "p = Sub([sys.executable, '-c', 'pass']); p.wait()\n"
                "print('SUBCLASS-OK', p.returncode)\n" % HERE)
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120,
                           encoding="utf-8", errors="replace")
        self.assertIn("SUBCLASS-OK 0", r.stdout,
                      "after ci_sim's interception, subclassing subprocess.Popen fails - asyncio does exactly "
                      "that on Windows:\n%s" % (r.stderr or r.stdout)[-600:])


class EveryModuleCompilesWithoutAWarning(unittest.TestCase):
    """#50 (REG-1450) - control_app.py held an invalid escape (`\\s` in a docstring). On Python 3.12 - the
    ALT's - that compiles with a SyntaxWarning printed to stderr, so EVERY child process that imports the
    console carried a warning line in its output, and a law that reads that output (the simulator's
    'reach:' line) failed on Windows and passed on his Mac's 3.9, where it is a silent DeprecationWarning.
    A later Python makes it an error. Four production modules had one; this keeps it at zero."""

    def test_no_production_module_compiles_with_a_warning(self):
        import warnings
        bad = []
        for name in sorted(os.listdir(HERE)):
            if not name.endswith(".py") or name.startswith("test_"):
                continue
            try:
                src = io.open(os.path.join(HERE, name), encoding="utf-8").read()
            except UnicodeDecodeError:
                continue
            with warnings.catch_warnings():
                warnings.simplefilter("error")
                try:
                    compile(src, name, "exec")
                except SyntaxError as e:
                    bad.append("%s:%s %s" % (name, e.lineno, e.msg))
                except (DeprecationWarning, SyntaxWarning) as e:
                    bad.append("%s %s" % (name, e))
        self.assertEqual(bad, [], "these compile with a warning (an error on a later Python, and noise in "
                                  "every child's output on 3.12):\n  %s" % "\n  ".join(bad))


RED_PROOF = [
    {
        "why": "2026-09-29 - the browser finder has no Windows path again, so every rendering law skips into BLIND (REG-1457)",
        "file": "tv/render_check.py",
        "find": "    if os.name == \"nt\":\n        _bases = [",
        "replace": "    if False:\n        _bases = [",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - ci_sim's Popen stub is a plain function again, and asyncio cannot subclass it on Windows",
        "file": "tv/ci_sim.py",
        "find": "        class Popen(_REAL_IO[\"Popen\"]):\n",
        "replace": "        class Popen(object):\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - control_app's docstring carries an invalid escape again (REG-1450)",
        "file": "tv/control_app.py",
        "find": "This folded `/(?:Users|home)/[^/\\\\s]+`,",
        "replace": "This folded `/(?:Users|home)/[^/\\s]+`,",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - off the Mac the sandbox gets no git history again (REG-1448): BLIND on every Windows PC",
        "file": "tv/heart2.py",
        "find": "    if os.path.basename(os.path.normpath(src)) == \".git\" and os.path.isdir(src):\n",
        "replace": "    if False:\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - the sandbox's git index is left empty, so ls-files laws read nothing",
        "file": "tv/heart2.py",
        "find": "        _gq.run([\"git\", \"read-tree\", \"HEAD\"], cwd=os.path.dirname(dst),\n",
        "replace": "        _gq.run([\"git\", \"--version\"], cwd=os.path.dirname(dst),\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - run_gates imports fcntl bare again: no Windows PC can load its gates or prove itself",
        "file": "tv/run_gates.py",
        "find": "try:\n    import fcntl\nexcept ImportError:  # Windows\n    fcntl = None\n",
        "replace": "import fcntl\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - the Windows lock sits on byte 0, so a refused run cannot read who holds the tree",
        "file": "tv/run_gates.py",
        "find": "        os.lseek(fd, 1 << 30, os.SEEK_SET)\n",
        "replace": "        os.lseek(fd, 0, os.SEEK_SET)\n",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
