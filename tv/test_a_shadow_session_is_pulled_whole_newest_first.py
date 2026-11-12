# -*- coding: utf-8 -*-
"""#208 (his ruling 11-12 ~23:50 IST: "Pull to the Mac") - A DONE SHADOW SESSION IS COPIED WHOLE, NEWEST FIRST, UNDER A BUDGET
AND HIS 8 GB FLOOR. tv/shadow_pull's planner: a reel is done when it is not the PC's rolling reel and its newest frame is 10+
minutes old; a reel is copied whole or not started; the walk stops at the first reel that does not fit; free space never
drops under his floor; an UNKNOWN free space plans nothing and says so. Fixtures only. RED_PROOF below."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import shadow_pull as SP  # noqa: E402

NOW = 1_800_000_000.0
MB = 1024 ** 2


def _reel(name, n, size_mb, age_s):
    return {"reel": name, "files": [{"name": "f_%04d.jpg" % i, "size": int(size_mb * MB / n), "mtime": NOW - age_s - (n - i)}
                                    for i in range(n)]}


class AShadowSessionIsPulledWholeNewestFirst(unittest.TestCase):

    def setUp(self):
        self.listing = [_reel("reel_s_3", 10, 100, 3600), _reel("reel_s_2", 10, 400, 7200),
                        _reel("reel_s_1", 10, 50, 9000), _reel("reel_s_live", 5, 10, 30), _reel("reel_s_empty", 0, 0, 9000)]

    def test_done_is_quiet_and_not_rolling_newest_first(self):
        done = SP.done_reels(self.listing, NOW, rolling="reel_s_9")
        self.assertEqual(done, ["reel_s_3", "reel_s_2", "reel_s_1"], "a reel still being written, or an empty one, was done")
        self.assertNotIn("reel_s_3", SP.done_reels(self.listing, NOW, rolling="reel_s_3"), "the rolling reel was copied")
        self.assertIsNone(SP.done_reels(None, NOW), "an unread listing read as nothing to copy")

    def test_a_reel_is_copied_whole_newest_first_and_the_walk_stops_at_the_first_that_does_not_fit(self):
        """* THE POINT"""
        done = SP.done_reels(self.listing, NOW)
        p = SP.plan(self.listing, done, {}, budget_bytes=200 * MB, free_bytes=100 * 1024 * MB, floor_bytes=8 * 1024 * MB)
        self.assertEqual([r for r, _f in p["copy"]], ["reel_s_3"], "the plan skipped past a reel too big for the room: %r" % p)
        self.assertEqual(len(p["copy"][0][1]), 10, "a reel was planned in part")
        self.assertIn("budget", p["why"])

    def test_his_floor_is_never_crossed(self):
        done = SP.done_reels(self.listing, NOW)
        p = SP.plan(self.listing, done, {}, budget_bytes=10 * 1024 * MB, free_bytes=8 * 1024 * MB + 120 * MB,
                    floor_bytes=8 * 1024 * MB)
        self.assertEqual([r for r, _f in p["copy"]], ["reel_s_3"])
        self.assertLessEqual(p["bytes"], 120 * MB)
        self.assertIn("floor", p["why"])

    def test_a_reel_already_here_costs_nothing_and_a_half_copy_finishes(self):
        done = SP.done_reels(self.listing, NOW)
        have = {"reel_s_3": set("f_%04d.jpg" % i for i in range(10)), "reel_s_2": set("f_%04d.jpg" % i for i in range(7))}
        p = SP.plan(self.listing, done, have, budget_bytes=10 * 1024 * MB, free_bytes=100 * 1024 * MB)
        self.assertEqual(p["copy"][0], ("reel_s_2", ["f_0007.jpg", "f_0008.jpg", "f_0009.jpg"]), p)

    def test_unknown_free_space_plans_nothing(self):
        self.assertIsNone(SP.plan(self.listing, ["reel_s_3"], {}, free_bytes=None), "an unread disk planned a copy")


RED_PROOF = [
    {"why": "#208 - a reel still being written is copied (the rolling one, or one written seconds ago)",
     "file": "tv/shadow_pull.py",
     "find": "        if now_s - newest >= quiet_s:\n",
     "replace": "        if True:\n",
     "matches": 1},
    {"why": "#208 - the walk skips past a reel too big for the room and copies an older one",
     "file": "tv/shadow_pull.py",
     "find": "                   else \"his 8 GB free floor would be crossed\") + \" - %s and older wait\" % reel\n            break\n",
     "replace": "                   else \"his 8 GB free floor would be crossed\") + \" - %s and older wait\" % reel\n            continue\n",
     "matches": 1},
    {"why": "#208 - his 8 GB floor is not held (only the budget)",
     "file": "tv/shadow_pull.py",
     "find": "    room = min(budget_bytes - held_bytes, free_bytes - floor_bytes)\n",
     "replace": "    room = budget_bytes - held_bytes\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
