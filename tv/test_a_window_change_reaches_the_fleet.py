# -*- coding: utf-8 -*-
"""A window or shadow change reaches the fleet without waiting for the 240s beacon.

The ALT reported about every 9 minutes, because the beacon loop sleeps 240s and then
builds the whole status. A close at 15:33 was still "window front" on the fleet until
15:39. The change itself is sent at once, and a flap is held to one extra report a
minute. The 240s loop stays the floor.

The report is a presence patch: window mode and shadow only. Building status under a
game is what made the beacon late, so this path must not call it.
"""
import ast
import io
import json
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))


def _src():
    with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
        return fh.read()


class TheChangeIsSentOnceAMinute(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import control_app as ca
        cls.ca = ca

    def test_the_floor_stays_four_minutes(self):
        import inspect
        self.assertIn("time.sleep(240)", inspect.getsource(self.ca._console_beacon_loop))
        self.assertEqual(60.0, self.ca._FLEET_CHANGE_MIN_S)

    def test_the_first_sample_is_not_a_report(self):
        cur = ("front", True, True, False)
        send, pending, prev = self.ca._fleet_change_due(None, cur, 1000, 0, False)
        self.assertFalse(send)
        self.assertFalse(pending)
        self.assertEqual(cur, prev)

    def test_a_change_sends_at_once_and_a_flap_waits_out_the_minute(self):
        front = ("front", True, True, False)
        back = ("background", True, True, True)
        send, pending, prev = self.ca._fleet_change_due(front, back, 1000, 0, False)
        self.assertTrue(send, "a window change was held for the floor")
        self.assertFalse(pending)
        send, pending, prev = self.ca._fleet_change_due(prev, front, 1010, 1000, False)
        self.assertFalse(send, "a second change inside the minute was sent")
        self.assertTrue(pending)
        send, pending, prev = self.ca._fleet_change_due(prev, front, 1060, 1000, pending)
        self.assertTrue(send, "the change that arrived during the quiet minute was dropped")
        self.assertFalse(pending)

    def test_an_unreadable_window_is_not_a_change(self):
        prev = ("front", True, True, False)
        send, pending, kept = self.ca._fleet_change_due(prev, None, 5000, 0, False)
        self.assertFalse(send)
        self.assertFalse(pending)
        self.assertEqual(prev, kept)

    def test_recording_is_a_change_and_the_beat_is_not(self):
        off = self.ca._fleet_change_sig("front", {
            "on": True, "available": True, "recording": False, "working": True, "beatAgeS": 1})
        on = self.ca._fleet_change_sig("front", {
            "on": True, "available": True, "recording": True, "working": False, "beatAgeS": 99})
        same = self.ca._fleet_change_sig("front", {
            "on": True, "available": True, "recording": False, "working": False, "beatAgeS": 400})
        self.assertNotEqual(off, on)
        self.assertEqual(off, same)
        self.assertNotEqual(
            self.ca._fleet_change_sig("front", {}),
            self.ca._fleet_change_sig("fullscreen", {}))
        self.assertIsNone(self.ca._fleet_change_sig("", {}))

    def test_the_loop_is_started_and_asks_the_decision(self):
        tree = ast.parse(_src())
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "_fleet_change_loop")
        calls = []
        for n in ast.walk(fn):
            if isinstance(n, ast.Call):
                f = n.func
                calls.append(f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None))
        self.assertIn("_fleet_change_due", calls)
        self.assertIn("_fleet_change_kick", calls)
        self.assertIn("_lane_tick", calls)
        started = False
        for n in ast.walk(tree):
            if not isinstance(n, ast.Call):
                continue
            f = n.func
            if not (isinstance(f, ast.Attribute) and f.attr == "Thread"):
                continue
            for kw in n.keywords:
                if kw.arg == "target" and isinstance(kw.value, ast.Name) and kw.value.id == "_fleet_change_loop":
                    started = True
        self.assertTrue(started, "nothing starts the change loop, so the decision never runs")


class ThePresenceReportDoesNotBuildStatus(unittest.TestCase):

    def setUp(self):
        import control_app as ca
        self.ca = ca
        self._env = {}
        for k in ("CI", "GITHUB_ACTIONS", "TVD_NO_BEACON"):
            self._env[k] = os.environ.pop(k, None)
        self._saved_body = ca._FLEET_LAST_BODY.get("body")
        ca._FLEET_LAST_BODY["body"] = {
            "machine": "law", "ver": "v3593", "event": "boot",
            "tally": {"ok": True}, "windowMode": "front", "lastBeacon": {"ok": True},
        }

    def tearDown(self):
        self.ca._FLEET_LAST_BODY["body"] = self._saved_body
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def _urlopen(self, posted, raw):
        def urlopen(req, timeout=8):
            posted.append(json.loads(req.data.decode("utf-8")))

            class R:
                status = 200

                def read(self):
                    return raw

                def getcode(self):
                    return 200

                def __enter__(self):
                    return self

                def __exit__(self, *a):
                    return False

            return R()
        return urlopen

    def test_a_presence_report_posts_the_window_and_not_the_status(self):
        import unittest.mock as mock
        posted = []
        raw = b'{"ok":true,"stored":["console","lastseen"],"skipped":[]}'
        with mock.patch.object(self.ca, "status_payload", side_effect=AssertionError("status built")), \
                mock.patch.object(self.ca, "_beacon_state_save", lambda: None), \
                mock.patch.object(self.ca.urllib.request, "urlopen", self._urlopen(posted, raw)):
            self.ca._console_beacon_presence()
        self.assertEqual(1, len(posted), posted)
        self.assertIs(posted[0].get("presenceOnly"), True)
        self.assertEqual("hb", posted[0].get("event"))
        self.assertEqual("v3593", posted[0].get("ver"),
                         "the patch dropped the row down to the two new fields")
        self.assertEqual({"ok": True}, posted[0].get("tally"))
        self.assertIn("windowMode", posted[0])
        self.assertIn("shadow", posted[0])
        self.assertNotIn("lastBeacon", posted[0])

    def test_a_patch_with_no_stored_row_sends_the_full_beacon(self):
        import unittest.mock as mock
        posted = []
        raw = b'{"ok":true,"stored":[],"skipped":["presence patch with no row yet"]}'
        full = []
        with mock.patch.object(self.ca, "_console_beacon", side_effect=lambda event="hb": full.append(event)), \
                mock.patch.object(self.ca, "_beacon_state_save", lambda: None), \
                mock.patch.object(self.ca.urllib.request, "urlopen", self._urlopen(posted, raw)):
            self.ca._console_beacon_presence()
        self.assertEqual(["hb"], full, "a patch with no row was not followed by a full beacon")
        self.assertIs(posted[0].get("presenceOnly"), True)

    def test_without_a_landed_beacon_the_change_sends_the_full_one(self):
        import unittest.mock as mock
        self.ca._FLEET_LAST_BODY["body"] = None
        full = []
        posted = []
        with mock.patch.object(self.ca, "_console_beacon", side_effect=lambda event="hb": full.append(event)), \
                mock.patch.object(self.ca.urllib.request, "urlopen", self._urlopen(posted, b"{}")):
            self.ca._console_beacon_presence()
        self.assertEqual(["hb"], full)
        self.assertEqual([], posted, "a change with no landed beacon posted a partial row")

RED_PROOF = [
    {"why": "a window change is held for the floor instead of sent at once: the fleet shows a closed game as front for minutes",
     "file": "tv/control_app.py",
     "find": "    if pending and (now - sent_at) >= min_s:\n        return True, False, prev\n    return False, pending, prev\n",
     "replace": "    if pending and (now - sent_at) >= 240:\n        return True, False, prev\n    return False, pending, prev\n",
     "matches": 1},
    {"why": "an unreadable window counts as a change, so a failed read reports a window state nobody saw",
     "file": "tv/control_app.py",
     "find": "    if cur is None:\n        return False, pending, prev\n    if prev is None:\n        return False, False, cur\n",
     "replace": "    if prev is None:\n        return False, False, cur\n",
     "matches": 1},
]


if __name__ == "__main__":
    # REG-1875 sweep - the gate runs this file as a script, and without this line it ran no case at all
    unittest.main(verbosity=2)
