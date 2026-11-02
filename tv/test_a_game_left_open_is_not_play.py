"""v3855 - a D2R.exe nobody has touched for hours is a game left open, not a game being played.

Dean's console stood aside for 'he is playing' ~17 h unbroken, so 151 reels waited. Past TRIAGE_STALE_PLAY_IDLE_S of
MEASURED keyboard/mouse idleness the process alone no longer refuses triage. An unreadable idle time changes nothing,
and the reason is surfaced on the Fleet beacon as river.triage.leftOpenWhy.
"""
import os
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _enable  # noqa: E402
_enable()
import control_app as CA  # noqa: E402

H = 3600.0


class GameLeftOpen(unittest.TestCase):
    def test_bar_is_hours_not_minutes(self):
        self.assertGreaterEqual(CA.TRIAGE_STALE_PLAY_IDLE_S, 2 * H)

    def test_really_playing_stays_playing(self):
        for idle in (0, 60, 30 * 60, CA.TRIAGE_STALE_PLAY_IDLE_S - 1):
            self.assertFalse(CA.stale_play_overrides(True, idle)[0], idle)

    def test_unreadable_idle_stays_playing(self):
        for idle in (None, "x", float("nan"), -5, True):
            self.assertFalse(CA.stale_play_overrides(True, idle)[0], idle)

    def test_not_playing_is_not_overridden(self):
        self.assertFalse(CA.stale_play_overrides(None, 20 * H)[0])
        self.assertFalse(CA.stale_play_overrides(False, 20 * H)[0])

    def test_hours_idle_is_a_game_left_open(self):
        ok, why = CA.stale_play_overrides(True, 17 * H)
        self.assertTrue(ok)
        self.assertIn("left open", why)

    def test_walk_goes_on_beside_a_game_left_open(self):
        with mock.patch.object(CA, "_d2r_running_here", return_value=(True, "probe")), \
                mock.patch.object(CA, "_os_input_idle_s", return_value=17 * H):
            self.assertIsNone(CA._triage_walk_should_stop())
        with mock.patch.object(CA, "_d2r_running_here", return_value=(True, "probe")), \
                mock.patch.object(CA, "_os_input_idle_s", return_value=60.0):
            self.assertEqual((CA._triage_walk_should_stop() or {}).get("key"), "playing")

    def test_the_tick_and_beacon_are_wired(self):
        with open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertIn("stale_play_overrides(_playing, _os_input_idle_s() if _playing is True else None)", src)
        self.assertIn('"leftOpenWhy": _wire_text((_TRIAGE_STALE_PLAY or {}).get("why"), 200) or None,', src)


RED_PROOF = [
    {"why": "the bar is gone, so any idle time reads as a game left open",
     "file": "tv/control_app.py", "find": "TRIAGE_STALE_PLAY_IDLE_S = 3 * 3600\n",
     "replace": "TRIAGE_STALE_PLAY_IDLE_S = 0\n", "matches": 1},
    {"why": "the mid-walk stop ignores a game left open",
     "file": "tv/control_app.py",
     "find": "        playing = False                      # v3855 - still a game left open: the walk goes on\n",
     "replace": "        pass\n", "matches": 1},
    {"why": "Fleet no longer hears why the game did not refuse",
     "file": "tv/control_app.py", "find": '"leftOpenWhy": _wire_text(',
     "replace": '"leftOpenWhyX": _wire_text(', "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
