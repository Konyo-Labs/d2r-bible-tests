# -*- coding: utf-8 -*-
"""REG-2880 (#83, his ruling "copy records carry a trade state (listed / traded-out) ... design it now, wire it later";
the lead's wiring brief) - A CONFIRMED D2JSP POST LISTS ITS COPIES ON THE VAULT, THROUGH THE ONE TRADE DOOR.

MEASURED before (the room's own code in node, and the whole page in node): the D2JSP tab and the vault had two words for
"listed". The room called an item listed when its post log held a confirmed answer (REG-2873), and published that through
window._d2jspTradeState. The vault's copy records carry their own trade slot (REG-2877), which FIND, the MOVE row, the
window tile and the shelf cell read (REG-2878). Nothing wrote that slot: a confirmed post left every copy record with
trade: null, so the vault never showed the mark the post earned, and the room's chip said "Listed" from a log the vault
could not see.

Now a confirmed post (one item, or the list) calls window._vaultTradeEvent({kind: 'listed', name, post: topic}) until as
many copies are listed as the post offers (copiesOf). A re-post tops up only. An answer that may be up (maybe-sent), a
refusal or a lost answer lists nothing: a maybe stays a question to him. A SOLD block and a planner pick the vault does
not hold list nothing. A refusal from the door is said on the status line. The room's chip reads "Listed" from the vault's
slot; a confirmed post with no listed copy says "Posted on board N" and why there is no listing. The log-based listed
state and window._d2jspTradeState are retired.

The room runs in node with a stub door that records every call (the room-cut world of REG-2873's law). The whole page runs
in node with the real door, the real records and the real room (vault_page_node). Never a browser, never d2jsp.
RED_PROOF below.
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
TOPIC = "https://forums.d2jsp.org/topic.php?t=9001&f=268"
TOPIC2 = "https://forums.d2jsp.org/topic.php?t=9002&f=268"


def _between(src, start, end):
    i = src.index(start)
    j = src.index(end, i + len(start))
    return src[i + len(start):j]


# The room's script in a fake page. The draft view is read back from what openDraft painted, so a send compares the
# draft the room itself showed (open, then Post this draft), exactly as on the page.
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
var ASSIGN = { 'Grief': 'm1', 'Shako': 'm2', 'Wisp': 'm1', 'Gull': 'm1' };
var COPIES = { 'Grief': 3, 'Shako': 1, 'Wisp': 2, 'Gull': 1 };
function copyCount(n){ return COPIES[n] || 1; }
// the stub trade door: records every call; refuses what the real door refuses (a name it is told to, a copy past the count)
var EVENTS = [], SLOTS = {}, REFUSE = {};
var window = { addEventListener: function(){}, LSR: { getItem: function(k){ return k === 'd2r_muleAssign' ? JSON.stringify(ASSIGN) : null; } },
  _vaultTradeEvent: function(ev){
    EVENTS.push({ kind: ev.kind, name: ev.name, post: ev.post == null ? null : ev.post });
    if (REFUSE[ev.name]) return { ok: false, kind: ev.kind, name: ev.name, why: REFUSE[ev.name] };
    var s = SLOTS[ev.name] || (SLOTS[ev.name] = []);
    if (ev.kind !== 'listed') return { ok: true, kind: ev.kind, name: ev.name, why: 'ok' };
    if (s.length >= copyCount(ev.name)) return { ok: false, kind: ev.kind, name: ev.name, why: 'every copy of ' + ev.name + ' is already listed' };
    s.push({ ci: s.length, state: 'listed', at: '2026-10-28T20:00:00Z', post: ev.post || null });   // _vaultTradeOf's shape
    return { ok: true, kind: ev.kind, name: ev.name, copyIx: s.length - 1, why: 'copy ' + s.length + ' is listed' };
  },
  _vaultTradeOf: function(n){ return (SLOTS[n] || []).slice(); } };
var ANSWER = null, SENT = 0;
function fetch(url){
  if (String(url) === '/api/d2jsp_send') { SENT++; return Promise.resolve({ status: 200, json: function(){ return Promise.resolve(ANSWER); } }); }
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
RAW['d2r_d2jsp_fg'] = JSON.stringify({ 'Grief': '55', 'Shako': '30', 'Wisp': '9', 'Gull': '5', "Tyrael's Might": '400' });
function click(attrs, sel){ LISTEN.click.forEach(function(f){ f({ target: button(attrs, sel), preventDefault: function(){} }); }); }
function of(n){ return EVENTS.filter(function(e){ return e.name === n; }); }
async function settle(){ for (var i = 0; i < 8; i++) await flush(); }
async function one(name, answer){
  ANSWER = answer; statusEl.textContent = '';
  click({ 'data-d2jsp-post': name }, []);                                   // the draft the room shows
  click({ 'data-d2jsp-post': name, 'data-d2jsp-send': '1' }, []);           // Post this draft
  await settle();
  return { status: statusEl.textContent, card: window._d2jspCardHtml(name) };
}
async function shop(answer){
  ANSWER = answer; statusEl.textContent = '';
  click({ 'data-d2jsp-shop': '1' }, ['[data-d2jsp-shop]']);
  click({ 'data-d2jsp-shop': '1', 'data-d2jsp-send': '1' }, ['[data-d2jsp-shop]']);
  await settle();
  return { status: statusEl.textContent };
}
function chip(card){ var m = String(card).match(/<div class="d2jsp-state" data-d2jsp-state="([^"]*)">([^<]*)</); return m ? [m[1], m[2]] : null; }
(async function(){
  var out = {}, ok = function(t){ return { ok: true, reason: 'submitted', topic: t }; };
  out.draftChip = chip(window._d2jspCardHtml('Grief'));
  var g = await one('Grief', ok('""" + TOPIC + r"""'));
  out.grief = { events: of('Grief'), status: g.status, chip: chip(g.card), sent: SENT };
  await one('Grief', ok('""" + TOPIC + r"""'));
  out.griefAgain = { events: of('Grief').length, sent: SENT };
  var w1 = await one('Wisp', { ok: false, reason: 'maybe-sent', board: 268, at: 'x' });
  var w2 = await one('Wisp', { ok: false, reason: 'not-posted' });
  var w3 = await one('Wisp', { ok: false, reason: 'busy' });
  out.wisp = { events: of('Wisp'), chip: chip(w1.card), chipAfter: chip(w3.card), status: [w1.status, w2.status, w3.status], sent: SENT };
  REFUSE['Shako'] = 'nothing changed - the copy records are held (law)';
  var s = await one('Shako', ok('""" + TOPIC + r"""'));
  out.shako = { events: of('Shako'), status: s.status, chip: chip(s.card) };
  delete REFUSE['Shako'];
  RAW['d2r_d2jsp_sold'] = JSON.stringify({ 'Gull': 1 });
  RAW['d2r_d2jsp_gear'] = JSON.stringify({ "Tyrael's Might": { id: 'u-tyrael', rolls: {} } });
  var before = EVENTS.length;
  var sh = await shop(ok('""" + TOPIC2 + r"""'));
  out.list = { events: EVENTS.slice(before), status: sh.status, sent: SENT,
               tyrael: chip(window._d2jspCardHtml("Tyrael's Might")), wisp: chip(window._d2jspCardHtml('Wisp')) };
  process.stdout.write(JSON.stringify(out));
})().catch(function(e){ process.stderr.write(String(e && e.stack || e)); process.exit(1); });
"""

PAGE = r"""
var W = window, GULL = 'Gull (dagger)', SHAKO = null;
function paint(){ W.renderVault(); H.flush(60, 3); }
function slots(n){ return (W._vaultTradeOf(n) || []).map(function(x){ return [x.ci, x.state, x.post || null]; }); }
W._vaultAutoIntakeSet(false);
W.vaultHandAdd('Gull'); W.vaultHandAdd('Gull'); SHAKO = (W.vaultHandAdd('Shako') || {}).name;
W.vaultAssign(GULL, 'uni-weap'); W.vaultAssign(SHAKO, 'uni-armor'); paint();   // the D2JSP tab trades what is filed on a mule
var assign = JSON.parse(W.LSR.getItem('d2r_muleAssign') || '{}');
OUT.premise = { shako: SHAKO, gull: copyCount(GULL), assigned: [GULL, SHAKO].filter(function(n){ return assign[n] != null; }), slots: slots(GULL) };
OUT.first = W._d2jspListOnVault([GULL], %(topic)s); paint();
OUT.after = { slots: slots(GULL), shako: slots(SHAKO), count: copyCount(GULL), card: W._d2jspCardHtml(GULL) };
OUT.again = W._d2jspListOnVault([GULL], %(topic)s);
OUT.againSlots = slots(GULL);
W.vaultFind('gull'); H.flush(400, 3);
OUT.find = (document.getElementById('vault-find-results') || {}).innerHTML || '';
""" % {"topic": json.dumps(TOPIC)}


def _room_code(src):
    """The room's script with comments stripped: what runs, never what the prose says."""
    script = _between(src, 'id="tab-d2jsp"', 'id="tab-vault"').split("<script>", 1)[1].split("</script>", 1)[0]
    return re.sub(r"/\*[\s\S]*?\*/", "", script)


@unittest.skipUnless(NODE, "node is required to run the room's own code - UNMEASURED here, never a pass")
class AConfirmedD2jspPostListsItsCopiesOnTheVault(unittest.TestCase):

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

    def test_a_confirmed_post_lists_every_copy_it_offers_with_its_topic(self):
        o = self.o
        self.assertEqual(o["draftChip"], ["draft", "Draft · not posted"], o["draftChip"])
        g = o["grief"]
        self.assertEqual(g["sent"], 1, "PREMISE: the post never reached the send route: %r" % g)
        self.assertEqual(g["events"], [{"kind": "listed", "name": "Grief", "post": TOPIC}] * 3,
                         "a confirmed post of 3 copies did not list 3 through the door: %r" % g["events"])
        self.assertIn("3 copies marked listed in the vault", g["status"])
        self.assertEqual(g["chip"], ["listed", "Listed on board 268 · not traded yet"], g["chip"])

    def test_a_re_post_tops_up_and_never_lists_twice(self):
        a = self.o["griefAgain"]
        self.assertEqual(a["sent"], 2, "PREMISE: the second post was not sent: %r" % a)
        self.assertEqual(a["events"], 3, "a re-post listed copies already listed: %r" % a)

    def test_a_maybe_a_refusal_and_a_busy_answer_list_nothing(self):
        w = self.o["wisp"]
        self.assertEqual(w["sent"], 5, "PREMISE: the three Wisp answers were not all sent: %r" % w)
        self.assertEqual(w["events"], [], "an answer that is not confirmed listed a copy: %r" % w["events"])
        self.assertEqual(w["chip"], ["maybe", "Maybe listed · check board 268"], w["chip"])
        self.assertEqual(w["chipAfter"][0], "maybe", "a later refusal turned the maybe into something else: %r" % w)
        self.assertFalse(any("marked listed" in s for s in w["status"]), w["status"])

    def test_a_refused_listing_is_said_and_the_chip_does_not_claim_listed(self):
        s = self.o["shako"]
        self.assertEqual(len(s["events"]), 1, "PREMISE: the door was not asked: %r" % s)
        self.assertIn("⚠ the vault did not mark it listed - Shako: nothing changed - the copy records are held (law)", s["status"])
        self.assertEqual(s["chip"], ["posted", "Posted on board 268 · no copy is listed in the vault"], s["chip"])

    def test_the_list_lists_only_what_the_vault_holds_and_is_for_sale(self):
        li = self.o["list"]
        self.assertEqual(li["sent"], 7, "PREMISE: the list was not sent: %r" % li)
        self.assertEqual(sorted((e["name"], e["post"]) for e in li["events"]),
                         [("Shako", TOPIC2), ("Wisp", TOPIC2), ("Wisp", TOPIC2)],
                         "the list listed the wrong copies (a SOLD block, a planner pick, or a copy twice): %r" % li["events"])
        self.assertIn("3 copies marked listed in the vault", li["status"])
        self.assertEqual(li["tyrael"], ["posted", "Posted on board 268 · not in the vault"], li["tyrael"])
        self.assertEqual(li["wisp"], ["listed", "Listed on board 268 · not traded yet"], li["wisp"])

    def test_the_room_lists_through_the_door_only(self):
        code = _room_code(self.src)
        self.assertEqual(code.count("window._vaultTradeEvent({ kind: 'listed'"), 1, "the room lists from more than one place")
        self.assertNotIn("d2r_vaultRecords", code, "the room writes the vault's copy records itself")
        self.assertNotIn("_d2jspTradeState", self.src, "the retired log-based listed state is still published")

    def test_on_the_whole_page_the_vault_holds_the_listing_and_find_shows_it(self):
        v = self.v
        self.assertEqual(v["__boot"]["errors"], [], v["__boot"])
        p = v["premise"]
        self.assertEqual((p["gull"], sorted(p["assigned"]), p["slots"]), (2, sorted(["Gull (dagger)", p["shako"]]), []),
                         "PREMISE: %r" % p)
        self.assertEqual(v["first"], {"listed": 2, "refused": []}, v["first"])
        self.assertEqual(v["after"]["slots"], [[0, "listed", TOPIC], [1, "listed", TOPIC]], v["after"])
        self.assertEqual(v["after"]["shako"], [], "a name the post did not carry was listed: %r" % v["after"])
        self.assertEqual(v["after"]["count"], 2, "listing changed the count")
        self.assertIn('data-d2jsp-state="listed">Listed on board 268 · not traded yet<', v["after"]["card"])
        self.assertEqual(v["again"], {"listed": 0, "refused": []}, v["again"])
        self.assertEqual(v["againSlots"], v["after"]["slots"])
        self.assertIn(">2 listed</span>", v["find"], v["find"][:600])


RED_PROOF = [
    {"why": "REG-2880 - a confirmed one-item post lists nothing on the vault",
     "file": "bible.html",
     "find": "          say(w.say + listedSay(listOnVault([draft.name || post], w.topic)));",
     "replace": "          say(w.say);",
     "matches": 1, "needs": "node"},
    {"why": "REG-2880 - a confirmed list post lists nothing on the vault",
     "file": "bible.html",
     "find": "        say(w.say + listedSay(listOnVault(listNames(draft), w.topic)));",
     "replace": "        say(w.say);",
     "matches": 1, "needs": "node"},
    {"why": "REG-2880 - a maybe-sent answer lists the copy as if it were up",
     "file": "bible.html",
     "find": "        d2jspLamp();\n        say(whySay(w));\n",
     "replace": "        listOnVault([draft.name || post], w.topic);\n        d2jspLamp();\n        say(whySay(w));\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2880 - a re-post lists the same copies again",
     "file": "bible.html",
     "find": "      try { have = (typeof window._vaultTradeOf === 'function') ? window._vaultTradeOf(nm).filter(function(x){ return x.state === 'listed'; }).length : 0; } catch (eH) { have = 0; }",
     "replace": "      have = 0;",
     "matches": 1, "needs": "node"},
    {"why": "REG-2880 - a SOLD block in the list is listed again",
     "file": "bible.html",
     "find": "      if (!nm || soldOf(nm) || held.indexOf(nm) < 0) return;",
     "replace": "      if (!nm || held.indexOf(nm) < 0) return;",
     "matches": 1, "needs": "node"},
    {"why": "REG-2880 - a planner pick the vault does not hold is sent to the door",
     "file": "bible.html",
     "find": "      if (!nm || soldOf(nm) || held.indexOf(nm) < 0) return;",
     "replace": "      if (!nm || soldOf(nm)) return;",
     "matches": 1, "needs": "node"},
    {"why": "REG-2880 - a refused listing is swallowed",
     "file": "bible.html",
     "find": "        if (!r || !r.ok) { out.refused.push(nm + ': ' + ((r && r.why) || 'the vault door did not answer')); break; }",
     "replace": "        if (!r || !r.ok) break;",
     "matches": 1, "needs": "node"},
    {"why": "REG-2880 - the listing does not carry the post's topic",
     "file": "bible.html",
     "find": "window._vaultTradeEvent({ kind: 'listed', name: nm, post: topic || null })",
     "replace": "window._vaultTradeEvent({ kind: 'listed', name: nm, post: null })",
     "matches": 1, "needs": "node"},
    {"why": "REG-2880 - the chip says Listed from the post log, not from the vault's slot",
     "file": "bible.html",
     "find": "      : (slot.length ? 'listed' : (conf ? 'posted' : (maybe ? 'maybe' : 'draft')));",
     "replace": "      : ((slot.length || conf) ? 'listed' : (maybe ? 'maybe' : 'draft'));",
     "matches": 1, "needs": "node"},
    {"why": "REG-2880 - a confirmed post the vault could not list reads as a draft never posted",
     "file": "bible.html",
     "find": "      : t.state === 'posted' ? ('Posted on board ' + t.board + (t.inVault ? ' · no copy is listed in the vault' : ' · not in the vault'))\n",
     "replace": "",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
