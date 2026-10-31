# -*- coding: utf-8 -*-
"""v3850 (Elad 17:51/17:53, 2026-10-31) - ONE ONLINE/OFFLINE FUNCTION, AND A RECORDER KEEPS A PC ONLINE.

Seen: Dean's laptop slept at ~17:14 IDT. At 17:47 the Fleet still listed him online and his shadow bar said
"Dean · online now". The site keeps a presence key 40 min; the bar asked only "is he listed"; the card had its own
2040 s rule. This law pins that fleet_presence.presence_of is the only rule, that /api/fleet stamps it, that the
shadow banner and the card only read it, and that a live recorder with the console down still reads ONLINE.

RED_PROOF below.
"""
import io
import os
import sys
import unittest
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fleet_presence as FP  # noqa: E402

NOW = 1793462400000


def _iso(ms):
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _src(name):
    with io.open(os.path.join(HERE, name), encoding="utf-8") as f:
        return f.read()


RED_PROOF = [
    {"why": "a row still in the site's online list past its refresh reads online again (Dean, 17:47)",
     "file": "fleet_presence.py",
     "find": "    if listed_online is True and ages.get(\"console\", 1e18) <= STALE_AFTER_S:\n",
     "replace": "    if listed_online is True:\n",
     "matches": 1},
    {"why": "a live recorder with the console stopped reads offline",
     "file": "fleet_presence.py",
     "find": "    if ages.get(\"recorder\", 1e18) <= STALE_AFTER_S:\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "the shadow banner asks list membership again",
     "file": "console_snapshot.py",
     "find": "                return _fp.presence_of(row, state).get(\"online\")\n",
     "replace": "                return state\n",
     "matches": 1},
    {"why": "/api/fleet stops stamping presence on its rows",
     "file": "control_app.py",
     "find": "                _fl = _fpz.stamp_fleet(_fl)\n",
     "replace": "                pass\n",
     "matches": 1},
]


class ThePresenceRule(unittest.TestCase):
    def row(self, ago_s=None, rec_ago_s=None, alive=True):
        r = {"nickname": "Dean", "platform": "win32"}
        if ago_s is not None:
            r["t"] = _iso(NOW - ago_s * 1000)
        if rec_ago_s is not None:
            r["recorder"] = {"alive": alive, "t": _iso(NOW - rec_ago_s * 1000)}
        return r

    def test_fresh_console_is_online_now(self):
        p = FP.presence_of(self.row(60), True, NOW)
        self.assertEqual((p["state"], p["words"]), ("online", "online now"))

    def test_listed_but_stale_is_offline_with_last_seen(self):
        p = FP.presence_of(self.row(33 * 60), True, NOW)
        self.assertEqual(p["state"], "offline", p)
        self.assertEqual(p["words"], "offline \u00b7 last seen 33 min ago")

    def test_the_bar_is_one_refresh_plus_one_beacon(self):
        self.assertEqual(FP.STALE_AFTER_S, 900 + 240 + 60)
        self.assertTrue(FP.presence_of(self.row(FP.STALE_AFTER_S), True, NOW)["online"])
        self.assertFalse(FP.presence_of(self.row(FP.STALE_AFTER_S + 1), True, NOW)["online"])

    def test_recorder_alive_console_down_is_online_recording(self):
        p = FP.presence_of(self.row(50 * 60, rec_ago_s=30), False, NOW)
        self.assertEqual((p["state"], p["via"], p["words"]), ("online", "recorder", "online \u00b7 recording"))

    def test_a_dead_or_stale_recorder_does_not_hold_it_online(self):
        self.assertFalse(FP.presence_of(self.row(50 * 60, rec_ago_s=30, alive=False), False, NOW)["online"])
        self.assertFalse(FP.presence_of(self.row(50 * 60, rec_ago_s=40 * 60), False, NOW)["online"])

    def test_no_readable_time_is_unknown_never_online(self):
        p = FP.presence_of({"nickname": "GrokBot"}, True, NOW)
        self.assertEqual(p["state"], "unknown")
        self.assertIsNone(p["online"])
        self.assertIsNone(FP.presence_of(self.row(-600), True, NOW)["online"])   # a clock in the future


class EverySurfaceAsksIt(unittest.TestCase):
    def test_the_shadow_banner_reads_the_rule(self):
        import console_snapshot as CS
        stale = {"nickname": "Dean", "platform": "win32", "t": _iso(int(__import__("time").time() * 1000) - 33 * 60000)}
        owner = CS._rp.owner_of("Dean", "win32")
        self.assertIs(CS.online_of(owner, {"online": [stale], "offline": []}), False)

    def test_api_fleet_stamps_every_row(self):
        src = _src("control_app.py")
        self.assertEqual(src.count("_fl = _fpz.stamp_fleet(_fl)"), 1)
        fl = FP.stamp_fleet({"online": [{"t": _iso(NOW)}], "offline": [{"t": _iso(NOW)}]}, NOW)
        self.assertTrue(fl["online"][0]["presence"]["online"])
        self.assertFalse(fl["offline"][0]["presence"]["online"])

    def test_no_surface_keeps_its_own_clock(self):
        ui = _src("control_ui.html")
        i = ui.index("  var _fleetPresence = function (m, online, nowMs) {")
        body = ui[i:ui.index("\n  };\n", i)]
        self.assertIn("m.presence", body)
        for own in ("Date.now", "nowMs -", "900", "_fleetAgeS", "Date.parse"):
            self.assertNotIn(own, body, "the card computes presence itself again: %r" % own)
        self.assertNotIn("_FLEET_SILENT_AFTER_S", ui)
        self.assertNotIn("PRESENCE_TTL", _src("console_snapshot.py"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
