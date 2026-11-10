# -*- coding: utf-8 -*-
"""v3895 (#153, REG-3584) - A BUSY SHADOW LOOK IS NOT A STOPPED WATCHER.

The Fleet's middle eye goes red and says "watcher has STOPPED" when shadow.working is false.
working is lane_liveness's verdict for tvd-shadow-watch: FLOWING = working, LATE = stopped.

The loop sleeps 20s, THEN looks (window find, HUD first-reads, maybe start_agent). Cycle time is
the sleep PLUS the look. The old stamp passed every_s=_SHADOW_WATCH_EVERY_S, so the bound was
60s (20 x 3). Any look longer than 40s made the lane LATE during the following sleep, and the
eye said the watcher STOPPED - a false red, especially on a slower Windows PC.

The stamp now declares no fixed period (the cycle is computed) and a silence bound of
sleep-slack + one look's budget. A 90s busy look stays FLOWING; a silence past the bound is
still LATE, and the eye still says STOPPED then.
RED_PROOF below.
"""
import io
import os
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _enable  # noqa: E402
_enable()

import control_app as ca  # noqa: E402
import lane_liveness as LL  # noqa: E402


def _read(rel):
    path = os.path.join(HERE, os.path.basename(rel)) if rel.startswith("tv/") else os.path.join(ROOT, rel)
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


class ABusyShadowLookIsNotAStoppedWatcher(unittest.TestCase):

    def setUp(self):
        self._saved = dict(LL._TICKS)
        with LL._LOCK:
            LL._TICKS.clear()

    def tearDown(self):
        with LL._LOCK:
            LL._TICKS.clear()
            LL._TICKS.update(self._saved)

    def _stamp_as_the_loop_does(self):
        LL.tick("tvd-shadow-watch", every_s=None, dead_after_s=ca._shadow_watch_dead_after_s())

    def _row_after(self, age_s):
        with LL._LOCK:
            row = LL._TICKS.get("tvd-shadow-watch")
            self.assertIsNotNone(row, "the lane never stamped")
            row["mono"] = time.monotonic() - float(age_s)
        return next(r for r in LL.rows() if r.get("lane") == "tvd-shadow-watch")

    def test_the_bound_outlasts_the_old_sleep_slack(self):
        bound = ca._shadow_watch_dead_after_s()
        old = ca._SHADOW_WATCH_EVERY_S * 3.0
        self.assertGreater(bound, old, "the bound is still the sleep slack that cried wolf")
        self.assertEqual(bound, old + ca._SHADOW_LOOK_BUDGET_S)

    def test_a_90s_look_stays_flowing(self):
        self._stamp_as_the_loop_does()
        row = self._row_after(90)
        self.assertEqual(row["state"], LL.FLOWING, row)
        self.assertLessEqual(90, ca._shadow_watch_dead_after_s())

    def test_silence_past_the_bound_is_still_late(self):
        self._stamp_as_the_loop_does()
        bound = ca._shadow_watch_dead_after_s()
        row = self._row_after(bound + 1)
        self.assertEqual(row["state"], LL.LATE, row)

    def test_the_loop_stamps_the_look_budget_not_the_sleep_alone(self):
        src = _read("tv/control_app.py")
        self.assertIn(
            "_lane_tick('tvd-shadow-watch', every_s=None, dead_after_s=_shadow_watch_dead_after_s())",
            src)
        self.assertNotIn("_lane_tick('tvd-shadow-watch', _SHADOW_WATCH_EVERY_S)", src)
        self.assertIn("def _shadow_watch_dead_after_s():", src)


RED_PROOF = [
    {"why": "v3895 (#153, REG-3584) - the bound shrinks back to the sleep slack, so a 90s look is LATE again",
     "file": "tv/control_app.py",
     "find": "    return _SHADOW_WATCH_EVERY_S * 3.0 + _SHADOW_LOOK_BUDGET_S\n",
     "replace": "    return _SHADOW_WATCH_EVERY_S * 3.0\n",
     "matches": 1},
    {"why": "v3895 (#153, REG-3584) - the loop stamps the sleep alone again",
     "file": "tv/control_app.py",
     "find": "_lane_tick('tvd-shadow-watch', every_s=None, dead_after_s=_shadow_watch_dead_after_s())",
     "replace": "_lane_tick('tvd-shadow-watch', _SHADOW_WATCH_EVERY_S)",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
