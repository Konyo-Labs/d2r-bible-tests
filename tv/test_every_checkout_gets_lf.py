# -*- coding: utf-8 -*-
"""#107 (REG-3364) - EVERY CHECKOUT GETS LF, ON EVERY PC.

Git for Windows installs with core.autocrlf=true. MEASURED 11-07 on the work ALT: `git config core.autocrlf` = true and
`git ls-files --eol` reads w/crlf for bible.html, tv/control_app.py and tv/start_tvd_win.ps1. GitHub's Windows runner does
the same. So every law that reads a file's raw bytes on a "\\n" anchor (a node driver cutting bible.html, a law reading
start_tvd_win.ps1 "rb") failed on Windows. GitHub's Windows proof set was never whole for them, and on the ALTs they
were owed forever. The repo's .gitattributes now says `* text=auto eol=lf`: the index already holds LF only (no blob is CRLF
or mixed), so nothing renormalizes. A Windows checkout writes LF from now on (an unchanged CRLF file stays until a version
touches it), and binaries are left alone. Measured here in a temp repo cloned with the Windows default. RED_PROOF below.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

GIT = shutil.which("git")


def _env():
    """git with none of a hook's GIT_* leaking in (a temp repo's answers must come from the temp repo)"""
    e = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    e.update(GIT_CONFIG_NOSYSTEM="1", GIT_AUTHOR_NAME="law", GIT_AUTHOR_EMAIL="law@x", GIT_COMMITTER_NAME="law",
             GIT_COMMITTER_EMAIL="law@x", HOME=tempfile.gettempdir())
    return e


def _git(cwd, *args):
    r = subprocess.run([GIT] + list(args), cwd=cwd, capture_output=True, env=_env(), timeout=60)
    if r.returncode != 0:
        raise AssertionError("git %s failed: %s" % (" ".join(args), r.stderr.decode("utf-8", "replace")[-400:]))
    return r.stdout


def _rule_lines():
    with io.open(os.path.join(ROOT, ".gitattributes"), encoding="utf-8") as fh:
        return [l.strip() for l in fh if l.strip() and not l.strip().startswith("#")]


class EveryCheckoutGetsLf(unittest.TestCase):

    def test_the_repo_says_lf_for_every_text_file(self):
        self.assertIn("* text=auto eol=lf", _rule_lines(), ".gitattributes no longer asks for LF on every checkout")

    @unittest.skipUnless(GIT, "git is absent - the checkout is UNMEASURED here, never a pass")
    def test_a_windows_default_checkout_writes_lf(self):
        """* THE POINT: a clone made with Git for Windows' default (autocrlf=true) still gets LF; a binary is untouched"""
        d = tempfile.mkdtemp(prefix="tvd_eol_")
        try:
            src, pc = os.path.join(d, "src"), os.path.join(d, "pc")
            os.makedirs(src)
            _git(src, "init", "-q", "-b", "main")
            shutil.copy(os.path.join(ROOT, ".gitattributes"), os.path.join(src, ".gitattributes"))
            with io.open(os.path.join(src, "law.py"), "wb") as fh:
                fh.write(b"first\nsecond\n")
            pic = b"GIF89a\x00\x01\r\n\x00\xff"
            with io.open(os.path.join(src, "pic.gif"), "wb") as fh:
                fh.write(pic)
            _git(src, "add", "-A")
            _git(src, "-c", "core.autocrlf=false", "commit", "-q", "-m", "seed")
            _git(d, "-c", "core.autocrlf=true", "clone", "-q", src, pc)
            with io.open(os.path.join(pc, "law.py"), "rb") as fh:
                got = fh.read()
            self.assertEqual(got, b"first\nsecond\n", "a Windows-default checkout wrote CR LF")
            with io.open(os.path.join(pc, "pic.gif"), "rb") as fh:
                self.assertEqual(fh.read(), pic, "a binary's bytes were converted")
            self.assertEqual(_git(pc, "-c", "core.autocrlf=true", "status", "--porcelain"), b"")
        finally:
            shutil.rmtree(d, True)

    @unittest.skipUnless(GIT, "git is absent - the index is UNMEASURED here, never a pass")
    def test_no_committed_file_is_crlf(self):
        """the rule renormalizes nothing: every text blob is already LF (else every PC would see it modified)"""
        if not os.path.isdir(os.path.join(ROOT, ".git")) and not os.path.isfile(os.path.join(ROOT, ".git")):
            self.skipTest("not a git checkout - the index is UNMEASURED here")
        out = subprocess.run([GIT, "-C", ROOT, "ls-files", "--eol"], capture_output=True, env=_env(), timeout=120)
        if out.returncode != 0:
            self.skipTest("git ls-files did not answer here - UNMEASURED")
        bad = [l for l in out.stdout.decode("utf-8", "replace").splitlines() if l.startswith(("i/crlf", "i/mixed"))]
        self.assertEqual(bad, [], "a committed file holds CR LF - the LF rule would show it modified on every PC")


RED_PROOF = [
    {"why": "#107 - the repo stops asking for LF, so Windows checkouts get CR LF again",
     "file": ".gitattributes",
     "find": "* text=auto eol=lf\n",
     "replace": "* text=auto\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
