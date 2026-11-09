# -*- coding: utf-8 -*-
"""v3889 (REG-3496, GrokBot 6733831813) - A d2jsp READ FINDS NODE WHERE THE ONE RESOLVER FINDS IT, NOT ONLY ON PATH.

GrokBot on v3888 (/api/fleet, GET): Konyo's Mac d2jsp.ok=true reason=read; Konyo - ALT and OLD PC ALT d2jsp.ok=false
reason=unread (the daily Shako check). MEASURED on the work ALT 11-09 over SSH (read-only): its .d2jsp_check.json says
{"item": "Shako", "reason": "unread", "ok": false}; node.exe sits in %LOCALAPPDATA%\\Programs\\nodejs (node_runtime placed
it, REG-2484) and on no PATH. d2jsp_chrome asked `shutil.which("node")` in three places - the quote parser, the search
words and the item resolver - so with node off PATH every page it fetched was "unread" and every search asked "Harlequin
Crest" instead of the traders' "shako". The rest of tv/ resolves node through cb_node_harness.node_path (TV_NODE, PATH,
the known install folders); these three now do too (_node_bin).

Driven with PATH emptied and node reachable only through TV_NODE (as on the ALT, where only the known folder holds it); a
baseline with no node at all proves the case can tell the two apart. The ALT's next daily check is the live proof (owed
after the rollout). RED_PROOF below. [[copy-drift]] [[the-unjoined-end]]
"""
import os
import sys
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

NODE = CNH.node_path()
PAGE = "<html><body>Search Results</body></html>"


@unittest.skipIf(NODE is None, "node is absent on this machine - the reads are UNMEASURED here, never a pass")
class ANodeOffPathIsStillFound(unittest.TestCase):

    def _off_path(self):
        p = mock.patch.dict(os.environ, {"PATH": "", "TV_NODE": NODE})
        p.start()
        self.addCleanup(p.stop)

    def test_the_search_asks_with_the_traders_word(self):
        """* THE POINT - node only where the resolver looks, and the search still asks "shako" """
        self._off_path()
        self.assertEqual(D._search_keywords("Harlequin Crest"), "shako")
        self.assertEqual(D._resolved_name("shako"), "Harlequin Crest")

    def test_a_fetched_page_is_parsed_not_unread(self):
        self._off_path()
        self.assertNotEqual(D.parse_public_quote(PAGE, "Harlequin Crest", "2026-11-09").get("reason"), "unread",
                            "with node off PATH the parser was never run")

    def test_no_node_at_all_is_unread_and_the_plain_name(self):
        """BASELINE: with no node anywhere the same calls fall back - so the cases above can tell the two apart"""
        with mock.patch.dict(os.environ, {"PATH": "", "TV_NODE": ""}), mock.patch.object(CNH, "NODE_KNOWN", ()):
            self.assertEqual(D._search_keywords("Harlequin Crest"), "Harlequin Crest")
            self.assertEqual(D.parse_public_quote(PAGE, "Harlequin Crest", "2026-11-09").get("reason"), "unread")


RED_PROOF = [
    {"why": "v3889 (REG-3496) - the d2jsp reads look for node on PATH only again",
     "file": "tv/d2jsp_chrome.py",
     "find": "        from cb_node_harness import node_path as _np\n        return _np()\n",
     "replace": "        return shutil.which(\"node\")\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
