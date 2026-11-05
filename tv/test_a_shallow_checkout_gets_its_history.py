# -*- coding: utf-8 -*-
"""v3861 - A SHALLOW INSTALL GETS ITS HISTORY ONCE, AND A NEW INSTALL IS NEVER SHALLOW.

install-tvd.ps1 cloned with `--depth 1`. MEASURED on the new Konyo · ALT (2026-11-04): `git rev-parse
--is-shallow-repository` = true and `rev-list --count HEAD` = 1, so `HEAD~1` was an unknown revision, the shallow guard
in test_tasks_ships_are_recorded skipped, and its five red-proofs filed BLIND on that PC - and one BLIND shuts every
lock. The installer now clones `--filter=blob:none` (full history, file bodies on demand), and a console that boots on
an older shallow install runs control_app.history_repair once: `remote.origin.promisor` + `partialclonefilter` and
`git fetch --unshallow --filter=blob:none` (4.8 s on the ALT, 7,185 commits, `git status` still clean).

Drives the REAL routine against a real bare origin and a real `--depth 1` clone built here. ⚠ GIT_* is scrubbed: under
the pre-push hook GIT_DIR points at the pushing repo, and a fetch run with it would act on that repo instead.
[[git-hook-leaks-git-dir-into-tests]]
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import control_app as CA  # noqa: E402

INSTALLER = os.path.join(HERE, "install-tvd.ps1")


def _env():
    e = dict((k, v) for k, v in os.environ.items() if not k.startswith("GIT_"))
    e.update(GIT_CONFIG_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0")
    return e


def _git(cwd, *args):
    r = subprocess.run(["git"] + list(args), cwd=cwd, capture_output=True, text=True, env=_env(), timeout=60)
    if r.returncode != 0:
        raise AssertionError("git %s failed: %s" % (" ".join(args), r.stderr.strip()))
    return r.stdout.strip()


def _run(argv, **kw):
    """the console's git runner, with this law's scrubbed environment"""
    kw.pop("creationflags", None)
    return subprocess.run(argv, env=_env(), **kw)


class AShallowCheckoutGetsItsHistory(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="shallow_law_")
        self.addCleanup(shutil.rmtree, self.d, True)
        src = os.path.join(self.d, "src")
        os.makedirs(src)
        _git(src, "init", "-q")
        _git(src, "config", "user.email", "law@example.invalid")
        _git(src, "config", "user.name", "law")
        _git(src, "config", "commit.gpgsign", "false")
        for i in range(3):
            io.open(os.path.join(src, "f.txt"), "w", encoding="utf-8").write("v%d\n" % i)
            _git(src, "add", "-A")
            _git(src, "commit", "-q", "-m", "c%d" % i)
        self.origin = os.path.join(self.d, "origin.git")
        _git(self.d, "clone", "-q", "--bare", src, self.origin)
        _git(self.origin, "config", "uploadpack.allowFilter", "true")
        self.work = os.path.join(self.d, "work")
        _git(self.d, "clone", "-q", "--depth", "1", "file://" + self.origin.replace(os.sep, "/"), self.work)

    def test_PREMISE_the_fixture_is_a_one_commit_shallow_clone(self):
        self.assertEqual(_git(self.work, "rev-parse", "--is-shallow-repository"), "true")
        self.assertEqual(_git(self.work, "rev-list", "--count", "HEAD"), "1")

    def test_the_repair_makes_it_full_history_and_says_so(self):
        out = CA.history_repair(repo=self.work, run=_run)
        self.assertTrue(out["repaired"], "a shallow checkout was left shallow: %r" % (out,))
        self.assertIs(out["shallow"], False)
        self.assertEqual(_git(self.work, "rev-list", "--count", "HEAD"), "3", "HEAD~1 is still unknown here")
        self.assertEqual(_git(self.work, "status", "--porcelain"), "", "the repair left the tree dirty")
        self.assertIn("full history", out["why"])

    def test_a_full_history_checkout_is_left_alone(self):
        CA.history_repair(repo=self.work, run=_run)
        again = CA.history_repair(repo=self.work, run=_run)
        self.assertIs(again["shallow"], False)
        self.assertFalse(again["repaired"], "a full checkout was 'repaired' again")
        self.assertIn("already", again["why"])

    def test_git_that_cannot_answer_is_unknown_never_fine(self):
        out = CA.history_repair(repo=os.path.join(self.d, "no-such-checkout"), run=_run)
        self.assertIsNone(out["shallow"], "a checkout git could not read was called shallow or not: %r" % (out,))
        self.assertFalse(out["repaired"])


class ANewInstallIsNeverShallow(unittest.TestCase):

    def test_the_installer_clones_full_history(self):
        with io.open(INSTALLER, encoding="utf-8-sig") as fh:
            code = [ln.split("#", 1)[0] for ln in fh.read().split("\n")]
        clones = [ln.strip() for ln in code if ln.strip().startswith("git clone ")]
        self.assertEqual(len(clones), 1, "PRINT THE DENOMINATOR: the installer's clone line was not found once: %r"
                         % (clones,))
        self.assertNotIn("--depth", clones[0], "the installer makes a shallow clone again: %s" % clones[0])
        self.assertIn("--filter=blob:none", clones[0])


RED_PROOF = [
    {"why": "v3861 - the repair never fetches the history: a shallow install stays one commit deep and five proofs "
            "file BLIND on it",
     "file": "tv/control_app.py",
     "find": "        r = _git_run([\"git\", \"fetch\", \"--quiet\", \"--unshallow\", \"--filter=blob:none\", \"origin\"],\n",
     "replace": "        r = _git_run([\"git\", \"rev-parse\", \"HEAD\"],\n",
     "matches": 1},
    {"why": "v3861 - the installer clones --depth 1 again",
     "file": "tv/install-tvd.ps1",
     "find": "  git clone --filter=blob:none $repoUrl $repoDir | Out-Null",
     "replace": "  git clone --depth 1 $repoUrl $repoDir | Out-Null",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
