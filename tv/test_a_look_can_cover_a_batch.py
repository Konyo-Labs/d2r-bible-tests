# -*- coding: utf-8 -*-
"""2026-09-27 — A BATCH BUILT ON AN INTEGRATION BRANCH SHIPPED CODE NO EYE COULD BE SHOWN.

v3515-v3517 were built in worktrees, merged, then stamped as three bump-only commits. The runner looks at the
ONE commit a version is bound to, so v3517's look was 2,692 chars of version strings and the eye answered
cannot-tell - correctly - and re-asking could only answer the same. The v3518 push was then refused at the
gate for a look no re-ask could ever supply.

`second_eye_run.py vNNNN --base REV` widens the look to every change from REV to the bound commit, the prompt
says the diff spans N commits, and the row says what it covered. Measured on v3517: 2,692 -> 460,877 raw diff
chars (shared into the 26,000 cap across the changed files), and the eye came back with 6 findings, one of them
a real regression (a key stack locked no longer; reproduced and fixed in v3519).

DRIVEN on a throwaway git repo (never this one - CI checks out one commit deep): feature, then a bump-only stamp.
RED_PROOF below.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402  #171 — this run's scratch dirs leave with it
_fx_tmp.contain()

try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import second_eye_run as SER  # noqa: E402


def _git(repo, *args):
    return subprocess.check_output(["git"] + list(args), cwd=repo,
                                   env=dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                                            GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")).decode().strip()


class ALookCanCoverABatch(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.repo = tempfile.mkdtemp(prefix="eye_batch_")
        r = cls.repo
        _git(r, "init", "-q")
        _git(r, "config", "core.autocrlf", "false")  # #107 REG-3626 - the fixture's bytes, not the PC's git default
        os.makedirs(os.path.join(r, "tv"))
        with open(os.path.join(r, "tv", "feature.py"), "w") as fh:
            fh.write("def base():\n    return 1\n")
        with open(os.path.join(r, "tv", "stamp.py"), "w") as fh:
            fh.write('VERSION = "v1"\n')
        _git(r, "add", "-A")
        _git(r, "commit", "-q", "-m", "v1: base")
        cls.base = _git(r, "rev-parse", "HEAD")
        with open(os.path.join(r, "tv", "feature.py"), "a") as fh:
            fh.write("\n\ndef the_real_change(stack):\n    return stack.strip().lower() == 'key'\n")
        _git(r, "commit", "-q", "-am", "feat: the real change")
        with open(os.path.join(r, "tv", "stamp.py"), "w") as fh:
            fh.write('VERSION = "v2"\n')
        _git(r, "commit", "-q", "-am", "v2: stamp")
        cls.bump = _git(r, "rev-parse", "HEAD")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.repo, ignore_errors=True)

    def setUp(self):
        self._saved = (SER.REPO, SER.REVIEW_BASE)
        SER.REPO = self.repo

    def tearDown(self):
        SER.REPO, SER.REVIEW_BASE = self._saved

    def test_premise_the_bound_commit_alone_carries_only_the_stamp(self):
        SER.REVIEW_BASE = None
        prompt = SER.payload_for(self.bump)[0]
        self.assertIn("stamp.py", prompt)
        self.assertNotIn("the_real_change", prompt, "premise: the bump commit already carried the feature")

    def test_a_base_widens_the_look_to_the_batch_and_says_so(self):
        SER.REVIEW_BASE = self.base
        prompt, dropped = SER.payload_for(self.bump)[:2]
        self.assertIn("the_real_change", prompt, "the widened look still shows only the bound commit")
        self.assertIn("THIS DIFF SPANS 2 COMMITS", prompt, "the eye is not told the diff spans the batch")
        self.assertIn("covers %s..%s (2 commits)" % (self.base[:8], self.bump[:8]), dropped,
                      "the row does not say what the look covered")

    def test_a_batch_that_was_not_cut_is_never_called_truncated(self):
        """REG-1739 - the batch label shared the truncation flag, so every --base look told the eye "IT IS ALSO
        TRUNCATED" with nothing cut, and the v3561 eye answered cannot-tell from that false warning."""
        from unittest import mock
        SER.REVIEW_BASE = self.base
        with mock.patch.dict(os.environ, {"SECOND_EYE_MAX_CHARS": "1000000"}):
            prompt = SER.payload_for(self.bump)[0]
        self.assertIn("SPANS", prompt, "PREMISE: this is not a batch look")
        self.assertNotIn("ALSO TRUNCATED", prompt, "a payload that was not cut told the eye it was truncated")
        with mock.patch.dict(os.environ, {"SECOND_EYE_MAX_CHARS": "120"}):
            cut = SER.payload_for(self.bump)[0]
        self.assertIn("ALSO TRUNCATED", cut, "PREMISE: a payload that WAS cut no longer says so")

    def test_every_changed_file_of_the_batch_is_on_the_roster(self):
        SER.REVIEW_BASE = self.base
        absent, why = SER.absent_from(self.bump, "")
        self.assertEqual(sorted(absent), ["tv/feature.py", "tv/stamp.py"],
                         "the missing-file roster still lists only the bound commit's files: %r %s" % (absent, why))

    def test_a_base_that_is_not_an_ancestor_is_never_asked(self):
        """DRIVEN through run_one: v9001 is bound to the FIRST commit and the base is the LAST, so the range is
        empty and "covers base..sha" would be a false claim. It must refuse before building anything."""
        with open(os.path.join(self.repo, "TASKS.md"), "w") as fh:
            fh.write("| **v9001** | `%s` | v9001 - base |\n| **v9002** | `%s` | v9002 - stamp |\n"
                     % (self.base[:8], self.bump[:8]))
        try:
            SER.REVIEW_BASE = self.bump
            self.assertFalse(SER.run_one("v9001", dry=True), "a base that is not an ancestor was asked anyway")
            SER.REVIEW_BASE = self.base
            self.assertTrue(SER.run_one("v9002", dry=True), "premise: a real ancestor base is asked")
        finally:
            os.remove(os.path.join(self.repo, "TASKS.md"))


class WithoutABaseTheLookIsTheVersionsRange(unittest.TestCase):
    """v3526 (#42): without --base every version was looked at through its bump alone - v3523, v3524 and v3525 each
    came back cannot-tell on their first ask; v3525 with --base returned five findings. The default look is now the
    range from the commit that shipped the version before it; --bump-only keeps the keyhole."""

    @classmethod
    def setUpClass(cls):
        ALookCanCoverABatch.setUpClass.__func__(cls)      # its own copy of the same two-commit batch

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.repo, ignore_errors=True)

    def setUp(self):
        self._saved = (SER.REPO, SER.REVIEW_BASE, SER.BUMP_ONLY)
        SER.REPO = self.repo
        self.tasks = os.path.join(SER.REPO, "TASKS.md")
        with open(self.tasks, "w") as fh:
            fh.write("| **v9001** | `%s` | v9001 - base |\n| **v9002** | `%s` | v9002 - stamp |\n"
                     % (self.base[:8], self.bump[:8]))
        self.seen = []
        self._pf = SER.payload_for
        SER.payload_for = lambda sha, *a, **k: (self.seen.append(SER.REVIEW_BASE) or self._pf(sha, *a, **k))

    def tearDown(self):
        SER.payload_for = self._pf
        SER.REPO, SER.REVIEW_BASE, SER.BUMP_ONLY = self._saved
        os.remove(self.tasks)

    def test_the_default_look_starts_where_the_previous_version_shipped(self):
        SER.REVIEW_BASE, SER.BUMP_ONLY = None, False
        self.assertTrue(SER.run_one("v9002", dry=True))
        self.assertEqual(self.seen, [self.base],
                         "the look was not widened to the version's range: %r" % (self.seen,))
        self.assertIsNone(SER.REVIEW_BASE, "the range must be this look's alone, never left behind for the next")

    def test_bump_only_keeps_the_keyhole(self):
        SER.REVIEW_BASE, SER.BUMP_ONLY = None, True
        self.assertTrue(SER.run_one("v9002", dry=True))
        self.assertEqual(self.seen, [None])

    def test_a_version_with_no_predecessor_falls_back_to_its_own_commit(self):
        SER.REVIEW_BASE, SER.BUMP_ONLY = None, False
        self.assertTrue(SER.run_one("v9001", dry=True), "v9000 never shipped, so the look is the bound commit alone")
        self.assertEqual(self.seen, [None])


RED_PROOF = [
    {"why": "REG-1739 - the batch label counts as a cut again: an uncut --base look tells the eye it is truncated",
     "file": "second_eye_run.py",
     "find": "    if _cut:\n        note += (\"\\nAND IT IS ALSO TRUNCATED",
     "replace": "    if dropped:\n        note += (\"\\nAND IT IS ALSO TRUNCATED",
     "matches": 1},
    {
        "why": "v3526 (#42) - the default look is the bump commit alone again",
        "file": "tv/second_eye_run.py",
        "find": "    elif not BUMP_ONLY:\n        _db, _dwhy = _default_base(version, sha)\n",
        "replace": "    elif False:\n        _db, _dwhy = _default_base(version, sha)\n",
        "matches": 1,
    },
    {
        "why": "2026-09-27 - --base is ignored: a batch shipped as bump-only commits can never be shown to the eye",
        "file": "second_eye_run.py",
        "find": "    if REVIEW_BASE:\n        return [\"git\", \"diff\"]",
        "replace": "    if False:\n        return [\"git\", \"diff\"]",
        "matches": 1,
    },
    {
        "why": "2026-09-27 - a base that is not an ancestor is asked anyway: the row claims a range that is empty",
        "file": "second_eye_run.py",
        "find": "        if _anc is None:\n            print(\"  %s: --base %s is not an ancestor",
        "replace": "        if False:\n            print(\"  %s: --base %s is not an ancestor",
        "matches": 1,
    },
    {
        "why": "2026-09-27 - the widened look does not tell the eye it spans several commits, nor the row what it covered",
        "file": "second_eye_run.py",
        "find": "    if REVIEW_BASE:\n        _span, _ = _sh(",
        "replace": "    if False:\n        _span, _ = _sh(",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
