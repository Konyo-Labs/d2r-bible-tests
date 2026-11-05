# -*- coding: utf-8 -*-
"""v3864 (GrokBot Batch B 6, #230 6655906382; re-read by the Grok CLI, 6655933519) - THE VAULT LANE SAYS HOW OLD ITS LAST
READ IS, NOT ONLY HOW OLD ITS CACHE IS.

/api/status vaultAutoread read {stale: false, ageMs ~2,000} on the Mac while its lastTs was 2026-11-01 13:51 and 8 reels
were owed: `stale` and `ageMs` are stamped by the 3-second status cache, so a lane that had read nothing in 4 days looked
fresh. The answer now carries lastReadAgeS (seconds since the last real read; None when it never read) and readStale (True
when reels are owed and none was read for VAULT_READ_STALE_S or ever; False when nothing is owed; None when the owed count
could not be read). lastTs is epoch MILLISECONDS. Fixtures only. RED_PROOF below.
"""
import inspect
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import control_app as CA  # noqa: E402

NOW = 1793900000.0
FOUR_DAYS_AGO_MS = int((NOW - 4 * 86400) * 1000)


class AVaultReadSaysItsOwnAge(unittest.TestCase):

    def test_four_days_without_a_read_while_reels_are_owed_is_stale(self):
        self.assertEqual(CA._vault_last_read_age_s(FOUR_DAYS_AGO_MS, NOW), 4 * 86400)
        self.assertIs(CA._vault_read_stale(FOUR_DAYS_AGO_MS, ["r"] * 8, NOW), True,
                      "8 owed and no read in 4 days reads fresh")

    def test_a_recent_read_and_an_empty_queue_are_not_stale(self):
        self.assertIs(CA._vault_read_stale(int((NOW - 60) * 1000), ["r"], NOW), False)
        self.assertIs(CA._vault_read_stale(FOUR_DAYS_AGO_MS, [], NOW), False, "nothing owed is called stale")

    def test_never_read_and_unknown_are_said_as_such(self):
        self.assertIsNone(CA._vault_last_read_age_s(0, NOW), "a lane that never read has an age of 0, not UNKNOWN")
        self.assertIs(CA._vault_read_stale(0, ["r"], NOW), True, "owed reels and no read ever reads fresh")
        self.assertIsNone(CA._vault_read_stale(FOUR_DAYS_AGO_MS, None, NOW), "an unread owed count is called fresh or stale")
        self.assertIsNone(CA._vault_last_read_age_s(True, NOW), "a boolean read as a timestamp")

    def test_the_status_answer_carries_both(self):
        src = inspect.getsource(CA._vault_autoread_state)
        self.assertIn('"lastReadAgeS": _vault_last_read_age_s(d.get("lastTs")),', src)
        self.assertIn('"readStale": _vault_read_stale(d.get("lastTs"), owed),', src)


RED_PROOF = [
    {"why": "v3864 - a lane with 8 owed and no read in 4 days reads fresh again",
     "file": "tv/control_app.py",
     "find": "    return True if age is None else age >= VAULT_READ_STALE_S\n",
     "replace": "    return False\n",
     "matches": 1},
    {"why": "v3864 - nothing owed is called stale",
     "file": "tv/control_app.py",
     "find": "    if not owed:\n        return False\n    age = _vault_last_read_age_s(last_ts, now)\n",
     "replace": "    age = _vault_last_read_age_s(last_ts, now)\n",
     "matches": 1},
    {"why": "v3864 - the status answer drops the read's own staleness",
     "file": "tv/control_app.py",
     "find": "                \"readStale\": _vault_read_stale(d.get(\"lastTs\"), owed),\n",
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
