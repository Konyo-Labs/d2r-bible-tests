# -*- coding: utf-8 -*-
"""#113 (REG-2501) - A PRICE READ ON ANOTHER BOARD IS NEVER THE POST PRICE.

The public price is read on board 243, D2:R Switch Ladder Trading (d2jsp_chrome.py QUOTE_BOARD and
functions/api/d2jsp_quote.js search there; the quote function's own header calls the boards "different
economies"). A post goes to board 268 (main) or 271 (ladder). With no typed price, d2jspPriceToSend fell back to
the quoted number, and all four callers (the list draft, the card, the price painter and the one-item post)
handed it the board-243 median, so a cross-economy number went up as his asking price. The price line named no
board, so nothing on screen said where the figure came from.

Now a reading is the post price only when it was read on the board the post goes to (d2jspQuotedForBoard); any
other reading is shown under its own board's name with a note that the post goes to another board, and the post
waits for his typed price. d2jspPriceToSend keeps its own contract (30, '' is still 30).

Run in node, never a browser: the desk block's pure functions, then the room's whole script with a stubbed quote
reading of board 243 / 268, on main and on ladder, read back from the cards it paints and the clicks it answers.
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

ROOT = os.path.dirname(HERE)
BIBLE = os.path.join(ROOT, "bible.html")
NODE = shutil.which("node")


def _read():
    with open(BIBLE, encoding="utf-8") as fh:
        return fh.read()


def _between(src, start, end):
    i = src.index(start)
    j = src.index(end, i + len(start))
    return src[i + len(start):j]


def _node(prog):
    r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError("node failed: " + (r.stderr or r.stdout)[-2500:])
    return json.loads(r.stdout.strip().splitlines()[-1])


PURE = r"""
var out = {};
var r243 = { reason: 'read', fg: 40, low: 40, high: 40, n: 1, readAt: '2026-10-22T13:00:00.000Z', board: 243 };
var r268 = { reason: 'read', fg: 40, low: 40, high: 40, n: 1, readAt: '2026-10-22T13:00:00.000Z', board: 268 };
var rNone = { reason: 'read', fg: 40, low: 40, high: 40, n: 1, readAt: '2026-10-22T13:00:00.000Z' };
out.q243 = d2jspQuotedForBoard(r243, 268);
out.q268 = d2jspQuotedForBoard(r268, 268);
out.q268on271 = d2jspQuotedForBoard(r268, 271);
out.qNone = d2jspQuotedForBoard(rNone, 268);
out.qNull = d2jspQuotedForBoard(null, 268);
out.qZero = d2jspQuotedForBoard({ reason: 'read', fg: 0, board: 268 }, 268);
out.send243 = d2jspPriceToSend(d2jspQuotedForBoard(r243, 268), '');
out.send243typed = d2jspPriceToSend(d2jspQuotedForBoard(r243, 268), '55');
out.send268 = d2jspPriceToSend(d2jspQuotedForBoard(r268, 268), '');
out.contract = [d2jspPriceToSend(30, ''), d2jspPriceToSend(30, '40'), d2jspPriceToSend(30, 'abc')];
out.line243 = d2jspPriceLine(r243);
out.lineRange = d2jspPriceLine({ reason: 'read', fg: 30, low: 10, high: 50, n: 3, board: 243, readAt: 'x' });
out.lineNone = d2jspPriceLine(rNone);
out.note243 = d2jspPriceNote(r243, 268);
out.note268 = d2jspPriceNote(r268, 268);
out.noteNone = d2jspPriceNote(rNone, 268);
out.noteUnread = d2jspPriceNote({ reason: 'need-login', fg: null }, 268);
process.stdout.write(JSON.stringify(out));
"""

FAKES = r"""
var LISTEN = { click: [], input: [], keydown: [] };
function Node(id){ this.id = id; this.attrs = {}; this.hidden = true; this._html = ''; this.textContent = ''; this.title = ''; }
Node.prototype.setAttribute = function(k, v){ this.attrs[k] = String(v); };
Node.prototype.getAttribute = function(k){ return Object.prototype.hasOwnProperty.call(this.attrs, k) ? this.attrs[k] : null; };
Node.prototype.removeAttribute = function(k){ delete this.attrs[k]; };
Node.prototype.querySelector = function(){ return { focus: function(){} }; };
Node.prototype.querySelectorAll = function(){ return []; };
Node.prototype.appendChild = function(){};
Object.defineProperty(Node.prototype, 'innerHTML', { get: function(){ return this._html; }, set: function(v){ this._html = String(v); } });
var list = new Node('d2jsp-list'), statusEl = new Node('d2jsp-status'), lamp = new Node('d2jsp-lamp');
var host = new Node('d2jsp-draft-host'), boardEl = new Node('d2jsp-board');
var document = {
  documentElement: { classList: { contains: function(){ return false; } } },
  getElementById: function(id){
    return ({ 'd2jsp-list': list, 'd2jsp-status': statusEl, 'd2jsp-lamp': lamp, 'd2jsp-draft-host': host, 'd2jsp-board': boardEl })[id] || null;
  },
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
var window = { addEventListener: function(){}, D2R_PROFILE: PROFILE,
               LSR: { getItem: function(k){ return k === 'd2r_muleAssign' ? JSON.stringify({ 'Grief': 'm1' }) : null; } } };
var READING = null;
var NOW = 1700000000000;
Date.now = function(){ return NOW; };   // each open() is an hour on, so the quote is asked again
function fetch(url){
  var body = String(url).indexOf('d2jsp_quote') >= 0 ? READING : { state: 'unknown' };
  return Promise.resolve({ json: function(){ return Promise.resolve(body); } });
}
function flush(){ return new Promise(function(r){ setTimeout(r, 0); }); }
function button(attrs, selfSel){
  var b = { getAttribute: function(k){ return Object.prototype.hasOwnProperty.call(attrs, k) ? attrs[k] : null; } };
  b.closest = function(sel){ return (sel === '#tab-d2jsp' || selfSel.indexOf(sel) >= 0) ? b : null; };
  return b;
}
"""

SCENARIO = r"""
async function open(reading, typed){
  NOW += 3600000;
  READING = reading;
  if (typed != null) RAW['d2r_d2jsp_fg'] = JSON.stringify({ 'Grief': typed });
  window._d2jspShow();                       // asks the quote; the card is painted before it answers
  for (var i = 0; i < 6; i++) await flush();
  list._html = ''; list.attrs = {};
  window._d2jspShow();                       // the reading is held now, so this paint carries it
  for (var k = 0; k < 4; k++) await flush();
  var card = list._html;
  statusEl.textContent = '';
  LISTEN.click[0]({ target: button({ 'data-d2jsp-post': 'Grief' }, []), preventDefault: function(){} });
  var postSaid = statusEl.textContent;
  statusEl.textContent = '';
  LISTEN.click[0]({ target: button({ 'data-d2jsp-shop': '1' }, ['[data-d2jsp-shop]']), preventDefault: function(){} });
  var shopSaid = statusEl.textContent;
  return {
    disabled: /data-d2jsp-post="Grief" disabled>Post</.test(card),
    waiting: card.indexOf('<div class="d2jsp-say" data-d2jsp-wait>The post waits for a price.</div>') >= 0,
    price: (card.match(/<div class="d2jsp-say" data-d2jsp-price>([^<]*)<\/div>/) || [])[1] || '',
    draft: (card.match(/<pre class="d2jsp-draft" data-d2jsp-draft[^>]*>([^<]*)<\/pre>/) || [])[1] || '',
    postSaid: postSaid, shopSaid: shopSaid
  };
}
(async function(){
  var r243 = { reason: 'read', fg: 40, low: 40, high: 40, n: 1, readAt: '2026-10-22T13:00:00.000Z', board: 243 };
  var r268 = { reason: 'read', fg: 40, low: 40, high: 40, n: 1, readAt: '2026-10-22T13:00:00.000Z', board: 268 };
  var out = {};
  if (PROFILE === 'ladder') {
    out.ladder268 = await open(r268, null);
  } else {
    out.read243 = await open(r243, null);
    out.typed243 = await open(r243, '55');
    RAW['d2r_d2jsp_fg'] = JSON.stringify({});
    out.read268 = await open(r268, null);
  }
  process.stdout.write(JSON.stringify(out));
})().catch(function(e){ process.stderr.write(String(e && e.stack || e)); process.exit(1); });
"""


@unittest.skipUnless(NODE, "node is required to run the room's own code")
class APriceReadOnAnotherBoardIsNotThePostPrice(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.src = _read()
        cls.desk = _between(cls.src, "/* ⟦D2JSP DESK BEGIN⟧ */\n", "\n/* ⟦D2JSP DESK END⟧ */")
        pane = _between(cls.src, 'id="tab-d2jsp"', 'id="tab-vault"')
        cls.script = pane.split("<script>", 1)[1].split("</script>", 1)[0]
        cls.pure = _node(cls.desk + "\n" + PURE)
        cls.main = _node("var PROFILE = 'main';\n" + FAKES + cls.script + "\n" + SCENARIO)
        cls.lad = _node("var PROFILE = 'ladder';\n" + FAKES + cls.script + "\n" + SCENARIO)

    def test_a_reading_counts_only_on_its_own_board(self):
        p = self.pure
        self.assertIsNone(p["q243"], "a board-243 reading became a board-268 post price")
        self.assertEqual(p["q268"], 40)
        self.assertIsNone(p["q268on271"], "a main-board reading became a ladder post price")
        self.assertIsNone(p["qNone"], "a reading that names no board became a post price")
        self.assertIsNone(p["qNull"])
        self.assertIsNone(p["qZero"])
        self.assertIsNone(p["send243"])
        self.assertEqual(p["send243typed"], 55, "his typed price no longer posts")
        self.assertEqual(p["send268"], 40)
        self.assertEqual(p["contract"], [30, 40, None], "d2jspPriceToSend's own contract moved")

    def test_the_price_line_names_its_board(self):
        p = self.pure
        self.assertIn("Board 243 (D2:R Switch Ladder Trading)", p["line243"])
        self.assertIn("40 fg", p["line243"])
        self.assertIn("Board 243", p["lineRange"])
        self.assertIn("10–50 fg", p["lineRange"])
        self.assertTrue(p["lineNone"].startswith("Public price 40 fg"), p["lineNone"])
        self.assertIn("goes to board 268", p["note243"])
        self.assertIn("Type your own", p["note243"])
        self.assertEqual(p["note268"], "")
        self.assertIn("not on record", p["noteNone"])
        self.assertEqual(p["noteUnread"], "")

    def test_a_board_243_reading_leaves_the_post_waiting(self):
        c = self.main["read243"]
        self.assertTrue(c["disabled"], "Post is live on a card whose only price was read on board 243")
        self.assertTrue(c["waiting"], "the card does not say the post waits for a price")
        self.assertIn("Board 243 (D2:R Switch Ladder Trading) price 40 fg", c["price"])
        self.assertIn("This post goes to board 268", c["price"])
        self.assertNotIn("40 fg", c["draft"], "the card's draft carries the board-243 price")
        self.assertEqual(c["postSaid"], "Forum gold is unknown, so this item is not posted.")
        self.assertEqual(c["shopSaid"], "Forum gold is unknown, so this list is not posted.")

    def test_his_typed_price_or_a_same_board_reading_still_posts(self):
        t = self.main["typed243"]
        self.assertFalse(t["disabled"], "his typed price no longer enables Post")
        self.assertIn("55 fg", t["draft"])
        self.assertNotIn("40 fg", t["draft"])
        s = self.main["read268"]
        self.assertFalse(s["disabled"], "a reading taken on the post board no longer prices the post")
        self.assertIn("40 fg", s["draft"])
        self.assertNotIn("goes to board", s["price"])

    def test_a_main_board_reading_is_not_a_ladder_price(self):
        c = self.lad["ladder268"]
        self.assertTrue(c["disabled"], "a board-268 reading priced a board-271 post")
        self.assertIn("This post goes to board 271", c["price"])

    def test_no_caller_hands_the_raw_reading_to_the_post_price(self):
        s = self.src
        self.assertEqual(s.count("d2jspPriceToSend((quoted"), 0)
        self.assertEqual(s.count("d2jspPriceToSend(q.fg"), 0)
        calls = [m.start() for m in re.finditer(r"d2jspPriceToSend\(", s)]
        # each offending call is reported up to the end of its own line, a real boundary
        # (not a fixed character count that measures a guess about the line length)
        outside = [s[i:s.find("\n", i) if s.find("\n", i) >= 0 else len(s)] for i in calls
                   if not s.startswith("d2jspPriceToSend(quoted, typed)", i)
                   and not s.startswith("d2jspPriceToSend(d2jspQuotedForBoard(", i)
                   and not s.startswith("d2jspPriceToSend(30", i)
                   and not s.startswith("d2jspPriceToSend(fg, typed)", i)]
        self.assertEqual(outside, [], "a caller prices a post from something other than d2jspQuotedForBoard")
        script = s[s.index("/* ⟦D2JSP DESK END⟧ */"):s.index('<div class="tab-content" id="tab-vault">')]
        self.assertEqual(script.count("sendOf("), 5, "the four callers and the helper are no longer one route")


RED_PROOF = [
    {"why": "#113 - the board check is gone, so a board-243 reading becomes the board-268 post price",
     "file": "bible.html",
     "find": "  if (!(on > 0) || on !== Number(board)) return null;\n",
     "replace": "  if (!(on >= 0)) return null;\n",
     "matches": 1},
    {"why": "#113 - the cards and the post read the raw quoted number again",
     "file": "bible.html",
     "find": "    return d2jspPriceToSend(d2jspQuotedForBoard(quoted[name], d2jspBoard()), typedOf(name));\n",
     "replace": "    return d2jspPriceToSend((quoted[name] || {}).fg, typedOf(name));\n",
     "matches": 1},
    {"why": "#113 - the price line stops naming the board its reading came from",
     "file": "bible.html",
     "find": "    var head = on ? ('Board ' + on + (on === 243 ? ' (D2:R Switch Ladder Trading)' : (on === 268 ? ' (D2:R RotW Softcore Trading)' : ''))) : 'Public';\n",
     "replace": "    var head = 'Public';\n",
     "matches": 1},
    {"why": "#113 - the card no longer says the post goes to another board",
     "file": "bible.html",
     "find": "    if (quoted[n]) { var note = d2jspPriceNote(quoted[n], d2jspBoard()), dbf = d2jspDbFirstLine(quoted[n]); return d2jspPriceLine(quoted[n]) + (note ? (' ' + note) : '') + (dbf ? (' ' + dbf) : ''); }",
     "replace": "    if (quoted[n]) { var dbf = d2jspDbFirstLine(quoted[n]); return d2jspPriceLine(quoted[n]) + (dbf ? (' ' + dbf) : ''); }",
     "matches": 1},
    {"why": "#113 - the one-item Post prices itself from the board-243 reading again",
     "file": "bible.html",
     "find": "      var fg = sendOf(post);\n",
     "replace": "      var fg = d2jspPriceToSend((quoted[post] || {}).fg, typedOf(post));\n",
     "matches": 1},
    {"why": "#113 - the list draft prices each item from the board-243 reading again",
     "file": "bible.html",
     "find": "        fg: sendOf(n), sold: tv.sold\n",
     "replace": "        fg: d2jspPriceToSend((quoted[n] || {}).fg, typedOf(n)), sold: tv.sold\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
