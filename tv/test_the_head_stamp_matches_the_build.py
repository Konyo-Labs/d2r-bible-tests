# -*- coding: utf-8 -*-
"""The browser tab and the d2r-build meta carry the same version as window.D2R_BUILD.

Measured: the <title> and <meta name="d2r-build"> still said v710.1 while
window.D2R_BUILD.id had moved. The bump rewrote the JS object and never the
head, so the tab stayed on that old token. The footer badge reads D2R_BUILD
at runtime and was not the frozen copy.

This reads bible.html. It does not open a browser.
"""
from __future__ import annotations

import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable
enable()

ROOT = os.path.dirname(HERE)
BIBLE = os.path.join(ROOT, "bible.html")

_VER = re.compile(r"v\d+(?:\.\d+)*")
_TITLE = re.compile(r"<title>([^<]*)</title>")
_META_VER = re.compile(r'<meta name="d2r-build" content="([^"]*)">')
_META_DATE = re.compile(r'<meta name="d2r-build-date" content="([^"]*)">')
_BUILD = re.compile(
    r"  window\.D2R_BUILD = \{ id:'(v\d+(?:\.\d+)*)', name:'(?:[^'\\]|\\.)*', "
    r"date:'(\d{4}-\d{2}-\d{2})', note:'(?:[^'\\]|\\.)*' \};")


def _one(src, pat, label):
    found = list(pat.finditer(src))
    if len(found) != 1:
        raise AssertionError(
            "%s matched %d times, so this guard is not reading one stamp" % (label, len(found)))
    return found[0]


def head_stamp(src):
    """The title version token, the d2r-build meta, and D2R_BUILD's id and date.

    Each anchor is required exactly once. A second copy, or none, is a failure
    of the guard's reach, not a pass.
    """
    title = _one(src, _TITLE, "<title>")
    versions = _VER.findall(title.group(1))
    if len(versions) != 1:
        raise AssertionError(
            "the title holds %d version tokens (%r), so there is no one token to compare"
            % (len(versions), versions))
    meta = _one(src, _META_VER, "d2r-build")
    date = _one(src, _META_DATE, "d2r-build-date")
    build = _one(src, _BUILD, "window.D2R_BUILD")
    return versions[0], meta.group(1), date.group(1), build.group(1), build.group(2)


def assert_head_matches(src):
    title_ver, meta_ver, meta_date, build_id, build_date = head_stamp(src)
    if title_ver != build_id:
        raise AssertionError(
            "title version %s != window.D2R_BUILD.id %s" % (title_ver, build_id))
    if meta_ver != build_id:
        raise AssertionError(
            "d2r-build %s != window.D2R_BUILD.id %s" % (meta_ver, build_id))
    if meta_date != build_date:
        raise AssertionError(
            "d2r-build-date %s != window.D2R_BUILD.date %s" % (meta_date, build_date))


_FROZEN = (
    "<title>Konyo's D2R Farming Bible v1.1 · TV DIABLO</title>\n"
    '<meta name="d2r-build" content="v1.1">\n'
    '<meta name="d2r-build-date" content="2020-01-01">\n'
    "  window.D2R_BUILD = { id:'v2', name:'v2 - a ship', date:'2020-01-02', note:'n' };\n"
)


class TestTheHeadStampMatchesTheBuild(unittest.TestCase):

    def test_the_page_title_and_build_meta_match_D2R_BUILD(self):
        with io.open(BIBLE, encoding="utf-8") as fh:
            src = fh.read()
        assert_head_matches(src)

    def test_a_frozen_title_is_refused(self):
        """A mismatch fixture must raise. A guard that stays green on this is reading prose."""
        with self.assertRaises(AssertionError) as cm:
            assert_head_matches(_FROZEN)
        self.assertIn("v1.1", str(cm.exception))
        self.assertIn("v2", str(cm.exception))


_PAGE = (
    "<title>Konyo's D2R Farming Bible v1.1 · TV DIABLO</title>\n"
    '<meta name="d2r-build" content="v1.1">\n'
    '<meta name="d2r-build-date" content="2020-01-01">\n'
    '<meta name="d2r-build-note" content="old note">\n'
    "<!-- v1 stays in this comment -->\n"
    '<style id="v710-tv-diablo"></style>\n'
    "  window.D2R_BUILD = { id:'v1.1', name:'v1.1 - old', date:'2020-01-01', note:'old note' };\n"
)


class TestTheBumpRewritesTheHead(unittest.TestCase):

    def test_only_the_version_token_moves_and_the_metas_follow(self):
        import bump_version as B
        note = 'quote "kept" & amp <not a tag>'
        out = B._rewrite_head_stamps(_PAGE, "v9", "2026-10-15", note)
        self.assertIn("<title>Konyo's D2R Farming Bible v9 · TV DIABLO</title>", out)
        self.assertIn('<meta name="d2r-build" content="v9">', out)
        self.assertIn('<meta name="d2r-build-date" content="2026-10-15">', out)
        self.assertIn(
            '<meta name="d2r-build-note" content="quote &quot;kept&quot; &amp; amp &lt;not a tag>">',
            out)
        self.assertIn("<!-- v1 stays in this comment -->", out)
        self.assertIn('<style id="v710-tv-diablo"></style>', out)
        self.assertIn("id:'v1.1'", out)
        note_line = next(ln for ln in out.split("\n") if "d2r-build-note" in ln)
        self.assertEqual(note_line.count('"'), 4)
        self.assertNotIn('"', note_line.split('content="', 1)[1].rsplit('"', 1)[0])

    def test_a_missing_title_refuses_before_a_write(self):
        import bump_version as B
        with self.assertRaises(SystemExit) as cm:
            B._rewrite_head_stamps("<html></html>", "v9", "2026-10-15", "plain")
        self.assertIn("nothing written", str(cm.exception))

RED_PROOF = [
    {"why": "v710 - the d2r-build meta keeps an old token while window.D2R_BUILD.id moves",
     "file": "bible.html",
     "find": "<meta name=\"d2r-build\" content=\"",
     "replace": "<meta name=\"d2r-build\" content=\"v710.1-",
     "matches": 1},
    {"why": "the d2r-build-date meta disagrees with window.D2R_BUILD.date",
     "file": "bible.html",
     "find": "<meta name=\"d2r-build-date\" content=\"",
     "replace": "<meta name=\"d2r-build-date\" content=\"2000-01-01 ",
     "matches": 1},
    {"why": "v710 - the bump rewrites the JS object and never the head, so the tab stays on the old token",
     "file": "tv/bump_version.py",
     "find": "    html = title_pat.sub(title_repl, html, count=1)\n",
     "replace": "",
     "matches": 1},
    {"why": "the build note is written into an attribute unescaped, so a quote in it breaks the meta",
     "file": "tv/bump_version.py",
     "find": "    note_attr = _attr_text(note)\n",
     "replace": "    note_attr = note\n",
     "matches": 1},
    {"why": "the bump replaces the whole title with the version, so the words around the token are lost",
     "file": "tv/bump_version.py",
     "find": "        return \"<title>\" + body.replace(versions[0], ver, 1) + \"</title>\"\n",
     "replace": "        return \"<title>\" + ver + \"</title>\"\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
