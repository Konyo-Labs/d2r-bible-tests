# -*- coding: utf-8 -*-
"""v3889 (REG-3502, #107/#30) - THE d2jsp NODE PROGRAMS NEVER RIDE THE COMMAND LINE.

MEASURED on the work ALT 11-09 (SSH, read-only): `node -e <program>` with the quote block's 44,935-character program raised
"[WinError 206] The filename or extension is too long" (Windows caps a command line at 32,767 characters); the same program
on stdin answered "shako". d2jsp_chrome ran the quote parser, the search words and the item resolver that way and caught the
error as an OSError, so on every Windows PC each fetched page read "unread" (both ALTs' daily Shako check), each search asked
the plain name, and GitHub's Windows proof run filed six d2jsp laws ALREADY RED. Now every one goes through _node_run: the
program alone on stdin; with a page to read (the page is stdin), the program in a temp file removed after - proven on the
ALT (stdin "shako"; a 60 KB page parsed "no prices", not "unread"; no temp file left).

Here the Windows cap is simulated: subprocess.run refuses any argument over 32,767 characters, as CreateProcess does, and
the real node runs the rest. RED_PROOF below. [[copy-drift]] [[the-unjoined-end]]
"""
import glob
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable   # it prints non-ASCII: never crash while REPORTING
    _enable()
except Exception:
    pass
import cb_node_harness as CNH  # noqa: E402
import d2jsp_chrome as D  # noqa: E402

CAP = 32767
REAL_RUN = subprocess.run


def _windows_run(argv, *a, **k):
    """CreateProcess's rule: a command line over 32,767 characters is refused before the program starts"""
    if sum(len(str(x)) + 1 for x in argv) > CAP:
        raise FileNotFoundError(206, "The filename or extension is too long")
    return REAL_RUN(argv, *a, **k)


@unittest.skipIf(CNH.node_path() is None, "node is absent on this machine - the reads are UNMEASURED here, never a pass")
class TheProgramNeverRidesTheCommandLine(unittest.TestCase):

    def setUp(self):
        p = mock.patch.object(D.subprocess, "run", side_effect=_windows_run)
        p.start()
        self.addCleanup(p.stop)

    def test_the_premise_the_program_is_over_the_cap(self):
        self.assertGreater(len(D._read_quote_parser()), CAP, "PREMISE: the quote block now fits a Windows command line")

    def test_the_search_words_and_the_resolver_answer(self):
        """* THE POINT - under the Windows cap the search still asks "shako" and the resolver names the item"""
        self.assertEqual(D._search_keywords("Harlequin Crest"), "shako")
        self.assertEqual(D._resolved_name("shako"), "Harlequin Crest")

    def test_a_page_is_parsed_not_unread(self):
        page = "<html><body>Search Results " + "x" * 60000 + "</body></html>"
        before = set(glob.glob(os.path.join(tempfile.gettempdir(), "tvd-d2jsp-*.js")))
        q = D.parse_public_quote(page, "Harlequin Crest", "2026-11-09")
        self.assertNotEqual(q.get("reason"), "unread", "the parser never ran under the Windows cap")
        after = set(glob.glob(os.path.join(tempfile.gettempdir(), "tvd-d2jsp-*.js")))
        self.assertEqual(after - before, set(), "a program file was left in the temp folder")

    def test_the_cap_is_real_here(self):
        """BASELINE: the simulated cap refuses a program on argv - so the cases above can tell the two ways apart"""
        with self.assertRaises(FileNotFoundError):
            _windows_run(["prog", "x" * (CAP + 1)])   # an over-cap argument, no program handed to anything


RED_PROOF = [
    {"why": "v3889 (REG-3502) - a program alone rides the command line again",
     "file": "tv/d2jsp_chrome.py",
     "find": "        return subprocess.run([node, \"-\"], input=prog, capture_output=True, timeout=timeout, text=True,\n",
     "replace": "        return subprocess.run([node, \"-e\", prog], capture_output=True, timeout=timeout, text=True,\n",
     "matches": 1},
    {"why": "v3889 (REG-3502) - the parser rides the command line again, its page on stdin",
     "file": "tv/d2jsp_chrome.py",
     "find": "        return subprocess.run([node, path], input=stdin_text, capture_output=True, timeout=timeout, text=True,\n",
     "replace": "        return subprocess.run([node, \"-e\", prog], input=stdin_text, capture_output=True, timeout=timeout, text=True,\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
