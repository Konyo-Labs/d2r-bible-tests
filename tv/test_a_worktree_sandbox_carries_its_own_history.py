# -*- coding: utf-8 -*-
"""REG-2364 — A SANDBOX BUILT FROM A WORKTREE CARRIES A HISTORY OF ITS OWN, AND NO DOOR BACK TO THE REAL REPO.

⚠ WHAT IT COST. heart2 proves a law in a sandbox: a copy of tv/ plus what the gates declare in PROOF_NEEDS, and
`../.git` is declared, so every sandbox carries a git history. From his MAIN checkout `.git` is a directory and comes
across as a private clone. From a LINKED WORKTREE - where every push now starts - `.git` is a one-line pointer into the
real repo, and make_sandbox rightly refuses to copy a pointer (a door), so the sandbox had NO history at all. Nobody
saw it, because git exports GIT_DIR into a pre-push hook from a worktree (MEASURED on git 2.50: from a worktree
GIT_DIR=<main>/.git/worktrees/<name>, from the main checkout none) and the hook passed it on: every git call a law made
in the sandbox answered from - and could write - the real worktree. REG-2360 made the hook unset it. MEASURED on that
branch, a sandbox from the worktree answered `git rev-parse HEAD` with "not a git repository": test_control's
relaunch case (TestV2153) ERRORED, so its clean run is red and a push that proves test_control is refused; and the
version-stamp law's red-proof [7] went BLIND, because its only catcher (RoutineIOnRealHistory) skips without history.

THE FIX (heart2._share_history, called by make_sandbox for a pointer and off the Mac for a directory): a private
`git clone --shared --no-checkout` of that checkout - HEAD is the worktree's HEAD, the objects are borrowed read-only
through alternates, the refs, index and config are the sandbox's own - made with no GIT_* variable in its environment
(a leaked GIT_DIR made its `read-tree HEAD` rewrite the REAL worktree's index, MEASURED on a fixture), and with the
clone's push url pointed at nothing, because its origin IS the real checkout.

REG-2396 / REG-2397 (the cross-family review of Push A2, 2026-10-22). The history was the sandbox's own; the LAW RUNS
were not. heart2 dropped GIT_* in 2 routines (5 of its 9 spawn calls): _run_gate_once copied the prover's environment
whole into every law it ran, and its own key questions (`git -C REPO ...`, `ls-files`) ran under whatever the caller
held - and a leaked GIT_DIR beats -C. So a prove started by an OLD hook (a push runs the hook file in his MAIN checkout, the one
origin/main had) or by hand inside one ran every law against the real repo and keyed proofs on another tree's files.
Now every process heart2 starts takes its environment from ONE helper, run_gates.git_free_env - EVERY GIT_*, not git's
--local-env-vars - which run_gates.law_env applies to every gate run, and suite_verdict, shard_suite and gate_ledger use
it for the suites and the git questions they start. And a Mac sandbox of the MAIN checkout, an APFS copy of its whole
.git, kept HIS remotes - origin is GitHub, the PUBLIC repo - so every remote's push is shut there too (_shut_push, one
routine with the clone's).

These cases build a FIXTURE - a main repo and a linked worktree one commit ahead, with a staged entry in the worktree's
index - and drive heart2.make_sandbox for real with heart2.REPO pointed at it, the registered gates' own declarations,
and GIT_DIR=<the worktree's git dir> in the prover's environment, exactly as a hook leaks it. They read the history in
the sandbox the way the two casualties do (`git -C <root> rev-parse HEAD`, `git cat-file -e <old commit>`), then try
every write a law could make in there and require the fixture to be byte-for-byte what it was.
[[feedback-fixtures-never-touch-live-data]] [[the-unjoined-end]] RED_PROOF below.
"""
import ast
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import warnings

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()       # these print non-ASCII; a cp1255 console must not crash while REPORTING
except Exception:
    pass
import heart2       # noqa: E402

#: the history every sandbox is handed, as the gates declare it (relative to tv/)
HISTORY_NEED = "../.git"
#: REG-2396 - every module that starts a law run or asks git about a tree. Each spawn passes env=, and none builds an
#: environment from os.environ by hand - so every one comes from run_gates.git_free_env. Literal names: the heart keys
#: this law on their bytes.
SPAWNERS = ("heart2.py", "suite_verdict.py", "shard_suite.py", "gate_ledger.py")
#: REG-2396 - a fixture law: what git and the environment look like from inside a law run, written beside itself. A
#: plain script, not a unittest module: its text sits inside this file, and test_folder_scans reads every column-0 main
#: guard in a suite as that suite's own (a guard line here put every class below it "after unittest.main()").
PROBE = "t_reads_its_own_git.py"
_PROBE_SRC = u'''# -*- coding: utf-8 -*-
"""fixture law (REG-2396): what a law run sees of git and of its environment, written to seen.json beside itself"""
import json, os, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
_ID = ["-c", "user.name=probe", "-c", "user.email=probe@example.invalid", "-c", "commit.gpgsign=false"]


def _git(*a):
    r = subprocess.run(["git"] + _ID + list(a), cwd=HERE, capture_output=True, text=True)
    return [r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()[-200:]]


seen = {"git": sorted(k for k in os.environ if k.upper().startswith("GIT_")),
        "pushed": [os.environ.get("TV_PUSHED_GIT_DIR"), os.environ.get("TV_PUSHED_COMMIT")],
        "gitDir": _git("rev-parse", "--absolute-git-dir"),
        "head": _git("rev-parse", "HEAD"),
        "commit": _git("commit", "-q", "--allow-empty", "-m", "a law's own commit"),
        "bare": _git("config", "core.bare", "true")}
with open(os.path.join(HERE, "seen.json"), "w") as fh:
    json.dump(seen, fh)
'''
_IDENT = ["-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid", "-c", "commit.gpgsign=false",
          "-c", "init.defaultBranch=main"]


def _clean_env(**extra):
    """os.environ without one GIT_* variable, plus `extra`, and never his global or system git config. -> dict"""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT="0")
    env.update(extra)
    return env


def _run_git(*args):
    """-> CompletedProcess of a fixture-side git call, whatever its exit"""
    return subprocess.run(["git"] + _IDENT + list(args), capture_output=True, text=True, timeout=120,
                          encoding="utf-8", errors="replace", env=_clean_env())


def _git(*args):
    r = _run_git(*args)
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
    """A repo standing in for HIS: a main checkout with tv/control_app.py (make_sandbox requires it), two commits, and a
    linked worktree one commit ahead with a STAGED entry in its index - the state a build must never disturb.
    remotes=True (REG-2397): two bare repos stand in for GitHub as its `origin` and a `mirror`, main pushed to both."""

    def __init__(self, root, remotes=False):
        self.main = os.path.join(root, "main")
        self.wt = os.path.join(root, "wt")
        self.remotes = {}
        os.makedirs(os.path.join(self.main, "tv"))
        _git("init", "-q", self.main)
        _git("-C", self.main, "config", "core.autocrlf", "false")  # #107 REG-3626 - the fixture's bytes, not the PC's git default
        with io.open(os.path.join(self.main, "tv", "control_app.py"), "w", encoding="utf-8") as fh:
            fh.write(u"# fixture\n")
        _git("-C", self.main, "add", "-A")
        _git("-C", self.main, "commit", "-q", "-m", "the first commit")
        self.first = _git("-C", self.main, "rev-parse", "HEAD")
        _git("-C", self.main, "commit", "-q", "--allow-empty", "-m", "main's second commit")
        self.main_head = _git("-C", self.main, "rev-parse", "HEAD")
        _git("-C", self.main, "worktree", "add", "-q", self.wt, "-b", "wtb")
        _git("-C", self.wt, "commit", "-q", "--allow-empty", "-m", "the worktree's own commit")
        self.wt_head = _git("-C", self.wt, "rev-parse", "HEAD")
        with io.open(os.path.join(self.wt, "staged.txt"), "w", encoding="utf-8") as fh:
            fh.write(u"staged, not committed\n")
        _git("-C", self.wt, "add", "staged.txt")
        self.gitdir = os.path.realpath(_git("-C", self.wt, "rev-parse", "--absolute-git-dir"))
        self.common = os.path.join(self.main, ".git")
        for name in (("origin", "mirror") if remotes else ()):
            self.remotes[name] = os.path.join(root, name + ".git")
            _git("init", "-q", "--bare", self.remotes[name])
            _git("-C", self.remotes[name], "config", "core.autocrlf", "false")  # #107 REG-3626 - the fixture's bytes, not the PC's git default
            _git("-C", self.main, "remote", "add", name, self.remotes[name])
            _git("-C", self.main, "push", "-q", name, "main")

    def remote_refs(self):
        """every ref of every stand-in remote - a push from anywhere shows here. -> {name: for-each-ref}"""
        return {n: _git("-C", d, "for-each-ref", "--format=%(refname) %(objectname)") for n, d in self.remotes.items()}

    def state(self):
        """Every write a git call could make into the real repo shows here - its refs (a pushed branch, a moved one),
        its objects, both HEADs, both indexes (the staged entry), the common config and core.bare - asked of git and
        read by name, never by listing a directory (a law that lists one cannot be keyed)."""
        return {
            "refs": _git("-C", self.main, "for-each-ref", "--format=%(refname) %(objectname)"),
            "objects": _git("-C", self.main, "count-objects", "-v"),
            "worktrees": _git("-C", self.main, "worktree", "list", "--porcelain"),
            "HEAD": _sha(os.path.join(self.common, "HEAD")),
            "wtHEAD": _sha(os.path.join(self.gitdir, "HEAD")),
            "config": _sha(os.path.join(self.common, "config")),
            "packed-refs": _sha(os.path.join(self.common, "packed-refs")),
            "index": _sha(os.path.join(self.common, "index")),
            "wtIndex": _sha(os.path.join(self.gitdir, "index")),
            "bare": _git("-C", self.main, "config", "--get", "core.bare"),
        }


_DECLARING = []


def _declaring():
    """The registered gates whose PROOF_NEEDS names the history, by absolute path (heart2 resolves a bare gate name
    against REPO, which build() points at the fixture). Read once, after setUp has taken every GIT_* away. -> list"""
    if not _DECLARING:
        with warnings.catch_warnings():     # other gate files' own escape sequences are not this law's finding
            warnings.simplefilter("ignore")
            for n, fn in heart2.gate_files(say=lambda *a, **k: None):
                fn = fn if os.path.isabs(fn) else os.path.join(HERE, fn)
                if HISTORY_NEED in (heart2.proof_needs_in(fn) or []):
                    _DECLARING.append((n, fn))
    return list(_DECLARING)


class _Case(unittest.TestCase):

    def setUp(self):
        # this law builds repos too: under a hook's leak its own fixture git calls must not reach the real one
        _gitenv = {_k: os.environ.pop(_k) for _k in list(os.environ) if _k.startswith("GIT_")}
        self.addCleanup(os.environ.update, _gitenv)
        self.root = tempfile.mkdtemp(prefix="wt_history_")
        self.addCleanup(heart2._rmtree_hard, self.root)
        self.declaring = _declaring()

    def build(self, repo, leak=None):
        """heart2.make_sandbox for real, with REPO = `repo`, the registered gates that declare the history, and
        GIT_DIR=`leak` in the prover's environment. -> (sandbox repo dir, said lines); dropped when the test ends."""
        said = []
        real = (heart2.REPO, heart2.gate_files)
        heart2.REPO = repo
        heart2.gate_files = lambda say=None: list(self.declaring)
        if leak:
            os.environ["GIT_DIR"] = leak
        try:
            tv, root = heart2.make_sandbox(say=lambda *a, **k: said.append(" ".join(str(x) for x in a)))
        finally:
            os.environ.pop("GIT_DIR", None)
            heart2.REPO, heart2.gate_files = real
        self.assertIsNotNone(root, "PREMISE: the fixture sandbox was not built: %s" % said)
        self.addCleanup(heart2._drop_sandbox, root)
        return os.path.dirname(tv), said


class AWorktreeSandboxReadsItsOwnHistory(_Case):

    def test_the_gates_still_hand_every_sandbox_the_history(self):
        """the premise both casualties stand on: neither declares the history itself - TestV2153 and
        RoutineIOnRealHistory read it because another registered gate's PROOF_NEEDS brings it into every sandbox"""
        self.assertTrue(self.declaring,
                        "no registered gate declares PROOF_NEEDS %r any more, so NO sandbox carries a git history: "
                        "test_control's relaunch case errors on `git rev-parse HEAD` and the version-stamp law's "
                        "red-proof [7] goes BLIND - declare it where it is read" % HISTORY_NEED)

    def test_a_sandbox_from_a_worktree_answers_from_the_worktrees_history(self):
        """★ the blocker: from a linked worktree, under the hook's leaked GIT_DIR, the sandbox reads that worktree's
        HEAD and its whole history - through a git dir of its own, never the pointer"""
        fx = _Fixture(self.root)
        sbx, said = self.build(fx.wt, leak=fx.gitdir)
        dotgit = os.path.join(sbx, ".git")
        self.assertTrue(os.path.isdir(dotgit),
                        "a sandbox built from a worktree holds no git history of its own (%s) - every law that reads "
                        "HEAD there errors or skips once the hook stops leaking GIT_DIR: %s"
                        % ("a pointer FILE: a door to the real worktree" if os.path.isfile(dotgit) else "none", said))
        r = _run_git("-C", sbx, "rev-parse", "HEAD")      # TestV2153's read, from the sandbox root
        self.assertEqual((r.returncode, (r.stdout or "").strip()), (0, fx.wt_head),
                         "`git rev-parse HEAD` in the sandbox did not answer the worktree's HEAD: %r" % (r.stderr,))
        self.assertEqual(_run_git("-C", os.path.join(sbx, "tv"), "cat-file", "-e", fx.first + "^{commit}").returncode,
                         0, "an old commit is not readable in the sandbox - RoutineIOnRealHistory skips, its proof "
                            "goes BLIND")
        gd = os.path.realpath(_git("-C", sbx, "rev-parse", "--absolute-git-dir"))
        self.assertEqual(gd, os.path.realpath(dotgit), "the sandbox's git calls answer from another git dir: %s" % gd)
        cd = os.path.realpath(os.path.join(sbx, _git("-C", sbx, "rev-parse", "--git-common-dir")))
        self.assertEqual(cd, os.path.realpath(dotgit), "the sandbox's refs live outside it: %s" % cd)
        self.assertIn("tv/control_app.py", _git("-C", sbx, "ls-files").split("\n"),
                      "the sandbox's index is empty - `git ls-files` laws read nothing")
        self.assertTrue(os.path.isfile(os.path.join(dotgit, "objects", "info", "alternates")),
                        "the history was COPIED, not borrowed - on his repo that is gigabytes per sandbox")
        self.assertFalse(os.path.exists(dotgit + ".shared"), "the clone's scratch dir was left in the sandbox")

    def test_a_sandbox_from_the_main_checkout_still_carries_its_history(self):
        """BASELINE: a `.git` directory comes across as before, at the main checkout's HEAD - the case tells the two
        shapes apart and the old one is untouched"""
        fx = _Fixture(self.root)
        sbx, said = self.build(fx.main)
        self.assertTrue(os.path.isdir(os.path.join(sbx, ".git")), "a main checkout's sandbox has no history: %s" % said)
        self.assertEqual(_git("-C", sbx, "rev-parse", "HEAD"), fx.main_head,
                         "the main checkout's sandbox answers some other HEAD")
        self.assertFalse(any("worktree POINTER" in l for l in said),
                         "a .git DIRECTORY was handled as a worktree pointer: %s" % said)


class NothingRunInTheSandboxReachesTheRealRepo(_Case):

    def test_a_push_from_a_main_checkout_sandbox_reaches_no_remote(self):
        """REG-2397: a sandbox of the MAIN checkout carries a copy of its whole .git on the Mac (an APFS clone), its
        remotes included - origin is GitHub. A commit and a push to EVERY remote made inside it fail, and both stand-in
        remotes and the real repo are what they were (off the Mac the history is a private clone; the same holds)"""
        fx = _Fixture(self.root, remotes=True)
        before, remote_before = fx.state(), fx.remote_refs()
        sbx, said = self.build(fx.main)
        self.assertEqual(_git("-C", sbx, "rev-parse", "HEAD"), fx.main_head,
                         "PREMISE: the main checkout's sandbox holds no history of its own: %s" % said)
        _git("-C", sbx, "commit", "-q", "--allow-empty", "-m", "made inside the sandbox")
        pushed = [n for n in sorted(fx.remotes)
                  if _run_git("-C", sbx, "push", n, "HEAD:refs/heads/from-the-sandbox").returncode == 0]
        self.assertEqual(pushed, [], "a push from the main checkout's sandbox reached %s - on his Mac that is GitHub, "
                                     "the PUBLIC repo" % pushed)
        self.assertEqual(fx.remote_refs(), remote_before, "a push from the sandbox wrote a remote")
        after = fx.state()
        self.assertEqual(sorted(k for k in before if before[k] != after[k]), [],
                         "a write made INSIDE the sandbox reached the real repo")

    def test_building_it_and_writing_in_it_leave_the_real_repo_byte_identical(self):
        """★ no door: the build itself (under the leaked GIT_DIR), then a commit, a push to origin and core.bare=true
        made INSIDE the sandbox - and the real repo (refs, objects, both HEADs, both indexes with the staged entry, the
        common config) is what it was, and the push failed"""
        fx = _Fixture(self.root)
        before = fx.state()
        self.assertEqual(before["bare"], "false", "PREMISE: the fixture repo starts bare")
        sbx, said = self.build(fx.wt, leak=fx.gitdir)
        self.assertEqual(_run_git("-C", sbx, "rev-parse", "HEAD").returncode, 0,
                         "PREMISE: the sandbox holds no history, so nothing below wrote through it: %s" % said)
        built = fx.state()
        self.assertEqual(sorted(k for k in before if before[k] != built[k]), [],
                         "BUILDING the sandbox wrote the real repo (a leaked GIT_DIR reached a git call)")
        _git("-C", sbx, "commit", "-q", "--allow-empty", "-m", "made inside the sandbox")
        push = _run_git("-C", sbx, "push", "origin", "HEAD:refs/heads/from-the-sandbox")
        _git("-C", sbx, "config", "core.bare", "true")
        after = fx.state()
        moved = sorted(k for k in before if before[k] != after[k])
        self.assertEqual(moved, [], "a write made INSIDE the sandbox reached the real repo (%s moved; core.bare is "
                                    "now %s) - in a push that is his live checkout" % (", ".join(moved), after["bare"]))
        self.assertNotEqual(push.returncode, 0, "a push from the sandbox to its origin - the real checkout - "
                                                "succeeded: %s" % (push.stderr or "").strip()[-300:])


class ALawRunNeverInheritsTheCallersGitDir(_Case):
    """REG-2396 - heart2 dropped GIT_* in 2 routines (5 of its 9 spawn calls): the law runs and its own key questions
    inherited the caller's environment. Driven with the caller's git variables in the prover's OWN environment, as an old hook (or a
    shell inside one) hands them over."""

    def _leak(self, fx, **more):
        """the caller's git variables in THIS process's environment until the test ends. -> dict"""
        leak = dict({"GIT_DIR": fx.gitdir, "GIT_INDEX_FILE": os.path.join(fx.gitdir, "index"),
                     "GIT_CONFIG_PARAMETERS": "'user.name'='leaked'", "GIT_NAMESPACE": "leaked"}, **more)
        os.environ.update(leak)
        self.addCleanup(lambda: [os.environ.pop(k, None) for k in leak])
        return leak

    def test_a_law_run_in_the_sandbox_reads_its_own_history_never_the_callers(self):
        """★ a fixture law that asks git for its git dir and HEAD, then commits and sets core.bare=true, run by
        heart2._run_gate_once in a worktree's sandbox while the prover holds the caller's GIT_DIR, GIT_INDEX_FILE,
        GIT_CONFIG_PARAMETERS and GIT_NAMESPACE: it sees no GIT_* variable, answers from the sandbox's own git dir and
        the worktree's HEAD, its writes land there, and the real repo is byte-for-byte what it was. TV_PUSHED_GIT_DIR
        and TV_PUSHED_COMMIT - the commit-stamps law's handle on the pushed commit - still reach it."""
        fx = _Fixture(self.root)
        before = fx.state()
        sbx, said = self.build(fx.wt, leak=fx.gitdir)
        tv = os.path.join(sbx, "tv")
        with io.open(os.path.join(tv, PROBE), "w", encoding="utf-8") as fh:
            fh.write(_PROBE_SRC)
        self._leak(fx, TV_PUSHED_GIT_DIR="/the/pushed/git/dir", TV_PUSHED_COMMIT="c0ffee")
        ok, tail = heart2._run_gate_once(tv, PROBE, timeout=120)
        try:
            with io.open(os.path.join(tv, "seen.json"), encoding="utf-8") as fh:
                seen = json.load(fh)
        except (OSError, ValueError):
            self.fail("PREMISE: the fixture law wrote nothing - the run did not happen: %s" % tail)
        self.assertEqual(seen["git"], [], "a law run inherited the caller's git variables: %s" % seen["git"])
        self.assertEqual(seen["pushed"], ["/the/pushed/git/dir", "c0ffee"],
                         "the commit-stamps law's TV_PUSHED_* handle did not reach the law run")
        self.assertEqual(os.path.realpath(seen["gitDir"][1]), os.path.realpath(os.path.join(sbx, ".git")),
                         "the law's `git rev-parse --absolute-git-dir` answered another repo's git dir: %r" % seen["gitDir"])
        self.assertEqual(seen["head"][1], fx.wt_head, "the law read some other HEAD: %r" % (seen["head"],))
        after = fx.state()
        self.assertEqual(sorted(k for k in before if before[k] != after[k]), [],
                         "a law run wrote the real repo through the caller's GIT_DIR (%s moved; core.bare is now %s)"
                         % (", ".join(k for k in before if before[k] != after[k]), after["bare"]))
        self.assertEqual(seen["commit"][0], 0, "PREMISE: the law's own commit failed, so no write was tried: %r"
                         % (seen["commit"],))
        self.assertTrue(ok, "the fixture law itself went red: %s" % tail)

    def test_heart2s_own_git_questions_answer_for_its_tree_not_a_leaked_one(self):
        """heart2 asks git about the tree it proves - `git -C REPO ...` (_git: the push base, the changed files) and
        `ls-files` (_tracked_files: the key's named-file half). A leaked GIT_DIR beats -C, so under the worktree's
        pointer both answered the WORKTREE's HEAD and index for the main checkout"""
        fx = _Fixture(self.root)
        self._leak(fx)
        real = heart2.REPO
        heart2.REPO = fx.main
        try:
            ok, head = heart2._git("rev-parse", "HEAD")
        finally:
            heart2.REPO = real
        self.assertEqual((ok, head.strip()), (True, fx.main_head),
                         "heart2's git question about its repo was answered by the leaked GIT_DIR's (HEAD %r)" % head)
        tracked = heart2._tracked_files(fx.main)
        self.assertIsNotNone(tracked, "git could not list the fixture's tracked files at all")
        self.assertIn("tv/control_app.py", tracked, "PREMISE: the main checkout's own file is not listed")
        self.assertNotIn("staged.txt", tracked, "the key's tracked-file list came from the worktree's index (the leaked "
                                                "GIT_INDEX_FILE / GIT_DIR) - a proof keyed on another tree's files")

    def test_every_gate_run_drops_every_git_variable_and_keeps_the_pushed_commit(self):
        """run_gates.law_env - the one door every gate run passes, in run_gates and in heart2 - drops EVERY GIT_* (not
        only git's list: GIT_NAMESPACE, a push's `git -c`, a name spelled in mixed case as Windows may) and keeps
        TV_PUSHED_GIT_DIR, TV_PUSHED_COMMIT and the rest; the caller's dict is left as it was"""
        import run_gates as RG
        base = {"GIT_DIR": "/r/.git/worktrees/w", "GIT_WORK_TREE": "/r", "GIT_INDEX_FILE": "/r/i",
                "GIT_COMMON_DIR": "/r/.git", "GIT_NAMESPACE": "n", "GIT_CONFIG_PARAMETERS": "'a.b'='c'",
                "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "a.b", "GIT_CONFIG_VALUE_0": "c", "Git_Dir": "/mixed",
                "TV_PUSHED_GIT_DIR": "/r/.git", "TV_PUSHED_COMMIT": "c0ffee", "PATH": "/bin", "TV_CONTROL_PORT": "17972"}
        kept = dict(base)
        for needs_app in (False, True):
            env = RG.law_env(needs_app, base)
            self.assertEqual(sorted(k for k in env if k.upper().startswith("GIT_")), [],
                             "a gate run (needs_app=%s) inherits git variables" % needs_app)
            for k in ("TV_PUSHED_GIT_DIR", "TV_PUSHED_COMMIT", "TV_CONTROL_PORT"):
                self.assertEqual(env.get(k), base[k], "law_env dropped %s" % k)
            # REG-2569 puts the refusing `claude` first on PATH; the caller's PATH must follow it, whole
            self.assertEqual(env.get("PATH"), os.path.join(os.path.dirname(os.path.abspath(RG.__file__)), "no_claude_bin")
                             + os.pathsep + base["PATH"], "law_env changed PATH beyond the refusing claude: %r" % env.get("PATH"))
        self.assertEqual(base, kept, "law_env changed the caller's environment")

    def test_every_process_these_modules_start_gets_its_environment_from_the_one_helper(self):
        """the spawn points, read: in heart2, suite_verdict, shard_suite and gate_ledger every subprocess call passes
        env=, and none of them builds an environment from os.environ by hand - so each comes from git_free_env (the
        two the review found stripped were hand-built; the nine it found unstripped passed no env at all)"""
        def _environ(n):
            return (isinstance(n, ast.Attribute) and n.attr == "environ" and isinstance(n.value, ast.Name)
                    and n.value.id == "os")
        bad = []
        for fname in SPAWNERS:
            with io.open(os.path.join(HERE, fname), encoding="utf-8") as fh:
                tree = ast.parse(fh.read())
            spawns = 0
            for node in ast.walk(tree):
                if isinstance(node, (ast.DictComp, ast.Call)):
                    gens = getattr(node, "generators", None) or []
                    if any(isinstance(g.iter, ast.Call) and isinstance(g.iter.func, ast.Attribute)
                           and g.iter.func.attr == "items" and _environ(g.iter.func.value) for g in gens):
                        bad.append("%s:%d builds an environment from os.environ.items()" % (fname, node.lineno))
                if not isinstance(node, ast.Call):
                    continue
                f = node.func
                if isinstance(f, ast.Name) and f.id == "dict" and node.args and any(
                        _environ(x) for x in ast.walk(node.args[0])):
                    bad.append("%s:%d dict(os.environ ...)" % (fname, node.lineno))
                if isinstance(f, ast.Attribute) and f.attr == "copy" and _environ(f.value):
                    bad.append("%s:%d os.environ.copy()" % (fname, node.lineno))
                if (isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == "subprocess"
                        and f.attr in ("run", "Popen", "call", "check_call", "check_output")):
                    spawns += 1
                    if not any(k.arg == "env" for k in node.keywords):
                        bad.append("%s:%d subprocess.%s inherits the caller's environment" % (fname, node.lineno, f.attr))
            self.assertGreater(spawns, 0, "PREMISE: %s starts no process any more - the list is stale" % fname)
        self.assertEqual(bad, [], "a spawn point that is not the one helper:\n  " + "\n  ".join(bad))


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {
        "why": "REG-2364 - a worktree's sandbox gets no history again: once the hook stops leaking GIT_DIR, "
               "TestV2153 errors and the version-stamp law's [7] goes BLIND",
        "file": "heart2.py",
        "find": "            if ((_dg + os.sep).startswith(os.path.normpath(dest) + os.sep)\n"
                "                    and _share_history(os.path.dirname(_s), _dg, say)):\n",
        "replace": "            if False:\n",
        "matches": 1,
    },
    {
        "why": "REG-2364 - the sandbox history's push url is left on its remote (a clone's origin is the real checkout): "
               "a push from the sandbox writes the real repo's refs",
        "file": "heart2.py",
        "find": "\"remote.%s.pushurl\" % name,",
        "replace": "\"sandbox.%s.note\" % name,",
        "matches": 1,
    },
    {
        "why": "REG-2364 - the sandbox history is built with the prover's GIT_* variables: under a hook's leaked "
               "GIT_DIR its read-tree rewrites the real worktree's index and its config the real common config",
        "file": "heart2.py",
        "find": "    env = _git_free_env(GIT_OPTIONAL_LOCKS=\"0\")\n    tmp = dst + \".shared\"\n",
        "replace": "    env = dict(os.environ, GIT_OPTIONAL_LOCKS=\"0\")\n    tmp = dst + \".shared\"\n",
        "matches": 1,
    },
    {
        "why": "REG-2364 - the 'fix' that copies the worktree's .git POINTER into the sandbox: history again, through "
               "a door to the real worktree",
        "file": "heart2.py",
        "find": "        if os.path.isfile(_s) and os.path.basename(_s) == \".git\":\n",
        "replace": "        if False:\n",
        "matches": 1,
    },
    {
        "why": "REG-2396 - the ONE helper keeps every GIT_* variable: every law run heart2 and run_gates start, and "
               "heart2's own key questions, inherit the caller's GIT_DIR again",
        "file": "run_gates.py",
        "find": "if not str(k).upper().startswith(\"GIT_\")}\n",
        "replace": "if not str(k).upper().startswith(\"_HEART2_TAMPERED_\")}\n",
        "matches": 1,
    },
    {
        "why": "REG-2396 - run_gates.law_env copies its base whole again: every gate run_gates and CI start inherits "
               "the caller's GIT_DIR",
        "file": "run_gates.py",
        "find": "    env = git_free_env(base)\n",
        "replace": "    env = dict(os.environ if base is None else base)\n",
        "matches": 1,
    },
    {
        "why": "REG-2396 - heart2's key question `git -C <tree> ls-files` runs under the caller's GIT_DIR again: the "
               "key lists another tree's files",
        "file": "heart2.py",
        "find": "\"ls-files\", \"-z\"], capture_output=True, timeout=30, env=_git_free_env())\n",
        "replace": "\"ls-files\", \"-z\"], capture_output=True, timeout=30)\n",
        "matches": 1,
    },
    {
        "why": "REG-2396 - heart2's `git -C REPO ...` question (the push base, the changed files) runs under the "
               "caller's GIT_DIR again: it answers for the leaked repo's HEAD",
        "file": "heart2.py",
        "find": "                           timeout=30, env=_git_free_env())\n",
        "replace": "                           timeout=30)\n",
        "matches": 1,
    },
    {
        "why": "REG-2396 - a law run starts from a copy of the caller's whole environment again (the review's :1944)",
        "file": "heart2.py",
        "find": "    env = _git_free_env()                      # REG-2396 - a law run never inherits the caller's GIT_DIR\n",
        "replace": "    env = dict(os.environ)\n",
        "matches": 1,
    },
    {
        "why": "REG-2397 - the Mac's copy of the main checkout's .git keeps HIS remotes' push open: a push from the "
               "sandbox goes to GitHub, the PUBLIC repo",
        "file": "heart2.py",
        "find": "            if not _shut_push(dst, say):\n                _rmtree_hard(dst)\n"
                "                say(\"  the sandbox's copy of %r",
        "replace": "            if False:\n                _rmtree_hard(dst)\n"
                   "                say(\"  the sandbox's copy of %r",
        "matches": 1,
        "needs": "macos",
    },
]
