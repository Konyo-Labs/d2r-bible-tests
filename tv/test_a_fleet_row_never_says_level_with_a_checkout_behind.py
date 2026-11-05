# -*- coding: utf-8 -*-
"""v3864 (GrokBot Batch B 1-2, #230 6655906382; the Grok CLI re-read it, 6655933519) - ONE FLEET ROW, ONE ANSWER ABOUT HOW
FAR BEHIND IT IS.

Measured in /api/fleet at 12:11-12:42 Israel time: Dean's row said ver v3860 and lag {behind 0, "level with what origin
publishes"} while the SAME row's pull said head e1fd8a98 (v3859), behind 9, local tracked edits (M tv/control_app.py,
M tv/tv_diablo.py). fleet_lag compares only the version a PC says it runs, so the card showed Dean current. GrokBot's row
held the opposite split: pull behind 0 (an 8-day-old self-report) beside lag 45.

Now fleet_annotate_lag asks fleet_lag_vs_pull: a checkout behind origin is never level (behind None, checkoutBehind N, the
reason names both reports, local edits said), and the card draws "checkout N commits behind"; a level pull beside a counted
lag is said to be the older report. Fixtures only. RED_PROOF below.
"""
import io
import json
import os
import re
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import control_app as CA  # noqa: E402

DEAN_PULL = {"head": "e1fd8a98c0ffee00", "behind": 9, "can": False, "why": "local tracked edits",
             "porcelain": "M tv/control_app.py | M tv/tv_diablo.py"}
GROK_PULL = {"head": "892d4d09", "behind": 0, "can": True, "why": "level with origin"}


def _fleet(rows):
    return {"me": "Konyo · Mac", "publishedVer": "v3860", "online": rows, "offline": []}


class OneRowOneAnswer(unittest.TestCase):

    def test_a_checkout_behind_origin_is_never_level(self):
        out = CA.fleet_annotate_lag(_fleet([{"machine": "Dean", "ver": "v3860", "pull": DEAN_PULL}]))
        lag = out["online"][0]["lag"]
        self.assertIsNone(lag["behind"], "Dean's row says level while his checkout is 9 behind: %r" % lag)
        self.assertEqual(lag.get("checkoutBehind"), 9)
        self.assertIs(lag.get("edits"), True, "the local edits his pull reported are not said")
        self.assertIn("9 commit(s) behind origin", lag["why"])
        self.assertIn("v3860", lag["why"], "the reason does not name the version the PC says it runs")

    def test_a_level_pull_beside_a_counted_lag_is_the_older_report(self):
        out = CA.fleet_annotate_lag(_fleet([{"machine": "GrokBot", "ver": "v3815", "pull": GROK_PULL}]))
        lag = out["online"][0]["lag"]
        self.assertEqual(lag["behind"], 45, "PREMISE: the version count moved")
        self.assertIs(lag.get("pullStale"), True, "the row holds 'level' and '45 behind' with nothing saying which is old")
        self.assertIn("older report", lag["why"])

    def test_two_reports_that_agree_are_left_alone(self):
        for ver, pull in (("v3860", {"behind": 0}), ("v3858", {"behind": 3}), ("v3860", None), ("v3860", {"behind": None})):
            out = CA.fleet_annotate_lag(_fleet([{"machine": "ALT", "ver": ver, "pull": pull}]))
            lag = out["online"][0]["lag"]
            self.assertNotIn("checkoutBehind", lag, (ver, pull))
            self.assertNotIn("pullStale", lag, (ver, pull))
        self.assertIsNone(CA.fleet_lag_vs_pull(0, "v3860", {"behind": True}), "a boolean is read as a commit count")

    def test_the_card_says_the_checkout_is_behind(self):
        ui = io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()
        i = ui.index("      var _lagTxt = function (m) {")
        j = ui.index("\n      };\n", i) + len("\n      };\n")
        prog = ("var escC = function (s) { return String(s); };\n" + ui[i:j]
                + "process.stdout.write(JSON.stringify([_lagTxt(%s), _lagTxt(%s)]));" % (
                    json.dumps({"ver": "v3860", "lag": {"behind": None, "checkoutBehind": 9, "edits": True, "why": "x"}}),
                    json.dumps({"ver": "v3860", "lag": {"behind": None, "why": "unknown here"}})))
        r = subprocess.run(["node", "-"], input=prog, capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-600:])
        split, unk = json.loads(r.stdout)
        self.assertIn("checkout 9 commits behind", split, "the card does not say Dean's checkout is behind: %r" % split)
        self.assertIn("local edits", split)
        self.assertNotIn("lag unknown", split)
        self.assertIn("lag unknown", unk, "PREMISE: an unknown lag no longer says so")


RED_PROOF = [
    {"why": "v3864 - a checkout 9 behind reads level again because its version stamp says so",
     "file": "tv/control_app.py",
     "find": "    if behind == 0 and pb > 0:\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "v3864 - the row's lag never asks its pull report",
     "file": "tv/control_app.py",
     "find": "                if _split:\n                    m[\"lag\"].update(_split)\n",
     "replace": "                if False:\n                    m[\"lag\"].update(_split)\n",
     "matches": 1},
    {"why": "v3864 - 'level' and '45 behind' sit on one row with nothing saying which report is old",
     "file": "tv/control_app.py",
     "find": "    if isinstance(behind, int) and behind > 0 and pb == 0:\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "v3864 - the card draws 'lag unknown' for a checkout it knows is behind",
     "file": "tv/control_ui.html",
     "find": "        if (lg.behind == null && typeof lg.checkoutBehind === 'number' && lg.checkoutBehind > 0) {\n",
     "replace": "        if (false) {\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
