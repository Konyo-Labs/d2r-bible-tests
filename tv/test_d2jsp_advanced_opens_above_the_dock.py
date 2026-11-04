# -*- coding: utf-8 -*-
"""v3861 (#230 6643907824 D1) - WHAT d2jsp's ADVANCED OPENS LANDS ABOVE THE COMMAND DOCK, AND ESCAPE CLOSES IT.

His words, 2026-11-05 00:24: "the ADVANCED for d2jsp is bugged and trapping buttons, something pops up and renders, I
can't really see anything there". GrokBot measured it on a guest: Advanced opens INLINE (+~117 px) and on a 1280x720
window what it opened, and the Find / Add an item / Post the list row under it, sat behind the fixed `.control-dock`
(z-index 120), so elementFromPoint at those buttons returned the dock until he scrolled. Escape did nothing.

Drives the REAL toggle, reveal and Escape listener over a stub DOM in node: the panel ends below the dock's top edge,
so opening must scroll it up by exactly the overlap (and never past its own top); Escape must close it, except while
the planner or the draft is open (each owns its own Escape).
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

A = "  window._d2jspPriceClick = function(ev){\n"
B = "  window._d2jspRevealAboveDock = d2jspRevealAboveDock;\n"
ESC_START = "  /* v3861 (#230 6643907824 D1) - Escape closes Advanced too"
ESC_END = "    if (door) door.setAttribute('aria-expanded', 'false');\n  });\n"

STUB = r"""
var listeners = [], scrolled = [];
function El(id, rect, hidden){ this.id = id; this._r = rect; this.hidden = hidden; this.attrs = {}; this.offsetParent = {}; }
El.prototype.getBoundingClientRect = function(){ return this._r; };
El.prototype.setAttribute = function(k, v){ this.attrs[k] = String(v); };
var ELS = {
  'd2jsp-price-backend': new El('d2jsp-price-backend', {top: 600, bottom: 717}, true),
  'd2jsp-price-advanced': new El('d2jsp-price-advanced', {top: 560, bottom: 590}, false),
  'd2jsp-planner-host': new El('d2jsp-planner-host', {top: 0, bottom: 0}, true),
  'd2jsp-draft-host': new El('d2jsp-draft-host', {top: 0, bottom: 0}, true)
};
var DOCK = new El('dock', {top: 640, bottom: 712}, false);
var window = { innerHeight: 720, scrollBy: function(x, y){ scrolled.push(y); } };
var document = {
  getElementById: function(id){ return ELS[id] || null; },
  querySelector: function(sel){ return sel === '.control-dock .dock-inner' ? DOCK : null; },
  addEventListener: function(type, fn){ if (type === 'keydown') listeners.push(fn); }
};
function d2jspLoadDatabase(){}
"""

TAIL = r"""
var out = {};
var door = ELS['d2jsp-price-advanced'], panel = ELS['d2jsp-price-backend'];
out.handled = window._d2jspPriceClick({target: door});
out.openHidden = panel.hidden; out.expanded = door.attrs['aria-expanded']; out.scrolled = scrolled.slice();
ELS['d2jsp-planner-host'].hidden = false;
listeners.forEach(function(fn){ fn({key: 'Escape'}); });
out.keptWithPlanner = panel.hidden;
ELS['d2jsp-planner-host'].hidden = true;
listeners.forEach(function(fn){ fn({key: 'Escape'}); });
out.closedByEsc = panel.hidden; out.expandedAfter = door.attrs['aria-expanded'];
process.stdout.write(JSON.stringify(out));
"""


def _code():
    with io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8") as fh:
        page = fh.read()
    for a in (A, B, ESC_START, ESC_END):
        assert page.count(a) == 1, "anchor %r found %d times - this law has lost its target" % (a[:50], page.count(a))
    i = page.index(A)
    j = page.index(B) + len(B)
    k = page.index(ESC_START)
    m = page.index(ESC_END, k) + len(ESC_END)
    return page[i:j] + page[k:m]


@unittest.skipIf(shutil.which("node") is None, "node is absent - UNMEASURED, not passing")
class AdvancedOpensAboveTheDock(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        js = STUB + _code() + TAIL
        r = subprocess.run([shutil.which("node"), "-"], input=js, capture_output=True, text=True, encoding="utf-8",
                           timeout=60)
        if r.returncode != 0:
            raise AssertionError("node could not run the real toggle - this law measured NOTHING:\n" + r.stderr[-1500:])
        cls.out = json.loads(r.stdout)

    def test_opening_scrolls_what_it_opened_above_the_dock(self):
        o = self.out
        self.assertTrue(o["handled"])
        self.assertFalse(o["openHidden"], "Advanced did not open")
        self.assertEqual(o["expanded"], "true")
        # the panel ends at 717, the dock's top is 640, 12 px of air: it must rise by 89 px, once
        self.assertEqual(o["scrolled"], [89], "what Advanced opened stayed behind the dock: scrolled %r" % (o["scrolled"],))

    def test_escape_closes_it_but_never_from_under_the_planner(self):
        o = self.out
        self.assertFalse(o["keptWithPlanner"], "Escape closed Advanced while the planner (which owns Escape) was open")
        self.assertTrue(o["closedByEsc"], "Escape did not close Advanced")
        self.assertEqual(o["expandedAfter"], "false")


RED_PROOF = [
    {"why": "v3861 - Advanced opens behind the command dock again: what it opened is never scrolled into view",
     "file": "bible.html",
     "find": "    if (!panel.hidden) d2jspRevealAboveDock(panel);\n",
     "replace": "",
     "matches": 1},
    {"why": "v3861 - Escape no longer closes Advanced",
     "file": "bible.html",
     "find": "    panel.hidden = true;\n    var door = document.getElementById('d2jsp-price-advanced');\n",
     "replace": "    var door = document.getElementById('d2jsp-price-advanced');\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
