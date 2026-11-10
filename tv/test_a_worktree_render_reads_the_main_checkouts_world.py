# -*- coding: utf-8 -*-
"""REG-2070 - A RENDER RUN IN A GIT WORKTREE READS THE MAIN CHECKOUT'S SMALL STATE, READ-ONLY.

render_check's sandbox copies his small state (sessions.jsonl and ten ledgers) from the tree it runs in. They are
gitignored, so a worktree carries none: every shelf target met an EMPTY world ("seeded film on 0 of 0 run(s)"), the
shelf grid never built, and river-strip / shelf-cards refused red "could not be ACTIVATED" - on v3627 AND on main's own
bytes rendered in a worktree, while the same bytes painted 20/20 and 29/29 once given a world (2026-10-08). A red that
the surface did not earn is how a working shelf gets "fixed". `_world_source` names the main checkout's tv/ when the
tree has no store, and the copy loop reads from it. Drives the shipped helper over a real temporary git repo + worktree.
"""
import os
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
import render_check  # noqa: E402


def _git(*a):
    subprocess.run(["git", "-c", "user.email=law@example.invalid", "-c", "user.name=law"] + list(a),
                   check=True, capture_output=True, text=True, timeout=30)


class AWorktreeRenderReadsTheMainCheckoutsWorld(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="rc-law-")
        self.main = os.path.join(self.root, "main")
        os.makedirs(os.path.join(self.main, "tv"))
        with open(os.path.join(self.main, "tv", "keep.txt"), "w") as f:
            f.write("x\n")
        _git("init", "-q", self.main)
        _git("-C", self.main, "config", "core.autocrlf", "false")  # #107 REG-3626 - the fixture's bytes, not the PC's git default
        _git("-C", self.main, "add", "tv/keep.txt")
        _git("-C", self.main, "commit", "-q", "-m", "seed")
        self.wt = os.path.join(self.root, "wt")
        _git("-C", self.main, "worktree", "add", "-q", "--detach", self.wt)

    def tearDown(self):
        shutil.rmtree(self.root, True)

    def _store(self, tv):
        with open(os.path.join(tv, "sessions.jsonl"), "w") as f:
            f.write('{"sessionId": "s1"}\n')

    def test_a_tree_with_its_own_store_reads_its_own(self):
        tv = os.path.join(self.main, "tv")
        self._store(tv)
        self.assertEqual(render_check._world_source(tv), (tv, ""))

    def test_a_worktree_reads_the_main_checkouts_store(self):
        self._store(os.path.join(self.main, "tv"))
        src, why = render_check._world_source(os.path.join(self.wt, "tv"))
        self.assertEqual(os.path.realpath(src), os.path.realpath(os.path.join(self.main, "tv")),
                         "a worktree rendered against an empty world although its main checkout has one: %r" % why)
        self.assertIn("read-only", why, "the run must say where its world came from: %r" % why)

    def test_no_store_anywhere_is_said_as_unknown(self):
        wt_tv = os.path.join(self.wt, "tv")
        src, why = render_check._world_source(wt_tv)
        self.assertEqual(src, wt_tv)
        self.assertIn("UNKNOWN rather than clean", why, "an empty world must say so: %r" % why)

    def test_a_tree_git_cannot_place_does_not_claim_its_main_checkout_was_asked(self):
        """REG-2092 (the v3624 second eye) - rev-parse's exit code was ignored, so a tree git could not place printed
        'no session store in this tree or its main checkout' although no main checkout was ever asked."""
        lone = os.path.join(self.root, "not-a-repo", "tv")
        os.makedirs(lone)
        src, why = render_check._world_source(lone)
        self.assertEqual(src, lone)
        self.assertIn("git could not name its main checkout (rev-parse exit", why,
                      "a tree git could not place must say git could not name a main checkout: %r" % why)
        self.assertNotIn("or its main checkout", why, "the reason claims a main checkout was asked: %r" % why)
        self.assertIn("UNKNOWN rather than clean", why)

    def test_the_sandbox_copy_loop_reads_the_named_world(self):
        with open(render_check.__file__.replace(".pyc", ".py"), encoding="utf-8") as f:
            src = f.read()
        self.assertEqual(src.count("    _wsrc, _wwhy = _world_source(HERE)\n"), 1, "the sandbox no longer asks where its world is")
        self.assertEqual(src.count("        _src = os.path.join(_wsrc, _n)\n"), 1,
                         "the copy loop reads the tree it runs in again, not the world _world_source named")


RED_PROOF = [
    {"why": "REG-2070 - a worktree renders against an empty world again (the main checkout's store is not consulted)",
     "file": "tv/render_check.py",
     "find": "        if os.path.realpath(main_tv) != os.path.realpath(here) and os.path.isfile(os.path.join(main_tv, \"sessions.jsonl\")):\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "REG-2070 - the copy loop ignores the named world and reads the tree it runs in",
     "file": "tv/render_check.py",
     "find": "        _src = os.path.join(_wsrc, _n)\n",
     "replace": "        _src = os.path.join(HERE, _n)\n",
     "matches": 1},
    {"why": "REG-2070 - a tree that carries its own store is sent elsewhere",
     "file": "tv/render_check.py",
     "find": "    if os.path.isfile(os.path.join(here, \"sessions.jsonl\")):\n        return here, \"\"\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-2092 - a failed rev-parse is read as 'no main checkout' again",
     "file": "tv/render_check.py",
     "find": "    if _g.returncode != 0 or not common:\n",
     "replace": "    if False:\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
