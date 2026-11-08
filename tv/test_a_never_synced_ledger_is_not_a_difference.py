# -*- coding: utf-8 -*-
"""#298 (REG-2064) - A LEDGER THAT NEVER SYNCED IS NOT A DIFFERENCE: THE FLEET WORD ASKS WHAT THE CELL ASKS.

GrokBot tick 422 on #230 (v3622, K01-K03): Dean's name card printed "UNIQUES —" (never synced: the figure it sent is not a
count of anything) while his "differs" tip said "3 of 3 ledger(s) count differently from this console: sets, uniques,
runewords"; ALT TEST's "RUNEWORDS —" the same. The cell asked the ledger's measurement flag (v3389 / #240); the machine word
asked only whether `have` was a number, so a never-synced 0 became a disagreement.

  * one reader, _ledgerMeasured(t, lab), answers for the cell (via _measOf) and for _machineWord;
  * a never-synced ledger is not compared - not in "N of M", named instead as "never synced, so not compared";
  * a measured mismatch still reads differs; with nothing measured to compare, the word is "no report".
Drives the SHIPPED _ledgerMeasured and _machineWord, cut from control_ui.html and run in node. A missing node raises.
"""
import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
from cb_node_harness import NODE  # noqa: E402

UI = os.path.join(HERE, "control_ui.html")
MEAS = ("      var _ledgerMeasured = function (t, lab) {\n", "        return t.measured;\n      };\n")
WORD = ("      var _machineWord = function (t, isMe) {\n", "rows came from, not whether they match'};\n      };\n")


def _src():
    with open(UI, encoding="utf-8") as f:
        return f.read()


def _cut(s, pair):
    start, end = pair
    if s.count(start) != 1:
        raise AssertionError("anchor %r matched %d times - re-point this law" % (start[:50], s.count(start)))
    i = s.index(start)
    return s[i:s.index(end, i) + len(end)]


def _words(tallies):
    if NODE is None:
        raise AssertionError("node is not on this machine - this gate does not skip")
    s = _src()
    js = """
var _MINE = { sets: { have: 134 }, uniques: { have: 327 }, runewords: { have: 99 } };
%s
%s
console.log(JSON.stringify(%s.map(function(t){ return _machineWord(t, false); })));
""" % (_cut(s, MEAS), _cut(s, WORD), json.dumps(tallies))
    # the program goes in on STDIN - a law never hands node its program on argv
    r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise AssertionError("the cut functions did not run in node: %s" % r.stderr[-500:])
    return json.loads(r.stdout.strip().splitlines()[-1])


DEAN = {"sets": {"have": 132}, "uniques": {"have": 0}, "runewords": {"have": 98},
        "ledgerVerdict": {"ledgers": [{"ledger": "sets", "provenance": "SYNCED"}, {"ledger": "uniques", "provenance": "UNSYNCED"},
                                      {"ledger": "runewords", "provenance": "SYNCED"}]}}


class ANeverSyncedLedgerIsNotADifference(unittest.TestCase):

    def test_deans_unsynced_uniques_are_not_counted(self):
        w = _words([DEAN])[0]
        self.assertEqual(w["w"], "ledgers differ", w)   # v3884 plain words
        self.assertIn("2 of 2 ledger(s) count differently", w["t"], "a never-synced ledger was counted: %r" % w["t"])
        self.assertIn("uniques never synced, so not compared", w["t"], w["t"])

    def test_measured_by_overrides_and_an_all_unsynced_row_is_no_report(self):
        t = {"sets": {"have": 0}, "uniques": {"have": 0}, "runewords": {"have": 0},
             "measuredBy": {"sets": False, "uniques": False, "runewords": False}}
        self.assertEqual(_words([t])[0]["w"], "no ledgers", "three never-synced zeros read as a verdict")   # v3884

    def test_a_measured_mismatch_still_differs(self):
        t = {"sets": {"have": 100}, "uniques": {"have": 327}, "runewords": {"have": 99},
             "measuredBy": {"sets": True, "uniques": True, "runewords": True}}
        w = _words([t])[0]
        self.assertEqual((w["w"], "1 of 3" in w["t"]), ("ledgers differ", True), w)

    def test_the_cell_asks_the_same_reader(self):
        self.assertEqual(_src().count("        var _measOf = function (lab) { return _ledgerMeasured(t, lab); };"), 1,
                         "the card cell and the machine word no longer share one measurement rule")


RED_PROOF = [
    {"why": "REG-2064 - a never-synced ledger is counted among the ledgers that differ again (Dean's '—' uniques)",
     "file": "control_ui.html",
     "find": "          if (_ledgerMeasured(t, k) === false) { _unk.push(k); return; }",
     "replace": "          if (false) { _unk.push(k); return; }",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
