# -*- coding: utf-8 -*-
"""REG-2924 - THE FIVE ROSTER LABELS ARE ONE LIST, AND EVERY READER OF A FLEET ROW NAMES THE SAME OWNER.

The five owner labels (Konyo · Mac, Konyo · ALT, Konyo · GrokBot, Dean, Wife PC) decide whose profile a row is, and they were
typed in four places: roster_publish.OWNERS (the console publishes under it; console_snapshot imports it), the worker's
`export const OWNERS` (functions/api/roster.js refuses any other key), and twice in the console page - the Fleet's
_FLEET_ROSTER_OWNERS beside _fleetRosterOwner, and a second copy inside _shadowRosterStores as a fallback that answered only
when the rule had said "no profile", so it could only ever disagree with it. The page now holds one list and the shadow reader
asks the one rule. Python and the page could not share a source without a new served-constant path, so this law holds the
three lists to one value and the two rules to one answer for every fleet row a reader can be handed. Measured on the way:
Python read a nickname untrimmed and the page trimmed it, so " Dean " was Dean's row to the eyes and nobody's to the
snapshot's online check; owner_of now trims as the page does.

Python + node (the page's own rule and shadow reader, cut from control_ui.html and run). RED_PROOF below.
"""
import io
import json
import os
import re
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import roster_publish as RP  # noqa: E402
from cb_node_harness import node_path  # noqa: E402

NODE = node_path()
UI = os.path.join(HERE, "control_ui.html")
ROSTER_JS = os.path.join(ROOT, "functions", "api", "roster.js")
RULE = ("  var _FLEET_ROSTER_OWNERS = [", "  window._fleetRosterOwner = _fleetRosterOwner;\n")
SHADOW = ("  window._shadowRosterStores = function (row, fleet, owner) {", "  window._shadowEnter = function (owner) {")
NICKS = list(RP.OWNERS) + ["Konyo", "Grok", "nobody", "", " Dean ", "Konyo · ALT ", None]
PLATS = ["mac", "windows", "linux", None]


def _read(p):
    return io.open(p, encoding="utf-8").read()


def _cut(s, ab):
    a, b = ab
    if s.count(a) != 1:
        raise AssertionError("PREMISE: %r is in the page %d times, not once" % (a[:60], s.count(a)))
    i = s.index(a)
    j = s.index(b, i)
    return s[i:j + (len(b) if b.endswith("\n") else 0)]


def _node(js):
    if not NODE:
        raise unittest.SkipTest("node is absent on this machine - UNMEASURED here, never a pass")
    r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, encoding="utf-8", timeout=120)
    if r.returncode != 0:
        raise AssertionError("the page's own code would not run in node: %s" % (r.stderr or r.stdout)[-1500:])
    return json.loads(r.stdout)


def _shadow_world(rule):
    ui = _read(UI)
    js = ("var window = globalThis;\n" + rule + _cut(ui, SHADOW)
          + "\nvar b = window._shadowRosterStores({ owner: 'Dean', published: true, sections: {} },"
          " { offline: [{ nickname: 'Dean', platform: 'windows', machine: 'h-dean' }] }, 'Dean');"
          "\nprocess.stdout.write(JSON.stringify(b && b.world));")
    return _node(js)


class TheRosterLabelsAreOneList(unittest.TestCase):

    def test_python_the_worker_and_the_console_page_hold_one_list(self):
        page = _node("var window = {};\n" + _cut(_read(UI), RULE) + "\nprocess.stdout.write(JSON.stringify(_FLEET_ROSTER_OWNERS));")
        m = re.search(r"^export const OWNERS = (\[[^\]\n]*\]);", _read(ROSTER_JS), re.M)
        self.assertIsNotNone(m, "PREMISE: the worker's OWNERS line moved")
        self.assertEqual(len(RP.OWNERS), 5, "PREMISE: the roster is not five labels")
        self.assertEqual(page, list(RP.OWNERS), "the console page's labels are not roster_publish's")
        self.assertEqual(json.loads(m.group(1)), list(RP.OWNERS), "the worker's labels are not roster_publish's")

    def test_the_console_page_holds_the_list_once(self):
        ui = _read(UI)
        n = sum(ui.count(q + "Konyo \\u00b7 GrokBot" + q) + ui.count(q + "Konyo · GrokBot" + q) for q in ("'", '"'))
        self.assertEqual(n, 1, "the console page types the roster labels %d times - a second copy can only drift" % n)

    def test_every_fleet_row_names_the_same_owner_in_python_and_on_the_page(self):
        rows = [{"nickname": n, "platform": p} for n in NICKS for p in PLATS]
        got = _node("var window = {};\n" + _cut(_read(UI), RULE)
                    + "\nprocess.stdout.write(JSON.stringify(%s.map(function (m) { return _fleetRosterOwner(m); })));" % json.dumps(rows))
        want = [RP.owner_of(r["nickname"], r["platform"]) or "" for r in rows]
        self.assertGreaterEqual(sum(1 for w in want if w), len(RP.OWNERS) * len(PLATS), "PREMISE: almost no row names an owner")
        diff = [(r, g, w) for r, g, w in zip(rows, got, want) if g != w]
        self.assertEqual(diff, [], "the page and Python name different owners for the same fleet row (row, page, python)")

    def test_the_shadow_reader_asks_the_one_rule(self):
        rule = _cut(_read(UI), RULE)
        base = _shadow_world(rule)
        self.assertEqual((base or {}).get("machine"), "windows", "PREMISE: Dean's windows row does not open a world: %r" % base)
        self.assertEqual(rule.count("'Dean', "), 1, "PREMISE: the rule's list moved")
        self.assertIsNone(_shadow_world(rule.replace("'Dean', ", "")),
                          "with Dean taken off the one list, the shadow reader still found his row - it reads its own copy")


RED_PROOF = [
    {"why": "REG-2924 - the shadow reader keeps its own copy of the labels as a fallback",
     "file": "tv/control_ui.html",
     "find": "      return (typeof window._fleetRosterOwner === 'function') ? (window._fleetRosterOwner(m) || '') : '';\n",
     "replace": "      var OWNERS = ['Konyo \\u00b7 Mac', 'Konyo \\u00b7 ALT', 'Konyo \\u00b7 GrokBot', 'Dean', 'Wife PC'];\n"
                "      var got = (typeof window._fleetRosterOwner === 'function') ? window._fleetRosterOwner(m) : '';\n"
                "      if (got) return got;\n"
                "      var nick = String((m && m.nickname) || '').trim();\n"
                "      return OWNERS.indexOf(nick) >= 0 ? nick : '';\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2924 - Python reads a fleet nickname untrimmed, the page trims it",
     "file": "tv/roster_publish.py",
     "find": "    if isinstance(name, str):\n        name = name.strip()\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2924 - the console page's list drifts from roster_publish's",
     "file": "tv/control_ui.html",
     "find": "  var _FLEET_ROSTER_OWNERS = ['Konyo \\u00b7 Mac', 'Konyo \\u00b7 ALT', 'Konyo \\u00b7 GrokBot', 'Dean', 'Wife PC'];\n",
     "replace": "  var _FLEET_ROSTER_OWNERS = ['Konyo \\u00b7 Mac', 'Konyo \\u00b7 ALT', 'Konyo \\u00b7 GrokBot', 'Dean'];\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2924 - the worker's list drifts from roster_publish's",
     "file": "functions/api/roster.js",
     "find": "export const OWNERS = [\"Konyo · Mac\", \"Konyo · ALT\", \"Konyo · GrokBot\", \"Dean\", \"Wife PC\"];",
     "replace": "export const OWNERS = [\"Konyo · Mac\", \"Konyo · ALT\", \"Konyo · GrokBot\", \"Dean\", \"Wife PC\", \"Guest\"];",
     "matches": 1},
    {"why": "REG-2924 - the page names Konyo on any platform but Windows as his Mac",
     "file": "tv/control_ui.html",
     "find": "    if (nick === 'Konyo' && m && m.platform === 'mac') return 'Konyo \\u00b7 Mac';\n",
     "replace": "    if (nick === 'Konyo' && m && m.platform !== 'windows') return 'Konyo \\u00b7 Mac';\n",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main()
