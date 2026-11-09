# -*- coding: utf-8 -*-
"""v3889 (#151 step 1, REG-3491) - THE CONSOLE KEEPS THE SIGNED-IN RESULTS PAGES IT READS, SCRUBBED, FOR THE BACKFILL.

His 11-09 ruling (00:35 IST): the 2-3 year d2jsp backfill runs on HIS Mac's signed-in console, forum 268 (SC non-ladder),
not on GrokBot - whose signed-out pilot got "You do not have permission to use this feature" on search. A pager that walks
the forum's older results can only be built from a REAL signed-in results page, and the only process allowed to fetch one
is the console (his cookie never leaves it - never another seat, never this shell). So the quote path the console already
runs keeps the page it read: beside the price database, gitignored, the newest D2JSP_PAGES_KEEP, every session value
(query values named like a session, hidden form fields) blanked before a byte is written. A law's stub transport never
writes one.

Driven on the real d2jsp_chrome with its network, parser and cookie stood in; files in a temp dir. RED_PROOF below.
[[heart-first]] [[borrowed-surface]]
"""
import os
import shutil
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
import d2jsp_chrome as D  # noqa: E402

PAGE = ('<html><body>Welcome back, somebody <a href="search.php?s=SECRETSESSION&o=25">Next</a>'
        '<input type="hidden" name="sid" value="HIDDENTOKEN"><input value="ALSOHIDDEN" name="k" type="hidden">'
        '<div class="results">Enigma 775 - 1.4k fg</div>Search Results</body></html>')


class _Dir(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="d2jsp_pages_")
        self.addCleanup(shutil.rmtree, self.d, True)
        p = mock.patch.dict(os.environ, {"D2JSP_PAGES_DIR": self.d})
        p.start()
        self.addCleanup(p.stop)

    def kept(self):
        return sorted(os.listdir(self.d))   # the dir is this case's own temp dir: everything in it is a kept page


class APageIsKeptScrubbed(_Dir):

    def test_every_session_value_is_blanked_and_the_pager_survives(self):
        out = D.scrub_page(PAGE)
        for secret in ("SECRETSESSION", "HIDDENTOKEN", "ALSOHIDDEN"):
            self.assertNotIn(secret, out, "a session value reached the kept page: %s" % secret)
        self.assertIn("&o=25", out, "the paging link the backfill needs was scrubbed away")
        self.assertIn("Enigma 775 - 1.4k fg", out, "the posts the backfill reads were scrubbed away")

    def test_only_the_newest_are_kept(self):
        for i in range(D.D2JSP_PAGES_KEEP + 2):
            D.keep_results_page("Enigma", PAGE, now=1000 + i)
        kept = self.kept()
        self.assertEqual(len(kept), D.D2JSP_PAGES_KEEP, "the page store grows without a bound: %s" % kept)
        self.assertTrue(kept[-1].startswith("%d-" % ((1000 + D.D2JSP_PAGES_KEEP + 1) * 1000)), "the newest page was dropped")


class OnlyTheConsolesOwnReadKeepsOne(_Dir):

    def _quote(self, transport):
        stubs = [mock.patch.object(D, "console_may_post", lambda *a, **k: True),
                 mock.patch.object(D, "parse_public_quote", lambda page, item, read_at, node_run=None: {"reason": "read"}),
                 mock.patch.object(D, "_search_keywords", lambda item, node_run=None: "nigma"),
                 mock.patch.object(D, "_resolved_name", lambda item, node_run=None: None),
                 mock.patch.object(D, "_transport", lambda *a, **k: (200, {}, PAGE.encode("utf-8")))]
        for s in stubs:
            s.start()
            self.addCleanup(s.stop)
        return D.d2jsp_quote("Enigma", "http://127.0.0.1:1", "127.0.0.1:1", 1, cookie_get=lambda: ("c=1", None),
                             transport=transport)

    def test_the_consoles_own_read_keeps_the_page(self):
        """* THE POINT - the network path the console runs (no transport handed in) keeps the page it read"""
        code, out = self._quote(None)
        self.assertEqual((code, out.get("reason")), (200, "read"), out)
        self.assertIs(out.get("pageKept"), True, "the console's read did not keep its page")
        self.assertEqual(len(self.kept()), 1)

    def test_a_handed_in_transport_never_writes_one(self):
        """BASELINE: every law that drives d2jsp_quote hands it a stub transport - none of them may write a page"""
        code, out = self._quote(lambda *a, **k: (200, {}, PAGE.encode("utf-8")))
        self.assertEqual(out.get("reason"), "read", out)
        self.assertNotIn("pageKept", out)
        self.assertEqual(self.kept(), [], "a stub transport wrote a page into the store")


RED_PROOF = [
    {"why": "v3889 (#151) - a kept page carries the session values again",
     "file": "tv/d2jsp_chrome.py",
     "find": "    out = _SCRUB_QS.sub(r\"\\1X\", str(html or \"\"))\n",
     "replace": "    out = str(html or \"\")\n",
     "matches": 1},
    {"why": "v3889 (#151) - the page store grows without a bound",
     "file": "tv/d2jsp_chrome.py",
     "find": "        for f in pages[:-(keep or D2JSP_PAGES_KEEP)]:\n",
     "replace": "        for f in []:\n",
     "matches": 1},
    {"why": "v3889 (#151) - a law's stub transport writes pages into the store",
     "file": "tv/d2jsp_chrome.py",
     "find": "    if transport is None and isinstance(out, dict) and out.get(\"reason\") == \"read\":\n",
     "replace": "    if isinstance(out, dict) and out.get(\"reason\") == \"read\":\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
