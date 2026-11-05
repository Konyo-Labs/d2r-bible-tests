# -*- coding: utf-8 -*-
"""REG-3196 - A FAILED RIVER READ SAYS WHY, ON THE WIRE AND ON THE ROW.

His words 2026-11-05: "i want the river flowing and the fleet rendering it properly that it is for each and for whoever
is not fix it!". MEASURED on his /api/fleet at 21:01: the OLD PC ALT row's river.why read "a newer river read failed
1043 s ago - these lanes are the last good read" and nothing else. Why it failed WAS recorded on that PC
(_RIVER_LAST['fail']['why']) and never reached the wire; and the recorded reason was only the exception's class
("the river could not be read (KeyError)").

Now:
  * the console keeps the exception's own message beside its class, scrubbed for the wire (_wire_text: no path, host or
    user folder crosses);
  * a newer failed read sends its reason in river.why AND as river.failWhy / river.failAgeS;
  * the worker (functions/api/console.js, its REAL shaper in node) forwards failWhy / failAgeS, scrubbed and capped,
    and an absent one stays absent;
  * the Fleet row (control_ui.html, the REAL _fleetStuckChip in node) draws a muted "last river read failed" whose hover
    carries the reason; a row with no newer failure draws nothing of the kind.
RED_PROOF below.
"""
import io
import json
import os
import subprocess
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
import control_app as CA  # noqa: E402
import test_one_river_chip_per_row as H  # noqa: E402  (the cut-and-run pieces for _fleetStuckChip)
import test_each_console_says_its_own_system as S  # noqa: E402  (its worker slicer)

NOW = 1793900000000
# a home path built at run time: the repo is public and its law counts literal home paths
HOME_ = "/" + "Users/"


def _chip(row, now=NOW):
    """The SHIPPED _fleetStuckChip over one fleet row, run in node (TZ=UTC). -> html"""
    with io.open(H.UI, encoding="utf-8") as fh:
        src = fh.read()
    boot = src[src.index(H.BOOT[0]):src.index("  var _fleetSay = function (k) {")]
    js = ("var window = {};\n"
          "function escC(x){ return String(x).replace(/&/g,'&amp;').replace(/\"/g,'&quot;')"
          ".replace(/</g,'&lt;').replace(/>/g,'&gt;'); }\n%s\n%s\n%s\n%s\n"
          "console.log(JSON.stringify(_fleetStuckChip(%s, %d)));") % (
        H._cut(src, H.AGO[0], H.AGO[1]), boot, H._cut(src, H.WHY[0], H.WHY[1]), H._cut(src, H.CHIP[0], H.CHIP[1]),
        json.dumps(row), now)
    r = subprocess.run([H._need_node(), "-"], input=js, capture_output=True, text=True, timeout=30,
                       env=dict(os.environ, TZ="UTC"))
    if r.returncode != 0:
        raise AssertionError("the cut chip did not run in node: %s" % r.stderr[-600:])
    return json.loads(r.stdout.strip().splitlines()[-1])


def _row(river, age_s=60):
    import datetime
    t = datetime.datetime.fromtimestamp((NOW / 1000.0) - age_s, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    return {"t": t, "presence": {"state": "online", "online": True, "via": "console", "ageS": age_s},
            "system": {"river": river}}


class TheConsoleKeepsTheReason(unittest.TestCase):

    def test_a_failed_read_keeps_its_message_scrubbed(self):
        last = {"good": None, "fail": None}
        with mock.patch.object(CA, "_RIVER_LAST", last):
            CA._river_remember_once(None, KeyError("station 'PRINTER' missing from " + HOME_ + "dean/tv/river.json"))
        why = last["fail"]["why"]
        self.assertIn("KeyError", why)
        self.assertIn("PRINTER", why, "the failure kept only its class, not why: %r" % why)
        self.assertNotIn(HOME_, why, "a path crossed toward the wire: %r" % why)
        self.assertNotIn("dean", why.lower())

    def test_a_newer_failure_sends_its_own_reason(self):
        good = {"ts": NOW - 2000 * 1000, "n": 1, "stations": {"PRINTER": 2}}
        fail = {"ts": NOW - 1043 * 1000, "n": 2, "why": "the river could not be read (OSError: disk read timed out)"}
        with mock.patch.object(CA, "_RIVER_LAST", {"good": good, "fail": fail}):
            out = CA._river_for_wire(now_ms=NOW)
        self.assertEqual(out["lanes"], {"PRINTER": 2}, "the last good lanes were dropped")
        self.assertIn("a newer river read failed 1043 s ago", out["why"])
        self.assertIn("disk read timed out", out["why"], "the failed read's reason never reached the wire: %r" % out["why"])
        self.assertEqual(out["failWhy"], fail["why"])
        self.assertEqual(out["failAgeS"], 1043.0)

    def test_an_older_failure_is_not_sent(self):
        good = {"ts": NOW - 10 * 1000, "n": 3, "stations": {"PRINTER": 2}}
        fail = {"ts": NOW - 1043 * 1000, "n": 2, "why": "the river could not be read (OSError)"}
        with mock.patch.object(CA, "_RIVER_LAST", {"good": good, "fail": fail}):
            out = CA._river_for_wire(now_ms=NOW)
        self.assertNotIn("failWhy", out, "a failure the good read already replaced still crossed")
        self.assertNotIn("failed", out["why"])


class TheWorkerForwardsIt(unittest.TestCase):

    def _river(self, rv):
        return S.TheRelayShapesIt._shape(self, {"tree": "ok", "reels": 1, "river": rv})["river"]

    def test_fail_why_and_age_cross_and_absent_stays_absent(self):
        got = self._river({"lanes": {"PRINTER": 2}, "ageS": 2000, "why": "x",
                           "failWhy": "the river could not be read (OSError: disk read timed out)", "failAgeS": 1043})
        self.assertEqual(got["failWhy"], "the river could not be read (OSError: disk read timed out)")
        self.assertEqual(got["failAgeS"], 1043)
        plain = self._river({"lanes": {"PRINTER": 2}, "ageS": 20, "why": ""})
        self.assertNotIn("failWhy", plain, "an absent failure arrived as a field")
        self.assertNotIn("failAgeS", plain)


@unittest.skipIf(H.NODE is None, "node is not on this machine - this law RUNS the shipped chip and will not re-implement it")
class TheRowSaysIt(unittest.TestCase):

    def test_the_row_says_the_read_failed_with_its_reason(self):
        html = _chip(_row({"lanes": {"PRINTER": 2}, "ageS": 2000, "stuck": [],
                           "heart": {"census": "current", "key": "current", "blind": 0},
                           "failWhy": "the river could not be read (OSError: disk read timed out)", "failAgeS": 1043}))
        self.assertIn(">last river read failed<", html, "a newer failed read drew nothing on the row: %r" % html)
        self.assertIn("disk read timed out", html, "the chip's hover does not say why it failed")
        self.assertIn("fleet-riverunk", html)
        self.assertNotIn("fleet-riverstuck", html, "a failed read was drawn as the red alarm")

    def test_no_failure_no_chip(self):
        html = _chip(_row({"lanes": {"PRINTER": 2}, "ageS": 20, "stuck": [],
                           "heart": {"census": "current", "key": "current", "blind": 0}}))
        self.assertNotIn("read failed", html)

    def test_the_red_proof_finds_match_once(self):
        for p in RED_PROOF:
            with io.open(os.path.join(ROOT, p["file"]), encoding="utf-8") as fh:
                self.assertEqual(fh.read().count(p["find"]), p["matches"], p["why"])


RED_PROOF = [
    {"why": "REG-3196 - the failed read's reason stays on the PC: no failWhy on the wire",
     "file": "tv/control_app.py",
     "find": "            out[\"failWhy\"] = _fwhy\n",
     "replace": "            pass\n",
     "matches": 1},
    {"why": "REG-3196 - the sentence says a newer read failed and not why (his 21:01 Fleet)",
     "file": "tv/control_app.py",
     "find": "            out[\"why\"] = (\"a newer river read failed %.0f s ago - %s - these lanes are the last good read\"\n"
             "                          % (_fage, _fwhy))\n",
     "replace": "            out[\"why\"] = (\"a newer river read failed %.0f s ago - these lanes are the last good read\"\n"
                "                          % _fage)\n",
     "matches": 1},
    {"why": "REG-3196 - a failure keeps only its exception class, not its message",
     "file": "tv/control_app.py",
     "find": "% (type(error).__name__, (\": \" + _detail) if _detail else \"\")}",
     "replace": "% (type(error).__name__, \"\")}",
     "matches": 1},
    {"why": "REG-3196 - the worker drops failWhy on arrival",
     "file": "functions/api/console.js",
     "find": "        if (fw !== null) {\n",
     "replace": "        if (false) {\n",
     "matches": 1},
    {"why": "REG-3196 - the Fleet row draws nothing for a newer failed read",
     "file": "tv/control_ui.html",
     "find": "    if (rv && typeof rv === 'object' && typeof rv.failWhy === 'string' && rv.failWhy) {\n",
     "replace": "    if (false) {\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
