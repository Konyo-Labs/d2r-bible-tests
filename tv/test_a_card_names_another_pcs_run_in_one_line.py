# -*- coding: utf-8 -*-
"""v3902 (REG-3768, #213) - A SHELF CARD NAMES ANOTHER PC'S RUN IN ONE LINE; ITS DAY RIDES THE LINE BELOW.

GrokBot 11-12 05:30, his live console at 1512 (shelf-header-1512.png): TOP READS/HR read "Konyo · ALT · Nov …". The card's
value line is ONE line, ellipsised (.shi-val nowrap), and another PC's run was named "<PC> · <day>" there - longer than
"Session 205", so the day was cut. Now the value line carries the run's NAME only and another PC's day moves to the sub line
("600 /hr · Nov 12"); the full name rides the value's tooltip.

DRIVEN: the shipped _cmpList / _shFleetRuns / _shHighlights cut from tv/control_ui.html and run in node. RED_PROOF below.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
from cb_node_harness import NODE  # noqa: E402

UI = os.path.join(HERE, "control_ui.html")


def _cards():
    ui = io.open(UI, encoding="utf-8").read()

    def fn(name):
        head = "  function %s(" % name
        assert ui.count(head) == 1, name
        i = ui.index(head)
        return ui[i:ui.index("\n  }\n", i) + 4]
    prog = ("function esc(s){ return String(s); }\nfunction _kpiFmt(n){ return String(n); }\nvar TH = {};\n"
            + "\n".join(fn(n) for n in ("_cmpList", "_shFleetRuns", "_shHighlights")) + r"""
var now = Date.UTC(2026, 10, 12, 5, 0, 0);
TH.sessions = [{ n: 205, sessionId: 's_m1', t0: now - 10 * 864e5, t1: now - 10 * 864e5 + 3600e3, reads: 5, finds: [],
                 coverage: { read: 1, total: 4 } }];
window = { _shFleet: { ok: true, sessions: [{ owner: 'Konyo · ALT', sessionId: 's_a1', t0: now - 3600e3, t1: now - 600e3,
                                             reads: 500, chron: 0 }] } };
console.log(JSON.stringify({ html: _shHighlights() }));
""")
    d = tempfile.mkdtemp(prefix="shelf_cards_ui_")
    try:
        h = os.path.join(d, "h.js")
        with io.open(h, "w", encoding="utf-8") as fh:
            fh.write(prog)
        r = subprocess.run([NODE, h], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")[-700:]
    html = json.loads(r.stdout.decode("utf-8").strip().splitlines()[-1])["html"]
    out = {}
    for m in re.finditer(r'<div class="shi-lab">([^<]*)</div><div class="shi-val"([^>]*)>([^<]*)</div>'
                         r'(?:<div class="shi-sub">([^<]*)</div>)?', html):
        out[m.group(1)] = {"attr": m.group(2), "val": m.group(3), "sub": m.group(4) or ""}
    return out


class ACardNamesAnotherPcsRunInOneLine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not NODE:
            raise AssertionError("node is not installed on this PC - this law runs the shipped cards in node and does not skip")
        cls.c = _cards()

    def test_baseline_his_own_run_is_session_n(self):
        self.assertIn("Most reads", self.c, self.c)
        self.assertEqual(self.c["Most reads"]["val"], "Konyo · ALT", "PREMISE: the fleet run does not win most reads")
        self.assertIn("Streak", self.c)

    def test_the_value_line_is_the_pc_and_the_day_is_below(self):
        """* THE POINT - 'Konyo · ALT · Nov …' at 1512"""
        top = self.c["Top reads/hr"]
        self.assertEqual(top["val"], "Konyo · ALT", "another PC's run is not named by its PC alone on the value line: %r" % top)
        self.assertRegex(top["sub"], r"/hr · \S+", "the run's day is not on the sub line: %r" % top)
        self.assertIn('title="Konyo · ALT · ', top["attr"], "the full name is not on the tooltip: %r" % top)


RED_PROOF = [
    {"why": "REG-3768 - another PC's day goes back on the one value line, where 1512 cuts it ('Konyo · ALT · Nov …')",
     "file": "tv/control_ui.html",
     "find": "    function _shRunName(m){ return m.n ? 'Session ' + m.n : esc(String(m.owner || 'another PC')); }\n",
     "replace": "    function _shRunName(m){ return m.n ? 'Session ' + m.n : esc(String(m.owner || 'another PC')) + ' \\u00b7 ' + esc(m.when || ''); }\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3768 - the day leaves the sub line",
     "file": "tv/control_ui.html",
     "find": "    function _shRunDay(m){ return (!m.n && m.when) ? ' \\u00b7 ' + esc(m.when) : ''; }\n",
     "replace": "    function _shRunDay(m){ return ''; }\n",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
