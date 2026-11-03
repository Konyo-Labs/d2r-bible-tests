# -*- coding: utf-8 -*-
"""v3859 B1 (#230, Claude slice 2) - A STALE ROLLING STAMP NEVER PAINTS THE SYNC BADGE RED.

_sync_facts copied the watcher's rollingSince with no currency check, so ~75 min into any ON AIR session (a hand reel never
rolls over), or after a hand End Session / crash / relaunch, machine_sync said "a reel has rolled N min without a seal" and
the published digest carried the red to every shadow. The watcher's own rule: rolling facts are CURRENT only while
rollingAt == lookedAt, and only a door-"shadow" reel rolls over on the hour. RED_PROOF below.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _enable  # noqa: E402
_enable()
import fixture_tmp  # noqa: E402
fixture_tmp.contain()
import control_app as ca  # noqa: E402

NOW = 1794000000000
SINCE = NOW - 90 * 60 * 1000


class AStaleRollingStampNeverPaintsTheSyncBadgeRed(unittest.TestCase):

    def _facts(self, w):
        old = ca._shadow_watch_stored
        ca._shadow_watch_stored = lambda: dict(w)
        try:
            return ca._sync_facts(NOW)
        finally:
            ca._shadow_watch_stored = old

    def test_a_stale_stamp_is_no_reel_rolling(self):
        f = self._facts({"lookedAt": NOW - 1000, "rollingAt": NOW - 60 * 60 * 1000, "rollingDoor": "shadow",
                         "rollingSince": SINCE, "rotateAfterS": 3600})
        self.assertIsNone(f.get("rollingSince"), "a stale rollingAt < lookedAt was read as a reel still rolling: %r" % f)

    def test_a_hand_reel_never_owes_a_rollover(self):
        f = self._facts({"lookedAt": NOW, "rollingAt": NOW, "rollingDoor": "onair", "rollingSince": SINCE})
        self.assertIsNone(f.get("rollingSince"), "an ON AIR (hand) reel was judged as owing an hourly rollover: %r" % f)

    def test_premise_a_current_shadow_reel_still_counts(self):
        f = self._facts({"lookedAt": NOW, "rollingAt": NOW, "rollingDoor": "shadow", "rollingSince": SINCE})
        self.assertEqual(f.get("rollingSince"), SINCE, "PREMISE: a current shadow reel lost its start: %r" % f)


RED_PROOF = [
    {"why": "v3859 B1 - _sync_facts copies rollingSince with no currency check",
     "file": "tv/control_app.py",
     "find": "        f[\"rollingSince\"] = w.get(\"rollingSince\") if _cur else None\n",
     "replace": "        f[\"rollingSince\"] = w.get(\"rollingSince\")\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
