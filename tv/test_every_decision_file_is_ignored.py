# -*- coding: utf-8 -*-
"""EVERY RUNTIME DECISION FILE IS IGNORED BY GIT — the name is read out of the code, not listed by hand.

`control_app._decision_path(name)` mints a per-machine DECISION record (his answers, the eagle's last look, the
auto-relaunch switch). This repo is PUBLIC. On 2026-09-25 his first answer to a console question sat in an untracked
`tv/his_answers.json` one `git add -A` away from being published: #223 added the store and no ignore line. .gitignore
records the same slip three times before (v2413, v2428, the auto_relaunch sweep), each fixed by listing an instance.

  · DRIVEN: every `_decision_path("<name>")` literal in control_app.py, primary AND scratch form, is asked of
    `git check-ignore` - the real matcher, not a re-implementation of it.
  · PREMISE: the code still names decision files (a zero here would be a law that checks nothing).
  · REG-2518: every git it runs goes through _git, which hands git an environment with no GIT_* in it. Inside a git
    hook GIT_DIR names the REAL repo and beats cwd=: this law's `git init` of its throwaway re-initialised the real
    repo's common config as bare (core.bare=true), the REG-2392 class, measured on a stand-in repo.
RED_PROOF below.
"""
import os
import sys
import re
import shutil
import subprocess
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
ROOT = os.path.dirname(HERE)
GIT = shutil.which("git")


def _names():
    with open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
        src = fh.read()
    return sorted(set(re.findall(r'_decision_path\(\s*"([^"]+)"\s*\)', src)))


#: #148 — tracked ON PURPOSE (.gitignore says why). REG-2461: none left. Its one entry was the console's slowest-request
#: record, which the running console rewrote on every PC; that record is per-PC now (.status_worst.here.json) and is
#: checked below like every other file the console mints at the state root.
TRACKED_ON_PURPOSE = {}


def _no_host(d):
    """-c value that points core.excludesFile at a file that does not exist, so no PC's global ignore answers for
    the tree (a host rule would keep this law green with the tree's own line deleted)."""
    return "core.excludesFile=" + os.path.join(d, "no-host-excludes")


def _state_root_names():
    """#148 — every file control_app mints as os.path.join(_fixture_root_for_state(), "<name>"). The decision-path
    reader above could not see these, and shadow_seals.jsonl, .view_request.json and runaway_dumps.txt were not ignored."""
    with open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
        src = fh.read()
    return sorted(set(re.findall(r'os\.path\.join\(\s*_fixture_root_for_state\(\)\s*,\s*"([^"]+)"\s*\)', src)))


def _log_root_names():
    """REG-2167 — every file control_app mints as os.path.join(_log_root(), "<name>").
    The state-root reader above does not see _log_root. The roster receipt used that
    form and sat untracked, one git add away from the public repo."""
    with open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
        src = fh.read()
    return sorted(set(re.findall(r'os\.path\.join\(\s*_log_root\(\)\s*,\s*"([^"]+)"\s*\)', src)))


def _git_env():
    """REG-2518 - the environment this law hands git: os.environ without one GIT_* variable. -> dict"""
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def _git(args, cwd=None, **kw):
    """Every git this law runs. -> subprocess.CompletedProcess

    ⚠ REG-2518 - INSIDE A GIT HOOK, GIT_DIR NAMES THE REAL REPO AND BEATS cwd=. A push from a linked worktree exports
    GIT_DIR=<main>/.git/worktrees/<name>, and this law's `git init -q <tmp>` then re-initialised the MAIN checkout's
    common config with core.bare=true (every git command there refuses: "this operation must be run in a work tree"),
    while its check-ignore answered for the real repo - and the law still printed OK. Measured on a stand-in repo, the
    REG-2392 class. So git gets no GIT_* at all, and one that is still there refuses HERE, before git runs: a broken
    scrub turns this law red without touching any repo."""
    env = _git_env()
    leaked = sorted(k for k in env if k.startswith("GIT_"))
    if leaked:
        raise AssertionError("this law would hand git %s - a hook's GIT_DIR beats cwd= and writes whichever repo it "
                             "names; refused before git ran (REG-2518)" % ", ".join(leaked))
    return subprocess.run([GIT] + list(args), cwd=cwd, env=env, **kw)


def _ignored(rels):
    """-> the subset of rels git's real matcher would NOT ignore, asked of a throwaway repo seeded with the tree's own
    .gitignore files (a proof sandbox is not a git work tree)."""
    d = tempfile.mkdtemp(prefix="decision-ignore-")
    try:
        _git(["init", "-q", d], check=True)
        _git(["-C", d, "config", "core.autocrlf", "false"], check=True)  # #107 REG-3626 - the fixture's bytes, not the PC's git default
        os.makedirs(os.path.join(d, "tv"))
        for rel in (".gitignore", os.path.join("tv", ".gitignore")):
            if os.path.isfile(os.path.join(ROOT, rel)):
                shutil.copyfile(os.path.join(ROOT, rel), os.path.join(d, rel))
        return [rel for rel in rels
                if _git(["-c", _no_host(d), "check-ignore", "-q", "--no-index", rel], cwd=d).returncode != 0]
    finally:
        shutil.rmtree(d, True)


@unittest.skipIf(GIT is None, "git is absent - this law is UNMEASURED, not passing")
class EveryDecisionFileIsIgnored(unittest.TestCase):

    def test_the_code_still_names_decision_files(self):
        self.assertGreaterEqual(len(_names()), 3, "fewer decision files than exist today - the reader broke")

    def test_each_one_is_ignored_in_both_forms(self):
        # ⚠ A THROWAWAY REPO SEEDED WITH THE TREE'S OWN .gitignore FILES (_ignored), so the answer comes from git's
        # real matcher and does not depend on this copy being a git work tree (a proof sandbox is not).
        rels = []
        for n in _names():
            stem, ext = os.path.splitext(n)
            rels += ["tv/" + n, "tv/%s.scratch-17999%s" % (stem, ext)]
        missing = _ignored(rels)
        self.assertEqual(missing, [], "runtime decision files git would publish: %s" % missing)

    def test_a_hooks_git_dir_never_reaches_git(self):
        """REG-2518 - GIT_DIR planted at a throwaway checkout's linked worktree, exactly what a pre-push hook exports
        for a push from a worktree: this law's own git leaves that checkout as it was, and answers from its own
        throwaway repo rather than the one GIT_DIR names."""
        d = tempfile.mkdtemp(prefix="decision-ignore-leak-")
        self.addCleanup(shutil.rmtree, d, True)
        main, wt = os.path.join(d, "main"), os.path.join(d, "wt")
        fixture = ["-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid", "-c", "commit.gpgsign=false",
                   "-c", "init.defaultBranch=main", "-c", "core.hooksPath=" + os.path.join(d, "no-hooks")]
        _git(fixture + ["init", "-q", main], check=True)
        _git(fixture + ["-C", main, "config", "core.autocrlf", "false"], check=True)  # #107 REG-3626 - the fixture's bytes, not the PC's git default
        with open(os.path.join(main, "f.txt"), "w", encoding="utf-8") as fh:
            fh.write("one\n")
        _git(fixture + ["-C", main, "add", "f.txt"], check=True)
        _git(fixture + ["-C", main, "commit", "-q", "-m", "one"], check=True)
        _git(fixture + ["-C", main, "worktree", "add", "-q", wt, "-b", "wtb"], check=True)
        planted = _git(["-C", wt, "rev-parse", "--absolute-git-dir"], capture_output=True, text=True,
                       check=True).stdout.strip()

        def bare():
            return _git(["-C", main, "config", "--get", "core.bare"], capture_output=True, text=True).stdout.strip()
        self.assertEqual(bare(), "false", "the stand-in checkout was not a work tree to begin with")
        saved = {k: os.environ.pop(k) for k in list(os.environ) if k.startswith("GIT_")}
        self.addCleanup(os.environ.update, saved)
        os.environ["GIT_DIR"] = planted
        try:
            got = _ignored(["tv/.tvd_roster.json", "tv/not-a-decision-file.txt"])
        finally:
            os.environ.pop("GIT_DIR", None)
        self.assertEqual(bare(), "false", "this law's throwaway `git init` re-initialised the repo GIT_DIR names as "
                                          "bare (REG-2518, the REG-2392 class)")
        self.assertEqual(got, ["tv/not-a-decision-file.txt"],
                         "git answered for the repo GIT_DIR names, not for this law's own throwaway")

    def test_every_git_call_goes_through_the_scrub(self):
        """REG-2518 - one door: a subprocess call that does not go through _git would carry a hook's GIT_DIR again."""
        import ast
        with open(os.path.abspath(__file__), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        calls = []
        for fn in ast.walk(tree):
            if not isinstance(fn, ast.FunctionDef):
                continue
            for node in ast.walk(fn):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and isinstance(node.func.value, ast.Name) and node.func.value.id == "subprocess"):
                    calls.append((fn.name, node.func.attr, sorted(k.arg for k in node.keywords if k.arg)))
        self.assertEqual(calls, [("_git", "run", ["cwd", "env"])],
                         "a subprocess call in this law does not go through _git's scrubbed environment: %r" % calls)

    def test_the_code_still_mints_files_at_the_state_root(self):
        self.assertGreaterEqual(len(_state_root_names()), 10, "the state-root reader found almost nothing - it broke")
        self.assertIn("shadow_seals.jsonl", _state_root_names())

    def test_every_state_root_file_is_ignored_or_kept_on_purpose(self):
        rels = ["tv/" + n for n in _state_root_names() if n not in TRACKED_ON_PURPOSE]
        rels += ["tv/shadow_seals.jsonl.1"]   # its rollover, minted by os.replace(path, path + ".1")
        self.assertEqual(_ignored(rels), [], "runtime files the console mints that git would publish")

    def test_every_log_root_file_is_ignored(self):
        names = _log_root_names()
        self.assertIn(".tvd_roster.json", names)
        self.assertIn(".tvd_beacon.json", names)
        self.assertIn("control_agent.log", names)
        rels = ["tv/" + n for n in names]
        rels.append("tv/.tvd_roster.json.tmp")  # _roster_state_save writes path + ".tmp"
        rels.append("tv/roster_book.json.tmp")  # _roster_book_take writes path + ".tmp"
        rels.append("tv/roster_cache/Konyo__Mac.json")
        rels.append("tv/.tvd_roster_fetch.json.tmp")
        self.assertIn("roster_cache", names)
        self.assertIn(".tvd_roster_fetch.json", names)
        self.assertEqual(_ignored(rels), [], "log-root files git would publish: %s" % _ignored(rels))


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {
        "why": "REG-2518 - git gets the inherited environment again, so a hook's GIT_DIR reaches this law's throwaway "
               "`git init` (it re-initialised the real repo as bare); the refusal before git runs is what turns it red",
        "file": "test_every_decision_file_is_ignored.py",
        "find": "    return {k: v for k, v in os.environ.items() if not k.startswith(\"GIT_\")}\n",
        "replace": "    return dict(os.environ)\n",
        "matches": 1,
    },
    {
        "why": "REG-2518 - a git call that skips the scrubbed door: a harmless stand-in for the bypass, so the proof itself "
               "never hands a hook's GIT_DIR to git",
        "file": "test_every_decision_file_is_ignored.py",
        "find": "    def test_the_code_still_names_decision_files(self):\n",
        "replace": "    def test_the_code_still_names_decision_files(self):\n        subprocess.run([sys.executable, \"-c\", \"pass\"])\n",
        "matches": 1,
    },
    {
        "why": "#148 - the shadow door's open/close record is trackable again - one `git add -A` publishes his hours",
        "file": "../.gitignore",
        "find": "\ntv/shadow_seals.jsonl\n",
        "replace": "\n",
        "matches": 1,
    },
    {
        "why": "his answers store is trackable again - one `git add -A` publishes his rulings to a public repo",
        "file": "../.gitignore",
        "find": "\ntv/his_answers.json\n",
        "replace": "\n",
        "matches": 1,
    },
    {
        "why": "REG-2167 - the roster receipt is trackable again",
        "file": "../.gitignore",
        "find": "\ntv/.tvd_roster.json\n",
        "replace": "\n",
        "matches": 1,
    },
    {
        "why": "REG-2167 - the roster receipt temp file is trackable again",
        "file": "../.gitignore",
        "find": "\ntv/.tvd_roster.json.tmp\n",
        "replace": "\n",
        "matches": 1,
    },
    {
        "why": "REG-2169 - the roster fetch cache is trackable again",
        "file": "../.gitignore",
        "find": "\ntv/roster_cache\n",
        "replace": "\n",
        "matches": 1,
    },
    {
        "why": "REG-2169 - the roster fetch receipt is trackable again",
        "file": "../.gitignore",
        "find": "\ntv/.tvd_roster_fetch.json\n",
        "replace": "\n",
        "matches": 1,
    },
]
