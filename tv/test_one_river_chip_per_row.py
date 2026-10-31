# -*- coding: utf-8 -*-
"""v3849 — a fleet row draws one river chip.

A stuck list and key "starting", still inside the boot window, used to draw "river stuck" and
"river · starting". It now draws one chip, "river stuck · proof check pending", and keeps the
stuck tip. An empty stuck list still says only "river · starting". Past the boot window a stuck
row says "river stuck" and "river UNKNOWN", never the pending chip and never "river · starting".
"""
import datetime
import io
import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
from cb_node_harness import NODE  # noqa: E402

UI = os.path.join(HERE, "control_ui.html")
NOW = 1700000000000
WHY = ("  function _fleetStuckWhy(list, label){\n", "join('  |  ');\n  }\n")
CHIP = ("  var _fleetStuckChip = function (m, nowMs) {\n", "    return bits.join('');\n  };\n")
AGO = ("  var _fleetAgo = function (sec) {\n", "  };\n")
BOOT = ("  var FLEET_BOOT_WINDOW_S = 15 * 60;\n", "  };\n")
STUCK = [{"station": "PRINTER", "n": 3, "oldestS": 40 * 3600, "why": "vault lane: owes 1"}]
START = {"census": None, "key": "starting", "blind": None}


def _need_node():
    if not NODE:
        raise AssertionError("node is not on this machine - this gate does not skip")
    return NODE


def _cut(src, start, end):
    if src.count(start) != 1:
        raise AssertionError("anchor %r matched %d times" % (start.strip()[:48], src.count(start)))
    i = src.index(start)
    # BOOT's end anchor "  };\n" is the age-text closer, the first one after the boot window.
    # AGO's end is the first closer after _fleetAgo. Both are the function's own closer.
    fn = src[i:src.index(end, i + len(start)) + len(end)]
    if fn.count("{") != fn.count("}"):
        raise AssertionError("the cut %r is not a whole function (%d/%d)" % (start.strip()[:40], fn.count("{"), fn.count("}")))
    return fn


def _html(heart, stuck, age_s):
    with io.open(UI, encoding="utf-8") as fh:
        src = fh.read()
    if age_s is None:
        stamp = ""
    else:
        stamp = datetime.datetime.fromtimestamp(
            NOW / 1000.0 - age_s, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    row = {"t": stamp, "system": {"river": {"stuck": stuck, "heart": heart}}}
    # BOOT includes _fleetAgeTxt, whose closer is the first "  };" after FLEET_BOOT_WINDOW_S only if
    # nothing between them ends a function the same way. The cut's brace check refuses a short slice.
    boot = src[src.index(BOOT[0]):src.index("  var _fleetSay = function (k) {")]
    if boot.count("{") != boot.count("}"):
        raise AssertionError("the boot helpers are not a whole slice")
    js = (
        "var window = {};\n"
        "function escC(x){ return String(x).replace(/&/g,'&amp;').replace(/\"/g,'&quot;')"
        ".replace(/</g,'&lt;').replace(/>/g,'&gt;'); }\n%s\n%s\n%s\n%s\n"
        "console.log(JSON.stringify(_fleetStuckChip(%s, %d)));"
    ) % (_cut(src, AGO[0], AGO[1]), boot, _cut(src, WHY[0], WHY[1]), _cut(src, CHIP[0], CHIP[1]),
         json.dumps(row), NOW)
    r = subprocess.run([_need_node(), "-"], input=js, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise AssertionError("the cut functions did not run in node: %s" % r.stderr[-600:])
    return json.loads(r.stdout.strip().splitlines()[-1])


class TestOneRiverChipPerRow(unittest.TestCase):
    def test_a_stuck_row_still_booting_draws_one_chip_and_keeps_the_tip(self):
        html = _html(START, STUCK, 60)
        self.assertEqual(html.count("fleet-riverstuck"), 1)
        self.assertEqual(html.count("fleet-riverunk"), 0)
        self.assertIn("river stuck \u00b7 proof check pending", html)
        self.assertNotIn("river \u00b7 starting", html)
        self.assertNotIn(">river stuck<", html)
        self.assertIn("PRINTER 3", html)
        self.assertIn("vault lane: owes 1", html)

    def test_an_empty_stuck_list_still_says_only_starting(self):
        for stuck in ([], None):
            html = _html(START, stuck, 60)
            self.assertIn("river \u00b7 starting", html)
            self.assertNotIn("proof check pending", html)
            self.assertEqual(html.count("fleet-riverunk"), 1, stuck)
            self.assertEqual(html.count("fleet-riverstuck"), 0, stuck)

    def test_a_stuck_row_past_the_boot_window_is_not_pending(self):
        for age in (int(5.5 * 3600), None):
            html = _html(START, STUCK, age)
            self.assertIn(">river stuck<", html, age)
            self.assertIn("river UNKNOWN", html, age)
            self.assertNotIn("proof check pending", html, age)
            self.assertNotIn("river \u00b7 starting", html, age)
            self.assertIn("PRINTER 3", html)

    def test_a_stuck_row_that_is_not_starting_stays_river_stuck(self):
        html = _html({"census": "current", "key": "current", "blind": 0}, STUCK, 60)
        self.assertIn(">river stuck<", html)
        self.assertNotIn("proof check pending", html)
        self.assertNotIn("river \u00b7 starting", html)
        self.assertEqual(html.count("fleet-riverstuck"), 1)

    def test_the_red_proof_finds_match_once(self):
        for proof in RED_PROOF:
            with io.open(os.path.join(ROOT, proof["file"]), encoding="utf-8") as fh:
                body = fh.read()
            self.assertEqual(body.count(proof["find"]), proof["matches"], proof["why"])
            self.assertNotEqual(proof["find"], proof["replace"])


RED_PROOF = [
    {"why": "a stuck boot window draws river stuck and river · starting again",
     "file": "tv/control_ui.html",
     "find": "      if (!(Array.isArray(sk) && sk.length)) bits.push('<span class=\"fleet-riverunk\"",
     "replace": "      if (true) bits.push('<span class=\"fleet-riverunk\"",
     "matches": 1},
    {"why": "the one chip loses the pending words and reads as a plain river stuck",
     "file": "tv/control_ui.html",
     "find": "      var _stuckLabel = _pending ? 'river stuck \\u00b7 proof check pending' : 'river stuck';\n",
     "replace": "      var _stuckLabel = 'river stuck';\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
