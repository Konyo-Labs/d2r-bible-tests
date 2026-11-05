# -*- coding: utf-8 -*-
"""v3860 (#230): a reel that seals after the last digest post publishes the digest within SEAL_GAP_MS, not 3 h later.

The ALT, 2026-11-03: the digest posted at 13:17 IST and the Shelf could not see 14:02 or 15:02 until ~16:17. A seal
opens the lane (rate-limited to 10 min after the last post, and after a refusal); without a seal the 3 h gap stands.

RED_PROOF below: each one, applied, turns this law red."""
import os
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable; enable()

H = 3600 * 1000
T = 1793704664894  # the ALT's real postedAt


class ASealedReel(unittest.TestCase):
    def test_a_seal_after_the_post_opens_the_lane(self):
        import shadow_sessions as ss
        st = {"postedAt": T, "checkedAt": T + 30 * 60000}
        self.assertTrue(ss.may_build(st, T + H, False, sealed_at=T + H - 60000))

    def test_no_seal_keeps_the_three_hour_gap(self):
        import shadow_sessions as ss
        # v3862 - the gap is the lane's own MIN_GAP_MS (1 h on Workers Paid; it was 3 h): one ms inside it
        self.assertFalse(ss.may_build({"postedAt": T}, T + ss.MIN_GAP_MS - 1, False, sealed_at=None))
        self.assertFalse(ss.may_build({"postedAt": T}, T + ss.MIN_GAP_MS - 1, False, sealed_at=T - 1000))

    def test_the_rate_limit_holds(self):
        import shadow_sessions as ss
        self.assertFalse(ss.may_build({"postedAt": T}, T + 5 * 60000, False, sealed_at=T + 60000))
        self.assertFalse(ss.may_build({"postedAt": T, "refuseAt": T + H}, T + H + 60000, False, sealed_at=T + H))

    def test_the_console_hands_its_seal_time_to_the_lane(self):
        import control_app as ca
        seen = {}
        def mb(state, now, boot, sealed_at=None):
            seen["s"] = sealed_at
            return False
        with mock.patch.object(ca, "_shadow_watch_stored", return_value={"rotatedAt": T + H}), \
                mock.patch.object(ca, "_beacon_suppressed_by", return_value=None), \
                mock.patch.object(ca, "_profile_json_load", return_value={}), \
                mock.patch("shadow_sessions.may_build", side_effect=mb):
            ca._frames_publish_once(False)
        self.assertEqual(T + H, seen.get("s"))


RED_PROOF = [
    {"why": "a seal no longer opens the lane",
     "file": "tv/shadow_sessions.py",
     "find": "    if _sealed is not None and (_posted is None or _sealed > _posted):\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "the console stops handing its seal time over",
     "file": "tv/control_app.py",
     "find": "bool(boot), sealed_at=_sealed):",
     "replace": "bool(boot), sealed_at=None):",
     "matches": 1},
    {"why": "no rate limit after the last post",
     "file": "tv/shadow_sessions.py",
     "find": "(_posted is None or now_ms - _posted >= SEAL_GAP_MS) and ",
     "replace": "",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
