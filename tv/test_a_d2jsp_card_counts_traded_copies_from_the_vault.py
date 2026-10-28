# -*- coding: utf-8 -*-
"""REG-2883 (#83, the lead's follow-up to REG-2881: "the D2JSP card's sold mark is per NAME while trade-out takes ONE copy")
- THE D2JSP CARD COUNTS TRADED COPIES FROM THE VAULT, ONE SOURCE.

MEASURED before (the room's own code in node, and the whole page in node): Mark traded wrote the per-name mark
d2r_d2jsp_sold AND took one copy out through the trade door. On an item with 3 copies the card said "Traded", the Post
button went dead and the list posted a SOLD block, while the vault still held 2 copies, 2 of them listed. Nothing in the
vault remembered a traded copy for long: the removal journal is a ring of 20 batches.

Now:
  - the vault keeps one row per traded copy in its records store (tradedOut, newest 1,000). The trade door writes it on
    both paths. Every rebuild carries it, and vaultRestoreLast takes it back out. It is read through
    window._vaultTradedOf / window._vaultTradedNames;
  - the card reads the vault only: "1 of 3 traded · 2 listed on board N", "Traded · all 3 copies" when no copy remains,
    "Mark one traded" while several remain. The list posts the remaining copies for sale, and a SOLD block (copies: 3)
    once all are gone. A name whose every copy is traded keeps its card;
  - the per-name mark is never written for a name the vault holds. It stays for a name the vault does not hold (a planner
    pick), and the card says "Marked traded here · not in the vault";
  - a held name with an OLD per-name mark (the Mark sold of before) is a doubt. The card asks, a For sale button clears the
    mark, Mark traded takes a copy out and clears it, and until he answers the list posts it SOLD, his last word.

Room in node with a stub door that records every call. Whole page in node with the real door, records, journal and room.
Never a browser, never d2jsp. RED_PROOF below.
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

import vault_page_node as VPN  # noqa: E402

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
function unesc(s){ return String(s).replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&amp;/g, '&'); }
function shown(attr, tag){ var m = host._html.match(new RegExp(attr + '>([\\s\\S]*?)</' + tag + '>')); return m ? unesc(m[1]) : ''; }
var VIEW = { get textContent(){ return shown('data-d2jsp-draft-view', 'pre'); } };
var SUBJECT = { get textContent(){ return shown('data-d2jsp-draft-subject', 'p'); } };
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
var ASSIGN = { 'Grief': 'm1', 'Shako': 'm2' };
var COPIES = { 'Grief': 3, 'Shako': 1 };
function copyCount(n){ return COPIES[n] || 1; }
// the stub trade door, shaped like the real one: a listing is a slot; a trade-out takes one copy, records a traded row,
// and the last copy leaves the filings
var CALLS = [], SLOTS = {}, TRADED = {};
var window = { addEventListener: function(){}, LSR: { getItem: function(k){ return k === 'd2r_muleAssign' ? JSON.stringify(ASSIGN) : null; } },
  _vaultTradeEvent: function(ev){
    CALLS.push([ev.kind, ev.name]);
    var s = SLOTS[ev.name] || (SLOTS[ev.name] = []);
    if (ev.kind === 'listed') {
      if (s.length >= copyCount(ev.name)) return { ok: false, why: 'every copy of ' + ev.name + ' is already listed' };
      s.push({ ci: s.length, state: 'listed', post: ev.post || null }); return { ok: true, why: 'copy ' + s.length + ' is listed' };
    }
    if (!ASSIGN[ev.name]) return { ok: false, why: ev.name + ' is not in the vault' };
    var have = copyCount(ev.name); s.shift(); (TRADED[ev.name] = TRADED[ev.name] || []).push({ at: 'x' });
    if (have > 1) { COPIES[ev.name] = have - 1; return { ok: true, why: 'copy 1 of ' + have + ' left the vault count' }; }
    delete ASSIGN[ev.name]; delete COPIES[ev.name]; return { ok: true, why: ev.name + ' left the vault count' };
  },
  _vaultTradeOf: function(n){ return (SLOTS[n] || []).slice(); },
  _vaultTradedOf: function(n){ return (TRADED[n] || []).slice(); },
  _vaultTradedNames: function(){ return Object.keys(TRADED); } };
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
RAW['d2r_d2jsp_fg'] = JSON.stringify({ 'Grief': '55', 'Shako': '30', "Tyrael's Might": '400' });
RAW['d2r_d2jsp_gear'] = JSON.stringify({ "Tyrael's Might": { id: 'u-tyrael', rolls: {} } });
function click(attrs, sel){ LISTEN.click.forEach(function(f){ f({ target: button(attrs, sel), preventDefault: function(){} }); }); }
function sold(n){ click({ 'data-d2jsp-sold': n }, ['[data-d2jsp-sold]']); }
function forSale(n){ click({ 'data-d2jsp-forsale': n }, ['[data-d2jsp-forsale]']); }
function marks(){ return JSON.parse(RAW['d2r_d2jsp_sold'] || '{}'); }
function card(n){
  var h = window._d2jspCardHtml(n), chip = h.match(/data-d2jsp-state="([^"]*)">([^<]*)</);
  var mark = h.match(/<button type="button" class="vault-btn" data-d2jsp-sold="[^"]*"( hidden)?>([^<]*)</);
  var fsale = h.match(/data-d2jsp-forsale="[^"]*"( hidden)?>/);
  var post = h.match(/data-d2jsp-post="[^"]*"( disabled)?>Post</);
  return { state: chip && chip[1], say: chip && chip[2], mark: mark ? (mark[1] ? null : mark[2]) : 'absent',
           forSale: fsale ? !fsale[1] : 'absent', post: post ? !post[1] : 'absent' };
}
async function settle(){ for (var i = 0; i < 8; i++) await flush(); }
async function shop(){
  ANSWER = { ok: false, reason: 'not-posted' };
  click({ 'data-d2jsp-shop': '1' }, ['[data-d2jsp-shop]']);        // the draft the room shows: read, never posted
  return VIEW.textContent;
}
(async function(){
  var out = {};
  ANSWER = { ok: true, reason: 'submitted', topic: '""" + TOPIC + r"""' };
  click({ 'data-d2jsp-post': 'Grief' }, []); click({ 'data-d2jsp-post': 'Grief', 'data-d2jsp-send': '1' }, []); await settle();
  out.listed = card('Grief');
  CALLS.length = 0; sold('Grief');
  out.one = { calls: CALLS.slice(), card: card('Grief'), marks: marks(), status: statusEl.textContent, list: await shop() };
  sold('Grief');
  out.two = card('Grief');
  sold('Grief');
  window._d2jspShow();
  out.all = { card: card('Grief'), kept: list._html.indexOf('data-d2jsp-item="Grief"') >= 0, marks: marks(), list: await shop() };
  CALLS.length = 0; sold('Grief');
  out.again = { calls: CALLS.slice(), status: statusEl.textContent };
  // a planner pick the vault does not hold: the per-name mark, said so
  out.pickBefore = card("Tyrael's Might");
  CALLS.length = 0; sold("Tyrael's Might");
  out.pick = { calls: CALLS.slice(), card: card("Tyrael's Might"), marks: marks(), status: statusEl.textContent };
  sold("Tyrael's Might");
  out.pickBack = { card: card("Tyrael's Might"), marks: marks() };
  // an old per-name mark on a name the vault holds: a doubt
  RAW['d2r_d2jsp_sold'] = JSON.stringify({ 'Shako': 1 });
  out.ask = { card: card('Shako'), list: await shop() };
  CALLS.length = 0; forSale('Shako');
  out.cleared = { calls: CALLS.slice(), card: card('Shako'), marks: marks(), status: statusEl.textContent };
  RAW['d2r_d2jsp_sold'] = JSON.stringify({ 'Shako': 1 });
  CALLS.length = 0; sold('Shako');
  out.askTraded = { calls: CALLS.slice(), card: card('Shako'), marks: marks() };
  process.stdout.write(JSON.stringify(out));
})().catch(function(e){ process.stderr.write(String(e && e.stack || e)); process.exit(1); });
"""

PAGE = r"""
var W = window, GULL = 'Gull (dagger)', SHAKO = null;
function paint(){ W.renderVault(); H.flush(60, 3); }
function chip(n){ var m = W._d2jspCardHtml(n).match(/data-d2jsp-state="([^"]*)">([^<]*)</); return m ? [m[1], m[2]] : null; }
function stored(){ var s = JSON.parse(W.LSR.getItem('d2r_vaultRecords') || '{}'); return (s.tradedOut || []).map(function(t){ return t.name; }); }
W._vaultAutoIntakeSet(false);
W.vaultHandAdd('Gull'); W.vaultHandAdd('Gull'); W.vaultHandAdd('Gull'); SHAKO = (W.vaultHandAdd('Shako') || {}).name;
W.vaultAssign(GULL, 'uni-weap'); W.vaultAssign(SHAKO, 'uni-armor'); paint();
OUT.start = { chip: chip(GULL), traded: W._vaultTradedOf(GULL).length };
OUT.say = W._d2jspMarkTraded(GULL); paint();
OUT.one = { chip: chip(GULL), traded: W._vaultTradedOf(GULL).length, stored: stored(), count: copyCount(GULL) };
W.vaultHandAdd('Lightsabre'); var pr = W._vaultRecordsPersist(); paint();
OUT.rebuilt = { wrote: !!(pr && pr.ok), stored: stored(), chip: chip(GULL) };
OUT.undo = W.vaultRestoreLast(); paint();
OUT.undone = { chip: chip(GULL), traded: W._vaultTradedOf(GULL).length, count: copyCount(GULL) };
OUT.shakoSay = W._d2jspMarkTraded(SHAKO); paint();
OUT.shako = { name: SHAKO, owned: owned.has(SHAKO), traded: W._vaultTradedOf(SHAKO).length, names: W._vaultTradedNames(), chip: chip(SHAKO) };
OUT.shakoUndo = W.vaultRestoreLast(); paint();
OUT.shakoBack = { owned: owned.has(SHAKO), traded: W._vaultTradedOf(SHAKO).length, stored: stored() };
"""


@unittest.skipUnless(NODE, "node is required to run the room's own code - UNMEASURED here, never a pass")
class AD2jspCardCountsTradedCopiesFromTheVault(unittest.TestCase):

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
        cls.v = VPN.run(PAGE, prelude="localStorage.setItem('d2r_ownerClaim', '*');\n", timeout=600)

    def test_one_of_three_traded_is_counted_and_the_rest_stay_for_sale(self):
        o = self.o
        self.assertEqual(o["listed"]["say"], "Listed on board 268 · not traded yet", "PREMISE: %r" % o["listed"])
        self.assertEqual(o["listed"]["mark"], "Mark one traded", o["listed"])
        one = o["one"]
        self.assertEqual(one["calls"], [["trade-out", "Grief"]], one["calls"])
        self.assertEqual((one["card"]["state"], one["card"]["say"]), ("part-traded", "1 of 3 traded · 2 listed on board 268"), one["card"])
        self.assertEqual(one["marks"], {}, "Mark traded wrote the per-name mark for a name the vault holds: %r" % one["marks"])
        self.assertTrue(one["card"]["post"], "the Post button went dead while 2 copies are for sale: %r" % one["card"])
        self.assertIn("WTS Grief", one["list"])
        self.assertIn("copies: 2", one["list"], "the list does not offer the 2 copies left: %r" % one["list"])
        self.assertNotIn("SOLD Grief", one["list"], "the list posts the whole name SOLD while 2 copies remain")
        self.assertEqual(o["two"]["say"], "2 of 3 traded · 1 listed on board 268", o["two"])
        self.assertEqual(o["two"]["mark"], "Mark traded", o["two"])

    def test_the_name_reads_traded_only_when_no_copy_remains_and_keeps_its_card(self):
        a = self.o["all"]
        self.assertEqual((a["card"]["state"], a["card"]["say"]), ("traded", "Traded · all 3 copies"), a["card"])
        self.assertIsNone(a["card"]["mark"], "a name with no copy left still offers Mark traded: %r" % a["card"])
        self.assertTrue(a["kept"], "a name whose every copy was traded lost its card")
        self.assertEqual(a["marks"], {}, a["marks"])
        self.assertIn("SOLD Grief", a["list"], a["list"])
        self.assertIn("copies: 3", a["list"], a["list"])
        g = self.o["again"]
        self.assertEqual(g["calls"], [], "a fourth Mark traded reached the vault: %r" % g)
        self.assertIn("Every copy of Grief is already traded", g["status"])

    def test_a_planner_pick_keeps_the_per_name_mark_and_says_so(self):
        o = self.o
        self.assertEqual(o["pickBefore"]["mark"], "Mark traded", "PREMISE: %r" % o["pickBefore"])
        p = o["pick"]
        self.assertEqual(p["calls"], [], "a name the vault does not hold went to the vault door: %r" % p["calls"])
        self.assertEqual(p["marks"], {"Tyrael's Might": 1}, p["marks"])
        self.assertEqual((p["card"]["state"], p["card"]["say"]), ("marked", "Marked traded here · not in the vault"), p["card"])
        self.assertEqual(p["card"]["mark"], "For sale", p["card"])
        self.assertIn("it is not in the vault, so no count changed", p["status"])
        b = o["pickBack"]
        self.assertEqual(b["marks"], {}, b)
        self.assertEqual(b["card"]["state"], "draft", b)

    def test_an_old_mark_on_a_held_name_is_a_question_with_two_answers(self):
        a = self.o["ask"]
        self.assertEqual(a["card"]["state"], "ask", a["card"])
        self.assertIn("Marked sold here, but the vault still holds 1 copy", a["card"]["say"])
        self.assertTrue(a["card"]["forSale"], "the doubt offers no For sale answer: %r" % a["card"])
        self.assertIn("SOLD Shako", a["list"], "his last word (SOLD) was dropped before he answered: %r" % a["list"])
        c = self.o["cleared"]
        self.assertEqual(c["calls"], [], "For sale on the doubt touched the vault: %r" % c["calls"])
        self.assertEqual(c["marks"], {}, c)
        self.assertEqual(c["card"]["state"], "draft", c)
        self.assertFalse(c["card"]["forSale"], c["card"])
        self.assertIn("the old sold mark is cleared, and the vault holds 1 copy", c["status"])
        t = self.o["askTraded"]
        self.assertEqual(t["calls"], [["trade-out", "Shako"]], t["calls"])
        self.assertEqual(t["marks"], {}, "Mark traded left the old mark beside the vault's count: %r" % t["marks"])
        self.assertEqual(t["card"]["state"], "traded", t["card"])

    def test_on_the_whole_page_the_vault_keeps_the_traded_copy_through_a_rebuild_and_the_undo_takes_it_back(self):
        v = self.v
        self.assertEqual(v["__boot"]["errors"], [], v["__boot"])
        self.assertEqual((v["start"]["traded"], v["start"]["chip"][0]), (0, "draft"), "PREMISE: %r" % v["start"])
        one = v["one"]
        self.assertTrue(v["say"].startswith("copy 3 of 3 left the vault count"), v["say"])
        self.assertEqual((one["traded"], one["stored"], one["count"]), (1, ["Gull (dagger)"], 2), one)
        self.assertEqual(one["chip"], ["part-traded", "1 of 3 traded · 2 left, not listed"], one)
        r = v["rebuilt"]
        self.assertTrue(r["wrote"], "PREMISE: the rebuild did not run: %r" % r)
        self.assertEqual(r["stored"], ["Gull (dagger)"], "a rebuild of the records dropped the traded row: %r" % r)
        self.assertEqual(v["undo"]["restored"], 1, v["undo"])
        self.assertEqual((v["undone"]["traded"], v["undone"]["count"], v["undone"]["chip"][0]), (0, 3, "draft"), v["undone"])

    def test_on_the_whole_page_the_last_copy_is_counted_traded_and_comes_back_whole(self):
        v = self.v
        s = v["shako"]
        self.assertTrue(s["name"], "PREMISE: %r" % s)
        self.assertIn("left the vault count", v["shakoSay"])
        self.assertNotIn("refused the traded row", v["shakoSay"])
        self.assertEqual((s["owned"], s["traded"]), (False, 1), s)
        self.assertIn(s["name"], s["names"])
        self.assertEqual(s["chip"], ["traded", "Traded"], s)
        b = v["shakoBack"]
        self.assertEqual(v["shakoUndo"]["restored"], 1, v["shakoUndo"])
        self.assertEqual((b["owned"], b["traded"], b["stored"]), (True, 0, []), b)


RED_PROOF = [
    {"why": "REG-2883 - the card calls the whole name traded when one copy of three left",
     "file": "bible.html",
     "find": "              all: !held && traded > 0, pick: mark && !held && !traded, legacy: mark && held };",
     "replace": "              all: traded > 0, pick: mark && !held && !traded, legacy: mark && held };",
     "matches": 1, "needs": "node"},
    {"why": "REG-2883 - Mark traded writes the per-name mark for a name the vault holds",
     "file": "bible.html",
     "find": "        if (sm[sn]) { delete sm[sn]; writeMap('d2r_d2jsp_sold', sm); }\n        soldNow = true;",
     "replace": "        sm[sn] = 1; writeMap('d2r_d2jsp_sold', sm);\n        soldNow = true;",
     "matches": 1, "needs": "node"},
    {"why": "REG-2883 - the trade door records no traded row for one of several copies",
     "file": "bible.html",
     "find": "    if (!write(rest, _tWith(raw))) return",
     "replace": "    if (!write(rest)) return",
     "matches": 1, "needs": "node"},
    {"why": "REG-2883 - the trade door records no traded row for the last copy",
     "file": "bible.html",
     "find": "for (var x in _r2) st[x] = _r2[x]; st.tradedOut = _tWith(_r2); return _vrRecGuardedSet(st);",
     "replace": "for (var x in _r2) st[x] = _r2[x]; return _vrRecGuardedSet(st);",
     "matches": 1, "needs": "node"},
    {"why": "REG-2883 - a rebuild of the records drops the traded rows",
     "file": "bible.html",
     "find": "    if (prior && Array.isArray(prior.tradedOut) && prior.tradedOut.length) store.tradedOut = prior.tradedOut;\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2883 - an undo of one of several copies leaves its traded row counted",
     "file": "bible.html",
     "find": "          var _coT = _vrTradedDrop(_coRaw.tradedOut, _coN); if (_coT) _coStore.tradedOut = _coT;",
     "replace": "          var _coT = null;",
     "matches": 1, "needs": "node"},
    {"why": "REG-2883 - an undo of the last copy leaves its traded row counted",
     "file": "bible.html",
     "find": "        if (_trHit) { var _trS = {}; for (var q in _tr0) _trS[q] = _tr0[q]; _trS.tradedOut = _trT; _vrRecGuardedSet(_trS); }",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2883 - a name whose every copy was traded loses its card",
     "file": "bible.html",
     "find": "    try { (typeof window._vaultTradedNames === 'function' ? window._vaultTradedNames() : []).forEach(",
     "replace": "    try { [].forEach(",
     "matches": 1, "needs": "node"},
    {"why": "REG-2883 - the SOLD block of an all-traded name says one copy",
     "file": "bible.html",
     "find": "        name: n, base: baseOf(n), mods: modsOf(n), copies: tv.all ? tv.traded : copiesOf(n),",
     "replace": "        name: n, base: baseOf(n), mods: modsOf(n), copies: copiesOf(n),",
     "matches": 1, "needs": "node"},
    {"why": "REG-2883 - an old mark on a held name posts it for sale before he answers",
     "file": "bible.html",
     "find": "    v.sold = v.all || v.pick || v.legacy;",
     "replace": "    v.sold = v.all || v.pick;",
     "matches": 1, "needs": "node"},
    {"why": "REG-2883 - the doubt's For sale is never offered",
     "file": "bible.html",
     "find": "data-d2jsp-forsale=\"' + esc(n) + '\"' + (tv.legacy ? '' : ' hidden') + '>For sale</button>'",
     "replace": "data-d2jsp-forsale=\"' + esc(n) + '\" hidden>For sale</button>'",
     "matches": 1, "needs": "node"},
    {"why": "REG-2883 - a planner pick marked traded is not said to be outside the vault",
     "file": "bible.html",
     "find": "      : t.state === 'marked' ? 'Marked traded here · not in the vault'\n",
     "replace": "      : t.state === 'marked' ? 'Traded'\n",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
