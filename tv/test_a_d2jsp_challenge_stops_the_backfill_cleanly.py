# -*- coding: utf-8 -*-
"""#151 (REG-3795) - A d2jsp CHALLENGE STOPS THE BACKFILL CLEANLY, AND THE RUNNER RUNS FROM THE TREE.

His rule: on a challenge or rate-limit page, stop - write CHALLENGE, exit - and never bypass it; nothing is asked again
until he has looked (11-11 17:49: the run stopped at 158 of 676 items, progress safe). The runner lived in a private run
folder whose own copies of d2jsp_backfill.py / d2jsp_price_db.py came FIRST on sys.path, so no fix here reached it. It
is tv/d2jsp_backfill_run.py now, and it never puts the run folder on sys.path. The signed-in chrome is a fake handed in:
no socket opens. RED_PROOF below.
"""
import argparse
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
os.environ.pop("D2JSP_BACKFILL_LOG", None)
import d2jsp_backfill_run as R  # noqa: E402


class FakeChrome(object):
    QUOTE_BOARD = 268

    def __init__(self, page):
        self.page, self.calls, self.logins = page, [], 0

    def d2jsp_login_status(self):
        self.logins += 1
        return {"ok": True, "state": "on", "kind": "fake", "why": "fixture"}

    def _search_keywords(self, item, node_run=None):
        return item.lower()

    def live_cookie_header(self):
        return "fixture=1", None

    def _headers(self, cookie):
        return {}

    def _search_url(self, item):
        return "https://forums.d2jsp.org/search.php"

    def _search_body(self, item):
        return b"q=" + item.encode()

    def _transport(self, method, url, headers, body):
        self.calls.append(method)
        return 200, {}, self.page.encode()

    def _forum_redirect(self, loc):
        return None

    def _challenge_page(self, text):
        return False

    def _chrome_search(self, item, cookie):
        raise OSError("search: no results page")

    def _chrome_open_results(self, url, cookie):
        raise OSError("results: no results page")

    def keep_results_page(self, *a, **k):
        return None


class AChallengeStopsTheBackfill(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="d2jsp_ch_")
        self.addCleanup(shutil.rmtree, self.root, True)
        with open(os.path.join(self.root, "items.json"), "w", encoding="utf-8") as fh:
            json.dump({"items": ["Enigma", "Shako"], "priority": []}, fh)
        self.args = argparse.Namespace(root=self.root, repo=self.root, shard=0, shards=1, once=False, no_self_log=True,
                                       ignore_challenge_file=False, no_console_wait=True, refresh=False)
        self.slept = []

    def _sleep(self, s):
        self.slept.append(s)
        if len(self.slept) > 50:
            raise RuntimeError("the runner kept waiting to search again after a challenge")

    def _run(self, C):
        return R.run_loop(self.args, C=C, sleep=self._sleep)

    def _stops_on(self, page):
        C = FakeChrome(page)
        self.assertEqual(self._run(C), 2)
        self.assertEqual(C.calls, ["POST"], "searched again after a challenge: %s" % C.calls)
        flag = os.path.join(self.root, "CHALLENGE")
        self.assertTrue(os.path.exists(flag), "no CHALLENGE file was written")
        with open(flag, encoding="utf-8") as fh:
            self.assertIn("page from d2jsp", json.load(fh)["reason"])
        again = FakeChrome("<html>Search Results topic.php</html>")
        self.assertEqual(self._run(again), 2)
        self.assertEqual((again.calls, again.logins), ([], 0), "asked d2jsp while CHALLENGE was present")

    def test_a_challenge_page_stops_and_is_never_retried(self):
        self._stops_on("<html><title>Just a moment...</title> cf-browser-verification</html>")

    def test_a_rate_limit_page_stops_the_same_way(self):
        self._stops_on("<html>Too Many Requests - please slow down your searches</html>")

    def test_the_run_folder_never_shadows_the_tree(self):
        R.setup_paths(self.root, self.root)
        self.assertNotIn(os.path.abspath(self.root), [os.path.abspath(p) for p in sys.path])
        self.assertEqual(os.path.dirname(os.path.abspath(R.__file__)), HERE)


RED_PROOF = [
    {"why": "REG-3795 - a challenge page is folded and the run goes on searching",
     "file": "tv/d2jsp_backfill_run.py",
     "find": "            write_flag(challenge_path(root), why)\n            log(\"CHALLENGE/RATE-LIMIT: %s - stopping this shard\" % why)\n            return 2\n",
     "replace": "            log(\"CHALLENGE/RATE-LIMIT: %s - going on\" % why)\n",
     "matches": 1},
    {"why": "REG-3795 - a CHALLENGE file left by the last run is ignored and d2jsp is asked again",
     "file": "tv/d2jsp_backfill_run.py",
     "find": "    if os.path.exists(challenge_path(root)) and not args.ignore_challenge_file:\n        log(\"CHALLENGE file already present - exiting without asking (look first; nothing is bypassed)\")\n        return 2\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3795 - the run folder's module copies come first on sys.path again",
     "file": "tv/d2jsp_backfill_run.py",
     "find": "    if HERE not in sys.path:\n        sys.path.insert(0, HERE)\n    return root, repo\n",
     "replace": "    for p in (root, HERE):\n        if p not in sys.path:\n            sys.path.insert(0, p)\n    return root, repo\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
