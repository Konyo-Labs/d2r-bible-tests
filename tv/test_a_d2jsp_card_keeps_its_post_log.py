# -*- coding: utf-8 -*-
"""REG-2872 (#83, his ask 3, GrokBot 6476487696) - A D2JSP CARD KEEPS ITS POST LOG.

GrokBot: "Post log and history on the card: posted at, board, topic.php link, and each attempt with its result. Today the
card looks exactly the same before and after the attempt, with only Options, Mark sold, Remove from this list and Post."

MEASURED before (the room's own code in node): a send on either path wrote nothing but the list's saved topic. The card
painted the same HTML before and after an attempt, and no store kept an attempt.

Now each send, on either path, writes one row per item it carried into d2r_d2jsp_log, a desk store that forks per profile
like the other six: when it was tried, the board, the result (confirmed / maybe / missed), its words and what the console
saw, the console's send time, and the topic link. A lost answer is a row too. The card shows "Not posted yet", or "No post
confirmed yet", or "Posted <when> on board N · <topic link>", above "Attempts (n)" with every row, newest first. The newest
12 are kept per item. The room runs in node with a fake page, never a browser and never d2jsp. RED_PROOF below.
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
var MULE = JSON.stringify({ 'Grief': 'm1', 'Shako': 'm2' });
var window = { addEventListener: function(){}, LSR: { getItem: function(k){ return k === 'd2r_muleAssign' ? MULE : null; } } };
var ANSWER = null, DROP = false;
function fetch(url, opts){
  if (String(url) === '/api/d2jsp_send') {
    if (DROP) return Promise.reject(new TypeError('Failed to fetch'));
    return Promise.resolve({ status: 200, json: function(){ return Promise.resolve(ANSWER); } });
  }
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
RAW['d2r_d2jsp_fg'] = JSON.stringify({ 'Grief': '55', 'Shako': '30' });
function log(n){ return (JSON.parse(RAW['d2r_d2jsp_log'] || '{}')[n]) || []; }
async function one(answer, drop){
  ANSWER = answer; DROP = !!drop;
  var shown = d2jspDraft('Grief', '', '', 1, 55);
  VIEW.textContent = shown.body; SUBJECT.textContent = shown.subject;
  LISTEN.click.forEach(function(f){ f({ target: button({ 'data-d2jsp-post': 'Grief', 'data-d2jsp-send': '1' }, []), preventDefault: function(){} }); });
  for (var i = 0; i < 6; i++) await flush();
  DROP = false;
}
async function shop(answer){
  ANSWER = answer;
  var d = d2jspShopDraft([{ name: 'Grief', base: '', mods: '', copies: 1, fg: 55, sold: false },
                          { name: 'Shako', base: '', mods: '', copies: 1, fg: 30, sold: false }]);
  VIEW.textContent = d.body; SUBJECT.textContent = d.subject;
  LISTEN.click.forEach(function(f){ f({ target: button({ 'data-d2jsp-shop': '1', 'data-d2jsp-send': '1' }, ['[data-d2jsp-shop]']), preventDefault: function(){} }); });
  for (var i = 0; i < 6; i++) await flush();
}
(async function(){
  var out = {};
  out.cardBefore = window._d2jspCardHtml('Grief');
  await one({ ok: false, reason: 'maybe-sent', board: 268, at: '2026-10-28T18:01:00.000Z', why: 'the click went out' });
  out.afterMaybe = { log: log('Grief'), card: window._d2jspCardHtml('Grief') };
  await one({ ok: true, reason: 'submitted', topic: '""" + TOPIC + r"""' });
  out.afterOk = { log: log('Grief'), card: window._d2jspCardHtml('Grief') };
  await one(null, true);
  out.afterLost = log('Grief');
  await shop({ ok: false, reason: 'not-posted', why: 'd2jsp sent the form back after the click' });
  out.shop = { grief: log('Grief'), shako: log('Shako') };
  for (var k = 0; k < 14; k++) await one({ ok: false, reason: 'busy' });
  out.capped = log('Grief').length;
  out.keys = D2JSP_FORKED_KEYS;
  process.stdout.write(JSON.stringify(out));
})().catch(function(e){ process.stderr.write(String(e && e.stack || e)); process.exit(1); });
"""


@unittest.skipUnless(NODE, "node is required to run the room's own code")
class AD2jspCardKeepsItsPostLog(unittest.TestCase):

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

    def test_an_attempt_is_a_row_with_its_board_result_and_why(self):
        rows = self.o["afterMaybe"]["log"]
        self.assertEqual(len(rows), 1, rows)
        r = rows[0]
        self.assertEqual((r["board"], r["kind"], r["why"], r["sent"]), (268, "maybe", "the click went out", "2026-10-28T18:01:00.000Z"), r)
        self.assertRegex(r["at"], r"^\d{4}-\d\d-\d\d \d\d:\d\d UTC$")
        self.assertIn("may already have this post", r["text"])

    def test_the_card_changes_after_an_attempt_and_shows_the_topic_once_confirmed(self):
        o = self.o
        self.assertIn("Not posted yet.", o["cardBefore"])
        self.assertNotEqual(o["cardBefore"], o["afterMaybe"]["card"], "the card looks the same before and after an attempt")
        self.assertIn("No post confirmed yet.", o["afterMaybe"]["card"])
        self.assertIn("<summary>Attempts (1)</summary>", o["afterMaybe"]["card"])
        self.assertIn("<b>Maybe sent</b>", o["afterMaybe"]["card"])
        self.assertIn("What the console saw: the click went out", o["afterMaybe"]["card"])
        ok = o["afterOk"]
        self.assertEqual(ok["log"][-1]["topic"], TOPIC, ok["log"])
        self.assertIn('on board 268 · <a href="%s" target="_blank" rel="noopener">' % TOPIC.replace("&", "&amp;"), ok["card"], ok["card"])
        self.assertIn("<summary>Attempts (2)</summary>", ok["card"])
        self.assertLess(ok["card"].index("<b>Confirmed</b>"), ok["card"].index("<b>Maybe sent</b>"), "the newest attempt is not first")

    def test_a_lost_answer_and_the_list_path_are_rows_too(self):
        lost = self.o["afterLost"][-1]
        self.assertEqual(lost["kind"], "maybe", lost)
        self.assertIn("did not answer", lost["text"])
        shop = self.o["shop"]
        for n in ("grief", "shako"):
            self.assertEqual((shop[n][-1]["kind"], shop[n][-1].get("list")), ("missed", True), (n, shop[n]))
            self.assertEqual(shop[n][-1]["why"], "d2jsp sent the form back after the click")

    def test_the_log_keeps_the_newest_twelve_and_forks_with_the_desk(self):
        self.assertEqual(self.o["capped"], 12)
        self.assertIn("d2r_d2jsp_log", self.o["keys"])


RED_PROOF = [
    {"why": "REG-2872 - the one-item path writes no attempt",
     "file": "bible.html",
     "find": "        logAdd([draft.name || post], d2jspLogEntry(w, got.j, draft.forum, false));   /* REG-2872 */\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2872 - a lost answer writes no attempt",
     "file": "bible.html",
     "find": "        logAdd([draft.name || post], d2jspLogEntry(lost, null, draft.forum, false));   /* REG-2872 */\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2872 - the list path writes no attempt",
     "file": "bible.html",
     "find": "      logAdd(listNames(draft), d2jspLogEntry(w, got.j, draft.forum, true));   /* REG-2872 */\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2872 - the card does not show its log (it looks the same before and after)",
     "file": "bible.html",
     "find": "      + '<div data-d2jsp-log>' + logHtml(n) + '</div>'   /* REG-2872 the post log on the card */\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2872 - an attempt row drops what the console saw",
     "file": "bible.html",
     "find": "  if (w.why) e.why = String(w.why).slice(0, 240);\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2872 - the log grows without a bound",
     "file": "bible.html",
     "find": "      m[n] = rows.slice(-D2JSP_LOG_MAX);\n",
     "replace": "      m[n] = rows;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2872 - the log does not fork with the desk (a 271 attempt shows on 268)",
     "file": "bible.html",
     "find": "'d2r_d2jsp_gear', 'd2r_d2jsp_mods', 'd2r_d2jsp_log'];",
     "replace": "'d2r_d2jsp_gear', 'd2r_d2jsp_mods'];",
     "matches": 1, "needs": "node"},
    {"why": "REG-2872 - the confirmed topic is not shown on the card",
     "file": "bible.html",
     "find": "      ? '<div class=\"d2jsp-say\" data-d2jsp-posted=\"1\">Posted ' + esc(ok.sent || ok.at) + ' on board ' + esc(ok.board) + ' · ' + logLink(ok.topic) + '</div>'\n",
     "replace": "      ? '<div class=\"d2jsp-say\" data-d2jsp-posted=\"1\">Posted</div>'\n",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
