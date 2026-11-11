#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v3900 (REG-3737) - A RELOOK PROBE AFTER A LAUNCHER SEAL IS NOT A SESSION CUT IN PARTS.

MEASURED 11-11 on the work ALT (SSH, read-only, its shadow_seals.jsonl): 23:00 a reel opens on "Diablo is on screen", 23:13 it
seals as the launcher (185 s of reads with no D2R zone, panel or item), 23:15 the relook opens a reel ("this PC films only
inside a reel, so the relook cannot be one frame"), 23:31 that seals as the launcher, 23:33 the next relook opens one. The
fleet error feed then said "this clock hour has opened 3 shadow reels - one session per hour is the rule, so something is
closing and reopening them". The relook reel is by design on a PC that films only inside a reel (#167: waiting for one frame
there held the door for ever, and his first D2 logo must never be missed), and a part that never showed the game is not a
game part (his 11-11 ruling). REG-1675's watchdog exists for a GAME session cut in parts.

Now the open path counts relook opens apart (relookOpensThisHour) and the watchdog judges the rest, naming the probes.

DRIVEN: the real _shadow_fragment_reading over hour records. RED_PROOF below.
"""
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

import control_app as ca  # noqa: E402

NOW = 1794432000000          # a fixed instant; the hour key is taken from it
F = ca._SHADOW_FRAGMENT_OPENS


def _hour(opens, relooks):
    return {"opensHour": ca._shadow_hour_key(NOW), "opensThisHour": opens, "relookOpensThisHour": relooks}


class ARelookProbeIsNotASessionInParts(unittest.TestCase):

    def test_probes_after_a_launcher_seal_do_not_warn(self):
        """* THE POINT - the ALT's 23:00 hour: one open, then relook probes"""
        r = ca._shadow_fragment_reading(_hour(F, F - 1), now_ms=NOW)
        self.assertIsNone(r["state"], "relook probes after a launcher seal read as a session cut in parts: %r" % r)
        self.assertEqual(r["probes"], F - 1)
        self.assertIn("relook probe", r["line"], "the probes are hidden instead of named")

    def test_baseline_the_same_opens_without_probes_still_warn(self):
        r = ca._shadow_fragment_reading(_hour(F, 0), now_ms=NOW)
        self.assertEqual(r["state"], "warn", r)

    def test_a_real_fragment_still_warns_and_names_its_probes(self):
        r = ca._shadow_fragment_reading(_hour(F + 2, 2), now_ms=NOW)
        self.assertEqual(r["state"], "warn", r)
        self.assertIn("opened %d shadow reels (+2 relook probe(s)" % F, r["line"])

    def test_an_old_hour_counts_nothing(self):
        old = dict(_hour(F + 5, 0), opensHour="1999-01-01 00")
        self.assertIsNone(ca._shadow_fragment_reading(old, now_ms=NOW)["state"])

    def test_the_open_path_counts_a_relook_open_apart(self):
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            code = "\n".join(l.split("#", 1)[0] for l in fh.read().split("\n"))
        self.assertEqual(code.count("+ (1 if ok and _relook_opens else 0)"), 1,
                         "the open path no longer counts a relook open apart")
        self.assertEqual(code.count("opensThisHour=_opens, relookOpensThisHour=_relooks,"), 1,
                         "the hour record no longer carries the relook count")


RED_PROOF = [
    {"why": "REG-3737 - relook probes after a launcher seal count as a session cut in parts again (the work ALT, 11-11)",
     "file": "tv/control_app.py",
     "find": "    if n - probes >= _SHADOW_FRAGMENT_OPENS:\n",
     "replace": "    if n >= _SHADOW_FRAGMENT_OPENS:\n",
     "matches": 1},
    {"why": "REG-3737 - the open path stops counting relook opens",
     "file": "tv/control_app.py",
     "find": "        + (1 if ok and _relook_opens else 0)\n",
     "replace": "        + 0\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
