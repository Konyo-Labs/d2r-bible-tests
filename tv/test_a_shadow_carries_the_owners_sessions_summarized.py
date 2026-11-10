# -*- coding: utf-8 -*-
"""#218 (REG-2765, his ruling 2026-10-28, phase 1) - THE OWNER'S SESSIONS, SUMMARIZED SO A SHADOW CAN CARRY THEM.

A shadow renders the owner's exact data one to one, and a full reel (8-12 GB) never leaves its PC: "a few small key
frames per session". tv/shadow_sessions.digest builds that: the newest sessions, newest first, dated by what they
captured, read counts by the Shelf's own rule (control_app._is_a_live_read - a commitment note is not a read, REG-2759),
the names read, and up to 3 key frames as the theatre's 160 px thumbnails - named frames first. A missing picture is
made by the theatre's resizer or the session says why; an oversized thumbnail is left out and named; the total stays
under its cap by dropping the OLDEST sessions' pictures first.

Driven on a fixture journal and a fixture reel root - never his. RED_PROOF below.
"""
import base64
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import fixture_tmp as _fx  # noqa: E402
_fx.contain()
import shadow_sessions as SS  # noqa: E402

A, B, C = "s_1792000000000_1", "s_1793000000000_2", "s_1794000000000_3"


def _rows():
    rows = []
    for sid, t in ((A, 1792000060000), (B, 1793000060000), (C, 1794000060000)):
        for k in range(5):
            c = t + k * 1000
            rows.append({"ts": c, "captureTs": c, "frameId": "%d_%d" % (k + 1, c), "sessionId": sid, "lane": "deep",
                         "scene": "stash", "names": (["Shako"] if k == 3 else [])})
            rows.append({"ts": c + 300, "frameId": "snap_0_%d.jpg" % k, "sessionId": sid, "lane": "deep-owed"})
    return rows


class TheOwnersSessionsSummarized(unittest.TestCase):

    def setUp(self):
        import control_app as ca
        self.is_read = ca._is_a_live_read
        self.d = tempfile.mkdtemp(prefix="shadow_sessions_")
        os.makedirs(os.path.join(self.d, "cache160"))
        for r in _rows():
            if r.get("lane") == "deep":
                # every read frame has its full picture; only some have a thumbnail already
                open(os.path.join(self.d, r["frameId"] + ".jpg"), "wb").write(b"\xff\xd8full")
                if r["frameId"].startswith(("1_", "3_", "4_", "5_")):
                    open(os.path.join(self.d, "cache160", r["frameId"] + ".jpg"), "wb").write(b"\xff\xd8thumb")

    def tearDown(self):
        shutil.rmtree(self.d, True)

    def test_newest_first_dated_by_capture_and_counted_by_the_shelfs_rule(self):
        o = SS.digest(_rows(), self.d, self.is_read, 1795000000000, make=None)
        self.assertEqual([s["sessionId"] for s in o["sessions"]], [C, B, A])
        c = o["sessions"][0]
        # the commitment note written 300 ms after the last capture is a moment of its session (not a read)
        self.assertEqual((c["t0"], c["t1"]), (1794000060000, 1794000064300))
        self.assertEqual(c["reads"], 5, "a commitment note was counted as a read: %r" % c["reads"])
        self.assertEqual(c["names"], ["Shako"])

    def test_the_named_frame_rides_first_as_a_thumbnail_never_a_full_frame(self):
        o = SS.digest(_rows(), self.d, self.is_read, 1795000000000, make=None)
        c = o["sessions"][0]
        ids = [f["id"] for f in c["frames"]]
        self.assertEqual(ids[0], "4_1794000063000", "the frame whose read named Shako is not the first key frame: %r" % ids)
        self.assertLessEqual(len(ids), SS.MAX_FRAMES)
        self.assertEqual(base64.b64decode(c["frames"][0]["jpg"]), b"\xff\xd8thumb", "a full frame rode instead of its thumbnail")

    def test_a_missing_thumbnail_is_made_or_its_absence_said(self):
        made = []

        def make(src, dst):
            made.append(os.path.basename(dst))
            open(dst, "wb").write(b"\xff\xd8made")
            return True
        rows = [r for r in _rows() if r.get("sessionId") == A and r.get("frameId", "").startswith(("2_", "snap"))]
        o = SS.digest(rows, self.d, self.is_read, 1795000000000, make=make)
        self.assertEqual(made, ["2_1792000061000.jpg"], "the theatre's resizer was not asked for the missing thumbnail")
        self.assertEqual(len(o["sessions"][0]["frames"]), 1)
        os.remove(os.path.join(self.d, "cache160", "2_1792000061000.jpg"))
        o2 = SS.digest(rows, self.d, self.is_read, 1795000000000, make=None)
        self.assertEqual(o2["sessions"][0]["frames"], [])
        self.assertIn("no thumbnail resizer", o2["sessions"][0]["why"] or "", "a session without pictures said nothing")

    def test_an_oversized_thumbnail_is_left_out_and_named(self):
        big = os.path.join(self.d, "cache160", "4_1794000063000.jpg")
        open(big, "wb").write(b"\xff" * (SS.MAX_THUMB + 1))
        o = SS.digest(_rows(), self.d, self.is_read, 1795000000000, make=None)
        self.assertNotIn("4_1794000063000", [f["id"] for f in o["sessions"][0]["frames"]])
        self.assertIn("4_1794000063000", o["left"], "an oversized thumbnail was dropped without being named")

    def test_the_oldest_sessions_give_their_pictures_up_first(self):
        keep = SS.MAX_TOTAL
        try:
            SS.MAX_TOTAL = 3 * len(base64.b64encode(b"\xff\xd8thumb"))
            o = SS.digest(_rows(), self.d, self.is_read, 1795000000000, make=None)
        finally:
            SS.MAX_TOTAL = keep
        by = {s["sessionId"]: s for s in o["sessions"]}
        self.assertEqual(len(by[C]["frames"]), 3, "the newest session lost its pictures to the cap")
        self.assertEqual((by[A]["frames"], by[B]["frames"]), ([], []))
        self.assertGreater(o["dropped"], 0)
        self.assertIn("left out to keep the record under", by[A]["why"] or "")
        self.assertLessEqual(o["bytes"], 3 * len(base64.b64encode(b"\xff\xd8thumb")))

    def test_a_session_with_no_read_says_why_it_has_no_picture(self):
        # v3847 - his two newest Mac sessions were skip-only; the shadow Shelf said "why UNKNOWN" under both
        rows = [{"ts": 1796000000000 + k, "captureTs": 1796000000000 + k, "lane": "skip", "kind": "skip"} for k in range(4)]
        o = SS.digest(rows, self.d, self.is_read, 1797000000000, make=None)
        s = o["sessions"][0]
        self.assertEqual((s["reads"], s["frames"]), (0, []))
        self.assertIn("no frame of this session was read", s["why"] or "", "a session with no read says nothing: %r" % s["why"])


RED_PROOF = [
    {"why": "v3847 - a session with no read says nothing under it",
     "file": "shadow_sessions.py",
     "find": "            s[\"why\"] = (\"no frame of this session was read, so it has no key frame\" if not reads\n",
     "replace": "            s[\"why\"] = (None if not reads\n",
     "matches": 1},
    {"why": "REG-2765 - a named frame is not preferred as a key frame",
     "file": "shadow_sessions.py",
     "find": "    for f in list(reversed(named)) + ([ids[0], ids[len(ids) // 2], ids[-1]] if ids else []):\n",
     "replace": "    for f in ([ids[0], ids[len(ids) // 2], ids[-1]] if ids else []):\n",
     "matches": 1},
    {"why": "REG-2765 - the newest sessions give their pictures up first",
     "file": "shadow_sessions.py",
     "find": "    for s in reversed(out[\"sessions\"]):                       # the oldest sessions give their pictures up first\n",
     "replace": "    for s in out[\"sessions\"]:\n",
     "matches": 1},
    {"why": "REG-2765 - an oversized thumbnail rides",
     "file": "shadow_sessions.py",
     "find": "    if len(data) > MAX_THUMB:\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "REG-2765 - a session without pictures says nothing",
     "file": "shadow_sessions.py",
     "find": "        if not s[\"frames\"] and whys:\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "REG-2765 - every journal row counts as a read",
     "file": "shadow_sessions.py",
     "find": "        reads = [r for r in g if is_read(r)]\n",
     "replace": "        reads = list(g)\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
