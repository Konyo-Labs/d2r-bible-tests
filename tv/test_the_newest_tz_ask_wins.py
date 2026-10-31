# -*- coding: utf-8 -*-
"""v3848 - THE NEWEST TERROR-ZONE ASK WINS; A STALE ANSWER NEVER PAINTS OVER A NEWER ONE.

Root cause of the J9 demo flake on the v3847 push (#3): a slow /api/tz fetch begun before a refresh landed after it
and painted the older rotation over the newer one (LIVE NOW lost its why, UP NEXT gained one). Driven in node on
the console's own _tzFetch with a fetch whose answers arrive out of order.
"""
import json
import os
import re
import shutil
import subprocess
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
UI = os.path.join(HERE, "control_ui.html")

DRIVER = r"""
var painted = [], pending = [];
global.document = { getElementById: function () { return null; } };
global.fetch = function () { return new Promise(function (res) { pending.push(res); }); };
function _tzPaint(d) { painted.push(d.current || d.error); }
var _tzNextMissing = false;
%s
(async function () {
  var a = _tzFetch(), b = _tzFetch();          // the old ask, then the refresh
  pending[1]({ ok: true, json: async function () { return { current: 'NEW', next: 'n' }; } });
  await b;
  pending[0]({ ok: true, json: async function () { return { current: 'OLD', next: 'n' }; } });
  await a;
  console.log(JSON.stringify(painted));
})();
"""


class TheNewestTzAskWins(unittest.TestCase):
    def test_a_stale_answer_does_not_paint_over_the_newer_one(self):
        if not shutil.which("node"):
            raise AssertionError("node is not on this machine - this law does not skip")
        src = open(UI, encoding="utf-8").read()
        m = re.search(r"\n  (var _tzSeq = 0;\n  async function _tzFetch\(\) \{.*?\n  \})\n", src, re.S)
        self.assertIsNotNone(m, "_tzFetch moved - this law must find it")
        p = subprocess.run(["node", "-"], input=DRIVER % m.group(1), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        self.assertEqual(p.returncode, 0, p.stderr[-800:])
        self.assertEqual(json.loads(p.stdout.strip().splitlines()[-1]), ["NEW"],
                         "an older /api/tz answer painted after the newer one")

    def test_a_missing_node_fails_the_law(self):
        with mock.patch("shutil.which", return_value=None):
            try:
                self.test_a_stale_answer_does_not_paint_over_the_newer_one()
            except AssertionError as e:
                self.assertIn("does not skip", str(e))
                return
            except unittest.SkipTest:
                self.fail("a missing node skipped this law; a skip exits 0")
        self.fail("a missing node ran the law")


RED_PROOF = [
    {"why": "v3848 - the stale answer paints",
     "file": "control_ui.html",
     "find": "      if (mine !== _tzSeq) return;   // a newer ask is in flight or has painted - this answer is stale\n",
     "replace": "",
     "matches": 1},
    {"why": "v3849 - no node skips this law and a skip exits 0",
     "file": "test_the_newest_tz_ask_wins.py",
     "find": "            raise AssertionError(\"node is not on this machine - this law does not skip\")\n",
     "replace": "            self.skipTest(\"no node here\")\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
