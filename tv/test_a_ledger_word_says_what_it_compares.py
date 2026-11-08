# -*- coding: utf-8 -*-
"""REG-1986 - THE FLEET CARD USED ONE WORD FOR TWO QUESTIONS, SO "SYNCED" SAT UNDER "3 OF 3 DISAGREE".

GrokBot (#230 tick 388, v3601, his live console): "Konyo ALT TEST's card shows only RUNEWORDS UNSYNCED (uniques and
sets SYNCED), but its tip says 3 of 3 ledger(s) disagree". Both were true. The rows under the name are ledger_authority's
PROVENANCE - SYNCED means "this ledger's rows were earned on that board" - while the word beside the name is whether its
COUNTS equal this console's. The tip said only "N of M disagree", so the card read as contradicting itself.

The law drives the REAL _machineWord (lifted from tv/control_ui.html) against a reference row: the differs tip names the
ledgers that count differently and the ones that match; and the provenance block carries a caption saying what its
words answer.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

UI = os.path.join(HERE, "control_ui.html")
START = "      var _machineWord = function (t, isMe) {"
CAPTION = "'<div class=\"ftt-seed ftt-seed-rows\"><div class=\"ftts-cap\">where its rows came from</div>'"


def _src():
    with io.open(UI, encoding="utf-8") as fh:
        return fh.read()


def _lift(src):
    if src.count(START) != 1:
        return None
    i = src.find(START)
    j = src.find("\n      };\n", i)
    if j <= i:
        return None
    # REG-2064 (#298) - the word asks _ledgerMeasured (defined beside it); the cut carries the shipped one along
    a = src.find("      var _ledgerMeasured = function (t, lab) {")
    b = src.find("        return t.measured;\n      };\n", a)
    helper = src[a:b + len("        return t.measured;\n      };\n")] if (a >= 0 and b > a) else ""
    return helper + src[i:j + 9]


HARNESS = r"""
var _MINE = %s;
%s
var out = [];
%s.forEach(function (t) { out.push(_machineWord(t, false)); });
process.stdout.write(JSON.stringify(out));
"""


def _code_only(src):
    src = re.sub(r"/\*.{0,4000}?\*/", lambda m: "\n" * m.group(0).count("\n"), src, flags=re.S)
    return src


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class ALedgerWordSaysWhatItCompares(unittest.TestCase):

    MINE = {"sets": {"have": 128}, "uniques": {"have": 320}, "runewords": {"have": 99}}

    def words(self, rows):
        fn = _lift(_src())
        self.assertIsNotNone(fn, "_machineWord is gone from tv/control_ui.html (or appears more than once)")
        js = HARNESS % (json.dumps(self.MINE), fn, json.dumps(rows))
        p = subprocess.run(["node", "-"], input=js, capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 0, "the shipped _machineWord would not run: %s" % p.stderr[-800:])
        return json.loads(p.stdout)

    def test_the_differs_tip_names_which_ledgers_differ_and_which_match(self):
        alt = {"sets": {"have": 128}, "uniques": {"have": 320}, "runewords": {"have": 0}}
        w = self.words([alt])[0]
        self.assertEqual(w["w"], "ledgers differ")   # v3884 plain words
        self.assertIn("1 of 3 ledger(s) count differently from this console: runewords", w["t"])
        self.assertIn("(sets, uniques match)", w["t"], "the tip never said which ledgers agree: %s" % w["t"])

    def test_all_three_differ_names_all_three_and_no_match(self):
        dean = {"sets": {"have": 130}, "uniques": {"have": 0}, "runewords": {"have": 96}}
        w = self.words([dean])[0]
        self.assertIn("3 of 3 ledger(s) count differently from this console: sets, uniques, runewords", w["t"])
        self.assertNotIn("match)", w["t"])

    def test_the_tip_says_the_provenance_words_are_not_a_match(self):
        w = self.words([{"sets": {"have": 1}, "uniques": {"have": 320}, "runewords": {"have": 99}}])[0]
        self.assertIn("SYNCED / SEEDED beside a ledger is where its rows came from, not whether they match", w["t"])

    def test_a_matching_row_still_reads_synced(self):
        w = self.words([dict(self.MINE)])[0]
        self.assertEqual((w["w"], w["c"]), ("synced", "ftts-synced"))

    def test_the_provenance_block_says_what_its_words_answer(self):
        code = _code_only(_src())
        self.assertEqual(code.count(CAPTION), 1, "the provenance rows lost the caption that keeps them apart from the match")
        self.assertEqual(code.count(".ftt-seed-rows .ftts-cap {"), 1, "the caption has no style of its own")


RED_PROOF = [
    {"why": "v3884 - the row's word says 'differs' without saying what differs",
     "file": "tv/control_ui.html",
     "find": "        return {w: 'ledgers differ', c: 'ftts-unsynced',", "replace": "        return {w: 'differs', c: 'ftts-unsynced',",
     "matches": 1},
    {
        "why": "REG-1986 - the differs tip says only 'N of M disagree' again, under rows that read SYNCED",
        "file": "tv/control_ui.html",
        "find": "                 + _off.join(', ') + (_on.length ? ' (' + _on.join(', ') + ' match)' : '')\n",
        "replace": "                 + ''\n",
        "matches": 1,
    },
    {
        "why": "REG-1986 - the provenance rows lose their caption and read as a second match verdict",
        "file": "tv/control_ui.html",
        "find": "'<div class=\"ftt-seed ftt-seed-rows\"><div class=\"ftts-cap\">where its rows came from</div>'",
        "replace": "'<div class=\"ftt-seed ftt-seed-rows\">'",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
