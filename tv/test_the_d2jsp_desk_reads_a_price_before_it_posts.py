# -*- coding: utf-8 -*-
"""The D2JSP room lists the vault filings and posts one priced item through
the Chrome login on this machine. Forum gold stays unknown until a public
reading returns a price.

The console reads the d2jsp cookie when he clicks Post. It is not stored
and not returned. A missing login, an unreadable cookie, or a board that
does not redirect to the topic does not become a sent post. A challenge
page or a page with no fg number does not become a price.

REG-2494 - THIS LAW DID NOT RUN FROM 2026-10-13 TO 2026-10-22. a66f08dfe dropped its
`if __name__ == "__main__"` block, so the gate's `python3 <file>` ran 0 tests and printed a
green tick; REG-2188, REG-2190 and REG-2196 named it as their guard the whole time. Run by
hand it had been red since e29faa5c8, on a 7200-character cap over a window between two
`def` anchors. The block is back, the backend cases read the REG-2490 send contract, and the
post flow is read from its own functions (_code_of), so no size cap is needed. RED_PROOF below.
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
QUOTE = os.path.join(ROOT, "functions", "api", "d2jsp_quote.js")
UI = os.path.join(HERE, "control_ui.html")
BEACON = os.path.join(ROOT, "functions", "api", "console.js")
NODE = shutil.which("node")
# Story quest codes in tv/item_tables.json. Pandemonium keys, organs, essences
# and the token are the trade, so they are not in this tuple.
QUEST_CODES = (
    "ass", "bbb", "bkd", "bks", "box", "d33", "g33", "g34",
    "hdm", "hfh", "hst", "ibk", "ice", "j34", "key", "leg",
    "luv", "msf", "mss", "qbr", "qey", "qhr", "qf1", "qf2",
    "std", "tbk", "tr1", "tr2", "vip", "xyz",
)
QUEST_EXTRA = ("keys", "wirts leg", "tome")


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _between(src, start, end):
    i = src.index(start)
    j = src.index(end, i + len(start))
    return src[i + len(start):j]


def _code_of(*objs):
    """The objects' own source, comments and docstrings dropped. -> str

    REG-2494 - inspect.getsource is the function and only it, so an assertion over it cannot
    drift onto a neighbour the way a window between two `def` anchors did, and it needs no size
    cap to stay honest. With the prose dropped, a sentence about the code can neither satisfy
    nor trip an assertion meant for the code. [[source-reading-guard]]"""
    import ast
    import inspect
    import io as _io
    import textwrap
    import tokenize
    parts = []
    for obj in objs:
        src = textwrap.dedent(inspect.getsource(obj))
        doc = set()
        for node in ast.walk(ast.parse(src)):
            body = getattr(node, "body", None)
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) or not body:
                continue
            first = body[0]
            if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str)):
                doc.update(range(first.lineno, first.end_lineno + 1))
        cut = {}
        for tok in tokenize.generate_tokens(_io.StringIO(src).readline):
            if tok.type == tokenize.COMMENT:
                cut[tok.start[0]] = tok.start[1]
        for n, line in enumerate(src.splitlines(), 1):
            if n not in doc:
                parts.append(line[:cut[n]] if n in cut else line)
    return "\n".join(parts)


def _send_fresh(desk,*args, **kwargs):
    """One d2jsp_send with nothing remembered from the case before it.

    REG-2490 - the same draft is not sent again for 30 minutes after it was posted or may have
    been. Each case here asks what ONE outcome is called, so the record starts empty; the record
    itself is test_a_d2jsp_post_is_sent_once_and_never_called_unsent's law."""
    desk._SENT.clear()
    return desk.d2jsp_send(*args, **kwargs)


def _node(prelude, body):
    prog = prelude + "\n;(function(){\n" + body + "\n})();\n"
    r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise AssertionError("node failed: " + (r.stderr or r.stdout)[-2000:])
    return r.stdout


class TheD2jspDeskReadsAPriceBeforeItPosts(unittest.TestCase):

    def setUp(self):
        import d2jsp_chrome as desk
        desk._SENT.clear()
        self.addCleanup(desk._SENT.clear)

    @classmethod
    def setUpClass(cls):
        cls.bible = _read(BIBLE)
        cls.quote = _read(QUOTE)
        cls.ui = _read(UI)
        cls.desk = _between(cls.bible, "/* ⟦D2JSP DESK BEGIN⟧ */\n", "\n/* ⟦D2JSP DESK END⟧ */")
        cls.parser = _between(cls.quote, "/* ⟦D2JSP QUOTE BEGIN⟧ */\n", "\n/* ⟦D2JSP QUOTE END⟧ */")

    def test_the_room_is_a_workshop_tab_and_a_console_door(self):
        ws = _between(self.bible, '<div class="tabs-workshop"', "</div>")
        order = __import__("re").findall(r'data-tab="([a-z0-9]+)"', ws)
        self.assertEqual(order.index("vault") + 1, order.index("d2jsp"), order)
        self.assertEqual(self.bible.count('id="tab-d2jsp"'), 1)
        self.assertIn("never asks for the password", self.bible)
        self.assertIn("Forum gold stays unknown until a public reading", self.bible)
        self.assertIn('data-tab="d2jsp"', _between(
            self.bible, 'body.app-ctx .tabs .tab[data-tab="session"]', "display:inline-flex"))
        pane = _between(self.bible, 'id="tab-d2jsp"', 'id="tab-vault"')
        self.assertNotIn('type="password"', pane)
        nav_at = self.ui.index('id="head-tabs"')
        nav = self.ui[nav_at:self.ui.index("</nav>", nav_at)]
        self.assertEqual(nav.count('data-tab="d2jsp"'), 1)
        self.assertIn('class="ht-lbl">D2JSP</span>', nav)
        self.assertLess(nav.index('data-tab="vault"'), nav.index('data-tab="d2jsp"'))
        self.assertLess(nav.index('data-tab="d2jsp"'), nav.index('data-tab="tvd"'))
        self.assertNotIn("d2jsp", _read(BEACON))

    def test_a_public_reading_with_no_price_stays_unknown(self):
        if NODE is None:
            self.skipTest("node is not on this machine")
        body = r"""
var page = 'Grief Phase Blade\nBump\n\nShako\n20 fg\n';
var prices = d2jspPrices(page, 'Grief');
var none = d2jspRead('Just a moment...', 'Grief', '2026-10-12T20:00:00.000Z');
var empty = d2jspRead(page, 'Grief', '2026-10-12T20:00:00.000Z');
var hit = d2jspRead('Oct 12, 2026\nGrief Phase Blade 10 fg\n\nGrief 50 fg\n\nGrief 30 fg\n\nShako 200 fg', 'Grief', '2026-10-12T20:01:00.000Z');
var one = d2jspRead('Oct 12, 2026\nGrief 40 fg', 'Grief', '2026-10-12T20:02:00.000Z');
var gheeds = d2jspRead([
  "Oct 12, 2026",
  "Gheeds Fortune gc 106/35/13 - 20fg",
  "Gheeds Fortune gc 108/31/12 - 15fg",
  "Pcomb plain - 10fg x 1",
  "35MF gheeds",
  "Gheed's Fortune 10 fg",
  "Summon Skill Necro + 26 life - 25fg"
].join("\n"), "Gheed's Fortune", '2026-10-12T20:03:00.000Z');
var wall = d2jspRead('You do not have permission to use this feature.', "Gheed's Fortune", '2026-10-12T20:04:00.000Z');
process.stdout.write(JSON.stringify({prices: prices, none: none, empty: empty, hit: hit, one: one, gheeds: gheeds, wall: wall}));
"""
        out = json.loads(_node("var BOARD = 268;\n" + self.parser, body))
        self.assertEqual(out["prices"], [])
        self.assertIsNone(out["none"]["fg"])
        self.assertEqual(out["none"]["reason"], "unread")
        self.assertEqual(out["none"]["readAt"], "2026-10-12T20:00:00.000Z")
        self.assertIsNone(out["empty"]["fg"])
        self.assertEqual(out["empty"]["reason"], "no prices")
        self.assertEqual(out["hit"]["fg"], 30)
        self.assertEqual(out["hit"]["n"], 3)
        self.assertEqual(out["hit"]["low"], 10)
        self.assertEqual(out["hit"]["high"], 50)
        self.assertEqual(out["hit"]["reason"], "read")
        self.assertEqual(out["one"]["fg"], 40)
        self.assertEqual(out["one"]["n"], 1)
        self.assertEqual(out["one"]["low"], 40)
        self.assertEqual(out["one"]["high"], 40)
        self.assertIsNone(out["empty"]["low"])
        self.assertIsNone(out["empty"]["high"])
        self.assertIsNone(out["none"]["low"])
        self.assertIsNone(out["none"]["high"])
        self.assertEqual(out["hit"]["board"], 268)
        self.assertEqual(out["gheeds"]["fg"], 15)
        self.assertEqual(out["gheeds"]["n"], 3)
        self.assertEqual(out["gheeds"]["low"], 10)
        self.assertEqual(out["gheeds"]["high"], 20)
        self.assertEqual(out["gheeds"]["reason"], "read")
        self.assertIsNone(out["wall"]["fg"])
        self.assertEqual(out["wall"]["reason"], "need-login")
        self.assertEqual(out["wall"]["n"], 0)

    def test_a_post_waits_for_a_price_and_the_open_login(self):
        if NODE is None:
            self.skipTest("node is not on this machine")
        body = r"""
var blocked = d2jspDraft('Grief', 'Phase Blade', '+damage', 2, null);
var draft = d2jspDraft('Grief', 'Phase Blade', '+damage', 2, d2jspPriceToSend(30, ''));
var typed = d2jspPriceToSend(30, '40');
var garbage = d2jspPriceToSend(30, 'abc');
var url = d2jspPostUrl(draft);
var clicks = 0;
function el(name){ return { name: name, value: '', click: function(){ clicks++; } }; }
var loggedOut = {
  querySelector: function(sel){
    if (sel.indexOf('subject') >= 0) return el('subject');
    if (sel.indexOf('message') >= 0) return el('message');
    if (sel.indexOf('logout') >= 0) return null;
    if (sel.indexOf('post') >= 0) return el('post');
    return null;
  }
};
var subject = el('subject');
var message = el('message');
var post = el('post');
var loggedIn = {
  querySelector: function(sel){
    if (sel.indexOf('subject') >= 0) return subject;
    if (sel.indexOf('message') >= 0) return message;
    if (sel.indexOf('logout') >= 0) return { href: 'mode=logout' };
    if (sel.indexOf('post') >= 0) return post;
    return null;
  }
};
var hash = url.slice(url.indexOf('#'));
var search = url.slice(url.indexOf('?'), url.indexOf('#'));
var need = d2jspBridgeAct(loggedOut, { hash: hash, search: search }, null);
var sent = d2jspBridgeAct(loggedIn, { hash: hash, search: search }, null);
var wrong = d2jspBridgeAct(loggedIn, { hash: hash, search: '?mode=post&f=271' }, null);
var src = d2jspBridgeSource();
process.stdout.write(JSON.stringify({
  blocked: blocked, draft: draft, typed: typed, garbage: garbage,
  url: url, need: need, sent: sent, wrong: wrong, clicks: clicks,
  subject: subject.value, body: message.value, srcHasPassword: src.indexOf('password') >= 0,
  srcHasLogout: src.indexOf('mode=logout') >= 0
}));
"""
        out = json.loads(_node(self.desk, body))
        self.assertFalse(out["blocked"]["ok"])
        self.assertEqual(out["blocked"]["reason"], "no price")
        self.assertTrue(out["draft"]["ok"])
        self.assertIn("30 fg", out["draft"]["body"])
        self.assertNotIn("password", out["draft"]["body"])
        self.assertEqual(out["draft"]["forum"], 268)
        self.assertEqual(out["typed"], 40)
        self.assertIsNone(out["garbage"])
        self.assertIn("post.php?mode=post&f=268#d2r=", out["url"])
        self.assertEqual(out["need"], "need-login")
        self.assertEqual(out["sent"], "submitted")
        self.assertEqual(out["wrong"], "wrong-board")
        self.assertEqual(out["clicks"], 1)
        self.assertIn("Grief", out["subject"])
        self.assertIn("30 fg", out["body"])
        self.assertFalse(out["srcHasPassword"])
        self.assertTrue(out["srcHasLogout"])

    def test_a_post_is_one_line_per_mod_from_the_builder_list(self):
        if NODE is None:
            self.skipTest("node is not on this machine")
        pane = _between(self.bible, 'id="tab-d2jsp"', 'id="tab-vault"')
        self.assertIn('id="d2jsp-add"', pane)
        self.assertIn(">Add an item</button>", pane)
        self.assertIn('id="d2jsp-shop"', pane)
        self.assertIn(">Post the list</button>", pane)
        script = pane.split("<script>", 1)[1].split("</script>", 1)[0]
        lines_at = script.index("function gearLines(")
        shown_at = script.index("function shownOf(", lines_at)
        lines_fn = script[lines_at:shown_at]
        self.assertLess(shown_at - lines_at, 2200)
        self.assertIn("_cbLineHtml", lines_fn)
        self.assertIn("_cbAfText", lines_fn)
        self.assertIn("Ethereal", lines_fn)
        file_at = script.index("function fileGear(")
        open_at = script.index("window._d2jspPlannerOpen = function", file_at)
        filed = script[file_at:open_at]
        self.assertLess(open_at - file_at, 1800)
        self.assertIn("d2r_d2jsp_gear", script[script.index("function gearMap("):lines_at])
        self.assertIn("d2jspIsQuest", filed)
        self.assertNotIn("vaultPlannerFile", filed)
        click_at = script.index("document.addEventListener('click'", open_at)
        opener = script[open_at:click_at]
        self.assertLess(click_at - open_at, 2800)
        self.assertIn("_cbHostOpen", opener)
        self.assertIn("desk: 'd2jsp'", opener)
        self.assertNotIn("vaultPlannerFile", opener)
        self.assertNotIn("vaultHandAdd", opener)
        self.assertNotIn("d2r_charBuilds", opener)
        card_at = script.index("  function cardHtml(")
        # REG-2883 - the window is cardHtml itself (to the next room function), never a size: the per-copy mark and the
        # doubt's For sale grew it to 2,648 chars, measured, and a 2,400 cap went red on reach
        cards_at = script.index("\n  function ", card_at + 1)
        card = script[card_at:cards_at]
        self.assertIn("data-d2jsp-options", card)
        self.assertIn("Opens a draft. Nothing is posted until Post this draft.", card)
        self.assertIn("This filing has no mods recorded.", card)
        self.assertIn("data-d2jsp-draft", card)
        self.assertIn("data-d2jsp-sold", card)
        self.assertIn('data-d2jsp-remove="', card)
        self.assertIn("Remove from this list", card)
        self.assertNotIn("stays on this list, because the vault still files it.", card)
        self.assertNotIn("<textarea", card)
        host = self.bible.index("var foot = (st.host.planner)")
        placed = self.bible.index("window._cbHostPlaced", host)
        self.assertLess(placed - host, 600)
        self.assertIn("st.host.desk === 'd2jsp'", self.bible[host:placed])
        self.assertIn("window._d2jspPlateHtml", self.bible[host:placed])
        note = self.bible.index("The same item list and the same mod list as the character builder.")
        pick = self.bible.rindex("function _cbPickHtml", 0, note)
        filt = self.bible.index("function _cbFiltOpts", note)
        self.assertLess(note - pick, 8000)
        self.assertLess(filt - note, 1600)
        self.assertIn("window._d2jspPlannerOn = true", opener)
        self.assertEqual(self.bible.count("window._d2jspPlannerOn"), 5)
        self.assertEqual(self.bible.count("!window._d2jspPlannerOn"), 2)
        modal_at = self.bible.index("function _cbModal(){")
        self.assertEqual(self.bible.count("function _cbModal(){"), 1)
        modal_end = self.bible.index("window._cbModal = _cbModal;", modal_at)
        self.assertLess(modal_end - modal_at, 1400)
        modal = self.bible[modal_at:modal_end]
        self.assertEqual(modal.count("st.host.desk === 'd2jsp'"), 2)
        self.assertIn("getElementById('d2jsp-planner-host')", modal)
        self.assertIn("st.host && (st.host.planner || st.host.desk === 'd2jsp')", modal)
        rel = modal.index("m.style.position = 'relative'")
        back = modal.index("return;", rel)
        place = modal.index("_cbPlace(m)")
        self.assertLess(rel, back)
        self.assertLess(back, place)
        self.assertNotIn("vaultPlannerFile", modal)
        placed_at = self.bible.index("window._cbHostPlaced = function(){")
        placed_end = self.bible.index("window._cbHostEsc = function(){", placed_at)
        self.assertLess(placed_end - placed_at, 500)
        placed_fn = self.bible[placed_at:placed_end]
        self.assertLess(placed_fn.index("st.host.desk === 'd2jsp'"), placed_fn.index("_cbPlace(m)"))
        open_b = self.bible.index("window.openCharBuilder = function(buildId){")
        open_end = self.bible.index("st.open = true", open_b)
        self.assertLess(open_end - open_b, 2000)
        opened = self.bible[open_b:open_end]
        self.assertLess(opened.index("window._d2jspPlannerClose"), opened.index("window._mpPick"))
        body = r"""
var lines = window._d2jspGearLines({
  id: 'grief', eth: true, rolls: {},
  affixes: [{ id: 'vita', rolls: {} }]
});
var draft = d2jspDraft('Grief', 'Phase Blade', lines.join('\n'), 1, 30);
var blocked = d2jspDraft('Grief', 'Phase Blade', lines.join('\n'), 1, 0);
var thunder = window._d2jspGearLines({ id: 'thunder', eth: false, rolls: {}, affixes: [] });
var sale = d2jspDraft("Guardian's Thunder", 'Colossal Jewel',
  thunder.join('\n') + '\nan effect the game&#39;s tables name Gethit-skill but do not describe\n+10% to Lightning Skill Damage',
  1, 1100);
var quest = (typeof d2jspIsQuest === 'function') && d2jspIsQuest('Horadric Cube');
var shopOne = d2jspShopDraft([{name:'Grief', base:'Phase Blade', mods: lines.join('\n'), copies:1, fg:30, sold:false}]);
var shopTwo = d2jspShopDraft([
  {name:'Grief', base:'Phase Blade', mods:'+340-400% Enhanced Damage\nEthereal', copies:1, fg:30, sold:false},
  {name:"Guardian's Thunder", base:'Colossal Jewel', mods: thunder.join('\n') + '\nan effect the game&#39;s tables name Gethit-skill but do not describe', copies:1, fg:1100, sold:false}
]);
var shopSold = d2jspShopDraft([
  {name:'Grief', base:'Phase Blade', mods:'+340-400% Enhanced Damage', copies:1, fg:30, sold:false},
  {name:"Guardian's Thunder", base:'Colossal Jewel', mods:'Adds 1-75 lightning damage', copies:2, fg:1100, sold:true}
]);
var shopSkip = d2jspShopDraft([
  {name:'Grief', base:'Phase Blade', mods:'+340-400% Enhanced Damage', copies:1, fg:30, sold:false},
  {name:'Shako', base:'', mods:'no price here', copies:1, fg:'', sold:false}
]);
var shopBlank = d2jspShopDraft([{name:'Grief', base:'Phase Blade', mods:'x', copies:1, fg:null, sold:false}]);
var shopGone = d2jspShopDraft([{name:'Grief', base:'Phase Blade', mods:'SHOULD NOT APPEAR', copies:1, fg:30, sold:true}]);
process.stdout.write(JSON.stringify({lines: lines, draft: draft, blocked: blocked, thunder: thunder, sale: sale, quest: quest, shopOne: shopOne, shopTwo: shopTwo, shopSold: shopSold, shopSkip: shopSkip, shopBlank: shopBlank, shopGone: shopGone}));
"""
        stubs = r"""
var document = {
  documentElement: { classList: { contains: function(){ return false; } } },
  getElementById: function(){ return null; },
  addEventListener: function(){},
  createElement: function(){ return { style: {}, hidden: true, querySelector: function(){ return null; }, setAttribute: function(){} }; },
  body: { appendChild: function(){} }
};
var localStorage = { _m: {}, getItem: function(k){ return this._m[k] || null; }, setItem: function(k, v){ this._m[k] = String(v); } };
var location = { hostname: '127.0.0.1' };
var window = { addEventListener: function(){}, LSR: null };
window._cbItem = function(id){
  if (id === 'grief') return ['grief', 'Grief', 'u', 'pblade', 0, 0, [[0, [[340, 400, 'ed']], 0, 'ed%']]];
  if (id === 'thunder') return ['thunder', "Guardian's Thunder", 'u', 'cjw', 75, 0, [
    [13, [[1, 75, 'ltng']], 0, 'dmg-ltng'],
    [0, [], 0, 2, 'Gethit-skill']
  ]];
  return null;
};
window._cbLineHtml = function(line){
  if (line && line[4] === 'Gethit-skill') return 'an effect the game&#39;s tables name Gethit-skill but do not describe';
  if (line && line[3] === 'dmg-ltng') return 'Adds 1-75 lightning damage';
  return '+340-400% Enhanced Damage';
};
window._cbAf = function(id){ return id === 'vita' ? ['vita'] : null; };
window._cbAfText = function(){ return '+36-40 to Life'; };
window._cbShown = function(){ return { name: 'Grief', base: 'Phase Blade' }; };
"""
        out = json.loads(_node(stubs + script, body))
        self.assertEqual(out["lines"], ["+340-400% Enhanced Damage", "+36-40 to Life", "Ethereal"])
        self.assertEqual(out["draft"]["subject"], "WTS Grief Phase Blade")
        self.assertEqual(
            out["draft"]["body"].split("\n"),
            ["WTS Grief Phase Blade", "+340-400% Enhanced Damage", "+36-40 to Life", "Ethereal", "30 fg"],
        )
        self.assertEqual(out["thunder"], ["Adds 1-75 lightning damage"])
        self.assertEqual(out["sale"]["subject"], "WTS Guardian's Thunder Colossal Jewel")
        self.assertEqual(
            out["sale"]["body"].split("\n"),
            [
                "WTS Guardian's Thunder Colossal Jewel",
                "Adds 1-75 lightning damage",
                "+10% to Lightning Skill Damage",
                "1100 fg",
            ],
        )
        self.assertNotIn("but do not describe", out["sale"]["body"])
        self.assertNotIn("Gethit-skill", out["sale"]["body"])
        self.assertNotIn("&#39;", out["sale"]["body"])
        self.assertEqual(out["draft"]["forum"], 268)
        self.assertFalse(out["blocked"]["ok"])
        self.assertEqual(out["blocked"]["reason"], "no price")
        self.assertTrue(out["quest"])
        self.assertEqual(out["shopOne"]["subject"], out["draft"]["subject"])
        self.assertEqual(out["shopOne"]["body"], out["draft"]["body"])
        self.assertEqual(out["shopTwo"]["subject"], "WTS 2 items")
        self.assertEqual(
            out["shopTwo"]["body"].split("\n\n"),
            [
                "WTS Grief Phase Blade\n+340-400% Enhanced Damage\nEthereal\n30 fg",
                "WTS Guardian's Thunder Colossal Jewel\nAdds 1-75 lightning damage\n1100 fg",
            ],
        )
        self.assertNotIn("but do not describe", out["shopTwo"]["body"])
        self.assertNotIn("&#39;", out["shopTwo"]["body"])
        self.assertEqual(out["shopSold"]["subject"], "WTS 1 item")
        self.assertEqual(
            out["shopSold"]["body"].split("\n\n"),
            [
                "WTS Grief Phase Blade\n+340-400% Enhanced Damage\n30 fg",
                "SOLD Guardian's Thunder Colossal Jewel\ncopies: 2\n1100 fg",
            ],
        )
        self.assertNotIn("Adds 1-75 lightning damage", out["shopSold"]["body"])
        self.assertEqual(out["shopSkip"]["subject"], "WTS Grief Phase Blade")
        self.assertNotIn("Shako", out["shopSkip"]["body"])
        self.assertFalse(out["shopBlank"]["ok"])
        self.assertEqual(out["shopBlank"]["reason"], "no price")
        self.assertEqual(out["shopGone"]["subject"], "WTS 0 items")
        self.assertEqual(out["shopGone"]["body"], "SOLD Grief Phase Blade\n30 fg")
        self.assertNotIn("SHOULD NOT APPEAR", out["shopGone"]["body"])

    def test_a_post_shows_the_screenshot_that_named_the_item(self):
        if NODE is None:
            self.skipTest("node is not on this machine")
        pane = _between(self.bible, 'id="tab-d2jsp"', 'id="tab-vault"')
        script = pane.split("<script>", 1)[1].split("</script>", 1)[0]
        card_at = script.index("  function cardHtml(")
        cards_at = script.index("\n  function ", card_at + 1)   # REG-2883 the function, never a size
        self.assertIn("d2jspArt(n)", script[card_at:cards_at])
        draft_fn = self.bible.index("function openDraft(")
        draft_end = self.bible.index("function showReceipt(", draft_fn)
        self.assertLess(draft_end - draft_fn, 1400)
        shown_box = self.bible[draft_fn:draft_end]
        self.assertIn("d2jspMountShots(host, draft)", shown_box)
        read_at = self.bible.index("function d2jspShotRead(")
        read_end = self.bible.index("function d2jspArt(", read_at)
        reader = self.bible[read_at:read_end]
        self.assertIn("getItem('d2r_intakeLog')", reader)
        self.assertNotIn("setItem", reader)
        mount_at = self.bible.index("function d2jspMountShots(")
        mount_end = self.bible.index("function openDraft(", mount_at)
        mount = self.bible[mount_at:mount_end]
        self.assertLess(mount.index("shown !== String(draft.body)"), mount.index("view.hidden = true"))
        self.assertIn("pre.textContent = row.body", mount)
        self.assertIn("d2jspPostPairs(draft, log)", mount)
        self.assertIn("d2jspShotCell(row.name, row.shot)", mount)
        self.assertLess(mount.index("line.appendChild(pre)"), mount.index("line.appendChild(d2jspShotCell"))
        wide_col = self.bible.index("grid-template-columns:minmax(0,1fr) 220px")
        narrow_col = self.bible.index("grid-template-columns:minmax(0,1fr) 112px", wide_col)
        self.assertLess(wide_col, narrow_col)
        self.assertNotIn("grid-template-columns:168px minmax(0,1fr)", self.bible)
        cell_rule = self.bible[self.bible.index("#d2jsp-draft-host .d2jsp-shot-cell{"):self.bible.index("#d2jsp-draft-host .d2jsp-shot-cell >")]
        self.assertNotIn("min-height", cell_rule)
        self.assertIn("object-fit:cover", self.bible[wide_col:narrow_col])
        paint_at = script.index("function paint(){")
        show_at = script.index("window._d2jspShow = function(){", paint_at)
        self.assertIn("_vHydrateShots(list)", script[paint_at:show_at])
        self.assertNotIn("draft.blocks", self.bible[self.bible.index("function postDraft("):self.bible.index("window.addEventListener('message'", self.bible.index("function postDraft("))])
        self.assertNotIn("d2r_intakeLog", _read(BEACON))
        body = r"""
var log = [
  { items: ['Grief'], pf: [{ nw: ['Shako'], th: 'data:image/gif;base64,QQQQ', ff: 'shako.png' }] },
  { pf: [{ nw: ['Grief'], th: 'data:image/gif;base64,AAAA', ff: 'grief.png' }] },
  { pf: [{ unr: ['Blade Bow (4os low base)'], th: 'data:image/gif;base64,BBBB', ff: 'bow.png' }] },
  { pf: [{ nw: ["Guardian's Thunder"], th: 'javascript:alert(1)', ff: 'C:/secret/thunder.png' }] },
  { pf: [{ mf: ['Guardian\u2019s Thunder'], th: 'data:image/png;base64,CCCC', ff: 'thunder.png' }] },
  { pf: [{ own: ['Tarnhelm'], th: 'javascript:alert(1)', ff: 'tarn.png' }] },
  { pf: [{ nw: ['Grief'], ff: 'newer-grief.png' }, { nw: ['Grief'], th: 'data:image/gif;base64,OLD', ff: 'old-grief.png' }] }
];
var griefOnly = [
  { pf: [{ nw: ['Grief'], ff: 'newer-grief.png' }] },
  { pf: [{ nw: ['Grief'], th: 'data:image/gif;base64,OLD', ff: 'old-grief.png' }] }
];
var shop = d2jspShopDraft([
  {name:'Grief', base:'Phase Blade', mods:'+340-400% Enhanced Damage', copies:1, fg:30, sold:false},
  {name:"Guardian's Thunder", base:'Colossal Jewel', mods:'Adds 1-75 lightning damage', copies:1, fg:1100, sold:false}
]);
var pairs = d2jspPostPairs(shop, log);
var bow = d2jspShotOf('Blade Bow', log);
var tarn = d2jspShotOf('Tarnhelm', log);
var none = d2jspShotOf('Grief', []);
var missing = d2jspShotOf('Grief', null);
var listed = d2jspShotOf('Grief', log.slice(0, 1));
var older = d2jspShotOf('Grief', griefOnly);
var bad = d2jspPostPairs({ body: 'Selling Grief Phase Blade\n30 fg', blocks: [{ name: 'Shako', body: 'SOLD Shako\n10 fg' }] }, log);
var one = d2jspDraft('Grief', 'Phase Blade', '+340-400% Enhanced Damage', 1, 30);
var onePairs = d2jspPostPairs(one, log);
function El(tag) {
  this.tag = tag; this.childNodes = []; this.hidden = false; this.attrs = {}; this.src = '';
}
El.prototype.setAttribute = function(k, v){ this.attrs[k] = String(v); };
El.prototype.getAttribute = function(k){ return Object.prototype.hasOwnProperty.call(this.attrs, k) ? this.attrs[k] : null; };
El.prototype.addEventListener = function(){};
El.prototype.appendChild = function(ch){ ch.parentNode = this; this.childNodes.push(ch); return ch; };
El.prototype.insertBefore = function(ch, ref){
  ch.parentNode = this;
  var i = this.childNodes.indexOf(ref);
  if (i < 0) this.childNodes.push(ch); else this.childNodes.splice(i, 0, ch);
  return ch;
};
El.prototype.removeChild = function(ch){
  var i = this.childNodes.indexOf(ch);
  if (i >= 0) this.childNodes.splice(i, 1);
  ch.parentNode = null;
};
El.prototype.querySelectorAll = function(sel){
  var out = [], wantAttr = '', wantTag = '';
  if (sel.charAt(0) === '[') wantAttr = sel.slice(1, -1); else wantTag = sel;
  function walk(node){
    if (wantAttr && node.attrs && Object.prototype.hasOwnProperty.call(node.attrs, wantAttr)) out.push(node);
    if (wantTag && node.tag === wantTag) out.push(node);
    (node.childNodes || []).forEach(walk);
  }
  walk(this);
  return out;
};
El.prototype.querySelector = function(sel){ return this.querySelectorAll(sel)[0] || null; };
Object.defineProperty(El.prototype, 'textContent', {
  get: function(){
    if (this.childNodes && this.childNodes.length) {
      return this.childNodes.map(function(ch){ return ch.textContent; }).join('');
    }
    return this._text || '';
  },
  set: function(v){ this._text = String(v == null ? '' : v); this.childNodes = []; }
});
document.createElement = function(tag){ return new El(tag); };
window.LSR = { getItem: function(k){ return k === 'd2r_intakeLog' ? JSON.stringify(log) : null; } };
var host = new El('div');
var view = new El('pre');
view.setAttribute('data-d2jsp-draft-view', '');
view.textContent = shop.body;
host.appendChild(view);
window._d2jspMountShots(host, shop);
var pres = host.querySelectorAll('pre').filter(function(node){ return node !== view; });
var srcs = [];
function walkImg(node){
  if (node.tag === 'img') srcs.push(node.src);
  (node.childNodes || []).forEach(walkImg);
}
walkImg(host);
var rowOrder = [];
function walkRows(node){
  if (node.className === 'd2jsp-shot-row') {
    rowOrder.push((node.childNodes || []).map(function(ch){ return ch.tag; }));
  }
  (node.childNodes || []).forEach(walkRows);
}
walkRows(host);
var host2 = new El('div');
var view2 = new El('pre');
view2.setAttribute('data-d2jsp-draft-view', '');
view2.textContent = 'Selling Grief Phase Blade\n30 fg';
host2.appendChild(view2);
window._d2jspMountShots(host2, { body: view2.textContent, blocks: [{ name: 'Shako', body: 'SOLD Shako\n10 fg' }] });
process.stdout.write(JSON.stringify({
  shop: shop, pairs: pairs, bow: bow, tarn: tarn, none: none, missing: missing,
  listed: listed, older: older, bad: bad, one: one, onePairs: onePairs,
  mounted: {
    hidden: view.hidden, view: view.textContent, shown: pres.map(function(node){ return node.textContent; }),
    srcs: srcs, rows: rowOrder, badHidden: view2.hidden, badPairs: !!host2.querySelector('[data-d2jsp-pairs]')
  }
}));
"""
        stubs = r"""
var document = {
  documentElement: { classList: { contains: function(){ return false; } } },
  getElementById: function(){ return null; },
  addEventListener: function(){},
  createElement: function(){ return { style: {}, hidden: true, querySelector: function(){ return null; }, setAttribute: function(){} }; },
  body: { appendChild: function(){} }
};
var localStorage = { _m: {}, getItem: function(k){ return this._m[k] || null; }, setItem: function(k, v){ this._m[k] = String(v); } };
var location = { hostname: '127.0.0.1' };
var window = { addEventListener: function(){}, LSR: null };
"""
        out = json.loads(_node(stubs + script, body))
        self.assertEqual(out["shop"]["blocks"][0]["name"], "Grief")
        self.assertEqual(out["shop"]["blocks"][1]["name"], "Guardian's Thunder")
        self.assertEqual(
            "\n\n".join(block["body"] for block in out["shop"]["blocks"]),
            out["shop"]["body"],
        )
        self.assertNotIn("data:image", out["shop"]["body"])
        self.assertNotIn("shako.png", out["shop"]["body"])
        self.assertTrue(out["pairs"]["ok"])
        self.assertEqual(out["pairs"]["rows"][0]["shot"]["th"], "data:image/gif;base64,AAAA")
        self.assertEqual(out["pairs"]["rows"][0]["shot"]["ff"], "grief.png")
        self.assertEqual(out["pairs"]["rows"][1]["shot"]["th"], "data:image/png;base64,CCCC")
        self.assertEqual(out["pairs"]["rows"][1]["shot"]["ff"], "thunder.png")
        self.assertEqual(out["bow"]["th"], "data:image/gif;base64,BBBB")
        self.assertEqual(out["tarn"]["th"], "")
        self.assertEqual(out["tarn"]["ff"], "tarn.png")
        self.assertIsNone(out["none"])
        self.assertIsNone(out["missing"])
        self.assertIsNone(out["listed"])
        self.assertEqual(out["older"]["th"], "data:image/gif;base64,OLD")
        self.assertEqual(out["older"]["ff"], "old-grief.png")
        self.assertFalse(out["bad"]["ok"])
        self.assertEqual(out["bad"]["rows"], [])
        self.assertEqual(out["onePairs"]["rows"][0]["name"], "Grief")
        self.assertEqual(out["onePairs"]["rows"][0]["body"], out["one"]["body"])
        self.assertEqual(out["onePairs"]["rows"][0]["shot"]["ff"], "grief.png")
        mounted = out["mounted"]
        self.assertTrue(mounted["hidden"])
        self.assertEqual(mounted["view"], out["shop"]["body"])
        self.assertEqual("\n\n".join(mounted["shown"]), out["shop"]["body"])
        self.assertEqual(mounted["srcs"], ["data:image/gif;base64,AAAA", "data:image/png;base64,CCCC"])
        self.assertEqual(mounted["rows"], [["pre", "div"], ["pre", "div"]])
        self.assertNotIn("data:image/gif;base64,QQQQ", mounted["srcs"])
        self.assertFalse(mounted["badHidden"])
        self.assertFalse(mounted["badPairs"])

    def test_the_room_lists_the_vault_and_posts_through_chrome(self):
        pane = _between(self.bible, 'id="tab-d2jsp"', 'id="tab-vault"')
        self.assertNotIn("Copy the bridge", pane)
        self.assertNotIn("d2jsp-bridge", pane)
        self.assertNotIn("cannot save the file", pane)
        self.assertNotIn("Install the bridge", pane)
        self.assertNotIn("Tag for trade", pane)
        room = pane.split("<script>", 1)[0]
        self.assertNotIn("<textarea", room)
        self.assertEqual(room.count('id="d2jsp-find"'), 1)
        self.assertIn('class="d2jsp-scroll"', room)
        self.assertNotIn("Read the public price", pane)
        self.assertNotIn("data-d2jsp-read", pane)
        end = self.bible.index("/* ⟦D2JSP DESK END⟧ */")
        names = self.bible.index("function names(){", end)
        esc_at = self.bible.index("function esc(s){", names)
        self.assertLess(esc_at - names, 1200)
        names_body = self.bible[names:esc_at]
        self.assertIn("d2r_muleAssign", names_body)
        self.assertNotIn("typeof assign", names_body)
        trade = self.bible.index("function tradeNames(){", end)
        find_q = self.bible.index("function findQuery(){", trade)
        self.assertIn("d2jspIsQuest", self.bible[trade:find_q])
        paint = self.bible.index("function paint(){", end)
        show = self.bible.index("window._d2jspShow = function(){", paint)
        self.assertIn("trade = tradeNames()", self.bible[paint:show])
        show_end = self.bible.index("};", show)
        self.assertIn("refreshQuotes()", self.bible[show:show_end])
        post = self.bible.index("t.getAttribute('data-d2jsp-post')")
        handler = self.bible[post:self.bible.index("document.addEventListener('input'", post)]
        self.assertIn("/api/d2jsp_send", handler)
        self.assertNotIn("createObjectURL", handler)
        self.assertNotIn("window.open", handler)
        self.assertNotIn("clipboard", handler)
        self.assertNotIn("d2jspBridgeSource()", handler)
        self.assertIn("nothing was posted", handler)
        self.assertIn("reason === 'title'", handler)
        self.assertIn("The board title holds 50 characters, so nothing was posted.", handler)
        gate = handler.index("t.getAttribute('data-d2jsp-send') !== '1'")
        preview_ret = handler.index("return;", gate)
        match = handler.index("shown.textContent !== draft.body")
        again_ret = handler.index("return;", match)
        fetch_at = handler.index("/api/d2jsp_send")
        self.assertLess(gate, preview_ret)
        self.assertLess(preview_ret, match)
        self.assertIn("title.textContent !== draft.subject", handler)
        self.assertLess(match, again_ret)
        self.assertLess(again_ret, fetch_at)
        guard = handler.index("if (posting)")
        self.assertLess(again_ret, guard)
        self.assertLess(guard, fetch_at)
        arm = handler.index("posting = true;")
        shown_while_sending = handler.index("showPosting()", arm)
        self.assertLess(guard, arm)
        self.assertLess(arm, shown_while_sending)
        self.assertLess(shown_while_sending, fetch_at)
        self.assertLess(fetch_at, handler.index("showReceipt('confirmed'"))
        self.assertLess(fetch_at, handler.index("settle();"))
        posting_fn = self.bible.index("function showPosting(")
        self.assertEqual(self.bible.count("function showPosting("), 1)
        posting_box = self.bible[posting_fn:self.bible.index("/* ⟦D2JSP PLANNER ESC BEGIN⟧", posting_fn)]
        self.assertIn("d2jspBoardSay('ask')", posting_box)
        self.assertIn("Asking Chrome on this machine to post on board ", self.desk)
        self.assertIn("D2:R RotW Softcore Ladder Trading", self.desk)
        self.assertNotIn("non-ladder forum", self.bible)
        self.assertIn("data-d2jsp-draft-close", posting_box)
        self.assertNotIn("data-d2jsp-send", posting_box)
        self.assertNotIn("/api/d2jsp_send", posting_box)
        draft_fn = self.bible.index("function openDraft(")
        self.assertEqual(self.bible.count("function openDraft("), 1)
        draft_end = self.bible.index("function showReceipt(", draft_fn)
        self.assertLess(draft_end - draft_fn, 1400)
        shown_box = self.bible[draft_fn:draft_end]
        self.assertIn("data-d2jsp-draft-view", shown_box)
        self.assertIn("data-d2jsp-draft-subject", shown_box)
        self.assertIn('data-d2jsp-send="1"', shown_box)
        self.assertIn("draft.forum", shown_box)
        self.assertNotIn("/api/d2jsp_send", shown_box)
        app = _read(os.path.join(HERE, "control_app.py"))
        self.assertEqual(app.count('if path == "/api/d2jsp_send":'), 1)
        route = app.index('if path == "/api/d2jsp_send":')
        nxt = app.index('if path == "/api/roster-book":', route)
        block = app[route:nxt]
        self.assertIn("import d2jsp_chrome as _d2jsp", block)
        self.assertIn("_d2jsp.d2jsp_send(", block)
        self.assertEqual(app.count('if path == "/api/d2jsp_quote":'), 1)
        quote_route = app.index('if path == "/api/d2jsp_quote":')
        quote_next = app.index('if path in ("/", "/index.html", "/ui"):', quote_route)
        qblock = app[quote_route:quote_next]
        self.assertIn("import d2jsp_chrome as _d2jsp", qblock)
        self.assertIn("_d2jsp.d2jsp_quote(", qblock)
        self.assertNotIn("d2jsp", _read(BEACON))

    def test_a_quest_item_is_not_a_trade_and_the_range_is_the_reading(self):
        if NODE is None:
            self.skipTest("node is not on this machine")
        with open(os.path.join(ROOT, "tv", "item_tables.json"), encoding="utf-8") as fh:
            tables = json.load(fh)
        names = set()
        for code in QUEST_CODES:
            names.add(tables["items"][code]["name"])
        for row in tables["uniques"].values():
            if isinstance(row, dict) and row.get("code") in QUEST_CODES and row.get("name"):
                names.add(row["name"])

        def fold(text):
            return " ".join(str(text).replace("\u2019", "'").replace("\u2018", "'").lower().split())

        expected = {fold(n) for n in names}
        expected.update(QUEST_EXTRA)
        body = r"""
var line = d2jspPriceLine({reason:'read', fg:30, n:3, low:10, high:50, readAt:'2026-10-12T20:01:00.000Z'});
var one = d2jspPriceLine({reason:'read', fg:40, n:1, low:40, high:40, readAt:'2026-10-12T20:02:00.000Z'});
var same = d2jspPriceLine({reason:'read', fg:15, n:4, low:15, high:15, readAt:'2026-10-12T20:03:00.000Z'});
var none = d2jspPriceLine({reason:'no prices', fg:null, n:0, low:null, high:null, readAt:'2026-10-12T20:04:00.000Z'});
var blank = d2jspPriceLine(null);
var login = d2jspPriceLine({reason:'need-login', fg:null, n:0, low:null, high:null, readAt:'2026-10-12T20:05:00.000Z'});
var unans = d2jspPriceLine({reason:'unanswered', fg:null, n:0, low:null, high:null, readAt:null});
var paused = d2jspPriceLine({reason:'paused', say:'paused while checks run', fg:null, n:0, low:null, high:null, readAt:''});
var badAt = d2jspPriceLine({reason:'no prices', fg:null, n:0, low:null, high:null, readAt:'not a time'});
process.stdout.write(JSON.stringify({
  list: D2JSP_QUEST,
  cube: d2jspIsQuest('Horadric Cube'),
  stack: d2jspIsQuest('2x Horadric Cube'),
  terror: d2jspIsQuest('Key of Terror'),
  black: d2jspIsQuest('Blackhand Key'),
  gheed: d2jspIsQuest("Gheed's Fortune"),
  eye: d2jspIsQuest("Khalim's Eye"),
  baal: d2jspIsQuest("Baal's Eye"),
  token: d2jspIsQuest('Token of Absolution'),
  keys: d2jspIsQuest('Keys'),
  line: line, one: one, same: same, none: none, blank: blank, login: login, unans: unans, badAt: badAt, paused: paused
}));
"""
        out = json.loads(_node(self.desk, body))
        self.assertEqual(set(out["list"]), expected)
        self.assertTrue(out["cube"])
        self.assertTrue(out["stack"])
        self.assertTrue(out["eye"])
        self.assertTrue(out["keys"])
        self.assertFalse(out["terror"])
        self.assertFalse(out["black"])
        self.assertFalse(out["gheed"])
        self.assertFalse(out["baal"])
        self.assertFalse(out["token"])
        self.assertIn("10", out["line"])
        self.assertIn("50", out["line"])
        self.assertIn("30", out["line"])
        self.assertNotIn("\u2013", out["one"])
        self.assertIn("40 fg", out["one"])
        self.assertNotIn("\u2013", out["same"])
        self.assertIn("15 fg", out["same"])
        self.assertIn("returned no fg number", out["none"])
        self.assertEqual(out["blank"], "Public price unknown.")
        self.assertIn("Chrome login", out["login"])
        self.assertNotIn("fg,", out["login"])
        # GrokBot bug 9 (2026-10-27) - a local 24-hour time, never the raw UTC stamp; no made-up reading
        import re as _re
        for k in ("line", "one", "same", "none"):
            self.assertIsNone(_re.search(r"\d{4}-\d\d-\d\dT\d\d:\d\d", out[k]), "a raw ISO stamp in %s: %r" % (k, out[k]))
            self.assertIsNotNone(_re.search(r"\b\d\d:\d\d\b", out[k]), "%s lost its time: %r" % (k, out[k]))
        self.assertEqual(out["unans"], "Public price unknown. No price reader answered this page.")
        # v3861 (#230 6644125606): his Shako click during a push read "No price reader answered" - the console HAD answered
        self.assertIn("running its checks", out["paused"])
        self.assertNotIn("No price reader answered", out["paused"])
        self.assertEqual(out["badAt"], "Public price unknown.", "an unreadable stamp was printed: %r" % out["badAt"])

    def test_a_logged_in_search_prices_only_the_lines_that_name_the_item(self):
        import d2jsp_chrome as desk
        calls = {"urls": [], "cookie": 0}

        def cookie_get():
            calls["cookie"] += 1
            return "sid=SECRETCOOKIE", "ok"

        def no_cookie():
            calls["cookie"] += 1
            return None, "need-login"

        page = "\n".join([
            "Oct 12, 2026",
            "Gheeds Fortune gc 106/35/13 - 20fg",
            "Gheeds Fortune gc 108/31/12 - 15fg",
            "Pcomb plain - 10fg x 1",
            "35MF gheeds",
            "Gheed's Fortune 10 fg",
            "Summon Skill Necro + 26 life - 25fg",
        ])

        def transport(method, url, headers, data):
            calls["urls"].append((method, url, data))
            self.assertNotIn("SECRETCOOKIE", url)
            self.assertNotIn("SECRETCOOKIE", data.decode("utf-8") if isinstance(data, bytes) else str(data or ""))
            self.assertEqual(headers.get("Cookie"), "sid=SECRETCOOKIE")
            return 200, {}, page.encode("utf-8")

        def chrome_fetch(item_name, cookie):
            raise AssertionError("a priced page does not need a second browser")

        code, out = desk.d2jsp_quote(
            "Gheed's Fortune", "http://evil.example", "evil.example", 17772,
            cookie_get=cookie_get, transport=transport,
        )
        self.assertEqual(code, 403)
        self.assertEqual(out["reason"], "origin")
        self.assertIsNone(out["fg"])
        self.assertEqual(calls["cookie"], 0)
        self.assertEqual(calls["urls"], [])

        code, out = desk.d2jsp_quote(
            "Gheed's Fortune", "http://127.0.0.1:17772", "127.0.0.1:17772", 17772,
            cookie_get=no_cookie, transport=transport,
        )
        self.assertEqual(out["reason"], "need-login")
        self.assertIsNone(out["fg"])
        self.assertEqual(calls["urls"], [])
        self.assertNotIn("SECRETCOOKIE", json.dumps(out))

        code, out = desk.d2jsp_quote(
            "Gheed's Fortune", "http://127.0.0.1:17772", "127.0.0.1:17772", 17772,
            cookie_get=cookie_get, transport=transport, chrome_fetch=chrome_fetch,
        )
        self.assertEqual(code, 200)
        self.assertEqual(out["reason"], "read")
        self.assertEqual(out["fg"], 15)
        self.assertEqual(out["low"], 10)
        self.assertEqual(out["high"], 20)
        self.assertEqual(out["n"], 3)
        self.assertEqual(out["board"], 268)
        self.assertEqual(len(calls["urls"]), 1)
        self.assertEqual(calls["urls"][0][0], "POST")
        self.assertIn("search.php?c=7&f=268&t=0", calls["urls"][0][1])
        self.assertIn(b"stext=gheeds", calls["urls"][0][2])
        self.assertNotIn("SECRETCOOKIE", json.dumps(out))
        self.assertNotIn("Gheeds Fortune gc", json.dumps(out))

    def test_a_challenge_page_is_read_through_a_scratch_chrome(self):
        import d2jsp_chrome as desk
        page = "\n".join([
            "Oct 12, 2026",
            "Gheeds Fortune gc 106/35/13 - 20fg",
            "Gheeds Fortune gc 108/31/12 - 15fg",
            "Pcomb plain - 10fg x 1",
            "35MF gheeds",
            "Gheed's Fortune 10 fg",
            "Summon Skill Necro + 26 life - 25fg",
        ])
        seen = []

        def transport(method, url, headers, data):
            self.assertEqual(method, "POST")
            self.assertIn("search.php?c=7&f=268", url)
            return 403, {}, b"<title>Just a moment...</title>"

        def chrome_fetch(item_name, cookie):
            seen.append(item_name)
            self.assertIn("SECRETCOOKIE", cookie)
            self.assertNotIn("SECRETCOOKIE", item_name)
            return page

        code, out = desk.d2jsp_quote(
            "Gheed's Fortune", "http://127.0.0.1:17772", "127.0.0.1:17772", 17772,
            cookie_get=lambda: ("sid=SECRETCOOKIE", "ok"),
            transport=transport, chrome_fetch=chrome_fetch,
        )
        self.assertEqual(code, 200)
        self.assertEqual(seen, ["Gheed's Fortune"])
        self.assertEqual(out["reason"], "read")
        self.assertEqual(out["fg"], 15)
        self.assertEqual(out["low"], 10)
        self.assertEqual(out["high"], 20)
        self.assertEqual(out["n"], 3)
        self.assertEqual(out["board"], 268)
        self.assertNotIn("SECRETCOOKIE", json.dumps(out))

    def test_chrome_posts_only_a_priced_board_268_draft_from_this_console(self):
        import d2jsp_chrome as desk
        calls = {"cookie": 0, "open": 0, "urls": []}

        def cookie_get():
            calls["cookie"] += 1
            return "sid=SECRETCOOKIE", "ok"

        def open_login():
            calls["open"] += 1
            return True

        def no_cookie():
            calls["cookie"] += 1
            return None, "need-login"

        code, out = _send_fresh(desk,
            {"subject": "WTS Grief", "body": "WTS Grief\n30 fg", "forum": 268},
            "https://evil.example", "127.0.0.1:17772", 17772,
            cookie_get=cookie_get, open_login=open_login,
        )
        self.assertEqual(code, 403)
        self.assertEqual(out["reason"], "origin")
        self.assertEqual(calls["cookie"], 0)
        self.assertEqual(calls["open"], 0)

        code, out = _send_fresh(desk,
            {"subject": "WTS Grief", "body": "WTS Grief\n30 fg", "forum": 243},
            "http://127.0.0.1:17772", "127.0.0.1:17772", 17772,
            cookie_get=cookie_get, open_login=open_login,
        )
        self.assertEqual(out["reason"], "wrong-board")
        self.assertEqual(calls["cookie"], 0)

        code, out = _send_fresh(desk,
            {"subject": "WTS Grief", "body": "WTS Grief", "forum": 268},
            None, "127.0.0.1:17772", 17772,
            cookie_get=cookie_get, open_login=open_login,
        )
        self.assertEqual(out["reason"], "no-price")
        self.assertEqual(calls["cookie"], 0)

        code, out = _send_fresh(desk,
            {"subject": "ISO Grief", "body": "ISO Grief\n30 fg", "forum": 268},
            None, "127.0.0.1:17772", 17772,
            cookie_get=cookie_get, open_login=open_login,
        )
        self.assertEqual(out["reason"], "no-price")
        self.assertEqual(calls["cookie"], 0)

        def refuse_chrome(subject, text, cookie):
            raise AssertionError("a title past 50 characters must not open Chrome")

        code, out = _send_fresh(desk,
            {"subject": "WTS " + ("A" * 47), "body": "WTS\n30 fg", "forum": 268},
            "http://127.0.0.1:17772", "127.0.0.1:17772", 17772,
            cookie_get=cookie_get, open_login=open_login, chrome_post=refuse_chrome,
        )
        self.assertFalse(out["ok"])
        self.assertEqual(out["reason"], "title")
        self.assertEqual(len("WTS " + ("A" * 47)), 51)

        logged_out = "<p>You are not currently logged in.</p>"
        def transport(method, url, headers, data):
            calls["urls"].append((method, url))
            self.assertNotIn("SECRETCOOKIE", url)
            self.assertEqual(url, desk.COMPOSE_URL)
            return 200, {}, logged_out.encode()

        code, out = _send_fresh(desk,
            {"subject": "WTS Grief Phase Blade", "body": "WTS Grief Phase Blade\n+damage\n30 fg", "forum": 268},
            "http://127.0.0.1:17772", "127.0.0.1:17772", 17772,
            cookie_get=no_cookie, transport=transport, open_login=open_login,
        )
        self.assertEqual(out["reason"], "need-login")
        self.assertTrue(out["opened"])
        self.assertEqual(calls["urls"], [])
        self.assertNotIn("SECRETCOOKIE", json.dumps(out))

        def transport_logged_out(method, url, headers, data):
            calls["urls"].append(method)
            self.assertEqual(method, "GET")
            return 200, {}, logged_out.encode()

        code, out = _send_fresh(desk,
            {"subject": "WTS Grief Phase Blade", "body": "WTS Grief Phase Blade\n30 fg", "forum": 268},
            "http://127.0.0.1:17772", "127.0.0.1:17772", 17772,
            cookie_get=cookie_get, transport=transport_logged_out, open_login=open_login,
        )
        self.assertEqual(out["reason"], "need-login")
        self.assertTrue(out["opened"])
        self.assertEqual(calls["urls"], ["GET"])
        self.assertEqual(calls["open"], 2)

        form = (
            '<a href="login.php?mode=logout">out</a>'
            '<input type="hidden" name="form_token" value="abc">'
            '<input name="subject">'
            '<textarea name="message"></textarea>'
            '<input type="submit" name="post" value="Submit">'
        )
        posted = {}

        def transport_ok(method, url, headers, data):
            self.assertEqual(url, desk.COMPOSE_URL)
            self.assertIn("Chrome/", headers.get("User-Agent", ""))
            self.assertNotEqual(headers.get("User-Agent"), "Mozilla/5.0")
            self.assertIn("sid=SECRETCOOKIE", headers.get("Cookie", ""))
            if method == "GET":
                return 200, {}, form.encode()
            posted["body"] = data.decode()
            return 302, {"Location": "https://forums.d2jsp.org/topic.php?t=9&f=268"}, b""

        code, out = _send_fresh(desk,
            {"subject": "Selling Grief Phase Blade", "body": "Selling Grief Phase Blade\n+damage\n30 fg", "forum": 268},
            "http://localhost:17772", "localhost:17772", 17772,
            cookie_get=cookie_get, transport=transport_ok, open_login=open_login,
        )
        self.assertTrue(out["ok"])
        self.assertEqual(out["reason"], "submitted")
        self.assertIn("form_token=abc", posted["body"])
        self.assertIn("subject=Selling", posted["body"])
        self.assertIn("30+fg", posted["body"])
        self.assertNotIn("SECRETCOOKIE", json.dumps(out))
        self.assertEqual(calls["open"], 2)

        def transport_back(method, url, headers, data):
            return 200, {}, form.encode()

        code, out = _send_fresh(desk,
            {"subject": "WTS Grief Phase Blade", "body": "WTS Grief Phase Blade\n30 fg", "forum": 268},
            "http://127.0.0.1:17772", "127.0.0.1:17772", 17772,
            cookie_get=cookie_get, transport=transport_back, open_login=open_login,
        )
        self.assertFalse(out["ok"])
        self.assertEqual(out["reason"], "not-posted")

        def transport_down(method, url, headers, data):
            raise OSError("down")

        code, out = _send_fresh(desk,
            {"subject": "WTS Grief Phase Blade", "body": "WTS Grief Phase Blade\n30 fg", "forum": 268},
            "http://127.0.0.1:17772", "127.0.0.1:17772", 17772,
            cookie_get=cookie_get, transport=transport_down, open_login=open_login,
        )
        self.assertFalse(out["ok"])
        self.assertEqual(out["reason"], "unread")
        self.assertNotIn("submitted", out["reason"])

    def test_a_challenge_page_is_posted_through_a_scratch_chrome(self):
        import d2jsp_chrome as desk
        seen = {}

        def transport(method, url, headers, data):
            self.assertEqual(method, "GET")
            self.assertEqual(url, desk.COMPOSE_URL)
            return 200, {}, b"<title>Just a moment...</title>"

        def chrome_post(subject, text, cookie):
            seen["subject"] = subject
            seen["text"] = text
            self.assertIn("SECRETCOOKIE", cookie)
            self.assertNotIn("SECRETCOOKIE", subject)
            self.assertNotIn("SECRETCOOKIE", text)
            return "https://forums.d2jsp.org/topic.php?t=9&f=268"

        code, out = _send_fresh(desk,
            {"subject": "WTS Grief Phase Blade", "body": "WTS Grief Phase Blade\n30 fg", "forum": 268},
            "http://127.0.0.1:17772", "127.0.0.1:17772", 17772,
            cookie_get=lambda: ("sid=SECRETCOOKIE", "ok"),
            transport=transport, open_login=lambda: True, chrome_post=chrome_post,
        )
        self.assertEqual(code, 200)
        self.assertTrue(out["ok"])
        self.assertEqual(out["reason"], "submitted")
        self.assertEqual(out["topic"], "https://forums.d2jsp.org/topic.php?t=9&f=268")
        self.assertEqual(seen["subject"], "WTS Grief Phase Blade")
        self.assertIn("30 fg", seen["text"])
        self.assertNotIn("SECRETCOOKIE", json.dumps(out))

        def chrome_post_login(subject, text, cookie):
            return "https://forums.d2jsp.org/login.php?redirect=post"

        code, out = _send_fresh(desk,
            {"subject": "WTS Grief Phase Blade", "body": "WTS Grief Phase Blade\n30 fg", "forum": 268},
            "http://127.0.0.1:17772", "127.0.0.1:17772", 17772,
            cookie_get=lambda: ("sid=SECRETCOOKIE", "ok"),
            transport=transport, open_login=lambda: False, chrome_post=chrome_post_login,
        )
        self.assertFalse(out["ok"])
        self.assertEqual(out["reason"], "need-login")
        self.assertNotIn("SECRETCOOKIE", json.dumps(out))

        # REG-2490 - the submit was clicked and the board never left post.php. That post may be up,
        # so it is maybe-sent with the board and the time, never the "not-posted" that read as
        # "nothing was posted" and invited a second post. Only a run that never clicked is not-posted.
        def chrome_post_stay(subject, text, cookie):
            return {"landed": "https://forums.d2jsp.org/post.php?mode=post&f=268", "clicked": True}

        code, out = _send_fresh(desk,
            {"subject": "WTS Grief Phase Blade", "body": "WTS Grief Phase Blade\n30 fg", "forum": 268},
            "http://127.0.0.1:17772", "127.0.0.1:17772", 17772,
            cookie_get=lambda: ("sid=SECRETCOOKIE", "ok"),
            transport=transport, open_login=lambda: False, chrome_post=chrome_post_stay,
        )
        self.assertFalse(out["ok"])
        self.assertEqual(out["reason"], "maybe-sent")
        self.assertEqual(out["board"], 268)
        self.assertRegex(out["at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$")
        self.assertNotIn("topic", out)
        self.assertNotIn("SECRETCOOKIE", json.dumps(out))

        def chrome_post_never(subject, text, cookie):
            return {"landed": "https://forums.d2jsp.org/post.php?mode=post&f=268", "clicked": False}

        code, out = _send_fresh(desk,
            {"subject": "WTS Grief Phase Blade", "body": "WTS Grief Phase Blade\n30 fg", "forum": 268},
            "http://127.0.0.1:17772", "127.0.0.1:17772", 17772,
            cookie_get=lambda: ("sid=SECRETCOOKIE", "ok"),
            transport=transport, open_login=lambda: False, chrome_post=chrome_post_never,
        )
        self.assertFalse(out["ok"])
        self.assertEqual(out["reason"], "not-posted")

        # REG-2494 - the window src[def _chrome_post : def d2jsp_quote] was held under 7200
        # characters so that it stayed the post function and nothing beside it. REG-2190's sweep
        # took it to 7226 and the law went red on its own number. The post flow is now read from
        # its own functions, which cannot reach a neighbour, so there is no number to outgrow.
        box = _code_of(desk._chrome_post, desk._scratch_chrome, desk._fill_js,
                       desk._open_link_js, desk._board_url)
        self.assertIn("--user-data-dir=%s", box)
        self.assertIn("forum.php?f=", box)
        self.assertIn("New Trade", box)
        self.assertIn('textarea[name="Post"]', box)
        self.assertIn('input[name="ttitle"]', box)
        self.assertIn('input[name="submit"]', box)
        self.assertIn("Selling Item", box)
        self.assertIn("subject.length>50", box)
        self.assertIn("sItalic", box)
        self.assertIn("btn.click()", box)
        self.assertIn("_chrome_bin()", box)
        self.assertNotIn('textarea[name="message"]', box)
        self.assertNotIn("mode=post", box)
        self.assertNotIn("form.submit", box)
        self.assertNotIn("9222", box)
        gate = _code_of(desk._send_through_chrome, desk._send_verdict)
        self.assertIn("_send_verdict(got, board, at, open_login)", gate)
        self.assertIn('topic = _public_topic(res["topic"])', gate)
        self.assertLess(gate.index('topic = _public_topic(res["topic"])'), gate.index('"submitted"'))
        self.assertIn('"topic": topic', gate)
        send = _code_of(desk.d2jsp_send, desk._send_locked, desk._send_route)
        self.assertIn("_send_through_chrome(", send)
        self.assertLess(send.index("transport is None and chrome_post is not False"), send.index('fetch("GET", COMPOSE_URL'))
        self.assertLess(send.index("_challenge_page(raw_text)"), send.index("parse_compose(raw)"))
        receipt = self.bible.index("  function showReceipt(")
        # REG-2882 - the window is the function itself (to the next room function), never a size: REG-2874 and REG-2870
        # grew showReceipt and put whySay before closeDraft (1,893 chars to closeDraft, measured), and a 1,400 cap went red
        # on reach
        receipt_end = self.bible.index("\n  function ", receipt + 1)
        panel = self.bible[receipt:receipt_end]
        self.assertIn("Confirmed", panel)
        self.assertIn("Not sent", panel)
        self.assertIn("https://forums.d2jsp.org/topic.php", panel)
        self.assertNotIn("window.open", panel)

        def live_post(subject, text, cookie):
            self.assertIn("SECRETCOOKIE", cookie)
            return "https://forums.d2jsp.org/topic.php?t=44&f=268#top"

        code, out = _send_fresh(desk,
            {"subject": "WTS Grief Phase Blade", "body": "WTS Grief Phase Blade\n30 fg", "forum": 268},
            "http://127.0.0.1:17772", "127.0.0.1:17772", 17772,
            cookie_get=lambda: ("sid=SECRETCOOKIE", "ok"),
            open_login=lambda: False, chrome_post=live_post,
        )
        self.assertTrue(out["ok"])
        self.assertEqual(out["reason"], "submitted")
        self.assertEqual(out["topic"], "https://forums.d2jsp.org/topic.php?t=44&f=268")
        self.assertNotIn("SECRETCOOKIE", json.dumps(out))

        # REG-2490 - a run that clicked and landed on another host has no receipt: the foreign
        # topic is never shown as his, and the click is maybe-sent, never "not-posted".
        def evil_post(subject, text, cookie):
            return {"landed": "https://evil.example/topic.php?t=1", "clicked": True,
                    "topic": "https://evil.example/topic.php?t=1"}

        code, out = _send_fresh(desk,
            {"subject": "WTS Grief Phase Blade", "body": "WTS Grief Phase Blade\n30 fg", "forum": 268},
            "http://127.0.0.1:17772", "127.0.0.1:17772", 17772,
            cookie_get=lambda: ("sid=SECRETCOOKIE", "ok"),
            open_login=lambda: False, chrome_post=evil_post,
        )
        self.assertFalse(out["ok"])
        self.assertEqual(out["reason"], "maybe-sent")
        self.assertNotIn("topic", out)
        self.assertNotIn("evil.example", json.dumps(out))

    def test_a_shop_list_updates_the_saved_topic_and_does_not_start_another(self):
        import d2jsp_chrome as desk
        shop = (
            "Selling Grief Phase Blade\n+damage\n30 fg\n\n"
            "SOLD Guardian's Thunder Colossal Jewel\n1100 fg"
        )
        self.assertTrue(desk._priced("Selling 1 item", shop))
        self.assertFalse(desk._priced("ISO list", shop))
        calls = {"cookie": 0, "new": 0, "edit": 0}

        def cookie_get():
            calls["cookie"] += 1
            return "sid=SECRETCOOKIE", "ok"

        long_body = "Selling Grief Phase Blade\n" + ("+1 to life\n" * 500) + "30 fg"
        self.assertGreater(len(long_body), 4000)
        code, out = _send_fresh(desk,
            {"subject": "Selling 1 item", "body": long_body, "forum": 268},
            "http://127.0.0.1:17772", "127.0.0.1:17772", 17772,
            cookie_get=cookie_get, open_login=lambda: False,
        )
        self.assertEqual(code, 200)
        self.assertEqual(out["reason"], "long")
        self.assertEqual(calls["cookie"], 0)

        def new_trade(subject, text, cookie):
            calls["new"] += 1
            raise AssertionError("an update must not start a new trade")

        def no_edit(topic, subject, text, cookie):
            calls["edit"] += 1
            self.assertEqual(topic, "https://forums.d2jsp.org/topic.php?t=9&f=268")
            self.assertIn("SECRETCOOKIE", cookie)
            self.assertNotIn("SECRETCOOKIE", subject)
            self.assertNotIn("SECRETCOOKIE", text)
            self.assertIn("SOLD Guardian's Thunder", text)
            return "no-edit"

        code, out = _send_fresh(desk,
            {"subject": "Selling 1 item", "body": shop, "forum": 268,
             "topic": "https://forums.d2jsp.org/topic.php?t=9&f=268"},
            "http://127.0.0.1:17772", "127.0.0.1:17772", 17772,
            cookie_get=cookie_get, open_login=lambda: False,
            chrome_post=new_trade, edit_post=no_edit,
        )
        self.assertFalse(out["ok"])
        self.assertEqual(out["reason"], "not-posted")
        self.assertEqual(calls["new"], 0)
        self.assertEqual(calls["edit"], 1)
        self.assertNotIn("topic", out)
        self.assertNotIn("SECRETCOOKIE", json.dumps(out))

        def edit_ok(topic, subject, text, cookie):
            calls["edit"] += 1
            return "https://forums.d2jsp.org/topic.php?t=9&f=268#top"

        code, out = _send_fresh(desk,
            {"subject": "Selling 1 item", "body": shop, "forum": 268,
             "topic": "https://forums.d2jsp.org/topic.php?t=9&f=268"},
            "http://127.0.0.1:17772", "127.0.0.1:17772", 17772,
            cookie_get=cookie_get, open_login=lambda: False,
            chrome_post=new_trade, edit_post=edit_ok,
        )
        self.assertTrue(out["ok"])
        self.assertEqual(out["reason"], "submitted")
        self.assertEqual(out["topic"], "https://forums.d2jsp.org/topic.php?t=9&f=268")
        self.assertEqual(calls["new"], 0)

        def foreign_edit(topic, subject, text, cookie):
            raise AssertionError("a foreign topic must not be edited")

        def new_ok(subject, text, cookie):
            calls["new"] += 1
            return "https://forums.d2jsp.org/topic.php?t=9&f=268"

        code, out = _send_fresh(desk,
            {"subject": "Selling 1 item", "body": shop, "forum": 268,
             "topic": "https://evil.example/topic.php?t=1"},
            "http://127.0.0.1:17772", "127.0.0.1:17772", 17772,
            cookie_get=cookie_get, open_login=lambda: False,
            chrome_post=new_ok, edit_post=foreign_edit,
        )
        self.assertTrue(out["ok"])
        self.assertEqual(calls["new"], 1)
        self.assertEqual(out["topic"], "https://forums.d2jsp.org/topic.php?t=9&f=268")

        edit = _code_of(desk._chrome_edit, desk._scratch_chrome, desk._fill_js, desk._open_link_js)
        self.assertIn('_open_link_js("Edit")', edit)
        self.assertIn('label!=="Edit"', desk._open_link_js("Edit"))
        self.assertIn("/post.php", edit)
        self.assertIn('textarea[name="Post"]', edit)
        self.assertIn('input[name="ttitle"]', edit)
        self.assertIn('input[name="submit"]', edit)
        self.assertIn("Selling Item", edit)
        self.assertIn("btn.click()", edit)
        self.assertNotIn("New Trade", edit)
        self.assertNotIn("mode=post", edit)
        self.assertNotIn("form.submit", edit)
        self.assertNotIn("9222", edit)
        send = _code_of(desk.d2jsp_send, desk._send_locked, desk._send_route)
        self.assertLess(
            send.index('_public_topic(str(body.get("topic")'),
            send.index("transport is None and chrome_post is not False"),
        )
        self.assertLess(send.index("_challenge_page(raw_text)"), send.index("parse_compose(raw)"))

    def test_the_cookie_header_is_only_the_d2jsp_host(self):
        import d2jsp_chrome as desk
        now = 1_700_000_000
        chrome_now = desk._chrome_now(now)
        rows = [
            ("example.com", "session", b"LEAKED", chrome_now + 10**12),
            (".d2jsp.org", "sid", b"desk-session", chrome_now + 10**12),
            ("forums.d2jsp.org", "old", b"stale", chrome_now - 10),
            ("notd2jsp.org", "sid", b"ALSOLEAKED", chrome_now + 10**12),
        ]
        header, reason = desk.cookie_header_from_rows(
            rows, "unused", now_utc=now, decrypt=lambda blob: blob.decode())
        self.assertEqual(reason, "ok")
        self.assertIn("sid=desk-session", header)
        self.assertNotIn("LEAKED", header)
        self.assertNotIn("ALSOLEAKED", header)
        self.assertNotIn("stale", header)
        self.assertIsNone(desk.decrypt_v10(b"v20not-this-format", "pw"))
        self.assertFalse(desk.console_may_post("https://evil.example", "127.0.0.1:17772", 17772))
        self.assertTrue(desk.console_may_post(None, "127.0.0.1:17772", 17772))
        # REG-2188 — a cross-site request carries no Origin but a browser-set Sec-Fetch-Site the page
        # cannot forge. A no-Origin GET from a page he visited (cross-site / same-site) is refused;
        # the console's own request (same-origin, none, or a client that omits the header) still passes.
        self.assertFalse(desk.console_may_post(None, "127.0.0.1:17772", 17772, "cross-site"))
        self.assertFalse(desk.console_may_post(None, "127.0.0.1:17772", 17772, "same-site"))
        self.assertTrue(desk.console_may_post(None, "127.0.0.1:17772", 17772, "same-origin"))
        self.assertTrue(desk.console_may_post(None, "127.0.0.1:17772", 17772, "none"))

        # REG-2190 — a scratch profile older than the stale bound is swept; a fresh one (an op in
        # flight) is left alone. No Chrome is planted, so nothing is killed; this tests the age gate.
        import tempfile as _tf, time as _tm, shutil as _sh
        _root = _tf.mkdtemp(prefix="sweep-test-")
        try:
            _old = os.path.join(_root, "d2jsp-quote-OLD"); os.makedirs(_old)
            _young = os.path.join(_root, "d2jsp-post-NEW"); os.makedirs(_young)
            _now = _tm.time() + desk._SCRATCH_STALE_S + 10
            os.utime(_young, (_now, _now))
            _removed = desk._sweep_stale_scratch(now=_now, tmp=_root)
            self.assertFalse(os.path.isdir(_old), "a stale scratch profile was not swept")
            self.assertTrue(os.path.isdir(_young), "a fresh (in-flight) scratch profile was swept")
            self.assertEqual(_removed, 1)
        finally:
            _sh.rmtree(_root, ignore_errors=True)

        password = "test-password"
        blob = desk.seal_v10(password, "roundtrip-value")
        if blob is None:
            return
        self.assertEqual(desk.decrypt_v10(blob, password), "roundtrip-value")
        import sqlite3
        import tempfile
        folder = tempfile.mkdtemp(prefix="d2jsp cookie ")
        db = os.path.join(folder, "Cookies")
        try:
            con = sqlite3.connect(db)
            con.execute("create table cookies (host_key text, name text, encrypted_value blob, expires_utc integer)")
            con.execute(
                "insert into cookies values (?,?,?,?)",
                (".d2jsp.org", "sid", blob, chrome_now + 10**12),
            )
            con.commit()
            con.close()
            read = desk._read_rows(db)
            self.assertEqual(len(read), 1)
            self.assertEqual(read[0][0], ".d2jsp.org")
            header, reason = desk.cookie_header_from_rows(read, password, now_utc=now)
            self.assertEqual(reason, "ok")
            self.assertEqual(header, "sid=roundtrip-value")
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    def test_a_chrome_cookie_opens_only_when_its_host_digest_matches(self):
        import hashlib
        import d2jsp_chrome as desk
        host = ".d2jsp.org"
        other = "forums.d2jsp.org"
        prefix = hashlib.sha256(host.encode("utf-8")).digest()
        self.assertEqual(len(prefix), 32)
        self.assertEqual(desk._cookie_text(prefix + b"desk-session", host), "desk-session")
        self.assertIsNone(desk._cookie_text(prefix + b"bad;value", host))
        self.assertEqual(desk._cookie_text(b"roundtrip-value", host), "roundtrip-value")
        password = "test-password"
        blob = desk._seal_v10_raw(password, prefix + b"desk-session")
        if blob is None:
            return
        self.assertEqual(desk.decrypt_v10(blob, password, host), "desk-session")
        self.assertIsNone(desk.decrypt_v10(blob, password, other))
        self.assertIsNone(desk.decrypt_v10(blob, password))
        wrong = desk._seal_v10_raw(password, hashlib.sha256(other.encode("utf-8")).digest() + b"other-session")
        now = 1_700_000_000
        chrome_now = desk._chrome_now(now)
        header, reason = desk.cookie_header_from_rows(
            [(host, "sid", blob, chrome_now + 10**12)],
            password, now_utc=now,
        )
        self.assertEqual(reason, "ok")
        self.assertEqual(header, "sid=desk-session")
        missed, missed_reason = desk.cookie_header_from_rows(
            [(host, "sid", wrong, chrome_now + 10**12)],
            password, now_utc=now,
        )
        self.assertIsNone(missed)
        self.assertEqual(missed_reason, "chrome-unread")

    def test_a_linux_chrome_cookie_opens_with_one_round(self):
        import sqlite3
        import tempfile
        import d2jsp_chrome as desk
        now = 1_700_000_000
        chrome_now = desk._chrome_now(now)
        blob = desk._seal_v10_raw("peanuts", b"desk-session", rounds=1)
        if blob is None:
            return
        self.assertEqual(desk.decrypt_v10(blob, "peanuts", rounds=1), "desk-session")
        self.assertIsNone(desk.decrypt_v10(blob, "peanuts"))
        self.assertIn("X11; Linux x86_64", desk.chrome_user_agent(platform="linux", version="120.0.0.0"))
        self.assertIn("Macintosh", desk.chrome_user_agent(platform="darwin", version="120.0.0.0"))
        self.assertEqual(
            desk._chrome_bin(platform="linux", which=lambda name: "/usr/bin/google-chrome" if name == "google-chrome" else None),
            "/usr/bin/google-chrome",
        )
        self.assertIsNone(desk._chrome_bin(platform="linux", which=lambda name: None))

        class _Proc(object):
            def __init__(self, code, out):
                self.returncode = code
                self.stdout = out

        words = desk._linux_chrome_passwords(
            run=lambda *args, **kwargs: _Proc(0, b"keyring-secret\n"),
            tool="/usr/bin/secret-tool",
        )
        self.assertEqual(words[0], "keyring-secret")
        self.assertEqual(words[-1], "peanuts")
        only = desk._linux_chrome_passwords(
            run=lambda *args, **kwargs: _Proc(1, b""),
            tool="/usr/bin/secret-tool",
        )
        self.assertEqual(only, ["peanuts"])
        live = desk.live_cookie_header
        self.assertIn("linux", live.__code__.co_consts)

        folder = tempfile.mkdtemp(prefix="d2jsp-linux-")
        db = os.path.join(folder, "Cookies")
        try:
            con = sqlite3.connect(db)
            con.execute("create table cookies (host_key text, name text, encrypted_value blob, expires_utc integer)")
            con.execute(
                "insert into cookies values (?,?,?,?)",
                (".d2jsp.org", "sid", blob, chrome_now + 10**12),
            )
            con.commit()
            con.close()
            header, reason = desk._linux_cookie_header(
                now_utc=now, paths=[db], passwords=["nope", "peanuts"],
            )
            self.assertEqual(reason, "ok")
            self.assertEqual(header, "sid=desk-session")
            missed, missed_reason = desk._linux_cookie_header(
                now_utc=now, paths=[db], passwords=["nope"],
            )
            self.assertIsNone(missed)
            self.assertEqual(missed_reason, "chrome-unread")
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    def test_a_console_signs_into_d2jsp_with_its_own_chrome(self):
        pane = _between(self.bible, 'id="tab-d2jsp"', 'id="tab-vault"')
        self.assertIn('id="d2jsp-lamp"', pane)
        self.assertNotIn('type="password"', pane)
        show = self.bible.index("window._d2jspShow = function(){")
        show_end = self.bible.index("};", show)
        self.assertIn("d2jspLamp();", self.bible[show:show_end])
        lamp_fn = self.bible.index("function d2jspLamp(")
        self.assertLess(self.bible.index("/* ⟦D2JSP PLANNER ESC END⟧ */"), lamp_fn)
        self.assertLess(lamp_fn, self.bible.index("function postDraft("))
        self.assertIn("/api/d2jsp_login", self.bible[lamp_fn:self.bible.index("function postDraft(")])
        app = _read(os.path.join(HERE, "control_app.py"))
        self.assertEqual(app.count('if path == "/api/d2jsp_login":'), 2)
        self.assertLess(app.index('if path == "/api/d2jsp_login":'), app.index('if path == "/api/d2jsp_quote":'))
        send_at = app.index('if path == "/api/d2jsp_send":')
        self.assertLess(app.rindex('if path == "/api/d2jsp_login":'), send_at)
        import d2jsp_chrome as desk
        saved = desk.live_cookie_header
        saved_sweep = desk._sweep_stale_scratch
        try:
            # REG-2492 - the login check sweeps stale scratch Chromes in this machine's temp dir. That
            # is the console's job; this law reads the answer and touches nothing of his.
            desk._sweep_stale_scratch = lambda now=None, tmp=None: 0
            desk.live_cookie_header = lambda now_utc=None: ("sid=SECRET", "ok")
            on = desk.d2jsp_login_status()
            self.assertEqual(on["state"], "on")
            self.assertNotIn("SECRET", json.dumps(on))
            self.assertNotIn("cookie", on)
            desk.live_cookie_header = lambda now_utc=None: (None, "need-login")
            off = desk.d2jsp_login_status()
            self.assertEqual(off["state"], "off")
            self.assertTrue(off["needsLogin"])
            desk.live_cookie_header = lambda now_utc=None: (None, "chrome-unread")
            unknown = desk.d2jsp_login_status()
            self.assertEqual(unknown["state"], "unknown")
        finally:
            desk.live_cookie_header = saved
            desk._sweep_stale_scratch = saved_sweep
        seen = []

        def run(argv, capture_output=False, timeout=0):
            seen.append(list(argv))
            return type("P", (), {"returncode": 0})()

        launched = []

        def popen(argv, **kw):
            launched.append(list(argv))
            return object()

        which = lambda name: "/usr/bin/google-chrome" if name == "google-chrome" else None
        self.assertTrue(desk._open_chrome_login(platform="linux", run=run, which=which, popen=popen))
        self.assertEqual(launched[-1][0], "/usr/bin/google-chrome")
        self.assertIn(desk.LOGIN_URL, launched[-1])
        self.assertNotIn("--user-data-dir", " ".join(launched[-1]))
        self.assertNotIn("--remote-debugging-port", " ".join(launched[-1]))
        self.assertTrue(all("9222" not in part for part in launched[-1]))
        self.assertFalse(desk._open_chrome_login(platform="linux", run=run, which=lambda name: None, popen=popen))
        self.assertTrue(desk._open_chrome_login(platform="darwin", run=run, popen=popen, env={"HOME": "/h/U"}))
        # #87 (his call 2026-11-06) - the Mac signs in through a profile this console owns, a separate Chrome beside his
        self.assertEqual(seen[-1][:4], ["open", "-na", "Google Chrome", "--args"])
        self.assertIn("--user-data-dir=/h/U/Library/Application Support/TVD/d2jsp-login", seen[-1])
        self.assertIn(desk.LOGIN_URL, seen[-1])
        self.assertTrue(all("9222" not in part for part in seen[-1]))
        win_chrome = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
        local = "C:\\Users\\U\\AppData\\Local"
        self.assertTrue(desk._open_chrome_login(
            platform="win32", run=run, popen=popen, env={"LOCALAPPDATA": local},
            which=lambda name: win_chrome if name == "chrome" else None,
        ))
        self.assertEqual(launched[-1][0], win_chrome)
        self.assertIn(desk.LOGIN_URL, launched[-1])
        # v3861 - Windows signs in through the profile this console owns and reads (Chrome 127+ locks the main
        # profile's d2jsp cookie to Chrome itself): the Chrome it opens is still the one it reads
        self.assertIn("--user-data-dir=" + desk.login_profile_dir(platform="win32", env={"LOCALAPPDATA": local}),
                      launched[-1])
        self.assertNotIn("--remote-debugging-port", " ".join(launched[-1]))
        self.assertTrue(all("9222" not in part for part in launched[-1]))
        self.assertFalse(desk._open_chrome_login(platform="win32", run=run, which=lambda name: None, popen=popen))
        # v3861 - "it opened a login but it was bugged it kept closing": a waited-on Chrome that was not already open
        # IS the browser, and the wait's timeout killed it. Linux and Windows start it and leave it running.
        self.assertEqual([a for a in seen if a[:1] != ["open"]], [],
                         "the login Chrome was started through a wait that kills it: %r" % (seen,))
        saved_open = desk._open_chrome_login
        try:
            desk._open_chrome_login = lambda: False
            shut = desk.open_d2jsp_login()
            self.assertFalse(shut["opened"])
            self.assertNotIn("cookie", shut)
        finally:
            desk._open_chrome_login = saved_open
        self.assertNotIn("d2jsp", _read(BEACON))

    def test_a_windows_chrome_cookie_opens_with_the_raw_key(self):
        """Windows Chrome seals a v10 cookie with the raw key. v20 stays closed."""
        import base64
        import sqlite3
        import tempfile
        from unittest import mock
        import d2jsp_chrome as desk

        key = bytes.fromhex(
            "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f")
        nonce = bytes.fromhex("0102030405060708090a0b0c")
        blob = b"v10" + nonce + bytes.fromhex("618f29bec1e795f53fcb0c29") + bytes.fromhex(
            "9bd2376ff1f62ef14a982c0c2bef8227")
        self.assertEqual(desk.decrypt_windows_gcm(blob, key), "desk-session")
        nist = b"v10" + bytes(12) + bytes.fromhex("0388dace60b6a392f328c2b971b2fe78ab6e47d42cec13bdf53a67b21257bddf")
        self.assertEqual(desk.decrypt_windows_gcm(nist, bytes(16)), "\x00" * 16)
        self.assertIsNone(desk.decrypt_windows_gcm(blob[:-1] + b"\x00", key))
        self.assertIsNone(desk.decrypt_windows_gcm(b"v20" + blob[3:], key))
        self.assertIsNone(desk._dpapi_unprotect(b"\x01\x00\x00\x00not-on-this-os"))
        agent = desk.chrome_user_agent(platform="win32", version="120.0.0.0")
        self.assertIn("Windows NT 10.0; Win64; x64", agent)
        self.assertNotIn("Macintosh", agent)
        self.assertEqual(
            desk._chrome_bin(platform="win32", which=lambda name: "C:\\chrome.exe" if name == "chrome" else None),
            "C:\\chrome.exe",
        )
        self.assertIsNone(desk._chrome_bin(platform="win32", which=lambda name: None))

        wrapped = b"DPAPI" + b"wrapped-bytes"
        state = '{"os_crypt": {"encrypted_key": "%s", "app_bound_encrypted_key": "APPB-LEAVE"}}' % (
            base64.b64encode(wrapped).decode("ascii"))
        seen_blobs = []

        def unprotect(raw):
            seen_blobs.append(bytes(raw))
            if raw == b"wrapped-bytes":
                return key
            if bytes(raw).startswith(b"\x01\x00\x00\x00"):
                return b"old-session"
            return None

        self.assertEqual(desk._windows_key_from_state(state, unprotect), key)
        self.assertEqual(seen_blobs, [b"wrapped-bytes"])
        self.assertNotIn(b"APPB-LEAVE", seen_blobs)

        now = 1_700_000_000
        chrome_now = desk._chrome_now(now)
        host = ".d2jsp.org"
        bound = bytes.fromhex(
            "7631300102030405060708090a0b0c"
            "c382a34efbd2cb3a0add7aad257baf5882500cf46d9c7b9b40ac0f0c501a03"
            "fde081e8b443c689ecc3c5d58b024b828b770d114e618134ea13f3da43")
        self.assertEqual(desk.decrypt_windows_gcm(bound, key, host), "desk-session")
        self.assertIsNone(desk.decrypt_windows_gcm(bound, key, "forums.d2jsp.org"))
        self.assertIsNone(desk.decrypt_windows_gcm(bound, key))
        folder = tempfile.mkdtemp(prefix="d2jsp-win-")
        db = os.path.join(folder, "Cookies")
        try:
            con = sqlite3.connect(db)
            con.execute(
                "create table cookies (host_key text, name text, encrypted_value blob, expires_utc integer)")
            con.execute(
                "insert into cookies values (?,?,?,?)",
                ("example.com", "session", b"LEAKED", chrome_now + 10 ** 12),
            )
            con.execute(
                "insert into cookies values (?,?,?,?)",
                (host, "sid", bound, chrome_now + 10 ** 12),
            )
            old = b"\x01\x00\x00\x00" + b"old-blob"
            con.execute(
                "insert into cookies values (?,?,?,?)",
                (host, "legacy", old, chrome_now + 10 ** 12),
            )
            con.execute(
                "insert into cookies values (?,?,?,?)",
                (host, "locked", b"v20" + b"\x00" * 40, chrome_now + 10 ** 12),
            )
            con.commit()
            con.close()
            header, reason = desk._windows_cookie_header(
                now_utc=now, paths=[db], key=key, unprotect=unprotect,
            )
            self.assertEqual(reason, "ok")
            self.assertIn("sid=desk-session", header)
            self.assertIn("legacy=old-session", header)
            self.assertNotIn("LEAKED", header)
            unread, why = desk._windows_rows_to_header(
                [(host, "locked", b"v20" + b"\x00" * 40, chrome_now + 10 ** 12)],
                key, now, unprotect,
            )
            self.assertIsNone(unread)
            self.assertEqual(why, "chrome-locked", "a v20 (app-bound) cookie no longer says the console signs in itself")
            self.assertTrue(all(not bytes(raw).startswith(b"v20") for raw in seen_blobs))
        finally:
            shutil.rmtree(folder, ignore_errors=True)

        called = {}

        def fake_header(now_utc=None):
            called["yes"] = True
            return "sid=desk-session", "ok"

        saved = desk._windows_cookie_header
        desk._windows_cookie_header = fake_header
        try:
            with mock.patch.object(desk.sys, "platform", "win32"):
                header, reason = desk.live_cookie_header()
            self.assertTrue(called.get("yes"))
            self.assertEqual(header, "sid=desk-session")
            self.assertEqual(reason, "ok")
        finally:
            desk._windows_cookie_header = saved

    def test_windows_reads_chromes_version_without_launching_chrome(self):
        """v3862 - on Windows `chrome.exe --version` OPENS A BROWSER WINDOW instead of printing a version. MEASURED
        2026-11-05 on the old ALT: the console's proof of this very law opened Chrome over and over ("chrome keeps
        reopening a page randomly"). The version is the folder Chrome installs beside chrome.exe; nothing is run."""
        from unittest import mock
        import d2jsp_chrome as desk
        ran = []

        def no_launch(argv, *a, **k):
            ran.append(list(argv))
            raise AssertionError("Chrome was launched to read its version: %r" % (argv,))
        with mock.patch.object(desk.sys, "platform", "win32"), \
                mock.patch.object(desk.subprocess, "run", no_launch), \
                mock.patch.object(desk, "_chrome_bin", lambda platform=None, which=None: "C:\\Chrome\\Application\\chrome.exe"), \
                mock.patch.object(desk.os, "listdir", lambda d: ["chrome.exe", "155.0.1.2", "156.0.8078.80", "SetupMetrics"]):
            agent = desk.chrome_user_agent()
        self.assertEqual(ran, [], "the Windows version read ran a process")
        self.assertIn("Chrome/156.0.8078.80", agent, "the newest version folder is not the version")
        self.assertIn("Windows NT 10.0", agent)
        self.assertIsNone(desk._windows_chrome_version(None))
        self.assertIsNone(desk._windows_chrome_version("C:\\x\\chrome.exe", listdir=lambda d: ["chrome.exe", "Locales"]))

        def unreadable(d):
            raise OSError("denied")
        self.assertIsNone(desk._windows_chrome_version("C:\\x\\chrome.exe", listdir=unreadable))

    def test_a_windows_console_signs_in_through_a_profile_it_owns(self):
        """v3861 - MEASURED 2026-11-05 on the work ALT (Chrome 156): the main profile's d2jsp cookies are v20, so the lamp
        stayed grey signed in or not. A profile the console owns stores v10, opened by its own Local State key; while its
        Chrome runs, Windows refuses the cookie file ("unable to open database file"), which is login-open."""
        import base64
        import sqlite3
        import tempfile
        import d2jsp_chrome as desk

        key = bytes.fromhex("000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f")
        state = '{"os_crypt": {"encrypted_key": "%s", "app_bound_encrypted_key": "APPB-LEAVE"}}' % (
            base64.b64encode(b"DPAPI" + b"wrapped-bytes").decode("ascii"))

        def unprotect(raw):
            return key if bytes(raw) == b"wrapped-bytes" else None

        now = 1_700_000_000
        far = desk._chrome_now(now) + 10 ** 12
        bound = bytes.fromhex(
            "7631300102030405060708090a0b0c"
            "c382a34efbd2cb3a0add7aad257baf5882500cf46d9c7b9b40ac0f0c501a03"
            "fde081e8b443c689ecc3c5d58b024b828b770d114e618134ea13f3da43")

        def profile(folder, rows, with_state=True):
            os.makedirs(os.path.join(folder, "Default", "Network"))
            if with_state:
                with open(os.path.join(folder, "Local State"), "w", encoding="utf-8") as fh:
                    fh.write(state)
            con = sqlite3.connect(os.path.join(folder, "Default", "Network", "Cookies"))
            con.execute("create table cookies (host_key text, name text, encrypted_value blob, expires_utc integer)")
            for r in rows:
                con.execute("insert into cookies values (?,?,?,?)", r)
            con.commit()
            con.close()
            return folder

        top = tempfile.mkdtemp(prefix="d2jsp-own-")
        saved = (desk._read_rows, desk.login_profile_dir, desk.live_cookie_header, desk._sweep_stale_scratch)
        try:
            own = profile(os.path.join(top, "own"), [(".d2jsp.org", "sid", bound, far)])
            self.assertEqual(desk._own_login_header(now_utc=now, root=own, unprotect=unprotect),
                             ("sid=desk-session", "ok"), "the console's own profile did not open with its own key")
            self.assertEqual(desk._own_login_header(now_utc=now, root=os.path.join(top, "never"))[1], "no-profile")
            bare = profile(os.path.join(top, "bare"), [("example.com", "x", b"v10zz", far)])
            self.assertEqual(desk._own_login_header(now_utc=now, root=bare, unprotect=unprotect)[1], "need-login")

            def held(path):
                raise sqlite3.OperationalError("unable to open database file")
            desk._read_rows = held
            self.assertEqual(desk._own_login_header(now_utc=now, root=own, unprotect=unprotect), (None, "login-open"),
                             "an open sign-in window read as anything but login-open")
            desk.login_profile_dir = lambda platform=None, env=None: own
            self.assertEqual(desk._windows_cookie_header(now_utc=now, unprotect=unprotect), (None, "login-open"))
            desk._read_rows = saved[0]
            self.assertEqual(desk._windows_cookie_header(now_utc=now, unprotect=unprotect), ("sid=desk-session", "ok"),
                             "the own profile is not asked first - a locked main profile would win")
            main = profile(os.path.join(top, "main"), [(".d2jsp.org", "member_id", b"v20" + b"\x00" * 40, far)])
            self.assertEqual(desk._windows_cookie_header(now_utc=now, paths=[os.path.join(main, "Default", "Network",
                                                         "Cookies")], key=key, unprotect=unprotect),
                             (None, "chrome-locked"))

            desk._sweep_stale_scratch = lambda now=None, tmp=None: 0
            desk.live_cookie_header = lambda now_utc=None: (None, "chrome-locked")
            lk = desk.d2jsp_login_status()
            self.assertEqual((lk["state"], lk.get("needsLogin")), ("off", True))
            self.assertIn("own d2jsp window", lk["why"])
            desk.live_cookie_header = lambda now_utc=None: (None, "login-open")
            op = desk.d2jsp_login_status()
            self.assertEqual((op["state"], op["kind"]), ("off", "signing-in"))
            self.assertIn("close it", op["why"])
        finally:
            desk._read_rows, desk.login_profile_dir, desk.live_cookie_header, desk._sweep_stale_scratch = saved
            shutil.rmtree(top, ignore_errors=True)

    def test_a_vault_filing_can_be_removed_from_the_trade_list(self):
        if NODE is None:
            self.skipTest("node is not on this machine")
        pane = _between(self.bible, 'id="tab-d2jsp"', 'id="tab-vault"')
        script = pane.split("<script>", 1)[1].split("</script>", 1)[0]
        self.assertNotIn("stays on this list, because the vault still files it.", pane)
        rm = script.index("var rm = t.closest('[data-d2jsp-remove]')")
        rm_end = script.index("t.closest('[data-d2jsp-draft-close]')", rm)
        removed = script[rm:rm_end]
        self.assertIn("d2r_d2jsp_hide", removed)
        self.assertNotIn("d2r_muleAssign", removed)
        self.assertNotIn("vaultPlannerFile", removed)
        self.assertNotIn("/api/d2jsp_send", removed)
        hide_fn = script.index("  function hiddenOf(")
        # REG-2882 - hiddenOf's own body, to the next room function: REG-2872's post log and REG-2873's trade state now sit
        # between hiddenOf and topicUrl (7,591 chars, measured), so a hiddenOf-to-topicUrl window went red on reach
        hide_end = script.index("\n  function ", hide_fn + 1)
        self.assertIn("d2r_d2jsp_hide", script[hide_fn:hide_end])
        listed = script.index("function listedNames()")
        price = script.index("function priceText(", listed)
        self.assertIn("hiddenOf(", script[listed:price])
        file_at = script.index("function fileGear(")
        open_at = script.index("window._d2jspPlannerOpen = function", file_at)
        self.assertLess(open_at - file_at, 1800)
        filed = script[file_at:open_at]
        self.assertLess(filed.index("d2jspIsQuest"), filed.index("d2r_d2jsp_hide"))
        self.assertNotIn("vaultPlannerFile", filed)
        self.assertNotIn("d2jsp", _read(BEACON))
        stubs = r"""
var clicks = [];
var store = {
  'd2r_d2jsp_gear': JSON.stringify({"Guardian's Thunder": { entry: { id: 'thunder', rolls: {}, affixes: [] } }}),
  'd2r_d2jsp_sold': JSON.stringify({"Gheed's Fortune": 1, "Guardian's Thunder": 1}),
  'd2r_d2jsp_fg': JSON.stringify({"Gheed's Fortune": "15"})
};
var mule = JSON.stringify({"Gheed's Fortune":"m1","Horadric Cube":"m1"});
var muleWrites = 0;
var list = {
  innerHTML: '',
  attrs: {},
  getAttribute: function(k){ return this.attrs[k] || null; },
  setAttribute: function(k, v){ this.attrs[k] = v; },
  querySelectorAll: function(){ return []; }
};
var statusEl = { textContent: '' };
var lamp = {
  title: '',
  attrs: {},
  setAttribute: function(k, v){ this.attrs[k] = v; },
  getAttribute: function(k){ return this.attrs[k] || null; },
  removeAttribute: function(k){ delete this.attrs[k]; }
};
var document = {
  documentElement: { classList: { contains: function(){ return false; } } },
  getElementById: function(id){
    if (id === 'd2jsp-list') return list;
    if (id === 'd2jsp-status') return statusEl;
    if (id === 'd2jsp-lamp') return lamp;
    return null;
  },
  addEventListener: function(type, fn){ if (type === 'click') clicks.push(fn); },
  createElement: function(){
    return { style: {}, hidden: true, innerHTML: '', querySelector: function(){ return null; }, querySelectorAll: function(){ return []; }, setAttribute: function(){}, appendChild: function(){} };
  },
  body: { appendChild: function(){} },
  querySelectorAll: function(){ return []; }
};
var localStorage = {
  getItem: function(k){ return Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null; },
  setItem: function(k, v){ store[k] = String(v); }
};
function fetch(){
  return Promise.resolve({ json: function(){ return Promise.resolve({ state: 'unknown', why: 'unread' }); } });
}
var window = {
  addEventListener: function(){},
  LSR: {
    getItem: function(k){ return k === 'd2r_muleAssign' ? mule : null; },
    setItem: function(){ muleWrites++; }
  },
  _cbHostOn: function(){ return false; },
  _cbHostOpen: function(ctx){ window._host = ctx; return true; },
  _cbItem: function(){ return null; },
  _cbShown: function(entry){
    if (entry && entry.id === 'cube') return { name: 'Horadric Cube', base: '' };
    return { name: "Gheed's Fortune", base: '' };
  },
  _cbLineHtml: function(){ return ''; }
};
"""
        body = r"""
function removes(html){ return (String(html).match(/data-d2jsp-remove=/g) || []).length; }
function clickRemove(name){
  var btn = {
    getAttribute: function(k){ return k === 'data-d2jsp-remove' ? name : ''; },
    closest: function(sel){
      if (sel === '#tab-d2jsp' || sel === '[data-d2jsp-remove]') return btn;
      return null;
    }
  };
  clicks[0]({ target: btn, preventDefault: function(){} });
}
window._d2jspShow();
var opened = list.innerHTML;
clickRemove("Gheed's Fortune");
var after = list.innerHTML;
var said = statusEl.textContent;
var hide = JSON.parse(store['d2r_d2jsp_hide'] || '{}');
var sold = JSON.parse(store['d2r_d2jsp_sold'] || '{}');
var gear = JSON.parse(store['d2r_d2jsp_gear'] || '{}');
var fg = JSON.parse(store['d2r_d2jsp_fg'] || '{}');
window._d2jspShow();
var again = list.innerHTML;
clickRemove('');
var blankHide = JSON.parse(store['d2r_d2jsp_hide'] || '{}');
window._d2jspPlannerOpen('');
var quest = window._host.write({ id: 'cube' });
window._d2jspShow();
var afterQuest = list.innerHTML;
window._d2jspPlannerOpen('');
var added = window._host.write({ id: 'gheed', rolls: {}, affixes: [] });
window._host.render();
var back = list.innerHTML;
var hideBack = JSON.parse(store['d2r_d2jsp_hide'] || '{}');
clickRemove("Guardian's Thunder");
var manual = list.innerHTML;
var gearGone = JSON.parse(store['d2r_d2jsp_gear'] || '{}');
var hideManual = JSON.parse(store['d2r_d2jsp_hide'] || '{}');
process.stdout.write(JSON.stringify({
  listeners: clicks.length,
  openedHasGheed: opened.indexOf("Gheed's Fortune") >= 0,
  openedHasThunder: opened.indexOf("Guardian's Thunder") >= 0,
  openedHasCube: opened.indexOf('Horadric Cube') >= 0,
  openedRemoves: removes(opened),
  afterHasGheed: after.indexOf("Gheed's Fortune") >= 0,
  afterHasThunder: after.indexOf("Guardian's Thunder") >= 0,
  afterRemoves: removes(after),
  said: said,
  hideGheed: hide["Gheed's Fortune"] || 0,
  soldGheed: sold["Gheed's Fortune"] || 0,
  soldThunder: sold["Guardian's Thunder"] || 0,
  gearThunder: gear["Guardian's Thunder"] ? 1 : 0,
  fgGheed: fg["Gheed's Fortune"] || '',
  muleWrites: muleWrites,
  muleSame: mule === JSON.stringify({"Gheed's Fortune":"m1","Horadric Cube":"m1"}),
  vaultStored: Object.prototype.hasOwnProperty.call(store, 'd2r_muleAssign'),
  againHasGheed: again.indexOf("Gheed's Fortune") >= 0,
  againHasThunder: again.indexOf("Guardian's Thunder") >= 0,
  blankHide: blankHide[""] || 0,
  questOk: !!(quest && quest.ok),
  afterQuestHasCube: afterQuest.indexOf('Horadric Cube') >= 0,
  afterQuestHasGheed: afterQuest.indexOf("Gheed's Fortune") >= 0,
  addedOk: !!(added && added.ok),
  backHasGheed: back.indexOf("Gheed's Fortune") >= 0,
  backHasThunder: back.indexOf("Guardian's Thunder") >= 0,
  backRemoves: removes(back),
  hideBack: hideBack["Gheed's Fortune"] || 0,
  manualHasGheed: manual.indexOf("Gheed's Fortune") >= 0,
  manualHasThunder: manual.indexOf("Guardian's Thunder") >= 0,
  gearAfter: gearGone["Guardian's Thunder"] ? 1 : 0,
  hideThunder: hideManual["Guardian's Thunder"] || 0
}));
"""
        out = json.loads(_node(stubs + script, body))
        self.assertEqual(out["listeners"], 1)
        self.assertTrue(out["openedHasGheed"])
        self.assertTrue(out["openedHasThunder"])
        self.assertFalse(out["openedHasCube"])
        self.assertEqual(out["openedRemoves"], 2)
        self.assertFalse(out["afterHasGheed"])
        self.assertTrue(out["afterHasThunder"])
        self.assertEqual(out["afterRemoves"], 1)
        self.assertEqual(out["said"], "Gheed's Fortune was removed from this list.")
        self.assertEqual(out["hideGheed"], 1)
        self.assertEqual(out["soldGheed"], 0)
        self.assertEqual(out["soldThunder"], 1)
        self.assertEqual(out["gearThunder"], 1)
        self.assertEqual(out["fgGheed"], "15")
        self.assertEqual(out["muleWrites"], 0)
        self.assertTrue(out["muleSame"])
        self.assertFalse(out["vaultStored"])
        self.assertFalse(out["againHasGheed"])
        self.assertTrue(out["againHasThunder"])
        self.assertEqual(out["blankHide"], 0)
        self.assertFalse(out["questOk"])
        self.assertFalse(out["afterQuestHasCube"])
        self.assertFalse(out["afterQuestHasGheed"])
        self.assertTrue(out["addedOk"])
        self.assertTrue(out["backHasGheed"])
        self.assertTrue(out["backHasThunder"])
        self.assertEqual(out["backRemoves"], 2)
        self.assertEqual(out["hideBack"], 0)
        self.assertTrue(out["manualHasGheed"])
        self.assertFalse(out["manualHasThunder"])
        self.assertEqual(out["gearAfter"], 0)
        self.assertEqual(out["hideThunder"], 1)

    def test_a_ladder_console_names_board_271_and_a_digit_stays_in_the_price_box(self):
        if NODE is None:
            self.skipTest("node is not on this machine")
        import d2jsp_chrome as desk
        edited = []

        def edit_post(topic, subject, text, cookie):
            edited.append(topic)
            return topic

        def chrome_post(subject, text, cookie):
            return "https://forums.d2jsp.org/topic.php?t=2&f=271"

        code, out = _send_fresh(desk,
            {"subject": "Selling Grief", "body": "Selling Grief\n30 fg", "forum": 271,
             "topic": "https://forums.d2jsp.org/topic.php?t=9&f=268"},
            "http://127.0.0.1:17772", "127.0.0.1:17772", 17772,
            cookie_get=lambda: ("sid=SECRETCOOKIE", "ok"),
            chrome_post=chrome_post, edit_post=edit_post,
        )
        self.assertEqual(code, 200)
        self.assertTrue(out["ok"])
        self.assertEqual(out["reason"], "submitted")
        self.assertIn("f=271", out["topic"])
        self.assertEqual(edited, [])

        code, out = _send_fresh(desk,
            {"subject": "Selling Grief", "body": "Selling Grief\n30 fg", "forum": 243},
            "http://127.0.0.1:17772", "127.0.0.1:17772", 17772,
            cookie_get=lambda: ("sid=SECRETCOOKIE", "ok"),
            chrome_post=chrome_post,
        )
        self.assertEqual(out["reason"], "wrong-board")

        body = r"""
var main = d2jspBoard();
var mainSay = d2jspBoardSay();
var mainDraft = d2jspDraft('Gheed\'s Fortune', 'Grand Charm', '', 1, 15);
window = { D2R_PROFILE: 'ladder' };
var ladder = d2jspBoard();
var ladderSay = d2jspBoardSay('ask');
var ladderDraft = d2jspDraft('Gheed\'s Fortune', 'Grand Charm', '', 1, 15);
var saved268 = 'https://forums.d2jsp.org/topic.php?t=9&f=268';
process.stdout.write(JSON.stringify({
  main: main, mainSay: mainSay, mainForum: mainDraft.forum,
  ladder: ladder, ladderSay: ladderSay, ladderForum: ladderDraft.forum
}));
"""
        got = json.loads(_node(self.desk, body))
        self.assertEqual(got["main"], 268)
        self.assertEqual(got["mainForum"], 268)
        self.assertIn("Board 268, D2:R RotW Softcore Trading.", got["mainSay"])
        self.assertEqual(got["ladder"], 271)
        self.assertEqual(got["ladderForum"], 271)
        self.assertEqual(got["ladderSay"], "Asking Chrome on this machine to post on board 271.")
        keys = self.bible.index("document.addEventListener('keydown', e => {")
        guard = self.bible[keys:self.bible.index("const key = e.shiftKey", keys)]
        self.assertIn("e.target && e.target.tagName", guard)
        self.assertIn("[data-d2jsp-fg]", guard)
        self.assertIn("pointerdown", self.bible[self.bible.rindex("document.addEventListener('pointerdown'", 0, keys):keys])
        self.assertIn("function catalogBase(", self.bible)
        self.assertIn("_cbItemsNamed", self.bible[self.bible.index("function catalogBase("):self.bible.index("function baseOf(", self.bible.index("function catalogBase("))])


    def test_a_chrome_version_read_that_times_out_still_names_chrome(self):
        # REG-2575 - `google-chrome --version` (Linux) or `defaults read` (Mac) that does not answer in 5 s
        # raised subprocess.TimeoutExpired through _headers, so a challenge-page post answered "unread"
        # before anything was fetched. CI's loaded runner hit it. A version that cannot be read is the
        # default version, and the send goes on. Both halves are asked on every host: the module sees
        # the platform under test, so neither proof below needs a Mac or a Linux box.
        import d2jsp_chrome as desk
        real_sys = sys

        class _Host(object):
            def __init__(self, platform):
                self.platform = platform

            def __getattr__(self, name):
                return getattr(real_sys, name)

        def transport(method, url, headers, data):
            return 200, {}, b"<title>Just a moment...</title>"

        for platform in ("linux", "darwin"):
            asked = []

            def slow_run(argv, *args, **kwargs):
                asked.append(list(argv))
                raise subprocess.TimeoutExpired(argv, kwargs.get("timeout", 5))

            real_run, real_bin, real_mod_sys = desk.subprocess.run, desk._chrome_bin, desk.sys
            desk.subprocess.run = slow_run
            desk._chrome_bin = lambda platform=None, which=None: "/opt/chrome/chrome"
            desk.sys = _Host(platform)
            try:
                agent = desk.chrome_user_agent()
                code, out = _send_fresh(desk,
                    {"subject": "WTS Grief Phase Blade", "body": "WTS Grief Phase Blade\n30 fg", "forum": 268},
                    "http://127.0.0.1:17772", "127.0.0.1:17772", 17772,
                    cookie_get=lambda: ("sid=SECRETCOOKIE", "ok"),
                    transport=transport, open_login=lambda: True,
                    chrome_post=lambda subject, text, cookie: "https://forums.d2jsp.org/topic.php?t=9&f=268",
                )
            finally:
                desk.subprocess.run, desk._chrome_bin, desk.sys = real_run, real_bin, real_mod_sys
            self.assertTrue(asked, "%s: the version read was never asked, so this case proved nothing" % platform)
            self.assertIn("Chrome/131.0.0.0", agent, platform)
            self.assertEqual((code, out.get("reason")), (200, "submitted"), (platform, out))
            self.assertNotIn("SECRETCOOKIE", json.dumps(out))

    def test_a_quote_parser_that_times_out_is_unread(self):
        # REG-2576 - the quote's node parser runs with a 20 s timeout and caught only OSError, so a
        # node that did not answer raised subprocess.TimeoutExpired out of d2jsp_quote instead of the
        # "unread" reading every other failure on that path gives. A page that was not parsed is unread.
        import d2jsp_chrome as desk
        asked = []

        def slow_node(prog, page):
            asked.append(page)
            raise subprocess.TimeoutExpired(["node", "-e"], 20)

        def transport(method, url, headers, data):
            return 200, {}, b"Grief 40 fg"

        real_ua = desk.chrome_user_agent
        desk.chrome_user_agent = lambda *a, **k: "Mozilla/5.0 Chrome/131.0.0.0"
        try:
            code, out = desk.d2jsp_quote(
                "Grief", "http://127.0.0.1:17772", "127.0.0.1:17772", 17772,
                cookie_get=lambda: ("sid=SECRETCOOKIE", "ok"), transport=transport,
                node_run=slow_node, chrome_fetch=False,
            )
        finally:
            desk.chrome_user_agent = real_ua
        self.assertEqual(asked, ["Grief 40 fg"], "the parser was never asked, so this case proved nothing")
        self.assertEqual((code, out.get("fg"), out.get("reason")), (200, None, "unread"), out)
        self.assertNotIn("SECRETCOOKIE", json.dumps(out))

RED_PROOF = [
    {
        "why": "v3862 - Windows reads Chrome's version by launching chrome.exe --version, which opens a browser window",
        "file": "tv/d2jsp_chrome.py",
        "find": "            version = _windows_chrome_version(_chrome_bin(platform=plat)) or version\n",
        "replace": "            subprocess.run([_chrome_bin(platform=plat), \"--version\"], capture_output=True, timeout=5)\n",
        "matches": 1,
    },
    {"why": "v3861 - a paused console reads as a reader that never answered (his Shako click during a push)",
     "file": "bible.html",
     "find": "  if (q.reason === 'paused') return 'Price not read yet - this machine is running its checks (' + (q.say || 'paused while checks run') + '). It reads as soon as they finish.';\n",
     "replace": "",
     "matches": 1},
    {"why": "GrokBot bug 9 - the price line prints the raw UTC stamp again",
     "file": "bible.html",
     "find": "    var when = d2jspWhen(q.readAt) ? (', read ' + d2jspWhen(q.readAt)) : '';\n",
     "replace": "    var when = q.readAt ? (', read ' + q.readAt) : '';\n",
     "matches": 1, "needs": "node"},
    {"why": "GrokBot bug 9 - a page no price reader answered says it read nothing at a made-up time again",
     "file": "bible.html",
     "find": "  if (q.reason === 'unanswered') return 'Public price unknown. No price reader answered this page.';\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {
        "why": "REG-2188 - a no-Origin request the browser marks cross-site or same-site is trusted on Host alone again, "
               "so any page he visits can make the console read his cookies and start a scratch Chrome",
        "file": "tv/d2jsp_chrome.py",
        "find": '    if str(sec_fetch_site or "").strip().lower() in {"cross-site", "same-site"}:\n        return False\n',
        "replace": "    pass\n",
        "matches": 1,
    },
    {
        "why": "REG-2190 - the sweep's age gate is gone, so a scratch profile an op still holds is swept from under it",
        "file": "tv/d2jsp_chrome.py",
        "find": "        return now - os.lstat(path).st_mtime >= _SCRATCH_STALE_S\n",
        "replace": "        return True\n",
        "matches": 1,
    },
    {
        "why": "REG-2490 - a click that stayed on post.php is reported not-posted again, the 'nothing was posted' "
               "that invites a duplicate",
        "file": "tv/d2jsp_chrome.py",
        "find": '        return answer({"ok": False, "reason": "maybe-sent", "board": int(board), "at": at})\n',
        "replace": '        return answer({"ok": False, "reason": "not-posted"})\n',
        "matches": 1,
    },
    {
        "why": "REG-2575 - a Chrome version read that times out raises through the send again, so a "
               "challenge-page post answers unread before anything is fetched",
        "file": "tv/d2jsp_chrome.py",
        "find": "        elif str(plat).startswith(\"linux\") and plat == sys.platform:\n"
                "            binary = _chrome_bin(platform=plat)\n"
                "            if binary:\n"
                "                try:\n"
                "                    proc = subprocess.run(\n"
                "                        [binary, \"--version\"],\n"
                "                        capture_output=True, timeout=5, text=True,\n"
                "                        encoding=\"utf-8\", errors=\"replace\",\n"
                "                    )\n"
                "                except (OSError, subprocess.SubprocessError):\n"
                "                    proc = None\n",
        "replace": "        elif str(plat).startswith(\"linux\") and plat == sys.platform:\n"
                   "            binary = _chrome_bin(platform=plat)\n"
                   "            if binary:\n"
                   "                try:\n"
                   "                    proc = subprocess.run(\n"
                   "                        [binary, \"--version\"],\n"
                   "                        capture_output=True, timeout=5, text=True,\n"
                   "                        encoding=\"utf-8\", errors=\"replace\",\n"
                   "                    )\n"
                   "                except OSError:\n"
                   "                    proc = None\n",
        "matches": 1,
    },
    {
        "why": "REG-2575 - the Mac half: a `defaults read` that times out raises through the send again",
        "file": "tv/d2jsp_chrome.py",
        "find": "            except (OSError, subprocess.SubprocessError):\n                proc = None\n",
        "replace": "            except OSError:\n                proc = None\n",
        "matches": 1,
    },
    {
        "why": "REG-2576 - a quote parser that times out raises out of d2jsp_quote again instead of reading unread",
        "file": "tv/d2jsp_chrome.py",
        "find": "        proc = node_run(prog, str(html or \"\"))\n    except (OSError, subprocess.SubprocessError):\n",
        "replace": "        proc = node_run(prog, str(html or \"\"))\n    except OSError:\n",
        "matches": 1,
    },
    {
        "why": "a Windows Chrome cookie stays unread again, so a price ask on that PC never reaches the forum",
        "file": "tv/d2jsp_chrome.py",
        "find": "    if sys.platform == \"win32\":\n        return _windows_cookie_header(now_utc)\n",
        "replace": "    pass\n",
        "matches": 1,
    },
    {
        "why": "v3861 - the login Chrome is waited on again, and the wait's timeout kills a Chrome that was not already open",
        "file": "tv/d2jsp_chrome.py",
        "find": "        (popen or subprocess.Popen)(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,\n"
                "                                    stderr=subprocess.DEVNULL, **kw)\n",
        "replace": "        runner(argv, capture_output=True, timeout=5)\n",
        "matches": 1,
    },
    {
        "why": "v3861 - Windows opens the login in Chrome's main profile again, whose d2jsp cookie Chrome locks to itself",
        "file": "tv/d2jsp_chrome.py",
        "find": "            return False\n        own = login_profile_dir(platform=plat, env=env)\n",
        "replace": "            return False\n        own = None\n",
        "matches": 1,
    },
    {
        "why": "v3861 - the console's own sign-in profile is never asked, so a signed-in Windows PC stays grey",
        "file": "tv/d2jsp_chrome.py",
        "find": "    if paths is None and key is None and state_text is None:\n"
                "        # v3861 - the profile this console owns is asked first",
        "replace": "    if False:\n"
                   "        # v3861 - the profile this console owns is asked first",
        "matches": 1,
    },
    {
        "why": "v3861 - an open sign-in window reads as signed out, not as signing in",
        "file": "tv/d2jsp_chrome.py",
        "find": "    except (OSError, sqlite3.Error):\n        return None, \"login-open\"\n",
        "replace": "    except (OSError, sqlite3.Error):\n        return None, \"need-login\"\n",
        "matches": 1,
    },
    {
        "why": "v3861 - an app-bound (v20) cookie reads as unreadable again, never as the sign-in the console does itself",
        "file": "tv/d2jsp_chrome.py",
        "find": "        return None, (\"chrome-locked\" if locked else \"chrome-unread\")",
        "replace": "        return None, \"chrome-unread\"",
        "matches": 1,
    },
    {"why": "REG-2882 - the receipt says neither Confirmed nor Not sent (the window reads showReceipt itself)",
     "file": "bible.html",
     "find": "    var head = kind === 'confirmed' ? 'Confirmed' : (kind === 'maybe' ? 'Maybe sent' : 'Not sent');\n",
     "replace": "    var head = kind === 'confirmed' ? 'Posted' : (kind === 'maybe' ? 'Maybe sent' : 'Unsent');\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2882 - hiddenOf no longer reads the hide map (the window reads hiddenOf itself)",
     "file": "bible.html",
     "find": "  function hiddenOf(name){\n    var v = readMap('d2r_d2jsp_hide')[name];\n",
     "replace": "  function hiddenOf(name){\n    var v = readMap('d2r_d2jsp_hidden')[name];\n",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
