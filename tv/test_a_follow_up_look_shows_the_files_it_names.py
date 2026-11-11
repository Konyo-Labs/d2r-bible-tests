# -*- coding: utf-8 -*-
"""v3897 (REG-3699, card #196) - A FILE THE BUDGET DROPPED FROM A LOOK CAN BE SHOWN ON ITS OWN.

MEASURED 11-11: the Grok CLI's look on v3892 came back CANNOT-TELL - "the payload omitted bible.html, control_ui.html,
run_gates.py" - and the doctor says the same of v3895's look ("NEVER SAW a SUBSTANTIVE part of the change (bible.html ...)").
payload_for adds *.html only when the code diff is already under the cap, so on any large version the page is never shown,
by construction, however often the version is asked again. `second_eye_run.py vNNNN --files PATH...` makes a follow-up look
at only the named paths (*.html included): the prompt says it is a follow-up, and the row's reach note names the files.

DRIVEN on a throwaway git repo (never this one): a code change larger than the cap beside a bible.html change.
RED_PROOF below.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import second_eye_run as SER  # noqa: E402

_ENV = dict((k, v) for k, v in os.environ.items() if not k.startswith("GIT_"))


def _git(repo, *args):
    return subprocess.check_output(["git"] + list(args), cwd=repo,
                                   env=dict(_ENV, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                                            GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")).decode().strip()


class AFollowUpLookShowsTheFilesItNames(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = tempfile.mkdtemp(prefix="eye_files_")
        r = cls.repo
        _git(r, "init", "-q")
        _git(r, "config", "core.autocrlf", "false")
        os.makedirs(os.path.join(r, "tv"))
        with open(os.path.join(r, "tv", "big.py"), "w") as fh:
            fh.write("def base():\n    return 1\n")
        with open(os.path.join(r, "bible.html"), "w") as fh:
            fh.write("<html><body>\n<p>old</p>\n</body></html>\n")
        _git(r, "add", "-A")
        _git(r, "commit", "-q", "-m", "v1: base")
        with open(os.path.join(r, "tv", "big.py"), "a") as fh:
            for i in range(400):
                fh.write("\n\ndef change_%d(x):\n    return x + %d\n" % (i, i))
        with open(os.path.join(r, "bible.html"), "w") as fh:
            fh.write("<html><body>\n<p>the page's real change</p>\n</body></html>\n")
        _git(r, "commit", "-q", "-am", "v2: a big code change beside the page's")
        cls.sha = _git(r, "rev-parse", "HEAD")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.repo, ignore_errors=True)

    def setUp(self):
        self._saved = (SER.REPO, SER.REVIEW_BASE, SER.REVIEW_FILES)
        SER.REPO, SER.REVIEW_BASE, SER.REVIEW_FILES = self.repo, None, None
        env = mock.patch.dict(os.environ, {"SECOND_EYE_MAX_CHARS": "3000"})
        env.start()
        self.addCleanup(env.stop)

    def tearDown(self):
        SER.REPO, SER.REVIEW_BASE, SER.REVIEW_FILES = self._saved

    def _prompt(self):
        got = SER.payload_for(self.sha)
        self.assertIsNotNone(got[0], "PREMISE: the payload would not build: %r" % (got,))
        return got

    def test_premise_a_full_look_never_shows_the_page(self):
        prompt = self._prompt()[0]
        self.assertNotIn("diff --git a/bible.html", prompt, "PREMISE: the code diff no longer starves the page here")
        self.assertIn("diff --git a/tv/big.py", prompt)

    def test_a_follow_up_look_shows_only_the_files_it_names(self):
        """* THE POINT"""
        SER.REVIEW_FILES = ["bible.html"]
        got = self._prompt()
        prompt, note = got[0], got[1] or ""
        self.assertIn("diff --git a/bible.html", prompt, "the named page was still not shown")
        self.assertIn("the page's real change", prompt)
        self.assertNotIn("diff --git a/tv/big.py", prompt, "a follow-up look carried the files it did not name")
        self.assertIn("FOLLOW-UP LOOK AT 1 NAMED FILE(S) ONLY (bible.html)", prompt, "the eye is not told it is a follow-up")
        self.assertIn("a follow-up look at 1 named file(s) only: bible.html", note, "the row would not say what it covered")

    def test_with_no_files_named_the_pathspec_is_the_default(self):
        self.assertEqual(SER._pathspec(["--", "*.py"]), ["--", "*.py"])
        SER.REVIEW_FILES = ["a.html", "tv/b.py"]
        self.assertEqual(SER._pathspec(["--", "*.py"]), ["--", "a.html", "tv/b.py"])


RED_PROOF = [
    {"why": "v3897 (REG-3699) - a follow-up look reads the default code pathspec again (the named page is never shown)",
     "file": "tv/second_eye_run.py",
     "find": "    return ([\"--\"] + list(REVIEW_FILES)) if REVIEW_FILES else list(default)\n",
     "replace": "    return list(default)\n",
     "matches": 1},
    {"why": "v3897 (REG-3699) - the eye is not told a follow-up look covers only the named files",
     "file": "tv/second_eye_run.py",
     "find": "    if REVIEW_FILES:\n        note += (",
     "replace": "    if False:\n        note += (",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
