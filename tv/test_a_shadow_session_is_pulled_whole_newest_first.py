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


class ThePullOnlyReadsThePC(unittest.TestCase):
    """#208 - the I/O: a listing that does not come back is UNKNOWN (None), never 'no reels'; the copy's sftp batch only ever
    GETs - nothing on his PC is written or removed by the pull. MEASURED 11-12: a 196-frame OLD PC ALT reel (14 MB) copied
    whole in 13.7 s over one sftp connection."""

    class _R(object):
        def __init__(self, rc, out=""):
            self.returncode, self.stdout = rc, out

    def test_an_unread_listing_is_unknown_never_empty(self):
        pc = {"ssh": "u@h"}
        self.assertIsNone(SP.list_remote(pc, run=lambda *a, **k: self._R(255)), "a failed ssh read as no reels")
        self.assertIsNone(SP.list_remote(pc, run=lambda *a, **k: self._R(0, "not json")), "a broken answer read as no reels")
        self.assertEqual(SP.list_remote(pc, run=lambda *a, **k: self._R(0, "[]")), [], "BASELINE: an empty PC is []")

    def test_the_copy_only_gets(self):
        import tempfile, shutil
        d = tempfile.mkdtemp(prefix="shadowpull-law-")
        self.addCleanup(shutil.rmtree, d, True)
        seen = {}

        def run(argv, **k):
            b = argv[argv.index("-b") + 1]
            with open(b, encoding="utf-8") as fh:
                seen["batch"] = fh.read()
            return self._R(0)
        ok, why = SP.copy_reel({"ssh": "u@h", "repo": "d2r_bible_tests"}, "reel_s_1", ["f_0001.jpg", "f_0002.jpg"], d, run=run)
        self.assertTrue(ok, why)
        lines = [l for l in seen["batch"].splitlines() if l.strip()]
        self.assertEqual(len(lines), 2)
        self.assertTrue(all(l.startswith("get ") for l in lines), "the pull's batch does more than read his PC: %r" % lines)
        self.assertIn("d2r_bible_tests/tv/frames/hist/reel_s_1/f_0001.jpg", seen["batch"])

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
    {"why": "#208 - a listing that never came back reads as a PC with no reels",
     "file": "tv/shadow_pull.py",
     "find": "    if getattr(r, \"returncode\", 1) != 0:\n        return None\n    raw = (r.stdout or \"\").strip()\n",
     "replace": "    if getattr(r, \"returncode\", 1) != 0:\n        return []\n    raw = (r.stdout or \"\").strip()\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
