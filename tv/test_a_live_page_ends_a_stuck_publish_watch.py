#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v3900 (REG-3736) - WHEN THE LIVE PAGE ALREADY SERVES THE VERSION, A PUBLISH WATCH STUCK ON A QUEUED RUN ENDS AND SAYS SO.

MEASURED 11-11: v3898 reached main at 22:30 and GitHub started none of the repo's runs - Publish sat QUEUED with no job for 50+
minutes. On his order v3898 went live by hand (deploy.sh, verified on the page's title and build meta at 23:20). The ship's
Publish watch could only ever ask the workflow, so it would have waited out its whole watch, and the next version's launcher
(waiting on its "SUCCEEDED" line) with it. Now, once Publish has stayed UNSTARTED past LIVE_PAGE_AFTER_S, the watch also asks
the live page's own build stamp: serving this version ends the watch with "LIVE ... published another way" - never the word
SUCCEEDED, which stays the workflow's. A page serving another version, or one that cannot be read, changes nothing.

DRIVEN: the real _watch_publish with a fake GitHub reader, a fake clock and a fake live probe; page_serves over fake pages.
Only main() hands the ship a real probe, so no law ever reaches the network. RED_PROOF below.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import ship_when_green as SW  # noqa: E402

SHA = "ad59459680" + "0" * 30


class _Clock(object):
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.t += s


def _watch_queued(sha):
    return {"worked": True, "runs": [{"name": SW.PUBLISH, "status": "queued", "minutes": None}], "running": []}


def _run(live, wait_s=40 * 60):
    clock, said, asked = _Clock(), [], []

    def probe():
        asked.append(clock())
        return live(clock())

    code = SW._watch_publish(SHA, _watch_queued, clock.sleep, clock, said.append, wait_s, 75, None, live=probe)
    return code, "\n".join(said), asked


class ALivePageEndsAStuckPublishWatch(unittest.TestCase):

    def test_a_page_serving_the_version_ends_the_watch_as_live(self):
        """* THE POINT - 11-11: Publish queued, the page already serves the version -> LIVE, the watch ends"""
        code, said, asked = _run(lambda t: True)
        self.assertEqual(code, 0, said)
        self.assertIn("LIVE - the live page already serves this version", said)
        self.assertNotIn("SUCCEEDED", said, "a page published another way was called a Publish success")
        self.assertTrue(asked and min(asked) >= SW.LIVE_PAGE_AFTER_S, "the page was asked before the grace: %r" % asked)

    def test_baseline_a_page_serving_another_version_keeps_watching(self):
        code, said, _asked = _run(lambda t: False)
        self.assertEqual(code, 2, said)
        self.assertNotIn("LIVE -", said)

    def test_an_unreadable_page_changes_nothing(self):
        code, said, _asked = _run(lambda t: None)
        self.assertEqual(code, 2, said)

    def test_the_page_stamp_is_read_off_its_build_meta(self):
        page = '<meta name="d2r-build" content="v3900">'
        self.assertIs(SW.page_serves("v3900", fetch=lambda u: page), True)
        self.assertIs(SW.page_serves("v3901", fetch=lambda u: page), False)
        self.assertIsNone(SW.page_serves("v3900", fetch=lambda u: "<html>no stamp</html>"))
        self.assertIsNone(SW.page_serves("v3900", fetch=lambda u: (_ for _ in ()).throw(OSError("down"))))

    def test_only_the_real_door_asks_the_live_page(self):
        import inspect
        self.assertIn("live=lambda: page_serves(a.version)", inspect.getsource(SW.main))
        self.assertIn("live=None", str(inspect.signature(SW.ship)), "ship() asks the network by default - a law would too")


RED_PROOF = [
    {"why": "REG-3736 - a Publish watch stuck on a queued run no longer sees the live page that already serves the version",
     "file": "tv/ship_when_green.py",
     "find": "            if on_page is True:\n",
     "replace": "            if False:\n",
     "matches": 1},
    {"why": "REG-3736 - the live page is asked before Publish has had its grace",
     "file": "tv/ship_when_green.py",
     "find": "                and clock() - t0 >= LIVE_PAGE_AFTER_S:\n",
     "replace": "                and clock() - t0 >= 0:\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
