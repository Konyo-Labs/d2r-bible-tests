# -*- coding: utf-8 -*-
"""v3880 (REG-3374) - THE STATE PANEL'S SUMMARY NEVER CLAIMS WHAT NOBODY MEASURED.

The Grok CLI, reading v3880's State panel render cold, quoted its first line back as a contradiction: "nothing is waiting on
you · nothing waiting on code · everything was measured · not measured yet". The render's payload carried no doctor report
(st.eagle absent), so the builder's `e = st.eagle || {}` gave every count its empty list's length - 0 - and the line said
three confident zeros nobody measured. The same shape on his console would read "all clear" on any build or boot whose
doctor has not answered. [[unknown-stays-unknown]]

The law drives the panel's OWN summary code (cut from tv/control_ui.html, from the counts to the line it pushes): with no
doctor count and no row, it says UNKNOWN and never "nothing is waiting on you"; a doctor that counted zeros still says the
zeros out loud (test_heart_surface's "a zero is said out loud" stays true). RED_PROOF below.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
NODE = shutil.which("node") or shutil.which("nodejs")
UI = os.path.join(HERE, "control_ui.html")
START = "    var _nYou  = (e.needsYou != null) ? e.needsYou : youRows.length;"
END = "a row was counted that this panel did not draw' : '')) + '</div>');"


def _cut():
    src = io.open(UI, encoding="utf-8").read()
    if src.count(START) != 1:
        raise AssertionError("the summary's counts moved - re-point this law (%d)" % src.count(START))
    i = src.index(START)
    j = src.index(END, i) + len(END)
    return src[i:j]


def _say(eagle, rows=0):
    js = ("var e = " + json.dumps(eagle) + ";\n"
          "var R = []; for (var i = 0; i < " + str(rows) + "; i++) R.push('<div>x</div>');\n"
          "var youRows = R, mineRows = [], unkRows = [], designRows = [], _lead = [], _dSay = '';\n"
          "function esc(s){ return String(s); }\n"
          + _cut() + "\nprocess.stdout.write(JSON.stringify(_lead));")
    r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=60, encoding="utf-8")
    if r.returncode != 0:
        raise AssertionError("node could not drive the summary: " + r.stderr[-600:])
    return json.loads(r.stdout)[0]


@unittest.skipUnless(NODE, "node is required to drive the panel's own summary - UNMEASURED here, not a pass")
class TheSummaryMeasuresOrSaysUnknown(unittest.TestCase):

    def test_no_doctor_report_is_unknown_never_all_clear(self):
        """* THE POINT: no count and no row from the doctor - the line says UNKNOWN, not three zeros"""
        s = _say({})
        self.assertIn("UNKNOWN", s)
        for claim in ("nothing is waiting on you", "nothing waiting on code", "everything was measured"):
            self.assertNotIn(claim, s, "an unmeasured panel claims %r" % claim)

    def test_a_doctor_that_counted_zeros_says_the_zeros(self):
        s = _say({"needsYou": 0, "mine": 0, "unknown": 0})
        self.assertIn("nothing is waiting on you", s)
        self.assertIn("everything was measured", s)
        self.assertNotIn("UNKNOWN", s)

    def test_counts_are_said_as_counted(self):
        s = _say({"needsYou": 3, "mine": 13, "unknown": 40})
        self.assertIn("3 thing(s) are waiting on YOU", s)
        self.assertIn("13 waiting on CODE", s)
        self.assertIn("40 not measured", s)

    def test_a_row_without_a_count_is_still_a_report(self):
        """a payload whose counts are absent but whose rows the panel drew is not 'unreported' - its rows are counted"""
        s = _say({}, rows=2)
        self.assertIn("2 thing(s) are waiting on YOU", s)
        self.assertNotIn("has not reported", s)


RED_PROOF = [
    {"why": "REG-3374 - with no doctor report the State summary says 'nothing is waiting on you · everything was measured' again",
     "file": "tv/control_ui.html",
     "find": "        (!_eHeard ? 'the doctor has not reported on this payload",
     "replace": "        (false ? 'the doctor has not reported on this payload", "matches": 1},
    {"why": "REG-3374 - a drawn row without a count is taken for an unreported doctor",
     "file": "tv/control_ui.html",
     "find": "      || !!(youRows.length || mineRows.length || unkRows.length || designRows.length);",
     "replace": "      || false;", "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
