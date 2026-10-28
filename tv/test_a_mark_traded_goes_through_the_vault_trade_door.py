# -*- coding: utf-8 -*-
"""REG-2881 (#83, his rulings: "the reconciler takes trade-out / trade-in events"; "Proven gone (... trade-out ...) is
removed automatically into a Vault log with undo"; the lead's wiring brief: one door) - MARK TRADED IS THE VAULT'S
TRADE-OUT, THROUGH THE ONE TRADE DOOR.

MEASURED before (REG-2873's tradeOut, the room's own code): Mark traded took the copy out of the vault itself, by a second
path beside window._vaultTradeEvent. With several copies it called the copy door, vaultCopyAdjust(name, -1). That door
drops the LAST copy's record, never the one he listed and traded, so the traded copy's MOVE task stayed and another copy's
went. It journals nothing, so vaultRestoreLast could not put it back. With one copy it called vaultRemove on the trade-out
lane. The room armed the toolbar Undo itself.

Now Mark traded calls window._vaultTradeEvent({kind: 'trade-out', name}) and nothing else. The door takes the listed copy
(else the last), journals that copy's own record on the trade-out lane, closes the rest up, and arms the toolbar Undo with
a snapshot taken before anything moved. The status line and the post log say the door's own words. A refusal says "the
vault count is unchanged" and why. No other trade-out call is left in the room. (REG-2883: Mark traded on a name the
vault holds is always one more copy through the door; the per-name "For sale again" is a planner pick's only, so the
REG-2834 Undo sentence on it is retired with it. The way back from a trade-out is the toolbar Undo the door armed.)

The room runs in node with a stub door that records every call. The whole page runs in node with the real door, records,
journal and Undo (vault_page_node). Never a browser, never d2jsp. RED_PROOF below.
"""
from __future__ import annotations

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
from console_safe import enable
enable()

import vault_page_node as VPN  # noqa: E402

ROOT = os.path.dirname(HERE)
BIBLE = os.path.join(ROOT, "bible.html")
NODE = shutil.which("node")


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
var document = {
  documentElement: { classList: { contains: function(){ return false; } } },
  getElementById: function(id){ return ({ 'd2jsp-list': list, 'd2jsp-status': statusEl, 'd2jsp-lamp': lamp, 'd2jsp-draft-host': host, 'd2jsp-board': board })[id] || null; },
  querySelector: function(){ return null; },
  querySelectorAll: function(){ return []; },
  addEventListener: function(type, fn){ if (LISTEN[type]) LISTEN[type].push(fn); },
  createElement: function(){ return new Node(''); },
  body: { appendChild: function(){} }
};
var RAW = {};
var localStorage = { getItem: function(k){ return Object.prototype.hasOwnProperty.call(RAW, k) ? RAW[k] : null; },
                     setItem: function(k, v){ RAW[k] = String(v); }, removeItem: function(k){ delete RAW[k]; } };
var location = { hostname: '127.0.0.1' };
var ASSIGN = { 'Grief': 'm1', 'Shako': 'm2' };
function copyCount(n){ return ({ 'Grief': 3 })[n] || 1; }
// the stub trade door and the vault doors a second path would call: every call is recorded
var CALLS = [], REFUSE = {};
var window = { addEventListener: function(){}, LSR: { getItem: function(k){ return k === 'd2r_muleAssign' ? JSON.stringify(ASSIGN) : null; } },
  _vaultUndo: null,
  _vaultTradeEvent: function(ev){
    CALLS.push(['trade', ev.kind, ev.name]);
    if (REFUSE[ev.name]) return { ok: false, kind: ev.kind, name: ev.name, why: REFUSE[ev.name] };
    window._vaultUndo = { what: 'the trade-out of ' + ev.name };
    return { ok: true, kind: ev.kind, name: ev.name, copyIx: 1, why: 'copy 2 of 3 left the vault count (↶ Undo in the toolbar puts it back)' };
  },
  _vaultTradeOf: function(){ return []; },
  vaultCopyAdjust: function(n, d){ CALLS.push(['copy', n, d]); },
  vaultRemove: function(names){ CALLS.push(['remove', names]); return { removed: names.slice(), skipped: [] }; },
  _vaultUndoSnap: function(){ CALLS.push(['snap']); return 'snap'; },
  _vaultUndoTake: function(w){ CALLS.push(['undo', w]); return true; } };
function fetch(){ return Promise.resolve({ status: 200, json: function(){ return Promise.resolve({ state: 'unknown', fg: null, reason: 'no prices', n: 0 }); } }); }
function button(attrs, selfSel){
  var b = { getAttribute: function(k){ return Object.prototype.hasOwnProperty.call(attrs, k) ? attrs[k] : null; } };
  b.closest = function(sel){ return (sel === '#tab-d2jsp' || selfSel.indexOf(sel) >= 0) ? b : null; };
  return b;
}
"""

SCENARIO = r"""
function click(attrs, sel){ LISTEN.click.forEach(function(f){ f({ target: button(attrs, sel), preventDefault: function(){} }); }); }
function sold(n){ click({ 'data-d2jsp-sold': n }, ['[data-d2jsp-sold]']); }
function last(n){ var r = JSON.parse(RAW['d2r_d2jsp_log'] || '{}')[n] || []; return r[r.length - 1] || null; }
var out = {};
CALLS.length = 0; sold('Grief');
out.traded = { calls: CALLS.slice(), status: statusEl.textContent, row: last('Grief') };
CALLS.length = 0; sold('Grief');
out.second = { calls: CALLS.slice(), row: last('Grief'), marks: JSON.parse(RAW['d2r_d2jsp_sold'] || '{}') };
REFUSE['Shako'] = 'nothing changed - the copy records are held (law)';
CALLS.length = 0; sold('Shako');
out.refused = { calls: CALLS.slice(), status: statusEl.textContent, row: last('Shako') };
process.stdout.write(JSON.stringify(out));
"""

PAGE = r"""
var W = window, GULL = 'Gull (dagger)', SHAKO = null;
function paint(){ W.renderVault(); H.flush(60, 3); }
function rows(n){ return (JSON.parse(W.LSR.getItem('d2r_vaultRecords') || '{}').records || []).filter(function(r){ return r && r.name === n; })
  .sort(function(a, b){ return (a.copyIx || 0) - (b.copyIx || 0); }).map(function(r){ return { ci: r.copyIx || 0, cell: r.move && r.move.to ? r.move.to.cell : null, trade: r.trade ? r.trade.state : null }; }); }
// a snapshot is the Save-profile text; its "saved" stamp is the clock, so two snapshots of one state compare without it
function same(a, b){ try { var x = JSON.parse(a), y = JSON.parse(b); delete x.saved; delete y.saved; return JSON.stringify(x) === JSON.stringify(y); } catch (e) { return false; } }
function lastBatch(){ var l = W.vaultRemovalLog() || []; var b = l[l.length - 1] || null; return b && { lane: b.lane, names: b.names, copyOut: b.copyOut ? { name: b.copyOut.name, copyIx: b.copyOut.copyIx, cell: b.copyOut.row && b.copyOut.row.move && b.copyOut.row.move.to ? b.copyOut.row.move.to.cell : null } : null }; }
W._vaultAutoIntakeSet(false);
W.vaultHandAdd('Gull'); W.vaultHandAdd('Gull'); W.vaultHandAdd('Gull'); SHAKO = (W.vaultHandAdd('Harlequin Crest') || {}).name;   /* a bare 'Shako' is asked since REG-2858; the unique's typed name files (REG-2897) */
W.vaultAssign(GULL, 'uni-weap'); W.vaultAssign(SHAKO, 'uni-armor'); paint();
OUT.start = { rows: rows(GULL), count: copyCount(GULL) };
W._vaultTradeEvent({ kind: 'listed', name: GULL, copyIx: 1, post: 'https://forums.d2jsp.org/topic.php?t=9001&f=268' }); paint();
var before = W._vaultUndoSnap();
OUT.say = W._d2jspMarkTraded(GULL); paint();
var after = W._vaultUndoSnap();
OUT.out = { rows: rows(GULL), count: copyCount(GULL), batch: lastBatch(), undo: W._vaultUndo && W._vaultUndo.what,
            undoIsBefore: !!(W._vaultUndo && same(W._vaultUndo.text, before)), undoIsAfter: !!(W._vaultUndo && same(W._vaultUndo.text, after)) };
OUT.restore = W.vaultRestoreLast(); paint();
OUT.back = { rows: rows(GULL), count: copyCount(GULL) };
OUT.shakoSay = W._d2jspMarkTraded(SHAKO); paint();
OUT.shako = { name: SHAKO, owned: owned.has(SHAKO), batch: lastBatch(), undo: W._vaultUndo && W._vaultUndo.what };
OUT.shakoRestore = W.vaultRestoreLast(); paint();
OUT.shakoBack = owned.has(SHAKO);
OUT.notHeld = W._d2jspMarkTraded('The Grandfather');
"""


def _room_code(src):
    """The room's script with comments stripped: what runs, never what the prose says."""
    script = _between(src, 'id="tab-d2jsp"', 'id="tab-vault"').split("<script>", 1)[1].split("</script>", 1)[0]
    return re.sub(r"/\*[\s\S]*?\*/", "", script)


@unittest.skipUnless(NODE, "node is required to run the room's own code - UNMEASURED here, never a pass")
class AMarkTradedGoesThroughTheVaultTradeDoor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(BIBLE, encoding="utf-8") as fh:
            cls.src = fh.read()
        pane = _between(cls.src, 'id="tab-d2jsp"', 'id="tab-vault"')
        r = subprocess.run([NODE, "-"], input=FAKES + pane.split("<script>", 1)[1].split("</script>", 1)[0] + "\n" + SCENARIO,
                           capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise AssertionError("node failed: " + (r.stderr or r.stdout)[-2500:])
        cls.o = json.loads(r.stdout.strip().splitlines()[-1])
        cls.v = VPN.run(PAGE, prelude="localStorage.setItem('d2r_ownerClaim', '*');\n", timeout=600)

    def test_mark_traded_is_one_call_to_the_trade_door_and_says_its_words(self):
        t = self.o["traded"]
        self.assertEqual(t["calls"], [["trade", "trade-out", "Grief"]],
                         "Mark traded did not go through the one door alone: %r" % t["calls"])
        self.assertIn("Grief is marked traded; copy 2 of 3 left the vault count (↶ Undo in the toolbar puts it back)", t["status"])
        self.assertEqual(t["row"]["kind"], "traded", t["row"])
        self.assertIn("Marked traded: copy 2 of 3 left the vault count", t["row"]["text"])

    def test_a_refused_trade_out_says_the_count_is_unchanged_and_why(self):
        r = self.o["refused"]
        self.assertEqual(r["calls"], [["trade", "trade-out", "Shako"]], r["calls"])
        self.assertIn("the vault count is unchanged: nothing changed - the copy records are held (law)", r["status"])
        self.assertIn("the vault count is unchanged", r["row"]["text"])

    def test_a_second_mark_traded_is_a_second_copy_through_the_same_door(self):
        h = self.o["second"]
        self.assertEqual(h["calls"], [["trade", "trade-out", "Grief"]], "the second click did not go through the door: %r" % h["calls"])
        self.assertEqual(h["row"]["kind"], "traded", h["row"])
        self.assertEqual(h["marks"], {}, "the room wrote a per-name mark beside the door: %r" % h["marks"])

    def test_no_second_trade_out_path_is_left_in_the_room(self):
        code = _room_code(self.src)
        self.assertEqual(code.count("window._vaultTradeEvent({ kind: 'trade-out'"), 1, "the room trades out from more than one place")
        for call in ("vaultCopyAdjust(", "vaultRemove(", "_vaultUndoTake(", "_vaultUndoSnap("):
            self.assertNotIn(call, code, "the room calls %s itself, beside the trade door" % call)

    def test_on_the_whole_page_the_traded_copy_leaves_through_the_journal_and_the_undo_puts_it_back(self):
        v = self.v
        self.assertEqual(v["__boot"]["errors"], [], v["__boot"])
        s = v["start"]
        self.assertEqual(s["count"], 3, "PREMISE: %r" % s)
        self.assertEqual(len(set(r["cell"] for r in s["rows"])), 3, "PREMISE: the three copies do not hold three cells: %r" % s)
        o = v["out"]
        self.assertTrue(v["say"].startswith("copy 2 of 3 left the vault count"), v["say"])
        self.assertEqual(o["count"], 2, o)
        self.assertEqual(o["batch"], {"lane": "trade-out", "names": [], "copyOut": {"name": "Gull (dagger)", "copyIx": 1, "cell": s["rows"][1]["cell"]}},
                         "the journal does not carry the LISTED copy's own record: %r" % o["batch"])
        self.assertEqual([r["cell"] for r in o["rows"]], [s["rows"][0]["cell"], s["rows"][2]["cell"]],
                         "another copy's task left with it: %r" % o["rows"])
        self.assertEqual(o["undo"], "the trade-out of Gull (dagger)", o)
        self.assertTrue(o["undoIsBefore"] and not o["undoIsAfter"], "the toolbar Undo was not taken before the copy moved: %r" % o)
        b = v["back"]
        self.assertEqual(v["restore"]["restored"], 1, v["restore"])
        self.assertEqual(b["count"], 3, b)
        self.assertEqual([r["cell"] for r in b["rows"]], [r["cell"] for r in s["rows"]], "the undo did not put each copy back at its cell: %r" % b)

    def test_on_the_whole_page_a_last_copy_leaves_on_the_trade_out_lane_with_the_undo_armed(self):
        v = self.v
        self.assertIn("left the vault count (↶ Undo in the toolbar puts it back)", v["shakoSay"])
        sh = v["shako"]
        self.assertFalse(sh["owned"], sh)
        self.assertTrue(sh["name"], "PREMISE: the hand add of Shako named nothing: %r" % sh)
        self.assertEqual((sh["batch"]["lane"], sh["batch"]["names"]), ("trade-out", [sh["name"]]), sh)
        self.assertEqual(sh["undo"], "the trade-out of " + sh["name"], sh)
        self.assertTrue(v["shakoBack"], "vaultRestoreLast did not put the last copy back")
        self.assertTrue(v["notHeld"].startswith("the vault count is unchanged: "), v["notHeld"])
        self.assertIn("is not in the vault", v["notHeld"])


RED_PROOF = [
    {"why": "REG-2881 - Mark traded leaves the vault count alone (a traded copy waits as a where-is-it)",
     "file": "bible.html",
     "find": "        how = markTraded(sn);\n",
     "replace": "        how = 'it left the vault count';\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2881 - Mark traded takes a copy out by the copy door, a second path beside the trade door",
     "file": "bible.html",
     "find": "    try { r = (typeof window._vaultTradeEvent === 'function') ? window._vaultTradeEvent({ kind: 'trade-out', name: n }) : null; }",
     "replace": "    try { window.vaultCopyAdjust(n, -1); r = { ok: true, why: 'copy 2 of 3 left the vault count (↶ Undo in the toolbar puts it back)' }; }",
     "matches": 1, "needs": "node"},
    {"why": "REG-2881 - a refused trade-out is reported as gone",
     "file": "bible.html",
     "find": "    return r.ok ? r.why : ('the vault count is unchanged: ' + r.why);",
     "replace": "    return r.why;",
     "matches": 1, "needs": "node"},
    {"why": "REG-2881 - trading one of several copies arms no toolbar Undo",
     "file": "bible.html",
     "find": "'copy ' + (k + 1) + ' of ' + have + ' left the vault count' + _undoSay() };",
     "replace": "'copy ' + (k + 1) + ' of ' + have + ' left the vault count' };",
     "matches": 1, "needs": "node"},
    {"why": "REG-2881 - trading the last copy arms no toolbar Undo",
     "file": "bible.html",
     "find": "(_tKept ? '' : ' (the copy records refused the traded row, so the D2JSP card cannot count this trade)') + _undoSay())",
     "replace": "(_tKept ? '' : ' (the copy records refused the traded row, so the D2JSP card cannot count this trade)'))",
     "matches": 1, "needs": "node"},
    {"why": "REG-2881 - the toolbar Undo is taken after the copy left, so it cannot put it back",
     "file": "bible.html",
     "find": "window._vaultUndoTake(_undoWhat, '', _undoT)",
     "replace": "window._vaultUndoTake(_undoWhat, '')",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
