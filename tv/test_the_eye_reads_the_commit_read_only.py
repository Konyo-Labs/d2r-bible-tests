# -*- coding: utf-8 -*-
"""#169 WIN 2 — THE SECOND EYE READS THE REVIEWED COMMIT'S FILES, READ-ONLY, AND ONLY THOSE.

His ruling, 2026-09-25: "forget this use the grok cli instead". The eye was run in an EMPTY folder on pasted text, so
it could not read one line of context around a hunk. It now gets the files the reviewed commit changed, exactly as they
stand AT that commit (`git archive`, never the live checkout - v3408: an agent pointed at the tree can edit it), every
entry read-only, and a prompt that names them and says not to look further. MEASURED the same day: given an open
folder, the CLI spent its whole 420 s budget exploring ("I'll measure ... Next I'll crop ...", rc=142) - the
instruction bounds it, the folder only makes the reading possible.

  · DRIVEN (a throwaway git repo): the snapshot holds the COMMIT's bytes, not the working tree's; a file over the size
    limit is left out and NAMED; a file the commit did not touch is absent; every entry is read-only.
  · DRIVEN: cleanup removes a read-only snapshot (a read-only directory cannot be unlinked without giving write back).
  · DRIVEN: the prompt note names the files, the skipped ones, and says not to open anything else.
  · JOINED: run_one hands the reviewed sha to ask().
RED_PROOF below.
"""
import inspect
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import second_eye_run as SE  # noqa: E402

GIT = shutil.which("git")


def _git(cwd, *args):
    return subprocess.run(["git"] + list(args), cwd=cwd, check=True, capture_output=True, text=True).stdout


@unittest.skipIf(GIT is None, "git is absent - this law is UNMEASURED, not passing")
class TheEyeReadsTheCommitReadOnly(unittest.TestCase):

    def setUp(self):
        self.repo = tempfile.mkdtemp(prefix="eye-repo-")
        self.addCleanup(shutil.rmtree, self.repo, True)
        _git(self.repo, "init", "-q")
        _git(self.repo, "config", "core.autocrlf", "false")  # #107 REG-3626 - the fixture's bytes, not the PC's git default
        _git(self.repo, "config", "user.email", "law@example.invalid")
        _git(self.repo, "config", "user.name", "law")
        with open(os.path.join(self.repo, "untouched.py"), "w") as fh:
            fh.write("A = 1\n")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-q", "-m", "base")
        os.makedirs(os.path.join(self.repo, "tv"))
        with open(os.path.join(self.repo, "tv", "small.py"), "w") as fh:
            fh.write("COMMITTED = True\n")
        with open(os.path.join(self.repo, "big.txt"), "w") as fh:
            fh.write("x" * 500)
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-q", "-m", "change")
        self.sha = _git(self.repo, "rev-parse", "HEAD").strip()
        with open(os.path.join(self.repo, "tv", "small.py"), "w") as fh:   # the LIVE tree moves on
            fh.write("WORKING_TREE = True\n")
        self.cwd = os.path.join(tempfile.gettempdir(), "eye-law-%d" % os.getpid())
        keep = (SE.REPO, SE.EYE_CWD, SE._EYE_CWD_IS_OURS)
        SE.REPO, SE.EYE_CWD, SE._EYE_CWD_IS_OURS = self.repo, self.cwd, True

        def restore():
            SE.eye_cwd_cleanup()
            if os.path.isdir(self.cwd):
                subprocess.run(["chmod", "-R", "u+w", self.cwd])
                shutil.rmtree(self.cwd, True)
            SE.REPO, SE.EYE_CWD, SE._EYE_CWD_IS_OURS = keep
        self.addCleanup(restore)

    def test_the_snapshot_holds_the_commit_and_only_it(self):
        snap = SE.eye_snapshot(self.sha, max_bytes=100)
        self.assertTrue(snap["ok"], snap)
        # REG-2016 (#259) - an over-limit file of the commit goes in as a NAMED excerpt of its changed blocks, not as nothing
        self.assertEqual(snap["included"], ["tv/small.py", "big.txt.EXCERPT.txt"])
        with open(os.path.join(self.cwd, "tv", "small.py")) as fh:
            self.assertEqual(fh.read(), "COMMITTED = True\n", "the eye read the live tree, not the commit")
        self.assertFalse(os.path.exists(os.path.join(self.cwd, "untouched.py")), "a file the commit never touched")
        self.assertTrue(any(s.startswith("big.txt") and "EXCERPT" in s for s in snap["skipped"]),
                        "an oversized file vanished unnamed, or its excerpt is not named beside it")

    def test_every_entry_is_read_only(self):
        SE.eye_snapshot(self.sha, max_bytes=100)
        f = os.path.join(self.cwd, "tv", "small.py")
        self.assertFalse(os.access(f, os.W_OK), "the eye can write the file it reviews")
        if os.name == "posix":   # v3886 (#107) - Windows' os.access ignores a folder's read-only mode; the file check above holds
            self.assertFalse(os.access(os.path.join(self.cwd, "tv"), os.W_OK), "the eye can add files beside it")

    def test_cleanup_removes_a_read_only_snapshot(self):
        SE.eye_snapshot(self.sha, max_bytes=100)
        self.assertTrue(SE.eye_cwd_cleanup())
        self.assertFalse(os.path.exists(self.cwd), "a read-only snapshot outlived its look")

    def test_the_prompt_names_the_files_and_bounds_the_eye(self):
        note = SE.snapshot_note(SE.eye_snapshot(self.sha, max_bytes=100))
        self.assertIn("tv/small.py", note)
        self.assertIn("big.txt", note)
        self.assertIn("Do NOT open anything else", note)
        self.assertEqual(SE.snapshot_note({"ok": False}), "", "a failed snapshot still promised a folder")

    def test_run_one_hands_the_sha_to_the_eye(self):
        self.assertIn("ask(prompt, sha=sha)", inspect.getsource(SE.run_one))
        self.assertIn("snapshot_note(eye_snapshot(sha))", inspect.getsource(SE.ask))


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {
        "why": "#169 Win 2 - the snapshot is writable again: the eye could edit the files it reviews",
        "file": "second_eye_run.py",
        "find": "                os.chmod(os.path.join(_root, _n), 0o444)\n",
        "replace": "                pass\n",
        "matches": 1,
    },
    {
        "why": "#169 Win 2 - an oversized file goes into the folder and stalls the look",
        "file": "second_eye_run.py",
        "find": "        if size > lim:\n",
        "replace": "        if False:\n",
        "matches": 1,
    },
    {
        "why": "#169 Win 2 - run_one stops handing the sha, so the eye is back in an empty folder",
        "file": "second_eye_run.py",
        "find": "    answer, reached, awhy, structured = ask(prompt, sha=sha)\n",
        "replace": "    answer, reached, awhy, structured = ask(prompt)\n",
        "matches": 1,
    },
    {
        "why": "#169 Win 2 - cleanup cannot remove a read-only snapshot, so one outlives every look",
        "file": "second_eye_run.py",
        "find": "                os.chmod(os.path.join(_root, _n), 0o700)\n",
        "replace": "                pass\n",
        "matches": 1,
    },
]
