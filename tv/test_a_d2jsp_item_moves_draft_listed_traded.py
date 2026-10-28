# -*- coding: utf-8 -*-
"""REG-2873 (#83, his ask 4, GrokBot 6476487696) - A D2JSP ITEM MOVES DRAFT -> LISTED -> TRADED, AND THE VAULT SEES IT.

GrokBot: "Monitoring and trade state: draft, then listed (live), then traded or not traded yet. This ties into the Vault:
a listed item is still counted in its spot, and a traded one leaves the count without a 'where is it?' task." The lead:
"Keep it light: the controls live in the D2JSP tab only."

MEASURED before (the room's own code in node): an item had no state. "Mark sold" only toggled the list's SOLD block. A post
left no trace a card or the Vault could read. Nothing took a traded copy out of the vault count, so the vault would go on
expecting it in its spot.

Now the room reads a state off the post log (REG-2872) and the traded mark. A confirmed post is "Listed on board N · not
traded yet". An answer that may be up is "Maybe listed". Anything else is "Draft · not posted", and Mark traded is
"Traded". The card shows it as a chip. Mark traded (the old Mark sold) is one trade-out event: with several copies, one
leaves the count through the vault's own copy door (vaultCopyAdjust), and a single copy leaves through the removal door on
its trade-out lane. The toolbar Undo is armed, and a log row says what happened. A traded item keeps its card (its SOLD
block rides the list) after it left the vault. Un-marking says the count is not put back there. The Vault's FIND shows a
small "listed" mark from the room's state (window._d2jspTradeState), and the copy still counts. The room runs in node with
stub vault doors, and the Vault's FIND runs on the whole page in node. Never a browser, never d2jsp. RED_PROOF below.

REG-2881 (the wiring, one door): Mark traded is window._vaultTradeEvent's trade-out; the room's own copy-door and
removal-door calls are retired (law: test_a_mark_traded_goes_through_the_vault_trade_door.py). The Vault's FIND reads the
copy's own trade slot (REG-2878's law), so the room's FIND mark is gone. This law keeps the item's states on its card,
Mark traded as one trade-out event, the traded card, and For sale again, with a stub door that records every call.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable
enable()


ROOT = os.path.dirname(HERE)
BIBLE = os.path.join(ROOT, "bible.html")
NODE = shutil.which("node")
TOPIC = "https://forums.d2jsp.org/topic.php?t=9001&f=268"


def _between(src, start, end):
    i = src.index(start)
    j = src.index(end, i + len(start))
    return src[i + len(start):j]


FAKES = r"""
var LISTEN = { click: [], input: [], keydown: [] };
function Node(id){ this.id = id; this.attrs = {}; this.hidden = true; this._html = ''; this.textContent = ''; this.title = ''; }
Node.prototype.setAttribute = function(k, v){ this.attrs[k] = String(v); };
Node.prototype.getAttribute = function(k){ return Object.prototype.hasOwnProperty.call(this.attrs, k) ? this.attrs[k] : null; };
Node.prototype.removeAttribute = function(k){ delete this.attrs[k]; };
Node.prototype.querySelector = function(){ return { focus: function(){} }; };
Node.prototype.querySelectorAll = function(){ return []; };
Node.prototype.appendChild = function(){};
Node.prototype.insertBefore = function(){};
Object.defineProperty(Node.prototype, 'innerHTML', { get: function(){ return this._html; }, set: function(v){ this._html = String(v); } });
var list = new Node('d2jsp-list'), statusEl = new Node('d2jsp-status'), lamp = new Node('d2jsp-lamp');
var host = new Node('d2jsp-draft-host'), board = new Node('d2jsp-board');
var VIEW = { textContent: '' }, SUBJECT = { textContent: '' };
var document = {
  documentElement: { classList: { contains: function(){ return false; } } },
  getElementById: function(id){ return ({ 'd2jsp-list': list, 'd2jsp-status': statusEl, 'd2jsp-lamp': lamp, 'd2jsp-draft-host': host, 'd2jsp-board': board })[id] || null; },
  querySelector: function(sel){
    if (sel === '#d2jsp-draft-host [data-d2jsp-draft-view]') return VIEW;
    if (sel === '#d2jsp-draft-host [data-d2jsp-draft-subject]') return SUBJECT;
    return null;
  },
  querySelectorAll: function(){ return []; },
  addEventListener: function(type, fn){ if (LISTEN[type]) LISTEN[type].push(fn); },
  createElement: function(){ return new Node(''); },
  body: { appendChild: function(){} }
};
var RAW = {};
var localStorage = { getItem: function(k){ return Object.prototype.hasOwnProperty.call(RAW, k) ? RAW[k] : null; },
                     setItem: function(k, v){ RAW[k] = String(v); }, removeItem: function(k){ delete RAW[k]; } };
var location = { hostname: '127.0.0.1' };
var ASSIGN = { 'Grief': 'm1', 'Shako': 'm2', 'Gull': 'm1' };
var COPIES = { 'Grief': 3, 'Shako': 1, 'Gull': 1 };
var DOORS = [], SLOTS = {};
function copyCount(n){ return COPIES[n] || 1; }
// the stub trade door (REG-2880/2881): records every call; a listing is a slot, a trade-out drops one copy (the last leaves)
var window = { addEventListener: function(){}, LSR: { getItem: function(k){ return k === 'd2r_muleAssign' ? JSON.stringify(ASSIGN) : null; } },
  _vaultTradeEvent: function(ev){
    DOORS.push(['trade', ev.kind, ev.name]);
    var s = SLOTS[ev.name] || (SLOTS[ev.name] = []);
    if (ev.kind === 'listed') {
      if (s.length >= copyCount(ev.name)) return { ok: false, why: 'every copy of ' + ev.name + ' is already listed' };
      s.push({ ci: s.length, state: 'listed', post: ev.post || null }); return { ok: true, why: 'copy ' + s.length + ' is listed' };
    }
    var have = copyCount(ev.name); s.shift();
    if (have > 1) { COPIES[ev.name] = have - 1; return { ok: true, why: 'copy 1 of ' + have + ' left the vault count (↶ Undo in the toolbar puts it back)' }; }
    delete ASSIGN[ev.name]; return { ok: true, why: ev.name + ' left the vault count (↶ Undo in the toolbar puts it back)' };
  },
  _vaultTradeOf: function(n){ return (SLOTS[n] || []).slice(); } };
var ANSWER = null;
function fetch(url){
  if (String(url) === '/api/d2jsp_send') return Promise.resolve({ status: 200, json: function(){ return Promise.resolve(ANSWER); } });
  return Promise.resolve({ status: 200, json: function(){ return Promise.resolve({ state: 'unknown', fg: null, reason: 'no prices', n: 0 }); } });
}
function flush(){ return new Promise(function(r){ setTimeout(r, 0); }); }
function button(attrs, selfSel){
  var b = { getAttribute: function(k){ return Object.prototype.hasOwnProperty.call(attrs, k) ? attrs[k] : null; } };
  b.closest = function(sel){ return (sel === '#tab-d2jsp' || selfSel.indexOf(sel) >= 0) ? b : null; };
  return b;
}
"""

SCENARIO = r"""
RAW['d2r_d2jsp_fg'] = JSON.stringify({ 'Grief': '55', 'Shako': '30', 'Gull': '5' });
function click(attrs, sel){ LISTEN.click.forEach(function(f){ f({ target: button(attrs, sel), preventDefault: function(){} }); }); }
async function post(name, answer){
  ANSWER = answer;
  var d = d2jspDraft(name, '', '', copyCount(name), Number(JSON.parse(RAW['d2r_d2jsp_fg'])[name]));   // the draft the room shows
  VIEW.textContent = d.body; SUBJECT.textContent = d.subject;
  click({ 'data-d2jsp-post': name, 'data-d2jsp-send': '1' }, []);
  for (var i = 0; i < 6; i++) await flush();
}
function state(n){ var m = window._d2jspCardHtml(n).match(/data-d2jsp-state="([^"]*)"/); return m ? m[1] : null; }
(async function(){
  var out = {};
  out.draft = { state: state('Grief'), chip: window._d2jspCardHtml('Grief') };
  await post('Grief', { ok: true, reason: 'submitted', topic: '""" + TOPIC + r"""' });
  out.listed = { st: state('Grief'), card: window._d2jspCardHtml('Grief') };
  await post('Gull', { ok: false, reason: 'maybe-sent', board: 268, at: 'x' });
  out.maybe = { state: state('Gull'), card: window._d2jspCardHtml('Gull') };
  DOORS.length = 0;
  click({ 'data-d2jsp-sold': 'Grief' }, ['[data-d2jsp-sold]']);
  out.tradeMany = { doors: DOORS.slice(), state: state('Grief'), status: statusEl.textContent,
                    row: JSON.parse(RAW['d2r_d2jsp_log']).Grief.slice(-1)[0], card: window._d2jspCardHtml('Grief') };
  DOORS.length = 0;
  click({ 'data-d2jsp-sold': 'Shako' }, ['[data-d2jsp-sold]']);
  out.tradeOne = { doors: DOORS.slice(), assign: Object.keys(ASSIGN), row: JSON.parse(RAW['d2r_d2jsp_log']).Shako.slice(-1)[0] };
  window._d2jspShow();
  out.keptCard = list._html.indexOf('data-d2jsp-item="Shako"') >= 0;
  DOORS.length = 0;
  click({ 'data-d2jsp-sold': 'Shako' }, ['[data-d2jsp-sold]']);
  out.forSale = { doors: DOORS.slice(), state: state('Shako'), row: JSON.parse(RAW['d2r_d2jsp_log']).Shako.slice(-1)[0] };
  process.stdout.write(JSON.stringify(out));
})().catch(function(e){ process.stderr.write(String(e && e.stack || e)); process.exit(1); });
"""

@unittest.skipUnless(NODE, "node is required to run the room's own code")
class AD2jspItemMovesDraftListedTraded(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(BIBLE, encoding="utf-8") as fh:
            src = fh.read()
        pane = _between(src, 'id="tab-d2jsp"', 'id="tab-vault"')
        r = subprocess.run([NODE, "-"], input=FAKES + pane.split("<script>", 1)[1].split("</script>", 1)[0] + "\n" + SCENARIO,
                           capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise AssertionError("node failed: " + (r.stderr or r.stdout)[-2500:])
        cls.o = json.loads(r.stdout.strip().splitlines()[-1])

    def test_the_states_draft_listed_maybe(self):
        o = self.o
        self.assertEqual(o["draft"]["state"], "draft")
        self.assertIn('data-d2jsp-state="draft">Draft · not posted<', o["draft"]["chip"])
        self.assertEqual(o["listed"]["st"], "listed", o["listed"])
        self.assertIn('data-d2jsp-state="listed">Listed on board 268 · not traded yet<', o["listed"]["card"])
        self.assertEqual(o["maybe"]["state"], "maybe", o["maybe"])
        self.assertIn('data-d2jsp-state="maybe">Maybe listed · check board 268<', o["maybe"]["card"])

    def test_mark_traded_is_one_trade_out_event(self):
        m = self.o["tradeMany"]
        self.assertEqual(m["doors"], [["trade", "trade-out", "Grief"]], m["doors"])
        self.assertEqual(m["state"], "traded")
        self.assertEqual(m["row"]["kind"], "traded", m["row"])
        self.assertIn("copy 1 of 3 left the vault count (↶ Undo in the toolbar puts it back)", m["row"]["text"])
        self.assertIn("is marked traded; copy 1 of 3 left the vault count", m["status"])
        self.assertIn('data-d2jsp-state="traded">Traded<', m["card"])
        self.assertIn(">For sale</button>", m["card"])
        one = self.o["tradeOne"]
        self.assertEqual(one["doors"], [["trade", "trade-out", "Shako"]], one["doors"])
        self.assertNotIn("Shako", one["assign"], "PREMISE: the stub door did not take it out")
        self.assertIn("Shako left the vault count", one["row"]["text"])
        self.assertTrue(self.o["keptCard"], "a traded item that left the vault lost its card (and its SOLD block)")

    def test_for_sale_again_moves_no_count(self):
        f = self.o["forSale"]
        self.assertEqual(f["doors"], [], "un-marking touched the vault: %r" % f["doors"])
        self.assertNotEqual(f["state"], "traded")
        self.assertEqual(f["row"]["kind"], "for-sale")
        self.assertIn("not changed back", f["row"]["text"])


RED_PROOF = [
    {"why": "REG-2873 - Mark traded does not show the item as traded",
     "file": "bible.html",
     "find": "    var st = soldOf(name) ? 'traded' : (conf ? 'listed' : (maybe ? 'maybe' : 'draft'));\n",
     "replace": "    var st = (conf ? 'listed' : (maybe ? 'maybe' : 'draft'));\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2873 - an answer that may be up reads as a draft",
     "file": "bible.html",
     "find": "(conf ? 'listed' : (maybe ? 'maybe' : 'draft'))",
     "replace": "(conf ? 'listed' : 'draft')",
     "matches": 1, "needs": "node"},
    {"why": "REG-2873 - the card shows no trade state",
     "file": "bible.html",
     "find": "    return tradeChip(name) + head + '<details class=\"d2jsp-log\">",
     "replace": "    return head + '<details class=\"d2jsp-log\">",
     "matches": 1, "needs": "node"},
    {"why": "REG-2873 - Mark traded leaves the vault count alone (a traded copy waits as a where-is-it)",
     "file": "bible.html",
     "find": "      var how = sm[sn] ? markTraded(sn) : ",
     "replace": "      var how = sm[sn] ? 'x' : ",
     "matches": 1, "needs": "node"},
    {"why": "REG-2873 - a traded item that left the vault loses its card",
     "file": "bible.html",
     "find": "    Object.keys(readMap('d2r_d2jsp_sold')).forEach(function(n){ if (n && soldOf(n) && extra.indexOf(n) < 0) extra.push(n); });",
     "replace": "",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
