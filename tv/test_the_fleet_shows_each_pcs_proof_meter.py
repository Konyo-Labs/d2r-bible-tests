# -*- coding: utf-8 -*-
"""v3862 (item 10) - EACH PC'S FLEET ROW SAYS HOW MANY LAWS IT STILL OWES, HOW FAST IT IS PROVING, AND WHEN IT WILL BE DONE.

GrokBot's v3860 pass named the proof meter as missing: a PC's row said "proof out of date" and nothing about whether it
was moving. The console reads its own self-prove `owed` on every beacon, keeps six hours of readings and sends
owed / ratePerH / etaS beside the census; the worker keeps them (and the console's own why-sentence, which it had sent
since v3855 C6 and the worker DROPPED on arrival - found building this); the card draws them as facts on `proved`.
Pinned:
  · under 20 minutes of readings there is no rate ("measuring"), never a guess; a measured 0 is "not moving";
  · a version that RAISES owed starts the readings again (not negative progress);
  · UNKNOWN owed adds nothing; a current census owes 0 and draws no meter;
  · the worker keeps the four fields and they are not news (no extra KV write);
  · the card's words, driven in node.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import control_app as CA  # noqa: E402

NODE = shutil.which("node")
T0 = 1_800_000_000_000
MIN = 60_000


def _node(js):
    r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=60)
    if r.returncode != 0:
        raise AssertionError("node could not run the shipped code - UNKNOWN, not passing: %s" % r.stderr[:400])
    return json.loads(r.stdout.strip().splitlines()[-1])


class TheMeter(unittest.TestCase):

    def test_no_rate_before_twenty_minutes_of_readings(self):
        s, rate, eta = CA.proof_meter([], T0, 120)
        s, rate, eta = CA.proof_meter(s, T0 + 10 * MIN, 110)
        self.assertIsNone(rate, "a rate was claimed from ten minutes of readings")
        self.assertIsNone(eta)

    def test_the_rate_and_the_time_left(self):
        s, _r, _e = CA.proof_meter([], T0, 120)
        s, rate, eta = CA.proof_meter(s, T0 + 60 * MIN, 90)
        self.assertEqual(rate, 30.0)
        self.assertEqual(eta, 3 * 3600, "90 owed at 30/h is three hours")

    def test_a_measured_standstill_is_zero_with_no_eta(self):
        s, _r, _e = CA.proof_meter([], T0, 50)
        s, rate, eta = CA.proof_meter(s, T0 + 40 * MIN, 50)
        self.assertEqual(rate, 0.0)
        self.assertIsNone(eta)

    def test_a_version_that_owes_more_starts_the_readings_again(self):
        s, _r, _e = CA.proof_meter([], T0, 10)
        s, _r, _e = CA.proof_meter(s, T0 + 60 * MIN, 5)
        s, rate, eta = CA.proof_meter(s, T0 + 61 * MIN, 140)
        self.assertEqual(s, [(T0 + 61 * MIN, 140)], "the jump to 140 was read against the old readings")
        self.assertIsNone(rate)

    def test_unknown_owed_adds_nothing_and_old_readings_age_out(self):
        s, _r, _e = CA.proof_meter([(T0, 100)], T0 + 5 * MIN, None)
        self.assertEqual(s, [(T0, 100)])
        s, _r, _e = CA.proof_meter([(T0, 100)], T0 + CA.PROOF_METER_WINDOW_MS + MIN, 40)
        self.assertEqual(s, [(T0 + CA.PROOF_METER_WINDOW_MS + MIN, 40)], "a reading older than the window was kept")

    def test_the_beacon_carries_it(self):
        import inspect
        src = inspect.getsource(CA._river_for_wire)
        self.assertIn("out[\"heart\"].update(owed=_owed, ratePerH=_rate, etaS=_eta)", src)


def _between(src, start, end):
    i = src.index(start)
    j = src.index(end, i + len(start))
    return src[i:j + len(end)]


@unittest.skipIf(NODE is None, "node is absent - the worker and the card are UNMEASURED, not passing")
class TheWorkerAndTheCard(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with io.open(os.path.join(ROOT, "functions", "api", "console.js"), encoding="utf-8") as fh:
            cls.worker = fh.read()
        with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
            cls.ui = fh.read()

    def test_the_worker_keeps_the_meter_and_the_why(self):
        import worker_source as _ws
        fn = _between(self.worker, "    system: (function (s) {", "    })(body.system),")
        fn = "(" + fn[len("    system: "):-len("(body.system),")] + ")"
        body = {"tree": "ok", "reels": 1, "river": {"lanes": {}, "ageS": 1, "why": "x", "heart": {
            "census": "stale", "key": "slicing", "blind": 0, "owed": 90, "ratePerH": 30.0, "etaS": 10800,
            "why": "census stale; lane: proving a slice at a time; 90 law(s) owed"}}}
        got = _node(_ws.prelude(self.worker) + "var shape = %s; console.log(JSON.stringify(shape(%s)));"
                    % (fn, json.dumps(body)))["river"]["heart"]
        self.assertEqual((got["owed"], got["ratePerH"], got["etaS"]), (90, 30.0, 10800))
        self.assertIn("90 law(s) owed", got["why"], "the console's why is still dropped on arrival")

    def test_the_meter_is_not_news(self):
        news = _between(self.worker, "    const heartWord = h ? [", "] : null;")
        for k in ("owed", "ratePerH", "etaS", "why"):
            self.assertNotIn("h." + k, news, "%s made every slice a KV write" % k)

    def _facts(self, hs):
        fn = _between(self.ui, "  var _proofMeterFacts = function (hs) {", "\n  };")
        return _node("%s; console.log(JSON.stringify(_proofMeterFacts(%s)));" % (fn, json.dumps(hs)))

    def test_the_cards_words(self):
        self.assertEqual(self._facts({"census": "stale", "owed": 90, "ratePerH": 30, "etaS": 10800}),
                         ["90 laws owed", "~30/h", "~3 h left"])
        self.assertEqual(self._facts({"census": "stale", "owed": 4, "ratePerH": 2.5, "etaS": 5760}),
                         ["4 laws owed", "~2.5/h", "~1.6 h left"])
        self.assertEqual(self._facts({"census": "missing", "owed": 1, "ratePerH": 12, "etaS": 300}),
                         ["1 law owed", "~12/h", "~5 min left"])
        self.assertEqual(self._facts({"census": "stale", "owed": 50, "ratePerH": 0, "etaS": None}),
                         ["50 laws owed", "not moving"])
        self.assertEqual(self._facts({"census": "stale", "owed": 50, "ratePerH": None}), ["50 laws owed", "measuring"])
        self.assertEqual(self._facts({"census": "current", "owed": 0}), [])
        self.assertEqual(self._facts({"census": "stale"}), [], "an older build drew a meter it never sent")

    def test_the_proved_part_draws_them(self):
        part = _between(self.ui, "      var hb = (typeof hs.blind === 'number')", "}));")
        self.assertIn(".concat(_proofMeterFacts(hs))", part)
        self.assertIn("(hs.why ? ' - ' + String(hs.why) : '')", part)


RED_PROOF = [
    {"why": "v3862 - a rate is claimed from a few minutes of readings",
     "file": "tv/control_app.py",
     "find": "    if span < PROOF_METER_MIN_SPAN_MS:\n        return keep, None, None\n",
     "replace": "",
     "matches": 1},
    {"why": "v3862 - a version that owes more reads as proving backwards",
     "file": "tv/control_app.py",
     "find": "    if keep and owed > keep[-1][1]:\n        keep = []\n",
     "replace": "",
     "matches": 1},
    {"why": "v3862 - the worker drops the meter on arrival",
     "file": "functions/api/console.js",
     "find": "            owed: whole(rv.heart.owed, 100000),\n",
     "replace": "",
     "matches": 1},
    {"why": "v3862 - a measured standstill reads as 'measuring' (nobody sees the PC is stuck)",
     "file": "tv/control_ui.html",
     "find": "    } else if (hs.ratePerH === 0) {\n      f.push('not moving');\n",
     "replace": "    } else if (false) {\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
