# -*- coding: utf-8 -*-
"""REG-2874 (#83, his ask 5, and GrokBot 6476487696) - A D2JSP POST SAYS WTS, AND BACK ON A DRAFT IS A CANCEL.

His ask, through GrokBot: "Wording: the subject reads 'Selling ...'. Earlier drafts used 'WTS ...', which is the d2jsp
norm." And GrokBot saw: "Closing the dialog with Back changed the status to 'The draft was closed. Nothing was posted.',
which reads like a post result."

MEASURED before (the room's own code in node): d2jspDraft gave the subject "Selling Grief Phase Blade" and the list
"Selling 2 items"; Back and Escape on an open draft both set the status "The draft was closed. Nothing was posted.", two
copies of one sentence.

Now one item's subject is "WTS <name> <base>" and the list's is "WTS <n> items"; Back and Escape both say "Cancelled. You
closed the draft." through one function. Closing mid-send still says the board has not confirmed a topic. The console
already took WTS as a priced subject (_priced), so nothing changes there. The room runs in node with a fake page, never a
browser. RED_PROOF below.
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


def _between(src, start, end):
    i = src.index(start)
    j = src.index(end, i + len(start))
    return src[i + len(start):j]


def _node(prog):
    r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError("node failed: " + (r.stderr or r.stdout)[-2500:])
    return json.loads(r.stdout.strip().splitlines()[-1])


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
  getElementById: function(id){
    return ({ 'd2jsp-list': list, 'd2jsp-status': statusEl, 'd2jsp-lamp': lamp, 'd2jsp-draft-host': host, 'd2jsp-board': board })[id] || null;
  },
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
var MULE = JSON.stringify({ 'Grief': 'm1' });
var window = { addEventListener: function(){}, LSR: { getItem: function(k){ return k === 'd2r_muleAssign' ? MULE : null; } } };
function fetch(url){ return Promise.resolve({ status: 200, json: function(){ return Promise.resolve({ state: 'unknown', fg: null, reason: 'no prices', n: 0 }); } }); }
function flush(){ return new Promise(function(r){ setTimeout(r, 0); }); }
function button(attrs, selfSel){
  var b = { getAttribute: function(k){ return Object.prototype.hasOwnProperty.call(attrs, k) ? attrs[k] : null; } };
  b.closest = function(sel){ return (sel === '#tab-d2jsp' || selfSel.indexOf(sel) >= 0) ? b : null; };
  return b;
}
"""

SCENARIO = r"""
RAW['d2r_d2jsp_fg'] = JSON.stringify({ 'Grief': '55' });
(async function(){
  var out = {};
  out.one = d2jspDraft('Grief', 'Phase Blade', '+340-400% Enhanced Damage', 1, 55);
  out.shop = d2jspShopDraft([{ name: 'Grief', base: 'Phase Blade', mods: '', copies: 1, fg: 55, sold: false },
                             { name: 'Shako', base: 'Harlequin Crest', mods: '', copies: 1, fg: 30, sold: false }]);
  out.shopOne = d2jspShopDraft([{ name: 'Grief', base: 'Phase Blade', mods: '', copies: 1, fg: 55, sold: false }]);
  function click(attrs, sel){ LISTEN.click.forEach(function(f){ f({ target: button(attrs, sel), preventDefault: function(){} }); }); }
  click({ 'data-d2jsp-post': 'Grief' }, []);
  out.opened = { hidden: host.hidden, status: statusEl.textContent };
  click({}, ['[data-d2jsp-draft-close]']);
  out.back = { hidden: host.hidden, status: statusEl.textContent };
  click({ 'data-d2jsp-post': 'Grief' }, []);
  LISTEN.keydown.forEach(function(f){ f({ key: 'Escape', preventDefault: function(){}, stopImmediatePropagation: function(){} }); });
  out.esc = { hidden: host.hidden, status: statusEl.textContent };
  process.stdout.write(JSON.stringify(out));
})().catch(function(e){ process.stderr.write(String(e && e.stack || e)); process.exit(1); });
"""


@unittest.skipUnless(NODE, "node is required to run the room's own code")
class AD2jspPostSaysWtsAndBackIsACancel(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(BIBLE, encoding="utf-8") as fh:
            src = fh.read()
        pane = _between(src, 'id="tab-d2jsp"', 'id="tab-vault"')
        cls.o = _node(FAKES + pane.split("<script>", 1)[1].split("</script>", 1)[0] + "\n" + SCENARIO)

    def test_one_item_and_the_list_say_wts(self):
        o = self.o
        self.assertEqual(o["one"]["subject"], "WTS Grief Phase Blade", o["one"])
        self.assertEqual(o["one"]["body"].split("\n")[0], "WTS Grief Phase Blade", "the post's first line is not its subject")
        self.assertEqual(o["shop"]["subject"], "WTS 2 items", o["shop"])
        self.assertEqual(o["shopOne"]["subject"], "WTS Grief Phase Blade", o["shopOne"])

    def test_back_and_escape_say_cancelled(self):
        o = self.o
        self.assertFalse(o["opened"]["hidden"], "PREMISE: the Post button did not open the draft: %r" % o["opened"])
        for k in ("back", "esc"):
            self.assertTrue(o[k]["hidden"], "%s did not close the draft" % k)
            self.assertEqual(o[k]["status"], "Cancelled. You closed the draft.", "%s: %r" % (k, o[k]))
            self.assertNotIn("posted", o[k]["status"].lower(), "a cancel reads like a post result: %r" % o[k])


RED_PROOF = [
    {"why": "REG-2874 - one item's subject says Selling again",
     "file": "bible.html",
     "find": "  var subject = 'WTS ' + nm + (b ? (' ' + b) : '');",
     "replace": "  var subject = 'Selling ' + nm + (b ? (' ' + b) : '');",
     "matches": 1, "needs": "node"},
    {"why": "REG-2874 - the list's subject says Selling again",
     "file": "bible.html",
     "find": "  var subject = 'WTS ' + n + (n === 1 ? ' item' : ' items');",
     "replace": "  var subject = 'Selling ' + n + (n === 1 ? ' item' : ' items');",
     "matches": 1, "needs": "node"},
    {"why": "REG-2874 - a cancelled draft reads like a post result again",
     "file": "bible.html",
     "find": ": 'Cancelled. You closed the draft.';",
     "replace": ": 'The draft was closed. Nothing was posted.';",
     "matches": 1, "needs": "node"},
    {"why": "REG-2874 - Escape keeps its own copy of the old sentence",
     "file": "bible.html",
     "find": "    var midSend = posting;\n    closeDraft();\n    say(closedSay(midSend));\n  }, true);",
     "replace": "    var midSend = posting;\n    closeDraft();\n    say(midSend ? 'x' : 'The draft was closed. Nothing was posted.');\n  }, true);",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
