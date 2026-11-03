# -*- coding: utf-8 -*-
"""LAW (v3859): the session digest's joined sync status never carries the `publish` lane. That lane reports on the very
upload it would ride in (unknown before the first post, ok after), so carried in the digest it moved the hash on every
look: an unchanged digest was posted again and the 30-min look never said "unchanged" - a write per look against the
site's budget. Red-proof: publish rides again and test_the_owner_publishes_its_session_digest goes red with it."""
import os, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import machine_sync as MS  # noqa: E402


class TheLaw(unittest.TestCase):
    def test_the_publish_lane_stays_home(self):
        v = MS.published_view({"level": "unknown", "lanes": {"recorder": "ok", "seal": "ok", "publish": "unknown", "shelf": "ok"}})
        self.assertEqual(v, {"level": "ok", "lanes": {"recorder": "ok", "seal": "ok", "shelf": "ok"}})

    def test_the_same_world_before_and_after_a_post_reads_the_same(self):
        a = MS.published_view({"lanes": {"recorder": "ok", "publish": "unknown"}})
        b = MS.published_view({"lanes": {"recorder": "ok", "publish": "ok"}})
        self.assertEqual(a, b)

    def test_the_console_attaches_that_view(self):
        src = open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        self.assertIn('d["sync"] = __import__("machine_sync").published_view(_sy)', src)


RED_PROOF = [
    {"file": "tv/machine_sync.py", "find": '    lanes.pop("publish", None)\n', "replace": "", "matches": 1,
     "why": "the publish lane rides in the digest again"},
]

if __name__ == "__main__":
    unittest.main()
