# -*- coding: utf-8 -*-
"""#218 phase 2b (REG-2772, his ruling 2026-10-28) - THE CONSOLE PUBLISHES ITS OWN SESSION DIGEST, CHANGE-ONLY.

REG-2765 builds the owner's sessions, summarized; REG-2771 gives them a signed record on the site. This joins the two:
the roster publish lane (rows, then the profile, every 60 s) now posts the digest to the frames door after the profile -
on the console's start, and then only when it changed, at most every 3 h, never rebuilding thumbnails every minute (it
looks again after 30 min) and never while the beacon is suppressed. A refusal waits 3 h. The reply is remembered in its
own per-machine state file.

Driven: shadow_sessions' due / may_build / apply_reply, and control_app._frames_publish_once on a fixture journal and
reel root with the post captured - never the site, never his stores. RED_PROOF below.
"""
import io
import json
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
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import fixture_tmp as _fx  # noqa: E402
_fx.contain()
import shadow_sessions as SS  # noqa: E402

T0 = 1794000000000
H3 = SS.MIN_GAP_MS          # v3862 - the frames gap is the lane's own constant (1 h on Workers Paid; it was 3 h)


def _rows(name="Shako"):
    c = T0 - 60000
    return [{"ts": c, "captureTs": c, "frameId": "1_%d" % c, "sessionId": "s_1793999000000_7", "lane": "deep",
             "scene": "stash", "names": [name]}]


class TheGate(unittest.TestCase):

    def test_a_boot_may_always_build_and_a_recent_post_may_not(self):
        self.assertTrue(SS.may_build({"postedAt": T0}, T0 + 1, True))
        self.assertFalse(SS.may_build({"postedAt": T0}, T0 + H3 - 1, False))
        self.assertTrue(SS.may_build({"postedAt": T0}, T0 + H3, False))
        self.assertFalse(SS.may_build({"checkedAt": T0}, T0 + 60000, False), "an unchanged digest is rebuilt every minute")
        self.assertFalse(SS.may_build({"refuseAt": T0}, T0 + 60000, False), "a refusal is retried at once")

    def test_change_only(self):
        d = {"v": 1, "sessions": [{"sessionId": "s_1_1"}]}
        body, why = SS.due({}, "Dean", d, T0, False)
        self.assertEqual((body["kind"], body["hash"], body["signedAt"]), ("frames", SS.digest_hash(d), T0))
        self.assertEqual(SS.due({"hash": SS.digest_hash(d)}, "Dean", d, T0, True), (None, "unchanged"))
        self.assertEqual(SS.due({}, "nobody", d, T0, False)[0], None)

    def test_a_reply_is_remembered(self):
        s = SS.apply_reply({}, "h1", {"ok": True, "stored": ["frames"]}, T0)
        self.assertEqual((s["hash"], s["postedAt"], s["why"]), ("h1", T0, "stored"))
        s2 = SS.apply_reply(s, "h2", {"ok": True, "stored": [], "skipped": ["within 3 h"]}, T0 + 5)
        self.assertEqual(s2["hash"], "h1", "a digest the site skipped was remembered as published")
        s3 = SS.apply_reply(s2, "h3", {"ok": False, "why": "quota"}, T0 + 9)
        self.assertEqual((s3["refuseAt"], s3["why"]), (T0 + 9, "refused: quota"))


class TheConsolePublishesIt(unittest.TestCase):

    def setUp(self):
        import control_app as ca
        self.ca = ca
        self.d = tempfile.mkdtemp(prefix="frames_publish_")
        self.hist = os.path.join(self.d, "hist")
        os.makedirs(os.path.join(self.hist, "cache160"))
        open(os.path.join(self.hist, "cache160", "1_%d.jpg" % (T0 - 60000)), "wb").write(b"\xff\xd8thumb")
        self.posts = []

    def tearDown(self):
        shutil.rmtree(self.d, True)

    def _once(self, boot, now, rows=None, held=None):
        ca = self.ca
        with mock.patch.object(ca, "_log_root", return_value=self.d), \
                mock.patch.object(ca, "HIST_DIR", self.hist), \
                mock.patch.object(ca, "_profile_owner", return_value="Dean"), \
                mock.patch.object(ca, "_beacon_suppressed_by", return_value=held), \
                mock.patch.object(ca, "_roster_post", side_effect=lambda url, body, key=None: (
                    self.posts.append(body) or {"ok": True, "stored": ["frames"]})), \
                mock.patch("replay.load_journal", return_value=rows or _rows()), \
                mock.patch.object(ca.time, "time", return_value=now / 1000.0):
            ca._frames_publish_once(boot)
        with io.open(os.path.join(self.d, ".roster_frames_state.json"), encoding="utf-8") as fh:
            return json.load(fh)

    def test_a_start_posts_the_digest_and_a_minute_later_nothing_is_built(self):
        st = self._once(True, T0)
        self.assertEqual(len(self.posts), 1, "the console's start did not post its digest")
        b = self.posts[0]
        self.assertEqual((b["kind"], b["owner"], b["hash"]), ("frames", "Dean", SS.digest_hash(b["digest"])))
        self.assertEqual(b["digest"]["sessions"][0]["frames"][0]["id"], "1_%d" % (T0 - 60000))
        self.assertEqual(st["postedAt"], T0)
        with mock.patch.object(SS, "digest", side_effect=AssertionError("built inside the 3 h gap")):
            self._once(False, T0 + 60000)
        self.assertEqual(len(self.posts), 1, "a second minute posted again")

    def test_an_unchanged_digest_is_looked_at_again_only_after_30_min(self):
        self._once(True, T0)
        st = self._once(False, T0 + H3 + 1)
        self.assertEqual((len(self.posts), st.get("why")), (1, "unchanged"))
        with mock.patch.object(SS, "digest", side_effect=AssertionError("rebuilt every minute")):
            self._once(False, T0 + H3 + 60000)

    def test_a_suppressed_beacon_holds_it(self):
        st = self._once(True, T0, held="a fixture")
        self.assertEqual(self.posts, [])
        self.assertIn("suppressed", st.get("why", ""))

    def test_a_suppressed_start_keeps_its_boot_exemption(self):
        """REG-2795 (the v3829 second eye) - a held start returned normally, so the tick said done and the boot exemption
        was spent with nothing posted; the restart then waited out the 3 h gap once the hold lifted. Both lanes."""
        ca = self.ca
        with mock.patch.object(ca, "_log_root", return_value=self.d), \
                mock.patch.object(ca, "_beacon_suppressed_by", return_value="a fixture"):
            self.assertIs(ca._roster_frames_tick(True), False, "a held start spent the frames lane's boot exemption")
            self.assertIs(ca._roster_profile_tick(True), False, "a held start spent the profile lane's boot exemption")
        st = self._once(True, T0)
        self.assertEqual((len(self.posts), st.get("postedAt")), (1, T0), "the start did not post once the hold lifted")

    def test_the_lane_runs_it_after_the_profile(self):
        src = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        loop = src[src.index("def _roster_publish_loop():"):src.index("def _frames_state_path():")]
        self.assertIn("_frames_boot = not _roster_frames_tick(True)", loop, "a console start does not publish its digest")
        self.assertIn("        if _roster_frames_tick(_frames_boot):", loop, "the lane never publishes the digest again")


RED_PROOF = [
    {"why": "REG-2795 - a held start spends the frames lane's boot exemption again",
     "file": "control_app.py",
     "find": "        return False     # REG-2795 - held: a console start's exemption is kept for when the hold lifts\n",
     "replace": "        return\n",
     "matches": 1},
    {"why": "REG-2795 - a held start spends the profile lane's boot exemption again",
     "file": "control_app.py",
     "find": "        return False     # REG-2795 - held: the boot exemption waits for the hold to lift (the frames lane's sibling)\n",
     "replace": "        return\n",
     "matches": 1},
    {"why": "REG-2772 - the digest carries its build time again, so its hash moves every build and nothing is change-only",
     "file": "shadow_sessions.py",
     "find": "    out = {\"v\": 1, \"sessions\": [], \"bytes\": 0, \"dropped\": 0, \"left\": []}\n",
     "replace": "    out = {\"v\": 1, \"at\": int(now_ms), \"sessions\": [], \"bytes\": 0, \"dropped\": 0, \"left\": []}\n",
     "matches": 1},
    {"why": "REG-2772 - the lane never publishes the digest",
     "file": "control_app.py",
     "find": "        if _roster_frames_tick(_frames_boot):\n            _frames_boot = False\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-2772 - the digest is rebuilt every minute",
     "file": "shadow_sessions.py",
     "find": "    for k, gap in ((\"refuseAt\", MIN_GAP_MS), (\"postedAt\", MIN_GAP_MS), (\"checkedAt\", LOOK_AGAIN_MS)):\n",
     "replace": "    for k, gap in ():\n",
     "matches": 1},
    {"why": "REG-2772 - an unchanged digest is posted again",
     "file": "shadow_sessions.py",
     "find": "    if state.get(\"hash\") == h:\n        return None, \"unchanged\"\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-2772 - a digest the site skipped is remembered as published",
     "file": "shadow_sessions.py",
     "find": "        if stored or \"unchanged\" in skipped:\n",
     "replace": "        if True:\n",
     "matches": 1},
    {"why": "REG-2772 - the frames lane ignores the beacon suppression",
     "file": "control_app.py",
     "find": "    held = _beacon_suppressed_by()\n    if held:\n        state[\"why\"] = \"suppressed: \" + str(held)[:160]\n        _profile_json_save(_frames_state_path(), state)\n",
     "replace": "    held = None\n    if held:\n        state[\"why\"] = \"suppressed: \" + str(held)[:160]\n        _profile_json_save(_frames_state_path(), state)\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
