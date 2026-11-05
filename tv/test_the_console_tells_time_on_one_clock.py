# -*- coding: utf-8 -*-
"""v3864 (GrokBot Batch A 4, #230 6656116697) - THE CONSOLE TELLS TIME ON ONE CLOCK.

GrokBot, v3860 at five window sizes: the header clock read 12:49:45 (built 24-hour from getHours) while "updated 05:10 PM"
(#tz-updated) and the forge's "scanned 5:10:05 PM" (#hd-forge-when, toLocaleTimeString) sat on the same screen. 26 stamps on
the page asked toLocaleTimeString() and got the PC's locale default; #214 had fixed one of them by hand. Now the page's first
script makes a time with no hour12 / hourCycle of its own 24-hour, and a caller that names hour12 keeps its choice. The page's
own shim is run in node. RED_PROOF below.
"""
import io
import json
import os
import re
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
UI = os.path.join(HERE, "control_ui.html")
START = "/* v3864 (GrokBot Batch A 4, #230 6656116697) - ONE CLOCK ON THE CONSOLE."


def _shim():
    s = io.open(UI, encoding="utf-8").read()
    i = s.index(START)
    j = s.index("\n})();\n", i) + len("\n})();\n")   # the shim's own IIFE: it shares its block with the icon-tab helper
    assert j < s.index("</script>", i), "the shim's IIFE does not close inside its block"
    return s, s[i:j]


class TheConsoleTellsTimeOnOneClock(unittest.TestCase):

    def test_the_shim_runs_before_any_other_script(self):
        s, _sh = _shim()
        first = s.index("<script>")
        self.assertLess(first, s.index(START), "PREMISE")
        self.assertEqual(s.index("<script>\n" + START), first, "the one-clock shim is not the page's first script")

    def test_a_bare_time_is_24_hour_and_a_named_choice_is_kept(self):
        _s, sh = _shim()
        prog = sh + """
var d = new Date(2026, 10, 5, 17, 10, 5);
process.stdout.write(JSON.stringify([d.toLocaleTimeString(), d.toLocaleTimeString([], {hour: 'numeric', minute: '2-digit'}),
  d.toLocaleTimeString('en-US'), d.toLocaleTimeString([], {hour12: true})]));"""
        r = subprocess.run(["node", "-"], input=prog, capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-500:])
        bare, hm, us, named = json.loads(r.stdout)
        for t in (bare, hm, us):
            self.assertIsNone(re.search(r"AM|PM", t), "a stamp with no choice of its own prints 12-hour: %r" % t)
            self.assertTrue(t.startswith("17:10"), t)
        self.assertRegex(named, r"PM", "a caller that names hour12 lost its choice: %r" % named)

    def test_the_header_clock_is_still_24_hour(self):
        s, _sh = _shim()
        self.assertIn("$('clock-t').textContent = p(d.getHours())+':'+p(d.getMinutes())+':'+p(d.getSeconds());", s)


RED_PROOF = [
    {"why": "v3864 - a bare toLocaleTimeString prints the locale's AM/PM beside the 24-hour header again",
     "file": "tv/control_ui.html",
     "find": "        if (o.hour12 === undefined && o.hourCycle === undefined) o.hourCycle = 'h23';\n",
     "replace": "",
     "matches": 1},
    {"why": "v3864 - a caller's own hour12 is overridden",
     "file": "tv/control_ui.html",
     "find": "        if (o.hour12 === undefined && o.hourCycle === undefined) o.hourCycle = 'h23';\n",
     "replace": "        o.hour12 = false;\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
