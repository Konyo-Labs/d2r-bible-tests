# -*- coding: utf-8 -*-
"""v3885 (his 11-08 on the Fleet: "the fleet is saying imprting 3min.. and 30hours and 168 hours? ... shouldnt be 168 hours lol..
and 30hours also sounds crazy") - A PROVER THAT IS WAITING HAS NO FINISH TIME.

MEASURED 11-08 ~15:15 (the Mac's /api/fleet, then each PC read-only over SSH): the work ALT owed 54 laws at 1.7 an hour ->
"proving 54 ~31.8 h", its lane key 'busy' (77% busy: 4 cores, 2 GB free, Boosteroid - his game - on top), and a proof starts
only when the PC is idle; the OLD ALT owed 108 at 0.6 an hour -> "~175.3 h", its key 'aside-cooldown' (a proof standing aside
for GitHub's import). Each hour figure divided by a rate measured while the prover mostly waited. Now, while the lane's key
says it waits (busy / playing / stood-aside / aside-cooldown / backoff / low-memory), the meter and the row name the wait;
a running prover keeps its measured time. Runs the console's own _proofMeterFacts in node. RED_PROOF below.
"""
import io
import json
import os
import re
import shutil
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
UI = os.path.join(HERE, "control_ui.html")
NODE = shutil.which("node")


def _cut(src, start, end):
    if src.count(start) != 1:
        raise AssertionError("cut start %r occurs %d times - re-point this law" % (start[:60], src.count(start)))
    i = src.index(start)
    return src[i:src.index(end, i + len(start)) + len(end)]


@unittest.skipUnless(NODE, "node is required to run the console's own meter")
class AWaitingProverHasNoFinishTime(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with io.open(UI, encoding="utf-8") as fh:
            cls.src = fh.read()
        fn = _cut(cls.src, "  var _proofMeterFacts = function (hs) {", "\n  };\n")
        prog = fn + r"""
var alt = { census: 'stale', key: 'busy', owed: 54, ratePerH: 1.7, etaS: 114606 };
var old = { census: 'stale', key: 'aside-cooldown', owed: 108, ratePerH: 0.6, etaS: 631102 };
var run = { census: 'stale', key: 'running', owed: 12, ratePerH: 12, etaS: 3600 };
process.stdout.write(JSON.stringify({ alt: _proofMeterFacts(alt), old: _proofMeterFacts(old), run: _proofMeterFacts(run),
  waitAlt: _proofMeterFacts(alt, true), waitRun: _proofMeterFacts(run, true), play: _proofMeterFacts({ key: 'playing' }, true),
  proto: _proofMeterFacts({ key: 'toString' }, true), cur: _proofMeterFacts({ census: 'current', key: 'busy', owed: 0 }) }));
"""
        r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise AssertionError("node could not run the console's meter - UNKNOWN, not passing: " + r.stderr[-600:])
        cls.o = json.loads(r.stdout)

    def test_his_two_rows(self):
        """* THE POINT - the ALT's "~31.8 h" and the OLD ALT's "~175.3 h" become the wait they are"""
        self.assertEqual(self.o["alt"], ["54 laws owed", "waits - PC busy"], self.o["alt"])
        self.assertEqual(self.o["old"], ["108 laws owed", "waits - import first"], self.o["old"])
        self.assertNotIn(" h left", " ".join(self.o["alt"] + self.o["old"]))

    def test_a_running_prover_keeps_its_time(self):
        self.assertEqual(self.o["run"], ["12 laws owed", "~12/h", "~1 h left"], self.o["run"])
        self.assertEqual((self.o["waitRun"], self.o["waitAlt"], self.o["play"], self.o["proto"]), ("", "PC busy", "you are playing", ""))
        self.assertEqual(self.o["cur"], [])

    def test_the_one_line_brief_reads_the_same_answer(self):
        self.assertIn("+ (_proofMeterFacts(hs, true) ? ' \\u00b7 ' + _proofMeterFacts(hs, true) : _eta(hs.etaS)) : '';", self.src,
                      "the Fleet row's brief still divides by a waiting prover's rate")


RED_PROOF = [
    {"why": "v3885 (his 11-08) - a waiting prover shows its stalled ETA again ('~31.8 h left')",
     "file": "tv/control_ui.html",
     "find": "    if (wait) { f.push('waits - ' + wait); return f; }   // v3885 - a waiting prover has no finish time\n",
     "replace": "", "matches": 1, "needs": "node"},
    {"why": "v3885 (his 11-08) - the row's brief divides by the waiting rate again ('proving 108 checks ~175.3 h')",
     "file": "tv/control_ui.html",
     "find": "      + (_proofMeterFacts(hs, true) ? ' \\u00b7 ' + _proofMeterFacts(hs, true) : _eta(hs.etaS)) : '';",
     "replace": "      + _eta(hs.etaS) : '';", "matches": 1},
    {"why": "v3885 - a key that is not a wait ('toString') reads as one (an object's own property only)",
     "file": "tv/control_ui.html",
     "find": "Object.prototype.hasOwnProperty.call(W, hs.key)) ? W[hs.key] : '';",
     "replace": "W[hs.key]) ? W[hs.key] : '';", "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
