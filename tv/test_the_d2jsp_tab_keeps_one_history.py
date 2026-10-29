# -*- coding: utf-8 -*-
"""#83 (REG-3094) - THE D2JSP TAB KEEPS ONE HISTORY: EVERY POST AND EVERY TRADE, NEWEST FIRST, FROM THE STORES THAT HOLD THEM.

Each card shows its own attempts (REG-2872) and the vault keeps every copy that left (REG-2883), so a post or a trade of an
item hidden or taken off the list had no surface left, and there was no one place to read what the desk had done. The tab
now has one History, painted on every paint and after every log write. It writes no store: every name's post log rows,
listed or not, and the vault's traded rows, the one source for a traded copy - a log 'traded' / 'for-sale' row speaks only
for a name the vault does not track (a planner pick), so one copy that left is never two rows. Both clocks read to one
spelling, newest first; a time that does not read says "time UNKNOWN" and sorts last; with no vault the trades are UNKNOWN.

Driven: the D2JSP pane's own script cut out of bible.html and run in node over a fake page and a fake vault - the history
read directly, then painted through the tab's own show and through its own Mark sold click - never a browser, never d2jsp.
RED_PROOF below.
"""
import json
import os
import re
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
NODE = shutil.which("node")
BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")

FAKES = r"""
function Node(id){ this.id = id; this.attrs = {}; this.hidden = true; this._html = ''; this.sets = 0; this.textContent = ''; this.title = ''; }
Node.prototype.setAttribute = function(k, v){ this.attrs[k] = String(v); };
Node.prototype.getAttribute = function(k){ return Object.prototype.hasOwnProperty.call(this.attrs, k) ? this.attrs[k] : null; };
Node.prototype.removeAttribute = function(k){ delete this.attrs[k]; };
Node.prototype.querySelector = function(){ return { focus: function(){} }; };
Node.prototype.querySelectorAll = function(){ return []; };
Node.prototype.appendChild = function(){};
Node.prototype.insertBefore = function(){};
Object.defineProperty(Node.prototype, 'innerHTML', { get: function(){ return this._html; }, set: function(v){ this._html = String(v); this.sets++; } });
var NODES = {};
['d2jsp-list', 'd2jsp-status', 'd2jsp-lamp', 'd2jsp-draft-host', 'd2jsp-board', 'd2jsp-history'].forEach(function(id){ NODES[id] = new Node(id); });
var CLICKS = [];
var document = {
  documentElement: { classList: { contains: function(){ return false; } } },
  getElementById: function(id){ return NODES[id] || null; },
  querySelector: function(){ return null; },
  querySelectorAll: function(){ return []; },
  addEventListener: function(type, fn){ if (type === 'click') CLICKS.push(fn); },
  createElement: function(){ return new Node(''); },
  body: { appendChild: function(){} }
};
var LOG = {
  'Odd': [{ at: 'Oct 20 2026 10:00', board: 268, kind: 'confirmed', text: 'a free-text time' },
          { at: '2026-13-40 10:00 UTC', board: 268, kind: 'missed', text: 'a month that is not one' }],
  'Grief': [{ at: '2026-10-20 10:00 UTC', board: 268, kind: 'confirmed', text: 'Accepted', topic: 'https://forums.d2jsp.org/topic.php?t=1' },
            { at: '2026-10-21 09:00 UTC', board: 268, kind: 'traded', text: 'Marked traded: one copy' }],
  'Shako': [{ at: '2026-10-22 08:00 UTC', board: 268, kind: 'maybe', text: 'may be up' },
            { at: '2026-10-22 09:00 UTC', board: 268, kind: 'for-sale', text: 'For sale again: the old sold mark is cleared' }],
  'Gone Item': [{ at: '2026-10-19 07:00 UTC', board: 268, kind: 'missed', text: 'Not sent <script>x</script>' }],
  'Pick': [{ at: '2026-10-23 12:00 UTC', board: 268, kind: 'traded', text: 'Marked traded: it is not in the vault' }]
};
var RAW = { 'd2r_d2jsp_log': JSON.stringify(LOG), 'd2r_d2jsp_hide': JSON.stringify({ 'Shako': 1 }) };
var localStorage = { getItem: function(k){ return Object.prototype.hasOwnProperty.call(RAW, k) ? RAW[k] : null; },
                     setItem: function(k, v){ RAW[k] = String(v); }, removeItem: function(k){ delete RAW[k]; } };
var location = { hostname: '127.0.0.1' };
var MULE = JSON.stringify({ 'Grief': 'm1', 'Shako': 'm1' });
var GONE = { 'Grief': [{ at: '2026-10-21T09:00:30.000Z', post: null }],
             'Tyrael': [{ at: '2026-10-24T01:02:03.000Z', post: 'https://forums.d2jsp.org/topic.php?t=9' }] };
var window = { addEventListener: function(){}, LSR: { getItem: function(k){ return k === 'd2r_muleAssign' ? MULE : null; } },
               _vaultTradedNames: function(){ return Object.keys(GONE); },
               _vaultTradedOf: function(n){ return GONE[n] || []; } };
function fetch(){ return Promise.resolve({ status: 200, json: function(){ return Promise.resolve({ state: 'unknown', fg: null, reason: 'no prices', n: 0 }); } }); }
"""

SCENARIO = r"""
var out = {}, box = NODES['d2jsp-history'];
out.full = window._d2jspHistoryHtml();
window._d2jspShow(); out.painted = box.innerHTML; out.sets1 = box.sets;
window._d2jspShow(); out.sets2 = box.sets;
var btn = { getAttribute: function(){ return 'Pick2'; } };
CLICKS.forEach(function(fn){ fn({ preventDefault: function(){}, target: { id: '', closest: function(sel){
  return sel === '#tab-d2jsp' ? {} : (sel === '[data-d2jsp-sold]' ? btn : null); } } }); });
out.afterMark = box.innerHTML; out.sets3 = box.sets;
var keep = window._vaultTradedNames; delete window._vaultTradedNames;
out.noVault = window._d2jspHistoryHtml();
window._vaultTradedNames = keep;
RAW['d2r_d2jsp_log'] = '{}'; GONE = {};
out.empty = window._d2jspHistoryHtml();
process.stdout.write(JSON.stringify(out));
"""

ROW = re.compile(r'<li data-kind="([^"]*)" data-src="(\w+)">(\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC|time UNKNOWN) · (.*?)(?: · |</li>)')


def _between(src, start, end):
    i = src.index(start)
    return src[i + len(start):src.index(end, i + len(start))]


def _rows(html):
    """[(kind, src, when, name)] in painted order."""
    return [m.groups() for m in ROW.finditer(html)]


class TheD2jspTabKeepsOneHistory(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not NODE:
            raise AssertionError("node is not on this machine - this law does not skip")
        with open(BIBLE, encoding="utf-8") as fh:
            src = fh.read()
        pane = _between(src, 'id="tab-d2jsp"', 'id="tab-vault"')
        cls.markup = pane.split("<script>", 1)[0]
        code = pane.split("<script>", 1)[1].split("</script>", 1)[0]
        r = subprocess.run([NODE, "-"], input=FAKES + code + "\n" + SCENARIO, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise AssertionError("the D2JSP pane did not run in node: %s" % r.stderr[-900:])
        cls.o = json.loads(r.stdout)
        cls.full = _rows(cls.o["full"])

    def test_premise_the_history_is_drawn_and_the_tab_has_its_box(self):
        self.assertIn('id="d2jsp-history"', self.markup, "the D2JSP tab has no History box")
        self.assertIn("History (8)", self.o["full"], "premise: %r" % self.o["full"][:400])
        self.assertEqual(len(self.full), 8, "the rows did not read: %r" % self.o["full"][:600])

    def test_every_post_and_trade_newest_first_unread_times_last(self):
        self.assertEqual([(r[3], r[2]) for r in self.full], [
            ("Tyrael", "2026-10-24 01:02 UTC"),
            ("Pick", "2026-10-23 12:00 UTC"),
            ("Shako", "2026-10-22 08:00 UTC"),
            ("Grief", "2026-10-21 09:00 UTC"),
            ("Grief", "2026-10-20 10:00 UTC"),
            ("Gone Item", "2026-10-19 07:00 UTC"),
            ("Odd", "time UNKNOWN"),
            ("Odd", "time UNKNOWN")])

    def test_a_traded_copy_is_the_vaults_row_and_never_two(self):
        grief = [r for r in self.full if r[3] == "Grief" and r[0] == "traded"]
        self.assertEqual([(r[0], r[1]) for r in grief], [("traded", "vault")], "Grief's one traded copy read as %r" % grief)
        self.assertEqual([(r[0], r[1]) for r in self.full if r[3] == "Tyrael"], [("traded", "vault")])
        self.assertNotIn("for-sale", [r[0] for r in self.full if r[3] == "Shako"], "a name the vault holds took its trade word from the log")
        self.assertIn("https://forums.d2jsp.org/topic.php?t=9</a>", self.o["full"], "the vault row's post link is gone")

    def test_a_planner_pick_keeps_its_log_trade(self):
        self.assertIn(("traded", "log", "2026-10-23 12:00 UTC", "Pick"), self.full)

    def test_hidden_and_removed_items_keep_their_history_escaped(self):
        names = [r[3] for r in self.full]
        self.assertIn("Shako", names, "an item hidden from the list lost its history")
        self.assertIn("Gone Item", names, "an item taken off the list lost its history")
        self.assertNotIn("<script>", self.o["full"])
        self.assertIn("&lt;script&gt;", self.o["full"])

    def test_no_vault_means_trades_unknown_never_none(self):
        nv = self.o["noVault"]
        self.assertIn("Trades: UNKNOWN", nv)
        self.assertEqual(sorted(set(r[1] for r in _rows(nv))), ["log"])
        self.assertNotIn("traded", [r[0] for r in _rows(nv)], "with no vault a trade was still drawn: %r" % _rows(nv))
        self.assertIn("History (5)", nv)

    def test_nothing_yet_says_so(self):
        self.assertIn("History (0)", self.o["empty"])
        self.assertIn("No post or trade yet.", self.o["empty"])

    def test_the_tab_paints_it_once_and_a_new_log_row_repaints_it(self):
        self.assertEqual(self.o["painted"], self.o["full"], "the tab's show did not paint the history")
        self.assertGreaterEqual(self.o["sets1"], 1)
        self.assertEqual(self.o["sets2"], self.o["sets1"], "an unchanged history was repainted")
        self.assertEqual(self.o["sets3"], self.o["sets2"] + 1, "Mark sold wrote a log row and the history did not repaint once")
        self.assertIn(("traded", "log"), [(r[0], r[1]) for r in _rows(self.o["afterMark"]) if r[3] == "Pick2"])


RED_PROOF = [
    {"why": "REG-3094 - the vault's traded rows are not read",
     "file": "bible.html",
     "find": "    (gone || []).forEach(function(n){\n      var rows = [];\n",
     "replace": "    ([]).forEach(function(n){\n      var rows = [];\n",
     "matches": 1},
    {"why": "REG-3094 - a log trade row is drawn beside the vault's own row (one copy, two rows)",
     "file": "bible.html",
     "find": "if ((r.kind === 'traded' || r.kind === 'for-sale') && (gone == null || tracked[n])) return;",
     "replace": "if (false) return;",
     "matches": 1},
    {"why": "REG-3094 - a name the vault holds but never traded takes its trade word from the log",
     "file": "bible.html",
     "find": "    (held || []).concat(gone || []).forEach(function(n){ tracked[n] = 1; });\n",
     "replace": "    (gone || []).forEach(function(n){ tracked[n] = 1; });\n",
     "matches": 1},
    {"why": "REG-3094 - with no vault the trades read as none, not UNKNOWN",
     "file": "bible.html",
     "find": "    return { rows: out, vault: gone != null };\n",
     "replace": "    return { rows: out, vault: true };\n",
     "matches": 1},
    {"why": "REG-3094 - the rows are not ordered",
     "file": "bible.html",
     "find": "    out.sort(function(a, b){ return (a.t == null || b.t == null) ? ((a.t == null) - (b.t == null)) : (b.t - a.t); });\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3094 - an unread time does not sort last",
     "file": "bible.html",
     "find": "((a.t == null) - (b.t == null))",
     "replace": "((b.t == null) - (a.t == null))",
     "matches": 1},
    {"why": "REG-3094 - the post log's own spelling does not read",
     "file": "bible.html",
     "find": "    if (/^\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2} UTC$/.test(v)) v = v.slice(0, 16).replace(' ', 'T') + ':00Z';   /* the post log's spelling */\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3094 - a free-text time is guessed into a date",
     "file": "bible.html",
     "find": "    var t = /^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}/.test(v) ? Date.parse(v) : NaN;",
     "replace": "    var t = Date.parse(v);",
     "matches": 1},
    {"why": "REG-3094 - the tab's paint does not paint the history",
     "file": "bible.html",
     "find": "    paintHistory();   /* REG-3094 - on every paint, whichever way the list paints */\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3094 - a new log row does not repaint the history",
     "file": "bible.html",
     "find": "    paintHistory();   /* REG-3094 */\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3094 - an unchanged history repaints on every paint",
     "file": "bible.html",
     "find": "    if (html !== historyDrawn) { box.innerHTML = html; historyDrawn = html; }",
     "replace": "    { box.innerHTML = html; historyDrawn = html; }",
     "matches": 1},
    {"why": "REG-3094 - the tab has no History box",
     "file": "bible.html",
     "find": "      <details id=\"d2jsp-history\" class=\"d2jsp-history\"><summary>History</summary></details>   <!-- REG-3094 -->\n",
     "replace": "",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
