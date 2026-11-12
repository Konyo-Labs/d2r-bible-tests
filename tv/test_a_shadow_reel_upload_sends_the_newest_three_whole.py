# -*- coding: utf-8 -*-
"""#208 (his 11-13 calls) - THIS PC SENDS ITS NEWEST 3 SESSIONS WHOLE AND THE REST AS SUMMARY REELS, STARTING AT THE LOGO.

His words: "maybe just the last 3 sessions recorded for each pc so those are online and always reachable even when a user
is offline ... a type of summary almost like it is now just not 3 frames for each session". tv/shadow_reels.py decides
what goes up; the site's reel door (test_a_shadow_reel_is_kept_under_the_cap) keeps it under the bucket's cap.
A reel still being written is never sent; a session already held the same way is not sent again; a summary keeps its
first and last frame, the frame play starts on and every door change, then one frame per 20 s, never more than 80; play
starts on the first D2 logo frame (his 11-11 ruling), or the first frame of a reel that shows none (the ALT reels open
mid-play). An unreadable reel store or a bucket that does not answer plans NOTHING - UNKNOWN, never "all sent".
"""
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
import shadow_reels as SR  # noqa: E402

T0 = 1792800000000


def _names(n, t0=T0, step=1000):
    return ["f_%d.jpg" % (t0 + i * step) for i in range(n)]


def _ses(k):
    return "s_%d_%d" % (T0 - 3600000 * k, k + 1)


class TheUploadPlan(unittest.TestCase):

    def setUp(self):
        self.hist = tempfile.mkdtemp(prefix="tvd-reelup-law-")
        self.addCleanup(shutil.rmtree, self.hist, True)

    def _reel(self, ses, n, age_s, extra=()):
        d = os.path.join(self.hist, "reel_" + ses)
        os.makedirs(d)
        for name in _names(n) + list(extra):
            p = os.path.join(d, name)
            with open(p, "wb") as fh:
                fh.write(b"\xff\xd8 frame")
            t = 2000000000 - age_s
            os.utime(p, (t, t))
        return d

    def test_only_done_reels_newest_first_and_never_the_rolling_one(self):
        self._reel(_ses(3), 4, 3600)
        self._reel(_ses(1), 4, 3600, extra=(".stash_eye_tab.jpg",))
        self._reel(_ses(0), 4, 60)            # still being written (quiet only a minute)
        self._reel(_ses(2), 4, 3600)
        got = SR.done_sessions(self.hist, 2000000000, rolling=_ses(2))
        self.assertEqual([s for s, _n in got], [_ses(1), _ses(3)], "a rolling or still-written reel was offered")
        self.assertEqual(got[0][1], _names(4), "a side file rode along as a frame")
        self.assertIsNone(SR.done_sessions(os.path.join(self.hist, "nope"), 2000000000), "an unlistable store read as none")

    def test_the_newest_three_go_whole_and_the_rest_as_summaries(self):
        local = [(_ses(k), _names(200)) for k in range(6)]
        got = SR.plan(local, {})
        self.assertEqual([g["mode"] for g in got], ["full"] * 3 + ["summary"] * 3)
        self.assertEqual(len(got[0]["frames"]), 200)
        self.assertLessEqual(max(len(g["frames"]) for g in got[3:]), SR.SUMMARY_MAX)
        self.assertLess(len(got[3]["frames"]), 200, "a summary carried every frame")

    def test_a_session_held_the_same_way_is_not_sent_again_and_a_slide_is_resent_as_a_summary(self):
        local = [(_ses(k), _names(50)) for k in range(4)]
        summary = SR.summary_frames(_names(50))
        server = {_ses(0): {"mode": "full", "frames": 50}, _ses(1): {"mode": "full", "frames": 50},
                  _ses(2): {"mode": "full", "frames": 50}, _ses(3): {"mode": "full", "frames": 50}}
        got = SR.plan(local, server)
        self.assertEqual([(g["session"], g["mode"]) for g in got], [(_ses(3), "summary")],
                         "the held sessions were resent, or the one that slid out of the newest 3 kept its full set")
        server[_ses(3)] = {"mode": "summary", "frames": len(summary)}
        self.assertEqual(SR.plan(local, server), [])

    def test_nothing_before_play_starts_goes_up(self):
        """his rule: account-page frames are never posted - what precedes the first D2 logo is the launcher (GeForce NOW's
        Loading page inside Chrome's window on the Mac, 55 frames of it on 3 Nov), never the game"""
        names = _names(120)
        logo_ts = T0 + 55000
        marks_of = lambda s: [[logo_ts, "logo"], [T0 + 80000, "char-select"]]
        local = [(_ses(k), names) for k in range(5)]
        got = SR.plan(local, {}, marks_of=marks_of)
        for g in got:
            ts = [int(n[2:-4]) for n in g["frames"]]
            self.assertGreaterEqual(min(ts), logo_ts, "a %s upload carries a frame from before the logo" % g["mode"])
            self.assertEqual(g["start"], g["frames"][0], "the upload does not open on the frame play starts on")
        self.assertEqual(len(got[0]["frames"]), 120 - 55, "a whole session lost game frames after the logo")
        no_logo = SR.plan([(_ses(0), names)], {}, marks_of=lambda s: [[T0 + 3000, "hud"]])
        self.assertEqual(len(no_logo[0]["frames"]), 120, "BASELINE: a reel with no logo (mid-play) goes up whole")

    def test_an_unknown_store_or_bucket_plans_nothing(self):
        self.assertIsNone(SR.plan(None, {}))
        self.assertIsNone(SR.plan([(_ses(0), _names(3))], None), "a bucket that did not answer read as an empty one")
        self.assertIsNone(SR.server_index({"ok": False, "why": "not bound"}))
        self.assertEqual(SR.server_index({"ok": True, "sessions": [{"session": _ses(0), "mode": "full", "frames": 3}]}),
                         {_ses(0): {"mode": "full", "frames": 3}})

    def test_play_starts_on_the_first_logo_else_the_first_frame(self):
        names = _names(30)
        marks = [[T0 + 5500, "title"], [T0 + 7200, "logo"], [T0 + 9000, "logo"], [T0 + 12000, "char-select"]]
        self.assertEqual(SR.start_frame(names, marks), "f_%d.jpg" % (T0 + 8000))
        self.assertEqual(SR.logo_frame(names, marks), "f_%d.jpg" % (T0 + 8000))
        self.assertEqual(SR.start_frame(names, [[T0 + 3000, "hud"]]), names[0], "a reel with no logo did not start at 1")
        self.assertIsNone(SR.logo_frame(names, [[T0 + 3000, "hud"]]))

    def test_a_summary_keeps_its_ends_its_start_and_every_door_change(self):
        names = _names(3000, step=1000)                 # 50 minutes of film, one frame a second
        marks = [[T0 + 61000, "logo"], [T0 + 62500, "logo"], [T0 + 90200, "char-select"], [T0 + 140000, "hud"],
                 [T0 + 2000000, "lobby"], [T0 + 2003000, "hud"]]
        got = SR.summary_frames(names, marks)
        self.assertLessEqual(len(got), SR.SUMMARY_MAX)
        must = [names[0], names[-1], "f_%d.jpg" % (T0 + 61000), "f_%d.jpg" % (T0 + 91000), "f_%d.jpg" % (T0 + 140000),
                "f_%d.jpg" % (T0 + 2000000), "f_%d.jpg" % (T0 + 2003000)]
        for m in must:
            self.assertIn(m, got, "the summary dropped a must-have frame %s" % m)
        self.assertEqual(got, sorted(got, key=lambda n: int(n[2:-4])), "the summary is not in film order")
        sparse = SR.summary_frames(_names(10, step=30000))
        self.assertEqual(len(sparse), 10, "BASELINE: frames sparser than the 20 s pacing are all kept")

    def test_an_upload_begins_sends_in_batches_and_seals_and_stops_on_a_refusal(self):
        d = self._reel(_ses(0), 6, 3600)
        item = {"session": _ses(0), "mode": "full", "frames": _names(6), "logo": None, "start": _names(6)[0]}
        sent = []

        def post(body):
            sent.append(body["op"])
            if body["op"] == "begin":
                return {"ok": True, "want": body["frames"][2:]}
            if body["op"] == "frames":
                return {"ok": True, "stored": [f["name"] for f in body["frames"]]}
            return {"ok": True, "manifest": {"bytes": 99}}

        made = lambda s, dst: shutil.copyfile(s, dst) or True
        before = set(n for n in os.listdir(tempfile.gettempdir()) if n.startswith(SR.SCRATCH_PREFIX))
        r = SR.upload(item, self.hist, post, "Dean", now_ms=lambda: T0, make=made)
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["sent"], 4, "frames the bucket already held were sent again")
        self.assertEqual(sent[0], "begin")
        self.assertEqual(sent[-1], "seal")
        after = set(n for n in os.listdir(tempfile.gettempdir()) if n.startswith(SR.SCRATCH_PREFIX))
        self.assertEqual(after - before, set(), "the upload's scratch folder outlived it")
        sent.clear()
        r = SR.upload(item, self.hist, lambda b: (sent.append(b["op"]) or {"ok": False, "why": "cap"}), "Dean",
                      now_ms=lambda: T0, make=made)
        self.assertFalse(r["ok"])
        self.assertEqual(sent, ["begin"], "a refused begin went on to send frames")
        self.assertTrue(os.path.isdir(d), "BASELINE: his reel is untouched")

    def test_a_frame_that_will_not_re_encode_is_never_sealed_into_a_hole(self):
        self._reel(_ses(0), 3, 3600)
        item = {"session": _ses(0), "mode": "full", "frames": _names(3), "logo": None, "start": _names(3)[0]}
        sent = []
        r = SR.upload(item, self.hist, lambda b: sent.append(b["op"]) or {"ok": True}, "Dean", now_ms=lambda: T0,
                      make=lambda s, dst: False)
        self.assertFalse(r["ok"])
        self.assertEqual(sent, [], "a session with frames that would not re-encode was begun")

    def test_batches_stay_under_the_limit(self):
        paths = [("f_%d.jpg" % i, "p%d" % i) for i in range(10)]
        got = SR.batches(paths, limit=250, size=lambda p: 100)
        self.assertEqual([len(b) for b in got], [2, 2, 2, 2, 2])
        self.assertEqual(SR.batches([("f_1.jpg", "p")], limit=50, size=lambda p: 100), [[("f_1.jpg", "p")]],
                         "one frame larger than the limit was dropped instead of sent alone")


class TheDoctorRow(unittest.TestCase):
    """the heart's doctor reads the lane's own receipt: a wait or nothing owed is OK, a refusal or an unanswered bucket is
    MISSING in the lane's words, no receipt is UNKNOWN"""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="tvd-reelup-doctor-")
        self.addCleanup(shutil.rmtree, self.root, True)
        import console_doctor as CD
        self.CD = CD

    def _row(self, state):
        if state is not None:
            import json
            with open(os.path.join(self.root, ".shadow_reels_state.json"), "w", encoding="utf-8") as fh:
                json.dump(state, fh)
        return self.CD._check_the_shadow_reels_reach_the_bucket(root=self.root)

    def test_each_receipt_reads_as_what_it_is(self):
        CD = self.CD
        self.assertEqual(self._row(None)[0], CD.UNKNOWN, "no receipt read as a verdict")
        self.assertEqual(self._row({"why": "waits: a reel is being written (he is playing)", "worked": 2, "owed": 1})[0], CD.OK)
        self.assertEqual(self._row({"why": "every done session is in the bucket", "worked": 5, "owed": 0})[0], CD.OK)
        bad = self._row({"why": "s_1_1: begin refused: the reel store would not take this: storage unavailable (the reel bucket D2R_ROSTER_FRAMES "
                                "bucket is not bound to the site)", "worked": 0, "owed": 4})
        self.assertEqual(bad[0], CD.MISSING, "a refused upload read as fine")
        self.assertIn("not bound", bad[1], "the row did not carry the lane's own words")
        self.assertEqual(self._row({"why": "the bucket did not answer (HTTPError) - UNKNOWN", "owed": None})[0], CD.MISSING)

    def test_the_row_is_registered(self):
        names = [n for n, _f in self.CD.CHECKS] if hasattr(self.CD, "CHECKS") else None
        src = open(os.path.join(HERE, "console_doctor.py"), encoding="utf-8").read()
        self.assertEqual(src.count('("shadow reels reach the bucket", _check_the_shadow_reels_reach_the_bucket)'), 1,
                         "the doctor never asks the reel lane")
        if names is not None:
            self.assertIn("shadow reels reach the bucket", names)


RED_PROOF = [
    {"why": "#208 - the frames before the first logo go up too, so the launcher and an account page are published",
     "file": "tv/shadow_reels.py",
     "find": "        played = ordered[ordered.index(first):] if first in ordered else []     # nothing before play starts goes up",
     "replace": "        played = ordered",
     "matches": 1},
    {"why": "#208 - every done session goes up whole, so 16 PCs' worth of full reels fill the bucket",
     "file": "tv/shadow_reels.py",
     "find": '        mode = "full" if i < full else "summary"',
     "replace": '        mode = "full"',
     "matches": 1},
    {"why": "#208 - the rolling reel is offered, so a session still being written goes up half-made",
     "file": "tv/shadow_reels.py",
     "find": "        if session_ms(ses) is None or (rolling and ses == rolling):",
     "replace": "        if session_ms(ses) is None:",
     "matches": 1},
    {"why": "#208 - a summary drops its door changes, so the logo and character select vanish from an offline PC's reel",
     "file": "tv/shadow_reels.py",
     "find": "        if kind != prev:\n            x = at_or_after(t)",
     "replace": "        if False:\n            x = at_or_after(t)",
     "matches": 1},
    {"why": "#208 - a bucket that did not answer reads as an empty one, so every session is sent again",
     "file": "tv/shadow_reels.py",
     "find": "    if local is None or server is None:\n        return None",
     "replace": "    if local is None:\n        return None\n    server = server or {}",
     "matches": 1},
    {"why": "#208 - the doctor reads every receipt as fine, so a refused upload (an unbound bucket) is never said",
     "file": "tv/console_doctor.py",
     "find": "    return MISSING, head + (why or \"the lane left no reason\")",
     "replace": "    return OK, head + (why or \"the lane left no reason\")",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main()
